"""Prove scoped JIT settings against unchanged Native financial readers.

Only a private predecessor clone and session-local GUC controls are created,
inside a savepoint that is always rolled back. No CP6 definition is changed.
"""
import hashlib
import json
import subprocess
from pathlib import Path
from time import monotonic
from cp7_p19_analysis_equivalence import BASE


def compare(cur, query, api, auth, kind='workspace'):
    assert kind in ('workspace', 'analysis')
    path = f"scripts/cp7-src/finance/{'read' if kind == 'workspace' else 'analysis'}.sql"
    root = Path(__file__).resolve().parents[1]
    source = subprocess.check_output(['git', '-C', str(root), 'show', f'{BASE}:{path}'], text=True)
    marker = f'create function cp7_finance.{kind}('
    start = source.index(marker)
    end = source.index('$$;', source.index('$$', start) + 2) + 3
    predecessor = source[start:end].replace(marker, f'create function cp7_finance.p19_previous_{kind}(', 1)
    signature = f'cp7_finance.{kind}(jsonb)'
    api.admin(cur)
    definition = cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0]
    config = cur.execute('select proconfig from pg_proc where oid=%s::regprocedure', (signature,)).fetchone()[0]
    assert 'jit=off' in config, 'P19_JIT_SCOPE_MISSING'
    before_jit = cur.execute("select current_setting('jit')").fetchone()[0]
    cur.execute('savepoint p19_financial_equivalence')
    try:
        cur.execute(predecessor, prepare=False)
        cur.execute(f'alter function cp7_finance.p19_previous_{kind}(jsonb) owner to cp7_finance_read')
        auth.actor(cur)
        api.admin(cur)  # Retain the real OWNER claims; enter the existing private reader role.
        cur.execute('set local role cp7_finance_read')
        cur.execute('set local jit=on')
        started = monotonic()
        old, current = cur.execute(
            f'select cp7_finance.p19_previous_{kind}(%s::jsonb)::text,'
            f'cp7_finance.{kind}(%s::jsonb)::text',
            (json.dumps(query), json.dumps(query))).fetchone()
        elapsed = round((monotonic() - started) * 1000)
        assert old == current, 'P19_FINANCIAL_FULL_BODY_DIFFERENCE'
        assert cur.execute("select current_setting('jit')").fetchone()[0] == 'on', 'P19_JIT_SETTING_LEAKED'
        # Reader failure must also restore the caller setting. The validation
        # error is the unchanged Native reader contract, not a relaxed branch.
        cur.execute('savepoint p19_financial_invalid')
        try:
            cur.execute(f'select cp7_finance.{kind}(%s::jsonb)', ('{}',))
            raise AssertionError('P19_INVALID_FINANCIAL_QUERY_ACCEPTED')
        except Exception as error:
            expected = 'CP7_FINANCE_QUERY' if kind == 'workspace' else 'CP7_FINANCE_ANALYSIS_QUERY'
            assert getattr(error, 'sqlstate', None) == 'P0001' and expected in str(error), str(error)
        finally:
            cur.execute('rollback to savepoint p19_financial_invalid')
            cur.execute('release savepoint p19_financial_invalid')
        assert cur.execute("select current_setting('jit')").fetchone()[0] == 'on', 'P19_JIT_FAILURE_LEAKED'
    finally:
        cur.execute('rollback to savepoint p19_financial_equivalence')
        cur.execute('release savepoint p19_financial_equivalence')
        api.admin(cur)
    assert cur.execute("select current_setting('jit')").fetchone()[0] == before_jit
    assert cur.execute('select pg_get_functiondef(%s::regprocedure)', (signature,)).fetchone()[0] == definition
    return dict(status='BYTE_IDENTICAL', base=BASE, function=signature,
                utf8_bytes=len(current.encode()), sha256=hashlib.sha256(current.encode()).hexdigest(),
                comparison_ms=elapsed, caller_jit_on_control=True,
                jit_restored_after_success_and_failure=True, definition_restored=True,
                CP6_definitions_changed=False, Native_case_credit_added=0)

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

# 17ce3f76 changed cp7_finance.analysis outputs on purpose (self-check F1/F2: no
# growth/margin ratio on a zero-or-negative revenue base, formula V2; Native P13
# ZERO_BASELINE case). The analysis predecessor therefore carries that formula:
# it is the 17ce3f76 definition without the JIT clause, and the definition just
# before 17ce3f76 must equal BASE plus the JIT clause only. The comparison still
# isolates the JIT scope byte for byte.
FORMULA_V2 = '17ce3f76b4c8836ae7bd7df7169bb3f3c990db61'
JIT = " set jit=off as $$"


def definition_at(root, commit, path, kind):
    source = subprocess.check_output(['git', '-C', str(root), 'show', f'{commit}:{path}'], text=True)
    start = source.index(f'create function cp7_finance.{kind}(')
    return source[start:source.index('$$;', source.index('$$', start) + 2) + 3]


def without_jit(text):
    assert text.count(JIT) == 1, 'P19_JIT_CLAUSE_NOT_EXACTLY_ONCE'
    return text.replace(JIT, ' as $$', 1)


def compare(cur, query, api, auth, kind='workspace'):
    assert kind in ('workspace', 'analysis')
    path = f"scripts/cp7-src/finance/{'read' if kind == 'workspace' else 'analysis'}.sql"
    root = Path(__file__).resolve().parents[1]
    marker = f'create function cp7_finance.{kind}('
    previous = definition_at(root, BASE, path, kind)
    if kind == 'analysis':
        assert without_jit(definition_at(root, f'{FORMULA_V2}^', path, kind)) == previous, 'P19_FORMULA_V2_PARENT_NOT_BASE_PLUS_JIT'
        previous = without_jit(definition_at(root, FORMULA_V2, path, kind))
    predecessor = previous.replace(marker, f'create function cp7_finance.p19_previous_{kind}(', 1)
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

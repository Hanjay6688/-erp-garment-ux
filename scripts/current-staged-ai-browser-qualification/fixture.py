"""Prepared controls for the existing real-Auth browser host, never a new runner.

prepare creates Native fixture business data. It does not create a screen, an
analysis job, a brief, a report, or an Auth session. All browser observations
remain PREPARED until the owning integration runtime actually executes them.
"""
from contextlib import redirect_stdout
from datetime import date
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse
import importlib.util
import json
import os
import sys
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CHECK_TABLE = 'cp7_analysis_stage.source_checks'
CHECK_SEQUENCE = 'sequence:cp7_analysis_stage.source_checks_id_seq'


def disposable_url(value):
    parsed = urlparse(value)
    if (parsed.scheme not in ('postgres', 'postgresql') or
            parsed.hostname not in ('127.0.0.1', 'localhost') or
            parsed.path != '/cp6_auditor_browser' or parsed.query or parsed.fragment):
        raise ValueError('STAGED_AI_DISPOSABLE_BROWSER_COPY_ONLY')
    return value


def plan():
    return dict(status='PREPARED', actual_native_auth_browser_executed=False,
                fixture_creation='accepted B native.setup: staged.analysis.setup + finance.given',
                browser_job_created=False, financial_results_fabricated=False,
                census='cp7_ow04_restore_bundle._data: every non-system row count/hash and sequence',
                excluded_catalog_keys=[], controlled_check_keys=[CHECK_TABLE, CHECK_SEQUENCE],
                production_go=False, independent_acceptance=False)


def load_helpers():
    # Same small Native setup used by the accepted B combined-finance fixture.
    # Use the selected installed backend explicitly; do not invent a parallel
    # installer/Auth server, seed result, or compatibility implementation.
    root = Path(os.environ['D17_18_SELECTED_BACKEND_ROOT']).resolve()
    sys.path.insert(0, str(root / 'scripts'))
    path = root / 'scripts/current-frozen-public-native-qualification/public_finance_cases.py'
    spec = importlib.util.spec_from_file_location('A_staged_ai_retained_native_fixture', path)
    native = importlib.util.module_from_spec(spec)
    argv = sys.argv[:]
    try:
        sys.argv = sys.argv[:1]
        spec.loader.exec_module(native)
        import cp7_ow04_restore_bundle as catalog
    finally:
        sys.argv = argv
    return native, catalog, dict(root=str(root), native_fixture_sha256=sha256(path.read_bytes()).hexdigest(),
                                 catalog_sha256=sha256(Path(catalog.__file__).read_bytes()).hexdigest())


def state(cur, native, catalog):
    native.staged.b.api.admin(cur)
    # Do not replace this census with selected monetary/stock tables, a whole
    # analysis-schema exclusion, or an aggregate which hides keyset changes.
    data = catalog._data(cur)
    assert CHECK_TABLE in data and CHECK_SEQUENCE in data, 'STAGED_AI_SOURCE_CHECK_CENSUS_MISSING'
    sequence = cur.execute("select pg_get_serial_sequence('cp7_analysis_stage.source_checks','id')").fetchone()[0]
    assert sequence == CHECK_SEQUENCE.removeprefix('sequence:'), sequence
    checks = [row[0] for row in cur.execute(
        'select to_jsonb(c) from cp7_analysis_stage.source_checks c order by id').fetchall()]
    assert data[CHECK_TABLE][0] == len(checks)
    return dict(data=data, source_checks=checks, census_keys=len(data),
                table_keys=sum(not key.startswith('sequence:') for key in data),
                sequence_keys=sum(key.startswith('sequence:') for key in data),
                excluded_catalog_keys=[])


def main():
    op = sys.argv[1]
    if op == 'plan':
        print(json.dumps(plan()))
        return
    target = disposable_url(os.environ['AUDITOR_BROWSER_DB_URL'])
    p = json.load(sys.stdin)
    import psycopg
    native, catalog, sources = load_helpers()
    with redirect_stdout(sys.stderr), psycopg.connect(target) as conn, conn.cursor() as cur:
        cur.execute('set transaction isolation level repeatable read')
        native.staged.b.api.admin(cur)
        cur.execute("set local statement_timeout='45s'")
        if op == 'prepare':
            today = date.fromisoformat(p['today'])
            had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
            acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
            if not had:
                cur.execute('grant usage on schema erp to authenticated')
            native.setup(cur, today)
            native.staged.b.api.admin(cur)
            if not had:
                cur.execute('revoke usage on schema erp from authenticated')
            assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
            conn.commit()
            out = dict(query=native.staged.query(today), fixture_only=True,
                       fixture_creation='retained Native analysis and finance writers',
                       browser_job_created=False, browser_screen_created=False,
                       financial_results_fabricated=False, sources=sources)
        elif op == 'state':
            out = state(cur, native, catalog)
            conn.rollback()
        elif op == 'read':
            actor = str(uuid.UUID(p['actor']))
            run = str(uuid.UUID(p['run']))
            targets = p['targets']
            assert isinstance(targets, list) and len(targets) <= 20 and len(set(targets)) == len(targets)
            for key in targets:
                assert len(key.split(':')) == 2
                assert ':'.join(str(uuid.UUID(part)) for part in key.split(':')) == key
            staged = native.staged
            brief = staged.limited(cur, 'erp_cp7_get_staged_ai_brief_v1', (run, json.dumps(targets)), actor)
            original, pages, metadata = staged.fetch(cur, run, actor)
            assert brief['actor_scope_id'] == actor and brief['run_id'] == pages['run_id'] == run
            assert brief['request_id'] == pages['request_id']
            assert brief['identity_hash'] == pages['identity_hash']
            assert brief['totals'] == pages['totals']
            assert original['financial_source'] is None
            out = dict(brief=brief, page_set=pages, page_metadata=metadata,
                       readback='real permitted public Native RPC under the browser actor; no fabricated HTTP identity')
            conn.rollback()
        else:
            raise ValueError('UNKNOWN_STAGED_AI_BROWSER_CONTROL')
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()

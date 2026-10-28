"""Prepared rollback-only reuse of one official check result within one report.

No cached result survives a statement. Browser/worker callers cannot supply
checks; only the existing private date-only helper can call the new helpers.
Native report, blockers, readiness, preflight and close definitions stay intact.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from cp7_hpp_close import native_delta as hpp
from cp7_laundry_unknown_wash import native_delta as wash
spec = importlib.util.spec_from_file_location('retained_readiness_reuse',
    ROOT / 'scripts/current-finance-check-reuse-diagnostic/readiness_reuse.py')
reuse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reuse)
BLOCKERS = 'erp.period_blockers_v1(date,date)'
READINESS = 'erp.period_readiness_v1(date,date)'
PRIVATE_BLOCKERS = 'cp7_finance.read_blockers_checks_diagnostic_v1(date,date,jsonb)'
PRIVATE_READINESS = 'cp7_finance.read_readiness_checks_diagnostic_v1(date,date,jsonb)'
RECORD = 'jsonb_to_recordset(p_checks) as r(check_name text,severity text,issue_count bigint,details text)'


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('SINGLE_CHECK_EXACT_SOURCE_ANCHOR_REQUIRED:' + old[:100])
    return text.replace(old, new, 1)


def derived():
    extract = reuse.snapshot_source.extract
    bf = (ROOT / 'supabase/dev/cp6_bf_t1_family.sql').read_text()
    aw = (ROOT / 'supabase/dev/cp6_aw_t1_family.sql').read_text()
    blockers, raw_blockers = extract(bf, 'erp.period_blockers_v1', '$function$')
    # Apply the exact already-installed OW07 and OW08b extensions to the BF
    # source. Every other dated/blocking/UNKNOWN rule remains byte-for-byte.
    raw_blockers = hpp.once(raw_blockers, hpp.GRNI, hpp.HPP + hpp.GRNI, 'prepared-blockers')
    for label, old, new in wash.STEPS[BLOCKERS]:
        raw_blockers = wash.once(raw_blockers, old, new, BLOCKERS + ':' + label)
    blockers = blockers.split('$function$')[0] + '$function$' + raw_blockers + '$function$;'
    readiness, raw_readiness = extract(aw, 'erp.period_readiness_v1', '$function$')
    bodies, _ = reuse.snapshot_source.expected()
    snapshot = reuse.sibling_body(bodies['snapshot'], bodies['preflight'])
    blocker_candidate = once(blockers,
        'erp.period_blockers_v1(p_through date, p_window_from date)',
        PRIVATE_BLOCKERS.split('(')[0] + '(p_through date, p_window_from date, p_checks jsonb)')
    blocker_candidate = once(blocker_candidate, 'erp.run_v268_financial_report_checks() r', RECORD)
    readiness_candidate = once(readiness,
        'erp.period_readiness_v1(p_through date, p_window_from date)',
        PRIVATE_READINESS.split('(')[0] + '(p_through date, p_window_from date, p_checks jsonb)')
    readiness_candidate = once(readiness_candidate, 'erp.period_blockers_v1(p_through,p_window_from)',
        PRIVATE_BLOCKERS.split('(')[0] + '(p_through,p_window_from,p_checks)')
    snapshot_candidate = once(snapshot, '  d17_snapshot jsonb;d17_preflight jsonb:=null;',
        '  d17_snapshot jsonb;d17_preflight jsonb:=null;d17_checks jsonb;')
    snapshot_candidate = once(snapshot_candidate,
        '  v_readiness:=erp.period_readiness_v1(p_as_of,erp.period_completeness_from_v1());',
        "  select coalesce(jsonb_agg(to_jsonb(d17_check)),'[]'::jsonb) into d17_checks\n"
        "  from erp.run_v268_financial_report_checks() d17_check;\n"
        '  v_readiness:=' + PRIVATE_READINESS.split('(')[0] + '(p_as_of,erp.period_completeness_from_v1(),d17_checks);')
    snapshot_candidate = once(snapshot_candidate, 'erp.run_v268_financial_report_checks() c',
        'jsonb_to_recordset(d17_checks) as c(check_name text,severity text,issue_count bigint,details text)')
    if snapshot_candidate.count('erp.run_v268_financial_report_checks()') != 1:
        raise ValueError('SINGLE_OFFICIAL_CHECK_CALL_REQUIRED')
    return dict(originals={BLOCKERS: raw_blockers, READINESS: raw_readiness, reuse.PRIVATE: snapshot},
                definitions={PRIVATE_BLOCKERS: blocker_candidate, PRIVATE_READINESS: readiness_candidate},
                snapshot_body=snapshot_candidate)


def exact_live(live, expected):
    if live != expected:
        raise ValueError('SINGLE_CHECK_LIVE_PARENT_DEFINITION_CHANGED')


def install_for_rollback(cur, catalog):
    assert cur.connection.info.host in ('localhost', '127.0.0.1') and cur.connection.info.port == 54322
    assert cur.execute('select current_database()').fetchone() == ('cp6_rollback',)
    prepared = derived()
    before = catalog._catalog_rows(cur)
    before_data = catalog._data(cur)
    rows = {name: reuse.row(cur, name) for name in prepared['originals']}
    for name, expected in prepared['originals'].items():
        exact_live(rows[name][0], expected)
        assert rows[name][1:4] == ('s', True, 'postgres'), name
    for name in prepared['definitions']:
        assert cur.execute('select to_regprocedure(%s)', (name,)).fetchone() == (None,)
    for name, definition in prepared['definitions'].items():
        cur.execute(definition, prepare=False)
        cur.execute('alter function ' + name + ' owner to postgres')
        cur.execute('revoke all on function ' + name + ' from public,anon,authenticated,service_role,cp7_capture,cp7_finance_read')
        for role in ('anon','authenticated','service_role','cp7_capture','cp7_finance_read'):
            assert cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (role,name)).fetchone() == (False,)
    old = rows[reuse.PRIVATE]
    new_definition = once(old[5], old[0], prepared['snapshot_body'])
    cur.execute(new_definition, prepare=False)
    assert reuse.row(cur, reuse.PRIVATE) == (prepared['snapshot_body'], *old[1:5], new_definition)
    after = catalog._catalog_rows(cur)
    changed = {(group,key) for group in before for key in set(before[group])|set(after[group])
               if before[group].get(key) != after[group].get(key)}
    assert len(before) == len(after) == 22 and set(before) == set(after)
    assert changed == {('functions', name) for name in (*prepared['definitions'], reuse.PRIVATE)}
    assert catalog._data(cur) == before_data
    return dict(strategy='ONE_OFFICIAL_CHECK_WITHIN_SAME_REPORT', existing_private_replacements=1,
                new_private_functions=2, new_public_functions=0, all22_exact_delta=True,
                original_Native_readiness_blockers_snapshot_preflight_close_unchanged=True,
                all_data_and_sequences_unchanged=True, private_helpers_not_callable_by_browser_or_worker=True,
                existing_helper_authority_unchanged=True, caller_supplied_check_results=False,
                cross_request_cache=False, product_adoption=False, production_go=False,
                parent_body_sha256={name:sha256(body.encode()).hexdigest() for name,body in prepared['originals'].items()},
                candidate_body_sha256=sha256(prepared['snapshot_body'].encode()).hexdigest())

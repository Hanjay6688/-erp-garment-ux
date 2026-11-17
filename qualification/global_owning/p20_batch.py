"""Independently check P20 on the disposable installed Global candidate."""

from contextlib import contextmanager
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import re
from zipfile import ZipFile

from . import owning
from audit.codex import p20_evidence, p20_resume

HEAD = 'a752459a0a8baf1920d0e6d1c1fba6f4ef14af8d'
TREE = '3440cb483c8f809987efb04c3e26072d14039ff2'
PARENT_APP = dict(head='eec7c6cccc374164098528ad8327ac92afda2d21', tree='21c5a7f958476814da4e7fdf9014133e3987b890')
MODE = 'P20_GLOBAL_SUCCESSOR'
ASSETS = 'qualification/global_owning/p20'
CASH = 'P20_AUTH_CASH_01_02'
PLANNER_PERMISSION = 'P20_PLANNER_CURRENT_CUTTING_PERMISSION'
IDS = (PLANNER_PERMISSION,)
PREVIOUS = dict(run=43785739039, artifact=14193992742, bytes=2537,
    sha256='4c7ce2e936fd92cd920721b23253d72dcd6d2e88f06a9016913aef741b052005',
    cases=['P20_CASH_OW09_03', 'P20_CARRY_DATE_05', 'P20_CARRY_CLOSED_06', 'P20_SALE_SERIES_BROWSER'])
PRIOR_RETEST = dict(run=43796086501, artifact=14197221354, bytes=1696,
    sha256='33645db2a0c8b2e96a413342d787cdcf0432ac9f212d066dbfd03b8160eab13b',
    cases=[CASH, 'P20_CARRY_CASH_04'])
ACCESS = 'erp_get_my_access_v1'


def enabled():
    mode = os.environ.get(MODE, '')
    owning.require(mode in ('', HEAD), 'CP7_P20_EXACT_PRODUCT_MODE_REQUIRED')
    return mode == HEAD


def product_checkout(candidate):
    product = Path(candidate).parent / 'p20-product'
    owning.require(owning.git(product, 'rev-parse', 'HEAD', 'HEAD^{tree}').splitlines() == [HEAD, TREE]
                   and not owning.git(product, 'status', '--porcelain=v1', '--untracked-files=no'),
                   'CP7_P20_EXACT_PRODUCT_GIT_SOURCE_REQUIRED')
    return product


def read_original(path, expected):
    raw = owning.read(path, 'CP7_P20_RETAINED_GLOBAL_ORIGINAL_REQUIRED')
    owning.require(len(raw) == expected['bytes'] and sha256(raw).hexdigest() == expected['sha256'],
                   'CP7_P20_RETAINED_GLOBAL_ARCHIVE_CHANGED')
    with ZipFile(path) as archive:
        owning.require(archive.namelist() == ['CP7_GLOBAL_INSTALLED_FINAL.json'] and archive.testzip() is None,
                       'CP7_P20_RETAINED_GLOBAL_ARCHIVE_MEMBERS_INVALID')
        proof = json.loads(archive.read('CP7_GLOBAL_INSTALLED_FINAL.json'))
    checks = proof['checks']
    owning.require(proof['contract'] == 'cp7.global.p20.retest.v1'
                   and proof['runner']['run_id'] == expected['run'] and proof['runner']['run_attempt'] == 1
                   and proof['successor'] == PARENT_APP
                   and proof['actual_Global_cases'] == len(expected['cases'])
                   and proof['passed_case_ids'] == expected['cases']
                   and all(proof['p20_cases'][name]['status'] == 'PASS' for name in expected['cases'])
                   and all(checks[name] is True for name in ('preflight','candidate','full_restore','transport','issuer_baseline','schema_export'))
                   and proof['independent_acceptance'] is proof['production_go'] is False,
                   'CP7_P20_RETAINED_GLOBAL_CASES_OR_RESTORE_CHANGED')
    return proof


def retained_original(scratch):
    read_original(Path(scratch) / 'p20-previous-run.zip', PREVIOUS)
    retest = read_original(Path(scratch) / 'p20-prior-retest.zip', PRIOR_RETEST)
    owning.require(retest['status'] == 'PASS' and all(retest['checks'].values())
                   and retest['retained_installed_P20'] == PREVIOUS,
                   'CP7_P20_RETAINED_RETEST_OR_RESTORE_CHANGED')
    return dict(product=PARENT_APP, runs=[PREVIOUS, PRIOR_RETEST])


def bind_provider(provider, runner, candidate):
    product = product_checkout(candidate)
    package, _ = owning.tracked_source(runner, ASSETS + '/retained_installer.py')
    for name in ('native.py', 'attendance.py', 'browser.mjs', 'legacy_native.py', 'legacy_browser.mjs'):
        owning.tracked_source(runner, ASSETS + '/' + name)
    for name in ('p20_a752_manifest.json', 'oracle.py', 'positive_close.py', 'planner.py', 'auth_identity.py',
                 'p20_resume.py'):
        owning.tracked_source(runner, 'qualification/audit/codex/' + name)
    # Resolve retained helper imports from the admitted graph. Only the P20
    # adapter and its two SQL files originate in the successor worktree.
    with owning.import_paths(Path(candidate) / 'scripts'):
        patch = owning.load('cp7_p20_exact_successor_overlay', product / 'scripts/cp7_finance_cash_access.py')
        return patch.bind_global(provider, package.read_text(encoding='utf-8'))


def auth_attempt(original):
    return type(original)(
        connect=original.connect, transport=original.transport, retain=original.retain,
        attempt=original.attempt, head=original.head,
        allowed_actors=(('OWNER', 'p20-owner'), ('ADMIN', 'p20-admin')),
        allowed_rpcs=(ACCESS,),
    )


def progress(label, status):
    print(f'GLOBAL_ORDINARY_PHASE {label} {status}', flush=True)


def bounded_failure(error):
    diagnostic = getattr(error, 'diag', None)
    primary = getattr(diagnostic, 'message_primary', None) or str(error)
    match = re.search(r'\b(?:CP[67]_|P20_|GLOBAL_|AUDITOR_|T3_|E_)[A-Z0-9_]{4,100}\b', primary)
    code = match[0] if match else 'CP7_P20_' + type(error).__name__.upper()
    locations = []
    trace = error.__traceback__
    while trace:
        path = Path(trace.tb_frame.f_code.co_filename)
        if path.name in ('p20_batch.py', 'native.py', 'attendance.py', 'positive_close.py', 'planner.py') or path.name.startswith('cp7_'):
            locations.append(f'{path.name}:{trace.tb_lineno}')
        trace = trace.tb_next
    result = dict(code=code, sqlstate=getattr(error, 'sqlstate', None), locations=locations[-6:])
    observed = getattr(error, 'audit_observed', None)
    if type(observed) is dict and set(observed) <= {
            'needed_pcs', 'capacity_pcs', 'available_fg_pcs', 'production_state',
            'fg', 'wip', 'need', 'capacity', 'selected'}:
        result['observed'] = observed
    blockers = getattr(error, 'audit_blocker_codes', None)
    if code == 'AUDITOR_P20_CLOSE_INITIAL_NOT_READY' and type(blockers) is list:
        result['blocker_codes'] = [item for item in blockers[:30]
                                   if type(item) is str and re.fullmatch(r'[A-Z][A-Z0-9_]{1,71}', item)]
    return result


@contextmanager
def case_evidence(journal, results, case_ids):
    started = p20_evidence.stamp()
    evidence = dict.fromkeys(case_ids, 'BOUNDARY_UNVERIFIED')
    for case_id in case_ids:
        progress(case_id, 'STARTED')
    try:
        yield evidence
    except Exception as error:
        failure = bounded_failure(error)
        for case_id in case_ids:
            result = results.setdefault(case_id, dict(status='INCOMPLETE', first_failure=failure))
            try:
                journal.case(case_id, result, 'BOUNDARY_UNVERIFIED', started, boundary_failure=failure)
            except Exception:
                error.add_note('P20_EVIDENCE_BOUNDARY_FAILURE_NOT_ARCHIVED')
            progress(case_id, 'FAILED')
        raise
    else:
        for case_id in case_ids:
            journal.case(case_id, results[case_id], evidence[case_id], started)
            progress(case_id, 'COMPLETED' if results[case_id]['status'] == 'PASS' else 'FAILED')


def exercise(conn, cur, state, report, *, namespace, lifecycle, candidate, output):
    """Execute the remaining Native case and evaluate the unchanged oracle."""
    product = Path(candidate).parent / 'p20-product'
    spool = Path(os.environ['P20_EVIDENCE_SPOOL'])
    journal = p20_evidence.Journal(spool)
    owning.require(p20_evidence.REMAINING_CASES == IDS, 'P20_EVIDENCE_EXACT_CASE_IDS_REQUIRED')
    retained = p20_resume.retained(spool.parent / 'cp7-live-parent')
    auth = namespace['_global_auth']
    auth.begin(conn, cur, namespace['package'].boundary.ADMIN, namespace['package'].boundary.PRIMARY_ADMIN,
               lambda cursor: lifecycle.verify(cursor, state), report)
    day = lifecycle.foundation.day
    owning.require(cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone() == (day,),
                   'AUDITOR_P20_EXACT_WIB_DAY_REQUIRED')
    conn.rollback()

    results = {}
    batch = report['p20_installed'] = dict(
        head=HEAD, tree=TREE, cases=results, retained_audit=p20_resume.provenance())
    # These two profile reads verify the disposable Auth lifecycle and cleanup.
    # The Planner case uses its own Native subject and no browser session.
    for role, label in sorted(auth.allowed_actors):
        profile = auth.login(role, label).rpc(ACCESS, {})
        owning.require(profile['status'] == 200 and profile['body']['allowed'] is True,
                       'AUDITOR_P20_CLEANUP_PROFILE_HTTP_REQUIRED')

    roots = [product / 'scripts']
    roots.extend(product / 'scripts/cp7_customer_credit' / name
                 for name in ('consumer', 'native', 'initial-settlement', 'reconciliation/native'))
    with owning.import_paths(*roots):
        native = importlib.import_module('.p20.native', __package__)
        from audit.codex import oracle, planner

        owning.require(PLANNER_PERMISSION == planner.PERMISSION,
                       'AUDITOR_P20_PLANNER_CASE_IDS_CHANGED')
        planner.verify_source()
        with case_evidence(journal, results, IDS) as evidence:
            try:
                native.prepare(cur)
                results[PLANNER_PERMISSION] = planner.permission(conn, cur, day)
                conn.commit()
                evidence[PLANNER_PERMISSION] = 'COMMITTED_RECOVERY_PENDING'
            except Exception as error:
                results[PLANNER_PERMISSION] = dict(status='INCOMPLETE', first_failure=bounded_failure(error))
                conn.rollback()
        try:
            batch['auditor_oracle'] = oracle.compare(retained | results)
        except Exception as error:
            batch['auditor_oracle'] = dict(status='INCOMPLETE', first_failure=bounded_failure(error))
        journal.oracle(batch['auditor_oracle'])
    return results


def complete(report):
    batch = report.get('p20_installed', {})
    cleanup = report.get('global_auth_cleanup', {})
    cases = batch.get('cases', {})
    return (batch.get('head') == HEAD and batch.get('tree') == TREE
            and set(cases) == set(IDS) and all(case.get('status') == 'PASS' for case in cases.values())
            and batch.get('retained_audit') == p20_resume.provenance()
            and batch.get('auditor_oracle', {}).get('status') == 'PASS'
            and report.get('global_auth_before_restore', {}).get('verified') is True
            and cleanup.get('status') == 'PASS' and cleanup.get('verified_actors') == 2
            and cleanup.get('restored_application_mappings_absent') is True
            and cleanup.get('installed_application_oid') != cleanup.get('restored_application_oid')
            and cleanup.get('application_rpc_responses', 0) >= 2 and not report.get('global_auth_cleanup_error'))

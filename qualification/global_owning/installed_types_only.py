"""Observe the committed disposable installation and its full restoration."""

from hashlib import sha256
import os
from types import FunctionType

from . import installed_types, p20_batch
from .lifecycle import INVERSE_FLAGS
from p21 import installed as p21_installed, mode as p21_mode


MODE_KEY = 'CP7_DISPOSABLE_INSTALL_OBSERVATION'
SCOPE = 'CURRENT_GLOBAL_INSTALLED_SCHEMA_AND_LEGACY_INVENTORY_ONLY'
RETAINED_WRITER = 'd3bea717a9167c4296efb20756cf16a5570c7966fffbbbcdfd69b9f6dcaa87de'

DIAGNOSTICS = """        case=report['committed'].setdefault(runner.CASE,dict(status='INCOMPLETE'))
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            _global_auth.begin(conn,cur,package.boundary.ADMIN,package.boundary.PRIMARY_ADMIN,
                               lambda cursor: _global_lifecycle.verify(cursor,STATE),report)
            measured(timings,'ISOLATED_DIAGNOSTICS',runner.exercise,conn,cur,database,package.boundary.ADMIN,case,STATE)
        assert case['used_guard_refused_before_DDL'] is True
        report['used_guard_refused_before_DDL']=True
"""
OBSERVATION = """        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            report['installed_public_types']=measured(timings,'INSTALLED_PUBLIC_TYPES',_observe_installed_types,conn,cur,STATE,report)
"""
P20_OBSERVATION = OBSERVATION + """        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            measured(timings,'P20_ACTUAL_GLOBAL_TESTS',_p20_run_installed_cases,conn,cur,STATE,report)
"""
P21_OBSERVATION = OBSERVATION + """        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            measured(timings,'P21_INSTALLED_CHECKS',_p21_installed_checks,conn,cur,STATE,report)
"""
AUTH_POST = """        if report.get('global_auth_before_restore',{}).get('verified') is True:
            try:
                _global_auth.after_restore(report)
            except Exception as error:
                report['global_auth_cleanup_error']=_global_auth_error(error)
"""
TERMINAL_AUTH = "and report.get('global_auth_cleanup',{}).get('status')=='PASS'and not report.get('global_auth_cleanup_error')and report.get('global_auth_cleanup',{}).get('verified_actors',0)>0 and report.get('global_auth_cleanup',{}).get('application_rpc_responses',0)>0 and (not _global_lifecycle.fixtures.CASE_IDS['browser'] or report['global_auth_before_restore'].get('browser',{}).get('process_tree_empty') is True) and report.get('focused_preuse_removal')and report['required_case_ids_pass']and report.get('used_guard_refused_before_DDL')"
TERMINAL_OBSERVATION = "and _installation_observation_complete(report)"
ORDINARY_COUNTS = "            report.update(_global_lifecycle.actual_counts(cases[runner.CASE]))\n"
OBSERVATION_COUNTS = """            report.update(actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
                          actual_browser_cases=0,actual_business_cases=0,real_Auth_HTTP_qualified=False)
"""
ROUTES = (
    (DIAGNOSTICS, OBSERVATION),
    ('                _global_auth.before_restore(report)\n', ''),
    (AUTH_POST, ''),
    (TERMINAL_AUTH, TERMINAL_OBSERVATION),
    (ORDINARY_COUNTS, OBSERVATION_COUNTS),
    ("            report['qualification_scope']='CURRENT_PARENT_SKU_GLOBAL_FIRST_SNAPSHOTS'\n",
     f"            report['qualification_scope']={SCOPE!r}\n"),
    ("manual_steps_scope='NATIVE_TRANSACTIONS_ON_ONE_DISPOSABLE_DATABASE'",
     "manual_steps_scope='SCHEMA_OBSERVATION_ON_ONE_DISPOSABLE_DATABASE'"),
)


def enabled():
    mode = os.environ.get(MODE_KEY, '')
    installed_types.require(mode in ('', SCOPE), 'CP7_INSTALLED_TYPES_EXACT_OBSERVATION_MODE_REQUIRED')
    installed_types.require(not p21_mode.enabled() or mode == SCOPE, 'CP7_P21_SCHEMA_OBSERVATION_REQUIRED')
    return mode == SCOPE


def p21_auth_complete(report):
    from p21.followup import ACTORS

    cleanup = report.get('global_auth_cleanup',{})
    return (cleanup.get('status')=='PASS' and cleanup.get('verified_actors')==len(ACTORS)
            and cleanup.get('application_rpc_responses',0)>=len(ACTORS)
            and len(cleanup.get('deletions',{}))==len(ACTORS)
            and not cleanup.get('failures')
            and cleanup.get('restored_application_mappings_absent') is True
            and cleanup.get('primary_application_mappings_absent') is True
            and report.get('global_auth_before_restore',{}).get('verified') is True
            and not report.get('global_auth_cleanup_error'))


def complete(report):
    inverse = report.get('focused_preuse_removal', {})
    return (report.get('installed_public_types', {}).get('status') == 'PASS'
            and all(inverse.get(key) is value for key, value in INVERSE_FLAGS.items())
            and report.get('committed') == {} and report.get('expected_case_count') == 0
            and ('used_guard_refused_before_DDL' not in report)
            and not any(name in report for name in
                 ('global_auth_application','global_auth_before_restore','global_auth_cleanup')))


def derive(source):
    installed_types.require(sha256(source.encode()).hexdigest() == RETAINED_WRITER,
                            'CP7_INSTALLED_TYPES_REVIEWED_COMPLETE_WRITER_REQUIRED')
    result = source
    for before, after in ROUTES:
        if p20_batch.enabled():
            if before in ('                _global_auth.before_restore(report)\n', AUTH_POST):
                continue
            if before == DIAGNOSTICS:
                after = P20_OBSERVATION
        installed_types.require(result.count(before) == 1, 'CP7_INSTALLED_TYPES_EXACT_OBSERVER_ROUTE_REQUIRED')
        result = result.replace(before, after, 1)
    compile(result, '<cp7 installed schema observer>', 'exec', dont_inherit=True)
    return result


def bind(owner, source, report_io, lifecycle, candidate):
    inner = owner.run_inner
    namespace = inner.__globals__
    filename = inner.__code__.co_filename
    installed_types.require(owner.run.__globals__ is namespace and inner.__code__ == report_io.function_code(source, filename, 'run_inner')
                            and namespace['IDS'] == (namespace['runner'].CASE,),
                            'CP7_INSTALLED_TYPES_EXACT_SOURCE_RUNNER_REQUIRED')
    derived = report_io.function_code(derive(source), filename, 'run_inner')

    def observe(conn, cur, state, report):
        foundation = report['preseal_foundation']
        installed_types.require(foundation.get('status') == 'VERIFIED_ON_EXISTING_INSTALLER_AFTER_COMMIT',
                                'CP7_INSTALLED_TYPES_COMMITTED_FOUNDATION_REQUIRED')
        print('GLOBAL_ORDINARY_PHASE INSTALLED_SCHEMA_OBSERVATION STARTED', flush=True)
        try:
            proof = installed_types.collect(conn, cur, package=namespace['package'], lifecycle=lifecycle,
                                            state=state, preseal_census=foundation['after_rows_and_sequences'],
                                            candidate=candidate, output=owner.output.parent)
        except Exception:
            print('GLOBAL_ORDINARY_PHASE INSTALLED_SCHEMA_OBSERVATION FAILED', flush=True)
            raise
        if p21_mode.enabled():
            from p21.checkpoints import record_case

            record_case('installed-schema', proof)
        print('GLOBAL_ORDINARY_PHASE INSTALLED_SCHEMA_OBSERVATION COMPLETED', flush=True)
        return proof

    namespace.update(IDS=(), _observe_installed_types=observe, _installation_observation_complete=complete)
    if p20_batch.enabled():
        namespace['_global_auth'] = p20_batch.auth_attempt(namespace['_global_auth'])
        namespace['_p20_run_installed_cases'] = lambda conn, cur, state, report: p20_batch.exercise(
            conn, cur, state, report, namespace=namespace, lifecycle=lifecycle,
            candidate=candidate, output=owner.output.parent)

        def complete_p20(report):
            inverse = report.get('focused_preuse_removal', {})
            return (report.get('installed_public_types', {}).get('status') == 'PASS'
                    and all(inverse.get(key) is value for key, value in INVERSE_FLAGS.items())
                    and p20_batch.complete(report))

        namespace['_installation_observation_complete'] = complete_p20
    elif p21_mode.enabled():
        def installed_candidate(report):
            receipt=report.get('installed_public_types',{})
            inverse=report.get('focused_preuse_removal',{})
            return (receipt.get('status')=='COMMITTED' and receipt.get('product')=='ffda5cfceb7ebc196656baa650dffd18dd425047'
                    and len(receipt.get('catalogue_groups',{}))==25 and bool(receipt.get('checkpoint',{}).get('sha256'))
                    and all(inverse.get(key) is value for key,value in INVERSE_FLAGS.items())
                    and report.get('committed')=={} and report.get('expected_case_count')==0)
        namespace['_installation_observation_complete'] = installed_candidate
    namespace['run_inner'] = FunctionType(derived, namespace, 'run_inner', inner.__defaults__)

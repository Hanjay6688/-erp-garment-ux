"""Reversible Auth hooks around the retained Global writer's full restore."""
from hashlib import sha256

from auth_adapter import error_code, require

GLOBAL_WRITER_SHA = '224406a2dba2ec0a3c13edb1a3a328599e315abaf256ea2d80f4df63474110c6'
DONOR_BEGIN = """        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            measured(timings,'ISOLATED_DIAGNOSTICS',runner.exercise,conn,cur,database,package.boundary.ADMIN,case,STATE)"""
AUTH_BEGIN = """        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            _global_auth.begin(conn,cur,package.boundary.ADMIN,package.boundary.PRIMARY_ADMIN,
                               lambda cursor: _global_lifecycle.verify(cursor,STATE),report)
            measured(timings,'ISOLATED_DIAGNOSTICS',runner.exercise,conn,cur,database,package.boundary.ADMIN,case,STATE)"""
DONOR_RESTORE = """        if before is not None and pre_dumped:
            try:
                if report['committed']:"""
AUTH_RESTORE = """        if before is not None and pre_dumped:
            try:
                _global_auth.before_restore(report)
                if report['committed']:"""
DONOR_POST = """        drill.docker('rm','-f',PRE_DUMP,check=False)
        cases=report['committed']"""
AUTH_POST = """        if report.get('global_auth_before_restore',{}).get('verified') is True:
            try:
                _global_auth.after_restore(report)
            except Exception as error:
                report['global_auth_cleanup_error']=_global_auth_error(error)
        drill.docker('rm','-f',PRE_DUMP,check=False)
        cases=report['committed']"""
DONOR_PASS = "and report.get('baseline_full25_portable_catalogue_equal')and report.get('focused_preuse_removal')"
AUTH_PASS = ("and report.get('baseline_full25_portable_catalogue_equal')"
             "and report.get('global_auth_cleanup',{}).get('status')=='PASS'"
             "and not report.get('global_auth_cleanup_error')"
             "and report.get('global_auth_cleanup',{}).get('verified_actors',0)>0 "
             "and report.get('global_auth_cleanup',{}).get('application_rpc_responses',0)>0 "
             "and (not _global_lifecycle.fixtures.CASE_IDS['browser'] "
             "or report['global_auth_before_restore'].get('browser',{}).get('process_tree_empty') is True) "
             "and report.get('focused_preuse_removal')")
ROUTES = (
    ('after_install_commit_before_fixtures', DONOR_BEGIN, AUTH_BEGIN),
    ('reap_attempt_transport_before_original_restore', DONOR_RESTORE, AUTH_RESTORE),
    ('final_issuer_cleanup_after_original_full_restore', DONOR_POST, AUTH_POST),
    ('auth_cleanup_required_before_writer_pass', DONOR_PASS, AUTH_PASS),
)


def derive(source):
    require(sha256(source.encode()).hexdigest() == GLOBAL_WRITER_SHA, 'EXACT_RETAINED_GLOBAL_WRITER_REQUIRED')
    revised = source
    for label, before, after in ROUTES:
        require(revised.count(before) == 1 and after not in revised, 'EXACT_RESTORE_ROUTE_' + label.upper())
        revised = revised.replace(before, after, 1)
    original = revised
    for label, before, after in reversed(ROUTES):
        require(original.count(after) == 1, 'EXACT_INVERSE_ROUTE_' + label.upper())
        original = original.replace(after, before, 1)
    require(original == source, 'COMPLETE_RETAINED_GLOBAL_WRITER_NOT_RECOVERED')
    compile(revised, '<Global owning Auth writer>', 'exec', dont_inherit=True)
    return revised, dict(retained_sha256=GLOBAL_WRITER_SHA, derived_sha256=sha256(revised.encode()).hexdigest(),
                         routes=[label for label, _, _ in ROUTES], exact_inverse=True,
                         outer_T3_changed=False, actual_Auth_HTTP_cases=0, runtime_admission=False)


def bind(owner, original_routes, engine, lifecycle, runner, report_io, sku_source, global_source, candidate, auth):
    # The existing owner still checks the two live SKU function identities.
    owner.require_gates()
    revised, _ = derive(global_source)
    result = original_routes.bind(engine, lifecycle, runner, report_io, sku_source, revised, candidate)
    namespace = result.run_inner.__globals__
    require(result.run.__globals__ is namespace and '_global_auth' not in namespace,
            'EXACT_PRIVATE_OWNING_AUTH_NAMESPACE_REQUIRED')
    namespace.update(_global_auth=auth, _global_auth_error=error_code)
    return result

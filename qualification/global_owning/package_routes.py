"""Derive the Global writer from the original complete SKU package."""

from hashlib import sha256
from types import FunctionType, SimpleNamespace


SKU_ENGINE_SHA = '4541b583800ce291faec1f2e68ebcaef3b7e75c3de6d8733a673d85b2841b6d2'
SCOPE = 'CURRENT_PARENT_SKU_GLOBAL_FIRST_SNAPSHOTS'
OLD_INSTALL = """                prior=measured(timings,'ACTUAL_CURRENT_MANDOR_MOVING_AND_MONEY_PARENT_INSTALL',_sku_install_parent,cur)
                STATE=measured(timings,'FIRST_FINANCE_DELTA',_sku_install_delta,cur,prior)
                report['focused_preuse_removal']=measured(timings,'FINANCE_DELTA_PREUSE_INVERSE',_sku_rollback_delta_preuse,cur,STATE)
                assert report['focused_preuse_removal']['used_guard_before_DDL'] is True
                STATE=measured(timings,'SECOND_FINANCE_DELTA',_sku_install_delta,cur,prior)"""
OLD_VERIFY = """            control.STATE=dict(installed_catalog=STATE['after'])
            report['complete_installed_verification']=_sku_verify_installed(cur,STATE)"""
ROUTES = (
    ('complete_SKU_then_Global_lifecycle', OLD_INSTALL,
     '                STATE=_global_lifecycle.install_cycle(cur,timings,report)'),
    ('Global_child_verification', OLD_VERIFY,
     "            report['complete_installed_verification']=_global_lifecycle.verify(cur,STATE)"),
    ('before_restore_dispatch_groups',
     '            baseline_data=predecessor.catalog._data(cur)\n',
     '            baseline_data=predecessor.catalog._data(cur)\n'
     '            baseline_dispatch=_global_lifecycle.dispatch_catalogue(cur)\n'),
    ('after_restore_dispatch_groups',
     "                    report['baseline_full22_all_rows_all_sequences_equal']=True\n",
     "                    report['baseline_full22_all_rows_all_sequences_equal']=True\n"
     "                    assert _global_lifecycle.dispatch_catalogue(cur)==baseline_dispatch\n"
     "                    report['baseline_full25_portable_catalogue_equal']=True\n"),
    ('full25_completion_gate',
     "and report.get('baseline_full22_all_rows_all_sequences_equal')and report.get('focused_preuse_removal')",
     "and report.get('baseline_full25_portable_catalogue_equal')and report.get('focused_preuse_removal')"),
    ('qualification_scope', "'CURRENT_PARENT_SKU_MONEY_AUTOMATIC_NATIVE25_BROWSER2_ONLY'", repr(SCOPE)),
    ('actual_runtime_counts',
     """            report['actual_two_session_races']=0
            report['actual_Native_cases']=cases[runner.CASE]['actual_Native_cases']
            report['actual_Auth_HTTP_cases']=0
            report['actual_browser_cases']=cases[runner.CASE]['actual_browser_cases']
            report['actual_business_cases']=cases[runner.CASE]['actual_Native_cases']+cases[runner.CASE]['actual_browser_cases']
            report['real_Auth_browser_claim']=cases[runner.CASE]['real_Auth_browser_claim']
            report['real_Auth_HTTP_qualified']=False""",
     """            report.update(_global_lifecycle.actual_counts(cases[runner.CASE]))"""),
    ('reviewed_Global_advisor_capture',
     "report['current_private_info_authority']=current_advisor.capture(cur)",
     "report['current_private_info_authority']=_global_lifecycle.capture_advisors(cur,STATE)"),
    ('reviewed_Global_advisor_gate',
     "report['advisor_disposition']=current_advisor.review(report['advisor_delta'],report['verified_predecessor_info_manifest'],report['current_private_info_authority'],core.advisor_disposition)",
     "report['advisor_disposition']=_global_lifecycle.review_advisors(report['advisor_delta'],report['verified_predecessor_info_manifest'],report['current_private_info_authority'],core.advisor_disposition)"),
)


def require(value, error):
    if not value:
        raise ValueError(error)


def derive(source):
    require(sha256(source.encode()).hexdigest() == SKU_ENGINE_SHA, 'GLOBAL_CALLER_EXACT_FULL_SKU_ENGINE_REQUIRED')
    result = source
    for label, before, after in ROUTES:
        require(result.count(before) == 1 and after not in result, 'GLOBAL_CALLER_EXACT_ROUTE_REQUIRED:' + label)
        result = result.replace(before, after, 1)
    restored = result
    for label, before, after in reversed(ROUTES):
        require(restored.count(after) == 1, 'GLOBAL_CALLER_EXACT_INVERSE_ROUTE_REQUIRED:' + label)
        restored = restored.replace(after, before, 1)
    require(restored == source, 'GLOBAL_CALLER_COMPLETE_SKU_ENGINE_SOURCE_NOT_RECOVERED')
    compile(result, '<prepared Global owning writer>', 'exec', dont_inherit=True)
    return result, dict(parent_sha256=SKU_ENGINE_SHA, derived_sha256=sha256(result.encode()).hexdigest(),
                        counted_routes=[label for label, _, _ in ROUTES], complete_source_inverse=True)


def bind(engine, lifecycle, runner, report_io, source, revised, candidate, *, source_identity=None):
    """Use the live parent's imported bindings and only replace its writer body."""
    namespace = dict(vars(engine), _global_lifecycle=lifecycle, runner=runner, IDS=(runner.CASE,),
                     STATE=None, STREAM_CONTEXT=None, REPO=candidate, LABEL='CP7_GLOBAL_FIRST_SNAPSHOTS',
                     PRE_DUMP='/tmp/current_global_first_snapshots_pre.dump',
                     OUT=candidate / 'cp6-proof/t3/CP7_GLOBAL_FIRST_SNAPSHOTS.json')
    for name, replacement in (('run', source), ('run_inner', revised)):
        original = getattr(engine, name)
        filename = original.__code__.co_filename
        require(original.__globals__ is engine.__dict__ and original.__closure__ is None
                and original.__code__ == report_io.function_code(source, filename, name),
                'GLOBAL_CALLER_EXACT_LIVE_SKU_FUNCTION_REQUIRED:' + name)
        code = report_io.function_code(replacement, filename, name)
        namespace[name] = FunctionType(code, namespace, name, original.__defaults__)

    if source_identity is not None:
        def admitted():
            return dict(engine.admitted(), global_owning_source=source_identity)

        namespace['admitted'] = admitted

    return SimpleNamespace(run=namespace['run'], run_inner=namespace['run_inner'], output=namespace['OUT'])

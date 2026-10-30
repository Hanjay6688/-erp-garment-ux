"""Exact complete-engine/runner/gate successors; no database operation here."""
from hashlib import sha256
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
NS = 'scripts/current-de-sku-global-census-qualification'
PARENT = 'scripts/current-de-sku-parent-catalogue-qualification'
HELPER = 'scripts/current-global-actual-writer-census-qualification'
OLD = 'scripts/current-vendor-receivable-qualification/probe.py'
LABEL = 'CP7_D1_E_SKU_GLOBAL_CENSUS'
CASE = 'D1_E_SKU_GLOBAL_WRITER_CENSUS_SOURCE_ONLY'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def replace_exact(text, changes, kind):
    original = text
    for before, after in changes:
        if text.count(before) != 1 or after in text: raise ValueError('GLOBAL_CENSUS_COUNTED_' + kind + '_ANCHOR_CHANGED')
        text = text.replace(before, after, 1)
    reverse = text
    for before, after in reversed(changes):
        if reverse.count(after) != 1: raise ValueError('GLOBAL_CENSUS_COUNTED_REVERSE_ANCHOR_CHANGED')
        reverse = reverse.replace(after, before, 1)
    if reverse != original: raise ValueError('GLOBAL_CENSUS_DERIVATION_NOT_BYTE_REVERSIBLE')
    compile(text, '<global-census-' + kind + '>', 'exec')
    return text, dict(kind=kind, before_sha256=sha256(original.encode()).hexdigest(),
                     after_sha256=sha256(text.encode()).hexdigest(), counted_changes=len(changes), byte_reversible=True)


def runner():
    helper = load('global_census_pinned_runner_patch', ROOT / HELPER / 'runner_patch.py')
    text, prior = helper.derive('runner')
    text, proof = replace_exact(text, (
        ("    census_integration=load('global_actual_census_integration',ROOT/'" + HELPER + "/integration.py')",
         "    census_integration=load('global_actual_census_integration_loader',ROOT/'" + NS + "/loader.py').integration()"),
        ("CASE='D1_E_SKU_ACTUAL_PARENT_CATALOGUE_RAW_ACL_SOURCE_ONLY'", "CASE='" + CASE + "'"),
        ("classification='ACTUAL_D1_E_SKU_INSTALL_PREUSE_CATALOGUE_ONLY'", "classification='ACTUAL_D1_E_SKU_GLOBAL_WRITER_METADATA_ONLY'"),
        ("    report['global_writer_supplemental_reference']=supplemental_reference",
         "    report['global_writer_supplemental_reference']=supplemental_reference\n    report['read_before']=before"),
    ), 'runner')
    return text, dict(inherited=prior, successor=proof, runtime_entry=None, actual_Native_credit=0)


def integration():
    # PostgreSQL serializes SET search_path='' as a quoted empty identifier.
    # set_config preserves the empty search-path text required by capture ABI.
    text = (ROOT / HELPER / 'integration.py').read_text()
    return replace_exact(text, (("    cur.execute(\"SET LOCAL search_path = ''\")",
        "    cur.execute(\"SELECT pg_catalog.set_config('search_path','',true)\")"),), 'integration')


def gate():
    helper = load('global_census_pinned_gate_patch', ROOT / HELPER / 'runner_patch.py')
    text, prior = helper.derive('gate')
    text, proof = replace_exact(text, (
        ("def checked(report,package,head,original_directory=None):",
         "def checked(report,package,head,original_directory=None):\n"
         "    require(report.get('production_go') is False and report.get('independent_acceptance') is False, 'GLOBAL_CENSUS_REPORT_CLOSED_FLAGS_REQUIRED')\n"
         "    require(type(report.get('actual_catalogue_qualification_groups')) is int and report['actual_catalogue_qualification_groups'] == 1, 'GLOBAL_CENSUS_EXACT_TYPED_METADATA_GROUP_REQUIRED')\n"
         "    require(package.get('production_go') is False and package.get('release_evidence') is False, 'GLOBAL_CENSUS_PACKAGE_CLOSED_FLAGS_REQUIRED')\n"
         "    for key in ('auth_users_before','auth_users_after'):\n"
         "        require(type(package.get(key)) is int and package[key] == 0, 'GLOBAL_CENSUS_TYPED_AUTH_ZERO_REQUIRED')\n"
         "    current_case = report.get('committed', {}).get(CASE, {})\n"
         "    for key in ('production_go','independent_acceptance','used_guard_business_witness_executed','global_bridge_installed','S03_S05_installed'):\n"
         "        require(current_case.get(key) is False, 'GLOBAL_CENSUS_CASE_CLOSED_FLAG_REQUIRED:' + key)\n"
         "    for key in ('actual_business_cases','actual_Native_cases','actual_Auth_HTTP_cases','actual_browser_cases'):\n"
         "        require(type(current_case.get(key)) is int and current_case[key] == 0, 'GLOBAL_CENSUS_CASE_TYPED_ZERO_REQUIRED:' + key)"),
        ("CASE='D1_E_SKU_ACTUAL_PARENT_CATALOGUE_RAW_ACL_SOURCE_ONLY'", "CASE='" + CASE + "'"),
        ("report.get('label')=='CP7_D1_E_SKU_PARENT_CATALOGUE'", "report.get('label')=='" + LABEL + "'"),
        ("'CP7_D1_E_SKU_PARENT_CATALOGUE.json'", "'" + LABEL + ".json'"),
        ("status='ACTUAL_D1_E_SKU_PARENT_CATALOGUE_PREUSE_AND_ALL5_QUALIFIED'",
         "status='ACTUAL_D1_E_SKU_GLOBAL_CENSUS_METADATA_PREUSE_AND_ALL5_QUALIFIED'"),
    ), 'gate')
    return text, dict(inherited=prior, successor=proof, runtime_entry=None, actual_Native_credit=0)


def engine():
    parent = load('global_census_exact_parent_engine_deriver', ROOT / PARENT / 'derive.py')
    text, prior = parent.derive()
    old_runner = "_spec=importlib.util.spec_from_file_location('full_current_finance_model_cron',REPO/'" + PARENT + "/runner.py')\nrunner=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(runner)"
    new_runner = "_spec=importlib.util.spec_from_file_location('global_census_admitted_runner_loader',REPO/'" + NS + "/loader.py')\n_census_loader=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_census_loader)\nrunner=_census_loader.runner()"
    text, proof = replace_exact(text, (
        (old_runner, new_runner),
        ("REPO/'" + PARENT + "/admission.py'", "REPO/'" + NS + "/admission.py'"),
        ("LABEL='CP7_D1_E_SKU_PARENT_CATALOGUE'", "LABEL='" + LABEL + "'"),
        ("PRE_DUMP='/tmp/current_de_sku_parent_catalogue_pre.dump'", "PRE_DUMP='/tmp/current_de_sku_global_census_pre.dump'"),
    ), 'engine')
    return text, dict(inherited=prior, successor=proof,
        install_preuse_inverse_reinstall_commit_outer_restore_all5_preserved=True,
        actual_business_cases=0, runtime_entry=None, actual_Native_credit=0)

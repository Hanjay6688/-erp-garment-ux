"""Explicit catalogue-only successor of the complete retained package engine."""
from pathlib import Path
from hashlib import sha256

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
NS='scripts/current-de-sku-parent-catalogue-qualification'
OLD='scripts/current-vendor-receivable-qualification/probe.py'
REPLACEMENTS=(
 ("from cp7_vendor_receivable import composition as product",
  "_stage_spec=importlib.util.spec_from_file_location('de_sku_catalogue_stage',REPO/'"+NS+"/stage.py')\nproduct=importlib.util.module_from_spec(_stage_spec);_stage_spec.loader.exec_module(product)"),
 ("HERE/'runner.py'","REPO/'"+NS+"/runner.py'"),
 ("HERE/'admission.py'","REPO/'"+NS+"/admission.py'"),
 ("LABEL='CP7_VENDOR_RECEIVABLE_COMBINED11'","LABEL='CP7_D1_E_SKU_PARENT_CATALOGUE'"),
 ("PRE_DUMP='/tmp/current_vendor_receivable_pre.dump'","PRE_DUMP='/tmp/current_de_sku_parent_catalogue_pre.dump'"),
 ("prior=measured(timings,'SINGLE_FULL_READONLY_PARENT_INSTALL',readonly.install,cur)\n                prior=measured(timings,'EXACT_BACKEND3194_PARENT_INSTALL',product.parent().install_delta,cur,prior)",
  "prior=measured(timings,'EXACT_VENDOR_PARENT_INSTALL',product.parent().install,cur)"),
 ("assert case['used_guard_refused_before_DDL'] is True\n        report['used_guard_refused_before_DDL']=True",
  "assert case['preuse_catalogue_qualified'] is True\n        report['preuse_catalogue_qualified']=True\n        report['used_guard_business_witness_executed']=False"),
 ("and report.get('used_guard_refused_before_DDL'):","and report.get('preuse_catalogue_qualified'):"),
 ("report['actual_two_session_races']=3","report['actual_two_session_races']=0"),
 ("report['actual_Native_cases']=7","report['actual_Native_cases']=0"),
 ("report['actual_Auth_HTTP_cases']=1","report['actual_Auth_HTTP_cases']=0"),
 ("report['actual_business_cases']=11","report['actual_business_cases']=0\n            report['actual_catalogue_qualification_groups']=1\n            report['full_final_composite_qualified']=False"),
 ("report['real_Auth_HTTP_qualified']=True","report['real_Auth_HTTP_qualified']=False"),
)


def derive(raw=None):
    raw=(ROOT/OLD).read_bytes()if raw is None else raw
    source=raw.decode();text=source
    for before,after in REPLACEMENTS:
        if text.count(before)!=1 or after in text:raise ValueError('DE_SKU_CATALOGUE_EXACT_ENGINE_ANCHOR_REQUIRED:'+before)
        text=text.replace(before,after,1)
    reverse=text
    for before,after in reversed(REPLACEMENTS):
        if reverse.count(after)!=1:raise ValueError('DE_SKU_CATALOGUE_EXACT_ENGINE_REVERSAL_REQUIRED')
        reverse=reverse.replace(after,before,1)
    if reverse.encode()!=raw:raise ValueError('DE_SKU_CATALOGUE_ENGINE_NOT_BYTE_REVERSIBLE')
    compile(text,str(ROOT/OLD),'exec')
    return text,dict(original_path=OLD,original_sha256=sha256(raw).hexdigest(),
        derived_sha256=sha256(text.encode()).hexdigest(),counted_changes=len(REPLACEMENTS),
        original_engine_bytes_preserved=True,all_install_preuse_reinstall_backup_roles_CP6_advisor_Auth_package_checks_retained=True,
        original_business_case_requirement_replaced_by_explicit_catalogue_only_group=True,
        no_used_business_witness_claim=True,actual_Native_cases=0)

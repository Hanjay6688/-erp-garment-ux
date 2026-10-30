"""Complete retained vendor engine: its five substitutions plus one report block."""
from hashlib import sha256
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[2]
path=ROOT/'scripts/current-sku-combined-followup-qualification/derive.py'
spec=importlib.util.spec_from_file_location('sku27_retained_five_engine_changes',path)
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
BEFORE="""report['actual_business_cases']=23
            report['base_Native_cases']=7
            report['cost_Native_cases']=3
            report['actual_Native_cases']=10
            report['actual_Native_session_permission_waits']=6
            report['group_recovery_supported']=False"""
AFTER="""report['actual_business_cases']=27
            report['base_Native_cases']=7
            report['cost_Native_cases']=5
            report['actual_Native_cases']=12
            report['actual_Native_session_permission_waits']=7
            report['actual_Native_nonblocking_busy_cases']=1
            report['group_recovery_supported']=False"""

def derive(raw):
    prior,proof=old.derive(raw)
    if prior.count(BEFORE)!=1:raise ValueError('SKU27_COMPLETE_ENGINE_EXACT_REPORT_ANCHOR_REQUIRED')
    text=prior.replace(BEFORE,AFTER,1)
    assert text.replace(AFTER,BEFORE,1)==prior
    return text,dict(original_sha256=sha256(raw).hexdigest(),derived_sha256=sha256(text.encode()).hexdigest(),
      counted_changes=6,retained_five_changes=proof,additional_report_block_changes=1,
      all_install_preuse_reinstall_used_backup_roles_CP6_advisors_Auth_and_five_gates_retained=True)

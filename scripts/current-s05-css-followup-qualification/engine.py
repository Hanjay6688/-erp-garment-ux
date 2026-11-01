"""Keep the complete owning package; change only the fresh-case report counts."""
from pathlib import Path
from hashlib import sha256
import importlib.util

PARENT=Path(__file__).resolve().parent.parent/'current-s03-sku-s05-composite-qualification'
COUNTS="""report['actual_two_session_races']=0
            report['actual_Native_cases']=0
            report['actual_Auth_HTTP_cases']=0
            report['actual_browser_cases']=2
            report['actual_business_cases']=2
            report['retained_Native_cases']=31
            report['retained_S03_browser_cases']=4
            report['retained_cases_are_not_fresh']=True
            report['real_Auth_HTTP_qualified']=False
            report['real_Auth_browser_claim']=True"""

def derive(raw):
    spec=importlib.util.spec_from_file_location('focused_unchanged_complete_parent_engine',PARENT/'engine.py')
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    original,prior=parent.derive(raw)
    if original.count(parent.COUNTS_AFTER)!=1 or COUNTS in original:raise ValueError('FOCUSED_EXACT_FRESH_COUNTS_ANCHOR_REQUIRED')
    text=original.replace(parent.COUNTS_AFTER,COUNTS,1)
    if text.count(COUNTS)!=1 or text.replace(COUNTS,parent.COUNTS_AFTER,1)!=original:
        raise ValueError('FOCUSED_EXACT_COMPLETE_ENGINE_INVERSE_REQUIRED')
    return text,dict(parent_complete_engine=prior,original_sha256=sha256(raw).hexdigest(),
        derived_sha256=sha256(text.encode()).hexdigest(),additional_counted_changes=1,
        complete_original_recovered=True,install_preuse_reinstall_restore_backup_roles_all22_ALLdata_sequences_advisors_CP6_Auth_checks_retained=True)

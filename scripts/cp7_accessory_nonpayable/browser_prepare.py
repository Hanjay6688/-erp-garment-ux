"""Native browser prerequisite; no caller connection or commit is owned here."""
from pathlib import Path
import json,sys

IDS=(
    'NONPAYABLE_BROWSER_DESKTOP_POSTED_USE_REFUSAL_LOST_REPLY_TWO_TABS',
    'NONPAYABLE_BROWSER_MOBILE390_CANCEL_LATE_SAVE_OWNER_AND_ADMIN_READ_ONLY',
)

def source_controls():
    from . import native_fixture,access_cases,ui_derivation
    return dict(status='NONPAYABLE_NORMAL_APP_BROWSER2_SOURCE_PREPARED_NOT_EXECUTED',browser_case_ids=list(IDS),
        Native_originals=native_fixture.source_controls(),access_originals=access_cases.source_controls(),
        UI_source=ui_derivation.source_manifest(),actual_SQL_executed=0,actual_Native_cases=0,
        actual_Auth_HTTP_cases=0,actual_browser_cases=0,production_go=False,independent_acceptance=False)

def prepare(cur,today,state):
    from . import native_fixture
    modules=native_fixture.admitted_modules(cur,state)  # Exact rollback DB and accepted parent.
    before=modules.bc.findings(cur)
    f=native_fixture.prepare(cur,today,modules);native_fixture.post_good(cur,modules,f)
    actual=native_fixture.observe(cur,modules,f);native_fixture.require_economics(actual,f,nonpayable=True,hpp='20')
    after=modules.bc.findings(cur)
    if modules.bc.new_findings(before,after):raise ValueError('NONPAYABLE_BROWSER_PREREQUISITE_FINANCIAL_INTEGRITY_REQUIRED')
    return dict(status='ACTUAL_NATIVE_NONPAYABLE_BROWSER_PREREQUISITE_PREPARED',fixture=f,
        actual_good=actual,physical_GOOD_day=str(f['good_day']),explicit_review_day=str(today),
        expected_positive_HPP='20',expected_reimbursement='0',expected_new_entitlements=0,
        findings_before=before,findings_after=after,Native_case_credit=0,screen_creation_claim=False)

if __name__=='__main__':
    if sys.argv[1:]not in(['--prepare'],['--admit']):raise SystemExit('SOURCE_PREPARATION_OR_ACTUAL_PARENT_ADMISSION_ONLY')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from cp7_accessory_nonpayable import admission
    from cp7_accessory_nonpayable.browser_prepare import source_controls as checked
    if sys.argv[1:] == ['--admit']:
        receipt=admission.parent_receipt()
        print(json.dumps(dict(status='ACTUAL_FREE3_PARENT_ADMITTED_BEFORE_BROWSER',head=receipt['head'],tree=receipt['tree'],source=checked()),sort_keys=True))
    else:print(json.dumps(checked(),sort_keys=True))

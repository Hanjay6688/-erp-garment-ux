"""Two exact reversible routes in the original whole package engine."""
from hashlib import sha256
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
ORIGINAL='scripts/current-vendor-receivable-qualification/probe.py'
ORIGINAL_BASE='0da4d79a4f7201ef053d6de1eb155d990b4bfa4d'
PIN=(12667, 'c420d894f8d5f16bddefeae73addb621507170f372a28e7d6e33d88c7eeb0be9')
INSTALL_BEFORE="prior=measured(timings,'SINGLE_FULL_READONLY_PARENT_INSTALL',readonly.install,cur)\n                prior=measured(timings,'EXACT_BACKEND3194_PARENT_INSTALL',product.parent().install_delta,cur,prior)"
INSTALL_AFTER="prior=measured(timings,'ACTUAL_QUALIFIED_FREE3_PARENT_INSTALL',product.parent().install,cur)"
COUNTS_BEFORE="""report['actual_two_session_races']=3
            report['actual_Native_cases']=7
            report['actual_Auth_HTTP_cases']=1
            report['actual_browser_cases']=0
            report['actual_business_cases']=11
            report['real_Auth_HTTP_qualified']=True"""
COUNTS_AFTER="""report['actual_two_session_races']=2
            report['actual_Native_cases']=9
            report['actual_Auth_HTTP_cases']=2
            report['actual_browser_cases']=2
            report['actual_business_cases']=15
            report['retained_FREE3_fresh_case_credit']=0
            report['real_Auth_browser_claim']=True
            report['real_Auth_HTTP_qualified']=True"""

def derive(raw):
    if PIN is None or (len(raw),sha256(raw).hexdigest())!=PIN:
        raise ValueError('NONPAYABLE_EXACT_ORIGINAL_WHOLE_PACKAGE_ENGINE_REQUIRED')
    if raw!=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',ORIGINAL_BASE+':'+ORIGINAL]):
        raise ValueError('NONPAYABLE_WHOLE_PACKAGE_ORIGINAL_PUBLIC_BYTES_REQUIRED')
    text=raw.decode();pairs=((INSTALL_BEFORE,INSTALL_AFTER),(COUNTS_BEFORE,COUNTS_AFTER))
    for before,after in pairs:
        if text.count(before)!=1 or after in text:raise ValueError('NONPAYABLE_EXACT_WHOLE_ENGINE_ROUTE_REQUIRED')
        text=text.replace(before,after,1)
    recovered=text
    for before,after in reversed(pairs):
        if recovered.count(after)!=1:raise ValueError('NONPAYABLE_WHOLE_ENGINE_REVERSE_REQUIRED')
        recovered=recovered.replace(after,before,1)
    if recovered.encode()!=raw:raise ValueError('NONPAYABLE_WHOLE_ENGINE_ORIGINAL_NOT_RECOVERED')
    compile(text,'afui_exact_whole_package_engine','exec')
    return text,dict(original_bytes=PIN[0],original_sha256=PIN[1],derived_sha256=sha256(text.encode()).hexdigest(),
        exact_reversible_changes=2,complete_original_engine_recovered=True,
        install_preuse_reinstall_used_backup_roles_all22_ALL_rows_ALL_sequences_CP6_advisors_Auth_package_checks_retained=True,
        actual_SQL_executed=0,actual_case_credit=0,production_go=False,independent_acceptance=False)

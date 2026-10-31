"""Whole disposable package engine; two reversible route/count changes only."""
from hashlib import sha256

INSTALL_BEFORE="prior=measured(timings,'SINGLE_FULL_READONLY_PARENT_INSTALL',readonly.install,cur)\n                prior=measured(timings,'EXACT_BACKEND3194_PARENT_INSTALL',product.parent().install_delta,cur,prior)"
INSTALL_AFTER="prior=measured(timings,'ACTUAL_QUALIFIED_COMPLETE_PERMANENT_PARENT_INSTALL',product.parent().install,cur)"
COUNTS_BEFORE="""report['actual_two_session_races']=3
            report['actual_Native_cases']=7
            report['actual_Auth_HTTP_cases']=1
            report['actual_browser_cases']=0
            report['actual_business_cases']=11
            report['real_Auth_HTTP_qualified']=True"""
COUNTS_AFTER="""report['actual_two_session_races']=0
            report['actual_Native_cases']=30
            report['actual_Auth_HTTP_cases']=0
            report['actual_browser_cases']=0
            report['actual_business_cases']=30
            report['retained_permanent6_fresh_case_credit']=0
            report['real_Auth_HTTP_qualified']=False"""


def derive(raw):
    text=raw.decode();pairs=((INSTALL_BEFORE,INSTALL_AFTER),(COUNTS_BEFORE,COUNTS_AFTER))
    for before,after in pairs:
        if text.count(before)!=1 or after in text:raise ValueError('COMPLETE_DE_EXACT_ENGINE_ANCHOR_REQUIRED')
        text=text.replace(before,after,1)
    original=text
    for before,after in reversed(pairs):
        if original.count(after)!=1:raise ValueError('COMPLETE_DE_EXACT_ENGINE_REVERSE_ANCHOR_REQUIRED')
        original=original.replace(after,before,1)
    if original.encode()!=raw:raise ValueError('COMPLETE_DE_WHOLE_ORIGINAL_ENGINE_NOT_RECOVERED')
    compile(text,'complete-DE-derived-owning-package-engine','exec')
    return text,dict(original_sha256=sha256(raw).hexdigest(),derived_sha256=sha256(text.encode()).hexdigest(),
        counted_changes=2,complete_original_recovered=True,
        install_preuse_reinstall_used_backup_roles_all22_ALL_rows_sequences_CP6_advisors_Auth_package_checks_retained=True,
        actual_Native_cases=0,production_go=False,independent_acceptance=False)

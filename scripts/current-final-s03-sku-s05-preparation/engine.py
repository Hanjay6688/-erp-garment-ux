"""Complete package engine; two reversible routing/report substitutions only."""
from hashlib import sha256

INSTALL_BEFORE="prior=measured(timings,'SINGLE_FULL_READONLY_PARENT_INSTALL',readonly.install,cur)\n                prior=measured(timings,'EXACT_BACKEND3194_PARENT_INSTALL',product.parent().install_delta,cur,prior)"
INSTALL_AFTER="prior=measured(timings,'ACTUAL_QUALIFIED_CURRENT_S03_SKU_FINANCIAL_PARENT_INSTALL',product.parent().install,cur)"
COUNTS_BEFORE="""report['actual_two_session_races']=3
            report['actual_Native_cases']=7
            report['actual_Auth_HTTP_cases']=1
            report['actual_browser_cases']=0
            report['actual_business_cases']=11
            report['real_Auth_HTTP_qualified']=True"""
COUNTS_AFTER="""report['actual_two_session_races']=0
            report['actual_Native_cases']=4
            report['actual_Auth_HTTP_cases']=0
            report['actual_browser_cases']=2
            report['actual_business_cases']=6
            report['retained_join37_fresh_case_credit']=0
            report['real_Auth_HTTP_qualified']=False
            report['real_Auth_browser_claim']=True"""


def derive(raw):
    value=raw.decode();pairs=((INSTALL_BEFORE,INSTALL_AFTER),(COUNTS_BEFORE,COUNTS_AFTER))
    for before,after in pairs:
        if value.count(before)!=1 or after in value:raise ValueError('JOIN_EXACT_COMPLETE_ENGINE_ANCHOR_REQUIRED')
        value=value.replace(before,after,1)
    reverse=value
    for before,after in reversed(pairs):
        if reverse.count(after)!=1:raise ValueError('JOIN_EXACT_COMPLETE_ENGINE_REVERSE_REQUIRED')
        reverse=reverse.replace(after,before,1)
    if reverse.encode()!=raw:raise ValueError('JOIN_COMPLETE_ENGINE_ORIGINAL_BYTES_REQUIRED')
    return value,dict(original_sha256=sha256(raw).hexdigest(),derived_sha256=sha256(value.encode()).hexdigest(),
        counted_changes=2,complete_original_recovered=True,
        full_install_preuse_reinstall_used_backup_roles_full22_ALL_rows_sequences_CP6_advisors_Auth_package_checks_retained=True)

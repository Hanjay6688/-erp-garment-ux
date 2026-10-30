"""Complete retained package/restore engine with two explicit source changes."""
from hashlib import sha256

INSTALL_BEFORE = "prior=measured(timings,'SINGLE_FULL_READONLY_PARENT_INSTALL',readonly.install,cur)\n                prior=measured(timings,'EXACT_BACKEND3194_PARENT_INSTALL',product.parent().install_delta,cur,prior)"
INSTALL_AFTER = "prior=measured(timings,'EXACT_QUALIFIED_VENDOR_PARENT_INSTALL',product.parent().install,cur)"
COUNTS_BEFORE = """report['actual_two_session_races']=3
            report['actual_Native_cases']=7
            report['actual_Auth_HTTP_cases']=1
            report['actual_browser_cases']=0
            report['actual_business_cases']=11
            report['real_Auth_HTTP_qualified']=True"""
COUNTS_AFTER = """report['actual_two_session_races']=0
            report['actual_Native_cases']=10
            report['actual_Auth_HTTP_cases']=0
            report['actual_browser_cases']=2
            report['actual_business_cases']=12
            report['retained_SKU27_fresh_case_credit']=0
            report['real_Auth_HTTP_qualified']=False
            report['real_Auth_browser_claim']=True"""
CHANGES = ((INSTALL_BEFORE, INSTALL_AFTER), (COUNTS_BEFORE, COUNTS_AFTER))


def derive(raw):
    text = raw.decode()
    for before, after in CHANGES:
        if text.count(before) != 1 or after in text: raise ValueError('S05_EXACT_COMPLETE_ENGINE_ANCHOR_REQUIRED')
        text = text.replace(before, after, 1)
    reverse = text
    for before, after in reversed(CHANGES):
        if reverse.count(after) != 1: raise ValueError('S05_UNIQUE_COMPLETE_ENGINE_REVERSE_REQUIRED')
        reverse = reverse.replace(after, before, 1)
    if reverse.encode() != raw: raise ValueError('S05_COMPLETE_ENGINE_REVERSE_BYTES_REQUIRED')
    return text, dict(original_sha256=sha256(raw).hexdigest(), derived_sha256=sha256(text.encode()).hexdigest(),
        counted_changes=2, exact_original_recovered=True,
        full_install_preuse_reinstall_used_dump_roles_catalog_ALL_sequences_CP6_advisors_package_retained=True)

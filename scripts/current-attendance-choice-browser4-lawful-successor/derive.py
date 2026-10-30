"""Seven counted selections; full vendor install/preuse/reinstall/restore code stays exact."""
from hashlib import sha256

REPLACEMENTS = (
    ("prior=measured(timings,'SINGLE_FULL_READONLY_PARENT_INSTALL',readonly.install,cur)\n"
     "                prior=measured(timings,'EXACT_BACKEND3194_PARENT_INSTALL',product.parent().install_delta,cur,prior)",
     "prior=measured(timings,'EXACT_QUALIFIED_VENDOR_PARENT_INSTALL',product.predecessor.install,cur)"),
    ("report['actual_two_session_races']=3", "report['actual_two_session_races']=0"),
    ("report['actual_Native_cases']=7", "report['actual_Native_cases']=0"),
    ("report['actual_Auth_HTTP_cases']=1", "report['actual_Auth_HTTP_cases']=0"),
    ("report['actual_browser_cases']=0", "report['actual_browser_cases']=cases[runner.CASE]['actual_browser_cases']"),
    ("report['actual_business_cases']=11", "report['actual_business_cases']=4\n            report['real_Auth_browser_claim']=True"),
    ("report['real_Auth_HTTP_qualified']=True", "report['real_Auth_HTTP_qualified']=False"),
)


def derive(raw):
    source = raw.decode()
    for before, after in REPLACEMENTS:
        if source.count(before) != 1:
            raise ValueError('S03_BROWSER4_EXACT_VENDOR_ANCHOR_REQUIRED:' + before)
        source = source.replace(before, after, 1)
    return source, dict(original_sha256=sha256(raw).hexdigest(), derived_sha256=sha256(source.encode()).hexdigest(),
        counted_changes=7, complete_restore_engine_unchanged=True, fresh_Native_race_Auth_HTTP=0,
        actual_browser_claim_only_after_final_observed_PASS=True)

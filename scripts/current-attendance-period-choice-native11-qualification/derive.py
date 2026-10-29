"""Six counted child selections; the complete vendor engine remains frozen."""
from hashlib import sha256

REPLACEMENTS = (
    ("prior=measured(timings,'SINGLE_FULL_READONLY_PARENT_INSTALL',readonly.install,cur)\n"
     "                prior=measured(timings,'EXACT_BACKEND3194_PARENT_INSTALL',product.parent().install_delta,cur,prior)",
     "prior=measured(timings,'EXACT_QUALIFIED_VENDOR_PARENT_INSTALL',product.predecessor.install,cur)"),
    ("report['actual_two_session_races']=3", "report['actual_two_session_races']=0"),
    ("report['actual_Native_cases']=7", "report['actual_Native_cases']=cases[runner.CASE]['actual_Native_cases']"),
    ("report['actual_Auth_HTTP_cases']=1", "report['actual_Auth_HTTP_cases']=0"),
    ("report['actual_business_cases']=11", "report['actual_business_cases']=cases[runner.CASE]['actual_Native_cases']"),
    ("report['real_Auth_HTTP_qualified']=True", "report['real_Auth_HTTP_qualified']=False"),
)


def derive(raw):
    source = raw.decode()
    for before, after in REPLACEMENTS:
        if source.count(before) != 1:
            raise ValueError('S03_NATIVE11_EXACT_VENDOR_ANCHOR_REQUIRED:' + before)
        source = source.replace(before, after, 1)
    return source, dict(original_sha256=sha256(raw).hexdigest(),
        derived_sha256=sha256(source.encode()).hexdigest(), counted_changes=len(REPLACEMENTS),
        unchanged_install_preuse_reinstall_used_guard_backup_roles_CP6_advisors_package=True,
        fresh_race_Auth_HTTP_browser_claim=False)

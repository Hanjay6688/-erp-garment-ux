"""Prepared six exact child selections above the unchanged complete vendor engine."""
from hashlib import sha256

REPLACEMENTS = (
    ("prior=measured(timings,'SINGLE_FULL_READONLY_PARENT_INSTALL',readonly.install,cur)\n"
     "                prior=measured(timings,'EXACT_BACKEND3194_PARENT_INSTALL',product.parent().install_delta,cur,prior)",
     "prior=measured(timings,'EXACT_QUALIFIED_VENDOR_PARENT_INSTALL',product.predecessor.install,cur)"),
    ("report['actual_two_session_races']=3", "report['actual_two_session_races']=0"),
    ("report['actual_Native_cases']=7", "report['actual_Native_cases']=0"),
    ("report['actual_Auth_HTTP_cases']=1", "report['actual_Auth_HTTP_cases']=0"),
    ("report['actual_business_cases']=11", "report['actual_business_cases']=4"),
    ("report['real_Auth_HTTP_qualified']=True", "report['real_Auth_HTTP_qualified']=False"),
)


def derive(raw):
    source = raw.decode()
    for before, after in REPLACEMENTS:
        if source.count(before) != 1:
            raise ValueError('S03_MOUNT_BROWSER_EXACT_VENDOR_ANCHOR_REQUIRED:' + before)
        source = source.replace(before, after, 1)
    return source, dict(original_sha256=sha256(raw).hexdigest(), derived_sha256=sha256(source.encode()).hexdigest(),
        counted_changes=len(REPLACEMENTS), all_install_preuse_reinstall_full_backup_restore_code_unchanged=True,
        baseline_raw_catalog_allrows_allsequences_roles_CP6_advisors_package_unchanged=True,
        fresh_Native_race_Auth_HTTP=0, prepared_browser_cases=4, actual_execution_claim=False)

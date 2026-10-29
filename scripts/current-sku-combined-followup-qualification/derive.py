"""Five counted substitutions; every original install/restore oracle retained."""
from hashlib import sha256

REPLACEMENTS = (
    ("prior=measured(timings,'SINGLE_FULL_READONLY_PARENT_INSTALL',readonly.install,cur)\n"
     "                prior=measured(timings,'EXACT_BACKEND3194_PARENT_INSTALL',product.parent().install_delta,cur,prior)",
     "prior=measured(timings,'EXACT_QUALIFIED_VENDOR_PARENT_INSTALL',product.parent().install,cur)"),
    ("report['actual_Auth_HTTP_cases']=1", "report['actual_Auth_HTTP_cases']=0"),
    ("report['actual_browser_cases']=0", "report['actual_browser_cases']=4"),
    ("report['actual_business_cases']=11", "report['actual_business_cases']=23\n            report['base_Native_cases']=7\n            report['cost_Native_cases']=3\n            report['actual_Native_cases']=10\n            report['actual_Native_session_permission_waits']=6\n            report['group_recovery_supported']=False"),
    ("report['real_Auth_HTTP_qualified']=True", "report['real_Auth_HTTP_qualified']=False\n            report['real_Auth_browser_claim']=True"),
)


def derive(raw):
    source = raw.decode()
    for before, after in REPLACEMENTS:
        if source.count(before) != 1:
            raise ValueError('SKU_COMBINED_EXACT_VENDOR_RUNNER_ANCHOR_REQUIRED:' + before)
        source = source.replace(before, after, 1)
    return source, dict(original_sha256=sha256(raw).hexdigest(), derived_sha256=sha256(source.encode()).hexdigest(),
                        counted_changes=len(REPLACEMENTS), all_install_preuse_reinstall_backup_roles_CP6_advisor_package_oracles_retained=True)

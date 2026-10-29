"""Retain every install/restore oracle of the qualified vendor runner.

Only select the new child installation and label the actual Native-only scope.
The historical runner remains byte-identical in its original namespace.
"""
from hashlib import sha256

REPLACEMENTS = (
    ("prior=measured(timings,'SINGLE_FULL_READONLY_PARENT_INSTALL',readonly.install,cur)\n"
     "                prior=measured(timings,'EXACT_BACKEND3194_PARENT_INSTALL',product.parent().install_delta,cur,prior)",
     "prior=measured(timings,'EXACT_QUALIFIED_VENDOR_PARENT_INSTALL',product.parent().install,cur)"),
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
            raise ValueError('SKU_NATIVE_EXACT_RUNNER_ANCHOR_REQUIRED:' + before)
        source = source.replace(before, after, 1)
    return source, dict(original_sha256=sha256(raw).hexdigest(),
                       derived_sha256=sha256(source.encode()).hexdigest(),
                       counted_changes=len(REPLACEMENTS),
                       unchanged_install_preuse_used_guard_backup_restore_roles_data_sequences_advisors=True,
                       fresh_Auth_HTTP_races_browser_claim=False)

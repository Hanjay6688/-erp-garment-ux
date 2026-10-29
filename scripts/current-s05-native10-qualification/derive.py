"""Exact vendor41c engine; source-root binding and honest Native-only counts.

The install/preuse/reinstall, committed-used guard, full dump/restore, all22,
rows/sequences/roles, CP6 and advisor code is retained without replacement.
"""
from hashlib import sha256

PARENT_SHA256 = 'c420d894f8d5f16bddefeae73addb621507170f372a28e7d6e33d88c7eeb0be9'
REPLACEMENTS = (
    ('REPO=HERE.parents[1]', "REPO=Path(os.environ['S05_CANDIDATE_SOURCE_ROOT']).resolve()"),
    ("report['actual_two_session_races']=3", "report['actual_two_session_races']=0"),
    ("report['actual_Native_cases']=7", "report['actual_Native_cases']=cases[runner.CASE]['actual_Native_cases']"),
    ("report['actual_Auth_HTTP_cases']=1", "report['actual_Auth_HTTP_cases']=0"),
    ("report['actual_business_cases']=11", "report['actual_business_cases']=cases[runner.CASE]['actual_Native_cases']"),
    ("report['real_Auth_HTTP_qualified']=True", "report['real_Auth_HTTP_qualified']=False"),
)


def derive(raw):
    if sha256(raw).hexdigest() != PARENT_SHA256:
        raise ValueError('S05_EXACT_VENDOR41C_ENGINE_BYTES_REQUIRED')
    source = raw.decode()
    for before, after in REPLACEMENTS:
        if source.count(before) != 1:
            raise ValueError('S05_EXACT_ENGINE_ANCHOR_REQUIRED: '+before)
        source = source.replace(before, after, 1)
    return source, dict(original_sha256=PARENT_SHA256, derived_sha256=sha256(source.encode()).hexdigest(),
        counted_changes=len(REPLACEMENTS), unchanged_install_preuse_reinstall_and_full_restore=True,
        unchanged_all22_rows_sequences_roles_CP6_advisors_and_package_engine=True,
        fresh_Auth_HTTP_races_browser_claim=False)

"""Run independently authored cases on the unchanged committed CP6 package in a disposable clone."""
from pathlib import Path
import json
import sys

import cp6_t3_package_run as package

# The package runner prepends an older aligned-writer checkout for baseline tools.
# CP6 case definitions and source verification must come from this audit candidate.
sys.path.insert(0,str(Path(__file__).resolve().parent))


def independent_runtime(browser_mode=False):
    assert not browser_mode
    import cp6_bf_probe as bf
    import cp6_auditor_runner as runner
    import cp6_independent_final_probe as probe
    group=runner.strict_group('INDEPENDENT_CP6_FINAL',probe.cases,bf.verified)
    return dict(label='INDEPENDENT_CP6_FINAL',status=group['status'],independent_acceptance=False,
        groups={'native':{k:group.get(k) for k in ('status','counts','database_remaining','error','cleanup')}})


# Pin the corrected BF release package, so a reused PR merge ref cannot silently
# rerun the old counterexample candidate.
_manifest=json.loads((Path(__file__).resolve().parents[1]/'supabase/release/cp6-t3/MANIFEST.json').read_text())
_bf=next(x for x in _manifest['files'] if x['key']=='BF')
assert _bf['package_sha256']=='9bf4b5642c9d6af3369f98ad265bd802ee993fac7e1d8d290412184588392643', 'AUDIT_WRONG_BF_PACKAGE'
print(json.dumps(dict(group='INDEPENDENT_CP6_CANDIDATE',bf_package_sha256=_bf['package_sha256'])),flush=True)

package._writer_runtime=independent_runtime

if __name__=='__main__':
    package.run('install')

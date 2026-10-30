"""Writer-only current475 source seal, never CI success/Original generation."""
import json
import os
from midnight_common import ROOT, HERE, NS, WORKFLOW, pin
import parent_binding


def seal():
    if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS'):
        raise ValueError('MIDNIGHT_SOURCE_REGENERATION_IN_CI_FORBIDDEN')
    _, source = parent_binding.source()
    for filename in ('GENERATED_RECEIPTS.json', 'LATER_GENERATED_RECEIPTS.json'):
        path = HERE / filename
        data = json.loads(path.read_bytes())
        data['producer_files'][WORKFLOW] = pin((ROOT / WORKFLOW).read_bytes())
        path.write_text(json.dumps(data, indent=2) + '\n')
    own = {str(path.relative_to(ROOT)): pin(path.read_bytes()) for path in HERE.rglob('*')
           if path.is_file() and not path.is_symlink() and path != HERE / 'SOURCE.json'}
    all_files = dict(source, **{parent_binding.SOURCE: parent_binding.SOURCE_PIN},
                     **own, **{WORKFLOW: pin((ROOT / WORKFLOW).read_bytes())})
    manifest = dict(contract='cp7.midnight-native1.current-source.v1',
        active_parent_head=parent_binding.HEAD, active_parent_tree=parent_binding.TREE,
        files=dict(sorted(all_files.items())), actual_current_source_members=475,
        accepted_parent14=None, Native_executed=False, actual_Native_cases=0,
        old425_is_accepted_current_source=False, production_go=False, independent_acceptance=False)
    (HERE / 'SOURCE.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return len(all_files)


if __name__ == '__main__':
    print(seal())

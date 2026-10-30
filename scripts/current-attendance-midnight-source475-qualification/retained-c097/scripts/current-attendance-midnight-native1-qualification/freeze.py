"""Writer-only explicit source seal. Never regenerates in CI or opens a gate."""
from pathlib import Path
from midnight_common import HERE, ROOT, NS, WORKFLOW, document, pin
import os
import json
import source_check


def freeze():
    if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS'):
        raise ValueError('MIDNIGHT_SOURCE_REGENERATION_IN_CI_FORBIDDEN')
    cfg = document((HERE / 'CONFIG.json').read_bytes())
    head, tree, active = source_check.current_declaration(ROOT, cfg)
    workflow = (ROOT / WORKFLOW).read_bytes()
    for name in ('GENERATED_RECEIPTS.json', 'LATER_GENERATED_RECEIPTS.json'):
        path = HERE / name
        data = document(path.read_bytes())
        data['producer_files'][WORKFLOW] = pin(workflow)
        path.write_text(json.dumps(data, indent=2) + '\n')
    own = {str(p.relative_to(ROOT)): pin(p.read_bytes()) for p in HERE.rglob('*')
           if p.is_file() and not p.is_symlink() and p != HERE / 'SOURCE.json'}
    files = dict(active, **own, **{WORKFLOW: pin(workflow)})
    result = dict(contract='cp7.midnight-native1.current-source.v1',
        active_parent_head=head, active_parent_tree=tree, files=dict(sorted(files.items())),
        failed9ac_is_accepted_parent=False, accepted_parent14=cfg['accepted_parent14'],
        actual_Native_cases=0, fresh_original11_or14_reexecuted=False,
        production_go=False, independent_acceptance=False)
    (HERE / 'SOURCE.json').write_text(json.dumps(result, indent=2) + '\n')
    return len(files)


if __name__ == '__main__':
    print(freeze())

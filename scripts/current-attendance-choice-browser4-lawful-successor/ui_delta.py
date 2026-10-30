"""One explicit CSS successor; retained UI originals and business code stay exact."""
from hashlib import sha256
from pathlib import Path
import json
import subprocess

PATH = 'src/attendance-period-choice.css'
PARENT = '84a9a09bf372caeeea4cc9eee4a91c51b43d3d93'
PUBLIC = '62ee27df840fb226ba735ce334ea16849edd54da'
TREE = '49f3fc472e662d8ad088eb18c7e6ad84fbc826b3'


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def expected(root, here, name, original):
    if name != PATH:
        return original
    plan = json.loads((Path(here) / 'UI_CONTRAST_DELTA.json').read_bytes())
    if (plan['path'] != PATH or plan['parent'] != PARENT or plan['public_commit'] != PUBLIC
            or plan['public_tree'] != TREE or plan['before'] != pin(original)):
        raise ValueError('S03_CONTRAST_EXACT_ORIGINAL_AND_PUBLIC_SUCCESSOR_REQUIRED')
    value = original.decode()
    for change in plan['changes']:
        if not change['before'] or value.count(change['before']) != 1:
            raise ValueError('S03_CONTRAST_EXACT_FORWARD_CSS_ANCHOR_REQUIRED')
        value = value.replace(change['before'], change['after'], 1)
    current = value.encode()
    if pin(current) != plan['after']:
        raise ValueError('S03_CONTRAST_CURRENT_CSS_PIN_CHANGED')
    for change in reversed(plan['changes']):
        if not change['after'] or value.count(change['after']) != 1:
            raise ValueError('S03_CONTRAST_EXACT_REVERSE_CSS_ANCHOR_REQUIRED')
        value = value.replace(change['after'], change['before'], 1)
    if value.encode() != original:
        raise ValueError('S03_CONTRAST_ORIGINAL_NOT_RESTORED')
    return current


def verify(root, here):
    root, here = Path(root), Path(here)
    git = lambda *args: subprocess.check_output(['/usr/bin/git', '-C', str(root), *args])
    if (git('rev-parse', PUBLIC + '^{tree}').decode().strip() != TREE
            or git('diff', '--name-only', PARENT, PUBLIC).decode().splitlines() != [PATH]):
        raise ValueError('S03_CONTRAST_EXACT_ONE_FILE_PUBLIC_DELTA_REQUIRED')
    original = git('show', PARENT + ':' + PATH)
    current = expected(root, here, PATH, original)
    if git('show', PUBLIC + ':' + PATH) != current or (root / PATH).read_bytes() != current:
        raise ValueError('S03_CONTRAST_PHYSICAL_CURRENT_PUBLIC_CSS_REQUIRED')
    return dict(public_commit=PUBLIC, public_tree=TREE, changed_paths=[PATH],
        original_UI7_unchanged=True, original_backend_runtime7_unchanged=True,
        actual_browser_credit=0, production_go=False)

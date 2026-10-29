"""Source-only admission. No imported database/client, process execution or network access."""
from hashlib import sha256
from pathlib import Path, PurePosixPath
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def check(root=ROOT, declaration=None):
    value = json.loads((HERE / 'SOURCE.json').read_text()) if declaration is None else declaration
    if value.get('contract_version') != 'cp7.s03-mounted-ui-preparation.v1':
        raise ValueError('S03_MOUNT_UI_DECLARATION_CHANGED')
    entries = value['sources']
    if len(entries) != len({entry['path'] for entry in entries}):
        raise ValueError('S03_MOUNT_UI_DUPLICATE_SOURCE')
    for entry in entries:
        relative = PurePosixPath(entry['path'])
        if relative.is_absolute() or '..' in relative.parts or '\\' in entry['path']:
            raise ValueError('S03_MOUNT_UI_UNSAFE_SOURCE_PATH')
        path = root / str(relative)
        if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError('S03_MOUNT_UI_SOURCE_UNAVAILABLE:' + str(relative))
        raw = path.read_bytes()
        if len(raw) != entry['bytes'] or sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('S03_MOUNT_UI_SOURCE_CHANGED:' + str(relative))
    gate = json.loads((root / value['gate']).read_text())
    if set(gate) != {'status', 'accepted_backend_Native11', 'accepted_reader_Native3', 'accepted_full_restore_and_all5_gates', 'accepted_browser_case_source'}:
        raise ValueError('S03_MOUNT_UI_GATE_SHAPE_CHANGED')
    # No acceptance can be invented by adding an unreviewed string or copying a projected catalog.
    if gate != {'status': 'CLOSED', 'accepted_backend_Native11': None, 'accepted_reader_Native3': None,
                'accepted_full_restore_and_all5_gates': None, 'accepted_browser_case_source': None}:
        raise ValueError('S03_MOUNT_UI_REQUIRES_REVIEWED_ACTUAL_PROOF_BINDER')
    return dict(status='SOURCE_PASS_EXECUTION_CLOSED', exact_source_count=len(entries), gate=gate,
        fresh_Native_cases=0, fresh_Auth_cases=0, fresh_browser_cases=0,
        mounted_candidate_only=True, production_go=False)


def require_execution():
    check()
    raise ValueError('S03_BROWSER_BACKEND11_READER3_FULL_RESTORE_ALL5_AND_CASE_SOURCE_REQUIRED')

"""Exact B component admission for A's isolated full-chain composition."""
from hashlib import sha256, sha1
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
BOUND_SHA256 = '4631deba8cf3b900308aed1cef2ba4f679bbb41eae52b852b6d305ab0d170dd7'


def verify_bound_sources():
    raw = (ROOT/'BOUND_B_SOURCES.json').read_bytes()
    if sha256(raw).hexdigest() != BOUND_SHA256:
        raise ValueError('CURRENT_FROZEN_BOUND_DECLARATION_CHANGED')
    declaration = json.loads(raw)
    directories = {str(Path(path).parent) for path in declaration['files']}
    present = {str(p.relative_to(REPO)) for directory in directories
               for p in (REPO/directory).iterdir() if p.is_file()}
    if present != set(declaration['files']):
        raise ValueError('CURRENT_FROZEN_QUALIFIED_B_FILE_SET_CHANGED')
    for path, expected in declaration['files'].items():
        body = (REPO/path).read_bytes()
        blob = sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()
        if (len(body), sha256(body).hexdigest(), blob) != (expected['bytes'], expected['sha256'], expected['B_blob']):
            raise ValueError('CURRENT_FROZEN_QUALIFIED_B_SOURCE_CHANGED:'+path)
    return dict(B_head=declaration['B_head'], A_parent=declaration['A_prepared_parent'],
                declaration_sha256=BOUND_SHA256, exact_B_files=len(declaration['files']),
                actual_component_originals=declaration['qualified_component_originals'])


def sources():
    from . import binary
    import cp7_frozen_analysis_v2 as capsule
    import cp7_frozen_analysis_units_v2 as units
    return dict(bound=verify_bound_sources(), binary=binary.verify_sources(),
                capsule=capsule.verify_sources(), units=units.verify_sources(),
                adapter_files={p.name:sha256(p.read_bytes()).hexdigest()
                               for p in sorted(ROOT.iterdir()) if p.is_file()})

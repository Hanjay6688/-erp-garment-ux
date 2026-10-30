"""Local-only manifest authoring: old425 pins fixed, NEW allocation hashes only."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import os

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-attendance-choice-reader-native14-qualification'
NS='scripts/current-s03-lawful-fixture-successor-qualification'
WF='.github/workflows/cp7-s03-lawful-fixture-native14.yml'


def pin(path):
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def seal():
    if os.environ.get('CI'):
        raise ValueError('S03_LAWFUL_MANIFEST_REGENERATION_IN_CI_FORBIDDEN')
    # Explicit reviewed base constants, never accept a refreshed parent SOURCE.
    old=json.loads((PARENT/'SOURCE.json').read_bytes())
    cfg=json.loads((HERE/'CONFIG.json').read_bytes())
    if pin(PARENT/'SOURCE.json')!=cfg['inherited_SOURCE']or pin(PARENT/'CONFIG.json')!=cfg['inherited_CONFIG']:
        raise ValueError('S03_LAWFUL_INHERITED_SOURCE_CONFIG_MUST_REMAIN_FROZEN')
    cfg['fixture_API']=dict(path=NS+'/lawful_fixture.py',**pin(HERE/'lawful_fixture.py'))
    (HERE/'CONFIG.json').write_text(json.dumps(cfg,indent=2)+'\n')
    own={str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()and '__pycache__'not in p.parts and p.suffix!='.pyc'}
    own.add(NS+'/SOURCE.json');allowed=own|{WF}
    # Source425 has no transition. Its self-manifest is pinned as one more input.
    files=dict(old['files']);files[str((PARENT/'SOURCE.json').relative_to(ROOT))]=pin(PARENT/'SOURCE.json')
    for name in sorted(allowed-{NS+'/SOURCE.json'}):
        if name in files:
            raise ValueError('S03_LAWFUL_NEW_SCOPE_OVERLAPS_FROZEN_SOURCE:'+name)
        files[name]=pin(ROOT/name)
    source=dict(contract=cfg['qualification_contract'],status='PREPARED_ONLY_NOT_NATIVE14_PASS',
        files=dict(sorted(files.items())),allowed_changes=sorted(allowed),
        source_base=cfg['source_base'],source_base_is_runtime_prerequisite=False,
        inherited425_pins_changed=0,adapted_callback_count=3,original_eight_callbacks_exact=True,
        original_eleven_runtime_callbacks_byte_exact=False,strict_groups=[11,3],
        captures=15,clones=2,runtime7_changed=False,Native_executed=False,
        actual_Native_cases=0,production_go=False,independent_acceptance=False)
    (HERE/'SOURCE.json').write_text(json.dumps(source,indent=2)+'\n')
    return dict(source_files=len(files),new_allocated_paths=len(allowed),source=pin(HERE/'SOURCE.json'))


if __name__=='__main__':print(json.dumps(seal(),indent=2))

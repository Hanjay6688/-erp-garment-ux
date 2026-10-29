"""Writer-only source envelope; never invoked by workflow or actual runner."""
from pathlib import Path
from hashlib import sha256
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def bind():
    origin = json.loads((HERE / 'ORIGIN.json').read_bytes())
    cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
    files = set(origin['copied_S03_files']) | set(cfg['unchanged_engine_files']) | {cfg['workflow']}
    files.update(str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file()
        and p.name != 'SOURCE.json' and '__pycache__' not in p.parts and p.suffix != '.pyc')
    archive = json.loads((ROOT / 'scripts/current-workflow-history-isolation/ARCHIVE.json').read_bytes())
    if len(archive['files']) != 24:
        raise ValueError('S03_NATIVE11_EXACT24_INHERITED_WORKFLOW_PROOFS_REQUIRED')
    files.update(item['archive'] for item in archive['files'])
    files.update(('scripts/current-workflow-history-isolation/ARCHIVE.json',
                  'scripts/current-workflow-history-isolation/materialize.py'))
    pins = {}
    for name in sorted(files):
        raw = (ROOT / name).read_bytes()
        pins[name] = dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
    historical = ['docs/cp7/d17-14/ow08/vendor-combined41c-pass/' + name + '.gz' for name in cfg['retained41c']]
    allowed = set(origin['copied_S03_files']) | {cfg['workflow']}
    allowed.update(name for name in files if name.startswith(str(HERE.relative_to(ROOT)) + '/'))
    allowed.add(str((HERE / 'SOURCE.json').relative_to(ROOT)))
    value = dict(contract=cfg['contract'], status='PREPARED_CURRENT_S03_NATIVE11_NOT_EXECUTED',
        files=pins, allowed_changes=sorted(allowed), untracked_historical_proof_inputs=historical,
        inherited_untracked_workflow_proof_inputs={item['path']: dict(bytes=item['bytes'], sha256=item['sha256'])
                                                  for item in archive['files']},
        source_base=cfg['source_base'], source_base_is_runtime_prerequisite=False,
        exact_copied_S03_files=80, expected_existing_capture=13, expected_private_clones=2,
        Native_case_ids=cfg['Native_case_ids'], Native_executed=False,
        old_cases_and_oracles_modified=False, old_parent_profile_modified=False,
        independent_acceptance=False, production_go=False)
    (HERE / 'SOURCE.json').write_text(json.dumps(value, indent=2) + '\n')
    return dict(status=value['status'], source_files=len(pins), allowed_changes=len(allowed))


if __name__ == '__main__':
    if sys.argv[1:] != ['--writer-freeze']:
        raise SystemExit('S03_NATIVE11_BINDER_IS_WRITER_ONLY')
    print(json.dumps(bind()))

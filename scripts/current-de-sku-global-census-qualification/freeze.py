"""Writer preparation only: create one new seal; never reseal inherited source."""
from pathlib import Path
import importlib.util
import json
import os
import yaml

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def write():
    if os.environ.get('CI') or os.environ.get('GITHUB_ACTIONS') == 'true':
        raise ValueError('GLOBAL_CENSUS_CI_CANNOT_RESEAL_SOURCE')
    a = load('global_census_freeze_admission', 'admission.py')
    w = load('global_census_freeze_workflow', 'workflow.py')
    profiles = load('global_census_freeze_profiles', 'producer_profiles.py')
    if yaml.safe_load((ROOT / w.NEW).read_bytes()) != w.derive(yaml.safe_load((ROOT / w.OLD).read_bytes())):
        raise ValueError('GLOBAL_CENSUS_WORKFLOW_NOT_EXACT_TRANSITION')
    a.immutable_parent()
    for name in profiles.FILES:
        value = profiles.derive(a.document((ROOT / profiles.PARENT / name).read_bytes()), name, (ROOT / w.NEW).read_bytes())
        (HERE / name).write_text(json.dumps(value, indent=2) + '\n')
    paths = {str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p.name != 'SOURCE.json'} | {w.NEW}
    files = {}
    for name in sorted(paths):
        if '__pycache__' in name or name.endswith('.pyc'): raise ValueError('GLOBAL_CENSUS_BYTECODE_FREEZE_FORBIDDEN')
        path = a.regular(name)
        files[name] = dict(a.pin(path.read_bytes()), mode='100755' if path.stat().st_mode & 0o111 else '100644')
    d = load('global_census_freeze_derivation', 'derive.py')
    value = dict(base=a.BASE, base_tree=a.BASE_TREE, original_catalogue_source=a.BCE,
        classification='READ_ONLY_GLOBAL_WRITER_METADATA_WITH_FULL_INHERITED_RESTORATION',
        metadata_only_entry=a.NS + 'probe.py --metadata-runtime', runtime_entry=None,
        actual_Native_credit=0, production_go=False, independent_acceptance=False,
        files=files, derivations={kind: getattr(d, kind)()[1] for kind in ('engine', 'runner', 'gate', 'integration')})
    (HERE / 'SOURCE.json').write_text(json.dumps(value, indent=2) + '\n')
    return a.preflight(require_clean=False)


if __name__ == '__main__': print(json.dumps(write(), sort_keys=True))

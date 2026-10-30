"""Local writer seal for this additive successor; inherited seals are immutable."""
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
        raise ValueError('GLOBAL_MULTISET_CI_CANNOT_RESEAL_SOURCE')
    a = load('multiset_seal_admission', 'admission.py'); w = load('multiset_seal_workflow', 'workflow.py')
    p = load('multiset_seal_profiles', 'producer_profiles.py'); d = load('multiset_seal_derivation', 'derive.py')
    if yaml.safe_load((ROOT / w.NEW).read_bytes()) != w.derive(yaml.safe_load((ROOT / w.OLD).read_bytes())):
        raise ValueError('GLOBAL_MULTISET_WORKFLOW_NOT_EXACT_TRANSITION')
    a.immutable_parent(); d.file_transitions()
    for name in p.FILES:
        value = p.derive(a.document((ROOT / p.PARENT / name).read_bytes()), name, (ROOT / w.NEW).read_bytes())
        (HERE / name).write_text(json.dumps(value, indent=2) + '\n')
    files = {}
    paths = {str(p.relative_to(ROOT)) for p in HERE.rglob('*') if p.is_file() and p.name != 'SOURCE.json'} | {w.NEW}
    for name in sorted(paths):
        if '__pycache__' in name or name.endswith('.pyc'): raise ValueError('GLOBAL_MULTISET_BYTECODE_FREEZE_FORBIDDEN')
        path = a.regular(name)
        files[name] = dict(a.pin(path.read_bytes()), mode='100755' if path.stat().st_mode & 0o111 else '100644')
    value = dict(base=a.BASE, base_tree=a.BASE_TREE, original_catalogue_source=a.BCE,
        classification='READ_ONLY_LOSSLESS_DEPENDENCY_MULTISET_WITH_FULL_INHERITED_RESTORATION',
        metadata_only_entry=a.NS + 'probe.py --metadata-runtime', runtime_entry=None,
        actual_Native_credit=0, production_go=False, independent_acceptance=False,
        files=files, derivations={kind: getattr(d, kind)()[1] for kind in ('engine','runner','gate','integration','capture','census')})
    (HERE / 'SOURCE.json').write_text(json.dumps(value, indent=2) + '\n')
    return a.preflight(require_clean=False)


if __name__ == '__main__': print(json.dumps(write(), sort_keys=True))

"""Old f671 transition intact except two explicit current physical source pins."""
from pathlib import Path
from types import ModuleType
from hashlib import sha256
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'scripts/current-credit-d1-owner-followup-qualification'
CONT = ROOT / 'scripts/current-credit-d1-continuation-qualification'


def check():
    declaration = json.loads((HERE / 'TRANSITION.json').read_bytes())
    old = json.loads((CONT / 'SOURCE.json').read_bytes())
    current_raw = (HERE / 'CONTINUATION_SOURCE.json').read_bytes()
    current = json.loads(current_raw)
    rows = declaration['current_physical_sources']
    if set(rows) != {'scripts/cp7_credit_correction_de/owning.sql', 'scripts/cp7_credit_correction_de/materialize.sql'}:
        raise ValueError('D1_CONT_CURRENT_EXACT_TWO_PHYSICAL_TRANSITIONS_REQUIRED')
    expected = json.loads(json.dumps(old))
    for path, row in rows.items():
        if old['files'][path] != row['before_sha256'] or old['D1_runtime_files'][Path(path).name] != row['before_sha256']:
            raise ValueError('D1_CONT_CURRENT_OLD_SOURCE_PIN_NOT_RETAINED:' + path)
        if sha256((ROOT / path).read_bytes()).hexdigest() != row['after_sha256']:
            raise ValueError('D1_CONT_CURRENT_REVIEWED_PHYSICAL_SOURCE_CHANGED:' + path)
        expected['files'][path] = row['after_sha256']
        expected['D1_runtime_files'][Path(path).name] = row['after_sha256']
    if current != expected or len(current['files']) != 43 or len(current['D1_runtime_files']) != 9:
        raise ValueError('D1_CONT_CURRENT_ONLY_TWO_PINS_IN_TWO_MAPS_ALLOWED')
    if sha256(current_raw).hexdigest() != declaration['continuation_current_manifest_sha256']:
        raise ValueError('D1_CONT_CURRENT_EXPLICIT_MANIFEST_CHANGED')
    spec = importlib.util.spec_from_file_location('d1_cont_current_transition_deriver', HERE / 'derive.py')
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    code, proof = helper.transition((OLD / 'transition.py').read_bytes())
    module = ModuleType('d1_cont_current_private_old_transition')
    module.__file__ = str(OLD / 'transition.py')
    module.CURRENT_PHYSICAL_SOURCE_EXCEPTIONS = {path: row['after_sha256'] for path, row in rows.items()}
    exec(compile(code, module.__file__, 'exec'), module.__dict__)
    prior = module.check()
    return dict(status='EXACT_OLD_TRANSITION_AND_REVIEWED_TWO_CURRENT_PINS', historical=prior,
                current_physical_sources=rows, private_transition_derivation=proof, unchanged_callback_count=3,
                actual_Native_cases=0, production_go=False, independent_acceptance=False)

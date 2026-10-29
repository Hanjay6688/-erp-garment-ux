"""Private original11 runner plus one real Reader3 call, before unchanged used witness."""
from pathlib import Path
from types import ModuleType
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def runtime():
    cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
    load('s03_native14_component_closed_gate', HERE / 'gate.py').selected(cfg)
    original = ROOT / 'scripts/current-attendance-period-choice-native11-qualification/native_runner.py'
    code, proof = load('s03_native14_private_component_derivation', HERE / 'derive.py').native_runner(original.read_bytes())
    reader = load('s03_native14_same_candidate_reader_group', HERE / 'reader_group.py')
    module = ModuleType('s03_native14_private_exact_eleven_plus_reader_three')
    module.__file__ = str(original)
    module.CURRENT_READER_IDS = tuple(cfg['reader_Native3_ids'])
    module.run_actual_reader3 = reader.run
    exec(compile(code, str(original), 'exec'), module.__dict__)
    module.PRIVATE_DERIVATION = proof
    return module

"""Private callback module; only its exact source-guard binding changes."""
from pathlib import Path
from types import ModuleType
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONT = ROOT / 'scripts/current-credit-d1-continuation-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def source_guard():
    code, _ = load('d1_cont_current_source_guard_deriver', HERE / 'derive.py').source_guard((CONT / 'source_guard.py').read_bytes())
    module = ModuleType('d1_cont_current_private_source_guard')
    module.__file__ = str(CONT / 'source_guard.py')
    exec(compile(code, module.__file__, 'exec'), module.__dict__)
    return module


def load_business():
    code, _ = load('d1_cont_current_private_case_deriver', HERE / 'derive.py').cases((CONT / 'cases.py').read_bytes())
    module = ModuleType('d1_cont_current_private_exact_three_callbacks')
    module.__file__ = str(CONT / 'cases.py')
    module.CURRENT_CONTINUATION_GUARD = source_guard
    exec(compile(code, module.__file__, 'exec'), module.__dict__)
    return module

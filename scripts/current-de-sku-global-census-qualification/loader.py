"""Load only source-admitted exact derived modules; no global business entry."""
from pathlib import Path
from types import ModuleType
import importlib.util
import sys

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
PARENT = ROOT / 'scripts/current-de-sku-parent-catalogue-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def module(kind):
    if kind not in ('runner', 'gate', 'integration'):
        raise ValueError('GLOBAL_CENSUS_EXACT_MODULE_KIND_REQUIRED')
    # Even direct use of this loader must first admit all current source bytes.
    load('global_census_loader_early_admission', HERE / 'admission.py').preflight()
    derived = load('global_census_loader_derivation', HERE / 'derive.py')
    text, proof = getattr(derived, kind)()
    result = ModuleType('admitted_global_census_' + kind)
    result.__file__ = str(ROOT / 'scripts/current-global-actual-writer-census-qualification/integration.py'
        if kind == 'integration' else PARENT / ('runner.py' if kind == 'runner' else 'result_gate.py'))
    if kind == 'gate':
        expected = (PARENT / 'context_catalog.py').resolve()
        if 'context_catalog' in sys.modules:
            if Path(sys.modules['context_catalog'].__file__).resolve() != expected:
                raise ValueError('GLOBAL_CENSUS_GATE_CONTEXT_MODULE_SHADOWED')
        else:
            sys.modules['context_catalog'] = load('context_catalog', expected)
    exec(compile(text, result.__file__, 'exec'), result.__dict__)
    result.CENSUS_DERIVATION = proof
    return result


def runner(): return module('runner')
def gate(): return module('gate')
def integration(): return module('integration')

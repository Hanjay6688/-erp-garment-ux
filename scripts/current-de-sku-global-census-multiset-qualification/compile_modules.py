"""Pure module construction, called only after source admission by entrypoints.

The output reader uses this helper during admission to avoid recursively
admitting its own output. Construction performs no SQL or connection.
"""
from pathlib import Path
from types import ModuleType
import importlib.util
import sys

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
HELPER = ROOT / 'scripts/current-global-actual-writer-census-qualification'
CATALOGUE = ROOT / 'scripts/current-de-sku-parent-catalogue-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result); return result


def module(kind):
    if kind not in ('capture', 'integration', 'runner', 'gate', 'census'):
        raise ValueError('GLOBAL_MULTISET_EXACT_MODULE_KIND_REQUIRED')
    derived = load('global_multiset_module_derivation', HERE / 'derive.py')
    text, proof = getattr(derived, kind)()
    result = ModuleType('global_multiset_' + kind)
    result.__file__ = str(HELPER / (kind + '.py') if kind in ('capture', 'integration', 'census')
        else CATALOGUE / ('runner.py' if kind == 'runner' else 'result_gate.py'))
    if kind == 'gate':
        expected = (CATALOGUE / 'context_catalog.py').resolve()
        if 'context_catalog' in sys.modules:
            if Path(sys.modules['context_catalog'].__file__).resolve() != expected:
                raise ValueError('GLOBAL_MULTISET_GATE_CONTEXT_MODULE_SHADOWED')
        else: sys.modules['context_catalog'] = load('context_catalog', expected)
    exec(compile(text, result.__file__, 'exec'), result.__dict__)
    result.CENSUS_DERIVATION = proof
    return result


def capture(): return module('capture')
def integration(): return module('integration')
def census(): return module('census')

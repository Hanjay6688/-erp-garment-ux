"""Compile the exact old cases privately; replace its recipe dependency only."""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASES = 'scripts/cp7_accessory_standard_report/cases.py'
CASES_SHA256 = 'e025be1280630dfb89f62261163194ce072b6f6ad6d909b56ff6c82f75778e98'


def business(retained):
    path = ROOT/CASES
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != CASES_SHA256 or Path(retained.__file__).resolve() != path.resolve():
        raise ValueError('S05_EXACT_RETAINED_NATIVE10_CASES_REQUIRED')
    spec = importlib.util.spec_from_file_location('s05_lawful_recipe_dependency', HERE/'recipe.py')
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    private = ModuleType(retained.__name__+'._lawful_fixture_dates')
    private.__file__ = str(path)
    private.__package__ = retained.__package__
    exec(compile(raw, str(path), 'exec'), private.__dict__)
    for name in ('stage', 'physical', 'issues', 'master', 'qc_source', 'sessions', 'b', 'prod'):
        if getattr(private, name) is not getattr(retained, name):
            raise ValueError('S05_UNCHANGED_RETAINED_DEPENDENCY_REQUIRED:'+name)
    if private.IDS != retained.IDS or len(private.IDS) != 10:
        raise ValueError('S05_EXACT_RETAINED_NATIVE10_IDS_REQUIRED')
    private.lawful_fixture_observations = []
    private.recipe = helper.LawfulRecipe(private, raw, private.lawful_fixture_observations)
    private.fixture_derivation = dict(original_cases_sha256=CASES_SHA256, cases_source_substitutions=0,
                                     changed_private_dependencies=['recipe'], original_imported_module_mutated=False,
                                     callback_function_bodies_and_financial_assertions_byte_exact=True)
    return private

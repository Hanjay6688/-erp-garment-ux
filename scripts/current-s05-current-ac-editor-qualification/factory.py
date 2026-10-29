"""Keep the old private case factory and replace only its private recipe object."""
from pathlib import Path
from hashlib import sha256
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT/'scripts/current-s05-lawful-master-dates-qualification'
FACTORY_SHA = '18eecbcf22f09ead60907ac5ded52bd54a1385cf7d74bad3b1ce25726730cc46'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def business(retained, state):
    raw = (OLD/'factory.py').read_bytes()
    if sha256(raw).hexdigest() != FACTORY_SHA:
        raise ValueError('S05_EXACT_FROZEN_LAWFUL_FACTORY_REQUIRED')
    frozen = load('s05_current_AC_frozen_private_factory', OLD/'factory.py')
    private = frozen.business(retained)
    recipe = load('s05_current_AC_guarded_private_recipe', HERE/'recipe.py')
    private.current_editor_observations = []
    private.recipe = recipe.LawfulRecipe(private, (ROOT/frozen.CASES).read_bytes(),
        private.lawful_fixture_observations, state=state,
        editor_observations=private.current_editor_observations)
    private.current_editor_derivation = recipe.DERIVATION
    return private

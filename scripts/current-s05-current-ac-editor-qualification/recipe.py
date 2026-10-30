"""The old complete lawful fixture with exact AC ABI and current parent guard."""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('s05_current_AC_recipe_binding', HERE/'binding.py')
binding = importlib.util.module_from_spec(spec); spec.loader.exec_module(binding)
legacy, DERIVATION = binding.current_recipe((binding.OLD/'recipe.py').read_bytes())


class LawfulRecipe(legacy.LawfulRecipe):
    def __init__(self, business, raw, observations, *, state, editor_observations):
        super().__init__(business, raw, observations)
        self.actual_installed_parent = state
        self.editor_observations = editor_observations

    def __call__(self, cur, f, qty='0.5', rate='2', empty=False, method='BOM_STANDARD'):
        self.business.b.api.admin(cur)
        binding.admit_editor(cur, self.actual_installed_parent, self.editor_observations)
        return super().__call__(cur, f, qty=qty, rate=rate, empty=empty, method=method)

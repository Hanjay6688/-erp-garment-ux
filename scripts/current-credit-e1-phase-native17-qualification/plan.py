"""The exact old seventeen IDs, with the accepted late callback source only."""
from pathlib import Path
import importlib.util

path = Path(__file__).resolve().parents[1] / 'current-credit-e1-native-qualification/plan.py'
spec = importlib.util.spec_from_file_location('e1_current_literal_retained_plan', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
D1_IDS = module.D1_IDS
E_IDS = module.E_IDS

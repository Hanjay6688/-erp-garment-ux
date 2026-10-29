"""Source-only entry point: imports and checks never connect to the database."""
from pathlib import Path
import importlib.util
import json

path = Path(__file__).resolve().parent / 'probe.py'
spec = importlib.util.spec_from_file_location('sku_admission_only', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
proof = module.admitted()
print(json.dumps(dict(status=proof['status'], actual_Native_cases=0,
                     prerequisite=proof['qualified_parent'], production_go=False)))

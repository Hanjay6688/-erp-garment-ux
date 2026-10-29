"""Admission before any database startup; null prerequisite refuses immediately."""
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value

gate = load('sku_combined_closed_precheck', HERE / 'gate.py')
gate.selected(json.loads((HERE / 'CONFIG.json').read_bytes()))
probe = load('sku_combined_complete_source_check', HERE / 'probe.py')
proof = probe.admitted()
print(json.dumps(dict(status=proof['status'], actual_cases=0, production_go=False)))

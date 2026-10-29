"""Inert until root terminal/raw binding; then exact frozen bounded GET code."""
from pathlib import Path
from types import ModuleType
import importlib.util
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    spec = importlib.util.spec_from_file_location('e1_current_before_any_GET_gate', HERE / 'gate.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    gate.selected(json.loads((HERE / 'CONFIG.json').read_bytes()))
    path = ROOT / 'scripts/current-credit-e1-native-qualification/fetch_prerequisite.py'
    module = ModuleType('e1_current_private_exact_retained_fetch')
    module.__file__ = str(HERE / 'fetch_prerequisite.py')
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    module.main()


if __name__ == '__main__':
    main()

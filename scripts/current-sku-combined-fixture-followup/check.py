"""Pre-DB child closure; --offline checks sources without importing runtime."""
from pathlib import Path
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == '__main__':
    offline = sys.argv[1:] == ['--offline']
    assert offline or sys.argv[1:] == []
    source = load('sku_unique_preDB_source', HERE / 'closure.py').source_only()
    first = load('sku_unique_preDB_first_failure', HERE / 'recovery.py').verified()
    if not offline:
        load('sku_unique_preDB_runtime', HERE / 'probe.py').admitted()
    print(json.dumps(dict(status=source['status'], first_failure=first,
        old_parent_files=source['unchanged_parent_files'], new_child_files=source['child_source_files'],
        runtime_imported=not offline, actual_successor_cases=0, production_go=False)))

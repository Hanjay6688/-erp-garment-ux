"""No DB/imports on --offline; unknown flags rejected before source/runtime work."""
from pathlib import Path
import argparse
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


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args(argv)
    admission = load('sku23_cli_admission', HERE / 'admission.py')
    proof = admission.preflight(require_clean=not args.offline)
    if not args.offline:
        runtime = load('sku23_cli_probe', HERE / 'probe.py').runtime()
        proof['runtime_admission'] = runtime.admitted()
    print(json.dumps(dict(status='SOURCE_ONLY_NOT_NATIVE_PASS', proof=proof, actual_successor_cases=0), sort_keys=True))


if __name__ == '__main__':
    main()

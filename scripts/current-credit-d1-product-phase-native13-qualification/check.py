"""Source-only admission CLI; runtime admission never connects to the DB."""
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--offline', action='store_true', help='joined source and closed-gate proof without runtime imports')
    group.add_argument('--runtime', action='store_true', help='full exact vendor Original admission, no SQL')
    args = parser.parse_args(argv)
    if args.offline:
        proof = load('d1_product_phase_offline_closure', HERE / 'source_check.py').check(require_bound=False)
        print(json.dumps(proof, indent=2))
    else:
        proof = load('d1_product_phase_admission_probe', HERE / 'probe.py').check()
        print(json.dumps(dict(status=proof['status'], actual_Native_cases=0,
            prerequisite=proof['qualified_parent'], production_go=False)))


if __name__ == '__main__':
    main()

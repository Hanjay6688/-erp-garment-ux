"""Stdlib-only first checkout admission; no inherited imports before admission."""
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--offline', action='store_true'); args = parser.parse_args()
    spec = importlib.util.spec_from_file_location('global_census_early_source', HERE / 'admission.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    proof = module.preflight(require_clean=not args.offline)
    print(json.dumps(dict(status='WHOLE_SOURCE_ONLY_NO_DATABASE', proof=proof,
        actual_business_cases=0, actual_Native_credit=0, runtime_entry=None), sort_keys=True))


if __name__ == '__main__': main()

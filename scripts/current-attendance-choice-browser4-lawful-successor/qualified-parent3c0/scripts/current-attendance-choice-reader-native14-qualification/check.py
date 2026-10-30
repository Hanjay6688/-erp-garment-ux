"""Offline source or actual prerequisite intake; unknown flags reject before gate."""
from pathlib import Path
import argparse
import importlib.util
import json

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--offline', action='store_true')
    mode.add_argument('--runtime', action='store_true')
    args = parser.parse_args(argv)
    if args.offline:
        result = load('s03_native14_offline_closure', HERE / 'source_check.py').check()
    else:
        result = load('s03_native14_current_runtime_intake', HERE / 'probe.py').runtime().admitted()
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

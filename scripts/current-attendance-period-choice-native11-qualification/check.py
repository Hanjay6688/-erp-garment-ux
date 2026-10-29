"""Offline source or full prerequisite admission, neither opens a DB."""
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
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--offline', action='store_true')
    group.add_argument('--runtime', action='store_true')
    args = parser.parse_args(argv)
    if args.offline:
        value = load('s03_native11_offline_check', HERE / 'source_check.py').check()
    else:
        value = load('s03_native11_full_import_check', HERE / 'probe.py').runtime().admitted()
    print(json.dumps(value, indent=2))


if __name__ == '__main__':
    main()

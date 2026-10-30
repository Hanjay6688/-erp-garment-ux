"""Read-only source or actual retained Original admission; never a DB run."""
from pathlib import Path
import argparse
import importlib.util
import json

HERE=Path(__file__).resolve().parent


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--offline',action='store_true');mode.add_argument('--runtime',action='store_true')
    args=parser.parse_args(argv)
    result=load('s03_lawful_cli_source',HERE/'source_check.py').check() if args.offline else load('s03_lawful_cli_runtime',HERE/'probe.py').runtime().admitted()
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()

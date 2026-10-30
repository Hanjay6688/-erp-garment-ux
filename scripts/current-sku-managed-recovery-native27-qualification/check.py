"""No database on source admission; CLI flags close before import/runtime."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');args=parser.parse_args(argv)
    context=load('sku27_cli_DB_context',HERE/'source_context.py')
    with context.fenced_source_read()as guard:
        admission=load('sku27_cli_source',HERE/'admission.py');proof=admission.preflight(require_clean=not args.offline)
        if not args.offline:proof['complete_runtime_admission']=load('sku27_cli_complete_probe',HERE/'probe.py').runtime().admitted()
    proof['source_DB_guard']=guard
    print(json.dumps(dict(status='SOURCE_ONLY_NATIVE_FINANCIAL_0',proof=proof,actual_successor_cases=0),sort_keys=True))

if __name__=='__main__':main()

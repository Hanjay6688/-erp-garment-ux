"""Actual source/import admission only; unknown flags refuse before imports."""
from pathlib import Path
import argparse
import importlib.util
import json

HERE=Path(__file__).resolve().parent


def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime',action='store_true');args=p.parse_args(argv)
    proof=load('s05_wib_owner_CLI_actual_source',HERE/'admission.py').offline()
    if args.runtime:
        actual=load('s05_wib_owner_CLI_actual_runtime',HERE/'probe.py').check()
        if actual['fresh_runtime_credit_from_admission']!=0:raise ValueError('S05_SOURCE_IMPORT_IS_NOT_NATIVE_EXECUTION')
    print(json.dumps(dict(status='PASS_SOURCE_ONLY',source_files=proof['source_files'],
        Native_case_ids=proof['Native_case_ids'],actual_Native=0,runtime_source_imports_checked=args.runtime,
        production_go=False,independent_acceptance=False)))


if __name__=='__main__':main()

"""New source gate first; unchanged full owning install/restore engine afterwards."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-attendance-choice-reader-native14-qualification'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def runtime():
    load('s03_lawful_first_source_gate',HERE/'source_check.py').check(require_bound=True)
    derivative=load('s03_lawful_private_outer_bindings',HERE/'derive.py')
    parent,proof=derivative.module('s03_lawful_complete_frozen_parent_probe',PARENT/'probe.py',
        derivative.PROBE_PAIRS,CURRENT_HERE=HERE)
    engine=parent.runtime()
    engine.LAWFUL_PROBE_DERIVATION=proof
    return engine


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    args=parser.parse_args(argv);engine=runtime()
    if args.check:
        proof=engine.admitted();print(json.dumps(dict(status=proof['status'],actual_Native_cases=0,production_go=False)))
    else:
        engine.admitted();engine.package._writer_runtime=lambda browser_mode=False:engine.run()
        engine.package.run('install')


if __name__=='__main__':main()

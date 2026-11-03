"""Separate local source preparation from complete environment admission."""
from pathlib import Path
import argparse
import importlib.util
import json
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--source',action='store_true');mode.add_argument('--complete',action='store_true');args=parser.parse_args()
    fence=load('sku_money_no_database_source_fence',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    with fence.fenced_source_read()as guard:
        if args.source:
            proof=load('sku_money_source_only',HERE/'admission.py').source_only(ROOT,HERE)
            business=load('sku_money_import_all_native_callbacks',HERE/'native_cases.py')
            assert list(business.IDS)==proof['case_ids']
        else:
            engine=load('sku_money_complete_probe',HERE/'probe.py').runtime();proof=engine.admitted()
    print(json.dumps(dict(status=proof['status'],case_ids=proof.get('case_ids'),network_database_guard=guard,
        actual_ERP_cases=0,complete_runtime_admitted=args.complete,production_go=False),sort_keys=True))

if __name__=='__main__':main()

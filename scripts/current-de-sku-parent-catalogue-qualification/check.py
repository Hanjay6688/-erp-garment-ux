"""Source-only CLI, with database and non-Git network explicitly fenced."""
from pathlib import Path
import argparse
import importlib.util
import json

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');args=parser.parse_args()
    context=load('de_sku_source_DB_fence',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
    with context.fenced_source_read()as guard:
        proof=load('de_sku_exact_source',HERE/'admission.py').preflight(require_clean=not args.offline)
    print(json.dumps(dict(status='SOURCE_ONLY_NO_DB',proof=proof,guard=guard,actual_business_cases=0),default=str))

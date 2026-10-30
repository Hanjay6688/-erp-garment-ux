"""Retain exact old census plus new per-case sequence prefixes, including failures."""
from pathlib import Path
from hashlib import sha256
import argparse
import importlib.util
import json

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

def retain(workspace):
    path=ROOT/'scripts/current-sku-all-member-native23-qualification/retain_outputs.py'
    spec=importlib.util.spec_from_file_location('sku27_unchanged_full_cost_retention',path)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    previous=old.retain(workspace);workspace=Path(workspace).resolve();target=workspace/'auditor/cp6-proof/t3';rows=[]
    for checkout in('writer','base','auditor'):
        for source in sorted((workspace/checkout/'cp6-proof/t3').glob('SKU27_SEQUENCE_PREFIX_*.json')):
            raw=source.read_bytes();destination=target/source.name
            if destination.exists()and destination.read_bytes()!=raw:raise ValueError('SKU27_SEQUENCE_ORIGINAL_NAME_COLLISION')
            if destination!=source:destination.write_bytes(raw)
            assert destination.read_bytes()==raw
            rows.append(dict(source=str(source.relative_to(workspace)),artifact_path=str(destination.relative_to(workspace)),bytes=len(raw),sha256=sha256(raw).hexdigest()))
    proof=dict(status='EXACT_COST_CENSUS_AND_SEQUENCE_PREFIX_ORIGINALS_RETAINED',retained_old=previous,sequence_prefixes=rows,
      original_result_fields_rewritten=False,absence_is_not_PASS=True,actual_new_case_credit=0)
    (target/'SKU27_ORIGINALS_COPY_RECEIPT.json').write_text(json.dumps(proof,indent=2)+'\n');return proof

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--workspace',required=True);args=parser.parse_args()
    print(json.dumps(retain(args.workspace),sort_keys=True))

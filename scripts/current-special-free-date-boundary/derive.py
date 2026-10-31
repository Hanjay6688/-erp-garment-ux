"""One exact Native predicate correction; no install or economic policy choice."""
from pathlib import Path
from hashlib import sha256
import argparse,json

HERE=Path(__file__).resolve().parent
BEFORE='v.effective_from<=p_at and (v.effective_to is null or v.effective_to>p_at)'
AFTER="v.effective_from<=(p_at at time zone 'Asia/Jakarta')::date and (v.effective_to is null or v.effective_to>=(p_at at time zone 'Asia/Jakarta')::date)"

def derive(raw):
    reference=json.loads((HERE/'ACTUAL_REFERENCE.json').read_bytes())
    if len(raw)!=reference['original_bytes']or sha256(raw).hexdigest()!=reference['original_sha256']:
        raise ValueError('SPECIAL_FREE_EXACT_ACTUAL_FUNCTION_REQUIRED')
    text=raw.decode()
    if text.count(BEFORE)!=1 or AFTER in text:raise ValueError('SPECIAL_FREE_EXACT_DATE_PREDICATE_REQUIRED')
    result=text.replace(BEFORE,AFTER,1)
    if result.count(AFTER)!=1 or result.replace(AFTER,BEFORE,1).encode()!=raw:
        raise ValueError('SPECIAL_FREE_EXACT_ORIGINAL_RECOVERY_REQUIRED')
    return result,dict(status='PREPARED_WIB_INCLUSIVE_DATE_FIX_NOT_INSTALLED',
        original_sha256=reference['original_sha256'],derived_sha256=sha256(result.encode()).hexdigest(),
        counted_predicate_changes=1,all_other_bytes_unchanged=True,function_metadata_change=False,
        owner_category_values_seeded=False,GOOD_eligibility_policy_decided=False,
        actual_Native_cases=0,production_go=False,independent_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emit',type=Path);args=parser.parse_args()
    text,proof=derive((HERE/'ORIGINAL.sql').read_bytes())
    if args.emit:args.emit.write_text(text)
    print(json.dumps(proof))

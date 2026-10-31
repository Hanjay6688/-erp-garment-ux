"""Explicit local writer freeze. Never regenerate accepted inputs in CI."""
from pathlib import Path
from hashlib import sha256
import json,os,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
WORKFLOW='.github/workflows/cp7-s03-sku-s05-composite.yml'


def freeze():
    if os.environ.get('CI')or sys.argv[1:]!=['--writer-freeze']:raise ValueError('JOIN_EXPLICIT_LOCAL_WRITER_FREEZE_ONLY')
    if not(ROOT/WORKFLOW).is_file():raise ValueError('JOIN_COMPLETE_WORKFLOW_REQUIRED_BEFORE_FREEZE')
    names={str(p.relative_to(ROOT))for p in HERE.rglob('*')if p.is_file()and p.name!='SOURCE.json'and'__pycache__'not in p.parts and p.suffix!='.pyc'}|{WORKFLOW}
    files={name:sha256((ROOT/name).read_bytes()).hexdigest()for name in sorted(names)}
    result=dict(status='PREPARED_CURRENT_COMPOSITE37_NOT_EXECUTED',base_head='b25eaae55a144aa03cc05f8f77109f5d0b02fbfb',
        base_tree='e08f5eba90fd9a2deeb53a0a483c49e7a080e31c',files=files,actual_cases=0,
        planned=dict(SKU_Native7=7,S03_Native14=14,S05_Native10=10,S03_browser4=4,S05_browser2=2,total=37),
        browser_case_ids=['S05_SKU_NORMAL_APP_DESKTOP_SOURCE_AND_LATE_REPLY','S05_SKU_NORMAL_APP_MOBILE390_UNKNOWN_ZERO_AND_CURRENT_ACCESS'],
        retained_current_SKU27_is_not_fresh_composite_case_credit=True,
        production_go=False,independent_acceptance=False)
    (HERE/'SOURCE.json').write_text(json.dumps(result,indent=2)+'\n')
    return dict(status=result['status'],files=len(files),actual_cases=0)


if __name__=='__main__':print(json.dumps(freeze()))

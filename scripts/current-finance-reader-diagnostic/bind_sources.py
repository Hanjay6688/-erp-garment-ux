from pathlib import Path
from hashlib import sha256
import argparse,json
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
HEAD='a569d322bb91162026c7f9cc162facf12f0dd7ea'
def main():
    p=argparse.ArgumentParser();p.add_argument('--proof',required=True);p.add_argument('--original',required=True);a=p.parse_args()
    proof=json.loads(Path(a.proof).read_bytes());raw=Path(a.original).read_bytes()
    assert proof['head']==HEAD and proof['status']=='PASS'
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw);assert actual['status']=='PASS'and actual['qualification_commit']==HEAD
    old=json.loads((REPO/'scripts/current-frozen-finance-stage-profile/SOURCE.json').read_bytes())
    assert actual['source_declaration']['qualification']==old
    files=dict(old['files'])
    for rel,digest in files.items():assert sha256((REPO/rel).read_bytes()).hexdigest()==digest,rel
    paths=[p for p in HERE.iterdir()if p.is_file()and p.name!='SOURCE.json']
    paths+=[REPO/'.github/workflows/cp7-d17-18-finance-reader-diagnostic.yml',REPO/'scripts/current-frozen-finance-stage-profile/SOURCE.json']
    for p in paths:files[str(p.relative_to(REPO))]=sha256(p.read_bytes()).hexdigest()
    result=dict(contract='cp7.d17-18.finance-reader-diagnostic.v1',profile_head=HEAD,
        actual_profile=proof,case_ids=['FINANCE_READER_SMALL_AND_FACTORY_PAIRED_ROLLBACK_DIAGNOSTIC'],
        files=dict(sorted(files.items())),diagnostic_only=True,performance_qualification=False,production_go=False)
    (HERE/'SOURCE.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='BOUND_TO_ACTUAL_PROFILE',pins=len(files),production_go=False)))
if __name__=='__main__':main()

from pathlib import Path
from hashlib import sha256
import argparse,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
HEAD='e352901d6975346fa6a099770d179ffc6a59475d'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--proof',required=True);parser.add_argument('--original',required=True)
    args=parser.parse_args();proof=json.loads(Path(args.proof).read_bytes());raw=Path(args.original).read_bytes()
    assert proof['head']==HEAD and proof['status']=='PASS','ACTUAL_COMPOSED_REUSE_PASS_REQUIRED_BEFORE_BINDING'
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw);assert actual['status']=='PASS'and actual['qualification_commit']==HEAD
    old=json.loads((REPO/'scripts/current-finance-check-reuse-diagnostic/SOURCE.json').read_bytes())
    assert actual['source_declaration']['qualification']==old
    for key in ('required_case_ids_pass','cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal'):
        assert actual[key]is True,key
    files=dict(old['files'])
    for path,digest in files.items():assert sha256((REPO/path).read_bytes()).hexdigest()==digest,path
    paths=[p for p in HERE.iterdir()if p.is_file()and p.name!='SOURCE.json']
    paths+=[REPO/'.github/workflows/cp7-d17-18-finance-reader-source-race.yml',REPO/'scripts/current-finance-check-reuse-diagnostic/SOURCE.json']
    for path in paths:files[str(path.relative_to(REPO))]=sha256(path.read_bytes()).hexdigest()
    result=dict(contract='cp7.d17-18.finance-reader-source-race.v1',reuse_head=HEAD,actual_reuse=proof,
        case_ids=['FINANCE_FRESH_SNAPSHOT_CONCURRENT_BOOK_CHANGE_AND_RECOVERY'],files=dict(sorted(files.items())),
        diagnostic_only=True,performance_qualification=False,production_go=False)
    with (HERE/'SOURCE.json').open('x')as stream:stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='BOUND_TO_ACTUAL_COMPOSED_REUSE',pins=len(files),production_go=False)))

if __name__=='__main__':main()

"""Bind a prepared candidate only to an existing exact PASS Native5 Original."""
from pathlib import Path
from hashlib import sha256
import argparse,ast,json,subprocess

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
PRODUCT_PARENT='73b5ada8a6e1c6fbbfc53a3a4fe2b305def6657f'
PROGRESS_HEAD='54676bcc969b950dd1ec52eb7feba2d7e58a8cb4'

def main():
    p=argparse.ArgumentParser();p.add_argument('--proof',required=True);p.add_argument('--original',required=True)
    a=p.parse_args();proof=json.loads(Path(a.proof).read_bytes());raw=Path(a.original).read_bytes()
    assert proof['head']==PROGRESS_HEAD and proof['status']=='PASS'
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['label']=='CP7_D17_18_PROGRESS_NATIVE5'and actual['status']=='PASS'
    assert actual['qualification_commit']==PROGRESS_HEAD and actual['native']['counts']=={'PASS':5}
    assert actual['required_case_ids_pass']and actual['cp6_restored']and actual['advisor_gate']
    assert actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
    assert actual['production_go']is actual['independent_acceptance']is False
    parent=REPO/'scripts/current-frozen-progress-native-qualification/SOURCE.json'
    declared=json.loads(parent.read_bytes());assert actual['source_declaration']['qualification']==declared
    files=dict(declared['files'])
    for rel,digest in files.items():assert sha256((REPO/rel).read_bytes()).hexdigest()==digest,rel
    retained=subprocess.check_output(['git','-C',str(REPO),'ls-tree','-r','--name-only',PROGRESS_HEAD,
        'scripts/current-frozen-progress-native-qualification','.github/workflows/cp7-d17-18-progress-native.yml'],text=True).splitlines()
    retained_pins={}
    for rel in retained:
        original=subprocess.check_output(['git','-C',str(REPO),'show',PROGRESS_HEAD+':'+rel])
        assert (REPO/rel).read_bytes()==original,rel
        retained_pins[rel]=sha256(original).hexdigest()
    additions=subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',declared['product_parent'],PRODUCT_PARENT],text=True).splitlines()
    fixture=json.loads((HERE/'B_FIXTURE_SOURCE.json').read_bytes())
    own=[str(p.relative_to(REPO))for p in HERE.iterdir()if p.is_file()and p.name!='SOURCE.json']
    for rel in set(additions)|set(retained)|set(fixture['files'])|set(own)|{'.github/workflows/cp7-d17-18-choice-preparation-native.yml'}:
        files[rel]=sha256((REPO/rel).read_bytes()).hexdigest()
    ids=None
    for statement in ast.parse((HERE/'cases.py').read_text()).body:
        if isinstance(statement,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='IDS'for t in statement.targets):ids=ast.literal_eval(statement.value)
    assert ids is not None and len(ids)==6
    result=dict(contract='cp7.d17-18.choice-preparation-native6-qualification.v1',policy_id='D17-18-20261026',
        product_parent=PRODUCT_PARENT,case_ids=list(ids),files=dict(sorted(files.items())),retained_progress_files=retained_pins,
        actual_predecessor=proof,full_final_acceptance=False,actual_Auth_HTTP_credit=False,production_go=False)
    (HERE/'SOURCE.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='BOUND_TO_ACTUAL_NATIVE5_PASS',files=len(files),production_go=False)))

if __name__=='__main__':main()

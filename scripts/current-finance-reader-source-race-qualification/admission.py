from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def admitted(repo,here,ids,product,native):
    assert (here/'SOURCE.json').is_file(),'ACTUAL_COMPOSED_REUSE_PASS_REQUIRED_BEFORE_BINDING'
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']=='cp7.d17-18.finance-reader-source-race.v1'
    assert pins['case_ids']==list(ids)and pins['performance_qualification']is pins['production_go']is False
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only',pins['reuse_head'],'HEAD'],text=True).splitlines()
    assert all(p.startswith('scripts/current-finance-reader-source-race-qualification/')or p=='.github/workflows/cp7-d17-18-finance-reader-source-race.yml'for p in changed)
    parent=load('race_retained_factory_admission',repo/'scripts/current-frozen-finance-factory-observe-qualification/probe.py').admitted()
    assert parent['current_installation']==product.sources()
    raw=Path(os.environ['D17_18_FINANCE_REUSE_ORIGINAL']).read_bytes()
    proof=load('race_reuse_evidence',here/'evidence.py').validate(repo,pins['actual_reuse'],raw,product,parent)
    return dict(qualification=pins,retained_admission=parent,current_installation=product.sources(),
        actual_reuse_verified=proof,unchanged_product_sources=True,diagnostic_only=True,
        performance_qualification=False,production_go=False)

if __name__=='__main__':
    here=Path(__file__).resolve().parent;repo=here.parents[1]
    probe=load('race_probe',here/'probe.py');result=probe.admitted()
    print(json.dumps(dict(status='SOURCE_RACE_ADMITTED',pins=len(result['qualification']['files']),production_go=False)))

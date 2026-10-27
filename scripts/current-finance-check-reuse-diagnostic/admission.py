from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def admitted(repo,here,ids,product,native):
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']=='cp7.d17-18.finance-check-reuse-diagnostic.v1'
    assert pins['case_ids']==list(ids)and pins['performance_qualification']is pins['production_go']is False
    for path,digest in pins['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only',pins['reader_head'],'HEAD'],text=True).splitlines()
    assert all(p.startswith('scripts/current-finance-check-reuse-diagnostic/')or p=='.github/workflows/cp7-d17-18-finance-check-reuse-diagnostic.yml'for p in changed)
    parent=load('reuse_retained_factory_admission',repo/'scripts/current-frozen-finance-factory-observe-qualification/probe.py').admitted()
    assert parent['current_installation']==product.sources()
    raw=Path(os.environ['D17_18_FINANCE_READER_ORIGINAL']).read_bytes()
    proof=load('reuse_reader_evidence',here/'evidence.py').validate(repo,pins['actual_reader'],raw,product,parent)
    return dict(qualification=pins,retained_admission=parent,current_installation=product.sources(),
        actual_reader_verified=proof,unchanged_product_sources=True,diagnostic_only=True,
        performance_qualification=False,production_go=False)

if __name__=='__main__':
    here=Path(__file__).resolve().parent;repo=here.parents[1]
    p=load('reuse_diagnostic_probe',here/'probe.py')
    result=admitted(repo,here,p.IDS,p.product,p.qualified_native)
    print(json.dumps(dict(status='ADMITTED_REUSE_DIAGNOSTIC',pins=len(result['qualification']['files']),production_go=False)))

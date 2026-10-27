"""Bind this experiment to the measured unchanged product and actual profile."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def admitted(repo,here,ids,product,native):
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']=='cp7.d17-18.finance-reader-diagnostic.v1'
    assert pins['case_ids']==list(ids)and pins['performance_qualification']is pins['production_go']is False
    for rel,digest in pins['files'].items():assert sha256((repo/rel).read_bytes()).hexdigest()==digest,rel
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only',pins['profile_head'],'HEAD'],text=True).splitlines()
    assert all(p.startswith('scripts/current-finance-reader-diagnostic/')or p=='.github/workflows/cp7-d17-18-finance-reader-diagnostic.yml'for p in changed)
    old=load('retained_factory_profile_source',repo/'scripts/current-frozen-finance-factory-observe-qualification/probe.py').admitted()
    assert old['current_installation']==product.sources()
    proof=pins['actual_profile'];raw=Path(os.environ['D17_18_FINANCE_PROFILE_ORIGINAL']).read_bytes()
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['status']==proof['status']=='PASS'and actual['qualification_commit']==pins['profile_head']==proof['head']
    declared=json.loads((repo/'scripts/current-frozen-finance-stage-profile/SOURCE.json').read_bytes())
    assert actual['source_declaration']['qualification']==declared
    assert actual['source_declaration']['retained_admission']==old
    for rel,digest in declared['files'].items():assert sha256((repo/rel).read_bytes()).hexdigest()==digest,rel
    for key in('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal','required_case_ids_pass'):
        assert actual[key]is True,key
    case=next(iter(actual['committed'].values()));m=case['measurements'][1]
    assert m['name']=='OFFICIAL_FINANCE_REPORT_UNIT'and m['status']=='COMPLETED_DIAGNOSTIC'
    calls={r['function']:r['calls']for r in m['functions']}
    assert calls['erp.run_v268_financial_report_checks()']==3
    assert calls['erp.resolve_opening_fg_unit_hpp(uuid,date)']==10800
    assert actual['production_go']is actual['independent_acceptance']is False
    return dict(qualification=pins,retained_admission=old,current_installation=product.sources(),
        actual_profile_verified=proof,unchanged_product_sources=True,diagnostic_only=True,
        performance_qualification=False,production_go=False)

if __name__=='__main__':
    here=Path(__file__).resolve().parent;repo=here.parents[1]
    p=load('finance_reader_diagnostic_probe',here/'probe.py')
    result=admitted(repo,here,p.IDS,p.product,p.qualified_native)
    print(json.dumps(dict(status='ADMITTED_DIAGNOSTIC',pins=len(result['qualification']['files']),production_go=False)))

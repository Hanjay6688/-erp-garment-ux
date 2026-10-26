"""Exact failed product and separately bound diagnostic sources, before DB."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import os
import subprocess

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def verify_pins(repo,here):
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['contract']=='cp7.d17-18.factory-stage-profile.v1'
    assert pins['policy_id']=='D17-18-20261026'
    assert pins['diagnostic_statement_limit_ms']==30000 and pins['small_statement_limit_ms']==8000
    assert pins['performance_qualification']is pins['production_go']is False
    for path,digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only',pins['product_parent'],'HEAD'],text=True).splitlines()
    assert all(p.startswith('scripts/current-frozen-finance-stage-profile/')or p=='.github/workflows/cp7-d17-18-factory-stage-profile.yml' for p in changed)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no'],text=True).strip()
    return pins

def admitted(repo,here,ids,product,native):
    pins=verify_pins(repo,here)
    assert pins['case_ids']==list(ids)
    old=load('unchanged_failed_factory_admission',repo/'scripts/current-frozen-finance-factory-observe-qualification/probe.py').admitted()
    assert old['current_installation']==product.sources()
    proof=pins['failure_original'];raw=Path(os.environ['D17_18_FACTORY_FAILURE_ORIGINAL']).read_bytes()
    assert len(raw)==proof['bytes'] and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['status']=='INCOMPLETE' and actual['qualification_commit']==pins['product_parent']
    assert actual['cp6_restored'] is actual['advisor_gate'] is True
    case=next(iter(actual['committed'].values()));diagnostics=case['terminal_diagnostics']
    assert len(diagnostics['job_rows'])==2 and len(diagnostics['finance_capture_rows'])==1
    for job in diagnostics['job_rows']:
        assert (job['state'],job['units_done'],job['failure_unit'],job['unit_attempts'],job['failure_sqlstate'])==('FAILED',0,0,3,'57014')
    finance=diagnostics['finance_capture_rows'][0]
    assert (finance['state'],finance['units_done'],finance['unit_attempts'],finance['failure_code'])==('FAILED',0,3,'CP7_FINANCE_REPORT_TIME_LIMIT')
    return dict(qualification=pins,retained_admission=old,exact_failed_original_verified=True,
                failure_remains_INCOMPLETE=True,product_sources_unchanged=True,
                diagnostic_only=True,performance_qualification=False,production_go=False)

if __name__=='__main__':
    here=Path(__file__).resolve().parent;repo=here.parents[1]
    probe=load('d17_18_diagnostic_preflight_graph',here/'probe.py')
    result=admitted(repo,here,probe.IDS,probe.product,probe.qualified_native)
    print(json.dumps(dict(status='ADMITTED_DIAGNOSTIC_ONLY',source_pins=len(result['qualification']['files']),
                         previous_failure_preserved=True,performance_qualification=False,production_go=False)))

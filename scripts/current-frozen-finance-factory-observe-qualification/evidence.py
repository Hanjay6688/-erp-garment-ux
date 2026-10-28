"""Retain nine prior Originals and the exact failed date2 run that requires diagnostics."""
from hashlib import sha256
import importlib.util,json
def validate(repo,config,proofs,actuals,product):
    old=repo/'scripts/current-frozen-finance-factory-date2-qualification'
    spec=importlib.util.spec_from_file_location('retained_factory_date2_evidence',old/'evidence.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    variable=config['terminal_failure_variable'];assert variable in proofs and len(proofs)==config['required_actual_originals']==10
    cfg=json.loads((old/'CONFIG.json').read_bytes())
    sources,verified=m.validate(repo,cfg,{k:v for k,v in proofs.items()if k!=variable},{k:v for k,v in actuals.items()if k!=variable},product)
    p=proofs[variable];d=actuals[variable]
    assert p['head']==d['qualification_commit']==config['terminal_failure_head']=='5bf4e03a37418545655f07a52582103348b17cd4'
    assert p['status']==d['status']=='INCOMPLETE'and d['production_go']is d['independent_acceptance']is False
    for key in('cp6_restored','advisor_gate','baseline_full22_all_rows_all_sequences_equal','baseline_advisors_equal','restore_raw_public_equal'):assert d[key]is True,key
    source=json.loads((repo/config['terminal_source']).read_bytes());assert d['source_declaration']['qualification']==source
    assert d['source_declaration']['current_installation']==product.sources()
    for path,digest in source['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    case=d['committed']['CURRENT_FROZEN_PRIVATE_FACTORY_1200X3_ACTUAL_MINUTE_OFFICIAL_FINANCE'];f=case['factory_fixture']
    assert f['status']=='PASS'and f['commercial_skus']==1200 and f['variants']==3600
    assert f['current_native_membership_verified']and f['current_membership_posted_history_guard']['all_rows_exact']
    assert not f['current_membership_posted_history_guard']['historical_sales_relabelled']
    assert len(case['observed_job_states'])==2 and set(case['observed_job_states'].values())=={'FAILED'}and case['observed_finance_state']=='FAILED'
    assert case['all_runs_recorded']and case['schedules_removed_and_unrelated_jobs_unchanged']
    assert 'terminal_diagnostics'not in case
    sources['terminal_factory']=source;verified[variable]=dict(p,observed_status='INCOMPLETE',diagnostic_gap_preserved=True)
    return sources,verified

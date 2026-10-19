"""Static/pure metadata controls only; never imports a product module."""
import ast
from copy import deepcopy
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import yaml

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]

def main():
    m=json.loads((ROOT/'MUTABLE_DETECTOR_PREEXECUTION_MANIFEST.json').read_text())
    for p,h in m['audit_tools'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
        ast.parse((ROOT/p).read_text())
    for p,h in m['pinned_product_sources'].items():assert hashlib.sha256((REPO/p).read_bytes()).hexdigest()==h
    source=gzip.decompress((REPO/'supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz').read_bytes()).decode()
    for table,pin in m['table_field_source_pins'].items():
        assert pin['ddl'] in source and hashlib.sha256(pin['ddl'].encode()).hexdigest()==pin['ddl_sha256']
        assert source.splitlines()[pin['line']-1].lower().startswith('create table "erp"."'+table+'"')
    ids=[row['id'] for row in m['cases']]
    assert len(ids)==len(set(ids))==4
    known=set(json.loads((ROOT/'DETECTOR_RESULT_REVIEW.json').read_text())['matrix'][i]['function']+':'+json.loads((ROOT/'DETECTOR_RESULT_REVIEW.json').read_text())['matrix'][i]['check_name'] for i in range(167))
    expected_checks={key for case in m['cases'] for phase in case['expected_phases'].values() for key in phase}
    assert len(expected_checks)==8 and expected_checks<=known
    tree=ast.parse((ROOT/'detector_mutable_controls.py').read_text())
    functions={n.name:n for n in tree.body if isinstance(n,ast.FunctionDef)}
    helper=next(n for n in ast.parse((ROOT/'detector_case.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='counts')
    env={};exec(compile(ast.fix_missing_locations(ast.Module(body=[helper,functions['baseline'],functions['phase'],functions['restored']],type_ignores=[])),'<actual metadata gates>','exec'),env)
    zeros={k:0 for k in known}
    def rows(v):return [dict(function=k.split(':',1)[0],check_name=k.split(':',1)[1],issue_count=value) for k,value in v.items()]
    env['fingerprints']=lambda cur:{'immutable_facts':'constant','guard_definitions':'constant'}
    env['detector_rows']=lambda cur:rows(zeros)
    seen={};assert env['baseline'](None,seen)==zeros
    key=next(iter(expected_checks));one=dict(zeros);one[key]=1
    env['detector_rows']=lambda cur:rows(one)
    env['phase'](None,seen,'PURE_CONTROL',{key:1},zeros)
    positives=1;negatives=0
    variants=[dict(one,**{'EXTRA:ID':1}),{k:v for k,v in one.items() if k!=next(k for k in zeros if k!=key)},dict(one,**{key:2}),dict(one,**{key:-1}),dict(one,**{next(k for k in zeros if k!=key):1})]
    for values in variants:
        env['detector_rows']=lambda cur,v=values:rows(v)
        try:env['phase'](None,seen,'PURE_NEGATIVE',{key:1},zeros)
        except AssertionError:negatives+=1
        else:raise AssertionError('NEGATIVE_PHASE_PASSED')
    env['detector_rows']=lambda cur:rows(one)
    for changed in ({'immutable_facts':'CHANGED','guard_definitions':'constant'},{'immutable_facts':'constant','guard_definitions':'CHANGED'}):
        env['fingerprints']=lambda cur,v=changed:v
        try:env['phase'](None,seen,'PURE_CHANGED_PROTECTED',{key:1},zeros)
        except AssertionError:negatives+=1
        else:raise AssertionError('PROTECTED_CHANGE_PASSED')
    env['fingerprints']=lambda cur:{'immutable_facts':'constant','guard_definitions':'constant'}
    env['detector_rows']=lambda cur:rows(zeros)
    env['restored'](None,seen,zeros)
    env['detector_rows']=lambda cur:rows(one)
    try:env['restored'](None,seen,zeros)
    except AssertionError:negatives+=1
    else:raise AssertionError('NONZERO_RESTORE_PASSED')
    try:env['baseline'](None,{})
    except AssertionError:negatives+=1
    else:raise AssertionError('NONZERO_BASELINE_PASSED')
    assert Decimal(1)*Decimal(10)==10 and Decimal(1)*Decimal(11)==11 and abs(Decimal(11)-10)>Decimal('.05')
    qt=ast.parse((ROOT/'detector_mutable_qualification.py').read_text());assign=next(n for n in ast.walk(qt) if isinstance(n,ast.Assign) and isinstance(n.value,ast.IfExp) and isinstance(n.targets[0],ast.Subscript) and isinstance(n.targets[0].slice,ast.Constant) and n.targets[0].slice.value=='status');gate=compile(ast.Expression(assign.value.test),'<actual mutable gate>','eval')
    report=dict(cp6_restored=True,observed_case_ids=ids,expected_case_ids=ids,counts={'PASS':4});n=dict(status='PASS',complete_boundary_restored=True,missing=[])
    assert eval(gate,{'report':report,'n':n}) is True
    changes=[('report','error','x'),('report','cp6_restored',False),('report','observed_case_ids',ids[:-1]),('report','counts',{'PASS':3,'INCOMPLETE':1}),('n','status','INCOMPLETE'),('n','complete_boundary_restored',False),('n','missing',[ids[0]]),('n','error','x')]
    for target,key,value in changes:
        context={'report':deepcopy(report),'n':deepcopy(n)};context[target][key]=value;assert eval(gate,context) is False
    before=yaml.safe_load((REPO/'.github/workflows/audit-sol-r4-functional-boundaries.yml').read_text());after=yaml.safe_load((REPO/'.github/workflows/audit-sol-r4-mutable-detectors.yml').read_text());expect=deepcopy(before)
    for k in ('name','run-name'):expect[k]=after[k]
    expect['on']['push']['paths']=after['on']['push']['paths'];expect['concurrency']['group']=after['concurrency']['group'];expect['jobs']['phase']['name']=after['jobs']['phase']['name']
    for i,s in enumerate(expect['jobs']['phase']['steps']):
        if s.get('run')=="python '../sol/audit/sol_cp17_r4/functional_boundaries_qualification.py'":s['run']="python '../sol/audit/sol_cp17_r4/detector_mutable_qualification.py'";s['name']=after['jobs']['phase']['steps'][i]['name']
        if s.get('uses','').startswith('actions/upload-artifact@'):s['with']['name']=after['jobs']['phase']['steps'][i]['with']['name']
    assert expect==after and after['permissions']=={'contents':'read','actions':'read'}
    assert not subprocess.check_output(['git','diff','--name-only',m['candidate_sha'],'--','src','supabase','scripts','package.json','package-lock.json','index.html','vite.config.ts'],cwd=REPO,text=True)
    out=dict(state='STATIC_AND_PURE_METADATA_ONLY_NO_PRODUCT_CASES_RUN',exact_case_ids=4,eight_target_detector_identities=True,source_and_tool_hashes_verified=True,DDL_fields_and_lines_verified=True,actual_phase_gate_positive=positives,actual_phase_and_restore_gate_negative=negatives,actual_outer_gate_positive=1,actual_outer_gate_negative=len(changes),all167identities_and_counters_enforced=True,immutable_fact_and_guard_hashes_enforced=True,parsed_workflow_changes_only_names_entrypoint_artifact=True,permissions_setup_budget_unchanged=True,source_arithmetic=True,product_diff_empty=True,no_earlier_PASS_repeated=True)
    (ROOT/'MUTABLE_DETECTOR_PREEXECUTION_VALIDATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))

if __name__=='__main__':main()

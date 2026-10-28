"""Local source/original admission controls; never a database/runtime PASS."""
from pathlib import Path
from copy import deepcopy
import argparse
import ast
import importlib.util
import json
import shutil
import subprocess
import tempfile
import yaml

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def run(original):
    guard=load('factory_date2_guard',HERE/'source_guard.py')
    evidence=load('factory_date2_evidence',HERE/'evidence.py')
    config=json.loads((HERE/'CONFIG.json').read_bytes())
    actual=json.loads(Path(original).read_bytes())
    bound=guard.source_binding()
    assert evidence.validate_fixture_provenance(config,actual)
    refused=[]
    def reject(name,operation):
        try:operation()
        except (AssertionError,KeyError):refused.append(name)
        else:raise AssertionError('NEGATIVE_CONTROL_ACCEPTED:'+name)
    cases=[('wrong_executed_path',lambda c,d:c.update(fixture_path='scripts/current-factory-finance-qualification/fixture.py')),
        ('wrong_fixture_sha',lambda c,d:c.update(fixture_sha256='6dceb87ae35bb87527eba3176f80b292e5ab9ef2a4a4b5a813bf6d3f3097724e')),
        ('wrong_head',lambda c,d:d.update(qualification_commit='0'*40)),
        ('missing_executed_pin',lambda c,d:d['source_declaration']['qualification']['files'].pop(config['fixture_path']))]
    key='CURRENT_FACTORY_1200X3_ACTUAL_MINUTE_OFFICIAL_FINANCE'
    for name,mutate in cases:
        c,d=deepcopy(config),deepcopy(actual);mutate(c,d)
        reject(name,lambda:evidence.validate_fixture_provenance(c,d))
    for name,field,value in [('missing_history_table','tables',[]),('history_rewritten','all_rows_exact',False),('sales_relabelled','historical_sales_relabelled',True)]:
        d=deepcopy(actual);d['committed'][key]['factory_fixture']['current_membership_posted_history_guard'][field]=value
        reject(name,lambda:evidence.validate_fixture_provenance(config,d))
    with tempfile.TemporaryDirectory(prefix='factory-date2-guard-')as temp:
        target=Path(temp)
        for name in ('CONFIG.json','fixture.py','runner.py','probe.py'):shutil.copyfile(HERE/name,target/name)
        saved=guard.HERE;guard.HERE=target
        try:
            raw=(REPO/'scripts/current-frozen-finance-factory-qualification/fixture.py').read_bytes()
            (target/'fixture.py').write_bytes(raw)
            reject('old_sibling_fixture',guard.source_binding)
            forged=deepcopy(config);forged['fixture_sha256']='6dceb87ae35bb87527eba3176f80b292e5ab9ef2a4a4b5a813bf6d3f3097724e'
            (target/'CONFIG.json').write_text(json.dumps(forged))
            reject('old_sibling_and_repinned_config',guard.source_binding)
            shutil.copyfile(HERE/'fixture.py',target/'fixture.py');shutil.copyfile(HERE/'CONFIG.json',target/'CONFIG.json')
            for name,filename,old,new in [('relaxed_deadline','runner.py','started+300','started+3000'),
                ('relaxed_metrics','runner.py','len(wanted)==24','len(wanted)>=1'),
                ('relaxed_restore','probe.py',"assert drill.data_hashes(database.SOURCE)==pre_data",'assert True')]:
                raw=(HERE/filename).read_text();assert old in raw
                (target/filename).write_text(raw.replace(old,new,1));reject(name,guard.source_binding)
                (target/filename).write_text(raw)
            assert guard.source_binding()==bound
        finally:guard.HERE=saved
    assert len(refused)==12
    for path in HERE.glob('*.py'):ast.parse(path.read_bytes())
    workflow=yaml.safe_load((REPO/'.github/workflows/cp7-current-frozen-finance-factory-date2.yml').read_text())
    shell=0
    for step in workflow['jobs']['p21']['steps']:
        if 'run'in step:
            result=subprocess.run(['bash','-n'],input=step['run'],text=True,capture_output=True)
            assert result.returncode==0,(step.get('name'),result.stderr);shell+=1
    assert workflow['on']['push']['branches']==['astra-a/d17-14-frozen-finance-factory2-20261026']
    return dict(status='LOCAL_SOURCE_PREFLIGHT_PASS',retained_source=bound,negative_controls=refused,
        shell_steps_checked=shell,actual_fixture_provenance_verified=True,
        runtime_qualified=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--original',required=True);args=parser.parse_args()
    print(json.dumps(run(args.original),indent=2))

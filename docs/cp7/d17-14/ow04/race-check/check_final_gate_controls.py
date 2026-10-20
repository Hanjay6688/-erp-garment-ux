"""Synthetic CI-control checks only; no product/Auth/DB/runtime case runs."""
from pathlib import Path
import copy,hashlib,json,sys,tempfile
REPO=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(REPO/'scripts/ow04-qualification'))
import qualification_gate as gate


def main():
    folder=REPO/'scripts/ow04-qualification'
    binding=json.loads((folder/'QUALIFIED_CORE.json').read_text())
    candidate='synthetic-qualification-gate-only'
    h='t3/CP7_OW04_HTTP.json';r='t3/CP7_OW04_RACES.json'
    hp='ow04-http-completed/T3_PACKAGE_INSTALL.json';rp='t3/T3_PACKAGE_INSTALL.json'
    base={};success={'HTTP':'success','RACES':'success'}
    for file,key,decl,count in ((h,'http','EXPECTED.json',8),(r,'races','RACE_EXPECTED.json',6)):
        ids=[c['id']for c in json.loads((folder/decl).read_text())['cases']]
        runtime=dict(status='RUN_COMPLETE',counts={'PASS':count},database_remaining=0,
            **{'cases'if key=='http'else'races':{i:dict(status='PASS')for i in ids}})
        if key=='http':runtime.update(auth_counts=dict(restored=True),cleanup_failures=[])
        base[file]=dict(status='PASS',candidate_commit=candidate,core_directory_tree=binding['core_directory_tree'],
            native_probe_blob=binding['native_probe_blob'],expected_case_count=count,observed_case_count=count,
            cp6_restored=True,advisor_gate=True,**{key:runtime})
    for file in(hp,rp):
        base[file]=dict(mode='install',status='ALL_STAGES_INSTALLED',gate={k:True for k in
            ('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')})
    mutations=[
        ('HTTP7_PLUS_INCOMPLETE',lambda x:x[h]['http'].update(counts={'PASS':7,'INCOMPLETE':1})),
        ('RACE5_PLUS_INCOMPLETE',lambda x:x[r]['races'].update(counts={'PASS':5,'INCOMPLETE':1})),
        ('CANDIDATE_CHANGED',lambda x:x[h].update(candidate_commit='other')),
        ('CORE_CHANGED',lambda x:x[r].update(core_directory_tree='other')),
        ('RESTORE_FALSE',lambda x:x[h].update(cp6_restored=False)),
        ('ADVISOR_FALSE',lambda x:x[r].update(advisor_gate=False)),
        ('AUTH_FALSE',lambda x:x[h]['http']['auth_counts'].update(restored=False)),
        ('AUTH_CLEANUP_FAILED',lambda x:x[h]['http'].update(cleanup_failures=['synthetic-user'])),
        ('DB_REMAINS',lambda x:x[r]['races'].update(database_remaining=1)),
        ('FORGED_COUNTS_WRONG_ROW',lambda x:next(iter(x[r]['races']['races'].values())).update(status='INCOMPLETE')),
        ('MISSING_CASE',lambda x:x[h]['http']['cases'].pop(next(iter(x[h]['http']['cases'])))),
        ('MISSING_REPORT',lambda x:x.pop(r)),
        ('MISSING_HTTP_PACKAGE',lambda x:x.pop(hp)),
        ('MISSING_RACE_PACKAGE',lambda x:x.pop(rp)),
        ('HTTP_OUTER_BACKUP_FAILED_WITH_INNER_PASS',lambda x:x[hp]['gate'].update(backup_restore_drill=False)),
        ('RACE_OUTER_PRIMARY_CHANGED_WITH_INNER_PASS',lambda x:x[rp]['gate'].update(primary_unchanged=False)),
        ('RACE_OUTER_ADVISOR_FAILED',lambda x:x[rp]['gate'].update(security_advisors=False)),
        ('OUTER_RUNTIME_FAILED',lambda x:x[rp]['gate'].update(writer_runtime=False)),
        ('OUTER_GATE_MISSING_KEY',lambda x:x[hp]['gate'].pop('primary_unchanged')),
        ('OUTER_TRUTHY_INTEGER_NOT_TRUE',lambda x:x[rp]['gate'].update(primary_unchanged=1))]
    results=[]
    with tempfile.TemporaryDirectory(prefix='ow04-ci-gate-')as temp:
        home=Path(temp);root=home/'t3'
        def write(value):
            for p in home.rglob('*.json'):p.unlink()
            for name,v in value.items():
                p=home/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v))
        write(base);assert gate.require(root,candidate,success)['status']=='PASS'
        results.append(dict(case='SYNTHETIC_COMPLETE14_AND_OUTER_GATES_ACCEPTED',status='PASS'))
        for name,mutate in mutations:
            value=copy.deepcopy(base);mutate(value);write(value)
            try:gate.require(root,candidate,success)
            except Exception as error:results.append(dict(case=name,status='PASS',refused=str(error)))
            else:raise AssertionError('FALSE_GREEN_'+name)
        write(base)
        for name,outcome in [('HTTP_COMMAND_FAILED',dict(HTTP='failure',RACES='success')),
            ('RACE_COMMAND_FAILED',dict(HTTP='success',RACES='failure')),('COMMAND_OUTCOMES_MISSING',None)]:
            try:gate.require(root,candidate,outcome)
            except Exception as error:results.append(dict(case=name,status='PASS',refused=str(error)))
            else:raise AssertionError('FALSE_GREEN_'+name)
    report=dict(classification='SYNTHETIC_CI_GATE_CONTROLS_NOT_PRODUCT_AUTH_NATIVE_HTTP_OR_RACE_EXECUTION',
        controls=len(results),results=results,gate_sha256=hashlib.sha256((folder/'qualification_gate.py').read_bytes()).hexdigest(),
        control_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),runtime_cases_executed=0,db_connections=0)
    Path(__file__).with_name('FINAL_GATE_CONTROLS.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(synthetic_gate_controls=len(results),all_pass=True,db_connections=0)))


if __name__=='__main__':main()

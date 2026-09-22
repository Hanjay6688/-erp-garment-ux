"""Read-only security advisor delta across the committed AN, AO, AP catalogs."""
import json,subprocess
import psycopg
import cp6_ao_ap_runtime as runtime
from cp6_ao_ap_inventory import data,platform,inventory

def run(url,stage,path,prior=None):
    with psycopg.connect(url) as conn,conn.cursor() as cur:
        runtime.verified(cur,stage);before=(data(cur),platform(cur),inventory(cur))
    version=subprocess.check_output(['supabase','--version'],text=True).strip();assert version=='2.116.0'
    process=subprocess.run(['supabase','db','advisors','--db-url',url,'--type','security','--level','info','--fail-on','none','--output-format','text','--agent','no'],capture_output=True,text=True,timeout=90)
    assert process.returncode==0,'ADVISORS_COMMAND_FAILED'
    if process.stdout.strip():findings=json.loads(process.stdout)
    else:
        assert 'No issues found' in process.stderr.splitlines(),'ADVISORS_MISSING_RESULT';findings=[]
    assert isinstance(findings,list) and all(isinstance(x,dict) and x.get('name') and x.get('level') for x in findings)
    with psycopg.connect(url) as conn,conn.cursor() as cur:
        runtime.verified(cur,stage);assert (data(cur),platform(cur),inventory(cur))==before,'ADVISORS_CHANGED_BOUNDARY'
    report=dict(stage=stage,status='BASELINE_RECORDED',findings=findings,boundary_unchanged=True,cli_version=version,production_go=False,independent_acceptance=False)
    if prior is not None:
        key=lambda x:json.dumps(x,sort_keys=True)
        baseline={key(x) for x in prior['findings']};added=[x for x in findings if key(x) not in baseline]
        p=runtime.pins()['families'][stage];private=set(p['new_tables'])|{p['capsule'].split('.')[1]}
        reviewed=[];unexpected=[]
        for f in added:
            m=f.get('metadata') or {}
            if f['name']=='rls_enabled_no_policy' and f['level']=='INFO' and m.get('schema')=='erp' and m.get('name') in private:reviewed.append(f)
            else:unexpected.append(f)
        report.update(status='PASS_REVIEWED_DELTA' if not unexpected else 'REVIEW_REQUIRED',new_findings=unexpected,reviewed_private_rls_information=reviewed,prior_findings_preserved=prior['findings'])
    path.write_text(json.dumps(report,indent=2)+'\n');assert report['status']!='REVIEW_REQUIRED',report['new_findings'];return report

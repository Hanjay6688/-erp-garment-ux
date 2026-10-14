"""Execute unchanged historical SQL/race programs once on separate FULL clones.

The historical dispatcher is not bypassed or represented as current acceptance.
These four declared program executions are separate from per-case business
credit. Their original stdout, exit, fixture failures and cleanup are retained.
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys,traceback
import psycopg
sys.path.insert(0,str(Path(__file__).resolve().parent))
import full_stack
import cp6_auditor_modes as modes
import cp6_auditor_runner as native
PROGRAMS=['supabase/tests/cutting_bridge_persistence_pickup_wip_rollback.sql','supabase/tests/cp5_bs_resolution_recovery_rollback.sql','supabase/tests/cp5_rework_accessory_lineage_rollback.sql','scripts/cp5_bs_resolution_concurrency.py']

def run():
    report=dict(label='ASTRA_CP17_CP5_EXACT',status='INCOMPLETE',programs=[],business_case_credit=0,oracle_origin='INHERITED_UNCHANGED',production_go=False)
    try:
        with full_stack.installed(report) as verify:
            for index,name in enumerate(PROGRAMS):
                database='cp6_auditor_cp5_exact_'+str(index);source=full_stack.PRODUCT/name
                row=dict(id='CP17-CP5-EXACT-'+str(index+1),source=name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),status='INCOMPLETE')
                try:
                    url=modes.copy_db(database)
                    with psycopg.connect(url)as conn,conn.cursor()as cur:
                        row['runtime_before']=verify(cur);row['app_users_before']=cur.execute('select count(*)from erp.app_users').fetchone()[0];conn.rollback()
                    env=dict(os.environ,PGURL=url,CP5_BS_RESOLUTION_RACE_REPORT=str(full_stack.OUT/'CP5_EXACT_RACE_ORIGINAL.json'))
                    cmd=['psql',url,'-X','-v','ON_ERROR_STOP=1','-f',str(source)]if source.suffix=='.sql'else[sys.executable,str(source)]
                    done=subprocess.run(cmd,cwd=full_stack.PRODUCT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=900)
                    row.update(exit_code=done.returncode,complete_stdout=done.stdout,status='PASS'if done.returncode==0 else'INCOMPLETE')
                    with psycopg.connect(url)as conn,conn.cursor()as cur:
                        row['runtime_after']=verify(cur);row['remaining_sessions']=modes.copy_sessions(database);conn.rollback()
                except Exception as exc:row.update(error=str(exc),traceback=traceback.format_exc())
                finally:row['database_remaining']=modes.drop_db(database)
                report['programs'].append(row);full_stack.save(report['label'],report)
    except Exception as exc:report.update(error=str(exc),traceback=traceback.format_exc())
    report['status']='PASS'if len(report['programs'])==4 and all(x['status']=='PASS'and x['database_remaining']==0 for x in report['programs'])and report.get('cp6_restored')and report.get('advisor_gate')else'INCOMPLETE'
    full_stack.save(report['label'],report)
    print(json.dumps({k:report.get(k)for k in('label','status','error','cp6_restored','advisor_gate')}),flush=True)
    return dict(status=report['status'],production_go=False)

if __name__=='__main__':
    full_stack.package._writer_runtime=lambda browser_mode=False:run()
    full_stack.package.run('install')

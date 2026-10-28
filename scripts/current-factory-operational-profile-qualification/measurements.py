"""Measure current frozen compilation and unit zero; roll every call back."""
from pathlib import Path
from time import monotonic
from hashlib import sha256
from urllib.parse import urlparse
import importlib.util,json,uuid,psycopg
ROOT=Path(__file__).resolve().parents[2]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
factory=load('current_profile_exact_factory_fixture',ROOT/'scripts/current-finance-factory-progress-followup-qualification/factory.py')
product=load('current_profile_exact_product',ROOT/'scripts/current-finance-factory-progress-followup-qualification/composition.py')
finance=factory.finance
def functions(cur):
    return {r[0]:dict(calls=r[1],total_ms=r[2],self_ms=r[3]) for r in cur.execute("""
        select funcid::regprocedure::text,calls,total_time,self_time
        from pg_stat_xact_user_functions where calls>0 order by funcid::regprocedure::text
    """).fetchall()}

def difference(before,after):
    out=[]
    for name,row in after.items():
        previous=before.get(name,{k:0 for k in row})
        delta={k:row[k]-previous[k]for k in row}
        if delta['calls'] or delta['total_ms'] or delta['self_ms']:
            out.append(dict(function=name,**delta))
    return sorted(out,key=lambda r:(-r['self_ms'],r['function']))

def measure(admin_url,name,statement,args,*,limit_ms,read_only):
    """No retry and no accepted runtime credit, including when the call succeeds."""
    u=urlparse(admin_url)
    assert u.hostname in ('localhost','127.0.0.1') and u.port==54322 and u.path=='/cp6_rollback'
    result=dict(name=name,status='INCOMPLETE',statement_limit_ms=limit_ms,
                diagnostic_only=True,performance_qualification=False,retries=0,
                statement_sha256=sha256(statement.encode()).hexdigest(),read_only=read_only)
    with psycopg.connect(admin_url)as conn,conn.cursor()as cur:
        if read_only:cur.execute('set local transaction read only')
        cur.execute("set local track_functions='all'")
        cur.execute("set local lock_timeout='2s'")
        cur.execute("select set_config('statement_timeout',%s,true)",(str(limit_ms),))
        with finance.finance.as_capture(cur):
            before=functions(cur)
            cur.execute('savepoint measured_call')
            started=monotonic()
            try:
                value=cur.execute(statement,args,prepare=False).fetchone()[0]
                result.update(status='COMPLETED_DIAGNOSTIC',elapsed_ms=round((monotonic()-started)*1000,3))
                body=json.dumps(value,sort_keys=True,default=str).encode()
                result.update(result_bytes=len(body),result_sha256=sha256(body).hexdigest())
                if name=='OFFICIAL_FINANCE_REPORT_UNIT':
                    result['server_report_ms']=value['server_ms']
                    result['provenance_row_counts']=value['rows']
                    result['official_snapshot_sections']=sorted(value['report']['snapshot'])
            except psycopg.Error as error:
                result.update(status='CANCELED_DIAGNOSTIC'if error.sqlstate=='57014'else'ERROR_DIAGNOSTIC',
                    elapsed_ms=round((monotonic()-started)*1000,3),sqlstate=error.sqlstate,
                    message=error.diag.message_primary,context=error.diag.context)
            finally:
                # Restores role/claims and all work rows after success or SQL error.
                cur.execute('rollback to savepoint measured_call')
                result['functions']=difference(before,functions(cur))
                cur.execute('release savepoint measured_call')
        conn.rollback()
    result['all_measured_effects_rolled_back']=True
    return result

def exercise(conn,cur,database_module,admin_url,report):
    assert conn.info.host in('localhost','127.0.0.1')and conn.info.port==54322
    assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
    granted,_=database_module._foundation(cur)
    today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
    finance.setup(cur,today);factory.factory.seed(conn,cur,today,report.setdefault('factory_fixture',{}))
    key=str(uuid.uuid4());started=monotonic();job=finance.request(cur,today,key)
    report['ordinary_request_and_identity_checks_ms']=round((monotonic()-started)*1000,3)
    capture=finance.sidecar(job,key,'RUNNING')['capture']['capture_id']
    finance.staged.b.api.admin(cur)
    if granted:cur.execute('revoke usage on schema erp from authenticated')
    conn.commit();_,_,_,_,catalog=product.runtime()
    before_data=catalog._data(cur);before_catalog=catalog._catalog_rows(cur);conn.rollback()
    report.update(diagnostic_only=True,actual_cron_claim=False,manual_committed_steps=0,product_timeout_changed=False,
        performance_qualification=False,production_go=False,request_id=key,capture_id=capture,measurements=[])
    calls=[
      ('FIRST_OPERATIONAL_UNIT',"select cp7_analysis_stage.run_unit(j,u)from cp7_analysis_stage.jobs j join cp7_analysis_stage.units u on u.job_id=j.id and u.idx=0 where j.request_id=%s",(key,),30000,False),
      ('FROZEN_INPUT_COMPILER',"select cp7_frozen_analysis_v2.prepare(j.reference,j.query,(cp7_analysis_stage.bounds()->>'job_targets')::integer)from cp7_analysis_stage.jobs j where j.request_id=%s",(key,),30000,True),
      ('SMALL_STATUS_READ','select cp7_analysis_stage.status(j.id)from cp7_analysis_stage.jobs j where j.request_id=%s',(key,),8000,True)]
    for name,statement,args,limit,readonly in calls:
        result=measure(admin_url,name,statement,args,limit_ms=limit,read_only=readonly);report['measurements'].append(result)
        assert catalog._data(cur)==before_data and catalog._catalog_rows(cur)==before_catalog;conn.rollback()
        print(json.dumps({k:result.get(k)for k in('name','status','elapsed_ms','sqlstate')},default=str),flush=True)
    assert cur.execute('select state,units_done,unit_attempts from cp7_analysis_stage.jobs where request_id=%s',(key,)).fetchone()==('RUNNING',0,0)
    assert cur.execute('select state,units_done,unit_attempts from cp7_finance_capture.captures where id=%s',(capture,)).fetchone()==('RUNNING',0,0)
    assert all(m['status']in('COMPLETED_DIAGNOSTIC','CANCELED_DIAGNOSTIC')for m in report['measurements'])
    assert report['measurements'][-1]['status']=='COMPLETED_DIAGNOSTIC'
    conn.rollback()
    report.update(status='PASS',diagnostic_collection_completed=True,all22_all_rows_and_sequences_unchanged_by_measurements=True,
        stored_job_and_capture_progress_unchanged=True,factory_native_finance_qualified=False,previous_factory_failures_remain_INCOMPLETE=True)

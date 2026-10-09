"""Independent P20 staged/retention/cleanup oracles. See the preregistered matrix.
Fixture origin: writer Native setup helpers, unchanged candidate.
Oracle origin: Astra contract-derived checks below, not writer verdicts.
"""
import hashlib,json,time,traceback,uuid
from datetime import timedelta
from pathlib import Path
import psycopg
from psycopg import sql
import cp7_p19_staged_cases as seed
import cp7_p19_plan_v2_cases as plan
import cp7_p19_report_v2_cases as report
import cp7_p19_ai_v2_cases as ai
import cp7_p19_reminder_v2_cases as rem

ROOT=Path(seed.__file__).resolve().parents[1]/'cp6-proof/t3'
TEMP=('outputs','target_rows','pair_rows','pair_lists','fragments')
KEPT_JOB=('jobs','units','capture_marks','plan_targets','plan_scope','plan_groups')
KEPT_RUN=('headers','pages','page_sets')
class ContractMismatch(Exception):pass

def check(ok, message, **witness):
    if not ok:raise ContractMismatch(json.dumps(dict(message=message,**witness),default=str))

def admin(cur):seed.b.api.admin(cur)
def save(name, data):
    ROOT.mkdir(parents=True,exist_ok=True)
    (ROOT/('ASTRA_'+name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2,default=str)+'\n')

def api(cur,name,*args,subject=None):
    # Transport/actor helper only. The independent oracle never calls seed.checked/fetch/drive.
    return seed.limited(cur,name,args,subject)

def refusal(cur,op):
    admin(cur);cur.execute('savepoint astra_refusal')
    try:
        result=op();got=dict(refused=False,result=result)
    except psycopg.Error as e:
        got=dict(refused=True,sqlstate=e.sqlstate,message=e.diag.message_primary,detail=e.diag.message_detail)
    finally:
        cur.execute('rollback to savepoint astra_refusal');admin(cur);cur.execute('release savepoint astra_refusal')
    return got

def new_run(cur,today,subject=None,setup=True):
    fixture=plan.fixture(cur,today) if setup else None
    key=uuid.uuid4();q=seed.query(today)
    first=api(cur,'erp_cp7_request_staged_analysis_v1',json.dumps(q),key,subject=subject)
    check(first.get('state')=='RUNNING' and first.get('run_id') is None,'No premature completed result',first=first)
    log=[];last=first
    for _ in range(20000):
        if last['state']!='RUNNING':break
        start=time.monotonic();last=api(cur,'erp_cp7_step_staged_analysis_v1',key,subject=subject)
        log.append(dict(state=last['state'],stage=last.get('stage'),units=last['units_done'],ms=(time.monotonic()-start)*1000))
    save('stage_calls_'+key.hex,log)
    check(last['state']=='DONE','Staged job must finish',last=last)
    admin(cur)
    job=cur.execute('select id::text from cp7_analysis_stage.jobs where request_id=%s',(key,)).fetchone()[0]
    return dict(key=key,job=job,run=last['run_id'],q=q,fixture=fixture,subject=subject,calls=log)

def read_pages(cur,r):
    ps=api(cur,'erp_cp7_read_staged_analysis_pages_v1',r['run'],subject=r.get('subject'))
    h=ps['header'];raw=h['body'].encode('utf8')
    check(hashlib.sha256(raw).hexdigest()==h['sha256'] and len(raw)==h['utf8_bytes']<=8_000_000,'Header byte identity')
    parsed=json.loads(h['body']);bodies=[];next_target=1
    check(len(ps['pages'])==ps['page_count'],'Complete page index')
    for index,p in enumerate(ps['pages']):
        check(p['index']==index and p['target_lo']==next_target,'Contiguous ordered targets',entry=p,next_target=next_target)
        envelope=api(cur,'erp_cp7_read_staged_analysis_page_v1',r['run'],index,ps['access_epoch'],subject=r.get('subject'))
        body=envelope['body'].encode('utf8')
        check(len(body)==p['utf8_bytes']==envelope['utf8_bytes']<=8_000_000,'Page UTF8 byte length')
        check(hashlib.sha256(body).hexdigest()==p['sha256']==envelope['sha256'],'Page body hash')
        value=json.loads(body)
        check(value['target_lo']==p['target_lo'] and value['target_hi']==p['target_hi'],'Page origin/range')
        bodies.append(value);next_target=p['target_hi']+1
    check(next_target-1==ps['targets_total'],'Every target covered exactly once',covered=next_target-1,total=ps['targets_total'])
    calculated=hashlib.sha256((h['sha256']+'\n'+'\n'.join(p['sha256'] for p in ps['pages'])).encode()).hexdigest()
    check(calculated==ps['identity_hash'],'Independent complete result identity')
    return dict(identity=calculated,header=parsed,pages=bodies,index={k:ps.get(k) for k in ('run_id','header','pages','page_count','targets_total','totals','paged','identity_hash')},epoch=ps['access_epoch'])

def digest_rows(cur,schema,table,col=None,val=None):
    admin(cur)
    q=sql.SQL('select to_jsonb(x)::text from {}.{} x').format(sql.Identifier(schema),sql.Identifier(table))
    if col:q+=sql.SQL(' where {}=%s').format(sql.Identifier(col))
    texts=sorted(x[0] for x in cur.execute(q,(val,) if col else ()).fetchall())
    h=hashlib.sha256()
    for x in texts:
        b=x.encode('utf8');h.update(len(b).to_bytes(8,'big'));h.update(b)
    return dict(rows=len(texts),sha256=h.hexdigest())

def retained(cur,r):
    out={}
    for t in KEPT_JOB:
        out[t]=digest_rows(cur,'cp7_analysis_stage',t,'id' if t=='jobs' else 'job_id',r['job'])
    for t in KEPT_RUN:out[t]=digest_rows(cur,'cp7_analysis_stage',t,'run_id',r['run'])
    return out

def temporaries(cur,r):return {t:digest_rows(cur,'cp7_analysis_stage',t,'job_id',r['job']) for t in TEMP}
def clean(cur,r):admin(cur);return cur.execute('select cp7_analysis_stage.clean_done(%s)',(r['job'],)).fetchone()[0]
def tick(cur):admin(cur);return cur.execute('select cp7_ops.cleanup_tick()').fetchone()[0]

def age(cur,r,delta):
    admin(cur);cur.execute('update cp7_analysis_stage.jobs set updated_at=clock_timestamp()-%s where id=%s',(delta,r['job']))

def wrap(case,op):
    def run():
        base=dict(case=case,evidence_origin='INDEPENDENT_NATIVE_CASE',oracle_origin='ASTRA_CONTRACT',fixture_origin='WRITER_SETUP_UNCHANGED',production_go=False)
        try:base.update(status='PASS',observations=op())
        except ContractMismatch as e:base.update(status='COUNTEREXAMPLE',counterexample=str(e),traceback=traceback.format_exc())
        except Exception as e:base.update(status='INCOMPLETE',error=str(e),traceback=traceback.format_exc())
        save(case,base);return base
    return case,run

def cases(cur,today):
    def acl():
        admin(cur)
        rows=cur.execute("""select n.nspname,p.oid::regprocedure::text,role,
          has_schema_privilege(role,n.oid,'USAGE'),has_function_privilege(role,p.oid,'EXECUTE')
          from pg_proc p join pg_namespace n on n.oid=p.pronamespace
          cross join unnest(array['anon','authenticated','service_role'])role
          where n.nspname like 'cp7\\_%' order by 1,2,3""").fetchall()
        exposed=[x for x in rows if x[3] and x[4]]
        tables=cur.execute("""select n.nspname,c.relname,role,has_schema_privilege(role,n.oid,'USAGE'),
         has_table_privilege(role,c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER'),c.relrowsecurity
         from pg_class c join pg_namespace n on n.oid=c.relnamespace
         cross join unnest(array['anon','authenticated','service_role'])role
         where n.nspname like 'cp7\\_%' and c.relkind in('r','p') order by 1,2,3""").fetchall()
        save('AS20-02_ACL_inventory',dict(functions=rows,tables=tables))
        check(bool(rows) and not exposed,'No exposed private callable function',exposed=exposed)
        check(not [x for x in tables if x[3] and x[4]],'No exposed private table',exposed=[x for x in tables if x[3] and x[4]])
        check(all(x[5] for x in tables),'Private tables all RLS enabled')
        return dict(function_role_pairs=len(rows),table_role_pairs=len(tables),runtime_rest_status='SEPARATE_CASE_REQUIRED')

    def preserve():
        r=new_run(cur,today);a=read_pages(cur,r);kept=retained(cur,r);temp=temporaries(cur,r)
        check(any(x['rows'] for x in temp.values()),'Fixture has intermediate work')
        business=seed.b.boundary.snapshot(cur);first=clean(cur,r)
        check(first['state']=='CLEANED','Cleanup performed',result=first)
        after=read_pages(cur,r)
        check(a['index']==after['index'] and a['pages']==after['pages'],'Final pages preserved exactly')
        check(retained(cur,r)==kept,'Every retained row preserved',before=kept,after=retained(cur,r))
        check(all(x['rows']==0 for x in temporaries(cur,r).values()),'Only intermediate work removed')
        check(seed.b.boundary.snapshot(cur)==business,'Cleanup makes no business writes')
        before_second=retained(cur,r);second=clean(cur,r)
        check(second['state']=='ALREADY_CLEANED' and retained(cur,r)==before_second,'Cleanup replay safe')
        statuses=[api(cur,'erp_cp7_get_staged_analysis_v1',r['key']),api(cur,'erp_cp7_step_staged_analysis_v1',r['key'])]
        check(all(x['state']=='DONE' and x['run_id']==r['run'] for x in statuses),'DONE reopening never recomputes')
        check(retained(cur,r)==kept,'DONE read/step changes no final or unit rows')
        log=cur.execute('select count(*) from cp7_analysis_stage.cleanups where job_id=%s',(r['job'],)).fetchone()[0]
        check(log==1,'One immutable cleanup receipt')
        return dict(run=r['run'],before_temporary=temp,retained=kept,identity=a['identity'],repeat=second,log_count=log)

    def guards():
        r=new_run(cur,today);out=[]
        modifications=[
          ('header_body','headers','update cp7_analysis_stage.headers set body=body||chr(32) where run_id=%s',r['run']),
          ('page_body','pages','update cp7_analysis_stage.pages set body=body||chr(32) where run_id=%s',r['run']),
          ('identity','page_sets',"update cp7_analysis_stage.page_sets set identity_hash=repeat('0',64) where run_id=%s",r['run']),
          ('index_missing','plan_targets','delete from cp7_analysis_stage.plan_targets where job_id=%s and ord=1',r['job']),
          ('index_value','plan_targets',"update cp7_analysis_stage.plan_targets set row=jsonb_set(row,'{conditional_gap_pcs}','\"987654321\"'::jsonb) where job_id=%s and ord=1",r['job']),
          ('scope','plan_scope',"update cp7_analysis_stage.plan_scope set scope='{}'::jsonb where job_id=%s",r['job']),
          ('page_range','pages','update cp7_analysis_stage.pages set target_lo=target_lo+1,target_hi=target_hi+1 where run_id=%s',r['run']),
          ('totals','page_sets',"update cp7_analysis_stage.page_sets set totals='{}'::jsonb where run_id=%s",r['run'])]
        for name,table,query,value in modifications:
            admin(cur);cur.execute('savepoint astra_mutant')
            # Deliberately weakened COPY solely to assess detector sensitivity.
            # Ordinary immutable protection is independently tested below.
            cur.execute(sql.SQL('alter table cp7_analysis_stage.{} disable trigger {}').format(sql.Identifier(table),sql.Identifier('immutable_stage_'+table)))
            cur.execute(query,(value,))
            check(cur.rowcount>0,'Negative control actually mutated a row',mutation=name)
            cur.execute(sql.SQL('alter table cp7_analysis_stage.{} enable trigger {}').format(sql.Identifier(table),sql.Identifier('immutable_stage_'+table)))
            before=temporaries(cur,r);got=refusal(cur,lambda:clean(cur,r));after=temporaries(cur,r)
            out.append(dict(mutation=name,intentionally_weakened_copy=True,refusal=got,temporary_unchanged=before==after))
            cur.execute('rollback to savepoint astra_mutant');admin(cur);cur.execute('release savepoint astra_mutant')
        save('AS20-39_negative_controls',out)
        protection=refusal(cur,lambda:cur.execute("update cp7_analysis_stage.plan_targets set row=row where job_id=%s",(r['job'],)))
        check(protection['refused'],'Ordinary immutable rows cannot be tampered with',result=protection)
        clean_ok=clean(cur,r)
        check(clean_ok['state']=='CLEANED','Healthy control after every corruption rollback succeeds')
        gaps=[x for x in out if not x['refusal']['refused'] or not x['temporary_unchanged']]
        check(not gaps,'Cleanup verification must detect invalid retained components',gaps=gaps,scope='DETECTOR_COVERAGE_IN_INTENTIONALLY_WEAKENED_COPY_NOT_PROOF_OF_LIVE_CORRUPTION',ordinary_immutable_guard=protection)
        return dict(controls=out,immutable_guard=protection)

    def rollback_busy():
        r=new_run(cur,today);running=uuid.uuid4()
        api(cur,'erp_cp7_request_staged_analysis_v1',json.dumps(seed.query(today)),running)
        before=temporaries(cur,r);out=tick(cur)
        check(not out['cleaned'] and out.get('deferred') is not None and before==temporaries(cur,r),'Active analysis defers server cleanup',result=out)
        admin(cur);cur.execute("update cp7_analysis_stage.jobs set updated_at=clock_timestamp()-interval'11 minutes' where request_id=%s",(running,))
        cur.execute("create function pg_temp.astra_fail_delete() returns trigger language plpgsql as $$begin raise exception 'ASTRA_INJECTED_DELETE_FAILURE';end$$")
        cur.execute('create trigger astra_fail_delete before delete on cp7_analysis_stage.target_rows for each statement execute function pg_temp.astra_fail_delete()')
        kept=retained(cur,r);failed=tick(cur)
        check(bool(failed['failed']) and not failed['cleaned'],'Injected cleanup fault reported',result=failed)
        check(before==temporaries(cur,r) and kept==retained(cur,r),'Failure rolls back all intermediate deletion and trigger changes')
        cur.execute('drop trigger astra_fail_delete on cp7_analysis_stage.target_rows');cur.execute('drop function pg_temp.astra_fail_delete()')
        retry=tick(cur)
        check(any(x['job_id']==r['job'] for x in retry['cleaned']),'Later scheduled attempt can clean after transient fault',result=retry)
        unfinished=cur.execute('select state from cp7_analysis_stage.jobs where request_id=%s',(running,)).fetchone()[0]
        check(unfinished=='RUNNING','Paused unfinished analysis never deleted')
        return dict(deferred=out,failed=failed,recovery=retry,synthetic_age='RUNNING progress minus11minutes; test only')

    def consumers():
        r=new_run(cur,today);r['identity']=read_pages(cur,r)['identity'];f=r['fixture']
        o,q,p=plan.draft_payload(cur,f,r['run']);draft=plan.save(cur,p)
        a_before=api(cur,'erp_cp7_get_staged_ai_brief_v1',r['run'],json.dumps([f['target']]))
        clean(cur,r)
        ai_after=api(cur,'erp_cp7_get_staged_ai_brief_v1',r['run'],json.dumps([f['target']]))
        keys=('run_id','identity_hash','priority','selected','need_counts','targets_total','totals')
        check({k:a_before[k] for k in keys}=={k:ai_after[k] for k in keys},'AI exact retained values after cleanup')
        check(ai_after['finance']=='NOT_IN_SNAPSHOT' and ai_after['apply_enabled'] is False,'AI brief has no money authority')
        check(len(ai_after['priority'])<=25 and len(ai_after['selected'])<=20,'AI bounded')
        option2=plan.options(cur,q)
        check(o==option2,'Plan options identical after cleanup')
        # Consumer payload/transport fixtures reused; acceptance below checks real terminal state and retained identities.
        report_key=uuid.uuid4();p_report=report.payload(r,title='Astra independent retained result',reason='Independent cleanup consumer audit')
        s=api(cur,'erp_cp7_publish_report_v2',json.dumps(p_report),report_key)
        for _ in range(10000):
            if s['state']!='RUNNING':break
            s=api(cur,'erp_cp7_step_report_v2',report_key)
        check(s['state']=='DONE','Report can seal from retained final result',result=s)
        publication=api(cur,'erp_cp7_read_report_v2',s['publication_id'])
        set_result=None
        for _ in range(10000):
            set_result=api(cur,'erp_cp7_step_reminder_conditions_v2',r['run'])
            if set_result['state']!='RUNNING':break
        check(set_result['state']=='DONE' and set_result['sent'] is False,'Reminder conditions complete locally after cleanup',result=set_result)
        check(read_pages(cur,r)['identity']==r['identity'],'All consumers retain same immutable source')
        return dict(draft=draft,report=publication,reminder=set_result,ai_bound=ai_after['bounds'],run=r['run'])

    def expired():
        r=new_run(cur,today);before=read_pages(cur,r)
        age(cur,r,timedelta(days=7)-timedelta(seconds=30))
        just_before=api(cur,'erp_cp7_get_staged_analysis_v1',r['key'])
        check(just_before['retention']['state']=='KEPT' and read_pages(cur,r)['identity']==before['identity'],'Within retention usable')
        age(cur,r,timedelta(days=7,seconds=30))
        status=api(cur,'erp_cp7_get_staged_analysis_v1',r['key'])
        check(status['retention']['state']=='EXPIRED','After7days status explicit expired',status=status)
        calls=[('pages',lambda:api(cur,'erp_cp7_read_staged_analysis_pages_v1',r['run'])),
          ('page',lambda:api(cur,'erp_cp7_read_staged_analysis_page_v1',r['run'],0,before['epoch'])),
          ('freshness',lambda:api(cur,'erp_cp7_staged_snapshot_freshness_v1',r['run'])),
          ('sourcecheck',lambda:api(cur,'erp_cp7_check_staged_snapshot_v1',r['run'])),
          ('ai',lambda:api(cur,'erp_cp7_get_staged_ai_brief_v1',r['run'],'[]')),
          ('reminder',lambda:api(cur,'erp_cp7_step_reminder_conditions_v2',r['run']))]
        got={name:refusal(cur,op) for name,op in calls}
        check(all(x['refused'] for x in got.values()),'Expired readers/consumers refuse',observed=got)
        check(all('EXPIRED' in x['message'] for x in got.values()),'Expiry is explicit, not generic missing-data error',observed=got)
        running=uuid.uuid4();api(cur,'erp_cp7_request_staged_analysis_v1',json.dumps(seed.query(today)),running)
        admin(cur);cur.execute("update cp7_analysis_stage.jobs set updated_at=clock_timestamp()-interval'12 days' where request_id=%s",(running,))
        check(api(cur,'erp_cp7_get_staged_analysis_v1',running)['retention']['state']=='NOT_FINISHED','Unfinished job never expired')
        return dict(readers=got,boundaries_seconds=30,synthetic_age='updated_at moved only in disposable copy')

    def revoked():
        plan.fixture(cur,today);subject,role=seed.auth.custom_actor(cur)
        r=new_run(cur,today,subject=subject,setup=False);before=read_pages(cur,r)
        admin(cur);cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
        ops=[('old_uuid',lambda:api(cur,'erp_cp7_request_staged_analysis_v1',json.dumps(r['q']),r['key'],subject=subject)),
         ('new_uuid',lambda:api(cur,'erp_cp7_request_staged_analysis_v1',json.dumps(r['q']),uuid.uuid4(),subject=subject)),
         ('status',lambda:api(cur,'erp_cp7_get_staged_analysis_v1',r['key'],subject=subject)),
         ('pages',lambda:api(cur,'erp_cp7_read_staged_analysis_pages_v1',r['run'],subject=subject)),
         ('page',lambda:api(cur,'erp_cp7_read_staged_analysis_page_v1',r['run'],0,before['epoch'],subject=subject)),
         ('ai',lambda:api(cur,'erp_cp7_get_staged_ai_brief_v1',r['run'],'[]',subject=subject)),
         ('freshness',lambda:api(cur,'erp_cp7_staged_snapshot_freshness_v1',r['run'],subject=subject))]
        before_db=retained(cur,r);out={k:refusal(cur,op) for k,op in ops}
        check(all(v['refused'] for v in out.values()),'Current access enforced even for replay/cached reads',results=out)
        check(retained(cur,r)==before_db,'Refused reads/replays make no job/unit change')
        return out

    def tamper():
        r=new_run(cur,today);out={}
        for t in KEPT_RUN+('plan_targets','units','capture_marks','plan_scope','plan_groups'):
            admin(cur)
            got=refusal(cur,lambda t=t:cur.execute(sql.SQL('delete from cp7_analysis_stage.{}').format(sql.Identifier(t))))
            # Some legitimately empty collections have no affected row and cannot prove the trigger.
            n=digest_rows(cur,'cp7_analysis_stage',t)['rows']
            out[t]=dict(rows=n,attempt=got)
            if n:check(got['refused'],'Immutable final/audit facts reject tampering',table=t,result=got)
        return out

    return [wrap('AS20-02_NATIVE_ACL',acl),wrap('AS20-28_38_PRESERVATION',preserve),wrap('AS20-39_VALIDATION_NEGATIVE',guards),
      wrap('AS20-40_ATOMIC_CLEANUP',rollback_busy),wrap('AS20-41_CONSUMERS',consumers),wrap('AS20-37_RETENTION',expired),
      wrap('AS20-01_REPLAY_ACCESS',revoked),wrap('AS20-49_IMMUTABILITY',tamper)]

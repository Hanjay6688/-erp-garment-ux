"""Independent current authority, failed retention and Unicode transport."""
import hashlib,json,uuid
from datetime import timedelta
import cp7_pl5_history_yield_cases as h
import cp7_p19_report_v2_cases as reports
from cases_stage import admin,api,seed,plan,check,wrap,new_run,read_pages,retained,refusal,age,clean,digest_rows

def report_drive(cur,key,subject=None):
    for _ in range(10000):
        s=api(cur,'erp_cp7_step_report_v2',key,subject=subject)
        if s['state']!='RUNNING':return s
    raise RuntimeError('AUDITOR_REPORT_DRIVER_BOUND')

def cases(cur,today):
    def revoke():
        subject,role=seed.auth.custom_actor(cur);r=new_run(cur,today,subject=subject);pages=read_pages(cur,r);r['identity']=pages['identity']
        payload=reports.payload(r,title='Astra independent revoke report');key=uuid.uuid4();api(cur,'erp_cp7_publish_report_v2',json.dumps(payload),key,subject=subject)
        done=report_drive(cur,key,subject);check(done['state']=='DONE','Positive published report before revocation',result=done)
        doc=api(cur,'erp_cp7_read_report_v2',done['publication_id'],subject=subject)
        for _ in range(10000):
            reminder=api(cur,'erp_cp7_step_reminder_conditions_v2',r['run'],subject=subject)
            if reminder['state']!='RUNNING':break
        check(reminder['state']=='DONE','Positive condition set before revocation',result=reminder)
        api(cur,'erp_cp7_get_staged_ai_brief_v1',r['run'],'[]',subject=subject)
        before=retained(cur,r);pubs=digest_rows(cur,'cp7_analysis_stage','report_publications');admin(cur)
        calls=[('cached_request','erp_cp7_request_staged_analysis_v1',(json.dumps(r['q']),r['key'])),('status','erp_cp7_get_staged_analysis_v1',(r['key'],)),('step','erp_cp7_step_staged_analysis_v1',(r['key'],)),('pages','erp_cp7_read_staged_analysis_pages_v1',(r['run'],)),('page','erp_cp7_read_staged_analysis_page_v1',(r['run'],0,pages['epoch'])),('AI','erp_cp7_get_staged_ai_brief_v1',(r['run'],'[]')),('report_replay','erp_cp7_publish_report_v2',(json.dumps(payload),key)),('report','erp_cp7_read_report_v2',(done['publication_id'],)),('report_section','erp_cp7_read_report_section_v2',(done['publication_id'],0,doc['access_epoch'])),('reminders','erp_cp7_step_reminder_conditions_v2',(r['run'],)),('reminder_workspace','erp_cp7_get_reminder_workspace_v2',(r['run'],))]
        for _,fn,args in calls:api(cur,fn,*args,subject=subject)
        admin(cur);cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,))
        out={name:refusal(cur,lambda fn=fn,args=args:api(cur,fn,*args,subject=subject)) for name,fn,args in calls}
        check(all(v['refused'] for v in out.values()),'Every cached/read/consumer entry checks current required permission',refusals=out)
        check(retained(cur,r)==before and digest_rows(cur,'cp7_analysis_stage','report_publications')==pubs,'Denied commands mutate neither snapshot nor published documents')
        return dict(refusals=out,positive_controls=['pages','report','reminders','AI'],retained_unchanged=True)

    def failed():
        plan.fixture(cur,today);actor,role=seed.auth.custom_actor(cur);key=uuid.uuid4();q=seed.query(today)
        first=api(cur,'erp_cp7_request_staged_analysis_v1',json.dumps(q),key,subject=actor)
        check(first['state']=='RUNNING','New job truly runs')
        api(cur,'erp_cp7_step_staged_analysis_v1',key,subject=actor);admin(cur)
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.hpp.view')",(role,))
        fail=api(cur,'erp_cp7_step_staged_analysis_v1',key,subject=actor)
        check(fail['state']=='FAILED' and fail['failure']['code']=='CP7_ANALYSIS_ACCESS_CHANGED' and fail['run_id'] is None,'Real changed access fails incomplete job without forged state',result=fail)
        admin(cur);job=cur.execute('select id::text from cp7_analysis_stage.jobs where request_id=%s',(key,)).fetchone()[0];r=dict(job=job)
        cannot=refusal(cur,lambda:clean(cur,r));check(cannot['refused'],'FAILED must never be cleaned as successful DONE',refusal=cannot)
        age(cur,r,timedelta(days=7,seconds=-30));before=api(cur,'erp_cp7_get_staged_analysis_v1',key,subject=actor)
        check(before['retention']['state']=='KEPT','Failed result still retained just before7days')
        age(cur,r,timedelta(days=7,seconds=30));expired=api(cur,'erp_cp7_get_staged_analysis_v1',key,subject=actor)
        check(expired['retention']['state']=='EXPIRED','Failed result expires just after7days')
        admin(cur);purge=cur.execute('select cp7_analysis_stage.purge_expired(100)').fetchone()[0]
        after=api(cur,'erp_cp7_get_staged_analysis_v1',key,subject=actor)
        check(after['state']=='FAILED' and after['failure']==fail['failure'],'Purge preserves original failure evidence')
        check(api(cur,'erp_cp7_step_staged_analysis_v1',key,subject=actor)['failure']==fail['failure'],'Repeated failed step cannot restart finished work')
        logs=cur.execute('select count(*) from cp7_analysis_stage.retention_log where job_id=%s',(job,)).fetchone()[0]
        check(logs==1,'One retained purge receipt')
        return dict(failure=fail['failure'],before=before['retention'],expired=expired['retention'],purge=purge,cleanup_refused=cannot,cancelled_state='NOT_SUPPORTED_STAGED_STATE; real states RUNNING,DONE,FAILED')

    def unicode():
        label='ไทย🧵é';p=h.product(cur,'AS-'+label);r=new_run(cur,today);proof=read_pages(cur,r)
        strings=[json.dumps(proof['header'],ensure_ascii=False)]+[json.dumps(p,ensure_ascii=False) for p in proof['pages']]
        text='\n'.join(strings)
        check(label in text,'Non-ASCII product label preserved in actual captured output',label=label)
        check(p['target'] in text,'Unicode-labelled target identity preserved')
        checks=[]
        ps=api(cur,'erp_cp7_read_staged_analysis_pages_v1',r['run'])
        for entry in [ps['header']]+[api(cur,'erp_cp7_read_staged_analysis_page_v1',r['run'],i,ps['access_epoch']) for i in range(ps['page_count'])]:
            body=entry['body'];raw=body.encode('utf8');check(len(raw)==entry['utf8_bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256'],'Length means UTF8 bytes, not codepoint count')
            checks.append(dict(chars=len(body),bytes=len(raw),sha256=entry['sha256']))
        check(any(x['bytes']>x['chars'] for x in checks),'Negative byte-count control really uses multibyte text')
        bad=refusal(cur,lambda:api(cur,'erp_cp7_request_staged_analysis_v1',json.dumps(dict(r['q'],root_ids=[])),uuid.uuid4()))
        check(bad['refused'],'Client cannot inject an empty partial scope into global capture',result=bad)
        return dict(label=label,target=p['target'],identity=proof['identity'],byte_checks=checks,empty_scope_refusal=bad,bound='Empty client scope injection rejected; not proof of factory with zero products')

    return [wrap('AS20C-01-CONSUMERS',revoke),wrap('AS20C-37-FAILED',failed),wrap('AS20C-27-UTF8',unicode)]

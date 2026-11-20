"""Complete the CP7 read portion of historical cross-stage record RMD-T35 on synthetic records."""
from common import *
from datetime import timedelta
from time import perf_counter
import cp7_r3_reminders_cases as rem
import cp7_master_cases as master

INDEX_SQL="""select indexrelname,idx_scan,pg_get_indexdef(indexrelid) from pg_stat_user_indexes
 where schemaname='erp' and relname='manual_reminders' order by indexrelname"""
def snap():
    with psycopg.connect(**db(),autocommit=True) as c:
        c.execute('select pg_stat_clear_snapshot()')
        return {name:dict(scans=scans,definition=ddl) for name,scans,ddl in c.execute(INDEX_SQL).fetchall()}
def signatures(q):
    admin(q)
    return {name:first(q,"select count(*)::text || '/' || md5(coalesce(string_agg(h,'' order by h),'')) from (select md5(to_jsonb(t)::text) as h from "+name+" t) sub") for name in ('erp.manual_reminders','cp7_alert_native.outbox','erp.fg_stock_movements','erp.journal_entries','erp.journal_lines','erp.cost_recalc_queue')}
def run():
    out=dict(phase='seeding',recipients=[],page_ms=[],scope='CP7 manual recipient list, visible counts, read window and source index',scheduled_sends=0)
    save('reminder-scale',out)
    subjects=[];fixtures=[];expected=[]
    with psycopg.connect(**db()) as c,c.cursor() as q:
        out['seal']=measure_seal(q)
        for index,count in enumerate([207]+[51]*23+[0]):
            role='OWNER' if index%2==0 else 'ADMIN'
            subject=master.role_actor(q,role);subjects.append(subject)
            dates=rem.at_wib(TODAY+timedelta(days=7),9)
            created=[]
            for k in range(count):
                token='Astra RMD '+str(index)+' item '+str(k)
                r=rem.save(q,subject,'SAVE',rem.body(dates+timedelta(minutes=k),title=token))
                created.append(r['reminder_id'])
            c.commit()
            ordered=rem.order_of(q,subject,'OPEN');assert len(ordered)==count and set(ordered)==set(created)
            fixtures.append(dict(role=role,index=index,total=count));expected.append(ordered)
        admin(q);q.execute('analyze erp.manual_reminders');c.commit()
        out['indices_before']=snap()
        out['before_reads']=signatures(q)
        out['phase']='paging';save('reminder-scale',out)
    for i,who in enumerate(subjects):
        originals=expected[i];count=len(originals);seen=[];offset=0;pages=[]
        with psycopg.connect(**db()) as c,c.cursor() as q:
            while True:
                t=perf_counter();w=rem.get(q,who,dict(filter='OPEN',limit=25,offset=offset));c.commit()
                out['page_ms'].append(round(1000*(perf_counter()-t),3))
                page=w['page'];items=[r['id'] for r in w['items']]
                assert items==originals[offset:offset+min(25,200-offset)]
                assert page['total']==w['counts']['open']==count and page['window']==min(count,200)
                assert page['beyond_window']==max(count-200,0) and page['window_limit']==200
                assert len(items)==page['shown'] and w['due']['complete']==(count<=200)
                if i==0 and offset==0:out['example_page']=w
                seen.extend(items);pages.append(len(items))
                if page['next_offset'] is None:break
                assert page['next_offset']==offset+25;offset=page['next_offset']
            admin(q);q.execute('select pg_stat_force_next_flush()');c.commit()
        assert seen==originals[:200] and len(seen)==len(set(seen))
        out['recipients'].append(dict(**fixtures[i],visible=len(seen),beyond=count-len(seen),pages=pages,ids_sha256=hashlib.sha256('\n'.join(seen).encode()).hexdigest()))
    with psycopg.connect(**db()) as c,c.cursor() as q:
        out['after_reads']=signatures(q)
        assert out['after_reads']==out['before_reads']
        out['inactive_jobs']=q.execute("select jobname,active from cron.job where jobname in ('erp-wa-collect','erp-wa-analysis','erp-wa-send') order by 1").fetchall()
        assert len(out['inactive_jobs'])==3 and all(not v for _,v in out['inactive_jobs'])
        out['scheduler_runs']=first(q,'select count(*) from cron.job_run_details')
        assert out['scheduler_runs']==0
    out['indices_after']=snap()
    out['index_hits']={k:v['scans']-out['indices_before'][k]['scans'] for k,v in out['indices_after'].items() if 'owner_user_id' in v['definition']}
    assert sum(out['index_hits'].values())>0,out['index_hits']
    out['saved']=sum(f['total'] for f in fixtures);out['pages']=len(out['page_ms'])
    assert out['saved']==1380 and len(out['recipients'])==25 and max(out['page_ms'])<1000
    out.update(phase='complete',outcome='PASS');save('reminder-scale',out)
if __name__=='__main__':
    try:run()
    except Exception as err:record_failure('reminder-scale',err);raise

"""Independent full-size storage/transport oracle and comparator adjudication."""
import hashlib,json,time,uuid
from collections import Counter
from psycopg import sql
import cp7_p19_scale_cases as fixture
import cases_stage as stage
import cases_ops as ops
from cases_stage import admin,api,check,save,wrap,new_run,retained,temporaries,clean,refusal

def cases(cur,today):
    def canonical():
        r=new_run(cur,today);zone=cur.execute('show TimeZone').fetchone()[0]
        raw={};stable={}
        try:
            for tz in ('UTC','Asia/Jakarta','America/Los_Angeles'):
                cur.execute("select set_config('TimeZone',%s,true)",(tz,))
                raw[tz]={t:cur.execute(sql.SQL('select to_jsonb(x)::text from cp7_analysis_stage.{} x where {}=%s').format(sql.Identifier(t),sql.Identifier('id' if t=='jobs' else 'run_id')),(r['job'] if t=='jobs' else r['run'],)).fetchone()[0] for t in ('jobs','page_sets')}
                stable[tz]=retained(cur,r)
        finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))
        differing={t:[k for k,v in json.loads(raw['UTC'][t]).items() if v!=json.loads(raw['Asia/Jakarta'][t]).get(k)] for t in ('jobs','page_sets')}
        check(stable['UTC']==stable['Asia/Jakarta']==stable['America/Los_Angeles'],'Canonical comparator timezone invariance')
        check(any(differing.values()),'Negative comparator control actually differs')
        save('AS20_comparator_timezone_diagnostic',dict(raw=raw,stable=stable,differing_fields=differing))
        return dict(scope='AUDITOR_COMPARATOR_SELF_CHECK_NOT_PRODUCT_CREDIT',differing_fields=differing,canonical_all_fields_equal=True)
    preserve=[row for row in stage.cases(cur,today) if row[0]=='AS20-28_38_PRESERVATION']
    return [wrap('AS20_COMPARATOR_TIMEZONE_CONTROL',canonical),*preserve]

def stream_pages(cur,r):
    ps=api(cur,'erp_cp7_read_staged_analysis_pages_v1',r['run']);h=ps['header'];body=h['body'].encode()
    check(len(body)==h['utf8_bytes']<=8000000 and hashlib.sha256(body).hexdigest()==h['sha256'],'Independent header byte/hash')
    expected_ord=1;counts=Counter();keys=[];index=[]
    for i,p in enumerate(ps['pages']):
        check(i==p['index'] and p['target_lo']==expected_ord,'Sequential complete target pages',entry=p)
        z=api(cur,'erp_cp7_read_staged_analysis_page_v1',r['run'],i,ps['access_epoch']);b=z['body'].encode()
        check(len(b)==z['utf8_bytes']==p['utf8_bytes']<=8000000,'Independent UTF8 page size',index=i)
        check(hashlib.sha256(b).hexdigest()==z['sha256']==p['sha256'],'Independent page SHA256',index=i)
        v=json.loads(b);check(v['target_lo']==p['target_lo'] and v['target_hi']==p['target_hi'] and v['run_id']==r['run'],'Page range/source bound')
        for name,items in v['items'].items():
            check(len(items)==v['counts'][name] and counts[name]==v['offsets'][name],'No array item skipped/duplicated across pages',field=name,page=i)
            counts[name]+=len(items)
            if name=='recommendations':keys.extend(x['target']['key'] for x in items)
        expected_ord=p['target_hi']+1;index.append({k:p[k] for k in ('index','target_lo','target_hi','sha256','utf8_bytes')})
    check(expected_ord-1==ps['targets_total'] and len(index)==ps['page_count'],'All declared targets/pages covered')
    check(dict(counts)==ps['totals']['items'],'Every whole-run array count reconciles',counts=counts,totals=ps['totals'])
    identity=hashlib.sha256((h['sha256']+'\n'+'\n'.join(p['sha256'] for p in index)).encode()).hexdigest()
    check(identity==ps['identity_hash'],'Whole result identity independently derived')
    return dict(identity=identity,targets=ps['targets_total'],keys=keys,pages=index,header_bytes=h['utf8_bytes'],totals=dict(counts))

def storage(cur,r):
    admin(cur);out={}
    tables=[(t,'job_id',r['job']) for t in stage.TEMP]+[(t,'id' if t=='jobs' else 'job_id',r['job']) for t in stage.KEPT_JOB]+[(t,'run_id',r['run']) for t in stage.KEPT_RUN]+[('cleanups','job_id',r['job'])]
    for t,key,val in tables:
        cols=[x[0] for x in cur.execute("select a.attname from pg_attribute a where a.attrelid=%s::regclass and a.attnum>0 and not a.attisdropped order by a.attnum",('cp7_analysis_stage.'+t,)).fetchall()]
        sizes={}
        for col in cols:
            sizes[col]=int(cur.execute(sql.SQL('select coalesce(sum(pg_column_size(x.{})),0) from cp7_analysis_stage.{} x where {}=%s').format(sql.Identifier(col),sql.Identifier(t),sql.Identifier(key)),(val,)).fetchone()[0])
        n=cur.execute(sql.SQL('select count(*) from cp7_analysis_stage.{} where {}=%s').format(sql.Identifier(t),sql.Identifier(key)),(val,)).fetchone()[0]
        allocated=cur.execute('select pg_total_relation_size(%s::regclass)',('cp7_analysis_stage.'+t,)).fetchone()[0]
        out[t]=dict(rows=n,column_bytes=sizes,all_column_bytes=sum(sizes.values()),allocated_relation_bytes=allocated)
    return out

def races(tools,today):
    def scale5000():
        with tools.connect() as conn,conn.cursor() as cur:
            seeded=fixture.ensure(cur,today,5000,wip_done=False,commit=conn.commit);conn.commit()
            keys=fixture.current_targets(cur);check(len(keys)==5000 and len(set(keys))==5000,'Independent actual current targets count5000')
            q=fixture.history.query(today,10);request=uuid.uuid4();calls=[]
            def call(name,*args):
                t=time.monotonic();v=api(cur,name,*args);calls.append(dict(rpc=name,ms=(time.monotonic()-t)*1000,state=v.get('state'),units_done=v.get('units_done')));conn.commit();return v
            s=call('erp_cp7_request_staged_analysis_v1',json.dumps(q),request)
            # Close/reconnect once in mid-job; same UUID continues under ordinary transaction boundaries.
            for _ in range(3):s=call('erp_cp7_step_staged_analysis_v1',request)
            before_pause=s
        with tools.connect() as conn,conn.cursor() as cur:
            resumed=call('erp_cp7_get_staged_analysis_v1',request)
            check(resumed['request_id']==str(request) and resumed['units_done']==before_pause['units_done'],'Real reconnect resumes same completed work')
            s=resumed
            for _ in range(20000):
                if s['state']!='RUNNING':break
                s=call('erp_cp7_step_staged_analysis_v1',request)
                if len(calls)%50==0:save('AS20-26_scale_progress',dict(last=s,calls=calls,seed=seeded))
            save('AS20-26_scale_calls',dict(last=s,calls=calls,seed=seeded))
            check(s['state']=='DONE','All5000 targets produce a complete result',terminal=s)
            admin(cur);job=cur.execute('select id::text from cp7_analysis_stage.jobs where request_id=%s',(request,)).fetchone()[0]
            r=dict(run=s['run_id'],job=job,key=request)
            proof=stream_pages(cur,r);conn.commit()
            check(sorted(proof['keys'])==keys and len(set(proof['keys']))==5000,'Exactly5000 recommendations match authoritative ordered target set')
            before=storage(cur,r);kept=retained(cur,r);conn.commit()
            cleanup=clean(cur,r);conn.commit();after=storage(cur,r)
            check(retained(cur,r)==kept,'5000 cleanup retains all complete final rows')
            check(all(after[t]['rows']==0 for t in stage.TEMP),'All five temporary sets removed')
            proof2=stream_pages(cur,r);check(proof2==proof,'Every byte/hash/key/count unchanged after5000 cleanup');conn.commit()
            payload_cols={'jobs':['reference'],'headers':['body'],'pages':['body'],'outputs':['output'],'target_rows':['payload'],'pair_rows':['pair_row'],'pair_lists':['results'],'fragments':['body'],'plan_targets':['row'],'plan_scope':['scope']}
            selected=lambda z:sum(z[t]['column_bytes'][c] for t,cols in payload_cols.items() for c in cols)
            measurement=dict(before=before,after=after,payload_bytes_before=selected(before),payload_bytes_after=selected(after),payload_bytes_saved=selected(before)-selected(after),all_column_bytes_before=sum(x['all_column_bytes'] for x in before.values()),all_column_bytes_after=sum(x['all_column_bytes'] for x in after.values()),note='pg_column_size per stored column includes TOAST compression; relation allocation is separately measured and not claimed to shrink after DELETE')
            save('AS20-42_storage5000',measurement);save('AS20-26_pages5000',proof)
            # Real5,001st target via the ordinary fixture writers, never a sampled or forged source.
            overflow_seed=fixture.ensure(cur,today,5001,wip_done=True,commit=conn.commit);conn.commit()
            bad=uuid.uuid4();overflow=None
            try:
                overflow=call('erp_cp7_request_staged_analysis_v1',json.dumps(q),bad)
                for _ in range(20000):
                    if overflow['state']!='RUNNING':break
                    overflow=call('erp_cp7_step_staged_analysis_v1',bad)
            except Exception as exc:
                conn.rollback();overflow=dict(refused=True,error=str(exc),sqlstate=getattr(exc,'sqlstate',None))
            admin(cur)
            completed=cur.execute("select count(*) from cp7_analysis_stage.jobs where request_id=%s and state='DONE'",(bad,)).fetchone()[0]
            check((overflow.get('refused') or overflow.get('state')=='FAILED') and completed==0 and 'TARGET_LIMIT' in json.dumps(overflow),'5001 refuses honestly without truncated success',observed=overflow)
            return dict(targets=5000,pages=len(proof['pages']),identity=proof['identity'],calls=len(calls),max_call_ms=max(x['ms'] for x in calls),source_fixture='WRITER_SCALE_SETUP_5000_UNCHANGED',payload_bytes_before=measurement['payload_bytes_before'],payload_bytes_after=measurement['payload_bytes_after'],overflow=overflow)
    cleaners=[row for row in ops.races(tools,today) if row[0]=='AS20-40_TWO_CLEANERS']
    return [*cleaners,wrap('AS20-26_27_42_SCALE5000',scale5000)]

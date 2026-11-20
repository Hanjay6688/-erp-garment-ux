"""Date ordinary application reads and a writer transaction boundary on the same PostgreSQL clock."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event,Lock
from time import monotonic,sleep
import psycopg
from common import db,first
import cp7_snapshot_cases as auth

def observe(writer, actor, calls, committed):
    stop=Event();lock=Lock();pids={};traces=[];errors=[]
    def one(kind,statement,args,summary):
        with psycopg.connect(**db(),application_name='astra25_'+kind) as conn,conn.cursor() as q:
            pid=first(q,'select pg_backend_pid()')
            with lock:pids[kind]=pid
            while not stop.is_set():
                auth.actor(q,actor)
                # No delay, fixture hook or change to the public ERP routine.
                sql='WITH response AS MATERIALIZED (SELECT '+statement+' AS body) SELECT body,statement_timestamp(),clock_timestamp() FROM response'
                body,begin,end=q.execute(sql,args).fetchone()
                row=dict(kind=kind,pid=pid,begin=begin,end=end,value=summary(body))
                with lock:traces.append(row)
                conn.commit()
    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        futures=[pool.submit(one,*c) for c in calls]
        check=psycopg.connect(**db(),autocommit=True)
        try:
            until=monotonic()+12;active=[]
            while monotonic()<until:
                if any(f.done() for f in futures):
                    for f in futures:
                        if f.done():f.result()
                with lock:ready={x['kind'] for x in traces}==set(pids) and len(pids)==len(calls)
                if ready:
                    active=check.execute("select pid,application_name,query_start,clock_timestamp() from pg_stat_activity where application_name like 'astra25_%' and state='active' and query like 'WITH response AS MATERIALIZED%'").fetchall()
                    if active:break
                sleep(.001)
            assert active,'No native reader observed in pg_stat_activity'
            pre=writer.execute('select clock_timestamp()').fetchone()[0]
            if committed:writer.commit()
            else:writer.rollback()
            post=writer.execute('select clock_timestamp()').fetchone()[0]
            deadline=monotonic()+3
            while monotonic()<deadline:
                with lock:
                    recent={x['kind']for x in traces if x['begin']>post}
                    if len(recent)==len(calls):break
                sleep(.003)
        finally:
            stop.set();check.close()
            for f in futures:
                try:f.result()
                except Exception as e:errors.append(str(e).splitlines()[0][:200])
    assert not errors,errors
    for x in traces:
        x['covers_entire_boundary']=x['begin']<=pre<=post<=x['end']
    return dict(boundary='COMMIT' if committed else 'ROLLBACK',writer_before=pre,writer_after=post,
                active_witness=[dict(pid=x[0],session=x[1],query_start=x[2],observed=x[3])for x in active],
                reads=traces,fully_enclosing=sum(x['covers_entire_boundary'] for x in traces))

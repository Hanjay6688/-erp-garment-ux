#!/usr/bin/env python3
"""Twelve observed native transfer edit/source-reversal schedules on AM."""
from pathlib import Path
import json,os,threading,time,traceback,uuid
import psycopg
import cp6_v2620am_sql_trial as trial
import cp6_v2620am_runtime as runtime
import cp6_v2620h_maintenance_rollback_matrix as matrix

f=trial.f
ROOT=Path('cp6-proof/writer-am/transfer-concurrency')
CLONE=matrix.CLONE.replace('postgres:postgres@','supabase_admin:postgres@')


def seed_case(cur,kind):
    cur.execute("set local timezone='Asia/Jakarta'")
    source,dest=f.locations(cur);mat=f.material(cur)
    receipt=f.purchase(cur,mat,source,100,10,f.MASTER['t0'])
    if kind.startswith('HOP_'):
        first=f.post_transfer(cur,f.transfer(cur,source,dest,[(mat,100)],f.MASTER['t1']))
        last,_=f.locations(cur)
        draft=f.transfer(cur,dest,last,[(mat,50)],f.MASTER['t2'])
    else:
        first=None
        draft=f.transfer(cur,source,dest,[(mat,20 if 'REVERSE' in kind else 10)],f.MASTER['t1'])
    return dict(material=mat,source=source,dest=dest,receipt=receipt,draft=draft,first=first)


def run_case(kind,commit):
    with psycopg.connect(CLONE) as conn,conn.cursor() as cur:fixture=seed_case(cur,kind)
    draft=fixture['draft'];first=second=thread=None
    try:
        first=psycopg.connect(CLONE,application_name='am-transfer-first')
        second=psycopg.connect(CLONE,application_name='am-transfer-second')
        for conn in (first,second):
            conn.execute("set statement_timeout='20s';set lock_timeout='15s';set timezone='Asia/Jakarta'");conn.commit()
        def edit(cur):return f.call(cur,'erp.save_material_transfer_draft_v2',f.encode(dict(
            id=draft['material_transfer_id'],change_reason='AM concurrent qty20',
            items=[dict(material_id=fixture['material'],qty=20)])),uuid.uuid4(),draft['row_version'])
        def post(cur):return f.post_transfer(cur,draft)
        def reverse(cur):
            if kind.startswith('HOP_'):
                source=fixture['first']
                return f.call(cur,'erp.reverse_material_transfer_v2',source['material_transfer_id'],
                    'AM source transfer inverse',uuid.uuid4(),source['row_version'])
            return f.call(cur,'erp.reverse_material_purchase',fixture['receipt'],'AM source receipt inverse')
        funcs={'EDIT_POST':(edit,post),'POST_EDIT':(post,edit),
            'REVERSE_POST':(reverse,post),'POST_REVERSE':(post,reverse),
            'HOP_REVERSE_POST':(reverse,post),'HOP_POST_REVERSE':(post,reverse)}
        fn1,fn2=funcs[kind];first_result=fn1(first.cursor());result={}
        def worker():
            try:
                value=fn2(second.cursor());second.commit();result.update(success=True,value=value)
            except Exception as exc:
                second.rollback();result.update(success=False,sqlstate=getattr(exc,'sqlstate',None),error=str(exc))
        thread=threading.Thread(target=worker,daemon=True);thread.start()
        blocked=False
        with psycopg.connect(CLONE,autocommit=True) as observer:
            deadline=time.monotonic()+7
            while time.monotonic()<deadline and thread.is_alive():
                blocked=observer.execute('select %s=any(pg_blocking_pids(%s))',(first.info.backend_pid,second.info.backend_pid)).fetchone()[0]
                if blocked:break
                time.sleep(.03)
        assert blocked,'No actual lock wait observed'
        first.commit() if commit else first.rollback()
        thread.join(22);assert not thread.is_alive(),'Concurrent operation did not finish'
        assert result['success']==(not commit),result
        if commit:
            assert result['sqlstate']=='P0001',result
            if kind in ('EDIT_POST','POST_EDIT'):assert 'STALE_VERSION' in result['error'] or 'DRAFT' in result['error'],result
        with psycopg.connect(CLONE) as observer,observer.cursor() as cur:
            state=f.stock(cur,fixture['material'])
            if kind in ('REVERSE_POST','HOP_REVERSE_POST') and commit:
                expected=0 if kind=='REVERSE_POST' else 100
            elif kind=='POST_REVERSE' and not commit:expected=0
            else:expected=100
            assert state['qty']==expected and state['value']==10*expected,state
            posted=cur.execute('select status from erp.material_transfers where id=%s',(draft['material_transfer_id'],)).fetchone()[0]
            wanted='POSTED' if (kind in ('POST_EDIT','POST_REVERSE','HOP_POST_REVERSE') and commit) or (kind in ('EDIT_POST','REVERSE_POST','HOP_REVERSE_POST') and not commit) else 'DRAFT'
            assert posted==wanted,(posted,wanted)
            assert len(runtime.verified_successor(cur))==690
        return dict(status='PASS',kind=kind,first_committed=commit,blocking_observed=True,
            first_result=first_result,second=result,global_state=state,draft_status=posted)
    finally:
        for conn in (first,second):
            if conn is not None:
                if thread and thread.is_alive():conn.cancel()
                conn.close()
        if thread:thread.join(2)


def run():
    head,tree=runtime.verify_audit_source()
    assert os.environ['PGURL']==matrix.SOURCE and os.environ['CP6_ROLLBACK_RACE_PGURL']==matrix.CLONE
    ROOT.mkdir(parents=True,exist_ok=True)
    result=dict(status='INCOMPLETE',head=head,tree=tree,runtime_generation='AM',cases={},production_go=False,independent_acceptance=False)
    def save():(ROOT/'manifest.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    save()
    try:
        matrix.command(['bash','scripts/clone-cp6-disposable-database.sh',matrix.SOURCE,matrix.MAINTENANCE,matrix.CLONE,
            'cp6_rollback',matrix.CONTAINER,str(ROOT/'PHYSICAL_BOUNDARY')],ROOT/'clone.log')
        with psycopg.connect(CLONE) as conn,conn.cursor() as cur:
            cur.execute("set local timezone='Asia/Jakarta'")
            assert len(runtime.verified_successor(cur))==690
            cur.execute('grant usage on schema erp to authenticated');trial.prepare(cur)
        for kind in ('EDIT_POST','POST_EDIT','REVERSE_POST','POST_REVERSE','HOP_REVERSE_POST','HOP_POST_REVERSE'):
            for commit in (True,False):
                name=kind+('_COMMIT' if commit else '_ABORT')
                try:row=run_case(kind,commit)
                except Exception as exc:row=dict(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
                result['cases'][name]=row;save()
                print(json.dumps(dict(case=name,status=row['status'],error=row.get('error'))),flush=True)
    finally:matrix.legacy.drop_clone()
    with psycopg.connect(matrix.MAINTENANCE) as conn:
        result['clone_removed']=conn.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]==0
    if result['clone_removed'] and len(result['cases'])==12 and all(r['status']=='PASS' for r in result['cases'].values()):result['status']='WRITER_PASS'
    save();return result

if __name__=='__main__':
    result=run();print(json.dumps({k:v for k,v in result.items() if k!='cases'},default=str))
    raise SystemExit(0 if result['status']=='WRITER_PASS' else 1)

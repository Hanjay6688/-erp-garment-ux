#!/usr/bin/env python3
"""Eight observed two-session return limits and original-sale reversal races."""
from pathlib import Path
from datetime import timedelta
import json,os,threading,traceback
import psycopg
import cp6_v2620af_concurrency as old
import cp6_v2620ah_runtime as runtime
import cp6_ag_residual_review as original
import cp6_v2620ah_family as family
actors,base,prior,peer=family.actors,family.base,family.prior,family.peer
ROOT=Path('cp6-proof/writer-ah/concurrency')

def fixture():
    with old.connect('ah-fixture') as conn,conn.cursor() as cur:
        day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3)
        f=original.posted_fixture(cur,day);f['ordinary_draft_creation']=True
        f['returns']=[original.create_return(cur,day,f,destination,grade,(2,))
                      for destination,grade in ((base.LOCATION,'GRADE_A'),(f['second_location'],'GRADE_B'))]
        return f

def post(index):
    def operation(cur,f):
        peer.ordinary(cur);cur.execute('select erp.post_sales_return(%s)',(f['returns'][index],))
    return operation

def reverse(cur,f):
    peer.ordinary(cur);cur.execute("select erp.reverse_sale(%s,'AH observed return race')",(f['sale']['sale_id'],))

def run_case(mode):
    f=fixture();response={};thread=None
    abort=mode.endswith('ABORT');allocation=mode.startswith('ALLOCATION')
    if allocation:
        index=1 if 'OTHER' in mode else 0
        first_operation,second_operation=post(index),post(1-index)
    else:
        return_first=mode.startswith('RETURN')
        first_operation,second_operation=(post(1),reverse) if return_first else (reverse,post(1))
    with old.connect('ah-first') as first,old.connect('ah-second') as second:
        try:
            with first.cursor() as cur:first_operation(cur,f)
            thread=threading.Thread(target=old.worker,args=(second,second_operation,f,response),daemon=True)
            thread.start();lock=old.await_lock(second.info.backend_pid)
            assert first.info.backend_pid in lock[2],lock
            first.rollback() if abort else first.commit()
            thread.join(30);assert not thread.is_alive(),'AH_SECOND_SESSION_STUCK'
        finally:
            first.rollback()
            if thread is not None and thread.is_alive():second.cancel();thread.join(5)
    if abort:assert response.get('committed'),response
    else:
        expected=('AH_RETURN_EXCEEDS_ORIGINAL_ALLOCATION' if allocation else
                  'retur POSTED' if return_first else 'Original sale must be active/posted')
        assert not response.get('committed') and response.get('sqlstate')=='P0001' and expected in response.get('error',''),response
    with old.connect('ah-observe') as conn,conn.cursor() as cur:
        actors.admin(cur)
        state=cur.execute("""select s.status,
          (select coalesce(sum(i.qty_pcs),0) from erp.sales_return_items i join erp.sales_returns r on r.id=i.return_id
           where r.sale_id=s.id and r.status='POSTED'),
          (select count(*) from erp.sales_returns r where r.sale_id=s.id and r.status='POSTED')
          from erp.sales_headers s where s.id=%s""",(f['sale']['sale_id'],)).fetchone()
        reversed_sale=not allocation and ((return_first and abort) or (not return_first and not abort))
        assert state==(('REVERSED',0,0) if reversed_sale else ('POSTED',2,1)),state
        today=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")
        report=family.report(cur,today)
    return dict(status='PASS',mode=mode,observed_lock=lock,second=response,final_state=state,report=report,
                fixture_admin_changed_posted_data=False,http_ui_csv_reachability_proven=False)

def run():
    head,tree=runtime.verify_audit_source()
    assert os.environ.get('PGURL')==old.SOURCE and os.environ.get('CP6_AH_CONFIRM')=='postgres'
    ROOT.mkdir(parents=True,exist_ok=True)
    result=dict(status='INCOMPLETE',head=head,tree=tree,cases=[],production_go=False,
                schema_usage_fixture_grant=True,http_ui_csv_reachability_proven=False)
    with psycopg.connect(old.SOURCE) as conn,conn.cursor() as cur:assert len(runtime.verified_successor(cur))==690
    try:
        old.matrix.command(['bash','scripts/clone-cp6-disposable-database.sh',old.SOURCE,old.matrix.MAINTENANCE,
                            old.matrix.CLONE,'cp6_rollback',old.matrix.CONTAINER,str(ROOT/'PHYSICAL_BOUNDARY')],ROOT/'clone.log')
        with old.connect('ah-foundation') as conn,conn.cursor() as cur:
            cur.execute('grant usage on schema erp to authenticated')
            cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps({'sub':base.OPERATOR_AUTH,'role':'authenticated'}),))
            base.load_fixture_foundation(cur);actors.admin(cur)
            day=base.one(cur,"select (statement_timestamp() at time zone 'Asia/Jakarta')::date")-timedelta(days=3)
            prior.set_open_period(cur,day-timedelta(days=4))
        for mode in ('ALLOCATION_MAIN_COMMIT','ALLOCATION_MAIN_ABORT','ALLOCATION_OTHER_COMMIT','ALLOCATION_OTHER_ABORT',
                     'RETURN_COMMIT','RETURN_ABORT','SALE_REVERSE_COMMIT','SALE_REVERSE_ABORT'):
            try:record=run_case(mode)
            except Exception as exc:record=dict(status='FAIL',mode=mode,error=str(exc),traceback=traceback.format_exc())
            result['cases'].append(record)
            print(json.dumps(dict(mode=mode,status=record['status'],error=record.get('error'))),flush=True)
            (ROOT/'RESULT.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    finally:old.matrix.legacy.drop_clone()
    with psycopg.connect(old.matrix.MAINTENANCE) as conn:
        result['clone_removed']=conn.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]==0
    if result['clone_removed'] and len(result['cases'])==8 and all(r['status']=='PASS' for r in result['cases']):result['status']='PASS'
    (ROOT/'RESULT.json').write_text(json.dumps(result,indent=2,default=str)+'\n');return result

if __name__=='__main__':
    try:result=run()
    except Exception as exc:
        result=dict(status='FAIL',error=str(exc),traceback=traceback.format_exc(),production_go=False)
        ROOT.mkdir(parents=True,exist_ok=True);(ROOT/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cases'}));raise SystemExit(0 if result['status']=='PASS' else 1)

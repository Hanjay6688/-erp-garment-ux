"""Three deterministic real-lock schedules + one actual Auth/RPC journey.

Prepared only. Execution must first admit a complete PASS Native7 Original on
the identical backend provider; fixture doubles cannot open that gate.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
import json,threading,time,uuid
import psycopg
from cp7_vendor_receivable import cases as native

RACE_IDS=('VENDOR_AR_REFUND_COMMIT_APPLY_CAPACITY_REFUSED',
          'VENDOR_AR_APPLY_COMMIT_REFUND_CAPACITY_REFUSED',
          'VENDOR_AR_SAME_UUID_REFUND_ONCE_AFTER_LOCK')
HTTP_IDS=('VENDOR_AR_REAL_AUTH_REFUND_REPLAY_CURRENT_REVOKE',)
WRITE='erp_save_laundry_bd_action_v1'
READ='erp_get_laundry_bd_workspace_v1'

def races(tools,today):
    def run(mode):
        with tools.connect()as connection,connection.cursor()as cur:
            f=native.fixture(cur,today);credit=native.correction(cur,f);source=credit['invoice_id'];up=None
            if mode!='SAME_UUID':_,up=native.bd.correction(cur,f,f['line'],'3000.00',f['invoice'],today)
            connection.commit()
        key=uuid.uuid4();started=threading.Event();waiting=[]
        def operation(cur,first):
            if mode=='SAME_UUID':return native.refund(cur,f,source,'3000.00',key=key)
            is_refund=(mode=='REFUND_FIRST')==first
            return native.refund(cur,f,source,'3000.00')if is_refund else native.use(cur,f,source,up['invoice_id'],'3000.00')
        def second():
            with tools.connect()as connection,connection.cursor()as cur:
                waiting.append(cur.execute('select pg_backend_pid()').fetchone()[0]);started.set()
                try:
                    result=operation(cur,False);connection.commit();return dict(committed=True,result=result)
                except psycopg.Error as error:
                    connection.rollback();return dict(committed=False,sqlstate=error.sqlstate,error=str(error).splitlines()[0])
        with tools.connect()as holder,holder.cursor()as cur:
            holder_pid=cur.execute('select pg_backend_pid()').fetchone()[0]
            first=operation(cur,True)
            with ThreadPoolExecutor(max_workers=1)as pool:
                future=pool.submit(second)
                try:
                    assert started.wait(5),'SECOND_SESSION_NOT_STARTED'
                    deadline=time.monotonic()+8;observed=None
                    while time.monotonic()<deadline:
                        cur.execute('select pg_stat_clear_snapshot()')
                        row=cur.execute('select wait_event_type,wait_event,pg_blocking_pids(pid)from pg_stat_activity where pid=%s',(waiting[0],)).fetchone()
                        if row and row[0]=='Lock'and holder_pid in row[2]:observed=row;break
                        time.sleep(.02)
                    assert observed,'ACTUAL_VENDOR_SOURCE_LOCK_WAIT_REQUIRED'
                finally:holder.commit()  # release only this test's first transaction
                result=future.result(30)
        if mode=='SAME_UUID':
            assert result['committed']is True and result['result']['refund_id']==first['refund_id']and result['result']['replayed']is True,result
        else:
            assert result['committed']is False and result['sqlstate']=='P0001'
            assert result['error'].startswith('BD_CLAIM_CREDIT_EXCEEDS_AVAILABLE:'),result
        with tools.connect()as connection,connection.cursor()as cur:
            state=native.state(cur,f);screen=native.screen(cur,f)
            assert D(state['ar'])==0 and screen['ledger']['matches'],(state,screen)
            refunds=cur.execute('select count(*),coalesce(sum(amount),0)from cp7_vendor_receivable.refunds_v1 where correction_id=%s',(source,)).fetchone()
            applications=cur.execute("select count(*),coalesce(sum(a.amount),0)from erp.bd_claim_credit_applications_v1 a join erp.vendor_payments p on p.id=a.vendor_payment_id where a.correction_invoice_id=%s and p.status='POSTED'",(source,)).fetchone()
            if mode=='APPLY_FIRST':assert refunds==(0,D(0))and applications==(1,D('3000.00'))and D(state['cash'])==0 and D(state['ap'])==0
            else:assert refunds==(1,D('3000.00'))and applications==(0,D(0))and D(state['cash'])==D('3000.00')and D(state['ap'])==(D(0)if mode=='SAME_UUID'else D('3000.00'))
            connection.rollback()
        return dict(status='PASS',mode=mode,observed_lock=list(observed),first=first,second=result,
            final_state=state,refund_rows=refunds[0],active_application_rows=applications[0],same_credit_never_spent_twice=True)
    return [(key,lambda mode=mode:run(mode))for key,mode in zip(RACE_IDS,('REFUND_FIRST','APPLY_FIRST','SAME_UUID'))]

def http_cases(http,today):
    def actual():
        actor=http.login('ADMIN','vendor-receivable-refund')
        with http.connect()as connection,connection.cursor()as cur:
            # Only the direct Native fixture needs this harness grant. It is
            # removed in the same transaction before any actual HTTP request.
            native.bd.api.admin(cur)
            grant=not cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
            if grant:cur.execute('grant usage on schema erp to authenticated')
            try:f=native.fixture(cur,today);credit=native.correction(cur,f)
            finally:
                native.bd.api.admin(cur)
                if grant:cur.execute('revoke usage on schema erp from authenticated')
            role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(actor.auth_user_id,)).fetchone()[0]
            for permission in ('production.laundry.view','finance.hpp.view','finance.hpp.manage'):
                cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,permission))
            before=native.state(cur,f);connection.commit()
        query=dict(p_filters=dict(vendor_id=f['vendor']))
        assert http.anon_rpc(READ,query)['status']in(401,403,404)
        initial=actor.rpc(READ,query);assert initial['status']==200 and initial['body']['money_visible']is True,initial
        assert initial['body']['payables']['ledger']['receivable_balance']=='3000.00'
        key=str(uuid.uuid4());payload=dict(source_id=credit['invoice_id'],amount='500.00',date=str(today),cash_account_id=f['cash'],reason='Uang vendor diterima di bank')
        args=dict(p_action='RECEIVE_VENDOR_REFUND',p_payload=payload,p_client_request_id=key)
        assert http.anon_rpc(WRITE,args)['status']in(401,403,404)
        result=actor.rpc(WRITE,args);assert result['status']==200 and result['body']['refund_id']==key and result['body']['remaining']=='2500.00',result
        replay=actor.rpc(WRITE,args);assert replay['status']==200 and replay['body']['refund_id']==key and replay['body']['replayed']is True,replay
        with http.connect()as connection,connection.cursor()as cur:
            state=native.state(cur,f)
            assert state['origin']==before['origin']and D(state['ar'])==D('2500.00')and D(state['cash'])==D('500.00')
            assert cur.execute('select count(*)from cp7_vendor_receivable.refunds_v1 where id=%s',(key,)).fetchone()[0]==1
            cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key in('finance.hpp.view','finance.hpp.manage')",(role,));connection.commit()
        denied=actor.rpc(WRITE,args);assert denied['status']==403,denied
        hidden=actor.rpc(READ,query);assert hidden['status']==200,hidden
        body=hidden['body'];assert body['money_visible']is False and body['payables']is None and body['vendor_receivable_accounts']is None
        with http.connect()as connection,connection.cursor()as cur:
            assert native.state(cur,f)==state;connection.rollback()
        return dict(status='PASS',actual_Auth_HTTP=True,refund_once_after_same_UUID_replay=True,
            permission_revocation_before_cached_reply=True,financial_values_hidden_after_view_revoke=True,original_payment_history_immutable=True)
    return [(HTTP_IDS[0],actual)]

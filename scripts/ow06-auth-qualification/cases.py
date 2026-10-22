"""Real GoTrue/PostgREST OW06 journeys through the two public RPCs the supplier transfer screen calls.

Receipts, bank and suppliers are prepared with the retained OW06 Native fixture on an admin connection and committed
(as the OW05 Auth cases do); every write under test goes through a signed-in user's PostgREST call. Oracles read the
Native supplier payments, the bank balance, the one transfer cash journal and the private transfer rows.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
import json
import time
import uuid

from cp7_supplier_transfer import cases as t

IDS=('OW06_REAL_AUTH_CREATE_REPLAY_CORRECT_REVERSE_EXACT_CASH',
     'OW06_REAL_AUTH_RIGHT_REVOKED_WHILE_WAITING_REFUSED_ATOMICALLY',
     'OW06_TWO_DISTINCT_AUTH_USERS_SAME_RECEIPTS_ONE_EFFECT',
     'OW06_REAL_AUTH_ROLE_WITHOUT_PAY_RIGHT_DENIED_NO_EFFECT')
REASON='OW06 satu transfer supplier lewat login nyata'
LOCK="select pg_backend_pid(),pg_advisory_xact_lock(hashtextextended('FG_HPP_SALES_V2620C',0))"
PAY='finance.ap.pay'
# Active role outside OWNER/ADMIN: cp7_invoice.payment_access() gives it no pay right whatever its permissions.
ROLE='KEUANGAN'


def body(reply):
    assert reply['status']==200,reply
    return reply['body']


def prepare(http,today):
    # The retained fixture writers run as the signed-in fixture actor; like the supplier payment browser fixture, ERP
    # USAGE is granted and revoked inside this one fixture transaction, so the committed catalog is unchanged.
    with http.connect()as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        f=t.fixture(cur,today);f['at']=t.single.at(cur);t.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    return f


def read(user,f,transfer=None):
    return body(user.rpc('erp_cp7_get_supplier_transfer_v1',dict(p_query=dict(supplier_id=f['supplier'],transfer_id=transfer))))


def payload(w,f,amounts=('400.00','600.00'),transfer=None):
    p=dict(action='CORRECT'if transfer else'CREATE',supplier_id=f['supplier'],review_token=w['review_token'],reason=REASON,
        amount=f'{sum(D(a)for a in amounts):.2f}',cash_account_id=f['cash'],payment_date=f['at'],
        allocations=[dict(purchase_id=pid,amount=a)for pid,a in zip(f['receipts'],amounts)])
    if transfer:p['transfer_id']=transfer
    return p


def save(user,p,key=None):
    return user.rpc('erp_cp7_save_supplier_transfer_v1',dict(p_payload=p,p_request=str(key or uuid.uuid4())))


def state(http,f):
    """Money and private rows of this supplier: bank movement since the fixture, Native paid per receipt, journals."""
    with http.connect()as conn,conn.cursor()as cur:
        t.b.api.admin(cur)
        out=dict(cash=str(t.single.misc.cash_balance(cur,f['cash'])-f['bank_start']),
            paid={pid:str(cur.execute("select coalesce(sum(amount),0)from erp.supplier_payments where purchase_id=%s and status='POSTED'",(pid,)).fetchone()[0])
                  for pid in f['receipts']},
            journals=[tuple(map(str,r))for r in cur.execute("""select j.status,sum(l.debit),sum(l.credit),count(*)from erp.journal_entries j
                join erp.journal_lines l on l.journal_entry_id=j.id join cp7_supplier_transfer.transfers_v1 x on x.id=j.source_id
                where j.source_type='CP7_SUPPLIER_TRANSFER'and x.supplier_id=%s group by j.id,j.status order by j.status,j.id""",(f['supplier'],)).fetchall()],
            private={name:cur.execute('select count(*)from cp7_supplier_transfer.'+name).fetchone()[0]
                     for name in('requests_v1','transfers_v1','allocations_v1','corrections_v1','context_v1')})
        conn.rollback()
    return out


def waiting(http,holder_pid,futures,count):
    until=time.monotonic()+20
    with http.connect()as conn,conn.cursor()as cur:
        while True:
            cur.execute('select pg_stat_clear_snapshot()')
            rows=cur.execute('select pid,wait_event_type,wait_event from pg_stat_activity '
                'where datname=current_database()and %s=any(pg_blocking_pids(pid))order by pid',(holder_pid,)).fetchall()
            if len(rows)==count:
                assert all(r[1:]==('Lock','advisory')for r in rows),rows
                conn.rollback();return rows
            assert time.monotonic()<until,('OW06_ACTUAL_WAIT_NOT_OBSERVED',rows)
            assert not any(x.done()for x in futures),[x.result()if x.done()else'pending'for x in futures]
            conn.rollback();time.sleep(.03)


def role_permission(http,role,restore=None):
    with http.connect()as conn,conn.cursor()as cur:
        t.b.api.admin(cur)
        if restore is None:
            row=cur.execute('delete from erp.app_role_permissions p where role_id=%s and permission_key=%s returning to_jsonb(p)',(role,PAY)).fetchone()
            assert row is not None,('OW06_ROLE_HAS_NO_PAY_RIGHT',role);result=row[0]
        else:
            cur.execute('insert into erp.app_role_permissions select *from jsonb_populate_record(null::erp.app_role_permissions,%s::jsonb)',(json.dumps(restore,default=str),))
            result=None
        conn.commit();return result


def role_of(http,user):
    with http.connect()as conn,conn.cursor()as cur:
        role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(user.auth_user_id,)).fetchone()[0];conn.rollback()
    return role


def http_cases(http,today):
    def journey():
        user=http.login('OWNER',label='ow06-journey');f=prepare(http,today)
        w=read(user,f);ids=[r['id']for r in w['receipts']['rows']]
        assert w['can_write']is True and all(pid in ids for pid in f['receipts']),w
        start=state(http,f);p=payload(w,f);key=uuid.uuid4();made=body(save(user,p,key))
        after=state(http,f)
        assert D(after['cash'])==D(start['cash'])-1000 and{k:D(v)for k,v in after['paid'].items()}=={pid:D(start['paid'][pid])+D(a)for pid,a in zip(f['receipts'],('400','600'))},(start,after)
        assert after['journals']==[('POSTED','1000.00','1000.00','2')]and after['private']['context_v1']==0,after
        assert body(save(user,p,key))==made and state(http,f)==after
        changed=save(user,dict(p,reason=REASON+' berubah'),key)
        assert changed['status']==400 and'CP7_SUPPLIER_TRANSFER_REQUEST_CHANGED'in str(changed['body']),changed
        shown=read(user,f,made['transfer_id'])['selected']
        assert shown['status']=='POSTED'and D(shown['amount'])==1000 and{a['purchase_id']:D(a['amount'])for a in shown['allocations']}==dict(zip(f['receipts'],(D(400),D(600)))),shown
        fixed=body(save(user,payload(read(user,f,made['transfer_id']),f,('250.00','500.00'),made['transfer_id'])))
        assert fixed['transfer_id']!=made['transfer_id']and read(user,f,made['transfer_id'])['selected']['status']=='REVERSED',fixed
        corrected=state(http,f)
        assert D(corrected['cash'])==D(start['cash'])-750 and{k:D(v)for k,v in corrected['paid'].items()}=={pid:D(start['paid'][pid])+D(a)for pid,a in zip(f['receipts'],('250','500'))},corrected
        w=read(user,f,fixed['transfer_id'])
        back=body(save(user,dict(action='REVERSE',supplier_id=f['supplier'],transfer_id=fixed['transfer_id'],review_token=w['review_token'],reason=REASON)))
        end=state(http,f)
        assert D(end['cash'])==D(start['cash'])and{k:D(v)for k,v in end['paid'].items()}=={k:D(v)for k,v in start['paid'].items()},end
        assert read(user,f,fixed['transfer_id'])['selected']['status']=='REVERSED'and end['private']['context_v1']==0
        return dict(status='PASS',real_Auth=True,created='400.00+600.00',bank_after_create='-1000.00',one_journal_two_lines=True,
            same_UUID_replay_no_effect=True,changed_payload_same_UUID_refused=True,corrected='250.00+500.00',bank_after_correction='-750.00',
            reversed_whole_transfer=True,bank_after_reverse='0.00',reverse_status=back.get('status'))

    def revoked():
        # ADMIN: the protected OWNER role grants every permission, so only a non-owner role can lose finance.ap.pay.
        user=http.login('ADMIN',label='ow06-rights');f=prepare(http,today);role=role_of(http,user)
        w=read(user,f);assert w['can_write']is True,w
        p=payload(w,f);key=uuid.uuid4();before=state(http,f);removed=None
        try:
            with ThreadPoolExecutor(max_workers=1)as pool:
                with http.connect()as holder,holder.cursor()as cur:
                    pid=cur.execute(LOCK).fetchone()[0]
                    future=pool.submit(save,user,p,key)
                    try:
                        observed=waiting(http,pid,[future],1)
                        removed=role_permission(http,role)
                    finally:holder.rollback()
                reply=future.result(timeout=60)
            # The re-check after the wait (transfer.sql, access_now_v1(true)) refuses a missing write right itself.
            assert reply['status']==403 and'CP7_SUPPLIER_TRANSFER_DENIED'in str(reply['body']),reply
            assert state(http,f)==before
            role_permission(http,role,removed);removed=None
            made=body(save(user,p,key))
            assert D(state(http,f)['cash'])==D(before['cash'])-1000 and body(save(user,p,key))==made
        finally:
            if removed is not None:role_permission(http,role,removed)
        return dict(status='PASS',actual_advisory_wait=[list(map(str,r))for r in observed],right_removed_while_waiting='403 CP7_SUPPLIER_TRANSFER_DENIED after the wait',
            zero_effect=True,same_UUID_after_right_restored_succeeds_once=True)

    def race():
        users=[http.login('OWNER',label='ow06-race-'+str(i))for i in range(2)]
        assert users[0].auth_user_id!=users[1].auth_user_id
        f=prepare(http,today);args=[payload(read(u,f),f)for u in users];keys=[uuid.uuid4(),uuid.uuid4()];before=state(http,f)
        with ThreadPoolExecutor(max_workers=2)as pool:
            with http.connect()as holder,holder.cursor()as cur:
                pid=cur.execute(LOCK).fetchone()[0]
                futures=[pool.submit(save,u,a,k)for u,a,k in zip(users,args,keys)]
                try:observed=waiting(http,pid,futures,2)
                finally:holder.rollback()
            replies=[x.result(timeout=60)for x in futures]
        winners=[i for i,r in enumerate(replies)if r['status']==200]
        assert len(winners)==1,replies
        win=winners[0];lose=1-win
        assert replies[lose]['status']==400 and'CP7_SUPPLIER_TRANSFER_STALE_REVIEW'in str(replies[lose]['body']),replies
        after=state(http,f)
        assert D(after['cash'])==D(before['cash'])-1000 and len(after['journals'])==len(before['journals'])+1,after
        assert body(save(users[win],args[win],keys[win]))==body(replies[win])and state(http,f)==after
        again=save(users[lose],args[lose],keys[lose])
        assert again['status']==400 and'CP7_SUPPLIER_TRANSFER_STALE_REVIEW'in str(again['body'])and state(http,f)==after,again
        return dict(status='PASS',two_distinct_Auth_users=True,actual_waiters=len(observed),one_winner=True,
            loser='400 CP7_SUPPLIER_TRANSFER_STALE_REVIEW',one_cash_journal=True,bank='-1000.00',winner_replay_identical=True)

    def denied():
        owner=http.login('OWNER',label='ow06-denied-owner');f=prepare(http,today);p=payload(read(owner,f),f)
        with http.connect()as conn,conn.cursor()as cur:
            perms={k for k,in cur.execute("""select p.permission_key from erp.app_role_permissions p join erp.app_roles r on r.id=p.role_id
                where r.role_code=%s and r.is_active""",(ROLE,)).fetchall()};conn.rollback()
        viewer='warehouse.procurement.view'in perms and'finance.ap.view'in perms
        staff=http.login(ROLE,label='ow06-denied-'+ROLE.lower());before=state(http,f)
        seen=staff.rpc('erp_cp7_get_supplier_transfer_v1',dict(p_query=dict(supplier_id=f['supplier'],transfer_id=None)))
        if viewer:
            assert seen['status']==200 and seen['body']['can_write']is False,seen
        else:
            assert seen['status']==403 and'CP7_INVOICE_ACCESS_DENIED'in str(seen['body']),seen
        refused=save(staff,p)
        expected='CP7_SUPPLIER_TRANSFER_DENIED'if viewer else'CP7_INVOICE_ACCESS_DENIED'
        assert refused['status']==403 and expected in str(refused['body']),refused
        assert state(http,f)==before
        anon=http.anon_rpc('erp_cp7_save_supplier_transfer_v1',dict(p_payload=p,p_request=str(uuid.uuid4())))
        assert anon['status']in(401,403)and state(http,f)==before,anon
        return dict(status='PASS',role=ROLE,role_has_finance_ap_pay=PAY in perms,staff_can_view=viewer,staff_read=seen['status'],staff_write='403 '+expected,anonymous=anon['status'],zero_effect=True)

    return list(zip(IDS,(journey,revoked,race,denied)))

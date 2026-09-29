"""Fixed native payroll oracles. Real financial writers; no connected writer UI claim."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from datetime import timedelta
from decimal import Decimal as D
import json,threading,time,uuid
import psycopg
import cp7_settlement_read_cases as review
import cp6_bc_probe as bc
n,source,auth,b=review.nota,review.source,review.auth,review.b
PERMS=('finance.payroll.view','finance.payroll.approve','finance.payroll.pay')

def doc(cur,pid,subject=None):return review.read(cur,id=pid,subject=subject)['page']['rows'][0]
def args(d,action,**extra):return dict(id=d['id'],review_token=d['review_token'],change_reason='P12 reviewed native payroll sources',**extra)
def command(cur,action,p,version,key=None,subject=None):
    auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_save_payroll_v1(%s,%s,%s,%s)',(action,json.dumps(p),key or uuid.uuid4(),str(version))).fetchone()[0];b.api.admin(cur);return r
def act(cur,action,d,key=None,subject=None,**extra):return command(cur,action,args(d,action,**extra),d['row_version'],key,subject)
def cash(cur):return bc.bank_account(cur,'P12'+uuid.uuid4().hex[:12])
def gl(cur,contractor):
    return dict(cur.execute('select account_id::text,sum(debit-credit) from erp.journal_lines where contractor_id=%s group by account_id order by account_id',(contractor,)).fetchall())
def change(before,after):return {k:after.get(k,D(0))-before.get(k,D(0)) for k in set(before)|set(after) if before.get(k,D(0))!=after.get(k,D(0))}
def acct(cur,key):return str(cur.execute('select erp.account_id(%s)',(key,)).fetchone()[0])
def journal(cur,pid,kind):return cur.execute("select count(*),coalesce(sum(jl.debit),0),coalesce(sum(jl.credit),0) from erp.journal_entries je join erp.journal_lines jl on jl.journal_entry_id=je.id where je.source_id=%s and je.source_type=%s and je.status='POSTED'",(pid,kind)).fetchone()
def physical(cur):return {k:v for k,v in n.facts(cur).items() if k!='journals'}
def native(cur,sql,values):
    b.chain.production.owner(cur);r=cur.execute(sql,values).fetchone()[0];b.api.admin(cur);return r

def attendance(cur,f,today):
    cur.execute('update erp.contractors set attendance_required=true where id=%s',(f['contractor'],))
    w=native(cur,'select public.erp_save_worker_roster_v1(%s::jsonb,%s,null)',(json.dumps(dict(contractor_id=f['contractor'],worker_code='P12'+uuid.uuid4().hex[:8],worker_name='P12 attendance worker',job_description='Jahit',pay_scheme='DAILY',initial_daily_rate=100,rate_effective_from=str(today),joined_at=str(today),is_active=True,reason='P12 ordinary worker and daily rate')),uuid.uuid4()))
    wid=bc.awp.find(w,'worker_id')
    p=native(cur,'select public.erp_save_attendance_period_v1(%s::jsonb,%s,null,false)',(json.dumps(dict(contractor_id=f['contractor'],period_number='P12-ATT-'+uuid.uuid4().hex[:12],period_start=str(today),period_end=str(today),pay_date=str(today),reason='P12 ordinary posted attendance',attendance=[dict(worker_id=str(wid),attendance_date=str(today),status='PRESENT')])),uuid.uuid4()))
    return native(cur,'select public.erp_post_attendance_period_v1(%s,%s,%s,%s)',(bc.awp.find(p,'period_id'),'P12 reviewed attendance',uuid.uuid4(),bc.awp.find(p,'row_version')))

def cases(cur,today):
    def lifecycle():
        f=review.fixture(cur,today);pid=f['payroll'];bank=cash(cur);coa=str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s',(bank,)).fetchone()[0]);baseline=gl(cur,f['contractor']);stock=physical(cur)
        d=doc(cur,pid);act(cur,'PREPARE',d);d=doc(cur,pid);key=uuid.uuid4();a=act(cur,'APPROVE',d,key);assert act(cur,'APPROVE',d,key)==a
        assert a['status']=='APPROVED' and gl(cur,f['contractor'])==baseline and physical(cur)==stock
        approved=doc(cur,pid);paykey=uuid.uuid4();paid=act(cur,'PAY',approved,paykey,payment_date=str(today),cash_account_id=bank);assert act(cur,'PAY',approved,paykey,payment_date=str(today),cash_account_id=bank)==paid
        assert paid['status']=='PAID' and doc(cur,pid)['net_payable']=='6000.00'
        assert change(baseline,gl(cur,f['contractor']))=={acct(cur,'CONTRACTOR_PAYABLE'):D(6000),coa:D(-6000)} and journal(cur,pid,'PAYROLL_PAYMENT')==(2,D(6000),D(6000))
        assert journal(cur,pid,'PAYROLL_ATTENDANCE_ACCRUAL')[0]==0 and physical(cur)==stock
        auth.refused(cur,lambda:act(cur,'PAY',approved,paykey,payment_date=str(today),cash_account_id=None),'CP7_PAYROLL_REQUEST_CHANGED')
        auth.refused(cur,lambda:act(cur,'CANCEL',doc(cur,pid)),'CP7_PAYROLL_UNPAID_ONLY')
        d=doc(cur,pid);revkey=uuid.uuid4();r=act(cur,'REVERSE',d,revkey);assert act(cur,'REVERSE',d,revkey)==r and r['status']=='REVERSED'
        assert change(baseline,gl(cur,f['contractor']))=={} and physical(cur)==stock
        assert n.read(cur,'SOURCES',contractor_id=f['contractor'])['page']['total']=='2' and n.read(cur,id=f['note'])['page']['rows'][0]['status']=='POSTED'
        return dict(status='PASS',native_full_payment='6000',exact_replay_each_action=True,one_balanced_payment=True,no_second_work_accrual=True,reverse_paid_ends_reversed=True,source_released_note_retained=True,stock_hpp_unchanged=True)
    def selected():
        f=review.fixture(cur,today);source.ax.post(cur,source.ax.repair_payload(f,1));pid=f['payroll'];before=n.facts(cur);items=cur.execute('select id::text,qty_payable,rate_snapshot,amount from erp.payroll_work_items where payroll_id=%s order by id',(pid,)).fetchall()
        for _ in range(2):act(cur,'PREPARE',doc(cur,pid))
        assert cur.execute('select id::text,qty_payable,rate_snapshot,amount from erp.payroll_work_items where payroll_id=%s order by id',(pid,)).fetchall()==items
        assert doc(cur,pid)['labor_total']=='6000.00' and n.read(cur,'SOURCES',contractor_id=f['contractor'])['page']['rows'][0]['remaining_amount']=='2000.00' and n.facts(cur)==before
        return dict(status='PASS',selected_two_cards_unchanged=True,unselected_card_still_available='2000',no_rebuilt_work_ids_or_rates=True,repeated_prepare_no_money_stock_effect=True)
    def attendance_accrual():
        f=review.fixture(cur,today);pid=f['payroll'];attendance(cur,f,today);d=doc(cur,pid);before=n.facts(cur)
        auth.refused(cur,lambda:act(cur,'APPROVE',d),'CP7_PAYROLL_PREPARE_REQUIRED');assert n.facts(cur)==before and doc(cur,pid)==d
        act(cur,'PREPARE',d);d=doc(cur,pid);assert d['attendance_total']=='100.00' and d['labor_total']=='6000.00' and d['net_payable']=='6100.00'
        rows=review.read(cur,'ATTENDANCE',id=pid)['page']['rows'];assert len(rows)==1 and rows[0]['amount']=='100.00' and rows[0]['date']==str(today) and rows[0]['worker_name']=='P12 attendance worker'
        bank=cash(cur);base=gl(cur,f['contractor']);act(cur,'APPROVE',d);approved=gl(cur,f['contractor'])
        assert change(base,approved)=={acct(cur,'WIP'):D(100),acct(cur,'CONTRACTOR_PAYABLE'):D(-100)} and journal(cur,pid,'PAYROLL_ATTENDANCE_ACCRUAL')==(2,D(100),D(100))
        act(cur,'PAY',doc(cur,pid),payment_date=str(today),cash_account_id=bank)
        assert journal(cur,pid,'PAYROLL_ATTENDANCE_ACCRUAL')==(2,D(100),D(100)) and journal(cur,pid,'PAYROLL_PAYMENT')==(2,D(6100),D(6100))
        assert gl(cur,f['contractor']).get(acct(cur,'WIP'),0)==approved.get(acct(cur,'WIP'),0)
        act(cur,'REVERSE',doc(cur,pid));assert change(base,gl(cur,f['contractor']))=={} and doc(cur,pid)['status']=='REVERSED'
        return dict(status='PASS',ordinary_roster_rate_and_posted_attendance=True,approve_requires_current_review=True,labor='6000',attendance='100',net='6100',attendance_accrual_at_approval_once=True,payment_settlement_only=True,inverse_neutral=True)
    def kasbon():
        # The accepted BC note fixture uses 08:00 WIB. Use a completed day for
        # both work/payroll and issue so this remains valid before 08:00 today.
        workday=today-timedelta(days=1)
        f=review.fixture(cur,workday);pid=f['payroll'];fx=bc.fixture(cur,workday,zones=False);_,item=bc.note(cur,fx,10,'1000.00',workday,contractor=f['contractor']);before=n.facts(cur);base=gl(cur,f['contractor'])
        for _ in range(2):act(cur,'PREPARE',doc(cur,pid))
        d=doc(cur,pid);assert (d['labor_total'],d['deduction_total'],d['net_payable'])==('6000.00','6000.00','0.00') and n.facts(cur)==before
        deductions=review.read(cur,'DEDUCTIONS',id=pid)['page']['rows'];assert len(deductions)==1 and deductions[0]['contractor_issue_item_id']==item and deductions[0]['amount']=='6000.00'
        act(cur,'APPROVE',d);act(cur,'PAY',doc(cur,pid),payment_date=str(today),cash_account_id=None)
        assert journal(cur,pid,'PAYROLL_PAYMENT')==(0,D(0),D(0)) and journal(cur,pid,'PAYROLL_MATERIAL_DEDUCTION')==(2,D(6000),D(6000))
        remaining=cur.execute("select erp.bc_note_item_collectible_v1(%s)-coalesce((select sum(d.amount) from erp.payroll_deductions d join erp.payroll_settlements p on p.id=d.payroll_id where d.contractor_issue_item_id=%s and p.status<>'REVERSED'),0)",(item,item)).fetchone()[0]
        assert remaining==4000 and change(base,gl(cur,f['contractor']))=={acct(cur,'CONTRACTOR_PAYABLE'):D(6000),acct(cur,'CONTRACTOR_RECEIVABLE'):D(-6000)}
        act(cur,'REVERSE',doc(cur,pid));assert change(base,gl(cur,f['contractor']))=={}
        assert cur.execute("select coalesce(sum(d.amount),0) from erp.payroll_deductions d join erp.payroll_settlements p on p.id=d.payroll_id where d.contractor_issue_item_id=%s and p.status<>'REVERSED'",(item,)).fetchone()[0]==0
        return dict(status='PASS',ordinary_accessory_note='10000',work='6000',deduction_capped='6000',carry_remains='4000',zero_net_no_cash_journal=True,no_double_prepare_deduction=True,reversal_releases_receivable=True)
    def stale():
        f=review.fixture(cur,today);d=doc(cur,f['payroll']);cur.execute("insert into erp.payroll_deductions(payroll_id,deduction_type,amount,notes) values(%s,'OTHER',1,'External child edit control')",(f['payroll'],));changed=doc(cur,f['payroll']);assert changed['row_version']==d['row_version'] and changed['review_token']!=d['review_token']
        auth.refused(cur,lambda:act(cur,'APPROVE',d),'CP7_PAYROLL_REVIEW_CHANGED')
        auth.refused(cur,lambda:act(cur,'APPROVE',changed),'CP7_PAYROLL_PREPARE_REQUIRED')
        act(cur,'PREPARE',changed);assert doc(cur,f['payroll'])['net_payable']=='5999.00'
        return dict(status='PASS',administrative_child_change_control=True,same_header_version_changed_child_refused=True,no_silent_unreviewed_recalculation=True)
    def access():
        f=review.fixture(cur,today);pid=f['payroll'];subject,role=source.procurement.custom(cur,PERMS[:2]);d=doc(cur,pid,subject);key=uuid.uuid4();prepared=act(cur,'PREPARE',d,key,subject)
        act(cur,'APPROVE',doc(cur,pid,subject),subject=subject)
        auth.refused(cur,lambda:act(cur,'PAY',doc(cur,pid,subject),subject=subject,payment_date=str(today),cash_account_id=cash(cur)),'CP7_PAYROLL_WRITE_DENIED')
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.payroll.approve'",(role,));auth.refused(cur,lambda:act(cur,'PREPARE',d,key,subject),'CP7_PAYROLL_WRITE_DENIED')
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'finance.payroll.pay')",(role,));act(cur,'PAY',doc(cur,pid,subject),subject=subject,payment_date=str(today),cash_account_id=cash(cur))
        auth.refused(cur,lambda:act(cur,'REVERSE',doc(cur,pid,subject),subject=subject),'CP7_PAYROLL_WRITE_DENIED')
        assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in('r','p','v') and has_table_privilege('cp7_payroll_write',c.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
        for who in ('anon','authenticated','service_role','cp7_capture','cp7_payroll_read','cp7_nota_write'):
            assert not cur.execute("select has_table_privilege(%s,'cp7_payroll.settlement_context','INSERT,UPDATE,DELETE')",(who,)).fetchone()[0]
            assert not cur.execute("select has_function_privilege(%s,'cp7_payroll.apply_settlement(text,jsonb,text)','EXECUTE')",(who,)).fetchone()[0]
        return dict(status='PASS',custom_role_not_owner_admin=True,approve_pay_permissions_separate=True,reverse_requires_both_existing_permissions=True,revoked_permission_denies_cached_replay=True,no_private_context_or_generic_business_dml=True)
    def invalid_cancel():
        f=review.fixture(cur,today);pid=f['payroll'];act(cur,'APPROVE',doc(cur,pid));d=doc(cur,pid);bank=cash(cur);before=n.facts(cur)
        auth.refused(cur,lambda:act(cur,'PAY',d,payment_date=str(today+timedelta(days=1)),cash_account_id=bank),'masa depan')
        auth.refused(cur,lambda:act(cur,'PAY',d,payment_date=str(today),cash_account_id=None),'Active payroll cash/bank account')
        auth.refused(cur,lambda:act(cur,'PAY',d,payment_date=str(today),cash_account_id=bank,amount='1'),'CP7_PAYROLL_FIELDS')
        assert doc(cur,pid)==d and n.facts(cur)==before
        key=uuid.uuid4();cancel=act(cur,'CANCEL',d,key);assert act(cur,'CANCEL',d,key)==cancel and cancel['status']=='REVERSED'
        assert n.read(cur,'SOURCES',contractor_id=f['contractor'])['page']['total']=='2' and n.facts(cur)==before
        return dict(status='PASS',future_date_inactive_or_missing_cash_no_partial_write=True,partial_cash_not_falsely_supported=True,native_approved_unpaid_cancellation=True,exact_cancel_replay_and_source_release=True)
    return [('P12_SETTLEMENT_'+k,fn) for k,fn in [('FULL_LIFECYCLE',lifecycle),('PRESERVE_SELECTED_WORK',selected),('ATTENDANCE_ACCRUAL',attendance_accrual),('KASBON_CARRY',kasbon),('STALE_CHILD',stale),('ACCESS',access),('INVALID_PAY_CANCEL',invalid_cancel)]]

def races(tools,today):
    def payments(same):
        with tools.connect() as conn,conn.cursor() as cur:
            f=review.fixture(cur,today);bank=cash(cur);act(cur,'APPROVE',doc(cur,f['payroll']));d=doc(cur,f['payroll']);conn.commit()
        gate=threading.Barrier(2);key=uuid.uuid4()
        def send(i):
            with tools.connect() as conn,conn.cursor() as cur:
                gate.wait()
                try:
                    action='PAY' if same or i==0 else 'CANCEL';extra=dict(payment_date=str(today),cash_account_id=bank) if action=='PAY' else {};r=act(cur,action,d,key if same else uuid.uuid4(),**extra);conn.commit();return ('PASS',r)
                except psycopg.Error as e:conn.rollback();return ('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(send,range(2)))
        if same:assert rows[0]==rows[1] and rows[0][0]=='PASS',rows
        else:assert sorted(x[0] for x in rows)==['PASS','REFUSED'],rows
        with tools.connect() as conn,conn.cursor() as cur:
            status=doc(cur,f['payroll'])['status'];assert status in('PAID','REVERSED');assert journal(cur,f['payroll'],'PAYROLL_PAYMENT')==((2,D(6000),D(6000)) if status=='PAID' else (0,D(0),D(0)))
        return dict(status='PASS',same_request=same,one_native_payment_at_most=True,exact_replay_or_one_version_winner=True)
    def revoke():
        with tools.connect() as conn,conn.cursor() as cur:
            f=review.fixture(cur,today);subject,role=source.procurement.custom(cur,PERMS);d=doc(cur,f['payroll']);conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select id from erp.payroll_settlements where id=%s for update',(f['payroll'],))
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:act(cur,'APPROVE',d,subject=subject);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(send);blocked=False;deadline=time.monotonic()+8
                try:
                    with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()');blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                        assert blocked,'EXPECTED_PAYROLL_ROW_WAIT';c.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,))
                finally:holder.rollback()
                result=future.result(30)
        assert 'ACCESS' in result or 'DENIED' in result,result
        with tools.connect() as conn,conn.cursor() as cur:assert doc(cur,f['payroll'])['status']=='CALCULATED' and journal(cur,f['payroll'],'PAYROLL_ATTENDANCE_ACCRUAL')[0]==0
        return dict(status='PASS',current_authority_after_actual_payroll_lock_wait=True,no_partial_approval=True)
    def new_attendance():
        with tools.connect() as conn,conn.cursor() as cur:
            f=review.fixture(cur,today);d=doc(cur,f['payroll']);conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute('select id from erp.payroll_settlements where id=%s for update',(f['payroll'],))
            def send():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:act(cur,'APPROVE',d);conn.commit();return 'UNEXPECTED_SUCCESS'
                    except psycopg.Error as e:conn.rollback();return str(e).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(send);blocked=False;deadline=time.monotonic()+8
                try:
                    with tools.connect(autocommit=True) as inspect,inspect.cursor() as c:
                        while time.monotonic()<deadline:
                            c.execute('select pg_stat_clear_snapshot()');blocked=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event_type='Lock' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                    assert blocked,'EXPECTED_APPROVAL_ROW_WAIT'
                    with tools.connect() as writer,writer.cursor() as c:attendance(c,f,today);writer.commit()
                finally:holder.rollback()
                result=future.result(30)
        assert 'CP7_PAYROLL_PREPARE_REQUIRED' in result,result
        with tools.connect() as conn,conn.cursor() as cur:
            after=doc(cur,f['payroll']);assert after['status']=='CALCULATED' and after['attendance_total']=='0.00' and journal(cur,f['payroll'],'PAYROLL_ATTENDANCE_ACCRUAL')[0]==0
        return dict(status='PASS',attendance_posted_during_actual_approval_wait=True,unreviewed_new_source_forces_prepare=True,no_partial_recalculation_or_accrual=True)
    return [('P12_SETTLEMENT_RACE_REPLAY',lambda:payments(True)),('P12_SETTLEMENT_RACE_PAY_CANCEL',lambda:payments(False)),('P12_SETTLEMENT_RACE_REVOKE',revoke),('P12_SETTLEMENT_RACE_SOURCE_CHANGE',new_attendance)]

def http_cases(http,today):
    def flow():
        user=http.login('ADMIN','p12-payroll-custom')
        with http.connect() as conn,conn.cursor() as cur:
            f=review.fixture(cur,today);bank=cash(cur);_,role=source.procurement.custom(cur,PERMS);cur.execute("update erp.app_users set role='STAFF',role_id=%s where auth_user_id=%s",(role,user.auth_user_id));conn.commit()
            actual=cur.execute('select r.role_code from erp.app_users u join erp.app_roles r on r.id=u.role_id where u.auth_user_id=%s',(user.auth_user_id,)).fetchone()[0]
            assert actual not in ('OWNER','ADMIN') and actual.startswith('P02_'),actual
        def read():
            r=user.rpc('erp_cp7_get_payroll_workspace_v1',dict(p_section='PAYROLLS',p_query=dict(id=f['payroll'])));assert r['status']==200,r;return r['body']['page']['rows'][0]
        for action in ('PREPARE','APPROVE','PAY'):
            d=read();extra=dict(payment_date=str(today),cash_account_id=bank) if action=='PAY' else {};payload=dict(p_action=action,p_payload=args(d,action,**extra),p_request=str(uuid.uuid4()),p_expected=d['row_version'])
            assert http.anon_rpc('erp_cp7_save_payroll_v1',payload)['status'] in(401,403)
            r=user.rpc('erp_cp7_save_payroll_v1',payload);assert r['status']==200,r;assert user.rpc('erp_cp7_save_payroll_v1',payload)['body']==r['body']
        assert read()['status']=='PAID'
        with http.connect() as conn,conn.cursor() as cur:
            assert journal(cur,f['payroll'],'PAYROLL_PAYMENT')==(2,D(6000),D(6000));cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,));conn.commit()
        assert user.rpc('erp_cp7_save_payroll_v1',payload)['status']==403
        return dict(status='PASS',real_auth_custom_role_native_prepare_approve_pay=True,exact_http_replay_once=True,payment='6000',current_deactivation_denies_replay=True,no_browser_settlement_claim=True)
    return [('P12_SETTLEMENT_HTTP',flow)]

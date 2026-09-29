"""Accepted CP6 opening sources through the CP7 payroll lifecycle.

Fixed oracle: selected work 6000 + old payable 85 + carry 2 x 2.50 -
old cash advance 30 = cash 6060. Only the carry creates new expense (5).
No new opening writer, native history, or partial-cash policy is introduced.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import json, threading, uuid
import psycopg
import cp7_settlement_cases as s
import cp6_bb_probe as bb


def rows(cur, f, today):
    contractor = cur.execute('select contractor_code from erp.contractors where id=%s', (f['contractor'],)).fetchone()[0]
    component = cur.execute('select component_code from erp.work_components where id=%s', (f['component'],)).fetchone()[0]
    old = str(today - timedelta(days=22))
    return {
        'OPENING_BALANCE_ITEM': [
            dict(balance_type=kind, contractor_code=contractor, amount=amount,
                 control_key=kind, document_number=number, document_date=old,
                 original_amount=original, settled_before_cutover=paid, **extra)
            for kind, number, amount, original, paid, extra in (
                ('CONTRACTOR_PAYABLE', 'UPAH-OLD', '65.00', '90.00', '25.00', {}),
                ('CONTRACTOR_PAYABLE', 'REIMB-OLD', '20.00', '20.00', '0.00', {}),
                ('CONTRACTOR_RECEIVABLE', 'KASBON-OLD', '30.00', '30.00', '0.00', {'source_kind': 'CONTRACTOR_CASH_ADVANCE'}))],
        'OPENING_CONTROL': [dict(control_key=kind, balance_type=kind, amount=amount)
                            for kind, amount in (('CONTRACTOR_PAYABLE', '85.00'), ('CONTRACTOR_RECEIVABLE', '30.00'))],
        'OPENING_PAYROLL_ENTITLEMENT': [dict(kind='SEWING_WORK', contractor_code=contractor,
            document_number='UPAH-OLD', line_number='1', document_date=old,
            work_component_code=component, earned_qty='40', paid_before_qty='10', carry_qty='4', rate='2.50')],
    }


def sources(cur, batch):
    bb.api.admin(cur)
    balances = dict(cur.execute('''select f.document_number,b.id::text from erp.initial_import_financial_sources f
        join erp.opening_subledger_balances b on b.opening_item_id=f.opening_item_id
        where f.batch_id=%s''', (batch,)).fetchall())
    e = cur.execute('select id::text from erp.bb_payroll_entitlements_v1 where batch_id=%s', (batch,)).fetchone()
    return dict(batch=str(batch), balances=balances, entitlement=e[0] if e else None)


def fixture(cur, today):
    f = s.review.fixture(cur, today)
    batch, code, cutover = bb.post_batch(cur, today, rows(cur, f, today), prefix='P12OPEN')
    f.update(sources(cur, batch), code=code, cutover=str(cutover), cash=s.cash(cur))
    return f


def payload(cur, f, kind, amount=None, payroll=None):
    pid = payroll or f['payroll']
    common = dict(batch_id=f['batch'], expected_revision=bb.revision(cur, f['batch']),
                  payroll_id=pid, expected_payroll_version=bb.payroll_version(cur, pid))
    if kind == 'CARRY':
        return 'PAYROLL_ENTITLEMENT', dict(common, operation='ALLOCATE_CARRY', entitlement_id=f['entitlement'], qty=amount or '2')
    if kind == 'KASBON-OLD':
        return 'ALLOCATE_CASH_ADVANCE', dict(common, balance_id=f['balances'][kind], amount=amount or '30.00')
    return 'OPENING_SETTLEMENT', dict(common, operation='ALLOCATE_PAYROLL', balance_id=f['balances'][kind],
        amount=amount or ('65.00' if kind == 'UPAH-OLD' else '20.00'), reason='P12 reviewed opening payroll allocation')


def allocate(cur, f, kind, amount=None, payroll=None, key=None):
    action, p = payload(cur, f, kind, amount, payroll)
    return bb.api.call(cur, action, p, key)


def all_sources(cur, f):
    for kind in ('UPAH-OLD', 'REIMB-OLD', 'KASBON-OLD', 'CARRY'):
        allocate(cur, f, kind)


def state(cur, f):
    bb.api.admin(cur)
    return dict(remaining={name: str(bb.balance_row(cur, f, name)[2]) for name in f['balances']},
        carry=str(cur.execute('select carry_qty-erp.bb_entitlement_carry_used_v1(id) from erp.bb_payroll_entitlements_v1 where id=%s', (f['entitlement'],)).fetchone()[0]),
        gl=bb.gl(cur), physical=s.physical(cur))


def assert_remaining(actual, wages, reimburse, advance, carry):
    assert {k: D(v) for k, v in actual['remaining'].items()} == {'UPAH-OLD': D(wages), 'REIMB-OLD': D(reimburse), 'KASBON-OLD': D(advance)}, actual
    assert D(actual['carry']) == D(carry), actual


def work(cur, pid):
    return cur.execute('select id::text,qty_payable,rate_snapshot,amount from erp.payroll_work_items where payroll_id=%s order by id', (pid,)).fetchall()


def cases(cur, today):
    def cycle():
        f=fixture(cur,today); pid=f['payroll']; before=state(cur,f); chosen=work(cur,pid)
        originals=cur.execute("select id::text,status from erp.journal_entries where source_type='OPENING_BALANCE' order by id").fetchall()
        all_sources(cur,f)
        for _ in range(2): s.act(cur,'PREPARE',s.doc(cur,pid))
        d=s.doc(cur,pid)
        assert (d['labor_total'],d['reimburse_total'],d['deduction_total'],d['net_payable'])==('6000.00','90.00','30.00','6060.00'), d
        assert work(cur,pid)==chosen and state(cur,f)['gl']==before['gl']
        assert_remaining(state(cur,f),65,20,30,2)
        s.act(cur,'APPROVE',d)
        assert s.change(before['gl'],bb.gl(cur))=={s.acct(cur,'LABOR_COST'):D(5),s.acct(cur,'CONTRACTOR_PAYABLE'):D(-5)}
        approved=s.doc(cur,pid); key=uuid.uuid4()
        paid=s.act(cur,'PAY',approved,key,payment_date=str(today),cash_account_id=f['cash'])
        assert s.act(cur,'PAY',approved,key,payment_date=str(today),cash_account_id=f['cash'])==paid
        actual=state(cur,f); assert_remaining(actual,0,0,0,2)
        coa=str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s',(f['cash'],)).fetchone()[0])
        assert s.change(before['gl'],actual['gl'])=={s.acct(cur,'LABOR_COST'):D(5),s.acct(cur,'CONTRACTOR_PAYABLE'):D(6085),s.acct(cur,'CONTRACTOR_RECEIVABLE'):D(-30),coa:D(-6060)}
        s.act(cur,'REVERSE',s.doc(cur,pid)); actual=state(cur,f)
        assert_remaining(actual,65,20,30,4)
        assert s.change(before['gl'],actual['gl'])=={} and actual['physical']==before['physical'] and work(cur,pid)==chosen
        assert cur.execute("select id::text,status from erp.journal_entries where source_type='OPENING_BALANCE' order by id").fetchall()==originals
        return dict(status='PASS',old_payable='85',old_advance='30',carry_expense_once='5',work='6000',cash='6060',repeat_prepare_preserves_sources=True,exact_pay_replay=True,inverse_restores_all_sources_and_gl=True,opening_journals_stock_hpp_unchanged=True)

    def edit_release():
        f=fixture(cur,today); before=state(cur,f); all_sources(cur,f)
        for kind,value in (('UPAH-OLD','40'),('REIMB-OLD','0'),('KASBON-OLD','10'),('CARRY','1')): allocate(cur,f,kind,value)
        s.act(cur,'PREPARE',s.doc(cur,f['payroll'])); assert s.doc(cur,f['payroll'])['net_payable']=='6032.50'
        for kind in ('UPAH-OLD','KASBON-OLD','CARRY'): allocate(cur,f,kind,'0')
        s.act(cur,'PREPARE',s.doc(cur,f['payroll'])); assert s.doc(cur,f['payroll'])['net_payable']=='6000.00'
        assert state(cur,f)==before
        return dict(status='PASS',allocation_edit_and_zero_release=True,exact_decimal_carry='2.50',prepare_preserves_reviewed_amount=True,no_financial_effect_before_approval=True)

    def stale():
        f=fixture(cur,today); d=s.doc(cur,f['payroll']); action,p=payload(cur,f,'UPAH-OLD'); allocate(cur,f,'CARRY')
        s.auth.refused(cur,lambda:s.act(cur,'APPROVE',d),'CP7_PAYROLL_')
        # Use the current batch revision to isolate the stale payroll guard.
        p['expected_revision']=bb.revision(cur,f['batch'])
        s.auth.refused(cur,lambda:bb.api.call(cur,action,p),'STALE_VERSION')
        assert s.doc(cur,f['payroll'])['net_payable']=='6005.00'
        return dict(status='PASS',source_allocation_invalidates_old_payroll_review=True,stale_payroll_version_not_hidden_by_batch_revision=True)

    def guards():
        f=fixture(cur,today); before=state(cur,f); other=s.review.fixture(cur,today)
        s.auth.refused(cur,lambda:allocate(cur,f,'CARRY','5'),'Y02_CARRY_EXCEEDS')
        s.auth.refused(cur,lambda:allocate(cur,f,'CARRY','1',other['payroll']),'Y02_CARRY_WRONG_CONTRACTOR')
        assert state(cur,f)['remaining']==before['remaining'] and state(cur,f)['carry']==before['carry']
        all_sources(cur,f); s.act(cur,'APPROVE',s.doc(cur,f['payroll']))
        s.auth.refused(cur,lambda:allocate(cur,f,'CARRY','1'),'Y02_ENTITLEMENT_IN_PAYROLL')
        return dict(status='PASS',carry_cap_and_same_contractor_enforced=True,approved_source_immutable=True)

    def cancel():
        f=fixture(cur,today); before=state(cur,f); all_sources(cur,f); s.act(cur,'APPROVE',s.doc(cur,f['payroll']))
        s.act(cur,'CANCEL',s.doc(cur,f['payroll'])); actual=state(cur,f)
        assert_remaining(actual,65,20,30,4)
        assert s.change(before['gl'],actual['gl'])=={} and actual['physical']==before['physical']
        assert s.doc(cur,f['payroll'])['status']=='REVERSED'
        return dict(status='PASS',approved_unpaid_cancel_releases_all_opening_reservations=True,carry_accrual_inverse=True,no_cash_or_stock_event=True)
    return [('P12_OPENING_LIFECYCLE',cycle),('P12_OPENING_EDIT_RELEASE',edit_release),('P12_OPENING_STALE_REVIEW',stale),('P12_OPENING_GUARDS',guards),('P12_OPENING_CANCEL',cancel)]


def races(tools,today):
    def race(same):
        with tools.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today); other=s.n.seed_header(cur,f,today+timedelta(days=1),today+timedelta(days=1))
            commands=[payload(cur,f,'CARRY','4'),payload(cur,f,'CARRY','4',other)]; conn.commit()
        gate=threading.Barrier(2); key=uuid.uuid4()
        def send(i):
            with tools.connect() as conn,conn.cursor() as cur:
                gate.wait()
                try:
                    action,p=commands[0 if same else i]; r=bb.api.call(cur,action,p,key if same else uuid.uuid4()); conn.commit(); return ('PASS',r)
                except psycopg.Error as e: conn.rollback(); return ('REFUSED',str(e).splitlines()[0])
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(send,range(2)))
        if same: assert results[0]==results[1] and results[0][0]=='PASS',results
        else: assert sorted(r[0] for r in results)==['PASS','REFUSED'],results
        with tools.connect() as conn,conn.cursor() as cur:
            assert D(state(cur,f)['carry'])==0
            assert cur.execute('select count(*),sum(opening_carry_qty),sum(amount) from erp.payroll_reimbursements where opening_carry_entitlement_id=%s',(f['entitlement'],)).fetchone()==(1,D(4),D(10))
        return dict(status='PASS',same_request=same,concurrent_import_revision_and_payroll_admission=True,one_carry_allocation=True,total_qty='4',amount='10')
    return [('P12_OPENING_RACE_REPLAY',lambda:race(True)),('P12_OPENING_RACE_RESERVATION',lambda:race(False))]


def http_cases(http,today):
    def flow():
        user=http.login('OWNER','p12-opening-pipeline')
        with http.connect() as conn,conn.cursor() as cur:
            f=fixture(cur,today); action,p=payload(cur,f,'CARRY'); conn.commit()
        request=dict(p_action=action,p_payload=p,p_client_request_id=str(uuid.uuid4()))
        assert http.anon_rpc('erp_save_initial_import_action_v1',request)['status'] in (401,403)
        r=user.rpc('erp_save_initial_import_action_v1',request); assert r['status']==200,r
        assert user.rpc('erp_save_initial_import_action_v1',request)['body']==r['body']
        with http.connect() as conn,conn.cursor() as cur:
            assert s.doc(cur,f['payroll'])['net_payable']=='6005.00'
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,)); conn.commit()
        denied=user.rpc('erp_save_initial_import_action_v1',request)
        # Accepted CP6 require_owner_admin raises P0001 (HTTP400), not42501.
        # Check the exact denial and absence of effect, not any HTTP failure.
        assert denied['status']==400 and denied['body'].get('code')=='P0001' and denied['body'].get('message')=='OWNER or ADMIN access required',denied
        with http.connect() as conn,conn.cursor() as cur:
            assert s.doc(cur,f['payroll'])['net_payable']=='6005.00'
            assert cur.execute('select count(*),sum(opening_carry_qty) from erp.payroll_reimbursements where opening_carry_entitlement_id=%s',(f['entitlement'],)).fetchone()==(1,D(2))
        return dict(status='PASS',real_auth_accepted_opening_writer=True,exact_replay_one_allocation=True,current_deactivation_denies_cached_replay=True,denial_http_status=400,denial_code='P0001',no_effect_after_denied_replay=True)
    return [('P12_OPENING_HTTP',flow)]

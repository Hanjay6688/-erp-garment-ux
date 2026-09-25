"""BB (writer): two-session races and real-HTTP cases of the open cutover states (auditor handoff T2, M:5311), run in the
auditor runtime (cp6-auditor-scenario.yml, phase after = the candidate with BB) as the writer's own scenario file, committed
here with its sha256. Label: WRITER_SCENARIO on the auditor runtime, not independent evidence, not release evidence.

Oracles (written before the runs, from the contract and the BB oracles already in scripts/cp6_bb_probe.py):
  RACE  one opening balance, two sessions. A balance never pays or promises more than it has: the second session waits
        for the first (row lock on the balance) and, once the first commits, is refused with the capacity code; when the
        first aborts, the second succeeds. Afterwards settled + promised <= opening amount and the ledger matches.
          settle vs settle (65.00 open, 40.00 each)                 -> 'Settlement exceeds opening outstanding'
          payroll vs payroll (60.00 open, 40.00 to two payrolls)    -> BB_OPENING_PAYABLE_EXCEEDS_AVAILABLE
          payroll vs settle (60.00 open, 40.00 promised, 40.00 cash) -> 'Settlement exceeds opening outstanding'
          public facade vs public facade (same balance, same revision) -> the second is refused STALE_VERSION
  HTTP  real Auth users through the real PostgREST: OWNER may settle an opening balance, cancel an open purchase order
        remainder and allocate a carried wage; GUDANG and anon are refused and nothing changes.
"""
from datetime import timedelta
import json,uuid
import cp6_bb_probe as bbp

api=bbp.api


def _fixture(tools,today,documents,bank='200.00'):
    with tools.connect() as conn,conn.cursor() as cur:
        fx=bbp.financial_fixture(cur,today,documents=documents,bank=bank);conn.commit()
    return fx


def _state(tools,balance):
    with tools.connect() as conn,conn.cursor() as cur:
        row=cur.execute("""select b.original_amount,b.settled_amount,erp.bb_opening_balance_reserved_v1(b.id),
            (select count(*) from erp.opening_subledger_settlements s where s.balance_id=b.id and s.status='POSTED')
          from erp.opening_subledger_balances b where b.id=%s""",(balance,)).fetchone()
        truth=bbp.truth(cur);conn.rollback()
    return dict(original=str(row[0]),settled=str(row[1]),promised=str(row[2]),posted=row[3],within=row[1]+row[2]<=row[0],truth=truth)


def _settle(fx,number,amount,day):
    def op(cur):
        api.admin(cur)
        sid=cur.execute("""insert into erp.opening_subledger_settlements(settlement_number,balance_id,amount,cash_account_id,physical_at,status,created_by)
          values(%s,%s,%s,%s,%s,'DRAFT',null) returning id""",('BBR-'+uuid.uuid4().hex,fx['balances'][number],amount,fx['cash'],
                                                              str(day)+'T10:00:00+07:00')).fetchone()[0]
        bbp.bap.api.ordinary(cur);cur.execute('select erp.post_opening_subledger_settlement(%s)',(sid,));api.admin(cur)
        return str(sid)
    return op


def _payroll(tools,fx,today,back):
    with tools.connect() as conn,conn.cursor() as cur:
        api.admin(cur)
        contractor=cur.execute('select id from erp.contractors where contractor_code=%s',(fx['code'],)).fetchone()[0]
        day=today-timedelta(days=back)
        p=cur.execute("""insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,manual_adjustment,payment_date,
            payment_cash_account_id) values(%s,%s,%s,%s,0,%s,%s) returning id,row_version""",('BBR-'+uuid.uuid4().hex,contractor,day,day,today,fx['cash'])).fetchone()
        conn.commit()
    return str(p[0]),p[1]


def _allocate(fx,number,payroll,version,amount):
    def op(cur):
        api.admin(cur)
        cur.execute('select erp.bb_set_opening_payable_payroll_v1(%s,%s,%s,%s)',(fx['balances'][number],payroll,amount,version))
        return 'ALLOCATED'
    return op


def _facade_settle(fx,number,amount,day,revision):
    def op(cur):
        return api.call(cur,'OPENING_SETTLEMENT',dict(batch_id=fx['batch'],expected_revision=revision,operation='SETTLE',
            balance_id=fx['balances'][number],amount=amount,effective_date=str(day),cash_account_id=fx['cash'],reason='BB race facade'))['status']
    return op


def _verdict(kind,commit,held,contention,outcome,state,code,expect_settled,expect_promised):
    refused=not outcome.get('ok') and code in (outcome.get('message') or '')
    second_ok=outcome.get('ok') is True
    ok=(contention.get('kind')=='BLOCKED' and contention.get('holder_blocks_worker') is True
        and (refused if commit else second_ok) and state['within'] and state['settled']==expect_settled and state['promised']==expect_promised
        and all(v==0 for v in state['truth'].values()))
    return dict(status='PASS' if ok else 'FAIL',race=kind,first_committed=commit,held=held,contention=contention,second=outcome,state=state,
                expected=dict(second='REFUSED '+code if commit else 'SUCCEEDS',settled=expect_settled,promised=expect_promised))


def settle_vs_settle(tools,today,commit):
    fx=_fixture(tools,today,[('SUPPLIER_PAYABLE','INV-R','100.00','35.00')])
    held,contention,outcome=tools.two_sessions(_settle(fx,'INV-R','40.00',today),_settle(fx,'INV-R','40.00',today),commit)
    state=_state(tools,fx['balances']['INV-R'])
    return _verdict('SETTLE_VS_SETTLE',commit,held,contention,outcome,state,'Settlement exceeds opening outstanding','40.00','0')


def payroll_vs_payroll(tools,today,commit):
    fx=_fixture(tools,today,[('CONTRACTOR_PAYABLE','UPAH-R','60.00','0.00')])
    p1,v1=_payroll(tools,fx,today,2);p2,v2=_payroll(tools,fx,today,1)
    held,contention,outcome=tools.two_sessions(_allocate(fx,'UPAH-R',p1,v1,'40.00'),_allocate(fx,'UPAH-R',p2,v2,'40.00'),commit)
    state=_state(tools,fx['balances']['UPAH-R'])
    return _verdict('PAYROLL_VS_PAYROLL',commit,held,contention,outcome,state,'BB_OPENING_PAYABLE_EXCEEDS_AVAILABLE','0.00','40.00')


def payroll_vs_settle(tools,today,commit):
    fx=_fixture(tools,today,[('CONTRACTOR_PAYABLE','UPAH-S','60.00','0.00')])
    p1,v1=_payroll(tools,fx,today,1)
    held,contention,outcome=tools.two_sessions(_allocate(fx,'UPAH-S',p1,v1,'40.00'),_settle(fx,'UPAH-S','40.00',today),commit)
    state=_state(tools,fx['balances']['UPAH-S'])
    expect=('0.00','40.00') if commit else ('40.00','0')
    return _verdict('PAYROLL_VS_SETTLE',commit,held,contention,outcome,state,'Settlement exceeds opening outstanding',*expect)


def facade_vs_facade(tools,today):
    fx=_fixture(tools,today,[('SUPPLIER_PAYABLE','INV-F','100.00','35.00')])
    with tools.connect() as conn,conn.cursor() as cur:
        revision=bbp.revision(cur,fx['batch']);conn.rollback()
    held,contention,outcome=tools.two_sessions(_facade_settle(fx,'INV-F','40.00',today,revision),_facade_settle(fx,'INV-F','40.00',today,revision),True)
    state=_state(tools,fx['balances']['INV-F'])
    return _verdict('FACADE_VS_FACADE',True,held,contention,outcome,state,'STALE_VERSION','40.00','0')


def races(tools,today):
    return [('BB_RACE:SETTLE_VS_SETTLE_FIRST_COMMITS',lambda:settle_vs_settle(tools,today,True)),
            ('BB_RACE:SETTLE_VS_SETTLE_FIRST_ABORTS',lambda:settle_vs_settle(tools,today,False)),
            ('BB_RACE:PAYROLL_VS_PAYROLL_FIRST_COMMITS',lambda:payroll_vs_payroll(tools,today,True)),
            ('BB_RACE:PAYROLL_VS_PAYROLL_FIRST_ABORTS',lambda:payroll_vs_payroll(tools,today,False)),
            ('BB_RACE:PAYROLL_VS_SETTLE_FIRST_COMMITS',lambda:payroll_vs_settle(tools,today,True)),
            ('BB_RACE:PUBLIC_FACADE_SAME_REVISION',lambda:facade_vs_facade(tools,today))]


# ---------------------------------------------------------------- real HTTP (Auth + PostgREST)

def _save(user,action,batch,revision,**payload):
    return user.rpc('erp_save_initial_import_action_v1',dict(p_action=action,p_payload=dict(batch_id=batch,expected_revision=revision,**payload),
                                                            p_client_request_id=str(uuid.uuid4())))


def _workspace(user,batch):
    r=user.rpc('erp_get_initial_import_workspace_v1',dict(p_batch_id=batch))
    return r['body']['batch'] if r['status']==200 else None


def _roles(http,today,build,action,payload,check):
    """OWNER succeeds, GUDANG and anon are refused with nothing changed (read back as admin before and after)."""
    fx=build()
    owner=http.login('OWNER','bb-owner');store=http.login('GUDANG','bb-gudang')
    rev=_workspace(owner,fx['batch'])['revision']
    before=check(fx)
    denied=_save(store,action,fx['batch'],rev,**payload(fx))
    anon=http.anon_rpc('erp_save_initial_import_action_v1',dict(p_action=action,p_payload=dict(batch_id=fx['batch'],expected_revision=rev,**payload(fx)),
                                                                   p_client_request_id=str(uuid.uuid4())))
    unchanged=check(fx)
    done=_save(owner,action,fx['batch'],rev,**payload(fx))
    after=check(fx)
    ok=(denied['status']>=400 and anon['status'] in (401,403) and unchanged==before and done['status']==200
        and isinstance(done['body'],dict) and done['body'].get('status')=='POSTED' and after!=before)
    return dict(status='PASS' if ok else 'FAIL',action=action,gudang=dict(status=denied['status'],message=(denied['body'] or {}).get('message') if isinstance(denied['body'],dict) else None),
                anon=dict(status=anon['status']),owner=dict(status=done['status'],result=done['body'] if done['status']!=200 else {k:done['body'].get(k) for k in ('action','status')}),
                before=before,unchanged=unchanged,after=after)


def http_cases(http,today):
    def settle():
        def build():
            with http.connect() as conn,conn.cursor() as cur:
                fx=bbp.financial_fixture(cur,today,documents=[('SUPPLIER_PAYABLE','INV-H','100.00','35.00')]);conn.commit()
            return fx
        def check(fx):
            with http.connect() as conn,conn.cursor() as cur:
                return str(cur.execute('select settled_amount from erp.opening_subledger_balances where id=%s',(fx['balances']['INV-H'],)).fetchone()[0])
        return _roles(http,today,build,'OPENING_SETTLEMENT',lambda fx:dict(operation='SETTLE',balance_id=fx['balances']['INV-H'],amount='20.00',
                      effective_date=str(today),cash_account_id=fx['cash'],reason='BB HTTP settle'),check)

    def cancel():
        def build():
            with http.connect() as conn,conn.cursor() as cur:
                batch,code,cutover=bbp.post_batch(cur,today,bbp.p04_rows(today-timedelta(days=10)))
                conn.commit()
            return dict(batch=batch,code=code)
        def line(fx):
            with http.connect() as conn,conn.cursor() as cur:
                return cur.execute('''select l.id::text,erp.bb_commitment_line_remaining_v1(l.id)::text,c.id::text from erp.bb_purchase_commitment_lines_v1 l
                  join erp.bb_purchase_commitments_v1 c on c.id=l.commitment_id where c.batch_id=%s''',(fx['batch'],)).fetchone()
        def check(fx):return line(fx)[1]
        def payload(fx):
            # 4 of the 10 remaining are cancelled; the native draft receipt of the remainder stays (only REOPEN needs it posted).
            l=line(fx);return dict(operation='CANCEL',commitment_id=l[2],line_id=l[0],qty='4',effective_date=str(today),reason='BB HTTP cancel')
        return _roles(http,today,build,'PURCHASE_COMMITMENT',payload,check)

    def carry():
        def build():
            with http.connect() as conn,conn.cursor() as cur:
                fx=bbp.y02_post(cur,today);conn.commit()
                p,v=None,None
                api.admin(cur)
                p=cur.execute("""insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,manual_adjustment,payment_date,
                    payment_cash_account_id) values(%s,%s,%s,%s,0,%s,%s) returning id""",('BBH-'+uuid.uuid4().hex,fx['contractor'],today,today,today,fx['cash'])).fetchone()[0]
                conn.commit()
            fx['payroll']=str(p);return fx
        def entitlement(fx):
            with http.connect() as conn,conn.cursor() as cur:
                return cur.execute("select id::text from erp.bb_payroll_entitlements_v1 where batch_id=%s and kind='SEWING_WORK'",(fx['batch'],)).fetchone()[0]
        def check(fx):
            with http.connect() as conn,conn.cursor() as cur:
                return str(cur.execute('select coalesce(sum(opening_carry_qty),0) from erp.payroll_reimbursements where payroll_id=%s',(fx['payroll'],)).fetchone()[0])
        def payload(fx):
            with http.connect() as conn,conn.cursor() as cur:
                version=str(cur.execute('select row_version from erp.payroll_settlements where id=%s',(fx['payroll'],)).fetchone()[0])
            return dict(operation='ALLOCATE_CARRY',entitlement_id=entitlement(fx),payroll_id=fx['payroll'],qty='2',expected_payroll_version=version)
        return _roles(http,today,build,'PAYROLL_ENTITLEMENT',payload,check)

    return [('BB_HTTP:OPENING_SETTLEMENT_OWNER_ONLY',settle),
            ('BB_HTTP:PURCHASE_COMMITMENT_OWNER_ONLY',cancel),
            ('BB_HTTP:PAYROLL_ENTITLEMENT_OWNER_ONLY',carry)]

"""E03 selected custody/service branch after an actual partial sales return.

Customer custody does not grant company stock or refundable customer credit.
This deliberately does not claim a cash refund for an unpaid invoice.
"""
from datetime import timedelta, timezone
from decimal import Decimal as D
import json
import uuid
import cp7_f03_e01_cases as e01
import cp6_bc_probe as bc


def protected(cur):
    tables = ('fg_lots', 'fg_stock_movements', 'hpp_versions', 'hpp_version_components',
              'contractor_accessory_reimbursement_entitlements', 'sales_headers',
              'sales_items', 'sales_return_items', 'sale_stock_allocations')
    zone = cur.execute('show timezone').fetchone()[0]
    try:
        cur.execute("select set_config('TimeZone','UTC',true)")
        return {t:cur.execute('select md5(coalesce(jsonb_agg(to_jsonb(x) order by x.id),\'[]\'::jsonb)::text) from erp.'+t+' x').fetchone()[0] for t in tables}
    finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))


def fixture(cur, today):
    acc = bc.fixture(cur, today, purchase=False, zones=True)
    receipt = e01.procurement.command(cur, 'SAVE_DRAFT', dict(purchase_number=acc['code']+'-FINAL', supplier_id=acc['supplier'], location_id=acc['main'], physical_at=bc.local_at(today-timedelta(days=3), 9), change_reason='E03 ten service buttons at two, final supplier price', lines=[dict(material_id=acc['material'], qty='10', unit_price='2', price_state='FINAL', price_source='SUPPLIER_INVOICE', rolls=[])]))
    e01.procurement.post(cur, receipt)
    expense = str(cur.execute("insert into erp.chart_accounts(account_code,account_name,account_type,report_group,normal_balance,is_postable,is_active) values(%s,'E03 customer service expense','EXPENSE','OPERATING_EXPENSES','DEBIT',true,true) returning id", (acc['code']+'EXP',)).fetchone()[0])
    bc.policy(cur, 'ACC_DEC04', dict(CUSTOMER_SERVICE_account_id=expense))
    f = e01.production(cur, today)
    now = e01.source.fg.ax.r1.now(cur)
    f.update(service_accessory=acc, service_expense=expense, sale_at=(now-timedelta(minutes=60)).isoformat(), today=str(today), custody_description='E03 repair '+f['tag'])
    e01.drafts.create(cur, f, e01.drafts.payload(f, '20', '25'))
    p, v = e01.cmd.review(cur, f)
    e01.cmd.command(cur, 'POST', p, v)
    e01.payments.pay(cur, f, '200')
    f['allocations'] = e01.returns.read(cur, f)['page']['rows']
    p, v = e01.returns.payload(cur, f, qty='5', refund='125')
    p['physical_at'] = (now-timedelta(minutes=30)).isoformat()
    e01.cmd.command(cur, 'RETURN', p, v)
    assert e01.physical(cur, f) == 45 and e01.source.read(cur, f)['detail']['financial']['open_balance'] == '175.00'
    service_at = lambda minutes:(now-timedelta(minutes=minutes)).astimezone(timezone(timedelta(hours=7))).isoformat(timespec='seconds')
    f.update(service_in_at=service_at(20), service_use_at=service_at(15), service_out_at=service_at(10))
    # One of the fifteen garments still owned by this customer enters custody.
    # The five company returns above are a different physical quantity.
    f['service_reference'] = 'Invoice '+f['sale']+'; one of 15 retained customer-owned garments'
    return f


def incoming(f):
    return dict(customer_id=f['customer'], product_id=f['product'], description=f['custody_description'], qty='1', physical_at=f['service_in_at'], reference=f['service_reference'], reason='Customer retains ownership during repair')


def consume(f, custody):
    return dict(location_id=f['service_accessory']['main'], items=[dict(material_id=f['service_accessory']['material'], qty='2', physical_at=f['service_use_at'], purpose='CUSTOMER_SERVICE', customer_custody_id=custody)], reference=f['service_reference'], reason='Two actual company accessories consumed on customer garment')


def outgoing(f, custody):
    return dict(custody_id=custody, physical_at=f['service_out_at'], reason='Repaired garment returned to its customer owner', reference=f['service_reference'])


def observe(cur, f):
    c = cur.execute("select c.id::text,c.out_document_id::text,coalesce(d.status='POSTED',false) from erp.bc_customer_custody_v1 c left join erp.bc_documents_v1 d on d.id=c.out_document_id where c.customer_id=%s and c.description=%s order by c.id", (f['customer'], f['custody_description'])).fetchall()
    return dict(protected=protected(cur), accounts=e01.cmd.accounts(cur), accessory_qty=bc.stock(cur, f['service_accessory']['material'], f['service_accessory']['main']), custody=[dict(id=i,out_document=o,returned=r) for i,o,r in c], report=e01.ready_report(cur, f['today'], f['sale_at'], f['service_in_at'], f['service_use_at'], f['service_out_at']), fg=e01.physical(cur, f), invoice=e01.source.read(cur, f)['detail']['financial'])


def assert_service(cur, f, before, returned):
    after = observe(cur, f)
    expected = {e01.cmd.mapping(cur, 'MATERIAL_INVENTORY'):D(-4), f['service_expense']:D(4)}
    assert e01.cmd.delta(before['accounts'], after['accounts']) == expected, ('E03_SERVICE_LEDGER', expected, after['accounts'])
    assert before['protected'] == after['protected'], 'E03_CUSTOMER_CUSTODY_CHANGED_COMPANY_FG_HPP_OR_SALE'
    assert before['accessory_qty'] == 10 and after['accessory_qty'] == 8
    assert len(after['custody']) == 1 and after['custody'][0]['returned'] is returned
    assert after['fg'] == 45 and after['invoice'] == before['invoice'] and after['invoice']['open_balance'] == '175.00'
    for section, key, expected in [('performance','operating_and_other_expense',4),('performance','sales_revenue_gl',0),('performance','cogs_gl',0),('performance','gross_profit',0),('financial_position','cash',0),('financial_position','customer_ar',0),('financial_position','fg_inventory',0)]:
        assert e01.finance.change(before['report'], after['report'], section, key) == expected, ('E03_REPORT', section, key)
    return after


def flow(cur, today):
    f = fixture(cur, today)
    before = observe(cur, f)
    key = uuid.uuid4(); payload = incoming(f)
    entered = bc.svc(cur, 'CUSTOMER_GARMENT_IN', payload, key)
    assert bc.svc(cur, 'CUSTOMER_GARMENT_IN', payload, key) == entered
    assert protected(cur) == before['protected'] and e01.cmd.accounts(cur) == before['accounts']
    custody = entered['custody_id']
    usekey = uuid.uuid4(); usepayload = consume(f, custody)
    used = bc.svc(cur, 'INTERNAL_USE', usepayload, usekey)
    assert bc.svc(cur, 'INTERNAL_USE', usepayload, usekey) == used
    assert_service(cur, f, before, False)
    denied = bc.refused(cur, lambda:bc.svc(cur, 'INTERNAL_USE', dict(usepayload, items=[dict(usepayload['items'][0], purpose='FACTORY_USE')])), 'BC_CUSTODY_INVALID')
    assert denied['ok'], denied
    outkey = uuid.uuid4(); outpayload = outgoing(f, custody)
    out = bc.svc(cur, 'CUSTOMER_GARMENT_OUT', outpayload, outkey)
    assert bc.svc(cur, 'CUSTOMER_GARMENT_OUT', outpayload, outkey) == out
    after = assert_service(cur, f, before, True)
    closed = bc.refused(cur, lambda:bc.svc(cur, 'INTERNAL_USE', usepayload), 'BC_CUSTODY_INVALID')
    twice = bc.refused(cur, lambda:bc.svc(cur, 'CUSTOMER_GARMENT_OUT', outpayload), 'BC_CUSTODY_CLOSED')
    assert closed['ok'] and twice['ok'], (closed, twice)
    boundary = e01.b.boundary.snapshot(cur)
    forged = bc.denied(cur, lambda:bc.svc(cur, 'CUSTOMER_GARMENT_IN', dict(payload, refund_amount='25', cash_account_id=f['bank'])), 'contains unexpected key')
    assert forged['ok'] and e01.b.boundary.snapshot(cur) == boundary
    # Dependency-order inverse changes only linked service facts; the original
    # invoice/return/FG/HPP and customer cash stay exactly as before service.
    bc.reverse(cur, out['document_id'])
    bc.reverse(cur, used['document_id'])
    bc.reverse(cur, entered['document_id'])
    assert protected(cur) == before['protected'] and e01.cmd.accounts(cur) == before['accounts']
    assert bc.stock(cur, f['service_accessory']['material'], f['service_accessory']['main']) == 10
    return dict(status='PASS',journey='E03_SELECTED_CUSTOMER_CUSTODY_SERVICE',source_ids={k:f[k] for k in ('po','sale','customer','product')},production_checkpoints=f['trace'],company_return5_then_one_distinct_customer_owned_garment=True,company_FG45_HPP15_AR175_cash200_unchanged=True,accessory10_to8_cost4=True,expense4_not_company_HPP_or_customer_entitlement=True,custody_replay_once=True,service_replay_once=True,returned_to_customer=True,closed_source_and_wrong_purpose_refused=True,forged_refund_fields_refused=True,dependency_inverse_restored=True,report_confidence=after['report']['snapshot']['data_confidence'],cash_refund_eligible_credit=False,cash_refund_execution_claim=False,full_E03_acceptance=False,full_family_acceptance=False)


def cases(cur, today):
    return [('F03_E03_NATIVE_CUSTODY_SERVICE_INVERSE', lambda:flow(cur, today))]


def http_cases(http, today):
    def run():
        owner = http.login('OWNER', 'e03-owner')
        with http.connect() as conn, conn.cursor() as cur:
            had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
            acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
            if not had:cur.execute('grant usage on schema erp to authenticated')
            f = fixture(cur, today); before = observe(cur, f)
            if not had:cur.execute('revoke usage on schema erp from authenticated')
            assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
            conn.commit()
        def send(action, payload):
            args = dict(p_action=action,p_payload=payload,p_client_request_id=str(uuid.uuid4()))
            assert http.anon_rpc('erp_save_accessory_service_action_v1',args)['status'] in (401,403)
            r = owner.rpc('erp_save_accessory_service_action_v1',args)
            assert r['status'] == 200, r
            assert owner.rpc('erp_save_accessory_service_action_v1',args)['body'] == r['body']
            return r['body'],args
        entered,_ = send('CUSTOMER_GARMENT_IN',incoming(f))
        send('INTERNAL_USE',consume(f,entered['custody_id']))
        _,args = send('CUSTOMER_GARMENT_OUT',outgoing(f,entered['custody_id']))
        with http.connect() as conn, conn.cursor() as cur:
            result = assert_service(cur,f,before,True)
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_save_accessory_service_action_v1',args)['status'] == 403
        return dict(status='PASS',journey='E03_SELECTED_CUSTOMER_CUSTODY_SERVICE',real_Auth_HTTP=True,current_revocation_before_cached_replay=True,anonymous_denied=True,source_production_and_sale_return_native=True,service_expense4_company_FG_HPP_AR_cash_unchanged=True,report_confidence=result['report']['snapshot']['data_confidence'],cash_refund_execution_claim=False,full_E03_acceptance=False,full_family_acceptance=False)
    return [('F03_E03_HTTP_CUSTODY_SERVICE', run)]

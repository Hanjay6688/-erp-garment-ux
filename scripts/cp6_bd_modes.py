"""BD (writer): two-session races and real-HTTP cases of the laundry price, invoice and ALL-W05 flows, run in the auditor runtime
(cp6-auditor-scenario.yml, phase after = the candidate with BD) as the writer's own scenario file. Label: WRITER_SCENARIO on the
auditor runtime, not independent evidence, not release evidence.

Oracles (written before the runs, from the contract and the BD probe oracles: LAU-T19 capacity, LAU-T12 unknown price, LAU-DEC
owner settings, ALL-W05 r9 "concurrent return/claim consuming same PCS", "double vendor charge"):
  RACE  the second session waits for the first (a row or advisory lock the first holds) and, once the first commits, is refused
        with the stated code; when the first aborts, the second succeeds. Each source is consumed once.
          INV  two invoices each billing all 10 GOOD of one receipt line                -> BD_INVOICE_CAPACITY; 10 billed once
          W05  completing the 7 unheld opening pieces vs a new claim on 1 of them. The import facade's WIP_OUTPUT serializes
               by the pocket-period try-lock (AR): while the first holds it the second request is refused at once with
               POCKET_PERIOD_BUSY (nothing written); the same request (the remaining it read) retried after the first ends is
               refused STALE_VERSION when the first committed, and succeeds when it aborted. 7 completed and 1 held, or 2
               held and nothing completed.
          PRC  two owners setting the same unknown component price                      -> BD_PRICE_ALREADY_KNOWN; set once
          POL  two owner LAU-DEC04 changes from the same version                         -> STALE_VERSION; one version step
          EST  posting an invoice that fully bills an opening record with an unknown estimate vs the owner setting its estimate
               -> BD_W05_ALREADY_BILLED; either the invoice or the estimate, never an accrual on a billed record
  HTTP  real Auth users through the real PostgREST: ADMIN may not set a laundry policy (BD_OWNER_ONLY), OWNER may, anon is
        refused; PRODUKSI_QC (laundry view, no money permission) reads the BD workspace with every amount hidden (invoices and
        billable sources null, prices null, an unknown price still UNKNOWN) and cannot draft an invoice; OWNER drafts it; a
        W05 claim on opening WIP is owner/admin only (PRODUKSI_QC refused, OWNER opens it).
"""
from contextlib import contextmanager
from datetime import timedelta
import json,uuid
import psycopg
import cp6_bd_probe as bdp

bbp,bcp,api=bdp.bbp,bdp.bcp,bdp.api
D=bdp.D


def _verdict(race,commit,held,contention,outcome,code,state,ok_state):
    refused=not outcome.get('ok') and code in (outcome.get('message') or '')
    ok=(contention.get('kind')=='BLOCKED' and contention.get('holder_blocks_worker') is True
        and (refused if commit else outcome.get('ok') is True) and ok_state)
    return dict(status='PASS' if ok else 'FAIL',race=race,first_committed=commit,held=str(held)[:300],contention=contention,second=outcome,state=state,
                expected=dict(second='REFUSED '+code if commit else 'SUCCEEDS'))


def _read(tools,fn):
    with tools.connect() as conn,conn.cursor() as cur:
        value=fn(cur);conn.rollback()
    return value


# ---------------------------------------------------------------- INV: one receipt line, two invoices
def inv_two_posts(tools,today,commit):
    with tools.connect() as conn,conn.cursor() as cur:
        fx=bdp.fixture(cur,today-timedelta(days=1),'RACE-INV');bdp.process_rate(cur,fx,'7000.00');bdp.invoice_policies(cur)
        line=bdp.receipt_line(cur,bdp.receive(cur,bdp.plain_delivery(cur,fx,10,11),fx,10,13)['receipt_id'])
        a,_=bdp.invoice(cur,fx,[dict(line=line,qty=10,amount='70000.00')],'70000.00',post=False)
        b,_=bdp.invoice(cur,fx,[dict(line=line,qty=10,amount='70000.00')],'70000.00',post=False);conn.commit()
    post=lambda draft:(lambda cur:bdp.post_draft(cur,draft)['status'])
    held,contention,outcome=tools.two_sessions(post(a),post(b),commit)
    billed=_read(tools,lambda cur:bdp.one(cur,'select erp.bd_invoice_billed_v1(%s,%s)',line,'GOOD'))
    return _verdict('INV_TWO_POSTS',commit,held,contention,outcome,'BD_INVOICE_CAPACITY',dict(billed=billed),billed==10)


# ---------------------------------------------------------------- W05: completion vs a new claim on the same pieces
def w05_rows(today):
    """The probe's W05 fixture with a brand name unique per batch (these copies keep what each race committed)."""
    rows=bdp.w05_rows(today)
    for brand in rows.get('BRAND',[]):brand['brand_name']='BD brand {C}'
    return rows


def w05_complete_vs_claim(tools,today,commit):
    with tools.connect() as conn,conn.cursor() as cur:
        fx=bbp.production_post(cur,today,w05_rows(today));conn.commit()
    request={}
    def complete(cur):return bbp.complete(cur,fx,today,7)['operation']
    def claim(cur):
        s=bbp.source_of(cur,fx)
        request.update(batch_id=fx['batch'],opening_item_id=s['opening_item_id'],expected_remaining=str(s['remaining_qty_pcs']),operation='OPEN_CLAIM',
                       claim_number=fx['code']+'-RACE',claim_type='STUCK',qty_pcs='1',date=str(today),reason='BD race claim')
        return api.call(cur,'WIP_OUTPUT',dict(request))['operation']
    held,contention,outcome=tools.two_sessions(complete,claim,commit)
    busy=not outcome.get('ok') and 'POCKET_PERIOD_BUSY' in (outcome.get('message') or '')
    retry=None
    if request:
        with tools.connect() as conn,conn.cursor() as cur:
            try:retry=dict(ok=True,result=api.call(cur,'WIP_OUTPUT',dict(request))['operation']);conn.commit()
            except psycopg.Error as exc:conn.rollback();retry=dict(ok=False,message=exc.diag.message_primary)
    s=_read(tools,lambda cur:bbp.source_of(cur,fx))
    state=dict(remaining=s['remaining_qty_pcs'],completed=s['completed_qty_pcs'],held=s['bd']['held_qty_pcs'])
    ok_state=state==(dict(remaining=0,completed=7,held=1) if commit else dict(remaining=6,completed=0,held=2))
    retried=(not retry['ok'] and 'STALE_VERSION' in (retry.get('message') or '')) if commit and retry else bool(retry and retry['ok'])
    ok=busy and retried and ok_state
    return dict(status='PASS' if ok else 'FAIL',race='W05_COMPLETE_VS_CLAIM',first_committed=commit,held=str(held)[:300],contention=contention,
                second=outcome,retry=retry,state=state,
                expected=dict(second='REFUSED POCKET_PERIOD_BUSY',retry='REFUSED STALE_VERSION' if commit else 'SUCCEEDS'))


# ---------------------------------------------------------------- PRC: an unknown component price set twice
def prc_two_sets(tools,today,commit):
    with tools.connect() as conn,conn.cursor() as cur:
        fx=bdp.fixture(cur,today-timedelta(days=1),'RACE-PRC')
        g=bdp.component(cur,fx,'GARMENT','5000.00');s=bdp.component(cur,fx,'SPRAY',None,status='UNKNOWN');bdp.terms(cur,fx,'COMPONENTS')
        sent=bdp.post_priced(cur,fx,dict(components=[dict(component_id=g,covered_qty=10),dict(component_id=s,covered_qty=10)]))
        charge=bdp.one(cur,"select c.id::text from erp.bd_laundry_charge_lines_v1 c join erp.laundry_delivery_lines l on l.id=c.delivery_line_id "
                           "where l.delivery_id=%s and c.rate_status='UNKNOWN'",sent['delivery_id']);conn.commit()
    def set_price(rate):
        return lambda cur:bdp.bd(cur,'SET_CHARGE_PRICE',dict(charge_line_id=charge,rate_per_pcs=rate,reason='BD race price'))['status']
    held,contention,outcome=tools.two_sessions(set_price('1000.00'),set_price('1200.00'),commit)
    rate=_read(tools,lambda cur:bdp.q(cur,'select rate_status,unit_rate::numeric(18,2)::text from erp.bd_laundry_charge_lines_v1 where id=%s',charge)[0])
    ok_state=rate==('KNOWN','1000.00') if commit else rate==('KNOWN','1200.00')
    return _verdict('PRC_TWO_SETS',commit,held,contention,outcome,'BD_PRICE_ALREADY_KNOWN',dict(rate=list(rate)),ok_state)


# ---------------------------------------------------------------- POL: two owner changes from one version
def pol_two_owner_sets(tools,today):
    version=_read(tools,lambda cur:str(bdp.one(cur,"select version from erp.bd_policy_settings_v1 where policy_key='LAU_DEC04'")))
    def op(cur):
        return bdp.bd(cur,'SET_POLICY',dict(policy_key='LAU_DEC04',operation='SET',expected_version=version,reason='BD race policy',
                                            value=dict(sale_with_unknown_laundry='REFUSE')))['status']
    held,contention,outcome=tools.two_sessions(op,op,True)
    after=_read(tools,lambda cur:str(bdp.one(cur,"select version from erp.bd_policy_settings_v1 where policy_key='LAU_DEC04'")))
    return _verdict('POL_TWO_OWNER_SETS',True,held,contention,outcome,'STALE_VERSION',dict(before=version,after=after),int(after)==int(version)+1)


# ---------------------------------------------------------------- EST: invoice vs estimate on one opening record
def est_invoice_vs_estimate(tools,today,commit):
    rows=bbp.masters()
    rows['OPENING_LAUNDRY_UNINVOICED']=[dict(document_number='{C}-TRM',vendor_code='{C}',receipt_date=str(today-timedelta(days=12)),
                                             category='FAILED_ATTEMPT',qty='2')]
    with tools.connect() as conn,conn.cursor() as cur:
        batch,code,_=bbp.post_batch(cur,today,rows)
        vendor=bdp.one(cur,'select id::text from erp.laundry_vendors where vendor_code=%s',code)
        source,version=bdp.q(cur,'select id::text,row_version::text from erp.bd_opening_laundry_uninvoiced_v1 where batch_id=%s',batch)[0]
        expense=bdp.one(cur,"select id::text from erp.chart_accounts where account_type='EXPENSE' and is_postable and is_active and account_code='5100'")
        bdp.invoice_policies(cur,mode='VARIANCE_ACCOUNT',account=expense)
        draft=bdp.opening_invoice(cur,vendor,today,[dict(source=source,category='FAILED_ATTEMPT',qty=2,amount='8000.00')],'8000.00',post=False)
        conn.commit()
    def post(cur):return bdp.post_draft(cur,draft)['status']
    def estimate(cur):
        return bdp.bd(cur,'SET_OPENING_ESTIMATE',dict(opening_uninvoiced_id=source,expected_version=version,estimated_amount='8000.00',reason='BD race estimate'))['estimated_amount']
    held,contention,outcome=tools.two_sessions(post,estimate,commit)
    state=_read(tools,lambda cur:dict(estimated=str(bdp.one(cur,'select estimated_amount from erp.bd_opening_laundry_uninvoiced_v1 where id=%s',source)),
                                      invoiced=bdp.one(cur,'select erp.bd_opening_invoiced_v1(%s)',source)))
    ok_state=state==(dict(estimated='None',invoiced=True) if commit else dict(estimated='8000.00',invoiced=False))
    return _verdict('EST_INVOICE_VS_ESTIMATE',commit,held,contention,outcome,'BD_W05_ALREADY_BILLED',state,ok_state)


def races(tools,today):
    return [('BD_RACE:INV_TWO_POSTS_FIRST_COMMITS',lambda:inv_two_posts(tools,today,True)),
            ('BD_RACE:INV_TWO_POSTS_FIRST_ABORTS',lambda:inv_two_posts(tools,today,False)),
            ('BD_RACE:W05_COMPLETE_VS_CLAIM_FIRST_COMMITS',lambda:w05_complete_vs_claim(tools,today,True)),
            ('BD_RACE:W05_COMPLETE_VS_CLAIM_FIRST_ABORTS',lambda:w05_complete_vs_claim(tools,today,False)),
            ('BD_RACE:PRC_TWO_SETS_FIRST_COMMITS',lambda:prc_two_sets(tools,today,True)),
            ('BD_RACE:PRC_TWO_SETS_FIRST_ABORTS',lambda:prc_two_sets(tools,today,False)),
            ('BD_RACE:POL_TWO_OWNER_SETS_SAME_VERSION',lambda:pol_two_owner_sets(tools,today)),
            ('BD_RACE:EST_INVOICE_VS_ESTIMATE_FIRST_COMMITS',lambda:est_invoice_vs_estimate(tools,today,True)),
            ('BD_RACE:EST_INVOICE_VS_ESTIMATE_FIRST_ABORTS',lambda:est_invoice_vs_estimate(tools,today,False))]


# ---------------------------------------------------------------- real HTTP (Auth + PostgREST)
def _save(user,action,payload):
    return user.rpc('erp_save_laundry_bd_action_v1',dict(p_action=action,p_payload=payload,p_client_request_id=str(uuid.uuid4())))


@contextmanager
def _fixture_usage(cur):
    """The HTTP copy gives authenticated no USAGE on schema erp (production-faithful). bdp.fixture builds its purchase through the
    owner's private-schema RPC path (chain.work.draft -> as_owner), so the grant exists only inside the fixture transaction and
    is revoked before that transaction commits: no committed state and no HTTP call ever sees it (checked before and after).
    First run without it: run 36190024230, BD_HTTP:MONEY_HIDDEN_INVOICE_OWNER_ADMIN INCOMPLETE 'permission denied for schema erp'."""
    usage=lambda:cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
    assert usage() is False,'BD_HTTP_COPY_ALREADY_HAS_SCHEMA_GRANT'
    cur.execute('grant usage on schema erp to authenticated')
    try:yield
    except BaseException:
        cur.connection.rollback();raise  # the grant goes with the rolled-back fixture transaction
    api.admin(cur);cur.execute('revoke usage on schema erp from authenticated')
    assert usage() is False,'BD_HTTP_FIXTURE_GRANT_NOT_REVOKED'


def http_cases(http,today):

    def policy_owner_only():
        admin=http.login('ADMIN','bd-admin');owner=http.login('OWNER','bd-owner-policy')
        read=owner.rpc('erp_get_laundry_bd_workspace_v1',dict(p_filters={}))
        version=next(p for p in read['body']['policies'] if p['key']=='LAU-DEC04')['version']
        payload=dict(policy_key='LAU_DEC04',operation='SET',expected_version=version,reason='BD HTTP policy',value=dict(sale_with_unknown_laundry='REFUSE'))
        refused=_save(admin,'SET_POLICY',payload)
        anon=http.anon_rpc('erp_save_laundry_bd_action_v1',dict(p_action='SET_POLICY',p_payload=payload,p_client_request_id=str(uuid.uuid4())))
        done=_save(owner,'SET_POLICY',payload)
        now=next(p for p in owner.rpc('erp_get_laundry_bd_workspace_v1',dict(p_filters={}))['body']['policies'] if p['key']=='LAU-DEC04')
        ok=(refused['status']>=400 and 'BD_OWNER_ONLY' in json.dumps(refused['body']) and anon['status'] in (401,403) and done['status']==200
            and now['status']=='SET' and int(now['version'])==int(version)+1)
        return dict(status='PASS' if ok else 'FAIL',admin=dict(status=refused['status'],body=str(refused['body'])[:300]),anon=dict(status=anon['status']),
                    owner=dict(status=done['status'],body=str(done['body'])[:300]),policy=now)

    def money_hidden_invoice_owner_admin():
        with http.connect() as conn,conn.cursor() as cur:
            with _fixture_usage(cur):
                fx=bdp.fixture(cur,today-timedelta(days=1),'HTTP-MONEY')
                g=bdp.component(cur,fx,'GARMENT','5000.00');s=bdp.component(cur,fx,'SPRAY',None,status='UNKNOWN');bdp.terms(cur,fx,'COMPONENTS')
                bdp.post_priced(cur,fx,dict(components=[dict(component_id=g,covered_qty=10),dict(component_id=s,covered_qty=10)]))
                fx2=bdp.fixture(cur,today-timedelta(days=1),'HTTP-INV');bdp.process_rate(cur,fx2,'7000.00');bdp.invoice_policies(cur)
                line=bdp.receipt_line(cur,bdp.receive(cur,bdp.plain_delivery(cur,fx2,10,11),fx2,10,13)['receipt_id'])
            conn.commit()
            committed_usage=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];conn.rollback()
        qc=http.login('PRODUKSI_QC','bd-qc');owner=http.login('OWNER','bd-owner-invoice')
        read=qc.rpc('erp_get_laundry_bd_workspace_v1',dict(p_filters=dict(vendor_id=fx['vendor'])))
        body=read['body'] if isinstance(read['body'],dict) else {}
        priced=body.get('priced_deliveries') or []
        comps=[c for c in body.get('components') or [] if c.get('vendor_id')==fx['vendor']]
        hidden=(read['status']==200 and body.get('money_visible') is False and body.get('invoices') is None and body.get('billable_receipts') is None
                and body.get('accounts') is None and bool(priced) and all('total_known' not in d and all('amount' not in c and 'unit_rate' not in c for c in d['charges']) for d in priced)
                and bool(comps) and all(c['current']['rate'] is None for c in comps)
                and any(c['rate_status']=='UNKNOWN' for d in priced for c in d['charges']))
        draft=dict(vendor_id=fx2['vendor'],invoice_number='HTTP-'+uuid.uuid4().hex[:8],invoice_date=str(fx2['day']),header_total='70000.00',
                   lines=[dict(line_kind='BILL',receipt_line_id=line,category='GOOD',qty=10,amount='70000.00')])
        denied=_save(qc,'SAVE_INVOICE_DRAFT',draft)
        done=_save(owner,'SAVE_INVOICE_DRAFT',draft)
        ok=(committed_usage is False and hidden and denied['status']>=400 and 'OWNER or ADMIN' in json.dumps(denied['body'])
            and done['status']==200 and (done['body'] or {}).get('status')=='DRAFT')
        return dict(status='PASS' if ok else 'FAIL',fixture_schema_grant='TRANSACTION_ONLY_REVOKED_BEFORE_COMMIT',committed_usage=committed_usage,qc_read=dict(status=read['status'],money_visible=body.get('money_visible'),invoices=body.get('invoices'),
                    priced=str(priced)[:400],components=str(comps)[:300]),qc_draft=dict(status=denied['status'],body=str(denied['body'])[:300]),
                    owner_draft=dict(status=done['status'],body=str(done['body'])[:300]))

    def w05_claim_owner_admin():
        with http.connect() as conn,conn.cursor() as cur:
            fx=bbp.production_post(cur,today,w05_rows(today));s=bbp.source_of(cur,fx);conn.commit()
        payload=dict(batch_id=fx['batch'],opening_item_id=s['opening_item_id'],expected_remaining=str(s['remaining_qty_pcs']),operation='OPEN_CLAIM',
                     claim_number=fx['code']+'-HTTP',claim_type='STUCK',qty_pcs='1',date=str(today),reason='BD HTTP claim')
        qc=http.login('PRODUKSI_QC','bd-qc-claim');owner=http.login('OWNER','bd-owner-claim')
        call=lambda user:user.rpc('erp_save_initial_import_action_v1',dict(p_action='WIP_OUTPUT',p_payload=payload,p_client_request_id=str(uuid.uuid4())))
        denied=call(qc);done=call(owner)
        with http.connect() as conn,conn.cursor() as cur:
            after=bbp.source_of(cur,fx);conn.rollback()
        ok=(denied['status']>=400 and done['status']==200 and after['remaining_qty_pcs']==s['remaining_qty_pcs']-1
            and after['bd']['held_qty_pcs']==s['bd']['held_qty_pcs']+1)
        return dict(status='PASS' if ok else 'FAIL',qc=dict(status=denied['status'],body=str(denied['body'])[:300]),
                    owner=dict(status=done['status'],body=str(done['body'])[:300]),before=s['remaining_qty_pcs'],after=after['remaining_qty_pcs'])

    return [('BD_HTTP:SET_POLICY_OWNER_ONLY',policy_owner_only),
            ('BD_HTTP:MONEY_HIDDEN_INVOICE_OWNER_ADMIN',money_hidden_invoice_owner_admin),
            ('BD_HTTP:W05_CLAIM_OWNER_ADMIN_ONLY',w05_claim_owner_admin)]

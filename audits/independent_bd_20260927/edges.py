"""Independent original-plan edges, not derived from peer/writer test cases.

Locked arithmetic before execution: paid failed attempt 5 * 237.41 = 1187.05;
13 * 237.41 = 3086.33. A retry stays in laundry, so neither Good/BS nor FG
appears. An actual unprocessed return restores 13 sewing PCS exactly once.
Legacy laundry rework of 5 BS recovers 5 PCS, charges no vendor service fee,
and retains its source case. Separate late correction adds 113.57 to AP and
expense, leaves paid original/closed history byte-identical, retains economic
2026-09-22, and books in the current open business day.

Uses our daily controlled prerequisite adapter (cut/pickup seeding transparently
excluded from tested workflows). No guards are disabled. Closed-period fixture
is a private rolled-back transaction: a synthetic cutoff is configuration only,
NOT proof of the period-closing workflow. No external/production writes.
"""
import json, traceback, time, hashlib
from decimal import Decimal as D
from datetime import datetime
from zoneinfo import ZoneInfo
import psycopg
from psycopg.types.json import Jsonb
import suite as s
import daily as d

C=s.CTX; R=s.RESULTS; E=s.EVENTS; X={}
eq=s.eq; admin=s.admin; cmd=s.command; uid=s.uid

class SetupBlocked(Exception): pass

def save():
    (s.OUT/'edges-results.json').write_text(json.dumps({
        'candidate':'e96db5a270da5aa6d0f12c3812ac1c0542df938e',
        'plan_sha256':hashlib.sha256((s.Path(__file__).parent/'PLAN.md').read_bytes()).hexdigest(),
        'scope':'IND-34 closed-period linked correction; IND-41 paid failed attempts and free legacy rewash; IND-08 configured-free contract discovery',
        'results':R,'production_go':False,
        'limits':['Not browser/HTTP','Cut/pickup prerequisites seeded by our daily adapter',
                  'Closed-period configuration seeded inside rollback transaction; closing workflow not tested']
    },indent=2,default=str)+'\n')
    (s.OUT/'edges-events.json').write_text(json.dumps(E,indent=2,default=str)+'\n')
    (s.OUT/'edges-fixture.json').write_text(json.dumps({'identity':C,'edges':X,'sources':d.F},indent=2,default=str)+'\n')
s.save=save

def case(key,title,fn,needs=()):
    if any(k not in X for k in needs):
        R.append({'id':key,'title':title,'status':'BLOCKED','classification':'prior edge prerequisite failed','missing':[k for k in needs if k not in X]});save();return
    started=time.monotonic(); r={'id':key,'title':title}
    try:r.update(status='PASS',observation=s.clean(fn()))
    except SetupBlocked as e:r.update(status='BLOCKED',classification='fixture/API setup',error=str(e),traceback=traceback.format_exc())
    except psycopg.Error as e:r.update(status='BLOCKED' if e.sqlstate in ('42601','42703','42P01','42883') else 'FAIL',classification='schema/adapter' if e.sqlstate in ('42601','42703','42P01','42883') else 'runtime business failure; inspect raw event',error=str(e),sqlstate=e.sqlstate,traceback=traceback.format_exc())
    except Exception as e:r.update(status='FAIL',error=str(e),traceback=traceback.format_exc())
    r['seconds']=round(time.monotonic()-started,4);R.append(r);save();print(json.dumps(r,default=str),flush=True)

def bs_rpc(action,payload,version=None):
    request=uid();event={'api':'public.erp_save_bs_resolution_action_v1','action':action,'payload':payload,'expected_version':version,'request':request}
    try:
        with s.actor_conn() as c:answer=c.execute('select public.erp_save_bs_resolution_action_v1(%s,%s,%s::uuid,%s)',(action,Jsonb(payload),request,version)).fetchone()[0]
        event['response']=answer;return answer['result']
    except psycopg.Error as e:event.update(error=str(e),sqlstate=e.sqlstate);raise
    finally:E.append(event)

def setup():
    fixture=json.loads((s.OUT/'daily-fixture.json').read_text());C.update(fixture['identity'])
    required=['app_owner','model','mandor','pattern','rawloc','material','work_component','daily_vendor','daily_wash','daily_finish','products','fg']
    missing=[k for k in required if k not in C]
    if missing:raise SetupBlocked('Our daily master fixture incomplete: '+str(missing))
    C['edge_failed_process']=uid()
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('app.change_reason','Independent edge process master',true)")
        c.execute("insert into erp.wash_processes(id,process_code,process_name) values(%s,'AUD-EDGE-FAIL','Independent paid failure service')",(C['edge_failed_process'],))
    cmd('SAVE_PROCESS_RATE',{'vendor_id':C['daily_vendor'],'wash_process_id':C['edge_failed_process'],'rate_per_pcs':'237.41','effective_from':'2026-09-01T08:00:00+07:00','reason':'Independent agreed attempted-service rate'})
    return {'rate':'237.41','fixture_boundary':'Master process seeded; rate through public BD command'}

def physical(key):
    f=d.F[key]
    wip=admin('select id::text,stage_from,stage_to,qty_pcs,source_type,source_id::text,physical_at::text from erp.wip_stage_events where po_id=%s order by id',(f['po'],))
    goods=admin('select coalesce(sum(l.qty_good_received),0),coalesce(sum(l.qty_bs_laundry),0) from erp.laundry_receipt_lines l join erp.laundry_receipts h on h.id=l.receipt_id where h.delivery_id=%s and h.status=\'POSTED\'',(f['delivery'],))[0]
    fg=admin('select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id where l.po_id=%s',(f['po'],),one=True)
    return {'wip':wip,'good_bs':goods,'fg':fg}

def laundry_accrual(key):
    return admin("select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.po_id=%s and l.account_id=erp.account_id('ACCRUED_MANUFACTURING') and j.status in('POSTED','REVERSED')",(d.F[key]['po'],),one=True)

def source_setup(key):
    try:d.precursor(key)
    except Exception as e:raise SetupBlocked('Own controlled cutting/pickup/sewing prerequisite failed: '+str(e)) from e
    answer=d.ship(key)
    X[key]=True
    return {'shipment':answer,'prepaid_laundry_accrual':laundry_accrual(key)}

def failed_payload(key,qty=None,outcome='RETRY_AT_VENDOR'):
    f=d.F[key]
    sizes=admin('select id::text,size_id::text,qty_sent_pcs from erp.laundry_delivery_batch_size_lines where delivery_line_id=%s order by size_id',(f['delivery_line'],))
    if qty is None:lines=[{'delivery_batch_size_line_id':i,'qty_attempted_pcs':q} for i,_,q in sizes]
    else:lines=[{'delivery_batch_size_line_id':next(i for i,z,_ in sizes if z==C['s1']),'qty_attempted_pcs':qty}]
    return {'delivery_id':f['delivery'],'wash_process_id':C['edge_failed_process'],'custody_outcome':outcome,'physical_at':'2026-09-16T08:00:00+07:00','reason':'Independent paid attempt, exact custody outcome','lines':lines}

def failed_retry():
    key='EDGE_RETRY';f=d.F[key];before=physical(key);before_accrual=laundry_accrual(key)
    p=failed_payload(key,5);request=uid();version=d.ver('laundry_deliveries',f['delivery'])
    r=d.rpc('POST_FAILED_WASH',p,version,request)
    X['retry_request']={'request':request,'payload':p,'version':version};X['retry']=r
    eq(D(r['actual_cost']),D('1187.05'));eq(r['qty_attempted_pcs'],5);eq(r['stock_effect'],'PHYSICAL_STAYS_AT_LAUNDRY')
    eq(physical(key),before,'Paid service attempt must not invent a physical receipt, WIP movement, or FG')
    eq(laundry_accrual(key)-before_accrual,D('1187.05'),'Only attempted service cost accrues')
    line=admin('select l.qty_good_received,l.qty_bs_laundry,l.actual_cost,l.actual_cost_status,a.qty_attempted_pcs,a.return_wip_event_id from erp.laundry_failed_wash_attempts a join erp.laundry_receipt_lines l on l.id=a.receipt_line_id where a.id=%s',(r['failed_wash_attempt_id'],))[0]
    eq(line,(0,0,D('1187.05'),'ESTIMATED',5,None))
    return {'response':r,'unchanged_physical':before,'attempt_and_receipt':line,'laundry_accrual_delta':'1187.05'}

def retry_replay():
    q=X['retry_request'];before=d.fp();r=d.rpc('POST_FAILED_WASH',q['payload'],q['version'],q['request']);eq(r,X['retry']);eq(d.fp(),before)
    return {'response':r,'unchanged_tables':before}

def retry_receive():
    key='EDGE_RETRY';f=d.F[key]
    before=laundry_accrual(key);r=d.receive(key)
    eq(physical(key)['good_bs'],(13,0));eq(physical(key)['fg'],0)
    eq(laundry_accrual(key),D('60755.77'));eq(laundry_accrual(key),before,'Physical return preserves estimate plus paid failed service')
    eq(admin('select count(*) from erp.laundry_failed_wash_attempts where delivery_id=%s',(f['delivery'],),one=True),1)
    return {'receipt':r,'physical':physical(key),'laundry_accrual':'60755.77'}

def unprocessed_return():
    key='EDGE_RETURN';f=d.F[key];before=physical(key)
    r=d.rpc('POST_FAILED_WASH',failed_payload(key,outcome='RETURN_UNPROCESSED'),d.ver('laundry_deliveries',f['delivery']));X['returned']=r
    eq(D(r['actual_cost']),D('3086.33'));eq(r['qty_attempted_pcs'],13);eq(r['delivery_status'],'REVERSED')
    now=physical(key);eq(now['good_bs'],(0,0));eq(now['fg'],0)
    event=admin("select rv.id::text,rv.stage_from,rv.stage_to,rv.qty_pcs,rv.source_type,rv.source_id::text,src.qty_pcs,src.source_id::text from erp.laundry_failed_wash_attempts a join erp.wip_stage_events rv on rv.id=a.return_wip_event_id join erp.wip_stage_events src on src.id=rv.source_id where a.id=%s",(r['failed_wash_attempt_id'],))
    eq(len(event),1);eq(event[0][1:5],('LAUNDRY','SEWING',13,'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'));eq(event[0][6],13);eq(event[0][7],f['delivery_line'])
    eq(admin('select unsent_ready_qty_pcs from erp.v_wip_control_status_v1 where cutting_group_id=%s',(f['group'],),one=True),13)
    eq(laundry_accrual(key),D('3086.33'),'Reversed first dispatch estimate removed; paid attempted service survives')
    X['returned_delivery']=f['delivery'];X['returned_line']=f['delivery_line']
    return {'response':r,'inverse_wip':event,'before':before,'after':now,'remaining_laundry_accrual':'3086.33'}

def redispatch():
    key='EDGE_RETURN';f=d.F[key];p=d.dp(key,at='2026-09-18T08:00:00+07:00');r=cmd('POST_PRICED_DELIVERY',p)
    f['delivery']=r['delivery_id'];f['delivery_line']=admin('select id::text from erp.laundry_delivery_lines where delivery_id=%s',(f['delivery'],),one=True)
    eq(D(r['pricing']['total_known']),D('59568.72'))
    received=d.receive(key);eq(physical(key)['good_bs'],(13,0));eq(physical(key)['fg'],0)
    eq(laundry_accrual(key),D('62655.05'),'One new successful service plus original paid failed attempt')
    attempts=admin('select a.id::text,a.delivery_id::text,a.qty_attempted_pcs,a.return_wip_event_id::text from erp.laundry_failed_wash_attempts a where a.delivery_id=%s',(X['returned_delivery'],))
    eq(len(attempts),1);eq(attempts[0][2],13)
    return {'redispatch':r,'receipt':received,'original_attempt_retained':attempts,'laundry_accrual':'62655.05'}

def free_bs_setup():
    key='EDGE_FREE';source_setup(key);f=d.F[key]
    product=C['products'][C['s1']+':'+C['brand']]
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('app.change_reason','Independent explicit no-accessory BOM prerequisite',true)")
        exists=c.execute("select id from erp.accessory_bom_versions where product_id=%s and is_active and effective_from<='2026-09-01T08:00:00+07:00' and effective_to is null",(product,)).fetchone()
        if not exists:c.execute("insert into erp.accessory_bom_versions(product_id,version_label,effective_from,notes,created_by) values(%s,'AUD-EDGE-NONE','2026-09-01T08:00:00+07:00','Explicit empty accessory BOM for independent rewash fixture',%s)",(product,C['app_owner']))
    p=d.rp(key,at='2026-09-17T08:00:00+07:00')
    for line in p['lines']:
        size=admin('select size_id::text from erp.laundry_delivery_batch_size_lines where id=%s',(line['delivery_batch_size_line_id'],),one=True)
        if size==C['s1']:line.update(qty_good_received=2,qty_bs_laundry=5,bs_product_id=product)
    r=d.rpc('POST_RECEIPT',p,d.ver('laundry_deliveries',f['delivery']));eq(r['good_qty_pcs'],8);eq(r['bs_qty_pcs'],5)
    rows=admin('select b.id::text,b.qty_pcs,b.product_id::text,b.source_laundry_receipt_line_id::text from erp.bs_cases b where b.po_id=%s',(f['po'],))
    eq(len(rows),1);eq(rows[0][1],5);eq(rows[0][2],product);assert rows[0][3]
    X['free_bs']=rows[0][0];return {'receipt':r,'source_bs':rows[0],'bom_boundary':'Existing explicit BOM reused, or direct empty master BOM prerequisite; not BOM-editor acceptance proof'}

def vendor_finances():
    return admin("select a.account_code,coalesce(sum(l.debit),0),coalesce(sum(l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id join erp.chart_accounts a on a.id=l.account_id where l.vendor_id=%s and j.status in('POSTED','REVERSED') group by a.account_code order by a.account_code",(C['daily_vendor'],))

def free_rewash():
    f=d.F['EDGE_FREE'];before=vendor_finances();before_accrual=laundry_accrual('EDGE_FREE')
    p={'rework_number':'AUD-EDGE-REWASH','bs_case_id':X['free_bs'],'destination_type':'LAUNDRY','contractor_id':None,'vendor_id':C['daily_vendor'],'qty_sent':5,'qty_good_returned':0,'qty_bs_returned':0,'physical_sent_at':'2026-09-18T08:00:00+07:00','status':'IN_PROGRESS','return_fg_location_id':C['fg'],'change_reason':'Independent free rewash of exact 5 Laundry BS','notes':'Legacy vendor rewash without service fee','accessory_bom_version_id':None,'accessory_bom_item_ids':[],'components':[]}
    created=bs_rpc('SAVE_REWORK',p);oid=created['rework_order_id'];X['free_order']=oid
    eq(admin('select count(*) from erp.rework_component_lines where rework_order_id=%s',(oid,),one=True),0)
    eq(physical('EDGE_FREE')['fg'],0,'Sending BS to rewash must not create GOOD FG')
    done=bs_rpc('COMPLETE_REWORK',{'rework_order_id':oid,'qty_good':5,'qty_bs':0,'completed_at':'2026-09-19T08:00:00+07:00','return_fg_location_id':C['fg'],'change_reason':'Independent actual recovery of all five rewashed pieces'},d.ver('rework_orders',oid))
    order=d.row('rework_orders',oid);eq(order['status'],'COMPLETED');eq(order['qty_sent'],5);eq(order['qty_good_returned'],5);eq(order['qty_bs_returned'],0);eq(order['bs_case_id'],X['free_bs']);eq(order['vendor_id'],C['daily_vendor'])
    eq(vendor_finances(),before,'Legacy free rewash creates no vendor fee/payable');eq(laundry_accrual('EDGE_FREE'),before_accrual)
    eq(physical('EDGE_FREE')['fg'],5);eq(physical('EDGE_FREE')['good_bs'],(8,5),'Original Laundry receipt remains unchanged')
    resolution=admin('select resolution_type,qty_pcs,source_rework_order_id::text from erp.bs_resolutions where bs_case_id=%s',(X['free_bs'],));eq(resolution,[('REWORK_LAUNDRY',5,oid)])
    movements=admin('select m.movement_type,m.qty_signed,m.source_type,m.source_id::text,l.id::text,l.po_id::text,l.product_id::text from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id where l.po_id=%s',(f['po'],))
    eq(len(movements),1);eq(movements[0][0:4],('REWORK_IN',5,'REWORK_ORDER',oid));eq(movements[0][5],f['po'])
    return {'created':created,'completed':done,'order':order,'vendor_finances_unchanged':before,'resolution':resolution,'fg_lineage':movements,'laundry_accrual_preserved':before_accrual}

def closed_correction():
    # Isolated whole-transaction rollback, so neither cutoff nor policy changes
    # contaminate other native/HTTP tests. Native authorization is not the claim.
    life=json.loads((s.OUT/'lifecycle-fixture.json').read_text());opening=life['sources']['A']
    original=admin("select to_jsonb(t) from erp.bd_laundry_invoices_v1 t where invoice_number='AUD-PART-7' and status='POSTED'",one=True)
    if not original:raise SetupBlocked('Our paid opening-invoice lifecycle prerequisite missing')
    expense=life['expense'];today=datetime.now(ZoneInfo('Asia/Jakarta')).date().isoformat()
    requests=[]
    with psycopg.connect(s.DSN) as c:
        try:
            c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],))
            c.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps({'sub':C['owner'],'role':'authenticated'}),))
            c.execute("select set_config('app.change_reason','Independent rolled-back closed-period configuration',true)")
            def fetch(sql,args=()):return c.execute(sql,args).fetchall()
            def crpc(action,payload):
                request=uid();event={'api':'public.erp_save_laundry_bd_action_v1','action':action,'payload':payload,'request':request,'boundary':'privileged native session, entire transaction rolled back'};requests.append(event)
                try:r=c.execute('select public.erp_save_laundry_bd_action_v1(%s,%s,%s::uuid)',(action,Jsonb(payload),request)).fetchone()[0];event['response']=r;return r
                except psycopg.Error as e:event.update(error=str(e),sqlstate=e.sqlstate);raise
            cutoff_before=fetch('select to_jsonb(t) from erp.accounting_period_control t')
            original_before=fetch('select to_jsonb(t) from erp.bd_laundry_invoices_v1 t where id=%s',(original['id'],))
            original_lines=fetch('select to_jsonb(t) from erp.bd_laundry_invoice_lines_v1 t where invoice_id=%s order by id',(original['id'],))
            payments_before=fetch('select to_jsonb(t) from erp.vendor_payments t where vendor_invoice_id=%s order by id',(original['id'],))
            if not payments_before:raise SetupBlocked('Expected original invoice payments absent')
            closed_journals=fetch("select to_jsonb(j),coalesce((select jsonb_agg(to_jsonb(l) order by l.id) from erp.journal_lines l where l.journal_entry_id=j.id),'[]') from erp.journal_entries j where j.transaction_date<='2026-09-23' and j.status in('POSTED','REVERSED') order by j.id")
            closed_balances=fetch("select to_jsonb(t) from erp.account_daily_balances t where balance_date<='2026-09-23' order by balance_date,account_id")
            c.execute("update erp.accounting_period_control set closed_through='2026-09-23',change_reason='Independent configuration only; transaction rolled back' where singleton_id=1")
            version=c.execute("select version from erp.bd_policy_settings_v1 where policy_key='LAU_DEC06'").fetchone()[0]
            crpc('SET_POLICY',{'policy_key':'LAU_DEC06','operation':'SET','expected_version':str(version),'reason':'Independent isolated correction accounting configuration','value':{'variance_mode':'VARIANCE_ACCOUNT','after_payment':'CORRECTION_DOCUMENT','variance_account_id':expense}})
            draft=crpc('SAVE_INVOICE_DRAFT',{'vendor_id':original['vendor_id'],'invoice_number':'AUD-EDGE-CLOSED-CORRECTION','invoice_date':'2026-09-22','header_total':'113.57','corrects_invoice_id':original['id'],'lines':[{'line_kind':'CORRECTION','opening_uninvoiced_id':opening,'category':'GOOD','qty':0,'amount':'113.57','note':'Independent late closed-period adjustment'}]})
            result=crpc('POST_INVOICE',{'invoice_id':draft['invoice_id'],'expected_version':str(draft['row_version'])})
            eq(result['corrects_invoice_id'],original['id']);eq(result['status'],'POSTED')
            j=c.execute('select transaction_date::text,economic_date::text,status from erp.journal_entries where id=%s',(result['journal_id'],)).fetchone();eq(j,(today,'2026-09-22','POSTED'),'Current open posting day; original economic date remains explicit')
            lines=fetch('select account_id::text,sum(debit),sum(credit) from erp.journal_lines where journal_entry_id=%s group by account_id order by account_id',(result['journal_id'],))
            ap=str(c.execute("select erp.account_id('AP_VENDOR')").fetchone()[0]);eq({a:(x,y) for a,x,y in lines},{ap:(D(0),D('113.57')),expense:(D('113.57'),D(0))})
            eq(fetch('select to_jsonb(t) from erp.bd_laundry_invoices_v1 t where id=%s',(original['id'],)),original_before)
            eq(fetch('select to_jsonb(t) from erp.bd_laundry_invoice_lines_v1 t where invoice_id=%s order by id',(original['id'],)),original_lines)
            eq(fetch('select to_jsonb(t) from erp.vendor_payments t where vendor_invoice_id=%s order by id',(original['id'],)),payments_before)
            eq(fetch("select to_jsonb(j),coalesce((select jsonb_agg(to_jsonb(l) order by l.id) from erp.journal_lines l where l.journal_entry_id=j.id),'[]') from erp.journal_entries j where j.transaction_date<='2026-09-23' and j.status in('POSTED','REVERSED') order by j.id"),closed_journals,'All closed posted journals remain identical')
            eq(fetch("select to_jsonb(t) from erp.account_daily_balances t where balance_date<='2026-09-23' order by balance_date,account_id"),closed_balances,'Closed daily account balances remain identical')
            observation={'correction':result,'journal_dates':j,'journal_lines':lines,'original_and_payments_preserved':True,'closed_journal_count_preserved':len(closed_journals),'closed_balances_preserved':True,'cutoff_before':cutoff_before,'boundary':'Synthetic cutoff prerequisite; closing workflow not tested; all changes rolled back'}
        finally:c.rollback();E.extend(requests)
    eq(admin('select to_jsonb(t) from erp.accounting_period_control t'),cutoff_before,'Rollback restored prior cutoff')
    eq(admin("select count(*) from erp.bd_laundry_invoices_v1 where invoice_number='AUD-EDGE-CLOSED-CORRECTION'",one=True),0,'Private test transaction left no correction')
    return observation

def free_contract():
    comp=s.component(C['daily_vendor'],'AUD-EDGE-FREE-CONTRACT');controls=[]
    for day,status,price in [(25,'FREE','0.00'),(26,'WAIVED','0.00'),(27,'UNKNOWN',None),(28,'KNOWN','123.45')]:
        controls.append(s.rate(comp,price,'2026-09-'+str(day)+'T08:00:00+07:00',status))
    versions=admin('select rate_status,rate_per_pcs from erp.bd_laundry_component_rates_v1 where component_id=%s order by effective_from',(comp,))
    eq(versions,[('FREE',D(0)),('WAIVED',D(0)),('UNKNOWN',None),('KNOWN',D('123.45'))])
    R.append({'id':'IND-08.CONFIGURED-FREE','title':'Explicit FREE/WAIVED zero is distinct from UNKNOWN null','status':'PASS','classification':'Revised public master contract; full physical lifecycle in free-contract-results.json','observation':{'responses':controls,'native_versions':versions}});save()

def main():
    try:setup();save()
    except Exception as e:R.append({'id':'SETUP.EDGES','status':'BLOCKED','error':str(e),'traceback':traceback.format_exc()});save();return 1
    case('IND-41.RETRY-SOURCE','Independent 13-PCS source for paid failure',lambda:source_setup('EDGE_RETRY'))
    case('IND-41.PAID-RETRY','Paid 5-PCS failed attempt accrues 1187.05 without fake return',failed_retry,['EDGE_RETRY'])
    case('IND-41.PAID-REPLAY','Paid attempt request replay has one cost and no physical duplication',retry_replay,['retry_request','retry'])
    case('IND-41.PAID-RECEIVE','Actual 13-PCS receipt retains prior failed service cost',retry_receive,['retry'])
    case('IND-41.RETURN-SOURCE','Independent 13-PCS source for unprocessed return',lambda:source_setup('EDGE_RETURN'))
    case('IND-41.PAID-RETURN','Actual unprocessed return restores exact WIP and retains 3086.33 failed cost',unprocessed_return,['EDGE_RETURN'])
    case('IND-41.REDISPATCH','New shipment after actual return preserves failed-attempt lineage and cost',redispatch,['returned_delivery'])
    case('IND-41.FREE-SOURCE','Five exact laundry BS pieces become authoritative free-rewash source',free_bs_setup)
    case('IND-41.FREE-REWASH','Legacy free rewash recovers five pieces with source lineage and no new vendor fee',free_rewash,['free_bs'])
    case('IND-34.CLOSED','Late separate correction preserves paid original and closed ledger',closed_correction)
    try:free_contract()
    except Exception as e:R.append({'id':'IND-08.CONFIGURED-FREE','status':'BLOCKED','classification':'Contract discovery fixture failed','error':str(e),'traceback':traceback.format_exc()});save()
    save();return int(any(r['status']!='PASS' for r in R))

if __name__=='__main__':raise SystemExit(main())

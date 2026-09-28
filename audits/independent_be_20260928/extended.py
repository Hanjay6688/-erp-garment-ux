"""Own extended BE oracle: sales, late costs, invoices, non-PO wages and conflicts."""
import native as n, flows as f, pocket as p, suite as s, daily as d
from decimal import Decimal as D
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo
from psycopg.types.json import Jsonb
import psycopg,json,threading,time,copy
C=n.C;F=n.F;X=f.X;A=n.A;eq=n.eq;uid=n.uid

def report(day,c=None):
    sql='select erp.get_owner_financial_snapshot_v2(%s::date,%s::date,%s::date)';args=('2026-09-01',day,day)
    if c:r=c.execute(sql,args).fetchone()[0]
    else:
        with s.actor_conn() as conn:r=conn.execute(sql,args).fetchone()[0]
    n.E.append({'actual_report':day,'response':r});return r

def gl(c=None):
    q="select k,coalesce(sum(l.debit-l.credit) filter(where j.status in('POSTED','REVERSED')),0) from unnest(array['FG_INVENTORY','WIP','COGS','OTHER_INCOME','OTHER_EXPENSE','CONTRACTOR_PAYABLE']) k left join erp.journal_lines l on l.account_id=erp.account_id(k) left join erp.journal_entries j on j.id=l.journal_entry_id group by k"
    return dict(c.execute(q).fetchall() if c else A(q))
def location(code):
    ident=uid()
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('app.change_reason','Independent source isolation',true)")
        c.execute("insert into erp.locations(id,location_code,location_name,location_type) values(%s,%s,%s,'FG_WAREHOUSE')",(ident,code,code))
    return ident

def sale(product,loc,lot,code,qty=3,at='2026-09-17T08:00:00+07:00'):
    payload={'sale_number':'BE-AUD-SALE-'+code,'customer_id':C['customer'],'source_location_id':loc,'sale_date':at,'reason':'Independent downstream sale','items':[{'product_id':product,'qty_pcs':qty,'unit_price_snapshot':'20000.00','discount_amount':'0.00'}]}
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],))
        r=c.execute('select erp.save_sale_draft_v2(%s,%s::uuid,null)',(Jsonb(payload),uid())).fetchone()[0];c.execute('select erp.post_sale(%s)',(r['sale_id'],))
    alloc=A('select a.id::text,a.lot_id::text,a.qty_pcs,a.unit_hpp_snapshot from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s',(r['sale_id'],));eq(sum(x[2] for x in alloc),qty);eq({x[1] for x in alloc},{lot})
    n.E.append({'native_sales_layer':'Native ERP posting with owner identity, not HTTP authorization proof','payload':payload,'response':r,'allocation':alloc})
    return {'sale_id':r['sale_id'],'allocations':alloc}
def returned(sale,code,at='2026-09-18T08:00:00+07:00'):
    ret=uid()
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],));c.execute("select set_config('app.change_reason','Independent linked one-piece return',true)")
        c.execute('insert into erp.sales_returns(id,return_number,sale_id,customer_id,physical_at,created_by) values(%s,%s,%s,%s,%s,%s)',(ret,'BE-AUD-RETURN-'+code,sale['sale_id'],C['customer'],at,C['app_owner']))
        c.execute('insert into erp.sales_return_items(return_id,sale_stock_allocation_id,product_id,lot_id,location_id,qty_pcs,refund_amount) select %s,a.id,l.product_id,l.id,a.location_id,1,20000 from erp.sale_stock_allocations a join erp.fg_lots l on l.id=a.lot_id where a.id=%s',(ret,sale['allocations'][0][0]));c.execute('select erp.post_sales_return(%s)',(ret,))
    n.E.append({'native_return_layer':'Header/item prerequisites plus actual native return posting; not browser proof','return_id':ret,'original_allocation':sale['allocations'][0][0]});return ret

def conversion_sale():
    before=gl();loc=location('BE-AUD-SALE-ISOLATION');source=uid();target=uid()
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('app.change_reason','Independent conversion cost isolation',true)")
        c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],))
        for ident,sku,color in [(source,'BE-AUD-CONV-ISOLATED-SOURCE','BE-CONV-SOURCE'),(target,'BE-AUD-CONV-ISOLATED-TARGET','BE-CONV-TARGET')]:
            c.execute("insert into erp.products(id,identity_root_id,sku,model_id,brand_id,color_name,size_id,product_name,effective_from) values(%s,%s,%s,%s,%s,%s,%s,%s,'2026-09-01T08:00:00+07:00')",(ident,ident,sku,C['model'],C['brand'],color,C['s1'],sku))
            c.execute("insert into erp.accessory_bom_versions(product_id,version_label,effective_from,notes,created_by) values(%s,'AUD-CONVERSION-NONE','2026-09-01T08:00:00+07:00','Explicit empty conversion BOM',%s)",(ident,C['app_owner']))
    imported=f.imported('CONVERSION-SALE-ISOLATION',[('OPENING_BALANCE_ITEM',[{'balance_type':'FINISHED_GOODS','product_sku':'BE-AUD-CONV-ISOLATED-SOURCE','brand_code':'AUD-brand','model_code':'AUD-DAY','color_name':'BE-CONV-SOURCE','size_code':'AUD-1','location_code':'BE-AUD-SALE-ISOLATION','qty':'13','unit_cost':'1234.57','hpp_input_method':'MANUAL','quality_grade':'GRADE_A','opening_source_key':'BE-AUD-CONV-SOURCE','control_key':'FG'}]),('OPENING_CONTROL',[{'control_key':'FG','balance_type':'FINISHED_GOODS','qty':'13','amount':'16049.41'}])])
    src=A("select m.lot_id::text from erp.fg_stock_movements m join erp.initial_import_opening_stock_sources k on k.opening_item_id=m.source_id where k.batch_id=%s and k.source_key='BE-AUD-CONV-SOURCE'",(imported['batch_id'],),one=True)
    eq(n.value(src),D('16049.41'));row=n.ws({'source_lot_id':src})['lots'][0]
    f.imported('CONVERSION-SALE-TAGS',[('MATERIAL',[{'material_sku':'BE-AUD-CONV-TAG','material_name':'Independent isolated downstream tag','material_type':'ACCESSORY','unit_code':'PCS','accessory_category_code':'BE-AUD-TAG'}]),('OPENING_BALANCE_ITEM',[{'balance_type':'MATERIAL','material_sku':'BE-AUD-CONV-TAG','location_code':'AUD-rawloc','qty':'30','unit_cost':'23.17','control_key':'TAG','opening_source_key':'BE-AUD-CONV-TAG'}]),('OPENING_CONTROL',[{'control_key':'TAG','balance_type':'MATERIAL','qty':'30','amount':'695.10'}])])
    tag=A("select id::text from erp.materials where material_sku='BE-AUD-CONV-TAG'",one=True);eq(A('select moving_average_cost from erp.materials where id=%s',(tag,),one=True),D('23.17'))
    cp={'source_lot_id':src,'target_product_id':target,'location_id':loc,'qty_pcs':5,'physical_at':'2026-09-15T08:00:00+07:00','reason':'Independent downstream five-piece conversion','expected_version':row['source_revision']}
    cv=n.cmd('POST',cp);lot=cv['destination_lot_id'];sl=sale(target,loc,lot,'CONVERT');ret=returned(sl,'CONVERT');eq(n.lotqty(lot),3)
    dates=['2026-09-19','2026-09-20'];old={day:report(day) for day in dates}
    doc=f.conversion_doc(cv['conversion_id']);usage=n.cmd('POST_USAGE',{'conversion_id':cv['conversion_id'],'expected_version':doc['revision'],'location_id':C['rawloc'],'physical_at':'2026-09-20T08:00:00+07:00','items':[{'material_id':tag,'qty':'5'}],'reason':'Five actual tags after sale and one return'})
    eq(D(usage['source']['cost']),D('115.85'))
    eq(n.lotqty(src),8);eq(n.lotqty(lot),3);eq(n.lotcost(lot)[0],D('1257.740000'));eq(n.value(lot),D('3773.22'));now=gl();delta={k:now[k]-before[k] for k in now};eq(delta['FG_INVENTORY'],D('13649.78'));eq(delta['COGS'],D('2515.48'));eq(delta['FG_INVENTORY']+delta['COGS'],D('16165.26'))
    reports={day:report(day) for day in dates};rd={day:{k:D(reports[day]['financial_position'][k])-D(old[day]['financial_position'][k]) for k in ['fg_inventory','wip_inventory']} for day in dates}
    eq(rd['2026-09-19'],{'fg_inventory':D(0),'wip_inventory':D(0)});eq(rd['2026-09-20']['fg_inventory'],D('69.51'))
    X['converted_sale']={'source':src,'lot':lot,'conversion':cv,'sale':sl,'return':ret,'location':loc}
    refuse=n.reject(lambda:n.cmd('REVERSE',{'conversion_id':cv['conversion_id'],'reason':'Independent inverse with sale and source cost dependencies'}))
    return {'conversion':cv,'sale':sl,'return':ret,'late_usage':usage,'gl_delta':delta,'report_delta':rd,'source_qty':8,'target_qty':3,'net_sold':2,'target_hpp':'1257.74','reverse_dependency':refuse}

def redye_race():
    payload=f.rpayload('RACE');payload2=copy.deepcopy(payload);payload2['order']['rework_number']+='-SECOND';bar=threading.Barrier(2)
    controls=[]
    for who in ['owner','admin']:
        with s.actor_conn(who) as c:
            control=c.execute('select public.erp_save_product_conversion_action_v1(%s,%s,%s::uuid)',('SAVE_REDYE',Jsonb(payload),uid())).fetchone()[0];controls.append({'actor':who,'response':control,'rolled_back':True});c.rollback()
    n.E.append({'redye_race_positive_controls':controls})
    def go(i):
        bar.wait()
        try:return {'actor':['owner','admin'][i],'accepted':True,'response':n.cmd('SAVE_REDYE',[payload,payload2][i],who=['owner','admin'][i])}
        except psycopg.Error as e:return {'actor':['owner','admin'][i],'accepted':False,'error':str(e),'sqlstate':e.sqlstate}
    with ThreadPoolExecutor(2) as pool:rs=list(pool.map(go,[0,1]))
    eq(sum(x['accepted'] for x in rs),1);assert all('PERMISSION' not in x.get('error','') for x in rs),rs
    q=A("select sum(qty_sent) from erp.rework_orders where bs_case_id=%s and status in('OPEN','IN_PROGRESS','PARTIAL')",(f.rsource('RACE')['bs'],),one=True);eq(q,7)
    return {'two_authorized_actors':rs,'dispatched':7,'source_bs':9}
def redye_partial_invoice():
    start=f.start_redye('BAD');done=f.complete('BAD');r=f.rsource('BAD');before=f.physical_fingerprint();reports_before={z:report(z) for z in ['2026-09-19','2026-09-20','2026-09-21']}
    posts=[]
    for code,day,lines,total in [('ONE','2026-09-20',[('GOOD',3,'605.43')],'605.43'),('TWO','2026-09-21',[('GOOD',2,'407.09'),('BS',2,'405.01')],'812.10')]:
        draft=s.command('SAVE_INVOICE_DRAFT',{'vendor_id':C['daily_vendor'],'invoice_number':'BE-AUD-PART-'+code,'invoice_date':day,'header_total':total,'lines':[{'line_kind':'BILL','rework_service_id':r['service'],'category':cat,'qty':q,'amount':a,'note':'Independent partial redye invoice'} for cat,q,a in lines]})
        post=s.command('POST_INVOICE',{'invoice_id':draft['invoice_id'],'expected_version':str(draft['row_version'])});posts.append(post)
    vals=A("select sum(l.qty),sum(l.net_amount),sum(l.released_estimate),sum(l.product_variance) from erp.bd_laundry_invoice_lines_v1 l join erp.bd_laundry_invoices_v1 h on h.id=l.invoice_id where l.rework_service_id=%s and h.status='POSTED'",(r['service'],))[0];eq(vals,(7,D('1417.53'),D('1381.17'),D('36.36')));eq(f.pogl(r['po']),D('14307.24'));eq(f.physical_fingerprint(),before)
    r['partial_invoices']=posts;X['partial_reports']=reports_before
    return {'start':start,'completion':done,'invoices':posts,'source_totals':vals,'physical_unchanged':True,'total_cost':'14307.24'}
def redye_paid_correction():
    r=f.rsource('BAD');origin=r['partial_invoices'][0];cash=A('select id::text from erp.cash_accounts where is_active order by cash_account_code limit 1',one=True)
    paid=[]
    for amount in ['200.00','405.43']:paid.append(s.command('PAY_VENDOR_DOCUMENT',{'target_kind':'VENDOR_INVOICE','target_id':origin['invoice_id'],'amount':amount,'date':'2026-09-22','cash_account_id':cash,'reason':'Independent staged payment for actual redye invoice'}))
    eq(D(paid[0]['remaining']),D('405.43'));eq(D(paid[1]['remaining']),D(0));old=d.row('bd_laundry_invoices_v1',origin['invoice_id']);pay=A('select to_jsonb(t) from erp.vendor_payments t where vendor_invoice_id=%s order by id',(origin['invoice_id'],));physical=f.physical_fingerprint()
    denied=n.reject(lambda:s.command('REVERSE_INVOICE',{'invoice_id':old['id'],'expected_version':str(old['row_version']),'reason':'Independent paid original reversal'}),'PAID')
    draft=s.command('SAVE_INVOICE_DRAFT',{'vendor_id':C['daily_vendor'],'invoice_number':'BE-AUD-REDYE-CORR','invoice_date':'2026-09-23','header_total':'-17.63','corrects_invoice_id':origin['invoice_id'],'lines':[{'line_kind':'CORRECTION','rework_service_id':r['service'],'category':'GOOD','qty':0,'amount':'-17.63','note':'Documented lower final charge'}]})
    correction=s.command('POST_INVOICE',{'invoice_id':draft['invoice_id'],'expected_version':str(draft['row_version'])});eq(f.pogl(r['po']),D('14289.61'));eq(d.row('bd_laundry_invoices_v1',origin['invoice_id']),old);eq(A('select to_jsonb(t) from erp.vendor_payments t where vendor_invoice_id=%s order by id',(origin['invoice_id'],)),pay);eq(f.physical_fingerprint(),physical)
    return {'payments':paid,'paid_reversal_denied':denied,'correction':correction,'original_and_payment_unchanged':True,'total_cost':'14289.61'}

def redye_sale():
    # Already completed exact KNOWN target is isolated for FIFO by native sale draft lot selection not assumed.
    r=f.rsource('UNKNOWN');loc=location('BE-AUD-REDYE-SALES');oldfg=C['fg'];C['fg']=loc
    try:done=f.complete('UNKNOWN')
    finally:C['fg']=oldfg
    lot=r['targetlot'];sl=sale(C['redye_target'],loc,lot,'REDYE',at='2026-09-19T08:00:00+07:00');ret=returned(sl,'REDYE',at='2026-09-20T08:00:00+07:00');eq(n.lotqty(lot),3)
    before=f.physical_fingerprint();draft=s.command('SAVE_INVOICE_DRAFT',{'vendor_id':C['daily_vendor'],'invoice_number':'BE-AUD-SOLD-REDYE','invoice_date':'2026-09-21','header_total':'1417.53','lines':[{'line_kind':'BILL','rework_service_id':r['service'],'category':'GOOD','qty':5,'amount':'1012.52','note':'Independent sold redye source'},{'line_kind':'BILL','rework_service_id':r['service'],'category':'BS','qty':2,'amount':'405.01','note':'Actual BS attempted'}]});post=s.command('POST_INVOICE',{'invoice_id':draft['invoice_id'],'expected_version':str(draft['row_version'])});eq(f.pogl(r['po']),D('14307.24'));eq(n.lotqty(lot),3);eq(f.physical_fingerprint(),before)
    ledger=A("select case when l.account_id=erp.account_id('WIP') then 'WIP' when l.account_id=erp.account_id('FG_INVENTORY') then 'FG' when l.account_id=erp.account_id('COGS') then 'COGS' else 'OTHER' end,sum(l.debit-l.credit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.po_id=%s and l.account_id in(erp.account_id('WIP'),erp.account_id('FG_INVENTORY'),erp.account_id('COGS')) and j.status in('POSTED','REVERSED') group by 1",(r['po'],));assert dict(ledger).get('COGS',0)>0,ledger
    denied=n.reject(lambda:n.bs('SAVE_REWORK',{'id':r['order'],'action':'CANCEL','change_reason':'Independent cancel after actual sale'},d.ver('rework_orders',r['order'])))
    return {'completion':done,'sale':sl,'return':ret,'invoice':post,'ledger':ledger,'qty':3,'total_value':'14307.24','downstream_cancel_refused':denied}

def closed_redye():
    r=f.rsource('BAD');origin=r['partial_invoices'][0];today=datetime.now(ZoneInfo('Asia/Jakarta')).date().isoformat();cutoff=A('select to_jsonb(t) from erp.accounting_period_control t')
    with psycopg.connect(s.DSN) as c:
        try:
            c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],));c.execute("select set_config('app.change_reason','Independent rolled-back closed-date fixture',true)")
            journal_sql="select to_jsonb(j),coalesce((select jsonb_agg(to_jsonb(l) order by l.id) from erp.journal_lines l where l.journal_entry_id=j.id),'[]') from erp.journal_entries j where j.transaction_date<='2026-09-25' and j.status in('POSTED','REVERSED') order by j.id"
            balance_sql="select to_jsonb(t) from erp.account_daily_balances t where balance_date<='2026-09-25' order by balance_date,account_id";old=c.execute(journal_sql).fetchall();bal=c.execute(balance_sql).fetchall();before=report('2026-09-25',c)
            c.execute("update erp.accounting_period_control set closed_through='2026-09-25',change_reason='Independent private test; transaction rolled back' where singleton_id=1")
            def cmd(action,payload):
                req=uid();out=c.execute('select public.erp_save_laundry_bd_action_v1(%s,%s,%s::uuid)',(action,Jsonb(payload),req)).fetchone()[0];n.E.append({'closed_redye_rpc':action,'payload':payload,'response':out,'layer':'Native owner session, complete rollback'});return out
            dr=cmd('SAVE_INVOICE_DRAFT',{'vendor_id':C['daily_vendor'],'invoice_number':'BE-AUD-CLOSED','invoice_date':'2026-09-24','header_total':'31.47','corrects_invoice_id':origin['invoice_id'],'lines':[{'line_kind':'CORRECTION','rework_service_id':r['service'],'category':'GOOD','qty':0,'amount':'31.47','note':'Independent late economic correction'}]});post=cmd('POST_INVOICE',{'invoice_id':dr['invoice_id'],'expected_version':str(dr['row_version'])})
            dates=c.execute('select transaction_date::text,economic_date::text from erp.journal_entries where id=%s',(post['journal_id'],)).fetchone();eq(dates,(today,'2026-09-24'));eq(c.execute(journal_sql).fetchall(),old);eq(c.execute(balance_sql).fetchall(),bal);eq(report('2026-09-25',c)['financial_position'],before['financial_position'])
            out={'correction':post,'dates':dates,'old_journals':len(old),'old_asof_report_unchanged':True,'boundary':'Seeded cutoff, not the close workflow; entire transaction rolled back'}
        finally:c.rollback()
    eq(A('select to_jsonb(t) from erp.accounting_period_control t'),cutoff);return out

def nonpo_wage():
    before=n.fp(['production_orders','work_completion_events','work_completion_lines','sewing_terminal_events']);base=gl();created=n.bs('CREATE_MANUAL_BS',{'untracked_type':'OUT_OF_NOWHERE','legacy_reference':'Independent physical count, nine found damaged garments','change_reason':'Independent found BS source','physical_at':'2026-09-13T08:00:00+07:00','qty_pcs':9,'product_id':C['product'],'bs_number':'BE-AUD-FOUND-BS','components':[]});bs=created.get('bs_case_id') or created.get('id');assert bs,created
    payload={'source_kind':'GOOD_FROM_UNSOURCED_BS','bs_case_id':bs,'product_id':C['product'],'location_id':C['fg'],'qty_pcs':5,'physical_at':'2026-09-14T08:00:00+07:00','reason':'Five actual repaired found BS','repair':{'contractor_id':C['mandor'],'work_component_id':C['work_component'],'rate_per_pcs':'31.47','rate_reason':'Explicit repair wage only for five recovered pieces'}}
    req=uid();r=n.rpc('erp_post_fg_unsourced_receipt_v1',[payload,req]);eq(D(r['unit_value']),D('1266.04'));eq(D(r['total_value']),D('6330.20'));eq(n.fp(['production_orders','work_completion_events','work_completion_lines','sewing_terminal_events']),before);delta={k:v-base[k] for k,v in gl().items()};eq(delta['FG_INVENTORY'],D('6330.20'));eq(delta['CONTRACTOR_PAYABLE'],-D('157.35'));eq(delta['OTHER_INCOME'],-D('6172.85'))
    snap=n.fp();eq(n.rpc('erp_post_fg_unsourced_receipt_v1',[payload,req]),r);eq(n.fp(),snap);refuse=n.reject(lambda:n.rpc('erp_post_fg_unsourced_receipt_v1',[payload,uid()]),'EXCEEDS_OPEN')
    row=n.ws({'source_lot_id':r['lot_id']})['lots'][0];converted=n.cmd('POST',{'source_lot_id':r['lot_id'],'target_product_id':C['target'],'location_id':C['fg'],'qty_pcs':3,'physical_at':'2026-09-15T08:00:00+07:00','reason':'Three repaired found pieces relabelled','expected_version':row['source_revision']});eq(n.value(r['lot_id']),D('2532.08'));eq(n.value(converted['destination_lot_id']),D('3798.12'));eq(n.fp(['production_orders','work_completion_events','work_completion_lines','sewing_terminal_events']),before)
    X['nonpo_bs']={'case':bs,'receipt':r,'converted':converted};return {'manual_bs':created,'good_receipt':r,'remaining_bs':4,'only_actual_repair_liability':'157.35','gl_delta':delta,'conversion':converted,'excess_refused':refuse,'no_fake_po_or_normal_sewing':True}

def access_more():
    # Each successful positive request supplies a real cached mutation for revocation.
    results=[];own=A('select role,role_id from erp.app_users where auth_user_id=%s',(C['admin'],))[0];viewer=A('select role_id from erp.app_users where auth_user_id=%s',(C['staff'],),one=True)
    q=uid();payload=p.live_payload(quantity='0.10',date='2026-09-24');positive=n.pocket('POST',payload,q,'admin')
    try:
        with psycopg.connect(s.DSN) as c:
            c.execute("select set_config('app.change_reason','Independent revocation of second authorized actor',true)");c.execute("update erp.app_users set role='STAFF',role_id=%s where auth_user_id=%s",(viewer,C['admin']))
        results.append(n.reject(lambda:n.pocket('POST',payload,q,'admin')));results.append(n.reject(lambda:n.pocket('POST',payload,who='admin')))
    finally:
        with psycopg.connect(s.DSN) as c:
            c.execute("select set_config('app.change_reason','Restore disposable admin',true)");c.execute('update erp.app_users set role=%s,role_id=%s where auth_user_id=%s',(*own,C['admin']))
    history=next(x for x in p.ws()['history'] if x['id']==positive['id']);n.pocket('REVERSE',{'id':positive['id'],'expected_version':history['row_version'],'reason':'Cleanup isolated permission-control issue'})
    for fn in [lambda:n.cmd('SAVE_REDYE',f.rpayload('BAD'),who='staff'),lambda:n.cmd('SET_REDYE_PRICE',{'service_id':f.rsource('UNKNOWN')['service'],'rate':'9.00','reason':'Unauthorized price write'},who='staff')]:results.append(n.reject(fn))
    return {'positive_pocket':positive,'revoked_fresh_and_replay':results,'returned_stock':True}

def selectors():
    # Public AX sources, not fabricated BE records. No financial invariants derived from search implementation.
    keys=[]
    for i in range(57):
        r=n.rpc('erp_post_fg_unsourced_receipt_v1',[{'source_kind':'FOUND_AT_OPNAME','product_id':C['wrongsize'],'location_id':C['fg'],'qty_pcs':1,'physical_at':'2026-09-13T08:00:00+07:00','reason':'Independent selector capacity source '+str(i)},uid()]);keys.append(r['lot_id'])
    pages=[n.ws({'query':'AUD-DAY-1','page':z}) for z in [1,2,3]];ids=[x['id'] for page in pages for x in page['lots']];eq(len(set(ids)),57);eq(set(ids),set(keys))
    oldest=A('select id::text,lot_number from erp.fg_lots where id=any(%s::uuid[]) order by created_at,id limit 1',(keys,))[0];search=n.ws({'query':oldest[1]});eq([x['id'] for x in search['lots']],[oldest[0]]);X['selector']={'lots':keys,'oldest':oldest};return {'sources':57,'page_lengths':[len(x['lots']) for x in pages],'searched_oldest':oldest,'no_loss_or_duplicates':True}

def run():
    f.load()
    f.case('CONV-15.NONPO-SALE','Convert, sell 3, return 1 and add real accessory cost; direct GL and as-of',conversion_sale,'Public conversion and usage; native sales/return integration with direct GL/report')
    f.case('REDYE-08.RACE','Two authorized actors cannot send 7 of same 9 BS twice',redye_race)
    f.case('REDYE-12.PARTIAL','Two actual invoices total 7 serviced PCS and release estimate once',redye_partial_invoice)
    f.case('REDYE-12.PAID','Partial and final payments, paid inverse guard and downward correction',redye_paid_correction)
    f.case('REDYE-13','Actual sold and returned redye goods receive late invoice variance',redye_sale,'Public rework/invoice; native sales/return integration')
    f.case('REDYE-15','Closed-date correction preserves old journal, balances and as-of report',closed_redye,'Public RPC in native owner transaction; configured cutoff, full rollback')
    f.case('NONPO-01-04-07-08','Found BS repair creates only real wage, then partial BE conversion',nonpo_wage)
    f.case('ACCESS-POCKET.REVOKE','Revoked pocket actor cannot replay prior successful request; redye viewer denied',access_more)
    f.case('UI.SELECTOR.57','Real 57-source pagination and oldest-source search',selectors)
    f.persist()
if __name__=='__main__':run()

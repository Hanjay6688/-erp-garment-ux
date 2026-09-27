"""Own remaining pocket invoice, descendant, cutoff, volume and non-PO probes."""
import native as n,flows as f,pocket as p,extended as e,daily as d,suite as s
from decimal import Decimal as D
from psycopg.types.json import Jsonb
import psycopg,json,copy,threading,time
from concurrent.futures import ThreadPoolExecutor
C=n.C;X=f.X;A=n.A;eq=n.eq;uid=n.uid

def fixture(key):
    if key not in X:raise n.Blocked('Missing successful independent prerequisite: '+key)
    return X[key]
def physical():
    # Native costs/snapshots may change; immutable movement identity, quantity and date may not.
    keys=['id','material_id','product_id','location_id','roll_id','lot_id','movement_type','source_type','source_id','qty_signed','quality_grade','physical_at','movement_at','movement_date','created_at','reversal_of_id']
    return {table:A("select md5(coalesce(string_agg((select jsonb_object_agg(k,to_jsonb(t)->k) from unnest(%s::text[]) k)::text,'' order by id),'')) from erp."+table+' t',(keys,),one=True) for table in ['fg_stock_movements','material_stock_movements','sewing_terminal_events']}
def source_setup():
    entities=[('SUPPLIER',[{'supplier_code':'BE-AUD-LIVE','supplier_name':'Independent pocket supplier'}]),('MATERIAL',[{'material_sku':'BE-AUD-LIVE','material_name':'Independent invoiced pocket fabric','material_type':'FABRIC','unit_code':'METER'}]),('MATERIAL_ROLL',[{'material_sku':'BE-AUD-LIVE','roll_number':'BE-AUD-LIVE-ROLL','opening_qty':'20','unit_cost':'17.29','location_code':'AUD-rawloc','control_key':'MAT','opening_source_key':'LIVE-ROLL'}]),('UNINVOICED_RECEIPT',[{'receipt_number':'BE-AUD-LIVE-RECEIPT','receipt_line_number':'1','receipt_date':'2026-09-08','supplier_code':'BE-AUD-LIVE','material_sku':'BE-AUD-LIVE','location_code':'AUD-rawloc','qty':'20','unit_cost':'17.29','control_key':'AP','opening_source_key':'LIVE-ROLL'}]),('OPENING_CONTROL',[{'control_key':'MAT','balance_type':'MATERIAL','qty':'20','amount':'345.80'},{'control_key':'AP','balance_type':'GRNI_MATERIAL','qty':'20','amount':'345.80'}])]
    imp=f.imported('LIVE-RECEIPT',entities);material=A("select id::text from erp.materials where material_sku='BE-AUD-LIVE'",one=True);roll=A("select id::text from erp.material_rolls where roll_number='BE-AUD-LIVE-ROLL'",one=True);supplier=A("select id::text from erp.suppliers where supplier_code='BE-AUD-LIVE'",one=True)
    item=A('select id::text,purchase_id::text from erp.material_purchase_items where material_id=%s',(material,))[0]
    X['live_invoice']={'material':material,'roll':roll,'supplier':supplier,'item':item[0],'purchase':item[1]};n.pocket('REGISTER',{'material_id':material,'reason':'Independent real supplier-backed pocket source'})
    choice=next(x for x in p.ws()['rolls'] if x['id']==roll);post=n.pocket('POST',{'roll_id':roll,'location_id':C['rawloc'],'expected_revision':choice['revision'],'mode':'USED','quantity':'6.75','date':'2026-09-23','reason':'Independent 6.75 used for actual sewing period'})
    X['live_invoice']['issue']=post;eq(f.matqty(material),D('13.25'));return {'import':imp,'source':X['live_invoice'],'issued_once':'6.75'}
def live_wip():
    v=fixture('live_invoice');prod=d.precursor('BE-POCKET',work_at='2026-09-23T08:00:00+07:00');X['pocket_production']=prod
    eq(f.pogl(prod['po']),D('1300.00'));preview=p.preview('2026-09-23','2026-09-23');eq(D(preview['amount']),D('116.71'));eq(D(preview['quantity']),D(13));before=physical()
    result=n.pocket('POST_PERIOD',{'period_start':'2026-09-23','period_end':'2026-09-23','expected_revision':preview['revision'],'reason':'Independent actual 13 sewn PCS live allocation'});v['pool']=result['id'];eq(f.pogl(prod['po']),D('1416.71'));eq(physical(),before)
    return {'production_boundary':'Controlled cut/pickup; native posted work and terminal event','actual_sewing':prod['sewing_terminal'],'preview':preview,'allocation':result,'wip_total':'1416.71','no_second_stock_issue':True}
def live_locks():
    v=fixture('live_invoice');prod=fixture('pocket_production');history=next(x for x in p.ws()['history'] if x['id']==v['issue']['id']);before=physical()
    denied=n.reject(lambda:n.pocket('REVERSE',{'id':history['id'],'expected_version':history['row_version'],'reason':'Independent active-period source inverse'}))
    row=next(x for x in p.ws()['rolls'] if x['id']==v['roll']);new=n.reject(lambda:n.pocket('POST',{'roll_id':v['roll'],'location_id':C['rawloc'],'expected_revision':row['revision'],'mode':'USED','quantity':'1','date':'2026-09-23','reason':'Independent add use inside active allocation'}))
    event_id=prod['sewing_terminal']['sewing_terminal_event_id'];version=A('select row_version from erp.sewing_terminal_events where id=%s',(event_id,),one=True)
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],))
        try:c.execute('select erp.reverse_sewing_terminal_v1(%s,%s,%s::uuid,%s)',(event_id,'Independent active denominator inverse',uid(),version))
        except psycopg.Error as error:c.rollback();eq(error.sqlstate,'P0001');sew={'native_four_argument_guard':str(error),'sqlstate':error.sqlstate}
        else:c.rollback();raise AssertionError('Active sewing denominator reversed')
    eq(physical(),before);return {'source_inverse':denied,'source_membership':new,'sewing_inverse':sew,'unchanged':True}
def public_sewing_wrapper():
    prod=fixture('pocket_production')
    return n.reject(lambda:n.rpc('erp_reverse_sewing_terminal_v1',[prod['sewing_terminal']['sewing_terminal_event_id'],'Independent public active denominator inverse',uid()]))
def live_descendants():
    prod=fixture('pocket_production');v=fixture('live_invoice');before=f.pogl(prod['po'])
    payload=d.dp('BE-POCKET',at='2026-09-24T08:00:00+07:00');payload['pricing']['components']=[{'component_id':C['daily_wash'],'covered_qty':13}]
    sent=s.command('POST_PRICED_DELIVERY',payload);prod['delivery']=sent['delivery_id'];prod['delivery_line']=A('select id::text from erp.laundry_delivery_lines where delivery_id=%s',(sent['delivery_id'],),one=True)
    got=d.rpc('POST_RECEIPT',d.rp('BE-POCKET',at='2026-09-25T08:00:00+07:00'),d.ver('laundry_deliveries',prod['delivery']));prod['receipt']=got['receipt_id'];prod['receipt_line']=A('select id::text from erp.laundry_receipt_lines where receipt_id=%s',(got['receipt_id'],),one=True)
    loc=e.location('BE-AUD-LIVE-DESC');q=d.qp('BE-POCKET');q.update(destination_location_id=loc,physical_at='2026-09-25T10:00:00+07:00');qc=d.rpc('POST_FINAL_SKU',q,d.ver('cutting_groups',prod['group']));eq(f.pogl(prod['po']),D('57590.88'))
    lots=A('select id::text,product_id::text from erp.fg_lots where po_id=%s',(prod['po'],));source=next(a for a,b in lots if b==C['product']);row=n.ws({'source_lot_id':source})['lots'][0]
    conv=n.cmd('POST',{'source_lot_id':source,'target_product_id':C['target'],'location_id':loc,'qty_pcs':3,'physical_at':'2026-09-25T12:00:00+07:00','reason':'Independent pocket cost into partial converted descendant','expected_version':row['source_revision']});sl=e.sale(C['target'],loc,conv['destination_lot_id'],'POCKET',qty=2,at='2026-09-26T08:00:00+07:00');ret=e.returned(sl,'POCKET',at='2026-09-26T10:00:00+07:00');eq(n.lotqty(source),4);eq(n.lotqty(conv['destination_lot_id']),2);eq(f.pogl(prod['po']),D('57590.88'))
    v.update(conversion=conv,source=source,sale=sl,returned=ret,location=loc);return {'sent':sent,'received':got,'qc':qc,'conversion':conv,'sale':sl,'return':ret,'qty_source':4,'qty_converted_remaining':2,'net_sold':1,'conserved_cost':'57590.88'}
def invoice_up():
    v=fixture('live_invoice');prod=fixture('pocket_production');before=physical();old=e.report('2026-09-26');payload={'invoice_number':'BE-AUD-POCKET-INVOICE','supplier_id':v['supplier'],'invoice_date':'2026-09-27','change_reason':'Independent actual pocket supplier price 19.31','lines':[{'purchase_item_id':v['item'],'qty_invoiced':'20','unit_price':'19.31','discount_amount':'0'}]}
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],));r=c.execute('select erp.save_material_supplier_invoice_draft_v2(%s,%s::uuid,null)',(Jsonb(payload),uid())).fetchone()[0];c.execute('select erp.post_material_supplier_invoice(%s)',(r['supplier_invoice_id'],))
    v['invoice']=r['supplier_invoice_id'];f.persist();history=next(x for x in p.ws()['history'] if x['id']==v['issue']['id']);eq(D(history['current_cost']),D('130.34'));eq(f.pogl(prod['po']),D('57604.51'));eq(physical(),before);eq(e.report('2026-09-26')['financial_position'],old['financial_position'])
    n.E.append({'native_supplier_payload':payload,'response':r});return {'invoice':r,'actual_source_cost':'130.34','po_with_descendant_and_sale_cost':'57604.51','source_delta':'13.63','physical_and_prior_asof_unchanged':True}
def invoice_down():
    v=fixture('live_invoice');prod=fixture('pocket_production');before=physical()
    if 'invoice' not in v:raise n.Blocked('Actual supplier invoice not successfully posted')
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],));c.execute('select erp.reverse_material_supplier_invoice(%s,%s)',(v['invoice'],'Independent reverse unpaid source invoice'))
    history=next(x for x in p.ws()['history'] if x['id']==v['issue']['id']);eq(D(history['current_cost']),D('116.71'));eq(f.pogl(prod['po']),D('57590.88'));eq(physical(),before)
    return {'reversed_invoice':v['invoice'],'source_cost_restored':'116.71','conserved_cost':'57590.88','physical_unchanged':True}
def live_cancel():
    v=fixture('live_invoice');prod=fixture('pocket_production');state=next(x for x in p.ws()['periods'] if x['id']==v['pool']);before=physical();r=n.pocket('CANCEL_PERIOD',{'id':v['pool'],'expected_revision':state['revision'],'reason':'Independent remove pocket cost after conversion and sale'});eq(f.pogl(prod['po']),D('57474.17'));eq(physical(),before)
    return {'cancelled':r,'po_cost_without_pocket':'57474.17','source_remains_real_expense':True,'physical_unchanged':True}
def nonpo_modes():
    src=fixture('nonpo_bs');before=n.fp();payload={'order':{'rework_number':'BE-AUD-NONPO-MODE','bs_case_id':src['case'],'destination_type':'LAUNDRY','vendor_id':C['daily_vendor'],'contractor_id':None,'qty_sent':3,'qty_good_returned':0,'qty_bs_returned':0,'physical_sent_at':'2026-09-16T08:00:00+07:00','status':'IN_PROGRESS','return_fg_location_id':C['fg'],'components':[],'accessory_bom_version_id':None,'accessory_bom_item_ids':[],'change_reason':'Independent genuine non-PO new identity rework'},'target_product_id':C['target'],'reason':'Independent genuine non-PO new identity rework'}
    try:result=n.cmd('SAVE_REWORK',payload)
    except psycopg.Error as error:
        eq(n.fp(),before);X['nonpo_mode_gap']={'stage':'SAVE_REWORK','error':str(error),'sqlstate':error.sqlstate};raise
    request=uid();oid=result['rework_id'];X['nonpo_new_mode']={'start':result,'order':oid};f.persist()
    r=n.bs('COMPLETE_REWORK',{'rework_order_id':oid,'qty_good':2,'qty_bs':1,'completed_at':'2026-09-17T08:00:00+07:00','return_fg_location_id':C['fg'],'change_reason':'Independent actual non-PO rework 2 GOOD and 1 BS'},d.ver('rework_orders',oid),request)
    return {'order':result,'completion':r,'source_po':None}
def boundary_redye():
    # CANCEL opening source has 9 BS and no active order after positive cancellation.
    payload=f.rpayload('CANCEL');tests=[]
    for name,changes in [('SIZE',{'target_product_id':C['wrongsize']}),('IDENTICAL',{'target_product_id':C['redye_product']})]:tests.append({'case':name,'result':n.reject(lambda changes=changes:n.cmd('SAVE_REDYE',{**payload,**changes}))})
    for name,at in [('FUTURE','2099-01-01T08:00:00+07:00'),('BEFORE','2026-09-01T08:00:00+07:00')]:tests.append({'case':name,'result':n.reject(lambda at=at:n.cmd('SAVE_REDYE',{**payload,'order':{**payload['order'],'rework_number':'BE-AUD-BOUNDARY-'+name,'physical_sent_at':at}}))})
    return tests
def recovery_atomic():
    before=n.fp();payload=n.pconv('EXTRA',qty=1,physical_at='2026-09-26T15:00:00+07:00');n.E.append({'unrelated_after_po_conversion':payload,'before':before})
    try:r=n.cmd('POST',payload)
    except psycopg.Error as err:
        eq(n.fp(),before);n.E.append({'unrelated_conversion_atomic_refusal':True,'sqlstate':err.sqlstate,'error':str(err)});raise
    return {'unrelated_posted':r}
def closed_pocket():
    # Independent closed-period posting attempt; rollback the fixture cutoff.
    before=A('select to_jsonb(t) from erp.accounting_period_control t');state=p.preview('2026-09-01','2026-09-04');events=physical()
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],));c.execute("select set_config('app.change_reason','Independent rolled-back closed pocket fixture',true)");c.execute("update erp.accounting_period_control set closed_through='2026-09-25',change_reason='Independent fixture' where singleton_id=1")
        try:
            r=c.execute('select public.erp_save_pocket_fabric_action_v1(%s,%s,%s::uuid)',('POST_PERIOD',Jsonb({'period_start':state['period_start'],'period_end':state['period_end'],'expected_revision':state['revision'],'reason':'Independent closed period allocation attempt'}),uid())).fetchone()[0]
            dates=c.execute('select j.transaction_date::text,j.economic_date::text from erp.pocket_period_events e join erp.journal_entries j on j.id=e.journal_entry_id where pool_id=%s',(r['id'],)).fetchall()
            assert dates and all(a>'2026-09-25' for a,b in dates),dates;out={'accepted_with_open_posting':r,'dates':dates}
        except psycopg.Error as err:
            assert err.sqlstate=='P0001' and any(word in str(err).lower() for word in ['closed','tutup']),str(err);out={'refused':True,'error':str(err),'sqlstate':err.sqlstate}
        finally:c.rollback()
    eq(A('select to_jsonb(t) from erp.accounting_period_control t'),before);eq(physical(),events);return out
def import_conflict():
    # Import is first validated with no active allocation. Both real public
    # commands succeed in isolation, then compete while a transaction is held.
    header=n.imp('CREATE',{'batch_code':'BE-AUD-RACE-IMPORT','cutover_date':'2026-09-10','notes':'Independent stale validated import race'})
    header=n.imp('SAVE_FILE',{'batch_id':header['batch_id'],'expected_revision':header['revision'],'entity':'OPENING_POCKET_USAGE','filename':'race.csv','rows':[{'source_row_no':1,'payload':{'document_number':'BE-AUD-RACE-SOURCE','line_number':'1','physical_date':'2026-09-07','material_sku':'BE-AUD-POCKET','qty':'1','amount':'17.29','allocation_status':'UNALLOCATED','control_key':'RACE','control_qty':'1','control_amount':'17.29'}}]})
    header=n.imp('VALIDATE',{'batch_id':header['batch_id'],'expected_revision':header['revision']});eq(header['error_rows'],0);payload={'batch_id':header['batch_id'],'expected_revision':header['revision']}
    with s.actor_conn('admin') as control:
        response=control.execute('select public.erp_save_initial_import_action_v1(%s,%s,%s::uuid)',('FINALIZE',Jsonb(payload),uid())).fetchone()[0];eq(response['status'],'POSTED');control.rollback()
    unrelated=n.imp('CREATE',{'batch_code':'BE-AUD-UNRELATED-LOCK','cutover_date':'2026-09-10','notes':'Independent unrelated-domain concurrency'})
    unrelated=n.imp('SAVE_FILE',{'batch_id':unrelated['batch_id'],'expected_revision':unrelated['revision'],'entity':'CUSTOMER','filename':'unrelated.csv','rows':[{'source_row_no':1,'payload':{'customer_code':'BE-AUD-UNRELATED-LOCK','customer_name':'Independent unrelated customer'}}]})
    unrelated=n.imp('VALIDATE',{'batch_id':unrelated['batch_id'],'expected_revision':unrelated['revision']});eq(unrelated['error_rows'],0)
    unrelated_payload={'batch_id':unrelated['batch_id'],'expected_revision':unrelated['revision']}
    with s.actor_conn('admin') as control:
        unrelated_control=control.execute('select public.erp_save_initial_import_action_v1(%s,%s,%s::uuid)',('FINALIZE',Jsonb(unrelated_payload),uid())).fetchone()[0];eq(unrelated_control['status'],'POSTED');control.rollback()
    preview=p.preview();period={'period_start':preview['period_start'],'period_end':preview['period_end'],'expected_revision':preview['revision'],'reason':'Independent held allocation versus stale import'}
    with s.actor_conn('owner') as holder:
        held=holder.execute('select public.erp_save_pocket_fabric_action_v1(%s,%s,%s::uuid)',('POST_PERIOD',Jsonb(period),uid())).fetchone()[0]
        with s.actor_conn('admin') as other:
            other.execute("set local lock_timeout='1200ms'")
            try:other.execute('select public.erp_save_initial_import_action_v1(%s,%s,%s::uuid)',('FINALIZE',Jsonb(payload),uid())).fetchone()
            except psycopg.Error as error:blocked={'sqlstate':error.sqlstate,'error':str(error)};eq(error.sqlstate,'55P03');other.rollback()
            else:other.rollback();holder.rollback();raise AssertionError('Conflicting import did not wait for in-flight allocation')
        with s.actor_conn('admin') as other:
            other.execute("set local lock_timeout='1200ms'")
            try:
                r=other.execute('select public.erp_save_initial_import_action_v1(%s,%s,%s::uuid)',('FINALIZE',Jsonb(unrelated_payload),uid())).fetchone()[0];eq(r['status'],'POSTED');unrelated_during={'completed':True,'response':r}
            except psycopg.Error as error:
                eq(error.sqlstate,'55P03');unrelated_during={'completed':False,'sqlstate':error.sqlstate,'error':str(error)};other.rollback()
        holder.commit()
    before=physical();refused=n.reject(lambda:n.imp('FINALIZE',payload,who='admin'));eq(physical(),before)
    state=next(x for x in p.ws()['periods'] if x['id']==held['id']);n.pocket('CANCEL_PERIOD',{'id':held['id'],'expected_revision':state['revision'],'reason':'Independent race fixture cleanup'})
    unrelated_after=unrelated_during['response'] if unrelated_during['completed'] else n.imp('FINALIZE',unrelated_payload,who='admin');eq(unrelated_after['status'],'POSTED')
    observation={'valid_before_race':header,'admin_positive_finalization_rolled_back':response,'conflicting_writer_waited':blocked,'unrelated_positive_control':unrelated_control,'unrelated_domain_while_lock_held':unrelated_during,'unrelated_after_release':unrelated_after,'refused_after_commit':refused,'no_stale_membership':True}
    n.E.append({'independent_scoped_import_race':observation});f.persist()
    assert unrelated_during['completed'],observation
    return observation
def capacity():
    v=fixture('live_invoice');fixture('pocket_production')
    # A legitimate older active period, followed by 51 successful correction/reallocation cycles.
    old_preview=p.preview();old=n.pocket('POST_PERIOD',{'period_start':old_preview['period_start'],'period_end':old_preview['period_end'],'expected_revision':old_preview['revision'],'reason':'Independent oldest active period must remain operable'})
    X['capacity']={'old':old,'cycles':[]};f.persist()
    for i in range(51):
        preview=p.preview('2026-09-23','2026-09-23');made=n.pocket('POST_PERIOD',{'period_start':'2026-09-23','period_end':'2026-09-23','expected_revision':preview['revision'],'reason':'Independent real reallocation cycle '+str(i)})
        state=next(x for x in p.ws()['periods'] if x['id']==made['id']);n.pocket('CANCEL_PERIOD',{'id':made['id'],'expected_revision':state['revision'],'reason':'Independent real cycle inverse '+str(i)});X['capacity']['cycles'].append(made['id'])
    found={q:any(x['id']==old['id'] for x in p.ws(q)['periods']) for q in ['',old['id'],'2026-09-05']};state=A('select erp.pocket_period_state_v1(%s)',(old['id'],),one=True);eq(state['status'],'ACTIVE');X['capacity'].update(search_found=found,state=state);f.persist();n.E.append({'actual_oldest_active_period':state,'workspace_searches_found':found,'posted_periods':A('select count(*) from erp.pocket_periods',one=True),'returned':len(p.ws()['periods'])})
    assert all(found.values()),{'active_period':old['id'],'searches_found':found,'workspace_returned':len(p.ws()['periods']),'actual_active':state}
def run():
    f.load()
    if 'capacity' in X and 'state' in X['capacity']:
        cap=X['capacity'];state=A('select erp.pocket_period_state_v1(%s)',(cap['old']['id'],),one=True)
        if state['status']=='ACTIVE':n.pocket('CANCEL_PERIOD',{'id':state['id'],'expected_revision':state['revision'],'reason':'Independent volume fixture cleanup after browser attempt'})
    f.case('SETUP-LIVE-INVOICE','Public import of actual supplier-backed pocket roll',source_setup)
    f.case('POCKET-07-08.WIP','Actual sewing denominator and initial WIP allocation',live_wip,'Controlled predecessor; native work/terminal plus public allocation')
    f.case('POCKET-13.LIVE','Active source and denominator inverses refuse atomically',live_locks)
    f.case('RELATED.SEWING-WRAPPER','Public sewing inverse reaches actual domain guard',public_sewing_wrapper)
    f.case('POCKET-07-08.DESC','Laundry QC conversion sale and return retain pocket cost',live_descendants,'Public production/conversion; native sale/return')
    f.case('POCKET-09.INVOICE-UP','Actual supplier invoice increases only cost and preserves prior report',invoice_up,'Public sources plus native supplier posting')
    f.case('POCKET-09.INVOICE-DOWN','Inverse unpaid supplier invoice restores source and descendant cost',invoice_down,'Native supplier inverse and direct GL')
    f.case('POCKET-11.DESC','Cancel allocation after conversion and sale without stock movement',live_cancel)
    f.case('NONPO-05-06','Actual non-PO new-identity rework route and GOOD completion',nonpo_modes)
    f.case('REDYE-07-14','Wrong size same identity future and pre-source dispatch refused',boundary_redye)
    f.case('CROSS-PO-NONPO','Unrelated non-PO conversion still works after legitimate PO conversion',recovery_atomic)
    f.persist()
if __name__=='__main__':run()

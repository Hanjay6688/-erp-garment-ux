"""Independent BE cross-family physical and financial flows; no writer probes."""
import native as n
import suite as s
import daily as d
import json,copy,traceback,threading,time
from decimal import Decimal as D
from concurrent.futures import ThreadPoolExecutor
from psycopg.types.json import Jsonb
import psycopg
C=n.C;F=n.F;A=n.A;eq=n.eq;uid=n.uid;X={}

def load():
    x=json.loads((s.OUT/'be-fixtures.json').read_text());C.update(x['identity']);F.update(x['sources']);d.F.update(x['daily'])
    n.R.extend(json.loads((s.OUT/'be-native-results.json').read_text())['results']);n.E.extend(json.loads((s.OUT/'be-native-events.json').read_text()))
    if (s.OUT/'be-flow-fixtures.json').exists():X.update(json.loads((s.OUT/'be-flow-fixtures.json').read_text()))

def persist():n.save();(s.OUT/'be-flow-fixtures.json').write_text(json.dumps(X,indent=2,default=str)+'\n')
def case(key,title,fn,layer='authenticated public SQL RPC'):
    try:n.case(key,title,fn,layer)
    finally:persist()
def bc(action,payload,request=None):return n.rpc('erp_save_accessory_service_action_v1',[action,payload,request or uid()])
def bp(key,value):
    version=A('select version from erp.bc_policy_settings_v1 where policy_key=%s',(key,),one=True)
    return bc('SET_POLICY',{'policy_key':key,'operation':'SET','expected_version':str(version),'value':value,'reason':'Independent synthetic audit configuration only'})
def imported(code,entities,cutover='2026-09-10'):
    b=n.imp('CREATE',{'batch_code':'BE-AUD-'+code,'cutover_date':cutover,'notes':'Independent synthetic source sheets'})
    for entity,rows in entities:
        b=n.imp('SAVE_FILE',{'batch_id':b['batch_id'],'expected_revision':b['revision'],'entity':entity,'filename':entity.lower()+'.csv','rows':[{'source_row_no':i,'payload':r} for i,r in enumerate(rows,1)]})
    b=n.imp('VALIDATE',{'batch_id':b['batch_id'],'expected_revision':b['revision']})
    if b['error_rows']:raise n.Blocked(json.dumps({'fixture_import':code,'validation':b,'rows':A('select entity_type,source_row_no,validation_status,validation_errors,normalized_payload from erp.migration_staging_rows where batch_id=%s order by entity_type,source_row_no',(b['batch_id'],))},default=str))
    b=n.imp('FINALIZE',{'batch_id':b['batch_id'],'expected_revision':b['revision']});eq(b['status'],'POSTED');return b

def materials():
    b=imported('MATERIALS',[
      ('ACCESSORY_CATEGORY',[{'category_code':'BE-AUD-TAG','category_name':'Independent tag','base_uom_code':'PCS'}]),
      ('MATERIAL',[{'material_sku':'BE-AUD-TAG','material_name':'Independent new tag','material_type':'ACCESSORY','unit_code':'PCS','accessory_category_code':'BE-AUD-TAG'}, {'material_sku':'BE-AUD-POCKET','material_name':'Independent pocket fabric','material_type':'FABRIC','unit_code':'METER'}]),
      ('MATERIAL_ROLL',[{'material_sku':'BE-AUD-POCKET','roll_number':'BE-AUD-ROLL','opening_qty':'20','unit_cost':'17.29','location_code':'AUD-rawloc','control_key':'FAB','opening_source_key':'BE-AUD-ROLL'}]),
      ('OPENING_BALANCE_ITEM',[{'balance_type':'MATERIAL','material_sku':'BE-AUD-TAG','location_code':'AUD-rawloc','qty':'30','unit_cost':'23.17','control_key':'TAG','opening_source_key':'BE-AUD-TAG'}]),
      ('OPENING_CONTROL',[{'control_key':'FAB','balance_type':'MATERIAL','qty':'20','amount':'345.80'}, {'control_key':'TAG','balance_type':'MATERIAL','qty':'30','amount':'695.10'}])])
    X['materials_batch']=b['batch_id'];C['tag']=A("select id::text from erp.materials where material_sku='BE-AUD-TAG'",one=True);C['pocket_material']=A("select id::text from erp.materials where material_sku='BE-AUD-POCKET'",one=True);C['pocket_roll']=A("select id::text from erp.material_rolls where roll_number='BE-AUD-ROLL'",one=True)
    X['expense']=A("select erp.account_id('OTHER_EXPENSE')::text",one=True)
    bp('ACC_DEC04',{'OWN_FG_REPAIR_account_id':X['expense']});bp('ACC_DEC07',{'approval':'NONE'});bp('ACC_DEC01',{'mode':'BOTH_REAL_TIMELINES'})
    C['inspection']=bc('REGISTER_ZONE',{'zone_kind':'INSPECTION','location_code':'BE-AUD-INSPECT','location_name':'Independent inspection','reason':'Independent return custody'})['location_id']
    return {'import':b,'stock':matqty(C['tag']),'material_average':A('select moving_average_cost from erp.materials where id=%s',(C['tag'],),one=True)}
def matqty(m):return A('select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=%s',(m,),one=True)
def conversion_doc(c):return next(x for x in n.ws()['documents'] if x['id']==c)
def usage():
    f=n.source('MAIN');cid=f['conversion'];beforemat=matqty(C['tag']);beforeqty=(n.lotqty(f['lot']),n.lotqty(f['targetlot']))
    p={'conversion_id':cid,'expected_version':conversion_doc(cid)['revision'],'location_id':C['rawloc'],'physical_at':'2026-09-16T08:00:00+07:00','items':[{'material_id':C['tag'],'qty':'5'}],'reason':'Five tags actually fitted to converted garments'}
    req=uid();r=n.cmd('POST_USAGE',p,req);X['usage']={'payload':p,'request':req,'response':r}
    eq(matqty(C['tag']),beforemat-5);eq((n.lotqty(f['lot']),n.lotqty(f['targetlot'])),beforeqty);eq(n.value(f['targetlot']),D('6288.70'));eq(n.value(f['targetlot'])+n.value(f['lot']),D('16165.26'))
    before=n.fp();eq(n.cmd('POST_USAGE',p,req),r);eq(n.fp(),before)
    return {'response':r,'target_value':n.value(f['targetlot']),'source_value':n.value(f['lot']),'actual_accessory_cost':'115.85','replay_no_effect':True}
def usage_dependency():return n.reject(lambda:n.cmd('REVERSE',{'conversion_id':F['MAIN']['conversion'],'reason':'Attempt inverse while real accessory cost remains'}),'DEPENDANTS')
def recovery():
    p=n.pconv('RETURNS',expected_returns=[{'material_id':C['tag'],'qty':'5','holder':'Independent shop floor'}]);r=n.cmd('POST',p);F['RETURNS'].update(conversion=r['conversion_id'],targetlot=r['destination_lot_id'])
    doc=conversion_doc(r['conversion_id']);eq(doc['value_state'],'PROVISIONAL_RECOVERY');out=doc['returns'][0]['id'];beforemat=matqty(C['tag']);beforevalue=n.value(r['destination_lot_id'])
    rec=bc('RECEIVE_RETURN',{'source_kind':'TEARDOWN','location_id':C['inspection'],'physical_at':'2026-09-16T10:00:00+07:00','items':[{'material_id':C['tag'],'qty':'3','outstanding_id':out}],'reference':'Independent actual receipt 3 of expected 5','reason':'Actual returned tags; two still outside'})
    lot=rec['lot_ids'][0];ins=bc('INSPECT',{'lot_id':lot,'inspected_at':'2026-09-16T11:00:00+07:00','inspector':'Independent audit inspector','qty_usable':'2','qty_damaged':'1','reason':'Two usable and one damaged actually counted'})
    eq(matqty(C['tag']),beforemat);eq(n.value(r['destination_lot_id']),beforevalue)
    doc=conversion_doc(r['conversion_id']);eq(D(doc['returns'][0]['received']),D(3));eq(D(doc['returns'][0]['unreturned']),D(2));eq(D(doc['returns'][0]['awaiting_value']),D(3))
    vp={'lot_id':lot,'condition':'USABLE','qty':'2','unit_value':'7.13','location_id':C['rawloc'],'physical_at':'2026-09-17T08:00:00+07:00','reason':'Explicit synthetic recovery value, two usable tags'}
    pending=n.reject(lambda:bc('VALUE_CUSTODY',vp),'PENDING')
    bp('ACC_DEC03',{'credit_account_id':X['expense'],'unit_value_cap':'NONE'})
    X['recovery']={'receipt':rec,'lot':lot,'conversion':r,'valuation_payload':vp,'before_material':str(beforemat),'before_value':str(beforevalue),'inspection':ins,'pending_policy_refusal':pending};persist()
    val=bc('VALUE_CUSTODY',vp);eq(matqty(C['tag']),beforemat+2);eq(n.value(r['destination_lot_id']),beforevalue-D('14.26'))
    X['recovery']={'receipt':rec,'lot':lot,'conversion':r,'valuation':val}
    return {'conversion':r,'received':rec,'inspected':ins,'pending_policy_refusal':pending,'valued':val,'actual_stock_added':2,'target_value':n.value(r['destination_lot_id']),'unreturned':2,'damaged_pending':1}

def new_products():
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('app.change_reason','Independent unique source/target master fixtures',true)")
        c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],))
        for key,sku,color in [('redye_product','BE-AUD-REDYE','BE-NAVY'),('redye_target','BE-AUD-EMERALD','EMERALD'),('pocket_product','BE-AUD-POCKET-FG','BE-POCKET')]:
            ident=uid();C[key]=ident;c.execute("insert into erp.products(id,identity_root_id,sku,model_id,brand_id,color_name,size_id,product_name,effective_from) values(%s,%s,%s,%s,%s,%s,%s,%s,'2026-09-01T08:00:00+07:00')",(ident,ident,sku,C['model'],C['brand'],color,C['s1'],sku))
            c.execute("insert into erp.accessory_bom_versions(product_id,version_label,effective_from,notes,created_by) values(%s,'BE-AUD-NONE','2026-09-01T08:00:00+07:00','Explicit no accessory fixture',%s)",(ident,C['app_owner']))
        C['redye_process']=uid();C['unknown_process']=uid()
        for k in ['redye_process','unknown_process']:c.execute('insert into erp.wash_processes(id,process_code,process_name) values(%s,%s,%s)',(C[k],'BE-AUD-'+k,'Independent '+k))
    return {'products':{k:C[k] for k in ['redye_product','redye_target','pocket_product']},'processes':[C['redye_process'],C['unknown_process']]}

def redye_sources():
    keys=['KNOWN','UNKNOWN','FREE','LEGACY','CANCEL','BAD','RACE','UI','MOBILE']
    entities=[('OPEN_PO',[{'po_number':'BE-AUD-RD-'+k,'model_code':'AUD-DAY','contractor_code':'AUD-DAY','target_qty_pcs':'9','status':'QC','current_stage':'QC','physical_start_at':'2026-09-02T08:00:00+07:00'} for k in keys]),
      ('OPENING_BALANCE_ITEM',[{'balance_type':'BS','product_sku':'BE-AUD-REDYE','brand_code':'AUD-brand','model_code':'AUD-DAY','color_name':'BE-NAVY','size_code':'AUD-1','location_code':'AUD-fg','stage':'QC','qty':'9','unit_cost':'1432.19','amount':'12889.71','po_number':'BE-AUD-RD-'+k,'accessory_cost_included':'false','opening_source_key':'BE-AUD-BS-'+k,'control_key':k,'hpp_input_method':'MANUAL'} for k in keys]),
      ('OPENING_CONTROL',[{'control_key':k,'balance_type':'BS','qty':'9','amount':'12889.71'} for k in keys])]
    before=A('select count(*) from erp.sewing_terminal_events',one=True);b=imported('REDYE-SOURCES',entities)
    eq(A('select count(*) from erp.sewing_terminal_events',one=True),before,'Opening BS cannot fabricate historical sewing')
    X['redye']={}
    for k in keys:
        row=A('select p.id::text,b.id::text from erp.production_orders p join erp.bs_cases b on b.po_id=p.id where p.po_number=%s',('BE-AUD-RD-'+k,))[0];X['redye'][k]={'po':row[0],'bs':row[1]}
    rate=s.command('SAVE_PROCESS_RATE',{'vendor_id':C['daily_vendor'],'wash_process_id':C['redye_process'],'rate_per_pcs':'197.31','effective_from':'2026-09-01T08:00:00+07:00','reason':'Independent agreed synthetic redye price'})
    s.policy('LAU_DEC02',{'billable':['GOOD','BS']})
    return {'import':b,'rate':rate,'sources':X['redye']}

def rsource(k):
    try:return X['redye'][k]
    except KeyError:raise n.Blocked('Independent opening BS fixture unavailable: '+k)
def order(k,qty=7):
    f=rsource(k)
    return {'rework_number':'BE-AUD-RW-'+k,'bs_case_id':f['bs'],'destination_type':'LAUNDRY','contractor_id':None,'vendor_id':C['daily_vendor'],'qty_sent':qty,'qty_good_returned':0,'qty_bs_returned':0,'physical_sent_at':'2026-09-14T08:00:00+07:00','status':'IN_PROGRESS','return_fg_location_id':C['fg'],'change_reason':'Independent actual BS dispatch','notes':'Independent redye fixture','accessory_bom_version_id':None,'accessory_bom_item_ids':[],'components':[]}
def rpayload(k,unknown=False,qty=7):return {'order':order(k,qty),'target_product_id':C['redye_target'],'wash_process_id':C['unknown_process'] if unknown else C['redye_process'],'price_status':'UNKNOWN' if unknown else 'KNOWN','reason':'Independent new-color service, actual source BS'}
def poqty(po):return A('select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id where l.po_id=%s',(po,),one=True)
def pogl(po):return A("select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.po_id=%s and l.account_id in(erp.account_id('WIP'),erp.account_id('FG_INVENTORY'),erp.account_id('COGS')) and j.status in('POSTED','REVERSED')",(po,),one=True)
def start_redye(k='KNOWN',unknown=False):
    f=rsource(k);beforeqty=poqty(f['po']);ap=A("select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.vendor_id=%s and l.account_id=erp.account_id('AP_VENDOR') and j.status in('POSTED','REVERSED')",(C['daily_vendor'],),one=True)
    p=rpayload(k,unknown);req=uid();r=n.cmd('SAVE_REDYE',p,req);f.update(service=r['service_id'],order=r['rework_id'],payload=p,request=req,response=r)
    eq(poqty(f['po']),beforeqty);eq(A("select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.vendor_id=%s and l.account_id=erp.account_id('AP_VENDOR') and j.status in('POSTED','REVERSED')",(C['daily_vendor'],),one=True),ap)
    eq(r['price_status'],'UNKNOWN' if unknown else 'KNOWN')
    if not unknown:eq(D(r['rate']),D('197.31'));eq(pogl(f['po']),D('14270.88'))
    before=n.fp();eq(n.cmd('SAVE_REDYE',p,req),r);eq(n.fp(),before)
    return {'response':r,'fg_unchanged':beforeqty,'no_posted_vendor_invoice_payable':True,'cost_ledger':pogl(f['po']),'note':'Known service estimate accrues at dispatch; no AP invoice or FG fabricated'}
def partial():
    f=rsource('KNOWN');before=poqty(f['po']);r=n.bs('SAVE_REWORK',{'id':f['order'],'action':'SAVE','qty_good_returned':2,'qty_bs_returned':1,'return_fg_location_id':C['fg'],'change_reason':'Independent physical first partial 2 good plus 1 BS'},d.ver('rework_orders',f['order']))
    o=d.row('rework_orders',f['order']);eq(o['status'],'PARTIAL');eq(o['qty_good_returned'],2);eq(o['qty_bs_returned'],1);eq(poqty(f['po']),before);eq(o['cost_posted'],False)
    return {'response':r,'order':o,'fg_unchanged':before}
def complete(k='KNOWN',good=5,bad=2):
    f=rsource(k);p={'rework_order_id':f['order'],'qty_good':good,'qty_bs':bad,'completed_at':'2026-09-18T00:01:00+07:00','return_fg_location_id':C['fg'],'change_reason':'Independent final actual cumulative result'}
    req=uid();ver=d.ver('rework_orders',f['order']);r=n.bs('COMPLETE_REWORK',p,ver,req);f.update(completion=r,complete_payload=p,complete_request=req,complete_version=ver)
    eq(poqty(f['po']),good);o=d.row('rework_orders',f['order']);eq(o['status'],'COMPLETED');eq(o['qty_good_returned'],good);eq(o['qty_bs_returned'],bad)
    rows=A('select c.to_product_id::text,a.source_lot_id::text,a.destination_lot_id::text,a.qty_pcs from erp.be_conversion_sources_v1 s join erp.product_conversions c on c.id=s.conversion_id join erp.product_conversion_allocations a on a.conversion_id=c.id where s.rework_id=%s',(f['order'],));eq(len(rows),1);eq(rows[0][0],C['redye_target']);eq(rows[0][3],good);eq(n.lotqty(rows[0][1]),0);eq(n.lotqty(rows[0][2]),good);f['targetlot']=rows[0][2]
    resolved=A('select coalesce(sum(qty_pcs),0) from erp.bs_resolutions where bs_case_id=%s',(f['bs'],),one=True);eq(resolved,good);eq(9-resolved,2+bad)
    if k=='KNOWN':eq(pogl(f['po']),D('14270.88'))
    return {'response':r,'lineage':rows,'remaining_bs':9-resolved,'good':good,'total_pieces':9,'cost_ledger':pogl(f['po']),'good_hpp':n.lotcost(f['targetlot'])}
def redye_replay():
    f=rsource('KNOWN');before=n.fp();r=n.bs('COMPLETE_REWORK',f['complete_payload'],f['complete_version'],f['complete_request']);eq(n.fp(),before);eq(r,f['completion']);return r

def physical_fingerprint():
    # Unit-cost snapshots may legitimately be recosted; physical facts must not change.
    return {'fg_stock_movements':A("select md5(coalesce(string_agg((to_jsonb(t)-'unit_hpp_snapshot')::text,'' order by id),'')) from erp.fg_stock_movements t",one=True),**n.fp(['bs_cases','bs_resolutions','rework_orders'])}

def redye_invoice(k='KNOWN',amount='1417.53'):
    f=rsource(k);lines=[{'line_kind':'BILL','rework_service_id':f['service'],'category':'GOOD','qty':5,'amount':'1012.52','note':'Independent actual invoice good share'}, {'line_kind':'BILL','rework_service_id':f['service'],'category':'BS','qty':2,'amount':'405.01','note':'Independent actual invoice serviced BS'}]
    p={'vendor_id':C['daily_vendor'],'invoice_number':'BE-AUD-REDYE-ACTUAL','invoice_date':'2026-09-19','header_total':amount,'lines':lines}
    phy=physical_fingerprint()
    dr=s.command('SAVE_INVOICE_DRAFT',p);eq(physical_fingerprint(),phy)
    r=s.command('POST_INVOICE',{'invoice_id':dr['invoice_id'],'expected_version':str(dr['row_version'])});f['invoice']=r
    eq(pogl(f['po']),D('14307.24'));eq(physical_fingerprint(),phy)
    vals=A('select sum(l.net_amount),sum(l.released_estimate),sum(l.product_variance) from erp.bd_laundry_invoice_lines_v1 l where invoice_id=%s',(r['invoice_id'],))[0];eq(vals,(D('1417.53'),D('1381.17'),D('36.36')))
    return {'draft':dr,'posted':r,'net_estimate_delta':vals,'total_cost':'14307.24','physical_unchanged':phy}

def known_snapshot():
    f=rsource('KNOWN');before=A('select to_jsonb(t) from erp.be_redye_services_v1 t where id=%s',(f['service'],),one=True);cost=pogl(f['po'])
    r=s.command('SAVE_PROCESS_RATE',{'vendor_id':C['daily_vendor'],'wash_process_id':C['redye_process'],'rate_per_pcs':'213.47','effective_from':'2026-09-22T08:00:00+07:00','reason':'New independent rate after original dispatch'})
    eq(A('select to_jsonb(t) from erp.be_redye_services_v1 t where id=%s',(f['service'],),one=True),before);eq(pogl(f['po']),cost)
    return {'new_master':r,'original_service_immutable':before,'old_cost_unchanged':cost}
def unknown_price():
    start=start_redye('UNKNOWN',True);f=rsource('UNKNOWN');eq(pogl(f['po']),D('12889.71'))
    r=s.command('SET_REDYE_PRICE',{'service_id':f['service'],'rate':'197.31','reason':'Owner supplies exact previously unknown service amount'})
    eq(r['price_status'],'KNOWN');eq(pogl(f['po']),D('14270.88'));return {'start':start,'bd_router':r,'cost':'14270.88'}
def redye_free():
    start=start_redye('FREE',True);f=rsource('FREE');r=n.cmd('SET_REDYE_PRICE',{'service_id':f['service'],'rate':'0.00','reason':'Explicit synthetic owner-waived service; no implied default zero'})
    eq(r['price_status'],'KNOWN');eq(D(r['rate']),D(0));eq(pogl(f['po']),D('12889.71'));done=complete('FREE');eq(pogl(f['po']),D('12889.71'))
    return {'start':start,'explicit_zero':r,'completion':done,'note':'BE own explicit unknown-to-known zero path, not BD component FREE policy acceptance'}
def legacy():
    f=rsource('LEGACY');before=pogl(f['po']);p=order('LEGACY',qty=7);r=n.bs('SAVE_REWORK',p);f['order']=r['rework_order_id'];before_be=A('select count(*) from erp.be_redye_services_v1',one=True)
    done=n.bs('COMPLETE_REWORK',{'rework_order_id':f['order'],'qty_good':5,'qty_bs':2,'completed_at':'2026-09-18T08:00:00+07:00','return_fg_location_id':C['fg'],'change_reason':'Independent free same-product rewash'},d.ver('rework_orders',f['order']))
    eq(pogl(f['po']),before);eq(poqty(f['po']),5);eq(A('select count(*) from erp.be_redye_services_v1',one=True),before_be)
    eq(A('select product_id::text from erp.fg_lots where id=(select good_fg_lot_id from erp.rework_orders where id=%s)',(f['order'],),one=True),C['redye_product'])
    return {'created':r,'completed':done,'unchanged_cost':before,'same_product':C['redye_product']}
def cancel_redye():
    start=start_redye('CANCEL');f=rsource('CANCEL');r=n.bs('SAVE_REWORK',{'id':f['order'],'action':'CANCEL','change_reason':'Independent cancellation before return'},d.ver('rework_orders',f['order']));eq(pogl(f['po']),D('12889.71'));eq(poqty(f['po']),0)
    return {'start':start,'cancelled':r,'cost_restored':'12889.71'}

def run():
    load()
    case('SETUP-MATERIALS','Own opening stock import and accessory policies',materials)
    case('CONV-05','Actual five-tag use capitalizes 115.85 once',usage)
    case('CONV-14.COST','Active accessory source prevents conversion inverse',usage_dependency)
    case('CONV-06-07','Three actual returns, two usable, one damaged; recovery reduces garment cost',recovery)
    case('SETUP-IDENTITIES','Independent exact source and new-color SKU identities',new_products,'Controlled master prerequisites')
    case('SETUP-REDYE','Nine real BS pieces per independent opening source, no fabricated sewing',redye_sources)
    case('REDYE-02-03-09','Known paid new-color service dispatch: custody, estimate and no invented invoice/FG',start_redye)
    case('REDYE-04','Partial 2 GOOD plus 1 BS records custody only',partial)
    for name,changes in [('OVER',{'qty_good':6,'qty_bs':2}),('DECREASE',{'qty_good':1,'qty_bs':6}),('BEFORE',{'completed_at':'2026-09-13T08:00:00+07:00'}),('LOCATION',{'return_fg_location_id':C['rawloc']})]:
        def probe(changes=changes):
            f=rsource('KNOWN');p={'rework_order_id':f['order'],'qty_good':5,'qty_bs':2,'completed_at':'2026-09-18T08:00:00+07:00','return_fg_location_id':C['fg'],'change_reason':'Independent invalid completion',**changes}
            return n.reject(lambda:n.bs('COMPLETE_REWORK',p,d.ver('rework_orders',f['order'])))
        case('REDYE-05-07-14.'+name,'Invalid completion '+name,probe)
    case('REDYE-05-06','Complete 5 new-color GOOD and 2 residual BS; all 9 pieces and cost conserved',complete)
    case('REDYE-08.REPLAY','Completion retry has exactly one physical effect',redye_replay)
    case('REDYE-11','Actual invoice replaces estimate and increases cost by 36.36 only',redye_invoice)
    case('REDYE-17','Future rate leaves posted original service unchanged',known_snapshot)
    case('REDYE-10.UNKNOWN-18','Unknown price resolved through actual BD router',unknown_price)
    case('REDYE-10.FREE','Explicit waived redye zero is distinct from unknown',redye_free)
    case('REDYE-01','Legacy free rewash keeps source identity and value',legacy)
    case('REDYE-16','Cancellation before completion restores cost and custody',cancel_redye)
    persist()
if __name__=='__main__':run()

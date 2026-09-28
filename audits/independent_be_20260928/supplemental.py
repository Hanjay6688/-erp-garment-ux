"""Own retest additions on a freshly restored BE database for each mode.
No writer business scenarios, oracle helpers, or product modifications are used.
"""
import sys,json,copy,psycopg
from psycopg.types.json import Jsonb
from decimal import Decimal as D
import native as n,flows as f,suite as s,daily as d,extended as e
C=n.C;A=n.A;eq=n.eq;uid=n.uid
MODE=sys.argv[1];s.DSN=s.DSN.replace('/cp6_rollback','/cp6_be_supp');s.OUT=s.OUT/'supplemental'/MODE;s.OUT.mkdir(parents=True,exist_ok=True)

def setup(redye=False):
    n.setup()
    if redye:f.new_products();f.redye_sources()
    else:f.materials()

def invoice_case(k,amount,discount='0.00'):
    f.start_redye(k);f.complete(k);r=f.rsource(k);base=f.pogl(r['po']);phy=f.physical_fingerprint()
    gross=D(amount);net=gross-D(discount)
    payload={'vendor_id':C['daily_vendor'],'invoice_number':'AUD-REV-BE-'+k,'invoice_date':'2026-09-19','header_total':str(net),'discount_amount':discount,'lines':[{'line_kind':'BILL','rework_service_id':r['service'],'category':'GOOD','qty':1,'amount':amount,'note':'Own one-piece large invoice boundary'}]}
    draft=s.command('SAVE_INVOICE_DRAFT',payload);eq(f.physical_fingerprint(),phy)
    req=uid();p={'invoice_id':draft['invoice_id'],'expected_version':str(draft['row_version'])};before=n.fp()
    try:post=s.command('POST_INVOICE',p,req)
    except Exception as error:eq(n.fp(),before);n.E.append({'one_line_invoice_atomic_refusal':str(error),'amount':amount,'discount':discount});raise
    eq(f.physical_fingerprint(),phy)
    lines=A('select net_amount,released_estimate,product_variance from erp.bd_laundry_invoice_lines_v1 where invoice_id=%s',(post['invoice_id'],));eq(lines,[(net,D('197.31'),net-D('197.31'))])
    ap=A("select coalesce(sum(credit-debit),0) from erp.journal_lines where journal_entry_id=%s and account_id=erp.account_id('AP_VENDOR')",(post['journal_id'],),one=True);eq(ap,net);eq(f.pogl(r['po']),base+net-D('197.31'))
    after=n.fp();replay=s.command('POST_INVOICE',p,req);eq(n.fp(),after);eq(replay['invoice_id'],post['invoice_id'])
    inverse=s.command('REVERSE_INVOICE',{'invoice_id':post['invoice_id'],'expected_version':str(post['row_version']),'reason':'Independent unpaid large-invoice inverse'})
    eq(f.pogl(r['po']),base);eq(f.physical_fingerprint(),phy)
    return {'peer_informed_origin':'BE peer invoice overflow, own different fixture and independent boundary arithmetic','gross':amount,'discount':discount,'net':str(net),'posted':post,'line_readback':lines,'ap':ap,'replay_one_effect':True,'inverse':inverse,'cost_restored':str(base),'physical_unchanged':True}

def large():
    setup(True);s.policy('LAU_DEC03',{'discount':'ALLOWED','extra':'ALLOWED','rounding':'LAST_LINE'})
    for k,a,dc in [('KNOWN','240.00','0.00'),('UNKNOWN','21474836.46','0.00'),('FREE','21474836.47','0.00'),('LEGACY','21474836.48','0.00'),('CANCEL','22000000.00','0.00'),('BAD','28123456.78','0.00'),('UI','28123456.78','1.23')]:
        n.case('REV.BE.INVOICE.'+k,'Real one-line redye invoice '+a+' discount '+dc,lambda k=k,a=a,dc=dc:invoice_case(k,a,dc))

def refused_pending_sale(mode,lot):
    before=n.fp();error=None;accepted=None
    payload={'sale_number':'AUD-PENDING-'+mode,'customer_id':C['customer'],'source_location_id':C['fg'],'sale_date':'2026-09-19T08:00:00+07:00','reason':'Independent pending refusal probe','items':[{'product_id':C['redye_target'],'qty_pcs':2,'unit_price_snapshot':'20000.00','discount_amount':'0.00'}]}
    with psycopg.connect(s.DSN) as c:
        try:
            c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],))
            made=c.execute('select erp.save_sale_draft_v2(%s,%s::uuid,null)',(Jsonb(payload),uid())).fetchone()[0]
            accepted=c.execute('select erp.post_sale(%s)',(made['sale_id'],)).fetchone()[0]
        except psycopg.Error as ex:error={'sqlstate':ex.sqlstate,'message':str(ex)}
        finally:c.rollback()
    eq(n.fp(),before)
    n.E.append({'pending_policy':mode,'sale_payload':payload,'refusal':error,'accepted_if_bug':accepted,'transaction_rolled_back_for_case_isolation':True})
    assert error and error['sqlstate']=='P0001' and 'BD_SALE_LAUNDRY_PRICE_UNKNOWN' in error['message'],{'expected':'policy refusal of actual unknown-redye sale','error':error,'accepted':accepted}
    return {'policy':mode,'error':error,'unchanged':True,'native_sales_layer':'real native save and post in one outer transaction, not HTTP authorization proof'}

def pending():
    setup(True);f.start_redye('UNKNOWN',True);f.complete('UNKNOWN');r=f.rsource('UNKNOWN');lot=r['targetlot']
    def preview():return n.rpc('erp_accounting_close_preflight_v1',['2026-09-21'])
    def own_blockers(p):return [x for x in p['blockers'] if x.get('reference',{}).get('rework_service_id')==r['service']]
    before=preview();assert any(x['code']=='BE_REDYE_PRICE_UNKNOWN' for x in own_blockers(before)),before
    n.case('REV.PENDING.CLOSE','Real unknown service appears in close preflight and close refuses',lambda:{'own_blockers':own_blockers(before),'close_refusal':n.reject(lambda:n.rpc('erp_close_accounting_through_v1',['2026-09-21','Independent unknown-price close refusal']))})
    for mode in ['UNSET','REFUSE']:
        ver=A("select version from erp.bd_policy_settings_v1 where policy_key='LAU_DEC04'",one=True)
        p={'policy_key':'LAU_DEC04','operation':'CLEAR' if mode=='UNSET' else 'SET','expected_version':str(ver),'reason':'Independent synthetic pending sale decision '+mode}
        if mode=='REFUSE':p['value']={'sale_with_unknown_laundry':'REFUSE'}
        s.command('SET_POLICY',p)
        n.case('REV.PENDING.'+mode,'Unknown-price sale refuses under '+mode,lambda mode=mode:refused_pending_sale(mode,lot))
    s.policy('LAU_DEC04',{'sale_with_unknown_laundry':'ALLOW_PENDING'})
    sl=e.sale(C['redye_target'],C['fg'],lot,'ALLOW',qty=3,at='2026-09-19T08:00:00+07:00');eq(n.lotqty(lot),2)
    markers=A('select to_jsonb(t) from erp.bd_pending_price_sales_v1 t where sale_id=%s',(sl['sale_id'],))
    def verify_allowed():
        assert markers,{'pending_sale_missing_marker':sl}
        blockers=own_blockers(preview());assert blockers
        return {'sale':sl,'markers':markers,'remaining_qty':n.lotqty(lot),'own_blockers_still_present':blockers}
    n.case('REV.PENDING.ALLOW','Allowed pending sale consumes three real PCS and carries pending marker',verify_allowed)
    ret=e.returned(sl,'PENDING',at='2026-09-20T08:00:00+07:00');eq(n.lotqty(lot),3)
    historical=e.report('2026-09-18')['financial_position'];phy=f.physical_fingerprint();base=f.pogl(r['po']);posted=A("select j.id::text,j.transaction_date,j.economic_date,(select jsonb_agg(to_jsonb(l) order by l.id) from erp.journal_lines l where l.journal_entry_id=j.id) from erp.journal_entries j where j.status in('POSTED','REVERSED') order by j.id")
    # No expectation of deleting audit markers: readiness must consult resolved price.
    result=n.cmd('SET_REDYE_PRICE',{'service_id':r['service'],'rate':'197.31','reason':'Independent pending service resolution after sale and return'})
    eq(f.physical_fingerprint(),phy);eq(f.pogl(r['po']),base+D('1381.17'));eq(own_blockers(preview()),[])
    after=A('select j.id::text,j.transaction_date,j.economic_date,(select jsonb_agg(to_jsonb(l) order by l.id) from erp.journal_lines l where l.journal_entry_id=j.id) from erp.journal_entries j where j.id=any(%s::uuid[]) order by j.id',([x[0] for x in posted],));eq(after,posted)
    n.case('REV.PENDING.RESOLVE','Pricing after sale and return clears own blocker without changing physical or old journal amounts',lambda:{'resolution':result,'return':ret,'cost_increment':'1381.17','own_close_blockers':[],'old_journal_amounts_preserved':len(posted),'current_hpp':n.lotcost(lot),'prior_report_snapshot':historical})

def recovery(po=False,usage=False):
    setup(False)
    if po:
        prod=d.precursor('SUP_REC');p=d.dp('SUP_REC');p['pricing']['components']=[{'component_id':C['daily_wash'],'covered_qty':13}]
        sent=s.command('POST_PRICED_DELIVERY',p);prod.update(delivery=sent['delivery_id'],delivery_line=A('select id::text from erp.laundry_delivery_lines where delivery_id=%s',(sent['delivery_id'],),one=True))
        got=d.rpc('POST_RECEIPT',d.rp('SUP_REC',at='2026-09-16T08:00:00+07:00'),d.ver('laundry_deliveries',prod['delivery']));prod.update(receipt=got['receipt_id'],receipt_line=A('select id::text from erp.laundry_receipt_lines where receipt_id=%s',(got['receipt_id'],),one=True))
        qp=d.qp('SUP_REC');qp['physical_at']='2026-09-17T08:00:00+07:00';d.rpc('POST_FINAL_SKU',qp,d.ver('cutting_groups',prod['group']))
        src=A('select id::text from erp.fg_lots where po_id=%s and product_id=%s',(prod['po'],C['product']),one=True);base=D('22105.45')
    else:src=n.F['RETURNS']['lot'];base=D('6172.85')
    row=n.ws({'source_lot_id':src})['lots'][0];cv=n.cmd('POST',{'source_lot_id':src,'target_product_id':C['target'],'location_id':C['fg'],'qty_pcs':5,'physical_at':'2026-09-19T08:00:00+07:00','expected_version':row['source_revision'],'expected_returns':[{'material_id':C['tag'],'qty':'5','holder':'Independent actual dismantling'}],'reason':'Independent recovery matrix '+MODE});lot=cv['destination_lot_id'];eq(n.value(lot),base)
    if usage:
        n.cmd('POST_USAGE',{'conversion_id':cv['conversion_id'],'expected_version':f.conversion_doc(cv['conversion_id'])['revision'],'location_id':C['rawloc'],'physical_at':'2026-09-19T09:00:00+07:00','items':[{'material_id':C['tag'],'qty':'5'}],'reason':'Independent five new tags actually attached'});base+=D('115.85');eq(n.value(lot),base)
    outstanding=f.conversion_doc(cv['conversion_id'])['returns'][0]['id'];rec=f.bc('RECEIVE_RETURN',{'source_kind':'TEARDOWN','location_id':C['inspection'],'physical_at':'2026-09-20T08:00:00+07:00','items':[{'material_id':C['tag'],'qty':'3','outstanding_id':outstanding}],'reference':MODE,'reason':'Independent three of five actually returned'})
    custody=rec['lot_ids'][0];f.bc('INSPECT',{'lot_id':custody,'inspected_at':'2026-09-20T09:00:00+07:00','inspector':'Independent auditor','qty_usable':'2','qty_damaged':'1','reason':'Two usable one damaged'});f.bp('ACC_DEC03',{'credit_account_id':f.X['expense'],'unit_value_cap':'NONE'})
    stock=f.matqty(C['tag']);phy=f.physical_fingerprint();state=n.fp();payload={'lot_id':custody,'condition':'USABLE','qty':'2','unit_value':'7.13','location_id':C['rawloc'],'physical_at':'2026-09-21T08:00:00+07:00','reason':'Independent actual two usable items recovered at7.13'}
    n.E.append({'recovery_oracle':{'po':po,'usage':usage,'before_value':str(base),'expected_value':str(base-D('14.26')),'expected_stock_added':2,'conversion':cv,'payload':payload}})
    try:val=f.bc('VALUE_CUSTODY',payload)
    except Exception as error:eq(n.fp(),state);n.E.append({'refusal_atomic':True,'error':str(error)});raise
    eq(f.matqty(C['tag']),stock+2);eq(n.value(lot),base-D('14.26'));eq(f.physical_fingerprint(),phy)
    refusals=[]
    if not usage:
        rows=A('select c.id::text,to_jsonb(c) from erp.hpp_version_components c join erp.hpp_versions h on h.id=c.hpp_version_id where h.lot_id=%s and h.is_current and c.unit_cost<0',(lot,));eq(len(rows),1)
        for label,change in [('wrong source','source_id=gen_random_uuid()'),('forged credit','total_cost=total_cost-1'),('negative ordinary cost',"component_type='LABOR'")]:
            error=None
            with psycopg.connect(s.DSN) as c:
                try:
                    c.execute("select set_config('app.change_reason','Independent negative cost integrity probe',true)")
                    c.execute('update erp.hpp_version_components set '+change+' where id=%s',(rows[0][0],))
                except psycopg.Error as ex:error={'sqlstate':ex.sqlstate,'message':str(ex)}
                finally:c.rollback()
            assert error and 'BE_SIGNED_HPP_REQUIRES_SOURCED_RECOVERY' in error['message'],(label,error)
            refusals.append({'probe':label,'refusal':error})
        eq(A('select to_jsonb(c) from erp.hpp_version_components c where c.id=%s',(rows[0][0],),one=True),rows[0][1])
    return {'po':po,'new_usage':usage,'valuation':val,'expected_and_actual_target_value':str(base-D('14.26')),'stock_added':2,'garment_qty_unchanged':True,'signed_cost_tampering_refused':refusals}

if __name__=='__main__':
    if MODE=='large':large()
    elif MODE=='cross-races':
        import cross_races;cross_races.run()
    elif MODE=='pending':n.case('REV.PENDING.MATRIX','All three configured pending-sale choices plus close and resolution',pending)
    else:n.case('REV.RECOVERY.'+MODE,'Actual usable recovery with '+MODE,lambda:recovery('nonpo' not in MODE,MODE.endswith('usage')))
    n.save()

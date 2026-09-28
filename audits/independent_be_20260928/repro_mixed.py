"""Small independent mixed PO/non-PO reproduction on a fresh exact BE database."""
import native as n,flows as f,suite as s,daily as d,extended as e
from decimal import Decimal as D
import json
s.DSN=s.DSN.replace('/cp6_rollback','/cp6_be_repro');s.OUT=s.OUT/'mixed-root-repro';s.OUT.mkdir(exist_ok=True)
C=n.C;A=n.A;eq=n.eq;uid=n.uid;X={}
def nonpo():
    s.setup();d.setup();C.update(product=C['products'][C['s1']+':'+C['brand']],target=C['products'][C['s1']+':'+C['brand2']])
    receipt=n.rpc('erp_post_fg_unsourced_receipt_v1',[{'source_kind':'FOUND_AT_OPNAME','product_id':C['product'],'location_id':C['fg'],'qty_pcs':13,'physical_at':'2026-09-13T08:00:00+07:00','reason':'Independent clean mixed-root source','owner_unit_value':'1234.57','owner_value_reason':'No prior production comparator in this separate database'},uid()]);X['source']=receipt['lot_id'];row=n.ws({'source_lot_id':X['source']})['lots'][0]
    payload={'source_lot_id':X['source'],'target_product_id':C['target'],'location_id':C['fg'],'qty_pcs':5,'physical_at':'2026-09-15T08:00:00+07:00','reason':'Independent clean non-PO positive control','expected_version':row['source_revision']};r=n.cmd('POST',payload);eq(n.lotqty(X['source']),8);eq(n.value(r['destination_lot_id']),D('6172.85'));X['positive']=r;return {'receipt':receipt,'conversion':r,'target_value':'6172.85'}
def po():
    prod=d.precursor('MIXED');X['po']=prod['po'];sent_payload=d.dp('MIXED');sent_payload['pricing']['components']=[{'component_id':C['daily_wash'],'covered_qty':13}];sent=s.command('POST_PRICED_DELIVERY',sent_payload);prod['delivery']=sent['delivery_id'];prod['delivery_line']=A('select id::text from erp.laundry_delivery_lines where delivery_id=%s',(sent['delivery_id'],),one=True)
    got=d.rpc('POST_RECEIPT',d.rp('MIXED',at='2026-09-17T08:00:00+07:00'),d.ver('laundry_deliveries',prod['delivery']));prod['receipt']=got['receipt_id'];prod['receipt_line']=A('select id::text from erp.laundry_receipt_lines where receipt_id=%s',(got['receipt_id'],),one=True)
    q=d.qp('MIXED');q['physical_at']='2026-09-18T08:00:00+07:00';qc=d.rpc('POST_FINAL_SKU',q,d.ver('cutting_groups',prod['group']));eq(f.pogl(prod['po']),D('57474.17'))
    source=A('select id::text from erp.fg_lots where po_id=%s and product_id=%s',(prod['po'],C['product']),one=True);row=n.ws({'source_lot_id':source})['lots'][0];r=n.cmd('POST',{'source_lot_id':source,'target_product_id':C['target'],'location_id':C['fg'],'qty_pcs':3,'physical_at':'2026-09-19T08:00:00+07:00','reason':'Independent only PO-backed conversion','expected_version':row['source_revision']});eq(n.lotqty(source),4);eq(n.lotqty(r['destination_lot_id']),3);eq(n.value(r['destination_lot_id']),D('13263.27'));eq(f.pogl(prod['po']),D('57474.17'));X['po_conversion']=r
    return {'native_boundary':'Only cut and pickup seeded; native work, sewing, laundry, receipt, QC and public conversion','qc':qc,'conversion':r,'po_conversion_value':'13263.27','po_total':'57474.17'}
def unrelated():
    before=n.fp();row=n.ws({'source_lot_id':X['source']})['lots'][0];payload={'source_lot_id':X['source'],'target_product_id':C['target'],'location_id':C['fg'],'qty_pcs':1,'physical_at':'2026-09-20T08:00:00+07:00','reason':'Independent next unrelated non-PO conversion','expected_version':row['source_revision']}
    n.E.append({'clean_expected':'Unrelated one-piece conversion moves1234.57 once; existing PO conversion must not block it','payload':payload,'two_previous_conversions':X})
    try:r=n.cmd('POST',payload)
    except Exception as error:
        eq(n.fp(),before);n.E.append({'clean_refusal_left_state_unchanged':True,'error':str(error)});raise
    eq(n.lotqty(X['source']),7);return r
def run():
    n.case('MIXED.CONTROL-NONPO','One real non-PO conversion works in fresh candidate',nonpo)
    n.case('MIXED.CONTROL-PO','One native PO source converted with exact13263.27 value',po)
    n.case('MIXED.NEXT-NONPO','Next unrelated non-PO conversion remains available',unrelated)
    n.save()
if __name__=='__main__':run()

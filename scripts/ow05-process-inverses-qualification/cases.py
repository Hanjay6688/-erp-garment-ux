"""Two bounded normal-process inverses on the qualified unchanged OW05 product."""
from decimal import Decimal as D
import json
import uuid

from cp7_contractor_correction import native_cases as n

IDS=('OW05_LAUNDRY_RECEIPT_DELIVERY_AND_SEWING_INVERSES',
     'OW05_FINISHED_PO_QC_VOIDED_FG_AND_LAUNDRY_INVERSES')
REASON='OW05 mandor salah, balik dokumen asal berurutan'

def native(cur,sql,args):return n.old.s.native(cur,sql,args)

def prepared(cur,today,finished):
    g=n.fixture(cur,today,False)
    extra=n.old.sewing_command(cur,n.old.sewing_workspace(cur,g),qty=6,at=g['at'](10,30))
    g['events']=[g['terminal'],extra['result']['sewing_event_id']]
    g['works']=[g['completion'],extra['result']['work_completion_id']]
    assert n.balance(cur,g['po'],'WIP')==g['base_wip']+D('40.00')
    wash=dict(n.old.laundry_for(cur,g),po=g['po'])
    delivery=n.old.bd.post_priced(cur,wash,{},qty=10,hour=12)['delivery_id']
    receipt=n.old.bd.receive(cur,delivery,wash,10,13)['receipt_id'];n.auth.b.api.admin(cur)
    g.update(delivery=delivery,receipt=receipt)
    if finished:
        _,g['lot']=n.old.bd.finish_goods(cur,wash,receipt,10,14);n.auth.b.api.admin(cur)
        g['qc']=n.one(cur,'select qi.inspection_id::text from erp.fg_lots l join erp.qc_inspection_items qi on qi.id=l.qc_item_id where l.id=%s',(g['lot'],))
        w=n.old.finish_workspace(cur,g['po']);assert w['eligible'],w
        n.old.finish_command(cur,w)
        assert n.one(cur,'select status from erp.production_orders where id=%s',(g['po'],))=='FINISHED'
    return g

def frozen_work(cur,g):
    return dict(work=cur.execute('select to_jsonb(w)from erp.work_completion_events w where id=any(%s::uuid[])order by id',(g['works'],)).fetchall(),
        lines=cur.execute('select to_jsonb(l)from erp.work_completion_lines l where completion_id=any(%s::uuid[])order by id',(g['works'],)).fetchall())

def refused(cur,g,kind):
    w=n.workspace(cur,g['po']);assert not w['eligible']and kind in{x['kind']for x in w['blockers']},w
    before=n.auth.b.boundary.snapshot(cur)
    n.auth.refused(cur,lambda:n.command(cur,n.payload(w,g['target'])),'CP7_MANDOR_CORRECTION_DEPENDENCIES')
    assert n.auth.b.boundary.snapshot(cur)==before
    return [b['kind']for b in w['blockers']]

def journey(cur,today,finished):
    g=prepared(cur,today,finished);initial=refused(cur,g,'PO_STATE'if finished else'LAUNDRY')
    if finished:
        assert {'QC','FG_LOT','LAUNDRY'}<=set(initial)
        # Native requires reopening before QC reversal. The workspace's
        # PO_STATE-first instruction agrees with that actual business rule.
        n.auth.refused(cur,lambda:native(cur,'select erp.reverse_qc(%s,%s)',(g['qc'],REASON)),'FINISHED')
        native(cur,'select erp.reopen_production_order(%s,%s)',(g['po'],REASON))
        native(cur,'select erp.reverse_qc(%s,%s)',(g['qc'],REASON))
        assert n.one(cur,'select lot_origin from erp.fg_lots where id=%s',(g['lot'],))=='VOIDED_PRODUCTION'
        assert n.one(cur,'select coalesce(sum(qty_signed),0)from erp.fg_stock_movements where lot_id=%s',(g['lot'],))==0
    # An active receipt keeps its delivery locked. Both exact originals and
    # their append-only Native WIP reversals must survive this process.
    native(cur,'select erp.reverse_laundry_receipt(%s,%s)',(g['receipt'],REASON))
    refused(cur,g,'LAUNDRY')
    native(cur,'select erp.reverse_laundry_delivery(%s,%s)',(g['delivery'],REASON))
    assert n.one(cur,'select status from erp.cutting_groups where id=%s',(g['group'],))=='PICKED_UP'
    assert n.one(cur,'select cp7_contractor_correction.wip_closed_v1(%s)',(g['po'],))is True
    for event in g['events']:n.old.sewing_command(cur,n.old.sewing_workspace(cur,g),event=event)
    assert n.balance(cur,g['po'],'WIP')==g['base_wip']
    assert n.balance(cur,g['po'],'CONTRACTOR_PAYABLE',g['mandor'])==0
    old=frozen_work(cur,g);before=n.one(cur,'select cp7_contractor_correction.financial_fingerprint_v1(%s)',(g['po'],))
    n.correct(cur,g)
    assert n.one(cur,'select cp7_contractor_correction.financial_fingerprint_v1(%s)',(g['po'],))==before
    for qty,minute in((4,0),(6,30)):
        w=n.old.sewing_workspace(cur,g)
        p=dict(action='RECORD',group_id=g['group'],qty_pcs=str(qty),physical_at=g['at'](10,minute).isoformat(),
            review_token=w['review_token'],change_reason=REASON,rate_choice='NEW')
        n.auth.actor(cur)
        result=n.one(cur,'select public.erp_cp7_save_sewing_completion_v1(%s,%s,%s)',(json.dumps(p),str(uuid.uuid4()),w['group_version']))
        n.auth.b.api.admin(cur);assert D(str(result['result']['wage_amount']))==D(qty)*6
    assert n.balance(cur,g['po'],'WIP')==g['base_wip']+D('60.00')
    assert n.balance(cur,g['po'],'CONTRACTOR_PAYABLE',g['mandor'])==0
    assert n.balance(cur,g['po'],'CONTRACTOR_PAYABLE',g['target'])==D('-60.00')
    assert frozen_work(cur,g)==old
    assert n.one(cur,'select count(*)from cp7_contractor_correction.history_v1 where po_id=%s',(g['po'],))==1
    return dict(status='PASS',initial_named_blockers=initial,finished_PO_reopened_first=finished,
        old_FG_voided_and_stock_zero=finished,original_laundry_and_exact_WIP_inverses_retained=True,
        incomplete_inverse_refused_atomically=True,original_work_history_unchanged=True,
        original_sewing_times_and_quantities=[dict(qty=4,hour=10,minute=0),dict(qty=6,hour=10,minute=30)],
        old_payable='0.00',new_payable='60.00',WIP_increment='60.00',one_correction=True,production_go=False)

def cases(cur,today):return [(IDS[0],lambda:journey(cur,today,False)),(IDS[1],lambda:journey(cur,today,True))]

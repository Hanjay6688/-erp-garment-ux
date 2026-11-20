"""Actual issue, read and inverse on two ERP sessions. All business changes use ordinary public ERP functions."""
from common import *
from overlap import observe
import cp7_master_cases as master
from pathlib import Path
from decimal import Decimal as D
from time import perf_counter_ns
from zoneinfo import ZoneInfo
import sys,traceback
from cp7_accessory_standard_report import cases as acc
capture=dict(transactions=[],rounds={})
def store_case():save('AUD-G02',capture)
def wib(t):
    return t.astimezone(ZoneInfo('Asia/Jakarta')).isoformat(timespec='seconds')
def issue_payload(q,f):
    a=f['accessory'];p=acc.issues.payload(a)
    p.update(number='S05-Astra-'+uuid.uuid4().hex[:12],contractor_id=f['contractor'],location_id=a['main'],
             po_id=f['po'],physical_at=wib(first(q,'select statement_timestamp()')),reason='Empat aksesori untuk PO terpilih, diperiksa sesuai nota mandor')
    p['items'][0].update(qty='4',material_id=a['material'])
    return p
def fixture_current_day(q):
    f=acc.physical.fixture(q,TODAY,finish=False);admin(q)
    f['contractor']=str(first(q,'select contractor_id from erp.production_orders where id=%s',f['po']))
    f['accessory']=acc.issues.receipt(q,TODAY,qty='30');a=f['accessory'];f['day']=TODAY
    published=first(q,"select statement_timestamp()-interval '90 seconds'")
    setting=dict(price=None,bom=[dict(category_id=a['category'],qty_per_good_fg_base='0.5',hpp_method='BOM_STANDARD',hpp_standard_rate='2',hpp_uom_code=a['pcs'],reimbursement_rate='2',reimbursement_uom_code=a['pcs'])],work_rates=[],laundry_rates=[])
    group=acc.master.group(q,[f['product']],published,settings=setting)
    acc.master.save(q,[group],published);admin(q)
    f['note']=acc.issue_note(q,f,at=wib(first(q,"select statement_timestamp()-interval '45 seconds'")))
    at=first(q,"select statement_timestamp()-interval '10 seconds'")
    op=dict(cutting_group_id=f['group'],destination_location_id=acc.physical.base.LOCATION,physical_at=wib(at),
      reason='QC barang baik dan BS untuk laporan aksesori',good_qty_pcs=15,completion_mode='PARTIAL_SELECTION',
      lines=[dict(final_product_id=f['product'],qty_good_pcs=15,qty_bs_pcs=5,source_laundry_receipt_line_id=f['receipt_line'],source_laundry_receipt_batch_size_line_id=f['receipt_size'])])
    response=acc.b.chain.laundry_action(q,'POST_FINAL_SKU',op,acc.physical.base.group_version(q,f['group']))
    admin(q);f['qc']=response['qc_inspection_id']
    f['lot']=str(first(q,'select l.id from erp.fg_lots l join erp.qc_inspection_items i on i.id=l.qc_item_id where i.inspection_id=%s',f['qc']))
    return f
def inspect(q,f,actor,qty,known):
    trace=[];t=perf_counter_ns();report=acc.read(q,f,trace,subject=actor);elapsed=(perf_counter_ns()-t)/1e6
    line=acc.category(report,f);a=f['accessory']
    stock=acc.issues.bc.stock(q,a['material'],a['main'])
    assert D(line['actual_qty'])==qty and D(line['standard_qty'])==D('7.5') and D(line['delta_qty'])==qty-D('7.5')
    assert D(line['actual_inventory_cost'])==2*qty and D(line['actual_receivable'])==D('3.25')*qty
    assert D(line['standard_hpp_cost'])==D(line['standard_reimbursement'])==15 and D(stock)==30-qty
    ids=sorted(i['issue_id']for i in report['actual_sources'] if i['category_id']==a['category'])
    assert ids==sorted(known)
    assert all(s['po_id']==f['po']for s in report['actual_sources'])
    return dict(report_ms=round(elapsed,3),qty=str(qty),actual_receivable=line['actual_receivable'],actual_cost=line['actual_inventory_cost'],
       inventory_now=str(stock),standard_qty=line['standard_qty'],standard_reimbursement=line['standard_reimbursement'],
       source_ids=ids,report=trace[0]['actual'])
def main():
    params=db()
    if params:
        with connection(params,capture,'install actual candidate, post receipt, issue and QC')as q:
            capture['seal']=measure_seal(q);owner,writer=actors(q)
            f=fixture_current_day(q)
            first_id=str(f['note']['id'])
            capture['facts']={k:str(f[k])for k in ('po','day','contractor','qc','lot')}
            capture['actors']=[str(owner),str(writer)];capture['fixture_material']=f['accessory']['material']
        for outcome in ['ABORT','COMMIT']:
            row={};capture['rounds'][outcome]=row
            with connection(params,capture,outcome+' initial solo reader')as q:row['before']=inspect(q,f,owner,D(7),[first_id])
            key=uuid.uuid4()
            with psycopg.connect(**params) as w,w.cursor()as q:
                pid=first(q,'select pg_backend_pid()');p=issue_payload(q,f)
                note=acc.issues.bc.note_call(q,'POST',p,key,writer)
                assert note['status']=='POSTED';row['note']=note;row['writer_pid']=pid
                with connection(params,capture,outcome+' second session reads before terminal')as rd:
                    row['reader_pid']=first(rd,'select pg_backend_pid()');row['during']=inspect(rd,f,owner,D(7),[first_id])
                    assert row['reader_pid']!=pid
                calls=[('accessory-po','public.erp_cp7_get_accessory_standard_report_v1(%s,%s,%s,%s,%s,%s,%s)',(f['day'],f['day'],f['contractor'],f['po'],'',0,30),lambda r:{k:acc.category(r,f)[k] for k in ('actual_qty','actual_inventory_cost','actual_receivable','standard_hpp_cost')})]
                row['in_flight']=observe(w,owner,calls,outcome=='COMMIT')
                for sample in row['in_flight']['reads']:
                    values=sample['value'];qty=D(values['actual_qty'])
                    assert qty in (7,11) and D(values['actual_receivable'])==qty*D('3.25') and D(values['actual_inventory_cost'])==qty*2 and D(values['standard_hpp_cost'])==15
                store_case()
            with connection(params,capture,outcome+' fresh reader')as rd:
                if outcome=='ABORT':row['after']=inspect(rd,f,owner,D(7),[first_id])
                else:row['after']=inspect(rd,f,owner,D(11),[first_id,str(note['id'])])
            if outcome=='COMMIT':
                with connection(params,capture,'same request after commit')as q:
                    again=acc.issues.bc.note_call(q,'POST',p,key,writer)
                    assert again['id']==note['id'];row['replay_id']=again['id']
        with connection(params,capture,'ordinary reversal of additional issue')as q:
            reversal=acc.issues.bc.note_call(q,'REVERSE',dict(id=note['id'],expected_version=note['row_version'],reason='Kembalikan empat unit dalam uji barang pada PO yang sama'),auth=writer)
            capture['reversal']=reversal
        with connection(params,capture,'fresh report after reversal')as q:
            capture['after_reversal']=inspect(q,f,owner,D(7),[first_id])
            doc=acc.issues.bc.note_read(q,dict(id=note['id']),writer)['document']
            assert doc['status']=='REVERSED'
            capture['retained_document_after_inverse']={'id':doc['id'],'status':doc['status']}
    capture['outcome']='PASS';store_case()

if __name__=='__main__':
    try:main()
    except Exception as err:
        store_case();record_failure('AUD-G02',err);raise

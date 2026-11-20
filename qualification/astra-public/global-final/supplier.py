"""Observe the real create, history, correction and journal readers across committed and aborted corrections."""
from common import *
import cp7_master_cases as master
from overlap import observe
from decimal import Decimal
import cp7_supplier_payment_cases as supplier
import cp7_supplier_payment_create_cases as create
import cp7_supplier_payment_correction_cases as correct

report=dict(transactions=[],rounds={})
def read_state(q,f,owner,bank_search):
    purchase=f['receipt']['purchase_id']
    common=dict(bank_q=bank_search,bank_offset=0)
    new=create.read(q,f,owner,**common)
    edit=correct.workspace(q,f,f['target'],owner,**common)
    first_page=supplier.read(q,f,subject=owner)
    last=supplier.read(q,f,25,subject=owner)
    focus=supplier.read(q,f,payment=f['target'],subject=owner)
    ap=[x['Native_AP'] for x in [new,first_page,last,focus]]
    assert all(v==ap[0] for v in ap)
    for data in [new,edit]:
        assert [v['id'] for v in data['cash_accounts']['rows']]==[f['cash']],data['cash_accounts']
    pages=first_page['page']['rows']+last['page']['rows']
    assert len(pages)==int(first_page['page']['total'])==len({v['id']for v in pages})
    assert len(first_page['page']['rows'])==25 and focus['selected_payment_id']==f['target']
    selected=next(v for v in focus['page']['rows'] if v['id']==f['target'])
    orig=edit['document']
    assert selected['journal']['id']==orig['journal']['id']==f['journal']
    assert orig['status']==selected['status']
    cash=create.misc.cash_balance(q,f['cash'])-Decimal(f['cash_before'])
    assert cash==-Decimal(ap[0]['paid']) and Decimal(ap[0]['paid'])+Decimal(ap[0]['remaining'])==1000
    assert f['physical']==supplier.physical_state(q)
    return dict(purchase=purchase,AP=ap[0],cash_delta=str(cash),
        selectors=[x['cash_accounts']for x in [new,edit]],history_pages=[[v['id']for v in a['page']['rows']]for a in [first_page,last]],
        selected_id=focus['selected_payment_id'],selected_page=focus['page']['offset'],original_status=orig['status'],
        original_journal=orig['journal']['id'],inverse=(orig.get('inverse')or{}).get('id'),
        replacement=((edit.get('next')or{}).get('document')or{}).get('id'),all_stock_and_cost_same=True)

def main():
    params=db()
    if params:
        with connection(params,report,'install; prepare 26 real posted supplier payments')as q:
            report['seal']=measure_seal(q);owner,other=actors(q)
            f=supplier.fixture(q,TODAY,26);f['payment']=f['target']
            offset=0
            while True:
                page=create.read(q,f,owner,bank_offset=offset)['cash_accounts']
                account=next((x for x in page['rows'] if x['id']==f['cash']),None)
                if account:break
                offset=page['next_offset']
                assert offset is not None
            bank_search=account['code']
            report['purchase']=f['receipt']['purchase_id'];report['payment']=f['target'];report['actors']=[owner,other]
        for outcome in ['ABORT','COMMIT']:
            row={};report['rounds'][outcome]=row
            with connection(params,report,outcome+' first reader')as q:row['before']=read_state(q,f,owner,bank_search)
            assert row['before']['AP']['paid']=='260.00' and row['before']['AP']['remaining']=='740.00'
            with psycopg.connect(**params)as separate,separate.cursor()as w:
                row['writer_pid']=first(w,'select pg_backend_pid()')
                request=correct.payload(w,f,'5.00',subject=other)
                result=correct.correct(w,request,subject=other)
                assert result['original_status']=='REVERSED' and result['status']=='POSTED'
                row['writer_result']=result
                with connection(params,report,outcome+' reader while correction held')as q:
                    row['reader_pid']=first(q,'select pg_backend_pid()');row['during']=read_state(q,f,owner,bank_search)
                assert row['reader_pid']!=row['writer_pid'] and row['during']==row['before']
                calls=[
                    ('supplier-history','public.erp_cp7_get_supplier_payments_v1(%s,%s,%s,%s)',(f['receipt']['purchase_id'],'',0,f['target']),lambda v:dict(paid=v['Native_AP']['paid'],remaining=v['Native_AP']['remaining'],focus=v['selected_payment_id'],ids=[t['id'] for t in v['page']['rows']],total=v['page']['total'])),
                    ('supplier-edit','public.erp_cp7_get_supplier_payment_correction_v1(%s::jsonb)',(json.dumps({'purchase_id':f['receipt']['purchase_id'],'payment_id':f['target'],'bank_q':bank_search,'bank_offset':0}),),lambda v:dict(status=v['document']['status'],journal=v['document']['journal']['id'],banks=[t['id'] for t in v['cash_accounts']['rows']])),
                    ('supplier-create','public.erp_cp7_get_supplier_payment_create_v1(%s::jsonb)',(json.dumps({'purchase_id':f['receipt']['purchase_id'],'bank_q':bank_search,'bank_offset':0}),),lambda v:dict(paid=v['Native_AP']['paid'],remaining=v['Native_AP']['remaining'],banks=[t['id'] for t in v['cash_accounts']['rows']]))]
                row['in_flight']=observe(separate,owner,calls,outcome=='COMMIT')
                for sample in row['in_flight']['reads']:
                    val=sample['value']
                    if sample['kind']=='supplier-edit':
                        assert val['status'] in ('POSTED','REVERSED') and val['journal']==f['journal'] and val['banks']==[f['cash']]
                        continue
                    assert (val['paid'],val['remaining']) in [('260.00','740.00'),('255.00','745.00')],val
                    if sample['kind']=='supplier-create':assert val['banks']==[f['cash']],val
                    else:assert val['focus']==f['target'] and int(val['total']) in (26,27),val
                save('AUD-G01',report)
            with connection(params,report,outcome+' independent reader after boundary')as q:row['after']=read_state(q,f,owner,bank_search)
            if outcome=='ABORT':assert row['after']==row['before']
            else:
                after=row['after']
                assert after['AP']['paid']=='255.00' and after['AP']['remaining']=='745.00' and after['original_status']=='REVERSED'
                assert after['replacement']==result['payment_id'] and after['inverse'] and sum(map(len,after['history_pages']))==27
    report['outcome']='PASS';save('AUD-G01',report)

if __name__=='__main__':
    try:main()
    except Exception as err:
        save('AUD-G01',report);record_failure('AUD-G01',err);raise

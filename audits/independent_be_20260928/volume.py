"""Real period history above UI limit, before independent mixed-root stress."""
import native as n,flows as f,pocket as p,edges as e
from decimal import Decimal as D
C=n.C;X=f.X;A=n.A;eq=n.eq
def empty_period():
    q=p.preview('2026-09-11','2026-09-11');eq(q['can_post'],False);eq(D(q['amount']),D(0));eq(D(q['quantity']),D(0));refused=n.reject(lambda:n.pocket('POST_PERIOD',{'period_start':q['period_start'],'period_end':q['period_end'],'expected_revision':q['revision'],'reason':'Independent empty period cannot invent a denominator'}),'memerlukan')
    return {'empty_preview':q,'post_refused':refused}
def capacity():
    imp=f.imported('SMALL-HISTORY',[
      ('OPENING_POCKET_USAGE',[{'document_number':'BE-AUD-SMALL-USE','line_number':'1','physical_date':'2026-09-02','material_sku':'BE-AUD-POCKET','qty':'1','amount':'1.03','allocation_status':'UNALLOCATED','control_key':'SMALL','control_qty':'1','control_amount':'1.03'}]),
      ('OPENING_POCKET_SEWING',[{'document_number':'BE-AUD-SMALL-SEW','line_number':'1','physical_date':'2026-09-03','contractor_code':'AUD-DAY','qty':'1','target_kind':'COGS','product_sku':'BE-AUD-POCKET-FG','sold_reference':'Independent one-piece historical sold garment','control_key':'ONE','control_qty':'1'}])])
    q=p.preview();old=n.pocket('POST_PERIOD',{'period_start':q['period_start'],'period_end':q['period_end'],'expected_revision':q['revision'],'reason':'Independent oldest active period must remain operable'})
    X['capacity']={'old':old,'cycles':[],'import':imp};f.persist()
    for i in range(51):
        q=p.preview('2026-09-01','2026-09-04');eq(D(q['amount']),D('1.03'));eq(D(q['quantity']),D(1))
        made=n.pocket('POST_PERIOD',{'period_start':q['period_start'],'period_end':q['period_end'],'expected_revision':q['revision'],'reason':'Independent real reallocation cycle '+str(i)})
        state=next(x for x in p.ws()['periods'] if x['id']==made['id']);n.pocket('CANCEL_PERIOD',{'id':made['id'],'expected_revision':state['revision'],'reason':'Independent real cycle inverse '+str(i)});X['capacity']['cycles'].append(made['id'])
    found={q:any(x['id']==old['id'] for x in p.ws(q)['periods']) for q in [old['id'],'2026-09-05']};state=A('select erp.pocket_period_state_v1(%s)',(old['id'],),one=True);eq(state['status'],'ACTIVE');X['capacity'].update(search_found=found,state=state);f.persist()
    n.E.append({'actual_oldest_active_period':state,'workspace_searches_found':found,'posted_periods':A('select count(*) from erp.pocket_periods',one=True),'returned':len(p.ws()['periods'])})
    assert all(found.values()),{'active_period':old['id'],'searches_found':found,'workspace_returned':len(p.ws()['periods']),'actual_active':state}
    ids=[];offset=0;pages=[]
    while True:
        page=n.rpc('erp_get_pocket_periods_v1',['',offset]);pages.append(page);ids.extend(x['id'] for x in page['periods'])
        if page['period_next_offset'] is None:break
        assert page['period_next_offset']>offset,page
        offset=page['period_next_offset']
    eq(len(ids),len(set(ids)));eq(len(ids),pages[0]['period_count']);assert old['id'] in ids
    X['capacity']['independent_pages']=pages;f.persist()
    return {'searches':found,'unique_count':len(ids),'page_count':len(pages),'old_active_reachable':True}
def run():
    f.load()
    f.case('POCKET-14.EMPTY','Empty source and sewing period cannot allocate or invent output',empty_period)
    f.case('NONPO-12.POCKET-RACE','Validated import waits for allocation then rechecks while unrelated import works',e.import_conflict)
    f.case('UI.POCKET.52','Old active allocation remains reachable after 51 real later cycles',capacity)
    f.case('POCKET-10.CLOSED','Closed allocation either refuses for the date or books in open day only',e.closed_pocket)
    f.persist()
if __name__=='__main__':run()

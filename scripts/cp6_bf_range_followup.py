"""Range follow-up: repeated drawing slots are not duplicate physical sizes.

An ordinary cut has size31 drawing1=2 and drawing2=3, size32=8, size33=3.
The SKU-reference public read must expose three sizes, and its natural UI payload
must bind once per size. The four physical cutting slots and all 16 PCS stay intact.
"""
import json,uuid
from datetime import timedelta
import cp6_bf_free_probe as free

bf,b,one=free.bf,free.b,free.one

def repeated_drawings(cur,today):
    f=free.master_fixture(cur);bf.save(cur,[f['g']],f['at'])
    prod=b.chain.production;sizes=[s for _,s in f['rows']]
    fabric=prod.estimated_receipt(cur,b.case_day(today));b.api.admin(cur)
    when=lambda hour:f['now']-timedelta(seconds=(19-hour)*10)
    po=str(uuid.uuid4())
    cur.execute("insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes) values(%s,%s,%s,16,'CUTTING','CUTTING',%s,'Range repeated drawings')",(po,'RANGE-SLOTS-'+po,prod.MODEL,when(7)))
    slots=[(1,sizes[0],1,2),(2,sizes[0],2,3),(3,sizes[1],1,8),(4,sizes[2],1,3)]
    payload=dict(action='SAVE_DRAFT',po_id=po,pattern_id=prod.PATTERN,source_location_id=fabric['location'],cut_at=when(8),change_reason='Two drawings of size31 in one wave',
        size_slots=[dict(slot_no=n,size_id=s,drawing_no=d) for n,s,d,_ in slots],
        rolls=[dict(roll_id=fabric['roll'],qty_issued=10,qty_consumed=10,qty_reported_remaining=0,yields=[dict(slot_no=n,qty_pcs=q) for n,_,_,q in slots])])
    draft=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',payload)
    wave=draft['cutting_group_id']
    prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(payload,id=wave,action='POST'),expected_version=int(draft['row_version']))
    prod.owner(cur)
    workspace=one(cur,'select public.erp_get_sku_workspace_v1(%s::jsonb)',json.dumps(dict(wave_id=wave,query=f['g']['sku'])))
    b.api.admin(cur);exposed=workspace['wave']['sizes']
    # This is the same mapping as SkuWaveReferences.save(), without deduplicating in the test.
    references=[dict(size_id=s['id'],sku_id=f['g']['id']) for s in exposed]
    key=str(uuid.uuid4());request=dict(cutting_group_id=wave,expected_version=workspace['wave']['revision'],references=references)
    saved=bf.call(cur,'BIND_WAVE',request,key);again=bf.call(cur,'BIND_WAVE',request,key)
    qty=dict(cur.execute('select s.size_id::text,sum(y.qty_pcs) from erp.cutting_roll_yields y join erp.cutting_group_size_slots s on s.id=y.size_slot_id where s.cutting_group_id=%s group by s.size_id',(wave,)).fetchall())
    return b.verdict(dict(three_unique_choices=len(exposed)==3 and {s['id'] for s in exposed}==set(sizes),
        four_slots_preserved=one(cur,'select count(*) from erp.cutting_group_size_slots where cutting_group_id=%s',wave)==4,
        quantity_preserved=qty==dict(zip(sizes,[5,8,3])),three_bindings=one(cur,'select count(*) from erp.bf_wave_skus_v1 where cutting_group_id=%s',wave)==3,
        replay=again['replayed'] and again['revision']==saved['revision'],
        no_fg=one(cur,'select count(*) from erp.fg_lots where po_id=%s',po)==0),exposed=exposed,physical=qty,slots=4)

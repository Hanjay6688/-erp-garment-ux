"""Finite OW05 normal-flow gaps: HPP inverse order, whole PO and SKU waves."""
from datetime import timedelta
from decimal import Decimal as D
import json
import uuid

from cp7_contractor_correction import native_cases as n
import cp7_nota_cases as nota
import cp7_settlement_cases as payroll
import cp7_r3_hpp_pool_cases as hp
import cp7_wave_sewing_cases as wave

IDS=('OW05_HPP_POOL_BEFORE_NOTA_AND_SEWING_INVERSES',
     'OW05_TWO_POSTED_PICKUPS_ONE_PO_ALL_REPLACED',
     'OW05_CORRECTED_MANDOR_WAVE_SKU_NATIVE56')

def repost(cur,g,choice='NEW',qty=4):
    w=n.old.sewing_workspace(cur,g)
    p=dict(action='RECORD',group_id=g['group'],qty_pcs=str(qty),physical_at=g['at'](10).isoformat(),
        review_token=w['review_token'],change_reason=n.REASON,rate_choice=choice)
    n.auth.actor(cur)
    r=n.one(cur,'select public.erp_cp7_save_sewing_completion_v1(%s,%s,%s)',
        (json.dumps(p),str(uuid.uuid4()),w['group_version']))
    n.auth.b.api.admin(cur);return r

def cases(cur,today):
    def pool_order():
        g=n.fixture(cur,today,False);day=g['day']
        p=nota.payload(cur,dict(contractor=g['mandor']),today);p.update(period_start=str(day),period_end=str(today))
        note=nota.act(cur,'POST',nota.command(cur,'SAVE',p));pid=note['payroll_id']
        attendance=hp.attendance_payroll(cur,g['mandor'],'OW05-HPP-'+uuid.uuid4().hex[:8],day)
        hp.policy(cur,g['mandor'],day-timedelta(days=1));actor=hp.owner(cur)
        preview=hp.read(cur,actor,day,day)['preview'];made=hp.save(cur,actor,'CREATE',hp.create_body(preview))
        hp.save(cur,actor,'ACTIVATE',hp.pool_body(hp.facade_pool(cur,actor,made['pool_id']),'OW05 active HPP fixture'))
        assert hp.active_view(cur,g['po'])==D('1000.00')
        w=n.workspace(cur,g['po']);kinds=[b['kind']for b in w['blockers']]
        assert kinds.index('ATTENDANCE_POOL')<kinds.index('PAYROLL')<kinds.index('SEWING')<kinds.index('WORK')<kinds.index('WORK_JOURNAL'),kinds
        n.auth.refused(cur,lambda:payroll.act(cur,'CANCEL',payroll.doc(cur,attendance)),'PAYROLL_CONSUMED_BY_ACTIVE_HPP_POOL')
        n.auth.refused(cur,lambda:n.old.sewing_command(cur,n.old.sewing_workspace(cur,g),event=g['terminal']),'ACTIVE')
        hp.save(cur,actor,'CANCEL',hp.pool_body(hp.facade_pool(cur,actor,made['pool_id']),'OW05 cancel HPP before wage inverse'))
        assert hp.active_view(cur,g['po'])==0
        payroll.act(cur,'CANCEL',payroll.doc(cur,pid))
        n.old.sewing_command(cur,n.old.sewing_workspace(cur,g),event=g['terminal'])
        assert n.workspace(cur,g['po'])['eligible']
        n.correct(cur,g);repost(cur,g)
        assert n.balance(cur,g['po'],'WIP')==g['base_wip']+D('24.00')
        assert n.balance(cur,g['po'],'CONTRACTOR_PAYABLE',g['mandor'])==0
        assert n.balance(cur,g['po'],'CONTRACTOR_PAYABLE',g['target'])==D('-24.00')
        assert payroll.doc(cur,attendance)['status']=='APPROVED'
        return dict(status='PASS',HPP_active_cost='1000.00',HPP_after_native_cancel='0.00',
            actual_inverse_order=['ATTENDANCE_POOL','PAYROLL','SEWING'],old_payable_for_PO='0.00',
            new_payable_for_PO='24.00',old_attendance_not_reassigned=True,Native_pool_journal_and_old_wages_retained=True)

    def whole_po():
        prod=n.old.cut.cutting.qc.physical.b.chain.production;base=n.old.cut.cutting.qc.physical.base
        first=prod.estimated_receipt(cur,today);n.auth.b.api.admin(cur)
        day=first['purchase_day']+timedelta(days=1);po=str(uuid.uuid4());mandor=n.old.mandor_row(cur,'OW05-MULTI-A-'+uuid.uuid4().hex[:8])
        cur.execute("insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)values(%s,%s,%s,20,'CUTTING','CUTTING',%s,'OW05 two physical groups')",
            (po,'OW05-MULTI-'+po,prod.MODEL,prod.at(day,7)))
        groups=[]
        for index in range(2):
            f=first if index==0 else prod.estimated_receipt(cur,today)
            n.auth.b.api.admin(cur)
            p=dict(action='SAVE_DRAFT',po_id=po,pattern_id=prod.PATTERN,source_location_id=f['location'],cut_at=prod.at(day,8,index),
                change_reason=n.REASON,size_slots=[dict(slot_no=1,size_id=base.SIZE,drawing_no=1)],
                rolls=[dict(roll_id=f['roll'],qty_issued=10,qty_consumed=10,qty_reported_remaining=0,yields=[dict(slot_no=1,qty_pcs=10)])])
            saved=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',p)
            saved=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(p,id=saved['cutting_group_id'],action='POST'),expected_version=int(saved['row_version']))
            group=saved['cutting_group_id'];n.auth.b.api.admin(cur)
            pickup=n.old.native_pickup(cur,group,mandor,prod.at(day,9,index))
            groups.append(dict(group=group,po=po,pickup=pickup,mandor=mandor,day=day,at=lambda h,minute=0:prod.at(day,h,minute)))
        n.old.work_rates(cur,groups[0]);base_wip=n.balance(cur,po,'WIP')
        for g in groups:n.old.sewing_command(cur,n.old.sewing_workspace(cur,g),qty=4,at=g['at'](10))
        assert n.balance(cur,po,'CONTRACTOR_PAYABLE',mandor)==D('-32.00')
        for g in groups:
            terminal=n.one(cur,"select id from erp.sewing_terminal_events where cutting_group_id=%s and event_kind='SELESAI_DIJAHIT'",(g['group'],))
            n.old.sewing_command(cur,n.old.sewing_workspace(cur,g),event=str(terminal))
        target=n.old.mandor_row(cur,'OW05-MULTI-B-'+uuid.uuid4().hex[:8])
        component=n.one(cur,'select work_component_id from erp.work_bom_items where bom_version_id=(select id from erp.work_bom_versions where model_id=%s and is_active order by effective_from desc limit 1)and sequence_no=1',(prod.MODEL,))
        cur.execute('insert into erp.contractor_work_rates(contractor_id,model_id,work_component_id,rate_per_pcs,effective_from)values(%s,%s,%s,5,%s)',(target,prod.MODEL,component,prod.at(day,0)))
        before=n.one(cur,'select cp7_contractor_correction.financial_fingerprint_v1(%s)',(po,))
        w=n.workspace(cur,po);assert w['eligible']
        result=n.command(cur,n.payload(w,target));assert len(result['replacements'])==2
        assert n.one(cur,'select cp7_contractor_correction.financial_fingerprint_v1(%s)',(po,))==before
        for g in groups:
            assert n.one(cur,'select status from erp.cutting_pickups where id=%s',(g['pickup'],))=='REVERSED'
            old_at=n.one(cur,'select picked_up_at from erp.cutting_pickups where id=%s',(g['pickup'],))
            current=cur.execute("select contractor_id::text,picked_up_at from erp.cutting_pickups where cutting_group_id=%s and status='POSTED'",(g['group'],)).fetchall()
            assert current==[(target,old_at)]
            repost(cur,g)
        assert n.balance(cur,po,'WIP')==base_wip+D('48.00')
        assert n.balance(cur,po,'CONTRACTOR_PAYABLE',mandor)==0
        assert n.balance(cur,po,'CONTRACTOR_PAYABLE',target)==D('-48.00')
        return dict(status='PASS',whole_PO_groups=2,all_old_pickups_reversed=2,all_successors_posted=2,
            original_pickup_times_and_quantities=True,old_payable='0.00',new_payable='48.00',sewn_pcs=8)

    def sku_wave():
        g=wave.fixture(cur,today);at=wave.now(cur)-timedelta(seconds=40);lines=[(g['A']['id'],2),(g['B']['id'],1)]
        base_wip=n.balance(cur,g['po'],'WIP')
        wave.record(cur,wave.read(cur,g),lines,at)
        assert n.balance(cur,g['po'],'CONTRACTOR_PAYABLE',g['mandor'])==D('-53.00')
        old_work=cur.execute("select id::text from erp.work_completion_events where po_id=%s and status='POSTED'order by id",(g['po'],)).fetchall();assert len(old_work)==2
        events=cur.execute("select id::text from erp.sewing_terminal_events where po_id=%s and event_kind='SELESAI_DIJAHIT'order by id",(g['po'],)).fetchall()
        for(event,)in events:n.old.sewing_command(cur,n.old.sewing_workspace(cur,g),event=event)
        preserved=cur.execute('select to_jsonb(w)from erp.work_completion_events w where id=any(%s::uuid[])order by id',([r[0]for r in old_work],)).fetchall()
        target=n.old.mandor_row(cur,'OW05-WAVE-B-'+uuid.uuid4().hex[:8]);model=n.one(cur,'select model_id from erp.production_orders where id=%s',(g['po'],))
        cur.execute('insert into erp.contractor_work_rates(contractor_id,model_id,work_component_id,rate_per_pcs,effective_from)values(%s,%s,%s,2,%s)',(target,model,g['rates']['obras'],g['since']))
        before=n.one(cur,'select cp7_contractor_correction.financial_fingerprint_v1(%s)',(g['po'],))
        w=n.workspace(cur,g['po']);assert w['eligible'];n.command(cur,n.payload(w,target))
        assert n.one(cur,'select cp7_contractor_correction.financial_fingerprint_v1(%s)',(g['po'],))==before
        w=wave.read(cur,g);p=wave.payload(w,lines,at);p['rate_choice']='NEW';wave.send(cur,w,p)
        assert n.balance(cur,g['po'],'WIP')==base_wip+D('56.00')
        assert n.balance(cur,g['po'],'CONTRACTOR_PAYABLE',g['mandor'])==0
        assert n.balance(cur,g['po'],'CONTRACTOR_PAYABLE',target)==D('-56.00')
        assert cur.execute('select to_jsonb(w)from erp.work_completion_events w where id=any(%s::uuid[])order by id',([r[0]for r in old_work],)).fetchall()==preserved
        assert n.one(cur,"select count(*)from erp.work_completion_events where po_id=%s and status='POSTED'",(g['po'],))==2
        return dict(status='PASS',old_wage='53.00',new_wage='56.00',SKU_A_pcs=2,SKU_B_pcs=1,
            original_wave_binding_and_physical_time=True,original_two_work_rows_retained=True,old_payable='0.00')
    return list(zip(IDS,(pool_order,whole_po,sku_wave)))

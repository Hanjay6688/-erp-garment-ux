"""Writer replay of five unmodified auditor case bodies, not independent acceptance.
Origin: 09990020355fb7329fbc7b8710692bf1357d2401/audits/cp7_f02_20260929/probe.py
Original file SHA256: 43ac48d8ec4dffdffa94722348a503a345771094d1f33219c72a4d70431c29d1
Only packaging/selection differs; original expected vectors and refusal gates retained.
"""
import json,uuid
import cp7_wip_cases as kernel
import cp7_wip_source_cases as cut
import cp7_wip_production_cases as prod
import cp7_snapshot_cases as p02
b=cut.b;base=cut.base

def actual_vector(r):
    v=r.get('result',r)
    return [kernel.total(v,k+'_pcs') for k in ('input','wip','fg','bs','withheld','exited')] if v.get('status')=='COMPLETE' else dict(status=v.get('status'),reason=v.get('reason'),component=v.get('component'))

def verdict(expected,actual,**detail):return dict(status='PASS' if actual==expected else 'COUNTEREXAMPLE',expected=expected,actual=actual,**detail)

def doc_version(cur,table,ident):
    b.api.admin(cur)
    query={'qc_inspections':'select row_version from erp.qc_inspections where id=%s',
           'laundry_receipts':'select row_version from erp.laundry_receipts where id=%s'}[table]
    return cur.execute(query,(ident,)).fetchone()[0]

def qc_reverse(cur,f):
    b.api.admin(cur);qid=b.one(cur,"select q.id::text from erp.qc_inspections q join erp.qc_inspection_items i on i.inspection_id=q.id where i.cutting_group_id=%s and q.status='POSTED' order by q.physical_at desc limit 1",f['group'])
    b.chain.laundry_action(cur,'REVERSE_FINAL_SKU',dict(qc_inspection_id=qid,reason='Independent F02 restore source before re-QC'),doc_version(cur,'qc_inspections',qid))
    b.api.admin(cur);return qid

def cases(cur,today):
    def reverse_qc_bs():
        f=cut.fixture(cur,today);old=cut.capture(cur,[f['group']]);qid=qc_reverse(cur,f)
        states=cur.execute('select status,count(*) from erp.bs_cases where cutting_group_id=%s group by status',(f['group'],)).fetchall()
        before=b.boundary.snapshot(cur);a=cut.capture(cur,[f['group']]);z=prod.capture(cur,prod.scope(groups=[f['group']]))
        assert b.boundary.snapshot(cur)==before
        assert cut.read(cur,old['run_id'])['result']==old['result'] and cut.read(cur,old['run_id'])['source_state']=='ARCHIVED_STALE'
        expect=[100,100,0,0,0,0]
        return verdict([expect,expect],[actual_vector(a),actual_vector(z)],ordinary_post_and_reversal=True,qc_id=qid,bs_statuses=states,archive_preserved=True,read_did_not_change_business=True)
    def reverse_qc_control():
        f=cut.fixture(cur,today,False);cut.qc(cur,f,12,0,14);old=cut.capture(cur,[f['group']]);qc_reverse(cur,f)
        a=prod.capture(cur,prod.scope(groups=[f['group']]))
        assert actual_vector(a)==[100,100,0,0,0,0],a
        b.chain.laundry_action(cur,'REVERSE_RECEIPT',dict(receipt_id=f['receipt'],reason='Independent F02 reverse now-unconsumed receipt'),doc_version(cur,'laundry_receipts',f['receipt']))
        z=prod.capture(cur,prod.scope(groups=[f['group']]))
        assert actual_vector(z)==[100,100,0,0,0,0],z
        assert cut.read(cur,old['run_id'])['source_state']=='ARCHIVED_STALE'
        return dict(status='PASS',ordinary_good_only_qc_then_receipt_reversal=True,expected_actual=[100,100,0,0,0,0])
    def reverse_receipt_bs():
        f=cut.fixture(cur,today,False)
        ds=b.one(cur,'select s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where l.delivery_id=%s',f['delivery'])
        rec=b.chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=f['delivery'],wash_process_id=f['process'],physical_at=b.chain.production.at(f['day'],14).isoformat(),reason='Independent receipt with five BS',lines=[dict(delivery_batch_size_line_id=ds,qty_good_received=5,qty_bs_laundry=5,bs_product_id=f['product'])]),base.delivery_version(cur,f['delivery']))
        old=prod.capture(cur,prod.scope(groups=[f['group']]));assert actual_vector(old)==[100,95,0,5,0,0],old
        b.chain.laundry_action(cur,'REVERSE_RECEIPT',dict(receipt_id=rec['receipt_id'],reason='Independent undo receipt containing BS'),doc_version(cur,'laundry_receipts',rec['receipt_id']))
        fresh=prod.capture(cur,prod.scope(groups=[f['group']]))
        assert prod.read(cur,old['run_id'])['source_state']=='ARCHIVED_STALE'
        return verdict([100,100,0,0,0,0],actual_vector(fresh),ordinary_receipt_bs_reversal=True,receipt_id=rec['receipt_id'])
    def reverse_rework():
        f=cut.fixture(cur,today);case=b.one(cur,'select id::text from erp.bs_cases where cutting_group_id=%s and qc_item_id is not null',f['group'])
        bom=b.one(cur,'select erp.resolve_rework_accessory_bom_v1(%s,%s)::text',case,b.chain.production.at(f['day'],15))
        made=b.chain.bs_action(cur,'SAVE_REWORK',dict(rework_number='AUD-F02-'+uuid.uuid4().hex[:8],bs_case_id=case,destination_type='LAUNDRY',contractor_id=None,vendor_id=f['vendor'],qty_sent=4,physical_sent_at=b.chain.production.at(f['day'],15).isoformat(),status='IN_PROGRESS',return_fg_location_id=base.LOCATION,accessory_bom_version_id=bom,accessory_bom_item_ids=[],components=[],change_reason='Independent partial-source rework'))
        rid=made['result']['rework_order_id'];start=prod.capture(cur,prod.scope(groups=[f['group']]))
        assert actual_vector(start)==[100,84,15,1,0,0],start
        b.chain.bs_action(cur,'COMPLETE_REWORK',dict(rework_order_id=rid,qty_good=1,qty_bs=3,completed_at=b.chain.production.at(f['day'],16).isoformat(),return_fg_location_id=base.LOCATION,change_reason='One recovered, three remain BS'),b.chain.version(cur,'rework_orders',rid))
        done=prod.capture(cur,prod.scope(groups=[f['group']]));assert actual_vector(done)==[100,80,16,4,0,0],done
        b.chain.bs_action(cur,'REVERSE_REWORK_COMPLETION',dict(rework_order_id=rid,change_reason='Independent full completion reversal'),b.chain.version(cur,'rework_orders',rid))
        back=prod.capture(cur,prod.scope(groups=[f['group']]))
        assert prod.read(cur,done['run_id'])['result']==done['result']
        return verdict([100,80,15,5,0,0],actual_vector(back),ordinary_rework_completion_reversal=True)
    def source_limits():
        fifty=prod.scope(groups=[str(uuid.uuid4()) for _ in range(20)],items=[str(uuid.uuid4()) for _ in range(20)],cases=[str(uuid.uuid4()) for _ in range(10)])
        normalized=cur.execute('select cp7_wip.production_scope(%s::jsonb)',(json.dumps(fifty),)).fetchone()[0];assert sum(map(len,normalized.values()))==50
        fifty['unsourced_bs'].append(str(uuid.uuid4()));p02.refused(cur,lambda:cur.execute('select cp7_wip.production_scope(%s::jsonb)',(json.dumps(fifty),)),'CP7_WIP_SCOPE')
        f=cut.fixture(cur,today);n=cur.execute('select count(*) from erp.sewing_terminal_events where cutting_group_id=%s',(f['group'],)).fetchone()[0];assert 0<n<2000
        def inflate(count):
            # Administrative volume fixture only. Keep CHECKs and unique source
            # identities valid; every terminal row points to its own cloned
            # work-completion record. No operational posting claim is made.
            cur.execute('set local session_replication_role=replica')
            cur.execute("""with source as materialized(select * from erp.sewing_terminal_events where cutting_group_id=%s limit 1),
              clones as(insert into erp.work_completion_events
                select (jsonb_populate_record(null::erp.work_completion_events,to_jsonb(w)||jsonb_build_object('id',gen_random_uuid(),'completion_number','AUD-F02-'||gen_random_uuid()))).*
                from erp.work_completion_events w join source s on s.source_work_completion_id=w.id cross join generate_series(1,%s) returning id)
              insert into erp.sewing_terminal_events
                select (jsonb_populate_record(null::erp.sewing_terminal_events,to_jsonb(s)||jsonb_build_object('id',gen_random_uuid(),'event_number','AUD-F02-'||gen_random_uuid(),'source_work_completion_id',c.id))).*
                from source s cross join clones c""",(f['group'],count))
            cur.execute('set local session_replication_role=origin')
            assert cur.execute('select count(*) from erp.sewing_terminal_events s left join erp.work_completion_events w on w.id=s.source_work_completion_id where s.cutting_group_id=%s and w.id is null',(f['group'],)).fetchone()[0]==0
        inflate(2000-n)
        r=prod.capture(cur,prod.scope(groups=[f['group']]));assert r['capture_complete'] and actual_vector(r)==[100,80,15,5,0,0]
        count=cur.execute("select jsonb_array_length(facts->'facts'->'cutting'->'sewing') from cp7_wip.production_runs where id=%s",(r['run_id'],)).fetchone()[0];assert count==2000
        inflate(1)
        p02.refused(cur,lambda:prod.capture(cur,prod.scope(groups=[f['group']])),'CP7_WIP_SOURCE_INCOMPLETE')
        assert cur.execute('select count(*) from cp7_wip.production_runs').fetchone()[0]==1
        return dict(status='PASS',scope_parser_50_allowed_51_refused=True,source_2000_complete_2001_refused=True,administrative_bounded_source_fixture=True)
    return [("F02_AUDITOR_REPLAY_"+name,fn) for name,fn in [('REVERSE_QC_BS',reverse_qc_bs),('REVERSE_QC_CONTROL',reverse_qc_control),('REVERSE_RECEIPT_BS',reverse_receipt_bs),('REVERSE_REWORK',reverse_rework),('SOURCE_LIMITS',source_limits)]]

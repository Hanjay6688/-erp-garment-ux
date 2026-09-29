"""Writer regression for independent F02-01 and peer X06; ordinary business paths.

The separately attributed audit replay preserves the original five case bodies.
These new cases extend cancellation/coexistence and composed private matching.
"""
from copy import deepcopy
import json,uuid
import cp7_wip_cases as kernel
import cp7_wip_source_cases as cut
import cp7_wip_production_cases as prod
import cp7_f02_audit_replay as audit
import cp7_snapshot_cases as p02
b=cut.b;base=cut.base


def receipt_bs(cur,f,good,bs,hour):
    b.api.admin(cur)
    ds=b.one(cur,'select s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where l.delivery_id=%s',f['delivery'])
    return b.chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=f['delivery'],wash_process_id=f['process'],physical_at=b.chain.production.at(f['day'],hour).isoformat(),reason='F02 cancellation regression',lines=[dict(delivery_batch_size_line_id=ds,qty_good_received=good,qty_bs_laundry=bs,bs_product_id=f['product'])]),base.delivery_version(cur,f['delivery']))


def reversed_qc(cur,today):
    f=cut.fixture(cur,today);old=cut.capture(cur,[f['group']]);audit.qc_reverse(cur,f)
    return f,old


def kernel_fixture(cur):
    g=kernel.graph();g['pools']=g['pools'][:1];g['nodes']=g['nodes'][:1];g['events']=g['events'][:1]
    g['pools'][0]['input_pcs']=g['events'][0]['qty_pcs']='17';g['pools'][0]['size_id']='XS'
    p=kernel.call(cur,'yield',kernel.call(cur,'reconcile',g),[dict(position_key='A-sew',eligible_input_pcs='17',numerator='2',denominator='3',basis='ASSUMED',assumption_id='F02-X06-2of3',refs=kernel.refs('yield'))])
    edge=dict(key='red-blue',position_key='A-sew',target_key='same-target',size_id='XS',input_pcs='17',projected_good_pcs='11',match='CANDIDATE_MATCH',refs=kernel.refs('edge'))
    a=kernel.bind_compatible_fixture(p,dict(scenario_id='F02-X06',scope_id='COMPLETE17',complete_scope=True,edges=[edge]))
    for facts in (a['matching']['sources'],a['matching']['targets']):
        facts[0]['constraints']=[dict(field='color',value='RED',required=True,basis='FACT')]
    return p,a


def cases(cur,today):
    def new_qc_after_reverse():
        f,old=reversed_qc(cur,today);cut.qc(cur,f,12,3,15)
        before=b.boundary.snapshot(cur);a=cut.capture(cur,[f['group']]);z=prod.capture(cur,prod.scope(groups=[f['group']]))
        assert [audit.actual_vector(a),audit.actual_vector(z)]==[[100,85,12,3,0,0]]*2,(a,z)
        states=cur.execute('select status,count(*) from erp.bs_cases where cutting_group_id=%s group by status',(f['group'],)).fetchall()
        assert dict(states)=={'CANCELLED':1,'OPEN':1},states
        assert cut.read(cur,old['run_id'])['result']==old['result'] and cut.read(cur,old['run_id'])['source_state']=='ARCHIVED_STALE'
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',expected_actual=[100,85,12,3,0,0],cancelled_and_active_bs_coexist=True,archive_immutable=True,no_business_write=True)
    def new_receipt_mixed():
        f=cut.fixture(cur,today,False);r=receipt_bs(cur,f,5,5,14);old=prod.capture(cur,prod.scope(groups=[f['group']]))
        b.chain.laundry_action(cur,'REVERSE_RECEIPT',dict(receipt_id=r['receipt_id'],reason='F02 old receipt BS cancelled'),audit.doc_version(cur,'laundry_receipts',r['receipt_id']))
        b.api.admin(cur);receipt_bs(cur,f,7,3,15);o=prod.opening(cur,today)
        s=prod.scope(groups=[f['group']],items=[o['item']]);before=b.boundary.snapshot(cur);key=uuid.uuid4();new=prod.capture(cur,s,key)
        assert prod.vector(new)==[108,105,0,3,0,0],new
        assert prod.capture(cur,s,key)==new and prod.read(cur,old['run_id'])['result']==old['result']
        assert prod.read(cur,old['run_id'])['source_state']=='ARCHIVED_STALE'
        assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',expected_actual=[108,105,0,3,0,0],new_receipt_after_cancelled_bs=True,mixed_scope_replay=True,archive_immutable=True,no_business_write=True)
    def hold_source_reverse():
        f=cut.fixture(cur,today);case=b.one(cur,'select id::text from erp.bs_cases where cutting_group_id=%s and qc_item_id is not null',f['group'])
        b.chain.bs_action(cur,'HOLD_BS',dict(bs_case_id=case,physical_at=b.chain.production.at(f['day'],15).isoformat(),change_reason='F02 retained hold history'),b.chain.version(cur,'bs_cases',case))
        held=cut.capture(cur,[f['group']]);assert audit.actual_vector(held)==[100,80,15,0,5,0],held
        audit.qc_reverse(cur,f);new=prod.capture(cur,prod.scope(groups=[f['group']]))
        assert prod.vector(new)==[100,100,0,0,0,0],new
        assert cur.execute('select count(*) from erp.bs_case_hold_events where bs_case_id=%s',(case,)).fetchone()[0]==1
        assert cut.read(cur,held['run_id'])['result']==held['result']
        return dict(status='PASS',cancelled_hold_history_preserved=True,expected_actual=[100,100,0,0,0,0])
    def bad_active_lineage():
        f,old=reversed_qc(cur,today)
        captured=cur.execute('select cp7_wip.capture_cutting_sources(%s::uuid[])',([f['group']],)).fetchone()[0]
        def normalize(facts):return cur.execute('select cp7_wip.normalize_cutting(%s::jsonb)',(json.dumps(facts),)).fetchone()[0]
        assert normalize(captured)['status']=='COMPLETE'
        active=deepcopy(captured);active['facts']['bs'][0]['status']='OPEN'
        rejected=normalize(active);assert rejected['status']=='CONFLICT' and rejected['reason']=='BS_SOURCE_LINEAGE_MISMATCH',rejected
        cancelled_wrong_source=deepcopy(captured);cancelled_wrong_source['facts']['qc'][0]['status']='POSTED'
        rejected=normalize(cancelled_wrong_source);assert rejected['status']=='CONFLICT' and rejected['reason']=='CANCELLED_BS_SOURCE_UNPROVEN',rejected
        active['facts']['qc'][0]['status']='POSTED';active['facts']['bs'][0]['qty_pcs']='6'
        rejected=normalize(active);assert rejected['status']=='CONFLICT' and rejected['reason']=='NEGATIVE_PREFIX',rejected
        return dict(status='PASS',synthetic_capture_negative_controls=True,active_orphan_denied=True,unproven_cancellation_denied=True,negative_prefix_not_clamped=True)
    def active_child_cancelled_parent():
        f,old=reversed_qc(cur,today)
        captured=cur.execute('select cp7_wip.capture_cutting_sources(%s::uuid[])',([f['group']],)).fetchone()[0]
        captured['facts']['reworks']=[dict(id=str(uuid.uuid4()),bs_case_id=captured['facts']['bs'][0]['id'],status='IN_PROGRESS',physical_sent_at=captured['captured_at'])]
        rejected=cur.execute('select cp7_wip.normalize_cutting(%s::jsonb)',(json.dumps(captured),)).fetchone()[0]
        assert rejected['status']=='UNKNOWN' and rejected['reason']=='REWORK_BS_SOURCE_UNPROVEN',rejected
        return dict(status='PASS',synthetic_active_child_of_cancelled_source_not_silently_dropped=True)
    def forged_match():
        p,a=kernel_fixture(cur);positive=kernel.call(cur,'allocate',p,a);assert positive['status']=='FEASIBLE' and positive['matching_basis']=='RECOMPUTED_FROM_SAME_SNAPSHOT_FACTS',positive
        source=a['matching']['sources'][0];target=a['matching']['targets'][0]
        target['constraints'][0]['value']='BLUE'
        actual=kernel.call(cur,'match',source,target);assert actual['match']=='INCOMPATIBLE' and actual['reasons']==['COLOR_MISMATCH'],actual
        p02.refused(cur,lambda:kernel.call(cur,'allocate',p,a),'CP7_WIP_INELIGIBLE_ALLOCATION')
        a['edges'][0]['match']='CONFIRMED_TARGET';p02.refused(cur,lambda:kernel.call(cur,'allocate',p,a),'CP7_WIP_INELIGIBLE_ALLOCATION')
        target['constraints'][0]['value']='RED';source['constraints']=[]
        assert kernel.call(cur,'match',source,target)['match']=='NEEDS_CHECK'
        p02.refused(cur,lambda:kernel.call(cur,'allocate',p,a),'CP7_WIP_INELIGIBLE_ALLOCATION')
        legacy=deepcopy(a);del legacy['matching'];assert kernel.call(cur,'allocate',p,legacy)==dict(status='UNKNOWN',reason='MATCHING_FACTS_REQUIRED')
        return dict(status='PASS',oracle='X06_PEER_REGRESSION',input=17,yield_ratio='2/3',projected_good=11,compatible_control=True,forged_candidate_and_confirmed_denied=True,required_proof_missing_denied=True,legacy_label_only_not_feasible=True)
    def versions_and_snapshot():
        p,a=kernel_fixture(cur);old=deepcopy(a)
        a['matching']['targets'][0]['refs'][0]['revision']='2'
        p02.refused(cur,lambda:kernel.call(cur,'allocate',p,a),'CP7_WIP_MATCH_BINDING')
        a['edges'][0]['refs']=a['matching']['sources'][0]['refs']+a['matching']['targets'][0]['refs']
        assert kernel.call(cur,'allocate',p,a)['status']=='FEASIBLE'
        a['matching']['targets'][0]['constraints'][0]['value']='BLUE'
        p02.refused(cur,lambda:kernel.call(cur,'allocate',p,a),'CP7_WIP_INELIGIBLE_ALLOCATION')
        a=deepcopy(old);a['matching']['snapshot_id']='OTHER-SNAPSHOT'
        p02.refused(cur,lambda:kernel.call(cur,'allocate',p,a),'CP7_WIP_MATCH_SNAPSHOT')
        a=deepcopy(old);a['matching']['sources'][0]['refs']=kernel.refs('wrong-position-version')
        a['edges'][0]['refs']=a['matching']['sources'][0]['refs']+a['matching']['targets'][0]['refs']
        p02.refused(cur,lambda:kernel.call(cur,'allocate',p,a),'CP7_WIP_MATCH_BINDING')
        return dict(status='PASS',stale_target_review_denied=True,reviewed_new_revision_accepted=True,new_constraint_recomputed=True,cross_snapshot_and_source_revision_denied=True)
    def shape_and_confirmation():
        p,a=kernel_fixture(cur);a['matching']['sources'][0]['confirmed_target']='same-target'
        p02.refused(cur,lambda:kernel.call(cur,'allocate',p,a),'CP7_WIP_MATCH_STALE')
        a['edges'][0]['match']='CONFIRMED_TARGET';assert kernel.call(cur,'allocate',p,a)['status']=='FEASIBLE'
        a['matching']['targets'].append(deepcopy(a['matching']['targets'][0]))
        p02.refused(cur,lambda:kernel.call(cur,'allocate',p,a),'CP7_WIP_MATCH_DUPLICATE')
        a['matching']['targets']=[];p02.refused(cur,lambda:kernel.call(cur,'allocate',p,a),'CP7_WIP_MATCH_FACTS')
        return dict(status='PASS',actual_explicit_destination_accepted=True,old_match_review_denied=True,duplicate_and_missing_target_denied=True)
    return [('F02_FIX_'+name,fn) for name,fn in [('NEW_QC_AFTER_REVERSAL',new_qc_after_reverse),('NEW_RECEIPT_MIXED_REPLAY',new_receipt_mixed),('HELD_BS_SOURCE_REVERSED',hold_source_reverse),('ACTIVE_LINEAGE_NEGATIVE',bad_active_lineage),('ACTIVE_CHILD_CANCELLED_PARENT',active_child_cancelled_parent),('X06_FORGED_MATCH',forged_match),('X06_VERSION_SNAPSHOT',versions_and_snapshot),('X06_SHAPE_CONFIRMATION',shape_and_confirmation)]]


def http_cases(http,today):
    def reversal_read():
        owner=http.login('OWNER','f02-fixed-wip')
        with http.connect() as conn,conn.cursor() as cur:
            f,old=reversed_qc(cur,today);conn.commit()
        args=dict(p_scope=prod.scope(groups=[f['group']]),p_request=str(uuid.uuid4()))
        first=owner.rpc('erp_cp7_capture_production_wip_v1',args);assert first['status']==200,first
        assert prod.vector(first['body'])==[100,100,0,0,0,0],first
        assert owner.rpc('erp_cp7_capture_production_wip_v1',args)['body']==first['body']
        with http.connect() as conn,conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_capture_production_wip_v1',args)['status']==403
        assert owner.rpc('erp_cp7_read_production_wip_v1',dict(p_run=first['body']['run_id']))['status']==403
        return dict(status='PASS',real_auth_http_reversed_bs_complete=True,expected_actual=[100,100,0,0,0,0],same_request_replay=True,current_revocation_enforced=True,planner_http_not_claimed=True)
    return [('F02_FIX_HTTP_REVERSED_BS_CURRENT_AUTH',reversal_read)]

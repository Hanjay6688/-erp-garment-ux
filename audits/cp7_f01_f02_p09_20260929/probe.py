"""Independent repair acceptance and extra F01/F02/P09 probes. See ORACLE.md."""
from pathlib import Path
from copy import deepcopy
from decimal import Decimal
from datetime import timedelta
import sys,json,uuid
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import original_f02_probe as old
import cp7_snapshot_cases as snap
import cp7_wip_cases as kernel
import cp7_wip_source_cases as cut
import cp7_wip_production_cases as prod
import cp7_procurement_cases as receipt
import cp7_material_cases as material
import cp7_material_count_cases as count
import cp7_invoice_cases as invoice
import cp7_invoice_document_cases as document
import cp7_receipt_reversal_cases as reversal
b=snap.b

def allocated(cur,p,a):
    b.api.admin(cur)
    return cur.execute('select cp7_wip.check_allocations(%s::jsonb,%s::jsonb)',(json.dumps(p),json.dumps(a))).fetchone()[0]

def matching_fixture(cur):
    p=old.project(cur,old.physical(cur,17),17,2,3)
    n=next(n for n in p['positions'] if n['key']=='sew')
    s=dict(key='sew',quality='COMPLETE',size_id='XS',confirmed_target=None,
      constraints=[dict(field='color',value='RED',required=True,basis='FACT')],refs=deepcopy(n['refs']))
    t=dict(key='target',size_id='XS',constraints=[dict(field='color',value='RED',required=True,basis='FACT')],refs=old.refs('target-facts'))
    e=old.edge('edge17',17,11);e['refs']=deepcopy(s['refs'])+deepcopy(t['refs'])
    a=dict(scenario_id='own17',scope_id='ALL',complete_scope=True,edges=[e],matching=dict(snapshot_id=p['snapshot_id'],sources=[s],targets=[t]))
    return p,a

def own_cases(cur,today):
    def repeat_cancel():
        f=cut.fixture(cur,today);scope=prod.scope(groups=[f['group']]);first=prod.capture(cur,scope)
        assert old.actual_vector(first)==[100,80,15,5,0,0]
        old.qc_reverse(cur,f)
        assert old.actual_vector(prod.capture(cur,scope))==[100,100,0,0,0,0]
        cut.qc(cur,f,7,3,15);second=prod.capture(cur,scope)
        assert old.actual_vector(second)==[100,90,7,3,0,0],second
        old.qc_reverse(cur,f)
        assert old.actual_vector(prod.capture(cur,scope))==[100,100,0,0,0,0]
        cut.qc(cur,f,11,2,16);third=prod.capture(cur,scope)
        assert old.actual_vector(third)==[100,87,11,2,0,0],third
        for archived in (first,second):
            r=prod.read(cur,archived['run_id']);assert r['source_state']=='ARCHIVED_STALE' and r['result']==archived['result']
        return dict(status='PASS',vectors=[[100,80,15,5],[100,100,0,0],[100,90,7,3],[100,100,0,0],[100,87,11,2]],cancelled_and_active_bs_coexist=True,archives_immutable=True)
    def labels_and_colors():
        p,a=matching_fixture(cur);legacy=deepcopy(a);legacy.pop('matching')
        assert allocated(cur,p,legacy)==dict(status='UNKNOWN',reason='MATCHING_FACTS_REQUIRED')
        assert allocated(cur,p,a)['status']=='FEASIBLE'
        bad=deepcopy(a);bad['matching']['targets'][0]['constraints'][0]['value']='BLUE'
        for label in ('CANDIDATE_MATCH','CONFIRMED_TARGET'):
            bad['edges'][0]['match']=label
            snap.refused(cur,lambda:allocated(cur,p,bad),'CP7_WIP_INELIGIBLE_ALLOCATION')
        bad=deepcopy(a);bad['matching']['sources'][0]['constraints'][0].update(value=None,basis='UNKNOWN')
        snap.refused(cur,lambda:allocated(cur,p,bad),'CP7_WIP_INELIGIBLE_ALLOCATION')
        bad=deepcopy(a);bad['edges'][0]['match']='CONFIRMED_TARGET'
        snap.refused(cur,lambda:allocated(cur,p,bad),'CP7_WIP_MATCH_STALE')
        return dict(status='PASS',legacy_label_unknown=True,red_red_feasible=True,red_blue_both_positive_labels_denied=True,required_unknown_denied=True,forged_confirmation_denied=True,input=17,projected_good=11)
    def binding():
        p,a=matching_fixture(cur)
        for side in ('sources','targets'):
            bad=deepcopy(a);bad['matching'][side][0]['refs'][0]['revision']='2'
            snap.refused(cur,lambda:allocated(cur,p,bad),'CP7_WIP_MATCH_BINDING')
            bad=deepcopy(a);bad['matching'][side].append(deepcopy(bad['matching'][side][0]))
            snap.refused(cur,lambda:allocated(cur,p,bad),'CP7_WIP_MATCH_DUPLICATE')
            bad=deepcopy(a);bad['matching'][side]=[]
            snap.refused(cur,lambda:allocated(cur,p,bad),'CP7_WIP_MATCH_FACTS')
        bad=deepcopy(a);bad['matching']['snapshot_id']='different'
        snap.refused(cur,lambda:allocated(cur,p,bad),'CP7_WIP_MATCH_SNAPSHOT')
        bad=deepcopy(a);bad['edges'][0]['projected_good_pcs']='12'
        assert allocated(cur,p,bad)['status']=='INFEASIBLE'
        bad=deepcopy(a);bad['edges'].append(deepcopy(bad['edges'][0]));bad['edges'][1].update(key='other',input_pcs='1',projected_good_pcs='0')
        assert allocated(cur,p,bad)['status']=='INFEASIBLE'
        assert allocated(cur,p,a)['status']=='FEASIBLE'
        return dict(status='PASS',source_target_version_binding=True,duplicate_missing_facts_denied=True,snapshot_binding=True,capacity_and_yield_preserved=True)
    def actor_uuid():
        f=snap.fixture(cur,today);a,role_a=snap.custom_actor(cur);z,role_z=snap.custom_actor(cur);key=uuid.uuid4()
        one=snap.create(cur,f['root'],key,a);two=snap.create(cur,f['root'],key,z)
        assert one['run_id']!=two['run_id']
        for who,other in ((a,two),(z,one)):
            snap.refused(cur,lambda:snap.read(cur,other['run_id'],subject=who),'CP7_RUN_UNAVAILABLE')
        before=snap.stored(cur,one['run_id'])
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(a,))
        snap.refused(cur,lambda:snap.create(cur,f['root'],key,a),'CP7_ACCESS_DENIED')
        snap.refused(cur,lambda:snap.read(cur,one['run_id'],subject=a),'CP7_ACCESS_DENIED')
        assert snap.stored(cur,one['run_id'])==before
        assert snap.create(cur,f['root'],key,z)['run_id']==two['run_id']
        return dict(status='PASS',same_uuid_actor_isolation=True,inactive_actor_cached_replay_and_read_denied=True,other_actor_unaffected=True,fixture='ADMIN_SOURCE_READER_ONLY')
    def money_cycle():
        f=snap.fixture(cur,today);who,role=snap.custom_actor(cur)
        first=snap.create(cur,f['root'],subject=who)
        cur.execute("insert into erp.app_role_permissions values(%s,'finance.hpp.view')",(role,))
        historical=snap.read(cur,first['run_id'],subject=who)
        assert not historical['financial_captured'] and 'lot_cost' not in historical['counts']
        second=snap.create(cur,f['root'],subject=who)
        assert snap.read(cur,second['run_id'],subject=who)['financial_captured']
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.hpp.view'",(role,))
        denied=snap.read(cur,second['run_id'],subject=who)
        assert not denied['financial_captured'] and 'lot_cost' not in denied['counts']
        snap.refused(cur,lambda:snap.read(cur,second['run_id'],'lot_cost',subject=who),'CP7_FINANCIAL_ACCESS_DENIED')
        return dict(status='PASS',grant_does_not_backfill_old_snapshot=True,revocation_redacts_old_financial_capture=True,fixture='ADMIN_SOURCE_READER_ONLY')
    def big_invoice():
        f=invoice.fixture(cur,today,qty='1',price='240');initial=reversal.net_ledger(cur)
        r=invoice.finalize(cur,f,'1','22000000');assert invoice.amounts(cur,f)==(22000000,0,1,22000000),invoice.amounts(cur,f)
        ap=cur.execute("select sum(l.credit-l.debit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id join erp.accounting_account_mappings a on a.account_id=l.account_id where a.mapping_key='AP_SUPPLIER' and j.source_type='MATERIAL_SUPPLIER_INVOICE' and j.source_id=%s",(r['invoice_id'],)).fetchone()[0]
        assert ap==22000000,ap
        invoice.reverse(cur,f,r['invoice_id']);assert invoice.amounts(cur,f)==(0,240,1,240) and reversal.net_ledger(cur)==initial
        return dict(status='PASS',one_line_no_discount=22000000,ap_gl=str(ap),physical_qty=1,inverse_exact=True)
    def two_receipts():
        f,g=invoice.fixture(cur,today,qty='7'),invoice.fixture(cur,today,qty='11');initial=reversal.net_ledger(cur)
        p=document.payload(f,g);p['lines'][0].update(qty_invoiced='7',unit_price='13');p['lines'][1].update(qty_invoiced='11',unit_price='17')
        d=document.save(cur,p);key=uuid.uuid4();posted=document.action(cur,'POST',f,g,d,key)
        assert document.action(cur,'POST',f,g,d,key)==posted
        assert invoice.amounts(cur,f)==(91,0,7,13) and invoice.amounts(cur,g)==(187,0,11,17)
        assert Decimal(document.detail(cur,f,d['invoice_id'])['document_net_amount'])==278
        document.action(cur,'REVERSE',f,g,posted)
        assert invoice.amounts(cur,f)==(0,70,7,10) and invoice.amounts(cur,g)==(0,110,11,10) and reversal.net_ledger(cur)==initial
        return dict(status='PASS',independent_inputs=['7*13','11*17'],net_invoice=278,source_ap=[91,187],physical=[7,11],replay_once_and_inverse_exact=True)
    def make_pair():
        f=material.fixture(cur,today);g0=receipt.fixture(cur,today);g0['payload']['location_id']=f['location'];g0['location']=f['location']
        gd=receipt.command(cur,'SAVE_DRAFT',g0['payload']);g0['receipt']=receipt.post(cur,gd)
        g0['roll']=str(cur.execute('select r.id from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=%s',(gd['purchase_id'],)).fetchone()[0])
        return f,g0
    def pair_payload(f,g,second):
        p=count.scope(f,'8');p['items'].append(dict(material_id=g['material'],roll_id=g['roll'],physical_qty=second))
        preview=count.preview(cur,p)
        for item,proof in zip(p['items'],preview['items']):item['basis_token']=proof['basis_token']
        p.update(adjustment_number=f['tag']+'-OWNCOUNT',reason_code='COUNT_CORRECTION',change_reason='Independent multi-item physical count')
        return p
    def multi_count():
        f,g=make_pair();initial=reversal.net_ledger(cur);p=pair_payload(f,g,'7');d=count.command(cur,'SAVE',p)
        assert receipt.qty(cur,f)[0]==10 and receipt.qty(cur,g)[0]==10
        posted=count.action(cur,'POST',d)
        assert receipt.qty(cur,f)[0]==8 and receipt.qty(cur,g)[0]==7
        count.action(cur,'REVERSE',posted)
        assert receipt.qty(cur,f)[0]==10 and receipt.qty(cur,g)[0]==10 and reversal.net_ledger(cur)==initial
        return dict(status='PASS',physical_count=[8,7],independent_deltas=[-2,-3],inverse_restores=[10,10],scope='NATIVE_PUBLIC_API_MULTILINE_NOT_UI')
    def zero_line_stale():
        f,g=make_pair();p=pair_payload(f,g,'10');d=count.command(cur,'SAVE',p)
        g['destination']=f['destination'];t,_=material.draft(cur,g,'1');material.post(cur,t)
        before=b.boundary.snapshot(cur)
        snap.refused(cur,lambda:count.action(cur,'POST',d),'CP7_COUNT_STOCK_CHANGED_REVIEW_AGAIN')
        assert b.boundary.snapshot(cur)==before and receipt.qty(cur,f)[0]==10
        return dict(status='PASS',initial_zero_delta_line_changed_before_post=True,entire_count_refused_atomically=True)
    def cross_action_request():
        f=material.fixture(cur,today);_,p=material.draft(cur,f,'2');p['transfer_number']+='-IDENTITY';key=uuid.uuid4()
        d=material.command(cur,'SAVE_TRANSFER',p,key=key);counter=count.payload(cur,f,'8');before=b.boundary.snapshot(cur)
        snap.refused(cur,lambda:count.command(cur,'SAVE',counter,key=key),'CP7_COUNT_REQUEST_CHANGED')
        assert b.boundary.snapshot(cur)==before and receipt.qty(cur,f)[0]==10
        assert material.command(cur,'SAVE_TRANSFER',p,key=key)==d
        return dict(status='PASS',shared_request_namespace_cannot_change_action=True,original_outcome_still_recoverable=True)
    targets={'AUD_F02_QC_BS_REVERSAL','AUD_F02_GOOD_ONLY_REVERSAL_CONTROL','AUD_F02_LAUNDRY_BS_REVERSAL','AUD_F02_REWORK_COMPLETION_REVERSE','AUD_F02_SCOPE_AND_SOURCE_LIMITS'}
    original=[(k,f) for k,f in old.cases(cur,today) if k in targets]
    new=[('F02_REPEAT_CANCEL_ACTIVE_BS',repeat_cancel),('F02_MATCH_LABEL_COLOR',labels_and_colors),('F02_MATCH_REFS_CAPACITY',binding),
      ('F01_ACTOR_UUID_DEACTIVATE',actor_uuid),('F01_FINANCE_GRANT_REVOKE',money_cycle),('P09_BIG_INVOICE_22M',big_invoice),
      ('P09_TWO_RECEIPTS_278',two_receipts),('P09_MULTILINE_COUNT',multi_count),('P09_ZERO_DELTA_LINE_STALE',zero_line_stale),('P09_CROSS_ACTION_UUID',cross_action_request)]
    return original+[('AUD_NEW_'+k,f) for k,f in new]

def http_cases(http,today):
    def repaired_capture():
        owner=http.login('OWNER','own-f02-fixed');other=http.login('OWNER','own-f02-other')
        with http.connect() as conn,conn.cursor() as cur:
            f=cut.fixture(cur,today);old.qc_reverse(cur,f);conn.commit()
        args=dict(p_scope=prod.scope(groups=[f['group']]),p_request=str(uuid.uuid4()))
        r=owner.rpc('erp_cp7_capture_production_wip_v1',args);assert r['status']==200,r
        assert old.actual_vector(r['body'])==[100,100,0,0,0,0]
        assert owner.rpc('erp_cp7_capture_production_wip_v1',args)['body']['run_id']==r['body']['run_id']
        assert other.rpc('erp_cp7_read_production_wip_v1',dict(p_run=r['body']['run_id']))['status']==403
        with http.connect() as conn,conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_capture_production_wip_v1',args)['status']==403
        return dict(status='PASS',ordinary_bs_reversal_public_http=True,vector=[100,100,0,0,0,0],replay_stable=True,other_actor_and_revoked_replay_denied=True)
    return [('AUD_NEW_F02_HTTP_FIXED_REPLAY',repaired_capture)]

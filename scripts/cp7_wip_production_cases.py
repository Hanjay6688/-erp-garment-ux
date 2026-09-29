"""Declared source oracles for one capture of cutting, opening and non-PO BS."""
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import json,uuid,threading,time
import cp7_wip_source_cases as cut
import cp6_ax_probe as ax
b=cut.b;p02=cut.p02;base=cut.base;total=cut.total

def scope(groups=(),items=(),cases=()):
    return dict(cutting_groups=list(groups),opening_items=list(items),unsourced_bs=list(cases))

def capture(cur,s,key=None,subject=None):
    p02.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_capture_production_wip_v1(%s::jsonb,%s)',(json.dumps(s),key or uuid.uuid4())).fetchone()[0]
    b.api.admin(cur);return r

def read(cur,run,subject=None):
    p02.actor(cur,subject);r=cur.execute('select public.erp_cp7_read_production_wip_v1(%s)',(run,)).fetchone()[0]
    b.api.admin(cur);return r

def opening(cur,today,stage='SEWING',claims=None):
    rows=b.w05_rows(today,claims=claims) if claims is not None else b.bbp.production_rows(stage=stage,po_mandor=stage!='CUTTING',holder=None if stage=='CUTTING' else '{C}')
    f=b.bbp.production_post(cur,today,rows);f['item']=b.bbp.source_of(cur,f)['opening_item_id'];return f

def vector(r):
    assert r['capture_complete'] and r['result']['status']=='COMPLETE',r
    return [total(r['result'],k+'_pcs') for k in ('input','wip','fg','bs','withheld','exited')]

def cases(cur,today):
    def opening_lifecycle():
        f=opening(cur,today,'CUTTING');s=scope(items=[f['item']]);r=capture(cur,s)
        assert vector(r)==[8,8,0,0,0,0] and r['source_state']=='UNCHANGED',r
        assert any(p['stage']=='CUT_UNASSIGNED' for p in r['result']['positions'])
        b.bbp.wip_op(cur,f,'PICKUP',contractor_code=f['code'],date=str(f['cutover']+timedelta(days=1)))
        picked=capture(cur,s);assert vector(picked)==[8,8,0,0,0,0] and any(p['stage']=='SEWING_UNRESOLVED' for p in picked['result']['positions'])
        out=b.bbp.complete(cur,f,f['cutover']+timedelta(days=2),3)
        done=capture(cur,s);assert vector(done)==[8,5,3,0,0,0]
        b.bbp.split(cur,f,f['cutover']+timedelta(days=3),2)
        split=capture(cur,s);assert vector(split)==[8,3,3,2,0,0]
        b.bbp.wip_op(cur,f,'REVERSE',output_id=out['output_id'])
        back=capture(cur,s);assert vector(back)==[8,6,0,2,0,0]
        assert read(cur,done['run_id'])['result']==done['result'] and read(cur,done['run_id'])['source_state']=='ARCHIVED_STALE'
        return dict(status='PASS',ordinary_import_pickup_complete_split_reverse=True,initial=8,after_split=[8,3,3,2,0,0],after_reverse=[8,6,0,2,0,0],old_snapshot_immutable=True)
    def opening_claims():
        f=opening(cur,today,claims=((None,'MISSING','2'),));s=scope(items=[f['item']]);r=capture(cur,s)
        assert vector(r)==[8,6,0,0,2,0]
        b.claim_op(cur,f,'RECOVER_CLAIM',b.claim_of(cur,f),qty_pcs='1',date=str(today))
        recovered=capture(cur,s);assert vector(recovered)==[8,7,0,0,1,0]
        b.claim_op(cur,f,'RESOLVE_CLAIM',b.claim_of(cur,f),resolution='WRITTEN_OFF',date=str(today))
        settled=capture(cur,s);assert vector(settled)==[8,7,0,0,1,0]
        assert read(cur,recovered['run_id'])['source_state']=='ARCHIVED_STALE'
        return dict(status='PASS',ordinary_import_claim_recover_writeoff=True,opening=8,recovered_to_wip=1,writeoff_does_not_create_good=True)
    def mixed():
        c=cut.fixture(cur,today);o=opening(cur,today);s=scope([c['group']],[o['item']]);r=capture(cur,s)
        assert vector(r)==[108,88,15,5,0,0]
        facts=cur.execute('select facts from cp7_wip.production_runs where id=%s',(r['run_id'],)).fetchone()[0]
        assert facts['captured_at']==r['captured_at'] or str(facts['captured_at'])==str(r['captured_at'])
        assert len(r['result']['totals'])==3 and len({p['pool_key'] for p in r['result']['totals']})==3
        assert r['result']['timing']['eta'] is None and r['result']['timing']['on_time'] is None
        return dict(status='PASS',one_capture_mixed_origins=True,expected_actual=[108,88,15,5,0,0],no_calendar_no_eta=True)
    def unsourced_good():
        f=ax.stocked_product(cur,today);now=ax.r1.now(cur)
        case=ax.manual_bs(cur,f['product'],'OUT_OF_NOWHERE',5,now-timedelta(minutes=15))['result']['bs_case_id']
        s=scope(cases=[case]);r=capture(cur,s);assert vector(r)==[5,0,0,5,0,0]
        posted=ax.post(cur,dict(source_kind='GOOD_FROM_UNSOURCED_BS',bs_case_id=case,location_id=base.LOCATION,qty_pcs=3,
          physical_at=(now-timedelta(minutes=5)).isoformat(),reason='P04 actual non-PO recovery'))
        good=capture(cur,s);assert vector(good)==[5,0,3,2,0,0]
        ax.reverse(cur,posted['receipt_id'],'P04 non-PO recovery reversal')
        back=capture(cur,s);assert vector(back)==[5,0,0,5,0,0]
        assert read(cur,good['run_id'])['source_state']=='ARCHIVED_STALE'
        return dict(status='PASS',ordinary_found_bs_and_ax_recovery=True,initial_bs=5,good=3,remaining_bs=2,reversal_restores_same_origin=True)
    def auth_scope():
        f=opening(cur,today);s=scope(items=[f['item']]);subject,role=p02.custom_actor(cur);key=uuid.uuid4()
        r=capture(cur,s,key,subject);assert capture(cur,s,key,subject)['run_id']==r['run_id']
        p02.refused(cur,lambda:read(cur,r['run_id']),'CP7_WIP_RUN_UNAVAILABLE')
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,))
        p02.refused(cur,lambda:capture(cur,s,key,subject),'CP7_ACCESS_DENIED')
        p02.refused(cur,lambda:read(cur,r['run_id'],subject),'CP7_ACCESS_DENIED')
        return dict(status='PASS',owner_only_and_current_auth_replay=True)
    def reject_aliases():
        f=cut.fixture(cur,today);case=b.one(cur,'select id::text from erp.bs_cases where cutting_group_id=%s and qc_item_id is not null',f['group'])
        p02.refused(cur,lambda:capture(cur,scope(groups=[f['group']],cases=[case])),'CP7_WIP_SOURCE_INCOMPLETE')
        for s in [scope(),scope(items=[str(uuid.uuid4())]),scope(groups=[f['group'],f['group']])]:
            p02.refused(cur,lambda:capture(cur,s),'CP7_WIP_')
        assert cur.execute('select count(*) from cp7_wip.production_runs').fetchone()[0]==0
        return dict(status='PASS',ordinary_bs_not_recaptured_as_non_po=True,no_partial_runs=True)
    return [('P04_PRODUCTION_'+name,fn) for name,fn in [('OPENING_LIFECYCLE',opening_lifecycle),('OPENING_CLAIMS',opening_claims),('MIXED_ONE_CAPTURE',mixed),('UNSOURCED_BS_GOOD',unsourced_good),('CURRENT_AUTH',auth_scope),('NO_ORIGIN_ALIAS',reject_aliases)]]

def http_cases(http,today):
    def auth():
        owner=http.login('OWNER','p04-production-owner');other=http.login('OWNER','p04-production-other')
        with http.connect() as conn,conn.cursor() as cur:f=opening(cur,today);conn.commit()
        args=dict(p_scope=scope(items=[f['item']]),p_request=str(uuid.uuid4()))
        r=owner.rpc('erp_cp7_capture_production_wip_v1',args);assert r['status']==200,r
        assert vector(r['body'])==[8,8,0,0,0,0]
        rid=r['body']['run_id'];assert owner.rpc('erp_cp7_capture_production_wip_v1',args)['body']['run_id']==rid
        assert other.rpc('erp_cp7_read_production_wip_v1',dict(p_run=rid))['status']==403
        assert http.anon_rpc('erp_cp7_read_production_wip_v1',dict(p_run=rid))['status'] in (401,403,404)
        with http.connect() as conn,conn.cursor() as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_read_production_wip_v1',dict(p_run=rid))['status']==403
        return dict(status='PASS',real_http_mixed_facade=True,owner_actor_revocation=True)
    return [('P04_PRODUCTION_HTTP_AUTH',auth)]

def races(tools,today):
    def coherent():
        with tools.connect() as conn,conn.cursor() as cur:
            c=cut.fixture(cur,today);o=opening(cur,today);conn.commit()
        s=scope([c['group']],[o['item']]);ready=threading.Event();done=threading.Event();pairs=[];overlap=0
        def writer():
            with tools.connect() as conn,conn.cursor() as cur:
                for i in range(24):
                    good,qty=(29,8) if i%2==0 else (30,9)
                    # Administrative atomic source corrections test cross-domain
                    # MVCC only. They do not authorize editing posted documents.
                    cur.execute('set local session_replication_role=replica')
                    cur.execute('update erp.laundry_receipt_lines set qty_good_received=%s where id=%s',(good,c['receipt_line']))
                    cur.execute('update erp.laundry_receipt_batch_size_lines set qty_good_received=%s where id=%s',(good,c['receipt_size']))
                    cur.execute('update erp.initial_import_production_sources set qty_pcs=%s where opening_item_id=%s',(qty,o['item']))
                    cur.execute('update erp.opening_balance_items set qty=%s where id=%s',(qty,o['item']))
                    cur.execute('set local session_replication_role=origin');conn.commit();ready.set();time.sleep(.03)
            done.set()
        with ThreadPoolExecutor(max_workers=1) as pool:
            w=pool.submit(writer);assert ready.wait(8)
            with tools.connect() as conn,conn.cursor() as cur:
                for _ in range(12):
                    r=capture(cur,s);assert r['result']['status']=='COMPLETE',r
                    facts=cur.execute('select facts from cp7_wip.production_runs where id=%s',(r['run_id'],)).fetchone()[0]['facts'];conn.commit()
                    pairs.append((int(facts['cutting']['receipts'][0]['good_pcs']),int(facts['other']['origins'][0]['qty_pcs'])))
                    if not done.is_set():overlap+=1
            w.result(timeout=20)
        assert overlap>0 and set(pairs)<={(29,8),(30,9)},(overlap,pairs)
        return dict(status='PASS',cross_origin_one_mvcc_snapshot=True,overlap=overlap,captures=12,observed_pairs=sorted(set(pairs)))
    return [('P04_PRODUCTION_RACE_CROSS_ORIGIN',coherent)]

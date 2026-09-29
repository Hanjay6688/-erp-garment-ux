"""Actual CP6 posting -> CP7 immutable cutting graph. No administrative stock setup."""
from concurrent.futures import ThreadPoolExecutor
import json,uuid,threading,time
import psycopg
import cp6_bf_probe as bf
import cp7_snapshot_cases as p02
from cp7_wip_cases import total
b=bf.b;base=b.chain.base

def fixture(cur,today,finish=True):
    f=b.two_size_fixture(cur,b.case_day(today),'P04-ORIGIN',q1=60,q2=40)
    b.api.admin(cur);product=b.sized_product(cur,base.SIZE,'P04-'+uuid.uuid4().hex[:8])
    payload=dict(distribution_batch_id=f['batch'],vendor_id=f['vendor'],wash_process_id=f['process'],target_dyeing_color='P04',
        physical_at=f['send'].isoformat(),reason='P04 actual 100 PCS provenance',lines=[dict(size_id=base.SIZE,qty_sent_pcs=40)])
    sent=b.bd(cur,'POST_PRICED_DELIVERY',dict(delivery=payload,expected_version=str(base.group_version(cur,f['group'])),pricing=dict(deferred=True)))
    delivery=sent['delivery_id'];b.api.admin(cur)
    ds=b.one(cur,'select s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where l.delivery_id=%s',delivery)
    rec=b.chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=delivery,wash_process_id=f['process'],physical_at=b.chain.production.at(f['day'],13).isoformat(),reason='P04 30 returned from 40 sent',
        lines=[dict(delivery_batch_size_line_id=ds,qty_good_received=30,qty_bs_laundry=0,bs_product_id=None)]),base.delivery_version(cur,delivery))
    b.api.admin(cur);line=b.receipt_line(cur,rec['receipt_id']);rs=b.one(cur,'select id::text from erp.laundry_receipt_batch_size_lines where receipt_line_id=%s',line)
    f.update(product=product,delivery=delivery,receipt=rec['receipt_id'],receipt_line=line,receipt_size=rs)
    if finish:qc(cur,f,15,5,14)
    return f

def qc(cur,f,good,bs,hour,mode='PARTIAL_SELECTION'):
    return b.chain.laundry_action(cur,'POST_FINAL_SKU',dict(cutting_group_id=f['group'],destination_location_id=base.LOCATION,
      physical_at=b.chain.production.at(f['day'],hour).isoformat(),reason='P04 QC physical transition',good_qty_pcs=good,completion_mode=mode,
      lines=[dict(final_product_id=f['product'],qty_good_pcs=good,qty_bs_pcs=bs,source_laundry_receipt_line_id=f['receipt_line'],source_laundry_receipt_batch_size_line_id=f['receipt_size'])]),base.group_version(cur,f['group']))

def capture(cur,groups,key=None,subject=None):
    p02.actor(cur,subject)
    value=cur.execute('select public.erp_cp7_capture_cutting_wip_v1(%s::uuid[],%s)',(groups,key or uuid.uuid4())).fetchone()[0]
    b.api.admin(cur);return value

def read(cur,run,subject=None):
    p02.actor(cur,subject);value=cur.execute('select public.erp_cp7_read_cutting_wip_v1(%s)',(run,)).fetchone()[0];b.api.admin(cur);return value

def smoke(cur,today):
    def qualify():
        f=fixture(cur,today);r=capture(cur,[f['group']]);assert r['result']['status']=='COMPLETE',r
        assert [total(r['result'],k+'_pcs') for k in ('input','wip','fg','bs')]==[100,80,15,5],r
        return dict(status='PASS',actual_posting_fixture_qualified=True,expected_actual=[100,80,15,5])
    return [('P04_SOURCE_FIXTURE_SMOKE',qualify)]

def cases(cur,today):
    def actual():
        f=fixture(cur,today);before=b.boundary.snapshot(cur);r=capture(cur,[f['group']]);result=r['result']
        assert result['status']=='COMPLETE',r
        assert [total(result,k+'_pcs') for k in ('input','wip','fg','bs')]==[100,80,15,5]
        assert r['source_state']=='UNCHANGED' and before==b.boundary.snapshot(cur)
        # Accepted CP6 storage accumulates known cost separately from the UNKNOWN
        # business state; internal numeric 0 is not a tariff or a complete quote.
        unknown=cur.execute('select erp.bd_delivery_line_price_unknown_v1(delivery_line_id) from erp.laundry_receipt_lines where id=%s',(f['receipt_line'],)).fetchone()[0]
        assert unknown is True
        raw_cost=cur.execute('select actual_cost from erp.laundry_receipt_lines where id=%s',(f['receipt_line'],)).fetchone()[0]
        money_run=p02.create(cur,f['product']);money=p02.read(cur,money_run['run_id'],'lot_cost')
        assert money['page']['rows'] and all(x['valuation']['state']=='UNKNOWN' for x in money['page']['rows']),money
        return dict(status='PASS',ordinary_cut_pickup_sewing_laundry_qc=True,input=100,wip=80,fg=15,bs=5,unknown_cost_does_not_block_quantity=True,canonical_price_unknown=unknown,public_valuation='UNKNOWN',internal_known_cost=str(raw_cost),business_boundary_unchanged=True)
    def immutable():
        f=fixture(cur,today);key=uuid.uuid4();r=capture(cur,[f['group']],key)
        qc(cur,f,5,0,15)
        archive=read(cur,r['run_id']);assert archive['source_state']=='ARCHIVED_STALE' and archive['result']==r['result']
        assert capture(cur,[f['group']],key)['run_id']==r['run_id']
        new=capture(cur,[f['group']]);assert [total(new['result'],k+'_pcs') for k in ('input','wip','fg','bs')]==[100,75,20,5]
        p02.refused(cur,lambda:capture(cur,[uuid.uuid4()],key),'CP7_WIP_REQUEST_REUSED')
        p02.refused(cur,lambda:cur.execute('update cp7_wip.runs set result=%s::jsonb where id=%s',('{}',r['run_id'])),'CP7_RUN_IMMUTABLE')
        return dict(status='PASS',ordinary_later_qc_marks_stale=True,archive_and_replay_immutable=True,new_capture=[100,75,20,5])
    def access():
        f=fixture(cur,today);subject,role=p02.custom_actor(cur);r=capture(cur,[f['group']],subject=subject)
        p02.refused(cur,lambda:read(cur,r['run_id']),'CP7_WIP_RUN_UNAVAILABLE')
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,))
        p02.refused(cur,lambda:read(cur,r['run_id'],subject),'CP7_ACCESS_DENIED')
        p02.refused(cur,lambda:capture(cur,[f['group']],r['request_id'],subject),'CP7_ACCESS_DENIED')
        # All transport facts are operational; no nested tariff/HPP or financial aggregate.
        def keys(v):
            if isinstance(v,dict):
                for k,x in v.items():yield k;yield from keys(x)
            elif isinstance(v,list):
                for x in v:yield from keys(x)
        assert not set(keys(r))&{'actual_cost','unit_hpp_snapshot','amount','rate','margin','compensation_amount','lot_cost'}
        return dict(status='PASS',other_actor_and_revoked_replay_denied=True,no_financial_fields=True)
    def malformed():
        f=fixture(cur,today)
        for groups in ([],[f['group'],f['group']],[None]):p02.refused(cur,lambda:capture(cur,groups),'CP7_WIP_SCOPE')
        p02.refused(cur,lambda:capture(cur,[uuid.uuid4()]),'CP7_WIP_SOURCE_INCOMPLETE')
        assert cur.execute('select count(*) from cp7_wip.runs').fetchone()[0]==0
        return dict(status='PASS',no_partial_run=True,unknown_group_not_empty_supply=True)
    def conflict():
        f=fixture(cur,today);b.api.admin(cur);cur.execute('set local session_replication_role=replica')
        cur.execute('update erp.laundry_receipt_lines set qty_good_received=29 where id=%s',(f['receipt_line'],));cur.execute('set local session_replication_role=origin')
        r=capture(cur,[f['group']]);assert r['capture_complete'] and r['result']['status']=='CONFLICT' and r['result']['reason']=='RECEIPT_SIZE_TOTAL_MISMATCH',r
        assert 'totals' not in r['result']
        return dict(status='PASS',administrative_conflict_fixture=True,capture_not_mislabeled_as_analysis_complete=True,no_zero_balance_fallback=True)
    def rework_lifecycle():
        f=fixture(cur,today);b.api.admin(cur)
        bs=b.one(cur,"select id::text from erp.bs_cases where cutting_group_id=%s and qc_item_id is not null",f['group'])
        bom=b.one(cur,'select erp.resolve_rework_accessory_bom_v1(%s,%s)::text',bs,b.chain.production.at(f['day'],15))
        payload=dict(rework_number='P04-RW-'+uuid.uuid4().hex[:10],bs_case_id=bs,destination_type='LAUNDRY',
          contractor_id=None,vendor_id=f['vendor'],qty_sent=5,physical_sent_at=b.chain.production.at(f['day'],15).isoformat(),
          status='IN_PROGRESS',return_fg_location_id=base.LOCATION,accessory_bom_version_id=bom,accessory_bom_item_ids=[],components=[],change_reason='P04 actual rework lifecycle')
        made=b.chain.bs_action(cur,'SAVE_REWORK',payload);rid=made['result']['rework_order_id']
        pending=capture(cur,[f['group']]);assert [total(pending['result'],k+'_pcs') for k in ('input','wip','fg','bs')]==[100,85,15,0]
        b.chain.bs_action(cur,'SAVE_REWORK',dict(id=rid,qty_good_returned=2,qty_bs_returned=1,change_reason='Cumulative return still not posted FG'),b.chain.version(cur,'rework_orders',rid))
        partial=capture(cur,[f['group']]);assert [total(partial['result'],k+'_pcs') for k in ('input','wip','fg','bs')]==[100,85,15,0]
        b.api.admin(cur);assert b.one(cur,'select good_fg_lot_id is null from erp.rework_orders where id=%s',rid)
        b.chain.bs_action(cur,'COMPLETE_REWORK',dict(rework_order_id=rid,qty_good=3,qty_bs=2,completed_at=b.chain.production.at(f['day'],16).isoformat(),
          return_fg_location_id=base.LOCATION,change_reason='Three GOOD and two BS final'),b.chain.version(cur,'rework_orders',rid))
        complete=capture(cur,[f['group']]);assert [total(complete['result'],k+'_pcs') for k in ('input','wip','fg','bs')]==[100,80,18,2]
        return dict(status='PASS',ordinary_rework_start_partial_complete=True,partial_good_not_fg=True,final=[100,80,18,2])
    def rewash_lifecycle():
        f=b.two_size_fixture(cur,b.case_day(today),'P04-REWASH',q1=60,q2=40)
        # Accepted POST_FAILED_WASH requires exactly one vendor/process rate.
        # This qualifies known vendor pricing only; ordinary deferred-price
        # sending/receipt/QC is independently covered by O15 above.
        b.process_rate(cur,f,'5.00')
        def send(qty,hour):
            payload=dict(distribution_batch_id=f['batch'],vendor_id=f['vendor'],wash_process_id=f['process'],target_dyeing_color='P04-REWASH',
              physical_at=b.chain.production.at(f['day'],hour).isoformat(),reason='Same source redispatch',lines=[dict(size_id=base.SIZE,qty_sent_pcs=qty)])
            result=b.bd(cur,'POST_PRICED_DELIVERY',dict(delivery=payload,expected_version=str(base.group_version(cur,f['group'])),pricing=dict(deferred=True)))
            b.api.admin(cur);delivery=result['delivery_id']
            size=b.one(cur,'select s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where l.delivery_id=%s',delivery)
            return delivery,size
        first,first_size=send(40,11)
        b.chain.laundry_action(cur,'POST_FAILED_WASH',dict(delivery_id=first,wash_process_id=f['process'],custody_outcome='RETURN_UNPROCESSED',
          physical_at=b.chain.production.at(f['day'],12).isoformat(),reason='All forty returned unprocessed',lines=[dict(delivery_batch_size_line_id=first_size,qty_attempted_pcs=40)]),base.delivery_version(cur,first))
        back=capture(cur,[f['group']]);assert total(back['result'],'wip_pcs')==100 and back['result']['rewash_review_required'],back
        second,second_size=send(20,13)
        for hour in (14,15):
            b.chain.laundry_action(cur,'POST_FAILED_WASH',dict(delivery_id=second,wash_process_id=f['process'],custody_outcome='RETRY_AT_VENDOR',
              physical_at=b.chain.production.at(f['day'],hour).isoformat(),reason='Repeated attempt is same five pieces',lines=[dict(delivery_batch_size_line_id=second_size,qty_attempted_pcs=5)]),base.delivery_version(cur,second))
        waiting=capture(cur,[f['group']]);assert total(waiting['result'],'wip_pcs')==100,waiting
        rec=b.chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=second,wash_process_id=f['process'],physical_at=b.chain.production.at(f['day'],16).isoformat(),
          reason='Twenty physical pieces returned once',lines=[dict(delivery_batch_size_line_id=second_size,qty_good_received=20,qty_bs_laundry=0,bs_product_id=None)]),base.delivery_version(cur,second))
        b.api.admin(cur);f['receipt_line']=b.receipt_line(cur,rec['receipt_id']);f['receipt_size']=b.one(cur,'select id::text from erp.laundry_receipt_batch_size_lines where receipt_line_id=%s',f['receipt_line'])
        f['product']=b.sized_product(cur,base.SIZE,'P04-REWASH-'+uuid.uuid4().hex[:8]);qc(cur,f,20,0,17,mode='ALL_READY')
        final=capture(cur,[f['group']]);assert [total(final['result'],k+'_pcs') for k in ('input','wip','fg','bs')]==[100,80,20,0],final
        # A duplicated participant interval cannot publish a plausible aggregate.
        b.api.admin(cur);facts=cur.execute('select facts from cp7_wip.runs where id=%s',(final['run_id'],)).fetchone()[0]
        alloc=next(x for x in facts['facts']['redispatch'] if x['event_type']=='ALLOCATE');clone=dict(alloc,id=str(uuid.uuid4()))
        facts['facts']['redispatch'].append(clone)
        blocked=cur.execute('select cp7_wip.normalize_cutting(%s::jsonb)',(json.dumps(facts),)).fetchone()[0]
        assert blocked['status']=='CONFLICT' and blocked['reason']=='REDISPATCH_RANGE_LINEAGE_CONFLICT'
        return dict(status='PASS',ordinary_return_redispatch_and_retries=True,failed_wash_vendor_rate='5.00',unknown_failed_wash_not_qualified=True,final=[100,80,20,0],same_source_not_new_input=True,overlapping_participant_interval_denied=True)
    def claims():
        f=fixture(cur,today);ids=[]
        for kind,qty in [('MISSING',2),('STUCK',3)]:
            name='P04-'+kind+'-'+uuid.uuid4().hex[:8]
            b.d12_bs(cur,'SAVE_CLAIM',dict(action='SAVE',claim_number=name,vendor_id=f['vendor'],delivery_id=f['delivery'],
              qty_claimed=qty,claim_type=kind,compensation_amount=0,
              opened_at=b.chain.production.at(f['day'],15).isoformat(),change_reason='P04 physical unreturned custody'))
            ids.append(b.one(cur,'select id::text from erp.laundry_claims where claim_number=%s',name))
        r=capture(cur,[f['group']]);assert [total(r['result'],k+'_pcs') for k in ('input','wip','fg','bs','withheld')]==[100,75,15,5,5],r
        b.d12_bs(cur,'SAVE_CLAIM',dict(id=ids[0],action='REJECT',change_reason='Missing classification recorded in error; remains outstanding'),b.one(cur,'select row_version from erp.laundry_claims where id=%s',ids[0]))
        old=read(cur,r['run_id']);assert old['source_state']=='ARCHIVED_STALE' and old['result']==r['result']
        now=capture(cur,[f['group']]);assert [total(now['result'],k+'_pcs') for k in ('input','wip','fg','bs','withheld')]==[100,77,15,5,3],now
        # The source cannot use a single visible line to assign a header claim
        # whose delivery actually contains additional lines outside this scope.
        b.api.admin(cur);facts=cur.execute('select facts from cp7_wip.runs where id=%s',(now['run_id'],)).fetchone()[0]
        item=next(x for x in facts['facts']['claims'] if x['status']!='REJECTED');item['receipt_line_id']=None;item['delivery_line_count']=2
        unknown=cur.execute('select cp7_wip.normalize_cutting(%s::jsonb)',(json.dumps(facts),)).fetchone()[0]
        assert unknown['status']=='UNKNOWN' and unknown['reason']=='CLAIM_EXACT_SIZE_OR_SOURCE_UNPROVEN'
        return dict(status='PASS',ordinary_missing_and_stuck=True,held=5,rejection_refreshed_not_rewritten=True,hidden_header_source_not_guessed=True)
    def bs_disposition():
        f=fixture(cur,today);b.api.admin(cur)
        case=b.one(cur,'select id::text from erp.bs_cases where cutting_group_id=%s and qc_item_id is not null',f['group'])
        def action(kind,**payload):
            return b.chain.bs_action(cur,kind,dict(payload,change_reason='P04 BS custody lifecycle'),b.chain.version(cur,'bs_cases',case))
        action('HOLD_BS',bs_case_id=case,physical_at=b.chain.production.at(f['day'],15).isoformat())
        held=capture(cur,[f['group']]);assert [total(held['result'],k+'_pcs') for k in ('input','wip','fg','bs','withheld','exited')]==[100,80,15,0,5,0],held
        action('RELEASE_HOLD',bs_case_id=case,physical_at=b.chain.production.at(f['day'],16).isoformat())
        released=capture(cur,[f['group']]);assert total(released['result'],'bs_pcs')==5 and total(released['result'],'withheld_pcs')==0,released
        disposed=action('DISPOSE_BS',bs_case_id=case,resolution_type='SCRAP',qty_pcs=2,physical_at=b.chain.production.at(f['day'],17).isoformat())
        scrap=capture(cur,[f['group']]);assert [total(scrap['result'],k+'_pcs') for k in ('input','wip','fg','bs','withheld','exited')]==[100,80,15,3,0,2],scrap
        action('REVERSE_DISPOSITION',resolution_id=disposed['result']['bs_resolution_id'])
        restored=capture(cur,[f['group']]);assert total(restored['result'],'bs_pcs')==5 and total(restored['result'],'exited_pcs')==0,restored
        assert read(cur,scrap['run_id'])['source_state']=='ARCHIVED_STALE' and read(cur,held['run_id'])['result']==held['result']
        return dict(status='PASS',ordinary_hold_release_scrap_reverse=True,held=5,scrap_exit=2,restored_bs=5,no_extra_good=True,old_results_immutable=True)
    def attention():
        f=fixture(cur,today)
        def flag(payload,version=None):
            b.chain.production.owner(cur)
            v=cur.execute('select public.erp_set_wip_control_flag_v1(%s::jsonb,%s,%s)',(json.dumps(payload),uuid.uuid4(),version)).fetchone()[0]
            b.api.admin(cur);return v
        payload=dict(cutting_group_id=f['group'],flag_type='PENDING_CORRECTION',note='Check physical reconciliation',change_reason='P04 actual attention flag')
        mark=flag(payload);r=capture(cur,[f['group']]);assert r['result']['allocation_review_required'] and total(r['result'],'wip_pcs')==80
        a=dict(scenario_id='P04-FLAG',scope_id=r['run_id'],complete_scope=True,edges=[])
        checked=cur.execute('select cp7_wip.check_allocations(%s::jsonb,%s::jsonb)',(json.dumps(r['result']),json.dumps(a))).fetchone()[0]
        assert checked==dict(status='UNKNOWN',reason='SOURCE_REVIEW_REQUIRED')
        flag(dict(payload,id=mark['flag_id'],status='RESOLVED'),mark['row_version'])
        now=capture(cur,[f['group']]);assert not now['result']['allocation_review_required']
        assert read(cur,r['run_id'])['source_state']=='ARCHIVED_STALE'
        return dict(status='PASS',ordinary_flag_changes_dependency=True,quantity_preserved=80,allocation_requires_review=True,resolution_does_not_rewrite_archive=True)
    def multi_scope():
        f=fixture(cur,today);other=b.two_size_fixture(cur,b.case_day(today),'P04-OTHER',q1=6,q2=4)
        r=capture(cur,[other['group'],f['group']]);assert [total(r['result'],k+'_pcs') for k in ('input','wip','fg','bs')]==[110,90,15,5]
        assert len(r['result']['totals'])==4 and len({x['pool_key'] for x in r['result']['totals']})==4
        return dict(status='PASS',one_capture_multiple_groups=True,input=110,wip=90,fg=15,bs=5)
    return [('P04_SOURCE_'+name,fn) for name,fn in [('O15_ACTUAL_POSTING',actual),('IMMUTABLE_QC_REPLAY',immutable),('AUTH_NO_MONEY',access),('MALFORMED_NO_PARTIAL',malformed),('CONFLICT_PROPAGATES',conflict),('MULTI_GROUP_ONE_CAPTURE',multi_scope),('REWORK_PARTIAL_COMPLETION',rework_lifecycle),('REWASH_RETURN_REDISPATCH',rewash_lifecycle),('CLAIM_CUSTODY',claims),('BS_HOLD_DISPOSITION',bs_disposition),('SOURCE_REVIEW_FLAG',attention)]]

def http_cases(http,today):
    def auth():
        owner=http.login('OWNER','p04-owner');other=http.login('OWNER','p04-other')
        with http.connect() as conn,conn.cursor() as cur:f=fixture(cur,today);conn.commit()
        args=dict(p_groups=[f['group']],p_request=str(uuid.uuid4()))
        r=owner.rpc('erp_cp7_capture_cutting_wip_v1',args);assert r['status']==200 and r['body']['result']['status']=='COMPLETE',r
        run=r['body']['run_id'];assert total(r['body']['result'],'wip_pcs')==80
        assert owner.rpc('erp_cp7_capture_cutting_wip_v1',args)['body']['run_id']==run
        assert other.rpc('erp_cp7_read_cutting_wip_v1',dict(p_run=run))['status']==403
        assert http.anon_rpc('erp_cp7_read_cutting_wip_v1',dict(p_run=run))['status'] in (401,403,404)
        with http.connect() as conn,conn.cursor() as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_capture_cutting_wip_v1',args)['status']==403
        return dict(status='PASS',real_auth=True,ordinary_posting_result=[100,80,15,5],same_token_revoked=True,other_actor_denied=True)
    return [('P04_HTTP_CUTTING_RUN_AUTH',auth)]

def races(tools,today):
    def duplicate():
        with tools.connect() as conn,conn.cursor() as cur:f=fixture(cur,today);conn.commit()
        key=uuid.uuid4();start=threading.Barrier(2)
        def run():
            with tools.connect() as conn,conn.cursor() as cur:start.wait(timeout=5);r=capture(cur,[f['group']],key);conn.commit();return r['run_id']
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(run);c=pool.submit(run);ids=[a.result(timeout=20),c.result(timeout=20)]
        assert ids[0]==ids[1]
        with tools.connect() as conn,conn.cursor() as cur:assert cur.execute('select count(*) from cp7_wip.runs').fetchone()[0]==1
        return dict(status='PASS',one_immutable_run=True)
    def coherent():
        with tools.connect() as conn,conn.cursor() as cur:f=fixture(cur,today);conn.commit()
        active=threading.Event();done=threading.Event();values=[];overlap=0
        def writer():
            with tools.connect() as conn,conn.cursor() as cur:
                active.set()
                # Atomic administrative correction to two coupled source fields;
                # this probes MVCC only, not permission to edit posted facts.
                for i in range(20):
                    n=29 if i%2==0 else 30
                    cur.execute('set local session_replication_role=replica')
                    cur.execute('update erp.laundry_receipt_lines set qty_good_received=%s where id=%s',(n,f['receipt_line']))
                    cur.execute('update erp.laundry_receipt_batch_size_lines set qty_good_received=%s where id=%s',(n,f['receipt_size']))
                    cur.execute('set local session_replication_role=origin');conn.commit();time.sleep(.02)
            done.set()
        with ThreadPoolExecutor(max_workers=1) as pool:
            w=pool.submit(writer);assert active.wait(5)
            with tools.connect() as conn,conn.cursor() as cur:
                for _ in range(12):
                    r=capture(cur,[f['group']]);v=cur.execute('select facts from cp7_wip.runs where id=%s',(r['run_id'],)).fetchone()[0]['facts'];conn.commit()
                    values.append((int(v['receipts'][0]['good_pcs']),int(v['receipt_sizes'][0]['good_pcs'])))
                    assert r['result']['status']=='COMPLETE',r
                    if not done.is_set():overlap+=1
            w.result(timeout=20)
        assert set(values)<={(29,29),(30,30)} and overlap>0,(values,overlap)
        return dict(status='PASS',paired_sources_one_snapshot=True,captures=12,overlap=overlap,observed_pairs=sorted(set(values)))
    return [('P04_RACE_DUPLICATE',duplicate),('P04_RACE_SOURCE_COHERENCE',coherent)]

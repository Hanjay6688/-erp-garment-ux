"""Independent F02 cases; uses accepted fixture builders, not writer expectations."""
from pathlib import Path
from copy import deepcopy
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import sys,json,uuid,time,threading
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import psycopg
import cp7_p04_wip_probe as runner
import cp7_identity_cases as ident
import cp7_wip_cases as kernel
import cp7_wip_source_cases as cut
import cp7_wip_production_cases as prod
import cp7_snapshot_cases as p02
import cp6_auditor_modes as modes
b=cut.b;base=cut.base


def refs(k):return [dict(kind='AUD_F02_ORACLE',id=k,revision='1')]
def graph(q=17):
    return dict(contract_version='cp7.wip-graph.v1',snapshot_id='auditor-17',complete=True,
      pools=[dict(key='origin',size_id='XS',input_pcs=str(q),origin='CUTTING',ownership='COMPANY',refs=refs('physical-origin'))],
      nodes=[dict(key=k,pool_key='origin',stage=stage,refs=refs(k)) for k,stage in [('sew','SEWING_ACTIVE'),('fg','FG'),('bs','BS'),('rw','REWORK'),('hold','HOLD')]],events=[])
def event(g,src,dst,q,reverse=None):
    n=str(len(g['events'])+1);g['events'].append(dict(key='e'+n,pool_key='origin',from_node=src,to_node=dst,qty_pcs=str(q),ordinal=n,reverses_key=reverse,refs=refs('e'+n)))
def physical(cur,q=17):
    g=graph(q);event(g,None,'sew',q);return kernel.call(cur,'reconcile',g)
def project(cur,p,qty,num=1,den=1):
    return kernel.call(cur,'yield',p,[dict(position_key='sew',eligible_input_pcs=str(qty),numerator=str(num),denominator=str(den),basis='ASSUMED',assumption_id='auditor-yield',refs=refs('yield'))])
def edge(k,q,out,target='target'):
    return dict(key=k,position_key='sew',target_key=target,size_id='XS',input_pcs=str(q),projected_good_pcs=str(out),match='CANDIDATE_MATCH',refs=refs(k))
def alloc(cur,p,edges):return kernel.call(cur,'allocate',p,dict(scenario_id='auditor',scope_id='ALL',complete_scope=True,edges=edges))
def actual_vector(r):
    v=r.get('result',r)
    return [kernel.total(v,k+'_pcs') for k in ('input','wip','fg','bs','withheld','exited')] if v.get('status')=='COMPLETE' else dict(status=v.get('status'),reason=v.get('reason'),component=v.get('component'))
def verdict(expected,actual,**detail):return dict(status='PASS' if actual==expected else 'COUNTEREXAMPLE',expected=expected,actual=actual,**detail)
def qc_reverse(cur,f):
    b.api.admin(cur);qid=b.one(cur,"select q.id::text from erp.qc_inspections q join erp.qc_inspection_items i on i.inspection_id=q.id where i.cutting_group_id=%s and q.status='POSTED' order by q.physical_at desc limit 1",f['group'])
    b.chain.laundry_action(cur,'REVERSE_FINAL_SKU',dict(qc_inspection_id=qid,reason='Independent F02 restore source before re-QC'),b.chain.version(cur,'qc_inspections',qid))
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
        b.chain.laundry_action(cur,'REVERSE_RECEIPT',dict(receipt_id=f['receipt'],reason='Independent F02 reverse now-unconsumed receipt'),b.chain.version(cur,'laundry_receipts',f['receipt']))
        z=prod.capture(cur,prod.scope(groups=[f['group']]))
        assert actual_vector(z)==[100,100,0,0,0,0],z
        assert cut.read(cur,old['run_id'])['source_state']=='ARCHIVED_STALE'
        return dict(status='PASS',ordinary_good_only_qc_then_receipt_reversal=True,expected_actual=[100,100,0,0,0,0])
    def reverse_receipt_bs():
        f=cut.fixture(cur,today,False)
        ds=b.one(cur,'select s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where l.delivery_id=%s',f['delivery'])
        rec=b.chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=f['delivery'],wash_process_id=f['process'],physical_at=b.chain.production.at(f['day'],14).isoformat(),reason='Independent receipt with five BS',lines=[dict(delivery_batch_size_line_id=ds,qty_good_received=5,qty_bs_laundry=5,bs_product_id=f['product'])]),base.delivery_version(cur,f['delivery']))
        old=prod.capture(cur,prod.scope(groups=[f['group']]));assert actual_vector(old)==[100,95,0,5,0,0],old
        b.chain.laundry_action(cur,'REVERSE_RECEIPT',dict(receipt_id=rec['receipt_id'],reason='Independent undo receipt containing BS'),b.chain.version(cur,'laundry_receipts',rec['receipt_id']))
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
    def graph_conservation():
        g=graph();event(g,None,'sew',17);event(g,'sew','fg',4);event(g,'sew','bs',3)
        a=kernel.call(cur,'reconcile',g);assert actual_vector(a)==[17,10,4,3,0,0]
        event(g,'bs','rw',3);event(g,'rw','fg',2);event(g,'rw','bs',1)
        z=kernel.call(cur,'reconcile',g);assert actual_vector(z)==[17,10,6,1,0,0]
        event(g,'fg','rw',2,'e5');event(g,'bs','rw',1,'e6');event(g,'rw','bs',3,'e4')
        back=kernel.call(cur,'reconcile',g);assert actual_vector(back)==[17,10,4,3,0,0]
        event(g,'sew','fg',11);bad=kernel.call(cur,'reconcile',g);assert bad['reason']=='NEGATIVE_PREFIX'
        return dict(status='PASS',independent_17pcs_oracle=True,after_rework=[17,10,6,1,0,0],inverse_restores_original=True)
    def yield_matrix():
        checks=[]
        for qty,num,den in [(1,0,1),(1,2,3),(2,2,3),(7,3,7),(101,9,10),(9007199254740993,2,3),(999999999999999999999999999999,999999999999999999999999999998,999999999999999999999999999999)]:
            p=physical(cur,qty);r=project(cur,p,qty,num,den);expected=qty*num//den
            got=next(x for x in r['positions'] if x['key']=='sew')['projection']
            assert int(got['projected_good_pcs'])==expected and int(got['expected_loss_pcs'])==qty-expected,got
            assert alloc(cur,r,[edge('e',qty,expected)])['status']=='FEASIBLE'
            if expected<qty:assert alloc(cur,r,[edge('e',qty,expected+1)])['status']=='INFEASIBLE'
            checks.append(dict(input=str(qty),numerator=str(num),denominator=str(den),expected_output=str(expected)))
        return dict(status='PASS',exact_integer_oracles=checks,physical_totals_unchanged=True)
    def malformed_pcs():
        for value in ('-1','0.5','1e2','NaN','Infinity','01',' 1',1,None,'1'*31):
            g=graph();g['pools'][0]['input_pcs']=value
            p02.refused(cur,lambda:kernel.call(cur,'reconcile',g),'CP7_WIP_PCS')
        return dict(status='PASS',malformed_physical_counts_refused=10)
    def shared_edges():
        p=project(cur,physical(cur,17),13,2,3)
        assert alloc(cur,p,[edge('a',6,4,'A'),edge('b',7,4,'B')])['status']=='FEASIBLE'
        over=alloc(cur,p,[edge('a',7,4,'A'),edge('b',7,4,'B')]);assert over['status']=='INFEASIBLE' and any(v['kind']=='ELIGIBLE_INPUT' for v in over['violations'])
        p02.refused(cur,lambda:alloc(cur,p,[edge('same',1,0),edge('same',1,0)]),'CP7_WIP_DUPLICATE_ALLOCATION')
        for match in ('UNKNOWN','NEEDS_CHECK','INCOMPATIBLE'):
            e=edge('a',1,0);e['match']=match;p02.refused(cur,lambda:alloc(cur,p,[e]),'CP7_WIP_INELIGIBLE_ALLOCATION')
        return dict(status='PASS',physical=17,eligible=13,valid_inputs=[6,7],invalid_inputs=[7,7],duplicate_and_uncertain_edges_refused=True)
    def eta_boundaries():
        def stage(key,minutes,windows):return dict(stage=key,remaining_minutes=str(minutes),basis='CONFIRMED_PLAN',assumption_id=None,calendar_version=key+'-v1',windows=[dict(start=a,end=z) for a,z in windows],refs=refs(key))
        work=[stage('sew',30,[('2026-09-29T09:00:00+07:00','2026-09-29T09:30:00+07:00')]),stage('QC',45,[('2026-09-29T09:15:00+07:00','2026-09-29T10:00:00+07:00'),('2026-09-29T11:00:00+07:00','2026-09-29T12:00:00+07:00')])]
        a=kernel.call(cur,'eta','2026-09-29T09:00:00+07:00','2026-09-29T11:15:00+07:00',work)
        assert a['eta']=='2026-09-29T04:15:00+00:00' and a['on_time'] is True,a
        z=kernel.call(cur,'eta','2026-09-29T09:00:00+07:00','2026-09-29T11:14:59+07:00',work);assert z['on_time'] is False
        broken=deepcopy(work);broken[1]['windows'][1]['start']='2026-09-29T09:45:00+07:00'
        p02.refused(cur,lambda:kernel.call(cur,'eta','2026-09-29T09:00:00+07:00','2026-09-29T12:00:00+07:00',broken),'CP7_WIP_TIMING_OVERLAP')
        broken=deepcopy(work);broken[1]['windows']=[]
        u=kernel.call(cur,'eta','2026-09-29T09:00:00+07:00','2026-09-29T12:00:00+07:00',broken);assert u['status']=='UNKNOWN' and u['eta'] is None and u['on_time'] is None
        return dict(status='PASS',sequential_remaining_work_finishes='2026-09-29T11:15:00+07:00',exact_deadline_boundary=True,overlap_denied=True,exhausted_horizon_unknown=True)
    def policy_cycles():
        f=ident.fixture(cur,today);before=b.boundary.snapshot(cur);history=[]
        for state in ('ACTIVE','PAUSED','STOPPED','ACTIVE'):
            row=ident.row(ident.get(cur,f['skus']),f['skus'][0]);p=ident.proposal(row,state,cur.execute("select clock_timestamp()-interval '2 days'").fetchone()[0])
            ident.apply(cur,[p]);v=ident.row(ident.get(cur,f['skus']),f['skus'][0]);assert v['policy']['state']==state and v['policy']['review_due'];history.append(state)
        assert b.boundary.snapshot(cur)==before
        assert [r[0] for r in cur.execute('select state from cp7_identity.production_policy order by revision').fetchall()]==history
        assert ident.row(ident.get(cur,f['skus']),f['skus'][1])['policy']['quality']=='UNREVIEWED'
        return dict(status='PASS',explicit_status_history=history,erp_business_boundary_unchanged=True)
    def bulk_and_exact_revision():
        f=ident.fixture(cur,today);ws=ident.get(cur,f['skus']);a=ident.proposal(ident.row(ws,f['skus'][0]));z=ident.proposal(ident.row(ws,f['skus'][1]))
        bads=[dict(z,review_at='infinity'),dict(z,members=z['members']*2),dict(z,state='STOP'),dict(z,reason=' '),dict(z,policy_revision='01')]
        for bad in bads:
            p02.refused(cur,lambda:ident.apply(cur,[a,bad]),'CP7_POLICY_')
            assert cur.execute('select count(*) from cp7_identity.production_policy').fetchone()[0]==0
            assert cur.execute('select count(*) from cp7_identity.commands').fetchone()[0]==0
        ident.apply(cur,[a]);cur.execute("insert into cp7_identity.production_policy select (jsonb_populate_record(null::cp7_identity.production_policy,to_jsonb(p)||jsonb_build_object('id',gen_random_uuid(),'request_id',gen_random_uuid(),'revision',9007199254740993))).* from cp7_identity.production_policy p limit 1")
        fresh=ident.proposal(ident.row(ident.get(cur,f['skus']),f['skus'][0]),'PAUSED');assert fresh['policy_revision']=='9007199254740993'
        result=ident.apply(cur,[fresh]);assert result['applied'][0]['revision']=='9007199254740994'
        return dict(status='PASS',late_invalid_rows_rollback_entire_bulk=5,exact_revision='9007199254740994',revision_seed_is_administrative=True)
    def source_limits():
        fifty=prod.scope(groups=[str(uuid.uuid4()) for _ in range(20)],items=[str(uuid.uuid4()) for _ in range(20)],cases=[str(uuid.uuid4()) for _ in range(10)])
        normalized=cur.execute('select cp7_wip.production_scope(%s::jsonb)',(json.dumps(fifty),)).fetchone()[0];assert sum(map(len,normalized.values()))==50
        fifty['unsourced_bs'].append(str(uuid.uuid4()));p02.refused(cur,lambda:cur.execute('select cp7_wip.production_scope(%s::jsonb)',(json.dumps(fifty),)),'CP7_WIP_SCOPE')
        f=cut.fixture(cur,today);n=cur.execute('select count(*) from erp.sewing_terminal_events where cutting_group_id=%s',(f['group'],)).fetchone()[0];assert 0<n<2000
        cur.execute('set local session_replication_role=replica')
        cur.execute("insert into erp.sewing_terminal_events select (jsonb_populate_record(null::erp.sewing_terminal_events,to_jsonb(s)||jsonb_build_object('id',gen_random_uuid(),'event_number','AUD-F02-'||gen_random_uuid(),'source_work_completion_id',null))).* from (select * from erp.sewing_terminal_events where cutting_group_id=%s limit 1) s cross join generate_series(1,%s)",(f['group'],2000-n))
        cur.execute('set local session_replication_role=origin')
        r=prod.capture(cur,prod.scope(groups=[f['group']]));assert r['capture_complete'] and actual_vector(r)==[100,80,15,5,0,0]
        count=cur.execute('select jsonb_array_length(facts->\'facts\'->\'cutting\'->\'sewing\') from cp7_wip.production_runs where id=%s',(r['run_id'],)).fetchone()[0];assert count==2000
        cur.execute('set local session_replication_role=replica')
        cur.execute("insert into erp.sewing_terminal_events select (jsonb_populate_record(null::erp.sewing_terminal_events,to_jsonb(s)||jsonb_build_object('id',gen_random_uuid(),'event_number','AUD-F02-'||gen_random_uuid(),'source_work_completion_id',null))).* from erp.sewing_terminal_events s where cutting_group_id=%s limit 1",(f['group'],));cur.execute('set local session_replication_role=origin')
        p02.refused(cur,lambda:prod.capture(cur,prod.scope(groups=[f['group']])),'CP7_WIP_SOURCE_INCOMPLETE')
        assert cur.execute('select count(*) from cp7_wip.production_runs').fetchone()[0]==1
        return dict(status='PASS',scope_parser_50_allowed_51_refused=True,source_2000_complete_2001_refused=True,administrative_bounded_source_fixture=True)
    def opening_conflict():
        f=prod.opening(cur,today);s=prod.scope(items=[f['item']]);old=prod.capture(cur,s)
        cur.execute('set local session_replication_role=replica');cur.execute('update erp.opening_balance_items set qty=9 where id=%s',(f['item'],));cur.execute('set local session_replication_role=origin')
        new=prod.capture(cur,s);assert new['result']['status']=='CONFLICT' and new['result']['reason']=='OPENING_ORIGIN_QUANTITY_MISMATCH',new
        assert prod.read(cur,old['run_id'])['result']==old['result'] and prod.read(cur,old['run_id'])['source_state']=='ARCHIVED_STALE'
        return dict(status='PASS',administrative_mismatched_source_not_ready=True,archive_preserved=True)
    def private_principals():
        business=cur.execute("select r.role,n.nspname,c.relname from (values('cp7_capture'),('cp7_policy')) r(role) cross join pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp' and c.relkind in ('r','p','v') and has_table_privilege(r.role,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')").fetchall();assert not business,business
        assert not cur.execute("select has_table_privilege('cp7_capture','cp7_identity.production_policy','INSERT,UPDATE,DELETE')").fetchone()[0]
        for role in ('anon','authenticated','service_role'):
            for schema in ('cp7_identity','cp7_wip'):
                assert not cur.execute('select has_schema_privilege(%s,%s,\'USAGE\')',(role,schema)).fetchone()[0]
                assert cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname=%s and has_function_privilege(%s,p.oid,'EXECUTE')",(schema,role)).fetchone()[0]==0
        return dict(status='PASS',both_principals_have_no_business_write_grants=True,compute_cannot_write_policy=True,private_helpers_no_public_grants=True)
    own=[('QC_BS_REVERSAL',reverse_qc_bs),('GOOD_ONLY_REVERSAL_CONTROL',reverse_qc_control),('LAUNDRY_BS_REVERSAL',reverse_receipt_bs),('REWORK_COMPLETION_REVERSE',reverse_rework),('GRAPH17_CONSERVATION_INVERSE',graph_conservation),('EXACT_YIELD_MATRIX',yield_matrix),('MALFORMED_COUNTS',malformed_pcs),('SHARED_ELIGIBLE_EDGES',shared_edges),('ETA_BOUNDARIES',eta_boundaries),('EXPLICIT_POLICY_CYCLES',policy_cycles),('BULK_INVALID_AND_BIGINT',bulk_and_exact_revision),('SCOPE_AND_SOURCE_LIMITS',source_limits),('OPENING_CONTROL_CONFLICT',opening_conflict),('PRIVILEGED_PRINCIPALS',private_principals)]
    inherited=ident.cases(cur,today)+kernel.cases(cur,today)+cut.cases(cur,today)+prod.cases(cur,today)
    return [('AUD_F02_'+k,f) for k,f in own]+[('WRITER_RERUN_'+k,f) for k,f in inherited]


def races(tools,today):
    def wait_capture(revoke=False,existing=False):
        with tools.connect() as conn,conn.cursor() as cur:
            f=cut.fixture(cur,today);subject,role=p02.custom_actor(cur);s=prod.scope(groups=[f['group']]);key=str(uuid.uuid4())
            old=prod.capture(cur,s,key,subject) if existing else None;conn.commit()
        with tools.connect() as holder,holder.cursor() as h:
            h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:PRODUCTION:'||%s||':'||%s,0))",(subject,key))
            def wait():
                with tools.connect() as conn,conn.cursor() as cur:
                    try:r=prod.capture(cur,s,key,subject);conn.commit();return r
                    except psycopg.Error as exc:conn.rollback();return str(exc).splitlines()[0]
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(wait)
                try:
                    with tools.connect(autocommit=True) as conn,conn.cursor() as cur:
                        deadline=time.monotonic()+10;blocked=False
                        while time.monotonic()<deadline:
                            cur.execute('select pg_stat_clear_snapshot()');blocked=cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database() and wait_event='advisory' and pid<>pg_backend_pid())").fetchone()[0]
                            if blocked:break
                            time.sleep(.03)
                        assert blocked,'REAL_PRODUCTION_REQUEST_WAIT_NOT_OBSERVED'
                    with tools.connect() as conn,conn.cursor() as cur:
                        if revoke:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.stock.view'",(role,))
                        else:cut.qc(cur,f,5,0,15)
                        conn.commit()
                finally:holder.rollback()
                result=future.result(timeout=20)
        if revoke:
            assert isinstance(result,str) and 'CP7_ACCESS_DENIED' in result,result
            with tools.connect() as conn,conn.cursor() as cur:assert cur.execute('select count(*) from cp7_wip.production_runs').fetchone()[0]==int(existing)
            return dict(status='PASS',revoked_during_real_wait=True,existing_replay=existing,result=result)
        assert actual_vector(result)==[100,75,20,5,0,0],result
        return dict(status='PASS',ordinary_qc_commit_while_waiting_included=True,expected_actual=[100,75,20,5,0,0])
    def reverse_order_bulk():
        with tools.connect() as conn,conn.cursor() as cur:
            f=ident.fixture(cur,today);ws=ident.get(cur,f['skus']);changes=[ident.proposal(ident.row(ws,k)) for k in f['skus']];conn.commit()
        barrier=threading.Barrier(2)
        def save(items):
            with tools.connect() as conn,conn.cursor() as cur:
                cur.execute("set local statement_timeout='12s'");barrier.wait(timeout=5)
                try:ident.apply(cur,items);conn.commit();return 'COMMITTED'
                except psycopg.Error as exc:conn.rollback();return str(exc).splitlines()[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            a=pool.submit(save,changes);z=pool.submit(save,list(reversed(changes)));results=[a.result(timeout=20),z.result(timeout=20)]
        assert results.count('COMMITTED')==1 and results.count('CP7_POLICY_VERSION_STALE')==1,results
        with tools.connect() as conn,conn.cursor() as cur:assert cur.execute('select count(*),count(distinct request_id) from cp7_identity.production_policy').fetchone()==(2,1)
        return dict(status='PASS',opposite_bulk_order_no_deadlock=True,one_atomic_winner=True)
    own=[('CAPTURE_COMMIT_AFTER_WAIT',lambda:wait_capture()),('CAPTURE_REVOKE_AFTER_WAIT',lambda:wait_capture(True)),('REPLAY_REVOKE_AFTER_WAIT',lambda:wait_capture(True,True)),('OPPOSITE_BULK_ORDER',reverse_order_bulk)]
    return [('AUD_F02_'+k,f) for k,f in own]+[('WRITER_RERUN_'+k,f) for k,f in ident.races(tools,today)+cut.races(tools,today)+prod.races(tools,today)]


def http_cases(http,today):
    def private_rest():
        owner=http.login('OWNER','f02-private');results=[]
        for schema in ('cp7_identity','cp7_wip'):
            for token in (None,owner._token):
                h={'apikey':http._anon,'Authorization':'Bearer '+(token or http._anon),'Content-Profile':schema}
                r=modes._call(modes.REST_URL+'/rpc/'+('apply_policy' if schema=='cp7_identity' else 'reconcile'),{},h)
                assert r['status'] in (400,401,403,404,406),r;results.append(dict(schema=schema,status=r['status']))
        return dict(status='PASS',direct_private_rest_denied=results)
    def ops_scope():
        op=http.login('ADMIN','f02-ops');other=http.login('OWNER','f02-other')
        with http.connect() as conn,conn.cursor() as cur:
            f=prod.opening(cur,today);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
            for perm in p02.PERMS:cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,perm))
            conn.commit()
        args=dict(p_scope=prod.scope(items=[f['item']]),p_request=str(uuid.uuid4()));r=op.rpc('erp_cp7_capture_production_wip_v1',args);assert r['status']==200,r
        assert actual_vector(r['body'])==[8,8,0,0,0,0];rid=r['body']['run_id']
        denied=other.rpc('erp_cp7_read_production_wip_v1',dict(p_run=rid));missing=other.rpc('erp_cp7_read_production_wip_v1',dict(p_run=str(uuid.uuid4())))
        assert denied==missing and denied['status']==403,(denied,missing)
        def keys(v):
            if isinstance(v,dict):
                for k,x in v.items():yield k;yield from keys(x)
            elif isinstance(v,list):
                for x in v:yield from keys(x)
        assert not set(keys(r['body']))&{'cost','amount','margin','rate','unit_price','unit_hpp_snapshot','lot_cost','actual_cost'}
        with http.connect() as conn,conn.cursor() as cur:
            cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,));conn.commit()
        assert op.rpc('erp_cp7_capture_production_wip_v1',args)['status']==403
        assert op.rpc('erp_cp7_read_production_wip_v1',dict(p_run=rid))['status']==403
        return dict(status='PASS',operations_no_financial_fields=True,other_actor_cannot_enumerate_run=True,same_token_revoked_replay=True)
    return [('AUD_F02_HTTP_PRIVATE_REST',private_rest),('AUD_F02_HTTP_OPS_SCOPE_REVOKE',ops_scope)]+[('WRITER_RERUN_'+k,f) for k,f in ident.http_cases(http,today)+cut.http_cases(http,today)+prod.http_cases(http,today)]

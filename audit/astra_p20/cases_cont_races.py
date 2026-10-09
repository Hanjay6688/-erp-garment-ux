"""Own interleavings, quantities and reconciliation on a fresh disposable DB per case."""
import hashlib,json,threading,time,uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
from queue import Queue
import psycopg
import cases_business as money
import cp7_wip_source_cases as wip
import cp7_p19_report_v2_cases as report
import cp7_opening_payroll_cases as opening
from cases_cont_state import report_drive
from cases_stage import admin,api,seed,plan,check,wrap,new_run,read_pages,retained,refusal

def together(ops):
    gate=threading.Barrier(len(ops))
    def run(op):gate.wait(timeout=10);return op()
    with ThreadPoolExecutor(max_workers=len(ops)) as pool:
        futures=[pool.submit(run,op) for op in ops]
        return [f.result(90) for f in futures]

def drive(tools,key):
    for _ in range(10000):
        with tools.connect() as conn,conn.cursor() as cur:
            s=api(cur,'erp_cp7_step_staged_analysis_v1',key);conn.commit()
        if s['state']!='RUNNING':return s
    raise RuntimeError('AUDITOR_STAGED_DRIVER_BOUND')

def races(tools,today):
    def lost():
        p=money.procurement;key=uuid.uuid4()
        with tools.connect() as conn,conn.cursor() as cur:
            f=p.fixture(cur,today,'29','4.73',True);draft=p.command(cur,'SAVE_DRAFT',f['payload']);conn.commit()
        # Deliberately discard the server response after a real successful commit.
        # This simulates the recovery boundary, not a claim of a literal TCP packet fault.
        with tools.connect() as conn,conn.cursor() as cur:p.post(cur,draft,key);conn.commit()
        with tools.connect() as conn,conn.cursor() as cur:
            before=money.gl(cur);stock=p.qty(cur,f);again=p.post(cur,draft,key)
            check(again['status']=='POSTED' and again['purchase_id']==draft['purchase_id'],'Reconnect finds original committed outcome')
            check(p.qty(cur,f)==stock==(D(29),1) and money.gl(cur)==before,'Lost-response recovery cannot post stock or AP twice')
            ap=cur.execute('select erp.material_purchase_final_ap_total(%s)',(draft['purchase_id'],)).fetchone()[0]
            check(D(ap)==D('137.17'),'Independent29x4.73 AP exact')
            changed=refusal(cur,lambda:p.command(cur,'POST',dict(purchase_id=draft['purchase_id'],change_reason='different intention'),key,draft['row_version']))
            check(changed['refused'],'Same UUID with changed post body remains bound')
            conn.commit()
        return dict(qty=29,movements=1,AP='137.17',request=str(key),simulation='SERVER_COMMIT_RESPONSE_INTENTIONALLY_DISCARDED_THEN_CONNECTION_CLOSED',changed=changed)

    def physical():
        with tools.connect() as conn,conn.cursor() as cur:
            f=wip.fixture(cur,today,finish=False);version=wip.base.group_version(cur,f['group']);conn.commit()
        quantities=[19,17];keys=[uuid.uuid4(),uuid.uuid4()];payloads=[]
        for q in quantities:
            payloads.append(dict(cutting_group_id=f['group'],destination_location_id=wip.base.LOCATION,physical_at=wip.b.chain.production.at(f['day'],14).isoformat(),reason='Astra competing completion finite30ready',good_qty_pcs=q,completion_mode='PARTIAL_SELECTION',lines=[dict(final_product_id=f['product'],qty_good_pcs=q,qty_bs_pcs=0,source_laundry_receipt_line_id=f['receipt_line'],source_laundry_receipt_batch_size_line_id=f['receipt_size'])]))
        def post(i):
            with tools.connect() as conn,conn.cursor() as cur:
                try:
                    wip.b.chain.production.owner(cur)
                    out=cur.execute('select public.erp_save_laundry_qc_action_v1(%s,%s::jsonb,%s,%s)',('POST_FINAL_SKU',json.dumps(payloads[i]),keys[i],version)).fetchone()[0]
                    conn.commit();return dict(i=i,committed=True,result=out)
                except psycopg.Error as e:conn.rollback();return dict(i=i,committed=False,sqlstate=e.sqlstate,message=e.diag.message_primary)
        outcomes=together([lambda:post(0),lambda:post(1)])
        winners=[x for x in outcomes if x['committed']];check(len(winners)==1,'Exactly one19/17completion admitted against30ready',results=outcomes)
        winner=winners[0]['i'];replay=post(winner);check(replay['committed'] and replay['result']==winners[0]['result'],'Same physical UUID replays once')
        with tools.connect() as conn,conn.cursor() as cur:
            captured=wip.capture(cur,[f['group']]);vals={k:sum(int(x[k+'_pcs']) for x in captured['result']['totals']) for k in ['input','wip','fg','bs']}
            check(vals==dict(input=100,wip=100-quantities[winner],fg=quantities[winner],bs=0),'Only admitted source quantity becomes FG',actual=vals)
            remainder=30-quantities[winner];wip.qc(cur,f,remainder,0,15)
            end=wip.capture(cur,[f['group']]);final={k:sum(int(x[k+'_pcs']) for x in end['result']['totals']) for k in ['input','wip','fg','bs']}
            check(final==dict(input=100,wip=70,fg=30,bs=0),'Legal remaining completion works, finite source ends exactly30FG',actual=final);conn.commit()
        return dict(source_ready=30,attempts=quantities,outcomes=outcomes,after_race=vals,after_remainder=final)

    def workers():
        key=uuid.uuid4()
        with tools.connect() as conn,conn.cursor() as cur:
            plan.fixture(cur,today);first=api(cur,'erp_cp7_request_staged_analysis_v1',json.dumps(seed.query(today)),key);conn.commit()
        def once():
            with tools.connect() as conn,conn.cursor() as cur:
                s=api(cur,'erp_cp7_step_staged_analysis_v1',key);conn.commit();return s
        with tools.connect() as holder,holder.cursor() as cur:
            cur.execute('select 1 from cp7_analysis_stage.jobs where request_id=%s for update',(key,))
            with ThreadPoolExecutor(max_workers=1) as pool:busy=pool.submit(once).result(20)
            check(busy.get('worker_active') and busy['units_done']==0,'Held job never executes duplicate work');holder.rollback()
        results=together([once,once]);done=drive(tools,key);check(done['state']=='DONE','Contended job completes',result=done)
        with tools.connect() as conn,conn.cursor() as cur:
            job=cur.execute('select id::text from cp7_analysis_stage.jobs where request_id=%s',(key,)).fetchone()[0]
            outputs=cur.execute('select count(*),count(distinct idx) from cp7_analysis_stage.outputs where job_id=%s',(job,)).fetchone()
            check(outputs==(done['unit_count'],done['unit_count']),'Exactly one output per declared unit',outputs=outputs,declared=done['unit_count'])
            r=dict(key=key,job=job,run=done['run_id']);proof=read_pages(cur,r);before=retained(cur,r)
            for _ in range(3):check(api(cur,'erp_cp7_step_staged_analysis_v1',key)['run_id']==r['run'],'RepeatedDONE identity')
            check(retained(cur,r)==before,'RepeatedDONE does not rewrite any unit/final row');conn.commit()
        return dict(busy=busy,concurrent=results,outputs=outputs,identity=proof['identity'],done_no_recompute=True)

    def inflight():
        with tools.connect() as conn,conn.cursor() as cur:plan.fixture(cur,today);conn.commit()
        with tools.connect() as writer,writer.cursor() as wc:
            loc=seed.location(wc,'Astra pending transaction before capture')
            with tools.connect() as conn,conn.cursor() as cur:
                r=new_run(cur,today,setup=False);proof=read_pages(cur,r);before=retained(cur,r);conn.commit()
            writer.commit()
        with tools.connect() as conn,conn.cursor() as cur:
            fresh=api(cur,'erp_cp7_staged_snapshot_freshness_v1',r['run'])
            check(fresh['capture_boundary']=='SNAPSHOT' and fresh['freshness_state']=='CHANGES_RECORDED' and fresh['changes_total']>=1,'Pre-capture uncommitted write becomes visible as change after commit',freshness=fresh)
            check(retained(cur,r)==before and read_pages(cur,r)['index']==proof['index'],'Commit changes freshness, never historical pages')
            cur.execute('delete from erp.locations where id=%s',(loc,));conn.commit()
        with tools.connect() as conn,conn.cursor() as cur:
            deleted=api(cur,'erp_cp7_staged_snapshot_freshness_v1',r['run'])
            check(deleted['changes_total']>=fresh['changes_total'] and read_pages(cur,r)['identity']==proof['identity'],'Recorded deletion does not mutate saved result');conn.commit()
        return dict(freshness=fresh,after_delete=deleted,identity=proof['identity'],scope='MASTER_DATA_IN_FLIGHT; PR44 conflict-free acceptance still reserved')

    def publishers():
        with tools.connect() as conn,conn.cursor() as cur:
            r=new_run(cur,today);r['identity']=read_pages(cur,r)['identity'];initial_key=uuid.uuid4()
            initial=report.payload(r,title='Astra baseline report');api(cur,'erp_cp7_publish_report_v2',json.dumps(initial),initial_key)
            baseline=report_drive(cur,initial_key);check(baseline['state']=='DONE','Initial revision exists');series=baseline['series_id'];keys=[uuid.uuid4(),uuid.uuid4()]
            for i,key in enumerate(keys):
                p=report.payload(r,series_id=series,expected_revision='1',title='Astra revision '+str(i));s=api(cur,'erp_cp7_publish_report_v2',json.dumps(p),key)
                while s['state']=='RUNNING' and s['units_done']<s['unit_count']-1:s=api(cur,'erp_cp7_step_report_v2',key)
                check(s['state']=='RUNNING' and s['stage']=='SUMMARY','Both candidates prepared immediately before seal',result=s)
            actor=cur.execute('select actor::text from cp7_analysis_stage.report_jobs where request_id=%s',(keys[0],)).fetchone()[0];conn.commit()
        pids=Queue()
        def seal(key):
            with tools.connect() as conn,conn.cursor() as cur:
                pids.put(cur.execute('select pg_backend_pid()').fetchone()[0]);s=api(cur,'erp_cp7_step_report_v2',key);conn.commit();return s
        with tools.connect() as holder,holder.cursor() as hc:
            hc.execute("select pg_advisory_xact_lock(hashtextextended('CP7:REPORT_SERIES_V2:'||%s||':'||%s,0))",(actor,series))
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs=[pool.submit(seal,key) for key in keys];ids=[pids.get(timeout=8),pids.get(timeout=8)]
                try:
                    with tools.connect(autocommit=True) as conn,conn.cursor() as cur:
                        deadline=time.monotonic()+6;waiting=0
                        while time.monotonic()<deadline:
                            waiting=cur.execute("select count(distinct pid) from pg_locks where pid=any(%s) and locktype='advisory' and not granted",(ids,)).fetchone()[0]
                            if waiting==2:break
                            time.sleep(.03)
                        check(waiting==2,'Both publishers really wait before release')
                finally:holder.commit()
                results=[j.result(40) for j in jobs]
        check(sorted(x['state'] for x in results)==['DONE','FAILED'],'Only one expected-revision1 publication seals',results=results)
        with tools.connect() as conn,conn.cursor() as cur:
            revisions=[x[0] for x in cur.execute('select revision from cp7_analysis_stage.report_publications where series_id=%s order by revision',(series,)).fetchall()];check(revisions==[1,2],'No duplicate published revision',revisions=revisions)
            done=next(x for x in results if x['state']=='DONE');doc=api(cur,'erp_cp7_read_report_v2',done['publication_id']);hashes=[]
            for entry in doc['sections']:
                s=api(cur,'erp_cp7_read_report_section_v2',doc['id'],entry['index'],doc['access_epoch']);raw=s['body'].encode('utf8');digest=hashlib.sha256(raw).hexdigest()
                check(len(raw)==entry['utf8_bytes'] and digest==entry['sha256'],'Published section independently hashes to one manifest');hashes.append(digest)
            summary=hashlib.sha256(doc['summary'].encode('utf8')).hexdigest();check(summary==doc['summary_sha256'] and hashlib.sha256('\n'.join([summary]+hashes).encode()).hexdigest()==doc['report_hash'],'Whole report seal coherent');conn.commit()
        return dict(results=results,revisions=revisions,report_hash=doc['report_hash'],actual_lock_waiters=2)

    def carry():
        with tools.connect() as conn,conn.cursor() as cur:
            f=opening.fixture(cur,today);other=opening.s.n.seed_header(cur,f,today+timedelta(days=1),today+timedelta(days=1));pids=[f['payroll'],other]
            payloads=[opening.payload(cur,f,'CARRY','4',pid) for pid in pids];before=money.gl(cur);conn.commit()
        def claim(i):
            with tools.connect() as conn,conn.cursor() as cur:
                try:
                    action,p=payloads[i];out=opening.bb.api.call(cur,action,p,uuid.uuid4());conn.commit();return dict(i=i,committed=True,result=out)
                except psycopg.Error as e:conn.rollback();return dict(i=i,committed=False,sqlstate=e.sqlstate,message=e.diag.message_primary)
        results=together([lambda:claim(0),lambda:claim(1)]);winners=[x for x in results if x['committed']]
        check(len(winners)==1,'Two payrolls cannot reserve the same four carry units',results=results)
        with tools.connect() as conn,conn.cursor() as cur:
            rows=cur.execute('select count(*),sum(opening_carry_qty),sum(amount) from erp.payroll_reimbursements where opening_carry_entitlement_id=%s',(f['entitlement'],)).fetchone()
            check(rows==(1,D(4),D(10)) and D(opening.state(cur,f)['carry'])==0,'Exactly4x2.50 once, no carry left',rows=rows)
            pid=pids[winners[0]['i']];opening.s.act(cur,'PREPARE',opening.s.doc(cur,pid));doc=opening.s.doc(cur,pid);key=uuid.uuid4();approved=opening.s.act(cur,'APPROVE',doc,key)
            changes=money.delta(before,money.gl(cur));expected={money.account(cur,'LABOR_COST'):D(10),money.account(cur,'CONTRACTOR_PAYABLE'):D(-10)}
            check(changes==expected,'Carry expense accrued exactly10 once at approval',actual=changes)
            check(opening.s.act(cur,'APPROVE',doc,key)==approved and money.delta(before,money.gl(cur))==expected,'Approval replay cannot accrue carry twice');conn.commit()
        return dict(outcomes=results,reserved_rows=rows,expense_delta=changes,scope='OPENING_CARRY_TWO_PAYROLLS; earliest automatic accessory-carry selection not asserted')

    return [wrap('AS20C-05-LOST',lost),wrap('AS20C-15-RACE',physical),wrap('AS20C-28-WORKERS',workers),wrap('AS20C-29-INFLIGHT',inflight),wrap('AS20C-34-PUBLISH',publishers),wrap('AS20C-19-CARRY',carry)]

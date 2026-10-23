"""Actual checked SAVE2000 on a committed disposable copy, not a race.

The shared copy runner supplies commit-capable isolation. Its concurrency helper
is never called. Profile/commercial/policy fixtures use actual public commands;
their explicit synthetic assumptions never become factory defaults.
"""
from time import monotonic
from decimal import Decimal
import copy
import uuid
import cp7_ow13c_bounded_stage_cases as bounded
import cp7_ow13c_checked_cases as checked
import cp7_ow13c_checked_scale_cases as dense
import cp7_p19_scale_cases as volume

plan=bounded.plan
CONTRACT='cp7.ow13c.bounded-checked-save-volume.v1'
ANCHOR='OW13C_NATIVE_FRESH_SAVE_REPLAY_AND_NO_PHYSICAL_FACT'
SCALE='OW13C_BOUNDED_ACTUAL_CHECKED_SAVE2000_202000_UNDER8S'
IDS=dict(native=[ANCHOR],committed=[SCALE])
REQUIRED=dict(native=1,committed=1)
EXPECTED=DECLARED=2
FUNCTIONS,SCHEDULES=bounded.FUNCTIONS,bounded.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}


def cases(cur,today):
    checked.INSTALL_STATES,checked.REORDER_STATES,checked.CHECKED_STATE=INSTALL_STATES,REORDER_STATES,CHECKED_STATE
    return [(ANCHOR,dict(checked.cases(cur,today))[ANCHOR])]


def races(tools,today):
    """Adapter for the unchanged exact-authority committed-copy runner only."""
    def scale():
        with tools.connect()as conn,conn.cursor()as cur:
            cur.execute("set time zone 'UTC'")
            cur.execute("set statement_timeout='8s'")
            x=plan.fixture(cur,today)
            plan.b.api.admin(cur)
            config=copy.deepcopy(cur.execute('select config from cp7_schedule_native.plans order by revision desc limit 1').fetchone()[0])
            conn.commit()
            size=dense.seed(cur)
            conn.commit()
            rows=cur.execute("select p.identity_root_id::text,p.model_id::text,p.sku from erp.products p where p.sku like 'OW13CSV-%%'order by p.sku").fetchall()
            assert len(rows)==2000 and len({r[0]for r in rows})==2000
            # Native P19 commands, with its explicit selected daily1 and
            # ACTIVE scenario. Each product has its own commercial SKU here,
            # since this volume fixture has repeated sizes within each model.
            log=volume.Phases();log.commit=conn.commit
            volume.profile(cur,[r[0]for r in rows],log)
            skus=volume.commercial(cur,[dict(root=root,model=model,code=sku)for root,model,sku in rows],log)
            volume.activate(cur,skus,log)
            assert len(skus)==2000
            conn.commit()
            work_key=str(uuid.uuid4())
            first=bounded.request(cur,today,work_key)
            conn.commit()
            assert first['state']=='RUNNING' and first['units_done']==0
            w=bounded.work.get(cur,work_key)
            assert w['source_state']=='UNCHANGED' and w['history_input_coverage']=='COMPLETE'
            payload=dict(source_run=w['source_run'],source_hash=w['source_hash'],expected_revision=w['revision'],
                         config=config,reason='Synthetic SAVE2000 work assumptions from actual Native fixture; not factory defaults',
                         staged_review_contract='cp7.schedule-staged-review.v1')
            bounded.work.save(cur,payload)
            conn.commit()
            # Calendar SAVE legitimately changes the analysis source. Capture
            # a NEW real reference after it, never refresh or relabel the old.
            key=str(uuid.uuid4());job=bounded.request(cur,today,key);conn.commit()
            step_ms=[]
            while job['state']=='RUNNING':
                assert len(step_ms)<plan.staged.DRIVER_CALLS
                start=monotonic();job=plan.staged.step(cur,key);conn.commit()
                step_ms.append(round((monotonic()-start)*1000,3))
                plan.staged.checked(job,key)
            assert job['state']=='DONE',job
            assert max(step_ms)<8000,step_ms
            run=job['run_id']
            row=plan.staged.job_row(cur,key)
            assert row['reference']['status']=='INCOMPLETE' and row['reference']['bounded_history_inputs']['coverage']=='COMPLETE'
            assert int(row['reference']['bounded_stock_reference']['row_count'])>=202000
            conn.commit()
            options,query,p=plan.draft_payload(cur,x,run)
            assert options['production_state']=='ACTIVE' and Decimal(options['needed_pcs'])>=2 and Decimal(options['capacity_pcs'])>=2,options
            x.update(run=run,key=key,options=options,query=query,payload=p)
            assert plan.staged.limited(cur,'erp_cp7_check_staged_analysis_source_v1',(run,))['source_state']=='UNCHANGED'
            before,physical=dense.counts(cur),plan.monetary_state(cur)
            conn.commit()
            times,requests,replies=[],[],[]
            for _ in range(3):
                request=str(uuid.uuid4());start=monotonic()
                result=checked.save(cur,checked.payload(x),request)
                # Includes both full source checks and both genuine Native
                # feasibility checks; the app's public writer is unchanged.
                elapsed=(monotonic()-start)*1000
                assert elapsed<8000,('BOUNDED_ACTUAL_CHECKED_SAVE_OVER8S',elapsed)
                assert result['state']=='SAVED' and result['cutting_save_guard']['feasible'] is True,result
                conn.commit()
                times.append(round(elapsed,3));requests.append(request);replies.append(result)
            assert checked.save(cur,checked.payload(x),requests[0])==replies[0]
            conn.commit()
            after=dense.counts(cur)
            assert after==(before[0]+3,before[1]+3,before[2],before[3]),(before,after)
            assert plan.monetary_state(cur)==physical
            assert cur.execute("select count(*)from erp.fg_stock_movements where source_type='OW13C_SAVE_VOLUME'").fetchone()[0]==202000
            return dict(status='PASS',label='SYNTHETIC_NATIVE_TIMING_ONLY_NOT_FACTORY_DEFAULTS',**size,
                        actual_products=len(row['reference']['facts']['products']),actual_public_checked_SAVE=True,
                        genuine_Native_staged_DONE_after_calendar_SAVE=True,real_public_profile_commercial_policy_writers=True,
                        preparation_committed_per_Native_command=True,synthetic_assumptions=volume.SYNTHETIC['profile'],
                        policy_state=volume.SYNTHETIC['policy_state'],preparation_command_timings=log,
                        fresh_unique_UUIDs=3,exact_first_UUID_replay=True,millis=times,wall_limit_ms=8000,statement_limit='8s',
                        both_full_source_checks_and_both_feasibility_checks_inside_measured_writer=True,
                        no_truncation_or_source_hash_or_job_state_override=True,
                        three_drafts_three_receipts_no_new_Native_group_or_intent=True,physical_stock_money_HPP_unchanged=True,
                        actual_checked_SAVE2000_qualified=True,concurrency_test=False,race_case_credit=0,
                        factory3600_or_end_to_end_UI_SLA_claim=False)

    return [(SCALE,scale)]

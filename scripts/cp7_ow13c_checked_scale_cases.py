"""Actual checked SAVE under 8s on 2,000 synthetic products/202,000 moves.

The fixture is labelled synthetic. Analysis, source checks and the save writer
are real Native calls; no private result/hash/proof is inserted or substituted.
Native31's positive anchor repeats here for zero new case credit.
"""
import uuid
from time import monotonic
import cp7_ow13c_checked_cases as base

plan = base.plan
CONTRACT = 'cp7.ow13c.checked-save-scale.v1'
POSITIVE = 'OW13C_NATIVE_FRESH_SAVE_REPLAY_AND_NO_PHYSICAL_FACT'
SCALE = 'OW13C_NATIVE_ACTUAL_CHECKED_SAVE2000_202000_UNDER8S'
IDS = dict(native=[POSITIVE, SCALE])
REQUIRED = dict(native=2)
EXPECTED = DECLARED = 2
FUNCTIONS, SCHEDULES = base.FUNCTIONS, base.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE = {}, {}, {}


def seed(cur):
    """Same declared size as OW10's timing fixture, with a distinct source tag."""
    plan.b.api.admin(cur)
    cur.execute('set local session_replication_role=replica')
    cur.execute("insert into erp.product_models(id,model_code,model_name,is_active)"
                "select gen_random_uuid(),'OW13CSV-M'||g,'OW13C SAVE synthetic model '||g,true from generate_series(1,200)g")
    cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,created_at,is_active,is_portal_visible)
        select x.id,'OW13CSV-'||x.n,m.id,b.brand_id,'OW13CSV',b.size_id,'OW13C SAVE synthetic '||x.n,x.id,
         now()-interval'131 days',now()-interval'131 days',true,true
        from(select gen_random_uuid()id,g n from generate_series(1,2000)g)x
        join(select id,row_number()over(order by model_code)rn from erp.product_models where model_code like 'OW13CSV-M%%')m on m.rn=1+(x.n%%200)
        cross join(select*from erp.products where id=%s)b""", (base.retained.formula.sales.fg.base.BASE_PRODUCT,))
    cur.execute("""insert into erp.fg_stock_movements(id,product_id,lot_id,location_id,quality_grade,movement_type,qty_signed,unit_hpp_snapshot,source_type,physical_at,system_created_at)
        select gen_random_uuid(),p.id,null,%s,'GRADE_A','OPENING',800,10,'OW13C_SAVE_VOLUME',now()-interval'130 days',now()-interval'130 days'
        from erp.products p where p.sku like 'OW13CSV-%%'""", (base.retained.formula.sales.fg.base.LOCATION,))
    cur.execute("""insert into erp.fg_stock_movements(id,product_id,lot_id,location_id,quality_grade,movement_type,qty_signed,unit_hpp_snapshot,source_type,physical_at,system_created_at)
        select gen_random_uuid(),p.id,null,%s,'GRADE_A','SALE',-(1+(g%%6)),10,'OW13C_SAVE_VOLUME',now()-((g%%120)||' days')::interval-interval'2 hours',now()-interval'1 hour'
        from erp.products p cross join generate_series(1,100)g where p.sku like 'OW13CSV-%%'""", (base.retained.formula.sales.fg.base.LOCATION,))
    cur.execute('set local session_replication_role=origin')
    cur.execute('analyze erp.fg_stock_movements')
    items, moves = cur.execute("select (select count(*)from erp.products where sku like 'OW13CSV-%%'),"
                               "(select count(*)from erp.fg_stock_movements where source_type='OW13C_SAVE_VOLUME')").fetchone()
    assert (items, moves) == (2000, 202000), (items, moves)
    return dict(products=items, movements=moves)


def counts(cur):
    plan.b.api.admin(cur)
    return cur.execute('select (select count(*)from cp7_plan_native.drafts),'
                       '(select count(*)from cp7_cutting_checked.receipts),'
                       '(select count(*)from cp7_plan_native.intents),'
                       '(select count(*)from erp.cutting_groups)').fetchone()


def cases(cur, today):
    base.INSTALL_STATES, base.REORDER_STATES, base.CHECKED_STATE = INSTALL_STATES, REORDER_STATES, CHECKED_STATE
    positive = dict(base.cases(cur, today))[POSITIVE]

    def scale():
        x = plan.fixture(cur, today)
        size = seed(cur)
        plan.plan.review_work(cur, today)
        run, key = plan.snapshot(cur, today)
        o, q, p = plan.draft_payload(cur, x, run)
        x.update(run=run, key=key, options=o, query=q, payload=p)
        check = plan.staged.recorded_check(cur, run, 'RECORDING_TIME')
        assert check['source_state'] == 'UNCHANGED', check
        before, physical = counts(cur), plan.monetary_state(cur)
        times, requests, replies = [], [], []
        for _ in range(3):
            cur.execute("set local statement_timeout='8s'")
            request = str(uuid.uuid4())
            started = monotonic()
            result = base.save(cur, base.payload(x), request)
            elapsed = (monotonic() - started) * 1000
            assert elapsed < 8000, ('OW13C_ACTUAL_CHECKED_SAVE_OVER8S', elapsed)
            assert result['state'] == 'SAVED' and result['cutting_save_guard']['feasible'] is True, result
            times.append(round(elapsed, 3))
            requests.append(request)
            replies.append(result)
        assert base.save(cur, base.payload(x), requests[0]) == replies[0]
        after = counts(cur)
        assert after == (before[0]+3, before[1]+3, before[2], before[3]), (before, after)
        assert plan.monetary_state(cur) == physical
        assert cur.execute("select count(*)from erp.fg_stock_movements where source_type='OW13C_SAVE_VOLUME'").fetchone()[0] == 202000
        return dict(status='PASS', label='SYNTHETIC_NATIVE_TIMING_ONLY', **size,
                    actual_public_checked_SAVE=True, fresh_unique_UUIDs=3, exact_first_UUID_replay=True,
                    millis=times, wall_limit_ms=8000, statement_limit='8s',
                    both_full_source_checks_and_both_feasibility_checks_inside_measured_writer=True,
                    no_truncation_or_source_hash_override=True,
                    three_drafts_three_receipts_no_new_Native_group_or_intent=True,
                    physical_stock_money_HPP_unchanged=True, factory3600_or_end_to_end_UI_SLA_claim=False)

    return [(POSITIVE, positive), (SCALE, scale)]

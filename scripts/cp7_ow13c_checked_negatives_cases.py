"""Five focused checked-save controls on the unchanged Native31 product source.

One repeated positive anchor earns no new case credit. Four negative controls
use real Native rows/commands, current staged analysis and the public writer.
This does not qualify HTTP, browser, races, scale or after-use restore.
"""
from decimal import Decimal as D
import copy
import cp7_ow13c_checked_cases as base

plan = base.plan
CONTRACT = 'cp7.ow13c.checked-save-negatives.v1'
POSITIVE = 'OW13C_NATIVE_FRESH_SAVE_REPLAY_AND_NO_PHYSICAL_FACT'
NEW_NATIVE = ['OW13C_NATIVE_CHANGED_PRODUCT_REFUSED_WITHOUT_ORPHAN',
              'OW13C_NATIVE_PAUSED_POLICY_REFUSED_WITHOUT_ORPHAN',
              'OW13C_NATIVE_CURRENT_SHARED_MATERIAL_REFUSED_WITHOUT_ORPHAN',
              'OW13C_NATIVE_CURRENT_SHARED_CAPACITY_REFUSED_WITHOUT_ORPHAN']
IDS = dict(native=[POSITIVE, *NEW_NATIVE])
REQUIRED = dict(native=5)
EXPECTED = DECLARED = 5
FUNCTIONS, SCHEDULES = base.FUNCTIONS, base.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE = {}, {}, {}


def state(cur):
    """A refusal must leave all rows/receipts and the physical/money facts exact."""
    plan.b.api.admin(cur)
    counts = cur.execute('select (select count(*)from cp7_plan_native.drafts),'
                         '(select count(*)from cp7_plan_native.intents),'
                         '(select count(*)from cp7_cutting_checked.receipts),'
                         '(select count(*)from erp.cutting_groups)').fetchone()
    return dict(counts=list(counts), money_stock_HPP=plan.monetary_state(cur),
                erp_platform_auth=plan.b.boundary.snapshot(cur))


def source(cur, run):
    return plan.staged.recorded_check(cur, run, 'RECORDING_TIME')


def refused_without_orphan(cur, x, code, sqlstate='40001'):
    before = state(cur)
    plan.refused(cur, lambda: base.save(cur, base.payload(x)), code, sqlstate)
    assert state(cur) == before, 'OW13C_REFUSAL_CHANGED_ROWS_OR_PHYSICAL_FACTS'
    return dict(status='PASS', exact_message=code, sqlstate=sqlstate,
                no_new_draft_intent_receipt_or_cutting_group=True,
                existing_ERP_rows_stock_money_HPP_unchanged=True)


def current_payload(cur, x, today, pcs='2', issued='1'):
    """Capture after the competing Native action, without altering its sources."""
    run, key = plan.snapshot(cur, today)
    o, q, p = plan.draft_payload(cur, x, run, pcs=pcs, issued=issued)
    check = source(cur, run)
    assert check['source_state'] == 'UNCHANGED', check
    return dict(x, run=run, key=key, options=o, query=q, payload=p)


def cases(cur, today):
    base.INSTALL_STATES, base.REORDER_STATES, base.CHECKED_STATE = INSTALL_STATES, REORDER_STATES, CHECKED_STATE
    positive = dict(base.cases(cur, today))[POSITIVE]

    def product():
        x = plan.single(cur, today)
        archived = plan.save(cur, x['payload'])
        plan.b.api.admin(cur)
        changed = cur.execute('update erp.products set is_active=false where id=%s and is_active returning id',
                              (x['root'],)).fetchall()
        assert len(changed) == 1, changed
        # Explicit administrative master fixture, not a claimed public UI action.
        live = plan.preview(cur, archived['draft_id'])['live']
        assert plan.verdicts(live)['PRODUCT'] == ('REFUSED', 'CP7_PLAN_V2_PRODUCT_CHANGED'), live
        check = source(cur, x['run'])
        assert check['source_state'] == 'ARCHIVED_STALE', check
        out = refused_without_orphan(cur, x, 'CP7_CUTTING_SUGGESTION_SOURCE_CHANGED')
        return dict(out, administrative_product_fixture_deactivated=True,
                    old_plan_preview_product_refused=True, source_state=check['source_state'])

    def policy():
        x = plan.single(cur, today)
        archived = plan.save(cur, x['payload'])
        plan.policy(cur, x, 'PAUSED')
        live = plan.preview(cur, archived['draft_id'])['live']
        assert plan.verdicts(live)['POLICY'] == ('REFUSED', 'CP7_PLAN_V2_POLICY_CHANGED') and live['policy_state'] == 'PAUSED', live
        check = source(cur, x['run'])
        assert check['source_state'] == 'ARCHIVED_STALE', check
        out = refused_without_orphan(cur, x, 'CP7_CUTTING_SUGGESTION_SOURCE_CHANGED')
        return dict(out, actual_public_policy_CAS_paused=True,
                    old_plan_preview_policy_refused=True, source_state=check['source_state'])

    def material():
        first, second = plan.two(cur, today)
        first['payload']['cutting']['rolls'][0].update(
            qty_issued='6', qty_consumed='3', qty_reported_remaining='3')
        before_money = plan.monetary_state(cur)
        draft = plan.save(cur, first['payload'])
        applied = plan.apply(cur, plan.action(draft))
        assert applied['state'] == 'NATIVE_DRAFT_CREATED', applied
        assert plan.monetary_state(cur) == before_money
        # Select the same actual roll for target two, then capture a NEW run.
        # The checked refusal must therefore be material feasibility, not stale source.
        second = dict(second, fabric=copy.deepcopy(first['fabric']))
        x = current_payload(cur, second, today, issued='6')
        pool = plan.plan.material_pool(cur, x['payload'])
        assert [D(pool[k]) for k in ('native_available', 'linked_native_draft_qty', 'free_for_new_plan')] == [D(10), D(6), D(4)], pool
        assert any(r['group_id'] == applied['native']['cutting_group_id'] for r in pool['linked_native_drafts']), pool
        before = state(cur)
        plan.refused(cur, lambda: plan.save(cur, x['payload']), 'CP7_PLAN_SHARED_MATERIAL_BUDGET_CHANGED', '40001')
        assert state(cur) == before
        out = refused_without_orphan(cur, x, 'CP7_PLAN_SHARED_MATERIAL_BUDGET_CHANGED')
        return dict(out, source_state='UNCHANGED', actual_unposted_Native_group_uses_shared_roll=True,
                    physical_available='10', linked_draft_qty='6', selected_issued='6', free_for_new_plan='4')

    def capacity():
        first, second = plan.two(cur, today)
        used, _ = plan.capacity_split(first, second)
        before_money = plan.monetary_state(cur)
        draft = plan.save(cur, plan.with_pcs(first['payload'], used))
        applied = plan.apply(cur, plan.action(draft))
        assert applied['state'] == 'NATIVE_DRAFT_CREATED', applied
        assert plan.monetary_state(cur) == before_money
        x = current_payload(cur, second, today)
        cap, need = D(x['options']['capacity_pcs']), D(x['options']['needed_pcs'])
        selected = max(1, int(cap) - used + 1)
        assert cap == int(cap) and 1 <= selected <= cap and selected <= int(-(-need // 1)), (cap, used, selected, need)
        x['payload'] = plan.with_pcs(x['payload'], selected)
        archived = plan.save(cur, x['payload'])
        live = plan.preview(cur, archived['draft_id'])['live']
        assert plan.verdicts(live)['CAPACITY'] == ('REFUSED', 'CP7_PLAN_V2_CAPACITY_USED'), live
        assert D(live['capacity_used_by_other_plans_pcs']) == used and D(live['selected_new_pcs']) == selected, live
        assert source(cur, x['run'])['source_state'] == 'UNCHANGED'
        out = refused_without_orphan(cur, x, 'CP7_PLAN_V2_CAPACITY_USED')
        return dict(out, source_state='UNCHANGED', actual_other_target_Native_group_uses_shared_centre=True,
                    capacity_snapshot=str(cap), used_by_other_plan=str(used), selected_pcs=str(selected),
                    capacity_remaining=live['capacity_now_pcs'])

    return [(POSITIVE, positive), *zip(NEW_NATIVE, [product, policy, material, capacity])]

"""Boundary 200->201 actual Native posted groups: UNKNOWN must not become zero.

Every added receipt/cutting group uses the retained public Native writers.
The checked SAVE is then refused as stale; its old-plan preview independently
proves that current WIP is UNKNOWN. This is no unchanged-source WIP claim.
"""
import cp7_ow13c_checked_cases as base
from cp7_ow13c_checked_negatives_cases import refused_without_orphan, source

plan = base.plan
CONTRACT = 'cp7.ow13c.checked-save-wip.v1'
POSITIVE = 'OW13C_NATIVE_FRESH_SAVE_REPLAY_AND_NO_PHYSICAL_FACT'
WIP = 'OW13C_NATIVE_ACTUAL_WIP200_201_UNKNOWN_STALE_REFUSAL'
IDS = dict(native=[POSITIVE, WIP])
REQUIRED = dict(native=2)
EXPECTED = DECLARED = 2
FUNCTIONS, SCHEDULES = base.FUNCTIONS, base.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE = {}, {}, {}


def posted_count(cur, x):
    plan.b.api.admin(cur)
    return cur.execute('select count(*)from erp.cutting_groups g join erp.production_orders p on p.id=g.po_id '
                       'where p.model_id=%s and g.material_issue_posted and g.cut_at<=clock_timestamp()',
                       (x['model'],)).fetchone()[0]


def cases(cur, today):
    base.INSTALL_STATES, base.REORDER_STATES, base.CHECKED_STATE = INSTALL_STATES, REORDER_STATES, CHECKED_STATE
    positive = dict(base.cases(cur, today))[POSITIVE]

    def unknown():
        x = plan.single(cur, today)
        archived = plan.save(cur, x['payload'])
        initial = posted_count(cur, x)
        assert 0 <= initial < 200, initial
        for _ in range(200-initial):
            plan.posted_cut(cur, x, '1', today)
        assert posted_count(cur, x) == 200
        at200 = plan.preview(cur, archived['draft_id'])['live']
        assert plan.verdicts(at200)['WIP'] == ('OK', None) and at200['wip_status'] == 'COMPLETE' and at200['wip_now_pcs'] is not None, at200
        plan.posted_cut(cur, x, '1', today)
        assert posted_count(cur, x) == 201
        at201 = plan.preview(cur, archived['draft_id'])['live']
        assert plan.verdicts(at201)['WIP'] == ('REFUSED', 'CP7_PLAN_V2_WIP_UNKNOWN'), at201
        assert at201['wip_status'] == 'UNKNOWN' and at201['wip_reason'] == 'MODEL_WIP_GROUP_LIMIT', at201
        assert at201['wip_now_pcs'] is None and at201['need_now_pcs'] is None and at201['apply_ready'] is False, at201
        check = source(cur, x['run'])
        assert check['source_state'] == 'ARCHIVED_STALE', check
        out = refused_without_orphan(cur, x, 'CP7_CUTTING_SUGGESTION_SOURCE_CHANGED')
        return dict(out, all_added_receipts_and_cuts_through_actual_Native_public_writers=True,
                    initial_posted_groups=initial, added_posted_groups=201-initial,
                    model_posted_groups=201, boundary200_WIP='COMPLETE', boundary201_WIP='UNKNOWN',
                    unknown_reason='MODEL_WIP_GROUP_LIMIT', unknown_WIP_and_need_preserved_as_null=True,
                    source_state='ARCHIVED_STALE', actual_checked_route_refused=True,
                    unchanged_source_WIP_refusal_claim=False, model_WIP_limit_unchanged=200)

    return [(POSITIVE, positive), (WIP, unknown)]

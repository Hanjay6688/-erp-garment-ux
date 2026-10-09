"""P19 plan v2: a production plan from a staged analysis snapshot (snapshot contract v2 §2-§3).

Owner decision 8 Oct 2026: a plan may be drafted and saved from a snapshot that is
no longer current ("data per <time>"); when it is applied the server re-reads, in
the same transaction, the target's product, production policy, finished stock and
WIP, the selected rolls, other plans and the caller's access, and refuses with a
stated reason (40001, the numbers in DETAIL) when the plan is no longer valid.
Real Native writers, real concurrent sessions and real Auth/PostgREST calls on the
closed harness; v1 (one whole Original) is not changed by any case.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal as D
from queue import Queue
import copy
import json
import threading
import time
import uuid

import psycopg

import cp7_p19_staged_cases as staged
import cp7_plan_native_cases as plan
import cp7_fg_cases as fg

IDS = dict(
    native=['P19P_INDEX_RETAINED', 'P19P_SAVE_FROM_STALE_SNAPSHOT', 'P19P_PREVIEW_READ_ONLY_LIVE', 'P19P_APPLY_AFTER_UNRELATED_CHANGE',
            'P19P_FG_INCREASE_NEED_CHANGED', 'P19P_WIP_INCREASE_NEED_CHANGED', 'P19P_POLICY_CHANGED', 'P19P_CAPACITY_USED',
            'P19P_TARGET_PLANNED_AND_LINKED', 'P19P_FIELDS_KINDS_ACCESS', 'P19P_V1_V2_SHARED_CAPACITY'],
    races=['P19P_RACE_CAPACITY_TWO_TARGETS', 'P19P_RACE_SAME_TARGET', 'P19P_RACE_FG_WHILE_WAITING', 'P19P_RACE_INTENT_IN_FLIGHT_AT_CAPTURE',
           'P19P_RACE_V1_HOLDS_V2_REFUSED', 'P19P_RACE_V2_HOLDS_V1_REFUSED', 'P19P_RACE_V1_ROLLBACK_FREES_CAPACITY'],
    http=['P19P_HTTP_FLOW', 'P19P_HTTP_REVOKED'],
    browser=['P19P_BROWSER_DESKTOP_PLAN', 'P19P_BROWSER_MOBILE_PLAN'],
)
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = sum(REQUIRED.values())
CONTRACT = 'cp7.p19.plan-v2.v1'
FUNCTIONS = ('erp_cp7_get_plan_options_v2', 'erp_cp7_save_plan_draft_v2', 'erp_cp7_read_plan_draft_v2',
             'erp_cp7_preview_plan_action_v2', 'erp_cp7_apply_plan_action_v2')
VERDICTS = ['PRODUCT', 'POLICY', 'TARGET_PLANS', 'LINKED_PLANS', 'WIP', 'NEED', 'CAPACITY']
auth, b, previous, schedule = plan.auth, plan.b, plan.previous, plan.schedule
action, monetary_state = plan.action, plan.monetary_state


def rpc(cur, name, args, subject=None):
    return staged.limited(cur, name, args, subject)


def options(cur, q, subject=None):
    return rpc(cur, 'erp_cp7_get_plan_options_v2', (json.dumps(q),), subject)


def save(cur, p, key=None, subject=None):
    return rpc(cur, 'erp_cp7_save_plan_draft_v2', (json.dumps(p), key or uuid.uuid4()), subject)


def read(cur, d, subject=None):
    return rpc(cur, 'erp_cp7_read_plan_draft_v2', (d,), subject)


def preview(cur, d, subject=None):
    return rpc(cur, 'erp_cp7_preview_plan_action_v2', (d,), subject)


def apply(cur, p, key=None, subject=None):
    return rpc(cur, 'erp_cp7_apply_plan_action_v2', (json.dumps(p), key or uuid.uuid4()), subject)


def now(cur):
    return cur.execute('select clock_timestamp()').fetchone()[0]


def refusal(cur, op):
    """One refused call: (sqlstate, message, DETAIL as JSON when it is JSON). Nothing of it is kept."""
    b.api.admin(cur)
    cur.execute('savepoint p19p_refusal')
    try:
        op()
    except psycopg.Error as e:
        cur.execute('rollback to savepoint p19p_refusal')
        b.api.admin(cur)
        cur.execute('release savepoint p19p_refusal')
        detail = e.diag.message_detail
        try:
            detail = json.loads(detail) if detail else None
        except ValueError:
            pass
        return e.sqlstate, e.diag.message_primary, detail
    cur.execute('rollback to savepoint p19p_refusal')
    b.api.admin(cur)
    raise AssertionError('P19P_EXPECTED_REFUSAL')


def refusal_of(cur, op):
    return refusal(cur, op)


def refused(cur, op, code, sqlstate=None):
    state, message, detail = refusal(cur, op)
    assert message == code and (sqlstate is None or state == sqlstate), (code, sqlstate, state, message, detail)
    return detail


def fixture(cur, today):
    """v1's plan fixture (a cut production, a posted fabric receipt, a new PO of the model, selected profiles,
    ACTIVE policies, a reviewed schedule) without its single analysis: the run here is a staged one."""
    f = previous.production.cut.fixture(cur, today)
    fabric = plan.receipt.fixture(cur, today, qty='10', price='10')
    plan.receipt.post(cur, plan.receipt.command(cur, 'SAVE_DRAFT', fabric['payload']))
    po = str(uuid.uuid4())
    cur.execute("insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)"
                "values(%s,%s,%s,2,'CUTTING','CUTTING',%s,'P19 plan v2 explicit plan master fixture')",
                (po, '0000-P19P-' + po, f['model'], now(cur) - timedelta(hours=2)))
    root = str(f['product'])
    previous.select_profiles(cur, root, True)
    # v1's setup reviews the schedule (supply capture, sized calendar) before its analysis.
    plan.review_work(cur, today)
    target = cur.execute("select coalesce(identity_root_id,id)::text||':'||size_id::text from erp.products where id=%s", (root,)).fetchone()[0]
    return dict(f=f, fabric=fabric, po=po, root=root, target=target, model=str(f['model']))


def snapshot(cur, today, subject=None):
    key, _, done, _ = staged.staged_done(cur, today, subject=subject)
    return done['run_id'], key


def draft_payload(cur, x, run, subject=None, pcs='2', issued='1'):
    q = dict(run_id=run, target_key=x['target'], location_id=str(x['fabric']['location']), po_query='', roll_query='',
             po_offset='0', roll_offset='0', pattern_offset='0', limit='50')
    o = options(cur, q, subject)
    roll = [r for r in o['rolls'] if r['material_id'] == str(x['fabric']['material'])]
    assert len(roll) == 1 and D(roll[0]['available']) == 10, o['rolls']
    payload = dict(run_id=run, target_key=x['target'], plan_id=None, expected_revision=None, identity_hash=o['identity_hash'],
                   reason='P19 plan v2 explicit exact-size draft composition from a dated snapshot',
                   reviewed_assumption_ids=[a['id'] for a in o['assumptions']],
                   cutting=dict(po_id=x['po'], pattern_id=o['patterns'][0]['id'], source_location_id=str(x['fabric']['location']),
                                cut_at=(now(cur) - timedelta(hours=1)).isoformat(), notes='P19 plan v2 unposted reviewed planning intent',
                                size_slots=[dict(slot_no='1', size_id=o['size_id'], drawing_no='1')],
                                rolls=[dict(roll_id=roll[0]['id'], qty_issued=issued, qty_consumed=str(D(issued) / 2),
                                            qty_reported_remaining=str(D(issued) / 2), yields=[dict(slot_no='1', qty_pcs=pcs)])]))
    return o, q, payload


def single(cur, today, subject=None):
    x = fixture(cur, today)
    run, key = snapshot(cur, today, subject)
    o, q, p = draft_payload(cur, x, run, subject)
    assert D(o['needed_pcs']) >= 2 and D(o['capacity_pcs']) >= 2 and o['production_state'] == 'ACTIVE', o
    x.update(run=run, key=key, options=o, query=q, payload=p)
    return x


def two(cur, today):
    first, second = fixture(cur, today), fixture(cur, today)
    # select_profiles of the second fixture set every other root's mean to
    # zero: restore the first target's selected mean through the public command.
    profile = previous.baseline.get(cur, [first['root']])['rows'][0]
    previous.baseline.save(cur, dict(root_id=profile['root_id'], product_version_id=profile['product_version_id'], expected_revision=profile['revision'],
                                     reason='P19 plan v2 explicit two-target fixture: selected daily ten on each target; no factory demand claim',
                                     config=dict(profile['config'], daily_pcs='10')))
    plan.review_work(cur, today)
    run, key = snapshot(cur, today)
    for x in (first, second):
        o, q, p = draft_payload(cur, x, run)
        assert D(o['needed_pcs']) >= 2 and D(o['capacity_pcs']) >= 2, o
        x.update(run=run, key=key, options=o, query=q, payload=p)
    assert first['options']['capacity_pcs'] == second['options']['capacity_pcs'], 'P19P_ONE_SHARED_CENTRE'
    return first, second


def capacity_split(first, second):
    """Pieces for A, then B, so that B fits the snapshot's capacity alone but not after A."""
    c = int(D(first['options']['capacity_pcs']))
    need = lambda x: int(-(-D(x['options']['needed_pcs']) // 1))
    a = min(need(first), c - 1)
    b_ = c - a + 1
    assert c >= 2 and 1 <= a and b_ <= min(need(second), c), ('P19P_CAPACITY_FIXTURE', c, need(first), need(second))
    return a, b_


def with_pcs(p, pcs):
    p = copy.deepcopy(p)
    p['cutting']['rolls'][0]['yields'][0]['qty_pcs'] = str(pcs)
    return p


def v1_draft(cur, x, pcs, today):
    """P20 F01: a v1 plan (its own whole Original, the v1 commands) of the same target composition with `pcs` pieces,
    on the one shared capacity centre of the v2 snapshot. Built as the independent audit built it (AS20-32)."""
    original = plan.analysis.capture(cur, today)
    o = plan.options(cur, dict(x['query'], run_id=original['run_id']))
    assert D(o['capacity_pcs']) == D(x['options']['capacity_pcs']), ('P19P_V1_SAME_CENTRE', o['capacity_pcs'], x['options']['capacity_pcs'])
    p = with_pcs(x['payload'], pcs)
    p.pop('identity_hash')
    p.update(run_id=original['run_id'], source_hash=o['source_hash'], reviewed_assumption_ids=[a['id'] for a in o['assumptions']])
    return plan.save(cur, p)


def planned_pcs(cur, drafts):
    """Pieces of the committed intents of these drafts (the plan's own composition)."""
    return cur.execute("select coalesce(sum((y->>'qty_pcs')::numeric),0)from cp7_plan_native.intents i join cp7_plan_native.drafts d on d.id=i.draft_id "
                       "cross join lateral jsonb_array_elements(d.payload->'cutting'->'rolls')r cross join lateral jsonb_array_elements(r->'yields')y "
                       "where d.id=any(%s::uuid[])", ([str(x['draft_id']) for x in drafts],)).fetchone()[0]


def posted_cut(cur, x, pcs, today):
    """An ordinary Native cut of the target's model and size, saved and posted outside any plan, from a roll of
    its own posted receipt. The plan's selected roll is not touched: a cut from it changes the plan's selection,
    which preview refuses on its own rule (CP7_PLAN_NATIVE_SELECTION_CHANGED) before any WIP verdict."""
    other = plan.receipt.fixture(cur, today, qty='10', price='10')
    plan.receipt.post(cur, plan.receipt.command(cur, 'SAVE_DRAFT', other['payload']))
    b.api.admin(cur)
    rolls = cur.execute('select id::text from erp.material_rolls where material_id=%s', (other['material'],)).fetchall()
    assert len(rolls) == 1 and rolls[0][0] != x['payload']['cutting']['rolls'][0]['roll_id'], rolls
    c = copy.deepcopy(x['payload']['cutting'])
    c['source_location_id'] = other['location']
    c['rolls'] = [dict(c['rolls'][0], roll_id=rolls[0][0], qty_issued='1', qty_consumed='1', qty_reported_remaining='0')]
    c['rolls'][0]['yields'] = [dict(c['rolls'][0]['yields'][0], qty_pcs=str(pcs))]
    c['notes'] = 'P19 plan v2 ordinary Native cut after the snapshot'
    g = b.chain.production.rpc(cur, 'public.erp_save_cutting_group_before_sewing_v2', dict(c, action='SAVE_DRAFT', change_reason='P19 plan v2 ordinary cut'))
    gid = g['cutting_group_id']
    b.api.admin(cur)
    b.chain.production.rpc(cur, 'public.erp_save_cutting_group_before_sewing_v2', dict(c, id=gid, action='POST', change_reason='P19 plan v2 ordinary cut posted'),
                           expected_version=int(b.chain.base.group_version(cur, gid)))
    b.api.admin(cur)
    return gid


def found_fg(cur, x, pcs):
    """Finished stock of the target found at a count, through the unchanged Native writer."""
    at = fg.ax.r1.now(cur) - timedelta(minutes=50)
    b.api.admin(cur)
    p = dict(source_kind='FOUND_AT_OPNAME', product_id=x['root'], location_id=fg.base.LOCATION, qty_pcs=pcs, physical_at=at.isoformat(),
             reason='P19 plan v2 finished stock found after the snapshot')
    # The writer's own rule: with an HPP reference the value follows its average;
    # an owner value is allowed (and required) only when there is none.
    if cur.execute('select erp.fg_unsourced_valuation_v1(%s,%s)->>%s', (x['root'], at, 'tier')).fetchone()[0] == 'OWNER_INPUT_REQUIRED':
        p.update(owner_unit_value='10', owner_value_reason='P19 plan v2 explicit independently supplied value')
    fg.ax.post(cur, p)
    b.api.admin(cur)


def policy(cur, x, state):
    skus = [r[0] for r in cur.execute("""select distinct v.sku_id::text from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id
        where m.product_root=%s::uuid and v.effective_from<=clock_timestamp() and(v.effective_to is null or v.effective_to>clock_timestamp())""",
                                       (x['target'].split(':')[0],)).fetchall()]
    w = previous.policies.get(cur, skus)
    previous.policies.apply(cur, [previous.policies.proposal(r, state) for r in w['rows']])
    b.api.admin(cur)


def short_of_need(x):
    """Whole pieces one short of the snapshot's need: what is left is (0, 1], below the plan's two pieces."""
    need = D(x['options']['needed_pcs'])
    return need, int(-(-need // 1)) - 1


def verdicts(live):
    return {v['check']: (v['status'], v['code']) for v in live['verdicts']}


def intents(cur):
    b.api.admin(cur)
    return cur.execute('select count(*)from cp7_plan_native.intents').fetchone()[0]


def groups(cur):
    b.api.admin(cur)
    return cur.execute('select count(*)from erp.cutting_groups').fetchone()[0]


def cases(cur, today):
    def index_retained():
        x = single(cur, today)
        job = staged.job_row(cur, x['key'])['id']
        row = cur.execute('select x.row from cp7_analysis_stage.plan_targets x where x.job_id=%s and x.target_key=%s', (job, x['target'])).fetchone()[0]
        net = cur.execute("select payload from cp7_analysis_stage.target_rows where job_id=%s and kind='NETROW'and key=%s", (job, x['target'])).fetchone()[0]
        stock = cur.execute("select payload from cp7_analysis_stage.target_rows where job_id=%s and kind='STOCK'and key=%s", (job, x['target'])).fetchone()[0]
        for k in ('available_fg_pcs', 'target', 'production_policy', 'raw_gap_pcs', 'base_gap_pcs', 'conditional_gap_pcs',
                  'directed_on_time_good_pcs', 'candidate_allocated_good_pcs'):
            assert row[k] == net[k], (k, row[k], net[k])
        assert row['supplies'] == net['net']['inputs']['supplies'] and row['stock'] == [stock], 'P19P_INDEX_ROW'
        scope = cur.execute('select scope from cp7_analysis_stage.plan_scope where job_id=%s', (job,)).fetchone()[0]
        scenario = cur.execute("select cp7_analysis_stage.output(%s,'SCENARIO')->'scenario'", (job,)).fetchone()[0]
        assert scope['capacity'] == scenario['capacity'] and scope['wip_status'] == scenario['wip']['status'], 'P19P_INDEX_SCOPE'
        assert D(x['options']['capacity_pcs']) == D(scenario['capacity']['capacity_pcs']), 'P19P_OPTIONS_CAPACITY'
        assert x['options']['needed_pcs'] == net['conditional_gap_pcs'], 'P19P_OPTIONS_NEED'
        assert {a['id'] for a in x['options']['assumptions']} >= {a['id'] for a in row['assumptions'] + row['fabric_assumptions']}, 'P19P_TARGET_ASSUMPTIONS'
        purged = cur.execute('select cp7_analysis_stage.purge_intermediates(%s)', (job,)).fetchone()[0]
        assert purged['removed']['target_rows'] > 0, purged
        assert options(cur, x['query'])['needed_pcs'] == x['options']['needed_pcs'], 'P19P_INDEX_NOT_RETAINED'
        refused(cur, lambda: cur.execute('update cp7_analysis_stage.plan_targets set target_key=target_key where job_id=%s', (job,)), 'CP7_RUN_IMMUTABLE')
        refused(cur, lambda: cur.execute('delete from cp7_analysis_stage.plan_scope where job_id=%s', (job,)), 'CP7_RUN_IMMUTABLE')
        cur.execute('set local role cp7_capture')
        missing = refusal(cur, lambda: cur.execute("select cp7_analysis_stage.plan_target(gen_random_uuid(),'x')"))
        cur.execute('set local role cp7_capture')
        unknown = refusal(cur, lambda: cur.execute('select cp7_analysis_stage.plan_target(%s,%s)', (job, str(uuid.uuid4()) + ':' + str(uuid.uuid4()))))
        assert missing[1] == 'CP7_PLAN_V2_SNAPSHOT_INDEX_MISSING' and unknown[1] == 'CP7_PLAN_TARGET', (missing, unknown)
        return dict(status='PASS', target_index_equals_units=True, scope_equals_scenario=True, retained_after_purge=True, immutable=True,
                    missing_index_and_unknown_target_refused=True)

    def save_from_stale():
        x = single(cur, today)
        staged.location(cur, 'changed after the plan snapshot')
        previous.baseline.save(cur, previous.baseline.payload(cur, dict(product=x['root']), revision='1', daily_pcs='11'))
        check = staged.recorded_check(cur, x['run'], 'RECORDING_TIME')
        assert check['source_state'] == 'ARCHIVED_STALE', check
        before = b.boundary.snapshot(cur)
        d = save(cur, x['payload'])
        assert b.boundary.snapshot(cur) == before
        r = read(cur, d['draft_id'])
        assert d['contract_version'] == 'cp7.plan-draft.v2' and r['contract_version'] == 'cp7.plan-draft-read.v2' and r['state'] == 'SAVED', (d, r)
        assert r['data_as_of'] == d['data_as_of'] == x['options']['data_as_of'] and r['identity_hash'] == x['options']['identity_hash'], r
        s = r['snapshot']
        assert s['need_pcs'] == x['options']['needed_pcs'] and D(s['capacity_pcs']) == D(x['options']['capacity_pcs']), s
        assert D(s['available_fg_pcs']) == D(x['options']['available_fg_pcs']) and s['production_state'] == 'ACTIVE' and s['wip_model_size_pcs'] is not None, s
        whole = refusal(cur, lambda: plan.options(cur, dict(x['query'])))
        assert whole[0] == '42501' and whole[1] == 'CP7_PLAN_ORIGINAL_UNAVAILABLE', whole
        return dict(status='PASS', saved_from_archived_stale_snapshot=True, stored_identity_time_and_values=True, whole_original_v1_refuses_staged_run=True,
                    snapshot=s)

    def preview_read_only():
        x = single(cur, today)
        d = save(cur, x['payload'])
        before, money = b.boundary.snapshot(cur), monetary_state(cur)
        r = preview(cur, d['draft_id'])
        assert b.boundary.snapshot(cur) == before and monetary_state(cur) == money and 'native_payload' not in r
        live = r['live']
        assert r['contract_version'] == 'cp7.plan-preview-staged.v1' and r['status'] == 'READY_FOR_EXPLICIT_NATIVE_DRAFT' and live['apply_ready'] is True, r
        assert [v['check'] for v in live['verdicts']] == VERDICTS and all(v['status'] == 'OK' and v['code'] is None for v in live['verdicts']), live
        # Nothing changed since the snapshot: the live numbers are the snapshot's.
        assert D(live['fg_now_pcs']) == D(live['fg_snapshot_pcs']) and D(live['wip_now_pcs']) == D(live['wip_snapshot_pcs']), live
        assert D(live['increase_pcs']) == 0 and D(live['need_now_pcs']) == D(x['options']['needed_pcs']), live
        assert D(live['capacity_now_pcs']) == D(x['options']['capacity_pcs']) and D(live['capacity_used_by_other_plans_pcs']) == 0, live
        assert r['data_as_of'] == x['options']['data_as_of'] and r['identity_hash'] == x['options']['identity_hash'] and r['already_applied'] is False
        return dict(status='PASS', preview_writes_nothing=True, live_equals_snapshot_when_unchanged=True, verdicts=live['verdicts'])

    def apply_after_unrelated():
        x = single(cur, today)
        d = save(cur, x['payload'])
        staged.location(cur, 'unrelated change after the snapshot')
        money, n = monetary_state(cur), groups(cur)
        key = uuid.uuid4()
        p = action(d)
        out = apply(cur, p, key)
        assert out['contract_version'] == 'cp7.plan-apply-outcome.v2' and out['state'] == 'NATIVE_DRAFT_CREATED', out
        assert out['native']['material_issue_posted'] is False and groups(cur) == n + 1 and intents(cur) == 1 and monetary_state(cur) == money
        assert out['live']['apply_ready'] is True and out['data_as_of'] == x['options']['data_as_of'], out['live']
        assert apply(cur, p, key) == out, 'P19P_REPLAY'
        refused(cur, lambda: apply(cur, {**p, 'reason': 'changed'}, key), 'CP7_PLAN_REQUEST_CHANGED')
        refused(cur, lambda: apply(cur, p), 'CP7_PLAN_ALREADY_APPLIED')
        r = read(cur, d['draft_id'])
        assert r['state'] == 'NATIVE_DRAFT_CREATED' and r['native_intent']['cutting_group_id'] == out['native']['cutting_group_id'], r
        b.api.admin(cur)
        core = cur.execute('select core_hash from cp7_plan_native.intents where draft_id=%s', (d['draft_id'],)).fetchone()[0]
        assert core == x['options']['identity_hash'] and intents(cur) == 1
        return dict(status='PASS', unrelated_change_does_not_block=True, one_unposted_Native_draft_and_intent=True, replay_same_outcome=True,
                    money_stock_HPP_unchanged=True)

    def fg_increase():
        x = single(cur, today)
        d = save(cur, x['payload'])
        need, k = short_of_need(x)
        found_fg(cur, x, k)
        r = preview(cur, d['draft_id'])
        live = r['live']
        assert D(live['fg_now_pcs']) - D(live['fg_snapshot_pcs']) == k and D(live['need_now_pcs']) == need - k, live
        assert verdicts(live)['NEED'] == ('REFUSED', 'CP7_PLAN_V2_NEED_CHANGED') and live['apply_ready'] is False and r['status'] == 'REVIEW_REQUIRED', live
        n = groups(cur)
        detail = refused(cur, lambda: apply(cur, action(d)), 'CP7_PLAN_V2_NEED_CHANGED', '40001')
        assert detail['code'] == 'CP7_PLAN_V2_NEED_CHANGED' and D(detail['need_now_pcs']) == need - k and D(detail['selected_new_pcs']) == 2, detail
        assert D(detail['fg_now_pcs']) == D(detail['fg_snapshot_pcs']) + k and detail['data_as_of'] == x['options']['data_as_of'], detail
        assert groups(cur) == n and intents(cur) == 0
        return dict(status='PASS', finished_stock_up_need_down=True, refused_40001_with_numbers=detail, no_Native_draft_or_intent=True)

    def wip_increase():
        x = single(cur, today)
        d = save(cur, x['payload'])
        need, k = short_of_need(x)
        posted_cut(cur, x, k, today)
        live = preview(cur, d['draft_id'])['live']
        assert D(live['wip_now_pcs']) - D(live['wip_snapshot_pcs']) == k and D(live['fg_now_pcs']) == D(live['fg_snapshot_pcs']), live
        assert verdicts(live)['NEED'] == ('REFUSED', 'CP7_PLAN_V2_NEED_CHANGED') and verdicts(live)['WIP'] == ('OK', None), live
        n = groups(cur)
        detail = refused(cur, lambda: apply(cur, action(d)), 'CP7_PLAN_V2_NEED_CHANGED', '40001')
        assert D(detail['need_now_pcs']) == need - k and D(detail['increase_pcs']) == k, detail
        assert groups(cur) == n and intents(cur) == 0
        return dict(status='PASS', posted_cut_of_same_model_size_counts_as_WIP=True, refused_40001_with_numbers=detail)

    def policy_changed():
        x = single(cur, today)
        d = save(cur, x['payload'])
        policy(cur, x, 'PAUSED')
        live = preview(cur, d['draft_id'])['live']
        assert verdicts(live)['POLICY'] == ('REFUSED', 'CP7_PLAN_V2_POLICY_CHANGED') and live['policy_state'] == 'PAUSED', live
        detail = refused(cur, lambda: apply(cur, action(d)), 'CP7_PLAN_V2_POLICY_CHANGED', '40001')
        assert intents(cur) == 0
        policy(cur, x, 'ACTIVE')
        out = apply(cur, action(d))
        assert out['state'] == 'NATIVE_DRAFT_CREATED' and intents(cur) == 1
        return dict(status='PASS', paused_policy_refused=True, active_again_applies=True, detail=detail)

    def capacity_used():
        first, second = two(cur, today)
        a, b_ = capacity_split(first, second)
        d1, d2 = save(cur, with_pcs(first['payload'], a)), save(cur, with_pcs(second['payload'], b_))
        apply(cur, action(d1))
        live = preview(cur, d2['draft_id'])['live']
        assert verdicts(live)['CAPACITY'] == ('REFUSED', 'CP7_PLAN_V2_CAPACITY_USED') and D(live['capacity_used_by_other_plans_pcs']) == a, live
        detail = refused(cur, lambda: apply(cur, action(d2)), 'CP7_PLAN_V2_CAPACITY_USED', '40001')
        assert D(detail['capacity_now_pcs']) == D(first['options']['capacity_pcs']) - a and D(detail['selected_new_pcs']) == b_, detail
        assert intents(cur) == 1
        return dict(status='PASS', one_shared_centre=True, other_target_plan_after_snapshot_uses_capacity=True, split=[a, b_], detail=detail)

    def v1_v2_shared_capacity():
        """P20 F01: a v2 plan already uses the one shared capacity centre; a v1 plan (an Original captured after it)
        one piece over what is left is refused with its numbers, and the v1 plan that fits exactly is accepted."""
        first, second = two(cur, today)
        c = int(D(first['options']['capacity_pcs']))
        a, b_ = capacity_split(first, second)
        assert a >= 2, ('P19P_V1_FIT_NEEDS_TWO', a)
        out2 = apply(cur, action(save(cur, with_pcs(second['payload'], b_))))
        assert out2['state'] == 'NATIVE_DRAFT_CREATED', out2
        over = v1_draft(cur, first, a, today)
        detail = refused(cur, lambda: plan.apply(cur, action(over)), 'CP7_PLAN_CAPACITY_USED', '40001')
        assert (D(detail['capacity_used_by_other_plans_pcs']), D(detail['capacity_now_pcs']), D(detail['selected_new_pcs'])) == (b_, c - b_, a), detail
        fit = v1_draft(cur, first, a - 1, today)
        out1 = plan.apply(cur, action(fit))
        assert out1['state'] == 'NATIVE_DRAFT_CREATED' and intents(cur) == 2, out1
        assert planned_pcs(cur, [fit]) + b_ == c
        return dict(status='PASS', capacity=c, v2_first=b_, v1_one_over_refused=detail, v1_exact_fit_accepted=a - 1, total=c)

    def planned_and_linked():
        x = single(cur, today)
        apply(cur, action(save(cur, x['payload'])))
        again = save(cur, x['payload'])
        live = preview(cur, again['draft_id'])['live']
        assert verdicts(live)['TARGET_PLANS'] == ('REFUSED', 'CP7_PLAN_V2_TARGET_PLANNED'), live
        refused(cur, lambda: apply(cur, action(again)), 'CP7_PLAN_V2_TARGET_PLANNED', '40001')
        # A later snapshot sees that plan as earlier work: its unposted Native
        # draft is v1's linked-intent conflict, refused the same way.
        plan.review_work(cur, today)
        run, _ = snapshot(cur, today)
        _, _, p = draft_payload(cur, x, run)
        later = save(cur, p)
        live = preview(cur, later['draft_id'])['live']
        assert verdicts(live)['TARGET_PLANS'] == ('OK', None) and verdicts(live)['LINKED_PLANS'] == ('REFUSED', 'CP7_PLAN_LINKED_INTENT_CONFLICT'), live
        refused(cur, lambda: apply(cur, action(later)), 'CP7_PLAN_LINKED_INTENT_CONFLICT', '40001')
        assert intents(cur) == 1
        return dict(status='PASS', plan_after_snapshot_target_planned=True, earlier_unposted_plan_linked_conflict=True)

    def fields_kinds_access():
        subject, role = plan.custom(cur)
        x = single(cur, today, subject)
        p = x['payload']
        for extra in ('source_hash', 'quantity_override', 'reservation'):
            refused(cur, lambda extra=extra: save(cur, {**p, extra: True}, subject=subject), 'CP7_PLAN_FIELDS')
        refused(cur, lambda: save(cur, {**p, 'identity_hash': '0' * 64}, subject=subject), 'CP7_PLAN_REVIEW')
        refused(cur, lambda: save(cur, {**p, 'reviewed_assumption_ids': p['reviewed_assumption_ids'][1:]}, subject=subject), 'CP7_PLAN_ASSUMPTIONS_NOT_REVIEWED')
        refused(cur, lambda: save(cur, with_pcs(p, int(D(x['options']['needed_pcs'])) + 1000000), subject=subject), 'CP7_PLAN_QUANTITY_EXCEEDS_NEED_OR_CAPACITY')
        d = save(cur, p, subject=subject)
        other, _ = plan.custom(cur)
        for op in (lambda: read(cur, d['draft_id'], other), lambda: preview(cur, d['draft_id'], other), lambda: apply(cur, action(d), subject=other)):
            refused(cur, op, 'CP7_PLAN_DRAFT_UNAVAILABLE', '42501')
        refused(cur, lambda: options(cur, x['query'], other), 'CP7_PLAN_V2_SNAPSHOT_UNAVAILABLE', '42501')
        refused(cur, lambda: plan.preview(cur, d['draft_id'], subject), 'CP7_PLAN_FIELDS')
        # A v1 draft (its own whole Original, the unchanged v1 command) is not a v2 draft.
        v1 = plan.save(cur, plan.setup(cur, today, subject)['payload'], subject=subject)['draft_id']
        for op in (lambda: read(cur, v1, subject), lambda: preview(cur, v1, subject), lambda: apply(cur, dict(draft_id=str(v1), expected_revision='1',
                   explicit_review=True, reason='v1 draft to v2'), subject=subject)):
            refused(cur, op, 'CP7_PLAN_V2_DRAFT_KIND')
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.cutting.create'", (role,))
        refused(cur, lambda: apply(cur, action(d), subject=subject), 'CP7_PLAN_ACCESS_DENIED', '42501')
        refused(cur, lambda: save(cur, p, subject=subject), 'CP7_PLAN_ACCESS_DENIED', '42501')
        assert read(cur, d['draft_id'], subject)['state'] == 'SAVED' and intents(cur) == 0
        assert not cur.execute("select has_function_privilege('cp7_capture','public.erp_cp7_apply_plan_action_v2(jsonb,uuid)','EXECUTE')"
                               "or has_function_privilege('authenticated','cp7_plan_native.staged_live(uuid,text)','EXECUTE')"
                               "or has_function_privilege('authenticated','cp7_plan_native.staged_source(uuid,text)','EXECUTE')").fetchone()[0]
        return dict(status='PASS', closed_fields=True, identity_and_review_bound=True, foreign_actor_denied=True, kinds_never_mixed=True,
                    current_create_permission_required=True, capabilities_private=True)

    return list(zip(IDS['native'], (index_retained, save_from_stale, preview_read_only, apply_after_unrelated, fg_increase, wip_increase,
                                    policy_changed, capacity_used, planned_and_linked, fields_kinds_access, v1_v2_shared_capacity)))


def races(tools, today):
    def waiting(workers, kind='advisory'):
        with tools.connect(autocommit=True) as inspect, inspect.cursor() as c:
            deadline, seen = time.monotonic() + 10, []
            while time.monotonic() < deadline:
                seen = c.execute("select pid from pg_locks where pid=any(%s)and locktype=%s and not granted", (workers, kind)).fetchall()
                if len(seen) == len(workers):
                    break
                time.sleep(.05)
        assert len(seen) == len(workers), ('P19P_WAIT_NOT_OBSERVED', kind, seen)
        return [r[0] for r in seen]

    def send(d, key, pids, gate=None, subject=None):
        with tools.connect() as conn, conn.cursor() as cur:
            pids.put(cur.execute('select pg_backend_pid()').fetchone()[0])
            if gate:
                gate.wait(timeout=8)
            try:
                result = apply(cur, action(d), key, subject)
                conn.commit()
                return result
            except psycopg.Error as e:
                conn.rollback()
                return dict(error=e.diag.message_primary, sqlstate=e.sqlstate, detail=e.diag.message_detail)

    def capacity_two_targets():
        with tools.connect() as conn, conn.cursor() as cur:
            first, second = two(cur, today)
            a, b_ = capacity_split(first, second)
            d1, d2 = save(cur, with_pcs(first['payload'], a)), save(cur, with_pcs(second['payload'], b_))
            conn.commit()
        pids, gate = Queue(), threading.Barrier(2)
        with tools.connect() as holder, holder.cursor() as h:
            h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:PLAN_CAPACITY',0))")
            with ThreadPoolExecutor(max_workers=2) as pool:
                jobs = [pool.submit(send, d, uuid.uuid4(), pids, gate) for d in (d1, d2)]
                workers = [pids.get(timeout=8), pids.get(timeout=8)]
                try:
                    observed = waiting(workers)
                finally:
                    holder.commit()
                results = [j.result(60) for j in jobs]
        won = [r for r in results if r.get('kind') == 'COMMITTED_OUTCOME']
        lost = [r for r in results if r.get('sqlstate') == '40001']
        assert len(won) == len(lost) == 1 and lost[0]['error'] == 'CP7_PLAN_V2_CAPACITY_USED', results
        with tools.connect() as conn, conn.cursor() as cur:
            assert intents(cur) == 1
        return dict(status='PASS', both_waited_on_the_one_capacity_lock=observed, one_committed_other_capacity_used=True, refusal=lost[0])

    def same_target():
        with tools.connect() as conn, conn.cursor() as cur:
            x = single(cur, today)
            d1, d2 = save(cur, x['payload']), save(cur, x['payload'])
            conn.commit()
        pids, gate = Queue(), threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(send, d, uuid.uuid4(), pids, gate) for d in (d1, d2)]
            results = [j.result(60) for j in jobs]
        won = [r for r in results if r.get('kind') == 'COMMITTED_OUTCOME']
        lost = [r for r in results if r.get('sqlstate') == '40001']
        assert len(won) == len(lost) == 1 and lost[0]['error'] == 'CP7_PLAN_V2_TARGET_PLANNED', results
        with tools.connect() as conn, conn.cursor() as cur:
            assert intents(cur) == 1
        return dict(status='PASS', two_drafts_same_target_one_plan=True, refusal=lost[0]['error'])

    def fg_while_waiting():
        with tools.connect() as conn, conn.cursor() as cur:
            x = single(cur, today)
            d = save(cur, x['payload'])
            need, k = short_of_need(x)
            n = groups(cur)
            conn.commit()
        pids = Queue()
        with tools.connect() as holder, holder.cursor() as h:
            h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:PLAN_CAPACITY',0))")
            with ThreadPoolExecutor(max_workers=1) as pool:
                job = pool.submit(send, d, uuid.uuid4(), pids)
                worker = pids.get(timeout=8)
                try:
                    waiting([worker])
                    # Finished stock arrives and commits while the apply waits.
                    with tools.connect() as w, w.cursor() as c:
                        found_fg(c, x, k)
                        w.commit()
                finally:
                    holder.commit()
                result = job.result(60)
        assert result.get('sqlstate') == '40001' and result['error'] == 'CP7_PLAN_V2_NEED_CHANGED', result
        detail = json.loads(result['detail'])
        assert D(detail['need_now_pcs']) == need - k, detail
        with tools.connect() as conn, conn.cursor() as cur:
            assert intents(cur) == 0 and groups(cur) == n
        return dict(status='PASS', stock_committed_during_wait_seen_after_lock=True, refused_without_Native_draft=True, detail=detail)

    def intent_in_flight():
        """A plan applied in a transaction still running when the snapshot is read: it is after the snapshot
        (the snapshot did not see it) although it was recorded before the capture time."""
        with tools.connect() as conn, conn.cursor() as cur:
            x = fixture(cur, today)
            conn.commit()
        with tools.connect() as conn, conn.cursor() as cur:
            run0, _ = snapshot(cur, today)
            _, _, p0 = draft_payload(cur, x, run0)
            d0 = save(cur, p0)
            conn.commit()
        key = uuid.uuid4()
        with tools.connect() as w, w.cursor() as c:
            first = apply(c, action(d0))
            recorded = c.execute('select recorded_at from cp7_plan_native.intents where draft_id=%s', (d0['draft_id'],)).fetchone()[0]
            with tools.connect() as conn, conn.cursor() as cur:
                staged.checked(staged.request(cur, today, key), key, 'RUNNING')
                conn.commit()
            w.commit()
        with tools.connect() as conn, conn.cursor() as cur:
            done, _ = staged.drive(cur, key)
            conn.commit()
            captured = datetime.fromisoformat(staged.job_row(cur, key)['captured_at'])
            boundary = cur.execute('select source_snapshot is not null from cp7_analysis_stage.capture_marks where job_id=(select id from cp7_analysis_stage.jobs where request_id=%s)', (key,)).fetchone()[0]
            _, _, p = draft_payload(cur, x, done['run_id'])
            d = save(cur, p)
            live = preview(cur, d['draft_id'])['live']
            conn.commit()
        assert boundary is True and recorded < captured, ('P19P_IN_FLIGHT_FIXTURE', boundary, recorded, captured)
        assert verdicts(live)['TARGET_PLANS'] == ('REFUSED', 'CP7_PLAN_V2_TARGET_PLANNED'), live
        with tools.connect() as conn, conn.cursor() as cur:
            refused(cur, lambda: apply(cur, action(d)), 'CP7_PLAN_V2_TARGET_PLANNED', '40001')
            conn.rollback()
        return dict(status='PASS', capture_boundary='SNAPSHOT', plan_in_flight_at_capture_is_after_the_snapshot=True,
                    recorded_before_capture_time=True, first=first['state'])

    def held(kind, d):
        """Apply one plan (kind 'v1' or 'v2') in an open transaction: it holds the capacity lock until commit/rollback."""
        conn = tools.connect()
        cur = conn.cursor()
        out = (plan.apply if kind == 'v1' else apply)(cur, action(d))
        assert out['state'] == 'NATIVE_DRAFT_CREATED', out
        return conn, out

    def apply_kind(kind, d, pids):
        with tools.connect() as conn, conn.cursor() as cur:
            pids.put(cur.execute('select pg_backend_pid()').fetchone()[0])
            try:
                result = (plan.apply if kind == 'v1' else apply)(cur, action(d))
                conn.commit()
                return result
            except psycopg.Error as e:
                conn.rollback()
                return dict(error=e.diag.message_primary, sqlstate=e.sqlstate, detail=e.diag.message_detail)

    def cross(first_kind, second_kind, finish):
        """P20 F01 (AS20-32): one version applies in an open transaction, the other version applies on another target
        of the same capacity centre and must wait on the capacity lock; then the first commits or rolls back."""
        with tools.connect() as conn, conn.cursor() as cur:
            first, second = two(cur, today)
            c = int(D(first['options']['capacity_pcs']))
            a, b_ = capacity_split(first, second)
            draft = lambda kind, x, pcs: v1_draft(cur, x, pcs, today) if kind == 'v1' else save(cur, with_pcs(x['payload'], pcs))
            d1, d2 = draft(first_kind, first, a), draft(second_kind, second, b_)
            conn.commit()
        pids = Queue()
        holder, out1 = held(first_kind, d1)
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                job = pool.submit(apply_kind, second_kind, d2, pids)
                observed = waiting([pids.get(timeout=8)])
                (holder.commit if finish == 'commit' else holder.rollback)()
                result = job.result(60)
        finally:
            holder.close()
        with tools.connect() as conn, conn.cursor() as cur:
            total = planned_pcs(cur, [d1, d2])
        assert total <= c, ('P19P_CAPACITY_EXCEEDED', c, total, result)
        return dict(capacity=c, quantities=[a, b_], first_version=first_kind, second_version=second_kind, waited_on_capacity_lock=observed,
                    first_finished=finish, second_result=result, committed_total=str(total)), (first, second, c, a, b_)

    def v1_holds_v2_refused():
        out, (first, second, c, a, b_) = cross('v1', 'v2', 'commit')
        r = out['second_result']
        assert r.get('sqlstate') == '40001' and r['error'] == 'CP7_PLAN_V2_CAPACITY_USED', r
        detail = json.loads(r['detail'])
        assert D(detail['capacity_used_by_other_plans_pcs']) == a and D(detail['capacity_now_pcs']) == c - a, detail
        # Exact fit after the v1 plan committed: c - a pieces of the v2 plan are accepted (the 59 + 1 control).
        with tools.connect() as conn, conn.cursor() as cur:
            fit = save(cur, with_pcs(second['payload'], c - a))
            accepted = apply(cur, action(fit))
            conn.commit()
            assert accepted['state'] == 'NATIVE_DRAFT_CREATED' and intents(cur) == 2, accepted
        return dict(status='PASS', **out, v2_refusal=detail, exact_fit_accepted=[a, c - a])

    def v2_holds_v1_refused():
        out, (first, second, c, a, b_) = cross('v2', 'v1', 'commit')
        r = out['second_result']
        # The v1 plan's own Original may also have changed (the v2 plan's Native draft); either refusal keeps the total.
        assert r.get('sqlstate') == '40001' and r['error'] in ('CP7_PLAN_CAPACITY_USED', 'CP7_PLAN_SOURCE_CHANGED'), r
        if r['error'] == 'CP7_PLAN_CAPACITY_USED':
            detail = json.loads(r['detail'])
            assert D(detail['capacity_used_by_other_plans_pcs']) == a and D(detail['capacity_now_pcs']) == c - a, detail
        with tools.connect() as conn, conn.cursor() as cur:
            assert intents(cur) == 1
        return dict(status='PASS', **out, v1_refusal=r['error'])

    def v1_rollback_frees():
        out, (first, second, c, a, b_) = cross('v1', 'v2', 'rollback')
        r = out['second_result']
        assert r.get('state') == 'NATIVE_DRAFT_CREATED', r
        with tools.connect() as conn, conn.cursor() as cur:
            assert intents(cur) == 1 and D(out['committed_total']) == b_
        return dict(status='PASS', **{k: v for k, v in out.items() if k != 'second_result'}, second_committed_after_rollback=True)

    return list(zip(IDS['races'], (capacity_two_targets, same_target, fg_while_waiting, intent_in_flight,
                                   v1_holds_v2_refused, v2_holds_v1_refused, v1_rollback_frees)))


def http_cases(http, today):
    state = {}

    def flow():
        owner = http.login('OWNER', 'p19p-owner')
        other = http.login('OWNER', 'p19p-other')
        with http.connect() as conn, conn.cursor() as cur:
            x = single(cur, today, owner.auth_user_id)
            conn.commit()

        def ok(user, name, args):
            r = user.rpc(name, args)
            assert r['status'] == 200, (name, r)
            return r['body']
        o = ok(owner, 'erp_cp7_get_plan_options_v2', dict(p_query=x['query']))
        assert o['identity_hash'] == x['payload']['identity_hash']
        saved = ok(owner, 'erp_cp7_save_plan_draft_v2', dict(p_payload=x['payload'], p_request=str(uuid.uuid4())))
        assert ok(owner, 'erp_cp7_read_plan_draft_v2', dict(p_draft=saved['draft_id']))['state'] == 'SAVED'
        v = ok(owner, 'erp_cp7_preview_plan_action_v2', dict(p_draft=saved['draft_id']))
        assert v['live']['apply_ready'] is True, v['live']
        args = dict(p_payload=action(saved), p_request=str(uuid.uuid4()))
        one = ok(owner, 'erp_cp7_apply_plan_action_v2', args)
        assert ok(owner, 'erp_cp7_apply_plan_action_v2', args) == one and one['state'] == 'NATIVE_DRAFT_CREATED'
        foreign = [other.rpc(name, payload)['status'] for name, payload in (
            ('erp_cp7_get_plan_options_v2', dict(p_query=x['query'])), ('erp_cp7_read_plan_draft_v2', dict(p_draft=saved['draft_id'])),
            ('erp_cp7_preview_plan_action_v2', dict(p_draft=saved['draft_id'])), ('erp_cp7_apply_plan_action_v2', args))]
        assert foreign == [403] * 4, foreign
        anonymous = [http.anon_rpc(name, payload)['status'] for name, payload in (
            ('erp_cp7_get_plan_options_v2', dict(p_query=x['query'])), ('erp_cp7_save_plan_draft_v2', dict(p_payload=x['payload'], p_request=str(uuid.uuid4()))),
            ('erp_cp7_read_plan_draft_v2', dict(p_draft=saved['draft_id'])), ('erp_cp7_preview_plan_action_v2', dict(p_draft=saved['draft_id'])),
            ('erp_cp7_apply_plan_action_v2', args))]
        assert all(code in (401, 403) for code in anonymous), anonymous
        again = ok(owner, 'erp_cp7_save_plan_draft_v2', dict(p_payload=x['payload'], p_request=str(uuid.uuid4())))
        planned = owner.rpc('erp_cp7_apply_plan_action_v2', dict(p_payload=action(again), p_request=str(uuid.uuid4())))
        assert planned['status'] >= 400 and 'CP7_PLAN_V2_TARGET_PLANNED' in json.dumps(planned['body']), planned
        with http.connect() as conn, conn.cursor() as cur:
            assert intents(cur) == 1
        state.update(owner=owner, x=x, saved=saved, args=args)
        return dict(status='PASS', real_Auth_options_save_read_preview_apply_replay=True, foreign_403=foreign, anonymous_refused=anonymous,
                    target_planned_over_HTTP=planned['status'])

    def revoked():
        assert state, 'P19P_REQUIRED_PRIOR_HTTP_CASE'
        owner, saved = state['owner'], state['saved']
        with http.connect() as conn, conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (owner.auth_user_id,))
            conn.commit()
        codes = [owner.rpc(name, payload)['status'] for name, payload in (
            ('erp_cp7_get_plan_options_v2', dict(p_query=state['x']['query'])),
            ('erp_cp7_save_plan_draft_v2', dict(p_payload=state['x']['payload'], p_request=str(uuid.uuid4()))),
            ('erp_cp7_read_plan_draft_v2', dict(p_draft=saved['draft_id'])), ('erp_cp7_preview_plan_action_v2', dict(p_draft=saved['draft_id'])),
            ('erp_cp7_apply_plan_action_v2', state['args']))]
        assert codes == [403] * 5, codes
        with http.connect() as conn, conn.cursor() as cur:
            assert intents(cur) == 1
        return dict(status='PASS', deactivated_user_all_five_403=True, no_new_effect=True)

    return list(zip(IDS['http'], (flow, revoked)))

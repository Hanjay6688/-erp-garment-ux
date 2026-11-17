"""Auditor-owned APPLY assertions on the admitted installed Global candidate.

Native fixture builders are retained product code. Expected quantities and
effects below are fixed before dispatch, independently of observed outputs.
"""
from datetime import timedelta
from decimal import Decimal as D
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import cp7_p19_plan_v2_cases as plan

SOURCE_SHA256 = '3f9e33ebc733d0bf7d49c00ce17899ec2ce6c6b8300661720767c6763eab412a'
FG = 'P19P_FG_INCREASE_NEED_CHANGED'
WIP = 'P19P_WIP_INCREASE_NEED_CHANGED'
UNRELATED = 'P19P_APPLY_AFTER_UNRELATED_CHANGE'
PERMISSION = 'P20_PLANNER_CURRENT_CUTTING_PERMISSION'
NATIVE_IDS = (FG, WIP, UNRELATED)
IDS = (*NATIVE_IDS, PERMISSION)
BASELINE = dict(fg='15', wip='40', need='85', capacity='60', selected='2')


def require(ok, code):
    if not ok:
        raise AssertionError(code)


def require_baseline(ok, observed):
    if not ok:
        error = AssertionError('AUDITOR_P20_PLANNER_FIXTURE_BASELINE_MISMATCH')
        error.audit_observed = observed
        raise error


def verify_source():
    require(sha256(Path(plan.__file__).read_bytes()).hexdigest() == SOURCE_SHA256,
            'AUDITOR_P20_PLANNER_FIXTURE_SOURCE_CHANGED')


def numbers(live):
    return {key: str(D(live[field]).normalize()) if D(live[field]) % 1 else str(int(D(live[field])))
            for key, field in (('fg', 'fg_now_pcs'), ('wip', 'wip_now_pcs'),
                               ('need', 'need_now_pcs'), ('capacity', 'capacity_now_pcs'),
                               ('selected', 'selected_new_pcs'))}


def marker(cur):
    """Transactional boundaries; full recovery additionally checks sequences."""
    plan.b.api.admin(cur)
    state = dict(money=plan.monetary_state(cur), groups=plan.groups(cur), intents=plan.intents(cur), tables={})
    for table in ('drafts', 'staged_drafts', 'commands', 'intents'):
        state['tables'][table] = cur.execute('select count(*),md5(coalesce(jsonb_agg(to_jsonb(t) '
            'order by to_jsonb(t)::text)::text,\'[]\')) from cp7_plan_native.' + table + ' t').fetchone()
    return state


def setup(cur, today, subject=None):
    verify_source()
    require(plan.intents(cur) == 0, 'AUDITOR_P20_PLANNER_PRIOR_INTENT_BASELINE_MISMATCH')
    x = plan.fixture(cur, today)
    if subject is not None:
        # Review the calendar using the SAME actor as snapshot/draft/APPLY.
        capture = plan.schedule.supply.capture(cur, today, subject=subject)
        revision = cur.execute('select max(revision)::text from cp7_schedule_native.plans').fetchone()[0]
        schedule = plan.schedule.payload(cur, capture, revision)
        load = sum(int(step['remaining_minutes']) for pos in schedule['config']['positions']
                   for step in pos['remaining_steps'])
        start = plan.now(cur).replace(microsecond=0) + timedelta(hours=1)
        schedule['config']['windows'] = [dict(key='aud-p20-plan-operator-shift',
            starts_at=plan.schedule.stamp(start), ends_at=plan.schedule.stamp(start + timedelta(minutes=load + 120)),
            other_load_minutes='0')]
        schedule['config']['through_at'] = plan.schedule.stamp(start + timedelta(minutes=load + 180))
        plan.schedule.save(cur, schedule, subject=subject)
    run, work = plan.snapshot(cur, today, subject)
    options, query, payload = plan.draft_payload(cur, x, run, subject)
    observed = {key: options.get(key) for key in ('needed_pcs', 'capacity_pcs', 'available_fg_pcs', 'production_state')}
    require_baseline(options['needed_pcs'] is not None and options['capacity_pcs'] is not None, observed)
    require_baseline(D(options['needed_pcs']) == 85 and D(options['capacity_pcs']) == 60
            and D(options['available_fg_pcs']) == 15 and options['production_state'] == 'ACTIVE', observed)
    draft = plan.save(cur, payload, subject=subject)
    preview = plan.preview(cur, draft['draft_id'], subject)
    require_baseline(numbers(preview['live']) == BASELINE and preview['live']['apply_ready'] is True,
                     numbers(preview['live']))
    x.update(run=run, key=work, options=options, query=query, payload=payload)
    return x, draft


def native(cur, today, case_id):
    x, draft = setup(cur, today)
    if case_id in (FG, WIP):
        if case_id == FG:
            plan.found_fg(cur, x, 84)
            expected = dict(fg='99', wip='40', need='1', capacity='60', selected='2')
        else:
            plan.posted_cut(cur, x, 84, today)
            expected = dict(fg='15', wip='124', need='1', capacity='60', selected='2')
        live = plan.preview(cur, draft['draft_id'])['live']
        require(numbers(live) == expected and live['apply_ready'] is False,
                'AUDITOR_P20_PLANNER_CHANGED_NEED_NUMBERS')
        before = marker(cur)
        state, code, detail = plan.refusal(cur, lambda: plan.apply(cur, plan.action(draft)))
        require((state, code) == ('40001', 'CP7_PLAN_V2_NEED_CHANGED')
                and numbers(detail) == expected and D(detail['increase_pcs']) == 84,
                'AUDITOR_P20_PLANNER_CHANGED_NEED_REFUSAL')
        require(marker(cur) == before and plan.read(cur, draft['draft_id'])['state'] == 'SAVED',
                'AUDITOR_P20_PLANNER_DENIED_CHANGED_STATE')
        return dict(status='PASS', baseline=BASELINE, observed=numbers(detail),
            sqlstate=state, code=code, native_draft_delta=0, intent_delta=0,
            apply_ready=False, money_stock_HPP_unchanged=True)
    require(case_id == UNRELATED, 'AUDITOR_P20_UNKNOWN_PLANNER_CASE')
    plan.staged.location(cur, 'P20 auditor unrelated location')
    old = plan.monetary_state(cur)
    groups, intents = plan.groups(cur), plan.intents(cur)
    request = uuid4()
    payload = plan.action(draft)
    result = plan.apply(cur, payload, request)
    require(result['state'] == 'NATIVE_DRAFT_CREATED' and result['native']['material_issue_posted'] is False
            and plan.groups(cur) == groups + 1 and plan.intents(cur) == intents + 1
            and plan.monetary_state(cur) == old, 'AUDITOR_P20_PLANNER_APPLY_EFFECT')
    after = marker(cur)
    require(plan.apply(cur, payload, request) == result and marker(cur) == after,
            'AUDITOR_P20_PLANNER_REPLAY_EFFECT')
    plan.refused(cur, lambda: plan.apply(cur, {**payload, 'reason': 'changed'}, request), 'CP7_PLAN_REQUEST_CHANGED')
    plan.refused(cur, lambda: plan.apply(cur, payload), 'CP7_PLAN_ALREADY_APPLIED')
    require(marker(cur) == after, 'AUDITOR_P20_PLANNER_REJECTED_REPEAT_EFFECT')
    return dict(status='PASS', baseline=BASELINE, state=result['state'], native_draft_delta=1,
        intent_delta=1, material_issue_posted=False, money_stock_HPP_unchanged=True,
        exact_uuid_replay=True, changed_request_code='CP7_PLAN_REQUEST_CHANGED',
        repeat_new_uuid_code='CP7_PLAN_ALREADY_APPLIED')


def permission(conn, cur, today):
    """Committed revoke; must be last, before owning full database recovery."""
    subject = str(uuid4())
    plan.b.api.admin(cur)
    role, = cur.execute('''insert into erp.app_users(auth_user_id,full_name,role,role_id,is_active)
        select %s,'P20 auditor synthetic plan operator','ADMIN',id,true
        from erp.app_roles where role_code='ADMIN' and is_active returning role_id''', (subject,)).fetchone()
    key = 'production.cutting.create'
    original = cur.execute('''select role_id,permission_key,granted_by,granted_at
        from erp.app_role_permissions where role_id=%s and permission_key=%s''', (role, key)).fetchone()
    require(original is not None, 'AUDITOR_P20_PLANNER_ADMIN_GRANT_REQUIRED')
    _, draft = setup(cur, today, subject)
    before = marker(cur)
    conn.commit()
    # Freeze the token/subject mapping; the same Native actor must see revocation.
    revoked = cur.execute('''delete from erp.app_role_permissions where role_id=%s and permission_key=%s
        returning role_id,permission_key,granted_by,granted_at''', (role, key)).fetchone()
    require(revoked == original, 'AUDITOR_P20_PLANNER_EXACT_GRANT_REVOKE')
    conn.commit()
    request, payload = uuid4(), plan.action(draft)
    try:
        state, code, _ = plan.refusal(cur, lambda: plan.apply(cur, payload, request, subject))
        require((state, code) == ('42501', 'CP7_PLAN_ACCESS_DENIED'), 'AUDITOR_P20_PLANNER_CURRENT_PERMISSION')
        require(plan.read(cur, draft['draft_id'], subject)['state'] == 'SAVED' and marker(cur) == before,
                'AUDITOR_P20_PLANNER_PERMISSION_REFUSAL_EFFECT')
    finally:
        conn.rollback()
        cur.execute('''insert into erp.app_role_permissions(role_id,permission_key,granted_by,granted_at)
            values(%s,%s,%s,%s)''', original)
        conn.commit()
    actual = cur.execute('''select role_id,permission_key,granted_by,granted_at
        from erp.app_role_permissions where role_id=%s and permission_key=%s''', (role, key)).fetchone()
    require(actual == original, 'AUDITOR_P20_PLANNER_EXACT_GRANT_RESTORE')
    result = plan.apply(cur, payload, request, subject)
    require(result['state'] == 'NATIVE_DRAFT_CREATED' and result['native']['material_issue_posted'] is False
            and plan.groups(cur) == before['groups'] + 1 and plan.intents(cur) == before['intents'] + 1
            and plan.monetary_state(cur) == before['money'], 'AUDITOR_P20_PLANNER_RESTORED_APPLY_EFFECT')
    after = marker(cur)
    require(plan.apply(cur, payload, request, subject) == result and marker(cur) == after,
            'AUDITOR_P20_PLANNER_RESTORED_REPLAY_EFFECT')
    return dict(status='PASS', baseline=BASELINE, sqlstate=state, code=code, draft_state_when_denied='SAVED',
        native_draft_delta_denied=0, intent_delta_denied=0, native_draft_delta_after_restore=1,
        intent_delta_after_restore=1, material_issue_posted=False, money_stock_HPP_unchanged=True,
        exact_grant_restored=True, exact_uuid_replay=True, revocation_committed=True, real_auth_http=False)

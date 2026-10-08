"""P19 reminders v2: reminders from a staged analysis snapshot (snapshot contract v2 §5).

Owner decision 8 Oct 2026: reminders may use the snapshot as analysis, labelled
with its time; before a reminder is "sent" (here: a local preview is claimed,
and again when it is finished) the condition is checked again against the ERP
as it is now, in the same transaction after the last lock, so that a condition
already resolved is never billed. The snapshot conditions are built once per
run, one page per ordinary request under the unchanged 8 s limit, and never
change. Receivables and payables are always read now with the v1 readers.
Delivery stays the local preview record: nothing is sent outside the ERP.
Real Native facts through the ordinary writers (the plan v2, fabric and
receivable fixtures), real staged runs, real concurrent sessions and real
Auth/PostgREST calls on the closed harness; v1 is not changed by any case.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import hashlib
import json
import math
import threading
import time
import uuid

import psycopg

import cp7_p19_staged_cases as staged
import cp7_p19_plan_v2_cases as planv2
import cp7_fabric_physical_cases as physical
import cp7_rule_source_cases as rules

IDS = dict(
    native=['P19M_SET_STEPS_SEAL', 'P19M_RESOLVED_AFTER_SNAPSHOT_NOT_SENT', 'P19M_STILL_OPEN_SENT_ONCE', 'P19M_PARTIAL_AND_THRESHOLD',
            'P19M_FABRIC_HELD_ON_MATERIAL_CHANGE', 'P19M_AR_PAID_NOT_SENT', 'P19M_POLICY_AND_DESTINATION', 'P19M_REQUEST_ONE_UUID',
            'P19M_AUTHORITY_AND_V1_APART'],
    races=['P19M_RACE_TWO_CLAIMS_ONE_CLAIM', 'P19M_RACE_FG_COMMITTED_WHILE_WAITING', 'P19M_RACE_TWO_STEPS_ONE_UNIT'],
    http=['P19M_HTTP_FLOW', 'P19M_HTTP_REVOKED'],
    browser=['P19M_BROWSER_DESKTOP_REMINDERS', 'P19M_BROWSER_MOBILE_REMINDERS'],
)
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = sum(REQUIRED.values())
CONTRACT = 'cp7.p19.reminder-v2.v1'
FUNCTIONS = ('erp_cp7_step_reminder_conditions_v2', 'erp_cp7_read_reminder_conditions_v2', 'erp_cp7_get_reminder_obligations_v2',
             'erp_cp7_recheck_reminder_v2', 'erp_cp7_get_reminder_workspace_v2', 'erp_cp7_save_reminder_policy_v2',
             'erp_cp7_save_reminder_binding_v2', 'erp_cp7_claim_reminder_v2', 'erp_cp7_finish_reminder_v2',
             'erp_cp7_resolve_reminder_claim_v2', 'erp_cp7_get_reminder_request_v2')
SIGNATURES = ('public.erp_cp7_step_reminder_conditions_v2(uuid)', 'public.erp_cp7_read_reminder_conditions_v2(jsonb)',
              'public.erp_cp7_get_reminder_obligations_v2(uuid)', 'public.erp_cp7_recheck_reminder_v2(uuid,text)',
              'public.erp_cp7_get_reminder_workspace_v2(uuid)', 'public.erp_cp7_save_reminder_policy_v2(jsonb,uuid)',
              'public.erp_cp7_save_reminder_binding_v2(jsonb,uuid)', 'public.erp_cp7_claim_reminder_v2(jsonb,uuid)',
              'public.erp_cp7_finish_reminder_v2(jsonb,uuid)', 'public.erp_cp7_resolve_reminder_claim_v2(jsonb,uuid)',
              'public.erp_cp7_get_reminder_request_v2(jsonb,uuid,text)')
CAPABILITIES = ('cp7_reminder_native.staged_authority(uuid,text[])', 'cp7_reminder_native.staged_page_inputs(uuid,integer)',
                'cp7_reminder_native.staged_target_now(uuid,text,text)')
auth, b = staged.auth, staged.b
QUIET = dict(enabled=False, starts_at=None, ends_at=None, timezone='Asia/Jakarta')


def rpc(cur, name, args, subject=None):
    return staged.limited(cur, name, args, subject)


def refusal(cur, op):
    return planv2.refusal(cur, op)


def refused(cur, op, code, sqlstate=None):
    return planv2.refused(cur, op, code, sqlstate)


def wib(t):
    if isinstance(t, str):
        t = datetime.fromisoformat(t)
    return t.astimezone(timezone(timedelta(hours=7))).strftime('%Y-%m-%d %H:%M:%S') + ' WIB'


def num(d):
    return format(D(d).normalize(), 'f')


def status_checked(s, run):
    assert s['contract_version'] == 'cp7.reminder-condition-set.v2' and s['run_id'] == str(run) and s['sent'] is False, s
    assert s['state'] in ('RUNNING', 'DONE', 'FAILED') and s['unit_count'] == s['page_count'] + 1, s
    assert (s['stage'] is None) == (s['state'] != 'RUNNING') and (s['failure'] is not None) == (s['state'] == 'FAILED'), s
    assert (s['set_hash'] is not None) == (s['state'] == 'DONE'), s
    return s


def step_all(cur, run, subject=None):
    """Step the condition set until it is final: one unit per call, each call under 8 s."""
    calls, prev = [], None
    for _ in range(10000):
        t0 = time.monotonic()
        s = status_checked(rpc(cur, 'erp_cp7_step_reminder_conditions_v2', (run,), subject), run)
        calls.append(round((time.monotonic() - t0) * 1000, 1))
        if s['state'] == 'FAILED':
            return s, calls
        assert s['worker_active'] is False and (prev is None or s['units_done'] == prev + 1), (s, prev)
        prev = s['units_done']
        if s['state'] == 'DONE':
            return s, calls
    raise AssertionError('P19M_SET_DID_NOT_FINISH')


def ready_set(cur, run, subject=None):
    s, calls = step_all(cur, run, subject)
    assert s['state'] == 'DONE', s
    return s, calls


def conditions(cur, run, rule=None, state=None, subject=None):
    out, offset = [], 0
    while True:
        x = rpc(cur, 'erp_cp7_read_reminder_conditions_v2', (json.dumps(dict(run_id=str(run), rule_id=rule, state=state, offset=offset, limit=50)),), subject)
        assert x['contract_version'] == 'cp7.reminder-conditions.v2' and x['eligibility_basis'] == 'SNAPSHOT_VALUE_POLICY_AT_READ', x.get('contract_version')
        assert x['recheck_required_before_preview'] is True and x['sent'] is False and x['run_id'] == str(run)
        out += x['rows']
        offset += len(x['rows'])
        if offset >= x['total'] or not x['rows']:
            assert offset == x['total'], (offset, x['total'])
            return out


def row(rows, key):
    found = [r for r in rows if r['key'] == key]
    assert len(found) == 1, (key, len(found))
    return found[0]


def workspace(cur, run, subject=None):
    w = rpc(cur, 'erp_cp7_get_reminder_workspace_v2', (run,), subject)
    assert w['contract_version'] == 'cp7.reminder-workspace.v2' and w['sent'] is False and w['external_delivery_enabled'] is False
    assert w['scheduler_enabled'] is False and w['run_id'] == str(run)
    return w


def command(cur, name, p, key=None, subject=None):
    out = rpc(cur, name, (json.dumps(p), str(key or uuid.uuid4())), subject)
    assert out['contract_version'] == 'cp7.reminder-command.v2' and out['sent'] is False and out['external_delivery_enabled'] is False, out
    return out


def lookup(cur, p, key, operation, subject=None):
    return rpc(cur, 'erp_cp7_get_reminder_request_v2', (json.dumps(p), str(key), operation), subject)


def bind(cur, r, rules_=('PRODUCTION_GAP',), revision='0', subject=None, enabled=True, key=None):
    p = dict(run_id=r['run'], identity_hash=r['identity'], expected_revision=revision, enabled=enabled,
             label='Tujuan pemeriksaan lokal · bukan penerima WhatsApp', environment='LOCAL_TEST_SINK', rules=list(rules_),
             reason='Explicit disposable reminders v2 local rehearsal; not an operating setting')
    out = command(cur, 'erp_cp7_save_reminder_binding_v2', p, key, subject)
    return out['result']['binding_id'], out


def policy(cur, r, rule, unit, value='1', revision='0', target=None, subject=None, key=None):
    p = dict(run_id=r['run'], identity_hash=r['identity'], rule_id=rule, scope_kind='TARGET' if target else 'GLOBAL', scope_key=target or '*',
             expected_revision=revision, config=dict(enabled=True, threshold_value=value, threshold_unit=unit, cooldown_minutes='0', quiet=QUIET),
             reason='Explicit reminders v2 fixture choice, not an operating default')
    return command(cur, 'erp_cp7_save_reminder_policy_v2', p, key, subject)


def claim_payload(r, c, binding):
    return dict(run_id=r['run'], identity_hash=r['identity'], condition_key=c['key'], condition_hash=c['condition_hash'], binding_id=binding)


def claim(cur, r, c, binding, key=None, subject=None):
    return command(cur, 'erp_cp7_claim_reminder_v2', claim_payload(r, c, binding), key, subject)


def finish(cur, r, cl, outcome='LOCAL_CAPTURE', key=None, subject=None):
    p = dict(run_id=cl['run_id'], identity_hash=cl['identity_hash'], claim_id=cl['id'], fence=cl['fence'], outcome=outcome)
    return command(cur, 'erp_cp7_finish_reminder_v2', p, key, subject)


def recheck(cur, run, key, subject=None):
    x = rpc(cur, 'erp_cp7_recheck_reminder_v2', (run, key), subject)
    assert x['contract_version'] == 'cp7.reminder-recheck.v2' and x['recorded'] is False and x['sent'] is False, x
    return x


def admin_count(cur, sql, args=()):
    b.api.admin(cur)
    return cur.execute(sql, args).fetchone()[0]


def claims_of(cur, key):
    return admin_count(cur, 'select count(*)from cp7_reminder_native.staged_claims where condition_key=%s', (key,))


def rechecks_of(cur, key):
    return admin_count(cur, 'select count(*)from cp7_reminder_native.staged_rechecks where condition_key=%s', (key,))


def episodes_of(cur, key):
    b.api.admin(cur)
    return cur.execute('select state from cp7_reminder_native.staged_episodes where condition_key=%s order by episode_number', (key,)).fetchall()


def identity(cur, run):
    b.api.admin(cur)
    return cur.execute('select identity_hash from cp7_analysis_stage.page_sets where run_id=%s', (run,)).fetchone()[0]


def plan_target(cur, today, subject=None):
    """The plan v2 fixture (a real production target with an open exact-size gap, ACTIVE policy, complete WIP) and its staged run."""
    x = planv2.single(cur, today, subject)
    r = dict(run=x['run'], identity=identity(cur, x['run']), target=x['target'], root=x['root'], x=x)
    ready_set(cur, r['run'], subject)
    c = row(conditions(cur, r['run'], 'PRODUCTION_GAP', subject=subject), 'PRODUCTION_GAP:' + r['target'])
    assert c['state'] == 'ACTIVE' and c['kind'] == 'SNAPSHOT' and D(c['value']['value']) >= 2, c
    r['gap'] = D(c['value']['value'])
    return r, c


def text_checked(body, data_as_of):
    assert body.startswith('PRATINJAU LOKAL — BELUM DIKIRIM\n') and 'Data analisis per ' + wib(data_as_of) in body, body
    assert 'Diperiksa ulang ' in body and 'terkini' not in body.lower() and body.endswith('Ini pratinjau lokal. Masalah tetap diperiksa dari transaksi ERP.'), body
    return body


def expected_rows(original):
    """Snapshot conditions written independently from the reassembled run (v1's rules, without its SOURCE_CHANGED state)."""
    labels = {}
    for l in original['product_labels']:
        labels.setdefault(l['target_key'], (l['sku'] or '') + ' · ' + (l['product_name'] or '') if l['sku'] is not None and l['product_name'] is not None else None)
    out = {}
    for rec in original['analysis'].get('recommendations') or []:
        v, t = rec['q_conditional'], rec['target']['key']
        known = v['state'] in ('KNOWN', 'ASSUMED')
        state = 'DATA_REVIEW' if not known else 'ACTIVE' if D(v['value']) > 0 else 'NO_CURRENT_GAP' if v['state'] == 'ASSUMED' else 'RESOLVED'
        out['PRODUCTION_GAP:' + t] = dict(state=state, value=v, rule_id='PRODUCTION_GAP', target_key=t, material_key=None, label=labels.get(t))
    for m in original['analysis'].get('material_needs') or []:
        v, t, mk = m['additional_external'], m['target_key'], m['material_key']
        known = v['state'] in ('KNOWN', 'ASSUMED')
        state = 'DATA_REVIEW' if not known else 'ACTIVE' if D(v['value']) > 0 else 'NO_CURRENT_GAP' if v['state'] == 'ASSUMED' else 'RESOLVED'
        fabric = (mk or '').startswith('FABRIC_')
        key = ('FABRIC_NEED:' + t + ':' + mk) if fabric else ('ACCESSORY_NEED:' + t + ':' + (mk or 'UNKNOWN_BOM'))
        out[key] = dict(state=state, value=v, rule_id='FABRIC_NEED' if fabric else 'ACCESSORY_NEED', target_key=t, material_key=mk, label=labels.get(t))
    return out


def receipt_of(cur, today, material):
    """A posted receipt of an existing material through the ordinary receipt writer (a stock movement after the snapshot)."""
    other = planv2.plan.receipt.fixture(cur, today, qty='5', price='10')
    payload = dict(other['payload'])
    payload['lines'] = [dict(payload['lines'][0], material_id=str(material))]
    planv2.plan.receipt.post(cur, planv2.plan.receipt.command(cur, 'SAVE_DRAFT', payload))
    b.api.admin(cur)


def cases(cur, today):
    def set_steps_seal():
        x = planv2.single(cur, today)
        run = x['run']
        b.api.admin(cur)
        before = b.boundary.snapshot(cur)
        refused(cur, lambda: rpc(cur, 'erp_cp7_read_reminder_conditions_v2', (json.dumps(dict(run_id=run, rule_id=None, state=None, offset=0, limit=50)),)),
                'CP7_REMINDER_V2_CONDITIONS_NOT_READY', '40001')
        s, calls = ready_set(cur, run)
        original, ps, shape = staged.fetch(cur, run)
        assert len(calls) == shape['page_count'] + 1 and s['units_done'] == s['unit_count'] == shape['page_count'] + 1, (len(calls), s)
        assert s['identity_hash'] == ps['identity_hash'] and s['targets_total'] == ps['targets_total'], s
        again = status_checked(rpc(cur, 'erp_cp7_step_reminder_conditions_v2', (run,)), run)
        assert again['state'] == 'DONE' and again['set_hash'] == s['set_hash'] and again['units_done'] == s['units_done'], again
        rows = conditions(cur, run)
        exp = expected_rows(original)
        assert {r['key'] for r in rows} == set(exp), ('P19M_CONDITION_KEYS', len(rows), len(exp))
        for r in rows:
            e = exp[r['key']]
            assert (r['state'], r['value'], r['rule_id'], r['target_key'], r['material_key'], r['label']) == (
                e['state'], e['value'], e['rule_id'], e['target_key'], e['material_key'], e['label']), (r['key'], r, e)
            assert r['kind'] == 'SNAPSHOT' and r['data_as_of'] == s['data_as_of'] and len(r['condition_hash']) == 64 and r['delivery_sent'] is False
        by_rule = {}
        for e in exp.values():
            by_rule.setdefault(e['rule_id'], {}).setdefault(e['state'], 0)
            by_rule[e['rule_id']][e['state']] += 1
        assert s['totals'] == dict(conditions=len(exp), by_rule=by_rule), (s['totals'], by_rule)
        assert len(exp) == ps['totals']['items'].get('recommendations', 0) + ps['totals']['items'].get('material_needs', 0)
        b.api.admin(cur)
        hashes = [h for (h,) in cur.execute('select condition_hash from cp7_reminder_native.staged_conditions where run_id=%s order by page_index,seq', (run,)).fetchall()]
        assert s['set_hash'] == hashlib.sha256((s['identity_hash'] + '\n' + '\n'.join(hashes)).encode()).hexdigest(), 'P19M_SET_HASH'
        assert len(set(hashes)) == len(hashes)
        refused(cur, lambda: cur.execute("update cp7_reminder_native.staged_conditions set label='x' where run_id=%s", (run,)), 'CP7_REMINDER_REQUEST_IMMUTABLE')
        refused(cur, lambda: cur.execute("update cp7_reminder_native.staged_condition_sets set units_done=0 where run_id=%s", (run,)), 'CP7_REMINDER_V2_SET_IMMUTABLE')
        refused(cur, lambda: cur.execute("delete from cp7_reminder_native.staged_condition_sets where run_id=%s", (run,)), 'CP7_REMINDER_V2_SET_IMMUTABLE')
        assert b.boundary.snapshot(cur) == before, 'P19M_SET_WROTE_NATIVE'
        return dict(status='PASS', one_unit_per_call=len(calls), pages=shape['page_count'], rows_equal_independent_snapshot_rules=len(exp),
                    totals=s['totals'], set_hash_over_identity_and_conditions=True, immutable=True, native_boundary_unchanged=True, step_ms=calls)

    def resolved_not_sent():
        r, c = plan_target(cur, today)
        binding, _ = bind(cur, r)
        policy(cur, r, 'PRODUCTION_GAP', 'PCS')
        planv2.found_fg(cur, r['x'], int(math.ceil(r['gap'])))
        v = recheck(cur, r['run'], c['key'])
        assert v['verdict'] == 'RESOLVED_NOW' and D(v['numbers']['need_now_pcs']) == 0 and D(v['numbers']['increase_pcs']) >= r['gap'], v
        assert rechecks_of(cur, c['key']) == 0, 'P19M_READ_ONLY_RECHECK_RECORDED'
        out = claim(cur, r, c, binding)
        res = out['result']
        assert res['status'] == 'COMMITTED' and res['outcome'] == 'NOT_SENT' and res['verdict'] == 'RESOLVED_NOW' and res['claim_id'] is None, res
        rec = out['recheck']
        assert rec['verdict'] == 'RESOLVED_NOW' and rec['phase'] == 'CLAIM' and rec['kind'] == 'SNAPSHOT' and rec['data_as_of'] == c['data_as_of'], rec
        assert D(rec['numbers']['need_snapshot_pcs']) == r['gap'] and D(rec['numbers']['need_now_pcs']) == 0, rec['numbers']
        again = claim(cur, r, c, binding)['result']
        assert again['outcome'] == 'NOT_SENT' and again['verdict'] == 'RESOLVED_NOW' and again['recheck_id'] != res['recheck_id'], again
        assert claims_of(cur, c['key']) == 0 and rechecks_of(cur, c['key']) == 2 and episodes_of(cur, c['key']) == [], 'P19M_RESOLVED_WAS_CLAIMED'
        return dict(status='PASS', resolved_after_snapshot_not_sent=True, recorded_with_numbers=rec['numbers'], no_claim_no_episode=True,
                    new_request_same_answer=True)

    def sent_once():
        r, c = plan_target(cur, today)
        binding, _ = bind(cur, r)
        policy(cur, r, 'PRODUCTION_GAP', 'PCS')
        v = recheck(cur, r['run'], c['key'])
        assert v['verdict'] == 'STILL_OPEN' and D(v['numbers']['need_now_pcs']) == r['gap'] and D(v['numbers']['increase_pcs']) == 0, v
        k1 = uuid.uuid4()
        out = claim(cur, r, c, binding, k1)
        res, cl = out['result'], out['claim']
        assert res['outcome'] == 'CLAIMED' and res['verdict'] == 'STILL_OPEN' and cl['status'] == 'CLAIMED' and cl['id'] == res['claim_id'], out
        text_checked(cl['body'], c['data_as_of'])
        assert 'masih kurang sedikitnya ' + num(r['gap']) + ' PCS' in cl['body'] and 'kurang ' + c['value']['value'] + ' PCS.' in cl['body'], cl['body']
        assert cl['body_sha256'] == hashlib.sha256(cl['body'].encode()).hexdigest()
        assert claim(cur, r, c, binding, k1)['result'] == res, 'P19M_REPLAY'
        other = claim(cur, r, c, binding)['result']
        assert other['claim_id'] == cl['id'] and other['outcome'] == 'CLAIMED', other
        done = finish(cur, r, cl)
        assert done['result']['local_status'] == 'LOCAL_SINK_CAPTURED' and done['claim']['status'] == 'LOCAL_SINK_CAPTURED', done
        assert done['recheck']['phase'] == 'FINISH' and done['recheck']['verdict'] == 'STILL_OPEN', done['recheck']
        later = claim(cur, r, c, binding)['result']
        assert later['claim_id'] == cl['id'], 'P19M_SECOND_PREVIEW_SAME_EPISODE'
        assert claims_of(cur, c['key']) == 1 and episodes_of(cur, c['key']) == [('ACTIVE',)]
        b.api.admin(cur)
        refused(cur, lambda: cur.execute("update cp7_reminder_native.staged_claims set status='CLAIMED' where id=%s", (cl['id'],)), 'CP7_LOCAL_CLAIM_IMMUTABLE')
        return dict(status='PASS', still_open_claimed_once=True, body_states_snapshot_time_and_recheck=True, same_episode_never_twice=True,
                    finish_rechecked=True, body=cl['body'])

    def partial_threshold():
        r, c = plan_target(cur, today)
        binding, _ = bind(cur, r)
        planv2.found_fg(cur, r['x'], 1)
        v = recheck(cur, r['run'], c['key'])
        assert v['verdict'] == 'STILL_OPEN' and D(v['numbers']['need_now_pcs']) == r['gap'] - 1 and D(v['numbers']['increase_pcs']) == 1, v
        policy(cur, r, 'PRODUCTION_GAP', 'PCS', value=str(r['gap']))
        res = claim(cur, r, c, binding)['result']
        assert res['outcome'] == 'NOT_SENT' and res['verdict'] == 'BELOW_THRESHOLD_NOW', res
        policy(cur, r, 'PRODUCTION_GAP', 'PCS', value='1', revision='1')
        out = claim(cur, r, c, binding)
        assert out['result']['outcome'] == 'CLAIMED' and 'masih kurang sedikitnya ' + num(r['gap'] - 1) + ' PCS' in out['claim']['body'], out
        assert D(out['recheck']['numbers']['need_now_pcs']) == r['gap'] - 1 and out['recheck']['numbers']['threshold'] == '1', out['recheck']
        return dict(status='PASS', reduced_need_stated=str(r['gap'] - 1), below_threshold_not_sent=True, lower_threshold_claims_reduced_need=True)

    def fabric_held():
        f = physical.bound(cur, today)
        key, _, done, _ = staged.staged_done(cur, today)
        r = dict(run=done['run_id'], identity=identity(cur, done['run_id']))
        ready_set(cur, r['run'])
        fabrics = [x for x in conditions(cur, r['run'], 'FABRIC_NEED') if x['target_key'] == f['target']]
        assert len(fabrics) == 1 and fabrics[0]['state'] == 'ACTIVE' and D(fabrics[0]['value']['value']) == 176, fabrics
        c = fabrics[0]
        binding, _ = bind(cur, r, ('FABRIC_NEED',))
        policy(cur, r, 'FABRIC_NEED', c['value']['unit'])
        out = claim(cur, r, c, binding)
        assert out['result']['outcome'] == 'CLAIMED' and out['recheck']['reason'] == 'FABRIC_NEED_UNCHANGED_SINCE_SNAPSHOT', out
        text_checked(out['claim']['body'], c['data_as_of'])
        receipt_of(cur, today, f['payload']['config']['material_id'])
        done_ = finish(cur, r, out['claim'])
        assert done_['claim']['status'] == 'SUPPRESSED' and done_['claim']['reason'] == 'RECHECK_CHANGED_REVIEW_REQUIRED', done_['claim']
        assert done_['recheck']['reason'] == 'FABRIC_MATERIAL_CHANGED_AFTER_SNAPSHOT' and done_['recheck']['numbers']['material']['movements_after'] >= 1, done_['recheck']
        res = claim(cur, r, c, binding)['result']
        assert res['outcome'] == 'NOT_SENT' and res['verdict'] == 'CHANGED_REVIEW_REQUIRED', res
        return dict(status='PASS', unchanged_fabric_claimed=True, material_received_after_snapshot_held_back=True,
                    finish_suppressed=done_['claim']['reason'], new_claim_not_sent=True)

    def ar_paid():
        fx, e, key = rules.due_fixture(cur, today)
        _, _, done, _ = staged.staged_done(cur, today)
        r = dict(run=done['run_id'], identity=identity(cur, done['run_id']))
        o = rpc(cur, 'erp_cp7_get_reminder_obligations_v2', (r['run'],))
        assert o['contract_version'] == 'cp7.reminder-obligations.v2' and o['basis'] == 'READ_NOW_NOT_FROM_SNAPSHOT' and o['sent'] is False, o.get('contract_version')
        live = row(o['rows'], key)
        v1 = rules.row(rules.source(cur, e), key)
        strip = lambda x: {k: v for k, v in x.items() if k not in ('policy_timing', 'eligibility', 'condition_hash', 'kind', 'policy_binding')}
        assert strip(live) == strip(v1) and live['state'] == 'ACTIVE' and live['kind'] == 'LIVE', (strip(live), strip(v1))
        binding, _ = bind(cur, r, ('AR_DUE',))
        policy(cur, r, 'AR_DUE', 'DAY', value='0')
        out = claim(cur, r, live, binding)
        assert out['result']['outcome'] == 'CLAIMED' and 'Sisa tagihan: ' + live['financial_source']['remaining']['value'] + ' IDR' in out['claim']['body'], out
        assert 'Dibaca ' in out['claim']['body'] and 'Data analisis per' not in out['claim']['body'] and 'terkini' not in out['claim']['body'].lower()
        rules.ar.sales.payment(cur, dict(fx, tag=fx['tag'] + '-part'), today, '100')
        done_ = finish(cur, r, out['claim'])
        assert done_['claim']['status'] == 'SUPPRESSED' and done_['claim']['reason'] == 'RECHECK_CONDITION_CHANGED', done_['claim']
        state, message, detail = refusal(cur, lambda: claim(cur, r, live, binding))
        assert (state, message) == ('40001', 'CP7_REMINDER_V2_CONDITION_CHANGED') and detail['presented_hash'] == live['condition_hash'], (state, message, detail)
        assert detail['current_hash'] != live['condition_hash'] and D(detail['remaining_idr']) == 200, detail
        now = row(rpc(cur, 'erp_cp7_get_reminder_obligations_v2', (r['run'],))['rows'], key)
        rules.ar.sales.payment(cur, dict(fx, tag=fx['tag'] + '-final'), today, '200')
        res = claim(cur, r, now, binding)
        assert res['result']['outcome'] == 'NOT_SENT' and res['result']['verdict'] == 'RESOLVED_NOW', res['result']
        assert res['recheck']['kind'] == 'LIVE' and res['recheck']['data_as_of'] is None, res['recheck']
        assert episodes_of(cur, key) == [('RESOLVED',)] and claims_of(cur, key) == 1
        return dict(status='PASS', live_row_equals_v1_reader=True, open_claimed=True, partial_payment_suppressed_and_refused_40001=detail,
                    paid_in_full_not_sent=True, episode_resolved=True)

    def policy_destination():
        r, c = plan_target(cur, today)
        binding, first = bind(cur, r)
        assert first['result']['revision'] == '1'
        refused(cur, lambda: bind(cur, r), 'CP7_LOCAL_BINDING_STALE', '40001')
        b.api.admin(cur)
        assert cur.execute('select environment,revision from cp7_reminder_native.local_bindings where id=%s', (binding,)).fetchone() == ('LOCAL_TEST_SINK', 1)
        out = policy(cur, r, 'PRODUCTION_GAP', 'PCS', value='3', target=r['target'])
        assert out['result']['status'] == 'COMMITTED' and out['result']['revision'] == '1', out
        unknown = str(uuid.uuid4()) + ':' + str(uuid.uuid4())
        refused(cur, lambda: policy(cur, r, 'PRODUCTION_GAP', 'PCS', target=unknown), 'CP7_RULE_POLICY_TARGET_UNAVAILABLE', '42501')
        refused(cur, lambda: policy(cur, r, 'PRODUCTION_GAP', 'KG'), 'CP7_RULE_POLICY_CONFIG')
        refused(cur, lambda: policy(cur, r, 'PRODUCTION_GAP', 'PCS', target=r['target']), 'CP7_RULE_POLICY_STALE_REVISION', '40001')
        now = row(conditions(cur, r['run'], 'PRODUCTION_GAP'), c['key'])
        assert now['policy_binding']['basis'] == 'EXACT_TARGET' and now['policy_binding']['policy']['config']['threshold_value'] == '3', now['policy_binding']
        b.api.admin(cur)
        stored = cur.execute("select scope_kind,scope_key,revision from cp7_reminder_native.rule_policies where id=%s", (out['result']['policy_id'],)).fetchone()
        assert stored == ('TARGET', r['target'], 1), stored
        w = workspace(cur, r['run'])
        assert w['manage_allowed'] is True and w['binding']['id'] == binding and any(p['policy_id'] == out['result']['policy_id'] for p in w['policies'])
        return dict(status='PASS', destination_versioned_in_v1_table=True, target_policy_for_a_target_of_the_run=True, unknown_target_refused=True,
                    stale_revision_40001=True, exact_target_binding_on_read=True)

    def one_uuid():
        r, c = plan_target(cur, today)
        binding, _ = bind(cur, r)
        policy(cur, r, 'PRODUCTION_GAP', 'PCS')
        k = uuid.uuid4()
        first = claim(cur, r, c, binding, k)['result']
        refused(cur, lambda: command(cur, 'erp_cp7_claim_reminder_v2', dict(claim_payload(r, c, binding), condition_hash='0' * 64), k), 'CP7_REMINDER_REQUEST_CHANGED')
        assert lookup(cur, claim_payload(r, c, binding), k, 'CLAIM')['result'] == first
        closed = uuid.uuid4()
        sealed = lookup(cur, claim_payload(r, c, binding), closed, 'CLAIM')['result']
        assert sealed['status'] == 'NOT_COMMITTED' and sealed['claim_id'] is None, sealed
        assert claim(cur, r, c, binding, closed)['result'] == sealed, 'P19M_SEALED_UUID_COMMITTED_LATER'
        # One UUID is one request across operations (and across v1 and v2, which share the request table).
        refused(cur, lambda: bind(cur, r, revision='1', key=k), 'CP7_REMINDER_REQUEST_CHANGED')
        assert claims_of(cur, c['key']) == 1
        return dict(status='PASS', same_uuid_same_payload_replays=True, changed_payload_refused=True, lookup_seals_unknown_uuid=True,
                    one_uuid_one_request_across_operations=True)

    def authority():
        r, c = plan_target(cur, today)
        other, role = auth.custom_actor(cur)
        b.api.admin(cur)
        staff = cur.execute("select id from erp.app_roles where role_code='STAFF'").fetchone()[0]
        cur.execute('update erp.app_roles set is_active=true where id=%s', (staff,))
        cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s', (staff, other))
        for permission in auth.PERMS:
            cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing', (staff, permission))
        for name, args in (('erp_cp7_step_reminder_conditions_v2', (r['run'],)), ('erp_cp7_get_reminder_workspace_v2', (r['run'],)),
                           ('erp_cp7_recheck_reminder_v2', (r['run'], c['key']))):
            refused(cur, lambda: rpc(cur, name, args, other), 'CP7_REMINDER_V2_SNAPSHOT_UNAVAILABLE', '42501')
        running = uuid.uuid4()
        staged.checked(staged.request(cur, today, running), running, 'RUNNING')
        refused(cur, lambda: rpc(cur, 'erp_cp7_step_reminder_conditions_v2', (staged.job_row(cur, running)['run_id'],)), 'CP7_REMINDER_V2_SNAPSHOT_UNAVAILABLE', '42501')
        _, _, done, _ = staged.staged_done(cur, today, subject=other)
        mine = dict(run=done['run_id'], identity=identity(cur, done['run_id']))
        ready_set(cur, mine['run'], other)
        assert conditions(cur, mine['run'], subject=other), 'P19M_STAFF_READS_CONDITIONS'
        w = workspace(cur, mine['run'], other)
        assert w['manage_allowed'] is False and w['claims'] == [] and w['binding'] is None, w
        refused(cur, lambda: bind(cur, mine, subject=other), 'CP7_RULE_POLICY_MANAGE_DENIED', '42501')
        for v1 in ('erp_cp7_get_rule_conditions_v1', 'erp_cp7_get_local_reminders_v1', 'erp_cp7_get_reminder_policy_v1'):
            refused(cur, lambda: rpc(cur, v1, (r['run'],)), 'CP7_ANALYSIS_RUN_UNAVAILABLE', '42501')
        b.api.admin(cur)
        for sig in SIGNATURES:
            for who in ('anon', 'authenticated', 'service_role'):
                assert cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0] == (who == 'authenticated'), (who, sig)
        for sig in CAPABILITIES:
            for who in ('anon', 'authenticated', 'service_role'):
                assert not cur.execute("select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)).fetchone()[0], (who, sig)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'", (staff,))
        refused(cur, lambda: workspace(cur, mine['run'], other), 'CP7_REMINDER_ACCESS_DENIED', '42501')
        return dict(status='PASS', foreign_run_42501=True, unfinished_run_42501=True, staff_reads_without_claims_or_settings=True,
                    v1_refuses_staged_run=True, only_public_wrappers_executable=True, permission_loss_refused=True)

    return list(zip(IDS['native'], (set_steps_seal, resolved_not_sent, sent_once, partial_threshold, fabric_held, ar_paid,
                                    policy_destination, one_uuid, authority)))


def races(tools, today):
    def prepared():
        with tools.connect() as conn, conn.cursor() as cur:
            r, c = plan_target(cur, today)
            binding, _ = bind(cur, r)
            policy(cur, r, 'PRODUCTION_GAP', 'PCS')
            conn.commit()
        return r, c, binding

    def two_claims():
        r, c, binding = prepared()
        gate = threading.Barrier(2)

        def one():
            with tools.connect() as conn, conn.cursor() as cur:
                gate.wait(timeout=8)
                out = claim(cur, r, c, binding)['result']
                conn.commit()
                return out
        with ThreadPoolExecutor(max_workers=2) as pool:
            a, z = pool.submit(one), pool.submit(one)
            ra, rz = a.result(60), z.result(60)
        assert ra['outcome'] == rz['outcome'] == 'CLAIMED' and ra['claim_id'] == rz['claim_id'] and ra['request_id'] != rz['request_id'], (ra, rz)
        with tools.connect() as conn, conn.cursor() as cur:
            assert claims_of(cur, c['key']) == 1 and episodes_of(cur, c['key']) == [('ACTIVE',)]
        return dict(status='PASS', two_requests_one_claim=True, one_episode=True)

    def fg_while_waiting():
        r, c, binding = prepared()
        holder = tools.connect()
        hc = holder.cursor()
        # Test-controlled holder of the shared episode lock (labelled): the claim must wait on it.
        hc.execute("select pg_advisory_xact_lock(hashtextextended('CP7:RULE_EPISODES:CURRENT_SOURCE',0))")
        result = {}

        def claimer():
            with tools.connect() as conn, conn.cursor() as cur:
                result['pid'] = cur.execute('select pg_backend_pid()').fetchone()[0]
                result['out'] = claim(cur, r, c, binding)['result']
                conn.commit()
        t = threading.Thread(target=claimer)
        t.start()
        waited = False
        for _ in range(200):
            time.sleep(0.05)
            if 'pid' in result:
                with tools.connect() as conn, conn.cursor() as cur:
                    waited = cur.execute("select exists(select 1 from pg_locks where pid=%s and not granted and locktype='advisory')", (result['pid'],)).fetchone()[0]
                if waited:
                    break
        assert waited, 'P19M_CLAIM_DID_NOT_WAIT'
        with tools.connect() as conn, conn.cursor() as cur:
            planv2.found_fg(cur, r['x'], int(math.ceil(r['gap'])))
            conn.commit()
        holder.commit()
        holder.close()
        t.join(60)
        out = result['out']
        assert out['outcome'] == 'NOT_SENT' and out['verdict'] == 'RESOLVED_NOW' and out['claim_id'] is None, out
        with tools.connect() as conn, conn.cursor() as cur:
            assert claims_of(cur, c['key']) == 0
        return dict(status='PASS', claim_waited_on_lock=True, stock_committed_meanwhile_seen_after_lock=True, not_sent=True)

    def two_steps():
        with tools.connect() as conn, conn.cursor() as cur:
            x = planv2.single(cur, today)
            run = x['run']
            first = status_checked(rpc(cur, 'erp_cp7_step_reminder_conditions_v2', (run,)), run)
            conn.commit()
        assert first['units_done'] == 1 and first['state'] == 'RUNNING' or first['state'] == 'DONE', first
        if first['state'] == 'DONE':
            return dict(status='PASS', single_unit_run=True)
        holder = tools.connect()
        hc = holder.cursor()
        held = status_checked(rpc(hc, 'erp_cp7_step_reminder_conditions_v2', (run,)), run)
        with tools.connect() as conn, conn.cursor() as cur:
            other = status_checked(rpc(cur, 'erp_cp7_step_reminder_conditions_v2', (run,)), run)
            conn.commit()
        holder.commit()
        holder.close()
        assert other['worker_active'] is True and other['units_done'] == 1 and held['units_done'] == 2, (other, held)
        with tools.connect() as conn, conn.cursor() as cur:
            s, _ = ready_set(cur, run)
            conn.commit()
        return dict(status='PASS', concurrent_step_skips_locked_set=True, one_unit_per_call=True, finished=s['state'])

    return list(zip(IDS['races'], (two_claims, fg_while_waiting, two_steps)))


def http_cases(http, today):
    state = {}

    def flow():
        owner = http.login('OWNER', 'p19m-owner')
        other = http.login('OWNER', 'p19m-other')
        with http.connect() as conn, conn.cursor() as cur:
            x = planv2.single(cur, today, owner.auth_user_id)
            r = dict(run=x['run'], identity=identity(cur, x['run']), target=x['target'])
            conn.commit()
        s = None
        for _ in range(1000):
            s = owner.rpc('erp_cp7_step_reminder_conditions_v2', dict(p_run=r['run']))
            assert s['status'] == 200, s
            if s['body']['state'] != 'RUNNING':
                break
        assert s['body']['state'] == 'DONE', s
        q = dict(run_id=r['run'], rule_id='PRODUCTION_GAP', state='ACTIVE', offset=0, limit=50)
        rows = owner.rpc('erp_cp7_read_reminder_conditions_v2', dict(p_query=q))
        assert rows['status'] == 200, rows
        c = row(rows['body']['rows'], 'PRODUCTION_GAP:' + r['target'])
        bp = dict(run_id=r['run'], identity_hash=r['identity'], expected_revision='0', enabled=True, label='Tujuan lokal HTTP', environment='LOCAL_TEST_SINK',
                  rules=['PRODUCTION_GAP'], reason='Explicit HTTP rehearsal')
        bo = owner.rpc('erp_cp7_save_reminder_binding_v2', dict(p_payload=bp, p_request=str(uuid.uuid4())))
        assert bo['status'] == 200, bo
        pp = dict(run_id=r['run'], identity_hash=r['identity'], rule_id='PRODUCTION_GAP', scope_kind='GLOBAL', scope_key='*', expected_revision='0',
                  config=dict(enabled=True, threshold_value='1', threshold_unit='PCS', cooldown_minutes='0', quiet=QUIET), reason='Explicit HTTP rehearsal')
        po = owner.rpc('erp_cp7_save_reminder_policy_v2', dict(p_payload=pp, p_request=str(uuid.uuid4())))
        assert po['status'] == 200, po
        v = owner.rpc('erp_cp7_recheck_reminder_v2', dict(p_run=r['run'], p_condition=c['key']))
        assert v['status'] == 200 and v['body']['verdict'] == 'STILL_OPEN', v
        cp = dict(run_id=r['run'], identity_hash=r['identity'], condition_key=c['key'], condition_hash=c['condition_hash'], binding_id=bo['body']['result']['binding_id'])
        cl = owner.rpc('erp_cp7_claim_reminder_v2', dict(p_payload=cp, p_request=str(uuid.uuid4())))
        assert cl['status'] == 200 and cl['body']['result']['outcome'] == 'CLAIMED', cl
        foreign = other.rpc('erp_cp7_get_reminder_workspace_v2', dict(p_run=r['run']))
        assert foreign['status'] == 403 and 'CP7_REMINDER_V2_SNAPSHOT_UNAVAILABLE' in json.dumps(foreign['body']), foreign
        anonymous = http.anon_rpc('erp_cp7_get_reminder_workspace_v2', dict(p_run=r['run']))['status']
        assert anonymous in (401, 403), anonymous
        state.update(owner=owner, run=r['run'], claim=cp)
        return dict(status='PASS', real_Auth_steps_read_settings_recheck_claim=True, foreign_403=True, anonymous_refused=anonymous)

    def revoked():
        assert state, 'P19M_REQUIRED_PRIOR_HTTP_CASE'
        with http.connect() as conn, conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (state['owner'].auth_user_id,))
            conn.commit()
        codes = [state['owner'].rpc('erp_cp7_get_reminder_workspace_v2', dict(p_run=state['run']))['status'],
                 state['owner'].rpc('erp_cp7_claim_reminder_v2', dict(p_payload=state['claim'], p_request=str(uuid.uuid4())))['status']]
        assert codes == [403, 403], codes
        return dict(status='PASS', deactivated_user_403=codes)

    return list(zip(IDS['http'], (flow, revoked)))

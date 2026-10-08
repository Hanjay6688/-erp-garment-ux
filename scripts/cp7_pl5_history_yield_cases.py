"""PL-5 B: the good-piece yield of a new start from the factory's own finished production.

Owner decision 8 Oct 2026 (docs/cp7/PL5_YIELD_POLICY_PROPOSAL_20261007.md, approved as one package):
180 days, at least 5 finished groups and 200 cut pieces, per product+size and then the same model,
one-sided 90% Wilson lower bound floored to 0.1%; never across models and never 100%; with too little
data the plan uses the reviewed estimate A or stays UNKNOWN. The decision is stored as a versioned policy
signed by an owner or admin, and tested before it is active. Only cutting groups whose stored PL-8
exhaustion proof still matches their current facts count. Real Native writers (cut, pickup, sewing,
laundry, final SKU, BS scrap), the ordinary proof capture, real concurrent sessions and real
Auth/PostgREST calls on the closed harness. SYNTHETIC rows are labelled where they are used.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal, getcontext
from fractions import Fraction
import json
import math
import threading
import time
import uuid

import psycopg

import cp7_p19_staged_cases as staged
import cp7_p19_plan_v2_cases as planv2
import cp6_az_probe as az
import cp6_ax_probe as ax

IDS = dict(
    native=['PL5H_PENDING_WITHOUT_POLICY', 'PL5H_POLICY_SIGNED_VERSIONED', 'PL5H_POLICY_VALUES_AND_AUTHORITY',
            'PL5H_PRODUCT_SIZE_SUFFICIENT', 'PL5H_MODEL_FALLBACK_SAME_MODEL', 'PL5H_INSUFFICIENT_NO_VALUE',
            'PL5H_NEVER_CROSS_MODEL', 'PL5H_NEVER_100_PERCENT', 'PL5H_WILSON_EXACT', 'PL5H_CANCEL_CORRECT_BACKDATE',
            'PL5H_WINDOW_FINISH_DATE', 'PL5H_LIMIT_200_UNDER_8S', 'PL5H_PLAN_USES_HISTORY_LIVE', 'PL5H_CATALOG_PRIVATE'],
    races=['PL5H_RACE_SAME_REVISION', 'PL5H_RACE_SAME_REQUEST_TWO_SESSIONS'],
    http=['PL5H_HTTP_FLOW', 'PL5H_HTTP_REVOKED'],
    browser=['PL5H_BROWSER_DESKTOP_POLICY', 'PL5H_BROWSER_MOBILE_POLICY'],
)
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = sum(REQUIRED.values())
CONTRACT = 'cp7.pl5.history-yield.v1'
FUNCTIONS = ('erp_cp7_get_history_yield_policy_v1', 'erp_cp7_save_history_yield_policy_v1')
SIGNATURES = ('public.erp_cp7_get_history_yield_policy_v1()', 'public.erp_cp7_save_history_yield_policy_v1(jsonb,uuid)')
PRIVATE = ('cp7_plan_native.history_source(text,uuid)', 'cp7_plan_native.history_groups(uuid[],timestamptz,text)',
           'cp7_plan_native.wilson_permille(bigint,bigint)', 'cp7_plan_native.history_yield(text,uuid)',
           'cp7_yield_policy.apply(jsonb,uuid)', 'cp7_yield_policy.workspace()', 'cp7_yield_policy.access(boolean)')
# The package the owner approved; the server returns it for the form and the policy holds it once saved.
DECIDED = dict(decision='OWNER_DECISION_2026_10_08', window_days='180', min_groups='5', min_cut_pcs='200', confidence='0.90',
               method='WILSON_SCORE_ONE_SIDED_LOWER_BOUND', rounding='FLOOR_PERMILLE', levels=['PRODUCT_SIZE', 'MODEL'])
PENDING_KEYS = ('status', 'reason', 'window_days', 'minimum_sample', 'lower_bound', 'numerator', 'denominator', 'target_key')
Z = Fraction('1.2815515655446004')
auth, b = staged.auth, staged.b
base = b.chain.base
supply = planv2.previous.supply


def rpc(cur, name, args, subject=None):
    return staged.limited(cur, name, args, subject)


def workspace(cur, subject):
    return rpc(cur, 'erp_cp7_get_history_yield_policy_v1', (), subject)


def save(cur, p, subject, key=None):
    return rpc(cur, 'erp_cp7_save_history_yield_policy_v1', (json.dumps(p), key or uuid.uuid4()), subject)


def payload(expected='0', state='ACTIVE', reason='Keputusan owner 8 Okt 2026: paket yield histori disetujui', **values):
    v = {k: DECIDED[k] for k in ('window_days', 'min_groups', 'min_cut_pcs', 'confidence')}
    v.update(values)
    return dict(expected_revision=expected, state=state, reason=reason, **v)


refusal, refused = planv2.refusal, planv2.refused


def wilson(x, n):
    """floor(1000·L) of the one-sided Wilson lower bound, independently: an exact rational test of k against
    L=(2x+z²−z·sqrt(z²+4x(n−x)/n))/(2(n+z²)), searched from a 60-digit decimal estimate."""
    getcontext().prec = 60
    d = lambda v: Decimal(v.numerator) / Decimal(v.denominator)
    zz = Z * Z
    estimate = (d(2 * x + zz) - d(Z) * (d(zz) + Decimal(4 * x * (n - x)) / Decimal(n)).sqrt()) / d(2 * (n + zz))
    k = max(0, int((estimate * 1000).to_integral_value(rounding='ROUND_FLOOR')))

    def ok(k):  # 1000L >= k, exactly
        a = 1000 * (2 * x + zz) - 2 * k * (n + zz)
        return a >= 0 and a * a * n >= 1000000 * zz * (zz * n + 4 * x * (n - x))
    while k > 0 and not ok(k):
        k -= 1
    while ok(k + 1):
        k += 1
    return k


def actor(cur, role_code='OWNER'):
    """An active user of a seeded role (master data, as other suites); returns its Auth subject."""
    b.api.admin(cur)
    subject, user = str(uuid.uuid4()), str(uuid.uuid4())
    role = cur.execute('select id from erp.app_roles where role_code=%s', (role_code,)).fetchone()[0]
    cur.execute('insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active)values(%s,%s,%s,%s,%s,true)',
                (user, subject, 'PL5H ' + role_code, role_code, role))
    return subject


def custom(cur, manage):
    """A non-owner role with the planning view rights, with or without master.product.manage."""
    subject, role = auth.custom_actor(cur)
    if manage:
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'master.product.manage')", (role,))
    return subject


def history(cur, target, model, subject, timeout='8s'):
    """The reader the plan preflight calls, under the ordinary statement limit, as the subject."""
    b.api.admin(cur)
    prior = cur.execute('show statement_timeout').fetchone()[0]
    cur.execute("select set_config('request.jwt.claim.sub','',true),set_config('request.jwt.claims',%s,true),set_config('statement_timeout',%s,true)",
                (json.dumps(dict(sub=subject, role='authenticated')), timeout))
    started = time.monotonic()
    value = cur.execute('select cp7_plan_native.history_yield(%s,%s::uuid)', (target, model)).fetchone()[0]
    ms = round((time.monotonic() - started) * 1000, 1)
    b.api.admin(cur)
    cur.execute("select set_config('statement_timeout',%s,true)", (prior,))
    return value, ms


def product(cur, label, size=None):
    """A fresh product (new root) of the base model, base size unless given."""
    p = b.sized_product(cur, size or base.SIZE, 'PL5H-' + label + '-' + uuid.uuid4().hex[:6])
    row = cur.execute('select coalesce(identity_root_id,id)::text,size_id::text,model_id::text from erp.products where id=%s', (p,)).fetchone()
    return dict(id=p, target=row[0] + ':' + row[1], model=row[2])


class Production:
    """Ordinary finished cutting groups of the base model (the AZ recipe with the quantities and a BS split):
    one fabric unit cut into `cut` pieces, pickup, zero-rate sewing and its terminal, laundry out and back,
    final SKU with `good` good and `cut-good` BS, then the BS pieces scrapped. All on `day`."""

    def __init__(self, cur, today):
        self.cur, self.today, self.fx, self.used = cur, today, None, 10
        prod = az.chain.production
        az.api.admin(cur)
        self.po = str(uuid.uuid4())
        cur.execute("insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)"
                    "values(%s,%s,%s,100000,'CUTTING','CUTTING',%s,'PL5H history yield master fixture')",
                    (self.po, 'PL5H-PO-' + self.po, prod.MODEL, prod.at(today - timedelta(days=2), 7)))

    def group(self, item, cut, good, day=None):
        cur, prod = self.cur, az.chain.production
        pbase = prod.base
        day = day or self.today - timedelta(days=1)
        if self.used >= 10:
            self.fx, self.used = prod.estimated_receipt(cur, self.today), 0
        self.used += 1
        group, made = az.cut_only(cur, self.fx, self.po, day, 1, cut)
        y = cur.execute("""select y.id from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
          where r.cutting_group_id=%s""", (group,)).fetchall()
        assert len(y) == 1, ('PL5H_ONE_YIELD', y)
        pick = dict(action='SAVE_DRAFT', cutting_group_id=group, contractor_id=prod.CONTRACTOR, picked_up_at=prod.at(day, 9), allocation_mode='ROLL',
                    expected_group_version=int(made['row_version']), change_reason='PL5H pickup',
                    batches=[dict(batch_no=1, allocations=[dict(cutting_roll_yield_id=y[0][0], qty_pcs=cut)])])
        pickup = prod.rpc(cur, 'public.erp_save_cutting_pickup_v1', pick)
        pickup = prod.rpc(cur, 'public.erp_save_cutting_pickup_v1', dict(pick, id=pickup['pickup_id'], action='POST'), expected_version=int(pickup['row_version']))
        az.api.admin(cur)
        batches = cur.execute('select id from erp.cutting_distribution_batches where pickup_id=%s', (pickup['pickup_id'],)).fetchall()
        assert len(batches) == 1, ('PL5H_ONE_BATCH', batches)
        completion = uuid.uuid4()
        snapshot = cur.execute('select id from erp.po_work_component_snapshots where po_id=%s and work_component_id=%s', (self.po, prod.COMPONENT)).fetchone()
        if snapshot:
            snapshot = snapshot[0]
        else:
            snapshot = uuid.uuid4()
            cur.execute("""insert into erp.po_work_component_snapshots(id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at)
              values(%s,%s,%s,1,0,%s)""", (snapshot, self.po, prod.COMPONENT, prod.at(day, 9, 30)))
        ordinary = az.awp.OrdinaryDraftCursor(cur)
        ordinary.execute("""insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by)
          values(%s,%s,%s,%s,%s,%s,'DRAFT','PL5H zero-rate sewing draft',%s)""",
                         (completion, 'PL5H-WC-' + str(completion), self.po, prod.CONTRACTOR, group, prod.at(day, 10), pbase.OPERATOR_APP))
        ordinary.execute("""insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot)
          values(%s,%s,%s,%s,%s,0)""", (completion, snapshot, prod.COMPONENT, cut, cut))
        prod.owner(cur)
        cur.execute('select erp.post_work_completion(%s)', (completion,))
        cur.execute('select public.erp_record_sewing_terminal_v1(%s::jsonb,%s::uuid)',
                    (json.dumps(dict(work_completion_id=str(completion), qty_pcs=cut, reason='PL5H sewing terminal')), uuid.uuid4()))
        az.api.admin(cur)
        gv = pbase.group_version(cur, str(group))
        prod.owner(cur)
        delivery = pbase.action(cur, 'POST_DELIVERY', {'distribution_batch_id': str(batches[0][0]), 'vendor_id': pbase.VENDOR, 'wash_process_id': pbase.BASE_PROCESS,
                                'target_dyeing_color': 'CP6-E-NAVY', 'physical_at': prod.at(day, 11).isoformat(), 'reason': 'PL5H laundry delivery',
                                'lines': [dict(size_id=pbase.SIZE, qty_sent_pcs=cut)]}, gv)
        az.api.admin(cur)
        line = pbase.delivery_size_line(cur, delivery['delivery_id'])
        dv = pbase.delivery_version(cur, delivery['delivery_id'])
        prod.owner(cur)
        receipt = pbase.action(cur, 'POST_RECEIPT', {'delivery_id': delivery['delivery_id'], 'wash_process_id': pbase.BASE_PROCESS,
                               'physical_at': prod.at(day, 12).isoformat(), 'reason': 'PL5H laundry receipt',
                               'lines': [dict(delivery_batch_size_line_id=line, qty_good_received=cut, qty_bs_laundry=0, bs_product_id=None)]}, dv)
        az.api.admin(cur)
        rows = cur.execute("""select s.id,s.receipt_line_id from erp.laundry_receipt_batch_size_lines s
          join erp.laundry_receipt_lines l on l.id=s.receipt_line_id where l.receipt_id=%s""", (receipt['receipt_id'],)).fetchall()
        assert len(rows) == 1, ('PL5H_ONE_RECEIPT', rows)
        gv = pbase.group_version(cur, str(group))
        prod.owner(cur)
        pbase.action(cur, 'POST_FINAL_SKU', {'cutting_group_id': str(group), 'destination_location_id': pbase.LOCATION, 'physical_at': prod.at(day, 13).isoformat(),
                     'reason': 'PL5H final SKU', 'good_qty_pcs': good, 'completion_mode': 'ALL_READY',
                     'lines': [dict(final_product_id=item['id'], qty_good_pcs=good, qty_bs_pcs=cut - good, source_laundry_receipt_line_id=str(rows[0][1]),
                                    source_laundry_receipt_batch_size_line_id=str(rows[0][0]))]}, gv)
        az.api.admin(cur)
        out = dict(group=str(group), day=day, cut=cut, good=good, case=None, resolution=None)
        if cut > good:
            out['case'] = cur.execute('select id::text from erp.bs_cases where cutting_group_id=%s and qc_item_id is not null', (group,)).fetchone()[0]
            out['resolution'] = self.scrap(out, prod.at(day, 14))
        return out

    def scrap(self, g, at):
        r = b.chain.bs_action(self.cur, 'DISPOSE_BS', dict(bs_case_id=g['case'], resolution_type='SCRAP', qty_pcs=g['cut'] - g['good'],
                                                           physical_at=at.isoformat(), change_reason='PL5H BS scrapped'),
                              b.chain.version(self.cur, 'bs_cases', g['case']))
        b.api.admin(self.cur)
        return r['result']['bs_resolution_id']


# A PL-5 group is finished through its sewing terminal and its BS resolution (scrap); PL-8's clone closure
# has neither, so a clone without them is honestly not exhausted. These two tables join the closure here only.
CLONE_EXTRA = (('sewing_terminal_events', 'cutting_group_id=%(g)s'),
               ('bs_resolutions', 'bs_case_id in(select id from erp.bs_cases where cutting_group_id=%(g)s)'))


def clone(cur, group, n, label):
    return supply.clone_groups(cur, group, n, label, CLONE_EXTRA)


def prove(cur, groups):
    """The unchanged prover (batch_verdict, store_proofs) over the case's own groups only, in batches of 50, at
    this clock: the ordinary prover proves every posted group; restricting it keeps the oracle exact."""
    b.api.admin(cur)
    made = 0
    for i in range(0, len(groups), 50):
        made += cur.execute("""select cp7_supply_native.store_proofs(cp7_supply_native.batch_verdict(
            cp7_wip.capture_cutting_sources(%s::uuid[],c.at),cp7_supply_native.proof_kernel())->'proofs',c.at)
          from(select clock_timestamp()at)c""", (groups[i:i + 50],)).fetchone()[0]
    return made


def proofs_of(cur, groups):
    b.api.admin(cur)
    return {r[0]: r[1] for r in cur.execute("""select group_id::text,count(*)from cp7_supply_native.exhaustion_proofs
        where group_id=any(%s::uuid[])group by 1""", (groups,)).fetchall()}


def level(h, name):
    return next(x for x in h['levels'] if x['level'] == name)


def rows(cur):
    b.api.admin(cur)
    return cur.execute('select (select count(*)from cp7_yield_policy.policies),(select count(*)from cp7_yield_policy.commands)').fetchone()


def available(h, lvl, groups, cut, fg):
    k = wilson(fg, cut)
    assert (h['status'], h['level'], h['groups'], h['cut_pcs'], h['fg_pcs'], h['lower_bound_permille'], h['numerator'], h['denominator']) == \
        ('AVAILABLE', lvl, str(groups), str(cut), str(fg), str(k), str(k), '1000'), h
    assert 1 <= k < 1000 and h['contract_version'] == 'cp7.history-yield.v2' and h['basis'] == 'PL8_STORED_PROOF_MATCHING_CURRENT_FACTS', h
    return k


def cases(cur, today):
    def pending():
        owner = actor(cur)
        p = product(cur, 'pending')
        h, _ = history(cur, p['target'], p['model'], owner)
        assert h == dict(status='PENDING_POLICY_VALUE', reason='OWNER_HISTORY_YIELD_POLICY_NOT_APPROVED', window_days=None, minimum_sample=None,
                         lower_bound=None, numerator=None, denominator=None, target_key=p['target']), h
        ws = workspace(cur, owner)
        assert ws['contract_version'] == 'cp7.history-yield-policy.v1' and ws['state'] == 'PENDING_POLICY_VALUE' and ws['current'] is None
        assert ws['revisions'] == [] and ws['decided_package'] == DECIDED and ws['manage_allowed'] is True, ws
        assert rows(cur) == (0, 0)
        return dict(status='PASS', pending_answer_byte_for_byte=True, decided_package_shown_not_in_force=True, nothing_written=True)

    def signed():
        owner = actor(cur)
        admin = actor(cur, 'ADMIN')
        key = uuid.uuid4()
        before = time.time()
        first = save(cur, payload(), owner, key)
        r = first['policy']
        assert first['contract_version'] == 'cp7.history-yield-policy-outcome.v1' and first['request_id'] == str(key), first
        assert (r['revision'], r['state'], r['window_days'], r['min_groups'], r['min_cut_pcs'], r['confidence'], r['actor'], r['actor_role']) == \
            ('1', 'ACTIVE', '180', '5', '200', '0.90', owner, 'OWNER'), r
        assert r['method'] == DECIDED['method'] and r['rounding'] == DECIDED['rounding'] and r['levels'] == DECIDED['levels'] and r['reason'].startswith('Keputusan owner')
        assert save(cur, payload(), owner, key) == first
        refused(cur, lambda: save(cur, payload(reason='other'), owner, key), 'CP7_YIELD_POLICY_REQUEST_CHANGED')
        refused(cur, lambda: save(cur, payload(), owner), 'CP7_YIELD_POLICY_REVISION_CHANGED', '40001')
        second = save(cur, payload(expected='1', state='PAUSED', reason='Jeda uji'), admin)['policy']
        assert (second['revision'], second['state'], second['actor_role']) == ('2', 'PAUSED', 'ADMIN'), second
        for sql in ('update cp7_yield_policy.policies set reason=reason', 'delete from cp7_yield_policy.policies',
                    'update cp7_yield_policy.commands set payload=payload', 'delete from cp7_yield_policy.commands'):
            refused(cur, lambda sql=sql: cur.execute(sql), 'CP7_POLICY_HISTORY_IMMUTABLE')
        ws = workspace(cur, owner)
        assert ws['state'] == 'PAUSED' and ws['current']['revision'] == '2' and [x['revision'] for x in ws['revisions']] == ['2', '1'], ws
        assert rows(cur) == (2, 2)
        return dict(status='PASS', signed_actor_role_reason_time=True, replay_same_request=True, changed_request_refused=True,
                    stale_revision_40001=True, second_revision_by_admin=True, rows_immutable=True, recorded_after=before <= time.time())

    def values_authority():
        owner = actor(cur)
        bad = [dict(confidence='0.95'), dict(confidence='0.9'), dict(window_days='0'), dict(window_days='3661'), dict(window_days='1.5'),
               dict(min_groups='0'), dict(min_groups='-1'), dict(min_cut_pcs='1000001'), dict(window_days=180), dict(state='ON'),
               dict(reason=' ')]
        codes = []
        for change in bad:
            p = payload()
            p.update(change)
            state, message, _ = refusal(cur, lambda p=p: save(cur, p, owner))
            codes.append(message)
        assert codes == ['CP7_YIELD_POLICY_CONFIDENCE_FIXED'] * 2 + ['CP7_YIELD_POLICY_VALUES'] * 7 + ['CP7_YIELD_POLICY_REVIEW'] * 2, codes
        extra = dict(payload(), z='1.0')
        refused(cur, lambda: save(cur, extra, owner), 'CP7_WIP_FIELDS')
        manager = custom(cur, True)
        viewer = custom(cur, False)
        refused(cur, lambda: save(cur, payload(), manager), 'CP7_YIELD_POLICY_OWNER_ADMIN_REQUIRED', '42501')
        refused(cur, lambda: save(cur, payload(), viewer), 'CP7_POLICY_ACCESS_DENIED', '42501')
        ws = workspace(cur, viewer)
        assert ws['manage_allowed'] is False and ws['state'] == 'PENDING_POLICY_VALUE', ws
        assert workspace(cur, manager)['manage_allowed'] is False
        assert rows(cur) == (0, 0)
        return dict(status='PASS', invalid_values_refused=len(bad) + 1, confidence_fixed_at_owner_decision=True,
                    non_owner_admin_refused=True, without_manage_refused=True, read_allowed_without_manage=True, nothing_written=True)

    def product_size():
        owner = actor(cur)
        p = product(cur, 'ps')
        make = Production(cur, today)
        made = [make.group(p, 40, 37) for _ in range(5)]
        groups = [g['group'] for g in made]
        # The ordinary proof capture (public supply capture) stores the proofs.
        supply.capture(cur, today)
        stored = proofs_of(cur, groups)
        assert sorted(stored) == sorted(groups), stored
        h0, _ = history(cur, p['target'], p['model'], owner)
        assert h0['status'] == 'PENDING_POLICY_VALUE' and h0['numerator'] is None, h0
        save(cur, payload(), owner)
        h, ms = history(cur, p['target'], p['model'], owner)
        k = available(h, 'PRODUCT_SIZE', 5, 200, 185)
        assert k == 897 and h['lower_bound'] == '0.897' and level(h, 'MODEL')['status'] == 'NOT_EVALUATED', h
        assert sorted(x['group_id'] for x in h['proofs']) == sorted(groups), h['proofs']
        for x in h['proofs']:
            first = cur.execute("""select id::text from cp7_supply_native.exhaustion_proofs where group_id=%s and facts_hash=%s and kernel_version=%s
              order by captured_at,id limit 1""", (x['group_id'], x['facts_hash'], h['kernel_version'])).fetchone()
            assert first and first[0] == x['proof_id'], (x, first)
        assert (h['policy']['revision'], h['window_days'], h['minimum_sample']) == ('1', '180', dict(groups='5', cut_pcs='200')), h
        first_day = cur.execute("select (clock_timestamp() at time zone 'Asia/Jakarta')::date-179").fetchone()[0]
        assert h['window_first_day'] == first_day.isoformat(), (h['window_first_day'], first_day)
        need = 100
        return dict(status='PASS', ordinary_finished_groups=5, cut=200, good=185, scrapped_bs=15, lower_bound_permille=k,
                    cut_for_need_100=math.ceil(need * 1000 / k), proofs_from_ordinary_capture=True, history_ms=ms)

    def model_fallback():
        owner = actor(cur)
        p, other = product(cur, 'target'), product(cur, 'colour')
        make = Production(cur, today)
        mine = [make.group(p, 40, 37) for _ in range(2)]
        theirs = [make.group(other, 40, 36) for _ in range(3)]
        assert prove(cur, [g['group'] for g in mine + theirs]) == 5
        save(cur, payload(), owner)
        h, _ = history(cur, p['target'], p['model'], owner)
        ps = level(h, 'PRODUCT_SIZE')
        assert (ps['status'], ps['groups'], ps['cut_pcs'], ps['fg_pcs']) == ('INSUFFICIENT_SAMPLE', '2', '80', '74'), ps
        k = available(h, 'MODEL', 5, 200, 182)
        assert level(h, 'MODEL')['status'] == 'SUFFICIENT'
        return dict(status='PASS', product_size_insufficient=[2, 80], model_level_same_model_other_colour=[5, 200, 182], lower_bound_permille=k)

    def insufficient():
        owner = actor(cur)
        p = product(cur, 'few')
        make = Production(cur, today)
        mine = [make.group(p, 40, 37) for _ in range(2)]
        assert prove(cur, [g['group'] for g in mine]) == 2
        save(cur, payload(), owner)
        h, _ = history(cur, p['target'], p['model'], owner)
        assert (h['status'], h['reason'], h['level'], h['numerator'], h['denominator'], h['lower_bound']) == \
            ('INSUFFICIENT_SAMPLE', 'HISTORY_SAMPLE_BELOW_POLICY', None, None, None, None), h
        for name in ('PRODUCT_SIZE', 'MODEL'):
            x = level(h, name)
            assert (x['status'], x['groups'], x['cut_pcs'], x['fg_pcs'], x['lower_bound_permille']) == ('INSUFFICIENT_SAMPLE', '2', '80', '74', None), x
        return dict(status='PASS', two_groups_80_pcs_no_value=True, never_assumed_100_percent=True, plan_falls_back_to_reviewed_A_or_unknown='PL5H_PLAN_USES_HISTORY_LIVE')

    def cross_model():
        owner = actor(cur)
        p = product(cur, 'base')
        make = Production(cur, today)
        made = [make.group(p, 40, 37) for _ in range(5)]
        groups = [g['group'] for g in made]
        assert prove(cur, groups) == 5
        q, _ = ax.owner_only_model_product(cur)
        b.api.admin(cur)
        qt = cur.execute('select coalesce(identity_root_id,id)::text||\':\'||size_id::text,model_id::text from erp.products where id=%s', (q,)).fetchone()
        # SYNTHETIC (labelled): one clone of a finished base-model group whose order is re-pointed to the other
        # model; its QC still went to a base-model product, so it is not attributable to the other model.
        twin = clone(cur, groups[0], 1, 'PL5H SYNTHETIC cross-model attribution probe')[0]
        po2 = str(uuid.uuid4())
        cur.execute("insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,notes)values(%s,%s,%s,10,'CUTTING','CUTTING','PL5H SYNTHETIC other model')",
                    (po2, 'PL5H-PO2-' + po2, qt[1]))
        cur.execute("select set_config('session_replication_role','replica',true)")
        cur.execute('update erp.cutting_groups set po_id=%s where id=%s', (po2, twin))
        cur.execute("select set_config('session_replication_role','origin',true)")
        assert prove(cur, [twin]) == 1
        save(cur, payload(), owner)
        hq, _ = history(cur, qt[0], qt[1], owner)
        assert hq['status'] == 'INSUFFICIENT_SAMPLE' and level(hq, 'MODEL')['groups'] == '0' and level(hq, 'PRODUCT_SIZE')['groups'] == '0', hq
        assert hq['excluded']['unattributed'] == '1', hq['excluded']
        wrong, _ = history(cur, p['target'], qt[1], owner)
        assert (wrong['status'], wrong['reason']) == ('UNKNOWN', 'TARGET_MODEL_CHANGED'), wrong
        hp, _ = history(cur, p['target'], p['model'], owner)
        available(hp, 'PRODUCT_SIZE', 5, 200, 185)
        return dict(status='PASS', other_model_target_gets_nothing_from_base_model=True, re_pointed_order_without_own_qc_unattributed=True,
                    wrong_model_refused=True, base_target_unchanged=True)

    def never_100():
        owner = actor(cur)
        p = product(cur, 'allgood')
        make = Production(cur, today)
        made = [make.group(p, 40, 40) for _ in range(5)]
        assert prove(cur, [g['group'] for g in made]) == 5
        save(cur, payload(), owner)
        h, _ = history(cur, p['target'], p['model'], owner)
        k = available(h, 'PRODUCT_SIZE', 5, 200, 200)
        assert k == 991 and h['lower_bound'] == '0.991', h
        return dict(status='PASS', all_good_200_of_200=True, lower_bound_permille=k, below_1000=True)

    def wilson_exact():
        b.api.admin(cur)
        got = cur.execute('select n,x,cp7_plan_native.wilson_permille(x,n)from generate_series(1,400)n,generate_series(0,n)x order by 1,2').fetchall()
        wrong = [(n, x, k) for n, x, k in got if k != wilson(x, n)]
        assert not wrong, wrong[:5]
        examples = {(180, 200): 869, (186, 200): 903, (185, 200): 897, (200, 200): 991, (0, 200): 0}
        for (x, n), k in examples.items():
            assert cur.execute('select cp7_plan_native.wilson_permille(%s,%s)', (x, n)).fetchone()[0] == k == wilson(x, n), (x, n, k)
        big = [(n, n) for n in (10**3, 10**5, 10**6)]
        assert all(cur.execute('select cp7_plan_native.wilson_permille(%s,%s)', (x, n)).fetchone()[0] < 1000 for x, n in big)
        for x, n in ((-1, 5), (6, 5), (0, 0)):
            refused(cur, lambda x=x, n=n: cur.execute('select cp7_plan_native.wilson_permille(%s,%s)', (x, n)), 'CP7_HISTORY_YIELD_WILSON_INPUT')
        return dict(status='PASS', pairs_checked=len(got), proposal_example_180_of_200=869, cut_for_need_100=math.ceil(100 * 1000 / 869),
                    never_1000=True, invalid_inputs_refused=3)

    def cancel_correct_backdate():
        owner = actor(cur)
        p = product(cur, 'redo')
        make = Production(cur, today)
        made = [make.group(p, 40, 37) for _ in range(5)]
        groups = [g['group'] for g in made]
        assert prove(cur, groups) == 5
        save(cur, payload(), owner)
        h, _ = history(cur, p['target'], p['model'], owner)
        available(h, 'PRODUCT_SIZE', 5, 200, 185)
        old = next(x['proof_id'] for x in h['proofs'] if x['group_id'] == groups[0])
        # Cancellation: the scrap of one group is reversed through the ordinary command.
        g0 = made[0]
        b.chain.bs_action(cur, 'REVERSE_DISPOSITION', dict(resolution_id=g0['resolution'], change_reason='PL5H scrap reversed'),
                          b.chain.version(cur, 'bs_cases', g0['case']))
        b.api.admin(cur)
        h, _ = history(cur, p['target'], p['model'], owner)
        ps = level(h, 'PRODUCT_SIZE')
        assert h['status'] == 'INSUFFICIENT_SAMPLE' and (ps['groups'], ps['cut_pcs'], ps['fg_pcs']) == ('4', '160', '148'), h
        assert h['excluded']['stale_or_unverifiable'] == '1', h['excluded']
        # Correction, backdated: scrapped again at an earlier physical time than the first scrap.
        make.scrap(g0, az.chain.production.at(g0['day'], 13, 30))
        h, _ = history(cur, p['target'], p['model'], owner)
        assert h['status'] == 'INSUFFICIENT_SAMPLE' and h['excluded']['stale_or_unverifiable'] == '1', h
        # Until proven again at the new facts; then it counts with its new proof.
        assert prove(cur, [groups[0]]) == 1
        h, _ = history(cur, p['target'], p['model'], owner)
        available(h, 'PRODUCT_SIZE', 5, 200, 185)
        new = next(x['proof_id'] for x in h['proofs'] if x['group_id'] == groups[0])
        assert new != old, (old, new)
        return dict(status='PASS', reversed_scrap_drops_group=True, backdated_rescrap_still_out_until_proven=True, reproven_counts_with_new_proof=True)

    def window():
        owner = actor(cur)
        p = product(cur, 'window')
        make = Production(cur, today)
        made = [make.group(p, 40, 37) for _ in range(5)]
        assert prove(cur, [g['group'] for g in made]) == 5
        yesterday = today - timedelta(days=1)
        assert all(g['day'] == yesterday for g in made)
        save(cur, payload(window_days='1'), owner)
        h, _ = history(cur, p['target'], p['model'], owner)
        assert h['status'] == 'INSUFFICIENT_SAMPLE' and h['excluded']['outside_window'] == '5' and level(h, 'PRODUCT_SIZE')['groups'] == '0', h
        save(cur, payload(expected='1', window_days='2', reason='Uji jendela dua hari'), owner)
        h, _ = history(cur, p['target'], p['model'], owner)
        available(h, 'PRODUCT_SIZE', 5, 200, 185)
        assert h['policy']['revision'] == '2' and h['excluded']['outside_window'] == '0'
        return dict(status='PASS', finished_yesterday_outside_one_day=True, inside_two_days=True, window_by_finish_date_WIB=True)

    def limit():
        owner = actor(cur)
        p = product(cur, 'limit')
        make = Production(cur, today)
        first = make.group(p, 40, 37)
        # SYNTHETIC (labelled): administrative clones of one finished group, as the PL-8 scale cases.
        clones = clone(cur, first['group'], 199, 'PL5H SYNTHETIC finished history at the 200-group limit')
        groups = [first['group']] + clones
        assert prove(cur, groups) == 200
        save(cur, payload(), owner)
        h, ms = history(cur, p['target'], p['model'], owner)
        available(h, 'PRODUCT_SIZE', 200, 8000, 7400)
        assert ms < 8000, ms
        # Clone ids are fixed per (source, number): the 201st is cloned from a clone, not from `first` again.
        extra = clone(cur, clones[-1], 1, 'PL5H SYNTHETIC group 201')
        assert prove(cur, extra) == 1
        h, ms2 = history(cur, p['target'], p['model'], owner)
        assert (h['status'], h['reason']) == ('UNKNOWN', 'HISTORY_GROUP_LIMIT') and level(h, 'PRODUCT_SIZE')['reason'] == 'HISTORY_GROUP_LIMIT', h
        return dict(status='PASS', groups_200_read_ms=ms, under_statement_timeout='8s', group_201_unknown_not_guessed=True, ms_at_201=ms2, limits_raised=False)

    def plan_live():
        owner = actor(cur)
        x = planv2.single(cur, today)
        target, model = x['target'], x['model']
        h0, _ = history(cur, target, model, owner)
        assert h0['status'] == 'PENDING_POLICY_VALUE'
        other = product(cur, 'plan-history')
        make = Production(cur, today)
        made = [make.group(other, 40, 37) for _ in range(5)]
        assert prove(cur, [g['group'] for g in made]) == 5
        save(cur, payload(), owner)
        h, _ = history(cur, target, model, owner)
        assert h['status'] == 'AVAILABLE' and h['level'] == 'MODEL' and int(h['groups']) >= 5, h
        k = int(h['numerator'])
        d = planv2.save(cur, x['payload'])
        v = planv2.preview(cur, d['draft_id'])
        y = v['new_start_yield']
        strip = lambda value: {key: item for key, item in value.items() if key != 'checked_at'}
        assert (y['basis'], y['numerator'], y['denominator']) == ('HISTORY_NATIVE', str(k), '1000') and strip(y['history']) == strip(h), y
        need = Decimal(v['needed_pcs'])
        assert Decimal(v['cut_limit_pcs']) == math.ceil(need * 1000 / k) and v['cut_limit_basis'] == 'NEED_AT_STATED_YIELD', v
        assert v['live']['apply_ready'] is True, v['live']
        est = dict(x['payload'], new_start_yield=dict(numerator='9', denominator='10'),
                   reviewed_assumption_ids=x['payload']['reviewed_assumption_ids'] + ['PLAN_NEW_START_YIELD'])
        refused(cur, lambda: planv2.save(cur, est), 'CP7_PLAN_NEW_START_YIELD_HISTORY_AVAILABLE')
        # The policy paused: no history value; the reviewed estimate A is accepted, without it the yield is UNKNOWN.
        save(cur, payload(expected='1', state='PAUSED', reason='Jeda uji rencana'), owner)
        a = planv2.preview(cur, planv2.save(cur, est)['draft_id'])
        assert a['new_start_yield']['basis'] == 'PLAN_ESTIMATE_REVIEWED' and a['new_start_yield']['history']['status'] == 'POLICY_PAUSED', a['new_start_yield']
        u = planv2.preview(cur, planv2.save(cur, x['payload'])['draft_id'])
        assert u['new_start_yield']['basis'] == 'UNKNOWN' and u['cut_limit_basis'] == 'NEED_CAP_YIELD_UNKNOWN_NOT_ASSUMED_100_PERCENT' and u['unresolved_pcs'] is None, u
        # Active again: apply re-reads the history in its own transaction and creates the Native draft.
        save(cur, payload(expected='2', reason='Aktif kembali sesudah uji'), owner)
        out = planv2.apply(cur, planv2.action(d))
        assert out['state'] == 'NATIVE_DRAFT_CREATED', out
        return dict(status='PASS', preview_history_equals_reader=True, cut_limit_ceil_need_1000_over_k=True, estimate_refused_while_available=True,
                    applied_with_live_recheck=True, paused_policy_A_or_unknown=True, lower_bound_permille=k)

    def catalog():
        b.api.admin(cur)
        for sig in SIGNATURES:
            assert cur.execute("select has_function_privilege('authenticated',%s,'EXECUTE')", (sig,)).fetchone()[0]
            assert not cur.execute("select has_function_privilege('anon',%s,'EXECUTE')", (sig,)).fetchone()[0]
        for sig in PRIVATE:
            for who in ('anon', 'authenticated', 'service_role'):
                assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')', (who, sig)).fetchone()[0], (who, sig)
        for table in ('cp7_yield_policy.policies', 'cp7_yield_policy.commands'):
            for who in ('anon', 'authenticated', 'service_role', 'cp7_plan_writer'):
                assert not cur.execute('select has_table_privilege(%s,%s,\'SELECT,INSERT,UPDATE,DELETE\')', (who, table)).fetchone()[0], (who, table)
        assert cur.execute("select has_function_privilege('cp7_plan_writer','cp7_plan_native.history_source(text,uuid)','EXECUTE')").fetchone()[0]
        public = [r[0] for r in cur.execute("""select p.proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace
          where n.nspname='public'and p.proname like 'erp_cp7_%%history_yield%%' order by 1""").fetchall()]
        assert public == sorted(FUNCTIONS), public
        return dict(status='PASS', two_public_wrappers=public, private_functions_closed=len(PRIVATE), tables_closed=True)

    return list(zip(IDS['native'], (pending, signed, values_authority, product_size, model_fallback, insufficient, cross_model, never_100,
                                    wilson_exact, cancel_correct_backdate, window, limit, plan_live, catalog)))


def races(tools, today):
    def owners():
        with tools.connect() as conn, conn.cursor() as cur:
            subjects = [actor(cur), actor(cur)]
            conn.commit()
        return subjects

    def send(subject, p, key, gate):
        with tools.connect() as conn, conn.cursor() as cur:
            gate.wait(timeout=8)
            try:
                r = save(cur, p, subject, key)
                conn.commit()
                return r
            except psycopg.Error as e:
                conn.rollback()
                return dict(error=e.diag.message_primary, sqlstate=e.sqlstate)

    def counts():
        with tools.connect() as conn, conn.cursor() as cur:
            return rows(cur)

    def revision():
        with tools.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            return cur.execute('select coalesce(max(revision),0)from cp7_yield_policy.policies').fetchone()[0]

    def same_revision():
        a, b_ = owners()
        rev, before = revision(), counts()
        gate = threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(send, s, payload(expected=str(rev), reason='Balapan ' + s[:4]), uuid.uuid4(), gate) for s in (a, b_)]
            results = [j.result(60) for j in jobs]
        won = [r for r in results if 'policy' in r]
        lost = [r for r in results if r.get('sqlstate') == '40001']
        assert len(won) == len(lost) == 1 and lost[0]['error'] == 'CP7_YIELD_POLICY_REVISION_CHANGED' and won[0]['policy']['revision'] == str(rev + 1), results
        assert counts() == (before[0] + 1, before[1] + 1)
        return dict(status='PASS', one_revision_one_refusal=True, refusal=lost[0]['error'])

    def same_request():
        a, _ = owners()
        rev, before = revision(), counts()
        key, gate = uuid.uuid4(), threading.Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(send, a, payload(expected=str(rev)), key, gate) for _ in range(2)]
            results = [j.result(60) for j in jobs]
        assert results[0] == results[1] and 'policy' in results[0], results
        assert counts() == (before[0] + 1, before[1] + 1)
        return dict(status='PASS', one_uuid_two_sessions_one_row=True)

    return list(zip(IDS['races'], (same_revision, same_request)))


def http_cases(http, today):
    state = {}

    def flow():
        owner = http.login('OWNER', 'pl5h-owner')

        def ok(name, args):
            r = owner.rpc(name, args)
            assert r['status'] == 200, (name, r)
            return r['body']
        ws = ok('erp_cp7_get_history_yield_policy_v1', {})
        assert ws['decided_package'] == DECIDED and ws['manage_allowed'] is True, ws
        rev = int(ws['current']['revision']) if ws['current'] else 0
        args = dict(p_payload=payload(expected=str(rev)), p_request=str(uuid.uuid4()))
        one = ok('erp_cp7_save_history_yield_policy_v1', args)
        assert ok('erp_cp7_save_history_yield_policy_v1', args) == one and one['policy']['revision'] == str(rev + 1)
        assert ok('erp_cp7_get_history_yield_policy_v1', {})['current']['revision'] == str(rev + 1)
        anonymous = [http.anon_rpc(name, a)['status'] for name, a in (('erp_cp7_get_history_yield_policy_v1', {}), ('erp_cp7_save_history_yield_policy_v1', args))]
        assert all(code in (401, 403) for code in anonymous), anonymous
        with http.connect() as conn, conn.cursor() as cur:
            state['rows'] = rows(cur)
        state.update(owner=owner, args=args)
        return dict(status='PASS', real_Auth_read_save_replay=True, anonymous_refused=anonymous)

    def revoked():
        assert state, 'PL5H_REQUIRED_PRIOR_HTTP_CASE'
        owner = state['owner']
        with http.connect() as conn, conn.cursor() as cur:
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (owner.auth_user_id,))
            conn.commit()
        rev = state['args']['p_payload']['expected_revision']
        codes = [owner.rpc(name, a)['status'] for name, a in (('erp_cp7_get_history_yield_policy_v1', {}),
                 ('erp_cp7_save_history_yield_policy_v1', dict(p_payload=payload(expected=str(int(rev) + 1), state='PAUSED'), p_request=str(uuid.uuid4()))))]
        assert codes == [403, 403], codes
        with http.connect() as conn, conn.cursor() as cur:
            assert rows(cur) == state['rows']
        return dict(status='PASS', deactivated_user_403=codes, nothing_written=True)

    return list(zip(IDS['http'], (flow, revoked)))

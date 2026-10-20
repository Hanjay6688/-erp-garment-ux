"""OW-01 proposal: exact Native accessory need -> a WA source-review notice.

Six additions to the retained 65-case WA suite. These tests deliberately keep
gross BOM demand separate from installation, allocated unused supply, and the
additional external quantity. Only the first is computable by this Native
fixture: target100 - projectedWIP7 = gap93; BOM2 * gap93 = gross186 ASSUMED.

The savepoint cases inspect the genuine pg_net queue, not provider delivery.
The transport proposal uses prepared()/assert_detail() with the real fake
CallMeBot worker and its request log for that separate proof.

Administrative invalid-master and private-reader-fault fixtures are labelled
at their mutations. They do not claim to be accepted business commands. The
positive source, the BOM successor, receipts, issues, and found FG use the
unchanged accepted Native writers. No Native guard is changed by this module.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from decimal import Decimal as D
import json
import uuid

import cp7_p19_staged_cases as staged

analysis = staged.analysis
material = analysis.material_cases
RULE = 'ACCESSORY_NEED'
REVIEW_REASON = 'INSTALLATION_AND_ELIGIBLE_UNUSED_SUPPLY_NOT_PROVEN'
NATIVE_IDS = [
    'WAF_ACCESSORY_NEED_NATIVE_UNKNOWN_FORWARDED',
    'WAF_ACCESSORY_NEED_MISSING_EMPTY',
    'WAF_ACCESSORY_NEED_BOM_SUCCESSOR',
    'WAF_ACCESSORY_NEED_CURRENT_PERMISSIONS',
    'WAF_ACCESSORY_NEED_ISSUE_NOT_INSTALLATION_RESOLVED',
    'WAF_ACCESSORY_NEED_POLICY_REPLAY_DEDUP',
]
DETAIL_KEYS = frozenset('run_id data_as_of checked_at label target_key category_key category_name state verdict '
    'gross_state gross_qty unit installed_state installed_proven unused_allocated_state unused_allocated_proven '
    'additional_external_state additional_external threshold_status reason'.split())
assert len(DETAIL_KEYS) == 20
UNKNOWN_FACTS = ('installed_proven', 'unused_allocated_proven', 'additional_external')
WA_VALUES = dict(kinds=[RULE], detail='DETAILED', analysis_every_minutes=0, repeat_minutes=1440)


@contextmanager
def isolated(cur, wa):
    """A complete subcase rolls back before another selected-profile fixture."""
    wa.b.api.admin(cur)
    name = 'ow01a_' + uuid.uuid4().hex
    cur.execute('savepoint ' + name)
    try:
        yield
    finally:
        # Recover an aborted statement before trying to change authorization.
        cur.execute('rollback to savepoint ' + name)
        wa.b.api.admin(cur)
        cur.execute('release savepoint ' + name)


def _json_version(version):
    if version is None:
        return None
    out = dict(version)
    if isinstance(out.get('at'), datetime):
        out['at'] = out['at'].isoformat()
    return out


def _settings(cur, wa, subject=None):
    """Create/configure the active owner BEFORE taking any source snapshot."""
    if subject is None:
        return wa.setup(cur, enabled=False, kinds=[], detail='DETAILED', analysis_every_minutes=0)
    wa.pg_net(cur)
    wa.b.api.admin(cur)
    user = cur.execute('select id::text from erp.app_users where auth_user_id=%s and is_active', (subject,)).fetchone()
    assert user is not None, 'OW01_EXPLICIT_FIXTURE_OWNER_NOT_ACTIVE'
    wa.save(cur, subject, enabled=False, kinds=[], detail='DETAILED', analysis_every_minutes=0)
    wa.rpc(cur, 'erp_cp7_set_wa_key_v1', (wa.KEY, str(uuid.uuid4())), subject)
    wa.b.api.admin(cur)
    cur.execute('update cp7_alert_native.transport set base_url=%s', (wa.FAKE,))
    return dict(owner=str(subject), user=user[0])


def quiet_window(cur, wa):
    """Explicitly selected local/WA quiet interval containing the actual WIB time."""
    wa.b.api.admin(cur)
    starts, ends = cur.execute("select to_char((clock_timestamp() at time zone 'Asia/Jakarta')-interval'1 hour','HH24:MI'),"
        "to_char((clock_timestamp() at time zone 'Asia/Jakarta')+interval'1 hour','HH24:MI')").fetchone()
    assert starts != ends
    return dict(enabled=True, starts_at=starts, ends_at=ends, timezone='Asia/Jakarta')


def policy_payload(cur, wa, x, *, enabled=True, threshold='1', local_quiet=False):
    """Read the actual CAS revision; no hard-coded revision0 after a policy exists."""
    wa.b.api.admin(cur)
    rev = cur.execute("select coalesce(max(revision),0) from cp7_reminder_native.rule_policies "
        "where rule_id=%s and scope_kind='GLOBAL' and scope_key='*'", (RULE,)).fetchone()[0]
    quiet = quiet_window(cur, wa) if local_quiet else deepcopy(wa.remv2.QUIET)
    return dict(run_id=x['r']['run'], identity_hash=x['r']['identity'], rule_id=RULE, scope_kind='GLOBAL', scope_key='*',
        expected_revision=str(rev), config=dict(enabled=enabled, threshold_value=str(threshold), threshold_unit=x['m']['gross']['unit'],
        cooldown_minutes='120' if local_quiet else '0', quiet=quiet),
        reason='OW01 explicit fixture choice: source review only, never an inferred purchase amount')


def save_policy(cur, wa, x, *, enabled=True, threshold='1', local_quiet=False, key=None):
    p = policy_payload(cur, wa, x, enabled=enabled, threshold=threshold, local_quiet=local_quiet)
    out = wa.remv2.command(cur, 'erp_cp7_save_reminder_policy_v2', p, key, x['source_subject'])
    assert out['result']['status'] == 'COMMITTED' and int(out['result']['revision']) == int(p['expected_revision']) + 1, out
    return p, out


def _source(cur, today, wa, mode, issue80):
    assert mode in ('VALID', 'MISSING', 'EMPTY', 'INACTIVE', 'OVERLAP'), mode
    assert not issue80 or mode == 'VALID'
    if issue80:
        _, root, _, _ = analysis.setup(cur, today)
        issue = material.issue
        f = issue.receipt(cur, today, qty='80')
        wa.b.api.admin(cur)
        category, unit = cur.execute('select accessory_category_id,unit_code from erp.materials where id=%s', (f['material'],)).fetchone()
        category = dict(category_id=str(category), unit=unit)
        version = material.bom(cur, root, analysis, category, qty='2')
        p = issue.payload(f)
        p.update(location_id=f['main'], po_id=None)
        p['items'][0]['qty'] = '80'
        p['reason'] = 'OW01 explicit Native issue80; an issue is not installation or allocation proof'
        draft = issue.bc.note_call(cur, 'SAVE_DRAFT', p)
        p.update(id=draft['id'], expected_version=draft['row_version'])
        posted = issue.bc.note_call(cur, 'POST', p)
        document = issue.bc.note_read(cur, dict(id=posted['id']))['document']
        assert document['status'] == 'POSTED' and issue.bc.stock(cur, f['material'], f['main']) == 0
        issue_proof = dict(note_id=str(posted['id']), material_id=str(f['material']), main_location_id=str(f['main']),
            posted_quantity='80', warehouse_remaining='0')
    elif mode == 'MISSING':
        _, root, _, _ = analysis.setup(cur, today)
        at = cur.execute('select clock_timestamp()').fetchone()[0]
        # Existing P06 administrative master fixture, before any shared-master
        # adoption. Missing means no effective version, never an empty recipe.
        material.close_current(cur, root, analysis, at)
        category, version, issue_proof = None, None, None
    else:
        f = material.prepared(cur, today, analysis, empty=mode == 'EMPTY')
        root, version = f['root'], f['bom']
        category = None if f['category'] is None else dict(category_id=f['category']['category_id'], unit=f['category']['unit'])
        issue_proof = None
        if mode == 'INACTIVE':
            # Administrative invalid-master fixture, already used by P06.
            # No physical quantity or financial source row is fabricated.
            wa.b.api.admin(cur)
            cur.execute('update erp.accessory_categories set is_active=false where id=%s', (category['category_id'],))
        elif mode == 'OVERLAP':
            # ADMINISTRATIVE_INVALID_MASTER_FIXTURE: the accepted BF command
            # prevents this state. Deliberately seed a corrupt master, without
            # changing any guard definition or claiming Native-writer acceptance.
            wa.b.api.admin(cur)
            prior = cur.execute('show session_replication_role').fetchone()[0]
            cur.execute('set local session_replication_role=replica')
            try:
                duplicate = cur.execute("insert into erp.accessory_bom_versions(product_id,version_label,effective_from,is_active,notes) "
                    "values(%s,%s,clock_timestamp(),true,%s) returning id::text", (root, 'OW01-INVALID-' + uuid.uuid4().hex,
                    'ADMINISTRATIVE_INVALID_MASTER_FIXTURE: overlapping effective BOM, not an accepted BF operation')).fetchone()[0]
            finally:
                cur.execute('select set_config(\'session_replication_role\',%s,true)', (prior,))
            assert duplicate != version['id']
    material.review_schedule(cur, today, analysis)
    wa.b.api.admin(cur)
    product = cur.execute('select coalesce(identity_root_id,id)::text,model_id::text,size_id::text from erp.products where id=%s', (root,)).fetchone()
    assert product is not None and product[0] == str(root)
    if category is not None:
        category['category_name'] = cur.execute('select category_name from erp.accessory_categories where id=%s', (category['category_id'],)).fetchone()[0]
    return dict(root=str(root), model=product[1], size=product[2], category=category, bom=_json_version(version), issue=issue_proof, mode=mode)


def _stage(cur, today, wa, f, s, source_subject, *, policy, policy_enabled, enabled, threshold, local_quiet, collect):
    # Metadata owner/settings and every Native source mutation already exist.
    # This boundary therefore isolates the capture + reminder + WA effects.
    wa.b.api.admin(cur)
    context = cur.execute("select jsonb_build_object('setup_current_user',current_user,'setup_session_user',session_user,"
        "'postgres_role_superuser',(select rolsuper from pg_roles where rolname='postgres'),"
        "'capture_role_superuser',(select rolsuper from pg_roles where rolname='cp7_capture'),"
        "'reminder_role_superuser',(select rolsuper from pg_roles where rolname='cp7_reminder'))").fetchone()[0]
    assert context['capture_role_superuser'] is False and context['reminder_role_superuser'] is False, context
    assert context['postgres_role_superuser'] is False, 'OW01_NON_SUPERUSER_DEFINER_PROOF_REQUIRED: ' + json.dumps(context)
    boundary = wa.b.boundary.snapshot(cur)
    _, _, done, _ = staged.staged_done(cur, today, subject=source_subject)
    run = done['run_id']
    document, pages, _ = staged.fetch(cur, run, source_subject)
    expected_target = f['root'] + ':' + f['size']
    expected_material = (None if f['mode'] in ('MISSING', 'OVERLAP') else
                         'NO_ACCESSORY:' + f['root'] if f['mode'] == 'EMPTY' else
                         'ACCESSORY_CATEGORY:' + f['category']['category_id'])
    # material.rows also contains this target's FABRIC_UNREVIEWED row. Select
    # the exact accessory source, then retain the uniqueness and value checks.
    rows = [m for m in material.rows(document, f['root'])
            if m['target_key'] == expected_target and m['material_key'] == expected_material]
    assert len(rows) == 1, (expected_target, expected_material, rows)
    m = rows[0]
    assert m['target_key'] == f['root'] + ':' + f['size'], (m['target_key'], f)
    r = dict(run=run, identity=pages['identity_hash'], target=m['target_key'], root=f['root'])
    x = dict(s=dict(s), f=f, r=r, m=m, key=RULE + ':' + r['target'] + ':' + (m['material_key'] or 'UNKNOWN_BOM'),
        document=document, source_subject=str(source_subject), boundary=boundary, ticks=[], execution_context=context)
    if policy:
        p, result = save_policy(cur, wa, x, enabled=policy_enabled, threshold=threshold, local_quiet=local_quiet)
        x.update(policy_payload=p, policy_result=result)
    if enabled is not None:
        assert str(source_subject) == str(s['owner']), 'OW01_COLLECTOR_ACTOR_MUST_OWN_THE_STAGED_RUN'
        wa.save(cur, s['owner'], enabled=enabled, **WA_VALUES)
    if collect:
        assert str(source_subject) == str(s['owner']), 'OW01_COLLECTOR_ACTOR_MUST_OWN_THE_STAGED_RUN'
        x['ticks'] = wa.drain(cur)
        assert x['ticks'][-1] == 'ANALYSIS_CHECKED', x['ticks']
    else:
        wa.remv2.ready_set(cur, run, source_subject)
    x['c'] = wa.remv2.row(wa.remv2.conditions(cur, run, RULE, subject=source_subject), x['key'])
    assert wa.b.boundary.snapshot(cur) == boundary, 'OW01_CAPTURE_OR_REMINDER_WROTE_NATIVE'
    return x


def prepared(cur, today, wa, *, subject=None, settings=None, mode='VALID', policy=True, policy_enabled=True,
             enabled=True, threshold='1', local_quiet=False, issue80=False, collect=True):
    """Prepare accepted sources and one scoped staged condition.

    settings=None configures a fresh active owner before source capture.
    Supplied settings={owner,user} skips initial settings/key/transport writes;
    enabled=None also skips the final WA settings save. Browser/HTTP callers
    use both with collect=False, then select/save settings through their UI or
    actual Auth RPC and drive wa.drain. Their fixture still uses public policy,
    source and staged-analysis facades and may not claim those as UI actions.
    """
    s = _settings(cur, wa, subject) if settings is None else dict(settings)
    source_subject = str(subject or s['owner'])
    wa.b.api.admin(cur)
    active = cur.execute('select id::text from erp.app_users where auth_user_id=%s and is_active', (s['owner'],)).fetchone()
    assert active is not None and active[0] == str(s['user']), 'OW01_SETTINGS_OWNER_MUST_BE_ACTIVE_BEFORE_CAPTURE'
    f = _source(cur, today, wa, mode, issue80)
    return _stage(cur, today, wa, f, s, source_subject, policy=policy, policy_enabled=policy_enabled, enabled=enabled,
        threshold=threshold, local_quiet=local_quiet, collect=collect)


def stage_existing(cur, today, wa, x, *, subject=None, collect=True):
    """New immutable staged run; retain the current Native fixture and policy."""
    return _stage(cur, today, wa, deepcopy(x['f']), x['s'], str(subject or x['source_subject']),
        policy=False, policy_enabled=True, enabled=None, threshold='1', local_quiet=False, collect=collect)


def successor(cur, x, qty='3'):
    """Real BF writer; caller owns commit/rollback and its genuine Native locks."""
    assert x['f']['category'] is not None
    return _json_version(material.bom(cur, x['f']['root'], analysis, x['f']['category'], qty=str(qty)))


def original_unchanged(cur, x):
    original, pages, _ = staged.fetch(cur, x['r']['run'], x['source_subject'])
    assert original == x['document'] and pages['identity_hash'] == x['r']['identity'], 'OW01_ORIGINAL_REWRITTEN'
    return True


def assert_unknown(m):
    for key in UNKNOWN_FACTS:
        assert m[key]['state'] == 'UNKNOWN' and 'value' not in m[key], (key, m[key])


def assert_detail(a, x, reason=REVIEW_REASON, gross='186'):
    """Exact twenty raw wire keys; no production parser/renderer as oracle."""
    d = a['detail']
    assert set(d) == DETAIL_KEYS and a['party_names'] == [], d
    if 'subject_key' in a:
        assert a['subject_key'] == x['key'], a['subject_key']
    assert (d['run_id'], d['target_key'], d['category_key']) == (
        x['r']['run'], x['r']['target'], x['m']['material_key'] or 'UNKNOWN_BOM'), d
    assert d['label'] == x['c']['label'] and d['data_as_of'] == x['c']['data_as_of'], d
    assert datetime.fromisoformat(d['checked_at'].replace('Z', '+00:00')) >= datetime.fromisoformat(d['data_as_of'].replace('Z', '+00:00'))
    assert (d['state'], d['verdict'], d['threshold_status'], d['reason']) == (
        'DATA_REVIEW', 'REVIEW_REQUIRED_NOW', 'NOT_EVALUATED_UNKNOWN', reason), d
    assert d['gross_qty'] == x['m']['gross'].get('value') and d['unit'] == x['m']['gross']['unit'], d
    if gross is None:
        assert d['gross_state'] == 'UNKNOWN' and d['gross_qty'] is None, d
    else:
        assert d['gross_state'] == 'ASSUMED' and D(d['gross_qty']) == D(gross), d
    expected_category = None if x['m']['material_key'] is None else x['f']['category']['category_name']
    assert d['category_name'] == expected_category, d
    for state, value in (('installed_state', 'installed_proven'), ('unused_allocated_state', 'unused_allocated_proven'),
                         ('additional_external_state', 'additional_external')):
        assert d[state] == 'UNKNOWN' and d[value] is None, d
    return d


def review(cur, wa, x, *, eligibility='REVIEW_NOTICE_ELIGIBLE', reason=REVIEW_REASON, gross='186'):
    v = wa.remv2.recheck(cur, x['r']['run'], x['key'], x['source_subject'])
    assert v['verdict'] == 'REVIEW_REQUIRED_NOW' and v['reason'] == reason, v
    assert v['numbers']['wa_notice_eligibility'] == eligibility and v['numbers']['threshold_status'] == 'NOT_EVALUATED_UNKNOWN', v
    d = assert_detail(dict(detail=v['numbers']['accessory_detail'], party_names=[], subject_key=v['condition_key']), x, reason, gross)
    assert d['checked_at'] == v['checked_at'] and d['data_as_of'] == v['data_as_of']
    return v


def actor_recheck(cur, wa, x):
    """Record the genuine authenticated execution context around the public RPC.

    Privileged source setup is recorded separately. No role is altered, and
    this is an authenticated SQL call, not a claim of real Auth/HTTP transport.
    """
    wa.b.api.admin(cur)
    prior = cur.execute('show statement_timeout').fetchone()[0]
    wa.auth.actor(cur, x['source_subject'])
    cur.execute("select set_config('statement_timeout','8s',true)")
    sql = "select jsonb_build_object('current_user',current_user,'session_user',session_user,'is_superuser',current_setting('is_superuser')," \
        "'claims',current_setting('request.jwt.claims',true)::jsonb)"
    before = cur.execute(sql).fetchone()[0]
    v = cur.execute('select public.erp_cp7_recheck_reminder_v2(%s,%s)', (x['r']['run'], x['key'])).fetchone()[0]
    after = cur.execute(sql).fetchone()[0]
    wa.b.api.admin(cur)
    cur.execute('select set_config(\'statement_timeout\',%s,true)', (prior,))
    assert before == after and before['current_user'] == before['session_user'] == 'authenticated', (before, after)
    assert before['is_superuser'] == 'off' and before['claims']['sub'] == x['source_subject'] and before['claims']['role'] == 'authenticated', before
    assert v['contract_version'] == 'cp7.reminder-recheck.v2' and v['recorded'] is False and v['sent'] is False
    assert v['verdict'] == 'REVIEW_REQUIRED_NOW' and v['numbers']['wa_notice_eligibility'] == 'REVIEW_NOTICE_ELIGIBLE', v
    assert_detail(dict(detail=v['numbers']['accessory_detail'], party_names=[]), x)
    return before


def assert_notice_text(body, x, gross='186'):
    """Independent copy requirements, separate from production formatting."""
    # WA's small-line contract intentionally uses a twenty-character label;
    # the UI keeps the full label. This is a literal oracle, not item_line().
    line = x['c']['label'][:20] + ': perlu diperiksa; jumlah tambahan belum diketahui'
    if gross is not None:
        line += '; BOM (perkiraan) ' + format(D(gross).normalize(), 'f') + ' ' + x['m']['gross']['unit']
    assert line in body, (line, body)
    lowered = body.lower()
    assert all(word not in lowered for word in ('perlu dibeli', 'perlu beli', 'tambahan 0', 'tambahan 186', 'ambang pengingat')), body


def sent(cur, wa, x, *, reason=REVIEW_REASON, gross='186'):
    before = wa.last_request(cur)
    result = wa.tick(cur, 'send_tick')
    assert result['outcome'] == 'SENT', result
    message = wa.dispatch(cur, result['dispatch_id'])
    requests = wa.queued(cur, before)
    assert len(requests) == 1 and requests[0]['base'] == wa.FAKE and requests[0]['phone'] == wa.PHONE, len(requests)
    assert requests[0]['text'] == message['body'] and 0 < len(message['body']) <= 1000
    assert_notice_text(message['body'], x, gross)
    assert_detail(wa.alerts(cur, RULE)[x['key']], x, reason, gross)
    # Do not return the decoded request: it contains the disposable fake key.
    return message


def _held(cur, wa, x, verdict, reason=None):
    v = wa.remv2.recheck(cur, x['r']['run'], x['key'], x['source_subject'])
    assert v['verdict'] == verdict and v['numbers']['wa_notice_eligibility'] == 'SOURCE_REVIEW_REQUIRED', v
    assert v['numbers']['accessory_detail'] is None, v
    if reason is not None:
        assert v['reason'] == reason, v
    before = wa.last_request(cur)
    result = wa.tick(cur, 'send_tick')
    assert wa.queued(cur, before) == [] and result['outcome'] != 'SENT', result
    return v, result


def _denied(cur, wa, op):
    state, message = wa.refusal(cur, op)
    assert state == '42501', (state, message)
    return message


def cases(cur, today, wa):
    def unknown_forwarded():
        x = prepared(cur, today, wa)
        assert x['m']['gross']['state'] == 'ASSUMED' and D(x['m']['gross']['value']) == D(93) * 2 == 186
        assert_unknown(x['m'])
        assert {'erp.accessory_bom_versions', 'erp.accessory_bom_items', 'erp.accessory_categories'} <= {r['kind'] for r in x['m']['gross']['refs']}
        assert x['c']['state'] == 'DATA_REVIEW' and x['c']['eligibility'] == 'SOURCE_REVIEW_REQUIRED', x['c']
        assert 'CONDITION_SET_STEP' in x['ticks'], x['ticks']
        review(cur, wa, x)
        authenticated_context = actor_recheck(cur, wa, x)
        a = wa.alerts(cur, RULE)[x['key']]
        assert_detail(a, x)
        assert [o['state'] for o in wa.outbox(cur, a['id'])] == ['PENDING']
        message = sent(cur, wa, x)
        assert wa.remv2.claims_of(cur, x['key']) == wa.remv2.rechecks_of(cur, x['key']) == 0
        assert original_unchanged(cur, x) and wa.b.boundary.snapshot(cur) == x['boundary']
        return dict(status='PASS', conditional_gap='93', Native_BOM_per_FG='2', gross_ASSUMED='186',
            installed_unused_external='UNKNOWN', raw_detail_keys=20, queued_genuine_pg_net_request=True,
            provider_delivery_proven_here=False, body=message['body'], no_local_claim=True, Native_boundary_unchanged=True,
            execution_context=x['execution_context'], authenticated_public_recheck=authenticated_context,
            auth_transport='AUTHENTICATED_SQL_ACTOR; actual Auth/PostgREST belongs to transport cases')

    def missing_empty():
        answers = {}
        with isolated(cur, wa):
            x = prepared(cur, today, wa, mode='MISSING')
            assert x['m']['material_key'] is None and x['m']['gross']['state'] == 'UNKNOWN'
            assert_unknown(x['m'])
            review(cur, wa, x, reason='BOM_NOT_RECORDED', gross=None)
            sent(cur, wa, x, reason='BOM_NOT_RECORDED', gross=None)
            assert wa.b.boundary.snapshot(cur) == x['boundary']
            answers['missing'] = 'BOM_NOT_RECORDED; gross/external UNKNOWN; source review forwarded'
        with isolated(cur, wa):
            x = prepared(cur, today, wa, mode='EMPTY')
            assert x['m']['material_key'] == 'NO_ACCESSORY:' + x['f']['root']
            assert all(x['m'][k]['state'] == 'KNOWN' and D(x['m'][k]['value']) == 0 for k in ('gross',) + UNKNOWN_FACTS)
            assert all(any(r['kind'] == 'erp.accessory_bom_versions' and r['id'] == x['f']['bom']['id'] for r in x['m'][k]['refs'])
                for k in ('gross',) + UNKNOWN_FACTS)
            assert x['c']['state'] == 'RESOLVED'
            _held(cur, wa, x, 'RESOLVED_NOW', 'KNOWN_ZERO_ACCESSORY_NEED')
            assert x['key'] not in wa.alerts(cur, RULE)
            assert cur.execute('select count(*) from cp7_alert_native.outbox where alert_kind=%s', (RULE,)).fetchone()[0] == 0
            assert wa.b.boundary.snapshot(cur) == x['boundary']
            answers['empty'] = 'explicit Native empty BOM -> four KNOWN zeros; no review or WA'
        return dict(status='PASS', distinctions=answers, no_UNKNOWN_to_zero=True, isolated_selected_profile_fixtures=True)

    def bom_successor():
        with isolated(cur, wa):
            x = prepared(cur, today, wa)
            a = wa.alerts(cur, RULE)[x['key']]
            new = successor(cur, x, '3')
            assert new['id'] != x['f']['bom']['id']
            _held(cur, wa, x, 'CHANGED_REVIEW_REQUIRED', 'ACCESSORY_SOURCE_CHANGED_AFTER_SNAPSHOT')
            old_outbox = wa.outbox(cur, a['id'])
            assert len(old_outbox) == 1 and old_outbox[0]['state'] == 'PENDING' and old_outbox[0]['attempts'] == 0, old_outbox
            assert old_outbox[0]['reason'] == 'RECHECK_ACCESSORY_SOURCE_CHANGED_AFTER_SNAPSHOT', old_outbox
            held = wa.alerts(cur, RULE)[x['key']]
            assert held['id'] == a['id'] and held['episode'] == a['episode']
            assert original_unchanged(cur, x)
            old_detail = cur.execute('select detail from cp7_alert_native.alerts where id=%s', (a['id'],)).fetchone()[0]
            assert D(old_detail['gross_qty']) == 186
            material.review_schedule(cur, today, analysis)
            fresh = stage_existing(cur, today, wa, x)
            fresh['f']['bom'] = new
            assert fresh['r']['run'] != x['r']['run'] and D(fresh['m']['gross']['value']) == D(93) * 3 == 279
            assert any(r['kind'] == 'erp.accessory_bom_versions' and r['id'] == new['id'] for r in fresh['m']['gross']['refs'])
            review(cur, wa, fresh, gross='279')
            refreshed = wa.alerts(cur, RULE)[fresh['key']]
            assert refreshed['id'] == a['id'] and refreshed['episode'] == a['episode']
            refreshed_outbox = wa.outbox(cur, a['id'])
            assert len(refreshed_outbox) == 1 and refreshed_outbox[0]['id'] == old_outbox[0]['id'] and refreshed_outbox[0]['attempts'] == 0
            sent(cur, wa, fresh, gross='279')
            assert original_unchanged(cur, x) and wa.b.boundary.snapshot(cur) == fresh['boundary']
        invalid = {}
        for mode, reason in (('INACTIVE', 'CATEGORY_UNAVAILABLE'), ('OVERLAP', 'BOM_AMBIGUOUS')):
            with isolated(cur, wa):
                x = prepared(cur, today, wa, mode=mode)
                assert x['m']['gross']['state'] == 'UNKNOWN'
                assert_unknown(x['m'])
                review(cur, wa, x, reason=reason, gross=None)
                sent(cur, wa, x, reason=reason, gross=None)
                assert wa.b.boundary.snapshot(cur) == x['boundary']
                invalid[mode] = reason
        return dict(status='PASS', real_Native_BF_successor_holds_old_notice=True, original186_fresh279=True,
            shared_master_schedule_rebound_through_public_CAS=True, complete_invalid_source_review=invalid,
            invalid_source_fixture_kind='ADMINISTRATIVE_INVALID_MASTER_FIXTURE')

    def current_permissions():
        x = prepared(cur, today, wa)
        foreign = wa.master.role_actor(cur, 'OWNER')
        _denied(cur, wa, lambda: wa.remv2.recheck(cur, x['r']['run'], x['key'], foreign))
        wa.b.api.admin(cur)
        role = cur.execute("select id from erp.app_roles where role_code='STAFF'").fetchone()[0]
        cur.execute('update erp.app_roles set is_active=true where id=%s', (role,))
        subject = wa.master.role_actor(cur, 'STAFF')
        for permission in sorted(wa.PLANNING):
            cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s) on conflict do nothing', (role, permission))
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.accessory.view'", (role,))
        staff = stage_existing(cur, today, wa, x, subject=subject, collect=False)
        review(cur, wa, staff)
        before_accessory = wa.rpc(cur, 'erp_cp7_get_alerts_v1', (json.dumps({}),), subject)
        assert RULE in {k['kind'] for k in before_accessory['kinds']} and 'ACCESSORY_AT_REORDER_POINT' not in {k['kind'] for k in before_accessory['kinds']}
        wa.b.api.admin(cur)
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key) values(%s,'warehouse.accessory.view') on conflict do nothing", (role,))
        full = wa.rpc(cur, 'erp_cp7_get_alerts_v1', (json.dumps({}),), subject)
        assert {RULE, 'ACCESSORY_AT_REORDER_POINT'} <= {k['kind'] for k in full['kinds']}
        assert all(r['wa'] is None for r in full['rows'])
        denied = []
        for permission in sorted(wa.PLANNING):
            with isolated(cur, wa):
                cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s', (role, permission))
                _denied(cur, wa, lambda: wa.remv2.recheck(cur, staff['r']['run'], staff['key'], subject))
                current = wa.rpc(cur, 'erp_cp7_get_alerts_v1', (json.dumps({}),), subject)
                kinds = {k['kind'] for k in current['kinds']}
                assert RULE not in kinds and 'ACCESSORY_AT_REORDER_POINT' in kinds, (permission, kinds)
                denied.append(permission)
        with isolated(cur, wa):
            cur.execute('update erp.app_roles set is_active=false where id=%s', (role,))
            _denied(cur, wa, lambda: wa.remv2.recheck(cur, staff['r']['run'], staff['key'], subject))
        # Private capability is not a new application-facing ERP table reader.
        wa.b.api.admin(cur)
        sig = cur.execute("select p.oid::regprocedure::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
            "where n.nspname='cp7_reminder_native' and p.proname='accessory_target_now'").fetchone()
        assert sig is not None and cur.execute("select has_function_privilege('cp7_reminder',%s,'EXECUTE')", (sig[0],)).fetchone()[0]
        for who in ('anon', 'authenticated', 'service_role', 'cp7_alert'):
            assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')', (who, sig[0])).fetchone()[0], who
        for who in ('cp7_capture', 'cp7_reminder', 'cp7_alert'):
            for table in ('erp.accessory_bom_versions', 'erp.accessory_bom_items', 'erp.accessory_categories'):
                assert not cur.execute('select has_table_privilege(%s,%s,\'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER\')', (who, table)).fetchone()[0], (who, table)
        with isolated(cur, wa):
            # ADMINISTRATIVE_PRIVATE_READER_FAULT: inaccessible != missing BOM.
            pending = wa.alerts(cur, RULE)[x['key']]
            pending_outbox = wa.outbox(cur, pending['id'])
            cur.execute('revoke select on erp.accessory_bom_items from cp7_capture')
            assert not cur.execute("select has_table_privilege('cp7_capture','erp.accessory_bom_items','SELECT')").fetchone()[0]
            _denied(cur, wa, lambda: wa.remv2.recheck(cur, x['r']['run'], x['key'], x['source_subject']))
            before = wa.last_request(cur)
            result = wa.tick(cur, 'send_tick')
            assert wa.queued(cur, before) == [] and result['outcome'] != 'SENT', result
            a = wa.alerts(cur, RULE)[x['key']]
            fault_outbox = wa.outbox(cur, a['id'])
            assert a['id'] == pending['id'] and a['episode'] == pending['episode']
            assert len(fault_outbox) == 1 and fault_outbox[0]['id'] == pending_outbox[0]['id']
            assert fault_outbox[0]['state'] == 'PENDING' and fault_outbox[0]['attempts'] == 0
        # The seed owner remains active; retiring this fixture owner is legal.
        wa.b.api.admin(cur)
        cur.execute('update erp.app_users set is_active=false where id=%s', (x['s']['user'],))
        boundary = wa.b.boundary.snapshot(cur)
        _denied(cur, wa, lambda: wa.remv2.recheck(cur, x['r']['run'], x['key'], x['source_subject']))
        before = wa.last_request(cur)
        result = wa.tick(cur, 'send_tick')
        assert result['outcome'] == 'OWNER_ACCESS_DENIED' and wa.queued(cur, before) == [], result
        assert all(o['attempts'] == 0 for o in wa.outbox(cur, wa.alerts(cur, RULE)[x['key']]['id']))
        assert wa.b.boundary.snapshot(cur) == boundary
        return dict(status='PASS', current_source_permissions=denied, foreign_and_inactive_denied=True,
            plan_need_permissions_separate_from_stock_minimum=True, private_reader_fault_not_missing_BOM=True,
            current_retired_owner_no_attempt=True, no_new_Native_writer_privilege=True)

    def issue_not_installed_resolved():
        with isolated(cur, wa):
            x = prepared(cur, today, wa, issue80=True)
            assert x['f']['issue']['posted_quantity'] == '80' and x['f']['issue']['warehouse_remaining'] == '0'
            assert D(x['m']['gross']['value']) == 186
            assert_unknown(x['m'])
            review(cur, wa, x)
            sent(cur, wa, x)
            assert wa.b.boundary.snapshot(cur) == x['boundary']
        with isolated(cur, wa):
            x = prepared(cur, today, wa)
            a = wa.alerts(cur, RULE)[x['key']]
            wa.planv2.found_fg(cur, dict(root=x['f']['root']), 1)
            partial, _ = _held(cur, wa, x, 'CHANGED_REVIEW_REQUIRED', 'PRODUCTION_NEED_FELL_AFTER_SNAPSHOT')
            assert D(partial['numbers']['need_now_pcs']) == 92
            wa.planv2.found_fg(cur, dict(root=x['f']['root']), 92)
            boundary = wa.b.boundary.snapshot(cur)
            resolved, _ = _held(cur, wa, x, 'RESOLVED_NOW', 'FINISHED_STOCK_AND_WIP_COVER_THE_NEED_NOW')
            assert D(resolved['numbers']['need_now_pcs']) == 0
            assert x['key'] not in wa.alerts(cur, RULE)
            assert all(o['attempts'] == 0 and o['state'] == 'RESOLVED_BEFORE_SEND' for o in wa.outbox(cur, a['id']))
            assert original_unchanged(cur, x) and D(x['m']['gross']['value']) == 186
            assert_unknown(x['m'])
            assert wa.b.boundary.snapshot(cur) == boundary
        return dict(status='PASS', accepted_Native_receipt80_issue80=True, issue_not_installation_or_allocated_unused=True,
            stock0_not_external0_or20=True, partial_FG1_holds_old_gross=True, Native_FG93_resolves_target=True,
            original_gross186_and_UNKNOWN_coverage_immutable=True)

    def policy_replay_dedup():
        checks = {}
        for state in ('UNCONFIGURED', 'DISABLED'):
            with isolated(cur, wa):
                x = prepared(cur, today, wa, policy=state != 'UNCONFIGURED', policy_enabled=False)
                review(cur, wa, x, eligibility=state)
                before = wa.last_request(cur)
                result = wa.tick(cur, 'send_tick')
                assert result['outcome'] != 'SENT' and wa.queued(cur, before) == []
                assert x['key'] not in wa.alerts(cur, RULE)
                checks[state] = 'no WA review without explicit configured enabled policy'
        with isolated(cur, wa):
            x = prepared(cur, today, wa, threshold='999999', local_quiet=True)
            v = review(cur, wa, x)
            assert v['policy_binding']['policy']['config']['threshold_value'] == '999999'
            timing = cur.execute('select cp7_reminder_native.policy_timing(%s::jsonb,clock_timestamp(),null)',
                (json.dumps(x['policy_payload']['config']),)).fetchone()[0]
            assert timing['status'] == 'QUIET', timing
            assert x['c']['eligibility'] == 'SOURCE_REVIEW_REQUIRED'
            binding, _ = wa.remv2.bind(cur, x['r'], rules_=(RULE,), subject=x['source_subject'])
            state, message = wa.refusal(cur, lambda: wa.remv2.claim(cur, x['r'], x['c'], binding, subject=x['source_subject']))
            assert (state, message) == ('40001', 'CP7_REMINDER_V2_NOT_ACTIVE_IN_SNAPSHOT'), (state, message)
            # Current source review is not a claim that this numeric threshold
            # is reached, nor may local quiet become a WA quiet preference.
            for _ in range(2):
                wa.tick(cur, 'analysis_tick')
            a = wa.alerts(cur, RULE)[x['key']]
            assert len(wa.outbox(cur, a['id'])) == 1
            first = sent(cur, wa, x)
            # SYNTHETIC_PROVIDER_ANSWER is only for this savepoint dedup check.
            wa.answer(cur, first['id'], 200, 'Message queued')
            wa.tick(cur, 'send_tick')
            before = wa.last_request(cur)
            wa.tick(cur, 'send_tick')
            wa.tick(cur, 'analysis_tick')
            assert wa.queued(cur, before) == []
            outbox = wa.outbox(cur, a['id'])
            assert len(outbox) == 1 and outbox[0]['state'] == 'ACCEPTED' and outbox[0]['attempts'] == 1, outbox
            assert wa.remv2.claims_of(cur, x['key']) == wa.remv2.rechecks_of(cur, x['key']) == 0
            # Exact public policy replay/lost reply: cache the full request,
            # repeat it and prove one revision without manufacturing a new one.
            p = policy_payload(cur, wa, x, threshold='999999', local_quiet=True)
            request = str(uuid.uuid4())
            one = wa.remv2.command(cur, 'erp_cp7_save_reminder_policy_v2', p, request, x['source_subject'])
            count = cur.execute('select count(*) from cp7_reminder_native.rule_policies').fetchone()[0]
            again = wa.remv2.command(cur, 'erp_cp7_save_reminder_policy_v2', p, request, x['source_subject'])
            assert again['result'] == one['result'] and cur.execute('select count(*) from cp7_reminder_native.rule_policies').fetchone()[0] == count
            changed = deepcopy(p)
            changed['reason'] += '; changed body'
            assert wa.refusal(cur, lambda: wa.remv2.command(cur, 'erp_cp7_save_reminder_policy_v2', changed, request, x['source_subject']))[1] == 'CP7_REMINDER_REQUEST_CHANGED'
            checks['LOCAL_QUIET'] = 'local claim still refused; WA own quiet=False delivers source review once'
            checks['THRESHOLD'] = '999999 is not evaluated against UNKNOWN external quantity'
        with isolated(cur, wa):
            x = prepared(cur, today, wa)
            # A fresh pending notice is necessary: repeat/pacing cannot explain
            # this hold because there has been no first dispatch in this subcase.
            q = quiet_window(cur, wa)
            wa.save(cur, x['s']['owner'], enabled=True, quiet_enabled=True, quiet_start=q['starts_at'], quiet_end=q['ends_at'], **WA_VALUES)
            before = wa.last_request(cur)
            result = wa.tick(cur, 'send_tick')
            assert result['outcome'] == 'HELD_QUIET' and wa.queued(cur, before) == [], result
            a = wa.alerts(cur, RULE)[x['key']]
            assert [o['state'] for o in wa.outbox(cur, a['id'])] == ['HELD_QUIET']
            wa.save(cur, x['s']['owner'], enabled=True, quiet_enabled=False, **WA_VALUES)
            save_policy(cur, wa, x, enabled=False)
            review(cur, wa, x, eligibility='DISABLED')
            before = wa.last_request(cur)
            result = wa.tick(cur, 'send_tick')
            assert result['outcome'] != 'SENT' and wa.queued(cur, before) == []
            held = wa.alerts(cur, RULE)[x['key']]
            held_outbox = wa.outbox(cur, held['id'])
            assert held['id'] == a['id'] and held['episode'] == a['episode']
            assert len(held_outbox) == 1 and held_outbox[0]['attempts'] == 0 and held_outbox[0]['state'] in ('PENDING', 'HELD_QUIET')
            checks['CURRENT_DISABLED'] = 'current disabled policy holds a previously queued notice before send'
        return dict(status='PASS', checks=checks, same_UUID_one_policy_revision=True,
            changed_UUID_body_refused=True, one_subject_episode_round_attempt=True,
            local_UNKNOWN_claim_remains_refused=True, no_fabricated_local_cooldown_history=True,
            provider_answer_fixture='SYNTHETIC_PROVIDER_ANSWER only; actual fake provider is a separate race case')

    result = list(zip(NATIVE_IDS, (unknown_forwarded, missing_empty, bom_successor, current_permissions,
        issue_not_installed_resolved, policy_replay_dedup)))
    assert len(result) == 6 and [key for key, _ in result] == NATIVE_IDS
    return result

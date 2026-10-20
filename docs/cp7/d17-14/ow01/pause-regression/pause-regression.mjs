#!/usr/bin/env node
// SYNTHETIC_MODULE_SELECTION_ONLY. Executes extracted product SQL in PGlite.
// No Native installation/Auth/ACL/race/pg_net/provider/WhatsApp proof is made.
import assert from 'node:assert/strict'
import { readFile, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { resolve } from 'node:path'
const args = process.argv.slice(2)
const option = (key, fallback) => args.includes(key) ? args[args.indexOf(key) + 1] : fallback
const sourcePath = resolve(option('--source', 'scripts/cp7-src/alerts/alerts.sql'))
const firstOnly = args.includes('--first-retention-only')
const report = { classification: 'SYNTHETIC_PGLITE_ACTUAL_SQL_MODULE_SELECTION_ONLY', source_path: sourcePath,
  proves_native_source: false, proves_real_auth_or_acl: false, proves_concurrency: false,
  proves_pg_net_or_provider: false, proves_whatsapp_delivery: false,
  stubs: ['owner_access', 'vault_key_present'], fixtures: 'synthetic alert/settings/outbox rows; accepted/unknown states are not provider receipts',
  cases: [], status: 'INCOMPLETE' }
const hash = x => createHash('sha256').update(x).digest('hex')
const id = n => `c0000000-0000-4000-8000-${String(n).padStart(12, '0')}`
let db, currentCase
try {
  const { PGlite } = await import(process.env.PGLITE_MODULE ?? '@electric-sql/pglite')
  const source = await readFile(sourcePath, 'utf8')
  report.source_sha256 = hash(source)
  const fn = (name, required = true) => {
    const start = source.indexOf(`create function cp7_alert_native.${name}(`)
    if (start < 0 && !required) return ''
    assert.notEqual(start, -1, `actual function missing: ${name}`)
    const end = source.indexOf('$$;', source.indexOf('as $$', start))
    assert.notEqual(end, -1, `actual function unterminated: ${name}`)
    return source.slice(start, end + 3)
  }
  const table = name => {
    const start = source.indexOf(`create table cp7_alert_native.${name}(`)
    assert.notEqual(start, -1, `actual table missing: ${name}`)
    return source.slice(start, source.indexOf(';\n', start) + 1)
  }
  const capture = (rx, text, label) => {
    const found = text.match(rx)
    assert.ok(found, `actual SQL extraction changed: ${label}`)
    return found[1]
  }
  const send = fn('send_tick')
  const offUpdates = capture(/if off is not null then\s*([\s\S]*?)\s*return cp7_alert_native\.record_tick\('SEND'/, send, 'off updates')
  const kindStart = send.indexOf(" update cp7_alert_native.outbox set state='KIND_OFF'")
  const kindEnd = send.indexOf(' if cp7_alert_native.in_quiet(', kindStart)
  assert.ok(kindStart >= 0 && kindEnd > kindStart, 'actual kind/pause block changed')
  const kindUpdates = send.slice(kindStart, kindEnd)
  const checkKinds = capture(/(check_kinds:=case when slot is not null then s\.kinds else[\s\S]*?end;)/, send, 'check kinds')
  const analysisSelection = capture(/an:=cp7_alert_native\.analysis_recheck\(case when slot is not null then\s*array\(([\s\S]*?)\)end,\s*t0\+interval'5 seconds'/, send, 'analysis selection')
  const digestIds = capture(/^([\s\S]*?)\)\s*else array\(/, analysisSelection, 'digest ids')
  const instantIds = capture(/\)\s*else array\(([\s\S]*)$/, analysisSelection, 'instant ids')
  const pendingSql = capture(/(select array_agg\(o\.id order by o\.id\)into pend from cp7_alert_native\.outbox o[\s\S]*?);/, send, 'final pending') + ';'
  const functions = Object.fromEntries(['guard_append_only', 'guard_alert', 'queue_alert', 'guard_outbox', 'current_settings', 'ts_key',
    'jwt', 'uid', 'require_owner', 'defaults', 'settings_json', 'wa_settings_save', 'apply_one', 'queue_repeats']
    .map(name => [name, fn(name)]))
  const eligible = fn('waiting_eligible', false)
  if (eligible) functions.waiting_eligible = eligible
  report.actual_function_sha256 = Object.fromEntries(Object.entries(functions).map(([key, text]) => [key, hash(text)]))
  report.actual_fragment_sha256 = Object.fromEntries(Object.entries({ offUpdates, kindUpdates, checkKinds, digestIds, instantIds, pendingSql })
    .map(([key, text]) => [key, hash(text)]))
  db = new PGlite()
  await db.exec(`create schema cp7_alert_native; create schema proof; create schema erp;
    create table erp.manual_reminders(id uuid,status text,due_at timestamptz);
    ${['settings', 'alerts', 'dispatches', 'outbox'].map(table).join('\n')}
    create unique index alerts_one_open on cp7_alert_native.alerts(kind,subject_key)where state='OPEN';
    create function cp7_alert_native.owner_access(p_user uuid default null)returns jsonb language sql stable as $$
      select jsonb_build_object('allowed',true,'profile',jsonb_build_object('id','${id(9002)}','role_code','OWNER'))$$;
    create function cp7_alert_native.vault_key_present()returns boolean language sql stable as $$select true$$;
    ${Object.values(functions).join('\n')}
    create trigger settings_append_only before update or delete on cp7_alert_native.settings for each row execute function cp7_alert_native.guard_append_only();
    create trigger alerts_guard before update or delete on cp7_alert_native.alerts for each row execute function cp7_alert_native.guard_alert();
    create trigger alerts_queue after insert on cp7_alert_native.alerts for each row execute function cp7_alert_native.queue_alert();
    create trigger outbox_guard before update or delete on cp7_alert_native.outbox for each row execute function cp7_alert_native.guard_outbox();
    create function proof.off_updates(p_off text,p_at timestamptz)returns void language plpgsql as $proof$
      declare off text:=p_off;t0 timestamptz:=p_at;begin ${offUpdates} end $proof$;
    create function proof.kind_updates(p_at timestamptz)returns void language plpgsql as $proof$
      declare s cp7_alert_native.settings:=cp7_alert_native.current_settings();t0 timestamptz:=p_at;begin ${kindUpdates} end $proof$;
    create function proof.check_kinds(p_at timestamptz,p_digest boolean)returns text[] language plpgsql as $proof$
      declare s cp7_alert_native.settings:=cp7_alert_native.current_settings();t0 timestamptz:=p_at;
      slot timestamptz:=case when p_digest then p_at end;check_kinds text[];
      begin ${checkKinds} return check_kinds;end $proof$;
    create function proof.analysis_ids(p_at timestamptz,p_digest boolean)returns uuid[] language plpgsql as $proof$
      declare s cp7_alert_native.settings:=cp7_alert_native.current_settings();t0 timestamptz:=p_at;
      begin if p_digest then return array(${digestIds});else return array(${instantIds});end if;end $proof$;
    create function proof.pending(p_at timestamptz,p_digest boolean,p_ok uuid[],p_failed text[])returns bigint[] language plpgsql as $proof$
      declare s cp7_alert_native.settings:=cp7_alert_native.current_settings();send_at timestamptz:=p_at;
      slot timestamptz:=case when p_digest then p_at end;ok uuid[]:=p_ok;failed text[]:=p_failed;pend bigint[];
      begin ${pendingSql} return pend;end $proof$;`)
  await db.query("select set_config('request.jwt.claims',$1,false)", [JSON.stringify({ sub: id(9001), role: 'authenticated' })])
  const one = async (sql, params = []) => (await db.query(sql, params)).rows[0]
  const at = async () => (await one('select clock_timestamp()::text at')).at
  const out = async ident => (await one('select to_jsonb(o) row from cp7_alert_native.outbox o where id=$1', [ident])).row
  const count = async () => (await one('select count(*)::int n from cp7_alert_native.outbox')).n
  const identity = row => Object.fromEntries(['id', 'item_kind', 'item_id', 'item_episode', 'round', 'queued_at'].map(k => [k, row[k]]))
  let sequence = 0
  async function save(values = {}, request = null, exactPayload = null) {
    const revision = (await one('select coalesce(max(revision),0)::int n from cp7_alert_native.settings')).n
    const payload = exactPayload ?? { expected_revision: revision, enabled: true, phone_e164: '+620000000000', detail: 'DETAILED',
      digest_times: [], kinds: ['ACCESSORY_NEED'], repeat_minutes: 1440, burst_after_per_day: 200, burst_merge_minutes: 30,
      max_items: 20, quiet_enabled: false, quiet_start: '21:00', quiet_end: '06:00', analysis_every_minutes: 0,
      analysis_start: '07:00', analysis_end: '20:00', ...values }
    const key = request ?? id(10000 + ++sequence)
    const result = (await one('select cp7_alert_native.wa_settings_save($1::jsonb,$2::uuid) result', [JSON.stringify(payload), key])).result
    return { payload, key, result }
  }
  async function open(kind = 'ACCESSORY_NEED', detail = {}) {
    const subject = `SYNTHETIC:${kind}:${++sequence}`
    const payload = { subject_key: subject, title: `Synthetic ${subject}`, detail: { run_id: id(9003), ...detail }, party_names: [] }
    assert.equal((await one('select cp7_alert_native.apply_one($1,$2::jsonb) result', [kind, JSON.stringify(payload)])).result, 'OPENED')
    return await one('select a.id alert_id,o.id outbox_id from cp7_alert_native.alerts a join cp7_alert_native.outbox o on o.item_id=a.id where a.subject_key=$1', [subject])
  }
  async function syntheticDispatch(status = 'PROVIDER_ACCEPTED') {
    return (await one(`insert into cp7_alert_native.dispatches(kind,settings_revision,body,body_sha256,status)
      select 'INSTANT',revision,'SYNTHETIC STATE FIXTURE',encode(sha256(convert_to('SYNTHETIC STATE FIXTURE','UTF8')),'hex'),$1
      from cp7_alert_native.current_settings() returning id`, [status])).id
  }
  async function settled(kind, state, minutes = 61) {
    const a = await open(kind)
    // A synthetic inserted history row, not a claimed provider receipt or legal business setup.
    const d = await syntheticDispatch(state === 'UNKNOWN' ? 'UNKNOWN' : state === 'DISPATCHED' ? 'QUEUED' : 'PROVIDER_ACCEPTED')
    await db.query(`update cp7_alert_native.outbox set state='DISPATCHED',attempts=attempts+1,dispatch_id=$2 where id=$1`, [a.outbox_id, d])
    if (state !== 'DISPATCHED') await db.query(`update cp7_alert_native.outbox set state=$2,settled_at=clock_timestamp()-$3*interval'1 minute' where id=$1`, [a.outbox_id, state, minutes])
    return a
  }
  async function pending(now, digest, ok = [], failed = []) {
    return (await one('select proof.pending($1,$2,$3::uuid[],$4::text[]) ids', [now, digest, ok, failed])).ids ?? []
  }
  async function analysisIds(now, digest = false) {
    return (await one('select proof.analysis_ids($1,$2) ids', [now, digest])).ids ?? []
  }
  const numericIds = xs => xs.map(String).sort((a, b) => Number(a) - Number(b))
  const sameIds = (actual, expected, label) => assert.deepEqual(numericIds(actual), numericIds(expected), label)
  async function refusal(sql, params, message) {
    await db.exec('savepoint expected_refusal')
    let error
    try { await db.query(sql, params) } catch (e) { error = e }
    await db.exec('rollback to savepoint expected_refusal;release savepoint expected_refusal')
    assert.ok(error, `expected refusal: ${message}`)
    assert.ok(String(error.message).includes(message), `different refusal: ${error?.message}`)
  }
  async function test(name, body) {
    currentCase = { name, status: 'RUNNING' }; report.cases.push(currentCase)
    await db.exec('begin')
    try { await body();currentCase.status = 'PASS' }
    catch (error) { currentCase.status = 'FAIL';currentCase.error = error.message;throw error }
    finally { await db.exec('rollback') }
  }

  await test('FIRST_RETENTION_WA_OFF_THEN_EXPLICIT_ENABLE_SAME_ROUND_ZERO', async () => {
    await save({ enabled: false })
    const a = await open(); const before = await out(a.outbox_id); const now = await at()
    await db.query('select proof.off_updates($1,$2)', ['WA_OFF', now])
    const paused = await out(a.outbox_id)
    currentCase.observed = { before, paused }
    assert.equal(paused.state, 'PENDING', 'WA_OFF must retain the new accessory first-delivery candidate')
    assert.deepEqual(identity(paused), identity(before));assert.equal(paused.round, 0);assert.equal(paused.attempts, 0)
    assert.equal(paused.dispatch_id, null);assert.equal(paused.settled_at, null);assert.equal(paused.reason, 'WA_OFF')
    await save({ enabled: true });await db.query('select proof.kind_updates($1)', [now])
    assert.equal(await count(), 1);assert.equal((await out(a.outbox_id)).reason, null)
    sameIds(await analysisIds(now), [a.alert_id], 'enabled same round must enter actual source-check selector')
    sameIds(await pending(now, false, [a.alert_id]), [a.outbox_id], 'freshly approved same round must enter actual pending selector')
    const d = await syntheticDispatch('QUEUED')
    await db.query("update cp7_alert_native.outbox set state='DISPATCHED',attempts=attempts+1,dispatch_id=$2 where id=$1", [a.outbox_id, d])
    sameIds(await pending(now, false, [a.alert_id]), [], 'dispatched candidate cannot be selected again')
    currentCase.observed.resumed = await out(a.outbox_id)
  })
  if (!firstOnly) {
    await test('GLOBAL_OFF_REASONS_RETAIN_ACCESSORY_LEGACY_TERMINAL_AND_HISTORY_UNCHANGED', async () => {
      await save({ enabled: false })
      const protectedRows = []
      for (const state of ['ACCEPTED', 'UNKNOWN', 'DISPATCHED']) protectedRows.push(await settled('ACCESSORY_NEED', state))
      for (const state of ['DISABLED', 'KIND_OFF']) {
        const a = await open();await db.query('update cp7_alert_native.outbox set state=$2,reason=$2,settled_at=clock_timestamp()where id=$1', [a.outbox_id, state]);protectedRows.push(a)
      }
      const protectedBefore = await Promise.all(protectedRows.map(a => out(a.outbox_id)))
      const traces = []
      for (const reason of ['NOT_CONFIGURED', 'WA_OFF', 'PHONE_MISSING', 'KEY_MISSING']) {
        const fresh = await open();const quiet = await open();const legacy = await open('FABRIC_NEED');const now = await at()
        await db.query("update cp7_alert_native.outbox set state='HELD_QUIET'where id=$1", [quiet.outbox_id])
        await db.query('select proof.off_updates($1,$2)', [reason, now])
        for (const [a, state] of [[fresh, 'PENDING'], [quiet, 'HELD_QUIET']]) {
          const row = await out(a.outbox_id)
          assert.equal(row.state, state);assert.equal(row.reason, reason);assert.equal(row.attempts, 0);assert.equal(row.round, 0)
          assert.equal(row.settled_at, null);assert.equal(row.dispatch_id, null)
        }
        const old = await out(legacy.outbox_id);assert.equal(old.state, 'DISABLED');assert.equal(old.reason, reason);assert.ok(old.settled_at)
        traces.push({ reason, accessory: (await out(fresh.outbox_id)).state, legacy: old.state })
      }
      await save({ kinds: [] });await db.query('select proof.kind_updates($1)', [await at()])
      assert.deepEqual(await Promise.all(protectedRows.map(a => out(a.outbox_id))), protectedBefore)
      await refusal("update cp7_alert_native.outbox set state='PENDING'where id=$1", [protectedRows.at(-1).outbox_id], 'CP7_ALERT_OUTBOX_TRANSITION')
      currentCase.observed = { traces, accepted_unknown_dispatched_and_old_terminal_unchanged: true }
    })
    await test('KIND_OFF_PAUSE_AND_REFRESH_KEEP_ONE_EPISODE_ROUND_ZERO', async () => {
      await save({ kinds: [] })
      const a = await open();const legacy = await open('FABRIC_NEED');const before = await out(a.outbox_id);const now = await at()
      await db.query('select proof.kind_updates($1)', [now])
      const paused = await out(a.outbox_id)
      assert.equal(paused.state, 'PENDING');assert.equal(paused.reason, 'KIND_OFF');assert.equal(paused.settled_at, null)
      assert.deepEqual(identity(paused), identity(before));assert.equal(paused.attempts, 0)
      assert.equal((await out(legacy.outbox_id)).state, 'KIND_OFF')
      const sourceRow = await one('select subject_key from cp7_alert_native.alerts where id=$1', [a.alert_id])
      assert.equal((await one('select cp7_alert_native.apply_one($1,$2::jsonb) result', ['ACCESSORY_NEED', JSON.stringify({
        subject_key: sourceRow.subject_key, title: 'Synthetic refreshed source', detail: { run_id: id(9004) }, party_names: [] })])).result, 'REFRESHED')
      assert.equal(await count(), 2);assert.deepEqual(identity(await out(a.outbox_id)), identity(before))
      sameIds(await analysisIds(now), []);sameIds(await pending(now, false, [a.alert_id]), [])
      await save({ kinds: ['ACCESSORY_NEED'], repeat_minutes: 0 });await db.query('select proof.kind_updates($1)', [now])
      sameIds(await pending(now, false, [a.alert_id]), [a.outbox_id]);assert.equal((await out(a.outbox_id)).reason, null)
      currentCase.observed = { same_episode_and_round_after_source_refresh: true, legacy_kind_off_terminal: true }
    })
    await test('QUEUED_REPEAT_HONORS_CURRENT_ZERO_NOT_DUE_NOW_DUE_AND_IMMEDIATE_PREDECESSOR', async () => {
      await save({ repeat_minutes: 60, kinds: [] })
      const original = await settled('ACCESSORY_NEED', 'ACCEPTED', 61)
      assert.equal((await one('select cp7_alert_native.queue_repeats(60) n')).n, 1)
      assert.equal((await one('select cp7_alert_native.queue_repeats(60) n')).n, 0)
      const repeat = await one('select id outbox_id from cp7_alert_native.outbox where item_id=$1 and round=1', [original.alert_id])
      const now = await at();await db.query('select proof.kind_updates($1)', [now])
      assert.equal((await out(repeat.outbox_id)).reason, 'KIND_OFF');assert.equal((await out(repeat.outbox_id)).state, 'PENDING')
      const phases = []
      for (const [minutes, eligibleNow, reason] of [[0, false, 'REPEAT_OFF'], [120, false, 'REPEAT_NOT_DUE'], [60, true, null]]) {
        await save({ kinds: ['ACCESSORY_NEED'], repeat_minutes: minutes });await db.query('select proof.kind_updates($1)', [now])
        const row = await out(repeat.outbox_id);assert.equal(row.reason, reason)
        sameIds(await analysisIds(now), eligibleNow ? [original.alert_id] : [])
        sameIds(await pending(now, false, [original.alert_id]), eligibleNow ? [repeat.outbox_id] : [])
        sameIds(await analysisIds(now, true), [original.alert_id], 'digest source scan is independent of instant-repeat setting')
        sameIds(await pending(now, true, [original.alert_id]), [repeat.outbox_id], 'digest may cover a waiting repeat independently')
        phases.push({ repeat_minutes: minutes, instant_eligible: eligibleNow, reason: row.reason })
      }
      // SYNTHETIC_INVALID_LINEAGE: an older accepted round cannot authorize round2 while round1 is pending.
      await db.query(`insert into cp7_alert_native.outbox(item_kind,item_id,item_episode,round,alert_kind)
        select item_kind,item_id,item_episode,2,alert_kind from cp7_alert_native.outbox where id=$1`, [repeat.outbox_id])
      const invalid = await one('select cp7_alert_native.waiting_eligible(o,s,$1,false) eligible from cp7_alert_native.outbox o cross join cp7_alert_native.current_settings()s where o.item_id=$2 and o.round=2', [now, original.alert_id])
      assert.equal(invalid.eligible, false)
      currentCase.observed = { phases, one_queued_repeat_only: true, older_accepted_cannot_replace_immediate_predecessor: true }
    })
    await test('ACTUAL_THREE_SEND_FILTERS_EXCLUDE_OFF_REPEATS_AND_REQUIRE_FRESH_OK', async () => {
      await save({ kinds: ['ACCESSORY_NEED', 'PRODUCTION_GAP', 'AR_DUE', 'MANUAL_REMINDER'], repeat_minutes: 0 })
      const first = await open();const unapproved = await open();const off = await open('FABRIC_NEED');const production = await open('PRODUCTION_GAP');const ar = await open('AR_DUE')
      const accepted = await settled('ACCESSORY_NEED', 'ACCEPTED', 61)
      await db.query(`insert into cp7_alert_native.outbox(item_kind,item_id,item_episode,round,alert_kind)
        select item_kind,item_id,item_episode,1,alert_kind from cp7_alert_native.outbox where id=$1`, [accepted.outbox_id])
      const repeat = await one('select id outbox_id from cp7_alert_native.outbox where item_id=$1 and round=1', [accepted.alert_id])
      const manual = await one(`insert into cp7_alert_native.outbox(item_kind,item_id,item_episode,round,alert_kind)
        values('MANUAL_REMINDER',$1,'synthetic-due-episode',0,'MANUAL_REMINDER') returning id outbox_id`, [id(8000)])
      const now = await at()
      const kinds = (await one('select proof.check_kinds($1,false) kinds', [now])).kinds
      assert.deepEqual(kinds.sort(), ['ACCESSORY_NEED', 'AR_DUE', 'PRODUCTION_GAP'].sort())
      assert.deepEqual((await analysisIds(now)).sort(), [first.alert_id, unapproved.alert_id, production.alert_id].sort())
      sameIds(await pending(now, false, [first.alert_id, production.alert_id], ['AR_DUE']), [first.outbox_id, production.outbox_id, manual.outbox_id])
      sameIds(await pending(now, false, [], ['AR_DUE']), [manual.outbox_id], 'unapproved analysis rows never pass the final actual selector')
      assert.deepEqual((await analysisIds(now, true)).sort(), [first.alert_id, unapproved.alert_id, production.alert_id, accepted.alert_id].sort())
      sameIds(await pending(now, true, [first.alert_id, production.alert_id, accepted.alert_id]),
        [first.outbox_id, production.outbox_id, repeat.outbox_id, ar.outbox_id, manual.outbox_id])
      assert.equal((await one('select cp7_alert_native.waiting_eligible(null::cp7_alert_native.outbox,null::cp7_alert_native.settings,$1,false) eligible', [now])).eligible, false)
      currentCase.observed = { check_kinds: kinds, off_kind_not_checked_or_selected: off.alert_id,
        instant_excludes_current_repeat_zero: true, fresh_ok_and_failed_whitelists_preserved: true, digest_independent: true }
    })
    await test('ACTUAL_SETTINGS_CAS_REPLAY_AND_APPEND_ONLY_GUARDS', async () => {
      const saved = await save({ enabled: false, kinds: [] })
      const replay = await save({}, saved.key, saved.payload)
      assert.equal(replay.result.replay, true)
      assert.equal((await one('select count(*)::int n from cp7_alert_native.settings')).n, 1)
      await refusal('select cp7_alert_native.wa_settings_save($1::jsonb,$2::uuid)', [JSON.stringify({ ...saved.payload, enabled: true }), saved.key], 'CP7_WA_REQUEST_REUSED')
      await refusal('select cp7_alert_native.wa_settings_save($1::jsonb,$2::uuid)', [JSON.stringify(saved.payload), id(6000)], 'CP7_WA_SETTINGS_STALE')
      await refusal('update cp7_alert_native.settings set enabled=true', [], 'CP7_ALERT_APPEND_ONLY')
      currentCase.observed = { exact_request_replay_one_revision: true, changed_request_and_stale_revision_refused: true, append_only_guard_executed: true }
    })
  }
  report.status = 'PASS'
} catch (error) {
  report.status = currentCase?.status === 'FAIL' ? 'FAIL' : 'SETUP_OR_EXTRACTION_ERROR'
  report.first_failure = { case: currentCase?.name ?? null, message: error.message, code: error.code ?? null }
  process.exitCode = 1
} finally {
  if (db) await db.close()
  const output = JSON.stringify(report, null, 2) + '\n'
  const dest = option('--output', null)
  if (dest) await writeFile(dest, output)
  process.stdout.write(output)
}

// SYNTHETIC_SOURCE / MODULE_SELECTION_ONLY: no Native installation, permissions,
// pg_net request, provider receipt, or real WhatsApp delivery is established here.
// The real candidate analysis_recheck and its real helper definitions execute in
// in-memory PostgreSQL. Only the Native source RPC is stubbed. Both ordering and
// final sendable-item SQL are extracted from the actual candidate send_tick.
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
const { PGlite } = await import(process.env.PGLITE_MODULE ?? '@electric-sql/pglite')

const root = process.cwd()
const args = process.argv.slice(2)
const sourcePath = args[args.indexOf('--source') + 1] && args.includes('--source')
  ? args[args.indexOf('--source') + 1] : `${root}/scripts/cp7-src/alerts/alerts.sql`
const legacyOrder = args.includes('--legacy-order-countervariant')
const source = await readFile(sourcePath, 'utf8')
const sha = value => createHash('sha256').update(value).digest('hex')
function definition(name) {
  const start = source.indexOf(`create function cp7_alert_native.${name}(`)
  assert.notEqual(start, -1, `missing actual ${name}`)
  const end = source.indexOf('$$;', source.indexOf('as $$', start))
  assert.notEqual(end, -1, `unterminated actual ${name}`)
  return source.slice(start, end + 3)
}
function actualTable(name) {
  const start = source.indexOf(`create table cp7_alert_native.${name}(`)
  assert.notEqual(start, -1, `missing actual ${name} table`)
  return source.slice(start, source.indexOf(';\n', start) + 1)
}
const actualFunctions = Object.fromEntries(['guard_alert', 'analysis_open', 'analysis_row', 'apply_one', 'resolve_one', 'analysis_recheck']
  .map(name => [name, definition(name)]))
const send = definition('send_tick')
const selection = send.slice(send.indexOf('an:=cp7_alert_native.analysis_recheck(case when slot is not null then'),
  send.indexOf("t0+interval'5 seconds'", send.indexOf('an:=cp7_alert_native.analysis_recheck(case')))
const capture = (regex, text, name) => {
  const found = text.match(regex)
  assert.ok(found, `actual candidate ${name} shape changed; review extraction`)
  return found[1]
}
let digestOrder = capture(/array\((select a2\.id[\s\S]*?)\)\s+else array/, selection, 'digest selection')
let instantOrder = capture(/else array\((select o\.item_id[\s\S]*?)\)end,/, selection, 'instant selection')
if (legacyOrder) {
  // Causal countervariant, explicitly not an exact prior commit. Keep the real
  // current analysis_recheck; ignore its timestamp using the prior sender orders.
  // An unused timestamp cannot prevent starvation, so this must fail the oracle.
  instantOrder = instantOrder.replace(/order by[\s\S]*$/, 'order by min(o.id)')
  digestOrder = digestOrder.replace(/order by[\s\S]*$/, 'order by a2.kind,a2.opened_at,a2.id')
}
const sendableSql = capture(/(select array_agg\(o\.id order by o\.id\)into pend from cp7_alert_native\.outbox o[\s\S]*?);/, send, 'sendable whitelist')
  .replace('into pend ', '')
  .replace("coalesce(failed,'{}')", "coalesce($2::text[],'{}')")
  .replace('any(ok)', 'any($1::uuid[])')
  .replaceAll('cp7_alert_native.waiting_eligible(o,s,send_at,slot is not null)', `cp7_alert_native.waiting_eligible(o,jsonb_populate_record(null::cp7_alert_native.settings,'{"kinds":["ACCESSORY_NEED"],"repeat_minutes":1440}'),clock_timestamp(),false)`)
instantOrder = instantOrder.replaceAll('cp7_alert_native.waiting_eligible(o,s,t0,false)', `cp7_alert_native.waiting_eligible(o,jsonb_populate_record(null::cp7_alert_native.settings,'{"kinds":["ACCESSORY_NEED"],"repeat_minutes":1440}'),clock_timestamp(),false)`)
const id = n => `b0000000-0000-4000-8000-${String(n).padStart(12, '0')}`

async function exercise(mode, cap, expectedTick) {
  const db = new PGlite()
  try {
    await db.exec(`create schema cp7_alert_native; create schema erp; create schema source_stub;
      create table erp.materials(id uuid primary key, material_name text);
      ${actualTable('alerts')}
      ${actualTable('settings')}
      create unique index alerts_one_open on cp7_alert_native.alerts(kind,subject_key)where state='OPEN';
      create table cp7_alert_native.outbox(id bigint primary key,item_kind text,item_id uuid,
        alert_kind text,state text,reason text,item_episode text,round integer default 0,settled_at timestamptz);
      ${definition('waiting_eligible')}
      create table source_stub.outcomes(condition_key text primary key,verdict text,eligibility text,reason text);
      create table source_stub.attempts(seq bigint generated always as identity,condition_key text);
      create function public.erp_cp7_recheck_reminder_v2(p_run uuid,p_key text)returns jsonb
      language plpgsql volatile as $$
      declare outcome source_stub.outcomes%rowtype; a cp7_alert_native.alerts%rowtype;
      begin
        insert into source_stub.attempts(condition_key)values(p_key);
        select *into strict outcome from source_stub.outcomes where condition_key=p_key;
        select *into strict a from cp7_alert_native.alerts where subject_key=p_key;
        return jsonb_build_object('rule_id','ACCESSORY_NEED','condition_key',p_key,'label',a.detail->>'label',
          'verdict',outcome.verdict,'reason',outcome.reason,'numbers',jsonb_build_object(
          'wa_notice_eligibility',outcome.eligibility,'accessory_detail',a.detail));
      end $$;
      ${Object.values(actualFunctions).join('\n')}
      create trigger alerts_guard before update or delete on cp7_alert_native.alerts
      for each row execute function cp7_alert_native.guard_alert();`)
    assert.match(actualFunctions.analysis_recheck, /last_rechecked_at=clock_timestamp\(\)/,
      'candidate does not persist an actual check attempt')
    for (let n = 1; n <= 21; n++) {
      const target = `${id(10000 + n)}:${id(20000 + n)}`
      const category = `ACCESSORY_CATEGORY:${id(30000 + n)}`
      const key = `ACCESSORY_NEED:${target}:${category}`
      const detail = { run_id: id(999), data_as_of: '2026-10-20T01:00:00Z', checked_at: '2026-10-20T02:00:00Z',
        label: `Synthetic target ${n}`, target_key: target, category_key: category, category_name: 'Synthetic buttons',
        state: 'DATA_REVIEW', verdict: 'REVIEW_REQUIRED_NOW', gross_state: 'ASSUMED', gross_qty: '186', unit: 'PCS',
        installed_state: 'UNKNOWN', installed_proven: null, unused_allocated_state: 'UNKNOWN', unused_allocated_proven: null,
        additional_external_state: 'UNKNOWN', additional_external: null, threshold_status: 'NOT_EVALUATED_UNKNOWN',
        reason: 'INSTALLATION_AND_ELIGIBLE_UNUSED_SUPPLY_NOT_PROVEN' }
      await db.query(`insert into cp7_alert_native.alerts(id,kind,subject_key,episode,title,detail,party_names,source_hash,opened_at)
        values($1,'ACCESSORY_NEED',$2,1,$3,$4::jsonb,'[]'::jsonb,$5,'2026-10-20T00:00:00Z')`,
      [id(n), key, `Synthetic accessory review ${n}`, JSON.stringify(detail), 'a'.repeat(64)])
      await db.query(`insert into cp7_alert_native.outbox(id,item_kind,item_id,alert_kind,state,reason)values($1,'ALERT',$2,'ACCESSORY_NEED','PENDING',null)`, [n, id(n)])
      const changed = n <= 10
      await db.query('insert into source_stub.outcomes values($1,$2,$3,$4)', [key,
        changed ? 'CHANGED_REVIEW_REQUIRED' : 'REVIEW_REQUIRED_NOW',
        n === 21 ? 'REVIEW_NOTICE_ELIGIBLE' : changed ? 'SOURCE_REVIEW_REQUIRED' : 'DISABLED',
        changed ? 'ACCESSORY_SOURCE_CHANGED_AFTER_SNAPSHOT' : 'INSTALLATION_AND_ELIGIBLE_UNUSED_SUPPLY_NOT_PROVEN'])
    }
    const before = (await db.query('select id,episode,opened_at,state from cp7_alert_native.alerts order by id')).rows
    const traces = []
    let reached = null
    for (let tick = 1; tick <= expectedTick; tick++) {
      await db.exec('begin')
      const orderSql = mode === 'INSTANT' ? instantOrder : digestOrder.replace('any(s.kinds)', 'any($1::text[])')
      const ordered = (await db.query(`select array(${orderSql}) ids`, mode === 'INSTANT' ? [] : [['ACCESSORY_NEED']])).rows[0].ids
      const checked = (await db.query(`select cp7_alert_native.analysis_recheck($1::uuid[],clock_timestamp()+interval'60 seconds',$2) result`,
        [ordered, cap])).rows[0].result
      const sendable = (await db.query(sendableSql, [checked.ok, checked.failed])).rows[0].array_agg ?? []
      const trace = { tick, firstSelected: ordered[0], checked: checked.checked.ACCESSORY_NEED ?? 0,
        unchecked: checked.unchecked.ACCESSORY_NEED ?? 0, ok: checked.ok, sendable }
      traces.push(trace)
      if (sendable.includes('21') || sendable.includes(21)) reached ??= tick
      assert.ok(sendable.every(n => Number(n) === 21), `held source/policy row escaped whitelist: ${JSON.stringify(trace)}`)
      await db.exec('commit')
    }
    const after = (await db.query('select id,episode,opened_at,state from cp7_alert_native.alerts order by id')).rows
    assert.deepEqual(after, before, 'recheck rotation changed episode identity, opening time or OPEN state')
    assert.equal((await db.query('select count(*)::int n from cp7_alert_native.alerts')).rows[0].n, 21, 'recheck duplicated an alert')
    assert.equal((await db.query("select count(*)::int n from cp7_alert_native.outbox where state='PENDING'")).rows[0].n, 21,
      'selection-only regression must not pretend to dispatch or resolve the held rows')
    if (!legacyOrder) {
      assert.equal(reached, expectedTick, `${mode} eligible21st never reached on expected tick; ${JSON.stringify(traces)}`)
      assert.equal(traces[expectedTick - 1].firstSelected, id(21), 'unchecked21st lost next-tick priority')
      assert.deepEqual(traces[expectedTick - 1].ok, [id(21)], 'only the known eligible synthetic verdict may pass')
    } else {
      assert.equal(reached, null, 'legacy-order countervariant unexpectedly passed; counterexample fixture is invalid')
      assert.ok(traces.every(t => t.firstSelected === id(1) && t.ok.length === 0), 'legacy order did not reproduce fixed-prefix starvation')
    }
    return { mode, cap, expectedTick, result: legacyOrder ? 'EXPECTED_COUNTEREXAMPLE' : 'PASS',
      eligibleReachedTick: reached, heldEpisodesPreserved: 20, traces }
  } finally { await db.close() }
}

const results = []
for (const [mode, cap, expectedTick] of [['INSTANT',20,2], ['DIGEST',20,2], ['DIGEST',10,3]])
  results.push(await exercise(mode, cap, expectedTick))
console.log(JSON.stringify({ case_id: 'OW01_SYNTHETIC_HELD_REVIEW_RECHECK_FAIRNESS',
  fixture_kind: 'SYNTHETIC_SOURCE_MODULE_SELECTION_ONLY', source_path: sourcePath, source_sha256: sha(source),
  analysis_recheck_sha256: sha(actualFunctions.analysis_recheck),
  instant_selector_sha256: sha(instantOrder), digest_selector_sha256: sha(digestOrder),
  variant: legacyOrder ? 'PRIOR_ORDER_CAUSAL_COUNTERVARIANT_NOT_EXACT_PREVIOUS_COMMIT' : 'ACTUAL_CANDIDATE',
  proves_provider_delivery: false, proves_native_source: false, results }, null, 2))

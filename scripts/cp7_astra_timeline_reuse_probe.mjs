// Writer-assistance proof, not independent audit acceptance. No external DB URL.
// The schedule producer is the existing fixture; netting and all pure kernels
// are real SQL. This is not an Auth/browser/full-application capacity proof.
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { createHash } from 'node:crypto'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { openRuntime, jsonArg } from '../tests/cp7/families/f04/runtime.mjs'
import { functionBlocks } from '../tests/cp7/families/f04/schedule-scenario-fixture.mjs'
import { DEFECTS, installNettingControls, nettingInput, orderProbe, suffixed } from '../tests/cp7/families/f04/netting-fixture.mjs'

const predecessor = 'aa638356e13aeffe7b2a2aa96f17dbe19676db1f'
const path = 'scripts/cp7-src/planning/netting.sql'
const original = execFileSync('git', ['show', `${predecessor}:${path}`], { encoding: 'utf8' })
const candidate = readFileSync(path, 'utf8')
const sha256 = s => createHash('sha256').update(s).digest('hex')
const originalBlocks = functionBlocks(original), candidateBlocks = functionBlocks(candidate)
assert.deepEqual([...candidateBlocks.keys()], [...originalBlocks.keys()])
for (const [name, body] of originalBlocks) if (name !== 'cp7_netting_native.build') assert.equal(candidateBlocks.get(name), body, name)
// No schema/ACL/wrapper/other-function changes can hide between blocks.
assert.equal(candidate.replace(candidateBlocks.get('cp7_netting_native.build'), 'BUILD_BODY'),
  original.replace(originalBlocks.get('cp7_netting_native.build'), 'BUILD_BODY'))
const prefix = text => text.slice(0, text.indexOf('declare'))
assert.equal(prefix(candidateBlocks.get('cp7_netting_native.build')), prefix(originalBlocks.get('cp7_netting_native.build')))
const helperSQL = text => [...functionBlocks(text)].filter(([name]) => /^cp7_netting_native\.(bound_product|matching_models|matching|matches|timeline|build)$/.test(name)).map(([, body]) => body).join('\n')
const fresh = helperSQL(candidate)
const variants = {
  ignores_supply: ["if line_edges='[]'::jsonb then", 'if true then'],
  wrong_target: ["baseline_lines[(planned_index->>(r->>'target_key'))::integer]", 'baseline_lines[1]'],
}
const out = process.argv[2] ?? 'test-results/astra-timeline-reuse/REPORT.json'
const quick = process.argv.includes('--quick')
if (process.env.CI && quick) throw new Error('CI must execute the full predeclared probe')
const report = { contract: 'cp7.astra.timeline-reuse.v1', predecessor, source_sha256: { original: sha256(original), candidate: sha256(candidate) },
  oracle_origin: 'EXACT_PINNED_PREDECESSOR_BYTE_AND_SQLSTATE_MESSAGE_COMPARISON', fixture_origin: 'WRITER_GENERATOR_PLUS_ASTRA_EMPTY_AND_MIXED_TARGET_CONTROLS',
  status: 'INCOMPLETE', quick, cases: [], mutations: [], benchmark: [], full_application: false, independent_acceptance: false, production_go: false }
let db
try {
  db = await openRuntime({ commandTimeoutMs: 600_000 })
  report.runtime = { flavor: db.flavor, version: db.version }
  await installNettingControls(db)
  await db.execute(suffixed(helperSQL(original), '_pinned'))
  for (const [name, [from, to]] of Object.entries(variants)) {
    assert.equal(fresh.split(from).length, 2, name)
    await db.execute(suffixed(fresh.replace(from, to), `_astra_${name}`))
  }
  await db.execute(`create function public.astra_compare(c jsonb,fn text,mode text)returns jsonb language plpgsql as $a$
    declare old jsonb;fresh jsonb;s0 text:='NO_ERROR';s1 text:='NO_ERROR';begin
     perform set_config('plan_cache_mode',mode,true);
     begin execute 'select cp7_netting_native.build_pinned($1,$2)'into old using c,'{}'::jsonb;
     exception when others then s0:=sqlstate||':'||sqlerrm;end;
     begin execute format('select cp7_netting_native.%I($1,$2)',fn)into fresh using c,'{}'::jsonb;
     exception when others then s1:=sqlstate||':'||sqlerrm;end;
     return jsonb_build_object('old_error',s0,'new_error',s1,'identical',old::text is not distinct from fresh::text,
      'old_md5',md5(old::text),'new_md5',md5(fresh::text),'bytes',octet_length(old::text),
      'rows',coalesce(jsonb_array_length(old->'rows'),0),
      'supply_events',(select count(*)from jsonb_array_elements(coalesce(old->'rows','[]'))r,
       jsonb_array_elements(coalesce(r->'timeline'->'inputs'->'events','[]'))e where e->>'kind'='SUPPLY'));
    end $a$;
    create table public.astra_bench_input(id int primary key,c jsonb not null);
    create function public.astra_bench(fn text,n int)returns jsonb language plpgsql as $b$
    declare v jsonb;t timestamptz;r jsonb;elapsed numeric;begin
     select c into v from public.astra_bench_input where id=n;
     t:=clock_timestamp();execute format('select cp7_netting_native.%I($1,$2)',fn)into r using v,'{}'::jsonb;
     elapsed:=extract(epoch from clock_timestamp()-t)*1000;
     return jsonb_build_object('fn',fn,'ms',elapsed,'md5',md5(r::text),'bytes',octet_length(r::text),
      'targets',jsonb_array_length(r->'rows'),'positions',jsonb_array_length(v->'stub_scenario'->'wip'->'positions'));
    end $b$;`)
  const cases = [ { id: 'ORDER', c: orderProbe(false) }, { id: 'ORDER_SWAPPED', c: orderProbe(true) } ]
  // Existing varied faults include duplicate row keys, unknown rates, negative
  // FG, invalid source refs, wrong matching, late/unknown ETAs and size conflict.
  for (let seed = 1; seed <= (quick ? 3 : 12); seed++) for (const defect of DEFECTS) {
    if (defect === 'BIG_HORIZON' && seed !== 1) continue
    cases.push({ id: `GENERATED_${seed}_${defect ?? 'VALID'}_${cases.length}`, c: nettingInput(seed, {
      positions: 6 + seed % 13, targets: 3 + seed % 9, roots: 2 + seed % 5, models: 2 + seed % 3, complete: seed % 3 !== 1, defect }) })
  }
  const edgeFree = [], mixed = []
  for (let seed = 100; seed < (quick ? 105 : 120); seed++) {
    const c = nettingInput(seed, { positions: 0, targets: 10, roots: 5, models: 3, complete: true })
    const rows = c.stub_scenario.supply_run_result.baseline_run_result.rows
    rows.forEach((row, i) => {
      row.profile.config = { lead_days: `${1 + i % 4}.5`, review_days: '2' }
      row.demand_estimate.daily_pcs = i % 5 === 0 ? null : `${i + 1}.375`
      row.available_fg_pcs = i % 7 === 0 ? '-2' : String(i * 3)
      if (i % 6 === 0) row.target = { status: 'UNKNOWN', target_pcs: null }
    })
    const record = { id: `EMPTY_SUPPLY_${seed}`, c }; cases.push(record); edgeFree.push(record)
    const withSupply = { id: `MIXED_SUPPLY_${seed}`, c: nettingInput(seed, { positions: 40, targets: 10, roots: 5, models: 2, complete: true }) }
    cases.push(withSupply); mixed.push(withSupply)
  }
  const modes = ['auto', 'force_custom_plan', 'force_generic_plan']
  assert.equal(cases.length, quick ? 145 : 571, 'predeclared case inventory changed')
  let successes = 0, supplyEvents = 0
  const refusals = new Set()
  for (let i = 0; i < cases.length; i += 12) {
    const batch = cases.slice(i, i + 12), mode = modes[Math.floor(i / 12) % modes.length]
    const results = await db.query(`select public.astra_compare(x.c,'build','${mode}') r from jsonb_array_elements(${jsonArg(batch.map(x => x.c))})with ordinality x(c,o)order by x.o`)
    results.forEach(({ r }, j) => {
      const id = batch[j].id; report.cases.push({ id, mode, ...r })
      assert.equal(r.new_error, r.old_error, `${id}: first refusal changed`)
      assert.equal(r.identical, true, `${id}: complete serialized output changed`)
      if (r.old_error === 'NO_ERROR') { successes++; supplyEvents += r.supply_events } else refusals.add(r.old_error)
    })
  }
  assert(successes > (quick ? 20 : 100), 'must exercise successful results')
  assert(refusals.size >= 10, 'must exercise distinct refusals')
  assert(supplyEvents > 10, 'must exercise actual supply events; not only empty inputs')
  for (const name of Object.keys(variants)) {
    const controls = name === 'ignores_supply' ? mixed : edgeFree
    let witness
    for (const c of controls) {
      const { r } = (await db.query(`select public.astra_compare(${jsonArg(c.c)},'build_astra_${name}','auto') r`))[0]
      if (r.new_error !== r.old_error || !r.identical) { witness = { id: c.id, ...r }; break }
    }
    report.mutations.push({ name, caught: Boolean(witness), witness })
    assert(witness, `negative control did not detect ${name}`)
    const control = controls.find(x => x.id === witness.id)
    const { r } = (await db.query(`select public.astra_compare(${jsonArg(control.c)},'build','auto') r`))[0]
    assert(r.identical && r.new_error === r.old_error, `unmutated control failed after ${name}`)
  }
  report.counts = { declared: cases.length, executed: report.cases.length, successes, refusals: report.cases.length - successes, distinct_refusals: refusals.size, supply_events: supplyEvents }
  console.log(JSON.stringify({ phase: 'PARITY_PASS', ...report.counts, mutations_caught: report.mutations.length }))
  const sizes = quick ? [[100, 0], [100, 40]] : [[100, 0], [300, 0], [1000, 0], [100, 100], [300, 100], [1000, 100]]
  for (const [i, [targets, positions]] of sizes.entries()) {
    const roots = Math.ceil(targets / 3.1), c = nettingInput(9000 + i, { targets, positions, roots, models: Math.max(3, Math.round(roots / 5)), complete: true })
    // Fully known forecasts and the same 10-day horizon on both versions.
    for (const r of c.stub_scenario.supply_run_result.baseline_run_result.rows) { r.profile.config = { lead_days: '3', review_days: '7' }; r.demand_estimate.daily_pcs = '2.125' }
    await db.execute(`insert into public.astra_bench_input values(${i},${jsonArg(c)})`)
    // One SQL call = one native psql session: warm both, then A/B/B/A.
    // Separate db.query calls would create new sessions and lose plan warmup.
    const samples = (await db.query(`select public.astra_bench(x.fn,${i}) r from
      unnest(array['build_pinned','build','build_pinned','build','build','build_pinned'])with ordinality x(fn,o)
      order by x.o`)).slice(2).map(x => x.r)
    for (const r of samples) { assert.equal(r.md5, samples[0].md5); assert.equal(r.bytes, samples[0].bytes) }
    const average = fn => { const a = samples.filter(x => x.fn === fn); return a.reduce((sum, x) => sum + Number(x.ms), 0) / a.length }
    const oldMs = average('build_pinned'), newMs = average('build')
    const entry = { requested_targets: targets, positions, actual_targets: samples[0].targets, old_ms: oldMs, new_ms: newMs, reduction_percent: 100 * (oldMs - newMs) / oldMs, samples }
    report.benchmark.push(entry)
    console.log(JSON.stringify({ phase: 'BENCHMARK', ...entry, samples: undefined }))
  }
  assert.deepEqual(await db.query('select id,amount::text amount from public.f04_ledger_canary order by id'), [{ id: 1, amount: '12345.67' }])
  report.ledger_canary_unchanged = true
  report.status = 'PASS'
} finally {
  if (db) await db.close()
  mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify({ status: report.status, out, runtime: report.runtime, counts: report.counts }))
}

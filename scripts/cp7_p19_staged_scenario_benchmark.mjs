#!/usr/bin/env node
// P19 phase B staged analysis benchmark on the REAL single chain (history,
// baseline, WIP/supply, schedule, netting, fabric/accessory needs, analysis):
// no stand-in. LOCAL kernel runtime over generated captures; never Native,
// Auth or HTTP evidence. For each vector (targets x history days):
// 1) the staged job, every unit its own psql session under the unchanged 8 s
//    statement limit, with per-unit server time, unit counts and completeness;
// 2) the single analysis build in ONE call without a statement limit
//    (measurement only): byte parity where it runs, its refusal where its caps
//    refuse (5000 targets).
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { openRuntime, jsonArg } from '../tests/cp7/families/f04/runtime.mjs'
import { ACCESS, ACTOR, installScenarioControls, scenarioCapture } from '../tests/cp7/families/f04/staged-scenario-fixture.mjs'

const out = process.argv[2] ?? 'test-results/cp7-shell-proof/P19_STAGED_SCENARIO_KERNEL.json'
const sizes = (process.env.CP7_P19_STAGED || '1000x30,5000x30,5000x100').split(',').map(s => s.split('x').map(Number))
// WIP: cutting groups and opening origins (positions independent of targets);
// netting keeps positions x targets <= 1,000,000 per job.
const groups = Number(process.env.CP7_P19_GROUPS || 8), origins = Number(process.env.CP7_P19_ORIGINS || 20)
// Planning horizon of the generated profiles (lead days, review days): the
// netting timeline has one row per horizon day, so it sets the analysis bytes.
const horizon = (process.env.CP7_P19_HORIZON || '20,10').split(',').map(Number)
const single = process.env.CP7_P19_SINGLE !== '0'
const report = { contract: 'cp7.p19.staged-scenario-kernel.v1', label: 'LOCAL_PG16_DEV_KERNEL_GENERATED_CAPTURES_NOT_EVIDENCE', statement_timeout: '8s', limits_raised: false,
  stand_ins: [], wip: { groups, origins }, horizon_days: { lead_max: horizon[0], review_max: horizon[1] }, vectors: [], status: 'INCOMPLETE', production_go: false }
const db = await openRuntime({ commandTimeoutMs: 600_000 })
let n = 0
try {
  report.runtime = db.flavor; report.version = db.version
  await installScenarioControls(db)
  report.bounds = (await db.query('select cp7_analysis_stage.bounds() b'))[0].b
  await db.execute('create table public.bench_cap(n integer primary key,c jsonb not null,q jsonb not null);')
  for (const [targets, days] of sizes) {
    const t00 = Date.now(), seed = 9000 + targets + days
    const { c, q } = scenarioCapture(seed, { targets, days, groups, origins, reviewed: true, horizon })
    await db.execute(`insert into public.bench_cap values(${++n},public.ss_complete(${jsonArg(c)},${seed}),${jsonArg(q)});`)
    const [cap] = await db.query(`select octet_length(c::text) bytes,jsonb_array_length(c->'facts'->'sales') sales,jsonb_array_length(c->'facts'->'stock') stock,
      jsonb_array_length(c->'schedule'->'config'->'positions') scheduled_positions from public.bench_cap where n=${n}`)
    const prepared_ms = Date.now() - t00
    const request = `03000000-0000-4000-8000-${String(n).padStart(12, '0')}`
    const [{ job }] = await db.query(`select cp7_analysis_stage.create_job('${ACTOR}','${request}',q,${jsonArg(ACCESS)},c) job from public.bench_cap where n=${n}`)
    const steps = []
    const t0 = Date.now()
    for (let k = 0; k < 100000; k++) {
      const t1 = Date.now()
      const res = await db.execute(`set statement_timeout='8s';select cp7_analysis_stage.step('${job}')::text;`)
      const s = JSON.parse(String(res).trim().split('\n').at(-1))
      steps.push({ client_ms: Date.now() - t1, attempts: s.unit_attempts })
      if (s.state !== 'RUNNING') break
    }
    const wall = Date.now() - t0
    const [st] = await db.query(`select cp7_analysis_stage.status('${job}') s,(select run_id from cp7_analysis_stage.jobs where id='${job}') run_id`)
    const units = await db.query(`select u.idx unit,u.kind stage,u.lo,u.hi,o.server_ms from cp7_analysis_stage.units u left join cp7_analysis_stage.outputs o using(job_id,idx)
      where u.job_id='${job}' order by u.idx`)
    const stages = {}
    for (const u of units) { const s = (stages[u.stage] ??= { units: 0, max_server_ms: 0, total_server_ms: 0 }); s.units++; s.max_server_ms = Math.max(s.max_server_ms, Number(u.server_ms ?? 0)); s.total_server_ms = Math.round((s.total_server_ms + Number(u.server_ms ?? 0)) * 10) / 10 }
    const vector = { targets, days, query: q, capture: { ...cap, prepared_ms }, state: st.s.state, failure: st.s.failure, unit_count: st.s.unit_count, wall_ms: wall,
      max_unit_server_ms: Math.max(...units.map(u => Number(u.server_ms ?? 0))), units_over_4000ms: units.filter(u => Number(u.server_ms) > 4000).length,
      retries: steps.filter(s => s.attempts > 0).length, stages, units: units.map((u, i) => ({ ...u, client_ms: steps[i]?.client_ms ?? null })) }
    report.vectors.push(vector)
    // A job that does not finish is recorded with the unit that stopped it;
    // the next vector still runs. The report is COMPLETE only if every job is.
    if (st.s.state !== 'DONE') {
      vector.stopped_at = units.find(u => u.server_ms === null) ?? null
      console.log(JSON.stringify({ targets, days, state: vector.state, failure: vector.failure, stopped_at: vector.stopped_at, units: vector.unit_count,
        stages: Object.fromEntries(Object.entries(stages).map(([k, v]) => [k, `${v.units}x${v.max_server_ms}`])), capture: vector.capture }))
      continue
    }
    const [done] = await db.query(`with pages as materialized(select body::jsonb p,utf8_bytes from cp7_analysis_stage.pages where run_id='${st.run_id}')
     select (select (totals->'recommendations'->>'ACTIVE')::integer+(totals->'recommendations'->>'PAUSED')::integer+(totals->'recommendations'->>'STOPPED')::integer+(totals->'recommendations'->>'OTHER')::integer from cp7_analysis_stage.page_sets where run_id='${st.run_id}') recommendations,
      (select count(*) from cp7_analysis_stage.target_rows where job_id='${job}' and kind='HIST') history_rows,
      (select count(*) from cp7_analysis_stage.target_rows where job_id='${job}' and kind='BASE') baseline_rows,
      (select count(*) from cp7_analysis_stage.target_rows where job_id='${job}' and kind='NETROW') netting_rows,
      (select count(distinct k) from(select r->'target'->>'key' k from pages cross join lateral jsonb_array_elements(p->'items'->'recommendations') r
        union all select substr(r->>'key',15) from pages cross join lateral jsonb_array_elements(p->'items'->'actions')r where r->>'key' like 'review-policy-%')x) target_keys_covered,
      (select count(*) from pages) page_count,(select sum(utf8_bytes) from pages) pages_utf8_bytes,(select max(utf8_bytes) from pages) max_page_utf8_bytes,
      h.utf8_bytes header_utf8_bytes,s.identity_hash
      from cp7_analysis_stage.headers h join cp7_analysis_stage.page_sets s using(run_id)where h.run_id='${st.run_id}'`)
    vector.completeness = done
    if ([done.history_rows, done.baseline_rows, done.netting_rows, done.target_keys_covered].some(x => Number(x) !== targets)) throw new Error(`P19_STAGED_INCOMPLETE ${JSON.stringify(done)}`)
    if (single) {
      const t1 = Date.now()
      const [s] = await db.query(`select case when x->>'state'='DONE' then jsonb_build_object('state','DONE','sha256',encode(pg_catalog.sha256(convert_to((x->'body')::text,'UTF8')),'hex'))
        else x end s from(select public.ss_single(c,q,'${st.run_id}',${jsonArg(ACCESS)}) x from public.bench_cap where n=${n})z`)
      vector.single = { ...s.s, client_ms: Date.now() - t1, note: 'single analysis build in ONE call without a statement limit (measurement only)' }
      if (s.s.state === 'DONE') {
        const [v] = await db.query(`select public.sv_verify('${job}',public.ss_single(c,q,'${st.run_id}',${jsonArg(ACCESS)})->'body') v from public.bench_cap where n=${n}`)
        vector.byte_identical = v.v.text_same && v.v.hash_same && v.v.document_same && v.v.bad.length === 0
        if (!vector.byte_identical) throw new Error(`P19_STAGED_NOT_IDENTICAL ${targets}x${days}`)
      }
    }
    console.log(JSON.stringify({ targets, days, state: vector.state, units: vector.unit_count, wall_ms: wall, max_unit_server_ms: vector.max_unit_server_ms,
      stages: Object.fromEntries(Object.entries(stages).map(([k, v]) => [k, `${v.units}x${v.max_server_ms}`])), completeness: done, capture: vector.capture,
      single: vector.single ?? null, byte_identical: vector.byte_identical ?? null }))
  }
  report.status = report.vectors.every(v => v.state === 'DONE') ? 'COMPLETE' : 'INCOMPLETE'
  if (report.status !== 'COMPLETE') process.exitCode = 1
} catch (error) {
  report.error = String(error); process.exitCode = 1
} finally {
  await db.close(); mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, JSON.stringify(report, null, 1) + '\n')
  console.log(JSON.stringify({ status: report.status, out, error: report.error }))
}

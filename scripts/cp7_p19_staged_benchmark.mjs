#!/usr/bin/env node
// P19 staged analysis PROTOTYPE benchmark (LOCAL kernel runtime, stand-ins for
// the schedule build, fabric and accessories; never Native/Auth/HTTP evidence).
// 1) parity: the staged job and the single build on the same capture at sizes
//    the single build still runs (default chunk bounds), byte for byte;
// 2) capacity: the single build at 5000 targets (its refusal is recorded) and
//    the staged job at 5000 targets, every unit its own session under the
//    unchanged 8 s statement limit, with per-unit server time and completeness.
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { openRuntime, jsonArg } from '../tests/cp7/families/f04/runtime.mjs'
import { ACCESS, QUERY, installStagedControls, runJob, stagedInput } from '../tests/cp7/families/f04/staged-analysis-fixture.mjs'

const out = process.argv[2] ?? 'test-results/cp7-shell-proof/P19_STAGED_ANALYSIS_KERNEL.json'
const sizes = (process.env.CP7_P19_STAGED || '1000x1,1000x100,5000x1,5000x100').split(',').map(s => s.split('x').map(Number))
const shape = (targets, positions) => { const roots = Math.ceil(targets / 3.3); return { targets, positions, roots, models: Math.max(3, Math.round(roots / 5)), complete: true } }
const report = { contract: 'cp7.p19.staged-analysis-kernel.v0', label: 'LOCAL_PG16_DEV_KERNEL_STAND_INS_NOT_EVIDENCE', statement_timeout: '8s', limits_raised: false,
  vectors: [], status: 'INCOMPLETE', production_go: false }
const db = await openRuntime({ commandTimeoutMs: 600_000 })
let n = 0
try {
  report.runtime = db.flavor; report.version = db.version
  await installStagedControls(db)
  report.bounds = (await db.query('select cp7_analysis_stage.bounds() b'))[0].b
  for (const [targets, positions] of sizes) {
    const c = stagedInput(9000 + targets + positions, shape(targets, positions))
    const rows = c.stub_scenario.supply_run_result.baseline_run_result.rows.length
    const units = []
    const t0 = Date.now()
    const job = await runJob(db, c, { request: `03000000-0000-4000-8000-${String(++n).padStart(12, '0')}`, oneCallPerUnit: true, timeout: '8s',
      onStep: (s, ms) => units.push({ unit: s.units_done - 1, stage: null, client_ms: ms, state: s.state, attempts: s.unit_attempts }) })
    const wall = Date.now() - t0
    const server = await db.query(`select u.idx unit,u.kind stage,u.lo,u.hi,o.server_ms from cp7_analysis_stage.units u left join cp7_analysis_stage.outputs o using(job_id,idx)
      where u.job_id='${job.job}' order by u.idx`)
    const [done] = await db.query(`select jsonb_array_length(r.result->'recommendations') recommendations,
      (select count(*) from cp7_analysis_stage.target_rows x where x.job_id='${job.job}' and x.kind='NETROW') netting_rows,
      (select count(distinct k) from (select x->'target'->>'key' k from jsonb_array_elements(r.result->'recommendations')x
        union all select substr(x->>'key',15) from jsonb_array_elements(r.result->'actions')x where x->>'key' like 'review-policy-%') y) target_keys_covered,
      octet_length(r.result::text) result_utf8_bytes,d.utf8_bytes document_utf8_bytes,d.segment_count,r.result->>'semantic_hash' semantic_hash
      from cp7_analysis_native.runs r join cp7_analysis_jobs.documents d on d.run_id=r.id where r.id='${job.run_id}'`)
    const vector = { targets: rows, positions, state: job.status.state, failure: job.status.failure, unit_count: job.status.unit_count, wall_ms: wall,
      max_unit_server_ms: Math.max(...server.map(u => Number(u.server_ms ?? 0))), units_over_4000ms: server.filter(u => Number(u.server_ms) > 4000).length,
      retries: units.filter(u => u.attempts > 0).length, completeness: done ?? null,
      server_ms_by_stage: server.reduce((a, u) => ({ ...a, [u.stage]: Math.round(((a[u.stage] ?? 0) + Number(u.server_ms ?? 0)) * 10) / 10 }), {}),
      max_server_ms_by_stage: server.reduce((a, u) => ({ ...a, [u.stage]: Math.max(a[u.stage] ?? 0, Number(u.server_ms ?? 0)) }), {}),
      units: server.map((u, i) => ({ ...u, client_ms: units[i]?.client_ms ?? null })) }
    if (job.status.state !== 'DONE') { report.vectors.push(vector); throw new Error(`P19_STAGED_NOT_DONE ${rows}x${positions} ${JSON.stringify(job.status.failure)}`) }
    // The single build: byte parity where it runs, its refusal where it does not.
    const t1 = Date.now()
    const [single] = await db.query(`select public.st_single(${jsonArg(c)},${jsonArg(QUERY)},'${job.run_id}',${jsonArg(ACCESS)}) - 'body' s`)
    vector.single = { ...single.s, client_ms: Date.now() - t1, note: 'single build in ONE call without a statement limit (measurement only)' }
    if (single.s.state === 'DONE') {
      vector.byte_identical = done && single.s.sha256 === (await db.query(`select encode(pg_catalog.sha256(convert_to(result::text,'UTF8')),'hex') h from cp7_analysis_native.runs where id='${job.run_id}'`))[0].h
      if (!vector.byte_identical) throw new Error(`P19_STAGED_NOT_IDENTICAL ${rows}x${positions}`)
    }
    if (job.status.state !== 'DONE') { report.vectors.push(vector); throw new Error(`P19_STAGED_NOT_DONE ${rows}x${positions} ${JSON.stringify(job.status.failure)}`) }
    if (done.netting_rows !== rows || Number(done.target_keys_covered) !== rows) throw new Error(`P19_STAGED_INCOMPLETE ${JSON.stringify(done)}`)
    report.vectors.push(vector)
    console.log(JSON.stringify({ targets: rows, positions, state: vector.state, units: vector.unit_count, wall_ms: wall, max_unit_server_ms: vector.max_unit_server_ms,
      max_server_ms_by_stage: vector.max_server_ms_by_stage, completeness: done, single: vector.single, byte_identical: vector.byte_identical ?? null }))
  }
  report.status = 'COMPLETE'
} catch (error) {
  report.error = String(error); process.exitCode = 1
} finally {
  await db.close(); mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, JSON.stringify(report, null, 1) + '\n')
  console.log(JSON.stringify({ status: report.status, out, error: report.error }))
}

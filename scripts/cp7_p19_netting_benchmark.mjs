// P19 netting: exact predecessor build (and its matching, matches,
// bound_product and timeline) vs the linear form on generated Native captures.
// Byte equality is required for every compared size; the cap sizes run the
// linear form only. The shared allocation kernel, cp7_baseline.allocate, is
// unchanged and timed on its own from the inputs the build handed it.
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { openRuntime, jsonArg } from '../tests/cp7/families/f04/runtime.mjs'
import { installNettingControls, nettingBase, nettingInput } from '../tests/cp7/families/f04/netting-fixture.mjs'
const out = process.argv[2] ?? 'test-results/cp7-shell-proof/P19_NETTING_KERNEL.json'
const runner = `create table public.bench_in(n int primary key,c jsonb not null);
create function public.bench_net(fn text,n int)returns jsonb language plpgsql as $b$
declare v jsonb;t0 timestamptz;ms numeric;r jsonb;a jsonb;begin select c into v from public.bench_in where bench_in.n=bench_net.n;t0:=clock_timestamp();
 execute format('select cp7_netting_native.%s($1,$2)',fn)into r using v,'{}'::jsonb;ms:=round(extract(epoch from clock_timestamp()-t0)*1000,1);
 if r->'allocation'->>'status'='SCENARIO'then t0:=clock_timestamp();a:=cp7_baseline.allocate(r->'allocation'->'inputs');
  if a::text<>(r->'allocation')::text then raise exception 'BENCH_ALLOCATION_NOT_REPEATED';end if;end if;
 return jsonb_build_object('fn',fn,'targets',jsonb_array_length(v->'stub_scenario'->'supply_run_result'->'baseline_run_result'->'rows'),
  'positions',jsonb_array_length(v->'stub_scenario'->'wip'->'positions'),'matching_products',jsonb_array_length(v->'matching_products'),
  'ms',ms,'allocate_ms',case when a is null then null else round(extract(epoch from clock_timestamp()-t0)*1000,1)end,
  'md5',md5(r::text),'utf8_bytes',octet_length(r::text),'status',r->>'status','allocation',r->'allocation'->>'status',
  'pairs',jsonb_array_length(r->'match_results'),'edges',coalesce(jsonb_array_length(r->'allocation'->'allocation'->'edges'),0),
  'confirmed',jsonb_array_length(jsonb_path_query_array(r,'$.match_results[*] ? (@.result.match == "CONFIRMED_TARGET")')));end $b$;`
// Product keys per root: four sizes at 0.85; about five roots per model.
const shape = (targets, positions) => { const roots = Math.ceil(targets / 3.3); return { targets, positions, roots, models: Math.max(3, Math.round(roots / 5)), complete: true } }
const db = await openRuntime({ commandTimeoutMs: 600_000 })
const report = { contract: 'cp7.p19.netting-kernel.v1', predecessor: nettingBase, compared: [], linear_only: [], status: 'INCOMPLETE', production_go: false }
try {
  await installNettingControls(db); await db.execute(runner)
  const sizes = [[100, 100], [300, 100], [1000, 100], [1000, 100], [100, 1000]]
  for (const [i, [targets, positions]] of sizes.entries()) await db.execute(`insert into public.bench_in values(${i},${jsonArg(nettingInput(8000 + i, shape(targets, positions)))})`)
  for (const i of [0, 1, 2]) {
    const old = (await db.query(`select public.bench_net('build_0',${i}) r`))[0].r
    const now = (await db.query(`select public.bench_net('build',${i}) r`))[0].r
    if (old.md5 !== now.md5 || old.utf8_bytes !== now.utf8_bytes) throw new Error(`P19_NETTING_NOT_IDENTICAL ${old.targets}x${old.positions}`)
    if (now.allocation !== 'SCENARIO' || now.confirmed === 0) throw new Error(`P19_NETTING_BENCH_NOT_EXERCISED ${JSON.stringify(now)}`)
    report.compared.push({ old, new: now, identical: true })
  }
  for (const i of [3, 4]) report.linear_only.push((await db.query(`select public.bench_net('build',${i}) r`))[0].r)
  report.status = 'COMPLETE'
} finally {
  await db.close(); mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, JSON.stringify(report, null, 1))
  const line = r => `${String(r.targets).padStart(5)} ${String(r.positions).padStart(5)} ${String(r.pairs).padStart(7)} ${String(r.ms).padStart(10)} ${String(r.allocate_ms ?? '-').padStart(10)}`
  console.log(' T     P       pairs  build_ms  allocate_ms  form')
  for (const row of report.compared) console.log(`${line(row.old)}  predecessor\n${line(row.new)}  linear (md5 ${row.new.md5})`)
  for (const row of report.linear_only) console.log(`${line(row)}  linear only`)
  console.log(JSON.stringify({ status: report.status, out }))
}

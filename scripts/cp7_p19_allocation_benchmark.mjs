// P19 allocation: exact predecessor cp7_baseline.allocate (git) vs the linear
// form (working tree) on the allocation inputs the Native netting build hands
// it, from the same generated captures as the netting benchmark. Byte equality
// is required for every compared size; the cap sizes run the linear form only.
// A last pair gives every source and target its own facts, so no verdict can
// be shared and each pair calls cp7_wip.match_target as before.
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { openRuntime, jsonArg } from '../tests/cp7/families/f04/runtime.mjs'
import { installNettingControls, nettingInput } from '../tests/cp7/families/f04/netting-fixture.mjs'
import { allocationBase, allocationInput, installAllocationControls } from '../tests/cp7/families/f04/allocation-fixture.mjs'
const out = process.argv[2] ?? 'test-results/cp7-shell-proof/P19_ALLOCATION_KERNEL.json'
// The input is read into a variable first (detoasted, as the build passes it).
const runner = `create table public.bench_in(n int primary key,v jsonb not null);
create function public.bench_allocate(fn text,n int)returns jsonb language plpgsql as $b$
declare v jsonb;t0 timestamptz;ms numeric;r jsonb;begin select bench_in.v||'{}'::jsonb into v from public.bench_in where bench_in.n=bench_allocate.n;t0:=clock_timestamp();
 execute format('select cp7_baseline.%s($1)',fn)into r using v;ms:=round(extract(epoch from clock_timestamp()-t0)*1000,1);
 return jsonb_build_object('fn',fn,'targets',jsonb_array_length(v->'targets'),'positions',jsonb_array_length(v->'positions'->'positions'),
  'ms',ms,'md5',md5(r::text),'utf8_bytes',octet_length(r::text),'status',r->>'status','rows',jsonb_array_length(r->'rows'),
  'reviews',jsonb_array_length(r->'review_queue'),'edges',coalesce(jsonb_array_length(r->'allocation'->'edges'),0));end $b$;`
// Product keys per root: four sizes at 0.85; about five roots per model.
const shape = (targets, positions) => { const roots = Math.ceil(targets / 3.3); return { targets, positions, roots, models: Math.max(3, Math.round(roots / 5)), complete: true } }
// No two sources or targets share facts; every target is active and timed.
function distinctFacts(seed, targets, positions) {
  const v = allocationInput(seed, { positions, targets, pools: 20 })
  for (const s of v.matching.sources) Object.assign(s, { quality: 'COMPLETE', confirmed_target: null, constraints: [{ field: 'material', value: `m-${s.key}`, required: false, basis: 'HINT' }] })
  for (const f of v.matching.targets) f.constraints = [{ field: 'finish', value: `f-${f.key}`, required: false, basis: 'HINT' }]
  for (const t of v.targets) Object.assign(t, { production_status: 'ACTIVE', need_pcs: '1000', deadline: '2026-06-30T00:00:00Z', risk_at: t.risk_at ?? '2026-06-20T00:00:00Z', helps_at: t.helps_at ?? '2026-06-20T00:00:00Z' })
  for (const p of v.positions.positions) Object.assign(p, { eligible_company_wip: true, projection: { quality: 'SCENARIO', numerator: '0', denominator: '1', eligible_input_pcs: p.remaining_pcs, projected_good_pcs: '0' } })
  for (const e of v.etas) e.at ??= '2026-06-02T00:00:00Z'
  v.capacity_pcs = '100000'
  return v
}
const db = await openRuntime({ commandTimeoutMs: 600_000 })
const report = { contract: 'cp7.p19.allocation-kernel.v1', predecessor: allocationBase, compared: [], linear_only: [], status: 'INCOMPLETE', production_go: false }
try {
  await installNettingControls(db); await installAllocationControls(db); await db.execute(runner)
  const sizes = [[100, 100], [300, 100], [1000, 100], [1000, 100], [100, 1000]]
  for (const [i, [targets, positions]] of sizes.entries()) {
    const c = nettingInput(8000 + i, shape(targets, positions))
    await db.execute(`insert into public.bench_in select ${i},cp7_netting_native.build(${jsonArg(c)},'{}'::jsonb)->'allocation'->'inputs'`)
  }
  await db.execute(`insert into public.bench_in values(5,${jsonArg(distinctFacts(8005, 300, 100))})`)
  for (const i of [0, 1, 2, 5]) {
    const old = (await db.query(`select public.bench_allocate('allocate_0',${i}) r`))[0].r
    const now = (await db.query(`select public.bench_allocate('allocate',${i}) r`))[0].r
    if (old.md5 !== now.md5 || old.utf8_bytes !== now.utf8_bytes) throw new Error(`P19_ALLOCATION_NOT_IDENTICAL ${old.targets}x${old.positions}`)
    if (now.status !== 'SCENARIO' || now.reviews === 0 || (i !== 5 && now.edges === 0)) throw new Error(`P19_ALLOCATION_BENCH_NOT_EXERCISED ${JSON.stringify(now)}`)
    report.compared.push({ input: i === 5 ? 'distinct-facts' : 'netting-build', old, new: now, identical: true })
  }
  for (const i of [3, 4]) report.linear_only.push({ input: 'netting-build', ...(await db.query(`select public.bench_allocate('allocate',${i}) r`))[0].r })
  report.status = 'COMPLETE'
} finally {
  await db.close(); mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, JSON.stringify(report, null, 1))
  const line = r => `${String(r.targets).padStart(5)} ${String(r.positions).padStart(5)} ${String(r.reviews).padStart(7)} ${String(r.edges).padStart(5)} ${String(r.ms).padStart(10)}`
  console.log(' T     P     reviews edges allocate_ms  form')
  for (const row of report.compared) console.log(`${line(row.old)}  predecessor (${row.input})\n${line(row.new)}  linear (md5 ${row.new.md5})`)
  for (const row of report.linear_only) console.log(`${line(row)}  linear only (${row.input})`)
  console.log(JSON.stringify({ status: report.status, out }))
}

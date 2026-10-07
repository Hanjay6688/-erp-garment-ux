// P19 schedule scenario: exact predecessor build (and its project_yield) vs the
// linear form on generated captured WIP. Byte equality is required for every
// compared size; the largest size runs the linear form only.
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { openRuntime, jsonArg } from '../tests/cp7/families/f04/runtime.mjs'
import { installScheduleControls, scheduleBase, scheduleInput } from '../tests/cp7/families/f04/schedule-scenario-fixture.mjs'
const out = process.argv[2] ?? 'test-results/cp7-shell-proof/P19_SCHEDULE_SCENARIO_KERNEL.json'
const runner = `create table public.bench_in(n int primary key,c jsonb not null);
create function public.bench_sched(fn text,n int)returns jsonb language plpgsql as $b$
declare v jsonb;t0 timestamptz;r jsonb;begin select c into v from public.bench_in where bench_in.n=bench_sched.n;t0:=clock_timestamp();
 execute format('select %s($1,$2)',fn)into r using v,'{}'::jsonb;
 return jsonb_build_object('fn',fn,'positions',jsonb_array_length(v->'stub_supply'->'wip'->'positions'),'windows',jsonb_array_length(v->'schedule'->'config'->'windows'),
  'ms',round(extract(epoch from clock_timestamp()-t0)*1000,1),'md5',md5(r::text),'utf8_bytes',octet_length(r::text),
  'status',r->>'status','known_etas',jsonb_array_length(jsonb_path_query_array(r,'$.etas[*] ? (@.result.status != "UNKNOWN")')));end $b$;`
const db = await openRuntime({ commandTimeoutMs: 600_000 })
const report = { contract: 'cp7.p19.schedule-scenario-kernel.v1', predecessor: scheduleBase, compared: [], linear_only: [], status: 'INCOMPLETE', production_go: false }
try {
  await installScheduleControls(db); await db.execute(runner)
  // Sizes 0-2 exhaust the calendar after about a hundred positions (the rest are
  // UNKNOWN by rule); 3-4 give every position a working-calendar ETA.
  const sizes = [[300, 40, 90], [1000, 40, 90], [2000, 40, 90], [1000, 60, 1], [5000, 60, 90], [5000, 60, 1]]
  for (const [i, [positions, windows, maxMinutes]] of sizes.entries()) await db.execute(`insert into public.bench_in values(${i},${jsonArg(scheduleInput(7000 + i, { positions, windows, maxMinutes }))})`)
  for (const i of [0, 1, 2, 3]) {
    const old = (await db.query(`select public.bench_sched('cp7_schedule_native.build_0',${i}) r`))[0].r
    const now = (await db.query(`select public.bench_sched('cp7_schedule_native.build',${i}) r`))[0].r
    if (old.md5 !== now.md5 || old.utf8_bytes !== now.utf8_bytes) throw new Error(`P19_SCHEDULE_NOT_IDENTICAL ${old.positions}`)
    if (now.status !== 'SCENARIO' || now.known_etas === 0) throw new Error(`P19_SCHEDULE_BENCH_NOT_EXERCISED ${JSON.stringify(now)}`)
    report.compared.push({ old, new: now, identical: true })
  }
  for (const i of [4, 5]) report.linear_only.push((await db.query(`select public.bench_sched('cp7_schedule_native.build',${i}) r`))[0].r)
  report.status = 'COMPLETE'
} finally {
  await db.close(); mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, JSON.stringify(report, null, 1)); console.log(JSON.stringify(report))
}

// P19 baseline build: exact predecessor cp7_baseline_native.build (git) vs the
// linear form (working tree) on generated captures with a profile and a
// production policy for every root. Byte equality is required for every size.
// history_build is timed alone too, so the layer's own cost is visible.
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { openRuntime, jsonArg } from '../tests/cp7/families/f04/runtime.mjs'
import { QUERY, baselineBase, baselineCapture, installBaselineControls } from '../tests/cp7/families/f04/baseline-build-fixture.mjs'
const out = process.argv[2] ?? 'test-results/cp7-shell-proof/P19_BASELINE_BUILD_KERNEL.json'
// The input is read into a variable first (detoasted, as the capture passes it).
const runner = `create table public.bench_in(n int primary key,c jsonb not null);
create function public.bench_build(fn text,n int)returns jsonb language plpgsql as $b$
declare c jsonb;t0 timestamptz;ms numeric;r jsonb;begin select bench_in.c||'{}'::jsonb into c from public.bench_in where bench_in.n=bench_build.n;t0:=clock_timestamp();
 execute format('select %s($1,$2)',fn)into r using c,${jsonArg(QUERY)};ms:=round(extract(epoch from clock_timestamp()-t0)*1000,1);
 return jsonb_build_object('fn',fn,'ms',ms,'md5',md5(r::text),'utf8_bytes',octet_length(r::text),
  'rows',jsonb_array_length(coalesce(r->'rows',r->'history'->'rows')));end $b$;`
const db = await openRuntime({ commandTimeoutMs: 600_000 })
const report = { contract: 'cp7.p19.baseline-build-kernel.v1', predecessor: baselineBase, history_days: 30, compared: [], status: 'INCOMPLETE', production_go: false }
try {
  await installBaselineControls(db); await db.execute(runner)
  for (const [i, targets] of [100, 300, 1000].entries()) {
    const c = baselineCapture(9100 + i, { products: targets, stock: targets * 8, sales: targets * 4 })
    await db.execute(`insert into public.bench_in values(${i},${jsonArg(c)})`)
    const [history] = (await db.query(`select public.bench_build('cp7_planning.history_build_real',${i}) r`)).map(x => x.r)
    const [old] = (await db.query(`select public.bench_build('cp7_baseline_native.build_0',${i}) r`)).map(x => x.r)
    const [fresh] = (await db.query(`select public.bench_build('cp7_baseline_native.build',${i}) r`)).map(x => x.r)
    const row = { targets, profiles: c.profiles.length, policies: c.production_policies.rows.length, history, old, new: fresh, identical: old.md5 === fresh.md5 && old.utf8_bytes === fresh.utf8_bytes,
      own_ms_old: Math.round((old.ms - history.ms) * 10) / 10, own_ms_new: Math.round((fresh.ms - history.ms) * 10) / 10 }
    report.compared.push(row)
    console.log(String(targets).padStart(6), String(history.ms).padStart(9), String(old.ms).padStart(9), String(fresh.ms).padStart(9), row.identical ? 'identical' : 'DIFFERENT')
    if (!row.identical) throw new Error(`P19 baseline build differs at ${targets} targets`)
  }
  report.status = 'COMPLETE'
} finally {
  await db.close()
  mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, JSON.stringify(report, null, 2) + '\n')
  console.log(JSON.stringify({ status: report.status, out }))
}
if (report.status !== 'COMPLETE') process.exit(1)

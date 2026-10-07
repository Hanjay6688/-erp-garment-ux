#!/usr/bin/env node
// P19 phase D: can one jsonb `runs.result` hold a REAL-SHAPED 5,000-target
// analysis, and what does one statement pay for it? The analysis text is built
// from a retained real Native Original (P19_LOAD_PROFILE_12, 14 targets,
// source 8f326d87; ~45 KB per target, 78 % timeline): its per-target items are
// repeated k times (key repetition does not change jsonb parse or size cost;
// SYNTHETIC from real items). Timings are LOCAL_PG16_DEV, one session, no
// statement limit (measurement only); never Native/Auth/HTTP evidence.
import { gunzipSync } from 'node:zlib'
import { readFileSync, writeFileSync, mkdirSync, rmSync, chmodSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { tmpdir } from 'node:os'
import { openRuntime } from '../tests/cp7/families/f04/runtime.mjs'

const out = process.argv[2] ?? 'test-results/cp7-shell-proof/P19_RESULT_STORAGE.json'
const targetsList = (process.env.CP7_P19_STORAGE_TARGETS || '14,1000,2500,4650,5000').split(',').map(Number)
const PER_TARGET = ['recommendations', 'timeline', 'actions', 'demand_models', 'material_needs']
const pg = v => v === null || typeof v !== 'object' ? JSON.stringify(v) : Array.isArray(v) ? '[' + v.map(pg).join(', ') + ']'
  : '{' + Object.entries(v).map(([k, x]) => JSON.stringify(k) + ': ' + pg(x)).join(', ') + '}'
const retained = JSON.parse(gunzipSync(readFileSync('docs/cp7/evidence/integration-8f/p19-native-load/ORIGINAL_REPORTS.json.gz')).toString('utf8'))
const real = JSON.parse(retained.root_json_utf8['P19_LOAD_PROFILE_12.json']).observed.original.analysis
const base = real.recommendations.length
const report = { contract: 'cp7.p19.result-storage.v0', label: 'LOCAL_PG16_DEV_SYNTHETIC_FROM_REAL_ITEMS_NOT_EVIDENCE', source: { name: 'P19_LOAD_PROFILE_12.json', commit: retained.source_commit, targets: base },
  jsonb_limit_bytes: 268435455, rows: [], status: 'INCOMPLETE', production_go: false }
// Repeat every per-target item k times; per-target metrics (scope TARGET) and
// assumptions after the schedule assumption likewise; global items once.
function scaled(k) {
  const a = { ...real }
  for (const f of PER_TARGET) a[f] = Array.from({ length: k }, () => real[f]).flat()
  const tm = real.metrics.filter(m => m.scope_kind === 'TARGET'), gm = real.metrics.filter(m => m.scope_kind !== 'TARGET')
  a.metrics = [...Array.from({ length: k }, () => tm).flat(), ...gm]
  a.assumptions = [real.assumptions[0], ...Array.from({ length: k }, () => real.assumptions.slice(1)).flat()]
  return pg(a)
}
const dir = join(tmpdir(), `cp7-p19-storage-${process.pid}`); mkdirSync(dir, { recursive: true }); chmodSync(dir, 0o755)
const db = await openRuntime({ commandTimeoutMs: 600_000 })
try {
  report.runtime = db.flavor; report.version = db.version
  await db.execute(`create table public.src(body text);create table public.as_jsonb(r jsonb);create table public.as_text(r text);
   create function public.measure()returns jsonb language plpgsql as $s$
   declare s text;j jsonb;t0 timestamptz;r jsonb;ms numeric;
   begin
    select body into s from public.src;r:=jsonb_build_object('text_utf8_bytes',octet_length(s));
    t0:=clock_timestamp();perform encode(sha256(convert_to(s,'UTF8')),'hex');r:=r||jsonb_build_object('sha256_ms',round(extract(epoch from clock_timestamp()-t0)*1000));
    t0:=clock_timestamp();insert into public.as_text values(s);r:=r||jsonb_build_object('insert_text_ms',round(extract(epoch from clock_timestamp()-t0)*1000),
     'text_stored_bytes',(select pg_column_size(x.r)from public.as_text x limit 1));
    begin
     for i in 1..2 loop
      t0:=clock_timestamp();j:=s::jsonb;ms:=round(extract(epoch from clock_timestamp()-t0)*1000);r:=r||jsonb_build_object('parse_ms_'||i,ms);
     end loop;
     r:=r||jsonb_build_object('jsonb_datum_bytes',pg_column_size(j),'jsonb_to_text_ratio',round(pg_column_size(j)::numeric/octet_length(s),3));
     t0:=clock_timestamp();insert into public.as_jsonb values(j);r:=r||jsonb_build_object('insert_jsonb_ms',round(extract(epoch from clock_timestamp()-t0)*1000),
      'jsonb_stored_bytes',(select pg_column_size(x.r)from public.as_jsonb x limit 1));
     t0:=clock_timestamp();perform octet_length(j::text);r:=r||jsonb_build_object('render_text_ms',round(extract(epoch from clock_timestamp()-t0)*1000));
     t0:=clock_timestamp();perform jsonb_array_length(x.r->'recommendations')from public.as_jsonb x;r:=r||jsonb_build_object('stored_jsonb_one_key_read_ms',round(extract(epoch from clock_timestamp()-t0)*1000));
    exception when others then r:=r||jsonb_build_object('refused',sqlstate||':'||sqlerrm);end;
    truncate public.as_jsonb,public.as_text;
    return r;
   end $s$;`)
  for (const n of targetsList) {
    const k = Math.max(1, Math.round(n / base)), text = scaled(k), file = join(dir, 'analysis.csv')
    writeFileSync(file, text); chmodSync(file, 0o644)
    await db.execute(`truncate public.src;\n\\copy public.src(body) from '${file}' with (format csv, quote E'\\x01', delimiter E'\\x02')`)
    rmSync(file)
    const [row] = await db.query('select public.measure() m')
    const r = { targets: k * base, k, ...row.m }
    report.rows.push(r); console.log(JSON.stringify(r))
  }
  report.status = 'COMPLETE'
} catch (error) {
  report.error = String(error?.stack ?? error); process.exitCode = 1
} finally {
  await db.close(); rmSync(dir, { recursive: true, force: true })
  mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, JSON.stringify(report, null, 1) + '\n')
  console.log(JSON.stringify({ status: report.status, out, error: report.error }))
}

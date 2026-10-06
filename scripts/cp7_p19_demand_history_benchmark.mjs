// P19 demand-1 history: exact predecessor vs linear form on generated inputs.
// Byte equality is required for every compared size; larger sizes run the
// linear form only (the predecessor needed 320 s at 200 targets x 60 days).
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { openRuntime } from '../tests/cp7/families/f04/runtime.mjs'
import { installHistoryControls, historyBase } from '../tests/cp7/families/f04/demand-history-fixture.mjs'
const out = process.argv[2] ?? 'test-results/cp7-shell-proof/P19_DEMAND_HISTORY_KERNEL.json'
const generator = `create function public.bench_input(nt int, nd int, ne int) returns jsonb language sql as $g$
with p as (select '2026-05-31'::date hi, '2026-05-31'::date-nd+1 lo),
t as (select coalesce(jsonb_agg(jsonb_build_object('key','T'||lpad(i::text,5,'0'),'size_id','M','current_group_key','G'||(i%7),
  'refs',jsonb_build_array(jsonb_build_object('kind','PRODUCT','id','p'||i,'revision','1'))) order by i),'[]') v from generate_series(1,nt) i),
e as (select coalesce(jsonb_agg(x order by j,rev),'[]') v from (
  select j,rev,jsonb_build_object('lineage_key','L'||j,'revision',rev::text,
   'known_at',to_char((p.lo+(j%nd))::timestamp+make_interval(hours=>j%24,mins=>rev)-interval '7 hours','YYYY-MM-DD"T"HH24:MI:SS"Z"'),
   'effective_at',to_char((p.lo+(j%nd))::timestamp+make_interval(hours=>j%24,mins=>rev)-interval '7 hours','YYYY-MM-DD"T"HH24:MI:SS"Z"'),
   'posted_at',case when j%10<8 then to_jsonb(to_char((p.lo+(j%nd))::timestamp+make_interval(hours=>j%24)-interval '7 hours','YYYY-MM-DD"T"HH24:MI:SS"Z"')) else 'null'::jsonb end,
   'status',case when j%10<8 then 'POSTED' when j%10=8 then 'DRAFT' else 'CANCELLED' end,
   'target_key','T'||lpad((j%nt+1)::text,5,'0'),'size_id','M','sold_group_key','G'||(j%5),
   'qty_pcs',(j%7+1+rev)::text,'returned_pcs',case when j%10<8 then (j%3)::text else '0' end,
   'refs',jsonb_build_array(jsonb_build_object('kind','SALE_ITEM','id','s'||j,'revision',rev::text))) x
  from p, generate_series(1,ne) j, generate_series(1,case when j%13=0 then 2 else 1 end) rev) z),
a as (select coalesce(jsonb_agg(jsonb_build_object('target_key','T'||lpad(i::text,5,'0'),'date',(p.lo+d)::text,'revision','1',
  'known_at','2026-05-31T12:00:00Z','state',(array['AVAILABLE','STOCKOUT','UNKNOWN','AVAILABLE'])[(i+d)%4+1],
  'refs',jsonb_build_array(jsonb_build_object('kind','PRODUCT','id','p'||i,'revision','1'))) order by i,d),'[]') v
  from p, generate_series(1,nt) i, generate_series(0,nd-1) d where (i+d)%5<>0)
select jsonb_build_object('contract_version','cp7.demand-input.v1','snapshot_id','snap','scope_id','scope',
 'known_as_of','2026-06-01T00:00:00Z','effective_as_of','2026-06-01T00:00:00Z','from_date',p.lo::text,'through_date',p.hi::text,
 'history_complete',true,'group_mode','AS_SOLD','targets',t.v,'events',e.v,'availability',a.v) from p,t,e,a
$g$;
create function public.bench_run(fn text, nt int, nd int, ne int) returns jsonb language plpgsql as $b$
declare v jsonb; t0 timestamptz; r jsonb; begin v:=public.bench_input(nt,nd,ne); t0:=clock_timestamp();
 execute format('select %s($1)',fn) into r using v;
 return jsonb_build_object('fn',fn,'targets',nt,'days',nd,'events',jsonb_array_length(v->'events'),'availability',jsonb_array_length(v->'availability'),
  'ms',round(extract(epoch from clock_timestamp()-t0)*1000,1),'md5',md5(r::text),'utf8_bytes',octet_length(r::text)); end $b$;`
const db = await openRuntime({ commandTimeoutMs: 600_000 })
const report = { contract: 'cp7.p19.demand-history-kernel.v1', predecessor: historyBase, compared: [], linear_only: [], status: 'INCOMPLETE', production_go: false }
try {
  await installHistoryControls(db); await db.execute(generator)
  for (const [nt, nd, ne] of [[10, 28, 200], [100, 30, 2000]]) {
    const old = (await db.query(`select public.bench_run('cp7_demand.history_0',${nt},${nd},${ne}) r`))[0].r
    const now = (await db.query(`select public.bench_run('cp7_demand.history',${nt},${nd},${ne}) r`))[0].r
    if (old.md5 !== now.md5 || old.utf8_bytes !== now.utf8_bytes) throw new Error(`P19_DEMAND_HISTORY_NOT_IDENTICAL ${nt}x${nd}`)
    report.compared.push({ old, new: now, identical: true })
  }
  for (const [nt, nd, ne] of [[200, 60, 5000], [400, 60, 10000], [1000, 100, 46000]])
    report.linear_only.push((await db.query(`select public.bench_run('cp7_demand.history',${nt},${nd},${ne}) r`))[0].r)
  report.status = 'COMPLETE'
} finally {
  await db.close(); mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, JSON.stringify(report, null, 1)); console.log(JSON.stringify(report))
}

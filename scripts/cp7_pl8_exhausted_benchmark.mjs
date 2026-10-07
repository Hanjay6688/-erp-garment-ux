// PL-8 part 2: cost of classifying posted cutting groups as exhausted in the
// global supply source (real capture readers and WIP kernel on SYNTHETIC erp
// stand-ins with FK-style indexes; administrative clones, not Native postings).
// Mix of history: 60% direct QC, 30% laundry, 5% BS scrapped, 5% BS reworked
// to FG (all spent), plus 40 open groups. The predecessor is run where it does
// not refuse. Default PostgreSQL settings of the disposable runtime.
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { openRuntime } from '../tests/cp7/families/f04/runtime.mjs'
import { AT, installSupplyControls, supplyBase } from '../tests/cp7/families/f04/supply-exhausted-fixture.mjs'
const out = process.argv[2] ?? 'test-results/cp7-shell-proof/PL8_EXHAUSTED_CLASSIFICATION.json'
const ladder = (process.argv[3] ?? '250x1,1000x1,5000x1,250x3,1000x3,5000x3').split(',').map(x => x.split('x').map(Number))
const db = await openRuntime({ commandTimeoutMs: 600_000 })
const report = { contract: 'cp7.pl8.exhausted-classification.v1', predecessor: supplyBase, synthetic: 'PL8_SYNTHETIC_CLONES_NOT_FACTORY_DATA', rows: [], status: 'INCOMPLETE', production_go: false }
try {
  await installSupplyControls(db)
  await db.execute(`create function public.sx_bench(p_at timestamptz)returns jsonb language plpgsql as $$
   declare ids uuid[];n int;i int:=1;part jsonb;t0 timestamptz;t1 timestamptz;tc numeric:=0;tn numeric:=0;k int:=0;src jsonb;w jsonb;ts numeric;tw numeric;o jsonb;ow jsonb;os text:='NO_ERROR';ws text:='NO_ERROR';to_ numeric;tow numeric;
   begin
    select array_agg(id order by id)into ids from erp.cutting_groups where material_issue_posted and cut_at<=p_at;n:=cardinality(ids);
    while i<=n loop t0:=clock_timestamp();part:=cp7_wip.capture_cutting_sources(ids[i:least(i+49,n)],p_at);t1:=clock_timestamp();tc:=tc+extract(epoch from t1-t0);
     k:=k+cardinality(cp7_supply_native.exhausted_groups(part));tn:=tn+extract(epoch from clock_timestamp()-t1);i:=i+50;end loop;
    t0:=clock_timestamp();src:=cp7_supply_native.wip_source_at(p_at);ts:=extract(epoch from clock_timestamp()-t0);
    t0:=clock_timestamp();w:=cp7_wip.normalize_production(src);tw:=extract(epoch from clock_timestamp()-t0);
    t0:=clock_timestamp();begin o:=cp7_supply_native.wip_source_at_0(p_at);exception when others then os:=sqlerrm;end;to_:=extract(epoch from clock_timestamp()-t0);
    if o is not null then t0:=clock_timestamp();begin ow:=cp7_wip.normalize_production(o);exception when others then ws:=sqlerrm;end;tow:=extract(epoch from clock_timestamp()-t0);end if;
    return jsonb_build_object('posted',n,'exhausted',k,'kept',jsonb_array_length(src->'scope'->'cutting_groups'),
     'capture_ms',round(tc*1000),'classify_ms',round(tn*1000),'new_source_ms',round(ts*1000),'new_normalize_ms',round(tw*1000),
     'new_positions',jsonb_array_length(w->'positions'),'new_status',w->>'status',
     'old_source',os,'old_source_ms',round(to_*1000),'old_normalize',case when o is null then null else ws end,'old_normalize_ms',round(tow*1000),
     'old_positions',jsonb_array_length(ow->'positions'),'old_status',ow->>'status');
   end $$;`)
  for (const [groups, sizes] of ladder) {
    const hist = groups - 40, mix = { direct: Math.floor(hist * 0.6), laundry: Math.floor(hist * 0.3), bs_scrap: Math.floor(hist * 0.05) }
    mix.rework_fg = hist - mix.direct - mix.laundry - mix.bs_scrap
    await db.execute('select public.sx_reset();')
    for (const [kind, n] of [...Object.entries(mix), ['open', 20], ['partial', 20]]) await db.execute(`select public.sx_seed('${kind}',${n},${sizes});`)
    await db.execute('vacuum analyze;')
    const row = { groups, sizes_per_group: sizes, mix, ...(await db.query(`select public.sx_bench('${AT}') r`))[0].r }
    row.classify_ms_per_group = Math.round(row.classify_ms / groups * 100) / 100
    report.rows.push(row); console.log(JSON.stringify(row))
  }
  report.status = 'COMPLETE'
} finally {
  await db.close(); mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, JSON.stringify(report, null, 1)); console.log(JSON.stringify({ status: report.status, out }))
}

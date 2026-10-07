// PL-8 part 3: cost of the global supply source with stored exhaustion proofs
// (real capture readers and WIP kernel on SYNTHETIC erp stand-ins with FK-style
// indexes; administrative clones, not Native postings). Same history mix as
// cp7_pl8_exhausted_benchmark: 60% direct QC, 30% laundry, 5% BS scrapped, 5%
// BS reworked to FG (all spent), plus 20 open and 20 partial groups. Columns:
// the cb201edf source (every group classified per request), the working tree
// with no proof (cold), the proof writer in windows of 1000 groups, the working
// tree with every spent group proven (warm), and warm after 1% of the proven
// groups got a backdated QC row (those are classified again). Local timings of
// a disposable PostgreSQL with default settings: not evidence for a runner.
import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'
import { openRuntime } from '../tests/cp7/families/f04/runtime.mjs'
import { AT } from '../tests/cp7/families/f04/supply-exhausted-fixture.mjs'
import { installProofControls, proofBase } from '../tests/cp7/families/f04/supply-proofs-fixture.mjs'
const out = process.argv[2] ?? 'test-results/cp7-shell-proof/PL8_EXHAUSTION_PROOFS.json'
const ladder = (process.argv[3] ?? '1000x1,5000x1,1000x3,5000x3').split(',').map(x => x.split('x').map(Number))
const db = await openRuntime({ commandTimeoutMs: 600_000 })
const report = { contract: 'cp7.pl8.exhaustion-proofs.v1', predecessor: proofBase, synthetic: 'PL8_SYNTHETIC_CLONES_NOT_FACTORY_DATA', evidence: 'LOCAL_TIMING_NOT_EVIDENCE', rows: [], status: 'INCOMPLETE', production_go: false }
try {
  await installProofControls(db)
  await db.execute(`create function public.sp_bench_source(p_at timestamptz,p_old boolean)returns jsonb language plpgsql as $$
   declare t0 timestamptz;v jsonb;s text:='NO_ERROR';
   begin
    t0:=clock_timestamp();
    begin if p_old then v:=cp7_supply_native.wip_source_at_1(p_at);else v:=cp7_supply_native.wip_source_at(p_at);end if;
    exception when others then s:=sqlerrm;end;
    return jsonb_build_object('ms',round(extract(epoch from clock_timestamp()-t0)*1000),'state',s,'exhausted',jsonb_array_length(v->'scope'->'exhausted_cutting_groups'),'text',md5(v::text));
   end $$;
   -- Per-layer cost of one warm source: capture of every batch, slicing and
   -- proof lookup, and the classifier over the groups no proof matched.
   create function public.sp_bench_layers(p_at timestamptz)returns jsonb language plpgsql as $$
   declare ids uuid[];n int;i int:=1;part jsonb;t0 timestamptz;tc numeric:=0;tr numeric:=0;tv numeric:=0;tk numeric;kernel text;r jsonb;hit int:=0;
   begin
    t0:=clock_timestamp();kernel:=cp7_supply_native.proof_kernel();tk:=extract(epoch from clock_timestamp()-t0);
    select array_agg(id order by id)into ids from erp.cutting_groups where material_issue_posted and cut_at<=p_at;n:=cardinality(ids);
    while i<=n loop
     t0:=clock_timestamp();part:=cp7_wip.capture_cutting_sources(ids[i:least(i+49,n)],p_at);tc:=tc+extract(epoch from clock_timestamp()-t0);
     t0:=clock_timestamp();r:=cp7_supply_native.batch_reuse(part,kernel);tr:=tr+extract(epoch from clock_timestamp()-t0);hit:=hit+jsonb_array_length(r->'hit');
     t0:=clock_timestamp();perform cp7_supply_native.batch_verdict(part,kernel);tv:=tv+extract(epoch from clock_timestamp()-t0);
     i:=i+50;
    end loop;
    return jsonb_build_object('kernel_ms',round(tk*1000,1),'capture_ms',round(tc*1000),'slice_hash_lookup_ms',round(tr*1000),'verdict_ms',round(tv*1000),'reused',hit);
   end $$;`)
  for (const [groups, sizes] of ladder) {
    const hist = groups - 40, mix = { direct: Math.floor(hist * 0.6), laundry: Math.floor(hist * 0.3), bs_scrap: Math.floor(hist * 0.05) }
    mix.rework_fg = hist - mix.direct - mix.laundry - mix.bs_scrap
    await db.execute('select public.sx_reset();truncate cp7_supply_native.exhaustion_proofs;')
    for (const [kind, n] of [...Object.entries(mix), ['open', 20], ['partial', 20]]) await db.execute(`select public.sx_seed('${kind}',${n},${sizes});`)
    await db.execute('vacuum analyze;')
    const q = async (sql) => (await db.query(sql))[0].r
    const row = { groups, sizes_per_group: sizes, mix }
    row.predecessor = await q(`select public.sp_bench_source('${AT}',true) r`)
    row.cold = await q(`select public.sp_bench_source('${AT}',false) r`)
    let t0 = Date.now(), after = null, made = 0
    for (;;) {
      const r = await q(`select cp7_supply_native.prove_exhausted('${AT}',${after ? `'${after}'` : 'null'},1000) r`)
      made += r.proofs_added; if (r.done) break; after = r.next_after
    }
    row.prove = { ms_including_client: Date.now() - t0, proofs: made, windows_of_1000: Math.ceil(groups / 1000) }
    await db.execute('vacuum analyze cp7_supply_native.exhaustion_proofs;')
    row.warm = await q(`select public.sp_bench_source('${AT}',false) r`)
    row.warm_layers = await q(`select public.sp_bench_layers('${AT}') r`)
    await db.execute(`select public.sp_mutate('qc_backdated',id,'${AT}') from(select group_id id from cp7_supply_native.exhaustion_proofs order by md5(group_id::text) limit ${Math.ceil(made / 100)})x;`)
    row.warm_1pct_changed = await q(`select public.sp_bench_source('${AT}',false) r`)
    row.predecessor_after_change = await q(`select public.sp_bench_source('${AT}',true) r`)
    row.identical = { cold: row.cold.text === row.predecessor.text && row.cold.state === row.predecessor.state, warm: row.warm.text === row.predecessor.text && row.warm.state === row.predecessor.state,
      changed: row.warm_1pct_changed.text === row.predecessor_after_change.text && row.warm_1pct_changed.state === row.predecessor_after_change.state }
    for (const k of ['predecessor', 'cold', 'warm', 'warm_1pct_changed', 'predecessor_after_change']) delete row[k].text
    row.ms_per_group = { predecessor: +(row.predecessor.ms / groups).toFixed(2), cold: +(row.cold.ms / groups).toFixed(2), warm: +(row.warm.ms / groups).toFixed(2) }
    report.rows.push(row); console.log(JSON.stringify(row))
  }
  report.status = 'COMPLETE'
} finally {
  await db.close(); mkdirSync(dirname(out), { recursive: true }); writeFileSync(out, JSON.stringify(report, null, 1)); console.log(JSON.stringify({ status: report.status, out }))
}

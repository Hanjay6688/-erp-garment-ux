import { readFileSync } from 'node:fs'
import { jsonArg } from './runtime.mjs'
import { PRODUCT, VERIFY_SQL, bounds as stageBounds } from './staged-analysis-fixture.mjs'
import { rng } from './demand-history-fixture.mjs'
import { functionBlocks } from './schedule-scenario-fixture.mjs'
import { productionInput } from './wip-normalize-fixture.mjs'
// P19 phase B: the staged job against the REAL single chain on one runtime:
// history_build (history_events, history_availability, cp7_demand.history),
// cp7_baseline_native.build, cp7_wip.normalize_production, the supply and
// schedule builds, netting, the fabric plan/needs, the accessory needs and the
// analysis compiler (build_operational + finance overlay), plus the job store.
// No stand-in is left in the chain. Captures are generated (never Native ERP
// rows); these are kernel comparisons, never Native/Auth/HTTP qualification.
export const ACTOR = '03000000-0000-4000-8000-000000000001'
export const ACCESS = { actor: ACTOR, profile: { role_code: 'OWNER' } }
export const CAPTURED_AT = '2026-10-07T03:00:00.000000Z'
// The history window: `days` complete WIB days ending the day before capture.
export const query = (days = 30, mode = 'AS_SOLD') => {
  const hi = Date.UTC(2026, 9, 6), lo = hi - (days - 1) * 86400000
  return { from_date: new Date(lo).toISOString().slice(0, 10), through_date: new Date(hi).toISOString().slice(0, 10), group_mode: mode }
}
const read = path => readFileSync(path, 'utf8')
const pick = (text, ...names) => { const all = functionBlocks(text); return names.map(n => { if (!all.has(n)) throw new Error(n); return all.get(n) }).join('\n') }

// Every product function the single analysis build reaches, unchanged.
export function chainSql() {
  const analysis = read('scripts/cp7-src/planning/analysis.sql'), finance = read('scripts/cp7-src/planning/analysis-finance.sql'), jobs = read('scripts/cp7-src/planning/analysis-jobs.sql')
  const runs = analysis.slice(analysis.indexOf('create table cp7_analysis_native.runs('), analysis.indexOf('create function cp7_analysis_native.serve('))
  const jobTables = jobs.slice(jobs.indexOf('create schema cp7_analysis_jobs'), jobs.indexOf('-- The capture compiler'))
  const fabric = read('scripts/cp7-src/planning/fabric-requirements.sql'), material = read('scripts/cp7-src/planning/material-requirements.sql')
  const netting = read('scripts/cp7-src/planning/netting.sql')
  return `create schema if not exists extensions;create extension if not exists pgcrypto schema extensions;
   create schema cp7_private;
   create function cp7_private.immutable_run()returns trigger language plpgsql set search_path='' as $$
    begin raise exception using errcode='55000',message='CP7_RUN_IMMUTABLE';end $$;
   create schema cp7_planning;create schema cp7_baseline_native;create schema cp7_supply_native;create schema cp7_schedule_native;
   create schema cp7_netting_native;create schema cp7_fabric_native;create schema cp7_analysis_native authorization cp7_capture;
   grant usage on schema cp7_private,cp7_planning,cp7_baseline_native,cp7_supply_native,cp7_schedule_native,cp7_netting_native,cp7_fabric_native,extensions to cp7_capture;
   ${read('scripts/cp7-src/wip/graph.sql')}
   ${read('scripts/cp7-src/wip/normalize.sql')}
   ${read('scripts/cp7-src/wip/bs.sql')}
   ${read('scripts/cp7-src/wip/rewash.sql')}
   ${read('scripts/cp7-src/wip/other-normalize.sql')}
   ${read('scripts/cp7-src/wip/yield.sql')}
   ${pick(read('scripts/cp7-src/wip/production.sql'), 'cp7_wip.normalize_production')}
   ${pick(read('scripts/cp7-src/planning/bootstrap.sql'), 'cp7_planning.utc')}
   ${pick(read('scripts/cp7-src/planning/history-source.sql'), 'cp7_planning.history_events')}
   ${pick(read('scripts/cp7-src/planning/history.sql'), 'cp7_planning.history_availability', 'cp7_planning.history_build')}
   ${pick(read('scripts/cp7-src/planning/baseline-source.sql'), 'cp7_baseline_native.build')}
   ${pick(read('scripts/cp7-src/planning/supply-source.sql'), 'cp7_supply_native.fingerprint', 'cp7_supply_native.build')}
   ${pick(read('scripts/cp7-src/planning/schedule.sql'), 'cp7_schedule_native.route', 'cp7_schedule_native.position_model')}
   ${pick(read('scripts/cp7-src/planning/schedule-scenario.sql'), 'cp7_schedule_native.fingerprint', 'cp7_schedule_native.build')}
   ${pick(netting, 'cp7_netting_native.fingerprint', 'cp7_netting_native.bound_product', 'cp7_netting_native.matching_models_within', 'cp7_netting_native.matching_models',
     'cp7_netting_native.matching', 'cp7_netting_native.matches', 'cp7_netting_native.timeline', 'cp7_netting_native.build')}
   ${pick(analysis, 'cp7_analysis_native.fact', 'cp7_analysis_native.fingerprint')}
   ${pick(fabric, 'cp7_fabric_native.material_hash', 'cp7_fabric_native.index', 'cp7_fabric_native.recipe_state', 'cp7_fabric_native.plan', 'cp7_fabric_native.needs')}
   ${pick(material, 'cp7_analysis_native.material_needs')}
   ${pick(analysis, 'cp7_analysis_native.build').replace('create function cp7_analysis_native.build(', 'create function cp7_analysis_native.build_operational(')}
   ${pick(finance, 'cp7_analysis_native.finance_apply', 'cp7_analysis_native.finance_overlay')}
   ${[...functionBlocks(finance)].filter(([name]) => name === 'cp7_analysis_native.build').map(([, b]) => b).join('')}
   ${runs}
   ${jobTables}
   ${pick(jobs, 'cp7_analysis_jobs.original', 'cp7_analysis_jobs.store')}`
}

// The selected schedule over the capture's own normalized WIP, bound to the
// capture's supply fingerprint (as the schedule command records it), and the
// fabric recipe hashes of their materials/patterns. Deterministic per seed.
export const COMPLETE_SQL = `
create function public.ss_pick(seed integer,k text,n integer)returns integer language sql immutable as $$select abs(hashtext(seed::text||'|'||k))%greatest(n,1)$$;
create function public.ss_complete(c jsonb,seed integer,defect text default null)returns jsonb language plpgsql as $s$
declare wip jsonb;positions jsonb;windows jsonb;at timestamptz:=(c->>'captured_at')::timestamptz;through timestamptz;plan jsonb;sel jsonb;fab jsonb;w integer:=coalesce((c->>'test_windows')::integer,30);reviewed boolean:=coalesce((c->>'test_reviewed')::boolean,false);
begin
 begin wip:=cp7_wip.normalize_production(c->'production_sources');exception when others then wip:=jsonb_build_object('positions','[]'::jsonb);end;
 select coalesce(jsonb_agg(jsonb_build_object('position_key',p->'key',
   'target_key',null,
   'eligible_input_pcs',case when defect='SCHEDULE_MISMATCH'and public.ss_pick(seed,p->>'key',3)=0 then to_jsonb(((p->>'remaining_pcs')::numeric+1)::text)else p->'remaining_pcs'end,
   'yield_numerator',case when p->'eligible_company_wip'='true'::jsonb and(reviewed or public.ss_pick(seed,'y'||(p->>'key'),10)<8)then to_jsonb((7+public.ss_pick(seed,'n'||(p->>'key'),4))::text)end,
   'yield_denominator',case when p->'eligible_company_wip'='true'::jsonb and(reviewed or public.ss_pick(seed,'y'||(p->>'key'),10)<8)
     then to_jsonb(case when defect='SCHEDULE_ZERO_DENOMINATOR'then '0'else '10'end)end,
   'remaining_steps',(select jsonb_agg(jsonb_build_object('stage',s.value,'remaining_minutes',
     case when defect='SCHEDULE_NULL_MINUTES'and public.ss_pick(seed,'m'||(p->>'key')||s.value,5)=0 then null
      else to_jsonb((1+public.ss_pick(seed,'m'||(p->>'key')||s.value,12))::text)end)order by s.o)
     from jsonb_array_elements_text(cp7_schedule_native.route(p->>'stage'))with ordinality s(value,o)))order by p->>'key'),'[]')
  into positions from jsonb_array_elements(coalesce(wip->'positions','[]'))p
  where cp7_schedule_native.route(p->>'stage')is not null and p->>'remaining_pcs'~'^[1-9][0-9]*$';
 if defect='SCHEDULE_DUPLICATE'and jsonb_array_length(positions)>0 then positions:=positions||jsonb_build_array(positions->(seed%jsonb_array_length(positions)));end if;
 select jsonb_agg(jsonb_build_object('key','win-'||lpad(i::text,4,'0'),
   'starts_at',cp7_planning.utc(date_trunc('day',at)+make_interval(days=>i,hours=>1)),
   'ends_at',cp7_planning.utc(date_trunc('day',at)+make_interval(days=>i,hours=>23)),
   'other_load_minutes',case when defect='SCHEDULE_OTHER_LOAD'and i%3=0 then '15' when defect='SCHEDULE_NULL_LOAD'and i%4=0 then null else '0'end)order by i)
  into windows from generate_series(case when defect='SCHEDULE_BAD_WINDOW'then -1 else 0 end,w-1)i;
 if defect='SCHEDULE_BAD_WINDOW'then windows:=jsonb_set(windows,'{0,starts_at}','"2026-10-07 01:00"');end if;
 through:=date_trunc('day',at)+make_interval(days=>w+1);
 if defect='SCHEDULE_EXPIRED'then through:=at-interval '1 minute';end if;
 plan:=jsonb_build_object('plan_id','plan-'||seed,'revision',(3+seed%5)::text,
  'source_hash',case when defect='SCHEDULE_SOURCE_CHANGED'then 'other' else cp7_supply_native.fingerprint(c)end,
  'config',jsonb_build_object('basis','SELECTED_ASSUMPTIONS','resource_scope','SINGLE_HOMOGENEOUS_SELECTED_CENTRE','work_centre_key','centre-1',
   'through_at',cp7_planning.utc(through),'unit_minutes',case when defect='SCHEDULE_NO_UNIT'then null else '2.5'end,'windows',windows,'positions',positions));
 -- Fabric recipes carry the hashes of the generated masters (a planted
 -- mismatch stays as generated).
 fab:=c->'fabric_source';
 if fab is not null and jsonb_typeof(fab->'selected')='array'then
  select coalesce(jsonb_agg(case when s->'config'->>'material_hash'='FILL'then jsonb_set(s,'{config,material_hash}',
    coalesce(to_jsonb(cp7_fabric_native.material_hash((select m from jsonb_array_elements(fab->'materials')m where m->>'id'=s->'config'->>'material_id' limit 1))),'"none"'))
    else s end order by o),'[]')into sel from jsonb_array_elements(fab->'selected')with ordinality x(s,o);
  select coalesce(jsonb_agg(case when s->'config'->>'pattern_hash'='FILL'then jsonb_set(s,'{config,pattern_hash}',
    coalesce((select to_jsonb(encode(extensions.digest(convert_to(p::text,'UTF8'),'sha256'),'hex'))from jsonb_array_elements(fab->'patterns')p
     where p->>'id'=s->'config'->>'pattern_id' limit 1),'"none"'))else s end order by o),'[]')into sel from jsonb_array_elements(sel)with ordinality x(s,o);
  c:=jsonb_set(jsonb_set(c,'{fabric_source,selected}',sel),'{fabric_source,versions}',sel);
 end if;
 return (c-'test_windows'-'test_reviewed')||jsonb_build_object('schedule',case when defect='SCHEDULE_UNREVIEWED'then 'null'::jsonb else plan end);
end $s$;`

// ------------------------------------------------------------- generator --
const SIZES = Array.from({ length: 5 }, (_, i) => `00000000-0000-4000-8000-00000000000${i + 1}`)
const hex12 = n => n.toString(16).padStart(12, '0')
const id = (tag, n) => `${tag}-0000-4000-8000-${hex12(n)}`
const iso = ms => new Date(ms).toISOString()
const AT = Date.parse(CAPTURED_AT), DAY = 86400000, HOUR = 3600000
const ref = (kind, x) => ({ kind, id: x, revision: '1' })

// A complete capture of everything the single analysis build reads. Shape:
// targets (one current product per root), days (history window), sales and
// stock rows per target, WIP cutting groups (positions), fabric materials.
// One planted defect (or none) per capture, each aimed at one refusal or one
// edge of the history, baseline, supply/WIP, schedule, netting or fabric kernels.
export function scenarioCapture(seed, { targets = 12, days = 30, sales = 3, stock = 3, groups = 6, origins = null, models = 4, materials = 3, other = true, reviewed = false, horizon = [20, 10] } = {}, defect = null) {
  const r = rng(seed * 7919 + 101), chance = x => r() < x, int = n => Math.floor(r() * n), any = a => a[int(a.length)]
  const q = query(days), lo = Date.parse(`${q.from_date}T00:00:00+07:00`), hi = Date.parse(`${q.through_date}T23:59:59+07:00`)
  const modelPool = Array.from({ length: models }, (_, i) => id('6d000000', seed * 100 + i))
  const products = [], matching = [], stockRows = [], salesRows = [], saleJournals = [], returns = [], returnJournals = []
  let serial = 1
  const next = tag => id(tag, seed * 1000000 + serial++)
  for (let i = 0; i < targets; i++) {
    const root = id('0a000000', seed * 100000 + i), pid = id('0b000000', seed * 100000 + i), size = SIZES[i % SIZES.length], model = any(modelPool)
    const established = iso(lo - (5 + int(40)) * DAY + (chance(0.1) ? (days + 10) * DAY : 0))
    const p = { id: pid, root_id: root, size_id: size, model_id: model, brand_id: `brand-${i % 3}`, sku: `SKU-${seed}-${i}`, product_name: `Produk ${i}`,
      is_active: chance(0.9), effective_from: '2026-01-01T00:00:00+00:00', effective_to: null, created_at: '2025-12-31T00:00:00+00:00', established_at: established,
      commercial: chance(0.6) ? [{ sku_id: id('0c000000', seed * 100000 + i), sku: `C-${i}`, version_id: id('0d000000', seed * 100000 + i), revision: '1' }] : [] }
    products.push(p)
    matching.push({ id: pid, root_id: root, model_id: model, size_id: size, brand_id: p.brand_id, color_name: any(['RED', 'BLUE', 'BLACK']),
      effective_from: '2026-01-01T00:00:00+00:00', effective_to: null, created_at: '2025-12-31T00:00:00+00:00' })
    // Stock: an opening receipt, receipts in the window, sale movements; draft
    // reservations (and a released one) as the Native ledger books them.
    let onHand = 0
    const move = (qty, at, type, extra = {}) => { const m = { id: next('0e000000'), root_id: root, size_id: size, product_id: pid, lot_id: null, location_id: null,
      quality_grade: extra.grade ?? (chance(0.8) ? 'GRADE_A' : 'GRADE_B'), qty_signed: String(qty), physical_at: iso(at), system_created_at: iso(at),
      movement_type: type, source_type: type, source_id: null, reversal_of_id: extra.reversal_of_id ?? null, book_order: String(serial) }; stockRows.push(m); return m }
    const opening = 20 + int(40); onHand += opening; move(opening, lo - (1 + int(20)) * DAY - int(DAY), 'RECEIPT')
    for (let k = 0; k < stock; k++) { const qty = 5 + int(30); onHand += qty; move(qty, lo + int(Math.max(1, days)) * DAY + int(DAY), 'RECEIPT') }
    if (chance(0.15)) move(3, lo + int(days) * DAY, 'RECEIPT', { grade: 'GRADE_C' })
    for (let k = 0; k < sales; k++) {
      const sid = next('0f000000'), header = next('1a000000'), qty = 1 + int(4), at = lo + int(days + 2) * DAY - 2 * DAY + int(DAY)
      const status = chance(0.08) ? 'DRAFT' : chance(0.05) ? 'CANCELLED' : 'POSTED'
      const sale = { id: sid, sale_id: header, root_id: root, size_id: size, product_id: pid, qty_pcs: String(qty), status, revision: String(1 + int(3)),
        sale_date: iso(at), created_at: iso(at), updated_at: iso(at + HOUR), sold_commercial: p.commercial.length && chance(0.8) ? [{ sku_id: p.commercial[0].sku_id, version_id: p.commercial[0].version_id, revision: '1' }] : [] }
      salesRows.push(sale)
      if (status === 'DRAFT') { if (onHand >= qty) { move(-qty, at, 'SALE_RESERVE', { grade: 'GRADE_A' }); onHand -= qty } else sale.status = 'CANCELLED'; continue }
      if (status === 'CANCELLED') continue
      const journal = { id: next('1b000000'), sale_id: header, status: 'POSTED', posting_at: iso(at + (chance(0.05) ? 30 * DAY : HOUR)), transaction_date: iso(at).slice(0, 10), economic_date: iso(at).slice(0, 10), reversal_of_id: null }
      saleJournals.push(journal)
      if (onHand >= qty) { move(-qty, at, 'SALE', { grade: 'GRADE_A' }); onHand -= qty }
      // An inverse journal is linked by reversal_of_id; its own source may be another document.
      if (chance(0.06)) saleJournals.push({ id: next('1b000000'), sale_id: chance(0.5) ? header : null, status: 'POSTED', posting_at: iso(at + 2 * DAY), transaction_date: iso(at + 2 * DAY).slice(0, 10), economic_date: iso(at + 2 * DAY).slice(0, 10), reversal_of_id: journal.id })
      else if (chance(0.1)) {
        const ret = next('1c000000'), back = 1 + int(qty)
        returns.push({ id: next('1d000000'), return_id: ret, sale_id: header, sale_item_id: sid, qty_pcs: String(Math.min(back, qty)), status: 'POSTED', physical_at: iso(at + DAY), created_at: iso(at + DAY) })
        returnJournals.push({ id: next('1e000000'), return_id: ret, status: 'POSTED', posting_at: iso(at + DAY + HOUR), transaction_date: iso(at + DAY).slice(0, 10), economic_date: iso(at + DAY).slice(0, 10), reversal_of_id: null })
      }
    }
    if (chance(0.1)) { const old = move(-2, lo - 3 * DAY, 'SALE_RESERVE', { grade: 'GRADE_A' }); move(2, lo - 2 * DAY, 'RELEASE', { grade: 'GRADE_A', reversal_of_id: old.id }) }
  }
  // Profiles and production policies over the roots (baseline fixture shapes).
  // reviewed: every target fully reviewed (profile, policy, yield), so the
  // global allocation runs and fabric/accessory needs get numbers.
  const config = mode => ({ mean_mode: mode, daily_pcs: mode === 'SELECTED_MANUAL' ? String(1 + int(9)) : null, minimum_available_days: reviewed ? '1' : String(1 + int(Math.max(1, Math.min(days, 20)))),
    lead_days: reviewed || chance(0.9) ? String(1 + int(horizon[0])) : null, review_days: reviewed || chance(0.9) ? String(int(horizon[1])) : null, buffer_days: reviewed || chance(0.7) ? String(int(8)) : null })
  const profiles = []
  products.forEach((p, i) => {
    const kind = reviewed ? 0.5 + r() / 2 : r()
    if (kind < 0.1) { profiles.push({ root_id: p.root_id, product_version_id: p.id, size_id: p.size_id, sku: p.sku, product_name: p.product_name, profile_id: null, revision: '0', config: null, reason: null, recorded_at: null, quality: 'UNREVIEWED' }); return }
    if (kind < 0.15) return
    profiles.push({ root_id: p.root_id, product_version_id: p.id, size_id: p.size_id, sku: p.sku, product_name: p.product_name, profile_id: id('2a000000', seed * 100000 + i),
      revision: String(1 + int(3)), config: config(reviewed || chance(0.3) ? 'SELECTED_MANUAL' : 'OWN_AVAILABLE_HISTORY'), reason: 'uji', recorded_at: '2026-09-20T00:00:00+00:00', quality: kind < 0.2 ? 'PHYSICAL_VERSION_CHANGED' : 'SELECTED_ASSUMPTION' })
  })
  const policyRows = products.map((p, i) => {
    if (!reviewed && chance(0.06)) return { sku_id: id('2b000000', seed * 100000 + i), status: 'UNAVAILABLE' }
    const quality = reviewed || chance(0.85) ? 'KNOWN' : 'UNREVIEWED'
    return { sku_id: id('2b000000', seed * 100000 + i), members: [p.root_id], status: 'AVAILABLE', policy_revision: '1',
      policy: { quality, state: quality === 'KNOWN' ? any(['ACTIVE', 'ACTIVE', 'ACTIVE', 'PAUSED', 'STOPPED']) : null, last_reviewed_state: 'ACTIVE', reason: 'uji', review_at: null, review_due: false, recorded_at: '2026-09-20T00:00:00+00:00' } }
  })
  // Production sources: generated cutting lifecycles and opening WIP; their
  // models and some bound products are this capture's, so netting matches.
  const production = productionInput(seed, { groups, other, ties: false, defect: wipDefect(defect) })
  production.captured_at = '2026-10-07T03:00:00+00:00'
  for (const g of production.facts.cutting.groups) g.model_id = any(modelPool)
  // Bound products: a target's own product (CONFIRMED_TARGET) or a product of
  // another root outside the facts, without a size, with a target's model/brand/colour
  // (CANDIDATE_MATCH, so the allocation has edges).
  const loose = []
  const bind = size => {
    const sized = products.filter(p => p.size_id === size)
    if (!sized.length) return null
    const p = any(sized); if (chance(0.5)) return p.id
    const m = matching.find(x => x.id === p.id), l = { ...m, id: id('2c000000', seed * 100000 + loose.length), root_id: id('2d000000', seed * 100000 + loose.length), size_id: null }
    loose.push(l); return l.id
  }
  // Opening WIP of every size (more bindable positions than the generator's few).
  for (let i = 0, n = origins ?? Math.ceil(targets / 4); i < n; i++) {
    const qty = 2 + int(20)
    production.facts.other.origins.push({ id: id('2e000000', seed * 100000 + i), source_row_id: id('2f000000', seed * 100000 + i), batch_id: id('3d000000', seed), po_id: id('3e000000', seed * 100000 + i),
      size_id: any(SIZES), stage: any(['CUTTING', 'SEWING', 'LAUNDRY', 'QC']), qty_pcs: String(qty), bs_case_id: null, balance_type: 'WIP', opening_qty_pcs: String(qty),
      product_id: null, model_id: null, customer_id: chance(0.1) ? id('3f000000', i) : null, vendor_id: null, contractor_id: null, opening_date: '2026-08-01', header_status: 'POSTED', batch_status: 'POSTED' })
  }
  production.facts.other.origins.sort((a, b) => (a.id < b.id ? -1 : 1))
  for (const o of production.facts.other.origins) { o.model_id = any(modelPool); if (chance(0.7)) o.product_id = bind(o.size_id) }
  for (const b of production.facts.other.bs) if (chance(0.6)) b.product_id = bind(b.size_id)
  matching.push(...loose)
  // Accessory BOM source (material-requirements) and fabric source (fabric-requirements).
  const roots = products.map(p => p.root_id).sort()
  const selected = [], versions = [], items = [], categories = Array.from({ length: 4 }, (_, i) => ({ id: id('3a000000', seed * 10 + i), category_code: `C${i}`,
    category_name: `Kategori ${i}`, base_uom_code: any(['PCS', 'M', 'SET']), is_active: i !== 3, revision: '1' }))
  for (const root of roots) {
    const k = r(), vid = id('3b000000', seed * 100000 + selected.length)
    if (k < 0.1) { selected.push({ root_id: root, effective_version_count: 0, version_id: null }); continue }
    versions.push({ id: vid, product_id: root, effective_from: '2026-01-01T00:00:00+00:00', effective_to: null, is_active: true, created_at: '2026-01-01T00:00:00+00:00' })
    selected.push({ root_id: root, effective_version_count: k < 0.14 ? 2 : 1, version_id: vid })
    if (k < 0.24) continue
    for (let j = 0; j < 1 + int(3); j++) items.push({ id: id('3c000000', seed * 1000000 + items.length), bom_version_id: vid, category_id: any(categories).id, qty_per_good_fg_base: String(1 + int(3)) + (chance(0.3) ? '.25' : '') })
  }
  const material_source = { contract_version: 'cp7.native-material-source.v1', captured_at: '2026-10-07T03:00:00+00:00', scope: 'CURRENT_NATIVE_ACCESSORY_BOM_FOR_NEW_START_EXACT_PHYSICAL_ROOT',
    selected, versions, items, categories, installation_authority: 'NO_NATIVE_BOM_COST_SNAPSHOT_OR_ISSUE_IS_INSTALLATION_PROOF' }
  const mats = Array.from({ length: materials }, (_, i) => ({ id: id('4a000000', seed * 100 + i), material_sku: `F-${i}`, material_name: `Kain ${i}`, unit_code: 'M', material_type: 'FABRIC',
    is_active: i % 5 !== 4, row_version: 1, created_at: '2026-01-01T00:00:00+00:00', cached_stock_qty: 0, moving_average_cost: 0, accessory_category_id: null, updated_at: null }))
  const patterns = [{ id: id('4b000000', seed), pattern_code: 'P1', pattern_name: 'Pola 1', revision: 'R1', is_active: true, row_version: 1, created_at: '2026-01-01T00:00:00+00:00' }]
  const recipes = []
  for (const p of products) if (mats.length && chance(0.55)) {
    const m = any(mats)
    recipes.push({ id: id('4c000000', seed * 100000 + recipes.length), target_key: `${p.root_id}:${p.size_id}`, revision: '1', recorded_at: '2026-09-01T00:00:00+00:00',
      config: { basis: 'SELECTED_ASSUMPTIONS', effective_from: '2026-01-01T00:00:00Z', effective_to: null, material_id: m.id, material_hash: chance(0.93) ? 'FILL' : 'f'.repeat(64),
        unit: chance(0.95) ? 'M' : 'KG', qty_per_good_pcs: String(1 + int(2)) + (chance(0.4) ? '.5' : ''), pattern_id: chance(0.5) ? patterns[0].id : null, pattern_hash: 'FILL' } })
    if (recipes.at(-1).config.pattern_id === null) recipes.at(-1).config.pattern_hash = null
  }
  recipes.sort((a, b) => (a.target_key < b.target_key ? -1 : 1))
  const locs = [{ id: id('5a000000', seed), location_type: 'RAW_MATERIAL_WAREHOUSE', is_active: true }, { id: id('5a000000', seed + 1), location_type: 'CUTTING', is_active: true }]
  const rolls = [], drafts = [], commitments = []
  for (const m of mats) for (let k = 0; k < 1 + int(3); k++) rolls.push({ id: id('5b000000', seed * 1000 + rolls.length), material_id: m.id, status: chance(0.9) ? 'AVAILABLE' : 'HALF_USED',
    consistent: chance(0.97), stock: [{ location_id: locs[chance(0.85) ? 0 : 1].id, qty: String(10 + int(200)) }] })
  rolls.sort((a, b) => (a.id < b.id ? -1 : 1))
  for (let k = 0; k < Math.min(recipes.length, 1 + int(4)); k++) {
    const rc = any(recipes), roll = rolls.find(x => x.material_id === rc.config.material_id) ?? any(rolls)
    if (!roll) break
    drafts.push({ id: id('5c000000', seed * 100 + k), revision: '1', source_location_id: locs[0].id, intents: chance(0.8) ? [{ id: id('5d000000', seed * 100 + k), target_key: rc.target_key }] : [],
      lines: [{ id: id('5e000000', seed * 100 + k), roll_id: roll.id, qty_issued: String(1 + int(9)) }] })
  }
  for (const m of mats) if (chance(0.5)) commitments.push({ id: id('5f000000', seed * 100 + commitments.length), commitment_id: id('6a000000', seed), po_number: `PO-${seed}`, line_number: '1',
    material_id: m.id, location_id: locs[0].id, expected_date: chance(0.8) ? '2026-10-20' : chance(0.5) ? '2026-10-01' : null, remaining: String(5 + int(50)) })
  const fabric_source = { contract_version: 'cp7.fabric-source.v2', captured_at: '2026-10-07T03:00:00+00:00', versions: recipes, selected: recipes, materials: mats, patterns,
    physical: { contract_version: 'cp7.fabric-physical.v1', drafts, rolls, locations: locs, commitments, basis: 'NATIVE_ROLL_STOCK_UNPOSTED_DRAFT_COMPOSITION_AND_OPEN_OPENING_COMMITMENT_NOT_RESERVATION' },
    basis: 'SELECTED_ASSUMPTIONS_NOT_NATIVE_RECIPE_INSTALLATION_OR_ALLOCATION' }
  const financial = seed % 3 === 0 ? null : { contract_version: 'cp7.native-analysis-finance.v1', dates: { from: q.from_date, to: q.through_date, as_of: '2026-10-07' }, book_signature: 'b'.repeat(64), source_hash: 'f'.repeat(64),
    report: { captured_at: CAPTURED_AT, snapshot: { data_confidence: { status: seed % 3 === 1 ? 'READY' : 'RECALC_PENDING' }, basis: { performance_lifecycle_basis: 'POSTED' },
      performance: { sales_revenue_gl: '1250000.00', cogs_gl: '-800000.00', gross_margin_pct: '36.0' }, financial_position: { cash: '125000.50', inventory: '9000000' } } } }
  const c = { contract_version: 'cp7.native-demand-facts.v1', captured_at: CAPTURED_AT, scope: 'GLOBAL_CURRENT_PHYSICAL_ROOTS', status: 'COMPLETE',
    facts: { products, stock: stockRows, sales: salesRows, sale_journals: saleJournals, returns, return_journals: returnJournals },
    profiles, production_policies: { contract_version: 'cp7.production-policy.v1', knowledge_mode: 'CURRENT', generated_at: CAPTURED_AT, rows: policyRows },
    production_sources: production, planning_time_bucket: '2026-10-07T03:00:00.000000Z', matching_products: matching,
    analysis_engine_signature: 'e'.repeat(64), material_source, fabric_source, financial_source: null, financial_capture:'DEFERRED', test_reviewed: reviewed }
  plantScenarioDefect(c, r, defect, q)
  return { c, q }
}

// One planted fault per capture. History/baseline/supply defects change the
// facts; schedule defects are applied by ss_complete; QUERY_* change the job query.
export const SCENARIO_DEFECTS = {
  history: ['CAPTURE_INCOMPLETE', 'BAD_CAPTURED_AT', 'CAPTURED_BEFORE_WINDOW', 'DUP_PRODUCT', 'NULL_SIZE', 'BAD_SALE_DATE', 'BAD_POSTING_AT', 'BAD_STOCK_TIME', 'BAD_STOCK_QTY',
    'STOCK_DUP_ID', 'SALE_EXACT_TWIN', 'LINEAGE_TWIN_ROOT', 'DRAFT_BAD_REVISION', 'DUP_PRODUCT_RETURN_OVER',
    'BAD_ESTABLISHED', 'RESERVATION_MISMATCH', 'TWO_ORIGINAL_JOURNALS', 'SALE_UNKNOWN_TARGET', 'RETURN_OVER_QTY', 'DRAFT_TWIN', 'NEGATIVE_PHYSICAL', 'QUERY_GROUP_MODE', 'QUERY_RESTATED', 'DUP_ROOT_SIZES', 'NO_PRODUCTS'],
  baseline: ['PROFILE_REPEAT', 'PROFILES_SCALAR', 'PROFILE_BAD_LEAD', 'PROFILE_ZERO_MIN_DAYS', 'PROFILE_BAD_MANUAL', 'POLICIES_OBJECT', 'POLICY_OVERLAP'],
  supply: ['WIP_NEGATIVE_QC', 'WIP_OVER_QC', 'WIP_FACTS_NOT_ARRAY', 'WIP_NULL_BS_ID', 'WIP_BAD_TIMESTAMP', 'WIP_INCOMPLETE', 'WIP_OTHER_REWORK_SOURCE'],
  schedule: ['SCHEDULE_DUPLICATE', 'SCHEDULE_SOURCE_CHANGED', 'SCHEDULE_UNREVIEWED', 'SCHEDULE_EXPIRED', 'SCHEDULE_MISMATCH', 'SCHEDULE_NULL_MINUTES', 'SCHEDULE_ZERO_DENOMINATOR',
    'SCHEDULE_NO_UNIT', 'SCHEDULE_OTHER_LOAD', 'SCHEDULE_NULL_LOAD', 'SCHEDULE_BAD_WINDOW'],
  netting: ['MISSING_MATCHING_PRODUCT', 'DUP_MATCHING_PRODUCT', 'BOUND_SIZE'],
  fabric: ['FABRIC_BAD_RATE', 'FABRIC_NO_PHYSICAL', 'ACCESSORY_DUP_SELECTED', 'MATERIAL_SOURCE_SCALAR'],
}
const WIP_DEFECT = { WIP_NEGATIVE_QC: 'NEGATIVE_QC', WIP_OVER_QC: 'OVER_QC', WIP_FACTS_NOT_ARRAY: 'FACTS_NOT_ARRAY', WIP_NULL_BS_ID: 'NULL_BS_ID', WIP_BAD_TIMESTAMP: 'BAD_TIMESTAMP',
  WIP_INCOMPLETE: 'CAPTURE_INCOMPLETE', WIP_OTHER_REWORK_SOURCE: 'OTHER_REWORK_SOURCE' }
export const wipDefect = defect => WIP_DEFECT[defect] ?? null
function plantScenarioDefect(c, r, defect, q) {
  const f = c.facts, any = a => a[Math.floor(r() * a.length)], int = n => Math.floor(r() * n)
  const posted = f.sales.filter(s => s.status === 'POSTED'), p = f.products.length ? any(f.products) : null
  switch (defect) {
    case null: case undefined: return
    case 'CAPTURE_INCOMPLETE': c.status = 'INCOMPLETE'; return
    case 'BAD_CAPTURED_AT': c.captured_at = '2026-10-07 03:00:00'; return
    case 'CAPTURED_BEFORE_WINDOW': c.captured_at = '2026-10-06T03:00:00.000000Z'; return
    case 'DUP_PRODUCT': if (p) f.products.splice(int(f.products.length), 0, { ...p, id: p.id.replace('0b000000', '0b0000ff') }); return
    case 'NULL_SIZE': if (p) p.size_id = null; return
    // Two bad values each, far apart: which one a refusal names depends on the
    // order the single statement reads them in.
    // The row read first in array order belongs to the last chunk (highest
    // sale id / last root): a chunk-wise read would name the other one.
    case 'BAD_SALE_DATE': if (posted.length > 1) { const last = posted.at(-1), js = f.sale_journals.filter(j => j.sale_id === last.sale_id)
      f.sales.splice(f.sales.indexOf(last), 1); f.sales.unshift(last); f.sale_journals = [...js, ...f.sale_journals.filter(j => !js.includes(j))]
      last.sale_date = '2026-13-01T00:00:00Z'; posted[0].sale_date = '2026-12-32T00:00:00Z' } return
    case 'BAD_POSTING_AT': if (f.sale_journals.length) { f.sale_journals.at(-1).posting_at = 'yesterday-ish'; f.sale_journals[0].posting_at = 'tomorrow-ish' } return
    case 'BAD_STOCK_TIME': case 'BAD_STOCK_QTY': { const m = f.stock.filter(x => x.quality_grade !== 'GRADE_C'), last = m.at(-1)
      if (m.length > 1 && last.root_id !== m[0].root_id) { const first = m.find(x => x.root_id === last.root_id); f.stock.splice(f.stock.indexOf(first), 1); f.stock.unshift(first)
        const [k, a, b] = defect === 'BAD_STOCK_TIME' ? ['physical_at', 'not-a-time', 'never'] : ['qty_signed', '1x', '2y']; first[k] = a; m[0][k] = b } } return
    // Legal sources that are not clean (repeated ids): the single path's whole
    // function runs instead of the chunks.
    case 'STOCK_DUP_ID': { const m = f.stock.filter(x => x.quality_grade !== 'GRADE_C'); if (m.length) { const x = any(m); f.stock.push({ ...x, qty_signed: '1' }) } } return
    case 'SALE_EXACT_TWIN': if (posted.length) f.sales.push({ ...any(posted) }); return
    case 'LINEAGE_TWIN_ROOT': if (posted.length && f.products.length > 1) { const s = any(posted), o = f.products.find(x => x.root_id !== s.root_id)
      f.sales.push({ ...s, sale_id: 'ffffffff-0000-4000-8000-0000000000aa', root_id: o.root_id, size_id: o.size_id, product_id: o.id, status: 'DRAFT', revision: '7' }) } return
    case 'DRAFT_BAD_REVISION': { const d = f.sales.find(x => x.status === 'DRAFT' || x.status === 'CANCELLED') ?? (f.sales.length ? Object.assign(any(f.sales), { status: 'CANCELLED' }) : null); if (d) d.revision = 'r2' } return
    case 'BAD_ESTABLISHED': if (p) p.established_at = 'not-established'; if (f.products.length > 3) f.products[1].established_at = 'also-bad'; return
    case 'RESERVATION_MISMATCH': if (p) f.stock.push({ ...f.stock.find(m => m.root_id === p.root_id), id: 'ffffffff-0000-4000-8000-000000000001', qty_signed: '-1', movement_type: 'SALE_RESERVE', quality_grade: 'GRADE_A' }); return
    case 'TWO_ORIGINAL_JOURNALS': { const s = posted.length ? any(posted) : null; const j = s && f.sale_journals.find(x => x.sale_id === s.sale_id && x.reversal_of_id === null)
      if (j) f.sale_journals.push({ ...j, id: 'ffffffff-0000-4000-8000-000000000002', posting_at: '2026-10-01T00:00:00Z' }) } return
    case 'SALE_UNKNOWN_TARGET': if (posted.length) { const s = any(posted); s.size_id = s.size_id === '00000000-0000-4000-8000-000000000009' ? 'x' : '00000000-0000-4000-8000-000000000009' } return
    case 'RETURN_OVER_QTY': if (f.returns.length) any(f.returns).qty_pcs = '99'; else if (posted.length) { const s = any(posted), j = f.sale_journals.find(x => x.sale_id === s.sale_id)
      if (j) { f.returns.push({ id: 'ffffffff-0000-4000-8000-000000000003', return_id: 'ffffffff-0000-4000-8000-000000000004', sale_id: s.sale_id, sale_item_id: s.id, qty_pcs: '99', status: 'POSTED', physical_at: j.posting_at, created_at: j.posting_at })
        f.return_journals.push({ id: 'ffffffff-0000-4000-8000-000000000005', return_id: 'ffffffff-0000-4000-8000-000000000004', status: 'POSTED', posting_at: j.posting_at, transaction_date: j.transaction_date, economic_date: j.economic_date, reversal_of_id: null }) } } return
    case 'DRAFT_TWIN': { const d = f.sales.find(s => s.status === 'DRAFT') ?? (f.sales.length ? Object.assign(any(f.sales), { status: 'DRAFT' }) : null); if (d) f.sales.push({ ...d, qty_pcs: String(Number(d.qty_pcs) + 1) }) } return
    // A target refusal and an events refusal: the kernel checks targets first.
    case 'DUP_PRODUCT_RETURN_OVER': plantScenarioDefect(c, r, 'DUP_PRODUCT', q); plantScenarioDefect(c, r, 'RETURN_OVER_QTY', q); return
    case 'NEGATIVE_PHYSICAL': if (p) f.stock.push({ ...f.stock.find(m => m.root_id === p.root_id), id: 'ffffffff-0000-4000-8000-000000000006', qty_signed: '-100000', movement_type: 'ADJUST', quality_grade: 'GRADE_B', physical_at: '2026-10-07T00:00:00Z' }); return
    case 'QUERY_GROUP_MODE': q.group_mode = 'SOLD'; return
    case 'QUERY_RESTATED': q.group_mode = 'RESTATED'; return
    case 'DUP_ROOT_SIZES': for (const x of f.products.slice(0, 3)) { const sz = SIZES.find(s => s !== x.size_id); f.products.push({ ...x, id: x.id.replace('0b000000', '0b0000ee'), size_id: sz })
      c.matching_products.push({ ...c.matching_products.find(m => m.id === x.id), id: x.id.replace('0b000000', '0b0000ee'), size_id: sz }) } return
    case 'NO_PRODUCTS': f.products = []; return
    case 'PROFILE_REPEAT': { const pr = c.profiles.find(x => x.config) ?? c.profiles[0]; if (pr) c.profiles.push({ ...pr, quality: 'IDENTITY_CONFLICT' }) } return
    case 'PROFILES_SCALAR': c.profiles = 'none'; return
    case 'PROFILE_BAD_LEAD': { const pr = c.profiles.find(x => x.quality === 'SELECTED_ASSUMPTION'); if (pr) pr.config.lead_days = 'x' } return
    case 'PROFILE_ZERO_MIN_DAYS': { const pr = c.profiles.find(x => x.quality === 'SELECTED_ASSUMPTION'); if (pr) pr.config.minimum_available_days = '0' } return
    case 'PROFILE_BAD_MANUAL': { const pr = c.profiles.find(x => x.quality === 'SELECTED_ASSUMPTION'); if (pr) Object.assign(pr.config, { mean_mode: 'SELECTED_MANUAL', daily_pcs: '-1' }) } return
    case 'POLICIES_OBJECT': c.production_policies.rows = { x: 1 }; return
    case 'POLICY_OVERLAP': if (p) c.production_policies.rows.unshift({ sku_id: 'odd', members: [p.root_id], status: 'AVAILABLE', policy: { quality: 'KNOWN', state: 'STOPPED' } }); return
    case 'MISSING_MATCHING_PRODUCT': if (c.matching_products.length) c.matching_products.splice(int(c.matching_products.length), 1); return
    case 'DUP_MATCHING_PRODUCT': { const o = c.production_sources.facts.other.origins.find(x => c.matching_products.some(m => m.id === x.product_id))
      const m = o ? c.matching_products.find(x => x.id === o.product_id) : any(c.matching_products); if (m) c.matching_products.push({ ...m, color_name: 'GREEN' }) } return
    case 'BOUND_SIZE': { const o = c.production_sources.facts.other.origins.find(x => c.matching_products.some(m => m.id === x.product_id))
      if (o) c.matching_products.find(x => x.id === o.product_id).size_id = SIZES[4] } return
    case 'FABRIC_BAD_RATE': if (c.fabric_source.selected.length) c.fabric_source.selected[0].config.qty_per_good_pcs = '1,5'; return
    case 'FABRIC_NO_PHYSICAL': delete c.fabric_source.physical; return
    case 'ACCESSORY_DUP_SELECTED': if (c.material_source.selected.length) c.material_source.selected.push({ ...c.material_source.selected[0], effective_version_count: 1, version_id: 'none' }); return
    case 'MATERIAL_SOURCE_SCALAR': c.material_source.selected = 'x'; return
    default:
      if (wipDefect(defect) || defect.startsWith('SCHEDULE_')) return
      throw new Error(`unknown defect ${defect}`)
  }
}

// ------------------------------------------------------------ the runtime --
export { PRODUCT }
export async function installScenarioControls(db, { bounds = null } = {}) {
  await db.execute(chainSql())
  await db.execute(`${COMPLETE_SQL}
   ${read(PRODUCT)}
   ${bounds ? stageBounds(bounds) : ''}
   ${VERIFY_SQL}
   ${SCENARIO_RESULT_SQL}
   ${COMPARE_SQL}`)
}
// A deliberately wrong product function (one text replacement that must
// apply exactly once), installed over the right one; restore() puts it back.
export async function applyMutant(db, [name, from, to]) {
  const block = functionBlocks(read(PRODUCT)).get(name)
  if (!block || block.split(from).length !== 2) throw new Error(`mutant on ${name} no longer applies: ${from}`)
  await db.execute(block.replace(from, to).replace(`create function ${name}(`, `create or replace function ${name}(`))
  return async () => db.execute(block.replace(`create function ${name}(`, `create or replace function ${name}(`))
}

// The staged job and the single chain on one capture, one call: the job
// (every unit, in order), then the single schedule build (scenario parity),
// the single netting build and the single analysis build with the job's run
// id; refusals as sqlstate + message. Only compact verdicts leave the server.
const SCENARIO_RESULT_SQL = `create function public.ss_scenario_result(p_job uuid)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare j cp7_analysis_stage.jobs%rowtype;c jsonb;g jsonb;val jsonb;demand jsonb;h jsonb;base jsonb;supply jsonb;s jsonb;
begin
 select *into j from cp7_analysis_stage.jobs where id=p_job;
 select reference into c from cp7_analysis_stage.jobs where id=p_job;
 g:=cp7_analysis_stage.output(p_job,'HIST_PREP');val:=cp7_analysis_stage.output(p_job,'HIST_VALIDATE');
 demand:=jsonb_build_object('contract_version','cp7.demand-result.v1','kernel_version','demand-1','snapshot_id',g->>'hash','scope_id','GLOBAL_CURRENT_PHYSICAL_ROOTS',
  'known_as_of',to_jsonb(c->>'captured_at'),'effective_as_of',to_jsonb(c->>'captured_at'),'from_date',j.query->'from_date','through_date',j.query->'through_date',
  'status','CAPTURE_COMPLETE','group_mode',j.query->'group_mode',
  'rows',(select coalesce(jsonb_agg(x.payload order by x.ord),'[]')from cp7_analysis_stage.target_rows x where x.job_id=p_job and x.kind='HIST'),
  'group_events',(select coalesce(jsonb_agg(e.value order by o.idx,e.o),'[]')from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
    cross join lateral jsonb_array_elements(o.output->'group_events')with ordinality e(value,o)where o.job_id=p_job and y.kind='HIST_EVENTS'),
  'selected_events',(select coalesce(jsonb_agg(e.value order by o.idx,e.o),'[]')from cp7_analysis_stage.outputs o join cp7_analysis_stage.units y using(job_id,idx)
    cross join lateral jsonb_array_elements(o.output->'selected_events')with ordinality e(value,o)where o.job_id=p_job and y.kind='HIST_EVENTS'),
  'reason','POSTED_ONCE_RETURNS_SEPARATE_DRAFT_RESERVED_CENSORED_NOT_ZERO');
 h:=jsonb_build_object('contract_version','cp7.native-demand-history.v1','scope','GLOBAL_CURRENT_PHYSICAL_ROOTS',
  'capture_complete',true,'captured_at',c->'captured_at','source_hash',g->>'hash','history',demand,
  'current_stock',(select coalesce(jsonb_agg(x.payload order by x.ord),'[]')from cp7_analysis_stage.target_rows x where x.job_id=p_job and x.kind='STOCK'),
  'availability_knowledge_basis','CURRENT_CAPTURE_RESTATED_LEDGER',
  'training_known_at',c->'captured_at','model_eligibility','HISTORICAL_AVAILABILITY_KNOWLEDGE_NOT_BACKFILLED',
  'versions',jsonb_build_object('producer','native-demand-1','history','demand-1','availability','availability-1'),
  'production_go',false);
 base:=jsonb_build_object('contract_version','cp7.native-baseline.v1','captured_at',c->>'captured_at',
  'source_hash',g->>'baseline_hash','scope','GLOBAL_CURRENT_PHYSICAL_ROOTS','history_run_result',h,
  'rows',(select coalesce(jsonb_agg(x.payload order by x.ord),'[]')from cp7_analysis_stage.target_rows x where x.job_id=p_job and x.kind='BASE'),
  'target_basis','DAYS_WITH_SELECTED_PROFILE_ASSUMPTIONS','apply_enabled',false,
  'model_basis','BASELINE_ADAPTIVE_PROMOTION_NOT_PROVEN','production_go',false);
 supply:=cp7_analysis_stage.output(p_job,'SUPPLY')||jsonb_build_object('baseline_run_result',base);
 s:=cp7_analysis_stage.output(p_job,'SCENARIO')->'scenario';
 return s||jsonb_build_object('supply_run_result',supply);
end $$;`;

const COMPARE_SQL = `
create function public.ss_single(c jsonb,q jsonb,p_run uuid,a jsonb)returns jsonb language plpgsql as $s$
declare r jsonb;begin r:=cp7_analysis_native.build(c||'{}'::jsonb,q,p_run,a);
 return jsonb_build_object('state','DONE','body',r);
exception when others then return jsonb_build_object('state','REFUSED','sqlstate',sqlstate,'message',sqlerrm);end $s$;
create function public.ss_try(fn text,c jsonb,q jsonb)returns jsonb language plpgsql as $s$
declare r jsonb;begin execute format('select %s($1,$2)',fn)into r using c||'{}'::jsonb,q;return jsonb_build_object('state','DONE','body',r);
exception when others then return jsonb_build_object('state','REFUSED','sqlstate',sqlstate,'message',sqlerrm);end $s$;
create function public.ss_case(c jsonb,q jsonb,p_request uuid,p_access jsonb)returns jsonb language plpgsql as $s$
declare job uuid;st jsonb;single jsonb;sched jsonb;n jsonb;rid uuid;g jsonb;staged_rows jsonb;staged_matches jsonb;staged_alloc jsonb;result jsonb;ek jsonb;
 failed_kind text;scenario jsonb;fab jsonb;ver jsonb;
begin
 job:=cp7_analysis_stage.create_job((p_access->>'actor')::uuid,p_request,q,p_access,c);
 loop st:=cp7_analysis_stage.step(job);exit when st->>'state'<>'RUNNING';end loop;
 select run_id into rid from cp7_analysis_stage.jobs where id=job;
 select u.kind into failed_kind from cp7_analysis_stage.jobs j join cp7_analysis_stage.units u on u.job_id=j.id and u.idx=j.failure_unit where j.id=job;
 single:=public.ss_single(c,q,rid,p_access);
 sched:=public.ss_try('cp7_schedule_native.build',c,q);
 if st->>'state'='DONE'or exists(select 1 from cp7_analysis_stage.outputs o join cp7_analysis_stage.units u using(job_id,idx)where o.job_id=job and u.kind='SCENARIO')then
  scenario:=public.ss_scenario_result(job);
 end if;
 n:=public.ss_try('cp7_netting_native.build',c,q)->'body';
 ver:=public.sv_verify(job,case when single->>'state'='DONE'then single->'body'end);
 result:=single->'body';
 select coalesce(jsonb_agg(x.payload order by x.ord),'[]')into staged_rows from cp7_analysis_stage.target_rows x where x.job_id=job and x.kind='NETROW';
 g:=cp7_analysis_stage.output(job,'NET_PREP');
 select jsonb_agg(x->'key'order by o)into ek from jsonb_array_elements(g->'eligible')with ordinality e(x,o);
 select coalesce(jsonb_agg(jsonb_build_object('position_key',ek->(y.i-1),'target_key',g->'row_target_keys'->(q.o::integer-1),'result',q.v)order by y.i,q.o),'[]')
  into staged_matches from cp7_analysis_stage.pair_rows y cross join lateral jsonb_array_elements(y.pair_row)with ordinality q(v,o)where y.job_id=job;
 staged_alloc:=coalesce(nullif(cp7_analysis_stage.output(job,'ALLOC_FINAL'),'null'),nullif(cp7_analysis_stage.output(job,'NET_PLAN')->'alloc','null'),nullif(g->'alloc','null'));
 if n is not null and st->>'state'='DONE'then fab:=public.ss_try('cp7_fabric_native.plan',c,n);end if;
 return jsonb_build_object('job',st->>'state','failure',case when st->>'state'='FAILED'then (st->'failure')||jsonb_build_object('message',(select failure_message from cp7_analysis_stage.jobs where id=job))end,'failed_kind',failed_kind,
  'single',single->>'state','single_sqlstate',single->>'sqlstate','single_message',single->>'message',
  'same',ver->'same','bytes',ver->'analysis_bytes','text_same',ver->'text_same','document_same',ver->'document_same','bad',ver->'bad',
  'scenario_state',sched->>'state','scenario_sqlstate',sched->>'sqlstate','scenario_message',sched->>'message',
  'scenario_same',scenario::text=(sched->'body')::text,
  'netting_rows_same',staged_rows::text=coalesce(n->'rows','[]')::text,
  'match_results_same',case when g->'wip_complete'='true'::jsonb then staged_matches::text=coalesce(n->'match_results','[]')::text else n->'match_results'is null end,
  'allocation_same',case when jsonb_typeof(staged_alloc)='object'and jsonb_typeof(n->'allocation')='object'then(staged_alloc-'inputs')::text=((n->'allocation')-'inputs')::text else false end,
  'fabric_plan_same',case when fab->>'state'='DONE'then(cp7_analysis_stage.output(job,'FABRIC_PLAN')->'plan')::text=(fab->'body')::text end,
  'allocation',n->'allocation'->>'status','edges',coalesce(jsonb_array_length(n->'allocation'->'allocation'->'edges'),0),
  'confirmed',coalesce(jsonb_array_length(jsonb_path_query_array(n,'$.match_results[*] ? (@.result.match == "CONFIRMED_TARGET")')),0),
  'candidates',coalesce(jsonb_array_length(jsonb_path_query_array(n,'$.match_results[*] ? (@.result.match == "CANDIDATE_MATCH")')),0),
  'fabric_numbers',coalesce(jsonb_array_length(jsonb_path_query_array(result,'$.material_needs[*] ? (@.additional_external.state == "ASSUMED")')),0),
  'accessory_rows',coalesce(jsonb_array_length(jsonb_path_query_array(result,'$.material_needs[*] ? (@.material_key starts with "ACCESSORY")')),0),
  'recommendations',jsonb_array_length(result->'recommendations'),'rows',jsonb_array_length(staged_rows),
  'history_rows',(select count(*)from cp7_analysis_stage.target_rows x where x.job_id=job and x.kind='HIST'),
  'events_clean',cp7_analysis_stage.output(job,'HIST_PREP')->'events_clean','availability_clean',cp7_analysis_stage.output(job,'HIST_PREP')->'availability_clean',
  'units',(select jsonb_object_agg(k,v)from(select kind k,count(*)v from cp7_analysis_stage.units where job_id=job group by 1)u));
end $s$;`

// Runs a job to its end (as runJob in staged-analysis-fixture), with a query.
export async function runScenarioJob(db, c, q, { request, oneCallPerUnit = false, timeout = '8s', onStep = null } = {}) {
  const [{ job }] = await db.query(`select cp7_analysis_stage.create_job('${ACTOR}','${request}',${jsonArg(q)},${jsonArg(ACCESS)},${jsonArg(c)}) job`)
  if (!oneCallPerUnit) {
    await db.execute(`do $d$declare s jsonb;begin loop s:=cp7_analysis_stage.step('${job}');exit when s->>'state'<>'RUNNING';end loop;end $d$;`)
  } else {
    for (let k = 0; k < 100000; k++) {
      const t0 = Date.now()
      const out = await db.execute(`set statement_timeout='${timeout}';select cp7_analysis_stage.step('${job}')::text;`)
      const status = JSON.parse(String(out).trim().split('\n').at(-1))
      if (onStep) await onStep(status, Date.now() - t0)
      if (status.state !== 'RUNNING') break
    }
  }
  const [state] = await db.query(`select cp7_analysis_stage.status('${job}') s, (select run_id from cp7_analysis_stage.jobs where id='${job}') run_id`)
  return { job, status: state.s, run_id: state.run_id }
}

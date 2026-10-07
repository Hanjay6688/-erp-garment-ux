import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { rng } from './demand-history-fixture.mjs'
import { functionBlocks } from './schedule-scenario-fixture.mjs'
// cp7_netting_native.build and its helpers before (git) and after (working
// tree) on the runtime's real wip, demand and baseline kernels (match_target,
// check_allocations, net, timeline, allocate) with the real position_model,
// wip.ref and planning utc. Only the Native schedule composition is a stub:
// build reads its scenario (c->'stub_scenario') and dependency hash from c.
export const nettingBase = 'd7548eb80c7f74d7bd1e7c74fc4177102283566a'
const NETTING = 'scripts/cp7-src/planning/netting.sql'
const git = path => execFileSync('git', ['show', `${nettingBase}:${path}`], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 })
const now = path => readFileSync(path, 'utf8')
const pick = (text, ...names) => { const all = functionBlocks(text); return names.map(n => { if (!all.has(n)) throw new Error(n); return all.get(n) }).join('\n') }
const HELPERS = /cp7_netting_native\.(bound_product|matching_models|matching|matches|timeline|build)\(/g
// Every netting helper definition and call, renamed to a suffixed copy.
export const suffixed = (text, suffix) => text.replace(HELPERS, (_, name) => `cp7_netting_native.${name}${suffix}(`)
const helperBlocks = text => [...functionBlocks(text)].filter(([name]) => /^cp7_netting_native\.(bound_product|matching_models|matching|matches|timeline|build)$/.test(name)).map(([, block]) => block)
// Deliberately wrong lookups. Each must still apply to the working tree once.
export const MUTANTS = {
  // match_target is handed the first target's facts for every target.
  TARGET_LOOKUP: ['else cp7_wip.match_target(s,target_at->u.k)end', 'else cp7_wip.match_target(s,target_at->row_keys[1])end'],
  // A position reuses the verdicts of the position before it, not of its leader.
  LEADER_LOOKUP: ['pair_rows:=array_append(pair_rows,pair_rows[leaders[i]]);', 'pair_rows:=array_append(pair_rows,pair_rows[i-1]);'],
  // A target key repeated among matching targets no longer refuses.
  REPEATED_TARGET_SILENT: ["if target_repeated?(r->>'target_key')then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;\n  tf:=", '  tf:='],
  // NONPO binding keeps the last captured case instead of the first.
  LAST_NONPO_CASE: ["(array_agg(x order by o))[1] v from jsonb_array_elements(facts->'other'->'bs')", "(array_agg(x order by o desc))[1] v from jsonb_array_elements(facts->'other'->'bs')"],
  // Every open position reads the first target's pair result.
  ROW_INDEX: ["j:=(row_at->>(r->>'target_key'))::integer", 'j:=1'],
}
export async function installNettingControls(db, { mutants = [] } = {}) {
  const head = git(NETTING), tree = now(NETTING)
  const old = suffixed(helperBlocks(head).join('\n'), '_0')
  if (!old.includes('cp7_netting_native.build_0(') || /cp7_netting_native\.(bound_product|matching|matches|timeline)\(/.test(old)) throw new Error('predecessor helpers not renamed')
  const fresh = helperBlocks(tree).join('\n')
  const variants = mutants.map(name => {
    const [from, to] = MUTANTS[name]
    if (fresh.split(from).length !== 2) throw new Error(`mutant ${name} no longer applies`)
    return suffixed(fresh.replace(from, to), `_m_${name.toLowerCase()}`)
  })
  await db.execute(`create schema if not exists extensions;create extension if not exists pgcrypto schema extensions;
   create schema cp7_planning;create schema cp7_schedule_native;create schema cp7_netting_native;
   create function cp7_schedule_native.fingerprint(c jsonb)returns text language sql immutable as $$select c->>'stub_hash'$$;
   create function cp7_schedule_native.build(c jsonb,q jsonb)returns jsonb language sql immutable as $$select c->'stub_scenario'$$;
   ${pick(now('scripts/cp7-src/wip/normalize.sql'), 'cp7_wip.ref')}
   ${pick(now('scripts/cp7-src/planning/bootstrap.sql'), 'cp7_planning.utc')}
   ${pick(now('scripts/cp7-src/planning/schedule.sql'), 'cp7_schedule_native.position_model')}
   ${pick(tree, 'cp7_netting_native.fingerprint')}
   ${old}
   ${fresh}
   ${variants.join('\n')}
   -- Both builds on one input, each refusal caught as SQLSTATE:message,
   -- under the given plan cache mode (custom plans fold constant arguments).
   create function public.nt_compare(c jsonb,fn text default 'build',mode text default 'auto')returns jsonb language plpgsql as $s$
   declare r0 jsonb;r1 jsonb;s0 text:='NO_ERROR';s1 text:='NO_ERROR';
   begin
    perform set_config('plan_cache_mode',mode,true);
    begin execute 'select cp7_netting_native.build_0($1,$2)'into r0 using c,'{}'::jsonb;
    exception when others then s0:=sqlstate||':'||sqlerrm;end;
    begin execute format('select cp7_netting_native.%s($1,$2)',fn)into r1 using c,'{}'::jsonb;
    exception when others then s1:=sqlstate||':'||sqlerrm;end;
    return jsonb_build_object('s0',s0,'s1',s1,'same',r0::text is not distinct from r1::text,'bytes',octet_length(r0::text),
     'status',r0->>'status','allocation',r0->'allocation'->>'status',
     'matches',(select coalesce(jsonb_object_agg(k,n),'{}')from(select x->'result'->>'match' k,count(*)n
       from jsonb_array_elements(coalesce(r0->'match_results','[]'))x group by 1)f),
     'edges',coalesce(jsonb_array_length(r0->'allocation'->'allocation'->'edges'),0),
     'supplies',(select count(*)from jsonb_array_elements(coalesce(r0->'rows','[]'))x,jsonb_array_elements(coalesce(x->'net'->'inputs'->'supplies','[]'))),
     'supply_events',(select count(*)from jsonb_array_elements(coalesce(r0->'rows','[]'))x,jsonb_array_elements(coalesce(x->'timeline'->'inputs'->'events','[]'))e
       where e->>'kind'='SUPPLY'));
   end $s$;
   -- timeline() called directly, as another caller could: odd ETA arrays too.
   create function public.nt_timeline(v jsonb,mode text default 'auto')returns jsonb language plpgsql as $s$
   declare r0 jsonb;r1 jsonb;s0 text:='NO_ERROR';s1 text:='NO_ERROR';
   begin
    perform set_config('plan_cache_mode',mode,true);
    begin r0:=cp7_netting_native.timeline_0(v->'c',v->'r',v->'etas',v->'edges',v->'matching',v->'wip');
    exception when others then s0:=sqlstate||':'||sqlerrm;end;
    begin r1:=cp7_netting_native.timeline(v->'c',v->'r',v->'etas',v->'edges',v->'matching',v->'wip');
    exception when others then s1:=sqlstate||':'||sqlerrm;end;
    return jsonb_build_object('s0',s0,'s1',s1,'same',r0::text is not distinct from r1::text,'status',r0->>'status',
     'supply_events',(select count(*)from jsonb_array_elements(coalesce(r0->'inputs'->'events','[]'))e where e->>'kind'='SUPPLY'));
   end $s$;`)
}
// One target's timeline inputs: ETAs (some unknown, some late), edges for it
// and for another target, with planted faults in the ETA array.
export function timelineInput(seed, defect = null) {
  const r = rng(seed), int = n => Math.floor(r() * n), chance = x => r() < x
  const at = Date.UTC(2026, 5, 1, 1, 7, 13, 250), hour = 3600000, target = 'root-1:S', positions = 2 + int(8)
  const row = { target_key: target, size_id: 'S', target: { status: chance(0.95) ? 'SCENARIO' : 'UNKNOWN', target_pcs: '10' }, available_fg_pcs: chance(0.9) ? String(int(20)) : '-2',
    profile: { config: { lead_days: String(1 + int(4)), review_days: String(1 + int(3)) } }, demand_estimate: { daily_pcs: (int(500) / 100).toFixed(2) }, refs: [ref('PRODUCT_TARGET', target)] }
  let etas = Array.from({ length: positions }, (_, i) => ({ position_key: `pos-${i}`, at: chance(0.85) ? iso(at + int(200) * hour) : null, refs: [ref('WIP_NODE', `n-${i}`)] }))
  const edges = Array.from({ length: 1 + int(6) }, (_, i) => ({ key: chance(0.5) ? `edge-${i + 1}` : `pos-${int(positions)}`, position_key: `pos-${int(positions)}`,
    target_key: chance(0.8) ? target : 'root-2:M', projected_good_pcs: String(1 + int(9)), refs: [ref('WIP_NODE', `e-${i}`)] }))
  if (defect === 'DUP_ETA') etas.splice(int(etas.length), 0, { ...etas[int(etas.length)] })
  if (defect === 'MISSING_ETA') edges.push({ ...edges[0], key: 'edge-x', position_key: 'nowhere', target_key: target })
  if (defect === 'BAD_AT') etas[int(etas.length)].at = '2026-13-01T00:00:00Z'
  if (defect === 'SCALAR_ETAS') etas = 'x'
  if (defect === 'OBJECT_ETAS') etas = { a: 1 }
  if (defect === 'NULL_ETAS') etas = null
  return { c: { captured_at: iso(at) }, r: row, etas, edges: defect === 'NO_EDGES' ? [] : edges, matching: { snapshot_id: 's' }, wip: { snapshot_id: 's' } }
}
export const TIMELINE_DEFECTS = [null, null, 'DUP_ETA', 'MISSING_ETA', 'BAD_AT', 'SCALAR_ETAS', 'OBJECT_ETAS', 'NULL_ETAS', 'NO_EDGES']

const SIZES = ['S', 'M', 'L', 'XL']
const STAGES = ['CUT_UNASSIGNED', 'SEWING_ACTIVE', 'LAUNDRY_OUTSTANDING', 'AWAIT_QC']
const iso = ms => new Date(ms).toISOString()
const ref = (kind, id) => ({ kind, id, revision: '1' })
const pad = i => String(i).padStart(5, '0')
// A captured Native source and the scenario the schedule stub returns:
// positions of every kind (OPEN, NONPO, CUT, REWORK), bound and unbound, over
// several sizes; products of several models; targets of every review state.
// `defect` plants one fault (or none) so refusals are compared as well.
export function nettingInput(seed, { positions = 16, targets = 8, roots = 4, models = 3, complete = false, defect = null } = {}) {
  const r = rng(seed), any = a => a[Math.floor(r() * a.length)], chance = x => r() < x, int = n => Math.floor(r() * n)
  const at = Date.UTC(2026, 5, 1, 1, 7, 13, 250), hour = 3600000
  const rootList = Array.from({ length: roots }, (_, i) => ({ id: `root-${pad(i)}`, model: `model-${i % models}`, brand: `brand-${i % 3}`, color: any(['RED', 'BLUE', 'BLACK']) }))
  const facts = [], matching = [], loose = []
  const product = (root, size, id = `prd-${root.id}-${size}`, model = root.model) => ({ id, root_id: root.id, model_id: model, size_id: size, brand_id: root.brand,
    color_name: root.color, effective_from: '2026-01-01T00:00:00.000000Z', effective_to: null, created_at: '2025-12-31T00:00:00.000000Z' })
  const add = p => { matching.push(p); facts.push({ id: p.id, root_id: p.root_id, model_id: p.model_id, size_id: p.size_id, name: `${p.root_id} ${p.size_id}` }) }
  for (const root of rootList) for (const size of SIZES) if (chance(0.85)) add(product(root, size))
  // Bindable products outside the facts: no size (CANDIDATE_MATCH sources) or another root.
  for (let i = 0; i < Math.max(2, roots >> 1); i++) { const root = any(rootList); loose.push({ ...product(root, null, `loose-${i}`), size_id: null }) }
  for (let i = 0; i < 2; i++) loose.push(product({ ...any(rootList), id: `root-x${i}` }, any(SIZES), `ext-${i}`))
  matching.push(...loose)
  if (defect === 'MODEL_CONFLICT' && facts.length) add(product(rootList.find(x => x.id === facts[0].root_id), 'XXL', 'prd-conflict', 'model-conflict'))
  if (defect === 'DUP_TARGET_PRODUCT' && facts.length) { const f = any(facts); add({ ...matching.find(p => p.id === f.id), id: `${f.id}-v2` }) }
  if (defect === 'NULL_EFFECTIVE' && facts.length) { const f = any(facts); matching.find(p => p.id === f.id).effective_from = null }
  const groups = Array.from({ length: Math.max(1, Math.ceil(positions / 4)) }, (_, g) => ({ id: `grp-${g}`, model_id: chance(0.8) ? any(rootList).model : null,
    pattern_id: chance(0.5) ? `pat-${g}` : null, pattern_revision_snapshot: chance(0.7) ? String(1 + int(3)) : null }))
  const origins = [], otherBs = [], otherRw = [], cutBs = [], cutRw = [], wip = [], etas = [], bound = []
  for (let i = 0; i < positions; i++) {
    const kind = any(['OPEN', 'OPEN', 'NONPO', 'NONPO', 'CUT', 'CUT', 'REWORK']), size = any(SIZES)
    const sized = matching.filter(p => p.size_id === size), to = sized.length && chance(0.7) ? any(sized) : null
    let key = `pos-${pad(i)}`, pool, stage = any(STAGES)
    if (kind === 'OPEN') {
      const id = to?.id ?? (chance(0.6) ? any(loose.filter(p => p.size_id === null)).id : null)
      origins.push({ id: `org-${i}`, product_id: id, model_id: chance(0.85) ? (to?.model_id ?? any(rootList).model) : null }); pool = `OPEN:org-${i}`
    } else if (kind === 'NONPO') {
      otherBs.push({ id: `bs-${i}`, product_id: to?.id ?? (chance(0.5) ? `missing-${i}` : null) }); pool = `NONPO:bs-${i}`
    } else {
      pool = `CUT:${any(groups).id}:${size}`
      if (kind === 'REWORK') {
        stage = 'REWORK'; key = `RW:rw-${i}:${pad(i)}`
        const caseId = chance(0.5) ? `cbs-${i}` : `bs-rw-${i}`
        ;(chance(0.5) ? cutRw : otherRw).push({ id: `rw-${i}`, bs_case_id: chance(0.9) ? caseId : 'nowhere' })
        ;(caseId.startsWith('cbs') ? cutBs : otherBs).push({ id: caseId, product_id: to?.id ?? null })
      }
    }
    const remaining = chance(0.08) ? '0' : String(1 + int(40)), eligible = chance(0.88)
    let projection = { quality: 'UNKNOWN', reason: 'YIELD_NOT_SELECTED' }
    if (eligible && (complete || chance(0.9))) {
      const den = 1 + int(10), num = Math.min(den, 1 + int(den + 1)), qty = Number(remaining) - (chance(0.2) ? Math.min(Number(remaining), int(3)) : 0)
      projection = { position_key: key, eligible_input_pcs: String(qty), numerator: String(num), denominator: String(den), basis: 'ASSUMED', assumption_id: 'plan-1',
        refs: [ref('WIP_NODE', `n-${seed}-${i}`), ref('PLANNING_SCHEDULE', 'plan-1')], quality: 'SCENARIO', projected_good_pcs: String(Math.floor(qty * num / den)),
        expected_loss_pcs: String(qty - Math.floor(qty * num / den)), not_actual_bs: true }
    }
    const p = { key, pool_key: pool, stage, refs: [ref('WIP_NODE', `n-${seed}-${i}`)], size_id: size, ownership: eligible ? 'COMPANY' : 'CUSTOMER',
      remaining_pcs: remaining, quantity_quality: 'KNOWN', eligible_company_wip: eligible, projection }
    wip.push(p); if (to && kind !== 'CUT') bound.push([p, to])
    if (remaining !== '0') {
      const status = defect === 'UNKNOWN_ETAS' ? 'UNKNOWN' : complete || chance(0.94) ? (defect === 'CONDITIONAL' || chance(0.1) ? 'CONDITIONAL' : 'KNOWN') : 'UNKNOWN'
      const eta = status === 'UNKNOWN' ? null : iso(at + (defect === 'LATE_ETAS' ? 400 : 1) * hour * (1 + int(defect === 'LATE_ETAS' ? 60 : 200)))
      etas.push({ position_key: key, target_key: null, result: { status, eta, on_time: null }, refs: [ref('WIP_NODE', `n-${seed}-${i}`), ref('PLANNING_SCHEDULE', 'plan-1')] })
    }
  }
  const pools = new Map()
  for (const p of wip) pools.set(p.pool_key, (pools.get(p.pool_key) ?? 0) + Number(p.remaining_pcs))
  const totals = [...pools].sort(([a], [b]) => (a < b ? -1 : 1)).map(([pool, pcs]) => ({ pool_key: pool, size_id: pool.split(':')[2] ?? 'S', ownership: 'COMPANY',
    input_pcs: String(pcs), wip_pcs: String(pcs + int(3)), fg_pcs: '0', bs_pcs: '0', withheld_pcs: '0', exited_pcs: '0', refs: [ref('WIP_POOL', pool)] }))
  // Targets: product keys, each once, in a shuffled capture order.
  const keys = facts.map(f => [`${f.root_id}:${f.size_id}`, f]).sort(() => r() - 0.5)
  const rows = []
  for (let t = 0; t < Math.min(targets, keys.length); t++) {
    const [target_key, f] = keys[t]
    const status = complete || chance(0.97) ? 'SCENARIO' : 'UNKNOWN', policy = complete || chance(0.97) ? any(['ACTIVE', 'ACTIVE', 'ACTIVE', 'PAUSED', 'STOPPED']) : null
    rows.push({ target_key, size_id: f.size_id, target: { status, target_pcs: status === 'SCENARIO' ? String(int(90)) : null },
      available_fg_pcs: complete || chance(0.97) ? String(int(30)) : null, profile: { config: { lead_days: String(1 + int(5)) + (chance(0.2) ? '.5' : ''), review_days: String(1 + int(4)) } },
      production_policy: { policy: policy === null ? null : { state: policy } }, demand_estimate: { daily_pcs: chance(0.1) ? null : (int(900) / 100).toFixed(chance(0.5) ? 2 : 0) },
      refs: [ref('PRODUCT_TARGET', target_key)] })
  }
  const known = list => list.filter(p => p.eligible_company_wip)
  // Planted faults. Each leaves the rest of the capture intact.
  const row = () => rows.length ? any(rows) : null, position = () => known(wip).length ? any(known(wip)) : null
  switch (defect) {
    case 'WORK_LIMIT': for (let i = wip.length; i <= 1000; i++) wip.push({ key: `pad-${i}`, eligible_company_wip: false }); break
    case 'MATCH_LIMIT': for (let i = matching.length; i <= 5000; i++) matching.push({ id: `pad-${i}` }); break
    case 'MISSING_PRODUCT': if (facts.length) { const f = any(facts); matching.splice(matching.findIndex(p => p.id === f.id), 1) } break
    case 'DUP_MATCHING_PRODUCT': if (bound.length) { const [, to] = any(bound); matching.push({ ...to }) } break
    case 'DUP_ORIGIN': if (origins.length) { const o = any(origins); origins.splice(int(origins.length), 0, { ...o, product_id: null }) } break
    case 'DUP_GROUP': groups.push({ ...any(groups) }); break
    case 'DUP_BS': { const nonpo = otherBs.filter(b => b.id.startsWith('bs-') && !b.id.startsWith('bs-rw')); if (nonpo.length) { const b = any(nonpo), other = any(loose)
      otherBs.splice(chance(0.5) ? otherBs.indexOf(b) : otherBs.indexOf(b) + 1, 0, { id: b.id, product_id: other.id }) } break }
    case 'NONPO_TWO': { const b = otherBs.find(x => x.product_id && facts.some(f => f.id === x.product_id)); if (b) otherBs.push({ id: b.id, product_id: any(facts).id }) } break
    case 'SIZE': { const b = bound.find(([p, to]) => to.size_id !== null); if (b) b[0].size_id = SIZES.find(s => s !== b[1].size_id) } break
    case 'DUP_POSITION': { const p = position(); if (p) wip.splice(int(wip.length), 0, { ...p, refs: [ref('WIP_NODE', 'twin')] }) } break
    case 'NULL_KEYS': for (let i = 0; i < 2; i++) wip.push({ pool_key: `CUT:grp-null-${i}:S`, stage: 'SEWING_ACTIVE', refs: [ref('WIP_NODE', `null-${i}`)], size_id: 'S', remaining_pcs: '3',
      quantity_quality: 'KNOWN', eligible_company_wip: true, projection: { quality: 'UNKNOWN', reason: 'YIELD_NOT_SELECTED' } }); break
    case 'NUMERIC_KEY': { const p = position(); if (p) { wip.push({ ...p, key: 5 }); p.key = '5' } } break
    case 'DUP_ETA': if (etas.length) etas.splice(int(etas.length), 0, { ...any(etas) }); break
    case 'BAD_ETA': { const e = etas.find(x => x.result.status !== 'UNKNOWN'); if (e) e.result.eta = 'not-a-time' } break
    case 'ORPHAN_ETA': etas.push({ position_key: 'nowhere', target_key: null, result: { status: 'KNOWN', eta: iso(at + hour) }, refs: [ref('WIP_NODE', 'nowhere')] }); break
    case 'DUP_ROW': if (rows.length) rows.splice(int(rows.length), 0, { ...any(rows), refs: [ref('PRODUCT_TARGET', 'twin')] }); break
    case 'MISSING_PROFILE': if (rows.length) delete row().profile; break
    case 'MISSING_POLICY': if (rows.length) row().production_policy = {}; break
    case 'BAD_POLICY': if (rows.length) row().production_policy = { policy: { state: 'DRAFT' } }; break
    case 'UNKNOWN_TARGET': if (rows.length) row().target = { status: 'UNKNOWN', target_pcs: null }; break
    case 'NULL_FG': if (rows.length) row().available_fg_pcs = null; break
    case 'NEG_FG': if (rows.length) row().available_fg_pcs = `-${1 + int(9)}`; break
    case 'BIG_HORIZON': if (rows.length) row().profile.config.lead_days = '4000'; break
    case 'TARGET_NOT_PRODUCT': rows.push({ ...(row() ?? { size_id: 'S', target: { status: 'SCENARIO', target_pcs: '4' }, available_fg_pcs: '1', profile: { config: { lead_days: '2', review_days: '1' } },
      production_policy: { policy: { state: 'ACTIVE' } }, demand_estimate: { daily_pcs: '1' } }), target_key: 'root-none:S', refs: [ref('PRODUCT_TARGET', 'none')] }); break
    case 'BAD_REMAINING': { const p = known(wip).find(x => x.projection.quality === 'SCENARIO' && etas.some(e => e.position_key === x.key && e.result.eta)); if (p) p.remaining_pcs = '1.5' } break
    case 'BAD_POSITION_REFS': if (bound.length) any(bound)[0].refs = []; break
    // Without company work the target lookup is the only scan of the repeat.
    case 'DUP_TARGET_PRODUCT': if (chance(0.5)) for (const p of wip) p.eligible_company_wip = false; break
    case 'SCALAR_ORIGINS': break
    case 'OBJECT_REWORKS': break
    case 'SCALAR_GROUPS': break
  }
  const other = { origins: defect === 'SCALAR_ORIGINS' ? 'x' : origins, bs: otherBs, reworks: defect === 'OBJECT_REWORKS' ? { a: 1 } : otherRw }
  const cutting = { groups: defect === 'SCALAR_GROUPS' ? 7 : groups, bs: cutBs, reworks: defect === 'OBJECT_REWORKS' ? { b: 2 } : cutRw }
  const snapshot = `snap-${seed}`
  return { captured_at: iso(at), stub_hash: `H${seed}`,
    stub_scenario: { contract_version: 'cp7.native-planning-scenario.v1', status: 'SCENARIO',
      schedule_state: defect === 'SOURCE_CHANGED' ? 'SOURCE_CHANGED' : 'SELECTED_ASSUMPTIONS',
      wip: { contract_version: 'cp7.wip-position.v1', status: defect === 'WIP_INCOMPLETE' ? 'INCOMPLETE' : 'COMPLETE', snapshot_id: snapshot,
        positions: defect === 'ZERO_POSITIONS' ? [] : wip, totals },
      etas, capacity: { status: 'SCENARIO', capacity_pcs: String(int(500)) },
      supply_run_result: { baseline_run_result: defect === 'NULL_ROWS' ? {} : { rows: defect === 'ZERO_ROWS' ? [] : rows } } },
    facts: { products: facts }, matching_products: matching,
    production_sources: { facts: { other, cutting } },
    schedule: defect === 'NO_SCHEDULE' ? null : { plan_id: 'plan-1', revision: '4' } }
}
// Pairs are evaluated positions outer, targets inner, each in array order:
// the first position refuses at its second target (duplicate ref) before the
// second position refuses at the first target (non-string key). Swapped, the
// key refusal comes first. A targets-outer order would differ in one of them.
export function orderProbe(swap) {
  const product = (id, root, model) => ({ id, root_id: root, model_id: model, size_id: 'S', brand_id: 'b', color_name: 'c', effective_from: '2026-01-01T00:00:00Z', effective_to: null, created_at: '2026-01-01T00:00:00Z' })
  const a = product('A', 'rA', 'mA'), b = product('B', 'rB', 'mB')
  const position = (key, origin, refs) => ({ key, pool_key: `OPEN:${origin}`, stage: 'SEWING_ACTIVE', refs, size_id: 'S', remaining_pcs: '3', eligible_company_wip: true, projection: { quality: 'UNKNOWN' } })
  const p1 = position('pos-1', 'o1', [{ kind: 'erp.products', id: 'A', revision: '2026-01-01T00:00:00Z' }]), p2 = position(7, 'o2', [ref('W', '2')])
  const row = key => ({ target_key: key, size_id: 'S', target: { status: 'SCENARIO', target_pcs: '5' }, available_fg_pcs: '1', profile: { config: { lead_days: '2', review_days: '1' } },
    production_policy: { policy: { state: 'ACTIVE' } }, demand_estimate: { daily_pcs: '1' }, refs: [ref('T', key)] })
  return { captured_at: '2026-06-01T00:00:00.000Z', stub_hash: 'H',
    stub_scenario: { schedule_state: 'SELECTED_ASSUMPTIONS', wip: { contract_version: 'cp7.wip-position.v1', status: 'COMPLETE', snapshot_id: 's', positions: swap ? [p2, p1] : [p1, p2], totals: [] },
      etas: [], capacity: {}, supply_run_result: { baseline_run_result: { rows: [row('rB:S'), row('rA:S')] } } },
    facts: { products: [a, b] }, matching_products: [a, b],
    production_sources: { facts: { other: { origins: [{ id: 'o1', product_id: 'A', model_id: 'mA' }, { id: 'o2', product_id: 'B', model_id: 'mB' }], bs: [], reworks: [] }, cutting: { groups: [], bs: [], reworks: [] } } },
    schedule: { plan_id: 'p', revision: '1' } }
}
export const DEFECTS = [null, null, null, null, 'WIP_INCOMPLETE', 'WORK_LIMIT', 'MATCH_LIMIT', 'MISSING_PRODUCT', 'DUP_MATCHING_PRODUCT', 'DUP_ORIGIN',
  'DUP_GROUP', 'DUP_BS', 'NONPO_TWO', 'SIZE', 'MODEL_CONFLICT', 'DUP_TARGET_PRODUCT', 'NULL_EFFECTIVE', 'DUP_POSITION', 'NULL_KEYS', 'NUMERIC_KEY',
  'DUP_ETA', 'BAD_ETA', 'ORPHAN_ETA', 'UNKNOWN_ETAS', 'CONDITIONAL', 'LATE_ETAS', 'DUP_ROW', 'MISSING_PROFILE', 'MISSING_POLICY', 'BAD_POLICY',
  'UNKNOWN_TARGET', 'NULL_FG', 'NEG_FG', 'BIG_HORIZON', 'TARGET_NOT_PRODUCT', 'BAD_REMAINING', 'BAD_POSITION_REFS', 'SCALAR_ORIGINS',
  'OBJECT_REWORKS', 'SCALAR_GROUPS', 'SOURCE_CHANGED', 'NO_SCHEDULE', 'ZERO_POSITIONS', 'ZERO_ROWS', 'NULL_ROWS']

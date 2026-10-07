import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { rng } from './demand-history-fixture.mjs'
import { functionBlocks } from './schedule-scenario-fixture.mjs'
// cp7_baseline.allocate before (git) and after (working tree) on the
// runtime's real wip and demand kernels (fields, key, pcs, refs, match_target,
// check_allocations, context, items, instant). Nothing is stubbed.
export const allocationBase = '083c90e30fbbea161705c370a38745d8641675a7'
const ALLOCATION = 'scripts/cp7-src/baseline/allocation.sql'
const git = path => execFileSync('git', ['show', `${allocationBase}:${path}`], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 })
const now = path => readFileSync(path, 'utf8')
const allocateBlock = text => { const all = functionBlocks(text); if (!all.has('cp7_baseline.allocate')) throw new Error('cp7_baseline.allocate'); return all.get('cp7_baseline.allocate') }
export const renamed = (text, suffix) => text.replace('create function cp7_baseline.allocate(', `create function cp7_baseline.allocate${suffix}(`)
// Deliberately wrong shortcuts. Each must still apply to the working tree once.
export const MUTANTS = {
  // A verdict is reused before the pair's own source and target are proven.
  MEMO_WITHOUT_PROOF: ['m:=case when target_proven and proven[o] then verdicts[slot] end;', 'm:=verdicts[slot];'],
  // Sources that differ only in their constraints share verdicts.
  MEMO_WITHOUT_CONSTRAINTS: ["x.s->'confirmed_target'='null'::jsonb,x.s->'constraints')", "x.s->'confirmed_target'='null'::jsonb)"],
  // A source confirmed to this target shares the verdict of one confirmed elsewhere.
  MEMO_WITHOUT_CONFIRMED: ["case when source_confirmed[o]=tf->>'key' then 2 else 1 end", '1'],
  // Targets with different facts share verdicts.
  MEMO_WITHOUT_TARGET: ['slot:=((target_id-1)*sources_n+', 'slot:=((1-1)*sources_n+'],
  // Unknown ETAs come first instead of last.
  ETA_NULLS_FIRST: ["row_number()over(order by x.at nulls last,x.p->>'key')", "row_number()over(order by x.at nulls first,x.p->>'key')"],
  // The pool cap no longer limits a position.
  POOL_CAP_DROPPED: ['room:=least(room,pool_wip[w]-pool_used[w]);', 'room:=room;'],
  // A target key repeated in the targets array no longer refuses.
  REPEATED_TARGET_SILENT: ["if i=repeated or t->>'production_status' is null", "if t->>'production_status' is null"],
  // Ineligible positions join the size lists.
  INELIGIBLE_LISTED: ["where r.p->'eligible_company_wip'<>'false'::jsonb group by 1", 'where true group by 1'],
}
export async function installAllocationControls(db, { mutants = [] } = {}) {
  const old = renamed(allocateBlock(git(ALLOCATION)), '_0')
  if (!old.includes('create function cp7_baseline.allocate_0(')) throw new Error('predecessor not renamed')
  const fresh = allocateBlock(now(ALLOCATION))
  const variants = mutants.map(name => {
    const [from, to] = MUTANTS[name]
    if (fresh.split(from).length !== 2) throw new Error(`mutant ${name} no longer applies`)
    return renamed(fresh.replace(from, to), `_m_${name.toLowerCase()}`)
  })
  await db.execute(`${old}
   ${variants.join('\n')}
   -- Both kernels on one input, each refusal caught as SQLSTATE:message,
   -- under the given plan cache mode (custom plans fold constant arguments).
   create function public.al_compare(v jsonb,fn text default 'allocate',mode text default 'auto')returns jsonb language plpgsql as $s$
   declare r0 jsonb;r1 jsonb;s0 text:='NO_ERROR';s1 text:='NO_ERROR';
   begin
    perform set_config('plan_cache_mode',mode,true);
    begin execute 'select cp7_baseline.allocate_0($1)'into r0 using v;
    exception when others then s0:=sqlstate||':'||sqlerrm;end;
    begin execute format('select cp7_baseline.%s($1)',fn)into r1 using v;
    exception when others then s1:=sqlstate||':'||sqlerrm;end;
    return jsonb_build_object('s0',s0,'s1',s1,'same',r0::text is not distinct from r1::text,'bytes',octet_length(r0::text),
     'status',r0->>'status','reason',r0->>'reason','rows',coalesce(jsonb_array_length(r0->'rows'),0),
     'edges',(select coalesce(jsonb_object_agg(k,n),'{}')from(select x->>'match' k,count(*)n
       from jsonb_array_elements(coalesce(r0->'allocation'->'edges','[]'))x group by 1)f),
     'reviews',(select coalesce(jsonb_object_agg(k,n),'{}')from(select case when jsonb_typeof(x->'reason')='object'then x->'reason'->>'match' else x->>'reason' end k,count(*)n
       from jsonb_array_elements(coalesce(r0->'review_queue','[]'))x group by 1)f));
   end $s$;`)
}

const SIZES = ['S', 'M', 'L']
const ref = (kind, id, revision = '1') => ({ kind, id, revision })
const pad = i => String(i).padStart(4, '0')
const clone = x => structuredClone(x)
// An allocation input over one complete scope: shared pools, positions of
// several sizes (eligible or not, with or without a selected yield, with
// known, unknown or missing ETAs), targets of every time state and both
// production states, and matching facts drawn from a small vocabulary so that
// many sources and targets share facts (the verdict memo) while some differ.
// Arrays are shuffled so array order, key order and priority order differ;
// `ties` collapses instants and needs so the key breaks every tie. `defect`
// plants one fault (or none) so refusals are compared as well.
export function allocationInput(seed, { positions = 12, targets = 8, pools = 4, ties = false, defect = null } = {}) {
  const r = rng(seed), int = n => Math.floor(r() * n), chance = x => r() < x, any = a => a[int(a.length)]
  const shuffle = a => { for (let i = a.length - 1; i > 0; i--) { const j = int(i + 1); [a[i], a[j]] = [a[j], a[i]] } return a }
  const base = Date.UTC(2026, 5, 1, 1, 7, 13), hour = 3600000
  // Equal instants are written either way; both forms are valid UTC instants.
  const when = h => { const s = new Date(base + h * hour).toISOString(); return chance(0.3) ? s : s.replace('.000Z', 'Z') }
  const vocabulary = () => {
    const out = []
    if (chance(0.6)) out.push({ field: 'brand', value: any(['b0', 'b0', 'b1']), required: chance(0.5), basis: 'FACT' })
    if (chance(0.5)) out.push(chance(0.8) ? { field: 'color', value: any(['RED', 'BLUE']), required: chance(0.5), basis: any(['FACT', 'FACT', 'HINT']) }
      : { field: 'color', value: null, required: true, basis: 'UNKNOWN' })
    if (chance(0.15)) out.push({ field: 'material', value: chance(0.8) ? any(['cotton', 'denim']) : null, required: chance(0.5), basis: 'FACT' })
    return out
  }
  const snapshot = `snap-${seed}`
  const poolKeys = Array.from({ length: pools }, (_, j) => `pool-${pad(j)}`)
  const ts = [], tfs = []
  for (let j = 0; j < targets; j++) {
    const key = `tgt-${pad(j)}`, size = any(SIZES)
    const slot = n => ties ? when(48) : when(int(n) * 12)
    ts.push({ key, size_id: size, need_pcs: String(ties ? 20 : int(9) * 5 + (chance(0.5) ? int(5) : 0)), deadline: chance(0.06) ? null : ties ? when(96) : when(24 + int(10) * 12),
      risk_at: chance(0.05) ? null : slot(8), helps_at: chance(0.05) ? null : slot(8), production_status: chance(0.8) ? 'ACTIVE' : 'STOP',
      refs: [ref('PRODUCT_TARGET', key), ref('POLICY', 'plan-1')] })
    tfs.push({ key, size_id: size, constraints: vocabulary(), refs: [ref('PRODUCT_TARGET', key)] })
  }
  for (let j = 0; j < 2; j++) tfs.push({ key: `tgt-x${j}`, size_id: any(SIZES), constraints: vocabulary(), refs: [ref('PRODUCT_TARGET', `tgt-x${j}`)] })
  const ps = [], sources = [], etas = []
  for (let i = 0; i < positions; i++) {
    const key = `pos-${pad(i)}`, size = any(SIZES), remaining = chance(0.08) ? 0 : 1 + int(30), refs = [ref('WIP_NODE', `${seed}-${i}`)]
    let projection = { quality: 'UNKNOWN', reason: 'YIELD_NOT_SELECTED' }
    if (chance(0.85)) {
      const den = 1 + int(6), num = chance(0.08) ? 0 : 1 + int(den), input = Math.max(0, remaining - (chance(0.3) ? int(4) : 0)) + (chance(0.08) ? 3 : 0)
      const most = Math.floor(input * num / den), good = most - (chance(0.2) ? Math.min(int(3), most) : 0)
      projection = { quality: 'SCENARIO', numerator: String(num), denominator: String(den), eligible_input_pcs: String(input), projected_good_pcs: String(good) }
    }
    ps.push({ key, pool_key: any(poolKeys), size_id: size, remaining_pcs: String(remaining), eligible_company_wip: chance(0.87), refs, projection })
    if (chance(0.9)) etas.push({ position_key: key, at: chance(0.12) ? null : ties ? when(24) : when(int(12) * 12), refs: [ref('ETA', key)] })
    const sameSize = ts.filter(t => t.size_id === size)
    const confirmed = chance(0.6) ? null : chance(0.7) && sameSize.length ? any(sameSize).key : chance(0.5) ? any(ts.length ? ts : [{ key: 'tgt-x0' }]).key : 'tgt-elsewhere'
    sources.push({ key, quality: chance(0.85) ? 'COMPLETE' : any(['PARTIAL', 'CONFLICT', 'UNKNOWN']), size_id: size, confirmed_target: confirmed,
      constraints: vocabulary(), refs: chance(0.3) ? [...refs, ref('PRODUCT', `p-${int(4)}`)] : [...refs] })
  }
  for (let j = 0; j < 2; j++) sources.push({ key: `src-x${j}`, quality: 'COMPLETE', size_id: any(SIZES), confirmed_target: null, constraints: [], refs: [ref('WIP_NODE', `x${j}`)] })
  const sums = new Map()
  for (const p of ps) sums.set(p.pool_key, (sums.get(p.pool_key) ?? 0) + Number(p.remaining_pcs))
  const totals = poolKeys.map(k => ({ pool_key: k, wip_pcs: String(Math.max(0, (sums.get(k) ?? 0) - (chance(0.4) ? int(25) : 0))) }))
  // Facts for the planted faults: a valid ETA'd, eligible, yielded position.
  const timed = () => ps.filter(p => p.eligible_company_wip && p.projection.quality === 'SCENARIO' && etas.some(e => e.position_key === p.key && e.at))
  const active = () => ts.filter(t => t.production_status === 'ACTIVE' && t.deadline && t.risk_at && t.helps_at)
  const source = key => sources.find(s => s.key === key), fact = key => tfs.find(f => f.key === key)
  let capacity = chance(0.08) ? '0' : String(chance(0.3) ? int(60) : 200 + int(400))
  const v = { contract_version: 'cp7.allocation-input.v1', snapshot_id: snapshot, scope_id: 'scope-1', scenario_id: `scenario-${seed}`, complete_scope: true,
    positions: { contract_version: 'cp7.wip-position.v1', snapshot_id: snapshot, status: 'COMPLETE', allocation_review_required: false, positions: ps, totals },
    matching: { snapshot_id: snapshot, sources, targets: tfs }, etas, targets: ts, capacity_pcs: capacity, refs: [ref('CAPACITY', 'calendar-1')] }
  const twin = (list, equal) => { for (const a of list) { const b = list.find(x => x !== a && equal(a, x)); if (b) return [a, b] } return null }
  switch (defect) {
    case 'SCOPE_FALSE': v.complete_scope = false; break
    case 'SCOPE_TEXT': v.complete_scope = 'true'; break
    case 'CAPACITY_NULL': v.capacity_pcs = null; break
    case 'CAPACITY_BAD': v.capacity_pcs = '7.5'; break
    case 'CAPACITY_ZERO': v.capacity_pcs = '0'; break
    case 'CAPACITY_TIGHT': v.capacity_pcs = String(1 + int(15)); break
    case 'CONTRACT': v.contract_version = 'cp7.allocation-input.v0'; break
    case 'EXTRA_FIELD': v.extra = 1; break
    case 'SNAPSHOT': v.matching.snapshot_id = 'other'; break
    case 'REVIEW_REQUIRED': v.positions.allocation_review_required = true; break
    case 'WIP_INCOMPLETE': v.positions.status = 'INCOMPLETE'; break
    case 'MATCH_DUPLICATE': sources.splice(int(sources.length), 0, clone(any(sources))); break
    case 'MATCH_KEY': any(tfs).key = 7; break
    case 'ARRAY_LIMIT': for (let i = etas.length; i <= 1000; i++) etas.push({ position_key: `pad-${i}` }); break
    case 'ALLOCATION_LIMIT': for (let i = ps.length; i <= 100; i++) ps.push({ key: `pad-${i}`, remaining_pcs: '0' }); for (let i = ts.length; i < 1000; i++) ts.push({ key: `pad-${i}` }); break
    case 'DUP_POOL': totals.splice(int(totals.length + 1), 0, { ...any(totals) }); break
    case 'POOL_KEY_NUMBER': any(totals).pool_key = 7; break
    case 'BAD_POOL_PCS': any(totals).wip_pcs = '-1'; break
    case 'DUP_POSITION': if (ps.length) { const p = any(ps); ps.splice(int(ps.length + 1), 0, { ...p, refs: [ref('WIP_NODE', 'twin')] }) } break
    case 'UNKNOWN_POOL': if (ps.length) any(ps).pool_key = 'pool-missing'; break
    case 'ELIGIBLE_TEXT': if (ps.length) any(ps).eligible_company_wip = 'yes'; break
    case 'BAD_YIELD': { const p = ps.find(x => x.projection.quality === 'SCENARIO'); if (p) Object.assign(p.projection, chance(0.5) ? { denominator: '0', numerator: '0' } : { numerator: '9', denominator: '4' }) } break
    case 'BAD_PROJECTED': { const p = ps.find(x => x.projection.quality === 'SCENARIO'); if (p) p.projection.projected_good_pcs = 'x' } break
    case 'BAD_POSITION_REFS': if (ps.length) { const p = any(ps); p.refs = chance(0.5) ? [] : [p.refs[0], p.refs[0]] } break
    case 'POSITION_KEY_NUMBER': if (ps.length) any(ps).key = 5; break
    case 'BAD_REMAINING': if (ps.length) any(ps).remaining_pcs = '1.5'; break
    case 'DUP_ETA': if (etas.length) etas.splice(int(etas.length + 1), 0, clone(any(etas))); break
    case 'ORPHAN_ETA': etas.splice(int(etas.length + 1), 0, { position_key: 'nowhere', at: null, refs: [ref('ETA', 'nowhere')] }); break
    case 'BAD_ETA_AT': { const e = etas.find(x => x.at); if (e) e.at = chance(0.5) ? '2026-13-01T00:00:00Z' : '2026-06-01 00:00:00' } break
    case 'ETA_FIELDS': if (etas.length) any(etas).note = 'x'; break
    case 'DUP_TARGET': if (ts.length) ts.splice(int(ts.length + 1), 0, { ...any(ts), refs: [ref('PRODUCT_TARGET', 'twin')] }); break
    case 'BAD_STATUS': if (ts.length) any(ts).production_status = 'PAUSED'; break
    case 'BAD_TARGET_TIME': if (ts.length) any(ts).deadline = '2026-06-01T25:00:00Z'; break
    case 'BAD_NEED': if (ts.length) any(ts).need_pcs = '01'; break
    case 'TARGET_FIELDS': if (ts.length) delete any(ts).helps_at; break
    case 'TARGET_NOT_MATCHED': if (ts.length) { const t = any(ts); tfs.splice(tfs.indexOf(fact(t.key)), 1) } break
    case 'TARGET_FACT_SIZE': if (ts.length) { const f = fact(any(ts).key); f.size_id = SIZES.find(x => x !== f.size_id) } break
    case 'TARGET_FACT_REFS': if (ts.length) fact(any(ts).key).refs = [ref('PRODUCT_TARGET', 'other')]; break
    // An active target with the facts of an earlier one but unprovable refs:
    // it must still refuse at its own first pair.
    case 'TARGET_FACT_TWIN_BAD': { const pair = twin(active(), (a, b) => a.size_id === b.size_id); if (pair) {
      const [a, b] = pair, bad = ref('PRODUCT_TARGET', `dup-${b.key}`); fact(b.key).constraints = clone(fact(a.key).constraints)
      fact(b.key).refs = [bad, bad]; b.refs.push(bad) } break }
    case 'TARGET_FACT_CONSTRAINT': if (ts.length) fact(any(ts).key).constraints = [{ field: 'size', value: 'S', required: true, basis: 'FACT' }]; break
    case 'SOURCE_MISSING': { const list = timed(); if (list.length) sources.splice(sources.indexOf(source(any(list).key)), 1) } break
    case 'SOURCE_QUALITY': { const list = timed(); if (list.length) source(any(list).key).quality = 'MAYBE' } break
    // A position whose source has the facts of another one but invalid refs.
    case 'SOURCE_TWIN_BAD': { const pair = twin(timed(), (a, b) => a.size_id === b.size_id); if (pair) { const [a, b] = pair, sa = source(a.key), sb = source(b.key)
      sa.quality = 'COMPLETE'; Object.assign(sb, { quality: 'COMPLETE', confirmed_target: sa.confirmed_target, constraints: clone(sa.constraints), refs: [sb.refs[0], sb.refs[0]] }) } break }
    case 'SOURCE_CONSTRAINT': { const list = timed(); if (list.length) source(any(list).key).constraints = [{ field: 'brand', value: 'b0', required: 'yes', basis: 'FACT' }] } break
    case 'SOURCE_FIELDS': { const list = timed(); if (list.length) delete source(any(list).key).confirmed_target } break
    case 'SOURCE_SIZE': { const list = timed(); if (list.length) { const s = source(any(list).key); s.size_id = SIZES.find(x => x !== s.size_id) } } break
    // Sources that do not cover their position's refs pass matching but not
    // the final edge check.
    case 'SOURCE_REFS_GAP': for (const p of timed()) source(p.key).refs = [ref('WIP_NODE', `gap-${p.key}`)]; break
    case 'POSITIONS_SCALAR': v.positions.positions = 'x'; break
    case 'TARGETS_OBJECT': v.targets = { a: 1 }; break
    case 'NO_ETAS': etas.length = 0; break
    case 'NO_POSITIONS': ps.length = 0; etas.length = 0; if (chance(0.5)) totals.length = 0; break
    case 'NO_TARGETS': ts.length = 0; break
    case 'ALL_CONFIRMED': for (const p of ps) { const t = ts.filter(x => x.size_id === p.size_id); const s = source(p.key); if (t.length) Object.assign(s, { quality: 'COMPLETE', confirmed_target: any(t).key, constraints: [] }) }
      for (const f of tfs) f.constraints = []; break
    case 'TIGHT_POOLS': for (const pool of totals) pool.wip_pcs = String(int(8)); break
  }
  shuffle(ps); shuffle(etas); shuffle(sources); shuffle(tfs); shuffle(totals)
  if (Array.isArray(v.targets)) shuffle(v.targets)
  return v
}
export const DEFECTS = [null, null, null, null, null, 'CAPACITY_TIGHT', 'CAPACITY_ZERO', 'TIGHT_POOLS', 'ALL_CONFIRMED', 'NO_ETAS', 'NO_POSITIONS', 'NO_TARGETS', 'SOURCE_SIZE',
  'SCOPE_FALSE', 'SCOPE_TEXT', 'CAPACITY_NULL', 'CAPACITY_BAD', 'CONTRACT', 'EXTRA_FIELD', 'SNAPSHOT', 'REVIEW_REQUIRED', 'WIP_INCOMPLETE',
  'MATCH_DUPLICATE', 'MATCH_KEY', 'ARRAY_LIMIT', 'ALLOCATION_LIMIT', 'DUP_POOL', 'POOL_KEY_NUMBER', 'BAD_POOL_PCS', 'DUP_POSITION', 'UNKNOWN_POOL',
  'ELIGIBLE_TEXT', 'BAD_YIELD', 'BAD_PROJECTED', 'BAD_POSITION_REFS', 'POSITION_KEY_NUMBER', 'BAD_REMAINING', 'DUP_ETA', 'ORPHAN_ETA', 'BAD_ETA_AT',
  'ETA_FIELDS', 'DUP_TARGET', 'BAD_STATUS', 'BAD_TARGET_TIME', 'BAD_NEED', 'TARGET_FIELDS', 'TARGET_NOT_MATCHED', 'TARGET_FACT_SIZE', 'TARGET_FACT_REFS',
  'TARGET_FACT_TWIN_BAD', 'TARGET_FACT_CONSTRAINT', 'SOURCE_MISSING', 'SOURCE_QUALITY', 'SOURCE_TWIN_BAD', 'SOURCE_CONSTRAINT', 'SOURCE_FIELDS',
  'SOURCE_REFS_GAP', 'POSITIONS_SCALAR', 'TARGETS_OBJECT']
// Two positions with the same source facts and one target: the first proves
// its source and the target; the second shares their facts but its own source
// (or, with `badTarget`, a second target with the first one's facts) is
// invalid and must refuse at its own pair, not reuse the earlier verdict.
export function memoProbe(variant) {
  const snapshot = 's', at = '2026-06-01T00:00:00Z', due = '2026-06-05T00:00:00Z'
  const position = key => ({ key, pool_key: 'pool', size_id: 'S', remaining_pcs: '5', eligible_company_wip: true, refs: [ref('W', key)],
    projection: { quality: 'SCENARIO', numerator: '1', denominator: '1', eligible_input_pcs: '5', projected_good_pcs: '5' } })
  const target = (key, risk) => ({ key, size_id: 'S', need_pcs: '50', deadline: due, risk_at: risk, helps_at: due, production_status: 'ACTIVE', refs: [ref('T', key), ref('T', `${key}-x`)] })
  const constraints = [{ field: 'brand', value: 'b0', required: true, basis: 'FACT' }]
  const source = (key, refs) => ({ key, quality: 'COMPLETE', size_id: 'S', confirmed_target: null, constraints: clone(constraints), refs })
  const sources = [source('p1', [ref('W', 'p1')]), source('p2', variant === 'BAD_SOURCE' ? [ref('W', 'p2'), ref('W', 'p2')] : [ref('W', 'p2')])]
  const tfs = [{ key: 't1', size_id: 'S', constraints: clone(constraints), refs: [ref('T', 't1')] },
    { key: 't2', size_id: 'S', constraints: clone(constraints), refs: variant === 'BAD_TARGET' ? [ref('T', 't2-x'), ref('T', 't2-x')] : [ref('T', 't2')] }]
  return { contract_version: 'cp7.allocation-input.v1', snapshot_id: snapshot, scope_id: 'scope', scenario_id: 'probe', complete_scope: true,
    positions: { contract_version: 'cp7.wip-position.v1', snapshot_id: snapshot, status: 'COMPLETE', allocation_review_required: false,
      positions: [position('p1'), position('p2')], totals: [{ pool_key: 'pool', wip_pcs: '10' }] },
    matching: { snapshot_id: snapshot, sources, targets: tfs }, etas: ['p1', 'p2'].map(k => ({ position_key: k, at, refs: [ref('E', k)] })),
    targets: [target('t1', '2026-06-02T00:00:00Z'), target('t2', '2026-06-03T00:00:00Z')], capacity_pcs: '100', refs: [ref('C', 'c')] }
}

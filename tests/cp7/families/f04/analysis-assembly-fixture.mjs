import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { jsonArg } from './runtime.mjs'

export const assemblyBase = 'ab4d8fa5a1ba640dc2fe03167aa2cabb92337cd5'
const path = 'scripts/cp7-src/planning/analysis.sql'
export const uid = i => `02000000-0000-4000-8000-${i.toString(16).padStart(12, '0')}`
export const actor = { actor: uid(1), profile: { role_code: 'OWNER' } }
export const run = uid(2)

export function extractFunction(source, marker) {
 const start = source.indexOf(`create function ${marker}(`)
 if (start < 0) throw new Error(`Missing function ${marker}`)
 return source.slice(start, source.indexOf('$$;', source.indexOf('$$', start) + 2) + 3)
}

export async function installAssemblyControls(db) {
 const current = readFileSync(path, 'utf8')
 const old = execFileSync('git', ['show', `${assemblyBase}:${path}`], { encoding: 'utf8', maxBuffer: 1024 * 1024 })
 const fact = extractFunction(current, 'cp7_analysis_native.fact')
 const ref = extractFunction(readFileSync('scripts/cp7-src/wip/normalize.sql', 'utf8'), 'cp7_wip.ref')
 // Explicit precomputed source stand-ins isolate the assembler. These are
 // kernel comparisons, never Native Auth/business lifecycle qualification.
 await db.execute(`create schema extensions;create schema cp7_analysis_native;
  create schema cp7_netting_native;create schema cp7_fabric_native;create schema cp7_supply_native;
  create function extensions.digest(b bytea,kind text)returns bytea language sql immutable as $$select pg_catalog.sha256(b)$$;
  ${fact}${ref}
  create function cp7_netting_native.build(c jsonb,q jsonb)returns jsonb language sql immutable as $$select c->'test_netting'$$;
  create function cp7_fabric_native.plan(c jsonb,n jsonb)returns jsonb language sql immutable as $$select '{}'::jsonb$$;
  create function cp7_fabric_native.needs(c jsonb,r jsonb,a jsonb,p jsonb)returns jsonb language sql immutable as $$select case when r?'sql_null_fabric'then null else coalesce(r->'test_fabric','[]'::jsonb)end$$;
  create function cp7_analysis_native.material_needs(c jsonb,r jsonb,a jsonb)returns jsonb language sql immutable as $$select case when r?'sql_null_accessory'then null else coalesce(r->'test_accessory','[]'::jsonb)end$$;
  create function cp7_analysis_native.fingerprint(c jsonb)returns text language sql immutable as $$select encode(pg_catalog.sha256(convert_to(c::text,'UTF8')),'hex')$$;
  create function cp7_supply_native.fingerprint(c jsonb)returns text language sql immutable as $$select 'EXPLICIT_ASSEMBLY_KERNEL_ONLY'::text$$;
  ${[old, current].map((src, i) => extractFunction(src, 'cp7_analysis_native.build').replace('create function cp7_analysis_native.build(', `create function public.p19_assembly_${i}(`)).join('\n')}
  ${[0, 1].map(i => `create function public.p19_state_${i}(c jsonb,q jsonb,p uuid,a jsonb)returns text language plpgsql as $$begin perform public.p19_assembly_${i}(c,q,p,a);return 'NO_ERROR';exception when others then return SQLSTATE;end$$;`).join('\n')}`)
}

export function assemblyInput(count, seed = 1) {
 let state = seed >>> 0
 const pick = choices => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return choices[state % choices.length] }
 const products = [], stocks = [], history = [], rows = [], edges = [], positions = [], etas = [], matching = []
 const schedule = seed % 3 ? { plan_id: uid(3), revision: '9007199254740991' } : null
 for (let i = 0; i < count; i++) {
  const root = uid(100 + i), size = uid(100000), key = `${root}:${size}`
  const refs = [{ kind: 'EXPLICIT_SYNTHETIC_KERNEL_ONLY', id: root, revision: '9007199254740993' }]
  const policy = pick(['ACTIVE', 'PAUSED', 'STOPPED', null])
  const rate = pick(['1.25', '0', null])
  products.push({ root_id: root, id: root, size_id: size, brand_id: uid(4), sku: `P19-${i}`, product_name: `Produk ${i}`, commercial: i % 2 ? [] : [{ sku_id: uid(200000 + i), version_id: uid(300000 + i) }] })
  stocks.push({ target_key: key, availability: { physical_fg_pcs: '11', reserved_pcs: '3' }, refs })
  history.push({ target_key: key, available_days: '10', stockout_days: '2', unknown_days: pick(['0', '1']) })
  const events = []
  for (let j = 0; j < seed % 4; j++) events.push({ event: { kind: pick(['SUPPLY', 'DEMAND', 'UNKNOWN']), at: j % 2 ? '2026-10-05T17:00:00.000001Z' : '2026-10-05T16:59:59.999999Z', key: 'supply-first', qty_pcs: '7', refs }, balance_pcs: j % 2 ? '-9007199254740993.01' : null, new_unmet_pcs: '0.01' })
  rows.push({ target_key: key, size_id: size, sku: `P19-${i}`, refs, production_policy: { policy: { state: policy } }, profile: { quality: i % 2 ? 'SELECTED_ASSUMPTION' : 'UNKNOWN', profile_id: uid(400000 + i) }, target: { target_pcs: '100', horizon_days: '10.1' }, available_fg_pcs: '8', base_gap_pcs: '93', conditional_gap_pcs: pick(['93', '0', null]), demand_estimate: { daily_pcs: rate, basis: 'NATIVE_AVAILABLE_HISTORY' }, timeline: { events, minimum_balance_pcs: '-9007199254740993.01', first_known_gap: { at: '2026-10-05T17:00:00.000001Z' } }, test_accessory: [{ target_key: key, material_key: 'ACCESSORY:' + uid(5), gross: { state: 'ASSUMED', value: '9007199254740993.01', unit: 'PCS', refs, assumption_ids: [uid(3)] } }], test_fabric: [{ target_key: key, material_key: 'FABRIC_MATERIAL:' + uid(6), additional_external: { state: 'UNKNOWN', unit: 'yd', reason: 'EXPLICIT_KERNEL_UNKNOWN', refs } }] })
  if (policy && i < 2) {
   const source = 'first'
   edges.push({ key: source, position_key: source, target_key: key, size_id: size, input_pcs: '4', projected_good_pcs: '3', match: pick(['CONFIRMED_TARGET', 'CANDIDATE_MATCH']), refs })
  }
 }
 if (count) {
  positions.push({ key: 'first', size_id: uid(100000), stage: 'SEWING', eligible_company_wip: true, remaining_pcs: '8', projection: { eligible_input_pcs: '8', projected_good_pcs: '7' }, refs: [{ kind: 'EXPLICIT_SYNTHETIC_KERNEL_ONLY', id: uid(7), revision: '1' }] })
  etas.push({ position_key: 'first', result: { eta: '2026-10-06T00:00:00Z', status: 'CONDITIONAL' } })
  matching.push({ key: 'first', confirmed_target: seed % 2 ? rows[0].target_key : null })
 }
 return { status: 'COMPLETE', captured_at: '2026-10-06T00:00:00.000001Z', analysis_engine_signature: 'f'.repeat(64), schedule, facts: { products }, production_sources: { facts: { positions } }, matching_products: products, profiles: [], production_policies: { rows: [] }, planning_time_bucket: 'FIXED_TEST', material_source: { captured_at: '2026-10-06T00:00:00Z' }, fabric_source: { selected: schedule && count ? [{ id: uid(8), target_key: rows[0].target_key }] : [], captured_at: '2026-10-06T00:00:00Z' }, test_netting: { rows, match_results: [], matching: { sources: matching }, allocation: { status: seed % 2 ? 'SCENARIO' : 'UNKNOWN', allocation: { edges } }, schedule_run_result: { wip: { status: 'COMPLETE', positions }, etas, capacity: { status: 'SCENARIO', capacity_pcs: '100', inputs: { windows: [{ existing_load_minutes: '2.5' }] } }, supply_run_result: { baseline_run_result: { history_run_result: { current_stock: stocks, history: { rows: history } } } } } } }
}

export function assemblyArgs(c) { return [jsonArg(c), jsonArg({ from_date: '2026-10-01', through_date: '2026-10-06' }), `'${run}'::uuid`, jsonArg(actor)].join(',') }

export async function compareAssembly(db, c) {
 const args = assemblyArgs(c)
 return (await db.query(`with bodies as materialized(select public.p19_assembly_0(${args}) old,public.p19_assembly_1(${args}) candidate)
  select old::text=candidate::text same,encode(pg_catalog.sha256(convert_to(candidate::text,'UTF8')),'hex') sha256,
   jsonb_array_length(candidate->'recommendations') recommendations,jsonb_array_length(candidate->'timeline') timeline,
   jsonb_array_length(candidate->'generation_warnings') warnings,candidate->'material_needs'='null'::jsonb material_null from bodies`))[0]
}

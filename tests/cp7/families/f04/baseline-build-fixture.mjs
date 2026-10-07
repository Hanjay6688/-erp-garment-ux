import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { rng } from './demand-history-fixture.mjs'
import { functionBlocks } from './schedule-scenario-fixture.mjs'
import { installBuildControls, capture } from './history-build-fixture.mjs'
// cp7_baseline_native.build before (git) and after (working tree) on the
// runtime's real demand/baseline kernels and the real history_build. The only
// addition is a dispatcher in front of history_build that can patch its result
// (duplicate or odd current stock, no rows) the same way for both builds.
export const baselineBase = '9e3394e3065ca15f19fdc811d76782523dcea815'
const BASELINE = 'scripts/cp7-src/planning/baseline-source.sql'
const git = path => execFileSync('git', ['show', `${baselineBase}:${path}`], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024 })
const now = path => readFileSync(path, 'utf8')
const buildBlock = text => { const all = functionBlocks(text); if (!all.has('cp7_baseline_native.build')) throw new Error('cp7_baseline_native.build'); return all.get('cp7_baseline_native.build') }
export const renamed = (text, suffix) => text.replace('create function cp7_baseline_native.build(', `create function cp7_baseline_native.build${suffix}(`)
const RAISE = "then raise exception using errcode='21000',message='more than one row returned by a subquery used as an expression';end if;"
// Deliberately wrong shortcuts. Each must still apply to the working tree once.
export const MUTANTS = {
  // Two profiles for one root no longer refuse.
  PROFILE_REPEAT_SILENT: [`if profiles_repeated?root ${RAISE}`, ''],
  // Two current-stock rows for one target no longer refuse.
  STOCK_REPEAT_SILENT: [`if stocks_repeated?(r->>'target_key')${RAISE}`, ''],
  // The last policy containing the root wins instead of the first.
  POLICY_LAST: ["(array_agg(x order by o))[1] v from jsonb_array_elements(c->'production_policies'->'rows')", "(array_agg(x order by o desc))[1] v from jsonb_array_elements(c->'production_policies'->'rows')"],
  // Non-string array members are read as text.
  POLICY_ANY_ELEMENT: ["\n       where jsonb_typeof(e)='string'", ''],
  // Object members no longer match by key.
  POLICY_OBJECT_DROPPED: ["\n      union select jsonb_object_keys(case when jsonb_typeof(x->'members')='object'then x->'members'end)", ''],
  // A string member no longer matches itself.
  POLICY_STRING_DROPPED: ["\n      union select x->'members'#>>'{}' where jsonb_typeof(x->'members')='string'", ''],
  // Profiles are read before the first row instead of at it.
  PROFILES_EAGER: ["for r in select value from jsonb_array_elements(h->'history'->'rows')", "perform count(*)from jsonb_array_elements(c->'profiles');for r in select value from jsonb_array_elements(h->'history'->'rows')"],
}
export async function installBaselineControls(db, { mutants = [] } = {}) {
  await installBuildControls(db)
  const old = renamed(buildBlock(git(BASELINE)), '_0')
  if (!old.includes('create function cp7_baseline_native.build_0(')) throw new Error('predecessor not renamed')
  const fresh = buildBlock(now(BASELINE))
  const variants = mutants.map(name => {
    const [from, to] = MUTANTS[name]
    if (fresh.split(from).length !== 2) throw new Error(`mutant ${name} no longer applies`)
    return renamed(fresh.replace(from, to), `_m_${name.toLowerCase()}`)
  })
  await db.execute(`create schema if not exists cp7_baseline_native;
   alter function cp7_planning.history_build(jsonb,jsonb) rename to history_build_real;
   create function cp7_planning.history_build(c jsonb,q jsonb)returns jsonb language plpgsql immutable as $h$
   declare h jsonb:=cp7_planning.history_build_real(c,q);
   begin
    return case c->>'patch'
     when 'STOCK_REPEAT_USED' then jsonb_set(h,'{current_stock}',(h->'current_stock')||jsonb_build_array(h->'current_stock'->-1))
     when 'STOCK_REPEAT_UNUSED' then jsonb_set(h,'{current_stock}',(h->'current_stock')||'[{"target_key":"zz:none","sku":"A"},{"target_key":"zz:none","sku":"B"}]'::jsonb)
     when 'STOCK_ODD' then jsonb_set(h,'{current_stock}',(h->'current_stock')||'[1,"x",null,[],{"target_key":null}]'::jsonb)
     when 'STOCK_OBJECT' then jsonb_set(h,'{current_stock}','{}'::jsonb)
     when 'STOCK_MISSING' then h-'current_stock'
     when 'NO_ROWS' then jsonb_set(h,'{history,rows}','[]'::jsonb)
     else h end;
   end $h$;
   ${old}
   ${fresh}
   ${variants.join('\n')}
   -- Both builds on one input, each refusal caught as SQLSTATE:message,
   -- under the given plan cache mode (custom plans fold constant arguments).
   create function public.bl_compare(c jsonb,q jsonb,fn text default 'build',mode text default 'auto')returns jsonb language plpgsql as $s$
   declare r0 jsonb;r1 jsonb;s0 text:='NO_ERROR';s1 text:='NO_ERROR';
   begin
    perform set_config('plan_cache_mode',mode,true);
    begin execute 'select cp7_baseline_native.build_0($1,$2)'into r0 using c,q;
    exception when others then s0:=sqlstate||':'||sqlerrm;end;
    begin execute format('select cp7_baseline_native.%s($1,$2)',fn)into r1 using c,q;
    exception when others then s1:=sqlstate||':'||sqlerrm;end;
    return jsonb_build_object('s0',s0,'s1',s1,'same',r0::text is not distinct from r1::text,'bytes',octet_length(r0::text),
     'rows',coalesce(jsonb_array_length(r0->'rows'),0),
     'reasons',(select coalesce(jsonb_object_agg(k,n),'{}')from(select x->>'reason' k,count(*)n
       from jsonb_array_elements(coalesce(r0->'rows','[]'))x group by 1)f),
     'profiled',(select count(*)from jsonb_array_elements(coalesce(r0->'rows','[]'))x where x->'profile'<>'null'::jsonb),
     'stocked',(select count(*)from jsonb_array_elements(coalesce(r0->'rows','[]'))x where x->>'sku' is not null));
   end $s$;`)
}
export const QUERY = { from_date: '2026-05-01', through_date: '2026-05-30', group_mode: 'AS_SOLD' }
const iso = ms => new Date(ms).toISOString()
const config = (r, mode) => ({ mean_mode: mode, daily_pcs: mode === 'SELECTED_MANUAL' ? String(1 + Math.floor(r() * 9)) : null,
  minimum_available_days: String(1 + Math.floor(r() * 20)), lead_days: r() < 0.85 ? String(1 + Math.floor(r() * 30)) : null,
  review_days: r() < 0.85 ? String(Math.floor(r() * 14)) : null, buffer_days: r() < 0.7 ? String(Math.floor(r() * 10)) : null })
// A history capture (stock kept non-negative unless asked) with profiles and
// production policies over its roots, plus one planted defect.
export function baselineCapture(seed, { products = 6, stock = 60, sales = 20, defect = null, negative = false } = {}) {
  const r = rng(seed * 7919 + 17), c = capture(seed, { products, stock, sales })
  if (!negative && defect !== 'NEGATIVE_STOCK') for (const m of c.facts.stock) if (m.movement_type === 'RECEIPT') m.qty_signed = String(Math.abs(Number(m.qty_signed)) + 30)
  const at = iso(Date.UTC(2026, 4, 20)), roots = [...new Set(c.facts.products.map(p => p.root_id))]
  c.profiles = []
  for (const [i, p] of c.facts.products.entries()) {
    const kind = r()
    if (kind < 0.15) { c.profiles.push({ root_id: p.root_id, product_version_id: p.id, size_id: p.size_id, sku: p.sku, product_name: p.product_name, profile_id: null, revision: '0', config: null, reason: null, recorded_at: null, quality: 'UNREVIEWED' }); continue }
    if (kind < 0.2) continue
    const quality = kind < 0.27 ? 'PHYSICAL_VERSION_CHANGED' : 'SELECTED_ASSUMPTION'
    c.profiles.push({ root_id: p.root_id, product_version_id: p.id, size_id: p.size_id, sku: p.sku, product_name: p.product_name, profile_id: `00000000-0000-4000-9000-${String(seed * 100 + i).padStart(12, '0')}`,
      revision: String(1 + Math.floor(r() * 3)), config: config(r, r() < 0.4 ? 'SELECTED_MANUAL' : 'OWN_AVAILABLE_HISTORY'), reason: 'uji', recorded_at: at, quality })
  }
  const state = () => ['ACTIVE', 'PAUSED', 'STOPPED'][Math.floor(r() * 3)], quality = () => (r() < 0.75 ? 'KNOWN' : r() < 0.5 ? 'UNREVIEWED' : 'MEMBERSHIP_CHANGED')
  const rows = []
  roots.forEach((root, i) => {
    if (r() < 0.1) { rows.push({ sku_id: `00000000-0000-4000-a000-${String(i).padStart(12, '0')}`, status: 'UNAVAILABLE' }); return }
    const q = quality(), members = [root, ...(r() < 0.3 ? [roots[(i + 1) % roots.length]] : [])]
    rows.push({ sku_id: `00000000-0000-4000-a000-${String(i).padStart(12, '0')}`, members, status: 'AVAILABLE', policy_revision: '1',
      policy: { quality: q, state: q === 'KNOWN' ? state() : null, last_reviewed_state: state(), reason: 'uji', review_at: null, review_due: false, recorded_at: at } })
  })
  c.production_policies = { contract_version: 'cp7.production-policy.v1', knowledge_mode: 'CURRENT', generated_at: at, rows }
  const used = roots[Math.floor(r() * roots.length)], profile = c.profiles.find(p => p.root_id === used) ?? { root_id: used, quality: 'UNREVIEWED', config: null }
  const policy = (members, st = 'PAUSED') => ({ sku_id: 'odd', members, status: 'AVAILABLE', policy: { quality: 'KNOWN', state: st } })
  switch (defect) {
    case 'PROFILE_REPEAT_USED': if (!c.profiles.includes(profile)) c.profiles.push(profile); c.profiles.push({ ...profile, quality: 'IDENTITY_CONFLICT' }); break
    case 'PROFILE_REPEAT_UNUSED': c.profiles.push({ root_id: '00000000-0000-4000-8000-999999999999', quality: 'IDENTITY_CONFLICT' }, { root_id: '00000000-0000-4000-8000-999999999999', quality: 'IDENTITY_CONFLICT' }); break
    case 'PROFILES_OBJECT': c.profiles = { [used]: profile }; break
    case 'PROFILES_SCALAR': c.profiles = 'none'; break
    case 'PROFILES_MISSING': delete c.profiles; break
    case 'PROFILES_ODD': c.profiles.push(1, 'x', null, [used], { root_id: null }, { root_id: 7 }); break
    case 'PROFILE_BAD_CONFIG': Object.assign(profile, { quality: 'SELECTED_ASSUMPTION', config: { ...config(r, 'OWN_AVAILABLE_HISTORY'), lead_days: 'x' } }); if (!c.profiles.includes(profile)) c.profiles.push(profile); break
    case 'POLICY_MEMBERS_OBJECT': rows.unshift(policy({ [used]: true, other: 1 }, 'STOPPED')); break
    case 'POLICY_MEMBERS_STRING': rows.unshift(policy(used, 'STOPPED')); break
    case 'POLICY_MEMBERS_ODD': rows.unshift(policy([null, 5, true, [used], { [used]: 1 }], 'STOPPED'), policy([null, used], 'PAUSED')); break
    case 'POLICY_OVERLAP': rows.push(policy([used], 'STOPPED')); rows.unshift(policy([used, roots[0]], 'ACTIVE')); break
    case 'POLICY_NUMBER_MEMBERS': rows.unshift(policy(5, 'STOPPED'), policy(null), policy([])); break
    case 'POLICIES_OBJECT': c.production_policies.rows = { [used]: rows[0] }; break
    case 'POLICIES_MISSING': delete c.production_policies; break
    case 'POLICY_ROWS_ODD': rows.unshift(1, 'x', null, [used]); break
    case 'NEGATIVE_STOCK': break
    case 'STOCK_REPEAT_USED': case 'STOCK_REPEAT_UNUSED': case 'STOCK_ODD': case 'STOCK_OBJECT': case 'STOCK_MISSING': c.patch = defect; break
    case 'NO_ROWS_PROFILES_OBJECT': c.patch = 'NO_ROWS'; c.profiles = {}; c.production_policies = { rows: 'x' }; break
    case null: break
    default: throw new Error(defect)
  }
  return c
}
export const DEFECTS = [null, null, null, 'PROFILE_REPEAT_USED', 'PROFILE_REPEAT_UNUSED', 'PROFILES_OBJECT', 'PROFILES_SCALAR', 'PROFILES_MISSING', 'PROFILES_ODD',
  'PROFILE_BAD_CONFIG', 'POLICY_MEMBERS_OBJECT', 'POLICY_MEMBERS_STRING', 'POLICY_MEMBERS_ODD', 'POLICY_OVERLAP', 'POLICY_NUMBER_MEMBERS', 'POLICIES_OBJECT',
  'POLICIES_MISSING', 'POLICY_ROWS_ODD', 'NEGATIVE_STOCK', 'STOCK_REPEAT_USED', 'STOCK_REPEAT_UNUSED', 'STOCK_ODD', 'STOCK_OBJECT', 'STOCK_MISSING', 'NO_ROWS_PROFILES_OBJECT']

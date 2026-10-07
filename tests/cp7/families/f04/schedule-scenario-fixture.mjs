import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { rng } from './demand-history-fixture.mjs'
// cp7_schedule_native.build and cp7_wip.project_yield before (git) and after
// (working tree) on the runtime's real wip, demand, capacity and timing kernels. Only the
// Native supply composition is a stub: build reads its WIP positions and hash.
export const scheduleBase = '117732fb35637e49fccd68695018d4f0b37f7cb3'
const git = path => execFileSync('git', ['show', `${scheduleBase}:${path}`], { encoding: 'utf8' })
const now = path => readFileSync(path, 'utf8')
// Every create function block of a source file, by qualified name.
export function functionBlocks(text) {
  const out = new Map(), re = /create function ([\w.]+)\(/g
  for (let m; (m = re.exec(text));) {
    const tag = text.slice(m.index).match(/\$[A-Za-z_]*\$/), open = m.index + tag.index, close = text.indexOf(tag[0], open + tag[0].length)
    out.set(m[1], text.slice(m.index, text.indexOf(';', close) + 1))
  }
  return out
}
const pick = (text, ...names) => { const all = functionBlocks(text); return names.map(n => { if (!all.has(n)) throw new Error(n); return all.get(n) }).join('\n') }
export async function installScheduleControls(db) {
  const yieldOld = pick(git('scripts/cp7-src/wip/yield.sql'), 'cp7_wip.project_yield').replace('create function cp7_wip.project_yield(', 'create function cp7_wip.project_yield_0(')
  const buildOld = pick(git('scripts/cp7-src/planning/schedule-scenario.sql'), 'cp7_schedule_native.build')
    .replace('create function cp7_schedule_native.build(', 'create function cp7_schedule_native.build_0(').replace('cp7_wip.project_yield(', 'cp7_wip.project_yield_0(')
  if (!buildOld.includes('project_yield_0(')) throw new Error('old build does not call project_yield')
  await db.execute(`create schema if not exists extensions;create extension if not exists pgcrypto schema extensions;
   create schema cp7_planning;create schema cp7_schedule_native;create schema cp7_supply_native;
   create function cp7_supply_native.fingerprint(c jsonb)returns text language sql immutable as $$select c->>'stub_hash'$$;
   create function cp7_supply_native.build(c jsonb,q jsonb)returns jsonb language sql immutable as $$select c->'stub_supply'$$;
   ${pick(now('scripts/cp7-src/planning/bootstrap.sql'), 'cp7_planning.utc')}
   ${yieldOld}
   ${pick(now('scripts/cp7-src/wip/yield.sql'), 'cp7_wip.project_yield')}
   ${pick(now('scripts/cp7-src/planning/schedule.sql'), 'cp7_schedule_native.route')}
   ${pick(now('scripts/cp7-src/planning/schedule-scenario.sql'), 'cp7_schedule_native.fingerprint')}
   ${buildOld}
   ${pick(now('scripts/cp7-src/planning/schedule-scenario.sql'), 'cp7_schedule_native.build')}
   create function public.sc_state(fn text,c jsonb)returns text language plpgsql as $s$
   begin execute format('select %s($1,$2)',fn)using c,'{}'::jsonb;return 'NO_ERROR';exception when others then return sqlstate||':'||sqlerrm;end $s$;
   create function public.yd_state(fn text,p jsonb,q jsonb)returns text language plpgsql as $s$
   begin execute format('select %s($1,$2)',fn)using p,q;return 'NO_ERROR';exception when others then return sqlstate||':'||sqlerrm;end $s$;`)
}
const iso = ms => new Date(ms).toISOString()
const STAGES = ['CUT_UNASSIGNED', 'SEWING_ACTIVE', 'LAUNDRY_OUTSTANDING', 'AWAIT_QC', 'REWORK', 'REWASH', 'FINISHED']
const STEPS = ['SEWING', 'LAUNDRY', 'QC', 'REWORK']
const ref = (kind, id) => ({ kind, id, revision: '1' })
// A captured WIP snapshot and a selected schedule. `defect` plants one fault
// (or none) so refusals are compared as well as complete scenarios.
export function scheduleInput(seed, { positions = 20, windows = 12, defect = null, maxMinutes = 90 } = {}) {
  const r = rng(seed), at = Date.UTC(2026, 5, 1, 1, 7, 13, 250), minute = 60000, keyOf = i => `pos-${String(i).padStart(6, '0')}`
  const wip = []
  for (let i = 0; i < positions; i++) {
    const remaining = r() < 0.08 ? '0' : String(1 + Math.floor(r() * 60))
    wip.push({ key: keyOf((i * 7919) % (positions * 3) + 1), stage: STAGES[Math.floor(r() * STAGES.length)], remaining_pcs: remaining,
      eligible_company_wip: r() < 0.85, refs: [ref('WIP_POSITION', `w-${i}`)] })
  }
  if (defect === 'BAD_PCS') wip[Math.floor(r() * wip.length)].remaining_pcs = '1.5'
  const cfgPositions = wip.filter(() => defect === 'PARTIAL_CONFIG' ? r() < 0.7 : true).map(p => {
    const yieldOn = r() < 0.6, den = 1 + Math.floor(r() * 20), steps = STEPS.filter(() => r() < 0.6).slice(0, 3)
    return { position_key: p.key, target_key: `t-${Math.floor(r() * 50)}`, eligible_input_pcs: defect === 'MISMATCH' && r() < 0.3 ? String(Number(p.remaining_pcs) + 1) : p.remaining_pcs,
      yield_numerator: yieldOn ? String(Math.floor(r() * (den + 1))) : null, yield_denominator: yieldOn ? String(den) : null,
      remaining_steps: (steps.length ? steps : ['QC']).map(stage => ({ stage, remaining_minutes: defect === 'NULL_MINUTES' && r() < 0.2 ? null : String(1 + Math.floor(r() * maxMinutes)) })) }
  })
  if (defect === 'DUPLICATE_CONFIG' && cfgPositions.length) cfgPositions.splice(Math.floor(r() * cfgPositions.length), 0, { ...cfgPositions[Math.floor(r() * cfgPositions.length)] })
  if (defect === 'ZERO_DENOMINATOR') { const y = cfgPositions.find(p => p.yield_denominator); if (y) y.yield_denominator = '0' }
  const win = []
  let cursor = at - 90 * minute
  for (let i = 0; i < (defect === 'MANY_WINDOWS' ? 1001 : windows); i++) {
    const start = cursor + Math.floor(r() * 120) * minute, end = start + (30 + Math.floor(r() * 400)) * minute + (r() < 0.2 ? 500 : 0)
    win.push({ key: `win-${String(i).padStart(3, '0')}`, starts_at: iso(start), ends_at: iso(end),
      other_load_minutes: defect === 'OTHER_LOAD' && r() < 0.3 ? String(1 + Math.floor(r() * 30)) : defect === 'NULL_LOAD' && r() < 0.3 ? null : '0' })
    cursor = end
  }
  if (r() < 0.5) win.reverse()
  const hash = `H${seed}`, through = defect === 'EXPIRED' ? at - minute : cursor + 60 * minute
  const plan = { plan_id: `plan-${seed}`, revision: '3', source_hash: defect === 'SOURCE_CHANGED' ? 'other' : hash,
    config: { through_at: iso(through), work_centre_key: 'centre-1', unit_minutes: defect === 'NO_UNIT' ? null : '2.5', windows: win, positions: cfgPositions } }
  return { captured_at: iso(at), planning_time_bucket: iso(Math.floor(at / minute) * minute), stub_hash: hash,
    stub_supply: { status: 'COMPLETE', wip: { contract_version: 'cp7.wip-position.v1', status: defect === 'WIP_INCOMPLETE' ? 'INCOMPLETE' : 'COMPLETE', snapshot_id: `snap-${seed}`, positions: wip } },
    schedule: defect === 'UNREVIEWED' ? null : plan }
}
export const DEFECTS = [null, null, null, 'PARTIAL_CONFIG', 'MISMATCH', 'NULL_MINUTES', 'DUPLICATE_CONFIG', 'ZERO_DENOMINATOR', 'BAD_PCS', 'OTHER_LOAD', 'NULL_LOAD', 'EXPIRED', 'SOURCE_CHANGED', 'NO_UNIT', 'WIP_INCOMPLETE', 'UNREVIEWED', 'MANY_WINDOWS']
// project_yield on its own: duplicate, missing, invalid and repeated-position inputs.
export function yieldInput(seed, { positions = 15, defect = null } = {}) {
  const r = rng(seed), rows = [], key = i => `p-${i}`
  for (let i = 0; i < positions; i++) rows.push({ key: key(Math.floor(r() * positions * 0.9)), remaining_pcs: String(Math.floor(r() * 40)), eligible_company_wip: r() < 0.9, refs: [ref('W', `x${i}`)] })
  const policies = []
  const seen = new Set()
  for (const p of rows) {
    if (seen.has(p.key) || r() < 0.3 || !p.eligible_company_wip) continue
    seen.add(p.key)
    const den = 1 + Math.floor(r() * 9), basis = ['ASSUMED', 'HISTORY', 'CONFIRMED_PLAN'][Math.floor(r() * 3)]
    policies.push({ position_key: p.key, eligible_input_pcs: String(Math.floor(r() * (Number(p.remaining_pcs) + 1))), numerator: String(Math.floor(r() * (den + 1))), denominator: String(den),
      basis, assumption_id: basis === 'ASSUMED' ? `a-${seed}` : null, refs: [ref('PLAN', `y${seed}`)] })
  }
  if (defect === 'DUPLICATE' && policies.length) policies.push({ ...policies[Math.floor(r() * policies.length)] })
  if (defect === 'MISSING') policies.push({ ...(policies[0] ?? { eligible_input_pcs: '0', numerator: '0', denominator: '1', basis: 'HISTORY', assumption_id: null, refs: [ref('PLAN', 'y')] }), position_key: 'nowhere' })
  if (defect === 'BAD_KEY' && policies.length) policies[Math.floor(r() * policies.length)].position_key = 7
  if (defect === 'OVER' && policies.length) policies[0].eligible_input_pcs = '999999'
  return { positions: { contract_version: 'cp7.wip-position.v1', status: 'COMPLETE', positions: defect === 'NOT_ARRAY' ? { k: 1 } : rows }, policies }
}
export const YIELD_DEFECTS = [null, null, 'DUPLICATE', 'MISSING', 'BAD_KEY', 'OVER', 'NOT_ARRAY']

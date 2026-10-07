import { execFileSync } from 'node:child_process'
// Exact predecessor of the linear demand-1 kernel, read from git and installed
// next to it under another name. Nothing else in the runtime changes.
export const historyBase = 'c1f91041035941edded57da13482176701b2bfb6'
export async function installHistoryControls(db) {
  const source = execFileSync('git', ['show', `${historyBase}:scripts/cp7-src/demand/history.sql`], { encoding: 'utf8' })
  const start = source.indexOf('create function cp7_demand.history(v jsonb)'), end = source.indexOf('create function cp7_demand.availability(v jsonb)')
  if (start < 0 || end < start) throw new Error('predecessor demand history not found')
  await db.execute(source.slice(start, end).replace('create function cp7_demand.history(v jsonb)', 'create function cp7_demand.history_0(v jsonb)'))
  await db.execute(`create function public.dh_state(fn text,v jsonb) returns text language plpgsql as $$
   begin execute format('select %s($1)',fn) using v;return 'NO_ERROR';
   exception when others then return sqlstate||':'||sqlerrm;end $$;`)
}
// Deterministic generator: valid histories plus one injected defect at a random row.
export function rng(seed) { let x = seed >>> 0 || 1; return () => { x = (x * 1664525 + 1013904223) >>> 0; return x / 4294967296 } }
const iso = ms => new Date(ms).toISOString().replace('.000Z', 'Z')
export function demandInput(seed, { targets = 6, days = 20, events = 60, availability = 0.7, defect = null } = {}) {
  const r = rng(seed), pick = a => a[Math.floor(r() * a.length)], hi = Date.UTC(2026, 4, 31), lo = hi - (days - 1) * 86400000
  const effective = Date.UTC(2026, 5, 1), known = effective - Math.floor(r() * 3) * 3600000
  const t = Array.from({ length: targets }, (_, i) => ({ key: `T${String((i * 7919 + seed) % 100000).padStart(5, '0')}`, size_id: pick(['S', 'M', 'L']), current_group_key: `G${i % 3}`, refs: [{ kind: 'PRODUCT', id: `p${i}`, revision: '1' }] }))
  const ev = []
  for (let j = 0; j < events; j++) {
    const target = pick(t), lineage = `L${Math.floor(r() * events * 0.7)}`, status = pick(['POSTED', 'POSTED', 'POSTED', 'DRAFT', 'CANCELLED'])
    const day = lo + Math.floor(r() * (days + 3) - 2) * 86400000, at = day + Math.floor(r() * 86400000)
    const late = r() < 0.08, qty = 1 + Math.floor(r() * 9), ret = status === 'POSTED' ? Math.floor(r() * (qty + 1)) : 0
    const same = ev.find(e => e.lineage_key === lineage), revisions = Math.max(0, ...ev.filter(e => e.lineage_key === lineage).map(e => Number(e.revision)))
    const row = { lineage_key: lineage, revision: String(revisions + 1 + (r() < 0.2 ? 1 : 0)), known_at: iso(late ? effective + 3600000 : at + 1000), effective_at: iso(at + 1000),
      posted_at: status === 'POSTED' ? iso(at) : null, status, target_key: same ? same.target_key : target.key, size_id: same ? same.size_id : target.size_id,
      sold_group_key: `S${Math.floor(r() * 4)}`, qty_pcs: String(qty), returned_pcs: String(ret), refs: [{ kind: 'SALE_ITEM', id: `s${j}`, revision: '1' }] }
    // An exact repeat of an earlier revision is legal; a changed repeat is an injected defect.
    ev.push(row); if (r() < 0.1) ev.push({ ...row })
  }
  const av = []
  for (const target of t) for (let d = 0; d < days; d++) if (r() < availability) {
    const rev = 1 + Math.floor(r() * 2)
    av.push({ target_key: target.key, date: new Date(lo + d * 86400000).toISOString().slice(0, 10), revision: String(rev), known_at: iso(r() < 0.1 ? effective + 7200000 : lo + d * 86400000 + 43200000), state: pick(['AVAILABLE', 'AVAILABLE', 'STOCKOUT', 'UNKNOWN']), refs: [{ kind: 'PRODUCT', id: target.key, revision: String(rev) }] })
    if (r() < 0.15) av.push({ ...av[av.length - 1] })
  }
  const v = { contract_version: 'cp7.demand-input.v1', snapshot_id: `snap-${seed}`, scope_id: 'scope', known_as_of: iso(known), effective_as_of: iso(effective),
    from_date: new Date(lo).toISOString().slice(0, 10), through_date: new Date(hi).toISOString().slice(0, 10), history_complete: r() < 0.85, group_mode: pick(['AS_SOLD', 'RESTATED']),
    targets: t.sort(() => r() - 0.5), events: ev, availability: av.sort(() => r() - 0.5) }
  if (defect) injectDefect(v, defect, r)
  return v
}
export const defects = ['conflict', 'identity', 'size', 'field', 'instant', 'duplicate_target', 'availability_conflict', 'availability_target', 'lifecycle', 'unposted_return', 'state']
// Every validator the set-based fast path restates (P19): one defect each, so a
// fast path that accepted what the row loop refuses would differ from the predecessor.
const EVENT_FIELDS = { key_space: ['lineage_key', ' L1'], key_empty: ['target_key', ''], key_number: ['sold_group_key', 5], key_long: ['size_id', 'X'.repeat(201)],
  pcs_zero_led: ['revision', '01'], pcs_decimal: ['qty_pcs', '1.5'], pcs_number: ['returned_pcs', 0], pcs_negative: ['qty_pcs', '-1'],
  refs_empty: ['refs', []], refs_object: ['refs', { kind: 'SALE_ITEM', id: 's', revision: '1' }], refs_extra: ['refs', [{ kind: 'SALE_ITEM', id: 's', revision: '1', x: 1 }]],
  refs_duplicate: ['refs', [{ kind: 'SALE_ITEM', id: 's', revision: '1' }, { kind: 'SALE_ITEM', id: 's', revision: '1' }]], refs_key: ['refs', [{ kind: 'SALE_ITEM', id: 's ', revision: '1' }]],
  hour_24: ['known_at', '2026-05-01T24:00:00Z'], minute_60: ['effective_at', '2026-05-01T10:60:00Z'], no_zulu: ['known_at', '2026-05-01T10:00:00'], micro_7: ['effective_at', '2026-05-01T10:00:00.1234567Z'],
  month_13: ['known_at', '2026-13-01T10:00:00Z'], instant_number: ['effective_at', 20260501], status_void: ['status', 'VOID'], status_null: ['status', null] }
const AVAILABILITY_FIELDS = { av_day_invalid: ['date', '2026-02-30'], av_day_short: ['date', '2026-5-01'], av_day_number: ['date', 20260501], av_revision: ['revision', '1.0'],
  av_known: ['known_at', '2026-05-01T23:59:60Z'], av_refs: ['refs', []], av_key: ['target_key', 7], av_state_null: ['state', null] }
defects.push(...Object.keys(EVENT_FIELDS), ...Object.keys(AVAILABILITY_FIELDS), 'posted_after_effective', 'draft_posted_at', 'event_extra_field', 'event_not_object',
  'availability_extra_field', 'availability_not_object', 'late_event_unknown_target', 'late_availability_unknown_target')
function injectDefect(v, kind, r) {
  const n = Math.floor(r() * v.events.length), e = v.events[n], a = v.availability[Math.floor(r() * v.availability.length)]
  if (kind === 'conflict' && e) v.events.push({ ...e, qty_pcs: String(Number(e.qty_pcs) + 1) })
  if (kind === 'identity' && e) v.events.push({ ...e, revision: String(Number(e.revision) + 7), size_id: e.size_id === 'S' ? 'XL' : 'S' })
  if (kind === 'size' && e) e.size_id = 'XXL'
  if (kind === 'field' && e) delete e.refs
  if (kind === 'instant' && e) e.known_at = '2026-02-30T00:00:00Z'
  if (kind === 'duplicate_target') v.targets.splice(Math.floor(r() * v.targets.length), 0, { ...v.targets[0] })
  if (kind === 'availability_conflict' && a) v.availability.push({ ...a, state: a.state === 'AVAILABLE' ? 'STOCKOUT' : 'AVAILABLE' })
  if (kind === 'availability_target' && a) a.target_key = 'NO-SUCH-TARGET'
  if (kind === 'lifecycle' && e) e.returned_pcs = String(Number(e.qty_pcs) + 1)
  if (kind === 'unposted_return' && e) { e.status = 'DRAFT'; e.posted_at = null; e.returned_pcs = '1' }
  if (kind === 'state' && a) a.state = 'MAYBE'
  if (EVENT_FIELDS[kind] && e) e[EVENT_FIELDS[kind][0]] = EVENT_FIELDS[kind][1]
  if (AVAILABILITY_FIELDS[kind] && a) a[AVAILABILITY_FIELDS[kind][0]] = AVAILABILITY_FIELDS[kind][1]
  if (kind === 'posted_after_effective' && e) { e.status = 'POSTED'; e.posted_at = '2026-06-01T00:00:00Z'; e.effective_at = '2026-05-31T00:00:00Z' }
  if (kind === 'draft_posted_at' && e) { e.status = 'DRAFT'; e.returned_pcs = '0'; e.posted_at = e.effective_at }
  if (kind === 'event_extra_field' && e) e.note = 'x'
  if (kind === 'event_not_object' && e) v.events[n] = 'row'
  if (kind === 'availability_extra_field' && a) a.note = 'x'
  if (kind === 'availability_not_object' && a) v.availability[v.availability.indexOf(a)] = ['row']
  // Rows known after the cutoff are skipped before the target lookup: legal.
  if (kind === 'late_event_unknown_target' && e) { e.lineage_key = 'LATE-ONLY'; e.revision = '1'; e.target_key = 'NO-SUCH-TARGET'; e.known_at = '2026-06-01T05:00:00Z' }
  if (kind === 'late_availability_unknown_target' && a) { a.target_key = 'NO-SUCH-TARGET'; a.known_at = '2026-06-01T05:00:00Z' }
}

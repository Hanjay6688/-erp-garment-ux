import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { rng } from './demand-history-fixture.mjs'
import { functionBlocks } from './schedule-scenario-fixture.mjs'
// PL-8: cp7_wip.normalize_cutting, settle_bs, reconcile and normalize_production
// before (git, renamed *_0) and after (working tree) on generated cutting
// lifecycles. normalize_other and transition are unchanged; the old copy of
// normalize_other only routes to the old settle_bs/reconcile.
export const wipBase = '3c0aca7f944e529c513d2b0027eb76b957e44cfa'
const git = path => execFileSync('git', ['show', `${wipBase}:${path}`], { encoding: 'utf8' })
const now = path => readFileSync(path, 'utf8')
const pick = (text, ...names) => { const all = functionBlocks(text); return names.map(n => { if (!all.has(n)) throw new Error(n); return all.get(n) }).join('\n') }
const RENAMED = ['reconcile', 'settle_bs', 'normalize_cutting', 'normalize_other', 'normalize_production']
const old = (text, ...names) => RENAMED.reduce((s, n) => s.replaceAll(`cp7_wip.${n}(`, `cp7_wip.${n}_0(`), pick(text, ...names))
export async function installWipControls(db) {
  const before = [old(git('scripts/cp7-src/wip/graph.sql'), 'cp7_wip.reconcile'), old(git('scripts/cp7-src/wip/bs.sql'), 'cp7_wip.settle_bs'),
    old(git('scripts/cp7-src/wip/normalize.sql'), 'cp7_wip.normalize_cutting'), old(git('scripts/cp7-src/wip/other-normalize.sql'), 'cp7_wip.normalize_other'),
    old(git('scripts/cp7-src/wip/production.sql'), 'cp7_wip.normalize_production')]
  for (const n of RENAMED) if (!before.some(s => s.includes(`create function cp7_wip.${n}_0(`))) throw new Error(`old ${n} missing`)
  await db.execute(`${now('scripts/cp7-src/wip/graph.sql')}
   ${now('scripts/cp7-src/wip/normalize.sql')}
   ${now('scripts/cp7-src/wip/bs.sql')}
   ${now('scripts/cp7-src/wip/rewash.sql')}
   ${now('scripts/cp7-src/wip/other-normalize.sql')}
   ${pick(now('scripts/cp7-src/wip/production.sql'), 'cp7_wip.normalize_production')}
   ${before.join('\n')}
   create table public.wn_in(n integer primary key,c jsonb not null);
   -- State and bytes of both versions in one call. Arguments are bound
   -- parameters, so no immutable call is folded at plan time.
   create function public.wn_cmp(fn0 text,fn1 text,c jsonb)returns jsonb language plpgsql as $s$
   declare r0 jsonb;r1 jsonb;s0 text:='NO_ERROR';s1 text:='NO_ERROR';t0 timestamptz;ms0 numeric;ms1 numeric;
   begin
    t0:=clock_timestamp();
    begin execute format('select %s($1)',fn0)into r0 using c;exception when others then s0:=sqlstate||':'||sqlerrm;end;
    ms0:=round(extract(epoch from clock_timestamp()-t0)*1000,1);t0:=clock_timestamp();
    begin execute format('select %s($1)',fn1)into r1 using c;exception when others then s1:=sqlstate||':'||sqlerrm;end;
    ms1:=round(extract(epoch from clock_timestamp()-t0)*1000,1);
    return jsonb_build_object('s0',s0,'s1',s1,'same',r0::text is not distinct from r1::text,'md5_0',md5(r0::text),'md5_1',md5(r1::text),
     'bytes',octet_length(r1::text),'status',r1->>'status','reason',r1->>'reason','ms0',ms0,'ms1',ms1,
     'positions',jsonb_array_length(r1->'positions'),'zero',jsonb_array_length(jsonb_path_query_array(r1,'$.positions[*] ? (@.remaining_pcs == "0")')));
   end $s$;
   create function public.wn_run(fn text,c jsonb)returns jsonb language plpgsql as $s$
   declare r jsonb;s text:='NO_ERROR';t0 timestamptz:=clock_timestamp();
   begin
    begin execute format('select %s($1)',fn)into r using c;exception when others then s:=sqlstate||':'||sqlerrm;end;
    return jsonb_build_object('fn',fn,'state',s,'ms',round(extract(epoch from clock_timestamp()-t0)*1000,1),'md5',md5(r::text),'utf8_bytes',octet_length(r::text),
     'status',r->>'status','reason',r->>'reason','positions',jsonb_array_length(r->'positions'),'pools',jsonb_array_length(r->'totals'),
     'zero_positions',jsonb_array_length(jsonb_path_query_array(r,'$.positions[*] ? (@.remaining_pcs == "0")')));
   end $s$;`)
}

// ---------------------------------------------------------------- generator
const hex = (r, n) => Array.from({ length: n }, () => Math.floor(r() * 16).toString(16)).join('')
const T0 = Date.UTC(2026, 7, 1, 1, 0, 0)
// Capture timestamps are Asia/Jakarta text; equal texts give sort ties.
const at = (r, ties) => { const ms = T0 + (ties ? Math.floor(r() * 4) * 3600000 : Math.floor(r() * 60 * 24) * 3600000); return new Date(ms + 7 * 3600000).toISOString().replace('.000Z', '+07:00') }
export const CAPTURED_AT = '2026-10-07T03:00:00+00:00'
const LATE = '2026-11-01T10:00:00+07:00'
const KINDS = ['open', 'done', 'partial', 'laundry', 'legacy', 'bs', 'rework', 'rewash', 'retry', 'reversal', 'hold', 'manual', 'claim', 'dispose']
export const EXHAUSTED_KINDS = ['done', 'exhausted_laundry', 'exhausted_bs']
const emptyFacts = () => Object.fromEntries(['groups', 'yields', 'batches', 'deliveries', 'delivery_sizes', 'receipts', 'receipt_sizes', 'qc', 'bs', 'reworks', 'resolutions',
  'holds', 'bs_fg', 'failed', 'failed_sizes', 'redispatch', 'claims', 'sewing', 'flags'].map(k => [k, []]))

// One posted cutting group. Quantities stay conserved unless a defect is planted.
function group(f, r, kind, { sizesPerGroup = 0, ties = false, sizePool }) {
  const uid = () => `${hex(r, 8)}-${hex(r, 4)}-4${hex(r, 3)}-8${hex(r, 3)}-${hex(r, 12)}`, ts = () => at(r, ties), rev = () => String(1 + Math.floor(r() * 4))
  const g = uid(), pickedAt = kind === 'open' && r() < 0.5 ? null : ts(), product = uid()
  const nSizes = sizesPerGroup || (['legacy', 'claim', 'manual'].includes(kind) ? 1 : 1 + Math.floor(r() * 3))
  const sizes = [...sizePool].sort(() => r() - 0.5).slice(0, nSizes)
  f.groups.push({ id: g, po_id: uid(), revision: rev(), status: 'POSTED', pattern_id: uid(), pattern_revision_snapshot: 1, cut_at: ts(), picked_up_at: pickedAt,
    material_issue_posted: true, model_id: uid() })
  const batch = uid(), pickup = uid(), total = {}, batchOf = {}
  for (const size of sizes) {
    total[size] = 0; batchOf[size] = batch
    for (let roll = 0; roll < (r() < 0.35 ? 2 : 1); roll++) {
      const y = uid(), q = 2 + Math.floor(r() * 30); total[size] += q
      f.yields.push({ id: y, group_id: g, size_id: size, qty_pcs: String(q), revision: rev() })
      if (pickedAt) f.batches.push({ id: uid(), batch_id: batch, pickup_id: pickup, group_id: g, status: 'POSTED', picked_up_at: pickedAt, revision: rev(), yield_id: y, qty_pcs: String(q) })
    }
  }
  if (r() < 0.15) f.flags.push({ id: uid(), group_id: g, flag_type: ['PENDING_CORRECTION', 'PENDING_REVERSAL', 'OTHER'][Math.floor(r() * 3)], status: r() < 0.6 ? 'OPEN' : 'RESOLVED', revision: rev(), created_at: ts(), resolved_at: null })
  if (r() < 0.2) f.sewing.push({ id: uid(), group_id: g, qty_signed: '1', event_kind: 'COMPLETE', reversal_of_id: null, physical_at: ts(), revision: rev() })
  const part = n => Math.floor(r() * (n + 1))
  const qc = (size, good, bs, receipt = null, rsize = null, status = 'POSTED') => {
    const q = { id: uid(), group_id: g, inspection_id: uid(), status, physical_at: ts(), revision: rev(), receipt_line_id: receipt, receipt_size_id: rsize,
      final_product_id: product, size_id: size, product_root: product, good_pcs: String(good), bs_pcs: String(bs) }
    f.qc.push(q); return q
  }
  const bsCase = (size, qty, { qcItem = null, receipt = null, rsize = null, status = 'OPEN', noSize = false } = {}) => {
    const b = { id: uid(), group_id: g, qc_item_id: qcItem, product_id: product, size_id: noSize ? null : size, receipt_line_id: receipt, receipt_size_id: rsize,
      qty_pcs: String(qty), status, detected_at_stage: qcItem ? 'QC' : receipt ? 'LAUNDRY' : 'SEWING', physical_at: ts(), revision: rev() }
    f.bs.push(b); return b
  }
  // Rework, disposition and hold on one case; `spend` leaves nothing behind.
  const settle = (b, qty, spend) => {
    let left = qty
    if (kind === 'rework' || (spend && r() < 0.4)) {
      const sent = spend ? left : 1 + part(left - 1), done = spend || r() < 0.6, good = done ? part(sent) : 0, back = done ? sent - good : 0, rw = uid()
      f.reworks.push({ id: rw, bs_case_id: b.id, sent_pcs: String(sent), good_pcs: done ? String(good) : null, bs_pcs: done ? String(back) : null, physical_sent_at: ts(),
        completed_at: done ? (spend || r() < 0.85 ? ts() : LATE) : null, status: done ? 'COMPLETED' : 'IN_PROGRESS', revision: rev(), good_fg_lot_id: done ? uid() : null, completion_posted: done })
      if (done && good > 0 && r() < 0.8) f.resolutions.push({ id: uid(), bs_case_id: b.id, resolution_type: 'REWORK_LAUNDRY', qty_pcs: String(good), source_rework_order_id: rw, physical_at: ts() })
      if (r() < 0.1) f.reworks.push({ id: uid(), bs_case_id: b.id, sent_pcs: '1', good_pcs: null, bs_pcs: null, physical_sent_at: ts(), completed_at: null, status: 'CANCELLED', revision: rev(), good_fg_lot_id: null, completion_posted: false })
      left = left - sent + back
    }
    if ((kind === 'dispose' || spend) && left > 0) {
      const q = spend ? left : 1 + part(left - 1), d = uid(), fg = r() < 0.4
      f.resolutions.push({ id: d, bs_case_id: b.id, resolution_type: fg ? 'OTHER' : ['SCRAP', 'WRITE_OFF', 'CASH_COMPENSATION'][Math.floor(r() * 3)], qty_pcs: String(q), source_rework_order_id: null, physical_at: ts() })
      if (fg) f.bs_fg.push({ id: uid(), bs_case_id: b.id, bs_resolution_id: d, qty_pcs: String(q), status: 'POSTED', lot_id: uid(), quality_grade: 'B', physical_at: ts() })
      if (r() < 0.2) f.bs_fg.push({ id: uid(), bs_case_id: b.id, bs_resolution_id: d, qty_pcs: String(q), status: 'REVERSED', lot_id: uid(), quality_grade: 'B', physical_at: ts() })
      left -= q
    }
    if (kind === 'hold' && left > 0 && !spend) {
      b.status = 'ON_HOLD'
      if (r() < 0.5) f.holds.push({ id: uid(), bs_case_id: b.id, action: 'RELEASE', resulting_status: 'OPEN', physical_at: at(r, true), created_at: ts() })
      f.holds.push({ id: uid(), bs_case_id: b.id, action: 'HOLD', resulting_status: 'ON_HOLD', physical_at: '2026-09-30T10:00:00+07:00', created_at: ts() })
    }
  }
  const delivery = (lines, { status = 'POSTED', legacy = false, header = uid() } = {}) => {
    const line = uid(), qty = lines.reduce((s, x) => s + x.qty, 0)
    f.deliveries.push({ id: line, group_id: g, delivery_id: header, status, physical_at: ts(), revision: rev(), qty_pcs: String(qty), target_wash_process_id: uid(), target_dyeing_color: 'BLUE' })
    const out = { line, header, sizes: [] }
    if (!legacy) for (const x of lines) { const s = { id: uid(), delivery_line_id: line, batch_id: batchOf[x.size], size_id: x.size, qty_pcs: String(x.qty), group_id: g }; f.delivery_sizes.push(s); out.sizes.push(s) }
    return out
  }
  const receipt = (d, lines, { status = 'POSTED', legacy = false } = {}) => {
    const rl = uid(), good = lines.reduce((s, x) => s + x.good, 0), bs = lines.reduce((s, x) => s + x.bs, 0)
    f.receipts.push({ id: rl, delivery_line_id: d.line, receipt_id: uid(), status, physical_at: ts(), revision: rev(), good_pcs: String(good), bs_pcs: String(bs), missing_pcs: '0', stuck_pcs: '0', group_id: g })
    const out = { id: rl, sizes: [] }
    if (!legacy) for (const x of lines) { const s = { id: uid(), receipt_line_id: rl, delivery_size_id: x.ds.id, size_id: x.ds.size_id, good_pcs: String(x.good), bs_pcs: String(x.bs), group_id: g }; f.receipt_sizes.push(s); out.sizes.push(s) }
    return out
  }
  const direct = (size, n, exhaust) => {
    const bs = exhaust ? (r() < 0.5 ? part(n) : 0) : part(Math.min(n, 4)), good = exhaust ? n - bs : part(n - bs)
    const q = qc(size, good, bs)
    if (bs > 0) { const b = bsCase(size, bs, { qcItem: q.id }); settle(b, bs, exhaust || kind === 'done') }
  }
  if (kind === 'open') return g
  if (kind === 'done' || kind === 'partial' || kind === 'bs' || kind === 'hold' || kind === 'dispose' || (kind === 'rework' && r() < 0.5)) {
    for (const size of sizes) direct(size, kind === 'partial' ? part(total[size]) : total[size], kind === 'done')
    return g
  }
  if (kind === 'manual') { const size = sizes[0], q = 1 + part(total[size] - 1); const b = bsCase(size, q, { noSize: r() < 0.5 }); settle(b, q, r() < 0.5); return g }
  if (kind === 'reversal') {
    for (const size of sizes) {
      const q = qc(size, part(total[size]), 0, null, null, 'REVERSED'); q.bs_pcs = '1'
      bsCase(size, 1, { qcItem: q.id, status: 'CANCELLED' })
      if (r() < 0.5) direct(size, part(Math.floor(total[size] / 2)), false)
    }
    if (r() < 0.5) delivery(sizes.map(size => ({ size, qty: 1 })), { status: r() < 0.5 ? 'DRAFT' : 'REVERSED' })
    if (r() < 0.6) {
      const d = delivery(sizes.map(size => ({ size, qty: 1 + part(Math.floor(total[size] / 2) - 1) })))
      const rc = receipt(d, d.sizes.map(ds => ({ ds, good: 0, bs: 1 })), { status: 'REVERSED' })
      bsCase(d.sizes[0].size_id, 1, { receipt: rc.id, rsize: rc.sizes[0].id, status: 'CANCELLED' })
    }
    return g
  }
  // Laundry paths: delivery (sizes or legacy parent-only) -> receipt -> QC.
  const exhaustAll = kind === 'laundry' && r() < 0.35
  const legacy = kind === 'legacy' || kind === 'claim'
  const sent = sizes.map(size => ({ size, qty: exhaustAll ? total[size] : 1 + part(total[size] - 1) }))
  if (kind === 'rewash') {
    // Full return unprocessed: the first delivery is reversed; a successor
    // takes the same batch-size range by ALLOCATE events.
    const first = delivery(sent, { status: 'REVERSED' }), rl = uid(), attempt = uid()
    f.receipts.push({ id: rl, delivery_line_id: first.line, receipt_id: uid(), status: 'POSTED', physical_at: ts(), revision: rev(), good_pcs: '0', bs_pcs: '0', missing_pcs: '0', stuck_pcs: '0', group_id: g })
    f.failed.push({ id: attempt, receipt_line_id: rl, delivery_id: first.header, custody_outcome: 'RETURN_UNPROCESSED', qty_pcs: first.sizes.reduce((s, x) => s + Number(x.qty_pcs), 0).toString() })
    for (const s of first.sizes) f.failed_sizes.push({ id: uid(), attempt_id: attempt, delivery_size_id: s.id, size_id: s.size_id, qty_pcs: s.qty_pcs })
    const second = delivery(sent)
    first.sizes.forEach((s, i) => f.redispatch.push({ id: uid(), event_type: 'ALLOCATE', source_id: s.id, successor_id: second.sizes[i].id, qty_pcs: s.qty_pcs, source_offset_pcs: 0, successor_offset_pcs: 0, releases_allocation_event_id: null, released_delivery_id: null }))
    const rc = receipt(second, second.sizes.map(ds => ({ ds, good: Number(ds.qty_pcs), bs: 0 })))
    rc.sizes.forEach(rs => qc(rs.size_id, part(Number(rs.good_pcs)), 0, rc.id, rs.id))
    return g
  }
  const d = delivery(sent, { legacy: legacy && sizes.length === 1 })
  if (kind === 'claim') {
    const lost = 1 + part(Math.max(0, sent[0].qty - 2))
    f.claims.push({ id: uid(), delivery_id: d.header, receipt_line_id: null, claim_type: r() < 0.5 ? 'MISSING' : 'STUCK', qty_pcs: String(Math.min(lost, sent[0].qty)), status: r() < 0.2 ? 'REJECTED' : 'OPEN', opened_at: ts(), resolved_at: null, revision: rev(), delivery_line_count: 1 })
    if (r() < 0.3) f.claims.push({ id: uid(), delivery_id: d.header, receipt_line_id: null, claim_type: 'OTHER', qty_pcs: '1', status: 'OPEN', opened_at: ts(), resolved_at: null, revision: rev(), delivery_line_count: 1 })
    return g
  }
  if (kind === 'retry') {
    const rl = uid(), attempt = uid()
    f.receipts.push({ id: rl, delivery_line_id: d.line, receipt_id: uid(), status: 'POSTED', physical_at: ts(), revision: rev(), good_pcs: '0', bs_pcs: '0', missing_pcs: '0', stuck_pcs: '0', group_id: g })
    f.failed.push({ id: attempt, receipt_line_id: rl, delivery_id: d.header, custody_outcome: 'RETRY_AT_VENDOR', qty_pcs: '1' })
    if (d.sizes.length) f.failed_sizes.push({ id: uid(), attempt_id: attempt, delivery_size_id: d.sizes[0].id, size_id: d.sizes[0].size_id, qty_pcs: '1' })
  }
  if (d.sizes.length === 0) {
    const n = sent[0].qty, bs = part(Math.min(2, n)), good = exhaustAll ? n - bs : part(n - bs), rc = receipt(d, [{ good, bs }], { legacy: true })
    if (good) qc(sent[0].size, exhaustAll ? good : part(good), 0, rc.id, null)
    if (bs) { const b = bsCase(sent[0].size, bs, { receipt: rc.id }); settle(b, bs, exhaustAll) }
    return g
  }
  const lines = d.sizes.map(ds => { const n = Number(ds.qty_pcs), bs = part(Math.min(3, n)); return { ds, bs, good: exhaustAll ? n - bs : part(n - bs) } })
  const rc = receipt(d, lines, { legacy: false })
  rc.sizes.forEach((rs, i) => {
    const good = Number(rs.good_pcs), take = exhaustAll ? good : part(good), qbs = exhaustAll ? 0 : part(Math.min(2, take)), q = qc(rs.size_id, take - qbs, qbs, rc.id, r() < 0.5 ? rs.id : null)
    if (qbs) { const b = bsCase(rs.size_id, qbs, { qcItem: q.id }); settle(b, qbs, false) }
    if (lines[i].bs) { const b = bsCase(rs.size_id, lines[i].bs, { receipt: rc.id, rsize: rs.id }); settle(b, lines[i].bs, exhaustAll) }
  })
  if (exhaustAll) for (const x of sent) for (const size of [x.size]) { const left = total[size] - x.qty; if (left > 0) qc(size, left, 0) }
  return g
}

// Every piece reached FG or EXIT: what the PL-8 scale finding is about.
function exhausted(f, r, opts, positionsPerSize) {
  const uid = () => `${hex(r, 8)}-${hex(r, 4)}-4${hex(r, 3)}-8${hex(r, 3)}-${hex(r, 12)}`, ts = () => at(r, false)
  const g = uid(), product = uid(), sizes = opts.sizePool.slice(0, opts.sizesPerGroup || 1)
  f.groups.push({ id: g, po_id: uid(), revision: '1', status: 'POSTED', pattern_id: uid(), pattern_revision_snapshot: 1, cut_at: ts(), picked_up_at: ts(), material_issue_posted: true, model_id: uid() })
  for (const size of sizes) {
    f.yields.push({ id: uid(), group_id: g, size_id: size, qty_pcs: '3', revision: '1' })
    if (positionsPerSize === 2) { f.qc.push({ id: uid(), group_id: g, inspection_id: uid(), status: 'POSTED', physical_at: ts(), revision: '1', receipt_line_id: null, receipt_size_id: null, final_product_id: product, size_id: size, product_root: product, good_pcs: '3', bs_pcs: '0' }); continue }
    // 4 positions: PRE, delivery, receipt, FG (laundry path, all good).
    const line = uid(), header = uid(), ds = uid(), rl = uid(), rs = uid()
    f.deliveries.push({ id: line, group_id: g, delivery_id: header, status: 'POSTED', physical_at: ts(), revision: '1', qty_pcs: '3', target_wash_process_id: uid(), target_dyeing_color: 'BLUE' })
    f.batches.push({ id: uid(), batch_id: header, pickup_id: uid(), group_id: g, status: 'POSTED', picked_up_at: ts(), revision: '1', yield_id: f.yields.at(-1).id, qty_pcs: '3' })
    f.delivery_sizes.push({ id: ds, delivery_line_id: line, batch_id: header, size_id: size, qty_pcs: '3', group_id: g })
    f.receipts.push({ id: rl, delivery_line_id: line, receipt_id: uid(), status: 'POSTED', physical_at: ts(), revision: '1', good_pcs: '3', bs_pcs: '0', missing_pcs: '0', stuck_pcs: '0', group_id: g })
    f.receipt_sizes.push({ id: rs, receipt_line_id: rl, delivery_size_id: ds, size_id: size, good_pcs: '3', bs_pcs: '0', group_id: g })
    f.qc.push({ id: uid(), group_id: g, inspection_id: uid(), status: 'POSTED', physical_at: ts(), revision: '1', receipt_line_id: rl, receipt_size_id: rs, final_product_id: product, size_id: size, product_root: product, good_pcs: '3', bs_pcs: '0' })
  }
}

// Planted faults, each aimed at one refusal (or a duplicate-key edge) of the
// predecessor. `null` plants nothing.
export const DEFECTS = [null, null, null, null, 'NOT_POSTED', 'NO_YIELDS', 'BAD_YIELD_QTY', 'NEGATIVE_QC', 'FRACTION_QC', 'OVER_QC', 'DELIVERY_TOTAL', 'BATCH_LINEAGE',
  'LEGACY_MULTI_SIZE', 'RECEIPT_TOTAL', 'RECEIPT_LINEAGE', 'RECEIPT_MISSING', 'FAILED_PHYSICAL', 'CLAIM_RECEIPT', 'CLAIM_LINES', 'QC_LINEAGE', 'QC_PARENT',
  'CANCELLED_SOURCE', 'BS_LINEAGE', 'BS_SIZE', 'REWORK_SOURCE', 'REWORK_UNPOSTED', 'REWORK_MISMATCH', 'RESOLUTION_SOURCE', 'RESOLUTION_LINEAGE', 'RESOLUTION_TYPE',
  'DUPLICATE_BS_FG', 'BS_FG_MISMATCH', 'HOLD_STATE', 'HOLD_ZERO', 'REDISPATCH_OVERLAP', 'DUPLICATE_QC_ID', 'NULL_REVISION', 'DUPLICATE_GROUP', 'DUPLICATE_DELIVERY',
  'DUPLICATE_RECEIPT', 'DUPLICATE_YIELD_GROUP', 'LEGACY_RECEIPT_MULTI_SIZE', 'DUPLICATE_BS', 'NULL_BS_ID', 'BAD_TIMESTAMP', 'SHUFFLE', 'CAPTURE_INCOMPLETE', 'BAD_CLOCK', 'FACTS_NOT_ARRAY', 'BAD_BS_QTY', 'BAD_SIZE_QTY', 'BAD_RECEIPT_SIZE_QTY']
function plant(c, r, defect) {
  const f = c.facts, any = a => a.length ? a[Math.floor(r() * a.length)] : null, uid = () => `${hex(r, 8)}-${hex(r, 4)}-4${hex(r, 3)}-8${hex(r, 3)}-${hex(r, 12)}`
  const shuffle = a => { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1));[a[i], a[j]] = [a[j], a[i]] } }
  const x = () => {
    switch (defect) {
      case 'NOT_POSTED': return any(f.groups) && (any(f.groups).material_issue_posted = false)
      case 'NO_YIELDS': { const g = any(f.groups); if (g) f.yields = f.yields.filter(y => y.group_id !== g.id); return }
      case 'BAD_YIELD_QTY': return any(f.yields) && (any(f.yields).qty_pcs = 'x1')
      case 'NEGATIVE_QC': return any(f.qc) && (any(f.qc).good_pcs = '-1')
      case 'FRACTION_QC': return any(f.qc) && (any(f.qc).bs_pcs = '1.5')
      case 'OVER_QC': return any(f.qc) && (any(f.qc).good_pcs = '999')
      case 'DELIVERY_TOTAL': { const d = any(f.deliveries.filter(d => f.delivery_sizes.some(s => s.delivery_line_id === d.id))); if (d) d.qty_pcs = String(Number(d.qty_pcs) + 1); return }
      case 'BATCH_LINEAGE': return any(f.delivery_sizes) && (any(f.delivery_sizes).batch_id = uid())
      case 'LEGACY_MULTI_SIZE': { const s = any(f.delivery_sizes); if (s) f.delivery_sizes = f.delivery_sizes.filter(x => x.delivery_line_id !== s.delivery_line_id); return }
      case 'RECEIPT_TOTAL': return any(f.receipts) && (any(f.receipts).good_pcs = '77')
      case 'RECEIPT_LINEAGE': return any(f.receipt_sizes) && (any(f.receipt_sizes).delivery_size_id = uid())
      case 'LEGACY_RECEIPT_MULTI_SIZE': { const d = any(f.deliveries.filter(d => f.delivery_sizes.filter(s => s.delivery_line_id === d.id).length > 1)), rc = d && f.receipts.find(x => x.delivery_line_id === d.id && f.receipt_sizes.some(s => s.receipt_line_id === x.id)); if (rc) f.receipt_sizes = f.receipt_sizes.filter(s => s.receipt_line_id !== rc.id); return }
      case 'RECEIPT_MISSING': return any(f.receipts) && (any(f.receipts).missing_pcs = '1')
      case 'FAILED_PHYSICAL': { const a = any(f.failed); const rc = a && f.receipts.find(x => x.id === a.receipt_line_id); if (rc) rc.good_pcs = '1'; return }
      case 'CLAIM_RECEIPT': return any(f.claims) && (any(f.claims).receipt_line_id = uid())
      case 'CLAIM_LINES': return any(f.claims) && (any(f.claims).delivery_line_count = 2)
      case 'QC_LINEAGE': return any(f.qc) && (any(f.qc).receipt_line_id = uid())
      case 'QC_PARENT': { const q = any(f.qc); if (q) { q.receipt_line_id = null; q.receipt_size_id = uid() } return }
      case 'CANCELLED_SOURCE': { const b = any(f.bs.filter(b => b.status === 'CANCELLED')); if (b) b.group_id = uid(); else if (f.bs.length) Object.assign(any(f.bs), { status: 'CANCELLED', qc_item_id: null, receipt_line_id: null }); return }
      case 'BS_LINEAGE': return any(f.bs) && (any(f.bs).qc_item_id = uid())
      case 'BS_SIZE': { const b = any(f.bs); if (b) { b.size_id = null; const gs = f.yields.filter(y => y.group_id === b.group_id); if (gs.length) f.yields.push({ ...gs[0], id: uid(), size_id: uid() }) } return }
      case 'REWORK_SOURCE': return any(f.reworks) && (any(f.reworks).bs_case_id = uid())
      case 'REWORK_UNPOSTED': { const w = any(f.reworks.filter(w => w.status === 'COMPLETED')); if (w) w.completion_posted = false; return }
      case 'REWORK_MISMATCH': { const w = any(f.reworks.filter(w => w.status === 'COMPLETED')); if (w) w.good_pcs = String(Number(w.good_pcs) + 1); return }
      case 'RESOLUTION_SOURCE': return any(f.resolutions) && (any(f.resolutions).bs_case_id = uid())
      case 'RESOLUTION_LINEAGE': { const d = any(f.resolutions.filter(d => d.source_rework_order_id)); if (d) d.qty_pcs = String(Number(d.qty_pcs) + 1); return }
      case 'RESOLUTION_TYPE': return any(f.resolutions) && (any(f.resolutions).resolution_type = 'GIFT')
      case 'DUPLICATE_BS_FG': { const x = any(f.bs_fg.filter(x => x.status === 'POSTED')); if (x) f.bs_fg.push({ ...x, id: uid() }); return }
      case 'BS_FG_MISMATCH': { const x = any(f.bs_fg); if (x) x.qty_pcs = String(Number(x.qty_pcs) + 1); return }
      case 'HOLD_STATE': { const b = any(f.bs.filter(b => b.status !== 'CANCELLED')); if (b) b.status = b.status === 'ON_HOLD' ? 'OPEN' : 'ON_HOLD'; return }
      case 'HOLD_ZERO': { const b = any(f.bs.filter(b => b.status === 'ON_HOLD')); if (b) f.resolutions.push({ id: uid(), bs_case_id: b.id, resolution_type: 'SCRAP', qty_pcs: b.qty_pcs, source_rework_order_id: null, physical_at: LATE }); return }
      case 'REDISPATCH_OVERLAP': { const e = any(f.redispatch); if (e) f.redispatch.push({ ...e, id: uid() }); return }
      case 'DUPLICATE_QC_ID': { const q = any(f.qc); if (q) f.qc.push({ ...q, group_id: any(f.groups).id, good_pcs: '1' }); return }
      case 'NULL_REVISION': return any(f.qc) && (any(f.qc).revision = null)
      case 'DUPLICATE_GROUP': { const g = any(f.groups); if (g) f.groups.splice(Math.floor(r() * f.groups.length), 0, { ...g, revision: '9', picked_up_at: g.picked_up_at ? null : CAPTURED_AT }); return }
      case 'DUPLICATE_DELIVERY': { const d = any(f.deliveries); if (d) f.deliveries.push({ ...d, qty_pcs: r() < 0.5 ? d.qty_pcs : '1', physical_at: r() < 0.5 ? d.physical_at : LATE }); return }
      case 'DUPLICATE_RECEIPT': { const x = any(f.receipts); if (x) f.receipts.push({ ...x }); return }
      case 'DUPLICATE_YIELD_GROUP': { const y = any(f.yields); if (y) f.yields.push({ ...y, id: uid(), group_id: y.group_id.toUpperCase() }); return }
      case 'DUPLICATE_BS': { const b = any(f.bs); if (b) f.bs.push({ ...b, qty_pcs: r() < 0.5 ? b.qty_pcs : '1', size_id: r() < 0.3 ? null : b.size_id }); return }
      case 'NULL_BS_ID': return any(f.bs) && (any(f.bs).id = null)
      case 'BAD_TIMESTAMP': { const w = any(f.reworks.filter(w => w.status === 'COMPLETED')) ?? any(f.holds); if (w) w[w.completed_at ? 'completed_at' : 'physical_at'] = 'not-a-time'; return }
      case 'SHUFFLE': for (const k of Object.keys(f)) shuffle(f[k]); return
      case 'CAPTURE_INCOMPLETE': c.status = 'INCOMPLETE'; return
      case 'BAD_CLOCK': c.captured_at = 'not-a-clock'; return
      case 'FACTS_NOT_ARRAY': f[any(['batches', 'failed', 'receipt_sizes', 'holds', 'bs_fg', 'delivery_sizes'])] = { not: 'an array' }; return
      case 'BAD_BS_QTY': return any(f.bs) && (any(f.bs).qty_pcs = '2e')
      case 'BAD_SIZE_QTY': return any(f.delivery_sizes) && (any(f.delivery_sizes).qty_pcs = 'n/a')
      case 'BAD_RECEIPT_SIZE_QTY': return any(f.receipt_sizes) && (any(f.receipt_sizes).bs_pcs = '')
      case null: return
      default: throw new Error(defect)
    }
  }
  x()
}

// A cutting capture: generated lifecycles plus `exhaustedGroups` spent groups.
export function cuttingInput(seed, { groups = 12, exhaustedGroups = 0, positionsPerSize = 2, sizesPerGroup = 0, defect = null, ties = false } = {}) {
  const r = rng(seed), f = emptyFacts(), sizePool = Array.from({ length: 5 }, (_, i) => `00000000-0000-4000-8000-00000000000${i + 1}`)
  for (let i = 0; i < groups; i++) group(f, r, KINDS[Math.floor(r() * KINDS.length)], { sizesPerGroup, ties, sizePool })
  for (let i = 0; i < exhaustedGroups; i++) exhausted(f, r, { sizesPerGroup, sizePool }, positionsPerSize)
  for (const k of Object.keys(f)) f[k].sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0))
  const c = { contract_version: 'cp7.cutting-facts.v1', knowledge_mode: 'CURRENT', captured_at: CAPTURED_AT, scope: f.groups.map(g => g.id), facts: f, status: 'COMPLETE' }
  plant(c, r, defect)
  return c
}

// Opening WIP/BS and unsourced BS for normalize_production (through settle_bs);
// `other: false` leaves them empty (cutting origins only).
export function productionInput(seed, opts = {}) {
  const r = rng(seed * 7 + 3), cut = cuttingInput(seed, { ...opts, defect: DEFECTS.includes(opts.defect) ? opts.defect : null }), uid = () => `${hex(r, 8)}-${hex(r, 4)}-4${hex(r, 3)}-8${hex(r, 3)}-${hex(r, 12)}`
  const o = Object.fromEntries(['origins', 'pickups', 'outputs', 'splits', 'claims', 'claim_events', 'non_po', 'bs', 'reworks', 'resolutions', 'holds', 'bs_fg'].map(k => [k, []]))
  const size = '00000000-0000-4000-8000-000000000001', origins = opts.other === false ? 0 : 1 + Math.floor(r() * 4)
  for (let i = 0; i < origins; i++) {
    const id = uid(), qty = 5 + Math.floor(r() * 20), bs = r() < 0.3, caseId = bs ? uid() : null
    o.origins.push({ id, source_row_id: uid(), batch_id: uid(), po_id: uid(), size_id: size, stage: ['CUTTING', 'SEWING', 'LAUNDRY', 'QC'][Math.floor(r() * 4)], qty_pcs: String(qty), bs_case_id: caseId,
      balance_type: bs ? 'BS' : 'WIP', opening_qty_pcs: String(qty), product_id: uid(), model_id: uid(), customer_id: r() < 0.2 ? uid() : null, vendor_id: null, contractor_id: null,
      opening_date: '2026-08-01', header_status: 'POSTED', batch_status: 'POSTED' })
    if (bs) {
      o.bs.push({ id: caseId, product_id: uid(), size_id: size, qty_pcs: String(qty), status: 'OPEN', physical_at: at(r, false), revision: '1' })
      if (r() < 0.5) o.resolutions.push({ id: uid(), bs_case_id: caseId, resolution_type: 'SCRAP', qty_pcs: String(1 + Math.floor(r() * qty)), source_rework_order_id: null, physical_at: at(r, false) })
      continue
    }
    if (r() < 0.6) o.outputs.push({ id: uid(), opening_item_id: id, lot_id: uid(), qty_pcs: String(Math.floor(r() * qty / 2)), physical_at: at(r, false), reversed_at: null, size_id: size })
    if (r() < 0.3) { const s = uid(), c = uid(); o.splits.push({ id: s, opening_item_id: id, bs_case_id: c, product_id: uid(), size_id: size, qty_pcs: '1', physical_at: at(r, false), reversed_at: null })
      o.bs.push({ id: c, product_id: uid(), size_id: size, qty_pcs: '1', status: r() < 0.5 ? 'ON_HOLD' : 'OPEN', physical_at: at(r, false), revision: '1' })
      if (o.bs.at(-1).status === 'ON_HOLD') o.holds.push({ id: uid(), bs_case_id: c, action: 'HOLD', resulting_status: 'ON_HOLD', physical_at: at(r, false), created_at: at(r, false) }) }
  }
  for (let i = 0; i < (opts.other === false ? 0 : Math.floor(r() * 3)); i++) { const id = uid(); o.non_po.push({ id, qty_pcs: '2', size_id: size, revision: '1', untracked_type: 'LEGACY', physical_at: at(r, false) })
    o.bs.push({ id, product_id: uid(), size_id: size, qty_pcs: '2', status: 'OPEN', physical_at: at(r, false), revision: '1' })
    if (r() < 0.5) { const w = uid(); o.reworks.push({ id: w, bs_case_id: id, sent_pcs: '2', good_pcs: '1', bs_pcs: '1', physical_sent_at: at(r, false), completed_at: at(r, false), status: 'COMPLETED', revision: '1', good_fg_lot_id: uid(), completion_posted: true })
      o.resolutions.push({ id: uid(), bs_case_id: id, resolution_type: 'REWORK_SEWING', qty_pcs: '1', source_rework_order_id: w, physical_at: at(r, false) }) } }
  if (opts.defect === 'OTHER_REWORK_SOURCE' && o.reworks.length) o.reworks[0].bs_case_id = uid()
  if (opts.defect === 'OTHER_OVER_OUTPUT' && o.outputs.length) o.outputs[0].qty_pcs = '999'
  return { contract_version: 'cp7.production-facts.v1', captured_at: cut.captured_at, status: cut.status, facts: { cutting: cut.facts, other: o } }
}
export const PRODUCTION_DEFECTS = [null, null, 'OTHER_REWORK_SOURCE', 'OTHER_OVER_OUTPUT', 'NEGATIVE_QC', 'HOLD_STATE', 'DUPLICATE_DELIVERY']

// Conserved graphs for reconcile on its own, including reversal events that
// normalization never emits, with planted faults.
export const GRAPH_DEFECTS = [null, null, null, 'DUP_POOL', 'DUP_NODE', 'BAD_STAGE', 'NODE_POOL', 'DUP_EVENT', 'ORDINAL', 'ZERO', 'REVERSE_TWICE', 'REVERSE_LATER',
  'REVERSE_SELF', 'REVERSE_INPUT', 'REVERSE_QTY', 'REVERSE_FROM', 'REVERSE_OF_REVERSAL', 'SELF_LOOP', 'UNKNOWN_DST', 'UNKNOWN_SRC', 'CROSS_POOL', 'INPUT_EXCEEDS', 'NEGATIVE',
  'UNACCOUNTED', 'BAD_PCS', 'BAD_KEY', 'NUMBER_REVERSES_KEY', 'INCOMPLETE', 'SHAPE', 'EXTRA_FIELD', 'BAD_ORIGIN', 'MANY_POOLS', 'DUP_REF']
export function graphInput(seed, { pools = 6, defect = null } = {}) {
  const r = rng(seed * 13 + 5), ref = id => [{ kind: 'K', id, revision: '1' }], P = [], N = [], E = [], bal = {}
  const stages = ['CUT_UNASSIGNED', 'SEWING_ACTIVE', 'LAUNDRY_OUTSTANDING', 'AWAIT_QC', 'FG', 'BS', 'MISSING', 'HOLD', 'REWORK', 'EXIT']
  const ev = (pool, from, to, qty, reverses = null) => { E.push({ key: `E${hex(r, 3)}${E.length}`, pool_key: pool, from_node: from, to_node: to, qty_pcs: String(qty), ordinal: String(E.length + 1), reverses_key: reverses, refs: ref(`e${E.length}`) }) }
  for (let i = 0; i < pools; i++) {
    const key = `CUT:${hex(r, 4)}:${i}`, input = 1 + Math.floor(r() * 40), nodes = []
    P.push({ key, size_id: `S${i % 3}`, input_pcs: String(input), origin: ['CUTTING', 'OPENING', 'NON_PO'][i % 3], ownership: r() < 0.8 ? 'COMPANY' : 'CUSTOMER', refs: ref(`p${i}`) })
    for (let j = 0; j < 2 + Math.floor(r() * 4); j++) { const k = `${key}:${['PRE', 'D', 'R', 'FG', 'BS', 'X'][j]}${hex(r, 2)}`; nodes.push(k); bal[k] = 0
      N.push({ key: k, pool_key: key, stage: j === 0 ? 'CUT_UNASSIGNED' : stages[Math.floor(r() * stages.length)], refs: ref(`n${N.length}`) }) }
    ev(key, null, nodes[0], input); bal[nodes[0]] = input
  }
  // Moves and exact reversals in a shuffled global order with valid prefixes.
  for (let step = 0; step < pools * 5; step++) {
    const pool = P[Math.floor(r() * P.length)].key, nodes = N.filter(n => n.pool_key === pool).map(n => n.key)
    const rev = E.filter(e => e.pool_key === pool && e.from_node && !e.reverses_key && !E.some(x => x.reverses_key === e.key) && bal[e.to_node] >= Number(e.qty_pcs))
    if (rev.length && r() < 0.3) { const e = rev[Math.floor(r() * rev.length)]; ev(pool, e.to_node, e.from_node, e.qty_pcs, e.key); bal[e.to_node] -= Number(e.qty_pcs); bal[e.from_node] += Number(e.qty_pcs); continue }
    const from = nodes.filter(k => bal[k] > 0)[0], to = nodes[1 + Math.floor(r() * (nodes.length - 1))]
    if (!from || from === to) continue
    const q = 1 + Math.floor(r() * bal[from]); ev(pool, from, to, q); bal[from] -= q; bal[to] += q
  }
  const g = { contract_version: 'cp7.wip-graph.v1', snapshot_id: `snap-${seed}`, complete: true, pools: P, nodes: N, events: E }
  const any = a => a[Math.floor(r() * a.length)], moves = E.filter(e => e.from_node), revs = E.filter(e => e.reverses_key)
  switch (defect) {
    case 'DUP_POOL': P.push({ ...any(P) }); break
    case 'DUP_NODE': N.splice(Math.floor(r() * N.length), 0, { ...any(N) }); break
    case 'BAD_STAGE': any(N).stage = 'LIMBO'; break
    case 'NODE_POOL': any(N).pool_key = 'CUT:none'; break
    case 'DUP_EVENT': { const e = any(E); E.splice(E.indexOf(e) + 1 + Math.floor(r() * 3), 0, { ...e, ordinal: e.ordinal }); E.forEach((x, i) => { x.ordinal = String(i + 1) }); break }
    case 'ORDINAL': { const e = any(E.slice(1)); if (e) e.ordinal = '1'; break }
    case 'ZERO': any(E).qty_pcs = '0'; break
    case 'REVERSE_TWICE': { const e = any(revs); if (e) ev(e.pool_key, e.from_node, e.to_node, e.qty_pcs, e.reverses_key); break }
    case 'REVERSE_LATER': { const e = any(moves); if (e) E[0].reverses_key = e.key; ev(e?.pool_key ?? P[0].key, e?.to_node ?? N[0].key, e?.from_node ?? N[1].key, e?.qty_pcs ?? '1', e?.key ?? 'nowhere'); break }
    case 'REVERSE_SELF': { const e = any(moves); if (e) e.reverses_key = e.key; break }
    case 'REVERSE_INPUT': { const e = E.find(x => !x.from_node); ev(e.pool_key, e.to_node, N.find(n => n.pool_key === e.pool_key && n.key !== e.to_node)?.key ?? e.to_node, e.qty_pcs, e.key); break }
    case 'REVERSE_QTY': { const e = any(revs); if (e) e.qty_pcs = String(Number(e.qty_pcs) + 1); else if (moves.length) { const m = any(moves); ev(m.pool_key, m.to_node, m.from_node, Number(m.qty_pcs) + 1, m.key) } break }
    case 'REVERSE_FROM': { const e = any(revs); if (e) [e.from_node, e.to_node] = [e.to_node, e.from_node]; break }
    case 'REVERSE_OF_REVERSAL': { const e = any(revs); if (e) ev(e.pool_key, e.to_node, e.from_node, e.qty_pcs, e.key); break }
    case 'SELF_LOOP': { const e = any(moves); if (e) e.to_node = e.from_node; break }
    case 'UNKNOWN_DST': any(E).to_node = 'nowhere'; break
    case 'UNKNOWN_SRC': { const e = any(moves); if (e) e.from_node = 'nowhere'; break }
    case 'CROSS_POOL': { const e = any(moves); if (e) e.pool_key = P.find(p => p.key !== e.pool_key)?.key ?? e.pool_key; break }
    case 'INPUT_EXCEEDS': { const p = any(P); ev(p.key, null, N.find(n => n.pool_key === p.key).key, 1); break }
    case 'NEGATIVE': { const e = any(moves); if (e) e.qty_pcs = String(Number(e.qty_pcs) + 50); break }
    case 'UNACCOUNTED': { const p = any(P); p.input_pcs = String(Number(p.input_pcs) + 1); break }
    case 'BAD_PCS': any([...E, ...P]).qty_pcs = '01'; any(P).input_pcs = r() < 0.5 ? '1.0' : '-3'; break
    case 'BAD_KEY': any([...P, ...N, ...E]).key = r() < 0.5 ? 7 : ' padded'; break
    case 'NUMBER_REVERSES_KEY': { const e = any(revs) ?? any(moves); if (e) e.reverses_key = 12; break }
    case 'INCOMPLETE': g.complete = false; break
    case 'SHAPE': g.nodes = {}; break
    case 'EXTRA_FIELD': any([...P, ...N, ...E]).extra = true; break
    case 'BAD_ORIGIN': any(P).origin = null; break
    case 'MANY_POOLS': for (let i = 0; i < 1001; i++) P.push({ ...P[0], key: `X${i}` }); break
    case 'DUP_REF': { const n = any(N); n.refs = [...n.refs, ...n.refs]; break }
    case null: break
    default: throw new Error(defect)
  }
  return g
}

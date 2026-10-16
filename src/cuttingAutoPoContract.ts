import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'

// Owner D15-6 (SOL-R1-002): Buat Potongan with the Production Order made automatically when the cutting is posted.
// Closed parsers for scripts/cp7-src/cutting-correction/auto-po.sql. Drafts live only in the facade (no PO, stock or journal).
export type AutoPoSize = { id: string; code: string }
export type AutoPoModel = { id: string; code: string; name: string; sizes: AutoPoSize[] }
export type AutoPoDraftRow = { id: string; modelId: string; modelCode: string; modelName: string; cutAt: string; pieces: number; rowVersion: number; updatedAt: string }
export type AutoPoRoll = {
  rollId: string; rollNumber: string; materialId: string; materialSku: string; materialName: string; unitCode: string
  supplierName: string | null; originalQty: number; availableQty: number
}
export type AutoPoCutting = {
  pattern_id: string; source_location_id: string; cut_at: string; notes: string | null
  size_slots: { slot_no: number; size_id: string; drawing_no: number }[]
  rolls: { roll_id: string; qty_issued: number; qty_consumed: number; qty_reported_remaining: number; yields: { slot_no: number; qty_pcs: number }[] }[]
}
export type AutoPoSelected = {
  id: string; rowVersion: number; model: AutoPoModel; pattern: { id: string; code: string; revision: string; name: string } | null
  cutting: AutoPoCutting; rolls: AutoPoRoll[]
}
export type AutoPoWorkspace = {
  today: string; canDraft: boolean; canPost: boolean
  models: { total: number; offset: number; query: string; rows: AutoPoModel[] }
  drafts: AutoPoDraftRow[]; selected: AutoPoSelected | null
}
export type AutoPoAction = 'SAVE_DRAFT' | 'DELETE' | 'POST'
export type AutoPoOutcome = {
  action: AutoPoAction; draftId: string | null; rowVersion: number | null
  poId: string | null; poNumber: string | null; groupId: string | null; groupNumber: string | null; totalPieces: number | null
}

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/
function fail(what: string): never { throw new Error(`Respons PO otomatis tidak cocok (${what}).`) }
type Obj = Record<string, unknown>
const isObj = (v: unknown): v is Obj => Boolean(v) && typeof v === 'object' && !Array.isArray(v)
const obj = (v: unknown, what: string) => isObj(v) ? v : fail(what)
const arr = (v: unknown, what: string) => Array.isArray(v) ? v : fail(what)
const str = (v: unknown, what: string) => typeof v === 'string' ? v : fail(what)
const id = (v: unknown, what: string) => typeof v === 'string' && uuid.test(v) ? v : fail(what)
const int = (v: unknown, what: string) => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 ? v : fail(what)
const num = (v: unknown, what: string) => typeof v === 'number' && Number.isFinite(v) ? v : typeof v === 'string' && v.trim() !== '' && Number.isFinite(Number(v)) ? Number(v) : fail(what)
const bool = (v: unknown, what: string) => typeof v === 'boolean' ? v : fail(what)
function keys(o: Obj, expected: string[], what: string) {
  const got = Object.keys(o).sort(), want = [...expected].sort()
  if (got.length !== want.length || got.some((k, i) => k !== want[i])) fail(what)
}

function model(v: unknown): AutoPoModel {
  const m = obj(v, 'model'); keys(m, ['id', 'code', 'name', 'sizes'], 'model')
  return { id: id(m.id, 'model.id'), code: str(m.code, 'model.code'), name: str(m.name, 'model.name'),
    sizes: arr(m.sizes, 'sizes').map(s => { const x = obj(s, 'size'); keys(x, ['id', 'code'], 'size'); return { id: id(x.id, 'size.id'), code: str(x.code, 'size.code') } }) }
}

export function parseAutoPoWorkspace(value: unknown): AutoPoWorkspace {
  const w = obj(value, 'ruang kerja')
  keys(w, ['contract_version', 'today', 'can_draft', 'can_post', 'models', 'drafts', 'selected_draft', 'business_DML'], 'ruang kerja')
  if (w.contract_version !== 'cp7.cutting-auto-po-workspace.v1' || w.business_DML !== false) fail('kontrak')
  const m = obj(w.models, 'models'); keys(m, ['total', 'offset', 'query', 'rows'], 'models')
  const drafts = arr(w.drafts, 'drafts').map(v => {
    const d = obj(v, 'draft'); keys(d, ['id', 'model_id', 'model_code', 'model_name', 'cut_at', 'pieces', 'row_version', 'updated_at'], 'draft')
    return { id: id(d.id, 'draft.id'), modelId: id(d.model_id, 'draft.model'), modelCode: str(d.model_code, 'draft.code'), modelName: str(d.model_name, 'draft.name'),
      cutAt: str(d.cut_at, 'draft.cut_at'), pieces: int(d.pieces, 'draft.pieces'), rowVersion: int(d.row_version, 'draft.version'), updatedAt: str(d.updated_at, 'draft.updated') }
  })
  let selected: AutoPoSelected | null = null
  if (w.selected_draft !== null && w.selected_draft !== undefined) {
    const s = obj(w.selected_draft, 'draft terpilih')
    keys(s, ['id', 'model_id', 'row_version', 'cutting', 'pattern', 'model', 'rolls'], 'draft terpilih')
    const sm = model(s.model)
    if (sm.id !== id(s.model_id, 'draft.model_id')) fail('draft.model')
    const p = s.pattern === null ? null : obj(s.pattern, 'pola')
    if (p) keys(p, ['id', 'code', 'revision', 'name'], 'pola')
    const cutting = obj(s.cutting, 'isi draft') as unknown as AutoPoCutting
    selected = { id: id(s.id, 'draft.id'), rowVersion: int(s.row_version, 'draft.version'), model: sm, cutting,
      pattern: p ? { id: id(p.id, 'pola.id'), code: str(p.code, 'pola.code'), revision: str(p.revision, 'pola.revisi'), name: str(p.name, 'pola.nama') } : null,
      rolls: arr(s.rolls, 'roll').map(v => {
        const r = obj(v, 'roll')
        keys(r, ['roll_id', 'roll_number', 'material_id', 'material_sku', 'material_name', 'unit_code', 'supplier_name', 'original_qty', 'available_qty'], 'roll')
        return { rollId: id(r.roll_id, 'roll.id'), rollNumber: str(r.roll_number, 'roll.no'), materialId: id(r.material_id, 'roll.material'),
          materialSku: str(r.material_sku, 'roll.sku'), materialName: str(r.material_name, 'roll.nama'), unitCode: str(r.unit_code, 'roll.unit'),
          supplierName: r.supplier_name === null ? null : str(r.supplier_name, 'roll.supplier'), originalQty: num(r.original_qty, 'roll.awal'), availableQty: num(r.available_qty, 'roll.tersedia') }
      }) }
  }
  return { today: str(w.today, 'today'), canDraft: bool(w.can_draft, 'can_draft'), canPost: bool(w.can_post, 'can_post'),
    models: { total: int(m.total, 'total'), offset: int(m.offset, 'offset'), query: str(m.query, 'query'), rows: arr(m.rows, 'rows').map(model) },
    drafts, selected }
}

export function autoPoPayload(action: AutoPoAction, draft: { id: string; version: number } | null, modelId: string | null, cutting: AutoPoCutting | null, reason: string): Json {
  const base: Record<string, Json> = { action, draft_id: draft?.id ?? null, expected_version: draft?.version ?? null }
  if (action === 'DELETE') { if (!draft) fail('draft'); return base }
  if (!modelId || !cutting) fail('isian')
  base.model_id = modelId; base.cutting = cutting as unknown as Json
  if (action === 'POST') { if (reason.trim().length < 5) fail('alasan'); base.change_reason = reason.trim() }
  return base
}

export function validateAutoPoOutcome(value: unknown, envelope: ProductionEnvelope): AutoPoOutcome {
  const o = obj(value, 'hasil')
  const action = envelope.action as AutoPoAction
  if (o.contract_version !== 'cp7.cutting-auto-po-outcome.v1' || o.kind !== 'COMMITTED_OUTCOME' || o.action !== action || o.request_id !== envelope.id) fail('hasil')
  if (action === 'POST') {
    keys(o, ['contract_version', 'kind', 'action', 'request_id', 'draft_id', 'po_id', 'po_number', 'cutting_group_id', 'group_number', 'total_pieces', 'material_issue_posted'], 'hasil')
    if (o.material_issue_posted !== true || typeof o.po_number !== 'string' || !/^PO-\d{6}-\d{3,}$/.test(o.po_number)) fail('hasil')
    const payload = envelope.payload as Record<string, unknown>
    if ((o.draft_id ?? null) !== (payload.draft_id ?? null)) fail('draft')
    return { action, draftId: o.draft_id === null ? null : id(o.draft_id, 'draft'), rowVersion: null, poId: id(o.po_id, 'po'), poNumber: o.po_number,
      groupId: id(o.cutting_group_id, 'potongan'), groupNumber: str(o.group_number, 'nomor potongan'), totalPieces: int(o.total_pieces, 'pcs') }
  }
  keys(o, ['contract_version', 'kind', 'action', 'request_id', 'draft_id', 'row_version'], 'hasil')
  return { action, draftId: id(o.draft_id, 'draft'), rowVersion: int(o.row_version, 'versi'), poId: null, poNumber: null, groupId: null, groupNumber: null, totalPieces: null }
}

import { parseCuttingWorkspace, type CuttingDraft, type CuttingWorkspace } from './cuttingPersistence'

export type CuttingSelectorPage = { query: string | null; limit: number; offset: number; total: number }
export type CuttingSelectorDraft = CuttingDraft & { model_id: string }
export type CuttingSelectorWorkspace = Omit<CuttingWorkspace, 'drafts'> & {
  contract_version: 2
  order_page: CuttingSelectorPage
  draft_page: CuttingSelectorPage
  drafts: CuttingSelectorDraft[]
  selected_order_id: string | null
  selected_order: CuttingWorkspace['orders'][number] | null
  selected_draft_id: string | null
  selected_draft: CuttingSelectorDraft | null
}

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Respons selector Potongan tidak valid.')
  return value as Record<string, unknown>
}
function nullableText(value: unknown): string | null {
  if (value === null) return null
  if (typeof value !== 'string' || value.length === 0) throw new Error('Identitas atau pencarian selector tidak valid.')
  return value
}
function integer(value: unknown, minimum = 0): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < minimum) throw new Error('Hitungan selector tidak valid.')
  return value
}
function page(value: unknown, length: number, maximum: number): CuttingSelectorPage {
  const raw = record(value)
  const result = { query: nullableText(raw.query), limit: integer(raw.limit, 1), offset: integer(raw.offset), total: integer(raw.total) }
  if (result.limit > maximum || (result.query?.length ?? 0) > 200
    || length !== Math.min(result.limit, Math.max(0, result.total - result.offset))) throw new Error('Halaman selector tidak lengkap.')
  return result
}
function unique(ids: string[]) {
  if (new Set(ids).size !== ids.length) throw new Error('Identitas selector berulang.')
}
function draft(value: unknown, parsed: CuttingDraft): CuttingSelectorDraft {
  const model = nullableText(record(value).model_id)
  if (!model) throw new Error('Model draft Potongan tidak lengkap.')
  return { ...parsed, model_id: model }
}

export function parseCuttingSelectorWorkspace(value: unknown): CuttingSelectorWorkspace {
  const raw = record(value)
  if (raw.contract_version !== 2) throw new Error('Versi workspace Potongan belum cocok. Muat ulang setelah pembaruan tersedia.')
  const base = parseCuttingWorkspace(raw)
  const draftRows = raw.drafts as unknown[]
  const drafts = base.drafts.map((row, i) => draft(draftRows[i], row))
  const selectedOrderId = nullableText(raw.selected_order_id)
  const selectedDraftId = nullableText(raw.selected_draft_id)
  // Reuse the legacy strict record parsers for the separate selected records.
  const selected = parseCuttingWorkspace({ ...raw,
    orders: raw.selected_order === null ? [] : [raw.selected_order],
    drafts: raw.selected_draft === null ? [] : [raw.selected_draft],
  })
  const selectedOrder = selected.orders[0] ?? null
  const selectedDraft = selected.drafts[0] ? draft(raw.selected_draft, selected.drafts[0]) : null
  if ((selectedOrder && selectedOrder.id !== selectedOrderId)
    || (selectedDraft && selectedDraft.cutting_group_id !== selectedDraftId)) throw new Error('Pilihan selector tidak cocok dengan permintaan.')
  unique(base.orders.map(row => row.id)); unique(drafts.map(row => row.cutting_group_id))
  const sameOrder = base.orders.find(row => row.id === selectedOrderId)
  const sameDraft = drafts.find(row => row.cutting_group_id === selectedDraftId)
  if ((sameOrder && JSON.stringify(sameOrder) !== JSON.stringify(selectedOrder))
    || (sameDraft && JSON.stringify(sameDraft) !== JSON.stringify(selectedDraft))) throw new Error('Snapshot pilihan berbeda dari halaman yang sama.')
  return { ...base, contract_version: 2, drafts,
    order_page: page(raw.order_page, base.orders.length, 200),
    draft_page: page(raw.draft_page, drafts.length, 100),
    selected_order_id: selectedOrderId, selected_order: selectedOrder,
    selected_draft_id: selectedDraftId, selected_draft: selectedDraft,
  }
}

export function cuttingOrder(workspace: CuttingSelectorWorkspace | null, id: string) {
  return workspace?.selected_order?.id === id ? workspace.selected_order : workspace?.orders.find(row => row.id === id)
}

export function cuttingSelectionIssue(workspace: CuttingSelectorWorkspace | null, orderId: string, draftId: string | null, version: number | null): string {
  if (orderId && !cuttingOrder(workspace, orderId)) return 'PO terpilih sudah tidak tersedia. Pilih PO yang masih aktif.'
  if (!draftId) return ''
  const current = workspace?.selected_draft?.cutting_group_id === draftId
    ? workspace.selected_draft : workspace?.drafts.find(row => row.cutting_group_id === draftId)
  if (!current || !current.editable) return 'Draft sudah berubah tahap atau tidak dapat diedit. Muat draft terbaru atau mulai Potongan baru.'
  if (current.row_version !== version || current.po_id !== orderId) return 'Draft berubah di sesi lain. Isianmu dipertahankan; muat draft terbaru sebelum menyimpan.'
  return ''
}

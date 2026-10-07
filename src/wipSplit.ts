// Splitting a Batch Distribusi into sub-batches (e.g. part of a sewn batch has
// fabric defects and goes to a different wash colour). Pure rules, shared by
// the WIP & Sewing page and its tests.
//
// Conservation: a split never creates or removes pieces. Per size, the source
// keeps `source − moved` and the new sub-batch receives `moved`; the sewn
// count is divided the same way, so the Batch Produksi total and the mandor's
// sewn total stay exactly the same.

export type WipSizes = [number, number, number]

export type WipSplitPiece = {
  id: string
  parentId: string
  /** The original Batch Distribusi this piece descends from. */
  rootId: string
  /** The batch the pieces were taken from (the root or another piece). */
  sourceId: string
  number: number
  suffix: string
  /** Sizes moved at split time (before any further split of this piece). */
  sizes: WipSizes
  /** Sewn pcs moved with the piece at split time. */
  completed: number
  note: string
  reason: string
  at: string
}

export type WipSplitBlock =
  | 'LAUNDRY_SENT'
  | 'LAUNDRY_RETURNED'
  | 'LAUNDRY_DRAFT'
  | 'FINAL_SKU'
  | 'TOO_SMALL'

export const WIP_SPLIT_BLOCK_LABEL: Record<WipSplitBlock, string> = {
  LAUNDRY_SENT: 'Sudah ada pcs di laundry; pecah batch hanya sebelum surat kirim dibuat.',
  LAUNDRY_RETURNED: 'Sudah ada hasil laundry kembali; pecah batch hanya sebelum dikirim.',
  LAUNDRY_DRAFT: 'Ada draft surat kirim laundry; hapus draft dulu sebelum memecah batch.',
  FINAL_SKU: 'Final SKU sudah lengkap untuk batch ini.',
  TOO_SMALL: 'Batch berisi kurang dari 2 pcs, tidak bisa dipecah.',
}

const SUFFIXES = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

export const sizeTotal = (sizes: readonly number[]) => sizes.reduce((sum, qty) => sum + qty, 0)
export const subtractSizes = (left: WipSizes, right: WipSizes): WipSizes => [left[0] - right[0], left[1] - right[1], left[2] - right[2]]
export const addSizes = (left: WipSizes, right: WipSizes): WipSizes => [left[0] + right[0], left[1] + right[1], left[2] + right[2]]
const zero: WipSizes = [0, 0, 0]

/** Suffix for the next piece of a root batch: the root is "A", pieces take B, C, … in order. */
export function nextSplitSuffix(rootId: string, pieces: readonly WipSplitPiece[]): string {
  const used = new Set(pieces.filter((piece) => piece.rootId === rootId).map((piece) => piece.suffix))
  for (const letter of SUFFIXES.slice(1)) if (!used.has(letter)) return letter
  throw new Error('WIP_SPLIT_SUFFIX_EXHAUSTED')
}

export const splitPieceId = (rootId: string, suffix: string) => `${rootId}${suffix}`

export function batchLabel(number: number, suffix?: string) {
  return `${String(number).padStart(2, '0')}${suffix ?? ''}`
}

/** Why a batch cannot be split right now, or null when it can. */
export function wipSplitBlock(facts: { qty: number; laundryOutside: number; laundryReturned: number; laundryDraft: boolean; finalSkuComplete: boolean }): WipSplitBlock | null {
  if (facts.finalSkuComplete) return 'FINAL_SKU'
  if (facts.laundryReturned > 0) return 'LAUNDRY_RETURNED'
  if (facts.laundryOutside > 0) return 'LAUNDRY_SENT'
  if (facts.laundryDraft) return 'LAUNDRY_DRAFT'
  if (facts.qty < 2) return 'TOO_SMALL'
  return null
}

/** Sewn pcs that may move with the new piece: both sides keep sewn ≤ their own qty. */
export function splitCompletedBounds(sourceQty: number, sourceCompleted: number, movedQty: number) {
  const remainingQty = sourceQty - movedQty
  const min = Math.max(0, sourceCompleted - remainingQty)
  const max = Math.min(movedQty, sourceCompleted)
  return { min, max }
}

export type WipSplitDraft = {
  sourceSizes: WipSizes
  sourceCompleted: number
  moveSizes: WipSizes
  completedMoved: number
  newNote: string
  sourceNote: string
  reason: string
}

export type WipSplitIssue =
  | 'NOTHING_MOVED'
  | 'SIZE_OVER_SOURCE'
  | 'SOURCE_EMPTY'
  | 'COMPLETED_OUT_OF_RANGE'
  | 'NEW_NOTE_REQUIRED'
  | 'SOURCE_NOTE_REQUIRED'
  | 'REASON_REQUIRED'

export const WIP_SPLIT_ISSUE_LABEL: Record<WipSplitIssue, string> = {
  NOTHING_MOVED: 'Isi jumlah pcs yang dipindah ke batch baru.',
  SIZE_OVER_SOURCE: 'Jumlah pindah per size tidak boleh melebihi isi batch asal.',
  SOURCE_EMPTY: 'Batch asal tidak boleh kosong; pindahkan sebagian saja.',
  COMPLETED_OUT_OF_RANGE: 'Pcs selesai dijahit yang ikut pindah di luar batas.',
  NEW_NOTE_REQUIRED: 'Isi arahan untuk batch baru (mis. warna cucian).',
  SOURCE_NOTE_REQUIRED: 'Arahan batch asal tidak boleh kosong.',
  REASON_REQUIRED: 'Isi catatan singkat alasan pecah batch (min. 4 huruf).',
}

export function validateWipSplit(draft: WipSplitDraft): WipSplitIssue[] {
  const issues: WipSplitIssue[] = []
  const moved = sizeTotal(draft.moveSizes)
  if (draft.moveSizes.some((qty) => !Number.isInteger(qty) || qty < 0)) issues.push('SIZE_OVER_SOURCE')
  else if (draft.moveSizes.some((qty, index) => qty > draft.sourceSizes[index])) issues.push('SIZE_OVER_SOURCE')
  if (moved === 0) issues.push('NOTHING_MOVED')
  else if (moved >= sizeTotal(draft.sourceSizes)) issues.push('SOURCE_EMPTY')
  const bounds = splitCompletedBounds(sizeTotal(draft.sourceSizes), draft.sourceCompleted, moved)
  if (!Number.isInteger(draft.completedMoved) || draft.completedMoved < bounds.min || draft.completedMoved > bounds.max) issues.push('COMPLETED_OUT_OF_RANGE')
  if (!draft.newNote.trim()) issues.push('NEW_NOTE_REQUIRED')
  if (!draft.sourceNote.trim()) issues.push('SOURCE_NOTE_REQUIRED')
  if (draft.reason.trim().length < 4) issues.push('REASON_REQUIRED')
  return [...new Set(issues)]
}

export type WipBatchBase = { id: string; number: number; sizes: WipSizes; note: string }

export type WipBatchView = WipBatchBase & {
  rootId: string
  suffix?: string
  sourceId?: string
  isPiece: boolean
  hasPieces: boolean
}

/**
 * Batches of one Batch Produksi with their pieces, each piece listed right after
 * the batch it came from. A batch's sizes are its own (or `overrides[id]` when
 * corrected in this session) minus everything split off it.
 */
export function batchesWithSplits(parentId: string, seeds: readonly WipBatchBase[], pieces: readonly WipSplitPiece[], overrides: Readonly<Record<string, WipSizes>> = {}): WipBatchView[] {
  const own = pieces.filter((piece) => piece.parentId === parentId)
  const childrenOf = (id: string) => own.filter((piece) => piece.sourceId === id)
  const result: WipBatchView[] = []
  const visit = (base: WipBatchBase, rootId: string, piece: WipSplitPiece | null) => {
    const children = childrenOf(base.id)
    const sizes = overrides[base.id] ?? subtractSizes(base.sizes, children.reduce((sum, child) => addSizes(sum, child.sizes), zero))
    const rootHasPieces = own.some((item) => item.rootId === rootId)
    result.push({
      ...base,
      sizes,
      rootId,
      suffix: piece ? piece.suffix : rootHasPieces ? 'A' : undefined,
      sourceId: piece?.sourceId,
      isPiece: piece !== null,
      hasPieces: children.length > 0,
    })
    for (const child of children) visit({ id: child.id, number: child.number, sizes: child.sizes, note: child.note }, rootId, child)
  }
  for (const seed of seeds) visit(seed, seed.id, null)
  return result
}

/** Sewn count a batch starts with in a fresh view: its own minus what moved to its pieces. */
export function initialCompleted(id: string, seedCompleted: number, pieces: readonly WipSplitPiece[]) {
  return seedCompleted - pieces.filter((piece) => piece.sourceId === id).reduce((sum, piece) => sum + piece.completed, 0)
}

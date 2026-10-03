import type { PickupQueue, PickupQueueRow } from './cuttingPersistence'
import type { TransactionDocument } from './transactionSource'

/** The current Native ALL page must contain this exact posted group and PO. */
export function cuttingSourceRow(queue: PickupQueue, document: TransactionDocument): PickupQueueRow {
  const focus = document.focus
  const fail = (): never => { throw Error('Potongan asal berubah atau belum tersedia pada halaman ini. Buka kembali transaksi asal untuk memeriksa sumber terbaru.') }
  if (document.domain !== 'CUTTING' || document.route !== 'mandor-wip' || focus?.kind !== 'CUTTING_GROUP'
    || focus.id !== document.id || queue.filter !== 'ALL' || queue.pattern_id !== null || queue.query !== null
    || queue.limit !== 100 || queue.offset !== focus.page_offset) return fail()
  const row = queue.rows.find(candidate => candidate.cutting_group_id === document.id)
  if (!row || row.po_id !== focus.parent_id || row.group_number !== document.number || row.status !== document.status
    || !Number.isSafeInteger(row.row_version) || String(row.row_version) !== document.revision) return fail()
  return row
}

import { laundryClaimSizes, laundryOutstandingSizes, laundryPhysicalTime, laundryQcSizes, type LaundryDelivery } from '../laundryModel'
import { sizeTotals, total, type Batch, type Source } from './distribution'
import type { Lot } from './model'

type StageRow = { id: string; stage: 'sewing' | 'laundry' | 'qc'; place: string; sizes: Record<string, number>; hold?: boolean; closed?:boolean }
type Projection = (lot: Lot, sources: Source[]) => Lot

export function stageBatch(
  lot: Lot, batch: Batch, id: string, deliveries: LaundryDelivery[], project: Projection,
): Lot[] | null {
  const sourced = total(batch.sources) === batch.qty
  const available = sourced ? sizeTotals(batch.sources) : batch.sizes
  if (Object.values(available).reduce((sum, qty) => sum + qty, 0) !== batch.qty) return null

  const remaining = { ...available }
  const rows: StageRow[] = []
  const ordered = [...deliveries].sort((a, b) => laundryPhysicalTime(a.sentAt).localeCompare(laundryPhysicalTime(b.sentAt)) || a.id.localeCompare(b.id))
  for (const delivery of ordered) {
    const pending = laundryOutstandingSizes(delivery)
    const append = (row: Omit<StageRow, 'sizes'>, amounts: number[]) => {
      const sizes: Record<string, number> = {}
      delivery.sizeLabels.forEach((size, i) => { if (amounts[i] > 0) sizes[size] = amounts[i] })
      for (const [size, qty] of Object.entries(sizes)) remaining[size] = (remaining[size] ?? 0) - qty
      if (Object.keys(sizes).length) rows.push({ ...row, sizes })
    }
    append({ id: delivery.id, stage: 'laundry', place: delivery.vendor }, pending)
    append({ id: delivery.id + '-QC', stage: 'qc', place: 'Meja QC' }, laundryQcSizes(delivery))
    append({ id: delivery.id + '-BS', stage: 'qc', place: 'Pemeriksaan BS', hold: true }, delivery.bsSizes)
    append({ id: delivery.id + '-KLAIM', stage: 'laundry', place: delivery.vendor, closed:true }, laundryClaimSizes(delivery,'CREDIT'))
  }
  if (Object.values(remaining).some(qty => qty < 0)) return null
  rows.push({ id, stage: 'sewing', place: batch.mandor, sizes: remaining })

  // A shipment records its sizes. A partial transfer cannot identify which material
  // moved if multiple fabrics contributed to that size.
  const hasMaterialAmbiguity = Object.keys(available).some(size => {
    if (rows.filter(row => row.sizes[size] > 0).length < 2) return false
    const rollIds = new Set(batch.sources.filter(source => source.size === size).map(source => source.rollId))
    return new Set(lot.outputs?.filter(roll => rollIds.has(roll.id)).map(roll => roll.material)).size > 1
  })
  const pool = batch.sources.map(source => ({ ...source }))
  return rows.flatMap(({ id, stage, place, sizes, hold, closed }) => {
    const base = { ...lot, id, stage, place, originId: lot.id, kind: hold ? 'quality-hold' : lot.kind }
    if (!sourced || hasMaterialAmbiguity) {
      return closed?[]:Object.entries(sizes).filter(([, qty]) => qty > 0).map(([size, qty]) => ({
        ...base, id: id + '-' + size, size, qty, outputs: undefined, roll: undefined,
        ...(hasMaterialAmbiguity ? { material: 'Bahan campuran', eta: null } : {}),
      }))
    }
    const left = { ...sizes }
    const sources: Source[] = []
    for (const row of pool) {
      const take = Math.min(row.qty, left[row.size] ?? 0)
      if (!take) continue
      sources.push({ ...row, qty: take })
      row.qty -= take
      left[row.size] -= take
    }
    if(!sources.length)return []
    const projected=project(base,sources)
    return closed?[]:[projected]
  })
}

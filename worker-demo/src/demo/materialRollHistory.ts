import { browseText } from '../browseMatch'
import { correctionRolls, cutDay, cutRolls, emptySession, originalCutLots, physicalRollId, type Session } from './planner/model'
import { pocketRollLabel, seedRolls, type PocketReceipt, type PocketUnit } from './pocketReceipts'
import { pocketScale, type PocketBook } from './pocketUsage'
import { cutDocumentPath, pocketIssuePath, receiptDocumentPath, type ReceiptReversal, type ReceiptRoll, type RollReceiptCorrection, type StockSourceLink } from './receiptRollCorrection'

export type RollMovement = {
  id: string
  at: string
  title: string
  delta: number
  ref: string
  note?: string
  source?: StockSourceLink
}

export type WarehouseRoll = {
  id: string
  label: string
  material: string
  materialKey: string
  supplier: string
  location: string
  unit: PocketUnit
  rate?: number
  events: RollMovement[]
  voided?: boolean
}

export const fabricKey = (name: string) => {
  const key = browseText(name).replace(/\s+/g, ' ')
  return key === 'denim 1069 ori' ? '1069 ori' : key
}
export const materialHistoryPath = (name: string, pocket = false) => (pocket ? '/gudang/kain-kantong/' : '/gudang/bahan-roll/')
  + '?' + new URLSearchParams({ bahan: name }) + '#riwayat-bahan'
const roundLength = (value: number) => Math.round(value * pocketScale) / pocketScale
export const rollBalance = (roll: WarehouseRoll) => roundLength(roll.events.reduce((total, event) => total + event.delta, 0))
export const rollLength = (qty: number, unit: PocketUnit) => qty.toLocaleString('id-ID', { maximumFractionDigits: 6 }) + ' ' + unit
export function stockLengths(rolls: WarehouseRoll[]) {
  const lengths = new Map<PocketUnit, number>()
  for (const roll of rolls) lengths.set(roll.unit, (lengths.get(roll.unit) ?? 0) + Math.round(rollBalance(roll) * pocketScale))
  return [...lengths].map(([unit, qty]) => rollLength(qty / pocketScale, unit)).join(' · ') || '—'
}

type RollDocument = {
  number: string; day: string; corrections?: RollReceiptCorrection[]; reversal?: ReceiptReversal
}
function receiptHistory(roll: ReceiptRoll, document: RollDocument, pocket = false) {
  const source = { label: 'Buka penerimaan', href: receiptDocumentPath(document.number, pocket ? 'kantong' : 'kain') }
  const base = { ref: document.number, source }
  const events: RollMovement[] = [{ ...base, id: 'receipt', at: document.day, title: 'Penerimaan', delta: roll.length }]
  let label = roll.physicalCode
  let length = roll.length
  for (const correction of document.corrections ?? []) {
    if (correction.roll !== roll.id) continue
    const before = correction.beforeCode ?? roll.id
    const after = correction.physicalCode ?? roll.id
    const note = [before !== after ? before + ' → ' + after : '', correction.reason].filter(Boolean).join(' · ')
    events.push({ ...base, id: correction.id, at: correction.at, title: 'Koreksi penerimaan', delta: roundLength(correction.length - length), note })
    label = correction.physicalCode
    length = correction.length
  }
  if (document.reversal) events.push({ ...base, id: 'receipt-reversal', at: document.reversal.at,
    title: 'Pembalikan penerimaan', delta: -length, note: document.reversal.reason })
  return { events, label: label ?? roll.id, voided: !!document.reversal }
}

export function operationalFabricRolls(session: Session): WarehouseRoll[] {
  const rows: WarehouseRoll[] = correctionRolls(emptySession).map(roll => ({
    id: roll.id, label: roll.id, material: roll.material, materialKey: fabricKey(roll.material),
    supplier: roll.supplier, location: 'Gudang Kain', unit: 'yd', rate: roll.rate,
    events: [{ id: 'opening', at: roll.day, title: roll.source.startsWith('SJ-') ? 'Penerimaan arsip' : 'Saldo awal',
      ref: roll.source, delta: roll.yards,
      source: roll.source === 'SJ-SNR-0821-07' ? { label: 'Buka penerimaan', href: '/gudang/pembelian-penerimaan/?jenis=kain#penerimaan-arsip-1069' } : undefined }],
  }))
  for (const doc of session.fabricReceipts ?? []) {
    for (const roll of doc.rolls) rows.push({ id: roll.id, material: doc.material, materialKey: fabricKey(doc.material),
      supplier: doc.supplier, location: 'Gudang Kain', unit: doc.unit, rate: doc.rate, ...receiptHistory(roll, doc) })
  }
  const byId = new Map(rows.map(roll => [roll.id, roll]))
  for (const lot of originalCutLots({ ...session, cutReversals: undefined })) {
    const source = { label: 'Buka Potongan', href: cutDocumentPath(lot.id) }
    for (const roll of cutRolls(lot)) {
      if (roll.usedYards <= 0) continue
      byId.get(roll.id)?.events.push({ id: 'cut:' + lot.id, ref: lot.id, at: cutDay(lot), title: 'Pemakaian Potongan', delta: -roll.usedYards, source })
      const reversal = session.cutReversals?.[lot.id]
      if (reversal) byId.get(physicalRollId(lot.id, roll.id, session))?.events.push({
        id: 'reverse:' + lot.id + ':' + roll.id, ref: lot.id, at: reversal.at, title: 'Pembalikan Potongan', delta: roll.usedYards, note: reversal.reason, source,
      })
    }
  }
  for (const event of session.rollCorrections ?? []) {
    const source = { label: 'Buka Ganti roll', href: '/gudang/bahan-roll/?' + new URLSearchParams({ switch: event.id }) + '#riwayat-ganti-roll' }
    const base = { id: 'switch:' + event.id, ref: event.cut, at: event.at, source }
    byId.get(event.from)?.events.push({ ...base, delta: event.yards, title: 'Ganti roll · saldo kembali',
      note: 'Pemakaian dipindah ke ' + (byId.get(event.to)?.label ?? event.to) + ' · ' + event.reason })
    byId.get(event.to)?.events.push({ ...base, delta: -event.yards, title: 'Ganti roll · terpakai',
      note: 'Pemakaian dari ' + (byId.get(event.from)?.label ?? event.from) + ' · ' + event.reason })
  }
  return rows
}

export function pocketHistoryRolls(receipts: PocketReceipt[], book: PocketBook): WarehouseRoll[] {
  const rows: WarehouseRoll[] = seedRolls.map(roll => ({
    id: roll.id, label: pocketRollLabel(roll), material: roll.name, materialKey: roll.materialId ?? roll.name,
    supplier: roll.supplier ?? '', location: roll.location, unit: roll.unit, events: [{
      id: 'opening', at: roll.date, title: 'Saldo awal', delta: roll.length, ref: roll.receipt,
      source: { label: 'Buka penerimaan', href: receiptDocumentPath(roll.receipt, 'kantong') },
    }],
  }))
  for (const doc of receipts) for (const roll of doc.rolls) {
    const history = receiptHistory(roll, doc, true)
    rows.push({ ...history, id: roll.id, label: pocketRollLabel({ ...roll, physicalCode: history.label === roll.id ? undefined : history.label }),
      material: roll.name, materialKey: roll.materialId ?? roll.name, supplier: doc.supplier, location: roll.location, unit: roll.unit })
  }
  const byId = new Map(rows.map(roll => [roll.id, roll]))
  for (const issue of book.issues) {
    const roll = byId.get(issue.roll)
    if (!roll) continue
    const source = { label: 'Buka pemakaian', href: pocketIssuePath(issue.id) }
    const qty = issue.qty / pocketScale
    roll.events.push({ id: issue.id, title: 'Pemakaian kain kantong', at: issue.date, delta: -qty, ref: issue.id, note: issue.reason, source })
    if (issue.reversal) roll.events.push({ id: 'reverse:' + issue.id, title: 'Pembalikan pemakaian', at: issue.reversedAt ?? '',
      delta: qty, ref: issue.id, note: issue.reversal, source })
  }
  return rows
}

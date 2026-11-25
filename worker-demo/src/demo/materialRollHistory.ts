import {archiveDocumentFor, archiveIdentity, archiveSource, openingCorrectionRolls, receiptMaterial} from './fabricArchive'
import { browseText } from '../browseMatch'
import { cutDay, cutRolls, originalCutLots, physicalRollId, type Session } from './planner/model'
import { pocketRollLabel, seedRolls, type PocketReceipt, type PocketUnit } from './pocketReceipts'
import { pocketScale, type PocketBook } from './pocketUsage'
import { cutDocumentPath, pocketIssuePath, receiptDocumentPath, type ReceiptReversal, type ReceiptRoll, type RollReceiptCorrection, type StockSourceLink } from './receiptRollCorrection'

export type RollMovement = {
  id: string
  at: string
  title: string
  delta: number
  flow: 'received' | 'used' | 'returned'
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
export type RollAmounts = { received: number; used: number; returned: number; balance: number }
export function rollTotalsByUnit(rolls: WarehouseRoll[]): Map<PocketUnit, RollAmounts> {
  const units = new Map<PocketUnit, RollAmounts>()
  for (const roll of rolls) {
    const amounts = units.get(roll.unit) ?? { received: 0, used: 0, returned: 0, balance: 0 }
    for (const event of roll.events) {
      const delta = Math.round(event.delta * pocketScale)
      amounts[event.flow] += event.flow === 'received' ? delta : -delta
      amounts.balance += delta
    }
    units.set(roll.unit, amounts)
  }
  for (const [unit, row] of units) units.set(unit, {
    received: row.received / pocketScale, used: row.used / pocketScale,
    returned: row.returned / pocketScale, balance: row.balance / pocketScale,
  })
  return units
}

export function formatRollTotal(totals: Map<PocketUnit, RollAmounts>, field: keyof RollAmounts) {
  return [...totals].map(([unit, row]) => rollLength(row[field], unit)).join(' · ') || '—'
}

export const stockLengths = (rolls: WarehouseRoll[]) => formatRollTotal(rollTotalsByUnit(rolls), 'balance')

type RollDocument = {
  number: string; day: string; corrections?: RollReceiptCorrection[]; reversal?: ReceiptReversal
}
function receiptHistory(roll: ReceiptRoll, document: RollDocument, pocket = false) {
  const source = { label: 'Buka penerimaan', href: receiptDocumentPath(document.number, pocket ? 'kantong' : 'kain',pocket?undefined:roll.id) }
  const base = { ref: document.number, source, flow: 'received' as const }
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

export function identityMovements(session:Session,key:string,rollId:string,source:StockSourceLink,ref:string):RollMovement[] {
  return (session.fabricIdentities??[]).filter(event=>event.source===key&&(!event.roll||event.roll===rollId)).map(event=>({
    id:event.id,flow:'received',at:event.at,ref,source,delta:0,title:event.roll?'Koreksi nomor roll':'Koreksi nama bahan',
    note:event.before+' → '+event.after+' · '+event.reason,
  }))
}
export function operationalFabricRolls(session: Session): WarehouseRoll[] {
  const rows: WarehouseRoll[] = openingCorrectionRolls.map(roll => {
    const {material,physicalCode}=archiveIdentity(session,roll.id)
    const source=archiveSource(roll.id)
    return {id:roll.id,label:physicalCode??roll.id,material,materialKey:fabricKey(material),
      supplier:roll.supplier,location:'Gudang Kain',unit:'yd',rate:roll.rate,
      events:[{id:'opening',flow:'received',at:roll.day,title:roll.source.startsWith('SJ-')?'Penerimaan arsip':'Saldo awal',
        ref:roll.source,delta:roll.yards,source},
        ...identityMovements(session,archiveDocumentFor(roll.id)!.key,roll.id,source,roll.source)],
    }
  })
  for (const doc of session.fabricReceipts ?? []) {
    const material=receiptMaterial(session,doc)
    for (const roll of doc.rolls) {
      const history=receiptHistory(roll,doc)
      history.events.push(...identityMovements(session,'penerimaan:'+doc.id,roll.id,history.events[0].source!,doc.number))
      rows.push({id:roll.id,material,materialKey:fabricKey(material),supplier:doc.supplier,location:'Gudang Kain',unit:doc.unit,rate:doc.rate,...history})
    }
  }
  const byId = new Map(rows.map(roll => [roll.id, roll]))
  for (const lot of originalCutLots({ ...session, cutReversals: undefined })) {
    const source = { label: 'Buka Potongan', href: cutDocumentPath(lot.id) }
    for (const roll of cutRolls(lot)) {
      if (roll.usedYards <= 0) continue
      byId.get(roll.id)?.events.push({ id: 'cut:' + lot.id, flow: 'used', ref: lot.id, at: cutDay(lot), title: 'Pemakaian Potongan', delta: -roll.usedYards, source })
      const reversal = session.cutReversals?.[lot.id]
      if (reversal) byId.get(physicalRollId(lot.id, roll.id, session))?.events.push({
        id: 'reverse:' + lot.id + ':' + roll.id, flow: 'used', ref: lot.id, at: reversal.at, title: 'Pembalikan Potongan', delta: roll.usedYards, note: reversal.reason, source,
      })
    }
  }
  for (const event of session.rollCorrections ?? []) {
    const source = { label: 'Buka Ganti roll', href: '/gudang/bahan-roll/?' + new URLSearchParams({ switch: event.id }) + '#riwayat-ganti-roll' }
    const base = { id: 'switch:' + event.id, flow: 'used' as const, ref: event.cut, at: event.at, source }
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
      id: 'opening', flow: 'received', at: roll.date, title: 'Saldo awal', delta: roll.length, ref: roll.receipt,
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
    roll.events.push({ id: issue.id, flow: 'used', title: 'Pemakaian kain kantong', at: issue.date, delta: -qty, ref: issue.id, note: issue.reason, source })
    if (issue.reversal) roll.events.push({ id: 'reverse:' + issue.id, flow: 'used', title: 'Pembalikan pemakaian', at: issue.reversedAt ?? '',
      delta: qty, ref: issue.id, note: issue.reversal, source })
  }
  return rows
}

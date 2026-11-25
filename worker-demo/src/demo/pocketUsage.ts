import type { PocketRoll, PocketUnit } from './pocketReceipts'
import { dayOk } from './warehouseDay'

export const pocketScale = 1_000_000
export const pocketBookKey = 'erp.demo.pocket.period.v1'

export type PocketIssue = {
  id: string
  roll: string
  date: string
  qty: number
  cents: number
  reason: string
  unit?: PocketUnit
  reversal?: string
}
type AllocationPart = { po: string; mandor: string; pcs: number; wip: number; fg: number; sold: number }
export type PocketAllocation = {
  start: string; end: string; cents: number; pcs: number; parts: AllocationPart[]; sources: string[]
}
type PostedAllocation = PocketAllocation & { id: string; reason: string; reversal?: string }
export type PocketBook = { issues: PocketIssue[]; allocations: PostedAllocation[] }
export type UsageLine = { roll: PocketRoll; qty: number; left: number; cents: number }

const sewn = [
  { po: 'PO-1069', mandor: 'Epi', day: '2026-11-23', wip: 12, fg: 18, sold: 6 },
  { po: 'PO-LUCY', mandor: 'Afui', day: '2026-11-24', wip: 8, fg: 10, sold: 6 },
]

export function readPocketBook(): PocketBook {
  return JSON.parse(sessionStorage.getItem(pocketBookKey) ?? '{"issues":[],"allocations":[]}')
}

export function pocketBalance(book: PocketBook, roll: PocketRoll, through?: string) {
  const issued = book.issues
    .filter(i => i.roll === roll.id && !i.reversal && (!through || i.date <= through))
    .reduce((sum, i) => sum + i.qty, 0)
  return Math.round(roll.length * pocketScale) - issued
}

export function periodActive(book: PocketBook, start: string, end: string) {
  return book.allocations.some(a => !a.reversal && a.start <= end && a.end >= start)
}

export function readPocketNumber(value: string) {
  const text = value.trim()
  return /^\d+(?:[.,]\d{1,6})?$/.test(text) ? Number(text.replace(',', '.')) : NaN
}

export function planPocketUsage(
  book: PocketBook,
  rolls: PocketRoll[],
  date: string,
  reason: string,
  mode: 'keluar' | 'sisa' | 'utuh',
  amount: string,
): UsageLine[] {
  if (!rolls.length) throw Error('Pilih roll yang akan dipakai.')
  if (!dayOk(date)) throw Error('Isi tanggal pemakaian yang sah.')
  if (!reason.trim()) throw Error('Isi alasan pemakaian.')
  if (periodActive(book, date, date)) throw Error('Batalkan pembagian biaya periode ini sebelum mencatat pemakaian.')
  const physical = Math.round(readPocketNumber(amount) * pocketScale)

  return rolls.map(roll => {
    if (date < roll.date) throw Error(roll.id + ' belum diterima pada tanggal ini.')
    const current = pocketBalance(book, roll)
    const atDate = pocketBalance(book, roll, date)
    if (mode === 'utuh' && atDate !== current) throw Error(roll.id + ' sudah punya pemakaian setelah tanggal ini.')
    const qty = mode === 'utuh' ? current : mode === 'sisa' ? atDate - physical : physical
    if (!Number.isSafeInteger(qty) || qty <= 0 || qty > Math.min(atDate, current)) {
      throw Error('Jumlah keluar untuk ' + roll.id + ' harus antara nol dan sisa roll, dengan nilai lebih dari nol.')
    }
    const cents = Math.round(qty * roll.rate * 100 / pocketScale)
    return { roll, qty, left: current - qty, cents }
  })
}

export function pocketIssueCost(issue: PocketIssue, roll: PocketRoll | undefined) {
  return roll?.finalBill ? Math.round(issue.qty / pocketScale * roll.rate * 100) : issue.cents
}

export function planPocketAllocation(book: PocketBook, start: string, end: string, rolls: PocketRoll[] = []): PocketAllocation {
  if (!dayOk(start) || !dayOk(end) || start > end || (Date.parse(end) - Date.parse(start)) / 86400000 > 366) {
    throw Error('Pilih periode sampai hari ini, maksimal 367 hari.')
  }
  if (periodActive(book, start, end)) throw Error('Periode ini bertumpang tindih dengan pembagian biaya aktif.')
  const docs = book.issues.filter(i => !i.reversal && start <= i.date && i.date <= end)
  const jobs = sewn.filter(j => start <= j.day && j.day <= end)
  const pcs = jobs.reduce((sum, j) => sum + j.wip + j.fg + j.sold, 0)
  const byId = new Map(rolls.map(roll => [roll.id, roll]))
  const cents = docs.reduce((sum, issue) => sum + pocketIssueCost(issue, byId.get(issue.roll)), 0)
  if (!cents) throw Error('Belum ada biaya kain keluar pada periode ini.')
  if (!pcs) throw Error('Belum ada hasil selesai dijahit pada periode ini.')
  let done = 0
  function share(qty: number) {
    const before = Math.round(cents * done / pcs)
    done += qty
    return Math.round(cents * done / pcs) - before
  }
  const parts = jobs.map(j => ({
    po: j.po, mandor: j.mandor, pcs: j.wip + j.fg + j.sold,
    wip: share(j.wip), fg: share(j.fg), sold: share(j.sold),
  }))
  return { start, end, cents, pcs, parts, sources: docs.map(i => i.id) }
}

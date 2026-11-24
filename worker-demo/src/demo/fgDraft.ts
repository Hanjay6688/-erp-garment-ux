import type { QcFinalResult } from '../QcFinalPage'
import { regularFgNotaCardId, type ReadyFgNotaCard, type RegularFgNotaSnapshot } from '../fgNota'
import { postedPayrollCards } from './payrollSources'

export type FgDraft = {
  number: string
  mandor: string
  note: string
  results: QcFinalResult[]
  repairs: ReadyFgNotaCard[]
  snapshots: Record<string, RegularFgNotaSnapshot>
  version: number
  closed?: 'VOID' | 'POSTED'
  reason?: string
}
const key = 'erp.owner.fg-drafts.1'
const cards = (d: FgDraft) => [...d.results.map(regularFgNotaCardId), ...d.repairs.map(c => c.id)]
const history = (): FgDraft[] => JSON.parse(sessionStorage.getItem(key) ?? '[]')
export const fgDrafts = () => history().filter(d => !d.closed)
export const claimedFgCards = (except?: string) => fgDrafts().filter(d => d.number !== except).flatMap(cards)
export function storeFgDraft(draft: FgDraft): FgDraft {
  const all = history()
  const old = all.find(d => d.number === draft.number)
  if (old?.closed || (old?.version ?? 0) !== draft.version) throw Error('Draft sudah berubah. Buka lagi dari daftar draft.')
  const ids = cards(draft)
  const unavailable = new Set([...claimedFgCards(draft.number), ...postedPayrollCards()])
  if (!ids.length || ids.length > 50 || ids.some(id => unavailable.has(id))) throw Error('Pilih 1–50 kartu yang belum masuk nota lain.')
  const next = {...draft, version: draft.version + 1}
  sessionStorage.setItem(key, JSON.stringify([...all.filter(d => d.number !== next.number), next]))
  return next
}
export function closeFgDraft(number: string, version: number, closed: 'VOID' | 'POSTED', reason: string) {
  const all = history(), old = all.find(d => d.number === number)
  if (old?.closed || old?.version !== version) throw Error('Versi draft berubah. Buka ulang dokumen.')
  if (reason.trim().length < 5 || reason.trim().length > 1000) throw Error('Isi alasan tindakan sepanjang 5–1.000 karakter.')
  sessionStorage.setItem(key, JSON.stringify(all.map(d => d.number === number ? {...d, closed, reason: reason.trim(), version: version + 1} : d)))
}

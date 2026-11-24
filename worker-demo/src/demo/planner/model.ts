import sample from './sample.json'
import projection from './projection.json'

export const { products, patterns, rolls } = sample
export type Product = typeof products[number]
export type Lot = {
  id: string; sku: string; stage: string; kind: string; qty: number; size: string
  pattern: string; material: string; eta: string; place: string; roll?: string; usedYards?: number; sourceYards?: number; remainingYards?: number; group?: string; requestId?: string
}
export type Pickup = { id: string; mandor: string; at: string; batches: {qty: number; note: string}[] }
export type Session = { cuts: Lot[]; pickups: Pickup[]; confirmed: string[] }
export const emptySession: Session = { cuts: [], pickups: [], confirmed: [] }
export const stageName: Record<string, string> = { cut: 'Meja potong', sewing: 'Jahit', laundry: 'Laundry', qc: 'QC' }
export const productFor = (sku: string) => products.find(p => p.sku === sku)
export function patternFor(code: string) { return patterns.find(p => p.code === code)! }
export function day(date: string) {
  return new Intl.DateTimeFormat('id-ID', {weekday: 'short', day: 'numeric', month: 'short', timeZone: 'Asia/Jakarta'}).format(new Date(date + 'T05:00:00Z')).replace(',', '')
}
export function lotsIn(session: Session): Lot[] {
  return [...sample.lots, ...session.cuts].map(lot => {
    const pickup = session.pickups.find(p => p.id === lot.id)
    if (pickup) return {...lot, stage: 'sewing', kind: 'directed', place: pickup.mandor}
    return session.confirmed.includes(lot.id) ? {...lot, kind:'directed'} : lot
  })
}
export function plan(product: Product, session: Session) {
  const initial = projection[product.sku as keyof typeof projection]
  const lots = lotsIn(session).filter(lot => lot.sku === product.sku)
  const newOnTime = session.cuts.filter(lot => lot.sku === product.sku && lot.eta <= product.due).reduce((sum, lot) => sum + lot.qty, 0)
  const picked = lots.filter(lot => lot.eta <= product.due && (session.pickups.some(p => p.id === lot.id) || session.confirmed.includes(lot.id))).reduce((sum, lot) => sum + lot.qty, 0)
  const confirmed = initial.directed + picked
  const potential = initial.candidate + newOnTime - picked
  const base = Math.max(0, initial.base - picked)
  const short = Math.max(0, initial.conditional - newOnTime)
  const queue = lots.filter(lot => lot.stage === 'cut' && lot.eta <= product.due)
  const check = lots.find(lot => lot.kind === 'candidate' && lot.stage !== 'cut' && lot.eta <= product.due)
  const late = lots.filter(lot => lot.eta > product.due).reduce((sum, lot) => sum + lot.qty, 0)
  return {product, lots, queue, check, confirmed, potential, base, short, late}
}
export type Plan = ReturnType<typeof plan>
export const plansIn = (session: Session) => products.map(p => plan(p, session))
export function action(row: Plan) {
  if (row.short) return 'Potong ' + row.short + ' pcs'
  if (row.queue.length) return 'Bagikan ' + row.queue.reduce((sum, lot) => sum + lot.qty, 0) + ' pcs'
  if (row.check) return 'Cek tujuan ' + row.check.qty + ' pcs'
  return 'Tunggu hasil produksi'
}
export function waitingLots(session: Session) {
  return plansIn(session).flatMap(row => row.queue).sort((a,b) => productFor(a.sku)!.due.localeCompare(productFor(b.sku)!.due) || a.id.localeCompare(b.id))
}
export function yardsLeft(id: string, session: Session) {
  return (rolls.find(r => r.id === id)?.yards ?? 0) - session.cuts.filter(l => l.roll === id).reduce((sum, l) => sum + (l.usedYards ?? 0), 0)
}
export function confirmDestination(session: Session, id:string): Session {
  const lot=lotsIn(session).find(l=>l.id===id && l.stage==='sewing' && l.kind==='candidate')
  if(!lot) throw Error('Tujuan jahitan ini sudah pasti.')
  return {...session,confirmed:[...session.confirmed,id]}
}
export function suggestedCut(row: Plan, session: Session) {
  const options=row.product.routes.flatMap(route=>rolls.filter(r=>r.material===route.material).map(roll=>{
    const available=yardsLeft(roll.id,session)
    return {route,roll,available,qty:Math.min(row.short,Math.floor(available/roll.yardPerPiece))}
  }))
  return options.sort((a,b)=>b.qty-a.qty)[0]
}
type CutInput = { requestId: string; sku: string; patternId: string; size: string; roll: string; qty: number; yards: number; date: string }
export function recordCut(session: Session, input: CutInput): Session {
  if (session.cuts.some(l=>l.requestId===input.requestId)) return session
  const product = productFor(input.sku)
  const roll = rolls.find(r => r.id === input.roll)
  const pattern = patterns.find(p => p.id === input.patternId)
  if (!product || !roll || !pattern || !product.routes.some(route => route.pattern === pattern.code && route.material === roll.material)) throw Error('Pilih pasangan pola dan bahan yang tercantum untuk SKU ini.')
  if (input.size !== product.size) throw Error('Pesanan ini membutuhkan ukuran ' + product.size + '.')
  if (input.date !== sample.date) throw Error('Latihan ini memakai tanggal potong 24 November 2026.')
  const row = plan(product,session)
  if (!Number.isSafeInteger(input.qty) || input.qty < 1 || input.qty > row.short) throw Error('Sisa yang perlu dipotong untuk pesanan ini ' + row.short + ' pcs.')
  if (!Number.isFinite(input.yards) || input.yards <= 0 || input.yards > yardsLeft(roll.id,session)) throw Error('Periksa jumlah yard terhadap sisa roll.')
  const lot: Lot = {requestId:input.requestId,id: 'POT-D' + String(session.cuts.length + 1).padStart(2,'0'), sku: product.sku, stage: 'cut', kind: 'candidate', qty: input.qty, size: input.size, pattern: pattern.code, material: roll.material, eta: product.due, place: 'Meja potong', roll: roll.id, usedYards: input.yards, sourceYards:yardsLeft(roll.id,session), remainingYards:yardsLeft(roll.id,session)-input.yards}
  return {...session, cuts: [...session.cuts,lot]}
}
export function recordPickup(session: Session, pickup: Pickup): Session {
  const lot = waitingLots(session).find(l => l.id === pickup.id)
  if (!lot) throw Error('Potongan ini sudah diambil. Pilih potongan lain.')
  if (!['Mandor Epi','Mandor Selo','Mandor Afat','Mandor Afui'].includes(pickup.mandor) || !/^2026-11-24T(?:[01]\d|2[0-3]):[0-5]\d$/.test(pickup.at)) throw Error('Pilih mandor dan jam ambil pada 24 November 2026.')
  if (!pickup.batches.length || pickup.batches.some(b => !Number.isSafeInteger(b.qty) || b.qty <= 0) || pickup.batches.reduce((sum,b) => sum + b.qty,0) !== lot.qty) throw Error('Jumlah di semua batch harus sama dengan potongan yang diambil.')
  return {...session, pickups:[...session.pickups,pickup]}
}

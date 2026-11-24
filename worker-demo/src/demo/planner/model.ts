import { sizeRangeLabel } from '../../sizeRangeLabel'
import sample from './sample.json'
import projection from './projection.json'
import { drawingLabel } from '../cuttingAllocation'
import type { ProductionPatternSnapshot } from '../productionModel'

export const { products, patterns, rolls } = sample
export type Product = typeof products[number]
export type Series = { name: string; sizes: string[] }
// Sample model master. A production model owns its set, independently of commercial destinations.
export const modelSeries: Record<string, Series> = {
  'Kulot Jumbo': {name:'Jumbo',sizes:['31','32','33']},
  'Kulot Kecil': {name:'Kecil',sizes:['28','29','30']},
  'Cutbray Jumbo': {name:'Jumbo',sizes:['34','35','36']},
  'Cutbray Lucy': {name:'Kecil',sizes:['28','29','30']},
}
export const rangeLabel = sizeRangeLabel
export const seriesLabel = (series: Series) => 'Seri '+series.name+' · '+rangeLabel(series.sizes)
export function seriesFor(product: Product): Series {
  return { name:modelSeries[patternFor(product.routes[0].pattern).name].name,sizes:product.sizes }
}
export type CutSlot = { size:string; image:string; qty:number }
export type CutRoll = { id:string; material:string; sourceYards:number; usedYards:number; remainingYards:number; slots:CutSlot[] }
export type Lot = {
  id: string; sku: string | null; articleKey?:string; brand?: string | null; patternSnapshot?: ProductionPatternSnapshot; stage: string; kind: string; qty: number; size: string
  series?: Series; outputs?: CutRoll[]; intent?: string; date?: string; notes?: string | null; model?: string; location?: string;
  pattern: string; material: string; eta: string | null; place: string; roll?: string; usedYards?: number; sourceYards?: number; remainingYards?: number; group?: string; requestId?: string
}
export type Pickup = { id: string; mandor: string; at: string; batches: {qty: number; note: string; sizes?: Record<string,number>; sources?: {rollId:string;size:string;qty:number;slot?:number}[]}[] }
type SourceClaim = { roll:string; slot:number; qty:number }
type Destination = { id: string; sku: string; eta: string; sources?:SourceClaim[] }
export type StockChange = { key:string; size:string; delta:number }
export type StockEvent = { id:string; action:'adjust'|'convert'; date?:string; reverses?:string; reason:string; intent?:string; notes?:string|null; changes:StockChange[] }
export type Session = { stockEvents?:StockEvent[]; patternRefs?:Record<string,string|null>; destinations?: Destination[]; cuts: Lot[]; pickups: Pickup[]; confirmed: string[]; elsewhere: string[] }
export const emptySession: Session = { cuts: [], pickups: [], confirmed: [], elsewhere: [] }
export const stageName: Record<string, string> = { cut: 'Meja potong', sewing: 'Jahit', laundry: 'Laundry', qc: 'QC' }
export const productFor = (sku: string | null | undefined) => products.find(p => p.sku === sku)
export function patternFor(code: string) { return patterns.find(p => p.code === code)! }
export type Article={key:string;sku:string;brand:string;colour:string;model:string;sizes:string[];opening:Record<string,number>;pair?:string}
export const articles:Article[]=products.map(p=>({
  key:p.brand+' '+p.sku,sku:p.sku,brand:p.brand,colour:p.colour,model:patternFor(p.routes[0].pattern).name,sizes:p.sizes,
  opening:Object.fromEntries(p.sizes.map(size=>[size,size===p.size?p.fg:6])),
  pair:p.sku==='93001'?'Widie 66002':p.sku==='66001'?'Vivo 66001':undefined,
}))
articles.push(
  {key:'Widie 66002',sku:'66002',brand:'Widie',colour:'Biru tua',model:'Kulot Jumbo',sizes:modelSeries['Kulot Jumbo'].sizes,opening:{31:2,32:3,33:4},pair:'Vivo 93001'},
  {key:'Vivo 66001',sku:'66001',brand:'Vivo',colour:'Biru muda',model:'Kulot Kecil',sizes:modelSeries['Kulot Kecil'].sizes,opening:{28:2,29:3,30:4},pair:'Widie 66001'},
  {key:'Vivo 93001-27',sku:'93001-27',brand:'Vivo',colour:'Biru tua',model:'Kulot Kecil',sizes:['27'],opening:{27:3}},
)
export const articleChoice=(a:Article)=>products.some(p=>p.brand===a.brand&&p.sku===a.sku)?a.sku:a.key
export const cutArticle=(value:string)=>articles.find(a=>articleChoice(a)===value)
export function planningPattern(a:Article,session:Session) {
  const p=products.find(p=>p.sku===a.sku&&p.brand===a.brand)
  return p?recipePattern(p,session):session.patternRefs?.[a.key]??null
}
export function lotPattern(lot: Lot) { return lot.patternSnapshot ?? patternFor(lot.pattern) }
export function lotLabel(lot: Lot) {
  const brand = lot.brand === undefined ? productFor(lot.sku)?.brand : lot.brand
  if (lot.sku) return lot.articleKey??(brand ? brand + ' ' + lot.sku : 'SKU ' + lot.sku)
  return brand ? brand + ' · SKU belum ditentukan' : 'Merek dan SKU belum ditentukan'
}
export function lotSeries(lot: Lot): Series {
  const p=productFor(lot.sku)
  return lot.series ?? (p ? seriesFor(p) : {name:lotPattern(lot).name,sizes:[lot.size]})
}
export function cutRolls(lot: Lot): CutRoll[] {
  if (lot.outputs) return lot.outputs
  if (!lot.roll) return []
  return [{id:lot.roll, material:lot.material, sourceYards:lot.sourceYards ?? 0, usedYards:lot.usedYards ?? 0, remainingYards:lot.remainingYards ?? 0,slots:[{size:lot.size,image:'',qty:lot.qty}]}]
}
export function recipePattern(p:Product,session:Session) {
  const key=p.brand+' '+p.sku
  return session.patternRefs && Object.hasOwn(session.patternRefs,key) ? session.patternRefs[key] : p.routes[0].pattern
}
export function stockDelta(key:string,size:string,session:Session) {
  return (session.stockEvents??[]).flatMap(e=>e.changes).reduce((n,c)=>n+(c.key===key && c.size===size?c.delta:0),0)
}
export function eligiblePieces(lot: Lot, p: Product, session:Session=emptySession) {
  if ((lot.brand && p.brand !== lot.brand) || (lot.sku && lot.articleKey && lot.articleKey!==p.brand+' '+p.sku)) return 0
  const code=recipePattern(p,session)
  const materials=code && patternFor(code)?.id===lotPattern(lot).id ? p.routes.map(route=>route.material) : []
  if (!lot.outputs) return materials.includes(lot.material) && p.size === lot.size ? lot.qty : 0
  return lot.outputs.filter(r => materials.includes(r.material)).flatMap(r => r.slots)
    .reduce((count,slot) => count + (slot.size === p.size ? slot.qty : 0),0)
}
export const possibleTargets = (lot: Lot,session:Session=emptySession) => products.filter(p => eligiblePieces(lot,p,session)>0)
export function day(date: string | null) {
  if (!date) return 'Jadwal belum ditentukan'
  return new Intl.DateTimeFormat('id-ID', {weekday: 'short', day: 'numeric', month: 'short', timeZone: 'Asia/Jakarta'}).format(new Date(date + 'T05:00:00Z')).replace(',', '')
}
function matchingSources(lot:Lot,p:Product,session:Session):SourceClaim[] {
  if(!eligiblePieces(lot,p,session))return []
  return cutRolls(lot).flatMap(roll=>p.routes.some(r=>r.material===roll.material)?roll.slots.flatMap((slot,i)=>slot.size===p.size&&slot.qty>0?[{roll:roll.id,slot:i,qty:slot.qty}]:[]):[])
}
function allocationsFor(lot:Lot,session:Session) {
  const used=new Map<string,number>()
  const claimed=(session.destinations??[]).filter(d=>d.id===lot.id).map(d=>{
    const p=productFor(d.sku)
    const sources=d.sources??(p?matchingSources(lot,p,session):[])
    for(const s of sources){const key=s.roll+'|'+s.slot;used.set(key,(used.get(key)??0)+s.qty)}
    return {...d,sources,qty:sources.reduce((n,s)=>n+s.qty,0)}
  })
  return {claimed,used}
}
function remainingSources(lot:Lot,p:Product,session:Session) {
  const {used}=allocationsFor(lot,session)
  return matchingSources(lot,p,session).map(s=>({...s,qty:s.qty-(used.get(s.roll+'|'+s.slot)??0)})).filter(s=>s.qty>0)
}
export const remainingPieces=(lot:Lot,p:Product,session:Session)=>remainingSources(lot,p,session).reduce((n,s)=>n+s.qty,0)
export function lotsIn(session: Session): Lot[] {
  return [...sample.lots, ...session.cuts].map(source => {
    const lot:Lot=source
    const pickup = session.pickups.find(p => p.id === lot.id)
    if (pickup) return {...lot, stage: 'sewing', kind: lot.sku ? 'directed' : 'unassigned', place: pickup.mandor}
    if (session.elsewhere.includes(lot.id)) return {...lot, kind:'elsewhere'}
    return session.confirmed.includes(lot.id) ? {...lot, kind:'directed'} : lot
  })
}
export function plan(product: Product, session: Session) {
  const initial = projection[product.sku as keyof typeof projection]
  const reference=recipePattern(product,session)
  const fgChange=stockDelta(product.brand+' '+product.sku,product.size,session)
  const all = lotsIn(session)
  const lots=all.flatMap(lot=>{
    const {claimed}=allocationsFor(lot,session)
    const fixed=claimed.filter(d=>d.sku===product.sku).map(d=>({...lot,sku:d.sku,eta:d.eta,kind:'directed',qty:d.qty}))
    if(lot.sku!==product.sku||lot.articleKey&&lot.articleKey!==product.brand+' '+product.sku)return fixed
    const qty=claimed.length?remainingPieces(lot,product,session):lot.kind==='directed'&&!lot.outputs?lot.qty:eligiblePieces(lot,product,session)
    return qty>0?[...fixed,{...lot,qty}]:fixed
  })
  const review=all.filter(lot=>(!lot.sku||(lot.sku===product.sku&&!lot.eta))&&remainingPieces(lot,product,session)>0)
  const active = lots.filter(lot => lot.eta && lot.eta <= product.due)
  const created = new Set(session.cuts.map(lot => lot.id))
  const quantity = (total: number, lot: Lot) => total + lot.qty
  const directed = active.filter(lot => lot.kind === 'directed' &&
    (created.has(lot.id) || session.pickups.some(p => p.id === lot.id) || session.confirmed.includes(lot.id))).reduce(quantity,0)
  const confirmed = initial.directed + directed
  const potential = active.filter(lot=>lot.kind==='candidate').reduce(quantity,0)
  const base = Math.max(0, product.need-product.fg-fgChange-confirmed)
  const short = Math.max(0,base-potential)
  const queue = active.filter(lot => lot.stage === 'cut')
  const check = active.find(lot => lot.kind === 'candidate' && lot.stage !== 'cut')
  const late = lots.filter(lot => lot.eta && lot.eta > product.due).reduce(quantity,0)
  return {product:{...product,fg:product.fg+fgChange}, reference,lots,review,queue,check,confirmed,potential,base,short,late}
}
export type Plan = ReturnType<typeof plan>
export const plansIn = (session: Session) => products.map(p => plan(p, session))
export function action(row: Plan) {
  if (row.short && !row.reference) return 'Tinjau pola rencana'
  if (row.short && row.review.length) return 'Cek potongan tanpa SKU'
  if (row.short) return 'Potong ' + row.short + ' pcs'
  if (row.queue.length) return 'Bagikan ' + row.queue.reduce((sum, lot) => sum + lot.qty, 0) + ' pcs'
  if (row.check) return 'Cek tujuan ' + row.check.qty + ' pcs'
  return 'Tunggu hasil produksi'
}
export function waitingLots(session: Session) {
  return lotsIn(session).filter(lot => lot.stage === 'cut').sort((a,b) => {
    const dueA = productFor(a.sku)?.due ?? '9999'
    const dueB = productFor(b.sku)?.due ?? '9999'
    return dueA.localeCompare(dueB) || a.id.localeCompare(b.id)
  })
}
export function setDestination(session: Session, id: string, sku: string, eta: string): Session {
  const lot = lotsIn(session).find(l => l.id === id)
  if (!lot || (lot.sku && (lot.sku!==sku || lot.eta)) || !possibleTargets(lot,session).some(p => p.sku === sku && remainingPieces(lot,p,session)>0)) throw Error('Pilih SKU yang cocok dengan pola, bahan, merek rencana, dan ukuran potongan.')
  const date = new Date(eta + 'T00:00:00Z')
  if (!/^\d{4}-\d{2}-\d{2}$/.test(eta) || Number.isNaN(date.valueOf()) || date.toISOString().slice(0,10) !== eta || eta < (lot.date??sample.date)) throw Error('Isi perkiraan tanggal siap mulai 24 November 2026.')
  const sources=remainingSources(lot,productFor(sku)!,session)
  return {...session, destinations: [...(session.destinations ?? []), {id,sku,eta,sources}]}
}
export function yardsLeft(id: string, session: Session) {
  return (rolls.find(r => r.id === id)?.yards ?? 0) - session.cuts.flatMap(cutRolls).reduce((sum,roll) => sum + (roll.id === id ? roll.usedYards : 0),0)
}
export function confirmDestination(session: Session, id:string, destination:'order'|'elsewhere'='order'): Session {
  const lot=lotsIn(session).find(l=>l.id===id && l.stage==='sewing' && l.kind==='candidate')
  if(!lot) throw Error('Tujuan jahitan ini sudah pasti.')
  return destination==='order' ? {...session,confirmed:[...session.confirmed,id]} : {...session,elsewhere:[...session.elsewhere,id]}
}
export function suggestedCut(row: Plan, session: Session, material?:string) {
  const options=row.product.routes.flatMap(route=>rolls.filter(r=>r.material===route.material).map(roll=>{
    const available=yardsLeft(roll.id,session)
    return {route,roll,available,qty:Math.min(row.short,Math.floor(available/roll.yardPerPiece))}
  }))
  return options.find(option=>option.roll.material===material) ?? options.sort((a,b)=>b.qty-a.qty)[0]
}
type CutInput = {
  requestId: string; articleKey?:string; sku?: string | null; brand?: string | null; pattern: ProductionPatternSnapshot
  series: Series; model: string; location: string; date: string; notes?: string; eta?: string | null
  slots: string[]; rolls: {id:string; yards:number; quantities:number[]}[]
}
export function recordCut(session: Session, input: CutInput): Session {
  const previous=session.cuts.find(lot=>lot.requestId===input.requestId)
  const intent=JSON.stringify(input)
  if(previous){if(previous.intent&&previous.intent!==intent)throw Error('Permintaan potong sudah dipakai dengan isi berbeda.');return session}
  const sku = input.sku?.trim() || null
  const brand = input.brand?.trim() || null
  const article = input.articleKey ? articles.find(a=>a.key===input.articleKey) : articles.find(a=>a.sku===sku&&(!brand||a.brand===brand))
  const {pattern,series} = input
  if (!input.model.trim() || !input.location.trim() || !pattern?.id || !pattern.code || !pattern.name || !pattern.revision) throw Error('Pilih model, lokasi sumber, dan pola aktif.')
  if (sku && (!article || article.sku!==sku || (brand && article.brand !== brand))) throw Error('Periksa merek dan SKU rencana.')
  if (brand && !products.some(p=>p.brand===brand)) throw Error('Merek rencana tidak dikenal.')
  if (!series.sizes.length || !series.name || !input.slots.length || !input.slots.every(size=>series.sizes.includes(size))) throw Error('Pilih seri ukuran milik model.')
  if (article && (article.model!==input.model || series.sizes.length!==article.sizes.length || series.sizes.some(size=>!article.sizes.includes(size)))) throw Error('Model dan anggota seri harus sesuai Master SKU.')
  if (!validDate(input.date) || input.date>sample.date || (input.eta && (!validDate(input.eta) || input.eta<input.date))) throw Error('Periksa tanggal potong dan perkiraan siap.')
  if (!input.rolls.length || new Set(input.rolls.map(r=>r.id)).size!==input.rolls.length) throw Error('Pilih roll sumber yang berbeda.')
  const outputs = input.rolls.map(row=>{
    const roll=rolls.find(r=>r.id===row.id)
    const available=yardsLeft(row.id,session)
    if (!roll || !Number.isFinite(row.yards) || row.yards<=0 || row.yards>available) throw Error('Periksa yard yang dipakai pada setiap roll.')
    if (row.quantities.length!==input.slots.length || !row.quantities.every(n=>Number.isSafeInteger(n)&&n>=0) || !row.quantities.some(n=>n>0)) throw Error('Isi hasil potong aktual pada setiap roll yang dipakai.')
    const slots=input.slots.map((size,i)=>({size,qty:row.quantities[i],image:input.slots.filter(s=>s===size).length>1?drawingLabel(input.slots.slice(0,i+1).filter(s=>s===size).length):''}))
    return {id:roll.id,material:roll.material,sourceYards:available,usedYards:row.yards,remainingYards:available-row.yards,slots}
  })
  const usedSizes=[...new Set(outputs.flatMap(r=>r.slots.filter(s=>s.qty>0).map(s=>s.size)))]
  const qty=outputs.reduce((sum,r)=>sum+r.slots.reduce((n,s)=>n+s.qty,0),0)
  const lot:Lot={
    id:'POT-D'+String(session.cuts.length+1).padStart(2,'0'), requestId:input.requestId,intent,
    sku,brand,articleKey:article?.key,pattern:pattern.code,patternSnapshot:{...pattern},series:{name:series.name,sizes:[...series.sizes]},
    date:input.date, model:input.model,location:input.location,notes:input.notes?.trim()||null,outputs,qty,
    size:usedSizes.join(', '),material:[...new Set(outputs.map(r=>r.material))].join(' / '),
    eta:input.eta||null,stage:'cut',kind:sku?'candidate':'unassigned',place:'Meja potong',
  }
  return {...session,cuts:[...session.cuts,lot]}
}
function validDate(date:string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false
  const timestamp=Date.parse(date+'T00:00:00Z')
  return Number.isFinite(timestamp) && new Date(timestamp).toISOString().slice(0,10)===date
}
export function recordPickup(session: Session, pickup: Pickup): Session {
  const lot = waitingLots(session).find(l => l.id === pickup.id)
  if (!lot) throw Error('Potongan ini sudah diambil. Pilih potongan lain.')
  if (!['Mandor Epi','Mandor Selo','Mandor Afat','Mandor Afui'].includes(pickup.mandor) || (!validDate(pickup.at.slice(0,10)) || !/^.{10}T(?:[01]\d|2[0-3]):[0-5]\d$/.test(pickup.at) || pickup.at.slice(0,10)<(lot.date??sample.date) || pickup.at.slice(0,10)>sample.date)) throw Error('Pilih mandor dan waktu ambil yang sesuai tanggal potong.')
  if (!pickup.batches.length || pickup.batches.some(b => !Number.isSafeInteger(b.qty) || b.qty <= 0) || pickup.batches.reduce((sum,b) => sum + b.qty,0) !== lot.qty) throw Error('Jumlah di semua batch harus sama dengan potongan yang diambil.')
  if (pickup.batches.some(b=>b.sources || b.sizes)) {
    const quantities=new Map<string,number>()
    for (const roll of cutRolls(lot)) for (const slot of roll.slots) {
      const key=roll.id+'|'+slot.size
      quantities.set(key,(quantities.get(key)??0)+slot.qty)
    }
    for (const batch of pickup.batches) {
      if (!batch.sources || !batch.sizes || Object.values(batch.sizes).reduce((n,q)=>n+q,0)!==batch.qty) throw Error('Rincian ukuran batch belum lengkap.')
      const mix:Record<string,number>={}
      for (const source of batch.sources) {
        const key=source.rollId+'|'+source.size
        if (!Number.isSafeInteger(source.qty)||source.qty<=0||!quantities.has(key)) throw Error('Periksa sumber batch.')
        quantities.set(key,quantities.get(key)!-source.qty)
        mix[source.size]=(mix[source.size]??0)+source.qty
      }
      if ([...new Set([...Object.keys(mix),...Object.keys(batch.sizes)])].some(size=>(mix[size]??0)!==(batch.sizes?.[size]??0))) throw Error('Rincian ukuran batch tidak cocok dengan roll.')
    }
    if ([...quantities.values()].some(q=>q!==0)) throw Error('Jumlah tiap roll dan ukuran harus cocok dengan potongan asal.')
  }
  // Assignments retain the actual drawing in addition to the size totals.
  if(pickup.batches.every(b=>b.sources)){
    const remaining=cutRolls(lot).flatMap(r=>r.slots.map((s,i)=>({rollId:r.id,size:s.size,slot:i+1,qty:s.qty})))
    const batches=pickup.batches.map(b=>({...b,sources:b.sources!.flatMap(source=>{
      let need=source.qty
      const split=[]
      for(const entry of remaining){
        if(entry.rollId!==source.rollId||entry.size!==source.size||!entry.qty||!need)continue
        const qty=Math.min(entry.qty,need);split.push({...entry,qty});need-=qty;entry.qty-=qty
      }
      if(need)throw Error('Hasil gambar tidak cukup untuk alokasi.')
      return split
    })}))
    return {...session,pickups:[...session.pickups,{...pickup,batches}]}
  }
  return {...session, pickups:[...session.pickups,pickup]}
}

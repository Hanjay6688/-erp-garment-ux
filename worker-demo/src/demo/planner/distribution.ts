import type { CutRoll, Lot, Pickup, Session } from './model'

export type Source = {rollId:string; size:string; slot:number; qty:number}
type PickupLine = Pickup['batches'][number]
export type ProofKind = 'Jahit'|'Laundry'|'QC'|'Barang jadi'
export type Batch = {
  no:number; qty:number; note:string; sizes:Record<string,number>; sources:Source[]
  mandor:string; at:string; revision:number; sewn:number; proof?:ProofKind; closed?:'Reverse'|'Adjust'; previous?:number
}
export type BatchEvent = {
  id:string; group:string; no:number; revision:number; recorded:string; physical:string; intent:string
  kind:'Reverse'|'Adjust'|'Bagi ulang'|'Proses'; reason:string; created:Batch[]; released:Source[]; proof?:ProofKind; pcs?:number
}
export type ReturnLot = {no:number; sources:Source[]}
export type Distribution = {id:string; batches:Batch[]; returns:ReturnLot[]; events:BatchEvent[]}
export const sampleGroup='POT-024'
const sampleRollA='ORI-024-A', sampleRollB='ORI-024-B'
const source=(rollId:string,size:string,slot:number,qty:number):Source=>({rollId,size,slot,qty})
const demoRoll=(id:string,slots:[string,number][]):CutRoll=>({
  id,material:'1069 Ori',sourceYards:32,usedYards:18,remainingYards:14,
  slots:slots.map(([size,qty])=>({size,image:'A',qty})),
})
export const distributionLot:Lot={
  id:sampleGroup,sku:'66002',articleKey:'Widie 66002',brand:'Widie',pattern:'KJ',model:'Kulot Jumbo',material:'1069 Ori',
  series:{name:'Jumbo',sizes:['31','32','33']},size:'31, 32, 33',qty:28,stage:'cut',kind:'directed',
  date:'2026-11-24',eta:null,place:'Meja potong',
  outputs:[demoRoll(sampleRollA,[['31',8],['32',8]]),demoRoll(sampleRollB,[['32',4],['33',8]])],
}
export const total=(rows:Source[])=>rows.reduce((sum,row)=>sum+row.qty,0)
export function sizeTotals(rows:Source[]) {
  const sizes:Record<string,number>={}
  for(const row of rows)sizes[row.size]=(sizes[row.size]??0)+row.qty
  return sizes
}
function lineFromSources(sources:Source[]):PickupLine{return {qty:total(sources),sizes:sizeTotals(sources),sources,note:''}}
export const distributionPickup:Pickup={
  id:sampleGroup,mandor:'Mandor Afui',at:'2026-11-24T09:00',batches:[
    lineFromSources([source(sampleRollA,'31',1,4),source(sampleRollA,'32',2,2),source(sampleRollB,'33',2,2)]),
    lineFromSources([source(sampleRollA,'31',1,4),source(sampleRollA,'32',2,4),source(sampleRollB,'32',1,2),source(sampleRollB,'33',2,2)]),
    lineFromSources([source(sampleRollA,'32',2,2),source(sampleRollB,'32',1,2),source(sampleRollB,'33',2,4)]),
  ],
}
export const pickupsIn=(s:Session)=>[...s.pickups,distributionPickup]
export const returnId=(id:string,no:number)=>id+'-B'+String(no).padStart(2,'0')+'-KEMBALI'
const key=(r:Source)=>JSON.stringify([r.rollId,r.slot,r.size])
function amounts(rows:Source[]) {
  const counts=new Map<string,number>()
  for(const row of rows){
    if(!row.rollId||!row.size||!Number.isSafeInteger(row.slot)||row.slot<1||!Number.isSafeInteger(row.qty)||row.qty<1)throw Error('Rincian roll, gambar, atau ukuran tidak lengkap.')
    counts.set(key(row),(counts.get(key(row))??0)+row.qty)
  }
  return counts
}
function sameSources(left:Source[],right:Source[]) {
  const a=amounts(left), b=amounts(right)
  return a.size===b.size&&[...a].every(([k,v])=>b.get(k)===v)
}
function batch(line:PickupLine,no:number,mandor:string,at:string,previous?:number):Batch {
  const traced=line.sources?.every(r=>Number.isSafeInteger(r.slot)&&r.slot!>0&&r.qty>0)
  const sources=traced?line.sources!.map(r=>({...r,slot:r.slot!})):[]
  return {no,mandor,at,previous,qty:line.qty,note:line.note,sizes:line.sizes??sizeTotals(sources),sources,revision:0,sewn:0}
}
export function distribution(pickup:Pickup,session:Session):Distribution {
  const batches=pickup.batches.map((b,i)=>batch(b,i+1,pickup.mandor,pickup.at))
  if(pickup.id===sampleGroup){batches[0].sewn=1;batches[0].proof='Jahit'}
  const returns:ReturnLot[]=[]
  const events=(session.batchEvents??[]).filter(e=>e.group===pickup.id)
  for(const event of events){
    const b=batches.find(row=>row.no===event.no)!
    if(event.kind==='Proses'){
      b.proof=event.proof
      b.sewn+=event.proof==='Jahit'?(event.pcs??0):0
    }else if(event.kind==='Bagi ulang'){
      const index=returns.findIndex(r=>r.no===b.no)
      if(index>=0)returns.splice(index,1)
    }else{
      b.closed=event.kind
      if(event.released.length)returns.push({no:b.no,sources:event.released})
    }
    b.revision++
    batches.push(...event.created.map(row=>({...row})))
  }
  return {id:pickup.id,batches,returns,events}
}
export function correctionLock(b:Batch) {
  if(b.closed)return 'Sudah dikoreksi'
  if(b.proof)return 'Ada bukti '+b.proof.toLowerCase()+(b.sewn?' · '+b.sewn+' pcs dijahit':'')
  if(!b.sources.length||total(b.sources)!==b.qty)return 'Rincian roll dan gambar asal belum lengkap'
  return ''
}
type CommandBase={id:string;group:string;no:number;revision:number;recorded:string;physical:string}
export type Command=CommandBase&(
  {kind:'Reverse';reason:string}|
  {kind:'Adjust';reason:string;sizes:Record<string,number>;note:string}|
  {kind:'Bagi ulang';pickup:Pickup;pickupRequest:string}|
  {kind:'Proses';proof:ProofKind;pcs:number}
)
export function applyBatch(session:Session,cmd:Command):Session {
  const {recorded,...parameters}=cmd
  const intent=JSON.stringify(parameters)
  const existing=session.batchEvents?.find(e=>e.id===cmd.id)
  if(existing){
    if(existing.intent!==intent)throw Error('Nomor permintaan sudah dipakai untuk perubahan lain.')
    return session
  }
  if(!cmd.id.trim()||!Number.isFinite(Date.parse(recorded))||!/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d$/.test(cmd.physical))throw Error('Waktu atau nomor permintaan tidak valid.')
  const pickup=pickupsIn(session).find(p=>p.id===cmd.group)
  if(!pickup)throw Error('Pengambilan asal tidak ditemukan.')
  const state=distribution(pickup,session)
  const b=state.batches.find(row=>row.no===cmd.no)
  if(!b||b.revision!==cmd.revision)throw Error('Batch sudah berubah. Buka kembali detailnya.')
  if(cmd.physical<b.at)throw Error('Waktu transaksi mendahului pengambilan asal.')
  const event:BatchEvent={id:cmd.id,group:state.id,no:b.no,revision:b.revision,kind:cmd.kind,recorded,physical:cmd.physical,intent,reason:'',created:[],released:[]}
  const next=Math.max(...state.batches.map(row=>row.no))+1
  if(cmd.kind==='Bagi ulang'){
    const pending=state.returns.find(r=>r.no===b.no)
    const lines=cmd.pickup.batches
    if(!pending||cmd.pickup.id!==returnId(state.id,b.no)||cmd.pickup.at!==cmd.physical||!lines.length)throw Error('Potongan kembali ini sudah dibagi atau sumbernya berubah.')
    if(!['Mandor Afui','Mandor Afat','Mandor Epi','Mandor Selo'].includes(cmd.pickup.mandor))throw Error('Periksa mandor penerima.')
    event.created=lines.map((line,i)=>batch(line,next+i,cmd.pickup.mandor,cmd.pickup.at,b.no))
    if(event.created.some(row=>!row.qty||total(row.sources)!==row.qty||Object.keys({...row.sizes,...sizeTotals(row.sources)}).some(size=>(row.sizes[size]??0)!==(sizeTotals(row.sources)[size]??0)))||
       !sameSources(pending.sources,event.created.flatMap(row=>row.sources)))throw Error('Jumlah tiap roll, gambar, dan ukuran harus sama dengan potongan kembali.')
  }else if(cmd.kind==='Proses'){
    if(b.closed||!Number.isSafeInteger(cmd.pcs)||cmd.pcs<1||cmd.pcs>b.qty||(cmd.proof==='Jahit'&&(b.sewn+cmd.pcs>b.qty||(b.proof&&b.proof!=='Jahit'))))throw Error('Jumlah proses melebihi sisa batch atau batch sudah ditutup.')
    event.proof=cmd.proof;event.pcs=cmd.pcs
  }else{
    const lock=correctionLock(b)
    if(lock)throw Error(lock)
    if(!state.batches.every(row=>total(row.sources)===row.qty))throw Error('Sumber distribusi lama belum lengkap untuk koreksi.')
    event.reason=cmd.reason.trim()
    if(!event.reason)throw Error('Isi alasan koreksi.')
    if(cmd.kind==='Reverse')event.released=b.sources
    else{
      const keep={...cmd.sizes}, capacity=sizeTotals(b.sources)
      if(Object.entries(keep).some(([size,n])=>!Object.hasOwn(capacity,size)||!Number.isSafeInteger(n)||n<0||n>capacity[size]))throw Error('Jumlah ukuran melebihi isi batch.')
      const selected:Source[]=[]
      for(const row of b.sources){
        const qty=Math.min(keep[row.size]??0,row.qty)
        if(qty)selected.push({...row,qty})
        if(row.qty>qty)event.released.push({...row,qty:row.qty-qty})
        keep[row.size]=(keep[row.size]??0)-qty
      }
      if(!selected.length)throw Error('Gunakan Reverse untuk mengembalikan seluruh batch.')
      if(!event.released.length&&cmd.note.trim()===b.note)throw Error('Jumlah dan catatan masih sama.')
      event.created=[batch({...lineFromSources(selected),note:cmd.note.trim()},next,b.mandor,cmd.physical,b.no)]
    }
  }
  return {...session,batchEvents:[...(session.batchEvents??[]),event]}
}

// Keep the original roll and drawing positions when projecting a partial lot.
export function sliceLot(lot:Lot,rolls:CutRoll[],sources:Source[]):Lot {
  const quantities=amounts(sources)
  const outputs=rolls.map(r=>({...r,slots:r.slots.map((s,i)=>({...s,qty:quantities.get(key({rollId:r.id,slot:i+1,size:s.size,qty:0}))??0}))}))
    .filter(r=>r.slots.some(s=>s.qty>0))
  return {...lot,outputs,qty:total(sources),size:Object.keys(sizeTotals(sources)).join(', ')}
}

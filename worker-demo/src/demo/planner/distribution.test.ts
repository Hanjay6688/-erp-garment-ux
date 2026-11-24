import { describe,expect,it } from 'vitest'
import { applyBatch,distribution,distributionPickup,pickupsIn,returnId,sampleGroup,sizeTotals,total,type Command,type Source } from './distribution'
import { emptySession,lotsIn,plan,products,recordPickup,setDestination,waitingLots,type Lot,type Pickup,type Session } from './model'
const clock='2026-11-24T10:30'
const original=()=>distribution(distributionPickup,emptySession)
const reverse:Command={id:'r2',group:sampleGroup,no:2,revision:0,kind:'Reverse',reason:'Batch 2 perlu dibagi dua',recorded:'2026-11-24T04:00:00Z',physical:clock}
const balances=(s:Session)=>lotsIn(s).filter(l=>(l.originId??l.id)===sampleGroup).map(l=>[l.stage,l.qty])
function split(s:Session):Pickup{
  const queue=waitingLots(s).find(l=>l.originId===sampleGroup)!
  return {id:queue.id,requestId:'split2',expectedRevision:queue.returnRevision,mandor:'Mandor Epi',at:clock,batches:[
    {qty:7,note:'',sizes:{31:4,32:3},sources:[{rollId:'ORI-024-A',size:'31',qty:4},{rollId:'ORI-024-A',size:'32',qty:3}]},
    {qty:5,note:'',sizes:{32:3,33:2},sources:[{rollId:'ORI-024-A',size:'32',qty:1},{rollId:'ORI-024-B',size:'32',qty:2},{rollId:'ORI-024-B',size:'33',qty:2}]}
  ]}
}
const bySource=(sources:Source[])=>sources.reduce<Record<string,number>>((a,r)=>{const k=[r.rollId,r.slot,r.size].join('/');a[k]=(a[k]??0)+r.qty;return a},{})
describe('Koreksi satu batch distribusi',()=>{
  it('menyisakan B1 dan B3 tepat seperti semula, menerbitkan B4+B5 dan menyimpan asal per gambar sesudah reload',()=>{
    const reversed=applyBatch(emptySession,reverse)
    expect(balances(reversed)).toEqual([['sewing',16],['cut',12]])
    const pending=distribution(distributionPickup,reversed)
    expect(sizeTotals(pending.returns[0].sources)).toEqual({31:4,32:6,33:2})
    const request=split(reversed),after=recordPickup(reversed,request)
    expect(recordPickup(after,request)).toBe(after)
    expect(()=>recordPickup(after,{...request,mandor:'Mandor Selo'})).toThrow(/perubahan lain/)
    const restored=JSON.parse(JSON.stringify(after)),ledger=distribution(distributionPickup,restored)
    expect(ledger.returns).toEqual([])
    expect(waitingLots(restored).some(l=>l.id===request.id)).toBe(false)
    expect(ledger.batches[0]).toEqual(original().batches[0]);expect(ledger.batches[2]).toEqual(original().batches[2])
    expect(ledger.batches[1]).toMatchObject({closed:'Reverse',qty:12})
    expect(ledger.batches.slice(3).map(b=>[b.no,b.qty,b.previous])).toEqual([[4,7,2],[5,5,2]])
    expect(bySource(ledger.batches.slice(3).flatMap(b=>b.sources))).toEqual(bySource(original().batches[1].sources))
    expect(balances(restored)).toEqual([['sewing',16],['sewing',12]])
    expect(ledger.events.map(e=>e.kind)).toEqual(['Reverse','Bagi ulang'])
  })
  it('adjust mengarsipkan yang lama, membiarkan tetangga, dan mengembalikan selisih per roll, gambar dan ukuran',()=>{
    const s=applyBatch(emptySession,{...reverse,kind:'Adjust',sizes:{31:4,32:3,33:0},note:'Paket pagi'})
    const ledger=distribution(distributionPickup,s),replacement=ledger.batches[3]
    expect(replacement).toMatchObject({previous:2,no:4,qty:7,note:'Paket pagi'})
    expect(ledger.batches[1]).toMatchObject({qty:12,closed:'Adjust'})
    expect(sizeTotals(ledger.returns[0].sources)).toEqual({32:3,33:2})
    expect(bySource([...replacement.sources,...ledger.returns[0].sources])).toEqual(bySource(original().batches[1].sources))
    expect(balances(s)).toEqual([['sewing',23],['cut',5]])
    expect(()=>applyBatch(emptySession,{...reverse,kind:'Adjust',sizes:{31:5,32:3},note:''})).toThrow(/melebihi/)
    expect(()=>applyBatch(emptySession,{...reverse,kind:'Adjust',sizes:{},note:''})).toThrow(/Reverse/)
  })
  it.each(['Jahit','Laundry','QC','Barang jadi'] as const)('bukti %s memblokir kedua operasi termasuk form usang',proof=>{
    const s=applyBatch(emptySession,{...reverse,kind:'Proses',id:'proof',proof,pcs:1})
    expect(()=>applyBatch(s,reverse)).toThrow(/berubah/)
    expect(()=>applyBatch(s,{...reverse,revision:1})).toThrow(/bukti/)
    expect(()=>applyBatch(s,{...reverse,revision:1,kind:'Adjust',sizes:{31:1},note:''})).toThrow(/bukti/)
    expect(()=>applyBatch(s,{...reverse,no:3})).not.toThrow()
  })
  it('menolak source palsu, pembagian ganda, nomor permintaan bentrok, dan tanggal ambil sebelum reversal',()=>{
    const s=applyBatch(emptySession,reverse),request=split(s)
    expect(applyBatch(s,{...reverse,recorded:'2026-11-25T01:00:00Z'})).toBe(s)
    expect(()=>applyBatch(s,{...reverse,reason:'lain'})).toThrow(/perubahan lain/)
    expect(()=>applyBatch(s,{...reverse,id:'r2b'})).toThrow(/berubah/)
    expect(()=>recordPickup(s,{...request,at:'2026-11-24T10:00'})).toThrow(/mendahului/)
    const bad=structuredClone(request);bad.batches[0].sources![0].rollId='ORI-024-B'
    expect(()=>recordPickup(s,bad)).toThrow(/sumber|roll/i)
    expect(distribution(distributionPickup,s).batches).toHaveLength(3)
  })
  it('memakai pickup baru dengan dua gambar ukuran yang sama dan membatasi tujuan Planner ke stok fisik',()=>{
    const cut:Lot={id:'POT-UJI',sku:null,pattern:'KJ',material:'1069 Ori',qty:10,size:'32',series:{name:'Jumbo',sizes:['31','32','33']},
      stage:'cut',kind:'unassigned',place:'Meja potong',eta:null,outputs:[{id:'R-A',material:'1069 Ori',sourceYards:30,usedYards:10,remainingYards:20,slots:[{size:'32',image:'A',qty:4},{size:'32',image:'B',qty:6}]}]}
    let s:Session={...emptySession,cuts:[cut]}
    s=setDestination(s,cut.id,'93001','2026-11-26')
    s=recordPickup(s,{id:cut.id,mandor:'Mandor Epi',at:clock,batches:[6,4].map(qty=>({qty,note:'',sizes:{32:qty},sources:[{rollId:'R-A',size:'32',qty}]}))})
    expect(distribution(pickupsIn(s)[0],s).batches[0].sources.map(r=>r.slot)).toEqual([1,2])
    s=applyBatch(s,{...reverse,group:cut.id,no:1})
    const planner=plan(products[0],s).lots.filter(l=>l.originId===cut.id)
    expect(planner.map(l=>[l.stage,l.qty])).toEqual([['sewing',4],['cut',6]])
    const returned=waitingLots(s).find(l=>l.id===returnId(cut.id,1))!
    expect(returned.outputs![0].slots.map(r=>[r.image,r.qty])).toEqual([['A',4],['B',2]])
    expect(s.stockEvents).toBeUndefined()
  })
  it('pembagian ulang satu retur tidak mengambil saldo retur kedua',()=>{
    const first=applyBatch(emptySession,reverse), both=applyBatch(first,{...reverse,id:'r3',no:3})
    const after=recordPickup(both,split(both)),ledger=distribution(distributionPickup,after)
    expect(ledger.returns.map(r=>[r.no,total(r.sources)])).toEqual([[3,8]])
    expect(ledger.batches.filter(b=>!b.closed).reduce((n,b)=>n+b.qty,0)).toBe(20)
  })
  it('kunci data lama bila gambar atau asal fisik belum tercatat',()=>{
    const pickup={id:'lama',at:clock,mandor:'Mandor Epi',batches:[{qty:6,note:''}]}
    expect(()=>applyBatch({...emptySession,pickups:[pickup]},{...reverse,no:1,group:'lama'})).toThrow(/belum lengkap/)
  })
  it('membatalkan kartu asli Lucy dan Zodiak dengan sumber yang persis lalu menolak pembatalan kedua',()=>{
    for(const [id,expected,rolls] of [['POT-260827-042',222,9],['POT-260825-039',114,1]] as const){
      const pickup=pickupsIn(emptySession).find(p=>p.id===id)!,initial=distribution(pickup,emptySession)
      const cmd={...reverse,group:id,no:3},s=applyBatch(emptySession,cmd)
      const group=distribution(pickup,s),returned=waitingLots(s).filter(l=>l.originId===id)
      expect(returned.map(l=>l.qty)).toEqual([expected]);expect(returned[0].outputs).toHaveLength(rolls)
      expect(group.batches.slice(0,2)).toEqual(initial.batches.slice(0,2))
      expect(group.returns[0].sources).toEqual(initial.batches[2].sources)
      expect(applyBatch(s,cmd)).toBe(s)
      expect(()=>applyBatch(s,{...cmd,id:'double'})).toThrow('berubah')
      expect(()=>applyBatch(emptySession,{...cmd,id:'sewn',no:1})).toThrow('bukti')
    }
  })
  it('koreksi antar batch mempertahankan setiap roll/gambar yang dapat dikembalikan kemudian',()=>{
    const cmd:Command={...reverse,kind:'Koreksi',operation:'REDISTRIBUTION',chosen:{},edits:[
      {no:2,revision:0,sizes:{31:4,32:5,33:2}},{no:3,revision:0,sizes:{32:5,33:4}}]}
    const s=applyBatch(emptySession,cmd),rows=distribution(distributionPickup,s).batches
    expect(rows.map(b=>b.qty)).toEqual([8,11,9]);expect(rows[0]).toEqual(original().batches[0])
    expect(bySource(rows.flatMap(r=>r.sources))).toEqual(bySource(original().batches.flatMap(r=>r.sources)))
    const back=applyBatch(s,{...reverse,id:'undo-three',no:3,revision:1})
    expect(waitingLots(back).find(l=>l.returnedBatch===3)?.qty).toBe(9)
    expect(()=>applyBatch(emptySession,{...cmd,edits:[cmd.edits[0]]})).toThrow(/sama/)
  })
  it('meminta sumber fisik yang tepat untuk kelebihan hasil hitung sebelum mengembalikan potongan',()=>{
    const cmd:Command={...reverse,kind:'Koreksi',operation:'PHYSICAL_RECOUNT',chosen:{},edits:[{no:2,revision:0,sizes:{31:4,32:7,33:2}}]}
    expect(()=>applyBatch(emptySession,cmd)).toThrow(/roll dan gambar/)
    const s=applyBatch(emptySession,{...cmd,chosen:{32:JSON.stringify(['ORI-024-B',1,'32'])}})
    const back=applyBatch(s,{...reverse,id:'return-13',revision:1})
    expect(waitingLots(back).find(l=>l.returnedBatch===2)?.qty).toBe(13)
    expect(distribution(distributionPickup,back).returns[0].sources.find(r=>r.rollId==='ORI-024-B'&&r.slot===1)?.qty).toBe(3)
  })

  it('satu batch yang jejaknya lengkap dapat kembali ketika rincian gambar batch saudara lama hilang',()=>{
    const group='POT-CAMPUR'
    const physical:Lot={id:group,sku:null,pattern:'KJ',material:'1069 Ori',qty:10,size:'32',stage:'cut',kind:'unassigned',place:'Meja potong',eta:null,
      series:{name:'Jumbo',sizes:['32']},outputs:[{id:'R',material:'1069 Ori',sourceYards:6,usedYards:5,remainingYards:1,slots:[{size:'32',image:'A',qty:10}]}]}
    const pickup:Pickup={id:group,mandor:'Mandor Epi',at:clock,batches:[{qty:6,note:''},{qty:4,note:'',sizes:{32:4},sources:[{rollId:'R',size:'32',slot:1,qty:4}]}]}
    const s={...emptySession,cuts:[physical],pickups:[pickup]}
    const after=applyBatch(s,{...reverse,group,no:2}),ledger=distribution(pickup,after)
    expect(ledger.batches[0]).toEqual(distribution(pickup,s).batches[0])
    const pieces=lotsIn(after).filter(l=>l.originId===group)
    expect(pieces.map(l=>[l.stage,l.qty,l.outputs?.[0].slots[0].qty])).toEqual([['sewing',6,6],['cut',4,4]])
    expect(()=>applyBatch(after,{...reverse,id:'missing',group,no:1})).toThrow('belum lengkap')
  })

})

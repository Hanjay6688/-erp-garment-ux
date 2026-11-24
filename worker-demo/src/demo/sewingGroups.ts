import {distribution,pickupsIn,type Batch} from './planner/distribution'
import {lotPattern,lotSeries,productionLots,type Session} from './planner/model'
import {sewingBatchId,sewingReceipts} from './sewingReceipts'
import {summarizeLaundryBatch,type LaundryDelivery} from './laundryModel'

export function sewingGroups(session:Session){
  const lots=new Map(productionLots(session).map(l=>[l.id,l]))
  return pickupsIn(session).map(pickup=>{
    const lot=lots.get(pickup.id),receipt=sewingReceipts.find(r=>r.parent.id===pickup.id)
    const ledger=distribution(pickup,session)
    const sizes=lot?lotSeries(lot).sizes:[...new Set(ledger.batches.flatMap(b=>Object.keys(b.sizes)))]
    return {
      id:pickup.id,sequence:receipt?.parent.sequence??(Number(pickup.id.match(/\d+$/)?.[0])||0),
      model:lot?.model||lot&&lotPattern(lot)?.name||pickup.id,material:lot?.material??'',
      mandor:pickup.mandor,plannedBrand:lot?.brand??undefined,skuRef:lot?.articleKey??undefined,
      pattern:lot?lotPattern(lot)??null:null,sizes,at:pickup.at,pickupAt:receipt?.parent.pickupAt??pickup.at.replace('T',' · '),
      pickup,ledger,batches:ledger.batches.map(b=>({
        id:sewingBatchId(pickup.id,b.no),number:b.no,qty:b.qty,sizes:sizes.map(size=>b.sizes[size]??0),
        completed:b.sewn,note:b.note,line:b,
      })),
    }
  }).sort((a,b)=>b.at.localeCompare(a.at)||b.sequence-a.sequence)
}
export type SewingGroup=ReturnType<typeof sewingGroups>[number]
export type SewingRow=SewingGroup['batches'][number]

export function downstreamLock(id:string,deliveries:LaundryDelivery[],drafts:Record<string,string>,finalized:{batchId:string}[]){
  if(finalized.some(r=>r.batchId===id))return 'hasil QC atau barang jadi'
  if(deliveries.some(d=>d.batchId===id))return 'bukti laundry'
  return drafts[id]?'draft laundry':''
}
export function sewingStatus(b:Batch,id:string,deliveries:LaundryDelivery[],drafts:Record<string,string>){
  const summary=summarizeLaundryBatch(deliveries,id)
  if(b.closed)return b.closed==='Reverse'?'Dibatalkan':'Disesuaikan'
  if(summary.returned)return summary.outside?'Kembali sebagian · siap QC':'Kembali · siap QC'
  if(summary.outside)return 'Di laundry'
  if(drafts[id])return 'Draft laundry'
  return b.sewn>=b.qty?'Siap laundry':b.sewn?'Sedang dijahit':'Menunggu jahit'
}

import {fabricRollCatalog} from './cuttingAllocation'
import {sewingWipSeeds} from './sewingModel'
import type {CutRoll,Lot,Pickup} from './planner/model'
import type {Source} from './planner/distribution'

const lucyRolls:CutRoll[]=fabricRollCatalog.slice(0,9).map(r=>({
  id:r.id,material:r.material,sourceYards:r.yards,usedYards:r.yards,remainingYards:0,
  slots:r.allocation.map((qty,i)=>({size:['31','32','33'][Math.floor(i/2)],image:i%2?'B':'A',qty})),
}))
export const zodiakRolls:CutRoll[]=[[7,107,103.5],[8,106.5,103],[9,105,101.5]].map(([n,yards,used])=>({
  id:'ZDK-260826-'+String(n).padStart(2,'0'),material:'Zodiak KW',sourceYards:yards,usedYards:used,remainingYards:yards-used,
  slots:['34','35','36'].flatMap(size=>['A','B'].map(image=>({size,image,qty:19}))),
}))

// The Lucy pickup assigned one size to each child. Zodiak assigned one complete roll per child.
export const sewingReceipts=sewingWipSeeds.map(parent=>{
  const lucy=parent.id==='POT-260827-042',zodiak=parent.id==='POT-260825-039'
  const outputs=lucy?lucyRolls:zodiak?zodiakRolls:[]
  const day='2026-08-'+parent.id.slice(8,10)
  const at=day+'T'+parent.pickupAt.split(' · ')[1]
  const children=parent.batches.map((b,i)=>{
    const sources:Source[]=outputs.flatMap((r,ri)=>r.slots.flatMap((slot,j)=>
      (lucy?slot.size===parent.sizes[i]:ri===i)&&slot.qty>0?[{rollId:r.id,slot:j+1,size:slot.size,qty:slot.qty}]:[]))
    return {qty:b.qty,note:b.note,sizes:Object.fromEntries(parent.sizes.map((s,j)=>[s,b.sizes[j]])),sources}
  })
  const pickup:Pickup={id:parent.id,mandor:parent.mandor,at,batches:children}
  const lot:Lot={id:parent.id,date:day,sku:null,brand:parent.plannedBrand,pattern:parent.pattern!.code,patternSnapshot:parent.pattern!,
    stage:'sewing',kind:'unassigned',place:parent.mandor,qty:children.reduce((n,b)=>n+b.qty,0),size:parent.sizes.join(', '),
    series:{name:'',sizes:parent.sizes},model:parent.model,material:parent.material,eta:null,outputs}
  return {parent,pickup,lot}
})

export function sewingBatchId(group:string,no:number){
  const archive=sewingReceipts.find(r=>r.parent.id===group)
  return (archive?String(archive.parent.sequence).padStart(3,'0')+'-':group+'-B')+String(no).padStart(2,'0')
}

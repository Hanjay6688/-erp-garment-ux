import type {Batch,Source} from './distribution'

export type CountEdit={no:number;revision:number;sizes:Record<string,number>}
export type CountOperation='REDISTRIBUTION'|'PHYSICAL_RECOUNT'
export const sourceCode=(s:Source)=>JSON.stringify([s.rollId,s.slot,s.size])
export function sourceChoices(rows:Source[]){
  const unique=new Map(rows.map(s=>[sourceCode(s),s]))
  return Array.from(unique.values())
}
export type CountUpdate={no:number;before:Record<string,number>;sizes:Record<string,number>;qty:number;sources:Source[]}
export function reviseCounts(batches:Batch[],edits:CountEdit[],operation:CountOperation,chosen:Record<string,string>,origin:Source[],physical:string):CountUpdate[]{
  if(!edits.length||new Set(edits.map(e=>e.no)).size!==edits.length)throw Error('Periksa batch yang berubah.')
  const pool:Source[]=[],choices=sourceChoices(origin)
  const result=edits.map(edit=>{
    const row=batches.find(b=>b.no===edit.no)
    if(!row||row.revision!==edit.revision||row.closed||row.proof||physical<row.at)throw Error('Batch sudah berubah atau mempunyai bukti proses.')
    if(!row.sources.length)throw Error('Asal potongan belum lengkap.')
    const needs={...edit.sizes},sizes={...needs},qty=Object.values(sizes).reduce((a,n)=>a+n,0)
    if(!qty||Object.entries(needs).some(([size,n])=>!Number.isSafeInteger(n)||n<0||(n>0&&!choices.some(r=>r.size===size))))throw Error('Periksa jumlah dan ukuran batch.')
    const sources:Source[]=[]
    for(const r of row.sources){
      const keep=Math.min(r.qty,needs[r.size]??0)
      if(keep)sources.push({...r,qty:keep})
      if(r.qty>keep)pool.push({...r,qty:r.qty-keep})
      needs[r.size]=(needs[r.size]??0)-keep
    }
    return {no:row.no,before:row.sizes,sizes,qty,sources,needs}
  })
  for(const row of result){
    for(const [size,need] of Object.entries(row.needs)){
      let left=need
      for(const r of pool){
        if(!left||r.size!==size||!r.qty)continue
        const take=Math.min(r.qty,left)
        row.sources.push({...r,qty:take});r.qty-=take;left-=take
      }
      if(!left)continue
      if(operation==='REDISTRIBUTION')throw Error('Total setiap ukuran harus tetap sama.')
      const options=choices.filter(r=>r.size===size)
      const source=options.length===1?options[0]:options.find(r=>sourceCode(r)===chosen[size])
      if(!source)throw Error('Pilih roll dan gambar untuk tambahan ukuran '+size+'.')
      row.sources.push({...source,qty:left})
    }
  }
  if(operation==='REDISTRIBUTION'&&pool.some(r=>r.qty>0))throw Error('Total setiap ukuran harus tetap sama.')
  return result.map(({needs,...row})=>{
    const bySlot=new Map<string,Source>()
    for(const r of row.sources){
      const k=sourceCode(r),old=bySlot.get(k)
      bySlot.set(k,{...r,qty:(old?.qty??0)+r.qty})
    }
    return {...row,sources:[...bySlot.values()]}
  })
}

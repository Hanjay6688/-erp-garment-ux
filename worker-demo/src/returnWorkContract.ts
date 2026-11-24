export type ReturnTask={key:string;domain:'ACCESSORY_CUSTODY';rule_id:string;source_id:string;document_id:string|null;stage:'INSPECTION'|'VALUATION'|'CREDIT_REVIEW';condition:'WAITING'|'USABLE'|'DAMAGED';pending:string;posted_valued:string|null;received:string}
export const names={INSPECTION:'Periksa barang retur',VALUATION:'Nilai barang retur',CREDIT_REVIEW:'Tinjau kredit retur mandor'}
export const conditions={WAITING:'belum diperiksa',USABLE:'layak',DAMAGED:'rusak'}
export function parseReturnTasks(v:unknown):ReturnTask[]{
 if(!Array.isArray(v))throw Error('Daftar tugas retur tidak lengkap.')
 const uuid=/^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/
 const decimal=/^\d+(\.\d+)?$/
 const unique=new Set<string>()
 return v.map((r:ReturnTask)=>{
  if(!r||r.domain!=='ACCESSORY_CUSTODY'||!Object.hasOwn(names,r.stage)||!Object.hasOwn(conditions,r.condition)||!uuid.test(r.source_id)
    ||r.key!==['ACCESSORY_RETURN',r.source_id,r.stage,r.condition].join(':')||r.rule_id!=='ACCESSORY_RETURN_'+r.stage||unique.has(r.key)
    ||r.document_id!==null&&!uuid.test(r.document_id)||(r.stage==='INSPECTION')!==(r.condition==='WAITING')
    ||typeof r.pending!=='string'||!decimal.test(r.pending)||!/[1-9]/.test(r.pending)||typeof r.received!=='string'||!decimal.test(r.received)||r.posted_valued!==null&&!decimal.test(r.posted_valued))throw Error('Sumber tugas retur tidak sesuai lot.')
  unique.add(r.key);return r
 })
}

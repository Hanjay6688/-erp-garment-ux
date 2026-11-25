import sample from './planner/sample.json'
import type {Session} from './planner/model'

type FabricRoll = {
  id: string
  material: string
  supplier: string
  receivedAt: string
  original: number
  remaining: number
  supplierReturned: number
  location: string
  status: 'Available' | 'In Use' | 'Empty'
  costState: 'ACTUAL' | 'ESTIMATED'
  activeCost: number
  source: string
}

export const fabricRolls: FabricRoll[] = [
  { id:'LCY-031', material:'Lucy', supplier:'Sinaran', receivedAt:'2026-08-27', original:131.5, remaining:113, supplierReturned:18.5, location:'A-02-03', status:'Available', costState:'ACTUAL', activeCost:49200, source:'SJ-260827-018' },
  { id:'LCY-030', material:'Lucy', supplier:'Sinaran', receivedAt:'2026-08-27', original:124, remaining:96.5, supplierReturned:0, location:'A-02-02', status:'Available', costState:'ACTUAL', activeCost:49200, source:'SJ-260827-018' },
  { id:'LCY-029', material:'Lucy', supplier:'Sinaran', receivedAt:'2026-08-27', original:91, remaining:18.5, supplierReturned:0, location:'Area Retur', status:'Available', costState:'ACTUAL', activeCost:49200, source:'RT-MD-260828-004' },
  { id:'LCY-028', material:'Lucy', supplier:'Sinaran', receivedAt:'2026-08-25', original:140, remaining:140, supplierReturned:0, location:'Staging Potong', status:'Available', costState:'ESTIMATED', activeCost:48500, source:'SJ-260825-012' },
  { id:'1069-027', material:'1069 Ori', supplier:'Sinaran', receivedAt:'2026-08-24', original:118, remaining:118, supplierReturned:0, location:'B-01-01', status:'Available', costState:'ACTUAL', activeCost:50750, source:'SJ-260824-009' },
  { id:'1069-026', material:'1069 Ori', supplier:'Sinaran', receivedAt:'2026-08-24', original:107.5, remaining:33, supplierReturned:0, location:'B-01-02', status:'Available', costState:'ACTUAL', activeCost:50750, source:'SJ-260824-009' },
  { id:'ZDK-018', material:'Zodiak KW', supplier:'Sumber Cahaya', receivedAt:'2026-08-27', original:103, remaining:103, supplierReturned:0, location:'C-02-01', status:'Available', costState:'ESTIMATED', activeCost:47600, source:'SJ-260827-021' },
  { id:'CRB-007', material:'Corduroy 8W', supplier:'Mitra Tekstil', receivedAt:'2026-08-22', original:108, remaining:28.5, supplierReturned:18, location:'D-01-02', status:'Available', costState:'ACTUAL', activeCost:68400, source:'SJ-260822-006' },
]

const historicalRolls = [
  {id:'ORI-018', material:'1069 Ori', supplier:'Sinaran', yards:50, yardPerPiece:1.5, day:'2026-08-21', source:'SJ-SNR-0821-07', rate:49_200},
  {id:'LCY-015', material:'Lucy', supplier:'Sinaran', yards:45, yardPerPiece:1.25, day:'2026-08-21', source:'SJ-SNR-0821-03', rate:49_200},
]
const demoRollRates: Record<string, number> = {'ORI-021':49_200,'KW-023':47_600,'LCY-022':49_200}
export const openingCorrectionRolls = [...sample.rolls.map(roll=>({
  ...roll, day:'2026-11-23', source:'Saldo latihan November', rate:demoRollRates[roll.id] as number|undefined, physicalCode:undefined,
})), ...historicalRolls.map(roll=>({...roll,physicalCode:undefined}))]

export type FabricIdentityCorrection = {
  id: string
  source: string
  roll?: string
  before: string
  after: string
  reason: string
  at: string
}
type ArchiveLine = {id:string; length:number; location:string}
export type FabricArchiveDocument = {
  key:string; reference:string; material:string; supplier:string; day:string
  kind:'surat'|'saldo'|'retur'; lines: ArchiveLine[]
}

const archiveByRoll = new Map<string,FabricArchiveDocument>()
const groups = new Map<string,FabricArchiveDocument>()
for (const row of [
  ...fabricRolls.map(r=>({id:r.id,reference:r.source,supplier:r.supplier,material:r.material,day:r.receivedAt,length:r.original,location:r.location})),
  ...openingCorrectionRolls.map(r=>({id:r.id,reference:r.source,supplier:r.supplier,material:r.material,day:r.day,length:r.yards,location:'Gudang Kain'})),
]) {
  const kind = row.reference.startsWith('SJ-')?'surat':row.reference.startsWith('RT-')?'retur':'saldo'
  const group = kind==='surat'?JSON.stringify([row.reference,row.supplier,row.material,row.day]):row.id
  const doc:FabricArchiveDocument = groups.get(group) ?? {key:'arsip:'+row.id,reference:row.reference,material:row.material,supplier:row.supplier,day:row.day,kind,lines:[]}
  doc.lines.push({id:row.id,length:row.length,location:row.location})
  groups.set(group,doc)
  archiveByRoll.set(row.id,doc)
}
export const archiveDocumentFor = (rollId:string) => archiveByRoll.get(rollId)
export const archiveDocuments = [...groups.values()]
export function archiveSource(rollId:string) {
  const doc = archiveByRoll.get(rollId)!
  return { label:doc.kind==='surat'?'Buka penerimaan':doc.kind==='retur'?'Buka retur masuk':'Buka saldo awal',
    href:'/gudang/pembelian-penerimaan/?'+new URLSearchParams({jenis:'kain',arsip:rollId})+'#dokumen-penerimaan' }
}
type IdentityBook = Pick<Session,'fabricIdentities'>
export function fabricIdentity(book:IdentityBook, source:string, original:string, roll?:string) {
  const events=book.fabricIdentities??[]
  for (let index=events.length-1;index>=0;index--) {
    const row=events[index]
    if(row.source===source&&row.roll===roll)return row.after
  }
  return original
}
export const receiptMaterial = (book:IdentityBook, doc:{id:string;material:string}) => fabricIdentity(book,'penerimaan:'+doc.id,doc.material)
export function archiveIdentity(book:IdentityBook,id:string) {
  const doc=archiveByRoll.get(id)!
  const code=fabricIdentity(book,doc.key,id,id)
  return {material:fabricIdentity(book,doc.key,doc.material),physicalCode:code===id?undefined:code}
}

import { accessoryStockAt, mainAccessories, masterBook, serviceAccessories, type AccessoryLocation } from './accessoryPricing'
import { dayOk } from './warehouseDay'
import type { Session } from './planner/model'
import type { ReceiptReversal, StockSourceLink } from './receiptRollCorrection'

export type ServiceAction = 'USE'|'TO_SERVICE'|'FROM_SERVICE'
export type ServiceDocument = {
  id:string; action:ServiceAction; location:AccessoryLocation; day:string; reason:string
  lines:{code:string;name:string;qty:number;job:string;rate:number}[]
  reversal?:ReceiptReversal
}
export type CustodyNote = {id:string;customer:string;item:string;qty:number;job:string;day:string;returnedOn?:string}
export type SalvageDocument = {
  id:string;code:string;name:string;expected:number;holder:string;reference?:string;conversion?:string;day:string
  receipts:{id:string;day:string;qty:number}[]
  inspections:{id:string;day:string;good:number;damaged:number;note:string;reversal?:ReceiptReversal}[]
}
type SalvageLink={id:string;day:string;left:number|null;holder:string;label:string}
export const serviceActions:Record<ServiceAction,string>={USE:'Pakai untuk servis',TO_SERVICE:'Transfer ke Pos Servis',FROM_SERVICE:'Kembalikan stok dari Pos Servis'}
const amountOk=(qty:number)=>Number.isSafeInteger(qty)&&qty>0&&qty<=999999999

export function postService(session:Session,input:Omit<ServiceDocument,'lines'>&{lines:{code:string;qty:number;job:string}[]}):Session {
  if(session.serviceDocuments?.some(doc=>doc.id===input.id))return session
  const location=input.action==='USE'?input.location:input.action==='TO_SERVICE'?mainAccessories:serviceAccessories
  if(!dayOk(input.day)||!input.lines.length||input.reason.trim().length<4||![mainAccessories,serviceAccessories].includes(location))throw Error('Isi tanggal, barang, lokasi, dan keterangan pemakaian/transfer.')
  const rows=masterBook().items
  const totals=new Map<string,number>()
  const lines=input.lines.map(line=>{
    const item=rows.find(row=>row.code===line.code&&row.active&&row.stockUom.toLowerCase()==='pcs')
    const qty=(totals.get(line.code)??0)+line.qty
    if(!item||!amountOk(line.qty)||qty>accessoryStockAt(item,location,session)||input.action==='USE'&&line.job.trim().length<2){
      throw Error('Periksa stok di lokasi asal, jumlah pcs, dan referensi pekerjaan per barang.')
    }
    totals.set(line.code,qty)
    return {...line,name:item.name,job:input.action==='USE'?line.job.trim():'',rate:item.movingAverage}
  })
  return {...session,serviceDocuments:[...(session.serviceDocuments??[]),{...input,location,reason:input.reason.trim(),lines}]}
}

export const serviceDocumentPath=(id:string)=>'/gudang/aksesori/?tab=servis&dokumen='+encodeURIComponent(id)+'#riwayat-servis'
export const salvageDocumentPath=(id:string)=>'/gudang/aksesori/?tab=bongkaran&dokumen='+encodeURIComponent(id)+'#riwayat-bongkaran'

export function serviceReversalBlockers(session:Session,doc:ServiceDocument):StockSourceLink[] {
  if(doc.action==='USE')return []
  const target=doc.action==='TO_SERVICE'?serviceAccessories:mainAccessories
  const projected={...session,serviceDocuments:session.serviceDocuments?.filter(row=>row.id!==doc.id)}
  const active=masterBook().items.filter(item=>doc.lines.some(line=>line.code===item.code)&&accessoryStockAt(item,target,projected)<0)
  if(!active.length)return []
  const codes=new Set(active.map(item=>item.code))
  const uses=(session.serviceDocuments??[]).filter(row=>row.id!==doc.id&&!row.reversal&&row.day>=doc.day&&row.lines.some(line=>codes.has(line.code))
    &&(row.action==='USE'?row.location===target:row.action==='FROM_SERVICE'?target===serviceAccessories:target===mainAccessories))
  const conversions=(session.stockEvents??[]).filter(row=>!session.stockEvents?.some(other=>other.reverses===row.id)
    &&row.kit?.used.some(line=>codes.has(line.code)&&(line.location??mainAccessories)===target))
  return [...uses.map(row=>({label:serviceActions[row.action]+' · '+row.id,href:serviceDocumentPath(row.id)})),
    ...conversions.map(row=>({label:'Ganti Merek '+row.id.slice(0,8),href:'/gudang/ganti-merek/?mutasi='+encodeURIComponent(row.id)+'#riwayat-konversi'})),
    ...active.map(item=>({label:'Saldo '+item.name+' · '+target,href:'/gudang/aksesori/?item='+encodeURIComponent(item.code)}))]
}

export function reverseService(session:Session,id:string,reason:string):Session {
  const doc=session.serviceDocuments?.find(row=>row.id===id&&!row.reversal)
  if(!doc||reason.trim().length<4||serviceReversalBlockers(session,doc).length)throw Error('Periksa saldo dan dokumen pemakaian terkait.')
  return {...session,serviceDocuments:session.serviceDocuments?.map(row=>row===doc?{...row,reversal:{reason:reason.trim(),at:new Date().toISOString()}}:row)}
}

export function postCustody(session:Session,record:CustodyNote):Session {
  if(session.accessoryCustody?.some(row=>row.id===record.id))return session
  if(!dayOk(record.day)||!amountOk(record.qty)||!record.customer.trim()||!record.job.trim()||!record.item.trim())throw Error('Isi pemilik, barang, jumlah, dan referensi servis.')
  return {...session,accessoryCustody:[...(session.accessoryCustody??[]),record]}
}

export function closeCustody(session:Session,id:string,day:string):Session {
  const row=session.accessoryCustody?.find(item=>item.id===id)
  if(!row||row.returnedOn||!dayOk(day)||day<row.day)throw Error('Periksa tanggal pengembalian titipan.')
  return {...session,accessoryCustody:session.accessoryCustody?.map(item=>item===row?{...item,returnedOn:day}:item)}
}

export function salvageProgress(doc:SalvageDocument) {
  const received=doc.receipts.reduce((sum,row)=>sum+row.qty,0)
  const good=doc.inspections.reduce((sum,row)=>sum+(row.reversal?0:row.good),0)
  const damaged=doc.inspections.reduce((sum,row)=>sum+(row.reversal?0:row.damaged),0)
  return {received,good,damaged,pending:received-good-damaged,held:doc.expected-received}
}

export function salvageLinks(session:Session,code:string) {
  if(!code)return []
  const events=session.stockEvents??[]
  return events.filter(event=>event.action==='convert'&&!event.reverses&&!events.some(row=>row.reverses===event.id)).flatMap<SalvageLink>(event=>{
    const line=event.kit?.expected.find(row=>row.code===code)
    const label=(event.changes.find(row=>row.delta<0)?.key??'')+' → '+(event.changes.find(row=>row.delta>0)?.key??'')
    if(!line)return [{id:event.id,day:event.date??'',left:null,holder:'',label}]
    const accepted=(session.conversionReturns??[]).reduce((sum,row)=>sum+(row.conversion===event.id&&row.code===code&&!row.reversed?row.good+row.damaged:0),0)
    const reserved=(session.accessorySalvage??[]).reduce((sum,row)=>sum+(row.conversion===event.id&&row.code===code?row.expected:0),0)
    const left=line.qty-accepted-reserved
    return left>0?[{id:event.id,day:event.date??'',left,holder:line.holder,label}]:[]
  })
}

export function openSalvage(session:Session,input:Omit<SalvageDocument,'name'|'inspections'|'receipts'>&{qty:number}):Session {
  if(session.accessorySalvage?.some(doc=>doc.id===input.id))return session
  const item=masterBook().items.find(row=>row.code===input.code&&row.active&&row.stockUom.toLowerCase()==='pcs')
  const link=salvageLinks(session,input.code).find(row=>row.id===input.conversion)
  if(!item||!dayOk(input.day)||!amountOk(input.qty)||!amountOk(input.expected)||input.qty>input.expected||!input.holder.trim()
    ||input.conversion&&(!link||link.left!==null&&input.expected>link.left||input.day<link.day))throw Error('Periksa aksesori, jumlah yang kembali, dan referensi bongkaran.')
  const {qty,...record}=input
  return {...session,accessorySalvage:[...(session.accessorySalvage??[]),{
    ...record,name:item.name,receipts:[{id:record.id,qty,day:record.day}],inspections:[],
  }]}
}

export function receiveSalvage(session:Session,id:string,receipt:SalvageDocument['receipts'][number]):Session {
  const doc=session.accessorySalvage?.find(row=>row.id===id)
  if(doc?.receipts.some(row=>row.id===receipt.id))return session
  if(!doc||!amountOk(receipt.qty)||receipt.qty>salvageProgress(doc).held||!dayOk(receipt.day)||receipt.day<doc.day){
    throw Error('Jumlah penerimaan melebihi barang yang masih ditunggu, atau tanggal belum sesuai.')
  }
  return {...session,accessorySalvage:session.accessorySalvage?.map(row=>row===doc?{...row,receipts:[...row.receipts,receipt]}:row)}
}

export function inspectSalvage(session:Session,id:string,inspection:SalvageDocument['inspections'][number]):Session {
  const doc=session.accessorySalvage?.find(row=>row.id===id)
  if(doc?.inspections.some(row=>row.id===inspection.id))return session
  if(!doc||!dayOk(inspection.day)||!amountOk(inspection.good+inspection.damaged)||inspection.good<0||inspection.damaged<0
    ||!Number.isInteger(inspection.good)||!Number.isInteger(inspection.damaged)||inspection.note.trim().length<4){
    throw Error('Periksa jumlah layak/rusak, tanggal, dan hasil pemeriksaan.')
  }
  const inspections=doc.inspections.filter(row=>!row.reversal)
  const days=[inspection.day,...inspections.map(row=>row.day)].filter(day=>day>=inspection.day)
  if(days.some(day=>doc.receipts.filter(row=>row.day<=day).reduce((sum,row)=>sum+row.qty,0)<inspection.good+inspection.damaged+
    inspections.filter(row=>row.day<=day).reduce((sum,row)=>sum+row.good+row.damaged,0))){
    throw Error('Jumlah diperiksa melebihi barang yang secara fisik sudah kembali pada tanggal tersebut.')
  }
  return {...session,accessorySalvage:session.accessorySalvage?.map(row=>row===doc?{...row,inspections:[...row.inspections,inspection]}:row)}
}

export function salvageInspectionBlockers(session:Session,doc:SalvageDocument,inspection:SalvageDocument['inspections'][number]):StockSourceLink[] {
  const item=masterBook().items.find(row=>row.code===doc.code)
  if(!inspection.good||item&&accessoryStockAt(item,mainAccessories,session)>=inspection.good)return []
  return [{label:'Pemakaian '+doc.name,href:'/gudang/aksesori/?item='+encodeURIComponent(doc.code)}]
}

export function reverseSalvageInspection(session:Session,docId:string,inspectionId:string,reason:string) {
  const doc=session.accessorySalvage?.find(row=>row.id===docId)
  const inspection=doc?.inspections.find(row=>row.id===inspectionId&&!row.reversal)
  if(!doc||!inspection||reason.trim().length<4||salvageInspectionBlockers(session,doc,inspection).length)throw Error('Periksa pemeriksaan dan saldo aksesori.')
  return {...session,accessorySalvage:session.accessorySalvage?.map(row=>row===doc?{...row,inspections:row.inspections.map(check=>check===inspection
    ?{...check,reversal:{reason:reason.trim(),at:new Date().toISOString()}}:check)}:row)}
}

import { readRupiahInput } from '../moneyInput'
import { correctionRolls, cutRolls, originalCutLots, physicalRollId, yardsLeft, type AccessoryReceipt, type FabricReceipt, type Session } from './planner/model'
import { cutDocumentPath, receiptRolls, reviewRollReceiptCorrection, type StockSourceLink } from './receiptRollCorrection'
import { pocketScale, readPocketNumber } from './pocketUsage'
import { dayOk } from './warehouseDay'
import { masterBook, noteStock, masterCode, mainAccessories } from './accessoryPricing'
import { readNotes } from './issueDocuments'
import { readSupplierInvoices } from './supplierInvoices'

export type FabricReceiptDraft = Omit<FabricReceipt,'rate'|'rolls'>&{price:string;lengths:string[]}
export function prepareFabricReceipt(draft:FabricReceiptDraft):FabricReceipt {
  const {id,day,unit}=draft
  const number=draft.number.trim(),material=draft.material.trim(),supplier=draft.supplier.trim()
  const rate=readRupiahInput(draft.price)
  if(!number||!material||!supplier||!dayOk(day))throw Error('Isi surat jalan, bahan, pabrik atau supplier, dan tanggal fisik.')
  if(!Number.isFinite(rate)||rate<0||!['yd','m'].includes(unit))throw Error('Periksa harga acuan dan satuan surat jalan.')
  const rolls=draft.lengths.flatMap((value,index)=>{
    if(!value.trim())return []
    const length=readPocketNumber(value)
    if(length<=0||!Number.isSafeInteger(Math.round(length*pocketScale)))throw Error('Periksa panjang roll '+(index+1)+'.')
    return [{id:number+'-'+String(index+1).padStart(2,'0'),length}]
  })
  if(!rolls.length)throw Error('Isi minimal satu roll.')
  const total=rolls.reduce((sum,roll)=>sum+Math.round(roll.length*rate*100),0)
  if(!Number.isSafeInteger(total))throw Error('Total nilai penerimaan melebihi batas.')
  return {id,number,material,supplier,day,unit,rate,rolls}
}

export function postFabricReceipt(session:Session,doc:FabricReceipt):Session {
  const previous=session.fabricReceipts??[]
  const same=previous.find(row=>row.id===doc.id)
  if(same){if(JSON.stringify(same)!==JSON.stringify(doc))throw Error('Isi penerimaan berubah. Buka review lagi.');return session}
  if(previous.some(row=>row.number.toLowerCase()===doc.number.toLowerCase()))throw Error('Surat jalan kain ini sudah tercatat.')
  const existing=new Set(fabricRollIdentities(session).flatMap(row=>[row.id,row.physicalCode??row.id]).map(code=>code.toLowerCase()))
  if(doc.rolls.some(row=>existing.has(row.id.toLowerCase())))throw Error('Nomor roll sudah tercatat.')
  return {...session,fabricReceipts:[doc,...previous]}
}

function fabricRollIdentities(session:Session) {
  return [
    ...correctionRolls({...session,fabricReceipts:[]}).map(row=>({id:row.id,length:row.yards,physicalCode:row.physicalCode})),
    ...(session.fabricReceipts??[]).flatMap(receiptRolls),
  ]
}

export function fabricRollUses(session:Session,id:string,includeReversed=false) {
  const cuts=originalCutLots(includeReversed?{...session,cutReversals:undefined}:session)
  return cuts.flatMap(lot=>cutRolls(lot).filter(roll=>physicalRollId(lot.id,roll.id,session)===id&&roll.usedYards>0)
    .map(roll=>({lot,qty:roll.usedYards,reversed:session.cutReversals?.[lot.id]})))
}

function invoiceLinks(sourceId:string):StockSourceLink[] {
  return readSupplierInvoices().filter(doc=>doc.lines.some(line=>line.source.id===sourceId)&&!doc.reversal)
    .map(doc=>({label:(doc.status==='DRAFT'?'Draf invoice ':'Invoice ')+doc.number,href:'/keuangan/hutang-supplier/?'+
      new URLSearchParams({invoice:doc.number,...(doc.group==='ACCESSORY'?{bagian:'aksesori'}:{})})}))
}

export function fabricReceiptBlockers(session:Session,receipt:FabricReceipt):StockSourceLink[] {
  const lots=[...new Set(receipt.rolls.flatMap(roll=>fabricRollUses(session,roll.id).map(({lot})=>lot.id)))]
  return [...invoiceLinks('kain:'+receipt.id),...lots.map(id=>({label:'Potongan '+id,href:cutDocumentPath(id)}))]
}

export function accessoryReceiptBlockers(session:Session,receipt:AccessoryReceipt):StockSourceLink[] {
  const blockers=invoiceLinks('acc:'+receipt.id)
  const opening=masterBook().items.find(row=>row.code===receipt.code)?.stock??0
  if(noteStock(receipt.code,opening,undefined,session)>=receipt.qty)return blockers
  const notes=readNotes().filter(doc=>doc.inventoryChange&&doc.inventoryChange<0&&doc.lines.some(line=>masterCode(line.id)===receipt.code))
  const events=(session.stockEvents??[]).filter(event=>event.kit?.used.some(line=>line.code===receipt.code&&(line.location??mainAccessories)===mainAccessories)
    &&!session.stockEvents?.some(row=>row.reverses===event.id))
  const service=(session.serviceDocuments??[]).filter(doc=>!doc.reversal&&(doc.action==='TO_SERVICE'||doc.action==='USE'&&doc.location===mainAccessories)
    &&doc.lines.some(line=>line.code===receipt.code))
  return [...blockers,
    ...notes.map(doc=>({label:'Nota Ambil '+doc.number,href:'/keuangan/nota-ambil-mandor/?nota='+encodeURIComponent(doc.number)})),
    ...events.map(doc=>({label:'Ganti Merek '+doc.id.slice(0,8),href:'/gudang/ganti-merek/?mutasi='+encodeURIComponent(doc.id)+'#riwayat-konversi'})),
    ...service.map(doc=>({label:doc.id,href:'/gudang/aksesori/?tab=servis&dokumen='+encodeURIComponent(doc.id)+'#riwayat-servis'})),
    {label:'Periksa saldo dan mutasi '+receipt.code,href:'/gudang/aksesori/?item='+encodeURIComponent(receipt.code)},
  ]
}

export function reverseWarehouseReceipt(session:Session,kind:'fabric'|'accessory',id:string,reason:string) {
  const reversal={reason:reason.trim(),at:new Date().toISOString()}
  if(reversal.reason.length<4)throw Error('Isi alasan pembalikan.')
  if(kind==='fabric'){
    const receipt=session.fabricReceipts?.find(row=>row.id===id&&!row.reversal)
    if(!receipt||fabricReceiptBlockers(session,receipt).length)throw Error('Periksa penerimaan dan selesaikan dokumen terkait.')
    return {...session,fabricReceipts:session.fabricReceipts?.map(row=>row===receipt?{...row,reversal}:row)}
  }
  const receipt=session.accessoryReceipts?.find(row=>row.id===id&&!row.reversal)
  if(!receipt||accessoryReceiptBlockers(session,receipt).length)throw Error('Periksa penerimaan dan selesaikan dokumen terkait.')
  return {...session,accessoryReceipts:session.accessoryReceipts?.map(row=>row===receipt?{...row,reversal}:row)}
}

export function correctFabricReceiptRoll(session:Session,receiptId:string,rollId:string,input:{id:string;code:string;length:number;reason:string;at:string}) {
  const receipt=session.fabricReceipts?.find(row=>row.id===receiptId&&!row.reversal)
  const roll=receipt&&receiptRolls(receipt).find(row=>row.id===rollId)
  if(!receipt||!roll)throw Error('Pilih roll dari penerimaan aktif.')
  const used=receipt.unit==='yd'?roll.length-yardsLeft(rollId,session):0
  const correction=reviewRollReceiptCorrection(roll,input,fabricRollIdentities(session),used)
  const total=receiptRolls(receipt).reduce((sum,line)=>sum+(line===roll||line.id===rollId?correction.length:line.length),0)
  const invoiced=readSupplierInvoices().filter(doc=>!doc.reversal).flatMap(doc=>doc.lines).reduce((sum,line)=>sum+(line.source.id==='kain:'+receipt.id?line.qty:0),0)
  if(Math.round(total*pocketScale)<Math.round(invoiced*pocketScale))throw Error('Panjang baru kurang dari yang sudah dipilih di invoice. Periksa invoice terkait.')
  if(!Number.isSafeInteger(Math.round(total*receipt.rate*100)))throw Error('Periksa nilai penerimaan setelah koreksi.')
  return {...session,fabricReceipts:session.fabricReceipts?.map(row=>row===receipt?{...row,corrections:[...(row.corrections??[]),correction]}:row)}
}

import { readRupiahInput } from '../moneyInput'
import { correctionRolls, type FabricReceipt, type Session } from './planner/model'
import { pocketScale, readPocketNumber } from './pocketUsage'
import { dayOk } from './warehouseDay'

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
  const existing=new Set(correctionRolls(session).map(row=>row.id.toLowerCase()))
  if(doc.rolls.some(row=>existing.has(row.id.toLowerCase())))throw Error('Nomor roll sudah tercatat.')
  return {...session,fabricReceipts:[doc,...previous]}
}

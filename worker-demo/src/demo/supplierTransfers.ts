import { cashAccounts, payables, type Payable } from '../financeData'
import { dayOk } from './warehouseDay'
import { invoicePayable, readSupplierInvoices, type SupplierInvoice } from './supplierInvoices'

type Allocation={number:string;cents:number}
export type SupplierTransfer={id:string;party:string;day:string;account:string;reference:string;allocations:Allocation[];replaces?:string;reversed?:{day:string;reason:string;replacement?:string}}
const key='erp.demo.supplier-transfers.v1'
export const readSupplierTransfers=():SupplierTransfer[]=>JSON.parse(sessionStorage.getItem(key)??'[]')
const save=(rows:SupplierTransfer[])=>{sessionStorage.setItem(key,JSON.stringify(rows));return rows}
const trainingPayables:Payable[]=[...payables,{
  number:'INV-ST-8823',party:'CV Sinar Textile',kind:'MATERIAL_AP',economicDate:'11 Nov 2026',receivedDate:'13 Nov 2026',dueDate:'13 Des 2026',
  amount:8300000,paid:0,status:'OPEN',costState:'ACTUAL',reference:'BELI-KAIN-0112',
}]
const invoiceReceived=(value:string)=>{
  const [day,month,year]=value.split(' ')
  return year+'-'+String('Jan Feb Mar Apr Mei Jun Jul Agu Sep Okt Nov Des'.split(' ').indexOf(month)+1).padStart(2,'0')+'-'+day.padStart(2,'0')
}

export function transferPayables(rows:SupplierTransfer[],except?:string,invoices:SupplierInvoice[]=readSupplierInvoices()):Payable[] {
  const allocations=rows.filter(row=>!row.reversed&&row.id!==except).flatMap(row=>row.allocations)
  return [...trainingPayables,...invoices.filter(row=>row.status==='POSTED').map(invoicePayable)].map(item=>{
    const paidCents=allocations.reduce((sum,row)=>sum+(row.number===item.number?row.cents:0),Math.round(item.paid*100))
    if(paidCents===Math.round(item.paid*100))return item
    return {...item,paid:paidCents/100,status:paidCents>=Math.round(item.amount*100)?'PAID':item.status==='OVERDUE'?'OVERDUE':'PARTIAL'}
  })
}
export const transferTotal=(row:SupplierTransfer)=>row.allocations.reduce((sum,item)=>sum+item.cents,0)/100

export function saveSupplierTransfer(input:SupplierTransfer,declaredCents:number,reason='') {
  const rows=readSupplierTransfers()
  const replay=rows.find(row=>row.id===input.id)
  if(replay){if(JSON.stringify(replay)!==JSON.stringify(input))throw Error('Nomor transfer sudah digunakan.');return rows}
  const original=rows.find(row=>row.id===input.replaces&&!row.reversed&&row.party===input.party)
  if(input.replaces&&(!original||original.allocations.length!==1||original.allocations[0]?.number!==input.allocations[0]?.number||reason.trim().length<4))throw Error('Periksa pembayaran dan alasan koreksi untuk invoice asal.')
  if(!dayOk(input.day)||!cashAccounts.some(row=>row.name===input.account)||input.reference.trim().length<3||input.allocations.length!==1)
    throw Error('Isi tanggal, rekening, bukti, dan pembayaran untuk satu invoice.')
  if(rows.some(row=>!row.reversed&&row.id!==original?.id&&row.account===input.account&&row.reference.toLowerCase()===input.reference.toLowerCase()))
    throw Error('Bukti transfer sudah terpakai pada rekening ini.')
  const source=transferPayables(rows,original?.id)
  const sum=input.allocations.reduce((n,row)=>n+row.cents,0)
  if(!Number.isSafeInteger(sum)||sum!==declaredCents||input.allocations.some(row=>{
    const item=source.find(doc=>doc.number===row.number)
    return !item||item.kind==='MATERIAL_GRNI'||item.party!==input.party||!Number.isSafeInteger(row.cents)||row.cents<=0
      ||row.cents>Math.round((item.amount-item.paid)*100)||input.day<invoiceReceived(item.receivedDate)
  }))throw Error('Periksa nominal terhadap sisa tagihan dan tanggal invoice.')

  return save([...rows.map(row=>row===original?{...row,reversed:{day:input.day,reason:reason.trim(),replacement:input.id}}:row),input])
}

export function reverseSupplierTransfer(id:string,day:string,reason:string) {
  const rows=readSupplierTransfers()
  const original=rows.find(row=>row.id===id&&!row.reversed)
  if(!original||!dayOk(day)||day<original.day||reason.trim().length<4)throw Error('Periksa transfer asal, tanggal, dan alasan pembalikan.')
  return save(rows.map(row=>row===original?{...row,reversed:{day,reason:reason.trim()}}:row))
}

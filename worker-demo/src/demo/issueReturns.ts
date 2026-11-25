import { activeIssueReturns, cash, documentTotal, outstandingIssue, readNotes, saveNotes, type IssueDocument, type IssueReturn } from './issueDocuments'
import { editablePayroll, payrollClaim, readPayDrafts } from './payrollSources'
import { masterBook, masterCode, noteStock } from './accessoryPricing'
import type { StockSourceLink } from './receiptRollCorrection'
import { dayOk } from './warehouseDay'

export function issueReturnPath(note:string,entry:string) {
  return '/keuangan/nota-ambil-mandor/?'+new URLSearchParams({nota:note,retur:entry})+'#'+encodeURIComponent(entry)
}

export function issuePaid(doc:IssueDocument) {
  if(doc.settledAt)return documentTotal(doc)
  const payroll=readPayDrafts().find(row=>row.number===payrollClaim(doc.number))
  const throughPayroll=payroll?.status==='PAID'?(payroll.accessoryNotes.find(row=>row.number===doc.number)?.total??0):0
  return (doc.settledAmount??0)+throughPayroll
}

export function returnableIssueLines(doc:IssueDocument) {
  const returned=activeIssueReturns(doc).flatMap(row=>row.lines)
  return doc.lines.map(line=>({...line,remaining:Math.max(0,line.qty-returned.reduce((sum,row)=>sum+(row.lineId===line.id?row.qty:0),0))}))
}

export function quoteIssueReturn(doc:IssueDocument,quantities:Record<string,string>,paid:number) {
  const eligible=returnableIssueLines(doc)
  const valid=Object.entries(quantities).every(([id,raw])=>!raw||/^\d{1,9}$/.test(raw)&&Number(raw)<=(eligible.find(row=>row.id===id)?.remaining??0))
  const lines=eligible.flatMap(line=>{
    const qty=Number(quantities[line.id]??0)
    return qty>0?[{lineId:line.id,qty,amount:cash(qty*(line.sellingPrice??0))}]:[]
  })
  const value=cash(lines.reduce((sum,row)=>sum+row.amount,0))
  const remaining=outstandingIssue(doc,paid)
  const chargeReduction=Math.min(value,remaining)
  return {valid,lines,value,chargeReduction,credit:cash(value-chargeReduction),remaining}
}

export function postIssueReturn(number:string,id:string,day:string,reason:string,quantities:Record<string,string>) {
  saveNotes(documents=>{
    const doc=documents.find(row=>row.number===number)
    if(!doc||doc.status!=='POSTED')throw Error('Buka Nota Ambil Aksesori yang sudah terposting.')
    if(doc.returns?.some(row=>row.id===id))return documents
    const assigned=readPayDrafts().find(row=>row.number===payrollClaim(number))
    if(assigned&&!editablePayroll(assigned)&&assigned.status!=='PAID')throw Error(`Periksa payroll ${assigned.number} yang sudah disetujui sebelum mengubah potongannya.`)
    const quote=quoteIssueReturn(doc,quantities,issuePaid(doc))
    if(!quote.valid||!quote.lines.length||!dayOk(day)||day<doc.issuedOn||reason.trim().length<4||doc.lines.some(line=>line.sellingPrice===null)){
      throw Error('Periksa sisa qty, harga nota, tanggal fisik, dan alasan retur.')
    }
    const record:IssueReturn={id,day,reason:reason.trim(),lines:quote.lines,chargeReduction:quote.chargeReduction,credit:quote.credit}
    return documents.map(row=>row===doc?{...row,returns:[...(row.returns??[]),record],rowVersion:row.rowVersion+1}:row)
  })
}

export function issueReturnBlockers(doc:IssueDocument,entry:IssueReturn,documents=readNotes()):StockSourceLink[] {
  if(entry.reversal)return []
  const returns=activeIssueReturns(doc)
  const later=returns.slice(returns.indexOf(entry)+1)
  const payroll=readPayDrafts().filter(note=>note.status!=='REVERSED')
  const credit=payroll.filter(note=>note.accessoryCredits?.some(row=>row.id===entry.id))
  const charge=entry.chargeReduction>0&&payroll.find(note=>!editablePayroll(note)&&note.accessoryNotes.some(row=>row.number===doc.number))
  const book=masterBook()
  const items=new Map<string,number>()
  for(const line of entry.lines){
    const code=masterCode(line.lineId)
    items.set(code,(items.get(code)??0)+line.qty)
  }
  return [
    ...later.map(row=>({label:'Retur lanjutan '+row.id,href:issueReturnPath(doc.number,row.id)})),
    ...credit.map(note=>({label:'Kredit retur di '+note.number,href:'/keuangan/payroll-kasbon/?'+new URLSearchParams({nota:note.number})+'#kredit-retur-payroll'})),
    ...(charge?[{label:'Potongan nota di '+charge.number,href:'/keuangan/payroll-kasbon/?'+new URLSearchParams({nota:charge.number})}]:[]),
    ...[...items].flatMap(([code,qty])=>{
      const item=book.items.find(row=>row.code===code)
      return noteStock(code,item?.stock??0,documents)<qty?[{label:'Periksa stok dan pemakaian '+(item?.name??code),href:'/gudang/aksesori/?item='+encodeURIComponent(code)}]:[]
    }),
  ]
}

export function reverseIssueReturn(number:string,id:string,reason:string) {
  saveNotes(documents=>{
    const doc=documents.find(row=>row.number===number&&row.status==='POSTED')
    const entry=doc?.returns?.find(row=>row.id===id&&!row.reversal)
    if(!doc||!entry||reason.trim().length<4)throw Error('Pilih retur aktif dan isi alasan pembalikan.')
    if(issueReturnBlockers(doc,entry,documents).length)throw Error('Periksa stok dan selesaikan dokumen terkait.')
    const reversal={at:new Date().toISOString(),reason:reason.trim()}
    return documents.map(row=>row===doc?{
      ...row,rowVersion:row.rowVersion+1,returns:row.returns?.map(ret=>ret===entry?{...ret,reversal}:ret),
    }:row)
  })
}

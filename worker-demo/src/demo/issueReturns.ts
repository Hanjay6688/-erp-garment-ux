import { cash, documentTotal, outstandingIssue, saveNotes, type IssueDocument, type IssueReturn } from './issueDocuments'
import { editablePayroll, payrollClaim, readPayDrafts } from './payrollSources'
import { dayOk } from './warehouseDay'

export function issuePaid(doc:IssueDocument) {
  if(doc.settledAt)return documentTotal(doc)
  const payroll=readPayDrafts().find(row=>row.number===payrollClaim(doc.number))
  const throughPayroll=payroll?.status==='PAID'?(payroll.accessoryNotes.find(row=>row.number===doc.number)?.total??0):0
  return (doc.settledAmount??0)+throughPayroll
}

export function returnableIssueLines(doc:IssueDocument) {
  return doc.lines.map(line=>({...line,remaining:Math.max(0,line.qty-(doc.returns??[]).flatMap(row=>row.lines).reduce((sum,row)=>sum+(row.lineId===line.id?row.qty:0),0))}))
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

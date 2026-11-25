import {payrollNotes,type PayrollNote} from '../financeData'
import {activeIssueReturns,readNotes,lineTotal,outstandingIssue} from './issueDocuments'
import {normalizeMandor} from './accessoryPricing'
import {isPieceUnit} from '../browseMatch'
import type {DemoInvoice} from './saleBook'
import {dayOk} from './warehouseDay'

export type FgSource=PayrollNote['fgNotes'][number]
type AccSource=PayrollNote['accessoryNotes'][number]
export type Source={kind:'FG';mandor:string;day:string;doc:FgSource}|{kind:'ACCESSORY';mandor:string;day:string;doc:AccSource}
type SavedFg={mandor:string;day:string;doc:FgSource;cards:string[]}
type MandorDebt = { invoice: string; amount: number }
export type PayrollPayment = {id:string;amount:number;day:string;account:string;reference:string;reversed?:string}
type AccessoryReturnCredit={id:string;note:string;day:string;amount:number;mandor:string}
export type PayDraft=PayrollNote&{start?:string;end?:string;mandorDebts?:MandorDebt[];payments?:PayrollPayment[];accessoryCredits?:AccessoryReturnCredit[]}
export function fgSourcePieces(doc: FgSource) {
  const returned = doc.good + doc.bs
  return [doc.good, doc.bs, doc.stuck, returned, returned + doc.stuck]
}
export function accessorySourcePieces(doc: AccSource) {
  return (doc.lines?.length ? doc.lines : [doc]).filter(line => isPieceUnit(line.unit)).map(line => line.qty)
}
const ledgerKey='erp.owner.payroll.selections.1',fgKey='erp.owner.fg-posted.1'
const readFg=():SavedFg[]=>JSON.parse(sessionStorage.getItem(fgKey)??'[]')
export const postedPayrollCards=()=>readFg().flatMap(n=>n.cards)
export function postedRegularWork(cardId: string) {
  const note = readFg().find(n => n.cards.includes(cardId))
  const card = note?.doc.regularCards?.find(c => c.id === cardId)
  return note && card ? { number: note.doc.number, card } : undefined
}
export function savePostedFg(source:SavedFg){
  const old=readFg(),same=old.find(n=>n.cards.some(id=>source.cards.includes(id)))
  if(same){if(same.cards.length===source.cards.length&&same.cards.every(id=>source.cards.includes(id)))return same.doc.number;throw Error('Ada kartu yang sudah tercatat di nota FG.')}
  sessionStorage.setItem(fgKey,JSON.stringify([...old,source]));return source.doc.number
}
const seedFg:FgSource={number:'NFG-261123-012',date:'23 Nov 2026',source:'PO-1069 · Batch 02',sku:'Vivo 93001 · 31–33',status:'POSTED',good:48,bs:0,stuck:0,labor:720000,reimbursement:24000,note:'48 pcs selesai dijahit dan diterima GOOD.',regularCards:[{
  id:'QC-261123-012',source:'PO-1069 · Batch 02 · QC 23 Nov',sku:'Vivo 93001 · 31–33',
  qcQty:48,sewnQty:48,returnedQty:48,good:48,bs:0,rewash:0,hold:0,sewingRate:13500,commissionRate:1500,bomRate:500,
  bsComponents:[],stuckComponents:[],grossValue:744000,bsDeduction:0,stuckDeduction:0,subtotal:744000,
  sizeRows:[{size:'31',sewn:16,good:16,bs:0,hold:0,rewash:0},{size:'32',sewn:18,good:18,bs:0,hold:0,rewash:0},{size:'33',sewn:14,good:14,bs:0,hold:0,rewash:0}]
}]}
const seedSources:Source[]=[{kind:'FG',mandor:'Afui',day:'2026-11-23',doc:seedFg}]
function dayOf(text:string){return '2026-08-'+text.slice(0,2)}
export function allPayrollSources():Source[]{
  const catalog=new Map<string,Source>()
  for(const n of payrollNotes){
    for(const doc of n.fgNotes)catalog.set(doc.number,{kind:'FG',mandor:n.contractor,day:dayOf(doc.date),doc})
    for(const doc of n.accessoryNotes)catalog.set(doc.number,{kind:'ACCESSORY',mandor:n.contractor,day:dayOf(doc.date),doc})
  }
  for(const s of seedSources)catalog.set(s.doc.number,s)
  for(const row of readFg())catalog.set(row.doc.number,{kind:'FG',...row})
  for(const n of readNotes()){
    if(n.status!=='POSTED'||n.settledAt||n.lines.some(l=>lineTotal(l)===null)){catalog.delete(n.number);continue}
    const lines=n.lines.map(l=>({item:l.item,qty:l.qty,unit:l.unit,price:l.sellingPrice!,total:lineTotal(l)!}))
    const total=outstandingIssue(n),single=lines.length===1
    if(total<=0){catalog.delete(n.number);continue}
    catalog.set(n.number,{kind:'ACCESSORY',mandor:n.mandor,day:n.issuedOn,doc:{number:n.number,date:n.issuedAt,source:n.productionBatch||n.location,item:lines.map(l=>l.item).join(' · '),qty:single?lines[0].qty:lines.length,unit:single?lines[0].unit:'baris',unitPrice:single?lines[0].price:0,total,returnDeduction:lines.reduce((sum,row)=>sum+row.total,0)-total,lines}})
  }
  return [...catalog.values()]
}
const matchMandor=(a:string,b:string)=>normalizeMandor(a).toLocaleLowerCase()===normalizeMandor(b).toLocaleLowerCase()
export function newPayDraft(mandor:string,start:string,end:string):PayDraft{
  if(!mandor.trim()||!start||!end||end<start)throw Error('Pilih mandor dan periode yang urut.')
  return {number:'PAY-'+mandor.replace(/^Mandor /i,'').toUpperCase()+'-'+start+'-'+end,contractor:mandor,period:start+' – '+end,start,end,status:'DRAFT',workQty:0,labor:0,attendance:0,reimbursement:0,deduction:0,netPayable:0,eligibleLines:0,paymentDate:end,fgNotes:[],accessoryNotes:[],deductions:[]}
}
export function payrollPeriod(n: PayDraft) {
  if(n.start&&n.end)return {start:n.start,end:n.end}
  const parsed=n.period.match(/^(\d{1,2})[–-](\d{1,2}) (\S+) (\d{4})$/)
  if(!parsed) return {start:'',end:''}
  const month=['jan','feb','mar','apr','mei','jun','jul','agu','sep','okt','nov','des'].indexOf(parsed[3].toLowerCase())+1
  if(!month)return {start:'',end:''}
  const prefix=parsed[4]+'-'+String(month).padStart(2,'0')+'-'
  return {start:prefix+parsed[1].padStart(2,'0'),end:prefix+parsed[2].padStart(2,'0')}
}
const cutoff=(n:PayDraft)=>payrollPeriod(n).end
export const editablePayroll=(n:PayDraft)=>['DRAFT','CALCULATED','REVIEW'].includes(n.status)
export const payrollDebtTotal = (note: PayDraft) => (note.mandorDebts ?? []).reduce((sum, debt) => sum + debt.amount, 0)
export const payrollAccessoryCreditTotal = (note:PayDraft) => (note.accessoryCredits??[]).reduce((sum,row)=>sum+row.amount,0)
export function accessoryCreditsForPayroll(notes:PayDraft[],note:PayDraft) {
  return readNotes().filter(doc=>doc.status==='POSTED'&&matchMandor(doc.mandor,note.contractor)).flatMap(doc=>
    activeIssueReturns(doc).filter(row=>row.credit>0&&row.day<=cutoff(note)).map(row=>({id:row.id,note:doc.number,day:row.day,amount:row.credit,mandor:doc.mandor}))
  ).filter(credit=>!notes.some(row=>row.number!==note.number&&row.status!=='REVERSED'&&row.accessoryCredits?.some(item=>item.id===credit.id)))
}
export function chooseAccessoryCredit(notes:PayDraft[],number:string,id:string,include:boolean) {
  const note=notes.find(row=>row.number===number)
  if(!note||!editablePayroll(note))throw Error('Payroll periode ini sudah dikunci.')
  const credit=accessoryCreditsForPayroll(notes,note).find(row=>row.id===id)
  if(include&&!credit)throw Error('Kredit tidak tersedia untuk periode ini.')
  const accessoryCredits=(note.accessoryCredits??[]).filter(row=>row.id!==id)
  if(include&&credit)accessoryCredits.push(credit)
  const updated=totalPay({...note,status:'DRAFT',accessoryCredits})
  if(payrollDebtTotal(note)>0&&updated.netPayable<0)throw Error('Kurangi potongan piutang mandor sebelum melepaskan kredit ini.')
  return notes.map(row=>row===note?updated:row)
}

export function mandorDebtBalance(invoice: DemoInvoice, notes: PayDraft[]) {
  let settled = 0
  let reserved = 0
  for (const note of notes) {
    if (note.status === 'REVERSED') continue
    const amount = note.mandorDebts?.find(debt => debt.invoice === invoice.number)?.amount ?? 0
    if (note.status === 'PAID') settled += amount
    else reserved += amount
  }
  const outstanding = Math.max(0, invoice.gross - invoice.returns - invoice.paid - settled)
  return { settled, reserved, outstanding, available: Math.max(0, outstanding - reserved) }
}

const canUseMandorInvoice = (invoice: DemoInvoice, note: PayDraft) =>
  invoice.buyerKind === 'MANDOR' && invoice.status === 'POSTED' && matchMandor(invoice.customer, note.contractor) && invoice.dateKey <= cutoff(note)

export function mandorBillsForPayroll(invoices: DemoInvoice[], notes: PayDraft[], note: PayDraft) {
  return invoices.filter(invoice => canUseMandorInvoice(invoice, note)).map(invoice => {
    const balance = mandorDebtBalance(invoice, notes)
    const allocated = note.mandorDebts?.find(debt => debt.invoice === invoice.number)?.amount ?? 0
    const editableAmount = editablePayroll(note) ? allocated : 0
    const maximum = Math.max(0, Math.min(balance.available, Math.floor(note.netPayable)) + editableAmount)
    return { invoice, ...balance, allocated, maximum }
  }).filter(bill => bill.outstanding > 0 || bill.allocated > 0)
    .sort((left, right) => right.invoice.dateKey.localeCompare(left.invoice.dateKey) || left.invoice.number.localeCompare(right.invoice.number))
}

export function validMandorDebts(invoices: DemoInvoice[], notes: PayDraft[], note: PayDraft) {
  if (!note.mandorDebts?.length) return true
  return note.netPayable >= 0 && note.mandorDebts.every(debt => {
    const invoice = invoices.find(row => row.number === debt.invoice)
    if (!invoice || !Number.isSafeInteger(debt.amount) || debt.amount <= 0 || !canUseMandorInvoice(invoice, note)) return false
    const balance = mandorDebtBalance(invoice, notes)
    return balance.reserved <= balance.outstanding
  })
}

export const payrollPaid = (note:PayDraft) => note.status==='PAID'&&!note.payments
  ? note.netPayable : (note.payments??[]).reduce((sum,row)=>sum+(row.reversed?0:Math.round(row.amount*100)),0)/100
export const payrollRemaining = (note:PayDraft) => Math.max(0,Math.round((note.netPayable-payrollPaid(note))*100)/100)

export function postPayrollPayment(notes:PayDraft[], invoices:DemoInvoice[], number:string, payment:PayrollPayment):PayDraft[] {
  const note=notes.find(row=>row.number===number)
  if(!note)throw Error('Payroll tidak ditemukan.')
  const duplicate=note.payments?.find(row=>row.id===payment.id)
  if(duplicate){if(JSON.stringify(duplicate)!==JSON.stringify(payment))throw Error('Pembayaran sudah tercatat.');return notes}
  const remaining=payrollRemaining(note)
  if(note.status!=='APPROVED'||!validMandorDebts(invoices,notes,note)||!dayOk(payment.day)||!payment.account||!payment.reference.trim()
    || !Number.isSafeInteger(Math.round(payment.amount*100))||payment.amount!==Math.round(payment.amount*100)/100
    ||payment.amount<0||payment.amount>remaining||payment.amount===0&&remaining>0) {
    throw Error('Periksa status payroll, tanggal, dan nominal sisa pembayaran.')
  }
  const status=payment.amount===remaining?'PAID':'APPROVED'
  return notes.map(row=>row===note?{...row,status,payments:[...(row.payments??[]),payment]}:row)
}

export function reversePayrollPayment(notes:PayDraft[],number:string,id:string|null,reason:string):PayDraft[] {
  const note=notes.find(row=>row.number===number)
  if(!note||!reason.trim())throw Error('Pilih pembayaran dan isi alasan pembalikan.')
  if(note.status==='PAID'&&readNotes().some(doc=>!doc.settledAt&&note.accessoryNotes.some(row=>row.number===doc.number)&&activeIssueReturns(doc).some(row=>row.credit>0))){
    throw Error('Nota biaya aksesori sudah menghasilkan kredit retur. Periksa kredit itu sebelum membalik pembayaran payroll ini.')
  }
  if(!id&&note.status==='PAID'&&!note.payments) {
    return notes.map(row=>row===note?{...row,status:'APPROVED'}:row)
  }
  const payment=note.payments?.find(row=>row.id===id&&!row.reversed)
  if(!payment)throw Error('Pembayaran ini sudah dibalik atau tidak ditemukan.')
  return notes.map(row=>row===note?{...row,status:'APPROVED',payments:row.payments?.map(current=>current===payment?{...current,reversed:reason.trim()}:current)}:row)
}

export function chooseMandorDebt(invoices: DemoInvoice[], notes: PayDraft[], payrollNumber: string, invoiceNumber: string, amount: number) {
  const note = notes.find(row => row.number === payrollNumber)
  if (!note || !editablePayroll(note)) throw Error('Payroll sudah dikunci.')
  if (!Number.isSafeInteger(amount) || amount < 0) throw Error('Isi nominal potongan yang sah.')
  if (amount > 0) {
    const bill = mandorBillsForPayroll(invoices, notes, note).find(row => row.invoice.number === invoiceNumber)
    if (!bill || amount > bill.maximum) throw Error('Potongan melebihi saldo bebas tagihan atau upah bersih.')
  }
  const mandorDebts = (note.mandorDebts ?? []).filter(debt => debt.invoice !== invoiceNumber)
  if (amount > 0) mandorDebts.push({ invoice: invoiceNumber, amount })
  return notes.map(row => row === note ? totalPay({ ...row, mandorDebts, status: 'DRAFT' }) : row)
}
export const availableSources=(notes:PayDraft[],n:PayDraft)=>allPayrollSources().filter(s=>matchMandor(s.mandor,n.contractor)&&s.day<=cutoff(n)&&!notes.some(pay=>pay.status!=='REVERSED'&&[...pay.fgNotes,...pay.accessoryNotes].some(doc=>doc.number===s.doc.number)))
function totalPay(n:PayDraft):PayDraft{
  const sum=(xs:number[])=>Math.round(xs.reduce((a,b)=>a+b,0)*100)/100
  const labor=sum(n.fgNotes.map(d=>d.labor)),reimbursement=sum(n.fgNotes.map(d=>d.reimbursement)),deduction=sum([...n.accessoryNotes.map(d=>d.total),...n.deductions.map(d=>d.amount),payrollDebtTotal(n)])
  return {...n,labor,reimbursement,deduction,workQty:n.fgNotes.reduce((qty,doc)=>qty+doc.good+doc.bs+doc.stuck,0),netPayable:sum([labor,reimbursement,n.attendance,payrollAccessoryCreditTotal(n),-deduction])}
}
export function readPayDrafts():PayDraft[]{
  const catalog=allPayrollSources()
  const read=sessionStorage.getItem(ledgerKey)
  const notes:PayDraft[]=read?JSON.parse(read):[newPayDraft('Mandor Afui','2026-11-23','2026-11-29'),...payrollNotes]
  return notes.map(note=>editablePayroll(note)?totalPay({...note,accessoryNotes:note.accessoryNotes.flatMap(old=>{
    const source=catalog.find(row=>row.doc.number===old.number);return source?.kind==='ACCESSORY'?[source.doc]:[]
  })}):note)
}
export const savePayDrafts=(notes:PayDraft[])=>{sessionStorage.setItem(ledgerKey,JSON.stringify(notes));return notes}
export const payrollClaim=(id:string)=>readPayDrafts().find(n=>n.status!=='REVERSED'&&n.accessoryNotes.some(a=>a.number===id))?.number
export function choosePayrollSource(notes:PayDraft[],payId:string,number:string,add:boolean):PayDraft[]{
  const n=notes.find(n=>n.number===payId)
  if(!n||!editablePayroll(n))throw Error('Komposisi payroll ini sudah terkunci.')
  let {fgNotes,accessoryNotes}=n
  if(add){const s=availableSources(notes,n).find(s=>s.doc.number===number);if(!s)throw Error('Nota sudah terpakai atau belum layak dibayar untuk mandor dan periode ini.')
    if(s.kind==='FG')fgNotes=[...fgNotes,s.doc];else accessoryNotes=[...accessoryNotes,s.doc]
  }else{fgNotes=fgNotes.filter(d=>d.number!==number);accessoryNotes=accessoryNotes.filter(d=>d.number!==number)}
  const next = totalPay({ ...n, fgNotes, accessoryNotes, status: 'DRAFT' })
  if (payrollDebtTotal(n) > 0 && next.netPayable < 0) throw Error('Lepas potongan piutang sebelum mengurangi sumber payroll ini.')
  return notes.map(doc=>doc.number===payId?next:doc)
}
export function payForSource(number:string,preferredId:string|null,include:boolean){
  const source=allPayrollSources().find(s=>s.doc.number===number)
  if(!source)throw Error('Nota posted belum tersedia untuk pembayaran.')
  let notes=readPayDrafts()
  const used=notes.find(n=>n.status!=='REVERSED'&&[...n.fgNotes,...n.accessoryNotes].some(d=>d.number===number))
  const eligible=(n:PayDraft)=>editablePayroll(n)&&matchMandor(n.contractor,source.mandor)&&source.day<=cutoff(n)
  let target=used??notes.find(n=>n.number===preferredId&&eligible(n))??notes.find(eligible)
  if(!target){
    const start=new Date(source.day+'T12:00:00Z');start.setUTCDate(start.getUTCDate()-(start.getUTCDay()+6)%7);const end=new Date(start);end.setUTCDate(start.getUTCDate()+6)
    const name='Mandor '+normalizeMandor(source.mandor)
    target=newPayDraft(name,start.toISOString().slice(0,10),end.toISOString().slice(0,10))
    if(notes.some(n=>n.number===target!.number))throw Error('Periode sudah dikunci. Buat draft periode berikut untuk mandor ini.')
    notes=[target,...notes]
  }
  if(include&&!used)notes=choosePayrollSource(notes,target.number,number,true)
  savePayDrafts(notes);sessionStorage.setItem('erp.owner.payroll.focus',target.number)
  return target.number
}

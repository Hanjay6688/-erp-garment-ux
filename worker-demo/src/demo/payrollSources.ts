import {payrollNotes,type PayrollNote} from '../financeData'
import {readNotes,lineTotal} from './issueDocuments'
import {normalizeMandor} from './accessoryPricing'

export type FgSource=PayrollNote['fgNotes'][number]
type AccSource=PayrollNote['accessoryNotes'][number]
export type Source={kind:'FG';mandor:string;day:string;doc:FgSource}|{kind:'ACCESSORY';mandor:string;day:string;doc:AccSource}
type SavedFg={mandor:string;day:string;doc:FgSource;cards:string[]}
export type PayDraft=PayrollNote&{start?:string;end?:string}
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
    const total=lines.reduce((sum,l)=>sum+l.total,0),single=lines.length===1
    if(total<=0){catalog.delete(n.number);continue}
    catalog.set(n.number,{kind:'ACCESSORY',mandor:n.mandor,day:n.issuedOn,doc:{number:n.number,date:n.issuedAt,source:n.productionBatch||n.location,item:lines.map(l=>l.item).join(' · '),qty:single?lines[0].qty:lines.length,unit:single?lines[0].unit:'baris',unitPrice:single?lines[0].price:0,total,lines}})
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
export const availableSources=(notes:PayDraft[],n:PayDraft)=>allPayrollSources().filter(s=>matchMandor(s.mandor,n.contractor)&&s.day<=cutoff(n)&&!notes.some(pay=>pay.status!=='REVERSED'&&[...pay.fgNotes,...pay.accessoryNotes].some(doc=>doc.number===s.doc.number)))
function totalPay(n:PayDraft):PayDraft{
  const sum=(xs:number[])=>Math.round(xs.reduce((a,b)=>a+b,0)*100)/100
  const labor=sum(n.fgNotes.map(d=>d.labor)),reimbursement=sum(n.fgNotes.map(d=>d.reimbursement)),deduction=sum([...n.accessoryNotes.map(d=>d.total),...n.deductions.map(d=>d.amount)])
  return {...n,labor,reimbursement,deduction,workQty:n.fgNotes.reduce((qty,doc)=>qty+doc.good+doc.bs+doc.stuck,0),netPayable:sum([labor,reimbursement,n.attendance,-deduction])}
}
export function readPayDrafts():PayDraft[]{
  const raw=sessionStorage.getItem(ledgerKey);if(raw)return JSON.parse(raw)
  const catalog=allPayrollSources()
  return [newPayDraft('Mandor Afui','2026-11-23','2026-11-29'),...payrollNotes.map(n=>editablePayroll(n)?totalPay({...n,accessoryNotes:n.accessoryNotes.flatMap(old=>{const s=catalog.find(s=>s.doc.number===old.number);return s?.kind==='ACCESSORY'?[s.doc]:[]})}):n)]
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
  return notes.map(doc=>doc.number===payId?totalPay({...n,fgNotes,accessoryNotes,status:'DRAFT'}):doc)
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

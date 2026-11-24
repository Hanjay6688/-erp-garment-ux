import {readPlannerSession} from './planner/session'
import {positionDelta} from './skuCatalog'
import {productCatalog,type Product} from '../productCatalog'
export type DraftLine={key:string;product:Product;quantities:number[];priceDozen:number}
export const allInvoices = [
  { number:'INV-JUAL-0245', customer:'Nusantara Fashion', dateKey:'2026-08-28', day:'28 Agu 2026', time:'10:30', sku:'73001 · 73005', qty:72, gross:6_660_000, returns:0, paid:0, status:'DRAFT' },
  { number:'INV-JUAL-0244', customer:'Toko Maju Jaya', dateKey:'2026-08-28', day:'28 Agu 2026', time:'09:15', sku:'73003', qty:64, gross:5_760_000, returns:0, paid:0, status:'DRAFT' },
  { number:'INV-JUAL-0243', customer:'Sentra Denim', dateKey:'2026-08-28', day:'28 Agu 2026', time:'08:40', sku:'73005', qty:36, gross:3_420_000, returns:0, paid:3_420_000, status:'PAID' },
  { number:'INV-JUAL-0241', customer:'Toko Maju Jaya', dateKey:'2026-08-27', day:'27 Agu 2026', time:'16:24', sku:'73001 · 73002', qty:84, gross:7_830_000, returns:180_000, paid:4_820_000, status:'POSTED' },
  { number:'INV-JUAL-0240', customer:'Nusantara Fashion', dateKey:'2026-08-27', day:'27 Agu 2026', time:'15:18', sku:'73001 · 73005', qty:144, gross:13_320_000, returns:0, paid:8_000_000, status:'POSTED' },
  { number:'INV-JUAL-0239', customer:'Sentra Denim', dateKey:'2026-08-27', day:'27 Agu 2026', time:'11:06', sku:'73003 · 73004', qty:60, gross:5_730_000, returns:0, paid:0, status:'POSTED' },
  { number:'INV-JUAL-0238', customer:'Nusantara Fashion', dateKey:'2026-08-26', day:'26 Agu 2026', time:'14:52', sku:'73002', qty:96, gross:8_640_000, returns:360_000, paid:8_280_000, status:'PAID' },
  { number:'INV-JUAL-0237', customer:'Nusantara Fashion', dateKey:'2026-08-25', day:'25 Agu 2026', time:'13:18', sku:'73001 · 73004', qty:132, gross:12_640_000, returns:860_000, paid:8_000_000, status:'POSTED' },
  { number:'INV-JUAL-0236', customer:'Toko Maju Jaya', dateKey:'2026-08-25', day:'25 Agu 2026', time:'10:42', sku:'73005', qty:48, gross:4_560_000, returns:0, paid:4_560_000, status:'PAID' },
  { number:'INV-JUAL-0231', customer:'Sentra Denim', dateKey:'2026-08-18', day:'18 Agu 2026',time:'09:08',sku:'73003',qty:48,gross:4_320_000,returns:0,paid:4_320_000,status:'PAID' },
  { number:'INV-JUAL-0207', customer:'Toko Maju Jaya', dateKey:'2026-07-31', day:'31 Jul 2026',time:'16:47',sku:'73001',qty:36,gross:3_240_000,returns:0,paid:3_240_000,status:'PAID' },
]


export type DemoInvoice=typeof allInvoices[number]&{lines?:DraftLine[];terms?:string;due?:string;location?:string;changeReason?:string;notes?:string;corrects?:string}
const invoiceKey='erp.owner.invoice-register.v2'
type SaleMove={id:string;recordedAt?:string;ref:string;day:string;when:string;type:string;note:string;key:string;delta:number[];balance:number[]}
type Journal={docs:DemoInvoice[];moves:SaleMove[]}
function journal():Journal{const raw=typeof sessionStorage==='undefined'?null:sessionStorage.getItem(invoiceKey);if(!raw)return {docs:allInvoices,moves:[]};const saved=JSON.parse(raw);return Array.isArray(saved)?{docs:saved,moves:[]}:saved}
export const readInvoices=()=>journal().docs
export const saleMoves=(key:string)=>journal().moves.filter(m=>m.key===key)
export function writeInvoices(docs:DemoInvoice[]){
  const before=journal(),moves=[...before.moves]
  const old=new Map(before.docs.map(d=>[d.number,d])),next=new Map(docs.map(d=>[d.number,d]))
  const changed=[...new Set([...old.keys(),...next.keys()])].filter(id=>JSON.stringify(old.get(id))!==JSON.stringify(next.get(id)))
  const interim=[...before.docs]
  for(const id of changed){
    const prior=old.get(id),after=next.get(id),d=after??prior!
    const index=interim.findIndex(x=>x.number===id)
    if(index>=0)interim.splice(index,1);if(after)interim.push(after)
    for(const p of productCatalog){
      const previous=prior&&counts(prior)?quantities(prior,p):p.sizes.map(()=>0)
      const current=after&&counts(after)?quantities(after,p):p.sizes.map(()=>0)
      const delta=previous.map((n,i)=>n-current[i]);if(!delta.some(n=>n!==0))continue
      moves.push({id:crypto.randomUUID(),recordedAt:new Date().toISOString(),ref:id,day:d.dateKey,when:d.day+' · '+d.time,type:!after||after.status==='REVERSED'?'Pelepasan reserve':prior?'Perubahan reserve':'Reserve penjualan',note:d.customer,key:p.brand+'::'+p.code,delta,balance:saleStock(p,interim)})
    }
  }
  sessionStorage.setItem(invoiceKey,JSON.stringify({docs,moves}));return docs
}
const chron=(a:DemoInvoice,b:DemoInvoice)=>a.dateKey.localeCompare(b.dateKey)||a.time.localeCompare(b.time)||a.number.localeCompare(b.number)
export const compareInvoices=(sort:string)=>(a:DemoInvoice,b:DemoInvoice)=>sort==='OLDEST'?chron(a,b):sort==='VALUE_DESC'?b.gross-a.gross||chron(b,a):sort==='VALUE_ASC'?a.gross-b.gross||chron(b,a):sort==='STORE'?a.customer.localeCompare(b.customer)||chron(b,a):chron(b,a)
const firstLine:Record<string,[number,number]>={'INV-JUAL-0245':[36,3240000],'INV-JUAL-0241':[48,4320000],'INV-JUAL-0240':[72,6480000],'INV-JUAL-0239':[36,3240000],'INV-JUAL-0237':[60,5400000]}
export function invoiceLines(invoice:DemoInvoice){
  if(invoice.lines)return invoice.lines.map(l=>({sku:l.product.brand+' '+l.product.code,qty:l.quantities.reduce((a,b)=>a+b,0),amount:Math.round(l.quantities.reduce((a,b)=>a+b,0)*l.priceDozen/12)}))
  const codes=invoice.sku.split(' · '),split=firstLine[invoice.number]
  if(!split)return [{sku:invoice.sku,qty:invoice.qty,amount:invoice.gross}]
  return [{sku:codes[0],qty:split[0],amount:split[1]},{sku:codes[1],qty:invoice.qty-split[0],amount:invoice.gross-split[1]}]
}



export function sourceLines(doc:DemoInvoice):DraftLine[]{
  if(doc.lines)return structuredClone(doc.lines)
  return invoiceLines(doc).map(r=>{
    const p=productCatalog.find(p=>p.code===r.sku)!
    const qty=p.sizes.map((_,i)=>Math.floor(r.qty/p.sizes.length)+(i<r.qty%p.sizes.length?1:0))
    return {key:p.brand+'::'+p.code,product:p,quantities:qty,priceDozen:r.amount*12/r.qty}
  })
}
const counts=(doc:DemoInvoice)=>!['REVERSED','CANCELLED'].includes(doc.status)
function quantities(doc:DemoInvoice,p:Product){const line=sourceLines(doc).find(l=>l.product.brand===p.brand&&l.product.code===p.code&&l.product.location===p.location);return line?.quantities??p.sizes.map(()=>0)}
export function baseSaleStock(p:Product,docs:DemoInvoice[],editing?:string){
  const balance=[...p.stocks]
  for(const d of allInvoices)if(counts(d))quantities(d,p).forEach((q,i)=>balance[i]+=q)
  for(const d of docs)if(d.number!==editing&&counts(d))quantities(d,p).forEach((q,i)=>balance[i]-=q)
  return balance
}
export function postInvoice(id:string){
  const rows=readInvoices(),draft=rows.find(d=>d.number===id)
  if(!draft||draft.status!=='DRAFT')throw Error('Dokumen ini sudah ditutup.')
  const original=draft.corrects?rows.find(d=>d.number===draft.corrects):null
  if(draft.corrects&&(!original||original.status!=='POSTED'||original.paid||original.returns))throw Error('Periksa pembayaran, retur dan status invoice asal.')
  return writeInvoices(rows.map(d=>d.number===id?{...d,status:'POSTED'}:original&&d.number===original.number?{...d,status:'REVERSED'}:d))
}

export function saleStock(p:Product,docs:DemoInvoice[],editing?:string){
  const session=readPlannerSession()
  return baseSaleStock(p,docs,editing).map((q,i)=>q+positionDelta(session,p.brand+' '+p.code,p.sizes[i],p.location,p.grade))
}

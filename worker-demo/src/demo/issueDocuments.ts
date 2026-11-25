import {amountText,contractorNames,noteStorage,type PricingMode} from './accessoryPricing'
import type { ReceiptReversal } from './receiptRollCorrection'
type IssueStatus = 'DRAFT' | 'POSTED' | 'REVERSED'
export type IssueLine = {
  id: string
  item: string
  category: string
  qty: number
  unit: string
  stock: number
  averageCost: number
  sellingPrice: number|null
  mode?:PricingMode;manual?:string;reimbursement?:number|null;source?:string;version?:string
}
export type IssueReturn = {id:string;day:string;reason:string;lines:{lineId:string;qty:number;amount:number}[];chargeReduction:number;credit:number;reversal?:ReceiptReversal}
export type IssueDocument = {
  number: string
  mandor: string
  productionBatch: string
  distributionBatch: string
  location: string
  issuedOn: string
  issuedAt: string
  status: IssueStatus
  settledAt?: string
  settledAmount?:number
  returns?:IssueReturn[]
  rowVersion: number
  note: string
  reason?:string;inventoryChange?:number
  lines: IssueLine[]
}

export const legacyCatalog: IssueLine[] = [
  { id:'ACC-BTN-017', item:'Kancing Jeans 17 mm · Silver', category:'Kancing', qty:0, unit:'pcs', stock:4800, averageCost:620, sellingPrice:750 },
  { id:'ACC-ZIP-014', item:'Resleting 14 cm · Black', category:'Resleting', qty:0, unit:'pcs', stock:2200, averageCost:5200, sellingPrice:6500 },
  { id:'ACC-RVT-011', item:'Rivet Copper', category:'Rivet', qty:0, unit:'pcs', stock:3600, averageCost:780, sellingPrice:900 },
  { id:'ACC-LBL-004', item:'Label Woven Vivo', category:'Label', qty:0, unit:'pcs', stock:8000, averageCost:530, sellingPrice:750 },
]

export const seedDocuments: IssueDocument[] = [

  { number:'NAA-260827-021', mandor:'Mandor Budi', productionBatch:'POT-260827-042', distributionBatch:'042-03', location:'Gudang Aksesori Utama', issuedOn:'2026-08-27', issuedAt:'27 Agu 2026 · 10:06', status:'DRAFT', rowVersion:2, note:'Persiapan jahit batch hitam.', lines:[{...legacyCatalog[1],qty:72},{...legacyCatalog[3],qty:240}] },
  { number:'NAA-260826-018', mandor:'Mandor Budi', productionBatch:'POT-260826-041', distributionBatch:'041-01', location:'Gudang Aksesori Utama', issuedOn:'2026-08-26', issuedAt:'26 Agu 2026 · 14:22', status:'POSTED', rowVersion:4, note:'Kebutuhan aktual batch distribusi pertama.', lines:[{...legacyCatalog[0],qty:480},{...legacyCatalog[2],qty:480}] },
  { number:'NAA-260824-019', mandor:'Mandor Rian', productionBatch:'POT-260824-039', distributionBatch:'039-02', location:'Gudang Aksesori Utama', issuedOn:'2026-08-24', issuedAt:'24 Agu 2026 · 08:44', status:'REVERSED', rowVersion:6, note:'Batch distribusi dibatalkan sebelum jahit.', lines:[{...legacyCatalog[3],qty:500}] },
  { number:'NAA-260814-009', mandor:'Mandor Dedi', productionBatch:'POT-260815-026', distributionBatch:'026-01', location:'Gudang Aksesori Utama', issuedOn:'2026-08-14', issuedAt:'14 Agu 2026 · 10:08', status:'POSTED', settledAt:'27 Agu 2026 · PAY-MANDOR-0086', rowVersion:7, note:'Sudah diselesaikan pada payroll.', lines:[{...legacyCatalog[0],qty:800,sellingPrice:800}] },
  {number:'NAA-261123-006',mandor:'Mandor Afui',productionBatch:'PO-1069',distributionBatch:'02',location:'Gudang Aksesori Utama',issuedOn:'2026-11-23',issuedAt:'23 Nov 2026 · 09:30',status:'POSTED',rowVersion:1,note:'Saldo awal latihan. Kancing untuk jahit.',lines:[{...legacyCatalog[0],item:'Kancing Jeans 17 mm · Metal',id:'ACC-BTN-MET',qty:20,sellingPrice:450,averageCost:690}]},
]

export const mandorNames = [...contractorNames.map(n=>'Mandor '+n),'Mandor Budi','Mandor Dedi','Mandor Rian']
export const money=(v:number)=>amountText(v)
export const cash=(n:number)=>Math.round((n+Number.EPSILON)*100)/100
export const lineTotal=(l:IssueLine)=>l.sellingPrice===null?null:cash(l.qty*l.sellingPrice)
export const documentTotal=(d:IssueDocument)=>d.lines.reduce((n,l)=>n+(lineTotal(l)??0),0)
export const activeIssueReturns=(d:IssueDocument)=>(d.returns??[]).filter(row=>!row.reversal)
export const outstandingIssue=(d:IssueDocument,paid=d.settledAmount??(d.settledAt?documentTotal(d):0))=>Math.max(0,cash(documentTotal(d)-paid-activeIssueReturns(d).reduce((sum,row)=>sum+row.chargeReduction,0)))
export const amountDue=(d:IssueDocument)=>!d.lines.length?'Belum ada baris':d.lines.some(l=>lineTotal(l)===null)?'Belum dihitung':money(documentTotal(d))
const key=noteStorage
let cached:{raw:string|null;docs:IssueDocument[]}|undefined
export function readNotes(){const raw=sessionStorage.getItem(key);if(cached&&raw===cached.raw)return cached.docs;const docs:IssueDocument[]=raw?JSON.parse(raw):seedDocuments;cached={raw,docs};return docs}
export const subscribe=(f:()=>void)=>{window.addEventListener(key,f);return()=>window.removeEventListener(key,f)}
export const saveNotes=(change:(d:IssueDocument[])=>IssueDocument[])=>{const d=change(readNotes());sessionStorage.setItem(key,JSON.stringify(d));cached=undefined;window.dispatchEvent(new Event(key))}

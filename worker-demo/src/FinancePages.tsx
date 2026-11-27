import NumberEntry from '../../src/components/NumberEntry'
import { BrowsePane } from './components/BrowsePane'
import { WorkspaceFigures } from './components/WorkspaceFigures'
import {browseMatchPieces} from './browseMatch'
import {PeriodFilter,periodFor,periodLabel} from './demo/PeriodFilter'
import {fgQuantity} from './fgQuantity'
import {fgDrafts} from './demo/fgDraft'
import {mandorNames,readNotes as readIssueSources} from './demo/issueDocuments'
import {accessoryCreditsForPayroll,chooseAccessoryCredit,payrollAccessoryCreditTotal,accessorySourcePieces,availableSources,allPayrollSources,chooseMandorDebt,choosePayrollSource,editablePayroll,fgSourcePieces,mandorBillsForPayroll,mandorDebtBalance,newPayDraft,payrollDebtTotal,readPayDrafts,savePayDrafts,payrollPeriod,payrollPaid,payrollRemaining,postPayrollPayment,reversePayrollPayment,validMandorDebts,type PayDraft} from './demo/payrollSources'
import {fixtureDate,normalizeMandor} from './demo/accessoryPricing'
import {readInvoices} from './demo/saleBook'
import {ReasonDialog} from './demo/planner/ReasonDialog'
import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Banknote, CalendarClock, CalendarDays, Check,
  CheckCircle2, CircleDollarSign, Clock3, FileClock, FileSearch, Landmark,
  FilePlus2, Layers3, LockKeyhole, NotebookTabs, Package, ReceiptText, RefreshCcw, Search, ShieldAlert, Waves,
  ShieldCheck, TrendingDown, TrendingUp, Undo2, UsersRound, WalletCards, X,
} from 'lucide-react'
import {
  cashAccounts, cashMovements, closeChecks, journals, payables, payrollNotes,
  receivables,
} from './financeData'
import type { CashMovement, JournalEntry, Payable, PayrollNote, Receivable } from './financeData'
import EnterpriseSelect from './EnterpriseSelect'
import { SupplierTransferPanel } from './demo/SupplierTransferPanel'
import { readSupplierTransfers, reverseSupplierInvoice, supplierInvoicePayments, transferPayables, transferTotal } from './demo/supplierTransfers'
import { readPlannerSession } from './demo/planner/session'
import { readSaleReturns } from './demo/saleReturnJournal'
import { SupplierInvoiceComposer } from './demo/SupplierInvoiceComposer'
import { payablePartnerNames } from './demo/payablePartners'
import { kasbonSources, readSupplierInvoices, supplierDateLabel, supplierInvoiceAmount, supplierSourceRemaining, type SupplierInvoice } from './demo/supplierInvoices'
import { availableCredits, billCredit, billGross, billPaid, billRemaining, vendorCreditApplied } from './demo/laundryCredits'
import { isLaundryInvoice, laundryContractKey, type LaundryDelivery, type LaundryFinalBill } from './demo/laundryModel'
import { LaundryInvoiceActions } from './demo/LaundryCreditActions'
import { LaundryVendorInvoiceComposer } from './demo/LaundryInvoiceComposer'
import { invoiceForLaundryContract, laundryContracts, laundryContractsPath, laundryDocuments, laundryInvoiceBlockers, laundryPayablesPath, reverseLaundryInvoice } from './demo/laundryVendorInvoices'
import type { UpdateLaundry } from './demo/LaundryClaimCreditDialog'
import { StockSourceReversal } from './demo/StockSourceReversal'
import { receiptDocumentPath } from './demo/receiptRollCorrection'
import { amountText } from './demo/accessoryPricing'
import { cleanMoneyInput, readRupiahInput } from './moneyInput'
import { dayOk, lastWarehouseDay } from './demo/warehouseDay'
import { calculateRegularWorkEntitlement } from './payroll/regularWorkEntitlement'
import './business-pages.css'

export type FinanceView = 'finance-overview' | 'finance-cash' | 'finance-ap' | 'finance-ar' | 'finance-payroll' | 'finance-journal' | 'finance-reports'
type FinanceProps = { view: FinanceView; onNavigate: (view: FinanceView) => void; onSalesPayment: () => void; onAttendance: () => void; onOpenFg?:()=>void; laundry: LaundryDelivery[]; updateLaundry: UpdateLaundry }
type Tone = 'good' | 'warn' | 'danger' | 'neutral'
type PayrollSourceSelection = { kind:'FG' | 'ACCESSORY'; number:string } | null

const money = (value:number)=>new Intl.NumberFormat('id-ID',{style:'currency',currency:'IDR',maximumFractionDigits:0}).format(value)
const compactMoney = (value:number)=>{
  const absolute=Math.abs(value);const sign=value<0?'−':''
  if(absolute>=1_000_000_000)return `${sign}Rp${(absolute/1_000_000_000).toLocaleString('id-ID',{maximumFractionDigits:1})} M`
  if(absolute>=1_000_000)return `${sign}Rp${(absolute/1_000_000).toLocaleString('id-ID',{maximumFractionDigits:1})} jt`
  return `${sign}${money(absolute)}`
}
const outstandingPayable=(item:Payable)=>Math.max(0,item.amount-item.paid)
// One set of August demo operands for the overview card, chart footer and Laba Rugi.
// Gross profit is net sales (after returns) minus COGS, never revenue alone.
const august={grossSales:414_200_000,returns:8_100_000,cogs:272_900_000,operating:57_800_000,otherNet:1_650_000}
const augustNetSales=august.grossSales-august.returns,augustGrossProfit=augustNetSales-august.cogs,augustNetProfit=augustGrossProfit-august.operating+august.otherNet
const augustMargin=(augustGrossProfit/augustNetSales*100).toFixed(1).replace('.',',')
const outstandingReceivable=(item:Pick<Receivable,'gross'|'returns'|'paid'>)=>Math.max(0,item.gross-item.returns-item.paid)
type DemoReceivable = Omit<Receivable, 'status'> & { status: Receivable['status'] | 'PAID'; qty?: number; mandor?: ReturnType<typeof mandorDebtBalance> }
function demoReceivables(): DemoReceivable[] {
  const notes = readPayDrafts()
  const mandor = readInvoices().filter(invoice => invoice.buyerKind === 'MANDOR' && invoice.status === 'POSTED').map((invoice): DemoReceivable => {
    const balance = mandorDebtBalance(invoice, notes)
    const paid = invoice.paid + balance.settled
    return {
      invoice: invoice.number, customer: invoice.customer, invoiceDate: invoice.day, dueDate: invoice.due || 'Tanpa jatuh tempo',
      gross: invoice.gross, returns: invoice.returns, paid, qty: invoice.qty, mandor: balance,
      status: balance.outstanding === 0 ? 'PAID' : invoice.due && invoice.due < fixtureDate ? 'OVERDUE' : paid > 0 ? 'PARTIAL' : 'OPEN',
    }
  })
  const docs=readInvoices()
  const customers=receivables.map(row=>({...row,returns:docs.find(doc=>doc.number===row.invoice)?.returns??row.returns}))
  return [...customers, ...mandor]
}

function financeTone(status:string):Tone {
  if(['POSTED','PAID','APPROVED','ACTUAL','CLEAR'].includes(status))return 'good'
  if(['OVERDUE','BLOCK','RECALC_PENDING','REVERSED'].includes(status))return 'danger'
  if(['PARTIAL','WAITING_INVOICE','ESTIMATED','REVIEW','WARNING'].includes(status))return 'warn'
  return 'neutral'
}

function Pill({children,tone}:{children:string;tone?:Tone}) {
  return <span className={`biz-pill ${tone??financeTone(children)}`}>{children.replaceAll('_',' ')}</span>
}

// These pages are the UX sample. Owner D15-2 / Fable FABLE-015: the sample label belongs to the page, not to the absence of
// a header button (Ringkasan Keuangan and Payroll & Kasbon have one), so every figure here is visibly a sample.
function FinanceHero({eyebrow,title,description,icon:Glyph,action}:{eyebrow:string;title:string;description:string;icon:typeof WalletCards;action?:React.ReactNode}) {
  return <section className="biz-hero finance"><div><span>{eyebrow}</span><h1>{title}</h1><p>{description}</p>{action?<small role="note">SIMULASI UX · semua angka di halaman ini contoh</small>:null}</div>{action??<div className="biz-hero-rule"><Glyph/><div><small role="note">SIMULASI UX · semua angka di halaman ini contoh</small><strong>Source transaction first</strong><em>Posted dikoreksi lewat reversal, bukan edit.</em></div></div>}</section>
}

function FinanceModal({title,description,onClose,children,action,actionLabel='Simpan simulasi',disabled=false,danger=false}:{title:string;description:string;onClose:()=>void;children:React.ReactNode;action:()=>void;actionLabel?:string;disabled?:boolean;danger?:boolean}) {
  return <div className="biz-modal-backdrop" role="presentation" onMouseDown={onClose}><section className="biz-modal finance" role="dialog" aria-modal="true" aria-labelledby="finance-review-title" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>{danger?'REVERSAL / KONTROL PERIODE':'REVIEW SEBELUM AKSI'}</span><h2 id="finance-review-title">{title}</h2><p>{description}</p></div><button aria-label="Tutup" onClick={onClose}><X/></button></header><div className="biz-modal-body">{children}</div><footer><button className="soft-btn" onClick={onClose}>Kembali</button><button className={`primary-btn ${danger?'danger':''}`} disabled={disabled} onClick={action}>{danger?<Undo2/>:<ShieldCheck/>} {actionLabel}</button></footer></section></div>
}

type FgSourceNote = PayrollNote['fgNotes'][number]
const fgNoteTotal=(item:FgSourceNote)=>item.regularCards||item.repairCards
  ? [...(item.regularCards??[]),...(item.repairCards??[])].reduce((sum,card)=>sum+card.subtotal,0)
  : item.labor+item.reimbursement
const fgRegularCount=(item:FgSourceNote)=>item.regularCards?.length??1
const fgRepairCount=(item:FgSourceNote)=>item.repairCards?.length??0

function PayrollSourceModal({selection,note,onClose,onRelease}:{onRelease?:()=>void;selection:Exclude<PayrollSourceSelection,null>;note:PayrollNote;onClose:()=>void}) {
  const docHref=selection.kind==='FG'?'/produksi/susun-nota-fg/?dari=payroll&nota='+encodeURIComponent(selection.number):readIssueSources().some(d=>d.number===selection.number)?'/keuangan/nota-ambil-mandor/?dari=payroll&nota='+encodeURIComponent(selection.number):null
  const actions=<div className="owner-payroll-actions">{docHref&&<a className="gar-button primary" href={docHref}>Buka dokumen lengkap</a>}{onRelease&&<button type="button" className="soft-btn" onClick={onRelease}>Lepas dari pembayaran ini</button>}</div>
  if(selection.kind==='FG'){
    const item=note.fgNotes.find((source)=>source.number===selection.number)
    if(!item)return null
    const regularCards=item.regularCards??[]
    const repairCards=item.repairCards??[]
    const total=fgNoteTotal(item)
    return <div className="biz-modal-backdrop" role="presentation" onMouseDown={onClose}><section className="biz-modal finance payroll-source-modal fg-composed" role="dialog" aria-modal="true" aria-labelledby="payroll-source-title" onMouseDown={(event)=>event.stopPropagation()}>
      <header><div><span>NOTA FG · POSTED · {note.status==='PAID'?'SUDAH DIBAYAR':'BELUM DIBAYAR'}</span><h2 id="payroll-source-title">{item.number}</h2><p>{item.date} · {fgRegularCount(item)} FG Reguler · {fgRepairCount(item)} Bikin Bagus</p></div><button aria-label="Tutup" onClick={onClose}><X/></button></header>
      <div className="biz-modal-body payroll-note-detail">{actions}{!regularCards.length&&!repairCards.length&&<p>{item.sku} · {fgQuantity(item.good)} Good · {item.bs} BS · {item.stuck} Stuck. Upah {money(item.labor)} · Reimburse {money(item.reimbursement)} · Total {money(fgNoteTotal(item))}.</p>}
        <div className="payroll-note-overview"><article className="regular"><ReceiptText/><span><small>FG REGULER</small><strong>{regularCards.length} pekerjaan</strong></span></article><article className="repair"><RefreshCcw/><span><small>BIKIN BAGUS</small><strong>{repairCards.length} pekerjaan</strong></span></article><article className="total"><WalletCards/><span><small>TOTAL NOTA FG</small><strong>{money(total)}</strong></span></article></div>
        <section className="payroll-work-group regular"><header><div><span>01 · FG REGULER</span><strong>Selesai Dijahit dikurangi komponen BS dan Stuck</strong></div><ReceiptText/></header><div>{regularCards.map((card)=>{const rate=card.sewingRate+card.commissionRate+card.bomRate;const formula=calculateRegularWorkEntitlement({sewnQty:card.sewnQty,fullRate:rate,bsQty:card.bs,bsComponents:card.bsComponents,stuckQty:card.hold,stuckComponents:card.stuckComponents});return <article className="payroll-work-card regular" key={card.id}><header><div><small>{card.source}</small><strong>{card.sku}</strong></div><b>{money(formula.subtotal)}</b></header><div className="payroll-work-quantity compact"><span><small>SELESAI DIJAHIT</small><strong>{fgQuantity(card.sewnQty)}</strong></span><span className="eligible"><small>GOOD → FG</small><strong>{fgQuantity(card.good)}</strong></span><span className="exception"><small>BS</small><strong>{card.bs} pcs</strong></span><span className="rewash"><small>CUCI ULANG</small><strong>{card.rewash} pcs</strong></span><span className="hold"><small>STUCK</small><strong>{card.hold} pcs</strong></span></div><div className="payroll-bs-components"><span>KOMPONEN BS BELUM DIKERJAKAN · SNAPSHOT</span><div>{card.bsComponents.length>0?card.bsComponents.map((component)=><em key={component.name}><CheckCircle2/>{component.name}<b>{money(component.rate)}</b></em>):<small>Tidak ada pengurang BS</small>}</div></div><div className="payroll-bs-components stuck-components"><span>KOMPONEN STUCK BELUM DIPASANG · SNAPSHOT</span><div>{card.stuckComponents.length>0?card.stuckComponents.map((component)=><em key={component.name}><CheckCircle2/>{component.name}<b>{money(component.rate)}</b></em>):<small>Tidak ada komponen Stuck yang ditahan</small>}</div></div><div className="payroll-regular-formula"><span><small>SELESAI DIJAHIT × HARGA</small><strong>{card.sewnQty} × {money(rate)}</strong><em>{money(formula.gross)}</em></span><i>−</i><span className="deduction"><small>BS × KOMPONEN BELUM DIKERJAKAN</small><strong>{card.bs} × {money(card.bsComponents.reduce((sum,component)=>sum+component.rate,0))}</strong><em>{money(formula.bsDeduction)}</em></span><i>−</i><span className="deduction stuck"><small>STUCK × KOMPONEN BELUM DIPASANG</small><strong>{card.hold} × {money(card.stuckComponents.reduce((sum,component)=>sum+component.rate,0))}</strong><em>{money(formula.stuckDeduction)}</em></span><i>=</i><span className="result"><small>NILAI FG REGULER</small><strong>{money(formula.subtotal)}</strong><em>Good bukan pengali upah</em></span></div><div className="payroll-rate-breakdown"><span>Upah jahit <b>{money(card.sewingRate)}</b></span><span>Komisi <b>{money(card.commissionRate)}</b></span><span>BOM <b>{money(card.bomRate)}</b></span><strong>Harga lengkap per pcs {money(rate)}</strong></div><p>Pengurang BS dan Stuck sudah melekat di Nota FG sumber. Susulan hanya melepas komponen yang pernah ditahan; Payroll tidak mengurangkannya lagi.</p></article>})}</div></section>
        <section className="payroll-work-group repair"><header><div><span>02 · BIKIN BAGUS</span><strong>Pekerjaan baru yang lolos QC ulang</strong></div><RefreshCcw/></header>{repairCards.length>0?<div>{repairCards.map((card)=><article className="payroll-work-card repair" key={card.id}><header><div><small>{card.source}</small><strong>{card.sku}</strong></div><b>{money(card.subtotal)}</b></header><div className="repair-component-list">{card.components.map((component)=><span key={component.name}><CheckCircle2/><small>{component.name}</small><strong>{money(component.rate)}</strong></span>)}</div><div className="payroll-rate-breakdown repair"><span>Qty diterima <b>{fgQuantity(card.qty)}</b></span><span>Komponen bayar <b>{card.components.length}</b></span><strong>{card.qty} × {money(card.unitRate)} = {money(card.subtotal)}</strong></div><p>Checkbox komponen berasal dari proses Bikin Bagus dan sudah menjadi snapshot; Payroll tidak memilih ulang.</p></article>)}</div>:<div className="payroll-empty-group"><RefreshCcw/><span><strong>Tidak ada Bikin Bagus pada nota ini</strong><small>Bagian tetap dipisahkan agar pekerjaan reguler tidak tercampur.</small></span></div>}</section>
        <section className="payroll-note-total"><span><small>FG REGULER</small><strong>{money(regularCards.length||repairCards.length?regularCards.reduce((sum,card)=>sum+card.subtotal,0):fgNoteTotal(item))}</strong></span><b>+</b><span><small>BIKIN BAGUS</small><strong>{money(repairCards.reduce((sum,card)=>sum+card.subtotal,0))}</strong></span><b>=</b><span className="result"><small>TOTAL NOTA FG</small><strong>{money(total)}</strong></span></section>
        <p className="payroll-source-note">{item.note}</p>
      </div><footer><button className="primary-btn" onClick={onClose}>Tutup detail</button></footer>
    </section></div>
  }
  const item=note.accessoryNotes.find((source)=>source.number===selection.number)
  if(!item)return null
  return <div className="biz-modal-backdrop" role="presentation" onMouseDown={onClose}><section className="biz-modal finance payroll-source-modal accessory" role="dialog" aria-modal="true" aria-labelledby="payroll-source-title" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>NOTA AMBIL AKSESORI · DOKUMEN SUMBER</span><h2 id="payroll-source-title">{item.number}</h2><p>{item.date} · {item.source}</p></div><button aria-label="Tutup" onClick={onClose}><X/></button></header><div className="biz-modal-body">{actions}{item.lines&&<section className="owner-invoice-lines"><h3>Barang pada nota</h3><table><thead><tr><th>Barang</th><th>Qty</th><th>Harga</th><th>Tagihan</th></tr></thead><tbody>{item.lines.map((l,i)=><tr key={i}><td>{l.item}</td><td>{l.qty} {l.unit}</td><td>{money(l.price)}</td><td>{money(l.total)}</td></tr>)}</tbody></table></section>}<div className="payroll-source-identity"><FileSearch/><span><small>BARANG DETAIL</small><strong>{item.item}</strong><em>{item.source}</em></span></div><div className="payroll-accessory-equation"><span><small>QTY AKTUAL</small><strong>{item.qty.toLocaleString('id-ID')} {item.unit}</strong></span><i>×</i><span><small>HARGA MANDOR SNAPSHOT</small><strong>{item.lines&&item.lines.length>1?'Harga per baris di atas':money(item.unitPrice)}</strong></span><i>=</i><span className="result"><small>TOTAL KASBON</small><strong>{money(item.total)}</strong></span></div><div className="biz-guard"><ShieldCheck/><span>Nota ini berasal dari pengambilan stok detail. Nilainya mengurangi settlement mandor dan tidak mengubah moving-average HPP.</span></div></div><footer><button className="primary-btn" onClick={onClose}>Tutup detail</button></footer></section></div>
}

export default function FinancePages({view,onNavigate,onSalesPayment,onAttendance,onOpenFg,laundry,updateLaundry}:FinanceProps) {
  if(view==='finance-overview')return <FinanceOverview onNavigate={onNavigate}/>
  if(view==='finance-cash')return <CashWorkspace onNavigate={onNavigate}/>
  if(view==='finance-ap')return <PayablesWorkspace laundry={laundry} updateLaundry={updateLaundry}/>
  if(view==='finance-ar')return <ReceivablesWorkspace onSalesPayment={onSalesPayment}/>
  if(view==='finance-payroll')return <PayrollWorkspace onAttendance={onAttendance} onOpenFg={onOpenFg}/>
  if(view==='finance-journal')return <JournalWorkspace/>
  return <ReportsWorkspace/>
}

function FinanceOverview({onNavigate}:{onNavigate:FinanceProps['onNavigate']}) {
  const totalCash=cashAccounts.reduce((sum,item)=>sum+item.balance,0)
  const totalAr=demoReceivables().reduce((sum,item)=>sum+outstandingReceivable(item),0)
  const totalAp=payables.reduce((sum,item)=>sum+outstandingPayable(item),0)
  const grni=payables.filter((item)=>item.kind==='MATERIAL_GRNI').reduce((sum,item)=>sum+outstandingPayable(item),0)
  const grniCount=payables.filter((item)=>item.kind==='MATERIAL_GRNI'&&outstandingPayable(item)>0).length
  const payroll=payrollNotes.filter((item)=>!['PAID','REVERSED'].includes(item.status)).reduce((sum,item)=>sum+item.netPayable,0)
  const chart=[
    {month:'Mar',sales:322,hpp:207},{month:'Apr',sales:348,hpp:221},{month:'Mei',sales:301,hpp:202},
    {month:'Jun',sales:389,hpp:247},{month:'Jul',sales:421,hpp:266},{month:'Agu',sales:414,hpp:273},
  ]
  return <>
    <FinanceHero eyebrow="KEUANGAN · OWNER COCKPIT" title="Ringkasan Keuangan" description="Satu layar untuk melihat uang, hutang, piutang, payroll, margin, dan kualitas laporan. Angka tidak dianggap final selama GRNI atau recost masih terbuka." icon={WalletCards} action={<button className="primary-btn biz-hero-action" onClick={()=>onNavigate('finance-reports')}><NotebookTabs/> Buka laporan</button>}/>
    <section className="biz-metrics finance-five"><button className="panel good" onClick={()=>onNavigate('finance-cash')}><span>KAS & BANK</span><strong>{compactMoney(totalCash)}</strong><small>Saldo buku seluruh akun</small></button><button className="panel warn" onClick={()=>onNavigate('finance-ar')}><span>PIUTANG TERBUKA</span><strong>{compactMoney(totalAr)}</strong><small>Net retur dan payment</small></button><button className="panel danger" onClick={()=>onNavigate('finance-ap')}><span>HUTANG + GRNI</span><strong>{compactMoney(totalAp)}</strong><small>{compactMoney(grni)} masih estimasi</small></button><button className="panel" onClick={()=>onNavigate('finance-payroll')}><span>PAYROLL TERBUKA</span><strong>{compactMoney(payroll)}</strong><small>Draft sampai approved</small></button><button className="panel good" onClick={()=>onNavigate('finance-reports')}><span>LABA KOTOR AGU</span><strong>{compactMoney(augustGrossProfit)}</strong><small>{augustMargin}% dari penjualan bersih · provisional</small></button></section>
    <section className="biz-finance-overview"><article className="panel biz-performance"><header><div><span>PERFORMANCE 6 BULAN</span><strong>Penjualan, HPP & laba kotor</strong><small>Agustus provisional sampai recost invoice terlambat selesai.</small></div><Pill tone="warn">RECALC PENDING</Pill></header><div className="biz-chart">{chart.map((item)=><article key={item.month}><div><i className="sales" style={{height:`${item.sales/4.6}px`}}/><i className="hpp" style={{height:`${item.hpp/4.6}px`}}/></div><span>{item.month}</span></article>)}</div><footer><span><i className="sales"/> Penjualan</span><span><i className="hpp"/> HPP</span><strong>Laba kotor Agustus {compactMoney(augustGrossProfit)} (penjualan bersih − HPP)</strong></footer></article><aside className="panel biz-finance-alerts"><header><div><span>KUALITAS ANGKA</span><strong>Yang membuat laporan belum final</strong></div><ShieldAlert/></header><button onClick={()=>onNavigate('finance-ap')} className="danger"><i/><div><strong>Invoice supplier terlambat 111 hari</strong><small>Recost RM, WIP, FG dan COGS masih antre</small></div><ArrowRight/></button><button onClick={()=>onNavigate('finance-ap')} className="warn"><i/><div><strong>{grniCount} GRNI belum menjadi invoice final</strong><small>{compactMoney(grni)} masih memakai benchmark / estimate</small></div><ArrowRight/></button><button onClick={()=>onNavigate('finance-ar')} className="warn"><i/><div><strong>2 piutang lewat jatuh tempo</strong><small>Butuh collection hari ini</small></div><ArrowRight/></button><button onClick={()=>onNavigate('finance-reports')}><i/><div><strong>Periode Agustus belum boleh ditutup</strong><small>1 blocker dan 3 warning aktif</small></div><ArrowRight/></button></aside></section>
    <section className="panel biz-action-grid"><header><div><span>WORKSPACE KEUANGAN</span><strong>Buka dari transaksi yang mau diperiksa</strong></div><WalletCards/></header><div>{[
      {view:'finance-cash' as const,icon:Landmark,title:'Kas & Bank',note:'Semua uang masuk/keluar dari jurnal posted'},
      {view:'finance-ap' as const,icon:ReceiptText,title:'Hutang Supplier & Vendor',note:'GRNI, AP bahan, dan AP laundry dipisah'},
      {view:'finance-ar' as const,icon:CircleDollarSign,title:'Piutang Pelanggan',note:'Invoice, retur, payment, dan aging'},
      {view:'finance-payroll' as const,icon:UsersRound,title:'Payroll & Kasbon',note:'Nota FG, Bikin Bagus, dan kasbon aktual'},
      {view:'finance-journal' as const,icon:FileClock,title:'Jurnal & Transaksi Lain',note:'Source journal read-only + misc finance'},
      {view:'finance-reports' as const,icon:NotebookTabs,title:'Laporan & Tutup Buku',note:'P&L, SOFP, cashflow, aging, close gate'},
    ].map((item)=><button key={item.view} onClick={()=>onNavigate(item.view)}><i><item.icon/></i><span><strong>{item.title}</strong><small>{item.note}</small></span><ArrowRight/></button>)}</div></section>
  </>
}

function CashWorkspace({onNavigate}:{onNavigate:FinanceProps['onNavigate']}) {
  const [account,setAccount]=useState('ALL')
  const [source,setSource]=useState('ALL')
  const [query,setQuery]=useState('')
  type CashRow=CashMovement&{href?:string}
  const invoices=readSupplierInvoices()
  const sales=readInvoices()
  function supplierPaymentLink(number:string) {
    const invoice=invoices.find(row=>row.number===number)
    const old=payables.find(row=>row.number===number)
    const group=invoice?.group==='ACCESSORY'||old?.reference.startsWith('BELI-ACC')?'aksesori':old?.kind==='LAUNDRY_AP'?'laundry':'kain'
    return '/keuangan/hutang-supplier/?'+new URLSearchParams({bagian:group,invoice:number})+'#pembayaran-invoice'
  }
  const extra:CashRow[]=[
    ...readSupplierTransfers().map((row):CashRow=>({date:row.day,number:row.id,source:'SUPPLIER_PAYMENT',account:row.account,
      counterparty:row.party,description:row.reference+' · '+row.allocations.map(item=>item.number).join(' · '),amount:-transferTotal(row),
      href:supplierPaymentLink(row.allocations[0].number),status:row.reversed?'REVERSED':'POSTED'})),
    ...(readPlannerSession().laundry??[]).flatMap(delivery=>(delivery.finalBills??[]).flatMap(bill=>[
      ...(bill.payments??[]).map((row):CashRow=>({date:row.day,number:'PAY-'+row.id.slice(0,8),source:'VENDOR_PAYMENT',account:row.account,counterparty:delivery.vendor,
        description:bill.number+' · '+row.reference,amount:-row.cents/100,href:laundryPayablesPath(delivery.vendor,bill.number)+'#pembayaran-invoice',status:row.reversal?'REVERSED':'POSTED'})),
      ...(bill.vendorUses??[]).flatMap((row):CashRow[]=>row.account?[{date:row.day,number:'REF-'+row.id.slice(0,8),source:'VENDOR_PAYMENT',account:row.account,counterparty:delivery.vendor,
        description:'Pengembalian kelebihan bayar '+bill.number,amount:row.cents/100,href:laundryPayablesPath(delivery.vendor,bill.number)+'#pembayaran-invoice',status:row.reversal?'REVERSED':'POSTED'}]:[]),
    ])),
    ...readSaleReturns().flatMap((doc):CashRow[]=>doc.settlement==='REFUND'&&doc.account?[{date:doc.at.slice(0,10),number:doc.number,source:'CUSTOMER_PAYMENT',account:doc.account,
      counterparty:sales.find(invoice=>invoice.number===doc.invoice)?.customer??doc.invoice,description:'Refund '+doc.invoice,amount:-doc.excess,
      href:'/penjualan/semua-invoice/?nota='+encodeURIComponent(doc.invoice),status:doc.replacedBy?'REVERSED':'POSTED'}]:[]),
    ...readPayDrafts().flatMap(note=>(note.payments??[]).filter(payment=>payment.amount>0).map((payment):CashRow=>({
      date:payment.day,number:'PAY-'+payment.id.slice(0,8),source:'PAYROLL_PAYMENT',account:payment.account,
      counterparty:note.contractor,description:note.number+' · '+payment.reference,amount:-payment.amount,
      href:'/keuangan/payroll-kasbon/?'+new URLSearchParams({nota:note.number})+'#pembayaran-payroll',status:payment.reversed?'REVERSED':'POSTED',
    }))),
  ]
  const movements:CashRow[]=[...extra.slice().reverse(),...cashMovements]
  const visible=movements.filter(movement=>`${movement.number} ${movement.counterparty} ${movement.description} ${movement.account}`.toLowerCase().includes(query.toLowerCase())
    && (account==='ALL'||movement.account===account)&&(source==='ALL'||movement.source===source))
  const accounts=cashAccounts.map(item=>{
    const posted=extra.filter(row=>row.account===item.name&&row.status==='POSTED')
    const inflow=posted.filter(row=>row.amount>0).reduce((sum,row)=>sum+row.amount,0)
    const outflow=posted.filter(row=>row.amount<0).reduce((sum,row)=>sum-row.amount,0)
    return {...item,balance:item.balance+inflow-outflow,inflow:item.inflow+inflow,outflow:item.outflow+outflow}
  })
  const totalCash=accounts.reduce((sum,item)=>sum+item.balance,0)
  return <>
    <FinanceHero eyebrow="KEUANGAN · CASH LEDGER" title="Kas & Bank" description="Browser semua uang masuk dan keluar berdasarkan jurnal posted. Tidak ada edit saldo; koreksi selalu lewat reversal transaksi sumber." icon={Landmark}/>
    <section className="biz-cash-accounts">{accounts.map((item)=><button className={`panel ${account===item.name?'active':''}`} key={item.code} onClick={()=>setAccount(account===item.name?'ALL':item.name)}><header><span>{item.kind}</span><Pill tone="good">RECONCILED</Pill></header><strong>{item.name}</strong><h2>{money(item.balance)}</h2><div><span>Masuk <b>+{compactMoney(item.inflow)}</b></span><span>Keluar <b>−{compactMoney(item.outflow)}</b></span></div><small>Rekonsiliasi {item.reconciledAt}</small></button>)}</section>
    <section className="panel biz-ledger"><header><div><span>CASH MOVEMENT</span><strong>{visible.length} transaksi · saldo {money(totalCash)}</strong></div><button className="soft-btn" onClick={()=>onNavigate('finance-journal')}><PlusIcon/> Transaksi lain-lain</button></header><div className="biz-history-toolbar compact"><label className="biz-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari ref, lawan transaksi, atau akun..."/></label><select value={account} onChange={(event)=>setAccount(event.target.value)}><option value="ALL">Semua akun</option>{accounts.map((item)=><option key={item.code}>{item.name}</option>)}</select><select value={source} onChange={(event)=>setSource(event.target.value)}><option value="ALL">Semua sumber</option>{[...new Set(movements.map((item)=>item.source))].map((item)=><option key={item}>{item}</option>)}</select></div><div className="biz-table cash"><div className="biz-table-head"><span>Waktu / ref</span><span>Lawan transaksi</span><span>Keterangan</span><span>Akun</span><span>Jumlah</span><span>Status</span></div>{visible.map((movement)=><article key={movement.number}><span>{movement.href?<a className="source-row-link" href={movement.href}><strong>{movement.number}</strong><ArrowRight aria-hidden="true"/></a>:<strong>{movement.number}</strong>}<small>{movement.date}</small></span><strong>{movement.counterparty}</strong><span>{movement.description}<small>{movement.source.replaceAll('_',' ')}</small></span><span>{movement.account}</span><b className={movement.amount<0?'negative':'positive'}>{movement.amount<0?'− ':'+ '}{money(Math.abs(movement.amount))}</b><Pill>{movement.status}</Pill></article>)}</div><footer className="biz-ledger-rule"><LockKeyhole/><span><strong>Saldo tidak boleh diketik.</strong><small>Kas berubah hanya dari payment/customer receipt/payroll/misc transaction yang posted.</small></span></footer></section>
  </>
}

function PlusIcon(){return <span className="biz-plus">+</span>}
const payableSections=[{key:'FABRIC',label:'Vendor Kain',icon:Layers3},{key:'LAUNDRY',label:'Laundry',icon:Waves},{key:'ACCESSORY',label:'Aksesori',icon:Package}] as const
type PayableSection=typeof payableSections[number]['key']
type PayableRow={key:string;number:string;party:string;reference:string;amount:number;paid:number;balance:number;status:string;credit?:number;payable?:Payable;invoice?:SupplierInvoice;laundry?:{delivery:LaundryDelivery;bill:LaundryFinalBill}}

function PayablesWorkspace({laundry,updateLaundry}:{laundry:LaundryDelivery[];updateLaundry:UpdateLaundry}) {
  const options=new URLSearchParams(location.search)
  const [section,setSection]=useState<PayableSection>(()=>options.get('bagian')==='laundry'?'LAUNDRY':options.get('bagian')==='aksesori'?'ACCESSORY':'FABRIC')
  const [state,setState]=useState(()=>options.has('invoice')?'ALL':'OPEN')
  const [partner,setPartner]=useState(()=>options.get('vendor')??(!options.has('invoice')?sessionStorage.getItem('erp.demo.ap-party:'+section):'')??'')
  const [mode,setMode]=useState<'compose'|'ledger'>(()=>options.has('invoice')||options.get('mode')==='bayar'?'ledger':'compose')
  const [editing,setEditing]=useState('')
  const [query,setQuery]=useState('')
  const [transfers,setTransfers]=useState(readSupplierTransfers)
  const [invoices,setInvoices]=useState(readSupplierInvoices)
  const [selectedKey,setSelectedKey]=useState(()=>options.get('invoice')??'')
  const [notice,setNotice]=useState('')
  const category=payableSections.find(row=>row.key===section)!
  const posted=transferPayables(transfers,undefined,invoices).filter(row=>row.kind!=='MATERIAL_GRNI')
  const sectionDocs:PayableRow[]=[
    ...invoices.filter(doc=>doc.group===section&&(doc.status==='DRAFT'||doc.reversal)).map(invoice=>({key:invoice.id,number:invoice.number,party:invoice.supplier,reference:invoice.lines.map(line=>line.source.number).join(' · '),
      amount:supplierInvoiceAmount(invoice),paid:0,balance:0,status:invoice.reversal?'REVERSED':'DRAFT',invoice})),
    ...posted.filter(doc=>{
      const invoice=invoices.find(row=>row.number===doc.number)
      const group=invoice?.group??(doc.kind==='LAUNDRY_AP'?'LAUNDRY':doc.reference.startsWith('BELI-ACC')?'ACCESSORY':'FABRIC')
      return group===section
    }).map(payable=>({key:payable.number,number:payable.number,party:payable.party,reference:payable.reference,amount:payable.amount,paid:payable.paid,
      balance:outstandingPayable(payable),status:payable.status,payable,invoice:invoices.find(row=>row.number===payable.number)})),
    ...(section==='LAUNDRY'?laundryDocuments(laundry).filter(({bill})=>isLaundryInvoice(bill)).map(({delivery,bill})=>{
      const balance=billRemaining(laundry,delivery,bill)
      const draft=bill.status==='DRAFT'
      return {key:bill.invoiceId??delivery.id+'|'+bill.number,number:bill.number,party:delivery.vendor,
        reference:bill.contracts?.map(ref=>ref.number).join(' · ')??delivery.id,
        amount:billGross(bill)/100,paid:billPaid(bill)/100,balance:bill.reversal?0:balance/100,credit:(billCredit(bill)+vendorCreditApplied(laundry,delivery.id,bill.number))/100,
        status:bill.reversal?'REVERSED':draft?'DRAFT':balance===0?'PAID':billPaid(bill)>0?'PARTIAL':'OPEN',laundry:{delivery,bill}}
    }):[]),
  ]
  const sectionSources=section==='LAUNDRY'?[]:kasbonSources().filter(row=>row.group===section)
  const sourceParties=section==='LAUNDRY'?[...laundryContracts(laundry).map(row=>row.delivery.vendor),...laundry.map(row=>row.vendor)]:sectionSources.map(row=>row.supplier)
  const vendors=[...new Set([...sourceParties,...sectionDocs.map(row=>row.party),...payablePartnerNames(section)])].sort((a,b)=>a.localeCompare(b,'id'))
  const linkedParty=sectionDocs.find(doc=>doc.number===options.get('invoice'))?.party
  const vendor=vendors.includes(partner)?partner:linkedParty??sourceParties[0]??vendors[0]??''
  const docs=sectionDocs.filter(doc=>doc.party===vendor)
  const sources=sectionSources.filter(row=>row.supplier===vendor)
  const openSources=sources.filter(row=>supplierSourceRemaining(invoices,row)>0)
  const openContracts=laundryContracts(laundry,vendor).filter(({ref})=>!invoiceForLaundryContract(laundry,ref))
  const drafts=docs.filter(doc=>doc.status==='DRAFT')
  const activeDraft=drafts.find(doc=>doc.key===editing)
  const visible=docs.filter(doc=>browseMatchPieces(query,doc.laundry?[doc.laundry.bill.qty]:doc.invoice?.lines.filter(line=>line.source.unit==='pcs').map(line=>line.qty)??[],
    doc.number,doc.party,doc.reference)&&(state==='ALL'||(state==='OPEN'?!['PAID','REVERSED'].includes(doc.status):doc.status===state)))
  const selected=visible.find(doc=>doc.key===selectedKey)??visible.find(doc=>doc.number===selectedKey)??visible[0]
  const payablesOpen=docs.filter(doc=>doc.status!=='DRAFT'&&doc.balance>0)
  const outstanding=payablesOpen.reduce((sum,doc)=>sum+doc.balance,0)
  const laundryCredit=availableCredits(laundry,vendor).reduce((sum,row)=>sum+row.remaining,0)
  function route(next:PayableSection,party:string,workspace:'compose'|'ledger',number='') {
    const url=new URL(location.href)
    url.search=''
    url.hash=''
    if(next!=='FABRIC')url.searchParams.set('bagian',next==='LAUNDRY'?'laundry':'aksesori')
    if(party)url.searchParams.set('vendor',party)
    if(workspace==='ledger')url.searchParams.set('mode','bayar')
    if(number)url.searchParams.set('invoice',number)
    window.history.replaceState(window.history.state,'',url)
  }
  function chooseSection(next:PayableSection) {
    if(next===section)return
    const nextParty=sessionStorage.getItem('erp.demo.ap-party:'+next)??''
    setSection(next);setState('OPEN');setPartner(nextParty);setQuery('');setSelectedKey('');setEditing('');setNotice('')
    route(next,nextParty,mode)
  }
  function chooseParty(next:string) {
    sessionStorage.setItem('erp.demo.ap-party:'+section,next)
    setPartner(next);setSelectedKey('');setEditing('');setQuery('');setState('OPEN');setNotice('')
    route(section,next,mode)
  }
  function openDocument(id:string,number:string) {
    setSelectedKey(id);setQuery('');setState('ALL');setMode('ledger');route(section,vendor,'ledger',number)
  }
  function editDraft(id:string) {
    setEditing(id);setMode('compose');setNotice('');route(section,vendor,'compose')
  }
  function invoiceSaved(id:string,number:string,draft:boolean) {
    setQuery('');setSelectedKey(id);setState('ALL')
    if(draft){setEditing(id);setMode('compose');route(section,vendor,'compose')}
    else {setEditing('');openDocument(id,number)}
    setNotice(draft?'Draf '+number+' tersimpan.':'Invoice '+number+' siap dibayar.')
  }
  const desk={
    drafts:drafts.map(doc=>({id:doc.key,number:doc.number,day:doc.laundry?.bill.day??doc.invoice!.day,
      count:doc.laundry?.bill.contracts?.length??doc.invoice?.lines.length??0,amount:doc.amount})),
    onEdit:editDraft, onNew:()=>editDraft(''),
    onDetail:(id:string)=>{const item=drafts.find(doc=>doc.key===id);if(item)openDocument(item.key,item.number)},
  }

  return <div className="ap-page">
    <section aria-label="Ringkasan hutang">
      <FinanceHero eyebrow="KEUANGAN · HUTANG" title="Hutang Supplier & Vendor"
        description="Gabungkan kontrabon dari satu supplier atau vendor, lalu catat pembayaran per invoice." icon={ReceiptText}
        action={section==='LAUNDRY'
          ? <a className="soft-btn ap-claims-link" href={laundryContractsPath(vendor)}><ReceiptText aria-hidden="true"/> Klaim &amp; Kontrabon <ArrowRight aria-hidden="true"/></a>
          : <div className="ap-hero-mark" aria-hidden="true"><WalletCards/></div>}/>
      <div className="panel ap-partner-bar">
        <nav className="payable-section-tabs" aria-label="Jenis tagihan">
          {payableSections.map(({key,label,icon:Glyph})=><button type="button" key={key} data-kind={key} aria-pressed={section===key} onClick={()=>chooseSection(key)}>
            <Glyph aria-hidden="true"/><strong>{label}</strong>
          </button>)}
        </nav>
        <label className="payable-filter-label ap-partner-picker">{section==='LAUNDRY'?'Pilih laundry':section==='FABRIC'?'Pilih supplier kain':'Pilih supplier aksesori'}
          <select value={vendor} onChange={event=>chooseParty(event.target.value)}>{vendors.map(name=><option key={name}>{name}</option>)}</select>
        </label>
      </div>
      <WorkspaceFigures label={'Ringkasan '+vendor} figures={[
        {label:'Total belum dibayar',value:money(outstanding),icon:WalletCards,tone:'amber'},
        {label:'Kontrabon siap dipilih',value:section==='LAUNDRY'?openContracts.length:openSources.length,icon:ReceiptText,tone:'green'},
        {label:'Draf invoice',value:drafts.length,icon:FileClock,tone:'blue'},
        section==='LAUNDRY'
          ? {label:'Kredit klaim tersedia',value:amountText(laundryCredit/100),icon:CheckCircle2,tone:'green'}
          : {label:'Invoice belum lunas',value:payablesOpen.length,icon:FileSearch,tone:'blue'},
      ]}/>
    </section>
    <div className="ap-mode-buttons" role="group" aria-label="Pekerjaan hutang">
      <button type="button" className="soft-btn" aria-pressed={mode==='compose'} onClick={()=>{setMode('compose');route(section,vendor,'compose')}}>
        <FilePlus2 aria-hidden="true"/> Susun invoice {section==='LAUNDRY'?'Laundry':'supplier'}</button>
      <button type="button" className="soft-btn" aria-pressed={mode==='ledger'} onClick={()=>{setMode('ledger');route(section,vendor,'ledger')}}>
        <WalletCards aria-hidden="true"/> Invoice &amp; pembayaran</button>
    </div>
    {notice&&<div className="biz-inline-notice" role="status"><CheckCircle2/> {notice}</div>}
    {mode==='compose' ? (section==='LAUNDRY'
      ? <LaundryVendorInvoiceComposer key={JSON.stringify([section,vendor,editing])} {...desk} deliveries={laundry} vendor={vendor}
          previous={activeDraft?.laundry?.bill} update={updateLaundry} onSaved={bill=>invoiceSaved(bill.invoiceId!,bill.number,bill.status==='DRAFT')}/>
      : <SupplierInvoiceComposer key={JSON.stringify([section,vendor,editing])} {...desk} group={section} party={vendor} rows={invoices} previous={activeDraft?.invoice}
          onSave={({doc,rows})=>{setInvoices(rows);invoiceSaved(doc.status==='DRAFT'?doc.id:doc.number,doc.number,doc.status==='DRAFT')}}/>)
      : <section className="panel biz-master-detail finance-detail payable-workspace">
      <BrowsePane aria-label="Daftar utang dan GRNI">
        <header className="ap-ledger-head"><i><NotebookTabs aria-hidden="true"/></i><div><span>{category.label}</span><strong>Daftar invoice</strong></div><small>{visible.length} invoice</small></header>
        <div className="payable-filters">
          <label className="biz-search"><Search aria-hidden="true"/><input aria-label="Cari invoice supplier" type="search" value={query} onChange={event=>setQuery(event.target.value)} placeholder="Cari invoice, supplier, atau kasbon…"/></label>
          <label className="payable-filter-label">Status invoice<select value={state} onChange={event=>setState(event.target.value)}>
            <option value="OPEN">Draf &amp; belum lunas</option><option value="ALL">Semua invoice</option><option value="DRAFT">Draf</option><option value="PAID">Lunas</option><option value="REVERSED">Dibalik</option>
          </select></label>
        </div>
        <div className="biz-browser-list">{visible.map(doc=><button type="button" key={doc.key} aria-pressed={doc===selected} className={doc===selected?'active':''} onClick={()=>openDocument(doc.key,doc.number)}>
          <i><ReceiptText aria-hidden="true"/></i><div><strong>{money(doc.status==='DRAFT'?doc.amount:doc.balance)}</strong><small>{doc.party}</small><em>{doc.number}</em></div>
          <Pill>{doc.status}</Pill>
        </button>)}</div>
      </BrowsePane>
      {selected?<main>
        <header className="biz-detail-head payable-identity">
          <i><category.icon aria-hidden="true"/></i>
          <div><span>{selected.party}</span><h2>{selected.number}</h2><p>{selected.laundry?supplierDateLabel(selected.laundry.bill.day):selected.invoice?supplierDateLabel(selected.invoice.day):selected.reference}</p></div>
          <Pill>{selected.status}</Pill>
        </header>
        <dl className="payable-metrics payable-balance">
          <div><dt><ReceiptText aria-hidden="true"/> Total invoice</dt><dd>{money(selected.amount)}</dd></div>
          {selected.status!=='DRAFT'&&<>
            <div className="ap-paid"><dt><Banknote aria-hidden="true"/> Sudah dibayar</dt><dd>{money(selected.paid)}</dd></div>
            {!!selected.credit&&<div className="ap-paid"><dt><CheckCircle2 aria-hidden="true"/> Potongan kredit</dt><dd>{money(selected.credit)}</dd></div>}
            <div className="payable-outstanding"><dt><WalletCards aria-hidden="true"/> Sisa tagihan</dt><dd>{money(selected.balance)}</dd></div>
          </>}
        </dl>
        {selected.invoice&&<section className="demo-ops-card demo-supplier-transfers" aria-label="Kasbon dalam invoice">
          <header className="demo-ops-header"><div className="demo-operation-heading"><i><ReceiptText aria-hidden="true"/></i><div><h3>Kasbon dalam invoice ini</h3><p>{selected.invoice.lines.length} kasbon</p></div></div>
            {selected.status==='DRAFT'&&<button type="button" className="primary-btn" onClick={()=>editDraft(selected.key)}>Tambah / lepas kasbon <ArrowRight size={16}/></button>}</header>
          {!!selected.invoice.lines.length&&<div className="payable-receipt-lines">{selected.invoice.lines.map(line=><article key={line.source.id}>
            <div><strong>{line.qty.toLocaleString('id-ID')} {line.source.unit}</strong> · {line.source.name}<small>{line.source.number} · {supplierDateLabel(line.source.day)}</small></div>
            <b>{amountText(line.cents/100)}</b>
            {line.source.id.includes(':')&&<a className="source-row-link" href={receiptDocumentPath(line.source.number,line.source.group==='ACCESSORY'?'aksesori':'kain')}>Buka penerimaan <ArrowRight size={15}/></a>}
          </article>)}</div>}
        </section>}
        {selected.laundry&&<section className="demo-ops-card demo-supplier-transfers" aria-label="Kontrabon dalam invoice">
          <header className="demo-ops-header"><div className="demo-operation-heading"><i><ReceiptText aria-hidden="true"/></i>
            <div><h3>{selected.laundry.bill.contracts?'Kontrabon dalam invoice ini':'Arsip tagihan Laundry'}</h3>
              <p>{selected.laundry.bill.contracts?.length??1} dokumen · {selected.laundry.bill.qty} pcs</p></div>
          </div>{selected.status==='DRAFT'&&<button className="primary-btn" type="button" onClick={()=>editDraft(selected.key)}>Tambah / lepas kontrabon <ArrowRight aria-hidden="true"/></button>}</header>
          <div className="payable-receipt-lines">{selected.laundry.bill.contracts?.map(ref=>{
            const source=laundryContracts(laundry,selected.party).find(row=>laundryContractKey(row.ref)===laundryContractKey(ref))
            return <article key={laundryContractKey(ref)}><div><strong>{source?.bill.qty??0} pcs</strong><small>{source?.bill.day}</small></div>
              <a className="soft-btn" href={laundryContractsPath(selected.party,ref.number)}>{ref.number} <ArrowRight aria-hidden="true"/></a></article>
          })??<a className="soft-btn invoice-document-link" href={laundryContractsPath(selected.party)}>Buka Klaim &amp; Kontrabon Laundry <ArrowRight aria-hidden="true"/></a>}</div>
        </section>}
        {selected.laundry&&!['DRAFT','REVERSED'].includes(selected.status)&&<LaundryInvoiceActions key={selected.key} delivery={selected.laundry.delivery} bill={selected.laundry.bill} deliveries={laundry} update={updateLaundry}/>}
        {selected.payable&&<SupplierTransferPanel key={selected.key} doc={selected.payable} transfers={transfers} onSaved={rows=>{setTransfers(rows);setState('ALL');setSelectedKey(selected.key)}}/>}
        {selected.invoice&&<div className="demo-supplier-transfers"><StockSourceReversal key={selected.key} label={selected.status==='DRAFT'?'Batalkan draf invoice':'Balikkan invoice'}
          document={selected.number} reversal={selected.invoice.reversal} blockers={supplierInvoicePayments(transfers,selected.invoice).map(row=>({label:'Pembayaran · '+row.reference,href:'#pembayaran-invoice'}))}
          onReverse={reason=>{setInvoices(reverseSupplierInvoice(selected.invoice!.id,reason));setState('ALL');setSelectedKey(selected.key)}}/></div>}
        {selected.laundry&&<div className="demo-supplier-transfers"><StockSourceReversal key={selected.key} label={selected.status==='DRAFT'?'Batalkan draf invoice':'Balikkan invoice'}
          document={selected.number} reversal={selected.laundry.bill.reversal} blockers={laundryInvoiceBlockers(laundry,selected.laundry.delivery,selected.laundry.bill)}
          onReverse={reason=>{
            const next=reverseLaundryInvoice(laundry,selected.laundry!.delivery.id,selected.number,reason)
            updateLaundry(current=>current===laundry?next:current);setState('ALL');setSelectedKey(selected.key)
          }}/></div>}
      </main>:<main className="biz-empty"><ReceiptText aria-hidden="true"/><strong>Belum ada invoice untuk pilihan ini</strong><small>{section==='LAUNDRY'?'Pilih Susun invoice Laundry saat invoice vendor sudah datang.':'Ubah filter atau pilih Susun invoice supplier.'}</small></main>}
    </section>}
  </div>
}

function ReceivablesWorkspace({onSalesPayment}:{onSalesPayment:()=>void}) {
  const [accounts]=useState(demoReceivables)
  const [customer,setCustomer]=useState('ALL')
  const [status,setStatus]=useState('OPEN')
  const [query,setQuery]=useState('')
  const [selectedInvoice,setSelectedInvoice]=useState(accounts[0].invoice)
  const visible=accounts.filter((item)=>browseMatchPieces(query,item.qty===undefined?[]:[item.qty],item.invoice,item.customer)
    && (customer==='ALL'||item.customer===customer) && (status==='ALL'||(status==='OPEN'?item.status!=='PAID':item.status===status)))
  const selected=accounts.find((item)=>item.invoice===selectedInvoice)??accounts[0]
  const outstanding=outstandingReceivable(selected)
  return <>
    <FinanceHero eyebrow="KEUANGAN · COLLECTION COCKPIT" title="Piutang Pelanggan" description="Lihat invoice, retur, pembayaran, jatuh tempo, dan risiko per toko. Buka rincian invoice pelanggan dan piutang belanja mandor yang terhubung ke payroll." icon={CircleDollarSign}/>
    <section className="biz-metrics"><div className="panel warn"><span>TOTAL AR</span><strong>{compactMoney(accounts.reduce((sum,item)=>sum+outstandingReceivable(item),0))}</strong><small>Net retur dan payment</small></div><div className="panel danger"><span>OVERDUE</span><strong>Rp7,7 jt</strong><small>2 invoice</small></div><div className="panel"><span>DUE ≤ 7 HARI</span><strong>Rp4,8 jt</strong><small>Prioritas collection</small></div><div className="panel good"><span>PAYMENT HARI INI</span><strong>Rp7,7 jt</strong><small>Dari dua pelanggan</small></div></section>
    <section className="panel biz-master-detail finance-detail"><BrowsePane aria-label="Daftar piutang"><header><div><span>AR BROWSER</span><strong>{visible.length} invoice</strong></div><CircleDollarSign/></header><label className="biz-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari invoice atau pelanggan..."/></label><div className="biz-double-filter"><select value={customer} onChange={(event)=>setCustomer(event.target.value)}><option value="ALL">Semua pelanggan</option>{[...new Set(accounts.map((item)=>item.customer))].map((item)=><option key={item}>{item}</option>)}</select><select value={status} onChange={(event)=>setStatus(event.target.value)}><option value="OPEN">Semua terbuka</option><option value="ALL">Semua status</option><option>OVERDUE</option><option>PARTIAL</option><option value="PAID">Lunas</option></select></div><div className="biz-browser-list">{visible.map((item)=><button key={item.invoice} className={item.invoice===selected.invoice?'active':''} onClick={()=>setSelectedInvoice(item.invoice)}><span>AR</span><div><strong>{item.invoice}</strong><small>{item.customer}</small><em>Due {item.dueDate}</em></div><b>{money(outstandingReceivable(item))}</b><Pill>{item.status}</Pill></button>)}</div></BrowsePane><main><header className="biz-detail-head"><div><span>{selected.mandor?'PIUTANG BELANJA MANDOR':'INVOICE PELANGGAN'}</span><h2>{selected.invoice}</h2><p>{selected.customer} · {selected.invoiceDate}</p></div><Pill>{selected.status}</Pill></header><div className="biz-ar-equation"><span><small>GROSS SALE</small><strong>{money(selected.gross)}</strong></span><i>−</i><span><small>RETUR</small><strong>{money(selected.returns)}</strong></span><i>−</i><span><small>{selected.mandor?'DIBAYAR VIA PAYROLL':'PAYMENT'}</small><strong>{money(selected.paid)}</strong></span><i>=</i><span><small>OUTSTANDING</small><strong>{money(outstanding)}</strong></span></div><div className="biz-date-audit"><article><CalendarClock/><span><small>INVOICE DATE</small><strong>{selected.invoiceDate}</strong><em>Tanggal sale posted</em></span></article><article><Clock3/><span><small>DUE DATE</small><strong>{selected.dueDate}</strong><em>{selected.status==='OVERDUE'?'Lewat jatuh tempo':'Belum jatuh tempo'}</em></span></article><article><TrendingDown/><span><small>RETUR</small><strong>{money(selected.returns)}</strong><em>Dokumen terpisah</em></span></article></div>{selected.mandor ? <section className="mandor-debt-panel" aria-label="Alokasi piutang mandor"><header><WalletCards aria-hidden="true"/><div><h3>Alokasi payroll</h3><p>Saldo piutang berkurang saat payroll dibayar.</p></div></header><dl className="mandor-debt-balances"><div><dt>Dialokasikan</dt><dd>{money(selected.mandor.reserved)}</dd></div><div><dt>Saldo bebas</dt><dd>{money(selected.mandor.available)}</dd></div></dl></section> : <><section className="biz-source-chain"><span>ALUR PIUTANG</span><div><article><small>01</small><strong>Sale posted</strong><em>Revenue + AR</em></article><ArrowRight/><article><small>02</small><strong>Retur bila ada</strong><em>AR + revenue turun</em></article><ArrowRight/><article><small>03</small><strong>Payment</strong><em>Kas naik · AR turun</em></article></div></section><div className="biz-guard"><ShieldCheck/><span>Piutang di sini read-only. Pembayaran dicatat dari invoice eligible di Penjualan agar allocation uang tidak dobel.</span></div></>}<footer className="biz-detail-actions"><span>Outstanding {money(outstanding)} · {selected.status}</span>{selected.mandor ? <a className="soft-btn" href={'/penjualan/semua-invoice/?nota='+encodeURIComponent(selected.invoice)}>Buka invoice <ArrowRight/></a> : <button className="primary-btn" onClick={onSalesPayment}><WalletCards/> Catat pembayaran pelanggan</button>}</footer></main></section>
  </>
}

function MandorDebtPicker({note,bills,linked,onChoose,onClose}:{
  note:PayDraft; bills:ReturnType<typeof mandorBillsForPayroll>; linked:string|null;
  onChoose:(invoice:string,amount:number)=>void; onClose:()=>void;
}) {
  const initial = bills.find(bill=>bill.invoice.number===linked) ?? bills[0]
  const [invoice,setInvoice]=useState(initial?.invoice.number ?? '')
  const [amount,setAmount]=useState(initial?.allocated ? String(initial.allocated) : '')
  const [error,setError]=useState('')
  const bill=bills.find(row=>row.invoice.number===invoice)
  const proposed=Number(amount)
  const canSave=!!bill&&Number.isSafeInteger(proposed)&&proposed>0&&proposed<=bill.maximum
  function choose(amountToApply:number) {
    if (!bill) return
    try { onChoose(invoice,amountToApply) }
    catch (failure) { setError((failure as Error).message) }
  }
  return <ReasonDialog title="Potongan piutang mandor" closeLabel="Tutup" onClose={onClose} className="mandor-debt-dialog">
    <p>{note.contractor} · {note.period}</p>
    {bill ? <form onSubmit={event=>{event.preventDefault();if(canSave)choose(proposed)}}>
      <label>Invoice piutang
        <select value={invoice} onChange={event=>{
          const next=bills.find(row=>row.invoice.number===event.target.value)
          setInvoice(event.target.value);setAmount(next?.allocated ? String(next.allocated) : '');setError('')
        }}>{bills.map(row=><option key={row.invoice.number} value={row.invoice.number}>{row.invoice.number} · {money(row.outstanding)} tersisa</option>)}</select>
      </label>
      <dl className="mandor-debt-balances">
        <div><dt>Sisa piutang</dt><dd>{money(bill.outstanding)}</dd></div>
        <div><dt>Batas potongan periode ini</dt><dd>{money(bill.maximum)}</dd></div>
      </dl>
      <label>Nominal potongan
        <NumberEntry inputMode="numeric" maxLength={22} value={amount} onValueChange={rawInput =>{setAmount(cleanMoneyInput(rawInput));setError('')}} placeholder="Rp 0"/>
      </label>
      <p>{bill.maximum>0 ? 'Saldo piutang turun saat payroll dibayar.' : 'Tambahkan nota upah atau cek alokasi piutang di periode lain.'}</p>
      {error&&<p role="alert">{error}</p>}
      <footer>
        <button type="button" className="soft-btn" disabled={bill.maximum<=0} onClick={()=>setAmount(String(bill.maximum))}>Isi batas potongan</button>
        {bill.allocated>0&&<button type="button" className="soft-btn" onClick={()=>choose(0)}>Lepas potongan</button>}
        <button className="primary-btn" disabled={!canSave}>Simpan potongan</button>
      </footer>
    </form> : <div className="mandor-debt-empty">
      <p>Invoice belanja {note.contractor} yang sudah dipost akan muncul sesuai periode payroll.</p>
      <a className="soft-btn" href={'/penjualan/invoice/?mandor='+encodeURIComponent(note.contractor)}>Buat invoice mandor <ArrowRight/></a>
    </div>}
  </ReasonDialog>
}

function PayrollWorkspace({onAttendance,onOpenFg}:{onAttendance:()=>void;onOpenFg?:()=>void}) {
  const [notes,renderNotes]=useState(readPayDrafts)
  function setNotes(update:(notes:PayDraft[])=>PayDraft[]){renderNotes(savePayDrafts(update(readPayDrafts())))}
  const [salesInvoices]=useState(readInvoices)
  const [debtLink]=useState(()=>new URLSearchParams(location.search))
  const linkedInvoice=salesInvoices.find(invoice=>invoice.number===debtLink.get('piutang')&&invoice.buyerKind==='MANDOR'&&invoice.status==='POSTED')
  const sourcePayroll=debtLink.get('nota')
  const suggestedPeriod=periodFor('week',linkedInvoice?.dateKey??fixtureDate)
  const [compose,setCompose]=useState(false)
  const [mandor,setMandor]=useState(linkedInvoice?.customer??'Mandor Afui')
  const [from,setFrom]=useState(suggestedPeriod.start),[until,setUntil]=useState(suggestedPeriod.end)
  const [pickOpen,setPickOpen]=useState<'FG'|'ACCESSORY'|null>(null),[sourceQuery,setSourceQuery]=useState('')
  const [debtOpen,setDebtOpen]=useState(false)
  const [creditsOpen,setCreditsOpen]=useState(false)
  const [workPeriod,setWorkPeriod]=useState(()=>periodFor('all','2026-11-24'))
  const [payrollSort,setPayrollSort]=useState('recent')

  const [statusFilter,setStatusFilter]=useState(sourcePayroll?'Semua status':'Aktif · lunas disembunyikan')
  const creditMandor=debtLink.get('mandor')
  const [mandorFilter,setMandorFilter]=useState(()=>notes.find(note=>note.contractor===(linkedInvoice?.customer??creditMandor))?.contractor??'Semua mandor')
  const [query,setQuery]=useState('')
  const [selectedNumber,setSelectedNumber]=useState(()=>{
    const linkedNote=linkedInvoice && notes.filter(editablePayroll).sort((left,right)=>payrollPeriod(right).end.localeCompare(payrollPeriod(left).end))
      .find(note=>mandorBillsForPayroll(salesInvoices,notes,note).some(bill=>bill.invoice.number===linkedInvoice.number))
    return notes.find(note=>note.number===sourcePayroll)?.number ?? linkedNote?.number ?? sessionStorage.getItem('erp.owner.payroll.focus') ?? notes[0].number
  })
  const [sourceSelection,setSourceSelection]=useState<PayrollSourceSelection>(null)
  const [payOpen,setPayOpen]=useState(false)
  const [payReference,setPayReference]=useState('')
  const [payAccount,setPayAccount]=useState('Mandiri Payroll')
  const [payAmount,setPayAmount]=useState('')
  const [payDay,setPayDay]=useState(lastWarehouseDay)
  const [paymentError,setPaymentError]=useState('')
  const [reverseOpen,setReverseOpen]=useState(false)
  const [reversalId,setReversalId]=useState<string|null>(null)
  const [reason,setReason]=useState('')
  const [notice,setNotice]=useState('')
  const mandorOptions=['Semua mandor',...new Set(notes.map((item)=>item.contractor))]
  const visible=useMemo(()=>notes.filter((item)=>{
    const statusMatches=statusFilter==='Semua status'
      || (statusFilter==='Aktif · lunas disembunyikan'&&!['PAID','REVERSED'].includes(item.status))
      || item.status===statusFilter.toUpperCase()
    const period=payrollPeriod(item)
    const overlaps=(!workPeriod.start||period.end>=workPeriod.start)&&(!workPeriod.end||period.start<=workPeriod.end)&&(!workPeriod.start||!workPeriod.end||workPeriod.start<=workPeriod.end)
    const quantities = [item.workQty, ...item.fgNotes.flatMap(fgSourcePieces), ...item.accessoryNotes.flatMap(accessorySourcePieces)]
    return overlaps&&browseMatchPieces(query,quantities,item.number,item.contractor,item.period)
      && (mandorFilter==='Semua mandor'||item.contractor===mandorFilter)
      && statusMatches
  }).sort((a,b)=>{
    if(payrollSort==='amount')return b.netPayable-a.netPayable||a.number.localeCompare(b.number)
    if(payrollSort==='contractor')return a.contractor.localeCompare(b.contractor)||a.number.localeCompare(b.number)
    const byPeriod=payrollPeriod(a).end.localeCompare(payrollPeriod(b).end)||a.number.localeCompare(b.number)
    return payrollSort==='old'?byPeriod:-byPeriod
  }),[mandorFilter,notes,query,statusFilter,payrollSort,workPeriod])
  const selected=visible.find((item)=>item.number===selectedNumber)??visible[0]??null
  function focus(id:string){setSelectedNumber(id);sessionStorage.setItem('erp.owner.payroll.focus',id);setPickOpen(null);setDebtOpen(false);setCreditsOpen(false);setSourceSelection(null);setNotice('')}
  function choose(number:string,add:boolean){if(!selected)return;try{setNotes(ns=>choosePayrollSource(ns,selected.number,number,add));setNotice(add?number+' ditambahkan ke pembayaran ini.':number+' dilepas. Bisa dipilih di pembayaran berikutnya.')}catch(e){setNotice((e as Error).message)}}
  const available=selected?availableSources(notes,selected):[]
  const choices = available.filter(source => {
    if (source.kind !== pickOpen) return false
    const { doc, day } = source
    return source.kind === 'FG'
      ? browseMatchPieces(sourceQuery, fgSourcePieces(source.doc), doc.number, source.doc.sku, day, doc.source)
      : browseMatchPieces(sourceQuery, accessorySourcePieces(source.doc), doc.number, source.doc.item, day, doc.source)
  })
  const currentMandor=normalizeMandor(selected?.contractor??'')
  const draftSources=[
    ...fgDrafts().map(d=>({number:d.number,mandor:d.mandor,kind:'FG',detail:(d.results.length+d.repairs.length)+' kartu',href:'/produksi/susun-nota-fg/?dari=payroll&draft='+encodeURIComponent(d.number)})),
    ...readIssueSources().filter(d=>d.status==='DRAFT').map(d=>({number:d.number,mandor:d.mandor,kind:'Aksesori',detail:d.lines.length+' baris',href:'/keuangan/nota-ambil-mandor/?dari=payroll&nota='+encodeURIComponent(d.number)}))
  ].filter(d=>normalizeMandor(d.mandor)===currentMandor)
  function rememberPayroll(){if(selected){sessionStorage.setItem('erp.owner.payroll.focus',selected.number);sessionStorage.setItem('erp.owner.payroll.mandor',selected.contractor)}}

  const fgTotal=selected?.fgNotes.reduce((sum,item)=>sum+fgNoteTotal(item),0)??0
  const fgRegularJobs=selected?.fgNotes.reduce((sum,item)=>sum+fgRegularCount(item),0)??0
  const fgRepairJobs=selected?.fgNotes.reduce((sum,item)=>sum+fgRepairCount(item),0)??0
  const accessoryTotal=selected?.accessoryNotes.reduce((sum,item)=>sum+item.total,0)??0
  const otherDeductions=selected?.deductions.reduce((sum,item)=>sum+item.amount,0)??0
  const mandorTotal=selected ? payrollDebtTotal(selected) : 0
  const mandorBills=selected ? mandorBillsForPayroll(salesInvoices,notes,selected) : []
  const accessoryCredits=selected?accessoryCreditsForPayroll(notes,selected):[]
  const accessoryCreditTotal=selected?payrollAccessoryCreditTotal(selected):0
  const linkedBalance=linkedInvoice && mandorDebtBalance(linkedInvoice,notes)
  const recomputed=Math.round((fgTotal+(selected?.attendance??0)+accessoryCreditTotal-accessoryTotal-otherDeductions-mandorTotal)*100)/100
  const calculationMatches=Boolean(selected
    && Math.round((fgTotal-selected.labor-selected.reimbursement)*100)===0
    && Math.round((accessoryTotal+otherDeductions+mandorTotal-selected.deduction)*100)===0
    && recomputed===selected.netPayable
    && validMandorDebts(salesInvoices,notes,selected))
  function changePayrollStatus(next:'REVIEW'|'APPROVED') {
    if (!selected) return false
    try {
      setNotes(current=>{
        const note=current.find(row=>row.number===selected.number)
        if (!note || note.status!==selected.status || !validMandorDebts(readInvoices(),current,note)) throw Error('Komposisi payroll berubah. Periksa lagi nota dan saldo piutangnya.')
        return current.map(row=>row===note ? {...row,status:next} : row)
      })
      return true
    } catch (failure) { setNotice((failure as Error).message);return false }
  }
  const activeNotes=notes.filter((item)=>!['PAID','REVERSED'].includes(item.status))
  const activeDeductions=activeNotes.reduce((sum,item)=>sum+item.deduction,0)
  const eligibleLines=activeNotes.reduce((sum,item)=>sum+item.eligibleLines,0)
  const readyToPay=notes.filter((item)=>item.status==='APPROVED').reduce((sum,item)=>sum+payrollRemaining(item),0)
  const remainingPay=selected?payrollRemaining(selected):0
  const subtotalPay=readRupiahInput(payAmount)
  const closingPayment=Number.isFinite(subtotalPay)&&subtotalPay===remainingPay
  function openPayment() {
    setPayReference('');setPayAmount(String(remainingPay).replace('.',','));setPayDay(lastWarehouseDay())
    setPaymentError('');setPayOpen(true);rememberPayroll()
  }
  function savePayment() {
    if(!selected)return
    try{
      const payment={id:crypto.randomUUID(),amount:subtotalPay,day:payDay,account:payAccount,reference:payReference.trim()}
      setNotes(current=>postPayrollPayment(current,readInvoices(),selected.number,payment))
      setPayOpen(false)
      setNotice(closingPayment?'Payroll periode ini lunas.'+ (mandorTotal ? ' Piutang berkurang '+money(mandorTotal)+'.' : '')
        : 'Pembayaran '+money(subtotalPay)+' tercatat. Sisa '+money(remainingPay-subtotalPay)+'.')
    }catch(failure){setPaymentError((failure as Error).message)}
  }
  function openPaymentReversal(id:string|null){
    setReversalId(id);setReason('');setPaymentError('');setReverseOpen(true)
  }
  function reversePayment(){
    if(!selected)return
    try{
      setNotes(current=>reversePayrollPayment(current,selected.number,reversalId,reason))
      setStatusFilter('Aktif · lunas disembunyikan');setReverseOpen(false)
      setNotice('Pembayaran dibalik. Saldo payroll diperbarui.')
    }catch(failure){setPaymentError((failure as Error).message)}
  }
  const sourceButton=(kind:'FG'|'ACCESSORY')=>selected&&editablePayroll(selected)&&<button type="button" className="soft-btn" onClick={()=>{
    setPickOpen(kind);setSourceQuery('');setNotice('')
  }}>{kind==='FG'?'Pilih nota FG':'Pilih nota aksesori'} ({available.filter(source=>source.kind===kind).length})</button>

  return <>
    <FinanceHero eyebrow="KEUANGAN · PAYROLL & SETTLEMENT" title="Payroll & Kasbon" description="Nota FG yang sudah posted berjajar sebagai sumber bayar. Absensi dan rate harian dikelola di halaman terpisah, lalu masuk ke sini sebagai snapshot posted." icon={UsersRound} action={<button className="primary-btn biz-hero-action" onClick={onAttendance}><CalendarDays/> Buka Absensi & Rate</button>}/>
    <section className="biz-metrics"><div className="panel"><span>NOTA TERBUKA</span><strong>{activeNotes.length}</strong><small>Draft sampai approved</small></div><div className="panel warn"><span>ELIGIBLE BELUM DITARIK</span><strong>{eligibleLines} baris</strong><small>Masuk nota berikutnya</small></div><div className="panel danger"><span>KASBON & POTONGAN</span><strong>{compactMoney(activeDeductions)}</strong><small>Aksesori aktual + koreksi</small></div><div className="panel good"><span>SIAP DIBAYAR</span><strong>{compactMoney(readyToPay)}</strong><small>Nota approved</small></div></section>
    <div className="owner-payroll-actions"><button type="button" className="primary-btn" onClick={()=>setCompose(true)}>Buat payroll untuk periode lain</button><button type="button" className="soft-btn" onClick={()=>{rememberPayroll();if(onOpenFg)onOpenFg();else location.assign('/produksi/susun-nota-fg/?dari=payroll')}}>Susun Nota FG</button>{selected&&<a className="gar-button" onClick={rememberPayroll} href={'/keuangan/nota-ambil-mandor/?dari=payroll&mandor='+encodeURIComponent(selected.contractor)}>Nota Ambil Aksesori</a>}</div>
    {linkedInvoice&&linkedBalance&&linkedBalance.available>0&&!mandorBills.some(bill=>bill.invoice.number===linkedInvoice.number)&&
      <div className="biz-guard"><WalletCards aria-hidden="true"/><span>Untuk potong tagihan {linkedInvoice.number} milik {linkedInvoice.customer}, pilih atau buat payroll dengan akhir periode sejak {linkedInvoice.day}.</span></div>}
    {selected&&<details className="panel owner-source-drafts"><summary>Draft nota sumber · {selected.contractor} ({draftSources.length})</summary>
      {draftSources.length?draftSources.map(d=><div className="owner-doc-row" key={d.number}><span><strong>{d.number} · {d.kind}</strong><small>{d.detail}</small></span><a className="gar-button" onClick={rememberPayroll} href={d.href}>Buka &amp; edit</a></div>):<p>Belum ada draft nota FG atau aksesori untuk mandor ini.</p>}</details>}
    {compose&&<ReasonDialog title="Buat payroll" closeLabel="Kembali" onClose={()=>setCompose(false)}><div className="sku-range-fields"><label>Mandor payroll<select value={mandor} onChange={e=>setMandor(e.target.value)}>{[...new Set([...mandorNames,...notes.map(n=>n.contractor),...allPayrollSources().map(s=>s.mandor)])].map(n=><option key={n}>{n}</option>)}</select></label><label>Mulai payroll<input type="date" value={from} onChange={e=>setFrom(e.target.value)}/></label><label>Akhir payroll<input type="date" value={until} onChange={e=>setUntil(e.target.value)}/></label></div><button className="primary-btn" disabled={!from||!until||from>until} onClick={()=>{const draft=newPayDraft(mandor,from,until);setNotes(ns=>ns.some(n=>n.number===draft.number)?ns:[draft,...ns]);setMandorFilter('Semua mandor');setStatusFilter('Semua status');setQuery('');focus(draft.number);setWorkPeriod(periodFor('all',from));setCompose(false)}}>Buka draft periode ini</button></ReasonDialog>}
    <section className="panel biz-payroll-browser-toolbar"><label className="biz-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari nota, mandor, periode..."/></label><EnterpriseSelect label="MANDOR" value={mandorFilter} options={mandorOptions} onChange={setMandorFilter}/><EnterpriseSelect label="STATUS" value={statusFilter} options={['Aktif · lunas disembunyikan','Semua status','Draft','Calculated','Review','Approved','Paid','Reversed']} onChange={setStatusFilter}/></section>
    <details className="panel owner-period-disclosure"><summary>Periode &amp; urutan payroll · {periodLabel(workPeriod)}</summary><PeriodFilter label="Periode kerja payroll" value={workPeriod} onChange={setWorkPeriod}/><label className="sku-range-field">Urutkan payroll<select value={payrollSort} onChange={e=>setPayrollSort(e.target.value)}><option value="recent">Periode terbaru</option><option value="old">Periode terlama</option><option value="amount">Jumlah bayar terbesar</option><option value="contractor">Nama mandor</option></select></label></details>
    <section className="panel biz-master-detail finance-detail payroll-detail"><BrowsePane aria-label="Daftar nota payroll"><header><div><span>PAYROLL BROWSER</span><strong>{visible.length} nota tampil</strong></div><UsersRound/></header><div className="biz-browser-list">{visible.map((item)=><button key={item.number} className={item.number===selected?.number?'active':''} onClick={()=>{focus(item.number);setPayReference('')}}><span>PY</span><div><strong>{item.number}</strong><small>{item.contractor}</small><em>{item.period}</em></div><b>{money(item.netPayable)}</b><Pill>{item.status}</Pill></button>)}{visible.length===0&&<div className="biz-empty"><Search/><strong>Nota tidak ditemukan</strong><small>Ubah filter mandor atau status.</small></div>}</div></BrowsePane>{selected?<main><header className="biz-detail-head"><div><span>NOTA PAYROLL · SOURCE LINKED</span><h2>{selected.number}</h2><p>{selected.contractor} · {selected.period}</p></div><Pill>{selected.status}</Pill></header>
      <div className="biz-payroll-source-summary"><article><ReceiptText/><span><small>TOTAL NOTA FG POSTED</small><strong>{money(fgTotal)}</strong><em>{selected.fgNotes.length} nota siap dihitung</em></span></article><article><FileSearch/><span><small>TOTAL NOTA AKSESORI</small><strong>{money(accessoryTotal)}</strong><em>{selected.accessoryNotes.length} nota kasbon</em></span></article><article><RefreshCcw/><span><small>KOMPOSISI PEKERJAAN</small><strong>{fgRegularJobs} FG · {fgRepairJobs} BG</strong><em>BS hanya ada di detail Nota FG</em></span></article><article className={calculationMatches?'good':'danger'}><ShieldCheck/><span><small>REKONSILIASI</small><strong>{calculationMatches?'Pas':'Tidak cocok'}</strong><em>Dokumen sumber → net payable</em></span></article></div>
      {pickOpen && editablePayroll(selected) && <ReasonDialog title={pickOpen === 'FG' ? 'Pilih nota FG' : 'Pilih nota aksesori'} closeLabel="Selesai" onClose={() => setPickOpen(null)}>
        <label>Cari nota, barang, atau jumlah pcs<input type="search" value={sourceQuery} onChange={event => setSourceQuery(event.target.value)}/></label>
        {choices.map(source => {
          const { doc } = source
          const isFg = source.kind === 'FG'
          const identity = isFg ? source.doc.sku : source.doc.item
          const amount = isFg ? fgNoteTotal(source.doc) : source.doc.total
          const detailPath = isFg ? '/produksi/susun-nota-fg/' : '/keuangan/nota-ambil-mandor/'
          const quantity = isFg ? source.doc.good.toLocaleString('id-ID') + ' pcs Good'
            : (source.doc.lines?.length ?? 0) <= 1 ? source.doc.qty.toLocaleString('id-ID') + ' ' + source.doc.unit : ''
          return <div className="owner-doc-row" key={doc.number}>
            <span><strong>{doc.number} · {isFg ? 'Nota FG' : 'Aksesori'}</strong>
              <small>{source.day} · {identity} · {quantity && <><b className="piece-total">{quantity}</b> · </>}{money(amount)}</small></span>
            {(isFg || readIssueSources().some(issue => issue.number === doc.number)) && <a className="gar-button" onClick={rememberPayroll}
              href={detailPath + '?dari=payroll&nota=' + encodeURIComponent(doc.number)}>Detail</a>}
            <button type="button" className="soft-btn" aria-label={'Tambahkan ' + doc.number} onClick={() => choose(doc.number, true)}>Tambahkan</button>
          </div>
        })}
        {!choices.length && <p>{sourceQuery ? 'Tidak ada nota yang cocok dengan pencarian.' : 'Semua nota jenis ini untuk mandor tersebut sudah dipilih.'}</p>}
        {notice && <p role="status">{notice}</p>}
      </ReasonDialog>}
      <section className="biz-payroll-documents compact payroll-source-block" aria-labelledby="payroll-sources-title">
        <header><div><h3 id="payroll-sources-title">Nota untuk pembayaran ini</h3><small>Nota yang dilepas bisa dipilih lagi di periode berikutnya.</small></div></header>
        <div className="biz-payroll-compact-groups payroll-source-grid">
          <section className="payroll-source-fg" aria-labelledby="payroll-fg-title">
            <header><i><ReceiptText aria-hidden="true"/></i><div><h4 id="payroll-fg-title">Nota FG</h4><small>{selected.fgNotes.length} nota posted</small></div><strong>{money(fgTotal)}</strong></header>
            <div className="payroll-source-items">{selected.fgNotes.map(item=><div className="owner-pay-source" key={item.number}>
              <button type="button" onClick={()=>setSourceSelection({kind:'FG',number:item.number})}><ReceiptText/><span><strong>{item.number}</strong><small>{item.date} · {item.sku}</small></span><em>{fgRegularCount(item)} FG Reguler · {fgRepairCount(item)} Bikin Bagus</em><b>{money(fgNoteTotal(item))}</b><ArrowRight/></button>
              {editablePayroll(selected)&&<button type="button" className="soft-btn owner-remove" aria-label={'Lepas '+item.number} onClick={()=>choose(item.number,false)}>Lepas dari pembayaran</button>}
            </div>)}{!selected.fgNotes.length&&<p>Belum ada nota FG dipilih.</p>}</div>
            {editablePayroll(selected)&&<footer>{sourceButton('FG')}</footer>}
          </section>
          <section className="payroll-source-accessory" aria-labelledby="payroll-accessory-title">
            <header><i><FileSearch aria-hidden="true"/></i><div><h4 id="payroll-accessory-title">Nota Aksesori</h4><small>{selected.accessoryNotes.length} nota kasbon</small></div><strong>{money(accessoryTotal)}</strong></header>
            <div className="payroll-source-items">{selected.accessoryNotes.map(item=><div className="owner-pay-source" key={item.number}>
              <button type="button" onClick={()=>setSourceSelection({kind:'ACCESSORY',number:item.number})}><FileSearch/><span><strong>{item.number}</strong><small>{item.date} · {item.item}</small></span><em>{item.qty.toLocaleString('id-ID')} {item.unit}</em><b>{money(item.total)}</b><ArrowRight/></button>
              {editablePayroll(selected)&&<button type="button" className="soft-btn owner-remove" aria-label={'Lepas '+item.number} onClick={()=>choose(item.number,false)}>Lepas dari pembayaran</button>}
            </div>)}{!selected.accessoryNotes.length&&<p>Belum ada nota aksesori dipilih.</p>}</div>
            {editablePayroll(selected)&&<footer>{sourceButton('ACCESSORY')}</footer>}
          </section>
        </div>
      </section>
      <section className="mandor-debt-panel" aria-labelledby="payroll-mandor-debt-title">
        <header><WalletCards aria-hidden="true"/><div><h3 id="payroll-mandor-debt-title">Potongan piutang mandor</h3><p>Invoice belanja dari Penjualan yang dipilih untuk periode ini.</p></div><strong>{money(mandorTotal)}</strong></header>
        {selected.mandorDebts?.length ? <ul className="mandor-payroll-sources">{selected.mandorDebts.map(debt=><li key={debt.invoice}>
          <a href={'/penjualan/semua-invoice/?nota='+encodeURIComponent(debt.invoice)}>{debt.invoice} <ArrowRight/></a><b>{money(debt.amount)}</b>
        </li>)}</ul> : null}
        {editablePayroll(selected)&&<button type="button" className="soft-btn" onClick={()=>setDebtOpen(true)}>Pilih piutang mandor ({mandorBills.length}) <ArrowRight/></button>}
      </section>
      {debtOpen&&editablePayroll(selected)&&<MandorDebtPicker key={selected.number} note={selected} bills={mandorBills} linked={debtLink.get('piutang')} onClose={()=>setDebtOpen(false)}
        onChoose={(invoice,amount)=>{
          setNotes(current=>chooseMandorDebt(readInvoices(),current,selected.number,invoice,amount))
          setDebtOpen(false)
          setNotice(amount>0?money(amount)+' dialokasikan ke payroll periode ini.':'Potongan dilepas. Saldo bisa dipilih di periode lain.')
        }}/>}
      {(accessoryCredits.length>0||accessoryCreditTotal>0)&&<section className="mandor-debt-panel" id="kredit-retur-payroll" aria-label="Kredit retur aksesori">
        <header><ReceiptText aria-hidden="true"/><div><h3>Kredit retur aksesori</h3><p>Kelebihan retur dari nota yang sudah dibayar.</p></div><strong>{money(accessoryCreditTotal)}</strong></header>
        {!!selected.accessoryCredits?.length&&<ul className="mandor-payroll-sources">{selected.accessoryCredits.map(credit=><li key={credit.id}>
          <a href={'/keuangan/nota-ambil-mandor/?nota='+encodeURIComponent(credit.note)}>{credit.note} <ArrowRight/></a><b>+ {money(credit.amount)}</b></li>)}</ul>}
        {editablePayroll(selected)&&<button type="button" className="soft-btn" onClick={()=>setCreditsOpen(true)}>Pilih kredit retur ({accessoryCredits.length})</button>}
      </section>}
      {creditsOpen&&editablePayroll(selected)&&<ReasonDialog title="Pilih kredit retur aksesori" closeLabel="Selesai" onClose={()=>setCreditsOpen(false)} className="demo-operation-dialog">
        <div className="demo-operation-form"><p>{selected.contractor} · {selected.period}</p>
          {accessoryCredits.map(credit=>{
            const included=selected.accessoryCredits?.some(row=>row.id===credit.id)
            return <section className="demo-ops-card" key={credit.id}><div className="demo-ops-header"><div><strong>{money(credit.amount)}</strong><small>{credit.note} · {credit.day}</small></div>
              <button type="button" className="soft-btn" onClick={()=>{
                try{setNotes(current=>chooseAccessoryCredit(current,selected.number,credit.id,!included));setNotice(included?'Kredit dilepas.':'Kredit ditambahkan ke payroll.')}
                catch(failure){setNotice((failure as Error).message)}
              }}>{included?'Lepas kredit':'Tambahkan kredit'}</button></div></section>
          })}
          {notice&&<p role="status">{notice}</p>}
        </div>
      </ReasonDialog>}
      <section className="biz-payroll-calculation"><header><div><span>03 · REKONSILIASI PAYROLL</span><strong>Hitung dari dokumen sumber yang sudah posted</strong></div><span>{selected.number}</span></header><div className="biz-payroll-calculation-lines"><article className="positive"><span><strong>Total Nota FG</strong><small>Upah jahit + BOM + komisi, termasuk Bikin Bagus</small></span><b>+ {money(fgTotal)}</b></article><article className="positive"><span><strong>Attendance eligible</strong><small>Hanya pekerja yang memang wajib attendance</small></span><b>+ {money(selected.attendance)}</b></article><article className="negative"><span><strong>Total Nota Ambil Aksesori</strong><small>{selected.accessoryNotes.map((item)=>item.number).join(' · ')}</small></span><b>− {money(accessoryTotal)}</b></article>{selected.deductions.map((item)=><article className="negative" key={item.label}><span><strong>{item.label}</strong><small>{item.reference}</small></span><b>− {money(item.amount)}</b></article>)}{mandorTotal>0&&<article className="negative"><span><strong>Potongan piutang mandor</strong><small>{selected.mandorDebts?.length} invoice belanja</small></span><b>− {money(mandorTotal)}</b></article>}{accessoryCreditTotal>0&&<article className="positive"><span><strong>Kredit retur aksesori</strong><small>{selected.accessoryCredits?.length} retur layak bayar</small></span><b>+ {money(accessoryCreditTotal)}</b></article>}<footer><span><small>NET PAYABLE</small><strong>{money(recomputed)}</strong></span><div><small>ELIGIBLE BELUM DITARIK</small><strong>{selected.eligibleLines} baris</strong></div><div><small>RENCANA BAYAR</small><strong>{selected.paymentDate}</strong></div></footer></div></section>
      {selected.eligibleLines>0&&<div className="biz-guard warn"><AlertTriangle/><span>{selected.eligibleLines} baris eligible belum masuk nota. Penarikan harus atomic dan idempotent; payroll tidak boleh menebak dari frontend.</span></div>}
      {(selected.status==='APPROVED'||selected.status==='PAID'||selected.payments?.length)&&
        <section className="mandor-debt-panel" id="pembayaran-payroll" aria-label="Pembayaran payroll">
          <header><Banknote aria-hidden="true"/><div><h3>Pembayaran payroll</h3><p>Lihat saldo setelah setiap pembayaran.</p></div></header>
          <dl className="mandor-debt-balances"><div><dt>Sudah dibayar</dt><dd>{money(payrollPaid(selected))}</dd></div><div><dt>Sisa bayar</dt><dd>{money(remainingPay)}</dd></div></dl>
          {!!selected.payments?.length&&<ul className="mandor-payroll-sources">{selected.payments.map(payment=><li key={payment.id}>
            <span><b>{money(payment.amount)}</b> · {payment.day} · {payment.reference}{payment.reversed?' · Dibalik: '+payment.reversed:''}</span>
            {!payment.reversed&&<button type="button" className="soft-btn" onClick={()=>openPaymentReversal(payment.id)}>Balikkan {payment.reference}</button>}
          </li>)}</ul>}
        </section>}
      <section className="biz-payroll-rules"><article><Check/><span><strong>Selesai Dijahit menjadi dasar</strong><small>Stuck tidak menghapus hak jahit; hanya komponen yang belum dipasang yang ditahan. Good hanya menentukan stok FG.</small></span></article><article><Check/><span><strong>Checkbox hanya di Bikin Bagus</strong><small>Tarif komponen terpilih menjadi pengurang BS sekaligus batas pembayaran rework.</small></span></article><article><Check/><span><strong>BS melekat pada pekerjaan asal</strong><small>Pengurang sudah ada di Nota FG dan tidak menjadi potongan Payroll kedua kali.</small></span></article><article><Check/><span><strong>Kasbon aksesori tetap barang detail</strong><small>Stok dan HPP memakai moving average; harga mandor memakai snapshot tersendiri.</small></span></article></section>{notice&&<div className="biz-inline-notice"><CheckCircle2/> {notice}</div>}<footer className="biz-detail-actions"><button className="soft-btn" disabled={selected.status!=='PAID'} onClick={()=>openPaymentReversal(selected.payments?.filter(payment=>!payment.reversed).at(-1)?.id??null)}><Undo2/> Reverse payment</button>{editablePayroll(selected)&&<button className="soft-btn" disabled={!calculationMatches||recomputed<0||!selected.fgNotes.length&&!selected.accessoryNotes.length} onClick={()=>{if(changePayrollStatus(selected.status==='REVIEW'?'APPROVED':'REVIEW'))setNotice(selected.status==='REVIEW'?'Payroll disetujui.':'Komposisi siap ditinjau.')}}>{selected.status==='REVIEW'?'Setujui payroll':'Review pembayaran ini'}</button>}<button className="primary-btn" disabled={selected.status!=='APPROVED'||!calculationMatches} onClick={openPayment}><Banknote/> Bayar nota</button></footer></main>:<main className="biz-empty payroll"><Search/><strong>Tidak ada detail payroll</strong><small>Sesuaikan filter di atas.</small></main>}</section>
    {sourceSelection&&selected&&<PayrollSourceModal selection={sourceSelection} note={selected} onRelease={editablePayroll(selected)?()=>{choose(sourceSelection.number,false);setSourceSelection(null)}:undefined} onClose={()=>setSourceSelection(null)}/>}
    {payOpen&&selected&&<FinanceModal title="Bayar nota payroll?" description="Catat seluruh sisa atau isi sebagian pembayaran periode ini." onClose={()=>setPayOpen(false)}
      action={savePayment} disabled={!payReference.trim()||!dayOk(payDay)||!Number.isFinite(subtotalPay)||subtotalPay<0||subtotalPay>remainingPay||subtotalPay===0&&remainingPay>0}>
      <div className="biz-payment-form">
        <label><span>JUMLAH DIBAYAR</span><NumberEntry rupiahDraft inputMode="decimal" aria-label="Jumlah pembayaran gaji" value={payAmount} onValueChange={rawInput =>setPayAmount(rawInput)}/></label>
        <EnterpriseSelect label="AKUN BAYAR" value={payAccount} options={['Mandiri Payroll','BCA Operasional','Kas Utama']} onChange={setPayAccount}/>
        <label><span>TANGGAL BAYAR</span><input type="date" max={lastWarehouseDay()} value={payDay} onChange={event=>setPayDay(event.target.value)}/></label>
        <label><span>REFERENSI</span><input value={payReference} onChange={event=>setPayReference(event.target.value)} placeholder="Nomor transfer / bukti"/></label>
      </div>
      <div className="biz-impact-grid">
        <article><span>Sisa sebelum bayar</span><strong>{money(remainingPay)}</strong><small>{selected.number}</small></article>
        <article><span>Kas / bank keluar</span><strong>{Number.isFinite(subtotalPay)?money(subtotalPay):'—'}</strong><small>{payAccount}</small></article>
        <article><span>Sisa sesudah bayar</span><strong>{Number.isFinite(subtotalPay)&&subtotalPay<=remainingPay?money(remainingPay-subtotalPay):'—'}</strong><small>{closingPayment?'Lunas':'Pembayaran sebagian'}</small></article>
        {mandorTotal>0&&closingPayment&&<article><span>Piutang mandor dilunasi</span><strong>{money(mandorTotal)}</strong><small>Potongan yang sudah dipilih</small></article>}
      </div>
      {paymentError&&<p role="alert">{paymentError}</p>}
    </FinanceModal>}
    {reverseOpen&&selected&&<FinanceModal danger title="Reverse pembayaran payroll?" description="Pembayaran asal tetap tampil. Sisa dibayar dikembalikan ke payroll periode ini." onClose={()=>setReverseOpen(false)}
      action={reversePayment} actionLabel="Review reversal" disabled={!reason.trim()}>
      <label className="biz-wide-field"><span>ALASAN REVERSAL · WAJIB</span><textarea value={reason} onChange={event=>setReason(event.target.value)} placeholder="Jelaskan salah akun, salah nominal, atau salah penerima…"/></label>
      {paymentError&&<p role="alert">{paymentError}</p>}
    </FinanceModal>}

  </>
}

function JournalWorkspace() {
  const [tab,setTab]=useState<'misc'|'journal'>('misc')
  const [type,setType]=useState('OTHER_EXPENSE')
  const [amount,setAmount]=useState('485000')
  const [account,setAccount]=useState('Kas Utama')
  const [counterparty,setCounterparty]=useState('Toko ATK Jaya')
  const [reference,setReference]=useState('NOTA-ATK-2808')
  const [notes,setNotes]=useState('Alat tulis kantor')
  const [reviewOpen,setReviewOpen]=useState(false)
  const [selectedJournal,setSelectedJournal]=useState(journals[0].number)
  const [query,setQuery]=useState('')
  const [reverseOpen,setReverseOpen]=useState(false)
  const [reverseReason,setReverseReason]=useState('')
  const [notice,setNotice]=useState('')
  const typedAmount=Math.max(0,Number(amount.replace(/\D/g,''))||0)
  const visible=journals.filter((item)=>`${item.number} ${item.source} ${item.description}`.toLowerCase().includes(query.toLowerCase()))
  const selected=journals.find((item)=>item.number===selectedJournal)??journals[0]
  return <>
    <FinanceHero eyebrow="KEUANGAN · JOURNAL GATEWAY" title="Jurnal & Transaksi Lain-lain" description="Owner boleh mencatat pemasukan/pengeluaran non-inti lewat kategori aman. Jurnal sale, purchase, laundry, payroll, dan stok hanya dibaca di sini—bukan diedit manual." icon={FileClock}/>
    <nav className="panel biz-workspace-tabs"><button className={tab==='misc'?'active':''} onClick={()=>setTab('misc')}><Banknote/> Pendapatan / pengeluaran lain</button><button className={tab==='journal'?'active':''} onClick={()=>setTab('journal')}><FileSearch/> Browser jurnal</button></nav>
    {tab==='misc'?<section className="biz-misc-layout"><div className="panel biz-misc-form"><header><div><span>TRANSAKSI NON-INTI</span><strong>{type==='OTHER_INCOME'?'Pendapatan Lain-lain':'Pengeluaran Lain-lain'}</strong><small>Jangan dipakai untuk bypass sale, AP, payroll, inventory, atau HPP.</small></div><Pill tone="warn">DRAFT</Pill></header><div className="biz-kind-choice"><button className={type==='OTHER_INCOME'?'active good':''} onClick={()=>setType('OTHER_INCOME')}><TrendingUp/><span><strong>Pendapatan lain-lain</strong><small>Uang masuk non-core</small></span></button><button className={type==='OTHER_EXPENSE'?'active danger':''} onClick={()=>setType('OTHER_EXPENSE')}><TrendingDown/><span><strong>Pengeluaran lain-lain</strong><small>Uang keluar non-core</small></span></button></div><div className="biz-payment-form misc"><label><span>WAKTU FISIK</span><input type="datetime-local" defaultValue="2026-08-28T11:00"/></label><label><span>JUMLAH</span><div><b>Rp</b><NumberEntry inputMode="numeric" value={amount} onValueChange={rawInput =>setAmount(cleanMoneyInput(rawInput))}/></div></label><label><span>AKUN KAS / BANK</span><select value={account} onChange={(event)=>setAccount(event.target.value)}>{cashAccounts.map((item)=><option key={item.code}>{item.name}</option>)}</select></label><label><span>LAWAN TRANSAKSI</span><input value={counterparty} onChange={(event)=>setCounterparty(event.target.value)} placeholder="Nama pihak"/></label><label><span>REFERENSI</span><input value={reference} onChange={(event)=>setReference(event.target.value)} placeholder="Nomor nota / bukti"/></label></div><label className="biz-wide-field"><span>ALASAN & CATATAN</span><textarea value={notes} onChange={(event)=>setNotes(event.target.value)} placeholder="Tujuan transaksi dan alasan klasifikasi..."/></label><div className="biz-guard"><ShieldCheck/><span>Backend tetap membuat double-entry journal. User tidak memilih akun debit/kredit manual dari flow ini.</span></div>{notice&&<div className="biz-inline-notice"><CheckCircle2/> {notice}</div>}<button className="primary-btn" disabled={typedAmount<=0||!counterparty.trim()||!reference.trim()||!notes.trim()} onClick={()=>setReviewOpen(true)}>Review transaksi <ArrowRight/></button></div><aside className="panel biz-misc-preview"><span>JOURNAL PREVIEW</span><h2>{money(typedAmount)}</h2><p>{type==='OTHER_INCOME'?'Uang masuk':'Uang keluar'} · {account}</p><div><article><small>DEBIT</small><strong>{type==='OTHER_INCOME'?account:'Pengeluaran lain-lain'}</strong><b>{money(typedAmount)}</b></article><article><small>CREDIT</small><strong>{type==='OTHER_INCOME'?'Pendapatan lain-lain':account}</strong><b>{money(typedAmount)}</b></article></div><footer><Check/> Debit = credit · preview only</footer></aside></section>:<JournalBrowser visible={visible} query={query} setQuery={setQuery} selected={selected} setSelectedJournal={setSelectedJournal} setReverseOpen={setReverseOpen}/>}
    {reviewOpen&&<FinanceModal title="Transaksi lain-lain siap direview" description="Gunakan hanya untuk transaksi non-core yang benar-benar terjadi." onClose={()=>setReviewOpen(false)} action={()=>{setReviewOpen(false);setNotice('Simulasi transaksi tersimpan. Kas dan backend belum berubah.')}}><div className="biz-impact-grid"><article><span>Jenis</span><strong>{type==='OTHER_INCOME'?'Pendapatan':'Pengeluaran'}</strong><small>Lain-lain</small></article><article><span>Jumlah</span><strong>{money(typedAmount)}</strong><small>{account}</small></article><article><span>Referensi</span><strong>{reference}</strong><small>{counterparty}</small></article></div></FinanceModal>}
    {reverseOpen&&<FinanceModal danger title="Reverse jurnal sumber?" description="Reversal membuat entry berlawanan; jurnal posted tidak diedit atau dihapus." onClose={()=>setReverseOpen(false)} action={()=>{setReverseOpen(false);setNotice('Simulasi reversal tersimpan. Backend belum berubah.')}} actionLabel="Review reversal" disabled={!reverseReason.trim()}><div className="biz-guard danger"><AlertTriangle/><span>{selected.number} · {selected.description} · {money(selected.debit)}</span></div><label className="biz-wide-field"><span>ALASAN REVERSAL · WAJIB</span><textarea value={reverseReason} onChange={(event)=>setReverseReason(event.target.value)} placeholder="Dokumen sumber mana yang salah dan kenapa harus dibalik?"/></label></FinanceModal>}
  </>
}

function JournalBrowser({visible,query,setQuery,selected,setSelectedJournal,setReverseOpen}:{visible:JournalEntry[];query:string;setQuery:(value:string)=>void;selected:JournalEntry;setSelectedJournal:(value:string)=>void;setReverseOpen:(value:boolean)=>void}) {
  return <section className="panel biz-master-detail finance-detail"><BrowsePane aria-label="Daftar jurnal"><header><div><span>JOURNAL BROWSER</span><strong>{visible.length} entry</strong></div><FileSearch/></header><label className="biz-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari nomor, sumber, deskripsi..."/></label><div className="biz-browser-list">{visible.map((item)=><button key={item.number} className={item.number===selected.number?'active':''} onClick={()=>setSelectedJournal(item.number)}><span>JR</span><div><strong>{item.number}</strong><small>{item.source.replaceAll('_',' ')}</small><em>{item.glDate}</em></div><b>{money(item.debit)}</b><Pill>{item.status}</Pill></button>)}</div></BrowsePane><main><header className="biz-detail-head"><div><span>{selected.source.replaceAll('_',' ')}</span><h2>{selected.number}</h2><p>{selected.description}</p></div><Pill>{selected.status}</Pill></header><div className="biz-date-audit"><article><CalendarClock/><span><small>TANGGAL EKONOMI</small><strong>{selected.economicDate}</strong><em>Kejadian sebenarnya</em></span></article><article><FileClock/><span><small>GL DATE</small><strong>{selected.glDate}</strong><em>{selected.shifted?'Digeser ke periode terbuka':'Sama dengan kejadian'}</em></span></article><article><ShieldCheck/><span><small>DOUBLE ENTRY</small><strong>{money(selected.debit)}</strong><em>Debit = credit</em></span></article></div>{selected.shifted&&<div className="biz-guard warn"><CalendarClock/><span>Tanggal ekonomi tetap {selected.economicDate}, tetapi GL date {selected.glDate} karena periode lama tidak boleh ditulis ulang.</span></div>}<div className="biz-journal-lines"><div><span>Akun</span><span>Keterangan</span><span>Debit</span><span>Kredit</span></div>{selected.lines.map((line)=><article key={`${line.account}-${line.description}`}><strong>{line.account}</strong><span>{line.description}</span><b>{line.debit?money(line.debit):'—'}</b><b>{line.credit?money(line.credit):'—'}</b></article>)}<footer><span>TOTAL</span><span/><strong>{money(selected.debit)}</strong><strong>{money(selected.credit)}</strong></footer></div><div className="biz-guard"><LockKeyhole/><span>Jurnal ini read-only. Koreksi dimulai dari transaksi sumber; reversal jurnal menjaga jejak dan tidak memutus subledger.</span></div><footer className="biz-detail-actions"><span>{selected.status==='REVERSED'?'Entry sudah punya reversal.':'Posted entry tidak bisa diedit.'}</span><button className="soft-btn" disabled={selected.status==='REVERSED'} onClick={()=>setReverseOpen(true)}><Undo2/> Review reversal</button></footer></main></section>
}

function ReportsWorkspace() {
  const [period,setPeriod]=useState('2026-08')
  const [report,setReport]=useState<'profit-loss'|'position'|'cashflow'|'aging'>('profit-loss')
  const [closeOpen,setCloseOpen]=useState(false)
  const [reason,setReason]=useState('')
  const [notice,setNotice]=useState('')
  const hasBlock=closeChecks.some((item)=>item.severity==='BLOCK'&&item.count>0)
  return <>
    <FinanceHero eyebrow="KEUANGAN · REPORTING & PERIOD CONTROL" title="Laporan & Tutup Buku" description="Laporan owner menampilkan angka sekaligus tingkat kepercayaannya. Tutup buku hanya berjalan setelah recost, jurnal, draft lama, dan rekonsiliasi kritis bersih." icon={NotebookTabs}/>
    <section className="panel biz-report-controls"><label><span>PERIODE</span><input type="month" value={period} onChange={(event)=>setPeriod(event.target.value)}/></label><nav>{[{key:'profit-loss',label:'Laba Rugi'},{key:'position',label:'Posisi Keuangan'},{key:'cashflow',label:'Arus Kas'},{key:'aging',label:'Aging AR/AP'}].map((item)=><button key={item.key} className={report===item.key?'active':''} onClick={()=>setReport(item.key as typeof report)}>{item.label}</button>)}</nav><div><Pill tone="warn">PROVISIONAL</Pill><button className="primary-btn" onClick={()=>setCloseOpen(true)}><LockKeyhole/> Tutup buku</button></div></section>
    <section className="biz-report-layout"><main className="panel biz-report-sheet"><header><div><span>PERIODE AGUSTUS 2026</span><h2>{report==='profit-loss'?'Laporan Laba Rugi':report==='position'?'Laporan Posisi Keuangan':report==='cashflow'?'Laporan Arus Kas':'Aging Piutang & Hutang'}</h2><p>Generated 28 Agu 2026 · 11:24 · basis jurnal posted</p></div><Pill tone="warn">BELUM FINAL</Pill></header>{report==='profit-loss'?<ProfitLoss/>:report==='position'?<FinancialPosition/>:report==='cashflow'?<CashFlow/>:<Aging/>}<footer><ShieldCheck/><span><strong>Traceable ke transaksi sumber</strong><small>Klik baris pada versi live nanti untuk drill-down jurnal → source document → stock/HPP lineage.</small></span></footer></main><aside className="panel biz-close-gate"><header><div><span>CLOSE GATE</span><strong>Agustus belum boleh ditutup</strong></div><ShieldAlert/></header><div>{closeChecks.map((item)=><article key={item.label} className={item.severity.toLowerCase()}><i>{item.count===0?<Check/>:item.severity==='BLOCK'?<X/>:<AlertTriangle/>}</i><span><strong>{item.label}</strong><small>{item.count===0?'Bersih':`${item.count} temuan`}</small></span><Pill>{item.severity}</Pill></article>)}</div><section><span>TINGKAT KEPERCAYAAN</span><strong>82%</strong><div><i style={{width:'82%'}}/></div><small>Margin masih bisa berubah karena satu recost dan tiga GRNI.</small></section>{notice&&<div className="biz-inline-notice"><CheckCircle2/> {notice}</div>}<button className="primary-btn" disabled={hasBlock} onClick={()=>setCloseOpen(true)}><LockKeyhole/> Tutup periode</button><small className="biz-block-note">1 blocker harus nol. Warning boleh dioverride Owner dengan alasan, tetapi tidak boleh hilang dari audit.</small></aside></section>
    {closeOpen&&<FinanceModal danger title="Review tutup buku Agustus" description="Periode tertutup tidak boleh menerima backdate GL. Late invoice tetap memakai tanggal ekonomi asli dan GL date periode terbuka." onClose={()=>setCloseOpen(false)} action={()=>{setCloseOpen(false);setNotice('Tutup buku belum dijalankan. Simulasi review tersimpan di layar.')}} actionLabel="Tutup periode" disabled={hasBlock||!reason.trim()}><div className="biz-close-summary"><article><span>BLOCKER</span><strong>{closeChecks.filter((item)=>item.severity==='BLOCK').reduce((sum,item)=>sum+item.count,0)}</strong><small>Harus nol</small></article><article><span>WARNING</span><strong>{closeChecks.filter((item)=>item.severity==='WARNING').reduce((sum,item)=>sum+item.count,0)}</strong><small>Perlu alasan Owner</small></article><article><span>STATUS</span><strong>{hasBlock?'BLOCKED':'READY'}</strong><small>{period}</small></article></div><label className="biz-wide-field"><span>ALASAN / CATATAN CLOSE</span><textarea value={reason} onChange={(event)=>setReason(event.target.value)} placeholder="Jelaskan warning yang diterima atau tindak lanjut..."/></label>{hasBlock&&<div className="biz-guard danger"><RefreshCcw/><span>Cost recalc masih PENDING. Tutup periode diblokir supaya HPP, COGS, laba, inventory, dan SOFP tidak dikunci dalam keadaan salah.</span></div>}</FinanceModal>}
  </>
}

function ReportRows({rows}:{rows:Array<{label:string;value:number;sub?:boolean;total?:boolean;negative?:boolean;note?:string}>}) {
  return <div className="biz-report-rows">{rows.map((row)=><article key={row.label} className={`${row.sub?'sub':''} ${row.total?'total':''}`}><span>{row.label}{row.note&&<small>{row.note}</small>}</span><strong className={row.negative?'negative':''}>{row.negative?'− ':''}{money(Math.abs(row.value))}</strong></article>)}</div>
}
function ProfitLoss(){return <><ReportRows rows={[{label:'Penjualan bruto',value:august.grossSales},{label:'Retur & potongan penjualan',value:august.returns,sub:true,negative:true},{label:'Penjualan bersih',value:augustNetSales,total:true},{label:'HPP bahan & aksesori',value:191_400_000,sub:true,negative:true},{label:'HPP tenaga kerja & komisi',value:49_600_000,sub:true,negative:true},{label:'HPP laundry, rework & konversi',value:31_900_000,sub:true,negative:true},{label:'Total HPP',value:august.cogs,total:true,negative:true,note:'Provisional · recost pending'},{label:'Laba kotor',value:augustGrossProfit,total:true},{label:'Beban operasional',value:august.operating,negative:true},{label:'Pendapatan / pengeluaran lain bersih',value:august.otherNet},{label:'Laba bersih sebelum pajak',value:augustNetProfit,total:true}]}/></>}
function FinancialPosition(){
  // Liabilities come from the same AP/GRNI/payroll records the workspaces show;
  // equity is the balancing remainder of the static demo asset total.
  const supplier=payables.filter((item)=>item.kind!=='MATERIAL_GRNI').reduce((sum,item)=>sum+outstandingPayable(item),0)
  const grniOpen=payables.filter((item)=>item.kind==='MATERIAL_GRNI').reduce((sum,item)=>sum+outstandingPayable(item),0)
  const payrollOpen=payrollNotes.filter((item)=>!['PAID','REVERSED'].includes(item.status)).reduce((sum,item)=>sum+item.netPayable,0)
  const assets=1_216_260_000,liabilities=supplier+grniOpen+payrollOpen
  return <div className="biz-position-grid"><section><span>ASET</span><ReportRows rows={[{label:'Kas & bank',value:284_600_000},{label:'Piutang pelanggan',value:14_260_000},{label:'Persediaan bahan',value:312_400_000},{label:'WIP produksi',value:186_800_000},{label:'Persediaan FG',value:418_200_000,note:'Provisional karena recost'},{label:'Total aset',value:assets,total:true}]}/></section><section><span>LIABILITAS & EKUITAS</span><ReportRows rows={[{label:'Hutang supplier & vendor',value:supplier},{label:'GRNI sementara',value:grniOpen},{label:'Payroll payable',value:payrollOpen},{label:'Total liabilitas',value:liabilities,total:true},{label:'Modal & laba ditahan',value:assets-liabilities-augustNetProfit},{label:'Laba periode berjalan',value:augustNetProfit},{label:'Total liabilitas & ekuitas',value:assets,total:true}]}/></section></div>}
function CashFlow(){return <ReportRows rows={[{label:'Penerimaan pelanggan',value:287_500_000},{label:'Pembayaran supplier & vendor',value:126_400_000,negative:true},{label:'Pembayaran payroll',value:64_800_000,negative:true},{label:'Pengeluaran operasional lain',value:21_350_000,negative:true},{label:'Arus kas operasi bersih',value:74_950_000,total:true},{label:'Arus kas investasi',value:4_800_000,negative:true},{label:'Kenaikan bersih kas',value:70_150_000,total:true},{label:'Kas awal periode',value:214_450_000},{label:'Kas akhir periode',value:284_600_000,total:true}]}/>} 
function Aging(){return <div className="biz-aging"><header><span>PIHAK</span><span>CURRENT</span><span>1–30 HARI</span><span>31–90 HARI</span><span>&gt;90 HARI</span><span>TOTAL</span></header><article><strong>Toko Maju Jaya<small>AR</small></strong><span>Rp2,8 jt</span><span>Rp1,9 jt</span><span>—</span><span>—</span><b>Rp4,7 jt</b></article><article><strong>Sentra Denim<small>AR</small></strong><span>—</span><span>Rp5,7 jt</span><span>—</span><span>—</span><b>Rp5,7 jt</b></article><article><strong>CV Sinar Textile<small>AP + GRNI</small></strong><span>Rp32,8 jt</span><span>—</span><span>—</span><span className="negative">Rp26,9 jt</span><b>Rp59,7 jt</b></article><article><strong>Laundry Tirta<small>AP</small></strong><span>Rp8,5 jt</span><span>—</span><span>—</span><span>—</span><b>Rp8,5 jt</b></article></div>}

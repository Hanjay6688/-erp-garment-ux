import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowLeft, ArrowRight, Check, FileCheck2, FileClock,
  Link2, LockKeyhole, ReceiptText, RefreshCcw, ShieldCheck, X,
} from 'lucide-react'
import './supplier-invoice-match.css'

type ReceiptLine = {
  id:string
  receipt:string
  receivedAt:string
  purchaseItemId:string
  item:string
  unit:string
  received:number
  invoiced:number
  estimatedUnitPrice:number
}

type DraftLine = {selected:boolean;qty:string;price:string;discount:string}
export type SupplierInvoiceMatchResult = {kind:'DRAFT'|'POSTED';invoiceNumber:string;amount:number;receiptCount:number;partial:boolean}

type Props = {
  grniNumber:string
  supplier:string
  purchaseReference:string
  estimatedAmount:number
  onClose:()=>void
  onSaved:(result:SupplierInvoiceMatchResult)=>void
}

const receiptLines:ReceiptLine[] = [
  {id:'line-0098-01',receipt:'RCV-RM-260826-0098',receivedAt:'26 Agu 2026 · 09:42',purchaseItemId:'PUR-ITEM-0098-01',item:'Kain Lucy · Navy',unit:'yard',received:360,invoiced:40,estimatedUnitPrice:51_500},
  {id:'line-0101-01',receipt:'RCV-RM-260827-0101',receivedAt:'27 Agu 2026 · 11:18',purchaseItemId:'PUR-ITEM-0101-01',item:'Kain Lucy · Maroon',unit:'yard',received:300,invoiced:0,estimatedUnitPrice:54_000},
]

const money=(value:number)=>new Intl.NumberFormat('id-ID',{style:'currency',currency:'IDR',maximumFractionDigits:0}).format(value)
const digits=(value:string)=>Math.max(0,Number(value.replace(/\D/g,''))||0)

export default function SupplierInvoiceMatchModal({grniNumber,supplier,purchaseReference,estimatedAmount,onClose,onSaved}:Props) {
  const [phase,setPhase]=useState<'edit'|'review'>('edit')
  const [invoiceNumber,setInvoiceNumber]=useState('INV-ST-8902')
  const [invoiceDate,setInvoiceDate]=useState('2026-08-27')
  const [receivedDate,setReceivedDate]=useState('2026-08-28')
  const [dueDate,setDueDate]=useState('2026-09-27')
  const [note,setNote]=useState('Invoice final diterima setelah dua penerimaan fisik.')
  const [rows,setRows]=useState<Record<string,DraftLine>>(()=>Object.fromEntries(receiptLines.map((line)=>[line.id,{selected:true,qty:String(line.received-line.invoiced),price:String(line.estimatedUnitPrice),discount:line.id==='line-0098-01'?'150000':'0'}])))

  const matched=useMemo(()=>receiptLines.flatMap((line)=>{
    const draft=rows[line.id]
    if(!draft?.selected)return []
    const remaining=line.received-line.invoiced
    const qty=Math.min(remaining,digits(draft.qty))
    const price=digits(draft.price)
    const discount=Math.min(qty*price,digits(draft.discount))
    return [{...line,qty,price,discount,amount:qty*price-discount,remainingAfter:remaining-qty}]
  }),[rows])
  const gross=matched.reduce((sum,line)=>sum+line.qty*line.price,0)
  const totalDiscount=matched.reduce((sum,line)=>sum+line.discount,0)
  const finalAmount=gross-totalDiscount
  const receiptCount=new Set(matched.map((line)=>line.receipt)).size
  const partial=matched.some((line)=>line.remainingAfter>0)||receiptLines.some((line)=>!rows[line.id]?.selected)
  const recostDelta=finalAmount-estimatedAmount
  const datesValid=Boolean(invoiceDate&&receivedDate&&dueDate&&receivedDate>=invoiceDate&&dueDate>=invoiceDate)
  const canReview=invoiceNumber.trim().length>=3&&datesValid&&matched.length>0&&matched.every((line)=>line.qty>0&&line.price>0)&&finalAmount>0&&note.trim().length>=4

  const update=(id:string,key:keyof DraftLine,value:string|boolean)=>setRows((current)=>({...current,[id]:{...current[id],[key]:value}}))
  const save=(kind:'DRAFT'|'POSTED')=>onSaved({kind,invoiceNumber:invoiceNumber.trim(),amount:finalAmount,receiptCount,partial})

  return <div className="simatch-backdrop" role="presentation" onMouseDown={onClose}>
    <section className="simatch-modal" role="dialog" aria-modal="true" aria-labelledby="simatch-title" onMouseDown={(event)=>event.stopPropagation()}>
      <header><div><span>{phase==='edit'?'GRNI → INVOICE FINAL':'IMPACT PREVIEW · POST FINAL'}</span><h2 id="simatch-title">{phase==='edit'?'Cocokkan invoice supplier':'Review sebelum menjadi AP'}</h2><p>{supplier} · {grniNumber} · {purchaseReference}</p></div><button aria-label="Tutup" onClick={onClose}><X/></button></header>

      {phase==='edit'?<>
        <div className="simatch-context"><ReceiptText/><div><span>SUMBER SEMENTARA</span><strong>{grniNumber} · {money(estimatedAmount)}</strong><small>Barang sudah diterima. Nilai masih benchmark/estimated dan tidak boleh dibayar sebagai AP final.</small></div><em>ROW VERSION 3</em></div>
        <section className="simatch-meta">
          <label><span>NOMOR INVOICE SUPPLIER</span><input autoFocus value={invoiceNumber} onChange={(event)=>setInvoiceNumber(event.target.value)} /></label>
          <label><span>TANGGAL INVOICE</span><input type="date" value={invoiceDate} onChange={(event)=>setInvoiceDate(event.target.value)}/></label>
          <label><span>DITERIMA ERP</span><input type="date" value={receivedDate} onChange={(event)=>setReceivedDate(event.target.value)}/></label>
          <label><span>JATUH TEMPO</span><input type="date" value={dueDate} onChange={(event)=>setDueDate(event.target.value)}/></label>
        </section>
        <section className="simatch-lines">
          <div className="simatch-lines-title"><div><span>RECEIPT YANG BISA DI-MATCH</span><strong>Satu invoice boleh mengambil beberapa receipt dan partial qty</strong></div><Link2/></div>
          <div className="simatch-line-head"><span>Pilih / receipt</span><span>Barang & sisa</span><span>Qty invoice</span><span>Harga final</span><span>Diskon baris</span><span>Net</span></div>
          {receiptLines.map((line)=>{const draft=rows[line.id];const remaining=line.received-line.invoiced;const qty=Math.min(remaining,digits(draft.qty));const price=digits(draft.price);const discount=Math.min(qty*price,digits(draft.discount));return <article className={draft.selected?'selected':''} key={line.id}>
            <label className="simatch-check"><input type="checkbox" checked={draft.selected} onChange={(event)=>update(line.id,'selected',event.target.checked)}/><i>{draft.selected&&<Check/>}</i><span><strong>{line.receipt}</strong><small>{line.receivedAt}</small></span></label>
            <span><strong>{line.item}</strong><small>Diterima {line.received} · sudah invoice {line.invoiced} · sisa {remaining} {line.unit}</small></span>
            <label><input disabled={!draft.selected} inputMode="numeric" value={draft.qty} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>update(line.id,'qty',String(Math.min(remaining,digits(event.target.value))))}/><small>/ {remaining} {line.unit}</small></label>
            <label><div><b>Rp</b><input disabled={!draft.selected} inputMode="numeric" value={draft.price} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>update(line.id,'price',event.target.value.replace(/\D/g,''))}/></div><small>Estimate {money(line.estimatedUnitPrice)}</small></label>
            <label><div><b>Rp</b><input disabled={!draft.selected} inputMode="numeric" value={draft.discount} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>update(line.id,'discount',event.target.value.replace(/\D/g,''))}/></div><small>Maks. nilai baris</small></label>
            <strong>{draft.selected?money(qty*price-discount):'—'}<small>{draft.selected&&qty<remaining?`${remaining-qty} ${line.unit} tetap GRNI`:draft.selected?'Receipt clear':'Tidak di-match'}</small></strong>
          </article>})}
        </section>
        <label className="simatch-note"><span>CATATAN SINGKAT · WAJIB</span><textarea value={note} onChange={(event)=>setNote(event.target.value)} placeholder="Jelaskan invoice yang diterima atau perbedaan harga/diskon."/><small>{note.trim().length}/4</small></label>
        <div className="simatch-total"><span><small>BRUTO</small><strong>{money(gross)}</strong></span><i>−</i><span><small>DISKON</small><strong>{money(totalDiscount)}</strong></span><i>=</i><span className="final"><small>AP FINAL</small><strong>{money(finalAmount)}</strong></span></div>
        <div className={`simatch-guard ${canReview?'safe':'warn'}`}>{canReview?<ShieldCheck/>:<AlertTriangle/>}<span><strong>{!datesValid?'Cek urutan tanggal invoice, diterima, dan jatuh tempo':!canReview?'Lengkapi invoice dan minimal satu receipt':'Siap direview tanpa mengubah kas'}</strong><small>Draft tidak membentuk AP/GL. Posting final memakai idempotency key dan menolak row-version yang basi.</small></span></div>
        <footer><span><LockKeyhole/><small>Invoice ≠ payment. Uang tetap dicatat terpisah.</small></span><button className="soft-btn" disabled={!canReview} onClick={()=>save('DRAFT')}>Simpan draft</button><button className="primary-btn" disabled={!canReview} onClick={()=>setPhase('review')}>Review invoice <ArrowRight/></button></footer>
      </>:<>
        <div className="simatch-review-doc"><FileCheck2/><div><span>INVOICE FINAL</span><h3>{invoiceNumber}</h3><p>{invoiceDate} · diterima ERP {receivedDate} · jatuh tempo {dueDate}</p></div><strong>{money(finalAmount)}</strong></div>
        <div className="simatch-review-chain"><article><span>01</span><strong>{receiptCount} receipt</strong><small>{matched.map((line)=>line.receipt).join(' · ')}</small></article><ArrowRight/><article><span>02</span><strong>{partial?'Partial match':'GRNI cleared'}</strong><small>{partial?'Sisa qty tetap terbuka sebagai GRNI':'Seluruh qty terpilih sudah punya harga final'}</small></article><ArrowRight/><article><span>03</span><strong>AP final</strong><small>{money(finalAmount)} · belum dibayar</small></article></div>
        <div className="simatch-recost"><RefreshCcw/><div><span>CHRONOLOGICAL RECOST</span><strong>{recostDelta>=0?'+':''}{money(recostDelta)} terhadap estimasi GRNI</strong><small>Backend memisahkan selisih ke RM tersisa, WIP, FG, COGS barang yang sudah terjual, retur, dan adjustment periode tertutup.</small></div></div>
        <div className="simatch-review-grid"><article><span>GRNI</span><strong>{partial?'Berkurang sesuai match':'Cleared'}</strong><small>Hanya qty terpilih</small></article><article><span>AP SUPPLIER</span><strong>+ {money(finalAmount)}</strong><small>Due {dueDate}</small></article><article><span>KAS / BANK</span><strong>Tidak berubah</strong><small>Payment terpisah</small></article><article><span>LAPORAN</span><strong>Recalc pending</strong><small>Sampai seluruh recost selesai</small></article></div>
        <div className="simatch-period-warning"><FileClock/><span><strong>Tanggal ekonomi tidak ditimpa tanggal input.</strong><small>Invoice terlambat tetap mengoreksi cost kronologis; periode tertutup memakai adjustment period, bukan edit jurnal lama.</small></span></div>
        <footer><button className="soft-btn" onClick={()=>setPhase('edit')}><ArrowLeft/> Kembali edit</button><button className="primary-btn" onClick={()=>save('POSTED')}><ShieldCheck/> Post invoice final</button></footer>
      </>}
    </section>
  </div>
}

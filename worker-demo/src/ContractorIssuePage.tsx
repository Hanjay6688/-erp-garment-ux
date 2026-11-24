import { useMemo, useState, useSyncExternalStore } from 'react'
import {
  AlertTriangle, ArrowRight, Boxes, CalendarDays, CheckCircle2, Clock3, Eye,
  EyeOff, Link2, LockKeyhole, PackageMinus, Plus, ReceiptText, Search,
  ShieldCheck, Undo2, UserRound, WalletCards, X,
} from 'lucide-react'
import {exactAccessoryQuantity,validAccessoryRetail,micro} from './accessoryIssue'
import EnterpriseSelect from './EnterpriseSelect'
import {fixtureDate,issueQuote,masterBook,noteStock,masterCode,useAccessoryBook,type AccessoryBook,type PricingMode} from './demo/accessoryPricing'
import './contractor-issue.css'

import {seedDocuments,readNotes,saveNotes,subscribe,mandorNames,money,lineTotal,documentTotal,amountDue,type IssueDocument,type IssueLine} from './demo/issueDocuments'
import {payrollClaim} from './demo/payrollSources'
type IssueStatus=IssueDocument['status']
type PeriodFilter = 'Hari ini' | '7 hari terakhir' | 'Bulan ini' | 'Semua tanggal' | 'Custom'
function priceLine(book:AccessoryBook,doc:IssueDocument,l:IssueLine,docs:IssueDocument[]):IssueLine {
  const item=book.items.find(i=>i.code===masterCode(l.id));if(!item)return {...l,sellingPrice:null,source:'Harga master belum diatur'}
  const q=issueQuote(book,item,doc.mandor,doc.issuedOn,l.mode??'MASTER',l.manual?.trim()?Number(l.manual.replace(',','.')):null)
  let price=q.per, source=q.source
  if(l.mode==='MANUAL' && !validAccessoryRetail(l.manual??'')){price=null;source='Isi harga eceran di atas nol, maksimal dua desimal.'}
  if((l.mode??'MASTER')==='MASTER' && price!==null && q.factor && Number.isSafeInteger(l.qty) && l.qty>0
    && !exactAccessoryQuantity(BigInt(l.qty),micro(String(q.factor)))){
    price=null;source='Konversi jumlah ke satuan harga tidak persis. Pilih Eceran per pcs.'
  }
  return {...l,item:item.name,category:item.category,unit:item.stockUom,stock:noteStock(item.code,item.stock,docs),sellingPrice:price,averageCost:q.hpp,reimbursement:q.reimbursement,source,version:q.version}
}
const quoteId=(d:IssueDocument)=>JSON.stringify([d.number,d.rowVersion,d.mandor,d.issuedOn,d.reason,d.note,d.lines.map(l=>[l.id,l.qty,l.mode,l.sellingPrice,l.version,l.stock,l.reimbursement,l.averageCost])])

function Status({value,settled}:{value:IssueStatus;settled:boolean}) {
  if (settled) return <em className="ci-status settled">LUNAS</em>
  return <em className={`ci-status ${value.toLowerCase()}`}>{value}</em>
}

export default function ContractorIssuePage() {
  const documents=useSyncExternalStore(subscribe,readNotes),setDocuments=saveNotes,book=useAccessoryBook()
  const catalog:IssueLine[]=book.items.filter(i=>i.active&&i.stockUom.toLowerCase()==='pcs').map(i=>({id:i.code,item:i.name,category:i.category,qty:0,stock:noteStock(i.code,i.stock,documents),unit:i.stockUom,averageCost:i.movingAverage,sellingPrice:null,mode:'MASTER'}))
  const [reviewQuote,setReviewQuote]=useState(''),[deleteOpen,setDeleteOpen]=useState(false),[sort,setSort]=useState('baru')
  const [selectedNumber,setSelectedNumber] = useState(()=>new URLSearchParams(location.search).get('nota')??seedDocuments[0].number)
  const [query,setQuery] = useState('')
  const [statusFilter,setStatusFilter] = useState('Semua status')
  const [mandorFilter,setMandorFilter] = useState('Semua mandor')
  const [periodFilter,setPeriodFilter] = useState<PeriodFilter>('Semua tanggal')
  const [dateFrom,setDateFrom] = useState('2026-08-01')
  const [dateTo,setDateTo] = useState('2026-08-28')
  const [showSettled,setShowSettled] = useState(false)
  const [catalogOpen,setCatalogOpen] = useState(false)
  const [catalogQuery,setCatalogQuery] = useState('')
  const [catalogCategory,setCatalogCategory] = useState('Semua kategori')
  const [reviewOpen,setReviewOpen] = useState(false)
  const [reverseOpen,setReverseOpen] = useState(false)
  const [reverseNote,setReverseNote] = useState('')
  const [notice,setNotice] = useState('')

  const effectiveFrom = periodFilter === 'Hari ini' ? fixtureDate
    : periodFilter === '7 hari terakhir' ? '2026-11-18'
    : periodFilter === 'Bulan ini' ? '2026-11-01'
    : periodFilter === 'Custom' ? dateFrom : ''
  const effectiveTo = periodFilter === 'Semua tanggal' ? '' : periodFilter === 'Custom' ? dateTo : fixtureDate
  const visible = useMemo(() => documents.filter((document) => {
    const searchable = `${document.number} ${document.mandor} ${document.productionBatch} ${document.distributionBatch}`.toLowerCase()
    const statusMatches = statusFilter === 'Semua status' || document.status === statusFilter.toUpperCase()
    return searchable.includes(query.toLowerCase())
      && statusMatches
      && (mandorFilter === 'Semua mandor' || document.mandor === mandorFilter)
      && (!effectiveFrom || document.issuedOn >= effectiveFrom)
      && (!effectiveTo || document.issuedOn <= effectiveTo)
      && (showSettled || !document.settledAt)
  }), [documents,effectiveFrom,effectiveTo,mandorFilter,query,showSettled,statusFilter])
  const ordered=[...visible].sort((a,b)=>sort==='lama'?a.issuedOn.localeCompare(b.issuedOn):sort==='mandor'?a.mandor.localeCompare(b.mandor):b.issuedOn.localeCompare(a.issuedOn))
  const original=visible.find(d=>d.number===selectedNumber)??ordered[0]??null
  const selected=original?.status==='DRAFT'?{...original,lines:original.lines.map(l=>priceLine(book,original,l,documents))}:original
  const availableCatalog = catalog.filter((item) => {
    const searchMatches = `${item.id} ${item.item} ${item.category}`.toLowerCase().includes(catalogQuery.toLowerCase())
    return searchMatches && (catalogCategory === 'Semua kategori' || item.category === catalogCategory)
  })
  const settledCount = documents.filter((document)=>Boolean(document.settledAt)).length
  const postedOpen = documents.filter((document)=>document.status==='POSTED'&&!document.settledAt)

  const updateDocument = (patch:Partial<IssueDocument>) => {
    if (!selected) return
    setDocuments((current)=>current.map((document)=>document.number===selected.number?{...document,...patch}:document))
  }
  const updateQty = (id:string,raw:string) => {
    if (!selected || selected.status!=='DRAFT') return
    const source = selected.lines.find((line)=>line.id===id)
    const qty = Math.min(source?.stock??0,Math.max(0,Number(raw.replace(/\D/g,''))||0))
    updateDocument({lines:selected.lines.map((line)=>line.id===id?{...line,qty}:line)})
    setNotice('')
  }
  const removeLine = (id:string) => {
    if (selected?.status==='DRAFT') updateDocument({lines:selected.lines.filter((line)=>line.id!==id)})
  }
  const addLine = (item:IssueLine) => {
    if (!selected || selected.status!=='DRAFT' || selected.lines.some((line)=>line.id===item.id)) return
    updateDocument({lines:[...selected.lines,{...item,qty:1}]})
  }
  const createDraft = () => {
    const next:IssueDocument = { number:`NAA-SIM-${crypto.randomUUID().slice(0,8).toUpperCase()}`, mandor:'Mandor Afui', productionBatch:'', distributionBatch:'', location:'Gudang Aksesori Utama', issuedOn:fixtureDate, issuedAt:fixtureDate, status:'DRAFT', rowVersion:1, note:'', lines:[] }
    setDocuments((current)=>[next,...current])
    setSelectedNumber(next.number)
    setStatusFilter('Semua status')
    setMandorFilter('Semua mandor')
    setPeriodFilter('Semua tanggal')
    setShowSettled(false)
    setNotice('Draft baru terbentuk lokal. Backend belum berubah.')
  }
  const post = () => {
    if(!selected||!canPost)return
    try{saveNotes(docs=>{const d=docs.find(d=>d.number===selected.number);if(!d||d.status!=='DRAFT')throw Error('Status nota berubah.');const priced={...d,lines:d.lines.map(l=>priceLine(masterBook(),d,l,docs))};if(quoteId(priced)!==reviewQuote)throw Error('Harga, stok atau draft berubah. Buka review lagi.');return docs.map(row=>row.number===d.number?{...priced,status:'POSTED',inventoryChange:-1,rowVersion:d.rowVersion+1}:row)})}catch(e){setNotice((e as Error).message);setReviewOpen(false);return}
    setReviewOpen(false)
    setNotice(`${selected.number} diposting sebagai simulasi. Stok latihan berkurang dan tagihan tersimpan sesuai review.`)
  }
  const reverse = () => {
    if(!selected||!reverseNote.trim())return
    if(payrollClaim(selected.number)){setNotice('Lepaskan nota ini dari payroll yang terkait lebih dahulu.');setReverseOpen(false);return}
    saveNotes(docs=>docs.map(d=>d.number===selected.number&&d.status==='POSTED'&&!d.settledAt?{...d,status:'REVERSED',inventoryChange:(d.inventoryChange??0)+1,rowVersion:d.rowVersion+1,note:`${d.note} · Pembalikan: ${reverseNote.trim()}`}:d))
    setReverseOpen(false)
    setReverseNote('')
    setNotice(`Reversal ${selected.number} terbentuk sebagai simulasi; nota asal tetap ada.`)
  }
  const totalLabel = selected ? amountDue(selected) : 'Belum ada baris'
  const canPost = Boolean(selected && selected.status==='DRAFT' && selected.lines.length>0 && selected.lines.every((line)=>Number.isSafeInteger(line.qty)&&line.qty>0&&line.qty<=line.stock&&line.sellingPrice!==null) && selected.reason?.trim() && selected.issuedOn && selected.issuedOn<=fixtureDate)

  return <>
    <section className="hero-copy compact ci-hero"><div><div className="eyebrow">KEUANGAN · KASBON MANDOR</div><h1>Nota Ambil Aksesori</h1><p>Catat aksesori detail yang benar-benar diambil mandor. Posting mengurangi Stock On Hand dan membentuk kasbon yang direkonsiliasi saat payroll.</p></div><button className="primary-btn" onClick={createDraft}><Plus/> Nota baru</button></section>
    <section className="ci-metrics"><article><span>DRAFT AKTIF</span><strong>{documents.filter((item)=>item.status==='DRAFT').length}</strong><small>Belum mengubah stok</small></article><article><span>BELUM DISELESAIKAN</span><strong>{postedOpen.length}</strong><small>Masih masuk rekonsiliasi payroll</small></article><article><span>KASBON TERBUKA</span><strong>{money(postedOpen.reduce((sum,item)=>sum+documentTotal(item),0))}</strong><small>Harga jual snapshot</small></article><article><span>OTOMATIS DISEMBUNYIKAN</span><strong>{settledCount} nota</strong><small>Sudah lunas · tetap bisa dibuka</small></article></section>
    <section className="panel ci-filter-bar">
      <label className="ci-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari nota, mandor, Batch Produksi..."/></label>
      <EnterpriseSelect label="MANDOR" value={mandorFilter} options={['Semua mandor',...mandorNames]} onChange={setMandorFilter}/>
      <EnterpriseSelect label="STATUS" value={statusFilter} options={['Semua status','Draft','Posted','Reversed']} onChange={setStatusFilter}/>
      <EnterpriseSelect label="PERIODE" value={periodFilter} options={['Hari ini','7 hari terakhir','Bulan ini','Semua tanggal','Custom']} onChange={(value)=>setPeriodFilter(value as PeriodFilter)}/>
      <label>Urutan nota<select value={sort} onChange={e=>setSort(e.target.value)}><option value="baru">Tanggal terbaru</option><option value="lama">Tanggal terlama</option><option value="mandor">Nama mandor</option></select></label>
      <button className={`ci-show-settled ${showSettled?'active':''}`} onClick={()=>setShowSettled((current)=>!current)}>{showSettled?<EyeOff/>:<Eye/>}<span><small>NOTA LUNAS</small><strong>{showSettled?'Sembunyikan lagi':'Tampilkan kembali'}</strong></span><b>{settledCount}</b></button>
      {periodFilter==='Custom'&&<div className="ci-custom-range"><CalendarDays/><span><small>PERIODE CUSTOM</small><strong>{dateFrom||'Tanggal awal'} → {dateTo||'Tanggal akhir'}</strong></span><label><small>DARI</small><input type="date" value={dateFrom} max={dateTo||undefined} onChange={(event)=>setDateFrom(event.target.value)}/></label><label><small>SAMPAI</small><input type="date" value={dateTo} min={dateFrom||undefined} onChange={(event)=>setDateTo(event.target.value)}/></label></div>}
    </section>
    <section className="panel ci-layout">
      <aside><header><div><span>BROWSER NOTA</span><strong>{visible.length} dokumen tampil</strong></div><ReceiptText/></header><div className="ci-browser">{ordered.map((document)=><button className={document.number===selected?.number?'active':''} key={document.number} onClick={()=>{setSelectedNumber(document.number);setNotice('')}}><i><PackageMinus/></i><span><strong>{document.number}</strong><small>{document.mandor} · {document.productionBatch}</small><em>Batch Distribusi {document.distributionBatch} · {document.issuedAt}</em></span><b>{amountDue(document.status==='DRAFT'?{...document,lines:document.lines.map(line=>priceLine(book,document,line,documents))}:document)}</b><Status value={document.status} settled={Boolean(document.settledAt)}/></button>)}{visible.length===0&&<div className="ci-empty browser"><Search/><strong>Tidak ada nota yang cocok</strong><small>Ubah mandor, status, rentang tanggal, atau buka kembali nota lunas.</small></div>}</div></aside>
      {selected ? <main><header className="ci-detail-head"><div><span>{selected.settledAt?'POSTED · SETTLED':selected.status==='DRAFT'?'DRAFT · BOLEH DIEDIT':'POSTED SOURCE · READ ONLY'}</span><h2>{selected.number}</h2><p>{selected.productionBatch||'Tanpa PO'}{selected.distributionBatch?' · Batch '+selected.distributionBatch:''}</p></div><div><Status value={selected.status} settled={Boolean(selected.settledAt)}/><small>row version {selected.rowVersion}</small></div></header>
        <div className="ci-facts"><article className="ci-fact-select"><UserRound/><EnterpriseSelect className="ci-inline-select" label="MANDOR" value={selected.mandor} options={mandorNames} disabled={selected.status!=='DRAFT'} onChange={(mandor)=>updateDocument({mandor,lines:selected.lines.map(l=>l.mode==='FREE'?{...l,mode:'MASTER'}:l)})}/></article><article><Boxes/><span><small>LOKASI SUMBER</small><strong>{selected.location}</strong></span></article><article><Clock3/><span><small>WAKTU AMBIL</small>{selected.status==='DRAFT'?<input required type="date" max={fixtureDate} aria-label="Tanggal nota" value={selected.issuedOn} onChange={e=>updateDocument({issuedOn:e.target.value,issuedAt:e.target.value,lines:selected.lines.map(l=>l.mode==='FREE'?{...l,mode:'MASTER'}:l)})}/>:<strong>{selected.issuedAt}</strong>}{selected.settledAt&&<em>Lunas · {selected.settledAt}</em>}</span></article></div>
        {selected.status==='DRAFT'&&<section className="ci-browse-entry"><div><Search/><span><strong>Tambah aksesori melalui browser</strong><small>Cari kode, nama, atau kategori; barang tidak ditumpuk di halaman nota.</small></span></div><button className="soft-btn" onClick={()=>setCatalogOpen(true)}><Search/> Browse aksesori</button></section>}
        <section className="ci-lines"><div className="ci-line-head"><span>Barang detail</span><span>Stock On Hand</span><span>Qty ambil</span><span>Harga jual snapshot</span><span>Nilai kasbon</span><span/></div>{selected.lines.map((line)=><article key={line.id}><span><strong>{line.item}</strong><small>{line.id} · BOM kategori {line.category}</small></span><span><strong>{line.stock} {line.unit}</strong><small>Moving avg {money(line.averageCost)}</small></span><label><input aria-label={'Jumlah ambil '+line.item} disabled={selected.status!=='DRAFT'} inputMode="numeric" value={line.qty} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateQty(line.id,event.target.value)}/><small>{line.unit}</small></label><div className="ci-price-choice">{selected.status==='DRAFT'&&<label>Dasar harga<select aria-label={'Dasar harga '+line.item} value={line.mode??'MASTER'} onChange={e=>updateDocument({lines:selected.lines.map(l=>l.id===line.id?{...l,mode:e.target.value as PricingMode}:l)})}><option value="MASTER">Harga master</option><option value="MANUAL">Eceran per pcs</option>{book.free.some(r=>r.mandor===selected.mandor.replace(/^Mandor /,'')&&r.categories.includes(line.category)&&r.start<=selected.issuedOn&&(!r.end||selected.issuedOn<r.end))&&<option value="FREE">Gratis Special</option>}</select></label>}
          {selected.status==='DRAFT'&&line.mode==='MANUAL'&&<input aria-label={'Harga eceran '+line.item} inputMode="decimal" value={line.manual??''} onChange={e=>updateDocument({lines:selected.lines.map(l=>l.id===line.id?{...l,manual:e.target.value}:l)})}/>}
          <strong>{line.sellingPrice===null?(line.source??'Harga master belum diatur'):money(line.sellingPrice)+'/pcs'}</strong>{line.sellingPrice!==null&&<small>{line.source??'Harga tersimpan'}</small>}<small>Reimburse {line.reimbursement!=null?money(line.reimbursement)+'/pcs':'belum diatur'}</small></div><b>{lineTotal(line)===null?'Belum dihitung':money(lineTotal(line)!)}</b><button disabled={selected.status!=='DRAFT'} aria-label={`Hapus ${line.item}`} onClick={()=>removeLine(line.id)}><X/></button></article>)}{selected.lines.length===0&&<div className="ci-empty"><PackageMinus/><strong>Belum ada aksesori</strong><small>Buka browser lalu pilih barang yang benar-benar diambil.</small></div>}</section>
        <label className="ci-note"><span>CATATAN · OPSIONAL</span><textarea disabled={selected.status!=='DRAFT'} value={selected.note} onChange={(event)=>updateDocument({note:event.target.value})} placeholder="Arahan atau kondisi pengambilan..."/></label>
        {selected.status==='DRAFT'&&<label className="ci-note"><span>ALASAN NOTA · WAJIB</span><input aria-label="Alasan nota" required maxLength={1000} value={selected.reason??''} onChange={e=>updateDocument({reason:e.target.value})}/></label>}
        <div className="ci-equation"><span><small>HPP STOK</small><strong>{money(selected.lines.reduce((sum,line)=>sum+line.qty*line.averageCost,0))}</strong></span><i>≠</i><span><small>HARGA JUAL MANDOR</small><strong>{totalLabel}</strong></span><i>→</i><span className="result"><small>KASBON PAYROLL</small><strong>{totalLabel}</strong></span></div>
        <p className="ci-sample-policy">Aturan latihan berlaku 24 Nov 2026 untuk Afui · Kancing.</p><div className="ci-guard"><ShieldCheck/><span><strong>BOM tetap kategori; pengambilan tetap barang detail.</strong><small>Kancing Silver/Metal sama-sama memenuhi kategori Kancing, dengan stok dan HPP masing-masing. Harga jual mengikuti kategori dan mandor pada tanggal nota.</small></span></div>
        {notice&&<div className="ci-notice"><CheckCircle2/> {notice}</div>}
        <footer><span>{selected.settledAt?'Nota sudah diselesaikan di payroll dan terkunci.':selected.status==='DRAFT'?'Draft belum mengurangi stok atau membentuk kasbon.':'Posted tidak diedit atau dihapus; koreksi lewat reversal.'}</span>{selected.status==='DRAFT'?<><button type="button" className="soft-btn" disabled={!selected.reason?.trim()} onClick={()=>setDeleteOpen(true)}>Hapus draft</button><button className="soft-btn" onClick={()=>setNotice('Draft disimpan sebagai simulasi; backend belum berubah.')}>Simpan draft</button><button className="primary-btn" disabled={!canPost} onClick={()=>{setReviewQuote(quoteId(selected));setReviewOpen(true)}}>Review & post <ArrowRight/></button></>:<button className="soft-btn" disabled={selected.status!=='POSTED'||Boolean(selected.settledAt)||!!payrollClaim(selected.number)} title={payrollClaim(selected.number)?'Terpilih di '+payrollClaim(selected.number):undefined} onClick={()=>setReverseOpen(true)}><Undo2/> Reverse nota</button>}</footer>
      </main> : <main className="ci-no-selection"><Search/><strong>Tidak ada detail untuk ditampilkan</strong><small>Sesuaikan filter browser di atas.</small></main>}
    </section>
    {catalogOpen&&selected&&<div className="ci-backdrop" onMouseDown={()=>setCatalogOpen(false)}><section className="ci-modal ci-catalog-modal" role="dialog" aria-modal="true" aria-labelledby="ci-catalog-title" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>MASTER AKSESORI · STOCK ON HAND</span><h2 id="ci-catalog-title">Browse aksesori</h2><p>Pilih barang detail yang benar-benar keluar untuk {selected.mandor}.</p></div><button onClick={()=>setCatalogOpen(false)} aria-label="Tutup katalog"><X/></button></header><div className="ci-catalog-toolbar"><label className="ci-search"><Search/><input autoFocus value={catalogQuery} onChange={(event)=>setCatalogQuery(event.target.value)} placeholder="Cari kode, nama, kategori..."/></label><EnterpriseSelect label="KATEGORI" value={catalogCategory} options={['Semua kategori',...new Set(catalog.map((item)=>item.category))]} onChange={setCatalogCategory}/></div><div className="ci-catalog-results">{availableCatalog.map((item)=>{const added=selected.lines.some((line)=>line.id===item.id);return <article key={item.id}><span><small>{item.id} · {item.category}</small><strong>{item.item}</strong><em>{item.stock.toLocaleString('id-ID')} {item.unit} On Hand</em></span><span><small>HARGA MANDOR</small><strong>{(()=>{const v=priceLine(book,selected,item,documents).sellingPrice;return v===null?'Harga master belum diatur':money(v)})()}</strong><em>Moving avg {money(item.averageCost)}</em></span><button disabled={added} onClick={()=>addLine(item)}>{added?<CheckCircle2/>:<Plus/>}{added?'Sudah dipilih':'Tambah'}</button></article>})}{availableCatalog.length===0&&<div className="ci-empty"><Search/><strong>Aksesori tidak ditemukan</strong><small>Coba kata kunci atau kategori lain.</small></div>}</div><footer><span>{selected.lines.length} barang sudah ada di draft</span><button className="primary-btn" onClick={()=>setCatalogOpen(false)}>Selesai memilih</button></footer></section></div>}
    {reviewOpen&&selected&&<div className="ci-backdrop" onMouseDown={()=>setReviewOpen(false)}><section className="ci-modal" role="dialog" aria-modal="true" aria-label="Review nota" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>IMPACT PREVIEW</span><h2>Post Nota Ambil Aksesori?</h2><p>{selected.number} · {selected.mandor} · {selected.productionBatch}</p></div><button aria-label="Kembali ke nota" onClick={()=>setReviewOpen(false)}><X/></button></header><div className="ci-impact"><article><PackageMinus/><span><small>STOCK ON HAND</small><strong>− {selected.lines.reduce((sum,line)=>sum+line.qty,0)} unit</strong></span></article><ArrowRight/><article><WalletCards/><span><small>KASBON MANDOR</small><strong>+ {totalLabel}</strong></span></article><ArrowRight/><article><Link2/><span><small>PAYROLL SOURCE</small><strong>{selected.number}</strong></span></article></div><div className="ci-modal-guard"><LockKeyhole/><span><strong>Satu transaksi atomik</strong><small>Stock movement, costing snapshot, contractor issue, dan subledger kasbon harus berhasil bersama; request berulang memakai idempotency key yang sama.</small></span></div><footer><button className="soft-btn" onClick={()=>setReviewOpen(false)}>Kembali</button><button className="primary-btn" onClick={post}><ShieldCheck/> Post simulasi</button></footer></section></div>}
    {deleteOpen&&selected&&<div className="ci-backdrop"><section className="ci-modal" role="dialog" aria-modal="true" aria-label="Hapus draft nota"><h2>Hapus draft nota?</h2><p>{selected.number} belum memindahkan stok.</p><button type="button" onClick={()=>setDeleteOpen(false)}>Kembali</button><button type="button" onClick={()=>{if(selected.status==='DRAFT'&&selected.reason?.trim())saveNotes(ds=>ds.filter(d=>d.number!==selected.number||d.status!=='DRAFT'));setDeleteOpen(false)}}>Ya, hapus draft</button></section></div>}
    {reverseOpen&&selected&&<div className="ci-backdrop" onMouseDown={()=>setReverseOpen(false)}><section className="ci-modal reverse" role="alertdialog" aria-modal="true" aria-label="Balikkan nota aksesori" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>REVERSAL · POSTED SOURCE</span><h2>Reverse {selected.number}?</h2><p>Nota asal tidak dihapus. Stock dan kasbon dipulihkan lewat dokumen lawan.</p></div><button aria-label="Kembali ke nota" onClick={()=>setReverseOpen(false)}><X/></button></header><div className="ci-modal-warning"><AlertTriangle/><span><strong>Server akan memblokir bila kasbon sudah diselesaikan.</strong><small>Jangan reverse hanya untuk mengganti catatan; gunakan ketika pengambilan memang batal atau salah barang/qty.</small></span></div><label className="ci-note"><span>CATATAN SINGKAT · WAJIB</span><textarea autoFocus value={reverseNote} onChange={(event)=>setReverseNote(event.target.value)} placeholder="Contoh: salah Batch Distribusi, barang belum dipakai."/></label><footer><button className="soft-btn" onClick={()=>setReverseOpen(false)}>Batal</button><button className="danger-btn" disabled={!reverseNote.trim()} onClick={reverse}><Undo2/> Reverse simulasi</button></footer></section></div>}
  </>
}

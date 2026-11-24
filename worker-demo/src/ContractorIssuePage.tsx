import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Boxes, CalendarDays, CheckCircle2, Clock3, Eye,
  EyeOff, Link2, LockKeyhole, PackageMinus, Plus, ReceiptText, Search,
  ShieldCheck, Undo2, UserRound, WalletCards, X,
} from 'lucide-react'
import EnterpriseSelect from './EnterpriseSelect'
import './contractor-issue.css'

type IssueStatus = 'DRAFT' | 'POSTED' | 'REVERSED'
type PeriodFilter = 'Hari ini' | '7 hari terakhir' | 'Bulan ini' | 'Semua tanggal' | 'Custom'
type IssueLine = {
  id: string
  item: string
  category: string
  qty: number
  unit: string
  stock: number
  averageCost: number
  sellingPrice: number
}
type IssueDocument = {
  number: string
  mandor: string
  productionBatch: string
  distributionBatch: string
  location: string
  issuedOn: string
  issuedAt: string
  status: IssueStatus
  settledAt?: string
  rowVersion: number
  note: string
  lines: IssueLine[]
}

const catalog: IssueLine[] = [
  { id:'ACC-BTN-017', item:'Kancing Jeans 17 mm · Silver', category:'Kancing', qty:0, unit:'pcs', stock:4800, averageCost:620, sellingPrice:750 },
  { id:'ACC-ZIP-014', item:'Resleting 14 cm · Black', category:'Resleting', qty:0, unit:'pcs', stock:2200, averageCost:5200, sellingPrice:6500 },
  { id:'ACC-RVT-011', item:'Rivet Copper', category:'Rivet', qty:0, unit:'pcs', stock:3600, averageCost:780, sellingPrice:900 },
  { id:'ACC-LBL-004', item:'Label Woven Vivo', category:'Label', qty:0, unit:'pcs', stock:8000, averageCost:530, sellingPrice:750 },
]

const seedDocuments: IssueDocument[] = [
  { number:'NAA-260827-021', mandor:'Mandor Budi', productionBatch:'POT-260827-042', distributionBatch:'042-03', location:'Gudang Aksesori Utama', issuedOn:'2026-08-27', issuedAt:'27 Agu 2026 · 10:06', status:'DRAFT', rowVersion:2, note:'Persiapan jahit batch hitam.', lines:[{...catalog[1],qty:72},{...catalog[3],qty:240}] },
  { number:'NAA-260826-018', mandor:'Mandor Budi', productionBatch:'POT-260826-041', distributionBatch:'041-01', location:'Gudang Aksesori Utama', issuedOn:'2026-08-26', issuedAt:'26 Agu 2026 · 14:22', status:'POSTED', rowVersion:4, note:'Kebutuhan aktual batch distribusi pertama.', lines:[{...catalog[0],qty:480},{...catalog[2],qty:480}] },
  { number:'NAA-260824-019', mandor:'Mandor Rian', productionBatch:'POT-260824-039', distributionBatch:'039-02', location:'Gudang Aksesori Utama', issuedOn:'2026-08-24', issuedAt:'24 Agu 2026 · 08:44', status:'REVERSED', rowVersion:6, note:'Batch distribusi dibatalkan sebelum jahit.', lines:[{...catalog[3],qty:500}] },
  { number:'NAA-260814-009', mandor:'Mandor Dedi', productionBatch:'POT-260815-026', distributionBatch:'026-01', location:'Gudang Aksesori Utama', issuedOn:'2026-08-14', issuedAt:'14 Agu 2026 · 10:08', status:'POSTED', settledAt:'27 Agu 2026 · PAY-MANDOR-0086', rowVersion:7, note:'Sudah diselesaikan pada payroll.', lines:[{...catalog[0],qty:800,sellingPrice:800}] },
]

const mandorNames = ['Mandor Afat','Mandor Budi','Mandor Dedi','Mandor Rian']
const money = (value:number) => new Intl.NumberFormat('id-ID',{style:'currency',currency:'IDR',maximumFractionDigits:0}).format(value)
const lineTotal = (line:IssueLine) => line.qty * line.sellingPrice
const documentTotal = (document:IssueDocument) => document.lines.reduce((sum,line)=>sum+lineTotal(line),0)

function Status({value,settled}:{value:IssueStatus;settled:boolean}) {
  if (settled) return <em className="ci-status settled">LUNAS</em>
  return <em className={`ci-status ${value.toLowerCase()}`}>{value}</em>
}

export default function ContractorIssuePage() {
  const [documents,setDocuments] = useState(seedDocuments)
  const [selectedNumber,setSelectedNumber] = useState(seedDocuments[0].number)
  const [query,setQuery] = useState('')
  const [statusFilter,setStatusFilter] = useState('Semua status')
  const [mandorFilter,setMandorFilter] = useState('Semua mandor')
  const [periodFilter,setPeriodFilter] = useState<PeriodFilter>('Bulan ini')
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

  const effectiveFrom = periodFilter === 'Hari ini' ? '2026-08-28'
    : periodFilter === '7 hari terakhir' ? '2026-08-22'
    : periodFilter === 'Bulan ini' ? '2026-08-01'
    : periodFilter === 'Custom' ? dateFrom : ''
  const effectiveTo = periodFilter === 'Semua tanggal' ? '' : periodFilter === 'Custom' ? dateTo : '2026-08-28'
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
  const selected = visible.find((document)=>document.number===selectedNumber) ?? visible[0] ?? null
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
    const next:IssueDocument = { number:`NAA-SIM-${String(documents.length+1).padStart(3,'0')}`, mandor:'Mandor Afat', productionBatch:'POT-260827-042', distributionBatch:'042-03', location:'Gudang Aksesori Utama', issuedOn:'2026-08-28', issuedAt:'28 Agu 2026 · simulasi', status:'DRAFT', rowVersion:1, note:'', lines:[] }
    setDocuments((current)=>[next,...current])
    setSelectedNumber(next.number)
    setStatusFilter('Semua status')
    setMandorFilter('Semua mandor')
    setPeriodFilter('Bulan ini')
    setShowSettled(false)
    setNotice('Draft baru terbentuk lokal. Backend belum berubah.')
  }
  const post = () => {
    if (!selected) return
    updateDocument({status:'POSTED',rowVersion:selected.rowVersion+1})
    setReviewOpen(false)
    setNotice(`${selected.number} diposting sebagai simulasi. Stock On Hand dan kasbon belum berubah di backend.`)
  }
  const reverse = () => {
    if (!selected) return
    updateDocument({status:'REVERSED',rowVersion:selected.rowVersion+1,note:`${selected.note} · Reverse: ${reverseNote.trim()}`})
    setReverseOpen(false)
    setReverseNote('')
    setNotice(`Reversal ${selected.number} terbentuk sebagai simulasi; nota asal tetap ada.`)
  }
  const total = selected ? documentTotal(selected) : 0
  const canPost = Boolean(selected && selected.status==='DRAFT' && selected.lines.length>0 && selected.lines.every((line)=>line.qty>0&&line.qty<=line.stock) && selected.note.trim().length>=4)

  return <>
    <section className="hero-copy compact ci-hero"><div><div className="eyebrow">KEUANGAN · KASBON MANDOR</div><h1>Nota Ambil Aksesori</h1><p>Catat aksesori detail yang benar-benar diambil mandor. Posting mengurangi Stock On Hand dan membentuk kasbon yang direkonsiliasi saat payroll.</p></div><button className="primary-btn" onClick={createDraft}><Plus/> Nota baru</button></section>
    <section className="ci-metrics"><article><span>DRAFT AKTIF</span><strong>{documents.filter((item)=>item.status==='DRAFT').length}</strong><small>Belum mengubah stok</small></article><article><span>BELUM DISELESAIKAN</span><strong>{postedOpen.length}</strong><small>Masih masuk rekonsiliasi payroll</small></article><article><span>KASBON TERBUKA</span><strong>{money(postedOpen.reduce((sum,item)=>sum+documentTotal(item),0))}</strong><small>Harga jual snapshot</small></article><article><span>OTOMATIS DISEMBUNYIKAN</span><strong>{settledCount} nota</strong><small>Sudah lunas · tetap bisa dibuka</small></article></section>
    <section className="panel ci-filter-bar">
      <label className="ci-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari nota, mandor, Batch Produksi..."/></label>
      <EnterpriseSelect label="MANDOR" value={mandorFilter} options={['Semua mandor',...mandorNames]} onChange={setMandorFilter}/>
      <EnterpriseSelect label="STATUS" value={statusFilter} options={['Semua status','Draft','Posted','Reversed']} onChange={setStatusFilter}/>
      <EnterpriseSelect label="PERIODE" value={periodFilter} options={['Hari ini','7 hari terakhir','Bulan ini','Semua tanggal','Custom']} onChange={(value)=>setPeriodFilter(value as PeriodFilter)}/>
      <button className={`ci-show-settled ${showSettled?'active':''}`} onClick={()=>setShowSettled((current)=>!current)}>{showSettled?<EyeOff/>:<Eye/>}<span><small>NOTA LUNAS</small><strong>{showSettled?'Sembunyikan lagi':'Tampilkan kembali'}</strong></span><b>{settledCount}</b></button>
      {periodFilter==='Custom'&&<div className="ci-custom-range"><CalendarDays/><span><small>PERIODE CUSTOM</small><strong>{dateFrom||'Tanggal awal'} → {dateTo||'Tanggal akhir'}</strong></span><label><small>DARI</small><input type="date" value={dateFrom} max={dateTo||undefined} onChange={(event)=>setDateFrom(event.target.value)}/></label><label><small>SAMPAI</small><input type="date" value={dateTo} min={dateFrom||undefined} onChange={(event)=>setDateTo(event.target.value)}/></label></div>}
    </section>
    <section className="panel ci-layout">
      <aside><header><div><span>BROWSER NOTA</span><strong>{visible.length} dokumen tampil</strong></div><ReceiptText/></header><div className="ci-browser">{visible.map((document)=><button className={document.number===selected?.number?'active':''} key={document.number} onClick={()=>{setSelectedNumber(document.number);setNotice('')}}><i><PackageMinus/></i><span><strong>{document.number}</strong><small>{document.mandor} · {document.productionBatch}</small><em>Batch Distribusi {document.distributionBatch} · {document.issuedAt}</em></span><b>{money(documentTotal(document))}</b><Status value={document.status} settled={Boolean(document.settledAt)}/></button>)}{visible.length===0&&<div className="ci-empty browser"><Search/><strong>Tidak ada nota yang cocok</strong><small>Ubah mandor, status, rentang tanggal, atau buka kembali nota lunas.</small></div>}</div></aside>
      {selected ? <main><header className="ci-detail-head"><div><span>{selected.settledAt?'POSTED · SETTLED':selected.status==='DRAFT'?'DRAFT · BOLEH DIEDIT':'POSTED SOURCE · READ ONLY'}</span><h2>{selected.number}</h2><p>{selected.productionBatch} · Batch Distribusi {selected.distributionBatch}</p></div><div><Status value={selected.status} settled={Boolean(selected.settledAt)}/><small>row version {selected.rowVersion}</small></div></header>
        <div className="ci-facts"><article className="ci-fact-select"><UserRound/><EnterpriseSelect className="ci-inline-select" label="MANDOR" value={selected.mandor} options={mandorNames} disabled={selected.status!=='DRAFT'} onChange={(mandor)=>updateDocument({mandor})}/></article><article><Boxes/><span><small>LOKASI SUMBER</small><strong>{selected.location}</strong></span></article><article><Clock3/><span><small>WAKTU AMBIL</small><strong>{selected.issuedAt}</strong>{selected.settledAt&&<em>Lunas · {selected.settledAt}</em>}</span></article></div>
        {selected.status==='DRAFT'&&<section className="ci-browse-entry"><div><Search/><span><strong>Tambah aksesori melalui browser</strong><small>Cari kode, nama, atau kategori; barang tidak ditumpuk di halaman nota.</small></span></div><button className="soft-btn" onClick={()=>setCatalogOpen(true)}><Search/> Browse aksesori</button></section>}
        <section className="ci-lines"><div className="ci-line-head"><span>Barang detail</span><span>Stock On Hand</span><span>Qty ambil</span><span>Harga jual snapshot</span><span>Nilai kasbon</span><span/></div>{selected.lines.map((line)=><article key={line.id}><span><strong>{line.item}</strong><small>{line.id} · BOM kategori {line.category}</small></span><span><strong>{line.stock} {line.unit}</strong><small>Moving avg {money(line.averageCost)}</small></span><label><input disabled={selected.status!=='DRAFT'} inputMode="numeric" value={line.qty} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateQty(line.id,event.target.value)}/><small>{line.unit}</small></label><span><strong>{money(line.sellingPrice)}</strong><small>Effective snapshot</small></span><b>{money(lineTotal(line))}</b><button disabled={selected.status!=='DRAFT'} aria-label={`Hapus ${line.item}`} onClick={()=>removeLine(line.id)}><X/></button></article>)}{selected.lines.length===0&&<div className="ci-empty"><PackageMinus/><strong>Belum ada aksesori</strong><small>Buka browser lalu pilih barang yang benar-benar diambil.</small></div>}</section>
        <label className="ci-note"><span>CATATAN SINGKAT</span><textarea disabled={selected.status!=='DRAFT'} value={selected.note} onChange={(event)=>updateDocument({note:event.target.value})} placeholder="Arahan atau kondisi pengambilan..."/></label>
        <div className="ci-equation"><span><small>HPP STOK</small><strong>{money(selected.lines.reduce((sum,line)=>sum+line.qty*line.averageCost,0))}</strong></span><i>≠</i><span><small>HARGA JUAL MANDOR</small><strong>{money(total)}</strong></span><i>→</i><span className="result"><small>KASBON PAYROLL</small><strong>{money(total)}</strong></span></div>
        <div className="ci-guard"><ShieldCheck/><span><strong>BOM tetap kategori; pengambilan tetap barang detail.</strong><small>Kancing Silver/Metal sama-sama memenuhi kategori Kancing, tetapi stok, moving average HPP, dan harga jual mandor tetap per detail.</small></span></div>
        {notice&&<div className="ci-notice"><CheckCircle2/> {notice}</div>}
        <footer><span>{selected.settledAt?'Nota sudah diselesaikan di payroll dan terkunci.':selected.status==='DRAFT'?'Draft belum mengurangi stok atau membentuk kasbon.':'Posted tidak diedit atau dihapus; koreksi lewat reversal.'}</span>{selected.status==='DRAFT'?<><button className="soft-btn" onClick={()=>setNotice('Draft disimpan sebagai simulasi; backend belum berubah.')}>Simpan draft</button><button className="primary-btn" disabled={!canPost} onClick={()=>setReviewOpen(true)}>Review & post <ArrowRight/></button></>:<button className="soft-btn" disabled={selected.status!=='POSTED'||Boolean(selected.settledAt)} onClick={()=>setReverseOpen(true)}><Undo2/> Reverse nota</button>}</footer>
      </main> : <main className="ci-no-selection"><Search/><strong>Tidak ada detail untuk ditampilkan</strong><small>Sesuaikan filter browser di atas.</small></main>}
    </section>
    {catalogOpen&&selected&&<div className="ci-backdrop" onMouseDown={()=>setCatalogOpen(false)}><section className="ci-modal ci-catalog-modal" role="dialog" aria-modal="true" aria-labelledby="ci-catalog-title" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>MASTER AKSESORI · STOCK ON HAND</span><h2 id="ci-catalog-title">Browse aksesori</h2><p>Pilih barang detail yang benar-benar keluar untuk {selected.mandor}.</p></div><button onClick={()=>setCatalogOpen(false)} aria-label="Tutup"><X/></button></header><div className="ci-catalog-toolbar"><label className="ci-search"><Search/><input autoFocus value={catalogQuery} onChange={(event)=>setCatalogQuery(event.target.value)} placeholder="Cari kode, nama, kategori..."/></label><EnterpriseSelect label="KATEGORI" value={catalogCategory} options={['Semua kategori',...new Set(catalog.map((item)=>item.category))]} onChange={setCatalogCategory}/></div><div className="ci-catalog-results">{availableCatalog.map((item)=>{const added=selected.lines.some((line)=>line.id===item.id);return <article key={item.id}><span><small>{item.id} · {item.category}</small><strong>{item.item}</strong><em>{item.stock.toLocaleString('id-ID')} {item.unit} On Hand</em></span><span><small>HARGA MANDOR</small><strong>{money(item.sellingPrice)}</strong><em>Moving avg {money(item.averageCost)}</em></span><button disabled={added} onClick={()=>addLine(item)}>{added?<CheckCircle2/>:<Plus/>}{added?'Sudah dipilih':'Tambah'}</button></article>})}{availableCatalog.length===0&&<div className="ci-empty"><Search/><strong>Aksesori tidak ditemukan</strong><small>Coba kata kunci atau kategori lain.</small></div>}</div><footer><span>{selected.lines.length} barang sudah ada di draft</span><button className="primary-btn" onClick={()=>setCatalogOpen(false)}>Selesai memilih</button></footer></section></div>}
    {reviewOpen&&selected&&<div className="ci-backdrop" onMouseDown={()=>setReviewOpen(false)}><section className="ci-modal" role="dialog" aria-modal="true" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>IMPACT PREVIEW</span><h2>Post Nota Ambil Aksesori?</h2><p>{selected.number} · {selected.mandor} · {selected.productionBatch}</p></div><button onClick={()=>setReviewOpen(false)}><X/></button></header><div className="ci-impact"><article><PackageMinus/><span><small>STOCK ON HAND</small><strong>− {selected.lines.reduce((sum,line)=>sum+line.qty,0)} unit</strong></span></article><ArrowRight/><article><WalletCards/><span><small>KASBON MANDOR</small><strong>+ {money(total)}</strong></span></article><ArrowRight/><article><Link2/><span><small>PAYROLL SOURCE</small><strong>{selected.number}</strong></span></article></div><div className="ci-modal-guard"><LockKeyhole/><span><strong>Satu transaksi atomik</strong><small>Stock movement, costing snapshot, contractor issue, dan subledger kasbon harus berhasil bersama; request berulang memakai idempotency key yang sama.</small></span></div><footer><button className="soft-btn" onClick={()=>setReviewOpen(false)}>Kembali</button><button className="primary-btn" onClick={post}><ShieldCheck/> Post simulasi</button></footer></section></div>}
    {reverseOpen&&selected&&<div className="ci-backdrop" onMouseDown={()=>setReverseOpen(false)}><section className="ci-modal reverse" role="alertdialog" aria-modal="true" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>REVERSAL · POSTED SOURCE</span><h2>Reverse {selected.number}?</h2><p>Nota asal tidak dihapus. Stock dan kasbon dipulihkan lewat dokumen lawan.</p></div><button onClick={()=>setReverseOpen(false)}><X/></button></header><div className="ci-modal-warning"><AlertTriangle/><span><strong>Server akan memblokir bila kasbon sudah diselesaikan.</strong><small>Jangan reverse hanya untuk mengganti catatan; gunakan ketika pengambilan memang batal atau salah barang/qty.</small></span></div><label className="ci-note"><span>CATATAN SINGKAT · WAJIB</span><textarea autoFocus value={reverseNote} onChange={(event)=>setReverseNote(event.target.value)} placeholder="Contoh: salah Batch Distribusi, barang belum dipakai."/></label><footer><button className="soft-btn" onClick={()=>setReverseOpen(false)}>Batal</button><button className="danger-btn" disabled={reverseNote.trim().length<4} onClick={reverse}><Undo2/> Reverse simulasi</button></footer></section></div>}
  </>
}

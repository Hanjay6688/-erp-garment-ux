import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Boxes, Check, CheckCircle2, Clock3, History,
  Link2, LockKeyhole, PackageMinus, Plus, ReceiptText, Search, ShieldCheck,
  Undo2, UserRound, WalletCards, X,
} from 'lucide-react'
import './contractor-issue.css'

type IssueStatus='DRAFT'|'POSTED'|'REVERSED'
type IssueLine={id:string;item:string;category:string;qty:number;unit:string;stock:number;averageCost:number;sellingPrice:number}
type IssueDocument={number:string;mandor:string;parent:string;batch:string;location:string;issuedAt:string;status:IssueStatus;rowVersion:number;note:string;lines:IssueLine[]}

const catalog:IssueLine[]=[
  {id:'ACC-BTN-017',item:'Kancing Jeans 17 mm · Silver',category:'Kancing',qty:0,unit:'pcs',stock:4800,averageCost:620,sellingPrice:750},
  {id:'ACC-ZIP-014',item:'Resleting 14 cm · Black',category:'Resleting',qty:0,unit:'pcs',stock:2200,averageCost:5200,sellingPrice:6500},
  {id:'ACC-RVT-011',item:'Rivet Copper',category:'Rivet',qty:0,unit:'pcs',stock:3600,averageCost:780,sellingPrice:900},
  {id:'ACC-LBL-004',item:'Label Woven Vivo',category:'Label',qty:0,unit:'pcs',stock:8000,averageCost:530,sellingPrice:750},
]

const seedDocuments:IssueDocument[]=[
  {number:'NAA-260827-021',mandor:'Mandor Budi',parent:'POT-260827-042',batch:'042-03',location:'Gudang Aksesori Utama',issuedAt:'27 Agu 2026 · 10:06',status:'DRAFT',rowVersion:2,note:'Persiapan jahit batch hitam.',lines:[{...catalog[1],qty:72},{...catalog[3],qty:240}]},
  {number:'NAA-260826-018',mandor:'Mandor Budi',parent:'POT-260826-041',batch:'041-01',location:'Gudang Aksesori Utama',issuedAt:'26 Agu 2026 · 14:22',status:'POSTED',rowVersion:4,note:'Kebutuhan aktual child batch pertama.',lines:[{...catalog[0],qty:480},{...catalog[2],qty:480}]},
  {number:'NAA-260824-019',mandor:'Mandor Rian',parent:'POT-260824-039',batch:'039-02',location:'Gudang Aksesori Utama',issuedAt:'24 Agu 2026 · 08:44',status:'REVERSED',rowVersion:6,note:'Batch mandor dibatalkan sebelum jahit.',lines:[{...catalog[3],qty:500}]},
]

const money=(value:number)=>new Intl.NumberFormat('id-ID',{style:'currency',currency:'IDR',maximumFractionDigits:0}).format(value)
const lineTotal=(line:IssueLine)=>line.qty*line.sellingPrice
const documentTotal=(document:IssueDocument)=>document.lines.reduce((sum,line)=>sum+lineTotal(line),0)

function Status({value}:{value:IssueStatus}){return <em className={`ci-status ${value.toLowerCase()}`}>{value}</em>}

export default function ContractorIssuePage(){
  const [documents,setDocuments]=useState(seedDocuments)
  const [selectedNumber,setSelectedNumber]=useState(seedDocuments[0].number)
  const [query,setQuery]=useState('')
  const [status,setStatus]=useState<'ALL'|IssueStatus>('ALL')
  const [reviewOpen,setReviewOpen]=useState(false)
  const [reverseOpen,setReverseOpen]=useState(false)
  const [reverseNote,setReverseNote]=useState('')
  const [notice,setNotice]=useState('')
  const selected=documents.find((document)=>document.number===selectedNumber)??documents[0]
  const visible=useMemo(()=>documents.filter((document)=>`${document.number} ${document.mandor} ${document.parent} ${document.batch}`.toLowerCase().includes(query.toLowerCase())&&(status==='ALL'||document.status===status)),[documents,query,status])
  const updateDocument=(patch:Partial<IssueDocument>)=>setDocuments((current)=>current.map((document)=>document.number===selected.number?{...document,...patch}:document))
  const updateQty=(id:string,raw:string)=>{
    if(selected.status!=='DRAFT')return
    const source=selected.lines.find((line)=>line.id===id)
    const qty=Math.min(source?.stock??0,Math.max(0,Number(raw.replace(/\D/g,''))||0))
    updateDocument({lines:selected.lines.map((line)=>line.id===id?{...line,qty}:line)})
    setNotice('')
  }
  const removeLine=(id:string)=>selected.status==='DRAFT'&&updateDocument({lines:selected.lines.filter((line)=>line.id!==id)})
  const addLine=(item:IssueLine)=>{
    if(selected.status!=='DRAFT'||selected.lines.some((line)=>line.id===item.id))return
    updateDocument({lines:[...selected.lines,{...item,qty:1}]})
  }
  const createDraft=()=>{
    const next:IssueDocument={number:`NAA-SIM-${String(documents.length+1).padStart(3,'0')}`,mandor:'Mandor Afat',parent:'POT-260827-042',batch:'042-03',location:'Gudang Aksesori Utama',issuedAt:'28 Agu 2026 · simulasi',status:'DRAFT',rowVersion:1,note:'',lines:[]}
    setDocuments((current)=>[next,...current]);setSelectedNumber(next.number);setNotice('Draft baru terbentuk lokal. Backend belum berubah.')
  }
  const post=()=>{
    updateDocument({status:'POSTED',rowVersion:selected.rowVersion+1})
    setReviewOpen(false);setNotice(`${selected.number} diposting sebagai simulasi. Stock On Hand dan kasbon belum berubah di backend.`)
  }
  const reverse=()=>{
    updateDocument({status:'REVERSED',rowVersion:selected.rowVersion+1,note:`${selected.note} · Reverse: ${reverseNote.trim()}`})
    setReverseOpen(false);setReverseNote('');setNotice(`Reversal ${selected.number} terbentuk sebagai simulasi; nota asal tetap ada.`)
  }
  const total=documentTotal(selected)
  const canPost=selected.status==='DRAFT'&&selected.lines.length>0&&selected.lines.every((line)=>line.qty>0&&line.qty<=line.stock)&&selected.note.trim().length>=4

  return <>
    <section className="hero-copy compact ci-hero"><div><div className="eyebrow">PRODUKSI · MATERIAL MANDOR</div><h1>Nota Ambil Mandor</h1><p>Catat aksesori atau bahan detail yang benar-benar diambil mandor. Posting langsung mengurangi Stock On Hand dan membentuk kasbon; payroll hanya membaca nota posted.</p></div><button className="primary-btn" onClick={createDraft}><Plus/> Nota baru</button></section>
    <section className="ci-metrics"><article><span>NOTA TERBUKA</span><strong>{documents.filter((item)=>item.status==='DRAFT').length}</strong><small>Belum mengubah stok</small></article><article><span>POSTED HARI INI</span><strong>{documents.filter((item)=>item.status==='POSTED').length}</strong><small>Terhubung ke payroll</small></article><article><span>NILAI KASBON</span><strong>{money(documents.filter((item)=>item.status==='POSTED').reduce((sum,item)=>sum+documentTotal(item),0))}</strong><small>Harga jual snapshot</small></article><article><span>AVAILABILITY</span><strong>Stock On Hand</strong><small>Tanpa reserved / ATP</small></article></section>
    <section className="panel ci-layout">
      <aside><header><div><span>BROWSER NOTA</span><strong>{visible.length} dokumen</strong></div><ReceiptText/></header><label className="ci-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari nota, mandor, Potongan..."/></label><select value={status} onChange={(event)=>setStatus(event.target.value as typeof status)}><option value="ALL">Semua status</option><option>DRAFT</option><option>POSTED</option><option>REVERSED</option></select><div className="ci-browser">{visible.map((document)=><button className={document.number===selected.number?'active':''} key={document.number} onClick={()=>{setSelectedNumber(document.number);setNotice('')}}><i><PackageMinus/></i><span><strong>{document.number}</strong><small>{document.mandor} · {document.parent}</small><em>{document.batch} · {document.issuedAt}</em></span><b>{money(documentTotal(document))}</b><Status value={document.status}/></button>)}</div></aside>
      <main><header className="ci-detail-head"><div><span>{selected.status==='DRAFT'?'DRAFT · BOLEH DIEDIT':'POSTED SOURCE · READ ONLY'}</span><h2>{selected.number}</h2><p>{selected.parent} · Child {selected.batch}</p></div><div><Status value={selected.status}/><small>row version {selected.rowVersion}</small></div></header>
        <div className="ci-facts"><article><UserRound/><span><small>MANDOR</small>{selected.status==='DRAFT'?<select value={selected.mandor} onChange={(event)=>updateDocument({mandor:event.target.value})}><option>Mandor Afat</option><option>Mandor Budi</option><option>Mandor Dedi</option><option>Mandor Rian</option></select>:<strong>{selected.mandor}</strong>}</span></article><article><Boxes/><span><small>LOKASI SUMBER</small><strong>{selected.location}</strong></span></article><article><Clock3/><span><small>WAKTU AMBIL</small><strong>{selected.issuedAt}</strong></span></article></div>
        {selected.status==='DRAFT'&&<section className="ci-catalog"><span>TAMBAH DARI MASTER AKSESORI</span><div>{catalog.map((item)=><button disabled={selected.lines.some((line)=>line.id===item.id)} key={item.id} onClick={()=>addLine(item)}><Plus/><span><strong>{item.item}</strong><small>{item.stock} {item.unit} On Hand · jual {money(item.sellingPrice)}</small></span></button>)}</div></section>}
        <section className="ci-lines"><div className="ci-line-head"><span>Barang detail</span><span>Stock On Hand</span><span>Qty ambil</span><span>Harga jual snapshot</span><span>Nilai kasbon</span><span/></div>{selected.lines.map((line)=><article key={line.id}><span><strong>{line.item}</strong><small>{line.id} · BOM kategori {line.category}</small></span><span><strong>{line.stock} {line.unit}</strong><small>Moving avg {money(line.averageCost)}</small></span><label><input disabled={selected.status!=='DRAFT'} inputMode="numeric" value={line.qty} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateQty(line.id,event.target.value)}/><small>{line.unit}</small></label><span><strong>{money(line.sellingPrice)}</strong><small>Effective snapshot</small></span><b>{money(lineTotal(line))}</b><button disabled={selected.status!=='DRAFT'} aria-label={`Hapus ${line.item}`} onClick={()=>removeLine(line.id)}><X/></button></article>)}{selected.lines.length===0&&<div className="ci-empty"><PackageMinus/><strong>Belum ada barang</strong><small>Browse master di atas lalu tambah item yang benar-benar diambil.</small></div>}</section>
        <label className="ci-note"><span>CATATAN SINGKAT</span><textarea disabled={selected.status!=='DRAFT'} value={selected.note} onChange={(event)=>updateDocument({note:event.target.value})} placeholder="Arahan atau kondisi pengambilan..."/></label>
        <div className="ci-equation"><span><small>HPP STOK</small><strong>{money(selected.lines.reduce((sum,line)=>sum+line.qty*line.averageCost,0))}</strong></span><i>≠</i><span><small>HARGA JUAL MANDOR</small><strong>{money(total)}</strong></span><i>→</i><span className="result"><small>KASBON PAYROLL</small><strong>{money(total)}</strong></span></div>
        <div className="ci-guard"><ShieldCheck/><span><strong>BOM kerja tetap kategori; pengambilan tetap barang detail.</strong><small>Kancing Silver/Metal sama-sama memenuhi kategori Kancing, tetapi stok, moving average HPP, dan harga jual mandor tetap per detail.</small></span></div>
        {notice&&<div className="ci-notice"><CheckCircle2/> {notice}</div>}
        <footer><span>{selected.status==='DRAFT'?'Draft belum mengurangi stok atau membentuk kasbon.':'Posted tidak diedit atau dihapus; koreksi lewat reversal.'}</span>{selected.status==='DRAFT'?<><button className="soft-btn" onClick={()=>setNotice('Draft disimpan sebagai simulasi; backend belum berubah.')}>Simpan draft</button><button className="primary-btn" disabled={!canPost} onClick={()=>setReviewOpen(true)}>Review & post <ArrowRight/></button></>:<button className="soft-btn" disabled={selected.status!=='POSTED'} onClick={()=>setReverseOpen(true)}><Undo2/> Reverse nota</button>}</footer>
      </main>
    </section>
    {reviewOpen&&<div className="ci-backdrop" onMouseDown={()=>setReviewOpen(false)}><section className="ci-modal" role="dialog" aria-modal="true" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>IMPACT PREVIEW</span><h2>Post Nota Ambil Mandor?</h2><p>{selected.number} · {selected.mandor} · {selected.parent}</p></div><button onClick={()=>setReviewOpen(false)}><X/></button></header><div className="ci-impact"><article><PackageMinus/><span><small>STOCK ON HAND</small><strong>− {selected.lines.reduce((sum,line)=>sum+line.qty,0)} unit</strong></span></article><ArrowRight/><article><WalletCards/><span><small>KASBON MANDOR</small><strong>+ {money(total)}</strong></span></article><ArrowRight/><article><Link2/><span><small>PAYROLL SOURCE</small><strong>{selected.number}</strong></span></article></div><div className="ci-modal-guard"><LockKeyhole/><span><strong>Satu transaksi atomik</strong><small>Stock movement, costing snapshot, contractor issue, dan subledger kasbon harus berhasil bersama; request berulang memakai idempotency key yang sama.</small></span></div><footer><button className="soft-btn" onClick={()=>setReviewOpen(false)}>Kembali</button><button className="primary-btn" onClick={post}><ShieldCheck/> Post simulasi</button></footer></section></div>}
    {reverseOpen&&<div className="ci-backdrop" onMouseDown={()=>setReverseOpen(false)}><section className="ci-modal reverse" role="alertdialog" aria-modal="true" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>REVERSAL · POSTED SOURCE</span><h2>Reverse {selected.number}?</h2><p>Nota asal tidak dihapus. Stock dan kasbon dipulihkan lewat dokumen lawan.</p></div><button onClick={()=>setReverseOpen(false)}><X/></button></header><div className="ci-modal-warning"><AlertTriangle/><span><strong>Server akan memblokir bila kasbon sudah diselesaikan.</strong><small>Jangan reverse hanya untuk mengganti catatan; gunakan ketika pengambilan memang batal atau salah barang/qty.</small></span></div><label className="ci-note"><span>CATATAN SINGKAT · WAJIB</span><textarea autoFocus value={reverseNote} onChange={(event)=>setReverseNote(event.target.value)} placeholder="Contoh: salah child batch, barang belum dipakai."/></label><footer><button className="soft-btn" onClick={()=>setReverseOpen(false)}>Batal</button><button className="danger-btn" disabled={reverseNote.trim().length<4} onClick={reverse}><Undo2/> Reverse simulasi</button></footer></section></div>}
  </>
}

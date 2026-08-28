import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Check, ChevronRight, ClipboardCheck,
  FileClock, History, Layers3, LockKeyhole, Minus, Plus, RotateCcw,
  Scissors, Search, ShieldCheck, Undo2, X,
} from 'lucide-react'
import './cutting-correction.css'

type CorrectionType = 'RECOUNT' | 'REDISTRIBUTION' | 'OTHER'
type HistoryStatus = 'POSTED' | 'REVERSED' | 'REVERSAL'
type SizeLine = { size: string; current: number }
type CuttingGroup = {
  id: string
  executor: string
  status: string
  downstreamFloor: number
  sizes: SizeLine[]
}
type CuttingBatch = {
  id: string
  po: string
  model: string
  material: string
  cutAt: string
  rowVersion: number
  original: number
  adjustment: number
  effective: number
  downstreamFloor: number
  groups: CuttingGroup[]
}
type CorrectionHistory = {
  id: string
  batchId: string
  number: string
  type: CorrectionType | 'REVERSAL'
  reasonCode: string
  reason: string
  delta: number
  happenedAt: string
  actor: string
  status: HistoryStatus
  reversedBy?: string
}

const batches: CuttingBatch[] = [
  {
    id:'CUT-260827-042', po:'PO-260812-031', model:'Kulot Lucy', material:'Lucy · Sinaran',
    cutAt:'27 Agu 2026 · 17:40', rowVersion:7, original:660, adjustment:8, effective:668,
    downstreamFloor:188,
    groups:[
      { id:'POT-260827-042', executor:'Mandor Afat', status:'PICKED_UP', downstreamFloor:188, sizes:[{size:'31',current:229},{size:'32',current:221},{size:'33',current:218}] },
    ],
  },
  {
    id:'CUT-260827-041', po:'PO-260812-028', model:'Malibu Regular', material:'1069 Ori · Sinaran',
    cutAt:'27 Agu 2026 · 15:12', rowVersion:4, original:488, adjustment:0, effective:488,
    downstreamFloor:0,
    groups:[
      { id:'POT-260827-041-A', executor:'Mandor Asep', status:'PICKED_UP', downstreamFloor:0, sizes:[{size:'28',current:84},{size:'29',current:80},{size:'30',current:80}] },
      { id:'POT-260827-041-B', executor:'Mandor Dedi', status:'CUT', downstreamFloor:0, sizes:[{size:'28',current:80},{size:'29',current:82},{size:'30',current:82}] },
    ],
  },
  {
    id:'CUT-260826-039', po:'PO-260811-024', model:'Zodiak Cargo', material:'Zodiak KW · Sumber Cahaya',
    cutAt:'26 Agu 2026 · 16:08', rowVersion:11, original:342, adjustment:-2, effective:340,
    downstreamFloor:340,
    groups:[
      { id:'POT-260826-039', executor:'Mandor Intan', status:'SEWING', downstreamFloor:340, sizes:[{size:'34',current:112},{size:'35',current:114},{size:'36',current:114}] },
    ],
  },
]

const initialHistory: CorrectionHistory[] = [
  { id:'cqc-1', batchId:'CUT-260827-042', number:'CQC-20260828-000014', type:'RECOUNT', reasonCode:'PHYSICAL_RECOUNT', reason:'Hitung ulang meja sortir menemukan delapan pcs tambahan.', delta:8, happenedAt:'28 Agu 2026 · 08:44', actor:'Nina · Produksi', status:'POSTED' },
  { id:'cqc-2', batchId:'CUT-260826-039', number:'CQC-20260827-000012', type:'RECOUNT', reasonCode:'COUNT_ERROR', reason:'Dua pcs tercatat ganda pada lembar cutting.', delta:-2, happenedAt:'27 Agu 2026 · 16:32', actor:'Owner', status:'POSTED' },
  { id:'cqc-3', batchId:'CUT-260827-041', number:'CQC-20260827-000011', type:'REDISTRIBUTION', reasonCode:'SIZE_SWAP', reason:'Size 28 dan 29 tertukar saat input awal.', delta:0, happenedAt:'27 Agu 2026 · 15:28', actor:'Nina · Produksi', status:'REVERSED', reversedBy:'CQC-20260827-000013' },
]

const formatNumber = (value: number) => new Intl.NumberFormat('id-ID', { maximumFractionDigits:0 }).format(value)
const lineKey = (groupId: string, size: string) => `${groupId}::${size}`

export default function CuttingCorrectionPage({ onOpenDistribution }: { onOpenDistribution: () => void }) {
  const [query,setQuery] = useState('')
  const [selectedBatchId,setSelectedBatchId] = useState(batches[0].id)
  const [type,setType] = useState<CorrectionType>('RECOUNT')
  const [reasonCode,setReasonCode] = useState('PHYSICAL_RECOUNT')
  const [reason,setReason] = useState('')
  const [deltas,setDeltas] = useState<Record<string,string>>({})
  const [reviewOpen,setReviewOpen] = useState(false)
  const [reverseTarget,setReverseTarget] = useState<CorrectionHistory|null>(null)
  const [reverseReason,setReverseReason] = useState('')
  const [history,setHistory] = useState(initialHistory)
  const [notice,setNotice] = useState('')

  const visibleBatches = useMemo(()=>batches.filter((batch)=>`${batch.id} ${batch.po} ${batch.model} ${batch.material}`.toLowerCase().includes(query.toLowerCase())),[query])
  const selected = batches.find((batch)=>batch.id===selectedBatchId) ?? batches[0]
  const draftLines = selected.groups.flatMap((group)=>group.sizes.map((line)=>({
    group,
    size:line.size,
    current:line.current,
    delta:Number(deltas[lineKey(group.id,line.size)] || 0),
  })))
  const changedLines = draftLines.filter((line)=>line.delta!==0)
  const netDelta = changedLines.reduce((sum,line)=>sum+line.delta,0)
  const groupChecks = selected.groups.map((group)=>{
    const current=group.sizes.reduce((sum,line)=>sum+line.current,0)
    const delta=group.sizes.reduce((sum,line)=>sum+Number(deltas[lineKey(group.id,line.size)]||0),0)
    return { id:group.id, current, delta, after:current+delta, floor:group.downstreamFloor }
  })
  const belowFloor = groupChecks.some((group)=>group.after<group.floor || group.after<0)
  const redistributionInvalid = type==='REDISTRIBUTION' && netDelta!==0
  const canReview = changedLines.length>0 && reason.trim().length>=8 && !belowFloor && !redistributionInvalid
  const selectedHistory = history.filter((item)=>item.batchId===selected.id)

  const updateDelta = (groupId:string,size:string,value:string) => {
    const clean=value.replace(/[^0-9-]/g,'').replace(/(?!^)-/g,'')
    setDeltas((current)=>({...current,[lineKey(groupId,size)]:clean}))
    setNotice('')
  }
  const nudgeDelta = (groupId:string,size:string,amount:number) => {
    const key=lineKey(groupId,size)
    setDeltas((current)=>({...current,[key]:String(Number(current[key]||0)+amount)}))
    setNotice('')
  }
  const selectBatch = (id:string) => {
    setSelectedBatchId(id)
    setDeltas({})
    setReason('')
    setNotice('')
  }
  const confirmSimulation = () => {
    const number=`CQC-SIM-${String(history.length+1).padStart(3,'0')}`
    setHistory((current)=>[{
      id:`sim-${Date.now()}`,batchId:selected.id,number,type,reasonCode,reason:reason.trim(),delta:netDelta,
      happenedAt:'28 Agu 2026 · simulasi',actor:'Owner',status:'POSTED',
    },...current])
    setReviewOpen(false)
    setDeltas({})
    setReason('')
    setNotice(`${number} terbentuk sebagai simulasi lokal. RPC v2.6.9 siap, tetapi aplikasi belum mengirim write ke Supabase.`)
  }
  const confirmReverseSimulation = () => {
    if(!reverseTarget || reverseReason.trim().length<8)return
    const reversalNumber=`CQC-SIM-RV-${String(history.length+1).padStart(3,'0')}`
    setHistory((current)=>[
      { id:`rv-${Date.now()}`,batchId:reverseTarget.batchId,number:reversalNumber,type:'REVERSAL',reasonCode:'REVERSAL',reason:reverseReason.trim(),delta:-reverseTarget.delta,happenedAt:'28 Agu 2026 · simulasi',actor:'Owner',status:'REVERSAL' },
      ...current.map((item)=>item.id===reverseTarget.id?{...item,status:'REVERSED' as const,reversedBy:reversalNumber}:item),
    ])
    setNotice(`${reverseTarget.number} dibalik pada simulasi lokal. Dokumen asal tetap ada dan tidak diedit.`)
    setReverseTarget(null)
    setReverseReason('')
  }

  return <>
    <section className="hero-copy compact cqc-hero">
      <div><div className="eyebrow">PRODUKSI · QUANTITY CONTROL</div><h1>Koreksi Potongan</h1><p>Tambah, kurangi, atau redistribusi hasil cutting lewat dokumen baru. Sumber tidak ditimpa; histori dan dampak HPP tetap bisa ditelusuri.</p></div>
      <div className="cqc-contract"><ShieldCheck/><div><span>BACKEND v2.6.9 READY</span><strong>Idempotent · row-version · append-only</strong><small>Frontend masih memakai data simulasi sampai Supabase client disambungkan.</small></div></div>
    </section>

    <section className="cqc-metrics">
      <article><span>BATCH TERPILIH</span><strong>{selected.id}</strong><small>{selected.po} · {selected.model}</small></article>
      <article><span>EFFECTIVE QTY</span><strong>{formatNumber(selected.effective)} pcs</strong><small>{formatNumber(selected.original)} original · {selected.adjustment>=0?'+':''}{selected.adjustment} adjustment</small></article>
      <article className="floor"><span>DOWNSTREAM FLOOR</span><strong>{formatNumber(selected.downstreamFloor)} pcs</strong><small>Tertinggi dari jahit/WIP/laundry/QC/FG/BS</small></article>
      <article className="version"><span>ROW VERSION</span><strong>v{selected.rowVersion}</strong><small>Draft basi akan ditolak server</small></article>
    </section>

    <section className="cqc-layout">
      <aside className="panel cqc-browser">
        <header><div><span>BROWSE CUTTING BATCH</span><strong>{visibleBatches.length} batch tampil</strong></div><History/></header>
        <label><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari batch, PO, model, bahan..."/></label>
        <div>{visibleBatches.map((batch)=><button key={batch.id} className={selected.id===batch.id?'active':''} onClick={()=>selectBatch(batch.id)}><span className="cqc-batch-index"><Scissors/></span><div><strong>{batch.id}</strong><small>{batch.po} · {batch.model}</small><em>{batch.material} · {batch.cutAt}</em></div><b>{formatNumber(batch.effective)} pcs</b><ChevronRight/></button>)}</div>
        <footer><button onClick={onOpenDistribution}>Buka Bagi Potongan <ArrowRight/></button><small>Pembagian batch dan koreksi sumber tetap dipisah.</small></footer>
      </aside>

      <main className="panel cqc-editor">
        <header className="cqc-editor-head"><div><span>BATCH TERPILIH</span><h2>{selected.id} · {selected.model}</h2><p>{selected.po} · {selected.material} · {selected.groups.length} Potongan</p></div><div><span>VERSI YANG DIREVIEW</span><strong>v{selected.rowVersion}</strong><small>Optimistic lock aktif</small></div></header>

        <div className="cqc-equation">
          <span><small>ORIGINAL</small><strong>{formatNumber(selected.original)}</strong></span><i>+</i>
          <span><small>POSTED ADJUSTMENT</small><strong>{selected.adjustment>=0?'+':''}{selected.adjustment}</strong></span><i>+</i>
          <span className={netDelta===0?'neutral':netDelta>0?'positive':'negative'}><small>DRAFT SEKARANG</small><strong>{netDelta>0?'+':''}{netDelta}</strong></span><i>=</i>
          <span className={belowFloor?'danger':'result'}><small>SETELAH KOREKSI</small><strong>{formatNumber(selected.effective+netDelta)} pcs</strong></span>
        </div>

        <section className="cqc-meta">
          <label><span>JENIS KOREKSI</span><select value={type} onChange={(event)=>setType(event.target.value as CorrectionType)}><option value="RECOUNT">Recount · total boleh berubah</option><option value="REDISTRIBUTION">Redistribusi · net harus 0</option><option value="OTHER">Lainnya · alasan spesifik</option></select></label>
          <label><span>REASON CODE</span><select value={reasonCode} onChange={(event)=>setReasonCode(event.target.value)}><option>PHYSICAL_RECOUNT</option><option>SIZE_SWAP</option><option>COUNT_ERROR</option><option>LEGACY_CLEANUP</option><option>OTHER</option></select></label>
          <label><span>WAKTU FISIK</span><input type="datetime-local" defaultValue="2026-08-28T10:30"/></label>
        </section>

        <section className="cqc-lines" data-keyboard-grid>
          <header><div><span>BARIS POTONGAN & SIZE</span><strong>Isi hanya sel yang berubah</strong></div><button onClick={()=>setDeltas({})}><RotateCcw/> Reset draft</button></header>
          {selected.groups.map((group)=>{
            const check=groupChecks.find((item)=>item.id===group.id)!
            return <article key={group.id}>
              <div className="cqc-group-head"><div><span>{group.id}</span><strong>{group.executor}</strong><small>Status {group.status}</small></div><div className={check.after<check.floor?'danger':'safe'}><span>SETELAH / FLOOR</span><strong>{check.after} / {check.floor} pcs</strong><small>{check.after<check.floor?'Di bawah bukti downstream':'Masih aman'}</small></div></div>
              <div className="cqc-line-head"><span>Size</span><span>Saat ini</span><span>Perubahan</span><span>Sesudah</span></div>
              {group.sizes.map((line,index)=>{const key=lineKey(group.id,line.size);const delta=Number(deltas[key]||0);const after=line.current+delta;return <div className={`cqc-line ${after<0?'invalid':''}`} key={key}><strong>{line.size}</strong><span>{line.current} pcs</span><div><button aria-label={`Kurangi Size ${line.size}`} onClick={()=>nudgeDelta(group.id,line.size,-1)}><Minus/></button><input data-grid-row={index} data-grid-col={0} inputMode="numeric" value={deltas[key]??''} placeholder="0" onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateDelta(group.id,line.size,event.target.value)}/><button aria-label={`Tambah Size ${line.size}`} onClick={()=>nudgeDelta(group.id,line.size,1)}><Plus/></button></div><b className={delta===0?'':delta>0?'positive':'negative'}>{after} pcs</b></div>})}
            </article>
          })}
        </section>

        <label className="cqc-reason"><span>ALASAN LENGKAP · WAJIB</span><textarea value={reason} onChange={(event)=>{setReason(event.target.value);setNotice('')}} placeholder="Apa yang salah, bagaimana dicek ulang, dan siapa yang mengonfirmasi kondisi fisik?"/><small>{reason.trim().length}/8 karakter minimum</small></label>

        <div className={`cqc-guard ${belowFloor||redistributionInvalid?'blocked':'safe'}`}>
          {belowFloor||redistributionInvalid?<AlertTriangle/>:<ShieldCheck/>}
          <div><strong>{belowFloor?'Ditolak: hasil lebih kecil dari bukti downstream':redistributionInvalid?'Redistribusi harus berjumlah net 0':'Server guard siap'}</strong><small>{belowFloor?'Reverse dokumen downstream dulu; jangan mengakali lewat angka size.':redistributionInvalid?`Net draft sekarang ${netDelta>0?'+':''}${netDelta} pcs.`:'Hasil tidak negatif, tidak di bawah floor, dan row-version akan diverifikasi saat submit.'}</small></div>
        </div>
        {notice&&<div className="cqc-notice"><Check/><span>{notice}</span></div>}
        <footer className="cqc-actions"><div><small>{changedLines.length} baris berubah</small><strong>Net {netDelta>0?'+':''}{netDelta} pcs</strong></div><button className="soft-btn" onClick={()=>{setDeltas({});setReason('')}}>Buang draft</button><button className="primary-btn" disabled={!canReview} onClick={()=>setReviewOpen(true)}>Review koreksi <ArrowRight/></button></footer>
      </main>
    </section>

    <section className="panel cqc-history">
      <header><div><span>IMMUTABLE HISTORY</span><h2>Koreksi dan reversal</h2><p>Posted tidak diedit atau dihapus. Kesalahan dibalik dengan dokumen lawan.</p></div><LockKeyhole/></header>
      <div className="cqc-history-head"><span>Nomor / waktu</span><span>Jenis & alasan</span><span>Perubahan</span><span>User</span><span>Status / aksi</span></div>
      {selectedHistory.length>0?selectedHistory.map((item)=><article key={item.id}><span><strong>{item.number}</strong><small>{item.happenedAt}</small></span><span><strong>{item.type} · {item.reasonCode}</strong><small>{item.reason}</small></span><b className={item.delta===0?'':item.delta>0?'positive':'negative'}>{item.delta>0?'+':''}{item.delta} pcs</b><span>{item.actor}</span><div><em className={item.status.toLowerCase()}>{item.status}</em>{item.status==='POSTED'&&item.type!=='REVERSAL'?<button onClick={()=>{setReverseTarget(item);setReverseReason('')}}><Undo2/> Balikkan</button>:<small>{item.reversedBy?`oleh ${item.reversedBy}`:'Dokumen lawan'}</small>}</div></article>):<div className="cqc-history-empty"><FileClock/><strong>Belum ada koreksi</strong><small>Batch ini masih sama dengan hasil cutting awal.</small></div>}
    </section>

    {reviewOpen&&<div className="cqc-backdrop" onMouseDown={()=>setReviewOpen(false)}><section className="cqc-modal" role="dialog" aria-modal="true" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>IMPACT PREVIEW</span><h2>Review sebelum posting</h2><p>{selected.id} · row version v{selected.rowVersion}</p></div><button onClick={()=>setReviewOpen(false)}><X/></button></header><div className="cqc-modal-impact"><article><Layers3/><span><small>QTY SAAT INI</small><strong>{selected.effective} pcs</strong></span></article><i><ArrowRight/></i><article className={netDelta<0?'negative':'positive'}><ClipboardCheck/><span><small>SETELAH POSTING</small><strong>{selected.effective+netDelta} pcs</strong></span></article></div><div className="cqc-modal-facts"><div><span>TIPE</span><strong>{type}</strong></div><div><span>NET DELTA</span><strong>{netDelta>0?'+':''}{netDelta} pcs</strong></div><div><span>BARIS</span><strong>{changedLines.length} perubahan</strong></div><div><span>ALASAN</span><strong>{reasonCode}</strong></div></div><div className="cqc-modal-warning"><ShieldCheck/><div><strong>Atomic domain write</strong><small>Server akan mengunci batch, cek row-version, posting histori, lalu rebuild HPP/GL bila FG dari PO ini sudah ada. Semua berhasil atau semuanya rollback.</small></div></div><footer><button className="soft-btn" onClick={()=>setReviewOpen(false)}>Kembali cek</button><button className="primary-btn" onClick={confirmSimulation}>Konfirmasi simulasi <ArrowRight/></button></footer></section></div>}

    {reverseTarget&&<div className="cqc-backdrop" onMouseDown={()=>setReverseTarget(null)}><section className="cqc-modal reverse" role="dialog" aria-modal="true" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>OWNER / ADMIN ONLY</span><h2>Balikkan koreksi?</h2><p>{reverseTarget.number} · {reverseTarget.delta>0?'+':''}{reverseTarget.delta} pcs</p></div><button onClick={()=>setReverseTarget(null)}><X/></button></header><div className="cqc-reversal-chain"><span><small>DOKUMEN ASAL</small><strong>{reverseTarget.delta>0?'+':''}{reverseTarget.delta} pcs</strong></span><i><Undo2/></i><span><small>DOKUMEN REVERSAL BARU</small><strong>{-reverseTarget.delta>0?'+':''}{-reverseTarget.delta} pcs</strong></span></div><label className="cqc-reason"><span>ALASAN REVERSAL · WAJIB</span><textarea autoFocus value={reverseReason} onChange={(event)=>setReverseReason(event.target.value)} placeholder="Kenapa koreksi ini harus dibalik?"/><small>{reverseReason.trim().length}/8 karakter minimum</small></label><div className="cqc-modal-warning danger"><AlertTriangle/><div><strong>Dokumen asal tidak akan hilang</strong><small>Server membuat baris lawan, mengecek floor downstream lagi, memperbarui HPP bila perlu, dan menolak double reversal.</small></div></div><footer><button className="soft-btn" onClick={()=>setReverseTarget(null)}>Batal</button><button className="danger-btn" disabled={reverseReason.trim().length<8} onClick={confirmReverseSimulation}>Buat reversal <Undo2/></button></footer></section></div>}
  </>
}

type PresewingStatus = 'EDITABLE' | 'NEEDS_REVERSAL' | 'LOCKED'
type PresewingRecord = {
  id: string
  mandor: string
  batches: number
  qty: number
  rowVersion: number
  status: PresewingStatus
  evidence: string
}

const initialPresewingRecords: PresewingRecord[] = [
  { id:'POT-260827-042', mandor:'Mandor Afat', batches:3, qty:668, rowVersion:5, status:'EDITABLE', evidence:'Belum ada jahit, stock issue, atau dokumen downstream.' },
  { id:'POT-260827-041', mandor:'Mandor Asep', batches:2, qty:488, rowVersion:8, status:'NEEDS_REVERSAL', evidence:'Material issue dan jurnal sudah posted; belum ada jahit.' },
  { id:'POT-260826-039', mandor:'Mandor Intan', batches:2, qty:340, rowVersion:12, status:'LOCKED', evidence:'188 pcs sudah tercatat sebagai hasil jahit.' },
]

export function CuttingGroupControlPanel({ onEdit }: { onEdit: () => void }) {
  const [records,setRecords] = useState(initialPresewingRecords)
  const [reverseTarget,setReverseTarget] = useState<PresewingRecord|null>(null)
  const [deleteTarget,setDeleteTarget] = useState<PresewingRecord|null>(null)
  const [reason,setReason] = useState('')
  const [notice,setNotice] = useState('')

  const confirmMaterialReversal = () => {
    if(!reverseTarget || reason.trim().length<8)return
    setRecords((current)=>current.map((item)=>item.id===reverseTarget.id?{
      ...item,status:'EDITABLE',rowVersion:item.rowVersion+1,
      evidence:'Stock movement dan jurnal lama tetap ada; dokumen lawan sudah terbentuk pada simulasi.',
    }:item))
    setNotice(`${reverseTarget.id} sudah dipulihkan pada simulasi. Pembagian boleh diedit/dihapus karena belum ada sewing.`)
    setReverseTarget(null)
    setReason('')
  }
  const confirmDelete = () => {
    if(!deleteTarget || reason.trim().length<8)return
    setRecords((current)=>current.filter((item)=>item.id!==deleteTarget.id))
    setNotice(`${deleteTarget.id} dihapus pada simulasi pre-sewing dengan alasan wajib. Histori reversal stock/jurnal tidak ikut hilang.`)
    setDeleteTarget(null)
    setReason('')
  }

  return <>
    <section className="panel cqc-presew">
      <header><div><span>PRE-SEWING CONTROL</span><h2>Kelola Bagi Potongan yang sudah tersimpan</h2><p>Edit/delete hanya untuk kesalahan sebelum jahit. Kalau material sudah posted, pulihkan stock + jurnal dulu.</p></div><ShieldCheck/></header>
      {notice&&<div className="cqc-notice"><Check/><span>{notice}</span></div>}
      <div className="cqc-presew-grid">{records.map((item)=><article key={item.id} className={item.status.toLowerCase()}><div className="cqc-presew-title"><span>{item.id}</span><strong>{item.mandor}</strong><small>{item.batches} child batch · {item.qty} pcs · row version v{item.rowVersion}</small></div><div className="cqc-presew-state"><em>{item.status==='EDITABLE'?'BOLEH DIUBAH':item.status==='NEEDS_REVERSAL'?'REVERSE DULU':'TERKUNCI'}</em><small>{item.evidence}</small></div><footer>{item.status==='EDITABLE'?<><button className="soft-btn" onClick={onEdit}>Edit pembagian</button><button className="cqc-delete-btn" onClick={()=>{setDeleteTarget(item);setReason('')}}><X/> Hapus pre-sewing</button></>:item.status==='NEEDS_REVERSAL'?<button className="cqc-reverse-flow" onClick={()=>{setReverseTarget(item);setReason('')}}><Undo2/> Pulihkan stock & jurnal</button>:<span><LockKeyhole/> Reverse dokumen jahit/downstream lebih dulu</span>}</footer></article>)}</div>
    </section>

    {reverseTarget&&<div className="cqc-backdrop" onMouseDown={()=>setReverseTarget(null)}><section className="cqc-modal reverse" role="dialog" aria-modal="true" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>CONTROLLED PRE-SEWING REVERSAL</span><h2>Pulihkan stock & jurnal?</h2><p>{reverseTarget.id} · row version v{reverseTarget.rowVersion}</p></div><button onClick={()=>setReverseTarget(null)}><X/></button></header><div className="cqc-modal-warning"><ShieldCheck/><div><strong>Urutan atomik</strong><small>Reverse jurnal return/issue → buat movement lawan → hitung ulang moving average → reset flag material. Kalau stok hasil retur sudah terpakai, seluruh aksi ditolak.</small></div></div><label className="cqc-reason"><span>ALASAN · WAJIB</span><textarea autoFocus value={reason} onChange={(event)=>setReason(event.target.value)} placeholder="Kenapa material flow ini harus dipulihkan?"/><small>{reason.trim().length}/8 karakter minimum</small></label><footer><button className="soft-btn" onClick={()=>setReverseTarget(null)}>Batal</button><button className="primary-btn" disabled={reason.trim().length<8} onClick={confirmMaterialReversal}>Konfirmasi simulasi <Undo2/></button></footer></section></div>}

    {deleteTarget&&<div className="cqc-backdrop" onMouseDown={()=>setDeleteTarget(null)}><section className="cqc-modal reverse" role="dialog" aria-modal="true" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>DESTRUCTIVE · PRE-SEWING ONLY</span><h2>Hapus Bagi Potongan?</h2><p>{deleteTarget.id} · {deleteTarget.batches} child batch · {deleteTarget.qty} pcs</p></div><button onClick={()=>setDeleteTarget(null)}><X/></button></header><div className="cqc-modal-warning danger"><AlertTriangle/><div><strong>Server cek ulang seluruh dependency</strong><small>Sewing, Laundry, QC, FG, BS, payroll, correction history, stock aktif, atau jurnal aktif akan memblokir delete. Request basi juga ditolak oleh row-version.</small></div></div><label className="cqc-reason"><span>ALASAN HAPUS · WAJIB</span><textarea autoFocus value={reason} onChange={(event)=>setReason(event.target.value)} placeholder="Jelaskan salah input yang membuat pembagian ini harus dihapus."/><small>{reason.trim().length}/8 karakter minimum</small></label><footer><button className="soft-btn" onClick={()=>setDeleteTarget(null)}>Batal</button><button className="danger-btn" disabled={reason.trim().length<8} onClick={confirmDelete}>Hapus simulasi <X/></button></footer></section></div>}
  </>
}

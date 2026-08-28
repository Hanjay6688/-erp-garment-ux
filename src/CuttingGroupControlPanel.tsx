import { useState } from 'react'
import { AlertTriangle, Check, LockKeyhole, ShieldCheck, Undo2, X } from 'lucide-react'
import './cutting-correction.css'

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

const initialRecords: PresewingRecord[] = [
  { id:'POT-260827-042', mandor:'Mandor Afat', batches:3, qty:668, rowVersion:5, status:'EDITABLE', evidence:'Belum ada jahit, stock issue, atau dokumen downstream.' },
  { id:'POT-260827-041', mandor:'Mandor Asep', batches:2, qty:488, rowVersion:8, status:'NEEDS_REVERSAL', evidence:'Material issue dan jurnal sudah posted; belum ada jahit.' },
  { id:'POT-260826-039', mandor:'Mandor Intan', batches:2, qty:340, rowVersion:12, status:'LOCKED', evidence:'188 pcs sudah tercatat sebagai hasil jahit.' },
]

export default function CuttingGroupControlPanel({ onEdit }: { onEdit: () => void }) {
  const [records,setRecords] = useState(initialRecords)
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

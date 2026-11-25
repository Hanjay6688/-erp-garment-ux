import { useState } from 'react'
import { ArrowLeft, ArrowRight, Factory, Layers3, Pencil, Plus, Search } from 'lucide-react'
import { browseMatch } from '../browseMatch'
import { ReasonDialog } from './planner/ReasonDialog'
import { readPocketMaterials, savePocketMaterial, type PocketMaterial } from './pocketMaterials'
import { receiptPath } from './pocketReceipts'
import './pocketFabric.css'

export default function PocketMaterialMaster() {
  const [materials, setMaterials] = useState(readPocketMaterials)
  const [query, setQuery] = useState('')
  const [editing, setEditing] = useState<PocketMaterial | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const visible = materials.filter(item=>browseMatch(query,item.name,item.factory,item.supplier))

  function edit(item: PocketMaterial) {
    setError('')
    setNotice('')
    setEditing(item)
  }

  return <div className="pocket-material-master">
    <header className="hero-copy compact pocket-heading">
      <div><div className="eyebrow">MASTER DATA · KAIN &amp; BENCHMARK</div><h1>Master kain kantong</h1>
        <p>Kelola nama bahan dan pabrik asal yang dipakai di penerimaan kain kantong.</p></div>
      <div className="pocket-heading-actions"><a className="soft-btn" href="/master/kain-benchmark/"><ArrowLeft size={16} aria-hidden="true"/>Kain &amp; Benchmark</a>
        <a className="soft-btn" href={receiptPath}>Ke penerimaan <ArrowRight size={16} aria-hidden="true"/></a></div>
    </header>
    <section className="panel pocket-master-list" aria-labelledby="pocket-master-list-title">
      <header><div><h2 id="pocket-master-list-title">Daftar bahan</h2><p>{visible.length} dari {materials.length} bahan</p></div>
        <button type="button" className="primary-btn" onClick={()=>edit({id:'',name:'',factory:'',supplier:''})}><Plus size={16} aria-hidden="true"/>Tambah bahan</button></header>
      <label className="wh-search"><Search size={16} aria-hidden="true"/><input type="search" aria-label="Cari bahan kain kantong" placeholder="Cari nama bahan, pabrik, atau supplier…" value={query} onChange={e=>setQuery(e.target.value)}/></label>
      {notice && <p className="wh-feedback" role="status">{notice}</p>}
      <div className="pocket-master-cards">{visible.map(item=><article key={item.id}>
        <header><i><Layers3 size={18} aria-hidden="true"/></i><div><h3>{item.name}</h3><p><Factory size={15} aria-hidden="true"/>{item.factory || 'Pabrik belum tercatat'}</p></div></header>
        <p>Supplier utama <strong>{item.supplier || 'Belum diisi'}</strong></p>
        <footer><button type="button" className="soft-btn" onClick={()=>edit(item)}><Pencil size={15} aria-hidden="true"/>Edit bahan</button>
          <a className="soft-btn" href={receiptPath+'&bahan='+encodeURIComponent(item.id)}>Pakai di penerimaan <ArrowRight size={15} aria-hidden="true"/></a></footer>
      </article>)}</div>
      {!visible.length && <p className="pocket-empty">Bahan tidak ditemukan.</p>}
    </section>
    {editing && <ReasonDialog title={editing.id ? 'Edit bahan kain kantong' : 'Tambah bahan kain kantong'} closeLabel="Kembali" onClose={()=>setEditing(null)}>
      <form onSubmit={event=>{
        event.preventDefault()
        try {
          const item = savePocketMaterial(editing.id || null,editing)
          setMaterials(readPocketMaterials())
          setEditing(null)
          setQuery('')
          setNotice(`${item.name} · ${item.factory} disimpan.`)
        } catch (error) { setError((error as Error).message) }
      }}>
        <label>Nama bahan<input required value={editing.name} maxLength={100} onChange={e=>setEditing({...editing,name:e.target.value})}/></label>
        <label>Pabrik asal<input required value={editing.factory} maxLength={100} onChange={e=>setEditing({...editing,factory:e.target.value})}/></label>
        <label>Supplier utama (opsional)<input value={editing.supplier} maxLength={100} onChange={e=>setEditing({...editing,supplier:e.target.value})}/></label>
        {error && <p role="alert">{error}</p>}
        <button type="submit" className="primary-btn">Simpan bahan</button>
      </form>
    </ReasonDialog>}
  </div>
}

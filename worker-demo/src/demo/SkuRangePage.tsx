import {useState} from 'react'
import {articles,rangeChange,stockAt} from './planner/inventory'
import {patternFor,patterns,products,rangeLabel,recipePattern,type StockChange} from './planner/model'
import {changeSession,usePlannerSession} from './planner/session'
import './planner/planner.css'

export function SkuRangePage({mode}:{mode:'master'|'adjust'|'convert'}) {
  const session=usePlannerSession()
  const [key,setKey]=useState(articles[0].key)
  const article=articles.find(a=>a.key===key)!
  const target=articles.find(a=>a.key===article.pair)
  const order=products.find(p=>p.brand===article.brand&&p.sku===article.sku)
  const defaultRef=order?recipePattern(order,session):session.patternRefs?.[key]??null
  const [values,setValues]=useState<Record<string,string>>({})
  const [reason,setReason]=useState('')
  const [note,setNote]=useState('')
  const [preview,setPreview]=useState<{id:string;expected:Record<string,number>;changes:StockChange[]}|null>(null)
  const [message,setMessage]=useState('')
  const [pendingRef,setPendingRef]=useState<string|undefined>()
  function select(next:string){setKey(next);setValues({});setReason('');setNote('');setPreview(null);setMessage('');setPendingRef(undefined)}
  const resetPreview=()=>{setPreview(null);setMessage('')}
  const title=mode==='master'?'Identitas SKU':mode==='adjust'?'Stock Adjustment · Barang jadi':'Ganti Merek'
  return <section className="panel gar-panel sku-range" aria-label={title}>
    <div className="gar-panel-head"><h2>{title}</h2>{mode!=='master'&&<a href="/master/produk-sku/">Lihat Master SKU</a>}</div>
    <div className="sku-range-fields"><label>{mode==='convert'?'SKU asal':'Pilih SKU'}<select aria-label="Pilih SKU" value={key} onChange={e=>select(e.target.value)}>{articles.filter(a=>mode!=='convert'||a.pair).map(a=><option key={a.key}>{a.key}</option>)}</select></label>
      <div><small>Warna</small><strong>{article.colour}</strong></div><div><small>{article.sizes.length===1?'Ukuran khusus':'Rentang master'}</small><strong>{rangeLabel(article.sizes)}</strong></div>
      {mode==='convert'&&target&&<div><small>SKU padanan · tujuan</small><strong>{target.key}</strong><small>{target.colour} · {rangeLabel(target.sizes)}</small></div>}
    </div>
    {mode==='master'?<><label className="sku-range-field">Pola rencana · opsional<select aria-label="Pola rencana SKU" value={pendingRef??defaultRef??''} onChange={e=>{setPendingRef(e.target.value);setMessage('')}}><option value="">Belum ditentukan</option>{patterns.map(p=><option key={p.id} value={p.code}>{p.name} · {p.revision}</option>)}</select></label>
      <p>Anggota ukuran · {article.sizes.join(', ')}. Warna dan ukuran ikut saat SKU dipilih.</p>
      <div className="gar-actions"><button type="button" className="gar-button primary" disabled={pendingRef===undefined} onClick={()=>{changeSession(s=>({...s,patternRefs:{...s.patternRefs,[key]:pendingRef||null}}));setPendingRef(undefined);setMessage('Pola rencana tersimpan. Planner sudah membaca pilihan ini.')}}>Simpan pola rencana</button><a href="/analisis/planner/">Lihat Planner</a></div></>:
    <><p>{mode==='adjust'?'Isi hasil hitung fisik. Slot kosong dilewati. Angka 0 berarti sudah dihitung dan tidak ada barang.':'Isi jumlah yang diganti merek per ukuran. Slot kosong dilewati.'}</p>
    <div className="sku-size-slots">{article.sizes.map(size=><label key={size}>Ukuran {size}<small>Stok asal {stockAt(article,size,session)} pcs{mode==='convert'&&target?' · tujuan '+stockAt(target,size,session)+' pcs':''}</small>
      <input aria-label={'Jumlah ukuran '+size} inputMode="numeric" placeholder="—" value={values[size]??''} onChange={e=>{setValues({...values,[size]:e.target.value});resetPreview()}}/></label>)}</div>
    <div className="sku-range-fields"><label>Alasan · wajib<input aria-label="Alasan transaksi" value={reason} onChange={e=>{setReason(e.target.value);resetPreview()}}/></label><label>Catatan · opsional<input aria-label="Catatan transaksi" value={note} onChange={e=>{setNote(e.target.value);resetPreview()}}/></label></div>
    <button type="button" className="gar-button" onClick={()=>{try{const id=crypto.randomUUID(),expected=Object.fromEntries(article.sizes.map(s=>[s,stockAt(article,s,session)]));const proposed=rangeChange(session,mode,article,values,reason,id,expected);setPreview({id,expected,changes:proposed.stockEvents!.slice(-1)[0].changes});setMessage('')}catch(e){setPreview(null);setMessage((e as Error).message)}}}>Periksa jumlah</button>
    {preview&&<div className="gar-box"><strong>Perubahan stok latihan</strong>{preview.changes.map(c=><p key={c.key+c.size}>{c.key} · ukuran {c.size} · {c.delta>0?'+':''}{c.delta} pcs</p>)}<button type="button" className="gar-button primary" onClick={()=>{try{changeSession(s=>rangeChange(s,mode,article,values,reason,preview.id,preview.expected,note));setValues({});setPreview(null);setMessage('Tersimpan. Saldo setiap ukuran dan Planner sudah diperbarui.')}catch(e){setMessage((e as Error).message);setPreview(null)}}}>Simpan transaksi latihan</button></div>}
    </>}
    {message&&<p role="status">{message}</p>}{mode==='master'&&defaultRef&&<small>Pola tersimpan · {patternFor(defaultRef)?.name}</small>}
  </section>
}

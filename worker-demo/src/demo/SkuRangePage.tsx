import {fgQuantity} from '../fgQuantity'
import RecordTable from '../RecordTable'
import {ReasonDialog} from './planner/ReasonDialog'
import {useState} from 'react'
import {articles,rangeChange,reverseRange,stockAt} from './planner/inventory'
import {patternFor,patterns,products,rangeLabel,recipePattern,type StockChange} from './planner/model'
import {changeSession,usePlannerSession} from './planner/session'
import {allSkus,skuByKey} from './skuCatalog'
import BrandConversionForm,{SkuPairField} from './BrandConversionForm'
import './planner/planner.css'

export function SkuRangePage({mode,historyOnly=false}:{mode:'master'|'adjust'|'convert';historyOnly?:boolean}) {
  if(historyOnly&&mode!=='master')return <RangeHistory mode={mode}/>
  return mode==='convert'?<BrandConversionForm/>:<RangeEditor mode={mode}/>
}

function RangeHistory({mode}:{mode:'convert'|'adjust'}){
  const session=usePlannerSession()
  const [message,setMessage]=useState('')
  const [undo,setUndo]=useState<{doc:string;id:string}|null>(null),[undoReason,setUndoReason]=useState(''),[undoError,setUndoError]=useState('')
  const events=(session.stockEvents??[]).filter(e=>e.action===mode)

  return <>{events.length>0&&<section className="document-history"><h3>Riwayat {mode==='adjust'?'Stock Adjustment':'Ganti Merek'}</h3><RecordTable><thead><tr><th>Tanggal fisik</th><th>SKU dan ukuran</th><th>Alasan</th><th>Status</th><th>Tindakan</th></tr></thead><tbody>{[...events].reverse().map(e=>{const reversed=events.some(r=>r.reverses===e.id);return <tr key={e.id}><td>{e.date??'2026-11-24'}</td><td>{[...new Set(e.changes.map(c=>c.key))].map(key=><div key={key}>{key} · {rangeLabel(skuByKey(key)?.sizes??[])}</div>)}<details><summary>Detail ukuran</summary>{e.changes.map(c=><div key={c.key+c.size}>{c.key} · {c.size} · {c.delta>0?'+':''}{fgQuantity(c.delta)}</div>)}</details></td><td>{e.reason}</td><td>{e.reverses?'Pembalikan':reversed?'Sudah dibalik':'Posted'}</td><td>{!e.reverses&&!reversed&&<button type="button" onClick={()=>{setUndo({doc:e.id,id:crypto.randomUUID()});setUndoReason('');setUndoError('')}}>Balikkan transaksi</button>}</td></tr>})}</tbody></RecordTable></section>}    {undo&&<ReasonDialog title="Balikkan transaksi stok" closeLabel="Kembali" onClose={()=>setUndo(null)}><p>Semua slot ukuran pada transaksi ini akan dikembalikan bersama.</p><label>Alasan pembalikan · wajib<input required value={undoReason} onChange={e=>setUndoReason(e.target.value)}/></label><button type="button" disabled={!undoReason.trim()} onClick={()=>{try{changeSession(s=>reverseRange(s,undo.doc,undo.id,undoReason));setUndo(null);setMessage('Pembalikan tercatat. Saldo stok dan Planner sudah diperbarui.')}catch(e){setUndoError((e as Error).message)}}}>Simpan pembalikan</button>{undoError&&<p role="alert">{undoError}</p>}</ReasonDialog>}
{message&&<p role="status">{message}</p>}</>
}

function RangeEditor({mode}:{mode:'master'|'adjust'}){
  const session=usePlannerSession()
  const draftStorage='erp.owner.range-draft.'+mode
  const [hasDraft,setHasDraft]=useState(()=>!!sessionStorage.getItem(draftStorage)),[discard,setDiscard]=useState(false)
  const options=mode==='master'?allSkus(session,true):articles
  const [selectedKey,setKey]=useState(()=>options.find(a=>a.key===new URLSearchParams(location.search).get('sku'))?.key??options[0].key)
  const article=options.find(a=>a.key===selectedKey)??options[0]
  const key=article.key
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
  const title=mode==='master'?'Identitas SKU':'Stock Adjustment · Barang jadi'
  return <section className={mode==='master'?'panel gar-panel sku-range':'sku-range ic-series-workspace'} aria-label={title}>
    <div className="gar-panel-head"><h2>{title}</h2>{mode!=='master'&&<a href="/master/produk-sku/">Lihat Master SKU</a>}</div>
    <div className="sku-range-fields"><label>Pilih SKU<select aria-label="Pilih SKU" value={key} onChange={e=>select(e.target.value)}>{options.map(a=><option key={a.key}>{a.key}</option>)}</select></label>
      <div><small>Warna</small><strong>{article.colour}</strong></div><div><small>{article.sizes.length===1?'Ukuran khusus':'Rentang master'}</small><strong>{rangeLabel(article.sizes)}</strong></div>
    </div>
    {mode==='master'?<><div id="padanan"><SkuPairField key={key} sku={key}/></div><label className="sku-range-field">Pola rencana · opsional<select aria-label="Pola rencana SKU" value={pendingRef??defaultRef??''} onChange={e=>{setPendingRef(e.target.value);setMessage('')}}><option value="">Belum ditentukan</option>{patterns.map(p=><option key={p.id} value={p.code}>{p.name} · {p.revision}</option>)}</select></label>
      <p>Anggota ukuran · {article.sizes.join(', ')}. Warna dan ukuran ikut saat SKU dipilih.</p>
      <div className="gar-actions"><button type="button" className="gar-button primary" disabled={pendingRef===undefined} onClick={()=>{changeSession(s=>({...s,patternRefs:{...s.patternRefs,[key]:pendingRef||null}}));setPendingRef(undefined);setMessage('Pola rencana tersimpan. Planner sudah membaca pilihan ini.')}}>Simpan pola rencana</button><a href="/analisis/planner/">Lihat Planner</a></div></>:
    <><div className="document-actions"><button type="button" onClick={()=>{sessionStorage.setItem(draftStorage,JSON.stringify({key,values,reason,note}));setHasDraft(true);setMessage('Draft form tersimpan di tab ini.')}}>Simpan draft form</button>
    {hasDraft&&<><button type="button" onClick={()=>{try{const d=JSON.parse(sessionStorage.getItem(draftStorage)??'null');if(!d||!articles.some(a=>a.key===d.key)||!d.values)throw Error();select(d.key);setValues(d.values);setReason(d.reason??'');setNote(d.note??'');setMessage('Draft dibuka untuk diedit.')}catch{setMessage('Draft tidak bisa dibuka.')}}}>Edit draft tersimpan</button><button type="button" onClick={()=>setDiscard(true)}>Hapus draft</button></>}</div>
    {discard&&<ReasonDialog title="Hapus draft form?" closeLabel="Kembali" onClose={()=>setDiscard(false)}><p>Draft ini belum mengubah saldo stok.</p><button type="button" onClick={()=>{sessionStorage.removeItem(draftStorage);setHasDraft(false);setDiscard(false);select(key);setMessage('Draft dihapus.')}}>Ya, hapus draft ini</button></ReasonDialog>}
    <div className="ic-series-balance"><span>Stok asal <strong>{fgQuantity(article.sizes.reduce((n,s)=>n+stockAt(article,s,session),0))}</strong></span></div>
    <details className="ic-size-detail" key={key}><summary>Detail ukuran · {rangeLabel(article.sizes)}</summary>
    <p>Isi hasil hitung fisik. Slot kosong dilewati. Angka 0 berarti sudah dihitung dan tidak ada barang.</p>
    <div className="sku-size-slots">{article.sizes.map(size=><label key={size}>Ukuran {size}<small>Stok asal {fgQuantity(stockAt(article,size,session))}</small>
      <input aria-label={'Jumlah ukuran '+size} inputMode="numeric" placeholder="—" value={values[size]??''} onChange={e=>{setValues({...values,[size]:e.target.value});resetPreview()}}/></label>)}</div></details>
    <div className="sku-range-fields"><label>Alasan · wajib<input required aria-label="Alasan transaksi" value={reason} onChange={e=>{setReason(e.target.value);resetPreview()}}/></label><label>Catatan · opsional<input aria-label="Catatan transaksi" value={note} onChange={e=>{setNote(e.target.value);resetPreview()}}/></label></div>
    <button type="button" className="gar-button" onClick={()=>{try{const id=crypto.randomUUID(),expected=Object.fromEntries(article.sizes.map(s=>[s,stockAt(article,s,session)]));const proposed=rangeChange(session,mode,article,values,reason,id,expected);setPreview({id,expected,changes:proposed.stockEvents!.slice(-1)[0].changes});setMessage('')}catch(e){setPreview(null);setMessage((e as Error).message)}}}>Periksa jumlah</button>
    {preview&&<div className="gar-box"><strong>Perubahan stok latihan</strong>{preview.changes.map(c=><p key={c.key+c.size}>{c.key} · ukuran {c.size} · {c.delta>0?'+':''}{fgQuantity(c.delta)}</p>)}<button type="button" className="gar-button primary" onClick={()=>{try{changeSession(s=>rangeChange(s,mode,article,values,reason,preview.id,preview.expected,note));sessionStorage.removeItem(draftStorage);setHasDraft(false);setValues({});setPreview(null);setMessage('Tersimpan. Saldo setiap ukuran dan Planner sudah diperbarui.')}catch(e){setMessage((e as Error).message);setPreview(null)}}}>Simpan transaksi latihan</button></div>}
    </>}
    {message&&<p role="status">{message}</p>}{mode==='master'&&defaultRef&&<small>Pola tersimpan · {patternFor(defaultRef)?.name}</small>}
  </section>
}

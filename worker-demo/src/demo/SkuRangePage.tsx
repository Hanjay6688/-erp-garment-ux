import { ClipboardCheck, ListChecks, Rows3, Shirt } from 'lucide-react'
import {fgQuantity} from '../fgQuantity'
import RecordTable from '../RecordTable'
import {ReasonDialog} from './planner/ReasonDialog'
import {StockSourceReversal} from './StockSourceReversal'
import {useState} from 'react'
import {rangeChange,rangeReversalBlockers,reverseRange,stockAt} from './planner/inventory'
import {type Article,type Session,rangeLabel,type StockChange} from './planner/model'
import {changeSession,usePlannerSession} from './planner/session'
import {allSkus,skuByKey} from './skuCatalog'
import BrandConversionForm from './BrandConversionForm'
import './planner/planner.css'

export function SkuRangePage({mode,historyOnly=false}:{mode:'adjust'|'convert';historyOnly?:boolean}) {
  if(historyOnly)return <RangeHistory mode={mode}/>
  return mode==='convert'?<BrandConversionForm/>:<RangeEditor/>
}

function RangeHistory({mode}:{mode:'convert'|'adjust'}){
  const session=usePlannerSession()
  const [message,setMessage]=useState('')
  const linked=new URLSearchParams(location.search).get('mutasi')
  const events=(session.stockEvents??[]).filter(e=>e.action===mode)
  const shown=linked&&events.some(row=>row.id===linked)?events.filter(row=>row.id===linked||row.reverses===linked):events
  return <>{events.length>0&&<section className="document-history" id="riwayat-konversi">
    <h3>Riwayat {mode==='adjust'?'Stock Adjustment':'Ganti Merek'}</h3>
    {linked&&<a className="soft-btn" href={location.pathname+'#riwayat-konversi'}>Lihat seluruh riwayat</a>}
    <RecordTable><thead><tr><th>Tanggal fisik</th><th>SKU dan ukuran</th><th>Alasan</th><th>Status</th><th>Tindakan</th></tr></thead>
      <tbody>{[...shown].reverse().map(event=>{
        const reversed=events.some(row=>row.reverses===event.id)
        return <tr key={event.id} data-source-selected={event.id===linked||undefined}>
          <td>{event.date??'Tanggal fisik belum tercatat'}{event.date&&event.physicalTime&&' · '+event.physicalTime+' WIB'}</td>
          <td>{[...new Set(event.changes.map(c=>c.key))].map(key=><div key={key}>{key} · {rangeLabel(skuByKey(key)?.sizes??[])}</div>)}
            <details><summary>Detail ukuran</summary>{event.changes.map(c=><div key={c.key+c.size}>{c.key} · {c.size} · {c.delta>0?'+':''}{fgQuantity(c.delta)}</div>)}</details></td>
          <td>{event.reason}</td><td>{event.reverses?'Pembalikan':reversed?'Sudah dibalik':'Posted'}</td>
          <td>{!event.reverses&&!reversed&&<StockSourceReversal label="Balikkan transaksi" title="Balikkan transaksi stok" document={event.id}
            blockers={rangeReversalBlockers(session,event.id)} onReverse={reason=>{
              changeSession(current=>reverseRange(current,event.id,crypto.randomUUID(),reason));setMessage('Pembalikan tercatat. Saldo stok dan Planner sudah diperbarui.')
            }}/>}</td>
        </tr>
      })}</tbody>
    </RecordTable>
  </section>}{message&&<p role="status">{message}</p>}</>
}

function RangeEditor(){
  const session=usePlannerSession()
  const options=allSkus(session,true)
  if(!options.length)return <section className="panel sku-range-page">Belum ada SKU aktif.</section>
  return <RangeForm session={session} options={options}/>
}

function RangeForm({session,options}:{session:Session;options:Article[]}){
  const draftStorage='erp.owner.range-draft.adjust'
  const [hasDraft,setHasDraft]=useState(()=>!!sessionStorage.getItem(draftStorage)),[discard,setDiscard]=useState(false)
  const [selectedKey,setKey]=useState(()=>options.find(a=>a.key===new URLSearchParams(location.search).get('sku'))?.key??options[0].key)
  const article=options.find(a=>a.key===selectedKey)??options[0]
  const key=article.key
  const [values,setValues]=useState<Record<string,string>>({})
  const [reason,setReason]=useState('')
  const [note,setNote]=useState(''),[physicalDay,setPhysicalDay]=useState('2026-11-24'),[physicalTime,setPhysicalTime]=useState('')
  const [preview,setPreview]=useState<{id:string;expected:Record<string,number>;changes:StockChange[]}|null>(null)
  const [message,setMessage]=useState('')
  function select(next:string){setKey(next);setValues({});setReason('');setNote('');setPreview(null);setMessage('')}
  const resetPreview=()=>{setPreview(null);setMessage('')}
  const title='Stock Adjustment · Barang jadi'
  return <section className="sku-range ic-series-workspace" aria-label={title}>
    <div className="gar-panel-head stock-form-heading"><i><Shirt aria-hidden="true"/></i><h2>{title}</h2><a className="soft-btn" href="/master/produk-sku/">Lihat Master SKU</a></div>
    <div className="sku-range-fields"><label>Pilih SKU<select aria-label="Pilih SKU" value={key} onChange={e=>select(e.target.value)}>{options.map(a=><option key={a.key}>{a.key}</option>)}</select></label>
      <div><small>Warna</small><strong>{article.colour}</strong></div><div><small>{article.sizes.length===1?'Ukuran khusus':'Rentang master'}</small><strong>{rangeLabel(article.sizes)}</strong></div>
    </div>
    <div className="document-actions"><button type="button" onClick={()=>{sessionStorage.setItem(draftStorage,JSON.stringify({key,values,reason,note,physicalDay,physicalTime}));setHasDraft(true);setMessage('Draft form tersimpan di tab ini.')}}>Simpan draft form</button>
    {hasDraft&&<><button type="button" onClick={()=>{try{const d=JSON.parse(sessionStorage.getItem(draftStorage)??'null');if(!d||!options.some(a=>a.key===d.key)||!d.values)throw Error();select(d.key);setValues(d.values);setReason(d.reason??'');setNote(d.note??'');setPhysicalDay(d.physicalDay??'2026-11-24');setPhysicalTime(d.physicalTime??'');setMessage('Draft dibuka untuk diedit.')}catch{setMessage('Draft tidak bisa dibuka.')}}}>Edit draft tersimpan</button><button type="button" onClick={()=>setDiscard(true)}>Hapus draft</button></>}</div>
    {discard&&<ReasonDialog title="Hapus draft form?" closeLabel="Kembali" onClose={()=>setDiscard(false)}><p>Draft ini belum mengubah saldo stok.</p><button type="button" onClick={()=>{sessionStorage.removeItem(draftStorage);setHasDraft(false);setDiscard(false);select(key);setMessage('Draft dihapus.')}}>Ya, hapus draft ini</button></ReasonDialog>}
    <div className="ic-series-balance"><Rows3 aria-hidden="true"/><span>Stok asal <strong>{fgQuantity(article.sizes.reduce((n,s)=>n+stockAt(article,s,session),0))}</strong></span></div>
    <details className="ic-size-detail" key={key}><summary>Detail ukuran · {rangeLabel(article.sizes)}</summary>
    <p>Isi hasil hitung fisik. Slot kosong dilewati. Angka 0 berarti sudah dihitung dan tidak ada barang.</p>
    <div className="sku-size-slots">{article.sizes.map(size=><label key={size}>Ukuran {size}<small>Stok asal {fgQuantity(stockAt(article,size,session))}</small>
      <input aria-label={'Jumlah ukuran '+size} inputMode="numeric" placeholder="—" value={values[size]??''} onChange={e=>{setValues({...values,[size]:e.target.value});resetPreview()}}/></label>)}</div></details>
    <div className="sku-range-fields"><label>Alasan · wajib<input required aria-label="Alasan transaksi" value={reason} onChange={e=>{setReason(e.target.value);resetPreview()}}/></label><label>Tanggal fisik<input type="date" value={physicalDay} onChange={e=>{setPhysicalDay(e.target.value);resetPreview()}}/></label><label>Jam fisik (WIB, opsional)<input type="time" value={physicalTime} onChange={e=>{setPhysicalTime(e.target.value);resetPreview()}}/></label><label>Catatan · opsional<input aria-label="Catatan transaksi" value={note} onChange={e=>{setNote(e.target.value);resetPreview()}}/></label></div>
    <button type="button" className="gar-button" onClick={()=>{try{const id=crypto.randomUUID(),expected=Object.fromEntries(article.sizes.map(s=>[s,stockAt(article,s,session)]));const proposed=rangeChange(session,'adjust',article,values,reason,id,expected,note,physicalDay,physicalTime);setPreview({id,expected,changes:proposed.stockEvents!.slice(-1)[0].changes});setMessage('')}catch(e){setPreview(null);setMessage((e as Error).message)}}}>Periksa jumlah</button>
    {preview&&<section className="stock-preview" aria-label="Review penyesuaian per ukuran">
      <header><ListChecks aria-hidden="true"/><div><h3>Review per ukuran</h3><p>{article.key} · {preview.changes.length} ukuran berubah</p></div></header>
      {preview.changes.map(change=><article key={change.size}>
        <strong>Ukuran {change.size}</strong><small>Hasil hitung {Number(values[change.size]).toLocaleString('id-ID')} pcs</small>
        <dl className="stock-balance">
          <div><dt>Saldo sekarang</dt><dd>{preview.expected[change.size].toLocaleString('id-ID')} pcs</dd></div>
          <div data-delta={change.delta<0?'negative':'positive'}><dt>Selisih stok</dt><dd>{change.delta>0?'+':''}{change.delta.toLocaleString('id-ID')} pcs</dd></div>
          <div><dt>Setelah posting</dt><dd>{(preview.expected[change.size]+change.delta).toLocaleString('id-ID')} pcs</dd></div>
        </dl>
      </article>)}
      <button type="button" className="gar-button primary" onClick={()=>{try{changeSession(s=>rangeChange(s,'adjust',article,values,reason,preview.id,preview.expected,note,physicalDay,physicalTime));sessionStorage.removeItem(draftStorage);setHasDraft(false);setValues({});setPreview(null);setMessage('Tersimpan. Saldo setiap ukuran dan Planner sudah diperbarui.')}catch(e){setMessage((e as Error).message);setPreview(null)}}}><ClipboardCheck aria-hidden="true"/> Simpan transaksi latihan</button>
    </section>}
    {message&&<p role="status">{message}</p>}
  </section>
}

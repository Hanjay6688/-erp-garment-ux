import { ArrowRight, CalendarDays, Check, ClipboardCheck, FolderOpen, ListChecks, Save, Shirt, Trash2 } from 'lucide-react'
import { CountAmount, CountDifference, CountHeading, countNumber } from '../components/PhysicalCountFields'
import { dayOk, lastWarehouseDay } from './warehouseDay'
import { fgActivity } from './fgTimeline'
import { sizeBalanceAt } from './planner/conversion'
import {fgQuantity} from '../fgQuantity'
import RecordTable from '../RecordTable'
import {ReasonDialog} from './planner/ReasonDialog'
import {StockSourceReversal} from './StockSourceReversal'
import {useEffect, useRef, useState} from 'react'
import {rangeChange,rangeReversalBlockers,reverseRange,stockAt} from './planner/inventory'
import {type Article,type Session,rangeLabel,type StockChange} from './planner/model'
import {changeSession,usePlannerSession} from './planner/session'
import {allSkus,nativePosition,skuByKey} from './skuCatalog'
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
  const draftStorage = 'erp.owner.range-draft.adjust'
  const [hasDraft, setHasDraft] = useState(() => !!sessionStorage.getItem(draftStorage))
  const [discard, setDiscard] = useState(false)
  const [selectedKey, setKey] = useState(() => options.find(a => a.key === new URLSearchParams(location.search).get('sku'))?.key ?? options[0].key)
  const article = options.find(a => a.key === selectedKey) ?? options[0]
  const key = article.key
  const [values, setValues] = useState<Record<string,string>>({})
  const [reason, setReason] = useState('')
  const [note, setNote] = useState('')
  const [physicalDay, setPhysicalDay] = useState(lastWarehouseDay)
  const [physicalTime, setPhysicalTime] = useState('')
  const [preview, setPreview] = useState<{id:string;expected:Record<string,number>;changes:StockChange[]}|null>(null)
  const [message, setMessage] = useState('')
  const [failed, setFailed] = useState(false)
  const reviewRef = useRef<HTMLElement>(null)
  useEffect(() => { if (preview) reviewRef.current?.focus() }, [preview])

  const position = nativePosition(article)
  const activity = fgActivity(article, session, position.location, position.grade)
  const validDay = dayOk(physicalDay)
  const balances = article.sizes.map((size, index) => sizeBalanceAt(stockAt(article, size, session), index, activity, physicalDay, physicalTime))
  const filled = article.sizes.filter(size => /^\d+$/.test(values[size]?.trim() ?? '') && Number.isSafeInteger(Number(values[size]))).length

  function resetPreview() { setPreview(null); setMessage(''); setFailed(false) }
  function select(next: string) { setKey(next); setValues({}); setReason(''); setNote(''); resetPreview() }
  function showError(error: unknown) { setPreview(null); setFailed(true); setMessage((error as Error).message) }
  function saveDraft() {
    sessionStorage.setItem(draftStorage, JSON.stringify({key, values, reason, note, physicalDay, physicalTime}))
    setHasDraft(true); setFailed(false); setMessage('Draf tersimpan di tab ini.')
  }
  function loadDraft() {
    try {
      const draft = JSON.parse(sessionStorage.getItem(draftStorage) ?? 'null')
      if (!draft || !options.some(a => a.key === draft.key) || !draft.values) throw Error('Draf tidak bisa dibuka.')
      select(draft.key); setValues(draft.values); setReason(draft.reason ?? ''); setNote(draft.note ?? '')
      setPhysicalDay(draft.physicalDay ?? '2026-11-24'); setPhysicalTime(draft.physicalTime ?? ''); setMessage('Draf dibuka untuk diedit.')
    } catch (error) { showError(error) }
  }
  function review() {
    try {
      const id = crypto.randomUUID()
      const expected = Object.fromEntries(article.sizes.map(size => [size, stockAt(article, size, session)]))
      const proposed = rangeChange(session, 'adjust', article, values, reason, id, expected, note, physicalDay, physicalTime)
      setPreview({id, expected, changes:proposed.stockEvents!.at(-1)!.changes}); setMessage(''); setFailed(false)
    } catch (error) { showError(error) }
  }
  function post() {
    if (!preview) return
    try {
      changeSession(s => rangeChange(s, 'adjust', article, values, reason, preview.id, preview.expected, note, physicalDay, physicalTime))
      sessionStorage.removeItem(draftStorage); setHasDraft(false); setValues({}); setPreview(null); setFailed(false)
      setMessage('Tersimpan. Saldo setiap ukuran dan Planner sudah diperbarui.')
    } catch (error) { showError(error) }
  }
  return <div className="count-workbook">
    <section className="count-panel count-entry" aria-label="Hitung barang jadi">
      <CountHeading icon={Shirt} title="Barang jadi"><a href="/master/produk-sku/" className="count-heading-link">Master SKU <ArrowRight/></a></CountHeading>
      <div className="count-panel-body">
        <label className="count-field">Pilih SKU<select aria-label="Pilih SKU" value={key} onChange={e => select(e.target.value)}>
          {options.map(a => <option key={a.key} value={a.key}>{a.key}</option>)}</select></label>
        <p className="count-item-meta">{article.model} · {article.colour} · {position.location}</p>
        <div className="count-sheet-title"><h3>Hitung per ukuran</h3><span>{filled}/{article.sizes.length} diisi</span></div>
        <div className="count-sheet" data-keyboard-grid="cek-fisik-ukuran">
          <div className="count-sheet-labels" aria-hidden="true"><span>Ukuran</span><span>Saldo saat cek</span><span>Hasil fisik</span></div>
          {article.sizes.map((size, index) => {
            const raw = values[size] ?? ''
            const invalid = !!raw.trim() && (!/^\d+$/.test(raw.trim()) || !Number.isSafeInteger(Number(raw)))
            return <div className="count-size-row" key={size}>
              <strong className="count-size-tag">{size}</strong>
              <span className="count-book-qty">{validDay ? countNumber(balances[index]) : '—'} <small>pcs</small></span>
              <div className="count-size-entry"><CountAmount label={'Jumlah ukuran '+size} unit="pcs" value={raw} invalid={invalid} row={index}
                onChange={value => { setValues({...values,[size]:value}); resetPreview() }}/>
                {raw.trim() && (invalid ? <small className="count-input-error">Isi pcs bulat, minimal 0.</small> :
                  validDay && <CountDifference value={Number(raw)-balances[index]} unit="pcs"/>)}</div>
            </div>
          })}
        </div>
        <p className="count-hint">Kosongkan ukuran yang dilewati. Isi <strong>0</strong> kalau fisiknya habis.</p>
      </div>
    </section>
    <section className="count-panel count-document" aria-label="Dokumen cek fisik">
      <CountHeading icon={CalendarDays} title="Dokumen cek fisik"/>
      <div className="count-panel-body count-fields">
        <div className="count-field-pair">
          <label className="count-field">Tanggal cek fisik<input aria-label="Tanggal cek fisik" type="date" required max={lastWarehouseDay()} value={physicalDay} onChange={e=>{setPhysicalDay(e.target.value);resetPreview()}}/></label>
          <label className="count-field"><span>Jam WIB <small>opsional</small></span><input aria-label="Jam fisik WIB" type="time" value={physicalTime} onChange={e=>{setPhysicalTime(e.target.value);resetPreview()}}/></label>
        </div>
        <label className="count-field">Alasan penyesuaian<input required aria-label="Alasan transaksi" placeholder="Mis. selisih setelah hitung ulang" value={reason} onChange={e=>{setReason(e.target.value);resetPreview()}}/></label>
        <label className="count-field"><span>Catatan <small>opsional</small></span><textarea aria-label="Catatan transaksi" rows={2} value={note} onChange={e=>{setNote(e.target.value);resetPreview()}}/></label>
      </div>
      <footer className="count-action-bar">
        <button type="button" className="primary-btn count-primary" onClick={review}><ListChecks/>Periksa jumlah</button>
        <button type="button" className="count-secondary" onClick={saveDraft}><Save/>Simpan draf</button>
        {hasDraft && <div className="count-saved"><button type="button" onClick={loadDraft}><FolderOpen/>Buka draf</button><button type="button" onClick={()=>setDiscard(true)}><Trash2/>Hapus draf</button></div>}
      </footer>
      {message && <p className="count-feedback" role={failed?'alert':'status'} data-error={failed || undefined}>{!failed && <Check/>}{message}</p>}
    </section>
    {preview && <section ref={reviewRef} tabIndex={-1} className="count-panel count-review" aria-label="Review penyesuaian per ukuran">
      <CountHeading icon={ListChecks} title="Review per ukuran"><span className="count-review-id">{article.key}</span></CountHeading>
      <div className="count-panel-body">{preview.changes.map(change => <article key={change.size} className="count-preview-row">
        <h3>Ukuran {change.size}</h3><small>Hasil hitung {countNumber(Number(values[change.size]))} pcs</small>
        <dl className="stock-balance">
          <div><dt>Saldo sekarang</dt><dd>{countNumber(preview.expected[change.size])} pcs</dd></div>
          <div data-delta={change.delta<0?'negative':'positive'}><dt>Selisih stok</dt><dd>{change.delta>0?'+':''}{countNumber(change.delta)} pcs</dd></div>
          <div><dt>Setelah posting</dt><dd>{countNumber(preview.expected[change.size]+change.delta)} pcs</dd></div>
        </dl></article>)}
        <button type="button" className="primary-btn count-primary" onClick={post}><ClipboardCheck/>Simpan transaksi latihan</button>
      </div>
    </section>}
    {discard && <ReasonDialog title="Hapus draf cek fisik?" closeLabel="Kembali" onClose={()=>setDiscard(false)}>
      <p>Draf ini belum mengubah saldo stok.</p><button type="button" onClick={()=>{sessionStorage.removeItem(draftStorage);setHasDraft(false);setDiscard(false);select(key);setMessage('Draf dihapus.')}}>Ya, hapus draf ini</button>
    </ReasonDialog>}
  </div>
}

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { accessoryUuid, displayDecimal, displayMoney, micro, parseAccessoryWorkspace, previewAccessoryLine,
  type AccessoryDocument, type AccessoryLine, type AccessoryWorkspace } from './accessoryIssue'
import type { Json } from './types/database.preconnect'
import './initial-import.css'

type Form = { id: string | null; version: string | null; number: string; contractor: string; location: string; po: string;
  at: string; notes: string; lines: AccessoryLine[] }
const emptyForm = (at = ''): Form => ({ id:null,version:null,number:'',contractor:'',location:'',po:'',at,notes:'',lines:[] })
const contextKey = (contractor: string | null, location: string | null, at: string) => JSON.stringify([contractor || null,location || null,at])
const fromDocument = (d: AccessoryDocument): Form => ({ id:d.id,version:d.row_version,number:d.number,contractor:d.contractor_id,
  location:d.location_id,po:d.po_id ?? '',at:d.physical_local,notes:d.notes,lines:d.items.map(i => ({ material_id:i.material_id,
    qty:displayDecimal(i.qty),mode:i.manual_price === null ? 'MASTER' : 'MANUAL',manual_price:i.manual_price ?? '' })) })

export default function ConnectedAccessoryIssuePage() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') return <section className="panel"><h1>Nota Ambil Aksesori</h1><p>Masuk ke ERP yang tersambung untuk mencatat pengambilan aksesori.</p></section>
  if (!identity.permissions.includes('finance.contractor_accessory.view')) return <section className="panel" role="alert"><h1>Nota Ambil Aksesori</h1><p>Hak melihat nota aksesori diperlukan.</p></section>
  return <AccessoryWorkspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`}/>
}

function AccessoryWorkspace() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('ERP belum tersambung.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const mutation = useProductionMutation('ACCESSORY_ISSUE')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = mutation
  const [data, setData] = useState<AccessoryWorkspace | null>(null), [error, setError] = useState(''), [loading, setLoading] = useState(false)
  const [form, setForm] = useState<Form>(() => emptyForm()), formRef = useRef(form)
  const selected = useRef<string | null>(null), opening = useRef(true), sequence = useRef(0)
  const [query, setQuery] = useState(''), [materialQuery, setMaterialQuery] = useState(''), filters = useRef({ query:'',material_query:'' })
  const [reason, setReason] = useState('Pengambilan aksesori'), [reverseReason, setReverseReason] = useState('')
  const [review, setReview] = useState<'POST' | 'DELETE' | 'REVERSE' | null>(null)
  const setEditor = useCallback((next: Form) => { formRef.current=next; setForm(next); setReview(null) }, [])
  const change = (patch: Partial<Form>) => setEditor({ ...formRef.current,...patch })
  const load = useCallback(async () => {
    const number = ++sequence.current, ticket = beginRead(), replace = opening.current, id = selected.current, editor = formRef.current
    const request: Record<string, Json> = { ...filters.current, id }
    if (!replace) Object.assign(request,{ contractor_id:editor.contractor || null,location_id:editor.location || null,
      ...(editor.at ? { physical_at:editor.at + '+07:00' } : {}),material_ids:editor.lines.map(i => i.material_id) })
    setLoading(true); setError(''); setReview(null)
    try {
      const result = await client.rpc('erp_get_accessory_issue_workspace_v1',{ p_filters:request })
      if (!isReadCurrent(ticket) || number !== sequence.current || (!replace && editor !== formRef.current)) return false
      if (result.error) throw result.error
      const value = parseAccessoryWorkspace(result.data)
      if (JSON.stringify(value.filters) !== JSON.stringify(request) && JSON.stringify(Object.entries(value.filters as object).sort()) !== JSON.stringify(Object.entries(request).sort())) throw new Error('Hasil pembacaan nota tidak cocok.')
      if ((id !== null && value.document?.id !== id) || (id === null && value.document !== null)) throw new Error('Identitas nota tidak cocok.')
      if (!replace && contextKey(value.contractor_id,value.location_id,value.physical_local) !== contextKey(editor.contractor,editor.location,editor.at || value.physical_local)) throw new Error('Harga dan stok memakai konteks berbeda.')
      setData(value)
      if (replace) { setEditor(value.document ? fromDocument(value.document) : emptyForm(value.physical_local)); opening.current=false; setReverseReason('') }
      return finishRead(ticket)
    } catch (failure) { if (isReadCurrent(ticket) && number === sequence.current) setError(failure instanceof Error ? failure.message : normalizeClientError(failure).message); return false }
    finally { if (number === sequence.current) setLoading(false) }
  },[client,beginRead,finishRead,isReadCurrent,setEditor])
  useEffect(() => { void load() },[load])
  const handlers: ProductionMutationHandlers = {
    send: envelope => client.rpc('erp_save_accessory_issue_action_v1',{ p_action:envelope.action,p_payload: envelope.payload,p_client_request_id: envelope.id }),
    validate: (value, envelope) => {
      const r=value as Record<string,unknown> | null, p=envelope.payload as Record<string,Json>
      const status=({ SAVE_DRAFT:'DRAFT',POST:'POSTED',DELETE:'DELETED',REVERSE:'REVERSED' } as Record<string,string>)[envelope.action]
      if (!r || r.action !== envelope.action || r.request_id !== envelope.id || !accessoryUuid(r.id) || r.status !== status
        || (p.id && r.id !== p.id) || (status === 'DELETED' ? r.row_version !== null : typeof r.row_version !== 'string' || !/^[1-9]\d{0,18}$/.test(r.row_version))) throw new Error('Respons nota tidak cocok; pulihkan transaksi yang sama.')
    },
    retire: (value, envelope) => { const r=value as { id:string }; selected.current=envelope.action==='DELETE' ? null : r.id; opening.current=true; setEditor(emptyForm()); setData(null) },
    reload:load,
  }
  const canCreate=identity.permissions.includes('finance.contractor_accessory.create')
  const canPost=canCreate && identity.permissions.includes('finance.contractor_accessory.post')
  const canReverse=['OWNER','ADMIN'].includes(identity.profile.role) && identity.permissions.includes('finance.contractor_accessory.reverse')
  const document=data?.document?.id === form.id ? data.document : null
  const isDraft=!document || document.status === 'DRAFT', locked=mutation.writerLocked || loading
  const editable=isDraft && canCreate && !locked
  const quotesCurrent=Boolean(data && contextKey(data.contractor_id,data.location_id,data.physical_local) === contextKey(form.contractor,form.location,form.at))
  const materials=new Map(data?.materials.map(m => [m.id,m]))
  const previews=form.lines.map(line => previewAccessoryLine(line,materials.get(line.material_id)))
  const valid=Boolean(quotesCurrent && form.number.trim() && form.contractor && form.location && form.at && reason.trim()
    && form.lines.length && previews.every(p => p.payload) && (!form.po || data?.orders.some(p => p.id === form.po)))
  const enoughStock=form.lines.every(line => /^[1-9]\d{0,11}$/.test(line.qty) && materials.has(line.material_id) && BigInt(line.qty)*1000000n <= micro(materials.get(line.material_id)!.stock))
  const total=previews.reduce((sum,p) => sum + (p.amount ?? 0n),0n)
  const submit = (action: 'SAVE_DRAFT' | 'POST' | 'DELETE' | 'REVERSE') => {
    const payload: Record<string,Json> = { id:form.id,expected_version:form.version,reason:action==='REVERSE' ? reverseReason.trim() : reason.trim() }
    if (action==='SAVE_DRAFT' || action==='POST') {
      if (!valid) return
      Object.assign(payload,{ number:form.number.trim(),contractor_id:form.contractor,location_id:form.location,po_id:form.po || null,
        physical_at:form.at + '+07:00',notes:form.notes,items:previews.map(p => p.payload!) })
    }
    void run(action,payload,null,handlers)
  }
  const open = (id: string | null) => { selected.current=id; opening.current=true; filters.current.material_query=''; setMaterialQuery(''); setReview(null); void load() }
  const updateLine = (id: string, patch: Partial<AccessoryLine>) => change({ lines:form.lines.map(line => line.material_id===id ? { ...line,...patch } : line) })
  return <section className="initial-import">
    <header className="panel initial-import-heading"><div><div className="eyebrow">KEUANGAN · MANDOR</div><h1>Nota Ambil Aksesori</h1><p>Isi jumlah fisik dalam PCS. Harga eceran per buah dapat berbeda dari harga master lusin atau gross.</p></div>
      <button type="button" disabled={locked || !canCreate} onClick={() => open(null)}>Nota baru</button><button type="button" disabled={mutation.busy || loading} onClick={() => void load()}>Muat ulang</button></header>
    <ProductionRecoveryNotice recovery={mutation} onReconcile={() => reconcile(handlers)} className="initial-import-message"/>
    {error && <p role="alert" className="initial-import-message">{error}</p>}
    <form className="panel initial-import-toolbar" onSubmit={e => { e.preventDefault(); filters.current.query=query.trim(); void load() }}>
      <label>Cari nota atau mandor<input aria-label="Cari nota aksesori" maxLength={120} value={query} onChange={e => setQuery(e.target.value)}/></label><button disabled={locked}>Cari nota</button>
      {data && <span>{data.history.length} dari {data.history_count} nota. Persempit pencarian untuk nota lama.</span>}
    </form>
    <section className="panel initial-import-table"><table><thead><tr><th>Nota</th><th>Mandor</th><th>Tanggal</th><th>Status</th><th>Tagihan</th><th/></tr></thead><tbody>{data?.history.map(h => <tr key={h.id}>
      <td>{h.number}</td><td>{h.contractor}</td><td>{h.date}</td><td>{h.status}</td><td>{displayMoney(micro(h.total))}</td><td><button disabled={locked} onClick={() => open(h.id)}>Buka {h.number}</button></td>
    </tr>)}</tbody></table>{data?.history.length===0 && <p>Belum ada nota aksesori hitung yang cocok.</p>}</section>
    <section className="panel initial-import-advances" aria-label="Form nota aksesori"><h2>{form.id ? form.number : 'Nota baru'} · {document?.status ?? 'Draft'}</h2>
      <p>{isDraft ? 'Draft belum mengurangi stok atau membentuk kasbon. Pengesahan memakai isi formulir terakhir.' : 'Nota disahkan tersimpan sebagai sumber. Koreksi dilakukan melalui pembatalan tertaut.'}</p>
      <div className="initial-import-toolbar">
        <label>Nomor nota<input aria-label="Nomor nota aksesori" maxLength={60} disabled={!editable} value={form.number} onChange={e => change({ number:e.target.value })}/></label>
        <label>Mandor<select aria-label="Mandor aksesori" disabled={!editable} value={form.contractor} onChange={e => change({ contractor:e.target.value,po:'' })}><option value="">Pilih mandor</option>{data?.contractors.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
        <label>Gudang sumber<select aria-label="Gudang aksesori" disabled={!editable} value={form.location} onChange={e => change({ location:e.target.value })}><option value="">Pilih gudang</option>{data?.locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}</select></label>
        <label>Waktu pengambilan (WIB)<input aria-label="Waktu ambil aksesori" type="datetime-local" step="1" disabled={!editable} value={form.at} onChange={e => change({ at:e.target.value.length===16 ? e.target.value+':00' : e.target.value })}/></label>
        <label>PO terkait (opsional)<select aria-label="PO aksesori" disabled={!editable || !quotesCurrent} value={form.po} onChange={e => change({ po:e.target.value })}><option value="">Tanpa PO</option>{data?.orders.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
      </div>
      {isDraft && <>
        <div className="initial-import-toolbar"><label>Cari barang<input aria-label="Cari barang aksesori" maxLength={120} disabled={!editable} value={materialQuery} onChange={e => setMaterialQuery(e.target.value)}/></label>
          <button type="button" disabled={!editable || !form.contractor || !form.location || !form.at} onClick={() => { filters.current.material_query=materialQuery.trim(); void load() }}>Perbarui harga dan stok</button></div>
        {!quotesCurrent && <p role="status">Pilih mandor, gudang, dan waktu pengambilan, lalu perbarui harga dan stok.</p>}
        <label>Tambah aksesori<select aria-label="Tambah aksesori" disabled={!editable || !quotesCurrent || form.lines.length>=100} value="" onChange={e => { if (e.target.value && !form.lines.some(i => i.material_id===e.target.value)) change({ lines:[...form.lines,{material_id:e.target.value,qty:'',mode:'MANUAL',manual_price:''}] }) }}>
          <option value="">Pilih barang detail</option>{data?.materials.filter(m => !form.lines.some(i => i.material_id===m.id)).map(m => <option key={m.id} value={m.id}>{m.sku} · {m.name} · {displayDecimal(m.stock)} PCS</option>)}</select></label>
        {data && <p>{data.materials.length} dari {data.material_count} aksesori. Gunakan pencarian untuk barang lainnya.</p>}
        <div className="initial-import-table"><table><thead><tr><th>Aksesori / stok gudang</th><th>Jumlah fisik</th><th>Dasar harga</th><th>Harga eceran / pcs</th><th>Tagihan</th><th/></tr></thead><tbody>{form.lines.map((line,index) => {
          const m=materials.get(line.material_id), p=previews[index]
          return <tr key={line.material_id}><td>{m?.name ?? document?.items.find(i => i.material_id===line.material_id)?.name ?? 'Aksesori belum dimuat'}<br/>{m && <small>Stok: {displayDecimal(m.stock)} PCS · {m.master_price === null ? 'Harga master belum tersedia' : `${displayMoney(micro(m.master_price))} / ${m.price_unit}`}</small>}</td>
            <td><input aria-label={`Jumlah PCS ${index+1}`} inputMode="numeric" disabled={!editable} value={line.qty} onChange={e => updateLine(line.material_id,{qty:e.target.value})}/><button type="button" disabled={!editable || !quotesCurrent || !m || micro(m.stock)<=0n || micro(m.stock)%1000000n!==0n} onClick={() => { if(m) updateLine(line.material_id,{qty:(micro(m.stock)/1000000n).toString()}) }}>Ambil sisa</button></td>
            <td><select aria-label={`Dasar harga ${index+1}`} disabled={!editable} value={line.mode} onChange={e => updateLine(line.material_id,{mode:e.target.value as 'MASTER' | 'MANUAL'})}><option value="MANUAL">Eceran per pcs</option><option value="MASTER">Harga master</option></select></td>
            <td>{line.mode==='MANUAL' ? <input aria-label={`Harga per PCS ${index+1}`} inputMode="decimal" disabled={!editable} value={line.manual_price} onChange={e => updateLine(line.material_id,{manual_price:e.target.value})}/> : 'Mengikuti master pada waktu ambil'}</td>
            <td>{p.amount===null ? <span role="status">{p.error}</span> : displayMoney(p.amount)}</td><td><button type="button" disabled={!editable} aria-label={`Hapus aksesori ${index+1}`} onClick={() => change({lines:form.lines.filter(i => i.material_id!==line.material_id)})}>Hapus</button></td></tr>
        })}</tbody></table></div>
        {!enoughStock && form.lines.length>0 && <p role="status">Jumlah melebihi stok atau belum lengkap. Draft boleh disimpan; pengesahan memeriksa stok kembali.</p>}
      </>}
      {!isDraft && document && <div className="initial-import-table"><table><thead><tr><th>Barang</th><th>Jumlah</th><th>Harga tersimpan</th><th>Tagihan</th><th>Payroll</th></tr></thead><tbody>{document.items.map(i => <tr key={i.id}><td>{i.name}</td><td>{displayDecimal(i.qty)} {i.unit}</td><td>{displayMoney(micro(i.price))} / {i.price_unit}{i.manual_price!==null ? ' · Eceran' : ' · Master'}</td><td>{displayMoney(micro(i.amount))}</td><td>{i.payroll_status}</td></tr>)}</tbody></table></div>}
      <label>Catatan<input aria-label="Catatan nota aksesori" maxLength={1000} disabled={!editable} value={form.notes} onChange={e => change({notes:e.target.value})}/></label>
      <p><strong>Total tagihan: {isDraft ? previews.every(p => p.amount!==null) ? displayMoney(total) : 'Lengkapi rincian' : displayMoney(micro(document!.total))}</strong></p>
      <p>Harga jual mandor terpisah dari biaya persediaan. Harga master dan kebijakan penggantian biaya produksi tetap mengikuti sumber masing-masing.</p>
      {isDraft && canCreate && <><label>Alasan perubahan<input aria-label="Alasan nota aksesori" maxLength={1000} disabled={locked} value={reason} onChange={e => { setReason(e.target.value); setReview(null) }}/></label>
        <div className="initial-import-toolbar"><button type="button" disabled={locked || !valid} onClick={() => submit('SAVE_DRAFT')}>Simpan draft</button>
          <button type="button" disabled={locked || !canPost || !valid || !enoughStock} onClick={() => setReview('POST')}>Periksa pengesahan</button>
          {form.id && <button type="button" disabled={locked || !reason.trim()} onClick={() => setReview('DELETE')}>Hapus draft</button>}</div></>}
      {document?.status==='POSTED' && canReverse && <><p>{document.payroll_locked ? 'Nota sudah terkait payroll aktif. Selesaikan pembatalan payroll terkait terlebih dahulu.' : 'Pembatalan memulihkan stok dan membalik tagihan terkait.'}</p>
        <label>Alasan pembatalan<input aria-label="Alasan pembatalan nota" maxLength={1000} disabled={locked || document.payroll_locked} value={reverseReason} onChange={e => {setReverseReason(e.target.value);setReview(null)}}/></label>
        <button type="button" disabled={locked || document.payroll_locked || !reverseReason.trim()} onClick={() => setReview('REVERSE')}>Periksa pembatalan</button></>}
      {review && <section className="initial-import-message" aria-label="Konfirmasi nota"><p>{review==='POST' ? `Sahkan pengeluaran ${form.lines.reduce((sum,l)=>sum+BigInt(l.qty),0n)} PCS dan tagihan ${displayMoney(total)}?` : review==='DELETE' ? 'Hapus draft yang belum disahkan ini?' : 'Batalkan nota ini dengan transaksi kebalikan tertaut?'}</p>
        <button type="button" disabled={locked} onClick={() => submit(review)}>{review==='POST' ? 'Sahkan nota' : review==='DELETE' ? 'Ya, hapus draft' : 'Sahkan pembatalan nota'}</button><button type="button" disabled={mutation.busy} onClick={() => setReview(null)}>Kembali</button></section>}
    </section>
  </section>
}

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { parseRateWorkspace, rupiah, validateRateOutcome, wibDay, type RateAction, type RateComponent, type RateWorkspace } from './masterContract'
import type { Json } from './types/database.preconnect'
import type { ProductionEnvelope } from './productionRecovery'

// Owner D15-3: Mandor work rates per model x work component, from a date. The wage of "Catat selesai jahit" uses the
// rate valid at the sewing date (the Native snapshot); a rate changed later never alters a wage already recorded.
type BomRow = { componentId: string; sequenceNo: string; defaultRate: string }
const money = /^[0-9]{1,12}(\.[0-9]{1,2})?$/

export default function WorkRatePanel({ contractorId }: { contractorId: string | null }) {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') throw new Error('Sesi tarif upah belum siap.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const recovery = useProductionMutation('WORK_RATE')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = recovery
  const serial = useRef(0)
  const [query, setQuery] = useState(''), [offset, setOffset] = useState(0), [modelId, setModelId] = useState<string | null>(null)
  const [data, setData] = useState<RateWorkspace | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState(''), [done, setDone] = useState('')
  const [bomOpen, setBomOpen] = useState(false), [bomRows, setBomRows] = useState<BomRow[]>([]), [bomDate, setBomDate] = useState('')
  const [bomReason, setBomReason] = useState(''), [bomChecked, setBomChecked] = useState(false)
  const [comp, setComp] = useState({ code: '', name: '', category: 'LABOR', reason: '' })

  const load = useCallback(async (q: { query: string; offset: number; model: string | null }) => {
    const ticket = beginRead(), n = ++serial.current
    setBusy(true); setError('')
    try {
      const reply = await client.rpc('erp_cp7_get_work_rates_v1', { p_query: { contractor_id: contractorId, model_id: q.model, q: q.query.trim(), offset: q.offset } })
      if (n !== serial.current || !isReadCurrent(ticket)) return false
      if (reply.error) throw reply.error
      setData(parseRateWorkspace(reply.data)); finishRead(ticket); return true
    } catch (e) {
      if (n === serial.current && isReadCurrent(ticket)) { setData(null); setError(normalizeClientError(e).message) }
      return false
    } finally { if (n === serial.current) setBusy(false) }
  }, [beginRead, client, contractorId, finishRead, isReadCurrent])
  useEffect(() => { void load({ query, offset, model: modelId }) }, [load, recovery.scope]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => { ++serial.current }, [])

  const handlers: ProductionMutationHandlers = {
    send: (e: ProductionEnvelope) => client.rpc('erp_cp7_save_work_rate_v1', { p_action: e.action, p_payload: e.payload, p_request: e.id }),
    validate: (value: unknown, e: ProductionEnvelope) => { validateRateOutcome(value, e.action as RateAction, e.id) },
    retire: (value: unknown, e: ProductionEnvelope) => {
      validateRateOutcome(value, e.action as RateAction, e.id)
      const p = e.payload as Record<string, unknown>
      setDone(e.action === 'SET_RATE' ? `Tersimpan: tarif ${rupiah(String(p.rate))}/pcs berlaku mulai ${String(p.effective_date)}.`
        : e.action === 'STOP_RATE' ? `Tersimpan: tarif berhenti mulai ${String(p.effective_date)}.`
        : e.action === 'SAVE_BOM' ? 'Tersimpan: komponen kerja model diperbarui.' : `Tersimpan: komponen kerja ${String(p.code).toUpperCase()} dibuat.`)
      setBomOpen(false); setBomReason(''); setBomChecked(false); setComp({ code: '', name: '', category: 'LABOR', reason: '' })
    },
    reload: () => load({ query, offset, model: modelId }),
  }
  const fresh = data !== null && !recovery.workspaceStale
  const writable = fresh && data.canWrite && !recovery.writerLocked && !busy
  const priceable = writable && data.canPrice
  const pick = (id: string) => { setModelId(id); setDone(''); setBomOpen(false); void load({ query, offset, model: id }) }
  const model = data?.model ?? null
  const currentBom = model?.bom.find(v => v.id === model.currentBomId) ?? null
  const openBom = () => {
    if (!data) return
    const latest = model?.bom.filter(v => v.isActive).at(-1) ?? null
    setBomRows((latest?.items ?? []).map(i => ({ componentId: i.componentId, sequenceNo: String(i.sequenceNo), defaultRate: i.defaultRate })))
    setBomDate(data.today); setBomReason(''); setBomChecked(false); setBomOpen(true)
  }
  const bomProblem = bomRows.length === 0 ? 'Isi paling sedikit satu komponen kerja.'
    : new Set(bomRows.map(r => r.componentId)).size !== bomRows.length || bomRows.some(r => !r.componentId) ? 'Setiap komponen dipilih sekali.'
    : bomRows.some(r => !/^\d{1,3}$/.test(r.sequenceNo) || !money.test(r.defaultRate.trim())) ? 'Urutan harus angka dan tarif bawaan harus angka rupiah.'
    : !/^\d{4}-\d{2}-\d{2}$/.test(bomDate) ? 'Tanggal mulai berlaku wajib diisi.' : ''

  return <section className="panel cmd-panel cmd-rates" aria-label="Tarif upah mandor">
    <h2>Tarif upah mandor</h2>
    <p className="cmd-note">Tarif per model dan komponen kerja, berlaku mulai tanggal yang diisi. "Catat selesai jahit" memakai tarif yang berlaku pada tanggal jahit;
      mengubah tarif sesudahnya tidak mengubah upah yang sudah tercatat. Bila mandor belum punya tarif, upah memakai tarif bawaan model.</p>
    {recovery.pending || recovery.error ? <ProductionRecoveryNotice recovery={recovery} onReconcile={() => reconcile(handlers)} className="" reconcileLabel="Periksa hasil simpan tarif"/> : null}
    {data?.contractor ? <p><strong>Mandor: {data.contractor.code} · {data.contractor.name}</strong>{data.contractor.isSpecial ? ' · Special' : ''}{data.contractor.active ? '' : ' · NONAKTIF'}</p>
      : <p className="cmd-note">Pilih mandor di daftar di atas untuk melihat dan mengisi tarifnya. Komponen kerja model bisa diatur tanpa memilih mandor.</p>}
    {done ? <p role="status" className="cmd-done">{done}</p> : null}
    {error ? <p role="alert">{error}</p> : null}
    {data && !data.canPrice ? <p className="cmd-note">Mengubah tarif dan komponen kerja perlu hak ubah harga (master.price.edit_draft).</p> : null}
    <form className="cmd-search" onSubmit={e => { e.preventDefault(); setOffset(0); void load({ query, offset: 0, model: modelId }) }}>
      <label>Cari model<input aria-label="Cari model" value={query} maxLength={80} onChange={e => setQuery(e.target.value)} placeholder="Kode atau nama model"/></label>
      <button type="submit" disabled={busy}>Cari model</button>
    </form>
    <div className="cmd-layout">
      <div className="cmd-list" aria-label="Daftar model">
        {data?.models.rows.map(m => <button type="button" key={m.id} aria-label={`Pilih model ${m.code}`} aria-pressed={modelId === m.id} disabled={busy} onClick={() => pick(m.id)}>
          <strong>{m.code} · {m.name}</strong><span>{m.components ? `${m.components} komponen kerja` : 'Belum ada komponen kerja'}{m.active ? '' : ' · nonaktif'}</span>
        </button>)}
        {data ? <div className="cmd-pages">
          <button type="button" disabled={busy || data.models.offset === 0} onClick={() => { const o = Math.max(0, offset - 20); setOffset(o); void load({ query, offset: o, model: modelId }) }}>Sebelumnya</button>
          <span>{data.models.total} model</span>
          <button type="button" disabled={busy || data.models.offset + data.models.rows.length >= data.models.total} onClick={() => { const o = offset + 20; setOffset(o); void load({ query, offset: o, model: modelId }) }}>Berikutnya</button>
        </div> : null}
      </div>
      <div className="cmd-detail">
        {model && data ? <section className="cmd-view" aria-label={`Model ${model.code}`}>
          <h3>{model.code} · {model.name}</h3>
          <div className="cmd-usage"><strong>Komponen kerja model{currentBom ? ` (versi ${currentBom.versionNo}, mulai ${wibDay(currentBom.effectiveFrom)})` : ''}</strong>
            {currentBom ? currentBom.items.map(i => <span key={i.componentId}>{i.sequenceNo}. {i.name} · tarif bawaan {rupiah(i.defaultRate)}/pcs</span>)
              : <span>Belum ada komponen kerja yang berlaku. Isi dulu supaya upah jahit bisa dihitung.</span>}</div>
          {data.canPrice && !bomOpen ? <button type="button" disabled={!priceable} onClick={openBom}>Ubah komponen kerja model</button> : null}
          {bomOpen ? <section className="cmd-form" aria-label="Komponen kerja model">
            {bomRows.map((r, i) => <div className="cmd-bom-row" key={i}>
              <label>Komponen<select aria-label={`Komponen ${i + 1}`} value={r.componentId} disabled={!priceable}
                onChange={e => { const v = e.target.value; setBomRows(rows => rows.map((x, j) => j === i ? { ...x, componentId: v } : x)); setBomChecked(false) }}>
                <option value="">—</option>{data.catalog.map(k => <option key={k.id} value={k.id}>{k.code} · {k.name}</option>)}</select></label>
              <label>Urutan<input aria-label={`Urutan ${i + 1}`} inputMode="numeric" value={r.sequenceNo} disabled={!priceable}
                onChange={e => { const v = e.target.value; setBomRows(rows => rows.map((x, j) => j === i ? { ...x, sequenceNo: v } : x)); setBomChecked(false) }}/></label>
              <label>Tarif bawaan / pcs<input aria-label={`Tarif bawaan ${i + 1}`} inputMode="decimal" value={r.defaultRate} disabled={!priceable}
                onChange={e => { const v = e.target.value; setBomRows(rows => rows.map((x, j) => j === i ? { ...x, defaultRate: v } : x)); setBomChecked(false) }}/></label>
              <button type="button" aria-label={`Hapus komponen ${i + 1}`} disabled={!priceable} onClick={() => { setBomRows(rows => rows.filter((_, j) => j !== i)); setBomChecked(false) }}>Hapus</button>
            </div>)}
            <button type="button" disabled={!priceable} onClick={() => { setBomRows(rows => [...rows, { componentId: '', sequenceNo: String((rows.length + 1)), defaultRate: '0' }]); setBomChecked(false) }}>Tambah baris komponen</button>
            <label>Berlaku mulai (WIB)<input aria-label="Komponen kerja berlaku mulai" type="date" value={bomDate} disabled={!priceable} onChange={e => { setBomDate(e.target.value); setBomChecked(false) }}/>
              <small>Bila versi sekarang belum pernah dipakai upah, perubahan langsung mengganti isinya; bila sudah dipakai, versi baru dibuat mulai tanggal ini.</small></label>
            {bomProblem ? <p className="cmd-problems">{bomProblem}</p> : null}
            <label>Alasan<input aria-label="Alasan komponen kerja" value={bomReason} maxLength={1000} disabled={!priceable} onChange={e => { setBomReason(e.target.value); setBomChecked(false) }}/></label>
            <label className="cmd-check"><input type="checkbox" aria-label="Komponen kerja sudah diperiksa" checked={bomChecked} disabled={!priceable || bomReason.trim().length < 5}
              onChange={e => setBomChecked(e.target.checked)}/>Komponen, urutan dan tarif bawaan sudah saya periksa.</label>
            <div className="cmd-actions">
              <button type="button" className="primary-btn" disabled={!priceable || !bomChecked || bomProblem !== '' || bomReason.trim().length < 5}
                onClick={() => void run('SAVE_BOM', { model_id: model.id, items: bomRows.map(r => ({ work_component_id: r.componentId, sequence_no: Number(r.sequenceNo), default_rate: r.defaultRate.trim() })),
                  effective_date: bomDate, review_token: model.bomReviewToken, reason: bomReason.trim() } as Json, null, handlers)}>Simpan komponen kerja model</button>
              <button type="button" onClick={() => setBomOpen(false)}>Batal</button>
            </div>
          </section> : null}
          {data.contractor ? <div className="cmd-rate-list">{model.components.length === 0 ? <p>Model ini belum punya komponen kerja.</p>
            : model.components.map(c => <RateRow key={c.componentId} component={c} today={data.today} writable={priceable && data.contractor!.active}
              onSave={(action, payload) => void run(action, { contractor_id: data.contractor!.id, model_id: model.id, work_component_id: c.componentId, review_token: c.reviewToken, ...payload } as Json, null, handlers)}/>)}</div> : null}
        </section> : <p className="cmd-note">Pilih model untuk melihat komponen kerja dan tarifnya.</p>}
        {data?.canWrite ? <section className="cmd-form" aria-label="Komponen kerja baru">
          <h3>Komponen kerja baru</h3>
          <label>Kode<input aria-label="Kode komponen kerja" value={comp.code} maxLength={40} disabled={!writable} onChange={e => setComp(x => ({ ...x, code: e.target.value }))}/></label>
          <label>Nama<input aria-label="Nama komponen kerja" value={comp.name} maxLength={120} disabled={!writable} onChange={e => setComp(x => ({ ...x, name: e.target.value }))}/></label>
          <label>Jenis<select aria-label="Jenis komponen kerja" value={comp.category} disabled={!writable} onChange={e => setComp(x => ({ ...x, category: e.target.value }))}>
            <option value="LABOR">Upah kerja</option><option value="COMMISSION">Komisi</option><option value="FINISHING">Finishing</option><option value="OTHER">Lainnya</option></select></label>
          <label>Alasan<input aria-label="Alasan komponen kerja baru" value={comp.reason} maxLength={1000} disabled={!writable} onChange={e => setComp(x => ({ ...x, reason: e.target.value }))}/></label>
          <button type="button" disabled={!writable || !/^[A-Za-z0-9][A-Za-z0-9._/-]{0,39}$/.test(comp.code.trim()) || !comp.name.trim() || comp.reason.trim().length < 5}
            onClick={() => void run('CREATE_COMPONENT', { code: comp.code.trim(), name: comp.name.trim(), category: comp.category, reason: comp.reason.trim() }, null, handlers)}>Tambah komponen kerja</button>
        </section> : null}
      </div>
    </div>
  </section>
}

function RateRow({ component: c, today, writable, onSave }: { component: RateComponent; today: string; writable: boolean;
  onSave: (action: 'SET_RATE' | 'STOP_RATE', payload: Record<string, string>) => void }) {
  const [rate, setRate] = useState(''), [date, setDate] = useState(today), [reason, setReason] = useState(''), [checked, setChecked] = useState(false)
  const lastUse = c.versions.map(v => v.lastUse).filter((x): x is string => x !== null).sort().at(-1) ?? null
  const ok = writable && checked && reason.trim().length >= 5 && /^\d{4}-\d{2}-\d{2}$/.test(date)
  return <section className="cmd-rate" aria-label={`Tarif upah ${c.code}`}>
    <strong>{c.name}</strong>
    <span>{c.current ? `Berlaku sekarang: ${rupiah(c.current.rate)}/pcs sejak ${wibDay(c.current.effectiveFrom)}`
      : `Belum ada tarif mandor ini${c.defaultRate !== null ? `; upah memakai tarif bawaan model ${rupiah(c.defaultRate)}/pcs` : ''}.`}{c.inCurrentBom ? '' : ' (komponen ini hanya ada di versi komponen kerja yang akan datang)'}</span>
    {c.versions.length ? <ol>{c.versions.map(v => <li key={v.id}>{rupiah(v.rate)}/pcs mulai {wibDay(v.effectiveFrom)}{v.effectiveTo ? ` s.d. sebelum ${wibDay(v.effectiveTo)}` : ''}
      {v.lastUse ? ` · dipakai upah sampai ${wibDay(v.lastUse)}` : ' · belum dipakai'}</li>)}</ol> : null}
    {lastUse ? <small>Tarif baru atau penghentian harus mulai sesudah {wibDay(lastUse)} (pemakaian terakhir).</small> : null}
    <div className="cmd-rate-form">
      <label>Tarif baru / pcs<input aria-label={`Tarif ${c.code}`} inputMode="decimal" value={rate} disabled={!writable} onChange={e => { setRate(e.target.value); setChecked(false) }}/></label>
      <label>Berlaku mulai (WIB)<input aria-label={`Tarif ${c.code} berlaku mulai`} type="date" value={date} disabled={!writable} onChange={e => { setDate(e.target.value); setChecked(false) }}/></label>
      <label>Alasan<input aria-label={`Alasan tarif ${c.code}`} value={reason} maxLength={1000} disabled={!writable} onChange={e => { setReason(e.target.value); setChecked(false) }}/></label>
      <label className="cmd-check"><input type="checkbox" aria-label={`Tarif ${c.code} sudah diperiksa`} checked={checked} disabled={!writable || reason.trim().length < 5}
        onChange={e => setChecked(e.target.checked)}/>Tarif dan tanggalnya sudah saya periksa.</label>
      <div className="cmd-actions">
        <button type="button" className="primary-btn" disabled={!ok || !money.test(rate.trim())} onClick={() => onSave('SET_RATE', { rate: rate.trim(), effective_date: date, reason: reason.trim() })}>Simpan tarif {c.code}</button>
        {c.versions.some(v => v.effectiveTo === null) ? <button type="button" disabled={!ok} onClick={() => onSave('STOP_RATE', { effective_date: date, reason: reason.trim() })}>Hentikan tarif {c.code} mulai tanggal itu</button> : null}
      </div>
    </div>
  </section>
}

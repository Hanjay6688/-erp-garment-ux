import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { normalizeClientError } from './lib/clientError'
import { formatCp6WibDateTime } from './cp6BusinessTime'
import { hasProductionPending, isDefiniteInitialRejection, observeProductionRecovery,
  productionLockManager, productionLockName, readProductionRecovery } from './productionRecovery'
import { clearGoodDateRequest, goodDateRefusalText, goodPolicyDate, goodPolicyDateRequestKey,
  persistGoodDateRequest, prepareGoodPolicyDate, readGoodDateRequest, readGoodPolicyDates, saveGoodPolicyDate,
  type GoodPolicyDates, type GoodPolicyEvent, type GoodPolicyPage, type PreparedGoodDate } from './nativeGoodPolicyDates'
import './good-policy-dates.css'

type Props = { client: unknown; scope: string; actor: string; canManage: boolean
  onAccessLost: (message: string) => void; onLockChange: (locked: boolean) => void }
const firstPage: GoodPolicyPage = { beforeVersion: null, beforeDate: null }
const dayText = (day: string) => new Intl.DateTimeFormat('id-ID', { dateStyle: 'long', timeZone: 'UTC' }).format(new Date(day + 'T00:00:00Z'))

function SourceDescription({ source }: { source: GoodPolicyEvent }) {
  return <div className="cset-preview">
    <p><strong>Versi kategori {source.version}</strong> · dicatat {formatCp6WibDateTime(source.recorded_at)}</p>
    {source.status === 'PENDING_POLICY_VALUE'
      ? <p>Versi ini masih menunggu isi kategori. Tanggal berlaku tidak menjadikannya gratis; GOOD yang bergantung padanya tetap ditahan.</p>
      : <p>{source.categories.length ? `Kategori bebas remburs: ${source.categories.map(c => c.name).join(', ')}.`
        : 'Daftar kategori gratis kosong: tidak ada kategori yang bebas remburs pada versi ini.'}</p>}
    <p>Alasan versi kategori: {source.reason}</p>
  </div>
}

export default function GoodPolicyDatesPanel({ client, scope, actor, canManage, onAccessLost, onLockChange }: Props) {
  const id = useId(), sequence = useRef(0), active = useRef(false), mounted = useRef(false)
  const [workspace, setWorkspace] = useState<GoodPolicyDates | null>(null), [busy, setBusy] = useState(false)
  const [error, setError] = useState(''), [notice, setNotice] = useState(''), [page, setPage] = useState(firstPage)
  const [held, setHeld] = useState(() => readGoodDateRequest(scope, actor))
  const [sourceId, setSourceId] = useState(''), [day, setDay] = useState(''), [reason, setReason] = useState('')
  const [reviewed, setReviewed] = useState(false)
  const report = useCallback((failure: unknown) => {
    const normalized = normalizeClientError(failure), message = goodDateRefusalText(normalized.message)
    setError(message)
    if (normalized.code === 'FORBIDDEN' || normalized.code === 'AUTH_REQUIRED') {
      setWorkspace(null); onAccessLost(message)
    }
  }, [onAccessLost])
  const load = useCallback(async (cursor: GoodPolicyPage = firstPage) => {
    if (active.current) return
    active.current = true
    const n = ++sequence.current
    setBusy(true); setError(''); setWorkspace(null); setReviewed(false)
    try {
      const next = await readGoodPolicyDates(client, actor, cursor)
      if (!mounted.current || n !== sequence.current) return
      setWorkspace(next); setSourceId(next.current_source.id); setPage(cursor)
    } catch (failure) { if (mounted.current && n === sequence.current) report(failure) }
    finally { active.current = false; if (mounted.current) setBusy(false) }
  }, [client, actor, report])
  useEffect(() => {
    mounted.current = true
    void load()
    // The same in-flight read can serve StrictMode's effect replay. A real
    // unmount still prevents its response from changing this component.
    return () => { mounted.current = false }
  }, [load])
  useEffect(() => {
    const invalidate = () => {
      ++sequence.current; setWorkspace(null); setReviewed(false); setHeld(readGoodDateRequest(scope, actor))
      setError('Catatan atau transaksi berubah di tab lain. Baca ulang dan periksa permintaan tersimpan.')
    }
    const changed = (event: StorageEvent) => {
      if (event.key === null || event.key === goodPolicyDateRequestKey(scope)) invalidate()
    }
    addEventListener('storage', changed)
    const stop = observeProductionRecovery(scope, invalidate)
    return () => { removeEventListener('storage', changed); stop() }
  }, [scope, actor])
  useEffect(() => { onLockChange(busy || Boolean(held.pending || held.error)) }, [busy, held.pending, held.error, onLockChange])
  useEffect(() => () => { onLockChange(false) }, [onLockChange])

  const send = async (mode: 'NEW' | 'RETRY' | 'CANCEL') => {
    if (active.current || busy || !canManage) return
    active.current = true
    const n = ++sequence.current
    setBusy(true); setError(''); setNotice('')
    try {
      const locks = productionLockManager()
      if (!locks) throw Error('Peramban ini belum mendukung penguncian penyimpanan. Gunakan peramban yang mendukung sebelum menyimpan.')
      await locks.request(productionLockName(scope), { mode: 'exclusive', ifAvailable: true }, async lock => {
        if (!lock) throw Error('Ada penyimpanan lain di tab ini atau tab lain. Tunggu selesai lalu periksa kembali.')
        if (!mounted.current || n !== sequence.current) return
        const other = readProductionRecovery(scope)
        if (other.corrupted || hasProductionPending(other)) throw Error('Pastikan hasil transaksi lain terlebih dahulu sebelum mencatat tanggal berlaku.')
        const old = readGoodDateRequest(scope, actor)
        if (old.error) throw Error(old.error)
        let command: PreparedGoodDate
        if (mode === 'NEW') {
          if (old.pending || !workspace) throw Error('Baca versi kategori dan periksa permintaan sebelumnya.')
          command = prepareGoodPolicyDate(workspace, sourceId, day, reason, reviewed, crypto.randomUUID())
          persistGoodDateRequest(scope, command)
        } else {
          if (!old.pending) throw Error('Permintaan tersimpan tidak tersedia.')
          command = old.pending
        }
        setHeld(readGoodDateRequest(scope, actor))
        try {
          const result = await saveGoodPolicyDate(client, command, mode === 'CANCEL')
          if (!mounted.current || n !== sequence.current) return
          clearGoodDateRequest(scope, command); setHeld(readGoodDateRequest(scope, actor))
          setWorkspace(null); setReviewed(false); setDay(''); setReason('')
          setNotice(result.status === 'CANCELLED' ? 'Permintaan dibatalkan. Tidak ada tanggal berlaku baru dari permintaan ini.'
            : `${mode === 'CANCEL' ? 'Permintaan sudah tersimpan sebelum pembatalan. ' : ''}Tanggal berlaku ${dayText(result.effective_from)} untuk versi kategori ${result.source_version} tersimpan. Riwayat lama tetap dipertahankan.`)
        } catch (failure) {
          if (!mounted.current || n !== sequence.current) return
          if (mode === 'NEW' && isDefiniteInitialRejection(failure)) {
            clearGoodDateRequest(scope, command); setHeld(readGoodDateRequest(scope, actor)); setWorkspace(null); setReviewed(false)
          }
          throw failure
        }
        try {
          const next = await readGoodPolicyDates(client, actor)
          if (mounted.current && n === sequence.current) {
            setWorkspace(next); setSourceId(next.current_source.id); setPage(firstPage)
          }
        } catch (failure) { if (mounted.current && n === sequence.current) report(failure) }
      })
    } catch (failure) { if (mounted.current && n === sequence.current) report(failure) }
    finally {
      active.current = false
      if (mounted.current) { setBusy(false); setHeld(readGoodDateRequest(scope, actor)) }
    }
  }
  const sources = workspace ? [...new Map([workspace.current_source, ...workspace.source_events].map(source => [source.id, source])).values()] : []
  const selected = sources.find(source => source.id === sourceId)
  const locked = busy || Boolean(held.pending || held.error) || !canManage || !workspace?.can_write
  let valid = false
  try { goodPolicyDate(day); valid = Boolean(selected && reason.trim() && Array.from(reason.trim()).length <= 1000) } catch { /* Explicit date stays required. */ }
  return <section className="panel good-policy-dates" aria-label="Tanggal berlaku kategori gratis untuk GOOD" aria-busy={busy}>
    <h2>Tanggal berlaku kategori gratis untuk GOOD</h2>
    <p>Hak bebas remburs mandor Special mengikuti tanggal fisik hasil GOOD di WIB. HPP barang tetap dicatat. Pilih versi kategori dan tanggal berlakunya secara eksplisit; nota pengambilan sebelumnya tetap utuh.</p>
    {busy ? <p role="status">Memeriksa tanggal berlaku dan hasil permintaan…</p> : null}
    {error || held.error ? <p className="cset-alert" role="alert">{error || held.error}</p> : null}
    {notice ? <p className="cset-done" role="status">{notice}</p> : null}
    {held.pending ? <div className="cset-alert">
      <p>Hasil permintaan tanggal {dayText(held.pending.payload.effective_from)} untuk versi {held.pending.sourceEvent.version} belum dipastikan. Pertahankan permintaan yang sama.</p>
      <div className="cset-actions">
        <button type="button" disabled={busy || !canManage} onClick={() => void send('RETRY')}>Periksa hasil tanggal yang sama</button>
        <button type="button" disabled={busy || !canManage} onClick={() => void send('CANCEL')}>Batalkan permintaan jika belum tersimpan</button>
      </div>
      <p>Jika sudah tersimpan, hasil simpannya ditampilkan. Pembatalan permintaan tidak menghapus riwayat tanggal berlaku yang sudah tersimpan.</p>
    </div> : null}
    <div className="cset-actions"><button type="button" disabled={busy} onClick={() => void load()}>Baca ulang tanggal berlaku</button></div>
    {workspace ? <>
      {!workspace.current_source_registered ? <p className="cset-problem">Versi kategori terbaru ({workspace.current_source.version}) belum punya tanggal berlaku untuk GOOD. Tetapkan tanggalnya sebelum GOOD mandor Special memakai kebijakan ini.</p> : null}
      {!canManage || !workspace.can_write ? <p>Owner dengan hak mengelola pengaturan dan melihat aksesori diperlukan untuk mencatat tanggal berlaku. Admin dapat membaca riwayat.</p> : null}
      <fieldset className="cset-editor" disabled={locked}>
        <legend>Konfirmasi tanggal berlaku</legend>
        <div className="cset-fields">
          <label htmlFor={id + '-source'}>Versi kategori ERP-DEC02<select id={id + '-source'} value={sourceId}
            onChange={event => { setSourceId(event.target.value); setReviewed(false) }}>
            {sources.map(source => <option key={source.id} value={source.id}>Versi {source.version}{source.status === 'PENDING_POLICY_VALUE' ? ' · menunggu isi kategori' : ''}</option>)}
          </select></label>
          <label htmlFor={id + '-day'}>Berlaku untuk GOOD mulai tanggal (WIB)<input id={id + '-day'} type="date" value={day}
            onChange={event => { setDay(event.target.value); setReviewed(false) }}/></label>
        </div>
        {selected ? <SourceDescription source={selected}/> : null}
        <label htmlFor={id + '-reason'}>Alasan pencatatan tanggal berlaku<textarea id={id + '-reason'} value={reason}
          onChange={event => { setReason(event.target.value); setReviewed(false) }}/></label>
        <label className="cset-check"><input type="checkbox" checked={reviewed} onChange={event => setReviewed(event.target.checked)}/>
          Saya memastikan versi kategori, tanggal berlaku, dan alasan ini benar. GOOD yang sudah dicatat harus dikoreksi melalui alur yang sah.</label>
        <button type="button" className="primary" disabled={!valid || !reviewed} onClick={() => void send('NEW')}>Simpan tanggal berlaku yang ditinjau</button>
      </fieldset>
      {workspace.source_has_more ? <button type="button" disabled={busy} onClick={() => void load({ ...page, beforeVersion: workspace.next_source_before })}>Lihat versi kategori lebih lama</button> : null}
      <details><summary>Riwayat tanggal berlaku · {workspace.versions.length} pada halaman ini</summary>
        <div className="cset-list">{workspace.versions.map(version => <article className="cset-policy" key={version.id}>
          <h3>GOOD mulai {dayText(version.effective_from)}</h3><SourceDescription source={version.source_event}/>
          <p>Alasan tanggal berlaku: {version.reason}</p><p className="cset-meta">Dicatat {formatCp6WibDateTime(version.recorded_at)}</p>
        </article>)}</div>
        {workspace.versions.length === 0 ? <p>Belum ada tanggal berlaku pada halaman ini.</p> : null}
        {workspace.version_has_more ? <button type="button" disabled={busy} onClick={() => void load({ ...page, beforeDate: workspace.next_version_before })}>Lihat tanggal berlaku lebih lama</button> : null}
      </details>
    </> : null}
  </section>
}

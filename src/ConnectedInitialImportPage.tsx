import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Download, FileUp, RefreshCw } from 'lucide-react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { initialImportCatalog, initialImportTemplate, readInitialImportFile, type InitialImportEntity, type InitialImportRow } from './initialImport'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import type { Json } from './types/database.preconnect'
import './initial-import.css'

type Row = InitialImportRow & { id: string; entity: InitialImportEntity; validation_status: string; errors: string[]; applied: boolean }
type Batch = { id: string; code: string; status: string; cutover_at: string; revision: string; rows: Row[] }
type Workspace = { batch: Batch | null; recent: { id: string; batch_code: string; status: string }[] }
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Respons impor tidak lengkap.')
  return value as Record<string, unknown>
}
export function parseInitialImportWorkspace(value: unknown): Workspace {
  const raw = object(value)
  if (!Array.isArray(raw.recent)) throw new Error('Daftar impor tidak lengkap.')
  const recent = raw.recent.map((entry) => {
    const r = object(entry)
    if (typeof r.id !== 'string' || !uuid.test(r.id) || typeof r.batch_code !== 'string' || typeof r.status !== 'string') throw new Error('Identitas impor tidak valid.')
    return { id: r.id, batch_code: r.batch_code, status: r.status }
  })
  if (raw.batch === null) return { batch: null, recent }
  const b = object(raw.batch)
  if (typeof b.id !== 'string' || !uuid.test(b.id) || typeof b.code !== 'string' || typeof b.status !== 'string'
    || typeof b.cutover_at !== 'string' || !Number.isFinite(Date.parse(b.cutover_at))
    || typeof b.revision !== 'string' || !/^[0-9a-f]{64}$/.test(b.revision) || !Array.isArray(b.rows)) throw new Error('Isi batch impor tidak lengkap.')
  const rows = b.rows.map((entry): Row => {
    const r = object(entry), payload = object(r.payload)
    if (typeof r.id !== 'string' || !uuid.test(r.id) || typeof r.entity !== 'string' || !(r.entity in initialImportCatalog)
      || !Number.isSafeInteger(r.source_row_no) || Number(r.source_row_no) < 1 || typeof r.validation_status !== 'string'
      || !Array.isArray(r.errors) || !r.errors.every((e) => typeof e === 'string') || typeof r.applied !== 'boolean'
      || Object.values(payload).some((v) => v !== null && typeof v !== 'string' && typeof v !== 'boolean' && (typeof v !== 'number' || !Number.isFinite(v)))) throw new Error('Rincian baris impor tidak valid.')
    return { id: r.id, entity: r.entity as InitialImportEntity, source_row_no: Number(r.source_row_no),
      payload: Object.fromEntries(Object.entries(payload).map(([key, v]) => [key, v === null ? '' : String(v)])),
      validation_status: r.validation_status, errors: r.errors as string[], applied: r.applied }
  })
  return { recent, batch: { id:b.id, code:b.code, status:b.status, cutover_at:b.cutover_at, revision:b.revision, rows } }
}

export default function ConnectedInitialImportPage() {
  const { runtime, identity } = useAuth()
  if (!isConnectedRuntime(runtime) || identity.status !== 'AUTHORIZED') return <section className="panel initial-import"><h1>Impor data awal</h1><p>Masuk ke ERP yang tersambung untuk mengunggah dan memeriksa data awal.</p></section>
  if (!['OWNER', 'ADMIN'].includes(identity.profile.role)) return <section className="panel initial-import" role="alert"><h1>Impor data awal</h1><p>Halaman ini tersedia untuk owner dan admin.</p></section>
  return <ImportWorkspace key={`${runtime.projectRef}:${identity.profile.id}`} />
}

function ImportWorkspace() {
  const { runtime } = useAuth()
  if (!isConnectedRuntime(runtime)) throw new Error('ERP belum tersambung.')
  const client = useMemo(() => getUatSupabaseClient(runtime), [runtime])
  const mutation = useProductionMutation('INITIAL_IMPORT')
  const { beginRead, finishRead, isReadCurrent, run, reconcile } = mutation
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [entity, setEntity] = useState<InitialImportEntity>('MATERIAL')
  const [editor, setEditor] = useState<InitialImportRow[] | null>(null)
  const [filename, setFilename] = useState('Perbaikan di aplikasi')
  const [code, setCode] = useState('')
  const [date, setDate] = useState('')
  const [page, setPage] = useState(0)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [reading, setReading] = useState(false)
  const batchId = useRef<string | null>(null)
  const editorRevision = useRef<string | null>(null)
  const readFileSequence = useRef(0)
  const loadSequence = useRef(0)
  const batch = workspace?.batch ?? null
  const spec = initialImportCatalog[entity]
  const fields = Object.entries(spec.fields)
  const storedRows = batch?.rows.filter((row) => row.entity === entity) ?? []
  const shownRows = editor ?? storedRows
  const locked = mutation.writerLocked || loading || reading
  const posted = batch?.status === 'POSTED'

  const load = useCallback(async () => {
    const sequence = ++loadSequence.current
    const ticket = beginRead(), requested = batchId.current
    setLoading(true); setError('')
    try {
      const { data, error: failure } = await client.rpc('erp_get_initial_import_workspace_v1', { p_batch_id: requested })
      if (!isReadCurrent(ticket) || requested !== batchId.current) return false
      if (failure) throw failure
      const parsed = parseInitialImportWorkspace(data)
      if ((parsed.batch?.id ?? null) !== requested) throw new Error('Respons tidak sesuai batch yang dipilih.')
      setWorkspace(parsed)
      return finishRead(ticket)
    } catch (failure) {
      if (isReadCurrent(ticket)) setError(normalizeClientError(failure).message)
      return false
    } finally { if (sequence === loadSequence.current) setLoading(false) }
  }, [client, beginRead, finishRead, isReadCurrent])
  useEffect(() => { void load(); return () => { readFileSequence.current++ } }, [load])

  const handlers: ProductionMutationHandlers = {
    send: (envelope) => client.rpc('erp_save_initial_import_action_v1', { p_action: envelope.action, p_payload: envelope.payload, p_client_request_id: envelope.id }),
    validate: (data, envelope) => {
      const result = object(data), payload = object(envelope.payload)
      if (result.request_id !== envelope.id || result.action !== envelope.action || typeof result.batch_id !== 'string'
        || !uuid.test(result.batch_id) || typeof result.status !== 'string'
        || (envelope.action !== 'CREATE' && result.batch_id !== payload.batch_id)) throw new Error('Respons transaksi tidak cocok.')
    },
    retire: (data) => { batchId.current = object(data).batch_id as string; setEditor(null); setPage(0); readFileSequence.current++ },
    reload: load,
  }
  const act = (action: string, extra: Record<string, Json> = {}) => {
    setError('')
    return run(action, { batch_id: batch?.id ?? null, expected_revision: action === 'SAVE_FILE' ? editorRevision.current : batch?.revision ?? null, ...extra }, null, handlers)
  }
  const upload = async (file: File | undefined) => {
    if (!file || locked || posted) return
    const sequence = ++readFileSequence.current, selected = entity, selectedBatch = batch?.id
    setReading(true); setError('')
    try {
      const rows = await readInitialImportFile(file, selected)
      if (sequence !== readFileSequence.current || selected !== entity || selectedBatch !== batchId.current) return
      editorRevision.current = batch?.revision ?? null; setEditor(rows); setFilename(file.name); setPage(0)
    } catch (failure) { if (sequence === readFileSequence.current) setError(normalizeClientError(failure).message) }
    finally { if (sequence === readFileSequence.current) setReading(false) }
  }
  const download = () => {
    const url = URL.createObjectURL(new Blob([initialImportTemplate(entity)], { type: 'text/csv;charset=utf-8' }))
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = `Impor_${entity}.csv`; anchor.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  const errors = batch?.rows.filter((row) => row.errors.length) ?? []
  return <section className="initial-import">
    <header className="panel initial-import-heading"><div><div className="eyebrow">PENGATURAN ERP</div><h1>Impor data awal</h1><p>Unggah tabel dari Excel, periksa isinya, lalu sahkan setelah semuanya cocok.</p></div><button type="button" disabled={mutation.busy || reading || Boolean(editor)} onClick={() => void load()}><RefreshCw size={16}/> Muat ulang</button></header>
    <ProductionRecoveryNotice recovery={mutation} onReconcile={() => reconcile(handlers)} className="initial-import-message"/>
    {error && <p role="alert" className="initial-import-message">{error}</p>}
    <div className="panel initial-import-toolbar">
      <label>Batch impor<select aria-label="Batch impor" disabled={locked || Boolean(editor)} value={batch?.id ?? ''} onChange={(event) => { batchId.current = event.target.value || null; setPage(0); void load() }}><option value="">Buat batch baru</option>{workspace?.recent.map((item) => <option key={item.id} value={item.id}>{item.batch_code} · {item.status}</option>)}</select></label>
      {!batch && <><label>Kode batch<input value={code} disabled={locked} maxLength={60} onChange={(event) => setCode(event.target.value)} placeholder="SALDO-AWAL-2026"/></label><label>Tanggal saldo awal<input type="date" value={date} disabled={locked} onChange={(event) => setDate(event.target.value)}/></label><button type="button" disabled={locked || !date || !code.trim()} onClick={() => void act('CREATE', { batch_code: code.trim(), cutover_date: date })}>Buat draft</button></>}
      {batch && <div><strong>{batch.code}</strong><p>{new Intl.DateTimeFormat('id-ID', { dateStyle: 'long', timeZone: 'Asia/Jakarta' }).format(new Date(batch.cutover_at))} · {posted ? 'Sudah disahkan' : 'Draft'} · {batch.rows.length} baris</p></div>}
    </div>
    {batch && <>
      <div className="panel initial-import-toolbar"><label>Jenis data<select disabled={locked || Boolean(editor)} value={entity} onChange={(event) => { setEntity(event.target.value as InitialImportEntity); setPage(0); readFileSequence.current++ }}>{Object.entries(initialImportCatalog).map(([key, item]) => <option key={key} value={key}>{item.label}</option>)}</select></label><button type="button" onClick={download}><Download size={16}/> Unduh template</button>{!posted && <label className="initial-import-upload"><FileUp size={16}/> Pilih file CSV<input aria-label="Pilih file CSV" type="file" accept=".csv,.tsv,text/csv" disabled={locked || Boolean(editor)} onChange={(event) => { const file = event.target.files?.[0]; event.target.value = ''; void upload(file) }}/></label>}</div>
      <p className="initial-import-help">Simpan dari Excel sebagai <strong>CSV UTF-8</strong>. Angka tanpa pemisah ribuan; desimal boleh memakai titik atau koma. Kolom aktif/absensi: true atau false. Satuan memakai kode ERP. Maksimal 5 MB dan 5.000 baris per batch. Hubungkan setiap rincian saldo ke kode total pembanding. Total pembanding hanya diperiksa dan tidak dibukukan.</p>
      {editor && editorRevision.current !== batch.revision && <p role="alert" className="initial-import-message">Draft di server sudah berubah. Perubahan di layar ini belum disimpan; batalkan perubahan lokal lalu periksa isi terbaru sebelum mengunggah ulang.</p>}
      {editor && <div className="initial-import-message" role="status"><span>{filename} · {editor.length} baris belum disimpan. Penyimpanan mengganti seluruh bagian “{spec.label}” dalam draft ini.</span><button type="button" disabled={locked || editorRevision.current !== batch.revision} onClick={() => void act('SAVE_FILE', { entity, filename, rows: editor as unknown as Json })}>Simpan perubahan draft</button><button type="button" disabled={mutation.busy || reading} onClick={() => { setEditor(null); setPage(0) }}>Batalkan perubahan</button></div>}
      <div className="panel initial-import-table"><table><thead><tr><th>Baris file</th>{fields.map(([key, label]) => <th key={key}>{label}{(spec.required as readonly string[]).includes(key) ? ' *' : ''}</th>)}{!editor && <th>Pemeriksaan</th>}</tr></thead><tbody>{shownRows.slice(page * 50, (page + 1) * 50).map((row, index) => <tr key={row.source_row_no}><th>{row.source_row_no}</th>{fields.map(([key, label]) => <td key={key}>{posted ? row.payload[key] ?? '—' : <input aria-label={`${label}, baris ${row.source_row_no}`} value={row.payload[key] ?? ''} disabled={locked} onChange={(event) => { const value = event.target.value; if (!editor) editorRevision.current = batch.revision; setEditor((current) => (current ?? storedRows).map((old, i) => i === page * 50 + index ? { source_row_no: old.source_row_no, payload: { ...old.payload, [key]: value } } : { source_row_no: old.source_row_no, payload: { ...old.payload } })); setFilename('Perbaikan di aplikasi') }}/>}</td>)}{!editor && <td>{(row as Row).errors?.join(' · ') || ((row as Row).validation_status === 'VALID' ? 'Valid' : 'Belum diperiksa')}</td>}</tr>)}</tbody></table>{shownRows.length === 0 && <p>Belum ada data {spec.label.toLowerCase()}. Unduh template lalu pilih file yang sudah diisi.</p>}</div>
      {shownRows.length > 50 && <nav className="initial-import-pagination" aria-label="Halaman rincian"><button type="button" disabled={page === 0} onClick={() => setPage(page - 1)}>Sebelumnya</button><span>{page + 1} / {Math.ceil(shownRows.length / 50)}</span><button type="button" disabled={(page + 1) * 50 >= shownRows.length} onClick={() => setPage(page + 1)}>Berikutnya</button></nav>}
      {errors.length > 0 && <div className="panel initial-import-errors" role="alert"><strong>{errors.length} baris perlu diperbaiki</strong><ul>{errors.slice(0,30).map((row) => <li key={row.id}>{initialImportCatalog[row.entity].label}, baris {row.source_row_no}: {row.errors.join(' · ')}</li>)}</ul>{errors.length > 30 && <p>Pilih jenis data untuk melihat seluruh kesalahan di tabel.</p>}</div>}
      {!posted && <footer className="panel initial-import-toolbar"><p>Draft tetap bisa diperbaiki. Pengesahan memeriksa ulang data terakhir dan membukukan seluruh batch sekaligus.</p><button type="button" disabled={locked || Boolean(editor) || !batch.rows.length} onClick={() => void act('VALIDATE')}>Periksa seluruh draft</button><button type="button" className="primary" disabled={locked || Boolean(editor) || !batch.rows.length || batch.status !== 'READY' || errors.length > 0} onClick={() => void act('FINALIZE')}>Sahkan data awal</button></footer>}
    </>}
  </section>
}

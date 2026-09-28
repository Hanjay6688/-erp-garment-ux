import { useEffect, useMemo, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { ArrowLeft, ArrowUpRight, Bell, BookOpen, Boxes, Clipboard, FileText, Layers3, MessageCircle, Scissors, Search, ShieldCheck, X } from 'lucide-react'
import type { RuntimeMode } from '../config/runtime'
import type { AnalysisResult, FactValue } from './contract'
import { createAnalysisReadPort, formatFact, projectShell, reasonLabel, refuseOperationalCommand, targetLabel } from './workspace'
import type { ExampleMode, PreviewAccess, ShellState, ShellView } from './workspace'
import { channelReadiness, previewWhatsApp, sendWhatsApp } from './notification'
import { benchmarks } from './benchmarks'
import './shell.css'

const pages = [
  { id: 'planner', label: 'Prioritas produksi', icon: Layers3 },
  { id: 'stock', label: 'Stok & saran SKU', icon: Boxes },
  { id: 'cutting', label: 'Panel Potongan', icon: Scissors },
  { id: 'report', label: 'Business Report', icon: FileText },
  { id: 'reminders', label: 'Reminder', icon: Bell },
  { id: 'ai', label: 'Tanya AI', icon: MessageCircle },
  { id: 'whatsapp', label: 'Sambungan WhatsApp', icon: ShieldCheck },
  { id: 'methods', label: 'Benchmark & metode', icon: BookOpen },
] as const
type Page = typeof pages[number]['id']
type Recommendation = AnalysisResult['recommendations'][number]
const initialState: ShellState = { kind: 'EMPTY', analysis: null, message: 'Belum terhubung ke data CP6.' }
const exampleOptions: Array<{ value: ExampleMode; label: string }> = [
  { value: 'EMPTY', label: 'Tanpa data' }, { value: 'FRAMEWORK', label: 'Contoh framework v2' },
  { value: 'PARTIAL', label: 'Contoh data parsial' }, { value: 'STALE', label: 'Contoh data berubah' },
  { value: 'ERROR', label: 'Contoh gagal baca' },
]

export default function Cp7Shell({ runtimeMode }: { runtimeMode: RuntimeMode }) {
  // Guard before the child mounts: connected runtime cannot even load fixtures.
  if (runtimeMode !== 'DEMO_SIMULATION') return <main className="cp7-shell cp7-unavailable"><ShieldCheck /><h1>Integrasi CP7 belum dibuka</h1><p>Data operasional belum terhubung. Sambungan sedang disiapkan dan diuji.</p><a href="/">Kembali ke ERP</a></main>
  return <PreviewWorkspace />
}

function PreviewWorkspace() {
  const [page, setPage] = useState<Page>('planner')
  const [mode, setMode] = useState<ExampleMode>('EMPTY')
  const [access, setAccess] = useState<PreviewAccess>('OWNER')
  const [state, setState] = useState<ShellState>(initialState)
  const [loading, setLoading] = useState(false)
  const [query, setQuery] = useState('')
  const [detail, setDetail] = useState<string | null>(null)
  const request = useRef(0)
  const port = useMemo(() => createAnalysisReadPort('DEMO_SIMULATION'), [])
  const view = useMemo(() => projectShell(state, access), [state, access])
  const rows = view.rows.filter(row => targetLabel(row.target).toLocaleLowerCase().includes(query.toLocaleLowerCase()))
  const actions = view.actions.filter(action => action.target_keys.some(key => rows.some(row => row.target.key === key)))
  const heading = pages.find(item => item.id === page)!.label
  useEffect(() => () => { request.current += 1 }, [])

  async function loadExample(next: ExampleMode) {
    const id = ++request.current
    setMode(next); setDetail(null); setLoading(true); setState(initialState)
    try {
      const loaded = await port.read(next)
      if (request.current === id) setState(loaded)
    } catch {
      if (request.current === id) setState({ kind: 'ERROR', analysis: null, message: 'Contoh tidak dapat dibaca atau tidak memenuhi kontrak. Hasil ditahan.' })
    } finally {
      if (request.current === id) setLoading(false)
    }
  }

  return <div className="cp7-shell">
    <aside className="cp7-sidebar">
      <a className="cp7-back" href="/"><ArrowLeft size={16} /> Kembali ke ERP</a>
      <div className="cp7-brand">ATELIER <span>CP7 / PRATINJAU</span></div>
      <nav aria-label="Ruang kerja CP7">{pages.map(({ id, label, icon: Icon }) => <button key={id} aria-current={page === id ? 'page' : undefined} onClick={() => { setPage(id); setDetail(null); setQuery('') }}><Icon size={19} /><span>{label}</span></button>)}</nav>
      <div className="cp7-rail-note"><ShieldCheck size={20} /><strong>Cangkang terpisah</strong><p>Sambungan data sedang disiapkan.</p></div>
    </aside>
    <main className="cp7-main">
      <header className="cp7-header"><div><span className="cp7-eyebrow">PERENCANAAN & KENDALI</span><h1>{heading}</h1></div><span className="cp7-tag">PRATINJAU · DATA CONTOH</span></header>
      <div className="cp7-controls">
        <label>Isi pratinjau<select value={mode} onChange={event => void loadExample(event.target.value as ExampleMode)}>{exampleOptions.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
        <label>Hak akses contoh<select value={access} onChange={event => { setAccess(event.target.value as PreviewAccess); setDetail(null) }}><option value="OWNER">Owner · contoh</option><option value="OPERATIONS">Operasional · tanpa keuangan</option><option value="DENIED">Tanpa akses</option></select></label>
        <button className="cp7-button" disabled={loading} onClick={() => void loadExample(mode)}>Muat ulang</button>
      </div>
      <div className="cp7-notice" data-state={state.kind} role="status" aria-live="polite">{loading ? 'Memuat contoh…' : state.message}</div>
      {view.denied ? <Empty title="Akses contoh ditolak" text="Tidak ada angka, laporan atau prompt yang ditampilkan untuk hak ini." /> : <>
        {view.analysis && <div className="cp7-context"><span>Fakta sampai <b>{dateLabel(view.analysis.snapshot.effective_as_of)}</b></span><span>Skenario <b>{view.analysis.scenario.kind === 'CONDITIONAL' ? 'Bersyarat' : 'Dasar'}</b></span><span>Basis <b>{view.analysis.snapshot.knowledge_mode}</b></span><details><summary>Waktu & sumber</summary><p>Diketahui sampai: {dateLabel(view.analysis.snapshot.known_as_of)}<br />Dibuat: {dateLabel(view.analysis.snapshot.generated_at)}<br />Run: {view.analysis.run_id}<br />Skenario: {view.analysis.scenario.id} / {view.analysis.scenario.version}</p></details></div>}
        {(page === 'planner' || page === 'stock') && <label className="cp7-search"><Search size={19} /><input aria-label="Cari SKU atau ukuran" placeholder="Cari merek, SKU, atau ukuran…" value={query} onChange={event => setQuery(event.target.value)} /></label>}
        {!view.analysis && !['whatsapp', 'methods'].includes(page) ? <Empty title={loading ? 'Menyiapkan contoh' : state.kind === 'EMPTY' ? 'Ruang kerja siap menerima data' : 'Hasil belum dapat ditampilkan'} text="Stok, WIP, biaya, dan rekomendasi belum dibaca. Kosong di sini tidak berarti nol atau semua aman."><button className="cp7-button cp7-primary" disabled={loading} onClick={() => void loadExample('FRAMEWORK')}>Lihat contoh framework <ArrowUpRight size={17} /></button></Empty> : <>
          {page === 'planner' && <><div className="cp7-section-heading"><h2>Tindakan yang perlu ditinjau</h2><span>{actions.length} tindakan terlihat · {rows.length} target ukuran</span></div><ActionList view={view} actions={actions} onDetail={setDetail} /><div className="cp7-footnote">Urutan mengikuti hasil analisis yang sama. Filter tidak mengalokasikan ulang sumber.</div></>}
          {page === 'stock' && <><div className="cp7-section-heading"><h2>Per ukuran fisik</h2><span>FG, WIP dan kebutuhan ditampilkan terpisah</span></div>{rows.length ? rows.map(row => <TargetCard key={row.target.key} row={row} onDetail={setDetail} />) : <Empty title="Tidak ada hasil filter" text="Filter tidak mengubah analisis atau stok." />}</>}
          {page === 'cutting' && <CuttingPreview view={view} onDetail={setDetail} />}
          {page === 'report' && <ReportPreview view={view} />}
          {page === 'reminders' && <Reminders view={view} onDetail={setDetail} />}
          {page === 'ai' && <><div className="cp7-section-heading"><h2>Tanya AI V1</h2><span>Salin, lalu tempel sendiri</span></div><p className="cp7-muted">Prompt memakai angka, asumsi, dan sumber dari analisis yang sedang dibuka.</p><CopyText key={`${access}-${state.kind}`} text={view.prompt} label="Prompt Tanya AI" /><a className="cp7-button cp7-link" href="https://chatgpt.com/" target="_blank" rel="noopener noreferrer">Buka ChatGPT <ArrowUpRight size={17} /></a><p className="cp7-footnote">Tautan dibuka tanpa membawa isi prompt. Jawaban AI tidak menyimpan atau menerapkan transaksi.</p></>}
          {page === 'whatsapp' && <WhatsAppPreview key={`${access}-${mode}`} view={view} />}
          {page === 'methods' && <Methods />}
        </>}
      </>}
      <footer className="cp7-footer"><span>CP6: diterima sesuai cakupan</span><span>CP7: cangkang & contoh lokal</span></footer>
    </main>
    {detail && view.analysis && <Dialog title="Dasar rekomendasi" onClose={() => setDetail(null)}><SourceDetail view={view} targetKey={detail} /></Dialog>}
  </div>
}

function dateLabel(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'Belum diketahui' : new Intl.DateTimeFormat('id-ID', { timeZone: 'Asia/Jakarta', dateStyle: 'medium', timeStyle: 'short' }).format(date) + ' WIB'
}

function Empty({ title, text, children }: { title: string; text: string; children?: ReactNode }) {
  return <div className="cp7-empty"><Layers3 size={30} /><h2>{title}</h2><p>{text}</p>{children}</div>
}

function Fact({ label, value }: { label: string; value: FactValue }) {
  return <div className="cp7-fact" data-fact-state={value.state}><span>{label}</span><strong>{formatFact(value)}</strong></div>
}

function TargetCard({ row, onDetail }: { row: Recommendation; onDetail: (key: string) => void }) {
  return <article className="cp7-card"><div className="cp7-card-heading"><h3>{targetLabel(row.target)}</h3><span className="cp7-tag">{row.production_state === 'ACTIVE' ? 'Aktif · contoh' : row.production_state === 'STOPPED' ? 'Jangan produksi lagi' : 'Produksi ditunda'}</span></div>
    <div className="cp7-facts"><Fact label="FG aktual" value={row.actual_fg} /><Fact label="Kebutuhan dasar" value={row.q_base} /><Fact label="Setelah kandidat · bersyarat" value={row.q_conditional} /><Fact label="Produksi yang layak" value={row.feasible_new} /></div>
    <p className="cp7-muted">{row.reason_codes.map(reasonLabel).join(' · ')}</p><button className="cp7-button" onClick={() => onDetail(row.target.key)}>Lihat dasar & ukuran <ArrowUpRight size={16} /></button>
  </article>
}

function ActionList({ view, actions = view.actions, onDetail }: { view: ShellView; actions?: ShellView['actions']; onDetail: (key: string) => void }) {
  if (!actions.length) return <Empty title="Belum ada tindakan pada tampilan ini" text="Jumlah ini bukan pernyataan bahwa produksi sudah aman." />
  return <div className="cp7-action-list">{actions.map(action => <article className="cp7-card cp7-action" key={action.key}>
    <div className="cp7-rank" aria-label={`Urutan contoh ${action.display_priority.rank ?? 'belum dinilai'}`}>{action.display_priority.rank ?? '—'}</div>
    <div className="cp7-action-body"><span className="cp7-eyebrow">{action.intent === 'CHECK_CANDIDATE' ? 'CEK KANDIDAT WIP' : action.intent}</span><h3>{reasonLabel(action.primary_reason)}</h3>
      {action.target_keys.map(key => { const row = view.rows.find(item => item.target.key === key); return row ? <div key={key}><p>{targetLabel(row.target)}</p><div className="cp7-facts"><Fact label="Kebutuhan dasar" value={row.q_base} /><Fact label="Bila kandidat sesuai & tepat waktu" value={row.q_conditional} /></div></div> : null })}
      <p className="cp7-muted">Kecocokan dan ETA perlu dikonfirmasi. Jumlah bersyarat belum menjadi perintah potong.</p>
      <div className="cp7-actions"><button className="cp7-button cp7-primary" onClick={() => onDetail(action.target_keys[0])}>Lihat detail <ArrowUpRight size={16} /></button><button className="cp7-button" disabled title={refuseOperationalCommand().message}>Terapkan rencana</button></div>
    </div>
  </article>)}</div>
}

function Dialog({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null)
  useEffect(() => { ref.current?.showModal(); return () => ref.current?.close() }, [])
  return <dialog className="cp7-dialog cp7-shell" ref={ref} aria-label={title} onCancel={onClose} onClose={onClose}><div className="cp7-dialog-heading"><h2>{title}</h2><button className="cp7-button" aria-label="Tutup detail" onClick={onClose}><X size={20} /></button></div>{children}</dialog>
}

function SourceDetail({ view, targetKey }: { view: ShellView; targetKey: string }) {
  const row = view.rows.find(item => item.target.key === targetKey)
  if (!row || !view.analysis) return null
  const analysis = view.analysis
  const edges = analysis.allocation_edges.filter(edge => edge.target_key === targetKey)
  return <div className="cp7-detail"><h3>{targetLabel(row.target)}</h3><p className="cp7-muted">Data contoh · satuan PCS. Sumber bersama tetap satu kapasitas.</p>
    <div className="cp7-facts"><Fact label="Target cakupan" value={row.target_qty} /><Fact label="Kebutuhan dasar" value={row.q_base} /><Fact label="Setelah kandidat" value={row.q_conditional} /><Fact label="Tambahan pembulatan" value={row.rounding_extra} /><Fact label="Layak diproduksi" value={row.feasible_new} /><Fact label="Kekurangan belum teratasi" value={row.unresolved_qty} /></div>
    <h3>Sumber WIP & alokasi</h3>{edges.map(edge => { const source = analysis.sources.find(item => item.source_key === edge.source_key)!; return <article className="cp7-source" key={`${edge.source_key}-${edge.target_key}`}><strong>{source.source_key}</strong><p>Tahap {source.stage} · ukuran {source.size_id} · {source.supply_kind === 'DIRECTED' ? 'Tujuan terarah' : 'Kandidat bersyarat'}</p><div className="cp7-facts"><Fact label="Sisa fisik sumber" value={source.physical_remaining} /><Fact label="Input dialokasikan" value={edge.input_qty} /><Fact label="Proyeksi output" value={edge.projected_output_qty} /></div><p>ETA: {source.eta ? dateLabel(source.eta) : 'Belum diketahui'} · {source.eta_basis === 'ASSUMED' ? 'asumsi' : source.eta_basis}</p></article> })}
    <h3>Identitas & histori</h3><p>Ukuran fisik: {row.target.size_id}. {row.target.kind === 'PRODUCT' ? `Versi produk: ${row.target.product_version_id}. Keanggotaan komersial: ${row.target.commercial_identity.membership_version_id ?? 'belum dipetakan'} (${row.target.commercial_identity.grouping_basis}).` : 'Belum ada identitas SKU final.'}</p>
    <h3>Asumsi yang dipakai</h3><ul>{analysis.assumptions.map(item => <li key={item.id}>{item.label}</li>)}</ul>
    <details><summary>Timeline skenario</summary><div className="cp7-table-scroll"><table><thead><tr><th>Tanggal</th><th>Demand</th><th>Saldo proyeksi</th><th>Gap pertama</th></tr></thead><tbody>{analysis.timeline.filter(item => item.target_key === targetKey).map(item => <tr key={item.date}><td>{item.date}</td><td>{formatFact(item.demand)}</td><td>{formatFact(item.balance_end)}</td><td>{item.first_gap_at ? dateLabel(item.first_gap_at) : 'Tidak tercatat pada contoh'}</td></tr>)}</tbody></table></div><p>Mode {analysis.timeline[0]?.mode}; urutan harian memakai kebijakan contoh, bukan kepastian jam fisik.</p></details>
    <details><summary>Referensi angka</summary><ul>{[row.actual_fg, row.q_base, row.q_conditional].flatMap((fact, index) => fact.refs.map(ref => <li key={`${index}-${ref.kind}-${ref.id}`}>{ref.kind}/{ref.id} · revisi {ref.revision}</li>))}</ul></details>
  </div>
}

function CuttingPreview({ view, onDetail }: { view: ShellView; onDetail: (key: string) => void }) {
  const [openedFrom, setOpenedFrom] = useState<string | null>(null)
  return <><div className="cp7-card"><h2>Rekomendasi di Buat / Bagi Potongan</h2><p className="cp7-muted">Coba panel yang sama dari dua pintu masuk. Pemasangan ke form transaksi menunggu sambungan CP6.</p><div className="cp7-actions"><button className="cp7-button" onClick={() => setOpenedFrom('Buat Potongan')}>Dari Buat Potongan</button><button className="cp7-button" onClick={() => setOpenedFrom('Bagi Potongan')}>Dari Bagi Potongan</button></div></div>{openedFrom && <div className="cp7-card"><div className="cp7-card-heading"><h2>Rekomendasi Produksi</h2><button className="cp7-button" onClick={() => setOpenedFrom(null)}>Tutup panel</button></div><p className="cp7-muted">Dibuka dari {openedFrom} · belum menyimpan draft.</p><ActionList view={view} onDetail={onDetail} /></div>}</>
}

function CopyText({ text, label }: { text: string; label: string }) {
  const [status, setStatus] = useState('')
  const [copying, setCopying] = useState(false)
  const attempt = useRef(0)
  useEffect(() => { attempt.current += 1; setStatus(''); setCopying(false); return () => { attempt.current += 1 } }, [text])
  async function copy() {
    const id = ++attempt.current; setCopying(true); setStatus('')
    try { await navigator.clipboard.writeText(text); if (attempt.current === id) setStatus('Teks berhasil disalin.') }
    catch { if (attempt.current === id) setStatus('Salin otomatis gagal. Pilih teks di bawah dan salin manual.') }
    finally { if (attempt.current === id) setCopying(false) }
  }
  return <div className="cp7-copy"><div className="cp7-actions"><button className="cp7-button" disabled={!text || copying} onClick={() => void copy()}><Clipboard size={16} />{copying ? 'Menyalin…' : 'Salin teks'}</button><span role="status">{status}</span></div><label className="cp7-text-label">{label}<textarea readOnly value={text} rows={15} /></label></div>
}

function ReportPreview({ view }: { view: ShellView }) {
  const [tab, setTab] = useState('Briefing')
  return <><div className="cp7-tabs" aria-label="Jenis laporan">{['Briefing', 'Review periode', 'Pengecualian', 'Arsip'].map(label => <button key={label} aria-pressed={tab === label} onClick={() => setTab(label)}>{label}</button>)}</div>
    {tab === 'Arsip' ? <Empty title="Belum ada laporan terbit" text="Arsip dan revisi laporan baru tersedia setelah penyimpanan authoritative tersambung." /> : tab === 'Review periode' ? <Empty title="Perbandingan periode menunggu data" text="Contoh ini hanya memiliki satu skenario. Periode pembanding tidak dibuat-buat." /> : <><article className="cp7-card"><h2>{tab === 'Pengecualian' ? 'Data yang masih perlu diperiksa' : 'Briefing dari analisis yang sama'}</h2>{tab === 'Pengecualian' ? <ul>{view.rows.flatMap(row => row.reason_codes.map(code => <li key={`${row.target.key}-${code}`}>{reasonLabel(code)}</li>))}<li>Utang/piutang dan jatuh tempo belum dibaca.</li></ul> : <div className="cp7-report">{view.report.split('\n\n').map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div>}</article><button className="cp7-button" disabled title={refuseOperationalCommand().message}>Terbitkan laporan</button></>}
  </>
}

function Reminders({ view, onDetail }: { view: ShellView; onDetail: (key: string) => void }) {
  const [domain, setDomain] = useState('Produksi')
  return <><div className="cp7-tabs" aria-label="Jenis reminder">{['Produksi', 'Aksesori', 'Utang', 'Piutang'].map(label => <button key={label} aria-pressed={domain === label} onClick={() => setDomain(label)}>{label}</button>)}</div><p className="cp7-muted">Kondisi sumber, perhatian operator, dan pengiriman adalah status terpisah.</p>
    {domain === 'Produksi' ? <ActionList view={view} onDetail={onDetail} /> : domain === 'Aksesori' ? <div className="cp7-card"><h2>Kebutuhan aksesori belum dapat dipastikan</h2>{view.analysis?.material_needs.map((item, index) => <div key={index}><Fact label="Tambahan dari luar" value={item.additional_external} /><p>BOM, pemasangan dan sisa yang dialokasikan perlu dibuktikan. Nota pengambilan saja belum cukup.</p></div>)}</div> : <Empty title={`${domain} belum dibaca`} text="Nominal outstanding, alokasi pembayaran/kredit, dan tanggal jatuh tempo menunggu sambungan data terverifikasi. Belum ada kesimpulan lunas atau terlambat." />}
  </>
}

function WhatsAppPreview({ view }: { view: ShellView }) {
  const [preview, setPreview] = useState(false)
  return <><div className="cp7-card"><h2>Pengiriman belum aktif</h2><p className="cp7-muted">Isi pesan memakai laporan yang sama. Cangkang hanya menampilkan pratinjau lokal.</p><dl className="cp7-readiness"><div><dt>Kontrak</dt><dd>{channelReadiness.contract === 'READY' ? 'Rancangan v2 tersedia' : 'Belum lengkap'}</dd></div><div><dt>Provider & penerima</dt><dd>Belum dipilih</dd></div><div><dt>Jadwal aktif</dt><dd>Tidak ada</dd></div><div><dt>Bukti terkirim / diterima</dt><dd>Belum diuji</dd></div></dl><div className="cp7-actions"><button className="cp7-button" disabled={!view.report} onClick={() => setPreview(true)}>Pratinjau isi pesan</button><button className="cp7-button" disabled title={sendWhatsApp().message}>Kirim WhatsApp</button></div></div>{preview && <CopyText text={previewWhatsApp(view)} label="Pratinjau lokal · tidak dikirim" />}</>
}

function Methods() {
  return <><p className="cp7-muted">Rujukan pakar untuk metode dan skenario awal. Belum menjadi kebijakan aktif atau angka usaha.</p><div className="cp7-method-grid">{benchmarks.map(item => <article className="cp7-card" key={item.title}><span className="cp7-eyebrow">USULAN BERDASARKAN RUJUKAN</span><h2>{item.title}</h2><p>{item.proposal}</p><p className="cp7-muted">{item.limit}</p><a href={item.url} target="_blank" rel="noopener noreferrer">{item.source} <ArrowUpRight size={14} /></a></article>)}</div><p className="cp7-footnote">Prioritas tetap mengikuti kontrak owner: gap bertanggal, tenggat sah, tindakan yang lebih cepat membantu, ukuran, lalu identitas stabil. Tidak ada klaim jadwal optimal.</p></>
}

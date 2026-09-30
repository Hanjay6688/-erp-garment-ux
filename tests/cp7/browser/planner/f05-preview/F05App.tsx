import { useEffect, useRef, useState } from 'react'
import { createAnalysisReadPort, projectShell, type AnalysisReadPort, type ExampleMode, type PreviewAccess, type ShellState } from '../../../../../src/cp7/workspace'
import type { RuntimeMode } from '../../../../../src/config/runtime'
import { ProductionPanel } from './ProductionPanel'
import { BusinessReport } from '../../../families/reports/preview/BusinessReport'
import { ReminderPanel } from '../../../families/reminder/preview/ReminderPanel'
import { AiPanel } from '../../ai-v1/preview/AiPanel'
import type { Page } from './model'
import { Empty } from './Common'
import type { YieldReadPort } from './CuttingYieldAnalyzer'
import './f05.css'

const pages: { key: Page; packet: string; label: string; description: string }[] = [
  { key: 'production', packet: 'P14', label: 'Panel produksi', description: 'Prioritas & alasan' },
  { key: 'reports', packet: 'P15', label: 'Business Report', description: 'Narasi & arsip' },
  { key: 'reminders', packet: 'P16', label: 'Reminder', description: 'Perhatian & simulasi' },
  { key: 'ai', packet: 'P17', label: 'Tanya AI', description: 'Prompt & sumber' },
]
const initialState: ShellState = { kind: 'EMPTY', analysis: null, message: 'Pilih data contoh secara eksplisit untuk menguji cangkang.' }
const fixturePort = createAnalysisReadPort('DEMO_SIMULATION')

export default function F05App({ runtimeMode, readPort = fixturePort, yieldReadPort }: { runtimeMode: RuntimeMode; readPort?: AnalysisReadPort; yieldReadPort?: YieldReadPort }) {
  if (runtimeMode !== 'DEMO_SIMULATION') return <main className="cp7-f05"><Empty title="Integrasi F05 belum dibuka" text="Cangkang ini hanya menerima data contoh pada pratinjau demo. Pembaca operasional belum disambungkan." /></main>
  return <Preview readPort={readPort} yieldReadPort={yieldReadPort} />
}
function Preview({ readPort, yieldReadPort }: { readPort: AnalysisReadPort; yieldReadPort?: YieldReadPort }) {
  const [mode, setMode] = useState<ExampleMode>('EMPTY')
  const [access, setAccess] = useState<PreviewAccess>('OWNER')
  const [page, setPage] = useState<Page>('production')
  const [snapshot, setSnapshot] = useState<{ port: AnalysisReadPort; state: ShellState }>({ port: readPort, state: initialState })
  // Replacing a reader withholds its old snapshot immediately, before effects.
  const state = snapshot.port === readPort ? snapshot.state : initialState
  const [loading, setLoading] = useState(false)
  const request = useRef(0)
  useEffect(() => { request.current += 1; setLoading(false); return () => { request.current += 1 } }, [readPort])
  async function load(next: ExampleMode) {
    const id = ++request.current; setMode(next); setLoading(true)
    try { const result = await readPort.read(next); if (request.current === id) setSnapshot({ port: readPort, state: result }) }
    catch { if (request.current === id) setSnapshot({ port: readPort, state: { kind: 'ERROR', analysis: null, message: 'Pembacaan gagal. Muat ulang secara eksplisit; data contoh tidak menjadi fallback otomatis.' } }) }
    finally { if (request.current === id) setLoading(false) }
  }
  const view = projectShell(state, access)
  const stale = state.kind === 'STALE'
  const blocked = loading || view.denied || !view.analysis
  return <div className="cp7-f05"><aside className="f05-sidebar"><div className="f05-brand"><span className="f05-brand-icon">H</span><div>HANSEN’S<small>OPERATIONS WORKSPACE</small></div></div><p className="f05-nav-caption">CP7 · CANGKANG F05</p><nav aria-label="Menu F05">{pages.map(item => <button key={item.key} aria-current={page === item.key ? 'page' : undefined} onClick={() => setPage(item.key)}><span className="f05-nav-packet">{item.packet}</span><span>{item.label}<small>{item.description}</small></span></button>)}</nav><div className="f05-sidebar-footer"><span className="f05-dot" /> DATA CONTOH<p>Pratinjau terpisah.<br />Belum terhubung ke transaksi.</p></div></aside>
    <main className="f05-main"><header className="f05-topbar"><div><span className="f05-kicker">WORKSPACE / {pages.find(item => item.key === page)!.packet}</span><h1>{pages.find(item => item.key === page)!.label}</h1></div><span className="f05-badge">Cangkang · belum terintegrasi</span></header>
      <section className="f05-controls" aria-label="Kontrol data contoh"><label>Data contoh<select value={mode} onChange={event => void load(event.target.value as ExampleMode)}><option value="EMPTY">Kosong</option><option value="FRAMEWORK">Contoh framework</option><option value="PARTIAL">Data kurang</option><option value="STALE">Data kedaluwarsa</option><option value="ERROR">Gagal memuat</option></select></label><label>Hak akses contoh<select value={access} onChange={event => setAccess(event.target.value as PreviewAccess)}><option value="OWNER">Owner</option><option value="OPERATIONS">Operasional · tanpa keuangan</option><option value="DENIED">Akses ditolak</option></select></label><button onClick={() => void load(mode)}>Muat ulang contoh</button></section>
      <div className="f05-alert" role="status">{loading ? 'Memuat snapshot contoh…' : view.denied ? 'Akses ditolak. Data, arsip, dan prompt tidak ditampilkan.' : state.message}</div>
      {blocked ? <Empty title={view.denied ? 'Akses ditolak' : loading ? 'Membaca snapshot' : state.kind === 'PARTIAL' ? 'Data belum lengkap' : state.kind === 'ERROR' ? 'Hasil belum tersedia' : 'Cangkang siap menerima data'} text={view.denied ? 'Hak contoh ini tidak memiliki izin membaca analisis.' : 'Rekomendasi dan angka ditahan sampai snapshot lengkap tersedia.'} /> : null}
      {view.analysis ? <div hidden={blocked}><Workspace key={JSON.stringify([access, view.analysis.scope.actor_scope_id, view.analysis.versions.access_epoch])} page={page} view={view} stale={stale || loading} yieldReadPort={yieldReadPort} /></div> : null}
      <footer className="f05-footer">F05 P14–P17 · uji fixture · server, penerapan, penerbitan, WA, dan API AI belum tersambung.</footer>
    </main></div>
}
function Workspace({ page, view, stale, yieldReadPort }: { page: Page; view: ReturnType<typeof projectShell>; stale: boolean; yieldReadPort?: YieldReadPort }) {
  const analysis = view.analysis!
  return <><div className="f05-context"><div><span>RUN</span><strong>{analysis.run_id}</strong></div><div><span>BATAS FAKTA · ASIA/JAKARTA</span><strong>{analysis.snapshot.effective_as_of}</strong></div><div><span>SKENARIO</span><strong>{analysis.scenario.id} · v{analysis.scenario.version}</strong></div></div>
    <details className="f05-source"><summary>Konteks snapshot & versi</summary><p>Diketahui sampai {analysis.snapshot.known_as_of} · dibuat {analysis.snapshot.generated_at} · {analysis.snapshot.knowledge_mode}</p><p>Engine {analysis.versions.engine} · policy {analysis.versions.policy} · model {analysis.versions.models} · template {analysis.versions.template}</p><p>Scope tampilan {analysis.scope.actor_scope_id} · alokasi {analysis.scope.allocation_scope_id} · snapshot {analysis.snapshot.snapshot_id}</p></details>
    <section hidden={page !== 'production'} aria-label="Panel produksi"><ProductionPanel view={view} stale={stale} yieldReadPort={yieldReadPort} /></section>
    <section hidden={page !== 'reports'} aria-label="Business Report"><BusinessReport view={view} stale={stale} /></section>
    <section hidden={page !== 'reminders'} aria-label="Reminder"><ReminderPanel view={view} stale={stale} /></section>
    <section hidden={page !== 'ai'} aria-label="Tanya AI"><AiPanel view={view} stale={stale} /></section>
  </>
}

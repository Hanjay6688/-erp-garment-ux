import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Check, ChevronDown,
  Clock3, FileSearch, GitCompareArrows, History, Info, Layers3, LockKeyhole,
  PackageSearch, RefreshCcw, Search, ShieldCheck, SlidersHorizontal,
} from 'lucide-react'
import './hpp.css'

type CostState = 'ESTIMATED' | 'ACTUAL' | 'ADJUSTED'
type DisplayStatus = 'SEMENTARA' | 'BELUM_LENGKAP' | 'LENGKAP_BERDASARKAN_DATA_SAAT_INI'
type HppTab = 'composition' | 'history' | 'recost'
type ComponentType = 'MATERIAL' | 'ACCESSORY' | 'LABOR' | 'COMMISSION' | 'LAUNDRY' | 'REWORK' | 'CONVERSION' | 'OTHER'

type HppComponent = {
  type: ComponentType
  label: string
  perPcs: number
  total: number
  sourceType: string
  sourceId: string
  basis: string
  sourceDate: string
}

type HppVersion = {
  no: number
  state: CostState
  calculatedAt: string
  reason: string
  components: HppComponent[]
  perPcs: number
  total: number
}

type CompletenessCheck = { label: string; note: string; ok: boolean }

type HppLot = {
  id: string
  po: string
  brand: string
  sku: string
  product: string
  color: string
  material: string
  qty: number
  soldQty: number
  sizes: string
  producedAt: string
  displayStatus: DisplayStatus
  currentVersion: number
  versions: HppVersion[]
  checks: CompletenessCheck[]
}

const money = (value: number) => new Intl.NumberFormat('id-ID', {
  style: 'currency', currency: 'IDR', maximumFractionDigits: 0,
}).format(value)

const signedMoney = (value: number) => `${value > 0 ? '+' : value < 0 ? '−' : ''}${money(Math.abs(value))}`

const componentInfo: Record<ComponentType, { label: string; short: string }> = {
  MATERIAL: { label: 'Kain & bahan utama', short: 'Kain' },
  ACCESSORY: { label: 'Aksesori', short: 'Aksesori' },
  LABOR: { label: 'Jahitan & tenaga kerja', short: 'Jahit' },
  COMMISSION: { label: 'Komisi produksi', short: 'Komisi' },
  LAUNDRY: { label: 'Laundry', short: 'Laundry' },
  REWORK: { label: 'BS & rework', short: 'Rework' },
  CONVERSION: { label: 'Biaya konversi', short: 'Konversi' },
  OTHER: { label: 'Lain-lain & penyesuaian', short: 'Lainnya' },
}

const componentOrder: ComponentType[] = ['MATERIAL', 'ACCESSORY', 'LABOR', 'COMMISSION', 'LAUNDRY', 'REWORK', 'CONVERSION', 'OTHER']

function makeVersion(
  qty: number,
  no: number,
  state: CostState,
  calculatedAt: string,
  reason: string,
  costs: Partial<Record<ComponentType, number>>,
  sources: Partial<Record<ComponentType, Pick<HppComponent, 'sourceType' | 'sourceId' | 'basis' | 'sourceDate'>>> = {},
): HppVersion {
  const defaults: Record<ComponentType, Pick<HppComponent, 'sourceType' | 'sourceId' | 'basis' | 'sourceDate'>> = {
    MATERIAL: { sourceType: 'CUTTING_BATCH', sourceId: 'POT-260826-041', basis: 'Pemakaian roll × moving average pada tanggal potong, dialokasikan lewat hasil efektif batch.', sourceDate: '26 Agu 2026' },
    ACCESSORY: { sourceType: 'FG_ACCESSORY_SNAPSHOT', sourceId: 'FACS-260827-005', basis: 'GOOD FG × BOM kategori aksesori. Snapshot terkunci agar histori tidak ikut berubah.', sourceDate: '27 Agu 2026' },
    LABOR: { sourceType: 'CUTTING_GROUP', sourceId: 'POT-041-B02', basis: 'Komponen kerja POSTED dari grup yang sama; fallback biaya bersama PO bila tidak punya lineage.', sourceDate: '27 Agu 2026' },
    COMMISSION: { sourceType: 'CUTTING_GROUP', sourceId: 'POT-041-B02', basis: 'Komisi terposting dari grup yang sama dan dibagi ke GOOD FG.', sourceDate: '27 Agu 2026' },
    LAUNDRY: { sourceType: 'CUTTING_GROUP', sourceId: 'POT-041-B02', basis: 'Biaya aktual penerimaan laundry; bagian yang belum final tetap memakai estimasi pengiriman.', sourceDate: '27 Agu 2026' },
    REWORK: { sourceType: 'CUTTING_GROUP', sourceId: 'POT-041-B02', basis: 'Biaya rework yang sudah POSTED, bukan sekadar kasus BS yang masih terbuka.', sourceDate: '27 Agu 2026' },
    CONVERSION: { sourceType: 'PO', sourceId: 'PO-260812-028', basis: 'Biaya konversi terpisah yang sah pada kontrak HPP.', sourceDate: '27 Agu 2026' },
    OTHER: { sourceType: 'PO', sourceId: 'PO-260812-028', basis: 'Penyesuaian lain yang punya alasan, sumber, tanggal ekonomi, dan audit trail.', sourceDate: '27 Agu 2026' },
  }
  const components = componentOrder
    .filter((type) => (costs[type] ?? 0) !== 0)
    .map((type) => {
      const perPcs = costs[type] ?? 0
      return { type, label: componentInfo[type].label, perPcs, total: perPcs * qty, ...defaults[type], ...sources[type] }
    })
  const perPcs = components.reduce((sum, component) => sum + component.perPcs, 0)
  return { no, state, calculatedAt, reason, components, perPcs, total: perPcs * qty }
}

const allComplete: CompletenessCheck[] = [
  { label: 'FG dan HPP current terbentuk', note: 'Semua lot produksi punya satu HPP aktif.', ok: true },
  { label: 'Produksi sudah selesai', note: 'PO berstatus FINISHED.', ok: true },
  { label: 'Biaya laundry final', note: 'Tidak ada qty laundry yang masih memakai estimasi.', ok: true },
  { label: 'BOM kerja dikonfirmasi', note: 'Snapshot komponen kerja tersedia.', ok: true },
  { label: 'Semua komponen kerja terposting', note: 'Tidak ada komponen upah yang belum pernah POSTED.', ok: true },
  { label: 'Snapshot aksesori tersedia', note: 'GOOD FG × BOM kategori sudah dibekukan.', ok: true },
  { label: 'BS/rework selesai', note: 'Tidak ada kasus OPEN, IN_REWORK, atau PARTIAL.', ok: true },
  { label: 'Antrean recost bersih', note: 'Tidak ada recost PENDING, RUNNING, atau FAILED.', ok: true },
]

const firstLotQty = 138
const firstLotVersions = [
  makeVersion(firstLotQty, 1, 'ESTIMATED', '27 Agu 2026 · 09:55', 'HPP awal saat QC membentuk FG; kain dan laundry masih benchmark.', {
    MATERIAL: 57200, ACCESSORY: 9150, LABOR: 24800, COMMISSION: 2200, LAUNDRY: 13800, REWORK: 2400, OTHER: 7500,
  }),
  makeVersion(firstLotQty, 2, 'ACTUAL', '27 Agu 2026 · 16:20', 'Kasbon kain dan tagihan laundry diposting; biaya aktual menggantikan benchmark.', {
    MATERIAL: 58100, ACCESSORY: 9150, LABOR: 24800, COMMISSION: 2200, LAUNDRY: 14500, REWORK: 3300, OTHER: 7500,
  }, {
    MATERIAL: { sourceType: 'CUTTING_BATCH', sourceId: 'POT-260826-041', basis: 'Moving average kain sesudah kasbon Sinaran diposting, dialokasikan lewat hasil efektif batch.', sourceDate: '27 Agu 2026' },
    LAUNDRY: { sourceType: 'CUTTING_GROUP', sourceId: 'LD-RCP-260827-012', basis: 'Penerimaan laundry FINAL dari Berkah Laundry.', sourceDate: '27 Agu 2026' },
  }),
  makeVersion(firstLotQty, 3, 'ADJUSTED', '27 Agu 2026 · 18:42', 'Koreksi kronologis moving average kain setelah invoice final.', {
    MATERIAL: 58400, ACCESSORY: 9150, LABOR: 24800, COMMISSION: 2200, LAUNDRY: 14500, REWORK: 3300, OTHER: 7500,
  }, {
    MATERIAL: { sourceType: 'CUTTING_BATCH', sourceId: 'POT-260826-041', basis: 'Moving average kain yang sudah direcost kronologis. Versi lama tetap terkunci.', sourceDate: '27 Agu 2026' },
  }),
]

const hppLots: HppLot[] = [
  {
    id: 'FG-260827-005', po: 'PO-260812-028', brand: 'Widie', sku: '73002', product: 'Widie Regular', color: 'Vintage Blue', material: 'Lucy', qty: firstLotQty, soldQty: 12, sizes: '31–33', producedAt: '27 Agu 2026 · 09:55', displayStatus: 'LENGKAP_BERDASARKAN_DATA_SAAT_INI', currentVersion: 3, versions: firstLotVersions, checks: allComplete,
  },
  {
    id: 'FG-260827-006', po: 'PO-260812-031', brand: 'Vivo', sku: '73002', product: 'Vivo Regular', color: 'Washed Blue', material: 'Lucy', qty: 72, soldQty: 0, sizes: '31–33', producedAt: '27 Agu 2026 · 10:22', displayStatus: 'BELUM_LENGKAP', currentVersion: 2,
    versions: [
      makeVersion(72, 1, 'ESTIMATED', '27 Agu 2026 · 10:22', 'HPP awal dari QC.', { MATERIAL: 56600, ACCESSORY: 8700, LABOR: 23600, COMMISSION: 1800, LAUNDRY: 13200, REWORK: 0, OTHER: 5900 }),
      makeVersion(72, 2, 'ACTUAL', '27 Agu 2026 · 17:08', 'Invoice utama sudah aktual; kelengkapan operasional masih diperiksa.', { MATERIAL: 57800, ACCESSORY: 8700, LABOR: 23600, COMMISSION: 1800, LAUNDRY: 13700, REWORK: 2400, OTHER: 5900 }),
    ],
    checks: allComplete.map((item) => item.label === 'Semua komponen kerja terposting'
      ? { ...item, ok: false, note: 'Pasang kancing belum pernah POSTED.' }
      : item.label === 'BS/rework selesai'
        ? { ...item, ok: false, note: '4 pcs masih IN_REWORK.' }
        : item),
  },
  {
    id: 'FG-260826-021', po: 'PO-260810-024', brand: 'Widie', sku: '73001', product: 'Widie Daily', color: 'Dark Navy', material: 'Zodiak KW', qty: 252, soldQty: 0, sizes: '28–30', producedAt: '26 Agu 2026 · 15:40', displayStatus: 'SEMENTARA', currentVersion: 1,
    versions: [
      makeVersion(252, 1, 'ESTIMATED', '26 Agu 2026 · 15:40', 'Sebagian produksi belum selesai; laundry masih memakai tarif estimasi.', { MATERIAL: 54100, ACCESSORY: 8250, LABOR: 22900, COMMISSION: 1800, LAUNDRY: 12100, REWORK: 0, OTHER: 5600 }),
    ],
    checks: allComplete.map((item) => item.label === 'Produksi sudah selesai'
      ? { ...item, ok: false, note: 'PO masih IN_PROGRESS.' }
      : item.label === 'Biaya laundry final'
        ? { ...item, ok: false, note: '96 pcs masih memakai tarif estimasi pengiriman.' }
        : item),
  },
  {
    id: 'FG-260825-018', po: 'PO-260809-019', brand: 'Vivo', sku: '73001', product: 'Vivo Classic', color: 'Indigo', material: '1069 Ori', qty: 216, soldQty: 36, sizes: '28–30', producedAt: '25 Agu 2026 · 14:10', displayStatus: 'LENGKAP_BERDASARKAN_DATA_SAAT_INI', currentVersion: 2,
    versions: [
      makeVersion(216, 1, 'ESTIMATED', '25 Agu 2026 · 14:10', 'HPP awal dari QC.', { MATERIAL: 60300, ACCESSORY: 9400, LABOR: 25100, COMMISSION: 2200, LAUNDRY: 14200, OTHER: 6200 }),
      makeVersion(216, 2, 'ACTUAL', '26 Agu 2026 · 11:20', 'Seluruh biaya sumber sudah aktual dan lengkap saat ini.', { MATERIAL: 61500, ACCESSORY: 9400, LABOR: 25100, COMMISSION: 2200, LAUNDRY: 14700, OTHER: 6200 }),
    ], checks: allComplete,
  },
]

const stateLabel: Record<CostState, string> = { ESTIMATED: 'Sementara', ACTUAL: 'Aktual', ADJUSTED: 'Disesuaikan' }
const statusLabel: Record<DisplayStatus, string> = {
  SEMENTARA: 'Sementara', BELUM_LENGKAP: 'Belum lengkap', LENGKAP_BERDASARKAN_DATA_SAAT_INI: 'Lengkap saat ini',
}

function HppPage() {
  const [query, setQuery] = useState('')
  const [brand, setBrand] = useState('Semua merek')
  const [status, setStatus] = useState('Semua status')
  const [activeLotId, setActiveLotId] = useState(hppLots[0].id)
  const [activeVersionNo, setActiveVersionNo] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<HppTab>('composition')
  const [selectedComponent, setSelectedComponent] = useState<ComponentType>('MATERIAL')
  const [recostDrafts, setRecostDrafts] = useState<Record<string, string>>({})
  const [recostReasons, setRecostReasons] = useState<Record<string, string>>({
    [hppLots[0].id]: 'Invoice final kain Sinaran berbeda dari moving average terakhir',
  })
  const [simulationNotice, setSimulationNotice] = useState('')

  const visibleLots = useMemo(() => hppLots.filter((lot) => {
    const haystack = `${lot.po} ${lot.id} ${lot.brand} ${lot.sku} ${lot.product} ${lot.color} ${lot.material}`.toLowerCase()
    const matchesQuery = haystack.includes(query.toLowerCase())
    const matchesBrand = brand === 'Semua merek' || lot.brand === brand
    const matchesStatus = status === 'Semua status' || lot.displayStatus === status
    return matchesQuery && matchesBrand && matchesStatus
  }), [query, brand, status])

  const lot = visibleLots.find((item) => item.id === activeLotId) ?? visibleLots[0] ?? hppLots[0]
  const currentVersion = lot.versions.find((version) => version.no === lot.currentVersion) ?? lot.versions[lot.versions.length - 1]
  const viewedVersion = lot.versions.find((version) => version.no === activeVersionNo) ?? currentVersion
  const historicalView = viewedVersion.no !== currentVersion.no
  const currentComponent = viewedVersion.components.find((component) => component.type === selectedComponent) ?? viewedVersion.components[0]
  const firstVersion = lot.versions[0]
  const hppDelta = currentVersion.perPcs - firstVersion.perPcs
  const completedChecks = lot.checks.filter((item) => item.ok).length
  const pendingChecks = lot.checks.length - completedChecks
  const materialComponent = currentVersion.components.find((component) => component.type === 'MATERIAL')!
  const proposedMaterial = Math.max(0, Number((recostDrafts[lot.id] ?? String(materialComponent.perPcs + 750)).replace(/[^0-9]/g, '')) || 0)
  const proposedDeltaPerPcs = proposedMaterial - materialComponent.perPcs
  const proposedHpp = currentVersion.perPcs + proposedDeltaPerPcs
  const inventoryImpact = proposedDeltaPerPcs * Math.max(0, lot.qty - lot.soldQty)
  const cogsImpact = proposedDeltaPerPcs * lot.soldQty
  const totalImpact = inventoryImpact + cogsImpact
  const reason = recostReasons[lot.id] ?? ''

  const chooseLot = (id: string) => {
    setActiveLotId(id)
    setActiveVersionNo(null)
    setSelectedComponent('MATERIAL')
    setSimulationNotice('')
  }

  return <>
    <section className="hero-copy compact hpp-hero">
      <div>
        <div className="eyebrow">KEUANGAN · COSTING PER FG LOT</div>
        <h1>HPP & Rekalkulasi</h1>
        <p>Satu HPP aktif untuk keputusan hari ini. Semua versi lama tetap terkunci untuk audit.</p>
      </div>
      <details className="hpp-state-guide">
        <summary><Info /> 3 keadaan biaya <ChevronDown /></summary>
        <div>
          <article><b>01</b><span><strong>Sementara</strong><small>Benchmark sebelum biaya final lengkap.</small></span></article>
          <article><b>02</b><span><strong>Aktual</strong><small>Sumber aktual sudah masuk; belum otomatis berarti lengkap.</small></span></article>
          <article><b>03</b><span><strong>Disesuaikan</strong><small>Versi baru sesudah koreksi atau recost.</small></span></article>
          <p>Bukan tiga angka aktif. Backend hanya mengizinkan satu versi current per lot.</p>
        </div>
      </details>
    </section>

    <section className="hpp-kpis">
      <article className="panel"><span>LOT DIPANTAU</span><strong>{hppLots.length}</strong><small>Unit versi HPP adalah FG lot</small></article>
      <article className="panel warn"><span>SEMENTARA</span><strong>{hppLots.filter((item) => item.displayStatus === 'SEMENTARA').length}</strong><small>Masih memakai benchmark</small></article>
      <article className="panel alert"><span>BELUM LENGKAP</span><strong>{hppLots.filter((item) => item.displayStatus === 'BELUM_LENGKAP').length}</strong><small>Butuh tindak lanjut sumber biaya</small></article>
      <article className="panel good"><span>LENGKAP SAAT INI</span><strong>{hppLots.filter((item) => item.displayStatus === 'LENGKAP_BERDASARKAN_DATA_SAAT_INI').length}</strong><small>Tetap bisa punya versi koreksi baru</small></article>
    </section>

    <section className="hpp-master-detail">
      <aside className="panel hpp-lot-browser">
        <header><div><span>PILIH LOT / PO</span><strong>{visibleLots.length} hasil</strong></div><PackageSearch /></header>
        <div className="hpp-search"><Search /><input aria-label="Cari PO, lot, SKU, atau bahan" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Cari PO, lot, SKU, bahan..." /></div>
        <div className="hpp-filter-row">
          <label><SlidersHorizontal /><select aria-label="Filter merek" value={brand} onChange={(event) => setBrand(event.target.value)}><option>Semua merek</option><option>Widie</option><option>Vivo</option></select></label>
          <label><select aria-label="Filter status HPP" value={status} onChange={(event) => setStatus(event.target.value)}><option>Semua status</option><option value="SEMENTARA">Sementara</option><option value="BELUM_LENGKAP">Belum lengkap</option><option value="LENGKAP_BERDASARKAN_DATA_SAAT_INI">Lengkap</option></select></label>
        </div>
        <div className="hpp-lot-list">
          {visibleLots.map((item) => {
            const version = item.versions.find((row) => row.no === item.currentVersion) ?? item.versions[item.versions.length - 1]
            return <button key={item.id} className={item.id === lot.id ? 'active' : ''} onClick={() => chooseLot(item.id)}>
              <span className="hpp-lot-seq">{String(hppLots.indexOf(item) + 1).padStart(2, '0')}</span>
              <span className="hpp-lot-copy"><small>{item.brand} · SKU {item.sku}</small><strong>{item.po}</strong><em>{item.id} · {item.material} · {item.qty} pcs</em></span>
              <span className={`hpp-lot-state ${item.displayStatus.toLowerCase()}`}>{statusLabel[item.displayStatus]}</span>
              <span className="hpp-lot-cost">{money(version.perPcs)}<small>/ pcs · v{version.no}</small></span>
            </button>
          })}
          {visibleLots.length === 0 && <div className="hpp-no-lot"><FileSearch /><strong>Lot tidak ketemu</strong><small>Ubah pencarian atau filter.</small></div>}
        </div>
      </aside>

      <div className="hpp-detail-stack">
        <section className="panel hpp-current-card">
          <header>
            <div className="hpp-product-id"><span>{lot.brand.slice(0, 1)}</span><div><small>{lot.brand} · SKU {lot.sku} · RANGE {lot.sizes}</small><h2>{lot.product} · {lot.color}</h2><p>{lot.po} · {lot.id} · {lot.material}</p></div></div>
            <div className={`hpp-display-status ${lot.displayStatus.toLowerCase()}`}><span>{statusLabel[lot.displayStatus]}</span><small>{currentVersion.state} · current v{currentVersion.no}</small></div>
          </header>
          <div className="hpp-current-grid">
            <div className="hpp-hero-cost"><span>HPP AKTIF / PCS</span><strong>{money(currentVersion.perPcs)}</strong><small>{money(currentVersion.total)} total · basis {lot.qty} pcs</small></div>
            <div><span>PERUBAHAN DARI V1</span><strong className={hppDelta >= 0 ? 'up' : 'down'}>{signedMoney(hppDelta)} <small>/ pcs</small></strong><small>{signedMoney(hppDelta * lot.qty)} seluruh lot</small></div>
            <div><span>DIPERBARUI</span><strong>{currentVersion.calculatedAt.split(' · ')[0]}</strong><small>{currentVersion.calculatedAt.split(' · ')[1]} · v{currentVersion.no}</small></div>
            <div><span>KELENGKAPAN</span><strong>{completedChecks}/{lot.checks.length} cek</strong><small>{pendingChecks ? `${pendingChecks} alasan masih terbuka` : 'Tidak ada alasan terbuka'}</small></div>
          </div>
          <div className="hpp-version-rail">
            {lot.versions.map((version, index) => <div className="hpp-version-step" key={version.no}>
              <button className={`${version.no === viewedVersion.no ? 'active' : ''} ${version.no === currentVersion.no ? 'current' : ''}`} onClick={() => setActiveVersionNo(version.no)}>
                <b>v{version.no}</b><span><strong>{stateLabel[version.state]}</strong><small>{money(version.perPcs)} / pcs</small></span>{version.no === currentVersion.no && <em>AKTIF</em>}
              </button>
              {index < lot.versions.length - 1 && <i><ArrowRight /></i>}
            </div>)}
          </div>
          {historicalView && <div className="hpp-history-notice"><History /><div><strong>Lu sedang melihat versi lama v{viewedVersion.no}</strong><span>HPP aktif tetap v{currentVersion.no} · {money(currentVersion.perPcs)} / pcs.</span></div><button onClick={() => setActiveVersionNo(null)}>Kembali ke aktif</button></div>}
        </section>

        <nav className="hpp-tabs panel" aria-label="Bagian HPP">
          <button className={activeTab === 'composition' ? 'active' : ''} onClick={() => setActiveTab('composition')}><Layers3 /> Komposisi & sumber</button>
          <button className={activeTab === 'history' ? 'active' : ''} onClick={() => setActiveTab('history')}><History /> Riwayat versi</button>
          <button className={activeTab === 'recost' ? 'active' : ''} onClick={() => setActiveTab('recost')}><RefreshCcw /> Review rekalkulasi</button>
        </nav>

        {activeTab === 'composition' && <section className="hpp-composition-layout">
          <div className="panel hpp-components">
            <header><div><span>KOMPOSISI v{viewedVersion.no}</span><h2>{historicalView ? 'Snapshot historis' : 'Pembentuk HPP aktif'}</h2></div><strong>{money(viewedVersion.perPcs)} / pcs</strong></header>
            <div className="hpp-component-head"><span>Komponen</span><span>Per pcs</span><span>Total lot</span><span>Porsi</span></div>
            <div className="hpp-component-list">
              {viewedVersion.components.map((component) => {
                const share = viewedVersion.perPcs ? (component.perPcs / viewedVersion.perPcs) * 100 : 0
                return <button key={component.type} className={component.type === currentComponent?.type ? 'active' : ''} onClick={() => setSelectedComponent(component.type)}>
                  <span className={`hpp-component-icon ${component.type.toLowerCase()}`}>{componentInfo[component.type].short.slice(0, 1)}</span>
                  <span><strong>{component.label}</strong><small>{component.sourceType}</small></span>
                  <b>{money(component.perPcs)}</b>
                  <b>{money(component.total)}</b>
                  <span className="hpp-share"><i style={{ width: `${share}%` }} /><small>{share.toFixed(1)}%</small></span>
                </button>
              })}
            </div>
            <footer><span>Total snapshot v{viewedVersion.no}</span><strong>{money(viewedVersion.total)}</strong><small>{viewedVersion.components.length} komponen · {lot.qty} pcs</small></footer>
          </div>

          <aside className="panel hpp-source-detail">
            <header><span>JEJAK SUMBER</span><FileSearch /></header>
            {currentComponent && <>
              <div className="hpp-source-title"><span className={`hpp-component-icon ${currentComponent.type.toLowerCase()}`}>{componentInfo[currentComponent.type].short.slice(0, 1)}</span><div><small>{currentComponent.type}</small><h3>{currentComponent.label}</h3></div></div>
              <dl>
                <div><dt>Nilai / pcs</dt><dd>{money(currentComponent.perPcs)}</dd></div>
                <div><dt>Total versi</dt><dd>{money(currentComponent.total)}</dd></div>
                <div><dt>Source type</dt><dd>{currentComponent.sourceType}</dd></div>
                <div><dt>Source ID</dt><dd>{currentComponent.sourceId}</dd></div>
                <div><dt>Tanggal ekonomi</dt><dd>{currentComponent.sourceDate}</dd></div>
              </dl>
              <div className="hpp-basis"><span>DASAR PERHITUNGAN</span><p>{currentComponent.basis}</p></div>
              <div className="hpp-lock-note"><LockKeyhole /><span><strong>Snapshot tidak ditimpa</strong><small>Kalau sumber berubah, backend membuat versi HPP baru yang menunjuk versi ini.</small></span></div>
            </>}
          </aside>
        </section>}

        {activeTab === 'history' && <section className="panel hpp-history-panel">
          <header><div><span>AUDIT TRAIL</span><h2>Perjalanan HPP lot {lot.id}</h2><p>Yang berubah adalah versi current; versi lama tetap utuh.</p></div><ShieldCheck /></header>
          <div className="hpp-history-table">
            <div className="hpp-history-head"><span>Versi</span><span>Keadaan</span><span>HPP / pcs</span><span>Perubahan</span><span>Alasan & waktu</span><span /></div>
            {[...lot.versions].reverse().map((version) => {
              const previous = lot.versions.find((item) => item.no === version.no - 1)
              const delta = previous ? version.perPcs - previous.perPcs : 0
              return <div className="hpp-history-row" key={version.no}>
                <span><b>v{version.no}</b>{version.no === currentVersion.no && <em>CURRENT</em>}</span>
                <span className={`hpp-engine-state ${version.state.toLowerCase()}`}>{stateLabel[version.state]}<small>{version.state}</small></span>
                <strong>{money(version.perPcs)}</strong>
                <strong className={delta > 0 ? 'positive' : delta < 0 ? 'negative' : ''}>{version.no === 1 ? 'Awal' : signedMoney(delta)}</strong>
                <span><b>{version.reason}</b><small>{version.calculatedAt}</small></span>
                <button onClick={() => { setActiveVersionNo(version.no); setActiveTab('composition') }}>Lihat <ArrowRight /></button>
              </div>
            })}
          </div>
          <div className="hpp-history-rule"><LockKeyhole /><p><strong>Golden rule HPP:</strong> koreksi tidak pernah mengedit v1/v2. Backend membuat v berikutnya, mengisi <code>supersedes_id</code>, lalu memindahkan satu-satunya penanda <code>is_current</code>.</p></div>
        </section>}

        {activeTab === 'recost' && <section className="hpp-recost-layout">
          <div className="panel hpp-recost-form">
            <header><div><span>SIMULASI UX · TIDAK MENULIS BACKEND</span><h2>Review rekalkulasi sebelum antre</h2><p>Masukkan nilai sumber baru. Dampaknya harus kelihatan sebelum membuat versi berikutnya.</p></div><GitCompareArrows /></header>
            <div className="hpp-recost-source"><span>Sumber yang berubah</span><strong>Invoice final kain · Sinaran</strong><small>{materialComponent.sourceId} · tanggal ekonomi 27 Agu 2026</small></div>
            <div className="hpp-recost-inputs">
              <label><span>NILAI KAIN SAAT INI / PCS</span><div><b>Rp</b><input value={materialComponent.perPcs.toLocaleString('id-ID')} readOnly /></div></label>
              <ArrowRight />
              <label><span>NILAI BARU / PCS</span><div className="editable"><b>Rp</b><input inputMode="numeric" value={recostDrafts[lot.id] ?? String(materialComponent.perPcs + 750)} onChange={(event) => { setRecostDrafts((current) => ({ ...current, [lot.id]: event.target.value })); setSimulationNotice('') }} /></div></label>
            </div>
            <label className="hpp-recost-reason"><span>ALASAN WAJIB</span><textarea value={reason} onChange={(event) => { setRecostReasons((current) => ({ ...current, [lot.id]: event.target.value })); setSimulationNotice('') }} placeholder="Contoh: harga final kasbon berbeda dari benchmark saat barang datang" /></label>
            <div className="hpp-recost-guard"><AlertTriangle /><p><strong>Bukan edit HPP.</strong> Saat backend disambung, aksi final harus memasukkan antrean recost, menghitung kronologis, lalu membuat v{currentVersion.no + 1}. Tidak boleh menimpa v{currentVersion.no}.</p></div>
          </div>

          <aside className="panel hpp-recost-preview">
            <header><span>PREVIEW DAMPAK</span><strong>v{currentVersion.no} → calon v{currentVersion.no + 1}</strong></header>
            <div className="hpp-before-after"><span><small>HPP AKTIF</small><strong>{money(currentVersion.perPcs)}</strong></span><ArrowRight /><span><small>SETELAH RECOST</small><strong>{money(proposedHpp)}</strong></span></div>
            <div className={`hpp-recost-delta ${proposedDeltaPerPcs < 0 ? 'down' : ''}`}><small>SELISIH</small><strong>{signedMoney(proposedDeltaPerPcs)} / pcs</strong><span>{signedMoney(totalImpact)} untuk {lot.qty} pcs</span></div>
            <div className="hpp-impact-lines">
              <p><span>FG masih di gudang <small>{lot.qty - lot.soldQty} pcs</small></span><strong>{signedMoney(inventoryImpact)}</strong></p>
              <p><span>Sudah terjual / COGS <small>{lot.soldQty} pcs</small></span><strong>{signedMoney(cogsImpact)}</strong></p>
              <p className="total"><span>Total dampak GL</span><strong>{signedMoney(totalImpact)}</strong></p>
            </div>
            <div className="hpp-output-list"><span>JIKA DIPOSTING NANTI</span><p><Check /> HPP version baru <b>ADJUSTED</b></p><p><Check /> Persediaan FG dan COGS dipisahkan</p><p><Check /> Versi lama dan sumber tetap tersimpan</p><p><Check /> Audit reason, user, dan waktu wajib</p></div>
            {simulationNotice && <div className="hpp-simulation-notice"><Check /> {simulationNotice}</div>}
            <button className="hpp-simulate-btn" disabled={!reason.trim() || proposedHpp < 0} onClick={() => setSimulationNotice(`Preview v${currentVersion.no + 1} siap. Belum ada data backend yang berubah.`)}><GitCompareArrows /> Simpan simulasi di layar</button>
            <small className="hpp-backend-lock"><LockKeyhole /> Tombol posting sengaja belum dibuka selama backend V2.6.1 frozen.</small>
          </aside>
        </section>}

        <section className="panel hpp-completeness">
          <header><div><span>STATUS MANUSIA · BUKAN CUMA KODE ENGINE</span><h2>{statusLabel[lot.displayStatus]}</h2><p>{pendingChecks ? `${pendingChecks} pemeriksaan masih perlu dibereskan.` : 'Lengkap berdasarkan data yang tersedia saat ini.'}</p></div><div className={pendingChecks ? 'pending' : 'complete'}>{pendingChecks ? <Clock3 /> : <ShieldCheck />}<strong>{completedChecks}/{lot.checks.length}</strong></div></header>
          <div className="hpp-check-grid">{lot.checks.map((item) => <article className={item.ok ? 'done' : 'open'} key={item.label}><span>{item.ok ? <Check /> : <AlertTriangle />}</span><div><strong>{item.label}</strong><small>{item.note}</small></div></article>)}</div>
          <footer><Info /><p><strong>ACTUAL tidak otomatis final.</strong> Halaman ini mengikuti fungsi kelengkapan backend, jadi biaya aktual tetap bisa berlabel “Belum lengkap” bila proses fisiknya belum beres.</p></footer>
        </section>
      </div>
    </section>
  </>
}

export default HppPage

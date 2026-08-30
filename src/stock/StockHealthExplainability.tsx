import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { ArrowRight, Calculator, Database, Link2, ShieldAlert, X } from 'lucide-react'
import {
  StockCalculationBasis,
  StockHealthStatus,
  type StockHealthResult,
} from './stockHealth'

export type StockLineageLink = {
  label: string
  source: string
  href: string | null
}

const healthLabels: Record<StockHealthStatus, string> = {
  [StockHealthStatus.BELUM_CUKUP_DATA]: 'Belum cukup data',
  [StockHealthStatus.AMAN]: 'Stok aman',
  [StockHealthStatus.RENDAH]: 'Stok rendah',
  [StockHealthStatus.PERLU_PESAN]: 'Perlu pesan',
  [StockHealthStatus.PERLU_PRODUKSI]: 'Perlu produksi',
  [StockHealthStatus.KRITIS]: 'Kritis',
}

const basisLabels: Record<StockCalculationBasis, string> = {
  [StockCalculationBasis.BELUM_DIATUR]: 'Batas belum diatur',
  [StockCalculationBasis.MANUAL]: 'Batas manual',
  [StockCalculationBasis.REKOMENDASI_SISTEM]: 'Rekomendasi sistem',
}

const healthTone: Record<StockHealthStatus, 'neutral' | 'good' | 'warn' | 'danger'> = {
  [StockHealthStatus.BELUM_CUKUP_DATA]: 'neutral',
  [StockHealthStatus.AMAN]: 'good',
  [StockHealthStatus.RENDAH]: 'warn',
  [StockHealthStatus.PERLU_PESAN]: 'danger',
  [StockHealthStatus.PERLU_PRODUKSI]: 'danger',
  [StockHealthStatus.KRITIS]: 'danger',
}

const number = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 2 })

const quantity = (value: number | null, uom: string) => value === null ? 'Belum tersedia' : `${number.format(value)} ${uom}`
const scalar = (value: number | null, suffix: string) => value === null ? 'Belum tersedia' : `${number.format(value)} ${suffix}`

export function getStockHealthLabel(result: StockHealthResult) {
  return healthLabels[result.healthStatus]
}

export function getStockBasisLabel(result: StockHealthResult) {
  return basisLabels[result.basis]
}

export function StockHealthExplainability({
  itemName,
  result,
  lineage,
  compact = false,
}: {
  itemName: string
  result: StockHealthResult
  lineage: StockLineageLink[]
  compact?: boolean
}) {
  const [open, setOpen] = useState(false)
  const close = useCallback(() => setOpen(false), [])
  const dialogId = useId()

  return <>
    <button
      type="button"
      className={`wh-stock-health-badge ${healthTone[result.healthStatus]}${compact ? ' compact' : ''}`}
      aria-haspopup="dialog"
      aria-expanded={open}
      aria-controls={dialogId}
      aria-label={`${getStockHealthLabel(result)}, ${getStockBasisLabel(result)}. Buka dasar perhitungan ${itemName}`}
      onClick={() => setOpen(true)}
    >
      <span>{getStockHealthLabel(result)}</span>
      <small>{getStockBasisLabel(result)}</small>
      <Calculator aria-hidden="true"/>
    </button>
    {open ? <StockCalculationDrawer dialogId={dialogId} itemName={itemName} result={result} lineage={lineage} onClose={close}/> : null}
  </>
}

function StockCalculationDrawer({
  dialogId,
  itemName,
  result,
  lineage,
  onClose,
}: {
  dialogId: string
  itemName: string
  result: StockHealthResult
  lineage: StockLineageLink[]
  onClose: () => void
}) {
  const titleId = `${dialogId}-title`
  const closeRef = useRef<HTMLButtonElement>(null)
  const drawerRef = useRef<HTMLElement>(null)
  const priorFocusRef = useRef<HTMLElement | null>(null)

  useEffect(() => {
    priorFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    closeRef.current?.focus()
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
      if (event.key === 'Tab') {
        const focusable = drawerRef.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href]')
        if (!focusable || focusable.length === 0) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault()
          last.focus()
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault()
          first.focus()
        }
      }
    }
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('keydown', closeOnEscape)
      priorFocusRef.current?.focus()
    }
  }, [onClose])

  const incomplete = result.healthStatus === StockHealthStatus.BELUM_CUKUP_DATA
  const resultSummary = incomplete
    ? 'Belum ada dasar valid untuk menilai stok. Sistem tidak membuat angka rekomendasi.'
    : (result.brokenRequiredSizes?.length ?? 0) > 0
      ? `Range size putus pada size ${result.brokenRequiredSizes?.join(', ')}. Qty produksi per-size belum dapat dihitung tanpa target size yang sah.`
    : result.recommendedQty === 0
      ? 'Projected stock memenuhi target yang berlaku. Tidak ada rekomendasi tambahan.'
      : result.recommendedQty === null
        ? 'Rekomendasi qty belum dapat dihitung dari data yang tersedia.'
        : `Projected stock berada di bawah target. Rekomendasi tambahan ${quantity(result.recommendedQty, result.uom)}.`

  return <div className="wh-stock-drawer-backdrop" role="presentation" onMouseDown={onClose}>
    <aside
      ref={drawerRef}
      id={dialogId}
      className="wh-stock-drawer"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onMouseDown={(event) => event.stopPropagation()}
    >
      <header>
        <div><span>DASAR PERHITUNGAN STOK</span><h2 id={titleId}>{itemName}</h2><p>Angka, sumber, dan formula yang membentuk status stok.</p></div>
        <button ref={closeRef} type="button" aria-label="Tutup dasar perhitungan" onClick={onClose}><X/></button>
      </header>

      {result.dataState === 'SIMULATED' ? <div className="wh-stock-fixture-warning" role="note">
        <ShieldAlert/><div><strong>Data simulasi frontend — belum tersambung backend</strong><small>Jangan gunakan angka di drawer ini untuk membuat PO atau keputusan produksi.</small></div>
      </div> : null}

      <section className="wh-stock-drawer-status" aria-label="Status dan sumber dasar">
        <span className={`wh-stock-pill ${healthTone[result.healthStatus]}`}>{getStockHealthLabel(result)}</span>
        <span className="wh-stock-pill basis">{getStockBasisLabel(result)}</span>
        <small>Confidence: {result.confidence.replaceAll('_', ' ').toLowerCase()}</small>
      </section>

      <section className="wh-stock-calc-grid" aria-label="Rincian angka perhitungan">
        <CalculationRow label="Stok fisik" value={quantity(result.physicalStock, result.uom)} source="Ledger stok posted"/>
        <CalculationRow label="Reserved" value={result.reservedStock === null ? 'Belum tersedia' : `−${quantity(result.reservedStock, result.uom)}`} source="Invoice/reservation sah"/>
        <CalculationRow label="Available stock" value={quantity(result.availableStock, result.uom)} formula="physical − reserved"/>
        <CalculationRow label="Incoming terkonfirmasi" value={result.confirmedIncoming === null ? 'Belum tersedia' : `+${quantity(result.confirmedIncoming, result.uom)}`} source="PO atau FG accepted; pre-QC WIP dikecualikan"/>
        <CalculationRow label="Projected stock" value={quantity(result.projectedStock, result.uom)} formula="available + confirmed incoming"/>
        <CalculationRow label="Rata-rata kebutuhan" value={scalar(result.averageDailyDemand, `${result.uom}/hari`)} source="Hanya hari stok tersedia"/>
        <CalculationRow label="Periode data" value={scalar(result.historyDays, 'hari')} source={`Minimum sampel ${result.minimumSampleDays} hari`}/>
        <CalculationRow label="Hari tersedia" value={scalar(result.availableDays, 'hari')} source="Stock availability calendar"/>
        <CalculationRow label="Hari stockout" value={scalar(result.stockoutDays, 'hari')} source="Tidak masuk denominator demand"/>
        <CalculationRow label="Range size putus" value={result.brokenRequiredSizes === null ? 'Belum tersedia' : result.brokenRequiredSizes.length > 0 ? result.brokenRequiredSizes.join(', ') : result.dataState === 'SIMULATED' ? 'Tidak ada pada fixture' : 'Tidak ada'} source="Setiap size wajib dinilai sendiri"/>
        <CalculationRow label="Lead time" value={scalar(result.leadTimeDays, 'hari')} source="Supplier/produksi aktual"/>
        <CalculationRow label="Kebutuhan lead time" value={quantity(result.leadTimeDemand, result.uom)} formula="average daily demand × lead time"/>
        <CalculationRow label="Safety stock" value={quantity(result.safetyStock, result.uom)} source="Buffer kebijakan berlaku"/>
        <CalculationRow label="Reorder point" value={quantity(result.reorderPoint, result.uom)} formula="lead-time demand + safety stock"/>
        <CalculationRow label="Target stock" value={quantity(result.targetStock, result.uom)} source="Versi kebijakan efektif"/>
        <CalculationRow label="Recommended qty" value={quantity(result.recommendedQty, result.uom)} formula="max(0, target − projected)" emphasis/>
      </section>

      <section className="wh-stock-formula-note">
        <Calculator/><div><span>KESIMPULAN SISTEM</span><strong>{resultSummary}</strong><small>Formula {result.formulaVersion} · as-of {result.asOf ?? 'belum tersedia'} · kalkulasi {result.calculatedAt ?? 'belum dijalankan'}</small></div>
      </section>

      <section className="wh-stock-lineage">
        <header><div><Database/><span><strong>Sumber & jejak angka</strong><small>{result.sourceSystem}</small></span></div></header>
        <div>{lineage.map((link) => link.href
          ? <a key={`${link.label}-${link.source}`} href={link.href} onClick={onClose}><Link2/><span><strong>{link.label}</strong><small>{link.source}</small></span><ArrowRight/></a>
          : <div key={`${link.label}-${link.source}`} className="wh-stock-lineage-unavailable" aria-disabled="true"><Link2/><span><strong>{link.label}</strong><small>{link.source} · belum tersambung</small></span></div>)}</div>
      </section>

      {result.missingFields.length > 0 ? <div className="wh-stock-missing"><strong>Belum bisa dihitung karena:</strong> {result.missingFields.join(', ')}.</div> : null}
      {result.validationIssues.length > 0 ? <div className="wh-stock-missing danger"><strong>Data tidak konsisten:</strong> {result.validationIssues.join(', ')}.</div> : null}
      <footer><ShieldAlert/><span>Rekomendasi hanya informasi. Sistem tidak otomatis membuat PO atau perintah produksi.</span></footer>
    </aside>
  </div>
}

function CalculationRow({ label, value, source, formula, emphasis = false }: { label: string; value: string; source?: string; formula?: string; emphasis?: boolean }) {
  return <div className={emphasis ? 'emphasis' : ''}><span><small>{label}</small>{source ? <em>{source}</em> : null}{formula ? <code>{formula}</code> : null}</span><strong>{value}</strong></div>
}

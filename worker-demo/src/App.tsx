import {
  PAGE_PERMISSION_BY_ID,
  SENSITIVE_ACTION_PERMISSION,
  firstAllowedPageId,
  hasPermission,
  isNavLabelAllowed,
  isPageAllowed,
} from './auth/accessCatalog'
import { useAuth } from './auth/AuthProvider'
import type { BsReworkWorkspace } from './BsReworkPage'
import { Icon } from './components/AppIcon'
import { RuntimeBadge, RuntimeEnvironmentCard, RuntimeIdentity } from './components/RuntimeIdentity'
import type { FinanceReportTab } from './ConnectedFinanceReportPage'
import { CuttingRollPage } from './demo/CuttingRollPage'
import {
  buildQcSeeds,
  laborBomComponents,
  laundryDeliverySeeds,
  laundryOutstandingSizes,
  laundryReadyFromSewingBatch,
  laundryReadySeeds,
} from './demo/laundryModel'
import type { LaundryDelivery, LaundryPrefill, LaundryReadyBatch } from './demo/laundryModel'
import { LaundryPage } from './demo/LaundryPage'
import { MandorWipPage } from './demo/MandorWipPage'
import { ProcurementPage } from './demo/ProcurementPage'
import type { QtyTuple } from './demo/productionModel'
import { sewingWipSeeds } from './demo/sewingModel'
import { SewingWipPage } from './demo/SewingWipPage'
import { chronologicalMovements } from './demo/stockModel'
import { Movements, StockCard } from './demo/StockPages'
import { regularFgNotaCardId } from './fgNota'
import type { ReadyFgNotaCard, RegularFgNotaSnapshot } from './fgNota'
import type { FinanceView } from './FinancePages'
import type { BusinessMasterView } from './MasterDataPages'
import type { MaterialMasterView } from './MaterialMasterPages'
import MobilePrimaryNavigation from './MobilePrimaryNavigation'
import type { OperationsAdminView } from './OperationsAdminPages'
import { OwnerDashboard } from './OwnerDashboard'
import type { QcFinalResult } from './QcFinalPage'
import { initialReminders } from './reminders'
import type { ReminderItem } from './reminders'
import type { SalesView } from './SalesPages'
import { SCREEN_ACTIVATION, connectedSections, isNavLabelHidden, isScreenHidden } from './screenActivation'
import { TransactionSourceProvider } from './TransactionSourceNavigation'
import type { WarehouseView } from './WarehousePages'
import { ShieldCheck } from 'lucide-react'
import { Suspense, lazy, useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { KeyboardEvent as ReactKeyboardEvent } from 'react'

import { applyUxTampilan, readUxTampilan, saveUxTampilan, type UxTampilan } from './uxTampilan'
import { UxTampilanToggle } from './UxTampilanToggle'
import { StageLots } from './demo/planner/StageLots'
import { SkuRangePage } from './demo/SkuRangePage'
import { cuttingFormAt, productionForms } from './demoCuttingRoutes'

export { UnassignedRollCard } from './demo/CuttingRollPage'
export { MandorWipPage } from './demo/MandorWipPage'
export { SewingWipPage } from './demo/SewingWipPage'
export { MovementBookRow } from './demo/StockPages'

const SalesPages = lazy(() => import('./SalesPages'))
const ConnectedSalesPage = lazy(() => import('./ConnectedSalesPage'))
const ConnectedFinanceReportPage = lazy(() => import('./ConnectedFinanceReportPage'))
const ConnectedFinanceOverviewPage = lazy(() => import('./ConnectedFinanceOverviewPage'))
const ConnectedReceivablesPage = lazy(() => import('./ConnectedReceivablesPage'))
const ConnectedCustomerHistoryPage = lazy(() => import('./ConnectedCustomerHistoryPage'))
const ConnectedJournalPage = lazy(() => import('./ConnectedJournalPage'))
const ConnectedCashLedgerPage = lazy(() => import('./ConnectedCashLedgerPage'))
const FinancePages = lazy(() => import('./FinancePages'))
const ConnectedPayrollPage = lazy(() => import('./ConnectedPayrollPage'))
const ConnectedAttendancePage = lazy(() => import('./ConnectedAttendancePage'))
const ConnectedRemindersPage = lazy(() => import('./ConnectedRemindersPage'))
const ConnectedSupplierCreditPage = lazy(() => import('./ConnectedSupplierCreditPage'))
const ConnectedSkuHppPage = lazy(() => import('./ConnectedSkuHppPage'))
const HppPage = lazy(() => import('./HppPage'))
const QcFinalPage = lazy(() => import('./QcFinalPage'))
const BsReworkPage = lazy(() => import('./BsReworkPage'))
const ConnectedStockAdjustmentPage = lazy(() => import('./ConnectedStockAdjustmentPage'))
const ConnectedMaterialsPage = lazy(() => import('./ConnectedMaterialsPage'))
const WarehousePages = lazy(() => import('./WarehousePages'))
const ContractorIssuePage = lazy(() => import('./ContractorIssuePage'))
const ConnectedAccessoryWorkspacePage = lazy(() => import('./ConnectedAccessoryWorkspacePage'))
const ConnectedProductConversionPage = lazy(() => import('./ConnectedProductConversionPage'))
const ConnectedAccessoryServicePage = lazy(() => import('./ConnectedAccessoryServicePage'))
const MaterialMasterPages = lazy(() => import('./MaterialMasterPages'))
const ConnectedSkuMasterPage = lazy(() => import('./ConnectedSkuMasterPage'))
const MasterDataPages = lazy(() => import('./MasterDataPages'))
const ConnectedMasterPage = lazy(() => import('./ConnectedMasterPage'))
const OperationsAdminPages = lazy(() => import('./OperationsAdminPages'))
const ConnectedAuditTrailPage = lazy(() => import('./ConnectedAuditTrailPage'))
const FgNotaPage = lazy(() => import('./FgNotaPage'))
const AccessControlPage = lazy(() => import('./AccessControlPage'))
const ConnectedInitialImportPage = lazy(() => import('./ConnectedInitialImportPage'))
const ConnectedErpSettingsPage = lazy(() => import('./ConnectedErpSettingsPage'))
const ConnectedPocketFabricPage = lazy(() => import('./ConnectedPocketFabricPage'))
const ConnectedProcurementPage = lazy(() => import('./ConnectedProcurementPage'))
const PatternPage = lazy(() => import('./PatternPage'))
const ConnectedCuttingPage = lazy(() => import('./ConnectedCuttingPage'))
const ConnectedPickupPage = lazy(() => import('./ConnectedPickupPage'))
const ConnectedWipStatusPage = lazy(() => import('./ConnectedWipStatusPage'))
const ConnectedBsResolutionPage = lazy(() => import('./ConnectedBsResolutionPage'))
const ConnectedLaundryPage = lazy(() => import('./ConnectedLaundryPage'))
const ConnectedQcFinalPage = lazy(() => import('./ConnectedQcFinalPage'))
const ConnectedFgBookPage = lazy(() => import('./ConnectedFgBookPage'))
const ConnectedFgStockPage = lazy(() => import('./ConnectedFgStockPage'))
const ConnectedWarehouseSummaryPage = lazy(() => import('./ConnectedWarehouseSummaryPage'))
const ConnectedFgHandoffBoundary = lazy(() => import('./ConnectedFgHandoffBoundary'))
const MigrationWorkbook = lazy(() => import('./MigrationWorkbook'))
const Cp7Shell = lazy(() => import('./cp7/Cp7Shell'))

type Page = 'dashboard' | 'stock-card' | 'movements-vivo' | 'movements-widie' | 'procurement' | 'cutting-roll' | 'mandor-wip' | 'contractor-issue' | 'sewing-wip' | 'qc' | 'fg-handoff' | 'bs-rework' | 'laundry' | 'hpp' | 'master-pattern' | 'admin-access' | 'admin-import' | 'pocket-fabric' | SalesView | FinanceView | WarehouseView | MaterialMasterView | BusinessMasterView | OperationsAdminView | 'placeholder'

type NavSection = 'Produksi' | 'Gudang' | 'Penjualan' | 'Keuangan' | 'Master Data'

type NotaFocus = { kind: 'REGULAR' | 'REPAIR'; id: string }

type NotaOrigin = 'MENU' | 'QC' | 'BS_REWORK'

const nav: Record<NavSection, string[]> = {
  Produksi: ['Buat Potongan', 'Bagi Potongan', 'WIP & Sewing', 'Laundry', 'QC & Final SKU', 'Susun Nota FG', 'Barang BS & Rework'],
  Gudang: ['Ringkasan Gudang', 'Pembelian & Penerimaan', 'Bahan & Roll', 'Kain kantong', 'Aksesori', 'Ringkasan Barang Jadi', 'Mutasi Barang Jadi · Vivo', 'Mutasi Barang Jadi · Widie', 'Kartu Stok FG', 'Stock Adjustment', 'Ganti Merek'],
  Penjualan: ['Penjualan & Invoice', 'Semua Invoice', 'Retur Penjualan', 'Pembayaran Pelanggan', 'Riwayat Pelanggan'],
  Keuangan: ['Ringkasan Keuangan', 'Kas & Bank', 'Hutang Supplier & Vendor', 'Piutang Pelanggan', 'Payroll & Kasbon', 'Absensi & Rate Harian', 'Nota Ambil Aksesori', 'HPP & Rekalkulasi', 'Jurnal & Transaksi Lain', 'Laporan & Tutup Buku'],
  'Master Data': ['Kain & Benchmark', 'Aksesori & Harga Mandor', 'Produk & SKU', 'Pelanggan', 'Supplier & Vendor', 'Mandor', 'Gudang & Lokasi', 'Pola'],
}

const salesPageByLabel: Partial<Record<string, SalesView>> = {
  'Penjualan & Invoice': 'sales-invoice',
  'Semua Invoice': 'sales-allocation',
  'Retur Penjualan': 'sales-returns',
  'Pembayaran Pelanggan': 'sales-payments',
  'Riwayat Pelanggan': 'sales-history',
}

const financePageByLabel: Partial<Record<string, FinanceView>> = {
  'Ringkasan Keuangan': 'finance-overview',
  'Kas & Bank': 'finance-cash',
  'Hutang Supplier & Vendor': 'finance-ap',
  'Piutang Pelanggan': 'finance-ar',
  'Payroll & Kasbon': 'finance-payroll',
  'Jurnal & Transaksi Lain': 'finance-journal',
  'Laporan & Tutup Buku': 'finance-reports',
}

const businessMasterPageByLabel: Partial<Record<string, BusinessMasterView>> = {
  'Produk & SKU':'master-products',
  'Pelanggan':'master-customers',
  'Supplier & Vendor':'master-partners',
  'Mandor':'master-workforce',
  'Gudang & Lokasi':'master-locations',
}

const operationsPageByLabel: Record<string, OperationsAdminView> = {
  'Absensi & Rate Harian':'operations-attendance',
  'Reminder':'admin-reminders',
  'Pengaturan ERP':'admin-settings',
  'Audit Trail':'admin-audit',
}

const adminNav = ['Reminder','Pengguna & Hak Akses','Pengaturan ERP','Impor data awal','Audit Trail']

const salesViews: SalesView[] = ['sales-invoice','sales-allocation','sales-returns','sales-payments','sales-history']

const financeViews: FinanceView[] = ['finance-overview','finance-cash','finance-ap','finance-ar','finance-payroll','finance-journal','finance-reports']

const isSalesView = (page: Page): page is SalesView => salesViews.includes(page as SalesView)

const isFinanceView = (page: Page): page is FinanceView => financeViews.includes(page as FinanceView)

const operationsViews: OperationsAdminView[] = ['operations-attendance','admin-reminders','admin-settings','admin-audit']

const isOperationsView = (page: Page): page is OperationsAdminView => operationsViews.includes(page as OperationsAdminView)

// Owner D16-5: "Tutup Periode" is now the "Tutup Buku" tab of "Laporan & Tutup Buku"; an old link to it opens that tab.
const redirectedPages: Partial<Record<Page, { page: Page; reportTab: FinanceReportTab }>> = { 'admin-period-close': { page: 'finance-reports', reportTab: 'PERIOD' } }

const focusKeyboardControl = (element: HTMLElement) => {
  element.focus()
  if (element instanceof HTMLInputElement && !['date','datetime-local','time'].includes(element.type)) element.select()
}

function handleErgonomicKeyboard(event: ReactKeyboardEvent<HTMLDivElement>) {
  if (event.defaultPrevented || event.nativeEvent.isComposing || event.ctrlKey || event.metaKey || event.altKey) return
  const target = event.target
  if (!(target instanceof HTMLInputElement) || target.disabled || target.readOnly || ['checkbox','radio','file','color'].includes(target.type)) return
  if (target.dataset.cuttingRow !== undefined) return

  const grid = target.closest<HTMLElement>('[data-keyboard-grid]')
  const row = Number(target.dataset.gridRow)
  const col = Number(target.dataset.gridCol)
  const gridKey = ['Enter','ArrowDown','ArrowUp','ArrowLeft','ArrowRight'].includes(event.key)
  if (grid && gridKey && Number.isFinite(row) && Number.isFinite(col)) {
    const cells = Array.from(grid.querySelectorAll<HTMLInputElement>('input[data-grid-row][data-grid-col]:not(:disabled):not([readonly])'))
    const parsed = cells.map((cell) => ({ cell, row: Number(cell.dataset.gridRow), col: Number(cell.dataset.gridCol) }))
    let candidate: HTMLInputElement | undefined
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      const direction = event.key === 'ArrowLeft' ? -1 : 1
      candidate = parsed.find((item) => item.row === row && item.col === col + direction)?.cell
    } else {
      const direction = event.key === 'ArrowUp' || (event.key === 'Enter' && event.shiftKey) ? -1 : 1
      const sameColumn = parsed.filter((item) => item.col === col && (direction > 0 ? item.row > row : item.row < row)).sort((a,b) => direction > 0 ? a.row-b.row : b.row-a.row)
      candidate = sameColumn[0]?.cell
    }
    if (candidate) {
      event.preventDefault()
      focusKeyboardControl(candidate)
      return
    }
    if (event.key !== 'Enter') return
  }

  if (event.key !== 'Enter') return
  const scope = target.closest<HTMLElement>('[data-keyboard-scope]')
  if (!scope) return
  const controls = Array.from(scope.querySelectorAll<HTMLElement>('input:not(:disabled):not([readonly]):not([type="checkbox"]):not([type="radio"]), select:not(:disabled)'))
    .filter((control) => control.offsetParent !== null)
  const current = controls.indexOf(target)
  const next = controls[current + (event.shiftKey ? -1 : 1)]
  if (!next) return
  event.preventDefault()
  focusKeyboardControl(next)
}

function App() {
  const { runtime } = useAuth()
  if (globalThis.location.pathname.replace(/\/+$/, '') === '/cp7-preview' || globalThis.location.pathname.startsWith('/analisis/')) {
    return <Suspense fallback={<WorkspaceFallback label="Pratinjau CP7" />}><Cp7Shell runtimeMode={runtime.mode} /></Suspense>
  }
  return <ErpApp />
}

function ErpApp() {
  const { runtime, identity } = useAuth()
  const accessBundle = identity.status === 'AUTHORIZED' ? identity : null
  const demoAccess = identity.status === 'DEMO'
  // Owner D15-2: in the Enteng build a menu without a connected screen is hidden (src/screenActivation.ts).
  const canSeeNavLabel = (label: string) => (demoAccess || isNavLabelAllowed(accessBundle, label)) && !isNavLabelHidden(runtime.mode, label)
  const [page, setRoutedPage] = useState<Page>(() => demoAccess
    ? (cuttingFormAt(globalThis.location.pathname) ?? (['/migrasi', '/migrasi/'].includes(globalThis.location.pathname) ? 'admin-import' : 'dashboard'))
    : (firstAllowedPageId(accessBundle, Object.keys(PAGE_PERMISSION_BY_ID).filter(id => !isScreenHidden(runtime.mode, id) && !(id in redirectedPages))) as Page | null) ?? 'dashboard')
  const [uxTampilan, setUxTampilan] = useState<UxTampilan>(readUxTampilan)
  useLayoutEffect(() => { applyUxTampilan(uxTampilan) }, [uxTampilan])
  function chooseUxTampilan(value: UxTampilan) {
    saveUxTampilan(value)
    setUxTampilan(value)
  }
  const [reportTab, setReportTab] = useState<FinanceReportTab>('REPORT')
  const setPageState = (requested: Page) => {
    const redirect = redirectedPages[requested]
    setReportTab(redirect?.reportTab ?? 'REPORT')
    setRoutedPage(redirect?.page ?? requested)
  }
  const [sourceEpoch,setSourceEpoch]=useState(0)
  const setPage=(next:Page)=>{if(next!==page)setInvoiceSource(null);setSourceEpoch(value=>value+1);setPageState(next)}
  const [invoiceSource,setInvoiceSource] = useState<{saleId:string;scope:string}|null>(null)
  const invoiceSourceScope=runtime.mode!=='DEMO_SIMULATION'&&identity.status==='AUTHORIZED'?`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`:null
  const [expanded, setExpanded] = useState<NavSection | null>(() => demoAccess && cuttingFormAt(window.location.pathname) ? (window.location.pathname.startsWith('/gudang/')?'Gudang':window.location.pathname.startsWith('/master/')?'Master Data':'Produksi') : null)
  useEffect(() => {
    if (!demoAccess) return
    const openedForm = cuttingFormAt(window.location.pathname)
    if(openedForm===page)return
    if(page in productionForms) {
      window.history.replaceState(window.history.state,'',productionForms[page as keyof typeof productionForms].path)
    } else if(openedForm) {
      window.history.replaceState(window.history.state,'',page==='admin-import'?'/migrasi/':'/')
    }
  }, [demoAccess, page])
  const [menuSearch, setMenuSearch] = useState<string | null>(null)
  const searchable = [...Object.values(nav).flat(), ...adminNav].filter(canSeeNavLabel)
  const [analysisExpanded, setAnalysisExpanded] = useState(false)
  const [adminExpanded,setAdminExpanded] = useState(false)
  const [mobileNav, setMobileNav] = useState(false)
  const mobileMenuRef = useRef<HTMLElement>(null)
  useEffect(() => {
    if (!mobileNav || !window.matchMedia('(max-width: 860px)').matches) return
    const menu = mobileMenuRef.current, previous = document.activeElement
    if (!menu) return
    const controls = () => Array.from(menu.querySelectorAll<HTMLElement>('button:not(:disabled), a[href]'))
      .filter(element => element.getClientRects().length > 0)
    controls()[0]?.focus()
    const keydown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); setMobileNav(false) }
      if (event.key !== 'Tab') return
      const items = controls(), first = items[0], last = items[items.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus() }
    }
    menu.addEventListener('keydown', keydown)
    const media = window.matchMedia('(max-width: 860px)')
    const resize = () => { if (!media.matches) setMobileNav(false) }
    media.addEventListener('change', resize)
    return () => {
      menu.removeEventListener('keydown', keydown)
      media.removeEventListener('change', resize)
      if (previous instanceof HTMLElement && previous.isConnected) previous.focus()
    }
  }, [mobileNav])
  const [movements, setMovements] = useState(chronologicalMovements)
  const [vivoBookBrands, setVivoBookBrands] = useState<string[]>(['Vivo'])
  const [widieBookBrands, setWidieBookBrands] = useState<string[]>(['Widie'])
  const [mandorBatchNotes,setMandorBatchNotes] = useState<string[]>([
    'Warna navy · stik pinggang 2 jalur',
    'Warna maroon · obras rapat',
    'Warna hitam · cek sambungan samping',
  ])
  const [laundryPrefill,setLaundryPrefill] = useState<LaundryPrefill|null>(null)
  const [laundryReadyBatches,setLaundryReadyBatches] = useState<LaundryReadyBatch[]>(laundryReadySeeds)
  const [laundryDeliveries,setLaundryDeliveries] = useState<LaundryDelivery[]>(laundryDeliverySeeds)
  const [laundryDrafts,setLaundryDrafts] = useState<Record<string,string>>({})
  const [wipReverseNotice,setWipReverseNotice] = useState<string|null>(null)
  const [qcSeedId,setQcSeedId] = useState('POT-260826-041::041-02')
  const [qcResult,setQcResult] = useState<QcFinalResult|null>(null)
  const [finalizedQcResults,setFinalizedQcResults] = useState<QcFinalResult[]>([])
  const [bsPrefill,setBsPrefill] = useState<QcFinalResult|null>(null)
  const [bsBackPage,setBsBackPage] = useState<'sewing-wip'|'fg-handoff'>('sewing-wip')
  const [notaFocus,setNotaFocus] = useState<NotaFocus|null>(null)
  const [notaOrigin,setNotaOrigin] = useState<NotaOrigin>('MENU')
  const [readyFgNotaCards,setReadyFgNotaCards] = useState<ReadyFgNotaCard[]>([])
  const [postedFgCardIds,setPostedFgCardIds] = useState<string[]>([])
  const [regularFgNotaSnapshots,setRegularFgNotaSnapshots] = useState<Record<string,RegularFgNotaSnapshot>>({})
  const [bsWorkspace,setBsWorkspace] = useState<BsReworkWorkspace|null>(null)
  const [reminders,setReminders] = useState<ReminderItem[]>(()=>initialReminders.map((item)=>({...item})))

  useEffect(() => {
    if (demoAccess || !accessBundle || isPageAllowed(accessBundle, page)) return
    const nextPage = firstAllowedPageId(accessBundle)
    if (nextPage && nextPage !== page) setPage(nextPage as Page)
  }, [accessBundle, demoAccess, page])

  const rememberFgNotaCard = (card: ReadyFgNotaCard) => {
    setReadyFgNotaCards((current) => current.some((item) => item.id === card.id) ? current : [card, ...current])
  }
  const rememberQcNotaSnapshot = (result: QcFinalResult) => {
    const cardId=regularFgNotaCardId(result)
    const fullRate=laborBomComponents.reduce((sum,component)=>sum+component.rate,0)
    const bsTotal=result.postedBsBySize.reduce((sum,value)=>sum+value,0)
    const stuckTotal=result.stuckBySize.reduce((sum,value)=>sum+value,0)
    const incompleteComponents=laborBomComponents.filter((component)=>['finishing-detail','centang','lipat'].includes(component.id)).map(({id,name,rate})=>({id,name,rate}))
    const bsComponents=bsTotal>0?incompleteComponents:[]
    const stuckComponents=stuckTotal>0?incompleteComponents:[]
    setRegularFgNotaSnapshots((current)=>current[cardId]?current:{...current,[cardId]:{cardId,fullRate,sewingRate:14_050,commissionRate:1_800,bomRate:Math.max(0,fullRate-15_850),bsComponents,stuckComponents}})
  }

  useEffect(()=>{
    window.scrollTo({top:0,left:0,behavior:'auto'})
  },[page])

  const title = page === 'dashboard' ? 'Ringkasan bisnis'
    : page === 'sales-invoice' ? 'Penjualan & Invoice'
    : page === 'sales-allocation' ? 'Semua Invoice'
    : page === 'sales-returns' ? 'Retur Penjualan'
    : page === 'sales-payments' ? 'Pembayaran Pelanggan'
    : page === 'sales-history' ? 'Riwayat Pelanggan'
    : page === 'finance-overview' ? 'Ringkasan Keuangan'
    : page === 'finance-cash' ? 'Kas & Bank'
    : page === 'finance-ap' ? 'Hutang Supplier & Vendor'
    : page === 'finance-ar' ? 'Piutang Pelanggan'
    : page === 'finance-payroll' ? 'Payroll & Kasbon'
    : page === 'operations-attendance' ? 'Absensi & Rate Harian'
    : page === 'finance-journal' ? 'Jurnal & Transaksi Lain'
    : page === 'finance-reports' ? 'Laporan & Tutup Buku'
    : page === 'stock-card' ? 'Kartu Stok FG'
    : page === 'movements-vivo' ? 'Mutasi Barang Jadi · Vivo'
    : page === 'movements-widie' ? 'Mutasi Barang Jadi · Widie'
    : page === 'procurement' ? 'Pembelian & Penerimaan'
    : page === 'cutting-roll' ? 'Buat Potongan'
    : page === 'mandor-wip' ? 'Bagi Potongan'
    : page === 'contractor-issue' ? 'Nota Ambil Aksesori'
    : page === 'sewing-wip' ? 'WIP & Sewing'
    : page === 'qc' ? 'QC & Final SKU'
    : page === 'fg-handoff' ? 'Susun Nota FG'
    : page === 'bs-rework' ? 'Barang BS & Rework'
    : page === 'laundry' ? 'Laundry'
    : page === 'hpp' ? 'HPP & Rekalkulasi'
    : page === 'warehouse-dashboard' ? 'Ringkasan Gudang'
    : page === 'pocket-fabric' ? 'Kain kantong'
    : page === 'materials-rolls' ? 'Bahan & Roll'
    : page === 'accessories' ? 'Aksesori'
    : page === 'fg-summary' ? 'Ringkasan Barang Jadi'
    : page === 'stock-adjustment' ? 'Stock Adjustment'
    : page === 'brand-conversion' ? 'Ganti Merek'
    : page === 'master-fabric' ? 'Kain & Benchmark'
    : page === 'master-accessory' ? 'Aksesori & Harga Mandor'
    : page === 'master-products' ? 'Produk & SKU'
    : page === 'master-customers' ? 'Pelanggan'
    : page === 'master-partners' ? 'Supplier & Vendor'
    : page === 'master-workforce' ? 'Mandor'
    : page === 'master-locations' ? 'Gudang & Lokasi'
    : page === 'master-pattern' ? 'Pola'
    : page === 'admin-reminders' ? 'Reminder'
    : page === 'admin-access' ? 'Pengguna & Hak Akses'
    : page === 'admin-import' ? 'Impor data awal'
    : page === 'admin-settings' ? 'Pengaturan ERP'
    : page === 'admin-audit' ? 'Audit Trail'
    : 'Modul ERP'

  const chooseSubmenu = (label: string) => {
    const salesTarget=salesPageByLabel[label]
    if(salesTarget!=='sales-invoice'||page!=='sales-invoice')setInvoiceSource(null)
    const financeTarget=financePageByLabel[label]
    const masterTarget=businessMasterPageByLabel[label]
    const operationsTarget=operationsPageByLabel[label]
    if (salesTarget) setPage(salesTarget)
    else if (financeTarget) setPage(financeTarget)
    else if (masterTarget) setPage(masterTarget)
    else if (operationsTarget) setPage(operationsTarget)
    else if (label === 'Kartu Stok FG') setPage('stock-card')
    else if (label === 'Mutasi Barang Jadi · Vivo') setPage('movements-vivo')
    else if (label === 'Mutasi Barang Jadi · Widie') setPage('movements-widie')
    else if (label === 'Pembelian & Penerimaan') setPage('procurement')
    else if (label === 'Ringkasan Gudang') setPage('warehouse-dashboard')
    else if (label === 'Kain kantong') setPage('pocket-fabric')
    else if (label === 'Bahan & Roll') setPage('materials-rolls')
    else if (label === 'Aksesori') setPage('accessories')
    else if (label === 'Ringkasan Barang Jadi') setPage('fg-summary')
    else if (label === 'Stock Adjustment') setPage('stock-adjustment')
    else if (label === 'Ganti Merek') setPage('brand-conversion')
    else if (label === 'Buat Potongan') setPage('cutting-roll')
    else if (label === 'Bagi Potongan') setPage('mandor-wip')
    else if (label === 'Nota Ambil Aksesori') setPage('contractor-issue')
    else if (label === 'WIP & Sewing') setPage('sewing-wip')
    else if (label === 'Laundry') { setLaundryPrefill(null); setPage('laundry') }
    else if (label === 'QC & Final SKU') {
      setPage('qc')
    }
    else if (label === 'Susun Nota FG') { setQcResult(null); setNotaFocus(null); setNotaOrigin('MENU'); setPage('fg-handoff') }
    else if (label === 'Barang BS & Rework') { setBsPrefill(null); setBsBackPage('sewing-wip'); setPage('bs-rework') }
    else if (label === 'HPP & Rekalkulasi') setPage('hpp')
    else if (label === 'Kain & Benchmark') setPage('master-fabric')
    else if (label === 'Aksesori & Harga Mandor') setPage('master-accessory')
    else if (label === 'Pola') setPage('master-pattern')
    else if (label === 'Pengguna & Hak Akses') setPage('admin-access')
    else if (label === 'Impor data awal') setPage('admin-import')
    else setPage('placeholder')
    setMobileNav(false)
  }

  const mobileDestinations = [
    { id: 'dashboard', label: 'Beranda', navLabel: 'Dashboard', icon: <Icon name="dashboard"/> },
    { id: 'sales-invoice', label: 'Penjualan', navLabel: 'Penjualan & Invoice', icon: <Icon name="Penjualan"/> },
    { id: 'fg-summary', label: 'Stok FG', navLabel: 'Ringkasan Barang Jadi', icon: <Icon name="stock"/> },
    { id: 'finance-payroll', label: 'Payroll', navLabel: 'Payroll & Kasbon', icon: <Icon name="Keuangan"/> },
  ].filter(item => canSeeNavLabel(item.navLabel) && (demoAccess || isPageAllowed(accessBundle, item.id)) && !isScreenHidden(runtime.mode, item.id))

  return <TransactionSourceProvider scope={invoiceSourceScope} epoch={sourceEpoch} onNavigate={route=>{if(!accessBundle||!isPageAllowed(accessBundle,route))throw Error('Hak membuka transaksi asal belum diberikan.');setInvoiceSource(null);setPageState(route as Page);setMobileNav(false)}}><div className="app-shell">
    <aside ref={mobileMenuRef} className={`sidebar ${mobileNav ? 'sidebar-open' : ''}`}>
      <div className="brand-row"><div className="brand-mark"><Icon name="brand" /></div><div><strong>ATELIER</strong><span>GARMENT ERP</span></div><button className="nav-close" aria-label="Tutup menu" onClick={() => setMobileNav(false)}>×</button></div>
      <div className="nav-caption">MENU UTAMA</div>
      {canSeeNavLabel('Dashboard') && <button className={`nav-main ${page === 'dashboard' ? 'active' : ''}`} onClick={() => { setPage('dashboard'); setExpanded(null); setAdminExpanded(false); setMobileNav(false) }}><Icon name="dashboard" /><span>Dashboard</span></button>}
      {(Object.keys(nav) as NavSection[]).filter((section) => nav[section].some(canSeeNavLabel)).map((section) => <div className="nav-section" key={section}>
        <button className={`nav-main ${expanded === section ? 'active' : ''}`} onClick={() => {setExpanded(expanded === section ? null : section);setAdminExpanded(false)}}><Icon name={section} /><span>{section}</span><span className="chevron">{expanded === section ? '⌄' : '›'}</span></button>
        {expanded === section && <div className="submenu">{nav[section].filter(canSeeNavLabel).map((item) => {
          const salesTarget=salesPageByLabel[item]
          const financeTarget=financePageByLabel[item]
          const masterTarget=businessMasterPageByLabel[item]
          const operationsTarget=operationsPageByLabel[item]
          const active = (salesTarget !== undefined && page === salesTarget) || (financeTarget !== undefined && page === financeTarget) || (masterTarget !== undefined && page === masterTarget) || (operationsTarget !== undefined && page === operationsTarget) || (item === 'Kartu Stok FG' && page === 'stock-card') || (item === 'Mutasi Barang Jadi · Vivo' && page === 'movements-vivo') || (item === 'Mutasi Barang Jadi · Widie' && page === 'movements-widie') || (item === 'Pembelian & Penerimaan' && page === 'procurement') || (item === 'Ringkasan Gudang' && page === 'warehouse-dashboard') || (item === 'Kain kantong' && page === 'pocket-fabric') || (item === 'Bahan & Roll' && page === 'materials-rolls') || (item === 'Aksesori' && page === 'accessories') || (item === 'Ringkasan Barang Jadi' && page === 'fg-summary') || (item === 'Stock Adjustment' && page === 'stock-adjustment') || (item === 'Ganti Merek' && page === 'brand-conversion') || (item === 'Buat Potongan' && page === 'cutting-roll') || (item === 'Bagi Potongan' && page === 'mandor-wip') || (item === 'Nota Ambil Aksesori' && page === 'contractor-issue') || (item === 'WIP & Sewing' && page === 'sewing-wip') || (item === 'QC & Final SKU' && page === 'qc') || (item === 'Susun Nota FG' && page === 'fg-handoff') || (item === 'Barang BS & Rework' && page === 'bs-rework') || (item === 'Laundry' && page === 'laundry') || (item === 'HPP & Rekalkulasi' && page === 'hpp') || (item === 'Kain & Benchmark' && page === 'master-fabric') || (item === 'Aksesori & Harga Mandor' && page === 'master-accessory') || (item === 'Pola' && page === 'master-pattern')
          return <button key={item} className={active ? 'sub-active' : ''} onClick={() => chooseSubmenu(item)}>• {item}</button>
        })}</div>}
      </div>)}
      {demoAccess && <div className="nav-section"><button type="button" className="nav-main" aria-expanded={analysisExpanded} onClick={() => { setAnalysisExpanded(!analysisExpanded); setExpanded(null); setAdminExpanded(false) }}><Icon name="dashboard"/><span>Analisis &amp; Planner</span><span className="chevron">{analysisExpanded ? '⌄' : '›'}</span></button>
        {analysisExpanded && <div className="submenu analysis-links">{[['planner','Prioritas produksi'],['stock','Stok & saran SKU'],['cutting','Panel Potongan'],['report','Business Report'],['reminders','Pengingat analisis'],['ai','Tanya AI']].map(([id, label]) => <a key={id} href={'/analisis/' + id + '/'}>{label}</a>)}</div>}</div>}
      <div className="sidebar-spacer" />
      {adminNav.some(canSeeNavLabel) && <div className="nav-section admin-nav-section"><button className={`nav-main ${adminExpanded||page.startsWith('admin-')?'active':''}`} onClick={()=>{setAdminExpanded((value)=>!value);setExpanded(null)}}><Icon name="audit" /><span>Pengaturan & Audit</span><span className="chevron">{adminExpanded?'⌄':'›'}</span></button>
        {adminExpanded&&<div className="submenu">{adminNav.filter(canSeeNavLabel).map((item)=>{const target=item==='Pengguna & Hak Akses'?'admin-access':item==='Impor data awal'?'admin-import':operationsPageByLabel[item];return <button key={item} className={page===target?'sub-active':''} onClick={()=>chooseSubmenu(item)}>• {item}</button>})}</div>}
      </div>}
      <RuntimeEnvironmentCard/>
      <UxTampilanToggle value={uxTampilan} onChange={chooseUxTampilan} placement="sidebar"/>
    </aside>
    {mobileNav && <button type="button" className="mobile-nav-backdrop" tabIndex={-1}
      aria-label="Tutup menu lengkap" onClick={() => setMobileNav(false)}/>}

    <main className="main-panel">
      <header className="topbar"><button className="mobile-menu" aria-label="Buka menu" onClick={() => setMobileNav(true)}><Icon name="menu" /></button><div className="top-title"><div className="top-icon"><Icon name="dashboard" /></div><div><strong>{title}</strong></div></div><div className="top-actions"><RuntimeBadge/><UxTampilanToggle value={uxTampilan} onChange={chooseUxTampilan}/><button className="round-btn" aria-label="Cari menu" aria-expanded={menuSearch !== null} onClick={() => setMenuSearch(menuSearch === null ? '' : null)}><Icon name="search"/></button><RuntimeIdentity/></div></header>
      {menuSearch !== null && <section className="menu-finder panel" role="search" aria-label="Cari menu ERP" onKeyDown={event => { if (event.key === 'Escape') setMenuSearch(null) }}>
        <label>Cari menu<input autoFocus type="search" value={menuSearch} placeholder="Nama menu…" onChange={event => setMenuSearch(event.target.value)}/></label><button type="button" className="soft-btn" onClick={() => setMenuSearch(null)}>Tutup</button>
        <div>{searchable.filter(label => label.toLocaleLowerCase('id').includes(menuSearch.trim().toLocaleLowerCase('id'))).map(label => <button type="button" className="soft-btn" key={label} onClick={() => {chooseSubmenu(label);setMenuSearch(null)}}>{label}</button>)}{!searchable.some(label => label.toLowerCase().includes(menuSearch.trim().toLowerCase())) && <p>Tidak ada menu yang cocok.</p>}</div>
      </section>}
      <div className="page-wrap" data-keyboard-scope onKeyDown={handleErgonomicKeyboard}>
        {!(demoAccess || isPageAllowed(accessBundle, page)) ? <AccessDenied permission={PAGE_PERMISSION_BY_ID[page] ?? 'route.unowned'} roleName={identity.status === 'AUTHORIZED' ? identity.profile.roleName : 'Tidak diketahui'} /> : isScreenHidden(runtime.mode, page) ? <ScreenNotConnected label={SCREEN_ACTIVATION[page]?.label ?? title}/> : <>
        {page === 'dashboard' && <OwnerDashboard
          connected={runtime.mode !== 'DEMO_SIMULATION'}
          connectedMenus={connectedSections(runtime.mode).filter(section => section !== 'Dashboard' && section !== 'Pengaturan & Audit')}
          reminders={reminders}
          onOpenSales={() => setPage('sales-invoice')}
          onOpenReminders={() => setPage('admin-reminders')}
          onToggleReminder={(id)=>setReminders((current)=>current.map((item)=>item.id===id?{...item,status:item.status==='OPEN'?'DONE':'OPEN',completedAt:item.status==='OPEN'?'Sesi ini':undefined}:item))}
        />}
        {isSalesView(page) && <Suspense fallback={<WorkspaceFallback label="Penjualan"/>}>{page==='sales-history'&&runtime.mode!=='DEMO_SIMULATION'?<ConnectedCustomerHistoryPage/>:runtime.mode!=='DEMO_SIMULATION'&&(page==='sales-invoice'||page==='sales-allocation'||page==='sales-payments'||page==='sales-returns')?<ConnectedSalesPage view={page} initialSaleId={page==='sales-invoice'&&invoiceSourceScope!==null&&invoiceSource?.scope===invoiceSourceScope?invoiceSource.saleId:null}/>:<SalesPages view={page} onNavigate={(next)=>setPage(next)} />}</Suspense>}
        {isFinanceView(page) && <Suspense fallback={<WorkspaceFallback label="Keuangan"/>}>{page === 'finance-overview' && runtime.mode !== 'DEMO_SIMULATION' ? <ConnectedFinanceOverviewPage onNavigate={(next)=>setPage(next)}/> : page === 'finance-reports' && runtime.mode !== 'DEMO_SIMULATION' ? <ConnectedFinanceReportPage tab={reportTab} onTab={setReportTab}/> : page === 'finance-cash' && runtime.mode !== 'DEMO_SIMULATION' ? <ConnectedCashLedgerPage/> : page === 'finance-journal' && runtime.mode !== 'DEMO_SIMULATION' ? <ConnectedJournalPage/> : page === 'finance-ar' && runtime.mode !== 'DEMO_SIMULATION' ? <ConnectedReceivablesPage onOpenInvoice={(saleId)=>{if(invoiceSourceScope!==null){setSourceEpoch(value=>value+1);setInvoiceSource({saleId,scope:invoiceSourceScope});setPageState('sales-invoice')}}}/> : page === 'finance-ap' && runtime.mode !== 'DEMO_SIMULATION' ? <ConnectedSupplierCreditPage onLaundry={()=>setPage('laundry')}/> : page === 'finance-payroll' && runtime.mode !== 'DEMO_SIMULATION' ? <ConnectedPayrollPage/> : <FinancePages view={page} onNavigate={(next)=>setPage(next)} onSalesPayment={()=>setPage('sales-payments')} onAttendance={()=>setPage('operations-attendance')} />}</Suspense>}
        {page === 'stock-card' && (runtime.mode === 'DEMO_SIMULATION' ? <StockCard /> : <Suspense fallback={<WorkspaceFallback label="Kartu stok FG"/>}><ConnectedFgStockPage purpose="CARD" onOpenMaster={()=>setPage('master-products')}/></Suspense>)}
        {page === 'fg-summary' && runtime.mode !== 'DEMO_SIMULATION' && <Suspense fallback={<WorkspaceFallback label="Barang jadi"/>}><ConnectedFgStockPage onOpenMaster={()=>setPage('master-products')}/></Suspense>}
        {page === 'movements-vivo' && (runtime.mode === 'DEMO_SIMULATION' ? <Movements bookName="Vivo" bookBrands={vivoBookBrands} setBookBrands={setVivoBookBrands} movements={movements} setMovements={setMovements} /> : <Suspense fallback={<WorkspaceFallback label="Buku mutasi Vivo"/>}><ConnectedFgBookPage bookName="Vivo"/></Suspense>)}
        {page === 'movements-widie' && (runtime.mode === 'DEMO_SIMULATION' ? <Movements bookName="Widie" bookBrands={widieBookBrands} setBookBrands={setWidieBookBrands} movements={movements} setMovements={setMovements} /> : <Suspense fallback={<WorkspaceFallback label="Buku mutasi Widie"/>}><ConnectedFgBookPage bookName="Widie"/></Suspense>)}
        {page === 'procurement' && (runtime.mode === 'DEMO_SIMULATION' ? <ProcurementPage /> : <Suspense fallback={<WorkspaceFallback label="Penerimaan"/>}><ConnectedProcurementPage/></Suspense>)}
        {page === 'brand-conversion' && runtime.mode !== 'DEMO_SIMULATION' && <Suspense fallback={<WorkspaceFallback label="Ganti Merek"/>}><ConnectedProductConversionPage/></Suspense>}
        {page === 'accessories' && runtime.mode !== 'DEMO_SIMULATION' && <Suspense fallback={<WorkspaceFallback label="Aksesori"/>}><ConnectedAccessoryServicePage/></Suspense>}
        {page === 'stock-adjustment' && runtime.mode !== 'DEMO_SIMULATION' && <Suspense fallback={<WorkspaceFallback label="Hitung fisik"/>}><ConnectedStockAdjustmentPage/></Suspense>}
        {page === 'materials-rolls' && runtime.mode !== 'DEMO_SIMULATION' && <Suspense fallback={<WorkspaceFallback label="Bahan & Roll"/>}><ConnectedMaterialsPage/></Suspense>}
        {page === 'warehouse-dashboard' && runtime.mode !== 'DEMO_SIMULATION' && <Suspense fallback={<WorkspaceFallback label="Ringkasan Gudang"/>}><ConnectedWarehouseSummaryPage onNavigate={(next)=>setPage(next)}/></Suspense>}
        {((page === 'warehouse-dashboard' && runtime.mode === 'DEMO_SIMULATION') || (page === 'materials-rolls' && runtime.mode === 'DEMO_SIMULATION') || (page === 'accessories' && runtime.mode === 'DEMO_SIMULATION') || (page === 'fg-summary' && runtime.mode === 'DEMO_SIMULATION') || (page === 'stock-adjustment' && runtime.mode === 'DEMO_SIMULATION') || (page === 'brand-conversion' && runtime.mode === 'DEMO_SIMULATION')) && <Suspense fallback={<WorkspaceFallback label="Gudang"/>}><WarehousePages view={page} onNavigate={(next)=>setPage(next)} /></Suspense>}
        {page === 'cutting-roll' && runtime.cuttingMode === 'CONNECTED' && <Suspense fallback={<WorkspaceFallback label="Buat Potongan connected"/>}><ConnectedCuttingPage/></Suspense>}
        {page === 'cutting-roll' && runtime.cuttingMode === 'SIMULATION' && <CuttingRollPage />}
        {page === 'mandor-wip' && runtime.distributionMode === 'CONNECTED' && <Suspense fallback={<WorkspaceFallback label="Bagi Potongan connected"/>}><ConnectedPickupPage/></Suspense>}
        {page === 'mandor-wip' && runtime.distributionMode === 'SIMULATION' && <MandorWipPage batchNotes={mandorBatchNotes} setBatchNotes={setMandorBatchNotes} />}
        {page === 'contractor-issue' && <Suspense fallback={<WorkspaceFallback label="Nota Ambil Aksesori"/>}>{runtime.mode === 'DEMO_SIMULATION' ? <ContractorIssuePage/> : <ConnectedAccessoryWorkspacePage/>}</Suspense>}
        {page === 'sewing-wip' && runtime.wipStatusMode === 'CONNECTED' && <Suspense fallback={<WorkspaceFallback label="WIP authoritative"/>}><ConnectedWipStatusPage/></Suspense>}
        {page === 'sewing-wip' && runtime.wipStatusMode === 'SIMULATION' && <SewingWipPage
          batchNotes={mandorBatchNotes}
          deliveries={laundryDeliveries}
          finalizedResults={finalizedQcResults}
          laundryDrafts={laundryDrafts}
          reverseNotice={wipReverseNotice}
          onClearReverseNotice={()=>setWipReverseNotice(null)}
          onClearLaundryDraft={(batchId)=>{
            setLaundryDrafts((current)=>{const next={...current};delete next[batchId];return next})
            setLaundryReadyBatches((current)=>current.filter((batch)=>batch.id!==batchId))
          }}
          onConfirmLaundry={(batchId,vendor,snapshot)=>{
            setLaundryDrafts((current)=>({...current,[batchId]:vendor}))
            setLaundryReadyBatches((current)=>{
              const existing=current.find((batch)=>batch.id===batchId)
              if(existing)return current.map((batch)=>batch.id===batchId?{...batch,vendor,...snapshot}:batch)
              const restored=laundryReadyFromSewingBatch(batchId,vendor,snapshot)
              return restored?[restored,...current]:current
            })
            setLaundryPrefill({batchId,vendor,view:'send'})
            setWipReverseNotice(null)
            setPage('laundry')
          }}
          onOpenLaundry={(batchId,vendor,view)=>{setLaundryPrefill({batchId,vendor,view});setPage('laundry')}}
          onOpenQc={(parentId,batchId)=>{
            const parent=sewingWipSeeds.find((item)=>item.id===parentId)
            const batch=parent?.batches.find((item)=>item.id===batchId)
            if(!parent||!batch)return
            setQcSeedId(`${parentId}::${batchId}`)
            setPage('qc')
          }}
        />}
        {page === 'qc' && runtime.qcFinalMode === 'CONNECTED' && <Suspense fallback={<WorkspaceFallback label="QC & Final SKU connected"/>}><ConnectedQcFinalPage/></Suspense>}
        {page === 'qc' && runtime.qcFinalMode === 'SIMULATION' && <StageLots stage="qc"/>}
        {page === 'qc' && runtime.qcFinalMode === 'SIMULATION' && <Suspense fallback={<WorkspaceFallback label="QC & Final SKU"/>}><QcFinalPage seeds={buildQcSeeds(laundryDeliveries)} initialSeedId={qcSeedId} finalizedResults={finalizedQcResults} postedFgCardIds={postedFgCardIds} canPostFinalSku={demoAccess || hasPermission(accessBundle, SENSITIVE_ACTION_PERMISSION.postFinalSku)} onBack={()=>setPage('sewing-wip')} onFinish={(result)=>{setFinalizedQcResults((current)=>{const id=`${result.parentId}::${result.batchId}::${result.completionCount}`;return current.some((item)=>`${item.parentId}::${item.batchId}::${item.completionCount}`===id)?current:[result,...current]});rememberQcNotaSnapshot(result);setQcResult(result)}} onOpenNota={(result)=>{rememberQcNotaSnapshot(result);setQcResult(result);setNotaFocus({kind:'REGULAR',id:regularFgNotaCardId(result)});setNotaOrigin('QC');setPage('fg-handoff')}} /></Suspense>}
        {page === 'fg-handoff' && runtime.fgHandoffMode === 'BLOCKED_UNTIL_AUTHORITATIVE' && <Suspense fallback={<WorkspaceFallback label="Nota FG safety boundary"/>}><ConnectedFgHandoffBoundary/></Suspense>}
        {page === 'fg-handoff' && runtime.fgHandoffMode === 'SIMULATION' && <Suspense fallback={<WorkspaceFallback label="Susun Nota FG"/>}><FgNotaPage
          key={`${notaOrigin}-${notaFocus?.kind??'QUEUE'}-${notaFocus?.id??'ALL'}`}
          result={qcResult}
          eligibleResults={finalizedQcResults}
          repairCards={readyFgNotaCards}
          regularSnapshots={regularFgNotaSnapshots}
          focus={notaFocus}
          origin={notaOrigin}
          postedCardIds={postedFgCardIds}
          onPost={(ids)=>setPostedFgCardIds((current)=>Array.from(new Set([...current,...ids])))}
          onReturn={()=>{
            if(notaOrigin==='QC'&&qcResult){setQcSeedId(`${qcResult.parentId}::${qcResult.batchId}`);setPage('qc')}
            else if(notaOrigin==='BS_REWORK'){setBsBackPage('fg-handoff');setPage('bs-rework')}
          }}
          onOpenQc={()=>{if(qcResult)setQcSeedId(`${qcResult.parentId}::${qcResult.batchId}`);setPage('qc')}}
          onOpenBs={()=>{setBsPrefill(qcResult);setBsBackPage('fg-handoff');setPage('bs-rework')}}
        /></Suspense>}
        {page === 'bs-rework' && runtime.bsResolutionMode === 'CONNECTED' && <Suspense fallback={<WorkspaceFallback label="BS Resolution connected"/>}><ConnectedBsResolutionPage/></Suspense>}
        {page === 'bs-rework' && runtime.bsResolutionMode === 'SIMULATION' && <Suspense fallback={<WorkspaceFallback label="Barang BS & Rework"/>}><BsReworkPage
          initialResult={bsPrefill}
          initialWorkspace={bsWorkspace??undefined}
          onWorkspaceChange={setBsWorkspace}
          postedFgCardIds={postedFgCardIds}
          onBack={()=>setPage(bsBackPage)}
          onNotaCardReady={rememberFgNotaCard}
          onOpenNota={(card)=>{rememberFgNotaCard(card);setNotaFocus({kind:'REPAIR',id:card.id});setNotaOrigin('BS_REWORK');setPage('fg-handoff')}}
          onStuckReturned={({batchId,laundry,goodBySize,bsBySize})=>{
            const remainingGood:number[]=[...goodBySize]
            const remainingBs:number[]=[...bsBySize]
            setLaundryDeliveries((current)=>current.map((delivery)=>{
              if(delivery.batchId!==batchId||(!delivery.vendor.includes(laundry)&&!laundry.includes(delivery.vendor))||(remainingGood.every((qty)=>qty<=0)&&remainingBs.every((qty)=>qty<=0)))return delivery
              const outstanding=laundryOutstandingSizes(delivery)
              const acceptedGood=outstanding.map((qty,index)=>Math.min(qty,remainingGood[index])) as QtyTuple
              const afterGood=outstanding.map((qty,index)=>Math.max(0,qty-acceptedGood[index])) as QtyTuple
              const acceptedBs=afterGood.map((qty,index)=>Math.min(qty,remainingBs[index])) as QtyTuple
              remainingGood.forEach((_,index)=>{remainingGood[index]=Math.max(0,remainingGood[index]-acceptedGood[index])})
              remainingBs.forEach((_,index)=>{remainingBs[index]=Math.max(0,remainingBs[index]-acceptedBs[index])})
              const acceptedGoodTotal=acceptedGood.reduce((sum,qty)=>sum+qty,0)
              const acceptedBsTotal=acceptedBs.reduce((sum,qty)=>sum+qty,0)
              if(acceptedGoodTotal+acceptedBsTotal<=0)return delivery
              return {...delivery,
                good:delivery.good+acceptedGoodTotal,
                bs:delivery.bs+acceptedBsTotal,
                goodSizes:delivery.goodSizes.map((qty,index)=>qty+acceptedGood[index]) as QtyTuple,
                bsSizes:delivery.bsSizes.map((qty,index)=>qty+acceptedBs[index]) as QtyTuple,
              }
            }))
          }}
        /></Suspense>}
        {page === 'laundry' && runtime.laundryMode === 'CONNECTED' && <Suspense fallback={<WorkspaceFallback label="Laundry connected"/>}><ConnectedLaundryPage/></Suspense>}
        {page === 'laundry' && runtime.laundryMode === 'SIMULATION' && <LaundryPage
          prefill={laundryPrefill}
          readyBatches={laundryReadyBatches}
          setReadyBatches={setLaundryReadyBatches}
          deliveries={laundryDeliveries}
          setDeliveries={setLaundryDeliveries}
          onPosted={(batchIds)=>setLaundryDrafts((current)=>{const next={...current};batchIds.forEach((batchId)=>delete next[batchId]);return next})}
          onReturnToWip={(batchId,vendor,qty)=>{
            setLaundryDrafts((current)=>{const next={...current};delete next[batchId];return next})
            setWipReverseNotice(`Batch ${batchId} · ${qty} pcs kembali dari ${vendor}. Pilih laundry baru.`)
            setPage('sewing-wip')
          }}
          onOpenQc={(parentId,batchId)=>{setQcSeedId(`${parentId}::${batchId}`);setQcResult(null);setPage('qc')}}
        />}
        {page === 'hpp' && <Suspense fallback={<WorkspaceFallback label="HPP & Rekalkulasi"/>}>{runtime.mode === 'DEMO_SIMULATION' ? <HppPage /> : <ConnectedSkuHppPage/>}</Suspense>}
        {(page === 'master-fabric' || page === 'master-accessory') && <Suspense fallback={<WorkspaceFallback label="Master Material"/>}>{runtime.mode !== 'DEMO_SIMULATION' ? <ConnectedMasterPage view={page}/> : <MaterialMasterPages view={page}/>}</Suspense>}
        {(page === 'master-products' || page === 'master-customers' || page === 'master-partners' || page === 'master-workforce' || page === 'master-locations') && <Suspense fallback={<WorkspaceFallback label="Master Data"/>}>{page === 'master-products' && runtime.mode !== 'DEMO_SIMULATION' ? <ConnectedSkuMasterPage/> : page !== 'master-products' && runtime.mode !== 'DEMO_SIMULATION' ? <ConnectedMasterPage view={page}/> : <>{page==='master-products'&&<SkuRangePage mode="master"/>}<MasterDataPages view={page}/></>}</Suspense>}
        {page === 'master-pattern' && <Suspense fallback={<WorkspaceFallback label="Master Pola"/>}><PatternPage/></Suspense>}
        {page === 'admin-access' && <Suspense fallback={<WorkspaceFallback label="Pengguna & Hak Akses"/>}><AccessControlPage/></Suspense>}
        {page === 'pocket-fabric' && <Suspense fallback={<WorkspaceFallback label="Kain kantong"/>}><ConnectedPocketFabricPage/></Suspense>}
        {page === 'admin-import' && <Suspense fallback={<WorkspaceFallback label="Impor data awal"/>}><MigrationWorkbook/>{!demoAccess && <ConnectedInitialImportPage/>}</Suspense>}
        {isOperationsView(page) && <Suspense fallback={<WorkspaceFallback label="Pengaturan operasional"/>}>{page === 'operations-attendance' && runtime.mode !== 'DEMO_SIMULATION' ? <ConnectedAttendancePage/> : page === 'admin-reminders' && runtime.mode !== 'DEMO_SIMULATION' ? <ConnectedRemindersPage/> : page === 'admin-settings' && runtime.mode !== 'DEMO_SIMULATION' ? <ConnectedErpSettingsPage onOpenImport={()=>setPage('admin-import')}/> : page === 'admin-audit' && runtime.mode !== 'DEMO_SIMULATION' ? <ConnectedAuditTrailPage/> : <OperationsAdminPages view={page} onNavigate={(next)=>setPage(next)} reminders={reminders} onChangeReminders={setReminders}/>}</Suspense>}
        {page === 'placeholder' && <Placeholder />}
        </>}
      </div>
    </main>
    <MobilePrimaryNavigation items={mobileDestinations} current={page} menuOpen={mobileNav}
      onNavigate={id => { setPage(id as Page); setExpanded(null); setAdminExpanded(false); setMobileNav(false) }}
      onMore={() => setMobileNav(true)}/>
  </div></TransactionSourceProvider>
}

function WorkspaceFallback({ label }: { label: string }) {
  return <div className="panel placeholder"><div className="placeholder-icon">◇</div><h2>Menyiapkan {label}…</h2><p>Memuat workspace dan guardrail transaksi.</p></div>
}

// Owner D15-2: a menu whose screen is not connected in this build shows no figure at all, sample or otherwise.
export function ScreenNotConnected({ label }: { label: string }) {
  return <section className="panel placeholder" role="status" aria-label={`${label} belum tersambung`}><div className="placeholder-icon"><ShieldCheck/></div><h2>{label} belum tersambung</h2><p>Layar ini belum membaca data ERP di aplikasi ini, jadi tidak ditampilkan. Menu ini muncul begitu layarnya tersambung.</p></section>
}

export function AccessDenied({ permission, roleName }: { permission: string; roleName: string }) {
  return <section className="panel placeholder access-denied" role="alert"><div className="placeholder-icon"><ShieldCheck/></div><h2>Tidak punya akses</h2><p>Role <strong>{roleName}</strong> tidak memiliki izin untuk membuka halaman ini.</p><code>{permission}</code><small>Menu disembunyikan untuk kenyamanan; server tetap memeriksa ulang setiap aksi.</small></section>
}

function Placeholder() { return <div className="panel placeholder"><div className="placeholder-icon">◇</div><h2>Fondasinya sudah disiapkan.</h2><p>Modul ini berikutnya akan mengikuti flow bisnis yang sama: informasi penting terlihat sebelum user menekan tombol yang mengubah uang atau stok.</p></div> }

export default App

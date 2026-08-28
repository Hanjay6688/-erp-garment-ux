import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Boxes, Check, ChevronDown, ClipboardCheck,
  FileClock, Filter, History, Layers3, MapPin, Package, PackageCheck,
  Plus, RotateCcw, Ruler, Search, ShieldCheck, SlidersHorizontal,
  Sparkles, Tag, Warehouse,
} from 'lucide-react'
import { productCatalog } from './productCatalog'
import './warehouse.css'

export type WarehouseView = 'warehouse-dashboard' | 'materials-rolls' | 'accessories' | 'fg-summary' | 'returns-adjustments'

type Tone = 'good' | 'warn' | 'danger' | 'neutral'
type MaterialSummary = {
  id: string
  material: string
  supplier: string
  physicalYards: number
  reservedYards: number
  availableYards: number
  totalRolls: number
  availableRolls: number
  avgCost: number
  location: string
  status: 'Aman' | 'Menipis' | 'Perlu cek'
  lastMovement: string
}
type FabricRoll = {
  id: string
  material: string
  supplier: string
  receivedAt: string
  original: number
  remaining: number
  reserved: number
  location: string
  status: 'Tersedia' | 'Terpesan' | 'WIP' | 'Habis'
  costState: 'ACTUAL' | 'ESTIMATED'
  activeCost: number
  source: string
}
type Accessory = {
  id: string
  name: string
  category: string
  supplier: string
  unit: string
  physical: number
  reserved: number
  minimum: number
  avgCost: number
  location: string
  status: 'Aman' | 'Menipis' | 'Perlu pesan'
  lastMovement: string
}
type WarehouseCase = {
  id: string
  type: 'Retur Mandor' | 'Stock Opname' | 'Penyesuaian'
  status: 'Menunggu review' | 'Selisih ditemukan' | 'Selesai'
  subject: string
  identity: string
  actor: string
  location: string
  happenedAt: string
  source: string
  note: string
  lines: Array<{ label: string; unit: string; recorded: number; physical: number }>
}

const materials: MaterialSummary[] = [
  { id:'MAT-LCY', material:'Lucy', supplier:'Sinaran', physicalYards:3248.5, reservedYards:892.5, availableYards:2356, totalRolls:31, availableRolls:22, avgCost:49200, location:'Rak Kain A', status:'Aman', lastMovement:'Potongan POT-260828-044 · 10:18' },
  { id:'MAT-1069', material:'1069 Ori', supplier:'Sinaran', physicalYards:3029.5, reservedYards:1760, availableYards:1269.5, totalRolls:27, availableRolls:11, avgCost:50750, location:'Rak Kain B', status:'Menipis', lastMovement:'Reservasi POT-260828-041 · 09:42' },
  { id:'MAT-ZDK', material:'Zodiak KW', supplier:'Sumber Cahaya', physicalYards:1884, reservedYards:442, availableYards:1442, totalRolls:18, availableRolls:14, avgCost:47600, location:'Rak Kain C', status:'Aman', lastMovement:'Penerimaan SJ-260827-018 · kemarin' },
  { id:'MAT-CRB', material:'Corduroy 8W', supplier:'Mitra Tekstil', physicalYards:686.5, reservedYards:318, availableYards:368.5, totalRolls:7, availableRolls:4, avgCost:68400, location:'Rak Kain D', status:'Perlu cek', lastMovement:'Retur Mandor RT-260828-004 · 08:12' },
]

const fabricRolls: FabricRoll[] = [
  { id:'LCY-031', material:'Lucy', supplier:'Sinaran', receivedAt:'27 Agu 2026', original:131.5, remaining:131.5, reserved:0, location:'A-02-03', status:'Tersedia', costState:'ACTUAL', activeCost:49200, source:'SJ-260827-018' },
  { id:'LCY-030', material:'Lucy', supplier:'Sinaran', receivedAt:'27 Agu 2026', original:124, remaining:96.5, reserved:60, location:'A-02-02', status:'Terpesan', costState:'ACTUAL', activeCost:49200, source:'SJ-260827-018' },
  { id:'LCY-029', material:'Lucy', supplier:'Sinaran', receivedAt:'27 Agu 2026', original:91, remaining:18.5, reserved:0, location:'Area Retur', status:'Tersedia', costState:'ACTUAL', activeCost:49200, source:'RT-MD-260828-004' },
  { id:'LCY-028', material:'Lucy', supplier:'Sinaran', receivedAt:'25 Agu 2026', original:140, remaining:140, reserved:140, location:'Staging Potong', status:'WIP', costState:'ESTIMATED', activeCost:48500, source:'SJ-260825-012' },
  { id:'1069-027', material:'1069 Ori', supplier:'Sinaran', receivedAt:'24 Agu 2026', original:118, remaining:118, reserved:118, location:'B-01-01', status:'Terpesan', costState:'ACTUAL', activeCost:50750, source:'SJ-260824-009' },
  { id:'1069-026', material:'1069 Ori', supplier:'Sinaran', receivedAt:'24 Agu 2026', original:107.5, remaining:33, reserved:0, location:'B-01-02', status:'Tersedia', costState:'ACTUAL', activeCost:50750, source:'SJ-260824-009' },
  { id:'ZDK-018', material:'Zodiak KW', supplier:'Sumber Cahaya', receivedAt:'27 Agu 2026', original:103, remaining:103, reserved:0, location:'C-02-01', status:'Tersedia', costState:'ESTIMATED', activeCost:47600, source:'SJ-260827-021' },
  { id:'CRB-007', material:'Corduroy 8W', supplier:'Mitra Tekstil', receivedAt:'22 Agu 2026', original:108, remaining:46.5, reserved:0, location:'D-01-02', status:'Tersedia', costState:'ACTUAL', activeCost:68400, source:'SJ-260822-006' },
]

const accessories: Accessory[] = [
  { id:'ACC-KNC-17', name:'Kancing Jeans 17 mm', category:'Kancing', supplier:'Inti Metal', unit:'pcs', physical:12480, reserved:3600, minimum:6000, avgCost:1850, location:'Aksesori A-01', status:'Aman', lastMovement:'Keluar ke Mandor Asep · 10:22' },
  { id:'ACC-RVT-CU', name:'Rivet Copper', category:'Rivet', supplier:'Inti Metal', unit:'pcs', physical:7160, reserved:3480, minimum:5000, avgCost:940, location:'Aksesori A-02', status:'Menipis', lastMovement:'Keluar ke Mandor Dedi · 09:48' },
  { id:'ACC-ZIP-14', name:'Resleting YKK 14 cm', category:'Resleting', supplier:'Sinar Zip', unit:'pcs', physical:4380, reserved:1680, minimum:2500, avgCost:7100, location:'Aksesori B-01', status:'Aman', lastMovement:'Terima PO-BELI-260827-018 · kemarin' },
  { id:'ACC-HTG-WD', name:'Hangtag Widie', category:'Label & tag', supplier:'Cetak Jaya', unit:'pcs', physical:2260, reserved:1920, minimum:1500, avgCost:620, location:'Aksesori C-02', status:'Perlu pesan', lastMovement:'Reservasi POT-260828-041 · 09:42' },
  { id:'ACC-KRT-32', name:'Karet Pinggang 32 mm', category:'Karet', supplier:'Maju Elastik', unit:'meter', physical:1860, reserved:420, minimum:900, avgCost:3950, location:'Aksesori B-03', status:'Aman', lastMovement:'Retur Mandor Asep · kemarin' },
  { id:'ACC-LBL-VV', name:'Label Woven Vivo', category:'Label & tag', supplier:'Cetak Jaya', unit:'pcs', physical:3820, reserved:1120, minimum:2000, avgCost:780, location:'Aksesori C-01', status:'Aman', lastMovement:'Keluar ke Mandor Intan · kemarin' },
]

const warehouseCases: WarehouseCase[] = [
  { id:'RT-MD-260828-004', type:'Retur Mandor', status:'Menunggu review', subject:'Sisa kain Lucy kembali', identity:'LCY-029 · 18,5 yd', actor:'Mandor Asep', location:'Area Retur', happenedAt:'28 Agu 2026 · 08:12', source:'POT-260826-041 · Batch 02', note:'Sisa gulung utuh. Yard fisik sudah diukur ulang oleh gudang.', lines:[{label:'Roll LCY-029',unit:'yd',recorded:0,physical:18.5}] },
  { id:'OPN-260828-002', type:'Stock Opname', status:'Selisih ditemukan', subject:'Hitung ulang Kancing Jeans', identity:'ACC-KNC-17 · Aksesori A-01', actor:'Nina · Gudang', location:'Aksesori A-01', happenedAt:'28 Agu 2026 · 07:44', source:'Sesi OPN-260828-A', note:'Dua kotak terbuka dihitung ulang. Selisih belum diposting.', lines:[{label:'Kancing Jeans 17 mm',unit:'pcs',recorded:12492,physical:12480}] },
  { id:'ADJ-FG-260827-006', type:'Penyesuaian', status:'Menunggu review', subject:'Koreksi label grade FG', identity:'Widie · SKU 73002 · Size 32', actor:'Rina · QC', location:'Gudang FG Cadangan', happenedAt:'27 Agu 2026 · 16:40', source:'QC-260827-011', note:'Bukan selisih fisik. 1 pcs dipindah klasifikasi Good → BS.', lines:[{label:'Good · Size 32',unit:'pcs',recorded:37,physical:36},{label:'BS · Size 32',unit:'pcs',recorded:35,physical:36}] },
  { id:'RT-MD-260827-011', type:'Retur Mandor', status:'Selesai', subject:'Karet pinggang tidak terpakai', identity:'ACC-KRT-32 · 24 meter', actor:'Mandor Intan', location:'Aksesori B-03', happenedAt:'27 Agu 2026 · 14:08', source:'POT-260824-036 · Batch 01', note:'Retur diterima layak pakai dan sudah masuk kembali ke saldo tersedia.', lines:[{label:'Karet Pinggang 32 mm',unit:'meter',recorded:1836,physical:1860}] },
]

const formatNumber = (value: number, digits = 1) => new Intl.NumberFormat('id-ID', { maximumFractionDigits: digits }).format(value)
const money = (value: number) => new Intl.NumberFormat('id-ID', { style:'currency', currency:'IDR', maximumFractionDigits:0 }).format(value)
const statusTone = (status: string): Tone => status === 'Aman' || status === 'Tersedia' || status === 'Selesai' || status === 'ACTUAL' ? 'good' : status === 'Menipis' || status === 'Terpesan' || status === 'WIP' || status === 'Menunggu review' || status === 'ESTIMATED' ? 'warn' : status === 'Perlu pesan' || status === 'Perlu cek' || status === 'Selisih ditemukan' ? 'danger' : 'neutral'

function StatusBadge({ children, tone }: { children: string; tone?: Tone }) {
  return <span className={`wh-status ${tone ?? statusTone(children)}`}>{children}</span>
}

function SearchBox({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder: string }) {
  return <label className="wh-search"><Search /><input value={value} onChange={(event)=>onChange(event.target.value)} placeholder={placeholder}/></label>
}

function SelectFilter({ label, value, options, onChange }: { label: string; value: string; options: string[]; onChange: (value: string) => void }) {
  return <label className="wh-filter"><span>{label}</span><select value={value} onChange={(event)=>onChange(event.target.value)}><option value="Semua">Semua</option>{options.map((option)=><option key={option}>{option}</option>)}</select><ChevronDown /></label>
}

function MetricCard({ label, value, note, tone='neutral', icon: Glyph=Boxes }: { label: string; value: string; note: string; tone?: Tone; icon?: typeof Boxes }) {
  return <div className={`panel wh-metric ${tone}`}><span>{label}</span><strong>{value}</strong><small>{note}</small><i><Glyph /></i></div>
}

function EmptyResult({ title, note }: { title: string; note: string }) {
  return <div className="wh-empty"><Filter/><strong>{title}</strong><small>{note}</small></div>
}

export default function WarehousePages({ view, onNavigate }: { view: WarehouseView; onNavigate: (view: WarehouseView) => void }) {
  if (view === 'warehouse-dashboard') return <WarehouseDashboard onNavigate={onNavigate}/>
  if (view === 'materials-rolls') return <MaterialsRollsPage/>
  if (view === 'accessories') return <AccessoriesPage/>
  if (view === 'fg-summary') return <FinishedGoodsSummaryPage/>
  return <ReturnsAdjustmentsPage/>
}

function WarehouseDashboard({ onNavigate }: { onNavigate: (view: WarehouseView) => void }) {
  const movements = [
    { time:'10:22', title:'Aksesori keluar', meta:'Mandor Asep · POT-260826-041', amount:'3.600 pcs', tone:'out' },
    { time:'10:18', title:'Kain ke meja potong', meta:'Lucy · 4 roll · POT-260828-044', amount:'482,5 yd', tone:'out' },
    { time:'09:31', title:'FG masuk', meta:'Widie 73001 · QC-260828-006', amount:'120 pcs', tone:'in' },
    { time:'08:12', title:'Retur mandor', meta:'Lucy · LCY-029', amount:'18,5 yd', tone:'in' },
  ]
  return <>
    <section className="hero-copy compact wh-hero"><div><div className="eyebrow">GUDANG · HARI INI</div><h1>Barang kebaca sebelum dicari.</h1><p>Satu layar untuk melihat bahan, roll, aksesori, barang jadi, dan kasus yang belum beres—tanpa mencampur saldo fisik dengan barang yang sudah terpesan.</p></div><div className="wh-updated"><span><ShieldCheck/> LEDGER READ-ONLY</span><strong>Terakhir sinkron 10:24</strong><small>Prototype frontend · belum posting ke backend</small></div></section>
    <section className="wh-metrics"><MetricCard label="Kain tersedia" value="5.435,5 yd" note="51 roll siap dialokasikan" tone="good" icon={Ruler}/><MetricCard label="Aksesori tersedia" value="22.240 unit" note="2 item di bawah minimum" tone="warn" icon={Package}/><MetricCard label="FG siap jual" value="1.074 pcs" note="8 SKU · 2 lokasi" tone="good" icon={PackageCheck}/><MetricCard label="Perlu review" value="3 kasus" note="Retur, opname, penyesuaian" tone="danger" icon={ClipboardCheck}/></section>
    <section className="wh-dashboard-grid">
      <div className="panel wh-zone-panel"><header><div><span>AREA GUDANG</span><h2>Buka dari pekerjaan fisiknya</h2><p>Angka tersedia sudah dikurangi reservasi aktif.</p></div><Warehouse/></header><div className="wh-zone-grid">
        <button onClick={()=>onNavigate('materials-rolls')}><i className="blue"><Ruler/></i><span><small>KAIN</small><strong>Bahan & Roll</strong><em>83 roll · 8.848,5 yd fisik</em></span><b>5.435,5 yd tersedia</b><ArrowRight/></button>
        <button onClick={()=>onNavigate('accessories')}><i className="violet"><Boxes/></i><span><small>KOMPONEN</small><strong>Aksesori</strong><em>6 item aktif · per unit</em></span><b>22.240 unit tersedia</b><ArrowRight/></button>
        <button onClick={()=>onNavigate('fg-summary')}><i className="green"><PackageCheck/></i><span><small>BARANG JADI</small><strong>Ringkasan FG</strong><em>Per merek, SKU, size, grade</em></span><b>1.074 pcs Good</b><ArrowRight/></button>
        <button onClick={()=>onNavigate('returns-adjustments')}><i className="amber"><SlidersHorizontal/></i><span><small>CONTROL</small><strong>Retur & Penyesuaian</strong><em>Semua koreksi harus beralasan</em></span><b>3 menunggu</b><ArrowRight/></button>
      </div></div>
      <div className="panel wh-attention"><header><div><span>BUTUH PERHATIAN</span><h2>Jangan kelewat hari ini</h2></div><AlertTriangle/></header><div className="wh-attention-list"><article className="danger"><i/><div><strong>Hangtag Widie tinggal 340 pcs</strong><small>Sesudah reservasi POT-260828-041</small></div><b>Pesan</b></article><article className="warn"><i/><div><strong>12 pcs selisih opname</strong><small>Kancing Jeans 17 mm · belum posting</small></div><b>Review</b></article><article><i/><div><strong>4 roll masih ESTIMATED</strong><small>Kasbon supplier belum cocok</small></div><b>Cek</b></article></div></div>
    </section>
    <section className="panel wh-movement-panel"><header><div><span>MUTASI TERBARU</span><h2>Gerak barang lintas gudang</h2></div><button className="soft-btn"><History/> Lihat ledger lengkap</button></header><div className="wh-movement-list">{movements.map((item)=><article key={`${item.time}-${item.title}`}><time>{item.time}</time><i className={item.tone}/><div><strong>{item.title}</strong><small>{item.meta}</small></div><b className={item.tone}>{item.tone==='in'?'+':'−'} {item.amount}</b></article>)}</div></section>
  </>
}

function MaterialsRollsPage() {
  const [query,setQuery] = useState('')
  const [supplier,setSupplier] = useState('Semua')
  const [status,setStatus] = useState('Semua')
  const [selectedId,setSelectedId] = useState(materials[0].id)
  const selected = materials.find((item)=>item.id===selectedId) ?? materials[0]
  const visibleMaterials = useMemo(()=>materials.filter((item)=>`${item.material} ${item.supplier} ${item.location}`.toLowerCase().includes(query.toLowerCase()) && (supplier==='Semua'||item.supplier===supplier) && (status==='Semua'||item.status===status)),[query,supplier,status])
  const visibleRolls = fabricRolls.filter((roll)=>roll.material===selected.material)
  const estimatedCount = visibleRolls.filter((roll)=>roll.costState==='ESTIMATED').length
  return <>
    <section className="hero-copy compact wh-hero"><div><div className="eyebrow">GUDANG · RAW MATERIAL</div><h1>Bahan & Roll</h1><p>Pilih bahan dulu, lalu telusuri setiap gulung: yard awal, sisa fisik, reservasi, lokasi, dan status harga aktif.</p></div><div className="wh-rule"><Ruler/><div><span>ATURAN UTAMA</span><strong>Saldo kain tetap per roll</strong><small>Total bahan adalah penjumlahan roll, bukan angka lepas.</small></div></div></section>
    <section className="wh-metrics"><MetricCard label="Fisik seluruh kain" value="8.848,5 yd" note="83 roll tercatat" icon={Layers3}/><MetricCard label="Sudah terpesan" value="3.413 yd" note="Tidak boleh dialokasikan ulang" tone="warn" icon={Tag}/><MetricCard label="Siap dipakai" value="5.435,5 yd" note="Fisik dikurangi reservasi" tone="good" icon={Check}/><MetricCard label="Harga estimasi" value="4 roll" note="Menunggu kasbon supplier" tone="warn" icon={FileClock}/></section>
    <div className="panel wh-workspace">
      <div className="wh-toolbar"><SearchBox value={query} onChange={setQuery} placeholder="Cari bahan, pabrik, atau lokasi..."/><SelectFilter label="Pabrik" value={supplier} options={[...new Set(materials.map((item)=>item.supplier))]} onChange={setSupplier}/><SelectFilter label="Status" value={status} options={[...new Set(materials.map((item)=>item.status))]} onChange={setStatus}/><button className="wh-reset" onClick={()=>{setQuery('');setSupplier('Semua');setStatus('Semua')}}><RotateCcw/> Reset</button></div>
      <div className="wh-master-detail">
        <aside className="wh-browser"><header><div><span>BROWSE BAHAN</span><strong>{visibleMaterials.length} bahan tampil</strong></div><small>Klik untuk buka roll</small></header><div className="wh-browser-list">{visibleMaterials.map((item)=><button key={item.id} className={selected.id===item.id?'active':''} onClick={()=>setSelectedId(item.id)}><span className="wh-index">{String(materials.indexOf(item)+1).padStart(2,'0')}</span><div><strong>{item.material}</strong><small>{item.supplier} · {item.location}</small><em>{item.availableRolls} dari {item.totalRolls} roll tersedia</em></div><b>{formatNumber(item.availableYards)} yd</b><StatusBadge>{item.status}</StatusBadge></button>)}{visibleMaterials.length===0&&<EmptyResult title="Bahan tidak ditemukan" note="Ubah pencarian atau reset filter."/>}</div></aside>
        <main className="wh-detail"><header className="wh-detail-head"><div><span>BAHAN TERPILIH</span><h2>{selected.material}</h2><p>{selected.supplier} · {selected.location} · {selected.id}</p></div><div className="wh-detail-total"><span>TERSEDIA</span><strong>{formatNumber(selected.availableYards)} yd</strong><small>{money(selected.avgCost)} / yd moving average</small></div></header>
          <div className="wh-balance-equation"><span><small>FISIK</small><strong>{formatNumber(selected.physicalYards)} yd</strong></span><i>−</i><span className="reserved"><small>TERPESAN</small><strong>{formatNumber(selected.reservedYards)} yd</strong></span><i>=</i><span className="available"><small>TERSEDIA</small><strong>{formatNumber(selected.availableYards)} yd</strong></span></div>
          {estimatedCount>0&&<div className="wh-inline-note warn"><FileClock/><div><strong>{estimatedCount} roll masih memakai harga benchmark</strong><small>Stok dan HPP boleh berjalan, tetapi histori benchmark tetap terlihat sampai kasbon actual cocok.</small></div></div>}
          <div className="wh-roll-head"><div><span>ROLL AKTIF</span><strong>{visibleRolls.length} gulung untuk {selected.material}</strong></div><small>Urut penerimaan terbaru</small></div>
          <div className="wh-roll-list">{visibleRolls.map((roll)=>{const available=Math.max(0,roll.remaining-roll.reserved);const used=Math.max(0,roll.original-roll.remaining);return <article key={roll.id}><header><div className="wh-roll-id"><i><Ruler/></i><div><strong>{roll.id}</strong><small>{roll.source} · {roll.receivedAt}</small></div></div><div><StatusBadge>{roll.status}</StatusBadge><StatusBadge tone={statusTone(roll.costState)}>{roll.costState}</StatusBadge></div></header><div className="wh-roll-numbers"><span><small>YARD AWAL</small><strong>{formatNumber(roll.original)}</strong></span><span><small>SUDAH DIPAKAI</small><strong>{formatNumber(used)}</strong></span><span><small>SISA FISIK</small><strong>{formatNumber(roll.remaining)}</strong></span><span className="reserved"><small>TERPESAN</small><strong>{formatNumber(roll.reserved)}</strong></span><span className="available"><small>TERSEDIA</small><strong>{formatNumber(available)} yd</strong></span></div><div className="wh-roll-progress"><span style={{width:`${Math.min(100,(roll.remaining/roll.original)*100)}%`}}/></div><footer><span><MapPin/> {roll.location}</span><span>{money(roll.activeCost)} / yd aktif</span><button>Riwayat roll <ArrowRight/></button></footer></article>})}</div>
        </main>
      </div>
    </div>
  </>
}

function AccessoriesPage() {
  const [query,setQuery] = useState('')
  const [category,setCategory] = useState('Semua')
  const [status,setStatus] = useState('Semua')
  const [selectedId,setSelectedId] = useState(accessories[0].id)
  const visible = useMemo(()=>accessories.filter((item)=>`${item.name} ${item.category} ${item.supplier} ${item.id}`.toLowerCase().includes(query.toLowerCase()) && (category==='Semua'||item.category===category) && (status==='Semua'||item.status===status)),[query,category,status])
  const selected = accessories.find((item)=>item.id===selectedId) ?? accessories[0]
  const available = selected.physical-selected.reserved
  const coverage = selected.minimum ? available/selected.minimum : 0
  const movementRows = [
    { ref:'OUT-260828-018', date:'Hari ini · 10:22', note:'Keluar ke Mandor Asep', delta:-1200, balance:selected.physical },
    { ref:'RSV-260828-041', date:'Hari ini · 09:42', note:'Reservasi POT-260828-041', delta:0, balance:selected.physical+1200 },
    { ref:'RCV-260827-018', date:'Kemarin · 15:08', note:`Terima dari ${selected.supplier}`, delta:4800, balance:selected.physical+1200 },
  ]
  return <>
    <section className="hero-copy compact wh-hero"><div><div className="eyebrow">GUDANG · KOMPONEN</div><h1>Aksesori</h1><p>Qty langsung per unit. Fisik, reservasi, minimum stok, dan nilai moving average terlihat tanpa memaksa aksesori mengikuti bentuk roll.</p></div><div className="wh-rule"><Boxes/><div><span>POLA INPUT</span><strong>Qty langsung, bukan gulungan</strong><small>PCS, meter, set, atau unit master item.</small></div></div></section>
    <section className="wh-metrics"><MetricCard label="Nilai stok aksesori" value="Rp78,4 jt" note="Moving average aktif" icon={Package}/><MetricCard label="Item aktif" value="6 item" note="5 kategori · 3 supplier" icon={Boxes}/><MetricCard label="Di bawah minimum" value="2 item" note="Rivet & hangtag" tone="danger" icon={AlertTriangle}/><MetricCard label="Reservasi produksi" value="12.220 unit" note="Belum mengurangi fisik" tone="warn" icon={Tag}/></section>
    <div className="panel wh-workspace">
      <div className="wh-toolbar"><SearchBox value={query} onChange={setQuery} placeholder="Cari aksesori, kode, supplier..."/><SelectFilter label="Kategori" value={category} options={[...new Set(accessories.map((item)=>item.category))]} onChange={setCategory}/><SelectFilter label="Status" value={status} options={[...new Set(accessories.map((item)=>item.status))]} onChange={setStatus}/><button className="wh-reset" onClick={()=>{setQuery('');setCategory('Semua');setStatus('Semua')}}><RotateCcw/> Reset</button></div>
      <div className="wh-master-detail accessory">
        <aside className="wh-browser"><header><div><span>BROWSE AKSESORI</span><strong>{visible.length} item tampil</strong></div><small>Urut status stok</small></header><div className="wh-browser-list">{visible.map((item)=>{const itemAvailable=item.physical-item.reserved;return <button key={item.id} className={selected.id===item.id?'active':''} onClick={()=>setSelectedId(item.id)}><span className="wh-index"><Package/></span><div><strong>{item.name}</strong><small>{item.id} · {item.category}</small><em>{item.supplier} · {item.location}</em></div><b>{formatNumber(itemAvailable,0)} {item.unit}</b><StatusBadge>{item.status}</StatusBadge></button>})}{visible.length===0&&<EmptyResult title="Aksesori tidak ditemukan" note="Coba kategori lain atau reset filter."/>}</div></aside>
        <main className="wh-detail"><header className="wh-detail-head"><div><span>ITEM TERPILIH</span><h2>{selected.name}</h2><p>{selected.id} · {selected.category} · {selected.supplier}</p></div><div className="wh-detail-total"><span>TERSEDIA</span><strong>{formatNumber(available,0)} {selected.unit}</strong><small>{money(selected.avgCost)} / {selected.unit} moving average</small></div></header>
          <div className="wh-accessory-facts"><div><MapPin/><span><small>LOKASI</small><strong>{selected.location}</strong></span></div><div><Boxes/><span><small>FISIK</small><strong>{formatNumber(selected.physical,0)} {selected.unit}</strong></span></div><div><Tag/><span><small>TERPESAN</small><strong>{formatNumber(selected.reserved,0)} {selected.unit}</strong></span></div><div className={coverage<1?'danger':'good'}><ShieldCheck/><span><small>MINIMUM</small><strong>{formatNumber(selected.minimum,0)} {selected.unit}</strong></span></div></div>
          <div className={`wh-stock-health ${coverage<1?'danger':coverage<1.5?'warn':'good'}`}><div><span>KESEHATAN STOK</span><strong>{coverage<1?'Di bawah minimum':coverage<1.5?'Mendekati minimum':'Aman untuk kebutuhan aktif'}</strong><small>Tersedia {formatNumber(available,0)} dibanding minimum {formatNumber(selected.minimum,0)} {selected.unit}.</small></div><b>{Math.round(coverage*100)}%</b></div>
          <section className="wh-mini-ledger"><header><div><span>MUTASI TERAKHIR</span><strong>{selected.lastMovement}</strong></div><button>Semua riwayat <ArrowRight/></button></header><div className="wh-mini-ledger-head"><span>Waktu / ref</span><span>Keterangan</span><span>Mutasi</span><span>Saldo fisik</span></div>{movementRows.map((row)=><article key={row.ref}><span><strong>{row.ref}</strong><small>{row.date}</small></span><span>{row.note}</span><b className={row.delta<0?'negative':row.delta>0?'positive':''}>{row.delta>0?'+':''}{formatNumber(row.delta,0)} {selected.unit}</b><strong>{formatNumber(row.balance,0)} {selected.unit}</strong></article>)}</section>
        </main>
      </div>
    </div>
  </>
}

function FinishedGoodsSummaryPage() {
  const brands = [...new Set(productCatalog.map((item)=>item.brand))]
  const grades = [...new Set(productCatalog.map((item)=>item.grade))]
  const locations = [...new Set(productCatalog.map((item)=>item.location))]
  const [query,setQuery] = useState('')
  const [brand,setBrand] = useState('Semua')
  const [grade,setGrade] = useState('Semua')
  const [location,setLocation] = useState('Semua')
  const [selectedKey,setSelectedKey] = useState(`${productCatalog[0].brand}::${productCatalog[0].code}`)
  const visible = useMemo(()=>productCatalog.filter((item)=>`${item.brand} ${item.code} ${item.name} ${item.color} ${item.range}`.toLowerCase().includes(query.toLowerCase()) && (brand==='Semua'||item.brand===brand) && (grade==='Semua'||item.grade===grade) && (location==='Semua'||item.location===location)),[query,brand,grade,location])
  const selected = productCatalog.find((item)=>`${item.brand}::${item.code}`===selectedKey) ?? productCatalog[0]
  const total = selected.stocks.reduce((sum,qty)=>sum+qty,0)
  const totalAll = productCatalog.reduce((sum,item)=>sum+item.stocks.reduce((acc,qty)=>acc+qty,0),0)
  const brandTotals = brands.map((name)=>({name,total:productCatalog.filter((item)=>item.brand===name).reduce((sum,item)=>sum+item.stocks.reduce((acc,qty)=>acc+qty,0),0)}))
  return <>
    <section className="hero-copy compact wh-hero"><div><div className="eyebrow">GUDANG · BARANG JADI</div><h1>Ringkasan Barang Jadi</h1><p>Browse merek → SKU → size. Ringkasan ini untuk melihat posisi stok; histori kronologis tetap berada di Kartu Stok dan Buku Mutasi.</p></div><div className="wh-rule"><PackageCheck/><div><span>SATU SUMBER SALDO</span><strong>Ledger FG, bukan hitungan manual</strong><small>Grade dan lokasi tetap menjadi dimensi terpisah.</small></div></div></section>
    <section className="wh-metrics"><MetricCard label="Seluruh FG" value={`${formatNumber(totalAll,0)} pcs`} note="Semua grade · 8 SKU" icon={PackageCheck}/><MetricCard label="Grade Good" value="1.074 pcs" note="Siap alokasi penjualan" tone="good" icon={Check}/><MetricCard label="Grade BS" value="216 pcs" note="Tidak ikut stok siap jual" tone="danger" icon={AlertTriangle}/><MetricCard label="Lokasi aktif" value="2 gudang" note="Utama & Cadangan" icon={Warehouse}/></section>
    <div className="panel wh-workspace"><div className="wh-toolbar"><SearchBox value={query} onChange={setQuery} placeholder="Cari merek, SKU, model, warna..."/><SelectFilter label="Merek" value={brand} options={brands} onChange={setBrand}/><SelectFilter label="Grade" value={grade} options={grades} onChange={setGrade}/><SelectFilter label="Lokasi" value={location} options={locations} onChange={setLocation}/><button className="wh-reset" onClick={()=>{setQuery('');setBrand('Semua');setGrade('Semua');setLocation('Semua')}}><RotateCcw/> Reset</button></div>
      <div className="wh-brand-strip">{brandTotals.map((item)=><button key={item.name} className={brand===item.name?'active':''} onClick={()=>setBrand(brand===item.name?'Semua':item.name)}><span>{item.name}</span><strong>{item.total} pcs</strong><small>{productCatalog.filter((product)=>product.brand===item.name).length} SKU</small></button>)}</div>
      <div className="wh-master-detail fg"><aside className="wh-browser"><header><div><span>BROWSE SKU</span><strong>{visible.length} SKU tampil</strong></div><small>Pilih untuk breakdown</small></header><div className="wh-browser-list">{visible.map((item)=>{const itemTotal=item.stocks.reduce((sum,qty)=>sum+qty,0);const key=`${item.brand}::${item.code}`;return <button key={key} className={selectedKey===key?'active':''} onClick={()=>setSelectedKey(key)}><span className="wh-index">{item.brand.slice(0,1)}</span><div><strong>{item.brand} · {item.code}</strong><small>{item.name} · {item.color}</small><em>{item.range} · {item.location}</em></div><b>{itemTotal} pcs</b><StatusBadge tone={item.grade==='Good'?'good':'danger'}>{item.grade}</StatusBadge></button>})}{visible.length===0&&<EmptyResult title="SKU tidak ditemukan" note="Ubah merek, grade, lokasi, atau pencarian."/>}</div></aside>
        <main className="wh-detail"><header className="wh-detail-head"><div><span>SKU TERPILIH</span><h2>{selected.brand} · {selected.code}</h2><p>{selected.name} · {selected.color} · Range {selected.range}</p></div><div className="wh-detail-total"><span>SALDO SKU</span><strong>{total} pcs</strong><small>{selected.location} · Grade {selected.grade}</small></div></header>
          <div className="wh-fg-size-grid">{selected.sizes.map((size,index)=><article key={size}><span>SIZE</span><strong>{size}</strong><div><small>SALDO</small><b>{selected.stocks[index]} pcs</b></div><div><small>LUSIN / POTONG</small><b>{Math.floor(selected.stocks[index]/12)} lusin · {selected.stocks[index]%12} potong</b></div><em className={selected.stocks[index]<45?'warn':'good'}>{selected.stocks[index]<45?'Perlu dipantau':'Stok aman'}</em></article>)}</div>
          <section className="wh-fg-location"><header><div><span>POSISI STOK</span><strong>Lokasi dan grade tidak dicampur</strong></div><button>Buka kartu stok <ArrowRight/></button></header><div><article><MapPin/><span><small>LOKASI</small><strong>{selected.location}</strong><em>Bin FG-{selected.brand==='Vivo'?'A':'B'}-{selected.code.slice(-2)}</em></span><b>{total} pcs</b></article><article><ShieldCheck/><span><small>GRADE</small><strong>{selected.grade}</strong><em>{selected.grade==='Good'?'Boleh dialokasikan ke penjualan':'Masuk jalur BS / rework'}</em></span><b>{selected.grade==='Good'?'READY':'HOLD'}</b></article></div></section>
        </main></div>
    </div>
  </>
}

function ReturnsAdjustmentsPage() {
  const [mode,setMode] = useState<'browse'|'draft'>('browse')
  const [query,setQuery] = useState('')
  const [type,setType] = useState('Semua')
  const [status,setStatus] = useState('Semua')
  const [selectedId,setSelectedId] = useState(warehouseCases[0].id)
  const [draftType,setDraftType] = useState<WarehouseCase['type']>('Retur Mandor')
  const [draftLines,setDraftLines] = useState([{item:'LCY-029',unit:'yd',system:'0',physical:'18,5'},{item:'',unit:'pcs',system:'0',physical:''}])
  const [draftNotice,setDraftNotice] = useState('')
  const visible = useMemo(()=>warehouseCases.filter((item)=>`${item.id} ${item.type} ${item.subject} ${item.identity} ${item.actor} ${item.source}`.toLowerCase().includes(query.toLowerCase()) && (type==='Semua'||item.type===type) && (status==='Semua'||item.status===status)),[query,type,status])
  const selected = warehouseCases.find((item)=>item.id===selectedId) ?? warehouseCases[0]
  const parseDraft = (value:string) => Number(value.replace(',','.'))||0
  const updateLine = (index:number,key:'item'|'unit'|'system'|'physical',value:string)=>setDraftLines((rows)=>rows.map((row,rowIndex)=>rowIndex===index?{...row,[key]:value}:row))
  return <>
    <section className="hero-copy compact wh-hero"><div><div className="eyebrow">GUDANG · KONTROL STOK</div><h1>Retur & Penyesuaian</h1><p>Retur menambah barang yang benar-benar kembali. Opname dan penyesuaian hanya mengubah ledger setelah alasan, bukti, serta angka sebelum–sesudah direview.</p></div><div className="wh-rule strict"><ShieldCheck/><div><span>GUARDRAIL</span><strong>Tidak ada edit saldo langsung</strong><small>Selalu draft → review → posting berjejak.</small></div></div></section>
    <section className="wh-metrics"><MetricCard label="Menunggu review" value="2 kasus" note="Belum mengubah saldo" tone="warn" icon={ClipboardCheck}/><MetricCard label="Selisih opname" value="12 pcs" note="Kancing Jeans 17 mm" tone="danger" icon={AlertTriangle}/><MetricCard label="Retur hari ini" value="18,5 yd" note="1 roll dari Mandor Asep" tone="good" icon={RotateCcw}/><MetricCard label="Selesai 7 hari" value="14 kasus" note="Semua punya sumber & alasan" icon={History}/></section>
    <div className="panel wh-workspace adjustments"><div className="wh-mode-tabs"><button className={mode==='browse'?'active':''} onClick={()=>setMode('browse')}><History/> Daftar kasus <b>{warehouseCases.length}</b></button><button className={mode==='draft'?'active':''} onClick={()=>setMode('draft')}><Plus/> Buat draft baru</button></div>
      {mode==='browse'?<><div className="wh-toolbar"><SearchBox value={query} onChange={setQuery} placeholder="Cari kasus, item, mandor, sumber..."/><SelectFilter label="Jenis" value={type} options={[...new Set(warehouseCases.map((item)=>item.type))]} onChange={setType}/><SelectFilter label="Status" value={status} options={[...new Set(warehouseCases.map((item)=>item.status))]} onChange={setStatus}/><button className="wh-reset" onClick={()=>{setQuery('');setType('Semua');setStatus('Semua')}}><RotateCcw/> Reset</button></div><div className="wh-master-detail cases"><aside className="wh-browser"><header><div><span>BROWSE KASUS</span><strong>{visible.length} kasus tampil</strong></div><small>Terbaru dulu</small></header><div className="wh-browser-list">{visible.map((item)=><button key={item.id} className={selected.id===item.id?'active':''} onClick={()=>setSelectedId(item.id)}><span className="wh-index">{item.type==='Retur Mandor'?'RT':item.type==='Stock Opname'?'OP':'AD'}</span><div><strong>{item.subject}</strong><small>{item.id} · {item.type}</small><em>{item.actor} · {item.happenedAt}</em></div><b>{item.identity.split(' · ').slice(-1)}</b><StatusBadge>{item.status}</StatusBadge></button>)}{visible.length===0&&<EmptyResult title="Kasus tidak ditemukan" note="Ubah filter jenis/status atau reset pencarian."/>}</div></aside><CaseDetail selected={selected}/></div></>:<DraftAdjustment draftType={draftType} setDraftType={setDraftType} lines={draftLines} updateLine={updateLine} addLine={()=>setDraftLines((rows)=>[...rows,{item:'',unit:'pcs',system:'0',physical:''}])} parseDraft={parseDraft} notice={draftNotice} onReview={()=>setDraftNotice('Draft simulasi siap direview. Saldo belum berubah dan belum dikirim ke backend.')}/>} 
    </div>
  </>
}

function CaseDetail({ selected }: { selected: WarehouseCase }) {
  const totalRecorded=selected.lines.reduce((sum,line)=>sum+line.recorded,0)
  const totalPhysical=selected.lines.reduce((sum,line)=>sum+line.physical,0)
  const delta=totalPhysical-totalRecorded
  return <main className="wh-detail case-detail"><header className="wh-detail-head"><div><span>{selected.type.toUpperCase()}</span><h2>{selected.subject}</h2><p>{selected.id} · {selected.happenedAt}</p></div><StatusBadge>{selected.status}</StatusBadge></header><div className="wh-case-facts"><div><span>PELAKU / SUMBER</span><strong>{selected.actor}</strong><small>{selected.source}</small></div><div><span>LOKASI</span><strong>{selected.location}</strong><small>Lokasi fisik pemeriksaan</small></div><div><span>IDENTITAS BARANG</span><strong>{selected.identity}</strong><small>Jangan ganti item setelah review</small></div></div><div className="wh-ledger-equation"><span><small>SALDO TERCATAT</small><strong>{formatNumber(totalRecorded)}</strong></span><i>{delta>=0?'+':'−'}</i><span className={delta===0?'neutral':delta>0?'positive':'negative'}><small>PERUBAHAN</small><strong>{delta>0?'+':''}{formatNumber(delta)}</strong></span><i>=</i><span><small>SALDO SESUDAH</small><strong>{formatNumber(totalPhysical)}</strong></span></div><section className="wh-case-lines"><header><span>RINCIAN BARIS</span><small>Per item / roll / size</small></header><div className="wh-case-line-head"><span>Item</span><span>Sebelum</span><span>Fisik / kembali</span><span>Perubahan</span></div>{selected.lines.map((line)=><article key={line.label}><strong>{line.label}</strong><span>{formatNumber(line.recorded)} {line.unit}</span><span>{formatNumber(line.physical)} {line.unit}</span><b className={line.physical-line.recorded<0?'negative':line.physical-line.recorded>0?'positive':''}>{line.physical-line.recorded>0?'+':''}{formatNumber(line.physical-line.recorded)} {line.unit}</b></article>)}</section><div className="wh-case-note"><FileClock/><div><span>CATATAN & AUDIT</span><strong>{selected.note}</strong><small>Saldo hanya berubah setelah dokumen ini diposting oleh user berwenang.</small></div></div><footer className="wh-case-actions"><button className="soft-btn">Lihat dokumen sumber</button><button className="primary-btn" disabled={selected.status==='Selesai'}>{selected.status==='Selesai'?'Sudah diposting':'Review sebelum posting'} <ArrowRight/></button></footer></main>
}

function DraftAdjustment({ draftType, setDraftType, lines, updateLine, addLine, parseDraft, notice, onReview }: { draftType: WarehouseCase['type']; setDraftType:(value:WarehouseCase['type'])=>void; lines:Array<{item:string;unit:string;system:string;physical:string}>; updateLine:(index:number,key:'item'|'unit'|'system'|'physical',value:string)=>void; addLine:()=>void; parseDraft:(value:string)=>number; notice:string; onReview:()=>void }) {
  const validLines=lines.filter((line)=>line.item.trim()&&line.physical.trim())
  const totalDelta=validLines.reduce((sum,line)=>sum+parseDraft(line.physical)-parseDraft(line.system),0)
  return <div className="wh-draft"><header><div><span>DRAFT BARU · BELUM MENGUBAH STOK</span><h2>{draftType}</h2><p>Pilih kejadian fisik yang benar. Jenis dokumen menentukan guardrail review, bukan sekadar label laporan.</p></div><div className="wh-draft-type">{(['Retur Mandor','Stock Opname','Penyesuaian'] as const).map((item)=><button key={item} className={draftType===item?'active':''} onClick={()=>setDraftType(item)}>{item}</button>)}</div></header><div className="wh-draft-meta"><label><span>SUMBER / REFERENSI</span><input placeholder={draftType==='Retur Mandor'?'POT / batch / mandor':'Nomor sesi / dokumen sumber'}/></label><label><span>LOKASI PEMERIKSAAN</span><select><option>Area Retur</option><option>Rak Kain A</option><option>Aksesori A-01</option><option>Gudang FG Utama</option></select></label><label><span>WAKTU FISIK</span><input type="datetime-local" defaultValue="2026-08-28T10:30"/></label></div><section className="wh-draft-lines" data-keyboard-grid><header><div><span>BARIS BARANG</span><strong>Enter turun · panah pindah sel</strong></div><button onClick={addLine}><Plus/> Tambah baris</button></header><div className="wh-draft-line-head"><span>Item / roll / SKU-size</span><span>Unit</span><span>Saldo sistem</span><span>Fisik / kembali</span><span>Selisih</span></div>{lines.map((line,index)=>{const delta=parseDraft(line.physical)-parseDraft(line.system);return <div className="wh-draft-line" key={index}><input data-grid-row={index} data-grid-col={0} value={line.item} onChange={(event)=>updateLine(index,'item',event.target.value)} placeholder="Cari item atau scan roll..."/><select value={line.unit} onChange={(event)=>updateLine(index,'unit',event.target.value)}><option>yd</option><option>pcs</option><option>meter</option><option>set</option></select><input data-grid-row={index} data-grid-col={1} value={line.system} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateLine(index,'system',event.target.value)} inputMode="decimal" placeholder="0"/><input data-grid-row={index} data-grid-col={2} value={line.physical} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>updateLine(index,'physical',event.target.value)} inputMode="decimal" placeholder="0"/><strong className={delta<0?'negative':delta>0?'positive':''}>{delta>0?'+':''}{formatNumber(delta)}</strong></div>})}</section><div className="wh-draft-bottom"><label><span>ALASAN & KONDISI FISIK</span><textarea placeholder="Contoh: sisa roll kembali utuh, sudah ukur ulang 18,5 yd..."/></label><div className="wh-draft-review"><span>TOTAL PERUBAHAN DRAFT</span><strong className={totalDelta<0?'negative':totalDelta>0?'positive':''}>{totalDelta>0?'+':''}{formatNumber(totalDelta)}</strong><small>{validLines.length} baris siap direview · belum posting</small><button className="primary-btn" disabled={validLines.length===0} onClick={onReview}>Review draft <ArrowRight/></button></div></div>{notice&&<div className="wh-inline-note good"><Check/><div><strong>Review lokal terbentuk</strong><small>{notice}</small></div></div>}</div>
}

import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Boxes, CalendarClock, CheckCircle2, Clock3,
  Coins, Database, History, Layers3, LockKeyhole, Package, Pencil, Plus,
  Ruler, Search, ShieldCheck, Tag, X,
} from 'lucide-react'
import { cleanMoneyInput, formatMoneyInput } from './moneyInput'
import './material-master.css'

export type MaterialMasterView='master-fabric'|'master-accessory'
type Props={view:MaterialMasterView}
type PriceHistory={id:string;amount:number;uom?:string;effectiveFrom:string;effectiveTo?:string;note:string;status:'CURRENT'|'SUPERSEDED'|'CANCELLED'}
type FabricMaster={id:string;code:string;name:string;family:string;defaultUom:string;active:boolean;rowVersion:number;benchmark:PriceHistory[]}
type AccessoryMaster={id:string;code:string;name:string;category:string;stockUom:string;purchaseUom:string;conversion:number;movingAverage:number;stock:number;active:boolean;rowVersion:number;specialPrices:PriceHistory[]}
type AccessoryRate={category:string;sellingPrices:PriceHistory[];reimbursementPrices:PriceHistory[]}
type ConversionHistory={id:string;factor:number|null;effectiveFrom:string;effectiveTo?:string;note:string;status:'CURRENT'|'SUPERSEDED'}
type UomMaster={code:string;name:string;family:'COUNT'|'LENGTH'|'WEIGHT';baseUom:string;mode:'BASE'|'FIXED'|'VARIABLE';active:boolean;rowVersion:number;conversions:ConversionHistory[]}

const fabricSeeds:FabricMaster[]=[
  {id:'fab-1069',code:'FAB-1069-ORI',name:'Denim 1069 Ori',family:'Denim Medium',defaultUom:'yard',active:true,rowVersion:6,benchmark:[{id:'bp-1069-03',amount:58_500,effectiveFrom:'2026-08-01',note:'Benchmark supplier utama Agustus',status:'CURRENT'},{id:'bp-1069-02',amount:56_750,effectiveFrom:'2026-05-01',effectiveTo:'2026-07-31',note:'Benchmark Mei–Juli',status:'SUPERSEDED'}]},
  {id:'fab-lucy',code:'FAB-LUCY',name:'Lucy',family:'Denim Stretch',defaultUom:'yard',active:true,rowVersion:4,benchmark:[{id:'bp-lucy-02',amount:52_500,effectiveFrom:'2026-08-15',note:'Rata-rata quotation dua supplier',status:'CURRENT'},{id:'bp-lucy-01',amount:50_000,effectiveFrom:'2026-04-01',effectiveTo:'2026-08-14',note:'Benchmark awal',status:'SUPERSEDED'}]},
  {id:'fab-zodiak',code:'FAB-ZODIAK-KW',name:'Zodiak KW',family:'Denim Light',defaultUom:'meter',active:true,rowVersion:8,benchmark:[{id:'bp-zdk-04',amount:51_700,effectiveFrom:'2026-07-01',note:'Benchmark Q3 per meter',status:'CURRENT'}]},
]
const accessorySeeds:AccessoryMaster[]=[
  {id:'acc-btn-silver',code:'ACC-BTN-017-SLV',name:'Kancing Jeans 17 mm · Silver',category:'Kancing',stockUom:'pcs',purchaseUom:'gross',conversion:144,movingAverage:620,stock:4800,active:true,rowVersion:7,specialPrices:[{id:'special-btn-silver-01',amount:0,uom:'pcs',effectiveFrom:'2026-08-29',note:'Default gratis untuk Mandor Special',status:'CURRENT'}]},
  {id:'acc-btn-metal',code:'ACC-BTN-017-MTL',name:'Kancing Jeans 17 mm · Metal',category:'Kancing',stockUom:'pcs',purchaseUom:'gross',conversion:144,movingAverage:690,stock:3200,active:true,rowVersion:5,specialPrices:[{id:'special-btn-metal-01',amount:0,uom:'pcs',effectiveFrom:'2026-08-29',note:'Default gratis untuk Mandor Special',status:'CURRENT'}]},
  {id:'acc-zip-14',code:'ACC-ZIP-014-BLK',name:'Resleting 14 cm · Black',category:'Resleting',stockUom:'pcs',purchaseUom:'lusin',conversion:12,movingAverage:5200,stock:2200,active:true,rowVersion:9,specialPrices:[{id:'special-zip-14-01',amount:0,uom:'pcs',effectiveFrom:'2026-08-29',note:'Default gratis untuk Mandor Special',status:'CURRENT'}]},
  {id:'acc-label-vivo',code:'ACC-LBL-VIVO',name:'Label Woven Vivo',category:'Label',stockUom:'pcs',purchaseUom:'roll',conversion:1000,movingAverage:530,stock:8000,active:true,rowVersion:3,specialPrices:[{id:'special-label-vivo-01',amount:0,uom:'pcs',effectiveFrom:'2026-08-29',note:'Default gratis untuk Mandor Special',status:'CURRENT'}]},
]
const accessoryRateSeeds:AccessoryRate[]=[
  {category:'Kancing',sellingPrices:[{id:'sell-btn-02',amount:495,uom:'pcs',effectiveFrom:'2026-08-01',note:'Tagihan kategori ke mandor',status:'CURRENT'},{id:'sell-btn-01',amount:475,uom:'pcs',effectiveFrom:'2026-04-01',effectiveTo:'2026-07-31',note:'Harga kategori lama',status:'SUPERSEDED'}],reimbursementPrices:[{id:'reim-btn-02',amount:500,uom:'pcs',effectiveFrom:'2026-08-01',note:'Buffer defect pabrik',status:'CURRENT'}]},
  {category:'Resleting',sellingPrices:[{id:'sell-zip-02',amount:29_900,uom:'lusin',effectiveFrom:'2026-08-01',note:'Mandor membeli per lusin',status:'CURRENT'}],reimbursementPrices:[{id:'reim-zip-02',amount:2_500,uom:'pcs',effectiveFrom:'2026-08-01',note:'Reimburse per Good FG',status:'CURRENT'}]},
  {category:'Label',sellingPrices:[{id:'sell-label-02',amount:750,uom:'pcs',effectiveFrom:'2026-06-01',note:'Tagihan kategori label',status:'CURRENT'}],reimbursementPrices:[{id:'reim-label-02',amount:800,uom:'pcs',effectiveFrom:'2026-06-01',note:'Reimburse standar BOM',status:'CURRENT'}]},
]
const uomSeeds:UomMaster[]=[
  {code:'PCS',name:'Piece',family:'COUNT',baseUom:'PCS',mode:'BASE',active:true,rowVersion:4,conversions:[{id:'pcs-1',factor:1,effectiveFrom:'2026-01-01',note:'Base unit count',status:'CURRENT'}]},
  {code:'LUSIN',name:'Lusin',family:'COUNT',baseUom:'PCS',mode:'FIXED',active:true,rowVersion:5,conversions:[{id:'doz-2',factor:12,effectiveFrom:'2026-01-01',note:'Konversi tetap',status:'CURRENT'}]},
  {code:'GROSS',name:'Gross',family:'COUNT',baseUom:'PCS',mode:'FIXED',active:true,rowVersion:3,conversions:[{id:'gross-1',factor:144,effectiveFrom:'2026-01-01',note:'12 lusin',status:'CURRENT'}]},
  {code:'PACK',name:'Pack',family:'COUNT',baseUom:'PCS',mode:'VARIABLE',active:true,rowVersion:2,conversions:[{id:'pack-1',factor:null,effectiveFrom:'2026-01-01',note:'Isi dicatat per transaksi',status:'CURRENT'}]},
  {code:'BOX',name:'Box',family:'COUNT',baseUom:'PCS',mode:'VARIABLE',active:true,rowVersion:2,conversions:[{id:'box-1',factor:null,effectiveFrom:'2026-01-01',note:'Isi dicatat per transaksi',status:'CURRENT'}]},
  {code:'METER',name:'Meter',family:'LENGTH',baseUom:'METER',mode:'BASE',active:true,rowVersion:4,conversions:[{id:'meter-1',factor:1,effectiveFrom:'2026-01-01',note:'Base unit panjang',status:'CURRENT'}]},
  {code:'YARD',name:'Yard',family:'LENGTH',baseUom:'METER',mode:'FIXED',active:true,rowVersion:6,conversions:[{id:'yard-2',factor:.9144,effectiveFrom:'2026-01-01',note:'Konversi panjang standar',status:'CURRENT'}]},
  {code:'ROLL',name:'Roll',family:'LENGTH',baseUom:'METER',mode:'VARIABLE',active:true,rowVersion:3,conversions:[{id:'roll-1',factor:null,effectiveFrom:'2026-01-01',note:'Panjang aktual per roll',status:'CURRENT'}]},
  {code:'KG',name:'Kilogram',family:'WEIGHT',baseUom:'KG',mode:'BASE',active:true,rowVersion:2,conversions:[{id:'kg-1',factor:1,effectiveFrom:'2026-01-01',note:'Base unit berat',status:'CURRENT'}]},
]

const money=(value:number)=>new Intl.NumberFormat('id-ID',{style:'currency',currency:'IDR',maximumFractionDigits:0}).format(value)
const currentPrice=(history:PriceHistory[])=>history.find((item)=>item.status==='CURRENT')?.amount??0
const currentPriceEntry=(history:PriceHistory[])=>history.find((item)=>item.status==='CURRENT')
const currentConversion=(uom:UomMaster)=>uom.conversions.find((item)=>item.status==='CURRENT')

function StatePill({active}:{active:boolean}){return <em className={`mm-state ${active?'active':'inactive'}`}>{active?'AKTIF':'NONAKTIF'}</em>}
function MasterHero({title,description,kind}:{title:string;description:string;kind:string}){return <section className="hero-copy compact mm-hero"><div><div className="eyebrow">MASTER DATA · {kind}</div><h1>{title}</h1><p>{description}</p></div><div className="mm-contract"><ShieldCheck/><span><small>SAFE WRITER v2</small><strong>Idempotency · row-version · effective date</strong><em>Dipakai sebagai simulasi sampai Auth tersambung.</em></span></div></section>}

export default function MaterialMasterPages({view}:Props){return view==='master-fabric'?<FabricWorkspace/>:<AccessoryWorkspace/>}

function FabricWorkspace(){
  const [fabrics,setFabrics]=useState(fabricSeeds)
  const [selectedId,setSelectedId]=useState(fabricSeeds[0].id)
  const [query,setQuery]=useState('')
  const [benchmarkOpen,setBenchmarkOpen]=useState(false)
  const [editMode,setEditMode]=useState<'create'|'edit'|null>(null)
  const [editCode,setEditCode]=useState('')
  const [editName,setEditName]=useState('')
  const [editFamily,setEditFamily]=useState('')
  const [editUom,setEditUom]=useState('yard')
  const [editActive,setEditActive]=useState(true)
  const [price,setPrice]=useState('')
  const [effective,setEffective]=useState('2026-08-28')
  const [note,setNote]=useState('')
  const [notice,setNotice]=useState('')
  const selected=fabrics.find((item)=>item.id===selectedId)??fabrics[0]
  const visible=useMemo(()=>fabrics.filter((item)=>`${item.code} ${item.name} ${item.family}`.toLowerCase().includes(query.toLowerCase())),[fabrics,query])
  const benchmark=currentPrice(selected.benchmark)
  const saveBenchmark=()=>{
    const amount=Number(price.replace(/\D/g,''))
    setFabrics((current)=>current.map((fabric)=>fabric.id===selected.id?{...fabric,rowVersion:fabric.rowVersion+1,benchmark:[{id:`bp-sim-${Date.now()}`,amount,effectiveFrom:effective,note:note.trim(),status:'CURRENT'},...fabric.benchmark.map((item)=>item.status==='CURRENT'?{...item,status:'SUPERSEDED' as const,effectiveTo:effective}:item)]}:fabric))
    setBenchmarkOpen(false);setNotice(`Benchmark ${money(amount)}/${selected.defaultUom} tersimpan sebagai simulasi. Receipt berikutnya boleh memakai estimate ini; invoice final tetap menang.`)
  }
  const openFabricEditor=(mode:'create'|'edit')=>{
    setEditMode(mode)
    setEditCode(mode==='create'?'':selected.code);setEditName(mode==='create'?'':selected.name);setEditFamily(mode==='create'?'':selected.family);setEditUom(mode==='create'?'yard':selected.defaultUom);setEditActive(mode==='create'||selected.active)
  }
  const saveFabric=()=>{
    if(editMode==='create'){
      const next:FabricMaster={id:`fab-sim-${Date.now()}`,code:editCode.trim(),name:editName.trim(),family:editFamily.trim(),defaultUom:editUom.trim(),active:editActive,rowVersion:1,benchmark:[]}
      setFabrics((current)=>[next,...current]);setSelectedId(next.id);setNotice(`${next.name} dibuat sebagai draft master simulasi. Tambahkan benchmark bila kain ini dipakai untuk receipt provisional.`)
    }else{
      setFabrics((current)=>current.map((fabric)=>fabric.id===selected.id?{...fabric,code:editCode.trim(),name:editName.trim(),family:editFamily.trim(),defaultUom:editUom.trim(),active:editActive,rowVersion:fabric.rowVersion+1}:fabric))
      setNotice(`${editName.trim()} diperbarui sebagai simulasi. Histori benchmark dan transaksi tetap utuh.`)
    }
    setEditMode(null)
  }
  return <>
    <MasterHero kind="KAIN" title="Kain & Benchmark Harga" description="Master identitas kain dipisah dari harga. Benchmark berlaku berdasarkan waktu untuk GRNI dan estimasi HPP; invoice supplier final tidak pernah ditimpa benchmark."/>
    <section className="mm-metrics"><article><span>MASTER AKTIF</span><strong>{fabrics.filter((item)=>item.active).length}</strong><small>Identitas kain siap dipakai</small></article><article><span>BENCHMARK BERLAKU</span><strong>{fabrics.filter((item)=>currentPrice(item.benchmark)>0).length}</strong><small>Effective-dated estimate</small></article><article><span>FINAL AP PRICE</span><strong>Invoice supplier</strong><small>Bukan benchmark master</small></article><article><span>HARD DELETE</span><strong>Dilarang</strong><small>Nonaktifkan bila tak dipakai</small></article></section>
    <section className="panel mm-layout"><aside><header><div><span>BROWSER KAIN</span><strong>{visible.length} master</strong></div><Layers3/></header><label className="mm-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari kode, nama, family..."/></label><div>{visible.map((fabric)=><button className={fabric.id===selected.id?'active':''} key={fabric.id} onClick={()=>{setSelectedId(fabric.id);setNotice('')}}><i><Ruler/></i><span><strong>{fabric.name}</strong><small>{fabric.code} · {fabric.family}</small><em>{currentPrice(fabric.benchmark)>0?`${money(currentPrice(fabric.benchmark))}/${fabric.defaultUom}`:'Benchmark belum ada'}</em></span><StatePill active={fabric.active}/></button>)}</div><footer><button onClick={()=>openFabricEditor('create')}><Plus/> Tambah kain</button><small>Record baru dimulai tanpa histori atau harga terselubung.</small></footer></aside><main>
      <header className="mm-detail-head"><div><span>IDENTITAS KAIN</span><h2>{selected.name}</h2><p>{selected.code} · {selected.family}</p></div><div><StatePill active={selected.active}/><small>row version {selected.rowVersion}</small></div></header>
      <div className="mm-identity"><article><Database/><span><small>MASTER CODE</small><strong>{selected.code}</strong></span></article><article><Layers3/><span><small>FAMILY / KATEGORI</small><strong>{selected.family}</strong></span></article><article><Ruler/><span><small>DEFAULT UOM</small><strong>{selected.defaultUom}</strong></span></article></div>
      <section className="mm-price-hero"><div><span>BENCHMARK CURRENT</span><h3>{benchmark>0?money(benchmark):'Belum ditetapkan'} {benchmark>0&&<small>/ {selected.defaultUom}</small>}</h3><p>{benchmark>0?`Berlaku ${selected.benchmark.find((item)=>item.status==='CURRENT')?.effectiveFrom} · estimate receipt/GRNI saja`:'Receipt baru wajib memakai harga manual yang direview sampai benchmark tersedia.'}</p></div><button className="primary-btn" onClick={()=>{setPrice(benchmark>0?String(benchmark):'');setNote('');setBenchmarkOpen(true)}}><Coins/> {benchmark>0?'Set harga penerus':'Set benchmark pertama'}</button></section>
      <div className="mm-rule"><AlertTriangle/><span><strong>Benchmark bukan harga hutang supplier.</strong><small>Penerimaan memakai benchmark untuk provisional cost. Invoice final melakukan match receipt dan recost kronologis; AP selalu mengikuti invoice final.</small></span></div>
      <section className="mm-history"><header><div><span>PRICE HISTORY</span><strong>Versi harga berdasarkan waktu</strong></div><History/></header><div className="mm-history-head"><span>Effective</span><span>Harga / UOM</span><span>Catatan</span><span>Status</span></div>{selected.benchmark.map((item)=><article key={item.id}><span><strong>{item.effectiveFrom}</strong><small>{item.effectiveTo?`s.d. ${item.effectiveTo}`:'Tanpa akhir'}</small></span><b>{money(item.amount)} / {selected.defaultUom}</b><span>{item.note}</span><em className={item.status.toLowerCase()}>{item.status}</em></article>)}</section>
      {notice&&<div className="mm-notice"><CheckCircle2/> {notice}</div>}
      <footer className="mm-actions"><span><LockKeyhole/> Record yang sudah dipakai tidak dihapus.</span><button className="soft-btn" onClick={()=>openFabricEditor('edit')}><Pencil/> Edit / nonaktifkan</button></footer>
    </main></section>
    {benchmarkOpen&&<MasterModal title="Set benchmark harga penerus" description={`${selected.name} · ${selected.code}`} onClose={()=>setBenchmarkOpen(false)} action={saveBenchmark} disabled={Number(price.replace(/\D/g,''))<=0||!effective||note.trim().length<4} actionLabel="Simpan simulasi"><div className="mm-form-grid"><label><span>HARGA / {selected.defaultUom.toUpperCase()}</span><div><b>Rp</b><input autoFocus inputMode="numeric" value={formatMoneyInput(price)} onChange={(event)=>setPrice(cleanMoneyInput(event.target.value))}/></div></label><label><span>BERLAKU MULAI</span><input type="date" value={effective} onChange={(event)=>setEffective(event.target.value)}/></label></div><label className="mm-modal-note"><span>CATATAN SINGKAT</span><textarea value={note} onChange={(event)=>setNote(event.target.value)} placeholder="Sumber benchmark / alasan perubahan..."/></label><div className="mm-modal-impact"><Clock3/><span><strong>Versi lama tidak ditimpa</strong><small>Harga current ditutup pada tanggal penerus; transaksi lampau tetap memakai snapshot yang berlaku saat itu.</small></span></div></MasterModal>}
    {editMode&&<MasterModal title={editMode==='create'?'Tambah master kain':'Edit identitas kain'} description={editMode==='create'?'Master baru dimulai aktif tanpa benchmark.':'Perubahan identitas memakai row-version; histori harga tetap terpisah.'} onClose={()=>setEditMode(null)} action={saveFabric} disabled={!editCode.trim()||!editName.trim()||!editFamily.trim()||!editUom.trim()} actionLabel={editMode==='create'?'Buat draft simulasi':'Simpan perubahan simulasi'}><div className="mm-form-grid three"><label><span>KODE</span><input autoFocus value={editCode} onChange={(event)=>setEditCode(event.target.value)}/></label><label><span>NAMA KAIN</span><input value={editName} onChange={(event)=>setEditName(event.target.value)}/></label><label><span>FAMILY</span><input value={editFamily} onChange={(event)=>setEditFamily(event.target.value)}/></label><label><span>DEFAULT UOM</span><select value={editUom} onChange={(event)=>setEditUom(event.target.value)}><option value="yard">Yard (yd)</option><option value="meter">Meter (m)</option></select></label><label><span>STATUS</span><select value={editActive?'ACTIVE':'INACTIVE'} onChange={(event)=>setEditActive(event.target.value==='ACTIVE')}><option value="ACTIVE">Aktif</option><option value="INACTIVE">Nonaktif</option></select></label></div><div className="mm-modal-impact warn"><AlertTriangle/><span><strong>Tidak ada tombol hard delete</strong><small>Nonaktif hanya mencegah pemakaian baru. Receipt, GRNI, HPP, dan invoice lama tetap terhubung ke master ini.</small></span></div></MasterModal>}
  </>
}

function AccessoryWorkspace(){
  const [workspace,setWorkspace]=useState<'ACCESSORY'|'UOM'>('ACCESSORY')
  const [items,setItems]=useState(accessorySeeds)
  const [rates,setRates]=useState(accessoryRateSeeds)
  const [selectedId,setSelectedId]=useState(accessorySeeds[0].id)
  const [query,setQuery]=useState('')
  const [category,setCategory]=useState('ALL')
  const [priceOpen,setPriceOpen]=useState(false)
  const [priceKind,setPriceKind]=useState<'SELLING'|'REIMBURSEMENT'|'SPECIAL'>('SELLING')
  const [historyKind,setHistoryKind]=useState<'SELLING'|'REIMBURSEMENT'|'SPECIAL'>('SELLING')
  const [editMode,setEditMode]=useState<'create'|'edit'|null>(null)
  const [categoryOpen,setCategoryOpen]=useState(false)
  const [extraCategories,setExtraCategories]=useState<string[]>([])
  const [newCategory,setNewCategory]=useState('')
  const [editCode,setEditCode]=useState('')
  const [editName,setEditName]=useState('')
  const [editCategory,setEditCategory]=useState('Kancing')
  const [editStockUom,setEditStockUom]=useState('pcs')
  const [editPurchaseUom,setEditPurchaseUom]=useState('lusin')
  const [editConversion,setEditConversion]=useState('12')
  const [editActive,setEditActive]=useState(true)
  const [price,setPrice]=useState('')
  const [priceUom,setPriceUom]=useState('pcs')
  const [effective,setEffective]=useState('2026-08-29')
  const [note,setNote]=useState('')
  const [notice,setNotice]=useState('')
  const selected=items.find((item)=>item.id===selectedId)??items[0]
  const categories=Array.from(new Set([...items.map((item)=>item.category),...extraCategories]))
  const visible=useMemo(()=>items.filter((item)=>`${item.code} ${item.name} ${item.category}`.toLowerCase().includes(query.toLowerCase())&&(category==='ALL'||item.category===category)),[items,query,category])
  const selectedRate=rates.find((item)=>item.category===selected.category)??{category:selected.category,sellingPrices:[],reimbursementPrices:[]}
  const sellingEntry=currentPriceEntry(selectedRate.sellingPrices)
  const reimbursementEntry=currentPriceEntry(selectedRate.reimbursementPrices)
  const specialEntry=currentPriceEntry(selected.specialPrices)
  const displayedHistory=historyKind==='SELLING'?selectedRate.sellingPrices:historyKind==='REIMBURSEMENT'?selectedRate.reimbursementPrices:selected.specialPrices
  const openPrice=(kind:'SELLING'|'REIMBURSEMENT'|'SPECIAL')=>{
    const entry=kind==='SELLING'?sellingEntry:kind==='REIMBURSEMENT'?reimbursementEntry:specialEntry
    setPriceKind(kind);setPrice(entry?String(entry.amount):'');setPriceUom(entry?.uom??selected.stockUom);setNote('');setPriceOpen(true)
  }
  const savePrice=()=>{
    const amount=Number(price.replace(/\D/g,''))
    const nextEntry:PriceHistory={id:`${priceKind.toLowerCase()}-${Date.now()}`,amount,uom:priceUom,effectiveFrom:effective,note:note.trim(),status:'CURRENT'}
    if(priceKind==='SPECIAL'){
      setItems((current)=>current.map((item)=>item.id===selected.id?{...item,rowVersion:item.rowVersion+1,specialPrices:[nextEntry,...item.specialPrices.map((row)=>row.status==='CURRENT'?{...row,status:'SUPERSEDED' as const,effectiveTo:effective}:row)]}:item))
    }else{
      const key=priceKind==='SELLING'?'sellingPrices':'reimbursementPrices'
      setRates((current)=>current.map((rate)=>rate.category===selected.category?{...rate,[key]:[nextEntry,...rate[key].map((row)=>row.status==='CURRENT'?{...row,status:'SUPERSEDED' as const,effectiveTo:effective}:row)]}:rate))
    }
    const label=priceKind==='SELLING'?'Harga jual ke mandor':priceKind==='REIMBURSEMENT'?'Tarif reimburse':'Harga Special'
    setPriceOpen(false);setHistoryKind(priceKind);setNotice(`${label} ${priceKind==='SPECIAL'?selected.code:`kategori ${selected.category}`} ${money(amount)}/${priceUom} tersimpan sebagai simulasi. HPP tetap mengikuti moving average pembelian.`)
  }
  const openAccessoryEditor=(mode:'create'|'edit')=>{
    setEditMode(mode)
    setEditCode(mode==='create'?'':selected.code);setEditName(mode==='create'?'':selected.name);setEditCategory(mode==='create'?(category==='ALL'?categories[0]:category):selected.category);setEditStockUom(mode==='create'?'pcs':selected.stockUom);setEditPurchaseUom(mode==='create'?'lusin':selected.purchaseUom);setEditConversion(mode==='create'?'12':String(selected.conversion));setEditActive(mode==='create'||selected.active)
  }
  const saveAccessory=()=>{
    const conversion=Math.max(1,Number(editConversion)||1)
    if(editMode==='create'){
      const next:AccessoryMaster={id:`acc-sim-${Date.now()}`,code:editCode.trim(),name:editName.trim(),category:editCategory,stockUom:editStockUom.trim(),purchaseUom:editPurchaseUom.trim(),conversion,movingAverage:0,stock:0,active:editActive,rowVersion:1,specialPrices:[{id:`special-sim-${Date.now()}`,amount:0,uom:editStockUom.trim(),effectiveFrom:'2026-08-29',note:'Default gratis untuk Mandor Special',status:'CURRENT'}]}
      setItems((current)=>[next,...current]);setSelectedId(next.id);setNotice(`${next.name} dibuat sebagai draft master simulasi. Saldo dan moving average tetap 0 sampai receipt posted.`)
    }else{
      setItems((current)=>current.map((item)=>item.id===selected.id?{...item,code:editCode.trim(),name:editName.trim(),category:editCategory,stockUom:editStockUom.trim(),purchaseUom:editPurchaseUom.trim(),conversion,active:editActive,rowVersion:item.rowVersion+1}:item))
      setNotice(`${editName.trim()} diperbarui sebagai simulasi; histori stok, HPP, dan Nota Ambil tetap utuh.`)
    }
    setEditMode(null)
  }
  const saveCategory=()=>{
    const value=newCategory.trim()
    if(!value)return
    setExtraCategories((current)=>current.some((item)=>item.toLowerCase()===value.toLowerCase())?current:[...current,value])
    setRates((current)=>[...current,{category:value,sellingPrices:[],reimbursementPrices:[]}])
    setCategory(value);setCategoryOpen(false);setNewCategory('');setNotice(`Kategori ${value} dibuat sebagai simulasi. Tetapkan harga kategori, lalu setiap barang detail baru otomatis mendapat Harga Special Rp0.`)
  }
  const tabs=<section className="mm-workspace-tabs"><button className={workspace==='ACCESSORY'?'active':''} onClick={()=>setWorkspace('ACCESSORY')}><Package/><span><strong>Daftar aksesori</strong><small>SKU detail, HPP & harga mandor</small></span></button><button className={workspace==='UOM'?'active':''} onClick={()=>setWorkspace('UOM')}><Ruler/><span><strong>Master UOM</strong><small>Konversi tetap & isi aktual</small></span></button></section>
  if(workspace==='UOM')return <>
    <MasterHero kind="UOM" title="Master UOM & Conversion" description="Satuan stok, pembelian, penjualan ke mandor, dan reimburse boleh berbeda. Konversi disimpan berbasis waktu agar transaksi lama tidak berubah."/>
    {tabs}
    <UomWorkspace/>
  </>
  return <>
    <MasterHero kind="AKSESORI" title="Aksesori, UOM & Harga Mandor" description="HPP tetap milik SKU detail dari moving average pembelian. Harga jual dan reimburse memakai rate kategori; Harga Special menempel pada barang detail dan default Rp0."/>
    {tabs}
    <section className="mm-category-strip"><button className={category==='ALL'?'active':''} onClick={()=>setCategory('ALL')}><Boxes/><span><strong>Semua kategori</strong><small>{items.length} barang detail</small></span></button>{categories.map((name)=><button className={category===name?'active':''} key={name} onClick={()=>setCategory(name)}><Tag/><span><strong>{name}</strong><small>{items.filter((item)=>item.category===name).length} detail</small></span></button>)}<button className="add" onClick={()=>{setNewCategory('');setCategoryOpen(true)}}><Plus/><span><strong>Tambah kategori</strong><small>Belum punya barang detail</small></span></button></section>
    <section className="panel mm-layout"><aside><header><div><span>BROWSER DETAIL AKSESORI</span><strong>{visible.length} barang</strong></div><Package/></header><label className="mm-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari kode, nama, kategori..."/></label><div>{visible.map((item)=><button className={item.id===selected.id?'active':''} key={item.id} onClick={()=>{setSelectedId(item.id);setNotice('')}}><i><Package/></i><span><strong>{item.name}</strong><small>{item.code} · {item.category}</small><em>{item.stock.toLocaleString('id-ID')} {item.stockUom} On Hand</em></span><StatePill active={item.active}/></button>)}</div><footer><button onClick={()=>openAccessoryEditor('create')}><Plus/> Tambah detail</button><small>Kategori dan detail dipisah; hard delete tidak dipakai.</small></footer></aside><main>
      <header className="mm-detail-head"><div><span>BARANG DETAIL · RATE KATEGORI {selected.category.toUpperCase()}</span><h2>{selected.name}</h2><p>{selected.code}</p></div><div><StatePill active={selected.active}/><small>row version {selected.rowVersion}</small></div></header>
      <div className="mm-identity accessory"><article><Tag/><span><small>KATEGORI BOM</small><strong>{selected.category}</strong></span></article><article><Boxes/><span><small>STOCK ON HAND</small><strong>{selected.stock.toLocaleString('id-ID')} {selected.stockUom}</strong></span></article><article><Ruler/><span><small>UOM PEMBELIAN</small><strong>1 {selected.purchaseUom} = {selected.conversion} {selected.stockUom}</strong></span></article><article><Database/><span><small>MOVING AVG HPP</small><strong>{money(selected.movingAverage)} / {selected.stockUom}</strong></span></article></div>
      <section className="mm-price-matrix"><article><span>HPP / VALUASI SKU</span><h3>{money(selected.movingAverage)} <small>/ {selected.stockUom}</small></h3><p>Moving average aktual · read-only dari receipt</p></article><article><span>MANDOR BELI DARI KITA</span><h3>{sellingEntry?money(sellingEntry.amount):'Belum ditetapkan'} {sellingEntry&&<small>/ {sellingEntry.uom}</small>}</h3><p>Qty aktual Nota Ambil · rate kategori {selected.category}</p><button className="soft-btn" onClick={()=>openPrice('SELLING')}><Coins/> Set harga penerus</button></article><article><span>KITA REIMBURSE MANDOR</span><h3>{reimbursementEntry?money(reimbursementEntry.amount):'Belum ditetapkan'} {reimbursementEntry&&<small>/ {reimbursementEntry.uom}</small>}</h3><p>Good FG × BOM standar · rate kategori {selected.category}</p><button className="soft-btn" onClick={()=>openPrice('REIMBURSEMENT')}><Coins/> Set tarif penerus</button></article><article className="special"><span>HARGA SPECIAL</span><h3>{specialEntry?money(specialEntry.amount):money(0)} <small>/ {specialEntry?.uom??selected.stockUom}</small></h3><p>Mandor ber-flag Special · Rp0 berarti gratis, tetapi stok tetap bergerak</p><button className="soft-btn" onClick={()=>openPrice('SPECIAL')}><Coins/> Set harga Special</button></article></section>
      <div className="mm-rule"><ShieldCheck/><span><strong>Harga Special mengubah tagihan Mandor, bukan HPP barang.</strong><small>Nota Ambil tetap mencatat SKU detail dan mengurangi stok fisik. Mandor Special membaca harga detail (default Rp0); valuasi persediaan tetap memakai moving average harga beli.</small></span></div>
      <section className="mm-history"><header><div><span>PRICE HISTORY · {historyKind==='SPECIAL'?`DETAIL ${selected.code}`:`KATEGORI ${selected.category.toUpperCase()}`}</span><strong>{historyKind==='SELLING'?'Harga jual ke mandor':historyKind==='REIMBURSEMENT'?'Tarif reimburse':'Harga Special barang detail'} berdasarkan waktu</strong></div><nav className="mm-history-tabs"><button className={historyKind==='SELLING'?'active':''} onClick={()=>setHistoryKind('SELLING')}>Jual ke mandor</button><button className={historyKind==='REIMBURSEMENT'?'active':''} onClick={()=>setHistoryKind('REIMBURSEMENT')}>Reimburse</button><button className={historyKind==='SPECIAL'?'active':''} onClick={()=>setHistoryKind('SPECIAL')}>Special</button></nav></header><div className="mm-history-head"><span>Effective</span><span>Harga / UOM</span><span>Catatan</span><span>Status</span></div>{displayedHistory.map((item)=><article key={item.id}><span><strong>{item.effectiveFrom}</strong><small>{item.effectiveTo?`s.d. ${item.effectiveTo}`:'Tanpa akhir'}</small></span><b>{money(item.amount)} / {item.uom??selected.stockUom}</b><span>{item.note}</span><em className={item.status.toLowerCase()}>{item.status}</em></article>)}{displayedHistory.length===0&&<div className="mm-history-empty">Belum ada versi harga untuk scope ini.</div>}</section>
      {notice&&<div className="mm-notice"><CheckCircle2/> {notice}</div>}
      <footer className="mm-actions"><span><LockKeyhole/> UOM dan rate yang sudah dipakai hanya boleh diganti lewat versi penerus.</span><button className="soft-btn" onClick={()=>openAccessoryEditor('edit')}><Pencil/> Edit / nonaktifkan</button></footer>
    </main></section>
    {priceOpen&&<MasterModal title={priceKind==='SELLING'?'Set harga jual ke mandor':priceKind==='REIMBURSEMENT'?'Set tarif reimburse mandor':'Set Harga Special aksesori'} description={priceKind==='SPECIAL'?`${selected.code} · hanya untuk Mandor ber-flag Special`:`${selected.category} · ditampilkan pada SKU ${selected.code}`} onClose={()=>setPriceOpen(false)} action={savePrice} disabled={(priceKind==='SPECIAL'?price.trim()==='':Number(price.replace(/\D/g,''))<=0)||!priceUom||!effective||note.trim().length<4} actionLabel="Simpan versi simulasi"><div className="mm-form-grid three"><label><span>NOMINAL</span><div><b>Rp</b><input autoFocus inputMode="numeric" value={formatMoneyInput(price)} onChange={(event)=>setPrice(cleanMoneyInput(event.target.value))}/></div></label><label><span>UOM HARGA</span><select value={priceUom} onChange={(event)=>setPriceUom(event.target.value)}><option value="pcs">PCS</option><option value="lusin">LUSIN</option><option value="gross">GROSS</option><option value="pack">PACK</option><option value="box">BOX</option></select></label><label><span>BERLAKU MULAI</span><input type="date" value={effective} onChange={(event)=>setEffective(event.target.value)}/></label></div><label className="mm-modal-note"><span>CATATAN SINGKAT</span><textarea value={note} onChange={(event)=>setNote(event.target.value)} placeholder="Alasan dan sumber perubahan rate..."/></label><div className="mm-modal-impact"><Coins/><span><strong>{priceKind==='SPECIAL'?'Rp0 sah dan berarti gratis untuk Mandor Special':'Nominal dan UOM disimpan bersama sebagai snapshot'}</strong><small>{priceKind==='SPECIAL'?'Stock issue tetap mengurangi fisik dan membawa moving-average HPP; hanya tagihan Mandor yang menjadi Rp0.':'Contoh resleting: jual Rp29.900/lusin dan reimburse Rp2.500/pcs. Nota posted tetap membaca versi lama; HPP SKU tidak ikut berubah.'}</small></span></div></MasterModal>}
    {editMode&&<MasterModal title={editMode==='create'?'Tambah barang detail':'Edit detail aksesori'} description={editMode==='create'?'Saldo dan HPP baru dimulai 0.':'Kategori, UOM, dan identitas divalidasi terpisah dari harga.'} onClose={()=>setEditMode(null)} action={saveAccessory} disabled={!editCode.trim()||!editName.trim()||!editCategory||!editStockUom.trim()||!editPurchaseUom.trim()||Number(editConversion)<=0} actionLabel={editMode==='create'?'Buat draft simulasi':'Simpan perubahan simulasi'}><div className="mm-form-grid three"><label><span>KODE</span><input autoFocus value={editCode} onChange={(event)=>setEditCode(event.target.value)}/></label><label><span>NAMA DETAIL</span><input value={editName} onChange={(event)=>setEditName(event.target.value)}/></label><label><span>KATEGORI BOM</span><select value={editCategory} onChange={(event)=>setEditCategory(event.target.value)}>{categories.map((name)=><option key={name}>{name}</option>)}</select></label><label><span>STOCK UOM</span><select value={editStockUom} onChange={(event)=>setEditStockUom(event.target.value)}><option value="pcs">PCS</option><option value="meter">METER</option><option value="kg">KG</option></select></label><label><span>PURCHASE UOM</span><select value={editPurchaseUom} onChange={(event)=>setEditPurchaseUom(event.target.value)}><option value="pcs">PCS</option><option value="lusin">LUSIN</option><option value="gross">GROSS</option><option value="pack">PACK</option><option value="box">BOX</option><option value="roll">ROLL</option></select></label><label><span>ISI PURCHASE UOM</span><input inputMode="numeric" value={editConversion} onChange={(event)=>setEditConversion(event.target.value.replace(/\D/g,''))}/></label><label><span>STATUS</span><select value={editActive?'ACTIVE':'INACTIVE'} onChange={(event)=>setEditActive(event.target.value==='ACTIVE')}><option value="ACTIVE">Aktif</option><option value="INACTIVE">Nonaktif</option></select></label></div><div className="mm-modal-impact warn"><AlertTriangle/><span><strong>UOM historis tidak ditimpa</strong><small>Jika conversion pernah dipakai pada receipt, perubahan berlaku sebagai versi penerus agar stok dan HPP lama tidak berubah.</small></span></div></MasterModal>}
    {categoryOpen&&<MasterModal title="Tambah kategori aksesori" description="Kategori dipakai BOM kerja; barang detail tetap dibuat terpisah." onClose={()=>setCategoryOpen(false)} action={saveCategory} disabled={!newCategory.trim()||categories.some((item)=>item.toLowerCase()===newCategory.trim().toLowerCase())} actionLabel="Buat kategori simulasi"><div className="mm-form-grid"><label><span>NAMA KATEGORI</span><input autoFocus value={newCategory} onChange={(event)=>setNewCategory(event.target.value)} placeholder="Contoh: Benang"/></label></div><div className="mm-modal-impact"><Tag/><span><strong>Kategori membawa rate normal; Harga Special menempel ke detail</strong><small>Harga jual dan reimburse ditetapkan per kategori. Barang detail baru otomatis mendapat Harga Special Rp0; stok dan moving average tetap milik SKU detail.</small></span></div></MasterModal>}
  </>
}

function UomWorkspace(){
  const [uoms,setUoms]=useState(uomSeeds)
  const [selectedCode,setSelectedCode]=useState('LUSIN')
  const [query,setQuery]=useState('')
  const [family,setFamily]=useState('ALL')
  const [qty,setQty]=useState('3')
  const [transactionFactor,setTransactionFactor]=useState('100')
  const [editOpen,setEditOpen]=useState(false)
  const [editMode,setEditMode]=useState<'FIXED'|'VARIABLE'>('FIXED')
  const [editFactor,setEditFactor]=useState('12')
  const [effective,setEffective]=useState('2026-08-29')
  const [note,setNote]=useState('Penyesuaian konversi UOM')
  const [notice,setNotice]=useState('')
  const selected=uoms.find((item)=>item.code===selectedCode)??uoms[0]
  const conversion=currentConversion(selected)
  const visible=useMemo(()=>uoms.filter((item)=>`${item.code} ${item.name} ${item.family}`.toLowerCase().includes(query.toLowerCase())&&(family==='ALL'||item.family===family)),[uoms,query,family])
  const sourceQty=Math.max(0,Number(qty.replace(',','.'))||0)
  const previewFactor=selected.mode==='VARIABLE'?Math.max(0,Number(transactionFactor.replace(',','.'))||0):(conversion?.factor??0)
  const preview=sourceQty*previewFactor
  const openEditor=()=>{setEditMode(selected.mode==='VARIABLE'?'VARIABLE':'FIXED');setEditFactor(conversion?.factor===null?'':String(conversion?.factor??1));setEffective('2026-08-29');setNote('Penyesuaian konversi UOM');setEditOpen(true)}
  const saveConversion=()=>{
    const factor=editMode==='VARIABLE'?null:Number(editFactor.replace(',','.'))
    setUoms((current)=>current.map((item)=>item.code===selected.code?{...item,mode:editMode,rowVersion:item.rowVersion+1,conversions:[{id:`uom-${Date.now()}`,factor,effectiveFrom:effective,note:note.trim(),status:'CURRENT'},...item.conversions.map((row)=>row.status==='CURRENT'?{...row,status:'SUPERSEDED' as const,effectiveTo:effective}:row)]}:item))
    setEditOpen(false);setNotice(`Versi penerus ${selected.code} tersimpan sebagai simulasi. Receipt lama tetap memakai snapshot konversi sebelumnya.`)
  }
  return <>
    <section className="mm-metrics"><article><span>UOM AKTIF</span><strong>{uoms.filter((item)=>item.active).length}</strong><small>Lintas count, length, weight</small></article><article><span>KONVERSI TETAP</span><strong>{uoms.filter((item)=>item.mode==='FIXED').length}</strong><small>Lusin, gross, yard</small></article><article><span>ISI AKTUAL</span><strong>{uoms.filter((item)=>item.mode==='VARIABLE').length}</strong><small>Pack, box, roll</small></article><article><span>SNAPSHOT</span><strong>Effective</strong><small>Transaksi lama tidak recalc</small></article></section>
    <section className="panel mm-layout mm-uom-layout"><aside><header><div><span>BROWSER UOM</span><strong>{visible.length} satuan</strong></div><Ruler/></header><label className="mm-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari kode, nama, family..."/></label><div className="mm-uom-family"><button className={family==='ALL'?'active':''} onClick={()=>setFamily('ALL')}>Semua</button><button className={family==='COUNT'?'active':''} onClick={()=>setFamily('COUNT')}>Count</button><button className={family==='LENGTH'?'active':''} onClick={()=>setFamily('LENGTH')}>Length</button><button className={family==='WEIGHT'?'active':''} onClick={()=>setFamily('WEIGHT')}>Weight</button></div><div>{visible.map((item)=>{const entry=currentConversion(item);return <button className={item.code===selected.code?'active':''} key={item.code} onClick={()=>{setSelectedCode(item.code);setNotice('')}}><i><Ruler/></i><span><strong>{item.code} · {item.name}</strong><small>{item.family} · base {item.baseUom}</small><em>{item.mode==='VARIABLE'?'Isi aktual per transaksi':`1 ${item.code} = ${entry?.factor??0} ${item.baseUom}`}</em></span><StatePill active={item.active}/></button>})}</div><footer><small>Base UOM tidak dikonversi ulang. Variable UOM wajib menyimpan isi aktual pada baris transaksi.</small></footer></aside><main>
      <header className="mm-detail-head"><div><span>MASTER UOM · {selected.family}</span><h2>{selected.code} · {selected.name}</h2><p>Base {selected.baseUom} · mode {selected.mode}</p></div><div><StatePill active={selected.active}/><small>row version {selected.rowVersion}</small></div></header>
      <div className="mm-identity"><article><Ruler/><span><small>UOM CODE</small><strong>{selected.code}</strong></span></article><article><Layers3/><span><small>FAMILY / BASE</small><strong>{selected.family} · {selected.baseUom}</strong></span></article><article><CalendarClock/><span><small>BERLAKU MULAI</small><strong>{conversion?.effectiveFrom??'—'}</strong></span></article></div>
      <section className="mm-uom-preview"><header><div><span>CONVERSION PREVIEW</span><strong>Cek hasil sebelum dipakai transaksi</strong></div><Ruler/></header><div><label><span>QTY {selected.code}</span><input inputMode="decimal" value={qty} onChange={(event)=>setQty(event.target.value.replace(/[^0-9,.]/g,''))}/></label>{selected.mode==='VARIABLE'&&<label><span>ISI AKTUAL / {selected.code}</span><input inputMode="decimal" value={transactionFactor} onChange={(event)=>setTransactionFactor(event.target.value.replace(/[^0-9,.]/g,''))}/><small>Disimpan di receipt / issue</small></label>}<i>× {previewFactor.toLocaleString('id-ID',{maximumFractionDigits:4})}</i><article><span>HASIL BASE UOM</span><strong>{preview.toLocaleString('id-ID',{maximumFractionDigits:4})} {selected.baseUom}</strong><small>{selected.mode==='VARIABLE'?'Isi aktual hanya untuk transaksi ini':'Menggunakan versi konversi current'}</small></article></div></section>
      <div className="mm-rule"><ShieldCheck/><span><strong>UOM transaksi dan UOM harga boleh berbeda.</strong><small>Contoh resleting dibeli atau dijual per lusin, stok disimpan per pcs, dan reimburse dibayar per pcs. Semua dokumen menyimpan qty, UOM, factor, dan hasil base sebagai snapshot.</small></span></div>
      <section className="mm-history"><header><div><span>CONVERSION HISTORY</span><strong>Versi konversi {selected.code}</strong></div><History/></header><div className="mm-history-head"><span>Effective</span><span>Factor ke base</span><span>Catatan</span><span>Status</span></div>{selected.conversions.map((item)=><article key={item.id}><span><strong>{item.effectiveFrom}</strong><small>{item.effectiveTo?`s.d. ${item.effectiveTo}`:'Tanpa akhir'}</small></span><b>{item.factor===null?'Isi aktual transaksi':`× ${item.factor}`}</b><span>{item.note}</span><em className={item.status.toLowerCase()}>{item.status}</em></article>)}</section>
      {notice&&<div className="mm-notice"><CheckCircle2/> {notice}</div>}
      <footer className="mm-actions"><span><LockKeyhole/> Conversion history tidak di-overwrite.</span><button className="soft-btn" disabled={selected.mode==='BASE'} onClick={openEditor}><Pencil/> Set versi penerus</button></footer>
    </main></section>
    {editOpen&&<MasterModal title={`Set konversi penerus ${selected.code}`} description={`Base UOM ${selected.baseUom} · versi sekarang ${conversion?.effectiveFrom??'—'}`} onClose={()=>setEditOpen(false)} action={saveConversion} disabled={(editMode==='FIXED'&&Number(editFactor.replace(',','.'))<=0)||!effective||note.trim().length<4} actionLabel="Simpan versi simulasi"><div className="mm-form-grid three"><label><span>MODE</span><select value={editMode} onChange={(event)=>setEditMode(event.target.value as 'FIXED'|'VARIABLE')}><option value="FIXED">Konversi tetap</option><option value="VARIABLE">Isi aktual transaksi</option></select></label>{editMode==='FIXED'&&<label><span>1 {selected.code} = ... {selected.baseUom}</span><input inputMode="decimal" value={editFactor} onChange={(event)=>setEditFactor(event.target.value.replace(/[^0-9,.]/g,''))}/></label>}<label><span>BERLAKU MULAI</span><input type="date" value={effective} onChange={(event)=>setEffective(event.target.value)}/></label></div><label className="mm-modal-note"><span>CATATAN SINGKAT</span><textarea value={note} onChange={(event)=>setNote(event.target.value)}/></label><div className="mm-modal-impact warn"><CalendarClock/><span><strong>Dokumen lama tidak dihitung ulang</strong><small>Versi baru hanya dipakai transaksi dengan tanggal efektif yang sesuai; snapshot qty base lama tetap utuh.</small></span></div></MasterModal>}
  </>
}

function MasterModal({title,description,onClose,action,actionLabel,disabled=false,children}:{title:string;description:string;onClose:()=>void;action:()=>void;actionLabel:string;disabled?:boolean;children:React.ReactNode}){return <div className="mm-backdrop" onMouseDown={onClose}><section className="mm-modal" role="dialog" aria-modal="true" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>REVIEW MASTER DATA</span><h2>{title}</h2><p>{description}</p></div><button onClick={onClose}><X/></button></header>{children}<footer><button className="soft-btn" onClick={onClose}>Batal</button><button className="primary-btn" disabled={disabled} onClick={action}>{actionLabel} <ArrowRight/></button></footer></section></div>}

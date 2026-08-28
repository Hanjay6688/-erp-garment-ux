import { useMemo, useState } from 'react'
import {
  AlertTriangle, ArrowRight, Boxes, CalendarClock, CheckCircle2, Clock3,
  Coins, Database, History, Layers3, LockKeyhole, Package, Pencil, Plus,
  Ruler, Search, ShieldCheck, Tag, X,
} from 'lucide-react'
import './material-master.css'

export type MaterialMasterView='master-fabric'|'master-accessory'
type Props={view:MaterialMasterView}
type PriceHistory={id:string;amount:number;effectiveFrom:string;effectiveTo?:string;note:string;status:'CURRENT'|'SUPERSEDED'|'CANCELLED'}
type FabricMaster={id:string;code:string;name:string;family:string;defaultUom:string;active:boolean;rowVersion:number;benchmark:PriceHistory[]}
type AccessoryMaster={id:string;code:string;name:string;category:string;stockUom:string;purchaseUom:string;conversion:number;movingAverage:number;stock:number;active:boolean;rowVersion:number;sellingPrices:PriceHistory[]}

const fabricSeeds:FabricMaster[]=[
  {id:'fab-1069',code:'FAB-1069-ORI',name:'Denim 1069 Ori',family:'Denim Medium',defaultUom:'yard',active:true,rowVersion:6,benchmark:[{id:'bp-1069-03',amount:58_500,effectiveFrom:'2026-08-01',note:'Benchmark supplier utama Agustus',status:'CURRENT'},{id:'bp-1069-02',amount:56_750,effectiveFrom:'2026-05-01',effectiveTo:'2026-07-31',note:'Benchmark Mei–Juli',status:'SUPERSEDED'}]},
  {id:'fab-lucy',code:'FAB-LUCY',name:'Lucy',family:'Denim Stretch',defaultUom:'yard',active:true,rowVersion:4,benchmark:[{id:'bp-lucy-02',amount:52_500,effectiveFrom:'2026-08-15',note:'Rata-rata quotation dua supplier',status:'CURRENT'},{id:'bp-lucy-01',amount:50_000,effectiveFrom:'2026-04-01',effectiveTo:'2026-08-14',note:'Benchmark awal',status:'SUPERSEDED'}]},
  {id:'fab-zodiak',code:'FAB-ZODIAK-KW',name:'Zodiak KW',family:'Denim Light',defaultUom:'meter',active:true,rowVersion:8,benchmark:[{id:'bp-zdk-04',amount:51_700,effectiveFrom:'2026-07-01',note:'Benchmark Q3 per meter',status:'CURRENT'}]},
]
const accessorySeeds:AccessoryMaster[]=[
  {id:'acc-btn-silver',code:'ACC-BTN-017-SLV',name:'Kancing Jeans 17 mm · Silver',category:'Kancing',stockUom:'pcs',purchaseUom:'gross',conversion:144,movingAverage:620,stock:4800,active:true,rowVersion:7,sellingPrices:[{id:'sp-01',amount:750,effectiveFrom:'2026-08-01',note:'Harga kasbon Agustus',status:'CURRENT'},{id:'sp-00',amount:700,effectiveFrom:'2026-04-01',effectiveTo:'2026-07-31',note:'Harga lama',status:'SUPERSEDED'}]},
  {id:'acc-btn-metal',code:'ACC-BTN-017-MTL',name:'Kancing Jeans 17 mm · Metal',category:'Kancing',stockUom:'pcs',purchaseUom:'gross',conversion:144,movingAverage:690,stock:3200,active:true,rowVersion:5,sellingPrices:[{id:'sp-02',amount:850,effectiveFrom:'2026-08-01',note:'Harga detail metal',status:'CURRENT'}]},
  {id:'acc-zip-14',code:'ACC-ZIP-014-BLK',name:'Resleting 14 cm · Black',category:'Resleting',stockUom:'pcs',purchaseUom:'lusin',conversion:12,movingAverage:5200,stock:2200,active:true,rowVersion:9,sellingPrices:[{id:'sp-03',amount:6500,effectiveFrom:'2026-07-15',note:'Harga jual mandor saat ini',status:'CURRENT'}]},
  {id:'acc-label-vivo',code:'ACC-LBL-VIVO',name:'Label Woven Vivo',category:'Label',stockUom:'pcs',purchaseUom:'roll',conversion:1000,movingAverage:530,stock:8000,active:true,rowVersion:3,sellingPrices:[{id:'sp-04',amount:750,effectiveFrom:'2026-06-01',note:'Harga kasbon label',status:'CURRENT'}]},
]

const money=(value:number)=>new Intl.NumberFormat('id-ID',{style:'currency',currency:'IDR',maximumFractionDigits:0}).format(value)
const currentPrice=(history:PriceHistory[])=>history.find((item)=>item.status==='CURRENT')?.amount??0

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
    {benchmarkOpen&&<MasterModal title="Set benchmark harga penerus" description={`${selected.name} · ${selected.code}`} onClose={()=>setBenchmarkOpen(false)} action={saveBenchmark} disabled={Number(price.replace(/\D/g,''))<=0||!effective||note.trim().length<4} actionLabel="Simpan simulasi"><div className="mm-form-grid"><label><span>HARGA / {selected.defaultUom.toUpperCase()}</span><div><b>Rp</b><input autoFocus inputMode="numeric" value={price} onChange={(event)=>setPrice(event.target.value.replace(/\D/g,''))}/></div></label><label><span>BERLAKU MULAI</span><input type="date" value={effective} onChange={(event)=>setEffective(event.target.value)}/></label></div><label className="mm-modal-note"><span>CATATAN SINGKAT</span><textarea value={note} onChange={(event)=>setNote(event.target.value)} placeholder="Sumber benchmark / alasan perubahan..."/></label><div className="mm-modal-impact"><Clock3/><span><strong>Versi lama tidak ditimpa</strong><small>Harga current ditutup pada tanggal penerus; transaksi lampau tetap memakai snapshot yang berlaku saat itu.</small></span></div></MasterModal>}
    {editMode&&<MasterModal title={editMode==='create'?'Tambah master kain':'Edit identitas kain'} description={editMode==='create'?'Master baru dimulai aktif tanpa benchmark.':'Perubahan identitas memakai row-version; histori harga tetap terpisah.'} onClose={()=>setEditMode(null)} action={saveFabric} disabled={!editCode.trim()||!editName.trim()||!editFamily.trim()||!editUom.trim()} actionLabel={editMode==='create'?'Buat draft simulasi':'Simpan perubahan simulasi'}><div className="mm-form-grid three"><label><span>KODE</span><input autoFocus value={editCode} onChange={(event)=>setEditCode(event.target.value)}/></label><label><span>NAMA KAIN</span><input value={editName} onChange={(event)=>setEditName(event.target.value)}/></label><label><span>FAMILY</span><input value={editFamily} onChange={(event)=>setEditFamily(event.target.value)}/></label><label><span>DEFAULT UOM</span><select value={editUom} onChange={(event)=>setEditUom(event.target.value)}><option value="yard">Yard (yd)</option><option value="meter">Meter (m)</option></select></label><label><span>STATUS</span><select value={editActive?'ACTIVE':'INACTIVE'} onChange={(event)=>setEditActive(event.target.value==='ACTIVE')}><option value="ACTIVE">Aktif</option><option value="INACTIVE">Nonaktif</option></select></label></div><div className="mm-modal-impact warn"><AlertTriangle/><span><strong>Tidak ada tombol hard delete</strong><small>Nonaktif hanya mencegah pemakaian baru. Receipt, GRNI, HPP, dan invoice lama tetap terhubung ke master ini.</small></span></div></MasterModal>}
  </>
}

function AccessoryWorkspace(){
  const [items,setItems]=useState(accessorySeeds)
  const [selectedId,setSelectedId]=useState(accessorySeeds[0].id)
  const [query,setQuery]=useState('')
  const [category,setCategory]=useState('ALL')
  const [priceOpen,setPriceOpen]=useState(false)
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
  const [effective,setEffective]=useState('2026-08-28')
  const [note,setNote]=useState('')
  const [notice,setNotice]=useState('')
  const selected=items.find((item)=>item.id===selectedId)??items[0]
  const categories=Array.from(new Set([...items.map((item)=>item.category),...extraCategories]))
  const visible=useMemo(()=>items.filter((item)=>`${item.code} ${item.name} ${item.category}`.toLowerCase().includes(query.toLowerCase())&&(category==='ALL'||item.category===category)),[items,query,category])
  const selling=currentPrice(selected.sellingPrices)
  const savePrice=()=>{
    const amount=Number(price.replace(/\D/g,''))
    setItems((current)=>current.map((item)=>item.id===selected.id?{...item,rowVersion:item.rowVersion+1,sellingPrices:[{id:`sp-sim-${Date.now()}`,amount,effectiveFrom:effective,note:note.trim(),status:'CURRENT'},...item.sellingPrices.map((row)=>row.status==='CURRENT'?{...row,status:'SUPERSEDED' as const,effectiveTo:effective}:row)]}:item))
    setPriceOpen(false);setNotice(`Harga jual mandor ${money(amount)}/${selected.stockUom} tersimpan sebagai simulasi. Moving average HPP tidak berubah.`)
  }
  const openAccessoryEditor=(mode:'create'|'edit')=>{
    setEditMode(mode)
    setEditCode(mode==='create'?'':selected.code);setEditName(mode==='create'?'':selected.name);setEditCategory(mode==='create'?(category==='ALL'?categories[0]:category):selected.category);setEditStockUom(mode==='create'?'pcs':selected.stockUom);setEditPurchaseUom(mode==='create'?'lusin':selected.purchaseUom);setEditConversion(mode==='create'?'12':String(selected.conversion));setEditActive(mode==='create'||selected.active)
  }
  const saveAccessory=()=>{
    const conversion=Math.max(1,Number(editConversion)||1)
    if(editMode==='create'){
      const next:AccessoryMaster={id:`acc-sim-${Date.now()}`,code:editCode.trim(),name:editName.trim(),category:editCategory,stockUom:editStockUom.trim(),purchaseUom:editPurchaseUom.trim(),conversion,movingAverage:0,stock:0,active:editActive,rowVersion:1,sellingPrices:[]}
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
    setExtraCategories((current)=>current.some((item)=>item.toLowerCase()===value.toLowerCase())?current:[...current,value]);setCategory(value);setCategoryOpen(false);setNewCategory('');setNotice(`Kategori ${value} dibuat sebagai simulasi. Tambahkan barang detail sebelum dipakai pada BOM.`)
  }
  return <>
    <MasterHero kind="AKSESORI" title="Aksesori, UOM & Harga Mandor" description="BOM kerja memakai kategori; pembelian, stok, HPP, dan Nota Ambil Aksesori memakai barang detail. UOM dan harga jual punya versi efektif sendiri."/>
    <section className="mm-category-strip"><button className={category==='ALL'?'active':''} onClick={()=>setCategory('ALL')}><Boxes/><span><strong>Semua kategori</strong><small>{items.length} barang detail</small></span></button>{categories.map((name)=><button className={category===name?'active':''} key={name} onClick={()=>setCategory(name)}><Tag/><span><strong>{name}</strong><small>{items.filter((item)=>item.category===name).length} detail</small></span></button>)}<button className="add" onClick={()=>{setNewCategory('');setCategoryOpen(true)}}><Plus/><span><strong>Tambah kategori</strong><small>Belum punya barang detail</small></span></button></section>
    <section className="panel mm-layout"><aside><header><div><span>BROWSER DETAIL AKSESORI</span><strong>{visible.length} barang</strong></div><Package/></header><label className="mm-search"><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder="Cari kode, nama, kategori..."/></label><div>{visible.map((item)=><button className={item.id===selected.id?'active':''} key={item.id} onClick={()=>{setSelectedId(item.id);setNotice('')}}><i><Package/></i><span><strong>{item.name}</strong><small>{item.code} · {item.category}</small><em>{item.stock.toLocaleString('id-ID')} {item.stockUom} On Hand</em></span><StatePill active={item.active}/></button>)}</div><footer><button onClick={()=>openAccessoryEditor('create')}><Plus/> Tambah detail</button><small>Kategori dan detail dipisah; hard delete tidak dipakai.</small></footer></aside><main>
      <header className="mm-detail-head"><div><span>BARANG DETAIL · BOM KATEGORI {selected.category.toUpperCase()}</span><h2>{selected.name}</h2><p>{selected.code}</p></div><div><StatePill active={selected.active}/><small>row version {selected.rowVersion}</small></div></header>
      <div className="mm-identity accessory"><article><Tag/><span><small>KATEGORI BOM</small><strong>{selected.category}</strong></span></article><article><Boxes/><span><small>STOCK ON HAND</small><strong>{selected.stock.toLocaleString('id-ID')} {selected.stockUom}</strong></span></article><article><Ruler/><span><small>UOM PEMBELIAN</small><strong>1 {selected.purchaseUom} = {selected.conversion} {selected.stockUom}</strong></span></article><article><Database/><span><small>MOVING AVG HPP</small><strong>{money(selected.movingAverage)} / {selected.stockUom}</strong></span></article></div>
      <section className="mm-dual-price"><article><span>HPP / VALUASI STOK</span><h3>{money(selected.movingAverage)}</h3><small>Moving average aktual · read-only dari ledger</small></article><i>≠</i><article><span>HARGA JUAL KE MANDOR</span><h3>{selling>0?money(selling):'Belum ditetapkan'}</h3><small>Snapshot kasbon pada Nota Ambil</small></article><button className="primary-btn" onClick={()=>{setPrice(selling>0?String(selling):'');setNote('');setPriceOpen(true)}}><Coins/> {selling>0?'Set harga penerus':'Set harga pertama'}</button></section>
      <div className="mm-rule"><ShieldCheck/><span><strong>Satu kategori BOM, banyak barang detail.</strong><small>Kancing Silver dan Metal sama-sama memenuhi komponen Kancing. Payroll rate berasal dari BOM; HPP mengikuti moving average detail; kasbon memakai harga jual mandor yang efektif.</small></span></div>
      <section className="mm-history"><header><div><span>SELLING PRICE HISTORY</span><strong>Harga jual ke mandor berdasarkan waktu</strong></div><History/></header><div className="mm-history-head"><span>Effective</span><span>Harga / UOM</span><span>Catatan</span><span>Status</span></div>{selected.sellingPrices.map((item)=><article key={item.id}><span><strong>{item.effectiveFrom}</strong><small>{item.effectiveTo?`s.d. ${item.effectiveTo}`:'Tanpa akhir'}</small></span><b>{money(item.amount)} / {selected.stockUom}</b><span>{item.note}</span><em className={item.status.toLowerCase()}>{item.status}</em></article>)}</section>
      {notice&&<div className="mm-notice"><CheckCircle2/> {notice}</div>}
      <footer className="mm-actions"><span><LockKeyhole/> UOM yang sudah dipakai hanya boleh diganti lewat versi penerus.</span><button className="soft-btn" onClick={()=>openAccessoryEditor('edit')}><Pencil/> Edit / nonaktifkan</button></footer>
    </main></section>
    {priceOpen&&<MasterModal title="Set harga jual mandor" description={`${selected.name} · HPP ${money(selected.movingAverage)}/${selected.stockUom}`} onClose={()=>setPriceOpen(false)} action={savePrice} disabled={Number(price.replace(/\D/g,''))<=0||!effective||note.trim().length<4} actionLabel="Simpan simulasi"><div className="mm-form-grid"><label><span>HARGA JUAL / {selected.stockUom.toUpperCase()}</span><div><b>Rp</b><input autoFocus inputMode="numeric" value={price} onChange={(event)=>setPrice(event.target.value.replace(/\D/g,''))}/></div></label><label><span>BERLAKU MULAI</span><input type="date" value={effective} onChange={(event)=>setEffective(event.target.value)}/></label></div><label className="mm-modal-note"><span>CATATAN SINGKAT</span><textarea value={note} onChange={(event)=>setNote(event.target.value)} placeholder="Alasan perubahan harga kasbon..."/></label><div className="mm-modal-impact"><Coins/><span><strong>Hanya Nota Ambil baru yang memakai harga ini</strong><small>Nota posted tetap memakai snapshot lama. Moving average HPP dan harga pembelian supplier tidak ikut berubah.</small></span></div></MasterModal>}
    {editMode&&<MasterModal title={editMode==='create'?'Tambah barang detail':'Edit detail aksesori'} description={editMode==='create'?'Saldo dan HPP baru dimulai 0.':'Kategori, UOM, dan identitas divalidasi terpisah dari harga.'} onClose={()=>setEditMode(null)} action={saveAccessory} disabled={!editCode.trim()||!editName.trim()||!editCategory||!editStockUom.trim()||!editPurchaseUom.trim()||Number(editConversion)<=0} actionLabel={editMode==='create'?'Buat draft simulasi':'Simpan perubahan simulasi'}><div className="mm-form-grid three"><label><span>KODE</span><input autoFocus value={editCode} onChange={(event)=>setEditCode(event.target.value)}/></label><label><span>NAMA DETAIL</span><input value={editName} onChange={(event)=>setEditName(event.target.value)}/></label><label><span>KATEGORI BOM</span><select value={editCategory} onChange={(event)=>setEditCategory(event.target.value)}>{categories.map((name)=><option key={name}>{name}</option>)}</select></label><label><span>STOCK UOM</span><input value={editStockUom} onChange={(event)=>setEditStockUom(event.target.value)}/></label><label><span>PURCHASE UOM</span><input value={editPurchaseUom} onChange={(event)=>setEditPurchaseUom(event.target.value)}/></label><label><span>KONVERSI</span><input inputMode="numeric" value={editConversion} onChange={(event)=>setEditConversion(event.target.value.replace(/\D/g,''))}/></label><label><span>STATUS</span><select value={editActive?'ACTIVE':'INACTIVE'} onChange={(event)=>setEditActive(event.target.value==='ACTIVE')}><option value="ACTIVE">Aktif</option><option value="INACTIVE">Nonaktif</option></select></label></div><div className="mm-modal-impact warn"><AlertTriangle/><span><strong>UOM historis tidak ditimpa</strong><small>Jika conversion pernah dipakai pada receipt, perubahan berlaku sebagai versi penerus agar stok dan HPP lama tidak berubah.</small></span></div></MasterModal>}
    {categoryOpen&&<MasterModal title="Tambah kategori aksesori" description="Kategori dipakai BOM kerja; barang detail tetap dibuat terpisah." onClose={()=>setCategoryOpen(false)} action={saveCategory} disabled={!newCategory.trim()||categories.some((item)=>item.toLowerCase()===newCategory.trim().toLowerCase())} actionLabel="Buat kategori simulasi"><div className="mm-form-grid"><label><span>NAMA KATEGORI</span><input autoFocus value={newCategory} onChange={(event)=>setNewCategory(event.target.value)} placeholder="Contoh: Benang"/></label></div><div className="mm-modal-impact"><Tag/><span><strong>Kategori tidak membawa harga atau stok</strong><small>Harga, UOM, moving average, dan Stock On Hand tetap milik barang detail di bawah kategori.</small></span></div></MasterModal>}
  </>
}

function MasterModal({title,description,onClose,action,actionLabel,disabled=false,children}:{title:string;description:string;onClose:()=>void;action:()=>void;actionLabel:string;disabled?:boolean;children:React.ReactNode}){return <div className="mm-backdrop" onMouseDown={onClose}><section className="mm-modal" role="dialog" aria-modal="true" onMouseDown={(event)=>event.stopPropagation()}><header><div><span>REVIEW MASTER DATA</span><h2>{title}</h2><p>{description}</p></div><button onClick={onClose}><X/></button></header>{children}<footer><button className="soft-btn" onClick={onClose}>Batal</button><button className="primary-btn" disabled={disabled} onClick={action}>{actionLabel} <ArrowRight/></button></footer></section></div>}

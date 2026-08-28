import { useMemo, useState } from 'react'
import type { LucideIcon } from 'lucide-react'
import {
  AlertTriangle, BadgeDollarSign, CalendarClock, Check, CheckCircle2,
  Database, History, Layers3, Link2, LockKeyhole,
  MapPin, Package, Pencil, Plus, Search, ShieldCheck, Store, Tags, Truck,
  UsersRound, Warehouse, X,
} from 'lucide-react'
import './master-data-pages.css'

export type BusinessMasterView='master-products'|'master-customers'|'master-partners'|'master-workforce'|'master-locations'

type FieldType='text'|'number'|'select'|'sizes'
type FieldDefinition={key:string;label:string;type:FieldType;options?:readonly string[];placeholder?:string;money?:boolean;suffix?:string}
type Dependency={label:string;value:string;tone:'safe'|'warn'|'neutral'}
type AuditEntry={at:string;actor:string;action:string}
type MasterEntity={
  id:string;code:string;name:string;active:boolean;rowVersion:number;updatedAt:string
  values:Record<string,string>;dependencies:Dependency[];audit:AuditEntry[]
}
type Metric={label:string;value:string;note:string;tone?:'good'|'warn'}
type MasterConfig={
  view:BusinessMasterView;eyebrow:string;title:string;description:string;browserLabel:string
  singular:string;icon:LucideIcon;fields:FieldDefinition[];seeds:MasterEntity[]
  writerStatus:string;integrityTitle:string;integrityCopy:string;emptyDependencyCopy:string
  metrics:(entities:MasterEntity[])=>Metric[]
}
type EditorDraft={code:string;name:string;active:boolean;values:Record<string,string>}

const allSizes=['28','29','30','31','32','33','34','35','36'] as const
const today='2026-08-28'
const idr=(value:string)=>new Intl.NumberFormat('id-ID',{style:'currency',currency:'IDR',maximumFractionDigits:0}).format(Number(value)||0)
const countActive=(entities:MasterEntity[])=>entities.filter((item)=>item.active).length
const seedAudit=(action:string):AuditEntry[]=>[
  {at:'28 Agu 2026 · 09:20',actor:'Owner',action},
  {at:'02 Agu 2026 · 15:42',actor:'Admin ERP',action:'Identitas diverifikasi dan row-version diperbarui'},
]

const productSeeds:MasterEntity[]=[
  {id:'prd-viv-73001',code:'73001',name:'Vivo Classic',active:true,rowVersion:8,updatedAt:'28 Agu 2026',values:{brand:'Vivo',model:'Classic',color:'Indigo',sizes:'28,29,30',sellingPrice:'185000',effectiveFrom:'2026-08-01'},dependencies:[{label:'FG ON HAND',value:'288 pcs',tone:'safe'},{label:'BOM AKTIF',value:'Versi 6',tone:'neutral'},{label:'INVOICE TERBUKA',value:'2 nota',tone:'warn'}],audit:seedAudit('Harga jual penerus efektif 1 Agustus')},
  {id:'prd-viv-73002',code:'73002',name:'Vivo Regular',active:true,rowVersion:5,updatedAt:'26 Agu 2026',values:{brand:'Vivo',model:'Regular',color:'Washed Blue',sizes:'31,32,33',sellingPrice:'190000',effectiveFrom:'2026-07-15'},dependencies:[{label:'FG ON HAND',value:'180 pcs',tone:'safe'},{label:'BOM AKTIF',value:'Versi 4',tone:'neutral'},{label:'WIP BERJALAN',value:'3 batch',tone:'warn'}],audit:seedAudit('Warna identitas diselaraskan dengan Final SKU')},
  {id:'prd-wid-73006',code:'73006',name:'Widie Workwear',active:false,rowVersion:4,updatedAt:'18 Agu 2026',values:{brand:'Widie',model:'Workwear',color:'Stone',sizes:'34,35,36',sellingPrice:'198000',effectiveFrom:'2026-06-01'},dependencies:[{label:'FG ON HAND',value:'90 pcs',tone:'warn'},{label:'BOM AKTIF',value:'Versi 3',tone:'neutral'},{label:'INVOICE TERBUKA',value:'0 nota',tone:'safe'}],audit:seedAudit('Dinonaktifkan untuk transaksi baru; histori tetap aktif')},
]

const customerSeeds:MasterEntity[]=[
  {id:'cus-nf',code:'CUS-NF-001',name:'Nusantara Fashion',active:true,rowVersion:7,updatedAt:'28 Agu 2026',values:{city:'Bandung',contact:'Ibu Nisa',phone:'0812 6600 1122',terms:'30',creditLimit:'150000000',priceTier:'Wholesale A'},dependencies:[{label:'OPEN AR',value:'Rp72,4 jt',tone:'warn'},{label:'INVOICE HARI INI',value:'1 draft',tone:'neutral'},{label:'CREDIT AVAILABLE',value:'Rp77,6 jt',tone:'safe'}],audit:seedAudit('Limit kredit direview tanpa mengubah invoice lama')},
  {id:'cus-mj',code:'CUS-MJ-004',name:'Maju Jaya',active:true,rowVersion:5,updatedAt:'27 Agu 2026',values:{city:'Jakarta',contact:'Pak Deni',phone:'0813 7200 0918',terms:'14',creditLimit:'90000000',priceTier:'Wholesale B'},dependencies:[{label:'OPEN AR',value:'Rp28,8 jt',tone:'safe'},{label:'INVOICE HARI INI',value:'1 draft',tone:'neutral'},{label:'CREDIT AVAILABLE',value:'Rp61,2 jt',tone:'safe'}],audit:seedAudit('Termin pembayaran diperbarui menjadi 14 hari')},
  {id:'cus-sd',code:'CUS-SD-008',name:'Sumber Denim',active:true,rowVersion:3,updatedAt:'25 Agu 2026',values:{city:'Tasikmalaya',contact:'Ibu Rani',phone:'0821 8004 0031',terms:'21',creditLimit:'120000000',priceTier:'Wholesale A'},dependencies:[{label:'OPEN AR',value:'Rp18,4 jt',tone:'warn'},{label:'OVERDUE',value:'Rp6,2 jt',tone:'warn'},{label:'CREDIT AVAILABLE',value:'Rp101,6 jt',tone:'safe'}],audit:seedAudit('Nomor kontak utama diverifikasi')},
]

const partnerSeeds:MasterEntity[]=[
  {id:'sup-sinaran',code:'SUP-FAB-001',name:'Sinaran',active:true,rowVersion:9,updatedAt:'28 Agu 2026',values:{partnerType:'Supplier Kain',city:'Bandung',contact:'Pak Yudi',phone:'0812 9001 2877',terms:'45',defaultUom:'yard'},dependencies:[{label:'OPEN AP',value:'Rp146,8 jt',tone:'warn'},{label:'GRNI UNMATCHED',value:'3 receipt',tone:'warn'},{label:'UOM TERAKHIR',value:'yard',tone:'neutral'}],audit:seedAudit('Default UOM dicatat sebagai preferensi, bukan konversi')},
  {id:'sup-accessory',code:'SUP-ACC-003',name:'Mitra Aksesori',active:true,rowVersion:6,updatedAt:'27 Agu 2026',values:{partnerType:'Supplier Aksesori',city:'Jakarta',contact:'Ibu Diah',phone:'0817 4400 0912',terms:'30',defaultUom:'pcs'},dependencies:[{label:'OPEN AP',value:'Rp42,6 jt',tone:'warn'},{label:'GRNI UNMATCHED',value:'1 receipt',tone:'neutral'},{label:'UOM TERAKHIR',value:'gross',tone:'neutral'}],audit:seedAudit('Termin supplier dikonfirmasi ulang')},
  {id:'ven-laundry',code:'VEN-LDY-002',name:'Laundry Bersih Jaya',active:true,rowVersion:4,updatedAt:'26 Agu 2026',values:{partnerType:'Vendor Laundry',city:'Cimahi',contact:'Pak Rudi',phone:'0857 0190 0443',terms:'7',defaultUom:'pcs'},dependencies:[{label:'OPEN AP',value:'Rp12,9 jt',tone:'neutral'},{label:'WIP DI VENDOR',value:'412 pcs',tone:'warn'},{label:'KLAIM TERBUKA',value:'1 kasus',tone:'warn'}],audit:seedAudit('Kontak operasional laundry diperbarui')},
]

const workforceSeeds:MasterEntity[]=[
  {id:'wrk-afat',code:'MDR-AFAT',name:'Mandor Afat',active:true,rowVersion:8,updatedAt:'28 Agu 2026',values:{role:'Mandor',phone:'0812 7110 0288',bank:'BCA · 1090 44xx',attendance:'Tidak wajib',teamSize:'18'},dependencies:[{label:'WIP AKTIF',value:'4 batch',tone:'warn'},{label:'PAYROLL READY',value:'Rp18,7 jt',tone:'neutral'},{label:'KASBON AKSESORI',value:'Rp2,1 jt',tone:'warn'}],audit:seedAudit('Rekening pembayaran diverifikasi Owner')},
  {id:'wrk-rina',code:'MDR-RINA',name:'Mandor Rina',active:true,rowVersion:5,updatedAt:'27 Agu 2026',values:{role:'Mandor',phone:'0813 8801 2270',bank:'BRI · 0248 30xx',attendance:'Tidak wajib',teamSize:'12'},dependencies:[{label:'WIP AKTIF',value:'2 batch',tone:'neutral'},{label:'PAYROLL READY',value:'Rp9,4 jt',tone:'neutral'},{label:'KASBON AKSESORI',value:'Rp860 rb',tone:'safe'}],audit:seedAudit('Jumlah tim diperbarui')},
  {id:'wrk-dodi',code:'WRK-DODI',name:'Dodi Firmansyah',active:true,rowVersion:3,updatedAt:'25 Agu 2026',values:{role:'Pekerja Finishing',phone:'0822 1077 1220',bank:'Tunai',attendance:'Wajib',teamSize:'1'},dependencies:[{label:'WIP AKTIF',value:'0 batch',tone:'safe'},{label:'PAYROLL READY',value:'Rp1,8 jt',tone:'neutral'},{label:'ABSENSI BULAN INI',value:'24 hari',tone:'safe'}],audit:seedAudit('Kebijakan absensi ditetapkan wajib')},
]

const locationSeeds:MasterEntity[]=[
  {id:'loc-fg-main',code:'LOC-FG-UTAMA',name:'Gudang FG Utama',active:true,rowVersion:8,updatedAt:'28 Agu 2026',values:{locationType:'Gudang',parent:'Pabrik Utama',stockScope:'Finished Goods',rackCount:'24'},dependencies:[{label:'STOCK ON HAND',value:'1.482 pcs',tone:'warn'},{label:'DRAFT ADJUSTMENT',value:'1 dokumen',tone:'warn'},{label:'OPEN TRANSFER',value:'0',tone:'safe'}],audit:seedAudit('Kapasitas rak diverifikasi saat stock count')},
  {id:'loc-fabric',code:'LOC-FAB-A',name:'Area Kain & Roll',active:true,rowVersion:6,updatedAt:'27 Agu 2026',values:{locationType:'Area',parent:'Gudang Bahan',stockScope:'Fabric Roll',rackCount:'18'},dependencies:[{label:'STOCK ON HAND',value:'186 roll',tone:'warn'},{label:'DRAFT ADJUSTMENT',value:'0',tone:'safe'},{label:'OPEN RECEIPT',value:'2 surat jalan',tone:'neutral'}],audit:seedAudit('Scope stok dikunci ke Fabric Roll')},
  {id:'loc-acc',code:'LOC-ACC-B',name:'Rak Aksesori B',active:true,rowVersion:4,updatedAt:'26 Agu 2026',values:{locationType:'Bin / Rak',parent:'Gudang Bahan',stockScope:'Accessory',rackCount:'8'},dependencies:[{label:'STOCK ON HAND',value:'18.200 pcs',tone:'warn'},{label:'DRAFT ADJUSTMENT',value:'1 dokumen',tone:'warn'},{label:'OPEN ISSUE',value:'3 nota',tone:'neutral'}],audit:seedAudit('Nama rak diperjelas untuk proses browse')},
]

const commonMetrics=(entities:MasterEntity[],third:Metric):Metric[]=>[
  {label:'MASTER AKTIF',value:String(countActive(entities)),note:'Boleh dipakai transaksi baru',tone:'good'},
  {label:'NONAKTIF',value:String(entities.length-countActive(entities)),note:'Histori tetap terbaca'},
  third,
  {label:'HARD DELETE',value:'Tidak ada',note:'Nonaktif + jejak audit'},
]

const masterConfigs:Record<BusinessMasterView,MasterConfig>={
  'master-products':{view:'master-products',eyebrow:'PRODUK & SKU',title:'Produk & SKU',description:'Kelola identitas barang jadi, kombinasi size, dan harga efektif tanpa memutus jejak HPP, stok, atau invoice.',browserLabel:'BROWSER SKU',singular:'produk',icon:Package,writerStatus:'Read-ready · writer produk masih simulasi',integrityTitle:'Identitas SKU yang sudah bergerak tidak ditimpa.',integrityCopy:'Perubahan kode, brand, size, atau harga harus menjadi versi penerus. FG dan invoice lama tetap membaca snapshot sebelumnya.',emptyDependencyCopy:'SKU baru belum memiliki BOM, WIP, stok, atau invoice.',fields:[{key:'brand',label:'Merek',type:'select',options:['Vivo','Widie']},{key:'model',label:'Model',type:'text'},{key:'color',label:'Warna',type:'text'},{key:'sizes',label:'Ukuran aktif',type:'sizes',options:allSizes},{key:'sellingPrice',label:'Harga jual',type:'number',money:true},{key:'effectiveFrom',label:'Berlaku mulai',type:'text'}],seeds:productSeeds,metrics:(items)=>commonMetrics(items,{label:'SKU DENGAN FG',value:'3',note:'Tidak boleh ganti identitas langsung',tone:'warn'})},
  'master-customers':{view:'master-customers',eyebrow:'PELANGGAN',title:'Pelanggan & Kredit',description:'Satu tempat untuk identitas toko, termin, limit kredit, dan dependency AR sebelum transaksi baru dibuat.',browserLabel:'BROWSER PELANGGAN',singular:'pelanggan',icon:Store,writerStatus:'Read-ready · save RPC aman belum dipasang',integrityTitle:'Nonaktif tidak menghapus piutang dan histori toko.',integrityCopy:'Perubahan termin atau limit hanya berlaku ke transaksi baru. Invoice, pembayaran, retur, dan AR lama tetap dapat ditelusuri.',emptyDependencyCopy:'Pelanggan baru belum memiliki invoice atau saldo AR.',fields:[{key:'city',label:'Kota',type:'text'},{key:'contact',label:'Kontak utama',type:'text'},{key:'phone',label:'Telepon',type:'text'},{key:'terms',label:'Termin (hari)',type:'number',suffix:'hari'},{key:'creditLimit',label:'Limit kredit',type:'number',money:true},{key:'priceTier',label:'Tier harga',type:'select',options:['Wholesale A','Wholesale B','Wholesale C']}],seeds:customerSeeds,metrics:(items)=>commonMetrics(items,{label:'LIMIT TERPAKAI',value:'Rp119,6 jt',note:'Dibentuk dari open AR',tone:'warn'})},
  'master-partners':{view:'master-partners',eyebrow:'SUPPLIER & VENDOR',title:'Supplier & Vendor',description:'Pisahkan peran supplier kain, aksesori, dan vendor proses sambil menjaga AP, GRNI, UOM, serta kasus vendor tetap terhubung.',browserLabel:'BROWSER PARTNER',singular:'partner',icon:Truck,writerStatus:'Read-ready · safe writer partner belum lengkap',integrityTitle:'Default UOM hanya preferensi, bukan konversi transaksi.',integrityCopy:'Setiap receipt menyimpan UOM aktualnya sendiri. Invoice final mengikuti receipt yang di-match dan tidak boleh mengubah kuantitas fisik.',emptyDependencyCopy:'Partner baru belum memiliki receipt, AP, WIP vendor, atau klaim.',fields:[{key:'partnerType',label:'Tipe partner',type:'select',options:['Supplier Kain','Supplier Aksesori','Vendor Laundry','Vendor Lain']},{key:'city',label:'Kota',type:'text'},{key:'contact',label:'Kontak utama',type:'text'},{key:'phone',label:'Telepon',type:'text'},{key:'terms',label:'Termin (hari)',type:'number',suffix:'hari'},{key:'defaultUom',label:'Preferensi UOM',type:'select',options:['yard','meter','pcs','lusin','gross']}],seeds:partnerSeeds,metrics:(items)=>commonMetrics(items,{label:'GRNI UNMATCHED',value:'4 receipt',note:'Menunggu invoice final',tone:'warn'})},
  'master-workforce':{view:'master-workforce',eyebrow:'MANDOR & PEKERJA',title:'Mandor & Pekerja',description:'Kelola identitas penerima WIP dan payroll tanpa menghilangkan batch, nota FG, kasbon aksesori, atau histori pembayaran.',browserLabel:'BROWSER TENAGA KERJA',singular:'tenaga kerja',icon:UsersRound,writerStatus:'Read-ready · safe writer tenaga kerja belum lengkap',integrityTitle:'Mandor dengan WIP atau payroll tidak boleh dihapus.',integrityCopy:'Perubahan rekening dan status harus meninggalkan row-version. Batch, Nota FG, Bikin Bagus, serta pembayaran lampau tetap menunjuk orang yang sama.',emptyDependencyCopy:'Tenaga kerja baru belum memiliki WIP, payroll, atau kasbon.',fields:[{key:'role',label:'Peran',type:'select',options:['Mandor','Pekerja Jahit','Pekerja Finishing','QC']},{key:'phone',label:'Telepon',type:'text'},{key:'bank',label:'Rekening / cara bayar',type:'text'},{key:'attendance',label:'Kebijakan absensi',type:'select',options:['Tidak wajib','Wajib']},{key:'teamSize',label:'Jumlah anggota tim',type:'number',suffix:'orang'}],seeds:workforceSeeds,metrics:(items)=>commonMetrics(items,{label:'WIP AKTIF',value:'6 batch',note:'Terkunci ke mandor asal',tone:'warn'})},
  'master-locations':{view:'master-locations',eyebrow:'GUDANG & LOKASI',title:'Gudang & Lokasi',description:'Susun hierarki gudang, area, dan rak sebagai scope Stock On Hand tanpa membuat konsep reservasi yang tidak ada di backend.',browserLabel:'BROWSER LOKASI',singular:'lokasi',icon:Warehouse,writerStatus:'Read-ready · safe writer lokasi belum lengkap',integrityTitle:'Lokasi berisi stok atau draft tidak boleh dinonaktifkan.',integrityCopy:'Pemindahan stok wajib melalui event mutasi. Edit lokasi tidak memindahkan quantity, tidak membuat reserved stock, dan tidak menulis ulang stock card.',emptyDependencyCopy:'Lokasi baru masih kosong dan belum menjadi tujuan transaksi.',fields:[{key:'locationType',label:'Tipe lokasi',type:'select',options:['Gudang','Area','Bin / Rak']},{key:'parent',label:'Lokasi induk',type:'text'},{key:'stockScope',label:'Scope stok',type:'select',options:['Finished Goods','Fabric Roll','Accessory','Mixed']},{key:'rackCount',label:'Kapasitas / jumlah rak',type:'number',suffix:'rak'}],seeds:locationSeeds,metrics:(items)=>commonMetrics(items,{label:'TOTAL ON HAND',value:'1.482 FG',note:'Plus 186 roll & aksesori',tone:'warn'})},
}

function MasterState({active}:{active:boolean}){return <em className={`md-state ${active?'active':'inactive'}`}>{active?'AKTIF':'NONAKTIF'}</em>}

function formatFieldValue(field:FieldDefinition,value:string){
  if(field.money)return idr(value)
  if(field.type==='sizes')return value.split(',').filter(Boolean).map((size)=>`Size ${size}`).join(' · ')||'Belum dipilih'
  return `${value||'—'}${value&&field.suffix?` ${field.suffix}`:''}`
}

function MasterHero({config}:{config:MasterConfig}){
  const Icon=config.icon
  return <section className="hero-copy compact md-hero"><div><div className="eyebrow">MASTER DATA · {config.eyebrow}</div><h1>{config.title}</h1><p>{config.description}</p></div><div className="md-contract"><Icon/><span><small>KONTRAK SAAT INI</small><strong>{config.writerStatus}</strong><em>UX ini simulasi sampai Auth dan RPC domain tersambung.</em></span></div></section>
}

function MasterEditor({mode,config,entity,onClose,onSave}:{mode:'create'|'edit';config:MasterConfig;entity?:MasterEntity;onClose:()=>void;onSave:(draft:EditorDraft)=>void}){
  const [draft,setDraft]=useState<EditorDraft>(()=>({code:entity?.code??'',name:entity?.name??'',active:entity?.active??true,values:entity?.values??Object.fromEntries(config.fields.map((field)=>[field.key,field.type==='sizes'?'':field.options?.[0]??'']))}))
  const update=(key:string,value:string)=>setDraft((current)=>({...current,values:{...current.values,[key]:value}}))
  const toggleSize=(size:string)=>{
    const current=(draft.values.sizes??'').split(',').filter(Boolean)
    const next=current.includes(size)?current.filter((item)=>item!==size):allSizes.filter((item)=>current.includes(item)||item===size)
    update('sizes',next.join(','))
  }
  const valid=draft.code.trim().length>1&&draft.name.trim().length>2&&config.fields.every((field)=>field.type==='sizes'?(draft.values[field.key]??'').length>0:(draft.values[field.key]??'').trim().length>0)
  return <div className="md-backdrop" role="presentation" onMouseDown={(event)=>{if(event.target===event.currentTarget)onClose()}}><section className="md-modal" role="dialog" aria-modal="true" aria-label={`${mode==='create'?'Tambah':'Edit'} ${config.singular}`}>
    <header><div><span>{mode==='create'?'MASTER BARU':'EDIT BER-VERSI'}</span><h2>{mode==='create'?`Tambah ${config.singular}`:`Edit ${entity?.name}`}</h2><p>{mode==='create'?'Record baru dimulai tanpa dependency transaksi.':`row-version ${entity?.rowVersion} akan bertambah saat tersimpan.`}</p></div><button type="button" aria-label="Tutup editor" onClick={onClose}><X/></button></header>
    <div className="md-editor-grid"><label><span>KODE</span><input autoFocus value={draft.code} onChange={(event)=>setDraft((current)=>({...current,code:event.target.value}))}/></label><label><span>NAMA</span><input value={draft.name} onChange={(event)=>setDraft((current)=>({...current,name:event.target.value}))}/></label>{config.fields.map((field)=><label className={field.type==='sizes'?'md-size-field':''} key={field.key}><span>{field.label.toUpperCase()}</span>{field.type==='select'?<select value={draft.values[field.key]??''} onChange={(event)=>update(field.key,event.target.value)}>{field.options?.map((option)=><option key={option}>{option}</option>)}</select>:field.type==='sizes'?<div className="md-size-selector">{allSizes.map((size)=>{const checked=(draft.values[field.key]??'').split(',').includes(size);return <button type="button" className={checked?'active':''} aria-pressed={checked} key={size} onClick={()=>toggleSize(size)}><i>{checked&&<Check/>}</i><b>{size}</b></button>})}</div>:<div className={field.money?'md-money-input':''}>{field.money&&<b>Rp</b>}<input type={field.type==='number'?'number':'text'} inputMode={field.type==='number'?'numeric':undefined} placeholder={field.placeholder} value={draft.values[field.key]??''} onChange={(event)=>update(field.key,event.target.value)}/>{field.suffix&&<em>{field.suffix}</em>}</div>}</label>)}</div>
    <label className="md-active-toggle"><input type="checkbox" checked={draft.active} onChange={(event)=>setDraft((current)=>({...current,active:event.target.checked}))}/><span><i>{draft.active&&<Check/>}</i><strong>{draft.active?'Aktif untuk transaksi baru':'Nonaktif untuk transaksi baru'}</strong><small>Histori dan dependency lama tidak ikut hilang.</small></span></label>
    <div className="md-editor-warning"><AlertTriangle/><span><strong>Tidak ada hard delete</strong><small>Perubahan di layar ini hanya simulasi lokal. Writer backend baru boleh dipasang setelah kontrak aman tersedia.</small></span></div>
    <footer><button type="button" className="soft-btn" onClick={onClose}>Batal</button><button type="button" className="primary-btn" disabled={!valid} onClick={()=>onSave(draft)}>{mode==='create'?'Buat simulasi':'Simpan simulasi'}</button></footer>
  </section></div>
}

function MasterWorkspace({config}:{config:MasterConfig}){
  const [entities,setEntities]=useState(config.seeds)
  const [selectedId,setSelectedId]=useState(config.seeds[0].id)
  const [query,setQuery]=useState('')
  const [status,setStatus]=useState<'ALL'|'ACTIVE'|'INACTIVE'>('ALL')
  const [editorMode,setEditorMode]=useState<'create'|'edit'|null>(null)
  const [notice,setNotice]=useState('')
  const selected=entities.find((item)=>item.id===selectedId)??entities[0]
  const visible=useMemo(()=>entities.filter((item)=>`${item.code} ${item.name} ${Object.values(item.values).join(' ')}`.toLowerCase().includes(query.toLowerCase())&&(status==='ALL'||item.active===(status==='ACTIVE'))),[entities,query,status])
  const metrics=config.metrics(entities)
  const save=(draft:EditorDraft)=>{
    if(editorMode==='create'){
      const next:MasterEntity={id:`${config.view}-${Date.now()}`,code:draft.code.trim(),name:draft.name.trim(),active:draft.active,rowVersion:1,updatedAt:today,values:draft.values,dependencies:[],audit:[{at:'28 Agu 2026 · sekarang',actor:'Owner',action:'Master dibuat sebagai simulasi lokal'}]}
      setEntities((current)=>[next,...current]);setSelectedId(next.id);setNotice(`${next.name} dibuat sebagai simulasi. Backend belum berubah.`)
    }else{
      setEntities((current)=>current.map((item)=>item.id===selected.id?{...item,code:draft.code.trim(),name:draft.name.trim(),active:draft.active,values:draft.values,rowVersion:item.rowVersion+1,updatedAt:today,audit:[{at:'28 Agu 2026 · sekarang',actor:'Owner',action:'Identitas diperbarui sebagai simulasi lokal'},...item.audit]}:item))
      setNotice(`${draft.name.trim()} diperbarui sebagai simulasi; dependency dan histori tetap utuh.`)
    }
    setEditorMode(null)
  }
  const EntityIcon=config.icon
  return <>
    <MasterHero config={config}/>
    <section className="md-metrics">{metrics.map((metric)=><article className={metric.tone??''} key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong><small>{metric.note}</small></article>)}</section>
    <section className="panel md-workspace"><aside>
      <header><div><span>{config.browserLabel}</span><strong>{visible.length} dari {entities.length}</strong></div><EntityIcon/></header>
      <div className="md-browser-tools"><label><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder={`Cari ${config.singular}, kode, detail...`}/></label><select aria-label="Filter status" value={status} onChange={(event)=>setStatus(event.target.value as typeof status)}><option value="ALL">Semua status</option><option value="ACTIVE">Aktif</option><option value="INACTIVE">Nonaktif</option></select></div>
      <div className="md-browser-list">{visible.map((item)=><button type="button" className={item.id===selected.id?'active':''} key={item.id} onClick={()=>{setSelectedId(item.id);setNotice('')}}><i><EntityIcon/></i><span><strong>{item.name}</strong><small>{item.code}</small><em>{config.fields.slice(0,2).map((field)=>item.values[field.key]).filter(Boolean).join(' · ')}</em></span><MasterState active={item.active}/></button>)}{visible.length===0&&<div className="md-empty"><Search/><strong>Tidak ada hasil</strong><small>Ubah kata pencarian atau filter status.</small></div>}</div>
      <footer><button type="button" onClick={()=>setEditorMode('create')}><Plus/> Tambah {config.singular}</button><small>Simulasi lokal · belum menulis backend.</small></footer>
    </aside><main>
      <header className="md-detail-head"><div><span>IDENTITAS MASTER</span><h2>{selected.name}</h2><p>{selected.code} · terakhir diperbarui {selected.updatedAt}</p></div><div><MasterState active={selected.active}/><small>row-version {selected.rowVersion}</small></div></header>
      <div className="md-facts">{config.fields.map((field,index)=>{const icons=[Tags,Layers3,BadgeDollarSign,CalendarClock,Database,MapPin];const FactIcon=icons[index%icons.length];return <article className={field.type==='sizes'?'wide':''} key={field.key}><FactIcon/><span><small>{field.label.toUpperCase()}</small><strong>{formatFieldValue(field,selected.values[field.key]??'')}</strong></span></article>})}</div>
      <section className="md-integrity"><ShieldCheck/><span><strong>{config.integrityTitle}</strong><small>{config.integrityCopy}</small></span></section>
      <section className="md-dependencies"><header><div><span>DEPENDENCY CHECK</span><strong>Dampak sebelum nonaktif / koreksi</strong></div><Link2/></header>{selected.dependencies.length>0?<div>{selected.dependencies.map((dependency)=><article className={dependency.tone} key={dependency.label}><span>{dependency.label}</span><strong>{dependency.value}</strong></article>)}</div>:<div className="md-no-dependency"><CheckCircle2/><span><strong>Belum ada dependency</strong><small>{config.emptyDependencyCopy}</small></span></div>}</section>
      <section className="md-audit"><header><div><span>AUDIT TRAIL</span><strong>Perubahan identitas terakhir</strong></div><History/></header>{selected.audit.map((entry)=><article key={`${entry.at}-${entry.action}`}><i/><span><strong>{entry.action}</strong><small>{entry.at} · {entry.actor}</small></span></article>)}</section>
      {notice&&<div className="md-notice"><CheckCircle2/><span>{notice}</span><button type="button" aria-label="Tutup pemberitahuan" onClick={()=>setNotice('')}><X/></button></div>}
      <footer className="md-actions"><span><LockKeyhole/> Record bertransaksi dijaga lewat nonaktif dan versi.</span><button type="button" className="soft-btn" onClick={()=>setEditorMode('edit')}><Pencil/> Edit / nonaktifkan</button></footer>
    </main></section>
    {editorMode&&<MasterEditor key={`${editorMode}-${selected.id}`} mode={editorMode} config={config} entity={editorMode==='edit'?selected:undefined} onClose={()=>setEditorMode(null)} onSave={save}/>} 
  </>
}

export default function MasterDataPages({view}:{view:BusinessMasterView}){
  return <MasterWorkspace key={view} config={masterConfigs[view]}/>
}

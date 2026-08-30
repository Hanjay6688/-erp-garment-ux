import { useMemo, useState } from 'react'
import type { LucideIcon } from 'lucide-react'
import {
  AlertTriangle, BadgeDollarSign, CalendarClock, Check, CheckCircle2,
  Calculator, Coins, Database, History, Layers3, Link2, LockKeyhole,
  MapPin, Package, Pencil, Plus, Search, ShieldCheck, Store, Tags, Trash2, Truck,
  UsersRound, Warehouse, X,
} from 'lucide-react'
import './master-data-pages.css'
import { cleanMoneyInput, formatMoneyInput } from './moneyInput'

export type BusinessMasterView='master-products'|'master-customers'|'master-partners'|'master-workforce'|'master-locations'

type FieldType='text'|'number'|'select'|'sizes'|'date'|'boolean'
type FieldDefinition={key:string;label:string;type:FieldType;options?:readonly string[];placeholder?:string;money?:boolean;suffix?:string;optional?:boolean}
type Dependency={label:string;value:string;tone:'safe'|'warn'|'neutral'}
type AuditEntry={at:string;actor:string;action:string}
type BomLine={id:string;category:string;quantity:number;uom:string}
type CategoryRate={category:string;chargeUom:string;reimbursementUom:string;mandorCharge:number;reimbursement:number;effectiveFrom:string;version:number}
type MasterEntity={
  id:string;code:string;name:string;active:boolean;rowVersion:number;updatedAt:string
  values:Record<string,string>;dependencies:Dependency[];audit:AuditEntry[];bom?:BomLine[]
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
const sizeGroups=[['28','29','30'],['31','32','33'],['34','35','36']] as const
const today='2026-08-29'
const idr=(value:string)=>new Intl.NumberFormat('id-ID',{style:'currency',currency:'IDR',maximumFractionDigits:0}).format(Number(value)||0)
const uomFactor=(uom:string)=>({pcs:1,lusin:12,gross:144}[uom.toLowerCase()]??1)
const rateInUom=(amount:number,sourceUom:string,targetUom:string)=>amount/uomFactor(sourceUom)*uomFactor(targetUom)
const countActive=(entities:MasterEntity[])=>entities.filter((item)=>item.active).length
const seedAudit=(action:string):AuditEntry[]=>[
  {at:'28 Agu 2026 · 09:20',actor:'Owner',action},
  {at:'02 Agu 2026 · 15:42',actor:'Admin ERP',action:'Identitas diverifikasi dan row-version diperbarui'},
]

const categoryRateSeeds:CategoryRate[]=[
  {category:'Kancing',chargeUom:'pcs',reimbursementUom:'pcs',mandorCharge:495,reimbursement:500,effectiveFrom:'2026-08-01',version:4},
  {category:'Resleting',chargeUom:'lusin',reimbursementUom:'pcs',mandorCharge:29_900,reimbursement:2_500,effectiveFrom:'2026-08-01',version:4},
  {category:'Label',chargeUom:'pcs',reimbursementUom:'pcs',mandorCharge:750,reimbursement:800,effectiveFrom:'2026-08-01',version:5},
]

const defaultBom=(prefix:string):BomLine[]=>[
  {id:`${prefix}-button`,category:'Kancing',quantity:1,uom:'pcs'},
  {id:`${prefix}-zipper`,category:'Resleting',quantity:1,uom:'pcs'},
  {id:`${prefix}-label`,category:'Label',quantity:1,uom:'pcs'},
]

const productSeeds:MasterEntity[]=[
  {id:'prd-viv-73001',code:'73001',name:'Vivo Classic',active:true,rowVersion:8,updatedAt:'28 Agu 2026',values:{brand:'Vivo',model:'Classic',color:'Indigo',sizes:'28,29,30',sellingPrice:'185000',sewingRate:'14050',commissionRate:'1800',specialCommissionRate:'',effectiveFrom:'2026-08-01'},bom:defaultBom('73001'),dependencies:[{label:'FG ON HAND',value:'288 pcs',tone:'safe'},{label:'BOM AKTIF',value:'Versi 6',tone:'neutral'},{label:'INVOICE TERBUKA',value:'2 nota',tone:'warn'}],audit:seedAudit('Harga jual penerus efektif 1 Agustus')},
  {id:'prd-viv-73002',code:'73002',name:'Vivo Regular',active:true,rowVersion:5,updatedAt:'26 Agu 2026',values:{brand:'Vivo',model:'Regular',color:'Washed Blue',sizes:'31,32,33',sellingPrice:'190000',sewingRate:'14500',commissionRate:'1900',specialCommissionRate:'',effectiveFrom:'2026-07-15'},bom:defaultBom('73002'),dependencies:[{label:'FG ON HAND',value:'180 pcs',tone:'safe'},{label:'BOM AKTIF',value:'Versi 4',tone:'neutral'},{label:'WIP BERJALAN',value:'3 batch',tone:'warn'}],audit:seedAudit('Warna identitas diselaraskan dengan Final SKU')},
  {id:'prd-wid-73006',code:'73006',name:'Widie Workwear',active:false,rowVersion:4,updatedAt:'18 Agu 2026',values:{brand:'Widie',model:'Workwear',color:'Stone',sizes:'34,35,36',sellingPrice:'198000',sewingRate:'15500',commissionRate:'2000',specialCommissionRate:'',effectiveFrom:'2026-06-01'},bom:defaultBom('73006'),dependencies:[{label:'FG ON HAND',value:'90 pcs',tone:'warn'},{label:'BOM AKTIF',value:'Versi 3',tone:'neutral'},{label:'INVOICE TERBUKA',value:'0 nota',tone:'safe'}],audit:seedAudit('Dinonaktifkan untuk transaksi baru; histori tetap aktif')},
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
  {id:'wrk-afat',code:'MDR-AFAT',name:'Mandor Afat',active:true,rowVersion:8,updatedAt:'28 Agu 2026',values:{role:'Mandor',special:'false',phone:'0812 7110 0288',bank:'BCA · 1090 44xx',attendance:'Wajib',teamSize:'18'},dependencies:[{label:'WIP AKTIF',value:'4 batch',tone:'warn'},{label:'PAYROLL READY',value:'Rp18,7 jt',tone:'neutral'},{label:'KASBON AKSESORI',value:'Rp2,1 jt',tone:'warn'}],audit:seedAudit('Rekening pembayaran diverifikasi Owner')},
  {id:'wrk-epi',code:'MDR-EPI',name:'Mandor Epi',active:true,rowVersion:5,updatedAt:'27 Agu 2026',values:{role:'Mandor',special:'false',phone:'Belum diisi',bank:'Belum diisi',attendance:'Wajib',teamSize:'12'},dependencies:[{label:'WIP AKTIF',value:'2 batch',tone:'neutral'},{label:'PAYROLL READY',value:'Rp9,4 jt',tone:'neutral'},{label:'KASBON AKSESORI',value:'Rp860 rb',tone:'safe'}],audit:seedAudit('Mandor regular memakai komisi base dan alokasi absensi')},
  {id:'wrk-selo',code:'MDR-SELO',name:'Mandor Selo',active:true,rowVersion:4,updatedAt:'27 Agu 2026',values:{role:'Mandor',special:'false',phone:'Belum diisi',bank:'Belum diisi',attendance:'Wajib',teamSize:'14'},dependencies:[{label:'WIP AKTIF',value:'1 batch',tone:'neutral'},{label:'PAYROLL READY',value:'Rp7,8 jt',tone:'neutral'},{label:'KASBON AKSESORI',value:'Rp720 rb',tone:'safe'}],audit:seedAudit('Mandor regular memakai komisi base dan alokasi absensi')},
  {id:'wrk-afui',code:'MDR-AFUI',name:'Mandor Afui',active:true,rowVersion:6,updatedAt:'28 Agu 2026',values:{role:'Mandor',special:'true',phone:'Belum diisi',bank:'Belum diisi',attendance:'Tidak wajib',teamSize:'1'},dependencies:[{label:'WIP AKTIF',value:'2 batch',tone:'warn'},{label:'PAYROLL READY',value:'Komisi special',tone:'neutral'},{label:'AKSESORI SPECIAL',value:'Rp0 default',tone:'safe'}],audit:seedAudit('Flag Special aktif; tidak hardcode nama Mandor')},
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
  'master-products':{view:'master-products',eyebrow:'PRODUK & SKU',title:'Produk, Tarif & BOM',description:'Kelola identitas SKU, BOM kategori, harga jual, upah jahit, komisi base, dan komisi Special berbasis versi tanpa memutus HPP, stok, payroll, atau invoice.',browserLabel:'BROWSER SKU',singular:'produk',icon:Package,writerStatus:'Read-ready · writer produk masih simulasi',integrityTitle:'Identitas dan tarif SKU yang sudah bergerak tidak ditimpa.',integrityCopy:'Perubahan kode, size, BOM, atau nominal menjadi versi penerus. FG, payroll, dan invoice lama tetap membaca snapshot sebelumnya.',emptyDependencyCopy:'SKU baru belum memiliki BOM, WIP, stok, payroll, atau invoice.',fields:[{key:'brand',label:'Merek',type:'select',options:['Vivo','Widie']},{key:'model',label:'Model',type:'text'},{key:'color',label:'Warna',type:'text'},{key:'sizes',label:'Ukuran aktif',type:'sizes',options:allSizes},{key:'sellingPrice',label:'Harga jual / pcs',type:'number',money:true},{key:'sewingRate',label:'Upah jahit / pcs',type:'number',money:true},{key:'commissionRate',label:'Komisi base / pcs',type:'number',money:true},{key:'specialCommissionRate',label:'Komisi Special / pcs',type:'number',money:true,optional:true,placeholder:'Kosong = tidak tersedia'},{key:'effectiveFrom',label:'Berlaku mulai',type:'date'}],seeds:productSeeds,metrics:(items)=>commonMetrics(items,{label:'BOM KATEGORI',value:'3 aktif',note:'Kancing · Resleting · Label',tone:'warn'})},
  'master-customers':{view:'master-customers',eyebrow:'PELANGGAN',title:'Pelanggan & Kredit',description:'Satu tempat untuk identitas toko, termin, limit kredit, dan dependency AR sebelum transaksi baru dibuat.',browserLabel:'BROWSER PELANGGAN',singular:'pelanggan',icon:Store,writerStatus:'Read-ready · save RPC aman belum dipasang',integrityTitle:'Nonaktif tidak menghapus piutang dan histori toko.',integrityCopy:'Perubahan termin atau limit hanya berlaku ke transaksi baru. Invoice, pembayaran, retur, dan AR lama tetap dapat ditelusuri.',emptyDependencyCopy:'Pelanggan baru belum memiliki invoice atau saldo AR.',fields:[{key:'city',label:'Kota',type:'text'},{key:'contact',label:'Kontak utama',type:'text'},{key:'phone',label:'Telepon',type:'text'},{key:'terms',label:'Termin (hari)',type:'number',suffix:'hari'},{key:'creditLimit',label:'Limit kredit',type:'number',money:true},{key:'priceTier',label:'Tier harga',type:'select',options:['Wholesale A','Wholesale B','Wholesale C']}],seeds:customerSeeds,metrics:(items)=>commonMetrics(items,{label:'LIMIT TERPAKAI',value:'Rp119,6 jt',note:'Dibentuk dari open AR',tone:'warn'})},
  'master-partners':{view:'master-partners',eyebrow:'SUPPLIER & VENDOR',title:'Supplier & Vendor',description:'Pisahkan peran supplier kain, aksesori, dan vendor proses sambil menjaga AP, GRNI, UOM, serta kasus vendor tetap terhubung.',browserLabel:'BROWSER PARTNER',singular:'partner',icon:Truck,writerStatus:'Read-ready · safe writer partner belum lengkap',integrityTitle:'Default UOM hanya preferensi, bukan konversi transaksi.',integrityCopy:'Setiap receipt menyimpan UOM aktualnya sendiri. Invoice final mengikuti receipt yang di-match dan tidak boleh mengubah kuantitas fisik.',emptyDependencyCopy:'Partner baru belum memiliki receipt, AP, WIP vendor, atau klaim.',fields:[{key:'partnerType',label:'Tipe partner',type:'select',options:['Supplier Kain','Supplier Aksesori','Vendor Laundry','Vendor Lain']},{key:'city',label:'Kota',type:'text'},{key:'contact',label:'Kontak utama',type:'text'},{key:'phone',label:'Telepon',type:'text'},{key:'terms',label:'Termin (hari)',type:'number',suffix:'hari'},{key:'defaultUom',label:'Preferensi UOM',type:'select',options:['yard','meter','pcs','lusin','gross']}],seeds:partnerSeeds,metrics:(items)=>commonMetrics(items,{label:'GRNI UNMATCHED',value:'4 receipt',note:'Menunggu invoice final',tone:'warn'})},
  'master-workforce':{view:'master-workforce',eyebrow:'MANDOR',title:'Master Mandor',description:'Kelola identitas, aturan absensi, dan flag Special Mandor tanpa hardcode nama. Roster pekerja ringan, riwayat rate, dan masa aktif pekerja dikelola langsung dari Payroll → Absensi.',browserLabel:'BROWSER MANDOR',singular:'mandor',icon:UsersRound,writerStatus:'Read-ready · safe writer Mandor belum lengkap',integrityTitle:'Mandor dengan WIP atau payroll tidak boleh dihapus.',integrityCopy:'Flag Special memilih komisi Special SKU dan harga Special aksesori pada transaksi baru. Snapshot batch dan Nota FG lama tidak dihitung ulang. Pekerja anak buah tidak dibuat di master global.',emptyDependencyCopy:'Mandor baru belum memiliki WIP, payroll, kasbon, atau roster pekerja.',fields:[{key:'role',label:'Peran',type:'select',options:['Mandor']},{key:'special',label:'Mandor Special',type:'boolean'},{key:'phone',label:'Telepon',type:'text'},{key:'bank',label:'Rekening / cara bayar',type:'text'},{key:'attendance',label:'Kebijakan absensi',type:'select',options:['Tidak wajib','Wajib']},{key:'teamSize',label:'Jumlah anggota tim',type:'number',suffix:'orang'}],seeds:workforceSeeds,metrics:(items)=>commonMetrics(items,{label:'MANDOR SPECIAL',value:String(items.filter((item)=>item.values.role==='Mandor'&&item.values.special==='true').length),note:'Dibaca dari checkbox, bukan nama',tone:'warn'})},
  'master-locations':{view:'master-locations',eyebrow:'GUDANG & LOKASI',title:'Gudang & Lokasi',description:'Susun hierarki gudang, area, dan rak sebagai scope Stock On Hand tanpa membuat konsep reservasi yang tidak ada di backend.',browserLabel:'BROWSER LOKASI',singular:'lokasi',icon:Warehouse,writerStatus:'Read-ready · safe writer lokasi belum lengkap',integrityTitle:'Lokasi berisi stok atau draft tidak boleh dinonaktifkan.',integrityCopy:'Pemindahan stok wajib melalui event mutasi. Edit lokasi tidak memindahkan quantity, tidak membuat reserved stock, dan tidak menulis ulang stock card.',emptyDependencyCopy:'Lokasi baru masih kosong dan belum menjadi tujuan transaksi.',fields:[{key:'locationType',label:'Tipe lokasi',type:'select',options:['Gudang','Area','Bin / Rak']},{key:'parent',label:'Lokasi induk',type:'text'},{key:'stockScope',label:'Scope stok',type:'select',options:['Finished Goods','Fabric Roll','Accessory','Mixed']},{key:'rackCount',label:'Kapasitas / jumlah rak',type:'number',suffix:'rak'}],seeds:locationSeeds,metrics:(items)=>commonMetrics(items,{label:'TOTAL ON HAND',value:'1.482 FG',note:'Plus 186 roll & aksesori',tone:'warn'})},
}

function MasterState({active}:{active:boolean}){return <em className={`md-state ${active?'active':'inactive'}`}>{active?'AKTIF':'NONAKTIF'}</em>}

function formatFieldValue(field:FieldDefinition,value:string){
  if(field.type==='boolean')return value==='true'?'SPECIAL':'REGULAR'
  if(field.money&&field.optional&&!value)return 'Belum diisi'
  if(field.money)return idr(value)
  if(field.type==='sizes')return value.split(',').filter(Boolean).map((size)=>`Size ${size}`).join(' · ')||'Belum dipilih'
  return `${value||'—'}${value&&field.suffix?` ${field.suffix}`:''}`
}

function MasterHero({config}:{config:MasterConfig}){
  const Icon=config.icon
  return <section className="hero-copy compact md-hero"><div><div className="eyebrow">MASTER DATA · {config.eyebrow}</div><h1>{config.title}</h1><p>{config.description}</p></div><div className="md-contract"><Icon/><span><small>KONTRAK SAAT INI</small><strong>{config.writerStatus}</strong><em>UX ini simulasi sampai Auth dan RPC domain tersambung.</em></span></div></section>
}

function MoneyEditorInput({value,onChange,autoFocus=false}:{value:string;onChange:(value:string)=>void;autoFocus?:boolean}){
  return <div className="md-money-input"><b>Rp</b><input autoFocus={autoFocus} inputMode="numeric" value={formatMoneyInput(value)} onFocus={(event)=>event.currentTarget.select()} onChange={(event)=>onChange(cleanMoneyInput(event.target.value))}/></div>
}

function ModalHeader({eyebrow,title,copy,onClose}:{eyebrow:string;title:string;copy:string;onClose:()=>void}){
  return <header><div><span>{eyebrow}</span><h2>{title}</h2><p>{copy}</p></div><button type="button" aria-label="Tutup editor" onClick={onClose}><X/></button></header>
}

function SizeSelector({value,onChange}:{value:string;onChange:(value:string)=>void}){
  const selected=value.split(',').filter(Boolean)
  const toggle=(size:string)=>onChange(allSizes.filter((item)=>selected.includes(item)!==(item===size)).join(','))
  return <div className="md-size-selector">{sizeGroups.map((group)=><fieldset key={group[0]}><legend>SIZE {group[0]}–{group[group.length-1]}</legend><div>{group.map((size)=>{const checked=selected.includes(size);return <button type="button" className={checked?'active':''} aria-pressed={checked} key={size} onClick={()=>toggle(size)}><i>{checked&&<Check/>}</i><b>{size}</b></button>})}</div></fieldset>)}</div>
}

function MasterEditor({mode,config,entity,onClose,onSave}:{mode:'create'|'edit';config:MasterConfig;entity?:MasterEntity;onClose:()=>void;onSave:(draft:EditorDraft)=>void}){
  const [draft,setDraft]=useState<EditorDraft>(()=>({code:entity?.code??'',name:entity?.name??'',active:entity?.active??true,values:entity?.values??Object.fromEntries(config.fields.map((field)=>[field.key,field.type==='boolean'?'false':field.type==='sizes'?'':field.options?.[0]??'']))}))
  const update=(key:string,value:string)=>setDraft((current)=>{
    const values={...current.values,[key]:value}
    if(key==='role'&&value!=='Mandor')values.special='false'
    return {...current,values}
  })
  const valid=draft.code.trim().length>1&&draft.name.trim().length>2&&config.fields.every((field)=>field.optional&&!(draft.values[field.key]??'').trim()?true:field.type==='sizes'?(draft.values[field.key]??'').length>0:(draft.values[field.key]??'').trim().length>0)
  return <div className="md-backdrop" role="presentation" onMouseDown={(event)=>{if(event.target===event.currentTarget)onClose()}}><section className="md-modal" role="dialog" aria-modal="true" aria-label={`${mode==='create'?'Tambah':'Edit'} ${config.singular}`}>
    <ModalHeader eyebrow={mode==='create'?'MASTER BARU':'EDIT BER-VERSI'} title={mode==='create'?`Tambah ${config.singular}`:`Edit ${entity?.name}`} copy={mode==='create'?'Record baru dimulai tanpa dependency transaksi.':`row-version ${entity?.rowVersion} akan bertambah saat tersimpan.`} onClose={onClose}/>
    <div className="md-editor-grid"><label><span>KODE</span><input autoFocus value={draft.code} onChange={(event)=>setDraft((current)=>({...current,code:event.target.value}))}/></label><label><span>NAMA</span><input value={draft.name} onChange={(event)=>setDraft((current)=>({...current,name:event.target.value}))}/></label>{config.fields.map((field)=>field.type==='sizes'?<div className="md-size-field" key={field.key}><span>{field.label.toUpperCase()}</span><SizeSelector value={draft.values[field.key]??''} onChange={(value)=>update(field.key,value)}/></div>:field.type==='boolean'?<label className="md-boolean-field" key={field.key}><span>{field.label.toUpperCase()}</span><input type="checkbox" checked={draft.values[field.key]==='true'} disabled={draft.values.role!=='Mandor'} onChange={(event)=>update(field.key,String(event.target.checked))}/><span className="md-boolean-control"><i>{draft.values[field.key]==='true'&&<Check/>}</i><b>{draft.values[field.key]==='true'?'Special aktif':'Mandor regular'}</b><small>{draft.values.role==='Mandor'?'Pakai komisi Special SKU dan harga Special aksesori.':'Hanya tersedia untuk peran Mandor.'}</small></span></label>:<label key={field.key}><span>{field.label.toUpperCase()}{field.optional?' · OPSIONAL':''}</span>{field.type==='select'?<select value={draft.values[field.key]??''} onChange={(event)=>update(field.key,event.target.value)}>{field.options?.map((option)=><option key={option}>{option}</option>)}</select>:field.money?<MoneyEditorInput value={draft.values[field.key]??''} onChange={(value)=>update(field.key,value)}/>:<div><input type={field.type==='date'?'date':'text'} inputMode={field.type==='number'?'numeric':undefined} placeholder={field.placeholder} value={draft.values[field.key]??''} onChange={(event)=>update(field.key,field.type==='number'?event.target.value.replace(/\D/g,''):event.target.value)}/>{field.suffix&&<em>{field.suffix}</em>}</div>}</label>)}</div>
    <label className="md-active-toggle"><input type="checkbox" checked={draft.active} onChange={(event)=>setDraft((current)=>({...current,active:event.target.checked}))}/><span><i>{draft.active&&<Check/>}</i><strong>{draft.active?'Aktif untuk transaksi baru':'Nonaktif untuk transaksi baru'}</strong><small>Histori dan dependency lama tidak ikut hilang.</small></span></label>
    <div className="md-editor-warning"><AlertTriangle/><span><strong>Tidak ada hard delete</strong><small>Perubahan di layar ini hanya simulasi lokal. Writer backend baru boleh dipasang setelah kontrak aman tersedia.</small></span></div>
    <footer><button type="button" className="soft-btn" onClick={onClose}>Batal</button><button type="button" className="primary-btn" disabled={!valid} onClick={()=>onSave(draft)}>{mode==='create'?'Buat simulasi':'Simpan simulasi'}</button></footer>
  </section></div>
}

function ProductCostPanel({entity,categoryRates,onEditBom,onEditCategories}:{entity:MasterEntity;categoryRates:CategoryRate[];onEditBom:()=>void;onEditCategories:()=>void}){
  const sewing=Number(entity.values.sewingRate)||0
  const commission=Number(entity.values.commissionRate)||0
  const specialCommission=entity.values.specialCommissionRate
  const reimbursement=(entity.bom??[]).reduce((total,line)=>{const rate=categoryRates.find((item)=>item.category===line.category);return total+line.quantity*(rate?rateInUom(rate.reimbursement,rate.reimbursementUom,line.uom):0)},0)
  return <section className="md-product-cost"><header><div><span>MASTER TARIF SKU</span><strong>Snapshot biaya kerja & BOM kategori</strong></div><Calculator/></header><div className="md-rate-cards"><article><small>HARGA JUAL / PCS</small><strong>{idr(entity.values.sellingPrice)}</strong><em>Invoice baru</em></article><article><small>UPAH JAHIT / PCS</small><strong>{idr(entity.values.sewingRate)}</strong><em>Tarif kerja</em></article><article><small>KOMISI BASE / PCS</small><strong>{idr(entity.values.commissionRate)}</strong><em>Mandor regular</em></article><article className={`special ${specialCommission?'':'empty'}`}><small>KOMISI SPECIAL / PCS</small><strong>{specialCommission?idr(specialCommission):'Belum diisi'}</strong><em>Mandor ber-flag Special saja</em></article><article className="total"><small>TOTAL KERJA REGULAR / PCS</small><strong>{idr(String(sewing+commission))}</strong><em>Jahit + komisi base</em></article></div><div className="md-bom-head"><div><span>MASTER BOM PER SKU</span><strong>{entity.bom?.length??0} kategori · reimburse standar {idr(String(reimbursement))} / Good FG</strong></div><div><button type="button" className="soft-btn" onClick={onEditCategories}><Coins/> Tarif kategori</button><button type="button" className="soft-btn" onClick={onEditBom}><Pencil/> Edit BOM SKU</button></div></div><div className="md-bom-table"><div className="head"><span>KATEGORI BOM</span><span>QTY / GOOD FG</span><span>HARGA TAGIH MANDOR</span><span>TARIF REIMBURSE</span><span>BUFFER / UOM BOM</span></div>{(entity.bom??[]).map((line)=>{const rate=categoryRates.find((item)=>item.category===line.category);const charge=rate?rateInUom(rate.mandorCharge,rate.chargeUom,line.uom):0;const reimburse=rate?rateInUom(rate.reimbursement,rate.reimbursementUom,line.uom):0;const buffer=reimburse-charge;return <article key={line.id}><span><strong>{line.category}</strong><small>Stok detail & HPP tetap terpisah</small></span><b>{line.quantity} {line.uom}</b><span><strong>{idr(String(rate?.mandorCharge??0))}/{rate?.chargeUom??line.uom}</strong><small>Setara {idr(String(charge))}/{line.uom}</small></span><span><strong>{idr(String(rate?.reimbursement??0))}/{rate?.reimbursementUom??line.uom}</strong><small>Good FG × BOM</small></span><em className={buffer>=0?'positive':'negative'}>{buffer>=0?'+':''}{idr(String(buffer))}/{line.uom}</em></article>})}</div><div className="md-cost-rule"><ShieldCheck/><span><strong>Kancing Rp495/pcs vs Rp500/pcs · Resleting Rp29.900/lusin vs Rp2.500/pcs.</strong><small>Nominal dan UOM kedua rate independen. Flag Mandor Special membaca kolom Special SKU; BOM dan HPP moving average barang detail tetap terpisah.</small></span></div></section>
}

function BomEditorModal({entity,categoryRates,onClose,onSave}:{entity:MasterEntity;categoryRates:CategoryRate[];onClose:()=>void;onSave:(lines:BomLine[])=>void}){
  const [lines,setLines]=useState<BomLine[]>(()=>(entity.bom??[]).map((line)=>({...line})))
  const available=categoryRates.filter((rate)=>!lines.some((line)=>line.category===rate.category))
  const valid=lines.length>0&&lines.every((line)=>line.quantity>0)&&new Set(lines.map((line)=>line.category)).size===lines.length
  const addLine=()=>{const rate=available[0];if(rate)setLines((current)=>[...current,{id:`${entity.code}-${rate.category}-${Date.now()}`,category:rate.category,quantity:1,uom:rate.reimbursementUom}])}
  return <div className="md-backdrop" role="presentation"><section className="md-modal wide" role="dialog" aria-modal="true" aria-label="Edit BOM SKU"><ModalHeader eyebrow="MASTER BOM PER SKU" title={`${entity.code} · ${entity.name}`} copy="BOM menentukan standar reimburse per Good FG; tidak mengurangi stock card." onClose={onClose}/><div className="md-bom-editor"><div className="head"><span>KATEGORI</span><span>QTY / GOOD FG</span><span>UOM</span><span/></div>{lines.map((line)=><article key={line.id}><select aria-label={`Kategori ${line.category}`} value={line.category} onChange={(event)=>{const rate=categoryRates.find((item)=>item.category===event.target.value);setLines((current)=>current.map((item)=>item.id===line.id?{...item,category:event.target.value,uom:rate?.reimbursementUom??item.uom}:item))}}>{categoryRates.map((rate)=><option disabled={lines.some((item)=>item.id!==line.id&&item.category===rate.category)} key={rate.category}>{rate.category}</option>)}</select><input aria-label={`Quantity ${line.category}`} type="number" min="0.01" step="0.01" value={line.quantity} onChange={(event)=>setLines((current)=>current.map((item)=>item.id===line.id?{...item,quantity:Number(event.target.value)}:item))}/><span>{line.uom}</span><button type="button" aria-label={`Hapus ${line.category} dari BOM`} onClick={()=>setLines((current)=>current.filter((item)=>item.id!==line.id))}><Trash2/></button></article>)}</div><button type="button" className="md-add-line" disabled={available.length===0} onClick={addLine}><Plus/> Tambah kategori BOM</button><div className="md-editor-warning"><ShieldCheck/><span><strong>Versi penerus, bukan overwrite</strong><small>WIP/payroll lama tetap membaca snapshot BOM sebelumnya. Harga reimburse diatur pada master kategori, bukan diulang per SKU.</small></span></div><footer><button type="button" className="soft-btn" onClick={onClose}>Batal</button><button type="button" className="primary-btn" disabled={!valid} onClick={()=>onSave(lines)}>Simpan BOM simulasi</button></footer></section></div>
}

type CategoryRateDraft={category:string;chargeUom:string;reimbursementUom:string;mandorCharge:string;reimbursement:string;effectiveFrom:string;version:number}

function CategoryRateModal({rates,onClose,onSave}:{rates:CategoryRate[];onClose:()=>void;onSave:(rates:CategoryRate[])=>void}){
  const [drafts,setDrafts]=useState<CategoryRateDraft[]>(()=>rates.map((rate)=>({...rate,mandorCharge:String(rate.mandorCharge),reimbursement:String(rate.reimbursement)})))
  const [note,setNote]=useState('Penyesuaian tarif kategori')
  const update=(category:string,key:'mandorCharge'|'reimbursement'|'chargeUom'|'reimbursementUom'|'effectiveFrom',value:string)=>setDrafts((current)=>current.map((item)=>item.category===category?{...item,[key]:value}:item))
  const valid=note.trim().length>=4&&drafts.every((item)=>Number(item.mandorCharge)>0&&Number(item.reimbursement)>0&&item.effectiveFrom)
  return <div className="md-backdrop" role="presentation"><section className="md-modal wide" role="dialog" aria-modal="true" aria-label="Tarif kategori aksesori"><ModalHeader eyebrow="TARIF AKSESORI PER KATEGORI" title="Tagihan mandor & reimburse" copy="Dua nominal dan dua UOM independen; HPP pembelian serta moving average tidak ikut berubah." onClose={onClose}/><div className="md-category-editor"><div className="head"><span>KATEGORI</span><span>HARGA TAGIH MANDOR</span><span>TARIF REIMBURSE</span><span>BERLAKU MULAI</span></div>{drafts.map((item)=><article key={item.category}><span><strong>{item.category}</strong><small>versi {item.version}</small></span><div className="md-category-price"><MoneyEditorInput value={item.mandorCharge} onChange={(value)=>update(item.category,'mandorCharge',value)}/><select aria-label={`UOM harga jual ${item.category}`} value={item.chargeUom} onChange={(event)=>update(item.category,'chargeUom',event.target.value)}><option value="pcs">PCS</option><option value="lusin">LUSIN</option><option value="gross">GROSS</option><option value="pack">PACK</option><option value="box">BOX</option></select></div><div className="md-category-price"><MoneyEditorInput value={item.reimbursement} onChange={(value)=>update(item.category,'reimbursement',value)}/><select aria-label={`UOM reimburse ${item.category}`} value={item.reimbursementUom} onChange={(event)=>update(item.category,'reimbursementUom',event.target.value)}><option value="pcs">PCS</option><option value="lusin">LUSIN</option><option value="gross">GROSS</option><option value="pack">PACK</option><option value="box">BOX</option></select></div><input type="date" value={item.effectiveFrom} onChange={(event)=>update(item.category,'effectiveFrom',event.target.value)}/></article>)}</div><label className="md-modal-note"><span>CATATAN SINGKAT</span><textarea value={note} onChange={(event)=>setNote(event.target.value)}/></label><div className="md-editor-warning"><Coins/><span><strong>Kancing Rp495/pcs vs Rp500/pcs · Resleting Rp29.900/lusin vs Rp2.500/pcs</strong><small>Tagihan menilai kuantitas aktual yang diambil. Reimburse membayar standar BOM dari Good FG; UOM masing-masing disimpan pada snapshot rate.</small></span></div><footer><button type="button" className="soft-btn" onClick={onClose}>Batal</button><button type="button" className="primary-btn" disabled={!valid} onClick={()=>onSave(drafts.map((item)=>({...item,mandorCharge:Number(item.mandorCharge),reimbursement:Number(item.reimbursement),version:item.version+1})))}>Simpan versi tarif</button></footer></section></div>
}

type BulkRateKey='sellingPrice'|'sewingRate'|'commissionRate'|'specialCommissionRate'
const bulkRateFields:[BulkRateKey,string][]=[['sellingPrice','Harga jual'],['sewingRate','Upah jahit'],['commissionRate','Komisi base'],['specialCommissionRate','Komisi Special']]
const bulkRateValue=(key:BulkRateKey,value:string)=>key==='specialCommissionRate'&&!value?'Kosong':idr(value)

function BulkRateModal({entities,selectedIds,onClose,onApply}:{entities:MasterEntity[];selectedIds:string[];onClose:()=>void;onApply:(values:Partial<Record<BulkRateKey,string>>,effectiveFrom:string,note:string)=>void}){
  const selected=entities.filter((item)=>selectedIds.includes(item.id))
  const [enabled,setEnabled]=useState<Record<BulkRateKey,boolean>>({sellingPrice:true,sewingRate:false,commissionRate:false,specialCommissionRate:false})
  const [values,setValues]=useState<Record<BulkRateKey,string>>({sellingPrice:selected[0]?.values.sellingPrice??'',sewingRate:selected[0]?.values.sewingRate??'',commissionRate:selected[0]?.values.commissionRate??'',specialCommissionRate:selected[0]?.values.specialCommissionRate??''})
  const [effectiveFrom,setEffectiveFrom]=useState(today)
  const [note,setNote]=useState('Pembaruan tarif SKU terpilih')
  const changes=bulkRateFields.filter(([key])=>enabled[key])
  const valid=selected.length>0&&changes.length>0&&changes.every(([key])=>Number(values[key])>0)&&Boolean(effectiveFrom)&&note.trim().length>=4
  return <div className="md-backdrop" role="presentation"><section className="md-modal wide" role="dialog" aria-modal="true" aria-label="Update tarif SKU massal"><ModalHeader eyebrow="BULK UPDATE · ATOMIK" title={`${selected.length} SKU terpilih`} copy="Centang hanya nominal yang ingin diubah, lalu review semua SKU sebelum apply." onClose={onClose}/><div className="md-bulk-fields">{bulkRateFields.map(([key,label])=><article className={enabled[key]?'active':''} key={key}><label><input type="checkbox" checked={enabled[key]} onChange={(event)=>setEnabled((current)=>({...current,[key]:event.target.checked}))}/><span><i>{enabled[key]&&<Check/>}</i><strong>{label}</strong><small>{enabled[key]?'Akan diperbarui':'Tetap memakai tarif lama'}</small></span></label>{enabled[key]&&<MoneyEditorInput value={values[key]} onChange={(value)=>setValues((current)=>({...current,[key]:value}))}/>}</article>)}</div><div className="md-bulk-meta"><label><span>BERLAKU MULAI</span><input type="date" value={effectiveFrom} onChange={(event)=>setEffectiveFrom(event.target.value)}/></label><label><span>CATATAN SINGKAT</span><input value={note} onChange={(event)=>setNote(event.target.value)}/></label></div><div className="md-bulk-preview"><header><span>PREVIEW PER SKU</span><strong>{changes.length} kolom berubah · tidak ada partial apply</strong></header>{selected.map((item)=><article key={item.id}><span><strong>{item.code} · {item.name}</strong><small>row-version {item.rowVersion} → {item.rowVersion+1}</small></span>{changes.map(([key,label])=><em key={key}><small>{label}</small><b>{bulkRateValue(key,item.values[key]??'')} → {bulkRateValue(key,values[key])}</b></em>)}</article>)}</div><div className="md-editor-warning"><ShieldCheck/><span><strong>Satu aksi atomik saat backend tersambung</strong><small>Jika satu SKU mengalami version conflict, seluruh batch harus gagal. Komisi Special tetap kosong pada SKU yang tidak dipilih.</small></span></div><footer><button type="button" className="soft-btn" onClick={onClose}>Batal</button><button type="button" className="primary-btn" disabled={!valid} onClick={()=>onApply(Object.fromEntries(changes.map(([key])=>[key,values[key]])),effectiveFrom,note)}>Apply {selected.length} SKU</button></footer></section></div>
}

function BrowserRecord({item,active,config,bulkSelected,onSelect,onToggleBulk}:{item:MasterEntity;active:boolean;config:MasterConfig;bulkSelected:boolean;onSelect:()=>void;onToggleBulk:()=>void}){
  const EntityIcon=config.icon
  const product=config.view==='master-products'
  return <article className={`md-browser-record ${active?'active':''} ${product?'with-check':''}`}>{product&&<label className="md-bulk-check"><input type="checkbox" checked={bulkSelected} disabled={!item.active} onChange={onToggleBulk}/><i>{bulkSelected&&<Check/>}</i><span className="sr-only">Pilih {item.code} untuk update massal</span></label>}<button type="button" className="md-browser-select" onClick={onSelect}><i><EntityIcon/></i><span><strong>{item.name}</strong><small>{item.code}</small><em>{config.fields.slice(0,2).map((field)=>formatFieldValue(field,item.values[field.key]??'')).filter(Boolean).join(' · ')}</em></span><MasterState active={item.active}/></button></article>
}

function MasterWorkspace({config}:{config:MasterConfig}){
  const [entities,setEntities]=useState(config.seeds)
  const [selectedId,setSelectedId]=useState(config.seeds[0].id)
  const [query,setQuery]=useState('')
  const [status,setStatus]=useState<'ALL'|'ACTIVE'|'INACTIVE'>('ALL')
  const [editorMode,setEditorMode]=useState<'create'|'edit'|null>(null)
  const [notice,setNotice]=useState('')
  const [bulkSelectedIds,setBulkSelectedIds]=useState<string[]>([])
  const [bulkOpen,setBulkOpen]=useState(false)
  const [bomOpen,setBomOpen]=useState(false)
  const [categoryOpen,setCategoryOpen]=useState(false)
  const [categoryRates,setCategoryRates]=useState(categoryRateSeeds)
  const isProduct=config.view==='master-products'
  const selected=entities.find((item)=>item.id===selectedId)??entities[0]
  const visible=useMemo(()=>entities.filter((item)=>`${item.code} ${item.name} ${Object.values(item.values).join(' ')}`.toLowerCase().includes(query.toLowerCase())&&(status==='ALL'||item.active===(status==='ACTIVE'))),[entities,query,status])
  const visibleActiveIds=visible.filter((item)=>item.active).map((item)=>item.id)
  const allVisibleSelected=visibleActiveIds.length>0&&visibleActiveIds.every((id)=>bulkSelectedIds.includes(id))
  const metrics=config.metrics(entities)
  const save=(draft:EditorDraft)=>{
    if(editorMode==='create'){
      const next:MasterEntity={id:`${config.view}-${Date.now()}`,code:draft.code.trim(),name:draft.name.trim(),active:draft.active,rowVersion:1,updatedAt:today,values:draft.values,bom:isProduct?[]:undefined,dependencies:[],audit:[{at:'29 Agu 2026 · sekarang',actor:'Owner',action:'Master dibuat sebagai simulasi lokal'}]}
      setEntities((current)=>[next,...current]);setSelectedId(next.id);setNotice(`${next.name} dibuat sebagai simulasi. Backend belum berubah.`)
    }else{
      setEntities((current)=>current.map((item)=>item.id===selected.id?{...item,code:draft.code.trim(),name:draft.name.trim(),active:draft.active,values:draft.values,rowVersion:item.rowVersion+1,updatedAt:today,audit:[{at:'29 Agu 2026 · sekarang',actor:'Owner',action:'Identitas dan tarif diperbarui sebagai simulasi lokal'},...item.audit]}:item))
      setNotice(`${draft.name.trim()} diperbarui sebagai simulasi; dependency dan histori tetap utuh.`)
    }
    setEditorMode(null)
  }
  const saveBom=(lines:BomLine[])=>{
    setEntities((current)=>current.map((item)=>item.id===selected.id?{...item,bom:lines,rowVersion:item.rowVersion+1,updatedAt:today,audit:[{at:'29 Agu 2026 · sekarang',actor:'Owner',action:'BOM kategori SKU dibuat sebagai versi penerus'},...item.audit]}:item))
    setBomOpen(false);setNotice(`BOM ${selected.code} diperbarui sebagai simulasi; stock card dan HPP tidak berubah.`)
  }
  const saveCategoryRates=(rates:CategoryRate[])=>{
    setCategoryRates(rates);setCategoryOpen(false);setNotice('Tarif kategori aksesori diperbarui sebagai simulasi versi penerus.')
  }
  const applyBulk=(values:Partial<Record<BulkRateKey,string>>,effectiveFrom:string,note:string)=>{
    setEntities((current)=>current.map((item)=>bulkSelectedIds.includes(item.id)?{...item,values:{...item.values,...values,effectiveFrom},rowVersion:item.rowVersion+1,updatedAt:today,audit:[{at:'29 Agu 2026 · sekarang',actor:'Owner',action:`Bulk rate: ${note}`},...item.audit]}:item))
    setBulkOpen(false);setNotice(`${bulkSelectedIds.length} SKU diperbarui atomik dalam simulasi. Backend belum berubah.`);setBulkSelectedIds([])
  }
  const toggleBulk=(id:string)=>setBulkSelectedIds((current)=>current.includes(id)?current.filter((item)=>item!==id):[...current,id])
  const toggleAllVisible=()=>setBulkSelectedIds((current)=>allVisibleSelected?current.filter((id)=>!visibleActiveIds.includes(id)):[...new Set([...current,...visibleActiveIds])])
  const EntityIcon=config.icon
  return <>
    <MasterHero config={config}/>
    <section className="md-metrics">{metrics.map((metric)=><article className={metric.tone??''} key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong><small>{metric.note}</small></article>)}</section>
    <section className="panel md-workspace"><aside>
      <header><div><span>{config.browserLabel}</span><strong>{visible.length} dari {entities.length}</strong></div><EntityIcon/></header>
      <div className="md-browser-tools"><label><Search/><input value={query} onChange={(event)=>setQuery(event.target.value)} placeholder={`Cari ${config.singular}, kode, detail...`}/></label><select aria-label="Filter status" value={status} onChange={(event)=>setStatus(event.target.value as typeof status)}><option value="ALL">Semua status</option><option value="ACTIVE">Aktif</option><option value="INACTIVE">Nonaktif</option></select></div>
      {isProduct&&<div className="md-bulk-toolbar"><button type="button" className={allVisibleSelected?'active':''} onClick={toggleAllVisible}><i>{allVisibleSelected&&<Check/>}</i>{allVisibleSelected?'Batal pilih tampil':'Pilih SKU tampil'}</button><strong>{bulkSelectedIds.length} dipilih</strong><button type="button" className="primary-btn" disabled={bulkSelectedIds.length===0} onClick={()=>setBulkOpen(true)}>Update harga massal</button></div>}
      <div className="md-browser-list">{visible.map((item)=><BrowserRecord item={item} active={item.id===selected.id} config={config} bulkSelected={bulkSelectedIds.includes(item.id)} key={item.id} onToggleBulk={()=>toggleBulk(item.id)} onSelect={()=>{setSelectedId(item.id);setNotice('')}}/>)}{visible.length===0&&<div className="md-empty"><Search/><strong>Tidak ada hasil</strong><small>Ubah kata pencarian atau filter status.</small></div>}</div>
      <footer><button type="button" onClick={()=>setEditorMode('create')}><Plus/> Tambah {config.singular}</button><small>Simulasi lokal · belum menulis backend.</small></footer>
    </aside><main>
      <header className="md-detail-head"><div><span>IDENTITAS MASTER</span><h2>{selected.name}</h2><p>{selected.code} · terakhir diperbarui {selected.updatedAt}</p></div><div><MasterState active={selected.active}/><small>row-version {selected.rowVersion}</small></div></header>
      <div className="md-facts">{config.fields.map((field,index)=>{const icons=[Tags,Layers3,BadgeDollarSign,CalendarClock,Database,MapPin];const FactIcon=icons[index%icons.length];return <article className={field.type==='sizes'?'wide':field.type==='boolean'?'boolean':''} key={field.key}><FactIcon/><span><small>{field.label.toUpperCase()}</small><strong>{formatFieldValue(field,selected.values[field.key]??'')}</strong></span></article>})}</div>
      {isProduct&&<ProductCostPanel entity={selected} categoryRates={categoryRates} onEditBom={()=>setBomOpen(true)} onEditCategories={()=>setCategoryOpen(true)}/>} 
      <section className="md-integrity"><ShieldCheck/><span><strong>{config.integrityTitle}</strong><small>{config.integrityCopy}</small></span></section>
      <section className="md-dependencies"><header><div><span>DEPENDENCY CHECK</span><strong>Dampak sebelum nonaktif / koreksi</strong></div><Link2/></header>{selected.dependencies.length>0?<div>{selected.dependencies.map((dependency)=><article className={dependency.tone} key={dependency.label}><span>{dependency.label}</span><strong>{dependency.value}</strong></article>)}</div>:<div className="md-no-dependency"><CheckCircle2/><span><strong>Belum ada dependency</strong><small>{config.emptyDependencyCopy}</small></span></div>}</section>
      <section className="md-audit"><header><div><span>AUDIT TRAIL</span><strong>Perubahan identitas terakhir</strong></div><History/></header>{selected.audit.map((entry)=><article key={`${entry.at}-${entry.action}`}><i/><span><strong>{entry.action}</strong><small>{entry.at} · {entry.actor}</small></span></article>)}</section>
      {notice&&<div className="md-notice"><CheckCircle2/><span>{notice}</span><button type="button" aria-label="Tutup pemberitahuan" onClick={()=>setNotice('')}><X/></button></div>}
      <footer className="md-actions"><span><LockKeyhole/> Record bertransaksi dijaga lewat nonaktif dan versi.</span><button type="button" className="soft-btn" onClick={()=>setEditorMode('edit')}><Pencil/> Edit / nonaktifkan</button></footer>
    </main></section>
    {editorMode&&<MasterEditor key={`${editorMode}-${selected.id}`} mode={editorMode} config={config} entity={editorMode==='edit'?selected:undefined} onClose={()=>setEditorMode(null)} onSave={save}/>} 
    {bomOpen&&<BomEditorModal entity={selected} categoryRates={categoryRates} onClose={()=>setBomOpen(false)} onSave={saveBom}/>} 
    {categoryOpen&&<CategoryRateModal rates={categoryRates} onClose={()=>setCategoryOpen(false)} onSave={saveCategoryRates}/>} 
    {bulkOpen&&<BulkRateModal entities={entities} selectedIds={bulkSelectedIds} onClose={()=>setBulkOpen(false)} onApply={applyBulk}/>} 
  </>
}

export default function MasterDataPages({view}:{view:BusinessMasterView}){
  return <MasterWorkspace key={view} config={masterConfigs[view]}/>
}

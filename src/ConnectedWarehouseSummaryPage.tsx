import {useCallback,useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isPageAllowed} from './auth/accessCatalog'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import {normalizeClientError} from './lib/clientError'
import {formatCp6WibDateTime} from './cp6BusinessTime'
import {formatReceiptDecimal as numberText} from './procurementContract'
import {isScreenHidden,SCREEN_ACTIVATION} from './screenActivation'
import {moneyText,parseWarehouseSummary,summaryAccess,type AccessoryPart,type Attention,type FgPart,type MaterialPart,type SummaryValuation,type WarehouseMenu,type WarehouseSummary} from './warehouseSummaryContract'
import './procurement-connected.css'
import './warehouse-summary.css'

// R3-03 (owner D16-1): Ringkasan Gudang from real stock. One read (erp_cp7_get_warehouse_summary_v1) sums the rows of
// Bahan & Roll, Aksesori and Ringkasan Barang Jadi per location; each part shows only with its screen's key, values only
// with finance.hpp.view. No sample figure: while loading or after an error nothing is shown but the message.
const PAGE_SIZE=25
const locationTypes:Record<string,string>={RAW_MATERIAL_WAREHOUSE:'Gudang bahan',FG_WAREHOUSE:'Gudang barang jadi',CUTTING_WIP:'Area potong'}
const zones:Record<string,string>={SERVICE_POST:'Pos jasa aksesori',INSPECTION:'Area pemeriksaan',DAMAGED:'Area barang rusak'}
const qty=(v:string,unit:string)=>`${numberText(v)} ${unit}`
const rupiah=(v:string)=>'Rp'+numberText(moneyText(v))
function attentionText(a:Attention){
 const n=numberText(a.count)
 switch(a.kind){
  case 'MATERIAL_BALANCE_REVIEW':return `${n} saldo bahan perlu diperiksa (jumlahnya minus atau roll-nya tidak cocok dengan bahannya).`
  case 'ACCESSORY_OUTSIDE_ACCESSORY_LOCATIONS':return `${n} saldo aksesori ada di lokasi yang tidak tampil di layar Aksesori (gudang nonaktif atau bukan gudang bahan). Saldo ini terlihat di Bahan & Roll.`
  case 'ACCESSORY_NEGATIVE':return `${n} saldo aksesori minus.`
  case 'FG_POSITION_REVIEW':return `${n} posisi barang jadi perlu diperiksa (jumlahnya minus atau lot-nya tidak cocok dengan barangnya).`
  case 'FABRIC_BELOW_MINIMUM':return `${n} kain di bawah stok minimum yang diisi di Kain & Benchmark (stok dihitung dari semua lokasi di Bahan & Roll).`
  case 'RECEIPT_DRAFT':return `${n} penerimaan bahan masih draft, jadi belum masuk stok.`
  case 'MATERIAL_TRANSFER_DRAFT':return `${n} transfer bahan masih draft, jadi stoknya belum pindah.`
  case 'MATERIAL_COUNT_DRAFT':return `${n} hitung fisik atau penyesuaian bahan masih draft.`
  case 'FG_ADJUSTMENT_DRAFT':return `${n} penyesuaian barang jadi masih draft.`
 }
}
const checked:Record<Attention['kind'],string>={MATERIAL_BALANCE_REVIEW:'saldo bahan',ACCESSORY_OUTSIDE_ACCESSORY_LOCATIONS:'lokasi aksesori',ACCESSORY_NEGATIVE:'saldo aksesori',
 FG_POSITION_REVIEW:'posisi barang jadi',FABRIC_BELOW_MINIMUM:'stok minimum kain',RECEIPT_DRAFT:'draft penerimaan',MATERIAL_TRANSFER_DRAFT:'draft transfer',
 MATERIAL_COUNT_DRAFT:'draft hitung fisik bahan',FG_ADJUSTMENT_DRAFT:'draft penyesuaian barang jadi'}

export default function ConnectedWarehouseSummaryPage({onNavigate}:{onNavigate?:(page:WarehouseMenu)=>void}={}){
 const {runtime,identity}=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')return <section className="panel" role="alert">Masuk ke ERP untuk melihat ringkasan gudang.</section>
 if(!identity.permissions.includes('warehouse.dashboard.view'))return <section className="panel" role="alert">Hak melihat ringkasan gudang belum diberikan.</section>
 return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`} onNavigate={onNavigate}/>
}

function Workspace({onNavigate}:{onNavigate?:(page:WarehouseMenu)=>void}){
 const {runtime,identity}=useAuth();if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')throw Error('Sesi gudang belum siap.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime]),access=useMemo(()=>summaryAccess(identity.permissions),[identity.permissions])
 const seq=useRef(0),requested=useRef({q:'',offset:0})
 const [search,setSearch]=useState(''),[data,setData]=useState<WarehouseSummary|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const load=useCallback(async()=>{
  const query={...requested.current},ticket=++seq.current;setData(null);setBusy(true);setError('')
  try{
   const result=await client.rpc('erp_cp7_get_warehouse_summary_v1',{p_query:{q:query.q,offset:query.offset,limit:PAGE_SIZE}})
   if(ticket!==seq.current)return
   if(result.error)throw result.error
   const read=parseWarehouseSummary(result.data,access)
   if(read.q!==query.q||read.page.offset!==query.offset||read.page.limit!==PAGE_SIZE)throw Error('Pencarian berubah. Muat ulang ringkasan.')
   setData(read)
  }catch(e){if(ticket===seq.current){setData(null);setError(normalizeClientError(e).message)}}
  finally{if(ticket===seq.current)setBusy(false)}
 },[client,access])
 useEffect(()=>{void load();return()=>{++seq.current}},[load])
 const go=(offset:number)=>{requested.current={...requested.current,offset};void load()}
 const open=(menu:WarehouseMenu)=>onNavigate&&isPageAllowed(identity,menu)&&!isScreenHidden(runtime.mode,menu)?<button type="button" disabled={busy} onClick={()=>onNavigate(menu)}>Buka {SCREEN_ACTIVATION[menu].label}</button>:null
 const searched=data?.q?' sesuai pencarian':''
 const hidden=[!access.materials&&'Bahan & Roll',!access.accessories&&'Aksesori',!access.finished_goods&&'Ringkasan Barang Jadi'].filter(Boolean) as string[]
 const visibleChecks=data?.attention??[],open_items=visibleChecks.filter(a=>a.count!=='0')
 return <main className="cproc cwhs" aria-label="Ringkasan gudang">
  <header className="panel cproc-heading"><div><div className="eyebrow">GUDANG</div><h1>Ringkasan Gudang</h1><p>Stok per gudang dari catatan stok yang sudah disahkan. Angkanya sama dengan layar rinciannya; draft belum dihitung sebagai stok.</p></div>
   <button type="button" disabled={busy} onClick={()=>void load()}>Muat ulang ringkasan</button></header>
  <form className="panel cwhs-search" role="search" onSubmit={e=>{e.preventDefault();requested.current={q:search.trim(),offset:0};void load()}}>
   <label>Cari gudang (nama atau kode)<input aria-label="Cari gudang" maxLength={120} value={search} onChange={e=>{++seq.current;setData(null);setBusy(false);setError('');setSearch(e.target.value)}}/></label>
   <div className="cproc-inline"><button type="submit" disabled={busy}>Cari gudang</button><button type="button" disabled={busy} onClick={()=>{setSearch('');requested.current={q:'',offset:0};void load()}}>Semua gudang</button></div>
  </form>
  {busy?<p role="status">Membaca stok gudang…</p>:null}
  {error?<p className="panel" role="alert">{error} Angka gudang tidak ditampilkan sampai data terbaca lengkap.</p>:null}
  {data?<>
   <section className="panel" aria-label="Dasar ringkasan gudang"><p>Dibaca {formatCp6WibDateTime(data.read_at)}{data.q?` · pencarian "${data.q}"`:''}. Aksesori dihitung di bagian Aksesori saja, tidak di Bahan & Roll.</p>
    {!access.finance?<p>Nilai stok tidak ditampilkan karena hak melihat HPP belum diberikan.</p>:null}
    {hidden.length?<p>Bagian {hidden.join(', ')} tidak ditampilkan karena hak melihat layar tersebut belum diberikan.</p>:null}</section>
   {!access.materials&&!access.accessories&&!access.finished_goods?<p className="panel">Anda belum punya hak melihat stok bahan, aksesori, atau barang jadi.</p>:
   <section className="cwhs-totals" aria-label="Total gudang">
    {data.totals.materials?<article className="panel" aria-label="Total bahan dan roll"><h2>Bahan & Roll{searched}</h2><MaterialLines part={data.totals.materials}/>{open('materials-rolls')}</article>:null}
    {data.totals.accessories?<article className="panel" aria-label="Total aksesori"><h2>Aksesori{searched}</h2><AccessoryLines part={data.totals.accessories}/>{open('accessories')}</article>:null}
    {data.totals.finished_goods?<article className="panel" aria-label="Total barang jadi"><h2>Barang jadi{searched}</h2><FgLines part={data.totals.finished_goods}/>{open('fg-summary')}</article>:null}
   </section>}
   <section className="panel" aria-label="Perlu diperhatikan"><h2>Perlu diperhatikan</h2>
    {open_items.length?<ul className="cwhs-attention">{open_items.map(a=><li key={a.kind} data-attention={a.kind}><p>{attentionText(a)}</p>
     {a.rows?.length?<ul>{a.rows.map(r=><li key={r.material_id}>{r.material_sku} · {r.material_name}: stok {qty(r.qty,r.unit_code)}, minimum {qty(r.minimum_qty,r.unit_code)}</li>)}</ul>:null}
     {a.rows&&Number(a.count)>a.rows.length?<small>Menampilkan {a.rows.length} kain pertama.</small>:null}{open(a.menu)}</li>)}</ul>
     :<p>Tidak ada yang perlu diperhatikan dari pemeriksaan ini.</p>}
    {visibleChecks.length?<small>Diperiksa untuk seluruh gudang: {visibleChecks.map(a=>checked[a.kind]).join(', ')}.</small>:<small>Belum ada pemeriksaan yang boleh Anda lihat.</small>}
   </section>
   <section className="panel" aria-label="Stok per gudang"><h2>Per gudang</h2>
    {!data.page.rows.length?<p>{data.q?'Tidak ada gudang berisi stok yang cocok dengan pencarian.':'Belum ada stok di gudang yang bisa Anda lihat.'}</p>:null}
    {data.page.rows.map(l=><article className="cwhs-location" key={l.location_id} data-location-id={l.location_id} aria-label={`Stok ${l.location_name}`}>
     <header><div><h3>{l.location_name}</h3><small>{[l.location_code,locationTypes[l.location_type]??'Lokasi lain',l.zone_kind?zones[l.zone_kind]??'Zona khusus':null,l.is_active?null:'Nonaktif'].filter(Boolean).join(' · ')}</small></div></header>
     <div className="cwhs-parts">
      {l.materials?.lines.length?<div><h4>Bahan & Roll</h4><MaterialLines part={l.materials}/></div>:null}
      {l.accessories?.lines.length?<div><h4>Aksesori</h4><AccessoryLines part={l.accessories}/></div>:null}
      {l.finished_goods&&l.finished_goods.positions!=='0'?<div><h4>Barang jadi</h4><FgLines part={l.finished_goods}/></div>:null}
     </div></article>)}
    <div className="cproc-pagination"><span>Total {numberText(data.page.total)} gudang berisi stok</span><button type="button" disabled={busy||data.page.offset===0} onClick={()=>go(Math.max(0,data.page.offset-PAGE_SIZE))}>Gudang sebelumnya</button><button type="button" disabled={busy||data.page.next_offset===null} onClick={()=>go(data.page.next_offset??0)}>Gudang berikutnya</button></div>
   </section>
  </>:null}
 </main>
}

function Value({valuation,what}:{valuation?:SummaryValuation;what:string}){
 if(!valuation)return null
 return <p className="cwhs-value">Nilai {what} {rupiah(valuation.value)}{valuation.unknown_count!=='0'?` · ${numberText(valuation.unknown_count)} saldo belum diketahui nilainya (tidak dihitung)`:''}</p>
}
function MaterialLines({part}:{part:MaterialPart}){
 if(!part.lines.length)return <p>Tidak ada stok bahan.</p>
 return <><ul className="cwhs-lines">{part.lines.map(l=><li key={l.kind+':'+l.unit_code}><span>{l.kind==='FABRIC'?'Kain':'Bahan lain'}</span><strong>{qty(l.qty,l.unit_code)}</strong>
  <small>{l.kind==='FABRIC'?`${numberText(l.rolls)} roll berisi`:`${numberText(l.balances)} saldo`}{l.quality==='CONFLICT'?' · ada saldo yang perlu diperiksa':''}</small></li>)}</ul><Value valuation={part.valuation} what="bahan"/></>
}
function AccessoryLines({part}:{part:AccessoryPart}){
 if(!part.lines.length)return <p>Tidak ada stok aksesori.</p>
 return <><ul className="cwhs-lines">{part.lines.map(l=><li key={l.unit_code}><span>Aksesori</span><strong>{qty(l.qty,l.unit_code)}</strong>
  <small>{numberText(l.items)} jenis{l.quality==='CONFLICT'?' · ada saldo minus':''}</small></li>)}</ul><Value valuation={part.valuation} what="aksesori"/></>
}
function FgLines({part}:{part:FgPart}){
 if(part.positions==='0')return <p>Tidak ada stok barang jadi.</p>
 return <><ul className="cwhs-lines"><li><span>Fisik di gudang</span><strong>{qty(part.physical_qty,'pcs')}</strong><small>Dicadangkan {numberText(part.reserved_qty)} · tersedia {numberText(part.available_qty)}{part.quality==='CONFLICT'?' · ada posisi yang perlu diperiksa':''}</small></li></ul>
  {part.grades.length?<p className="cwhs-grades">{part.grades.map(g=>`${g.quality_grade.replaceAll('_',' ')} ${numberText(g.physical_qty)}`).join(' · ')} pcs</p>:null}<Value valuation={part.valuation} what="barang jadi"/></>
}

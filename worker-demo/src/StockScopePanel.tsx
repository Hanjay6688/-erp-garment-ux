import {useEffect,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {getUatSupabaseClient} from './lib/supabase'
type Item={item:string;category:string|null;sku:string;name:string;unit:string}
type Observation={monitored:boolean;at_or_below:boolean|null;location:string|null;stock:string;unit:string;threshold:string|null;enabled:boolean|null;scope_kind:string|null;revision:string|null}
type Version={kind:string;key:string;revision:string;reason:string;threshold:string|null;enabled:boolean}
type Workspace={domain:string;manage:boolean;items:Item[];locations:{id:string;name:string}[];observations:Observation[];history:Version[]}
const scopes:Record<string,string>={GLOBAL:'Semua barang dalam satuan ini',CATEGORY:'Kategori barang',TARGET:'Barang ini',ITEM_LOCATION:'Barang ini di gudang tertentu'}
const nativeScopes:Record<string,string>={NATIVE_MANUAL:'Ambang manual barang',NATIVE_FORMULA:'Rumus stok',NATIVE_ESTIMATE:'Perkiraan pemakaian'}
const errorText=(e:unknown)=>e&&typeof e==='object'&&'message'in e?String(e.message):'Data pengingat belum dapat dibaca.'
export default function StockScopePanel(){
 const {runtime,identity}=useAuth()
 if(runtime.mode!=='DISPOSABLE_TEST'||identity.status!=='AUTHORIZED')return null
 return <StockWorkspace key={[runtime.projectRef,identity.profile.id,identity.profile.rowVersion,identity.profile.roleRowVersion,...identity.permissions].join('|')}/>
}
function StockWorkspace(){
 const {runtime,identity}=useAuth()
 const domains=identity.status==='AUTHORIZED'?[...(identity.permissions.includes('warehouse.fg.view')?['FG']:[]),...(identity.permissions.includes('warehouse.accessory.view')?['ACCESSORY']:[]),...(identity.permissions.includes('warehouse.material.view')&&identity.permissions.includes('master.fabric.view')?['FABRIC']:[])]:[]
 const [open,setOpen]=useState(false),[domain,setDomain]=useState(domains[0]??''),[query,setQuery]=useState(''),[item,setItem]=useState(''),[location,setLocation]=useState('')
 const [kind,setKind]=useState('TARGET'),[limit,setLimit]=useState(''),[enabled,setEnabled]=useState(true),[reason,setReason]=useState(''),[message,setMessage]=useState('')
 const [ws,setWs]=useState<Workspace|null>(null),[saving,setSaving]=useState(false),[reading,setReading]=useState(false),[refresh,setRefresh]=useState(0)
 const serial=useRef(0),pending=useRef<{key:string;id:string}|null>(null)
 const selected=ws?.items.find(i=>i.item===item)
 const scopeKey=kind==='GLOBAL'?'*':kind==='CATEGORY'?selected?.category:kind==='TARGET'?item:item+':'+location
 const previous=ws?.history.find(r=>r.kind===kind&&r.key===scopeKey)?.revision??'0'
 useEffect(()=>{
  let current=true
  if(!open||!domain||runtime.mode!=='DISPOSABLE_TEST')return
  const seq=++serial.current;setReading(true);setMessage('');setWs(null)
  const timer=setTimeout(async()=>{
   try{const r=await getUatSupabaseClient(runtime).rpc('erp_cp7_stock_rule_workspace_v1',{p_domain:domain,p_query:query,p_item:item||null,p_location:location||null})
    if(r.error)throw r.error
    const w=r.data as unknown as Workspace
    if(!w||w.domain!==domain||typeof w.manage!=='boolean'||![w.items,w.locations,w.observations,w.history].every(Array.isArray))throw Error('Hasil gudang belum lengkap.')
    if(current&&seq===serial.current)setWs(w)
   }catch(e){if(current)setMessage(errorText(e))}finally{if(current)setReading(false)}
  },150)
  return()=>{current=false;clearTimeout(timer)}
 },[open,domain,query,item,location,refresh,runtime])
 async function save(){
  if(!ws?.manage||!selected||saving||reading||runtime.mode!=='DISPOSABLE_TEST')return
  const body={domain,kind,item,location:kind==='ITEM_LOCATION'?location:null,threshold:limit||null,enabled,expected_revision:previous,reason}
  const key=JSON.stringify(body)
  if(pending.current?.key!==key)pending.current={key,id:crypto.randomUUID()}
  setSaving(true);setMessage('')
  try{const r=await getUatSupabaseClient(runtime).rpc('erp_cp7_save_stock_rule_v1',{p:body,p_request:pending.current.id});if(r.error)throw r.error
   pending.current=null;setRefresh(n=>n+1);setReason('')
  }catch(e){setMessage(errorText(e))}finally{setSaving(false)}
 }
 if(!domains.length)return null
 return <section aria-label="Ambang stok per gudang"><button type="button" aria-expanded={open} disabled={saving} onClick={()=>setOpen(!open)}>Aturan stok per barang dan gudang</button>
  {open&&<><fieldset disabled={saving}><label>Jenis stok <select value={domain} onChange={e=>{setDomain(e.target.value);setItem('');setLocation('');setKind('TARGET')}}>{domains.map(d=><option key={d} value={d}>{{FG:'Barang jadi',ACCESSORY:'Aksesori',FABRIC:'Kain'}[d]}</option>)}</select></label>
  <label>Cari barang <input value={query} onChange={e=>{setQuery(e.target.value);setItem('')}}/></label>
  <label>Barang <select value={item} onChange={e=>{setItem(e.target.value);setLimit('');setReason('')}}><option value="">Pilih barang</option>{ws?.items.map(i=><option key={i.item} value={i.item}>{i.sku} · {i.name}</option>)}</select></label>
  <label>Gudang pembanding <select value={location} onChange={e=>setLocation(e.target.value)}><option value="">Seluruh gudang</option>{ws?.locations.map(l=><option key={l.id} value={l.id}>{l.name}</option>)}</select></label>
  {reading&&<p role="status">Membaca stok dan versi aturan…</p>}
  {selected&&<>{ws?.observations.map(o=><p key={o.location??'*'}>{o.location?(ws.locations.find(l=>l.id===o.location)?.name??o.location):'Seluruh gudang'} · {o.stock} {o.unit} · {o.location&&!o.monitored?'simulasi gudang, belum dipantau · ':''}{o.at_or_below===true?'mencapai ambang pengingat · ':o.at_or_below===false&&o.enabled?'di atas ambang · ':''}{o.scope_kind?`${scopes[o.scope_kind]??nativeScopes[o.scope_kind]??o.scope_kind}${o.revision?' versi '+o.revision:''} · ${o.enabled?'ambang '+(o.threshold??'belum diatur'):'dimatikan'}`:'belum ada aturan tetap'}</p>)}
  {ws?.manage&&<><label>Cakupan aturan <select value={kind} onChange={e=>setKind(e.target.value)}>{Object.entries(scopes).filter(([k])=>k!=='CATEGORY'||selected.category).map(([k,t])=><option key={k} value={k}>{k==='CATEGORY'&&domain==='FG'?'Kelompok model':t}</option>)}</select></label>
  <label>Ambang ({selected.unit}) <input inputMode="decimal" value={limit} onChange={e=>setLimit(e.target.value.replace(',','.'))}/></label>
  <label><input type="checkbox" checked={enabled} onChange={e=>setEnabled(e.target.checked)}/>Aktif</label>
  <label>Alasan perubahan <input value={reason} maxLength={500} onChange={e=>setReason(e.target.value)}/></label>
  <button type="button" disabled={!reason.trim()||reading||kind==='ITEM_LOCATION'&&!location} onClick={()=>void save()}>Simpan versi aturan stok</button></>}
  <details><summary>Riwayat aturan</summary>{ws?.history.map(h=><p key={h.kind+h.key+h.revision}>{scopes[h.kind]} · versi {h.revision} · {h.threshold??'belum diatur'} {selected.unit} · {h.reason}</p>)}</details></>}
  </fieldset>{message&&<p role="alert">{message}</p>}</>}
 </section>
}

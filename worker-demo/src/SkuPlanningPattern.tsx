import { sizeRangeLabel } from './sizeRangeLabel'
import {useEffect,useMemo,useRef,useState} from 'react'
import {useAuth} from './auth/AuthProvider'
import {isConnectedRuntime} from './config/runtime'
import {getUatSupabaseClient} from './lib/supabase'
import type {SkuGroup} from './skuMaster'

type Pattern={id:string;code:string;name:string;revision:string;active?:boolean}
type Catalog={group_id:string|null;revision:number;pattern:Pattern|null;options:Pattern[];total:number}
const isObject=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v)
const isUuid=(v:unknown):v is string=>typeof v==='string'&&/^[\da-f]{8}(?:-[\da-f]{4}){3}-[\da-f]{12}$/i.test(v)
const isPattern=(v:unknown):v is Pattern=>isObject(v)&&isUuid(v.id)&&['code','name','revision'].every(k=>typeof v[k]==='string')
export function parseSkuPattern(v:unknown):Catalog {
  if(!isObject(v)||v.group_id!==null&&!isUuid(v.group_id)||!Number.isSafeInteger(v.revision)||Number(v.revision)<0||v.pattern!==null&&(!isPattern(v.pattern)||typeof v.pattern.active!=='boolean')||!Array.isArray(v.options)||!v.options.every(isPattern)||!Number.isSafeInteger(v.total)||Number(v.total)<v.options.length)throw Error('Respons master pola belum sesuai.')
  return v as Catalog
}
type Command={p_group:string;p_pattern:string|null;p_version:number;p_request:string}
function readHeld(key:string,id:string):Command|null {
  const raw=sessionStorage.getItem(key);if(!raw)return null
  const v:unknown=JSON.parse(raw);if(!isObject(v)||v.p_group!==id||!isUuid(v.p_request)||v.p_pattern!==null&&!isUuid(v.p_pattern)||!Number.isSafeInteger(v.p_version)||Number(v.p_version)<0)throw Error('Catatan penyimpanan pola perlu diperiksa.')
  return v as Command
}
export function SkuPlanningPattern({group,canEdit}:{group:SkuGroup;canEdit:boolean}) {
  const {runtime,identity}=useAuth()
  if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED')return null
  return <Editor key={runtime.projectRef+identity.profile.id+group.id} group={group} canEdit={canEdit} storageKey={'cp8.sku-pattern.'+runtime.projectRef+'.'+identity.profile.id+'.'+group.id}/>
}
function Editor({group,canEdit,storageKey}:{group:SkuGroup;canEdit:boolean;storageKey:string}) {
  const {runtime}=useAuth();if(!isConnectedRuntime(runtime))throw Error('Sesi ERP belum siap.')
  const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime])
  const [data,setData]=useState<Catalog|null>(null),[query,setQuery]=useState(''),[page,setPage]=useState(0),[selected,setSelected]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false)
  const [held,setHeld]=useState(()=>!!sessionStorage.getItem(storageKey)),seq=useRef(0),posting=useRef(false)
  async function load(q:string,offset:number){const n=++seq.current;setBusy(true);setData(null);try{
    const r=await client.rpc('erp_cp8_get_sku_pattern_v1',{p_group:group.id,p_product:null,p_query:q,p_offset:offset});if(r.error)throw r.error
    const c=parseSkuPattern(r.data);if(c.group_id!==group.id)throw Error('SKU pada respons berbeda.')
    if(n===seq.current){setData(c);setSelected(c.pattern?.id??'');setPage(offset)}
  }catch{if(n===seq.current)setMessage('Pola belum bisa dibaca. Periksa koneksi dan pemasangan fungsi Master SKU.')}finally{if(n===seq.current)setBusy(false)}}
  useEffect(()=>{void load('',0);return()=>{seq.current++}},[group.id])
  async function save(){if(posting.current||!canEdit)return;posting.current=true;setBusy(true);setMessage('');try{
    const prior=readHeld(storageKey,group.id);if(!prior&&!data)throw Error('Baca master lebih dulu.')
    const cmd=prior??{p_group:group.id,p_pattern:selected||null,p_version:data!.revision,p_request:crypto.randomUUID()}
    sessionStorage.setItem(storageKey,JSON.stringify(cmd));setHeld(true)
    const r=await client.rpc('erp_cp8_save_sku_pattern_v1',cmd)
    if(r.error){if(r.error.code==='P0001'&&/Pola SKU berubah|Pola sudah tidak aktif/.test(r.error.message)){sessionStorage.removeItem(storageKey);setHeld(false);await load(query,page)}throw Error(r.error.message)}
    const result:unknown=r.data;if(!isObject(result)||result.request_id!==cmd.p_request||result.pattern_id!==cmd.p_pattern||result.group_id!==cmd.p_group||result.revision!==cmd.p_version+1)throw Error('Hasil penyimpanan belum bisa dipastikan.')
    sessionStorage.removeItem(storageKey);setHeld(false);setMessage(cmd.p_pattern?'Pola rencana SKU tersimpan.':'Pola rencana SKU dikosongkan.');await load(query,page)
  }catch(e){setMessage(e instanceof Error?e.message:'Hasil simpan belum diketahui.')}finally{posting.current=false;setBusy(false)}}
  const options=data?.options??[],stored=data?.pattern
  return <section className="panel"><h2>Pola rencana · {group.brand_name} {group.sku}</h2><p>{group.color_name} · {sizeRangeLabel(group.members.map(m => m.size))}</p>
    <form onSubmit={e=>{e.preventDefault();void load(query,0)}}><label>Cari pola<input maxLength={100} value={query} onChange={e=>setQuery(e.target.value)}/></label><button disabled={busy||held}>Cari</button></form>
    {data&&<><label>Pola rencana · opsional<select aria-label="Pola rencana master" value={selected} disabled={busy||held||!canEdit} onChange={e=>setSelected(e.target.value)}><option value="">Belum ditentukan</option>{stored&&!options.some(p=>p.id===stored.id)&&<option value={stored.id}>{stored.name} · {stored.revision}{stored.active?'':' · nonaktif'}</option>}{options.map(p=><option key={p.id} value={p.id}>{p.name} · {p.code} · {p.revision}</option>)}</select></label>
    {data.total>25&&<div><button disabled={busy||held||!page} onClick={()=>void load(query,Math.max(0,page-25))}>Sebelumnya</button><button disabled={busy||held||page+25>=data.total} onClick={()=>void load(query,page+25)}>Berikutnya</button></div>}</>}
    {canEdit&&<button disabled={busy||(!held&&(!data||selected===(stored?.id??'')))} onClick={()=>void save()}>{held?'Pastikan hasil penyimpanan':'Simpan pola rencana'}</button>}{message&&<p role="status">{message}</p>}
  </section>
}

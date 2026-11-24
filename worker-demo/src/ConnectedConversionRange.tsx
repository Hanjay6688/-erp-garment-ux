import {useEffect,useRef,useState} from 'react'
import {cp6WibDateTimeInput,cp6WibPhysicalTimeToIso} from './cp6BusinessTime'
import type {getUatSupabaseClient} from './lib/supabase'
import type {Json} from './types/database.preconnect'
type Client=ReturnType<typeof getUatSupabaseClient>
type Group={id:string;brand_name:string;sku:string;color_name:string}
type Member={size:string;source:string;available:number|null}
type Target={size:string;target:string;available:number|null}
type Catalog={options:Group[];total:number;offset:number;group_id:string|null;partner_id:string|null;target_group_id:string|null;target_label:string|null;location_id:string|null;locations:{id:string;location_name:string}[];members:Member[];target_members:Target[]}
const uuid=(s:unknown)=>typeof s==='string'&&/^[a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}$/i.test(s)
function obj(v:unknown):Record<string,unknown>{if(!v||typeof v!=='object'||Array.isArray(v))throw Error('Respons seri tidak lengkap.');return v as Record<string,unknown>}
function rows(v:unknown){if(!Array.isArray(v))throw Error('Daftar seri tidak lengkap.');return v.map(obj)}
function count(v:unknown){return typeof v==='number'&&Number.isSafeInteger(v)&&v>=0}
function catalog(v:unknown,g:string,l:string,offset:number,t?:string):Catalog {
 const d=obj(v)
 if(d.version!=='cp8.conversion-range.v1'||d.group_id!==(g||null)||d.location_id!==(l||null)||d.offset!==offset||!count(d.total)||
  (d.partner_id!==null&&!uuid(d.partner_id))||(d.target_group_id!==null&&!uuid(d.target_group_id))||(t&&d.target_group_id!==t)||
  !rows(d.options).every(x=>uuid(x.id)&&[x.brand_name,x.sku,x.color_name].every(s=>typeof s==='string'))||
  !rows(d.locations).every(x=>uuid(x.id)&&typeof x.location_name==='string')||
  !rows(d.members).every(m=>typeof m.size==='string'&&uuid(m.source)&&(m.available===null||count(m.available)))||
  !rows(d.target_members).every(m=>typeof m.size==='string'&&uuid(m.target)&&(m.available===null||count(m.available))))throw Error('Master atau stok seri berubah. Muat kembali.')
 return d as unknown as Catalog
}
export function rangeResult(v:unknown,action:'PREVIEW'|'POST',id:string,payload:Json) {
 const d=obj(v),p=obj(payload),res=rows(d.items),want=rows(p.items)
 if(d.version!=='cp8.conversion-range.v1'||d.action!==action||d.request_id!==id||d.group_id!==p.group_id||
   (p.target_group_id?d.target_group_id!==p.target_group_id:d.partner_id!==p.partner_id)||d.location_id!==p.location_id||
   !res.length||res.length!==want.length||!count(d.total)||d.total!==want.reduce((n,x)=>n+Number(x.qty),0)||res.some((x,i)=>x.size!==want[i].size||x.qty!==want[i].qty||
   (want[i].target_size&&want[i].target_size!==x.target_size)||!uuid(x.source)||!uuid(x.target)||(action==='POST'?!uuid(x.conversion_id):typeof x.revision!=='string'||!x.revision)))throw Error('Hasil konversi seri tidak cocok dengan permintaan.')
 return res
}
function Picker({label,client,time,value,picked,exclude,onPick}:{label:string;client:Client;time:string;value:string;picked:string;exclude?:string;onPick:(id:string,label:string)=>void}){
 const [q,setQ]=useState(''),[page,setPage]=useState(0),[matches,setMatches]=useState<Group[]>([]),[total,setTotal]=useState(0),[error,setError]=useState('')
 useEffect(()=>{
  let current=true
  const timer=setTimeout(async()=>{
   setMatches([]);setTotal(0);setError('')
   if(!time)return
   try{const r=await client.rpc('erp_cp8_get_conversion_range_v1',{p_query:{q,offset:page,physical_at:time}})
    if(!current)return
    if(r.error)throw Error('Gagal mencari SKU.')
    const d=catalog(r.data,'','',page);setMatches(d.options);setTotal(d.total)
   }catch(e){if(current)setError((e as Error).message)}
  },180)
  return ()=>{current=false;clearTimeout(timer)}
 },[q,page,client,time])
 return <div><label>Cari {label}<input value={q} onChange={e=>{setQ(e.target.value);setPage(0)}}/></label><label>{label}<select value={value} onChange={e=>onPick(e.target.value,e.target.selectedOptions[0]?.text??'')}><option value="">Pilih {label}</option>{value&&!matches.some(g=>g.id===value)&&<option value={value}>{picked}</option>}{matches.filter(g=>g.id!==exclude).map(g=><option key={g.id} value={g.id}>{g.brand_name} {g.sku} · {g.color_name}</option>)}</select></label>
 {total>25&&<div><button type="button" disabled={!page} onClick={()=>setPage(page-25)}>Sebelumnya</button><button type="button" disabled={page+25>=total} onClick={()=>setPage(page+25)}>Berikutnya</button></div>}{error&&<p role="status">{error}</p>}</div>
}
export default function ConnectedConversionRange({client,locked,canPost,post}:{client:Client;locked:boolean;canPost:boolean;post:(p:Json)=>void}) {
 const [at,setAt]=useState(()=>cp6WibDateTimeInput()),[group,setGroup]=useState(''),[sourceLabel,setSourceLabel]=useState(''),[location,setLocation]=useState('')
 const [target,setTarget]=useState(''),[targetLabel,setTargetLabel]=useState(''),[data,setData]=useState<Catalog|null>(null)
 const [reason,setReason]=useState(''),[qty,setQty]=useState<Record<string,string>>({}),[sizeMap,setSizeMap]=useState<Record<string,string>>({}),[review,setReview]=useState<Json|null>(null),[message,setMessage]=useState(''),[busy,setBusy]=useState(false)
 const seq=useRef(0),time=cp6WibPhysicalTimeToIso(at)??''
 useEffect(()=>()=>{++seq.current},[])
 function invalidate(){seq.current++;setReview(null);setBusy(false);setMessage('')}
 async function read(g:string,t:string,l:string,keep=false){
  const stamp=++seq.current;setBusy(true);setData(null);setGroup(g);setTarget(t);setLocation(l);setReview(null);if(!keep)setQty({});setMessage('')
  try{if(!g)return
   if(!time)throw Error('Isi waktu fisik yang valid.')
   const r=await client.rpc('erp_cp8_get_conversion_range_v1',{p_query:{group_id:g,target_group_id:t||null,location_id:l||null,physical_at:time}})
   if(stamp!==seq.current)return
   if(r.error)throw Error('Daftar seri belum tersedia dari server ini.')
   const d=catalog(r.data,g,l,0,t);setData(d);setTarget(d.target_group_id??'');setTargetLabel(d.target_label??'')
   if(!keep)setSizeMap(Object.fromEntries(d.members.map(m=>[m.size,d.target_members.some(b=>b.size===m.size)?m.size:''])))
  }catch(e){if(stamp===seq.current)setMessage((e as Error).message)}finally{if(stamp===seq.current)setBusy(false)}
 }
 async function preview(){
  const stamp=++seq.current;setBusy(true);setMessage('');setReview(null)
  try{
   if(!data||!location||!group||!target||!reason.trim())throw Error('Pilih dua SKU, gudang dan isi alasan.')
   const items=data.members.filter(m=>qty[m.size]?.trim()&&qty[m.size]!=='0').map(m=>{
    const n=Number(qty[m.size]),dest=data.target_members.find(x=>x.size===sizeMap[m.size])
    if(!/^\d{1,9}$/.test(qty[m.size])||!dest||m.available===null||n>m.available)throw Error('Periksa stok dan ukuran tujuan untuk ukuran '+m.size+'.')
    return {size:m.size,target_size:dest.size,qty:n}
   })
   if(!items.length)throw Error('Isi minimal satu slot ukuran.')
   const id=crypto.randomUUID(),payload={group_id:group,target_group_id:target,location_id:location,physical_at:time,reason:reason.trim(),items}
   const r=await client.rpc('erp_cp8_conversion_range_v1',{p_action:'PREVIEW',p_payload:payload,p_request:id})
   if(stamp!==seq.current)return
   if(r.error)throw Error('Stok atau identitas SKU berubah. Periksa kembali.')
   const checked=rangeResult(r.data,'PREVIEW',id,payload)
   if(checked.some(x=>!data.members.some(m=>m.size===x.size&&m.source===x.source)||!data.target_members.some(m=>m.size===x.target_size&&m.target===x.target)))throw Error('Produk fisik tidak cocok dengan master.')
   setReview({...payload,items:items.map((x,i)=>({...x,revision:String(checked[i].revision)}))})
  }catch(e){if(stamp===seq.current)setMessage((e as Error).message)}finally{if(stamp===seq.current)setBusy(false)}
 }
 return <section className="panel"><h2>Ganti merek satu seri</h2><fieldset disabled={locked||busy}><label>Waktu fisik WIB<input type="datetime-local" value={at} onChange={e=>{invalidate();setAt(e.target.value);setData(null);setGroup('');setTarget('');setLocation('');setQty({})}}/></label>
 <Picker label="SKU asal" client={client} time={time} value={group} picked={sourceLabel} onPick={(id,label)=>{setSourceLabel(label);void read(id,'','')}}/>{group&&<><Picker label="SKU tujuan" client={client} time={time} exclude={group} value={target} picked={targetLabel} onPick={(id,label)=>{setTargetLabel(label);void read(group,id,location)}}/>{data?.partner_id&&target!==data.partner_id&&<button onClick={()=>void read(group,data.partner_id!,location)}>Pakai padanan master</button>}</>}
 {data&&group&&<><label>Gudang<select value={location} onChange={e=>void read(group,target,e.target.value,true)}><option value="">Pilih gudang</option>{data.locations.map(l=><option key={l.id} value={l.id}>{l.location_name}</option>)}</select></label>
 <div className="cproc-grid">{data.members.map(m=><div key={m.source}><label>Ukuran {m.size} · tersedia {m.available??'—'}<input aria-label={'Jumlah ganti ukuran '+m.size} inputMode="numeric" placeholder="Lewati" disabled={!location||!target||!canPost} value={qty[m.size]??''} onChange={e=>{invalidate();setQty({...qty,[m.size]:e.target.value})}}/></label><label>Ukuran tujuan untuk {m.size}<select value={sizeMap[m.size]??''} onChange={e=>{invalidate();setSizeMap({...sizeMap,[m.size]:e.target.value})}}><option value="">Pilih ukuran</option>{data.target_members.map(d=><option key={d.target} value={d.size}>{d.size} · tersedia {d.available??'—'}</option>)}</select></label></div>)}</div>
 <label>Alasan perpindahan<input value={reason} onChange={e=>{invalidate();setReason(e.target.value)}}/></label><button disabled={!canPost} onClick={()=>void preview()}>Periksa konversi seri</button></>}
 {review&&<div><p>{rows(obj(review).items).map(x=>String(x.size)+' → '+String(x.target_size)+' · '+x.qty+' pcs').join(' / ')}</p><button disabled={!canPost} onClick={()=>post(review)}>Catat seluruh ukuran</button></div>}</fieldset>{message&&<p role="status">{message}</p>}</section>
}

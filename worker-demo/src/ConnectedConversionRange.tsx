import {useEffect,useRef,useState} from 'react'
import {cp6WibDateTimeInput,cp6WibPhysicalTimeToIso} from './cp6BusinessTime'
import type {getUatSupabaseClient} from './lib/supabase'
import type {Json} from './types/database.preconnect'
type Client=ReturnType<typeof getUatSupabaseClient>
type Group={id:string;brand_name:string;sku:string;color_name:string}
type Member={size:string;source:string;target:string|null;available:number|null;target_available:number|null}
type Catalog={options:Group[];total:number;offset:number;group_id:string|null;partner_id:string|null;target_label:string|null;location_id:string|null;locations:{id:string;location_name:string}[];members:Member[]}
const uuid=(s:unknown)=>typeof s==='string'&&/^[a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}$/i.test(s)
function obj(v:unknown):Record<string,unknown>{if(!v||typeof v!=='object'||Array.isArray(v))throw Error('Respons seri tidak lengkap.');return v as Record<string,unknown>}
function rows(v:unknown){if(!Array.isArray(v))throw Error('Daftar seri tidak lengkap.');return v.map(obj)}
function count(v:unknown){return typeof v==='number'&&Number.isSafeInteger(v)&&v>=0}
function catalog(v:unknown,g:string,l:string,offset:number):Catalog {
 const d=obj(v)
 if(d.version!=='cp8.conversion-range.v1'||d.group_id!==(g||null)||d.location_id!==(l||null)||d.offset!==offset||!count(d.total)||
   !rows(d.options).every(x=>uuid(x.id)&&[x.brand_name,x.sku,x.color_name].every(s=>typeof s==='string'))||
   !rows(d.locations).every(x=>uuid(x.id)&&typeof x.location_name==='string')||
   !rows(d.members).every(m=>typeof m.size==='string'&&uuid(m.source)&&(m.target===null||uuid(m.target))&&(m.available===null||count(m.available))&&(m.target_available===null||count(m.target_available))))throw Error('Master atau stok seri berubah. Muat kembali.')
 return d as unknown as Catalog
}
export function rangeResult(v:unknown,action:'PREVIEW'|'POST',id:string,payload:Json) {
 const d=obj(v),p=obj(payload),res=rows(d.items),want=rows(p.items)
 if(d.version!=='cp8.conversion-range.v1'||d.action!==action||d.request_id!==id||d.group_id!==p.group_id||d.partner_id!==p.partner_id||d.location_id!==p.location_id||
   !res.length||res.length!==want.length||!count(d.total)||d.total!==want.reduce((n,x)=>n+Number(x.qty),0)||res.some((x,i)=>x.size!==want[i].size||x.qty!==want[i].qty||
    !uuid(x.source)||!uuid(x.target)||(action==='POST'?!uuid(x.conversion_id):typeof x.revision!=='string'||!x.revision)))throw Error('Hasil konversi seri tidak cocok dengan permintaan.')
 return res
}
export default function ConnectedConversionRange({client,locked,canPost,post}:{client:Client;locked:boolean;canPost:boolean;post:(p:Json)=>void}) {
 const [q,setQ]=useState(''),[at,setAt]=useState(()=>cp6WibDateTimeInput()),[group,setGroup]=useState(''),[location,setLocation]=useState(''),[data,setData]=useState<Catalog|null>(null)
 const [reason,setReason]=useState(''),[qty,setQty]=useState<Record<string,string>>({}),[review,setReview]=useState<Json|null>(null),[message,setMessage]=useState(''),[busy,setBusy]=useState(false)
 const seq=useRef(0)
 useEffect(()=>()=>{++seq.current},[])
 function invalidate(){seq.current++;setReview(null);setBusy(false);setMessage('')}
 async function read(g:string,l:string,offset=0){
  const stamp=++seq.current;setBusy(true);setData(null);setGroup(g);setLocation(l);setReview(null);setQty({});setMessage('')
  try{
   const time=cp6WibPhysicalTimeToIso(at);if(!time)throw Error('Isi waktu fisik yang valid.')
   const r=await client.rpc('erp_cp8_get_conversion_range_v1',{p_query:{q,offset,physical_at:time,group_id:g||null,location_id:l||null}})
   if(stamp!==seq.current)return
   if(r.error)throw Error('Daftar seri belum tersedia dari server ini.')
   setData(catalog(r.data,g,l,offset))
  }catch(e){if(stamp===seq.current)setMessage((e as Error).message)}finally{if(stamp===seq.current)setBusy(false)}
 }
 async function preview(){
  const stamp=++seq.current;setBusy(true);setMessage('');setReview(null)
  try{
   if(!data||!location||!group||!data.partner_id||!reason.trim())throw Error('Pilih SKU, gudang, dan isi alasan.')
   const items=data.members.filter(m=>qty[m.size]?.trim()&&qty[m.size]!=='0').map(m=>{
    const n=Number(qty[m.size]);if(!/^\d{1,9}$/.test(qty[m.size])||!m.target||m.available===null||n>m.available)throw Error('Periksa stok ukuran '+m.size+'.')
    return {size:m.size,qty:n}
   })
   if(!items.length)throw Error('Isi minimal satu slot ukuran.')
   const id=crypto.randomUUID(),payload={group_id:group,partner_id:data.partner_id,location_id:location,physical_at:cp6WibPhysicalTimeToIso(at),reason:reason.trim(),items}
   const r=await client.rpc('erp_cp8_conversion_range_v1',{p_action:'PREVIEW',p_payload:payload,p_request:id})
   if(stamp!==seq.current)return
   if(r.error)throw Error('Stok atau padanan berubah. Muat kembali sebelum mencatat.')
   const checked=rangeResult(r.data,'PREVIEW',id,payload)
   if(checked.some(x=>!data.members.some(m=>m.size===x.size&&m.source===x.source&&m.target===x.target)))throw Error('Produk fisik tidak cocok dengan master.')
   setReview({...payload,items:items.map((x,i)=>({...x,revision:String(checked[i].revision)}))})
  }catch(e){if(stamp===seq.current)setMessage((e as Error).message)}finally{if(stamp===seq.current)setBusy(false)}
 }
 return <section className="panel"><h2>Ganti merek satu seri</h2><fieldset disabled={locked||busy}><label>Waktu fisik WIB<input type="datetime-local" value={at} onChange={e=>{invalidate();setAt(e.target.value);setData(null);setGroup('');setLocation('');setQty({})}}/></label>
  <form onSubmit={e=>{e.preventDefault();void read('','')}}><label>Cari merek, SKU atau warna<input value={q} onChange={e=>setQ(e.target.value)}/></label><button>Cari seri padanan</button></form>
  {data&&<><label>SKU asal dan warna<select value={group} onChange={e=>void read(e.target.value,'',data.offset)}><option value="">Pilih SKU asal</option>{data.options.map(g=><option key={g.id} value={g.id}>{g.brand_name} {g.sku} · {g.color_name}</option>)}</select></label>
  {data.total>25&&<div><button disabled={!data.offset} onClick={()=>void read('','',Math.max(0,data.offset-25))}>SKU sebelumnya</button> {data.total} SKU <button disabled={data.offset+25>=data.total} onClick={()=>void read('','',data.offset+25)}>SKU berikutnya</button></div>}
  {group&&<><p>Tujuan padanan · {data.target_label}</p><label>Gudang<select value={location} onChange={e=>void read(group,e.target.value,data.offset)}><option value="">Pilih gudang</option>{data.locations.map(l=><option key={l.id} value={l.id}>{l.location_name}</option>)}</select></label>
  <div className="cproc-grid">{data.members.map(m=><label key={m.source}>Ukuran {m.size} · asal {m.available??'—'} · tujuan {m.target_available??'—'}<input aria-label={'Jumlah ganti ukuran '+m.size} inputMode="numeric" placeholder="Lewati" disabled={!location||!m.target||!canPost} value={qty[m.size]??''} onChange={e=>{invalidate();setQty({...qty,[m.size]:e.target.value})}}/></label>)}</div>
  <label>Alasan perpindahan<input value={reason} onChange={e=>{invalidate();setReason(e.target.value)}}/></label><button disabled={!canPost} onClick={()=>void preview()}>Periksa konversi seri</button></>}
  {review&&<div><p>{rows(obj(review).items).map(x=>x.size+' = '+x.qty+' pcs').join(' · ')}</p><button disabled={!canPost} onClick={()=>post(review)}>Catat seluruh ukuran</button></div>}</>}
 </fieldset>{message&&<p role="status">{message}</p>}</section>
}

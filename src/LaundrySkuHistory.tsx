import { useEffect, useMemo, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { skuObject } from './skuHpp'
import { rupiah } from './laundryBd'

export type LaundryHistoryItem = { sku_id: string; sku: string; target_size_ids: string[]; delivery_id: string; number: string; at: string;
 process_id: string; mode: string; reference_kind: 'ACTUAL' | 'ESTIMATE' | 'UNKNOWN'; reference_total: string | null; reference_qty: number;
 charges: { kind: string; ref_id: string | null; label: string; all_source_pieces: boolean }[] }

function parseHistory(value: unknown, vendor: string, wave: string): LaundryHistoryItem[] {
 const w=skuObject(value)
 if(w.vendor_id!==vendor || w.wave_id!==wave || !Array.isArray(w.items))throw new Error('Riwayat cucian tidak cocok dengan batch ini.')
 for(const raw of w.items){const r=skuObject(raw)
  if(!['sku_id','sku','delivery_id','number','at','process_id','mode'].every(k=>typeof r[k]==='string')
   ||!Array.isArray(r.target_size_ids)||!r.target_size_ids.every(x=>typeof x==='string')||!Array.isArray(r.charges)
   ||!['ACTUAL','ESTIMATE','UNKNOWN'].includes(String(r.reference_kind))||!Number.isSafeInteger(r.reference_qty)||Number(r.reference_qty)<=0
   ||!(r.reference_total===null||typeof r.reference_total==='string'&&/^\d+\.\d{2}$/.test(r.reference_total)))throw new Error('Rincian riwayat cucian tidak lengkap.')
  for(const rawCharge of r.charges){const c=skuObject(rawCharge)
   if(typeof c.kind!=='string'||typeof c.label!=='string'||!(c.ref_id===null||typeof c.ref_id==='string')||typeof c.all_source_pieces!=='boolean')throw new Error('Pilihan jasa pada riwayat tidak lengkap.')
  }
 }
 return w.items as LaundryHistoryItem[]
}

export default function LaundrySkuHistory({vendor,wave,at,locked,onSelect}:{vendor:string;wave:string;at:string|null;locked:boolean;onSelect:(item:LaundryHistoryItem)=>void}){
 const {runtime}=useAuth();if(!isConnectedRuntime(runtime))throw new Error('ERP belum tersambung.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime])
 const [items,setItems]=useState<LaundryHistoryItem[]|null>(null),[error,setError]=useState('')
 useEffect(()=>{
  let active=true;setItems(null);setError('')
  void (async()=>{try{
   const result=await client.rpc('erp_get_laundry_history_v1',{p_filters:{vendor_id:vendor,wave_id:wave,...(at?{at}:{})}})
   if(!active)return;if(result.error)throw result.error;setItems(parseHistory(result.data,vendor,wave))
  }catch(e){if(active)setError(normalizeClientError(e).message)}})()
  return()=>{active=false}
 },[client,vendor,wave,at])
 return <section aria-label="Riwayat cucian SKU"><h3>Riwayat cucian SKU</h3>
  <p>Riwayat membantu memilih jasa. Tarif kiriman ini tetap diambil dari master vendor pada tanggal kirim.</p>
  {error?<p role="status">Riwayat belum dapat dibaca: {error}</p>:items===null?<p role="status">Memuat riwayat cucian…</p>:items.length===0?<p>Belum ada riwayat untuk referensi SKU batch ini. Rincian boleh dipilih sendiri atau dikosongkan.</p>:items.map(item=>{
   const selectable=item.charges.length>0&&item.charges.every(c=>['COMPONENT','PACKAGE','EXTRA','RATE','SCOPED_RATE','PROCESS_REFERENCE'].includes(c.kind)&&c.all_source_pieces)
   return <article key={`${item.delivery_id}:${item.sku_id}`}><strong>{item.sku} · {item.number}</strong>
    <p>{item.charges.map(c=>c.label).join(' + ')} · {new Date(item.at).toLocaleDateString('id-ID')}</p>
    <p>{item.reference_kind==='ACTUAL'?'Biaya dari kontra bon':'Estimasi biaya'} seluruh kiriman sebelumnya ({item.reference_qty} PCS): {item.reference_total===null?'belum diketahui / nominal tidak ditampilkan':rupiah(item.reference_total)}.</p>
    <button type="button" disabled={locked||!selectable} onClick={()=>onSelect(item)}>Gunakan pilihan jasa {item.number} · {item.sku}</button>
    {!selectable&&<p>Cakupan jasa sebelumnya parsial atau berbeda; cocokkan komponen dan penerimanya secara manual.</p>}
   </article>
  })}
 </section>
}

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useAuth } from './auth/AuthProvider'
import { isConnectedRuntime } from './config/runtime'
import { getUatSupabaseClient } from './lib/supabase'
import { normalizeClientError } from './lib/clientError'
import { useProductionMutation, type ProductionMutationHandlers } from './useProductionMutation'
import ProductionRecoveryNotice from './ProductionRecoveryNotice'
import { skuObject, skuMoney } from './skuHpp'
import { creditAmount, creditCents, parseSupplierCredit, type SupplierCredit, type SupplierCreditWorkspace } from './supplierCredit'
import './initial-import.css'
import './supplier-credit.css'

export default function ConnectedSupplierCreditPage({ onLaundry }: { onLaundry: () => void }) {
 const { runtime, identity }=useAuth()
 if(!isConnectedRuntime(runtime)||identity.status!=='AUTHORIZED'||!identity.permissions.includes('finance.ap.view'))return <section className="panel" role="alert">Hak lihat utang supplier diperlukan.</section>
 return <Workspace key={`${runtime.projectRef}:${identity.profile.id}:${identity.profile.rowVersion}:${identity.profile.roleRowVersion}:${identity.permissions.join('|')}`} onLaundry={onLaundry}/>
}
function Workspace({onLaundry}:{onLaundry:()=>void}){
 const {runtime}=useAuth();if(!isConnectedRuntime(runtime))throw new Error('ERP belum tersambung.')
 const client=useMemo(()=>getUatSupabaseClient(runtime),[runtime])
 const recovery=useProductionMutation('SUPPLIER_CREDIT'),{beginRead,finishRead,isReadCurrent,run,reconcile}=recovery
 const [data,setData]=useState<SupplierCreditWorkspace|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const [draft,setDraft]=useState<SupplierCredit|null>(null),[amounts,setAmounts]=useState<Record<string,string>>({}),[reason,setReason]=useState(''),[confirmed,setConfirmed]=useState(false)
 const filters=useRef({supplier_id:'',page:1}),sequence=useRef(0)
 const load=useCallback(async()=>{
  const seq=++sequence.current,ticket=beginRead(),f={...filters.current};setBusy(true);setError('');setData(null);setDraft(null);setConfirmed(false)
  try{const r=await client.rpc('erp_get_supplier_credit_v1',{p_filters:{page:f.page,...(f.supplier_id?{supplier_id:f.supplier_id}:{})}})
   if(seq!==sequence.current||!isReadCurrent(ticket))return false;if(r.error)throw r.error
   const w=parseSupplierCredit(r.data);if(w.supplier_id!==(f.supplier_id||null)||w.page!==f.page)throw new Error('Supplier atau halaman tidak cocok.')
   setData(w);return finishRead(ticket)
  }catch(e){if(seq===sequence.current&&isReadCurrent(ticket))setError(normalizeClientError(e).message);return false}
  finally{if(seq===sequence.current)setBusy(false)}
 },[client,beginRead,finishRead,isReadCurrent])
 useEffect(()=>{void load();return()=>{++sequence.current}},[load])
 const handlers:ProductionMutationHandlers={send:e=>client.rpc('erp_save_supplier_credit_v1',{p_payload:e.payload,p_client_request_id:e.id}),
  validate:(value,e)=>{const r=skuObject(value),p=skuObject(e.payload);if(r.request_id!==e.id||r.return_id!==p.return_id||r.source_purchase_id!==p.source_purchase_id||typeof r.version!=='string')throw new Error('Respons alokasi kredit tidak cocok.')},
  retire:()=>{setDraft(null);setAmounts({});setReason('');setConfirmed(false)},reload:load}
 const locked=busy||recovery.writerLocked
 const allocations=Object.entries(amounts).filter(([,v])=>v.trim()&&creditCents(v)!==0n)
 const validAmounts=allocations.every(([,v])=>creditCents(v)!==null)
 const moved=allocations.reduce((n,[,v])=>n+(creditCents(v)??0n),0n),original=draft?(creditCents(draft.credit)??0n)-moved:0n
 const previousMoved=draft?.allocations.reduce((n,a)=>n+creditCents(a.amount)!,0n)??0n
 const projected=data?.purchases.map(p=>({number:p.number,remaining:creditCents(p.remaining)!+(p.id===draft?.source_purchase_id
  ? moved-previousMoved : (creditCents(draft?.allocations.find(a=>a.purchase_id===p.id)?.amount??'0')??0n)-(creditCents(amounts[p.id]??'0')??0n))}))??[]
 const balancesValid=projected.every(p=>p.remaining>=0n)
 const edit=(c:SupplierCredit)=>{setDraft(c);setAmounts(Object.fromEntries(c.allocations.map(a=>[a.purchase_id,a.amount])));setReason('');setConfirmed(false)}
 return <section className="initial-import supplier-credit">
  <header className="panel"><h1>Utang & kredit retur supplier</h1><p>Kredit retur kain dan aksesori tetap memotong pembelian asal. Alihkan seluruhnya atau sebagian ke pembelian lain dari supplier yang sama.</p><button type="button" onClick={onLaundry}>Buka tagihan & kredit klaim laundry</button></header>
  <ProductionRecoveryNotice recovery={recovery} onReconcile={()=>reconcile(handlers)} className="initial-import-message"/>
  {error&&<p role="alert">{error}</p>}
  <section className="panel initial-import-toolbar"><label>Supplier kredit<select aria-label="Supplier kredit" disabled={locked} value={filters.current.supplier_id} onChange={e=>{filters.current={supplier_id:e.target.value,page:1};void load()}}><option value="">Pilih supplier…</option>{data?.suppliers.map(s=><option key={s.id} value={s.id}>{s.code} · {s.name}</option>)}</select></label><button disabled={busy||recovery.busy} onClick={()=>void load()}>Muat ulang kredit supplier</button></section>
  {data&&<><section className="panel"><h2>Utang pembelian</h2><div className="supplier-credit-table"><table><thead><tr><th>Pembelian</th><th>Utang setelah kredit</th><th>Sudah dibayar</th><th>Sisa utang</th></tr></thead><tbody>{data.purchases.map(p=><tr key={p.id}><td>{p.number}</td><td>{skuMoney(p.final_ap)}</td><td>{skuMoney(p.paid)}</td><td>{skuMoney(p.remaining)}</td></tr>)}</tbody></table></div></section>
   <section className="panel"><h2>Kredit retur</h2>{data.credits.map(c=><article key={`${c.return_id}:${c.source_purchase_id}`}><h3>{c.return_number} · {c.purchase_number}</h3><p>Kredit {skuMoney(c.credit)} · bagian pembelian asal {skuMoney(c.original_purchase_credit)}.</p><button aria-label={`Atur alokasi ${c.return_number}`} disabled={locked||!data.can_manage||!filters.current.supplier_id} onClick={()=>edit(c)}>Atur alokasi</button>
    {c.events.length>0&&<details><summary>Riwayat alokasi</summary>{c.events.map(e=><p key={e.id}>{e.date} · {data.purchases.find(p=>p.id===e.purchase_id)?.number??e.purchase_id} · {e.reversal_of?'Pembatalan':'Pengalihan'} {skuMoney(e.amount.replace('-',''))} · {e.reason}</p>)}</details>}</article>)}{data.credits.length===0&&<p>Belum ada kredit retur yang bisa dialokasikan.</p>}
    <button disabled={locked||data.page<=1} onClick={()=>{filters.current.page--;void load()}}>Sebelumnya</button> Halaman {data.page} <button disabled={locked||data.page*50>=data.total} onClick={()=>{filters.current.page++;void load()}}>Berikutnya</button></section>
  </>}
  {draft&&data&&<form className="panel" onSubmit={e=>{e.preventDefault();if(locked||!confirmed||!validAmounts||!balancesValid||original<0n||reason.trim().length<4)return;void run('ALLOCATE',{return_id:draft.return_id,source_purchase_id:draft.source_purchase_id,expected_version:draft.version,reason:reason.trim(),allocations:allocations.map(([purchase_id,v])=>({purchase_id,amount:creditAmount(creditCents(v)!)}))},null,handlers)}}>
   <h2>Alokasi {draft.return_number}</h2><p>Kosongkan semua tujuan untuk mengembalikan kredit ke pembelian asal. Pengalihan dicatat pada hari ini.</p><fieldset disabled={locked}>
    {data.purchases.filter(p=>p.id!==draft.source_purchase_id).map(p=><label key={p.id}>{p.number} · sisa {skuMoney(p.remaining)}<input aria-label={`Kredit untuk ${p.number}`} inputMode="decimal" value={amounts[p.id]??''} onChange={e=>{setAmounts(x=>({...x,[p.id]:e.target.value}));setConfirmed(false)}}/></label>)}
    <p>Bagian kredit untuk {draft.purchase_number}: {original<0n?'Melebihi kredit retur':skuMoney(creditAmount(original))}.</p>
    <h3>Sisa utang setelah alokasi</h3>{projected.map(p=><p key={p.number}>{p.number}: {p.remaining<0n?'Alokasi melebihi sisa utang sesudah pembayaran':skuMoney(creditAmount(p.remaining))}.</p>)}
    <label>Alasan pengalihan<input aria-label="Alasan pengalihan kredit" maxLength={1000} value={reason} onChange={e=>{setReason(e.target.value);setConfirmed(false)}}/></label>
    <label className="supplier-credit-confirm"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>Saya sudah memeriksa pembelian asal, tujuan, dan nominal kredit.</label>
    <button disabled={!confirmed||!validAmounts||!balancesValid||original<0n||reason.trim().length<4}>Simpan alokasi kredit</button>
   </fieldset>
  </form>}
 </section>
}

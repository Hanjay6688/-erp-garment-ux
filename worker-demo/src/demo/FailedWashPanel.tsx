import { useState, type FormEvent } from 'react'
import { RotateCcw } from 'lucide-react'
import { readRupiahInput } from '../moneyInput'
import { amountText } from './accessoryPricing'
import { claimedOutsidePieces } from './laundryCredits'
import { laundryOutstanding, laundryPhysicalTime, validLaundryTime, type FailedWash, type LaundryDelivery } from './laundryModel'
import { ReasonDialog } from './planner/ReasonDialog'
import { dayOk, lastWarehouseDay } from './warehouseDay'

type Entry = {custody:FailedWash['custody'];qty:string;at:string;pricing:'PENDING'|'ZERO'|'ACTUAL';rate:string;reason:string}

export function FailedWashPanel({delivery,onRecord,onPrice}:{delivery:LaundryDelivery;onRecord:(entry:FailedWash)=>void;onPrice:(id:string,rate:number,day:string)=>void}) {
  const [form,setForm]=useState<Entry|null>(null)
  const [price,setPrice]=useState<{id:string;raw:string;day:string}|null>(null)
  const [error,setError]=useState('')
  const history=delivery.failedWashes??[]
  const remaining=laundryOutstanding(delivery)
  const sentAt=laundryPhysicalTime(delivery.sentAt)
  const earliest=[sentAt,...history.map(row=>row.at),...(delivery.returns??[]).map(row=>row.at)].sort().at(-1)??sentAt
  if(!remaining&&!history.length)return null
  function save(event:FormEvent) {
    event.preventDefault()
    if(!form)return
    const qty=form.custody==='RETURN'?remaining:Number(form.qty)
    const rate=form.pricing==='PENDING'?null:form.pricing==='ZERO'?0:readRupiahInput(form.rate)
    if(!validLaundryTime(form.at)||form.at<earliest||!Number.isSafeInteger(qty)||qty<=0||qty>remaining||form.reason.trim().length<4
      ||rate!==null&&(!Number.isSafeInteger(Math.round(rate*qty*100))||rate<0)){
      setError('Periksa jumlah, tarif, waktu fisik, dan alasan cuci gagal.');return
    }
    if(form.custody==='RETURN'&&claimedOutsidePieces(delivery)>0){setError('Selesaikan pembalikan klaim Stuck atau Hilang sebelum memindahkan fisik ke Jahit.');return}
    onRecord({id:crypto.randomUUID(),custody:form.custody,qty,at:form.at,reason:form.reason.trim(),rate})
    setForm(null)
  }
  return <section className="laundry-bill-card" aria-label="Penanganan cuci gagal">
    <div className="demo-operation-heading"><i><RotateCcw/></i><div><h3>Cuci gagal & cuci ulang</h3><p>Catat posisi barang dan biaya percobaan.</p></div></div>
    {remaining>0&&<button type="button" className="soft-btn" onClick={()=>{
      setError('');setForm({custody:'STAY',qty:String(remaining),at:[earliest,lastWarehouseDay()+'T12:00'].sort().at(-1)!,pricing:'PENDING',rate:'',reason:''})
    }}>Catat cuci gagal</button>}
    {history.length>0&&<details className="demo-operation-history" open><summary>Riwayat percobaan ({history.length})</summary>
      {history.map(row=><article key={row.id}><strong>{row.qty} pcs · {row.custody==='STAY'?'Tetap di laundry':'Kembali belum diproses'}</strong>
        <small>{row.at.replace('T',' · ')} WIB · {row.reason}</small>
        <small>{row.rate===null?'Harga aktual menunggu vendor':`${amountText(row.rate)} / pcs · ${row.rate===0?'Cuci ulang gratis':amountText(row.rate*row.qty)}`}{row.pricedOn?' · Dilengkapi '+row.pricedOn:''}</small>
        {row.rate===null&&<div><button className="soft-btn" type="button" onClick={()=>{setError('');setPrice({id:row.id,raw:'',day:lastWarehouseDay()})}}>Isi tarif aktual</button></div>}
      </article>)}
    </details>}
    {form&&<ReasonDialog title="Catat cuci gagal" closeLabel="Kembali" onClose={()=>setForm(null)} className="demo-operation-dialog">
      <form className="demo-operation-form" onSubmit={save}>
        <p>{delivery.vendor} · <strong>{remaining} pcs</strong> masih di surat kirim {delivery.id}</p>
        <label>Posisi fisik<select value={form.custody} onChange={event=>setForm({...form,custody:event.target.value as Entry['custody']})}>
          <option value="STAY">Masih di laundry, bisa cuci ulang</option><option value="RETURN">Seluruh sisa kembali ke Jahit tanpa diproses</option></select></label>
        <div className="demo-operation-fields"><label>Jumlah cuci gagal (pcs)<input required inputMode="numeric" disabled={form.custody==='RETURN'} value={form.custody==='RETURN'?remaining:form.qty} onChange={event=>setForm({...form,qty:event.target.value.replace(/\D/g,'').slice(0,9)})}/></label>
          <label>Waktu fisik (WIB)<input required type="datetime-local" min={earliest} max={lastWarehouseDay()+'T23:59'} value={form.at} onChange={event=>setForm({...form,at:event.target.value})}/></label></div>
        <label>Tarif percobaan<select value={form.pricing} onChange={event=>setForm({...form,pricing:event.target.value as Entry['pricing']})}>
          <option value="PENDING">Harga belum diketahui</option><option value="ZERO">Gratis sesuai kesepakatan (Rp0)</option><option value="ACTUAL">Isi harga aktual</option></select></label>
        {form.pricing==='ACTUAL'&&<label>Harga aktual (Rp/pcs)<input required inputMode="decimal" value={form.rate} onChange={event=>setForm({...form,rate:event.target.value})}/></label>}
        <label>Alasan dan kesepakatan<textarea required minLength={4} maxLength={400} value={form.reason} onChange={event=>setForm({...form,reason:event.target.value})}/></label>
        {error&&<p role="alert">{error}</p>}
        <footer><button className="primary-btn">Simpan cuci gagal</button></footer>
      </form>
    </ReasonDialog>}
    {price&&<ReasonDialog title="Isi tarif aktual cuci gagal" closeLabel="Kembali" onClose={()=>setPrice(null)} className="demo-operation-dialog">
      <form className="demo-operation-form" onSubmit={event=>{
        event.preventDefault()
        const row=history.find(item=>item.id===price.id)
        const rate=readRupiahInput(price.raw)
        if(!row||row.rate!==null||!Number.isSafeInteger(Math.round(rate*row.qty*100))||rate<0||!dayOk(price.day)||price.day<row.at.slice(0,10)){
          setError('Periksa tarif per pcs dan tanggal aktual.');return
        }
        onPrice(price.id,rate,price.day);setPrice(null)
      }}><div className="demo-operation-fields">
        <label>Tarif aktual (Rp/pcs)<input required inputMode="decimal" value={price.raw} onChange={event=>setPrice({...price,raw:event.target.value})}/></label>
        <label>Tanggal tarif<input required type="date" max={lastWarehouseDay()} value={price.day} onChange={event=>setPrice({...price,day:event.target.value})}/></label>
      </div><p>Masukkan 0 jika vendor menyepakati cuci ulang gratis.</p>{error&&<p role="alert">{error}</p>}<footer><button className="primary-btn">Simpan tarif aktual</button></footer></form>
    </ReasonDialog>}
  </section>
}

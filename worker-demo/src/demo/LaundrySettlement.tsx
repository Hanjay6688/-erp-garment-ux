import { useState, type FormEvent } from 'react'
import { Banknote, FilePenLine, WalletCards } from 'lucide-react'
import { cashAccounts } from '../financeData'
import { readRupiahInput } from '../moneyInput'
import { amountText } from './accessoryPricing'
import { billRemaining, vendorBalance, vendorReceivable } from './laundryCredits'
import { settleLaundry, type Settlement } from './laundrySettlement'
import type { LaundryDelivery, LaundryFinalBill } from './laundryModel'
import { ReasonDialog } from './planner/ReasonDialog'
import { lastWarehouseDay } from './warehouseDay'

type Form = {kind:'PAY'|'CORRECT'|'USE';id:string;amount:string;day:string;note:string;account:string;targetIndex:string}
const rupiah = (cents:number) => amountText(cents/100)
const title = {PAY:'Catat pembayaran kontrabon',CORRECT:'Koreksi tarif kontrabon',USE:'Selesaikan piutang vendor'}

export function LaundrySettlement({delivery,bill,deliveries,update}:{delivery:LaundryDelivery;bill:LaundryFinalBill;deliveries:LaundryDelivery[];update:(change:(rows:LaundryDelivery[])=>LaundryDelivery[])=>void}) {
  const [form,setForm]=useState<Form|null>(null)
  const [error,setError]=useState('')
  const balance=vendorBalance(deliveries,delivery,bill)
  const remaining=billRemaining(deliveries,delivery,bill)
  const targets=deliveries.filter(row=>row.vendor===delivery.vendor).flatMap(row=>(row.finalBills??[])
    .filter(item=>item!==bill&&billRemaining(deliveries,row,item)>0).map(item=>({delivery:row.id,bill:item.number,remaining:billRemaining(deliveries,row,item)})))
  const target=form?.targetIndex?targets[Number(form.targetIndex)-1]:undefined
  const value=form?readRupiahInput(form.amount):NaN
  const cents=Math.round(value*100)
  const correctedGross=Math.round(value*bill.qty*100)
  const correctionExcess=vendorReceivable(deliveries,delivery,{...bill,rate:value})
  const open=(kind:Form['kind'])=>{setError('');setForm({kind,id:crypto.randomUUID(),amount:kind==='PAY'?String(remaining/100):'',day:lastWarehouseDay(),note:'',account:'',targetIndex:''})}
  const patch=(values:Partial<Form>)=>{setForm(current=>current?{...current,...values}:null);setError('')}
  function save(event:FormEvent) {
    event.preventDefault()
    if(!form)return
    const {id,day,note,account,kind}=form
    const action:Settlement=kind==='PAY'?{kind,record:{id,day,cents,account,reference:note.trim()}}
      :kind==='CORRECT'?{kind,record:{id,day,rate:value,previousRate:bill.rate,reason:note.trim()}}
        :{kind,record:{id,day,cents,reason:note.trim(),target:target?{delivery:target.delivery,bill:target.bill}:undefined,account:target?undefined:account}}
    try {
      const next=settleLaundry(deliveries,delivery.id,bill.number,action)
      update(current=>current===deliveries?next:current)
      setForm(null)
    } catch(failure) {setError((failure as Error).message)}
  }

  return <>
    <div className="demo-operation-actions">
      {remaining>0&&<button type="button" className="soft-btn" onClick={()=>open('PAY')}><Banknote size={16}/> Bayar kontrabon</button>}
      <button type="button" className="soft-btn" onClick={()=>open('CORRECT')}><FilePenLine size={16}/> Koreksi tarif</button>
    </div>
    {balance>0&&<div className="demo-vendor-credit"><WalletCards size={19}/><div><h4>Piutang vendor</h4><strong>{rupiah(balance)}</strong></div>
      <button type="button" className="soft-btn" onClick={()=>open('USE')}>Selesaikan piutang</button></div>}
    {((bill.payments?.length??0)+(bill.corrections?.length??0)+(bill.vendorUses?.length??0)>0)&&<details className="demo-operation-history"><summary>Riwayat pembayaran dan koreksi</summary>
      {bill.payments?.map(row=><article key={row.id}><strong>{rupiah(row.cents)} · Pembayaran</strong><small>{row.day} · {row.account} · {row.reference}</small></article>)}
      {bill.corrections?.map(row=><article key={row.id}><strong>{amountText(row.previousRate)} → {amountText(row.rate)} / pcs</strong><small>{row.day} · Koreksi {bill.number} · {row.reason}</small></article>)}
      {bill.vendorUses?.map(row=><article key={row.id}><strong>{rupiah(row.cents)} · {row.target?'Potong kontrabon '+row.target.bill:'Uang kembali ke '+row.account}</strong><small>{row.day} · {row.reason}</small></article>)}
    </details>}
    {form&&<ReasonDialog title={title[form.kind]} closeLabel="Kembali" onClose={()=>setForm(null)} className="demo-operation-dialog">
      <form className="demo-operation-form" onSubmit={save}>
        <p>{delivery.vendor} · {bill.number}</p>
        {form.kind==='USE'&&<label>Penyelesaian<select value={form.targetIndex} onChange={event=>patch({targetIndex:event.target.value,amount:''})}>
          <option value="">Terima uang dari vendor</option>{targets.map((row,index)=><option value={String(index+1)} key={row.delivery+row.bill}>Potong {row.bill} · {rupiah(row.remaining)}</option>)}</select></label>}
        <div className="demo-operation-fields">
          <label>{form.kind==='CORRECT'?'Tarif aktual pengganti (Rp/pcs)':'Nominal (Rp)'}<input inputMode="decimal" required value={form.amount} onChange={event=>patch({amount:event.target.value})}/>
            <small>{form.kind==='CORRECT'?`Tarif asal ${amountText(bill.rate)} / pcs`:`Batas ${rupiah(form.kind==='PAY'?remaining:Math.min(balance,target?.remaining??balance))}`}</small></label>
          <label>Tanggal<input type="date" required min={bill.day} max={lastWarehouseDay()} value={form.day} onChange={event=>patch({day:event.target.value})}/></label>
        </div>
        {(form.kind==='PAY'||form.kind==='USE'&&!target)&&<label>{form.kind==='PAY'?'Rekening keluar':'Rekening penerima'}<select required value={form.account} onChange={event=>patch({account:event.target.value})}>
          <option value="">Pilih rekening</option>{cashAccounts.map(row=><option key={row.code}>{row.name}</option>)}</select></label>}
        <label>{form.kind==='CORRECT'?'Alasan koreksi':'Bukti atau referensi'}<textarea required minLength={4} maxLength={400} value={form.note} onChange={event=>patch({note:event.target.value})}/></label>
        {form.kind==='CORRECT'&&Number.isFinite(correctedGross)&&<div className="demo-operation-facts">
          <article><span>Tagihan terkoreksi</span><strong>{rupiah(correctedGross)}</strong></article>
          <article><span>Kelebihan bayar</span><strong>{rupiah(correctionExcess)}</strong></article>
        </div>}
        {error&&<p role="alert">{error}</p>}
        <footer><button className="primary-btn">Simpan {form.kind==='CORRECT'?'koreksi':form.kind==='PAY'?'pembayaran':'penyelesaian'}</button></footer>
      </form>
    </ReasonDialog>}
  </>
}

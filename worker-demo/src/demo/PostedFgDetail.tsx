import {useState} from 'react'
import {allPayrollSources,choosePayrollSource,editablePayroll,payForSource,readPayDrafts,savePayDrafts} from './payrollSources'
import {amountText} from './accessoryPricing'
import RecordTable from '../RecordTable'
export default function PostedFgDetail({number}:{number:string}){
  const source=allPayrollSources().find(s=>s.kind==='FG'&&s.doc.number===number),[msg,setMsg]=useState('')
  if(!source||source.kind!=='FG')return <section className="panel gar-panel"><h1>Nota FG tidak ditemukan</h1><a href="/keuangan/payroll-kasbon/">Kembali ke Payroll &amp; Kasbon</a></section>
  const d=source.doc,pay=readPayDrafts().find(p=>p.status!=='REVERSED'&&p.fgNotes.some(n=>n.number===number))
  return <><section className="hero-copy compact"><div className="eyebrow">Produksi · Susun Nota FG</div><h1>{number}</h1><p>{source.mandor} · {d.date} · Posted</p></section><section className="panel gar-panel"><h2>{d.sku}</h2><p>{d.source}</p><p>Good {d.good} pcs · BS {d.bs} pcs · Stuck {d.stuck} pcs</p><div className="ic-series-balance"><span>Upah dan komponen<strong>{amountText(d.labor)}</strong></span><span>Reimburse<strong>{amountText(d.reimbursement)}</strong></span><span>Total nota<strong>{amountText(d.labor+d.reimbursement)}</strong></span></div>
  {!!d.regularCards?.length&&<><h3>FG reguler</h3><RecordTable><thead><tr><th>Dokumen asal</th><th>Selesai dijahit</th><th>Good / BS / stuck</th><th>Nilai</th></tr></thead><tbody>{d.regularCards.map(c=><tr key={c.id}><td>{c.source} · {c.sku}</td><td>{c.sewnQty}</td><td>{c.good} / {c.bs} / {c.hold}</td><td>{amountText(c.subtotal)}</td></tr>)}</tbody></RecordTable></>}
  {!!d.repairCards?.length&&<><h3>Bikin Bagus / susulan</h3>{d.repairCards.map(c=><p key={c.id}>{c.source} · {c.sku} · {c.qty} pcs × {amountText(c.unitRate)} = {amountText(c.subtotal)}</p>)}</>}
  {d.note&&<p>Catatan · {d.note}</p>}<p>{pay?'Terpilih di '+pay.number+' · '+pay.status:'Belum dipilih untuk pembayaran'}</p>
  <div className="owner-payroll-actions">{pay&&editablePayroll(pay)&&<button className="soft-btn" onClick={()=>{savePayDrafts(choosePayrollSource(readPayDrafts(),pay.number,number,false));setMsg('Nota dilepas untuk periode berikutnya.')}}>Lepas dari pembayaran</button>}
  <button className="primary-btn" onClick={()=>{try{payForSource(number,sessionStorage.getItem('erp.owner.payroll.focus'),true);location.assign('/keuangan/payroll-kasbon/')}catch(e){setMsg((e as Error).message)}}}>{pay?'Buka payroll terkait':'Masukkan ke payroll'}</button><a className="gar-button" href="/keuangan/payroll-kasbon/">Kembali ke Payroll &amp; Kasbon</a></div>{msg&&<p role="status">{msg}</p>}</section></>
}

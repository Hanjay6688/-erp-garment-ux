import {fgQuantity} from '../fgQuantity'
import {useState} from 'react'
import {allPayrollSources,choosePayrollSource,editablePayroll,payForSource,readPayDrafts,savePayDrafts} from './payrollSources'
import {amountText} from './accessoryPricing'
import RecordTable from '../RecordTable'
export default function PostedFgDetail({number}:{number:string}){
  const source=allPayrollSources().find(s=>s.kind==='FG'&&s.doc.number===number),[msg,setMsg]=useState('')
  if(!source||source.kind!=='FG')return <section className="panel gar-panel"><h1>Nota FG tidak ditemukan</h1><a href="/keuangan/payroll-kasbon/">Kembali ke Payroll &amp; Kasbon</a></section>
  const d=source.doc,pay=readPayDrafts().find(p=>p.status!=='REVERSED'&&p.fgNotes.some(n=>n.number===number))
  return <><section className="hero-copy compact"><div className="eyebrow">Produksi · Susun Nota FG</div><h1>{number}</h1><p>{source.mandor} · {d.date} · Posted</p></section><section className="panel gar-panel"><h2>{d.sku}</h2><p>{d.source}</p><p>Good {fgQuantity(d.good)} · BS {fgQuantity(d.bs)} · Stuck {d.stuck} pcs</p><div className="ic-series-balance"><span>Upah dan komponen<strong>{amountText(d.labor)}</strong></span><span>Reimburse<strong>{amountText(d.reimbursement)}</strong></span><span>Total nota<strong>{amountText(d.labor+d.reimbursement)}</strong></span></div>
  {!!d.regularCards?.length&&<><h3>FG reguler</h3><RecordTable><thead><tr><th>Dokumen asal</th><th>Selesai dijahit</th><th>Good / BS / stuck</th><th>Nilai</th></tr></thead><tbody>{d.regularCards.map(c=><tr key={c.id}><td>{c.source} · {c.sku}</td><td>{fgQuantity(c.sewnQty)}</td><td>{c.good} / {c.bs} / {c.hold}</td><td>{amountText(c.subtotal)}</td></tr>)}</tbody></RecordTable></>}
  {d.regularCards?.map(c=><details className="panel owner-source-drafts" key={c.id}><summary>Ukuran &amp; tarif · {c.sku}</summary>
    <p>Jahit {amountText(c.sewingRate)} + komisi {amountText(c.commissionRate)} + reimburse {amountText(c.bomRate)} per pcs.</p>
    <p>{c.sewnQty} pcs × {amountText(c.sewingRate+c.commissionRate+c.bomRate)} − BS {amountText(c.bsDeduction)} − Stuck {amountText(c.stuckDeduction)} = {amountText(c.subtotal)}</p>
    {!!c.sizeRows?.length&&<RecordTable><thead><tr><th>Ukuran</th><th>Dijahit</th><th>Good</th><th>BS</th><th>Stuck</th><th>Cuci ulang</th></tr></thead><tbody>{c.sizeRows.map(r=><tr key={r.size}><th>{r.size}</th><td>{r.sewn}</td><td>{fgQuantity(r.good)}</td><td>{r.bs}</td><td>{r.hold}</td><td>{r.rewash}</td></tr>)}</tbody></RecordTable>}</details>)}
  {!!d.repairCards?.length&&<><h3>Bikin Bagus / susulan</h3>{d.repairCards.map(c=><div key={c.id}><p>{c.source} · {c.sku} · {c.qty} pcs × {amountText(c.unitRate)} = {amountText(c.subtotal)} · {fgQuantity(c.qty)}</p><details className="panel owner-source-drafts"><summary>Ukuran &amp; komponen · {c.sku}</summary>{c.sizeRows?.map(r=><p key={r.size}>Ukuran {r.size} · {fgQuantity(r.qty)}</p>)}{c.components.map((x,i)=><p key={i}>{x.name} · {amountText(x.rate)}/pcs</p>)}</details></div>)}</>}
  {d.note&&<p>Catatan · {d.note}</p>}<p>{pay?'Terpilih di '+pay.number+' · '+pay.status:'Belum dipilih untuk pembayaran'}</p>
  <div className="owner-payroll-actions">{pay&&editablePayroll(pay)&&<button className="soft-btn" onClick={()=>{savePayDrafts(choosePayrollSource(readPayDrafts(),pay.number,number,false));setMsg('Nota dilepas untuk periode berikutnya.')}}>Lepas dari pembayaran</button>}
  <button className="primary-btn" onClick={()=>{try{payForSource(number,sessionStorage.getItem('erp.owner.payroll.focus'),true);location.assign('/keuangan/payroll-kasbon/')}catch(e){setMsg((e as Error).message)}}}>{pay?'Buka payroll terkait':'Masukkan ke payroll'}</button><a className="gar-button" href="/keuangan/payroll-kasbon/">Kembali ke Payroll &amp; Kasbon</a></div>{msg&&<p role="status">{msg}</p>}</section></>
}

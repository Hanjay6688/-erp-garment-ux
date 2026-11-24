import {useState} from 'react'
import {FileText} from 'lucide-react'
import {fgQuantity} from '../fgQuantity'
import {allPayrollSources,choosePayrollSource,editablePayroll,payForSource,readPayDrafts,savePayDrafts} from './payrollSources'
import {amountText as price} from './accessoryPricing'
import RecordTable from '../RecordTable'
import './warehouseForms.css'

export default function PostedFgDetail({number}:{number:string}){
  const source=allPayrollSources().find(s=>s.kind==='FG'&&s.doc.number===number),[msg,setMsg]=useState('')
  const fromPay=new URLSearchParams(location.search).get('dari')==='payroll'
  const back=<a className="soft-btn" href={fromPay?'/keuangan/payroll-kasbon/':'/produksi/susun-nota-fg/'}>{fromPay?'Kembali ke Payroll & Kasbon':'Kembali ke Susun Nota FG'}</a>
  if(!source||source.kind!=='FG')return <section className="panel wh-nota-document"><h1>Nota FG tidak ditemukan</h1>{back}</section>
  const d=source.doc,pay=readPayDrafts().find(p=>p.status!=='REVERSED'&&p.fgNotes.some(n=>n.number===number))
  const repairs=d.repairCards??[],regular=d.regularCards??[],additional=repairs.reduce((n,c)=>n+c.qty,0)
  const status=pay?.status==='PAID'?'Sudah dibayar':pay?'Terpilih di '+pay.number+' · '+pay.status:'Belum dipilih untuk pembayaran'
  return <><section className="hero-copy compact wh-doc-bar"><div><div className="eyebrow">PRODUKSI · NOTA FG</div><h1>{number}</h1><p>{source.mandor} · {d.date} · Posted</p></div>{back}</section>
  <section className="panel wh-nota-document"><header className="wh-section-head"><div><span>DOKUMEN SUMBER</span><h2>{d.sku}</h2><small>{d.source}</small></div><FileText/></header>
  <div className="wh-doc-summary">{regular.length>0||!repairs.length?<div><small>Good reguler</small><strong>{fgQuantity(d.good)}</strong></div>:null}{repairs.length>0&&<div><small>Good dari perbaikan / susulan</small><strong>{fgQuantity(additional)}</strong></div>}{(regular.length>0||d.bs>0||d.stuck>0)&&<><div><small>BS</small><strong>{fgQuantity(d.bs)}</strong></div><div><small>Stuck</small><strong>{fgQuantity(d.stuck)}</strong></div></>}</div>
  {regular.map(c=><article className="wh-nota-block" key={c.id}><div className="wh-doc-bar"><div><small>FG REGULER</small><h3>{c.sku}</h3><p>{c.source} · {c.id}</p></div><strong>{price(c.subtotal)}</strong></div>
  <details><summary>Ukuran &amp; tarif · {c.sku}</summary><p>Jahit {price(c.sewingRate)} + komisi {price(c.commissionRate)} + reimburse {price(c.bomRate)} per pcs.</p><p>{c.sewnQty} pcs × {price(c.sewingRate+c.commissionRate+c.bomRate)} − BS {price(c.bsDeduction)} − Stuck {price(c.stuckDeduction)} = {price(c.subtotal)}</p>
  {c.sizeRows?.length?<RecordTable><thead><tr><th>Ukuran</th><th>Dijahit</th><th>Good</th><th>BS</th><th>Stuck</th><th>Cuci ulang</th></tr></thead><tbody>{c.sizeRows.map(r=><tr key={r.size}><th>{r.size}</th><td>{r.sewn}</td><td>{fgQuantity(r.good)}</td><td>{r.bs}</td><td>{r.hold}</td><td>{r.rewash}</td></tr>)}</tbody></RecordTable>:<p>Rincian ukuran tidak tersimpan pada kartu ini.</p>}</details></article>)}
  {repairs.map(c=><article className="wh-nota-block" key={c.id}><div className="wh-doc-bar"><div><small>BIKIN BAGUS / SUSULAN</small><h3>{c.sku}</h3><p>{c.source} · {c.qty} pcs × {price(c.unitRate)} = {price(c.subtotal)}</p></div><strong>{price(c.subtotal)}</strong></div><details><summary>Ukuran &amp; komponen · {c.sku}</summary><p>{c.id}</p><div className="wh-size-boxes">{c.sizeRows?.map(r=><div className="wh-size-box" key={r.size}><header>Ukuran <strong>{r.size}</strong></header><p>{fgQuantity(r.qty)}</p></div>)}</div>{c.components.map((x,i)=><div className="wh-register-row" key={i}><span>{x.name}</span><strong>{price(x.rate)}/pcs</strong></div>)}</details></article>)}
  {!regular.length&&!repairs.length&&<p>Arsip nota ini menyimpan total. Rincian kartu dan ukuran tidak tersedia.</p>}
  <div className="wh-doc-summary"><div><small>Upah dan komponen</small><strong>{price(d.labor)}</strong></div><div><small>Reimburse</small><strong>{price(d.reimbursement)}</strong></div><div><small>Total nota</small><strong>{price(d.labor+d.reimbursement)}</strong></div></div>
  {d.note&&<p>Catatan · {d.note}</p>}<p>{status}</p><div className="owner-payroll-actions">{pay&&editablePayroll(pay)&&<button className="soft-btn" onClick={()=>{try{savePayDrafts(choosePayrollSource(readPayDrafts(),pay.number,number,false));setMsg('Nota dilepas untuk periode berikutnya.')}catch(e){setMsg((e as Error).message)}}}>Lepas dari pembayaran</button>}
  <button className="primary-btn" onClick={()=>{try{payForSource(number,sessionStorage.getItem('erp.owner.payroll.focus'),true);location.assign('/keuangan/payroll-kasbon/')}catch(e){setMsg((e as Error).message)}}}>{pay?'Buka payroll terkait':'Masukkan ke payroll'}</button></div>{msg&&<p role="status">{msg}</p>}</section></>
}

import {browseMatch} from '../browseMatch'
import {dayOk,lastWarehouseDay} from './warehouseDay'
import {useState} from 'react'
import RecordTable from '../RecordTable'
import {ReasonDialog} from './planner/ReasonDialog'
import {amountText,fixtureDate} from './accessoryPricing'

import {pocketRolls,readReceipts,receiptPath,type PocketRoll,type PocketUnit} from './pocketReceipts'
import {ArrowDownLeft,ArrowUpRight,Ruler} from 'lucide-react'
import './warehouseForms.css'
const sewn=[
  {po:'PO-1069',mandor:'Epi',day:'2026-11-23',wip:12,fg:18,sold:6},
  {po:'PO-LUCY',mandor:'Afui',day:'2026-11-24',wip:8,fg:10,sold:6},
]
type Issue={id:string;roll:string;date:string;qty:number;cents:number;reason:string;unit?:PocketUnit;reversal?:string}
type Split={po:string;mandor:string;pcs:number;wip:number;fg:number;sold:number}
type Allocation={id:string;start:string;end:string;cents:number;pcs:number;parts:Split[];sources:string[];reason:string;reversal?:string}
type Book={issues:Issue[];allocations:Allocation[]}
const key='erp.demo.pocket.period.v1'
const read=():Book=>JSON.parse(sessionStorage.getItem(key)??'{"issues":[],"allocations":[]}')
const units=1_000_000
const fmt=(q:number)=>q.toLocaleString('id-ID',{maximumFractionDigits:6})
const price=(cents:number)=>amountText(cents/100)
const active=(b:Book,start:string,end:string)=>b.allocations.some(a=>!a.reversal&&a.start<=end&&a.end>=start)
const balance=(b:Book,roll:PocketRoll,through?:string)=>roll.length*units-b.issues.filter(i=>i.roll===roll.id&&!i.reversal&&(!through||i.date<=through)).reduce((s,i)=>s+i.qty,0)
function planAllocation(book:Book,start:string,end:string){
  if(!start||!end||start>end||end>lastWarehouseDay()||(Date.parse(end)-Date.parse(start))/86400000>366)throw Error('Pilih periode sampai hari ini, maksimal 367 hari.')
  if(active(book,start,end))throw Error('Periode ini bertumpang tindih dengan alokasi aktif.')
  const docs=book.issues.filter(i=>!i.reversal&&start<=i.date&&i.date<=end)
  const jobs=sewn.filter(j=>start<=j.day&&j.day<=end)
  const pcs=jobs.reduce((n,j)=>n+j.wip+j.fg+j.sold,0), cents=docs.reduce((n,i)=>n+i.cents,0)
  if(!cents||!pcs)throw Error(!cents?'Belum ada biaya kain keluar pada periode ini.':'Belum ada hasil selesai dijahit pada periode ini.')
  let done=0
  function share(qty:number){const before=Math.round(cents*done/pcs);done+=qty;return Math.round(cents*done/pcs)-before}
  const parts=jobs.map(j=>({po:j.po,mandor:j.mandor,pcs:j.wip+j.fg+j.sold,wip:share(j.wip),fg:share(j.fg),sold:share(j.sold)}))
  return {start,end,cents,pcs,parts,sources:docs.map(i=>i.id)}
}
export default function PocketFabric(){
  const rolls=pocketRolls()
  const requested=new URLSearchParams(location.search).get('roll')
  const [book,setBook]=useState(read),[rollId,setRoll]=useState(()=>rolls.find(r=>r.id===requested)?.id??rolls[0].id),[mode,setMode]=useState('keluar'),[qty,setQty]=useState(''),[day,setDay]=useState(()=>[fixtureDate,rolls.find(r=>r.id===requested)?.date??''].sort().at(-1)!)
  const [reason,setReason]=useState('Pemakaian kain kantong'),[start,setStart]=useState('2026-11-23'),[end,setEnd]=useState(fixtureDate),[allocReason,setAllocReason]=useState('Pembagian biaya kain kantong')
  const [preview,setPreview]=useState<ReturnType<typeof planAllocation>|null>(null),[msg,setMsg]=useState(''),[undo,setUndo]=useState<{id:string;kind:'issue'|'period'}|null>(null),[why,setWhy]=useState('')
  const roll=rolls.find(r=>r.id===rollId)!,left=balance(book,roll)
  function mutate(operation:(b:Book)=>Book,message:string){try{const next=operation(read());sessionStorage.setItem(key,JSON.stringify(next));setBook(next);setPreview(null);setMsg(message);return true}catch(e){setMsg((e as Error).message);return false}}
  function issue(){
    const ok=mutate(b=>{
      const n=qty.trim().replace(',','.')
      if(!/^\d+(\.\d{1,6})?$/.test(n)||!reason.trim()||!dayOk(day)||day<roll.date)throw Error('Periksa tanggal, jumlah dan alasan pemakaian.')
      if(!pocketRolls().some(r=>r.id===roll.id))throw Error('Roll tidak lagi tersedia.')
      if(active(b,day,day))throw Error('Batalkan pembagian periode ini sebelum mengubah pemakaian.')
      const physical=Math.round(Number(n)*units),atDate=balance(b,roll,day),available=Math.min(atDate,balance(b,roll)),delta=mode==='sisa'?atDate-physical:physical
      if(!Number.isSafeInteger(delta)||delta<=0||delta>available)throw Error('Jumlah keluar harus positif dan cukup dari saldo roll.')
      const entry={id:'KT-'+String(b.issues.length+1).padStart(3,'0')+'-OUT',roll:roll.id,unit:roll.unit,date:day,qty:delta,cents:Math.round(delta*roll.rate*100/units),reason:reason.trim()}
      return {...b,issues:[...b.issues,entry]}
    },'Pengeluaran tercatat. Saldo roll dan biaya periode sudah diperbarui.')
    if(ok)setQty('')
  }
  const [rollQuery,setRollQuery]=useState(''),[whole,setWhole]=useState<string[]>([])
  const [wholeReview,setWholeReview]=useState<{roll:string;qty:number;unit:PocketUnit;rate:number}[]|null>(null)
  const shownRolls=rolls.filter(r=>browseMatch(rollQuery,r.id,r.name,r.receipt,r.unit,r.date))
  function selectRoll(r:PocketRoll){setRoll(r.id);if(r.date>day)setDay(r.date);setQty('');setMsg('')}
  function wholeLines(b:Book){
    if(!dayOk(day)||!reason.trim()||!whole.length)throw Error('Pilih roll, tanggal dan alasan pemakaian.')
    if(active(b,day,day))throw Error('Periode sudah dibagikan.')
    return whole.map(id=>{
      const r=pocketRolls().find(x=>x.id===id)
      if(!r||r.date>day)throw Error('Roll belum diterima pada tanggal ini.')
      const qty=balance(b,r,day)
      if(qty<=0||qty!==balance(b,r))throw Error('Saldo roll berubah atau sudah ada pemakaian sesudah tanggal ini.')
      return {roll:id,qty,unit:r.unit,rate:r.rate}
    })
  }
  function saveWhole(){
    if(!wholeReview)return
    const ok=mutate(b=>{
      const rows=wholeLines(b)
      if(JSON.stringify(rows)!==JSON.stringify(wholeReview))throw Error('Saldo roll berubah. Buka review lagi.')
      const issues=rows.map((r,i)=>({id:'KT-'+String(b.issues.length+i+1).padStart(3,'0')+'-OUT',roll:r.roll,unit:r.unit,date:day,
        qty:r.qty,cents:Math.round(r.qty*r.rate*100/units),reason:reason.trim()}))
      return {...b,issues:[...b.issues,...issues]}
    },wholeReview.length+' roll dikeluarkan. Rincian panjang dan biaya tersimpan per roll.')
    if(ok){setWhole([]);setWholeReview(null)}
  }
  function post(){if(!preview)return;mutate(b=>{const current=planAllocation(b,start,end);if(!allocReason.trim()||JSON.stringify(current)!==JSON.stringify(preview))throw Error('Periksa ulang pratinjau dan isi alasan.')
    return {...b,allocations:[...b.allocations,{...current,id:'BAGI-'+String(b.allocations.length+1).padStart(3,'0'),reason:allocReason.trim()}]}
  },'Biaya dibagikan. Saldo roll tetap sama.')}
  function reverse(){if(!undo||!why.trim())return;const ok=mutate(b=>{
    if(undo.kind==='period'){const a=b.allocations.find(a=>a.id===undo.id);if(!a||a.reversal)throw Error('Alokasi sudah dibatalkan.');return {...b,allocations:b.allocations.map(a=>a.id===undo.id?{...a,reversal:why.trim()}:a)}}
    const row=b.issues.find(i=>i.id===undo.id);if(!row||row.reversal||active(b,row.date,row.date))throw Error('Batalkan alokasi aktif yang memakai biaya ini dahulu.')
    return {...b,issues:b.issues.map(i=>i.id===undo.id?{...i,reversal:why.trim()}:i)}
  },undo.kind==='period'?'Pembagian dibalik. Biaya kembali ke periode.':'Pemakaian dibalik. Panjang kembali ke saldo roll.');if(ok)setUndo(null)}
  return <><section className="hero-copy compact"><div className="eyebrow">Gudang</div><h1>Kain kantong</h1><p>Catat kain keluar dari gudang. Biayanya bisa dibagi ke hasil jahit satu periode.</p></section>
    <section className="panel wh-pocket-use"><header className="wh-section-head"><div><span>GUDANG BAHAN</span><h2>Pemakaian roll</h2></div><a className="soft-btn" href={receiptPath}><ArrowDownLeft size={16}/>Terima pembelian kain kantong</a></header>
    <section className="pocket-roll-register" aria-label="Daftar pemakaian per roll"><div className="wh-section-head"><div><h3>Pemakaian per roll</h3><small>Centang untuk menghabiskan seluruh sisa. Pilih nomor roll untuk memakai sebagian.</small></div><label>Cari roll<input type="search" value={rollQuery} onChange={e=>setRollQuery(e.target.value)} placeholder="Nomor roll atau surat jalan"/></label></div>
    <div className="pocket-roll-lines">{shownRolls.map(r=>{const residual=balance(book,r);return <div key={r.id} className="pocket-roll-line">
      <label><input type="checkbox" aria-label={'Pakai seluruh '+r.id} disabled={residual<=0} checked={whole.includes(r.id)} onChange={e=>setWhole(e.target.checked?[...whole,r.id]:whole.filter(id=>id!==r.id))}/></label>
      <button type="button" className="gar-text" onClick={()=>selectRoll(r)}><strong>{r.id}</strong><small>{r.name} · {r.receipt}</small></button>
      <span>Masuk <b>{fmt(r.length)} {r.unit}</b></span><span>Terpakai <b>{fmt(r.length-residual/units)} {r.unit}</b></span><span>Sisa <b>{fmt(residual/units)} {r.unit}</b></span></div>})}
      {!shownRolls.length&&<p>Roll tidak ditemukan.</p>}</div><div className="owner-payroll-actions"><button className="soft-btn" disabled={!whole.length} onClick={()=>{try{setWholeReview(wholeLines(read()));setMsg('')}catch(e){setMsg((e as Error).message)}}}>Pakai seluruh sisa · {whole.length} roll</button></div></section>
    {wholeReview&&<ReasonDialog title="Pemakaian roll utuh" closeLabel="Kembali" onClose={()=>setWholeReview(null)}><p>{day} · {reason}</p>{wholeReview.map(r=><p key={r.roll}><b>{r.roll}</b> · {fmt(r.qty/units)} {r.unit} keluar · sisa 0 {r.unit}</p>)}<button className="primary-btn" onClick={saveWhole}>Catat {wholeReview.length} roll keluar</button>{msg&&<p role="status">{msg}</p>}</ReasonDialog>}
    <div className="wh-columns"><div className="wh-side"><header><Ruler size={18}/><h3>Roll yang dipakai</h3></header><label>Roll<select aria-label="Roll" value={rollId} onChange={e=>{const next=rolls.find(r=>r.id===e.target.value);if(next)selectRoll(next)}}>{rolls.map(r=><option key={r.id} value={r.id}>{r.id} · {r.name} · {r.unit}</option>)}</select></label><div className="wh-stock"><div><small>{roll.location} · {roll.name}</small><span>Saldo gudang</span></div><strong>{fmt(left/units)} {roll.unit}</strong></div><small>Nilai per {roll.unit} · {amountText(roll.rate)}</small></div>
    <div className="wh-side"><header><ArrowUpRight size={18}/><h3>Kain keluar</h3></header><div className="wh-fields"><label>Cara mencatat<select value={mode} onChange={e=>{setMode(e.target.value);setQty('')}}><option value="keluar">Jumlah keluar</option><option value="sisa">Hitung sisa roll</option></select></label><label>{(mode==='sisa'?'Sisa fisik':'Keluar')+' ('+roll.unit+')'}<input inputMode="decimal" placeholder="0" value={qty} onChange={e=>setQty(e.target.value)}/></label><label>Tanggal pemakaian<input type="date" value={day} min={roll.date} max={lastWarehouseDay()} onChange={e=>setDay(e.target.value)}/></label><label>Alasan pemakaian<input value={reason} onChange={e=>setReason(e.target.value)}/></label></div><button className="primary-btn" type="button" onClick={issue}>Catat pemakaian</button></div></div>
    <div className="wh-roll-ledger"><h3>Mutasi roll · {roll.id}</h3><div className="wh-register-row"><span><strong>Masuk · {fmt(roll.length)} {roll.unit}</strong><small>{roll.date} · {roll.receipt}</small></span><a href={receiptPath+'&surat='+encodeURIComponent(roll.receipt)}>Lihat penerimaan</a></div>
    {book.issues.filter(i=>i.roll===roll.id).map(i=><div className="wh-register-row" key={i.id}><span><strong>Keluar · {fmt(i.qty/units)} {roll.unit}</strong><small>{i.date} · {i.id} · {i.reason}</small></span><span>{i.reversal?'Dibalik · '+i.reversal:'Posted'}</span></div>)}</div></section>
    <section className="panel gar-panel"><h2>Bagi ke HPP per periode</h2><div className="sku-range-fields"><label>Mulai periode<input type="date" value={start} onChange={e=>{setStart(e.target.value);setPreview(null)}}/></label><label>Akhir periode<input type="date" value={end} max={lastWarehouseDay()} onChange={e=>{setEnd(e.target.value);setPreview(null)}}/></label><label>Alasan pembagian<input value={allocReason} onChange={e=>setAllocReason(e.target.value)}/></label></div>
    <button className="soft-btn" type="button" onClick={()=>{try{setPreview(planAllocation(read(),start,end));setMsg('')}catch(e){setPreview(null);setMsg((e as Error).message)}}}>Lihat perhitungan</button>
    {preview&&<div className="gar-box"><h3>{price(preview.cents)} ÷ {preview.pcs} pcs = {amountText(preview.cents/100/preview.pcs)}/pcs</h3><RecordTable><thead><tr><th>PO / mandor</th><th>Selesai dijahit</th><th>WIP</th><th>FG tersedia</th><th>HPP terjual</th></tr></thead><tbody>{preview.parts.map(p=><tr key={p.po}><td>{p.po} · {p.mandor}</td><td>{p.pcs} pcs</td><td>{price(p.wip)}</td><td>{price(p.fg)}</td><td>{price(p.sold)}</td></tr>)}</tbody></RecordTable><button className="primary-btn" disabled={!allocReason.trim()} onClick={post}>Sahkan pembagian</button></div>}</section>
    <section className="panel gar-panel"><h2>Riwayat</h2>{!book.issues.length&&<p>Belum ada pengeluaran.</p>}{[...book.issues].reverse().map(i=><div className="owner-doc-row" key={i.id}><span><strong>{i.id} · {i.roll}</strong><small>{i.date} · {fmt(i.qty/units)} {i.unit??rolls.find(r=>r.id===i.roll)?.unit??readReceipts().flatMap(r=>r.rolls).find(r=>r.id===i.roll)?.unit??'yd'} · {price(i.cents)} · {i.reason}</small></span>{i.reversal?<span>Dibalik · {i.reversal}</span>:<button className="soft-btn" onClick={()=>{setUndo({kind:'issue',id:i.id});setWhy('')}}>Balikkan pemakaian</button>}</div>)}
    {book.allocations.map(a=><div className="owner-doc-row" key={a.id}><span><strong>{a.id} · {price(a.cents)}</strong><small>{a.start} – {a.end} · {a.pcs} pcs</small></span>{a.reversal?<span>Dibatalkan · {a.reversal}</span>:<button className="soft-btn" onClick={()=>{setUndo({kind:'period',id:a.id});setWhy('')}}>Batalkan pembagian</button>}</div>)}</section>
    {msg&&!undo&&<p className="gar-success" role="status">{msg}</p>}{undo&&<ReasonDialog title={'Pembalikan '+undo.id} onClose={()=>setUndo(null)} closeLabel="Kembali"><label>Alasan pembalikan<input value={why} onChange={e=>setWhy(e.target.value)}/></label><button disabled={!why.trim()} onClick={reverse}>Konfirmasi pembalikan</button>{msg&&<p role="status">{msg}</p>}</ReasonDialog>}</>
}

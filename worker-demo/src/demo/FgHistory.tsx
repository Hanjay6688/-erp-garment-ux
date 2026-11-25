import {browseMatchPieces} from '../browseMatch'
import {useState} from 'react'
import {ArrowRight} from 'lucide-react'
import {fgQuantity} from '../fgQuantity'
import type {Product} from '../productCatalog'
import RecordTable from '../RecordTable'
import {comparePhysical,fgActivity,type FgMovement} from './fgTimeline'
import {stockAt} from './planner/conversion'
import {type Session} from './planner/model'
import {skuByKey} from './skuCatalog'
import {matchesPeriod,PeriodFilter,periodFor} from './PeriodFilter'
import {ReasonDialog} from './planner/ReasonDialog'
import './warehouseForms.css'

type Row=FgMovement
export function historyRows(p:Product,s:Session):Row[]{
  const article=skuByKey(p.brand+' '+p.code,s)!
  const rows=fgActivity(article,s,p.location,p.grade)
  rows.sort((a,b)=>comparePhysical(a,b)||(a.sequence??'').localeCompare(b.sequence??'')).reverse()
  let balance=p.sizes.map(size=>stockAt(article,size,s,p.location,p.grade))
  for(const row of rows){
    row.balance=balance
    balance=balance.map((n,i)=>n-row.delta[i])
  }
  if(!rows.some(r=>r.fromOpeningBook)){
    rows.push({id:'awal-'+article.key,ref:'Saldo awal',day:'',physicalTime:'',type:'Saldo awal',note:p.location,delta:balance.map(()=>0),balance})
  }
  return rows
}
function movementWhen(row:Row){
  if(!row.day)return 'Tanggal fisik belum tercatat'
  const date=new Intl.DateTimeFormat('id-ID',{day:'numeric',month:'short',year:'numeric',timeZone:'Asia/Jakarta'}).format(new Date(row.day+'T06:00:00Z'))
  const time=row.physicalTime
  return date+(time?' · '+time.replace('.',':')+' WIB':' · jam fisik belum tercatat')
}
function recordedWhen(value:string){return new Intl.DateTimeFormat('id-ID',{day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23',timeZone:'Asia/Jakarta'}).format(new Date(value))+' WIB'}
export function FgHistory({product,session}:{product:Product;session:Session}){
  const rows=historyRows(product,session),[q,setQ]=useState(''),[sort,setSort]=useState('new'),[period,setPeriod]=useState(()=>periodFor('all',rows[0]?.day||'2026-11-24')),[detail,setDetail]=useState<Row|null>(null)
  const visible=rows.filter(r=>{
    const quantities = [r.delta.reduce((n,d)=>n+Math.max(d,0),0),r.delta.reduce((n,d)=>n+Math.min(d,0),0),r.balance.reduce((n,x)=>n+x,0)]
    return (r.day||(!period.start&&!period.end))&&matchesPeriod(r.day,period)&&browseMatchPieces(q,quantities,r.ref,r.type,r.note,r.day,movementWhen(r))
  })
  if(sort==='old')visible.reverse()
  return <section className="fg-history"><h3>Riwayat stok · {product.brand} {product.code}</h3><div className="wh-fields"><label>Cari dokumen atau transaksi<input value={q} onChange={e=>setQ(e.target.value)}/></label><label>Urutan riwayat<select value={sort} onChange={e=>setSort(e.target.value)}><option value="new">Terbaru dulu</option><option value="old">Terlama dulu</option></select></label></div>
  <PeriodFilter label="Periode mutasi" value={period} onChange={setPeriod}/>
  <table className="wh-moves"><tbody>{visible.map(r=><tr key={r.id}><td><div className="wh-move-head"><div><div className="fg-movement-date"><span>Waktu fisik</span><time dateTime={r.day||undefined}>{movementWhen(r)}</time></div><button className="gar-text" onClick={()=>setDetail(r)}>{r.type} · {r.ref}</button><small>{r.note}</small>{r.href&&<a className="source-row-link" href={r.href}>Buka dokumen sumber <ArrowRight aria-hidden="true"/></a>}{r.sequence&&<small>Dicatat sistem · {recordedWhen(r.sequence)}</small>}</div><div className="wh-move-totals"><span>Masuk <b>{fgQuantity(r.delta.reduce((n,d)=>n+Math.max(d,0),0))}</b></span><span>Keluar <b>{fgQuantity(r.delta.reduce((n,d)=>n+Math.max(-d,0),0))}</b></span><span>Saldo <b>{fgQuantity(r.balance.reduce((n,x)=>n+x,0))}</b></span></div></div>
    <div className="wh-size-boxes">{product.sizes.map((v,i)=><div className="wh-size-box" key={v} aria-label={'Ukuran '+v}><header>Ukuran <strong>{v}</strong></header><dl><div className={r.delta[i]>0?'wh-in':''}><dt>Masuk</dt><dd>{Math.max(r.delta[i],0)} potong</dd></div><div className={r.delta[i]<0?'wh-out':''}><dt>Keluar</dt><dd>{Math.max(-r.delta[i],0)} potong</dd></div><div><dt>Saldo</dt><dd>{r.balance[i]} potong</dd></div></dl></div>)}</div></td></tr>)}</tbody></table>
  {!visible.length&&<p>Tidak ada mutasi yang cocok.</p>}
  {detail&&<ReasonDialog title={detail.type+' · '+product.brand+' '+product.code} onClose={()=>setDetail(null)} closeLabel="Kembali"><p><strong>Waktu fisik · {movementWhen(detail)}</strong></p>{detail.sequence&&<p>Dicatat sistem · {recordedWhen(detail.sequence)}</p>}<p>{detail.ref} · {detail.note}</p>{detail.href&&<a className="soft-btn" href={detail.href}>Buka dokumen sumber <ArrowRight size={15}/></a>}<RecordTable><thead><tr><th>Ukuran</th><th>Sebelum</th><th>Perubahan</th><th>Sesudah</th></tr></thead><tbody>{product.sizes.map((x,i)=><tr key={x}><td>{x}</td><td>{fgQuantity(detail.balance[i]-detail.delta[i])}</td><td>{fgQuantity(detail.delta[i])}</td><td>{fgQuantity(detail.balance[i])}</td></tr>)}</tbody></RecordTable></ReasonDialog>}</section>
}

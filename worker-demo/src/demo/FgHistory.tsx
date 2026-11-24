import {useState} from 'react'
import {fgQuantity} from '../fgQuantity'
import type {Product} from '../productCatalog'
import RecordTable from '../RecordTable'
import {saleMoves} from './saleBook'
import {initialMovements,productKey,movementProductKey} from './stockModel'
import {type Session} from './planner/model'
import {atPosition,nativePosition,skuByKey} from './skuCatalog'
import {matchesPeriod,PeriodFilter,periodFor} from './PeriodFilter'
import {ReasonDialog} from './planner/ReasonDialog'
import './warehouseForms.css'

type Row={id:string;ref:string;when:string;day:string;type:string;note:string;delta:number[];balance:number[];sequence?:string}
const months=['jan','feb','mar','apr','mei','jun','jul','agu','sep','okt','nov','des']
function isoDate(text:string){const [d,m,y]=text.split(' ');return y+'-'+String(months.indexOf(m.toLowerCase())+1).padStart(2,'0')+'-'+d.padStart(2,'0')}
export function historyRows(p:Product,s:Session):Row[]{
  const key=p.brand+' '+p.code,a=skuByKey(key)!
  const pos=nativePosition(a),home=pos.grade===p.grade&&pos.location===p.location
  const old=home?initialMovements.filter(m=>movementProductKey(m)===productKey(p)).map(m=>({...m,when:m.date,day:isoDate(m.date)})):[]
  let balance=p.sizes.map(x=>home?a.opening[x]??0:0)
  const opening:Row[] = old.length?old:[{id:'awal-'+key,ref:'Saldo awal',when:'Saldo pembukaan',day:'2026-08-01',type:'Saldo awal',note:p.location,delta:balance.map(()=>0),balance:[...balance]}]
  const newRows:Row[]=home?saleMoves(productKey(p)).map(m=>({...m,sequence:m.recordedAt})):[]
  for(const e of s.stockEvents??[]){
    const changes=e.changes.filter(c=>c.key===key&&atPosition(c,p.location,p.grade))
    if(!changes.length)continue
    const delta=p.sizes.map(size=>changes.filter(c=>c.size===size).reduce((n,c)=>n+c.delta,0))
    const day=e.date??'2026-11-24'
    newRows.push({id:e.id,ref:e.id,when:day,day,type:e.reverses?'Pembalikan':e.action==='adjust'?'Stock Adjustment':'Ganti Merek',note:e.reason,delta,balance:[],sequence:e.recordedAt})
  }
  newRows.sort((a,b)=>a.day.localeCompare(b.day)||(a.sequence??'').localeCompare(b.sequence??''))
  for(const row of newRows){balance=balance.map((n,i)=>n+row.delta[i]);row.balance=[...balance]}
  return [...newRows.reverse(),...opening].sort((a,b)=>b.day.localeCompare(a.day))
}
export function FgHistory({product,session}:{product:Product;session:Session}){
  const rows=historyRows(product,session),[q,setQ]=useState(''),[sort,setSort]=useState('new'),[period,setPeriod]=useState(()=>periodFor('all',rows[0]?.day??'2026-11-24')),[detail,setDetail]=useState<Row|null>(null)
  const visible=rows.filter(r=>matchesPeriod(r.day,period)&&(r.ref+' '+r.type+' '+r.note).toLowerCase().includes(q.toLowerCase()))
  if(sort==='old')visible.reverse()
  return <section className="fg-history"><h3>Riwayat stok · {product.brand} {product.code}</h3><div className="wh-fields"><label>Cari dokumen atau transaksi<input value={q} onChange={e=>setQ(e.target.value)}/></label><label>Urutan riwayat<select value={sort} onChange={e=>setSort(e.target.value)}><option value="new">Terbaru dulu</option><option value="old">Terlama dulu</option></select></label></div>
  <PeriodFilter label="Periode mutasi" value={period} onChange={setPeriod}/>
  <table className="wh-moves"><tbody>{visible.map(r=><tr key={r.id}><td><div className="wh-move-head"><div><small>{r.when}</small><button className="gar-text" onClick={()=>setDetail(r)}>{r.type} · {r.ref}</button><small>{r.note}</small></div><div className="wh-move-totals"><span>Masuk <b>{fgQuantity(r.delta.reduce((n,d)=>n+Math.max(d,0),0))}</b></span><span>Keluar <b>{fgQuantity(r.delta.reduce((n,d)=>n+Math.max(-d,0),0))}</b></span><span>Saldo <b>{fgQuantity(r.balance.reduce((n,x)=>n+x,0))}</b></span></div></div>
    <div className="wh-size-boxes">{product.sizes.map((v,i)=><div className="wh-size-box" key={v} aria-label={'Ukuran '+v}><header>Ukuran <strong>{v}</strong></header><dl><div className={r.delta[i]>0?'wh-in':''}><dt>Masuk</dt><dd>{Math.max(r.delta[i],0)} potong</dd></div><div className={r.delta[i]<0?'wh-out':''}><dt>Keluar</dt><dd>{Math.max(-r.delta[i],0)} potong</dd></div><div><dt>Saldo</dt><dd>{r.balance[i]} potong</dd></div></dl></div>)}</div></td></tr>)}</tbody></table>
  {!visible.length&&<p>Tidak ada mutasi yang cocok.</p>}
  {detail&&<ReasonDialog title={detail.type+' · '+product.brand+' '+product.code} onClose={()=>setDetail(null)} closeLabel="Kembali"><p>{detail.ref} · {detail.when} · {detail.note}</p><RecordTable><thead><tr><th>Ukuran</th><th>Sebelum</th><th>Perubahan</th><th>Sesudah</th></tr></thead><tbody>{product.sizes.map((x,i)=><tr key={x}><td>{x}</td><td>{fgQuantity(detail.balance[i]-detail.delta[i])}</td><td>{fgQuantity(detail.delta[i])}</td><td>{fgQuantity(detail.balance[i])}</td></tr>)}</tbody></RecordTable></ReasonDialog>}</section>
}

import {fgQuantity} from '../fgQuantity'
import {saleMoves} from './saleBook'
import {useState} from 'react'
import type {Product} from '../productCatalog'
import RecordTable from '../RecordTable'
import {initialMovements,productKey,movementProductKey} from './stockModel'
import {articles,type Session} from './planner/model'
import {matchesPeriod,PeriodFilter,periodFor} from './PeriodFilter'
import {ReasonDialog} from './planner/ReasonDialog'

type Row={id:string;ref:string;when:string;day:string;type:string;note:string;delta:number[];balance:number[]}
const months=['jan','feb','mar','apr','mei','jun','jul','agu','sep','okt','nov','des']
function isoDate(text:string){const [d,m,y]=text.split(' ');return y+'-'+String(months.indexOf(m.toLowerCase())+1).padStart(2,'0')+'-'+d.padStart(2,'0')}
function history(p:Product,session:Session):Row[]{
  const key=p.brand+' '+p.code,article=articles.find(a=>a.key===key)
  if(!article)return [...saleMoves(productKey(p))].reverse().concat(initialMovements.filter(m=>movementProductKey(m)===productKey(p)).map(m=>({...m,when:m.date,day:isoDate(m.date),key:productKey(p)})))
  let balance=p.sizes.map(size=>article.opening[size]??0)
  const rows:Row[]=[{id:'awal-'+key,ref:'Saldo awal',when:'20 Nov 2026',day:'2026-11-20',type:'Saldo awal',note:p.location,delta:[...balance],balance:[...balance]}]
  for(const e of session.stockEvents??[]){
    const changes=e.changes.filter(c=>c.key===key);if(!changes.length)continue
    const delta=p.sizes.map(s=>changes.filter(c=>c.size===s).reduce((n,c)=>n+c.delta,0))
    balance=balance.map((n,i)=>n+delta[i]);rows.push({id:e.id,ref:e.id,when:e.date??'2026-11-24',day:e.date??'2026-11-24',type:e.reverses?'Pembalikan':e.action==='adjust'?'Stock Adjustment':'Ganti Merek',note:e.reason,delta,balance:[...balance]})
  }
  return rows.reverse()
}
export function FgHistory({product,session}:{product:Product;session:Session}){
  const rows=history(product,session),[q,setQ]=useState(''),[sort,setSort]=useState('new'),[period,setPeriod]=useState(()=>periodFor('all',rows[0]?.day??'2026-11-24')),[detail,setDetail]=useState<Row|null>(null)
  const visible=rows.filter(r=>matchesPeriod(r.day,period)&&(r.ref+' '+r.type+' '+r.note).toLowerCase().includes(q.toLowerCase()))
  if(sort==='old')visible.reverse()
  return <section className="fg-history"><h3>Riwayat stok · {product.brand} {product.code}</h3><div className="sku-range-fields"><label>Cari dokumen atau transaksi<input value={q} onChange={e=>setQ(e.target.value)}/></label><label>Urutan riwayat<select value={sort} onChange={e=>setSort(e.target.value)}><option value="new">Terbaru dulu</option><option value="old">Terlama dulu</option></select></label></div>
  <PeriodFilter label="Periode mutasi" value={period} onChange={setPeriod}/>
  <div className="responsive-table"><table><thead><tr><th>Waktu fisik</th><th>Dokumen</th><th>Masuk</th><th>Keluar</th><th>Saldo</th></tr></thead><tbody>{visible.map(r=><tr key={r.id}><td>{r.when}</td><td><button className="gar-text" onClick={()=>setDetail(r)}>{r.type} · {r.ref}</button></td><td>{fgQuantity(r.delta.reduce((n,x)=>n+Math.max(0,x),0))}</td><td>{fgQuantity(r.delta.reduce((n,x)=>n+Math.max(0,-x),0))}</td><td>{fgQuantity(r.balance.reduce((a,b)=>a+b,0))}</td></tr>)}</tbody></table></div>{!visible.length&&<p>Tidak ada mutasi yang cocok.</p>}
  {detail&&<ReasonDialog title={detail.type+' · '+product.brand+' '+product.code} onClose={()=>setDetail(null)} closeLabel="Kembali"><p>{detail.ref} · {detail.when} · {detail.note}</p><RecordTable><thead><tr><th>Ukuran</th><th>Sebelum</th><th>Perubahan</th><th>Sesudah</th></tr></thead><tbody>{product.sizes.map((s,i)=><tr key={s}><td>{s}</td><td>{fgQuantity(detail.balance[i]-detail.delta[i])}</td><td>{fgQuantity(detail.delta[i])}</td><td>{fgQuantity(detail.balance[i])}</td></tr>)}</tbody></RecordTable></ReasonDialog>}</section>
}

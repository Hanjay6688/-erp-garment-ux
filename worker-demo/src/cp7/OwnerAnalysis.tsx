import { useState } from 'react'
import { ArrowRight, Search } from 'lucide-react'
import { action, day, patternFor, plansIn, seriesFor, seriesLabel, stageName } from '../demo/planner/model'
import { ActionTable, AdviceBox, cutPath, pickupPath, productionReason, routesLabel } from '../demo/planner/ProductionAdvice'
import { usePlannerSession } from '../demo/planner/session'

export default function OwnerAnalysis({page, onDetail, copy}: {page:string;onDetail:(sku:string)=>void;copy:(text:string,label:string)=>React.ReactNode}) {
  const session=usePlannerSession()
  const rows=plansIn(session)
  const [query,setQuery]=useState('')
  const [message,setMessage]=useState(false)
  const q=query.trim().toLocaleLowerCase()
  const filtered=rows.filter(r=>[r.product.brand,r.product.sku,r.product.size,r.product.range,r.product.customer,...r.product.routes.map(x=>patternFor(x.pattern).name+' '+x.material),...r.lots.map(l=>l.id+' '+l.place+' '+stageName[l.stage])].join(' ').toLocaleLowerCase().includes(q))
  const summary=rows.map(r=>r.product.brand+' '+r.product.sku+', ukuran '+r.product.size+', '+r.product.customer+' perlu '+r.product.need+' pcs pada '+day(r.product.due)+'. Stok siap '+r.product.fg+', WIP pasti tepat waktu '+r.confirmed+', WIP potensial '+r.potential+', WIP terlambat '+r.late+'. '+action(r)+'.').join('\n')
  const isList=['planner','stock','report','reminders'].includes(page)
  return <div className="gar-work">
    {isList&&<label className="cp7-search gar-search"><Search size={17}/><input value={query} onChange={e=>setQuery(e.target.value)} aria-label="Cari SKU atau ukuran" placeholder="Cari SKU, pola, bahan, atau mandor"/></label>}
    {page==='planner'&&<><div className="gar-pagehead"><h2>Tindakan yang perlu ditinjau</h2></div><p className="gar-help">Pilih satu SKU untuk melihat pesanannya, lokasi barang, dan sisa yang perlu dipotong.</p><ActionTable rows={filtered} onDetail={onDetail}/></>}
    {(page==='report'||page==='stock')&&<><div className="gar-pagehead"><h2>{page==='stock'?'Stok jadi dan barang dalam proses':'Kebutuhan per pesanan'}</h2></div><p className="gar-help">WIP adalah barang yang masih dikerjakan. Kolom pasti dan potensial hanya menghitung barang yang bisa siap sebelum tenggat.</p>
      <div className="gar-box gar-report"><table aria-label="Produksi per SKU"><thead><tr><th>SKU / ukuran</th><th>Pesanan</th><th>Siap jual</th><th>WIP pasti</th><th>WIP potensial</th><th>Perlu potong</th></tr></thead><tbody>{filtered.map(r=><tr key={r.product.sku}><th scope="row"><button className="gar-text" onClick={()=>onDetail(r.product.sku)}>{r.product.brand} {r.product.sku}</button><small>{seriesLabel(seriesFor(r.product))} · {day(r.product.due)}</small></th>{[r.product.need,r.product.fg,r.confirmed,r.potential,r.short].map((value,i)=><td key={i}>{value} pcs</td>)}</tr>)}</tbody></table></div></>}
    {page==='cutting'&&<><p className="gar-help">Ada dua pekerjaan di sini. Buat Potongan memakai kain baru. Bagi Potongan menyerahkan barang yang sudah dipotong ke mandor.</p>
      <AdviceBox mode="cut" session={session} onCut={(r,material)=>location.assign(cutPath+'?'+new URLSearchParams({sku:r.product.sku,...(material?{bahan:material}:{})}))}/>
      <AdviceBox mode="pickup" session={session} onPickup={l=>location.assign(pickupPath+'?pot='+l.id)}/></>}
    {page==='reminders'&&<><h2>Yang perlu ditindaklanjuti</h2><p className="gar-help">Urut dari pesanan yang paling dekat tenggatnya.</p><ActionTable rows={filtered.filter(r=>r.short||r.queue.length||r.check).sort((a,b)=>a.product.due.localeCompare(b.product.due))} onDetail={onDetail}/>{filtered.length>0&&!filtered.some(r=>r.short||r.queue.length||r.check)&&<p>Produksi untuk pilihan ini sudah mencukupi.</p>}</>}
    {page==='ai'&&<><h2>Tanya soal produksi</h2><p className="gar-help">Pilih SKU untuk membaca alasannya, atau salin angka latihan ini sebagai konteks pertanyaan.</p><div className="gar-actions">{rows.map(r=><button className="gar-button" key={r.product.sku} onClick={()=>onDetail(r.product.sku)}>Kenapa {r.product.sku}?</button>)}</div>{copy('Jelaskan prioritas potong dan bagi per SKU. Bedakan barang siap jual, WIP pasti, WIP potensial, dan WIP terlambat.\n'+summary,'Salin konteks produksi')}</>}
    {page==='whatsapp'&&<div className="gar-box"><h2>Ringkasan untuk mandor</h2><p>Lu bisa melihat isi pesan latihan di sini. Pengiriman WhatsApp belum aktif.</p><button className="gar-button" onClick={()=>setMessage(!message)}>{message?'Tutup pratinjau':'Pratinjau isi pesan'}</button>{message&&copy(summary,'Isi pesan contoh')}</div>}
    {isList&&!filtered.length&&<p role="status">Tidak ada SKU yang cocok dengan pencarian ini.</p>}
    {page==='planner'&&<details className="gar-box"><summary>Pola dan bahan untuk empat SKU contoh</summary><ul className="gar-dictionary">{rows.map(r=><li key={r.product.sku}><strong>{r.product.brand} {r.product.sku} · {seriesLabel(seriesFor(r.product))}</strong><span>{patternFor(r.product.routes[0].pattern).name} · {routesLabel(r)}</span></li>)}</ul></details>}
    {page==='stock'&&<details className="gar-box"><summary>Rincian per tahap dan tanggal siap</summary>{filtered.map(r=><p key={r.product.sku}><strong>{r.product.brand} {r.product.sku}</strong> · {r.lots.map(l=>stageName[l.stage]+' '+l.qty+' pcs ('+day(l.eta)+')').join(' · ')}. {productionReason(r)}</p>)}</details>}
    {page==='cutting'&&<div className="gar-actions"><a className="gar-button" href={cutPath}>Buka Buat Potongan <ArrowRight size={15}/></a><a className="gar-button" href={pickupPath}>Buka Bagi Potongan <ArrowRight size={15}/></a></div>}
  </div>
}

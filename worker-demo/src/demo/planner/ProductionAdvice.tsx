import { useState } from 'react'
import { ArrowRight, ChevronDown } from 'lucide-react'
import { cuttingForms, productionForms } from '../../demoCuttingRoutes'
import { action, day, patternFor, plan, plansIn, productFor, stageName, suggestedCut, waitingLots, type Lot, type Plan, type Session } from './model'
import './planner.css'

export const cutPath = cuttingForms['cutting-roll'].path
export const pickupPath = cuttingForms['mandor-wip'].path
export function routesLabel(row: Plan) {
  return row.product.routes.map(r => r.material).join(' / ')
}
export function productionReason(row: Plan) {
  const p=row.product
  const stages=['cut','sewing','laundry','qc'].flatMap(stage=>{
    const qty=row.lots.filter(l=>l.stage===stage && l.eta<=p.due).reduce((sum,l)=>sum+l.qty,0)
    const where:Record<string,string>={cut:'di meja potong',sewing:'sedang dijahit',laundry:'di laundry',qc:'di QC'}
    return qty?[qty+' pcs '+where[stage]]:[]
  })
  if (row.short) return 'Pesanan '+p.need+' pcs. Ada '+p.fg+' pcs siap jual, '+stages.join(' dan ')+'. Masih kurang '+row.short+' pcs.'
  if (row.check) return 'Tanyakan ke '+row.check.place+' apakah '+row.check.qty+' pcs ini untuk '+p.brand+' '+p.sku+'.'+(row.late?' Ada '+row.late+' pcs lain yang baru siap sesudah tenggat.':'')
  if (row.queue.length) return (p.fg?p.fg+' pcs sudah siap jual. ':'')+stages.join(' dan ')+'. Serahkan potongan yang ada ke mandor.'
  return (p.fg?p.fg+' pcs siap jual, ':'')+stages.join(' dan ')+'. Cukup untuk pesanan '+p.need+' pcs.' 
}
export function SourceDetail({ row }: {row: Plan}) {
  const p = row.product
  return <div className="gar-detail">
    <p className="gar-lead"><strong>{p.customer}</strong> memesan <strong>{p.need} pcs</strong> untuk {day(p.due)}. Semua harus ukuran <strong>{p.size}</strong>.</p>
    <dl className="gar-counts">{[['Pesanan',p.need],['Stok siap jual',p.fg],['WIP tujuan pasti',row.confirmed],['WIP potensial',row.potential],['Sisa perlu potong',row.short]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value} <small>pcs</small></dd></div>)}</dl>
    <p>{row.base > row.short ? <>Kalau hanya mengandalkan stok dan WIP yang pasti, masih kurang <strong>{row.base} pcs</strong>. Setelah memakai WIP potensial yang cocok, sisanya <strong>{row.short} pcs</strong>.</> : productionReason(row)}</p>
    <h3>Barangnya ada di mana?</h3>
    <ul className="gar-lots">{row.lots.map(lot=><li key={lot.id}><div><strong>{stageName[lot.stage]} · {lot.qty} pcs</strong><small>{lot.id}{lot.group?' / '+lot.group:''} · {lot.place}{lot.roll ? ' · roll ' + lot.roll : ''}</small></div><div>{patternFor(lot.pattern).name} · {lot.material}<small>Uk. {lot.size} · {lot.kind === 'directed' ? 'Tujuan pasti' : 'Tujuan perlu dipastikan'}</small></div><div className={lot.eta>p.due?'gar-late':''}>Siap {day(lot.eta)}<small>{lot.eta>p.due?'Lewat tenggat':'Masuk hitungan tenggat'}</small></div></li>)}</ul>
    {row.late>0&&<p className="gar-warn">{row.late} pcs tiba sesudah pesanan harus siap. Jumlah itu dikeluarkan dari hitungan di atas.</p>}
    <details><summary>Pesanan, pola dan bahan</summary><p>{p.order} · {p.brand} {p.sku} · rentang jual {p.range} · ukuran fisik {p.size} · {p.colour} · {p.finish}.</p><ul>{p.routes.map(r=><li key={r.material}>{patternFor(r.pattern).name} · {patternFor(r.pattern).revision} · {r.material}</li>)}</ul></details>
  </div>
}
export function Forms({row}: {row:Plan}) {
  return <div className="gar-actions">
    {row.short>0&&<a className="gar-button primary" href={cutPath+'?sku='+row.product.sku}>Buka Buat Potongan <ArrowRight size={15}/></a>}
    {row.check&&<a className="gar-button" href={productionForms['sewing-wip'].path+'?lot='+row.check.id}>Cek jahitan {row.check.place} <ArrowRight size={15}/></a>}
    {!row.queue.length&&!row.check&&row.lots.some(l=>l.stage==='laundry')&&<a className="gar-button" href={productionForms.laundry.path+'?sku='+row.product.sku}>Lihat laundry SKU ini <ArrowRight size={15}/></a>}
    {row.queue.length>0&&<a className="gar-button" href={pickupPath+'?pot='+row.queue[0].id}>Buka Bagi Potongan <ArrowRight size={15}/></a>}
  </div>
}
export function AdviceBox({mode, session, onCut, onPickup, selected}: {mode:'cut'|'pickup';session:Session;onCut?:(row:Plan)=>void;onPickup?:(lot:Lot)=>void;selected?:string}) {
  const [opened,setOpened]=useState('')
  const cuts=plansIn(session).filter(r=>r.short>0)
  const queue=waitingLots(session)
  const entries=mode==='cut' ? cuts.map(row=>({row,lot:null as Lot|null})) : queue.map(lot=>({row:plan(productFor(lot.sku)!,session),lot}))
  return <section className="panel gar-panel" aria-label={mode==='cut'?'Saran buat potongan':'Saran bagi potongan'}>
    <div className="gar-panel-head"><div><p className="gar-kicker">Planner · Selasa 24 Nov 2026</p><h2>{mode==='cut'?'Yang perlu dipotong':'Potongan yang dibagi dulu'}</h2></div><a href="/analisis/planner/">Lihat semua SKU</a></div>
    {!entries.length&&<p className="gar-empty">{mode==='cut'?'Kebutuhan tambahan sudah tertutup. Potongan yang tersedia bisa dilanjutkan ke mandor.':'Semua potongan contoh sudah diambil mandor.'}</p>}
    {entries.map(({row,lot})=>{
      const p=row.product, id=lot?.id??p.sku
      const suggestion=lot?undefined:suggestedCut(row,session)
      return <article className="gar-advice" key={id}><div className="gar-advice-line"><div>
        <h3>{lot ? lot.id+' · ' : ''}{p.brand} {p.sku} <span>· Uk. {p.size}</span></h3>
        <p>{patternFor(lot?.pattern??p.routes[0].pattern).name} · {lot?.material??routesLabel(row)} · {lot?.qty??row.short} pcs</p>
        <small>{lot ? p.customer+' perlu '+p.need+' pcs. Potongan ini belum diambil.' : productionReason(row)} Siap {day(p.due)}.</small>
        {suggestion&&<small className="gar-fabric">Roll {suggestion.roll.id} · tersedia {suggestion.available} yd · rencana pakai {suggestion.qty*suggestion.roll.yardPerPiece} yd{suggestion.qty<row.short?' · bahan cukup untuk '+suggestion.qty+' pcs':''}</small>}
      </div><button type="button" className="gar-button primary" disabled={Boolean(suggestion && !suggestion.qty)} onClick={()=>lot ? onPickup?.(lot) : onCut?.(row)}>{lot ? (selected===id?'Lihat pembagian '+id:'Pilih '+id) : suggestion?.qty ? 'Isi form · '+suggestion.qty+' pcs' : 'Bahan perlu disiapkan'} <ArrowRight size={15}/></button></div>
      <button type="button" className="gar-text" aria-expanded={opened===id} onClick={()=>setOpened(opened===id?'':id)}>Kenapa {lot?'dibagi':'dipotong'}? <ChevronDown size={14}/></button>
      {opened===id&&<SourceDetail row={row}/>}</article>
    })}
    {mode==='cut'&&<a className="gar-next" href={pickupPath}>Lihat potongan yang sudah siap dibagi <ArrowRight size={15}/></a>}
  </section>
}
export function ActionTable({ rows, onDetail }: {rows: Plan[];onDetail:(sku:string)=>void}) {
  return <div className="gar-list">{rows.map(row=><article key={row.product.sku} className="gar-plan" data-sku={row.product.sku}>
    <div><h3>{row.product.brand} {row.product.sku} <span>· Uk. {row.product.size}</span></h3><p>{patternFor(row.product.routes[0].pattern).name} · {routesLabel(row)}</p><small>{row.product.customer} · {row.product.need} pcs · {day(row.product.due)}</small></div>
    <div><strong>{action(row)}</strong><p>{productionReason(row)}</p></div>
    <button type="button" className="gar-button" onClick={()=>onDetail(row.product.sku)}>Lihat detail</button>
  </article>)}</div>
}

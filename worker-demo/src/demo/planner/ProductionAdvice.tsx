import { useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { cuttingForms, productionForms } from '../../demoCuttingRoutes'
import { action, cutRolls, day, remainingPieces, lotLabel, lotPattern, lotSeries, patternFor, plansIn, possibleTargets, seriesFor, seriesLabel, setDestination, stageName, suggestedCut, waitingLots, type Lot, type Plan, type Session } from './model'
import { ReasonDialog } from './ReasonDialog'
import { changeSession, usePlannerSession } from './session'
import './planner.css'

export const cutPath = cuttingForms['cutting-roll'].path
export const pickupPath = cuttingForms['mandor-wip'].path
export function routesLabel(row: Plan) {
  return row.product.routes.map(r => r.material).join(' / ')
}
export function productionReason(row: Plan) {
  const p=row.product
  const stages=['cut','sewing','laundry','qc'].flatMap(stage=>{
    const qty=row.lots.filter(l=>l.stage===stage && l.kind!=='elsewhere' && l.eta && l.eta<=p.due).reduce((sum,l)=>sum+l.qty,0)
    const where:Record<string,string>={cut:'di meja potong',sewing:'sedang dijahit',laundry:'di laundry',qc:'di QC'}
    return qty?[qty+' pcs '+where[stage]]:[]
  })
  if (row.short) return 'Pesanan '+p.need+' pcs. Ada '+p.fg+' pcs siap jual'+(stages.length?', '+stages.join(' dan '):'')+'. Masih kurang '+row.short+' pcs.'
  if (row.check) return 'Tanyakan ke '+row.check.place+' apakah '+row.check.qty+' pcs ini untuk '+p.brand+' '+p.sku+'.'+(row.late?' Ada '+row.late+' pcs lain yang baru siap sesudah tenggat.':'')
  if (row.queue.length) return (p.fg?p.fg+' pcs sudah siap jual. ':'')+stages.join(' dan ')+'. Serahkan potongan yang ada ke mandor.'
  return (p.fg?p.fg+' pcs siap jual, ':'')+stages.join(' dan ')+'. Cukup untuk pesanan '+p.need+' pcs.'
}
export function SourceDetail({ row }: {row: Plan}) {
  const p = row.product
  const session=usePlannerSession()
  return <div className="gar-detail">
    <p className="gar-lead"><strong>{p.customer}</strong> memesan <strong>{p.need} pcs</strong> untuk {day(p.due)}. Permintaan ini untuk ukuran <strong>{p.size}</strong> di {seriesLabel(seriesFor(p))}.</p>
    <dl className="gar-counts">{[['Pesanan',p.need],['Stok siap jual',p.fg],['WIP tujuan pasti',row.confirmed],['WIP potensial',row.potential],['Sisa perlu potong',row.short]].map(([label,value])=><div key={label}><dt>{label}</dt><dd>{value} <small>pcs</small></dd></div>)}</dl>
    <p>{row.base > row.short ? <>Kalau hanya mengandalkan stok dan WIP yang pasti, masih kurang <strong>{row.base} pcs</strong>. Setelah memakai WIP potensial yang cocok, sisanya <strong>{row.short} pcs</strong>.</> : productionReason(row)}</p>
    <h3>Barangnya ada di mana?</h3>
    <ul className="gar-lots">{row.lots.map(lot=><li key={lot.id}><div><strong>{stageName[lot.stage]} · {lot.qty} pcs</strong><small>{lot.id}{lot.group?' / '+lot.group:''} · {lot.place}{lot.roll ? ' · roll ' + lot.roll : ''}</small></div><div>{lotPattern(lot).name} · {lot.material}<small>Uk. {lot.size} · {lot.kind === 'directed' ? 'Tujuan pasti' : lot.kind==='elsewhere'?'Untuk pesanan lain':'Tujuan perlu dipastikan'}</small></div><div className={lot.eta && lot.eta>p.due?'gar-late':''}>Siap {day(lot.eta)}<small>{lot.kind==='elsewhere'?'Di luar kebutuhan SKU ini':!lot.eta?'Tanggal belum diketahui':lot.eta>p.due?'Lewat tenggat':'Masuk hitungan tenggat'}</small></div></li>)}</ul>
    {row.review.length>0&&<><h3>Potongan yang perlu dipastikan</h3>{row.review.map(l=><p key={l.id}>{l.id} · {stageName[l.stage]} · {remainingPieces(l,p,session)} pcs cocok untuk ukuran {p.size} · {lotLabel(l)}. Tujuan dan tanggal siap perlu diperiksa sebelum mengurangi kebutuhan.</p>)}</>}
    {row.late>0&&<p className="gar-warn">{row.late} pcs tiba sesudah pesanan harus siap. Jumlah itu dikeluarkan dari hitungan di atas.</p>}
    <details><summary>Pesanan, pola dan bahan</summary><p>{p.order} · {p.brand} {p.sku} · rentang jual {p.range} · ukuran fisik {p.size} · {p.colour} · {p.finish}.</p><ul>{p.routes.map(r=><li key={r.material}>{row.reference?patternFor(row.reference).name:'Pola belum ditentukan'} · {row.reference?patternFor(row.reference).revision:''} · {r.material}</li>)}</ul></details>
  </div>
}
export function Forms({row}: {row:Plan}) {
  return <div className="gar-actions">
    {row.review.map(l=><a key={l.id} className="gar-button" href={l.stage==='cut'?pickupPath+'?pot='+l.id:productionForms['sewing-wip'].path+'?lot='+l.id}>Periksa {l.id}</a>)}
    {row.short>0&&row.reference&&!row.review.length&&<a className="gar-button primary" href={cutPath+'?sku='+row.product.sku}>Buka Buat Potongan <ArrowRight size={15}/></a>}
    {row.check&&<a className="gar-button" href={productionForms['sewing-wip'].path+'?lot='+row.check.id}>Cek jahitan {row.check.place} <ArrowRight size={15}/></a>}
    {!row.queue.length&&!row.check&&row.lots.some(l=>l.stage==='laundry')&&<a className="gar-button" href={productionForms.laundry.path+'?sku='+row.product.sku}>Lihat laundry SKU ini <ArrowRight size={15}/></a>}
    {row.queue.length>0&&<a className="gar-button" href={pickupPath+'?pot='+row.queue[0].id}>Buka Bagi Potongan <ArrowRight size={15}/></a>}
  </div>
}
export function DestinationChoice({lot}:{lot:Lot}) {
  const [sku,setSku]=useState(lot.sku??'')
  const [eta,setEta]=useState(lot.eta??'')
  const [message,setMessage]=useState('')
  const session=usePlannerSession()
  const destinations=session.destinations?.filter(d=>d.id===lot.id)??[]
  const assigned=destinations.map(d=>d.sku+' · '+(d.sources?.reduce((n,s)=>n+s.qty,0)??'')+' pcs').join(', ')
  const options=possibleTargets(lot,session).filter(p=>(!lot.sku||p.sku===lot.sku)&&remainingPieces(lot,p,session)>0)
  if(!options.length)return <p>{assigned?'Tujuan tersimpan · '+assigned:'Tujuan belum ditentukan. Potongan tetap bisa dibagi.'}</p>
  return <details className="gar-destination"><summary>Pastikan tujuan potongan · opsional</summary>
    {assigned&&<p>Tujuan tersimpan · {assigned}</p>}
    <label>Tujuan SKU<select aria-label="Tujuan SKU" value={sku} onChange={e=>setSku(e.target.value)}><option value="">Belum ditentukan</option>{options.map(p=><option key={p.sku} value={p.sku}>{p.brand} {p.sku} · {remainingPieces(lot,p,session)} pcs cocok</option>)}</select></label>
    <label>Perkiraan siap<input type="date" aria-label="Tanggal siap tujuan" value={eta} onChange={e=>setEta(e.target.value)}/></label>
    <button type="button" className="gar-button" disabled={!sku||!eta} onClick={()=>{try{changeSession(s=>setDestination(s,lot.id,sku,eta))}catch(e){setMessage((e as Error).message)}}}>Simpan tujuan</button>{message&&<p role="alert">{message}</p>}
  </details>
}
export function AdviceBox({mode,session,onCut,onPickup,selected}:{mode:'cut'|'pickup';session:Session;onCut?:(row:Plan,material?:string)=>void;onPickup?:(lot:Lot)=>void;selected?:string}) {
  const [opened,setOpened]=useState('')
  const [material,setMaterial]=useState<Record<string,string>>(()=>{
    const q=new URLSearchParams(window.location.search),sku=q.get('sku'),fabric=q.get('bahan')
    return sku&&fabric?{[sku]:fabric}:{}
  })
  const plans=plansIn(session)
  const entries:{id:string;row?:Plan;lot?:Lot}[]=mode==='cut'
    ?plans.filter(r=>r.short>0).map(row=>({id:row.product.sku,row}))
    :waitingLots(session).map(lot=>({id:lot.id,lot,row:plans.find(r=>r.product.sku===lot.sku)}))
  const detail=entries.find(entry=>entry.id===opened)
  return <section className="panel gar-panel" aria-label={mode==='cut'?'Saran buat potongan':'Saran bagi potongan'}>
    <details className="planner-disclosure"><summary>{mode==='cut'?'Planner · Saran buat potongan':'Planner · Saran bagi potongan'}</summary>
    <div className="gar-panel-head"><div><p className="gar-kicker">Planner · Selasa 24 Nov 2026</p><h2>{mode==='cut'?'Yang perlu dipotong':'Potongan yang dibagi dulu'}</h2></div><a href="/analisis/planner/">Lihat semua SKU</a></div>
    {!entries.length&&<p className="gar-empty">{mode==='cut'?'Kebutuhan pesanan sudah tertutup.':'Semua potongan sudah diambil mandor.'}</p>}
    {entries.map(({id,row,lot})=>{
      const p=row?.product
      const check=!lot&&row?.review[0]
      const missingRecipe=!lot&&row&&!row.reference
      const suggestion=!lot&&!check&&!missingRecipe&&row?suggestedCut(row,session,material[row.product.sku]):undefined
      return <article className="gar-advice" key={id}><div className="gar-advice-line"><div>
        <h3>{lot?lot.id+' · '+lotLabel(lot):p?.brand+' '+p?.sku}</h3>
        <p>{lot?lotPattern(lot).name:row?.reference?patternFor(row.reference).name:'Pola belum ditentukan'} · {seriesLabel(lot?lotSeries(lot):seriesFor(p!))}</p>
        <small>{lot?.material??routesLabel(row!)} · {lot?.qty??row?.short} pcs{p?' · '+day(p.due):''}</small>
        {suggestion&&p&&p.routes.length>1&&<label className="gar-material">Bahan<select aria-label={'Pilih bahan untuk '+p.sku} value={suggestion.roll.material} onChange={e=>setMaterial({...material,[p.sku]:e.target.value})}>{p.routes.map(route=><option key={route.material}>{route.material}</option>)}</select></label>}
      </div><div className="gar-actions"><button type="button" className="gar-button" aria-haspopup="dialog" onClick={()=>setOpened(id)}>Lihat alasan</button>
        {missingRecipe?<a className="gar-button primary" href="/master/produk-sku/">Pilih pola rencana</a>:check?<a className="gar-button primary" href={check.stage==='cut'?pickupPath+'?pot='+check.id:productionForms['sewing-wip'].path+'?lot='+check.id}>Periksa {check.id}</a>:<button type="button" className="gar-button primary" disabled={Boolean(suggestion&&!suggestion.qty)} onClick={()=>lot?onPickup?.(lot):onCut?.(row!,suggestion?.roll.material)}>{lot?(selected===id?'Lihat pembagian '+id:'Pilih '+id):suggestion?.qty?'Isi form · '+suggestion.qty+' pcs':'Siapkan bahan'} <ArrowRight size={15}/></button>}
      </div></div></article>
    })}
    {detail&&<ReasonDialog title={'Alasan · '+detail.id} onClose={()=>setOpened('')}>
      {detail.lot&&<><p><strong>{lotLabel(detail.lot)}</strong> · {seriesLabel(lotSeries(detail.lot!))} · {detail.lot.qty} pcs</p>
        {cutRolls(detail.lot).map(r=><p key={r.id}>Roll {r.id} · {r.material} · {r.slots.filter(s=>s.qty).map(s=>s.size+s.image+' = '+s.qty+' pcs').join(' · ')}</p>)}</>}
      {detail.row?<SourceDetail row={detail.row}/>:<p>Tujuan SKU belum pasti. Potongan tersedia di meja potong dan bisa dibagi ke mandor.{detail.lot&&possibleTargets(detail.lot,session).filter(p=>remainingPieces(detail.lot!,p,session)>0).map(p=>' '+p.brand+' '+p.sku+' cocok untuk '+remainingPieces(detail.lot!,p,session)+' pcs.').join('')}</p>}
    </ReasonDialog>}
    {mode==='cut'&&<a className="gar-next" href={pickupPath}>Lihat potongan yang siap dibagi <ArrowRight size={15}/></a>}
    </details>
  </section>
}
export function ActionTable({rows,onDetail}:{rows:Plan[];onDetail:(sku:string)=>void}) {
  const [from,setFrom]=useState(''),[until,setUntil]=useState(''),[order,setOrder]=useState('')
  const visible=rows.filter(r=>(!from||r.product.due>=from)&&(!until||r.product.due<=until))
  if(order==='due')visible.sort((a,b)=>a.product.due.localeCompare(b.product.due))
  if(order==='short')visible.sort((a,b)=>b.short-a.short)
  if(order==='sku')visible.sort((a,b)=>a.product.sku.localeCompare(b.product.sku,'id',{numeric:true}))
  return <><details className="erp-table-tools"><summary>Filter dan urutkan pesanan</summary><div><label>Tenggat mulai<input type="date" max={until||undefined} value={from} onChange={e=>setFrom(e.target.value)}/></label><label>Tenggat sampai<input type="date" min={from||undefined} value={until} onChange={e=>setUntil(e.target.value)}/></label><label>Urutan pesanan<select value={order} onChange={e=>setOrder(e.target.value)}><option value="">Urutan Planner</option><option value="due">Tenggat terdekat</option><option value="short">Kekurangan terbesar</option><option value="sku">Nomor SKU</option></select></label><button type="button" disabled={!from&&!until&&!order} onClick={()=>{setFrom('');setUntil('');setOrder('')}}>Reset</button></div></details>{!visible.length&&<p role="status">Tidak ada pesanan pada rentang ini.</p>}<div className="gar-list">{visible.map(row=><article key={row.product.sku} className="gar-plan" data-sku={row.product.sku}>
    <div><h3>{row.product.brand} {row.product.sku} <span>· {seriesLabel(seriesFor(row.product))}</span></h3><p>{row.reference?patternFor(row.reference).name:'Pola belum ditentukan'} · {routesLabel(row)}</p><small>{row.product.customer} · {row.product.need} pcs · {day(row.product.due)}</small></div>
    <div><strong>{action(row)}</strong></div><button type="button" className="gar-button" aria-haspopup="dialog" onClick={()=>onDetail(row.product.sku)}>Lihat alasan</button>
  </article>)}</div></>
}

import {useState} from 'react'
import {browseMatchPieces} from '../browseMatch'
import {allPayrollSources,fgSourcePieces,readPayDrafts} from './payrollSources'
import {amountText,fixtureDate} from './accessoryPricing'
import {matchesPeriod,PeriodFilter,periodFor} from './PeriodFilter'

export default function FgRegister({payroll}:{payroll:boolean}){
  const [query,setQuery]=useState(''),[order,setOrder]=useState('new'),[period,setPeriod]=useState(()=>periodFor('all',fixtureDate))
  const payrolls=readPayDrafts(),sources=allPayrollSources().filter(s=>s.kind==='FG')
  const notes=sources.filter(s=>matchesPeriod(s.day,period)&&browseMatchPieces(query,fgSourcePieces(s.doc),s.doc.number,s.mandor,s.doc.sku,s.doc.source)).sort((a,b)=>(order==='new'?-1:1)*(a.day.localeCompare(b.day)||a.doc.number.localeCompare(b.doc.number)))
  return <details className="panel wh-posted-list"><summary>Nota FG yang sudah disusun · {sources.length} nota</summary><div className="wh-fields"><label>Cari nota, mandor atau SKU<input value={query} onChange={e=>setQuery(e.target.value)}/></label><label>Urutan nota<select value={order} onChange={e=>setOrder(e.target.value)}><option value="new">Terbaru dulu</option><option value="old">Terlama dulu</option></select></label></div><PeriodFilter label="Tanggal nota FG" value={period} onChange={setPeriod}/>
    {notes.map(s=>{const pay=payrolls.find(p=>p.status!=='REVERSED'&&p.fgNotes.some(d=>d.number===s.doc.number))
    return <div className="wh-register-row" key={s.doc.number}><span><strong>{s.doc.number} · {s.mandor}</strong><small>{s.day} · {s.doc.sku} · {pay?.status==='PAID'?'Sudah dibayar':pay?'Dalam payroll':'Siap dipilih untuk payroll'}</small></span><strong>{amountText(s.doc.labor+s.doc.reimbursement)}</strong><a className="soft-btn" aria-label={'Buka detail '+s.doc.number} href={'/produksi/susun-nota-fg/?nota='+encodeURIComponent(s.doc.number)+(payroll?'&dari=payroll':'')}>Buka detail</a></div>})}{!notes.length&&<p>Tidak ada nota yang cocok.</p>}</details>
}

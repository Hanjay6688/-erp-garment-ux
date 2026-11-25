import { ArrowRight, CalendarDays, ClipboardList, Layers3, ReceiptText, Scissors, UsersRound } from 'lucide-react'
import { useState } from 'react'
import { WorkspaceFigures } from '../components/WorkspaceFigures'
import { amountText } from './accessoryPricing'
import { attendancePeriods, attendanceSourcePath, pocketCostPath } from './periodCostSources'
import { pocketAllocationPath, pocketIssuePath } from './receiptRollCorrection'
import { pocketRolls } from './pocketReceipts'
import { pocketIssueCost, pocketPriceDifference, readPocketBook } from './pocketUsage'
import '../period-costs.css'

export type PeriodArea = 'kantong' | 'absensi'
const pcs = (n:number) => n.toLocaleString('id-ID') + ' pcs'
const periodDate = (day:string) => new Intl.DateTimeFormat('id-ID',{day:'numeric',month:'short',year:'numeric',timeZone:'UTC'}).format(new Date(day+'T00:00:00Z'))
const period = (start:string,end:string) => periodDate(start) + ' – ' + periodDate(end)

export default function PeriodCostPanel({ area }: {area:PeriodArea}) {
  return area === 'kantong' ? <PocketPeriods/> : <AttendancePeriods/>
}

function UnitCost({amount, quantity}:{amount:number;quantity:number}) {
  if (quantity <= 0) return null
  return <div className="period-unit-cost"><span>Biaya per potong</span><strong>{amountText(amount / quantity)} <small>/ pcs</small></strong></div>
}

function PocketPeriods() {
  const book = readPocketBook()
  const rolls = new Map(pocketRolls().map(roll=>[roll.id,roll]))
  const issues = new Map(book.issues.map(row=>[row.id,row]))
  const active = book.allocations.filter(row=>!row.reversal)
  const allocatedIssues = new Set(active.flatMap(row=>row.sources))
  const waiting = book.issues.filter(row=>!row.reversal && !allocatedIssues.has(row.id))
  const pendingValue = waiting.reduce((sum,i)=>sum+pocketIssueCost(i,rolls.get(i.roll)),0)
  const total = active.reduce((sum,a)=>sum+a.cents,0)
  const [showAllIssues, setShowAllIssues] = useState(false)
  return <section className="period-workspace" data-area="kantong" aria-label="HPP kain kantong">
    <header className="period-title"><i><Layers3/></i><div><h2>Kain kantong</h2><p>Pemakaian roll dibagi ke hasil jahit dalam periode yang sama, termasuk hasil Afui.</p></div>
      <a className="period-action" href={pocketCostPath}>Bagi biaya kain kantong <ArrowRight/></a></header>
    <WorkspaceFigures label="Biaya kain kantong" figures={[
      {label:'Belum dibagi',value:amountText(pendingValue/100),icon:ReceiptText,tone:'amber'},
      {label:'Sudah dibagi ke HPP',value:amountText(total/100),icon:Layers3,tone:'green'},
      {label:'Hasil jahit penerima',value:pcs(active.reduce((sum,a)=>sum+a.pcs,0)),icon:Scissors,tone:'blue'},
    ]}/>
    <div className="period-list"><header><ClipboardList/><h3>Pembagian per periode</h3></header>
      {book.allocations.length === 0 && <p className="period-empty">Belum ada pembagian. {waiting.length ? 'Pilih periode untuk melihat biaya per potong sebelum disahkan.' : 'Mulai dari roll yang dipakai, lalu bagi biayanya ke hasil jahit.'}
        {!waiting.length && <a className="period-source-link" href="/gudang/kain-kantong/">Catat pemakaian roll <ArrowRight/></a>}</p>}
      {[...book.allocations].reverse().map(row=>{
        const difference = row.reversal ? 0 : pocketPriceDifference(row, issues, rolls)
        return <article key={row.id} className="period-record">
        <div><small>{period(row.start,row.end)}</small><h4>{amountText(row.cents/100)} <span>· {pcs(row.pcs)}</span></h4><p>{row.id} · {row.reason}</p></div>
        <span className="period-status" data-state={row.reversal?'muted':'active'}>{row.reversal?'Dibatalkan':'Disahkan'}</span>
        <UnitCost amount={row.cents / 100} quantity={row.pcs}/>
        {difference !== 0 && <p className="period-destination period-reprice">Selisih harga final <strong>{amountText(difference / 100)}</strong>. Buka pembagian untuk membalik dan menghitung ulang.</p>}
        <details><summary>Rincian {row.parts.length} PO</summary><div className="period-parts">{row.parts.map(part=><div key={part.po}>
          <strong>{part.mandor} · {pcs(part.pcs)}</strong><small>{part.po}</small>
          <dl><div><dt>WIP</dt><dd>{amountText(part.wip/100)}</dd></div><div><dt>FG tersedia</dt><dd>{amountText(part.fg/100)}</dd></div><div><dt>Terjual</dt><dd>{amountText(part.sold/100)}</dd></div></dl>
        </div>)}</div></details>
        <a className="period-source-link" href={pocketAllocationPath(row.id)}>Buka pembagian <ArrowRight/></a>
      </article>})}
    </div>
    {waiting.length>0 && <div className="period-list"><header><Scissors/><h3>Pemakaian yang belum dibagi</h3></header>
      {(showAllIssues?waiting:waiting.slice(-5)).slice().reverse().map(i=><article key={i.id} className="period-record"><div>
        <strong>{amountText(pocketIssueCost(i,rolls.get(i.roll))/100)}</strong><small>{i.roll} · {periodDate(i.date)}</small></div>
        <a className="period-source-link" href={pocketIssuePath(i.id)}>Buka pemakaian <ArrowRight/></a></article>)}
      {waiting.length>5 && <button className="period-source-link" onClick={()=>setShowAllIssues(!showAllIssues)}>{showAllIssues?'Ringkas daftar':'Lihat semua '+waiting.length+' pemakaian'}</button>}
    </div>}
  </section>
}

function AttendancePeriods() {
  const rows = attendancePeriods()
  const held = rows.reduce((n,r)=>n+(r.decision?.choice==='CARRY'&&!r.decision.allocated?r.decision.cost:0),0)
  const allocated = rows.reduce((n,r)=>n+(r.decision?.allocated?r.decision.cost:0),0)
  const expensed = rows.reduce((n,r)=>n+(r.decision?.choice==='EXPENSE'?r.decision.cost:0),0)
  return <section className="period-workspace" data-area="absensi" aria-label="HPP absensi">
    <header className="period-title"><i><UsersRound/></i><div><h2>Biaya absensi</h2><p>Telusuri upah per mandor dari periode asal sampai keputusan pembagian biayanya.</p></div>
      <a className="period-action" href="/keuangan/absensi/">Buka absensi pekerja <ArrowRight/></a></header>
    <WorkspaceFigures label="Keputusan biaya absensi" figures={[
      {label:'Dibawa ke periode berikut',value:amountText(held),icon:CalendarDays,tone:'amber'},
      {label:'Dialokasikan ke hasil jahit',value:amountText(allocated),icon:Scissors,tone:'green'},
      {label:'Beban periode',value:amountText(expensed),icon:ReceiptText,tone:'blue'},
    ]}/>
    <div className="period-list"><header><ClipboardList/><h3>Periode absensi terposting</h3></header>
      {!rows.length && <p className="period-empty">Belum ada absensi terposting. Catat kehadiran dan posting periodenya di Absensi Pekerja.</p>}
      {rows.map(row=>{
        const decision=row.decision
        const status=decision?.allocated?'Dialokasikan':decision?.choice==='CARRY'?'Menunggu hasil jahit':decision?.choice==='EXPENSE'?'Beban periode':'Belum dialokasikan'
        return <article className="period-record" key={row.key}>
          <div><small>{row.mandor} · {period(row.start,row.end)}</small><h4>{amountText(row.cost)}</h4>
          {decision&&<p>{decision.reason}</p>}</div>
          <span className="period-status" data-state={decision?.allocated?'active':decision?.choice==='EXPENSE'?'muted':'waiting'}>{status}</span>
          {decision?.allocated&&<><UnitCost amount={decision.cost} quantity={decision.allocated.qty}/><p className="period-destination"><Scissors/>Hasil jahit {period(decision.allocated.start,decision.allocated.end)} · <strong>{pcs(decision.allocated.qty)}</strong> · {decision.allocated.reason}</p></>}
          <a className="period-source-link" href={attendanceSourcePath(row.id,row.start,row.end)}>Buka periode {row.mandor} <ArrowRight/></a>
        </article>
      })}
    </div>
  </section>
}

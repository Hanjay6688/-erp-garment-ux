import {History,ArrowRight} from 'lucide-react'
import {returnId,total,type Batch,type Distribution} from './planner/distribution'
import './wipDistribution.css'

export const pickupUrl=(group:string,no:number)=>'/produksi/bagi-potongan/?pot='+encodeURIComponent(returnId(group,no))
export function BatchTrace({row,group}:{row:Batch;group:Distribution}){
  const pending=group.returns.find(r=>r.no===row.no)
  const children=group.batches.filter(b=>b.previous===row.no)
  return <div className="sewing-trace">
    {row.previous&&<small>Asal Batch {row.previous} · {row.mandor}</small>}
    {children.length>0&&<small>Terbagi ke {children.map(b=>'Batch '+b.no+' ('+b.qty+' pcs)').join(' dan ')}</small>}
    {pending&&<a className="dist-link" href={pickupUrl(group.id,row.no)}>Bagi ulang {total(pending.sources)} pcs <ArrowRight/></a>}
    {!!row.sources.length&&<details><summary>Ukuran &amp; asal</summary>
      <ul>{row.sources.map(r=><li key={JSON.stringify([r.rollId,r.slot,r.size])}>{r.rollId} · slot gambar {r.slot} · ukuran {r.size} · {r.qty} pcs</li>)}</ul></details>}
  </div>
}
const actionName={Reverse:'Pembatalan',Adjust:'Koreksi',Koreksi:'Koreksi',Proses:'Proses', 'Bagi ulang':'Bagi ulang'}
export function SewingHistory({ledger}:{ledger:Distribution}){
  if(!ledger.events.length)return null
  return <details className="dist-history"><summary><History/> Riwayat distribusi ({ledger.events.length})</summary><ol>
    {ledger.events.map(e=><li key={e.id}><strong>{e.proof??actionName[e.kind]} · Batch {e.no}</strong><span>{e.physical.replace('T',' ')} WIB{e.reason?' · '+e.reason:''}</span>
      {e.released.length>0&&<span>Kembali ke Bagi Potongan · {total(e.released)} pcs</span>}
      {e.created.length>0&&<span>{e.created.map(b=>'Batch '+b.no+' · '+b.qty+' pcs').join(' / ')}</span>}
      {e.updates?.map(u=><span key={u.no}>Batch {u.no} · {Object.keys(u.sizes).map(s=>'uk. '+s+' '+(u.before[s]??0)+' → '+u.sizes[s]).join(' · ')}</span>)}
    </li>)}</ol></details>
}

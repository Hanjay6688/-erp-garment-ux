import {browseMatch} from '../browseMatch'
import {allSkus} from './skuCatalog'
import {cutRolls,lotLabel,lotsIn,rolls} from './planner/model'
import {usePlannerSession} from './planner/session'
import {sewingBatchId} from './sewingReceipts'
import {distribution,pickupsIn} from './planner/distribution'
import type {LaundryDelivery,LaundryReadyBatch} from './laundryModel'
import {pocketRolls} from './pocketReceipts'
type Hit={type:string;id:string;description:string;href:string;terms:(string|number|undefined)[]}
export function RecordFinder({query,ready,deliveries}:{query:string;ready:LaundryReadyBatch[];deliveries:LaundryDelivery[]}){
  const session=usePlannerSession()
  if(!query.trim())return null
  const q=encodeURIComponent
  const hits:Hit[]=[
    ...lotsIn(session).filter(l=>l.stage==='cut').map(l=>({type:'Bagi potongan',id:l.id,description:lotLabel(l),href:'/produksi/bagi-potongan/?pot='+q(l.id),terms:[l.material,l.size,...cutRolls(l).map(r=>r.id)]})),
    ...pickupsIn(session).map(p=>({type:'WIP jahit',id:p.id,description:p.mandor,href:'/produksi/jahit/?cari='+q(p.id),terms:distribution(p,session).batches.flatMap(b=>[sewingBatchId(p.id,b.no),b.mandor,'Batch '+b.no,...b.sources.map(r=>r.rollId)])})),
    ...rolls.map(r=>({type:'Roll potong',id:r.id,description:r.material,href:'/produksi/buat-potongan/?cari='+q(r.id),terms:[r.supplier]})),
    ...ready.map(b=>({type:'Laundry · siap kirim',id:b.id,description:b.parentId+' · '+b.vendor,href:'/produksi/laundry/?cari='+q(b.id),terms:[b.skuRef,b.model,b.material,b.mandor,...b.sizeLabels]})),
    ...deliveries.map(d=>({type:'Surat laundry',id:d.id,description:d.parentId+' · '+d.vendor,href:'/produksi/laundry/?tab=kembali&cari='+q(d.id),terms:[d.batchId,d.skuRef,d.model,d.material,d.mandor,...d.sizeLabels]})),
    ...allSkus(session,true).map(a=>({type:'Barang jadi',id:a.key,description:a.model+' · '+a.colour,href:'/gudang/barang-jadi/?cari='+q(a.key),terms:a.sizes})),
    ...pocketRolls().map(r=>({type:'Roll kain kantong',id:r.id,description:r.name,href:'/gudang/kain-kantong/?roll='+q(r.id),terms:[r.receipt,r.location]})),
  ].filter(hit=>browseMatch(query,hit.id,hit.description,hit.type,...hit.terms))
  return <section className="finder-records" aria-label="Hasil pencarian dokumen"><h3>Dokumen dan barang ({hits.length})</h3>{hits.length===0?<p>Dokumen atau nomor barang belum ditemukan.</p>:<div>{hits.map(hit=><a key={hit.type+'#'+hit.id} href={hit.href}><strong>{hit.id}</strong><span>{hit.type} · {hit.description}</span></a>)}</div>}</section>
}

import {browseMatchPieces, isPieceUnit} from '../browseMatch'
import {fgProducts, piecesIn} from './fgOverview'
import {allSkus} from './skuCatalog'
import {cutRolls,lotLabel,lotsIn,rolls} from './planner/model'
import {usePlannerSession} from './planner/session'
import {sewingBatchId} from './sewingReceipts'
import {distribution,pickupsIn} from './planner/distribution'
import {laundryOutstanding,type LaundryDelivery,type LaundryReadyBatch} from './laundryModel'
import {pocketRolls, readReceipts, receiptPath} from './pocketReceipts'
import {readInvoices} from './saleBook'
import {readNotes} from './issueDocuments'
import {allPayrollSources, fgSourcePieces} from './payrollSources'
import {fgDrafts} from './fgDraft'
type Hit={type:string;id:string;description:string;href:string;terms:(string|number|undefined)[];pieces?:number[]}
export function RecordFinder({query,ready,deliveries}:{query:string;ready:LaundryReadyBatch[];deliveries:LaundryDelivery[]}){
  const session=usePlannerSession()
  if(!query.trim())return null
  const q=encodeURIComponent
  const receiptHits: Hit[] = readReceipts().map(r => ({
    type: 'Penerimaan kain kantong', id: r.number, description: r.supplier,
    href: receiptPath + '&surat=' + q(r.number), terms: r.rolls.map(roll => roll.id),
  }))
  const stockBySku = new Map<string, number[]>()
  for (const product of fgProducts(session)) {
    const key = product.brand + ' ' + product.code
    const quantities = stockBySku.get(key) ?? []
    quantities.push(piecesIn(product))
    stockBySku.set(key, quantities)
  }
  const hits:Hit[]=[
    ...readInvoices().map(r => ({ type: 'Invoice penjualan', id: r.number, description: r.customer,
      href: '/penjualan/semua-invoice/?nota=' + q(r.number), terms: [r.sku], pieces: [r.qty] })),
    ...readNotes().map(r => ({ type: 'Nota Ambil Aksesori', id: r.number, description: r.mandor,
      href: '/keuangan/nota-ambil-mandor/?nota=' + q(r.number), terms: r.lines.map(line => line.item),
      pieces: r.lines.filter(line => isPieceUnit(line.unit)).map(line => line.qty) })),
    ...allPayrollSources().flatMap(r => r.kind === 'FG' ? [{ type: 'Nota FG', id: r.doc.number, description: r.mandor,
      href: '/produksi/susun-nota-fg/?nota=' + q(r.doc.number), terms: [r.doc.sku], pieces: fgSourcePieces(r.doc) }] : []),
    ...fgDrafts().map(r => ({ type: 'Draft Nota FG', id: r.number, description: r.mandor,
      href: '/produksi/susun-nota-fg/?draft=' + q(r.number), terms: [] })),
    { type: 'Penerimaan kain kantong', id: 'SJ-KT-001', description: 'Saldo pembukaan',
      href: receiptPath + '&surat=SJ-KT-001', terms: [] },
    ...receiptHits,
    ...lotsIn(session).filter(l=>l.stage==='cut').map(l=>({type:'Bagi potongan',id:l.id,description:lotLabel(l),href:'/produksi/bagi-potongan/?pot='+q(l.id),terms:[l.material,l.size,...cutRolls(l).map(r=>r.id)],pieces:[l.qty]})),
    ...pickupsIn(session).map(p => {
      const batches = distribution(p, session).batches
      const active = batches.filter(batch => !batch.closed)
      return { type:'WIP jahit', id:p.id, description:p.mandor, href:'/produksi/jahit/?cari='+q(p.id),
        terms:batches.flatMap(b => [sewingBatchId(p.id,b.no),b.mandor,'Batch '+b.no,...b.sources.map(r=>r.rollId)]),
        pieces:[active.reduce((qty, batch) => qty + batch.qty, 0), ...active.flatMap(batch => [batch.qty, batch.sewn])] }
    }),
    ...rolls.map(r=>({type:'Roll potong',id:r.id,description:r.material,href:'/produksi/buat-potongan/?cari='+q(r.id),terms:[r.supplier]})),
    ...ready.map(b=>({type:'Laundry · siap kirim',id:b.id,description:b.parentId+' · '+b.vendor,href:'/produksi/laundry/?cari='+q(b.id),terms:[b.skuRef,b.model,b.material,b.mandor,...b.sizeLabels],pieces:[b.qty]})),
    ...deliveries.map(d=>({type:'Surat laundry',id:d.id,description:d.parentId+' · '+d.vendor,href:'/produksi/laundry/?tab=kembali&cari='+q(d.id),terms:[d.batchId,d.skuRef,d.model,d.material,d.mandor,...d.sizeLabels],pieces:[d.qty,d.good+d.bs,laundryOutstanding(d)]})),
    ...allSkus(session,true).map(a=>({type:'Barang jadi',id:a.key,description:a.model+' · '+a.colour,href:'/gudang/barang-jadi/?cari='+q(a.key),terms:a.sizes,pieces:stockBySku.get(a.key)})),
    ...pocketRolls().map(r=>({type:'Roll kain kantong',id:r.id,description:r.name,href:'/gudang/kain-kantong/?roll='+q(r.id),terms:[r.receipt,r.location]})),
  ]
  const found = hits.filter(hit=>browseMatchPieces(query,hit.pieces??[],hit.id,hit.description,hit.type,...hit.terms))
  return <section className="finder-records" aria-label="Hasil pencarian dokumen"><h3>Dokumen dan barang ({found.length})</h3>{found.length===0?<p>Dokumen atau nomor barang belum ditemukan.</p>:<div>{found.map(hit=><a key={hit.type+'#'+hit.id} href={hit.href}><strong>{hit.id}</strong><span>{hit.type} · {hit.description}</span></a>)}</div>}</section>
}

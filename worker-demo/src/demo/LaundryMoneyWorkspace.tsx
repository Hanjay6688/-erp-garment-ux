import { ArrowRight, FilePlus2, ReceiptText, ShieldCheck, WalletCards, Waves } from 'lucide-react'
import { LaundryClaims } from './LaundryCreditActions'
import { claimMoney, type UpdateLaundry } from './LaundryClaimCreditDialog'
import { availableCredits, billGross } from './laundryCredits'
import { laundryOutstanding, type LaundryDelivery } from './laundryModel'
import { invoiceForLaundryContract, laundryDocuments, laundryPayablesPath, reverseLaundryContract } from './laundryVendorInvoices'
import { StockSourceReversal } from './StockSourceReversal'

export function LaundryMoneyWorkspace({visible,deliveries,update,unbilled,openContract}: {
  visible:LaundryDelivery[]; deliveries:LaundryDelivery[]; update:UpdateLaundry
  unbilled:(delivery:LaundryDelivery)=>number; openContract:(vendor:string)=>void
}) {
  const vendors=[...new Set(visible.map(row=>row.vendor))]
  return <section className="laundry-money-workspace" aria-label="Klaim dan tagihan laundry">
    <header className="demo-operation-heading laundry-money-title"><i><WalletCards aria-hidden="true"/></i>
      <div><h2>Klaim &amp; Kontrabon Laundry</h2><p>Susun penerimaan ke kontrabon. Lanjutkan ke Hutang saat invoice datang atau kredit siap dipakai.</p></div>
    </header>
    {!vendors.length&&<div className="laundry-empty"><ReceiptText/><strong>Surat kirim atau kontrabon tidak ditemukan</strong><small>Coba cari nama laundry, batch, nomor kontrabon, atau jumlah pcs.</small></div>}
    {vendors.map(vendor=>{
      const rows=visible.filter(row=>row.vendor===vendor)
      const credits=availableCredits(deliveries,vendor).reduce((sum,row)=>sum+row.remaining,0)
      const ids=new Set(rows.map(row=>row.id))
      const contracts=laundryDocuments(deliveries).filter(({delivery,bill})=>bill.kind==='CONTRABON'&&delivery.vendor===vendor
        &&(ids.has(delivery.id)||bill.parts?.some(part=>ids.has(part.delivery))))
        .map(({delivery,bill})=>{
          const ref={delivery:delivery.id,number:bill.number}
          return {delivery,bill,ref,invoice:invoiceForLaundryContract(deliveries,ref)}
        })
      const unbilledRows=rows.filter(row=>unbilled(row)>0)
      return <section className="laundry-money-vendor" aria-label={'Klaim dan tagihan '+vendor} key={vendor}>
        <header className="laundry-vendor-header">
          <div className="demo-operation-heading"><i><Waves aria-hidden="true"/></i><div><h3>{vendor}</h3></div></div>
          <dl className="laundry-money-totals">
            <div className={credits>0?'has-credit':undefined}><dt>Kredit siap dipakai</dt><dd>{claimMoney(credits)}</dd></div>
            <div><dt>Kontrabon siap masuk invoice</dt><dd>{contracts.filter(row=>!row.invoice&&!row.bill.reversal).length}</dd></div>
          </dl>
          <a className="soft-btn" href={laundryPayablesPath(vendor)}><WalletCards aria-hidden="true"/> Buka invoice di Hutang <ArrowRight aria-hidden="true"/></a>
        </header>
        <div className="laundry-money-columns">
          <section className="laundry-money-column laundry-money-claims" aria-label={'Klaim '+vendor}>
            <header className="demo-operation-heading"><i><ShieldCheck aria-hidden="true"/></i><div><h4>Klaim &amp; penyelesaian</h4><p>Pilih surat kirim asal barang yang diklaim.</p></div></header>
            {rows.map(delivery=><article className="laundry-money-source" key={delivery.id}>
              <strong>{laundryOutstanding(delivery)} pcs di luar <span>· {delivery.model}</span></strong><small>{delivery.bs} pcs BS diterima · {delivery.id}</small>
              <LaundryClaims delivery={delivery} deliveries={deliveries} update={update}/>
            </article>)}
          </section>
          <section className="laundry-money-column" aria-label={'Kontrabon '+vendor}>
            <header className="demo-operation-heading"><i><ReceiptText aria-hidden="true"/></i><div><h4>Kontrabon</h4><p>Gabungkan satu atau beberapa penerimaan milik laundry ini.</p></div></header>
            {unbilledRows.length>0&&<div className="laundry-money-sources"><header className="demo-ops-header"><strong>Siap ditagih</strong>
              <button className="primary-btn" type="button" onClick={()=>openContract(vendor)}><FilePlus2 aria-hidden="true"/> Buat kontrabon</button></header>
              {unbilledRows.map(delivery=><article className="laundry-money-source" key={delivery.id}>
                <div><strong>{unbilled(delivery)} pcs</strong><span>{delivery.model}</span><small>{delivery.id}</small></div>
              </article>)}
            </div>}
            {contracts.map(({delivery,bill,ref,invoice})=><section className="laundry-money-source laundry-contract-card" aria-label={'Kontrabon '+bill.number} key={delivery.id+'|'+bill.number}>
              <header className="demo-ops-header">
                <div><strong>{bill.qty} pcs</strong><span className="laundry-contract-number">{bill.number}</span><small>{bill.day} · {bill.parts?.length??1} penerimaan</small></div>
                <b>{claimMoney(billGross(bill))}</b>
              </header>
              {bill.parts?.length&&<details className="demo-operation-history"><summary>Lihat penerimaan</summary>
                {bill.parts.map(part=><article key={part.delivery}><strong>{part.qty} pcs</strong><small>{part.process} · {claimMoney(part.rate*100)} / pcs</small>
                  <a className="source-row-link" href={'/produksi/laundry/?'+new URLSearchParams({tab:'kembali',vendor,cari:part.delivery})}>{part.delivery} <ArrowRight aria-hidden="true"/></a>
                </article>)}
              </details>}
              {invoice ? <a className="soft-btn" href={laundryPayablesPath(vendor,invoice.bill.number)}>
                {invoice.bill.status==='DRAFT'?'Draf invoice':'Invoice'} {invoice.bill.number} <ArrowRight aria-hidden="true"/>
              </a> : !bill.reversal&&<small className="laundry-contract-state">Siap masuk invoice</small>}
              <StockSourceReversal label="Balikkan kontrabon" document={bill.number} reversal={bill.reversal}
                blockers={invoice?[{label:'Invoice '+invoice.bill.number,href:laundryPayablesPath(vendor,invoice.bill.number)}]:[]}
                onReverse={reason=>{
                  const next=reverseLaundryContract(deliveries,ref,reason)
                  update(current=>current===deliveries?next:current)
                }}/>
            </section>)}
            {!contracts.length&&<p className="invoice-list-empty">Belum ada kontrabon tercatat.</p>}
          </section>
        </div>
      </section>
    })}
  </section>
}

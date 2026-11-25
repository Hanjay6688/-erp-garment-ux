import { FilePlus2, ReceiptText, ShieldCheck, WalletCards } from 'lucide-react'
import { LaundryBillCard, LaundryClaims } from './LaundryCreditActions'
import { claimMoney, type UpdateLaundry } from './LaundryClaimCreditDialog'
import { availableCredits, billRemaining } from './laundryCredits'
import { laundryOutstanding, type LaundryDelivery } from './laundryModel'

export function LaundryMoneyWorkspace({visible,deliveries,update,openBill,unbilled,openCombined}: {
  visible:LaundryDelivery[]; deliveries:LaundryDelivery[]; update:UpdateLaundry; openBill:(delivery:LaundryDelivery)=>void
  unbilled:(delivery:LaundryDelivery)=>number; openCombined:(vendor:string)=>void
}) {
  const vendors=[...new Set(visible.map(row=>row.vendor))]
  return <section className="laundry-money-workspace" aria-label="Klaim dan tagihan laundry">
    <header className="laundry-section-head"><div><h2>Klaim &amp; Tagihan Laundry</h2><p>Selesaikan klaim di kiri. Pilih kontrabon tujuan dan potong tagihan saat kredit tersedia.</p></div></header>
    {!vendors.length&&<div className="laundry-empty"><ReceiptText/><strong>Surat kirim atau kontrabon tidak ditemukan</strong><small>Coba cari nama laundry, batch, nomor kontrabon, atau jumlah pcs.</small></div>}
    {vendors.map(vendor=>{
      const rows=visible.filter(row=>row.vendor===vendor)
      const credits=availableCredits(deliveries,vendor).reduce((sum,row)=>sum+row.remaining,0)
      const bills=rows.flatMap(delivery=>(delivery.finalBills??[]).map(bill=>({delivery,bill})))
      const outstanding=bills.reduce((sum,{delivery,bill})=>sum+billRemaining(deliveries,delivery,bill),0)
      const unbilledRows=rows.filter(row=>unbilled(row)>0)
      return <section className="laundry-money-vendor" aria-label={'Klaim dan tagihan '+vendor} key={vendor}>
        <header className="demo-ops-header"><div className="demo-operation-heading"><i><WalletCards/></i><div><h3>{vendor}</h3></div></div>
          <div className="laundry-money-totals"><span>Kredit siap dipakai <strong>{claimMoney(credits)}</strong></span><span>Sisa kontrabon <strong>{claimMoney(outstanding)}</strong></span></div></header>
        <div className="demo-ops-columns">
          <section className="laundry-money-column" aria-label={'Klaim '+vendor}>
            <div className="demo-operation-heading"><i><ShieldCheck/></i><div><h3>Klaim &amp; penyelesaian</h3><p>Pilih surat kirim asal barang yang diklaim.</p></div></div>
            {rows.filter(row=>row.claims?.length||row.bs>0||laundryOutstanding(row)>0).map(delivery=><article className="laundry-money-source" key={delivery.id}>
              <strong>{laundryOutstanding(delivery)} pcs di luar · {delivery.model}</strong><small>{delivery.id} · {delivery.bs} pcs BS diterima</small>
              <LaundryClaims delivery={delivery} deliveries={deliveries} update={update}/>
            </article>)}
            {!rows.some(row=>row.claims?.length||row.bs>0||laundryOutstanding(row)>0)&&<small>Belum ada barang yang perlu diklaim.</small>}
          </section>
          <section className="laundry-money-column" aria-label={'Kontrabon '+vendor}>
            <div className="demo-operation-heading"><i><ReceiptText/></i><div><h3>Kontrabon &amp; pembayaran</h3><p>Potong kredit dari kontrabon vendor yang sama.</p></div></div>
            {unbilledRows.length>0&&<div className="laundry-money-sources"><header className="demo-ops-header"><strong>Siap ditagih</strong>
              <button className="primary-btn" type="button" onClick={()=>openCombined(vendor)}><FilePlus2 size={16}/> Susun kontrabon</button></header>
              {unbilledRows.map(delivery=><article className="laundry-money-source" key={delivery.id}>
                <div><strong>{unbilled(delivery)} pcs</strong><small>{delivery.id} · {delivery.model}</small></div>
                <button className="soft-btn" type="button" onClick={()=>openBill(delivery)}>Catat kontrabon</button>
              </article>)}
            </div>}
            {bills.map(({delivery,bill})=><LaundryBillCard key={delivery.id+'|'+bill.number} delivery={delivery} bill={bill} deliveries={deliveries} update={update}/>)}
            {!bills.length&&<small>Kontrabon yang sudah dicatat akan muncul di sini.</small>}
          </section>
        </div>
      </section>
    })}
  </section>
}

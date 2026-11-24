import {useState} from 'react'
import MaterialReorderPanel from './MaterialReorderPanel'

/** OW14a: display the existing authoritative reader, without another formula or write path. */
export default function WarehouseFabricReorderSummary(){
  const [open,setOpen]=useState(false)
  return <section className="panel cwhs-fabric-rule" aria-label="Ringkasan kebutuhan kain">
    <h2>Kebutuhan kain dan pengingat stok</h2>
    <p>Angka stok per gudang di atas adalah fisik yang sudah tercatat. Buka perhitungan untuk melihat kebutuhan kain, pesanan yang belum diterima, dan aturan pengingat yang aktif.</p>
    <details open={open} onToggle={event=>setOpen(event.currentTarget.open)}>
      <summary>Lihat titik pesan ulang kain dari seluruh gudang</summary>
      {open?<MaterialReorderPanel materialType="FABRIC" readOnlySummary/>:null}
    </details>
  </section>
}

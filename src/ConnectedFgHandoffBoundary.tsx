import { AlertTriangle, Calculator, ShieldCheck } from 'lucide-react'
import './connected-laundry-qc.css'

export default function ConnectedFgHandoffBoundary() {
  return <div className="connected-laundry-qc-page">
    <section className="clq-hero"><div><span>CP6 · SAFETY BOUNDARY</span><h1>Susun Nota FG</h1><p>Halaman simulasi tidak dipakai pada UAT connected.</p></div></section>
    <div className="clq-boundary"><ShieldCheck/><span>Final SKU dan stok FG sudah authoritative di halaman QC. Hak kerja/payroll tidak boleh dihitung ulang dari card browser.</span></div>
    <section className="clq-panel"><header><div><span>WRITER DIBLOKIR</span><h2>Formula Nota FG lama belum menjadi kontrak backend</h2><p>Tarif hard-coded dan subtotal React dapat berbeda dari entitlement, HPP, jurnal, dan laporan authoritative.</p></div><Calculator/></header><div className="clq-warning"><AlertTriangle/><span><strong>Tidak ada data yang dihapus atau diposting.</strong> CP6 akan membuka writer ini hanya setelah sumber entitlement, snapshot komponen, idempotency, reversal, dan refetch authoritative terbukti end-to-end.</span></div><div className="clq-empty"><ShieldCheck/><strong>Gunakan QC untuk post Final SKU</strong><small>Nota/payroll connected menyusul sebagai kontrak terpisah; tidak ada fallback ke simulasi.</small></div></section>
  </div>
}

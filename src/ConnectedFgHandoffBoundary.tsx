import { AlertTriangle, Calculator, ShieldCheck } from 'lucide-react'
import './connected-laundry-qc.css'

export default function ConnectedFgHandoffBoundary() {
  return <div className="connected-laundry-qc-page">
    <section className="clq-hero"><div><span>CP6 · PAGAR KEAMANAN DATA</span><h1>Susun Nota FG</h1><p>Fitur ini belum aktif di UAT. Ini bukan masalah hak akses role Anda.</p></div></section>
    <div className="clq-boundary"><ShieldCheck/><span><strong>Final SKU dan stok FG sudah tersimpan dari halaman QC.</strong> Hak kerja dan payroll tidak boleh dihitung ulang dari angka sementara di browser.</span></div>
    <section className="clq-panel"><header><div><span>WRITER DIBLOKIR</span><h2>Nota FG belum aman untuk disimpan</h2><p>Rumus lama masih berada di tampilan dan dapat berbeda dari hak kerja, HPP, jurnal, serta laporan di server.</p></div><Calculator/></header><div className="clq-warning"><AlertTriangle/><span><strong>Tidak ada data yang dihapus atau diposting.</strong> Tombol simpan baru akan dibuka setelah sumber hak kerja, tarif saat transaksi, pencegah duplikasi, pembatalan, dan muat-ulang data server lulus uji menyeluruh.</span></div><div className="clq-empty"><ShieldCheck/><strong>Untuk sekarang, simpan Final SKU dari halaman QC</strong><small>Nota dan payroll terhubung akan hadir sebagai alur terpisah. Sistem tidak akan diam-diam kembali ke data simulasi.</small></div></section>
  </div>
}

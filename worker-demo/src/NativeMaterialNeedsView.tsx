import {formatFact} from './cp7/workspace'
import type {NativeAnalysis} from './nativeAnalysis'

// Display the shared receipt; never infer installation/allocation from stock.
export default function NativeMaterialNeedsView({data,visibleTargets}:{data:NativeAnalysis;visibleTargets:string[]}){
 const rows=data.analysis.material_needs.filter(m=>visibleTargets.includes(m.target_key))
 return <section aria-label="Kebutuhan bahan dari BOM ERP">
  <h3>Kebutuhan bahan</h3>
  <p>Aksesori mengikuti BOM ERP; kain mengikuti pemakaian per PCS yang direview. Keduanya memakai jumlah rencana yang sama. Bahan yang dikeluarkan belum tentu terpasang. Untuk kain, sisa layak hanya dihitung dari draf potong ERP yang terhubung ke rencana, atau stok bebas gudang bahan bila pembagiannya pasti; ini bukan reservasi stok. Tambahan dari luar hanya memperhitungkan PO terbuka yang tercatat di ERP dan datang sebelum batas waktu.</p>
  {rows.map((m,i)=><article key={`${m.target_key}:${m.material_key}:${i}`}>
   <h4>{data.labels.find(l=>l.key===m.target_key)?.sku??'Produk'} · bahan untuk rencana</h4>
   <p>{m.reason}</p><p>{m.material_key?.startsWith('FABRIC_')?'Kebutuhan kain':'Kebutuhan BOM'}: <strong>{formatFact(m.gross)}</strong>.</p>
   <p>Terpasang terbukti: {formatFact(m.installed_proven)}. Sisa layak yang sudah dialokasikan: {formatFact(m.unused_allocated_proven)}. Tambahan dari luar: {formatFact(m.additional_external)}.</p>
   <details><summary>Sumber kebutuhan bahan</summary>{m.gross.refs.map((r,j)=><p key={`${r.kind}:${r.id}:${j}`}>{r.kind} · {r.id} · versi {r.revision??'belum tercatat'}</p>)}</details>
  </article>)}
  {!rows.length?<p>Tidak ada baris kebutuhan bahan pada hasil yang ditampilkan.</p>:null}
  <p>Angka aksesori nol hanya berlaku bila BOM tercatat tanpa aksesori. Kain, kapasitas, dan kesiapan pekerjaan tetap diperiksa terpisah.</p>
 </section>
}

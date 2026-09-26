# BE — rencana implementasi writer GPT (27 September 2026 WIB)

CP6 HOLD. Dokumen ini rencana implementasi, bukan bukti lulus. Dasar: kontrak M/P, C6 rev4 yang disahkan, konsep audit `9aa7c76`, serta errata ALL-C04. Nilai fixture bukan nilai kebijakan produksi.

## Batas dan sumber existing
| Alur | Rancangan | Sumber existing / perubahan yang harus dibuktikan |
|---|---|---|
| Ganti merek FG | Pilih lot sumber dan target; atomik OUT/IN per ukuran; biaya aksesori/jasa tertaut; bongkaran terpisah | `post_product_conversion`, allocations, native adjustments BC, `propagate_conversion_hpp_for_po` |
| Rework ke SKU baru | Rework native menyimpan partial tanpa FG; COMPLETE menghasilkan GOOD lalu mengonversi lot itu dalam transaksi yang sama | `save_rework_order_v2`, `complete_rework_order_v2`, completion AV, konversi; jangan membuat dua saldo GOOD |
| Celup ulang | Pesanan vendor nyata dengan target SKU, hasil/QC dan jasa; invoice serta biaya mengikuti sumber tersebut | Rework laundry baseline tetap gratis; jalur celup berbayar membutuhkan sumber harga efektif, receipt biaya, adapter invoice BD dan recost |
| ALL-C04 | Sisa gudang terpisah dari pengeluaran/alokasi historis; periode lintas cutover memakai seluruh denominator yang terbukti | Impor native + `pocket_period_*`; jangan menciptakan adjustment atau hasil jahit historis palsu hanya untuk memenuhi foreign key |

## Invariant yang sudah dikunci sebelum kode BE
1. Stok sumber dikonsumsi sekali; jumlah per ukuran/grade pada konversi tetap. Target ganti merek/rework/celup harus mempertahankan model konstruksi dan ukuran sumber; brand/warna yang berubah tercatat eksplisit. Kenaikan GOOD hanya lewat hasil rework/QC, bukan pilihan SKU.
2. Partial rework tidak membukukan FG/payable. COMPLETE memerlukan GOOD+BS=sent. Output antara (GOOD SKU asal) dan konversinya harus atomik; pemanggilan ulang tidak membuat hasil baru.
3. Nilai sumber + tambahan sah = nilai hasil + nilai pulih + rugi terpisah. Nilai pulih yang belum diketahui tetap pending; aksesori yang diharapkan kembali bukan stok.
4. Koreksi biaya harus menjangkau seluruh turunan termasuk terjual/retur/konversi lanjutan. Posted history tetap; perhitungan berikutnya memakai versi/adjustment tertaut.
5. Non-PO/opening harus memiliki alur nilai tersendiri yang sah; guard existing `NON_PO_CONVERSION_REQUIRES_SOURCED_HPP_WORKFLOW` tidak boleh sekadar dihapus. Bila implementasi awal belum mencakupnya, status family tetap belum lengkap.
6. Tarif laundry per ukuran tidak diaktifkan. Proses/tarif yang sama dibagi per potong terkait sesuai D10; sumber tagihan yang berbeda tetap terpisah. Tarif celup unknown tidak dianggap gratis.
7. Kain kantong: pengeluaran awal expense; pengesahan alokasi mereklasifikasi ke WIP/FG/COGS, tanpa stok keluar kedua. Histori yang sudah dialokasikan tidak diposting ulang. Seluruh hasil jahit sah termasuk Afui masuk denominator.
8. Izin dicek sebelum replay cache; global submit/recovery tetap; stale version, race, inverse sumber/turunan dan periode tertutup ditolak/dikoreksi sesuai native guard. Tidak ada pengecualian detektor diam-diam.

## Tahap implementasi
1. Dokumen proses BE dan facade izin/recovery, koneksi Ganti Merek, transformasi sumber FG; keluaran/lineage dibuktikan lebih dulu.
2. Sumber biaya + bongkaran BC, koreksi/transitive recost dan opening/non-PO; kontrol konservasi positif/negatif.
3. Binding target pada native rework, celup berbayar dan adapter invoice BD; UI BS/Laundry tetap memiliki entrypoint jelas.
4. Adapter ALL-C04 dengan sumber historis dan denominator lintas cutover; continuation/inverse/jurnal/layar.
5. Tabel kasus, before/after T1, race/HTTP/browser, T2, package ke-29, rollback, CodeQL, handoff final.

## Risiko integrasi yang ditemukan dari sumber
- Fungsi konversi AC masih hanya PO, biaya nol, FIFO source; pemilihan lot spesifik membutuhkan pembatas sumber yang disahkan command, tanpa menghilangkan guard native.
- Propagasi dan target GL konversi existing menganggap source value berasal dari root PRODUCTION. Tambahan/recovery serta opening non-PO perlu masuk persamaan nilai; menambahkan angka ke HPP tujuan saja salah.
- `conversion_cost_allocated` nonnegative dan child allocations frozen sesudah POSTED. Recovery terlambat tidak boleh mengubah angka frozen menjadi negatif; gunakan fakta koreksi append-only.
- BC valuation custody membukukan kredit akun pilihan owner. Agar bongkaran dari konversi tidak bernilai ganda, BE harus menghubungkan reklasifikasi nilai dan resync HPP, termasuk sesudah penjualan.
- BD invoice sekarang hanya receipt_line atau opening_uninvoiced. Celup BS tidak boleh disamarkan sebagai kiriman produksi/opening lama; adapter sumber jasa baru harus nyata.
- Pocket period sources/destinations saat ini FK ke adjustment dan sewing event native. Fakta cutover perlu tipe sumber historis yang eksplisit; jangan membuat gerakan fisik palsu agar lolos FK.

## Status
Rencana dikunci sebelum implementasi BE. Semua kasus BE BELUM. BD completion runtime: run 36263717916, job 108464257310; selftest 108464257515. Penerimaan independen dilakukan chat auditor lain.

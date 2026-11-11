# Perbaikan harness SKU setelah shutdown kedua

Kandidat `6a087cec56aed0e0e4bec4ea8ba2132d573e8f7e`, tree
`6c6332527098c4cfff58fb65f4dc679c3082400d`, adalah satu commit di atas
`32590613a08e176536d9a19b3843f6a72f4479b4`. GitHub mengonfirmasi enam
berkas harness dan manifest, dengan lima preimage serta enam postimage
sesuai `DELTA_PINS.json`.

| Perbaikan | Hasil uji |
| --- | --- |
| Verifikasi sumber secara batch | 85 proses Git menjadi 2. Pada enam pengukuran lokal dengan 20 blob asli dan 44 identitas blob warisan, median 142,30 ms menjadi 7,03 ms. Hasil deriver dan semua pin sama. Lima perubahan path, blob atau pin yang disengaja ditolak. |
| Uji gate tertutup | Fixture sekarang menutup lima gate secara eksplisit, termasuk saat kode kandidat memiliki gate aktif. Uji lulus dan tetap menolak pembacaan receipt sebelum gate siap. |
| Pengamatan moving average | Delapan subfase mencatat awal, hasil, durasi dan waktu CPU. Uji dengan fungsi hasil deriver asli menghasilkan urutan panggilan dan hasil yang sama. Kegagalan DDL simulasi tetap diteruskan sebagai exception yang sama dan scope transaksi tetap keluar sesuai urutan. |

Lima belas kontrol terarah dan `workflow.py --check` lulus. Semua 91 pin
sumber di manifest cocok. Workflow 83 langkah, anggaran, pemulihan, kontrol
keuangan, dan pengunggahan arsip akhir menggunakan jalur semula. Uji batch
memakai tree lokal yang direkonstruksi dari blob asli dan identitas warisan.
Uji pengamatan memakai operasi pengganti untuk menelusuri urutan installer.
Kualifikasi SKU tetap membutuhkan checkout lengkap dan 27 kasus aktual.

`SKU_GLOBAL_SOURCE_COLLISION_RECEIPT.json` mencocokkan seluruh 214 path
sumber terhadap Global tertutup `c9248b87`. Seluruh 209 path dari SKU awal
cocok dengan tree Global dan lima path tambahan belum ada di tree itu.
Pemeriksaan sumber ini memberi nol kredit runtime. Verifikasi terminal untuk
run 42996079217 tetap terikat pada kandidat lama. Reader kandidat baru perlu
identitas terminal asli dan arsip kanonis baru.

Dua shutdown GitHub tetap tercatat sebagai kegagalan. Waktu penghematan
pada fixture dan pengamatan baru tidak menetapkan penyebab shutdown.
Commit ini disimpan untuk review. Kualifikasi memerlukan satu run aktif,
cabang disposable yang diotorisasi, dan sisa anggaran WIB 6j25m.

[Perbandingan enam berkas](https://github.com/Hanjay6688/-erp-garment-ux/compare/32590613a08e176536d9a19b3843f6a72f4479b4...6a087cec56aed0e0e4bec4ea8ba2132d573e8f7e)
[Run yang terputus](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/42996079217/job/130440406014)

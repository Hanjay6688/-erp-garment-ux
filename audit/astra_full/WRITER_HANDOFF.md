# CP7 d0b9e9c2 — handoff Astra (audit masih berjalan)

Kandidat produk: `d0b9e9c2e41a9f0f3a138346887434fd7d3c14f0`, tree `4bd5e1acf55f0b441d9c8f67949ee5b070eb9c41`.
Belum merupakan putusan akhir seluruh CP7. `production_go:false`. Produk tidak diubah auditor.

## ASF-F01 — kegagalan yang tidak terkait tanggal bisa diloloskan oleh retry pergantian hari

- **S3, OPEN_TOOLING, teruji runtime.** Area integritas bukti, bukan temuan salah uang/stok aplikasi.
- Sumber: `scripts/cp6_auditor_business_day.py`, `explained`, `retry_allowed`, `with_retry`.
  Dipakai oleh `strict_group`, `run_races`, `run_http`, dan `run_browser` pada kandidat.
- Kontrak paket `AUDITOR_START.md`: kontrol pergantian hari tidak boleh mengubah FAIL menjadi PASS atau
  mengulang kelompok yang gagal karena alasan lain.
- Akar masalah: `explained` menyamakan **terjadi berbarengan dengan pergantian hari** dengan **disebabkan
  pergantian hari**. Selain beberapa pengecualian alat, FAIL/COUNTEREXAMPLE apa pun dengan flag rollover
  diterima sebagai alasan retry.
- Kontrol mandiri memasukkan ketidakcocokan aritmetika yang sengaja dibuat dan tidak bergantung tanggal:
  10.001 sen teramati, 10.000 sen diharapkan. `guard` memang mempertahankan status gagal awal. Akan tetapi
  `retry_allowed=True`, kelompok dijalankan dua kali, dan `with_retry` mengembalikan status utama PASS
  ketika upaya kedua yang disuntikkan PASS. Hal ini terjadi untuk FAIL maupun COUNTEREXAMPLE.
- **Bukti gagal pertama tidak dihapus**: masih ada di `business_day_first_attempt` dan callback penyimpan.
  Cacatnya adalah keputusan retry dan hasil utama, bukan pemalsuan atau penghilangan log.
- Kontrol pembanding: PASS yang melewati hari menjadi INCOMPLETE dan boleh dicoba ulang; kegagalan tanpa
  rollover, kegagalan boundary, hasil malformed, kasus hilang, dan cleanup gagal semuanya tetap ditolak.
- Bukti: [run 38159947839](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38159947839),
  **2 PASS + 2 COUNTEREXAMPLE**; sumber alat SHA-256
  `2a8e3c61edeab8f92f3b9aaa36623e5d1ab0f1452c89ecb440b04b7f9a2ee60e`.
  `evidence/ASF_BUSINESS_DAY.json` dan `evidence/JOB_114530570757.json` menyimpan input/hasil utuh.
- Reproduksi: dari checkout audit ini jalankan
  `python audit/astra_full/probe_business_day_new.py /path/to/unchanged/d0b9e9c2`.
  Skrip hanya menjalankan modul Python asli dengan hasil kasus sintetis, tanpa database.
- Arah perbaikan: otomatisasi hanya retry hasil yang **terbukti invalid karena fixture tanggal**,
  misalnya kasus yang semula PASS dan baru dibuat INCOMPLETE oleh guard. FAIL/COUNTEREXAMPLE atau
  INCOMPLETE yang sebabnya belum terbukti tetap menjadi hasil yang harus diperiksa. Refresh tanggal
  sebelum membentuk fixture juga boleh dipertimbangkan. Jangan mengubah assertion bisnis atau status
  gagal lama supaya hijau.
- Penutup: kontrol ASF-10/11 harus menahan satu upaya dan status gagal; kontrol positif ASF-09 dan kelima
  kontrol ASF-12 tetap lulus. Jalankan semua mode yang memakai helper. Simpan first attempt dan jelaskan
  apakah bukti kandidat lama pernah terkena retry ini; jangan otomatis membuang seluruh bukti lama.

## Batas lama yang tidak dibebankan sebagai bug baru

`AS20-39_VALIDATION_NEGATIVE` masih menghasilkan counterexample ketika auditor **sengaja mematikan
trigger immutable** di salinan sekali pakai lalu merusak semantik indeks/scope/metadata. Guard ordinary
tetap menolak perubahan (55000 `CP7_RUN_IMMUTABLE`). F04 sebelumnya sudah ditutup sebagai pembetulan
klaim cakupan detektor: semantik tersebut dilindungi immutable, tidak dihitung ulang sebelum cleanup.
Raw hasil lama dan baru dipertahankan, tanpa menganggapnya sebagai bukti korupsi lewat aplikasi.

## Catatan asal bukti

Tiga workflow utama menjalankan 44 kelompok regresi, Shell/CodeQL, serta kasus mandiri pada checkout
produk terpisah dan beku. Oracle writer diberi kredit `INDEPENDENT_NATIVE_RERUN`; oracle Astra terpisah.
File metadata umum `ASTRA_EXECUTION_ORIGIN.json` pada workflow mandiri masih menulis
`oracle_origin=WRITER_UNCHANGED` dari template. Itu kesalahan label auditor; manifest preregistrasi dan
setiap case row sendiri menyebut asal dengan benar. Label mentah tidak diubah setelah run.

PR44 pernah ditulis Astra; laporan ini tidak akan memberikan penerimaan independen baru untuk area itu.
Temuan lain, penutupan temuan lama, seluruh jumlah kasus, matriks area, dan batas pemasangan akan
ditambahkan setelah seluruh bukti selesai diperiksa.

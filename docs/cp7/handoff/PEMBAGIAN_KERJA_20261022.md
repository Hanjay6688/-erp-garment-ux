# Pembagian kerja Claude dan Codex — 22 Oktober 2026 WIB

> **Digantikan (22 Okt 2026, D17-17).** Owner menyetujui `docs/cp7/PEMBAGIAN_DUA_PENULIS_20261022.md` versi 2 dan
> menyalin kotaknya ke sesi Astra. Yang tetap: Claude mengerjakan OW-06 dan menjadi penggabung tunggal. Yang berubah:
> OW-07 dikerjakan Claude (bukan Codex); Astra/Codex mengerjakan OW-10, OW-11, OW-12b, OW-13, OW-14, OW-16 di
> `astra/d17-14-produksi`; cabang kerja Claude `claude/d17-14-uang`. Isi di bawah disimpan sebagai riwayat.

Arahan terbaru owner: bagi pekerjaan supaya tidak bertabrakan dan mudah digabung. Ini memperbarui aturan satu writer
untuk seluruh repo dalam handoff awal. **Siap untuk dua penulis; orang ketiga opsional sebagai pemeriksa.** Tidak ada
agent baru yang diluncurkan dan belum ada pengakuan mulai dari Claude. Pembagian ini tidak menambah butir selesai.

## Dasar bersama dan tanggung jawab

Repo `Hanjay6688/-erp-garment-ux`. Dasar produk sebelum dokumen pembagian ini:
`01c5f8565cdae2ed36acb71fcf8a62154a4dda74`, tree `45b3773934785c83803a02624fe100ab0d107659`.
Kedua cabang kerja dimulai dari commit dokumen pembagian yang sama di atas dasar itu. Ambil versi GitHub terbaru;
ZIP privat awal berisi konteks lengkap, tetapi aturan satu writer di dalamnya sudah digantikan dokumen ini.

Status tetap **5/16**. OW06 baru mesin Native10 lulus, belum layar/izin/race/pemulihan sesudah dipakai.
OW07 belum diperiksa. Laporan kredit pelanggan masih BLOCKED di OW08 (detektor lama 2/3/1).

| Jalur | Penanggung jawab | Cabang | Hasil yang dituntaskan |
|---|---|---|---|
| A | Claude | `claude/ow06-supplier-transfer` | OW06: kontrak dan layar satu transfer ke banyak penerimaan, pembatalan/koreksi parent, login/race/browser, pemasangan dan pemulihan sesudah dipakai |
| B | Codex | `codex/ow07-hpp-close` | OW07: buktikan penghalang tutup buku untuk kantong/absen belum dialokasikan dan sisa WIP PO selesai saat pool absen terlambat diaktifkan; perbaiki celah yang terbukti |
| C opsional | Pemeriksa yang ditugaskan kemudian | Checkout terpisah pada commit yang diperiksa | Uji ulang A/B dan bandingkan dengan dasar; laporkan expected/observed serta kegagalan. Tidak mengedit produk atau mengambil OW08/09 sendiri |

**Claude adalah integrator tunggal** untuk `astra/d17-14-integrasi`. Codex tidak push produk langsung ke cabang itu.
Pembaruan dokumen pembagian ini adalah persiapan sebelum dua cabang berjalan. Reviewer internal bukan audit independen
Fable/Sol. Jalur C tidak diaktifkan otomatis; dua jalur penulisan sudah cukup untuk tahap uang/HPP sekarang.

## Batas file dan fungsi

Kepemilikan berikut mencakup file sumber, pengujian dan kuitansi yang terkait. File di luar daftar harus dialokasikan
tertulis sebelum diedit. Boleh membaca seluruh repo. Jangan mengambil semua file yang kebetulan bernama HPP/supplier.

| Pemilik | Boleh diubah di cabangnya | Batas penting |
|---|---|---|
| Claude, OW06 | `scripts/cp7_supplier_transfer/**`; file baru `scripts/cp7_ow06_*`; `.github/workflows/cp7-ow06-*.yml`; `docs/cp7/d17-14/ow06/**`; file baru `src/SupplierTransfer*` dan `src/supplierTransfer*` | Pertahankan satu kas nyata, jumlah alokasi tepat, child Native per penerimaan, pembalikan/koreksi seluruh parent, metadata/ACL lama dan pemeriksaan lengkap |
| Claude, sambungan OW06 | `src/ConnectedProcurementPage.tsx` beserta tesnya; `src/SupplierPaymentPanel.tsx`, `SupplierPaymentCreatePanel.tsx`, `SupplierPaymentCorrectionPanel.tsx` beserta tes; `src/supplierPaymentContract.ts`, `supplierPaymentCreateContract.ts`, `supplierPaymentCorrectionContract.ts` | Parser lama harus mengenal field `transfer` secara eksplisit; jangan menjadikan anak grup bisa diedit/dibatalkan sendiri. OW09 belum boleh mengubah layar ini |
| Codex, OW07 | Folder baru `scripts/cp7_hpp_close/**`; file baru `scripts/cp7_ow07_*`; `.github/workflows/cp7-ow07-*.yml`; `docs/cp7/d17-14/ow07/**` | Perbaikan sebagai delta baru terhadap fungsi installed yang benar-benar diverifikasi; jangan menulis ulang migration/release lama atau folder OW06 |
| Codex, bila celah terbukti pada facade HPP | `scripts/cp7-src/hpp-pool/pool.sql`, `scripts/cp7_hpp_pool_bundle.py`; `src/AttendanceHppPoolPanel.tsx` beserta tes dan `src/hppPoolContract.ts` | Hanya perubahan OW07 yang diperlukan. Berkas uji lama `scripts/cp7_r3_hpp_pool_cases.py` tetap menjadi oracle; tambah kasus di folder baru, jangan melonggarkan expected lama |
| Claude sebagai integrator | Pemasang/default P21, `scripts/cp7_payment_source_owning_install.py`, `scripts/cp7_payment_source_restore.py`, source/catalog manifests bersama, registrasi/routing aplikasi, `src/transactionSource.ts`, `src/TransactionSourceNavigation.tsx`, hooks bersama | Codex menulis usulan sambungan di `docs/cp7/d17-14/ow07/INTEGRATION_REQUEST.md`, bukan mengedit file bersama dari cabangnya |
| Claude sebagai integrator | `AGENTS.md`, `CLAUDE.md`, register keputusan, OPEN_WORK, SELESAI_UNTUK_DIUJI, handoff bersama dan daftar status akhir | Masing-masing writer mencatat progres di folder butirnya; integrator memperbarui status gabungan satu kali berdasarkan bukti aktual |

Satu fungsi SQL juga hanya punya satu pemilik meskipun file Python yang menurunkannya berbeda.
Sembilan delta OW06 di `scripts/cp7_supplier_transfer/native_delta.py` milik Claude, termasuk
`erp.run_v267_financial_truth_checks()`, inverse jurnal dan resolver sumber. Codex tidak menambah patch kedua atas
fungsi yang sama: tulis kebutuhan, signature, sumber awal, hasil yang diharapkan dan kasus gagal di INTEGRATION_REQUEST.
Claude mengomposisikan perubahan setelah sumber OW06 final diketahui. Gunakan aturan yang sama bila fungsi pengunci
tutup buku, pembaca GL, penghitungan HPP atau helper bersama ternyata disentuh kedua jalur.

## Langkah pertama masing-masing

Claude membaca `HANDOFF_CLAUDE_20261022.md`, OW06/CHECKPOINT dan tujuh langkah sisa OW06. Lanjut dari Native10
f764c5080991690bac443ecfe0f9171c77a0307e; jangan mengulang suite hijau OW05 tanpa perubahan/risiko yang relevan.
Tulis kemajuan di `docs/cp7/d17-14/ow06/PROGRESS.md`. Kontrak publik terbaru wajib dicatat sebelum layar memakainya.

Codex membaca OW07 pada OPEN_WORK, D17-13 kelompok3 dan keputusan owner. Telusur fungsi installed untuk tutup buku,
activate/cancel pool absen, pembagian kantong dan `erp.sync_finished_po_wip_residual(uuid,date,text)`.
Skenario minimal: belum dialokasikan menahan tutup buku tanpa efek; sesudah alokasi penghalang terkait hilang;
PO yang sudah FINISHED lalu menerima pool absen tidak menyimpan sisa WIP; cancel/correct/replay mempertahankan uang,
HPP dan sejarah. Termasuk Afui/kebijakan mandor, tanggal ekonomi/buku dan periode tertutup yang relevan.
Catat fakta terbukti terlebih dahulu di `docs/cp7/d17-14/ow07/PROGRESS.md`; jangan mengarang celah hanya agar ada patch.
Gunakan komposisi uji terpisah di atas pemasang OW05 yang diwariskan, lalu integrasikan ulang setelah OW06 masuk.

Setiap sesi memakai worktree/clone, port dan database uji buangan sendiri. Jangan checkout cabang berbeda dalam satu
direktori yang sedang dipakai penulis lain. Jangan menjalankan install/rollback ke database uji yang sama bersamaan.
Nama cabang dan daftar file tidak mengunci pekerjaan secara teknis: periksa perubahan remote sebelum mulai.
Belum ada klaim bahwa Claude sudah membaca atau menyetujui pembagian ini.

## Urutan penggabungan

1. Masing-masing push checkpoint kecil ke cabangnya, berisi satu butir pekerjaan. PROGRESS mencatat commit dasar,
   commit kandidat, file/fungsi berubah, hasil/perintah/run, masalah terbuka dan langkah berikutnya. Log besar tetap privat.
2. Claude menuntaskan dan menguji OW06, lalu menggabungkannya ke `astra/d17-14-integrasi`. Jalur Codex boleh selesai
   lebih dulu, tetapi jangan menyalip pemasangan OW06 atau mengubah source pin untuk menyembunyikan perbedaan.
3. Codex mengambil kepala integrasi yang memuat OW06, lalu **merge** integrasi ke cabang OW07 yang sudah dibagikan.
   Tidak force-push/rebase riwayat yang dipakai orang lain. Selesaikan benturan lewat kontrak/sumber, bukan memilih
   seluruh versi file salah satu pihak. INTEGRATION_REQUEST diterapkan Claude secara terpisah bila diperlukan.
4. Buktikan OW07 pada komposisi gabungan yang sebenarnya. Perubahan fungsi installed memerlukan definisi sumber/pin
   dan verifikasi seluruh22 katalog yang sesuai; jangan memproyeksikan definisi lama agar pemeriksa tampak lulus.
   Periksa dampak gabungan ke alokasi/kas supplier serta tutup buku/HPP/pool/stock. Jalankan tes yang relevan atas
   commit gabungan; tes masing-masing cabang saja belum cukup.
5. Claude menggabungkan OW07 dan menyelesaikan bukti pemasangan/pemulihan gabungan bila katalog/komposisi berubah.
   Baru perbarui daftar selesai berdasarkan kebutuhan yang terbukti. Hitungan tidak dinaikkan karena branch/PR dibuat.
   Pembagian OW08/seterusnya dicatat berikutnya, tanpa menunggu owner mengetik lanjut untuk pekerjaan yang sudah jelas.

Jika salah satu jalur terhambat CI, kerjakan tes/dokumen/scope sendiri yang masih bebas. Jangan mengambil file milik
jalur lain. Perubahan API, nama object, source pin atau urutan lock ditulis sebelum dipakai pihak lain. Push tanpa
force dan dengan kepala remote yang diperiksa; tidak ada dua penulis yang memajukan cabang integrasi.

## Dua atau tiga orang dan sisa backlog

Dua penulis sekarang memberi dua hasil terpisah pada prioritas uang/HPP. Orang ketiga paling berguna menguji commit
yang sudah konkret, sehingga penulis tidak sama-sama menulis fitur yang sama. Bila kelak dibutuhkan penulis ketiga,
OW09 dapat dipisah sebagai paket tersendiri setelah endpoint/file dibagi; jangan mengaktifkannya berdasarkan dokumen ini.
Delapan layarnya tersebar di Nota, kas, stok FG, penyesuaian FG, hitung fisik, aksesori, riwayat bayar penjualan dan retur
invoice. Pembagian menurut halaman saja belum cukup: source resolver, hooks, RecordTools dan fungsi SQL bersama
bisa bertabrakan dengan OW06/OW08. OW10–14 juga berbagi mesin analisis; jangan memecahnya acak ke banyak orang.

Tujuan tetap menyelesaikan kebutuhan ERP owner, mendahulukan keuangan/stok/HPP dan membuat satu versi yang bisa diaudit.
OW15 paket auditor dikerjakan terakhir. CP7C formal belum dimulai. Kandidat auditor55c885d1, main, Enteng, hosted,
produksi dan WA nyata tetap tidak disentuh. Jangan mengubah angka kebijakan, menyamarkan kegagalan lama, atau
menyamakan pemeriksaan internal dengan persetujuan produksi.

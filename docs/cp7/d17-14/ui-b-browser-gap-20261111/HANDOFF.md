# Serah-terima B · bukti UI/browser CP7 · 11 November 2026 WIB

Pemeriksaan dilakukan di repo terpisah. `BROWSER_PLAN.json` mengikat skenario ke blob
skrip yang ada, peran, prasyarat, dan bukti terdahulu. Jalur yang bisa memakai ulang
bukti dipisahkan dari uji yang perlu dijalankan setelah kandidat dan database uji
diterima A.

## SKU · penyebab penolakan pemeriksaan sumber

Run `42860774082`, job `129985976421`, attempt 1, head `82b03bb` berakhir
**FAILURE**. Tahap 67 menjalankan `check_source.py --runtime` dan berhenti pada
baris 247 dengan `SKU_AUTOMATIC_EXACT_ADDITIVE_NAMESPACE_REQUIRED`. Tahap 68–76
dilewati, termasuk instalasi browser, start database dan Native25+Browser2.
Run ini menghasilkan **0 transaksi ERP dan 0 skenario browser**. Unggah bukti
dan langkah pembersihan selesai. [Log asli](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/42860774082/job/129985976421#step:67:1)

- Set path Git kandidat dan gabungan path deklarasi sama persis, 14.828 masing-masing.
- ZIP asli `13785432077` berukuran 72.973 byte, SHA-256
  `933564713f8602f3385317c12072ee2a51370d440cb78beae9de313b996cd958`, 118 entri
  lulus CRC. Dua receipt di dalamnya ditulis oleh langkah sukses 65 dan 66 ke
  `cp6-proof/t3/`.
- Replay offline mengekstrak ZIP ke repo sementara yang menggunakan `.gitignore`
  asli. `git ls-files --others --exclude-standard` dan kedua fungsi
  `runner_inputs` asli menyisakan tepat dua path:
  `FREE3_PARENT_ORIGINAL_ADMISSION.json` dan
  `SKU_CURRENT_MANDOR17_ORIGINAL_ADMISSION.json`. Mengeluarkan dua berkas itu
  dari replay membuat selisih kosong. Dua nama tetangga yang tidak dideklarasikan
  tetap ditolak. Pemeriksaan awal B mengira hanya FREE3 yang tertolak. Hasil
  pertama memunculkan kedua path dan pemeriksaan ulang mengonfirmasinya.
- Usulan untuk A adalah mengakui dua path persis sebagai keluaran prasyarat
  yang diverifikasi, memakai pemeriksaan berkas reguler dan pin/identitas
  prasyarat yang berlaku. Jalankan ulang pemeriksaan sumber dengan keluaran
  tahap 65/66, kontrol berkas ekstra, dan validasi receipt sebelum kandidat
  penerus. Jangan mengabaikan seluruh folder bukti atau melonggarkan perbandingan
  path. A memegang patch dan keputusan menjalankan kandidat penerus.
  [Arsip kegagalan pertama](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/42860774082/artifacts/13785432077)

## Pemakaian ulang bukti

| Jalur | Bukti yang dipertahankan | Sisa pada kandidat sekarang |
| --- | --- | --- |
| Mandor | Receipt gabungan 15 + 2 skenario Auth aktual, termasuk 1440/390, respons hilang dengan UUID tetap dan dua tab pada desktop, stale/fresh read pada HP. Sumber Mandor gabungan telah diikat oleh SKU. | Pakai hasil gabungan sesuai sumber dan skenario yang sudah diverifikasi A. |
| SKU | Empat tampilan fixture B mendukung kesiapan kontrol Mandor/SKU. Dua skenario SKU aktual sudah ada di runner Native25. | Jalankan dua kasus yang sudah ada bersama kandidat penerus A. Run 82 gagal sebelum kasus itu. |
| Analisis produksi dan progres keuangan | Bukti browser aktual B dari run 40697846383. Pemeriksaan A mengikat 79 masukan build B yang identik pada SKU82 dan Global c924. | Pertahankan bukti pada cakupan itu. Cocokkan lagi hanya bila sumber build, Auth atau backend progres berubah pada kandidat akhir. |
| OW08 | Delapan skenario asli (SOURCE6 + MONEY2) dan 187 tes terarah sumber saat ini tersedia. | Uji ulang terarah QC/FG. Kasbon, cuci, dan vendor mengikuti delta di bawah. |
| R10/G04 | Original P11 membuktikan 10 skenario Auth. Original rantai penjualan dan pembetulan retur membuktikan 2 + 2 skenario Auth. Browser OW04 juga memiliki kasus refund, undo, dan akses dicabut. | Jalur transaksi dan tampilan penjualan berubah sejak fd702d7. Ikat bukti terkini per kasus. Jalankan hanya delta yang belum memiliki bukti setara. |
| OW06/OW09 | Browser2 OW06 dan Browser13 OW09 historis tersedia. Usulan penutupan 68773c1 memiliki 92 tes klien dan build lulus. | Periksa runtime untuk perubahan yang diadopsi, termasuk konteks harga aksesori, paginasi uang, dan paginasi daftar supplier. |

Bukti Mandor gabungan [arsip terverifikasi](https://chatgpt.com/library?file_id=libfile_406787deb6f88191bb73c7d652297167&account_id=personal).
Bukti B [Mandor/SKU fixture](https://github.com/Hanjay6688/-erp-garment-ux/blob/36092cfbccfb7543b628f857bd0bab900a7bab72/docs/cp7/d17-14/ui-b-mandor-sku-smoke-20261106/HANDOFF.md)
dan [analisis gabungan](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/40697846383).
Pemetaan [OW08](https://chatgpt.com/library?file_id=libfile_fde3_f-d86d9ef0d1d881919f1d2eb2940cc3ed_3b0e0eac7dc08191b44c16f18a1e98fe&account_id=personal).

## Seleksi pengujian siap diperiksa A

1. **OW08 QC/FG, dua skenario dari runner yang ada.** Ambil ekspor `cases`
   dari `scripts/current-ow08-source-browser/fg.mjs` langsung. Host yang ada
   menerima `exercise_browser(..., script=fg_path, ids=dua_id_fg, tag=tag_baru)`.
   Pemanggil SOURCE6 yang lama memaksa enam ID, jadi gunakan pengikatan kandidat
   penerus yang memasukkan dua ID di manifestnya. A mengikat host dan katalog
   aktual, build, aktor, fixture moving average dan restore sebelum jalan.
   QC menyebut transaksi penjualan dan adjustment penyebab blokir. Tombol
   batal finalisasi harus nonaktif. OWNER membuka adjustment terbalik yang
   benar. ADMIN HP menerima 403/42501 dan layar tak menampilkan dokumen.
   Cocokkan business rows dan sequence sebelum/sesudah, serta cek tampilan
   1440/390, kontras dan console dengan pengecualian 403 terverifikasi.
2. **R10/G04, dua skenario rantai utama bila belum ada bukti setara pada
   kandidat akhir.** Gunakan ekspor `cases` dari `cp7_p11_returns_browser.mjs`
   untuk grade A desktop dan grade B HP. Kedua skenario mulai dari master dan
   stok fixture, lalu membuat, posting, retur, pembayaran, dan membalik dari
   UI. Ikat ulang fixture nilai ke aturan valuasi aktif dan bandingkan jurnal,
   AR, stok dan HPP dengan hasil resmi. Pertahankan oracle asli pada sumbernya.
   Tambahkan hanya sel yang masih kosong setelah pencocokan: refund kas
   pelanggan dan revoke/recovery dari kasus OW04 yang sudah ada, serta stale
   draft atau klik ganda jika belum tercakup. Untuk stale gunakan dua sesi
   dan cek versi lama ditolak tanpa DML, lalu refresh. Untuk klik ganda
   tangkap jumlah permintaan, UUID dan kejadian finansial, lalu cocokkan
   satu efek bisnis. Cocokkan dahulu bukti draft, pembayaran sebagian, reverse
   atomik dan pembetulan retur sebelum memilih uji tambahan.
3. **OW08 lain, hanya bagian yang berubah.** Kasbon cukup navigasi GIVEN/
   CANCELLED dari buku besar dan cek layout bila resolver, izin dan fixture
   sama. Cuci cukup UI harga belum diketahui dan aksi tarif bila perubahan
   hanya di tampilan. Ulang transaksi tarif satu kali bila writer atau state
   berubah. Vendor mulai dari layar refund/riwayat dan akses dicabut di HP.
   Jalankan ulang rantai desktop refund–recovery–inverse–kredit invoice hanya
   bila writer, izin atau komposisi laporan berubah. Pakai ID asal di JSON.
4. **OW06/OW09, hanya jika perubahan 68773c1 diadopsi.** Pakai kasus OW06
   desktop/HP yang sudah ada dan fixture penerimaan dua halaman. Pembacaan
   yang punya `next_offset` tidak boleh mengembalikan halaman kosong.
   Untuk OW09 pilih bagian kas desktop/HP dari Browser13 dan kembangkan
   fixture multi-halaman: Browse kembali ke offset 0, filter dan total
   tetap konsisten, serta jumlah debit/kredit di halaman tidak melampaui
   hasil filter. Cek nota aksesori dengan konteks bawaan dokumen dan override
   yang sah secara terpisah. Tambah bukti browser aksesori hanya bila suite
   kandidat akhir belum mencakup kedua jalur. Cakupan 92 tes klien tidak
   diberi kredit Auth atau database.

A tetap memegang kandidat, izin, dan integrasi. Paket B berisi seleksi uji dan
reproduksi offline dengan 0 run baru. Global masih menunggu SKU aktual dan
restore. Formal CP7 5/16, R10/G04 terbuka, `production_go=false`,
`independent_acceptance=false`.

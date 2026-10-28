# A — saksi layar uang OW08b, dua perjalanan

Status awal **PREPARED/CLOSED**. Belum ada klaim browser aktual. Kandidat backend
41caaaed sedang diuji pada run40769840440 (kegagalan fixture pertama54b tetap disimpan); `accepted_backend11=null` menutup
pelaksanaan sebelum database. Isi pin hanya sesudah Original lengkap backend11
dan kelima gate paket benar-benar diterima. Hasil Native7 lama atau job hijau
tanpa Original tidak dapat membuka gate ini.

Komponen yang dipakai ulang: pemasang `cp7_vendor_receivable.composition`, mode
`cp6_auditor_modes.run_browser`, host Auth/Playwright CP6 dan adapter salinan
`ow04-payment-current-qualification/copy_authority.py`. Tidak ada host browser,
scheduler, ledger atau mesin uang kedua. Paket analisis produksi/perencanaan B
tidak diulang atau diubah.

Probe memanggil `cp7_vendor_receivable.composition.install(cur)` secara langsung,
bukan merakit ulang tiga langkah pemasangan di probe. Fungsi existing tersebut
memasang rantai readonly/3194 dan delta vendor yang sama. `verify(cur,state)` dan
`rollback_preuse(cur,state)` adalah kontrak existing. Registry entry point ada
di CONFIG dan masuk deklarasi bukti; sumber installer historis tetap utuh karena
masih dipakai sebagai fondasi rantai. Pengujian browser penerus akan menjadi
saksi aktual panggilan pemasang lengkap ini; persiapan sumber belum meluluskannya.

| Perjalanan | Bukti yang harus dibuat |
|---|---|
| Desktop OWNER | Refund 1.000,25 lewat layar; piutang 3.000 → 1.999,75; bank +1.000,25; respons transaksi yang benar-benar committed dihilangkan satu kali; reload dan reconcile memakai UUID/payload sama, baris refund tetap satu; pembatalan lewat layar memulihkan piutang/bank; pembayaran asal tetap utuh; bukti refund tetap ada berstatus dibatalkan |
| Mobile ADMIN, 390 px | Refund 750,10 lewat layar; piutang 2.249,90; bank +750,10; pencabutan izin uang lalu muat ulang menyembunyikan angka dan kontrol; seluruh keadaan uang tetap sama |

Periksa kontras teks, lebar halaman, console, Auth, salinan database, seluruh
22 kelompok katalog, data/sequence/role/CP6/advisor dan pemulihan penuh. Simpan
hasil pertama. Tinjau screenshot hasil aktual sebelum menerima tampilan.

Invoice dan koreksi awal dibuat oleh penulis Native existing di salinan lokal;
ini **belum** membuktikan pembuatan invoice/koreksi melalui layar. Tidak ada
klaim kelulusan respons hilang sebelum perjalanan aktual dijalankan; belum ada klaim browser seluruh alur laundry, pengiriman atau produksi. Console helper B dipakai persis tanpa perubahan: semua error disimpan, hanya satu pesan jaringan dari URL refund yang sengaja diputus yang boleh dikenali sebagai expected.
Penjaga pencopotan setelah uang dipakai dan inverse sebelum pemakaian memakai
bukti backend11 identik yang sudah lengkap, tidak diberi label pengujian baru.

Satu perubahan produk: penjelasan pencocokan saldo menambahkan piutang vendor
yang memang sudah dihitung server; kredit belum dipakai sudah mencakup piutang
itu. Tidak mengubah rumus, angka, penulis, recovery atau RPC. Admission membatasi
perubahan klien tepat dua penggantian teks dan menolak perubahan lain.

Kontrol lokal: `python -B scripts/current-vendor-money-browser/test_admission.py`,
`node --check scripts/current-vendor-money-browser/cases.mjs`, serta DOM dan
typecheck layar terkait. Ini kontrol lokal, bukan kelulusan Auth/browser aktual.
Workflow hanya dipicu pada cabang kualifikasi penerus setelah pin lengkap;
checkout persiapan ini tidak memulai CI/database.

Penerimaan penulis tidak sama dengan audit independen. Formal CP7 tetap5/16;
`production_go=false`, `independent_acceptance=false`, CP7C belum dimulai.


Pemeriksa visual A meneruskan rumus luminance dan ambang4,5 existing, tanpa
mengubah helper B. Adaptasi alpha/group-opacity diperlukan karena tombol
nonaktif pada `initial-import.css` memakai opacity0,5. Semua teks terlihat
tetap dicatat dan wajib4,5; tidak ada pengecualian tombol nonaktif atau angka.
Foreground dan background dikomposisikan terpisah ke setiap ancestor. Tujuh
kontrol matematika mencakup opaque, alpha, opacity bersarang, background
transparan serta penolakan image yang benar-benar berkontribusi. Ini hanya
bukti alat ukur lokal; kontras UI tetap harus dibuktikan pada browser aktual.

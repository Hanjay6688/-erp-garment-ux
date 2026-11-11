# Koreksi pembulatan HPP non-PO SKU

Kandidat Writer A `6b3d69a707c040a8770b7548fb4e041f1dc0b394`, tree
`d7671173c03228f2c3049826ff4dd8b3efc5e675`, berinduk langsung pada
`87c60856783395e0aa25af97b7f839538b4e2c0d`. Kandidat ini mencakup
perlindungan cleanup dari run lain. Kualifikasi aktif masih di
`32590613a08e176536d9a19b3843f6a72f4479b4`.
[Kandidat A](https://github.com/Hanjay6688/-erp-garment-ux/commit/6b3d69a707c040a8770b7548fb4e041f1dc0b394)

## Penyebab dan koreksi

Setelah biaya susulan dan retur parsial, nilai mentah persediaan dan HPP
penjualan masing-masing 36,505. Pembulatan sendiri-sendiri menghasilkan
36,51 + 36,51 terhadap total 73,01. Selisih menghasilkan kredit
`OTHER_INCOME` 0,01. Writer B menyimpan kegagalan pertama dan menguji
usulan pembulatan kumulatif. Writer A mengikat koreksi tersebut ke
derivasi dan profil katalog yang dipakai pemasang SKU. Rumus mempertahankan
prioritas pembulatan persediaan, menghitung HPP penjualan dari selisih
total kumulatif, dan tetap menghitung saldo akun lain dari nilai yang sah.
Jalur PO memakai rumus sebelumnya.
[Kegagalan dan reproduksi B](https://github.com/Hanjay6688/-erp-garment-ux/blob/ad6085433f4c394236a3284670fd704a4524191c/docs/cp7/review/sku-moving-average-regression-20261111/HANDOFF.md)

Dua definisi diubah pada instans komposisi uang yang dipakai SKU.
Pemeriksaan profil donor masih berjalan terlebih dulu. PostgreSQL 17.6
menghasilkan isi kedua definisi yang sama dengan pin katalog baru serta
atribut fungsi yang sama dengan sebelum koreksi. Dari 30 penggantian uang,
28 definisi lainnya identik. Sembilan penggantian otomatis dan semua
penambahan katalog tetap cocok dengan profil asal.

Pemeriksaan sebelum database juga mereproduksi `ModuleNotFoundError`
pada impor internal `financial_delta`. Pemasang uang dan otomatis kini
memakai modul yang sama dari donor uang yang dipatok selama derivasi.
Pemeriksaan menolak modul dari sumber lain dan melepaskan pengikatan
sesudah derivasi. Pemeriksaan sebelum setup database membaca Original
Native27 dengan hash yang dipatok, menurunkan kedua profil, dan menolak
lapisan otomatis yang akan menimpa definisi hasil koreksi.
[Pemeriksaan derivasi](ROUNDING_SOURCE_PREFLIGHT.json)

Pemeriksaan pohon kandidat membaca ulang 14.730 berkas parent dan 95
berkas pada namespace SKU. Semua byte cocok dengan sumber yang dipatok.
Template aktif cocok dengan 83 langkah yang ditinjau, termasuk urutan
pemeriksaan sebelum database. Kontrol receipt worker, checkpoint dan
deadline browser lulus 28/28. Paket kontrol preparasi historis memuat
kasus untuk gate yang masih tertutup dan aset historis yang absen dari
checkout lokal. Hasilnya sama pada baseline dan kandidat saat dibandingkan.
[Pemeriksaan sumber dan template](SKU_SOURCE_CHECKS.json)

## Hasil uji terarah

| Kasus | Hasil PostgreSQL 17.6 |
| --- | --- |
| Biaya susulan 3,02 sesudah penjualan satu dari dua pcs | Persediaan 36,51 dan HPP penjualan 36,51. Retur mengembalikan 2 pcs dengan persediaan 73,02 dan HPP penjualan 0. |
| Retur satu dari dua pcs setelah biaya susulan 3,01 | Persediaan 36,51, HPP penjualan 36,50, dan saldo pendapatan lain 0. Koreksi balik biaya mengembalikan 36,00 untuk masing-masing persediaan dan HPP penjualan tanpa mengubah snapshot transaksi. |
| Tujuh kontrol aritmetika | Sen ganjil, sen genap, saldo akun lain yang sah, HPP penjualan mentah negatif, persediaan kosong, nilai besar, dan rumus PO lama lulus. |

Kedua kasus transaksi cocok terhadap jurnal per akun, nilai persediaan,
HPP penjualan, kuantitas buku stok serta cache, dan replay rekonsiliasi
dengan nilai yang sama. Kedua rollback mengembalikan sensus 75 tabel
fixture. Rollback luar mengembalikan skema dan role fixture. Proses
PostgreSQL loopback berhenti. Pemeriksaan katalog 22 kelompok memakai
proyeksi katalog donor. Penilaian perubahan atribut fungsi memakai
`pg_proc` aktual pada fixture.
[Hasil PostgreSQL](ROUNDING_POSTGRES17_RESULT.json)

## Dampak lintas ERP

Pemindaian sumber SKU membaca 256 berkas SQL pada migrasi dan
`scripts/cp7-src`. Sembilan belas berkas cocok dengan pencarian pola
pembulatan HPP. Tiga overlay CP7 yang cocok membaca atau memformat nilai
untuk potong, persediaan dan ringkasan gudang. Pasangan pembulatan
independen yang menghasilkan kegagalan ini ditelusuri ke donor moving
average dan kedua definisi uang yang diperbarui oleh kandidat SKU.
Migrasi dasar non-PO memakai pembulatan per lot. Beberapa pembaca
membulatkan ulang angka yang sudah ditetapkan. Rumus dan kontrak masing-masing perlu
counterexample bisnis sendiri sebelum diubah. Audit sumber ini mencakup
kode yang dipatok, dengan bukti perilaku pada fixture SKU di atas.

Untuk kualifikasi gabungan, skenario Native `sold_return` sudah memuat
invoice pemasok aktual, retur parsial, dan inverse yang sama dengan
counterexample. Fixture lokal menjalankan fungsi penjualan, retur, jurnal
dan rekonsiliasi pada data uji bertipe, sedangkan posting invoice pemasok
dan replay UUID pada ERP gabungan masih memerlukan kualifikasi SKU.
Penerimaan SKU menunggu 25 Native, dua browser, lima pemeriksaan, pemulihan
utuh, worker berhenti dan arsip kanonis. Global tetap menunggu hasil SKU.

Reproduksi memakai input kandidat yang dibangun dari langkah 1–3 pada
handoff B. Tempatkan hasil preparasi kandidat dalam `focused-r6/` di lab
yang sama dengan `native27/` dan `handoff/`. Jalankan
`prepare_rounding_probe.py` dengan direktori akar kedua donor, direktori
sumber komposisi A, direktori lab B, lalu direktori hasil baru. Jalankan
`run_rounding_probe.sh` dengan direktori hasil dan lab B. Server uji
menggunakan PGDATA baru dan port loopback tersendiri.

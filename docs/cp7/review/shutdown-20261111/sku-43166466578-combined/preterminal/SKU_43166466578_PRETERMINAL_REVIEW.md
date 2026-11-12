# Pemeriksaan sumber SKU dan bukti Writer B

12 November 2026 WIB. Kandidat `af6e5710c0a3265daeb14c8ccd078ea82c99c482`, tree `41aa56dc3247e7a802e8b2f48d55e15ff933954b`. Run 43166466578 dan job 131009386319, attempt 1. Arsip checkpoint sebelum database terikat pada kandidat ini. Ukuran 22.421 byte, SHA-256 `fbb0f377d289ca520748ce3208a3074ea37ad93723eee4ee00eed6331b2259d9`, CRC satu anggota lulus dan isi tiga receipt cocok. Kredit skenario 0. [Run SKU](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/43166466578/job/131009386319)

## SQL yang dihasilkan pemasang

Parser PostgreSQL 17.7 memeriksa 757 berkas SQL terdaftar dari tree SKU. Temuan mencakup sintaks khusus psql, masukan builder, potongan diagnostik, placeholder, dan penetapan atribut komposit yang memerlukan katalog. Pemeriksaan menemukan nol pola pembatas tunggal yang menjatuhkan 3f2a. Kompilasi ulang memeriksa 27 masukan SQL yang dikirim pemasang atau driver, termasuk Money, Automatic, Mandor, dua paket CP6 yang dihasilkan builder, kapsul analisis, dan 20 masukan Global. Seluruh 350 statement, 106 body PL/pgSQL, dan 22 body SQL terurai. Pemasang 3f2a yang dibentuk ulang tetap mereproduksi error `as $`. Pemasangan PostgreSQL 17.6 dan rollback terarah untuk SQL Automatic dicatat di receipt reproduksi terdahulu.

Sebelum pengujian mahal, bentuk SQL dengan donor dan manifest yang benar-benar akan dipakai. Periksa SQL hasil pembentukan dan body fungsi, lalu uji pemasangan yang berubah pada fixture PostgreSQL disposable. Pemeriksaan tata bahasa dan bukti pemasangan dicatat terpisah.

## Handoff Writer B

Empat belas berkas paket cocok ukuran dan SHA-256. Seluruh 21 pin sumber dan UI sama pada `d08032a` dan `af6e5710`. Dari katalog aktual E4EA, 20 fungsi dan lima view snapshot cocok dengan Native27. Dua fungsi buku moving average juga cocok, dan dua postimage pembulatan sen cocok dengan hasil perbaikan A. Receipt menyimpan pin per fungsi untuk dibandingkan dengan katalog aktual kandidat saat terminal.

| Bukti yang dipakai | Hasil dan cakupan |
| --- | --- |
| Moving average | Tujuh langkah pada fixture UTC, termasuk dua biaya susulan, retur bertahap, inverse dan replay yang sama. Fingerprint 75 tabel pulih. Posting invoice pemasok dan replay UUID gabungan masih mengikuti Native SKU. |
| QC fisik dan snapshot WIP/FG | 8/0 menjadi 5/3 PCS. Snapshot awal tetap dapat dibaca. |
| Report v2 `DEFERRED` | Fisik dan tersedia 0 menjadi 3 PCS, 11 PCS di luar filter dikecualikan, arsip awal utuh, identitas salah ditolak. |
| UI laporan | Tujuh uji DOM/unit lulus. Bukti browser mengikuti cakupan run historis yang dicatat B. |
| Valuasi QC dan Report v2 `INCLUDED` | Menunggu fixture Native dengan biaya resmi 8 PCS Rp288,00 dan akun WIP/FG aktif. Setelah posting 3 PCS, cocokkan WIP Rp180,00, FG Rp108,00 dan HPP penjualan Rp0,00 ke buku serta owner report untuk periode dan tanggal laporan yang sama. |

Bukti laporan agregat harus memakai baseline dan perubahan nilai yang sama dengan buku jurnal. Laporan `INCLUDED` mengikat hash ke sumber keuangan yang sama dengan RPC owner. Pakai publikasi sebelum dan sesudah QC untuk memeriksa arsip serta tanggal bacanya. [Handoff B](https://github.com/Hanjay6688/-erp-garment-ux/blob/52b6cf93dd85bc76a713e29beb5ae6d91247f9c7/docs/cp7/review/sku-snapshot-report-focused-20261112/HANDOFF.md)

Kualifikasi SKU gabungan masih menunggu 13 kasus Native, dua browser, lima gate, pemulihan dan Original terminal. Bukti E4EA dipakai untuk 12 kasus yang terbukti setara. Formal CP7 5/16. Penerimaan independen dan produksi mengikuti keputusan yang berwenang.

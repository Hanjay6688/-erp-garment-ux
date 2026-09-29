# Hasil audit independen CP7 keluarga 2

**F02 masih HOLD: satu bug WIP dan satu gate integrasi X06.** Kandidat `17e8540`. `production_go=false`.

## Temuan tes mandiri

Pembatalan QC atau penerimaan laundry yang mengandung BS sudah diterima oleh ERP, tetapi pembaca WIP CP7 masih mencari jejak BS yang sumbernya sudah dibatalkan. Hasilnya menjadi `CONFLICT / BS_SOURCE_LINEAGE_MISMATCH`.

Contoh gampang: ada 100 PCS. Setelah QC, posisinya 80 WIP + 15 jadi + 5 BS. QC dibatalkan secara sah. Seharusnya kembali menjadi **100 WIP**, tetapi CP7 malah menganggap hubungan asal barangnya bermasalah.

Pembanding tanpa BS lulus. Pembatalan rework juga lulus. Temuan ini membuktikan hasil WIP tidak bisa dipakai setelah koreksi tersebut; tidak membuktikan uang, jurnal atau stok hilang.

**20 kasus baru auditor: 18 PASS, 2 counterexample untuk masalah yang sama.** Tes lulus mencakup hitungan jumlah/yield besar, batas data, status produksi, bulk atomik, benturan operator dan pencabutan izin saat menunggu/replay.

## Cross-check writer

**54 kasus writer lulus saat dijalankan ulang oleh auditor.** Bukti historis P03 15 kasus dan P04 39 kasus cocok dengan kode, hash dan artefak aslinya. Jadi hasil hijau mereka valid untuk kasus yang mereka uji; pembatalan dengan BS di atas belum tertangkap oleh suite tersebut.

Tes aplikasi auditor: **638 PASS**, pemeriksaan keamanan dan build lulus. Enam browser shell milik writer sudah dicocokkan, tetapi bukan bukti UI P03/P04 yang terhubung.

## Tambahan auditor sebelah, sudah direproduksi sendiri

**Temuan X06 valid.** Dengan 17 PCS dan yield 2/3, matcher menolak sumber merah → target biru. Allocator tetap menyebut alokasinya layak ketika diberi label “cocok” palsu. Kontrol merah → merah lulus. Kasus tanpa bukti warna yang diwajibkan juga bisa diberi label positif dan lolos kernel allocator.

Ini **gate sambungan matcher ke allocator**, belum bukti stok/transaksi live salah: fungsi masih privat. Owner menempatkan X06 di P04; sambungan sumber/target P06/P07 wajib membawa gate ini sampai tertutup. Hasil hijau auditor sebelah berarti reproduksinya berhasil, bukan berarti produk sudah menolak alokasi tersebut.

[Reproduksi mandiri tambahan](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36528326077) memakai kode fungsi yang sama pada PostgreSQL sementara. Satu kasus tambahan ini dicatat terpisah dari 74 kasus ERP lengkap sebelumnya. Asal temuannya tetap dikreditkan ke [PR34](https://github.com/Hanjay6688/-erp-garment-ux/pull/34).

## Catatan supaya writer tidak dibebani temuan palsu

Lima kasus awal tersangkut setup auditor: pemakaian helper versi yang keliru, bentuk data volume yang tidak sah, dan nama master contoh yang berbenturan. Semuanya dituntaskan lewat ulangan terarah. Itu tidak diserahkan sebagai bug produk. Hasil akhir unik adalah **72 PASS + 2 counterexample**, tanpa kasus tersisa INCOMPLETE.

Paket 30 berkas, pemulihan database, batas bisnis CP6, keamanan dan pembersihan lingkungan uji lulus. Kode produk tidak diubah. Push terbaru yang dicek (`e21f0b9`) belum mengubah bagian F02 tersebut.

[Run awal](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36526434075) · [Run ulangan terarah](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36527127588) · [Handoff lengkap untuk writer](HANDOFF.md)

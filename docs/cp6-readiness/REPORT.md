# Hasil perbaikan enam risiko CP6

Perbaikan kode dan uji sudah selesai, tersimpan di [draft PR 39](https://github.com/Hanjay6688/-erp-garment-ux/pull/39). **Go produksi masih ditahan.** Database hosted belum dipasang dan delapan isian nyata belum disimpan. CP6 tetap ditutup untuk lingkup kontrak; pekerjaan ini tidak menutup CP7.

| Catatan auditor | Yang sudah dibereskan | Yang masih harus dibuktikan |
|---|---|---|
| Belum pernah dipasang di hosted | Pemasang maintenance diuji dari versi v2.6.20, dengan akun pemilik biasa. Seluruh 58 berkas terpasang, mesin Native BF terverifikasi, dan 10 kasus pemasangan/penolakan lolos | Pemasangan pertama ke hosted pada jendela maintenance yang disetujui |
| Sen W8 bisa menumpuk dalam satu PO | Laporan HPP menjelaskan aturan ini. Tujuh nota diuji memakai hitungan Decimal yang disusun terpisah, termasuk koreksi langsung dan invoice terlambat | Keuangan memahami pilihan T3=A: pembulatan per dokumen tetap berlaku dan tidak ada batas sen per PO |
| Skenario BF memakai tarif laundry pada SKU | Skenario aktif diperbaiki agar harga berasal dari vendor/proses/paket. FREE, WAIVED, UNKNOWN dan KNOWN diuji; contoh SKU tetap tanpa tarif laundry | Receipt lama tetap historis. Uji yang sengaja menyuntikkan override SKU salah tetap merupakan uji penolakan |
| UI belum diperiksa langsung | Browser dengan login dan API asli lolos 31 kasus desktop/ponsel. Delapan screenshot hasil terbaru sudah dilihat; laporan HPP benar-benar selesai dimuat | Penyamaan dengan demo acuan dan pemeriksaan auditor lain belum selesai |
| Delapan pengaturan kosong membuat operator bingung | Halaman menunjukkan pengaturan yang kurang dan akibatnya sebelum posting. Empat keputusan yang sudah disetujui punya tombol pengisian formulir; nilai aktif tetap didahulukan | Bos menetapkan akun, kategori dan perjanjian nyata. Tombol pengisian tidak otomatis menyimpan |
| Bukti terlalu bergantung pada skenario penulis lama | Ditambah hitungan terpisah untuk pembulatan, campuran status harga, prasyarat posting invoice dan HPP fisik 16 PCS; semua dijalankan di database | Ini bukti penulis penerus, belum pengesahan auditor independen. Tidak ada klaim kepercayaan 100% |

Hosted yang diperiksa masih **v2.6.20**, belum mempunyai 28 tahap A–AB. Karena itu, memasang hanya paket 30 berkas AC–BF belum cukup. Pemasang sekarang membawa 28 tahap pendahulu yang dibekukan, lalu 30 berkas CP6 yang diterima. Semua SQL tetap dengan byte/hash aslinya.

## Bukti terakhir

Source yang diuji: `07f949dfcf3bfea2f96df6173ed82331d379150c`, dari CP6 diterima `10a834712e515af86c6d8baa89bbe40cff9793e3`. Semua job pada [run Native](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36821348197) dan [run Shell](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36821348177) selesai sukses.

| Pemeriksaan | Hasil |
|---|---|
| Transaksi database | 104 PASS |
| Benturan transaksi serentak | 26 PASS |
| Hak akses HTTP dengan Auth asli | 9 PASS |
| Browser desktop dan ponsel | 31 PASS; nol kesalahan console |
| Pemasang pemilik tanpa superuser | 10 PASS; seluruh 58 berkas terpasang |
| Tes aplikasi | 583 PASS dalam 54 berkas; pemeriksaan keamanan dan build lolos |
| Kebersihan runtime | Database utama uji tetap utuh; Auth kembali 0; salinan uji race/HTTP/browser dibersihkan |
| Backup/restore sekali pakai | Data identik dan jawaban mesin sama. Ada 19 pesan pg_cron yang terjelaskan karena nama database tujuan; tidak ada error restore yang belum terjelaskan |

Pemeriksaan advisor memenuhi gate paket, tetapi **bukan berarti daftar advisor kosong**: dari 73 menjadi 216 entri, dengan 143 tambahan INFO. Perbandingan advisor hosted setelah pemasangan tetap tercantum di runbook. Latihan restore di CI juga belum membuktikan pemulihan hosted nyata.

Receipt yang memuat source, batas klaim dan hash ketiga arsip: [FINAL_VERIFICATION.json](FINAL_VERIFICATION.json). Bukti pemasang: [OWNER_QUALIFICATION_FINAL.json](OWNER_QUALIFICATION_FINAL.json). Penjelasan skenario BF: [BF_SCENARIO_ERRATA.md](BF_SCENARIO_ERRATA.md).

## Urutan menuju pemasangan pertama

1. Tetapkan delapan isian nyata pada [daftar pengaturan](README.md#pengaturan-delapan-isian-empat-keputusan-satu-sengaja-kosong), serta tinjau empat keputusan yang sudah tersedia. Akun dan perjanjian vendor tidak ditebak.
2. Siapkan backup yang sudah diuji pemulihannya, pemeriksaan baseline terbaru dan jendela maintenance yang disetujui. Jalankan [runbook hosted](HOSTED_MAINTENANCE.md); pemasang tidak mematikan sesi orang lain secara paksa.
3. Setelah pemasangan berhasil, aplikasi tetap dalam maintenance. Pemilik menerapkan pengaturan lewat RPC Native dan memeriksa transaksi contoh, laporan, advisor dan bukti pemasangan. Pengaturan BC/BD belum bisa diisi pada hosted sekarang karena tabelnya belum ada.
4. Cocokkan UI dengan demo acuan, minta pemeriksaan independen, lalu putuskan go produksi secara terpisah.

Tidak ada merge utama, pemasangan hosted, perubahan admission hosted atau penyimpanan nilai nyata dalam pekerjaan ini. Kegagalan percobaan CI sebelumnya tetap tersimpan, tidak diberi ulang label PASS.

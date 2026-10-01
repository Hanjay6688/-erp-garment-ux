# CP7: melanjutkan dari kegagalan Native163

Writer CP7 dilanjutkan 1 Oktober 2026 dari `2874698`. Run [36816430354](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36816430354) belum qualified. [Receipt asli](../evidence/f05-native-history/first163-2874698/RECEIPT.json) mempertahankan error, kasus yang diamati, hash arsip dan Auth yang belum kembali bersih. Native155 pada `928332d` tetap bukti historis yang diterima dalam batasnya.

Perbaikan berikut membutuhkan uji Native baru; statusnya **IMPLEMENTED, NATIVE_PENDING**:

- Kontrol sumber riwayat yang sengaja incomplete sekarang memakai dollar quoting PL/pgSQL yang sah. Angka 26 episode tetap dibuat dari pembayaran dan pembatalan Native, bukan insert langsung.
- Kalender skenario browser memasukkan seluruh pekerjaan WIP yang tersimpan dari perjalanan sebelumnya, lalu menambah 120 menit bebas. Oracle kapasitas menghitung lama kalender aktual dikurangi seluruh pekerjaan dan beban lain. Fixture tidak membuang asal WIP atau mengganti UNKNOWN menjadi SCENARIO untuk kalender yang kurang.
- Perintah perhatian dan pemeriksaan episode memeriksa ulang aktor, role, seluruh permission, kewenangan keuangan dan domain setelah setiap lock. Pembacaan berat seluruh Original/sumber/keuangan tidak diulang pada setiap lock metadata. Respons akhir tetap membaca Original dengan guard, pemeriksaan sumber terbaru dan redaksi Native yang sama. Pembaca tugas pribadi hanya membaca tautan milik aktor dan tetap melalui guard Native pengingat.
- Helper browser Tanya AI menunggu tindakan dan respons dalam satu Promise.all. Penolakan wait tidak lagi menjadi promise liar yang mematikan host sebelum pencatatan kasus dan cleanup.

Tambahan satu race memegang lock permintaan pengingat secara nyata, mencabut hanya `finance.period_close.manage` milik ADMIN yang Original-nya memuat preflight keuangan, lalu melepas lock. Perintah harus ditolak tanpa commit perhatian/receipt. Ini memeriksa bahwa pengurangan pembacaan tidak melemahkan kewenangan setelah menunggu.

Anggaran successor: **164 = 105 Native + 21 race transaksi + 14 Auth HTTP + 24 browser**. Semua kasus harus PASS, Source SHA harus cocok, primary dan Auth kembali bersih, CP6 terpulihkan, dan gate advisor terpenuhi. Batas waktu PostgREST tidak dinaikkan. SQL CP6 yang diterima, angka keuangan/stok/HPP, arsip Original dan kontrak framework tetap utuh.

Pemeriksaan lokal: 1105 tes unit PASS; satu kernel F04 berhenti karena lingkungan ini tidak memiliki PostgreSQL Native. Ini kegagalan lingkungan yang tercatat, bukan PASS atau skip. Security checks dan build PASS. Workflow Shell menyediakan PostgreSQL Native untuk memeriksa seluruh 1106 tes.

Belum ada penutupan seluruh F01–F06, penerimaan auditor independen, merge utama, hosted install, pengiriman WA atau go produksi. Sesudah irisan ini qualified, pekerjaan berikutnya tetap material/model/apply, lifecycle laporan, aturan/domain P16 lain dan paket final F06.

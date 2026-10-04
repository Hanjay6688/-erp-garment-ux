# Pembetulan retur pelanggan tercatat

Kandidat ini menambah edit retur fisik pelanggan: retur lama dibalik dan satu retur pengganti disahkan dalam satu transaksi database. Nomor, waktu dan isian fisik retur lama tetap tersimpan. Pulihkan isi lama membuat pembetulan baru dengan alasan dan pemeriksaan baru. Ini tidak menghapus transaksi lama atau otomatis membatalkan seluruh rantai usaha.

## Batas dan sumber

- Read: `erp_cp7_get_sales_return_correction_v1(p_query)`; write: `erp_cp7_correct_sales_return_v1(p_payload,p_request,p_expected)`.
- Parent, alokasi baris penjualan, lot, stok, gudang aktif, grade, nilai retur, pembayaran aktif dan HPP berasal dari Native yang terpasang. Client tidak mengirim produk, lot atau HPP buatan.
- Setiap dokumen tetap memakai satu baris per alokasi, mengikuti batas Native. Kombinasi grade/gudang untuk alokasi yang sama tetap memakai dokumen retur terpisah.
- Review mengikat revisi/token parent dan token retur yang mencakup stok lot terkait, HPP, gudang serta jurnal sumber. Pemeriksaan otoritas dan token diulang setelah menunggu kunci.
- Izin edit memerlukan Owner/Admin dengan izin create/post/reverse retur serta lihat HPP yang sekarang berlaku. Cached outcome tidak melewati pemeriksaan otoritas sekarang.
- UUID dan payload yang sama mengembalikan satu hasil committed. UUID sama dengan payload berubah ditolak. Error akhir mengembalikan seluruh efek transaksi, termasuk metadata CP7.
- Stock yang sudah dipakai tetap bisa menahan pembalikan Native. Pembayaran aktif tidak otomatis direfund. Tidak ditambahkan batas umur koreksi atau kebijakan pemilik baru.
- Waktu WIB yang tidak diedit mempertahankan mikrodetik sumber. Pembalikan private menggunakan waktu fisik asli. Jurnal Native tetap memakai tanggal posting yang diizinkan Native; metadata penataan waktu dan overlay laporan mengikat jurnal asli/invers sebenarnya.

## Native tetap utuh

Empat helper inverse Native disalin ke namespace private dengan empat delta yang dinyatakan: penjagaan context, panggilan helper private, timestamp gerakan inverse asli, dan pencatatan penataan waktu jurnal/HPP retur. Definisi Native asli dibandingkan dengan SHA-256 sumber dan derivasi private harus identik dengan delta yang dinyatakan. Tidak ada aplikasi diberi DML ERP atau EXECUTE private. Tabel history dan helper source menolak UPDATE, DELETE dan TRUNCATE.

Resolver sumber membaca tautan nyata dan mengembalikan parent/child serta offset halaman. Outcome membawa offset pengganti yang dihitung resolver Native; UI tidak menebak halaman pertama. Sumber inverse yang tidak memiliki tautan pembetulan ini mempertahankan pembatasan sebelumnya.

## UI dan recovery

`ConnectedSalesPage` memiliki write/recovery UUID. `SalesReturnPanel` membaca riwayat dan gudang memakai tiket owning invoice. `SalesReturnCorrectionPanel` memiliki satu read RPC, meminjam tiket tersebut, dan tidak membuat atau menyelesaikan tiket parent. Reply lama/retired tidak menghidupkan fakta kembali. Error read sekarang meretire owning invoice.

Input operator disimpan sementara dalam sesi per actor/permission/parent dan dihapus setelah commit. Yang disimpan hanya ID pilihan dan isian pengguna; kapasitas, baris katalog, token, tiket dan tanda sudah diperiksa tidak disimpan. Alokasi yang belum dimuat kembali tidak dapat disimpan.

Riwayat mempunyai `Edit retur …`, `Lihat perubahan retur …`, tautan transaksi lama/pengganti dan `Pulihkan isi retur sebelum pembetulan`. Tombol inverse lama tetap mengikuti perilaku dan label yang telah diuji sebelumnya.

## Uji yang dinyatakan sebelum hasil

`scripts/cp7_sales_return_correction_cases.py` menetapkan 25 ID unik: 16 Native, 4 race dengan koneksi/kunci nyata, 3 Auth HTTP, 2 browser desktop/mobile. Alur browser melakukan 2 PCS/Rp40 → 1 PCS/Rp20 → 2 PCS/Rp40, menautkan child asli/pengganti, dan desktop membuang reply setelah backend commit lalu mereconcile UUID yang sama setelah reload.

YEAR_364 membuat transaksi Native sungguhan: saldo awal 4.516 PCS, penjualan asal 48, retur 24, 364 penjualan kemudian masing-masing 12. Retur pengganti 36 harus menambah semua 364 saldo berjalan berikutnya sebesar 12 di urutan buku dan kronologi, baik stok fisik maupun tersedia. Empat array asli sebelum/sesudah disimpan. Ini bukan bukti SLA produksi atau seluruh P19.

Tes history menambah 26 peer-return Native supaya child pengganti benar-benar di offset 25. Pembatasan field, jumlah, cents, pembayaran aktif, stok yang telah dipakai, gagal posting terakhir, closed books, akses dicabut, source berubah, replay dan pemulihan diuji dengan rollback boundary Native/private lengkap.

Status ketika kandidat ditulis: Python/JS/TS parser syntax dan diff whitespace lolos lokal. Runtime Native dan browser baru belum dikualifikasi. Jalankan workflow `CP7 Native Atomic Customer Return Correction`, simpan ZIP asli/digest/seluruh JSON roots/log, periksa setiap 25 ID dan empat grup, install/restore/advisor gates, pin source serta screenshot asli sebelum memperbarui status. Shell, CodeQL dan regresi F03 yang terpicu juga harus diperiksa pada head baru; hijau head sebelumnya bukan penerimaan kandidat ini.

`production_go=false`; penulis bukan auditor independen. Supplier-return, cutting-posted edit/inverse, rollback seluruh dependency, recipe/material eligibility, P18/P19 penuh, keputusan owner dan hosted P21 masih terpisah.


## First c79 UI compile result

Actual cash/misc run37173078125/job111349864833 and run37173077938/job111349864508 stop before disposable provisioning on six TypeScript diagnostics. Completed Original full logs and exact diagnostics are retained at evidence/sales-return-correction/first-c79-ui/RECEIPT.json. No Native/restore credit is claimed. The successor uses the actual TransactionSourceLink sourceType/sourceId props with pending/stale disablement, a nullable ticket signature in the declared DOM stand-in, explicit globalThis.document for its DOM container, and Number only after the strict outcome parser has accepted the actual page offset. No Native budget, guard or timeout is altered. Fresh Shell/Native25 and triggered regressions remain required.

# Kontrol transaksi — rollout awal

Mandat owner: USER_TRANSACTION_TOOLS.md. Seluruh submenu dan seluruh entry belum selesai. Ini kandidat UI berikutnya di atas sumber produk9cc70e5 yang sebelumnya lulus seluruh paket wajib; bukti Native sumber9cc tidak otomatis mengesahkan perubahan ini.

Implementasi awal mencakup empat tampilan penjualan yang memakai ConnectedSalesPage, Penyesuaian Bahan, dan Penyesuaian Barang Jadi. RecordTools memberi pencarian melalui reader yang sudah dimiliki, Browse semua yang mengembalikan query ke awal, dan urutan nomor/nama pada halaman yang sedang tampil. Filter status invoice tetap memakai query backend. Status penyesuaian hanya memfilter halaman yang sudah dibaca dan diberi label "Status di halaman ini"; ini belum memenuhi exit filter global untuk seluruh dokumen. Sort tampilan tidak mengubah row_version, ID, waktu fisik, qty/harga, pagination, saldo resmi atau Original.

Edit draft dan Benerin nota dipindah dekat judul invoice; nama tindakan dan handler Native yang sudah dimiliki tetap dipakai. Hapus/batalkan membuka pemeriksaan dan alasan tindakan yang ada. Invoice dengan pembayaran atau retur aktif menyebut nomor invoice, jenis penghalang, dan tombol untuk membuka daftar pembayaran/retur yang berhak dilihat. Pembatalan prematur dikunci; koreksi atomik nota tetap tersedia jika haknya lengkap. Backend tetap memeriksa review_token, expected version, akses dan seluruh ketergantungan saat perintah dikirim. Daftar UI ini belum merupakan graph seluruh penghalang: pemakaian barang retur, kredit/refund dan ketergantungan modul lain tetap harus datang dari writer sumbernya.

Enam kontrol lokal baru memeriksa: browse/filter via reader tanpa business write; source-page sorting tetap mempertahankan identitas, saldo exact dan versi besar; hide/show filter menjaga nilainya; invoice dengan dua jenis penghalang menolak reversal tanpa menolak atomic edit; page filter penyesuaian FG tidak mengubah stok atau writer; page filter hitung bahan tidak membuat hitung fisik atau writer. Seluruh aplikasi lokal1149/119 PASS. Build/security PASS. Tes DOM lokal bukan Native PostgreSQL atau browser hosted.

Sumber SQL, Native business helpers, grant, formula stok/uang/HPP/laporan, timeout, payload owning correction dan UUID recovery tidak diubah. File Claude tidak disentuh: ConnectedProcurementPage.tsx, ConnectedMaterialsPage.tsx, productionRecovery.ts, types/database.preconnect.ts, source/access catalogs serta receipt/name SQL. Tidak ada impor WIP Claude.

Complete owning-note40, all eight F03 components dan Native Shell wajib lolos pada sumber baru. Jalur material count/FG adjustment harus tetap menjaga bukti P09/P10 dan browsernya; semua failed Originals tetap dipertahankan. Paket kandidat ini tidak menutup mandat seluruh transaksi, keluarga CP7, audit independen, demo atau production GO.

Sisa rollout: header fitur lain, filter/sort global yang belum dimiliki reader, tindakan pada seluruh transaksi sumber, navigasi source dari buku/ledger/jurnal/laporan, daftar ketergantungan bernama dan terurut, serta edit atomik yang memang belum tersedia. Jangan menyamarkan tombol pembalikan sebagai bukti bahwa semua edit sudah ada.

CP6 HOLD; audit_complete=false; production_go=false.

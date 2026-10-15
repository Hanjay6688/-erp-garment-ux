# Astra — 48 layar benar-benar dimuat, tiga mode, desktop dan HP

Run 38794405101, control 8344fbc171b6a115ac9efa1730c5f6b4cf3a499d, kandidat dfab13bf. **288 PASS untuk inventaris awal halaman**, nol fallback lazy-loading, nol overflow horizontal, nol pageerror dan nol RPC4xx/5xx yang tercatat. Ini tidak menyatakan semua aksi/tombol telah diuji. Mode Enteng memakai build UAT_AUTH_SIMULATION yang asli dengan Auth/PostgREST lokal; tidak mengakses hosted.

Kolom vonis mempertahankan kajian perilaku/source pada laporan pertama. Bukti runtime baru mencatat kontrol yang terlihat, body, respons RPC dan screenshot per ID. Kesamaan teks awal dengan demo menguatkan keberadaan halaman contoh; bukan bukti CRUD berhasil. Perbedaan antara demo dan connected bukan otomatis cacat.

| # | Menu | Tes vs demo | Enteng vs demo | Kontrol awal demo/tes/Enteng (desktop) | RPC awal tes/Enteng | Teks awal Enteng = demo |
|---|---|---|---|---|---|---|
| 1 | Dashboard | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | 9/0/0 | 0/0 | TIDAK |
| 2 | Buat Potongan | BEDA | BEDA | 129/28/25 | 2/2 | TIDAK |
| 3 | Bagi Potongan | BEDA | BEDA | 48/14/14 | 2/2 | TIDAK |
| 4 | WIP & Sewing | BEDA | BEDA | 31/21/21 | 2/2 | TIDAK |
| 5 | Laundry | BEDA | BEDA | 19/16/16 | 1/1 | TIDAK |
| 6 | QC & Final SKU | BEDA | BEDA | 21/10/10 | 1/1 | TIDAK |
| 7 | Susun Nota FG | BEDA | TIDAK ADA LAYAR TERSAMBUNG | 6/19/0 | 1/0 | TIDAK |
| 8 | Barang BS & Rework | BEDA | BEDA | 23/17/17 | 2/2 | TIDAK |
| 9 | Ringkasan Gudang | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | 6/6/6 | 0/0 | YA |
| 10 | Pembelian & Penerimaan | BEDA | BEDA | 22/12/12 | 1/1 | TIDAK |
| 11 | Bahan & Roll | BEDA | BEDA | 22/12/12 | 2/2 | TIDAK |
| 12 | Kain kantong | BEDA | BEDA | 0/15/15 | 1/1 | TIDAK |
| 13 | Aksesori | BEDA | BEDA | 25/11/11 | 1/1 | TIDAK |
| 14 | Ringkasan Barang Jadi | BEDA | BEDA | 20/11/10 | 1/1 | TIDAK |
| 15 | Mutasi Barang Jadi · Vivo | BEDA | BEDA | 17/22/22 | 2/2 | TIDAK |
| 16 | Mutasi Barang Jadi · Widie | BEDA | BEDA | 17/22/22 | 2/2 | TIDAK |
| 17 | Kartu Stok FG | BEDA | BEDA | 13/11/10 | 1/1 | TIDAK |
| 18 | Stock Adjustment | BEDA | BEDA | 10/20/20 | 2/2 | TIDAK |
| 19 | Ganti Merek | BEDA | BEDA | 16/22/22 | 2/2 | TIDAK |
| 20 | Penjualan & Invoice | BEDA | TIDAK ADA LAYAR TERSAMBUNG | 30/11/30 | 1/0 | YA |
| 21 | Semua Invoice | BEDA | TIDAK ADA LAYAR TERSAMBUNG | 14/11/14 | 1/0 | YA |
| 22 | Retur Penjualan | BEDA | TIDAK ADA LAYAR TERSAMBUNG | 12/11/12 | 1/0 | YA |
| 23 | Pembayaran Pelanggan | BEDA | TIDAK ADA LAYAR TERSAMBUNG | 11/11/11 | 1/0 | YA |
| 24 | Riwayat Pelanggan | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | 6/6/6 | 0/0 | YA |
| 25 | Ringkasan Keuangan | BEDA | TIDAK ADA LAYAR TERSAMBUNG | 16/12/16 | 1/0 | YA |
| 26 | Kas & Bank | BEDA | TIDAK ADA LAYAR TERSAMBUNG | 7/11/7 | 1/0 | YA |
| 27 | Hutang Supplier & Vendor | BEDA | BEDA | 8/5/5 | 1/1 | TIDAK |
| 28 | Piutang Pelanggan | BEDA | TIDAK ADA LAYAR TERSAMBUNG | 8/10/8 | 1/0 | YA |
| 29 | Payroll & Kasbon | BEDA | TIDAK ADA LAYAR TERSAMBUNG | 12/18/12 | 1/0 | YA |
| 30 | Absensi & Rate Harian | BEDA | TIDAK ADA LAYAR TERSAMBUNG | 42/17/42 | 1/0 | YA |
| 31 | Nota Ambil Aksesori | BEDA | BEDA | 18/21/21 | 1/1 | TIDAK |
| 32 | HPP & Rekalkulasi | BEDA | BEDA | 24/13/13 | 2/2 | TIDAK |
| 33 | Jurnal & Transaksi Lain | BEDA | TIDAK ADA LAYAR TERSAMBUNG | 11/12/11 | 1/0 | YA |
| 34 | Laporan & Tutup Buku | BEDA | TIDAK ADA LAYAR TERSAMBUNG | 7/14/7 | 2/0 | YA |
| 35 | Kain & Benchmark | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | 7/7/7 | 0/0 | YA |
| 36 | Aksesori & Harga Mandor | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | 27/27/27 | 0/0 | YA |
| 37 | Produk & SKU | BEDA | BEDA | 14/5/5 | 1/1 | TIDAK |
| 38 | Pelanggan | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | 7/7/7 | 0/0 | YA |
| 39 | Supplier & Vendor | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | 7/7/7 | 0/0 | YA |
| 40 | Mandor | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | 8/8/8 | 0/0 | YA |
| 41 | Gudang & Lokasi | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | 7/7/7 | 0/0 | YA |
| 42 | Pola | BEDA | BEDA | 12/10/10 | 1/1 | TIDAK |
| 43 | Reminder | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | 19/19/19 | 0/0 | YA |
| 44 | Pengguna & Hak Akses | BEDA | BEDA | 8/24/24 | 1/1 | TIDAK |
| 45 | Pengaturan ERP | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | 13/13/13 | 0/0 | YA |
| 46 | Impor data awal | BEDA | BEDA | 0/5/5 | 1/1 | TIDAK |
| 47 | Tutup Periode | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | 7/7/7 | 0/0 | YA |
| 48 | Audit Trail | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | 14/14/14 | 0/0 | YA |

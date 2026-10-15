# Astra — 48 menu, kandidat dfab13bf

`INDEPENDENT_SOURCE_REVIEW` atas percabangan `src/App.tsx:276–314,630–762`, `config/runtime.ts`, komponen tujuan, serta kontrak RPC. Bukti DOM baru ada di `INDEPENDENT_CASE_DETAILS.json`; bukti Chromium yang dijalankan ulang Astra: CP17, run 38784698219, sepuluh kasus desktop/HP. Bukti browser penulis dibaca per kasus dalam `REUSED_WRITER_CASE_LEDGER.json`. Ini bukan klaim 48 layar telah diuji seluruh isian/tolak/HP secara langsung oleh Astra.

Istilah vonis membandingkan perilaku, bukan sekadar kesamaan judul. **BEDA** berarti ada perbedaan nyata pada alur/isian/perhitungan; tidak otomatis cacat. **TIDAK ADA LAYAR TERSAMBUNG** mencakup halaman contoh, pemberitahuan, atau batas yang sengaja belum dibuka. Keberadaan RPC di kode tidak membuktikan RPC sudah terpasang di Enteng; audit ini tidak mengakses hosted.

| # | Menu / id | DISPOSABLE_TEST vs demo | Enteng vs demo | Perbedaan yang diperiksa; komponen utama |
|---|---|---|---|---|
| 1 | Dashboard / dashboard | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | `OwnerDashboard`: angka contoh disembunyikan sesuai keputusan owner; hanya pemberitahuan. Rujukan ke menu lain belum menjamin angka asli. |
| 2 | Buat Potongan / cutting-roll | BEDA | BEDA | `ConnectedCuttingPage`: ID PO/pola/roll, versi, draft→POST dan recovery server; demo memakai katalog lokal. Panel analisis CP7 tertentu hanya disposable. |
| 3 | Bagi Potongan / mandor-wip | BEDA | BEDA | `ConnectedPickupPage`: antrian dan batch sumber, versi, POST; REOPEN/pickup reverse/kain kembali memakai review server. Demo menyimpan state lokal. |
| 4 | WIP & Sewing / sewing-wip | BEDA | BEDA | `ConnectedWipStatusPage` + `SewingCompletionPanel`: jumlah selesai dan upah nyata; demo memilih laundry dari kartu. Pengiriman nyata dilanjutkan pada menu Laundry. Tarif wave SKU ditolak secara eksplisit. |
| 5 | Laundry / laundry | BEDA | BEDA | `ConnectedLaundryPage`: sumber batch/ukuran, harga dan invoice BD, kapasitas/versi/dependensi; demo lokal. Uji browser nyata penulis tersedia; bukan sertifikasi semua variasi. |
| 6 | QC & Final SKU / qc | BEDA | BEDA | `ConnectedQcFinalPage`: identitas receipt/batch-size dan Final SKU nyata; demo membuat kartu nota lokal. Server melindungi lineage/qty. |
| 7 | Susun Nota FG / fg-handoff | BEDA | TIDAK ADA LAYAR TERSAMBUNG | `ConnectedFgHandoffBoundary`: disposable membuka `ConnectedNotaPage` berbasis hak kerja; Enteng hanya batas belum aktif. |
| 8 | Barang BS & Rework / bs-rework | BEDA | BEDA | `ConnectedBsResolutionPage`: kasus/lineage, rework/resolve/scrap dan guard biaya native; demo state lokal. Tautan ke sumber rework diperiksa browser penulis; seluruh kombinasi penyelesaian belum diuji Astra melalui browser. |
| 9 | Ringkasan Gudang / warehouse-dashboard | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | `WarehousePages` tetap data contoh dalam kedua mode. |
| 10 | Pembelian & Penerimaan / procurement | BEDA | BEDA | `ConnectedProcurementPage`: sumber supplier/material, penerimaan ESTIMATED/FINAL, draft/post, koreksi dan pembayaran; state contoh tidak digunakan. |
| 11 | Bahan & Roll / materials-rolls | BEDA | BEDA | `ConnectedMaterialsPage`: buku/stock roll dan transfer berbasis server; tanggal dan pembalikan diperiksa server. |
| 12 | Kain kantong / pocket-fabric | BEDA | BEDA | `ConnectedPocketFabricPage`: alokasi/sumber CP6, sementara demo hanya pemberitahuan; perhitungan tidak berasal dari angka contoh. |
| 13 | Aksesori / accessories | BEDA | BEDA | `ConnectedAccessoryServicePage`: sumber/layanan/retur/biaya server, berbeda dengan daftar simulasi gudang. |
| 14 | Ringkasan Barang Jadi / fg-summary | BEDA | BEDA | `ConnectedFgStockPage`: stok dan lineage server; planner/analisis/tautan CP7 tertentu dibatasi disposable. UAT bukan semua panel yang diuji CI. |
| 15 | Mutasi Barang Jadi · Vivo / movements-vivo | BEDA | BEDA | `ConnectedFgBookPage`: buku per merek dan tanggal dari sumber, bukan array mutasi yang bisa diedit lokal. |
| 16 | Mutasi Barang Jadi · Widie / movements-widie | BEDA | BEDA | Komponen buku sama dengan parameter Widie; identitas merek harus tetap terpisah. |
| 17 | Kartu Stok FG / stock-card | BEDA | BEDA | `ConnectedFgStockPage purpose=CARD`: lineage dan sejarah server; tautan transaksi asal hanya disposable. |
| 18 | Stock Adjustment / stock-adjustment | BEDA | BEDA | `ConnectedStockAdjustmentPage`: hitung fisik, review, posting dan penolakan stale; berbeda dengan perubahan state contoh. |
| 19 | Ganti Merek / brand-conversion | BEDA | BEDA | `ConnectedProductConversionPage`: pilih lot, inverse dan nilai server; tidak sekadar ubah label produk. Bukti BE native/HTTP/browser lama dibedakan dari komposisi CP7. |
| 20 | Penjualan & Invoice / sales-invoice | BEDA | TIDAK ADA LAYAR TERSAMBUNG | `ConnectedSalesPage` hanya disposable; Enteng `SalesPages`. Lusin 3/5/4 dan satu ukuran berhasil, tetapi ditemukan pencampuran merek dan simpan saat seri masih dimuat. |
| 21 | Semua Invoice / sales-allocation | BEDA | TIDAK ADA LAYAR TERSAMBUNG | Disposable memakai daftar/paging server `ConnectedSalesPage`; Enteng halaman contoh. Tidak ada bukti browser khusus seluruh alur view ini. |
| 22 | Retur Penjualan / sales-returns | BEDA | TIDAK ADA LAYAR TERSAMBUNG | Disposable kapasitas retur berasal dari allocation/lot server; Enteng simulasi. E01/return-correction dibaca per kasus. |
| 23 | Pembayaran Pelanggan / sales-payments | BEDA | TIDAK ADA LAYAR TERSAMBUNG | Disposable payment/reversal dengan ID, tanggal, bank dan versi; Enteng simulasi. |
| 24 | Riwayat Pelanggan / sales-history | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | Selalu `SalesPages`, bukan riwayat pelanggan server. |
| 25 | Ringkasan Keuangan / finance-overview | BEDA | TIDAK ADA LAYAR TERSAMBUNG | Disposable `ConnectedFinanceOverviewPage`; Enteng `FinancePages`, angka contoh tanpa label simulasi pada hero (DOM terbukti). |
| 26 | Kas & Bank / finance-cash | BEDA | TIDAK ADA LAYAR TERSAMBUNG | Disposable `ConnectedCashLedgerPage`: tanggal, akun, sumber dan running balance; Enteng contoh. |
| 27 | Hutang Supplier & Vendor / finance-ap | BEDA | BEDA | `ConnectedSupplierCreditPage`: saldo/kredit supplier; vendor diarahkan ke Laundry, berbeda dari gabungan daftar contoh. |
| 28 | Piutang Pelanggan / finance-ar | BEDA | TIDAK ADA LAYAR TERSAMBUNG | Disposable `ConnectedReceivablesPage` dengan tautan invoice; Enteng contoh. |
| 29 | Payroll & Kasbon / finance-payroll | BEDA | TIDAK ADA LAYAR TERSAMBUNG | Disposable `ConnectedPayrollPage`: sumber, review/approve/pay/cicilan/kasbon; Enteng angka contoh tanpa label simulasi hero (DOM terbukti). |
| 30 | Absensi & Rate Harian / operations-attendance | BEDA | TIDAK ADA LAYAR TERSAMBUNG | Disposable `ConnectedAttendancePage` berbasis periode/roster server; Enteng `OperationsAdminPages`. Tidak berarti lifecycle pool HPP absensi lengkap melalui UI. |
| 31 | Nota Ambil Aksesori / contractor-issue | BEDA | BEDA | `ConnectedAccessoryIssuePage`: sumber gudang, qty/harga hak mandor, POST/inverse dan recovery; demo lokal. Sambungan sampai kas payroll belum dibuktikan satu perjalanan browser. |
| 32 | HPP & Rekalkulasi / hpp | BEDA | BEDA | `ConnectedSkuHppPage`: nilai stok per SKU/lot, recost dan `PoFinishPanel`; demo checklist. Label “HPP final” terlalu tegas ketika hasil server BELUM_LENGKAP/ESTIMATED. |
| 33 | Jurnal & Transaksi Lain / finance-journal | BEDA | TIDAK ADA LAYAR TERSAMBUNG | Disposable `ConnectedJournalPage` dan writer misc; Enteng contoh. Tautan transaksi asal dibatasi disposable. |
| 34 | Laporan & Tutup Buku / finance-reports | BEDA | TIDAK ADA LAYAR TERSAMBUNG | Disposable `ConnectedFinanceReportPage`: laporan/tutup periode berdasarkan sumber; Enteng contoh. Menu admin Tutup Periode lain masih simulasi. |
| 35 | Kain & Benchmark / master-fabric | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | `MaterialMasterPages` tetap state contoh; bukan CRUD material harian server. |
| 36 | Aksesori & Harga Mandor / master-accessory | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | `MaterialMasterPages` tetap contoh; tarif khusus yang ada di alur lain tidak menggantikan halaman master ini. |
| 37 | Produk & SKU / master-products | BEDA | BEDA | `ConnectedSkuMasterPage`: kelompok Merek/SKU, versi efektif, member ukuran dan legacy basis; demo edit lokal. DB mengizinkan nomor SKU sama pada merek berbeda. |
| 38 | Pelanggan / master-customers | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | `MasterDataPages` memakai state lokal; pelanggan baru harian tidak disimpan server dari menu ini. |
| 39 | Supplier & Vendor / master-partners | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | `MasterDataPages` contoh; master khusus vendor laundry tidak menutup seluruh kebutuhan supplier. |
| 40 | Mandor / master-workforce | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | `MasterDataPages` contoh; bukan pembuatan kontraktor server harian. |
| 41 | Gudang & Lokasi / master-locations | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | `MasterDataPages` contoh; lokasi baru tidak tersimpan ke ERP dari sini. |
| 42 | Pola / master-pattern | BEDA | BEDA | `PatternPage` memakai runtime patternMode; connected list/save/deactivate RPC, kode+revisi stabil dan alasan audit. Uji browser nyata seluruh CRUD belum ditemukan. |
| 43 | Reminder / admin-reminders | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | `OperationsAdminPages` + state reminders; bukan sumber pengingat native meski planner mempunyai fitur lain. |
| 44 | Pengguna & Hak Akses / admin-access | BEDA | BEDA | `AccessControlPage`: permission bundle, role/user save RPC, protected role dan review risiko; demo lokal. Bukan sertifikasi seluruh kombinasi RBAC melalui browser. |
| 45 | Pengaturan ERP / admin-settings | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | `OperationsAdminPages` contoh; tidak mengatur kebijakan server dari menu ini. |
| 46 | Impor data awal / admin-import | BEDA | BEDA | `ConnectedInitialImportPage`: berkas/preview/review/apply/rollback native, bukan CRUD harian; demo pemberitahuan. |
| 47 | Tutup Periode / admin-period-close | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | Menu admin tetap contoh; writer periode nyata hanya tersedia melalui Laporan di disposable. |
| 48 | Audit Trail / admin-audit | TIDAK ADA LAYAR TERSAMBUNG | TIDAK ADA LAYAR TERSAMBUNG | Menu contoh; adanya audit immutable di DB tidak membuat halaman ini tersambung. |

## Batas UX dan pengujian

Lusin: bukti browser independen desktop/HP mencakup pilih satu ukuran→semua ukuran, satu ukuran→12, 3/5/4→teks 1 lusin, simpan dan reread server, serta tiga ukuran satu baris tanpa overflow. DOM Astra menambah kontrol 2 lusin→edit 3/5/4: total berubah menjadi 1 lusin, isian helper tetap 2. Perbedaan isian helper dicatat sebagai perilaku, tidak dianggap membatalkan permintaan owner yang secara eksplisit meminta tulisan total mengikuti PCS.

HP seluruh 48 menu, seluruh pesan penolakan dan seluruh kombinasi role **belum diuji langsung Astra**. Baris BEDA tidak memberi kelulusan visual menyeluruh. Uji browser CP17 memakai runtime DISPOSABLE_TEST dengan backend/Auth nyata. Enteng di sini dinilai dari kode routing; tidak ada kontak ke hosted atau deploy.

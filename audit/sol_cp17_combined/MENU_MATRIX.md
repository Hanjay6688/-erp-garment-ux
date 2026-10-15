# Matriks 48 menu — Sol

Kandidat `dfab13bf62398a69a02bf6221c06d29075e5e40b`. Semua 48 menu diperiksa pada kedua mode, dibanding demo; 288 kunjungan Chromium = 3 mode × 48 × 2 ukuran layar. **Auth/access tiruan, semua RPC bisnis 403** pada inventory ini. Saksi browser Native positif berasal dari run F03/CP17 yang dicatat terpisah, hanya build DISPOSABLE_TEST. Tidak ada SQL/permintaan hosted.

T = tersambung; D = data contoh; B = batas belum aktif; N = pemberitahuan. Setiap T/N dinilai **BEDA** dari demo sesuai perilaku kolom akhir; D/B = **TIDAK ADA LAYAR TERSAMBUNG**. BEDA mencakup penjagaan yang memang diwajibkan, bukan selalu bug.

| Menu | DISPOSABLE | UAT/Enteng | Perilaku dan batas |
|---|---|---|---|
| Dashboard | N | N | Demo menampilkan KPI; mode tersambung hanya pemberitahuan tanpa angka. Pemberitahuan mengarahkan ke Penjualan/Keuangan/Gudang yang sebagian masih simulasi di UAT. |
| Buat Potongan | T | T | PO aktif, Pola, roll/lokasi, waktu WIB, yard dan hasil per ukuran divalidasi server; demo memakai state lokal. SOL-R1-002: tidak ada jalur PO harian baru. POST potongan dari browser belum dibuktikan di putaran ini; panel kain kembali diuji terpisah. |
| Bagi Potongan | T | T | Pembagian memakai pickup Native, versi sumber dan pemulihan UUID; demo menambah kartu lokal. Browser membuktikan batal pickup yang sah, bukan POST pembagian baru dari awal. |
| WIP & Sewing | T | T | G1 mencatat jumlah selesai + upah komponen + siap laundry satu transaksi; demo memakai aliran kartu lokal. Jalur dasar lulus. Tarif wave BF per SKU/ukuran ditolak WAVE_SKU_RATES; tidak ditutup oleh uji dasar. |
| Laundry | T | T | Kirim/terima, vendor, jasa, invoice, klaim/cuci ulang memakai status dan jumlah Native; demo mengubah state lokal. Current CP17 menguji klaim/rewash Native; browser positif penuh dipertahankan dari audit lama, belum diulang untuk seluruh rantai final. |
| QC & Final SKU | T | T | Good/BS/final SKU mengacu penerimaan dan PCS siap Native; demo memproses seed lokal. Tidak ada fresh browser POST QC pada kandidat ini. Demo pada 390 px melebar ke 669 px (SOL-R1-004). |
| Susun Nota FG | T | B | DISPOSABLE memakai Nota posted/eligible Native dan konfirmasi; demo drag/drop lokal. UAT berhenti pada layar batas. UAT tidak menyediakan layar transaksi aktif; pergantian mode perlu bukti/pekerjaan CP7C. |
| Barang BS & Rework | T | T | Tujuan BS/rework, jumlah selesai dan upah mengikuti Native; demo memakai state lokal. RWK01 Native lulus termasuk sebagian selesai saat kasus OPEN; tidak ada fresh browser penyelesaian BS/rework. |
| Ringkasan Gudang | D | D | Ringkasan gudang tetap angka contoh di kedua mode. Tidak ada layar ringkasan gudang tersambung; bukan saldo Native. |
| Pembelian & Penerimaan | T | T | Penerimaan, harga estimasi/final, GRNI, invoice dan retur via command Native, bukan state demo. P09 positif, penolakan, koreksi dan lost reply terikat cakupan provider. |
| Bahan & Roll | T | T | Roll fisik/lokasi/saldo, transfer, UOM dan hitung fisik dibaca/diposting Native; demo angka lokal. Tidak mewakili seluruh kombinasi roll, cutoff dan rantai produksi baru. |
| Kain kantong | T | T | Jalur Native kain kantong dan pembukaan impor; di demo hanya pemberitahuan, bukan simulasi transaksi. BE Native T1 lulus; belum fresh browser positif kain kantong pada tumpukan CP7 akhir. |
| Aksesori | T | T | Layanan aksesori Native memakai stok, BOM/rate, status dan izin; demo angka/state lokal. Browser P09 transfer aksesori terkait bukan bukti seluruh layanan halaman ini selesai. |
| Ringkasan Barang Jadi | T | T | Saldo SKU/ukuran/lot dari Native; panel analisis/rencana/reminder/Tanya AI dibatasi izin dan hanya dibuka sesuai mode. Uji pembaca P10 tidak menggantikan seluruh P19/K2–K6. Bukti lama keluarga itu dipertahankan dengan label historis. |
| Mutasi Barang Jadi · Vivo | T | T | Buku berisi sumber transaksi, lineage koreksi dan saldo berjalan Native; demo kartu/mutasi lokal. Filter Vivo diuji oleh provider buku; bukan bukti seluruh varian koreksi baru. |
| Mutasi Barang Jadi · Widie | T | T | Buku Widie memakai pembaca Native yang sama dengan filter merek; demo buku lokal. Saksi provider buku dibagi dua menu, tidak dihitung dua oracle independen. |
| Kartu Stok FG | T | T | Kartu kronologis dan sumber efektif dari RPC; demo memakai mutasi contoh. STK01 Native reopen/repost lulus. Inventory 403 bukan bukti kartu berisi semua transaksi positif. |
| Stock Adjustment | T | T | Hitung fisik/penyesuaian punya lokasi, waktu, alasan, versi dan writer Native; demo lokal. Belum satu browser yang melakukan adjustment di tengah seluruh rantai 13 tahap. |
| Ganti Merek | T | T | Konversi memakai lot sumber, snapshot identitas dan pembalik Native; demo lokal. BE 16 Native lulus pada CP6 T1; belum fresh browser konversi→jual→HPP pada final CP7. |
| Penjualan & Invoice | T | D | DISPOSABLE memakai draft/reservasi/invoice Native dan seri lusin per ukuran; UAT masih komponen demo. D14-5/12 lulus termasuk 4/4/4, 3/5/4, sisa PCS dan SKU satu ukuran; UAT belum tersambung. |
| Semua Invoice | T | D | DISPOSABLE mengarahkan daftar invoice ke workspace Native; UAT masih daftar contoh. Tidak ada saksi positif khusus navigasi menu Semua Invoice; keluarga invoice terkait bukan bukti menu khusus ini. |
| Retur Penjualan | T | D | DISPOSABLE memakai retur sumber Native dan PCS/AR/kredit yang ditinjau; UAT demo. UAT tidak mengirim command; kombinasi koreksi/pembalikan seluruh rantai dibatasi bukti yang disebut. |
| Pembayaran Pelanggan | T | D | DISPOSABLE mencatat pelunasan Native serta koreksi/reversal; UAT contoh. SOL-R1-001: koreksi setelah dana dipakai gagal walau saldo akhir positif; saksi baru Native + real Auth HTTP, bukan browser. |
| Riwayat Pelanggan | D | D | Riwayat pelanggan tetap contoh pada kedua mode. Tidak ada layar riwayat tersambung. |
| Ringkasan Keuangan | T | D | DISPOSABLE membaca ringkasan Native; UAT memakai FinancePages dengan Rp284,6 jt contoh tanpa label simulasi lokal. KNOWN-UI-MODE: angka contoh terlihat sebagai saldo buku; harus beres sebelum penggunaan Enteng. |
| Kas & Bank | T | D | DISPOSABLE membaca mutasi/akun kas Native, sumber dan tanggal; UAT ledger contoh. D14-3 pengeluaran biasa lulus; koreksi pemasukan tetap bermasalah. |
| Hutang Supplier & Vendor | T | T | Utang supplier/vendor, sisa sumber dan kredit dipilih dari Native; demo angka lokal. Saksi kredit supplier bukan bukti browser seluruh invoice/klaim laundry. |
| Piutang Pelanggan | T | D | DISPOSABLE membaca AR/kredit per pelanggan dari Native; UAT angka contoh. Koreksi pembayaran sah yang tertahan menghalangi pembaruan AR/uang yang diperlukan. |
| Payroll & Kasbon | T | D | DISPOSABLE memakai Nota/upah/absensi/kasbon Native; UAT menampilkan payroll contoh tanpa label simulasi lokal. D14-2/6/11 Native lulus. UAT contoh; rework OPEN dibuktikan Native, bukan browser rantai penuh. |
| Absensi & Rate Harian | T | D | DISPOSABLE membuat roster/rate/absensi posted Native; UAT operasi contoh. Pool HPP absensi dan keseluruhan lintas Nota belum dibuktikan satu browser berantai. |
| Nota Ambil Aksesori | T | T | Nota pengambilan aksesori, tanggal, stok/biaya dan potongan mandor memakai Native; demo lokal. Belum fresh browser Nota Ambil→potongan payroll→bayar dalam satu rantai. |
| HPP & Rekalkulasi | T | T | Recost Native dan G2 selesai PO/WIP nol; demo preview versi biaya lokal. G2 dasar lulus. Demo 390 px melebar 627 px (SOL-R1-005); QC→G2 satu browser penuh belum ada. |
| Jurnal & Transaksi Lain | T | D | DISPOSABLE membaca GL dan menulis transaksi lain lewat Native; UAT jurnal contoh. Misc-income correction reverse dahulu berisiko akar SOL-R1-001; dampak ini baru trace kode, belum runtime. |
| Laporan & Tutup Buku | T | D | DISPOSABLE laporan bertanggal, analisis, unduhan dan periode Native; UAT laporan contoh. Angka Native positif teruji pada fixture. UAT angka contoh; tidak mewakili laporan data hosted. |
| Kain & Benchmark | D | D | Kain, benchmark dan simpan memakai seed/state contoh di kedua mode. KNOWN-DAILY-MASTER: tidak ada penambahan/perubahan master harian Native di menu ini. |
| Aksesori & Harga Mandor | D | D | Kategori aksesori/harga mandor tetap simulasi di kedua mode. KNOWN-DAILY-MASTER; import awal dan master khusus bukan pengelolaan harian lengkap. |
| Produk & SKU | T | T | SKU/range/ukuran/riwayat kontrak memakai Native; demo state master lokal. Retained audit BF sebelumnya; tidak ada fresh browser positif master SKU di putaran ini. |
| Pelanggan | D | D | Pelanggan tetap seed/state lokal dan tombol simpan simulasi. KNOWN-DAILY-MASTER: pelanggan baru harian belum punya penulisan Native di menu ini. |
| Supplier & Vendor | D | D | Supplier/vendor umum tetap seed/state lokal. Master laundry khusus tidak menggantikan master supplier/vendor umum harian. |
| Mandor | D | D | Mandor tetap seed/state lokal. Mandor baru/hak/rate lintas produksi perlu jalan harian Native. |
| Gudang & Lokasi | D | D | Gudang/lokasi tetap seed/state lokal. Gudang/lokasi baru harian tidak tersimpan Native melalui menu ini. |
| Pola | T | T | Mode tersambung membaca/menulis Pola dengan izin, versi, rentang dan pencarian; demo lokal. Inventory 403 + source trace saja; tidak ada fresh real Auth browser positive master Pola. |
| Reminder | D | D | Menu Reminder mandiri tetap simulasi; panel reminder terhubung berada di Ringkasan FG. Jangan menyamakan layar mandiri ini dengan seluruh mesin P16/K yang mempunyai bukti historis sendiri. |
| Pengguna & Hak Akses | T | T | Mode tersambung memakai workspace izin server, peran dan perubahan akses; demo lokal. Native/Auth keluarga akses punya bukti; tidak ada fresh positive browser menu administrasi ini. |
| Pengaturan ERP | D | D | Pengaturan ERP mandiri tetap contoh/state lokal. Pengaturan kebijakan terhubung khusus tidak otomatis membuat menu ini tersambung. |
| Impor data awal | T | T | Impor awal CSV, validasi, batch, posting dan lanjutan saldo awal Native; demo hanya pemberitahuan. Saksi subset payroll/refund awal; bukan restore backup CP2 atau seluruh cutover. |
| Tutup Periode | D | D | Menu Tutup Periode mandiri tetap simulasi; command periode terhubung ada di Laporan & Tutup Buku. P13 periode teruji di menu finance-reports, tidak mengubah status menu mandiri ini. |
| Audit Trail | D | D | Audit Trail mandiri tetap contoh di kedua mode. Tidak ada layar audit trail umum tersambung; lineage khusus transaksi tidak mewakili menu umum ini. |

UAT: **23 T, 23 D, 1 B, 1 N**. DISPOSABLE: **35 T, 12 D, 1 N**. Jumlah ini rute sumber + observasi browser, bukan persentase fitur siap pakai. JSON menyimpan isian/tombol/RPC aktual, perbedaan, sumber, saksi positif dan batas masing-masing menu. Nilai `viewport` mentah berupa angka 1440/390 karena metadata tertimpa `innerWidth`; nama desktop/phone tetap terikat ID kasus.

# Astra — kelanjutan audit aplikasi CP1–CP7

Kandidat **dfab13bf62398a69a02bf6221c06d29075e5e40b**; tree **886f83312958b53781a450a4ea2a8fb2147b3be3**. Dokumen ini melengkapi laporan pertama yang dikunci pada commit **3a3da9ef2c1662da85c016920403bdb63a0de3a8**. Laporan pertama tidak diubah. Pernyataan selesai di laporan pertama hanya sah untuk lingkup yang tertulis di sana; pemeriksaan aplikasi tambahan di sini dikerjakan setelah owner meminta lingkup itu dituntaskan.

**Audit lanjutan selesai; vonis tetap TAHAN penerimaan akhir/pemasangan Enteng.** Keberhasilan tambahan tidak menutup dua cacat penjualan, perbedaan aktivasi Enteng, master harian, atau cacat penyajian selesai PO dari laporan pertama. Auditor tidak memperbaiki produk.

## Bukti tambahan yang sudah selesai

### Lima belas perjalanan browser dari sumber penulis, dijalankan Astra

Run **38793203625**, job **116622793225**, control **fca97be34ce8ed1d1d84d9e1876f31e315fa64f4**. Manifest mengunci SHA-256 setiap modul dan ID sebelum eksekusi. **15 PASS**, bukan 15 oracle baru Astra. Label `INDEPENDENT_EXECUTION_WRITER_ORACLE` dipertahankan.

| Perjalanan | Kasus | Hasil sebelum pembersihan |
|---|---:|---|
| Penerimaan bahan desktop/HP | 2 | Satu gerakan 10, GRNI 100, AP 0; lost reply HP replay persis sama. |
| Retur dan kredit supplier | 1 | stok 6/4→6/2, AP 80, alokasi kredit pindah dan inverse; stok kembali 6/4. |
| Susun Nota FG desktop/HP | 2 | Dua kartu, qty 3, upah 6000; POST CALCULATED, tidak membayar atau menambah FG/HPP. |
| Pelunasan payroll desktop/HP | 2 | kerja 6000+absensi 100→kas 6100; persetujuan, pembayaran dan pembalikan lewat UI; jurnal kembali netral. |
| Roster/rate/absensi→nota→payroll | 2 | Pekerja/rate dan absensi dibuat melalui UI, absensi 125, koreksi100 lalu inverse; kas 6125; konsumsi sumber dan pembalikan diuji. |
| Impor saldo awal→nota→payroll | 2 | Buat/periksa/sahkan CSV, alokasi tiga sumber, bayar 6060; hanya carry baru5 diakru; saldo awal/carry/jurnal pulih sesudah inverse. |
| BS→rework dan rewash SKU | 2 | Partial belum membuat FG, complete menghasilkan 2 GOOD +2 BS; rework inverse mengembalikan FG 0; rewash UNKNOWN kemudian biaya 200/rate 50. |
| Nota aksesori desktop/HP | 2 | SAVE/POST/inverse nyata:7×3,25 = 22,75, stok 20/3; inverse memulihkan stok dan seluruh akun; HP memulihkan balasan hilang. |

Setiap kasus memakai Auth dan PostgREST nyata pada clone lokal. Browser HP memakai viewport390×844 dan beberapa kasus timezone America/Los_Angeles, sementara waktu bisnis tetap WIB. Restore CP6, batas katalog, advisor, Auth, sesi dan pembersihan lulus; database browser tersisa 0. Ini bukan uji hosted.

### Oracle Astra: nota aksesori sampai kas

Run **38793203672**, job **116622792645**, ID **ASTRA_CHAIN_ACCESSORY_NOTA_TO_CASH: PASS**. Penerimaan/transfer dan dua sumber kerja adalah fixture Native sah. Semua langkah sesudahnya—buat/sahkan nota aksesori, susun/sahkan Nota FG, hitung sumber, setujui dan bayar payroll—dijalankan lewat Chromium.

Satu mandor yang sama menerima7 aksesori×3,25 = **22,75**. Dua kartu kerja memberi **6000**. Payroll memilih tepat satu potongan **22,75**, membayar **5977,25**, dan status nota aksesori berubah UNALLOCATED→ALLOCATED→SETTLED. Debit/kredit jurnal pembayaran masing-masing5977,25; jurnal potongan masing-masing22,75. Utang mandor dan piutang aksesori menjadi 0. Stok gudang20/3 serta hash gerakan/HPP tidak berubah oleh nota/payroll. Ini menutup celah aplikasi **S4 untuk perjalanan yang dideklarasikan**.

Job gabungan tetap **INCOMPLETE**, karena kasus produksi di job yang sama berhenti pada locator. PASS kasus payroll tidak diubah menjadi PASS seluruh job; kasus berhasil ini tidak dijalankan ulang.

### Oracle Astra: potongan sampai FG

Run **38797114166**, job **116636308078**, control **4fff5c63240280e12fcd998c46ec83b6b504d438**, ID **ASTRA_CHAIN_CUT_TO_FG: PASS**. Satu PO dan group yang sama menjalani keenam tahap bisnis lewat UI: POST potongan, pickup mandor, catat selesai jahit, kirim laundry, terima laundry, POST QC/Final SKU.

Fixture hanya menyiapkan penerimaan bahan, master/rate, PO dan draft potongan. Awalnya bahan 100/nilai 1000; sesudah potong 60, sisa **40/nilai 400** dan WIP 600. Sesudah jahit **60 pcs**, upah **120** dan WIP 720. Surat kirim memiliki tepat **60 pcs** berstatus kanonik SENT; penerimaan tercatat satu kali. QC menghasilkan **60 pcs FG** pada PO yang sama; sisa bahan dan upah tetap 40/400 dan 60/120. WIP akhir **0**; PO masih berstatus QC, belum FINISHED, dan riwayat selesai PO tetap 0. Trace menyimpan identitas PO/group/batch/delivery dan enam keadaan sebelum cleanup.

Ini menutup celah POST aplikasi B2/B3/B7 untuk perjalanan tersebut dan menghubungkan B4/B5 dalam satu rantai nyata. Tidak mengklaim pembuatan draft awal, pembayaran supplier/vendor, selesai PO, penjualan atau tutup periode ikut dilakukan dalam kasus ini; bukti tahapan itu ditunjuk terpisah. Ketiga attempt INCOMPLETE alat sebelumnya tetap tersimpan.

### Inventaris tiga mode setelah workspace benar-benar siap

Run **38794405101**, control **8344fbc171b6a115ac9efa1730c5f6b4cf3a499d**: **288 PASS** = 48 menu × desktop/HP × 3 mode. Tidak ada fallback “Menyiapkan…”, overflow horizontal, pageerror, atau RPC 4xx/5xx dalam pengamatan. Ketiga mode lulus restore dan advisor. Inventaris lengkap, kontrol awal, nama RPC, hash body dan screenshot ada di `SCREEN_RUNTIME_COMPARISON.md/.json` serta `CASE_LEDGER.json`.

Hasil runtime tepat menguatkan hitungan source: **35 menu memanggil RPC pada DISPOSABLE_TEST; 23 pada mode Enteng; demo 0.** Sebanyak **23 isi halaman Enteng identik dengan demo**. Dua sisanya tanpa RPC adalah pemberitahuan Dashboard dan pagar Susun Nota FG. Ini pengamatan halaman awal, bukan sertifikasi semua aksi CRUD.

- Penjualan Enteng menampilkan “SIMULASI UX / Belum menulis backend” dan tidak memanggil RPC; tes connected membaca `erp_cp7_get_sales_v1` (200).
- Ringkasan Keuangan Enteng menampilkan kas contoh **Rp284,6 juta** dan laba **Rp133,2 juta**, tanpa tanda SIMULASI pada hero. Isi sama persis dengan demo dan tidak membaca RPC. Badge global “UAT · MODUL TERPILIH LIVE” tidak menjelaskan bahwa halaman ini masih contoh.
- Payroll Enteng juga sama dengan demo dan tidak membaca RPC. Tes connected membaca workspace payroll (200), sementara kasus transaksi terpisah membuktikan pelunasan nyata pada clone.
- Susun Nota FG Enteng secara eksplisit menolak writer karena belum aktif; tes connected memuat kartu kerja server.
- Master Pelanggan, Supplier/Vendor, Mandor, Gudang/Lokasi, Kain/Benchmark dan Aksesori/Harga Mandor tetap halaman contoh. Misalnya Pelanggan menulis “Simulasi lokal · belum menulis backend” dan tidak memanggil RPC di seluruh mode.

Dengan demikian ASTRA-C17-03/04 sekarang memiliki **bukti Chromium independen pada build mode Enteng**, selain source/DOM sebelumnya. Tidak menyatakan backend hosted sudah dipasang atau diuji. Screenshot pilihan tersimpan di `screenshots/`.

## Koreksi alat auditor dan status asli

Semua attempt tersimpan. Tidak ada produk, hasil yang diharapkan, ID kasus, seed, timeout, atau guard yang dilonggarkan demi hijau. `TOOL_QUALIFICATION.md` menghubungkan setiap koreksi dengan bukti sebab dan diff alat sesuai Pro Max §16.3.

1. Run 38791612672: empat job berhenti sebelum kasus karena folder tujuan copy belum ada.
2. Satu retry pre-case 38792368517: empat job kembali berhenti sebelum kasus; YAML melipat newline sehingga mkdir menerima argumen cp/-R. Run pertama integration 38792810239 mewarisi cacat yang sama. Kesembilan job tetap gagal/INCOMPLETE alat.
3. Sesudah koreksi dan pemeriksaan parse/bash/copy lokal, run 38793203625 menghasilkan 288PASS mentah inventaris. **156 tangkapan masih fallback lazy-loading**, sehingga tidak diberi kredit halaman siap. Seluruh inventaris dikualifikasi kembali; raw status tidak dihapus. Hasil navigasi awal tidak dihitung dua kali sebagai bukti baru.
4. Run 38793203672 produksi mencapai POST potongan nyata: bahan 100/nilai 1000→40/nilai 400, WIP 600. Locator exact “Mandor” gagal karena nama aksesibel label juga memuat penjelasan bahwa mandor dikunci. Bukti body/screenshot dan source membuktikan elemen ada. Kualifikasi memperbaiki locator menjadi combobox tunggal dalam `.cpick-setup`, nama diawali Mandor, lalu memastikan nilai mandor benar. Kasus dan oracle asli dipertahankan.

5. Run 38794704824 melanjutkan sampai pickup, jahit dan pengiriman laundry. Reader auditor keliru mencari status POSTED pada surat kirim, padahal writer beku menetapkan SENT. Reader dibetulkan ke status kanonik SENT dan ditambah pemeriksaan qty surat kirim tepat 60. INCOMPLETE pertama tetap disimpan; angka bisnis yang diharapkan tidak dilonggarkan.

6. Run 38796017970 membuktikan seluruh langkah sampai penerimaan laundry dan antrean QC 60 pcs. Locator exact pada label bersarang kembali berhenti sebelum QC POST; dipersempit ke select tunggal dalam label yang terlihat, dengan pemeriksaan nilai group. Bukti INCOMPLETE dan lima checkpoint berhasil dipertahankan.

Pembersihan berhasil bukan bukti bisnis berhasil. Trace dan jurnal sebelum cleanup tersimpan terpisah; metadata restore/Auth/session/database juga disimpan. Tidak ada workflow yang masih berjalan boleh dianggap selesai dalam receipt akhir.

## Perubahan cakupan sambungan

Rujuk `CHAIN_CLOSURE.md` untuk seluruh B1–B13/S1–S7, bersama laporan pertama. Penerimaan seluruh aplikasi belum diberikan; setiap hasil dibatasi jalur yang dijalankan.

- **S4 ditutup untuk alur yang dideklarasikan:** nota aksesori → potongan payroll → kas pada mandor yang sama, lewat UI, dengan jurnal/stok/HPP dibaca ulang.
- **S3 diperkuat:** roster/rate/absensi → nota → persetujuan → kas → inverse benar-benar berjalan desktop/HP. Lifecycle pool HPP absensi tetap tidak mempunyai perjalanan UI lengkap yang ditemukan.
- **S5 diperkuat:** pembuatan rework/rewash, partial, complete, SKU hasil, koreksi harga dan inverse ditunjukkan lewat browser. Penyatuan seluruh varian BS → nota → kas dalam satu kasus tetap tidak disertifikasi; hak upah rework dan settlement punya bukti masing-masing dari putaran ini/laporan pertama.
- **S7 diperkuat:** CSV saldo awal → alokasi sumber lama → payroll/kas → inverse berjalan desktop/HP. Ini tidak menyertifikasi satu perjalanan impor WIP → produksi → penjualan → kas.
- B1, S1/S2 dan langkah nota/payroll punya tambahan browser independen. Hasil perbaikan lama B6/B8–B13 tetap sesuai laporan pertama; tidak dijalankan ulang tanpa alasan.

Kekurangan fungsi Enteng/master dan lifecycle pool adalah pekerjaan produk. Kombinasi kalender, semua role, seluruh variasi impor WIP/BS, dan close/adjustment di tengah setiap perjalanan belum diuji secara menyeluruh. Keterbatasan itu dinyatakan terbuka; tidak diberi label PASS dari gabungan kasus yang berbeda.

## Vonis tujuh tahap

| Tahap | Disposisi setelah kelanjutan |
|---|---|
| CP1 | Hasil baseline/fingerprint dari laporan pertama tetap berlaku. Tidak ada perubahan produk. |
| CP2 | Bukti restore lama diterima bersyarat sesuai keputusan yang sudah ada; pemulihan dengan engine asli/Storage belum disertifikasi. CP7C tetap HOLD, bukan kasus yang diam-diam diabaikan atau diberi PASS. |
| CP3/3.5 | Perbaikan FIN01/HPP01 pada laporan pertama tetap lulus; bukti aplikasi roster/absensi→nota→kas serta saldo awal→payroll ditambah. Lifecycle pool HPP absensi belum tersedia sebagai perjalanan UI lengkap. |
| CP4/4.5 | Bukti HPP/akses/pola tetap qualified; penyajian status selesai PO tetap perlu diperbaiki. 82 EXECUTE tetap keputusan CP7C, tidak dibuka ulang. |
| CP5 | Bukti perbaikan stok/laundry/BS dari laporan pertama dan browser rework/rewash ditambah. Rincian rantai produksi ada di atas. |
| CP6 | Baseline/regresi/ledger/cutover dari laporan pertama tetap berlaku beserta disposition historis dan cacat entry point arsip. |
| CP7 | **TAHAN.** Kelengkapan pemeriksaan tidak berarti fitur lengkap atau izin operasi. Temuan produk terbuka perlu revisi penulis dan uji kandidat perbaikan. |

## Yang masih harus dikerjakan penulis sebelum penerimaan

- Pisahkan seri penjualan berdasarkan identitas merek/SKU; blokir simpan selama ukuran seri masih dimuat. Bukti kedua cacat tetap DOM+source dari laporan pertama, tidak dipromosikan menjadi posting lintas merek nyata.
- Cocokkan pra-kondisi dan pesan selesai PO dengan kondisi fisik dan status biaya server.
- Selesaikan/putuskan aktivasi Enteng dan alur master harian; beri tanda contoh yang selalu terlihat. Build lokal dengan jalur Enteng tidak membuktikan paket telah dipasang di hosted.
- Perbaiki entry point G01/T2 yang masih mengandalkan arsip kedaluwarsa, dengan tetap mempertahankan batas apply/oracle.
- Tutup keterbatasan aplikasi yang disebut eksplisit dalam matriks sambungan; lifecycle yang tidak tersedia adalah pekerjaan produk, bukan tugas owner mengetik SQL.
- Backup/Drive, revoke/exposure gate dan pemulihan CP2 baru dilanjutkan ketika owner membuka CP7C. Keputusan lama tidak ditanyakan ulang.

`feature_complete=false`; `production_go=false`. Tidak ada akses/mutasi hosted, Drive, main, deployment atau cabang penulis. Belum membaca hasil auditor lain dari putaran gabungan ini. Bukti lama dan tambahan memiliki ID/origin masing-masing dan tidak dijumlahkan sebagai ribuan tes baru Astra.

## Penguncian dan penghitungan

Seluruh **20 job pada 9 run** selesai. Himpunan akhir tepat **305 ID**: 17 kasus transaksi (2 oracle Astra, 15 oracle penulis dieksekusi Astra) dan 288 inventaris halaman awal. Tidak ada ID kanonik hilang/duplikat. seluruh 305 hasil kanonik PASS untuk lingkup masing-masing; **596 rekaman mentah** tetap memuat 593 PASS dan 3 INCOMPLETE. 288 rekaman inventaris awal yang dikualifikasi ulang tidak dihitung sebagai kasus baru, dan 156 fallback di dalamnya berstatus protokol INCOMPLETE. 9 kegagalan alat sebelum kasus tidak ditambahkan sebagai PASS.

Receipt, ledger, laporan gate, SHA256 log/archive dan screenshot pilihan berada dalam folder ini. Seluruh bukti bersumber pada kandidat beku, database sekali pakai; first-report lock 21 berkas dan direktori produk diverifikasi tidak berubah. `REPORT_LOCK.json` memuat hash berkas final dan waktu penguncian.

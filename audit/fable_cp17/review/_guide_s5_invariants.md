## 5. Katalog invarian (hukum yang tidak boleh dilanggar)

Setiap invarian wajib diuji dari dua arah: kasus yang harus lolos dan kasus yang harus ditolak. Auditor menandai setiap invarian `PASS / FAIL / INCOMPLETE` beserta buktinya.

### 5.U Uang dan jurnal

- **INV-U01** Setiap jurnal seimbang: jumlah debit = jumlah kredit, per jurnal dan per tanggal ekonomi.
- **INV-U02** Satu kejadian bisnis menghasilkan tepat satu efek. Mengulang permintaan yang sama tidak menambah efek (INV-C01).
- **INV-U03** Pembalikan adalah kebalikan persis aslinya per akun dan dimensi (pelanggan, vendor, mandor, PO, produk). Tanggal pembalikan mengikuti aturan tanggal bisnis.
- **INV-U04** Saldo buku besar akun kontrol = jumlah subledger (utang supplier, piutang pelanggan, utang upah, uang muka, GRNI).
- **INV-U05** Saldo kas/bank = jumlah semua mutasi kas yang diposting. Tidak boleh negatif kecuali kebijakan yang disahkan mengizinkan.
- **INV-U06** Tidak ada aritmetika float untuk uang. Pembulatan sen dilakukan sekali, pada titik yang ditentukan kontrak (per baris atau per dokumen, konsisten). Selisih sen dialokasikan secara deterministik.
- **INV-U07** Pembayaran tidak boleh melebihi tagihan. Kelebihan bayar menjadi kredit atau uang muka yang tercatat, tidak hilang.
- **INV-U08** Mengubah pembayaran tidak menciptakan hak kerja atau HPP baru (pemisahan keuangan).

### 5.S Stok

- **INV-S01** Saldo stok = jumlah semua mutasi, per bahan, roll, lokasi, dan SKU/lot.
- **INV-S02** Tidak ada stok negatif pada urutan kronologis, termasuk saat pencatatan mundur (backdate) kecuali ada izin pengganti eksplisit, dan izin itu harus tercatat.
- **INV-S03** Transfer antar gudang berjumlah nol untuk total, dan nilainya ikut pindah.
- **INV-S04** Identitas roll fisik tetap. Pemakaian, transfer, dan riwayat menunjuk roll yang sama, termasuk sesudah koreksi.
- **INV-S05** Konversi satuan memakai snapshot faktor yang berlaku saat transaksi.
- **INV-S06** WIP terkonservasi: masuk = keluar + susut/BS + sisa. Satu PCS dihitung sekali.
- **INV-S07** Barang jadi per SKU/ukuran/lot terkonservasi dari QC sampai penjualan dan retur.

### 5.H HPP dan biaya

- **INV-H01** Nilai persediaan = Σ(jumlah × biaya satuan) dan cocok dengan saldo akun persediaan.
- **INV-H02** Biaya mengalir dan terkonservasi: bahan → WIP → barang jadi → HPP penjualan. Tidak ada biaya yang muncul atau hilang tanpa sumber.
- **INV-H03** Recost bersifat kronologis dan bertanggal dari barang dan pergerakannya (keluarga AY/AZ), bukan dari tanggal koreksi.
- **INV-H04** Harga perkiraan vs final: GRNI harus nol sesudah semua invoice final. Invoice terlambat mengoreksi GRNI, utang, dan HPP pada tanggal ekonominya, tanpa menciptakan stok.
- **INV-H05** Koreksi biaya merambat ke semua posisi barang: sisa bahan, WIP, barang jadi, terjual, dan diretur. Masing-masing pada tanggalnya sendiri.
- **INV-H06** HPP yang belum pasti, misalnya harga laundry belum diketahui, ditandai belum pasti dan memblokir aksi yang bergantung padanya (contoh: LAU-DEC04 memblokir penjualan).

### 5.P Utang, piutang, dan kas

- **INV-P01** Sisa utang/piutang per dokumen = total − pembayaran − retur/kredit yang dialokasikan. Tidak boleh negatif tanpa dokumen kredit.
- **INV-P02** Uang muka hanya dipakai sampai sisanya, untuk pihak yang sama, dan pada tanggal ≥ tanggal sumbernya.
- **INV-P03** Jatuh tempo dan aging dihitung dari dokumen yang aktif. Dokumen yang dibalik tidak ikut terhitung.

### 5.T Tanggal dan periode

- **INV-T01** Tanggal bisnis memakai WIB (`erp._cp3_business_date`). Transaksi sekitar tengah malam WIB tidak boleh pindah hari karena UTC.
- **INV-T02** Periode tertutup tidak berubah diam-diam. Koreksi masuk dengan tanggal ekonomi asal dan tanggal pengakuan di periode terbuka, sesuai aturan Native dan `cp7_period`.
- **INV-T03** Tidak ada kejadian fisik di masa depan. Tanggal datang tidak boleh sesudah pemakaian pertama.
- **INV-T04** Non-kebocoran waktu: menambah fakta yang baru diketahui sesudah cutoff tidak mengubah hasil "as-known" yang lama. Restatement mendapat revisi baru.

### 5.L Laporan

- **INV-L01** Setiap angka laporan berasal dari sumber kebenaran yang sama dengan buku besar dan stok, dan cocok dengan jumlahnya.
- **INV-L02** Laporan per tanggal bisa direproduksi. Laporan lama immutable; revisi menjadi dokumen baru yang tertaut.
- **INV-L03** **"Tidak diketahui" bukan nol.** Data yang tidak terbaca atau belum lengkap tampil sebagai "belum diketahui", tidak pernah 0 atau kosong yang terlihat seperti 0.
- **INV-L04** Laporan keuangan tidak boleh berstatus READY palsu. Kalau ada komponen yang belum pasti (HPP, invoice, saldo awal), statusnya ikut belum pasti.
- **INV-L05** Perbandingan periode harus sebanding (hari penuh vs hari penuh), atau diberi label yang jelas.
- **INV-L06** Membaca laporan tidak mengubah data bisnis apa pun. Bandingkan seluruh tabel operasional dan sequence sebelum dan sesudah.
- **INV-L07** Data di luar izin pengguna tidak muncul di angka, total, alasan, cache, atau prompt AI.

### 5.R Rekomendasi produksi, perencanaan, model, dan AI

- **INV-R01** Rekomendasi hanya dari data yang berlaku dan lengkap. Kalau masukan basi, sebagian, atau tidak diketahui, rekomendasinya ditandai "perlu cek data", bukan dihitung dengan angka karangan.
- **INV-R02** Setiap kartu tindakan menjawab: kerjakan apa, SKU/ukuran, berapa PCS, paling lambat kapan, kenapa sekarang, sumber apa, dan apa yang belum pasti (`06_RUSUK_KEBUTUHAN_OWNER.md` §5).
- **INV-R03** Urutan prioritas bisa dijelaskan: gap sebelum pasokan siap → deadline nyata → aksi yang lebih cepat menutup gap → ukuran yang kurang → ID stabil. Laba tidak boleh menyembunyikan gap mendesak.
- **INV-R04** Netting tidak menghitung dua kali. Draf penjualan sudah mengurangi stok barang jadi, jadi forecast sisa tidak menghitung penjualan itu lagi. Kelebihan ukuran lain tidak menutup kekurangan ukuran yang tidak bisa dikonversi.
- **INV-R05** Pasokan yang mundur tidak memperbaiki gap sebelum tanggal datang yang baru.
- **INV-R06** Model adaptif hanya dipromosikan oleh selector yang lolos uji (M01–M08 dan positive promotion). Data tipis atau seri kembali ke baseline. Holdout luar tidak dipakai untuk tuning.
- **INV-R07** Tanya AI V1 hanya membaca proyeksi yang diizinkan. Prompt memuat asumsi, unknown, dan sumber. Tidak ada auto-send, auto-writeback, kunci API, atau data di URL.
- **INV-R08** Membaca atau menghitung rekomendasi tidak membuat reservasi atau efek bisnis. Menerapkan rencana hanya lewat command sah dengan validasi ulang.
- **INV-R09** Kebutuhan bahan = kebutuhan bersih dari model potong yang lolos uji. Kalau yield atau model belum terkualifikasi, tampilkan rentang atau "belum pasti", bukan satu angka yang terlihat pasti.

### 5.K Koreksi transaksi dan riwayat

- **INV-K01** Dokumen asal yang sudah diposting tidak diubah isinya. Koreksi = pembalik Native pada waktu sumber + pengganti yang persis + lineage privat.
- **INV-K02** Efek koreksi jatuh pada tanggal ekonomi aslinya. Selisih tidak dicatat sebagai keuntungan atau kerugian hari ini, kecuali barang yang memang terjual hari ini.
- **INV-K03** Pemetaan baris lama → baru harus eksplisit (lineage per baris), bukan dicocokkan lewat atribut yang bisa kembar.
- **INV-K04** Setiap penulisan langsung ke tabel Native di luar writer Native terdaftar, alasannya ditulis, dan tercatat di lineage (`docs/cp7/RECEIPT_CORRECTION.md` butir 4 dan dokumen yang setara milik GPT).
- **INV-K05** Draft terkait (invoice, retur, pembayaran, potong, transfer) memblokir koreksi dan disebut nomornya.
- **INV-K06** Koreksi berulang (R1, R2, …) menghasilkan satu dokumen berlaku dan satu baris efektif di kartu mutasi.
- **INV-K07** Tabel fakta dan buku (jurnal, mutasi stok, fakta recost, lineage) **append-only**: `UPDATE`/`DELETE` ditolak oleh trigger bahkan untuk peran admin aplikasi. Auditor wajib mencoba merusaknya di dalam savepoint dan mencatat penolakannya (kode, misalnya `MATERIAL_ADJUSTMENT_REVALUATION_FACT_APPEND_ONLY`). Pembalikan selalu baris baru.

### 5.C Konkurensi dan idempoten

- **INV-C01** UUID permintaan yang sama dengan payload yang sama menghasilkan satu efek. UUID sama dengan payload berbeda ditolak secara atomik.
- **INV-C02** Versi baris (`row_version`, `review_token`) dicek. Data yang berubah sesudah ditinjau ditolak.
- **INV-C03** Dua sesi bersamaan menghasilkan urutan yang sah, atau salah satunya ditolak. Tidak ada efek setengah jadi.
- **INV-C04** Kegagalan di langkah terakhir membatalkan semua efek (atomik).
- **INV-C05** Balasan yang hilang bisa di-reconcile memakai UUID yang sama. Writer tetap terkunci sampai statusnya pasti.
- **INV-C06** Setiap command meninggalkan database bersih: tidak ada advisory lock tersisa, tidak ada sesi tambahan, skema `public` tidak berubah, dan batas transaksi dipulihkan penuh. Runner ketat memeriksa ini sesudah **setiap** kasus (`full_boundary_restored`, `session_leaks`), dan kasus yang melanggar ditandai `FAIL` walau oraclenya lolos.

### 5.A Akses dan keamanan

- **INV-A01** Izin dicek di awal dan di akhir command. Izin yang dicabut di tengah jalan menggagalkan transaksi tanpa sisa.
- **INV-A02** Peran nol atau nonaktif ditolak (fail-closed).
- **INV-A03** Tidak ada kunci server di artefak klien. Gate artefak UAT dan scan rahasia harus lolos.
- **INV-A04** Advisor keamanan tidak menunjukkan temuan baru di luar daftar yang sudah ditinjau.
- **INV-A05** RLS dan grant persis seperti yang dideklarasikan; tidak ada akses langsung ke skema privat.

### 5.UI Layar

- **INV-UI01** Angka yang tampil = angka sumber. Tidak ada perhitungan uang di klien yang bisa berbeda dari server.
- **INV-UI02** Sesudah 403, balasan hilang, atau pemulihan bersama, fakta lama disembunyikan sampai dibaca ulang.
- **INV-UI03** Aksi yang mengubah uang atau stok punya langkah periksa dan konfirmasi. Penolakan ditampilkan jelas dalam bahasa Indonesia.
- **INV-UI04** Tampilan desktop, HP, dan iPad menampilkan angka yang sama.

### 5.Pol Kebijakan dan keputusan owner

- **INV-POL01** Nilai kebijakan adalah pengaturan di aplikasi dengan nilai awal `PENDING_POLICY_VALUE`. **Tidak ada angka karangan.**
- **INV-POL02** Kebijakan yang masih pending membuat fitur yang bergantung padanya berstatus belum siap, bukan memakai nilai default diam-diam.
- **INV-POL03** Satu aturan bisnis, satu sumber. Dua implementasi berbeda untuk hal yang sama adalah temuan.
- **INV-POL04** Skenario uji yang oraclenya bertentangan dengan keputusan owner yang lebih baru adalah skenario **basi**, bukan bug produk. Ia ditandai `SUPERSEDED_BY_OWNER_RULE`, dipindah ke historis, dan ditulis ulang pada tingkat yang benar. **Produk tidak pernah diubah supaya skenario lama lulus.** Contoh nyata: paket uji BF yang memasang tarif laundry pada SKU, ditolak produk sesuai D13 (tarif dari vendor).
- **INV-POL05** Hasil `COUNTEREXAMPLE` yang diterima owner lewat keputusan tertulis (contoh: sen per PO, T3 = A) tetap dicatat `COUNTEREXAMPLE` dengan rujukan keputusannya. Tidak direlabel `PASS`, tidak dihapus dari matriks, dan laporan menampilkan aturannya kepada pembaca keuangan.

### 5.M Saldo awal, impor, dan cutover

- **INV-M01** Saldo awal (stok, WIP, utang, piutang, uang muka, upah) sama persis dengan dokumen sumber cutover, per baris.
- **INV-M02** Impor bersifat idempoten dan menolak baris yang tidak valid dengan alasan. Tidak ada baris yang hilang diam-diam.
- **INV-M03** Sesudah cutover, semua cek integritas bernilai nol pelanggaran.
- **INV-M04** Paket rilis diuji **dari baseline hosted yang sebenarnya**, bukan baseline yang diasumsikan. Preflight baca-saja mencatat versi ledger hosted dan objek yang ada; pemasang membawa semua pendahulu yang hilang (contoh nyata: hosted masih v2.6.20 sehingga 30 berkas CP6 membutuhkan 28 pendahulu A–AB, total 58). Hash setiap berkas pendahulu diverifikasi auditor terhadap berkas asli di repo.
- **INV-M05** Pemasang menolak sebelum mengubah admission bila: baseline berbeda, katalog G-01 bergeser, berkas sudah terpasang, endpoint salah, bukan pemilik database, atau ada maintenance lain. Semua penolakan ini punya kasus uji masing-masing, dan pemasang **tidak pernah mematikan sesi orang lain**.

### 5.N Reminder dan notifikasi

- **INV-N01** Reminder dihitung dari fakta yang berlaku. Dokumen yang dibalik atau dibatalkan tidak memunculkan alert palsu, dan episodenya selesai dengan jelas.
- **INV-N02** ACK atau snooze tidak mengubah fakta bisnis.

### 5.D Detektor, alarm, dan cek integritas

- **INV-D01** Setiap detektor punya **kontrol positif dan negatif** di run auditor: diam pada buku yang benar (0 baris), dan **naik tepat +1** ketika auditor merusak satu angka di dalam savepoint, lalu kembali 0 sesudah rollback. Detektor yang tidak bisa dibuat berbunyi berlabel `TIDAK TERUJI`, bukan `PASS`.
- **INV-D02** Detektor yang berbunyi pada buku yang benar adalah **cacat detektor** (S1), bukan alasan membuang alarm: ia disetel ulang ke tingkat yang benar (per dokumen, per fakta), dan kontrol negatifnya dibuktikan lagi sesudah disetel. Mematikan alarm memerlukan keputusan owner tertulis.
- **INV-D03** Detektor membaca tabel yang **memang ditulis mesin yang berlaku**. Detektor lama yang membaca tabel yang tidak lagi ditulis mesin baru (contoh nyata: `material_cost_revaluation_state` vs fakta v2.6.20t) adalah temuan.
- **INV-D04** Nol pelanggaran dicatat **sebelum dan sesudah** setiap skenario §7, bukan hanya di akhir run.

**Batas kesimpulan detektor (klarifikasi Fable):** kontrol negatif §5.D membuktikan kepekaan terhadap kerusakan dan jalur yang benar-benar diuji; aturan tersebut tidak menjanjikan semua kesalahan pasti tertangkap. Oracle independen dan rekonsiliasi §13 tetap wajib. Penolakan perusakan tabel append-only membuktikan pencegahan INV-K07, bukan kepekaan detektor INV-D01.

---

## 6. Pola bug yang sering lolos (wajib dicari aktif)

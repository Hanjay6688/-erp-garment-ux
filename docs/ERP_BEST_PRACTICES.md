# Best practice ERP Garment (dari audit CP1–CP7 Fable, Astra, Sol)

Berlaku untuk penulis (Claude dan penulis cadangan) dan menjadi daftar periksa auditor. Setiap aturan diambil dari
temuan nyata; ID temuan disebut supaya alasannya bisa dilacak. Rincian per temuan: `docs/cp7/audit-candidate/
cp1-7-r2-20261016/CROSS_AUDIT.md`. Keputusan owner tetap di `docs/cp7/OWNER_DECISIONS_20261008.md` dan tidak
dibuka ulang oleh dokumen ini.

Disusun 16 Okt 2026. Tambahkan aturan baru di bagian yang sesuai, dengan ID temuan sumbernya.

## A. Uang dan buku besar

1. **Nilai keadaan akhir perintah, bukan keadaan setengah jalan.** Perintah majemuk (balik dulu, lalu pengganti) tidak
   boleh ditolak karena saldo sementara. Penjaga saldo dinilai di akhir transaksi; kunci tetap diambil saat baris
   ditulis supaya urutannya stabil. (SOL-R1-001)
2. **Periksa setiap dasar tanggal yang dilihat owner.** Bila buku punya tanggal ekonomi dan tanggal buku/pengakuan,
   penjaga dan detektor memeriksa keduanya; laporan tidak boleh menunjukkan angka yang penjaga anggap mustahil.
   (FABLE-013, D15-1)
3. **Penjaga tanpa detektor tidak cukup.** Setiap aturan "tidak boleh" punya detektor baca-saja untuk data lama, dengan
   kontrol 0 → +1 → 0 di uji. (FABLE-001, FABLE-013)
4. **Tanggal asli tidak diubah oleh koreksi; periode tertutup tidak dibuka otomatis.** Pengakuan terlambat dicatat
   pada tanggal buku yang sah dan diberi tanda. (D15-1)
5. **Jangan meloloskan uji dengan uang buatan.** Modal fixture hanya sebesar yang dibutuhkan kasus positif; kasus
   bank kosong tetap kosong. (SOL-001, G3)
5a. **Batas tanggal resmi dijaga di tabel, bukan di layar atau satu penulis saja.** Tanggal mulai pakai aplikasi
   (cutover) ditolak lewat trigger pada jurnal dan gerakan stok, sehingga penulis mana pun kena. Jalur yang sah lewat
   tanggal itu (impor saldo awal, invoice terlambat atas penerimaan saldo awal, pelunasan sesudahnya, pembalikan dokumen
   lama) dikecualikan dengan nama sumbernya yang jelas, tidak dengan bendera umum. Uji batas 00:00 WIB dan 23:59:59 hari
   sebelumnya, untuk jurnal dan stok. (FABLE-011, D15-5)

## B. Identitas data

6. **Kunci pengelompokan memakai semua dimensi keunikan, dari server, bukan teks tampilan.** Contoh: seri penjualan =
   merek + SKU, karena nomor SKU yang sama sah untuk Vivo dan Widie (`bf_skus_v1 UNIQUE(brand_id,sku)`). Pencarian
   berbasis teks tidak boleh menentukan barang mana yang masuk. (ASTRA-C17-01)
7. **Data master yang sudah dipakai transaksi tidak dihapus**; dinonaktifkan, dengan riwayat yang tidak bisa diubah.
   Mengubah master tidak mengubah identitas dokumen yang sudah diposting. (FABLE-017, D15-3)
8. **Tarif dan harga berversi dengan tanggal berlaku**; transaksi menyimpan snapshot tarif yang dipakai. (G1, D15-3)
8a. **Membetulkan versi pada tanggal yang sama bukan membuat versi baru.** Penjaga "sudah dipakai" diperiksa untuk
    versi tanggal itu sendiri; "sudah ada versi yang lebih baru" hanya untuk versi baru atau penghentian. Urutan yang
    salah memberi alasan penolakan yang salah. (CP17_R2_FABLE_D15_3, CI 38861916560)
8b. **Penyeragaman nilai (misalnya kode huruf besar) hanya saat membuat.** Saat mengubah, nilai tersimpan dibandingkan
    dengan aturan kesamaan yang sama dengan keunikannya (tanpa beda huruf) dan disimpan apa adanya; kalau tidak, data
    lama berkode huruf kecil yang sudah dipakai tidak bisa diubah sama sekali. (R2-03 gudang berisi stok, CI 38861916560)
8c. **Satu angka "sisa" per lingkup yang dijaga Native.** Bila Native membatasi per SKU (upah wave BF dibayar per SKU
    menurut potongan di ukurannya), layar meminta jumlah per SKU dan menghitung sisa per SKU dengan rumus yang sama
    (selesai dan hak bayar per komponen); satu jumlah untuk seluruh potongan tidak boleh dibayar dengan tarif dasar.
    (Sol R2-10 KNOWN-BF-WAVE)
8d. **Nomor urut berformat memakai lebar minimum, bukan panjang tetap.** `lpad(n,3)` memotong 1000 menjadi `100`.
    Uji perubahan jumlah digit (999 → 1000, 9999 → 10000) dan ruang nomor yang sudah penuh, termasuk dua sesi di batas
    itu. (ASTRA-R2-02, SOL-R2-001)

## C. Alur aplikasi lengkap

9. **Setiap entitas harian punya jalan dari aplikasi untuk dibuat, diubah, ditutup dan dibuka ulang** (atau keputusan
   owner tertulis bila tidak). Buat matriks per tabel Native: siapa penulisnya, layar mana yang memanggilnya.
   (SOL-R1-002 PO harian, FABLE-017 master, FABLE-014 buka ulang PO)
10. **Komentar dan dokumen yang menyatakan "tidak ada X" dicek ke katalog dulu.** (FABLE-014: komentar "no Native
    inverse" padahal `erp.reopen_production_order` ada)
11. **Uji rantai dimulai dari data yang dibuat lewat layar**, bukan PO/master/tarif yang disisipkan SQL. Fixture SQL
    hanya untuk isolasi, dan uji yang memakainya tidak boleh diklaim membuktikan operator bisa melakukannya.
    (SOL-R1-002, FABLE-016, FABLE-017)
12. **Ada saksi browser untuk setiap langkah posting**, bukan hanya tombol yang terlihat atau nonaktif. (FABLE-016;
    ditutup sebagian oleh perjalanan Astra CUT_TO_FG)
12a. **Dokumen induk yang dibuat otomatis lahir dalam transaksi yang sama dengan posting yang membutuhkannya.**
    Penolakan di tengah tidak meninggalkan induk yatim, stok bergerak, atau nomor terpakai; draf tidak menyentuh tabel
    bisnis; kirim ulang dengan UUID sama memberi jawaban sama. Uji juga dari layar dengan jawaban yang hilang di jalan.
    (SOL-R1-002, D15-6)
12b. **Penghalang "sudah dipakai" menghitung pemakaian yang masih aktif.** Pembatalan dan pembalik meniadakan
    pemakaian yang dibatalkannya; menjumlahkan semua mutasi keluar dalam sejarah membuat koreksi macet selamanya. Uji
    setiap aksi koreksi dengan urutan pakai → batalkan → koreksi harus bisa lagi, dan kontrol pemakaian yang masih aktif
    tetap menolak. (ASTRA-R2-01)

## D. Layar

13. **Pemeriksaan di layar memakai predikat yang sama dengan penjaga Native.** "Boleh diselesaikan" di layar harus
    sama dengan yang diterima database; jangan menebak ulang aturan di frontend. (ASTRA-C17-05)
14. **Teks status diambil dari status server.** Jangan menulis "final", "lunas", "selesai" bila server berkata
    sementara/belum lengkap. (ASTRA-C17-05)
15. **Selama data pendukung dimuat, simpan diblokir dan tinjauan dibatalkan sejak perubahan dimulai**, bukan sesudah
    respons datang. Respons terlambat atau gagal tidak boleh diam-diam mengubah dokumen yang sudah disimpan.
    (ASTRA-C17-02)
16. **Angka contoh tidak pernah tampil tanpa label**, dan label tidak bergantung pada tata letak (misalnya ada atau
    tidaknya tombol). Satu tabel aktivasi menentukan menu mana tersambung di tiap mode; yang belum tersambung di mode
    data nyata disembunyikan atau berupa layar batas tanpa angka. (FABLE-015, ASTRA-C17-03, KNOWN-UI-MODE, D15-2)
    Owner D16-1 (16 Okt): "selesain biar gausa sembunyiin" — tujuan akhirnya layar tersambung di mode data nyata, bukan
    menu tersembunyi; uji browser juga memakai build mode data nyata.
17. **Lebar HP diuji dengan rumus tertulis:** `document.documentElement.scrollWidth <= window.innerWidth` pada 390 px
    untuk setiap menu di setiap mode, dengan data terisi. Jangan menutup luapan dengan `overflow:hidden`.
    (SOL-R1-004/005; Astra melaporkan nol luapan dengan cara ukur lain)
18. **Pesan penolakan menyebut jalan keluarnya** (layar mana yang harus diisi). (FABLE-017 `NO_WORK_RATE`)
18a. **Pratinjau memakai aturan tanggal yang sama dengan pencatatan.** Upah yang ditampilkan sebelum simpan dihitung
    dengan tarif yang berlaku pada waktu jahit yang diisi, persis aturan snapshot Native, bukan tarif hari ini.
    (Fable D15-3, rate_timeline)
18b. **Satu layar dengan dua penulis memuat ulang keduanya sesudah setiap simpan dan pada tombol Refetch.** Penanda
    transaksi tertunda disimpan bersama, jadi simpan di satu penulis membuat penulis lain ikut "belum dimuat"; bila hanya
    satu yang dimuat ulang, seluruh layar terkunci. Uji DOM: sesudah simpan di tiap mode, kontrol layar aktif kembali.
    (Temuan penulis saat kualifikasi r2: Buat Potongan mode "PO yang sudah ada" sesudah D15-6, run 38878801310 dan
    38890676716)
18c. **Pembacaan ulang yang kalah oleh pembacaan lebih baru bukan "muat ulang gagal".** Bila layar induk memuat ulang dan
    panel anak ikut memulai pembacaan baru, hasil muat ulang adalah hasil pembacaan terbaru, sesudah simpan maupun
    sesudah ditolak server. Pesan penolakan harus persis kalimat server, tanpa tambahan "Refetch gagal" yang tidak benar.
    Uji DOM meniru induk yang memuat ulang di tengah jalan. (CI 39020856920, kasbon ditolak di kasus pengaman R3)

## E. Bukti dan alat uji

19. **Hitung run, job dan kasus secara terpisah**; warna job bukan hasil kasus. Laporan tidak menyebut "80 uji" bila
    yang dimaksud 80 run. (catatan Astra dan Sol atas receipt `dfab13bf`)
19a. **Alat yang membaca daftar dari API membaca semua halamannya**, dan jumlah run di receipt dicocokkan dengan jumlah
    workflow yang dipicu sebelum receipt dipakai. (Temuan penulis di kualifikasi r2: `scripts/cp7_ci_receipt.py` hanya
    membaca 100 run pertama dari 115; receipt r2 dibuat dengan salinan yang membaca semua halaman; alat diperbaiki di r3 untuk
    run, job dan anotasi)
20. **Run yang dibatalkan, diulang, atau gagal sebelum kasus ditulis terbuka** di receipt dan dokumen, beserta
    penyebab yang terbukti atau ditandai dugaan. (CodeQL dibatalkan antrean, Offsite Backup percobaan kedua)
21. **Bukti yang dipakai lebih dari 30 hari tidak boleh hanya berupa artifact CI.** Simpan di pohon (dengan SHA-256)
    atau salinan bertenggat panjang; catat tanggal kedaluwarsa. (arsip 10392910720, D14-17)
22. **Perubahan alat uji diterapkan ke semua titik masuk**, dan alat tahu titik berhentinya (langkah yang tidak dijalankan
    dicatat "tidak berlaku", bukan dituntut). (ASTRA-C17-06, SOL-R1-003)
23. **Potret sebelum perbaikan diberi nama kelompok `*_BEFORE`** supaya COUNTEREXAMPLE yang disengaja tidak dibaca
    sebagai regresi. (catatan Astra atas AV/BE)
24. **Kasus gagal dari auditor dipakai apa adanya** saat menguji perbaikan: nominal, tanggal dan hasil yang diharapkan
    tidak diganti; penjaga tidak dilonggarkan; log gagal disimpan. (aturan owner, Pro Max)
25. **Fixture yang mencakup satu dimensi menyembunyikan cacat dimensi lain.** Untuk setiap fitur, tambahkan kontrol
    lintas merek, lintas gudang, lintas tanggal tutup buku, dan dua sesi bersamaan. (ASTRA-C17-01, FABLE-013)
25a. **Kasus browser yang gagal mencetak alert dan status di layar ke log**, karena artifact CI tidak selalu bisa
    diunduh dari tempat log dibaca. Tombol dipilih lewat nama aksesibelnya; tombol di dalam `<label>` memakai nama
    label itu. (CI 38861916560: lokasi dan rantai Bagi Potongan)
25b. **Helper uji membaca teks elemen yang bisa hilang sendiri (alert sesaat) tanpa menunggu**, dan menyimpan teksnya.
    Menghitung lalu meminta teks bisa menunggu elemen yang sudah hilang sampai batas waktu, sehingga kasus yang oraclenya
    tercapai tercatat INCOMPLETE. (FABLE-018)
25c. **Fungsi PL/pgSQL dikompilasi lokal dan diperiksa bentrok nama sebelum CI.** Variabel yang bernama sama dengan alias
    tabel di fungsi yang sama baru gagal saat dijalankan ("column reference ... is ambiguous"); kompilasi tidak
    menangkapnya. `CASE ... THEN` di dalam syarat `IF` harus diberi kurung. Jalankan
    `scripts/cp7_plpgsql_compile_check.py` lalu `scripts/cp7_plpgsql_clash_check.py` pada setiap berkas SQL yang diubah,
    di database cek milik sendiri. (CI 39002828381: 21 kasus jahit INCOMPLETE karena variabel `x`, `r`, `c`; R3-09)
25d. **Uji build mode data nyata memakai build rilis yang sama**, bukan build uji: hanya alamat proyek dan kunci browser
    yang diganti (kunci pengganti, bukan kunci proyek mana pun), alamat proyek dijawab oleh database sekali pakai di
    loopback, semua alamat lain diblokir, dan host proyek diarahkan ke loopback di runner. (owner D16-1, oracle Fable 2)
    Pengalih permintaan di alat uji harus tahan halaman yang ditutup saat jawaban masih di jalan: kegagalannya dicatat dan
    diberikan ke halaman sebagai gangguan jaringan, bukan mematikan seluruh grup uji. (CI 39024246702: grup Enteng berhenti
    di 266 dari 321 kasus)
25e. **Fixture yang menutup buku memenuhi seluruh jendela pemeriksaan penutupan, bukan hanya hari kasusnya.** Kelengkapan
    absensi diperiksa sejak tanggal mulai mesin (`erp.period_completeness_from_v1()`), jadi hari kosong pekerja seed yang
    ditinggal fixture lain ikut menghalangi. Fixture mengisinya dengan cara owner (OFF) lalu memastikan tidak ada yang
    tersisa; oracle "Penghalang: 0." tidak dilonggarkan. Data uji juga mengikuti batas kolom Native (misalnya
    `erp.app_users.role` varchar 20). (CI 39020856920 rantai R3 sewing → close; CI 39019699925 Ringkasan Gudang HTTP)

## F. Proses audit

26. **Minimal tiga auditor independen, tanpa saling intip sampai laporan dikunci.** Putaran `dfab13bf`: delapan akar
    hanya ditemukan oleh satu auditor; tiga ditemukan oleh semuanya.
27. **Penulis memeriksa ulang setiap klaim auditor ke kode atau dengan reproduksi sendiri** sebelum memperbaiki, dan
    mencatat bila klaim auditor keliru atau saling bertentangan (`CROSS_AUDIT.md` §4).
28. **Oracle uji ulang ditetapkan sebelum perbaikan dibuat** dan disimpan di cabang auditor, supaya ukurannya tidak
    bisa digeser. (Fable `OWNER_DECISIONS_TO_AUDITOR_20261016.md`)
29. **Hal yang sudah diungkap penulis tetap temuan** dengan tingkat penuh; pengungkapan tidak menurunkan tingkat.
    (FABLE-015)
29a. **Batas yang diungkap penulis bukan keputusan owner.** Fungsi yang punya penulis Native tetapi tanpa layar adalah
    fungsi yang belum tersedia, sampai owner menuliskan penundaannya; menyembunyikan menu bukan penerimaan. (Sol
    KNOWN-R2-POOL-UI, ASTRA-C17-07, owner D16-1)
29b. **Bila auditor memberi tingkat berbeda untuk akar yang sama, dipakai tingkat yang lebih tinggi.** (R3-01: Astra S1,
    Sol S2; R3-04: Sol S1, Astra S2)

## Daftar periksa sebelum penulis menyerahkan kandidat

- [ ] Setiap entitas baru/berubah: buat, ubah, tutup, buka ulang dari aplikasi, atau keputusan owner tertulis (C9).
- [ ] Penjaga uang: keadaan akhir, semua dasar tanggal, detektor dengan kontrol 0→+1→0 (A1–A3).
- [ ] Kunci identitas lengkap dari server; uji lintas merek/gudang/tanggal (B6, E25).
- [ ] Versi bertanggal: pembetulan hari yang sama vs versi baru; penyeragaman nilai hanya saat membuat (B8a, B8b).
- [ ] Dokumen induk otomatis: satu transaksi, gagal di tengah tidak meninggalkan apa pun, kirim ulang sama (C12a);
  nomor urut lewat batas digit (B8d).
- [ ] Setiap aksi koreksi: pakai → batalkan → koreksi bisa lagi; pemakaian aktif tetap menolak (C12b).
- [ ] Batas tanggal resmi: trigger tabel, jalur sah dikecualikan per nama sumber, uji 00:00 vs 23:59:59 WIB (A5a).
- [ ] Batas Native per SKU/lingkup: layar meminta dan menghitung per lingkup yang sama (B8c).
- [ ] Layar: pemeriksaan sama dengan Native, teks status dari server, simpan diblokir saat memuat (D13–D15);
  layar dengan dua penulis aktif kembali sesudah simpan di tiap mode (D18b).
- [ ] Mode data nyata: tidak ada angka contoh tanpa label; tidak ada fungsi Native tanpa layar kecuali owner menunda
  tertulis; tabel aktivasi diperbarui; uji browser build mode data nyata (D16, F29a).
- [ ] 47 menu × 3 mode × HP 390 px: `scrollWidth <= innerWidth` (D17; 48 sebelum D16-5 menggabungkan Tutup Periode).
- [ ] SQL yang diubah: kompilasi lokal + pemeriksaan bentrok nama variabel/alias (E25c).
- [ ] Rantai diuji mulai dari data yang dibuat di layar (C11–C12).
- [ ] Receipt: run, job, kasus terpisah; batal/ulang/gagal-sebelum-kasus ditulis; jumlah run = jumlah workflow yang
  dipicu (E19–E20, E19a).
- [ ] Bukti jangka panjang tidak bergantung artifact 30 hari (E21).

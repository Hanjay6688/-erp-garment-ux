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
8e. **Nomor id berurutan bukan urutan commit.** Transaksi yang mendapat id lebih kecil bisa selesai sesudah id yang
    lebih besar terlihat. Daftar berhalaman dengan batas "id tertinggi yang terlihat" diam-diam melewatkan baris itu.
    Setiap daftar membawa tanda isinya (jumlah dan total id di dalam batas) di kursor; halaman berikut yang tandanya
    berbeda berkata "daftar berubah" dan layar meminta Muat ulang. Uji tiga sesi: id rendah ditahan, id tinggi commit,
    halaman pertama dibaca, id rendah commit. (ASTRA-R3-02)

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
12c. **Pasangan pembalik berlaku dua arah.** Gerakan keluar yang membalik gerakan masuk (misalnya -2 yang membatalkan
    penyesuaian +2) bukan pemakaian; gerakan masuk yang tidak berhubungan tetap tidak boleh menutupi pemakaian aktif. Uji
    kedua arah: keluar lalu dibalik, dan masuk lalu dibalik. (ASTRA-R2-01 sisa r3)
12d. **Fasad baru menutup semua jalur lama ke penulis yang sama.** Bila fasad CP7 menambah penjaga (periode tertutup,
    hak kelola, token tinjauan), pembungkus publik lama ke penulis Native yang sama ikut ditutup untuk Data API, bukan
    hanya tidak dipakai layar. Sensus semua fungsi publik yang bisa dijalankan peran browser (authenticated dan anon):
    setiap fungsi masuk daftar yang dipakai aplikasi, daftar yang sengaja dibiarkan, atau daftar yang ditutup; fungsi
    baru yang belum ditinjau membuat pemeriksaan gagal. Uji lewat Auth dan PostgREST sungguhan, bukan sesi database.
    (ASTRA-R3-01, owner D14-9)
12e. **Jenis sumber baru diajarkan ke semua pembaca, termasuk detektor integritas.** Saat sebuah kolom jenis (misalnya
    `payroll_work_items.source_type`) mendapat nilai baru, daftar setiap fungsi dan view yang bercabang pada kolom itu:
    penulis, pembaca, layar, dan detektor. Setiap fungsi harus menangani nilai baru, atau terbukti hanya untuk satu jenis
    saja. Uji buku sehat dengan nilai baru: semua detektor harus tetap 0. Detektor yang tidak mengenal sumbernya akan
    mengira baris sah sebagai pelanggaran. (SOL-R4-001: Nota FG_REPAIR sah dihitung "salah mandor" CRITICAL, karena AX
    mengajari view, CHECK, validator dan merge, tetapi tidak pemeriksa integritas)

## D. Layar

13. **Pemeriksaan di layar memakai predikat yang sama dengan penjaga Native.** "Boleh diselesaikan" di layar harus
    sama dengan yang diterima database; jangan menebak ulang aturan di frontend. (ASTRA-C17-05)
14. **Teks status diambil dari status server.** Jangan menulis "final", "lunas", "selesai" bila server berkata
    sementara/belum lengkap. (ASTRA-C17-05)
15. **Selama data pendukung dimuat, simpan diblokir dan tinjauan dibatalkan sejak perubahan dimulai**, bukan sesudah
    respons datang. Respons terlambat atau gagal tidak boleh diam-diam mengubah dokumen yang sudah disimpan.
    (ASTRA-C17-02)
15a. **RPC401 dan403 sama-sama membatalkan fakta yang memerlukan sesi/hak tersebut**, termasuk hasil bertahap,
    ringkasan, laporan anak dan generasi respons yang masih menunggu. Jangan menunggu provider login berubah atau
    halaman mendapat fokus. Uji saat identitas provider masih AUTHORIZED tetapi pembacaan halaman, kesegaran, atau
    pemeriksaan sumber ditolak. (WR-OW03-401: tiga DOM gagal sebelum perbaikan,17/17 lulus sesudahnya;
    `docs/cp7/d17-14/ow03/README.md`)
16. **Angka contoh tidak pernah tampil tanpa label**, dan label tidak bergantung pada tata letak (misalnya ada atau
    tidaknya tombol). Satu tabel aktivasi menentukan menu mana tersambung di tiap mode; yang belum tersambung di mode
    data nyata disembunyikan atau berupa layar batas tanpa angka. (FABLE-015, ASTRA-C17-03, KNOWN-UI-MODE, D15-2)
    Owner D16-1 (16 Okt): "selesain biar gausa sembunyiin" — tujuan akhirnya layar tersambung di mode data nyata, bukan
    menu tersembunyi; uji browser juga memakai build mode data nyata.
16a. **Keputusan owner yang mengubah keadaan layar diikuti pencarian semua oracle lama atas keadaan itu**, termasuk uji
    browser CP4.5–CP6 di workflow Build UX. Oracle lama diperbarui ke keputusan baru dengan tetap menjaga maksud aslinya
    (misalnya: penulis Nota lama di browser tidak pernah terbuka), bukan dihapus. (CI 39027273503: uji "WRITER DIBLOKIR"
    Susun Nota FG masih mengharapkan layar batas D15-2 sesudah D16-1)
17. **Lebar HP diuji dengan rumus tertulis:** `document.documentElement.scrollWidth <= window.innerWidth` pada 390 px
    untuk setiap menu di setiap mode, dengan data terisi. Jangan menutup luapan dengan `overflow:hidden`.
    (SOL-R1-004/005; Astra melaporkan nol luapan dengan cara ukur lain)
17a. **Kartu berlatar terang mengatur warna teksnya sendiri.** Warna teks bawaan aplikasi terang (untuk latar gelap);
    kartu putih yang tidak mengatur warna membuat angka hampir tak terlihat. Sensus keterbacaan di setiap menu, desktop
    dan HP: kontras teks terhadap latar (rumus luminans WCAG, gradien dihitung per titik warna) tidak boleh di bawah 2:1,
    dan angka utama minimal 4,5:1. (ASTRA-R3-03; keluarga yang sama ditemukan di Data Master > Pola)
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

25f. **Cari penyebab lambat dengan hitungan waktu per fungsi pada satu panggilan nyata, bukan dengan menebak.**
    `track_functions=all` di dalam transaksi yang dibatalkan, selisih `pg_stat_xact_user_functions` sebelum dan sesudah,
    per mode (misalnya dengan dan tanpa angka keuangan), plus satu kali dengan JIT mati. Profil per lapisan saja meleset
    4 detik dari waktu nyata. Penjaga yang dipanggil ribuan kali per panggilan (di sini `erp.require_internal()` 32.000 kali,
    3,9 dari 6,3 detik) dipercepat hanya dengan jalan pintas yang terbukti sama hasilnya: cabang yang dilewati hanya bisa
    mengizinkan, hanya lewat baris transaksi itu sendiri, satu CASE dengan filter identitas lebih dulu; uji lama-lawan-baru
    berdampingan, dan pemeriksaan bentuk yang gagal bila cabang baru ditambah tanpa ikut diperiksa jalan pintasnya.
    (R4-05, Sol KNOWN-P19-DIRECT-LATENCY, CI 39157467151)
25h. **Fungsi STABLE dengan argumen tetap di dalam filter per baris dijalankan sekali per baris.** Hitungan waktu per
    fungsi menunjukkan `erp.account_id('<KEY>')` dipanggil 31.000 kali dalam satu analisis, masing-masing dengan
    penjaganya. Tulis `(select erp.account_id('<KEY>'))`: PostgreSQL menghitungnya sekali per query (init plan) dan
    angkanya sama. Satu beda yang harus ditutup: perencana query juga memanggil fungsi STABLE inline saat menaksir,
    sehingga teks lama menolak kunci yang tidak ada walau tidak ada baris; init plan baru menolak saat ada baris yang
    membutuhkannya. Tutup dengan prasyarat (semua kunci adalah mapping inti yang dijaga dari hapus/ganti nama) dan
    uji lama-lawan-baru berdampingan pada data yang sama. (R5-02, owner D17-2)
25g. **Hasil yang sudah terlihat bukan berarti catatan penjadwal sudah ditulis.** pg_cron menyimpan pekerjaan sebuah run
    lebih dulu, lalu menulis status run itu sesudahnya. Uji yang membaca `cron.job_run_details` begitu pekerjaannya
    terlihat bisa mendapati status "running" untuk run yang sebenarnya berhasil. Baca catatan run sesudah jadwal dicabut,
    sesudah sesi pg_cron pergi, dan sesudah setiap run punya akhir yang tertulis (dengan batas waktu). Syarat lulus tetap
    sama. Celah ini sudah ada sejak r3; r3 lulus karena kebetulan membaca lebih lambat (cron_runs 1). (R4-Q1,
    kualifikasi `769f2cc3`, CI 39161868253 `K6P_RACE_PG_CRON_FINISHES_PASS`)
25i. **Uji "jawaban sama" harus membuktikan ia membandingkan sesuatu.** Uji lama-lawan-baru R5-02 lulus walau tiga dari
    sebelas pembaca dibandingkan pada nol masukan: buku uji CP17 tidak punya kredit saldo awal, periode pocket atau
    jurnal penjualan. Catat per fungsi berapa masukan, berapa yang dijawab tanpa penolakan dan berapa yang berisi nilai;
    gagalkan uji bila ada fungsi yang tidak pernah menjawab; bangun baris yang tidak ada di buku uji di dalam savepoint
    yang dibatalkan, lewat jalur yang sama dengan probe. (R5-02, CI 39209921715 di `3b9817ae`)
25j. **Pasang dan uji sebagai `postgres` biasa, bukan hanya sebagai superuser.** Di Supabase `postgres` bukan superuser.
    Alat uji Native memasang semua bundle sebagai `supabase_admin`, jadi dua hal tidak pernah terlihat: (1) menyerahkan
    skema/tabel/fungsi ke peran baru ditolak ("must be able to SET ROLE") kecuali sesi memakai
    `createrole_self_grant = 'set, inherit'` atau peran itu di-grant ke pemasang; (2) `grant usage on schema auth` oleh
    `postgres` dilewati diam-diam (hanya peringatan), lalu fungsi milik peran itu gagal saat dipanggil. Setiap modul baru
    punya uji pasang-pakai-copot sebagai `postgres` di stack bersih; jangan bergantung pada hak di skema milik Supabase
    yang tidak bisa diteruskan `postgres`. (WA-3a, CI 39271239303 dan 39271994388; lihat
    `docs/cp7/wa/CP7C_INSTALL_FINDINGS_20261019.md`)
25k. **Server palsu dan alat uji juga tidak boleh mencetak kunci, walau kuncinya palsu.** Server CallMeBot palsu WA-3
    mencetak `apikey` ke log; gerbang CodeQL menolaknya (`py/clear-text-logging-sensitive-data`). Jangan longgarkan
    gerbang: server palsu menerima kunci uji yang diharapkan lewat variabel lingkungan dan hanya mencetak `key_ok`
    (benar/salah), sehingga uji tetap membuktikan kunci yang tepat sampai tanpa kunci masuk log. (WA-3, CodeQL run
    39273065854 di `65789737`)
25l. **Pemilik objek yang disyaratkan desain ditulis eksplisit, tidak mengikuti siapa yang memasang.** Tabel `transport`
    modul WA harus milik `postgres`; uji tumpukan memasang sebagai `postgres` sehingga lulus, tetapi alat uji Native memasang
    sebagai `supabase_admin` dan tabel itu jadi milik pemasang (pemeriksa menolak). Tulis `alter ... owner to` untuk setiap
    objek yang pemiliknya penting, dan pasang modul baru sekali sebagai `postgres` dan sekali sebagai superuser lain sebelum
    kandidat diserahkan. (WA-3b, CI 39275715784 di `97cd1386`)
25m. **Batas jam (jam kerja, jam analisis, jam tenang) hanya menahan pekerjaan baru, bukan laporan keadaan, dan ujinya tidak
    bergantung jam berapa CI berjalan.** Tick analisis WA menjawab "di luar jam analisis" sebelum "Bos belum pernah
    menjalankan analisis"; uji lokal siang hari lulus, CI pukul 22.47 WIB gagal di dua kasus. Urutan pemeriksaan: keadaan
    pekerjaan pemilik dulu (sedang berjalan, belum ada), lalu sakelar, lalu jam. Uji yang menyentuh jendela jam memilih
    jendelanya dari jam database saat itu (satu jendela berisi sekarang, satu tidak), dan kasus yang tidak bisa dibuat
    di menit terakhir hari menunggu hari berganti agar kontrol pergantian hari mengulangnya. (WA-2b, CI 39279865016 di
    `4c36f1a2`)
25n. **Pelaku dalam data uji memenuhi aturan pelaku modul yang dipakai.** Kasus WA memakai pengguna Gudang untuk
    "pengingat orang lain", padahal modul pengingat hanya menerima OWNER, ADMIN dan STAFF; kasus berhenti sebelum
    pemeriksaannya. Pilih peran dari aturan modul itu sendiri (lihat kasus modul aslinya), bukan peran yang kebetulan dipakai
    kasus lain. (WA-3b, CI 39279865016)
25o. **Pemantau CI mencari run dengan SHA penuh, dan diam terlalu lama berarti pemantaunya yang diperiksa dulu.** API run
    GitHub hanya mencocokkan `head_sha` yang lengkap; pemantau penulis memakai SHA pendek, tidak pernah menemukan run, dan
    hasil WA Forward 39285796156 (selesai 16.39 UTC) baru terbaca 85 menit kemudian. Pemantau mengubah SHA ke bentuk penuh
    sebelum bertanya, dan mencetak jumlah run yang ia temukan pada setiap putaran. (WA-4b, 19 Okt)
25p. **Kerja yang jalan tiap menit diukur dengan data sebesar pemakaian nyata, dan rencana kuerinya dibaca.** Rumus titik
    pesan ulang (SS-1) butuh 3,7 detik untuk 2.000 barang dan 202.000 gerakan; 3,1 detik di antaranya kompilasi JIT karena
    perkiraan baris planner jauh di atas kenyataan (deret hari × barang). Dengan `set jit=off` pada fungsinya dan satu himpunan
    model berjalan (bukan panggilan fungsi per baris): 0,6 detik. Kasus volume berlabel `SYNTHETIC_VOLUME` menjaga batasnya di
    CI. Ukur dulu (`auto_explain` dengan `log_nested_statements`), baru ubah. (SS-1, 20 Okt)
25q. **Rumus stok tidak menganggap hari kehabisan stok sebagai permintaan nol, dan pembandingnya dihitung ulang dari angka
    fixture.** Hari tanpa stok di awal dan tanpa penjualan tidak masuk hitungan rata-rata dan simpangan; kasus
    `SS1_OUT_OF_STOCK_DAYS_NOT_ZERO_DEMAND` menunjukkan titik yang berbeda (28 lawan 24) bila hari itu dihitung. Pembanding di
    kasus (`oracle()`) memakai hari dan jumlah fixture sendiri di Python, tidak membaca tabel modul. (SS-1, 20 Okt)
25r. **Hasil yang disimpan sementara untuk satu putaran diberi kunci putaran itu, bukan kunci transaksi.** Tiga sumber
    pengingat stok (barang jadi, kain, aksesori) memakai satu hitungan per tick. Tanda "sudah dihitung" pertama dipasang per
    transaksi; kasus yang menaikkan stok lalu membaca sumber lagi di transaksi yang sama mendapat hitungan basi
    (`SS1_SOURCE_AND_ACCESS` gagal lokal). Kunci yang benar: waktu mulai perintah (`statement_timestamp()`), sehingga satu tick
    berbagi satu hitungan dan perintah berikutnya menghitung ulang. (SS-2, 20 Okt)
25s. **"Stok ada di gudang" dibaca dari aturan layar yang sudah diterima, bukan dari jenis lokasi saja.** Area pos servis,
    area periksa dan area rusak aksesori (BC) tercatat sebagai `RAW_MATERIAL_WAREHOUSE`; menghitung semua lokasi jenis itu
    akan menganggap barang rusak dan barang yang belum diperiksa sebagai stok bebas, dan pengingat terlambat. Rumus aksesori
    memakai aturan Bahan & Roll (zona khusus bukan "ON_HAND"); kasus `SS3_SERVICE_ZONES_NOT_FREE_STOCK` menjaganya. Begitu
    pula retur nota yang dikreditkan sebagai rusak tidak mengurangi pemakaian. (SS-3, 20 Okt)
25t. **Deklarasi kasus dicocokkan dengan modul kasus di lokal sebelum push.** Deklarasi WA mencantumkan empat RPC barang jadi
    yang tidak ada di daftar `FUNCTIONS` modul kasus; probe akan menolak seluruh suite (`..._PREDECLARED_CASE_BUDGET_CHANGED`)
    sebelum satu kasus pun jalan. Jalankan pemeriksaan yang sama dengan probe (`contract`, jumlah, ID, RPC, jadwal) di lokal
    setiap kali deklarasi atau modul kasus berubah. (SS-2, 20 Okt)
25u. **Dua jenis pengingat digabung tanpa mengubah sumber lama yang sudah punya pembanding.** Owner D17-10 meminta kain
    berumus masuk ke "Stok kain di bawah minimum". Sumber lama (`fabric_source()`, aturan Ringkasan Gudang, dibuktikan sama
    oleh `WAF_FABRIC_EQUALS_WAREHOUSE_SUMMARY`) tidak disentuh; gabungannya fungsi baru `fabric_kind_source()`. Dua himpunan
    tidak boleh berbagi subjek: `apply_kind` menolak sumber yang memberi satu subjek sebagai baris dan juga sebagai keadaan,
    jadi keadaan `MANUAL_MINIMUM_IN_FORCE` dari rumus dibuang dan keadaan kain yang punya minimum diambil dari sumber lama.
    (D17-10, 20 Okt)
25v. **Kalikan dulu, baru bagi; pembanding memakai pecahan eksak.** Batas minimum aksesori D17-12 ditulis
    `pemakaian_bulan / 30 × (lama kirim + cadangan)`. PostgreSQL membulatkan `500/30` ke 16 desimal (ke atas di digit
    terakhir) sebelum dikali, sehingga 500 per bulan dengan 14 + 7 hari menjadi 350,01, padahal tepatnya 350. Kelas yang sama
    ada di rumus barang jadi mode cadangan hari (rata-rata dibulatkan × (lama kirim + cadangan): 20 terjual dalam 30 hari,
    2 + 1 hari menjadi 3 pcs, padahal tepatnya 2) dan rumus kain. Ditemukan oleh pemeriksaan layar yang menghitung ulang
    secara eksak (bilangan bulat besar); pembanding Python lama memakai `Decimal` yang dibulatkan dengan cara serupa sehingga
    ikut salah dan tidak menangkapnya. Aturan: susun rumus sebagai satu pembilang dibagi satu penyebut
    (`ceil(total × hari × 100 / 30) / 100`), dan pembanding di kasus memakai `fractions.Fraction`, bukan desimal yang
    dibulatkan. Selalu sertakan kasus batas yang hasil tepatnya bilangan bulat/sen bulat (`SS1_DAYS_BUFFER_NOT_STACKED`,
    `SS3_ACCESSORY_MINIMUM_FROM_OWNER_ESTIMATE`); log gagal di kode lama ada di
    `docs/cp7/evidence/stock-formula-rounding-20261020/`. (D17-12, 20 Okt)
25w. **Masukan run yang diulang diambil dari log run yang diterima sebelumnya, bukan dari ingatan atau riwayat perintah.**
    Skenario penulis CP6 lengkap untuk `55c885d1` dijalankan dengan `scripts/cp6_be_modes.py` (17 kasus) karena perintahnya
    disalin dari riwayat lama; run lulus, padahal skenario lengkap kandidat sebelumnya `scripts/cp6_bf_combined_modes.py`
    (170 kasus). Sebelum dispatch, baca baris `SCENARIO_PATH`/`BROWSER_PATH` (atau masukan lain) di log run pembanding dan
    pakai yang sama; sesudah run, cocokkan jumlah kasus dengan run pembanding sebelum menyebutnya lulus. (r6, 20 Okt)

25x. **Data opsional di PL/pgSQL tetap mempunyai tipe pasti sejak pemanggilan pertama.** `RECORD` yang hanya diisi
    ketika invoice tujuan ada dapat gagal dengan SQLSTATE55000 saat cabang JSON/CASE disiapkan, walaupun permintaan kas
    tidak memilih invoice tujuan. Pemanggilan sebelumnya pada sesi yang sama dapat menutupi cacat ini. Pakai variabel
    nullable bertipe kolom yang eksplisit dan pertahankan seluruh penjaga identitas/uang/tanggal. Uji pada sesi baru:
    tujuan kosong dahulu, tujuan ada dahulu lalu kosong, dan hasil dengan tujuan yang sama. REFUND dan pembatalan
    refund pertama gagal pada UI8 `f41acbae`; kontrol reproduksi membedakan backend dingin dari hangat, dan sumber
    `da6a5454` lulus current42 tanpa mengganti oracle. Bukti: `cp7/d17-14/ow04/consumer-ui-selector-record-fix/` dan
    `cp7/d17-14/ow04/consumer-current42-da6a5454-pass/`. (WR-OW04-UI8-55000, 22 Okt)

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
29c. **Rumus atau fitur yang "disiapkan, belum aktif" punya pemilik dan diangkat ke owner di setiap laporan sampai
    diputuskan.** Riset 28 Sep menyiapkan rumus safety stock "tidak aktif otomatis"; ERP menyimpan tempat angkanya dan
    layar demo menghitungnya, tetapi rumus itu tidak pernah disambungkan ke data dan tidak diangkat lagi, sampai owner
    bertanya tiga minggu kemudian (D17-8, D17-9). Setiap butir "belum aktif" masuk daftar terbuka di laporan, dengan apa
    yang kurang untuk mengaktifkannya.

## Daftar periksa sebelum penulis menyerahkan kandidat

- [ ] Setiap entitas baru/berubah: buat, ubah, tutup, buka ulang dari aplikasi, atau keputusan owner tertulis (C9).
- [ ] Penjaga uang: keadaan akhir, semua dasar tanggal, detektor dengan kontrol 0→+1→0 (A1–A3).
- [ ] Kunci identitas lengkap dari server; uji lintas merek/gudang/tanggal (B6, E25).
- [ ] Versi bertanggal: pembetulan hari yang sama vs versi baru; penyeragaman nilai hanya saat membuat (B8a, B8b).
- [ ] Dokumen induk otomatis: satu transaksi, gagal di tengah tidak meninggalkan apa pun, kirim ulang sama (C12a);
  nomor urut lewat batas digit (B8d).
- [ ] Setiap aksi koreksi: pakai → batalkan → koreksi bisa lagi; pemakaian aktif tetap menolak (C12b).
- [ ] Pembalik dua arah: keluar-dibalik dan masuk-dibalik sama-sama bukan pemakaian (C12c).
- [ ] Fasad baru: semua jalur publik lama ke penulis yang sama ditutup untuk Data API; sensus fungsi publik peran browser
  lulus tanpa fungsi yang belum ditinjau (C12d).
- [ ] Daftar berhalaman: tanda isi di kursor, uji commit terlambat dengan id lebih kecil (B8e).
- [ ] Batas tanggal resmi: trigger tabel, jalur sah dikecualikan per nama sumber, uji 00:00 vs 23:59:59 WIB (A5a).
- [ ] Batas Native per SKU/lingkup: layar meminta dan menghitung per lingkup yang sama (B8c).
- [ ] Layar: pemeriksaan sama dengan Native, teks status dari server, simpan diblokir saat memuat (D13–D15);
  layar dengan dua penulis aktif kembali sesudah simpan di tiap mode (D18b).
- [ ] Mode data nyata: tidak ada angka contoh tanpa label; tidak ada fungsi Native tanpa layar kecuali owner menunda
  tertulis; tabel aktivasi diperbarui; uji browser build mode data nyata (D16, F29a).
- [ ] 47 menu × 3 mode × HP 390 px: `scrollWidth <= innerWidth` (D17; 48 sebelum D16-5 menggabungkan Tutup Periode).
- [ ] Sensus keterbacaan: tidak ada teks di bawah 2:1 di menu mana pun; angka utama minimal 4,5:1 (D17a).
- [ ] SQL yang diubah: kompilasi lokal + pemeriksaan bentrok nama variabel/alias (E25c).
- [ ] Layar berat lebih dari 3 detik: penyebab diukur per fungsi sebelum diubah; jalan pintas penjaga terbukti sama
  hasilnya dan cabang konteks baru ikut diperiksa (E25f).
- [ ] Uji penjadwal: catatan run dibaca sesudah setiap akhir run tertulis, bukan begitu hasilnya terlihat (E25g).
- [ ] Nilai jenis baru (source_type dan sejenisnya): semua fungsi yang bercabang pada kolom itu ditinjau, termasuk
  detektor; buku sehat dengan nilai baru membuat semua detektor 0 (C12e).
- [ ] Panggilan fungsi STABLE di filter per baris: dibungkus scalar subquery bila panas, dengan prasyarat untuk jalur
  error dan uji lama-lawan-baru (E25h).
- [ ] Uji perbandingan mencatat jumlah masukan per fungsi dan gagal bila ada fungsi yang tidak pernah menjawab (E25i).
- [ ] Modul baru dipasang, dipakai dan dicopot sebagai `postgres` (bukan superuser) di stack bersih; tidak ada grant ke
  skema `auth` (E25j).
- [ ] Objek yang pemiliknya disyaratkan diberi `alter ... owner to` eksplisit; modul dipasang sebagai `postgres` dan sebagai superuser
  lain, pemeriksa lulus di keduanya (E25l).
- [ ] Tidak ada kunci, token atau kata sandi (termasuk yang palsu) yang dicetak oleh server uji atau probe (E25k).
- [ ] Batas jam hanya menahan pekerjaan baru; kasus yang menyentuh jendela jam lulus pada jam berapa pun CI berjalan (E25m).
- [ ] Pelaku data uji dipilih dari aturan pelaku modul yang dipanggil (E25n).
- [ ] Pemantau CI memakai SHA penuh dan mencetak berapa run yang ia lihat (E25o).
- [ ] Setiap rumus/fitur "disiapkan, belum aktif" tercantum di daftar terbuka laporan, dengan apa yang kurang (29c).
- [ ] Kerja tiap menit diukur dengan volume pemakaian nyata dan rencana kuerinya dibaca; JIT tidak memakan waktunya (E25p).
- [ ] Rumus stok: hari kehabisan stok bukan permintaan nol; pembanding dihitung ulang dari angka fixture, bukan dari modul (E25q).
- [ ] Cache satu putaran berkunci putaran (waktu mulai perintah), bukan transaksi (E25r).
- [ ] Stok bebas mengikuti aturan "ada di gudang" layar yang diterima, termasuk zona khusus (E25s).
- [ ] Deklarasi kasus dicek lokal dengan aturan probe sebelum push (E25t).
- [ ] Menggabungkan sumber: sumber lama yang punya pembanding tetap utuh, subjek kedua himpunan tidak tumpang tindih (E25u).
- [ ] Rumus dengan pembagian: kalikan dulu baru bagi; pembanding pakai pecahan eksak; ada kasus batas yang hasil tepatnya bulat (E25v).
- [ ] Run yang diulang memakai masukan yang sama dengan run pembanding (baca log-nya), dan jumlah kasusnya dicocokkan (E25w).
- [ ] Rantai diuji mulai dari data yang dibuat di layar (C11–C12).
- [ ] Receipt: run, job, kasus terpisah; batal/ulang/gagal-sebelum-kasus ditulis; jumlah run = jumlah workflow yang
  dipicu (E19–E20, E19a).
- [ ] Bukti jangka panjang tidak bergantung artifact 30 hari (E21).


## Tambahan hasil kualifikasi24 Oktober2026 WIB

25y. **Data contoh positif hari ini harus sah sejak awal hari, tanpa mengubah penjaga tanggal aplikasi.** Jam bawaan
     08:00WIB pada contoh stok sah saat uji siang, tetapi masih masa depan bila CI berjalan00:23WIB. Tiga kontrol OW10
     berhenti di penolakan masa depan sebelum mencapai assertion cache/stale/stock-baru-rendah. Pakai00:00WIB pada
     tanggal rencana yang sama untuk contoh positif hari ini; atau waktu database yang sah bila urutan intra-hari
     memang diuji. Pertahankan tanggal, jumlah, urutan yang menjadi maksud kasus dan oracle bisnis. Jangan menjepit
     semua tanggal ke sekarang, memundurkan clock database, melewati writer Native, mengubah tanggal kasus negatif
     atau melonggarkan penolakan masa depan. Default contoh historis lain tidak perlu diganti.
     Bukti pertama16a0aeb0/run39993639712:13/15 Native,7/8 race,4/4 Auth,4/4 browser; ketiga kegagalan
     FG_UNSOURCED_PHYSICAL_AT_FUTURE. Fix fixture1ba69eaa, periksa hasil Native terbaru sebelum menyatakan lulus.
     (`WR-OW10-FIXTURE-WIB`, [receipt](cp7/d17-14/ow13c/16a0aeb-native31-28-clock.json)).

- [ ] Contoh positif bertanggal hari ini sah sebelum jam08WIB; uji masa depan tetap memakai tanggal/jam masa depan
  eksplisit dan tetap ditolak Native (E25y).


Validasi E25y/WR-OW10-FIXTURE-WIB: kandidat a15054c2, run39996465132/
job120561154474 lulus31/31 pada24 Oktober2026 WIB; ketiga kasus yang sebelumnya
berhenti karena contoh08:00WIB kini lulus dengan00:00 pada tanggal yang sama.
Tidak ada perubahan penjaga masa depan, jumlah atau oracle. [Receipt](cp7/d17-14/ow13c/a15054c-native31-pass.json).


## E25z — pembanding timestamp memakai representasi waktu yang sama (WR-METADATA-COMPARE-UTC)

Temuan writer24 Okt2026, bukan audit independen: Native8 pertama6370d29/
run40008494076 menunjukkan1PASS/7INCOMPLETE pada no-write GET. Hash metadata
`to_jsonb(timestamptz)` dibuat sebelum helper boundary.data() memilihUTC,
lalu dibandingkan dengan hashUTC sesudahnya. Baris sama dapat memiliki teks
berbeda. SetUTC sebelum seluruh serialisasi/hash, kembalikanGUCsemula dalam
finally. Tetap bandingkan seluruhbaris,kolom,nilai,receipt danmetadata; tampilkan
selisih bila gagal. Jangan menghapus tanggal/kolom, membulatkan hash atau
mengubah physical_at/system_created_at/clock untuk membuat tes lulus.

Fixb508bf77 hanyahelper pembanding. d85187dc/run40010384850 PASS8/8 dengan
32 sumber/9 invers22/restore/advisor/5gatepaket tepat, termasuk metadata2000/
202000 dan kegagalan atomik. Kegagalan awal/Original/rawlog dipertahankan di
receipt6370d29-schedule8-first-incomplete.json; kelulusan di d85187d-schedule8-pass.json.
Pelajaran ini tidak memberikan fullOW13c/rantaiA/audit/production_go.

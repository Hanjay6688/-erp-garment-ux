# UJI ULANG FABLE r4 — kandidat 663f6faefcbb9c70f0f99bbc7e78164e03521329, tree 023f3554 — 2026-10-19

Auditor: Fable, independen, baca-saja terhadap produk. Dasar: laporan Fable r3 terkunci (2033fdfc), oracle D16-1 nomor 1–5
(f2758f39), keputusan owner D14-2..D17-2. Kepala penulis saat run: `5eda90e1`, yang beda dari kandidat hanya 9 berkas
`docs/`; tree `src`, `scripts` dan `supabase` sama dengan kandidat. Status per kasus dibaca dari baris JSON log. Rincian
ada di `WORKLOG.md` dan `MANIFEST.md`. `production_go: false`.

## Ringkasan

Kelima oracle D16-1 tetap terpenuhi pada kandidat r4. Tidak ada temuan Fable yang terbuka dari r3. FABLE-012 **MASIH
TERBUKA** (ditunda ke CP7C, D14-9). **Tidak ada temuan produk baru.**

Klaim R4-05 "jawaban penjaga sama" saya coba patahkan dengan matriks sendiri: 70 sel, 0 beda. Aturan baru buka ulang PO
(R4-02) tidak bisa menyembunyikan pemakaian, karena semua pembalik stok terpasang menolak membalik pembalik. Skenario kas
saya dan sensus layar (kedua build) tetap lulus seperti r3. Semua 12 workflow penulis yang saya jalankan ulang lulus per
kasus, termasuk 341 kasus CP17 yang 57 kasus browsernya berjalan di build Enteng.

Ada dua kesalahan alat di pihak saya, keduanya dicatat terbuka: pengecualian Dashboard di sensus (sama seperti r3) dan
probe v1 yang kosong maknanya.

## Oracle D16-1 (diuji ulang karena r4 mengubah CSS layar tersambung, Audit Trail, panel analisis dan penjaga)

| Oracle | Status | Bukti (label) |
|---|---|---|
| 1. Tanpa menu tersembunyi dan tanpa angka contoh di build Enteng; Dashboard angka asli atau pemberitahuan tanpa angka | **DITUTUP** | Sensus saya (modul tidak diubah dari r3, sha 12954e42), build ENTENG run 39184472280 dan DISPOSABLE run 39184465655: 47/47 menu terbuka, 46 tanpa label contoh dan tanpa layar batas; satu-satunya tanda adalah pemberitahuan Dashboard, yang diizinkan oracle tertulis (FABLE; tanda Dashboard = AUDITOR_TOOL, sama dengan r3) |
| 2. Uji browser build Enteng; OWNER + peran terbatas; 1440 dan 390 px tanpa luapan | **DITUTUP** | Sensus ENTENG: OWNER 1440 dan 390, 0 luapan; GUDANG 7/7 menu, tanpa Keuangan; 159 permintaan origin Enteng dijawab loopback, 0 error (FABLE). CP17 run 39184479044: 57 kasus browser build Enteng PASS, 1.361 permintaan loopback, 0 error rute (INDEPENDENT_NATIVE_RERUN). Phone width (demo): 47 menu, `failed: []`, `unreadable: []` |
| 3. Rantai lewat layar di build Enteng; penjaga D14-2, D14-3/D15-1, D15-5 tetap menolak | **DITUTUP** | `CP17_BROWSER_R3_03_CHAIN_SEWING_TO_CLOSE`, `_CHAIN_FG_TO_AR_ZERO`, `_GUARDS_REFUSE` PASS di kedua build (run 39184479044). Kas saya tanpa perubahan: runs 39184451023 (1/1) dan 39184458478 (2/2) PASS (FABLE) |
| 4. Layar baru membaca data nyata; akses sesuai katalog; tanpa tulis melewati Native | **DITUTUP** | Kasus CP17 R3_03/R3_04 PASS (run 39184479044). Sumber fasad r3 tidak berubah, kecuali `audit.sql` (R4-03, baca-saja) (INDEPENDENT_SOURCE_REVIEW) |
| 5. Skenario Fable lama tetap lulus, juga di build Enteng | **DITUTUP** | `fable_cp17c_cash_basis.py` dan `fable_r2_cash_both.py` tanpa perubahan: PASS. Sensus layar berjalan di build Enteng (dengan catatan Dashboard di atas) |

## Status temuan Fable

| Temuan | Status | Bukti |
|---|---|---|
| FABLE-016, FABLE-018 (ditutup r3) | **TETAP DITUTUP** | Kasus R3_05 QC/Final SKU dan Nota Ambil Aksesori PASS di kedua build (run 39184479044); prefreeze 31 PASS (run 39184486140) |
| FABLE-012 EXECUTE `authenticated` ke penulis `erp` | **MASIH TERBUKA (ditunda D14-9)** | Tidak berubah. R4-01 menolak sesi Data API di 25 jalur publik lama (termasuk empat pembungkus pool HPP), tetapi itu bukan pencabutan hak langsung `erp` |

## Juga diperiksa (bukan temuan saya)

- **R4-05 penjaga `erp.require_internal()`:** klaim "jawaban sama" bertahan.
  - Tinjauan sumber: probe hanya menjawab saat tidak ada baris konteks backend+transaksi ini; dengan baris apa pun,
    dispatch lama berjalan utuh (INDEPENDENT_SOURCE_REVIEW).
  - Matriks saya sendiri (run 39187095072, FABLE): penjaga terpasang vs penjaga yang sama tanpa probe, yang saya bangun
    ulang dari badan terpasang.
  - Identitas: semua 9 peran aplikasi, OWNER nonaktif, pengguna tak dikenal, JWT tanpa sub, anon, service_role.
  - Keadaan: tanpa id transaksi, dengan id, baris konteks penjualan/pengadaan sendiri, baris yang di-commit transaksi
    sebelumnya.
  - Hasil: 70 sel, 0 beda, termasuk penolakan halus `CP7_SALES_WRITE_DENIED` dan `CP7_SALES_ACCESS_DENIED`.
  - Catatan alat: harness menandai run ini INCOMPLETE karena pengguna uji yang saya commit tidak bisa dihapus semua
    (lihat AUDITOR_TOOL).
- **R4-02 buka ulang PO:** pengecualian "gerakan keluar yang membalik pemasukan positif" aman. Katalog runtime
  menunjukkan:
  - Tiga pembalik gerakan FG terpasang menolak membalik pembalik.
  - Pelepasan reservasi hanya membalik SALE_RESERVE.
  - Retur (SALE_RETURN) tidak pernah menunjuk ke gerakan SALE.
  Jadi pengecualian itu tidak bisa memulihkan atau menyembunyikan pemakaian aktif. Kasus Astra dan kontrol penulis PASS.
- **R4-01 jalur publik:** penolakan `session_user='authenticator'` jadi pernyataan pertama, dan `session_user` tidak
  berubah oleh SECURITY DEFINER. Inisialisasi di bagian DECLARE plpgsql tetap jalan sebelum penolakan; ke-25 rute
  dibuktikan menolak lewat Auth nyata (`CP17_HTTP_R4_01_EVERY_CLOSED_ROUTE_REFUSED_APP_ROUTES_OPEN` PASS). Sensus hanya
  mencakup `public.erp_%`.
- **R4-03 Audit Trail:** tanda = jumlah dan total id di dalam cutoff; log audit hanya bertambah, jadi baris terlambat
  selalu terdeteksi di halaman berikutnya. Kasus jadwal Astra dan tiga kontrol PASS.
- **R4-04 teks terbaca:** kasus keterbacaan penulis PASS di kedua build. Sensus saya tidak mengukur kontras, hanya luapan
  dan label.
- **R4-Q1 pg_cron:** `wait_recorded` hanya menunggu; syarat lulus tidak berubah (sumber). K6 10/10 dan K4 17/17 PASS
  (run 39184494131).
- **Kecepatan analisis (D17-1, D17-2):** angka di runner saya sama dengan pengungkapan penulis.
  - 100 produk dengan angka keuangan: 4,6 s (SQL) dan 5,6 s (browser).
  - 300 produk dengan angka keuangan: analisis langsung **berhenti di batas 8 detik** dengan pesan.
  - "Sedang dihitung sejak" muncul seketika.
  Target 3 detik tidak tercapai dan tidak diklaim tercapai; ini tugas penulis berikutnya (D17-2).
- **Penjaga lama tidak dilonggarkan:**
  - Kas dua basis (kasus saya PASS).
  - Upah tidak mendahului akrual (CP17 FIN01, P12 64/81/43 PASS).
  - Lantai cutover (trigger `cp7_cutover_fg` terpasang; kasus CP17 PASS).
  - Delta Native yang dideklarasikan (F03 Full 8 job PASS, termasuk pemeriksaan definisi persis).
  - Regresi yang bisa dibandingkan sama persis dengan r2–r3: F03 cash 21, misc 20, payment 23, cutting 19, P13 25, sales
    chain 25.

## AUDITOR_TOOL (kesalahan alat saya, dicatat terbuka)

1. Sensus layar tidak mengecualikan pemberitahuan Dashboard (sama dengan r3). Oracle tidak diubah, dan vonis dibaca
   terhadap oracle tertulis.
2. Probe v1 (run 39185025017) kosong maknanya. Pembungkus invoker berhenti di "permission denied" karena `authenticated`
   tidak punya EXECUTE pada penjaga, dan tidak ada pengguna aplikasi yang di-commit. Syarat "bermakna" v1 terlalu lemah.
   Diperbaiki di v2 dengan syarat lebih ketat, tanpa mengubah oracle. Log v1 disimpan.
3. Fixture v2 meninggalkan pengguna uji di database sekali pakai (`LAST_ACTIVE_OWNER_PROTECTED`), sehingga harness
   menandai run INCOMPLETE. Vonis oracle tetap dibaca dari sel-selnya.

## Catatan untuk owner (bukan cacat)

- Analisis langsung belum 3 detik. Untuk 300 produk dengan angka keuangan, analisis langsung masih berhenti di 8 detik
  dengan pesan, bukan memberi angka salah. Ini tugas penulis berikutnya (D17-2).
- Dashboard masih tanpa angka (F-UI-01); angka asli di Dashboard akan jadi permintaan baru.

## Yang harus beres sebelum pemasangan ke Enteng

1. Pasang lapisan database CP7 (CP7C) sebelum UI CP7, lalu jalankan `docs/cp7/cp17/R3_INSTALL_TIME_CHECKS.md` di Enteng.
   Di database lama, layar kesiapan masih gagal 404 (`LEGACY_RUNTIME_GAP`, run 39184486140).
2. FABLE-012 / D14-9: cabut hak panggil langsung `authenticated` ke penulis `erp` sebelum `erp` terbuka ke Data API.
   Penolakan R4-01 tidak menggantikan pencabutan ini.
3. Sahkan tanggal cutover resmi di aplikasi sebelum transaksi operasional pertama (D15-5).
4. Isi data master, tarif mandor dan resep aksesori produk hasil impor sebelum QC atau rework.
5. Kunci CP2 yang terpapar tidak dipakai lagi.
6. Uji ulang kecepatan analisis sesudah pekerjaan D17-2, di runner yang sama, sebelum layar analisis dipakai harian
   dengan angka keuangan.

## Yang belum saya periksa

- Data dan setelan Supabase Enteng: tidak ada akses hosted pada putaran ini.
- Kontras warna teks: hanya lewat kasus keterbacaan penulis; sensus saya tidak mengukurnya.
- Panel detail di balik layar daftar: sensus hanya mencatat tampilan pertama tiap menu.
- Workflow kualifikasi penulis yang tidak saya ulang: receipt mencatat 116 run; saya ulang 12 workflow dan 6 run Fable.
  21 workflow CP6 lama tidak saya ulang.
- Patch backup Sol untuk CP7C (tidak dipasang), alat backup CP7C (D13-9a), red team di luar RBAC, dan pekerjaan auditor
  lain putaran ini (§16.7).

## Pernyataan paparan

Lihat `MANIFEST.md` §Paparan. Tidak ada laporan, cabang, run, artifact atau komentar auditor lain dari putaran r4 yang
dibuka. `HANDOFF_ASTRA.md` dan `HANDOFF_SOL.md` tidak dibuka. Hosted Enteng tidak diakses.

# Fable r4 — log kerja

## CP1 — kandidat dan persiapan (2026-10-19)
- `git diff --name-only 663f6fae origin/claude/new-session-deapao` (kepala 5eda90e1): 9 berkas, semua `docs/`. Tree
  `src`, `scripts`, `supabase` kandidat = kepala.
- `git diff --name-only b53b5acd 663f6fae -- supabase`: kosong.
- Cabang `audit/fable-cp1-7-r4-663f6fae-20261019` dari kunci r3 2033fdfc; workflow Fable diarahkan ke kandidat r4.

## CP2a — oracle baru sebelum run (2026-10-19)
`audit/fable_cp7/scenarios/fable_r4_probes.py` (oracle di docstring, ditulis sebelum run):
- `FABLE_R4:GUARD_SAME_ANSWER_MATRIX` — coba patahkan klaim R4-05 "jawaban sama": penjaga terpasang vs penjaga yang sama
  tanpa probe (dibangun ulang Fable dari badan terpasang, atribut SECURITY/config, pemilik dan hak EXECUTE disamakan),
  tiap jawaban di transaksi baru pada koneksi kedua sebagai sesi Data API. Matriks: semua peran aplikasi aktif di
  `erp.app_users`, pengguna nonaktif bila ada, pengguna tak dikenal, JWT tanpa sub, anon, service_role × FRESH (tanpa id
  transaksi), XID, baris konteks penjualan/pengadaan transaksi ini, baris konteks yang di-commit transaksi sebelumnya di
  backend yang sama. Beda jawaban di sel mana pun → COUNTEREXAMPLE.
- `FABLE_R4:FG_REVERSAL_PATHS` — bahan baca (INFO, bukan vonis) untuk R4-02: bentuk gerakan FG di data, semua fungsi yang
  menulis `erp.fg_stock_movements`, dan apakah tabel sendiri menolak pembalik dari pembalik. Pertanyaannya: apakah ada jalur
  Native yang membuat gerakan keluar yang membalik pemasukan positif, padahal pemasukan itu sendiri mengimbangi pemakaian
  (pembalik dari pembalik, atau retur yang menunjuk ke gerakan SALE). Kalau ada, aturan R4-02 bisa menyembunyikan pemakaian
  aktif.
- R4-Q1 (sumber): `wait_recorded` hanya menunggu; nilai baliknya diabaikan dan run dinilai seperti sebelumnya (minimal satu
  run selesai, semua run berhasil). Syarat lulus tidak berubah (INDEPENDENT_SOURCE_REVIEW).

## CP3a — run Fable pada kandidat (dibaca per kasus dari log)
| Run | Isi | Hasil per kasus | Label |
|---|---|---|---|
| 39184451023 | `fable_cp17c_cash_basis.py` tanpa perubahan | `FABLE_CP17C:CASH_BASIS_MISMATCH` PASS; cp6_restored true | FABLE |
| 39184458478 | `fable_r2_cash_both.py` tanpa perubahan | 2/2 PASS (CASH_BOTH_BASES_INVARIANT, DETECTOR_BOOK_DATE) | FABLE |
| 39184465655 | sensus `fable_r3_screens.mjs` tanpa perubahan, build DISPOSABLE | TUTUP_BUKU_TAB PASS; OWNER 1440, OWNER 390, GUDANG: COUNTEREXAMPLE dengan satu-satunya pelanggaran Dashboard `boundary` (pemberitahuan F-UI-01). 47/47 menu terbuka di 1440 dan 390, 0 label contoh, 0 luapan; GUDANG 7/7 menu, tanpa Keuangan | FABLE; Dashboard = AUDITOR_TOOL seperti r3 |
| 39184472280 | sensus yang sama, build ENTENG | identik; 159 permintaan origin Enteng dijawab loopback, 0 error rute | FABLE |

Modul sensus sengaja tidak diubah dari r3 (sha sama dengan kunci r3), supaya hasilnya sebanding; vonis Dashboard dibaca
terhadap oracle 1 tertulis (pemberitahuan tanpa angka diizinkan), sama dengan r3.

## CP3b — probe r4 v1 (run 39185025017) kosong maknanya: kesalahan alat saya
- `GUARD_SAME_ANSWER_MATRIX` v1 berstatus PASS tetapi **bukan bukti**. `authenticated` dan `anon` tidak punya EXECUTE
  pada `erp.require_internal()`, sehingga pembungkus invoker saya berhenti di "permission denied" untuk kedua versi.
  Koneksi kedua juga tidak melihat pengguna aplikasi yang di-commit, jadi matriks hanya punya UNKNOWN_USER, JWT tanpa sub,
  anon dan service_role. Hanya service_role yang mencapai penjaga (ALLOW = ALLOW). Syarat "bermakna" v1 terlalu lemah,
  karena menerima penolakan hak sebagai penolakan. Dicatat terbuka sebagai AUDITOR_TOOL; log run pertama disimpan
  (`runs/PROBES_R4_v1_39185025017.json`).
- `FG_REVERSAL_PATHS` v1: data FG kosong pada titik itu. Satu-satunya fungsi yang meng-insert gerakan FG adalah
  `erp.post_fg_movement()`, yang tidak mengisi `reversal_of_id`; pembalik mengisinya lewat UPDATE. Tidak ada trigger atau
  constraint tabel yang melarang pembalik dari pembalik (hanya FK, cek tipe, cek qty≠0, penjaga tanggal masa depan,
  penjaga cutover, penjaga tabel sistem).
- Perbaikan alat v2 (oracle sama, syarat "bermakna" diperketat, lihat docstring): pembungkus SECURITY DEFINER milik
  postgres seperti fasad CP7; satu pengguna aplikasi per kode peran dan satu OWNER nonaktif di-commit untuk matriks;
  FRESH wajib ALLOW untuk peran internal dan wajib memunculkan penolakan penjaga sendiri. FG: daftar semua badan fungsi
  terpasang yang mengisi `reversal_of_id`.

## CP3c — workflow penulis dijalankan ulang (ref `claude/new-session-deapao`, head 5eda90e1, tree produk = kandidat)
Status dibaca per kasus dari baris JSON log (INDEPENDENT_NATIVE_RERUN):
| Run | Workflow | Hasil |
|---|---|---|
| 39184479044 | CP7 CP17 Fixes | 341/341 PASS + `CP6_AUDITOR_PUBLIC_STATE_STABLE_ORDER` (Native 161, race 39, HTTP 27, browser 57, browser build Enteng 57). 20 kasus R4 semua PASS. Grup Enteng: 1.361 permintaan dijawab loopback, 0 error rute |
| 39184486140 | Pre-freeze UI | 31 PASS + 2 INCOMPLETE `LEGACY_RUNTIME_GAP` lama (sama dengan r3) |
| 39184502576 | F03 Full Retained (8 job) | p09 135, p10 34, p11 64, p12 91, p13 50, cash_installments 61, customer_refund 10, supplier_credit 5: semua PASS |
| 39184511169 / 39184519333 / 39184528182 | F03 cash / misc corr / payment corr | 21 / 20 / 23 PASS (sama dengan r2–r3) |
| 39184536564 | P12 payroll (3 job) | roster 64, attendance-write 81, payroll-review 43 PASS (sama) |
| 39184544615 / 39184552527 / 39184560474 | cutting corr / P13 / sales chain | 19 / 25 / 25 PASS (sama) |
| 39184567627 | UI phone width (build demo) | `{"menus":47,"failed":[],"unreadable":[]}` |
| 39184494131 | P19 Analysis Job Transport (12 job) | masih berjalan saat dicatat |

## CP2b — tinjauan sumber (INDEPENDENT_SOURCE_REVIEW)
- **R4-05 penjaga `erp.require_internal()`** (`scripts/cp7_internal_guard_bundle.py`). Probe disisipkan tepat sesudah
  anchor. `contexts()` memastikan semua isi antara anchor dan uji peran akhir hanya cabang
  `if exists(select 1 from <ctx> c where c.backend_pid=pg_backend_pid() and c.transaction_id=txid_current() and case when
  <filter identitas yang sama> … else false end) then return;end if;` plus komentar. Cabang semacam itu hanya bisa *mengizinkan*,
  dan hanya lewat baris backend+transaksi ini, karena filter identitas diulang di WHEN dan AND di dalam ekspresi dievaluasi
  berurutan dengan short-circuit. Jadi tanpa baris seperti itu jawabannya = uji peran akhir, dan probe menjawab persis kasus
  itu. Dengan baris apa pun, dispatch lama berjalan utuh. `verify()` membangun ulang probe dari dispatch terpasang, sehingga
  cabang konteks baru yang ditambahkan delta lain akan gagal. Satu beda samping: versi lama memanggil `txid_current()` dan
  karena itu memberi id transaksi pada transaksi baca; versi baru tidak. Tidak mengubah jawaban.
- **R4-01 jalur publik** (`scripts/cp7_public_routes_bundle.py`). Penolakan `session_user='authenticator'` disisipkan sebagai
  pernyataan pertama: untuk SQL sebagai `select` pertama, untuk plpgsql sesudah `begin` pertama. `session_user` tidak
  berubah oleh SECURITY DEFINER atau SET ROLE. Catatan: inisialisasi di bagian DECLARE tetap berjalan sebelum penolakan, dan
  `begin` yang ada di dalam string DECLARE akan salah tempat. Itu tertangkap kasus HTTP penulis yang memanggil ke-25 rute
  lewat Auth nyata (PASS). Sensus hanya mencakup `public.erp_%` non-CP7; fungsi `public` tanpa awalan `erp_` di luar
  cakupannya (bukan temuan; pemeriksaan RBAC saya di cp17 mencakup `public.erp_*`). Batas SQL langsung tetap FABLE-012/D14-9.
- **R4-03 Audit Trail** (`audit.sql`). Tanda = jumlah dan total id baris di dalam cutoff yang cocok filter. Log audit hanya
  bertambah, jadi baris terlambat selalu mengubah tanda. Kursor tanpa cutoff, atau tanda kursor ≠ tanda kiriman, ditolak.
  Baris terlambat yang commit sesudah halaman terakhir dibaca tidak terdeteksi sampai Muat ulang; semantiknya sama dengan
  baris baru biasa. Bukan temuan.
- **R4-02 buka ulang PO** (`po-reopen.sql`). Gerakan keluar yang membalik pemasukan positif tidak dihitung pemakaian.
  Risikonya: pembalik dari pembalik suatu pemakaian, atau retur yang menunjuk ke gerakan SALE, akan menyembunyikan
  pemakaian. Di pohon hanya `erp._release_sale_draft_reservations` yang mengisi `reversal_of_id` (target SALE_RESERVE).
  Pembalik lain ada di skema dasar di luar pohon, jadi diperiksa runtime lewat katalog (probe v2).
- **R4-Q1**: syarat lulus K4/K6 dan fixture K4 tidak berubah (lihat CP2a).
- **R4-04**: hanya CSS warna teks. Sensus saya (luapan/label) dan sensus keterbacaan penulis (CP17 R4_04 desktop/HP, kedua
  build; phone width `unreadable: []`) PASS.

## CP3d — probe v2 (run 39187095072) dan P19 (run 39184494131)
- `GUARD_SAME_ANSWER_MATRIX` v2: **70 sel, 0 beda**. Identitas: OWNER, ADMIN, STAFF, AUDITOR_VIEW_ONLY, CUSTOMER, GUDANG,
  KEUANGAN, PRODUKSI_QC, SALES_KASIR, OWNER nonaktif, pengguna tak dikenal, JWT tanpa sub, anon, service_role × FRESH,
  XID, baris konteks penjualan sendiri, baris konteks pengadaan sendiri, baris konteks yang di-commit transaksi sebelumnya.
  FRESH tanpa id transaksi di semua sel; OWNER/ADMIN/service_role ALLOW, lainnya penolakan penjaga sendiri. Dengan baris
  konteks penjualan sendiri, penolakan halus (`CP7_SALES_WRITE_DENIED`, `CP7_SALES_ACCESS_DENIED`) sama persis di kedua
  versi; GUDANG dengan baris pengadaan ALLOW di keduanya. Vonis oracle: **PASS (FABLE)**. Harness menandai kasus
  INCOMPLETE dan `cp6_restored:false` karena fixture saya (pengguna yang di-commit) tidak bisa dihapus semua: OWNER saya
  dilindungi `LAST_ACTIVE_OWNER_PROTECTED`, sehingga tersisa 1 baris auth, baris `app_users` dan `audit_logs`. Itu efek
  samping alat saya di database sekali pakai, bukan perilaku produk. Tidak ada rerun (§1.9).
- `FG_REVERSAL_PATHS` v2 (INFO, dibaca saya): ada 7 fungsi terpasang yang mengisi `reversal_of_id`. Tiga pembalik gerakan
  FG (`erp.reverse_fg_movement` dan salinan di `cp7_note`, `cp7_sales_return_correction`) menolak "Cannot reverse a
  reversal" dan "already reversed". `erp._release_sale_draft_reservations` hanya membalik SALE_RESERVE. Tiga lainnya untuk
  jurnal. `erp.post_fg_movement` tidak pernah mengisi `reversal_of_id`, jadi SALE_RETURN tidak menunjuk ke SALE. Artinya
  gerakan keluar yang membalik pemasukan positif selalu pembalik pemasukan asli, tidak pernah memulihkan pemakaian. Aturan
  R4-02 tidak bisa menyembunyikan pemakaian aktif lewat rantai pembalik (INDEPENDENT_SOURCE_REVIEW, katalog runtime).
- P19 (12 job, semua PASS per kasus): scale5 5/5, k6-proof-runner 10/10 (termasuk `K6P_RACE_PG_CRON_FINISHES_PASS`),
  k4-runner 17/17 (termasuk `K4R_RACE_PG_CRON_FINISHES_JOB`), staged 14/14. Angka di runner saya:
  - Tangga SQL, 100 target: tanpa angka keuangan 1,23 s; dengan angka keuangan 4,57–4,62 s.
  - Tangga SQL, 300 target: tanpa angka keuangan 3,42 s; dengan angka keuangan **dihentikan di 8,0 s** (57014,
    statement timeout) di kedua jendela.
  - Browser, 100 target: hasil 1,77–2,61 s; dengan angka keuangan 5,63–5,67 s.
  - Browser, 300 target: hasil 5,2–6,7 s; dengan angka keuangan langsung ditolak di 8,05–8,06 s (pesan penolakan
    tampil).
  - "Sedang dihitung sejak" tampil 8–49 ms sesudah klik (klaim R4-05 UI benar).
  Semua sesuai pengungkapan penulis (`P19_R4_05_DIRECT_LATENCY.md` bagian Qualification run). Target 3 detik tidak
  tercapai dan tidak diklaim tercapai (D17-1, D17-2).

## CP4 — kunci
`RETEST_FABLE_663f6fae.md`, `FINDINGS.json`, entri ledger r4 (`runs/dispatch_ledger_r4.jsonl`) dan `LOCK.md` dikunci
dengan commit sebelum membaca pekerjaan auditor lain putaran r4.

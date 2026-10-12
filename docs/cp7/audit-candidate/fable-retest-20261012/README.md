# Perbaikan temuan audit penuh CP7 Fable — kandidat uji ulang 12 Okt 2026

Audit penuh CP7 Fable atas `d0b9e9c2` (cabang `audit/fable-cp7-full-d0b9e9c2-20261011`,
`audit/fable_cp7/AUDIT_FABLE_d0b9e9c2.md`) memberi **HOLD** dengan tiga temuan major (F-OPS-01, F-OPS-02, F-UI-01),
sembilan minor dan tiga observasi. Handoff Fable: "Writer boleh diminta perbaiki tiga temuan major, lalu kandidat baru
diuji ulang dengan kasus Fable yang sama." Paket ini adalah kandidat perbaikannya. Bukti writer (WRITER_CROSSCHECK),
bukan penerimaan auditor. `production_go:false`.

## Identitas

- **Commit sumber: `ddedf06cceb290549dbc7b9d5e1d4a0fbd3f064f`**, cabang `claude/new-session-deapao`.
- Selisih dari `d0b9e9c2` yang diaudit: `SOURCE_DELTA.json` — 45 berkas, 27 bukan dokumen. Termasuk perbaikan ASF-F01
  (`5f1506f4`, paket `../asf-f01-retest-20261012/`).
- Commit sesudahnya hanya dokumen; buktikan dengan `git diff --name-only ddedf06c HEAD`.

## Keputusan owner 12 Okt (dari dua pertanyaan Fable §7)

Dicatat di `../../OWNER_DECISIONS_20261008.md` bagian "Keputusan owner 12 Okt":

1. Dashboard mode terhubung: **sembunyikan** angka contoh.
2. Kebijakan PL-5 B: **owner saja** yang boleh mengubah; admin hanya melihat; diperiksa di server; tiap perubahan versi
   baru dengan alasan, waktu dan identitas owner; analisis dan riwayat lama tetap memakai versi asalnya.

## Temuan major

| Temuan | Perbaikan | Kasus writer (kasus Fable yang sama dijalankan auditor) |
|---|---|---|
| **F-OPS-01** backup bisa menghapus database lain | `scripts/cp7_nightly_backup.py`: database scratch diberi tanda milik alat (komentar database). Database yang sudah ada tanpa tanda itu ditolak (`BACKUP_SCRATCH_EXISTS_NOT_OURS`) dan dibiarkan; malam itu tidak terverifikasi dan tidak memangkas apa pun. Scratch dibuat dengan `createdb` **tanpa menghapus dulu**, jadi database bernama sama yang muncul sesudah pemeriksaan membuat `createdb` gagal, bukan terhapus. Yang dihapus hanya database yang dibuat alat ini atau bertanda miliknya. Nama scratch bebas selain sumber dan `postgres`. | `K3C_RACE_BACKUP_SCRATCH_NEVER_DROPS_ANOTHER_DATABASE` (database asing ditolak dan utuh; database yang muncul sesudah pemeriksaan tidak terhapus; nama bebas yang kosong dipakai lalu dihapus; sisa bertanda dipakai ulang). Kontrol negatif lokal: langkah lama "hapus lalu buat" menggagalkan kasus ini. |
| **F-OPS-02** pembersihan mengunci tabel | `scripts/cp7-src/planning/analysis-stages.sql`: `clean_done`, `purge_expired` dan `purge_intermediates` tidak lagi memakai `alter table … disable trigger`. Trigger tabel kerja `cp7_analysis_stage.work_immutable()` hanya mengizinkan DELETE untuk job yang disebut di setelan transaksi `cp7.analysis_work_delete` (halaman: run di `cp7.analysis_work_delete_run`); selain itu tetap `55000 CP7_RUN_IMMUTABLE`. Setelan dikosongkan lagi sesudah hapus. DELETE hanya memakai kunci ROW EXCLUSIVE, jadi INSERT unit job lain tidak menunggu. `purge_expired` mendapat `lock_timeout` 2 detik. Bundel memeriksa ketiga fungsi tidak memuat `disable trigger`. | `K3C_RACE_CLEANUP_BESIDE_RUNNING_STEP` (`clean_done` dan `purge_expired(100)` ditahan terbuka; step job lain menyimpan unit dengan `unit_attempts` 0 di bawah 8 dtk; izin hapus tidak bisa menghapus baris job lain, tidak bisa mengubah baris). `K3C_RACE_BUSY_TABLE` kini memakai kunci baris. Kontrol negatif lokal: SQL lama membuat step 8,5 dtk lalu gagal. |
| **F-UI-01** Dashboard menampilkan angka karangan | `src/OwnerDashboard.tsx`: di mode terhubung (`runtime.mode !== 'DEMO_SIMULATION'`) Dashboard hanya menampilkan judul dan keterangan "Ringkasan angka belum tersambung ke data ERP" (`role="status"`); tidak ada angka, tanggal atau grafik contoh. Mode demo tidak berubah. | `src/OwnerDashboard.dom.test.tsx` (2 uji: mode terhubung tanpa angka Rp/tanggal contoh; mode demo tetap). Kasus browser Fable `FABLE_UI:LANDING_NO_FABRICATED_FIGURES_{DESKTOP,MOBILE}` dijalankan auditor. |

## Keputusan owner PL-5 (OBS-01)

`scripts/cp7-src/plan-native/history-yield.sql`: tabel versi hanya menerima `actor_role='OWNER'`; akses tulis menolak
selain owner (`CP7_YIELD_POLICY_OWNER_REQUIRED`), `manage_allowed` hanya untuk owner; versi hanya ditambah. Hasil
pengesahan rencana (`plan-native/commands.sql`, `staged.sql`) menyimpan `new_start_yield` termasuk revisi kebijakan yang
dipakai, sehingga kebijakan baru tidak mengubah rencana lama. Layar `NativeHistoryYieldPolicyPanel.tsx`: "Hanya pemilik
yang dapat menyimpan kebijakan ini; admin dan pengguna lain hanya dapat melihat." Kasus `scripts/cp7_pl5_history_yield_cases.py`,
deklarasi `../../pl5/PL5_HISTORY_YIELD.json`, uji layar `src/NativeHistoryYieldPolicyPanel.dom.test.tsx`.

## Temuan minor dan observasi

| Temuan | Disposisi | Bukti writer |
|---|---|---|
| F-OPS-03 verifikasi membandingkan dengan sumber hidup | **Diperbaiki.** Sumber dibaca dalam satu snapshot yang diekspor (`pg_export_snapshot()`); `pg_dump --snapshot` memakai snapshot itu dan hash tabel sumber dihitung di transaksi yang sama. Tulisan selama backup tidak lagi membuat malam itu tidak terverifikasi. | `K3C_RACE_BACKUP_VERIFIED_UNDER_WRITES` (penulis menulis ratusan baris selama backup; tetap terverifikasi). |
| F-OPS-04 `--database` jadwal tidak dicek | **Diperbaiki.** `scripts/cp7_schedule.py`: `--database` wajib sama dengan `current_database()` dari `--erp-url` (`CP7_SCHEDULE_DATABASE_MISMATCH`); `uninstall` wajib `--removal-approved`. | Pemeriksaan di kasus K3 jadwal (`schedule.same_database`). |
| F-AN-01 >5.000 target tidak ditolak saat request | **Diperbaiki.** `request()` menolak dengan `CP7_ANALYSIS_STAGED_TARGET_LIMIT` (detail `refused_at=REQUEST`) sebelum job atau acuan disimpan. | `scripts/cp7_p19_staged_cases.py` (batas diturunkan di savepoint: ditolak, 0 job/acuan/unit/halaman); uji `tests/cp7/families/f05-staged-api.test.ts` diubah dari "diterima" ke "ditolak, 0 job". |
| F-PAY-01 tanggal bayar gaji memakai jam server | **Tidak terulang pada tumpukan terpasang.** Fable mengutip migrasi `20260901023200` (cek `current_date`), tetapi fungsi Native itu sudah diganti di `v2.6.20ac` (`20260915031500`, juga rilis CP6 T3) menjadi `payment_date > (statement_timestamp() at time zone 'Asia/Jakarta')::date`. Kode tidak diubah; kasus baru membuktikannya. | `P12_SETTLEMENT_WIB_PAYMENT_DATE`: jam sesi digeser ke UTC−12 (hari sebelum WIB) dan/atau UTC+14 (hari sesudah WIB) — tanggal WIB hari ini diterima, besok WIB ditolak, tanpa tulisan sebagian. Dijalankan lokal pukul 00.06 WIB (jam yang dikhawatirkan Fable): lulus; kontrol negatif dengan cek `current_date` lama: kasus gagal dengan "masa depan". |
| F-AP-01 kredit kelebihan bayar ke nota yang datang belakangan | **Tidak diubah: keputusan owner 2 Okt** ("kreditnya bisa gw tempel di next nota mana pun simple"). Tanggal bayar tetap tanggal uang keluar sungguhan, jadi di nota tujuan pembayaran itu bisa bertanggal sebelum barangnya datang; berbeda dari bayar supplier biasa yang menolak bayar sebelum barang datang, dan disengaja. Ditulis jelas di `../../RECEIPT_CORRECTION.md`. | `RF_OVERPAID_CREDIT_TO_NEXT_NOTA` kini menegaskan tanggal bayar < tanggal datang nota tujuan. |
| F-TOOL-01 receipt tidak menampilkan pengulangan tanggal | **Diperbaiki.** Akar masalah sudah ditutup di ASF-F01 (`5f1506f4`: FAIL produk tidak lagi diulang). Tambahan: setiap baris `RERUN_FROM_FRESH_COPY`/`KEPT_FIRST_RESULT` juga menjadi anotasi peringatan GitHub (`AUDITOR_BUSINESS_DAY_*`), dan alat baru `scripts/cp7_ci_receipt.py` mencantumkannya per job (`business_day_reruns`, `business_day_kept_first`) lewat API tanpa mengunduh log. | `scripts/cp6_auditor_business_day_test.py` (25 uji, termasuk anotasi). `CI_RECEIPT.json` paket ini dibuat dengan alat itu. |
| F-TOOL-02 probe PR44 basi | **Diperbaiki (alat uji).** Probe `scripts/cp7_astra_timeline_reuse_probe.mjs` sebenarnya sudah tidak bisa jalan sejak `a68abf1e` (7 Okt), bukan hanya sejak K7a: (1) daftar fungsi kini mengharapkan `source_within` dan `matching_models_within` dengan pemeriksaan turunan persis (badan lama + hanya batas yang dijadikan parameter; nama lama pembungkus satu baris pada batas lama; di luar badan fungsi hanya komentar dan baris owner K7a); (2) jangkar mutan `ignores_supply` mengikuti kondisi baru `a68abf1e` (tetap hanya membuang uji "tanpa pasokan"); (3) jumlah kasus 571 → 595 karena dua defect bersama baru dari `a68abf1e` (`DUP_ROW_SKIPPED_TARGET`, `DUP_ROW_SKIPPED_FG`), diperiksa ada. Oracle paritas (byte dan penolakan pertama sama dengan pendahulu terkunci) tidak berubah. | Lokal (bukan bukti): 595/595 identik, 2/2 mutan tertangkap. Workflow `CP7 Astra Timeline Reuse` dijalankan pada commit ini. |
| F-TOOL-03 fixture tanggal D12 di probe CP6 | **Tidak diubah (CP6 beku).** `scripts/cp6_bd_probe.py` adalah alat CP6 yang dibekukan. Merah palsu hanya pada `reject_after_invoice` (12 cek bisnis lain lulus) bila tanggal "Juni" fixture jatuh pada tanggal 1 bulan 31 hari (terlihat 11 Okt 2026). Auditor mengklasifikasikan sebagai WRITER_TEST_FIXTURE_DATE (POLA-21) bila tanggalnya cocok. | — |
| F-UI-02 UI kandidat di atas paket CP6 saja | **Dicatat, tidak diubah.** UI CP7 memanggil RPC CP7; UI ini dipasang hanya bersama paket CP6+CP7. Oracle browser CP6 dijalankan di tumpukan CP7 penuh oleh `CP7 Pre-freeze UI Regression`. | Run pre-freeze pada commit ini. |
| F-DOC-01 panduan tanpa tambahan PR #42 | **Diperbaiki.** Isi PR #42 (`d684b21a`, Fable + Astra) dimasukkan utuh ke `docs/AUDIT_PANDUAN_PRO_MAX.md` dengan penggabungan tiga arah terhadap `31ee23f0`: +138/−0 baris; semua baris versi PR #42 ada kecuali tiga baris yang sudah diperbarui untuk Sol; log revisi §15 mencatatnya. | `git diff d0b9e9c2 ddedf06c -- docs/AUDIT_PANDUAN_PRO_MAX.md` |
| OBS-01 siapa boleh ubah PL-5 | **Diputuskan owner 12 Okt: owner saja** (di atas). | |
| OBS-02 kapasitas v2 tidak mengurangi grup manual sesudah snapshot | **Tidak diubah.** Sesuai kalimat kontrak §3; sifat F01 terbukti. | |
| OBS-03 10 jalur tanpa `CP7_FRESH_ACCESS_REQUIRED` | **Tidak diubah.** Tidak terjangkau lewat PostgREST; dicatat untuk ringkasan kode CP7.5. | |

## CI pada satu commit (`CI_RECEIPT.json`)

_Diisi sesudah semua run selesai._

## Yang tetap terbuka

- Penerimaan area optimasi timeline PR44 oleh auditor yang tidak menulisnya (Astra penulisnya; Fable boleh).
- K4 browser mobile sempat diam dua kali sebelum ada batas waktu kasus (alat uji, penyebab belum ditemukan).
- Belum diuji: HP fisik/Safari, tab HP yang benar-benar ditutup, pemasangan hosted, 5.000 target seluruhnya lewat
  penjalan K4. Jadwal dan backup belum dipasang; tujuan simpan backup di luar database belum ditentukan (syarat Fable §2.5).
- `independent_acceptance=false`, `installed_P21_acceptance=false`, `production_go=false`.

Untuk auditor: `AUDITOR_RETEST.md`.

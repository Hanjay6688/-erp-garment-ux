# Audit penuh CP7 — kandidat `d0b9e9c2` — auditor independen Fable

**Status laporan:** DRAFT v0.9 (12 Okt 2026, ~03:30 UTC). Dua run Fable terakhir (kasus AI baca-saja, kasus UI browser) masih berjalan; bagian yang menunggu diberi tanda ⏳. Tidak ada klaim di bawah ini yang bergantung pada kedua run itu kecuali yang ditandai.

| | |
|---|---|
| Kandidat | commit `d0b9e9c2e41a9f0f3a138346887434fd7d3c14f0`, tree `4bd5e1acf55f0b441d9c8f67949ee5b070eb9c41`, cabang `claude/new-session-deapao` (head `5548ff18`, selisih hanya `docs/`) |
| Tree produk dipin | src `fa7f62e2f59a`, supabase/release `be1e91c172ff`, supabase/migrations `8f6053bbd0bd`, supabase/dev `88759f4fc518`, scripts/cp7-src `e396ea69049a` |
| Panduan | `docs/AUDIT_PANDUAN_PRO_MAX.md` versi PR #42 (perintah owner 6 Okt). Versi di cabang kandidat adalah versi lama (lihat F-DOC-01) |
| Cabang audit | `audit/fable-cp7-full-d0b9e9c2-20261011` (hanya berkas audit) |
| Batas yang dipatuhi | tidak ada push ke cabang penulis/`main`/`cp7/integration`; tidak menyentuh hosted/legacy/Cloudflare; tidak memasang pg_cron/backup di luar salinan sekali pakai; oracle tidak dilonggarkan; log gagal pertama disimpan; laporan auditor lain putaran ini (`audit/astra-cp7-full-d0b9e9c2-*`) **tidak dibaca** |
| Status tetap | `independent_acceptance=false` sampai syarat §2 terpenuhi; `installed_P21_acceptance=false`; `production_go=false` |

## 1. Ringkasan untuk owner (bahasa sehari-hari)

Mesin CP7-nya sendiri sehat: semua 15 workflow kualifikasi penulis saya jalankan ulang sendiri pada kode yang sama dan 2.493 kasus lulus per kasus, ditambah kasus milik saya untuk hal paling berisiko (kunci kapasitas rencana v1+v2, batas 8 detik, rumus yield, segel laporan, akses skema) juga lulus. Yang belum boleh: **memasang jadwal server dan backup malam**, karena saya menemukan dua cacat operasional nyata di bagian itu: (1) skrip backup bisa **menghapus database lain** kalau nama `--scratch` salah, dan (2) pembersihan data kerja **mengunci tabel** sehingga analisis yang sedang berjalan tertahan 8 detik dan dihitung sebagai percobaan gagal; pembersihan harian kadaluwarsa bisa menggagalkan job. Satu cacat UI: halaman depan (Dashboard) menampilkan **angka uang karangan** (Rp284,6 jt dst.) di semua mode tanpa tulisan "simulasi". Sisanya temuan kecil (tanggal payroll pakai jam server, tanggal replay pembayaran koreksi, pesan penolakan 5.001 target, alat uji). Vonis saya: **TAHAN (HOLD)** untuk izin jadwal dan backup sampai tiga hal itu diperbaiki dan diuji ulang; CP7 inti layak lanjut ke tahap berikut. PR #45 tetap ditahan (sudah dijawab). Keputusan owner yang masih perlu: dua pertanyaan di §7, masing-masing sudah ada rekomendasinya.

## 2. Vonis akhir CP7 dan syaratnya

**Vonis: HOLD — CP7 inti LULUS pada 14 dari 18 area; 3 area GAGAL karena temuan major (K3b pembersihan, F02/F03 jadwal-backup, UI); 1 area menunggu run ⏳.** `production_go:false` tetap. Penerimaan independen belum saya tulis.

Syarat sebelum owner memberi izin **memasang jadwal** (`cp7-staged-cleanup`, `cp7-staged-retention`, `cp7-staged-runner`, `cp7-proof-runner`):
1. F-OPS-02 diperbaiki: `clean_done`/`purge_expired` tidak boleh memakai `alter table … disable trigger` (kunci tabel) saat ada analisis berjalan; `purge_expired` wajib punya penundaan dan `lock_timeout` seperti `clean_pending`, atau hapus lewat jalur yang tidak mengunci tabel (misal izin hapus per sesi yang dihormati trigger). Bukti ulang: kasus Fable `FABLE_CORE:CLEANUP_LOCK_VS_RUNNING_STEP` harus PASS (step tidak lagi menunggu/dibatalkan), plus suite `k3-cleanup-19` dan `k4-runner-17`.
2. Jadwal dipasang hanya lewat `scripts/cp7_schedule.py install --installation-approved` pada database yang namanya dicek sama dengan `current_database()` (F-OPS-04), dan receipt pemasangan disimpan.

Syarat sebelum izin **backup malam**:
3. F-OPS-01 diperbaiki: `cp7_nightly_backup.py` menolak `--scratch` yang menunjuk database yang sudah ada dan bukan buatannya (atau wajib berawalan `cp7_backup_`), dan nama scratch dicatat di receipt. Bukti ulang: `FABLE_CORE:BACKUP_SCRATCH_DROPS_FOREIGN_DB` harus PASS (database lain tetap ada).
4. F-OPS-03 ditutup salah satu: verifikasi membandingkan hasil restore dengan **isi dump** (bukan sumber hidup), atau receipt menyatakan jelas bahwa malam dengan tulisan selama backup dicatat "belum terverifikasi" dan owner menerima itu tertulis.
5. Tujuan simpan di luar database ditentukan dan diuji sekali (template workflow masih menulis ke runner sementara).

Syarat UI (sebelum pemakaian terhubung oleh pengguna selain owner):
6. F-UI-01 diperbaiki: Dashboard di mode terhubung tidak menampilkan angka karangan (tampilkan angka Native atau sembunyikan kartu dengan label jelas).

## 3. Daftar temuan

Keparahan: blocker = uang/stok/HPP salah atau data hilang tanpa peringatan; major = kehilangan data karena satu kesalahan wajar, atau fitur yang dijanjikan tidak bekerja dalam kondisi normal; minor = selisih kontrak tanpa dampak uang, atau alat uji.

| ID | Area | Keparahan | Temuan | Reproduksi | Bukti | Dampak |
|---|---|---|---|---|---|---|
| F-OPS-01 | Jadwal & backup (F03) | **major** | `scripts/cp7_nightly_backup.py` menjalankan `dropdb --if-exists --force <scratch>` dengan pagar hanya `scratch != source and scratch != 'postgres'` (`cp7_nightly_backup.py:95-99,151`). Nama `--scratch` yang menunjuk database lain yang sudah ada **menghapusnya**, lalu backup tetap "terverifikasi". | Di salinan: `create database fable_victim_db`; jalankan `nightly.backup(admin, source, 'fable_victim_db', dest)`; cek `pg_database`. | Fable native race `FABLE_CORE:BACKUP_SCRATCH_DROPS_FOREIGN_DB` run 38196137312 job 114639081720: `victim_existed_before=true, victim_exists_after=false, restore_verified=true` → FAIL. Sumber: R3 D2. | Kehilangan database karena satu argumen salah saat memasang backup; tidak ada peringatan. Syarat §2.3. |
| F-OPS-02 | Retensi/hapus sesudah DONE (K3b), K2, K4 | **major** | `clean_done` dan `purge_expired` menghapus data kerja dengan `alter table … disable trigger` per tabel (`planning/analysis-stages.sql:2326-2334`, `:2235-2248`) = kunci SHARE ROW EXCLUSIVE sampai transaksi selesai. INSERT unit dari halaman atau penjalan K4 menunggu; dengan batas 8 detik ia dibatalkan dan dihitung `unit_attempts+1` (3 → `CP7_ANALYSIS_STAGE_STOPPED`/FAILED). `clean_pending` punya penundaan 10 menit dan `lock_timeout` 2 detik; `purge_expired` (harian 02:30 WIB, sampai 200 job) **tidak punya keduanya**. | Sesi A: `begin; select cp7_analysis_stage.clean_done(<job DONE>)` tahan; sesi B (8 s): `erp_cp7_step_staged_analysis_v1(<job RUNNING>)`. | Fable `FABLE_CORE:CLEANUP_LOCK_VS_RUNNING_STEP` (run 38196137312): `cleanup_state=CLEANED, step_seconds=8.01, unit_attempts=1` → FAIL. Sumber: R3 D5, R2 D2. | Analisis 5.000 target yang berjalan saat pembersihan/purge bisa gagal tanpa sebab produk; penjalan server kehilangan menit. Syarat §2.1. |
| F-UI-01 | UI | **major** | Halaman Dashboard (landing default untuk setiap peran dengan `dashboard.view`) menampilkan angka karangan — "Rp284,6 jt", "Rp418,2 jt", "Rp176,8 jt", "Rp298,4 jt", "Kamis, 27 Agustus 2026", grafik tetap — di **semua mode** termasuk UAT/DISPOSABLE (`src/App.tsx:629-634, 780-782`), tanpa label simulasi di komponennya; hanya badge topbar yang menyiratkan data tidak nyata. | Login peran apa pun di build DISPOSABLE_TEST → halaman pertama. | Review sumber (R6 B6, diverifikasi Fable pada App.tsx:780-782). ⏳ Browser Fable `FABLE_UI:LANDING_NO_FABRICATED_FIGURES_*` (run dispatched 12 Okt ~03:20 UTC). | Owner/kasir bisa membaca kas, piutang, HPP yang bukan angka ERP. Melanggar "tanpa angka palsu". Syarat §2.6. |
| F-OPS-03 | Jadwal & backup (F03) | minor (desain) | Verifikasi backup membandingkan hash tabel **sumber hidup sesudah restore** dengan hasil restore (`cp7_nightly_backup.py:181-184`). Setiap tulisan ke sumber selama backup membuat `restore_verified=false` dan malam itu tidak memangkas. | Jalankan backup sambil ada tulisan ke tabel CP7. | Fable `FABLE_CORE:BACKUP_VERIFY_UNDER_LIVE_WRITES`: dengan 31 tick penjalan IDLE selama backup, `restore_verified=true` (tick IDLE tidak menulis) → risiko hanya saat ada tulisan nyata; tidak terbukti gagal dalam kondisi uji. Sumber: R3 D1. | Malam dengan aktivitas (penjalan K6 menulis state, pengguna) berisiko tidak pernah "terverifikasi" → tidak pernah memangkas, tumpukan dump. Aman (tidak hapus apa pun). Syarat §2.4. |
| F-OPS-04 | Jadwal (F02) | minor | `cp7_schedule.py` menerima `--database` bebas tanpa dicek sama dengan `current_database()` dari `--erp-url` (`:93,98-105`); `uninstall` tanpa flag persetujuan. | `install --erp-url A --database B` | Review sumber R3 D4 (Fable membaca baris yang disebut). | Job pg_cron bisa dipasang menunjuk database lain. Dipagari oleh syarat §2.2. |
| F-AN-01 | Analisis 5.000 target | minor | Permintaan dengan >5.000 target **tidak ditolak saat request**: `request()` menangkap `source_within(5000,…)` dan `create_job` menyimpan job RUNNING + acuan (`analysis-stages.sql:2064-2075`); penolakan baru di unit 0 dengan kode `CP7_PLANNING_CAPTURE_INCOMPLETE` (`:129`), bukan kode yang dideklarasikan `CP7_ANALYSIS_STAGED_TARGET_LIMIT` (`:130`, hanya tercapai bila status COMPLETE — mustahil untuk >5.000). | Seed ≥5.001 produk; request; step sekali. | Review sumber R2 D1, diverifikasi Fable. Konsisten dengan Astra P20 (5.001 ditolak sebagai job FAILED). | Job FAILED + acuan besar tersimpan 7 hari; pesan tidak sesuai deklarasi `P19_STAGED_5000 §7`. Tidak ada dampak angka. |
| F-PAY-01 | Payroll | minor | Dua jam untuk tanggal bayar: PAY penggajian memakai cek Native `payment_date > current_date` (zona server) via `erp.post_payroll_payment` (`payroll/settlement-write.sql:92` → migrasi `20260901023200:432`), sedangkan cicilan memakai WIB (`payroll/installments.sql:296`). Pukul 00.00–07.00 WIB tanggal "hari ini" ditolak sebagai masa depan di satu jalur dan diterima di jalur lain. | PAY pada 02.00 WIB dengan tanggal WIB hari ini. | Review sumber R5 D1, diverifikasi Fable. | Arah aman (menolak), tetapi melanggar "tanggal ekonomi WIB"; pengguna pagi hari bingung. |
| F-AP-01 | AP/pembelian | minor | Koreksi penerimaan mereplay kelebihan bayar sebagai pembayaran ke nota lain pada **tanggal pembayaran asli** tanpa cek `>= physical_at` nota tujuan (`procurement/correction.sql:461-476, 984-1000`), padahal jalur bayar supplier dari aplikasi menolak `CP7_SUPPLIER_PAYMENT_BEFORE_RECEIPT` (`invoices/payment-create.sql:128`). | Terima A (1 Sep), bayar 2 Sep; terima B (10 Sep); koreksi A turun dengan kredit ke B. | Review sumber R5 D2, diverifikasi Fable. | Pembayaran bertanggal sebelum barang nota B tiba; total uang tetap, umur AP per nota bergeser. Aturan tidak konsisten. |
| F-TOOL-01 | Integritas uji | minor (alat uji) | Kontrol pergantian hari `with_retry` mengulang kelompok dari salinan baru bila setiap baris non-PASS berlabel rollover dan bukan cek harness; sebuah **FAIL produk yang kebetulan melintasi tengah malam** memenuhi syarat itu dan status akhir laporan memakai percobaan kedua. Percobaan pertama tetap tersimpan, tetapi `CI_RECEIPT.json` dan ringkasan probe tidak menampilkan `business_day_retried` (R6 A5). | `bd.guard(r={'status':'FAIL'},…); bd.retry_allowed({},{'A':r})` → True | `scripts/cp6_auditor_business_day.py:45-77`; pada semua run audit ini tidak ada rollover/rerun (0 dari 56 job). | Bug yang hanya muncul lintas tengah malam bisa tersembunyi di status akhir. Auditor wajib membaca percobaan pertama; receipt perlu kolom rerun. |
| F-TOOL-02 | Integritas uji / PR44 | minor (alat uji) | `astra-cp7-timeline-reuse.yml` gagal sebelum satu kasus pun: daftar fungsi `cp7_netting_native` di `cp7_astra_timeline_reuse_probe.mjs:19` basi (K7a menambah `source_within`, `matching_models_within`). | Dispatch workflow pada kandidat. | Run 38161262099 job 114534491610. | Paritas PR44 tidak punya bukti berjalan pada kandidat ini dari workflow itu; `netting` 83/83 di `claude-pl-native` tetap lulus. |
| F-TOOL-03 | Integritas uji | minor (alat uji penulis) | Kasus BF `VENDOR_REG:D12:CLAIM_CREDIT_DAILY_OLDER_INVOICE` memakai fixture jam dinding (`today-100 hari`, `cp6_bd_probe.py:1411-1416,1458`): pada 11 Okt 2026 `june_end<july` palsu → FAIL walau 12 cek bisnis lolos (POLA-21). | Jalankan paket T3 saat `today-100` jatuh di tanggal 1–2 bulan. | Run 38161280079 job 114534548232: 103 PASS / 1 FAIL. | Merah palsu berkala; bukan produk. |
| F-UI-02 | UI / pemasangan | minor | UI kandidat memanggil `erp_cp7_get_recost_queue_v1` di layar keuangan; di atas **paket CP6 saja** fungsi itu tidak ada → alert "Data belum dimuat ulang" (2 kasus READINESS INCOMPLETE, sama sejak 2 Okt). | Paket T3 CP6 + UI kandidat. | Run 38161280079 job 114534548451; prefreeze_ui diagnostik legacy. | UI kandidat tidak boleh dipasang di atas database yang hanya berisi CP6; pasang CP6+CP7 bersama. |
| F-DOC-01 | Dokumen | minor | `docs/AUDIT_PANDUAN_PRO_MAX.md` di cabang kandidat = versi 31ee23f0 + nama Sol, tanpa tambahan Fable/Astra PR #42 (§1.7–1.9, §2.8–2.12, §5.D, INV-K07/C06/POL04-05/M04-05, POLA-16..22, SKN-19..29, §16). | `diff` kedua berkas. | `scratchpad/out/panduan_pr42.md` vs `panduan_sol.md` (129 baris hilang). | Auditor berikutnya bisa memakai aturan yang lebih longgar tanpa sadar. |
| OBS-01 | Perencanaan/PL-5 | observasi → §7 Q1 | Parameter PL-5 B (180 hari, ≥5 grup, ≥200 PCS) **dapat diubah** oleh OWNER atau ADMIN dengan `master.product.manage` dalam rentang 1..3660 / 1..1000 / 1..1.000.000 (`plan-native/history-yield.sql:18-20,100-104`); hanya confidence/z/metode/pembulatan yang terkunci. | — | Review sumber R4 D3, diverifikasi Fable. | Sesuai "kebijakan berversi"; pertanyaannya siapa boleh mengubah angka owner. |
| OBS-02 | Rencana v2 | observasi | Pemeriksaan ulang kapasitas v2 hanya mengurangi intent **rencana** lain (`plan-native/staged.sql:264-268`); grup potong manual yang diposting sesudah snapshot tidak dikurangi (`capacity_now` tetap). Sesuai kalimat kontrak §3 "potong semua rencana lain". | — | R4 D1. | Bisa menerima sedikit lebih banyak dibanding analisis segar; sifat F01 (dua pengesahan tidak melewati kapasitas) tidak terpengaruh dan terbukti. |
| OBS-03 | Akses | observasi (rendah) | Penjaga isolasi `CP7_FRESH_ACCESS_REQUIRED` ada di 50/60 jalur tulis; 10 jalur (period, recost, report_command, obligation_*, rule_episode_evaluate) tidak memilikinya; tidak terjangkau lewat PostgREST (read committed tetap). | — | R1. | Pertahanan berlapis tidak seragam; bukan jalur serangan nyata. |

## 4. Vonis per area (tabel AUDITOR_START)

Label bukti: **INR** = INDEPENDENT_NATIVE_RERUN kasus penulis oleh Fable (eksekusi independen, oracle penulis); **FABLE** = kasus dan oracle Fable sendiri; **ISR** = INDEPENDENT_SOURCE_REVIEW; **RWE** = REUSED_WRITER_EVIDENCE.

| Area | Vonis | Dasar |
|---|---|---|
| Akses dan pemulihan | **LULUS** | FABLE smoke 8/8 (tidak ada fungsi/tabel `cp7_*` terjangkau anon/authenticated/service_role; `cp7_ops` menolak 42501; HTTP `cp7_ops` tidak terjangkau; request idempoten sekuensial+balapan) run 38195346649; ISR R1: 197 fasad SECURITY DEFINER, 60/60 penulis cek hak sebelum tulis, 58/58 cek ulang sesudah kunci, UUID disimpan sebelum tulis, replay mengembalikan respons lama; INR koreksi nota 40/40, penerimaan 43/43, pembayaran supplier 23/23+10/10, rantai penjualan (f03-full p11 64/64). OBS-03 dicatat. |
| Keuangan dan laporan | **LULUS** | ISR R5: tidak ada float; debit=kredit di `erp.post_journal`; UNKNOWN tetap null/"Belum tersedia"; WIB di pembaca; INR P13 12/12, f03-full p13 50/50 (periode), cash_installments 61/61, misc. FABLE: segel laporan v2 (`REPORT_V2_SEALED_ONCE_IMMUTABLE` PASS). Catatan: tidak ada oracle uang baru milik Fable di luar segel laporan; angka laba bergantung pada snapshot Native (CP6) yang sudah diaudit di CP6. |
| AP/pembelian/bahan | **LULUS dengan temuan minor** | INR penerimaan 43/43, pembayaran supplier create 10/10 + correction 23/23, f03-full p09 132/132, supplier_credit 5/5; ISR R5 (GRNI, idempoten, AP-5 tertua-dulu). F-AP-01 minor. |
| AR/penjualan | **LULUS** | INR nota 40/40 (termasuk harga baris yang sudah diretur → `CP7_NOTE_RETURNED_LINE_PRICE_CHANGED`), f03-full p11 64/64, customer_refund 10/10; ISR R5 (cadangan draf Native, retur terikat alokasi). Tidak ada kasus Fable baru. |
| Stok/HPP/produksi | **LULUS** | INR fabric-physical 21/21 (P08 fail-closed), fabric-recipe 13/13, f03-full p10 34/34, supply 53/53 (PL-8 `facts_hash`/`kernel_version`), netting 83/83; ISR R5 (`CP7_WIP_CONSERVATION`, prefix tidak negatif). |
| Payroll | **LULUS dengan temuan minor** | INR P12 3 job PASS, f03-full p12 90/90; ISR R5: tidak ada aturan baru yang dikarang (HALF_DAY ≤0,5 diwarisi Native). F-PAY-01 minor. |
| Perencanaan/model (PL-5 B) | **LULUS** + §7 Q1 | FABLE: Wilson satu sisi 90% dibulatkan ke bawah 0,1% **sama persis** 8/8 titik uji termasuk 200/200→991 (tidak pernah 100%); tanpa kebijakan → `PENDING_POLICY_VALUE`. INR pl5 20/20, plan39 43/43, model 32/32, schedule 71/71. OBS-01. |
| Rencana v1/v2 (F01) | **LULUS** | FABLE balapan dua arah pada salinan baru: v1 59 menahan kunci, v2 2 menunggu di `advisory` lalu 40001 `CP7_PLAN_V2_CAPACITY_USED` (capacity_now 1), total 59 ≤ 60; arah sebaliknya 40001 `CP7_PLAN_CAPACITY_USED`, total 59. INR plan-v2 22/22. ISR R4 §1 (satu kunci `CP7:PLAN_CAPACITY`, cek sesudah kunci). |
| Analisis 5.000 target | **LULUS dengan temuan minor** | INR staged 14/14, scale5 PASS (5.000 target, batas tidak dilonggarkan), transport 15/15; FABLE 8 detik: `run_next` menolak tanpa batas/9 s/8001 ms (55000), berjalan pada 8 s. ISR R2: batas 8.000.000 B dicek (`:1671/1933`), identity_hash dihitung terakhir dan dicek saat baca. F-AN-01 (5.001). |
| Snapshot berlabel waktu (v2) | **LULUS** | INR staged `P19G_SNAPSHOT_FRESHNESS` + reminder/report v2; ISR R2: kesegaran dari pg_snapshot + hitungan per tabel, teks "Data per …", kata "terkini" tidak ada di tiga berkas UI. Tidak ada kasus Fable sendiri. |
| Rencana v2, BR v2, pengingat v2, Tanya AI v2 | **LULUS** (AI ⏳) | FABLE segel laporan PASS; INR plan-v2 22/22, report-v2 20/20, reminder-v2 16/16, ai-v2 9/9; ISR R4 §2–5 (cek ulang live satu transaksi; pengingat dicek sebelum klaim dan sebelum selesai; AI tanpa tulis). ⏳ `FABLE_CORE:AI_BRIEF_RUNS_READ_ONLY` (run 1 INCOMPLETE karena alat Fable sendiri; diulang). |
| Retensi 7 hari (K2) & hapus sesudah DONE (K3b) | **GAGAL (major F-OPS-02)** | INR k2 10/10, k3 19/19 lulus; ISR R3 §3–4 (7 hari dari `updated_at`, RUNNING tak pernah kedaluwarsa, hasil/halaman/hash/log tetap); tetapi FABLE membuktikan pembersihan mengunci tabel dan menahan step job berjalan 8,01 s → percobaan gagal. Ukuran 5.000 target sebelum/sesudah: RWE 126–129 MB → 31,1 MB (`K3_SCALE_CLEANUP.json`, 2e605bb7), **belum diukur ulang Fable** pada d0b9e9c2. |
| K4 penjalan analisis server | **LULUS** | INR k4 17/17 (6 balapan termasuk pg_cron nyata, cold start dua tick); FABLE batas 8 detik wajib; ISR R2 (unit eksklusif `for update skip locked` + PK, hak dicek per unit tanpa login, heartbeat `pg_try_advisory_xact_lock`, `run_next` tidak terjangkau HTTP, "boleh ditutup" hanya saat `serverRunner.active`). Catatan R2 D3: error non-42501 dari fungsi akses menahan job lain (belum terbukti terjadi). |
| K6 penjalan bukti PL-8 | **LULUS** | INR k6 10/10; ISR R3 §5 (satu pembukti tak diubah, `facts_hash`+`kernel_version`, insert-only + trigger immutable, 8 detik wajib, BUSY tanpa menunggu, 200→100→50→lewati, istirahat 1 jam, HTTP tidak terjangkau). Tidak ada kasus Fable sendiri selain `cp7_ops.proof_tick` menolak peran publik. |
| Jadwal server & backup malam (F02, F03) | **GAGAL (major F-OPS-01; minor F-OPS-03/04)** | FABLE `schedules()` = deklarasi K3_CLEANUP.json (4 entri, nama unik); ISR R3 (`<nama>@<database>`, `schedule_in_database`, install menolak tanpa flag); FABLE backup di bawah tick IDLE terverifikasi; FABLE `--scratch` menghapus database lain → FAIL. **Belum dipasang** (benar). |
| Integritas uji (F04, F05, alat uji) | **LULUS dengan catatan** | ISR R6: host browser tidak bisa mengubah FAIL→PASS; timeout kasus → INCOMPLETE `AUDITOR_BROWSER_CASE_TIMEOUT`; 6/6 log gagal pertama di `docs/cp7/evidence/` **MATCH** dengan log CI yang disebut; F-TOOL-01..03. Tidak ada rollover di 56 job audit ini. |
| UI | **GAGAL (major F-UI-01)** ⏳ | INR prefreeze_ui 31/31 dan semua grup browser suite (desktop+HP, 390 px tanpa geser samping pada layar yang diuji); ISR R6 B6–B8: 48 rute terjaga `isPageAllowed`, pesan penolakan "Tidak punya akses … <permission>", tanpa fallback nol di halaman keuangan terhubung; tetapi Dashboard angka karangan (F-UI-01). ⏳ browser Fable. |
| P21 gladi | **LULUS (gladi, bukan pemasangan)** | INR dua job P21 PASS (pasang/rollback pra-pakai/pasang ulang identik/pakai/tolak rollback pasca-pakai/backup-restore); komposisi penuh memuat `cp7_ops` dan `cp7_proof_runner` (bundel `cp7_analysis_stages_bundle` memasukkan `ops/schedule.sql` dan `planning/proof-runner.sql`). |

## 5. Hasil merah yang bukan temuan produk

| Run/job | Kasus | Klasifikasi | Alasan |
|---|---|---|---|
| 38161262099 / 114534491610 | astra-cp7-timeline-reuse | STALE_TEST_SELECTOR (alat uji Astra) | daftar fungsi basi (F-TOOL-02) |
| 38161300045 (3 job) | cp6-release-readiness | NOT_APPLICABLE | penjaga `READINESS_SCOPE` menolak cabang dengan berkas di luar cakupan lamanya |
| 38161309511 / 114534627983 | cp6-final-boundary-audit | NOT_APPLICABLE | `assert not git rev-list --merges` — cabang punya merge commit |
| 38161280079 / 114534548232 | `VENDOR_REG:D12:…` FAIL | WRITER_TEST_FIXTURE_DATE (POLA-21) | F-TOOL-03 |
| 38161280079 / 114534548451 | READINESS_BROWSER ×2, SALES_MANUAL_13 ×2 INCOMPLETE | LEGACY_RUNTIME_OBSERVATION / STALE_TEST_SELECTOR (PRE-05) | F-UI-02; selector lama GPT |
| 38161236621 / 114534414226 | 2 INCOMPLETE diagnostik legacy | LEGACY_RUNTIME_OBSERVATION_ONLY | sama dengan 2 Okt, 0 kredit kasus |
| 38161271353 (T2) | CALENDAR DPRR 12, COUNTEREXAMPLE 20, INCOMPLETE 5; AR `ACCESSORY_CONNECTED_ZERO` | FROZEN_CP6_DISPOSITION / SUPERSEDED_BY_OWNER_RULE (D11) | multiset **identik** dengan beku r16 |
| 38162239881, 38195346649, 38196137312 (Fable) | job merah | AUDITOR_TOOL | gate `cp6_t3_package_run` memerahkan job karena ringkasan driver Fable gagal (`NoneType.get`); semua baris kasus tercetak dan dibaca per kasus; diperbaiki |
| 38196137312 | `FABLE_CORE:AI_BRIEF_RUNS_READ_ONLY` INCOMPLETE | AUDITOR_TOOL | reset `transaction_read_only` di dalam transaksi tidak diizinkan; kasus diulang ⏳ |

## 6. Label asal-bukti per klaim

| Klaim | Label | Run/commit |
|---|---|---|
| Identitas produk d0b9e9c2 = tree 4bd5e1ac; head cabang hanya docs | INDEPENDENT_SOURCE_REVIEW | git lokal 11 Okt |
| 15 workflow kualifikasi + f03-full + prefreeze + CP6 regresi lulus per kasus | INDEPENDENT_NATIVE_RERUN (oracle penulis) | run 38161112248…38161327762 (ledger `dispatch_ledger_all.jsonl`) |
| Akses skema/HTTP `cp7_*`, `cp7_ops`, idempoten request | FABLE (oracle sendiri) | 38162239881 / 38195346649 |
| F01 dua arah, Wilson, PL-5 PENDING, 8 detik, segel laporan, backup, cleanup-lock | FABLE | 38196137312 job 114639081720 |
| Semua butir sumber (R1–R6) | INDEPENDENT_SOURCE_REVIEW (sub-reviewer Fable, diverifikasi ulang baris yang dikutip untuk setiap temuan) | tree 4bd5e1ac |
| Ukuran 5.000 target sebelum/sesudah pembersihan | REUSED_WRITER_EVIDENCE | `docs/cp7/k3/K3_SCALE_CLEANUP.json` (2e605bb7) |
| Log gagal pertama = log CI | INDEPENDENT_SOURCE_REVIEW + log CI dibaca | R6 A4 (6 job) |
| Keputusan owner 8–9 Okt (K2 7 hari, 6 syarat K3b, K4 sekarang, PR #45 ditahan) | UNVERIFIED_OWNER_DECISION (dikutip penulis) kecuali PR #45 yang owner tanyakan langsung ke Fable | `docs/cp7/OWNER_DECISIONS_20261008.md` |

## 7. Pertanyaan untuk owner (masing-masing dengan rekomendasi)

1. **Siapa boleh mengubah angka kebijakan PL-5 B (180 hari / 5 grup / 200 PCS)?** Sekarang OWNER dan ADMIN dengan `master.product.manage`, rentang sangat lebar (OBS-01). **Rekomendasi: owner saja**, atau nilai 180/5/200 dikunci sebagai minimum dan hanya boleh diperketat. Jawab "ya" bila setuju owner saja.
2. **Dashboard di mode terhubung:** sembunyikan kartu angka sampai tersambung ke angka Native, atau tampilkan label besar "CONTOH — bukan angka ERP"? **Rekomendasi: sembunyikan** (tidak ada angka uang yang bukan dari ERP). Jawab "sembunyikan" bila setuju.

Tidak ada pertanyaan lain: K2 7 hari, 6 syarat K3b, K4, PR #45 sudah diputuskan dan tidak dibuka ulang.

## 8. Belum diperiksa siapa pun (termasuk Fable)

- 5.000 target yang diselesaikan **seluruhnya oleh penjalan server K4** (suite K4 memakai target kecil; scale5 memakai jalur halaman).
- Pemasangan jadwal/backup pada **hosted** dan tujuan simpan di luar database (sengaja belum; §2).
- HP fisik/Safari; tab HP benar-benar ditutup (hanya emulasi Playwright).
- Pengukuran ulang penyimpanan 5.000 target pada d0b9e9c2 (angka dari 2e605bb7).
- Reproduksi runtime F-PAY-01 dan F-AP-01 (ditulis dari sumber; dua-duanya minor).
- 5.001 target lewat request (ditulis dari sumber + Astra P20).
- Hosted baseline masih v2.6.20 (TIDAK DAPAT DIVERIFIKASI DARI SESI INI; REUSED_WRITER_EVIDENCE).

## 9. Lampiran

- Ledger dispatch: `dispatch_ledger_all.jsonl`; hasil per job: `runs/SUMMARY.md`, `runs/SUMMARY.json`; log kasus Fable: `runs/fable_*.json`.
- Catatan sub-reviewer: `review/R1_ACCESS.md` … `review/R6_TEST_INTEGRITY_UI.md`, `review/PRIOR_REPORTS.md`.
- Skenario Fable: `scenarios/fable_cp7_probe.py` (driver), `fable_cp7_smoke.py`, `fable_cp7_core.py`, `fable_cp7_ui.mjs`; workflow `.github/workflows/fable-cp7-native.yml` (checkout produk dipin d0b9e9c2).

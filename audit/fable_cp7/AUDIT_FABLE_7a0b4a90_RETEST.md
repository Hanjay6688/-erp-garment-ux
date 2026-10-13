# Uji ulang Fable — kandidat revisi `7a0b4a90` (perbaikan temuan audit penuh CP7 `d0b9e9c2`)

**Status:** v1.0 FINAL (13 Okt 2026, 02:30 UTC). Semua run selesai dan dibaca per kasus. **Catatan v1.0.1:** owner menegaskan keputusan 12 Okt dan menerima vonis bersyarat ini pada 13 Okt (lihat `OWNER_DECISIONS_TO_AUDITOR_20261013.md`); label UNVERIFIED_OWNER_DECISION di bawah menjadi OWNER_CONFIRMED_TO_AUDITOR. v1.1 menyusul setelah hasil penulis (diagnosis selisih + 3 run bayar supplier; gladi jadwal) dibaca.

| | |
|---|---|
| Kandidat revisi | commit `7a0b4a90af234a906d3cda7fc8ec9fd411a15dd2`, tree `05d4ccd84ed7faedede1d9161cd08952591659b2`; head cabang `5656f072` (selisih dari 7a0b4a90 hanya `docs/`, diperiksa sendiri) |
| Selisih produk dari d0b9e9c2 | 27 berkas non-dokumen: `analysis-stages.sql`, `plan-native/{history-yield,commands,staged}.sql`, `cp7_nightly_backup.py`, `cp7_schedule.py`, `cp6_auditor_business_day.py` (+test), `cp7_astra_timeline_reuse_probe.mjs`, `cp7_ci_receipt.py`, kasus K3/PL5/staged/settlement/receipt, `src/App.tsx`, `src/OwnerDashboard.tsx` (+test), panel PL-5. Tree `supabase/*` tidak berubah (paket CP6 identik). |
| Metode | kasus Fable yang sama **tanpa diubah oracle** (smoke 8, core native 5 + balapan 5, UI browser 3) + 1 kasus baru (PL-5 owner-only HTTP) pada `product_ref=7a0b4a90`; 17 workflow penulis didispatch ulang pada head `5656f072`; review sumber setiap perbaikan. Panduan PR #42. |

## 1. Review sumber perbaikan (INDEPENDENT_SOURCE_REVIEW, dibaca baris per baris dari `git diff d0b9e9c2 7a0b4a90`)

| Temuan | Perbaikan yang terbaca | Penilaian statis |
|---|---|---|
| F-OPS-01 | `cp7_nightly_backup.py`: `scratch_state()` membaca komentar database; `FOREIGN` → `BACKUP_SCRATCH_EXISTS_NOT_OURS` sebelum apa pun; `Tools.create` memakai `createdb` tanpa `dropdb` dulu (nama yang muncul di tengah membuat `createdb` gagal, bukan dihapus); hanya database bertanda milik alat yang di-drop; receipt mencatat `scratch_before/after`. | Benar. Tidak ada jalur `dropdb` tanpa cek tanda. |
| F-OPS-02 | `analysis-stages.sql`: trigger baru `work_immutable()` pada `outputs/target_rows/pair_rows/pair_lists/fragments/pages` meloloskan DELETE hanya untuk job yang disebut di setelan transaksi `cp7.analysis_work_delete` (dan `_run` untuk pages); `clean_done/purge_expired/purge_intermediates` tidak lagi `alter table … disable trigger`; `purge_expired` kini `lock_timeout` 2 s. | Benar: DELETE biasa tidak mengambil kunci tabel yang ditunggu INSERT unit. Catatan: setelan GUC bisa dipasang sesi mana pun, tetapi DELETE tetap memerlukan hak tabel (hanya pemilik; RLS) → tidak membuka jalur hapus baru. Penundaan 10 menit `clean_pending` tetap; `purge_expired` tetap tanpa penundaan (sekarang tidak perlu karena tidak mengunci). |
| F-OPS-03 | sumber dibaca dalam satu snapshot (`pg_export_snapshot`), `pg_dump --snapshot`, hash tabel sumber di transaksi yang sama → pembandingan dengan isi dump. | Benar; menutup observasi. |
| F-OPS-04 | `cp7_schedule.py`: `same_database()` membandingkan `--database` dengan `current_database()`; `uninstall` butuh `--removal-approved`. | Benar. |
| F-UI-01 | `OwnerDashboard.tsx`: `connected` (= `runtime.mode !== 'DEMO_SIMULATION'`) → hanya judul + panel `role="status"` "Ringkasan angka belum tersambung ke data ERP"; angka contoh hanya di demo. | Benar sesuai keputusan owner 12 Okt (sembunyikan). Dibuktikan browser (§2.1). |
| OBS-01 → keputusan owner 12 Okt | `history-yield.sql`: `actor_role` check `='OWNER'`; akses tulis `CP7_YIELD_POLICY_OWNER_REQUIRED` (42501) untuk selain OWNER; `manage_allowed` hanya OWNER; `commands.sql`/`staged.sql` menyimpan `new_start_yield` (termasuk revisi kebijakan) pada rencana yang disahkan. | Benar. Dibuktikan kasus Fable HTTP owner-only (§2.1). |
| F-AN-01 | `request()` menolak `CP7_ANALYSIS_STAGED_TARGET_LIMIT` (detail `refused_at=REQUEST`) sebelum `create_job`. Uji penulis menurunkan `bounds()` di savepoint dan memastikan 0 job/acuan. | Benar. |
| F-PAY-01 | Penulis benar: fungsi Native `erp.post_payroll_payment` yang **terpasang** (v2.6.20ac `20260915031500:4709`, juga `ap` `20260922135615:4695`, keduanya di paket T3) memakai `(statement_timestamp() at time zone 'Asia/Jakarta')::date`. Temuan saya mengutip definisi lama `20260901023200` yang sudah diganti. **Temuan F-PAY-01 saya tarik (salah kutip versi).** Uji baru `P12_SETTLEMENT_WIB_PAYMENT_DATE` memaksa zona sesi berbeda hari dari WIB. | Koreksi auditor; bukan cacat produk. |
| F-AP-01 | Tidak diubah: keputusan owner 2 Okt (kredit boleh ke nota berikutnya mana pun). | Diterima sebagai ACCEPTED_BY_DECISION; dicatat di dokumen koreksi penerimaan. |
| F-TOOL-01 | ASF-F01 (Astra) `5f1506f4`: `explained()` kini mensyaratkan `status_before_rollover=PASS` dan error `AUDITOR_BUSINESS_DAY_ROLLOVER` → FAIL/COUNTEREXAMPLE/INCOMPLETE kasus tidak pernah diulang; `KEPT_FIRST_RESULT` + anotasi GitHub; `cp7_ci_receipt.py` membaca anotasi. | Benar; menutup kekhawatiran saya. |
| F-TOOL-02 | Probe PR44 diperbarui: setiap blok fungsi `cp7_netting_native` harus = pendahulu `aa638356` kecuali dua turunan `_within` dengan **tepat** suntingan yang disebut; bagian luar blok hanya boleh beda komentar/owner. | Benar dan ketat. Run §2.3. |
| F-TOOL-03 | CP6 beku, dicatat. | Diterima. |
| F-UI-02, F-DOC-01 | dicatat / panduan +138 baris (PR #42) | Diterima. F-DOC-01 saya diff ulang: panduan di `7a0b4a90` = panduan PR #42 (`SP/out/panduan_pr42.md`, 544 baris) + 9 baris tambahan saja (Sol sebagai auditor, penegasan SKN-26 32-bit, konvensi nama run, 3 baris log); **tidak ada baris PR #42 yang hilang atau dilonggarkan**. DITUTUP. |
| OBS-02, OBS-03 | tidak diubah | Diterima (observasi). |

## 2. Hasil run independen (dibaca per kasus dari log JSON; warna job tidak dipakai)

Identitas: workflow Fable `fable-cp7-native.yml` (cabang audit) dengan `product_ref=7a0b4a90…`, `product_tree=05d4ccd8…` (langkah assert memastikan HEAD dan tree sebelum apa pun berjalan); workflow penulis didispatch oleh Fable lewat REST pada head `5656f072` (identitas produk = tree 7a0b4a90, selisih hanya `docs/`). Register run: `runs/retest_7a0b4a90/jobs_completed_retest.json`, ringkasan per job `runs/retest_7a0b4a90/SUMMARY_RETEST.md`.

### 2.1 Kasus Fable (oracle sendiri, tidak diubah dari audit `d0b9e9c2`; label FABLE)

| Run / job | Kasus | d0b9e9c2 | 7a0b4a90 | Yang terukur |
|---|---|---|---|---|
| 38330288917 / 115078269515 | FABLE_CORE:CLEANUP_LOCK_VS_RUNNING_STEP (balapan) | **COUNTEREXAMPLE** → F-OPS-02 (step 8,01 s, unit_attempts 1) | **PASS** | `clean_done` ditahan terbuka (belum commit) sementara job lain `step()`: 0,01 s, unit tersimpan, `unit_attempts 0`. |
| 38330288917 / 115078269515 | FABLE_CORE:BACKUP_SCRATCH_DROPS_FOREIGN_DB (balapan) | **COUNTEREXAMPLE** → F-OPS-01 (database asing di-drop) | **PASS** | Database korban `fable_victim_db` dibuat lalu nama itu dipakai sebagai scratch: alat menolak `BACKUP_SCRATCH_EXISTS_NOT_OURS`, `victim_exists_after=true`. |
| 38330288917 / 115078269515 | FABLE_CORE:BACKUP_VERIFY_UNDER_LIVE_WRITES (balapan) | PASS (OBS, F-OPS-03) | **PASS** | Thread `k4.tick` menulis selama backup (24 tick); `verified=true` dibandingkan dengan sumber pada snapshot dump. |
| 38330288917 / 115078269515 | FABLE_CORE:F01_V1_HOLDS_V2_REFUSED, F01_V2_HOLDS_V1_REFUSED | PASS | **PASS** | Kunci kapasitas dibagi v1/v2 dua arah (40001 saat kapasitas penuh). |
| 38330288917 / 115078269515 | FABLE_CORE:WILSON_PERMILLE_ONE_SIDED_90_FLOOR, PL5_NO_POLICY_IS_PENDING, RUN_NEXT_REFUSES_WITHOUT_8S_LIMIT, AI_BRIEF_RUNS_READ_ONLY, REPORT_V2_SEALED_ONCE_IMMUTABLE | PASS | **PASS** | Regresi; oracle Wilson milik Fable (z = 1,2815515655446004, pembulatan ke bawah permille). |
| 38330288917 / 115078269515 | FABLE_CORE:HTTP_PL5_POLICY_OWNER_ONLY (HTTP, **kasus baru** untuk keputusan owner 12 Okt) | — | **PASS** | ADMIN simpan kebijakan → 403 `CP7_YIELD_POLICY_OWNER_REQUIRED`; OWNER → 200; `manage_allowed=false` untuk ADMIN. |
| 38330296574 / 115078294976 | FABLE_UI:LANDING_NO_FABRICATED_FIGURES_DESKTOP, _MOBILE (browser, mode tersambung) | **COUNTEREXAMPLE** → F-UI-01 (7 angka palsu) | **PASS** | Tidak satu pun dari 7 string angka contoh muncul; panel status "belum tersambung" tampil. |
| 38330296574 / 115078294976 | FABLE_UI:GUDANG_SEES_NO_FINANCE_NAV | PASS | **PASS** | |
| 38330296574 / 115078294976 | FABLE_SMOKE: 5 native + 1 balapan + 2 HTTP (skema CP7 tak terjangkau peran publik; `cp7_ops` 42501; `schedules()` = deklarasi K3; satu job per kunci berurutan & bersamaan; tidak ada pg_cron CP7 di salinan; HTTP ops tak terjangkau; owner request staged → RUNNING) | PASS | **PASS** | Regresi. |

Semua grup Fable `complete_boundary_restored=true`; tidak ada kasus yang diulang karena pergantian hari (`business_day_retried` kosong).

### 2.2 Workflow penulis pada tree 7a0b4a90 (INDEPENDENT_NATIVE_RERUN; dispatch Fable, dibaca per kasus)

| Workflow / job | Kasus | Hasil per kasus | Catatan |
|---|---|---|---|
| p19-transport / k3-cleanup-22 (115078924624) | 22 | 22 PASS | Termasuk 3 kasus baru: `K3C_RACE_CLEANUP_BESIDE_RUNNING_STEP` (step 0,01 s, `unit_attempts 0`, izin hapus terbatas job yang disebut), `K3C_RACE_BACKUP_SCRATCH_NEVER_DROPS_ANOTHER_DATABASE` (asing ditolak & tetap ada; muncul setelah cek → tidak di-drop; sisa bertanda milik alat dipakai ulang), `K3C_RACE_BACKUP_VERIFIED_UNDER_WRITES` (343 baris ditulis selama backup; 560 tabel dibandingkan dengan snapshot dump). |
| p19-transport / k4-runner-17, k6-proof-runner-10, k2-retention-10, pl5-history-yield-20, p19-plan-v2-22, p19-staged12 (14 kasus), p19-report-v2-20, p19-reminder-v2-16, p19-ai-v2-9, p19-transport11 (15) | 17/10/10/20/22/14/20/16/9/15 | semua PASS | `pl5` memuat owner-only + versi kebijakan tersimpan; `staged` memuat penolakan 5.001 target di `request()` (F-AN-01). |
| p19-transport / p19-scale5 (115078924666) | 5 | 5 PASS (native 100 grid cap; browser desktop 100/300/1.000/5.000) | Selesai 02:16 UTC (70 menit). Jalur yang diubah (`analysis-stages.sql`) juga terbukti di `p19-staged12` dan job shell `p19-staged` (5.000 target × 100 hari DONE, unit terlama 2,11 s). |
| p08-physical / analysis152, attention284, plan39, fabric-physical21, fabric13-successor | 153/289/43/21/13 | semua PASS | |
| p08-shell / p19-assembly, p19-staged, shell | vitest 15 + 5 berkas PASS; benchmark paritas byte-identik 300/1.200/5.000 target; shell = uji-diri harness | 32 baris JSON job `shell` **identik** (modulo waktu) dengan run d0b9e9c2 → INCOMPLETE di dalamnya adalah uji-diri yang disengaja ("deliberate restoration lock failure"), bukan produk. | |
| p12-payroll / attendance-write (81), roster (64), payroll-review (43) | 188 | semua PASS | Termasuk `P12_SETTLEMENT_WIB_PAYMENT_DATE` baru (zona sesi ≠ WIB). |
| p13-finance (12); p18-fabric-rule / fabric-rule11, p18-e01-9, rule-lifecycle16; p18-full-cycle (2) | 12/11/9/16/2 | semua PASS | |
| p21-rehearsal / 2 job | PASS (label) | writer_runtime PASS, `installed_P21_acceptance=false` (tetap) | |
| pl-native / model 32, netting **83**, supply 53, schedule 71 | 239 | semua PASS | Netting 83/83 = regresi area PR44 pada tree yang berisi kernel reuse. |
| note-correction 43, receipt-correction 43, supplier-payment-correction 23 | 109 | semua PASS | |
| cp7-f03-full / p09 135, p10 34, p11 64, **p12 91**, p13 50, supplier_credit 5, cash_installments 61, customer_refund 10 | 450 | semua PASS | p12 91 = perbaikan hitung ddedf06c→7a0b4a90 terbukti. |
| cp7-prefreeze-ui | 31 PASS + 2 INCOMPLETE | kedua INCOMPLETE adalah kasus legacy yang sama dengan d0b9e9c2 (LEGACY_RUNTIME_OBSERVATION_ONLY), bukan regresi. | |
| cp6-candidate-codeql (4 job), p08-shell CodeQL (2) | hijau | tidak ada alert baru dibaca dari log | |
| **claude-supplier-payment-create** (115079091992) | 10 | **10/10 PASS per kasus; label grup INCOMPLETE** | lihat §2.4 |

Agregat retest: 50 job dibaca per kasus, 1.806 baris kasus: 1.804 PASS, 2 INCOMPLETE (keduanya legacy prefreeze, sama seperti sebelumnya), 0 FAIL, 0 COUNTEREXAMPLE, 0 pengulangan hari bisnis.

### 2.3 Penerimaan area PR44 (optimasi netting / timeline reuse, penulis Astra)

Fable bukan penulis PR44, jadi boleh menerima. Dasar:

1. **Probe paritas Astra pada tree 7a0b4a90** (run `38330587114`, job `115079188390`, didispatch Fable): `PARITY_PASS` declared 595 = executed 595, successes 312, refusals 283 (16 kode berbeda), supply_events 448, **mutations_caught 2** (dua mutasi sengaja tertangkap → probe bukan tautologi). Benchmark 100/300/1.000 target: 41,7 % / 39,4 % / 41,8 % lebih cepat tanpa posisi; 13,0 % / 24,1 % / 29,9 % dengan 100 posisi. Label: oracle milik Astra (penulis PR44), **eksekusi dan pembacaan oleh Fable** (INDEPENDENT_NATIVE_RERUN atas oracle pihak lain).
2. **Review sumber Fable** atas probe yang diperbaiki (F-TOOL-02): setiap blok fungsi `cp7_netting_native` wajib identik dengan pendahulu `aa638356` kecuali dua turunan `_within` dengan tepat suntingan K7a yang disebut; selain itu hanya komentar/owner boleh berbeda. Daftar fungsi tidak lagi basi (STALE_TEST_SELECTOR pada d0b9e9c2 tertutup).
3. **Regresi netting penulis** 83/83 PASS (`pl-native/netting`, job 115078990545) dan F01 kunci kapasitas dua arah PASS (kasus Fable).

**Keputusan Fable: area optimasi PR44 DITERIMA pada tree 7a0b4a90** (ACCEPTED, bukti 1–3). Catatan: penerimaan ini tentang paritas hasil dan tidak-rusaknya invariant, bukan klaim angka benchmark di produksi.

### 2.4 Kegagalan `CP7 Supplier Payment Create` (job 115079091992) — penilaian

- Sepuluh kasus (4 native, 3 balapan, 1 HTTP, 2 browser) **PASS**, masing-masing dengan `full_boundary_restored=true`, `public_schema_unchanged=true`, tidak ada kebocoran sesi.
- Yang gagal hanya pemeriksaan akhir grup di harness (`cp6_auditor_runner.strict_group`, baris 152–153): sesudah `conn.rollback()` dan `verify(cur)`, `boundary.snapshot()`/`public_state()` dibandingkan dengan snapshot awal grup → `complete_boundary_restored=false`. Harness **tidak mencatat kunci mana yang berbeda**, sehingga akar penyebabnya tidak bisa dibaca dari log.
- Reproduksi: pada tree 7a0b4a90 gagal 2 dari 4 run (penulis `38288829388`, Fable `38330557862`), lulus pada ddedf06c dan e0583314 (penulis). Selisih ddedf06c→7a0b4a90 tidak menyentuh `supabase/`, `src/`, atau skema supplier payment (hanya `docs/` dan `cp7_f03_full_manifest.json`).
- **Probe Fable** (run `38332667386`, job `115085711294`): empat kasus native penulis dijalankan di antara `FABLE_SPC:CAPTURE_STATE` dan `FABLE_SPC:COMPARE_STATE_AFTER_WRITER_CASES` memakai fungsi snapshot yang sama → `boundary_equal=true`, `public_equal=true`. Kasus produk tidak meninggalkan perubahan; ketidaksamaan muncul di jalur akhir grup (rollback → `verify` → snapshot), kemungkinan dari sesuatu yang tidak transaksional atau tidak deterministik yang masuk ke snapshot.
- Klasifikasi: **AUDITOR_TOOL — belum terjelaskan** (bukan temuan produk berdasarkan bukti di atas, tetapi juga belum terbukti bukan). Tidak saya labeli "flake". Syarat lihat §3.

### 2.5 Hal yang tidak diulang

CP6 T2 (56 kasus beku) dan T3 tidak diulang penuh: tree `supabase/*` identik antara d0b9e9c2 dan 7a0b4a90, dan setiap job penulis di atas memasang T3 ulang (`ALL_STAGES_INSTALLED`, `primary_unchanged=true`, `backup_restore_drill` RESTORED_SAME_MEANING) sebagai prasyarat. Identitas T3 di job penulis mencatat `product_ref=ddedf06c` untuk jalur produk `supabase/*`+`src` — jalur itu identik di 7a0b4a90 (diff kosong), jadi bukan masalah identitas, tetapi penulis sebaiknya memajukan pin itu.

## 3. Vonis

**Kandidat `7a0b4a90` (tree `05d4ccd8`): LULUS DENGAN SYARAT.** Vonis HOLD atas d0b9e9c2 dicabut.

| Temuan audit penuh | Status di 7a0b4a90 | Bukti |
|---|---|---|
| F-OPS-01 (backup men-drop database asing) — mayor | **DITUTUP** | §1 sumber; FABLE BACKUP_SCRATCH_DROPS_FOREIGN_DB PASS; K3C baru PASS |
| F-OPS-02 (cleanup mengunci tabel, unit gagal 8 s) — mayor | **DITUTUP** | §1 sumber; FABLE CLEANUP_LOCK_VS_RUNNING_STEP 0,01 s; K3C baru PASS |
| F-UI-01 (angka palsu di dashboard tersambung) — mayor | **DITUTUP** | FABLE_UI 2 kasus PASS; sumber `OwnerDashboard.tsx` |
| F-OPS-03, F-OPS-04 | DITUTUP | sumber + BACKUP_VERIFY_UNDER_LIVE_WRITES; `same_database`/`--removal-approved` |
| F-AN-01 | DITUTUP | sumber + `p19-staged12` 14/14 |
| F-PAY-01 | **DITARIK oleh Fable** (salah kutip versi fungsi) | migrasi v2.6.20ac/ap WIB; `P12_SETTLEMENT_WIB_PAYMENT_DATE` PASS |
| F-AP-01 | ACCEPTED_BY_DECISION (owner 2 Okt) | register keputusan |
| F-TOOL-01 | DITUTUP (ASF-F01 Astra) | sumber `cp6_auditor_business_day.py`; 0 pengulangan di 50 job |
| F-TOOL-02 | DITUTUP | probe PR44 PASS, mutations_caught 2 |
| F-TOOL-03 | FROZEN_CP6_DISPOSITION | — |
| F-UI-02, F-DOC-01, OBS-01..03 | DITUTUP / dicatat | panduan = PR #42 + tambahan; PL-5 owner-only PASS |

**Syarat yang masih berlaku (bukan pembuka ulang keputusan owner):**

1. **Belum terjelaskan — `complete_boundary_restored=false` di `CP7 Supplier Payment Create`.** Penulis menambahkan pencatatan kunci yang berbeda (diff snapshot awal vs akhir) di `strict_group`, lalu menjalankan ulang workflow itu minimal 3 kali pada tree yang sama; hasil dan akar penyebab dilaporkan ke owner sebelum pembekuan. Sampai itu ada, status area supplier payment = "kasus produk lulus, pemeriksaan harness belum terjelaskan".
2. **Pemasangan jadwal (pg_cron) dan backup malam belum boleh**, sampai owner memutuskan dan mencatat di register: (a) nama database tujuan yang persis (alat `cp7_schedule.py install --installation-approved` menolak bila `--database` ≠ `current_database()`); (b) tujuan simpan dump di **luar** mesin database (alat hanya membuktikan dump+restore di scratch lokal; tempat penyimpanan akhir dan retensi adalah keputusan owner); (c) satu kali gladi di salinan sekali pakai dengan jadwal sesungguhnya (01:00 WIB) yang dibaca `schedules()` = deklarasi K3, lalu uninstall `--removal-approved`. Rekomendasi saya: putuskan (a)–(b) dahulu; (c) bisa dijalankan penulis di CI tanpa menyentuh hosted.
3. `production_go:false` tetap sampai penerimaan dan izin pemasangan final (keputusan owner 13 Okt D13-2/D13-3).

Hal yang **tidak** saya periksa ulang: proses hosted (dilarang), isi `docs/cp7/OWNER_DECISIONS_20261008.md` selain bagian 9 & 12 Okt yang dikutip penulis (keputusan 12 Okt kini OWNER_CONFIRMED_TO_AUDITOR, 13 Okt), dan benchmark pada perangkat keras produksi.

## 4. Label bukti
FABLE = oracle & eksekusi Fable; INDEPENDENT_NATIVE_RERUN = oracle penulis/Astra, dispatch & pembacaan per kasus oleh Fable; INDEPENDENT_SOURCE_REVIEW = diff dibaca Fable; REUSED_WRITER_EVIDENCE = tidak ada (semua run dibaca dari dispatch Fable); ACCEPTED_BY_DECISION = F-AP-01; AUDITOR_TOOL = §2.4; OWNER_CONFIRMED_TO_AUDITOR = keputusan 12 Okt, ditegaskan owner langsung ke auditor 13 Okt (register `OWNER_DECISIONS_TO_AUDITOR_20261013.md`).

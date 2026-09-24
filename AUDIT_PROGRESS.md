# AUDIT_PROGRESS — audit independen akhir CP6 (buta, dua fase)

Cabang audit: `audit/cp6-final-20260924` (dibuat dari `9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc`, tree `5d5f833b2e75e23184c643d5ac469781f1c3ce5e`). Tidak ada kode produk yang diubah di cabang ini; semua berkas audit ada di `audit/` dan berkas ini.
Baseline pembanding: `competition/cp6-j-closure-20260911` @ `ca7f09556397801c50a2277bdb65b1bf019f9a05`.
Sumber kebenaran: hanya `ERP_V3_2_Master_Pulih_20260923.md` (M), `ERP_V3_2_Perubahan_Pulih_20260923.md` (P), `ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md` (A, batas CP6/CP7 saja). Rujukan ditulis `M:<baris>`. Berkas kontrak tidak di-commit (milik owner); hash: M `f21ac703…9af07`, P `92966cd6…7676`, A `4566ab6f…5886`.
`production_go=false`. Auditor hanya merekomendasikan.

## FASE AKTIF
**Fase 1 (buta) — berjalan.** Temuan fase 1 belum dikunci/di-hash. `docs/cp6-*.md`, `docs/evidence/`, laporan auditor lain, dan isi pesan commit belum dibaca dengan sengaja (lihat "Kontaminasi").

## Rencana kerja (prioritas owner)
1. Daftar gate + temuan fase 1 → kunci + hash ke berkas ini.
2. Run native: T2, T3, CodeQL (sudah), skenario auditor per keluarga (berjalan).
3. Fase 2 rekonsiliasi (setelah hash fase 1 dicatat).
4. Laporan akhir `AUDIT_REPORT_CP6.md` di cabang ini.
Aturan token: satu workflow per fase, ≤4 agen sekaligus, effort rendah–sedang untuk pembaca, tinggi hanya untuk oracle/verifikasi; tiap agen menulis `audit/out/<agen>.md` bertahap; batas ±150k token/agen.

## a) Gate CP6 yang diturunkan dari kontrak (ringkas; rincian kutipan di `audit/out/C1_gates.md`)
| Gate | Isi | Rujukan kontrak | Status kontrak (23 Sep) | Status audit |
|---|---|---|---|---|
| GATE-01 | Perlindungan tumpang tindih saldo awal pada SEMUA jalur opening lama | M:138, M:229, M:361, M:1043 | OPEN | BELUM |
| GATE-02 | Gerbang gabungan keluarga terdampak pada kandidat beku, cakupan penerus benar | M:138, M:1763-1765, M:6661 | NOT RUN | BELUM (T2 dibaca, lihat d) |
| GATE-03 | Gerbang lama Full-Schema/Final Boundary tidak dilonggarkan/dilabel ulang | M:136, M:223, M:957 | FAIL dipertahankan | BELUM |
| GATE-04 | HTTP/Auth-JWT/browser nyata + concurrency dua koneksi untuk semua transaksi bisnis | M:229, M:317, M:422, M:4321 | PARTIAL | BELUM |
| GATE-05 | 12 kasus tanggal HOLD ditutup di bawah ERP-DEC01 (tanggal invoice) satu keluarga recost–GL–HPP–as-of–confidence–close | M:1057-1065, M:1080-1082, M:1404, M:6144-6169 | HOLD | HOLD (lihat T2 klasifikasi) |
| GATE-06 | Jalur eceran PCS exact di bawah ACC-DEC02 | M:1066-1071, M:1405, M:44, M:94 | writer PASS | BELUM |
| GATE-07 | Transport CSV nyata untuk scope impor (ERP-DEC03/ALL) | M:138, M:1024-1025, M:1072-1078, M:6381 | OPEN, dua status bertentangan | BELUM |
| GATE-08 | Cakupan role/akses CP6 (AUD-G07) ditutup untuk scope final | M:1729, M:1407, M:1526, M:98 | PARTIAL | BELUM |
| GATE-09 | Keluarga yang diperbaiki writer harus VERIFIED_INDEPENDENT (A01–A05/G15, S02–S05, B01–B03, T01–T02, AO/AP/AQ) | M:1259, M:1308, M:1720-1722, M:1222-1224 | FIXED_WRITER | BELUM |
| GATE-10 | Paket migrasi permanen: install / rollback sebelum pakai / penolakan, byte-bound, di disposable | M:163, M:206, M:108-115, M:2713-2719 | WRITER_PACKAGE_PASS | BELUM (T3 dibaca, lihat d) |
| GATE-11 | Freeze SHA/tree/runtime, bukti per-ID terikat commit yang diuji | M:1767, M:132 | selesai untuk 5ae7330 saja | SEBAGIAN (head 9add57e diverifikasi di runtime, lihat probe) |
| GATE-12 | Audit independen dengan oracle sendiri atas perbaikan DAN jalur residual | M:4500-4501, M:1436-1437 | belum | BERJALAN |
| GATE-13 | Tidak ada POLICY_BLOCKED/INCOMPLETE/HOLD dalam scope CP6 saat lock | M:1699, M:4387, M:1220-1221 | tidak terpenuhi | HOLD |
| GATE-14 | CP6_LOCK_READY sah, lalu acceptance owner | M:1218-1219, M:1418-1420, M:229 | belum | BELUM (milik owner) |
| GATE-15 | Matriks historis: hanya diulang bila dibatalkan; label bukti jelas | M:4391, M:1766, M:1161-1163 | REUSED | BELUM |
| GATE-16 | CR aksesori/laundry: tuntas di kandidat final atau dikecualikan owner secara eksplisit | M:1755-1756, M:1697 | tanpa pernyataan owner | BELUM |
Keputusan owner DI KONTRAK: ERP-DEC01 (koreksi periode terbuka ikut tanggal invoice, M:1057-1062), ACC-DEC02 (harga eceran manual, 7 PCS tepat 7, M:1066-1071), 7 PCS = aksesori (M:44), total kontrol impor tidak dibukukan (M:43-46). PENDING di kontrak: ERP-DEC03 (CSV, M:1072-1078). Keputusan yang hanya dikutip writer di skrip (24 Sep: "geser tanggal recost", max(tanggal invoice, hari potong), 8 kasus AS, ADJUSTMENT_DATE, AO terbuka/tertutup, payroll APPROVED sebagai fixture) = **UNVERIFIED_OWNER_DECISION** (0 hit di ketiga berkas kontrak).

## b) Status per gate
Lihat kolom "Status audit" di atas. Belum ada ACCEPT. Putusan akhir menunggu skenario native per keluarga dan fase 2.

## c) Skenario auditor (berkas di `audit/scenarios/`, hash di `audit/scenarios/SHA256SUMS`)
| Berkas | sha256 | Isi |
|---|---|---|
| rt_probe_1.py | 13b3b800900e55d5ae60d67baafffec6aa07216da76bf6b7a95534f42da0c33a | probe runtime: identitas head, semua fungsi dev AW..AZ verbatim, kebocoran savepoint, status bebas, id ganda, commit koneksi kedua |
| rt_probe_2.py | cd6df40c868afefa9023c84d6c4f284f3b79d4abaa63907d66101b8395d82789 | probe runtime: asal modul (writer vs auditor), sequence, bocor tabel erp lewat koneksi kedua, COMMIT di koneksi kasus |
| date_family_1.py | 492908b5dcf3184bacabcb99a878630c1b206e67c5d6f96586f02105f4a537d0 | keluarga tanggal (ERP-DEC01): invoice setelah potong (12/8), dua potong, invoice sebelum potong (ambigu), periode tertutup, resep AA barang jadi+jual |
Alat: `audit/tools/dispatch_scenario.py <file> <after|before>` (menolak bila head cabang ≠ 9add57e; mencatat ke `audit/runs/dispatch_ledger.jsonl`), `audit/tools/fetch_run.py` (log job harus diambil lewat GitHub MCP/API karena redirect blob diblokir proxy).

## d) Run yang di-dispatch auditor (semua head_sha 9add57e; label INDEPENDENT_NATIVE_RERUN)
| Workflow | Run | Job(s) | Hasil per kasus (dibaca dari log, bukan warna job) |
|---|---|---|---|
| cp6-candidate-codeql.yml | 36037878419 | 107762403880 js-ts, 107762404091 python, 107762404177 actions, 107762404232 c-cpp | gate `cp6_codeql_artifact_gate.py`: 4× `{"status":"PASS","result_count":0}`. Batas: CodeQL tidak menganalisis SQL/PLpgSQL. |
| cp6-t2-regression.yml | 36037873682 | 107762384861 ar, 107762384959 temporal, 107762385235 regression | ar: AR_SEQUENTIAL 146 PASS, AR_CONCURRENCY 28 PASS. temporal: AT 16 PASS + 4 race PASS, AU 15 PASS + 6 race PASS. regression: BUSINESS 179 PASS / 39 CONTROL_PASS / 12 DATE_POLICY_REVIEW_REQUIRED; IMPORTS 31 PASS; VALUES 65 PASS; NEW_CASES 25 PASS / 8 COUNTEREXAMPLE / 1 INCOMPLETE; AO_TRIAL 8 PASS / 4 INCOMPLETE; harness: T2_APPROVED_ORACLE 8 MATCH, T2_CALENDAR_POLICY 12 COUNTEREXAMPLE, APPROVED_ORACLE_B 5 PASS; T2_IDENTITY moved: 8 DATE PASS→COUNTEREXAMPLE, ADJUSTMENT_DATE PASS→INCOMPLETE; verdict `DISPOSITION_REQUIRED`. Klasifikasi auditor: `audit/out/T2_classification.md`. |
| cp6-t3-release-package.yml | 36037876338 | 107762395202 install, 107762394813 capture, 107762395187 browser | install: 24/24 file PASS, AW_AX_AY_AZ_VERIFY PASS, advisors 73→127 (+54, semua INFO rls_enabled_no_policy) status REVIEW_REQUIRED, restore drill RESTORED_SAME_MEANING (restore exit 1, 19 error pg_cron diabaikan; katalog constraint/extension/index/view berbeda "dijelaskan"), tidak ada tahap rollback/post-use refusal. capture: T3_PINS_REPRODUCED equal. browser: 10/10 PASS. |
| cp6-auditor-scenario.yml | 36039753521 | 107768697263 | rt_probe_1 (after): RUN_COMPLETE; IDENTITY PASS (head 9add57e, tree 5d5f833), INSTALLED_BODIES_VERBATIM PASS (40/40 fungsi dev AW/AX/AY/AZ = prosrc), LEAK_CHECK COUNTEREXAMPLE (advisory lock sesi lolos rollback savepoint), STATUS_VOCAB 'OK' diterima, DUP_ID hasil pertama tertimpa (counts 7 dari 8 kasus), SECOND_CONNECTION_COMMIT tidak terdeteksi (full_boundary_restored=true, job hijau). Rincian: `audit/out/RT_probe1_findings.md`. |
| cp6-auditor-scenario.yml | 36040954954 | (ambil via API) | rt_probe_2 (after) — BERJALAN saat commit ini |
| cp6-auditor-scenario.yml | 36041422305 | (ambil via API) | date_family_1 phase after — BERJALAN |
| cp6-auditor-scenario.yml | 36041435083 | (ambil via API) | date_family_1 phase before (tanpa AZ) — BERJALAN |
Ledger: `audit/runs/runs_dispatched.json`, `audit/runs/dispatch_ledger.jsonl`, ringkasan log `audit/runs/gate_runs_summary.txt`, `audit/runs/auditor_36039753521.json`. Log mentah tidak di-commit; ambil ulang dengan run/job ID.
REUSED_EVIDENCE (fase 2 saja): run 36034620907 (empat skenario GPT) — belum dibaca.

## e) Temuan sementara (fase 1, belum diverifikasi adversarial)
| ID | Prio | Jenis | Temuan | Oracle / rujukan | Bukti |
|---|---|---|---|---|---|
| F1-01 | P1 | CONTRACT_GAP / PRODUK | Kandidat (AY/AZ) menanggalkan bagian WIP/FG/COGS dari koreksi invoice pada hari potong/barang jadi/jual, bukan tanggal invoice. Kontrak ERP-DEC01 (M:1057-1062) menyatakan tanggal invoice untuk semua komponen. Aturan yang diimplementasikan hanya ada sebagai kutipan writer ("owner 24 Sep") di skrip → UNVERIFIED_OWNER_DECISION. 8 kasus AS COUNTEREXAMPLE + 12 HOLD + 4 AO INCOMPLETE bergantung padanya. | ERP-DEC01 M:1057-1062; R3.5 M:1404-1406 | T2 run 36037873682 job 107762385235 (mismatch `revaluation_events`/`hpp_events` expected 2026-09-22 actual 2026-09-23); `cp6_t2_regression.py:42-52` |
| F1-02 | P1 | CONTRACT_GAP | Kontrak memuat dua status ERP-DEC03 (CSV): "masih perlu penjelasan cakupan" (M:1072-1078) vs "ALL data awal disetujui" (M:1024); kewajiban ALL tetap (M:138). Kandidat tidak punya transport CSV nyata (perlu konfirmasi di source). | M:138, M:1024, M:1072 | C1_gates.md F03 |
| F1-03 | P2 | TOOLING | Harness T2 mengubah lingkungan kasus sebelum assertion (seed quieting, payroll APPROVED-belum-dibayar untuk item kasus, cancel_unpaid_payroll) atas dasar keputusan owner 24 Sep yang tidak ada di kontrak; hasil "PROVEN" untuk kasus yang bergantung readiness hanya berlaku di bawah completion itu. | M:4322-4324 (setup harus dinyatakan) | `cp6_t2_regression.py:24-40`; log T2_FIXTURE_PAYROLL 6+103 baris |
| F1-04 | P2 | TOOLING | Runtime auditor: commit lewat koneksi kedua tidak terdeteksi (`full_boundary_restored=true`, RUN_COMPLETE); id kasus ganda menimpa hasil sebelumnya; status bebas ('OK') diterima; advisory lock sesi lolos rollback. FAIL membuat job merah, COUNTEREXAMPLE tidak → warna job bukan bukti. | pack §4 | run 36039753521 job 107768697263 |
| F1-05 | P2 | TOOLING/PRODUK | T3 install tidak menjalankan tahap rollback/penolakan pasca-pakai untuk paket 24 berkas; tidak ada berkas rollback untuk AW..AZ di `supabase/rollbacks/` (AV terakhir). Kontrak: paket permanen = migrasi + rollback sebelum pakai + penolakan (M:163, M:206). Perlu cek kapsul rollback di dalam paket. | M:163, M:206, M:2713-2719 | run 36037876338 job 107762395202 (kunci `t3_package_run` tanpa rollback); `ls supabase/rollbacks` |
| F1-06 | P3 | PRODUK/INFO | Advisors T3 73→127: +54 INFO `rls_enabled_no_policy` (tabel internal erp: kapsul rollback AC..AZ, fg_unsourced_*, initial_import_*, accounting_close_filings_v1, …). Status REVIEW_REQUIRED; kontrak tidak menetapkan ambang (M:112 "109 temuan baseline belum dinyatakan selesai"). | M:112 | run 36037876338 job 107762395202 |
| F1-07 | P3 | TOOLING | Restore drill T3 "RESTORED_SAME_MEANING" mentoleransi 19 error pg_cron dan perbedaan md5 constraint (29 VARCHAR_IN_LIST_REPARSE)/extension/index/view; kontrak AQ menuntut pemulihan "tepat" (M:108-110). Perlu cek apa yang ditoleransi. | M:108-110 | run 36037876338 job 107762395202 |
| F1-08 | INFO | PROTOCOL | Rantai runtime auditor/T2: skrip writer dari checkout baseline ca7f095 mendahului skrip kandidat di sys.path (writer/scripts di posisi 0); modul yang ada di keduanya diimpor dari baseline. Fungsi dev AW..AZ tetap terpasang verbatim dari 9add57e (probe 1). | pack §4 | run 36039753521 RT:IDENTITY sys_path_head |

## Kontaminasi / catatan protokol buta
- `docs/cp6-*.md`, `docs/evidence/`, `docs/reviews/`, `docs/runbooks/` TIDAK dibuka.
- Pesan commit terpapar tanpa sengaja: (1) baris subjek commit 9add57e dicetak oleh `git worktree add`; (2) GitHub API `list_workflow_runs` mengembalikan `head_commit.message` untuk run T2/T3/CodeQL/auditor-scenario (commit 9add57e, 208afce, 0628a68, b110e54, e51614a, 702f5f0, ed6c4e7, 6c65eff, e4584a3, 95954aa, b242d45, 311e0cc, 13dbcb1, 4de42cf, d5761d3, 46ad845). Isinya tidak dipakai sebagai oracle; oracle diturunkan dari kontrak. Sejak itu listing run diparse dengan pesan dibuang.
- Docstring/komentar skrip writer dibaca sebagai klaim writer (pembuat data), bukan oracle.

## Kejadian sesi
- 24 Sep 18:05-18:15 UTC: 16 agen pembaca (workflow) mati karena batas sesi akun ("session limit, reset 22:20 UTC"); hanya C1-gates selesai (`audit/out/C1_gates.md`). Pengulangan: ≤4 agen sekaligus, model murah untuk tugas mekanis, catatan bertahap ke `audit/out/`.

## f) LANGKAH BERIKUTNYA (untuk sesi baru: checkout cabang ini, baca berkas ini, lanjut dari sini)
1. Ambil hasil run 36040954954 (rt_probe_2), 36041422305 (date after), 36041435083 (date before): job log via GitHub API/MCP `get_job_logs` → parse baris JSON `{"group":...,"case":...}` → tulis ringkasan ke `audit/runs/auditor_<run>.json` dan tabel d) di atas; temuan baru ke e).
2. Setelah 22:20 UTC: jalankan ulang pembaca yang belum ada catatannya, ≤4 sekaligus, dengan `audit/tools/phase1_derive.js` (`args.keys`): prioritas C3-business, R1-runtime-install, R2-runtime-isolation, P-helper-catalog; lalu F-DATE, F-CLOSE, F-ACC, F-OPEN; lalu F-FG, F-IDENT, F-REL, F-ACCESS; lalu F-FRONT, F-T2, C2-register. Tiap batch selesai → commit `audit/out/`.
3. Tulis skenario per keluarga (CLOSE, ACC 7 PCS + lock order, OPEN overlap/total kontrol, FG unsourced, ACCESS fail-closed, IDENT) dengan oracle dari kontrak; gabungkan banyak kasus per dispatch; dispatch `after` (dan `before` bila perlu atribusi).
4. Verifikasi adversarial temuan P0–P2 (2 lensa) dengan `audit/tools/phase1_verify.js` (args.findings).
5. Kunci fase 1: tulis `audit/PHASE1_FINDINGS.md`, catat sha256-nya di berkas ini, commit.
6. Fase 2: baca `docs/cp6-au-r1-handoff.md` §18–20, §23–27 dan `docs/evidence/`; label CONFIRMED/REFUTED/UNVERIFIED; run 36034620907 = REUSED_EVIDENCE; keputusan owner hanya di handoff = UNVERIFIED_OWNER_DECISION.
7. `AUDIT_REPORT_CP6.md` sesuai blind pack §6; commit ke cabang ini.

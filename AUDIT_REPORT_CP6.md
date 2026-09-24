# AUDIT_REPORT_CP6 — Audit independen buta, dua fase, kandidat CP6 ERP Garment

**Status:** rekomendasi auditor. **Belum ada keputusan gate.** `production_go=false` sampai owner memutuskan.
**Auditor:** sesi independen (Claude Code), cabang audit `audit/cp6-final-20260924`. Tidak ada tulisan ke cabang kandidat, hosted, legacy, atau production; tidak ada SQL ke hosted.

## 0. Identitas target dan sumber kebenaran
| Hal | Nilai |
|---|---|
| Kandidat beku | `Hanjay6688/-erp-garment-ux` cabang `claude/new-session-deapao` @ `9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc` (tree `5d5f833b2e75e23184c643d5ac469781f1c3ce5e`) |
| Baseline | `competition/cp6-j-closure-20260911` @ `ca7f09556397801c50a2277bdb65b1bf019f9a05` |
| Kontrak (satu-satunya oracle) | M = `ERP_V3_2_Master_Pulih_20260923.md` (sha256 f21ac703…), P = `ERP_V3_2_Perubahan_Pulih_20260923.md` (92966cd6…), A = `ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md` (4566ab6f…). `M:n` = nomor baris Master. |
| Latar (bukan oracle) | `ERP_GARMENT_MASTER_CONTEXT_2026-09-06.md` |
| Kunci fase 1 | `audit/PHASE1_FINDINGS.md` sha256 `72ccbfe8613fca783be4050f0f722096262c9849e6a308adc6f37bc68e41ab6e`, dikunci 24 Sep 2026 19:0x UTC sebelum membuka dokumen writer |
| Semua run auditor | head_sha `9add57e` (diverifikasi via API dan via probe runtime `RT:IDENTITY`: head 9add57e, tree 5d5f833). Run dengan head lain tidak dipakai. |

**Label bukti:** INDEPENDENT_NATIVE_RERUN (run yang di-dispatch auditor pada 9add57e, status dibaca per kasus dari log JSON, bukan warna job) · INDEPENDENT_SOURCE_REVIEW (pembacaan sumber kandidat) · INDEPENDENT_ARTIFACT_CHECK (artefak/manifest) · REUSED_EVIDENCE (run 36034620907 milik GPT, hanya untuk jalur yang diujinya) · UNVERIFIED_OWNER_DECISION (keputusan owner yang hanya ada di handoff/skrip writer, tidak di M/P/A).

**Protokol buta:** fase 1 tanpa membuka `docs/cp6-*.md`, `docs/evidence/`, `docs/reviews/`, audit lama, laporan auditor lain. Kontaminasi tercatat: baris subjek/pesan commit terpapar lewat `git worktree add` dan API run (tidak dipakai sebagai oracle); docstring skrip writer dibaca sebagai klaim pembuat data. Fase 2 dibuka setelah hash kunci dicatat (commit `c38f153`).

## 1. Ringkasan eksekutif
1. **Kandidat 9add57e terpasang verbatim dan gate writer dapat direproduksi**: T2 identik per kasus dengan referensi AU (12 HOLD identik, 8 AS COUNTEREXAMPLE, 1+4 INCOMPLETE, oracle-disetujui MATCH), T3 hijau (24 berkas, restore drill), CodeQL 0 hasil, vitest 454/454. Verdict T2 tetap `DISPOSITION_REQUIRED`.
2. **Satu temuan produk P1 baru (F1-12):** jalur impor saldo awal membukukan **batch kedua untuk item stok yang sama** (material+lokasi, atau produk+lokasi) menjadi POSTED lagi → stok dan nilai awal dobel (MATERIAL_INVENTORY/FG_INVENTORY +15,75 dua kali untuk 7 unit fisik), tanpa penolakan. Guard AR hanya membandingkan lintas jalur (impor vs legacy), bukan impor vs impor. Kontrak M:1043 menandai identitas lintas batch "masih perlu kontrak/tes"; M:138 menuntut perlindungan pada semua jalur. Tidak ada di daftar terbuka writer.
3. **Satu P1 protokol rilis (F1-05):** rollback paket T3 tidak pernah diuji (`MANIFEST.json`: `"rollbacks": "NOT_TESTED"`), padahal kontrak menuntut paket permanen dipasang–dipulihkan–dipasang ulang (M:108-115, M:206).
4. **Satu P1 celah kontrak (F1-01):** 25 hasil kasus T2 (12 kalender HOLD, 8 AS, 1 ADJUSTMENT_DATE, 4 AO) bergantung pada keputusan owner 24 Sep yang hanya ada di handoff/skrip writer. Perilaku produk konsisten dengan keputusan itu dan **bacaan literal ERP-DEC01 ("semua leg pada tanggal invoice") secara fisik tidak konsisten** (terbukti: tanpa AZ, WIP negatif sebelum potongan ada). Ini keputusan owner, bukan bug produk.
5. Keluarga yang diuji dengan oracle auditor sendiri dan LULUS pada 9add57e: tutup buku S06 atomik dan penolakan persis; akses fail-closed 10 facade baru untuk anon/unmapped/nonaktif/5 role non-owner (lapisan DB); aksesori 7 PCS eceran persis M:94 (lifecycle penuh + reversal); FG tanpa sumber (konservasi, penolakan persis, periode tertutup); tumpang tindih jalur lama setelah impor ditolak 10/10 jenis; total kontrol tidak pernah dibukukan; replay batch ditolak; keluarga tanggal bentuk tak-ambigu dan periode tertutup.
6. **Rekomendasi:** CP6 tetap HOLD. Yang harus diputuskan owner (tertulis di kontrak): ratifikasi/penolakan keputusan tanggal 24 Sep; identitas lintas batch impor; cakupan CR aksesori/laundry; kebijakan P-03; status ERP-DEC03/ALL. Yang harus dibuktikan writer: perbaikan F1-12 + tes lintas batch untuk semua jenis saldo; rollback T3 native; jalur HTTP/JWT/browser nyata untuk facade CP6; perilaku AV.

## 2. Verdict per gate (diturunkan dari kontrak; rincian kutipan di `audit/out/C1_gates.md`)
| Gate | Isi | Rujukan | Verdict auditor | Dasar / batas |
|---|---|---|---|---|
| GATE-01 | Perlindungan tumpang tindih saldo awal pada SEMUA jalur | M:138, M:229, M:361, M:1043 | **HOLD** | Jalur lama setelah impor ditolak 10/10 jenis (`AR_OPENING_ROUTE_OVERLAP…`, run 36044022037); impor→impor lintas batch DIBUKUKAN dan menggandakan stok (F1-12, run 36045629594). INDEPENDENT_NATIVE_RERUN. |
| GATE-02 | Gerbang gabungan keluarga terdampak pada kandidat beku | M:138, M:1763-1765, M:6661 | **HOLD** | T2 direproduksi identik (run 36037873682) tetapi verdict `DISPOSITION_REQUIRED`; 25 hasil bergantung keputusan di luar kontrak (F1-01). |
| GATE-03 | Gerbang lama Full-Schema/Final Boundary tidak dilonggarkan/dilabel ulang | M:136, M:223, M:957 | **UNVERIFIED** | Tidak diperiksa auditor. Yang diperiksa: T2 tidak melabel ulang hasil beku (oracle-disetujui dicetak terpisah, hasil beku tetap) — CONFIRMED untuk T2 saja. |
| GATE-04 | HTTP/Auth-JWT/browser nyata + concurrency dua koneksi | M:229, M:317, M:422, M:4321 | **UNVERIFIED** | Semua skenario auditor memakai identitas via `set_config(request.jwt.claims)`+`set local session authorization` dalam satu sesi Postgres; job browser T3 hijau tetapi isinya tidak diperiksa per kasus; concurrency hanya T2 AR_CONCURRENCY milik writer (28 PASS). |
| GATE-05 | 12 kasus tanggal HOLD ditutup di bawah ERP-DEC01 satu keluarga recost–GL–HPP–as-of–close | M:1057-1065, M:1080-1086, M:1404, M:6144-6169 | **HOLD** | DECISION_EXISTS_EVIDENCE_MISSING: kontrak = tanggal invoice; produk = leg bahan pada E, leg WIP/FG/HPP pada hari pergerakan (aturan 24 Sep, UNVERIFIED_OWNER_DECISION). Bentuk tak-ambigu dan periode tertutup LULUS oracle auditor (run 36041422305, 36042210333). |
| GATE-06 | Jalur eceran PCS exact (ACC-DEC02) | M:1066-1071, M:1405, M:44, M:94 | **ACCEPT (terbatas)** | 7 PCS @3,25 → 22,75, stok 300→293, master 36,00/lusin tetap, replay idempoten, REVERSE pulih penuh, 5 penolakan input (run 36043204365). Batas: satu sesi; concurrency/deadlock AQ tidak diuji auditor. |
| GATE-07 | Transport CSV nyata untuk scope impor (ERP-DEC03/ALL) | M:138, M:1024-1025, M:1072-1078, M:6381 | **HOLD** | Kontrak memuat dua status ERP-DEC03 yang bertentangan (F1-02); parser CSV browser ada (`src/initialImport.ts`); cakupan ALL dan jalur browser→RPC tidak diverifikasi. |
| GATE-08 | Cakupan role/akses CP6 (AUD-G07) untuk scope final | M:1729, M:1407, M:1526, M:98, M:1322 | **HOLD** | Lapisan DB LULUS: 10 facade baru menolak anon (42501), unmapped, owner nonaktif, dan 5 role non-owner sungguhan; viewer boleh baca workspace aksesori sesuai M:281 (run 36043758572, 36044313409). Jalur HTTP/JWT nyata tidak diuji (GATE-04). |
| GATE-09 | Keluarga perbaikan writer VERIFIED_INDEPENDENT | M:1259, M:1308, M:1720-1722, M:1222-1224 | **HOLD** | CONFIRMED: A04 (vitest 454/454 lokal), S06/B04, AX perilaku, AZ bentuk dasar, AQ 7 PCS, AO/AP total kontrol. UNVERIFIED: AV perilaku, cabang AY rev6–7.4 (retur, konversi, void, batch, relabel, kantong, kontraktor) kecuali 3 jalur REUSED_EVIDENCE. HOLD: F1-12. |
| GATE-10 | Paket migrasi permanen: install / rollback / penolakan, byte-bound | M:163, M:206, M:108-115, M:2713-2719 | **HOLD** | Install 24/24 + verifikasi AW..AZ + restore drill CONFIRMED (run 36037876338). Rollback NOT_TESTED (F1-05). |
| GATE-11 | Freeze SHA/tree/runtime; bukti terikat commit | M:1767, M:132 | **ACCEPT** | Runtime menginstal 9add57e verbatim (40/40 fungsi dev AW..AZ = prosrc; run 36039753521). Batas: modul helper harness diimpor dari baseline ca7f095 (F1-08, tanpa dampak bukti). |
| GATE-12 | Audit independen dengan oracle sendiri atas perbaikan DAN jalur residual | M:4500-4501, M:1436-1437 | **HOLD (sebagian terpenuhi)** | Laporan ini: 10 skenario, 14 run, oracle sendiri. Jalur residual yang belum: lihat §7. |
| GATE-13 | Tidak ada POLICY_BLOCKED/INCOMPLETE/HOLD dalam scope saat lock | M:1699, M:4387, M:1220-1221 | **HOLD** | 12 HOLD + 8 COUNTEREXAMPLE + 5 INCOMPLETE tetap; F1-12 baru. |
| GATE-14 | CP6_LOCK_READY sah lalu acceptance owner | M:1218-1219, M:1418-1420, M:229 | **BELUM (milik owner)** | Bukan wewenang auditor. |
| GATE-15 | Matriks historis: hanya diulang bila dibatalkan; label bukti jelas | M:4391, M:1766, M:1161-1163 | **UNVERIFIED** | Auditor hanya melabeli bukti sendiri; matriks historis writer tidak diperiksa. |
| GATE-16 | CR aksesori/laundry tuntas atau dikecualikan owner secara eksplisit | M:1755-1756, M:1697 | **HOLD** | Tidak ada pernyataan owner di kontrak; usulan writer "kunci daftar selesai" (handoff §18.4) dinyatakan bukan keputusan. |

## 3. Temuan (P0 tidak ada). PRODUK dan TOOLING dipisah.
### 3A. Produk
**F1-12 — P1 — Stok/nilai awal dobel lewat dua batch impor (tumpang tindih impor→impor tidak dijaga)**
- Reproduksi: impor MATERIAL (7 PCS @2,25 = 15,75) lewat RPC impor → POSTED. Batch baru dengan `material_sku`, `location_code`, qty, unit_cost, cutover yang sama → `FINALIZE` → `status POSTED, valid_rows 2, error_rows 0`. Sama untuk cutover lebih awal dan untuk FINISHED_GOODS (`product_sku`+lokasi).
- Oracle auditor: M:138 ("buktikan perlindungan tumpang tindih saldo awal pada semua jalur"), M:1043 (identitas dokumen lintas batch), M:43-46 (impor membukukan draf terakhir; total kontrol bukan transaksi), M:10 ("keuangan, stok, HPP adalah raja"): batch kedua untuk item yang sama harus ditolak/tidak POSTED, ledger dan item POSTED tidak berubah.
- Hasil: `MATERIAL_INVENTORY +15,75` kedua kalinya; item opening POSTED 1→2, qty 7→14, header POSTED 1→2; FG: `FG_INVENTORY +15,75`, qty 14. Replay FINALIZE batch yang sama DITOLAK persis `Impor yang sudah disahkan tidak dapat diedit atau disahkan ulang dengan permintaan baru` (guard replay ada; yang tidak ada adalah identitas lintas batch).
- Akar (INDEPENDENT_SOURCE_REVIEW): `supabase/migrations/20260922185015_erp_v2_6_20ar_cp6_opening_overlap.sql:372` predikat `((h.migration_batch_id is null)<>(oh.migration_batch_id is null))` — hanya membandingkan opening dengan opening POSTED dari jalur lain. Guard roll FABRIC (`Migration roll already exists`, AP:2198-2201) tidak berlaku untuk material non-roll dan FG. Writer sendiri menulis "AR does not claim to detect … every duplicate import source across batches" (`docs/cp6-ar-opening-overlap.md:59-62`), tetapi item ini tidak ada di daftar terbuka handoff (§23.7, §24.4, §25.4, §26.7) dan §26 menyatakan "tidak ada keputusan owner yang tertunda".
- Bukti: run 36044022037 job 107782968845 kasus `OPEN:IMPORT_SAME_MATERIAL_TWICE` (skenario `open_1.py`, sha256 di §9); run 36045629594 job 107788356714 kasus `OPEN2:MATERIAL_SECOND_BATCH_SAME_CUTOVER`, `…EARLIER_CUTOVER`, `OPEN2:FG_SECOND_BATCH_SAME_CUTOVER` COUNTEREXAMPLE, `OPEN2:MATERIAL_SAME_BATCH_FINALIZE_REPLAY` PASS (`open_2.py`). JSON: `audit/runs/auditor_open1_36044022037.json`, `auditor_open2_36045629594.json`. Label: INDEPENDENT_NATIVE_RERUN.
- Batas klaim: diuji untuk MATERIAL (non-roll) dan FINISHED_GOODS; jenis saldo pihak (piutang/utang) diklaim writer punya guard nomor dokumen lintas batch (`docs/cp6-initial-import-progress.md:796`) — tidak diuji auditor.

**F1-05 — P1 (produk/protokol rilis) — Rollback paket T3 tidak pernah diuji**
- `supabase/release/cp6-t3/MANIFEST.json`: `"rollbacks": "NOT_TESTED"`; job install T3 tidak menjalankan tahap rollback/penolakan pasca-pakai; tidak ada berkas rollback AW..AZ di `supabase/rollbacks/` (terakhir AV). Writer mengakui (handoff §23.9 N2 "rollback memang belum diuji").
- Oracle: M:108-115, M:206, M:2713-2719 (paket permanen = dipasang, dipulihkan, dipasang ulang, dipulihkan kembali di disposable; rollback hanya sebelum pakai).
- Bukti: run 36037876338 job 107762395202 (install 24/24 PASS, AW_AX_AY_AZ_VERIFY PASS, restore drill RESTORED_SAME_MEANING) — INDEPENDENT_NATIVE_RERUN + INDEPENDENT_ARTIFACT_CHECK. Terkait: F1-11 (rollback AV memulihkan fungsi yang diganti secara dinamis dari kapsul `pg_get_functiondef` + digest guard, rollback AV baris 36-135; masuk akal statis, belum native).

**F1-01 — P1 (CONTRACT_GAP, bukan bug produk) — Aturan tanggal koreksi biaya tidak lengkap di kontrak; 25 hasil T2 bergantung pada keputusan 24 Sep yang tidak tertulis di kontrak**
- Kontrak ERP-DEC01 (M:1057-1062, P:999-1004): koreksi periode terbuka mengikuti tanggal invoice, konsisten di persediaan/jurnal/WIP/FG/HPP/laporan/readiness. Produk 9add57e: leg bahan dikoreksi pada E di akun tempat unit berada pada E; leg WIP/FG/HPP mengikuti hari pergerakan fisik (aturan "prinsip WIP", handoff §23.1).
- Bukti auditor: fase sebelum AZ (run 36041435083, 36042223829): leg WIP dibukukan pada E sebelum potongan ada → WIP PO negatif (−8; −14 saat baru 3 unit dipotong; +20 sebelum barang ada). Fase sesudah AZ (36041422305, 36042210333): tidak ada saldo negatif per tanggal; leg bahan pada E; konservasi terpenuhi; periode tertutup: jurnal bertanggal ekonomi E diposting hari pengakuan, hari tertutup tak berubah. Jadi bacaan literal "semua leg pada E" tidak dapat dipenuhi tanpa saldo negatif; aturan penyelesaiannya hanya ada di handoff → UNVERIFIED_OWNER_DECISION.
- Dampak: GATE-05, GATE-02, GATE-13 tidak bisa ditutup dari kontrak saja. Klasifikasi T2 di §4.

**F1-02 — P2 (CONTRACT_GAP) — ERP-DEC03/ALL: dua status bertentangan di kontrak**
- M:1072-1078 "masih perlu penjelasan cakupan" vs M:1024 "ALL data awal disetujui"; kewajiban ALL tetap (M:138, M:1043). Kandidat punya parser CSV browser (`src/initialImport.ts` `parseInitialImportCsv`; `src/ConnectedInitialImportPage.tsx:267-286` unduh template + unggah → RPC) — INDEPENDENT_SOURCE_REVIEW. Cakupan entitas vs ALL (M:1043: master laundry/lokasi/akun, uang muka, penerimaan belum ditagih, invoice sebagian, WIP fisik per ukuran/tahap) dan jalur browser→HTTP→RPC tidak diverifikasi.

**F1-06 — P3 — Advisors 73→127 (+54 INFO `rls_enabled_no_policy`)** untuk tabel internal erp (kapsul rollback AC..AZ, fg_unsourced_*, initial_import_*, accounting_close_filings_v1, po_hpp_gl_*_state_v1, …). Status REVIEW_REQUIRED; kontrak tidak menetapkan ambang (M:112). Run 36037876338 job 107762395202.

**Ditarik:** F1-09 (potong sebelum penerimaan) — REFUTED oleh run 36042210333: RPC cutting MENOLAK potongan 08:00 sebelum penerimaan 23:30 (S04 terpenuhi); F1-13 (viewer membaca workspace aksesori) — oracle auditor salah, produk sesuai M:281.

### 3B. Tooling / protokol
**F1-04 — P2 — Runtime skenario auditor punya celah isolasi** (run 36039753521 job 107768697263, 36040954954 job 107772716244): commit lewat koneksi kedua ke tabel `erp.*` TERDETEKSI (`full_boundary_restored=false`) tetapi commit ke skema `public` tidak; id kasus ganda menimpa hasil sebelumnya (7 dari 8 kasus dihitung); status bebas (`OK`) diterima; advisory lock sesi lolos rollback savepoint; sequence tidak di-rollback; hanya FAIL/INCOMPLETE membuat job merah, COUNTEREXAMPLE tidak → warna job bukan bukti. Auditor membaca status per kasus. (pack §4)

**F1-03 — P2 — Harness T2 mengubah lingkungan sebelum assertion** (`CP6_T2_SEED=QUIETED`, `CP6_T2_FIXTURE=PAYROLL_APPROVED`, `cp6_t2_regression.py:24-40`) atas dasar "arahan owner 24 Sep" (handoff §22 baris 936) yang tidak ada di kontrak. Hasil PROVEN untuk kasus yang bergantung readiness berlaku hanya di bawah completion itu (M:4322-4324: setup harus dinyatakan). Writer menyatakannya terbuka di §20.6/§23.5.

**F1-07 — P3 — Restore drill T3** memeriksa `restore_errors_only_pg_cron`, `catalog_explained`, `data_identical`, `engine_equal` (log job 107762395202); data dan jawaban engine identik, tetapi toleransi katalog "dijelaskan" (constraint reparse/extension/index/view) adalah penilaian writer, bukan oracle kontrak (M:108-110 "tepat").

**F1-08 / F1-10 — INFO** — `writer/scripts` (baseline ca7f095) mendahului `auditor/scripts` di sys.path (11 modul helper diimpor dari baseline); fungsi dev AW..AZ tetap terpasang verbatim dari 9add57e; `cp6_au_browser_fixture.py` versi kandidat tetap dipakai T3 karena dijalankan sebagai skrip dari checkout auditor. Tanpa dampak bukti.

## 4. Klasifikasi kasus T2 beku/HOLD (rerun auditor 36037873682; tidak ada relabel)
| Bucket | Jumlah | Kelas | Dasar kontrak |
|---|---|---|---|
| 12 kalender HOLD (`DATE_POLICY_REVIEW_REQUIRED`; oracle beku COUNTEREXAMPLE pada `material_event_date`; oracle-disetujui 12/12 MATCH) | 12 | **DECISION_EXISTS_EVIDENCE_MISSING** | ERP-DEC01 ada (M:1057-1062) tetapi bukti pada 9add57e mengikuti aturan hari potong (24 Sep, hanya di handoff); "12 HOLD tetap sampai kebijakan dan bukti lengkap" (M:1406). Tetap HOLD. |
| 8 AS `DATE:False:<zona>:True:<biaya>` (beku COUNTEREXAMPLE; disetujui 8/8 MATCH) | 8 | **DECISION_MISSING** | Kontrak tidak memuat "HPP PO ikut hari barang jadi/jual"; di bawah ERP-DEC01 hasilnya COUNTEREXAMPLE. Perilaku produk direproduksi juga dengan oracle auditor (date_family), penerimaannya keputusan owner. |
| `ADJUSTMENT_DATE:False` (beku INCOMPLETE; disetujui MATCH) | 1 | **DECISION_MISSING** | Tidak ada aturan tanggal revaluasi penyesuaian di kontrak; M:4324: tool/setup error = INCOMPLETE. |
| AO trial `INVOICE:*:False` (periode terbuka, INCOMPLETE; disetujui MATCH) | 2 | **DECISION_MISSING** | Perilaku mengikuti keputusan 24 Sep. |
| AO trial `INVOICE:*:True` (periode tertutup, INCOMPLETE; disetujui MATCH) | 2 | **DECISION_EXISTS_EVIDENCE_MISSING** | M:1061 "aturan periode tertutup tetap memakai penyesuaian terkendali yang sudah ada"; oracle trial tidak selesai. |
| Sisanya: BUSINESS 179 PASS + 39 CONTROL_PASS, IMPORTS 31, VALUES 65, NEW_CASES 25, AR 146+28, AT 16+4, AU 15+6 | — | **COVERED_BY_OWNER_DECISION+PROVEN** | Identik per id dengan referensi AU (`T2_IDENTITY` moved [] pada grup lama). Caveat F1-03 (fixture completion). |

## 5. Rekonsiliasi fase 2 (dibuka setelah kunci; catatan lengkap `audit/out/phase2_reconciliation.md`)
### 5A. Klaim writer utama
| Klaim writer (handoff §18–20, §23–27) | Label auditor |
|---|---|
| T2 identik per kasus dengan AU; 12 HOLD identik; verdict DISPOSITION_REQUIRED (§26.6, §27.5) | CONFIRMED (rerun 36037873682) |
| Oracle-disetujui: AS 8/8, kalender 12/12, AO 4/4, ADJUSTMENT_DATE MATCH | CONFIRMED sebagai reproduksi harness (`T2_APPROVED_ORACLE_SUMMARY` 8/8; `calendar_policy` 12 MATCH, log baris 2196/2199; `APPROVED_ORACLE_B` 5 PASS). MATCH ≠ PASS beku; penerimaan = UNVERIFIED_OWNER_DECISION |
| T3 hijau: 24 file, AW..AZ verified, RESTORED_SAME_MEANING, advisor 127, browser 10/10 (§27.5) | CONFIRMED (rerun 36037876338) kecuali rincian browser 10/10 tidak diperiksa per kasus |
| CodeQL 0 hasil 4 bahasa (§27.5) | CONFIRMED (rerun 36037878419); batas: SQL/PLpgSQL tidak dianalisis |
| A04-R2: 454/454 vitest; browser NOT_RUN (§18.3) | CONFIRMED lokal (`npx vitest run` 454/454; 4 berkas gagal = Playwright spec di luar `npm test` yang memakai `--exclude tests/browser/**`) |
| AW P-01..P-04 diperbaiki; registri 108 cek; S06 atomik (§20.2) | CONFIRMED sebagian (S06 atomik, penolakan persis, filing immutable, periode tertutup); registri 108 dan P-04 race dua sesi UNVERIFIED |
| AX perilaku (§20.3) | CONFIRMED perilaku (run 36043204365); kebijakannya UNVERIFIED_OWNER_DECISION |
| AZ menghilangkan WIP/persediaan negatif per tanggal (§23.2) | CONFIRMED bentuk dasar (date_family before/after) |
| AB-01 diperbaiki di 46ad845 (§27.1) | REUSED_EVIDENCE: run GPT 36034620907 (head 9add57e, job 107751512664, sha skenario dfd9ad70…) 4/4 PASS untuk pemakaian kantong dibalik + invoice terlambat, write-off dibalik, potong dibatalkan sebelum jahit |
| AV rev2 (identitas) writer-qualified, GPT ulang 5 fase (§19.1) | UNVERIFIED perilaku; instalasi CONFIRMED (T3) |
| G-01 hosted selaras; usulan (b) (§20.1, §20.5) | UNVERIFIED (hosted di luar batas auditor) |
| "Tidak ada keputusan owner yang tertunda" (§26) | REFUTED sebagian: F1-12, P-03 (§20.5 no.1), keputusan 24 Sep belum masuk kontrak, CR aksesori/laundry (GATE-16) |
| Penerimaan independen AY rev7.4/AZ rev2.1/AB-01 = RERUN_REQUIRED (§27.6) | Skenario auditor = jawaban parsial (bentuk dasar + periode tertutup + 3 jalur GPT); cabang rev6–7.4 lainnya UNVERIFIED |

### 5B. Keputusan owner yang hanya ada di handoff/skrip (UNVERIFIED_OWNER_DECISION — perlu ditulis ke kontrak atau dikonfirmasi owner)
1. 8 kasus AS: HPP PO mengikuti hari barang jadi/jual; nominal dan tanggal invoice tetap (§23.1).
2. Prinsip WIP `max(E, tanggal fisik potong)`; "Ikut prinsip WIP" untuk revaluasi bahan→WIP (§23.1).
3. Jawaban kedua 24 Sep: 12 kalender HOLD ikut hari potong (tetap HOLD); AO terbuka ikut hari pindah tahap; AO tertutup posting hari pengakuan; ADJUSTMENT_DATE tidak disahkan otomatis (§23.1; `cp6_t2_regression.py:42-52`).
4. AX: HPP rata-rata pada tanggal fisik hanya untuk barang tanpa nilai asal; tidak pernah Rp0 kecuali owner+alasan; Cr Pendapatan lain (§19.2, §20.3).
5. Invoice pemasok bertanggal sebelum barang diterima → dibukukan hari terima (§26.2).
6. Fixture kasus T2 dilengkapi (payroll disetujui) dan seed QUIETED (§22 baris 936; F1-03).
7. Cakupan CP6 dikunci pada A04-R2, AV, AW, AX, gerbang rilis (draf GPT diteruskan owner, §19.1) — bertentangan dengan M:1699/M:2148 (33 AUD-ID + aksesori/laundry) bila dibaca sebagai pengecualian.
8. "Pertahankan pemeriksaan saldo negatif per tanggal" per akun (§26.4 no.5).

## 6. Label bukti per klaim auditor (dan batasnya)
| Klaim auditor | Label | Batas |
|---|---|---|
| Kandidat 9add57e terpasang verbatim; 40/40 fungsi dev = prosrc | INDEPENDENT_NATIVE_RERUN (36039753521) | Fungsi dev AW..AZ saja; migrasi AC..AV via rantai harness |
| T2/T3/CodeQL direproduksi | INDEPENDENT_NATIVE_RERUN (36037873682, 36037876338, 36037878419) | Oracle milik writer; auditor membaca status per kasus |
| Tumpang tindih legacy setelah impor ditolak 10/10; total kontrol tidak dibukukan; replay ditolak; impor→impor dobel | INDEPENDENT_NATIVE_RERUN (36044022037, 36045629594) | Data generator writer `cp6_opening_overlap_probe.imported`; oracle auditor |
| Keluarga tanggal: bentuk tak-ambigu, periode tertutup, atribusi AZ | INDEPENDENT_NATIVE_RERUN before/after (36041422305/36041435083, 36042210333/36042223829) | Fixture auditor via helper writer `cp6_az_probe`; potong pada d+1 |
| Tutup buku S06 atomik, penolakan persis, filing immutable | INDEPENDENT_NATIVE_RERUN (36042716805) | Satu sesi; race dua sesi tidak diuji |
| Akses fail-closed 10 facade: anon, unmapped, nonaktif, 5 role | INDEPENDENT_NATIVE_RERUN (36043758572, 36044313409) | Lapisan DB (session authorization + klaim JWT); bukan HTTP nyata |
| Aksesori 7 PCS persis M:94; FG tanpa sumber konservasi/penolakan | INDEPENDENT_NATIVE_RERUN (36043204365) | Satu sesi |
| vitest 454/454 | INDEPENDENT_NATIVE_RERUN lokal (jsdom) | Bukan browser/HTTP |
| CSV parser ada; akar F1-12; rollback AV via kapsul; require_owner_admin/current_app_role | INDEPENDENT_SOURCE_REVIEW | Statis |
| Manifest T3 rollbacks NOT_TESTED; package_sha256 cocok | INDEPENDENT_ARTIFACT_CHECK | — |
| AB-01/AZ rev2.1/AY rev7.4 tiga jalur | REUSED_EVIDENCE (36034620907, head 9add57e) | Hanya jalur itu; oracle GPT |

## 7. Yang TIDAK diperiksa auditor (batas klaim laporan ini)
- Concurrency/deadlock AQ (urutan kunci) dengan oracle auditor; hanya T2 AR_CONCURRENCY milik writer.
- Jalur HTTP/JWT/browser nyata (browser→HTTP→RPC) untuk facade CP6; isi job browser T3 per kasus.
- IDENT/AV: perilaku identitas produk; rollback AV native.
- Rollback paket T3 (NOT_TESTED oleh writer, tidak dijalankan auditor).
- Transport CSV browser→RPC dan cakupan ALL impor; G-01 hosted (hosted tidak boleh disentuh).
- Cabang AY rev6–7.4 / AZ rev2.x di luar bentuk dasar: retur, konversi/relabel, void/QC ulang, batch lintas hari, kantong per pool, kontraktor, PO tanpa state, antrean recost non-invoice, invoice multi-penerimaan (kecuali 3 jalur REUSED_EVIDENCE).
- Guard lintas batch untuk jenis saldo pihak (piutang/utang) dan roll FABRIC pada jalur impor.
- Matriks historis writer (GATE-15) dan gerbang lama Full-Schema/Final Boundary (GATE-03).
- Verifikasi adversarial dua lensa atas temuan P1–P2 oleh agen terpisah belum berjalan (batas sesi akun sampai 22:20 UTC); temuan P1 di sini masing-masing didukung ≥2 run native atau manifest + sumber.

## 8. Rekomendasi (bukan keputusan)
1. **CP6 tetap HOLD; `production_go=false`.**
2. **Owner (tulis di kontrak):** (a) ratifikasi atau tolak keputusan tanggal 24 Sep (§5B no.1–3,5) sebagai amandemen ERP-DEC01, lalu 12+8+1+4 kasus di-oracle ulang dan dijalankan ulang, bukan dilabel ulang; (b) tetapkan identitas dokumen lintas batch untuk item stok impor (F1-12); (c) nyatakan cakupan CR aksesori/laundry (GATE-16); (d) putuskan P-03 (tahan semua tanggal vs per tanggal); (e) satu status ERP-DEC03/ALL (F1-02); (f) kebijakan AX (§5B no.4) bila ingin dianggap keputusan.
3. **Writer (bukti native pada kandidat beku baru):** perbaikan F1-12 + tes lintas batch untuk semua jenis saldo (MATERIAL non-roll, roll, FG, BS, WIP, pihak, kas) dua arah; rollback T3 native (pasang–pulihkan–pasang ulang) untuk paket 24 berkas; jalur HTTP/JWT/browser nyata untuk 10 facade CP6 dengan role anon/unmapped/nonaktif/view-only; perilaku AV; cabang AY/AZ tanpa fixture native (§7).
4. **Protokol:** runtime skenario auditor perlu deteksi commit ke skema `public`, penolakan id kasus ganda dan status di luar kosakata (F1-04); harness T2 mencetak completion fixture sebagai bagian hasil (F1-03).

## 9. Lampiran
### 9A. Run auditor (semua head_sha 9add57e)
| Workflow | Run | Job(s) | Skenario / isi |
|---|---|---|---|
| cp6-candidate-codeql.yml | 36037878419 | 107762403880 js-ts, 107762404091 python, 107762404177 actions, 107762404232 c-cpp | 4× `result_count 0` |
| cp6-t2-regression.yml | 36037873682 | 107762384861 ar, 107762384959 temporal, 107762385235 regression | lihat §4 |
| cp6-t3-release-package.yml | 36037876338 | 107762395202 install, 107762394813 capture, 107762395187 browser | 24/24, verify, restore drill, advisors 127 |
| cp6-auditor-scenario.yml | 36039753521 | 107768697263 | rt_probe_1 |
| cp6-auditor-scenario.yml | 36040954954 | 107772716244 | rt_probe_2 (job merah by design: kasus terakhir COMMIT) |
| cp6-auditor-scenario.yml | 36041422305 / 36041435083 | 107774254372 / 107774296346 | date_family_1 after / before |
| cp6-auditor-scenario.yml | 36042210333 / 36042223829 | 107776876564 / 107776920429 | date_family_2 after / before |
| cp6-auditor-scenario.yml | 36042716805 | 107778594395 | close_access_1 |
| cp6-auditor-scenario.yml | 36043204365 | 107780207435 | fg_acc_1 |
| cp6-auditor-scenario.yml | 36043758572 | 107782073208 | access_2 |
| cp6-auditor-scenario.yml | 36044022037 | 107782968845 | open_1 |
| cp6-auditor-scenario.yml | 36044313409 | 107783945930 | access_3 |
| cp6-auditor-scenario.yml | 36045629594 | 107788356714 | open_2 |
| (REUSED) cp6-auditor-scenario.yml | 36034620907 | 107751512664 | empat skenario GPT |
Per-kasus: `AUDIT_PROGRESS.md` tabel d) dan JSON di `audit/runs/`.

### 9B. Skenario auditor (`audit/scenarios/`, sha256 = `audit/scenarios/SHA256SUMS`)
| Berkas | sha256 |
|---|---|
| `access_2.py` | `e1f4093c9c683627af1a46a0f9a18ae0955718c1e6b72bc52a9abfd733acc310` |
| `access_3.py` | `1f1a25bc069d947db0441d64e4db30b9bc1a70e66d6267a6ef54c66be4453afd` |
| `close_access_1.py` | `cafea79d8d73f8979475c7ebe27837ecf65a4181630ba40bbbdc0cb5bd182f5f` |
| `date_family_1.py` | `492908b5dcf3184bacabcb99a878630c1b206e67c5d6f96586f02105f4a537d0` |
| `date_family_2.py` | `44f09ad11948e15cbfc0df20925c10acec055888f6f4b46c6b577eb3f4f4a9a8` |
| `fg_acc_1.py` | `79da4c2e77f5ad3dc0a57d084ad426faf7db5e42f81c4ebf244270539bfa11a7` |
| `open_1.py` | `983a66f58524aeebb8f57826023ada76b2bb5757b80ed61680cca0c3cb125333` |
| `rt_probe_1.py` | `13b3b800900e55d5ae60d67baafffec6aa07216da76bf6b7a95534f42da0c33a` |
| `rt_probe_2.py` | `cd6df40c868afefa9023c84d6c4f284f3b79d4abaa63907d66101b8395d82789` |
| `open_2.py` | `e8b84000396cc6e9ee27cdd49a50ea3d3806386a7b916e7868fc9b974709e9e0` |

### 9C. Berkas audit lain
`audit/PHASE1_FINDINGS.md` (kunci fase 1), `audit/out/C1_gates.md` (turunan gate + kutipan), `audit/out/T2_classification.md`, `audit/out/RT_probe1_findings.md`, `audit/out/RT_probe2_findings.md`, `audit/out/DATE_family_results.md`, `audit/out/phase2_reconciliation.md`, `audit/tools/` (dispatch_scenario.py, parse_saved_log.py, phase1_derive.js, phase1_verify.js), `audit/runs/` (JSON per run, ledger dispatch, log vitest).

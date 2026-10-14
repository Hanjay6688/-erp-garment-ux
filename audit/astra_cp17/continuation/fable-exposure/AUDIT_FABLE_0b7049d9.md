# AUDIT FABLE — commit 0b7049d9203bac52b47a4c89f3e0d75646067a8f tree ce6aed0a… — 2026-10-14 (putaran cp17-20261014, DRAFT v0.1 — belum dikunci)

Lingkungan: GitHub Actions ubuntu-24.04; Supabase CLI 2.116.0 dengan PostgreSQL 17.6.1.165 (basis sekali pakai, hosted-faithful G-01 opsi 1); Node 22; Chromium/Playwright untuk grup browser; psycopg 3.2.10; Python 3.12. Tidak ada koneksi ke hosted Supabase Enteng/legacy/produksi; tidak ada SQL ke hosted; tidak ada pemasangan pg_cron/backup di mana pun selain salinan sekali pakai.

Perintah yang dijalankan: `workflow_dispatch` lewat REST untuk 56 run (14 workflow CP7, 31 workflow CP3–CP6, 2 run Fable) — daftar lengkap dan id job di `REGISTER_RUNS.md` dan `runs/cp17/dispatch_ledger_cp17.jsonl`; pembacaan log per kasus lokal (`case_summary.py`, status dari baris JSON, bukan warna job); tinjauan sumber baca-saja pohon beku (`review/R1..R6`); skenario Fable `audit/fable_cp7/scenarios/fable_cp17_chain.py` (run 38557410928) dan `fable_cp7_smoke.py` (run 38522428512) pada `product_ref=0b7049d9` lewat `AUDIT/fable/cp7-native`.

Manifest putaran: `MANIFEST.md` (tree produk, sha panduan 5752e96d…, pernyataan paparan). Register keputusan yang dipakai sebagai oracle: `docs/cp7/OWNER_DECISIONS_20261008.md` (s.d. D13-13), `audit/fable_cp7/OWNER_DECISIONS_TO_AUDITOR_20261013.md`, addendum CP6 2026-09-25 (D01–D06), D11/GBD-03.

## Ringkasan
[[PENDING — diisi setelah run rantai Fable 38557410928 dan tinjauan R2/R5 selesai]]

## Vonis per tahap (diminta HANDOFF_FABLE.md)

| Tahap | Vonis | Alasan singkat |
|---|---|---|
| CP1 (fingerprint/baseline, single writer) | **BELUM DIPERIKSA — TIDAK DAPAT DIVERIFIKASI DARI SESI INI** | Set fingerprint asli (A1–A4 di `review/R6`) hanya ada di dua cabang bukti yang tidak pernah menjadi leluhur 0b7049d9; pohon beku hanya memuat pin turunan (sha `a0c59b96…` dikutip, algoritmanya tidak di pohon). Auditor tidak boleh query hosted (§1.2). Status terbaik: REUSED_WRITER_EVIDENCE. |
| CP2 (backup terenkripsi + restore basis pra-v2.6.10) | **BELUM DIPERIKSA — TIDAK DAPAT DIVERIFIKASI DARI SESI INI** | Arsip `…CP2_BACKUP_20260831T193529Z.zip.enc`, kunci, set restore, dan artefak bukti restore semuanya di luar git (artefak Actions sudah kedaluwarsa; klaim Drive/perpustakaan chat); hanya sha256 yang ada di repo; tidak ada restore independen non-penulis; manifest CP2 sendiri menyebut basis **pasca** v2.6.11a. Daftar ABSENT eksplisit di `review/R6` §B. |
| CP3 / CP3.5 (absensi → HPP → payroll) | [[PENDING]] | Regresi runtime: T2 (Original 326 + AS 34, AR 174, AT/AU) identik multiset dengan beku r16; P12 payroll 3 job PASS. Tinjauan sumber R1 mengangkat hipotesis S1 (R1-01..R1-05) — status setelah run rantai Fable: [[PENDING]]. |
| CP4 / CP4.5 (RBAC, identitas produksi, WIP) | [[PENDING — R2]] | Runtime: AT 16 + AU 15 + races PASS (identitas temporal/produk), AV qualification after PASS, matriks Auth/HTTP di setiap job CP7 PASS. Tinjauan sumber R2: [[PENDING]]. |
| CP5 (potong → pickup → WIP → BS/rework/klaim) | [[PENDING]] | Runtime: T2 identik, AV after PASS, cutting-bridge/CP5 snapshot workflow = gate identitas historis (tidak menguji 0b7049d9, lihat RED_CLASSIFICATION). Tinjauan sumber R3: 13 hipotesis (R3-01..R3-13), S1 belum dibuktikan/dibantah kecuali yang diuji run rantai. |
| CP6 (cutover, uang muka, tutup buku, HPP bertanggal, paket T3) | **LULUS DENGAN SYARAT** | T2 identik beku r16; paket rilis T3 `ALL_STAGES_INSTALLED` (104 native + 26 races + 9 http PASS; browser 27 PASS + 4 INCOMPLETE yang diterima D13-9c/F-UI-02); rollback 152 objek identik; G-01 `ALIGNED_PER_OBJECT`; probe T1 AW..BE after 0 merah. Syarat: FABLE-001 (dua salinan AC berbeda), FABLE-003 (manifest rilis menyatakan rollback NOT_TESTED), hipotesis R4-02 (tidak ada lantai cutover untuk writer masuk) diputuskan owner. |
| CP7 | **LULUS** (dibekukan D13-13; dikonfirmasi ulang) | 26/26 job berkasus identik multiset dengan putaran retest/XC; smoke Fable PASS; tidak ada `business_day_retried`; `cp6_restored`/`advisor_gate` true di semua SUMMARY. Catatan S3 FABLE-001 menyentuh pemasangan baru (CP7C/VPS), bukan CP7 beku. |

## Temuan
[[PENDING — FABLE-001… ditulis setelah run rantai; rancangan triase di bagian bawah berkas ini]]

## Matriks invarian
[[PENDING]]

## Yang belum saya periksa (wajib)
1. CP1 dan CP2 (lihat vonis): tidak ada artefak di pohon beku; tidak boleh query hosted.
2. Daftar alert CodeQL (`code-scanning/alerts` → 403 untuk auditor): hanya "analisis selesai" yang terbukti, bukan "nol alert".
3. Rencana "uji gabungan 75 kasus C6 + 22 ALL dari ujung ke ujung pada satu head": tidak ditemukan bukti eksekusi satu-ke-satu di pohon beku (`review/R6` §D4); yang ada adalah 90 native + 22 contention + 8 HTTP + 27 browser BF (penulis, add1704a) dan T2 era AU.
4. Workflow CP3-R4/CP4/CP4.5/CP5/cutting-bridge/CP6 full-schema/review-scope/readiness: semuanya gate identitas historis yang menolak di 0b7049d9 (`runs/cp17/RED_CLASSIFICATION.md`); regresi CP3–CP5 pada kode final hanya lewat T2, suite CP7 (P12/P18/full cycle), dan skenario rantai Fable.
5. CP7C (backup offsite, restore drill, `ops/backup-repo/`): **di luar lingkup** per D13-9a — tidak diperiksa, tidak dinyatakan lulus.
6. Hosted: `show timezone`, fingerprint hari ini vs CP1/G-01, apakah skema `erp` terjangkau PostgREST di hosted (relevan R3-07) — TIDAK DAPAT DIVERIFIKASI DARI SESI INI.
7. Materi auditor lain (Astra): tidak dibuka sama sekali sampai laporan ini dikunci (D13-11/§10).
8. Jalur klaim laundry mundur (R3-03) dan R3-04..R3-12, R1-01..R1-04, R1-06..R1-12, R4-03, R4-04: hanya tinjauan sumber (STATIC) kecuali disebut lain di Temuan.
9. Tinjauan R2 (CP4/4.5) dan R5 (jahitan lintas tahap): [[PENDING — subagen terputus oleh batas pemakaian pada percobaan pertama, dijalankan ulang satu per satu]].

## Hasil merah yang bukan temuan (wajib)
Semua 26 job merah regresi: `runs/cp17/RED_CLASSIFICATION.md` (25 gate identitas historis/READINESS_SCOPE/merge-commit assert/`source()` trial/AS_SCOPE/AD admission; 1 = `cp6-t3-aligned-install` → `runs/cp17/AC_VIEW_MISMATCH.md`, GUARD_BY_DESIGN pada jalur T3_PREP yang penulis sendiri catat menolak). Baris non-PASS di job hijau:

| Run / kasus | Status | Klasifikasi §8 | Alasan |
|---|---|---|---|
| T2 AR `ACCESSORY_CONNECTED_ZERO` | INCOMPLETE | SUPERSEDED_BY_OWNER_RULE (D11, ERP-DEC02 `BC_FREE_REQUIRES_POLICY`) | harga eceran 0 hanya lewat gratis Special; kasus lama basi; identik dengan beku r16 |
| T2 NEW_CASES `DATE:False:*:True:{20,20.003}` ×8, `ADJUSTMENT_DATE:False` INCOMPLETE, T2_CALENDAR_POLICY ×12, AO_TRIAL INCOMPLETE ×4, BUSINESS DATE_POLICY_REVIEW_REQUIRED ×12 | COUNTEREXAMPLE/INCOMPLETE/DPRR | FROZEN_CP6_DISPOSITION / ACCEPTED_BY_DECISION (D01, r16, D11) | disposisi beku (docs/evidence/cp6-t2, r16); multiset identik |
| T3 release browser READINESS ×2, SALES_MANUAL_13 ×2 | INCOMPLETE | ACCEPTED_BY_DECISION (F-UI-02 legacy; D13-9c retired) | gate installed/primary_unchanged true |
| AV `*_BEFORE`, T1 `*_CASES_BEFORE` (AW..BE) | COUNTEREXAMPLE/NO_ROUTE/N/A | GUARD_BY_DESIGN | probe "before" mendemonstrasikan cacat pada predecessor; "after" 0 merah |
| S06 close probe PENDING/RUNNING/FAILED_* | COUNTEREXAMPLE | LEGACY_RUNTIME_OBSERVATION_ONLY | probe AUD-S06 di AU beku (runtime 690 objek era AN), ditutup oleh AW; bukan 0b7049d9 |
| auditor-scenario self-test ST:* ×6, ST:COMMITS | INCOMPLETE | AUDITOR_TOOL (self-test negatif) | runtime auditor mendeteksi pelanggaran yang disuntik: `SELFTEST_PASS` |
| p08-shell `shell` SUMMARY INCOMPLETE ×6 | INCOMPLETE | AUDITOR_TOOL (uji-diri shell) | `deliberate restoration lock failure`, `earlier actual case failure` terdeteksi |
| AW after `DISCOVERY:SEED`, AX after `AX:BACKDATED_OBSERVATION` | OBSERVED | observasi berlabel penulis | bukan PASS; AX: tanggal fisik tertutup "dicakup iterasi berikut" → masuk daftar belum diperiksa |

## Label asal-bukti per klaim (wajib)
| Klaim | Label §2.9 | Run / commit |
|---|---|---|
| Regresi CP6 T2/T3/rollback/probe/AV/G-01 pada ref 00b0eb24 (produk 0b7049d9) | INDEPENDENT_NATIVE_RERUN (Fable dispatch; status per kasus) | 38522008302, 38522017994, 38522026931, 38522044340, 38522054629, 38522090695..38522171091, 38522248192 |
| Regresi CP7 14 workflow | INDEPENDENT_NATIVE_RERUN | 38521746469 … 38521872645 |
| Smoke Fable pada 0b7049d9 | FABLE | 38522428512 |
| Rantai lintas tahap Fable (SKN-22) | FABLE (oracle Fable; fixture_origin=writer E01/P18; angka worksheet E01 = owner-approved) | 38557410928 |
| CP7 vonis beku v1.2 (R2-A6 LENGKAP, R2-F05 DITUTUP, R2-REG identik) | FABLE + WRITER_CROSSCHECK | `audit/fable_cp7/AUDIT_FABLE_XC2_0b7049d9_v1.2.md` |
| Tinjauan sumber R1/R3/R4/R6 (+R2/R5) | INDEPENDENT_SOURCE_REVIEW (STATIC) | `review/*.md` pada 0b7049d9 |
| CodeQL 4 bahasa "selesai" | WRITER_CROSSCHECK untuk klaim nol alert | 38521863082 |
| CP1/CP2 | REUSED_WRITER_EVIDENCE / TIDAK DAPAT DIVERIFIKASI | `review/R6` |
| CP7C backup tools | NOT_APPLICABLE (D13-9a, di luar lingkup) | — |

## Pertanyaan untuk owner, masing-masing dengan rekomendasi auditor (wajib)
[[PENDING — dirapikan setelah temuan final; rancangan: (1) sumber kanonik migrasi AC untuk pemasangan baru; (2) GBD-03 opsi 1 diperluas eksplisit ke BS QC/jahit (R3-04); (3) jalur sah pengembalian sisa kain ke stok (R3-09); (4) lantai cutover untuk writer masuk (R4-02); (5) koreksi pickup POSTED (R3-06) — masing-masing dengan rekomendasi]]

## Ringkasan untuk owner (bahasa sehari-hari, ≤ 10 kalimat)
[[PENDING]]

## Fokus tambahan yang menurut saya paling berisiko
[[PENDING]]

## Register run
Lihat `REGISTER_RUNS.md` (B1 CP6, B2 CP7, [[B3 Fable chain PENDING]]).

## Pernyataan paparan (§16.7)
Fable hanya membaca pohon beku 0b7049d9 dan cabang penulis `claude/new-session-deapao`; menulis hanya ke cabang `audit/fable-cp1-7-0b7049d9-20261014`; tidak membuka cabang/run/artefak Astra; tidak mengirim pesan ke pihak lain; tidak meminta kredensial; tidak menyentuh hosted/produksi/Cloudflare; `production_go:false`.

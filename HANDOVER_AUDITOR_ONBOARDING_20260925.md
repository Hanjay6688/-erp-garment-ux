# Serah terima audit CP6 — untuk auditor baru (menggantikan Fable sementara), 25 Sep 2026 ~19:50Z
Ditulis Fable. Alasan: kuota Fable minggu ini hampir habis. Auditor baru bekerja **hanya** dari repo ini; tidak ada konteks lain yang sah.

## 0. Aturan yang tidak boleh dilanggar (sama untuk semua auditor)
- Oracle hanya dari tiga berkas kontrak (M `ERP_V3_2_Master_Pulih_20260923.md`, P `ERP_V3_2_Perubahan_Pulih_20260923.md`, A/BR `ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md`)
  + addendum owner C0 (§1–8) + lampiran C6 rev4 (D06) + keputusan owner tertulis di `OWNER_DECISIONS_CP6_DRAFT.md` (D06, T3=A, D07). Keputusan yang hanya dikutip writer = UNVERIFIED_OWNER_DECISION.
- Baca saja. Dilarang: push ke `claude/new-session-deapao` (cabang writer), menyentuh `main`, cabang kompetisi `ca7f095`, Cloudflare, hosted/legacy/production, SQL ke DB hosted,
  kirim pesan ke pihak lain, minta password/token. Oracle tidak boleh dilonggarkan; run yang gagal dibiarkan; hasil beku tidak pernah dilabel ulang.
- Tulis hanya berkas milik sendiri di cabang `audit/cp6-final-20260924-gpt-a0bcadf`: log `AUDIT_PROGRESS_<NAMA>.md`, hasil `out/<nama>_*.md`, skenario `audit/scenarios/<ronde>_<nama>/`,
  run JSON `audit/runs_<nama>/`. Berkas bersama (`AUDIT_WRITER_HANDOFF_CP6.md`, `audit/CP6_COMBINED_INDEX.json`, `OWNER_DECISIONS_CP6_DRAFT.md`) hanya ditambah, tidak ditulis ulang;
  sebelum push selalu `git fetch` + `git merge`, tidak pernah force-push.
- Independen dulu, baru cek silang: tulis oracle + skenario + hash sebelum melihat hasil writer/auditor lain. Label: INDEPENDENT_NATIVE_RERUN / INDEPENDENT_SOURCE_REVIEW /
  REUSED_WRITER_EVIDENCE / REUSED_GPT_LOG_READ / OWNER_CONFIRMED_TO_AUDITOR.

## 1. Bacaan wajib, urut
1. `AUDIT_WRITER_HANDOFF_CP6.md` (register tertutup + tugas writer), lalu `WRITER_HANDOFF_R12_PASTE_20260925.md` (keadaan terakhir).
2. `out/fable_r12_results.md` (pra-BC F1–F4 + putaran 12 BC) dan `out/gpt_bc_20260926_initial_review.md`; `audit/CP6_COMBINED_INDEX.json` kunci `fable_round12_bc`.
3. Writer: `docs/cp6-au-r1-handoff.md` §30–§31, `docs/cp6-bc-case-table.md`, `docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25*.md`.
4. Oracle pra-kode: `out/fable_c6_75_oracles_pre_code.md`, `out/fable_all22_oracles_pre_code.md`, `out/r9_acc_oracle.md`, `out/r9_all_oracle.md`.

## 2. Alat (semua di repo)
- Runtime: `cp6-auditor-scenario.yml` (input `scenario_b64`/`browser_b64` atau `scenario_path`/`browser_path`; fase `after`=dengan BC, `pre_bc`, `pre_bb`, `pre_ba`, `before`),
  `cp6-t2-regression.yml`, `cp6-t3-release-package.yml`, `cp6-t3-rollback.yml`, `cp6-candidate-codeql.yml`, `cp6-bc-t1-probe.yml` — dispatch ref = cabang writer.
- Workflow pinned milik auditor di cabang audit: `.github/workflows/fable-cp6-bc-t1.yml` (pin `ref:` + assert ke head alat; ganti hash bila head baru; trigger = push berkas itu).
- Skrip bantu (salinan di `audit/runs_fable/r12/`): `pin_head.sh` (cek identitas produk sebelum pin), `list_runs.py`, ledger dispatch `dispatch_ledger_snapshot.jsonl`.
- Kontrak skenario: `cases(cur,today)` → list `(id, callable)`; status hanya PASS/FAIL/COUNTEREXAMPLE/INCOMPLETE; `races(tools,today)`, `http_cases(http,today)`; browser ES module `cases(ui,today)`.
  Hanya FAIL/INCOMPLETE membuat job merah.

## 3. Keadaan saat serah terima (25 Sep 19:50Z)
- Head writer: `caeff6f` (BC produk = `27e1a05`; BD baru dimulai: `supabase/dev/cp6_bd_t1_family.sql`, belum final).
- BC: gate T2/T3(27)/rollback/CodeQL hijau (run auditor sendiri), regresi identik r11, probe PLAN 44/44 + 5 kasus Fable (run 36179524130), F1 fix terbukti,
  D09 browser writer hijau di 62d05c4 (seed mandor dinonaktifkan di salinan uji; F3 di produk **belum** diubah).
- Terbuka: D07 (alarm F2 disetel ulang ke tingkat dokumen — spesifikasi di paste R12 §2.1), F3 (guard UUID halaman nota), ACC-C12 key baru (pertanyaan kebijakan owner),
  `ACCESSORY_CONNECTED_ZERO` (disposisi EXPECTED_CHANGE ditulis; writer menambah kasus pengganti), BD/BE belum ada, uji gabungan 75+22 belum.
- Run terakhir Fable yang mungkin belum tercatat hasilnya: 36181745737 (6 race + 1 browser lintas tab Fable) — baca statusnya, catat apa adanya.

## 4. Yang diminta dari auditor baru
1. Jangan mengulang run yang sudah beku; verifikasi dengan **hash skenario + head** bila perlu, bukan run ulang tanpa alasan.
2. Untuk BD (LAU-05b, LAU-DEC01–06, W05 fisik): oracle pra-kode dari kontrak dulu (LAU di `out/fable_c6_75_oracles_pre_code.md`), skenario sendiri + hash, baru dispatch;
   probe writer dijalankan di workflow pinned milik auditor (salin pola `fable-cp6-bc-t1.yml`).
3. Cek silang GPT setelah fase sendiri; yang berbeda diuji sendiri; kompilasi ke handoff yang satu (tambah bagian, jangan tulis ulang).
4. Setiap fase: commit + push (fetch/merge dulu). CP6 tetap HOLD, `audit_complete=false`, `production_go=false` sampai semua family + gate + uji gabungan lulus.

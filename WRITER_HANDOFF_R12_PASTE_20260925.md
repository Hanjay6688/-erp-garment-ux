# Handoff auditor → writer, putaran 12 (pra-BC), 25 Sep 2026 ~17:45Z — TEMPEL KE WRITER
Dari: Fable (independen; GPT menyusul cek silang). Sumber: `audit/cp6-final-20260924-gpt-a0bcadf` → `out/fable_r12_results.md`, `audit/runs_fable/r12/`.

## 1. Dua temuan "pre-existing" di commit 7c9d00a sudah direproduksi independen sebelum BC (run 36168041413, fase `pre_bc`, head 95353aa)
- **F1 CONFIRMED.** Nota mandor harga manual (fasad AP, mode MANUAL, 3.00) → `contractor_issue_price_provenance_gap` +1 CRITICAL. Predikat baseline tidak mengenal
  `manual_retail_unit_price`; M:1066 ACC-DEC02 membuat harga manual sah. Perbaikanmu di BC (tambah `and manual_retail_unit_price is null` pada cabang ACCESSORY) konsisten
  kontrak. Minta: di handoff BC sertakan diff badan fungsi v265 baseline→BC (hanya predikat itu yang berubah).
- **F2 CONFIRMED sebagai cacat detektor, bukan buku.** `MATERIAL_RECOST_GL_STATE_DRIFT` (v2.5.5, ERROR) menyala pada (a) penyesuaian + invoice terlambat: gerakan
  penyesuaian tidak punya baris `material_cost_revaluation_state` (recost-nya ada di `material_adjustment_revaluation_facts` v2.6.20t, V2620T_* = 0), dan (b) n=10 nota
  bertumpuk: satu gerakan potong `applied −0.05` vs target per gerakan −0.01 (sen dokumen terkumpul di satu PO = T3-A). Buku memenuhi oracle di semua jalur
  (kewajiban per dokumen, WIP = jumlah nota dibulatkan, persediaan habis = 0, GL dalam 1 sen dari qty×rata2 saat rata2 pecahan sen).

## 2. Yang diminta dari writer (bukan cara perbaikan; itu wewenangmu + owner)
1. **Jangan kecualikan `STALE_F2` diam-diam.** Di handoff BC tulis F2 sebagai temuan terbuka pre-existing dengan disposisi yang diusulkan ke owner:
   selaraskan/pensiunkan aturan "≤ 0,01 per gerakan" v2.5.5 yang bertentangan dengan T3-A (CR kecil), atau catatan owner bahwa detektor itu tidak berlaku lagi.
   Sampai ada disposisi, tiap kasus BC yang recost tetap mengunci `books = subledger` **dan** `V2620T_MATERIAL_ADJUSTMENT_* = 0`.
2. Sebutkan dampak: `run_v255_…` tidak dipanggil UI dan tidak digate T2/T3 → dampak pada pemeriksaan operator/probe, bukan laporan pengguna. Kalau ada halaman
   "cek data" yang memanggilnya, sebutkan.
3. **BC belum final bagi auditor** sampai ada: head final tertulis, tabel kasus (before/after, 32 + L-cases + 6 state ALL), run CI `cp6-bc-t1-probe.yml` hijau yang bisa
   saya baca, races/HTTP/browser BC di runtime auditor, dan paket T3 27 berkas + rollback BC. Setelah itu saya jalankan ulang regresi (xa1/2/7/8/9, open_1, C0), T2, T3,
   probe BC before/after di workflow pinned milik auditor, kasus BC saya sendiri dari `out/fable_c6_75_oracles_pre_code.md`.
4. Perubahan workflow auditor (fase `pre_bc`, `after` memasang BC) sudah saya baca; runner/modes B1 tidak berubah. Kalau runner/modes berubah lagi, sebut eksplisit.

## 3. Sudah dicek OK
D06/T3 tercatat verbatim (ab4ea6d). Probe enam state ALL era BA ada (4b1bd66) — diuji di CI BC. Paket rilis DB identik 4c61aca..95353aa.

# Fable — putaran 11: head BB final `4c61acad2270e11a2aca762237790a68cf36278a` (writer §30) — 2026-09-25T16:05Z

Label: INDEPENDENT_NATIVE_RERUN / INDEPENDENT_SOURCE_REVIEW / REUSED_WRITER_EVIDENCE. Oracle: M/P/BR + C0 1–8; oracle pra-kode ALL/C6 (Fable + GPT). Semua run di-dispatch Fable lewat API pada ref writer (run_identity `tool_head 4c61aca`, `product_ref 797fadd`). Diff d1bc8ad..4c61aca: 44 berkas, migrasi `…20bb_cp6_open_cutover_states.sql` (+6.498), `cp6_ba_t1_family.sql` +12 (T4), paket T3 26 berkas.

## 1. Regresi BA (BA berubah untuk T4) — tidak ada yang mundur

| Skenario (sha) | Run / job | Hasil 4c61aca | d1bc8ad |
|---|---|---|---|
| xaudit_1_rev2 dad4331b | 36154100359 / 108134310851 | 4/4 PASS | 4/4 |
| xaudit_2_rev2 06e6149c | 36154113308 / 108134351941 | 5/5 PASS | 5/5 |
| xaudit_7 e21d9d0c | 36154126699 / 108134396128 | 12/12 PASS | 12/12 |
| open_1 983a66f5 | 36154440755 / 108135446365 | 13/13 PASS | 13/13 |
| xaudit_9 0b1a4bf2 | 36154153444 / 108134485104 | 3/3 PASS | 3/3 |
| xaudit_8 rev3 97f95e6a | 36154139979 / 108134440642 | 10 PASS + 2 COUNTEREXAMPLE beku (3 penerimaan bertumpuk, per-PO ±1 sen — sama persis: 10,02/10,00/10,01 dan 9,99/10,01/10,00) | sama |
| gpt_c0_oracles 7c2c19b6 | 36154165566 / 108134523072 | 24 PASS + 1 INCOMPLETE transport (ADJUSTMENT_DATE, grant) | sama |

## 2. T4 dokumen pembelian multi-bahan — bukti Fable sendiri
`xaudit_8.py` rev4 3fddec0a, run 36154303619 / 108134987726: `T4_MULTI_MATERIAL_DOC_INVOICE_UP` **PASS** (dokumen 2×10,005 → WIP 20,01 = pembulatan per dokumen M:835, bukan 20,02 per baris; kedua bahan qty 0 nilai 0; per PO 10,01 / 10,00), `T4_MULTI_MATERIAL_DOC_DIRECT_DOWN` **PASS** (2×10,004 → 20,01; per PO 10,01 / 10,00). → **T4 CONFIRMED** (perbaikan 4cd2171 benar). Catatan: sen dokumen jatuh ke satu bahan (id terkecil) — konsisten dengan aturan BA W8; total dan stok nol benar.

## 3. Alat: T2 / T3 / rollback dengan BB
| Workflow | Run | Hasil |
|---|---|---|
| T2 | 36154060877 (3 job success) | `T2_IDENTITY` holds 12/12 identik, DISPOSITION_REQUIRED by design; BUSINESS 179+39+12, IMPORTS 31, VALUES 65, NEW_CASES 25/8/1 beku, APPROVED 8 MATCH, CALENDAR 12 CE beku, AO 8+4, APPROVED_B 5, `T2_C0_ORACLE` 25/25; `auditor_head 4c61aca`, primary_unchanged |
| T3 paket 26 berkas | 36154073882 (install 108134224181, pins 108134224487, browser 108134258500 — semua success) | AC..BB 26/26 PASS; verify stage `AV_PLUS_AW_AX_AY_AZ_BA_BB_T1` (ba sha 3359a42f…, bb sha a4232686…); gate {installed, primary_unchanged, backup_restore_drill, security_advisors} true; advisor 73 → 148 (**+75 INFO `rls_enabled_no_policy`**, termasuk 19 tabel `bb_*` dan capsule BB — cocok dengan catatan T5 writer); drill RESTORED_SAME_MEANING (19 error pg_cron dijelaskan, 339 tabel / 1.691 baris identik); UUID CLEAN 855 kolom; alias CASH_BANK NONE |
| Rollback AC..BB | 36154086810 / 108134265265 | cycle **131/131 PASS**, primary_unchanged |

## 4. BB pada head final
| Uji | Run / job | Hasil Fable |
|---|---|---|
| Race/HTTP/browser BB (skenario writer `scripts/cp6_bb_modes.py` + `cp6_bb_browser.mjs`, dijalankan di runtime auditor oleh Fable) | 36154245241 / 108134790206 | **races 8/8, HTTP 3/3, browser 3/3 PASS**, RUN_COMPLETE, tool_head 4c61aca → klaim writer 14/14 CONFIRMED |
| Probe BB before/after (PLAN writer 52 + 5 kasus Fable, workflow Fable rev3) | 36154186985 / before 108134588705, after 108134589189 | **after 57/57 PASS** (52 writer + `FAB:S01_OPENING_AR_DIRECTION`, `FAB:P02_SETTLE_EXACT_THEN_CENT`, `FAB:S01_TWO_PARTIALS_REVERSE_FIRST`, `FAB:OSS_BALANCE_OF_OTHER_BATCH_REFUSED`, `FAB:P03_NO_DUPLICATE_OBLIGATION` rev3); **before 52 NO_ROUTE + 2 COUNTEREXAMPLE + 3 PASS**, expectation_mismatch {}. Status job INCOMPLETE hanya karena workflow Fable belum `npm ci` untuk parser halaman writer (`cp6_bb_workspace_parse.mjs` butuh esbuild) — cacat workflow auditor; run ulang 36155406049 (§6) |

## 5. Review teks
- **T1 lampiran C6 rev4 (b7833e0): CONFIRMED** — keenam koreksi ada (sitasi M:1678/4139–4143/4454–4479, M:1757 hanya acceptance; ACC-04b vs LAU-06b dipisah dengan pagar identitas M:3094/M:3735; "D06" = pengesahan lampiran, bukan ACC-DEC06/Auth D06; PENDING_POLICY_VALUE; LAU-04 terbuka; W05 PARTIAL; butir CP7 M:1694/1697). **Siap ditandatangani owner (D06).**
- **T3 penjelasan sen per PO (docs/cp6-t3-cent-per-po-and-t5-advisor-note.md): CONFIRMED konsisten** dengan bacaan sumber Fable (`sync_material_cost_revaluation`: nilai pemakaian = selisih nilai stok dibulatkan; selisih sen dokumen dibawa ke pemakaian berikutnya); deterministik (dua isi BA memberi hasil sama). Pertanyaan owner: **A** (tetap, rata-rata bergerak, HPP per PO boleh meleset ≤1 sen per dokumen pada stok campuran) atau **B** (tolak; butuh CR penilaian per roll). Default A. Tidak menghambat gate.
- **T5 catatan advisor: CONFIRMED** dari log Fable (+75 INFO, semua `rls_enabled_no_policy` erp).
- **Tabel kasus BB (docs/cp6-bb-case-table.md):** 52 kasus → 13 keadaan ALL (P02, P03, P04, S01, S02, S03, A03, Y01, Y02, W02, W04, W06, W05-finansial) → oracle F/G. S02 dibangun di BB (tak ada di family mana pun); bacaan GPT (reservasi dibawa) dipakai karena lebih fail-closed — Fable setuju.

## 6. Kesimpulan BB (sementara, menunggu run ulang parser)
- **BB family pada 4c61aca: T1 (57/57), race/HTTP/browser (14/14), T2 identik, paket T3 26 berkas, rollback 131/131 — semua CONFIRMED natively oleh Fable.** GPT: BB round 10 pra-run (10 dokumen pool sen; dua draf reservasi bersama) berjalan — dicek silang setelah selesai.
- Keadaan ALL: 13 di BB + 6 dari era BA (P01, A01, A02, W01, W03, C01; inventaris writer, rute belum diverifikasi SQL oleh auditor) = 19/22 punya jalur; sisa C02, C03 (BC), W05 fisik (BD), C04 (BE).
- **CP6 tetap HOLD, audit_complete=false, production_go=false** — BC, BD, BE belum ada; D06 belum ditandatangani; nilai kebijakan pending.

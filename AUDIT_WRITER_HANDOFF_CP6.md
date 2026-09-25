# Handoff untuk WRITER — CP6, versi gabungan dua auditor (Fable + GPT), 25 September 2026 13:00 WIB

> **Blok tempel putaran 11 (16:10 WIB):** `WRITER_HANDOFF_R11_PASTE_20260925.md` — D06 disahkan owner, T3 = opsi A (perbaiki kalimat), BB tanpa cacat produk pada 4c61aca, catatan sebelum BC.

**Ini satu-satunya daftar tugas writer yang berlaku.** Dokumen ini merapikan semua handoff yang tumpang tindih (`WRITER_HANDOFF_R9_20260925.md`, `WRITER_HANDOFF_R10_20260925.md`, `WRITER_HANDOFF_R10_PASTE_20260925.md`, `out/gpt_writer_r9_intake.md`, tabel aktif putaran 8 GPT) menjadi satu versi yang disepakati kedua auditor. Riwayat lama utuh di `archive/AUDIT_WRITER_HANDOFF_CP6_r8_r9_history.md` dan di git. Hasil beku tidak dilabel ulang.

Head diaudit: BA `d1bc8ad` (alat = produk), BB `db9e276` (P04/Y02). Cabang kompetisi `ca7f095`. **CP6 HOLD · audit_complete=false · production_go=false.** Oracle: M/P/BR + addendum C0 bagian 1–8 (disahkan owner). Lampiran C6 **rev4 pada 4c61acad DISAHKAN owner sebagai D06** (langsung ke auditor, 25 Sep 2026 sore; teks di `OWNER_DECISIONS_CP6_DRAFT.md`), termasuk scope ACC-04b, LAU-05b, LAU-06b, ALL 22; `PENDING_POLICY_VALUE` tetap pending; pengesahan ≠ penerimaan uji. **T3 = opsi A** (rata-rata bergerak; tanpa batas tetap "1 sen per PO"; oracle wajib total/per tanggal/stok habis/jejak).

## 1. Tertutup — jangan diregresi (bukti kedua auditor, run masing-masing)

| ID | Apa | Bukti Fable | Bukti GPT |
|---|---|---|---|
| W2 | grup oracle C0 di T2 | T2 36121911881 `T2_C0_ORACLE` 25/25; retry native 25/25 | T2 36125151913 25/25 |
| W7 | grup ketat race/HTTP (ID ganda, status di luar kosakata, non-dict, exception, None, huruf kecil, tanpa kunci) | 36121901467, 36132001602 (9 bentuk) | 36122470639 (2 job negatif) |
| W8 | sen dua penerimaan (DIRECT/INVOICE × UP/DOWN) | xaudit_8 rev2 36123155393 4/4 | 36122470639 4/4 |
| W9 | `changed_since_filing` (C0 D01 3.4) + kontrol + adversarial d+1 | xaudit_9 36123165642 3/3 | 36122470639 2/2 |
| W10 | identitas permintaan Pola/Hak Akses (envelope UUID tetap, replay exact) | browser rev2 36130179246 2/2 | browser rev2 36124300108 2/2 |
| W11 | pesan asli parser vs jaringan | log GPT 108036762327 dibaca Fable + sumber `clientError.ts:71–96` | `G9UI:W11:PARSER_ERROR_VS_NETWORK` PASS |
| W13 | KPI "— belum diketahui" saat baca gagal; muat ulang → nilai nyata | Laundry rev5 2/2, QC rev6 2/2 | sama, run 36124300108 |
| LAU-T14 | tarif saat kirim (naik, turun, kontrol, **celah versi ditolak atomik**) | xaudit_8 rev2 4/4 | 2/2 |
| CP6-01 | WIB 12 kasus browser (Potongan, Bagi Potongan, BS × 4 zona) | 8 + pickup rev2 4/4 | 8 (pickup: locator) |
| C0 | 25 kasus uang/tanggal | 24 + retry 1 = 25/25 | 25/25 |
| HTTP | matriks argumen valid, revocation, helper prepare tak terjangkau | 3/3 (file GPT beku) | 3/3 |
| T2 / T3 / rollback | identik (holds 12/12) / 25 berkas, pins equal, drill RESTORED_SAME_MEANING, advisor gate true / cycle 127/127 | 36121911881 / 36121924229 / 36123219619 | 36125151913 / 36126474798 / 36126986327 |
| BB T1 | PLAN writer 34/34 PASS after; before 34 NO_ROUTE + 2 COUNTEREXAMPLE + kontrol | 36132268786, 36132808005 (db9e276) + 5 kasus Fable (4 PASS, P03 angka benar) | 36127700002 (72bf53f) 25/25 + S01 arah jurnal |
| Owner | D01–D05 sah; D03 §5.3 "boleh posting, dicatat unknown" (syarat tercatat); scope C6 §0 keempat poin | konfirmasi langsung ke Fable | teks lampiran diaudit GPT |

Cek auditor yang terbukti salah dan sudah diperbaiki (bukan tindakan writer): oracle HALF_EVEN (r8), locator `.pattern-error` setelah banner W10, locator `getByLabel('Mandor')`, cek jenis jurnal P03 "hanya OPENING_BALANCE" (`OPENING_UNINVOICED_RECEIPT` = jurnal kewajiban awal M:831, benar), wrapper KPI GPT rev1.

## 2. Tugas writer SEKARANG (urut prioritas; sebelum BC dibangun jauh)

| # | Tugas | Dasar | Bukti penutup yang diminta |
|---|---|---|---|
| T1 | **Revisi lampiran C6 → rev4** sebelum owner menandatangani D06: (a) sitasi "sesuai M:1757" untuk pengaturan kebijakan → "konsisten dengan M:1678, M:4139–4143, M:4454–4479" (M:1757 hanya kewajiban acceptance CR yang masuk CP6); (b) pisahkan §0 butir 1: konversi ganti merek + aksesori (M:3913, M:3925) vs celup ulang BS → SKU baru = **LAU-06b, scope tambahan dari mandat "semuanya"**, bukan desain di M; pagar: tarif/referensi SKU laundry tidak mengubah identitas produk, perubahan identitas hanya lewat command konversi sah dengan lineage/QC/HPP; (c) "D06" ditulis eksplisit = pengesahan lampiran (bukan ACC-DEC06/kasus Auth D06); (d) setiap nilai default kebijakan (ACC-DEC03/04/05/06, LAU-DEC01/03/05/06) = `PENDING_POLICY_VALUE` sampai owner melihat angkanya; default aman = tolak/pending, bukan nol/OTHER_INCOME/tarif karangan; (e) LAU-04: `post_sale_v2` tanpa cek harga laundry unknown tetap **terbuka** (M:1678/M:4475) — sale final yang bergantung nilai unknown diblok sampai ada aturan tertulis; (f) label W05 di BB = **PARTIAL** (hanya finansial) | GPT `out/r9_scope_contract.md` + Fable §5a | teks rev4 + diff |
| T2 | **Kirim head BB FINAL** + tabel kasus BB → ID keadaan ALL (P02, P03, P04, S01, S03, A03, Y01, Y02, W05-finansial) → oracle pra-kode yang dirujuk. Lengkapi untuk BB sebelum BC diklaim: race dua sesi pada satu balance pembukaan (dua pelunasan melebihi sisa; dua ALLOCATE_PAYROLL), HTTP Auth nyata + UI untuk OPENING_SETTLEMENT / PURCHASE_COMMITMENT / PAYROLL_ENTITLEMENT, T2 dengan BB, paket T3 berkas ke-26 + rollback BB (cycle + post-use). Pola sama untuk BC, BD, BE | M:5311 (dua sesi nyata), M:1757 | run T1/T2/T3/rollback/browser per family pada head exact |
| T3 | **DIPUTUSKAN owner: opsi A.** Tugas writer tersisa: perbaiki kalimat pertanyaan di `docs/cp6-t3-cent-per-po-and-t5-advisor-note.md` (hapus "paling banyak 1 sen per PO", tulis keputusan A + kewajiban uji: total, per tanggal, stok habis = 0, jejak sumber/penyesuaian; per roll = CR terpisah) dan catat D06 + T3 di addendum induk bagian 9. Latar: tiga penerimaan bertumpuk lalu dikoreksi bersamaan → WIP per PO 10,02 / 10,00 / 10,01 (total 30,03 dan bahan 0 benar); stok nol di antara penerimaan → 10,01 ×3 (PASS dua auditor). Jelaskan jejak `sync_material_cost_revaluation` (rata-rata bergerak + selisih sen dokumen ke pemakaian berikutnya, `cp6_ba_t1_family.sql:689–727`), konfirmasi deterministik, dan minta owner memutuskan apakah HPP per PO boleh meleset 1 sen dari dokumennya pada stok campuran. Kontrak: total & per tanggal (M:6632) dijamin; M:485 hanya pool kain kantong. **Bukan blocker gate** | Fable xaudit_8 rev2/rev3; GPT `out/gpt_r9_cent_origin_result.md` | penjelasan + keputusan owner tertulis; hasil beku tetap |
| T4 | Dokumen pembelian **multi-bahan** (sen dokumen ke material id terkecil, BA W8) belum diuji siapa pun — tambah probe BA/T2 | W8 sumber | probe + run |
| T5 | Advisor T3: **+56 INFO `rls_enabled_no_policy`** pada tabel erp (25 capsule rollback, initial_import_*, pocket_*, po_hpp_*, laundry_rate_owner_estimates_v1, dll.) — fail-closed, bukan celah; catat sebagai disengaja di paket rilis | log T3 kedua auditor | catatan rilis |
| T6 | W12/W6 pada data nyata: drill T3 baseline sudah CLEAN (UUID 765 kolom) dan alias CASH_BANK NONE; **hosted/legacy belum diperiksa siapa pun** — jalankan `scripts/cp6_cutover_data_checks.py --pgurl <salinan drill>` pada salinan hosted yang diizinkan (baca saja), lampirkan hasil | batas auditor: tidak menyentuh hosted | keluaran drill |
| T7 | Opsional (tetap): W3 cabut grant `authenticated` pada `erp.prepare_migration_opening_balance` (successor); W5 pesan STALE_VERSION | — | — |

## 2a. Tambahan putaran 12 (pra-BC, 25 Sep 17:45Z) — lihat `WRITER_HANDOFF_R12_PASTE_20260925.md`
- **F1 (pre-existing, CONFIRMED independen, run 36168041413):** nota harga manual (ACC-DEC02) ditandai CRITICAL oleh `contractor_issue_price_provenance_gap`. Diperbaiki di BC;
  verifikasi diff badan fungsi v265 di putaran BC.
- **F2 (pre-existing, CONFIRMED sebagai cacat detektor):** `MATERIAL_RECOST_GL_STATE_DRIFT` (v2.5.5) menyala pada buku yang memenuhi oracle (penyesuaian tanpa baris state;
  sen dokumen terkumpul di satu PO = T3-A). Butuh **disposisi tertulis** (CR kecil atau catatan owner), bukan pengecualian diam di probe. Kasus BC yang recost tetap mengunci
  books = subledger dan V2620T_* = 0.
- **F3 (pre-existing, CONFIRMED sumber):** guard UUID ketat halaman nota (`src/accessoryIssue.ts:20`) menolak ID sah non-RFC (seed CP3) → halaman kosong; menghalangi bukti
  browser ACC-D09. P3; perbaikan sempit disarankan (UUID kanonik), keputusan writer/owner.
- BC belum final bagi auditor (syarat di berkas paste §2.3). Writer sudah: paket T3 27 berkas (fe226cf), tabel kasus BC (d385e7e); pins T3 belum.

## 3. Oracle pra-kode untuk 75 C6 + 22 ALL (writer memakai keduanya; jangan menyesuaikan oracle ke kode)
- Fable: `out/fable_c6_75_oracles_pre_code.md`, `out/fable_all22_oracles_pre_code.md` (22: 8 ORACLE_READY murni + 3 bersyarat; 11 NEEDS_OWNER_INPUT: P03, P04, S02, S03, Y02, W04, W05, W06, C02, C03, C04).
- GPT: `out/r9_acc_oracle.md`, `out/r9_lau_oracle.md`, `out/r9_all_oracle.md` + `out/r9_all_oracle_errata.md` (S01: Dr AR / Cr OPENING_EQUITY).
- Bila kedua set berbeda: pakai bacaan yang lebih fail-closed sampai owner memutuskan. Hitungan 9 MAPPED / 6 PARTIAL / 7 NO_ADAPTER adalah inventaris writer, belum diverifikasi dari SQL oleh auditor mana pun.

## 4. Cara auditor memverifikasi ulang (tidak berubah)
Push head baru H (final per family) → auditor mencatat H, diff, rerun skenario terdampak lewat `cp6-auditor-scenario.yml` (`phase=after`) + workflow multi-file/BB milik auditor yang dipin ke H; T2/T3/rollback di-dispatch auditor. Hash skenario di `audit/scenarios/*/MANIFEST*.json`, `audit/scenarios/FABLE_SHA256SUMS`. Hasil per run di `audit/runs_fable/`, `out/gpt_r9_*.json`.

## 5. Batas kedua auditor
Baca saja; tidak ada push ke `claude/new-session-deapao`; tidak ada SQL ke hosted/legacy/produksi; tidak ada pesan ke pihak lain; skenario pihak lain dipakai ulang hanya sebagai berkas beku; hasil beku tidak dilabel ulang; MATCH/RUN_COMPLETE bukan penerimaan produk.

# Handoff writer Claude — kandidat CP6 putaran 8 (25 September 2026) — diteruskan owner ke auditor Fable (disimpan apa adanya)

STATUS
CP6 HOLD · audit_complete=false · production_go=false · 12 HOLD historis tetap HOLD.
Label bukti: T1_FAMILY / T2_REGRESSION / T3_PREP / AUDITOR_SCENARIO. Semuanya bukan bukti rilis dan bukan penerimaan independen.

IDENTITAS
- Repo Hanjay6688/-erp-garment-ux, cabang claude/new-session-deapao.
- Head: 9dd7bc2b9309d008e8a2e50d81876d831f3e5ea7.
- Produk acuan: a095a9d804d29643721e18635c2c3e26adcd56ea. Commit sesudahnya hanya alat auditor, gate CodeQL, dan dokumen/bukti.
- Setiap run mencetak run_identity (tool_head, product_ref).
- Cabang kompetisi ca7f09556397801c50a2277bdb65b1bf019f9a05 tidak ditulis. main 557005e tidak disentuh.
- Tidak ada SQL ke hosted. Cloudflare tidak diubah oleh writer.
- Sumber tugas: AUDIT_WRITER_HANDOFF_CP6.md (cabang audit/cp6-final-20260924-gpt-a0bcadf, 8d3ee4c).
- Rincian lengkap: docs/cp6-au-r1-handoff.md §28. Hasil CI, termasuk run merah yang disimpan, ada di §28.6.

PRODUK (BA v2.6.20ba, supabase/dev/cp6_ba_t1_family.sql; berkas paket rilis ke-25)
- A1: batch impor kedua dengan identitas item yang sama ditolak (BA_IMPORT_OPENING_ALREADY_POSTED). Sumber berbeda tetap boleh.
- A2: helper WIB di halaman potong, pickup, dan BS (frontend, 01c28e1).
- A3: COMPLETE WIP bertanggal sebelum pembalikan ditolak (BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING).
- A4: recost pemakaian dengan aturan sen utuh, jadi stok 0 bernilai 0. Retur supplier tetap memakai aturan AZ.
- A5: sumber BS yang masih bisa diklaim dan draf impor yang belum diposting tidak lagi terpotong 100/50. Kotak cari muncul di UI bila daftar lebih dari 20.
- A6: close ulang tanggal yang sama ditolak (CLOSE_ALREADY_CLOSED). Close sesudah reopen tetap boleh.
- A9 (D02): refund/apply uang muka melebihi kapasitas pada tanggalnya atau hari sesudahnya ditolak (BA_ADVANCE_DATED_CAPACITY). Aturan stok AUD-S04 sudah ditegakkan AO.
- A10 (D03): produk pada WIP awal mengikat output (BA_WIP_OUTPUT_PRODUCT_BOUND). Tanpa produk, merek/warna sumber harus cocok (BA_WIP_OUTPUT_SOURCE_MISMATCH). Dasar penetapan dicatat di erp.initial_import_wip_output_identity_v1; data yang tidak diketahui tidak dianggap cocok.
- A7 dan A8 (opsional, P3) tidak dikerjakan supaya produk yang diuji tidak berubah lagi. Bisa dikerjakan bila diminta.
- Regresi T2 dari BA ditemukan writer lalu diperbaiki (35612d6): CROSS:SUPPLIER_CENT:SPLIT_RETURN dan CROSS_SOURCE_INVERSE_IDENTITY. Oracle N tidak diubah.

ALAT (B1–B6)
- B1: grup ketat. ID ganda ditolak; status di luar kosakata jadi INCOMPLETE; lock atau sesi baru yang bocor jadi INCOMPLETE. Ada job self-test.
- B2: gate T3 mencakup terpasang, primary tidak berubah, drill backup/restore, dan advisor.
- B3: rollback AC..BA varian rilis, siklus penuh BA→AC→AB, dan matriks post-use untuk 25 keluarga.
- B4: mode browser (input browser_b64).
- B5: T2_FIXTURE_SUMMARY per fase.
- B6: run_identity.

DOKUMEN
- C0 docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25.md, sha256 e83d56e66812011c9a7a4057bf29987d0bcf62aabc17ad23ab422170abb00c99.
  - D01–D05 disahkan tertulis owner 25 Sep 2026, termasuk butir 3.4 dan 5.3. Kutipan apa adanya ada di bagian 9.
  - Teks yang disahkan adalah bagian 1–8 versi sha256 d39762da0520f30268a73244e7471b7d990138e3cbe36475d639c7cfca8e926d (5d54472). Yang berubah hanya baris status dan bagian 9.
  - D06 tetap OWNER_CONFIRMED_CHAT sampai lampiran C6 ditinjau.
- C6 draf lampiran …_LAMPIRAN_C6.md, sha256 72621c8a978573506b8c829a2a8790de948f6cb10e83ecd14dfddf35d495bc0d.
  - Isinya ACC-01..04 dan LAU-01..07, berlabel BASELINE atau CR-TUNDA.

BUKTI CI WRITER (disposable)
- BA T1 run 36090518293 (a095a9d): before 23 COUNTEREXAMPLE + 16 PASS sesuai rencana; after 39/39 PASS.
- T2 run 36089425974 (35612d6) dan 36089919596 (a4ad590): identitas per kasus sama dengan referensi tercatat (run 36011365657, 208afce).
  - 2 kasus SUPPLIER_CENT kembali PASS; 12 HOLD sama; oracle AS 8/8 MATCH.
- T3 package run 36090518284 (a095a9d): pin tereproduksi; 25 berkas terpasang; advisor baru hanya INFO rls_enabled_no_policy di erp; drill RESTORED_SAME_MEANING; primary tidak berubah; alur browser 10/10.
- T3 rollback: capture run 36089919551 (a4ad590); siklus run 36090518234 (a095a9d) 127/127 PASS.
- CodeQL run 36090824553 (d113bed): 0 hasil di keempat bahasa.
- Auditor Scenario run 36090909397 (4c379bf): keempat mode sampel RUN_COMPLETE, self-test SELFTEST_PASS.

BATAS YANG DIKETAHUI
- A4: bahan dengan beberapa penerimaan masih bisa menyisakan paling banyak 0,01 per penerimaan. Grup potong multi-bahan membagi sen per bahan. Retur supplier mengikuti cent state v2.6.20n.
- B3: transaksi post-use sama di setiap keluarga (saldo awal piutang 17,25). Deteksi post-use membandingkan semua data erp.

MOHON DIKERJAKAN AUDITOR
1. Rerun skenario yang terdampak pada head 9dd7bc2, phase = after. (A1: open_1.py, open_2.py, xaudit_5.py R1 + kasus positif sumber berbeda. A3: xaudit_1.py U02, SI-02 + kontrol tanggal ≥ pembalikan. A4: xaudit_1.py U03, xaudit_2.py invoice, MONEY×4. A5: xaudit_2.py selector-101, import_selector_fable_fix.py. A6: xaudit_5.py R2. A9: DATED_CAPACITY ×3 dan ORDERED_CONTROL ×3; AUD-S04/B04. A10: SI-01 + kontrol positif. B1: rt_probe_1.py, rt_probe_2.py.) Fase: after = AN + AU..AY + AZ + BA; pre_ba; before. Mode browser: browser_b64 (ES module cases(ui, today); ui.login(role,{label,mobile,timezoneId}), ui.anonPage(), ui.anonRpc(), ui.sql(), ui.expect; contoh scripts/cp6_auditor_browser_sample.mjs).
2. T2: CP6 T2 Combined Regression. T3: CP6 T3 Release Package dan CP6 T3 Rollback (mode auto memilih cycle).
3. Catat hash addendum yang disahkan dan cocokkan kutipan di bagian 9.
4. Tulis oracle baru untuk 25 kasus T2 dan CP6-07/CP6-18, karena addendum C0 sekarang sudah ada.
5. Cocokkan lampiran C6 baris per baris dengan M:1691–1699, M:1753–1757, dan M:4448–4479. Sesudah itu owner mengesahkan D06, dan GATE-16 bisa dinilai.
6. Tentukan apakah A7 dan A8 perlu dikerjakan.

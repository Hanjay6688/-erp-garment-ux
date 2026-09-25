> **DIGANTIKAN (25 Sep 2026 13:00):** versi gabungan dua auditor yang berlaku = `AUDIT_WRITER_HANDOFF_CP6.md`. Berkas ini dipertahankan sebagai riwayat.

# Auditor (Fable) → Writer, CP6 putaran 10 — 25 September 2026

Head yang diaudit: `d1bc8adff3ba1a2a7001ef39e4819d0c3813d00b`. Head writer terbaru yang terlihat: `fbafa51` (BB P03) — **belum diaudit Fable**. Vonis: CP6 HOLD, `audit_complete=false`, `production_go=false`.
Rincian: `out/fable_r9_results.md` (§0–§12), audit silang GPT: `out/fable_crossreview_gpt_r9.md`. Run JSON: `audit/runs_fable/r9/`.

## 1. Rerun putaran 9 — semua tertutup pada d1bc8ad (dua auditor konvergen)

| Item | Status | Bukti Fable |
|---|---|---|
| W2 grup oracle C0 di T2 | CLOSED | T2 36121911881 `T2_C0_ORACLE` 25/25; retry native 25/25 (36123210828) |
| W7 grup ketat race/HTTP | CLOSED | 36121901467: ID ganda ditolak sebelum operasi |
| W8 sen multi-penerimaan | CLOSED | xaudit_8 rev2 36123155393: 2 penerimaan 4/4 PASS (bahan 0, WIP 20,02/20,00, per PO tepat) |
| W9 `changed_since_filing` | CLOSED | xaudit_9 36123165642: 3/3 PASS (termasuk koreksi bertanggal d+1 tidak menandai d) |
| LAU-T14 | CLOSED | xaudit_8 rev2: tarif naik/turun/kontrol/celah versi 4/4 PASS |
| W10 identitas permintaan Pola/Role | CLOSED | browser rev2 36130179246: envelope sama, replay exact, satu baris |
| W11 pesan asli | CLOSED | sumber + log GPT 108036762327 (parser "ID Mandor bukan UUID valid." vs "Layanan UAT belum dapat dihubungi") |
| W13 KPI unknown | CLOSED | QC rev6 2/2, Laundry rev5 2/2 ("—, belum diketahui", muat ulang → nilai nyata) |
| CP6-01 WIB 12 kasus browser | CONFIRMED | cutting/bs 8 + pickup 4 (rev2) |
| T2 / T3 package / T3 rollback | identik / success / success (rerun setelah gagal infra port 54324) | §2, §9 |

## 2. Catatan baru (bukan blocker, mohon dijawab singkat)
- **W8-b (P3, NOTED):** tiga penerimaan @1 unit dikoreksi bersamaan → total WIP dan bahan benar, tetapi WIP per PO 10,02 / 10,00 / 10,01 (UP) dan 9,99 / 10,01 / 10,00 (DOWN). M:485 menerima pembagian sen deterministik, jadi bukan pelanggaran; konfirmasi bahwa urutannya deterministik dan dokumentasikan. Dokumen multi-bahan (sen dokumen ke material id terkecil) belum diuji siapa pun.
- **Advisor T3 (dari log GPT):** +56 INFO `rls_enabled_no_policy` di skema erp setelah paket. Fail-closed, bukan celah; catat di paket rilis bahwa itu disengaja.
- **Locator browser:** `getByLabel('Mandor',{exact:true})` di halaman Bagi Potongan tidak lagi cocok (nama aksesibel select memuat teks opsi). Bukan produk; skenario auditor sudah rev2.

## 3. Scope owner — SUDAH DIKONFIRMASI ke auditor
Owner menjawab langsung ke Fable: **"Ya, keempat poin benar"** (semua CR ACC-04b/LAU-05b/LAU-06b termasuk ganti SKU hasil BS di CP6; ALL = 22 keadaan; kebijakan M §14 sebagai pengaturan aplikasi dengan default aman; D06 disahkan setelah revisi). Status OWNER_CONFIRMED_TO_AUDITOR (`out/fable_r9_results.md` §5a, `OWNER_DECISIONS_CP6_DRAFT.md`).
Untuk revisi lampiran C6 (rev4) sebelum owner menandatangani D06, perbaiki teks (temuan audit teks GPT, disetujui Fable):
1. Sitasi "sesuai M:1757" untuk pengaturan kebijakan → ganti "konsisten dengan M:1678, M:4139–4143, M:4454–4479"; M:1757 hanya untuk kewajiban acceptance CR yang masuk CP6.
2. Pisahkan kalimat §0 butir 1: (a) konversi ganti merek + aksesori (didukung M:3913, M:3925); (b) celup ulang BS → SKU baru = LAU-06b, scope tambahan dari mandat "semuanya", bukan desain yang sudah ada di M. Tambahkan pagar: tarif/referensi SKU laundry tidak mengubah identitas produk; perubahan identitas hanya lewat command konversi yang sah dengan lineage/QC/HPP dibuktikan.
3. "D06" ditulis eksplisit sebagai pengesahan lampiran C6 (bukan ACC-DEC06 rounding atau kasus Auth D06).
4. Nilai default tiap kebijakan (ACC-DEC03/04/05/06, LAU-DEC01/03/05/06) tetap `PENDING_POLICY_VALUE` di laporan auditor sampai owner melihat angkanya tertulis; default aman = tolak/pending, bukan nol/OTHER_INCOME/tarif karangan.
5. LAU-04 `post_sale_v2` tanpa cek harga laundry unknown: tetap AUDITOR DECISION OPEN (M:1678/M:4475); sale final yang bergantung nilai laundry unknown harus diblok sampai ada aturan tertulis.

## 4. Oracle pra-kode (permintaan writer #3) — dua set independen tersedia
- Fable (agen, spot-check): `out/fable_c6_75_oracles_pre_code.md` (75 kasus), `out/fable_all22_oracles_pre_code.md` (22 keadaan: 8 ORACLE_READY murni + 3 bersyarat; 11 NEEDS_OWNER_INPUT: P03, P04, S02, S03, Y02, W04, W05, W06, C02, C03, C04).
- GPT: `out/r9_acc_oracle.md`, `out/r9_lau_oracle.md`, `out/r9_all_oracle.md` (+ errata S01: Dr AR 70 / Cr OPENING_EQUITY 70).
Writer memakai keduanya sebagai target; hasil PASS hanya dari run auditor pada head exact.

## 4a. Tambahan setelah uji sendiri Fable (12:10Z)
- W7: Fable menguji 9 bentuk keluaran tidak sah (status di luar kosakata, None, huruf kecil, tanpa kunci, non-dict, exception) di cases/races/HTTP — semua INCOMPLETE dengan nilai asli dicatat. W7 tertutup penuh.
- T3 rinci & rollback 127/127: dikonfirmasi dari log run Fable sendiri (bukan lagi klaim GPT).
- Sen per-PO: varian berurutan (stok nol di antara penerimaan) PASS per PO di run Fable dan GPT; selisih 1 sen hanya pada stok bertumpuk. Pertanyaan kecil untuk owner/writer (P3): apakah HPP per PO boleh meleset 1 sen dari dokumen bahannya saat beberapa penerimaan bertumpuk (rata-rata bergerak)? Kontrak hanya menjamin total & per tanggal.

## 5. Family BB (72bf53f → fbafa51 → db9e276)
- Writer probe BB di 72bf53f gagal alat (`dict() got multiple values for keyword argument 'case'`, `scripts/cp6_bb_probe.py:325`) — diperbaiki writer di fbafa51 (per pesan commit). GPT menjalankan versi independen pada 72bf53f: after 25/25 PASS, before 20 NO_ROUTE + 2 COUNTEREXAMPLE + 3 PASS (run 36127700002).
- **Temuan cakupan GPT (P2, disetujui Fable secara teks):** "BB plus ALL W05" terlalu luas — BB hanya menutup hutang vendor laundry (finansial); fisik 10 kirim/2 kembali/1 hilang, klaim, failed attempt, harga unknown belum ada. Labeli W05 PARTIAL sampai BD.
- **Fable sudah menjalankan ulang BB pada db9e276** (run 36132268786, rev2 36132808005): PLAN writer 34/34 PASS (after) dan 34 NO_ROUTE + 2 COUNTEREXAMPLE + kontrol (before) — cocok dengan klaim; 5 kasus Fable tambahan: 4 PASS (arah jurnal S01; pelunasan tepat lalu 0,01 ditolak; dua parsial reverse-pertama; balance batch lain ditolak) dan P03 tanpa kewajiban ganda — semua angka benar (inventory 22, GRNI 12, AP 7, equity 103, AP native 0, tanpa dokumen historis), FAIL beku hanya karena cek auditor "hanya OPENING_BALANCE" tidak mengizinkan jenis jurnal `OPENING_UNINVOICED_RECEIPT` (jurnal kewajiban awal M:831) — bukan cacat produk. Yang belum: race dua sesi pada satu balance, HTTP/UI, T2/T3/rollback BB, family BC–BE. Sisa putaran BB Fable: review sumber `cp6_bb_objects_financial.sql`/`_purchase.sql` + `cp6_bb_t1_family.sql` (≈4.100 baris), skenario sendiri per keadaan ALL yang diklaim (P02, P03, S01, S03, A03, Y01, W05-finansial) memakai oracle pra-kode §4, race dua sesi, T2/T3/rollback BB. Mohon: head BB **final** (bukan per commit) + tabel kasus BB dengan ID ALL yang diklaim, agar auditor tidak mengejar head yang bergerak.

## 6. Batas
Baca saja; tidak ada push ke cabang writer; tidak ada SQL ke hosted; tidak menyentuh main/competition/production/legacy. Skenario GPT dipakai ulang hanya sebagai file beku; hasil GPT dibaca setelah fase independen Fable selesai.

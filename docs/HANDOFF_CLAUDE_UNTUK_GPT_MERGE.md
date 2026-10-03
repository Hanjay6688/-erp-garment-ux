# Handoff Claude → GPT: seluruh pekerjaan Claude, aturan merge, dan daftar periksa audit

Dokumen ini adalah pintu masuk tunggal untuk GPT. Isinya mencakup semua perubahan buatan Claude di cabang `claude/new-session-deapao`, aturan yang harus dijaga saat menggabungkannya ke arsitektur GPT, dan daftar periksa audit. Rincian teknis tidak diulang; setiap baris menunjuk ke dokumen sumbernya.

**Urutan yang diminta owner: GPT mengaudit dulu, baru merge.** Kalau ada temuan, catat sebagai temuan dan kembalikan ke owner/Claude. Jangan "dibetulkan" dengan melonggarkan tes.

## 0. Identitas dan status

- Cabang: `claude/new-session-deapao`. Head saat dokumen ini dibuat: commit yang memuat dokumen ini. Commit kode Claude terakhir `dda66b9a`; bukti CI terakhirnya `cp7-receipt-correction` run 37083713960, 39/39 PASS.
- Commit buatan Claude di cabang ini: **279**, dari 23 Sep sampai 3 Okt 2026. Cara melihatnya: `git log origin/main..HEAD --author=Claude`.
- Status tetap: `production_go=false`, CP6 HOLD, `audit_complete=false`. Semua pekerjaan Claude berstatus **kandidat** dan belum diterima auditor independen.
- Tidak pernah dimutasi oleh Claude: `main`, deployment Cloudflare, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment (`vlxdhpkjeevubjxexnfo`), dan production.
  - Akses ke hosted hanya baca, tercatat di `docs/evidence/hosted_access_log_20260924.json`.
  - Cabang kompetisi `competition/cp6-j-closure-20260911` tetap `ca7f09556397801c50a2277bdb65b1bf019f9a05`; ini dicek sebelum setiap push.
- Label bukti: hanya run CI yang dihitung sebagai bukti. Hasil `LOCAL_PG16_DEV` hanya catatan kerja. Run yang gagal tetap tercatat FAIL di dokumen masing-masing.

## 1. Peta pekerjaan Claude

Kolom "Sesudahnya diubah GPT" penting untuk merge. Kalau GPT sudah merevisi suatu bagian, versi GPT terakhir yang berlaku, dan uraian Claude hanya menjelaskan keadaan sebelum revisi itu.

| Area | Isi singkat | Dokumen rinci | Bukti terakhir Claude | Sesudahnya diubah GPT |
|---|---|---|---|---|
| AU-R1 / AV (successor identitas) | Cutoff successor membaca semua fakta fisik NEW_STOCK; BS ditemukan sebelum successor tidak hilang | `docs/cp6-au-r1-handoff.md` §1–§16 | §16 (AV rev2, run 35853810855) | tidak |
| AUD-A04-R2 | Koleksi saldo awal yang tidak terbaca ditampilkan "tidak diketahui", bukan 0 | §10–§15, `docs/evidence/cp6-a04-r2/` | §15 | tidak |
| AW | Engine tutup buku per tanggal (AUD-S06, AUD-B04) | `docs/cp6-aw-design.md`, handoff §17, §20–§21 | §21 (T1 16 kasus + 8 race) | ya, rollback dibangun ulang 29 Sep |
| AX | Barang jadi tanpa sumber produksi; upah perbaikan BS → utang mandor via payroll | §20–§22 | §22 (T1 32 PASS) | ya, rollback 29 Sep |
| AY | Koreksi HPP PO bertanggal dari barangnya (rev2–rev7.4) | §22–§26, `docs/evidence/cp6-ay/` | §26 (rev7.4) | ya, rollback 29 Sep |
| AZ | Recost bahan bertanggal dari pergerakan; sisa WIP PO selesai ditutup; opsi 1 owner | §23–§27, `docs/evidence/cp6-az/` | §27 (AB-01 diperbaiki) | ya, rollback 29 Sep |
| G-01 | Baseline uji disamakan dengan katalog hosted, dari metadata yang dibaca saja | §20–§21 | §21 | tidak |
| H-01 / T2 | Runner regresi gabungan per ID kasus, disposisi kasus yang berubah, oracle AS yang disetujui owner | §21–§34, `docs/evidence/cp6-t2/` | §34.5 (run 36222388263) | ya, workflow T2 diubah 28 Sep |
| T3 + rollback | Paket rilis dengan pin dari capture, drill backup/restore, advisor gate, rollback AC..BD dan cycle | §22–§34, `docs/cp6-t3-cent-per-po-and-t5-advisor-note.md` | §34.5 (28 berkas, rollback 139/139) | **ya**: paket sekarang 30 berkas (+BE, BF), dipin ulang GPT 28–29 Sep |
| BA | Perbaikan audit independen A1–A10; putaran 9 W1–W13 | §28–§29 | T1 38/38 (commit `5d544729`), §29 | ya, rollback 29 Sep |
| BB | Saldo awal dan ALL tanpa CR: facade pelunasan saldo awal, P03, P04, Y02, W02, W04, W06, S02 | §30, `docs/cp6-bb-case-table.md` | §30 | ya, rollback 29 Sep |
| BC | Aksesori: pos servis, pemakaian, kembali, terima + inspeksi, custody, kredit nota; ACC-DEC sebagai pengaturan | §31–§34, `docs/cp6-bc-case-table.md` | §34.5 (probe 45/45, browser 5/5) | ya, `src/ConnectedAccessoryServicePage.tsx` 1 Okt |
| BD | Laundry: harga kiriman, invoice vendor, klaim, LAU-DEC01–06, D07–D12, keputusan owner no. 4/6/11/13 | §32–§34.9, `docs/cp6-bd-case-table.md`, `docs/cp6-d11-kebijakan-dan-gbd03.md` | §34.9 (probe 35/35, browser 8/8) | **ya, besar**: revisi uang BD, rentang SKU, dan BF (dokumen `docs/cp6-bd-*-20260928.md`, `docs/cp6-bf-*`) |
| Kontrak owner | Addendum C0 D01–D06 dan lampiran C6 rev4 dengan crosswalk 75 ID; D07–D12 belum masuk addendum, tercatat di handoff §32–§34 dan dokumen D11 | `docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25*.md` | §29–§31 | tidak |
| Runtime auditor | Workflow skenario auditor (race dua sesi, HTTP Auth nyata, browser) | §27–§31 | §31 | ya, 27 Sep |
| UI WIB | Halaman potong, pickup, dan BS mengirim waktu fisik sebagai jam dinding WIB (A2/CP6-01) | §28 | §28 | tidak |
| **CP7: Benerin penerimaan** | Koreksi penerimaan bahan/aksesori yang sudah diposting dan dipakai (jumlah, roll, nomor roll, harga, salah bahan, invoice supplier termasuk gabungan, nomor/tanggal invoice, surat jalan, tanggal datang, gudang, supplier, kelebihan bayar "retur bayangan", uang muka saldo awal, periode tertutup) | `docs/cp7/RECEIPT_CORRECTION.md` (termasuk bagian "Serah terima untuk merge") | run 37083713960, **39/39 PASS** | tidak |
| **CP7: Benerin nama / kode bahan** | Nama dan SKU bahan yang sama; identitas lain diperiksa tidak berubah | sama | sama | tidak |
| **CP7: Kartu Mutasi v2** | `erp_cp7_get_material_ledger_v2`: baris penerimaan yang dibetulkan tampil sebagai jumlah efektif | sama | sama | tidak |

BE (pocket/celup/konversi) dikerjakan GPT atas arahan owner. Claude tidak menyentuh BE.

## 2. Aturan merge

1. **Satu aturan bisnis, satu sumber.**
   - Untuk setiap aturan di §3, cek apakah arsitektur GPT punya versi sendiri. Kalau ya, pilih satu sumber, arahkan pemakai lain ke sana, lalu hapus duplikatnya.
   - Dua aturan berbeda untuk hal yang sama dilarang. Kalau keduanya bertentangan, jangan pilih sendiri: bawa ke owner.
2. **Definisi Native tidak diubah.**
   - Pekerjaan CP6 Claude berupa keluarga rilis berlapis AC..BD di `supabase/release/cp6-t3/`. Urutan lapisannya diatur `scripts/cp6_layers.py` dan `MANIFEST.json`.
   - Pekerjaan CP7 Claude berupa skema privat (`cp7_receipt_fix`) dengan wrapper publik.
   - Kalau GPT menyatukan lapisan, urutan keluarga dan "substitusi terperiksa" yang tercatat per berkas di `MANIFEST.json` (kolom `substitutions`) harus tetap sama hasilnya.
3. **Kebijakan owner berupa pengaturan di aplikasi** dengan nilai awal `PENDING_POLICY_VALUE`. Jangan mengisi angka sendiri.
4. **Oracle tidak boleh dilonggarkan.** Expected tidak boleh diubah supaya hijau, fixture yang salah disimpan, dan run gagal tetap FAIL. Pengecualian hanya dengan izin tertulis owner, seperti LAU-T36 di §34.9.
5. **Batas yang dilindungi** (lihat §0) dan tanpa SQL ke hosted.
6. **Waktu.** Tanggal bisnis memakai WIB lewat `erp._cp3_business_date`. UI mengirim jam dinding WIB (helper `src/cp6BusinessTime.ts`).
7. **Tidak diketahui tidak sama dengan nol.** Nilai yang tidak terbaca ditampilkan "belum diketahui" (AUD-A04-R2, W13).
8. **Urutan kunci** mengikuti writer Native: periode, lalu bahan (urut id), lalu dokumen.
9. **Pola koreksi dokumen** dipakai bersama oleh pembetulan penerimaan (Claude) dan koreksi nota penjualan (GPT, `cp7_note`):
   - sumber immutable;
   - pembalik Native pada waktu sumber;
   - pengganti yang persis;
   - lineage privat;
   - jurnal pembalik dipindah ke tanggal ekonomi asal.

   Kalau digabung menjadi helper umum, perilaku keduanya harus tetap lolos tes masing-masing.
10. **Envelope pemulihan.** Semua penulisan UI lewat `useProductionMutation` dengan UUID permintaan yang tetap dan reconcile. Domain baru didaftarkan di `src/productionRecovery.ts`.
11. **Kepemilikan RPC.** Setiap RPC browser baru didaftarkan di `scripts/check-source-ownership.mjs` dan `scripts/check-access-catalog.mjs`.
12. **Penulisan di luar writer Native harus terdaftar.** Daftar untuk CP7 ada di `docs/cp7/RECEIPT_CORRECTION.md`, bagian serah terima, butir 4. Kalau GPT menambah guard pada kolom-kolom itu, perintah terkait harus dikecualikan secara eksplisit, bukan diam-diam rusak.

## 3. Aturan bisnis yang harus punya satu sumber kebenaran

| Aturan | Tempat sekarang (Claude) | Kemungkinan bertemu milik GPT |
|---|---|---|
| Penomoran revisi: penerimaan `· R<n>-<8hex>`, invoice supplier `· R<n>` dengan akhiran kosong berikutnya | `correction.sql` | penomoran revisi `cp7_note` |
| Putar ulang pembayaran supplier (tanggal, kas, metode asli; uang muka saldo awal ke uang muka yang sama) | `cp7_receipt_fix.replay_payment` | pola `cp7_note` (sumber asli polanya) |
| Kelebihan bayar = "retur bayangan" ke nota lain supplier yang sama (keputusan owner 2 Okt) | `correction.sql` | kredit supplier `bf_supplier_credit_moves_v1` (BF) dan kredit klaim laundry D12 (BD). Ketiganya mekanisme berbeda, jangan dicampur tanpa owner |
| Tanggal datang tidak boleh sesudah pemakaian pertama; gudang hanya bisa diganti bila barang belum dipakai; supplier tidak bisa diganti untuk invoice gabungan atau pembayaran dari uang muka | `correction.sql` | aturan tanggal/lokasi di keluarga AW/AZ/BA |
| Batas bawah koreksi = pemakaian roll / saldo terendah di gudang | `roll_use`, `location_floor`, `shifted_floor` | pemeriksaan stok negatif Native/AM |
| Nomor roll unik per bahan; nama dan kode bahan unik tanpa membedakan huruf besar/kecil | `correction.sql`, `material-name.sql` | master bahan GPT |
| Pesan penolakan berbahasa Indonesia | `src/receiptCorrectionContract.ts` (`correctionRefusal`) | `src/lib/clientError.ts` (GPT) |
| Kartu mutasi: baris koreksi digabung ke baris asal kecuali tanggal/gudang berubah | `cp7_receipt_fix.ledger` (v2) | kartu v1 dan reader stok GPT |
| Recost/HPP bertanggal dari barang dan pergerakan | keluarga AY, AZ | perubahan GPT sesudah 28 Sep (BD/BE/BF) |
| Tutup buku per tanggal | keluarga AW | pembukaan/penutupan periode CP7 GPT (`cp7_period_*`) |

## 4. File bersama yang disentuh Claude

- **CP7 (dari `1baa7ce9` sampai `dda66b9a`):**
  - `src/ConnectedProcurementPage.tsx`
  - `src/ConnectedMaterialsPage.tsx` (+ dom test)
  - `src/productionRecovery.ts` (domain `RECEIPT_CORRECTION`, `MATERIAL_NAME`)
  - `src/types/database.preconnect.ts`
  - `scripts/check-source-ownership.mjs`, `scripts/check-access-catalog.mjs`
- **CP6:** `src/productionRecovery.ts` (aksi LAUNDRY_BD/BC), halaman impor saldo awal, halaman laundry dan aksesori, serta berkas paket/rollback T3. GPT kemudian mengubah sebagian (lihat §1).
- **Tidak disentuh Claude:** BE, F03–F05, nota penjualan (`cp7_note`), dan berkas GPT lain yang sedang ditulis.

## 5. Daftar periksa audit untuk GPT (sebelum merge)

Jalankan di head cabang ini. Hasilnya dicatat apa adanya.

1. **CP7 pembetulan penerimaan:** workflow `cp7-receipt-correction` (`.github/workflows/cp7-receipt-correction.yml`).
   - Harapan: 39/39 (33 native, 3 race, 1 HTTP, 2 browser), `cp6_restored=true`, advisor gate lolos.
   - Manifest: `scripts/cp7_receipt_correction_manifest.json`.
   - Periksa juga lima hal ini:
     - definisi Native tidak berubah (`native_writers_unchanged` di probe);
     - fungsi privat tidak bisa dipanggil (`scripts/cp7_receipt_correction_verify.py`);
     - pengujian tanggal di kasus tidak bergantung jam (lihat run 37048755577 yang FAIL karena jam);
     - semua run FAIL tercatat di `docs/cp7/RECEIPT_CORRECTION.md` "Bukti CI";
     - temuan GPT di bagian "Temuan untuk GPT" (anchor baris SALE pengganti di koreksi nota) direproduksi di harness nota.
2. **CP6 keluarga AW..BD:**
   - probe T1 per keluarga (`cp6-aw/ax/ay/az/ba/bb/bc/bd-t1-probe`);
   - T2 gabungan (`cp6-t2-regression`);
   - paket T3 (`cp6-t3-release-package`, `cp6-t3-aligned-install`) dan rollback cycle (`cp6-t3-rollback`);
   - CodeQL (`cp6-candidate-codeql`);
   - runtime auditor (`cp6-auditor-scenario`).

   Karena GPT mengubah BD/T2/T3/rollback sesudah 26 Sep, bukti Claude di §34 tidak lagi mewakili head ini. **Jalankan ulang di head sekarang**, lalu bandingkan dengan disposisi T2 yang tercatat.
3. **Frontend:** `npm run check:source`, `check:access`, `check:css`, `check:cp5`; `npx tsc --noEmit`; `npx vitest run`.
   - Diketahui gagal dan bukan dari Claude: `tests/cp7/families/cutting-learning.test.ts`.
   - Tes F04/F05 butuh PostgreSQL native non-root.
   - Spec Playwright di `tests/browser/` bukan untuk vitest.
4. **Ketidakcocokan antar aturan:** untuk setiap baris di §3, tulis keputusannya ("pakai versi Claude", "pakai versi GPT", atau "ke owner") sebelum merge.

## 6. Yang masih terbuka

- **Owner:**
  - nilai pengaturan BD/BC yang tersisa (no. 1, 2, 3, 5, 7, 8, 9, 10; lihat `docs/cp6-d11-kebijakan-dan-gbd03.md`);
  - inventaris ID cutover;
  - UI-01 (tampilan halaman BC/BD).
- **Batas produk yang diketahui:**
  - piutang ke vendor laundry belum punya alur;
  - LAU-DEC04 belum diuji di browser;
  - pembetulan penerimaan tidak menangani pemakaian non-potong pada salah bahan (jalan keluar yang disetujui owner: batalkan, betulkan, catat ulang);
  - kredit kelebihan bayar butuh nota tujuan yang sudah ada.
- **Auditor:**
  - verifikasi D07–D12, keputusan owner no. 4/6/11/13, dan substitusi cek `V2620C_WIP_SOURCE_CONSERVATION_MISMATCH` (§34.8);
  - seluruh CP7 pembetulan penerimaan.

## 7. Indeks dokumen Claude

- CP6: `docs/cp6-au-r1-handoff.md` (§1–§34.9), `docs/cp6-aw-design.md`, `docs/cp6-bb-case-table.md`, `docs/cp6-bc-case-table.md`, `docs/cp6-bd-case-table.md`, `docs/cp6-d11-kebijakan-dan-gbd03.md`, `docs/cp6-t3-cent-per-po-and-t5-advisor-note.md`, `docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25.md` (+ `_LAMPIRAN_C6.md`), `docs/evidence/cp6-*`.
- CP7: `docs/cp7/RECEIPT_CORRECTION.md`, tambahan Claude di `docs/cp7/TRANSACTION_CORRECTION_COVERAGE.md`.
- Dokumen ini: `docs/HANDOFF_CLAUDE_UNTUK_GPT_MERGE.md`.

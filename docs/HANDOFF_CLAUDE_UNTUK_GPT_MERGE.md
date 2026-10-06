# Handoff Claude → GPT: seluruh pekerjaan Claude, aturan merge, dan daftar periksa audit

Dokumen ini adalah pintu masuk tunggal untuk GPT. Isinya mencakup semua perubahan buatan Claude di cabang `claude/new-session-deapao`, aturan yang harus dijaga saat menggabungkannya ke arsitektur GPT, dan daftar periksa audit. Rincian teknis tidak diulang; setiap baris menunjuk ke dokumen sumbernya.

**Urutan yang diminta owner: GPT mengaudit dulu, baru merge.** Kalau ada temuan, catat sebagai temuan dan kembalikan ke owner/Claude. Jangan "dibetulkan" dengan melonggarkan tes.

**Mulai dari §8.** Per 3 Okt 2026, cabang ini sudah digabung dengan `cp7/integration` (`40c4127c`) dan semua konflik sudah diselesaikan di cabang ini. Atas instruksi owner 3 Okt ("serahin file lu, gpt tinggal cek sendiri pas di merge"), GPT tinggal mengaudit selisih `origin/cp7/integration..origin/claude/new-session-deapao`.

## 0. Identitas dan status

- Cabang: `claude/new-session-deapao`. Sejak 3 Okt sudah memuat `cp7/integration` `40c4127c` (merge `eabfec75`). Commit kode Claude terakhir `19ff70ee`; bukti CI-nya ada di §8.2 dan §8.5. Bukti sebelum merge: `cp7-receipt-correction` run 37083713960 (39/39 PASS di `dda66b9a`).
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
| **CP7: Benerin penerimaan** | Koreksi penerimaan bahan/aksesori yang sudah diposting dan dipakai (jumlah, roll, nomor roll, harga, salah bahan, invoice supplier termasuk gabungan dan invoice FINAL setahun lalu, nomor/tanggal invoice, surat jalan, tanggal datang, gudang, supplier, kelebihan bayar "retur bayangan", uang muka saldo awal, periode tertutup, baris ganda, draft yang memakai roll) | `docs/cp7/RECEIPT_CORRECTION.md` (termasuk bagian "Serah terima untuk merge") | lihat §8 | **ya**: GPT memasukkan versi `08d19674` ke `cp7/integration` (`77307d55`) dengan 5 edit kecil; sudah digabung balik (§8) |
| **CP7: Benerin nama / kode bahan** | Nama dan SKU bahan yang sama; identitas lain diperiksa tidak berubah | sama | sama | ya, sama dengan baris di atas |
| **CP7: Kartu Mutasi v2** | `erp_cp7_get_material_ledger_v2`: baris penerimaan yang dibetulkan tampil sebagai jumlah efektif | sama | sama | ya, sama dengan baris di atas |

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
| Pesan penolakan berbahasa Indonesia | **sudah satu jalur**: `normalizeClientError` (`src/lib/clientError.ts`, GPT) → `src/lib/receiptCorrectionMessages.ts` | — |
| Pelaku di riwayat koreksi: UUID tetap + nama profil saat ini | `actor_id`/`actor_display_name`/`actor_name_basis` di kedua riwayat Claude | **sama** dengan `cp7_note.workspace_with_actors` |
| Draft terkait memblokir koreksi dan disebut nomornya | `cp7_receipt_fix.blockers` (`documents`) | `cp7_note_pending_child_review_required` (GPT) |
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
   - Harapan: 42/42 (36 native, 3 race, 1 HTTP, 2 browser), `cp6_restored=true`, advisor gate lolos.
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
   - Di mesin tanpa PostgreSQL native non-root dan browser Playwright, 16 file / 27 baris tes gagal **sama persis** di `cp7/integration` murni dan di hasil merge (keluarga DB CP7, spec Playwright). Itu soal lingkungan, bukan merge.
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
  - seluruh CP7 pembetulan penerimaan, termasuk hasil merge dan perbaikan di §8.
- **GPT:** temuan dan dokumen basi di §8.4.

## 7. Indeks dokumen Claude

- CP6: `docs/cp6-au-r1-handoff.md` (§1–§34.9), `docs/cp6-aw-design.md`, `docs/cp6-bb-case-table.md`, `docs/cp6-bc-case-table.md`, `docs/cp6-bd-case-table.md`, `docs/cp6-d11-kebijakan-dan-gbd03.md`, `docs/cp6-t3-cent-per-po-and-t5-advisor-note.md`, `docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25.md` (+ `_LAMPIRAN_C6.md`), `docs/evidence/cp6-*`.
- CP7: `docs/cp7/RECEIPT_CORRECTION.md`, tambahan Claude di `docs/cp7/TRANSACTION_CORRECTION_COVERAGE.md`.
- Dokumen ini: `docs/HANDOFF_CLAUDE_UNTUK_GPT_MERGE.md`.

## 8. Status merge dengan `cp7/integration` (3 Okt 2026)

### 8.1 Yang terjadi dan cara konflik diselesaikan

- GPT memasukkan snapshot Claude `08d19674` ke `cp7/integration` (`77307d55`, `c5c08262`): SQL pembetulan penerimaan kini dipasang sekali di basis P09 (`scripts/cp7_procurement_bundle.py`). Claude melanjutkan 7 commit di cabangnya sendiri. Akibatnya 14 file konflik *add/add*.
- Merge `eabfec75` (parent `32b25b53` + `40c4127c`) menyelesaikannya di cabang ini, tanpa menyentuh cabang GPT:
  - 9 file tidak diubah GPT sejak snapshot itu, jadi versi Claude yang lebih baru dipakai: `correction.sql`, `material-name.sql`, manifest, verify, kedua panel, kontrak + tes, dokumen coverage.
  - 5 file diedit GPT, dan editnya diterapkan apa adanya di atas versi Claude: workflow (trigger `cp7/integration` + path komposisi), katalog akses (note-correction v2, FG ledger v2, boundary potong), probe (SQL penerimaan dari basis P09), cases (fixture jam hari ini, tanpa efek untuk kasus Claude yang sudah bertanggal lampau), dan catatan integrasi di `RECEIPT_CORRECTION.md`.
- Sesudah merge, `git diff origin/cp7/integration origin/claude/new-session-deapao` hanya berisi pekerjaan Claude: file pembetulan penerimaan, dokumen, dan perbaikan di 8.3.

### 8.2 Uji gabungan

Hanya run CI yang dihitung sebagai bukti. Hasil lokal (`LOCAL_PG16_DEV`) hanya catatan kerja.

| Commit | Isi | Hasil CI |
|---|---|---|
| `40c4127c` (GPT murni, pembanding) | — | 20 workflow yang terpicu hijau, termasuk F05 Durable Attention (37090157536) dan F03 Full (37090157569). |
| `2f50178b` (merge + trigger sementara) | Kode Claude sebelum perbaikan 8.3 | 53 run: 51 workflow CP7 GPT + Build UX + CodeQL. Pembetulan penerimaan [37091436624](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436624) **PASS 39/39** di atas komposisi P09 GPT. Build UX [37091436427](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436427) **FAIL** di `test:browser:cp5` (8.3a). Build UX tidak dijalankan di cabang GPT, tetapi `build:uat-auth` gagal dengan kode yang sama saat direproduksi lokal di `40c4127c` murni. Total 52 PASS, 1 FAIL (Build UX). |
| `19ff70ee` (perbaikan 8.3) | Kode final | **21/21 PASS**: 21 workflow yang path-nya menyentuh file yang diubah, termasuk pembetulan penerimaan [37093021067](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021067) **42/42** (36 native, 3 race, 1 HTTP, 2 browser), Build UX [37093021103](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021103) PASS (8.3a terbukti), P09 Procurement, 14 workflow F03, koreksi nota historis, P18, Shell S0, dan CodeQL. 30 workflow lain tidak terpicu karena path-nya tidak menyentuh file yang diubah. Semuanya PASS di `2f50178b`, dan perubahan `19ff70ee` tidak menambah atau menghapus objek database (hanya isi fungsi `cp7_receipt_fix` dan UI). |

Lokal (`LOCAL_PG16_DEV`, bukan bukti): 35/35 kasus native kode final PASS. `RF_YEAR_HISTORY_364` lokal kena batas waktu 80 menit (TIMEOUT), karena mesin lokal lambat untuk 364 transfer pada satu roll; di CI kasus ini PASS. Kode sebelum merge lokal 33/33. Lokal di hasil merge: `tsc -b`, `npm run test:security`, `check:source` dan `check:access` lolos. `vitest` penuh menghasilkan 27 baris gagal yang **identik** dengan `40c4127c` murni; semuanya tes yang butuh PostgreSQL native atau browser Playwright.

### 8.3 Perbaikan sesudah audit gabungan

Dua audit baca-saja dijalankan atas hasil merge: alur SQL/data GPT terhadap pembetulan penerimaan, dan frontend serta aturan GPT. Yang diperbaiki di cabang ini:

a. **Build UX merah sejak `3ab575a0` (GPT).** `VITE_DISPOSABLE_API_PORT` masuk ke objek runtime, tetapi gate artefak UAT belum mengenalnya, sehingga `build:uat-auth` dan `deploy:uat-auth` selalu gagal (`UAT_ARTIFACT_MODE_MISMATCH`). Gate sekarang mewajibkan input itu `void 0`; nilai apa pun, duplikat, atau posisi lain ditolak (`UAT_ARTIFACT_DISPOSABLE_PORT_PRESENT`). Tes gate ditambah. Gate tidak dilonggarkan.
b. **Pemetaan baris pengganti eksplisit**, satu id per posisi baris; sebelumnya ditebak dari bahan/harga/jumlah. **Lot dan catatan baris tidak lagi hilang.** Ini cacat nyata: sebelum perbaikan, `RF_DUPLICATE_LINES_KEEP_LOT` gagal di SQL `2f50178b` dengan `[('LOT-A2', None, 20), (None, None, 20)]`.
c. **Draft potong/transfer yang memakai roll penerimaan memblokir** dengan nomor dokumennya (`CP7_RECEIPT_FIX_DRAFT_ROLL_USE`). Draft potong Native berstatus `CUT` dengan `material_issue_posted=false`. Sebelum perbaikan, daftar blocker kosong di SQL `2f50178b`.
d. **Setiap blocker menyebut dokumennya** (`documents: [{type, number}]`), seperti aturan GPT.
e. **Pelaku di riwayat** memakai kontrak `cp7_note`: `actor_id`, nama profil saat ini, `CURRENT_PROFILE`, dengan fallback "pengguna <UUID>".
f. **Pesan penolakan satu jalur**: `normalizeClientError` → `src/lib/receiptCorrectionMessages.ts`. Penolakan 42501 memakai pesan umum GPT.
g. **Fakta uang disembunyikan saat `workspaceStale`**, aturan GPT dari `ConnectedSalesPage`.
h. **Teks periode tertutup** di panel invoice dibetulkan.
i. **Klaim "invoice FINAL setahun lalu" kini diuji** oleh `RF_YEAR_FINAL_INVOICE_PRICE`.
j. **Daftar penulisan langsung ke tabel Native dilengkapi** (`RECEIPT_CORRECTION.md`, serah terima butir 4).

### 8.4 Temuan di sisi GPT (tidak diubah Claude; diputuskan GPT)

1. **Pembelajaran potong sesudah salah bahan A→B.** Pembetulan memindah pemakaian potong ke roll baru dengan bahan B. Rencana input potong GPT memakai `roll_id`/`material_id` lama, sehingga observasi lama menjadi `INPUT_IDENTITY_UNAVAILABLE_OR_CHANGED` dan dikeluarkan. Ini gagal tertutup dan tidak merusak data, tetapi data belajar dari potongan itu hilang. Uji: rencana input → posting potong → betulkan bahan roll → ambil observasi; harapannya slice dikeluarkan.
2. **Episode reminder utang (AP_DUE) untuk penerimaan yang dibalik**, baik oleh pembetulan maupun pembalikan Native biasa, tetap `ACTIVE` tanpa alert (`SCENARIO_NO_ALERT_EPISODE_RETAINED`, `rule-episodes.sql`), dan penerimaan pengganti membuka episode baru. Uji: penerimaan jatuh tempo dengan episode aktif → betulkan → jalankan episode.
3. **Ganti kode bahan (SKU)** menandai hasil dan observasi cutting-yield GPT sebagai `ARCHIVED_STALE`, karena SKU disimpan di sumber potong. Aman, tetapi ramai.
4. **Format nomor pembayaran putar ulang** berbeda: nota memakai `· K-<8hex>`, penerimaan `· K<n>-<8hex>`. Pilih satu bila ingin seragam.
5. **Dokumen GPT yang menjadi basi sesudah merge** (masih menyebut "receipt32" atau "Claude WIP ditunda"): `docs/cp7/CURRENT_STATE.json` (antara lain baris 75–132, 3274, 4020, 4794), `ACTIVE_CONTINUATION.md` (21, 23, 63, 79, 87, 103), `CURRENT_PROGRESS.md:16`, `USER_TRANSACTION_TOOLS.md:30`, `GUARD_PREDICATE_ORDER.md:29,31`, `PENDING_SOURCE_READ.md:17`, `NOTE_CORRECTION_PRESENTATION.md:29`, `F03_REMAINING_CONTRACT.md:3`. Hash bundle P09/F03 di `CURRENT_STATE.json` berubah karena SQL Claude terbaru ada di basis P09. Mohon GPT memperbaruinya dengan run ID kualifikasinya sendiri.
6. **Celah yang dipunyai keduanya:** baris kartu mutasi belum membuka dokumen sumbernya, dan "Benerin penerimaan" masih panel terpisah (rencana komposisi GPT di `USER_TRANSACTION_TOOLS.md:30`).

7. **Batas umur koreksi HPP** masih keputusan owner yang terbuka di dokumen GPT (`NOTE_CORRECTION_PRESENTATION.md:29`, `CURRENT_PROGRESS.md:26`). Pembetulan penerimaan saat ini tidak punya batas umur, karena owner meminta koreksi harga final setahun lalu (`RF_YEAR_HISTORY_364`, `RF_YEAR_FINAL_INVOICE_PRICE`). Kalau owner menetapkan batas, batas itu harus menjadi satu pengaturan (`PENDING_POLICY_VALUE`) yang dipakai nota dan penerimaan sekaligus.
8. **Aturan GPT "dokumen terposting immutable"** (`framework-v2/01_KONTRAK_DAN_INTEGRASI.md:98`): dokumen asal pembetulan penerimaan tetap immutable dan dibalik oleh writer Native. Yang diubah di tempat hanyalah atribut roll fisik (nomor, supplier, waktu terima, baris induk), status header asal sesudah pembalikan, dan nama/kode bahan. Semuanya tercatat di lineage privat dan terdaftar di `RECEIPT_CORRECTION.md` (serah terima butir 4). Alasannya: roll fisik yang sama tetap dipakai potong, termasuk input potong GPT yang mengikat UUID roll.

### 8.5 Hasil CI per workflow

Disusun langsung dari API GitHub. "—" berarti workflow tidak terpicu di commit itu.

| Workflow | `40c4127c` | `2f50178b` | `19ff70ee` |
|---|---|---|---|
| Build UX | — | [**FAIL**](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436427) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021103) |
| CP6 Candidate CodeQL (T3) | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436463) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021054) |
| CP7 Completed Native Artifact Projection | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436742) | — |
| CP7 F03 Cash and Native Finance Readers | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157499) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436673) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021145) |
| CP7 F03 Combined Stack | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157524) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436714) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021081) |
| CP7 F03 Combined Supplier Returns | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157549) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436690) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021080) |
| CP7 F03 E01 Source Journey | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157523) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436621) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021055) |
| CP7 F03 E03 Customer Service | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157540) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436641) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021034) |
| CP7 F03 E05 Payroll Installments | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157527) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436626) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021019) |
| CP7 F03 E06 Year-end Late Invoice | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157537) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436636) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021027) |
| CP7 F03 E20 E14 Complete Stock Capacity | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157491) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436530) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021000) |
| CP7 F03 E24 Material Issue | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157492) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436648) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021097) |
| CP7 F03 Full Retained Components | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157569) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436587) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021069) |
| CP7 F03 Native Misc Finance | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157535) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436614) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021072) |
| CP7 F03 Native Reservation and Size Planner Seams | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436595) | — |
| CP7 F03 P13 Retained Regression | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436629) | — |
| CP7 F03 Required Cost Continuations | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157505) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436695) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021056) |
| CP7 F03 Supplier Current Authority | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436693) | — |
| CP7 F03 X04 Paid Redye Continuation | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157503) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436688) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021064) |
| CP7 F03 X04 Source Versions | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157514) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436613) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021041) |
| CP7 F04 Global Native Production Supply | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436661) | — |
| CP7 F04 Native Cutting Observations | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436486) | — |
| CP7 F04 Native Demand History | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436692) | — |
| CP7 F04 Native Model Evaluation | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436646) | — |
| CP7 F04 Native Planning Draft Bridge | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436618) | — |
| CP7 F04 Native Product Bound Netting | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436697) | — |
| CP7 F04 Native Profile and Baseline Targets | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436691) | — |
| CP7 F04 Native Selected Production Schedule | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436665) | — |
| CP7 F04 Prospective Cutting Inputs | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436602) | — |
| CP7 F04 Prospective Native Cutting Model and Consumer | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436657) | — |
| CP7 F05 Native Durable Attention | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157536) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436472) | — |
| CP7 F05 Native Frozen Analysis | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436475) | — |
| CP7 Native Read Stage Diagnostic | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436640) | — |
| CP7 Note Command Diagnostic | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436718) | — |
| CP7 Owning Historical Note Correction | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157538) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436647) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021018) |
| CP7 Owning Receipt Correction | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436624) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021067) |
| CP7 P00 accepted-base catalogue | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436551) | — |
| CP7 P02 actor facade | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091437153) | — |
| CP7 P02 source capture probe | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436671) | — |
| CP7 P03 production policy | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436617) | — |
| CP7 P04 WIP kernels | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436709) | — |
| CP7 P09 Procurement | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157508) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436609) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021030) |
| CP7 P10 Finished goods | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436571) | — |
| CP7 P11 Sales | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157555) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436716) | — |
| CP7 P12 Nota and payroll lifecycle | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436678) | — |
| CP7 P12 Nota source | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436616) | — |
| CP7 P13 Finance | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436635) | — |
| CP7 P13 Finance Analysis | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436663) | — |
| CP7 P13 HPP recost | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436706) | — |
| CP7 P13 Period control | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436525) | — |
| CP7 P18 E01 Consumer Bridge | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090157488) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436701) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021003) |
| CP7 Retain Existing Native Originals | — | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436503) | — |
| CP7 Shell S0 | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37090156257) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37091436612) | [PASS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37093021038) |

Ringkasan: `40c4127c` success 20; `2f50178b` failure 1, success 52; `19ff70ee` success 21

### 8.6 Commit CI sementara

`2f50178b` hanya menambahkan `claude/new-session-deapao` ke trigger push 50 workflow CP7 GPT, supaya semua tes GPT jalan di hasil gabungan; job, langkah, path, dan izin tidak diubah. Perubahan ini dibalik di commit terakhir cabang ini. Cek: `git diff origin/cp7/integration origin/claude/new-session-deapao -- .github/workflows` harus kosong.

### 8.7 Cara merge untuk GPT

- Audit: `git diff origin/cp7/integration...origin/claude/new-session-deapao` (hanya pekerjaan Claude).
- Merge: `git merge origin/claude/new-session-deapao` dari `cp7/integration`. Selama `cp7/integration` masih `40c4127c`, merge ini tanpa konflik karena cabang Claude sudah memuatnya. Kalau `cp7/integration` sudah maju, konflik yang tersisa hanya pada perubahan GPT sesudah `40c4127c`.
- Sesudah merge: jalankan ulang workflow GPT yang memasang basis P09, dan perbarui dokumen di 8.4 butir 5.

## 9. P08 bukti fisik kain (5 Okt 2026, cabang `claude/new-session-deapao`)

Basis: `cp7/integration` caa1b038 (checkpoint kain + recovery) yang sudah digabung ke cabang ini (1a030315). Dokumen utama: [`docs/cp7/f04/NATIVE_FABRIC_PHYSICAL.md`](cp7/f04/NATIVE_FABRIC_PHYSICAL.md) dan deklarasi [`NATIVE_FABRIC_PHYSICAL.json`](cp7/f04/NATIVE_FABRIC_PHYSICAL.json).

### 9.1 Yang berubah

| Berkas | Perubahan |
|---|---|
| `scripts/cp7-src/planning/fabric-requirements.sql` | `source` → `cp7.fabric-source.v2` dengan blok `physical` (roll, stok per lokasi, draf potong belum diposting, intent, PO terbuka BB); fungsi baru `physical_source`, `index`, `recipe_state`, `plan`; `needs` kini 4 argumen. Hak baca kolom saja + EXECUTE fungsi sisa PO BB. |
| `scripts/cp7-src/planning/analysis.sql` | `plan()` dihitung sekali per analisis dan diteruskan ke `needs()`. |
| `scripts/cp7-src/plan-native/bootstrap.sql` | `cp7_capture` boleh SELECT kolom `id,target_key,cutting_group_id` pada `cp7_plan_native.intents` (tanpa payload/aktor). Tabel privat baru `cp7_plan_native.apply_own_drafts` (lihat 9.2 butir 6). |
| `scripts/cp7-src/plan-native/commands.sql` (milik GPT) | `apply` menandai draf Native miliknya sendiri hanya di sekitar pemeriksaan ulang setelah tulis (sisip → preflight → hapus). |
| `src/nativeAnalysis.ts`, `src/NativeMaterialNeedsView.tsx` | Penerima menerima angka fisik kain hanya dalam batas kernel; teks menjelaskan "bukan reservasi stok" dan "hanya PO yang tercatat di ERP". |
| `scripts/cp7_fabric_physical_*`, `scripts/cp7_f05_analysis_probe.py` | Suite Native baru 21 kasus (flag `fabric_physical`). |
| `scripts/cp7_fabric_recipe_cases.py`, `scripts/cp7_fabric_recipe_browser.mjs`, `tests/cp7/families/f04/fabric-recipe.mjs` | Oracle penerus fabric13 (ID/jumlah tetap); kontrol SQL Shell 24 → 28. |
| `scripts/cp7_analysis_bundle.py` | `TABLE_GRANTS['cp7_capture']` memuat hak kolom P08; `GRANTS['cp7_capture']` mendeklarasikan satu-satunya EXECUTE baru pada fungsi pendahulu: `erp.bb_commitment_line_remaining_v1(uuid,uuid)` (lihat 9.4). |
| `.github/workflows/claude-p08-*.yml` | Workflow khusus cabang ini (P08 + regresi 152/284/39 + Shell/CodeQL). Tidak mengubah workflow GPT. |

### 9.2 Keputusan desain yang perlu GPT ketahui

1. Draf potong yang ditautkan intent dihitung sebagai **alokasi rencana**, bukan reservasi (tetap konsisten dengan `SHARED_MATERIAL_POOL.json`). Stok bebas hanya ditambahkan bila pembagiannya unik.
2. WIP potong Native hanya terikat model+ukuran; warna/merek belum terbukti → NEEDS_CHECK. Untuk produk seperti itu "terpasang" dan "tambahan dari luar" sengaja UNKNOWN, dengan batas atas di alasan (bukan angka beli). Terpasang = 0 hanya untuk PCS yang terbukti belum dipotong (semua WIP produk/ukuran itu sudah pasti). Sesuai masukan GPT 5 Okt: fixture terikat (gap 93) untuk jalur pasti, fixture ambigu untuk UNKNOWN/batas atas; tidak ada hasil yang diberi KNOWN hanya karena fixture terikat.
3. Sidik jari analisis kini mencakup stok/draf/PO bahan kain yang direview: penerimaan atau draf potong bahan itu membuat Original lama `ARCHIVED_STALE`. Tanpa resep kain, blok fisik kosong sehingga suite 152/284/39 secara logika tidak berubah — tetap wajib dikualifikasi ulang karena tanda tangan mesin berubah.
4. **Cacat resep lama yang ikut diperbaiki:** hash resep dulu memakai seluruh baris `erp.materials`; Native menulis ulang stok tersimpan/biaya rata-rata/`row_version`/`updated_at` pada tiap penerimaan dan pemakaian, sehingga resep yang sudah direview langsung UNKNOWN setelah barang masuk/keluar. Kini `cp7_fabric_native.material_hash` hanya memakai field master. Counterfixture `P08_FABRIC_MASTER_CHANGED` diganti ke revisi nama master; kontrol Shell 25 → 26.
5. Kemampuan produksi global tetap UNKNOWN (kebijakan kelipatan/kapasitas masih PENDING_POLICY_VALUE).
6. **Cacat apply rencana yang ditemukan CI P08 (run 37360628807).** `cp7_plan_native.apply` memeriksa ulang Original setelah SAVE_DRAFT Native. Sidik jari P08 memuat draf belum diposting pada kain yang direview, sehingga pemeriksaan ulang menolak draf buatannya sendiri (`CP7_PLAN_SOURCE_CHANGED`). Perbaikannya: penanda transaksi-lokal `apply_own_drafts` (dihapus sebelum commit, terikat `txid`), dan `physical_source` hanya mengabaikan draf itu di dalam transaksi apply tersebut. Perubahan lain tetap membuat Original basi. Setelah satu apply ter-commit, Original lama menjadi basi bila ada resep kain yang direview, jadi apply berikutnya perlu ambil analisis baru. Mohon GPT menilai apakah perilaku ini cocok dengan alur planner; alternatif yang lebih longgar tidak dipilih karena bisa memakai angka alokasi lama.
7. **Batas skala sumber fisik.** Roll yang sudah habis tidak lagi ikut sumber. Sebelumnya semua roll historis ikut, sehingga setelah bertahun-tahun penerimaan ambil analisis bisa ditolak. Batas baris PO dihitung setelah memilih baris terbuka; sebelumnya baris tutup bisa menyingkirkan baris terbuka tanpa error. Kontrol Shell ke-27 membuktikan keduanya: gagal pada SQL lama, lulus pada perbaikan.

### 9.3 Status bukti

Lihat tabel CI di `docs/cp7/f04/NATIVE_FABRIC_PHYSICAL.md` (diperbarui setelah run selesai). Hasil lokal hanya LOCAL_PG16_DEV, bukan bukti. `full_P08_acceptance=false`, `production_go=false`.

### 9.4 Riwayat CI dan temuan di luar P08

1. **Run pertama P08 gagal (tetap tercatat FAIL).** Run 37357315101 pada 1850619c: kelima suite matriks (fabric-physical21, fabric13-successor, analysis152, plan39, attention284) berhenti saat pemasangan dengan `F03_UNDECLARED_ACL_DELTA` pada `erp.bb_commitment_line_remaining_v1(uuid,uuid)`. Sumber fisik memberi EXECUTE fungsi BB itu ke `cp7_capture`, tetapi GRANTS gabungan belum mendeklarasikannya. Perbaikan ebf3a394 hanya menambah deklarasi signature itu; guard ACL probe tidak diubah. Itu satu-satunya hak fungsi baru di diff P08 (sisanya SELECT kolom di `TABLE_GRANTS`).
2. **Build UX merah sejak merge basis (bukan dari P08).** Uji browser CP6 `tests/browser/cp6-laundry-qc.spec.ts:567` ("committed send form stays retired after failed then successful refetch") gagal di desktop dan mobile pada merge 1a030315 (run 37339224171, sebelum perubahan P08) dan pada 1850619c (run 37357314906). Penyebabnya commit GPT 3c7cb2cf ("retire stale Laundry/QC facts"). Setelah aksi tersimpan tetapi refresh gagal, `useLaundryQcWorkspace` kini membuang workspace lama, sehingga form kirim tidak dirender lagi. Yang tampil adalah "Data belum tersedia; semua tombol transaksi tetap terkunci." Uji lama masih mengharapkan form ada dengan nilai batch kosong (`toHaveValue('')`). Perilaku baru lebih aman, tetapi workflow Build UX tidak berjalan di `cp7/integration`, jadi ketidakcocokan ini tidak terlihat di sana. Claude **tidak** mengubah domain Laundry milik GPT di cabang ini. Usulan patch uji di bawah sudah dicoba di lokal: 26/26 PASS (LOCAL, bukan bukti). Patch ini tidak melonggarkan guard: form yang sudah dipakai harus hilang, tidak cukup dikosongkan, dan sisa uji (Refetch → satu opsi, tombol Post nonaktif, tepat satu aksi) tetap sama. Keputusan ada di GPT.

```diff
--- a/tests/browser/cp6-laundry-qc.spec.ts
+++ b/tests/browser/cp6-laundry-qc.spec.ts
@@ -578,7 +578,11 @@
   await expect(page.getByText(/Aksi sudah tersimpan, tetapi refresh authoritative gagal/i)).toBeVisible()
-  await expect(page.getByLabel('BATCH DISTRIBUSI AUTHORITATIVE')).toHaveValue('')
+  // CP7 3c7cb2cf: a failed post-commit refresh retires the stale workspace, so
+  // the committed form is gone (not merely cleared) until Refetch succeeds.
+  await expect(page.getByText('Data belum tersedia; semua tombol transaksi tetap terkunci.')).toBeVisible()
+  await expect(page.getByLabel('BATCH DISTRIBUSI AUTHORITATIVE')).toHaveCount(0)
+  await expect(page.getByRole('button', { name: /Post pengiriman atomic/ })).toHaveCount(0)
   await page.getByRole('button', { name: 'Refetch', exact: true }).click()
```

## 10. P18 — pengingat kebutuhan kain `FABRIC_NEED` (5 Okt 2026, cabang ini)

Dokumen: [`docs/cp7/p18/P18_FABRIC_RULE.md`](cp7/p18/P18_FABRIC_RULE.md) dan deklarasi `P18_FABRIC_RULE.json` (11 kasus: 7 DB, 1 race, 1 HTTP, 2 browser). Workflow: `.github/workflows/claude-p18-fabric-rule.yml` (fabric-rule11, rule-lifecycle16, p18-e01-9). attention284 berjalan di workflow P08 pada head yang sama.

| Berkas (milik GPT kecuali disebut) | Perubahan |
|---|---|
| `reminders/rule-condition-source.sql` | Domain `FABRIC`, satu kondisi per baris kain (nilai = `additional_external` persis), cakupan `fabric`. |
| `reminders/rule-policy.sql`, `policy-history.sql`, `local-sink.sql` | Aturan kelima `FABRIC_NEED` (GLOBAL/TARGET, label "Kebutuhan kain"). Khusus `FABRIC_NEED`, satuan ambang boleh huruf kecil agar sama persis dengan satuan Native (mis. `yd`). Aturan lama tidak berubah. |
| `src/nativeRuleSource.ts`, `src/nativeReminderPolicy.ts`, `src/NativeReminderPolicyPanel.tsx`, `src/NativeRuleSourcePanel.tsx` | Penerima tertutup untuk `FABRIC_NEED`, input "Satuan dasar kain", kalimat alasan kain. |
| `scripts/cp7_rule_policy_cases.py`, `scripts/cp7_rule_source_cases.py` | Oracle penerus dalam rantai 284 (ID/jumlah tetap): lima aturan; nilai dan cakupan kain. |
| `scripts/cp7_p18_fabric_rule_*` (Claude) | Suite baru. |

Keputusan: nol yang masih asumsi tidak pernah "selesai"; UNKNOWN atau resep belum direview menjadi `DATA_REVIEW` tanpa episode; ambang hanya dibandingkan dengan satuan yang sama persis (tanpa konversi atau penyamaan huruf); pratinjau hanya lokal. Kontrak tetap `cp7.native-rule-conditions.v2` karena belum terpasang di mana pun. Bila GPT ingin naik ke v3, penerima dan SQL perlu diubah bersamaan.

### 10.1 Status CI (5 Okt 2026, 21:10 UTC)

- **Head 7b89f767:** analysis152, plan39, rule-lifecycle16, p18-e01-9, Shell S0 dan CodeQL PASS.
- **fabric-physical21: 17/21.** Perbaikan apply terbukti. Sisa kegagalan adalah dua fixture `post` yang masih berperan `authenticated`, ditambah dua browser dengan `today` hilang.
- **fabric-rule11: 9/11.** Sisa kegagalan adalah dua browser karena `today` yang sama.
- **Perbaikan** hanya di fixture/skrip uji. Oracle dan SQL produk tidak diubah.
- **Tidak dijalankan karena kapasitas runner:** fabric13, attention284 dan receipt-correction ("job was not acquired by Runner"). Ketiganya dijalankan ulang.
- **attention284 pada ebf3a394 (run 37360628807) PASS**, tetapi itu sebelum perubahan SQL pengingat. Bukti 284 untuk P18 masih menunggu run baru.
- **Kegagalan pertama tetap tercatat** di `NATIVE_FABRIC_PHYSICAL.md` dan `P18_FABRIC_RULE.md`.

### 10.2 Status CI (5 Okt 2026, 23:15 UTC)

- **P18 lulus penuh.** fabric-rule11 PASS 11/11 (run 37374231262). attention284 PASS dengan SQL pengingat baru (run 37374383973). rule-lifecycle16 dan p18-e01-9 PASS (run 37366015710).
- **P08:** fabric13-successor, analysis152, plan39 dan attention284 PASS. Shell S0 PASS (28 kontrol), CodeQL PASS, receipt-correction PASS (rerun).
- **fabric-physical21: 17/21.** Kegagalan pertamanya tetap tercatat. Dua sisa diperbaiki:
  1. Oracle penerus untuk kasus POST nyata. Celah rencana memang UNKNOWN setelah potongan diposting, jadi oracle sekarang membuktikan pengeluaran terhitung sekali lewat sumber fisik.
  2. Laporan bersama sekarang mengutip sumber semua fakta, sehingga rujukan stok bebas dan PO tampil.

  `src/nativeAnalysis.ts` (`analysisReport`) berubah. Konsumen pembanding laporan memakai fungsi yang sama, jadi tetap konsisten.


### 10.3 Status CI (6 Okt 2026, 00:35 UTC) — P08 dan P18 hijau pada b292ae4c

- **P08 lulus penuh.** Run 37387866413:
  - fabric-physical21 PASS 21/21 (16 DB, 2 race, 1 Auth/HTTP, 2 browser);
  - fabric13-successor PASS 13/13;
  - attention284 PASS 284/284.
  Semua dengan `cp6_restored=true` dan `advisor_gate=true`.
- **Shell S0 dan CodeQL.** Shell S0 PASS dengan 28 kontrol kain (run 37387866583). CodeQL PASS (run 37387866362).
- **Kegagalan pertama tetap tercatat.** Run 37357315101, 37360628807, 37366015511 dan 37374383973 ada di tabel `NATIVE_FABRIC_PHYSICAL.md`.
- **Belum termasuk.** Bukti ini adalah kualifikasi Native di CI, bukan audit independen. `full_P08_acceptance=false`, `independent_acceptance=false`, `production_go=false`.
- **Build UX** tetap merah karena warisan 3c7cb2cf (§9.4).
- **Commit sesudahnya.** 9b90b4c6 hanya mengubah dokumen.

## 11. P19 — skala hitung kain dan dua temuan untuk GPT (6 Okt 2026)

Rincian ada di `docs/cp7/p19/P19_FABRIC_SCALE.md`. Ringkasnya:
- **Perbaikan di kode kain cabang ini.** `cp7_fabric_native.plan` dan `needs` sebelumnya tumbuh sebesar bahan × roll, draf × roll, dan target². Sesudah perbaikan, waktunya 3–4 detik pada 5.000 target / 20.000 roll berisi (sebelumnya 57 detik), LOCAL.
  - Keluaran `plan` sekarang datar (kunci indeks di tingkat atas). Konsumennya hanya `needs`.
  - Kesetaraan dibuktikan lokal: 3.300 set data acak, keluaran lama dan baru sama persis.
  - Kualifikasi CI pada head baru sedang dijalankan.
- **Perbaikan fixture tes (bukan kode produk).** Fixture `cp7_fabric_recipe_browser_fixture.py` sekarang mengirim waktu WIB tanpa detik nol, persis seperti yang dipegang input `datetime-local` di Chromium. Kegagalan pertama tercatat di run 37394553511.
- **Untuk GPT, tidak diubah Claude:**
  1. Loop `cp7_analysis_native.build` menggabungkan larik per baris dengan `||`, sehingga waktunya tumbuh sebesar target². Pola `materials` saja butuh 4 detik pada 1.200 target dan 85 detik pada 5.000 target (LOCAL).
  2. Snapshot keuangan pemilik di ambil analisis butuh ±10 detik di DB lokal kecil. Sebabnya JIT PostgreSQL pada `erp.initial_prepayment_checks_v1` (CP6), dihitung dua kali per ambil, ditambah hash seluruh riwayat GL. Status `jit` di hosted perlu dicek (baca saja).

  Keduanya menahan uji P19 untuk ambil analisis penuh.

### 11.1 Status CI (6 Okt 2026, 03:50 UTC)

- **a4ebb6a8 (perbaikan `plan`/`needs`):** semua suite cabang PASS pada satu head.
  - fabric-physical21 21/21, fabric13 13/13, analysis152 152/152, plan39 39/39, attention284 284/284 (run 37404829353).
  - fabric-rule11 11/11, rule-lifecycle16 16/16, p18-e01-9 9/9 (run 37404835115).
  - Shell S0, CodeQL dan receipt-correction PASS.
- **882fc40a (perbaikan `condition_rows`):**
  - P18 PASS (run 37406898697); Shell S0, CodeQL dan receipt-correction PASS.
  - Suite P08 lengkap di 2ae1db92 juga PASS (run 37408720092): 21/21, 13/13, 152/152, 39/39, 284/284. 2ae1db92 hanya menambah dokumen.
  - **Kandidat merge/audit dari cabang Claude saat ini: 2ae1db92.**
- **Kegagalan pertama tetap tercatat.** fabric13 di 7dad62c9 gagal karena fixture waktu WIB, dan sudah diperbaiki di fixture.


### 11.2 Bukti integrasi GPT dan penutupan regresi layar oleh penulis (6 Okt 2026)

Paket bukti baru ada di `docs/cp7/WRITER_CHECKPOINT_20261006_QUALIFIED_UI_AND_P19.md`. Cabang Claude telah digabung di `ac714a5b`; Fable independen menutup PRE-02/03/04 di audit `db8c057`. GPT tidak mengirim pesan kepada auditor atau memulai pekerjaan mereka.

- **PRE-01 diketahui sebabnya:** layar CP7 memakai `erp_cp7_get_recost_queue_v1`, tetapi paket T3 CP6-BF tidak memasangnya. Run `a3aabd1d` merekam HTTP404/PGRST202 dan kedua teks alert, lalu membuktikan keduanya hilang sesudah stack CP7 lengkap dipasang. Assertion nol alert tetap.
- **PRE-05 punya pengganti terhubung:** 29 kasus CP6 tetap, dua simulasi penjualan hanya dipensiunkan dari komposisi CP7 dan diganti dua lifecycle invoice P11 (manual13 PCS, create/edit/post; mobile kehilangan balasan dan reconcile sesudah reload). Browser **31/31**, run37466200640. Hasil lama27/4 tidak diubah menjadi hijau.
- **P19 hasil terukur:** popup stok desktop/mobile415.4/529.1ms; analisis952.5/1195ms. Koreksi nota year364 yang benar-benar commit1810.595ms, sebelumnya2982.830ms di3a4. Forced-rollback diagnostic adalah jalur terpisah; angka4596.946ms/5491.544ms lama bukan waktu command commit Native40.
- **Regresi integrasi:** `ca37884d` mengkualifikasi Native P11 terpisah64/64 dan delapan komponen F03 penuh132(+3 smoke),34,64,90,50,61,5,10. Semua kasus, pemulihan penuh, backup, primary, advisor dan Auth0→0 dibaca.385 keputusan/penolakan izin persis dan empat penolakan mutasi OWNER dilindungi terbukti; dispatch51/75 mempertahankan urutan konteks Native. Shell Native385 plus kontrol negatif36, browser fixture6 dan SARIF CodeQL0 disimpan terpisah dari bukti bisnis.
- **PRE-06:** workflow CP3/CP5 ditandai historis dan menolak cabang yang tidak cocok sebelum menjalankan runtime lama. Regresi numerik warisan tetap memakai T2; tidak ada klaim backup Actions yang kedaluwarsa hidup kembali.
- **CAT-01/PRE-07:** komparator lengkap yang sama dipakai E05/E06. E03 Native10 sudah mempertahankan OID/owner/tuple; successor tool `56c48b6e` memperluas saksi ini ke E05/E06 dan seluruh grup Native F03. Kualifikasi successor sudah dibaca dari Originals: E0526/26, E065/5 dan seluruh delapan komponen F03 lulus;39 grup Native mempertahankan614 snapshot katalog lengkap/575 transisi OID/owner yang sama, tanpa perubahan tuple. Penyebab OID pada kegagalan pertama yang tidak merekam OID tetap tidak diketahui.
- **Head bukti terbaru `56c48b6e`:** browser31/31 (run37468012520), combined22, supplier authority6, Build UX1551/164 dan browser fixture2/2/16/26, Shell385 keputusan persis/kontrol negatif36 plus browser6, dan dua SARIF CodeQL0 juga selesai lulus. Semua tetap source-bound, dengan formula/SQL produk/frontend identik dengan4b; no extra Native credit dari alat pembaca bukti.

Ini kualifikasi penulis pada source tertentu. Penutupan PRE-01/05/06/07 oleh auditor independen, kapasitas pabrik/transport lengkap, full P18/P19, P20, P21 dan GO tetap terpisah. Tidak ada perubahan hosted/main atau nilai operasional owner yang dikarang.

### 11.3 P19 penerima sumber UTF8 — kandidat setelah checkpoint e724c521

Checkpoint §11.2 sudah diterbitkan di e724c521. Lanjutan P19 menemukan empat contoh tandingan nyata di penerima: sumber analisis/dokumen finansial menghitung karakter UTF16, dan penerima seluruh baris kondisi belum memeriksa batas byte produsen. Termasuk dokumen historis yang melebihi8MB ketika sumber terkini kecil. Empat penolakan yang seharusnya terjadi justru diterima oleh versi lama; laporan pertama6 dan profil7 beserta source uji persis dipertahankan.

Kandidat frontend menghitung JSON lengkap sebagai UTF8 di tiga batas itu. Angka batas tetap8,000,000; tidak membuang baris, menaikkan batas, mengubah SQL/rumus Native atau mengizinkan hasil parsial. Lokal38/38 termasuk tujuh kontrol kapasitas, body ASCII/Unicode tepat8MB dan cek hak/uang asli; build/typecheck/ownership/client scan juga lulus. Kesalahan tipe pada penempatan awal oracle Node ikut disimpan; uji kini di lane Node yang sudah ada, tanpa melonggarkan compiler. Kualifikasi Native/Auth/browser yang terdampak tetap wajib di head kandidat. Lihat `docs/cp7/p19/P19_UTF8_SOURCE_RECEIVERS_20261006.md`.

Ini perbaikan cacat penghitung byte; transport sumber31MB/volume5000 dan pekerjaan latar yang benar tetap belum selesai. Bukti lama di source56/e724 tidak dipromosikan menjadi bukti produk frontend baru. Batas layar1/2/3 detik, full P18/P19/P20/P21, owner inputs HOLD dan larangan production GO tetap sama.


### 11.4 Kualifikasi penerima UTF8 di source0bd (6 Okt 2026)

Kode produk ada di `0bd60f2c073d490e34060305b37709c9b479eeae`, tree `015b640493215f562bfde690e3c8b633913550ac`. `38242918` hanya pembacaan arsip lama yang dipin; tidak mengubah frontend/SQL. Detail dan seluruh Originals: `docs/cp7/p19/P19_UTF8_QUALIFICATION_CHECKPOINT_20261006.md` dan `docs/cp7/evidence/p19/utf8-receiver-native-0bd/INDEX.json`.

- Native analisis152, pengingat284, browser31, kain fisik21/resep13/rencana39, aturan kain11/lifecycle16/bridge9, delapan komponen F03 dan koreksi/keuangan/sumber transaksi yang terdampak lulus serta dibaca per kasus. Build UX/Shell1,558 tes/165 file dan dua CodeQL0. Seluruh32 workflow source0bd sudah selesai sukses. Kelima komponen P08 lengkap; pengingat284 duplikat juga dibaca sendiri dari Original lengkap179 Native/40 race/29 Auth-HTTP/36 browser, dengan tiga probe tambahan tanpa kredit exit. Tidak ada run checkpoint ini yang masih tertunda.
- Semua614 snapshot/575 transisi identitas pada39 grup F03 tetap sama. Ada satu contoh nyata42 posisi pasangan fungsi bergeser tanpa perubahan OID/owner/tuple/definisi. Ini bukti urutan saja tidak cukup menyimpulkan DROP/CREATE, bukan rekonstruksi penyebab merah lama.
- Popup stok415.9/495.7ms; analisis lengkap964.2/1221.3ms. Perintah nota setahun benar-benar commit2236.219ms sebelum readback buku terpisah. Semua366 baris buku/lot,364 saldo stok sesudahnya+12, FG112/net240/paid0/AR240 dan replay UUID tanpa efek kedua diperiksa. Angka ini bukan bukti simpan biasa≤2s atau seluruh alur layar≤3s.
- Lanjutan penulis: hasil asli P08 terakhir sudah tersimpan; selesaikan transport sumber lengkap/pekerjaan latar P19 dengan pengikatan actor/run/request/hash dan hak terkini, lalu volume Native/konkurensi/pemulihan. Sumber stand-in31MB/5000 target/13.15s belum merupakan capture Native sukses. Batas1/2/3 detik dan8MB/8s tidak dinaikkan.

Full P18/P19/P20/P21, pembekuan resmi dan GO belum selesai. Tidak ada pesan eksternal, perubahan hosted/main/live WA atau nilai owner yang dikarang. Penulis berikutnya membaca head canonical serta checkpoint ini sebelum mengambil alih, dan tidak menggabungkan kasus yang tumpang tindih menjadi jumlah unik/fullCP7.

## 12. P18 siklus penuh, Bayar supplier, latihan P21 (6 Okt 2026 sore, cabang Claude)

Basis: cabang ini di-fast-forward ke `cp7/integration` `ab6f1f97`, lalu ditambah commit berikut. Saya tidak menyentuh P19 transport/latar belakang maupun koreksi nota setahun karena keduanya lane GPT. Pekerjaan GPT juga tidak diubah.

### 12.1 P18 siklus penuh, tanpa perubahan produk

`scripts/cp7_p18_full_cycle_{cases,probe}.py`, workflow `claude-p18-full-cycle.yml`, dokumen `docs/cp7/p18/P18_FULL_CYCLE.md`.

- **Alur:** lembar kerja E01 diteruskan sampai semua hutang lunas:
  - supplier 1.000;
  - vendor laundry 120;
  - upah mandor 180.
- **Pengecekan batas:** di 8 batas, perubahan buku besar sejak awal sama dengan buku pembantu (bahan, WIP, lot FG, hutang supplier, hutang vendor, hutang mandor, piutang, kas). Pengecekan per dimensi vendor, mandor, dan pelanggan juga dijalankan. Perubahan pada akun di luar daftar membuat kasus gagal. Posisi laporan keuangan dibandingkan di awal, sesudah produksi, dan di akhir.
- **Hasil:**
  - Run pertama di 8beab7fe, run 37488624358: PASS dengan posting Native.
  - Run penerus di 4042235f, run 37490923997: PASS, dengan supplier, vendor, dan payroll dibayar lewat penulis aplikasi.
  - Angka akhir: bahan 400, FG 675, piutang 175, kas −1.100, laba kotor 150.
- **Bukti:** `docs/cp7/evidence/p18-full-cycle/`.

### 12.2 Temuan dan penutupan: pembayaran supplier baru dari aplikasi

Sebelumnya CP7 tidak punya cara mencatat pembayaran supplier baru; yang ada hanya baca, koreksi, dan pembalikan. Penutupnya dirinci di `docs/cp7/SUPPLIER_PAYMENT_CREATE_HANDOFF.md`.

**Berkas yang ditambah atau diubah:**

| Jenis | Berkas |
|---|---|
| SQL | `scripts/cp7-src/invoices/payment-create.sql`, dipasang lewat `cp7_procurement_bundle.py` sesudah `payment-correction.sql` |
| Penguji bundel | `cp7_supplier_payment_create_bundle.py` |
| Frontend | `SupplierPaymentCreatePanel.tsx`, `supplierPaymentCreateContract.ts`, `SupplierPaymentPanel.tsx`, aksi recovery `CREATE` di `productionRecovery.ts`, tipe RPC |
| Daftar kepemilikan | `check-source-ownership.mjs`, `check-access-catalog.mjs`: dua batas RPC baru |

**Hasil CI:**
- **Run pertama** 4042235f, run 37490924137: 7 PASS dan 1 INCOMPLETE. Sub-kontrol baru saya salah menganggap `authenticated` tidak bisa INSERT ke `erp.supplier_payments`; di klon setara hosted, INSERT itu bisa. Log aslinya disimpan.
- **Run f999b502**, run 37491709756: browser desktop dan mobile PASS, termasuk balasan hilang sesudah commit → reload → UUID sama. Sub-kontrol yang sama masih INCOMPLETE.
- **Run 917ff2b7:** sub-kontrol itu diganti pengamatan yang dicatat sebagai temuan. Hasilnya sedang jalan (lihat §12.4).

**Shell di 4042235f** (run 37490924114): lulus, termasuk 6 kontrol DOM baru dan pemeriksaan kepemilikan dan akses.

**Temuan bawaan hosted untuk GPT dan owner:**
- `authenticated` punya USAGE pada skema `erp` (dipertahankan G-01).
- Di klon setara hosted, `authenticated` bisa INSERT DRAFT ke `erp.supplier_payments`.
- `erp.post_supplier_payment` bisa dieksekusi `authenticated` dan hanya memeriksa peran, tidak memeriksa `finance.ap.pay`.
- PostgREST hanya membuka `public`, jadi ini bukan rute aplikasi.
- Hasil pengamatan lengkapnya ada di laporan kasus `CURRENT_ACCESS`. Keputusan menutup jalur ini ada di GPT dan owner.

**Catatan merge:**
- Bundel P09 kini memuat satu berkas SQL tambahan. Reachability lokal 155/155 lulus.
- Semua tumpukan yang memakai `cp7_procurement_bundle` ikut memasang modul ini. Receipt-correction, P18, dan E01 composition memasangnya tanpa masalah.

### 12.3 Latihan P21 (klon sekali pakai, bukan hosted)

`scripts/cp7_p21_rehearsal_probe.py`, workflow `claude-p21-rehearsal.yml`.

**Run pertama** 15baeb3e, run 37491648792:
- Pasang berhasil: 1.407 fungsi, 75 tabel cp7, 34 role, dan 11 baris seed bawaan pemasangan.
- Rollback sebelum dipakai berhasil, dengan ketiga komponen pemulihan persis.
- Pasang ulang menghasilkan katalog identik, baik sha256 maupun baris seed.
- Langkah "pakai" berhenti di fixture karena probe tidak menyiapkan fondasi seperti yang dilakukan runner. Ini kesalahan probe.

**Penerus 0fcc04ac** sedang berjalan.

Ini latihan, bukan receipt P21. Receipt P21 tetap menunggu P20.

### 12.4 Status run terbaru

- **Bayar supplier, 917ff2b7** (run 37492084385, job 112367128931): **10/10 PASS** (Native 4, race 3, HTTP 1, browser 2), `cp6_restored=true`, `advisor_gate=true`.
- **Pengamatan jalur lama hosted:** ADMIN tanpa `finance.ap.pay` bisa INSERT DRAFT dan memposting lewat Native, tetapi hanya dengan koneksi database langsung karena PostgREST hanya membuka `public`. Ini perlu keputusan GPT/owner; rinciannya di `SUPPLIER_PAYMENT_CREATE_HANDOFF.md`.
- **P18 siklus penuh, 4042235f:** PASS.
- **Latihan P21 penerus, 0fcc04ac** (run 37492771185, job 112369494740): **PASS**, `cp6_restored=true`, `advisor_gate=true`.
  - Pasang sekali menghasilkan katalog `e75968e2…`.
  - Rollback sebelum dipakai memulihkan keadaan persis.
  - Pasang ulang menghasilkan katalog dan baris seed yang identik.
  - Langkah pakai berupa satu pembayaran supplier nyata.
  - Rollback sesudah dipakai **ditolak** (`CP7_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE`) karena ada 2 baris request CP7 baru.
  - Pemulihan harness berhasil, dan drill backup/restore T3 hasilnya `RESTORED_SAME_MEANING`.
  - Bukti: `docs/cp7/evidence/p21-rehearsal/`.
  - Ini latihan, bukan receipt P21.

## 13. P19 dikerjakan di cabang Claude (6 Okt 2026 malam)

GPT sudah berhenti menulis, dan owner meminta P19 diselesaikan di cabang ini. Catatan §12 yang menyebut "lane GPT" berlaku untuk saat itu. Rincian lengkap: `docs/cp7/p19/P19_KERNEL_JOB_TRANSPORT_CLAUDE.md`.

### 13.1 Kernel analisis linear (`90615b4c`)

- **Penyebab:** `n` utuh dirujuk dari query per baris, sehingga di-copy ke setiap custom plan PL/pgSQL. Akibatnya waktu tumbuh kuadratik.
- **Perbaikan:**
  - peta dibangun sekali (edge dan `match_results` per target, ETA per posisi, input per sumber, sumber berarah);
  - teks timeline beku GPT tidak diubah dan berjalan dengan `n` berisi subset target itu.
- **Kontrol yang lulus:**
  - `f05-assembly` dan `f05-timeline` (keduanya milik GPT, tidak diubah);
  - `f05-kernel-maps` baru, yang mendeteksi semua mutan tidak setara;
  - analysis152 Native PASS (run 37515388149).
- **Angka CI** (run 37515388418, job p19-assembly):
  - 5.000 target: **3.265 ms**, dibanding pendahulu 247.659 ms dan kandidat GPT 13.152 ms;
  - 1.200 target: 784 ms;
  - 300 target: 202 ms;
  - semuanya byte-identik.
- **Bukti:** `docs/cp7/evidence/p19/kernel-maps-90615b4c/`.

### 13.2 Hitung latar belakang dan transport segmen (`c1f91041`)

**SQL** `planning/analysis-jobs.sql` (skema privat `cp7_analysis_jobs`, dipasang lewat `cp7_analysis_bundle.py` sesudah `analysis-finance.sql`; inventaris katalog di `cp7_analysis_jobs_bundle.py`) menambah lima RPC:
- `erp_cp7_request_analysis_job_v1`, `erp_cp7_run_analysis_job_v1`, `erp_cp7_get_analysis_job_v1`;
- `erp_cp7_read_analysis_manifest_v1`, `erp_cp7_read_analysis_segment_v1`.

**Sifat utama:**
- Job berjalan di bawah batas statement 8 s yang ada. Pembatalan dicatat FAILED/STOPPED.
- Pembacaan RUNNING dilakukan dari `pg_locks` tanpa mengambil kunci.
- Segmen berisi 2.000.000 code point, jadi body-nya ≤ 8 MB.
- Manifest mengikat epoch akses aktor.

**Frontend:**
- `nativeAnalysisTransport.ts` (baru).
- Parameter batas byte opsional di `parseNativeAnalysis`; default tetap 8.000.000.
- Panel diubah aditif:
  - capture biasa tidak berubah;
  - status "Sedang dihitung sejak jam X WIB" muncul sesudah 3 s;
  - fallback segmen untuk hasil di atas 8 MB;
  - tombol "Hitung di latar belakang" dengan pemulihan sesudah reload.
- Ke-18 skrip browser GPT yang memakai capture tetap berlaku.

**Uji lokal:** 1.578/1.578 lulus, build dan security lulus. Suite Native baru `claude-p19-transport.yml` (11 kasus, deklarasi `docs/cp7/p19/P19_TRANSPORT.json`) dan hasilnya dicatat di dokumen P19.

**Perubahan berkas milik GPT (perlu dibaca saat merge):**

| Berkas | Perubahan |
|---|---|
| `scripts/cp7-src/planning/analysis.sql` | Peta kernel. Teks timeline beku tidak berubah. |
| `scripts/cp7_analysis_bundle.py` | Satu berkas SQL tambahan, ditambah panggilan verifikasi job. |
| `scripts/cp7_f05_analysis_probe.py` | Mode `p19_transport`. Mode lain tidak berubah. |
| `src/nativeAnalysis.ts` | Parameter batas opsional. |
| `src/NativeAnalysisPanel.tsx` | Perubahan aditif seperti di atas. |
| `src/types/database.preconnect.ts`, `scripts/check-source-ownership.mjs`, `scripts/check-access-catalog.mjs` | Lima batas RPC baru. |

### 13.3 Yang tetap terbuka (tidak dikarang)

- **Perhitungan lebih dari 8 s** perlu worker database di luar request HTTP (misalnya pg_cron) dan batas waktu job tersendiri. Itu keputusan instalasi/owner untuk P21.
- **Transport segmen** baru ada untuk analisis. Kondisi, laporan, dan klaim belum.
- **Capture aplikasi penuh 5.000 target** di Native nyata dan latensi klik-sampai-tampil di browser belum diukur.
- **Pindaian jalur langsung lama** untuk P20 (fungsi Native yang bisa dieksekusi `authenticated`) ditambahkan sebagai pengamatan baca-saja di latihan P21. Ringkasannya tercetak di log sebagai `P20_DIRECT_PATH_SCAN`, dan tidak mengubah kriteria PASS.

## 14. Pemeriksaan mandiri rumus & keuangan + P19 kernel permintaan (6–7 Okt 2026)

Persiapan audit, **bukan** audit independen. Rincian lengkap: [docs/cp7/SELF_CHECK_FORMULAS_20261006.md](cp7/SELF_CHECK_FORMULAS_20261006.md).

Untuk penggabungan ke `cp7/integration`, perubahan perilaku yang perlu diketahui:
- `finance/analysis.sql`: `formula_version` → `GROWTH_POSITIVE_BASE_AND_GROSS_MARGIN_PP_V2`; pertumbuhan & selisih margin `null` bila basis pendapatan ≤ 0 (sebelumnya tanda terbalik). Parser `financeAnalysisContract.ts` ikut.
- `procurement/correction.sql`: `restate_all` hanya pembalikan dari perintah ini; penghalang kredit supplier memakai netto ≠ 0. Manifest RF 37 native / 43 total (`RF_CREDIT_RESTORED_UNBLOCKS`).
- `invoices/payment-correction.sql`: tolak waktu masa depan dan waktu yang diubah sebelum barang datang.
- `sales/correction.sql`: tolak invoice dengan pembayaran realokasi Native (`CP7_NOTE_REALLOCATED_PAYMENT_REVIEW_REQUIRED`).
- `payroll/roster-write.sql` (kode pekerja dipertahankan), `payroll/settlement-read.sql` (payroll beku dibanding item sendiri).
- `cutting-yield/model-producer.sql`: kernel hanya menerima record batch prospektif terpilih.
- `demand/history.sql` + `planning/history.sql` (`history_build`): bentuk linear, byte-identik dengan `c1f91041` (uji lama-vs-baru di job Shell `p19-assembly`).
- Frontend: refund retur pengganti kosong, saldo kredit pelanggan tidak error, tarif ribuan ambigu ditolak, diskon dibanding eksak, angka demo Keuangan konsisten.
- `demand/estimate.sql`: laju harian `trunc(…,12)` (bukan dibulatkan ke atas) — target tidak lagi +1 pcs; `planning/netting.sql`: posisi WIP sisa 0 bukan suplai.
- `sales/correction.sql` (7 Okt): koreksi yang mengubah harga bersih per pcs baris yang **sudah diretur** ditolak `CP7_NOTE_RETURNED_LINE_PRICE_CHANGED` (refund lama tidak diputar ulang diam-diam). Kasus Native `NOTE_FINANCIAL` diperkuat tanpa mengubah jumlah kasus.
- Frontend (7 Okt): field rupiah 6 desimal (penerimaan, invoice supplier, hitung fisik, koreksi penerimaan) menolak "16.000"/"1,500" (`moneyDecimal`); label "Nilai absensi" menggantikan "Perkiraan upah" (oracle browser P12 attendance ikut label, angka sama); kartu FG v2 menulis "HPP lot saat ini"; pesan Indonesia untuk dua kode penolakan nota.

Oracle lama yang tidak diubah: browser P12 payroll-review masih mencari `.cpay-net` "Bersih payroll" (dipindah oleh F03 E05) — perlu pembaruan oleh pemilik oracle.

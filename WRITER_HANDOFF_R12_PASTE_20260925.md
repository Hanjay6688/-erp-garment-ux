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

- **F3 CONFIRMED (sumber).** `src/accessoryIssue.ts:20` regex UUID ketat (versi [1-8], varian [89ab]) + `list()` gagal total → ID seed CP3 `a1000000-…-0001` ditolak
  (Node: strict false, kanonik true). Tidak berubah sejak 4c61aca (pre-existing). Saudara: `src/laundryQcModel.ts:123`. P3 ketahanan; tetapi ia **menghalangi bukti
  browser ACC-D09** di rantai uji. Pilihan (kalian yang putuskan): perbaikan sempit ke UUID kanonik seperti `src/accessoryService.ts:58`, atau catatan owner bahwa
  halaman nota tanpa bukti browser. Auditor lebih suka perbaikan, lalu ACC-D09 diuji browser di runtime auditor.
- **F4 CONFIRMED + perbaikan CONFIRMED** (run 36171335601 pre_bc: `reversible` NULL, halaman menolak; run 36171347110 after: `false`; pelunasan tunai tetap `true`).
  Ini cacat BB yang lolos putaran 11; laporan auditor dikoreksi. Minta: di §31 tulis F4 sebagai cacat BB (bukan BC) dengan run before/after-mu.

## 2. Yang diminta dari writer (bukan cara perbaikan; itu wewenangmu + owner)
1. **D07 (owner, 18:30Z; `OWNER_DECISIONS_CP6_DRAFT.md`): alarm F2 disetel ulang ke tingkat dokumen, bukan dimatikan.** Spesifikasi (auditor; writer memilih
   implementasinya, bukan di alur uang):
   - baris `MATERIAL_RECOST_GL_STATE_DRIFT` tetap ada, severity tetap ERROR; predikat baru per **bahan × dokumen koreksi** (invoice/koreksi harga):
     `sum(target per gerakan konsumsi) − sum(applied) ≤ 0.01` per dokumen, bukan per gerakan (sen dokumen boleh terkumpul di satu gerakan, T3-A);
   - gerakan `MATERIAL_ADJUSTMENT_ITEM` dibaca dari `material_adjustment_revaluation_facts` (v2.6.20t), bukan dari `material_cost_revaluation_state`;
   - gerakan tanpa recost sama sekali (tidak ada state/fakta padahal dokumennya sudah dikoreksi) **tetap** ditandai; itu inti alarm yang dipertahankan;
   - kontrol negatif wajib di probe: satu state/fakta diubah sengaja di savepoint → alarm harus bunyi; lalu rollback;
   - hapus `STALE_F2` dari `new_findings()` di `cp6_bc_probe.py` sesudah disetel ulang; sampai itu terjadi, tiap kasus recost tetap mengunci
     `books = subledger` dan `V2620T_* = 0`.
   Auditor akan menguji ulang dengan lima jalur `xaudit_12_f1f2.py` (harus diam pada buku benar) + kontrol negatif sendiri (harus bunyi).
2. Sebutkan dampak: `run_v255_…` tidak dipanggil UI dan tidak digate T2/T3 → dampak pada pemeriksaan operator/probe, bukan laporan pengguna. Kalau ada halaman
   "cek data" yang memanggilnya, sebutkan.
3. **BC belum final bagi auditor** sampai ada (dilihat 17:55Z: fe226cf paket T3 27 berkas + d385e7e tabel kasus sudah ada; pins T3 "dari capture berikutnya" belum): head final tertulis, tabel kasus (before/after, 32 + L-cases + 6 state ALL), run CI `cp6-bc-t1-probe.yml` hijau yang bisa
   saya baca, races/HTTP/browser BC di runtime auditor, dan paket T3 27 berkas + rollback BC. Setelah itu saya jalankan ulang regresi (xa1/2/7/8/9, open_1, C0), T2, T3,
   probe BC before/after di workflow pinned milik auditor, kasus BC saya sendiri dari `out/fable_c6_75_oracles_pre_code.md`.
4. Perubahan workflow auditor (fase `pre_bc`, `after` memasang BC) sudah saya baca; runner/modes B1 tidak berubah. Kalau runner/modes berubah lagi, sebut eksplisit.

## 2a. Kompilasi bacaan GPT (`out/gpt_bc_20260926_initial_review.md`, REUSED_GPT_LOG_READ) — disepakati dua auditor
- **GPT-BC-01 (P3 UI, klaim GPT, belum diverifikasi Fable):** kotak cari di tab Stok (`src/ConnectedAccessoryServicePage.tsx` ~41–52, 92–105, 340–355) disimpan
  sebagai satu `filters.query` yang ikut dipakai tab Dokumen, padahal kotaknya tidak tampil di sana; router (`cp6_bc_objects_router.sql` ~198/204) mencocokkan
  dokumen hanya pada nomor/referensi/PJ/alasan → dokumen baru "hilang" sampai pengguna kembali ke Stok dan menghapus filter. Minta: pisahkan query per tab atau
  tampilkan/hapus filter saat pindah tab; skrip browser FILL_POST/REVERSE reset query dulu. Diuji kedua auditor lewat browser lintas tab.
- **ACC-C12 belum lengkap (GPT, Fable setuju):** probe C12 baru membuktikan penerimaan fisik baru menambah 10; oracle juga melarang dokumen susulan untuk
  **barang yang sama** (5 diketahui / 3 pending) menambah stok kedua kali. Tambah kasus identitas/lineage barang sama + kontrol positif pembelian baru; bila
  sistem tidak punya identitas sumber, tandai HOLD/UNVERIFIED dan minta kebijakan eksplisit.
- **ACC-D09 (halaman nota) belum terbukti** sampai F3 diputus (lihat §1). Jangan label PASS.
- **Browser BC `FILL_POST_AND_REVERSE` masih INCOMPLETE** pada dua run (5e1ae83: format jam; e21d15b: tombol `Buka BCA-…` tidak muncul = kemungkinan GPT-BC-01).
  Ulangi pada head yang sama sesudah perbaikan; run lama tetap apa adanya.
- **T3/rollback (bacaan GPT):** paket 27 berkas e21d15b pins `equal=true` (run 36170892085); rollback 0746c33 siklus (run 36171280254) belum selesai saat dibaca;
  advisor +92 INFO `rls_enabled_no_policy` (REVIEW_REQUIRED, naik dari 75). Semua bukti writer; auditor akan rerun sendiri.

## 2b. Putaran 12 BC — hasil auditor pada head §31 (tool 23abac1, produk 27e1a05); rincian `out/fable_r12_results.md` §9
- Gate auditor sendiri: T2 36177884812 ✓, T3 27 berkas 36177895962 ✓, rollback 36177907418 ✓, CodeQL 36177919063 ✓.
- Regresi auditor (fase after): xa1/xa2/xa7/xa9/open_1 semua PASS; xa8 12 + 2 CE beku (T3-A); C0 24 + 1 INCOMPLETE grant (sama r11). **Tidak ada regresi.**
- F1: perbaikan CONFIRMED natively (run 36178015645, baris harga manual lewat fasad → detektor diam); badan v265 BC = baseline + predikat itu saja (sidik jari
  run 36178552990). F2: masih bunyi, menunggu D07 (§2.1).
- Probe BC PLAN 44 di workflow pinned auditor: after 44/44 PASS (36178145305). Kasus adversarial auditor (isi pos sebelum terima, pemakaian > pos, qty tidak
  valid ×6, pembalikan ganda) semuanya ditolak/pulih dengan benar; satu FAIL di run 36178552990 adalah pembanding auditor, bukan produk; **rev2 run 36179524130: after 49/49 PASS, before sesuai rencana**.
- **Disposisi T2 `ACCESSORY_CONNECTED_ZERO`: EXPECTED_CHANGE** (ERP-DEC02, M:5023 B). Kasus lama tetap INCOMPLETE tercatat; tambahkan kasus pengganti di harness T2
  yang mengunci `BC_FREE_REQUIRES_POLICY`, tandai kasus lama *superseded* di tabel kasus.
- Pengecualian pembanding rollback (§31.3 butir 7): ditinjau, **diterima** (sempit: `set_at` / `id,set_at` dua tabel seed, hanya cek reinstall).
- Race tambahan auditor (run 36182433079, 7/7): pemakaian dari pos vs pembalikan isi pos, dua pembalikan dokumen sama (sesi 2 `STALE_VERSION`), dua kredit lot sama
  (`BC_QTY_EXCEEDS_BUCKET`), semuanya fail-closed dan stok/lot tepat; browser: perbaikan filter tab Dokumen (27e1a05) terverifikasi. Tidak ada temuan baru.
- Masih terbuka sebelum BC dianggap tuntas oleh auditor: (a) D09 browser halaman nota hijau (F3 diputus dulu), (b) D07 alarm F2, (c) ACC-C12 key baru = pertanyaan owner.

## 3. Sudah dicek OK
D06/T3 tercatat verbatim (ab4ea6d). Probe enam state ALL era BA ada (4b1bd66) — diuji di CI BC. Paket rilis DB identik 4c61aca..95353aa.

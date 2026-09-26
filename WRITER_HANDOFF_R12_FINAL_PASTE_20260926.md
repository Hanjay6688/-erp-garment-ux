# Handoff auditor → writer (Opus), putaran 12 FINAL — BC, 26 Sep 2026; redaksi 08:07 WIB — TEMPEL KE WRITER
Dari: Fable + GPT (kompilasi bersama; tiga penajaman redaksi GPT setelah kompilasi). Sumber: cabang `audit/cp6-final-20260924-gpt-a0bcadf` → `out/fable_r12_results.md` (§7–§14), `out/gpt_bc_native_followup_run2.md`,
`audit/CP6_COMBINED_INDEX.json` kunci `fable_round12_bc`. Menggantikan `WRITER_HANDOFF_R12_PASTE_20260925.md` (isi lengkapnya tetap di sana).
Identitas yang diaudit: §31 (b7a1a2b) → produk BC = `src` + paket rilis pada **27e1a05**, paket DB **e21d15b** (27 berkas), alat uji hingga **caeff6f**. CP6 tetap HOLD, `production_go=false`.

## 1. BC: kasus yang dinyatakan PASS lulus pada cakupan yang diuji; pengecualian tetap terbuka
Hasil berikut berasal dari run auditor yang berbeda dan tetap berlabel menurut pemilik skenarionya. Ini **bukan ACCEPT penuh atas 39 ID ACC** atau izin production GO; status GBC-1/GBC-2 dan HOLD historis tidak ikut berubah.

| Uji | Run | Hasil |
|---|---|---|
| T2 · paket T3 27 berkas · rollback cycle · CodeQL | 36177884812 · 36177895962 · 36177907418 · 36177919063 | job hijau pada cakupan masing-masing; HOLD/COUNTEREXAMPLE/INCOMPLETE per kasus historis tetap tercatat |
| Regresi auditor 8 skenario (fase after) | 36177930596 … 36178015645 | identik dengan putaran 11 (xa8 2 CE beku T3-A; C0 1 INCOMPLETE grant skenario) |
| Probe BC PLAN 44 + 5 kasus Fable, workflow pinned auditor | 36179524130 | before sesuai rencana; **after 49/49 PASS** |
| Race Fable ×6 (pakai-vs-balik, dua pembalikan `STALE_VERSION`, dua kredit `BC_QTY_EXCEEDS_BUCKET`) + browser filter lintas tab | 36182433079 | 7/7 PASS; perbaikan 27e1a05 terverifikasi di browser |
| F1 fix | 36178015645 + sidik jari 36179524130 | baris harga manual tidak lagi ditandai; badan v265 = baseline + predikat itu saja |
| F4 fix (cacat BB) | 36171335601 (pre_bc) / 36171347110 (after) | NULL → false; pelunasan tunai tetap true |
| GPT mandiri GBC-1/GBC-2 | 36182902112, job 108229314210 | GBC-1 **INCOMPLETE** (identitas fisik lintas key belum terbukti); GBC-2 **COUNTEREXAMPLE pada fixture klon**, relevansi cutover belum diketahui. Browser RUN_COMPLETE, job keseluruhan merah; lihat §2 butir 3–4. |

Disposisi yang kamu minta: **`ACCESSORY_CONNECTED_ZERO` = EXPECTED_CHANGE** (ERP-DEC02, M:5023 B); **pengecualian pembanding rollback baris seed = DITERIMA** (sempit, terdokumentasi).

## 2. Yang masih terbuka — tugas writer sekarang (urut)
1. **D07 — setel ulang alarm F2 `MATERIAL_RECOST_GL_STATE_DRIFT` ke tingkat dokumen.** Owner membolehkan alarm dimatikan bila tidak berguna dan menerima setel ulang bila masih bermanfaat; pilihan setel ulang adalah **pembacaan/rekomendasi auditor**, dicatat terbuka di `OWNER_DECISIONS_CP6_DRAFT.md` §D07. Rumus berikut **usulan teknis untuk diverifikasi**, bukan rumus yang diratifikasi owner kata demi kata.
   Pertahankan baris dan severity ERROR; uji predikat per bahan × dokumen koreksi: `|Σ target gerakan konsumsi − Σ applied| ≤ 0.01` per dokumen (sen boleh terkumpul di satu gerakan,
   T3-A); gerakan `MATERIAL_ADJUSTMENT_ITEM` dibaca dari `material_adjustment_revaluation_facts`; gerakan yang sama sekali tidak ter-recost tetap ditandai; probe wajib
   punya kontrol negatif (rusak satu state/fakta di savepoint → alarm bunyi → rollback); hapus `STALE_F2` dari `new_findings()`. Auditor menguji ulang dengan
   `xaudit_12_f1f2.py` (harus diam pada buku benar) + kontrol negatif sendiri.
2. **Kasus pengganti T2** untuk `ACCESSORY_CONNECTED_ZERO`: kunci penolakan `BC_FREE_REQUIRES_POLICY`; kasus lama tetap tercatat INCOMPLETE dan ditandai *superseded* di tabel kasus.
3. **F3 — D08 (owner, 26 Sep, `OWNER_DECISIONS_CP6_DRAFT.md`): perbaikan sempit opsi (b) DIIZINKAN dengan syarat.** Owner membedakan validasi format ID dari keamanan
   akses; klaim "melanggar guard keamanan" harus ditunjukkan dari kode, bukan disimpulkan. Yang diminta: (1) pasang kembali dua suntingan yang kamu batalkan:
   `src/accessoryIssue.ts:20` dan `src/laundryQcModel.ts:123` menerima UUID kanonik 8-4-4-4-12 (pola yang sudah kamu pakai di `src/accessoryService.ts:58`); (2) diff
   hanya menyentuh regex itu, **tidak ada** baris role/izin/grant yang berubah, dan tulis pernyataan itu + diff di §32; (3) hapus penonaktifan seed di flow browser D09/Laundry
   supaya halaman diuji dengan mandor non-RFC aktif; (4) kalau kamu masih menilai ada aspek keamanan yang melemah, tunjukkan barisnya, jangan batalkan diam-diam.
   Auditor memverifikasi diff dan menguji ulang browser (non-RFC aktif + kontrol v4).
4. **ACC-C12 kunci baru** (batasmu `limit.new_custody_key=ACCEPTED`, direproduksi GPT: 3→6→9): siapkan **dua opsi ringkas untuk owner** — (a) rujukan lembar hitung/lot wajib
   pada tiap item pending (kunci baru tanpa rujukan ditolak), (b) kontrol manual gudang + catatan di lampiran C6. Sampai owner memilih: ACC-C12 PARTIAL.
5. **§32** untuk BD: head final tertulis, tabel kasus BD → ID C6/ALL (LAU-05b, LAU-DEC01–06, W05 fisik) → oracle pra-kode auditor (`out/fable_c6_75_oracles_pre_code.md`
   bagian LAU, `audit/scenarios/r13_bd/GPT_BD_ORACLE.md`), run CI per gate (probe BD before/after, races/HTTP/browser di runtime auditor, T2, T3 **28 berkas** + rollback,
   CodeQL), dan fase `pre_bd` di `cp6-auditor-scenario.yml` (pola `pre_bc`). **Oracle dan skenario BD dari kontrak boleh disusun serta di-hash sekarang; penerimaan native/final BD menunggu head, fase, dan bukti §32 yang terpin.**

## 3. Konvensi (tidak berubah)
- Produk = `src` + `supabase/release` + `supabase/migrations`; berkas `supabase/dev/*` bukan produk sampai masuk paket. Sebut hash produk dan hash alat terpisah di §32.
- Jangan mengecualikan detektor diam-diam; setiap pengecualian ditulis sebagai temuan terbuka dengan disposisi.
- Hasil lokal bukan bukti; run CI dengan nomor run/job. Auditor tidak pernah melabel ulang run yang sudah beku.
- Kalau writer berganti (Opus → GPT), syarat auditor ada di `HANDOVER_WRITER_OPUS_TO_GPT_20260925.md`.

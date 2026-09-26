# Handoff auditor → writer (Opus), putaran 12 FINAL — BC, 26 Sep 2026 ~03:20 WIB — TEMPEL KE WRITER
Dari: Fable + GPT (satu versi, disepakati). Sumber: cabang `audit/cp6-final-20260924-gpt-a0bcadf` → `out/fable_r12_results.md` (§7–§14), `out/gpt_bc_native_followup_run2.md`,
`audit/CP6_COMBINED_INDEX.json` kunci `fable_round12_bc`. Menggantikan `WRITER_HANDOFF_R12_PASTE_20260925.md` (isi lengkapnya tetap di sana).
Identitas yang diaudit: §31 (b7a1a2b) → produk BC = `src` + paket rilis pada **27e1a05**, paket DB **e21d15b** (27 berkas), alat uji hingga **caeff6f**. CP6 tetap HOLD, `production_go=false`.

## 1. BC: bersih pada cakupan yang diuji (semua run auditor sendiri)
| Uji | Run | Hasil |
|---|---|---|
| T2 · paket T3 27 berkas · rollback cycle · CodeQL | 36177884812 · 36177895962 · 36177907418 · 36177919063 | semua hijau |
| Regresi auditor 8 skenario (fase after) | 36177930596 … 36178015645 | identik dengan putaran 11 (xa8 2 CE beku T3-A; C0 1 INCOMPLETE grant skenario) |
| Probe BC PLAN 44 + 5 kasus Fable, workflow pinned auditor | 36179524130 | before sesuai rencana; **after 49/49 PASS** |
| Race Fable ×6 (pakai-vs-balik, dua pembalikan `STALE_VERSION`, dua kredit `BC_QTY_EXCEEDS_BUCKET`) + browser filter lintas tab | 36182433079 | 7/7 PASS; perbaikan 27e1a05 terverifikasi di browser |
| F1 fix | 36178015645 + sidik jari 36179524130 | baris harga manual tidak lagi ditandai; badan v265 = baseline + predikat itu saja |
| F4 fix (cacat BB) | 36171335601 (pre_bc) / 36171347110 (after) | NULL → false; pelunasan tunai tetap true |
| GPT mandiri GBC-1/GBC-2 | 36182902112 | konsisten dengan Fable (lihat §2 butir 3–4) |
Disposisi yang kamu minta: **`ACCESSORY_CONNECTED_ZERO` = EXPECTED_CHANGE** (ERP-DEC02, M:5023 B); **pengecualian pembanding rollback baris seed = DITERIMA** (sempit, terdokumentasi).

## 2. Yang masih terbuka — tugas writer sekarang (urut)
1. **D07 (owner, tertulis di `OWNER_DECISIONS_CP6_DRAFT.md`): alarm F2 `MATERIAL_RECOST_GL_STATE_DRIFT` disetel ulang ke tingkat dokumen, bukan dimatikan.**
   Baris dan severity ERROR tetap; predikat per bahan × dokumen koreksi: `|Σ target gerakan konsumsi − Σ applied| ≤ 0.01` per dokumen (sen boleh terkumpul di satu gerakan,
   T3-A); gerakan `MATERIAL_ADJUSTMENT_ITEM` dibaca dari `material_adjustment_revaluation_facts`; gerakan yang sama sekali tidak ter-recost tetap ditandai; probe wajib
   punya kontrol negatif (rusak satu state/fakta di savepoint → alarm bunyi → rollback); hapus `STALE_F2` dari `new_findings()`. Auditor menguji ulang dengan
   `xaudit_12_f1f2.py` (harus diam pada buku benar) + kontrol negatif sendiri.
2. **Kasus pengganti T2** untuk `ACCESSORY_CONNECTED_ZERO`: kunci penolakan `BC_FREE_REQUIRES_POLICY`; kasus lama tetap tercatat INCOMPLETE dan ditandai *superseded* di tabel kasus.
3. **F3 (guard UUID halaman nota, `src/accessoryIssue.ts:20`).** Rumusan bersama auditor: P3 pada produk dengan ID buatan aplikasi; **naik P2 bila** data cutover memuat
   kontraktor/mandor aktif ber-ID non-RFC. Minta: (a) inventaris **baca-saja** ID kontraktor aktif pada data cutover (di drill T3 atau salinan yang diizinkan; auditor tidak
   menyentuh hosted), catat hasilnya di §32; (b) perbaikan sempit ke UUID kanonik (seperti `src/accessoryService.ts:58`) supaya bukti browser D09 tidak bergantung pada
   penonaktifan seed di klon. Keputusan akhir di owner/writer; auditor menyarankan (b).
4. **ACC-C12 kunci baru** (batasmu `limit.new_custody_key=ACCEPTED`, direproduksi GPT: 3→6→9): siapkan **dua opsi ringkas untuk owner** — (a) rujukan lembar hitung/lot wajib
   pada tiap item pending (kunci baru tanpa rujukan ditolak), (b) kontrol manual gudang + catatan di lampiran C6. Sampai owner memilih: ACC-C12 PARTIAL.
5. **§32** untuk BD: head final tertulis, tabel kasus BD → ID C6/ALL (LAU-05b, LAU-DEC01–06, W05 fisik) → oracle pra-kode auditor (`out/fable_c6_75_oracles_pre_code.md`
   bagian LAU, `audit/scenarios/r13_bd/GPT_BD_ORACLE.md`), run CI per gate (probe BD before/after, races/HTTP/browser di runtime auditor, T2, T3 **28 berkas** + rollback,
   CodeQL), dan fase `pre_bd` di `cp6-auditor-scenario.yml` (pola `pre_bc`). Sebelum itu auditor tidak memulai audit BD.

## 3. Konvensi (tidak berubah)
- Produk = `src` + `supabase/release` + `supabase/migrations`; berkas `supabase/dev/*` bukan produk sampai masuk paket. Sebut hash produk dan hash alat terpisah di §32.
- Jangan mengecualikan detektor diam-diam; setiap pengecualian ditulis sebagai temuan terbuka dengan disposisi.
- Hasil lokal bukan bukti; run CI dengan nomor run/job. Auditor tidak pernah melabel ulang run yang sudah beku.
- Kalau writer berganti (Opus → GPT), syarat auditor ada di `HANDOVER_WRITER_OPUS_TO_GPT_20260925.md`.

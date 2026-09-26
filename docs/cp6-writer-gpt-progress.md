# CP6 — progres writer GPT, takeover 27 September 2026 WIB

CP6 HOLD · audit_complete=false · production_go=false.

## Otorisasi dan identitas
- Owner meminta: "takeover writer, finalize BD kalo masih ada yang kurang, selesain BE. Audit independen akan dilakukan chat box lain".
- Writer aktif: GPT. Hasil setelah takeover adalah bukti writer; penerimaan independen milik sesi auditor lain.
- Cabang kerja: `claude/new-session-deapao`; head saat takeover `e020bebcf40e07e8a74d93715820555ca2d5189b`.
- Handoff sebelumnya: `docs/cp6-au-r1-handoff.md` §34/§34.9; handover auditor `HANDOVER_WRITER_OPUS_TO_GPT_20260925.md` pada cabang audit.
- Konsep BE: `out/gpt_be_concept_map_20260926.md`, audit commit `9aa7c766ac0d23f403fc458ce513193716c6bd1e`. Konsep mengacu kontrak; tidak merupakan implementasi/acceptance.
- Main, kompetisi, hosted/legacy/production tidak menjadi target pekerjaan ini. Kebijakan riil owner tidak diisi dari nilai fixture.

## Fase aktif dan rencana
1. **AKTIF: intake takeover dan finalisasi BD.** Baca handoff/sumber, verifikasi log T36 pada 36226363180/job 108361073793, identitas paket/rollback, serta kekurangan §34.8.
2. Lengkapi bukti browser LAU-DEC04 `ALLOW_PENDING` (handoff hanya membuktikan probe/unit). Bila ada cacat, perbaiki dengan expected dari keputusan owner; jangan mengubah hasil beku.
3. BE-01 konversi/ganti merek FG + aksesori aktual/pulih; BE-02 rework ke SKU baru; BE-03 celup ulang BS dengan jasa/biaya yang sah; BE-04 ALL-C04 kain kantong lintas cutover. Tetapkan transisi dan oracle sebelum implementasi.
4. Lengkapi probe before/after, race/HTTP/browser, T2, paket T3 dan rollback BE serta CodeQL. Hasil lokal dilabel lokal; bukan bukti runtime CI.
5. Handoff writer dengan commit produk/alat, hash, run/job/per-kasus dan batas untuk auditor independen.

## Status intake
| Bagian | Status |
|---|---|
| BD T36 pembanding + tautan SQL | BELUM dibaca ulang log oleh writer GPT; klaim writer lama 8/8 browser pada run baru |
| BD paket T3 28 berkas dan rollback | BELUM diverifikasi GPT; handoff mencatat 36222100215 dan 36222384316 (139/139) |
| BD ALLOW_PENDING browser | BELUM; gap bukti dinyatakan §34.4 |
| BE-01/02/03/04 | BELUM dibangun pada snapshot takeover |
| Penerimaan independen | HOLD; tidak dikerjakan sesi writer ini |

## Koreksi oracle yang wajib dibawa
`out/gpt_all_c04_oracle_errata_20260926.md` di audit commit `9aa7c76` mengoreksi oracle GPT lama: kain kantong mula-mula menjadi beban, tetapi alokasi periode yang disahkan memindahkan nilai ke WIP/FG/COGS (M:466–511/P:406–439), tanpa pengeluaran stok kedua. Jangan memakai expected lama bahwa seluruh alokasi tetap di luar HPP. Hasil beku tetap.

## LANGKAH BERIKUTNYA
Baca berkas rujukan dan sumber BD/konversi/rework/kain kantong; ambil log run/job di atas; tambah kasus browser ALLOW_PENDING; tulis pemetaan implementasi BE beserta tabel kasus dan mulai family. Setelah tiap fase/run/temuan, append checkpoint di sini dan commit/push. Jangan menandai seluruh BD atau BE lulus hanya dari ringkasan handoff.

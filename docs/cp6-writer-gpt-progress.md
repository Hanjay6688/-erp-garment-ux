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

## Checkpoint BD-1 — alat uji tambahan siap, belum ada hasil baru
- Takeover tersimpan di `24d4550581077d3a4ae068c77aea7a24d46e02eb`. Git baca tersedia; push dilakukan melalui connector GitHub karena terminal tidak memiliki credential tulis.
- Log 36226363180/job 108361073793 dibaca: browser 8/8 PASS, T36 tujuh cek true, komponen GAR/SPR tertaut, respons harga 10000 incomplete → 13000 complete, D12/DEC06 PASS. Label tetap bukti writer.
- Job T3 36222100215: install 108349157867, capture 108349157809, browser 108349157892 semuanya success. Job rollback 36222384316/108349950711 success. Identitas produk di log T36 = `231f47b1b6c4306cd9f49e0fd66069d9e5a1fa78`.
- Ditambah `cp6_bd_completion_browser.mjs` + fixture native khusus database `cp6_auditor_browser`: 10 PCS, 2 sudah terjual dengan harga SPR unknown; UI harus menampilkan HPP belum final dan setelah owner mengisi 1000/PCS, lot +10000, FG +8000, COGS +2000, snapshot sale tidak berubah, blocker hilang. Pembuatan sale adalah setup native, bukan bukti klik halaman penjualan (masih demo).
- `cp6_writer_dispatch.json` memilih satu batch writer pada push; workflow auditor yang sama tetap menerima dispatch auditor seperti sebelumnya. Selftest grup tidak diubah; skenario race/HTTP BD dipakai ulang tanpa perubahan.
- Python compile/JS syntax/YAML parse lokal lulus. **BELUM** ada hasil runtime baru. Langkah berikut: commit/push batch; catat run/job, baca per-kasus, perbaiki jika gagal. Selagi CI berjalan, lanjut desain/implementasi BE.

## Run BD-1 berjalan
- Commit alat `01149217d4c2cefbbe4265b44826cdd46dc52a20`; run `36263717916`.
- Job skenario `108464257310` berjalan; job selftest `108464257515` success saat checkpoint. Browser baru belum memiliki verdict.
- SHA256 browser `73927e764208d850bc1368bf6410f5b9c2df17228c4dd1450a8556de58e2b588`; fixture `53a714cb359c9ddee60a4fda82536ebe65a9c15d763815f9b1d1d98f09021b0c`; Python wrapper `214890ffad1edd7c605441f3e9ff6d9333af4fc8dd17e8fc0a3229b268cedaa5`.
- Pembacaan log paket/rollback: install 28 keluarga PASS; rollback cycle PASS per kasus. Gate/primary/drill akhir masih akan disalin dari ringkasan log, bukan dari status job semata.
- Native konversi existing menolak biaya tanpa sumber dan stok non-PO. BE wajib memberi alur sumber biaya lengkap sebelum memperluasnya. Partial rework existing belum menghasilkan FG; native COMPLETE GOOD+BS=sent menghasilkan lot GOOD asal, yang dapat dijadikan sumber konversi atomik. Pekerjaan analisis ini bukan hasil BE.

## Hasil BD-1 dan koreksi fixture
- Run `36263717916`, job skenario `108464257310`: **INCOMPLETE**, selftest `108464257515` PASS. Browser gagal saat fixture `create`, sebelum membuat user Auth atau membuka UI: helper native mencoba `erp.current_app_role()` dengan role authenticated tanpa USAGE schema erp. Ini kegagalan setup uji, bukan hasil produk.
- Rev2 memberi USAGE hanya selama transaksi setup pada database salinan `cp6_auditor_browser`, lalu mengembalikan hak persis seperti semula dan mengassert restorasinya sebelum commit. Browser tidak mendapat grant tambahan. Operasi baca di-rollback. Expected angka/UI tidak berubah; run lama tetap INCOMPLETE.
- Desain BE disimpan pada `docs/cp6-be-implementation-plan.md`. Berikutnya: run BD rev2, lanjut implementasi konversi BE dan sumber biaya; family belum lengkap sampai empat alur dan seluruh gate writer selesai.

## Hasil BD-2 — gap browser ALLOW_PENDING terjawab
- Run baru `36264421663`, commit `3be185acdbe75d70e3d74ebc884bd74912baad24`, job skenario `108466247346`: **RUN_COMPLETE**. Selftest `108466247334`: PASS.
- Race 9/9 PASS; HTTP Auth 3/3 PASS; browser `BD_COMPLETION:ALLOW_PENDING_VISIBLE_AND_BROWSER_RECOST` PASS, sembilan cek true. Sebelum pengisian: nilai lot 50100, FG 40080, COGS 10020; sesudah pengisian: 60100/48080/12020. Snapshot penjualan tetap 5010 per PCS, NOT_FINAL menjadi RECOSTED, blocker harga hilang. 0 console error, satu user Auth dibersihkan; primary_unchanged=true, clone_remaining=0.
- Batas bukti tetap: penjualan adalah fixture melalui command native; browser membuktikan tampilan pending dan pengisian harga. Ini tidak mengklaim halaman penjualan demo telah tersambung.
- Log paket BD `36222100215`/`108349157867`: 28 keluarga terpasang, drill RESTORED_SAME_MEANING. Log rollback `36222384316`/`108349950711`: cycle PASS, primary_unchanged=true. Produk BD tidak diubah dalam dua run tambahan ini.

## Tahap BE-1 — fondasi dipush untuk probe sebelum/sesudah
- `cp6_be_objects_conversion.sql`: facade izin + idempotensi, preview kapasitas bertanggal, satu lot sumber eksplisit, target model/ukuran tetap, hasil native conversion, inverse dan daftar bongkaran pending. Guard biaya tanpa sumber dan non-PO masih berlaku pada tahap ini; belum lengkap.
- Builder memakai substitusi tepat-sekali pada fungsi AC, bukan salinan bebas. Registry layer memverifikasi teks BE yang menggantikan fungsi predecessor. Workflow T1 baru memakai pin bootstrap/harness identik dengan BD; tidak mengubah cabang kompetisi.
- BELUM: sumber biaya/recovery, non-PO, BE rework/redye, ALL-C04, UI, race/HTTP/browser BE, T2, paket 29/rollback/CodeQL. Tidak ada hasil BE yang diklaim lulus.
- LANGKAH BERIKUTNYA: baca run T1 BE-1 (dua kasus fondasi), perbaiki hasil bila perlu, kemudian sambungkan biaya aktual BC dan recost transitive, dilanjutkan rework/redye dan ALL-C04. Independen tetap sesi auditor lain.

## Hasil BE-1 / tahap BE-2 (belum lengkap)
- Commit `7b0ca8c58ce4a1dee18384d79d470e96a9252728`; BE T1 run `36265003501`. Before job `108467891536` success (jalur BE belum tersedia); after job `108467891652` **INCOMPLETE sebelum instalasi BE**, guard predecessor AQ `PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE` menghentikan setup. Guard tidak diubah; ini tidak memberi verdict pada kasus produk BE.
- Workflow terpicu lain selesai success: BD T1 `36265003351`, BA T1 `36265003386`, BB T1 `36265003314`, paket BD T3 `36265003344`, runtime BD tambahan `36265003327`. Status ini dari Actions; rincian per-kasus baru tidak menggantikan bukti BD-2 yang sudah dibaca.
- Tahap berikut menambahkan sumber biaya BC aktual dan recovery tertaut: jurnal reklasifikasi sumber, fakta perubahan nilai append-only, HPP turunan, hook invoice/recost material dan reversal BC. Detektor sumber biaya dan lineage ikut menghitung sumber BE, tanpa mengecualikan kasus dari detector.
- Ditambah kasus pemakaian enam aksesori @2,00: stok turun 6 sekali, HPP tujuan +12,00, beban tidak rangkap; sumber harus dibalik sebelum konversi, lalu nilai/qty kembali. Expected dikunci sebelum run; belum punya hasil.
- Validasi lokal hanya parser SQL/PLpgSQL (26 fungsi) dan Python compile; PostgreSQL lokal tidak tersedia pada lingkungan ini. Bukti native tetap CI. BE masih NOT_READY; non-PO, rework/redye, ALL-C04, UI dan gate akhir belum selesai.

## Hasil BE-2 dan perbaikan berikutnya
- Commit `bdccc2b200e382da56158ebb8eac0373cf4435ab`; run `36265435090`: before job `108469087334` success; after job `108469087464` INCOMPLETE. Ketiga kasus sudah masuk runtime BE: roundtrip INCOMPLETE, refusal FAIL, biaya INCOMPLETE. Penyebab yang sama: expected revision berbeda antara sesi WIB dan wrapper UTC.
- Cacat writer BE ditemukan: hash source_revision menserialisasi timestamptz menurut zona sesi. Diperbaiki menjadi epoch; guard STALE_VERSION tetap. Hasil lama tidak diubah.
- Tahap selanjutnya menambahkan konversi non-PO/opening: admission eksplisit pada sumber BE, HPP turunan berakar, transfer nilai antar-SKU dan pembukuannya, recost/inverse tertaut. Jalur non-PO tanpa sumber BE tetap ditolak. Probe tambahan 10 PCS @10,01, konversi 6: sumber 40,04, tujuan 60,06, inverse kembali 100,10.
- Run fase baru akan menguji empat kasus; parser SQL/PLpgSQL lokal lulus (35 fungsi). Masih belum merupakan family lengkap.
- Job terpicu pada `7b0ca8c`: BD T1 before/after `108467891098`/`108467890999`; BA `108467891108`/`108467891360`; BB `108467891021`/`108467891228`; T3 browser/capture/install `108467890938`/`108467891109`/`108467891182`; runtime BD/selftest `108467891016`/`108467891170`. Semua Actions success; log rinci hanya yang disebut telah dibaca di atas.

## Hasil BE-3 dan sambungan rework
- Commit `f2b4770dcac3fec2f82f0322483b1b195fc77011`, run `36265833090`: before job `108470196470` success. After `108470196642`: roundtrip pilihan lot/replay/inverse **PASS**, guard kapasitas/stale/biaya tanpa sumber **PASS**; penggunaan aksesori dan non-PO **INCOMPLETE**.
- Dua cacat kode writer BE: adapter penggunaan meneruskan timestamp hasil serialisasi UTC ke parser BC yang mewajibkan WIB; alias `b` pada SQL baru berbenturan dengan variabel record native. Keduanya diperbaiki tanpa mengubah oracle.
- Ditambahkan binding SKU tujuan pada order rework baru; COMPLETE native membuat GOOD sumber lalu mengonversi lot tersebut atomik, partial tetap tanpa output. Inverse menyelesaikan konversi turunan sebelum inverse rework. Target masuk registry sumber identitas. Probe baru memakai 4 BS → 2 GOOD SKU baru + 2 BS; replay dan inverse harus tepat sekali.
- Tahap BE sekarang masih pengembangan T1. Paket rilis masih AC..BD 28 berkas; **jangan memasang SQL dev ini ke hosted**. Masih harus selesai: celup ulang berbiaya/invoice, ALL-C04, UI seluruh alur, kasus biaya/recost/recovery negatif, race/HTTP/browser, T2 dan T3 29 berkas + rollback + CodeQL.
- LANGKAH BERIKUTNYA: baca run baru lima kasus BE, selesaikan error yang tersisa; sambungkan jasa celup ke dokumen vendor BD, lalu adapter kain kantong lintas cutover. Status seluruh family tetap NOT_READY dan CP6 HOLD.

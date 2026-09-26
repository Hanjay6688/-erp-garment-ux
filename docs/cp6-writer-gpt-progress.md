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
1. **SELESAI: intake takeover dan finalisasi BD writer.** Baca handoff/sumber, verifikasi log T36 pada 36226363180/job 108361073793, identitas paket/rollback, serta kekurangan §34.8.
2. Lengkapi bukti browser LAU-DEC04 `ALLOW_PENDING` (handoff hanya membuktikan probe/unit). Bila ada cacat, perbaiki dengan expected dari keputusan owner; jangan mengubah hasil beku.
3. **AKTIF: implementasi family BE.** BE-01 konversi/ganti merek FG + aksesori aktual/pulih; BE-02 rework ke SKU baru; BE-03 celup ulang BS dengan jasa/biaya yang sah; BE-04 ALL-C04 kain kantong lintas cutover. Tetapkan transisi dan oracle sebelum implementasi.
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

## Hasil BE-4 — lima kasus fondasi native PASS
- Commit `398044fcc9538f11208955493acb06ec78606737`, run `36266198940`, before job `108471224169`, after job `108471223837`; kedua job success. Log after dibaca per kasus: selected-lot/replay/inverse, capacity/stale/unsourced-cost, actual-accessory-cost, opening/non-PO, dan rework-new-SKU masing-masing PASS; full_boundary_restored=true untuk kelimanya.
- Nilai yang terbukti: penggunaan aksesori +12,00 tepat sekali, non-PO 40,04 sumber +60,06 tujuan dan inverse; rework 4 BS → 2 GOOD target +2 BS dengan replay/inverse atomik.
- Ini lima kasus fondasi, **bukan BE lengkap**. Celup ulang berbayar/invoice, ALL-C04, UI, negatif/recost lanjutan dan seluruh gate akhir masih harus diselesaikan. LANGKAH BERIKUTNYA: adapter jasa rework sebagai sumber invoice nyata, lalu pembuka kain kantong, kemudian UI dan paket.

## Tahap BE-5 — sumber jasa celup dan invoice (belum diuji native)
- Ditambahkan sumber jasa nyata per order rework, vendor/proses/tarif waktu kirim, pilihan UNKNOWN eksplisit dan penetapan harga pertama append-only. Rework gratis existing tidak memperoleh biaya celup.
- Invoice BD mendapat sumber ketiga `rework_service_id`, tetap memakai jurnal/pembayaran/koreksi native BD. Kapasitas GOOD/BS dari hasil rework, estimasi dilepas proporsional dengan residual terakhir; selisih PRODUCT_COST masuk sumber rework dan HPP lot tepat, lalu turunan/COGS. Cancel/inverse ditolak bila invoice sumber masih aktif. Harga unknown masuk close blocker dan kebijakan penjualan ALLOW_PENDING/REFUSE.
- Dua expected baru: 4 PCS @50 = 200, satu dijual, invoice240 → biaya240, akrual0, FG+30/COGS+10, snapshot sale tetap; UNKNOWN → 50 menambah200 tepat sekali dan menghapus blocker. Tarif tidak dibedakan menurut ukuran. Belum ada verdict runtime.
- Parser lokal 67 fungsi PL/pgSQL lulus. Struktur invoice berubah sehingga rollback BE wajib merekam kolom/constraint/index tambahan, tidak sekadar drop tabel BE. Belum masuk paket 29.
- Berikutnya: run tujuh kasus, baca/fix; lanjut adapter ALL-C04, UI, race/HTTP/browser, T2/T3/rollback/CodeQL. BE masih NOT_READY.

## Hasil BE-5 dan UI konversi tahap pertama
- Commit `b86c66deef33ae04fbae8164c2c52a626a375e81`, run `36267009395`; before job `108473508276`, after `108473508503`, kedua job success. Log after: **7/7 PASS**. Lima kasus sebelumnya tetap PASS; invoice jasa nyata 200→240 sesudah 1/4 terjual: FG+30, COGS+10, akrual0, AP+240, snapshot sale tetap dan kapasitas invoice ditolak. Unknown→harga50: nilai+200, blocker hilang, replay sekali, overwrite ditolak.
- UI Ganti Merek mulai tersambung: pilihan lot/lokasi, pencarian dan paging SKU tujuan, preview server, perintah dengan recovery global, histori dan pembatalan, pemakaian aksesori aktual, rencana bongkaran tanpa stok. Parser menerima UUID kanonik, uang berupa teks, response identity harus cocok. Hanya tambahan src BE; demo hanya pada runtime demo.
- Validasi lokal: TypeScript PASS; 34 tes parser/input/recovery PASS. Ini belum bukti browser native. SQL baru (workspace/history/paging) masih perlu run CI.
- Berikutnya: UI binding rework/celup serta sumber invoice dan harga celup, ALL-C04 impor historis/lifecycle, bukti negatif/race/HTTP/browser, T2/T3 29/rollback/CodeQL. Tidak ada pengurangan scope.

## Hasil BE-6 / UI rework dan celup
- Commit `5bdca71da7bfac748c7337c39dfe2fce90a9c021`, run `36267540607`; before `108474974454`, after `108474974653` success; log after **7/7 PASS**. Run ini memeriksa SQL workspace/paging yang baru, belum browser UI.
- Form BS kini memilih target kompatibel lewat search/paging API BE; hasil baru memakai command BE, completion/partial/inverse tetap command native. Mode laundry + SKU baru memakai jasa celup berbayar; rewash biasa tetap tersendiri. Recovery domain BS menyimpan dua action baru tanpa menghapus envelope lama.
- Tab Harga & Tagihan Laundry kini membaca jasa rework nyata, harga unknown, pengisian harga pertama, dan sumber invoice/correction `rework_service_id`. Parser menerima tepat satu dari tiga sumber. Command harga memeriksa izin sebelum replay; semua biaya tetap sumber vendor.
- Probe BE sekarang menyimpan respons facade/workspace asli dan menjalankan parser halaman di CI (termasuk invoice jasa). Ini gate tambahan, tanpa mengubah expected tujuh kasus.
- Lokal: TypeScript PASS, 51 unit parser/input/recovery/model PASS, SQL/PLpgSQL 70 fungsi parse. Percobaan lint ESLint tidak tersedia pada repo (tidak ada config), bukan PASS; dependency repo tidak diubah.
- Berikutnya: baca run baru + gate parser; **ALL-C04 masih belum diimplementasikan**. Selesaikan adapter impor pengeluaran/denominator historis, lalu bukti biaya pulih/recost negatif, browser/race/HTTP BE, T2, paket 29, rollback dan CodeQL. Family belum siap rilis.

## Hasil BE-7 — parser menangkap cacat format respons
- Commit `fab908189878c25791c9043ca4ca86411c181984`, run `36267949653`: before `108476139256` success; after `108476139364` **INCOMPLETE**. Tujuh kasus transaksi PASS, tetapi parser halaman atas 27 snapshot menolak `bd_21.json`: `Tarif celup: nominal tidak valid.`
- Penyebab produk BE: workspace jasa celup menserialisasi numeric(18,6) tanpa format kontrak uang halaman (dua desimal). Server kini mengirim tarif/biaya sebagai numeric(20,2)::text seperti workspace BD lainnya. Parser dan expected tidak dilonggarkan. Run lama tetap INCOMPLETE; verifikasi harus melalui run baru.
- Run BD `36267949656`: before `108476139501`, after `108476139409` keduanya success (status Actions; tidak menggantikan pembacaan per-kasus BD-2).
- Rancangan C04 disimpan `docs/cp6-be-pocket-design.md`. LANGKAH BERIKUTNYA: baca run BE berikut termasuk semua snapshot parser; implementasikan adapter C04 lengkap tanpa event produksi/adjustment historis palsu, lalu gate BE seluruhnya. BE tetap NOT_READY, CP6 HOLD.

## Hasil BE-8 / tahap ALL-C04
- Commit `46164cb7530113c00f266fa5666ee678b7b34f99`, run `36268744958`: before `108478502103`, after `108478502010` success. After **7/7 PASS**, parser halaman **27 snapshot / 0 penolakan**, primary_unchanged=true. Perbaikan format respons tarif celup terbukti; hasil BE-7 tidak dilabel ulang.
- Adapter C04 tahap pertama: impor fakta pengeluaran dan hasil jahit historis dengan provenance dokumen/baris lintas batch; ALLOCATED hanya referensi, UNALLOCATED expense pembuka eksplisit. Manifest periode menyatukan sumber native/historis; stok/event kerja tidak dibuat ulang. Hasil historis terikat opening WIP/BS/FG atau bukti penjualan lama; alokasi/correction/cancel memperbarui biaya turunan.
- Kasus baru mengunci 10 PCS (5 WIP, 3 FG, 2 terjual): 11,25 → 5,62/3,38/2,25; koreksi15 → 7,50/4,50/3,00; cancel alokasi mengembalikan seluruh biaya ke expense tanpa stok. **Belum diuji native** pada checkpoint ini. Sumber receipt supplier belum ditagih + propagasi invoice C04 masih harus disambungkan, beserta UI koreksi/riwayat, guard tambahan dan pengujian lanjut.
- TypeScript dan parser SQL lokal lulus; bukti transaksi tetap CI. LANGKAH BERIKUTNYA: baca run delapan kasus, perbaiki bila gagal, lengkapi sumber harga receipt C04 dan lanjutan WIP/sale/return/conversion, kemudian seluruh gate BE. Family NOT_READY.

## Hasil BE-9 / receipt-backed C04
- Commit `58edc56d4f67e6bc3574ca1c1f6100a9341628c5`, run `36269387604`: before `108480303935` success; after `108480304039` **INCOMPLETE** pada setup kasus C04: kode satuan `YARD` tidak ada di fixture rantai. Fixture kini membaca satuan kain yang benar-benar ada. Tujuh kasus BE sebelumnya PASS, 27 snapshot parser lolos. BD terpicu `36269387695` success (status saja).
- C04 diteruskan ke penerimaan supplier belum ditagih: identitas supplier/receipt/baris eksplisit, qty terpakai ikut rekonsiliasi receipt; nilai awal harus sesuai harga sumber, recost invoice/reversal menambah event biaya dan memperbarui pool, tidak mengubah stok. Koreksi manual ditolak bila biaya bersumber nota supplier. Detector qty receipt dan supplier-cent target ditambah sumber ini, tidak dikecualikan.
- Probe tambahan: 20 bahan @2,25, stok tersisa15 dan kain keluar5 (=11,25); invoice3,00 membuat pool15,00 dan WIP+1,88/FG+1,12/COGS+0,75; inverse kembali, stok tetap15. Belum hasil native. LANGKAH BERIKUTNYA: baca run sembilan kasus, perbaiki kesalahan yang terbukti; lalu UI C04, guard/lanjutan, pengujian biaya BE lainnya dan gate akhir.

## Hasil BE-10 / UI C04
- Commit `7bdaa97093f3eb56d58ff1cf3d393081e25de59a`, run `36269783473`: before `108481400161` success; after `108481400038` **INCOMPLETE**. Kedua kasus C04 masih ditolak saat setup satuan: material seed menyimpan `YD`, tetapi kode itu bukan UOM aktif yang diterima importer. Fixture kini mengambil **uom_definitions LENGTH aktif**, sama seperti trial impor native AP. Ini kesalahan fixture writer, bukan alasan melonggarkan validasi produk. Tujuh kasus BE/27 snapshot sebelumnya tetap PASS.
- Halaman Kain Kantong ditambah riwayat sumber/hitungan hasil jahit historis dengan pencarian/count, status sudah dibagi sebelum cutover vs pool aktif, dan koreksi nilai tertaut recovery. Sumber receipt hanya dapat dikoreksi lewat nota supplier. Parser membedakan ekstensi belum tersedia dari daftar kosong; nominal invalid tidak diubah jadi0. BELUM bukti browser.
- Total kontrol denominator historis kini wajib dan harus sama dengan seluruh rincian lembar; sumber tidak lengkap ditolak. Nilai receipt dan pembilang punya kontrol terpisah. C04 belum dinyatakan lulus sebelum run native baru.
- Berikutnya: baca run baru C04, perbaiki, uji invoice dan inverse aktual; lanjut WIP/sale/retur/konversi, tanggal/cancel/race, gate HTTP/browser dan paket BE.
- Verifikasi UI checkpoint ini memakai perintah proyek yang tepat: `npx tsc -b` PASS; 45 tes Pocket DOM + parser opening + recovery PASS. Catatan: `tsc --noEmit` pada tsconfig root yang berisi references saja tidak mencakup build seluruh src; klaim TypeScript sebelumnya digantikan hasil `tsc -b` ini (tanpa error src).

## Hasil BE-11 / biaya berantai dan bongkaran
- Commit `865fbd8a04049d6c051858b66202eeba48a6ea8e`, run `36270121880`: before job `108482355136` success, after `108482355277` **INCOMPLETE**. Tujuh kasus lama PASS dan 27 snapshot parser lolos. C04 menemukan bug produk: qty historis yang sudah tervalidasi bulat tetapi berbentuk `5.000000` dicast langsung dari text ke bigint; diperbaiki melalui numeric. Kasus receipt C04 gagal pada fixture FABRIC berbentuk MATERIAL biasa; diperbaiki menjadi MATERIAL_ROLL, guard produk dipertahankan.
- Probe kesepuluh menguji koreksi harga aksesori setelah konversi berantai dan penjualan, lalu bongkaran terlambat diterima/dinilai, batas kuantitas, inverse valuation/invoice, snapshot sale tetap, sumber HPP lama tetap, dan detector native. Expected ditulis sebelum run: recost+6 → FG+4/COGS+2; recovery3 → FG-2/COGS-1. Belum verdict native.
- UI mendukung beberapa komponen bongkaran; waktu fisik wajib dipilih, tidak diisi otomatis saat membuka halaman. Histori membedakan PROVISIONAL_RECOVERY dari SOURCED_TO_DATE, menampilkan sisa belum diterima dan belum dinilai. Keduanya fakta sumber, bukan izin mengarang harga. Build TypeScript PASS.
- LANGKAH BERIKUTNYA: baca run 10 kasus, selesaikan C04 dan biaya lanjutan; tanggal periode cutover, lanjutan WIP dan kontrol negatif; kemudian race/HTTP/browser BE, T2, paket29/capture/rollback, CodeQL, handoff final. BE NOT_READY, CP6 HOLD.

## Hasil BE-12 / tanggal historis dan lanjutan
- Commit `0ac0d48869948c9cd2826805fc75d0ce784a0f53`, run `36270681304`, before `108483912988` success, after `108483913158` **INCOMPLETE**: 8 PASS, 2 FAIL. Parser34 snapshot lolos. C04 receipt invoice/inverse PASS (FG+1,12/WIP+1,88/COGS+0,75, stok tetap15). C04 manual semua nominal benar tetapi detector bertambah; hasil detector rinci ditambahkan untuk diagnosis, tidak dikecualikan.
- Kasus biaya berantai: seluruh nominal, lineage, inverse, policy pending, provisional recovery dan detector PASS; kontrol over-return FAIL karena fixture tidak menyertakan reference wajib. Ditambah reference agar penolakan kapasitas benar-benar dicapai. Run lama tetap FAIL.
- Histori C04 yang seluruhnya sebelum cutover kini memilih tanggal jurnal paling awal sejak cutover sumber. Preview menampilkan tanggal ekonomi. Periode berisi transaksi native tetap menjalani kunci tanggal periode asli, tanpa pelonggaran guard. Alokasi ke WIP juga menyinkronkan nilai BS hasil split. Kasus baru menguji completed3/split2/scrap2 dan koreksi, serta tujuh kontrol provenance/pembilang/penyebut.
- LANGKAH BERIKUTNYA: baca run12 kasus dan diagnosis detector C04; sambungkan phase pre_be/after, jalankan race/HTTP/browser BE lalu seluruh gate paket29 dan rollback. Belum ada penerimaan independen.

## Hasil BE-13 / runtime BE
- Commit `c9f3c93db7404f01200a3e4eb8eefa9910dd8ef7`, run `36271005752`: before job `108484817774` success; after `108484817965` **INCOMPLETE**, 11/12 PASS. Biaya berantai lengkap PASS. Periode murni historis dibukukan sejak cutover; completion3/split2/scrap2 berubah menjadi FG34,50/BS23,00 dari sumber57,50; ketujuh kontrol invalid import ditolak.
- Kasus manual C04 mengidentifikasi `V2620E_OPENING_HPP_LINEAGE_MISMATCH`: predikat lama belum menghitung alokasi historis baru yang sah. Predikat diperluas dengan tepat sumber biaya pocket, tanpa menghapus check atau menambah toleransi. Probe menambah kontrol negatif: current HPP +1 tanpa sumber harus tetap terdeteksi; seluruh korupsi uji hanya dalam savepoint yang dibalik.
- Runtime `after` sekarang memasang BE, `pre_be` berhenti pada BD. Skenario writer baru: 7 race (commit/abort/replay konversi, first price dan invoice jasa), 2 HTTP Auth nyata, 3 browser (konversi desktop UTC/HP Honolulu + inverse; C04 allocation/correction HP). Ini expected sebelum run, bukan hasil lulus.
- Berikutnya: baca kedua run, perbaiki bukti gagal; lengkapi browser rework/celup, sumber estimated dan kontrol tanggal/cancel; lanjut gate T2/T3 paket29/rollback/CodeQL. BE NOT_READY.

## Hasil BE-14 / persiapan paket ke-29
- Commit `96cba9aeb7941a6d8ea97e12df0a585c349c223a`, native run `36271341380`: before job `108485769191`, after `108485769296`, keduanya success. Log after **12/12 PASS**, 34 snapshot parser tanpa penolakan; primary_unchanged=true. Kontrol negatif HPP +1 tanpa sumber terdeteksi; run lama tidak dilabel ulang.
- Runtime race/HTTP/browser run `36271341354`: selftest job `108485768902` success; skenario `108485769047` masih berjalan saat checkpoint.
- Paket BE disiapkan sebagai berkas ke-29; wrapper AC..BD tidak berubah. Identitas row pocket memakai generated coalesce dari ID sumber nyata (tanpa menulis ulang data lama atau UUID acak). Perbandingan instalasi membuktikan seluruh kolom lama identik, kolom alternatif kosong, ID baru persis turunan sumber. Constraint invoice mempertahankan nama sebelumnya supaya capture/rollback dapat mengembalikan definisi tepat.
- Rollback BE mencakup kolom, nullability, dua primary key beserta index, constraint sumber invoice, seluruh fungsi dan objek baru; tak memakai CASCADE. Capture akan membuktikan daftar objek; jenis/diff di luar daftar tetap ditolak. **Belum** berkas rilis terpin atau bukti rollback BE. Capture awal bisa merah karena paket committed masih28; pins lengkap harus diambil, paket29 dibangun, kemudian capture/install/cycle ulang.
- LANGKAH BERIKUTNYA: baca hasil modes dan capture; lengkapi browser rework/redye dan kontrol biaya; finalisasi paket29/pins, rollback, T2/CodeQL, tulis handoff BE dengan identitas final. CP6 HOLD.

## Hasil BE-15 / modes pertama dan pins lengkap
- Head `21b03040eed68bf9ace7a8c22684f27e492072fc`, native `36271725917`: before `108486836989`, after `108486837064` success; after **12/12 PASS**, perubahan generated ID/constraint tidak merusak hasil native.
- Modes head `96cba9a`, run `36271341354`, selftest `108485768902` PASS; skenario `108485769047` **INCOMPLETE**. Race7/7 PASS; HTTP1 PASS/1 FAIL (oracle writer keliru mengira GUDANG punya izin view); browser1 PASS/2 INCOMPLETE (locator select memakai label exact). C04 allocation/correction HP PASS. Primary tidak berubah. Hasil beku tidak diubah.
- Tes berikut memakai role baca-saja khusus yang dibuat melalui API Owner di salinan, untuk menguji view tanpa HPP dan penolakan tulis. Default GUDANG tetap ditolak. Locator select diperbaiki tanpa perubahan UI.
- T3 `36271725924`: install `108486836976` dan browser `108486837113` success **untuk paket committed28, bukan BE**; capture `108486837097` memasang29 dan restore drill berhasil tetapi job FAIL `T3_COMMITTED_PACKAGE_STALE [BE]`. Pins `c944d677f2e519f61369623cfceff145550f82a25c906baaebdc5464da5865fb`, 118733 byte, disimpan `docs/evidence/cp6-t3/be_pins_36271725924.json` dan diverifikasi saat build. Paket29 dibangun; AC..BD byte identik. Gate install diperketat untuk daftar family tepat29, agar paket kurang anggota selalu ditolak.
- Rollback `36271725913` job `108486837197` FAIL sebelum capture: paket committed masih28 (`T3_ROLLBACK_PACKAGE_KEYS`). Rerun setelah paket29 diperlukan; belum ada rollback BE yang dinyatakan lulus.
- LANGKAH BERIKUTNYA: rerun modes dan T3/rollback capture, lengkapi browser rework/redye serta C04 certainty/continuation, kemudian T2, rollback cycle, CodeQL dan handoff final. BE NOT_READY, CP6 HOLD.

## Hasil BE-16 / kepastian biaya C04 dan browser rework
- Head `7370710855e311a2ed5abc2572991a7497446400`; native `36272226618` after `108488234529`, before `108488234733` success (12/12 after PASS).
- T3 `36272226547`: install `108488234694` dan browser `108488234786` success (status Actions); capture `108488234896` FAIL pembanding lama. Pins BE dari capture **byte identik** dengan run sebelumnya (source `00b17d57…`, package `42ba9f17…`); alat masih membaca `docs/evidence/cp6-t3/release_pins.json` lama28, bukan MANIFEST paket29. Pembanding sekarang membaca daftar/hash MANIFEST yang benar-benar diinstal, tetap wajib persis. Ini cacat alat, run merah tetap merah.
- Rollback `36272226520`, job `108488234525`: **CAPTURED**, primary_unchanged=true; BE menambah298 objek, mengubah tiga nullability, dua PK/index, constraint sumber invoice dan fungsi. Blob157806 byte sha `76c15d353be8cfc6ef629e60da7a54f46fd744361c7dfb501dcd56c50194990c` disimpan sebagai capture historis. Belum cycle; perubahan kepastian biaya berikut membutuhkan capture baru.
- C04: hasil tinjauan sumber menemukan biaya receipt kain kantong belum ikut menentukan ESTIMATED/ADJUSTED, terutama invoice yang sama persis dengan estimasi. BE menambahkan ketergantungan harga tersebut pada FG awal dan WIP/BS; zero-delta invoice tetap menyegarkan kepastian tanpa membuat jurnal nilai. Probe invoice sama harga dan inverse ditambahkan; belum bukti native pada checkpoint ini.
- Dua browser tambahan: rework mandor ke SKU baru (partial→complete→inverse) dan celup ulang HP (partial→complete→harga unknown diisi lewat Laundry). T2 kini memasang BE, oracle lama tidak disunting.
- Modes `36272226513`, scenario `108488234392` masih berjalan; selftest `108488234479` success. LANGKAH BERIKUTNYA: baca semua hasil, perbaiki kegagalan konkret; capture/pin produk BE terbaru, rollback capture/build/cycle, CodeQL dan handoff final. Family NOT_READY.

## Hasil BE-17 — urutan DDL dan kontrol kelanjutan
- Modes `36272226513` sudah selesai: race7 PASS, HTTP harga PASS; HTTP reader INCOMPLETE karena kode role fixture22 karakter melewati kolom app_users.role20. Fixture dipendekkan15 karakter, API/validasi produk tetap. Dua conversion browser mencapai preview tetapi tidak menghasilkan tombol post; bukti galat UI/respons preview ditambahkan untuk diagnosis, **belum dianggap hanya kesalahan tes**. C04 browser tetap PASS.
- Head `58e4a22`: BE `36272662289` before `108489437001` success; after `108489437137` INCOMPLETE sebelum kasus: SQL function kepastian harga merujuk tabel receipt yang baru dibuat belakangan. Urutan DDL diperbaiki (tanpa menonaktifkan check_function_bodies). T2 `36272662308` jobs `108489436968/108489437097/108489437120` FAIL; T3 `36272662292` jobs `108489436784/108489436936/108489436957` FAIL; modes `36272662312` scenario `108489437142` FAIL/selftest `108489437005` success. Gate produk belum hijau; run baru wajib.
- Ditambah expected kasus native riwayat ALLOCATED tidak membuat expense/pool kedua, duplicate dokumen lintas batch ditolak, dan FG awal dijual→konversi→retur→koreksi. Dua race C04 memegang transaksi nyata pada koneksi pertama, menuntut POCKET_PERIOD_BUSY pada koneksi kedua lalu retry sesudah commit/abort. Batas waktu mencegah lock macet ditafsirkan PASS.
- LANGKAH BERIKUTNYA: baca native14 dan modes, selesaikan cacat konkret; lanjut matrix mixed/native cutover dan inverse biaya, paket29 final, rollback cycle, T2/CodeQL dan handoff. Produk belum siap audit final.

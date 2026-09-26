# Progres audit CP6 — GPT (log khusus auditor)

**Cabang bersama:** `audit/cp6-final-20260924-gpt-a0bcadf`. Hanya GPT yang menulis berkas ini dan `out/gpt_*.md`; Fable menulis `AUDIT_PROGRESS_FABLE.md` dan `out/fable_*.md`. **Satu handoff writer** tetap `AUDIT_WRITER_HANDOFF_CP6.md`. `AUDIT_PROGRESS.md` adalah arsip gabungan historis, dibaca saja sejak pemisahan ini. Jika push branch maju di tengah pekerjaan, ambil HEAD terbaru lalu commit fast-forward; jangan force-push atau menimpa berkas auditor lain. Tidak ada kode produk, main, kompetisi, hosted, legacy, atau production yang disentuh auditor.

**Fase aktif:** audit silang BC putaran pertama; checkpoint BB final dan BC di `out/gpt_bc_20260926_initial_review.md`. Acuan BB historis: head `e6487118bbef5c62fc355835ad5b9baaf525c719`, tool `4c61acad2270e11a2aca762237790a68cf36278a`, product_ref `797fadd8b0b4aa033d3c807f0f806270fa1cf87b`; itu bukan identitas BC. Head BC terpantau `27e1a05eea61cfe68f461d445c024d3963dfe6dd` (perbaikan UI), head rollback yang gagal `0746c33e7afaebaeace995e3979b7eef4c84fd36`. Bukti BB di bawah adalah cakupan lokal. **CP6 HOLD · audit_complete=false · production_go=false**. D06 lampiran C6 rev4 telah dicatat disahkan owner pada addendum C0 §9 (25 Sep 15:55 UTC; commit lampiran `4c61acad`, hash tertulis `42e04815…`); nilai `PENDING_POLICY_VALUE` belum disahkan. Pengesahan ini bukan penerimaan uji.

## Gate kontrak GPT (cakupan penuh, bukan status subkasus)

Sumber gate hanya tiga kontrak: `ERP_V3_2_Master_Pulih_20260923.md` (M), `ERP_V3_2_Perubahan_Pulih_20260923.md` (P), `ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md` (BR); owner addendum C0 dipakai hanya untuk keputusan owner yang sudah diratifikasi. Kelompok C6-01..10 adalah register GPT, tidak sama dengan GATE-01..16 Fable. Rujukan baris berasal dari register beku `AUDIT_PROGRESS.md:82–99`; status di sini terkini dan konservatif. **Tidak satu pun gate penuh ACCEPT.**

| Gate | Dasar kontrak | Status penuh | Yang sudah dibuktikan / batas |
|---|---|---|---|
| C6-01 identitas dan kecukupan bukti | M:1624–1626,1693,1699,1762–1767,4324 | HOLD | Hash/head/run terpin; masih perlu hasil final dan acceptance owner. |
| C6-02 atomik dan fakta posted | M:3816–3826,5048–5052 | HOLD | Kasus transaksi terpilih lulus; belum semua 22/75 lifecycle dan inverse. |
| C6-03 recovery, input unknown, selector | M:1678–1679,1691,3817–3820,3825–3826,3939 | UNVERIFIED | W10/W11/W13 browser terpilih lulus pada BA; matriks seluruh rute belum ditutup. |
| C6-04 ALL saldo awal | M:44–45,359–365,749–755,829–843,934–938,1024–1025,1691; P:966–967 | HOLD | S02 dua draf dan BB T1 lokal lulus; scope ALL22 tetap wajib, BC/BD/BE belum dibuktikan. |
| C6-05 tanggal, HPP, jurnal, laporan | M:375,377,835,837,1022,1059–1065,1666,1691,3816,3820,3825,6632 | HOLD | Pool 10 nota total/stok tepat, C0 25/25; 12 HOLD kalender historis dan jalur biaya lain tetap ditangani terpisah. |
| C6-06 produksi, AR/AP, payroll dan uang muka | M:359–379,629–648,749–757,3822–3824 | UNVERIFIED | BB partial/family dan kontrol penolakan lokal lulus; seluruh sumber dan efek belum diterima. |
| C6-07 aksesori/pocket/laundry CR | M:44–48,466–472,495,557–561,1023,3900–3902,3951,5192–5199 | HOLD | Crosswalk 39 ACC + 36 LAU pra-kode tersedia; runtime lengkap BC/BD/BE dan D06 belum selesai. |
| C6-08 Auth, izin dan UI | M:1691,4486,5046–5052,5209,5213–5224 | UNVERIFIED | HTTP/Auth dan browser terpilih berhasil; matriks role/action/location penuh belum dinilai. |
| C6-09 concurrency/stale | M:751–755,1025,4165,4486,5048–5052 | UNVERIFIED | Race terpilih ada, seluruh interleaving dan inverse belum selesai. |
| C6-10 instalasi, restore, rollback dan cleanup | M:1767,3826,4306–4314,4486,5192–5209; BR batas CP6/CP7 | HOLD | T3 paket BB 26/26 dan rollback 131/131 teruji disposable; bukan paket kandidat final seluruh 22/75. |

## Skenario dan hasil GPT yang terbaru

- `audit/scenarios/r10_bb/gpt_bb_independent.py`, **sha256 `4655575482e90e333f753bd65d7f788c2f04f55e8c47e05ae31d275a80393b86`**, manifest `audit/scenarios/r10_bb/MANIFEST.json`, workflow `.github/workflows/gpt-cp6-bb-round10.yml`. Oracle sebelum run M:835/M:3820/M:6632 untuk 10 dokumen, M:3821/M:6631 untuk dua draf.
- [Run rev2 **36155477550**](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36155477550), job **108138841475**, `AUDITOR_SCENARIO`, tool head `4c61aca`, dua kasus PASS/RUN_COMPLETE, `primary_unchanged=true`, full boundary restored dan kebocoran sesi 0:
  - `G10:BA_TEN_DOCUMENT_CENT_POOL`: 10 nota masing-masing 10,005 → nilai dokumen 10,01, total WIP **100,10**, stok qty **0**, nilai **0,00**. PO pertama 10,05; semua per PO di `out/gpt_bb_round10_result.md`. **ACCEPT lokal** untuk total dan exhaustion; deviasi +0,04 tidak otomatis gagal kontrak per PO.
  - `G10:BB_TWO_DRAFT_SHARED_RESERVE`: stok 10, dua reservasi 3+2, tersedia **5→4→6→6** sesudah edit/cancel/POST; AR +40, revenue −40, COGS +24, FG −24 sekali; dua reserve habis. **ACCEPT lokal** untuk siklus ini, bukan semua ALL.
- [Run rev1 **36154846659**](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36154846659), job **108136764090**, skenario sha256 `18dc5075eabb27302b80d7c9919164d1ed371342f6c6c78839d7614f523f8d7c`: S02 PASS; sen mentah COUNTEREXAMPLE akibat snapshot baseline auditor **salah** (setelah penerimaan); adjudikasi **INCOMPLETE oracle**, tidak dilabel ulang. Detail `out/gpt_bb_round10_result.md`.
- [Run T2 BA **36125151913**](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36125151913), jobs AR **108039445366** 174/174, tanggal **108039445443** 41/41, regresi **108039445222** DISPOSITION_REQUIRED: 12 HOLD historis tetap, C0 25/25. [T3 BA **36126474798**](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36126474798) jobs **108043639348/108043639585/108043639625** 25/25 install/capture, browser10/10; [rollback BA **36126986327**](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36126986327) job **108045271455** 127/127. Semua hanya pada BA lama dan bukan acceptance BB. Kasus/ID terinci di `out/gpt_r9_t2_cases.json`, `out/gpt_r9_t3_run.md`, `out/gpt_r9_rollback_cases.json`.
- [BB T1 awal **36127700002**](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36127700002) before **108047512931** 20 NO_ROUTE+2 CE+3 PASS, after **108047512581** 25/25 PASS pada BB dev awal; detail `out/gpt_r9_bb_t1_run.md`. Kode BB final sudah berbeda, maka lihat run final Fable berikut.

## Cross-check hasil Fable yang dibaca GPT

[Run final Fable **36155406049**](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36155406049), tool head 4c61aca, before job **108138601608** 52 NO_ROUTE+2 CE+3 PASS, after **108138602159** **57/57 PASS**, mismatch kosong, `primary_unchanged=true`. Parser lulus 402/809 file sesudah `npm ci`. Run lama 36154186985 tetap INCOMPLETE akibat `esbuild` hilang; bukan produk gagal. Detail `out/gpt_fable_r11_probe_crosscheck.md`. Ini verifikasi **log Fable**, bukan skenario GPT baru. Laporan Fable `out/fable_r11_results.md`; handoff writer **tetap satu**.

## Temuan dan risiko terbuka

- **P2 alat/oracle historis (GPT):** skenario sen rev1 salah snapshot; rev2 baru membuktikan total dan stok. Oracle ALL-S01 pernah salah arah Dr/Cr, errata `out/r9_all_oracle_errata.md`; BB S01 sudah dicek Dr AR 70/Cr equity70 dalam konteks opening. Kedua kesalahan auditor dipertahankan pada riwayat.
- **P3 alat historis (Fable):** parser BB memerlukan `npm ci`, run ulang selesai; run lama tidak diubah.
- **P3 pengungkapan keputusan T3:** banyak nota bertumpuk dapat memindahkan beberapa sen ke PO pertama (+0,04 pada 10 nota); bunyi "paling banyak 1 sen per PO" keliru. Kontrak hanya mengikat pembulatan per dokumen, total/per tanggal, stok nol dan jejak. Owner menerima A hanya setelah keputusannya dicatat tertulis pada sumber yang tepat; jangan mencampurnya dengan D06.
- **HOLD scope:** ALL22 dan 75 C6 belum tuntas; D06 lampiran C6 rev4 sudah tercatat disahkan; bukti produk BC/BD/BE dan nilai kebijakan owner belum lengkap. BC/BD/BE, nilai kebijakan pending dan final release tetap perlu pembuktian.

## BC — pemeriksaan GPT awal (26 Sep WIB; writer evidence, bukan acceptance independen)

- [Rincian 43 kasus dan verifikasi kode](https://github.com/Hanjay6688/-erp-garment-ux/blob/audit/cp6-final-20260924-gpt-a0bcadf/out/gpt_bc_20260926_initial_review.md). Head writer saat catatan awal `5e1ae83`; kemudian bergerak ke `0746c33` dan verifikasi head final perlu ditinjau ulang. **Status penuh:** C6-04/C6-07/C6-10 HOLD; C6-08/C6-09 UNVERIFIED.
- [BC T1 `36168802591`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36168802591) before job `108183052987`: 32 NO_ROUTE, 3 COUNTEREXAMPLE, 8 PASS. After job `108183053304`: 43/43 PASS; parser 320 berkas, F3=2, F4=0. Ini T1 writer.
- [Auditor Scenario `36168808537`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36168808537), job `108183042642`: 11/11 races PASS, 2/2 HTTP Auth PASS, browser 2 PASS + 1 INCOMPLETE (datetime-local input); skenario `fdc06d1808b86e8918e7b80b64386517d3bbd60f1582a45c71020b973fb203ab`, browser `4e43fb8c3952159476abfdf3ef3ddb868221b0344e47492399663d904057051b`.
- [T3 `36168802454`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36168802454): install job `108183850057` hijau untuk paket AC..BB (26 file), capture job `108183850580` merah BC pin berbeda; browser job `108183850317` hijau pada paket lama. Rollback/T2 final head ini belum lulus.
- Writer sudah mendorong paket 27 file pada `e21d15b`: [T3 `36170892085`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36170892085) dan [rollback `36170892127`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36170892127) berstatus success saat dibaca, tetapi perlu periksa per-job apakah benar rollback BC sudah ada; run `36171280254` pada `0746c33` sedang berjalan, dan browser re-run `36170901705` pada `e21d15b` juga berjalan. Jangan klaim selesai sebelum log per-kasus dan exact head cocok.
- F4 SQL/parse terbukti dan fixed lokal T1: SQL BB `reversible=NULL` untuk settlement advance, parser `initialImportBB.ts:98` menolak, BC `coalesce(...,false)`. F3 Nota Ambil Aksesori (regex UUID seed non-RFC) masih buka; ACC-D09 UI note belum dibuktikan. ACC-C12 kasus writer menguji penerimaan fisik baru +10, belum duplikat dokumen susulan bagi barang fisik opening yang sama. Tambahkan dua kasus independen ini ke skenario audit.
- [T3 paket 27 file `36170892085`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36170892085) pada `e21d15b`: jobs install `108189869318`, capture `108189869280`, browser `108189868928` success; `T3_PINS_REPRODUCED.equal=true`. [Rollback `36170892127`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36170892127), job `108189867439` success **CAPTURE saja**, cycle `36171280254` job `108191139823` pada `0746c33` berjalan saat cek ini.
- [Browser ulang `36170901705`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36170901705) pada `e21d15b`, job `108189903737`: 2 PASS + `BC_BROWSER:FILL_POST_AND_REVERSE` INCOMPLETE (dokumen BCA sudah tercatat, tombol `Buka` hilang dari daftar). Temuan **GPT-BC-01 P3 UI**: `filters.current.query` diisi SKU saat tab Stok, tetap menyaring dokumen tetapi kotak pencarian hanya terlihat pada tab Stok; backend mencari query dokumen pada nomor/referensi/alasan, tidak pada SKU (`src/ConnectedAccessoryServicePage.tsx:41–52,92–105,340–355`; `scripts/cp6_bc_objects_router.sql:198,204`). Ada workaround membersihkan filter Stok; tetap perlu perbaikan UX terpisah dan browser rerun. Detail log dan oracle di `out/gpt_bc_20260926_initial_review.md` commit `c8f90dd`.
- **LANGKAH BERIKUTNYA BC:** baca log browser re-run dan T3/rollback pada head final; tulis skenario GPT ACC-C12 dan ACC-D09, pin hash, jalankan di disposable runtime bila dispatch tersedia; catat run/job/per-kasus. T2 final, CodeQL dan release pin tetap perlu dicek. Sesudah itu Fable dapat mengompilasi temuan dari berkas GPT ini tanpa membaca chat.

## LANGKAH BERIKUTNYA

1. Setiap sesi GPT: checkout cabang bersama, baca berkas ini dan `AUDIT_WRITER_HANDOFF_CP6.md`, baca hasil Fable dari `AUDIT_PROGRESS_FABLE.md` jika sudah tersedia. Jangan ulang dari nol atau mengambil alih tulis log Fable.
2. Untuk head BC/BD/BE, beku oracle kontrak dan scenario/hash di `audit/scenarios/` lebih dahulu; jalankan satu workflow per fase, simpan run/job/per-kasus di `out/gpt_*.md`, commit+push **hanya berkas GPT**. Periksa head terbaru sebelum push; kalau branch maju, rebase commit secara fast-forward tanpa force.
3. D06 dan keputusan T3 A tercatat pada addendum C0 §9 di head writer; tetap pin commit/hash lampiran dan review penerapannya terhadap hasil. Nilai kebijakan `PENDING_POLICY_VALUE` tetap pending sampai owner memilihnya.
4. Saat semua family dan gate terbukti, koordinasikan satu pembaruan serial pada `AUDIT_WRITER_HANDOFF_CP6.md` bersama Fable. Sampai itu terjadi: CP6 HOLD, `production_go=false`.


## Checkpoint BC — rollback merah, 25 Sep 18:12 UTC

- [Cycle rollback `36171280254`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36171280254), job `108191139823`, head `0746c33`: **FAIL 134 PASS / 1 FAIL**, `primary_unchanged=true`; `REINSTALL_BC_SAME_AS_FIRST_INSTALL` memiliki digest data berbeda pada `bc_policy_settings_v1`, `bc_policy_setting_events_v1`. Rollback BC→BB dan post-use refusal BC masing-masing PASS. Semantik tujuh default policy tampak tetap pending, tetapi sebab beda digest belum dibuktikan dari diff isi baris. Sumber BC: `supabase/dev/cp6_bc_t1_family.sql:15–41` menaruh default `statement_timestamp()` dan `gen_random_uuid()` di dua tabel tersebut. **C6-10 HOLD**; penilaian awal GPT-BC-02 P2 reproduksibilitas alat/seed, perlu diff row atau comparator spesifik, lalu rerun penuh. Rincian dan rekomendasi oracle di `out/gpt_bc_20260926_initial_review.md`.
- Head UI `27e1a05`: perbaikan kandidat GPT-BC-01 sudah didorong writer. [Browser/races/HTTP `36171707986`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36171707986), job `108192583283`, dan [T2 `36171725748`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36171725748), jobs `108192643312/108192643438/108192643634`, masih berjalan saat dicatat. Jangan upgrade label sebelum log selesai.

**LANGKAH BERIKUTNYA (BC):** baca per-case browser `36171707986` dan T2 `36171725748`, simpan hasil job; minta writer diff baris seed policy pada dua instalasi, perbaiki alat/seed terbatas dan rerun rollback penuh; lanjut tes independen ACC-C12 barang opening sama vs baru dan ACC-D09 Nota Ambil Aksesori dengan fixture UUID valid; update log ini dan `out/gpt_bc_20260926_initial_review.md` tanpa menyentuh berkas Fable.


## Checkpoint BC — browser/race/HTTP final head `27e1a05`, 25 Sep 18:15 UTC

- [Run `36171707986`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36171707986), job `108192583283` (self-test `108192583719`), scenario sha256 `fdc06d1808b86e8918e7b80b64386517d3bbd60f1582a45c71020b973fb203ab`, `tool_head=product_ref=27e1a05`: **11/11 race PASS**, **2/2 HTTP Auth PASS**, **3/3 browser PASS**, `RUN_COMPLETE`, browser console_errors=0, Auth cleanup 0. Browser `FILL_POST_AND_REVERSE` membuktikan stok utama 15→20, pos 5→0 dan dokumen REVERSED; set+clear owner pending lagi; impor menunjukkan pending/quarantine/unreturned/customer. GPT-BC-01 (filter pencarian tersembunyi) **FIX_VERIFIED pada alur ini**. Detail per kasus di `out/gpt_bc_20260926_initial_review.md`. Ini skenario writer yang dibaca mandiri dari log, belum oracle auditor ACC-C12 dan ACC-D09.
- Rollback cycle `36171280254` **tetap FAIL**; jangan gabung hasilnya dengan browser hijau. T2 pada `36171725748` masih perlu per-case dan job final.

**LANGKAH BERIKUTNYA:** ambil status/log T2 `36171725748`; dapatkan diff data seed policy pada reinstall BC dan minta writer rerun rollback; uji ACC-C12 same-item dan ACC-D09 Nota Ambil Aksesori sesuai oracle; commit setiap hasil ke log khusus GPT.


## Checkpoint T2 parsial BC — 25 Sep 18:19 UTC

[Run `36171725748`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36171725748) head `27e1a05`: AR job `108192643312` success tetapi 174 kasus = **173 PASS + 1 INCOMPLETE** (`ACCESSORY_CONNECTED_ZERO` ditolak `BC_FREE_REQUIRES_POLICY`, karena gratis Special ERP-DEC02 perlu pengaturan owner). Kasus dan status AR cocok 174/174 dengan run lama `36168125448` job `108180772488`: bukan regresi baru. AT/AU job `108192643634` 41/41 PASS, identik dengan `108180772219`. Original+AS job `108192643438` masih berjalan. Penilaian lengkap T2 belum final; `INCOMPLETE` tetap INCOMPLETE sambil memutuskan nasib oracle lama sesuai D06. Detail ada di `out/gpt_bc_20260926_initial_review.md`.

**LANGKAH BERIKUTNYA:** tunggu job ketiga T2, catat semua HOLD/identity; rollback cycle masih FAIL satu cek seed nondeterministik; rerun cycle setelah diff seed; uji ACC-C12/ACC-D09 mandiri.


## BC checkpoint koreksi setelah CI 25 Sep 18:40 UTC — supersedes catatan sementara di atas

- Identitas: writer tool head **`21ce322c8556b23dbf70d4f04befeb6eda4ba1ef`**, product_ref **`27e1a05eea61cfe68f461d445c024d3963dfe6dd`**. Diff `27e1a05..21ce322` hanya `docs/` dan `scripts/`, tanpa produk. Tidak ada kode produksi/main/hosted disentuh auditor.
- [Rollback cycle `36174363509`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36174363509) job `108201252869` **135/135 PASS**, primary_unchanged=true. GPT-BC-02 (sebelumnya FAIL `36171280254`) **FIX_VERIFIED**: tujuh key cocok; hanya seed install `set_at` dan event `id` berbeda, comparator spesifik dan tetap strict pada rollback predecessor.
- [T3 package `36174363719`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36174363719) jobs install `108201254387`, browser `108201254683`, pins `108201254739` success untuk produk `27e1a05`, 27 file pins equal, drill RESTORED_SAME_MEANING/data_identical. [BC T1 `36174363546`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36174363546) after `108201253371` **44/44 PASS**, before `108201253819` expected NO_ROUTE/CE. [CodeQL `36174371647`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36174371647) jobs `108201289479/108201289495/108201289518/108201289524` success; jumlah SARIF tidak disimpulkan tanpa cek.
- [T2 `36171725748`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36171725748) jobs `108192643312/108192643438/108192643634` selesai success tetapi disposition tetap: AR 173 PASS + 1 INCOMPLETE, original+AS 422 identitas kasus sama dengan run sebelum F4 (termasuk 12 HOLD kalender, 4 AO INCOMPLETE), AT/AU 41 PASS. T2 tetap label T2_REGRESSION, bukan independent acceptance.
- [Auditor Scenario `36174368419`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36174368419) job `108201278783` **red**: race 11 PASS, HTTP Auth 2 PASS, browser lama 3 PASS, **kasus baru ACC-D09 INCOMPLETE** karena setelah `p.reload()` skrip mengharapkan halaman nota tetap terbuka sementara `src/App.tsx:417–427` memulai kembali pada halaman pertama. Selftest `108201278552` sukses. Kasus belum menguji posting/double-click/mobile; status ACC-D09 **UNVERIFIED**, bukan kegagalan produk terbukti.
- C12 tambahan `C12:SAME_GOODS_COUNTED_ONCE` PASS menutup saldo kedua, key custody sama, valuasi dua kali; **key custody baru masih diterima sebagai pending** dan belum diuji sampai inspect+value pada barang fisik yang sebenarnya sama. Oracle M:5290/fable C12; **PARTIAL/UNVERIFIED** pada jalur itu. F3 guard UUID non-RFC tetap, fixture UUID v4/seed deactivation perlu untuk D09.

**Status gate penuh:** C6-04 ALL22 HOLD (W05 PARTIAL/C04 no route), C6-07 C6/aksesori-laundry HOLD (ACC-D09 dan BD/BE), C6-10 release/rollback **HOLD secara keseluruhan** walau subgate BC package dan BC rollback sekarang success (final BD/BE belum dibuat). C6-08 UI UNVERIFIED untuk D09. `audit_complete=false`, `production_go=false`.

**LANGKAH BERIKUTNYA:** lihat apakah writer rerun D09 dengan navigasi ulang pasca-refresh; baca JSON kasusnya sampai browser desktop/HP/double-click/recovery. Susun/dispatch skenario independen C12 key custody baru→inspect→value, beda barang nyata vs barang sama; pertahankan oracle pra-kode. Fable dapat kompilasi detail di `out/gpt_bc_20260926_initial_review.md`. Setelah BC, lanjut BD/BE dan T2 disposition tanpa mengulang dari nol.


### Run D09 baru dipantau (25 Sep 18:4x UTC)

Writer commit `bc538e239f1e9ed5cfea93daaeaa281ae4ac88ea` hanya mengubah skenario browser: sesudah `p.reload()`, ia kembali membuka menu Nota Ambil Aksesori lalu memeriksa bahwa draf belum posting. [Run `36175345878`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36175345878), job kasus `108204487548`, self-test `108204486861`, **in_progress saat dicatat**. Produk tetap `27e1a05`. **LANGKAH BERIKUTNYA:** baca status dan per-case JSON run itu; jangan label D09 PASS sebelum desktop, double-click, reload, HP dan recovery semua diuji; bila merah, bedakan skrip dari produk, commit temuan.


## Checkpoint BC selesai pada cakupan family — 26 Sep 02:39 WIB

Catatan sebelumnya yang menyatakan ACC-D09 INCOMPLETE bersifat historis: run baru [`36178858173`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36178858173), job kasus `108216024933`, selftest `108216024702`, **11 race + 2 HTTP Auth + 4 browser = 17/17 PASS**, `RUN_COMPLETE`, primary unchanged. D09 UUID v4: reload tidak posting, double-click satu nota 7 PCS, stok 20→13, setelah HP nota kedua stok 6; galat/unknown/loading pulih. Enam mandor seed non-RFC dinonaktifkan hanya pada klon uji; **F3 produk tetap terbuka** pada data sejenis. Browser SHA256 `f39544a35d501fb822dc8af98cb0e70fbd2b1e8b1348d8343ccaf22faea78486`, Python modes `fdc06d1808b86e8918e7b80b64386517d3bbd60f1582a45c71020b973fb203ab`. Run tool_head `62d05c43b`, product_ref `40d690635` (BD file telah ditambah, tetapi runtime run ini masih menginstal sampai BC; UI/SQL BC tidak berubah sejak `27e1a05`).

[Fable own BC probe run `36179524130`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36179524130), after `108218207456`, before `108218207667`: **49/49 PASS**, including 4 adversarial cases and fingerprint (lihat `out/fable_r12_results.md`). T1 writer [`36174363546`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36174363546) 44/44; T3 [`36174363719`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36174363719) 3 jobs success; rollback [`36174363509`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36174363509) 135/135; CodeQL [`36174371647`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36174371647) 4 jobs success. T2 [`36171725748`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36171725748) 3 jobs success dengan HOLD lama; `ACCESSORY_CONNECTED_ZERO` frozen tetap INCOMPLETE, disposisi auditor Fable **EXPECTED_CHANGE** sesuai ERP-DEC02/M:5023, bukan lulus.

**Status:** BC family selesai dalam cakupan kasus yang disebut; GPT-BC-01 filter UI dan GPT-BC-02 comparator rollback FIX_VERIFIED. ACC-D09 positif pada fixture v4 PASS; F3 UUID non-RFC pada data yang terbaca tetap open/conditional; ACC-C12 key baru tetap PARTIAL dan membutuhkan keputusan sumber/kontrol gudang. C6-04 ALL22 HOLD (W05 fisik/C04 menyusul), C6-07 HOLD (BD/BE, nilai policy pending), C6-10 full release HOLD sampai final BC+BD+BE. `audit_complete=false`, `production_go=false`.

**LANGKAH BERIKUTNYA:** Fable kompilasi `out/gpt_bc_20260926_initial_review.md` dan putusan R12; GPT beralih audit BD setelah head keluarga dibekukan, menjaga oracle LAU dan W05 pra-kode serta run identity. Jangan menyebut BC=CP6 selesai, dan jangan menyentuh produk, hosted, legacy, main, atau cabang kompetisi.


## Koreksi eksplisit BC — GPT belum audit lengkap sendiri (26 Sep 2026 WIB)

Pertanyaan owner menuntut pembedaan sumber bukti. **GPT belum menjalankan skenario BC baru miliknya sendiri.** Klaim terdahulu bahwa "BC family selesai" hanya berlaku pada cakupan **run writer/Fable** yang telah dibaca silang, bukan acceptance independen GPT atas BC penuh. Writer T1 44/44 pada run `36174363546`, job after `108201253371`; Fable T1 49/49 pada run `36179524130`, job after `108218207456`; writer race 11/11, HTTP 2/2, browser 4/4 pada `36178858173`, job `108216024933`; T3 `36174363719` jobs `108201254387/108201254683/108201254739`; rollback 135/135 `36174363509`, job `108201252869`. Semua tetap berlabel sumbernya. GPT sendiri melakukan review kode/log yang menemukan GPT-BC-01 dan GPT-BC-02, tetapi itu bukan seluruh audit runtime.

Oracle lanjutan **GPT sendiri** dibekukan di `audit/scenarios/r12_bc_gpt/ORACLE.md`, sha256 `34c744864e548aa1b06300321a40ccf227158dab97375220cf63cbcfc9cdf82c`, commit `0e833525ac5fa0b878f51831fd30ed5be3db6b16`. Disclosure: sebelum membekukannya GPT telah membaca kode BC, 44 kasus T1 writer, 49 kasus Fable, temuan F3 dan ACC-C12. Karena itu ini oracle *follow-up* dari kontrak, bukan klaim oracle BC pra-kode. Kasus baru GBC-1 custody sumber fisik sama/key baru dan kontrol barang baru; GBC-2 UUID legacy yang diterima Postgres vs v4 pada Nota Ambil; GBC-3 filter lintas tab dan inverse. Belum ada `.py`, hash skenario, run ID atau job ID untuk ketiganya: status **BELUM**.

Status per gate penuh tidak berubah: C6-01 HOLD; C6-02 HOLD; C6-03 UNVERIFIED; C6-04 HOLD; C6-05 HOLD; C6-06 UNVERIFIED; C6-07 HOLD; C6-08 UNVERIFIED; C6-09 UNVERIFIED; C6-10 HOLD. Dasar baris per gate di tabel atas. Untuk BC khusus: ACC-C12 **PARTIAL/UNVERIFIED**, F3 non-RFC **UNVERIFIED pada data nyata**; browser v4 ACCEPT hanya lokal. CP6 HOLD / audit_complete=false / production_go=false.

**LANGKAH BERIKUTNYA:** tulis `.py` dan modul browser sendiri untuk GBC-1–3 yang menguji boundary asli, catat sha256 ke progres, jalankan satu workflow BC di runtime klon pada head produk BC yang dipin, simpan run/job/per-kasus di `out/gpt_bc_*`, lalu baru simpulkan cakupan BC GPT. Fable dapat mengompilasi koreksi ini; lanjut BD sesudah BC follow-up terdisposisi tanpa mengubah hasil historis.


## Skenario GPT BC dibekukan sebelum run

- `audit/scenarios/r12_bc_gpt/gpt_bc_followup.py` sha256 `35f9aaf22de529a1ac436001d38ddfc3a18111c33e36a9d79687bc0c7586d8c2`, commit `b4610dec0781885e1513cdcdd290963b88281022`: GBC-1 dua custody key dan kontrol penerimaan fisik baru. Helper writer hanya menyiapkan fixture/API; expected ditulis GPT pada oracle `34c74486…`. Bila sumber fisik tak punya ID yang bisa dipastikan sama, status wajib INCOMPLETE/NEEDS_SOURCE_IDENTITY_POLICY.
- `audit/scenarios/r12_bc_gpt/gpt_bc_browser.mjs` sha256 `0fa516b3cd0a3cc165393b25c06bd947b456fbed7a39318aeb9f5f49d25f39a2`, commit `bd9ada10407af657b00a29599c6cd12384cdbf84`: GBC-2 halaman nota dengan UUID legacy aktif vs kontrol v4; modifikasi seed hanya di klon. Keterkaitan hosted belum diketahui.
- Kedua berkas lulus `python -m py_compile` / `node --check`. GBC-3 filter lintas tab masih BELUM ditulis. Run/job belum ada; tidak ada PASS baru. Gate C6-07 HOLD, C6-08 UNVERIFIED; seluruh CP6 HOLD.

**LANGKAH BERIKUTNYA:** dispatch satu workflow native pada head alat BC pinned `62d05c43b981dc031bca260e8b4809aadcd9a01c`; simpan run/job/per-kasus dan `primary_unchanged`. Jika tool atau fixture error, catat INCOMPLETE. Setelah GBC-1/2, tulis/dispatch GBC-3 atau dokumentasikan batasnya; jangan menaikkan BC ke ACCEPT hanya berdasarkan hasil orang lain.


## Run GPT BC mandiri dimulai

Workflow `.github/workflows/gpt-cp6-bc-followup.yml` commit `ed741dfdf0ec8933ccb7c2cbbce5943fe70fc09e` memicu run [36182512996](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36182512996), job **108228022712**, pada cabang audit. Ref alat BC dipin ke `62d05c43b981dc031bca260e8b4809aadcd9a01c`; input oracle/Python/browser dicek tiga sha256 sebelum runtime. Saat pencatatan job sedang menyalakan DB disposable; **belum ada hasil per kasus**. GBC-1/2 BELUM; GBC-3 BELUM. Tahan seluruh acceptance BC/CP6.

**LANGKAH BERIKUTNYA:** baca job `108228022712` setelah selesai; bila gagal sebelum kasus, catat tahap dan perbaiki alat tanpa mengganti oracle historis; bila kasus selesai, rekam input/actual/status, cleanup, `primary_unchanged`, dan putuskan prioritas/limit. Commit+push hasil ke progres GPT dan `out/gpt_bc_*`, baru lanjut GBC-3 dan BD.


## Run BC 36182512996 selesai — merah, hasil tidak diubah

Job **108228022712** pada product_ref `40d6906358af451711d04574d184d500ab4fa944` **FAIL**. Rincian lengkap dan oracle di `out/gpt_bc_native_followup_run1.md` commit `78a0361cb1467d4b3a9354fd8cda4728af972940`. GBC-1 **INCOMPLETE**: key custody pertama 3 PCS bernilai 6, key kedua diklaim barang sama lewat catatan diterima dan setelah valuasi stok menjadi 6 PCS, jurnal +6 kedua kali; barang fisik baru kontrol +3 menjadi 9. Catatan pemanggil tidak cukup sebagai pembuktian kesamaan fisik: ACC-C12 PARTIAL/UNVERIFIED dan kebijakan identitas sumber tetap dibutuhkan. GBC-2 **INCOMPLETE alat** sebelum browser, `@playwright/test` tidak terpasang; GBC-3 BELUM. `primary_unchanged=true`, DB klon terhapus, 0 lock/sesi bocor, Auth kembali nol. Semua gate penuh tetap HOLD/UNVERIFIED, CP6 HOLD.

**LANGKAH BERIKUTNYA:** perbaiki workflow audit dengan `npm ci` + instal Chromium pada checkout auditor (tanpa kode produk), lalu run baru untuk GBC-2 dengan hash scenario sama. Setelah itu susun GBC-3 dan disposisi. Jangan menaikkan status GBC-1 yang sumber fisiknya belum punya bukti.


## BC rerun alat browser dimulai

Workflow audit saja diperbaiki `086246ea8e2831b56301f0d76f338177a1471350`: `npm ci` dan `npx playwright install --with-deps chromium` pada checkout pinned. [Run **36182902112**](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36182902112), job **108229314210**, input oracle/skenario dan tiga hash tetap; saat catat sedang berjalan. GBC-1 run lama tetap INCOMPLETE; GBC-2 belum ada hasil sampai log run 2 dibaca. GBC-3 BELUM. **LANGKAH BERIKUTNYA:** ambil log job setelah selesai; tulis per-kasus, error tooling bila ada, `primary_unchanged` dan keputusan F3 dalam `out/gpt_bc_*` lalu commit+push. CP6 HOLD.


## BC run mandiri 2 selesai — F3 terkonfirmasi di fixture, ACC-C12 menunggu identitas

[Run **36182902112**](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36182902112), job **108229314210**, tool_head `62d05c43b981dc031bca260e8b4809aadcd9a01c`, product_ref `40d6906358af451711d04574d184d500ab4fa944`, input hash tetap; rincian `out/gpt_bc_native_followup_run2.md` commit `f58f671704b2860ce5b5781e0571c646eaa35b71`. GBC-1 **INCOMPLETE** (3→6→9 PCS; ±6 di jurnal per valuasi, tidak ada sumber fisik yang bisa dipastikan sama). GBC-2 browser **COUNTEREXAMPLE pada fixture**: enam mandor UUID non-RFC aktif membuat halaman nota gagal parse meski HTTP Auth OWNER RPC 200; alert identitas tidak valid + data belum dimuat ulang. Setelah mandor seed dinonaktifkan hanya di klon dan kontrol v4 ditambah, halaman bersih. Browser group RUN_COMPLETE, Auth bersih, primary_unchanged=true, clone_remaining=0. Job keseluruhan **failure** akibat status GBC-1 INCOMPLETE, sesuai oracle; tidak boleh diklaim PASS.

**Temuan baru P2 bersyarat F3:** bila data cutover memuat ID aktif seperti itu, Nota Ambil dapat kosong. Kehadiran di hosted belum diuji dan bukan tugas auditor; inventaris read-only oleh writer/operator. **ACC-C12 PARTIAL/UNVERIFIED:** sumber fisik pada key berbeda butuh kebijakan/identitas yang eksplisit. 39 ID ACC belum diaudit lengkap sendiri; tabel cakupan `out/gpt_bc_own_coverage.md` commit `55f0d61ceac5ff879af7d575a9976226fa5a4481`. C6-04/C6-07/C6-10 HOLD, C6-08 UNVERIFIED; CP6 HOLD / audit_complete=false / production_go=false.

**LANGKAH BERIKUTNYA:** Fable kompilasi hasil run2 secara terpisah; writer/operator cek UUID cutover read-only dan tetapkan kebijakan provenance ACC-C12; GPT menuntaskan GBC-3 browser sendiri atau catat UNVERIFIED, lalu lanjut BD. Tidak mengubah status 49/49 Fable menjadi acceptance GPT.


## Oracle BD yang sudah ditulis ikut dipersistkan

`audit/scenarios/r13_bd/GPT_BD_ORACLE.md` sha256 `24a2347e579ab748bd6ed66611781669d58e8b0d103ae544592087754349d8f7`, commit `9f473c629970487a350eed8bd34097469520f728`: GBD-01 UNKNOWN price vs error; GBD-02 invoice 40/60 dan dua sumber; GBD-03 ALL-W05 fisik/claim/credit NEEDS_OWNER_INPUT. **Belum ada .py BD/run/job**. Exposure log daftar 15 kasus T1 writer dicatat di oracle; belum membaca detail kode BD untuk expected. Fase aktif tetap penutupan BC follow-up, kemudian BD. Semua gate penuh tetap HOLD/UNVERIFIED. **LANGKAH BERIKUTNYA:** susun dan pin skenario BD dari oracle ini, jalankan hanya setelah head BD final; catat oracle owner pending sebagai HOLD, jangan membaca hasil writer sebagai expected.


## Penajaman handoff gabungan R12 (26 Sep 08:07 WIB)

`WRITER_HANDOFF_R12_FINAL_PASTE_20260926.md` dirapikan di commit `b274a5446f9a040993528726fd446e46594e33fd` dan pemolesan Markdown `207ec781f53dd2de43168989165a2b36e088416c`, sesuai permintaan owner. Tiga koreksi: (1) PASS BC hanya pada kasus teruji, GBC-1 INCOMPLETE/GBC-2 COUNTEREXAMPLE fixture dan HOLD historis tetap; (2) owner D07 memberi arahan fleksibel, predikat ≤0,01 per dokumen masih usulan teknis auditor yang harus diverifikasi; (3) oracle/skenario BD boleh dibekukan sekarang, penerimaan native/final menunggu §32/head terpin. Hasil historis, gate, hash skenario, dan nilai kebijakan tidak berubah. **LANGKAH BERIKUTNYA:** Fable boleh review penajaman ini; writer menggunakan handoff R12 terbaru, sambil auditor meneruskan skenario BD dari oracle beku. CP6 HOLD, `audit_complete=false`, `production_go=false`.

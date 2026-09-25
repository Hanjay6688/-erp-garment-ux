# GPT — BC pemeriksaan awal (26 Sep 2026 WIB)

Status: **REVIEW_PARTIAL / CP6 HOLD / audit_complete=false / production_go=false**. Ini pembacaan mandiri atas kode dan log CI writer pada head `5e1ae83fbc17c8e3f53465635f3a3c816fe43a30`, **belum** skenario GPT baru dan **bukan** acceptance independen BC. Tidak ada produk, hosted, legacy, production, main, atau cabang kompetisi diubah.

## Oracle pra-kode dan catatan pembacaan

- `out/r9_acc_oracle.md` §C12/D09/D11 dan `out/fable_c6_75_oracles_pre_code.md` ACC-C12 (M:5290), ACC-D09 (M:5304), ACC-D11 (M:5306); `out/r9_all_oracle.md` ALL-A01. Semua ada di cabang audit sebelum kode BC.
- D06 **sudah disahkan**: `docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25.md:223–235` mengutip owner langsung pada 25 Sep 15:55 UTC dan mem-pin lampiran C6 rev4 commit `4c61acad` sha256 `42e0481579497c0acfe45d7092681741d431efaaeb7c200533051690b1d25f35`. `PENDING_POLICY_VALUE` tetap menunggu nilai; keputusan D06 tidak sama dengan penerimaan uji.

## Identitas dan run per kasus

- Writer [BC T1 run 36168802591](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36168802591): before job `108183052987` = 32 NO_ROUTE + 3 COUNTEREXAMPLE + 8 PASS; after job `108183053304` = **43/43 PASS**, `expectation_mismatch=[]`, before parser 225 berkas (F4 null: 28), after parser 320 berkas (F3: 2, F4: 0), `primary_unchanged=true` di ringkasan. Label `T1_FAMILY`, bukan bukti rilis. Kasus:

| Kasus | before | after |
|---|---|---|
| `B01:FILL_POST_KEEPS_TOTAL` | NO_ROUTE | PASS |
| `B02:USE_95_RETURN_25` | NO_ROUTE | PASS |
| `B03:DIRECT_USE_PURPOSE_ACCOUNT` | NO_ROUTE | PASS |
| `B04:BACKDATED_TRANSFER_LATE_INVOICE` | NO_ROUTE | PASS |
| `B05:LOCATION_AND_BYPASS_REFUSED` | NO_ROUTE | PASS |
| `B06:LINE_DAYS_AND_UNKNOWN_VARIANCE` | NO_ROUTE | PASS |
| `B07:END_TO_END_RECONCILES` | NO_ROUTE | PASS |
| `C01:RECEIVE_100_CLASSIFY_80_20` | NO_ROUTE | PASS |
| `C02:PARTIAL_INSPECTIONS_CAPPED` | NO_ROUTE | PASS |
| `C03:USED_SOURCE_NEW_KEY_REFUSED` | NO_ROUTE | PASS |
| `C04:THREE_SOURCES_SEPARATE` | NO_ROUTE | PASS |
| `C05:NO_VALUE_STAYS_PENDING` | NO_ROUTE | PASS |
| `C09:PAID_NOTE_RETURN_POLICY` | NO_ROUTE | PASS |
| `C10:CUSTOMER_GARMENT_CUSTODY` | NO_ROUTE | PASS |
| `C11:TWO_REAL_TIMELINES` | NO_ROUTE | PASS |
| `A08:REPEATED_PARTIAL_RETURNS_CENTS` | NO_ROUTE | PASS |
| `D05:REPLAY_SAME_KEY` | NO_ROUTE | PASS |
| `D06:ACCESS_DENIED_BY_SERVER` | NO_ROUTE | PASS |
| `D07:MID_COMMAND_FAILURE_ROLLS_BACK` | NO_ROUTE | PASS |
| `D08:WIB_DATES_SEPARATE` | NO_ROUTE | PASS |
| `D12:SERVER_PAGINATION` | NO_ROUTE | PASS |
| `POLICY:SETTINGS_OWNER_VERSIONED_PENDING` | NO_ROUTE | PASS |
| `DEC07:APPROVAL_THRESHOLD_ZONE_USERS` | NO_ROUTE | PASS |
| `DEC02:SPECIAL_FREE_LINE` | NO_ROUTE | PASS |
| `DEC02:MANUAL_ZERO_PRICE_REFUSED` | COUNTEREXAMPLE | PASS |
| `DEC06:ROUNDING_LINE` | NO_ROUTE | PASS |
| `F1:MANUAL_PRICE_PROVENANCE_DETECTOR` | COUNTEREXAMPLE | PASS |
| `REV:LINKED_INVERSE_MATRIX` | NO_ROUTE | PASS |
| `ALL:C02_OLD_NOTE_PARTLY_PAID_RETURN` | NO_ROUTE | PASS |
| `ALL:C02_IMPORT_REFUSALS` | NO_ROUTE | PASS |
| `ALL:C03_CUSTODY_STATES` | NO_ROUTE | PASS |
| `ALL:C03_IMPORT_REFUSALS` | NO_ROUTE | PASS |
| `C12:OPNAME_BASELINE_INCOMPLETE_SOURCE` | NO_ROUTE | PASS |
| `F4:ADVANCE_SETTLEMENT_REVERSIBLE_READ` | COUNTEREXAMPLE | PASS |
| `L:P01_RECEIPT_UNBILLED_PART_CONSUMED` | PASS | PASS |
| `L:A01_SUPPLIER_ADVANCE` | PASS | PASS |
| `L:A01_CUSTOMER_ADVANCE` | PASS | PASS |
| `L:A01_VENDOR_ADVANCE` | PASS | PASS |
| `L:A02_CASH_ADVANCE_PAYROLL` | PASS | PASS |
| `L:W01_OPEN_PO_HEADER` | PASS | PASS |
| `L:W03_OPENING_BS` | PASS | PASS |
| `L:C01_STOCK_NOTE_ROUTE` | PASS | PASS |
| `L:C01_STOCK_COMPANY_USE` | NO_ROUTE | PASS |

- Writer [Auditor Scenario 36168808537](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36168808537), job `108183042642`, hash skenario `fdc06d1808b86e8918e7b80b64386517d3bbd60f1582a45c71020b973fb203ab`, hash browser `4e43fb8c3952159476abfdf3ef3ddb868221b0344e47492399663d904057051b`: 11/11 race PASS, 2/2 HTTP Auth PASS, browser `BC_BROWSER:POLICY_SET_AND_CLEAR_BY_OWNER` PASS, `BC_BROWSER:IMPORT_PAGE_OPENING_ACCESSORIES` PASS, `BC_BROWSER:FILL_POST_AND_REVERSE` **INCOMPLETE** (`locator.fill` pada input `datetime-local`: `Malformed value` untuk `2026-09-25T09:00:00`). Job dan run merah. Kasus gagal sebelum mutasi, sehingga tidak membuktikan UI posting/reversal.
- Writer [T3 package run 36168802454](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36168802454): job install `108183850057` dan browser `108183850317` hijau **pada paket committed 26 file AC..BB**; capture job `108183850580` merah: `T3_PINS_REPRODUCED.equal=false, differ=[BC]` ketika chain AC..BC 27 file dibandingkan paket committed. BC file belum ada di `supabase/release/cp6-t3/`; rollback BC belum ada di `supabase/release/cp6-t3-rollbacks/`. Capture install/restore dan `primary_unchanged` tercatat; advisor menambah 92 INFO `rls_enabled_no_policy` (REVIEW_REQUIRED). **GATE T3 BC HOLD** sampai paket/rollback baru terpasang dan putaran lulus.
- [T2 run 36168125448](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36168125448) hijau pada head `fe226cf` (**sebelum F4**). T2 final pada `5e1ae83` belum terlihat; CodeQL final BC juga belum terlihat. [Rollback run 36168125647](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36168125647) merah pada head `fe226cf` sebelum file rollback BC dibangun.
- Push sample [Auditor Scenario 36168802442](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36168802442) hijau, job `108183006142`, menjalankan sample runtime (bukan 11/2/3 kasus BC) sehingga tidak menutup browser merah.

## Temuan dan batas oracle

1. **F4 — valid, diperbaiki di T1 BC**: `supabase/dev/cp6_bb_t1_family.sql:1020–1021` menghasilkan `false OR NULL = NULL` pada pelunasan uang muka tanpa cash account/credit; `src/initialImportBB.ts:96–101` menolak `reversible` selain boolean dan menghilangkan batch dari tampilan. `supabase/dev/cp6_bc_t1_family.sql:4001–4002` memberi `coalesce(...,false)`. Probe before `flags=[null]`, after `flags=[false]`; parser 28→0 null. Status **ACCEPT lokal untuk F4** pada T1; paket rilis BC masih HOLD.
2. **F3 / ACC-D09 — UI belum terbukti, kondisi data nyata belum diputus**: `src/accessoryIssue.ts:20,33–37` menolak UUID seed `a1000000-…` walau tersimpan di kolom PostgreSQL uuid; after workspace parser melaporkan 2 penolakan F3 yang dipisahkan sebagai pengecualian, bukan layar nota yang lulus. `scripts/cp6_bc_browser.mjs:9–11` sengaja melewatkan Nota Ambil Aksesori. Oracle ACC-D09 mewajibkan desktop/HP, 7 PCS, reload/double-click dan state error. Jalankan kontrol browser dengan fixture UUID v4 dan tanpa seed yang masuk lookup, serta lakukan pemeriksaan data cutover read-only; jangan label ACC-D09 PASS dulu.
3. **ACC-C12 — cakupan parsial, belum bukti duplikasi ditolak**: `scripts/cp6_bc_probe.py:1113–1152` mengimpor 5 stok diketahui + 3 pending, lalu mencatat pembelian baru 10 dan mengecek total 15. Ini membuktikan penambahan penerimaan baru yang sah. Oracle ACC-C12 melarang **dokumen susulan untuk 5/3 barang fisik yang sama** menambah stok untuk kedua kalinya. Tambahkan fixture idempotensi/lineage barang yang sama dan kontrol positif pembelian benar-benar baru; bila sistem tidak punya identitas sumber untuk membedakannya, tandai `HOLD/UNVERIFIED` dan minta keputusan kebijakan yang eksplisit sebelum mengklaim penuh.
4. **Browser servis BC**: `BC_BROWSER:FILL_POST_AND_REVERSE` belum menghasilkan verdict; koreksi input test dan ulangi pada head yang sama tanpa menyulap INCOMPLETE lama menjadi PASS.

## Tambahan pada head `e21d15b` / `0746c33` (CI berikutnya)

- [T3 paket run `36170892085`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36170892085) pada `e21d15b`: install job `108189869318`, capture/pin job `108189869280`, browser job `108189868928` semua hijau; `T3_PINS_REPRODUCED.equal=true`, committed 27 file AC..BC, restore drill dan primary unchanged pada install. [Rollback `36170892127`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36170892127), job `108189867439`, status PASS hanya **mode capture** (capture AW..BC), bukan cycle. File BC rollback ditambah pada `0746c33`, [cycle run `36171280254`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36171280254), job `108191139823`, **gagal**: 134/135 cek PASS; satu cek `REINSTALL_BC_SAME_AS_FIRST_INSTALL` FAIL pada dua tabel kebijakan. Rincian di bawah. Semua ini penilaian writer CI, bukan acceptance independen.
- [Auditor Scenario ulang `36170901705`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36170901705), job `108189903737`, head `e21d15b`, browser `BC_BROWSER:FILL_POST_AND_REVERSE` **INCOMPLETE** lagi: tanggal input `09:00` sudah melewati galat lama, stok pos menjadi 5 dan nomor dokumen ditemukan di SQL, tetapi tombol `Buka BCA-…` tidak muncul dalam 20 detik. Dua browser lain PASS. Race/HTTP sebelumnya pada `5e1ae83` tetap hasil beku, tidak dilabel ulang sebagai head baru.
- **GPT-BC-01 (P3 UI, sumber+runtime): filter stok tersembunyi menyaring daftar dokumen.** `scripts/cp6_bc_browser.mjs:68–88` memasukkan kode SKU pada tab Stok, membuat FILL_POST, lalu pindah ke Dokumen tanpa menghapus pencarian. `src/ConnectedAccessoryServicePage.tsx:41–52,92–105,340–355` menyimpan satu `filters.current.query` untuk tab Stok dan Dokumen, tetapi kotak pencariannya hanya ada di Stok. `scripts/cp6_bc_objects_router.sql:198,204` memakai `v_query` untuk SKU/nama stok, sedangkan untuk dokumen hanya nomor/referensi/penanggung jawab/alasan; SKU fixture tidak cocok dengan nomor BCA. Akibatnya dokumen yang sudah dibuat tidak bisa dibuka dari tab Dokumen sampai pengguna kembali ke Stok lalu membersihkan filter yang tidak terlihat di tab itu. Memperbaiki skrip uji dengan reset query dapat menyelesaikan verifikasi FILL_POST/REVERSE; cacat visibilitas filter UI tetap perlu diputuskan/fix terpisah. Oracle terkait ACC-D09 (UI desktop/HP) dan pencarian/paging ACC-D12; cek dengan skenario browser lintas tab sebelum menaikkan status.

## LANGKAH BERIKUTNYA

1. Tunggu dan review diff writer untuk paket rilis BC 27 file, rollback BC, pin/rebuild; rerun T3 full dan rollback (drill exact), T2 pada head final, CodeQL. Jangan hitung T3 AC..BB sebagai bukti BC.
2. Tulis skenario independen GPT, pin oracle dan hash sebelum dispatch: (a) F3/ACC-D09 UI Nota Ambil Aksesori dengan UUID sah; (b) ACC-C12 barang opening sama vs penerimaan fisik baru; (c) browser FILL_POST/REVERSE; (d) sampel inversi buku/stock lintas dua sesi BC. Gunakan runtime disposable saja.
3. Sesudah setiap run baru, tambahkan run/job/per-kasus ke berkas ini dan `AUDIT_PROGRESS_GPT.md`, commit ke cabang audit; nilai belum lulus tetap HOLD/UNVERIFIED.

## Hasil baru: rollback 27 file AC..BC (25 Sep 18:12 UTC)

- [Run `36171280254`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36171280254), job `108191139823`, head `0746c33e7afaebaeace995e3979b7eef4c84fd36`: **FAIL, 134/135 check PASS, primary_unchanged=true**. Semua rollback ke predecessor pada dua siklus dan penolakan post-use BC PASS. Satu kegagalan adalah `REINSTALL_BC_SAME_AS_FIRST_INSTALL`: digest baris `bc_policy_setting_events_v1` dan `bc_policy_settings_v1` berbeda antara pemasangan pertama dan pemasangan ulang. Log memberi nama tabel dan digest berbeda, belum menampilkan nilai baris pembanding; jangan mengarang kolom penyebab sebagai fakta terbukti.
- **GPT-BC-02 (gate rollback HOLD; prioritas penilaian P2 alat/reproducibility):** dari sumber BC `supabase/dev/cp6_bc_t1_family.sql:15–41`, instalasi mengisi tujuh pengaturan default status `PENDING_POLICY_VALUE`; `set_at` memakai `statement_timestamp()` pada kedua tabel dan `bc_policy_setting_events_v1.id` memakai `gen_random_uuid()`. Ini *kemungkinan sebab* hash dua pemasangan berbeda; katalog, fungsi dan predecessor justru dibanding sama serta PASS. Tampilkan diff baris agar terbukti apakah hanya ID/waktu default yang berbeda. Jika kontrak mengikat semantik default tetapi bukan timestamp/UUID instalasi, perbaiki comparator dengan normalisasi **sangat spesifik untuk kolom seed** disertai assert tujuh key, status, value, version, reason, hubungan event→key tetap identik. Jika bit-identik memang disyaratkan, buat seed deterministik. Ulangi cycle penuh pada head alat final. Run ini tidak boleh dicatat PASS.
- [Auditor Scenario `36171707986`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36171707986), job `108192583283`, dan [T2 `36171725748`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36171725748), jobs `108192643312`, `108192643438`, `108192643634`, pada head `27e1a05` masih in_progress saat pencatatan. Writer telah memperbaiki GPT-BC-01 lewat `27e1a05` dengan input/indikator pencarian di tab Dokumen; verifikasi browser belum selesai, jadi status temuan **FIX_CANDIDATE / UNVERIFIED**.

## Run baru selesai — Auth/Browser/Race pada head `27e1a05` (18:15 UTC)

[Auditor Scenario `36171707986`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36171707986), job kasus `108192583283` (self-test runner `108192583719`), scenario sha256 `fdc06d1808b86e8918e7b80b64386517d3bbd60f1582a45c71020b973fb203ab`, run identity `tool_head=product_ref=27e1a05eea61cfe68f461d445c024d3963dfe6dd`, label AUDITOR_SCENARIO, mode after; **run/job success**. Kasus (ini skenario writer; auditor mengecek per-case langsung dari log):

| Kelompok | Kasus dan hasil yang tercatat |
|---|---|
| Browser | `BC_BROWSER:FILL_POST_AND_REVERSE` **PASS**: stok utama 15, pos 5 sesudah FILL_POST; kembali utama 20, pos 0, dokumen REVERSED. `BC_BROWSER:POLICY_SET_AND_CLEAR_BY_OWNER` **PASS**: pending → set → pending versi 3. `BC_BROWSER:IMPORT_PAGE_OPENING_ACCESSORIES` **PASS**: pending/quarantine/unreturned/customer terlihat. Grup `RUN_COMPLETE`, console_errors=0, users_created=3, auth_cleanup_failures=[]. |
| Race dua sesi | 11/11 **PASS**: D01×2, D02×2, C02×2, retur×2, D04×2, dua set kebijakan pada versi sama×1; grup tidak ada kasus hilang. |
| HTTP Auth nyata | 2/2 **PASS**: GUDANG 403, anon 401, OWNER 200 untuk FILL_POST; ADMIN 400 dan OWNER 200 untuk SET_POLICY; grup tidak ada kasus hilang. |

**GPT-BC-01 (filter tersembunyi) — FIX_VERIFIED pada jalur browser ini**, lewat dokumen servis yang sekarang dapat dibuka sesudah alih tab, kemudian dibalik. Dua run merah lama tetap INCOMPLETE historis; bukti baru ini berlaku pada `27e1a05`. Ini belum menguji Nota Ambil Aksesori ACC-D09 ataupun kasus stok awal ACC-C12.

## T2 sementara pada head `27e1a05`: status per kasus tidak sama dengan hijau seluruhnya

[Run `36171725748`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36171725748) belum selesai seluruhnya. Job AR `108192643312` selesai success: **145 PASS + 1 INCOMPLETE** di `AR_SEQUENTIAL` dan **28/28 PASS** di `AR_CONCURRENCY`; total 174 case IDs. Satu INCOMPLETE ialah `ACCESSORY_CONNECTED_ZERO`: `BC_FREE_REQUIRES_POLICY`, harga eceran nol hanya lewat gratis Special ERP-DEC02 yang diset owner. Per-case status **persis sama** dengan job AR sebelum F4 `108180772488` (run `36168125448`), jadi bukan regresi baru head `27e1a05`. Perlu disposisi oracle lama secara eksplisit terhadap keputusan D06, bukan disebut PASS. Job AT/AU `108192643634`: 16/16 AT + 4/4 race, 15/15 AU + 6/6 race PASS, identik per ID/status dengan `108180772219`. Job original+AS `108192643438` belum selesai saat dicatat. Hijau GitHub job AR dan AT/AU berarti eksekusi runner berakhir sesuai kebijakan `DISPOSITION_REQUIRED`; **bukan** lulus penerimaan CP6.

## Pin head setelah perbaikan UI

Commit [`27e1a05`](https://github.com/Hanjay6688/-erp-garment-ux/commit/27e1a05eea61cfe68f461d445c024d3963dfe6dd) mengubah `src/ConnectedAccessoryServicePage.tsx` (dan skenario browser), sehingga `product_ref` pada run browser kini `27e1a05`. T3 27 file yang hijau berjalan pada `e21d15b` dan rollback merah pada `0746c33`; GitHub hanya menunjukkan dua run pada `27e1a05` saat diperiksa (Auditor Scenario dan T2), **belum ada T3 full package dan rollback cycle pada head UI tersebut**. Pin 27 berkas dari e21d masih bukti paket SQL saat itu; penilaian full-head BC tetap HOLD sambil menunggu T3 ulang dan rollback yang lulus.

## Update CI writer setelah review GPT (25 Sep 18:40 UTC; head alat `21ce322`)

Perbandingan `27e1a05..21ce322` menyentuh hanya `docs/` serta `scripts/cp6_bc_browser.mjs`, `scripts/cp6_bc_probe.py`, `scripts/cp6_t3_rollback.py`; tidak menyentuh `src`, `supabase/dev`, migrasi, atau paket. Log `run_identity` menegaskan **tool_head `21ce322c8556b23dbf70d4f04befeb6eda4ba1ef` / product_ref `27e1a05eea61cfe68f461d445c024d3963dfe6dd`**. Semua di bawah bukti writer pada runtime disposable, belum penerimaan independen.

| Run / job | Bukti per kasus atau tahap | Status |
|---|---|---|
| [Rollback `36174363509`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36174363509), job `108201252869` | **135/135 PASS**, primary_unchanged=true. `REINSTALL_BC_SAME_AS_FIRST_INSTALL` PASS; tujuh seed policy pada tiap tabel punya key identik, dan perbedaan kolom hanya `set_at` (settings), `id,set_at` (events). Comparator `scripts/cp6_t3_rollback.py:404–449` membuang kolom instalasi tersebut **hanya untuk reinstall**, sementara predecessor strict/full dan 134 cek lain tidak dilonggarkan. | GPT-BC-02 **FIX_VERIFIED pada batas itu**; run gagal lama `36171280254` tetap FAIL historis. |
| [T3 package `36174363719`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36174363719), install `108201254387`, browser `108201254683`, capture/pins `108201254739` | Tiga job success, AC..BC 27 file, pins equal=true, backup/restore RESTORED_SAME_MEANING dan data_identical=true (error pg_cron yang dijelaskan); product_ref kini sesuai UI `27e1a05`. | T3_PREP hijau untuk paket dan head produk itu. |
| [BC T1 `36174363546`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36174363546), after `108201253371`, before `108201253819` | After **44/44 PASS** (satu tambahan `C12:SAME_GOODS_COUNTED_ONCE`); before C12 NO_ROUTE, F4 COUNTEREXAMPLE. | Writer T1, bukan penerimaan auditor. |
| [Auditor Scenario `36174368419`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36174368419), kasus `108201278783`, selftest `108201278552` | Race 11/11, HTTP Auth 2/2, browser lama 3/3 PASS; **browser baru `BC_BROWSER:NOTE_PAGE_D09_DESKTOP_PHONE` INCOMPLETE** setelah `p.reload()`: script menunggu heading halaman nota tanpa membuka menu lagi. `src/App.tsx:417–427` menyimpan page pada `useState` yang kembali ke firstAllowedPage setelah refresh; `scripts/cp6_bc_browser.mjs:147` berasumsi masih di halaman nota. Kasus belum mencapai POST/double-click/mobile/recovery. | Run merah. Perbaiki **skrip** dengan navigasi `openNotes(ui,owner)` sesudah refresh dan rerun; jangan menyimpulkan produk Nota Ambil Aksesori PASS/FAIL dari kasus ini. |
| [T2 `36171725748`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36171725748), AR `108192643312`, original+AS `108192643438`, AT/AU `108192643634` | Tiga job success pada product_ref yang sama. Status **per ID identik** dengan T2 `36168125448`: AR 173 PASS + 1 INCOMPLETE; AT/AU 41 PASS; original+AS 422 case IDs termasuk 12 DATE_POLICY_REVIEW_REQUIRED di BUSINESS, AO_TRIAL 4 INCOMPLETE, NEW_CASES 8 COUNTEREXAMPLE +1 INCOMPLETE, C0 25 PASS. Job green membawa label DISPOSITION_REQUIRED, bukan semua ACCEPT. | HOLD lama tetap, butuh disposisi oracle lama. |
| [CodeQL `36174371647`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36174371647) | JS/TS `108201289479`, Actions `108201289495`, C/C++ `108201289518`, Python `108201289524` semuanya job success; tanpa memeriksa SARIF, jangan menulis angka temuan nol. | Gate alat success, laporan detail bila dibutuhkan. |

**ACC-C12 kini lebih teruji, tetapi belum bebas ambiguitas barang fisik.** `scripts/cp6_bc_probe.py:1159–1219` membuktikan saldo awal item sama batch kedua ditolak `BA_IMPORT_OPENING_ALREADY_POSTED`, custody key identik ditolak `BC_C03_DUPLICATE`, valuasi lot sama kedua ditolak `BC_QTY_EXCEEDS_BUCKET`, pembelian fisik benar-benar baru menambah 10. Log kasus after menyatakan `limit.new_custody_key=ACCEPTED`: custody key baru bagi material fisik yang mungkin sama diterima sebagai **pending di luar stok**, lalu jalur inspect→value dapat menambah stok. Itu belum dibuktikan end-to-end untuk key baru sebagai duplikat fisik; perlu skenario key baru→nilai→rekonsiliasi atau aturan sumber fisik yang dapat dibedakan. Jadi `ACC-C12` **PARTIAL/UNVERIFIED pada duplikasi ber-key baru**, bukan P1 terbukti. Oracle pra-kode M:5290 dan `out/fable_c6_75_oracles_pre_code.md §ACC-C12`.

**LANGKAH BERIKUTNYA:** tunggu rerun D09 setelah memperbaiki navigasi skrip; catat hasil reload, post sekali pada double-click, mobile, unknown/error dan pemulihan. Audit independen key baru custody yang mengaku barang sama versus barang baru; jangan mengubah oracle setelah melihat hasil. T2 historis tetap HOLD dan CP6 belum selesai sementara BD/BE belum ada.

## BC family checkpoint sesudah browser D09 final (26 Sep 02:39 WIB)

[Writer Auditor Scenario run `36178858173`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36178858173) job `108216024933` (selftest `108216024702`) **RUN_COMPLETE**: 11/11 race dua sesi, 2/2 HTTP Auth, 4/4 browser PASS, primary_unchanged=true, console_errors=0, Auth kembali bersih. Browser module sha256 `f39544a35d501fb822dc8af98cb0e70fbd2b1e8b1348d8343ccaf22faea78486`; Python scenario sha256 `fdc06d1808b86e8918e7b80b64386517d3bbd60f1582a45c71020b973fb203ab`. D09 per-case log: enam mandor seed non-RFC dinonaktifkan **hanya di klon disposable**; pada UUID v4 yang sah halaman terbuka tanpa alert, reload belum posting dan stok 20; desktop double-click mengirim tepat satu nota 7 PCS (stok 13); uji kosong/error menampilkan galat dan notice stale, menahan posting, baca lambat mengunci muat ulang, pemulihan berhasil; HP mengirim satu nota 7 PCS lagi (stok 6). Lima run merah sebelumnya tetap INCOMPLETE historis, sebab skenario/browser, bukan diubah menjadi PASS.

**Pin identitas:** run D09 tool_head `62d05c43b981dc031bca260e8b4809aadcd9a01c`, product_ref `40d6906358af451711d04574d184d500ab4fa944`; BD dev file sudah ditambahkan di ref itu, tetapi `phase=after` di runtime tersebut masih memasang **sampai BC** (log ada `bc_install`, tidak ada `bd_install`). Diff produk dari `27e1a05` ke `40d690` hanya menambah `supabase/dev/cp6_bd_t1_family.sql`, tidak mengubah `src`, migrasi/BC/package yang diuji. Jadi bukti browser ini berlaku untuk alur BC dengan UI BC sama, bukan bukti fungsional BD.

**Verifikasi silang auditor lain:** [Fable BC T1 run `36179524130`](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36179524130), after job `108218207456`, before `108218207667`: **49/49 PASS** after (44 writer plan + 4 skenario adversarial Fable + 1 fingerprint); hasil rinci `out/fable_r12_results.md §9–12`. Itu skenario Fable, bukan skenario GPT baru. Fable menilai perbedaan rollback seed yang dikecualikan sudah terbatas, dan kasus AR `ACCESSORY_CONNECTED_ZERO` sebagai **EXPECTED_CHANGE menurut ERP-DEC02/M:5023**; kasus beku tetap INCOMPLETE dengan disposisi, tidak ditulis ulang.

**Putusan terbatas BC:** jalur uji BC yang terdaftar selesai: T1 writer 44/44, T1 Fable 49/49, race 11/11, HTTP 2/2, browser 4/4, T3 27 file/pin/drill, rollback 135/135, CodeQL jobs success. Tidak berarti CP6 selesai atau semua 39 ACC oracle diterima. **F3 masih ada**: halaman nota menolak mandor seed UUID non-RFC; run D09 mengeluarkan enam seed dari lookup uji dan tidak membuktikan halaman pada data seperti itu. **ACC-C12 PARTIAL** bila barang fisik sama datang dengan key custody baru; Fable sudah menyiapkan pilihan kontrol sumber vs manual untuk owner di `out/fable_r12_results.md §12`. **D07** retune detektor v255 masih masuk tugas penulis. W05 fisik dan C04 bergantung BD/BE. Status penuh C6-04/C6-07/C6-10 tetap HOLD, `audit_complete=false`, `production_go=false`.

**LANGKAH BERIKUTNYA:** audit BD pada head produk finalnya dengan oracle LAU dan W05 fisik pra-kode, lalu BE/C04; jangan pindahkan PASS BC untuk membenarkan modul BD. Ikuti keputusan owner atas kunci custody baru ACC-C12 dan F3/data mandor; simpan per-run dan per-kasus baru di progres GPT, Fable memegang kompilasi handoff gabungan.

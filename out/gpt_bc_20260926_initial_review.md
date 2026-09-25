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

## LANGKAH BERIKUTNYA

1. Tunggu dan review diff writer untuk paket rilis BC 27 file, rollback BC, pin/rebuild; rerun T3 full dan rollback (drill exact), T2 pada head final, CodeQL. Jangan hitung T3 AC..BB sebagai bukti BC.
2. Tulis skenario independen GPT, pin oracle dan hash sebelum dispatch: (a) F3/ACC-D09 UI Nota Ambil Aksesori dengan UUID sah; (b) ACC-C12 barang opening sama vs penerimaan fisik baru; (c) browser FILL_POST/REVERSE; (d) sampel inversi buku/stock lintas dua sesi BC. Gunakan runtime disposable saja.
3. Sesudah setiap run baru, tambahkan run/job/per-kasus ke berkas ini dan `AUDIT_PROGRESS_GPT.md`, commit ke cabang audit; nilai belum lulus tetap HOLD/UNVERIFIED.

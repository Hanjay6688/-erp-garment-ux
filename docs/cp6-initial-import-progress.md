# CP6 AP — master dan dokumen saldo awal, checkpoint lanjutan

**22 September 2026 · CP6_HOLD · production_go:false · migration_installed:false · independent_acceptance:false.**

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa.
Keuangan—termasuk laporan—stok, dan HPP adalah raja.

Lapisan ini melanjutkan checkpoint 8+10 di bawah. Owner meminta lanjut dan menegaskan bahwa **7 PCS adalah aksesori**. Keputusan tanggal invoice, harga eceran manual per buah, dan scope **ALL impor** tetap berlaku; jangan meminta keputusan yang sama lagi.

## Sumber dan bukti terbaru

| Item | Nilai |
| --- | --- |
| Branch penulis tunggal | competition/cp6-j-closure-20260911 · fast-forward saja |
| Commit yang diuji | `8a7616f823d409a1d086690f2391c965e932cf0a` |
| Tree yang diuji | `d71425b722efab8aa8225f64491547ab2cea7d04` |
| Native | [35684520266 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35684520266) · job106608391252 |
| Impor AP | **28/28 PASS**, 0 unfinished |
| Biaya/eceran AO | **10/10 PASS**, 0 unfinished |
| Frontend/recovery | **62/62 di CI**; **85/85 lokal** termasuk23 recovery produksi existing |
| Pemeriksaan lain | TypeScript, source/access/recovery/CSS dan [CodeQL35684520242](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35684520242) PASS |
| Artifact | `10675464571` · 51.228byte · 11entriZIP |
| SHA256 artifact | `4089be3dd968c1c8d5a10e7ed1de67aba16b7afcb12c5fff75f1a1e2e6803805` |
| Main terverifikasi | `557005e6674058f1e5e966b350cba05501e06182` · tidak diubah |

CRC, hash, SHA/tree, jumlah/status seluruh kasus, restoration, serta flag hold pada laporan ZIP sudah dicocokkan. Kedua proposal tetap hanya dipasang dalam transaksi uji yang dibatalkan pada database disposable AC→AN. Data/fungsi kembali ke batas sebelumnya dan database dibersihkan. Ini tidak membuktikan deployment rollback atau pemasangan migrasi permanen.

## Perubahan yang sudah teruji

**Empat master baru:** LAUNDRY_VENDOR, LOCATION, CHART_ACCOUNT dan CASH_ACCOUNT. Kini17 jenis template/entity berjalan melalui uploader yang sama. Akun induk boleh muncul setelah anak di CSV. Validasi memeriksa graf induk tanpa membuat akun pada preview; siklus dan induk hilang ditolak. Impor menolak perubahan arti/induk/status akun buku besar existing, pemindahan rekening existing ke COA lain, COA kas yang bukan ASSET aktif/postable, jenis lokasi tidak dikenal, dan master ganda. Guard stok dan akun existing tetap digunakan.

**Satu batch17 jenis** diuji dari master yang belum ada sampai opening dan OPEN_PO. Preview tidak mengubah master/jurnal/stok. Posting menghasilkan tepat11 rincian opening, dengan stock/roll, FG, BS fisik, WIP nilai, kas, dan kelima jenis saldo pihak yang diharapkan. Sebelas total pembanding tidak ikut menjadi opening. OPEN_PO hanya header/target/status; **WIP fisik tidak diklaim**.

**Dokumen piutang/utang yang sudah dibayar sebagian:** kolom nomor/tanggal/jatuh tempo, nominal awal, dan pembayaran sebelum cutover ditambahkan pada OPENING_BALANCE_ITEM. Nilai awal100 dikurangi pembayaran lama32,75 harus sama dengan amount/saldo67,25. Nominal dan pembayaran lama disimpan sebagai fakta asal pada registry privat; opening subledger/jurnal hanya mengakui67,25. Tidak dibuat invoice penjualan/pembelian atau arus kas historis palsu.

Kelima saldo diuji: CUSTOMER_RECEIVABLE, SUPPLIER_PAYABLE, VENDOR_PAYABLE, CONTRACTOR_RECEIVABLE dan CONTRACTOR_PAYABLE. Bank awal100 tetap100 saat impor; pembayaran berikut7,25 memberi sisa60 dan arus bank yang tepat; reversal kembali ke67,25 dan bank100. Empat pemeriksaan canonical atas sumber/jurnal, orphan, status saldo dan tanggal tetap0 temuan sebelum/sesudah impor, settlement dan reversal pada setiap jenis pihak.

**Pencegahan pencatatan ganda:** nomor dokumen yang sama pada pihak/jenis saldo yang sama ditolak dalam maupun lintas batch, termasuk beda huruf besar/kecil. Ringkasan saldo dan rincian dokumennya tidak boleh dicampur walaupun total kontrol secara aritmetika cocok. Dua dokumen berbeda pada pihak yang sama boleh masuk dan berjumlah134,50 sesuai data. Nominal sisa salah atau tanggal dokumen melewati cutover ditolak tanpa perubahan ledger/registry. Saat pencatatan, advisory lock per pihak/jenis saldo dan unique index melindungi identitas sumber; **jadwal concurrency antarsesi belum dikualifikasi oleh trial ini**.

## Urutan bukti gelombang ini

| Commit | Native | Hasil |
| --- | --- | --- |
| `4ed70c35cc3d7db78b0a8fced9652d0411c4142d` | `35683545804` | 15AP +10AO PASS · master dan seluruh17 entity |
| `d50d0ebe7990d9f35265324eb8f3d67cd1307f96` | `35684189688` | 23AP +10AO PASS · dokumen parsial/penolakan duplikat |
| `8a7616f823d409a1d086690f2391c965e932cf0a` | `35684520266` | 28AP +10AO PASS · seluruh5 saldo pihak dan oracle jurnal/tanggal |

Commit terakhir menambah penguji/pin terhadap produk d50. Rangkaian lama di bawah tetap bukti historis sesuai SHA masing-masing; hasilnya tidak diubah menjadi hasil baru.

## Yang masih terbuka dan urutan lanjut

- ALL masih memerlukan **uang muka, penerimaan belum ditagih, serta WIP fisik per ukuran/tahap/custody**. Opening BS yang diuji masih fisik saja; kebutuhan nilainya belum selesai. Tidak ada tabel advance dedicated dalam schema AN yang diperiksa; jangan menyamakan uang muka dengan saldo pihak tanpa kontrak pelunasan/alokasinya.
- Dokumen parsial sudah mempunyai provenance dan dapat diteruskan melalui settlement opening canonical. Ini tidak membuatnya menjadi ordinary sales/supplier-invoice history; penerimaan belum ditagih beserta pencocokan tagihan/stok masih harus disambungkan terpisah.
- Guard lintas batch terbukti untuk jalur impor baru, termasuk penolakan jika saldo pihak sudah ada lewat opening lama. Jalur direct legacy yang membukukan opening setelah impor, koreksi dokumen, serta race antarsesi masih perlu pemetaan/tes sebelum mengklaim perlindungan global.
- Form aksesori yang benar-benar terhubung, reader, dan HTTP/browser masih perlu selesai. Tetap7PCS aksesori × harga manual; jangan mengganti keputusan owner dengan pecahan lusin.
- Tidak ada migrasi AO/AP dan rollback maintenance terikat sumber yang terpasang. Bentuk paket setelah kontrak produk stabil, lalu uji runtime gabungan AO+AP (trial sekarang masing-masing di atas AN), jalur public HTTP/browser, rollback/refusal/cleanup, dan seluruh keluarga tanggal/invoice direct/reverse yang terdampak.
- Audit independen tetap belum lulus. Workflow lama yang menolak scope successor tidak boleh dilabel ulang PASS. Main/PR24/25/hosted DB/deploy/CP7 tidak ditulis.

Workflow legacy Final Boundary Audit `35683545792` dan `35684189846` tetap **FAIL** pada `Verify unchanged AI-R2 backend and bounded writer UI scope`, sebelum pengujian bisnis successor. Workflow tersebut tidak diubah untuk meloloskan scope baru; native trial khusus di atas tidak menggantikan acceptance gate itu.

Jangan mengulang matrix historis yang masih terikat sumber hanya untuk menambah angka; perubahan fungsi/kontrak yang memengaruhi bukti wajib mempunyai pengujian keluarga yang tepat. Simpan branch tunggal, idempotency, draft inert, latest-data finalization, append-only correction dan laporan filed yang tetap utuh.

---

# Riwayat checkpoint pertama — status historis pada 1b3fbaa

# CP6 AO/AP — verified writer trial, 22 September 2026

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa. Keuangan—termasuk laporan—stok, dan HPP adalah raja.

**CP6_HOLD · production_go:false · independent_acceptance:false · migration_installed:false.**

Continuation from `3767458fa571f3a6f8e20945ccd01bd7ce1ab47c` on the single writer branch `competition/cp6-j-closure-20260911`, fast-forward only. The decisions in `docs/cp6-ao-ap-owner-decisions.md` remain authoritative: invoice date in an open period, manually entered retail price, and **ALL initial data**. These choices do not need to be asked again. Closed-period controlled adjustments and filed reports remain protected.

Owner clarification in this continuation: **7 PCS refers to accessories**, with the physical count independent of the dozen/gross master price. The manual price is per physical unit. This is not a change to garment quantities or a new rounding policy.

## Exact tested source and evidence

| Item | Result |
| --- | --- |
| Tested commit | `1b3fbaaec5e16962f608c5fc40e480b21e619144` |
| Tested tree | `688f8c1d8ed403e2d811a8cfff84ab6cb324e653` |
| Native writer trial | [35681922366](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35681922366) · SUCCESS · job `106600496797` |
| AP import cases | 8/8 PASS; no unfinished cases |
| AO invoice/retail cases | 10/10 PASS; no unfinished cases |
| Frontend checks in that run | 58/58 parser, connected-form and recovery tests; TypeScript, source, access, recovery and CSS checks PASS |
| Additional local affected recovery checks | 81/81 across four test files, including the existing 23 connected-production recovery tests; TypeScript clean |
| CodeQL | [35681922634](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35681922634) · SUCCESS |
| Artifact | `10674874864` · 43,025 bytes · 11 ZIP entries |
| Artifact SHA256 | `bee475d7ef95b08604d1abafe276c0b7055250089e293bd0a032fb549cd862c2` |
| Main, rechecked after the trial | `557005e6674058f1e5e966b350cba05501e06182` · unchanged |

ZIP CRC and the GitHub digest match. `SOURCE.json`, `NATIVE_TRIAL.json` and `AO_TRIAL.json` bind the results to the tested commit. The workflow reconstructed AC through AN with frozen source, verified the 692-object AN runtime, installed each proposal only inside a transaction, ran the tests, then rolled back. Both reports confirm the full data/function boundary was restored. The disposable database was removed successfully. No hosted database, deployment, main, PR24/25 or CP7 was changed.

This documentation may be committed after the tested SHA. It does not turn the later documentation commit into a fresh native test or upgrade the result to migration/independent acceptance. Historical matrices were not rerun or relabelled.

## Implemented proposal

The connected admin page reads actual UTF-8 CSV/TSV files, preserves exact numeric text, supports quoted/multiline cells and comma/semicolon/tab delimiters, and supplies templates, editable rows and row-specific errors. Files are bounded to 5 MiB and 5,000 rows. The selected entity can be replaced while the batch remains a draft. Posted batches are read-only.

The page uses the shared global writer lock and durable request envelope. A stable UTC revision fingerprint binds edits and finalization to the server draft. Late reads cannot silently overwrite the editor. A stale draft is refused and the user's unsaved content is retained visibly. A lost response replays the same request UUID and payload. Server authorization is checked before cached replay.

Finalization locks the batch, validates the latest rows, reconciles their totals and invokes the canonical master/open-PO/opening-balance writers in one transaction. The native test changed a validated amount from 14.25 to 17.25: the old total blocked posting, correcting the total posted exactly 17.25, and replay did not duplicate it. Draft and refusal cases left the ledger unchanged.

Opening details require `control_key`. `OPENING_CONTROL` compares quantities and the sum of each posting line rounded to cents; control rows create no opening item, stock movement or journal. Missing, duplicate or mismatched controls prevent finalization. Native material and roll cases each posted exactly 7 units, value 15.75, and one stock movement. Those separate stock fixtures do not redefine the owner's 7-PCS accessory requirement. Excess precision was refused rather than silently rounded. An owner disabled through the canonical access rules could no longer read the draft.

AO adds an explicit manual retail-price field to the contractor-accessory issue proposal. With either a dozen or gross master basis, a manual price of 3.25 posts exactly 7 physical accessory PCS and a 22.75 receivable; the 300-PCS fixture ends at 293. Negative, nonfinite and overprecise prices, and fractional PCS input before column coercion, are refused. The master dozen/gross price is not overwritten.

Invoice cost posting carries a private, transaction-scoped invoice date through material revaluation, PO HPP, FG/COGS and journal synchronization. Affected queued PO recalculations finish before the invoice command returns. Four two-month-delayed, partly invoiced production scenarios passed in UTC and Pacific/Kiritimati, with periods open and closed. New correction journals use invoice economic date; closed periods retain the existing controlled accounting date. Totals, reports, confidence, replay and removal of the private context were checked by the fixture. This does not convert all twelve historical date-policy observations into new PASS results.

## Affected paths and remaining scope

| Path | Current disposition |
| --- | --- |
| File decode → editor → public workspace/action RPC → canonical staging | Implemented proposal; parser/DOM and native public RPC checks pass separately. Full browser → HTTP → installed successor remains unproven. |
| Master import | Nine existing types exposed: BRAND, SIZE, MODEL, PRODUCT, CUSTOMER, SUPPLIER, CONTRACTOR, ACCESSORY_CATEGORY, MATERIAL. The new trial exercises customer and material routes; no fresh positive coverage claimed for all nine. |
| Physical opening stock | MATERIAL_ROLL and MATERIAL opening paths pass focused native cases. Existing FINISHED_GOODS and BS routes are exposed through the opening contract; their full affected-family regressions remain required. |
| WIP | Existing `erp.post_opening_balance(uuid)` creates value only. It does not create physical work by size, stage or custody. Physical WIP still needs a domain contract and implementation. |
| Cash and party balances | Existing types: CASH_BANK, CUSTOMER_RECEIVABLE, SUPPLIER_PAYABLE, VENDOR_PAYABLE, CONTRACTOR_RECEIVABLE, CONTRACTOR_PAYABLE. Customer receivable passed latest-draft/replay; other affected routes still need focused verification. |
| Open production orders | Existing `erp.apply_migration_open_pos(uuid)` maps OPEN_PO to legacy PO headers and target/status metadata. It does not create physical WIP or historical production events. |
| Laundry vendors, locations, chart/cash accounts as imported masters | Not yet implemented as new upload types. Existing references must resolve to existing records. |
| Advances, uninvoiced receipts, partly settled invoices and other outstanding documents | Not yet implemented. Must map original document identity, outstanding quantity/value and settlement linkage without inventing historical transactions. |
| Detail/control double count | Prevented within the tested batch: controls never post; exact request replay is idempotent. Cross-batch duplicate source documents and overlap between opening summary and operational documents remain uncovered. |
| BS valuation | Current BS opening is physical-only with zero control value. This does not complete all legacy BS valuation requirements. |
| Manual accessory retail entry | Native trigger/save/post proposal verified. A connected contractor-issue editor, workspace reader and HTTP family still need completion; the existing simulation UI is not evidence of that connection. |
| Invoice writer family | Four post/reverse functions for supplier invoices and direct purchase-cost corrections are modified. New native cases exercise invoice finalization with production consumption; direct-correction/reversal and concurrent queue schedules still need proof. |
| SQL admission and rollback | No AO/AP migration or maintenance rollback package generated/installed. Trial transaction rollback proves isolation of the experiment, not deployment rollback qualification. |
| Independent acceptance | Pending. Writer-owned tests cannot grant independent PASS. |

The total scope remains ALL. The first transport contract has 12 existing types plus `OPENING_CONTROL`; that count does not mean ALL is finished. Unknown amounts, historical invoices and physical production events must not be fabricated to fill the remaining contracts.

## Attempts retained as observed

| Candidate | Native run | Outcome at that attempt |
| --- | --- | --- |
| `793a11a5b2b89fec586661d85c35115f617be719` | `35680566540` | Fixture called a private role helper after private-schema access was revoked; no business-case PASS. |
| `968227774003caf2e0aa23ac1efe74b10cff1453` | `35680813968` | Four import cases passed; revocation fixture hit the real LAST_ACTIVE_OWNER_PROTECTED guard. |
| `53c67714bf23495a6fcb23e5d0a7fd7d0c0a2761` | `35681139619` | Five import cases passed; two new physical-stock fixtures lacked a required location. |
| `bb801b917f2c747c400f75eb3027b767f061dc06` | `35681575334` | Six import cases passed; roll fixture used an unknown unit alias. AO was skipped by that workflow version. |
| `1b3fbaaec5e16962f608c5fc40e480b21e619144` | `35681922366` | AP 8/8 and AO 10/10 PASS with complete boundary restoration. |

Fixture repairs preserved the last-owner guard, server authorization and installed UOM definitions. Original failing runs remain failures.

On the tested SHA, general router run `35681922247` succeeded only as routing evidence. The automatically triggered legacy AI-R2 independent workflow `35681922487` failed its unchanged bounded-source assertion before business tests because this successor is outside its old scope. It remains a failure, not independent evidence for AO/AP. Earlier generic source-gate and workbench failures remain as recorded.

## Resume from this checkpoint

Keep the writer branch and source pins above. Map and complete the remaining ALL import contracts, including document-to-opening reconciliation; finish the connected accessory retail editor; enumerate direct/reverse/date/report and concurrency paths. Then generate pinned AO/AP migration and pre-use rollback packages from genuine CLI provenance, complete installed-runtime/HTTP/UI checks, and run one combined affected-family gate after the product stabilizes. Preserve old evidence only where exact source/runtime equivalence permits it. Hand off the qualified writer result for independent review; do not self-certify CP6 or begin CP7.

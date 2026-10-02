# Transaction correction coverage — owner examples, 2Oct2026

Owner asks whether other transactions stay safe under changes: a prior-year wrong material price, an erroneous three-roll receipt, and choosing material A when the actual receipt was material B. These are distinct acceptance questions. Refusal to edit an unsafe posted transaction is a successful integrity guard, not proof that the required correction workflow exists.

| Case | Current evidence / behavior | Required before claiming complete correction |
|---|---|---|
| Unposted material receipt | Actual receipt draft/save/post/replay coverage is in the retained P09 component132. UI permits editing supported drafts; Native roll totals and unit conversion snapshots are enforced. | Exact three-roll typo and wrong-material draft journeys must be mapped to literal stock/value worksheets and current rights. |
| Old estimated receipt finalized by a supplier invoice | E06 executes actual prior-year receipt/production/sale, a later final invoice, recost and an immutable closed filing. Raw remainder40, FG40 and sold20 receive the correct price delta. Physical material/FG/work facts remain identical; current book records the lawful correction and an economic-period change marker. | Preserve E06's specific scope. Late estimate finalization does not alone prove a mistaken already-FINAL price correction after a complete year of downstream activity. |
| Already-final material price correction | Accepted Native cost-correction post/reverse functions exist. E07 and retained CP6 cost journeys check cost propagation through WIP, FG, COGS and conversion/return descendants. | Public entry/review/recovery, a complete year of later Native activity, paid supplier liability/refund bounds, closed filing, recost completion/failure, exact money conservation and current access need a source-bound end-to-end receipt. No blanket all-transactions guarantee. |
| Posted receipt quantity / roll count | Current connected receipt UI exposes reversal. Native dependencies, active invoice/payment/return, consumed or transferred stock and chronological negative prefixes can refuse it. Posted receipt details cannot enter the draft editor. | A refusal protects data but does not supply the owner a one-step historical quantity/roll correction. Do not label a current physical count as correction of a historical receipt typo. |
| Wrong material identity after posting/use | The transaction links a specific material and roll through stock movements and production. Renaming a label does not move that lineage. | A supported replacement/reclassification workflow must handle every affected physical position, costs, supplier liability and production source in one lawful atomic command, or give the concrete unresolved dependency. Existing receipt reversal is not proof of arbitrary historical identity replacement. |
| Typo in the same material's name | Distinguish master display text from material identity, quantity, unit and price. | Verify exactly which labels are current master text versus immutable document/source snapshots; preserve identity and economic facts. Never use a rename to disguise receipt A as B. |

Owning sale-note correction is separately qualified Native30, including all30/364 later stock balances, cash/return/advance and owner-report conservation. It does not qualify the material cases above. The all-eight F03 component PASS remains source-bound evidence for its declared lifecycle, not a claim that every posted document has an arbitrary edit capability. Independent acceptance and hosted installation remain open. Keep these cases visible in full P18–P21 and the owner-facing completion report.

## Tambahan: koreksi bahan di cabang `claude/new-session-deapao` (kandidat, belum diterima auditor)

Baris tabel di atas tidak diubah. Untuk kasus bahan, sekarang ada perintah pemilik "Benerin penerimaan" dan "Benerin nama bahan". Rincian, batas, dan bukti ada di `docs/cp7/RECEIPT_CORRECTION.md`.

| Kasus di atas | Kasus uji yang menjawabnya |
|---|---|
| Posted receipt quantity / roll count | `RF_QTY_DOWN_AFTER_CUTTING`, `RF_QTY_UP_AFTER_CUTTING`, `RF_ROLL_COUNT_TYPO_UNUSED_ROLL`, `RF_YEAR_HISTORY_364` (+ penolakan `RF_REMOVED_ROLL_USED_REFUSED`, `RF_ROLL_BELOW_USE_REFUSED`) |
| Wrong material identity after posting/use | `RF_WRONG_MATERIAL_AFTER_CUTTING`, `RF_WRONG_MATERIAL_AND_PRICE` (pemakaian potong; pemakaian lain ditolak dengan nama pemakaiannya) |
| Already-final material price correction | `RF_PRICE_AFTER_SALE_AND_RETURN` (harga final di penerimaan), `RF_INVOICE_PRICE_AFTER_SALE` dan `RF_INVOICED_QTY_DOWN_WITH_PAYMENT` (harga final di invoice supplier, setiap efek pada tanggalnya sendiri); `RF_SHARED_INVOICE_CORRECTED` (invoice supplier yang juga mencakup penerimaan lain) |
| Pembayaran supplier dan periode tertutup | `RF_PAYMENT_REPLAY`, `RF_OVERPAID_CREDIT_TO_NEXT_NOTA` (retur bayangan), `RF_OPENING_ADVANCE_PAYMENT_REPLAY` (dibayar dari uang muka saldo awal), `RF_CLOSED_PERIOD_CORRECTION` |
| Typo in the same material's name | `RF_MATERIAL_NAME_TYPO`, `RF_MATERIAL_NAME_REFUSALS` (hanya nama; nama bahan lain ditolak sebagai masalah identitas), `RF_MATERIAL_SKU_TYPO` (kode/SKU bahan yang sama) |
| Typo nomor roll dan data surat jalan | `RF_ROLL_NUMBER_TYPO_USED_ROLL` (roll yang sama, juga sesudah dipakai; tukar nomor), `RF_HEADER_TYPO` (nomor surat jalan supplier, jatuh tempo) |

Status bukti: lihat tabel "Bukti CI" di dokumen itu (run gagal tetap tercatat). `production_go=false`.

**VENI. VIDI. VICI. ERP. Reliable data adalah dewa. Keuangan—termasuk laporan—stok, dan HPP adalah raja.**

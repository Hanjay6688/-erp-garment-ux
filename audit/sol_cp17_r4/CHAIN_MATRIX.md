# CHAIN MATRIX — Sol r4

Kandidat `663f6faefcbb9c70f0f99bbc7e78164e03521329`. PASS selalu dalam lingkup tertulis; bukti r3 tetap bertanggal, dengan kredit runtime r4 nol. FAIL mempunyai bukti produk tersendiri. Tidak ada persentase ERP atau persetujuan produksi.

| ID | Status | Lingkup dan batas | Contoh witness yang sudah dibaca |
|---|---|---|---|
| B1 | PASS | Public/Native/Auth browser receipt,GRNI,roll; master source sintetis. | `P09_DRAFT_ESTIMATED_GRNI`, `P09_BROWSER_RECEIPT_DESKTOP` |
| B2 | PASS | Cut issue dan inverse tepat, rencana bukan physical confirmation. | `P08_ACTUAL_PHYSICAL_CUT`, `CP7_CUTTING_REOPEN_EXACT_STOCK_GL_DRAFT` |
| B3 | PASS | Pickup Native dua PCS aktual ditelusuri, browser source navigation bukan full factory journey. | `P08_ACTUAL_PARTIAL_LIFECYCLE` |
| B4 | PASS | Sewing→wage entitlement/ready Laundry teruji dalam fixture; upah tidak menunggu denominator retur-good palsu. | `CP17_G1_SEWING_RECORD_WAGE_READY_FOR_LAUNDRY`, `P12_NOTA_SOURCE_REGULAR_LAUNDRY_OUTSTANDING` |
| B5 | PASS | Ordinary/claim satu lineage dari Native pickup start lalu actual UI sewing→send→GOOD receive→QC. Free same-product rewash dimulai dari Native QC/BS lalu empat actual UI create/partial/complete/inverse. Lot/SKU/receipt/quantity, WIP/FG/HPP dan no-double-wage/AP cocok. Seeded starting steps tidak dihitung sebagai langkah layar. | `SOL_R4_B5_B6_ORDINARY_DESKTOP`, `SOL_R4_B5_B6_CLAIM_MOBILE`, `SOL_R4_B5_FREE_REWASH_SAME_PRODUCT_DESKTOP` |
| B6 | PASS | Actual same-lineage invoice draft/edit/post8→claim2 or ordinary→two cash payments→cash/credit/claim/invoice inverses. Ordinary total124/claim130; final AP0/kas8; source lot/SKU/HPP/physical unchanged, posted originals and inverses retained. Q3 qualifies genuine tool repair; all first INCOMPLETE remain. | `SOL_R4_B5_B6_ORDINARY_DESKTOP`, `SOL_R4_B5_B6_CLAIM_MOBILE` |
| B7 | PASS | Actual QC final SKU dan FG/BS, dengan Native-fixtured source dan real Auth browser. | `CP17_BROWSER_R3_05_QC_FINAL_SKU_DESKTOP`, `P08_ACTUAL_PARTIAL_LIFECYCLE` |
| B8 | PASS | Finish/reopen satu FG/HPP, active usage; FINISHED tidak memalsukan ACTUAL bila HPP belum lengkap. | `CP17_G2_FINISH_PO_FINAL_HPP_WIP_CLOSED`, `CP17_R4_02_POSITIVE_INVERSE_REOPEN_THEN_FINISH_SAME` |
| B9 | PASS | Book rank terpisah dari physical; adjustment/inverse dan qualified conversion scope retained. | `P10_BOOK_REORDER_FACTS`, `P10_ADJUST_NEGATIVE_VALUE` |
| B10 | PASS | Create/edit/manual13/post dan reservation sekali, money/FG Native source sama. | `P11_DRAFT_BROWSER_DESKTOP`, `P11_COMMAND_POST_ONCE` |
| B11 | PASS | Actual AR partial/full/inverse, cents, no second stock/HPP. | `P11_PAYMENT_BROWSER_DESKTOP`, `P11_PAYMENT_EXACT_LIFECYCLE` |
| B12 | PASS | Return grade/location/allocation/cash dependencies, exact inverse and refund source bounded. | `P11_RETURN_BROWSER_R10_DESKTOP_A`, `P11_RETURN_LIFECYCLE` |
| B13 | PASS | GL/report/close/reopen dan periode sumber benar; finance latency tetap OPEN. | `P13_REPORT_LEDGER_LIFECYCLE`, `P13_PERIOD_CLOSE_REOPEN`, `F03_COMBINED_LEDGER` |
| S1 | PASS | 26th payment exact owning AP/cash, inverse once and no stock/HPP. | `CP7_SOURCE_SUPPLIER_PAYMENT_BROWSER_DESKTOP`, `CP7_SOURCE_SUPPLIER_PAYMENT_INVERSE` |
| S2 | PASS | Return/credit reallocation same party/date, current paid child prevents unsafe reuse. | `F03_P09_NATIVE_PAID_SUPPLIER_CREDIT_CARRY`, `P09_RETURN_FABRIC_PORTABLE_CREDIT` |
| S3 | FAIL | Attendance/nota/payroll approval/pay/inverse plus old opening obligations, no double accrual. Penerimaan integritas end-to-end FAIL pada FG_REPAIR Nota: actual source/6000 benar tetapi detector false CRITICAL2. Tidak mengklaim pembayaran atau period-close UI macet. | `P12_ATTENDANCE_BROWSER_DESKTOP_CYCLE`, `P12_OPENING_BROWSER_DESKTOP_CYCLE`, `SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM` |
| S4 | PASS | Accessory/kasbon deduct limited to payable, carry retained, zero net no cash journal. | `P12_SETTLEMENT_KASBON_CARRY`, `CP17_KASBON_GIVE_DEDUCT_PAY` |
| S5 | PASS | Ordinary rework2/labor60 plus eligibility/partial-paid, owning inverse; not all rewash full browser. | `CP7_SOURCE_REWORK_DOCUMENTS`, `CP17_RWK01_OPEN_CASE_FINISHED_PART_PAID_ONCE` |
| S6 | PASS | Physical count/adjust/inverse including registered zero-history position, unknown quantity/cost not defaulted. | `P09_COUNT_FABRIC`, `P09_BROWSER_COUNT_UNMOVED_DESKTOP`, `P10_ADJUST_NEGATIVE_VALUE` |
| S7 | PASS | Synthetic opening import→downstream/cutover floor qualified; real cutover remains INCOMPLETE. | `P12_OPENING_BROWSER_DESKTOP_CYCLE`, `CP17_R2_D15_5_CUTOVER_OPENING_PATH_LATE_INVOICE_SETTLEMENT` |

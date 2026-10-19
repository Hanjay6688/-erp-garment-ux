# Inventaris kebutuhan dan siklus fungsi — Sol r4

Kandidat `663f6fae`. Pemetaan ini melengkapi tabel checkpoint; setiap baris memiliki positif, penolakan, koreksi/revisi dan pembaca hilir dalam JSON. Bukti keuangan dan kegagalan integritas Nota/payroll dipisahkan.

| ID | CP | Kebutuhan | Status cakupan | Batas |
|---|---|---|---|---|
|FUN-001|CP1|Identitas produk, baseline, paket dan katalog|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Tujuh root BEFORE/AFTER dan sumber bundle; fresh hosted baseline tidak diamati.|
|FUN-002|CP1|Satu tabel aktivasi untuk semua 47 menu|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Dashboard NOTICE; census kehadiran bukan semua field loaded. Demo/Enteng loopback terpisah.|
|FUN-003|CP1|Readability dan build yang dapat ditelusuri|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|290 rasio WIP dihitung ulang; opacity/disabled/image/form yang tidak dibuka belum terbukti.|
|FUN-004|CP2|Backup/restore data, struktur dan ACL ke copy baru|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Backup source names diperiksa lewat pencarian ID di bawah; original tidak ditulis ulang. Hosted/Drive CP7C ditunda.|
|FUN-005|CP2|Retention dan cleanup tanpa membuang Original|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Metadata time-aging, bukan tujuh hari nyata. Replacement B tetap menulis sebelum mismatch; D13-9a.|
|FUN-006|CP3|Aktor aktif, role, hak current dan private context|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|25 legacy Data API ditutup; Native DB grants tetap D14-9. Fresh STAFF belum dijalankan.|
|FUN-007|CP3|Current authority sesudah menunggu sumber|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Strict wait yang diamati dibedakan dari Barrier-only; bukan setiap race memiliki PID lengkap.|
|FUN-008|CP4|Master pelanggan create/edit/nonaktif dan dipakai sales|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Master soft retirement tidak menghapus fakta posted lama.|
|FUN-009|CP4|Master supplier, vendor, lokasi dan receipt|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Tidak menguji semua kombinasi pihak; identitas setiap fixture dipertahankan.|
|FUN-010|CP4|Master kain, benchmark, aksesori dan harga mandor|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Native identity dan ukuran/unit tidak dicocokkan hanya lewat nama.|
|FUN-011|CP4|Mandor, Work BOM dan tarif bertanggal|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|OLD/NEW dan per-PO always-new hanya Owner/Admin; old wage tidak ditulis ulang.|
|FUN-012|CP4|Nomor PO otomatis, draft/post dan rollback atomik|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|999/1000/1001/10000, same UUID dan batas tiga detik terukur di CP17.|
|FUN-013|CP4|Cutting create/edit/post, material issue dan reopen|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Correction sebelum sewing; setelah dependensi aktif harus inverse sah lebih dahulu.|
|FUN-014|CP4|Pickup mandor dan pembatalan|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|PO dan material posted tidak ikut dibalik ketika pickup saja dibatalkan.|
|FUN-015|CP4|Sewing biasa dan per-SKU, upah sekali|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Upah dari selesai dijahit, bukan menunggu denominator barang kembali GOOD.|
|FUN-016|CP4|Kain kembali/correct return yang sah|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Single compound transaction, original dan inverse tersimpan; tanggal sumber dipertahankan.|
|FUN-017|CP4|Finish/reopen PO dan HPP|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|FINISHED sah dapat BELUM_LENGKAP/ESTIMATED; tidak diberi label ACTUAL palsu.|
|FUN-018|CP4|Pool HPP attendance, activate/cancel/replacement|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Public legacy route ditutup Data API; Native DB guard batas D14-9. Held independent pool probe tidak dijalankan.|
|FUN-019|CP5|Receipt bahan estimated/final dan inverse|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Draft bukan stok; estimated GRNI bukan final AP.|
|FUN-020|CP5|Invoice supplier parsial/multi-receipt/exact|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Harga bukan stok tambahan; discount/precision dan receipt lineage lengkap.|
|FUN-021|CP5|Return supplier/portable credit/alokasi ulang|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Pihak dan sumber sama; paid child memblokir reuse yang tidak sah.|
|FUN-022|CP5|Pembayaran supplier create/correct/inverse|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Cash tanggal ekonomi dan book date, accrual floor serta huge exact cents.|
|FUN-023|CP5|Transfer roll/aksesori/other lintas lokasi|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Jumlah/nilai seluruh lokasi nol, tanpa roll palsu pada barang null-roll.|
|FUN-024|CP5|Stock count/opname bahan dan aksesori|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Physical entered, system delta dari Native; unrecorded cost bukan nol.|
|FUN-025|CP5|Laundry physical delivery/receipt/correction|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Q3 ordinary3 menjalankan sewing→send→receipt→QC pada satu lineage; tiga first INCOMPLETE tetap tersimpan.|
|FUN-026|CP5|Laundry pricing dan invoice vendor/koreksi harga|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Q3 ordinary3/claim1 menutup draft/edit/post invoice8, payment/credit dan inverse; BD document dan core payable dibaca terpisah.|
|FUN-027|CP5|Klaim laundry dan pemakaian kredit/AP/kas|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Q3 claim mobile: lima sent/empat GOOD, total130; kompensasi2 hanya AP/OTHER_EXPENSE, cicilan6 dan seluruh inverse; physical/HPP tetap.|
|FUN-028|CP5|Free same-product rewash dan hasil/reversal|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|UI free same-product rewash empat aksi lulus pada initial run39193738642; inverse sah, AP/wage/rework journal tetap0. Tidak diulang.|
|FUN-029|CP5|BS, ordinary rework dan hak kerja|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Hak kerja dan reimbursement bukan lagi upah baru setiap kali barang dicuci ulang.|
|FUN-030|CP5|QC final SKU, grade/size, FG dan inverse|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Good/BS/lot/receipt FK persis; source fixture terpisah dari browser post.|
|FUN-031|CP5|FG stock adjustment/count/book rank|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Rank tampilan tidak mengubah physical stock, HPP atau laporan.|
|FUN-032|CP5|Ganti merek/celup ulang/pocket origins|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Accepted unchanged Native BE/BF source; current X04 source pin dan biaya dibaca. Tidak fresh seluruh CP6.|
|FUN-033|CP7|Sales draft multi-line/manual13/post/inverse|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Reservation tidak double-deduct saat post; original posted tidak diedit.|
|FUN-034|CP7|Customer payment/correct/inverse|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Bukan pendapatan atau HPP kedua; 364 prefix sesudah koreksi dihitung ulang.|
|FUN-035|CP7|Sales return per allocation/grade/correction|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Duplicate product/lot tidak membuat allocation ID dapat ditukar.|
|FUN-036|CP7|Customer refund/custody source|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Service customer-owned tidak masuk FG/HPP perusahaan; refund punya credit source sendiri.|
|FUN-037|CP7|Attendance roster/rate dated/current version|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Blank attendance tidak disimpulkan HADIR/ABSEN, role/period/current revisions wajib.|
|FUN-038|CP7|Attendance record/correction/consumed source|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Koreksi consumed perlu release/payroll inverse lebih dahulu, bukan edit fakta lama.|
|FUN-039|CP7|Nota mandor/source allocation|FINANCIAL_LIFECYCLE_QUALIFIED_INTEGRITY_FAIL_S1|Source page lengkap, satu hak kerja tidak diambil nota dua kali. Valid FG_REPAIR Nota 2 lines/6000 has correct source/contractor/component but raises2 false CRITICAL wrong-contractor alarms. Financial proof remains separate; end-to-end integrity is FAIL, see PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json.|
|FUN-040|CP7|Nota ambil aksesori ke payroll deduction|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|7*300=2100; reversed3*500 tidak dihitung; net6000−2100=3900.|
|FUN-041|CP7|Payroll approve/partial/final/inverse|FINANCIAL_LIFECYCLE_QUALIFIED_INTEGRITY_FAIL_S1|Approval menimbulkan hak/biaya; pembayaran hanya settlement, tanggal tidak sebelum accrual. Valid FG_REPAIR Nota 2 lines/6000 has correct source/contractor/component but raises2 false CRITICAL wrong-contractor alarms. Financial proof remains separate; end-to-end integrity is FAIL, see PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json.|
|FUN-042|CP7|Kasbon GIVE/ALLOCATE/release/cancel|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Net tak negatif, carry tersimpan, zero-net tidak membuat jurnal kas.|
|FUN-043|CP6/CP7|Opening import/validate/finalize/inverse downstream|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Data sintetis, bukan real cutover atau satu periode shadow.|
|FUN-044|CP7|Misc income/expense/correction/cash prefix|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Compound cash rule berlaku saldo akhir; penggunaan income yang sah tidak diblokir palsu.|
|FUN-045|CP7|Laporan GL/AR/AP/cash dan known/current vs filed|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|As-filed immutable; facade finance menolak arbitrary as_known. Finance latency D17-2 tetap OPEN.|
|FUN-046|CP7|Tutup/reopen periode dan filing immutable|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Satu tab finance, permission report/period terpisah; current READY tidak menghapus change marker.|
|FUN-047|CP7|Recost bounded queue/retry/per tanggal|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Max20 completed berbeda dari attempted, fault bukan selesai; sejarah sale tetap immutable.|
|FUN-048|CP7|Native source capture/projection/model/capacity|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Kernel/factory proof berbeda; projected7 bukan physical7; global source tidak diubah filter tampilan.|
|FUN-049|CP7|Native plan draft/apply/cancel/current recheck|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Finite Native matching8→7, color mismatch dan relabel CANDIDATE ditolak; public command menolak extra matching dan membuat satu draft2 dari Original sah, tanpa stok/uang/HPP.|
|FUN-050|CP7|Publication/report/AI immutable current-authorized output|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Exact body/UTF8 source escaping; model obedience dan provider contact tidak diuji.|
|FUN-051|CP7|Manual reminder/current episode/ACK/snooze|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Review/archive bukan debt resolved; actual Native settlement/inverse menentukan episode.|
|FUN-052|CP7|Versioned reminder policy/local claim/ambiguity|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Local preview belum dikirim; UNKNOWN tidak otomatis resend atau dianggap selesai.|
|FUN-053|CP7|Staged runner/closed-page/current auth/budget|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|K4 raw17, Q1metadata4 terpisah; future production scheduler CP7C.|
|FUN-054|CP7|Server physical proof bounded/shared tick|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|151group includes labelled spent clones; ordinary five-group positive terpisah, no capture-time work.|
|FUN-055|CP7|Large transport/pages/caps and honest refusal|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|5business IDs/48 measurements bukan48 transaksi baru atau all-size SLA.|
|FUN-056|CP7|Riwayat pelanggan/CSV dan audit trail listing|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|CSV actual sesuai rows tampil; current audit content marker bukan immutable transaction snapshot.|
|FUN-057|CP7|ERP settings/policy source dan warehouse summary|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|Satu Native policy/source, non-admin redaction dan mutation read-only dibedakan.|

47 route dari `src/screenActivation.ts` disimpan satu per satu dalam JSON; census membuktikan hadir/aktivasi, sedangkan bukti angka dan lifecycle berasal dari baris fungsi di atas. Tidak ada rasio ini yang menyatakan persentase ERP.

| Route | Kebutuhan terkait | Batas |
|---|---|---|
|dashboard|FUN-002, FUN-045, FUN-057|Sensus aktivasi dan witness siklus terpisah.|
|cutting-roll|FUN-012, FUN-013, FUN-016, FUN-048, FUN-049|Sensus aktivasi dan witness siklus terpisah.|
|mandor-wip|FUN-014, FUN-015, FUN-029|Sensus aktivasi dan witness siklus terpisah.|
|sewing-wip|FUN-015, FUN-017, FUN-048|Sensus aktivasi dan witness siklus terpisah.|
|laundry|FUN-025, FUN-026, FUN-027, FUN-028|Sensus aktivasi dan witness siklus terpisah.|
|qc|FUN-030|Sensus aktivasi dan witness siklus terpisah.|
|fg-handoff|FUN-039|ConnectedFgHandoffBoundary returns ConnectedNotaPage; work-right/nota needs, not sales.|
|bs-rework|FUN-027, FUN-028, FUN-029|Sensus aktivasi dan witness siklus terpisah.|
|warehouse-dashboard|FUN-019, FUN-023, FUN-024, FUN-031, FUN-057|Sensus aktivasi dan witness siklus terpisah.|
|procurement|FUN-019, FUN-020, FUN-021, FUN-022|Sensus aktivasi dan witness siklus terpisah.|
|materials-rolls|FUN-019, FUN-023, FUN-024|Sensus aktivasi dan witness siklus terpisah.|
|pocket-fabric|FUN-023, FUN-032, FUN-043|Sensus aktivasi dan witness siklus terpisah.|
|accessories|FUN-010, FUN-023, FUN-024, FUN-040|Sensus aktivasi dan witness siklus terpisah.|
|fg-summary|FUN-030, FUN-031, FUN-032, FUN-057|Sensus aktivasi dan witness siklus terpisah.|
|movements-vivo|FUN-023, FUN-024, FUN-031, FUN-032|Sensus aktivasi dan witness siklus terpisah.|
|movements-widie|FUN-023, FUN-024, FUN-031, FUN-032|Sensus aktivasi dan witness siklus terpisah.|
|stock-card|FUN-023, FUN-024, FUN-031|Sensus aktivasi dan witness siklus terpisah.|
|stock-adjustment|FUN-024, FUN-031|Sensus aktivasi dan witness siklus terpisah.|
|brand-conversion|FUN-032|Sensus aktivasi dan witness siklus terpisah.|
|sales-invoice|FUN-033|Sensus aktivasi dan witness siklus terpisah.|
|sales-allocation|FUN-033|Sensus aktivasi dan witness siklus terpisah.|
|sales-returns|FUN-035, FUN-036|Sensus aktivasi dan witness siklus terpisah.|
|sales-payments|FUN-034, FUN-036|Sensus aktivasi dan witness siklus terpisah.|
|sales-history|FUN-033, FUN-034, FUN-035, FUN-056|Sensus aktivasi dan witness siklus terpisah.|
|finance-overview|FUN-045|Sensus aktivasi dan witness siklus terpisah.|
|finance-cash|FUN-022, FUN-034, FUN-036, FUN-041, FUN-044, FUN-045|Sensus aktivasi dan witness siklus terpisah.|
|finance-ap|FUN-020, FUN-021, FUN-022, FUN-026, FUN-027, FUN-041, FUN-045|Sensus aktivasi dan witness siklus terpisah.|
|finance-ar|FUN-034, FUN-035, FUN-036, FUN-042, FUN-045|Sensus aktivasi dan witness siklus terpisah.|
|finance-payroll|FUN-039, FUN-040, FUN-041, FUN-042|Sensus aktivasi dan witness siklus terpisah.|
|operations-attendance|FUN-037, FUN-038|Sensus aktivasi dan witness siklus terpisah.|
|contractor-issue|FUN-040, FUN-042|Sensus aktivasi dan witness siklus terpisah.|
|hpp|FUN-017, FUN-018, FUN-047|Sensus aktivasi dan witness siklus terpisah.|
|finance-journal|FUN-044, FUN-045|Sensus aktivasi dan witness siklus terpisah.|
|finance-reports|FUN-045, FUN-046|Sensus aktivasi dan witness siklus terpisah.|
|master-fabric|FUN-009, FUN-010|Sensus aktivasi dan witness siklus terpisah.|
|master-accessory|FUN-010, FUN-040|Sensus aktivasi dan witness siklus terpisah.|
|master-products|FUN-001, FUN-011, FUN-030, FUN-032|Canonical product/model/size identity and master Native source retained unchanged from accepted CP4/CP6; current consumers/QC/source mappings exercised. No fresh all-product-CRUD browser claim.|
|master-customers|FUN-008|Sensus aktivasi dan witness siklus terpisah.|
|master-partners|FUN-009|Sensus aktivasi dan witness siklus terpisah.|
|master-workforce|FUN-011, FUN-037|Sensus aktivasi dan witness siklus terpisah.|
|master-locations|FUN-009, FUN-023|Sensus aktivasi dan witness siklus terpisah.|
|master-pattern|FUN-011, FUN-013, FUN-048, FUN-049|Sensus aktivasi dan witness siklus terpisah.|
|admin-reminders|FUN-051, FUN-052|Sensus aktivasi dan witness siklus terpisah.|
|admin-access|FUN-006, FUN-007|Sensus aktivasi dan witness siklus terpisah.|
|admin-settings|FUN-057|Sensus aktivasi dan witness siklus terpisah.|
|admin-import|FUN-043|Sensus aktivasi dan witness siklus terpisah.|
|admin-audit|FUN-056|Sensus aktivasi dan witness siklus terpisah.|

| ID fungsi | Positif | Penolakan | Koreksi/revisi | Pembaca hilir |
|---|---|---|---|---|
|FUN-001|SOURCE_CHANGE_REVIEW.json|WRITER_CI_REVIEW.json|REHEARSAL_RESULT_REVIEW.json|RESULT_REVIEW.json|
|FUN-002|INITIAL_RESULT_REVIEW.json|CP17_R3_03_HISTORY_DENIED_WITHOUT_VIEW|CP17_RESULT_REVIEW.json|CP17_BROWSER_R3_03_HISTORY_DESKTOP|
|FUN-003|CP17_RESULT_REVIEW.json|BUILD_RESULT_REVIEW.json|CODEQL_RESULT_REVIEW.json|BUILD_RESULT_REVIEW.json|
|FUN-004|REHEARSAL_RESULT_REVIEW.json|K3C_RACE_NIGHTLY_BACKUP_VERIFIED|REHEARSAL_RESULT_REVIEW.json|K3C_RACE_BACKUP_VERIFIED_UNDER_WRITES|
|FUN-005|K2_PURGE_ONLY_EXPIRED_TEMPORARY|K3C_RACE_BUSY_TABLE_RETRIED|K2_PURGE_KEEPS_DOCUMENT_RUNS|K3C_CLEANED_ONLY_TEMPORARY|
|FUN-006|CP17_R4_01_EVERY_PUBLIC_ROUTE_REVIEWED|CP17_R4_01_DATA_API_REFUSED_DATABASE_SESSION_UNCHANGED|FRESH_TX_RESULT_REVIEW.json|CP17_R4_05_INTERNAL_GUARD_DISPATCH_REVIEWED|
|FUN-007|CP7_SOURCE_SUPPLIER_PAYMENT_BROWSER_DESKTOP|CP7_SOURCE_SUPPLIER_PAYMENT_INVERSE|CP7_SALES_CHAIN_RACE_AUTH_RETIRE|CP7_SOURCE_SUPPLIER_PAYMENT_INVERSE|
|FUN-008|CP17_R2_MASTER_CUSTOMER_LIFECYCLE|CP17_R2_MASTER_ACCESS_RIGHTS|CP17_R2_MASTER_CUSTOMER_USED_IN_SALES|P11_DRAFT_MULTI_CREATE_EDIT_POST|
|FUN-009|CP17_R2_MASTER_SUPPLIER_LOCATION_FABRIC_IN_RECEIPT|CP17_R2_MASTER_VENDOR_AND_LOCATION_RULES|CP17_R2_MASTER_SUPPLIER_LOCATION_FABRIC_IN_RECEIPT|P09_FINAL_EXACT_VALUE|
|FUN-010|CP17_R2_MASTER_FABRIC_PROFILE_BENCHMARK|CP17_R2_MASTER_ACCESS_RIGHTS|CP17_R2_MASTER_ACCESSORY_CATEGORY_VARIANT_PRICE|CP7_SOURCE_ACCESSORY_DOCUMENTS|
|FUN-011|CP17_R2_MASTER_RATE_VERSIONS_AND_BOM|CP17_R3_09_SWITCH_REFUSALS_AND_ACCESS|CP17_R3_09_CHOOSE_NEW_PAYS_THROUGH_REVISION|CP17_R3_09_NEW_RATE_WAGE_TO_PAYROLL_AND_DETECTORS|
|FUN-012|CP17_R3_01_AUTO_PO_NUMBER_1000_BOUNDED|CP17_R2_D15_6_AUTO_PO_FAILURE_MIDWAY_LEAVES_NOTHING|CP17_R2_D15_6_AUTO_PO_DRAFT_NO_STOCK_NO_FINANCE|CP17_R2_D15_6_AUTO_PO_THEN_BAGI_POTONGAN_AND_SEWING|
|FUN-013|P08_ACTUAL_PHYSICAL_CUT|CP7_CUTTING_REOPEN_PICKUP_DOWNSTREAM|CP7_CUTTING_REOPEN_EXACT_STOCK_GL_DRAFT|P09_TRANSFER_PRODUCTION_LATE_INVOICE|
|FUN-014|CP17_R2_D15_6_AUTO_PO_THEN_BAGI_POTONGAN_AND_SEWING|CP17_SG01_PICKUP_REVERSE_REFUSED|CP17_SG01_PICKUP_REVERSE_BEFORE_SEWING|CP17_G1_SEWING_RECORD_WAGE_READY_FOR_LAUNDRY|
|FUN-015|CP17_G1_SEWING_RECORD_WAGE_READY_FOR_LAUNDRY|CP17_G1_SEWING_REFUSALS_UNCHANGED|CP17_G1_SEWING_CANCEL_ONLY_AT_MANDOR|CP17_R3_09_NEW_RATE_WAGE_TO_PAYROLL_AND_DETECTORS|
|FUN-016|CP17_SG02_RETURN_STOCK_VALUE_PO_COST|CP17_SG02_OVER_REMAINDER_REFUSED|CP17_SG02_CORRECT_RETURN_ONE_TRANSACTION|CP17_SG02_CANCEL_RETURN_RESTORES_STOCK_GL_COST|
|FUN-017|CP17_G2_FINISH_PO_FINAL_HPP_WIP_CLOSED|CP17_G2_FINISH_REFUSALS_UNCHANGED|CP17_R4_02_POSITIVE_INVERSE_REOPEN_THEN_FINISH_SAME|CP17_R4_02_POSITIVE_INVERSE_DOES_NOT_HIDE_ACTIVE_USE|
|FUN-018|CP17_R3_04_HPP_POOL_CREATE_ACTIVATE_CANCEL_EQUALS_NATIVE|CP17_R3_04_HPP_POOL_CLOSED_PERIOD_REFUSED_ATOMICALLY|CP17_R3_04_HPP_POOL_CANCEL_SOURCE_CORRECTION_REPLACEMENT|CP17_R3_04_HPP_POOL_PREVIEW_READY_AND_BLOCKED|
|FUN-019|P09_DRAFT_ESTIMATED_GRNI|P09_INVALID_ATOMIC|P09_RECEIPT_REVERSE_ESTIMATED|RF_PRICE_AFTER_SALE_AND_RETURN|
|FUN-020|P09_INVOICE_COMPLETE_MULTI_RECEIPT|P09_INVOICE_ATOMIC_REFUSALS|P09_INVOICE_STAGED_AND_REVERSE|P18_E13_LATE_SUPPLIER_PRICE_AFTER_FULL_CYCLE|
|FUN-021|P09_RETURN_PARTIAL_AP_GRNI|P09_RETURN_ATOMIC_LINEAGE|P09_COMBINED_RETURN_FABRIC_CREDIT_INVERSE|F03_P09_NATIVE_PAID_SUPPLIER_CREDIT_CARRY|
|FUN-022|CP7_SUPPLIER_PAYMENT_CREATE_EXACT_REPLAY_SETTLE|CP17_CASH_EMPTY_BANK_REFUSED|CP7_SUPPLIER_PAYMENT_CORRECTION_EXACT_CENTS|CP7_SOURCE_SUPPLIER_PAYMENT_INVERSE|
|FUN-023|P09_TRANSFER_CONSERVATION|P09_TRANSFER_HISTORICAL_PREFIX|P09_TRANSFER_CONSUMED_REVERSE|P09_TRANSFER_CLOSED_DAY_LATE_INVOICE|
|FUN-024|P09_COUNT_FABRIC|P09_COUNT_FORGED_ATOMIC|P09_COUNT_MULTI_EDIT_INVERSE|P09_COUNT_ACCESSORY|
|FUN-025|SOL_R4_B5_B6_ORDINARY_DESKTOP|CP7_SOURCE_LAUNDRY_DEPENDENCIES|CP7_SOURCE_LAUNDRY_DOCUMENTS|SOL_R4_B5_B6_ORDINARY_MOBILE|
|FUN-026|SOL_R4_B5_B6_ORDINARY_DESKTOP|CP17_CASH_LAUNDRY_VENDOR_EMPTY_BANK_REFUSED|BD_BROWSER:DEC06_CORRECTION_UP_DOWN_ON_SCREEN|SOL_R4_B5_B6_ORDINARY_IPAD_VIEWPORT|
|FUN-027|SOL_R4_B5_B6_CLAIM_MOBILE|CP17_FIN02_CLAIM_BEFORE_SOURCE_REFUSED|SOL_R4_B5_B6_CLAIM_MOBILE|SOL_R4_B5_B6_CLAIM_MOBILE|
|FUN-028|SOL_R4_B5_FREE_REWASH_SAME_PRODUCT_DESKTOP|CP6_SCOPE_RETENTION.json|SOL_R4_B5_FREE_REWASH_SAME_PRODUCT_DESKTOP|CP7_SOURCE_REWORK_DOCUMENTS|
|FUN-029|CP17_RWK01_GOOD_CONTROL|CP17_RWK01_ALL_SCRAP_REWORK_PAYABLE_ONCE|CP7_SOURCE_REWORK_DOCUMENTS|CP17_RWK01_OPEN_CASE_FINISHED_PART_PAID_ONCE|
|FUN-030|CP17_BROWSER_R3_05_QC_FINAL_SKU_DESKTOP|CP7_SOURCE_LAUNDRY_DEPENDENCIES|CP7_SOURCE_LAUNDRY_DEPENDENCIES|P10_FG_NATIVE_SOURCE|
|FUN-031|P10_ADJUST_POSITIVE_VALUE|P10_ADJUST_FORGED_ATOMIC|P10_ADJUST_MULTI_EDIT_VERSION|P10_BOOK_REORDER_FACTS|
|FUN-032|F03_X04_REWORK_NEW_CONTRACTOR|F03_X04_PO_PIN_MISMATCH_REFUSED|CP6_SCOPE_RETENTION.json|CP7_SOURCE_REWORK_DOCUMENTS|
|FUN-033|P11_DRAFT_MULTI_CREATE_EDIT_POST|P11_DRAFT_INSUFFICIENT_EDIT|CP7_SALES_CHAIN_EXACT|P11_READ_NATIVE_LIFECYCLE|
|FUN-034|P11_PAYMENT_EXACT_LIFECYCLE|P11_PAYMENT_SOURCE_CHANGE|CP7_PAYMENT_CORRECTION_EXACT_CENTS|P13_REPORT_LEDGER_LIFECYCLE|
|FUN-035|P11_RETURN_LIFECYCLE|P11_RETURN_PAID_REFUSAL|CP7_RETURN_CORRECTION_TWO_ALLOCATIONS|CP7_RETURN_CORRECTION_YEAR_364|
|FUN-036|F03_E03_NATIVE_LEGACY_REFUND|P11_RETURN_CONSUMED|F03_E03_NATIVE_IMPORTED_REFUND|F03_E03_NATIVE_LEGACY_REFUND|
|FUN-037|P12_ROSTER_LIFECYCLE|P12_ROSTER_FIELDS|P12_ROSTER_POSTED_HISTORY|P12_ATTENDANCE_WRITE_DATED_RATES|
|FUN-038|P12_ATTENDANCE_WRITE_LIFECYCLE|P12_ATTENDANCE_WRITE_CONSUMED|P12_ATTENDANCE_WRITE_CORRECTION|P12_SETTLEMENT_ATTENDANCE_ACCRUAL|
|FUN-039|P12_NOTA_SAVE_POST_REPLAY|P12_NOTA_STALE_SOURCE|P12_NOTA_CANCEL_RELEASE|P12_SETTLEMENT_PRESERVE_SELECTED_WORK|
|FUN-040|CP17_BROWSER_R3_05_ACCESSORY_NOTE_TO_PAYROLL_DESKTOP|P12_SETTLEMENT_INVALID_PAY_CANCEL|CP7_SOURCE_ACCESSORY_DOCUMENTS|P12_SETTLEMENT_KASBON_CARRY|
|FUN-041|P12_SETTLEMENT_FULL_LIFECYCLE|CP17_FIN01_INSTALLMENT_BEFORE_ACCRUAL_REFUSED|P12_PAYROLL_READ_REVERSED_HISTORY|E05_EXACT_LARGE_CENTS|
|FUN-042|CP17_KASBON_GIVE_DEDUCT_PAY|CP17_KASBON_LIMITS_REFUSED|CP17_KASBON_RELEASE_CANCEL_REPLAY|P12_SETTLEMENT_KASBON_CARRY|
|FUN-043|P12_OPENING_LIFECYCLE|CP17_R2_D15_5_CUTOVER_FAILURE_MIDWAY_LEAVES_NOTHING|P12_OPENING_CANCEL|CP17_R2_D15_5_CUTOVER_OPENING_PATH_LATE_INVOICE_SETTLEMENT|
|FUN-044|CP17_R2_SPENT_INCOME_CORRECTION_COMMITS|CP17_CASH_BACKDATE_BEFORE_FUNDS_REFUSED|CP17_R2_MISC_SPENT_INCOME_CORRECTION_COMMITS|P13_ANALYSIS_INVERSE_DATES|
|FUN-045|P13_REPORT_LEDGER_LIFECYCLE|P13_REPORT_QUERY|P13_REPORT_FILED_LATE_CORRECTION|F03_COMBINED_LEDGER|
|FUN-046|P13_PERIOD_CLOSE_REOPEN|P13_PERIOD_BLOCKED|P13_PERIOD_LATE_ARCHIVE|P13_REPORT_FILING_PAGES|
|FUN-047|P13_RECOST_LATE_COST|P13_RECOST_BOUNDED_FAILURE|P13_RECOST_RETRY|F03_E06_YEAR_END_INCREASE_UTC|
|FUN-048|P14_NATIVE_ANALYSIS_FROZEN_NATIVE|P14_NATIVE_ANALYSIS_MISSING_POLICY|P08_VERSION|P15_NATIVE_ANALYSIS_FINANCE_SAME_SOURCE|
|FUN-049|SOL_R4_SKN24_NATIVE_MATCH_ALLOCATE_PLAN_COMMAND|P08_PHYSICAL_WRONG_MATERIAL_DRAFT|P08_SHARED_FABRIC_NATIVE_DRAFT_EDIT|P08_ACTUAL_PARTIAL_LIFECYCLE|
|FUN-050|P15_OBLIGATION_REPORT_NATIVE_EXACT_DATED_NATIVE|P15_OBLIGATION_REPORT_NATIVE_CURRENT_FINE_RIGHTS|P15_OBLIGATION_REPORT_NATIVE_LINKED_REVISION|P17_BROWSER_DESKTOP_NATIVE_HANDOFF|
|FUN-051|CP17_R3_03_REMINDERS_CREATE_EDIT_NATIVE_ROW_AND_AUDIT|CP17_R3_03_REMINDERS_DENIED_WITHOUT_KEYS|CP17_R3_03_REMINDERS_DONE_REOPEN_CANCEL_NATIVE_ROW_AND_AUDIT|P16_NATIVE_ATTENTION_REVIEW_METADATA|
|FUN-052|P16_RULE_SOURCE_LOCAL_UTF8_CAPTURE|P16_RULE_SOURCE_LOCAL_DISABLED_SUPPRESSION|P16_RULE_SOURCE_LOCAL_MANUAL_RESOLUTION|P16_RULE_SOURCE_LOCAL_NATIVE_HEAL|
|FUN-053|K4R_RACE_PG_CRON_FINISHES_JOB|K4R_LIMIT_REQUIRED|K4R_RACE_COLD_START_TWO_TICKS|Q1_STATE_RESULT_REVIEW.json|
|FUN-054|K6P_RACE_PG_CRON_FINISHES_PASS|K6P_LIMIT_REQUIRED|K6P_CANCEL_CORRECT_BACKDATE_REPROVEN_BY_SERVER|Q1_STATE_RESULT_REVIEW.json|
|FUN-055|P19S_BROWSER_DESKTOP_100|P08_PHYSICAL_WIP_IDENTITY_UPPER_BOUND|PERFORMANCE_RESULT_REVIEW.json|PERFORMANCE_RESULT_REVIEW.json|
|FUN-056|CP17_BROWSER_R3_03_HISTORY_DESKTOP|CP17_R3_03_HISTORY_AMOUNTS_HIDDEN_WITHOUT_AR|CP17_R3_03_HISTORY_REVERSALS_LISTED_NOT_COUNTED|CP17_BROWSER_R3_03_AUDIT_DESKTOP|
|FUN-057|CP17_R3_03_ERP_SETTINGS_FACADE_EQUALS_NATIVE|CP17_R3_03_ERP_SETTINGS_NON_OWNER_REFUSED_BY_NATIVE|CP17_R3_03_ERP_SETTINGS_SET_CHANGES_ONLY_THAT_POLICY|CP17_R3_03_WAREHOUSE_RECEIPT_CUTTING_EQUALS_NATIVE_AND_READS|

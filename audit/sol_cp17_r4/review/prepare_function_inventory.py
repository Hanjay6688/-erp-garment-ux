"""Manually scoped need-to-lifecycle index; ID lookups only navigate read evidence."""
from pathlib import Path
from hashlib import sha256
import json,re
R=Path(__file__).resolve().parents[1]; REPO=R.parents[1]
records=[json.loads(line)for name in ('SOL_REVIEWED_CASE_LEDGER.jsonl','SOL_CP17_CASE_LEDGER.jsonl','SOL_QUALIFIED_CASE_INDEX.jsonl')for line in(R/'ci_receipts'/name).read_text().splitlines()]
by={}
for row in records:by.setdefault(row['case_id'],[]).append(row)
# cp, need, positive, refusal, lawful correction/revision, downstream, evidence limit
D=[
('CP1','Identitas produk, baseline, paket dan katalog','@SOURCE_CHANGE_REVIEW.json','@WRITER_CI_REVIEW.json','@REHEARSAL_RESULT_REVIEW.json','@RESULT_REVIEW.json','Tujuh root BEFORE/AFTER dan sumber bundle; fresh hosted baseline tidak diamati.'),
('CP1','Satu tabel aktivasi untuk semua 47 menu','@INITIAL_RESULT_REVIEW.json','CP17_R3_03_HISTORY_DENIED_WITHOUT_VIEW','@CP17_RESULT_REVIEW.json','CP17_BROWSER_R3_03_HISTORY_DESKTOP','Dashboard NOTICE; census kehadiran bukan semua field loaded. Demo/Enteng loopback terpisah.'),
('CP1','Readability dan build yang dapat ditelusuri','@CP17_RESULT_REVIEW.json','@BUILD_RESULT_REVIEW.json','@CODEQL_RESULT_REVIEW.json','@BUILD_RESULT_REVIEW.json','290 rasio WIP dihitung ulang; opacity/disabled/image/form yang tidak dibuka belum terbukti.'),
('CP2','Backup/restore data, struktur dan ACL ke copy baru','@REHEARSAL_RESULT_REVIEW.json','K3C_RACE_NIGHTLY_BACKUP_VERIFIED','@REHEARSAL_RESULT_REVIEW.json','K3C_RACE_BACKUP_VERIFIED_UNDER_WRITES','Backup source names diperiksa lewat pencarian ID di bawah; original tidak ditulis ulang. Hosted/Drive CP7C ditunda.'),
('CP2','Retention dan cleanup tanpa membuang Original','K2_PURGE_ONLY_EXPIRED_TEMPORARY','K3C_RACE_BUSY_TABLE_RETRIED','K2_PURGE_KEEPS_DOCUMENT_RUNS','K3C_CLEANED_ONLY_TEMPORARY','Metadata time-aging, bukan tujuh hari nyata. Replacement B tetap menulis sebelum mismatch; D13-9a.'),
('CP3','Aktor aktif, role, hak current dan private context','CP17_R4_01_EVERY_PUBLIC_ROUTE_REVIEWED','CP17_R4_01_DATA_API_REFUSED_DATABASE_SESSION_UNCHANGED','@FRESH_TX_RESULT_REVIEW.json','CP17_R4_05_INTERNAL_GUARD_DISPATCH_REVIEWED','25 legacy Data API ditutup; Native DB grants tetap D14-9. Fresh STAFF belum dijalankan.'),
('CP3','Current authority sesudah menunggu sumber','CP7_SOURCE_SUPPLIER_PAYMENT_BROWSER_DESKTOP','CP7_SOURCE_SUPPLIER_PAYMENT_INVERSE','CP7_SALES_CHAIN_RACE_AUTH_RETIRE','CP7_SOURCE_SUPPLIER_PAYMENT_INVERSE','Strict wait yang diamati dibedakan dari Barrier-only; bukan setiap race memiliki PID lengkap.'),
('CP4','Master pelanggan create/edit/nonaktif dan dipakai sales','CP17_R2_MASTER_CUSTOMER_LIFECYCLE','CP17_R2_MASTER_ACCESS_RIGHTS','CP17_R2_MASTER_CUSTOMER_USED_IN_SALES','P11_DRAFT_MULTI_CREATE_EDIT_POST','Master soft retirement tidak menghapus fakta posted lama.'),
('CP4','Master supplier, vendor, lokasi dan receipt','CP17_R2_MASTER_SUPPLIER_LOCATION_FABRIC_IN_RECEIPT','CP17_R2_MASTER_VENDOR_AND_LOCATION_RULES','CP17_R2_MASTER_SUPPLIER_LOCATION_FABRIC_IN_RECEIPT','P09_FINAL_EXACT_VALUE','Tidak menguji semua kombinasi pihak; identitas setiap fixture dipertahankan.'),
('CP4','Master kain, benchmark, aksesori dan harga mandor','CP17_R2_MASTER_FABRIC_PROFILE_BENCHMARK','CP17_R2_MASTER_ACCESS_RIGHTS','CP17_R2_MASTER_ACCESSORY_CATEGORY_VARIANT_PRICE','CP7_SOURCE_ACCESSORY_DOCUMENTS','Native identity dan ukuran/unit tidak dicocokkan hanya lewat nama.'),
('CP4','Mandor, Work BOM dan tarif bertanggal','CP17_R2_MASTER_RATE_VERSIONS_AND_BOM','CP17_R3_09_SWITCH_REFUSALS_AND_ACCESS','CP17_R3_09_CHOOSE_NEW_PAYS_THROUGH_REVISION','CP17_R3_09_NEW_RATE_WAGE_TO_PAYROLL_AND_DETECTORS','OLD/NEW dan per-PO always-new hanya Owner/Admin; old wage tidak ditulis ulang.'),
('CP4','Nomor PO otomatis, draft/post dan rollback atomik','CP17_R3_01_AUTO_PO_NUMBER_1000_BOUNDED','CP17_R2_D15_6_AUTO_PO_FAILURE_MIDWAY_LEAVES_NOTHING','CP17_R2_D15_6_AUTO_PO_DRAFT_NO_STOCK_NO_FINANCE','CP17_R2_D15_6_AUTO_PO_THEN_BAGI_POTONGAN_AND_SEWING','999/1000/1001/10000, same UUID dan batas tiga detik terukur di CP17.'),
('CP4','Cutting create/edit/post, material issue dan reopen','P08_ACTUAL_PHYSICAL_CUT','CP7_CUTTING_REOPEN_PICKUP_DOWNSTREAM','CP7_CUTTING_REOPEN_EXACT_STOCK_GL_DRAFT','P09_TRANSFER_PRODUCTION_LATE_INVOICE','Correction sebelum sewing; setelah dependensi aktif harus inverse sah lebih dahulu.'),
('CP4','Pickup mandor dan pembatalan','CP17_R2_D15_6_AUTO_PO_THEN_BAGI_POTONGAN_AND_SEWING','CP17_SG01_PICKUP_REVERSE_REFUSED','CP17_SG01_PICKUP_REVERSE_BEFORE_SEWING','CP17_G1_SEWING_RECORD_WAGE_READY_FOR_LAUNDRY','PO dan material posted tidak ikut dibalik ketika pickup saja dibatalkan.'),
('CP4','Sewing biasa dan per-SKU, upah sekali','CP17_G1_SEWING_RECORD_WAGE_READY_FOR_LAUNDRY','CP17_G1_SEWING_REFUSALS_UNCHANGED','CP17_G1_SEWING_CANCEL_ONLY_AT_MANDOR','CP17_R3_09_NEW_RATE_WAGE_TO_PAYROLL_AND_DETECTORS','Upah dari selesai dijahit, bukan menunggu denominator barang kembali GOOD.'),
('CP4','Kain kembali/correct return yang sah','CP17_SG02_RETURN_STOCK_VALUE_PO_COST','CP17_SG02_OVER_REMAINDER_REFUSED','CP17_SG02_CORRECT_RETURN_ONE_TRANSACTION','CP17_SG02_CANCEL_RETURN_RESTORES_STOCK_GL_COST','Single compound transaction, original dan inverse tersimpan; tanggal sumber dipertahankan.'),
('CP4','Finish/reopen PO dan HPP','CP17_G2_FINISH_PO_FINAL_HPP_WIP_CLOSED','CP17_G2_FINISH_REFUSALS_UNCHANGED','CP17_R4_02_POSITIVE_INVERSE_REOPEN_THEN_FINISH_SAME','CP17_R4_02_POSITIVE_INVERSE_DOES_NOT_HIDE_ACTIVE_USE','FINISHED sah dapat BELUM_LENGKAP/ESTIMATED; tidak diberi label ACTUAL palsu.'),
('CP4','Pool HPP attendance, activate/cancel/replacement','CP17_R3_04_HPP_POOL_CREATE_ACTIVATE_CANCEL_EQUALS_NATIVE','CP17_R3_04_HPP_POOL_CLOSED_PERIOD_REFUSED_ATOMICALLY','CP17_R3_04_HPP_POOL_CANCEL_SOURCE_CORRECTION_REPLACEMENT','CP17_R3_04_HPP_POOL_PREVIEW_READY_AND_BLOCKED','Public legacy route ditutup Data API; Native DB guard batas D14-9. Held independent pool probe tidak dijalankan.'),
('CP5','Receipt bahan estimated/final dan inverse','P09_DRAFT_ESTIMATED_GRNI','P09_INVALID_ATOMIC','P09_RECEIPT_REVERSE_ESTIMATED','RF_PRICE_AFTER_SALE_AND_RETURN','Draft bukan stok; estimated GRNI bukan final AP.'),
('CP5','Invoice supplier parsial/multi-receipt/exact','P09_INVOICE_COMPLETE_MULTI_RECEIPT','P09_INVOICE_ATOMIC_REFUSALS','P09_INVOICE_STAGED_AND_REVERSE','P18_E13_LATE_SUPPLIER_PRICE_AFTER_FULL_CYCLE','Harga bukan stok tambahan; discount/precision dan receipt lineage lengkap.'),
('CP5','Return supplier/portable credit/alokasi ulang','P09_RETURN_PARTIAL_AP_GRNI','P09_RETURN_ATOMIC_LINEAGE','P09_COMBINED_RETURN_FABRIC_CREDIT_INVERSE','F03_P09_NATIVE_PAID_SUPPLIER_CREDIT_CARRY','Pihak dan sumber sama; paid child memblokir reuse yang tidak sah.'),
('CP5','Pembayaran supplier create/correct/inverse','CP7_SUPPLIER_PAYMENT_CREATE_EXACT_REPLAY_SETTLE','CP17_CASH_EMPTY_BANK_REFUSED','CP7_SUPPLIER_PAYMENT_CORRECTION_EXACT_CENTS','CP7_SOURCE_SUPPLIER_PAYMENT_INVERSE','Cash tanggal ekonomi dan book date, accrual floor serta huge exact cents.'),
('CP5','Transfer roll/aksesori/other lintas lokasi','P09_TRANSFER_CONSERVATION','P09_TRANSFER_HISTORICAL_PREFIX','P09_TRANSFER_CONSUMED_REVERSE','P09_TRANSFER_CLOSED_DAY_LATE_INVOICE','Jumlah/nilai seluruh lokasi nol, tanpa roll palsu pada barang null-roll.'),
('CP5','Stock count/opname bahan dan aksesori','P09_COUNT_FABRIC','P09_COUNT_FORGED_ATOMIC','P09_COUNT_MULTI_EDIT_INVERSE','P09_COUNT_ACCESSORY','Physical entered, system delta dari Native; unrecorded cost bukan nol.'),
('CP5','Laundry physical delivery/receipt/correction','SOL_R4_B5_B6_ORDINARY_DESKTOP','CP7_SOURCE_LAUNDRY_DEPENDENCIES','CP7_SOURCE_LAUNDRY_DOCUMENTS','SOL_R4_B5_B6_ORDINARY_MOBILE','Q3 ordinary3 menjalankan sewing→send→receipt→QC pada satu lineage; tiga first INCOMPLETE tetap tersimpan.'),
('CP5','Laundry pricing dan invoice vendor/koreksi harga','SOL_R4_B5_B6_ORDINARY_DESKTOP','CP17_CASH_LAUNDRY_VENDOR_EMPTY_BANK_REFUSED','BD_BROWSER:DEC06_CORRECTION_UP_DOWN_ON_SCREEN','SOL_R4_B5_B6_ORDINARY_IPAD_VIEWPORT','Q3 ordinary3/claim1 menutup draft/edit/post invoice8, payment/credit dan inverse; BD document dan core payable dibaca terpisah.'),
('CP5','Klaim laundry dan pemakaian kredit/AP/kas','SOL_R4_B5_B6_CLAIM_MOBILE','CP17_FIN02_CLAIM_BEFORE_SOURCE_REFUSED','SOL_R4_B5_B6_CLAIM_MOBILE','SOL_R4_B5_B6_CLAIM_MOBILE','Q3 claim mobile: lima sent/empat GOOD, total130; kompensasi2 hanya AP/OTHER_EXPENSE, cicilan6 dan seluruh inverse; physical/HPP tetap.'),
('CP5','Free same-product rewash dan hasil/reversal','SOL_R4_B5_FREE_REWASH_SAME_PRODUCT_DESKTOP','@RETAINED_CP6_CLOSED','SOL_R4_B5_FREE_REWASH_SAME_PRODUCT_DESKTOP','CP7_SOURCE_REWORK_DOCUMENTS','UI free same-product rewash empat aksi lulus pada initial run39193738642; inverse sah, AP/wage/rework journal tetap0. Tidak diulang.'),
('CP5','BS, ordinary rework dan hak kerja','CP17_RWK01_GOOD_CONTROL','CP17_RWK01_ALL_SCRAP_REWORK_PAYABLE_ONCE','CP7_SOURCE_REWORK_DOCUMENTS','CP17_RWK01_OPEN_CASE_FINISHED_PART_PAID_ONCE','Hak kerja dan reimbursement bukan lagi upah baru setiap kali barang dicuci ulang.'),
('CP5','QC final SKU, grade/size, FG dan inverse','CP17_BROWSER_R3_05_QC_FINAL_SKU_DESKTOP','CP7_SOURCE_LAUNDRY_DEPENDENCIES','CP7_SOURCE_LAUNDRY_DEPENDENCIES','P10_FG_NATIVE_SOURCE','Good/BS/lot/receipt FK persis; source fixture terpisah dari browser post.'),
('CP5','FG stock adjustment/count/book rank','P10_ADJUST_POSITIVE_VALUE','P10_ADJUST_FORGED_ATOMIC','P10_ADJUST_MULTI_EDIT_VERSION','P10_BOOK_REORDER_FACTS','Rank tampilan tidak mengubah physical stock, HPP atau laporan.'),
('CP5','Ganti merek/celup ulang/pocket origins','F03_X04_REWORK_NEW_CONTRACTOR','F03_X04_PO_PIN_MISMATCH_REFUSED','@RETAINED_CP6_CLOSED','CP7_SOURCE_REWORK_DOCUMENTS','Accepted unchanged Native BE/BF source; current X04 source pin dan biaya dibaca. Tidak fresh seluruh CP6.'),
('CP7','Sales draft multi-line/manual13/post/inverse','P11_DRAFT_MULTI_CREATE_EDIT_POST','P11_DRAFT_INSUFFICIENT_EDIT','CP7_SALES_CHAIN_EXACT','P11_READ_NATIVE_LIFECYCLE','Reservation tidak double-deduct saat post; original posted tidak diedit.'),
('CP7','Customer payment/correct/inverse','P11_PAYMENT_EXACT_LIFECYCLE','P11_PAYMENT_SOURCE_CHANGE','CP7_PAYMENT_CORRECTION_EXACT_CENTS','P13_REPORT_LEDGER_LIFECYCLE','Bukan pendapatan atau HPP kedua; 364 prefix sesudah koreksi dihitung ulang.'),
('CP7','Sales return per allocation/grade/correction','P11_RETURN_LIFECYCLE','P11_RETURN_PAID_REFUSAL','CP7_RETURN_CORRECTION_TWO_ALLOCATIONS','CP7_RETURN_CORRECTION_YEAR_364','Duplicate product/lot tidak membuat allocation ID dapat ditukar.'),
('CP7','Customer refund/custody source','F03_E03_NATIVE_LEGACY_REFUND','P11_RETURN_CONSUMED','F03_E03_NATIVE_IMPORTED_REFUND','F03_E03_NATIVE_LEGACY_REFUND','Service customer-owned tidak masuk FG/HPP perusahaan; refund punya credit source sendiri.'),
('CP7','Attendance roster/rate dated/current version','P12_ROSTER_LIFECYCLE','P12_ROSTER_FIELDS','P12_ROSTER_POSTED_HISTORY','P12_ATTENDANCE_WRITE_DATED_RATES','Blank attendance tidak disimpulkan HADIR/ABSEN, role/period/current revisions wajib.'),
('CP7','Attendance record/correction/consumed source','P12_ATTENDANCE_WRITE_LIFECYCLE','P12_ATTENDANCE_WRITE_CONSUMED','P12_ATTENDANCE_WRITE_CORRECTION','P12_SETTLEMENT_ATTENDANCE_ACCRUAL','Koreksi consumed perlu release/payroll inverse lebih dahulu, bukan edit fakta lama.'),
('CP7','Nota mandor/source allocation','P12_NOTA_SAVE_POST_REPLAY','P12_NOTA_STALE_SOURCE','P12_NOTA_CANCEL_RELEASE','P12_SETTLEMENT_PRESERVE_SELECTED_WORK','Source page lengkap, satu hak kerja tidak diambil nota dua kali.'),
('CP7','Nota ambil aksesori ke payroll deduction','CP17_BROWSER_R3_05_ACCESSORY_NOTE_TO_PAYROLL_DESKTOP','P12_SETTLEMENT_INVALID_PAY_CANCEL','CP7_SOURCE_ACCESSORY_DOCUMENTS','P12_SETTLEMENT_KASBON_CARRY','7*300=2100; reversed3*500 tidak dihitung; net6000−2100=3900.'),
('CP7','Payroll approve/partial/final/inverse','P12_SETTLEMENT_FULL_LIFECYCLE','CP17_FIN01_INSTALLMENT_BEFORE_ACCRUAL_REFUSED','P12_PAYROLL_READ_REVERSED_HISTORY','E05_EXACT_LARGE_CENTS','Approval menimbulkan hak/biaya; pembayaran hanya settlement, tanggal tidak sebelum accrual.'),
('CP7','Kasbon GIVE/ALLOCATE/release/cancel','CP17_KASBON_GIVE_DEDUCT_PAY','CP17_KASBON_LIMITS_REFUSED','CP17_KASBON_RELEASE_CANCEL_REPLAY','P12_SETTLEMENT_KASBON_CARRY','Net tak negatif, carry tersimpan, zero-net tidak membuat jurnal kas.'),
('CP6/CP7','Opening import/validate/finalize/inverse downstream','P12_OPENING_LIFECYCLE','CP17_R2_D15_5_CUTOVER_FAILURE_MIDWAY_LEAVES_NOTHING','P12_OPENING_CANCEL','CP17_R2_D15_5_CUTOVER_OPENING_PATH_LATE_INVOICE_SETTLEMENT','Data sintetis, bukan real cutover atau satu periode shadow.'),
('CP7','Misc income/expense/correction/cash prefix','CP17_R2_SPENT_INCOME_CORRECTION_COMMITS','CP17_CASH_BACKDATE_BEFORE_FUNDS_REFUSED','CP17_R2_MISC_SPENT_INCOME_CORRECTION_COMMITS','P13_ANALYSIS_INVERSE_DATES','Compound cash rule berlaku saldo akhir; penggunaan income yang sah tidak diblokir palsu.'),
('CP7','Laporan GL/AR/AP/cash dan known/current vs filed','P13_REPORT_LEDGER_LIFECYCLE','P13_REPORT_QUERY','P13_REPORT_FILED_LATE_CORRECTION','F03_COMBINED_LEDGER','As-filed immutable; facade finance menolak arbitrary as_known. Finance latency D17-2 tetap OPEN.'),
('CP7','Tutup/reopen periode dan filing immutable','P13_PERIOD_CLOSE_REOPEN','P13_PERIOD_BLOCKED','P13_PERIOD_LATE_ARCHIVE','P13_REPORT_FILING_PAGES','Satu tab finance, permission report/period terpisah; current READY tidak menghapus change marker.'),
('CP7','Recost bounded queue/retry/per tanggal','P13_RECOST_LATE_COST','P13_RECOST_BOUNDED_FAILURE','P13_RECOST_RETRY','F03_E06_YEAR_END_INCREASE_UTC','Max20 completed berbeda dari attempted, fault bukan selesai; sejarah sale tetap immutable.'),
('CP7','Native source capture/projection/model/capacity','P14_NATIVE_ANALYSIS_FROZEN_NATIVE','P14_NATIVE_ANALYSIS_MISSING_POLICY','P08_VERSION','P15_NATIVE_ANALYSIS_FINANCE_SAME_SOURCE','Kernel/factory proof berbeda; projected7 bukan physical7; global source tidak diubah filter tampilan.'),
('CP7','Native plan draft/apply/cancel/current recheck','SOL_R4_SKN24_NATIVE_MATCH_ALLOCATE_PLAN_COMMAND','P08_PHYSICAL_WRONG_MATERIAL_DRAFT','P08_SHARED_FABRIC_NATIVE_DRAFT_EDIT','P08_ACTUAL_PARTIAL_LIFECYCLE','Finite Native matching8→7, color mismatch dan relabel CANDIDATE ditolak; public command menolak extra matching dan membuat satu draft2 dari Original sah, tanpa stok/uang/HPP.'),
('CP7','Publication/report/AI immutable current-authorized output','P15_OBLIGATION_REPORT_NATIVE_EXACT_DATED_NATIVE','P15_OBLIGATION_REPORT_NATIVE_CURRENT_FINE_RIGHTS','P15_OBLIGATION_REPORT_NATIVE_LINKED_REVISION','P17_BROWSER_DESKTOP_NATIVE_HANDOFF','Exact body/UTF8 source escaping; model obedience dan provider contact tidak diuji.'),
('CP7','Manual reminder/current episode/ACK/snooze','CP17_R3_03_REMINDERS_CREATE_EDIT_NATIVE_ROW_AND_AUDIT','CP17_R3_03_REMINDERS_DENIED_WITHOUT_KEYS','CP17_R3_03_REMINDERS_DONE_REOPEN_CANCEL_NATIVE_ROW_AND_AUDIT','P16_NATIVE_ATTENTION_REVIEW_METADATA','Review/archive bukan debt resolved; actual Native settlement/inverse menentukan episode.'),
('CP7','Versioned reminder policy/local claim/ambiguity','P16_RULE_SOURCE_LOCAL_UTF8_CAPTURE','P16_RULE_SOURCE_LOCAL_DISABLED_SUPPRESSION','P16_RULE_SOURCE_LOCAL_MANUAL_RESOLUTION','P16_RULE_SOURCE_LOCAL_NATIVE_HEAL','Local preview belum dikirim; UNKNOWN tidak otomatis resend atau dianggap selesai.'),
('CP7','Staged runner/closed-page/current auth/budget','K4R_RACE_PG_CRON_FINISHES_JOB','K4R_LIMIT_REQUIRED','K4R_RACE_COLD_START_TWO_TICKS','@Q1_STATE_RESULT_REVIEW.json','K4 raw17, Q1metadata4 terpisah; future production scheduler CP7C.'),
('CP7','Server physical proof bounded/shared tick','K6P_RACE_PG_CRON_FINISHES_PASS','K6P_LIMIT_REQUIRED','K6P_CANCEL_CORRECT_BACKDATE_REPROVEN_BY_SERVER','@Q1_STATE_RESULT_REVIEW.json','151group includes labelled spent clones; ordinary five-group positive terpisah, no capture-time work.'),
('CP7','Large transport/pages/caps and honest refusal','P19S_BROWSER_DESKTOP_100','P08_PHYSICAL_WIP_IDENTITY_UPPER_BOUND','@PERFORMANCE_RESULT_REVIEW.json','@PERFORMANCE_RESULT_REVIEW.json','5business IDs/48 measurements bukan48 transaksi baru atau all-size SLA.'),
('CP7','Riwayat pelanggan/CSV dan audit trail listing','CP17_BROWSER_R3_03_HISTORY_DESKTOP','CP17_R3_03_HISTORY_AMOUNTS_HIDDEN_WITHOUT_AR','CP17_R3_03_HISTORY_REVERSALS_LISTED_NOT_COUNTED','CP17_BROWSER_R3_03_AUDIT_DESKTOP','CSV actual sesuai rows tampil; current audit content marker bukan immutable transaction snapshot.'),
('CP7','ERP settings/policy source dan warehouse summary','CP17_R3_03_ERP_SETTINGS_FACADE_EQUALS_NATIVE','CP17_R3_03_ERP_SETTINGS_NON_OWNER_REFUSED_BY_NATIVE','CP17_R3_03_ERP_SETTINGS_SET_CHANGES_ONLY_THAT_POLICY','CP17_R3_03_WAREHOUSE_RECEIPT_CUTTING_EQUALS_NATIVE_AND_READS','Satu Native policy/source, non-admin redaction dan mutation read-only dibedakan.'),
]

def evidence(value):
 if value.startswith('@'):
  doc=value[1:]
  if doc=='RETAINED_CP6_CLOSED':return dict(kind='ACCEPTED_UNCHANGED_CP6_SCOPE',seal='ff6374ad6edef19896c32258e3f30172a95069bd',runtime_credit_r4=0,review='CP6_SCOPE_RETENTION.json')
  assert (R/doc).exists(),doc
  return dict(kind='AUDITOR_REVIEW_DOCUMENT',path=doc,sha256=sha256((R/doc).read_bytes()).hexdigest())
 # Exact IDs only; unresolved manual transcription is explicit, never auto-PASS.
 if value not in by:return dict(kind='UNRESOLVED_NAVIGATION_ID',requested=value)
 row=by[value][0]
 return dict(kind='REVIEWED_CURRENT_CASE',**{k:row[k]for k in ('case_id','run_id','artifact_id','group','raw_status')},oracle_origin=row.get('oracle_origin','WRITER_ACCEPTED_ORACLE_EXECUTED_BY_SOL'),fixture_origin=row.get('fixture_origin','WRITER_SYNTHETIC_NATIVE_FIXTURE'),review_document=row.get('review_document'))
rows=[]
for i,(cp,need,pos,ref,corr,down,limit) in enumerate(D,1):
 row=dict(id=f'FUN-{i:03d}',checkpoint=cp,defined_need=need,positive=evidence(pos),refusal=evidence(ref),correction_or_revision=evidence(corr),downstream=evidence(down),scope_limit=limit,oracle_origin='WRITER_ACCEPTED_CONTRACT_ORACLE_PLUS_SOL_REVIEWED_LITERAL_DOCUMENT_ARITHMETIC; individual audit qualifications separately labelled',status='QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE')
 if any(row[k].get('kind')=='UNRESOLVED_NAVIGATION_ID'for k in ('positive','refusal','correction_or_revision','downstream')):row['status']='NAVIGATION_REQUIRES_EXACT_ID_BINDING'
 if i in (39,41):
  dispute=json.loads((R/'PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json').read_text())
  assert dispute['false_alarm_reproduced'] is True
  row.update(status='FINANCIAL_LIFECYCLE_QUALIFIED_INTEGRITY_FAIL_S1',integrity_finding='SOL-R4-001',integrity_counterexample=evidence('SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM'),financial_amounts_wrong=False,period_close_or_payment_UI_blocking='NOT_VERIFIED')
  row['scope_limit']+=' Valid FG_REPAIR Nota 2 lines/6000 has correct source/contractor/component but raises2 false CRITICAL wrong-contractor alarms. Financial proof remains separate; end-to-end integrity is FAIL, see PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json.'
 rows.append(row)
text=(REPO/'src/screenActivation.ts').read_text();screens=[dict(route=a or b,label=label,section=section,enteng=enteng,test=test)for a,b,label,section,enteng,test in re.findall(r"^\s*(?:'([^']+)'|([\w-]+)):\s*\{ label: '([^']+)', section: '([^']+)', enteng: '([^']+)', test: '([^']+)'",text,re.M)]
assert len(screens)==47
route_functions={
'dashboard':[2,45,57],'cutting-roll':[12,13,16,48,49],'mandor-wip':[14,15,29],'sewing-wip':[15,17,48],
'laundry':[25,26,27,28],'qc':[30],'fg-handoff':[39],'bs-rework':[27,28,29],
'warehouse-dashboard':[19,23,24,31,57],'procurement':[19,20,21,22],'materials-rolls':[19,23,24],
'pocket-fabric':[23,32,43],'accessories':[10,23,24,40],'fg-summary':[30,31,32,57],
'movements-vivo':[23,24,31,32],'movements-widie':[23,24,31,32],'stock-card':[23,24,31],
'stock-adjustment':[24,31],'brand-conversion':[32],'sales-invoice':[33],'sales-allocation':[33],
'sales-returns':[35,36],'sales-payments':[34,36],'sales-history':[33,34,35,56],
'finance-overview':[45],'finance-cash':[22,34,36,41,44,45],'finance-ap':[20,21,22,26,27,41,45],
'finance-ar':[34,35,36,42,45],'finance-payroll':[39,40,41,42],
'operations-attendance':[37,38],'contractor-issue':[40,42],'hpp':[17,18,47],
'finance-journal':[44,45],'finance-reports':[45,46],
'master-fabric':[9,10],'master-accessory':[10,40],'master-products':[1,11,30,32],
'master-customers':[8],'master-partners':[9],'master-workforce':[11,37],
'master-locations':[9,23],'master-pattern':[11,13,48,49],
'admin-reminders':[51,52],'admin-access':[6,7],'admin-settings':[57],
'admin-import':[43],'admin-audit':[56]}
assert set(route_functions)=={r['route']for r in screens}
for screen in screens:
 screen['defined_need_ids']=[f'FUN-{n:03d}'for n in route_functions[screen['route']]]
 screen['census_evidence']='CP17_RESULT_REVIEW.json / INITIAL_RESULT_REVIEW.json'
 screen['runtime_scope']='CONNECTED_NATIVE_LOOPBACK; activation census is separate from each function lifecycle'
 if screen['route']=='master-products':screen['explicit_limit']='Canonical product/model/size identity and master Native source retained unchanged from accepted CP4/CP6; current consumers/QC/source mappings exercised. No fresh all-product-CRUD browser claim.'
 if screen['route']=='fg-handoff':screen['source_binding']='ConnectedFgHandoffBoundary returns ConnectedNotaPage; work-right/nota needs, not sales.'
 for fn in screen['defined_need_ids']:rows[int(fn[4:])-1].setdefault('routes',[]).append(screen['route'])
result=dict(candidate_sha='663f6faefcbb9c70f0f99bbc7e78164e03521329',state='FINAL_DEFINED_NEED_LIFECYCLE_AND_INTEGRITY_DISPOSITIONS',defined_function_rows=len(rows),screen_rows=47,source_screen_table_sha256=sha256(text.encode()).hexdigest(),method='Manual lifecycle mapping to already-read exact case IDs/review docs. Navigation lookup never creates PASS or runtime credit. Read-only needs use explicit revision/restore rather than fabricated financial correction.',rows=rows,screens=screens)
(R/'FUNCTION_DETAIL.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
lines=['# Inventaris kebutuhan dan siklus fungsi — Sol r4','','Kandidat `663f6fae`. Pemetaan ini melengkapi tabel checkpoint; setiap baris memiliki positif, penolakan, koreksi/revisi dan pembaca hilir dalam JSON. Bukti keuangan dan kegagalan integritas Nota/payroll dipisahkan.','','| ID | CP | Kebutuhan | Status cakupan | Batas |','|---|---|---|---|---|']
for row in rows:lines.append('|'+row['id']+'|'+row['checkpoint']+'|'+row['defined_need']+'|'+row['status']+'|'+row['scope_limit']+'|')
lines+=['','47 route dari `src/screenActivation.ts` disimpan satu per satu dalam JSON; census membuktikan hadir/aktivasi, sedangkan bukti angka dan lifecycle berasal dari baris fungsi di atas. Tidak ada rasio ini yang menyatakan persentase ERP.']
lines+=['','| Route | Kebutuhan terkait | Batas |','|---|---|---|']
for screen in screens:lines.append('|'+screen['route']+'|'+', '.join(screen['defined_need_ids'])+'|'+screen.get('explicit_limit',screen.get('source_binding','Sensus aktivasi dan witness siklus terpisah.'))+'|')
lines+=['','| ID fungsi | Positif | Penolakan | Koreksi/revisi | Pembaca hilir |','|---|---|---|---|---|']
def brief(item):return item.get('case_id',item.get('path',item.get('review','retained scope')))
for row in rows:lines.append('|'+row['id']+'|'+'|'.join(brief(row[k])for k in ('positive','refusal','correction_or_revision','downstream'))+'|')
(R/'FUNCTION_DETAIL.md').write_text('\n'.join(lines)+'\n')
print('functions',len(rows),'screens',len(screens),'unresolved',[(x['id'],[x[k]['requested']for k in ('positive','refusal','correction_or_revision','downstream')if x[k]['kind']=='UNRESOLVED_NAVIGATION_ID'])for x in rows if x['status'].startswith('NAVIGATION')])

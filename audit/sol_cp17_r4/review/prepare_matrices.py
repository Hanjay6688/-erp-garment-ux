"""Write manually adjudicated coverage rows with exact already-reviewed witnesses.

ID lookup is navigation only. Row status follows the written scope/qualification,
never the number of matched IDs. No product code or fixture is executed here.
"""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
PRIOR = ROOT / 'ci_receipts/retained_r3'
SEAL = 'ff6374ad6edef19896c32258e3f30172a95069bd'
CANDIDATE = '663f6faefcbb9c70f0f99bbc7e78164e03521329'

# Explicit semantic dispositions. PASS is always limited to these witnessed or
# retained scopes; INCOMPLETE is not a proved product defect.
I = {
'U01': ('P13_REPORT_LEDGER_LIFECYCLE|P18_FULL_CYCLE_STOCK_WIP_HPP_GL_PAYABLES_CASH', 'Jurnal dan sepuluh boundary P18 dihitung ulang; GL + delta kas = 0. Per tanggal sumber dan inverse yang diuji.'),
'U02': ('CP17_R3_04_HPP_POOL_SAME_UUID_REPLAYS_ONCE|CP7_SALES_CHAIN_REPLAY', 'UUID yang sama memberi satu efek; receipt asli sesudah inverse tetap outcome historis.'),
'U03': ('CP7_SALES_CHAIN_EXACT|P09_TRANSFER_CONSERVATION|P12_SETTLEMENT_FULL_LIFECYCLE', 'Inverse mengembalikan stok dan semua akun pada fixture, mempertahankan sumber dan tanggal aslinya.'),
'U04': ('P18_FULL_CYCLE_STOCK_WIP_HPP_GL_PAYABLES_CASH|F03_COMBINED_LEDGER', 'AP/AR/payroll/GRNI dan delapan delta laporan combined cocok dengan Native; bukan seluruh data nyata.'),
'U05': ('CP17_CASH_EMPTY_BANK_REFUSED|CP17_CASH_LATER_DAY_PROTECTED|CP17_R2_CASH_BOOK_DATE_REFUSED', 'Kas tidak negatif pada tanggal ekonomi maupun buku. P18 delta −1200 adalah perubahan dari modal1200, saldo akhir0.'),
'U06': ('P09_RETURN_EXACT_CENTS|P13_REPORT_EXACT_LARGE|P12_OPENING_LIFECYCLE', 'Transport decimal string, pembulatan sen dan contoh besar diperiksa; bukan semua pecahan/alokasi universal.'),
'U07': ('P11_PAYMENT_FIELDS|P11_RETURN_PAID_REFUSAL|P12_SETTLEMENT_KASBON_CARRY', 'Overpayment ditolak atomik; retur sesudah paid perlu inverse sah; kasbon dibatasi hak kerja.'),
'U08': ('P12_SETTLEMENT_FULL_LIFECYCLE|CP7_SOURCE_SUPPLIER_PAYMENT_INVERSE', 'Pembayaran/inverse mengubah kas dan kewajiban, tidak menggandakan stok, hak kerja atau HPP.'),
'S01': ('P09_TRANSFER_CONSERVATION|P10_ADJUST_NEGATIVE_VALUE|CP7_RETURN_CORRECTION_YEAR_364', 'Mutasi dan prefix buku/lot 367 baris dihitung ulang, termasuk 364 saldo sesudah koreksi.'),
'S02': ('P09_TRANSFER_HISTORICAL_PREFIX|P09_RECEIPT_REVERSE_HISTORY', 'Backdate yang merusak prefix ditolak tanpa efek; pemulihan dependensi memungkinkan inverse sah.'),
'S03': ('P09_TRANSFER_CONSERVATION|P09_ACCESSORY_LEDGER_TRANSFER', 'Transfer rol dan null-roll menjumlah nol kuantitas/nilai; invoice terlambat mengikuti lokasi tanpa stok baru.'),
'S04': ('CP7_CUTTING_REOPEN_EXACT_STOCK_GL_DRAFT|P09_TRANSFER_LOCATIONS_LINEAGE', 'Roll dan semua field movement asli dipertahankan dalam exact UTC; salah roll/bahan ditolak.'),
'S05': ('P09_UOM_DOZEN|P09_UOM_GROSS_FINAL|P09_UOM_DATED_MASTER', '2 lusin=24;0,5 gross=72; perubahan faktor10→20 tidak menulis ulang nilai snapshot lama.'),
'S06': ('P08_ACTUAL_PARTIAL_LIFECYCLE|CP17_R2_ASTRA_G1_G2_TEN_PIECES_CONSERVED', 'Dua PCS aktual menjadi satu WIP+satu FG; sepuluh PCS sewing/laundry/FG tetap terkonservasi pada fixture.'),
'S07': ('P11_RETURN_LIFECYCLE|CP17_BROWSER_R3_05_QC_FINAL_SKU_DESKTOP', 'QC final SKU, sale/return per lot/grade dan inverse diuji; same-lineage B5/B6 current qualified di JOURNEY_Q3_RESULT_REVIEW.'),
'H01': ('P18_FULL_CYCLE_STOCK_WIP_HPP_GL_PAYABLES_CASH|RF_PRICE_AFTER_SALE_AND_RETURN', 'Nilai FG45×15=675 dan perubahan source menyebar ke posisi/akun pada fixture yang dihitung ulang.'),
'H02': ('P18_E13_LATE_SUPPLIER_PRICE_AFTER_FULL_CYCLE|P12_SETTLEMENT_ATTENDANCE_ACCRUAL', 'Bahan/laundry/upah/pool mengalir sekali ke HPP; biaya dan sen residual tetap dijelaskan, bukan hilang.'),
'H03': ('F03_E06_YEAR_END_INCREASE_UTC|P13_RECOST_LATE_COST', 'Recost bertanggal dan closed-year/current recognition pada contoh diperiksa; arsip tidak ditulis ulang.'),
'H04': ('P09_INVOICE_STAGED_AND_REVERSE|P18_E13_LATE_SUPPLIER_PRICE_AFTER_FULL_CYCLE', 'Invoice parsial AP50→95/GRNI60→0; akhir invoice tidak menambah kuantitas, inverse mengembalikan.'),
'H05': ('RF_PRICE_AFTER_SALE_AND_RETURN|P18_E13_LATE_SUPPLIER_PRICE_AFTER_FULL_CYCLE', 'Sisa bahan/WIP/FG/COGS/retur yang masuk fixture ikut recost; tidak mengklaim seluruh permutasi.'),
'H06': ('P10_FG_DEFERRED_UNKNOWN|CP17_G2_FINISH_PO_FINAL_HPP_WIP_CLOSED', 'Unknown bukan nol. FINISHED yang sah dapat tetap BELUM_LENGKAP/ESTIMATED bila kontrak mengizinkan; tidak diklaim ACTUAL.'),
'P01': ('P11_READ_NATIVE_LIFECYCLE|CP7_SOURCE_SUPPLIER_PAYMENT_INVERSE', '80−20−30=30 AR; AP1000−260=740, inverse10 menjadi750. Semua sesuai dokumen aktif.'),
'P02': ('P12_OPENING_LIFECYCLE|F03_P09_NATIVE_PAID_SUPPLIER_CREDIT_CARRY', 'Sumber advance/kredit, kontraktor/pihak/tanggal/capacity dan pemulihan alokasi diuji dalam fixture yang dirujuk.'),
'P03': ('CP17_R3_03_REMINDERS_DONE_REOPEN_CANCEL_NATIVE_ROW_AND_AUDIT|P11_READ_NATIVE_LIFECYCLE', 'Status dokumen aktif/inverse menjadi sumber aging/reminder; ruang lingkup otomatis P19 dicatat terpisah.'),
'T01': ('P12_SETTLEMENT_WIB_PAYMENT_DATE|CP17_R2_D15_5_CUTOVER_DAY_BOUNDARY_JOURNAL_AND_STOCK', 'WIB dan cutover diukur; branch sesi di belakang WIB diuji. Branch ahead yang false belum dieksekusi, tidak disebut actual midnight.'),
'T02': ('CP17_R3_04_HPP_POOL_CLOSED_PERIOD_REFUSED_ATOMICALLY|CP17_R4_01_DATA_API_REFUSED_DATABASE_SESSION_UNCHANGED', 'Facade current menolak closed period;25 public Data API lama ditutup. Native DB sessions tetap sama sesuai D14-9, jadi invariant semua entrypoint belum ditutup.'),
'T03': ('CP17_SG02_BEFORE_CUT_OR_FUTURE_REFUSED|P11_RETURN_DATE_LOCATION', 'Tanggal fisik sebelum sumber/masa depan ditolak pada jalur Native/public yang diuji.'),
'T04': ('P15_REPORT_NATIVE_PERIOD_SCOPE|P13_REPORT_FILED_LATE_CORRECTION', 'Arsip/Original immutable dan batas pengetahuan tertentu teruji; arbitrary historical as-known untuk semua fakta belum tersedia.'),
'L01': ('P13_REPORT_LEDGER_LIFECYCLE|F03_COMBINED_LEDGER', 'Laporan berasal dari GL/Native yang sama; prior-day sale/current-day return mempunyai periode yang benar, wide60/30 vs single-day−20/−10.'),
'L02': ('P13_REPORT_FILED_LATE_CORRECTION|P15_REPORT_NATIVE_REVISION', 'As-filed/Original dan revisi tertaut immutable sesudah perubahan source; corrected READY tetap menyimpan change marker.'),
'L03': ('P15_REPORT_NATIVE_UNKNOWN_NOT_ZERO|P06_MATERIAL_NATIVE_MISSING_UNKNOWN', 'Unknown/null/absen dibedakan dari nol; tidak ada biaya/yield/kapasitas yang diisi secara diam-diam.'),
'L04': ('P13_PERIOD_BLOCKED|CP17_G2_FINISH_REFUSALS_UNCHANGED', 'Readiness Native yang belum pasti memblokir close/aksi yang bergantung padanya; status operasional tidak dipaksakan final HPP.'),
'L05': ('P13_ANALYSIS_O13|P15_REPORT_NATIVE_PERIOD_SCOPE', '1000→1200=20%, margin27→24=−3pp; periode dan versi dipertahankan, nol/negatif baseline tidak dibagi menjadi angka menyesatkan.'),
'L06': ('P13_REPORT_READ_ONLY_PRIVATE|P08_PHYSICAL_SINGLE_FREE_STOCK', 'Runner Native membandingkan seluruh boundary/public/sequence sesuai oracle; reader tidak menulis bisnis. Fixture admin dipisahkan.'),
'L07': ('P15_REPORT_NATIVE_CURRENT_FINANCE_AUTH|P15_NATIVE_ARCHIVE_CURRENT_OPS_AUTH|P17_BROWSER_DESKTOP_NATIVE_HANDOFF|CP17_BROWSER_R3_03_HISTORY_DESKTOP', 'Current Auth/RPC/Original/AI dan actual CSV terbukti pada jalur terpilih. Kombinasi download CSV history/audit dari halaman yang sudah memuat data sesudah revoke tanpa refetch belum dieksekusi; jangan menganggap bukti current403 di consumer lain menutup jalur file ini. Tidak ada probe keamanan baru.'),
'R01': ('P14_NATIVE_ANALYSIS_MISSING_POLICY|P14_NATIVE_ANALYSIS_UNKNOWN_WORK', 'Source stale, policy hilang, load/yield tidak pasti tetap perlu cek data; tidak ada rekomendasi dari angka karangan.'),
'R02': ('P14_NATIVE_ANALYSIS_FROZEN_NATIVE|P15_REPORT_NATIVE_TEMPLATES', 'Action card dan provenance bersumber Original yang sama dengan unknown/needed/feasible terpisah; cakupan kontrak lama tetap bertanggal.'),
'R03': ('P14_NATIVE_ANALYSIS_LATE_SUPPLY|P14_NATIVE_ANALYSIS_PAUSED', 'Prioritas/gap tidak hilang karena pause atau supply terlambat; alasan dan urutan pada Original terkunci.'),
'R04': ('P14_NATIVE_ANALYSIS_SIGNED_AVAILABLE|P08_SHARED_FABRIC_POSTED_ONCE', 'Draft100−24=76, post tidak mengurangi dua kali; shared roll10→4 setelah issue6 sekali. Surplus ukuran lain tidak menutup gap.'),
'R05': ('P14_NATIVE_ANALYSIS_LATE_SUPPLY|P08_PHYSICAL_INCOMING_LATE', 'Pasokan7 terlambat tidak memperbaiki gap100 lebih awal; incoming tidak bertanggal/overdue tidak disamakan siap.'),
'R06': ('P14_NATIVE_ANALYSIS_FROZEN_NATIVE', 'Model/selector M01–M08 dipertahankan dari seal lama plus PL model current. Positive tiga fold/holdout adalah kernel privat sintetis, bukan promosi histori Native saat ini.'),
'R07': ('P14_BROWSER_DESKTOP_SHARED_ANALYSIS|P15_REPORT_NATIVE_ACTOR_SCOPE', 'Prompt/read-only projection mengikuti Original/hak pada fixture; tidak ada auto-send/write/key URL. Exhaustive prompt injection tetap batas L07/SKN29.'),
'R08': ('P08_PREVIEW_READONLY|P08_NATIVE_APPLY', 'Hitung/preview tidak reservasi atau menulis uang. Apply hanya membuat Native draft sah dengan live recheck; bukan physical confirmation.'),
'R09': ('P06_MATERIAL_NATIVE_GROSS_ASSUMED|P08_PHYSICAL_WIP_IDENTITY_UPPER_BOUND', 'BOM2×93=186 masih ASSUMED; yield/identity belum terbukti membuat rentang/UNKNOWN, bukan feasible palsu.'),
'K01': ('CP7_SALES_CHAIN_OLD_CLOCKS|CP7_CUTTING_REOPEN_IMMUTABLE_HISTORY', 'Original posted, microseconds/source facts dan lineage tidak diubah oleh inverse/koreksi pada jalur yang disaksikan.'),
'K02': ('NOTE_YEAR_364|CP7_RETURN_CORRECTION_YEAR_364', 'Semua prefix source dan 364 saldo berikut dihitung ulang pada ekonomi aslinya; bukan keuntungan hari ini yang dibuat-buat.'),
'K03': ('CP7_SOURCE_INVOICES|CP7_SOURCE_RETURNS', 'Resolver mengikuti FK/lineage yang tepat, termasuk baris identik dan sumber di luar halaman pertama; tidak menebak UUID/atribut.'),
'K04': ('RF_PRICE_AFTER_SALE_AND_RETURN|CP7_CUTTING_REOPEN_EXACT_STOCK_GL_DRAFT', 'Penulisan Native yang diadopsi dalam koreksi telah dideklarasikan pada bundle/lineage; static delta34file ditinjau, bukan izin semua DML.'),
'K05': ('CP7_SALES_CHAIN_PENDING_DRAFT|P09_RECEIPT_REVERSE_INVOICE_RETURN', 'Draft/active invoice/return/payment dan pickup/consumption memblokir dengan identitas sumber sebelum efek.'),
'K06': ('CP7_SALES_CHAIN_REPLAY|P09_RETURN_REPLAY_STALE_SOURCE', 'Koreksi/replay/inverse berulang mempertahankan satu efek dan receipt historis, tidak menduplikasi mutasi aktif.'),
'K07': ('CP7_CUTTING_REOPEN_IMMUTABLE_HISTORY|P15_REPORT_NATIVE_IMMUTABLE', 'Penolakan update/delete/truncate pada fakta/lineage/Original yang diuji tetap dipertahankan; bukan poison semua detector.'),
'C01': ('CP7_SALES_CHAIN_REPLAY|CP7_CUTTING_REOPEN_REPLAY', 'UUID sama/intent sama sekali; intent berbeda atomik ditolak. Banyak kelompok identik lintas fase tidak dihitung oracle baru.'),
'C02': ('P11_COMMAND_CHILD_REVIEW|CP17_R3_04_HPP_POOL_CHANGED_REVIEW_TOKEN_REFUSED', 'Child/source berubah tanpa bump header tetap meretire review; token/version bukan hanya pemeriksaan UI.'),
'C03': ('CP7_SALES_CHAIN_RACE_STOCK_CHANGE|K4R_RACE_COLD_START_TWO_TICKS', 'Urutan dua sesi disaksikan pada scope spesifik. Barrier-only tidak diberi strict-race credit; sejumlah source menegakkan wait sebelum COMMIT tanpa mengekspor PID lengkap.'),
'C04': ('CP7_SALES_CHAIN_FINAL_INVOICE_FAILURE|CP7_CUTTING_REOPEN_ATOMIC_LATE_FAILURE', 'Fault sengaja di langkah akhir sesudah efek Native awal; stock/GL/group/UUID rollback seluruhnya sebelum disposal.'),
'C05': ('CP7_SALES_CHAIN_BROWSER_DESKTOP|P08_BROWSER_DESKTOP_NATIVE_DRAFT', 'Balasan committed hilang lalu reload memakai UUID sama; writer terkunci sampai outcome resolved pada kasus browser nyata.'),
'C06': ('CP7_CUTTING_REOPEN_EXACT_STOCK_GL_DRAFT|K4R_RACE_COLD_START_TWO_TICKS', 'Boundary/sesi/locks diperiksa pada kasus strict, copy terhapus, Auth0→0. P21 committed-use sengaja data berubah namun clone dibuang; bukan exact data restore oleh uninstall.'),
'A01': ('CP7_SALES_CHAIN_RACE_AUTH_RETIRE|P12_ATTENDANCE_RACE_REVOKE', 'Hak current sesudah wait/ketika unit berubah diperiksa. Level trace setiap race dibatasi oleh source/metadata yang tersimpan.'),
'A02': ('P14_NATIVE_ANALYSIS_CURRENT_REVOKE|CP17_R3_04_HPP_POOL_OWNER_ADMIN_ONLY_AND_FIELDS', 'Aktif/Owner/Admin/current authority pada facade diuji; kegagalan fixture STAFF bukan bukti penolakan ataupun ALLOW produk.'),
'A03': ('', 'Build r4 menjalankan client artifact/secret gate, 1861 test/221file; empat SARIF0hasil. C/C++ hanya fixture clock; mocked UI bukan Native/hosted.'),
'A04': ('', 'Advisor tiap suite yang dieksekusi diperiksa terhadap daftar RLS INFO CP7 yang ditinjau; tidak ada gate baru dari Q1 metadata yang tidak diukur.'),
'A05': ('CP17_R4_01_EVERY_PUBLIC_ROUTE_REVIEWED|P15_REPORT_NATIVE_ACTOR_SCOPE', 'Declared owner/grant/private context diverifikasi current,25 public closures berlaku Data API.82 Native grant ditunda D14-9; bukan global grant closure.'),
'UI01': ('P12_PAYROLL_READ_EXACT_PAGES|P13_ANALYSIS_BROWSER_DESKTOP', 'Nilai UI/Native yang sama dan format decimal dipertahankan; hasil percase, bukan jumlah request atau screenshot sebagai oracle.'),
'UI02': ('P14_BROWSER_DESKTOP_SHARED_ANALYSIS|P15_BROWSER_MOBILE_NATIVE_PUBLICATION', '403/source change/lost reply meretire fakta lama dan mempertahankan input pribadi; tidak mengembalikan cache uang tanpa current auth.'),
'UI03': ('CP7_CUTTING_REOPEN_BROWSER_DESKTOP|P11_PAYMENT_BROWSER_DESKTOP', 'Review/confirm dan no-partial refusal benar pada journey write yang dipilih. Seluruh jenis transaksi masih SKN27 belum lengkap.'),
'UI04': ('SOL_R4_B5_B6_ORDINARY_DESKTOP|SOL_R4_B5_B6_ORDINARY_MOBILE|SOL_R4_B5_B6_ORDINARY_IPAD_VIEWPORT', 'Q3 actual Chromium desktop1440×1000, mobile390×844 dan iPad viewport820×1180 menunjukkan signature sama: sewing4/upah16/GOOD4/FG4/FG+WIP124/invoice8/final AP0 kas8. Ini proof viewport, bukan hardware Apple fisik.'),
'POL01': ('PL5_NEW_START_YIELD|P14_NATIVE_ANALYSIS_MISSING_POLICY', 'Nilai belum disahkan tetap pending; estimate/operator fixture diberi label, bukan default kebijakan baru.'),
'POL02': ('PL5_NEW_START_YIELD|CP17_HPP01_EXCLUDED_CONTRACTOR_POLICY_REFUSED', 'Pending/excluded policy tidak menjadi yield100% atau nol biaya dan memblokir jalur yang bergantung padanya.'),
'POL03': ('CP17_R3_09_NEW_RATE_WAGE_TO_PAYROLL_AND_DETECTORS|P15_NATIVE_ANALYSIS_FINANCE_SAME_SOURCE|P16_OTHER_NATIVE_SOURCE_CONSERVATION', 'Sumber Native uang/upah/HPP/obligasi tetap satu pada fungsi yang didefinisikan dalam inventaris; exact body/compiler dan state comparator menautkan pembaca current. Tidak ada duplikasi aturan terbukti pada34delta source. Cash SOL-R1-001 tetap CLOSED qualified; ini bukan klaim verifikasi setiap algoritme yang mungkin.'),
'POL04': ('P11_DRAFT_BROWSER_DESKTOP|P11_DRAFT_BROWSER_MOBILE_RECOVERY', 'Owner superseded manual13 lama dibedakan dari pengganti browser nyata yang mempertahankan13. CP6 CLOSED tidak dibuka ulang karena scope hold historis.'),
'POL05': ('', 'Counterexample diterima/scope holds historis tetap status asli beserta keputusan; writer22failure dan first K6 writer9PASS/1INC tidak dihapus.'),
'M01': ('P12_OPENING_LIFECYCLE', 'Impor sumber sintetis teruji, tetapi baris saldo awal dokumen cutover nyata belum direkonsiliasi; CP7C ditunda.'),
'M02': ('P12_OPENING_BROWSER_DESKTOP_CYCLE|CP17_R2_D15_5_CUTOVER_FAILURE_MIDWAY_LEAVES_NOTHING', 'CSV/idempotency/validasi/inverse sumber sintetis dan partial-fault atomic dibuktikan; bukan data cutover nyata.'),
'M03': ('', 'Nol detector pada fixture tidak membuktikan sesudah real cutover. Tahap produksi/CP7C belum dijalankan.'),
'M04': ('', 'Tidak ada SQL hosted aktual pada sesi ini. Operator receipt/aligned clone dan r3 baseline retained bukan fresh hosted observation.'),
'M05': ('', 'CP6 CLOSED: refusal pra-admission dipertahankan qualified dari Sol r3 dengan sepuluh source byte-identik dan supabase tree sama. P21 r4 install/restore menguji integrasi berubah. Bukan fresh seluruh refusal atau hosted preflight; CP6_SCOPE_RETENTION.json.'),
'N01': ('CP17_R3_03_REMINDERS_DONE_REOPEN_CANCEL_NATIVE_ROW_AND_AUDIT', 'Episode/manual reminder lifecycle current teruji. P19/reminder/AI sudah dibaca; Native heal/inverse menentukan episode, bukan ACK/DONE/arsip dianggap utang lunas.'),
'N02': ('', 'ACK/snooze no-effect pada versi r3 dipertahankan dengan origin terpisah; tail r4 belum dipakai menutup klaim yang belum dibaca.'),
'D01': ('', 'Belum setiap detector mempunyai kontrol0→tepat+1→0 di run auditor current. Fixture buku benar0 saja tidak cukup.'),
'D02': ('CP17_R3_09_NEW_RATE_WAGE_TO_PAYROLL_AND_DETECTORS', 'Regresi tariff/payroll pada buku benar0 dan disposisi detector lama dipertahankan; tidak ada izin mematikan alarm atau menghapus first failure.'),
'D03': ('CP17_R3_09_NEW_RATE_WAGE_TO_PAYROLL_AND_DETECTORS', 'Sumber detector Native yang berlaku ditelusuri bersama r3 sealed scope; provenance table/fact saat runtime tidak diganti tabel historis kosong.'),
'D04': ('', 'Belum ada nol integritas sebelum/sesudah setiap29 skenario; pemeriksaan akhir/global0 tidak menggantikannya.'),
}
INCOMPLETE_I = {'T02','T04','L07','M01','M03','M04','D01','D04'}

S = {
1: ('NOTE_YEAR_364|CP7_RETURN_CORRECTION_YEAR_364', '364 hari sintetis dan seluruh prefix sesudah koreksi dihitung ulang; bukan aktivitas nyata setahun.'),
2: ('RF_PRICE_AFTER_SALE_AND_RETURN|P18_E13_LATE_SUPPLIER_PRICE_AFTER_FULL_CYCLE', 'Harga terlambat menyebar ke material/WIP/FG/COGS/retur pada fixture; tidak ada stok tambahan.'),
3: ('P13_PERIOD_CLOSE_REOPEN|P13_PERIOD_LATE_ARCHIVE', 'Close/reopen/reclose, koreksi sumber dan filing immutable teruji; batas semua entrypoint tetap INV-T02.'),
4: ('P11_PAYMENT_EXACT_LIFECYCLE|P12_OPENING_LIFECYCLE', 'Parsial/full/overpayment/refund/advance pada fixture; pembayaran tidak mengulang HPP.'),
5: ('P11_RETURN_LIFECYCLE|CP7_RETURN_CORRECTION_YEAR_364', 'Retur parsial, grade/cap, sesudah paid dan koreksi dibaca dengan inverse sah dan saldo tepat.'),
6: ('P09_COMBINED_INVOICE_ATOMIC|P11_RETURN_ALLOCATION_CAP', 'Duplikat/baris lineage menurut ID/source dan complete review teruji; retained identical-line controls tetap scope lama.'),
7: ('P09_RETURN_EXACT_CENTS|P13_REPORT_EXACT_LARGE', 'Contoh sen/huge diuji; semua1/3,0.005,alokasi dan batas intermediate semua jenis transaksi belum lengkap.'),
8: ('P15_REPORT_NATIVE_UNKNOWN_NOT_ZERO|P12_ROSTER_FIELDS', 'Unknown/null/empty/negative/zero eksplisit, tidak memakai error apa pun sebagai PASS.'),
9: ('P12_SETTLEMENT_WIB_PAYMENT_DATE', 'UTC/device/WIB counters teruji; tidak ada actual wall-clock23:59:59→00:00:00 atau proses lintas midnight current.'),
10: ('CP7_SALES_CHAIN_RACE_SAME_UUID|CP7_CUTTING_REOPEN_RACE_COMPETING', 'Dua sesi dan UUID/intent, dengan level Barrier vs observed wait terpisah.'),
11: ('CP7_SALES_CHAIN_BROWSER_DESKTOP|P12_ATTENDANCE_RACE_REVOKE', 'Lost committed response dan current revoke/inactive actual Auth, sumber/root dan cleanup tetap tercatat.'),
12: ('CP7_CUTTING_REOPEN_EXACT_STOCK_GL_DRAFT|P12_SETTLEMENT_FULL_LIFECYCLE', 'Draft/post/inverse dan koreksi berulang pada keluarga yang dirujuk; seluruh transaksi masih SKN27.'),
13: ('P09_TRANSFER_HISTORICAL_PREFIX|P09_RETURN_HISTORICAL_PREFIX', 'Negative historical prefix atomik ditolak sebelum efek; dependencies/inverse sah dibedakan.'),
14: ('P09_TRANSFER_CONSERVATION|P11_RETURN_SPLIT_GRADES', 'Lokasi/supplier/mandor/vendor pada fixture multi-entitas; tidak semua kartesius kombinasi.'),
15: ('RF_PRICE_AFTER_SALE_AND_RETURN|CP7_SOURCE_INVOICES', 'Koreksi identitas/quantity/price dan resolver FK tepat pada jalur yang disaksikan, source invalid atomic.'),
16: ('P12_OPENING_LIFECYCLE', 'Impor awal sintetis bukan sumber cutover nyata sampai satu periode; CP7C belum dijalankan.'),
17: ('P14_NATIVE_ANALYSIS_UNKNOWN_WORK|P08_PHYSICAL_INCOMING_NO_DATE', 'Unknown yield/deadline/load/harga tidak diisi nol, late supply tidak menghapus gap lebih awal.'),
18: ('P13_REPORT_CONCURRENT_CASH|P15_NATIVE_ANALYSIS_FINANCE_SAME_SOURCE', 'MVCC old/new coherent dan40actual financial reads/byte equivalence; no read business effect.'),
19: ('CP7_CUTTING_REOPEN_IMMUTABLE_HISTORY', 'Penolakan append-only teruji; semua detector poison+1/rollback0 belum lengkap.'),
20: ('CP17_R3_09_NEW_RATE_WAGE_TO_PAYROLL_AND_DETECTORS', 'Regrouping/identity history qualified retained r3, current source/rate boundaries tidak merusak physical/old wages; semua real-world history tidak diklaim.'),
21: ('', 'P21 aligned disposable current dan retained preflight bukan fresh actual-hosted install; tidak ada SQL hosted.'),
22: ('P18_FULL_CYCLE_STOCK_WIP_HPP_GL_PAYABLES_CASH|F03_COMBINED_LEDGER', 'Komposisi Native/real browser slices luas; bukan satu real cutover→satu periode→semua detector/BR/reminder/correction chain.'),
23: ('', 'CP6 CLOSED dipertahankan qualified: source canonical/regression/installer dan supabase byte-identik; CP7 guard baru dipasang sesudah preflight CP6, sehingga baseline canonical sebelum F03 tidak bergantung padanya. Broad current F03/CP17/P21 menutup perubahan integrasi yang dipilih. Tidak mengklaim326+AS34+AR174+AT16+AU15 fresh r4; CP6_SCOPE_RETENTION.json.'),
24: ('SOL_R4_SKN24_NATIVE_MATCH_ALLOCATE_PLAN_COMMAND', 'Satu sumber Native8→projected7/target100 gap93 yang sama ditelusuri matcher→allocator→rencana→public command. Pasangan cocok FEASIBLE; color mismatch dan relabel CANDIDATE ditolak. Extra matching ditolak di save/apply; payload legal menghasilkan satu draft2 tanpa physical stock/uang/HPP atau perubahan Original. Qualified finite contract control, bukan kartesius semua warna.'),
25: ('', 'Delapan amount delivery FREE/WAIVED/NORMAL prefreeze current dihitung ulang. Tidak diketahui/zero tanpa konfigurasi dibedakan, no fake final HPP.'),
26: ('SOL_R4_SKN26_PROCUREMENT_12_6_BOUNDARY|SOL_R4_SKN26_PROCUREMENT_SIX_DECIMAL_SCALE|SOL_R4_SKN26_PROCUREMENT_32BIT_CENT_AROUND|SOL_R4_SKN26_LAUNDRY_NUMERIC18_2_AND_TWO_LINES|SOL_R4_SKN26_ACTUAL_CLIENT_BOUNDARY_HELPERS|P09_COMPLETE_PAGES_OPTIONS|CP7_SOURCE_QC_HISTORY|CP7_SOURCE_CUTTING_NATIVE_PAGE100', 'Finite named facade/type classes: procurement12integer/6decimal under/at/above and six-scale, raw AP exact versus actual GL cents, 32bit-cent around, Native BD18,2 draft under/at/above and two lines/zero discount,27 actual pure client helpers including pool precision/count. Current source pages25/50/100/200/105 and huge exact-money paths retained separately. No global32bit N/A; maximum BD POST/cash and physical devices are not inferred from draft/helper evidence.'),
27: ('CP7_SALES_CHAIN_EXACT|CP7_CUTTING_REOPEN_EXACT_STOCK_GL_DRAFT|SOL_R4_B5_B6_ORDINARY_DESKTOP|SOL_R4_B5_B6_CLAIM_MOBILE|SOL_R4_B5_FREE_REWASH_SAME_PRODUCT_DESKTOP', 'Koreksi/revisi/inverse dan pembaca hilir dipetakan per57 kebutuhan pada FUNCTION_DETAIL, termasuk receipt/invoice/return/payment, production, payroll, cash, master/policy dan output. B5/B6 current one-lineage ordinary/claim serta free rewash selesai. Native immediate-post/versioned-master mengikuti kontrak diterima, bukan dibuat persistent DRAFT baru; sumber CP6 yang tidak berubah tetap retained, bukan fresh-all-CRUD claim.'),
28: ('CP7_SALES_CHAIN_OLD_CLOCKS|CP17_R3_09_CHOOSE_OLD_PAYS_LOCKED_RATE', 'Effective identity/rate/wage/source boundaries current + qualified prior lineage, original microseconds/old facts tidak ditulis ulang.'),
29: ('P14_BROWSER_DESKTOP_SHARED_ANALYSIS|P15_REPORT_NATIVE_CURRENT_FINANCE_AUTH|P17_BROWSER_DESKTOP_NATIVE_HANDOFF|CP17_BROWSER_R3_03_HISTORY_DESKTOP', 'Native/RPC/UI/CSV/prompt UTF8 dengan source framing dan instruksi dalam label diuji, episode/ACK/snooze/local transport teruji. Jalur file CSV yang sudah dimuat sesudah revoke tanpa refetch belum dieksekusi. Provider obedience/live delivery tidak diukur dan tidak diperlukan sebagai klaim test-sink; tidak ada security probe baru.'),
}
INCOMPLETE_S = {7,9,16,19,21,22,29}

C = {
'B1': ('P09_DRAFT_ESTIMATED_GRNI|P09_BROWSER_RECEIPT_DESKTOP', 'Public/Native/Auth browser receipt,GRNI,roll; master source sintetis.'),
'B2': ('P08_ACTUAL_PHYSICAL_CUT|CP7_CUTTING_REOPEN_EXACT_STOCK_GL_DRAFT', 'Cut issue dan inverse tepat, rencana bukan physical confirmation.'),
'B3': ('P08_ACTUAL_PARTIAL_LIFECYCLE', 'Pickup Native dua PCS aktual ditelusuri, browser source navigation bukan full factory journey.'),
'B4': ('CP17_G1_SEWING_RECORD_WAGE_READY_FOR_LAUNDRY|P12_NOTA_SOURCE_REGULAR_LAUNDRY_OUTSTANDING', 'Sewing→wage entitlement/ready Laundry teruji dalam fixture; upah tidak menunggu denominator retur-good palsu.'),
'B5': ('SOL_R4_B5_B6_ORDINARY_DESKTOP|SOL_R4_B5_B6_CLAIM_MOBILE|SOL_R4_B5_FREE_REWASH_SAME_PRODUCT_DESKTOP', 'Ordinary/claim satu lineage dari Native pickup start lalu actual UI sewing→send→GOOD receive→QC. Free same-product rewash dimulai dari Native QC/BS lalu empat actual UI create/partial/complete/inverse. Lot/SKU/receipt/quantity, WIP/FG/HPP dan no-double-wage/AP cocok. Seeded starting steps tidak dihitung sebagai langkah layar.'),
'B6': ('SOL_R4_B5_B6_ORDINARY_DESKTOP|SOL_R4_B5_B6_CLAIM_MOBILE', 'Actual same-lineage invoice draft/edit/post8→claim2 or ordinary→two cash payments→cash/credit/claim/invoice inverses. Ordinary total124/claim130; final AP0/kas8; source lot/SKU/HPP/physical unchanged, posted originals and inverses retained. Q3 qualifies genuine tool repair; all first INCOMPLETE remain.'),
'B7': ('CP17_BROWSER_R3_05_QC_FINAL_SKU_DESKTOP|P08_ACTUAL_PARTIAL_LIFECYCLE', 'Actual QC final SKU dan FG/BS, dengan Native-fixtured source dan real Auth browser.'),
'B8': ('CP17_G2_FINISH_PO_FINAL_HPP_WIP_CLOSED|CP17_R4_02_POSITIVE_INVERSE_REOPEN_THEN_FINISH_SAME', 'Finish/reopen satu FG/HPP, active usage; FINISHED tidak memalsukan ACTUAL bila HPP belum lengkap.'),
'B9': ('P10_BOOK_REORDER_FACTS|P10_ADJUST_NEGATIVE_VALUE', 'Book rank terpisah dari physical; adjustment/inverse dan qualified conversion scope retained.'),
'B10': ('P11_DRAFT_BROWSER_DESKTOP|P11_COMMAND_POST_ONCE', 'Create/edit/manual13/post dan reservation sekali, money/FG Native source sama.'),
'B11': ('P11_PAYMENT_BROWSER_DESKTOP|P11_PAYMENT_EXACT_LIFECYCLE', 'Actual AR partial/full/inverse, cents, no second stock/HPP.'),
'B12': ('P11_RETURN_BROWSER_R10_DESKTOP_A|P11_RETURN_LIFECYCLE', 'Return grade/location/allocation/cash dependencies, exact inverse and refund source bounded.'),
'B13': ('P13_REPORT_LEDGER_LIFECYCLE|P13_PERIOD_CLOSE_REOPEN|F03_COMBINED_LEDGER', 'GL/report/close/reopen dan periode sumber benar; finance latency tetap OPEN.'),
'S1': ('CP7_SOURCE_SUPPLIER_PAYMENT_BROWSER_DESKTOP|CP7_SOURCE_SUPPLIER_PAYMENT_INVERSE', '26th payment exact owning AP/cash, inverse once and no stock/HPP.'),
'S2': ('F03_P09_NATIVE_PAID_SUPPLIER_CREDIT_CARRY|P09_RETURN_FABRIC_PORTABLE_CREDIT', 'Return/credit reallocation same party/date, current paid child prevents unsafe reuse.'),
'S3': ('P12_ATTENDANCE_BROWSER_DESKTOP_CYCLE|P12_OPENING_BROWSER_DESKTOP_CYCLE', 'Attendance/nota/payroll approval/pay/inverse plus old opening obligations, no double accrual.'),
'S4': ('P12_SETTLEMENT_KASBON_CARRY|CP17_KASBON_GIVE_DEDUCT_PAY', 'Accessory/kasbon deduct limited to payable, carry retained, zero net no cash journal.'),
'S5': ('CP7_SOURCE_REWORK_DOCUMENTS|CP17_RWK01_OPEN_CASE_FINISHED_PART_PAID_ONCE', 'Ordinary rework2/labor60 plus eligibility/partial-paid, owning inverse; not all rewash full browser.'),
'S6': ('P09_COUNT_FABRIC|P09_BROWSER_COUNT_UNMOVED_DESKTOP|P10_ADJUST_NEGATIVE_VALUE', 'Physical count/adjust/inverse including registered zero-history position, unknown quantity/cost not defaulted.'),
'S7': ('P12_OPENING_BROWSER_DESKTOP_CYCLE|CP17_R2_D15_5_CUTOVER_OPENING_PATH_LATE_INVOICE_SETTLEMENT', 'Synthetic opening import→downstream/cutover floor qualified; real cutover remains INCOMPLETE.'),
}


def gap_action(ident,status):
    if status == 'FAIL':
      return dict(classification='PROVED_S1_VALID_FG_REPAIR_FALSE_ALARM',owner='Writer Native detector/installer then independent auditor',
                  action='Resolve supported FG_REPAIR source contractor/component from actual wage/receipt in the Native checker; retain real wrong-contractor/orphan detection and installer definition pins/restore. Retest valid Nota6000 with all167zero and legitimate negative controls. No alarm filtering or guard weakening.',executable_now=False)
    table={
      'INV-T02':('OWNER_DEFERRED_CP7C','Writer/operator CP7C','Native DB legacy wrappers/grants remain D14-9; execute already-defined install boundaries only at authorized CP7C. Data API25closure current verified.',False),
      'INV-T04':('UNIMPLEMENTED_GENERAL_QUERY_SEMANTICS','Writer contract/source','Current finance rejects arbitrary as_known; existing immutable filed/capture views are verified. Define supported historical knowledge view before any general as-known acceptance.',False),
      'INV-L07':('PRIOR_SESSION_SECURITY_SCOPE_HOLD','Audit coordinator','Review existing loaded CSV/history/audit download after permission revoke without refetch. New access/security probes remain held in this session; no product bug inferred.',False),
      'INV-UI04':('AUDITOR_QUALIFICATION_RUNNING','Sol','Read three declared ordinary desktop/mobile/iPad viewport originals after observer correction; physical Apple-device UAT is separate.',True),
      'INV-M01':('OWNER_DEFERRED_CP7C','Operator CP7C','Reconcile actual signed opening source documents, row by row, against approved cutover.',False),
      'INV-M03':('OWNER_DEFERRED_CP7C','Operator/auditor CP7C','Run all integrity checks before/after actual cutover and reconcile real controls.',False),
      'INV-M04':('HOSTED_OBSERVATION_NOT_AUTHORIZED','Operator CP7C','Capture actual hosted version/catalog/alignment receipt under permitted runbook; audit clone is not fresh hosted observation.',False),
      'INV-D01':('PROVED_S1_PLUS_PARTIAL_SENSITIVITY','Writer Native detector then independent auditor','Resolve the proved healthy FG_REPAIR false alarm first. Current21 exact identities,146 sensitivity gaps and two prevention-only controls have per-ID predicate/source/disposition. Static maps and normal zeros never confer sensitivity PASS.',False),
      'INV-D04':('SCENARIO_DEPENDENCY_DEFERRED','Auditor after executable scenario prerequisites','Per-scenario complete detector snapshots need all29scenario fixtures; actual cutover/hosted/midnight dependencies are currently unavailable or deferred. Final global0 is not a substitute.',False),
      'SKN-07':('EXACT_FRACTION_ORACLE_NOT_EXECUTED','Auditor','Current cents/huge6decimal paths and retained half-cent controls exist; one-third allocation contract/path lacks a current independently observed complete source allocation. Held pool probe is not resumed under another value.',False),
      'SKN-09':('WALL_CLOCK_ENVIRONMENT_NOT_AVAILABLE','Auditor timed CI','UTC/WIB and synthetic clock boundary controls exist; actual23:59:59->00:00:00 crossing was not scheduled/observed. Do not fake system clock or claim simulated passage.',False),
      'SKN-16':('OWNER_DEFERRED_CP7C','Operator/auditor CP7C','Real opening source->one full period/shadow reconciliation requires cutover documents/authorized operator action.',False),
      'SKN-19':('PARTIAL_SENSITIVITY_WITH_PROVED_FALSE_ALARM','Writer Native detector; auditor for remaining declared scope','Current21 exact identities and two source-bound guard-prevention controls are distinct. Remaining132 fact/lineage,11 held catalog/access,1 schema and2 guard-prevented sensitivities retain per-ID predicates and next actions; no outstanding current qualification run. Correct S1 healthy-book false alarm before integration acceptance.',False),
      'SKN-21':('HOSTED_BASELINE_UNAVAILABLE','Operator CP7C','Fresh actual-hosted clone/version with hosted-like non-superuser and every pre-admission refusal; existing aligned-source clone scope remains qualified.',False),
      'SKN-22':('OWNER_DEFERRED_REAL_CUTOVER_CHAIN','Operator/auditor CP7C','Synthetic P18/F03 end-to-end components pass; real cutover plus full period plus BR/reminder plus upstream correction requires authorized real-source shadow phase.',False),
      'SKN-24':('DEFINED_MATCHER_TO_COMMAND_LINK_NOT_EXECUTED','Auditor contract fixture','Kernel forged-CANDIDATE control is retained; Native plan/physical source identity current is tested. Exact one-output matcher->allocator->plan->public-command counterfixture remains unexecuted; no kernel-only PASS for full chain.',True),
      'SKN-26':('EXACT_TYPE_INTERMEDIATE_BOUNDARIES_NOT_COMPLETE','Auditor numeric source inventory','Current actual pagination limits25/50/100/200/105 and exact huge cents are proved; explicit under/at/above numeric(18,2) nominal maximum plus all intermediate casts not yet bound for every named money facade. No unproved32bit N/A.',True),
      'SKN-27':('AUDITOR_UI_QUALIFICATIONS_RUNNING','Sol','Read ordinary one-lineage and claim/free-rewash screen continuations after genuine observer repair; bind each function lifecycle in FUNCTION_DETAIL rather than generic all-transactions claim.',True),
      'SKN-29':('PRIOR_SESSION_SECURITY_SCOPE_HOLD','Audit coordinator','Actual CSV, protected Original and quoted prompt pass respective paths; loaded-file cache after revoke without refetch remains unexecuted. New access/security probes held, no live recipient/provider claims.',False),
      'B5':('AUDITOR_UI_QUALIFICATIONS_RUNNING','Sol','Read ordinary/claim one-lineage screen outputs and separate Native-start free-rewash create/partial/final/inverse. Preserve first observer failures and raw status.',True),
      'B6':('AUDITOR_UI_QUALIFICATIONS_RUNNING','Sol','Correct only proven draft observer table and read remaining invoice edit/post/payment/credit/inverses under frozen expected. No product fix or green-fishing identical retry.',True),
    }
    if status=='PASS':
      return dict(classification='QUALIFIED_DEFINED_SCOPE',owner='Writer regression / auditor next candidate',action='Retain exact witnessed or accepted-unchanged scope; no additional run required solely for more permutations.',executable_now=False)
    category,owner,action,now=table[ident]
    return dict(classification=category,owner=owner,action=action,executable_now=now)


def main():
    dispute_path = ROOT / 'PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json'
    confirmed_false_alarm = dispute_path.exists() and json.loads(dispute_path.read_text()).get('false_alarm_reproduced') is True
    if confirmed_false_alarm:
        finding_id = 'SOL_R4_INV_D02_VALID_FG_REPAIR_NOTA_ZERO_ALARM'
        I['D01'] = (finding_id, 'FAIL pada kontrol positif: Nota FG_REPAIR yang sah memberi dua false CRITICAL wrong_contractor. Kontrol sensitivitas21/167 terpisah; sisanya tetap TIDAK TERUJI, lihat DETECTOR_DISPOSITIONS. Tidak ada alarm yang difilter.')
        I['D02'] = (finding_id, 'COUNTEREXAMPLE S1: dua actual FG_REPAIR work lines, payroll/source contractor dan component sama, qty1+2/rate2000/total6000 benar, tetapi alarm wrong_contractor naik2; rollback0. Nilai stok/HPP/jurnal tidak salah karena Nota.')
        I['D03'] = (finding_id, 'Resolver detector hanya membaca PRODUCTION/REWORK; mesin Native/CP7 saat ini juga menulis source FG_REPAIR ke fg_unsourced_repair_wages_v1. Source live yang tidak di-resolve menghasilkan false alarm2 pada Nota sah.')
        old_ids, old_scope = C['S3']
        C['S3'] = (old_ids + '|' + finding_id, old_scope + ' Penerimaan integritas end-to-end FAIL pada FG_REPAIR Nota: actual source/6000 benar tetapi detector false CRITICAL2. Tidak mengklaim pembayaran atau period-close UI macet.')
    ledgers = [ROOT / 'ci_receipts/SOL_REVIEWED_CASE_LEDGER.jsonl', ROOT / 'ci_receipts/SOL_CP17_CASE_LEDGER.jsonl', ROOT / 'ci_receipts/SOL_QUALIFIED_CASE_INDEX.jsonl']
    records = [json.loads(line) for path in ledgers for line in path.read_text().splitlines()]
    by_id = {}
    for row in records:
        by_id.setdefault(row['case_id'], []).append(row)

    def witnesses(ids):
        out = []
        for case in ids.split('|') if ids else []:
            assert case in by_id, case
            row = by_id[case][0]
            out.append(dict({k: row[k] for k in ('case_id','run_id','artifact_id','group','raw_status')},oracle_origin=row.get('oracle_origin','WRITER_ACCEPTED_ORACLE_EXECUTED_BY_SOL'),fixture_origin=row.get('fixture_origin','WRITER_NATIVE_SYNTHETIC_FIXTURE'),review_document=row.get('review_document')))
        return out

    for filename, definitions, incomplete, id_key, count in [
        ('INVARIANT_MATRIX.json', I, INCOMPLETE_I, 'invariant', 82),
        ('SCENARIO_MATRIX.json', S, INCOMPLETE_S, 'id', 29),
        ('CHAIN_MATRIX.json', C, set(), 'id', 20)]:
        prior_path = PRIOR / filename
        prior = json.loads(prior_path.read_text())
        assert len(definitions) == len(prior['rows']) == count
        rows = []
        for old in prior['rows']:
            ident = old[id_key]
            key = ident.removeprefix('INV-') if filename.startswith('INVARIANT') else int(ident.removeprefix('SKN-')) if filename.startswith('SCENARIO') else ident
            ids, scope = definitions[key]
            status = 'FAIL' if confirmed_false_alarm and ((filename.startswith('INVARIANT') and key in ('D01','D02','D03')) or (filename.startswith('CHAIN') and key == 'S3')) else 'INCOMPLETE' if key in incomplete else 'PASS'
            current = witnesses(ids)
            rows.append({id_key: ident, 'requirement': old.get('requirement', old.get('chain')), 'status': status,
                         'current_scope': scope, 'current_witness_examples': current,
                         'evidence_origins': sorted({('INDEPENDENT_BROWSER_RERUN' if 'browser' in w['group'] else 'INDEPENDENT_NATIVE_RERUN') for w in current}) + ['REUSED_AUDITOR_LOG_READ'],
                         'review_document_refs': ['PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json','DETECTOR_DISPOSITIONS.json'] if status=='FAIL' else ['CP6_SCOPE_RETENTION.json'] if key in ('M05',23) else ['BUILD_RESULT_REVIEW.json','CODEQL_RESULT_REVIEW.json'] if key=='A03' else ['RESULT_REVIEW.json'] if key=='A04' else ['JOURNEY_Q3_RESULT_REVIEW.json','FUNCTION_DETAIL.json'] if key in ('UI04','B5','B6',27) else ['FUNCTIONAL_BOUNDARIES_RESULT_REVIEW.json'] if key in (24,26) else [],
                         'oracle_origin': 'Per-witness origin preserved: writer/legacy accepted oracles are distinct from Sol-designed contract qualifications. ID matching is navigation only.',
                         'qualification': 'PASS is limited to written current/retained scope, not every permutation, current whole-production gate or an ERP percentage. INCOMPLETE does not itself prove a product bug.',
                         'retained_r3': {'seal': SEAL, 'candidate': prior['candidate_sha'], 'status': old['status'],
                                         'path': 'audit/sol_cp17_r3/' + filename, 'runtime_credit_r4': 0},
                         'next_action': gap_action(ident, status)})
            if key == 'D01':
                detector = json.loads((ROOT / 'DETECTOR_DISPOSITIONS.json').read_text())
                rows[-1]['negative_sensitivity_dimension'] = dict(status='INCOMPLETE', counts=detector['status_counts'], detail='DETECTOR_DISPOSITIONS.json')
                rows[-1]['positive_healthy_book_dimension'] = 'FAIL_S1' if confirmed_false_alarm else 'VALID_NOTA_DISPUTE_PENDING'
        result = {'candidate_sha': CANDIDATE, 'report_state': 'FINAL_LIMITED_SCOPE_ASSESSMENT',
                  'audit_complete': False, 'denominator': count, 'status_counts': dict(Counter(r['status'] for r in rows)),
                  'retained_source_sha256': sha256(prior_path.read_bytes()).hexdigest(),
                  'witness_ledger_sha256': {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in ledgers},
                  'method': 'Each row manually adjudicated to a semantic scope; exact ID lookup only locates examples. No matched-count closes an invariant.',
                  'all_20_one_browser_chain_proven': False if count == 20 else None, 'rows': rows}
        (ROOT / filename).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        lines = ['# ' + filename.removesuffix('.json').replace('_',' ') + ' — Sol r4', '',
                 'Kandidat `' + CANDIDATE + '`. PASS selalu dalam lingkup tertulis; bukti r3 tetap bertanggal, dengan kredit runtime r4 nol. FAIL mempunyai bukti produk tersendiri. Tidak ada persentase ERP atau persetujuan produksi.', '',
                 '| ID | Status | Lingkup dan batas | Contoh witness yang sudah dibaca |', '|---|---|---|---|']
        for row in rows:
            lines.append('| ' + row[id_key] + ' | ' + row['status'] + ' | ' + row['current_scope'].replace('|','/') + ' | ' + ', '.join('`'+w['case_id']+'`' for w in row['current_witness_examples']) + ' |')
        (ROOT / filename.replace('.json','.md')).write_text('\n'.join(lines) + '\n')
        print(filename, count, result['status_counts'])


if __name__ == '__main__':
    main()

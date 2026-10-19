# Inventaris kebutuhan CP1–7 — Sol r5

57 kebutuhan dan47 layar adalah inventaris, bukan persentase ERP selesai. Bukti r4 dipertahankan dengan kredit eksekusi r5 nol; bukti r5 ada per dimensi di FUNCTION_DETAIL.json.

|ID|CP|Kebutuhan|Status terbatas|Batas|
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
|FUN-039|CP7|Nota mandor/source allocation|LIFECYCLE_SCOPED_AND_REPAIR_INTEGRITY_RETEST_PASS|Original valid repair Nota6000 all167zero, wrong/missing+1, REVERSED/reallocation zero, and F03P12 lifecycle pass. Other historical scope limits retained; no universal payment/period-close UI claim.|
|FUN-040|CP7|Nota ambil aksesori ke payroll deduction|QUALIFIED_LIFECYCLE_EVIDENCE_NOT_GLOBAL_ACCEPTANCE|7*300=2100; reversed3*500 tidak dihitung; net6000−2100=3900.|
|FUN-041|CP7|Payroll approve/partial/final/inverse|LIFECYCLE_SCOPED_AND_REPAIR_INTEGRITY_RETEST_PASS|Original valid repair Nota6000 all167zero, wrong/missing+1, REVERSED/reallocation zero, and F03P12 lifecycle pass. Other historical scope limits retained; no universal payment/period-close UI claim.|
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

# Kualifikasi hasil lanjutan — Q08 sampai Q14

Kandidat tetap `0b7049d9203bac52b47a4c89f3e0d75646067a8f`. Semua status mentah disimpan. Penjelasan alat/oracle berikut bukan perubahan produk, bukan penghapusan hasil merah, dan bukan izin mengulang kasus untuk mencari hijau. Ledger individual: `CONTINUATION_NONPASS.json`.

## Q08 — kosakata OBSERVED dan CONTROL_PASS

Run `38558323653`, AW/AX: lima baris dibungkus `INCOMPLETE` oleh runner strict yang hanya menerima kosakata terbatas. Field `status_outside_vocabulary` tetap menyimpan asalnya: `DISCOVERY:SEED` dan observasi backdate AX adalah `OBSERVED`; tiga kontrol AW adalah `CONTROL_PASS`. Expected/observed dan status asal tidak ditulis ulang. Observasi bukan bukti lulus invariant baru.

## Q09 — oracle AW sebelum keputusan BA tentang laporan tersimpan

AW `B04:LATE_INVOICE_JAKARTA`, `B04:LATE_INVOICE_KIRITIMATI`, `P07:PROCESSED_AFTER_CLOSE` berstatus `FAIL`. Pemeriksaan yang tidak cocok meminta `changed_since_filing=false` setelah recost. Nilai kas/stok/GL dan arsip asli cocok. Aturan BA W9/C0 D01 §3.4 justru mempertahankan penanda perubahan sesudah koreksi; recost tidak menghapus fakta bahwa laporan tersimpan berbeda dari keadaan terbaru.

Sumber pembanding: `scripts/cp6_aw_probe.py` (oracle lama), `scripts/cp6_ba_build.py` dan `scripts/cp6_ba_probe.py` (W9), `scripts/cp7_finance_cases.py` (kontrak current). Kedua kontrol W9 positif/negatif dalam BA pada run yang sama PASS. Ketiga FAIL lama tetap tersimpan dan tidak dieksekusi ulang dengan expected yang dilonggarkan.

## Q10 — adaptor auditor tidak memanggil factory RANGE

Job `115834143948`, run `38558702356`, menyelesaikan **nol kasus**. `cp6_bd_revision_modes` mengekspor `cases()`, sedangkan wrapper modes auditor awal hanya memanggil native untuk BF. Ini kekurangan adaptor auditor, bukan bukti dua RANGE lulus/gagal. Run `38560416364`, job `115839822085`, memanggil hanya dua kasus `RANGE:` yang belum berjalan: **2 PASS**, full restoration dan advisor gate true; artifact `11893358428`. Sumber kasus/fixture/oracle tidak diubah. Enam kasus REV lain yang sudah dijalankan tidak dimasukkan lagi.

## Q11 — fixture BC lama belum membawa identitas sumber D09

Run `38558323653`: `ALL:C03_CUSTODY_STATES`, `C12:OPNAME_BASELINE_INCOMPLETE_SOURCE`, dan `C12:SAME_GOODS_COUNTED_ONCE` berhenti dengan `BC_C12_SOURCE_REQUIRED`; `ALL:C03_IMPORT_REFUSALS` FAIL hanya pada pemeriksaan area inspeksi karena penolakan sumber terjadi lebih dahulu.

Keputusan owner D09 26 September mensyaratkan count sheet + baris atau source lot. Fixture BC itu mendahului keputusan tersebut. `scripts/cp6_bd_probe.py` kasus `D09:ACC_C12_SOURCE_IDENTITY` PASS: sumber hilang/kedua jenis/separuh pasangan ditolak, input sah menghasilkan 9 pending, sumber sama dengan key baru ditolak, FINALIZE tidak menambah qty, sumber sah berbeda menghasilkan total 17, tanpa kas/jurnal palsu. Browser BC current memakai sumber lengkap dan lima kasus browser PASS pada run `38558702356`. Empat non-PASS lama tetap utuh; sumber fixture tidak diam-diam diperbaiki untuk mengubah hasilnya.

## Q12 — fixture pocket menghapus USAGE yang sudah ada pada baseline

Run `38558702356`, job `115834144443`, kasus `BE_REV_HTTP:PUBLIC_SEWING_AND_PERIOD_ACCESS` berhenti **sebelum permintaan HTTP bisnis pertama** dengan `BD_HTTP_FIXTURE_SCHEMA_USAGE_CHANGED`. Tujuh HTTP dan dua puluh race lain pada suite itu PASS.

`cp6_pocket_period_trial.production` melakukan GRANT lalu REVOKE `USAGE` untuk authenticated tanpa mempertimbangkan ACL awal. Profil baseline G01 yang dipasang memang sudah mempunyai USAGE. Penjaga `_fixture_usage` benar mendeteksi perubahan tersebut.

Run kualifikasi `38561483350` menjalankan hanya fase HTTP yang belum tercapai. `sewing_http_qualification.py` mempertahankan ACL awal persis: hanya pasangan GRANT/REVOKE fixture yang sudah redundan dicegat, sebelum/sesudah `nspacl` harus identik, USAGE awal harus true, dan tepat dua statement itu harus teramati. Guard luar tetap aktif; seluruh SQL bisnis dan oracle original tetap. Manifest mengikat run asal. Hasil pada artifact `11893039442`: **1 PASS**, clone tersisa 0, ACL sebelum/sesudah identik, restoration/advisor true. Sembilan checks anon/warehouse/dependency/version/owner/replay/revoked/page-owner/page-restricted semuanya true. Hasil INCOMPLETE pertama tetap ada.

## Q13 — rollback BF mandiri tidak berlaku di bawah lapisan CP7

Run `38558702356`, job `115834144415`, `BF:UNUSED_ROLLBACK_EXACT` INCOMPLETE dengan `BF_ROLLBACK_SOURCE_DRIFT: erp.bf_supplier_credit_allocate_v1(jsonb,uuid)`. Kasus lama mencoba melepas BF saja saat lapisan CP7 masih terpasang. CP7 sengaja mengganti admission current-authority fungsi itu melalui `scripts/cp7-src/procurement/supplier-credit-authority.sql`; exact declared delta dibuktikan oleh `scripts/cp7_supplier_credit_guard.py`. `scripts/cp6_bf_recovery.py` benar menolak bila installed hash BF berbeda.

Tidak menghapus guard atau memaksa rollback ke predecessor di bawah CP7. Hasil pertama tetap INCOMPLETE. Bukti lifecycle yang berlaku adalah rehearsal P21 pada laporan terkunci: rollback CP7 sebelum pemakaian, penolakan sesudah dipakai, dan restore. Ini bukan klaim BF-alone rollback pada CP7 FULL lulus.

## Q14 — dua browser SALES_MANUAL_13 sudah dipensiunkan

Run/job BF di atas: `BF_BROWSER:SALES_MANUAL_13_DESKTOP` dan `_MOBILE` INCOMPLETE karena selector lama menuntut tiga `.biz-size-entry input` pada layar simulasi. Layar pengguna current adalah P11. Owner D13-9c mensyaratkan pengganti lengkap; putaran silang 2 kandidat **sama** telah membuktikan P11 desktop/HP, lusin+sisa PCS, baris lain tidak berubah, simpan, server reread, dan overflow.

Bukti yang dibawa: laporan Astra pada `57ac8aab164f7c3fc25cf8e2500a8346477da618` dan `fb24bd924fd7e790fba4cecbcd0c43651fab63e6`; penerimaan A6 COMPLETE sudah dicatat. Dua selector usang ini tidak membuka ulang A6 dan tidak dihitung PASS. Sumber/hasil pertama tetap disimpan; tidak membuat pengulangan browser demi mengganti warnanya.

## Temuan produk yang berbeda dari seluruh kualifikasi di atas

`CP17-ASTRA-FIN-07-FULL-DETECTOR-OBSERVATION` tetap COUNTEREXAMPLE. Ia memperluas observasi FIN01; bukan cacat adaptor/oracle. Perubahan kewajiban bertanggal −375,25 dan 135 baris detector yang tetap nol dijelaskan pada laporan lanjutan. Status BLOCKED laporan contoh yang sudah ada sebelum kasus tetap diungkapkan.

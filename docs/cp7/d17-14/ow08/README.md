# OW-08 — cek uang dan pembaca pemeriksa keuangan

Belum dikerjakan pada produk. Temuan berikut disimpan dari latihan P21 sesuai syarat7 penutupan OW-04; urutan owner tetap OW-05, OW-06, lalu OW-07/08.

## Pemeriksa piutang lama belum memasukkan kredit

Pada36a6b880, run39746622985/job119716564121, pemasangan/copot/pasang ulang lulus. Pembuat contoh E01 mengharuskan laporan global READY; setelah dua rantai kredit/pengembalian uang sah, pemeriksa lama menandai tiga kelompok salah hitung.

|Pemeriksa|Jumlah dalam contoh dua rantai|
|---|---:|
|V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH|2|
|V2620H_CUSTOMER_AR_STATUS_MISMATCH|3|
|V268_AR_GL_SUBLEDGER_MISMATCH|1|

Pemeriksa memakai net penjualan dikurangi pembayaran P. Kontrak kredit memakai pembayaran efektif E=P+U-I: U adalah kredit masuk dan I adalah kredit terbit. Pada sumber net800/P1000/I200, E800 dan AR0; pada target net500/P0/U100, E100 dan AR400. Uang dan AR literal tersebut telah diuji oleh kasus Native; tanda kesiapan laporan lama tetap BLOCKED dan belum boleh disebut READY.

Sumber yang harus diperbaiki saat OW-08: erp.run_v268_financial_report_checks() SHA25682e0f45d264507679d8a6bbf0915dea8752f9868cec3602ad3e8756bb15cb167 dan erp._v268_financial_report_checks_pre_scope() SHA256e151310a11ca78fd4289a789131968fc9c1d1cdb5279cd780509315e66ede6ad. Helper faktual erp._cp7_current_credit_adjustment(uuid) sudah membuktikan U-I, jurnal, sumber dan asal materialisasi; jangan memakai jumlah yang tidak terbukti atau melewati penjaga.

Saat diperbaiki: pertahankan seluruh pemeriksa lain, nama/kadar temuan, tanggal dan filing lama; verifikasi CURRENT yang terkoreksi, zero-participation legacy, pemakaian/pembatalan kredit, dua arah koreksi, serta penolakan jurnal/fakta tak beralas. Ulangi Native dan transport yang memang sumbernya berubah. Tidak mengarang kebijakan dan tidak mengubah laporan lama yang sudah diarsip.

Lihat [kegagalan P21 yang dipertahankan](../ow04/p21-36a6b880-readiness-boundary.json); tidak ada log mentah baru di repo.

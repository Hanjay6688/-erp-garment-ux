# OW-08 — cek uang dan pembaca pemeriksa keuangan

## Status current, 24 Oktober 2026

Tahap laporan kredit sudah terpasang pada current A/B. Native62 membuktikan
kredit sah READY dan selisih nyata tetap tertangkap. P21 current seluruh uang
run40064922630/head d18f5d26 membuktikan empat pemeriksa AR/kredit0, dua
readback finansial sama sesudah restore, serta sumber kasbon/FG dan cuci
UNKNOWN yang tetap menahan sampai harga sah diisi sekali. Lihat
[Native62](../ow15/owner62-28abdeef-pass.json) dan
[P21 uang+status](../ow15/full-money-d18f5d26-status-pass.json).

Kasbon, koreksi FG/QC dan cuci tanpa tarif sudah mempunyai bukti mesin dan
pemulihan. Piutang/kelebihan bayar vendor laundry tetap batas kebijakan
[OW08b](OW08B.md). Tidak mengklaim semua perjalanan browser OW08 atau seluruh
kebutuhan telah ditutup. Audit independen dan production_go tetap belum.

## Riwayat awal sebelum komposisi current

Bagian berikut mempertahankan pengamatan dan checkpoint23Oktober. Kata
"belum" dan BLOCKED di riwayat ini mengacu kandidat yang disebut, bukan
status current di atas.

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

## OW-08a — pemeriksa laporan memakai kredit pelanggan (penulis A, 23 Okt 2026)

Dikerjakan sebagai tahap `scripts/cp7_report_credit/` di atas produk OW-05 yang sudah lulus. Dua pembaca di atas diganti
dengan perubahan terhitung (`native_delta.py`): bayar efektif tiap invoice = pembayaran + kredit masuk − kredit terbit
(`erp._cp7_current_credit_adjustment`, dibaca sekali per pemeriksaan). Invoice tanpa kredit hasilnya sama persis. Bila
kredit sebuah invoice tidak bisa dibuktikan, laporan tidak error tetapi muncul temuan kritis baru
`CP7_CUSTOMER_CREDIT_REPORT_UNPROVEN`. Pemeriksa lain, nama dan kadar temuan tidak berubah.

| Bukti | Hasil |
|---|---|
| Run CI | 39817748051 percobaan 2, job 119966636081, kepala `d38f6ee6` (produk OW-05 `5e4b4c1c`); percobaan 1 gagal sebelum uji karena batas unduh image (infrastruktur) |
| Native6 | PASS 6/6: tanpa kredit sama dengan pembaca lama; kredit terbit dan dipakai READY; uang kembali READY; pakai lalu batal READY; selisih asli (status PAID palsu, GL +0,01) tetap tertangkap; kredit tak terbukti memblokir tanpa error |
| Pulih | Copot sebelum dipakai mengembalikan katalog persis; bukti pemulihan CP6 dan gerbang advisor lulus |
| Laporan asli | `CP7_OW08A_REPORT_CREDIT_NATIVE6.json` 1.807.336 byte, sha256 `1f13604f358be7ee1375c49a335b174d7de5ddc196cddb28fbf785a16dabe2d8`; artifact 12444192203 |

Belum: dirangkai ke pemasang bawaan (P21 akan berubah dari BLOCKED 2/3/1 menjadi 0/0/0, pengetatan) saat penggabungan;
OW-08b (kasbon dari buku besar, piutang vendor laundry, cuci gagal tanpa tarif, koreksi FG di QC) belum dikerjakan.

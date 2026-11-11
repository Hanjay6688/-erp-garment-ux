# Prasyarat tanggal dan cakupan uji QC dengan Business Report INCLUDED

Pemeriksaan sumber Writer A pada kandidat `a1652a808f5f9e7a5bcc3fe0ea0feb081075adc3`. Handoff B `52b6cf93dd85bc76a713e29beb5ae6d91247f9c7` mencatat transaksi QC fisik 8 WIP menjadi 5 WIP dan 3 FG serta dua publikasi `DEFERRED`. Valuasi resmi dan publikasi `INCLUDED` masih menunggu salinan uji gabungan. Pemeriksaan ini membaca kode tanpa menjalankan transaksi.

## Tanggal yang harus dicakup oleh laporan HPP

Fixture B menetapkan `from_date` dan `through_date` ke hari WIB sebelumnya. QC memakai `physical_at` saat pengujian. Laporan stok sengaja membaca mutasi sampai waktu langkah `ACTUALS` sehingga stok 0 → 3 tetap sah pada fixture itu. Jalur keuangan mengambil `from` dan `to` dari periode publikasi dan `as_of` dari waktu baca `ACTUALS` dalam WIB. Menyalin periode hari sebelumnya bisa melewatkan jurnal HPP yang salah pada tanggal ekonomi QC.

Untuk pasangan publikasi `INCLUDED`, tetapkan `from` dan `to` yang mencakup tanggal transaksi QC. Gunakan tanggal WIB yang sama pada pasangan sebelum dan sesudah. Simpan `ACTUALS.read_at`, `finance.dates`, tanggal ekonomi transaksi dan jurnal asli. Cocokkan kedua publikasi dengan laporan owner yang memakai `from`, `to`, dan `as_of` aktual yang sama. Validasi tanggal ekonomi dari hasil posting.

## Saldo dan izin yang diperiksa

- Mulai dari satu PO dengan 8 PCS dan biaya resmi Rp288,00 yang sudah terposting, dengan akun WIP dan FG terpetakan. Ambil baseline sebelum QC. Setelah 3 PCS terposting lewat `erp.post_final_sku_allocation_v1`, cocokkan 5 PCS dan Rp180,00 WIP, 3 PCS dan Rp108,00 FG, serta HPP penjualan Rp0,00. Ikat mutasi, lot, biaya dan jurnal ke PO dan identitas permintaan.
- Filter root diterapkan pada pembacaan stok. Angka keuangan diambil dari `cp7_finance.workspace`. Cocokkan nilai per PO di buku dan perubahan saldo akun pada laporan owner untuk periode yang sama. Selisih yang diharapkan WIP −Rp108,00, FG +Rp108,00 dan HPP penjualan Rp0,00. Bila salinan memuat saldo lain, bandingkan perubahan dari baseline.
- Jalankan tahap publikasi dan baca arsip dengan aktor owner yang memiliki `finance.reports.view` aktual. `close_preflight` hanya disajikan bila aktor juga memiliki `finance.period_close.manage`. Simpan hash sumber, ringkasan, bagian dan arsip sebelum QC. Baca ulang arsip setelah publikasi kedua dan cocokkan byte serta hash.
- Enam hook keuangan dan provider finance pada fixture B hanya merekam panggilan atau menolak akses. Gunakan fungsi HPP dan ledger terpasang untuk bukti baru, serta simpan pemulihan salinan uji.

Status `BLOCKED` untuk valuasi resmi dan publikasi `INCLUDED`. Native25 SKU memiliki lingkup kasus lain. Kredit kasus aktual dari pemeriksaan ini 0. Formal CP7 5/16.

[Sumber periode fixture B](https://github.com/Hanjay6688/-erp-garment-ux/blob/52b6cf93dd85bc76a713e29beb5ae6d91247f9c7/docs/cp7/review/sku-snapshot-report-focused-20261112/snapshot_report_probe.py#L207) · [Pembacaan ACTUALS](https://github.com/Hanjay6688/-erp-garment-ux/blob/a1652a808f5f9e7a5bcc3fe0ea0feb081075adc3/scripts/cp7-src/planning/report-staged.sql#L241) · [Tanggal dan sumber finance](https://github.com/Hanjay6688/-erp-garment-ux/blob/a1652a808f5f9e7a5bcc3fe0ea0feb081075adc3/scripts/cp7-src/planning/analysis-finance.sql#L24) · [Laporan owner dan izin tutup buku](https://github.com/Hanjay6688/-erp-garment-ux/blob/a1652a808f5f9e7a5bcc3fe0ea0feb081075adc3/scripts/cp7-src/finance/read.sql#L35)

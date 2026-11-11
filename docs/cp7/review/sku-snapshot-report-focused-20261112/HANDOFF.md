# CP7 | Uji terarah B untuk moving average, snapshot WIP, dan Business Report

12 November 2026 WIB. Kandidat acuan A `d08032a28b9f00d0ee70a6f98c6b7d0f5b770c4a`, tree `a80a212694fc6b67d23e2dcdd9e648b4eea78541`. Run SKU A terpisah, [43065549640, job 130679406466](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/43065549640/job/130679406466). Basis cabang bukti B `ad6085433f4c394236a3284670fd704a4524191c`.

| Skenario | Versi yang diuji | Bukti lama yang dipakai ulang | Harapan vs aktual | Status |
| --- | --- | --- | --- | --- |
| Dua perubahan biaya susulan, diselingi dua retur parsial, lalu balikkan delta biaya kedua | PostgreSQL 17.6, SQL moving average dan jurnal dari komposisi `d08032a` dengan kedua postimage koreksi A terverifikasi. Provider biaya dan beberapa dependensi penulis berupa fixture bertipe. | Dua kasus koreksi sen 11 Nov dari A dan B. Donor lama punya retur bertahap dengan biaya genap. Rencana run A punya satu invoice susulan dan alur recost pembukaan. | Urutan PCS / nilai FG / HPP penjualan dalam rupiah cocok persis dari awal `2 / 72,00 / 0`, jual `0 / 0 / 72,00`, biaya pertama `0 / 0 / 73,01`, retur pertama `1 / 36,51 / 36,50`, biaya kedua `1 / 37,02 / 37,01`, retur kedua `2 / 74,03 / 0`, hingga inverse `2 / 73,01 / 0`. Jurnal per akun cocok pada tujuh langkah. Ulang sumber `4,03` identik dan riwayat jual/retur tetap utuh. [Hasil](MOVING_AVERAGE_RESULT.json) | `PASS` |
| Satu posting QC parsial dan dua snapshot WIP/FG | SQL pembaca WIP `d08032a` dan penulis QC fisik dari katalog Native27 yang dipin. Fixture PostgreSQL 17.6. | `opening_lifecycle` lama membuktikan pemindahan dari saldo awal dan snapshot lama. Uji ini memakai grup potong dan posting final SKU. | WIP/FG `8/0 → 5/3 PCS` cocok dengan buku progres grup dan satu mutasi `QC_GOOD`. SKU, root, ukuran, lot, PO, lokasi gudang FG, grade, PCS dan cache cocok. Jumlah unik tetap 8 PCS. Snapshot lama tetap `8/0` dengan jam ambil asli dan `ARCHIVED_STALE`. [Hasil](SNAPSHOT_REPORT_RESULT.json) | `PASS` |
| Business Report v2 sesudah QC, buka arsip, lalu identitas sumber salah | RPC publik dari `d08032a`, role PostgreSQL `authenticated` dengan identitas fixture. Satu hasil staged `DONE` sebagai input, pilihan `DEFERRED`. | `P19R_ACTUAL_STOCK_AT_REPORT_TIME`, `P19R_REVISION_SERIES`, `P19R_FIELDS_AND_IDENTITY` dan dua kasus browser di job `113577594659`. Bukti visual lama berlaku untuk terbit, label waktu, dan baca bagian. | Periode dan filter tetap 11 Nov WIB / `AS_SOLD` / satu root. Buku stok dan laporan fisik/tersedia `0/0 → 3/3 PCS` pada jam baca masing-masing, 11 PCS root kontrol di luar filter. Angka snapshot tetap 0. Revisi 1 dibuka dengan baris, bagian, dan hash asli. Revisi 2 `CHANGES_RECORDED`. Hash sumber salah ditolak `CP7_REPORT_V2_IDENTITY_CHANGED`, jumlah job tetap. [Hasil](SNAPSHOT_REPORT_RESULT.json) | `PASS` |
| Nilai resmi WIP/FG dan angka keuangan Business Report `INCLUDED` pada QC yang sama | Memerlukan DB uji dengan lapisan valuasi Native, buku besar dan owner report dari kandidat gabungan yang dipilih A. | `P19R_FINANCE_FROM_OWNER_REPORT` lama membuktikan jalur owner report untuk fixture lain. | Dengan 8 PCS homogen, biaya resmi Rp288,00 dan Rp36,00/PCS terverifikasi, harapan WIP `Rp288,00 → Rp180,00`, FG `Rp0,00 → Rp108,00`, HPP penjualan tetap Rp0,00 pada periode tanpa penjualan. Aktual resmi belum tersedia. Hook finance fixture merekam panggilan dan laporan `DEFERRED` menyimpan `finance=null`. | `BLOCKED` |

## Jurnal moving average

Angka di bawah adalah net per akun dalam rupiah. Hasil JSON menyimpan tiap baris debit/kredit, tanggal ekonomi, referensi transaksi, dan rekonsiliasi stok dengan buku HPP.

- Biaya awal Rp2,00 menaikkan nilai pool menjadi Rp72,00. Debit `FG_INVENTORY` dan kredit `MATERIAL_COST_OFFSET` Rp2,00. Penjualan 2 PCS mendebit `AR_CUSTOMER` dan mengkredit `SALES_REVENUE` Rp370.000,00. Debit `COGS` dan kredit `FG_INVENTORY` Rp72,00.
- Sumber biaya Rp2,00 → Rp3,01. Debit `COGS`, kredit `MATERIAL_COST_OFFSET` Rp1,01. Retur 1 mendebit `FG_INVENTORY` dan mengkredit `COGS` Rp36,51.
- Sumber biaya Rp3,01 → Rp4,03. Debit `FG_INVENTORY` Rp0,51 dan `COGS` Rp0,51. Kredit `MATERIAL_COST_OFFSET` Rp1,02. Retur 2 mendebit `FG_INVENTORY` dan mengkredit `COGS` Rp37,01. Masing-masing retur mendebit `SALES_REVENUE` dan mengkredit `AR_CUSTOMER` Rp185.000,00.
- Inverse delta sumber Rp4,03 → Rp3,01. Debit `MATERIAL_COST_OFFSET` dan kredit `FG_INVENTORY` Rp1,02. `OTHER_INCOME` tetap nol. Kedua nilai retur historis tetap Rp36,51 dan Rp37,01.

Inverse di atas memakai rekonsiliasi biaya sumber dalam fixture. Invoice supplier, inverse dokumen dan replay UUID ERP gabungan mengikuti uji A. Sumber koreksi dan bukti lama tercatat dalam [preflight](ROUNDING_SOURCE_PREFLIGHT.json), [review A](https://github.com/Hanjay6688/-erp-garment-ux/blob/c360ef3bc4f02c147bb3905047166711df23f0d9/docs/cp7/review/shutdown-20261111/sku-non-po-rounding/SKU_NON_PO_ROUNDING_REVIEW.md), dan [handoff B 11 Nov](https://github.com/Hanjay6688/-erp-garment-ux/blob/ad6085433f4c394236a3284670fd704a4524191c/docs/cp7/review/sku-moving-average-regression-20261111/HANDOFF.md).

## Cakupan snapshot dan laporan

- Lokasi fisik dicek pada mutasi `QC_GOOD`. WIP ditelusuri ke pool grup potong/ukuran. FG pada snapshot WIP adalah status disposisi 3 PCS yang sama dengan 3 PCS di buku stok. Persamaan memakai 5 PCS WIP ditambah 3 PCS dari buku stok.
- Arsip pertama disegel sebelum posting QC. Kedua revisi menjalankan empat RPC tahap terpisah. Laporan memakai target dan angka analisis yang sama, lalu membaca stok aktual pada tanggal laporan 12 Nov WIB. Buku pembanding memakai root yang sama serta batas waktu fisik dan waktu catat yang sama. Arsip lama berisi 0 PCS walau revisi 2 berisi 3 PCS. Status `is_latest` arsip lama menjadi `false`.
- Prasyarat penilaian rupiah adalah salinan uji yang terpasang `erp.rebuild_po_hpp`, `erp.sync_po_hpp_to_gl`, pemetaan akun WIP/FG, dan sumber biaya terposting yang membuat 8 PCS memiliki basis resmi Rp288,00 sebelum QC. Pakai owner dengan `finance.reports.view` untuk dua publikasi `INCLUDED`. Cocokkan nilai lot dan perpindahan WIP/FG ke saldo serta jurnal resmi pada cutoff yang sama. Cocokkan HPP periode dan posisi WIP/FG dengan owner report untuk `from`, `to`, dan `as_of` yang identik. Simpan publikasi awal sebelum QC, lalu buka lagi dan bandingkan hash, ringkasan, dan bagian.
- Job lama `p19-report-v2-20` sukses pada `05b2368f`, termasuk desktop `INCLUDED` dan HP `DEFERRED`. Panel kini punya perubahan saat membuka ulang, penanganan akses, pembanding dan progres keuangan. Tujuh uji DOM/unit terarah pada `d08032a` lulus untuk buka arsip, pengosongan hasil lama, dan validasi hash. Bukti browser D17-18 dipakai sesuai cakupan READY/BLOCKED dan pencabutan akses. Tidak ada sesi browser Auth baru pada fixture QC ini. [Hasil DOM/unit](UI_TARGETED_RESULT.log) · [Cuplikan job lama](P19_PRIOR_CASES.log) · [Job asli](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37855200317/job/113577594659) · [Bukti D17-18](https://github.com/Hanjay6688/-erp-garment-ux/blob/d08032a28b9f00d0ee70a6f98c6b7d0f5b770c4a/docs/cp7/d17-18/b-qualified3194-browser-20261028/ACTUAL_RESULT.json)

## Reproduksi dan pemulihan

Pakai direktori B baru. Sediakan katalog Native27 asli dari [artefak 13031164777](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/41167734749/artifacts/13031164777), PostgreSQL 17.6, `pg@8.16.3` di `lab/node_modules`, dan `psycopg[binary]==3.2.10` di `lab/python`. Nama file katalog dan pin ada di [receipt](SOURCE_AND_RUN_RECEIPT.json).

Untuk moving average, ikuti struktur donor pada handoff B 11 Nov. Donor otomatis `9b1b0fcc` juga memerlukan `scripts/cp7_ow04_restore_bundle.py` dari commit yang sama. Pakai preparer lama dan `run-local.sh` asli B di root lab. `current` adalah arsip sumber `d08032a`, `prior` folder handoff B 11 Nov, `rounding` folder review A dari `c360ef3`, dan `here` folder paket ini. Buat `lab/handoff` sebelum menyiapkan adapter.

```bash
python -B "$prior/prepare_probe.py" "$lab/qualified-sku-money" "$lab/qualified-sku-automatic" "$lab/native27" "$lab/focused-r6"
python -B "$rounding/prepare_rounding_probe.py" "$lab" "$current/scripts/current-sku-automatic-composite-preparation" "$lab" "$lab/ma-two-stage"
python -B "$here/prepare_staged_moving.py" "$lab" "$prior/focused_probe.mjs" "$here/moving_staged_case.mjs.inc"
bash "$lab/run-local.sh" "$lab/ma-two-stage"
bash "$here/run_snapshot_lab.sh" "$lab" "$current" snapshot-qc-repro
```

Driver snapshot membuat fixture 8 PCS pada satu grup potong dan 11 PCS root kontrol. Urutannya adalah capture dan terbit revisi 1, satu `post_final_sku_allocation_v1` dengan `PARTIAL_SELECTION` 3 PCS, capture kedua, revisi 2, baca arsip, lalu uji penolakan identitas. Hasil staged awal dan identitas aktor disiapkan sebagai fixture. Lapisan biaya QC merekam enam panggilan dependensi tanpa valuasi.

Moving average memulihkan fingerprint fixture 75 tabel dan batas transaksi luar. Snapshot/report menghapus DB disposable serta role fixture dan mencocokkan daftar awal/akhir. Kedua server dihentikan. Percobaan awal yang gagal saat menyusun fixture tersimpan di [receipt](SOURCE_AND_RUN_RECEIPT.json), [galat donor](MA_FIRST_SETUP_FAILURE.txt), dan [hasil snapshot pertama](SNAPSHOT_REPORT_FIRST_SETUP_FAILURE.json). Perbaikan terbatas pada ekstraksi donor dan pengikatan izin fixture.

Paket cabang B berisi driver uji dan bukti. A tetap memegang kandidat gabungan, run SKU/Global dan keputusan integrasi. Formal CP7 5/16, `production_go=false`, `independent_acceptance=false`.

# Regresi moving average biaya susulan dan retur

11 November 2026 WIB. Pengujian B menggunakan PostgreSQL 17.6 di loopback
dan database disposable. Kandidat SKU yang dipatok adalah
`32590613a08e176536d9a19b3843f6a72f4479b4`, tree
`262811e77e1a305a9d54baa9374e27df06793d10`. Sumber uang berasal dari
`f1674ae84739f577571d68415beabfca3f3b832b` dan lapisan otomatis dari
`9b1b0fcc9fbf477634619f07d4628d5be3a1b634`. Pemeriksa mencocokkan
44 berkas uang, 20 berkas lapisan otomatis, DDL uang, 30 definisi uang,
sembilan penggantian otomatis, serta pembaca jurnal non-PO dan resolver akun
asli. [Kandidat SKU](https://github.com/Hanjay6688/-erp-garment-ux/commit/32590613a08e176536d9a19b3843f6a72f4479b4)

Arsip Native27 dan Moving6 diverifikasi terhadap ukuran, SHA-256 dan seluruh
CRC (170 dan 125 entri). Folder `scripts/cp7_sku_moving_average` pada donor
uang cocok dengan Moving6 yang lulus, termasuk skenario retur dan recost
HPP lama. Bukti historis tersebut dipakai sesuai cakupan asalnya. Skenario
Native uang untuk invoice susulan dan retur sudah ada pada `sold_return`,
tetapi run kandidat berhenti sebelum skenario bisnis. [Moving6](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/41660989394/job/126003816789) [Skenario Native](https://github.com/Hanjay6688/-erp-garment-ux/blob/f1674ae84739f577571d68415beabfca3f3b832b/scripts/current-sku-cost-money-qualification/native_cases.py#L145-L165) [Diagnosis shutdown](https://github.com/Hanjay6688/-erp-garment-ux/blob/fd00b866743f00229536ef98ca23b535bcdb66e1/docs/cp7/review/shutdown-20261111/sku-terminal-42996079217/SKU_42996079217_SHUTDOWN_REVIEW.md)

## Angka dan jurnal yang diukur

Fixture menggunakan dua pcs Grade A di gudang yang sama. Konversi membawa
HPP 20 dari stok A `2×10 + 2×30` ke B yang punya `1×50`. HPP dua pcs
B menjadi 70. Biaya aksesori awal 2 menaikkan total ke 72. Kasus berikut
memakai lot fisik asal dan campuran biaya ekonomi dari alokasi penjualan.
Kolom angka mengikuti urutan stok pcs, total HPP, persediaan FG, HPP
penjualan, lalu saldo akun lain.

| Kasus dan langkah | Harapan | Aktual kandidat | Status lokal |
| --- | --- | --- | --- |
| Jual 1 dari 2 pcs, lalu biaya 2,00 → 3,02 | 1 / 73,02 / 36,51 / 36,51 / 0 | 1 / 73,02 / 36,51 / 36,51 / 0 | PASS |
| Retur pcs yang terjual dari kasus itu | 2 / 73,02 / 73,02 / 0 / 0 | 2 / 73,02 / 73,02 / 0 / 0 | PASS, langkah kasus yang sama |
| Jual 2 dari 2 pcs, biaya 2,00 → 3,01, lalu retur 1 pcs | 1 / 73,01 / 36,51 / 36,50 / 0 | 1 / 73,01 / 36,51 / 36,51 / −0,01 | FAIL |

- Kasus pertama membukukan bersih debit FG 0,51, debit COGS 0,51 dan kredit
  lawan biaya 1,02. Retur mendebit FG 36,51 dan mengkredit COGS 36,51.
  Kuantitas buku stok dan cache cocok. Rekonsiliasi ulang dengan harga
  sumber yang sama tidak mengubah satu pun baris dari 75 tabel fixture.
- Kasus kedua merekam jurnal retur debit FG 36,51, kredit COGS 36,50,
  dan kredit `OTHER_INCOME` 0,01. Baris pendapatan dan piutang masing-masing
  185.000 berlawanan arah sebagaimana retur fixture. Total tetap seimbang,
  tetapi klasifikasi 0,01 menyimpang dari oracle Native. Sebelum retur,
  biaya 1,01 seluruhnya menambah COGS dan rekonsiliasi ulang meninggalkan
  sensus baris identik. [Kegagalan pertama](FIRST_BUSINESS_RESULT.json)
- Kedua kasus dibatalkan dengan savepoint. Sensus 75 tabel kembali ke
  hash awal, transaksi luar menghapus skema dan role fixture, dan server
  disposable berhenti. [Hasil kandidat dan pemulihan](CANDIDATE_RESULT.json)

## Sumber selisih dan usulan untuk A

Setelah retur, kontribusi biaya tambahan terjual 3,01 dikurangi kontribusi
biaya yang kembali 1,505. Nilai mentah FG dan sisa COGS masing-masing
36,505. `erp.compute_non_po_product_hpp_targets_v2620f` membulatkan keduanya
secara terpisah ke 36,51. Selisih `73,01 − 36,51 − 36,51` kemudian menjadi
saldo akun lain −0,01. `cp7_credit.initial_hpp_targets_v1` memakai pembulatan
terpisah yang sama, sehingga pemeriksaan kesetaraan buku dan proyeksi tidak
menangkap salah klasifikasi ini. [Derivasi target](https://github.com/Hanjay6688/-erp-garment-ux/blob/f1674ae84739f577571d68415beabfca3f3b832b/scripts/cp7_sku_cost_components/financial_delta.py#L42-L55) [Derivasi kredit](https://github.com/Hanjay6688/-erp-garment-ux/blob/f1674ae84739f577571d68415beabfca3f3b832b/scripts/cp7_sku_cost_components/money_delta.py#L125-L154)

Usulan yang sudah dicoba pada fixture adalah pembulatan kumulatif untuk
non-PO. Pertahankan `FG = round(FG_mentah, 2)`, lalu hitung
`COGS = round(FG_mentah + COGS_mentah, 2) − FG`. Hitung saldo akun lain dari
selisih HPP terhadap jumlah FG dan COGS kumulatif. Terapkan aturan yang sama
ke proyeksi kredit dengan sumber perhitungannya sendiri dan pertahankan
cabang PO yang ada. Kedua kasus lulus pada model ini. Jurnal retur kasus
kedua menjadi debit FG 36,51 dan kredit COGS 36,51 tanpa kredit akun lain.
Saat biaya dikembalikan dari 3,01 ke 2,00 dengan retur masih aktif, hasil
menjadi 1 pcs / HPP 72,00 / FG 36,00 / COGS 36,00 / akun lain 0. Snapshot
penjualan dan retur tetap identik. [Usulan uji](cumulative_cent_proposal.py) [Hasil usulan](PROPOSAL_RESULT.json)

A perlu membawa perubahan ke derivasi sumber dan profil katalog yang
berlaku. Pada database uji aktual, gunakan kembali `sold_return` untuk
biaya 3,01 dan dua inverse. Untuk kasus pertama, pakai `canonical`,
`material`, `usage` dan `invoice` dari modul yang sama, reservasi satu pcs
melalui `f.reserve`, lalu posting penjualan, invoice `3.02` dan retur
satu pcs. Cocokkan jurnal sumber dan jurnal retur per akun, baca jumlah
dari buku stok, pakai replay invoice UUID yang sama dari helper `invoice`,
dan lakukan pemulihan yang diwajibkan runner. Cakup biaya non-PO lain yang
sah dalam review rumus sebelum memasang perubahan.

**Native pada ERP gabungan masih BLOCKED.** PostgreSQL menjalankan fungsi
posting penjualan, posting retur, rekonsiliasi biaya, target dan pembaca buku
yang dipatok. Data awal konversi, sumber nilai material, penyimpanan jurnal
dan otorisasi memakai provider fixture. Jalur simpan invoice pemasok,
otorisasi aktual, dan replay UUID dari endpoint memerlukan database uji
dengan state gabungan Afui/Mandor serta komposisi moving average, money dan
automatic yang terpasang dan terverifikasi. Arsip shutdown terbaru tidak
memuat state itu. Bukti B tidak memberi kelulusan Native25, restore paket
kandidat, atau penerimaan CP7. Formal CP7 5/16.

## Reproduksi lokal

1. Di direktori disposable, ambil objek Git `32590613`, `f1674ae8`, dan
   `9b1b0fcc` dari repo ini. Checkout donor uang `f1674ae8` ke
   `money-checkout` dengan `scripts/cp7_sku_cost_components` dan
   `scripts/cp7_sku_moving_average` termaterialisasi. Ekstrak empat folder
   dari `9b1b0fcc` ke `auto-source/scripts` menggunakan `git archive`
   untuk `cp7_sku_cost_components`, `cp7_sku_moving_average`,
   `cp7_sku_pending_accounting`, dan `cp7_sku_automatic_pending`.
2. Verifikasi dan ekstrak `CP7_SKU_MANAGED_RECOVERY_NATIVE27.json` dari
   [arsip 13031164777](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/41167734749/artifacts/13031164777)
   ke `native27`. Pin ZIP dan JSON ada di [receipt](RUN_RECEIPT.json).
3. Di direktori lab, instal `pg@8.16.3` dengan `--ignore-scripts`.
   Gunakan PostgreSQL 17.6. Pembungkus yang dipakai mengharapkan binari di
   `pg17/package/native/bin` dan dijalankan dari root lab. Pada percobaan
   ini binari berasal dari paket `@embedded-postgres/linux-x64@17.6.0-beta.15`
   dan tautan pustaka paket dipulihkan dengan `node scripts/hydrate-symlinks.js`
   dari direktori `pg17/package`. Salin tiga helper Python/Node ke `handoff/`
   dan `run-local.sh` ke root lab.
4. Jalankan dua percobaan terpisah seperti di bawah. Percobaan kandidat
   keluar dengan kode 1 karena kasus sen ganjil gagal. Percobaan usulan
   menggunakan PGDATA baru dan keluar 0.

```bash
python -B handoff/prepare_probe.py money-checkout auto-source native27 candidate
bash run-local.sh candidate
python -B handoff/prepare_probe.py money-checkout auto-source native27 proposal
python -B handoff/cumulative_cent_proposal.py proposal/COST_MODEL_INPUT.json proposal/PROPOSED_INPUT.json
bash run-local.sh proposal PROPOSED_INPUT.json
```

Pemeriksaan setup pertama menemukan impor `financial_delta` belum terbuka.
Percobaan setup berikutnya menemukan dua tabel kosong yang memang ditambah
lapisan otomatis, fungsi `erp.account_id`, dan tabel bertipe `erp.bs_cases`
yang dibutuhkan pembaca. Perbaikannya hanya pada pengikatan fixture. Receipt
menyimpan galat setup dan galat bisnis secara terpisah.

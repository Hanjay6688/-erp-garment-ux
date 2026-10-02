# Benerin penerimaan bahan & Benerin nama bahan (CP7, cabang `claude/new-session-deapao`)

Status: **kandidat, belum diterima auditor independen** (run CI terakhir 37026064573: 28/28 PASS). `production_go=false`, CP6 tetap HOLD, `audit_complete=false`. Hasil `LOCAL_PG16_DEV` di bawah hanya catatan kerja, **bukan bukti**. Bukti hanya dari run workflow `cp7-receipt-correction` (lihat bagian "Bukti CI").

## Untuk apa

Owner perlu membetulkan penerimaan bahan yang **sudah diposting dan sudah dipakai** (dipotong, dijual, dibayar), bukan hanya ditolak. Pembetulan harus berlaku sejak tanggal kejadian aslinya, bukan dicatat sebagai selisih hari ini, dan seluruh transaksi lain harus tetap konsisten.

| Kasus owner | Yang dilakukan sistem | Kasus uji |
|---|---|---|
| Jumlah roll/qty salah ketik (turun atau naik), sesudah dipotong | Penerimaan asal dibalik pada waktu fisiknya sendiri. Penerimaan pengganti yang persis diposting pada waktu yang sama. Roll fisik yang sama dipakai (id roll tetap), jadi potongan, transfer, dan kartu tetap menunjuk roll yang sama. Recost bahan, HPP PO, dan GL dihitung dari tanggal barang datang. | `RF_QTY_DOWN_AFTER_CUTTING`, `RF_QTY_UP_AFTER_CUTTING`, `RF_YEAR_HISTORY_364` |
| Jumlah roll salah (3 tertulis, datang 2) | Roll yang belum terpakai ditutup (lineage `REMOVED`). Roll terpakai tidak bisa dihapus. | `RF_ROLL_COUNT_TYPO_UNUSED_ROLL`, `RF_REMOVED_ROLL_USED_REFUSED` |
| Jumlah dibetulkan di bawah yang sudah terpakai | Ditolak dengan angka pemakaian | `RF_ROLL_BELOW_USE_REFUSED` |
| Harga penerimaan salah (sesudah dipotong, dijual, diretur) | Selisih masuk bahan sisa, barang jadi, dan HPP penjualan sesuai posisi barangnya | `RF_PRICE_AFTER_SALE_AND_RETURN` |
| Salah pilih bahan A, padahal yang datang bahan B (sudah dipotong) | Roll pindah ke bahan B. Pemakaian potong yang sama (baris, waktu, jumlah) sekarang tercatat di bahan B, dengan atribut lama disimpan di `movement_lineage`. Riwayat bahan A menjadi 0. | `RF_WRONG_MATERIAL_AFTER_CUTTING`, `RF_WRONG_MATERIAL_AND_PRICE` |
| Harga final di **invoice supplier** salah (setahun lalu pun) | Invoice lama dibalik dengan writer Native, lalu efeknya dipindah ke tanggal ekonominya sendiri. Invoice yang benar diposting ulang dengan tanggal invoice yang sama. Tidak ada selisih yang dicatat hari ini, kecuali barang yang memang terjual hari ini. | `RF_INVOICE_PRICE_AFTER_SALE`, `RF_INVOICED_QTY_DOWN_WITH_PAYMENT` |
| Pembayaran supplier sudah ada | Dibalik lalu diputar ulang ke dokumen yang benar dengan tanggal dan jumlah aslinya. Tidak ada uang yang berubah. Kalau yang dibayar lebih besar dari total yang benar, permintaan ditolak (alur refund supplier tidak dikarang). | `RF_PAYMENT_REPLAY`, `RF_PAID_EXCEEDS_CORRECTED_REFUSED` |
| Nama bahan salah ketik | Hanya `material_name` yang berubah pada bahan yang sama. SKU, jenis, satuan, kategori, stok, biaya, roll, dan mutasi tetap. Nama yang sudah dipakai bahan lain ditolak, karena itu masalah identitas, bukan typo. | `RF_MATERIAL_NAME_TYPO`, `RF_MATERIAL_NAME_REFUSALS` |

Kasus lain: `RF_REPEATED_REVISIONS` (R1, R2: yang terakhir berlaku, satu baris kartu), `RF_REPLAY_SAME_REQUEST` (satu UUID, satu efek), `RF_REVIEW_CHANGED_REFUSED` (data berubah sesudah ditinjau), `RF_ACCESS_CURRENT_AUTHORITY`, `RF_LATE_FAILURE_ATOMIC` (gagal di langkah terakhir: tidak ada efek tersisa), `RF_ACCESSORY_LINE_QTY` (aksesori dalam satuan dasar; GRNI ikut), `RF_INVOICE_SHARED_OR_INCOMPLETE_REFUSED`, tiga race (`RF_RACE_*`), satu HTTP Auth nyata, dan dua alur browser (desktop serta HP dengan balasan hilang lalu reconcile; di desktop juga ada pembetulan nama).

Oracle integritas di setiap kasus utama: semua `erp.run_v*_checks()` sebelum dan sesudah **tidak berubah**, `V2620U_JOURNAL_REVERSAL_BUSINESS_DATE = 0`, dan perubahan buku besar per akun (dan per tanggal ekonomi pada kasus invoice) sama persis dengan angka yang ditulis sebelum kasus dijalankan.

## Cara kerjanya (ringkas)

- Satu perintah atomik `erp_cp7_correct_receipt_v1(payload, request_id, expected_version)` dengan token tinjauan (`review_token`). Kalau data berubah sesudah ditinjau, ditolak `CP7_RECEIPT_FIX_REVIEW_CHANGED`.
- Semua efek stok, biaya, HPP, AP, dan jurnal memakai writer Native yang sudah diterima. Tidak ada definisi, owner, atau ACL Native yang diubah.
- Dokumen asal tetap immutable sebagai riwayat. Riwayat revisi, lineage roll, lineage pemakaian, pemindahan tanggal jurnal, replay pembayaran, replay invoice, dan riwayat nama semuanya ada di skema privat `cp7_receipt_fix`, dengan trigger immutable.
- Kartu bahan v2 (`erp_cp7_get_material_ledger_v2`): baris penerimaan asal menampilkan jumlah yang berlaku (misalnya 80, asli 100), dan saldo berjalan sesudahnya ikut berubah. Baris mentah tetap bisa dilihat sebagai anggota audit.
- Tanggal jurnal: pembalikan Native bertanggal hari ini. Efek pastinya dipindah ke tanggal ekonomi asal lewat pasangan jurnal netral (hari ini) dan efektif (tanggal asal).
- Untuk invoice, tanggal per efek (tanggal invoice, hari produksi, hari jual) diukur dengan **dry run Native** yang di-rollback: invoice yang sama diposting ulang pada tanggal bukunya sendiri. Hasilnya harus persis kebalikan pembalikan Native per akun dan dimensi. Kalau tidak sama, ditolak `CP7_RECEIPT_FIX_INVOICE_RESTATEMENT_MISMATCH`.

## Batas yang masih berlaku (jujur)

1. Invoice supplier yang **juga mencakup penerimaan lain** ditolak (`CP7_RECEIPT_FIX_INVOICE_SHARED`). Batalkan invoice gabungan itu dulu.
2. Baris invoice harus menunjuk baris penerimaan yang tetap ada. Menghapus barang yang sudah ditagih ditolak (`CP7_RECEIPT_FIX_INVOICE_LINE_ORPHAN`).
3. Tidak ada alur refund supplier. Kalau sudah dibayar lebih dari total yang benar, permintaan ditolak.
4. Salah bahan A→B hanya memindahkan pemakaian jenis potong (`CUTTING_GROUP` / `CUTTING_GROUP_RETURN`). Pemakaian lain pada roll itu (misalnya transfer, kain kantong) ditolak dengan nama pemakaiannya.
5. Retur supplier, koreksi harga lama, kredit supplier, kain kantong, dan penerimaan hasil impor saldo awal tetap memblokir dengan pesan yang jelas.
6. Periode tertutup mengikuti aturan Native (`post_journal` memakai hari pengakuan dengan tanggal ekonomi tetap). Belum ada kasus uji khusus untuk periode tertutup di paket ini.
7. Aksesori dibetulkan dalam satuan dasar.

## File

- SQL: `scripts/cp7-src/procurement/correction.sql`, `scripts/cp7-src/procurement/material-name.sql`
- Harness: `scripts/cp7_receipt_correction_{manifest.json,cases.py,bundle.py,verify.py,probe.py,browser.mjs,browser_fixture.py}`, workflow `.github/workflows/cp7-receipt-correction.yml`
- UI: `src/ReceiptCorrectionPanel.tsx` (di Pembelian & Penerimaan), `src/MaterialNamePanel.tsx` (di Bahan & Roll, kolom mutasi), `src/receiptCorrectionContract.ts` (+ tes)
- File bersama yang ikut disentuh (mohon diketahui GPT): `src/ConnectedProcurementPage.tsx`, `src/ConnectedMaterialsPage.tsx` (+ dom test), `src/productionRecovery.ts` (domain `RECEIPT_CORRECTION`, `MATERIAL_NAME`), `src/types/database.preconnect.ts`, `scripts/check-source-ownership.mjs`, `scripts/check-access-catalog.mjs` (registrasi 5 RPC browser baru; kartu bahan v1 → v2).

## Temuan untuk GPT (koreksi nota, bukan scope saya)

`LOCAL_PG16_DEV`, bukan bukti; mohon direproduksi di harness note-correction GPT.

Satu nota dengan SKU yang sama di dua baris (5 dan 10). Baris 10 dibetulkan menjadi 6. Di `scripts/cp7-src/sales/correction.sql`, kedua baris SALE pengganti diberi anchor ke baris SALE asli **pertama** dengan produk, lokasi, dan grade yang sama (`order by ... limit 1`, tanpa mengecualikan baris asli yang sudah dipasangkan). Hasil di buku FG:

- Sebelum: −5 (saldo 95), −10 (saldo 85).
- Sesudah: **−11 (saldo 89), 0 (saldo 89)**.
- Seharusnya: −5 (saldo 95), −6 (saldo 89).

Total akhir benar, tetapi baris kedua (yang bisa sudah dipisah owner di buku pergerakan stok) menjadi 0 dan saldo berjalan di posisi baris pertama salah. Usulan: pasangkan baris pengganti ke baris asli per urutan baris untuk produk yang sama (atau lewat lineage baris), dan kecualikan baris asli yang sudah dipakai sebagai anchor dalam koreksi yang sama.

## Bukti CI

Workflow `.github/workflows/cp7-receipt-correction.yml`, artefak `cp7-receipt-correction` (`cp6-proof/t3/CP7_RECEIPT_CORRECTION.json`). Run yang gagal tetap dicatat.

| Run | Commit | Hasil | Catatan |
|---|---|---|---|
| [37019103974](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37019103974) | `1baa7ce9` | **FAIL** (0 kasus berjalan) | Probe berhenti di `RF_UNDECLARED_GRANT`: katalog menulis `cp7_procurement."decimal"(jsonb,boolean)` (pakai tanda kutip), sedangkan grant yang dideklarasikan tanpa kutip. Diperbaiki di `61c36bbe`. |
| [37021304465](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37021304465) | `61c36bbe` | **FAIL** (INCOMPLETE) | Native **22/22 PASS** (termasuk `RF_YEAR_HISTORY_364`, tiga kasus invoice, dua kasus nama bahan), race **3/3 PASS**, HTTP Auth nyata **1/1 PASS**, CP6 dipulihkan, advisor gate lolos. Browser **0/2**: (a) desktop: halaman tetap menampilkan penerimaan lama sesudah disimpan, karena panel meminta reload halaman saat envelope masih tercatat pending; (b) HP: sesudah reload, daftar penerimaan terkunci oleh hasil yang belum diketahui, sementara tombol Reconcile hanya ada di panel yang perlu memilih penerimaan dulu. Dua-duanya bug UI nyata dan diperbaiki di `4990c57f`. |
| [37024948067](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37024948067) | `4990c57f` | **FAIL** (INCOMPLETE) | Native 22/22, race 3/3, HTTP 1/1 PASS. Browser desktop **PASS** (termasuk pembetulan nama bahan di halaman Bahan & Roll). Browser HP INCOMPLETE di `requests 2 !== 1`: fixture menghitung seluruh tabel permintaan, padahal permintaan dari alur desktop masih ada. Hitungan dipersempit ke penerimaan ini (dan bahan ini untuk nama); maksud oracle tetap sama: satu permintaan untuk satu penerimaan, juga sesudah balasan hilang dan reconcile. |
| [37026064573](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37026064573) | `415b76a6` | **PASS** | **28/28**: native 22/22, race 3/3, HTTP Auth nyata 1/1, browser 2/2 (desktop termasuk pembetulan nama bahan; HP termasuk balasan hilang lalu reconcile dengan UUID yang sama). `observed_case_count=28`, CP6 dipulihkan (`cp6_restored=true`), advisor gate lolos, console error 0. Ini bukti kandidat di runner CI sekali pakai, belum penerimaan auditor independen dan belum hosted. |

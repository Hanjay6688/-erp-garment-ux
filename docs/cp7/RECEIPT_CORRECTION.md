# Benerin penerimaan bahan & Benerin nama bahan (CP7, cabang `claude/new-session-deapao`)

Status: **kandidat, belum diterima auditor independen** (run CI terakhir 37083713960: 39/39 PASS; run gagal tetap dicatat di "Bukti CI"). `production_go=false`, CP6 tetap HOLD, `audit_complete=false`. Hasil `LOCAL_PG16_DEV` di bawah hanya catatan kerja, **bukan bukti**. Bukti hanya dari run workflow `cp7-receipt-correction` (lihat bagian "Bukti CI").

## Untuk apa

Owner perlu membetulkan penerimaan bahan yang **sudah diposting dan sudah dipakai** (dipotong, dijual, dibayar), bukan hanya ditolak. Pembetulan harus berlaku sejak tanggal kejadian aslinya, bukan dicatat sebagai selisih hari ini, dan seluruh transaksi lain harus tetap konsisten.

| Kasus owner | Yang dilakukan sistem | Kasus uji |
|---|---|---|
| Jumlah roll/qty salah ketik (turun atau naik), sesudah dipotong | Penerimaan asal dibalik pada waktu fisiknya sendiri. Penerimaan pengganti yang persis diposting pada waktu yang sama. Roll fisik yang sama dipakai (id roll tetap), jadi potongan, transfer, dan riwayat keluar-masuk bahan tetap menunjuk roll yang sama. Recost bahan, HPP PO, dan GL dihitung dari tanggal barang datang. | `RF_QTY_DOWN_AFTER_CUTTING`, `RF_QTY_UP_AFTER_CUTTING`, `RF_YEAR_HISTORY_364` |
| **Nomor roll salah ketik** (misalnya tercatat R-21, label fisik R-12), juga pada roll yang sudah dipotong, dan nomor yang tertukar antar roll | Roll yang sama tetap dipakai (id, pemakaian, transfer, dan riwayat tetap). Hanya nomornya yang berubah, lewat nomor sementara privat, jadi nomor juga bisa ditukar antar roll di penerimaan yang sama. Nomor lama dan baru disimpan di `roll_lineage` (`previous_roll_number`) dan di riwayat dokumen. Nomor yang dipakai dua kali atau sudah dipakai roll lain dari bahan yang sama ditolak (`CP7_RECEIPT_FIX_ROLL_NUMBER_TAKEN`). Tidak ada efek stok atau buku besar. | `RF_ROLL_NUMBER_TYPO_USED_ROLL` |
| **Nomor surat jalan** (nomor nota penerimaan) salah ketik | Penerimaan pengganti memakai nomor yang benar (`<nomor benar> · R1-…`), dan revisi berikutnya tetap memakai nomor yang benar itu. Nomor lama tetap di dokumen asal dan riwayat. Nomor yang sudah dipakai penerimaan lain ditolak (`CP7_RECEIPT_FIX_PURCHASE_NUMBER_TAKEN`). Tanpa efek stok atau buku besar bila hanya nomornya yang berubah. | `RF_HEADER_TYPO` |
| **Nomor, tanggal, dan jatuh tempo invoice supplier** salah ketik | Diisi di baris invoice pada panel yang sama. Invoice lama dibalik, invoice baru diposting dengan nomor yang benar (`· R1`) pada tanggal invoice yang benar. Jumlah efeknya sama; hanya tanggalnya pindah dari tanggal yang salah ke tanggal yang benar. Nomor invoice lain dari supplier yang sama ditolak (`CP7_RECEIPT_FIX_INVOICE_NUMBER_TAKEN`). | `RF_INVOICE_HEADER_TYPO` |
| **Tanggal & jam datang** salah ketik | Penerimaan pengganti diposting pada waktu yang benar. Efek stok, HPP, dan utang pindah dari tanggal yang salah ke tanggal yang benar; nilainya sama. Recost dihitung dari tanggal yang lebih awal. Kalau roll sudah dipakai atau dipindah sebelum tanggal yang baru, atau saldo aksesori di gudang akan minus, permintaan ditolak (`CP7_RECEIPT_FIX_DATE_AFTER_USE`). Tanggal di masa depan ditolak (`CP7_RECEIPT_FIX_DATE_FUTURE`). | `RF_ARRIVAL_DATE_TYPO` |
| **Gudang** salah pilih | Stok pindah ke gudang yang benar sejak tanggal datang; gudang lama menjadi 0. Hanya untuk barang yang belum dipakai atau dipindah; kalau sudah, ditolak (`CP7_RECEIPT_FIX_LOCATION_USED`) dan jalannya adalah transfer. | `RF_WAREHOUSE_TYPO` |
| **Supplier** salah pilih | Utang pindah ke supplier yang benar. Pembayaran diputar ulang dengan tanggal dan kas aslinya. Invoice supplier ikut pindah supplier (Native mewajibkan invoice dan penerimaan dari supplier yang sama), dan roll ikut tercatat dari supplier yang benar. Ditolak bila invoicenya juga mencakup penerimaan lain dari supplier lama (`CP7_RECEIPT_FIX_SUPPLIER_SHARED_INVOICE`) atau pembayarannya dari uang muka saldo awal supplier lama (`CP7_RECEIPT_FIX_SUPPLIER_ADVANCE_PAYMENT`). Kelebihan bayar dan ganti supplier dilakukan dalam dua langkah. | `RF_SUPPLIER_TYPO` |
| Jumlah roll salah (3 tertulis, datang 2) | Roll yang belum terpakai ditutup (lineage `REMOVED`). Roll terpakai tidak bisa dihapus. | `RF_ROLL_COUNT_TYPO_UNUSED_ROLL`, `RF_REMOVED_ROLL_USED_REFUSED` |
| Jumlah dibetulkan di bawah yang sudah terpakai | Ditolak dengan angka pemakaian | `RF_ROLL_BELOW_USE_REFUSED` |
| Harga penerimaan salah (sesudah dipotong, dijual, diretur) | Selisih masuk bahan sisa, barang jadi, dan HPP penjualan sesuai posisi barangnya | `RF_PRICE_AFTER_SALE_AND_RETURN` |
| Salah pilih bahan A, padahal yang datang bahan B (sudah dipotong) | Roll pindah ke bahan B. Pemakaian potong yang sama (baris, waktu, jumlah) sekarang tercatat di bahan B, dengan atribut lama disimpan di `movement_lineage`. Riwayat bahan A menjadi 0. | `RF_WRONG_MATERIAL_AFTER_CUTTING`, `RF_WRONG_MATERIAL_AND_PRICE` |
| Harga final di **invoice supplier** salah (setahun lalu pun) | Invoice lama dibalik dengan writer Native, lalu efeknya dipindah ke tanggal ekonominya sendiri. Invoice yang benar diposting ulang dengan tanggal invoice yang sama. Tidak ada selisih yang dicatat hari ini, kecuali barang yang memang terjual hari ini. | `RF_INVOICE_PRICE_AFTER_SALE`, `RF_INVOICED_QTY_DOWN_WITH_PAYMENT` |
| Invoice supplier yang **juga mencakup penerimaan lain** (invoice gabungan) | Invoice dibetulkan utuh. Baris penerimaan ini mengikuti angka yang benar; baris penerimaan lain dicatat ulang apa adanya pada invoice baru dengan tanggal yang sama. Pembayaran penerimaan lain itu dibalik lalu diputar ulang utuh ke penerimaan yang sama, dengan tanggal dan kas aslinya, sehingga statusnya tetap (misalnya tetap LUNAS). Sumber penerimaan lain tidak berubah; hanya waktu "harga final dicatat" milik Native yang mengikuti invoice baru. Penerimaan lain itu kemudian juga bisa membetulkan invoice yang sama: nomor invoice unik per supplier (termasuk yang sudah dibalik), jadi invoice pengganti memakai akhiran berikutnya yang masih kosong (`· R1`, `· R2`, …). Sebelum perbaikan ini, pembetulan kedua gagal dengan *duplicate key* (direproduksi di `LOCAL_PG16_DEV`). | `RF_SHARED_INVOICE_CORRECTED` |
| Pembayaran supplier sudah ada | Dibalik lalu diputar ulang ke dokumen yang benar dengan tanggal, kas, dan jumlah aslinya. Tidak ada uang yang berubah. | `RF_PAYMENT_REPLAY` |
| Pembayaran dari **uang muka saldo awal** | Diputar ulang dari uang muka yang sama (bukan kas). Validasi Native memeriksa sisa uang muka, pihak, dan tanggalnya. Sisa uang muka dan saldo bank tidak berubah. Sebelum perbaikan ini, pembetulan penerimaan seperti itu gagal dengan "Active cash/bank account is required" (direproduksi di `LOCAL_PG16_DEV`). | `RF_OPENING_ADVANCE_PAYMENT_REPLAY` |
| Sudah dibayar lebih dari total yang benar (keputusan owner 2 Okt 2026: "retur bayangan") | Kelebihannya jadi kredit supplier dan dipotong ke nota lain dari supplier yang sama yang dipilih owner. Pembayaran asli dibagi: ke penerimaan yang benar sebesar utangnya, sisanya ke nota tujuan, dengan tanggal dan kas pembayaran asli serta catatan "retur bayangan … barang tidak pernah diterima". Berlaku untuk kain dan aksesori. Kalau belum ada nota tujuan, atau jumlahnya tidak pas, permintaan ditolak tanpa efek. Kalau kelebihan itu berasal dari uang muka saldo awal, nota tujuannya harus bertanggal sama atau sebelum tanggal pemakaian uang muka itu (aturan Native); kalau tidak, ditolak dengan pesan yang jelas. | `RF_OVERPAID_CREDIT_TO_NEXT_NOTA`, `RF_PAID_EXCEEDS_CORRECTED_REFUSED`, `RF_OPENING_ADVANCE_PAYMENT_REPLAY` |
| Penerimaan di **periode yang sudah ditutup** | Pembetulan diterima. Jurnal tetap memakai tanggal ekonomi asal (di periode tertutup), dengan tanggal pengakuan hari ini, sesuai aturan periode tertutup Native. Stok, HPP, dan perubahan buku besar sama dengan pembetulan biasa, dan semua cek integritas tidak berubah. | `RF_CLOSED_PERIOD_CORRECTION` |
| Jumlah aksesori (barang tanpa roll) dibetulkan, padahal sebagian sudah keluar dari gudang penerimaan | Batas minimumnya adalah jumlah yang sudah keluar dari gudang penerimaan sesudah tanggal terima (saldo berjalan terendah di lokasi itu). Batas ini tampil di panel ("sudah keluar 16"). Kalau dibetulkan di bawahnya, atau bahannya diganti, ditolak dengan nama (`CP7_RECEIPT_FIX_LINE_BELOW_USE`). Sebelumnya hanya pengaman Native yang menolak, dengan pesan teknis. | `RF_ACCESSORY_LINE_QTY` |
| Nama bahan salah ketik | Hanya `material_name` yang berubah pada bahan yang sama. SKU, jenis, satuan, kategori, stok, biaya, roll, dan mutasi tetap. Nama yang sudah dipakai bahan lain ditolak, karena itu masalah identitas, bukan typo. | `RF_MATERIAL_NAME_TYPO`, `RF_MATERIAL_NAME_REFUSALS` |
| **Kode bahan (SKU) salah ketik** | Di panel yang sama ("Benerin nama / kode bahan" di Bahan & Roll). Hanya `material_sku` (dan nama bila ikut diubah) yang berubah pada bahan yang sama; jenis, satuan, stok, biaya, roll, dan mutasi tetap. Kode lama dan baru disimpan di riwayat. Kode yang sudah dipakai bahan lain (tanpa membedakan huruf besar/kecil) ditolak (`CP7_MATERIAL_NAME_SKU_TAKEN`). | `RF_MATERIAL_SKU_TYPO` |

Kasus lain: `RF_REPEATED_REVISIONS` (R1, R2: yang terakhir berlaku, tetap satu baris di riwayat keluar-masuk bahan), `RF_REPLAY_SAME_REQUEST` (satu UUID, satu efek), `RF_REVIEW_CHANGED_REFUSED` (data berubah sesudah ditinjau), `RF_ACCESS_CURRENT_AUTHORITY`, `RF_LATE_FAILURE_ATOMIC` (gagal di langkah terakhir: tidak ada efek tersisa), `RF_ACCESSORY_LINE_QTY` (aksesori dalam satuan dasar; GRNI ikut), `RF_INVOICE_INCOMPLETE_REFUSED` (keputusan invoice wajib, jumlah invoice tidak boleh melebihi penerimaan, semua baris invoice wajib ada), tiga race (`RF_RACE_*`), satu HTTP Auth nyata, dan dua alur browser (desktop serta HP dengan balasan hilang lalu reconcile; di desktop juga ada pembetulan nama).

Oracle integritas di setiap kasus utama: semua `erp.run_v*_checks()` sebelum dan sesudah **tidak berubah**, `V2620U_JOURNAL_REVERSAL_BUSINESS_DATE = 0`, dan perubahan buku besar per akun (dan per tanggal ekonomi pada kasus invoice) sama persis dengan angka yang ditulis sebelum kasus dijalankan.

## Cara kerjanya (ringkas)

- Satu perintah atomik `erp_cp7_correct_receipt_v1(payload, request_id, expected_version)` dengan token tinjauan (`review_token`). Kalau data berubah sesudah ditinjau, ditolak `CP7_RECEIPT_FIX_REVIEW_CHANGED`.
- Semua efek stok, biaya, HPP, AP, dan jurnal memakai writer Native yang sudah diterima. Tidak ada definisi, owner, atau ACL Native yang diubah.
- Dokumen asal tetap immutable sebagai riwayat. Riwayat revisi, lineage roll, lineage pemakaian, pemindahan tanggal jurnal, replay pembayaran, replay invoice, dan riwayat nama semuanya ada di skema privat `cp7_receipt_fix`, dengan trigger immutable.
- Riwayat keluar-masuk bahan (panel **Mutasi** di halaman Bahan & Roll; RPC `erp_cp7_get_material_ledger_v2`): baris penerimaan asal menampilkan jumlah yang berlaku (misalnya 80, asli 100), dan saldo berjalan sesudahnya ikut berubah. Baris mentah tetap bisa dilihat sebagai anggota audit.
- Tanggal jurnal: pembalikan Native bertanggal hari ini. Efek pastinya dipindah ke tanggal ekonomi asal lewat pasangan jurnal netral (hari ini) dan efektif (tanggal asal).
- Pembayaran diputar ulang lewat satu helper (`replay_payment`): tanggal, kas, metode, dan referensi asli. Pembayaran dari uang muka saldo awal dihubungkan lagi ke uang muka yang sama, mengikuti pola koreksi nota GPT (`cp7_note`).
- Penolakan perintah ditampilkan di panel dalam bahasa Indonesia (misalnya "Kredit melebihi sisa tagihan nota tujuan (SJ-7)."). Kode dan status error tetap sama, jadi pemulihan (reconcile) tetap membaca penolakan yang pasti.
- Untuk invoice, tanggal per efek (tanggal invoice, hari produksi, hari jual) diukur dengan **dry run Native** yang di-rollback: invoice yang sama diposting ulang pada tanggal bukunya sendiri. Hasilnya harus persis kebalikan pembalikan Native per akun dan dimensi. Kalau tidak sama, ditolak `CP7_RECEIPT_FIX_INVOICE_RESTATEMENT_MISMATCH`.

## Batas yang masih berlaku (jujur)

1. Invoice gabungan ditolak hanya bila penerimaan lain pada invoice itu punya retur supplier yang sudah diposting dan mengurangi utang (`CP7_RECEIPT_FIX_SHARED_INVOICE_RETURN_ACTIVE`). Writer Native memang menolak membalik invoice dalam keadaan itu. Batalkan retur itu dulu.
2. Baris invoice harus menunjuk baris penerimaan yang tetap ada. Menghapus barang yang sudah ditagih ditolak (`CP7_RECEIPT_FIX_INVOICE_LINE_ORPHAN`).
3. Kredit dari kelebihan bayar harus langsung ditempel ke nota yang sudah ada (writer Native tidak mengizinkan satu penerimaan dibayar melebihi utangnya). Kalau belum ada nota berikutnya, pembetulan dilakukan setelah nota itu dicatat. Refund tunai ke supplier tidak dibuat di sini.
4. Salah bahan A→B hanya memindahkan pemakaian jenis potong (`CUTTING_GROUP` / `CUTTING_GROUP_RETURN`). Pemakaian lain pada roll itu ditolak dengan nama pemakaiannya. Owner sudah menyetujui jalan keluarnya (2 Okt 2026): batalkan pemakaian itu, betulkan penerimaan, lalu catat ulang.
5. Retur supplier, koreksi harga lama, kredit supplier pada penerimaan ini, kain kantong, dan penerimaan hasil impor saldo awal tetap memblokir dengan pesan yang jelas.
6. Periode tertutup: pembetulan diterima dan diuji (`RF_CLOSED_PERIOD_CORRECTION`). Artinya laporan per tanggal ekonomi untuk periode yang sudah ditutup ikut berubah, sedangkan pencatatannya bertanggal pengakuan hari ini. Ini aturan Native yang sudah berlaku, bukan aturan baru.
7. Aksesori dibetulkan dalam satuan dasar.
8. Tanggal datang, gudang, dan supplier sekarang bisa dibetulkan, dengan pengaman: tanggal tidak boleh sesudah pemakaian pertama; gudang hanya untuk barang yang belum dipakai atau dipindah; supplier tidak untuk invoice gabungan atau pembayaran dari uang muka supplier lama. Kartu mutasi menampilkan baris penerimaan pada waktu dan gudang yang benar, sedangkan baris asal tetap ada dengan jumlah efektif 0.

## File

- SQL: `scripts/cp7-src/procurement/correction.sql`, `scripts/cp7-src/procurement/material-name.sql`
- Harness: `scripts/cp7_receipt_correction_{manifest.json,cases.py,bundle.py,verify.py,probe.py,browser.mjs,browser_fixture.py}`, workflow `.github/workflows/cp7-receipt-correction.yml`
- UI: `src/ReceiptCorrectionPanel.tsx` (di Pembelian & Penerimaan), `src/MaterialNamePanel.tsx` (di Bahan & Roll, kolom mutasi), `src/receiptCorrectionContract.ts` (+ tes)
- File bersama yang ikut disentuh (mohon diketahui GPT): `src/ConnectedProcurementPage.tsx`, `src/ConnectedMaterialsPage.tsx` (+ dom test), `src/productionRecovery.ts` (domain `RECEIPT_CORRECTION`, `MATERIAL_NAME`), `src/types/database.preconnect.ts`, `scripts/check-source-ownership.mjs`, `scripts/check-access-catalog.mjs` (registrasi 5 RPC browser baru; RPC riwayat Mutasi bahan v1 → v2).

## Serah terima untuk merge dengan arsitektur GPT

Bagian ini merangkum aturan yang dipakai "Benerin penerimaan" dan "Benerin nama / kode bahan", supaya saat digabung tidak ada aturan yang bertentangan. Kalau arsitektur GPT sudah punya aturan yang setara, pakai satu sumber saja dan hapus yang lain. Jangan menjalankan dua aturan berbeda untuk hal yang sama.

**Pola koreksi.** Pola ini sama dengan koreksi nota penjualan GPT (`cp7_note`):
- Dokumen asal tidak diubah.
- Writer Native membalik dokumen asal pada waktu sumbernya, lalu memposting dokumen pengganti yang persis.
- Riwayat disimpan di skema privat `cp7_receipt_fix`, dengan tabel immutable.
- Jurnal pembalik bertanggal hari ini dipindah ke tanggal ekonomi asal lewat pasangan jurnal netral dan efektif.

**Aturan yang perlu diselaraskan dengan aturan GPT:**
1. **Penomoran revisi.** Penerimaan: `<nomor dasar> · R<n>-<8 hex request>`. Invoice supplier: `<nomor dasar> · R<n>`, memakai akhiran kosong berikutnya, karena nomor invoice unik per supplier termasuk yang sudah dibalik.
2. **Putar ulang pembayaran supplier.** Tanggal, kas, metode, dan referensi tetap asli. Pembayaran dari uang muka saldo awal dihubungkan lagi ke uang muka yang sama; polanya disalin dari `cp7_note`. Kalau GPT punya helper umum, pakai satu helper.
3. **Kelebihan bayar ("retur bayangan", keputusan owner 2 Okt 2026).** Pembayaran asli dibagi ke nota lain dari supplier yang sama, dengan catatan "barang tidak pernah diterima". Ini bukan dokumen retur Native dan bukan `bf_supplier_credit_moves_v1`. Kredit klaim laundry GPT (BD) adalah mekanisme terpisah.
4. **Penulisan ke tabel Native di luar writer Native.** Perintah ini dimiliki `postgres`, sehingga melewati trigger "frozen" milik Native untuk hal-hal berikut:
   - `material_rolls`: `purchase_item_id`, `original_qty`, `roll_number`, `supplier_id`, `received_at`. Tujuannya agar roll fisik yang sama tetap dipakai.
   - `material_stock_movements`: `material_id` dan `roll_id`, hanya untuk pemakaian potong pada kasus salah bahan A→B.
   - `cutting_group_rolls.roll_id`.
   - `materials`: `material_name` dan `material_sku`.
   - Baris baru di `initial_import_prepayment_payments`.

   Semuanya dicatat di lineage privat. Kalau GPT menambah guard pada kolom-kolom ini, perintah ini harus dikecualikan secara eksplisit.
5. **Kartu mutasi bahan.** Halaman Bahan & Roll memakai `erp_cp7_get_material_ledger_v2` (bukan v1). Baris penerimaan yang dibetulkan digabung ke baris asal, kecuali bila tanggal atau gudangnya berubah: baris asal tetap ada dengan jumlah efektif 0, dan baris baru tampil pada waktu dan gudang yang benar.
6. **Pesan penolakan.** Pemetaan kode `CP7_RECEIPT_FIX_*` dan `CP7_MATERIAL_NAME_*` ke bahasa Indonesia ada di `src/receiptCorrectionContract.ts` (`correctionRefusal`), bukan di `src/lib/clientError.ts` milik GPT. Kalau GPT memusatkan pemetaan, pindahkan ke sana.
7. **Domain pemulihan.** Domain `RECEIPT_CORRECTION` dan `MATERIAL_NAME` didaftarkan di `src/productionRecovery.ts`.
8. **Batas akses.** Hanya OWNER/ADMIN dengan izin pengadaan (create, post, reverse) dan `finance.ap.view` untuk penerimaan, atau izin master kain/aksesori untuk nama dan kode bahan. Izin dicek ulang di awal dan akhir perintah.

**Aturan bisnis yang perlu satu sumber kebenaran:**
- Tanggal datang tidak boleh sesudah pemakaian pertama.
- Gudang hanya bisa diganti untuk barang yang belum dipakai atau dipindah.
- Supplier tidak bisa diganti untuk invoice gabungan atau pembayaran dari uang muka supplier lama.
- Nomor roll unik per bahan.
- Nama dan kode bahan unik tanpa membedakan huruf besar/kecil.
- Batas bawah aksesori ditentukan oleh saldo berjalan terendah di gudang.

**File bersama yang ikut disentuh** (sudah tercantum di bagian File):
- `src/ConnectedProcurementPage.tsx`, `src/ConnectedMaterialsPage.tsx` (+ dom test)
- `src/productionRecovery.ts`, `src/types/database.preconnect.ts`
- `scripts/check-source-ownership.mjs`, `scripts/check-access-catalog.mjs`

Di putaran-putaran sesudahnya tidak ada file GPT yang diubah.

**Bukti.** Workflow terpisah `cp7-receipt-correction`, dengan manifest `scripts/cp7_receipt_correction_manifest.json` (33 native, 3 race, 1 HTTP, 2 browser; run terakhir 37083713960 lulus 39/39). Run yang gagal tetap tercatat di bagian "Bukti CI".

## Temuan untuk GPT (koreksi nota, bukan scope saya)

**Tindak lanjut cabang integrasi:** temuan dua baris SKU yang sama sudah diperbaiki dengan lineage per baris di `sales/correction-lines.sql` dan ID baris asal dari formulir. Run [37037364406](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37037364406), sumber `ddac4e2c`, lulus lengkap **40/40** (28 database, 4 race, 3 Auth/HTTP, 5 browser). Angka main/per-lot benar −5/−6, main 95/89. Penghapusan, pengurutan ulang, harga berbeda, retur kedua baris, dan rollback atomic ikut lolos. Original lengkap ada di `evidence/owning-note-correction/qualified40-ddac4e2/`. Reproduksi lama di bawah tetap dicatat sebagai asal temuan. Native40 ini belum menguji gabungan penerimaan Claude, dan kegagalan timeout pada run sebelumnya tetap disimpan.

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
| [37029649347](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37029649347) | `f1e11a04` | **FAIL** (INCOMPLETE) | Native 22/23 PASS (termasuk `RF_OVERPAID_CREDIT_TO_NEXT_NOTA`), race 3/3, HTTP 1/1, browser 2/2 PASS. `RF_YEAR_HISTORY_364` INCOMPLETE sebelum pembetulan dijalankan: `duplicate key ... material_transfers_transfer_number_key` (`P09-48d477f36e54-T-c24aad`). Fixture transfer memberi nomor acak 6 hex; 364 transfer bisa bertabrakan (peluang kira-kira 0,4%) dan kali ini terjadi. Cacat fixture, bukan produk. Helper transfer di kasus ini sekarang memakai nomor berurutan per fixture; oracle tidak diubah, dan file fixture GPT tidak disentuh. |
| [37032710947](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37032710947) | `08d19674` | **PASS** | **32/32**: native 26/26 (termasuk `RF_SHARED_INVOICE_CORRECTED` dengan dua penerimaan yang membetulkan invoice yang sama, `RF_CLOSED_PERIOD_CORRECTION`, `RF_OPENING_ADVANCE_PAYMENT_REPLAY`, `RF_ACCESSORY_LINE_QTY` dengan stok yang sudah keluar, dan `RF_YEAR_HISTORY_364`), race 3/3, HTTP Auth nyata 1/1, browser 2/2. `observed_case_count=32`, `cp6_restored=true`, advisor gate lolos, console error 0. Bukti kandidat di runner CI sekali pakai, belum penerimaan auditor independen dan belum hosted. |
| [37048755577](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37048755577) | `899cd4e7` | **FAIL** (INCOMPLETE) | 34/35 PASS (termasuk `RF_ROLL_NUMBER_TYPO_USED_ROLL`, `RF_MATERIAL_SKU_TYPO`, race, HTTP, browser). `RF_OPENING_ADVANCE_PAYMENT_REPLAY` INCOMPLETE: "physical_at cannot be in the future". Kasus itu membuat penerimaan pada hari ini jam 10:00 WIB, padahal run berjalan pukul 01:41 WIB. Ini cacat waktu di fixture saya (run 37032710947 lulus karena berjalan pukul 23:20 WIB). Di `03dc836b` semua tanggal kasus itu digeser ke masa lalu; oracle tidak diubah. Di commit yang sama, isian kepala penerimaan dari commit ini diganti dengan nomor surat jalan yang benar dan kepala invoice supplier. |
| [37049589357](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37049589357) | `03dc836b` | **PASS** | **36/36**: native 30/30 (termasuk `RF_ROLL_NUMBER_TYPO_USED_ROLL`, `RF_HEADER_TYPO` untuk nomor surat jalan, `RF_INVOICE_HEADER_TYPO` untuk nomor/tanggal/jatuh tempo invoice supplier, `RF_MATERIAL_SKU_TYPO`, dan `RF_OPENING_ADVANCE_PAYMENT_REPLAY` dengan tanggal yang sudah digeser ke masa lalu, berjalan pukul 01:48 WIB), race 3/3, HTTP Auth nyata 1/1, browser 2/2. `observed_case_count=36`, `cp6_restored=true`, advisor gate lolos, console error 0. Bukti kandidat di runner CI sekali pakai, belum penerimaan auditor independen dan belum hosted. |
| [37083713960](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37083713960) | `dda66b9a` | **PASS** | **39/39**: native 33/33 (termasuk `RF_ARRIVAL_DATE_TYPO`, `RF_WAREHOUSE_TYPO`, `RF_SUPPLIER_TYPO`), race 3/3, HTTP Auth nyata 1/1, browser 2/2. `observed_case_count=39`, `cp6_restored=true`, advisor gate lolos. Bukti kandidat di runner CI sekali pakai, belum penerimaan auditor independen dan belum hosted. |

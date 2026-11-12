# Kualifikasi SKU gabungan 12 November 2026

## 12 November, 14.18 WIB

Run 43166466578 berhenti sebelum kasus transaksi dan browser. Definisi Money yang dipasang kedua kali menimpa pengaturan UTC untuk `capture_cost_source_v3(uuid)`. Arsip 13922802413 mempertahankan error pertama, nol kasus, pemulihan 407 tabel dan worker yang sudah berhenti.

Commit `882fdd376387f66e607cce62152eba9732654211` menempatkan UTC pada definisi terakhir sambil mempertahankan isi `cost_money_state` dan ACL. Replay PostgreSQL 17.6 menjalankan CREATE, REVOKE, dan CREATE OR REPLACE sesuai urutan pemasang. Kandidat lama memicu error katalog yang sama. Kandidat baru mencocokkan 19 kolom katalog fungsi dan rollback lulus. Pemeriksaan sumber juga cocok untuk 14.730 berkas induk dan 101 berkas kandidat. Uji lokal mencakup pemasangan fungsi pada fixture. [Bukti pemasangan](SKU_AF6E_FINAL_COST_CAPTURE_REPRODUCTION.json)

Run 43174323175 dimulai pada 14.18 WIB. Paket membawa 13 kasus Native, dua browser Auth, dan 12 bukti lama yang diperiksa setaranya. `verify_cost_capture_successor.py` disiapkan untuk memeriksa keempat arsip asli, dua kegagalan pemasangan, semua gate dan katalog aktual bila kualifikasi berhasil. [Run pengganti](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/43174323175/job/131034780958)

## Bukti sebelumnya

Run 43158542850 berhenti saat memasang SQL otomatis. Arsip GitHub 13919701197 berisi error pembatas dollar quote, nol kasus Native atau browser, dan pemulihan penuh 407 tabel. PostgreSQL 17.6 mereproduksi error dari SQL hasil pembentukan yang sama. SQL penerus mempertahankan kedua pembatas, mengubah pengaturan zona waktu dua fungsi, dan berhasil dipasang serta di-rollback pada skema fixture.

Kandidat `af6e5710c0a3265daeb14c8ccd078ea82c99c482` memuat pembetulan pemasang, UTC untuk penangkapan riwayat biaya non-PO, pemeriksaan akun AP supplier, dan perhitungan hash yang lebih cepat. Pemeriksaan mencocokkan seluruh 14.730 berkas induk. Run 43166466578 memulai paket 13 skenario Native dan dua browser, lalu berhenti sebelum skenario berjalan. Dua belas skenario E4EA yang tidak terdampak dapat dibawa setelah pemeriksaan kedua arsip dan pemulihan. [Run kandidat](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/43166466578/job/131009386319)

`verify_combined_sku.py` memeriksa sumber dan tiga arsip terminal sesuai identitas run. Simpan `canonical.zip`, `run.json`, `job.json` dan `artifact.json` pada direktori terpisah untuk E4EA, 3f2a dan penerus. Gunakan modul pembaca arsip yang sudah tersimpan pada paket pemeriksa SKU dan Mandor. Keluaran pada hasil sukses membawa katalog aktual, bukti 13 kasus baru, 12 bukti yang dipakai ulang, dua browser dan pemulihan.

Pemeriksaan sumber Global pada salinan lokal mencocokkan 223 jalur SKU, 14.881 berkas induk dan 23 berkas milik Global. Pemeriksaan otoritas menyandingkan 209 referensi dari sumber dengan proyeksi katalog E4EA untuk tiga pengaturan fungsi. Penerimaan masukan Global masih membutuhkan katalog aktual, sensus penulis, advisori, D1/E, pemulihan, dan otorisasi runtime yang berlaku.

Replay supplier memasang tiga pembaca asli dan usulan `STABLE` pada PostgreSQL 17.6 dengan dua backend. Pembaca lama melihat hasil campuran saat pembalikan di-commit. Ketiga pembaca `STABLE` melihat keadaan awal pada pembacaan yang sedang berjalan dan keadaan terbalik pada pembacaan berikutnya. Kontrol rollback tetap melihat keadaan awal. Identitas dan sumber AP berasal dari fixture. Definisi asli dipulihkan dan database fixture dihapus. Verifikasi produk OW06 tetap membutuhkan Auth dan basis gabungan yang diterima.

# Pemeriksa hasil SKU 43211990138

GitHub menjalankan kandidat `beda75853d9cb698ec912639002b3e4bd1ec52cf`, tree `108f843ddaa96571436e7f54f8cd9770612ae6cd`, job `131161671229`, attempt 1. Perbedaan dari AE0D terdiri atas 13 berkas pemeriksa setup sequence, pengawasan worker, jendela WIB, tes dan workflow. Lingkupnya membawa 12 hasil E4EA serta menjalankan 13 Native, pembatalan setelah transaksi terpakai, dan dua browser dengan login nyata. [Run GitHub](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/43211990138/job/131161671229)

`verify_beda_successor.py` memakai pembaca Original yang sama dengan AE0D. Jalankan setelah metadata run, job, dan artefak kanonis terminal tersedia. Masukkan direktori E4EA dan BEDA dengan `canonical.zip`, `run.json`, `job.json`, dan `artifact.json`, serta repositori sumber dengan objek kedua kandidat. Tambahkan direktori pembaca `sku-43166466578-combined` dan dependensinya pada `PYTHONPATH`.

```bash
python -B verify_beda_successor.py --repo <repo> --origin-source <mandor-source-repo> \
  --e4ea <original-e4ea> --current <original-beda> --output <direktori-baru>
```

Pada kelulusan, pemeriksa mengikat daftar ID audit yang benar-benar dialokasikan oleh seed, seluruh 15 sequence dari batas sebelum seed hingga sesudah skenario terakhir, dua Original browser dan asetnya, lima pemeriksaan, pemulihan dan worker ke identitas yang sama. Laporan worker memuat batas nominal 360/330 menit. Untuk run ini, waktu kerja aktual diverifikasi dari `wib_window` bersama cadangan 20 menit pemulihan, 10 menit artefak dan 35 detik terminasi. Katalog penuh 25 grup disimpan sebagai bytes asli setelah hasilnya terverifikasi.

Jika run gagal, simpan galat pertama dan catatan yang tersedia untuk worker, pemulihan, prasyarat dan hasil skenario. Pemeriksa menerbitkan receipt kegagalan dan tidak menerbitkan Root SKU.

Kontrol lokal memakai source kandidat persis, arsip gagal AE0D dan model receipt untuk bagian baru. Pemeriksa menolak ID audit yang hilang, selisih sequence antarskenario, cadangan artefak yang dipotong, batas kerja terlalu panjang, dan waktu selesai melewati hari WIB. Replay arsip AE0D memeriksa 13 hasil Native dan pemulihan 407 tabel. Hasil aktual BEDA menunggu artefak terminal.

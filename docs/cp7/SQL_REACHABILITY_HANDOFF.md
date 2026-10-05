# Sambungan berkas SQL CP7

`python scripts/cp7_bundle_reachability.py --output out/cp7-sql-reachability.json`

Pemeriksaan ini membaca dan menyusun paket F03/F04/F05 dalam urutan instalasi yang sama dengan runtime terpadu. Ia tidak menghubungi database atau menjalankan SQL. Hasil lokal saat ini:146 berkas SQL masuk paket aktif,1 berkas punya pemanggil diagnostik, seluruh147 punya pemilik. Exact source hashes dan digest paket ada di `evidence/sql-reachability/LOCAL_RECEIPT.json`. Kontrol negatif membuat satu berkas SQL sementara yang tidak dirujuk; pemeriksaan menolak berkas itu, lalu berkas dihapus dan pemeriksaan kembali PASS.

`snapshot/capture_probe.sql` sengaja tidak diinstal sebagai RPC. `cp7_p02_snapshot_probe.py` membaca berkas itu ke `SQL` dan fungsi `capture` mengirimkannya ke pembaca SQL pada clone CP6 terisolasi. Pemeriksaan memverifikasi sambungan tersebut lewat AST, bukan sekadar menerima nama berkas sebagai pengecualian. Jangan menghapus probe atau menambah daftar pengecualian untuk membuat hasil hijau.

Workflow `cp7-transaction-source.yml` menjalankan pemeriksaan sebelum install/qualification dan menyimpan `CP7_SQL_REACHABILITY.json` dalam artifact yang sama. Berkas baru yang tidak dirujuk, pemilik probe yang terputus atau probe diagnostik yang ikut masuk paket aktif menolak gerbang. Seluruh budget kasus Native dan gerbang restore/backup/advisor/Auth sebelumnya tetap.

PASS di sini hanya membuktikan sambungan berkas. Pemeriksaan import frontend, kepemilikan RPC/izin/CSS, perilaku bisnis, Auth, browser, pemulihan database dan acceptance tetap punya bukti masing-masing. Jangan menyamakan berkas tersambung dengan fitur CP7 selesai.

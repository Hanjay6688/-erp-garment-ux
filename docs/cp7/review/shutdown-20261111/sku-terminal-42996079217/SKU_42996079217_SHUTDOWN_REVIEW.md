# Pemeriksaan shutdown runner SKU pada 11 November 2026

| Run | Runner | Durasi job | Tahap terakhir yang terlihat |
| --- | --- | --- | --- |
| 42941789501 | 1000021016 | 57m24s | Pemasangan gabungan parent |
| 42996079217 | 1000021017 | 63m08s | Pemasangan moving average setelah Afui dan Mandor selesai |

Kedua log mencatat shutdown runner dan supervisor menerima SIGTERM eksternal
sebelum batas internal. Pemicu upstream belum diketahui. Kualifikasi Afui
42258224710 pada label `ubuntu-24.04` yang sama selesai dalam 5j10m43d.
Durasi yang teramati tidak menunjukkan batas umum satu jam pada label ini.

[Run pertama](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/42941789501/job/130265082676)
[Run kedua](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/42996079217/job/130440406014)
[Run Afui](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/42258224710/job/128031001027)

## Bukti yang masih berlaku

Afui selesai dalam 25m19s dan delta Mandor dalam 1m13s pada run kedua.
Moving average sempat berjalan 12m39s sebelum shutdown. Tahap money dan 27
kasus SKU belum tercapai. Worker keluar dengan kode -9 dan kelompok proses
kosong. Pembersihan database dan unggah arsip akhir dilewati oleh runner.
Checkpoint asli 13845740094 membuktikan pemeriksaan sebelum database.
Pemulihan run ini belum terverifikasi.

Arsip asli historis 13798150032 dari run 42881544889 memiliki 137 entri dan
lulus pemeriksaan CRC. Stack trace membuktikan alur moving average terdahulu
mencapai pengikatan state setelah DDL lalu gagal pada serialisasi `datetime`.
Perbandingan `69124742` ke `32590613` menunjukkan 15 berkas workflow dan
harness yang berubah. Sumber DDL moving average tetap pada preimage yang sama.
Perbaikan serialisasi telah lulus kontrol tipe. Arsip historis menyimpan dua
dump pembanding skema `erp` sebelum parent, masing-masing 215 perintah COPY.
Keduanya tidak berisi state lengkap Afui/Mandor yang baru dipasang. Database
run yang terputus tidak dapat dilanjutkan dari arsip yang tersedia.

[Run serialisasi lama](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/42881544889/job/130058811476)
[Perbandingan sumber](https://github.com/Hanjay6688/-erp-garment-ux/compare/69124742b7f312290ead868ee8b0bc0e94b25479...32590613a08e176536d9a19b3843f6a72f4479b4)

## Uji terarah

- PostgreSQL 17.6 disposable di loopback menunjukkan masuk ulang advisory lock
  di backend yang sama berhasil setelah perubahan role dalam savepoint. Sesi
  terpisah yang sengaja diblokir tercatat sebagai `Lock/advisory` dan
  `Lock/relation`. Pembatalan dan rollback melepas lock. Probe hanya merekam
  jenis wait dan jumlah blocker. Run GitHub yang terputus tidak punya sampel
  `pg_stat_activity`, sehingga penyebab tunggu pada run itu masih terbuka.
- Pengodean state kandidat diuji pada sensus Mandor asli 15,360,523 byte.
  Pengodean streaming dan batch menghasilkan SHA-256 yang sama. Pengodean
  state lengkap memerlukan sekitar 2,1 detik di workspace. Sampel ini tidak
  mewakili state runtime SKU yang hilang.
- Empat belas kontrol terarah lulus, meliputi SIGKILL, checkpoint, batas
  otorisasi, pengikatan tipe, dan kesetaraan workflow. Percobaan seluruh
  `test_qualification` pada salinan parsial menghasilkan enam error lokal.
  Lima membutuhkan worktree dan sumber historis, satu mengasumsikan gate
  tertutup sementara salinan kandidat telah diaktifkan. Hasil kelas lengkap
  tidak dipakai sebagai bukti kualifikasi.

Run kedua berakhir sesudah batas mulai 17.35 WIB untuk anggaran 6j25m.
Percobaan selanjutnya memerlukan mitigasi runner yang dapat dibuktikan atau
reproduksi terarah dengan kondisi awal yang setara, lalu jendela yang cukup.
Sampel yang diperlukan selama moving average ialah waktu per suboperasi
serta jenis wait database. Pertahankan sumber dan assertion, lalu verifikasi
25 Native, dua browser, lima pemeriksaan, pemulihan dan arsip akhir sebelum
membuka intake Global. Formal CP7 tetap 5/16.

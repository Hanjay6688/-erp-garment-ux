# Gladi backup malam ke Box

Program menerima arsip terenkripsi dan tanda terima dari proses ekspor. Satu tanggal WIB dapat mempunyai satu arsip terverifikasi. Nomor percobaan dan waktu unggah tidak memengaruhi tanggal itu.

## Menyiapkan satu mesin Linux

1. Sediakan Python 3.9 atau lebih baru, basis data zona waktu, rclone, dan ruang sementara privat untuk dua salinan arsip terbesar.
2. Di akun sistem khusus backup, hubungkan rclone dengan Box lewat persetujuan OAuth. Namai koneksi itu `box`. Tambahkan bagian `[boxbackup]` dari `../cp7c-backup-sintetis/box-250mb.conf` ke konfigurasi privat yang sama. Beri akun sistem tersebut izin baca dan tulis pada konfigurasi agar rclone dapat menyimpan pembaruan token. Simpan konfigurasi dengan izin 0600.
3. Siapkan direktori persisten privat untuk kunci proses. Jalankan semua percobaan folder tujuan dari satu mesin dengan direktori kunci yang sama. Pasang input ekspor secara konsisten dan simpan referensi sumber di luar folder Box.

Proses ekspor perlu menghasilkan `ciphertext_bytes`, `ciphertext_sha256`, dan `captured_at` (ISO 8601 dengan zona). Nilai diambil ketika arsip selesai dibuat. Tanda terima gladi lama dengan `environment=synthetic isolated loopback` juga dapat memakai `writer_rehearsal_utc`.

## Menjalankan satu siklus

Contoh ini dijalankan dari direktori program pada mesin yang punya akun Box. Sesuaikan jalur dengan lokasi ekspor dan direktori privat di mesin itu.

```sh
python3 backup_malam.py backup \
  --archive /srv/erp-export/current.cp7 \
  --reference /srv/erp-export/current.json \
  --state /var/lib/erp-box \
  --folder Gladi-Mesin-CP7C
python3 backup_malam.py retention-plan --folder Gladi-Mesin-CP7C
```

Program memeriksa salinan lokal, mengunggah arsip jika perlu, lalu mengunduhnya ke file baru. Setelah ukuran dan SHA-256 cocok, program menulis bukti `.verified.json` dan membacanya kembali. Percobaan ulang untuk pasangan tanggal dan isi yang sama memeriksa ulang arsip yang ada. Tanggal sama dengan isi lain, sumber kedaluwarsa, unduhan rusak, atau bukti yang berubah menghentikan proses dengan kode keluar selain nol.

Profil chunker menyimpan bagian maksimum 250.000.000 byte. Unduhan lewat `boxbackup:` otomatis mengembalikan satu arsip utuh. Arsip yang diunduh langsung dari tampilan Box dapat dipulihkan dengan alat pemulihan yang menyertai gladi Box.

## Jadwal dan retensi

Untuk timer systemd pada mesin yang dipilih, ekspresi kalender 01.00 WIB adalah `OnCalendar=*-*-* 01:00:00 Asia/Jakarta`. Selesaikan ekspor untuk tanggal WIB tersebut sebelum memanggil pekerja. Jika ekspor gagal atau tanda terima masih milik hari sebelumnya, catat kegagalan dan ulangi setelah ekspor hari itu tersedia. Workflow publik hanya menjalankan pengujian sintetis.

`retention-plan` membaca bukti dan memeriksa keberadaan serta ukuran arsip. Ia melaporkan 14 malam terverifikasi terbaru dalam `keep` dan arsip lebih lama dalam `eligible`. Output rencana tidak menghapus berkas. Bukti lama yang rusak atau arsip terverifikasi yang hilang menghentikan perencanaan. Pemeriksaan isi penuh dijalankan pada siklus backup dan uji pemulihan.

# Keputusan owner sesudah laporan r2 dikunci (16 Okt 2026) — dicatat auditor

Dicatat Fable sesudah `LOCK.md` r2 (commit 80f01cee). Laporan yang terkunci tidak diubah. Nomor keputusan resmi ditetapkan
penulis di `docs/cp7/OWNER_DECISIONS_20261008.md`.

**Teks owner:** "selesain biar gausa sembunyiin"

**Tafsiran auditor (dikembalikan ke owner bila keliru):** menggantikan D15-2 untuk mode Enteng. Layar yang sekarang
disembunyikan di Enteng diselesaikan dan disambungkan, bukan disembunyikan. Di kandidat 2e9d6a46 ada 17 menu tersembunyi
(`src/screenActivation.ts`):
- 11 sudah tersambung di mode uji dan tinggal dinyalakan untuk Enteng: Penjualan & Invoice, Semua Invoice, Retur Penjualan,
  Pembayaran Pelanggan, Ringkasan Keuangan, Kas & Bank, Piutang Pelanggan, Payroll & Kasbon, Absensi & Rate Harian,
  Jurnal & Transaksi Lain, Laporan & Tutup Buku. Susun Nota FG (layar batas di Enteng) termasuk.
- 6 belum punya layar tersambung sama sekali: Ringkasan Gudang, Riwayat Pelanggan, Reminder, Pengaturan ERP, Tutup Periode,
  Audit Trail. Ditambah pool HPP absensi yang belum punya layar. Menu yang isinya sama dengan menu lain (misalnya Tutup
  Periode dan Laporan & Tutup Buku) boleh digabung dengan persetujuan owner, bukan dibuat dua kali.
Layar ini memanggil fungsi `erp_cp7_*`, jadi di Enteng baru berfungsi sesudah lapisan database CP7 terpasang (CP7C).

**Oracle uji ulang Fable (ditetapkan sebelum pekerjaan dibuat):**
1. Di build mode Enteng tidak ada menu tersembunyi dan tidak ada angka contoh, kecuali yang owner setujui tertulis. Setiap
   menu memakai komponen tersambung yang sama dengan mode uji. Dashboard menampilkan angka asli atau pemberitahuan tanpa
   angka.
2. Uji browser memakai **build mode Enteng** terhadap database sekali pakai (bukan hanya build DISPOSABLE_TEST). Untuk
   setiap menu yang baru tampil: dibuka sebagai OWNER dan sebagai peran terbatas, desktop 1440 px dan HP 390 px tanpa
   luapan.
3. Rantai lewat layar di build mode Enteng: jahit selesai → Nota → payroll → bayar → Kas & Bank → laporan → tutup buku;
   barang jadi → invoice → pembayaran pelanggan → kas → piutang nol. Penjaga D14-2 (upah tidak dibayar sebelum utangnya),
   D14-3/D15-1 (kas tidak minus di kedua tanggal), dan D15-5 (cutover) tetap menolak dari layar.
4. Enam layar baru (atau gabungannya) membaca data asli, punya kasus native, race, HTTP, dan browser desktop + HP. Hak akses
   per peran sama dengan katalog akses. Tidak ada tulis yang melewati penulis Native.
5. Skenario Fable yang sudah ada tetap lulus tanpa diubah: `fable_cp17c_cash_basis.py`, `fable_r2_cash_both.py`, sensus layar
   `fable_cp17c_screens.mjs`, yang dijalankan juga pada build mode Enteng.

# QC, nilai persediaan dan Business Report

Uji memakai salinan PostgreSQL 17.6 dari arsip run 43132617378. Salinan ERP AB berasal dari dua dump identik dalam arsip. Driver membentuk transaksi delapan potong dari penulis ERP yang sama dengan skenario invoice dan produksi terdahulu. Invoice bahan memakai Rp29 per unit dan tarif laundry yang sudah ada memakai Rp7 per unit. Akun WIP, persediaan FG dan HPP penjualan masing-masing memiliki satu pemetaan aktif yang dapat diposting.

| Pengamatan per PO | Sebelum QC | Sesudah QC 3 potong |
| --- | ---: | ---: |
| WIP fisik | 8 PCS | 5 PCS |
| FG fisik dan tersedia | 0 PCS | 3 PCS |
| WIP buku besar | Rp288,00 | Rp180,00 |
| Persediaan FG buku besar | Rp0,00 | Rp108,00 |
| HPP penjualan | Rp0,00 | Rp0,00 |

Laporan owner menunjukkan pergerakan Rp108 dari WIP ke FG. Lot FG mempunyai HPP Rp36 per potong. Dua publikasi `INCLUDED` memakai periode 10–12 November 2026 WIB dan mengikuti empat tahap masing-masing. Stok aktual yang tersimpan berubah dari 0 ke 3 PCS. Angka dan hash sumber keuangan cocok dengan laporan Native yang dibaca pada tanggal sama. Revisi pertama tetap memiliki isi, bagian, waktu baca dan hash yang sama ketika dibuka kembali. Pembacaan arsip menolak ADMIN setelah izin `finance.reports.view` dicabut dalam fixture.

SQL publikasi dan pembaca keuangan berasal dari kandidat saat ini. Analisis tersimpan memakai satu target fixture dan transaksi biaya memakai penulis AB. Aktor ADMIN memakai izin ERP aktual melalui klaim sesi SQL fixture. Penerimaan kandidat gabungan masih memerlukan skenario dengan identitas owner, Auth dan sumber produksi gabungan pada salinan yang sudah diterima. Transaksi fixture di-rollback dan PostgreSQL lokal dihentikan setelah pemeriksaan.

Jalankan `qc_report_publication_probe.py` dari checkout Global tertutup yang bersih dengan direktori `scripts` dan psycopg dalam `PYTHONPATH`. Driver mengambil arsip E4EA dan PostgreSQL lokal dari direktori kerja induk yang sama seperti driver supplier dua sesi. Simpan ulang hasil untuk tanggal dan identitas eksekusi baru.

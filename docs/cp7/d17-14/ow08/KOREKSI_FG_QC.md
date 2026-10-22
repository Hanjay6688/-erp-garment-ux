# OW-08b butir 2.21 — koreksi barang jadi dan pembatalan QC

Sudah beres di kode dan lulus uji di komputer penulis; uji besar di database salinan (uji otomatis GitHub) belum
dijalankan. Belum dirangkai ke pemasang bawaan, sama seperti tahap OW lain sebelum digabung.

## Yang sekarang bisa

1. **Baris pembatalan barang jadi bisa dibuka ke dokumen aslinya.** Di buku mutasi atau kartu stok barang jadi, baris
   "pembalik" (stok yang dikembalikan karena transaksinya dibatalkan) dulu hanya bisa dibuka bila asalnya QC. Sekarang
   juga untuk penjualan (termasuk pemesanan draft invoice yang dibatalkan), retur penjualan, penyesuaian barang jadi
   (Gudang › Stock Adjustment) dan hasil rework. Tombol "Buka transaksi asal" membawa ke halaman dokumen yang sama
   dengan baris aslinya. Retur yang sudah dibetulkan, yang dulu ditolak layar walau server sudah menjawab, sekarang
   juga terbuka.
2. **Pembatalan finalisasi QC menyebut apa yang menghalangi.** Di Produksi › QC & Final SKU, bila "Batalkan
   finalisasi" tidak bisa dipakai, kalimatnya sekarang menyebut nomor dokumen yang menghalangi dan menu tempat
   membatalkannya (keputusan owner D14-10). Contoh:

   > FG hasil QC masih dipakai transaksi downstream aktif. Yang harus dibetulkan dulu: 1) Penyesuaian barang jadi
   > ADJ-9 mengubah lot LOT-1: di Gudang › Stock Adjustment, bagian Barang jadi, pilih Batalkan koreksi FG.
   > 2) Draft invoice INV-9 memesan barang dari lot LOT-1: di Penjualan › Penjualan & Invoice ubah drafnya atau pilih
   > Batalkan draft invoice.

   Yang disebut: PO yang sudah selesai (Keuangan › HPP & Rekalkulasi, Buka ulang PO), rework dan keputusan BS
   (Produksi › Barang BS & Rework), penjualan, draft invoice, retur, penyesuaian barang jadi, ganti merek, dan payroll
   yang memuat hak tagih aksesori (Keuangan › Payroll & Kasbon). Riwayat asli tetap tersimpan.

**Aturan penolakannya tidak berubah.** Kapan QC boleh dibatalkan sama persis seperti sebelumnya; hanya kalimatnya yang
lebih jelas. Kalimat lama tetap menjadi kalimat pertama.

## Yang sudah diuji

| Uji | Hasil |
|---|---|
| Database percobaan di komputer penulis (PostgreSQL 16, tabel tiruan kecil) | Semua fungsi lama dan baru terpasang. Pembaca transaksi asal: pembalik QC, penjualan, retur, retur yang dibetulkan, penyesuaian dan rework membuka dokumen yang sama dengan baris aslinya; ganti merek dan saldo awal tetap "belum didukung"; hak lihat diperiksa seperti sebelumnya. Pembatalan QC: untuk PO selesai, BS/rework, barang terpakai, payroll aksesori dan QC bukan POSTED, mesin lama dan baru sama-sama menolak dengan kode yang sama dan kalimat lama di depan; QC tanpa penghalang sama-sama berhasil. Daftar riwayat di layar QC: baris, urutan dan tanda "bisa dibatalkan" sama; hanya baris yang tertahan mendapat nama penghalang |
| Letak setiap perubahan pada teks fungsi yang terpasang | Setiap potongan yang diganti ditemukan tepat sekali, termasuk sesudah tahap OW-06 dan kasbon |
| Layar (uji unit) | Semua 1.928 uji di `src` lulus; uji baru untuk pembalik barang jadi gagal pada kode lama dan lulus pada kode baru; pemeriksaan tipe lulus |
| Pemeriksaan proyek (`scripts/check-*.mjs`) | 33 lulus, 3 pemeriksaan kepemilikan backend gagal seperti sebelum perubahan ini |

## Yang menunggu uji otomatis GitHub

Uji Native9 (`.github/workflows/cp7-ow08b-fg-correction-native.yml`) memakai data yang dibuat lewat penulis aplikasi
sungguhan: QC, draft invoice, penyesuaian, penjualan dan retur, rework, PO selesai dan dibuka ulang, lalu membandingkan
mesin lama dan baru pada keadaan yang sama, termasuk sensus semua QC dan semua jenis sumber di database salinan.
Hasilnya dicatat di sini setelah dijalankan.

## Yang belum didukung, dan kenapa

- **Pembalik ganti merek, saldo awal, penerimaan barang tanpa sumber, impor WIP dan retur saldo awal** tetap
  "belum didukung" bila dibuka dari buku: pembaca transaksi asal belum punya halaman dokumen untuk jenis itu.
  Penghalang ganti merek tetap disebut di pembatalan QC beserta menunya.
- **Hak tagih aksesori yang statusnya tertahan tanpa payroll aktif**: aplikasi belum punya tombol untuk
  mengembalikannya; kalimatnya menyebut hal itu apa adanya.
- **Payroll aksesori** belum diuji dengan rantai sungguhan di uji GitHub (belum ada contoh siap pakai); bagian ini
  diuji di database percobaan dan akan tercatat bila sensus menemui data seperti itu.
- Dua jawaban kecil berubah: pembalik pemesanan draft yang barisnya sudah dihapus karena draf diubah sekarang
  berkata "transaksi asal tidak tersedia" (dulu "belum didukung"); pengguna gudang tanpa hak lihat penjualan sekarang
  ditolak (dulu "belum didukung"), jadi isi penjualan tidak terlihat olehnya.

Rincian teknis: `scripts/cp7_fg_correction_source/` (tahap di atas tahap kasbon) dan `src/transactionSource.ts`.

# Belanja FG mandor melalui payroll — persiapan A, belum diaktifkan

Penyimpanan dan pemilik perubahan status sudah ditulis. Modul ini belum mempunyai
pemasang, perintah publik, sambungan pembayaran Native, pembaca saldo invoice,
atau pop-up aplikasi. Gerbang parent dan runtime masih tertutup. Tidak ada
penambahan kasus Native atau izin memakai produksi dari hasil model ini.

Identitas invoice dan payroll memakai UUID mandor yang sama melalui foreign key
gabungan. Nominal baris penyelesaian dan proyeksi harus persis nominal alokasi.
Nilai pecahan sen ditolak sebelum pembulatan penyimpanan. Satu nota hanya punya
satu kartu aktif pada payroll yang sama; nota yang sama boleh dialokasikan sebagian
ke payroll minggu lain melalui alokasi lain.

Alokasi mempunyai histori baru untuk RESERVE, RELEASE, SETTLE, REOPEN dan REVERSE.
Fakta posted tidak diubah atau dihapus. Pembukaan kembali pelunasan mempertahankan
reservasi; pembalikan penuh melepaskannya. Draf pembeli dan jembatan ke potongan
Native tetap berupa keadaan kerja yang bisa diperbarui oleh pemilik perintahnya.
Semua tabel memakai RLS dan tidak memberikan akses tabel/fungsi kepada peran browser.

`storage_model.mjs` menjalankan SQL penyimpanan pada PostgreSQL/WASM terisolasi,
dengan enam tabel Native model berisi kolom rujukan yang tipenya diperiksa terhadap
katalog Permanent15a yang sudah sah. Fungsi Native ERP, Auth HTTP, dua sesi, stok,
HPP, penjualan, jurnal dan pembayaran tidak dijalankan. Hasilnya menguji foreign key,
nominal, histori, perubahan status dan penolakan akses tabel; hasil itu bukan bukti
pelunasan invoice atau perhitungan upah.

Pekerjaan berikutnya: pertahankan mesin Penjualan existing; hubungkan master mandor
secara eksplisit; tambahkan pembaca kartu dan sumber review; pasang/lepas alokasi
dengan penguncian serta idempotensi; turunkan sambungan Native dari definisi parent
terakhir yang benar-benar diterima. Potongan FG harus keluar dari OTHER_INCOME dan
menjadi jurnal nonkas Dr CONTRACTOR_PAYABLE / Cr AR_CUSTOMER pada invoice yang sama.
Pembayaran kas hanya sebesar upah bersih. Selesaikan jalur neto nol, cicilan,
pembatalan/pembalikan, retur/perubahan saldo, tampilan desktop/HP dan dua tab sebelum
mengaktifkan modul. Jangan membuat sales_payments atau kasbon tunai buatan.

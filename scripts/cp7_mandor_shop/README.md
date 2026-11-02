# Belanja FG mandor melalui payroll — persiapan A, belum diaktifkan

Penyimpanan, pemilik perubahan status, pembaca kartu dan perintah privat untuk
pasang/lepas alokasi draft sudah ditulis. Modul ini belum mempunyai pemasang,
perintah publik, sambungan pelunasan Native atau pop-up aplikasi.
Gerbang parent dan runtime masih tertutup. Tidak ada
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

Perintah privat memakai identitas mandor yang eksplisit, token review sumber,
batas sisa invoice lintas payroll dan kapasitas neto payroll. Penguncian memakai
NOWAIT, serialisasi mandor/request, kunci invoice dan perlindungan empat tabel
hak akses. Request yang sama mengembalikan hasil tersimpan; perubahan payload
ditolak. Alokasi menambah potongan draft OTHER melalui jembatan yang eksplisit
dan menjalankan perhitungan ulang Native dengan konteks PREPARE existing.
Pelepasan menghapus potongan draft sambil menyimpan histori. Payroll yang sudah
APPROVED dibekukan. Saldo invoice yang berubah membatalkan review lama; kartu
yang masih terpasang tetap dapat dilepas ketika invoice sudah tidak aktif.

`allocation_model.mjs` menjalankan 15 pemeriksaan perilaku baru pada PG/WASM,
memakai definisi persis `recalculate_payroll` dan `cp7_installment.meaning`
dari katalog Permanent15a yang diterima. Tabel Native diperkecil; Auth, izin,
admission internal dan proyeksi saldo invoice dimodelkan secara eksplisit.
Ini membuktikan SQL alokasi pada batas model tersebut, termasuk contoh upah
2.000.000 dikurangi alokasi 300.000 menjadi pratinjau 1.700.000, tanpa jurnal.
Token usang diuji berurutan pada satu backend; ini belum uji dua sesi/tab.
Lima belas pemeriksaan penyimpanan lama tetap dipakai tanpa dijalankan ulang.

Pekerjaan berikutnya: pertahankan mesin Penjualan existing; hubungkan pilihan
pembeli ke master mandor; turunkan sambungan Native dari definisi parent
terakhir yang benar-benar diterima. Potongan FG harus keluar dari OTHER_INCOME dan
menjadi jurnal nonkas Dr CONTRACTOR_PAYABLE / Cr AR_CUSTOMER pada invoice yang sama.
`invoice_basis` harus membaca proyeksi pembayaran otoritatif yang sama sesudah
sambungan offset tersebut; persiapan sekarang belum memasang atau membuktikannya.
Pembayaran kas hanya sebesar upah bersih. Selesaikan jalur neto nol, cicilan,
pembatalan/pembalikan, retur/perubahan saldo, tampilan desktop/HP dan dua tab sebelum
mengaktifkan modul. Jangan membuat sales_payments atau kasbon tunai buatan.

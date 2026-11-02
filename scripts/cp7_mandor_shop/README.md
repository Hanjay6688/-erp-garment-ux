# Belanja FG mandor melalui payroll — persiapan A, belum diaktifkan

Penyimpanan, pemilik perubahan status, pembaca kartu, perintah privat untuk
pasang/lepas alokasi draft, persiapan identitas pembeli mandor serta penghubung
identitas draft/posting sudah ditulis.
Proyeksi privat pembayaran nonkas dan pemeriksa pasangan jurnal juga sudah ditulis.
Modul ini belum mempunyai pemasang, sambungan pelunasan Native atau pop-up
aplikasi yang diaktifkan. Sumber empat perintah publik sempit sudah disiapkan,
tetapi belum dipasang.
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

`buyers.sql` mencari master mandor aktif dan menyiapkan satu identitas pelanggan
Native per UUID mandor. Nama yang sama tidak menyatukan dua mandor atau pelanggan
toko. Kode pelanggan mempertahankan seluruh 128 bit UUID dalam 28 karakter;
tabrakan dengan kode pelanggan toko ditolak untuk ditinjau, bukan dipasang diam-diam.
Persiapan memakai izin Penjualan existing, review sumber, penguncian NOWAIT,
identitas request dan konteks Native privat. Perintah berulang memakai hasil
tersimpan, mandor/sumber yang berubah membatalkan review, dan pelanggan nonaktif
tidak diaktifkan lagi otomatis. Belum ada perintah publik atau sambungan formulir.

`buyer_model.mjs` lulus 20 pemeriksaan baru dengan definisi persis
`cp7_sales.command_access` dan tipe kolom master/konteks dari katalog D/E6e615
yang diterima. Auth, penyedia izin, penjagaan konteks audit dan sebagian tabel
Native dimodelkan secara eksplisit. Pengujian UUID nol/maksimum dan 100 identitas
menangkap pembulatan pada pembagian awal; implementasi memakai hasil bagi bulat
yang tepat sebelum diaktifkan. Model pertama tetap gagal. Model ini tidak
menjalankan invoice, stok, HPP, payroll, pembayaran, Auth HTTP atau dua backend.
Lima belas pemeriksaan alokasi dan lima belas pemeriksaan penyimpanan terdahulu
tetap dipakai tanpa dijalankan ulang.

`sale_identity.sql` menyiapkan satu trigger header Native yang hanya merekam
identitas. Perubahan pilihan mandor/toko dan pembatalan membersihkan pilihan draft.
Posting pertama menyimpan UUID mandor/pelanggan dan nama mandor pada saat posting.
Pengamatan posting berulang, pembayaran, retur dan pembalikan tidak mengubah
fakta pembeli yang sudah diposting. Fungsi invoice, stok, HPP, kas dan jurnal
Native tidak ditulis ulang. Sumber trigger ini belum dipasang pada ERP.

`sale_identity_model.mjs` lulus 17 pemeriksaan baru pada PG/WASM dengan tipe kolom
header/master dari katalog D/E yang diterima. Model menguji perubahan pilihan,
snapshot saat posting, penolakan perubahan pembeli posted, pembersihan konteks,
master nonaktif dan transaksi toko tanpa fakta mandor. Auth dan pemeriksaan
konteks Native dimodelkan; mesin transaksi Native dan browser belum dijalankan.
Lima puluh pemeriksaan penyimpanan/alokasi/pembeli sebelumnya tetap dipakai.

`offset_projection.sql` menyimpan snapshot akun pembayaran pada saat posting;
perubahan pemetaan akun berikutnya tidak mengubah jurnal lama. Pemeriksa mewajibkan
dua kaki jurnal nonkas yang persis, pembeli/invoice yang sama, potongan Native dan
histori alokasi yang sesuai. Jurnal awal serta pembalikan diperiksa sebelum commit.
Pembalikan memakai bentuk sumber Native `JOURNAL_REVERSAL`, jurnal berlawanan yang
persis, dan kejadian REOPEN/REVERSE yang sah. Pembayaran ulang memakai jurnal baru;
bukti pembalikan lama tetap sah setelah payroll kembali PAID. Pembaca saldo hanya
menghitung penyelesaian aktif, menolak jurnal tanpa pemilik, dan meminta koreksi
bila invoice tidak aktif masih mempunyai pembayaran offset.

Perubahan offset lokal sebelumnya belum sempat dipublikasikan ketika lingkungan
eksekusi hilang. Sumber ini dibangun ulang dari sumber publik yang tersimpan dan
referensi katalog D/E yang diterima. `offset_model.mjs` lulus 28 pemeriksaan baru
pada PG/WASM dengan tipe kolom 10 tabel Native yang dibandingkan terhadap katalog
tersebut. Ini menguji kode privat dan pemicu sebelum commit; batasan Native, Auth,
mesin jurnal/payroll/invoice, stok, HPP serta dua backend tidak dijalankan. Seluruh
67 pemeriksaan terdahulu dipakai tanpa dijalankan ulang. Hasil 19 pemeriksaan pada
sumber lokal yang hilang tidak dipakai sebagai bukti bagi sumber yang dibangun ulang.
Fungsi privat ini belum dipasang ke proyeksi saldo Native dan belum memicu pembayaran.

Pekerjaan berikutnya: pertahankan mesin Penjualan existing; hubungkan pilihan
pembeli ke master mandor; turunkan sambungan Native dari definisi parent
terakhir yang benar-benar diterima. Potongan FG harus keluar dari OTHER_INCOME dan
menjadi jurnal nonkas Dr CONTRACTOR_PAYABLE / Cr AR_CUSTOMER pada invoice yang sama.
`invoice_basis` harus membaca proyeksi pembayaran otoritatif yang sama sesudah
sambungan offset tersebut; persiapan sekarang belum memasang atau membuktikannya.
Pembayaran kas hanya sebesar upah bersih. Selesaikan jalur neto nol, cicilan,
pembatalan/pembalikan, retur/perubahan saldo, tampilan desktop/HP dan dua tab sebelum
mengaktifkan modul. Jangan membuat sales_payments atau kasbon tunai buatan.

`payment_owner.sql` menyiapkan empat pemilik privat untuk awal/akhir perintah
pembayaran, pelunasan nonkas dan pembalikannya. Identitas request diambil langsung
dari konteks perintah Native payroll atau cicilan yang sama; tidak menebak request
terakhir. Sumber invoice, mandor, potongan, hak akses serta akun dikunci dan ditinjau
ulang. Cicilan kas yang belum terakhir tetap berupa reservasi. Pada PAID, pemilik
memasang satu jurnal nonkas dan histori SETTLE; REOPEN mempertahankan reservasi,
pembalikan penuh/pembatalan melepaskannya. Potongan Native historis tetap disimpan.
Pembaca pembayaran invoice wajib berubah tepat sebesar kejadian FG; bila belum
terhubung, seluruh transaksi ditolak. OTHER_INCOME diperiksa agar hanya memuat
potongan biasa. Peran internal cp7_payroll_write hanya memperoleh begin/finish,
karena perintah Native tersebut memakai hak pemanggil; browser tidak diberi akses.

`native_payment_routes.py` menurunkan delapan definisi Native dengan 17 perubahan
yang dapat dibalik persis. Query OTHER pada pembayaran penuh dan cicilan akhir
mengecualikan jembatan FG. Semua jalur return proyeksi kredit lama dipertahankan
dengan tambahan offset invoice yang sama. Rumus kas neto, pengakuan upah, hak
akses, tanggal, review dan idempotensi Native tetap pada kode aslinya. Definisi
parent akhir harus sama dengan katalog yang ditinjau; perubahan parent menolak
pemasangan sampai ditinjau, bukan ditimpa. Sumber ini belum dipasang pada ERP.

Model pembayaran baru mempunyai 23 pemeriksaan logis: 19 yang sudah selesai
dipertahankan dari percobaan yang kemudian gagal pada pemulihan GUC izin model,
lalu hanya empat pemeriksaan tersisa dijalankan. Empat sisanya lulus pertama kali.
Dua kegagalan persiapan lebih awal (sintaks CASE SQL dan nama kolom fixture) tetap
disimpan; tidak dilabel lulus. Model memakai tipe kolom 32 tabel dari katalog D/E,
menjalankan badan definisi Native jurnal/pembayaran/reversal pada tabel model,
dan memodelkan izin, konteks pemanggil, sumber saldo invoice serta beberapa
penjagaan Native. Ini bukan pemasangan atau kualifikasi ERP, Auth, stok/HPP,
pengakuan upah, browser maupun dua backend. Sebanyak 95 model sebelumnya tidak
diulang. Jangan menjumlahkan cakupan model sebagai kasus Native baru.

Masih diperlukan pemasang dan adopsi profil program akhir, penjagaan retur/koreksi
invoice yang mempunyai offset aktif, sambungan pembeli/perintah publik/pop-up,
serta bukti Native penuh, Auth, desktop/HP dan dua tab. Selama itu runtime dan
perintah publik tetap tertutup.

`payment_guards.sql` menyiapkan enam fungsi dan enam trigger pada tabel Native
untuk jurnal FG, kaki jurnal, invoice dan retur. Jurnal/inverse harus berasal dari
pemilik payroll yang tepat dan mempunyai fakta lengkap sebelum commit. Kaki jurnal
posted tidak dapat diedit; sumber tidak dapat disamarkan, dan rantai pembalikan
tidak dapat dipakai untuk membalik inverse lagi lewat jurnal umum. Retur/koreksi
invois bersaldo offset aktif menunggu reversal payroll yang sah; perubahan status
pembayaran biasa tetap diperbolehkan. Reservasi draft bukan pelunasan.

Tiga belas pemeriksaan model pengaman lulus pada percobaan pertama, memakai
33 peta tipe kolom Native dan badan fungsi Native lama pada tabel model. Pemeriksaan
terarah baru ini memasang keenam trigger; 95 model lama serta 23 model pembayaran
tetap dipakai, tidak diulang. Mesin retur, Auth, penjagaan Native dasar, stok/HPP
dan dua backend tetap belum dijalankan. Pemasang/profil program akhir dan
pembuktian Native dengan seluruh lapisan tetap diperlukan sebelum modul dibuka.

`facade.sql` menyiapkan empat pintu publik: pilihan mandor, persiapan identitas
pembeli, kartu tagihan pada payroll terpilih, serta pasang/lepas kartu. Satu peran
NOLOGIN tanpa hak istimewa hanya dapat memanggil empat pemilik privat yang sudah
ada. Peran browser tidak memperoleh akses tabel/privat; peran anon dan service
tidak mendapat hak menjalankan pintu publik ini. Pemeriksaan aktor, izin saat ini,
sumber, review dan request tetap dilakukan pemilik privat existing.

Sembilan pemeriksaan baru lulus pada percobaan pertama di PG/WASM: hak peran,
pembeli bernama sama dengan UUID berbeda, minggu manual, kartu berisi alokasi
dan minggunya, replay tanpa potongan ganda, perubahan payload, pencabutan izin,
serta pelepasan draft. Setup memakai rumus kolom neto dan badan fungsi Native
yang sudah dipakai model alokasi; 131 pemeriksaan lama tidak diulang. Ini belum
Auth HTTP atau pemasangan ERP: provider izin/Auth, sebagian tabel/batasan dan
saldo invoice masih model yang dinyatakan dalam bukti. Pop-up dan integrasi
formulir Penjualan, pemasang/profil akhir serta kualifikasi lengkap tetap terbuka.

`facade_display.sql` menormalisasi nominal alokasi bersarang menjadi teks desimal
di PostgreSQL sebelum dikirim ke browser, tanpa mengubah field lain, urutan,
review, pemilik fungsi atau izin. Empat model baru lulus pertama kali, termasuk
nominal di atas batas integer aman JavaScript. 140 kontrol sebelumnya tidak diulang.

Pop-up terkontrol dan parser klien sudah ditulis dalam enam file UI tambahan;
belum dipasang ke halaman atau disambungkan RPC. Delapan kasus parser serta tujuh
kasus DOM lulus pertama kali, dan typecheck tidak menghasilkan diagnostik. Cakupan
ini menguji pilihan minggu/mandor, sen tepat, review ulang, pelepasan, data usang
dan klik ganda pada komponen. Metode dialog jsdom dimodelkan setelah diperiksa pada
dependensi yang benar; ini bukan bukti layout desktop/HP, Auth atau dua tab nyata.

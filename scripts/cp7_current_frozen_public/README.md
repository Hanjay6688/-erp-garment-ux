# A — persiapan dua fasad permintaan analisis beku

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.

Composer ini hanya persiapan opt-in pada cabang A. Tidak diimpor pemasang
bawaan atau aplikasi. Dua RPC baru dimiliki `cp7_capture`, hanya memberi
EXECUTE kepada pengguna terautentikasi, memakai search_path kosong dan UTC.
Tidak ada tabel, schema, penggantian fungsi lama atau perhitungan uang baru.

Permintaan operasional memakai SQL B pada c1dd6b5c byte demi byte, termasuk
pencabutan grant bawaan postgres. Permintaan keuangan meneruskan query dan UUID
ke pemilik privat A yang sudah mengikat mode STAGED sebelum seal pertama.
Identitas dan izin tetap dibaca server. Status, proses server dan halaman hasil
tetap memakai pemilik yang sama; pergantian rute tidak memberi izin baru.

Pemasang komponen B tidak dipanggil pada susunan A: pemeriksa exact request
pribadinya memang menolak dua delta privat A. A membuat delta penuh sendiri,
memeriksa parent keuangan sebelum delta, mengikat bukti tersebut, dan menerima
hanya dua fungsi publik baru pada seluruh22kelompok katalog. Katalog lama dan
otoritas tidak disubstitusi agar pemeriksa seolah cocok.

Inverse membandingkan seluruh baris dan sequence sebelum DDL apa pun. Perubahan
data mewajibkan cadangan/pemulihan penuh. Dependent view atau perubahan metadata
harus ditolak sebelum inverse; kegagalan DDL juga dibungkus transaksi atomik.

Kualifikasi berikutnya wajib menunggu Original Native45 A aktualPASS serta
Original fasad B aktualPASS dengan seluruh kasus Native/race/Auth, pin sumber,
pemulihan dan lima gate. Pemeriksaan lokal memakai parser dan katalog tiruan;
bukan hasil PostgreSQL, AuthHTTP, browser, factory atau penerimaan independen.
Jalankan source checker dari checkout `writer`, karena pembaca CP6 lama masih
memakai path relatif. production_go=false.

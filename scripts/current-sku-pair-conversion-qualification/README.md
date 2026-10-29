# Native qualifier prepared — dua fitur SKU owner 29 Oktober

Status **PREPARED, NOT EXECUTED**. Tidak ada workflow dipicu atau klaim actual
Native/Auth/browser/restore dari berkas ini. Gunakan pemasang
`cp7_sku_pair_conversion.composition`, yang menambah delta di atas
`cp7_vendor_receivable.composition`; jangan mengubah pemasang beku menjadi
pembungkus melingkar. Parent vendor yang sudah diterima: backend41c,
run40769840440, actual7 Native +3 races +1 Auth/HTTP; itu bukti parent,
bukan bukti modul SKU baru.

`fixture.py` membuat master sintetis serta draf opening, lalu memanggil penulis
Native untuk opening/produksi, sales draft/reservasi/post/cancel, dan konversi.
Tidak ada mutasi posted, HPP atau jurnal yang disisipkan SQL oleh fixture.
Prasyarat itu tidak diklaim dibuat melalui browser.

`cases.py` menyiapkan tujuh kasus Native: padanan dua arah/replay/ganti/hapus
dengan ledger nyata tetap persis; FIFO dua lot non-PO 10,01 dan 20,02 dengan
reservasi, perpindahan4PCS bernilai60,06; tujuan beda model/ukuran tanpa padanan
dan konversi balik manual memakai lot sumber terbaru30,03; perubahan reservasi,
tujuan dan SALE_RESERVE→SALE menolak review lama tanpa efek; reversal grup
ditolak bila satu hasil dipakai draft, lalu bisa setelah cancel sah; sumber
campuran opening+PO; serta regresi aksesori Native satu-lot yang sudah ada.

`runner.py` memakai strict runner Native yang sudah ada terhadap pemasangan
aktual, lalu membuat satu committed use witness untuk membuktikan inverse DDL
menolak sebelum mengubah katalog/data. Koneksi wajib loopback54322 dan database
`cp6_rollback`. **Integrator masih harus membungkusnya dengan admission exact
source, install+preuse inverse, seluruh22 grup katalog, data, sekuens, roles,
advisor, full backup restore dan semua lima package gates.**

`races.py` menyiapkan tiga callback untuk alat dua sesi yang sudah ada:
UUID sama setelah commit, UUID berbeda menjadi stale setelah commit, serta
rollback holder membiarkan writer kedua melanjutkan. Runner Native di atas
belum memanggil callbacks itu; belum ada kredit tiga race aktual.

`auth_waits.py` menambah enam calon uji dua sesi: perubahan hak setelah pair
advisory, replay pair, baris SKU; demosi actor setelah baris SKU; perubahan hak
konversi setelah kunci FG; dan replay konversi setelah row-lock idempotency.
Penantian harus terlihat lewat `pg_blocking_pids`. Pembanding seluruh katalog,
baris dan sekuens diambil setelah perubahan Auth lalu harus sama setelah
penolakan. Pengguna baru memakai role ADMIN yang sudah ada, bukan OWNER;
perubahan Auth merupakan fixture administratif eksplisit, bukan klaim UI admin.
Callback belum dijalankan dan tidak otomatis ikut runner Native.

Batas yang tetap terbuka: Auth/PostgREST dan browser komputer/390px untuk modul
baru; cost/recost lintas semua bagian; pemulihan bongkaran yang nilainya besar
relatif child pertama; pemasangan+recovery lengkap dan penerimaan independen.
Regresi aksesori lama tidak menutup batas `expected_returns` yang dilekatkan
pada child pertama. Jangan mengubah label kasus atau menghitungnya sebagai
bukti aksesori grup penuh. Formal CP7 tetap, `production_go=false`.

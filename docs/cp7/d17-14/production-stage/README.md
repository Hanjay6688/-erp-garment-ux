# Tahap produksi B di atas SQL dasar beku

23 Oktober2026 WIB. Menjawab permintaan A di b91a60b19494e0ed161a8fb4d53b9fc8b12cb951,
KOORDINASI/OW15. **WIP tahap; belum lulus rantai A dan belum siap digabung sebagai produk.**

Sembilan berkas cp7-src yang sebelumnya berubah sudah kembali tepat ke byte a255e48f. Gerbang
cp7_payment_source_owning_install.sources() == SOURCE.json/product_sources semula menolak
CP7_FULL_PREDECESSOR_SQL_SOURCE_CHANGED; sesudah pemindahan sekarang lulus tanpa mengubah pin,
pemasang/bundle, SOURCE.json, atau oracle beku. first-frozen-source-failure.json menyimpan penolakan pertama.

Perubahan fitur tidak dibuang:18 badan fungsi dipindahkan ke scripts/cp7_production_stage/sql,
dengan18 invers, MANIFEST.json berisi hash sebelum/sesudah dan asal tiap fungsi. OW14b menambah3 kolom privat
nullable dan4 constraint bernama; tanpa backfill, endpoint/role baru, grant baru, DML Native atau pengiriman pesan.
Status OW16 tetap modul terpisah cp7_ow16_status_install.py; A memasangnya di atas tahap ini.

Antarmuka untuk komposisi A: apply(cur) mengembalikan state sebelum pemasangan; verify(cur,state)
memeriksa badan serta owner/ACL/security/config/type persis; admit_catalog(before,after,state)
hanya menerima18 badan/3 kolom/4 constraint/1 perubahan presisi privat di22 kelompok. rollback_preuse(cur,state) memulihkan DDL
sebelum dan menghapus kolom; A WAJIB memegang transaksi/envelope lock serta penjaga setelah-pakai global sebelum
pemanggilan. Pilihan minimum eksplisit sendiri juga menahan rollback sebelum DDL pertama.
Tidak ada koneksi, commit, pemasangan bawaan, penjadwalan, atau pemasangan Enteng dari modul ini.

Probe B sekarang memasang dasar beku, lalu menjalankan apply/admission/rollback/22 kelompok identik/reapply
sebagai gerbang wajib sebelum menghitung kasus. Bagian ini belum dinyatakan lulus Native sampai Original dibaca.
Baseline38 memakai4 fungsi yang tersedia; netting84 memakai7; staged15/history20/status16 memakai11;
WA/OW14b113 memakai seluruh18. Tidak menambah angka kasus karena preflight. Kualifikasi lama yang lulus
adalah jalur bundle terisolasi; tidak membuktikan rantai A ini sudah tersambung.

Lokal pada tata letak baru: SQL target/netting5 kelompok lulus (168 pembanding independen,129 target v1 identik,
12 netting v1 identik), SQL bahan6 kelompok lulus. TypeScript/CSS dan44 uji klien sebelumnya lulus;
perubahan pemindahan ini hanya SQL/alat uji. Uji server tata letak baru masih perlu dijalankan.
Rencana satu lingkungan uji menjalankan enam suite berurutan:113+16+20+38+15+84=286, pemulihan wajib sebelum
suite berikutnya. Menghindari unduhan lingkungan yang sama enam kali; runtime, batas per unit dan kontrol lama tetap.

A belum diberi klaim sambungan rantai ujungnya selesai. Rantai OW15 tetap dikomposisi A; proof286 terisolasi
juga tidak akan menggantikan P21 rantai, pemeriksaan gabungan, atau audit Fable/Sol. OW10 sumber permintaan/WIP
relevan tetap terbuka; pemindahan tahap tidak menutup kebutuhan bisnis itu. Status induk tetap5/16.


Perbaikan sesudah Original460ada9:108/113 lulus;1 Native dan4 layar belum lulus, pemulihan/advisor lulus.
Kegagalan pertama di ow14b/460ada9-first-native113.json, Original lengkap privat. NULL pilihan lama sempat
menghilangkan satu tanda delegasi; sekarang kondisi pilihan eksplisit memakai Boolean pasti. Pencatat permintaan
klien juga menolak referensi Native enam desimal sebelum RPC; Master Native memang menerima6 desimal. Validator
klien/server dan pin privat kini mempertahankan6 angka tanpa pembulatan (manual_point18,4 →20,6; metadata ini
masuk admisi/invers). Pesan minimum terpilih mempertahankan angkanya. Form tanpa pilihan eksplisit mempertahankan
penjelasan Master lama ditambah keterangan referensi/aturan aktif; assertion browser lama tidak dihapus.
Lokal8 kelompok SQL bahan/pemulihan plus5 kelompok kernel lulus; pemeriksaan server tahap baru masih menunggu.


## Sesudah Original4eaf6bc

Paket OW14b113 sekarang PASS pada4eaf6bce69ddcb52b89c8d24446ce5466825ac78/run39865429494/job120126319220.
ID kasus tepat; Native61, dua pengguna34, HTTP7, browser11; pemulihan/advisor dan22-group preuse gate PASS.
Receipt di ../ow14b/4eaf6bc-native113-pass.json. Pengatur gabungan masih INCOMPLETE: paket kedua0 kasus
karena cp6_t3_package_run.run menghapus cp6_rollback di finally, juga saat PASS. Lima suite173 belum jalan.
Kegagalan pertama di4eaf6bc-first-clone-boundary.json.

Sequence berikutnya mereklon AB primer yang tetap utuh dengan skrip clone milik writerca7f095 sebelum
masing-masing suite2–6. Writer HEAD/byte skrip dikunci; koneksi hanya allowlist loopback disposable.
Penolakan clone menghentikan sequence sebelum suite berikutnya. Original T3_*.json dipindah ke folder
suite-NN-probe setelah setiap proses; file Native utama tetap bernama unik. Upload complete-json harus
rekursif agar Original paket pertama tidak hilang/ditimpa. Tidak mengubah runner/bundle/pemasang A.
Tiga uji pengatur urutan mereproduksi penghapusan database, kegagalan clone dan writer berubah.

# Padanan SKU dan Ganti Merek/SKU — owner 29 Oktober 2026

Pegangan: Reliable data adalah dewa. Keuangan termasuk laporan, stok dan HPP
adalah raja. VENI. VIDI. VICI. ERP.

Delta ini dibangun di atas `cp7_vendor_receivable.composition`, dengan pemasang
`cp7_sku_pair_conversion.composition`. Berkas predecessor yang sudah dibekukan
tetap utuh. Enam definisi yang berubah dinyatakan di `native_delta.py`; semuanya
diturunkan dengan substitusi tepat satu kali. Tidak ada RPC publik tambahan.

Successor recovery yang masih PREPARED menambah dua tangkapan Native tepat di
`recovery_delta.py`, tanpa mengganti keenam derivasi semula. Penjaga baca saja
memeriksa biaya pemulihan SKU yang dikelola sebelum dokumen/audit pertama, dan
hak mutakhir diperiksa lagi sebelum replay UUID. Perhitungan Native tetap utuh;
profil material/graph yang belum dapat dipastikan meminta peninjauan sebelum
efek. Batas bagian pertama tetap berlaku, tanpa pembagian recovery satu grup.
Ruang bukti, profil yang diterima, lock dan batas kualifikasi dinyatakan di
`scripts/current-sku-managed-recovery-preflight/README.md`; ini belum merupakan
hasil actual Native27 atau penerimaan default.

Padanan disimpan satu kali per grup SKU bersama, sehingga tidak perlu diulang
untuk setiap ukuran. Endpoint diurutkan, satu SKU hanya punya satu pasangan,
dan perubahan yang bersamaan memakai kunci transaksi yang sama. Pembacaan
berlaku dari dua sisi. Mengganti pasangan membersihkan pasangan lama kedua
endpoint. Request/actor/payload tersimpan, termasuk penghapusan. Aksi ini hanya
memerlukan hak kelola master dan tidak memanggil penulis stok atau keuangan.

Form konversi memilih produk/ukuran aktual dan gudang. Seluruh tujuan aktif
tersedia; padanan diurutkan sebagai saran, tanpa otomatis mengganti ukuran.
Pembaca mengambil fisik, reservasi dan tersedia dari gerakan resmi. Pemilihan
asal/tujuan/gudang membaca ulang server. Jumlah mengubah tampilan sebelum/sesudah;
pratinjau sebelum simpan juga memeriksa tanggal dan lot yang memenuhi syarat.

Satu request mengalokasikan FIFO menurut `produced_at,id` dan memanggil alur
Native satu-lot yang sudah ada untuk setiap bagian, dalam transaksi database
yang sama. Setiap bagian menyimpan HPP sumber dan jejak lotnya sendiri.
Algoritme HPP/COGS penjualan tidak diganti dan tidak ada rata-rata FG baru.
Nilai pratinjau memakai pembulatan sen masing-masing jurnal Native. Harga/HPP
yang tidak diketahui tetap menolak; harga nol yang sah tidak diubah menjadi
nilai buatan. Biaya aksesori/bongkaran tetap melalui dokumen Native yang ada;
daftar bongkaran induk melekat pada bagian pertama, tidak diulang per lot.

Fingerprint mencakup kedua produk, gudang, setiap lot/HPP dan seluruh baris
mutasi dalam lingkup, termasuk perubahan `SALE_RESERVE` menjadi `SALE` tanpa
perubahan jumlah. Simpan memeriksa ulang fingerprint di bawah kunci stok/HPP
Native. Penolakan memuat ulang angka dan mematikan pratinjau lama; operator
meninjau ulang sebelum request baru. Klik ganda dan respons hilang memakai
envelope persisten dengan UUID yang sama.

Riwayat menandai bagian-bagian dari satu konversi dan jumlah totalnya.
Pembatalan dari bagian mana pun membalik seluruh grup secara atomik. Pemakaian
turunan aktif di satu bagian menolak semuanya; pembalik Native menjaga jejak
dan reservasi. Panggilan langsung untuk membalik satu bagian grup ditolak.
Konversi balik manual kemudian tetap transaksi baru yang memakai biaya sumber
pada waktu itu; tidak ada pencocokan pasangan batch atau pembalik otomatis.

Lima tabel baru bersifat privat, RLS menyala dengan kebijakan menolak. Fungsi
privat dimiliki postgres dengan search_path kosong, tanpa akses browser/service
role. Konteks manual dibatasi pada backend+transaksi+request+alokasi tepat,
disimpan di tabel privat. Tidak ada bendera GUC umum untuk melewati penjaga.
Preuse inverse memulihkan definisi dan seluruh 22 grup katalog secara tepat.
Sesudah ada pemakaian, inverse DDL menolak dan memerlukan backup restore penuh.

## Pemeriksaan dan batas bukti

`test_delta.py` memeriksa keenam substitusi dan kontrol negatif katalog.
`tests/cp7/families/sku-pair-conversion.test.ts` menjalankan SQL baru sungguhan
di runtime lokal, dengan posting Native/Auth/jurnal/workspace sebagai **doubles
yang dinyatakan**. Itu bukan bukti Native/Auth/PostgREST/HPP atau pemasangan
rantai sebenarnya. `src/ConnectedSkuConversion.dom.test.tsx` memakai komponen
dan recovery hook sebenarnya dengan respons RPC contoh.

Sebelum penerimaan, integrator masih harus membuktikan pemasangan+preuse
inverse, Native multi-lot PO/non-PO dan sen, recost/aksesori/reversal setelah
pemakaian, Auth/dua pengguna/race, browser komputer/390px, serta backup restore
seluruh katalog/data/sekuens/roles. `production_go=false`,
`independent_acceptance=false`; formal CP7 tidak dinaikkan oleh delta ini.

Integrasi bersama satu baris `SAVE_PAIR` di domain `SKU` dalam
`src/productionRecovery.ts` sudah diterapkan dengan alokasi integrator dan
commit terpisah `[bersama]`; empat RPC UI tidak berubah signature.
Pilih pemasang baru hanya setelah kualifikasi actual, tanpa membuat pembungkus
melingkar terhadap pemasang beku.

Perbaikan counter-review: trigger RI parent di ERP hanya diizinkan untuk tiga
FK yang dideklarasikan dan enam metadata trigger yang tepat; trigger ERP lain
tetap ditolak. Query katalog22 asli direproduksi terhadap katalog PostgreSQL
lokal dan kontrol rogue trigger nyata menolak. Perintah NULL/kosong/tidak
dikenal tidak dapat jatuh ke reversal. Hak diperiksa ulang setelah penantian
advisory, idempotency, serta baris SKU/produk sebelum replay atau DML. Uji lokal
injeksi perubahan hak setelah batas idempotency bukan klaim race dua sesi.
Pencarian/paging tujuan dan padanan menghapus pilihan belum tersimpan yang
tidak terlihat; penulis tidak dapat memakai ID tersembunyi.

Actual Native805 pertama menolak hapus padanan karena validator bersama
memaknai daftar required sebagai key bernilai non-null. Layar memang mengirim
`target_group_id:null` sebagai perintah hapus. Target kini tetap wajib hadir
secara eksplisit, tetapi boleh JSON null; tujuan lain tetap melalui parser UUID
Native. Key hilang tidak menjadi penghapusan diam-diam. Uji lokal memakai body
validator key dan UUID Native asli, sehingga tidak lagi bergantung pada double
lama yang hanya mengecek keberadaan key. Penolakan lama direproduksi sebelum
patch; hapus dari kedua sisi, replay dan malformed/stale zero-effect diuji.
Ini belum merupakan Native805 successor PASS; Original disimpan integrator.

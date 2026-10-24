# Produk pembanding — pembaca kandidat

24 Oktober2026. Komponen opt-in, bukan penutupan OW11 atau pemilihan forecast.

Facade baru `erp_cp7_read_product_analog_candidates_v1(p_request uuid,
p_target text,p_offset integer,p_limit integer,p_access text)` hanya membaca
snapshot Native DONE milik aktor. UUID adalah UUID permintaan bounded analysis
lama yang sama; pembaca tidak membuat permintaan analisis atau konfigurasi baru.

Server memeriksa READ COMMITTED, akses Native saat ini, epoch yang sama dengan
page set, kepemilikan request/run, K2 tujuh hari, metode bounded, clock/query/hash
snapshot serta producer Native yang masih sama. Setelah membaca, akses diperiksa
lagi. Hasil membawa actor/request/run/query/reference/identity/epoch/producer dan
context histori yang sama. K3 menyimpan reference job sehingga pembacaan sesudah
cleanup tetap mungkin. Jangan menyusun snapshot lama dari sumber sekarang.

`source_state=CAPTURED_NOT_CHECKED` selalu eksplisit. Ini bukan cek kesegaran;
cek sumber existing terpisah. Perubahan stok sekarang tidak mengubah kandidat
pada snapshot lama. Konfirmasi nantinya harus memeriksa sumber lengkap dan menolak
sumber berubah. Kandidat tetap selected/reviewed/forecast_applied=false, termasuk
ketika ada mean nol yang sah dari hari AVAILABLE. UNKNOWN bukan nol.

Delta satu schema privat berisi kernel lama yang tidak berubah dan satu pembaca,
ditambah satu facade authenticated: 2 fungsi privat/1 facade/0 tabel/0 penggantian
fungsi lama. Tidak ada grants schema privat, service/anon/alert, atau CREATE public
yang tersisa. Pemasang mewajibkan checker predecessor dua belas tahap yang ketat;
baris dependency Native disimpan dan diperiksa. Tidak ada koneksi/commit/default
installer. Invers read-only memakai RESTRICT dan menolak caller luar sebelum DDL.
A tetap mengomposisikan ke pemasang/full-chain/after-use/global census.

Native4 dideklarasikan terpisah di `ANALOG_READER_CONTRACT.json`: source/catalog22/
ACL/invers/caller luar; DONE binding/replay/K3/sumber berubah tetap captured;
aktor lain dengan epoch sendiri/epoch salah/nonaktif/RUNNING/K2; 11 produk asli
lewat import BB Native pada10 ukuran fisik, satu pembanding AVAILABLE nol ukuran
sama serta9 ukuran lain dikeluarkan meskipun merek sama. Delta dibuat/dilepas di
setiap kasus rollback di atas parent12; bukan diam-diam tahap bawaan ke13.

Belum ada bukti runtime Native4 saat dokumen ini ditulis. Auth/PostgREST/browser,
mid-call revocation/concurrency, konfirmasi/CAS/UUID/scale/alasan, satu mesin target,
model aktif dan paket auditor tetap terbuka. Native4 tidak dijumlahkan dengan
Native3 lama untuk mengarang penerimaan penuh. Parent tetap5/16.

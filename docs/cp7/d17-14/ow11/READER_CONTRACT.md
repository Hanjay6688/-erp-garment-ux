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
aktor lain dengan epoch sendiri/epoch salah/nonaktif/RUNNING/K2; 11 produk baru
lewat import BB Native pada10 ukuran fisik tetap UNKNOWN pada hari sebelumnya.
Sepuluh pembanding historis Native SYNTHETIC terpisah dinyatakan jelas: satu
AVAILABLE nol ukuran sama serta9 ukuran lain dikeluarkan meskipun merek sama.
Tidak ada kredit semua histori berasal dari impor publik. Delta dibuat/dilepas di
setiap kasus rollback di atas parent12; bukan diam-diam tahap bawaan ke13.

Native4 pertama0a1deb1f INCOMPLETE2/4; katalog dan DONE/K3/advisory lulus.
Kesalahan fixture epoch/riwayat impor diperbaiki tanpa mengubah reader SQL atau
memajukan UNKNOWN menjadi tersedia; rerun d2680d34/run40050851768 actual4/4 lulus dan semua5 gate paket lulus.
Workflow masih merah karena penutup probe membaca nilai balik None sebagai dict;
penutup dibetulkan dan kasus gagal pertamanya tetap disimpan. Native4 tidak
diulang hanya demi badge hijau; Browser2 menguji penutup yang sudah benar. Auth/PostgREST/browser,
mid-call revocation/concurrency, konfirmasi/CAS/UUID/scale/alasan, satu mesin target,
model aktif dan paket auditor tetap terbuka. Native4 tidak dijumlahkan dengan
Native3 lama untuk mengarang penerimaan penuh. Parent tetap5/16.


## Layar baca kandidat

`nativeProductAnalog.ts` memakai facade bernama tepat dari SQL dan parser ketat:
aktor/request/run/target/query/epoch/identity/reference sampai mikrodetik, hash
histori/producer/profil dan angka total lintas halaman. Ukuran berbeda, target
sendiri, duplikat, hari UNKNOWN/STOCKOUT yang dipromosikan, mean null dan flag
selected/reviewed/applied ditolak. Mean desimal tetap string; nol AVAILABLE sah.

`NativeProductAnalogPanel` membaca50 kandidat per permintaan, membersihkan halaman
lama saat membaca berikutnya dan mengabaikan balasan sesudah target/tab/aktor
berganti. Akses ditolak membersihkan induk dan kandidat. Pencarian target memakai
seluruh label hasil yang telah diverifikasi, termasuk target tanpa rekomendasi;
pilihan layar maksimal20, bukan pembatas sumber perhitungan. Permintaan UUID
analisis tetap, pemilihan kandidat belum disediakan dan target belum diubah.

Uji lokal terbaru:38/4 untuk parser, page binding, respons terlambat,403, induk
dan pencarian lintas halaman; kumpulan terkait255 uji/16 berkas lulus sebelum push.
TS dan CSS diperiksa. Browser2/Auth nyata dideklarasikan terpisah; belum ada
kredit lulus saat persiapan. Registry A tetap tidak diubah; proposal satu pasangan
baru setelah17 terdahulu, total18 persis, graph367 runtime/313RPC lulus dengan
proposal tersebut. Gate asli masih terbuka sampai A menerapkannya.


## Browser2 terbukti pada624e2786

Run40083891933/job120842786283 PASS2/2, Original lengkap diperiksa.
Komputer1440px:2.000 produk/202.000 movement,100 kandidat unik lintas halaman,
reload UUID sama dan K2 menolak/bersihkan. HP390px: AVAILABLE nol sah,
9 ukuran lain dikeluarkan, anon/aktor lain/epoch salah/nonaktif ditolak.
Tidak ada overflow halaman atau error console. Auth0/0/0/0 kembali persis,
CP6/public/ACL pulih, advisor dan semua5 gate paket true. Receipt
`624e278-browser2-pass.json` mempertahankan kegagalan a104345 sebelumnya.
Pencarian exact SKU diutamakan; semua hasil tersedia lewat halaman20 pilihan.
256 uji klien terkait/16 berkas,3 helper Node,TS dan64 kepemilikan CSS lulus.
Ini membuktikan pembaca advisory. Konfirmasi dan pemakaian forecast masih terpisah.

# Konfirmasi pembanding — metadata berversi

24 Oktober2026. Stage opt-in ini menyimpan keputusan pengguna; belum memasukkan
pilihan tersebut ke forecast. OW11 tetap terbuka dan induk5/16.

`erp_cp7_get_product_analog_choices_v1(p_targets text[])` membaca revisi terbaru
untuk maksimal200 identitas root:ukuran. Hasil memiliki aktor/epoch dan state
UNREVIEWED, CONFIRMED_ASSUMPTION atau CLEARED. Akses Native diperiksa lagi setelah
baca. Hak tulis memakai Native `master.product.manage`, tidak menambah grant ERP.

`erp_cp7_save_product_analog_choice_v1(p_payload jsonb,p_request uuid)` menerima
kontrak `cp7.product-analog-choice-command.v1`. Payload tepat berisi action,
target_key, source_key, source_request, source_hash, access_epoch, scale_factor,
reason, reviewed, expected_revision dan contract_version. Skala string positif
wajib eksplisit; tidak ada nilai bawaan. reviewed wajib true, alasan1–1000 huruf.

CONFIRM mengambil envelope Native terlebih dahulu, kemudian lock aktor+UUID dan
target. Akses diperiksa ulang sesudah tiap tunggu. Receipt lama hanya dikembalikan
setelah hak tulis sekarang lolos dan payload byte-semantik JSON sama. UUID berubah
payload ditolak. Revisi dibandingkan dengan nilai terakhir; pilihan baru wajib
berasal dari DONE milik aktor, epoch/clock/query/identity/producer yang benar,
belum K2, serta sumber penuh yang masih sama. Dua pemeriksaan fingerprint sumber
tetap berada di dalam writer dan batas8s; tidak diberi pengecualian performa.

Produk sendiri dan ukuran fisik berbeda ditolak. Minimum histori diambil dari
profil target yang dipilih. UNKNOWN/STOCKOUT tidak menjadi nol AVAILABLE. Bukti
menyimpan produk target/pembanding, profil/revisi, snapshot/query/hash, numerator
PCS asli dari hari AVAILABLE, jumlah hari, skala, aktor dan waktu rekam server.
Mean yang dibulatkan tidak dikalikan untuk membuat total baru.

CLEAR menambah revisi pembatalan dengan alasan; source_request/source_hash/
source_key/scale_factor harus null. Pembatalan tidak memerlukan snapshot lama
masih tersimpan sehingga pilihan basi bisa dicabut. Kedua tabel menolak UPDATE/
DELETE. source_at memilih revisi terakhir yang sudah diketahui pada waktunya;
tidak ada effective_at yang bisa dimundurkan oleh client.

Delta berisi4 fungsi privat,2 facade authenticated,2 tabel RLS tertutup,
0 penggantian fungsi lama. Pemasang wajib checker predecessor ketat yang mencakup
pembaca advisory. Invers preuse memeriksa22 grup, memakai RESTRICT, dan memulihkan
DDL parsial jika ada dependency luar. Setelah ada receipt/pilihan, invers menolak;
A mengomposisikan backup/restore after-use dan pemasangan bawaan.

Native6 dideklarasikan terpisah. Bukti lokal syntax/tipe bukan bukti Native.
Auth HTTP, race lock/revocation, consumer source hashes, satu mesin forecast,
layar persetujuan, integrasi A dan pemeriksaan independen masih terbuka.

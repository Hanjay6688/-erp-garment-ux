# CP6 AT — pemeriksaan masa berlaku hasil WIP

Status saat paket ini dibuat: kandidat perbaikan, belum ada kelulusan AT yang diklaim. CP6 tetap HOLD; CP7 belum dibuka. Production tidak berubah. Hasil penulis tidak sama dengan penerimaan tinjauan independen.

## Landasan dan temuan

Prinsip ERP tetap: “Reliable data adalah dewa”; “Keuangan—termasuk laporan—stok, dan HPP adalah raja”. Draft memakai koreksi terakhir, posting menyimpan sejarah, pengulangan request tidak menambah efek, dan pembatalan menggunakan transaksi balik yang terhubung.

AS dibekukan pada `8a170ce9931523f6fabe02ac5c24154d3333236b`. Pemeriksaan independen pada `5eb9de3ca59e3b86621ce1c158277e462d57efb4`, run `35802923757`, mengulang 500 kasus asli (488 berhasil, 12 HOLD historis), 34 kasus AS berhasil, serta 12 pemeriksaan kebijakan kalender terpisah. Arsip mentah: artifact `10726429481`, SHA-256 `285d5b0cb44af56947f16696270eb9126fb3138b3ab98c5cecabf987a8574e7c`.

Satu keluarga temuan produk terbukti dalam empat kasus WIP: pemilihan otomatis menolak versi yang sebenarnya tunggal pada tanggal produksi, dan ID eksplisit versi yang sudah berakhir masih bisa membuat lot baru di luar masa berlakunya. Masing-masing direproduksi dengan zona sesi UTC dan Pacific/Kiritimati, melalui RPC publik sebagai authenticated biasa. Kesamaan SKU lintas merek, aturan model/ukuran, pengulangan request, serta transaksi balik ikut diamati.

Dua dugaan BS dalam arsip audit **tidak diterima sebagai bug produk**. Stok fisik awal boleh berasal dari identitas historis yang sudah berakhir atau tidak aktif pada tampilan master. Bila seluruh penanda identitas masih ambigu, penolakan adalah perilaku yang benar. Arsip audit dan oraclenya tetap utuh; empat kontrol BS baru mendokumentasikan penafsiran yang benar tanpa mengubah kasus lama.

## Perubahan terbatas

AT mengubah satu fungsi privat: `erp.complete_initial_import_wip_v1(jsonb)`. Selain syarat AS yang sudah ada, kandidat harus belum berakhir pada awal hari produksi Asia/Jakarta. Bersama batas awal yang sudah ada, ini berarti masa berlaku harus beririsan dengan hari produksi. Batas akhir bersifat eksklusif. Dua versi yang berganti di tengah hari tetap ambigu tanpa ID; ID eksplisit memakai waktu fisik dalam bagian hari yang sah.

Resolver stok awal, validator BS AS, tampilan/UI, keuangan, ACL, owner, serta seluruh oracle historis tetap byte-identik. Fungsi pemilihan tetap mengunci kandidat dengan `FOR SHARE`. Dua urutan perubahan status master dan pengesahan output diperiksa dengan sesi database terpisah, termasuk commit dan abort, serta pengamatan `pg_blocking_pids`.

Migration dibuat melalui Supabase CLI 2.116.0 dan menghasilkan `20260923005153_erp_v2_6_20at_cp6_wip_temporal_identity.sql`. Migration/rollback, builder, definisi, dan predecessor terikat SHA-256. Pemasangan hanya pada clone disposable, dengan admission tertutup dan seluruh sesi lain selesai. Dua siklus pemasangan/pemulihan harus mengembalikan data, riwayat migrasi, owner, ACL, 648 fungsi dan 7148 objek persis. Rollback setelah pemakaian harus ditolak, termasuk setelah transaksi balik bisnis.

## Pemeriksaan yang diwajibkan

Workflow `CP6 AT Qualification` menjalankan:

1. Delapan kontrol pada AS asli: empat temuan WIP tetap teramati, empat kontrol berhasil. Tidak ada fungsi yang ditambal untuk tes.
2. Pemulihan AT dua siklus pada AS yang sudah berisi data, pemeriksaan advisor sebelum/sesudah, 174 kasus asli termasuk sesi bersamaan, serta empat jadwal master/output baru.
3. Clone baru: 326 kasus asli sisanya, 34 kasus AS, 12 pemeriksaan kalender, dan 16 kasus temporal AT (delapan WIP, empat BS historis, empat batas hari).
4. Clone baru: Auth/password nyata, browser dan PostgREST publik, penolakan anonim/identitas ambigu tanpa efek, pemilihan merek, HPP/stok, kehilangan balasan setelah commit, reload dan pengulangan payload/UUID persis, serta transaksi balik. Sepuluh observasi diwajibkan. Respons produk tidak diganti dengan mock.
5. Snapshot primary AN tetap sama, seluruh clone/REST/Auth sementara dihapus. Semua bukti mentah disimpan walaupun gagal.

Hasil 12 kasus kalender historis tetap `DATE_POLICY_REVIEW_REQUIRED`; pemeriksaan kebijakan baru tidak mengubah labelnya. Source guard lama tidak dilonggarkan. Workflow lama yang khusus menerima paket AC bukan bukti penerimaan AT dan kegagalannya harus tetap dilaporkan.

## Reproduksi dan penyerahan berikutnya

Jalankan workflow pada commit penulis yang tepat. `scripts/cp6_at_trial.py source()` mengikat SHA/tree dan tepat 15 file baru terhadap audit `5eb9de3`; paket lama dan tiga file audit asli tidak berubah. Pengujian native memerlukan runtime disposable yang dibangun workflow, bukan database hosted.

Setelah hasil tersedia, simpan commit/tree, SHA migration/rollback, hasil lengkap, riwayat kandidat gagal, dan penjelasan dua dugaan BS yang dikoreksi. Bekukan penulis sebelum menyerahkan kepada peninjau independen. Peninjau berikutnya diminta memeriksa bukti, menjalankan ulang kasus terkait, dan mencari kondisi yang belum tercakup dengan bahasa Indonesia yang tenang dan jelas. Tidak ada perpindahan ke production, pembukaan CP7, atau perubahan status CP6 tanpa penerimaan terpisah.

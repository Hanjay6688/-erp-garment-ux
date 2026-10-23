# OW13a — analisis awal otomatis

Kontrak B sebelum caller,23 Oktober2026 WIB. Ini **analisis awal sekali per actor
Owner/Admin**, bukan perubahan jadwal analisis rutin atau sakelar WA. Sesudah analisis
awal ada, data/aturan berubah, kegagalan maupun kedaluwarsa tidak membuat loop
permintaan baru. Analisis baru tetap melalui jalur manual atau jadwal rutin yang
sudah ada. Semua hasil adalah snapshot; status memperlihatkan sumber berubah.

Minimum teknis untuk analisis operasional: sumber global COMPLETE, setidaknya
satu produk aktif dan setidaknya satu produk aktif dengan profil terkini yang
sudah diperiksa serta waktu proses, jarak pemeriksaan dan satu cara cadangan
yang diketahui. Tidak mengisi angka kebijakan, mengharuskan penjualan pertama,
atau mengubah unknown menjadi0. Semua produk dalam sumber tetap masuk analisis;
produk lain yang belum lengkap tetap menghasilkan alasan ketidaklengkapan.
Kalender tidak menjadi syarat awal karena pemeriksaannya sendiri memerlukan
snapshot analisis. Kelayakan produksi, status produksi, kapasitas dan kelipatan
tetap dijaga mesin yang sama; kesiapan awal tidak mengizinkan posting potong.

Tidak ada RPC publik baru. Tambahan tertutup pada RPC request analisis bertahap:
`p_query={initial_auto:'STATUS'|'ENSURE'}`, **p_request=null**. STATUS hanya baca;
ENSURE bersifat kondisional/idempoten dengan satu intent server per actor dan
satu UUID server yang tersimpan atomik dengan job/capture mark. Payload campuran
atau UUID klien pada mode ini ditolak. Payload analisis lama persis jalur lama.
Jawaban `cp7.initial-analysis.v1` mengikat actor, query, waktu, kesiapan dan job
milik actor itu. Job memakai capture operasional DEFERRED, tidak membaca laporan
atau mengaktifkan keuangan. Status job/header/pages tetap kontrak lama.

Pemicu server menumpang tick analisis yang sudah ada, sebelum syarat pengaturan
WA; tidak membuat cron/provider/penerima/pesan baru. Actor berasal dari profil
yang sudah diperiksa dan wajib masih Owner/Admin dengan empat hak operasi sekarang.
Claims dipulihkan pada setiap jalan, termasuk error dan pembatalan. Hak dibaca
ulang sesudah mutex/capture dan sebelum jawaban. Satu mutex pabrik dan job actor yang
sedang berjalan menahan duplikasi; unique actor menjaga tepat satu analisis awal.
Pekerjaan dilanjutkan runner bertahap yang sama meskipun browser ditutup.
Jika actor sudah mempunyai job bertahap dengan periode, akses dan sumber yang
sama serta belum kedaluwarsa, intent memakai job/UUID tersebut, termasuk job
yang dimulai manual. Tidak membuat salinan analisis itu.
Setelah intent awal ada, tick hanya memeriksa hak dan UUID/status job; tidak
mengambil ulang seluruh sumber tiap menit. STATUS dari layar tetap membaca
sumber terkini untuk memberi tanda snapshot sudah berubah.

UI menunjukkan kekurangan dan membuka pengisian target yang sudah ada; hasil
awal dibuka dengan UUID server yang sama tanpa memulai request lain. Jalur Master
produk yang berada pada host milik A dikoordinasikan lewat callback; jangan
mengubah App/halaman stok milik A. Hak401/403 membatalkan fakta dan respons lama.

Tahap privat baru dipasang A setelah tahap produksi dan pilihan target; bila
bridge keuangan dipakai, pasang bridge lebih dahulu. Dua badan diganti tepat:
`cp7_analysis_stage.request(jsonb,uuid)` dan `cp7_alert_native.analysis_tick()`.
Objek baru hanya skema privat, satu tabel intent append-only beserta constraint,
policy/trigger dan empat fungsi. Tidak ada grant Native baru. A memegang
transaksi/envelope lock/admission22 dan penjaga setelah-pakai global. Rollback
lokal menolak intent yang sudah dibuat sebelum DDL pertama. Uji lokal bukan
Native/Auth/dua sesi/browser/pasang-pulih rantai A; OW13a tetap OPEN sampai bukti
tersebut dan tombol pengisian di host A lengkap.

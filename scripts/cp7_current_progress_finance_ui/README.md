# D17-18 — host A untuk progres dan keuangan (baru disiapkan)

VENI. VIDI. VICI. ERP. Reliable data adalah dewa.
Keuangan termasuk laporan, stok, dan HPP adalah raja.

Host opsional milik A, integrator, di atas backend persiapan `5c30a4ea079afad5139b8fa08dbbad6d8af31227`.
Sumber B sebanyak 91 berkas dipertahankan persis pada
`d6fad0d2303bfe39531afdbe62f6faec95f79046`, tercatat di `B_SOURCE.json`.
Tidak ada perubahan default aplikasi, pemasang, sumber B, rumus uang/HPP, atau batas database.

`Panel.tsx` memakai extension `renderFinance` yang sudah disediakan B. Panel kebutuhan,
pencarian, pembukaan ulang UUID, penyimpanan pilihan, dan pemulihannya tetap milik B.
Build mengarahkan pemanggil analog tunggal pada panel kebutuhan ke wrapper persiapan
pilihan B yang persis. Wrapper itu tetap memakai panel analog asal; tidak ada siklus redirect.
AuthProvider/AuthGate tetap asli. Klien A mempertahankan routing finance STAGED terdahulu.

Pembaca A memakai RPC read-only `erp_cp7_get_frozen_analysis_progress_v1` dengan UUID
tersimpan. Ia memeriksa identitas lengkap, waktu sumber hingga mikrodetik, hash sumber,
kontrak, dan urutan waktu pengamatan server. Pembacaan yang bersamaan berbagi satu
permintaan; hasil selesai tidak di-cache, sehingga pembacaan berikutnya memeriksa ACL terkini.
Tidak ada request baru, step, transaksi, atau perhitungan angka di pembaca progres.

Waktu berasal dari server; durasi selesai membeku. Produksi dan keuangan mempunyai jumlah
serta persentase masing-masing. Total yang belum diketahui tetap tidak diketahui, dan tidak
ada persentase keseluruhan buatan. Saat produksi berjalan, host membaca setiap lima detik;
setelah produksi selesai, panel keuangan asli meneruskan pembacaan sampai selesai. Fokus
dan muat ulang keuangan tetap melalui pembaca yang sama. Kegagalan pembacaan menghentikan
polling dan menyediakan pemeriksaan ulang UUID yang sama. Respons setelah unmount ditolak.

Identitas menggunakan nilai kolom eksplisit, bukan urutan key JSON. Pencabutan izin lokal
langsung menyembunyikan uang; penolakan server diteruskan ke callback retire milik B.
Angka hanya ditampilkan panel keuangan asli setelah status, run, sumber, dan readiness cocok.
UNKNOWN tidak diubah menjadi nol, dan hasil parsial tidak disebut lengkap.

## Pembaruan setelah bukti B tentang buka ulang

Dua berkas kode, satu tes yang berubah, dan satu tes buka ulang baru diambil
persis dari d6fad0d2; 91 berkas B seluruhnya diperiksa terhadap Git. Pengamat
persiapan sekarang terus membaca pekerjaan asal setelah buka ulang, tanpa
membuat atau memajukan pekerjaan otomatis. Kemajuan nyata mengatur batas
pengamatan; perubahan lock saja tidak dianggap kemajuan. Tutup panel,
kelanjutan eksplisit, atau pergantian identitas menghentikan pengamat lama.

190 tes dalam 17 berkas, TypeScript, serta build79modul lulus pada salinan A.
Angka ini menggantikan jumlah lokal179 terdahulu, bukan ditambahkan padanya.
B mempunyai Original browser e94e8037 PASS6 dengan identity/RPC terkendali;
A memeriksa kedua Original termasuk kegagalan9ff dan51pin masing-masing.
Ini belum bukti Auth/database atau keuangan pada host gabungan baru.
Pemeriksaan React mencakup identitas efek, satu pembacaan berurutan,
pembersihan pengamat, dan penolakan respons terlambat; tidak menambah pustaka.

## Bukti lokal host sebelumnya dan batas yang tetap

- TypeScript `--noEmit` lulus; 179 uji di 16 berkas lulus dalam 10,04 detik.
- Tujuh uji host memakai komponen keuangan dan parser asli, dengan RPC/Auth terkendali.
  Termasuk StrictMode, satu pembacaan bersama, RUNNING→READY, buka ulang UUID,
  respons hilang, pencabutan izin, serta respons terlambat sesudah panel ditutup.
- Build Vite mencakup 79 modul sumber; `BUILD_SOURCE.json` mengunci byte yang dikompilasi.
  `LOCAL_BUILD.json` membuktikan kedua redirect. Ini belum bukti modul disajikan browser.
- Kegagalan awal tetap tersimpan di `LOCAL_STARTUP_FAILURE.json` dan `LOCAL_FAILURES.json`.
- Tidak ada kredit Auth/HTTP asli, database, konkurensi server, cron, pemulihan database,
  skala pabrik, atau penerimaan gabungan dari bukti lokal ini.

Native5 progres, Native6 komposisi pilihan, dan pembuktian finansial/produksi skala besar
masih menjadi prasyarat runtime. Status antre, observasi pekerja, deteksi macet dan pemulihan
harus dibuktikan lewat backend; host tidak mengarangnya dari ketiadaan lock atau lama menunggu.
Semua scope belum ditutup: `production_go=false`, `independent_acceptance=false`.

Jalankan dari root repo:

```sh
node_modules/.bin/tsc --noEmit -p scripts/cp7_current_progress_finance_ui/tsconfig.json
node_modules/.bin/vitest run --config scripts/cp7_current_progress_finance_ui/vitest.config.mjs
python scripts/cp7_current_progress_finance_ui/source_guard.py
```

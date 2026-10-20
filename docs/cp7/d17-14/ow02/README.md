# OW-02 — proses server, kandidat penulis

Dasar: `0bde7153dbf06238bde89999454dd98c33cf81c5`. Kandidat audit `55c885d1` tetap beku.
Status **BELUM SELESAI** sampai kualifikasi Native dan browser berikut lulus pada commit ini.
Tidak ada jadwal dipasang di hosted, pengiriman WA, atau perubahan data Enteng.

## Kontrak dan implementasi

Penjalan privat yang sudah ada mengambil satu unit pekerjaan tertua dari empat keluarga:
analisis bertahap, laporan bertahap, kumpulan kondisi pengingat, dan analisis tunggal WAITING.
Ia memakai pelaku yang meminta pekerjaan, izin terkini dan langkah asli keluarga itu.
Hasil tetap memakai UUID, identitas sumber dan hash yang sama. Izin dicabut membuat pekerjaan gagal
tanpa keluaran parsial; identitas pemanggil penjalan dikembalikan. Pekerjaan terkunci dilewati.
Jadwal, batas 8 detik per perintah, facade publik, dan hak tulis Native tidak ditambah.
Tiga indeks parsial hanya memuat pekerjaan belum selesai.

Layar laporan dapat membaca hasil permintaan yang sama. Layar pengingat sekarang mempunyai tombol
**Muat hasil pengingat tersimpan**, yang hanya membaca workspace dan hasil selesai; tidak mengklaim
atau mengirim pesan. Keterangan menjelaskan penjalan server yang aktif tetap bekerja saat halaman ditutup.
Pemasangan operasional tetap pekerjaan CP7C yang ditahan.

## Expected yang dideklarasikan sebelum CI

Manifest `docs/cp7/k4/K4_RUNNER.json`: **30 kasus** (13 Native, 11 balapan, 2 HTTP, 4 browser).
Seluruh 17 kasus lama dipertahankan. Tambahan: enam Native, lima balapan dan dua browser desktop/HP.

- Laporan: selesai tanpa langkah halaman; dokumen dan seluruh bagian diverifikasi hash; satu publikasi;
  angka keuangan tetap disertakan dan rekonsiliasi bisnis tetap sama.
- Pengingat: hasil server sama dengan seluruh kondisi, total dan hash hasil langkah halaman pada sumber yang sama;
  nol klaim/kirim. Langkah pertama membuat permintaan, sisanya dikerjakan server.
- Analisis tunggal: satu permintaan, satu run, satu dokumen utuh; hasil segmen sama dengan pembaca aslinya.
- Empat keluarga mendapat giliran; izin dicabut sebelum/di tengah langkah menolak tanpa efek parsial;
  kunci halaman/server tidak menggandakan unit; identitas sesi pulih; penjalan tidak terbuka di Data API.
- Browser sungguhan menutup tiga tab saat laporan/pengingat/analisis sedang berjalan, menunggu server selesai,
  lalu membuka ulang hasil yang sama tanpa permintaan/pekerjaan baru, di desktop dan HP.

## Bukti lokal — bukan kualifikasi Native

- `local-dispatch-check.mjs` / `local-dispatch-green.jsonl`: 15 pemeriksaan lulus pada
  **PGlite 0.5.10 / PostgreSQL 18.6 WASM**, memakai SQL dispatcher asli dan kontrak pekerjaan sintetis.
  Termasuk batas perintah, giliran empat keluarga, rollback perubahan izin, pemulihan JWT dan hak privat.
  Tidak membuktikan konkurensi, pg_cron, fixture Native atau PostgreSQL Supabase yang dipin.
- Reproduksi: `PGLITE_MODULE=/path/to/pglite/dist/index.js node docs/cp7/d17-14/ow02/local-dispatch-check.mjs`.
  PGlite adalah dependensi alat lokal di luar aplikasi, bukan dependensi produk.
- Dua berkas uji DOM laporan/pengingat: **10/10 lulus**; TypeScript, pemeriksaan sintaks Python/JavaScript,
  keterjangkauan SQL, kepemilikan sumber dan pemulihan perintah lulus lokal.
- Pemeriksaan ulang pembacaan saat membuka halaman: pemulihan analisis tunggal mempunyai prioritas terhadap
  pemulihan analisis bertahap; tidak ditambahkan loop penulis lain saat halaman dibuka.

CI pada cabang penulis harus menguji instalasi asli, seluruh kasus dan pemulihan. Kegagalan pertama disimpan.
Counter-review internal penulis tidak menggantikan audit independen Fable/Sol.
`production_go:false`.

## Counter-review dan kegagalan lokal pertama

Pada kandidat lokal `5e4554247b5e0a8c6d71d6687d6e77e6c79989b2`, pemeriksa UI menemukan
fakta laporan/pengingat lama tetap terlihat setelah pembacaan ditolak atau tidak pasti.
Empat kasus baru dideklarasikan dan dijalankan sebelum perbaikan: **4 gagal, 10 lulus**
(`local-stale-ui-first-failure.log`). Setelah state fakta dikosongkan di jalur gagal yang sama,
seluruh **14/14 lulus** (`local-stale-ui-fixed.log`). UUID perintah yang belum pasti tetap disimpan;
uji kehilangan balasan dan pemulihannya tetap lulus. Ini bukti DOM sintetis, bukan pencabutan izin Native.

Pemeriksa juga menemukan pemantau permintaan browser dipasang sesudah membuka ulang halaman.
Kini dipasang sebelum navigasi, sehingga pekerjaan ganda saat mount juga menggagalkan kasus.
Laporan dibuka ulang harus cocok nomor publikasi, run, identitas, hash, dan ringkasan utuh;
analisis tunggal harus cocok run yang ditampilkan, hash semantik hasil dan jumlah seluruh target.
Kasus mobile K4 lama hanya berhenti memantau; dua kasus OTHER yang baru benar-benar menutup
tiga tab masing-masing pada desktop dan HP. Batas kasus lama tetap dicatat, tidak dilabeli ulang.

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

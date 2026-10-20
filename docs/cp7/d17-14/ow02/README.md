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

Manifest `docs/cp7/k4/K4_RUNNER.json`: **32 kasus** (13 Native, 13 balapan, 2 HTTP, 4 browser).
Seluruh 17 kasus lama dipertahankan. Tambahan: enam Native, tujuh balapan dan dua browser desktop/HP.

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

Tambahan setelah penilaian awal pemeriksa SQL: dua kasus batas waktu memakai kunci tabel keluaran
asli dan batas lebih ketat 2 detik. Expected: percobaan 1/2 RUNNING tanpa unit/keluaran tambahan,
percobaan 3 FAILED dengan kode tepat 57014, sesudahnya tidak dicoba selamanya.
Semua balapan tambahan juga memeriksa ketiga pengaturan JWT pemanggil pada koneksi yang sama,
sebelum commit/pemulihan harness. Deklarasi 32 kasus dicocokkan dengan modul sebelum push.

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

Putaran koreksi kedua memakai enam kasus tambahan: recovery dari tab lain dan balasan lama yang
datang terlambat; workspace pengingat RUNNING/FAILED/tidak ada setelah DONE; pindah publikasi B
sesudah menyiapkan revisi A. **6 gagal, 14 lulus** pada kode `155d9dc7`
(`local-shared-recovery-first-failure.log`). Perbaikan membatalkan generasi baca saat recovery,
membersihkan fakta yang tidak lagi DONE, serta membatalkan pilihan revisi dan konfirmasi saat membuka
publikasi lain. Seluruh **20/20 lulus** (`local-shared-recovery-fixed.log`).
Satu percobaan perbaikan membersihkan halaman DONE terlalu luas saat workspace normal dimuat ulang,
sehingga dua prasyarat uji lama tidak terpenuhi. Percobaan gagal itu dipertahankan di
`local-refresh-attempt-first-failure.log`; pembersihan kini sesuai perubahan keadaan/hak.
Expected negatif dan hasil akhir uji tidak dilonggarkan.

## CI pertama — 333005ed

Run `39411967722`, job `118591662201`: **28 PASS, 4 INCOMPLETE dari 32**.
Seluruh empat browser dan dua kasus timeout lulus; laporan, pengingat dan analisis
benar-benar selesai sesudah tiga tab ditutup pada desktop/HP. Ini belum PASS penuh.
Semua baris hasil dan traceback awal disimpan dalam `CI_39411967722_FIRST_FAILURE.json`.

- Pembanding kondisi pengingat keliru menuntut `policy_timing.checked_at` sama
  antara dua permintaan yang berbeda. Kontrak `SNAPSHOT_VALUE_POLICY_AT_READ`
  memang menghitung waktu itu dari `read_at` setiap halaman. Perbaikan alat uji
  menuntut seluruh baris tersegel persis sama, dan seluruh field publik persis
  sama kecuali satu clock tersebut, yang **wajib cocok persis dengan read_at**.
  Nilai, hash, rujukan, policy, kelayakan dan semua field waktu lain tetap diuji.
- Tiga skenario pencabutan izin mencoba menonaktifkan satu-satunya OWNER.
  Native menolaknya dengan `LAST_ACTIVE_OWNER_PROTECTED` sebelum penjalan diuji.
  Fixture kini menyiapkan OWNER kedua melalui helper yang sudah ada, sebelum
  sumber ditangkap. Actor peminta, pencabutan, tuntutan FAILED dan rollback
  keluaran tetap sama. Trigger dan pengaman OWNER tidak diubah.

Diagnosis sumber dikonfirmasi pemeriksa internal Sol Max sebelum perbaikan.
Perubahan ini hanya alat uji; hasil Native perbaikannya masih menunggu CI baru.

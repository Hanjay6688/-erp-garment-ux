# OW-01 — bukti pengembangan, belum penerimaan

Dasar sebelum perbaikan: `5fd5d38ef43618e48f9aa36208f46ad2290404c0` (produk sama dengan kandidat beku `55c885d1`).
Penulis Astra/Codex; audit independen menunggu Fable/Sol. Tidak ada pengiriman WA nyata atau perubahan hosted.

- Uji layar baru D17-14 gagal pada kode lama: dua kasus menolak tujuh jenis yang belum dikenal
  (`local-ui-old.log`). Kode baru lulus seluruh 16 kasus di berkas yang sama (`local-ui-new.log`),
  termasuk mempertahankan Rp9.007.199.254.740.993,01 dan membedakan nilai belum diketahui dari nol.
- `local-sql-old.jsonl`: assertion tujuh jenis bawaan gagal pada SQL lama.
- `local-sql-new.jsonl`: SQL modul lengkap berhasil dipasang dan 24 pemeriksaan adaptor lulus
  dalam **PGlite 0.5.10 / PostgreSQL 18.6 WASM**, dengan sumber kewajiban sintetis.
  Ini **bukan** PostgreSQL/Supabase yang dipin di CI, bukan pemeriksaan transaksi Native, balapan,
  Vault, jaringan atau pengiriman sungguhan. Tidak dihitung sebagai kelulusan kualifikasi.
- Reproduksi adaptor: instal `@electric-sql/pglite@0.5.10` pada direktori pengembangan terpisah;
  jalankan `PGLITE_MODULE=/path/to/pglite/dist/index.js node docs/cp7/d17-14/ow01/local-adapter-check.mjs`
  (tambahkan `--old` untuk penolakan kode lama). Tidak ada dependensi baru di aplikasi.
- TypeScript, kepemilikan sumber/akses/CSS, pemulihan perintah, dan keterjangkauan seluruh SQL lulus lokal.

## Pengujian Native yang ditambahkan

`scripts/cp7_wa_obligation_cases.py` menambahkan tujuh kasus ke suite WA: saldo awal AR/AP;
gaji cicilan/lunas/balik; alokasi kredit aksesori yang belum dibayar; invoice dan penerimaan laundry
dibayar/dibalik; laundry awal belum ditagih; pencabutan hak sempit; privasi ringkasan semua domain.
Sumber bisnis dibuat dengan writer Native yang sudah diterima, bukan pengganti pembaca atau perubahan tabel bisnis.
Dua kasus browser nyata yang sudah ada diperluas agar pilihan tujuh domain terbukti terlihat, aktif secara bawaan,
dan tersimpan di desktop/HP. Jumlah manifest sekarang 65 (48 Native, 6 balapan, 4 HTTP, 7 browser).

CI WA dipicu oleh push produk pada cabang writer baru yang dideklarasikan di workflow; isi job,
identitas pemasang, oracle dan gate tetap. Ini pekerjaan penulis, bukan dispatch audit pada kandidat beku.
Hasil CI harus dicatat sebelum OW-01 ditandai selesai. Dengan OW-16 dari D17-15, ada 16 butir pekerjaan.

## CI pertama dan koreksinya — 20 Oktober

Run 39406686784 / attempt 1 pada 39212271: **59/65 PASS, 6 INCOMPLETE**.
Native 42/48, balapan 6/6, HTTP 4/4, browser 7/7; stack smoke juga PASS.
Data dan skema dipulihkan; enam kegagalan tidak dihapus atau disebut hijau.
Rincian asli ada di ci-39406686784-first-failures.json.

- Cacat produk: ringkasan kewajiban ACTIVE tanpa suffix DATA_REVIEW menggabungkan SQL NULL.
  Akibatnya pesan laundry kosong dan guard dispatch menolak. ELSE kosong ditambahkan;
  guard dispatch tetap. Reproduksi lokal gagal pada 39212271 dan lulus setelah koreksi.
- Penyiapan uji sumber: RESET ROLE tidak membatalkan SESSION AUTHORIZATION authenticated.
  Pembacaan pembanding kini memakai helper admin harness, dengan identitas JWT yang sama.
- Oracle gaji: ringkasan benar menjumlahkan gaji fixture lain juga. Kasus saldo 400 kini
  memilih mode rinci agar angka payroll itu sendiri dapat diperiksa; saldo Native tetap diuji persis.
- Dua oracle antrian menghitung jenis yang sengaja tidak dipilih di pengaturan. Hitungan kini
  tepat mencakup semua jenis yang dipilih, dan jenis nonaktif wajib KIND_OFF tanpa dispatch.
  Oracle hak baca owner diperluas dengan tujuh jenis baru, tetap perbandingan himpunan persis.
- Pada batas panjang pesan, fallback hitungan seluruh jenis dipakai sebelum memotong rincian uang,
  agar satu jenis tidak hilang hanya karena pesan memuat banyak domain.

CI berikutnya pada `0bde7153`, run **39409032583**, attempt 1: **65/65 PASS**
(48 Native, 6 balapan, 4 HTTP, 7 browser). Stack smoke PASS; restore/advisor/boundary gate PASS.
Kasus dan observed disimpan di `CI_39409032583.json`, bukan hanya warna job.
Hash SQL terpasang `fc5256d9abf563bd4069124c4cadae0ac088b687b3af8438324c5eb3edf7ee39`
dicocokkan dengan komposisi sumber `0bde7153` dari objek Git dan berbeda dari SQL `39212271`.
Label legacy `product_ref=39212271` hanya memindai src/supabase, tidak scripts/cp7-src;
limit metadata itu dicatat, bukan dianggap seluruh run menguji produk lama.
Bukti ini milik penulis, bukan penerimaan auditor, dan tidak menguji perubahan OW-02 sesudahnya.
Jalur tujuh domain baru teruji; **OW-01 belum ditandai selesai penuh** karena batas keputusan
kebutuhan aksesori rencana masih terbuka sebagaimana bagian akhir dokumen ini.

## Perubahan perilaku yang disengaja

`DATA_REVIEW` diteruskan sebagai perlu diperiksa. Tidak dibuat jatuh tempo baru atau saldo nol.
Sisa nilai disalin persis dari sumber Native, dan sumber laundry yang belum final tidak dijumlahkan lagi
sebagai invoice. Ringkas tidak menyebut pihak; rinci mengikuti label sumber yang diizinkan.
Format rupiah kini mempertahankan sen dan angka besar, di layar maupun teks WA; pembulatan tampilan lama
tidak dijadikan oracle untuk membuang presisi.

Kebutuhan aksesori dari rencana (D17-10 beda 2) masih menunggu keputusan yang tercatat di handoff.
`production_go:false`.

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

## Pengujian Native yang ditambahkan, belum dijalankan

`scripts/cp7_wa_obligation_cases.py` menambahkan tujuh kasus ke suite WA: saldo awal AR/AP;
gaji cicilan/lunas/balik; alokasi kredit aksesori yang belum dibayar; invoice dan penerimaan laundry
dibayar/dibalik; laundry awal belum ditagih; pencabutan hak sempit; privasi ringkasan semua domain.
Sumber bisnis dibuat dengan writer Native yang sudah diterima, bukan pengganti pembaca atau perubahan tabel bisnis.
Dua kasus browser nyata yang sudah ada diperluas agar pilihan tujuh domain terbukti terlihat, aktif secara bawaan,
dan tersimpan di desktop/HP. Jumlah manifest sekarang 65 (48 Native, 6 balapan, 4 HTTP, 7 browser).

CI WA dipicu oleh push produk pada cabang writer baru yang dideklarasikan di workflow; isi job,
identitas pemasang, oracle dan gate tetap. Ini pekerjaan penulis, bukan dispatch audit pada kandidat beku.
Hasil CI harus dicatat sebelum OW-01 ditandai selesai. Sisa 14 pekerjaan tetap terbuka.

## Perubahan perilaku yang disengaja

`DATA_REVIEW` diteruskan sebagai perlu diperiksa. Tidak dibuat jatuh tempo baru atau saldo nol.
Sisa nilai disalin persis dari sumber Native, dan sumber laundry yang belum final tidak dijumlahkan lagi
sebagai invoice. Ringkas tidak menyebut pihak; rinci mengikuti label sumber yang diizinkan.
Format rupiah kini mempertahankan sen dan angka besar, di layar maupun teks WA; pembulatan tampilan lama
tidak dijadikan oracle untuk membuang presisi.

Kebutuhan aksesori dari rencana (D17-10 beda 2) masih menunggu keputusan yang tercatat di handoff.
`production_go:false`.

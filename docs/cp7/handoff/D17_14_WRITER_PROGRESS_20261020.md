# Writer D17-14 — checkpoint 20 Oktober 2026

Penulis: Astra/Codex. Cabang `astra/d17-14-20261020`, mulai dari
`5fd5d38ef43618e48f9aa36208f46ad2290404c0`. Otorisasi owner: **“gas”**, 20 Oktober 2026,
sesudah serah-terima D17-14. Kandidat auditor `55c885d1` tetap beku.

Lingkup kini semua **16 butir** `OPEN_WORK_D17_14_20261020.md` (15 D17-14 + OW-16 D17-15).
Belum ada butir yang dinyatakan selesai penuh.
Penulis tidak memberikan penerimaan audit independen. Pemeriksa berikutnya Fable atau Sol.
`production_go:false`; tidak ada perubahan hosted, main, Cloudflare, Drive, atau pengiriman WA nyata.

## OW-01 — seluruh sumber pengingat ke WA (sedang dikerjakan)

- Akar celah: collector WA hanya memanggil `receivable_source` dan `payable_source`.
  Pengingat kewajiban juga membaca `other_obligation_source`, yang sudah mencakup saldo awal,
  payroll, retur aksesori mandor, invoice/penerimaan laundry dan laundry awal belum ditagih.
- Sambungkan pembaca Native yang sama, tanpa menghitung ulang sisa uang. Satu pembacaan bersama
  per collect/recheck, bukan tujuh pemindaian yang sama. Kunci sumber asli menjadi identitas episode.
- Tambahkan tujuh jenis yang dapat dibaca/disaring terpisah. Hak baca mengikuti
  `condition_domain_access`, termasuk hak payroll/laundry/aksesori/HPP, bukan hak AP saja.
- `ACTIVE` diteruskan sesuai keadaan sumber. `DATA_REVIEW` juga diteruskan sebagai **perlu diperiksa**,
  dengan sebab dan nilai KNOWN/UNKNOWN tetap dibedakan. Tanggal kosong tidak disebut terlambat;
  penerimaan laundry belum final tidak dijumlahkan lagi sebagai utang invoice.
- Ringkas menyembunyikan identitas pihak; rincian dapat menampilkan label sumber. Pemilik tujuan tetap
  owner yang menyimpan sambungan; pengingat pribadi staf tidak dibaca (D17-3 dan desain yang berlaku).
- Pengiriman memakai outbox/status/deduplikasi dan cek ulang yang sama. Uji memakai server palsu saja.
- Kebutuhan aksesori dari rencana tetap pertanyaan terpisah yang belum dijawab pada D17-10;
  tidak ditandai selesai atau disamarkan sebagai pengingat minimum aksesori.

## Verifikasi

Uji layar baru gagal pada kode lama dan lulus pada perubahan; seluruh 16 kasus layar WA lulus.
24 pemeriksaan adaptor SQL dengan sumber sintetis lulus di PGlite 18 (LOCAL_PGLITE18_DEV),
bukan Native PostgreSQL/Supabase CI. PostgreSQL biasa tidak dapat dijalankan di lingkungan ini
karena hanya UID root tersedia; tidak ada pengujian hosted sebagai pengganti.
TypeScript dan pemeriksaan kepemilikan sumber/akses/CSS, pemulihan perintah dan keterjangkauan SQL lulus.
Bukti dan batasnya: `docs/cp7/d17-14/ow01/README.md`. Tujuh kasus Native baru dan perluasan browser
desktop/HP telah dideklarasikan. CI pertama 39406686784 di 39212271 selesai 59/65 PASS:
enam INCOMPLETE disimpan; tujuh browser PASS. Perbaikan pada `0bde7153` lulus run39409032583:
65/65 PASS (48 Native/6 balapan/4 HTTP/7 browser). Hash SQL terpasang cocok komposisi0b,
meskipun metadata legacy product_ref masih392 karena tidak memindai scripts/cp7-src.
Receipt per kasus: `docs/cp7/d17-14/ow01/CI_39409032583.json`. Batas kebutuhan aksesori rencana tetap terbuka.

## Berikutnya

OW-02 penjalan server (analisis, laporan bisnis, pengingat), OW-03 isian kelipatan produksi;
lalu urutan daftar kerja, termasuk OW-16 sebelum paket OW-15. Kegagalan CP6 lama tetap dicatat sebagai gagal beserta
pembanding dan cakupan penggantinya. Paket auditor baru menunggu tiga butir Kelompok 1 selesai.

## Tambahan scope Claude yang diambil 20 Oktober

Owner meminta lanjut dan tambahkan scope baru Claude. Dokumen owner/daftar kerja disalin persis dari
claude/new-session-deapao 41b5b0e (rantai 19293bf, 684bb4a, 41b5b0e); hanya dua dokumen itu yang diambil.
OW-16: setelah potongan selesai, tampil otomatis status total pcs berdasarkan riwayat seluruh pabrik,
berkelompok jenis bahan + pola + rentang ukuran pola (jumbo/kecil). Tidak ke WA atau Pengingat.
Lebar rentang dan minimum riwayat belum boleh dikarang. Perubahan produk belum dimulai.

OW-02: dispatcher privat sudah di-commit, memakai satu tick K4 yang sama untuk analisis
bertahap, laporan, set pengingat dan analisis tunggal. Pemeriksaan lokal sintetis 15/15, bukan Native.
Manifest 32 kasus lengkap (13 Native, 13 balapan, 2 HTTP, 4 browser), dicocokkan sebelum push;
dua browser baru benar-benar menutup tab laporan/pengingat/analisis lalu membuka hasil yang sama.
Counter-review menemukan cacat fakta basi/recovery/seri revisi; 4 gagal awal→14/14, lalu 6 gagal→20/20 DOM.
Log semua percobaan dipertahankan. Hasil Native/browser CI OW-02 belum ada saat catatan ini dibuat.

## Pemeriksa internal dan lanjutannya

Owner menegaskan satu integrator dan empat pembantu GPT-6.1 Sol Max, tanpa anak agen.
Penilaian awal dikunci pada satu kandidat, baru kemudian UI↔SQL dan uang/HPP↔stok/koreksi saling counter.
Ini review internal writer, bukan audit eksternal. Temuan, bukti dan batasnya:
`docs/cp7/d17-14/INTERNAL_COUNTER_REVIEW_20261020.md`.
Rancangan reproduksi uang/HPP berikutnya ada di `NEXT_MONEY_WORK_SOURCE_REVIEW.md`; belum dianggap runtime terbukti.

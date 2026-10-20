# Writer D17-14 — checkpoint 20 Oktober 2026

Penulis: Astra/Codex. Cabang `astra/d17-14-20261020`, mulai dari
`5fd5d38ef43618e48f9aa36208f46ad2290404c0`. Otorisasi owner: **“gas”**, 20 Oktober 2026,
sesudah serah-terima D17-14. Kandidat auditor `55c885d1` tetap beku.

Lingkup tetap semua 15 butir `OPEN_WORK_D17_14_20261020.md`. Belum ada butir yang dinyatakan selesai.
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
desktop/HP telah dideklarasikan; CI belum dijalankan, OW-01 belum selesai.

## Berikutnya

OW-02 penjalan server (analisis, laporan bisnis, pengingat), OW-03 isian kelipatan produksi;
lalu urutan OW-04..15 dari daftar kerja. Kegagalan CP6 lama tetap dicatat sebagai gagal beserta
pembanding dan cakupan penggantinya. Paket auditor baru menunggu tiga butir Kelompok 1 selesai.

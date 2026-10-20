# Writer D17-14 — checkpoint 20 Oktober 2026

Penulis: Astra/Codex. Cabang `astra/d17-14-20261020`, mulai dari
`5fd5d38ef43618e48f9aa36208f46ad2290404c0`. Otorisasi owner: **“gas”**, 20 Oktober 2026,
sesudah serah-terima D17-14. Kandidat auditor `55c885d1` tetap beku.

Lingkup kini semua **16 butir** `OPEN_WORK_D17_14_20261020.md` (15 D17-14 + OW-16 D17-15).
OW-02 dan OW-03 sudah selesai terbukti pada cakupan kebutuhan aplikasi masing-masing; pemasangan operasional CP7C tetap HOLD.
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
- D17-14 sudah mencakup kebutuhan aksesori dari rencana; tidak perlu meminta
  izin forwarding lagi. Pemeriksaan live `ACCESSORY_NEED` dan sambungan WA
  belum tersedia, jadi butir ini tetap terbuka sebagai implementasi, tidak
  disamarkan sebagai pengingat minimum aksesori. Ini mengoreksi disposisi
  penulis sebelumnya yang masih menyebut menunggu jawaban D17-10.

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

Sesudah checkpoint OW-02/03, lanjut jalur retur lunas, koreksi mandor dan pembayaran supplier
sesuai urutan daftar kerja, termasuk OW-16 sebelum paket OW-15. Kegagalan CP6 lama tetap dicatat sebagai gagal beserta
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

## Checkpoint lanjutan writer — OW-02/03

Base publikasi sebelumnya333005ed. WA run39411967784/job118591662633 lulus65/65;
receipt per kasus disimpan di `docs/cp7/d17-14/ow01/CI_39411967784.json`.
K4 run39411967722/job118591662201 **28/32 PASS,4 INCOMPLETE**. Empat browser
lulus, tetapi tiga fixture pencabutan OWNER terakhir dan satu pembanding clock
pengingat perlu diperbaiki. Kegagalan awal dan diagnosis disimpan; perbaikan
alat uji tidak mengubah penjalan atau pengaman produk. Pada kandidat2ad56e14,
run39420750772/job118620792070 kemudian **32/32 PASS**, restore/advisor PASS.
Receipt lengkap `docs/cp7/d17-14/ow02/CI_39420750772.json`; kegagalan awal tetap ada.

OW-03 kini mempunyai isian kelipatan PCS per produk/ukuran, tanpa default,
legacy UUID tetap, helper exact bersama untuk direct/staged, dan teks laporan
bersyarat.40/40 profil dan17/17 layar bertahap lulus lokal;165 pemeriksaan
PGlite sintetis terdokumentasi. Tiga kegagalan401 sebelum perbaikan disimpan.
Native profile38 dan staged15 beserta browserdesktop/HP dideklarasikan,
termasuk gap93->96+3, M5->95+2, bahan186 tetap, clearUNKNOWN, arsip utuh,
publikasi langsung/bertahap dan izin dicabut. F04 kandidat2ad56e14 kemudian
**38/38 PASS**, run39420750723/job118620792464, restore/advisor PASS; receipt
`docs/cp7/d17-14/ow03/CI_39420750723.json`. Analisis penuh kemudian **154/154 PASS**,
run39420750819/job118620792620; staged **15/15 PASS** pada
run39420750772/job118620792697. Receipt masing-masing ada di folder ow03.
Penguatan perjalanan yang mengetik12 di layar lalu memakai profil yang sama
untuk analisis96+3 disiapkan sebagai follow-up alat uji; belum runtime.
WA pada2ad juga **65/65 PASS**,
run39420750724/job118620792072; receipt `docs/cp7/d17-14/ow01/CI_39420750724.json`.
Rincian/reproduksi: `docs/cp7/d17-14/ow03/README.md`.

Paket auditor baru tetap menunggu syarat Kelompok1, termasuk pemeriksaan live
dan sambungan WA kebutuhan aksesori rencana. Semua OW uang/stok/HPP berikutnya tetap
daftar terbuka; belum ada klaim feature_complete/audit_complete/production_go.

## Bukti terbaru — perjalanan layar878e0a9c

Run39423331714/job118629536646 pada head878e0a9c **154/154 PASS**.
Browser desktop/HP mengetik12, simpan dan baca kembali, lalu analisis memakai
ID/revisi profil yang sama untuk93→96+3. SQLsourcehash3c0364ce… cocok bundle
lokal. Produk byte-identik terhadap2ad; hanya dua alat browser berubah.
Receipt ow03/CI_39423331714.json. OW-03 kini selesai pada kontrak isian→analisis.

K6job118620792566 belum menguji produk: port54322 bentrok, lalu registry
menolak unduhan akibat batas data. Bukti awal disimpan, tidak diubah menjadi
PASS; GitHub menolak permintaan ulang selama workflow masih berjalan.
Skala5.000 masih berjalan pada saat pembaruan ini. Bukan bukti SLA1/2/3detik.

## OW-04 mulai dikerjakan — belum selesai

Keputusan penyelesaian retur sudah ada pada D17-14. Empat pembantu Sol Max
menelusuri satu sumber yang sama, lalu saling counter. Peta lengkap pembaca
piutang/status/detektor, lock, koreksi, akun, undo dan fixture disimpan di
`d17-14/ow04/SETTLEMENT_SOURCE_MAP.md`; semua hitungan di sana expected sumber,
bukan runtime kredit/refund baru. Native lama tidak boleh dilonggarkan hanya
dengan menghapus penolakan overpayment. Kredit/refund masih belum tersedia.

Satu cacat pendahuluan sudah ditulis perbaikannya: waktu penerimaan retur
baru tidak lagi diisi dari jam buka halaman. Uji baru merah1/10 sebelum
perbaikan; seluruh32 kasus tiga formulir lulus sesudahnya. Browser P11
desktop/HP diperkuat dengan waktu eksplisit dan pemeriksaan instant tersimpan;
CI64 kasus diaktifkan pada cabang writer. Bukti/batas: ow04/PHYSICAL_TIME.md.
Native/browser perbaikannya belum ada saat catatan ini dibuat.

## Skala selesai diukur dan CI perbaikan waktu fisik

Skala2ad run39420750772/job118620792724 attempt1 kemudian **5/5 PASS**
untuk pengukuran, restore/advisor PASS. Bukan SLA: klik sampai hasil5000
siap/halaman pertama terlihat79,40/88,22/105,27dtk untuk1/30/100hari,
dengan keuangan DEFERRED. Seluruh26halaman dibaca/diverifikasi; buka ulang
1,261–1,568dtk. Keuangan langsung5000 masih timeout8dtk, jadi OW-12 tetap
belum selesai. Data lengkap dan batas: ow03/SCALE_LIMITS_20261020.md.

Sesudah skala selesai, ulang **K6 saja** diterima GitHub pada kode2ad yang
sama; kegagalan lingkungan awal tetap tersimpan. Attempt2/job118654098080
kemudian **10/10 PASS**, restore/advisor PASS; receipt ow03/CI_39420750772_K6_RETRY.json.
Perbaikan waktu fisik retur sudah di-push pada4e3c98b3, tree29db6ac1;
CI P11run39430283909/job118653236629 kemudian **64/64 PASS**, restore/advisor
PASS. Sourcehash722aca08… cocok bundle; desktop/HP membuktikan input kosong,
waktu eksplisit WIB→UTC, review dibatalkan bila waktu berubah, dan readback
tetap tepat pada replay. Receipt ow04/CI_39430283909_PHYSICAL_TIME.json.
Ini perbaikan waktu fisik; settlement retur lunas tetap belum tersedia.

## Counter tanggal dan langkah berikutnya

Pemeriksaan lanjutan menemukan celah rancangan, sebelum menjadi kode produk:
seluruh kredit tidak boleh diberi tanggal retur bila dananya baru ada setelah
tanggal itu. Satu tanggal juga tidak cukup ketika sebagian pembayaran datang
lebih dahulu, atau tanggal buku sumber berbeda karena periode tutup/buka.
Writer dan dua pemeriksa membaca jurnal sumber; detail expected, anchor dan
batas bukti: ow04/TEMPORAL_COUNTER_20261020.md. Ini source-only, bukan hasil
runtime atau cacat kredit yang sudah terpasang. Perlu rancangan penerbitan
bertanggal dan Native oracle sebelum implementasi uang penuh.

OW-01 kebutuhan aksesori dari rencana masih ditelusuri: sumber saat ini
menandai tambahan pembelian UNKNOWN bila pemasangan/alokasi fisik belum
terbukti. D17-14 mengizinkan forwarding seluruh pengingat, termasuk keadaan
perlu diperiksa; tidak boleh mengganti UNKNOWN dengan kebutuhan bruto atau0.

## Checkpoint penutup — E01 dan reproduksi tanggal

Publikasi5ae9979c, tree4050507b, hanya memperkuat alat E01/workflow cabang
dan menyimpan bukti; produk tetap identik4e. Pencarian semua browser form
retur menemukan E01 masih mengandalkan default waktu. Writer menambah
isian operator dan assertion waktu/review/readback, tanpa mengubah seluruh
expected uang/stok/HPP, replay UUID atau pagar tab kedua. Source review
dan kontrol tengah malam lulus; tidak diklaim pernah ada kegagalan Native
E01 sebelum perubahan alat tersebut.

E01 kemudian **4/4 PASS sekali jalan**, run39433112026/job118663009654,
alat5ae/produk4e; restore/advisor PASS; sourcehasha7305cfc… cocok bundle.
Desktop/HP menghasilkan FG45/nilai675, kas200, AR175, pendapatan375,
COGS225 dan laba kotor150. Receipt ow04/CI_39433112026_E01.json.

Counter tanggal kini mempunyai reproducer Decimal terpisah5 contoh;
hasil/skrip diikat SHA256 pada TEMPORAL_COUNTER_MODEL_RECEIPT.json.
Ini model, bukan penulis kredit atau Native. Pemeriksa menemukan deskripsi
varian buka ulang900+100 tidak sama dengan model1000; penjelasan diperbaiki,
angka/expected model tetap, varian900+100 tetap source-only.

Scope WA kebutuhan aksesori, fingerprint/race dan expected UNKNOWN yang
harus dijaga sudah dipetakan di ow01/ACCESSORY_NEED_NEXT_SCOPE.md, belum
diimplementasikan. Semua butir daftar selain OW-02/03 tetap terbuka sesuai
statusnya; waktu fisik tidak menutup OW-04, dan pengukuran tidak menutup OW-12.
Handoff checkpoint terkini: HANDOFF_WRITER_5AE9979C_CHECKPOINT.md.

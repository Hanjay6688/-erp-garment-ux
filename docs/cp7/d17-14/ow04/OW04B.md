# OW-04b — lanjutan retur transaksi lunas (uji ulang 23 Okt 2026)

**Sudah beres tetapi masih menunggu uji otomatis di GitHub (CI): bagian 3 dan 4. Belum dikerjakan: bagian 1 dan 2.**
Retur kedua pada invoice lunas yang sudah punya saldo kredit, retur pada invoice yang pernah dibayar pakai saldo kredit,
serta Edit retur dan Benerin nota pada invoice yang ikut saldo kredit masih ditolak sistem. Bedanya sekarang: layar
menyebut alasannya dan langkah berikutnya, bukan lagi "Sumber penyelesaian retur belum dapat diperiksa".

Dasar: uji ulang `docs/cp7/d17-14/UJI_ULANG_CLAUDE.md` bagian OW-04, keputusan owner D17-14 butir 4 dan D17-16
("jangan dinyatakan selesai hanya karena ada tampilan atau fallback"). Cabang kerja `claude/d17-14-ow04b`.

## Yang sekarang berjalan

**Bagian 3 — layar menyebut alasan dan langkah berikutnya.** Penolakan lama tetap sama persis (syarat, urutan dan kodenya
tidak diubah), tetapi server sekarang ikut mengirim alasan rinci. Layar menerjemahkannya:

| Keadaan invoice | Yang tampil di layar |
|---|---|
| Sudah punya retur yang menjadi saldo kredit atau uang kembali, lalu ada retur kedua | "Retur ini belum bisa dicatat dan diselesaikan ... Alasannya: invoice ini sudah punya retur yang menjadi saldo kredit pelanggan atau uang kembali. Langkah berikutnya: ..." |
| Pernah dibayar memakai saldo kredit pelanggan | alasan "invoice ini pernah dibayar memakai saldo kredit pelanggan" |
| Pernah dibetulkan lewat Benerin nota (atau nota penggantinya) | alasan "pernah dibetulkan lewat Benerin nota" |
| Ada retur yang pernah dibetulkan lewat Edit retur | alasan "ada retur ... yang pernah dibetulkan lewat Edit retur" |
| Riwayat jurnal invoice tidak lengkap/tidak cocok | alasan itu, ditambah kode pemeriksaan untuk admin |
| Edit retur, Benerin nota atau pembayaran baru pada invoice yang ikut saldo kredit | kalimat pembukanya menyebut tindakan itu ("Retur pada invoice ini belum bisa diubah lewat Edit retur ...", "Pembayaran baru belum bisa dicatat ..."), lalu alasan dan langkahnya |

Langkah berikutnya yang tertulis jujur: fitur lanjutan ini belum ada; membatalkan pemakaian saldo, pembayaran atau
retur sebelumnya tidak membuka jalannya (riwayat kredit tetap disimpan); catat nomor invoice, barang dan nilainya, beri
tahu admin, dan jangan mencatatnya lewat menu lain. Penolakan lain saat memeriksa retur (invoice berubah, jumlah atau
nilai melebihi sisa, waktu salah, akun saldo kredit atau rekening tidak memenuhi syarat, HPP belum cocok, server belum
menjawab) juga punya kalimat sebab dan langkahnya. Bila alasan dari server tidak terbaca, layar tidak menebak: ia menulis
kode server untuk dilaporkan.

**Bagian 4 — uji yang diminta (sudah ditulis, menunggu CI):**

- Uang kembali dari rekening kosong ditolak dengan kalimat "Saldo <bank> (<kode>) menjadi minus -200.00 pada tanggal
  <tanggal> ... Kas/bank tidak boleh minus", dan tidak ada yang tercatat (retur, saldo kredit, jurnal, stok, permintaan).
  Sesudah modal masuk tepat 200 pada hari yang sama, permintaan yang sama berhasil dan saldo bank kembali 0,00.
- Modal 200 yang baru masuk sehari sesudah tanggal pengembalian tetap ditolak untuk tanggal itu (penjaga melihat tanggal).
- Pengembalian uang dari saldo kredit yang tersisa (bukan saat retur) juga ditolak tanpa efek bila bank kosong, lalu
  berhasil sesudah modal 80.
- Dua orang membatalkan pemakaian saldo yang sama pada saat bersamaan (dua sesi database sungguhan): satu berhasil, satu
  ditolak "sudah dibatalkan"; hanya satu pembatalan tercatat. Diuji untuk pemakaian ke invoice lain (dengan nomor
  permintaan berbeda dan sama) dan untuk pembatalan uang kembali saat retur.

## Temuan baru yang perlu Bos ketahui

Pembayaran biasa untuk sisa tagihan pada invoice yang sebagian dibayar pakai saldo kredit ditolak oleh sistem kredit
OW-04 (sudah begitu sejak OW-04, bukan perubahan baru). Contoh: invoice 500, dipakai saldo 80, sisa 420 tidak bisa
dibayar lewat menu pembayaran. Sekarang layar menyebut alasannya; perbaikannya belum dibuat dan dicatat sebagai pekerjaan
terbuka bersama bagian 1 dan 2. Satu kasus CI (`OW04B_PAYMENT_ON_CREDIT_PAID_INVOICE_NAMES_REASON`) membuktikan penolakan
dan alasannya.

## Yang sudah diuji di komputer penulis

- Tahap server: semua jangkar perubahan muncul tepat sekali pada teks fungsi yang dibangun ulang dari sumber repo; fungsi
  baru dan fungsi yang diubah terpasang dan dipanggil di PostgreSQL 16 sekali pakai dengan tabel tiruan
  (`scripts/cp7_credit_followups/local_check.py`, hasil LOCAL_PASS): pesan penolakan sama, alasan rinci benar, versi lama
  tanpa alasan rinci. Pemeriksa kompilasi dan bentrok nama: 4 fungsi, 0 galat. Ini bukan uji Native.
- Layar: `tsc -b` lulus; 221 uji terkait lulus (termasuk 31 uji pesan, 15 uji layar penyelesaian retur, 2 uji halaman
  penjualan: penolakan retur kedua dan uang kembali yang ditolak karena bank kurang).
- Semua `scripts/check-*.mjs` hasilnya sama dengan sebelum perubahan (tiga pemeriksa kepemilikan backend memang merah
  sejak awal). Sumber SQL dasar yang dibekukan tidak disentuh (`source_manifest()` lulus).

## Menunggu CI

CI adalah uji otomatis di GitHub yang menjalankan database sungguhan. Berkasnya `cp7-ow04b-native.yml` (CP7 OW04b ...
Native9 Race3): 9 kasus dan 3 kasus balapan dua sesi, dipasang di atas produk OW-05 yang sudah lulus, lalu dilepas dan
database CP6 dipulihkan. Belum pernah dijalankan; hasil pertama akan
dicatat apa adanya.

Kasus untuk bagian 3 memakai alur aplikasi yang sebenarnya, lalu memasang versi lama berdampingan untuk
membandingkan: retur pertama tetap dihitung sama seperti sebelumnya; retur kedua, retur pada invoice yang dibayar pakai
saldo, Edit retur, pembayaran sisa tagihan, dan Benerin nota (pada invoice asal saldo dan pada invoice yang dibayar pakai
saldo) ditolak dengan kode dan pesan yang sama seperti dulu, kini dengan alasan rinci, dan tidak ada yang tercatat.

## Yang BELUM dikerjakan

1. **Bagian 1** (retur kedua pada invoice lunas yang sudah punya saldo kredit; retur pada invoice yang pernah menerima
   kredit, dengan uang kembali atau saldo kredit). Sistem kredit OW-04 dibangun untuk satu kelompok kredit per invoice.
   Membuka retur kedua berarti mengajarkan banyak kelompok kredit pada satu invoice ke semua bagian yang memeriksa uang:
   perhitungan retur, pencatatan, pemeriksa akhir, pemakaian/pembatalan saldo, pembatalan retur dan pembayaran, koreksi
   pembayaran, dan pemeriksa laporan. Masing-masing sekarang sengaja menolak keadaan itu supaya uang tidak dihitung dua
   kali. Mengangkat penolakan tanpa membangun semua itu sekaligus bisa membuat saldo kredit atau piutang salah, jadi belum
   dikerjakan.
2. **Bagian 2** (Edit retur dan Benerin nota pada invoice yang ikut saldo kredit): sama, butuh jalur pembalikan yang
   membawa saldo kredit ikut pindah ke dokumen pengganti.
3. Pembayaran sisa tagihan pada invoice yang dibayar sebagian pakai saldo kredit (temuan di atas). **Tahap A sudah
   dibuat, menunggu CI** (`scripts/cp7_credit_remaining/`, uji otomatis `cp7-ow04b-remaining-native.yml`): pembayaran
   biasa dan pembatalannya pada invoice seperti itu diterima selama tidak melebihi sisa tagihan pada tanggal mana pun;
   status invoice dihitung dari pembayaran ditambah saldo kredit yang dipakai. Koreksi pembayaran pada invoice itu dan
   invoice yang punya retur sendiri masih ditolak. Belum boleh disebut selesai sebelum hasil CI lulus.

Ketiganya tetap terbuka; OW-04 belum boleh disebut selesai.

## Catatan teknis (untuk penulis berikutnya)

- Tahap `scripts/cp7_credit_followups/` di atas `cp7_contractor_correction.composition`. Fungsi yang diubah (hanya
  menambah `using detail=`): `cp7_credit.build_initial_return_for_draft_v1(jsonb,text,jsonb,uuid)`,
  `cp7_credit.native_source_enter(text,uuid)`, `cp7_credit.assert_simple_native_base_v1(uuid)`. Pembaca baru (privat,
  milik postgres): `cp7_credit_followups.detail_v1`, `initial_family_reasons_v1`, `correction_reasons_v1`,
  `source_mutation_reasons_v1`. Kontrak detail `cp7.credit-followups.refusal.v1`; layar: `src/lib/creditRefusalMessages.ts`.
- Pesan penolakan tidak berubah, jadi oracle lama (misalnya balapan DISTINCT `CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED`)
  tetap berlaku.
- Penolakan yang harus diganti untuk bagian 1: `02_initial_projection.sql:314-318` dan `assert_zero_excess_v1` untuk
  keluarga baru; `_consumer_root_source_profile_v1` (`CP7_CREDIT_MULTI_COHORT_RECONCILIATION_UNIMPLEMENTED`,
  `CP7_CREDIT_CURRENT_RECOGNITION_TARGET_UNRECONCILED` bila U≠0); `native_source_enter` dan `source_request_enter_v1`
  untuk invoice dengan beberapa kelompok; `payment_correction` (syarat satu kelompok); pemeriksa laporan OW-08a. Aritmetika
  banyak keluarga sudah ada di `ow04_ordinal_wrapper.reconcile_v1` (target keluarga ke-n = pengakuan dari base + keluarga
  sebelumnya dikurangi yang sudah diakui), tetapi materialisasi dan pembuktiannya belum.

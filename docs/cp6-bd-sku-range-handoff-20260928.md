# BD — follow-up SKU range, 28 September 2026 WIB

**CP6 HOLD; `production_go=false`, `audit_complete=false`.** Ini kelanjutan paket revisi temuan auditor di [handoff BD sebelumnya](cp6-bd-revision-handoff-20260928.md). Auditor/owner tetap menguji ulang sebelum menutup temuan. Tidak ada hosted/UAT/legacy write, merge ke main, atau deployment.

**Follow-up kiriman siap diuji ulang auditor; master SKU bersama tetap terbuka.** Source produk `2f6ac0ddb543a25edeca305beabd4513e8597c62`; kandidat lengkap `1c1d1a64ee05c051719caee4f81a52451c73da19` memperbaiki oracle tarif dasar dan dokumentasi. `src` dan `supabase` identik sejak source produk tersebut. Kedua run awal tetap INCOMPLETE; recheck terarah sudah PASS pada seluruh20 verdict. Bukti terstruktur: [sku_range_20260928.json](evidence/cp6-bd/sku_range_20260928.json). Commit handoff sesudah kandidat hanya berisi dokumen/bukti.

## Aturan owner dan batas pekerjaan

Satu SKU komersial mengelompokkan beberapa ukuran fisik. Harga jual dan tarif dasar jasa diatur sekali per SKU. Stok tetap masing-masing ukuran; HPP owner dapat ditampilkan sebagai nilai stok tersisa dibagi jumlah PCS tersisa. Ukuran spesial27 adalah SKU terpisah seperti `32007-27`. Ini aturan asli owner, bukan aturan tambahan.

Revisi produk kali ini memperbaiki form pemilihan penerima jasa. Master SKU bersama untuk harga jual, jasa dan BOM belum selesai. Semua gap, dampak CP1–6, sumber angka aksesori/HPP, pendekatan perubahan minimal serta oracle lanjutan tercatat di [cp6-sku-range-impact-20260928.md](cp6-sku-range-impact-20260928.md). Kelulusan biaya kiriman tidak boleh dipakai untuk menutup gap master tersebut.

Owner juga memberi contoh perubahan range31–33 menjadi31–34. Basis per ukuran mendukung penelusuran stok/nilai sebelum dan sesudah perubahan. Implementasi master berikutnya harus menyimpan keanggotaan bertanggal, mencegah ukuran34 terhitung pada dua SKU, dan menjaga snapshot transaksi lama. Skenario perubahan keanggotaan itu belum merupakan fitur yang dikualifikasi dalam follow-up ini.

## Revisi BD yang disediakan

Paket sebelumnya tetap membawa perbaikan alokasi biaya ke penerima jasa, respons total exact, invoice besar, replay setelah izin dicabut, extra paket, pagination invoice/sumber, jalur FREE/WAIVED sah, serta input tarif celup BE. Tidak ada perubahan SQL pada follow-up ini; hash BD/BE dan paket29 berkas tetap sama dengan handoff sebelumnya.

Form **Kirim dengan harga** sekarang:

1. Centang jasa yang dikerjakan; pilihan awal **Seluruh kiriman** mengambil jumlah positif yang benar-benar dikirim pada setiap ukuran.
2. Untuk pengecualian, pilih **Sebagian ukuran/jumlah**, lalu isi penerimanya. Contoh: finishing5 PCS ukuran32 tidak menambah pekerjaan ukuran31/33.
3. Ukuran yang tidak dikirim boleh0 atau kosong. Kiriman hanya32 dan SKU singleton27 tidak memerlukan ukuran fiktif.
4. Cakupan kosong, pecahan, negatif atau melebihi kiriman ditolak. Qty kiriman yang dikecilkan tidak diam-diam memangkas cakupan lama; operator harus memperbaikinya.
5. Perubahan membatalkan konfirmasi. Ganti batch/paket/vendor atau batalkan pilihan jasa menghapus state terkait. Komponen yang termasuk paket tidak bisa ditambahkan lagi; tambahan tetap wajib alasan.

## Bukti dan riwayat kegagalan

| Pemeriksaan | Bukti | Hasil yang sudah dibaca |
|---|---|---|
| Build dan tes lokal | Source2f6ac0d | Build resmi PASS;40 tes laundry/QC/conversion PASS; security PASS |
| Skenario BD+BE awal | Run36349471819 /job108705193247 | Native7 PASS+1 INCOMPLETE;18 race,6 Auth/HTTP,19 browser PASS; console0; primary tetap, clone0 |
| Upaya perbaikan oracle pertama | Run36350528938 /job108708212366 | Native7 PASS+1 INCOMPLETE;18 race,6 Auth/HTTP,19 browser PASS; console0; primary tetap, clone0 |
| Penyebab dua INCOMPLETE | `RANGE:SAME_SERVICE_VERSION_MIXED_SINGLE_32_SINGLETON_27` | Pertama mencari ID pada respons publik; kedua keliru mewajibkan FK versi non-null pada ordinary RATE. Kolom itu berasal dari scoped rate; nominal tarif dasar disimpan sebagai snapshot. Lihat koreksi oracle di bawah |
| Recheck terarah | Run36351308461 /job108710390034 |1/1 native yang diperbaiki +19/19 browser PASS; console0; Auth dipulihkan; primary tetap, clone0. Bukan eksekusi ulang seluruh51 kasus |
| BD T1 | Run36349471790 /job108706102770, attempt2 |41/41 PASS;232 berkas reader diterima; expectation mismatch kosong; primary tetap, clone0 |
| Paket install dan capture | Run36349471753 /job108705193152 dan108705192999, attempt1 |29 berkas terpasang; pins sama; restore SAME_MEANING; empat gate true |
| Browser paket | Run36349471753 /job108706104262, attempt2 |10/10 PASS; console0; auth0→0; primary tetap |
| CodeQL source produk | Run36349471752 | Actions, Python, C/C++, JS/TS PASS; masing-masing result_count0 |
| CodeQL helper pertama | Run36350528956 | Actions, Python, C/C++, JS/TS PASS; masing-masing result_count0 |
| CodeQL helper final | Run36351308448 | Actions, Python, C/C++, JS/TS PASS; masing-masing result_count0 |

T1 attempt1 terhenti sebelum skenario oleh `PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE`; browser paket attempt1 terhenti sebelum kasus oleh port54328 yang sudah dipakai. Hanya job gagal yang diulang pada commit yang sama, tanpa perubahan guard/oracle/produk. Kegagalan awal tidak dihapus.

Oracle pengganti diberi nama eksplisit `RANGE:SAME_EFFECTIVE_BASE_RATE_MIXED_SINGLE_32_SINGLETON_27`: setiap nominal/qty/jumlah snapshot harus cocok dengan tepat satu versi vendor/proses yang berlaku pada waktu kiriman tersimpan, dengan ID master yang dibuat fixture. Bukti ini tidak menyatakan ordinary RATE menyimpan FK versi. Alasan, kontrak source dan batas koreksi disimpan sebelum recheck di [cp6-bd-range-oracle-correction-20260928.md](cp6-bd-range-oracle-correction-20260928.md). Syarat bisnis untuk FK versi eksplisit, bila diperlukan, belum diimplementasikan oleh follow-up ini. Produk tidak berubah; native7/race18/HTTP6 yang sudah PASS tetap memakai bukti run sebelumnya, sedangkan recheck hanya menguji oracle tersisa dan browser yang dikonfigurasi. Machinery strict-group/workflow tidak dilonggarkan.

Dasar kualifikasi gabungan: native7 +18 race +6 HTTP dari run36350528938, ditambah native pengganti1 +19 browser dari run36351308461. Seluruh verdict yang dipakai PASS pada source produk identik. Ini bukan klaim51 PASS dalam satu run, bukan pengubahan status dua run lama, dan bukan penutupan gap master. Runtime self-test terakhir juga SELFTEST_PASS dengan pemeriksaan kebocoran/rollback/planned-case yang tetap aktif.

Native HPP yang sudah PASS memakai satu SKU dan tiga produk fisik dengan stok31=4,32=7,33=2. Biaya finishing hanya5×32; total HPP59668.72. Penjualan2×32 menyisakan4/5/2; invoice+13 terbagi FG+11/COGS+2/WIP0; retur1×32 kembali ke produk/lot yang sama sehingga stok4/6/2. Ringkasan tertimbang berubah mengikuti kuantitas/nilai tersisa. Ini bukti native, bukan klaim halaman HPP connected atau browser penjualan selesai.

## Batas penerimaan yang tetap berlaku

- Temuan auditor belum ditutup oleh writer. FREE/WAIVED disediakan untuk diuji pada jalur owner yang sah; hasil lama tidak diubah menjadi vonis bug tanpa bukti.
- HP fisik dan Safari belum dikualifikasi. Browser memakai desktop dan emulasi HP.
- Data master bisnis live belum diaudit; tidak ada bukti dari follow-up ini bahwa seluruh SKU atau jurnal historis rusak.
- T2 dan rollback dari handoff sebelumnya tetap dirujuk karena SQL/paket tidak berubah; bukan klaim pengujian baru.12 kasus kalender tetap HOLD beserta seluruh disposition historis yang disebut di sana.
- Advisor menyisakan delta132 INFO privat yang ditangani gate existing; tidak ada klaim zero-advisory. Restore SAME_MEANING pada disposable clone tetap mempunyai batas pg_cron yang sudah dicatat.

Untuk audit ulang, gunakan kandidat lengkap dan harness disposable yang dipin. Jangan menimpa database dengan marker kandidat lama atau menganggap paket ini izin produksi.

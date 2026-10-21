# Retur CP7 dan pemicu HPP saldo awal

Kandidat pertama `7613621553b6cb8f2227d2b6dcca695ae019f15a` belum lulus.
CI run39528857467/job118989826518 menghasilkan 50 PASS dan8 INCOMPLETE;
seluruh44 kasus lama lulus. Bukti pertama, seluruh58 status, laporan lengkap,
log lengkap dan hash artefak disimpan dalam `CI_761362_FIRST_FAILURE*`.
Semua batas pemulihan kasus, pemulihan CP6 dan gerbang advisor lulus.
Ini kegagalan integrasi produk, bukan alasan mengubah expected.

Pemicu Native `sync_opening_hpp_after_return_status` memanggil sinkronisasi
saldo awal ketika status menjadi POSTED, sebelum Native membentuk jurnal
SALES_RETURN. Pada lot yang memiliki koreksi HPP asli, pemicu itu menghabiskan
vektor HPP pada jurnal lifecycle terpisah. Dua kasus refund0 kehilangan jurnal
retur; enam lainnya mempunyai jurnal retur tanpa vektor HPP yang diwajibkan.
Jurnal lifecycle memakai versi koreksi sebagai sumber dan tanggal hari ini;
jurnal itu tidak boleh diperlakukan sebagai bukti jurnal retur bertanggal sumber.

## Kontrak kandidat perbaikan, dideklarasikan sebelum CI

- Expected14 kasus tetap byte-identik `f53001d8ec87289a7fc7ca1a6f69752f994480418256923133329e6395a37d4c`.
  Ke44 kasus lama, urutan kasus dan hitungan58 tetap sama.
- Hanya DRAFT→POSTED milik retur CP7 ORDINARY/REVIEWED_SETTLEMENT yang
  tepat dan telah melewati guard Native boleh menunda pemicu: PID, tx, actor,
  request, sale/customer, fase ENTERED, totals guard dan projection harus cocok.
  Native EMPTY dan konteks/status lain memakai loop pemicu lama persis.
- Keberadaan/ketiadaan dan seluruh isi cache saldo awal serta catatan koreksi
  disegel pada projection; baris yang ada dikunci sebelum account/period.
  Sebelum penundaan, metadata disandingkan lagi dengan sumber yang disegel.
  Lot yang ditunda wajib berada dalam daftar lot yang sudah dikunci.
- Native membuat jurnal SALES_RETURN lengkap dengan pemeriksaan lama atas
  akun, dimensi, nilai dan kedua tanggal. Expected uang tidak dilonggarkan.
- Sesudah jurnal, sebelum materialisasi, full target Native harus sama dengan
  actual book. Selisih sumber Native
  `round(total_cost,2)-round(initial_qty*state.current_hpp,2)` wajib nol.
- Refresh hanya menggunakan salinan byte-identik bagian diagnostik dari
  Native BE yang dipin sumber dan metadata. Tidak memanggil fungsi finansial,
  penyiapan transfer atau sinkronisasi konversi global. Catatan ini merupakan
  penyempitan adapter yang disengaja: pemanggilan fungsi sinkronisasi Native
  lengkap dibatalkan setelah counter menemukan efek pada produk lain.
- Sumber stock/HPP/konversi/jurnal terkait tidak boleh berubah selama refresh.
  Saksi proses privat harus hilang; constraint tertunda menguji INSERT maupun
  UPDATE agar pengubahan PID/tx tidak menghindari penutupan.
- Definisi/metadata fungsi pemicu dan attachment sebenarnya dicapture,
  diverifikasi dan dipulihkan. Fungsi Native sinkronisasi asli tetap identik.

## Tambahan kontrol negatif pada kasus pertama

Semua injeksi berikut berlabel disposable dan dipulihkan dengan savepoint
sebelum transaksi positif; tidak mengganti sumber ekonomi maupun oracle uang.

1. Transisi NULL/tidak tepat serta operasi tanpa pemilik tidak boleh menunda.
2. Perubahan `updated_at` cache saja menghasilkan quote hash baru; quote lama
   ditolak `CP7_CREDIT_COMPLETE_QUOTE_CHANGED` tanpa efek tambahan.
3. Trigger uji yang menolak UPDATE diagnostik setelah jurnal Native harus
   membatalkan jurnal, gerak stok, request dan family bersama-sama.
4. Saksi privat yang sengaja bocor lalu diubah PID-nya harus ditolak saat
   `SET CONSTRAINTS ALL IMMEDIATE`, tanpa data transaksi tersisa.

## Batas bukti dan sisa pekerjaan

Pemeriksaan lokal22 skenario memakai PGlite dan sumber rumus asli, dengan
baris sintetis; ini bukan bukti Native, browser, race atau penerimaan auditor.
Dua pemeriksa internal menelusuri urutan secara independen sebelum saling
counter. Berkas diagnosis, source check dan bantahan disimpan di folder ini.
Hasil CI kandidat perbaikan masih diperlukan. Pecahan HPP pada jalur direct
Native EMPTY belum diklaim diperbaiki. Selisih basis sumber dan snapshot positif
dengan vektor nol tetap menolak; cakupan OW04 yang lain tetap terbuka.
`production_go:false`; Enteng, main dan cp7/integration tidak disentuh.

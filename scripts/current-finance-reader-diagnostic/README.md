# D17-18 — diagnosis pembaca HPP stok awal

Pengukuran aktual a569d322, run40286613815/artifact12636473845:
laporan resmi11.679,017ms, tiga pemeriksa laporan,10.800 panggilan resolver
HPP stok awal dan fungsi audit. Resolver melakukan satu FOR UPDATE dan dua
cabang UPDATE. Mengurangi pengulangan belum aman sebelum efek ini dipahami.

Eksperimen ini mempertahankan resolver penulis asli. Dalam transaksi yang
selalu dibatalkan, satu panggilan pembaca laporan dialihkan ke salinan privat
yang mempertahankan semua rumus/penolakan, menghilangkan lock dan dua UPDATE.
Isi resolver harus persis SHA256d82bdae08187b2121b7a777e0b3973f292318b195a148762f3ba5998407bf48a;
perubahan sumber ditolak. Helper milik postgres, search_path kosong, tidak
dapat dijalankan peran browser maupun pekerja. Tidak dipasang pada produk.

Pembanding menjalankan laporan lama dan kandidat pada fixture kecil serta
1.200SKU×3ukuran yang diposting melalui Native. Seluruh laporan dibandingkan,
hanya report.captured_at yang dikecualikan. Hitungan sumber harus sama.
pg_stat_xact_user_tables membuktikan percobaan penulisan; kandidat harus nol,
semua data/sequence tetap sama sebelum rollback. Sesudah rollback seluruh22
kelompok katalog dan seluruh data/sequence harus sama, termasuk definisi asli.
Gerbang pemasangan/pemulihan CP6 dan keamanan lama tetap dipakai.

Batas kecil8detik, diagnosis pabrik30detik, lock2detik; tanpa retry atau
perubahan batas produk. Waktu lama/kandidat serta selisihnya dicatat, bukan
diluluskan memakai persentase lebih cepat yang dikarang. Belum membuktikan
seluruh analisis selesai, PRICE_PERCENT, perubahan sumber bersamaan, Auth,
layar, pengurangan tiga pemeriksa, audit independen, maupun izin produksi.
Kegagalan lama tetap tersimpan dan tidak diganti oleh hasil eksperimen ini.

Rujukan teknis: PostgreSQL17 Function Volatility Categories dan CREATE FUNCTION.
STABLE tidak cukup untuk menyatakan tanpa penulisan jika memanggil fungsi
VOLATILE. Karena itu pengujian memeriksa penulisan nyata dan seluruh data.

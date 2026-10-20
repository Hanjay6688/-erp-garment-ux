# Usulan penulis: safety stock dengan rumus + peringatan WA, sebelum paket r6 dikirim ke auditor (20 Okt 2026)

Dasar: keputusan owner D17-4, D17-5, D17-7, D17-8 (kutipan persis di `docs/cp7/OWNER_DECISIONS_20261008.md`) dan riset pakar
28 Sep (`docs/cp7/benchmark-decisions.md`). Status: **disetujui owner (D17-9)**. Bagian 1–4 (barang jadi, kain, aksesori) sudah dibuat,
desain teknis dan bedanya dari usulan ini di `docs/cp7/wa/STOCK_FORMULA_FG_DESIGN.md` (tiga beda menunggu keputusan owner);
bagian 5: uji lengkap satu versi belum.

## 1. Safety stock barang jadi dengan rumus pakar

- Per barang per ukuran (satu SKU). Stok yang dihitung: stok bebas di semua gudang barang jadi (stok fisik dikurangi yang
  sudah dipesan di draf penjualan), ditambah yang sedang diproduksi untuk model dan ukuran itu.
- Rumus (riset pakar 28 Sep, MIT ESD.260):
  - kebutuhan selama menunggu produksi = rata-rata jual per hari × lama produksi;
  - safety stock = angka tingkat layanan × naik-turunnya penjualan selama lama produksi;
  - **titik pesan ulang = kebutuhan selama menunggu produksi + safety stock**.
- Bahan rumus dari data ERP sendiri: penjualan yang sudah diposting per hari (jendela 30 hari, bisa diubah), lama
  produksi per model dari catatan produksi nyata (potong sampai barang jadi masuk gudang), tingkat layanan bawaan 95%
  (pilihan 90/95/99%, bisa diubah di aplikasi).
- Dihitung ulang otomatis di belakang hanya untuk barang yang berubah (penjualan, retur, barang masuk, produksi selesai).
- Barang yang datanya belum cukup (barang baru, model yang belum pernah selesai diproduksi) tidak diberi angka tebakan:
  tampil "belum cukup data" sampai datanya cukup, atau memakai angka yang diisi manual.
- Angka manual per barang menggantikan rumus bila diisi (tempatnya sudah ada di ERP: `erp.stock_policy_versions`).
- Layar di Ringkasan Barang Jadi: per barang tampil stok bebas, sedang diproduksi, titik pesan ulang, asal angkanya
  (rumus/manual/belum cukup data) dan rinciannya; Owner bisa mengisi atau menghapus angka manual.
- Batas yang ditulis jujur: tingkat layanan 95% belum diuji ke data penjualan Bos sendiri (data nyata tidak ada di
  lingkungan uji). Uji itu dilakukan sesudah pemasangan (CP7C), lalu angkanya bisa diganti di aplikasi.

## 2. Peringatan WA "stok barang jadi menipis"

- Dicek server tiap menit seperti stok kain. Kalau stok bebas + sedang diproduksi ≤ titik pesan ulang → masuk Pengingat
  sistem dan WA sekitar semenit kemudian. Contoh: "Kaos Polos Hitam M: sisa 12 pcs, sedang diproduksi 0 pcs, titik pesan
  ulang 40 pcs".
- Sekali per kejadian; selama masih di bawah, diingatkan lagi tiap 24 jam (bisa diubah); bunyi lagi hanya sesudah stok
  sempat naik di atas titik itu.
- Hanya akun yang boleh melihat stok barang jadi yang melihatnya di Pengingat sistem.

## 3. Kain: minimum dengan rumus

- Rumus sama: pemakaian kain per hari (dari catatan potong) × lama kirim supplier + safety stock rumus pakar.
- Lama kirim supplier tidak tercatat di ERP (owner 20 Okt: "Lama kirim supplier cenderung gak ada data ke record pula";
  diperiksa: ERP hanya mencatat penerimaan barang, tidak ada pesanan ke supplier dengan tanggal pesan). Jadi lama kirim
  menjadi isian "lama kirim (hari)" per kain di data master, diisi saat dipakai. Kosong berarti rumus tidak jalan untuk
  kain itu: dipakai angka minimum manual bila ada, kalau tidak, kain itu ditandai "belum diatur" dan tidak berbunyi.
- Angka minimum yang sekarang diisi manual di data kain tetap bisa dipakai dan menggantikan rumus.
- Peringatan "stok kain di bawah minimum" yang sudah ada tetap jalan, memakai angka rumus bila tidak ada angka manual.
- Kebutuhan kain dari rencana produksi (analisis) tetap seperti sekarang.

## 4. Aksesori

- Safety stock dengan rumus yang sama seperti kain (pemakaian per hari × lama kirim + safety stock), dengan isian
  "lama kirim (hari)" per aksesori di data master (alasan sama dengan kain), angka manual bisa, dan peringatan WA
  "aksesori menipis" tiap menit.
- Kebutuhan aksesori dari rencana produksi ikut diteruskan ke WA. Untuk itu dibuat pengecekan ulang ke stok aksesori
  terbaru sebelum pesan dikirim (sekarang modul pengingat belum punya pengecekan ini, jadi kebutuhan aksesori tidak pernah
  diteruskan).

## 5. Lain-lain dalam putaran yang sama

- Bawaan analisis otomatis tiap 4 jam (D17-7) dipasang sekarang, tidak menunggu CP7C.
- Semua uji memakai server CallMeBot palsu. Setiap peringatan baru diuji dengan pembanding yang dihitung terpisah
  (bukan memakai fungsi yang diuji), layar diuji di komputer dan HP, lalu ke-117 uji dijalankan ulang di satu versi.
- Paket r6 diperbarui (README, kotak Fable/Astra/Sol) sesudah semuanya lulus, baru dikirim.

## 6. Hasil pemeriksaan data (20 Okt, baca saja, tidak ada yang diubah)

- **Stok barang jadi:** sudah ada pembaca CP7 yang diterima (`cp7_fg.positions`, layar Ringkasan Barang Jadi), dihitung
  dari gerakan stok barang jadi; stok bebas sudah dikurangi draf penjualan. Itu yang dipakai, bukan view lama
  `erp.v_fg_stock_position_v1` (tidak dipakai pembaca CP7 mana pun dan tanpa filter tanggal fisik).
- **Penjualan per hari per barang:** pembaca riwayat permintaan yang ada terlalu berat untuk tiap menit (sekali tangkap
  semua barang, batas 1.000 barang). Sumber yang dipakai: gerakan stok `SALE` yang tidak dibalik, per barang (akar
  identitas + ukuran) per hari WIB. Retur dicatat terpisah, tidak mengurangi penjualan (sama dengan aturan riwayat
  permintaan yang sudah ada).
- **Lama produksi:** belum ada yang mengukur. Datanya ada: tanggal potong (`cutting_groups.cut_at`, bahan sudah dikeluarkan)
  sampai barang lulus QC masuk gudang (`fg_lots.produced_at`, asal PRODUCTION, QC tidak dibalik), dihitung per model
  (median beberapa bulan terakhir). Yang tidak dihitung: lot saldo awal/impor/void, hasil rework. Kalau model belum punya
  catatan, dipakai `lead_days` manual di profil perencanaan yang sudah ada, kalau tidak ada: "belum cukup data".
- **Rumus yang sudah ada di ERP:** profil perencanaan per barang (`lead_days`, `review_days`, `buffer_days`, isian manual)
  dan hitungan target `ceil(D*(L+R+B))` (cadangan dalam hari). Riset 28 Sep mempertahankan dua cara cadangan, DAYS (hari)
  atau STATISTICAL (rumus pakar), dan melarang memakai keduanya sekaligus. Bawaan baru: STATISTICAL; kalau Bos mengisi
  cadangan dalam hari untuk barang tertentu, barang itu memakai DAYS.
- **Angka manual titik pesan ulang:** tempatnya ada (`erp.stock_policy_versions`), tetapi fungsi tulis Native ditutup untuk
  browser sejak R4-01 dan tidak ada layarnya. Dibuat fasad CP7 baru khusus Owner/Admin untuk mengisi dan menutupnya.
- **Hak lihat:** peringatan barang jadi mengikuti hak layar Ringkasan Barang Jadi (`warehouse.fg.view`).
- **Hitung ulang saat berubah:** modul peringatan tidak mengubah tabel Native. Angka rumus disimpan di tabel CP7 sendiri dan
  dihitung ulang hanya untuk barang yang punya gerakan baru sejak hitungan terakhir (cara deteksi perubahan yang sudah
  dipakai analisis bertahap).
- **Lama kirim supplier:** tidak tercatat (tidak ada tabel pesanan ke supplier; hanya `lead_time_days` kosong di tabel
  penjelasan stok). Menjadi isian per kain/aksesori, lihat bagian 3 dan 4.
- **Belum diperiksa:** pemakaian aksesori per hari, dan pembagian barang yang sedang diproduksi (dicatat per model dan ukuran)
  ke SKU akhir.

## Tidak termasuk

Pemasangan ke Enteng (CP7C, ditahan D13-9a), uji tingkat layanan ke data nyata Bos (sesudah pemasangan), kecepatan analisis
langsung dengan angka keuangan (tetap terbuka, tidak diubah).

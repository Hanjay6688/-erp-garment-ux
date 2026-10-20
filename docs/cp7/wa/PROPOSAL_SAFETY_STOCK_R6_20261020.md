# Usulan penulis: safety stock dengan rumus + peringatan WA, sebelum paket r6 dikirim ke auditor (20 Okt 2026)

Dasar: keputusan owner D17-4, D17-5, D17-7, D17-8 (kutipan persis di `docs/cp7/OWNER_DECISIONS_20261008.md`) dan riset pakar
28 Sep (`docs/cp7/benchmark-decisions.md`). Status: **usulan**, belum dibuat.

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

- Rumus sama: pemakaian kain per hari (dari catatan potong) × lama kirim supplier (dari tanggal pesan ke tanggal terima)
  + safety stock rumus pakar.
- Angka minimum yang sekarang diisi manual di data kain tetap bisa dipakai dan menggantikan rumus.
- Peringatan "stok kain di bawah minimum" yang sudah ada tetap jalan, memakai angka rumus bila tidak ada angka manual.
- Kebutuhan kain dari rencana produksi (analisis) tetap seperti sekarang.

## 4. Aksesori

- Safety stock dengan rumus yang sama seperti kain (pemakaian per hari × lama kirim + safety stock), angka manual bisa,
  dan peringatan WA "aksesori menipis" tiap menit.
- Kebutuhan aksesori dari rencana produksi ikut diteruskan ke WA. Untuk itu dibuat pengecekan ulang ke stok aksesori
  terbaru sebelum pesan dikirim (sekarang modul pengingat belum punya pengecekan ini, jadi kebutuhan aksesori tidak pernah
  diteruskan).

## 5. Lain-lain dalam putaran yang sama

- Bawaan analisis otomatis tiap 4 jam (D17-7) dipasang sekarang, tidak menunggu CP7C.
- Semua uji memakai server CallMeBot palsu. Setiap peringatan baru diuji dengan pembanding yang dihitung terpisah
  (bukan memakai fungsi yang diuji), layar diuji di komputer dan HP, lalu ke-117 uji dijalankan ulang di satu versi.
- Paket r6 diperbarui (README, kotak Fable/Astra/Sol) sesudah semuanya lulus, baru dikirim.

## 6. Yang masih dipastikan penulis saat mulai

- Data penjualan per hari per barang, lama produksi per model, dan lama kirim supplier: sumbernya di ERP dan seberapa
  lengkap. Bila salah satu tidak tercatat di ERP, bagian itu memakai angka manual sampai datanya ada, dan ditulis di laporan.
- Stok "sedang diproduksi" tercatat per model dan ukuran, belum per SKU akhir; pembagiannya ke SKU dipastikan.

## Tidak termasuk

Pemasangan ke Enteng (CP7C, ditahan D13-9a), uji tingkat layanan ke data nyata Bos (sesudah pemasangan), kecepatan analisis
langsung dengan angka keuangan (tetap terbuka, tidak diubah).

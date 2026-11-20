# Pengesahan nota penjualan Global

Paket ini diterapkan setelah pemasangan Global gabungan `ffda5cfc`. Dari mesin pengujian dengan Git, Python dan psycopg 3, arahkan variabel koneksi PostgreSQL biasa ke salinan Global, lalu jalankan perintah berikut dari akar produk.

```sh
python scripts/cp7_global_invoice_post/install.py up
```

Perintah `down` pada jalur yang sama mengembalikan definisi induk dan melepas tiga indeks paket. Kedua arah berjalan dalam satu transaksi, memeriksa isi objek sebelum dan sesudah, serta dapat dijalankan ulang. Kunci transaksi pengesahan nota menyelaraskan pemasangan dengan penulis HPP.

Pengesahan tetap melalui `public.erp_cp7_save_sale_v1`. PostgreSQL memilih riwayat alokasi milik SKU sebelum mencocokkan lot dan biaya. Penghitungan biaya non-PO memakai kembali hasil antara dalam satu pernyataan SQL. Pemeriksaan konteks konversi otomatis tetap memanggil seluruh validasi ketika sesi, transaksi, lokasi dan SKU cocok. Tiga indeks melayani pencarian lot, alokasi penjualan dan retur per SKU.

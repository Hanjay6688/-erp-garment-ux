# Uji kontrol browser Mandor dan SKU

6 November 2026 WIB. Empat pengamatan di Chromium 151.0.7922.34 dengan Playwright 1.62.1 lulus pada App asli dan respons fixture loopback. Desktop memakai 1440 px dan WIB. HP memakai 390 px dan zona Los Angeles, sementara input tanggal SKU tetap diproses sebagai WIB. Kedua kandidat memiliki sumber App, paket dan masukan build yang sama, sehingga satu build digunakan untuk dua jalur uji.

| Jalur | Kontrol yang berhasil dipakai | Bukti |
| --- | --- | --- |
| Mandor `415e951` | Masuk melalui form, cari dan buka payroll, pilih nota, isi nominal, centang pemeriksaan, batal, baca ulang, dan buka konfirmasi lepas tagihan | 2 tampilan lulus dalam 2,695 detik. Hasil Mandor sah pada cakupan fixture walaupun keseluruhan run pertama gagal pada impor SKU. [Run 42144159256](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/42144159256) |
| SKU `49a0f1c` | Masuk melalui form, cari dan pilih padanan, kirim satu aksi padanan ke fixture, baca sisi pasangan, ganti pilihan SKU tujuan, isi jumlah dan waktu WIB, buka pratinjau, dan periksa tombol konversi aktif | 2 tampilan lulus dalam 4,626 detik. Run SKU berakhir sukses. [Run 42144442754](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/42144442754) |

Potongan helper locator diambil langsung dari skrip browser A yang dipatok. Permintaan autentikasi dan data ditangani fixture. Nol permintaan luar, galat console, dan limpahan dokumen pada empat pengamatan. Durasi tersebut mengukur browser dengan fixture. Waktu transaksi ERP aktual masih perlu diukur pada backend yang diterima A.

Unduhan Chromium lokal menghasilkan arsip terpotong, dan Chromium sistem ditolak saat membuka socket internal. Uji diteruskan di runner GitHub. Konfigurasi awal CI gagal sebelum job dibuat karena konteks `runner` dipakai di `jobs.env`. Pemakaian `github.workspace` membuat runner mulai. Arsip pertama juga merekam kegagalan impor SKU karena checkout ringkas belum memuat `scripts/current-sku-pair-browser-qualification/evidence.mjs`. Berkas itu kini ikut dimuat. Pemeriksa aslinya tetap mencocokkan 7.049 byte serta SHA-256 sumber. SKU saja dijalankan kembali setelah perbaikan, dengan hasil Mandor pertama dipertahankan. [Aturan konteks GitHub](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability)

`FINAL_RECEIPT.json` mengikat versi, sumber skrip, durasi, dan dua arsip asli. Perbaikannya pada setup smoke B. Untuk run gabungan, A tetap memegang integrasi dan penerimaan. Bukti empat pengamatan ini mendukung kesiapan kontrol dan data fixture. Pengujian Auth aktual, simpan resmi, pemulihan respons hilang, pembalikan transaksi dan pemulihan database tetap berada pada paket aktual.

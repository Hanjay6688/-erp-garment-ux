# Kelanjutan audit — 27 September 2026

Rencana awal tetap utuh. Kelanjutan ini menutup celah eksekusi, bukan menurunkan kriteria awal.

Prasyarat produksi dibuat auditor: PO, potongan, hasil ukuran 7+6 PCS, distribusi mandor, dan dokumen kerja. Dokumen kerja diposting dengan tarif 100/PCS (biaya awal 1.300), lalu terminal jahit dicatat. Bahan/aksesori tidak mempunyai biaya dalam model terkontrol ini. Ini batas integrasi untuk mengisolasi tambahan biaya laundry, bukan bukti alur pembelian/potong lulus. Seed tidak menonaktifkan trigger/constraint. Laundry kirim, terima, QC dan invoice dijalankan melalui RPC publik sebagai OWNER terautentikasi. Bila jual/retur perlu fungsi ERP native, lapis itu disebut eksplisit.

Oracle fisik: 13 keluar jahit, 13 dikirim, 13 diterima, 13 masuk FG. Proses tambahan atas 5 PCS tidak menambah fisik. Penjualan 4 PCS menyisakan 9; retur 1 menyisakan 10 dan net terjual 3. Tidak ada snapshot posted yang berubah saat master harga berubah. SKU sama tetapi merek berbeda tetap identitas terpisah.

Oracle nilai: laundry 59.568,72 + tenaga kerja 1.300 = 60.868,72. Selisih invoice 1.677,52 menghasilkan total 62.546,24. Tidak mengandalkan fungsi perhitungan produk sebagai expected. Pembulatan total dua desimal; HPP enam desimal diperiksa dengan toleransi akumulasi 0,000013. Alokasi nilai FG/COGS diperiksa menurut PCS aktual dan konservasi total. Nilai biaya unknown tidak dianggap final. Setelah harga diisi, komponen yang diketahui harus masuk biaya tanpa menggandakan stok. Kebijakan PRODUCT_COST dan ALLOW_PENDING dipilih dalam data audit sesuai pilihan owner yang dipulihkan; ini tidak mengubah konfigurasi produksi.

Kegagalan setup/adaptor tetap disimpan. Jika prasyarat gagal, skenario bergantung dicatat BLOCKED, bukan FAIL produk atau PASS. Penolakan domain dinilai tanpa menuntut kode error tertentu. Browser/HTTP harus mempunyai bukti sendiri; tes SQL tidak menggantikannya.

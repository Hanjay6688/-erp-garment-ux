# BF: penyelesaian master SKU range

Owner telah mengizinkan seluruh revisi range; ini pelaksanaan aturan awal, bukan aturan bisnis baru. CP6 tetap HOLD sampai bukti writer dan audit independen lengkap.

Kontrak: satu brand + SKU komersial mengikat satu model/warna dan daftar akar produk fisik. Daftar anggota bertanggal; akar identitas, size, lot, stock movement dan alokasi penjualan tidak digabung. Perubahan kelompok atomik, memakai expected revision dan request id. Pemindahan ukuran antar kelompok harus dalam satu perubahan; riwayat kelompok tetap disimpan.

Satu konfigurasi harga/resep SKU diturunkan ke versi ekonomi existing per akar produk, dengan pemetaan ke satu revisi bisnis. Resolver transaksi lama tetap membaca versi lama. BOM produksi mengikat revisi bisnis yang sama untuk saudara ukuran dalam PO. Tarif kerja dan laundry memakai referensi SKU yang eksplisit; snapshot yang sudah terjadi tidak dihitung ulang oleh edit master.

Oracle yang harus dibuktikan: 31/32/33 satu harga dan BOM; produksi hanya32 tetap tarif sama; singleton27 terpisah; anggota34 masuk bersama keluarnya dari kelompok lama tanpa perubahan qty/value; tanggal efektif dan riwayat tetap; konflik data lama terlihat; edit lewat ukuran tidak melewati master; dua operator stale ditolak; replay sesudah pencabutan izin ditolak; HPP menggunakan qty/value fisik; QC/sale/return/invoice/conversion dan import tidak kehilangan lineage.

Artefak BF adalah lapisan pengembangan setelah BE, hanya untuk runtime disposable. Tidak mengubah migration historis, menggabungkan main, atau mengizinkan produksi. Status implementasi dan hasil uji akan dicatat setelah eksekusi, tanpa mengubah verdict lama.

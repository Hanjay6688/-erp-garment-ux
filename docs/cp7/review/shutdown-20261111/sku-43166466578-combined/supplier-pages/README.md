# Halaman kedua transfer supplier

Endpoint `erp_cp7_get_supplier_transfer_v1` dan definisi lama `workspace_v1` cocok byte dengan katalog E4EA. PostgreSQL 17.6 membuka dua backend. Backend pembaca tertahan saat menghitung halaman kedua, kemudian backend penulis memasukkan transfer ke-26 dan menguji commit serta rollback.

| Pengamatan | Sebelum transfer ke-26 | Saat commit di tengah pembacaan | Pembacaan berikutnya |
| --- | --- | --- | --- |
| Definisi lama | Total 25, halaman kedua kosong | Total 25, halaman kedua memuat T-26 | Total 26, halaman kedua memuat T-26 |
| Jumlah dan baris satu pernyataan | Total 25, halaman kedua kosong | Total 25, halaman kedua kosong | Total 26, halaman kedua memuat T-26 |

Kontrol rollback menghasilkan halaman awal pada kedua definisi. Halaman pertama setelah commit memberi offset 25. Kedua halaman mencakup 26 transfer unik, dan halaman kedua invoice tetap memuat AP-26. `workspace_v1` tetap `VOLATILE` dengan pemeriksaan akses awal dan akhir. Definisi asal dipulihkan dan cluster fixture dihapus.

Uji memakai sumber AP dan akses fixture, serta endpoint dan pembaca SQL asli. Adopsi OW06 masih memakai Auth aktual dan katalog setelah Global diterima. Patch gabungan UI OW06/OW09 yang sudah diuji cocok pada salinan sumber Global dengan SKU af6e. Pertahankan hasil 92 uji UI lama sesuai hash sumbernya.

# Batas HPP yang ditemukan ketika menunggu browser4

Ini pembacaan sumber dan contoh matematika, bukan hasil runtime baru atau
perubahan implementasi. initial_hpp_projection_v1 dalam
scripts/cp7_customer_credit/coordinator/02_initial_projection.sql:75–79,103
secara sengaja menolak biaya per pcs yang bukan kelipatan sen. Quote harus
cocok target dan buku penuh sebelum diterima; kode menghitung q*cost pada118
sebelum pembandingan target/buku pada125–143. Native44 dan browser4 memakai
HPP10,00; bukti itu tidak menerima seluruh biaya pecahan/multi-lot/PO.

Sumber Native terbaru pada rantai yang dipakai: release BE
supabase/release/cp6-t3/20260926050000_erp_v2_6_20be_cp6_conversion_redye_pocket.sql,
compute_po_hpp_gl_targets_v2620d pada1613 dan
compute_non_po_product_hpp_targets_v2620f pada3225.

- PO menghitung raw_owned/raw_cogs seluruh lot, baru membulatkan target pool.
  Target FG=round(total,2)−round(total−raw_owned,2), COGS=round(raw_cogs,2)
  dan other_out=total_out−COGS. Kain kantong/konversi/extra yang ada tetap
  ikut raw_total; rumusnya tidak boleh diganti penjumlahan per-lot yang
  sudah dibulatkan.
- Non-PO membulatkan target masing-masing lot setelah pengurangan nilai
  konversi yang berlaku, baru menjumlahkan hasil per produk.
- Contoh sederhana tanpa konversi/extra: satu lot biaya1,00 dengan basis3
  pcs, dijual3 lalu dikembalikan masing-masing1. Target FG sesudah retur
  pertama0,33 dan sesudah kedua0,67. Marginal retur kedua0,34, sehingga
  pembulatan biaya per pcs menjadi0,33 lalu mengalikannya tidak benar.
- Dua lot dengan data biaya/basis yang sama, masing-masing tersisa1 dan
  net terjual2: Non-PO FG0,66/COGS1,34, sedangkan jika keduanya satu pool
  PO, FG0,67/COGS1,33. Ini contoh matematika dari letak pembulatan dalam
  sumber, bukan fixture bisnis yang sudah dijalankan.

Tahap berikutnya harus mendeklarasikan expected terpisah untuk before/after
target Native, marginal tiap akun termasuk other_out, pasangan tanggal,
versi HPP yang berubah, beberapa alokasi pada lot/PO sama, total quote sama
dengan jurnal aktual, replay dan penolakan atomik. Jangan menghilangkan
penolakan pecahan atau membulatkan biaya per pcs tanpa implementasi proyeksi
yang tepat dan bukti terhadap Native aktual. Belum ada tes tambahan tersebut
yang dijalankan; backend/core tetap identik.

Counter internal sumber yang terpisah mengonfirmasi perbedaan tersebut dan
menambah kasus penting: lot biaya1,00/basis3, stok0/net terjual2/other-out1,
retur1 menghasilkan ΔFG+0,33, ΔCOGS−0,34, Δother+0,01. Jadi mengganti scalar
HPP saja sambil memaksakan dua baris FG/COGS bernilai sama juga tidak cukup.
Dua lot biaya1,00/basis3 masing-masing stok2/net terjual1, retur1 per lot:
satu PO menghasilkan ΔFG+0,67/ΔCOGS−0,67, tetapi satu produk non-PO
menghasilkan +0,66/−0,66. Menghitung delta alokasi PO masing-masing dari
keadaan before yang sama akan salah menjadi0,68.

Counter menyampaikan kontrol matematika rasional, bukan eksekusi database.
Seluruh kasus pecahan itu masih ditolak. Fixture berikutnya harus membuat
HPP1,00/basis3 lewat writer Native yang sah, tanpa merekayasa HPP/jurnal.
FG lock, urutan lock lokasi/inventory/lot/current-HPP/PO-state, sumber dan
gudang, batas alokasi, stok/net sold, rekonsiliasi buku serta lineage konversi
yang sudah ada wajib dipertahankan.

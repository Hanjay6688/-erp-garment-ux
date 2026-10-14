# SG-02 — kain kembali ke gudang (keputusan owner D14-4)

Keputusan owner (15 Okt 2026): "Ya, masuk stok lagi (Disarankan)" — "Ada langkah 'kain kembali ke gudang': roll yang
sama masuk stok lagi beserta nilainya, biaya PO berkurang sebesar itu."

## Yang terjadi saat disimpan

1. Admin/owner membuka potongan yang sudah diposting di **Bagi Potongan → Catat kain kembali ke gudang**, mengisi
   jumlah per roll (paling banyak sisa yang dicatat saat potong), tanggal & jam kembali (WIB) dan alasan.
2. Server (`public.erp_cp7_return_cutting_fabric_v1` → `cp7_cutting_correction.return_command`) memeriksa ulang hak
   akses, versi potongan dan token tinjauan, lalu mencatat tiga fakta fisik pada roll potongan itu saja:
   `qty_physically_returned`, `return_destination='WAREHOUSE'`, `returned_at`. Hanya tiga kolom ini yang ditulis.
3. Lalu memanggil fungsi Native yang sudah diterima, **tanpa perubahan**, `erp.post_cutting_material_returns(group,
   gudang asal)`: gerakan stok `CUTTING_RETURN` untuk roll yang sama di gudang asal dengan harga saat dipotong,
   jurnal Dr `MATERIAL_INVENTORY` / Cr `WIP` untuk PO itu (biaya PO turun sebesar nilai itu), hitung ulang biaya
   bahan, dan bila PO sudah punya barang jadi, PO masuk antrean hitung ulang HPP (mekanisme Native yang sama).
4. Fungsi Native itu meminta izin "internal". Perintah memakai konteks eksekusi Native `POST_CUTTING` yang sama
   dengan posting potong Native (`erp.cutting_bridge_execution_context`), terikat ke proses, transaksi dan pengguna,
   dan hanya lolos bila pengguna itu sendiri punya izin `production.cutting.post`; konteks dihapus segera sesudahnya.

## Batas

- Sekali per potongan (aturan Native `material_return_posted`). Sesudah kain kembali, "buka potongan sebagai draft
  koreksi" juga tertutup (aturan Native yang sudah ada).
- Tanggal kembali tidak boleh sebelum waktu potong, tidak di masa depan, tidak di periode yang sudah ditutup.
- Jumlah > sisa yang dicatat saat potong ditolak; bila sisa memang lebih banyak, koreksi potongannya dulu.
- Belum ada pembalikan bila jumlah salah ketik (Native juga belum punya pembalik untuk ini).

## Bukti

- Kasus native (suite CP17): `CP17_SG02_RETURN_STOCK_VALUE_PO_COST`, `CP17_SG02_OVER_REMAINDER_REFUSED`,
  `CP17_SG02_ONCE_AND_SAME_REQUEST_REPLAY`, `CP17_SG02_BEFORE_CUT_OR_FUTURE_REFUSED`. Oracle dari gerakan stok, baris
  jurnal per PO dan baris roll, bukan dari fungsi yang diuji.
- Uji layar: `src/CuttingFabricReturnPanel.dom.test.tsx`, `src/cuttingReturnContract.test.ts`.

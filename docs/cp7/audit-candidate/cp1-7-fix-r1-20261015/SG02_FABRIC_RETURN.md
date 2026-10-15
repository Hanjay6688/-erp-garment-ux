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
- Pembalikan bila jumlahnya salah: lihat bagian "Batal / betulkan kain kembali (D14-10)" di bawah.

## Bukti

- Kasus native (suite CP17): `CP17_SG02_RETURN_STOCK_VALUE_PO_COST`, `CP17_SG02_OVER_REMAINDER_REFUSED`,
  `CP17_SG02_ONCE_AND_SAME_REQUEST_REPLAY`, `CP17_SG02_BEFORE_CUT_OR_FUTURE_REFUSED`. Oracle dari gerakan stok, baris
  jurnal per PO dan baris roll, bukan dari fungsi yang diuji.
- Uji layar: `src/CuttingFabricReturnPanel.dom.test.tsx`, `src/cuttingReturnContract.test.ts`.
- Browser HP (Auth dan PostgREST nyata): `CP17_BROWSER_SG02_FABRIC_RETURN_MOBILE` — 3,5 ditolak di layar (melebihi sisa 3),
  2 disimpan; stok roll naik 2, satu gerakan kembali, satu permintaan, halaman tidak lebih lebar dari layar.
  Run pertama gagal karena tabel roll membuat halaman 722 piksel di layar 412 piksel (ketukan meleset); tampilan
  dibetulkan di `src/connected-pickup.css`, oracle tidak diubah.

## Batal / betulkan kain kembali (keputusan owner D14-10)

Keputusan owner (15 Okt 2026, persis): "Ya, buat tombol batal/koreksi retur kain. Pembalikan stok, hutang/kredit,
jurnal, dan HPP yang terdampak harus selesai dalam satu transaksi, dengan riwayat asli tetap tersimpan. Kalau ada
transaksi lanjutan yang menghalangi, tampilkan bagian mana yang harus dibetulkan terlebih dahulu."

### Yang terjadi saat disimpan

Layar: **Bagi Potongan → Batal / betulkan kain kembali** (`src/CuttingFabricReturnReversalPanel.tsx`). Pilihan
"Batalkan saja" atau "Betulkan jumlahnya" (isi jumlah yang benar per roll), alasan, centang "sudah diperiksa".

Server: `public.erp_cp7_get_cutting_return_reversal_v1` (baca) dan `public.erp_cp7_reverse_cutting_return_v1`
(tulis) → `cp7_cutting_correction.return_reversal_workspace` / `return_reversal_command`. Dalam **satu transaksi**:

1. Jurnal kain kembali yang sudah diposting (`CUTTING_MATERIAL_RETURN_LINE`) dibalik lewat fungsi Native yang sudah
   diterima, **tanpa perubahan**, `erp.reverse_journal`: jurnal asli jadi `REVERSED`, jurnal pembalik
   `JOURNAL_REVERSAL` tertaut. Biaya PO (WIP) naik lagi sebesar nilai kain kembali.
2. Satu gerakan stok `REVERSAL` per gerakan `CUTTING_RETURN` yang masih aktif (`reversal_of_id`, sumber
   `CUTTING_GROUP_RETURN_REVERSAL`), ditulis seperti pembalik Native sebelum jahit. Pengaman Native tetap berlaku:
   satu pembalik per gerakan, urutan waktu (tidak sebelum gerakan asli), stok tidak boleh minus.
3. `erp.recalculate_material_cost` untuk bahan itu (Native; bila PO sudah punya barang jadi, PO masuk antrean hitung
   ulang HPP, mekanisme yang sama dengan kain kembali).
4. Fakta kembali di roll potongan dikosongkan dan tanda `material_return_posted` dibuka lagi.
5. Bila "Betulkan jumlahnya": jumlah yang benar langsung diposting lagi lewat jalur kain kembali yang sama
   (`post_return_rolls`, fungsi Native `erp.post_cutting_material_returns` tanpa perubahan), pada saat yang sama.
6. Hasil diperiksa ulang (jumlah gerakan aktif, nilai), lalu satu baris riwayat ditulis
   (`cp7_cutting_correction.return_reversal_history`, tidak bisa diubah/dihapus).

"Hutang/kredit": kain kembali tidak pernah menyentuh hutang supplier (jurnalnya hanya persediaan ↔ WIP), jadi tidak
ada hutang/kredit yang dibalik. Ini dibuktikan kasus (baris hutang supplier tidak berubah).

Riwayat asli tetap: gerakan `CUTTING_RETURN` asli, jurnal asli (status `REVERSED`), permintaan asli dan baris riwayat
kain kembali tidak dihapus atau diubah.

### Penghalang (ditampilkan di layar, perintah menolak)

- **LATER_USE**: kain yang sudah kembali dari roll itu sudah dipakai lagi (gerakan keluar dari roll yang sama sesudah
  kain kembali, mis. potongan lain). Layar menyebut nomor dokumennya, jumlah, jam, dan sisa di gudang sekarang:
  "Betulkan dulu: CUT-xxx …". Sesudah dokumen itu dibetulkan, batal bisa dilakukan.
- **PERIOD_CLOSED**: periode hari ini sudah ditutup.
- **NOT_RETURNED**: belum ada kain kembali yang aktif (mis. sudah dibatalkan).

### Batas yang perlu diketahui

- Pembatalan dan pembetulan **bertanggal saat disimpan**, sama seperti pembalik Native lain (`erp.reverse_journal`
  memakai tanggal hari itu). Akibatnya, untuk hari-hari di antara kain kembali yang salah dan pembetulannya, laporan per
  tanggal tetap menunjukkan angka lama; angka yang benar berlaku sejak pembetulan. Angka lama tetap terlihat di riwayat.
- Sekali kirim dengan nomor permintaan yang sama = satu hasil (kirim ulang mengembalikan jawaban yang sama). Token
  tinjauan basi ditolak.

### Bukti

- Kasus native: `CP17_SG02_CANCEL_RETURN_RESTORES_STOCK_GL_COST`, `CP17_SG02_CORRECT_RETURN_ONE_TRANSACTION`,
  `CP17_SG02_CANCEL_BLOCKED_BY_LATER_USE` (potongan lain memakai sisa roll → batal ditolak dan menyebut potongan itu;
  sesudah potongan itu dibuka lagi, batal berhasil), `CP17_SG02_CANCEL_REPLAY_ONCE_STALE`. Oracle dari gerakan stok,
  baris jurnal per PO, status jurnal dan baris roll.
- Uji layar: `src/CuttingFabricReturnReversalPanel.dom.test.tsx` (batal, betulkan, penghalang disebut, jawaban untuk
  potongan lain ditolak).
- Browser desktop (Auth dan PostgREST nyata): `CP17_BROWSER_SG02_FABRIC_RETURN_CORRECT_DESKTOP` — catat 2, buka lagi,
  "Betulkan jumlahnya", 3,5 ditolak di layar, 3 disimpan; stok roll naik 3, satu kain kembali aktif, riwayat 1.

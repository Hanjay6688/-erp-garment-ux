# OW-08b butir 2.21 — koreksi barang jadi di QC

Tahap Native di atas tahap kasbon (`cp7_kasbon_source.composition`), karena keduanya mengubah pembaca sumber transaksi
`cp7_transaction_source.resolve(jsonb)`. Penjelasan untuk owner: `docs/cp7/d17-14/ow08/KOREKSI_FG_QC.md`.

- `fg_correction_source.sql`: skema privat `cp7_fg_correction_source` dengan dua pembaca penghalang batal QC (daftar dan
  kalimat), milik `postgres`, tanpa hak untuk peran API.
- `native_delta.py`: baris pembalik stok barang jadi dari penjualan, retur, penyesuaian stok dan rework dibuka ke dokumennya
  (keluarga lain tetap "sumber belum didukung"); penolakan `erp.reverse_qc` dan riwayat QC menyebut dokumen penghalang dan
  menu tempat membetulkannya, dengan syarat, kode dan kalimat pertama yang sama.
- `composition.py`: pasang, periksa 22 kelompok katalog, lepas sebelum dipakai mengembalikan pendahulu persis.
- `cases.py`: 9 kasus Native (dibandingkan dengan fungsi asli pada keadaan yang sama).
- Uji: `.github/workflows/cp7-ow08b-fg-correction-native.yml` (Native9).

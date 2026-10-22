# OW-08b butir 2.18 — jurnal kasbon dibuka dari buku besar

Tahap Native di atas produk OW-06 (`cp7_supplier_transfer.composition`), karena keduanya mengubah pembaca sumber
transaksi `cp7_transaction_source.resolve(jsonb)`.

- `kasbon_source.sql`: skema privat `cp7_kasbon_source` dengan satu pembaca dokumen kasbon, hanya untuk peran pembaca
  sumber transaksi.
- `native_delta.py`: lima substitusi terhitung pada pembaca sumber (jenis `CP7_KASBON` → domain KASBON, rute Payroll &
  Kasbon; hanya OWNER/ADMIN seperti panel kasbon; nomor dan status kasbon; fokus ke mandornya). Butuh penanda OW-06 dan
  menolak bila sudah terpasang.
- `composition.py`: pasang, periksa 22 kelompok katalog, lepas sebelum dipakai mengembalikan pendahulu persis.
- `cases.py`: 4 kasus Native — jurnal beri kasbon membuka kasbon (pembaca lama: sumber belum didukung); jurnal balik saat
  kasbon dibatalkan membuka kasbon yang sama berstatus batal; kasbon tak dikenal dan peran non-OWNER/ADMIN ditolak;
  semua jenis sumber jurnal lain menjawab sama dengan pembaca OW-06 asli.
- Uji: `.github/workflows/cp7-ow08b-kasbon-native.yml` (Native4). Layar: `src/ConnectedPayrollPage.tsx` membuka panel
  kasbon mandor itu dan menandai baris kasbonnya.

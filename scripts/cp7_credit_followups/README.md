# OW-04b bagian 3–4 — penolakan kredit menyebut alasan; penjaga kas refund; batal bersamaan

Tahap Native di atas produk OW-05 (`cp7_contractor_correction.composition`). SQL dasar tidak diubah. Penjelasan untuk owner:
`docs/cp7/d17-14/ow04/OW04B.md`.

- `followups.sql`: skema privat `cp7_credit_followups` (milik `postgres`) dengan empat fungsi alasan penolakan.
- `native_delta.py`: tiga penolakan kredit yang dipertahankan (syarat, urutan, SQLSTATE dan pesan sama) mendapat `DETAIL`
  kontrak `cp7.credit-followups.refusal.v1` (jenis, aksi, alasan, dokumen penghalang); layar menampilkannya sebagai alasan dan
  langkah berikutnya.
- `cases.py`: 9 kasus Native + 3 balapan (refund dari kas kosong, dana sesudah tanggal refund, refund konsumen, dua orang
  membatalkan pemakaian kredit yang sama). Uji: `.github/workflows/cp7-ow04b-native.yml`.

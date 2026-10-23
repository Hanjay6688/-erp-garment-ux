# OW-04b bagian A — bayar sisa tagihan sesudah kredit pelanggan dipakai

Tahap Native di atas `cp7_credit_followups` (tahap OW-04b bagian 3–4). SQL dasar tidak diubah. Rancangan:
`docs/cp7/d17-14/ow04/OW04B_MULTI_COHORT_DESIGN.md`; penjelasan untuk owner: `docs/cp7/d17-14/ow04/OW04B.md`.

- `remaining.sql`: skema privat `cp7_credit_remaining` (milik `postgres`, tanpa hak API) dengan dua fungsi penerimaan.
- `native_delta.py`: tiga penggantian terhitung pada `cp7_credit.native_source_enter` dan `cp7_credit.source_request_enter_v1`:
  pembayaran biasa (dan pembaliknya) pada invoice yang hanya menerima kredit masuk diterima lewat kait yang sudah ada, yang
  membuktikan tidak ada kelebihan bayar di setiap pasangan tanggal sebelum dan sesudah pembayaran; kohort atau keluarga
  retur milik invoice itu sendiri tetap ditolak.
- `composition.py`: pasang di atas followups, 22 kelompok katalog, lepas sebelum dipakai mengembalikan definisi followups persis.
- `cases.py`: 6 kasus Native + 2 balapan. Uji: `.github/workflows/cp7-ow04b-remaining-native.yml`.

# OW-09 — urut, saring dan cari seluruh hasil di 8 daftar

Tahap Native di atas tahap OW-12a (`cp7_finance_capture.composition`), langkah 8 rantai OW-15 (OW05, OW06, kasbon,
fgqc, OW05b, OW08a, OW12a, lalu OW-09); tidak ada tahap di bawahnya yang mengubah delapan pembaca ini. SQL dasar `scripts/cp7-src` tidak diubah
(dibekukan, E25j2). Penjelasan untuk owner: `docs/cp7/d17-14/ow09/README.md`.

- `native_delta.py`: penggantian terhitung pada 8 pembaca yang terpasang (`cp7_finance.analysis`, `cp7_sales.cash_workspace`,
  `cp7_sales.return_workspace`, `cp7_payroll.note_workspace`, `cp7_fg.adjust_workspace`, `cp7_fg.corrected_ledger`,
  `cp7_material.count_workspace`, `erp.get_accessory_issue_workspace_v1`): kunci opsional urutan/status/jenis/cari dipakai
  sebelum halaman dipotong; panggilan lama tanpa kunci itu menjawab sama persis.
- `composition.py`: pasang sebagai pemilik terverifikasi tiap pembaca, 22 kelompok katalog, lepas sebelum dipakai mengembalikan
  definisi asli persis.
- `cases.py`: 8 kasus Native (Native8), masing-masing dengan pembanding panggilan lama terhadap definisi asli.
- Uji: `.github/workflows/cp7-ow09-native.yml`. Layar yang memakai kunci baru baru digabung sesudah Native8 lulus.

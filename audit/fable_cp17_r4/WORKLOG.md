# Fable r4 — log kerja

## CP1 — kandidat dan persiapan (2026-10-19)
- `git diff --name-only 663f6fae origin/claude/new-session-deapao` (kepala 5eda90e1): 9 berkas, semua `docs/`. Tree
  `src`, `scripts`, `supabase` kandidat = kepala.
- `git diff --name-only b53b5acd 663f6fae -- supabase`: kosong.
- Cabang `audit/fable-cp1-7-r4-663f6fae-20261019` dari kunci r3 2033fdfc; workflow Fable diarahkan ke kandidat r4.

## CP2a — oracle baru sebelum run (2026-10-19)
`audit/fable_cp7/scenarios/fable_r4_probes.py` (oracle di docstring, ditulis sebelum run):
- `FABLE_R4:GUARD_SAME_ANSWER_MATRIX` — coba patahkan klaim R4-05 "jawaban sama": penjaga terpasang vs penjaga yang sama
  tanpa probe (dibangun ulang Fable dari badan terpasang, atribut SECURITY/config, pemilik dan hak EXECUTE disamakan),
  tiap jawaban di transaksi baru pada koneksi kedua sebagai sesi Data API. Matriks: semua peran aplikasi aktif di
  `erp.app_users`, pengguna nonaktif bila ada, pengguna tak dikenal, JWT tanpa sub, anon, service_role × FRESH (tanpa id
  transaksi), XID, baris konteks penjualan/pengadaan transaksi ini, baris konteks yang di-commit transaksi sebelumnya di
  backend yang sama. Beda jawaban di sel mana pun → COUNTEREXAMPLE.
- `FABLE_R4:FG_REVERSAL_PATHS` — bahan baca (INFO, bukan vonis) untuk R4-02: bentuk gerakan FG di data, semua fungsi yang
  menulis `erp.fg_stock_movements`, dan apakah tabel sendiri menolak pembalik dari pembalik. Pertanyaannya: apakah ada jalur
  Native yang membuat gerakan keluar yang membalik pemasukan positif, padahal pemasukan itu sendiri mengimbangi pemakaian
  (pembalik dari pembalik, atau retur yang menunjuk ke gerakan SALE). Kalau ada, aturan R4-02 bisa menyembunyikan pemakaian
  aktif.
- R4-Q1 (sumber): `wait_recorded` hanya menunggu; nilai baliknya diabaikan dan run dinilai seperti sebelumnya (minimal satu
  run selesai, semua run berhasil). Syarat lulus tidak berubah (INDEPENDENT_SOURCE_REVIEW).

# Kandidat pengembangan retur lunas

Ini pekerjaan writer internal, bukan audit independen atau fitur yang telah
diterima. Produk WA yang telah terbukti adalah9b323f13; OW-04 tetap BELUM SELESAI.

Kandidat SQL sumber, ledger, refund, pembaca dan koordinator dikomposisikan
secara atomik hanya oleh `scripts/cp7_ow04_probe.py` di database sekali pakai.
Default installer produk tidak berubah. Tidak ada pemasangan di Enteng.
Deklarasi32 kasus ada di `NATIVE_INITIAL_QUALIFICATION.json`:12 kasus baru
CREDIT/REFUND,11 kasus retur lama,8 kasus pembaca/sumber Native lama, dan E01.
Semua expected keuangan, tanggal, pengulangan, izin dan pemulihan tetap ketat.

Hasil SQL terpisah dan DOM tidak boleh disebut hasil Native. Sampai run baru
benar-benar selesai, status Native adalah BELUM DIJALANKAN/DIKUALIFIKASI.
Sumber dan konfigurasi kandidat harus dibaca dari commit/run hasil tersebut.

Blokir kontrak yang tetap terbuka meskipun32 kasus nanti lulus:

- Cabang Native langsung tanpa partisipasi kredit mempertahankan perilaku
  lama, tetapi belum mencatat keluarga EMPTY baru. Jalur ini memerlukan
  operasi teknis Native yang terikat pada returnID pertama, tanpa memalsukan
  request atau konteks CP7. Ini belum memenuhi seluruh kontrak registrasi.
- Rekonsiliasi keluarga yang pernah dikoreksi, beberapa cohort, kredit APPLY,
  dan mutasi lanjutan cohort masih ditolak secara tertutup. Tidak boleh
  menganggap12 kasus pertama sebagai penerimaan seluruh siklus koreksi.
- Parent UI baru belum digabung ke alur aktif. Uji transaksi utuh HTTP,
  browser, race, hak dicabut, dan pemulihan setelah gangguan belum terbukti.

Counter yang sudah diperbaiki sebelum Native: tinjauan akun UUID sama dengan
hash baru, urutan hash akun refund, bypass pembaca kredit lama, dan serialisasi
hash berbeda zona waktu. Bukti awal tetap tersimpan dalam paket proposal.

`feature_complete:false`, `audit_complete:false`, `production_go:false`.

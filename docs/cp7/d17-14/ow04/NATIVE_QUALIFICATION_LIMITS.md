# Kandidat pengembangan retur lunas

Ini pekerjaan writer internal, bukan audit independen atau fitur yang telah
diterima. Produk WA yang telah terbukti adalah9b323f13; OW-04 tetap BELUM SELESAI.

Kandidat SQL sumber, ledger, refund, pembaca dan koordinator dikomposisikan
secara atomik hanya oleh `scripts/cp7_ow04_probe.py` di database sekali pakai.
Default installer produk tidak berubah. Tidak ada pemasangan di Enteng.
Deklarasi32 kasus ada di `NATIVE_INITIAL_QUALIFICATION.json`:12 kasus baru
CREDIT/REFUND,11 kasus retur lama,8 kasus pembaca/sumber Native lama, dan E01.
Semua expected keuangan, tanggal, pengulangan, izin dan pemulihan tetap ketat.

Hasil SQL terpisah dan DOM tidak boleh disebut hasil Native. Dua percobaan
awal belum menjalankan kasus: c0a63312 gagal memuat dependensi jsonschema,
f6a05315 lolos pemuatan dan bootstrap tetapi ditolak komposer karena asumsi
daftar konteks yang salah. Kedua hasil pertama disimpan pada CI_C0_FIRST_FAILURE
dan CI_F6_FIRST_FAILURE. Status Native tetap BELUM TERKUALIFIKASI; nol kasus
bukan PASS produk. Sumber dan konfigurasi harus dibaca dari commit/run hasilnya.

Sebelum percobaan berikutnya,12 fixture baru juga diperkuat dengan
`SET CONSTRAINTS ALL IMMEDIATE` sebelum rollback internal. Ini memaksa semua
FK tertunda dan trigger penutupan fakta berjalan; bukan bukti COMMIT nyata
atau pemulihan setelah gangguan. Expected finansial dan32 ID kasus tidak berubah.

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

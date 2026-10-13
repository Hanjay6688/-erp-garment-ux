# ASR-OPS-01 — kepemilikan scratch backup diikat ke OID (perbaikan writer, 13 Okt 2026)

Temuan: Astra, retest `7a0b4a90`, `audit/astra_retest_20261013/ASR_OPS_01.md` (commit audit `41dbd14d`), kasus
`ASD-B05-REPLACED_LEFTOVER`, run 38354577233 job 115154354639. Status di sisi writer: **diperbaiki, menunggu uji
ulang auditor**. `production_go:false`.

## Yang berubah

Kandidat: `85e171688de2038dfd8a1ee85cb0e2b143ffea58` (tree `08f3423a`). Di antara kode yang dipasang, hanya
`scripts/cp7_nightly_backup.py` yang berubah dari `7a0b4a90`. `supabase/`, `src/` dan `scripts/cp7-src/` identik:
`git diff --name-only 7a0b4a90 85e17168 -- supabase src scripts/cp7-src` kosong.

| Berkas | Isi |
|---|---|
| `scripts/cp7_nightly_backup.py` | Kepemilikan scratch diikat ke OID database, bukan ke nama (rincian di bawah) |
| `scripts/cp7_k3_cleanup_cases.py`, `docs/cp7/k3/K3_CLEANUP.json`, `scripts/cp7_f05_analysis_probe.py`, `.github/workflows/claude-p19-transport.yml` | Kasus balapan ke-11 `K3C_RACE_BACKUP_SCRATCH_OWNERSHIP_BY_OID`, suite `k3-cleanup-24` (24 kasus) |
| `.github/workflows/cp7-nightly-backup.yml` | Komentar saja (nama suite) |

## Rancangan

1. Setiap percobaan memulihkan dump ke database miliknya sendiri, `<scratch>_<16 hex acak>`. OID database itu
   dipilih alat sendiri lewat `CREATE DATABASE ... OID` (PostgreSQL 15+), jadi identitasnya sudah diketahui sebelum
   pihak lain bisa menyentuhnya. Tandanya (komentar database) memuat token percobaan dan OID tersebut. Tanda hanya
   dihitung milik alat pada database yang OID-nya sama dengan yang tertulis di tanda.
2. Nama `--scratch` yang dikonfigurasi hanya diperiksa, tidak pernah dipakai untuk memulihkan dump. Database yang
   memegang nama itu tetap ditolak seperti sebelumnya:
   - tanpa tanda sejak awal → `BACKUP_SCRATCH_EXISTS_NOT_OURS`;
   - muncul sesudah pemeriksaan → `BACKUP_SCRATCH_NOT_CREATED`.
3. Penghapusan hanya lewat OID (`drop_owned`). Urutannya:
   - cari nama database itu saat ini lewat OID-nya;
   - pastikan tandanya masih tanda alat;
   - akhiri sesi yang tersambung ke OID itu;
   - pindahkan database ke nama acak baru, lalu cek OID-nya sekali lagi;
   - baru setelah itu `DROP`.

   Kalau nama itu ternyata sudah menunjuk ke database lain, database tersebut dikembalikan ke namanya dan hasilnya
   `REPLACED`. `Tools.drop` dan `Tools.create`, yang bekerja berdasarkan nama, sudah dihapus.
4. Sisa malam sebelumnya ikut dibersihkan, dengan aturan berikut:
   - yang dihitung sisa: database bernama `--scratch` atau `<scratch>_<acak>` yang bertanda untuk OID-nya sendiri;
   - OID-nya dibaca sebelum dump, lalu dihapus dengan OID yang sama sesudah dump;
   - kalau nama itu tidak lagi menunjuk ke OID tersebut, malam itu ditolak dengan `BACKUP_SCRATCH_REPLACED`: tidak ada
     yang dihapus, diverifikasi, atau dipangkas.
5. OID database percobaan dicek sebelum dan sesudah `pg_restore`. Koneksi untuk menghitung hash juga memeriksa OID
   database tempat ia tersambung. Kalau ada perubahan, malam itu dicatat `BACKUP_SCRATCH_REPLACED` dan tidak
   terverifikasi.
6. `finally` hanya menghapus database milik percobaan itu, berdasarkan OID dan token. Tidak ada penghapusan berdasarkan
   nama.

**Batas operasional yang dinyatakan (bukan dianggap disetujui).** Ada satu celah yang masih mungkin. Seorang admin
database bisa melihat daftar database saat backup berjalan, lalu sengaja mengganti database percobaan (nama acaknya)
tepat di antara pengecekan OID dan saat `pg_restore` tersambung. Kalau itu terjadi, tabel hasil restore bisa masuk ke
database pengganti. Database pengganti itu tidak dihapus, dan malam itu dicatat tidak terverifikasi. Celah ini ikut
hilang kalau pemeriksaan pemulihan dipindah ke mesin GitHub, bukan di server database (pertanyaan 3 di
`docs/cp7/BACKUP_DESTINATION_PROPOSAL_20261013.md`). Owner yang memutuskan.

## Bukti

| Bukti | Hasil |
|---|---|
| CI: `K3C_RACE_BACKUP_SCRATCH_OWNERSHIP_BY_OID` dan empat kasus backup K3 lama di `k3-cleanup-24` | diisi setelah run selesai (`CI_RECEIPT.md`) |
| Lokal PG16 (bukan bukti, kontrol penulis): logika `ASD-B01..B05` Astra dengan oracle yang sama, alat baru | 5/5 PASS |
| Lokal PG16, kontrol sensitivitas: kasus yang sama pada alat `7a0b4a90` | B01–B04 PASS, **B05 COUNTEREXAMPLE** (sama dengan temuan Astra) |
| Lokal PG16: database percobaan diganti sebelum restore / sebelum hapus akhir; sisa berpola nama | 3/3 PASS |
| Lokal PG16: lima kasus backup K3 (`NIGHTLY_BACKUP_VERIFIED`, `RETRY_SAME_SECOND`, `SCRATCH_NEVER_DROPS_ANOTHER_DATABASE`, `VERIFIED_UNDER_WRITES`, `SCRATCH_OWNERSHIP_BY_OID`) | 5/5 PASS |

Kasus Astra (`audit/astra_retest_20261013/cases_delta.py`) hanya memakai `backup()`, `scratch_state(admin, name)`,
`mark_scratch(admin, name)` dan `Tools.dump`. Keempatnya masih ada dengan perilaku yang sama untuk pemanggilan itu,
jadi kasusnya bisa dijalankan ulang tanpa diubah. Hal yang sama berlaku untuk kasus Fable
`FABLE_CORE:BACKUP_SCRATCH_DROPS_FOREIGN_DB` dan `BACKUP_VERIFY_UNDER_LIVE_WRITES`, yang hanya memanggil `backup()`.

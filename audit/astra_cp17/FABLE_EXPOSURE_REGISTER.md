# Paparan Fable — izin owner 14 Oktober 2026

Pada 2026-10-14 13:50:45 WIB (06:50:45 UTC), owner mengubah batas blind audit:

> cheat sheet lu boleh intip fable sekarang karena kuota dia habis, tugas lu tetep jalan independen tambahin temuan dia juga ya, jangan mau disetir tp, cuma bantu rekap temuan karen cooldown masih jauh

Izin ini berlaku untuk membaca dan merekap pekerjaan Fable putaran CP1–CP7.
Vonis Astra tetap memerlukan sumber dan bukti yang diperiksa Astra. Tidak ada
klaim blind discovery untuk kasus yang dirancang setelah melihat petunjuk Fable.

## Materi yang diterima

- Pesan owner: Fable mengklaim 53 run, termasuk G-01 baseline fingerprint. Ini
  belum diverifikasi Astra sebagai 53 eksekusi atau 53 kelulusan.
- Pesan owner: CP3/3.5 memiliki 12 dugaan statis, dengan tiga contoh: periode
  kolam biaya absensi bertumpang tindih; absensi dibayar lewat nota lain;
  pembayaran payroll sebelum akrual. Ketiganya berstatus LEAD_UNVERIFIED.
- Pesan owner: lima review lain masih berjalan. Tidak ada hasilnya dalam pesan.
- Branch Fable `audit/fable-cp1-7-0b7049d9-20261014` pada commit
  `31cf30090b712897714f35c5a507cd1cd48c5d04`: dibaca
  `audit/fable_cp17/MANIFEST.md` (blob bcdf2dd4291061160fa0e6168386c5d6faa5ff7f)
  dan `REGISTER_RUNS.md` (blob e50390e4f5745fa25b3c4a5fddb4c253f7126547).
  Belum ada laporan review atau daftar run terperinci dalam direktori CP17
  pada commit tersebut. Inventaris tree bukan bukti isi file sudah direview.

## Pekerjaan Astra sebelum paparan

Gelombang native 31 suite: commit adf0c7d2e9918708095ca0d3818d5a20f8456252,
run 38522545215. Gelombang baseline tiga fase: commit
794bdb402b3c3ef64a3e5e49819e6a509e4aac9a, run 38523724159.
Manifest, fixture dan oracle sudah dikunci sebelum menerima petunjuk Fable.
Oracle lama Astra yang disalin dari e800e016 juga mendahului petunjuk tersebut.

CP1 tetap mencakup baseline/fingerprint/riwayat migrasi. CP2 lama sebelum
v2.6.10 tidak dapat diberi PASS tanpa set pemulihan dan bukti restore yang
sesuai. Bukti restore sintetis CP6/CP7 tidak menggantikan bukti CP2 historis.

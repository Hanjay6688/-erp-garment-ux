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
  pembayaran payroll sebelum akrual. Pada saat diterima, ketiganya LEAD_UNVERIFIED; hasil pemeriksaan Astra ada di bawah.
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

## Rekap hasil independen setelah paparan

| Petunjuk Fable | Bukti Astra | Disposisi |
|---|---|---|
| Pembayaran payroll mendahului akrual | PAY-04 dan PAY-05 pada run38525930407; PAY-06 pada run38527771239, respons public RPC dan laporan tanggal cutoff | TERBUKTI: satu akar masalah ASTRA-CP17-FIN-01, S0; tiga saksi runtime, kontrol sah juga PASS |
| Absensi yang sudah dibayar/di-approve dimasukkan nota lain | PAY-02-PAID-SOURCE dan PAY-03-APPROVED-SOURCE, run38525930407 | TIDAK TERBUKTI pada dua jalur ini: server menolak period overlap; bukan pembebasan semua kemungkinan jalur |
| Dua kolam HPP mengambil biaya absensi yang sama lewat periode bertumpang tindih | HPP-01-OVERLAPPING-SOURCE, run38527771239 | TIDAK TERBUKTI pada saksi ini: kolam kedua tanpa payroll exact-period ditolak. Sumber biaya identik tidak teralokasi dua kali; bukan bukti bahwa semua overlap mustahil |
| CP2 tanpa bukti restore | Receipt writer CP2_ENCRYPTED_RECOVERY.json dibaca, bukan ciphertext atau kunci | ADA receipt pembukaan arsip149 anggota, tetapi restore database historis tetap tidak dapat diverifikasi |

Sembilan dugaan lain dari klaim12, lima review yang belum selesai, dan daftar53 run tidak tersedia dalam materi yang diterima atau kedua file pada commit Fable tersebut. Tidak dihitung sebagai temuan/kelulusan Astra. Hasil Fable tambahan, bila kelak tersedia, harus ditambahkan sebagai addendum dengan asal bukti; tidak boleh ditulis mundur sebagai penemuan blind Astra.

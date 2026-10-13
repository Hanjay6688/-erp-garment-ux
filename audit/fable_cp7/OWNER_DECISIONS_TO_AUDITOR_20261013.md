# Register keputusan owner — disampaikan langsung ke auditor Fable

Dicatat oleh Fable (auditor independen) pada **2026-10-13T05:53:51Z** (13 Oct 2026 12:53 WIB), dalam sesi audit CP7 kandidat `7a0b4a90`.
Sumber: pesan owner kepada auditor, dikutip verbatim di bawah. Register kanonik proyek tetap
`docs/cp7/OWNER_DECISIONS_20261008.md` di cabang penulis; auditor tidak menulis ke cabang itu, jadi penulis
menyalin butir di bawah ke register kanonik tanpa mengubah kata-katanya dan merujuk berkas ini sebagai sumber.

Status label: keputusan 12 Oktober yang sebelumnya dikutip penulis berpindah dari UNVERIFIED_OWNER_DECISION menjadi
**OWNER_CONFIRMED_TO_AUDITOR** per butir 1 di bawah.

## Keputusan 13 Oktober 2026 (penegasan waktu: 2026-10-13T05:53:51Z)

| No | Keputusan owner (verbatim) | Konsekuensi untuk audit |
|---|---|---|
| D13-1 | "Ya, tegaskan keputusan 12 Oktober: dashboard disembunyikan sesuai cakupan keputusan tersebut; perubahan kebijakan PL-5 hanya oleh owner. Admin tetap boleh melihat. Catat waktu penegasan sekarang." | F-UI-01 ditutup dengan dasar keputusan yang sudah ditegaskan; PL-5: tulis = OWNER saja, baca = ADMIN tetap boleh (kasus Fable `HTTP_PL5_POLICY_OWNER_ONLY` sudah memeriksa tulis; baca ADMIN diperiksa di kasus penulis `pl5-history-yield-20`). |
| D13-2 | "Ya, terima `7a0b4a90` sebagai dasar pembekuan bersyarat. Pencatatan selisih, tiga run bayar supplier, dan verifikasi auditor atas hasilnya harus selesai sebelum pembekuan final." | Vonis Fable LULUS DENGAN SYARAT diterima owner. Syarat §3.1 laporan uji ulang menjadi prasyarat pembekuan final. Laporan v1.1 Fable menunggu hasil penulis. |
| D13-3 | "Ya, tunda izin pemasangan jadwal dan backup malam sampai nama database tujuan yang persis serta lokasi dump di luar mesin database ditetapkan. Penulis siapkan usulan lokasi dan cara pemulihannya untuk saya pilih." | Tidak ada pemasangan pg_cron atau backup malam di database mana pun selain salinan sekali pakai. Daftar periksa pemasangan disusun auditor setelah owner memilih. |

## Instruksi owner kepada penulis (dicatat agar auditor tahu apa yang akan dibaca)

1. "Tambahkan diagnosis selisih pemeriksaan akhir, lalu jalankan workflow bayar supplier tiga kali pada tree yang sama. Laporkan SHA/tree, seluruh hasil termasuk kegagalan, dan akar penyebabnya. Tiga run hijau saja belum menjelaskan penyebab kegagalan sebelumnya."
2. "Gladi jadwal di salinan sekali pakai CI dengan deklarasi 01:00 WIB, cocokkan `schedules()` dengan K3, lalu uninstall dan buktikan pemulihannya. Hosted tetap tidak disentuh."

## Instruksi owner kepada auditor

- Baca hasil kedua pekerjaan itu, terbitkan laporan v1.1. Tidak perlu menjalankan ulang audit sekarang. Kalau penyebab teknis masih belum terjelaskan, tetap catat OPEN.
- Setelah tujuan database dan lokasi dump diputuskan, lanjutkan daftar periksa pemasangan serta backup pertama.
- `production_go:false` sampai penerimaan dan izin pemasangan final.

## Yang akan dibaca auditor untuk v1.1 (agar penulis tahu bentuk bukti yang diperlukan)

| Pekerjaan | Bukti yang dibaca Fable | Dinilai dengan |
|---|---|---|
| Diagnosis selisih akhir grup | diff `cp6_auditor_runner.py` (kunci snapshot yang berbeda dicatat ke log JSON dan laporan), SHA commit | review sumber: pencatatan tidak boleh mengubah hasil pemeriksaan, hanya menambah detail |
| 3 run bayar supplier | run id, head SHA, tree produk, log per kasus, baris akhir grup dengan selisih (bila ada) | tree harus sama dengan 7a0b4a90 (`05d4ccd8`) atau selisih dijelaskan; 10 kasus per run; akar penyebab harus menjelaskan kegagalan run 38288829388 dan 38330557862 |
| Gladi jadwal | run id, log `cp7_schedule.py install --installation-approved` di salinan, `schedules()` vs deklarasi K3, `cron.job` sebelum/sesudah, uninstall `--removal-approved`, bukti database kembali ke keadaan awal | tidak ada koneksi ke hosted; nama database salinan tercatat; perbandingan K3 identik |

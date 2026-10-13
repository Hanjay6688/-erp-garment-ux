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

## Keputusan 13 Oktober 2026, sesudah laporan v1.1 putaran silang 1 (penegasan waktu: 2026-10-13T16:30:49Z, 13 Oct 2026 23:30 WIB)

Sumber: pesan owner kepada auditor, verbatim. Penulis menyalin ke register kanonik tanpa mengubah kata-kata.

| No | Keputusan owner (verbatim) | Konsekuensi untuk audit |
|---|---|---|
| D13-10 | "Ya, A2 diterima sebagai bukan penghalang pembekuan, dengan diagnosis tetap terpasang. Status akar penyebab tetap OPEN, dan dua kegagalan lama beserta bukti aslinya tetap disimpan." | A2 = keterbatasan terbuka yang tercantum, bukan syarat pembekuan. Log gagal pertama run 38288829388 dan 38330557862 tetap bukti asli; tidak dilabel ulang. |
| D13-11 | "Saya izinkan pembanding terurut sebagai pelengkap diagnosis. Pembanding asli tetap menentukan hasil pemeriksaan. Pelengkap harus mempertahankan semua anggota, duplikat, definisi, owner, dan hak akses; tujuannya membedakan perubahan urutan dari perubahan isi, tanpa menyamarkan kegagalan." | Fable memeriksa di putaran 2: pelengkap tidak memengaruhi `complete_boundary_restored`; multiset anggota (termasuk duplikat), definisi, owner, ACL tetap dibandingkan; hanya menambah klasifikasi ORDER_ONLY/CONTENT. |
| D13-12 | Putaran 2 penulis: (1) "A6: tambahkan kasus browser sungguhan P11 desktop dan HP yang menekan 'Terapkan lusin baris N'. Periksa hasil qty, pemeliharaan baris lain, serta hasil simpan/baca ulang. Pensiun `SALES_MANUAL_13` baru sah setelah auditor menyatakan cakupan penggantinya LENGKAP." (2) "F-OPS-05: hanya tanda kepemilikan dengan OID yang cocok boleh mengizinkan penghapusan. Tambahkan uji tanda lama disalin ke database asing: database itu harus tetap utuh." | Fable menilai LENGKAP/TIDAK LENGKAP untuk A6 dengan kasus browser Fable sendiri bila perlu; F-OPS-05 diuji ulang dengan `XC1:PLAIN_MARK_COPIED_ONTO_FOREIGN` tanpa mengubah oracle (harus PASS). |
| D13-13 | "Simpan bukti pertama, catat SHA/tree setiap hasil, lalu kirim kandidat putaran 2 yang sama ke Astra dan Fable. Pembekuan final mengikuti penutupan dua butir tersebut; A2 tetap tercantum sebagai keterbatasan terbuka. `production_go:false`." | Pembekuan final = A6 LENGKAP + F-OPS-05 DITUTUP oleh auditor. Kandidat putaran 2 harus satu SHA/tree yang sama untuk kedua auditor. |

## Yang akan dibaca Fable di putaran 2

| Butir | Bukti | Dinilai dengan |
|---|---|---|
| A6 | kasus browser P11 desktop + HP (skrip, log per kasus, tangkapan layar): isi "Lusin invoice N" dan "Sisa PCS invoice N", tekan "Terapkan lusin baris N", qty baris = lusin×12 + sisa, baris lain tidak berubah, simpan, baca ulang dari server = yang disimpan; tidak ada overflow horizontal di HP | run Fable sendiri atas workflow penulis + review sumber kasus; bila perlu kasus browser Fable di `fable_cp7_ui.mjs` |
| F-OPS-05 | diff `cp7_nightly_backup.py` (`is_mark` tanpa cabang tanda polos), kasus penulis "tanda lama disalin ke database asing tetap utuh" | `XC1:PLAIN_MARK_COPIED_ONTO_FOREIGN` harus PASS; 4 kasus XC1 lain dan 2 kasus backup core tetap PASS; k3-cleanup PASS |
| D13-11 | diff pembanding pelengkap di `cp6_auditor_runner.py`/`cp6_auditor_difference.py` | pembanding asli tidak berubah; pelengkap hanya menulis klasifikasi; multiset lengkap |

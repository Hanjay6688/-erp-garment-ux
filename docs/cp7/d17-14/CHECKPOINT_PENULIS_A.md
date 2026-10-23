# Checkpoint penulis A (cabang `claude/d17-14-uang`)

Aturan owner 22 Okt 2026: "update pake perlahan pake checkpoint ... biar kalo token abis ga sayang", lalu: "selagi masih banyak
ya lu pake banyak orang gapapa, kalo udah tipis lu baru slowing down ... jangan tiba tiba di stop". Jadi: setiap langkah selesai
langsung di-commit dan di-push dan berkas ini diperbarui; selama kuota banyak boleh banyak pembantu; pembantu yang sudah jalan
tidak dihentikan; baru diperlambat bila kuota menipis. Owner: yang dilihat kuota 5 jam (bila habis semua langsung berhenti).
Sisa kuota tidak terlihat dari sesi, jadi patokannya jam: jendela sekarang mulai sekitar 20.00 UTC 22 Okt, habis sekitar
01.00 UTC 23 Okt. Hitungan dari layar Usage Bos (03.35 WIB): sesi 47% terpakai, reset 4 jam 25 menit lagi (01.00 UTC);
laju sekitar 1,3% per menit dengan 4–5 pembantu, jadi habis sekitar 21.15 UTC. Patokan mode hemat: sekitar 80% terpakai.
Owner: jangan mulai pembantu baru bila tidak yakin selesai sebelum kuota habis (boleh selesai di dalam mode hemat). Mode hemat
jendela berikutnya sekitar 2 jam 20 menit sebelum reset (pengingat 03.50 UTC). Kuota mingguan boleh habis sebelum reset Kamis
29 Okt 00.59 WIB; perkiraan habis Senin 27 Okt pagi; pengingat serah terima ke Astra Minggu 26 Okt 11.40 UTC (18.40 WIB).
Pengingat terjadwal: 20.58 UTC mode hemat (tidak memulai pekerjaan besar baru, gabung dan push semua commit
pembantu, perbarui berkas ini), 01.10 UTC jalan normal lagi.

Diperbarui: 23 Okt 2026, 02.00 UTC (09.00 WIB). Jendela kuota baru mulai sekitar 01.12 UTC, reset sekitar 06.12 UTC; mode hemat
sekitar 03.50 UTC. Satu dispatch OW-12a (39882795647): database sudah menyala lagi (registry melayani); gagal di langkah kasus, log sedang dibaca.
Antrean ulang: wash, fgqc, OW06 browser, OW05b browser (`ciqueue-after-reset.log`). OW04b dan OW-09 menunggu push non-skip
untuk mendaftarkan workflow-nya saat antrean longgar.

## Sudah terbukti (uji database penuh atau browser lulus)

| Butir | Bukti |
|---|---|
| OW-05b petunjuk koreksi mandor | Native6 6/6 `176dcf38` (`ow05/native6-176dcf38-pass.json`); browser 2/2 `eda58db5` |
| OW-06 hak akses transfer supplier | Auth4 4/4 `b9456b5a` |
| OW-06 layar transfer supplier | Browser2 2/2 `d8b0164e` (run 39884070148; `ow06/browser2-d8b0164e-pass.json`) |
| OW-07 tutup buku menunggu HPP | Native7 7/7 (`ow07/PROGRESS.md`) |
| OW-08b 2.21 koreksi barang jadi di QC | Native9 9/9 `048f194e` (run 39884816533; `ow08/fgqc-native9-048f194e-pass.json`) |
| OW-05b layar ulang | Browser2 2/2 `8438a4a7` (run 39884456248; `ow05/browser2-8438a4a7-pass.json`) |
| OW-09 tahap daftar (8 pembaca) | Native8 8/8 `559ac537` (run 39885622953; `ow09/native8-559ac537-pass.json`); layar ditahan sampai rantai OW-15 (`ow09/screens/`) |
| OW-04b bagian 3–4 | Native9+Race3 12/12 `e9b88564` (run 39885599854; `ow04/ow04b-native9-race3-e9b88564-pass.json`) |
| OW-04b bagian A bayar sisa sesudah kredit | Native6+Race2 8/8 `33115188` (run 39885477424; `ow04/ow04b-slice-a-native6-race2-33115188-pass.json`) |
| OW-12a modul angka keuangan | Native7 7/7 `efa800cd` (run 39886155240; `ow12/native7-efa800cd-pass.json`) |
| OW-08b 2.20 cuci gagal tanpa tarif | Native11 11/11 `efa800cd` (run 39886298512; `ow08/wash-native11-efa800cd-pass.json`) |
| OW-08b 2.18 kasbon dari buku besar | Native4 4/4 `6c8be6f6` (run 39847032024; `ow08/kasbon-native4-6c8be6f6-pass.json`, laporan sha256 `8f9f2c83…`, artifak 12456785458) |

## Sudah dibuat, uji sedang/akan jalan

| Butir | Keadaan |
|---|---|

## Belum selesai / berikutnya (urutan kerja)

1. Catat hasil tiga run di atas (lulus: berkas bukti; gagal: simpan kegagalan pertama, betulkan).
2. OW-08b 2.21 koreksi barang jadi di QC: digabung (`5be35e60`), Native9 dikirim di `2927dd25`; browser OW-05b dan OW-06 diulang
   karena `src/transactionSource.ts` berubah (diantrekan).
3. OW-04b: bagian 3–4 dan A lulus (lihat tabel). Bagian B (retur kedua) besar, 16–24 jam: daftar 11 titik di
   `ow04/OW04B_SLICE_B_INVENTORY.md`; langkah 1 (fungsi before-events/snapshot per keluarga + pengganti cek zero-excess + local
   check) sedang dikerjakan pembantu di `claude/d17-14-ow04b`. C–E menyusul; D dan E menunggu 3 keputusan Bos.
4. OW-09: tahap `scripts/cp7_ow09_lists/` (8 pembaca termasuk aksesori, Native8, workflow `cp7-ow09-native.yml`) sudah
   di cabang ini (`15fb2a69`, `00385161`), belum pernah jalan di CI (daftarkan dengan push non-skip, sesudah login ghcr bila
   uji coba OW-12a berhasil). Bagian layar (`d8cd1960`, `2a0a6fb4`) masih di cabang lokal `claude/d17-14-ow09-stage`; digabung
   hanya sesudah Native8 lulus, karena layar baru mengirim kunci yang ditolak pembaca dasar tanpa tahap ini. Sisa: README
   `ow09/README.md`, cek F04/F05 gagal di base (`cp7_analysis_native.rounded_suggestion` tidak ada, area B), `check-*.mjs`.
5. Penggabungan harian 17.00 WIB 23 Okt ke `astra/d17-14-integrasi` (pengingat terjadwal 09.35 UTC). Pembanding vitest: base
   50 gagal/2102, gabungan uji 50 gagal/2146, tidak ada kegagalan baru; ke-50 itu uji `tests/cp7/families` yang menolak root.
6. OW-15: rencana `ow15/RENCANA_OW15.md`. Langkah 4 lulus: fgqc Native9 9/9 di `903b1879` mengakui laporan kasbon Native4
   (`ow08/fgqc-native9-903b1879-pass.json`; laporan sha256 `56d3294f…`, artifak 12472787961). Langkah 5 (OW05b di atas fgqc) dikerjakan.
   Berikutnya langkah 5 (OW05b di atas fgqc) dst., satu tahap per run.

## Antrean uji yang ditahan (registry image menolak unduhan sejak sekitar 20.20 UTC)

Semua run baru berhenti di "Start disposable database" (ghcr.io `toomanyrequests`, public.ecr.aws `Data limit exceeded`):
OW12a Native7 (39847548230 dua kali), wash Native11 (39849752268), fgqc Native9 (39850804753), OW06 Browser2 (39850343966).
Antrean dihentikan supaya jatah unduh tidak makin habis. Uji coba login ghcr.io di workflow OW-12a dikirim di `ab63c4c1`
(skrip `scratchpad/ghcr_login.py`). Hasil run 39854094236: `Login Succeeded`, tetapi ghcr.io tetap `toomanyrequests ... allowed:
44000/minute` dan public.ecr.aws tetap `Data limit exceeded`; login tidak menolong (batasnya di sisi registry), jadi tidak
dipasang ke workflow lain. Sesudah reset, coba satu dispatch dulu; bila start database lulus, kirim ulang berurutan:  OW12a, wash, fgqc, OW04b (daftarkan dengan push non-skip), OW06 browser,
OW05b browser bila run 39851046496 juga gagal.

## Serah terima untuk Astra (keadaan 23 Okt 04.00 WIB)

- Terbukti di database penuh/browser: OW-05b (Native6 6/6, browser 2/2), OW-06 hak akses (Auth4 4/4) dan mesin (Native10),
  OW-07 (Native7 7/7), OW-08a (Native6 6/6), OW-08b 2.18 kasbon (Native4 lulus `6c8be6f6`).
- Dibuat, belum lulus karena registry image menolak unduhan (bukan kode): OW-12a, OW-08b 2.20 cuci gagal, OW-08b 2.21 koreksi QC,
  OW-06 browser, OW-05b browser ulang. OW-04b bagian 3–4 dibuat, workflow belum pernah jalan.
- Belum: OW-04b bagian 1–2 (multi-kohort kredit); OW-09 (dibangun ulang sebagai tahap, cabang lokal `claude/d17-14-ow09`);
  2.19 piutang vendor laundry (menunggu Bos); OW-15 rantai (rencana `ow15/RENCANA_OW15.md`).
- Untuk B: 9 berkas `scripts/cp7-src` di `astra/d17-14-produksi` harus kembali ke byte beku dan perubahannya jadi tahap
  (permintaan di `KOORDINASI.md`, E25j2). Sampai itu cabang B tidak digabung ke integrasi apa adanya.
- Cabang lokal pembantu yang belum di-push (hanya di mesin ini): `claude/d17-14-ow09-stage` (bagian layar OW-09).
  Semua cabang pembantu lain sudah digabung ke `claude/d17-14-uang`.

## Menunggu Bos

- 2.19 kelebihan bayar laundry: dicatat piutang ke vendor itu, dipotong tagihan berikutnya atau ditutup pengembalian tunai — ya/tidak.
- Biaya absensi periode tanpa hasil jahit: A = beban periode itu, B = dibawa ke periode berikutnya yang ada jahitan.

## Cara melanjutkan bila sesi putus

- Worktree kerja: `/home/user/wt-uang` (cabang `claude/d17-14-uang`); semua yang tercatat di atas sudah di-push.
- Cabang pembantu yang belum di-push hanya ada di mesin ini (`.claude/worktrees/agent-*`); bila hilang, butir 2–4 dikerjakan ulang.

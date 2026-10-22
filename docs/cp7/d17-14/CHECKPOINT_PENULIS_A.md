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

Diperbarui: 22 Okt 2026, 21.00 UTC (23 Okt 04.00 WIB), mode hemat.

## Sudah terbukti (uji database penuh atau browser lulus)

| Butir | Bukti |
|---|---|
| OW-05b petunjuk koreksi mandor | Native6 6/6 `176dcf38` (`ow05/native6-176dcf38-pass.json`); browser 2/2 `eda58db5` |
| OW-06 hak akses transfer supplier | Auth4 4/4 `b9456b5a` |
| OW-07 tutup buku menunggu HPP | Native7 7/7 (`ow07/PROGRESS.md`) |
| OW-08b 2.18 kasbon dari buku besar | Native4 lulus di `6c8be6f6` (run 39847032024); baris per kasus belum disalin |

## Sudah dibuat, uji sedang/akan jalan

| Butir | Keadaan |
|---|---|
| OW-12a modul angka keuangan | Native7 `47688e63` run 39847548230 berhenti dua kali di "Start disposable database": registry image menolak (ghcr.io `toomanyrequests`, public.ecr.aws `Data limit exceeded`), infrastruktur; dikirim ulang lewat antrean. Usul lanjutan: login ghcr.io dengan token run di workflow agar batas unduh lebih longgar |
| OW-08b 2.20 cuci gagal tanpa tarif | Native11 `3c3dea91` ditolak di penerimaan sumber karena OW-09 mengubah SQL dasar yang dibekukan (`ow08/wash-native11-3c3dea91-admission-failure.json`); diulang di `03242502` (run 39849752268) |
| OW-06 layar transfer supplier | Browser2 `3c3dea91` berhenti di pin `src/productionRecovery.ts`; pin diperbarui `ed4818b3`; diantrekan ulang sesudah cuci gagal |
| OW-09 urut/saring seluruh hasil | Gabungan pertama dibatalkan (`43452c27`): mengedit `scripts/cp7-src` yang dibekukan (E25j2). Pembantu membangun ulang sebagai satu tahap Native (7 pembaca + aksesori) di `claude/d17-14-ow09`; F03 combined run 39849124506 masih menguji versi lama, hasilnya hanya info |

## Belum selesai / berikutnya (urutan kerja)

1. Catat hasil tiga run di atas (lulus: berkas bukti; gagal: simpan kegagalan pertama, betulkan).
2. OW-08b 2.21 koreksi barang jadi di QC: digabung (`5be35e60`), Native9 dikirim di `2927dd25`; browser OW-05b dan OW-06 diulang
   karena `src/transactionSource.ts` berubah (diantrekan).
3. OW-04b retur berulang dengan kredit: bagian 3–4 digabung (`6ff98674`, tahap `scripts/cp7_credit_followups/`, workflow
   `cp7-ow04b-native.yml` belum pernah jalan; daftarkan dengan push non-skip yang menyentuh foldernya). Bagian 1–2 BELUM:
   retur kedua / retur pada invoice yang dibayar kredit, dan Edit retur / Benerin nota pada invoice berkredit; produk kredit
   OW04 dan semua pemeriksanya sengaja satu-kohort, perlu tahap multi-kohort dengan bukti (lihat `ow04/OW04B.md`). Juga celah
   lama: bayar sisa invoice yang sebagian dibayar kredit masih ditolak (sekarang dengan alasan jelas).
4. OW-09 layar ke-8 (Nota Ambil Aksesori): pembantu sedang membuat tahap Native untuk `erp.get_accessory_issue_workspace_v1`
   (offset, status, urutan, jumlah) di `claude/d17-14-ow09` (lokal).
5. Penggabungan harian 17.00 WIB 23 Okt ke `astra/d17-14-integrasi` (pengingat terjadwal 09.35 UTC). Pembanding vitest: base
   50 gagal/2102, gabungan uji 50 gagal/2146, tidak ada kegagalan baru; ke-50 itu uji `tests/cp7/families` yang menolak root.
6. OW-15: rantai linear tahap, P21 untuk OW-06/OW-08a, sambungan B untuk OW-12a. Pembantu perencana sedang menyusun rencana
   rinci (urutan tahap, tumpang tindih fungsi, pin yang harus dibuat ulang).

## Antrean uji yang ditahan (registry image menolak unduhan sejak sekitar 20.20 UTC)

Semua run baru berhenti di "Start disposable database" (ghcr.io `toomanyrequests`, public.ecr.aws `Data limit exceeded`):
OW12a Native7 (39847548230 dua kali), wash Native11 (39849752268), fgqc Native9 (39850804753), OW06 Browser2 (39850343966).
Antrean dihentikan supaya jatah unduh tidak makin habis. Sesudah reset: (1) login `docker login ghcr.io` dengan token run di
langkah start database pada workflow tahap yang BELUM lulus (OW12a, wash, fgqc, OW04b; workflow tahap yang sudah lulus jangan
diedit karena dikunci); (2) kirim ulang berurutan: OW12a, wash, fgqc, OW04b (daftarkan dengan push non-skip), OW06 browser,
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
- Cabang lokal pembantu yang belum di-push (hanya di mesin ini): `claude/d17-14-ow09` (OW-09 tahap, sedang dirapikan).
  Semua cabang pembantu lain sudah digabung ke `claude/d17-14-uang`.

## Menunggu Bos

- 2.19 kelebihan bayar laundry: dicatat piutang ke vendor itu, dipotong tagihan berikutnya atau ditutup pengembalian tunai — ya/tidak.
- Biaya absensi periode tanpa hasil jahit: A = beban periode itu, B = dibawa ke periode berikutnya yang ada jahitan.

## Cara melanjutkan bila sesi putus

- Worktree kerja: `/home/user/wt-uang` (cabang `claude/d17-14-uang`); semua yang tercatat di atas sudah di-push.
- Cabang pembantu yang belum di-push hanya ada di mesin ini (`.claude/worktrees/agent-*`); bila hilang, butir 2–4 dikerjakan ulang.

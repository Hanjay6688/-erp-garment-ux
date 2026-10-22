# Checkpoint penulis A (cabang `claude/d17-14-uang`)

Aturan owner 22 Okt 2026: "update pake perlahan pake checkpoint ... biar kalo token abis ga sayang." Jadi: kerja bertahap, setiap
langkah selesai langsung di-commit dan di-push, berkas ini diperbarui, paling banyak dua pembantu jalan bersamaan.

Diperbarui: 22 Okt 2026, 20.35 UTC (23 Okt 03.35 WIB).

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
| OW-12a modul angka keuangan | Native7 di `47688e63` (run 39847548230) sedang jalan; dua kegagalan pasang sebelumnya dicatat di `ow12/` |
| OW-08b 2.20 cuci gagal tanpa tarif | Native11 di `3c3dea91` (run 39848501244) sedang jalan |
| OW-06 layar transfer supplier | Browser2 di `3c3dea91` (run 39848539599) sedang jalan |
| OW-09 urut/saring seluruh hasil, 7 layar | Digabung (`24149f41`); 11 workflow diantrekan bertahap oleh `ciqueue.sh` (scratchpad) |

## Belum selesai / berikutnya (urutan kerja)

1. Catat hasil tiga run di atas (lulus: berkas bukti; gagal: simpan kegagalan pertama, betulkan).
2. OW-08b 2.21 koreksi barang jadi di QC: pembantu sedang bekerja di `claude/d17-14-ow08b-qc` (lokal).
3. OW-04b retur berulang dengan kredit: pembantu sedang bekerja di `claude/d17-14-ow04b` (lokal). Sesudah digabung, pin UI OW-04
   (`scripts/ow04-*/SOURCE.json`, `ACTIVE_UI_SOURCE.json`) harus diperbarui karena OW-09 mengubah `src/SalesReturnPanel.tsx`.
4. OW-09 layar ke-8 (Nota Ambil Aksesori): butuh tahap Native untuk `erp.get_accessory_issue_workspace_v1` (offset, status,
   urutan, jumlah). Ditunda sampai salah satu pembantu di atas selesai.
5. Penggabungan harian 17.00 WIB 23 Okt ke `astra/d17-14-integrasi` (pengingat terjadwal 09.35 UTC). Pembanding vitest: base
   50 gagal/2102, gabungan uji 50 gagal/2146, tidak ada kegagalan baru; ke-50 itu uji `tests/cp7/families` yang menolak root.
6. OW-15: rantai linear tahap, P21 untuk OW-06/OW-08a, sambungan B untuk OW-12a.

## Menunggu Bos

- 2.19 kelebihan bayar laundry: dicatat piutang ke vendor itu, dipotong tagihan berikutnya atau ditutup pengembalian tunai — ya/tidak.
- Biaya absensi periode tanpa hasil jahit: A = beban periode itu, B = dibawa ke periode berikutnya yang ada jahitan.

## Cara melanjutkan bila sesi putus

- Worktree kerja: `/home/user/wt-uang` (cabang `claude/d17-14-uang`); semua yang tercatat di atas sudah di-push.
- Cabang pembantu yang belum di-push hanya ada di mesin ini (`.claude/worktrees/agent-*`); bila hilang, butir 2–4 dikerjakan ulang.

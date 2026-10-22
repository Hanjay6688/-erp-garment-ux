# Koordinasi dua penulis D17-14

Dasar: `docs/cp7/PEMBAGIAN_DUA_PENULIS_20261022.md` versi 2 (owner D17-17). Penulis A = Claude (`claude/d17-14-uang`),
Penulis B = Astra (`astra/d17-14-produksi`). Cabang gabungan `astra/d17-14-integrasi` hanya dimajukan Claude.

## Cara pakai

- Butuh mengubah berkas milik penulis lain: tulis satu baris di bagian "Permintaan" (tanggal, butir, berkas, alasan,
  bentuk perubahan). Pemiliknya yang menulis, lalu mengisi kolom "Selesai".
- Mengubah berkas bersama (`src/App.tsx`, `package.json`/lock, `OPEN_WORK`, `OWNER_DECISIONS`, `ERP_BEST_PRACTICES`,
  `SELESAI_UNTUK_DIUJI`): commit kecil tersendiri berlabel `[bersama]` dan satu baris di bagian "Perubahan bersama".
- Kontrak antar-penulis (fungsi, nama objek, bentuk data) ditulis di bagian "Kontrak" sebelum dipakai pihak lain.
- Status harian 17.00 WIB: satu baris per penulis di bagian "Status harian".

## Kontrak

| Tanggal | Kontrak | Pemilik | Pemakai | Isi |
|---|---|---|---|---|
| 23 Okt 2026 | Modul angka keuangan/HPP untuk analisis (OW-12a) | A | B (OW-12b) | [`ow12/KONTRAK_OW12A.md`](ow12/KONTRAK_OW12A.md) (`cp7.finance-capture.v1`): start/step/status/result, hak OWNER/ADMIN + `finance.reports.view`, angka dari pembaca laporan resmi yang sama |

## Permintaan

| Tanggal | Butir | Dari → ke | Berkas | Alasan dan bentuk perubahan | Selesai |
|---|---|---|---|---|---|

## Perubahan bersama

| Tanggal | Penulis | Berkas | Commit | Ringkas |
|---|---|---|---|---|
| 23 Okt 2026 | A | `docs/cp7/OWNER_DECISIONS_20261008.md`, `AGENTS.md`, handoff | `2d625616` | D17-17 dicatat; pembagian versi 2 berlaku |

## Status harian

| Tanggal | Penulis | Status (bahasa sehari-hari) |
|---|---|---|
| 23 Okt 2026 | A | Perbaikan laporan sesudah saldo kredit pelanggan (OW-08a) sedang diuji otomatis; uji ulang OW-05 selesai dengan empat catatan tampilan |
| 23 Okt 2026 (malam) | A | OW-08a lulus uji otomatis 6/6. OW-07 (tutup buku tertahan bila kain kantong/pool absen belum dibagi, sisa WIP PO selesai ditutup) sedang diuji. OW-06: uji login asli dan uji layar desktop/HP sedang diuji |

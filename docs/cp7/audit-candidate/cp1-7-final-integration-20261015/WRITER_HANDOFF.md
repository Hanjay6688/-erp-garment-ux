# Serah-terima penulis (untuk penulis cadangan) — 15 Okt 2026

Ditulis penulis Claude agar penulis cadangan bisa meneruskan tanpa mengulang. Bukan bukti; bukti ada di run CI.

## Keadaan sekarang

- Cabang kerja `claude/new-session-deapao` = `6cf2b7f9fe3807ddba171b7a49d439a3205885fc` (fast-forward dari
  `claude/final-gaps-20261015`). Isi baru sejak kandidat r1 `66baa8e8`: D14-14 G1 (selesai jahit + upah mandor),
  G2 (selesaikan PO + HPP final), G3 (51 workflow lama dijalankan ulang, 3 data uji dibetulkan), D14-17 (pengganti
  arsip CI 10392910720 yang kedaluwarsa). Rincian dan batas: `GAPS_D14_14.md`.
- **Sedang berjalan:** kualifikasi satu commit di `6cf2b7f9`: 23 workflow dari push + 55 di-dispatch = 78 run
  (25 Q25 dari `../cp1-7-fix-r1-20261015/CI_RECEIPT.json`, 51 dari `2e16fcb4`, ditambah `cp7-group-end-diagnosis` dan
  `cp7-supabase-restore-drill` yang ikut terpicu push). Daftar run: `gh api "repos/Hanjay6688/-erp-garment-ux/actions/runs?head_sha=6cf2b7f9fe3807ddba171b7a49d439a3205885fc&per_page=100"`.
- Jangan push ke `claude/new-session-deapao` sampai 78 run selesai: push memicu run baru pada commit lain.

## Langkah berikutnya

1. Bila ada run merah: unduh log job lewat alat GitHub (bukan `gh api .../logs`, yang ditolak proxy), cari akar
   masalah, perbaiki di `claude/final-gaps-20261015`, uji workflow yang gagal di sana, lalu fast-forward lagi dan
   kualifikasi ulang seluruhnya pada satu commit. Jangan melonggarkan penjaga atau oracle; simpan log gagal.
2. Bila semua hijau: `python3 scripts/cp7_ci_receipt.py 6cf2b7f9fe3807ddba171b7a49d439a3205885fc <OUT>.json`,
   lalu siapkan **satu paket gabungan** (D14-16): uji ulang r1 (`../cp1-7-fix-r1-20261015/`) + audit akhir (folder ini),
   satu kandidat, kotak handoff Fable/Astra/Sol diperbarui ke commit baru. Paket belum dikirim; owner yang mengirim.
3. Laporan ke owner: bahasa sehari-hari, kalimat pertama apa yang beres dan apa yang belum (`CLAUDE.md`).

## Yang tidak boleh

Main, Cloudflare, Supabase hosted Enteng `siimvrusnzxexizpyoib`, legacy `vlxdhpkjeevubjxexnfo` tidak diubah. Tidak
mengirim pesan ke orang lain. Keputusan owner yang sudah ada tidak dibuka ulang (`docs/cp7/OWNER_DECISIONS_20261008.md`,
terakhir D14-17). `production_go:false`. Tanpa biaya.

## Arsip CI

Arsip CI disimpan 30 hari. 14 arsip yang dikunci workflow disalin ke artifact `11967162735` (sampai 13 Jan 2027).
Dua arsip F05 (`11139828865`, `11141076740`) habis 31 Okt; `cp7-f05-attention` masih mengunduh yang asli.

# Handoff uji pemulihan Supabase lokal (D13-8b) — sama untuk Astra dan Fable

Owner menyalin kotak pertama ke Astra dan kotak kedua ke Fable. Isinya sama, kecuali nama. Boleh dikirim bersama paket
alat backup v2 (`../offsite-backup-r1-20261013/HANDOFF.md`).

## Untuk Astra

```text
Kamu Astra, auditor independen CP7 ERP Garment. Repo Hanjay6688/-erp-garment-ux, cabang claude/new-session-deapao.
Ini paket uji silang UJI PEMULIHAN KE SUPABASE LOKAL (owner D13-8b). Paket yang sama dikirim ke Fable, dan kalian
menguji secara independen. Keputusan owner yang sudah disahkan tidak dibuka ulang.

KANDIDAT: bebf2dc5c7c4924c3578e62f3a1788e5a65b8fd7. Baca dulu
docs/cp7/audit-candidate/restore-drill-r1-20261013/README.md, lalu docs/cp7/evidence/restore-drill-20261013/CI_RECEIPT.md
dan D13-8 di docs/cp7/OWNER_DECISIONS_20261008.md.

YANG WAJIB DIPERIKSA
1. Pemilihan isi yang dipulihkan (select_toc): apakah ada objek aplikasi yang bisa tertinggal tanpa ketahuan, atau
   objek Supabase yang ikut tertimpa. Cobalah membuat counterexample.
2. Pengosongan hak bawaan postgres sebelum pemulihan (clear_default_privileges): benar, lengkap (per skema dan global),
   dan hak bawaan sumber kembali persis. Nilai juga apakah hasilnya bisa membuka akses yang di sumber tertutup.
3. Pembanding: data aplikasi + login, nomor urut, struktur seluruh database (pemilik, hak akses), perbedaan mentah
   tercatat. Pastikan tidak ada yang dilonggarkan dibanding alat backup.
4. Syarat target: role postgres bukan superuser, target baru, hash file. Tiga kasus tolak di workflow.
5. Batas yang dinyatakan: lokal ≠ hosted, butuh sumber hidup, pg_cron dan data Supabase lain tidak ikut. Nilai apakah
   batas itu lengkap dan jujur.
Boleh menjalankan .github/workflows/cp7-supabase-restore-drill.yml (workflow_dispatch) atau workflow sendiri di cabang
audit baru.

BATAS
- Jangan mengubah main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only) atau produksi. Jangan menyentuh Google Drive atau R2.
- Jangan push ke claude/new-session-deapao atau cp7/integration. Pakai cabang audit baru.
- Jangan mengirim pesan ke orang lain. Jangan meminta password, token atau kunci.
- Jangan melonggarkan oracle. Simpan log gagal pertama.
- production_go:false.

KIRIM BALIK: per butir 1-5: DITUTUP / MASIH TERBUKA / temuan baru (ID baru), dengan run + kasus + log gagal
pertama, dan commit laporan.
```

## Untuk Fable

```text
Kamu Fable, auditor independen CP7 ERP Garment. Repo Hanjay6688/-erp-garment-ux, cabang claude/new-session-deapao.
Ini paket uji silang UJI PEMULIHAN KE SUPABASE LOKAL (owner D13-8b). Paket yang sama dikirim ke Astra, dan kalian
menguji secara independen. Keputusan owner yang sudah disahkan tidak dibuka ulang.

KANDIDAT: bebf2dc5c7c4924c3578e62f3a1788e5a65b8fd7. Baca dulu
docs/cp7/audit-candidate/restore-drill-r1-20261013/README.md, lalu docs/cp7/evidence/restore-drill-20261013/CI_RECEIPT.md
dan D13-8 di docs/cp7/OWNER_DECISIONS_20261008.md.

YANG WAJIB DIPERIKSA
1. Pemilihan isi yang dipulihkan (select_toc): apakah ada objek aplikasi yang bisa tertinggal tanpa ketahuan, atau
   objek Supabase yang ikut tertimpa. Cobalah membuat counterexample.
2. Pengosongan hak bawaan postgres sebelum pemulihan (clear_default_privileges): benar, lengkap (per skema dan global),
   dan hak bawaan sumber kembali persis. Nilai juga apakah hasilnya bisa membuka akses yang di sumber tertutup.
3. Pembanding: data aplikasi + login, nomor urut, struktur seluruh database (pemilik, hak akses), perbedaan mentah
   tercatat. Pastikan tidak ada yang dilonggarkan dibanding alat backup.
4. Syarat target: role postgres bukan superuser, target baru, hash file. Tiga kasus tolak di workflow.
5. Batas yang dinyatakan: lokal ≠ hosted, butuh sumber hidup, pg_cron dan data Supabase lain tidak ikut. Nilai apakah
   batas itu lengkap dan jujur.
Boleh menjalankan .github/workflows/cp7-supabase-restore-drill.yml (workflow_dispatch) atau workflow sendiri di cabang
audit.

BATAS
- Jangan mengubah main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only) atau produksi. Jangan menyentuh Google Drive atau R2.
- Jangan push ke claude/new-session-deapao atau cp7/integration.
- Jangan mengirim pesan ke orang lain. Jangan meminta password, token atau kunci.
- Jangan melonggarkan oracle. Simpan log gagal pertama.
- production_go:false.

KIRIM BALIK: per butir 1-5: DITUTUP / MASIH TERBUKA / temuan baru (ID baru), dengan run + kasus + label bukti, dan
commit laporan.
```

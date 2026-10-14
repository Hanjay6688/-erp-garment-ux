# Addendum A2 laporan cp17 — restore independen CP2 (izin owner D14-1), 14 Okt 2026

Tidak menimpa laporan v1.0. Label: FABLE, tingkat bukti LOCAL (bukan image Supabase hosted).

## Sumber
Google Drive owner (konektor sesi, baca-saja): `ERP_ENTENG_CP2_ENCRYPTED_BACKUP_PACKAGE_20260831T193529Z.zip` (887 926 B), `ERP_ENTENG_CP2_RECOVERY_KEY_PACKAGE_20260831T193529Z.zip` (679 B), `ERP_ENTENG_CP2_FREE_LOCAL_RESTORE_PROOF_20260901.zip` (tidak dipakai).

## Langkah dan hasil
| Langkah | Hasil |
|---|---|
| sha256 file kunci vs repo | `6ed0dd8c…` = tercatat di paket dan di `review/R6` B — **cocok** |
| sha256 arsip terenkripsi vs manifest CP2 | `f4a7e060…` — **cocok** |
| Dekripsi AES-256-CBC, PBKDF2-HMAC-SHA256 600 000 iterasi (openssl, passphrase dari file kunci) | berhasil; sha256 arsip mentah `e176cac9…` = `raw.sha256` dan `cp2-export-validation.json` — **cocok** |
| `SHA256SUMS.json` set pemulihan | 148/148 file cocok |
| Generator restore asli `scripts/cp2_generate_catalog_restore.py` @ 41bda0f7 | menghasilkan SQL katalog/ledger/sequence seperti workflow asli |
| Restore ke **PostgreSQL 16.13 lokal sekali pakai** dengan pengganti minimal platform Supabase (`runs/cp12/cp2_local_pg16_stubs.sql`: peran anon/authenticated/service_role, skema auth/storage/cron/net/vault/extensions, `auth.uid()`/`auth.jwt()`, tabel `cron.job`); 5 baris `create extension` (supabase_vault, pg_cron, dan 3 ekstensi yang sudah dibuat stub) dilewati | katalog, data ERP, ledger platform, reseed sequence: semua `ON_ERROR_STOP` rc=0 |
| Verifier asli `scripts/cp2_verify_local_restore.py` @ 41bda0f7 | **PASS**: tabel 142, view 48, fungsi 436, trigger 383, index 419, constraint 944, policy 190, migrasi platform 55, migrasi aplikasi 41, cron 1, auth_users 0, app_users 0, baris erp 104; object/count/data mismatch kosong; ledger platform & aplikasi cocok; integrity findings/errors kosong. **Identik** dengan bukti penulis 1 Sep (run 33457299164). Laporan: `runs/cp12/cp2_local_restore_report_fable_20261014.json` |
| Objek storage `chatgpt-temp-erp-export/ERP_GARMENT_V2_6_0_COMPACT_ONE_SHOT.sql` | 1 084 146 B, sha256 `756a962d…` — **cocok**; tidak diunggah ulang ke storage (tidak ada layanan storage lokal) |
| Pembersihan | database lokal dihentikan dan dihapus; arsip mentah, set pemulihan, file kunci, dan unduhan Drive dihapus dari kontainer; tidak ada yang dikomit selain laporan verifier dan stub |

## Batas (jujur)
- Bukan image `supabase/postgres:17.6.1.165`: pull image diblokir kebijakan jaringan sesi (CDN ECR/GHCR 403, Docker Hub 429). Restore berjalan di PG16 dengan pengganti platform minimal; perilaku Auth/Storage/pg_cron nyata tidak diuji.
- Round-trip storage tidak diuji (hanya hash).
- **Insiden auditor:** saat memeriksa struktur file kunci, 40 dari 64 karakter passphrase CP2 tercetak di keluaran alat sesi Fable (tidak masuk repo, commit, CI, atau pesan ke owner). Anggap kunci CP2 terpapar ke log sesi ini.

## Dampak pada vonis
- **CP2: LULUS DENGAN SYARAT** (sebelumnya BELUM DIPERIKSA). Arsip, kunci, dan set pemulihan utuh dan dapat dipulihkan secara independen; hasil verifier identik dengan bukti penulis. Syarat: (1) restore pada image Supabase yang sama dengan hosted dilakukan saat jaringan mengizinkan (bagian CP7C/VPS); (2) owner memperlakukan passphrase CP2 sebagai terpapar — bila skema kunci yang sama dipakai untuk backup baru, buat kunci baru; arsip CP2 lama boleh dienkripsi ulang atau dibiarkan bila sudah tidak dibutuhkan.
- Catatan: CP2 adalah backup basis **31 Agustus (v2.6.11a)**, bukan basis kode final; untuk produksi, backup CP7C yang baru tetap diperlukan (D13-3).

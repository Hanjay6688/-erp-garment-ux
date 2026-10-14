# Bukti CP1 dan CP2 di pohon kandidat (FABLE-004)

Salinan byte-demi-byte, bukan tulisan ulang. Asal dan sha256 tiap berkas ada di `MANIFEST.json`.

| Berkas | Asal | Isi |
|---|---|---|
| `cp1_cp1_fingerprint.sql` | cabang `codex/cp1-revalidation-evidence-20260901`, `scripts/cp1_fingerprint.sql` | Algoritma `CP1_REVALIDATION_V1`, hanya SELECT. sha256 `943bf118…`, sama dengan yang dijalankan Fable ke hosted (addendum A1) |
| `cp1_checkpoint_1_*.json/.md` | cabang yang sama, `docs/evidence/2026-09-01/` | Hasil revalidasi CP1 tanggal 1 Sep (hash dan jumlah objek) |
| `cp2_cp2_generate_catalog_restore.py`, `cp2_cp2_verify_local_restore.py`, `cp2_cp2-free-local-restore.yml` | commit `41bda0f7` | Generator restore, verifier, dan workflow restore CP2 asli. Passphrase dibaca dari berkas kunci saat dijalankan; tidak ada nilai kunci di sini |

Tidak ada di repo, dan memang tidak boleh: arsip CP2 terenkripsi, berkas kunci, set pemulihan, dan baris data bisnis.
Hash arsip (terenkripsi `f4a7e060…`, hasil dekripsi `e176cac9…`) ada di `MANIFEST.json` dan
`docs/cp7/evidence/writer-resume-20261005/CP2_ENCRYPTED_RECOVERY.json`.

Workflow CP2 di folder ini hanya arsip, karena GitHub hanya menjalankan berkas di `.github/workflows`.

## Pemeriksaan independen yang sudah ada
- Fable, addendum A1 (`audit/fable-cp1-7-0b7049d9-20261014` @ `1224901f`): CP1 diukur ulang baca-saja di hosted.
  Hasilnya identik 16/16 dengan G-01.
- Fable, addendum A2 (@ `f24c71b8`): CP2 dipulihkan sendiri di PostgreSQL 16 lokal. Verifier asli PASS dan identik dengan
  bukti 1 Sep.
  - Syarat yang masih terbuka: (1) restore di image Supabase yang sama dengan hosted, masuk CP7C; (2) passphrase CP2
    dianggap terpapar di log sesi Fable, jadi backup baru memakai kunci baru (D13-3).
- Astra (`audit/astra-cp1-7-0b7049d9-20261014` @ `be1a5993`): `CP1_CP2_EVIDENCE_REVIEW.md`.

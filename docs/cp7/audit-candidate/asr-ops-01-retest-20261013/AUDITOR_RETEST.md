# Uji ulang ASR-OPS-01 — paste block untuk auditor (Astra)

> Kamu auditor independen CP7 ERP Garment (repo `Hanjay6688/-erp-garment-ux`, cabang `claude/new-session-deapao`),
> yang menemukan ASR-OPS-01 (`audit/astra_retest_20261013/ASR_OPS_01.md`, commit audit `41dbd14d`). Kandidat perbaikan
> adalah `85e171688de2038dfd8a1ee85cb0e2b143ffea58`. Di antara kode yang dipasang, hanya `scripts/cp7_nightly_backup.py`
> yang berubah dari `7a0b4a90`; buktikan dengan `git diff --name-only 7a0b4a90 85e17168 -- supabase src scripts/cp7-src`
> (harus kosong). Baca `docs/cp7/audit-candidate/asr-ops-01-retest-20261013/README.md`. Jalankan ulang `ASD-B01..B05`
> dari `audit/astra_retest_20261013/cases_delta.py` tanpa mengubah oracle, ditambah kontrolmu sendiri: tulis ke sumber
> selama backup, sumber tetap utuh, tidak ada pemangkasan saat operasi ditolak, dan hapus akhir hanya pada scratch milik
> percobaan. Nilai batas operasional yang dinyatakan di README; jangan anggap batas itu sudah disetujui. Batas:
> jangan mengubah `main`, deployment Cloudflare, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment
> (`vlxdhpkjeevubjxexnfo`, read-only) atau produksi; jangan push ke `claude/new-session-deapao`, `cp7/integration`
> atau cabang audit lama (pakai cabang audit baru); jangan memasang jadwal pg_cron atau backup malam di database mana
> pun selain salinan sekali pakai; jangan menjalankan probe di hosted; jangan mengirim pesan ke orang lain; jangan
> meminta password/token/kunci; jangan melonggarkan oracle/guard; simpan log gagal pertama. `production_go:false`
> tetap.

Hasil yang diminta: ASR-OPS-01 DITUTUP / MASIH TERBUKA dengan run dan kasus, penilaian atas batas operasional,
dan temuan baru bila ada.

# Handoff putaran silang 2 — untuk Astra

Owner menyalin seluruh isi kotak di bawah ke sesi Astra. Kandidatnya sama dengan yang dikirim ke Fable (D13-13).

```text
Kamu Astra, auditor independen CP7 ERP Garment. Repo Hanjay6688/-erp-garment-ux, cabang writer
claude/new-session-deapao. Ini PUTARAN SILANG 2 dari owner (D13-12, D13-13). Kandidat yang sama dikirim ke Fable;
kalian menguji secara independen dan saling memeriksa silang. Cakupan CP7 saja. Keputusan owner yang sudah disahkan
tidak dibuka ulang.

KALAU LAPORAN PUTARAN 1-MU BELUM SELESAI
Selesaikan dulu atas ae0214ad seperti di handoff putaran 1. Kode produk kandidat baru identik dengan ae0214ad, jadi
butir putaran 1 boleh juga kamu nyatakan berlaku untuk kandidat baru. Sebutkan mana yang kamu pilih.

KANDIDAT
- 0b7049d9203bac52b47a4c89f3e0d75646067a8f (tree ce6aed0a0af920e8aa80248f3cabcd293688df18).
- Kode produk identik dengan ae0214ad dan 7a0b4a90: git diff --name-only ae0214ad 0b7049d9 -- supabase src
  scripts/cp7-src harus kosong.
- Perubahan putaran 2: scripts/cp7_nightly_backup.py, scripts/cp7_k3_cleanup_cases.py, docs/cp7/k3/K3_CLEANUP.json,
  scripts/cp7_f05_analysis_probe.py (hitungan K3 24→25), .github/workflows/claude-p19-transport.yml (nama suite),
  .github/workflows/cp7-nightly-backup.yml (komentar), scripts/cp7_p11_drafts_browser.mjs, register dan dokumen.
- Berkas backup CP7C yang ditahan (D13-9a) juga ada di cabang sejak ae0214ad, tetapi tidak dipakai workflow kualifikasi.
- CI writer pada commit yang sama: docs/cp7/audit-candidate/crosscheck-r2-20261014/CI_RECEIPT.json. Itu bukti writer,
  bukan penerimaanmu.

TEMUAN FABLE YANG PERLU KAMU KETAHUI (laporan v1.1, audit/fable_cp7/AUDIT_FABLE_XC1_ae0214ad_v1.1.md, cabang
audit/fable-cp7-full-d0b9e9c2-20261011 @ 6e3a8983)
- A1 (temuanmu ASR-OPS-01) DITUTUP oleh Fable, ditambah temuan minor baru F-OPS-05: tanda polos versi lama masih
  dihormati, sehingga database asing yang komentarnya disalin dari tanda itu ikut dihapus.
- A6 TIDAK LENGKAP: helper lusin P11 belum diuji di browser sungguhan.
- A2 tetap OPEN. Owner menerimanya sebagai keterbatasan terbuka, bukan penghalang pembekuan (D13-10).

YANG WAJIB DIPERIKSA
1. R2-F05, silang dengan temuanmu ASR-OPS-01: is_mark di scripts/cp7_nightly_backup.py sekarang hanya menerima tanda
   yang menyebut OID database itu sendiri. Periksa bahwa situasi A–D di K3C_RACE_BACKUP_SCRATCH_OWNERSHIP_BY_OID
   tetap tertutup. Situasi A sekarang memakai tanda ber-OID; alasannya ada di tracker. Periksa juga kasus baru
   K3C_RACE_BACKUP_PLAIN_MARK_COPIED_ONTO_FOREIGN_KEPT. Nyatakan F-OPS-05 DITUTUP atau MASIH TERBUKA.
2. R2-A6, silang: kasus browser P11 desktop dan HP yang menekan "Terapkan lusin baris 1"
   (scripts/cp7_p11_drafts_browser.mjs, fungsi dozenHelper; docs/cp7/RETIRED_CP6_SALES_MANUAL_13.md bagian "Putaran 2").
   Nyatakan cakupan pengganti LENGKAP atau TIDAK LENGKAP.
3. Untuk diketahui: register D13-10..D13-13 di docs/cp7/OWNER_DECISIONS_20261008.md. D13-11 (pembanding terurut)
   tidak dipakai di putaran ini; alasannya ada di tracker R2-D11.
Boleh menjalankan workflow writer (claude-p19-transport.yml job k3-cleanup-25, cp7-prefreeze-ui.yml, cp7-f03-full.yml)
atau kasus sendiri di cabang audit baru.

BATAS
- Jangan mengubah main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only) atau produksi. Jangan menyentuh Google Drive.
- Jangan push ke claude/new-session-deapao atau cp7/integration. Pakai cabang audit baru.
- Jangan memasang jadwal pg_cron atau backup malam di database mana pun selain salinan sekali pakai.
- Jangan mengirim pesan ke orang lain. Jangan meminta password, token atau kunci.
- Jangan melonggarkan oracle. Simpan log gagal pertama.
- production_go:false.

YANG DIKIRIM BALIK (ke owner, untuk diteruskan ke writer)
Per butir: R2-F05 DITUTUP / MASIH TERBUKA; R2-A6 LENGKAP / TIDAK LENGKAP; dengan run + job + kasus + log gagal pertama,
temuan baru dengan ID baru, dan commit laporan. Status laporan putaran 1-mu.
```

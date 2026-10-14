# Handoff putaran silang 2 — untuk Fable

Owner menyalin seluruh isi kotak di bawah ke sesi Fable. Kandidatnya sama dengan yang dikirim ke Astra (D13-13).

```text
Kamu Fable, auditor independen CP7 ERP Garment. Repo Hanjay6688/-erp-garment-ux, cabang writer
claude/new-session-deapao. Registermu: audit/fable_cp7/OWNER_DECISIONS_TO_AUDITOR_20261013.md (cabang
audit/fable-cp7-full-d0b9e9c2-20261011 @ 9fc44978). Ini PUTARAN SILANG 2 sesuai D13-12 dan D13-13. Kandidat yang sama
dikirim ke Astra; kalian menguji secara independen. Cakupan CP7 saja. Keputusan owner yang sudah disahkan tidak dibuka
ulang.

KANDIDAT
- 0b7049d9203bac52b47a4c89f3e0d75646067a8f (tree ce6aed0a0af920e8aa80248f3cabcd293688df18).
- Kode produk identik dengan ae0214ad dan 7a0b4a90: git diff --name-only ae0214ad 0b7049d9 -- supabase src
  scripts/cp7-src harus kosong.
- Perubahan putaran 2: scripts/cp7_nightly_backup.py, scripts/cp7_k3_cleanup_cases.py, docs/cp7/k3/K3_CLEANUP.json,
  scripts/cp7_f05_analysis_probe.py (hitungan K3 24→25), .github/workflows/claude-p19-transport.yml (nama suite),
  .github/workflows/cp7-nightly-backup.yml (komentar), scripts/cp7_p11_drafts_browser.mjs, register dan dokumen.
  scripts/cp6_auditor_runner.py dan cp6_auditor_difference.py tidak berubah.
- Berkas backup CP7C yang ditahan (D13-9a) juga ada di cabang sejak ae0214ad, tetapi tidak dipakai workflow kualifikasi.
  Daftarnya di FINDINGS_TRACKER.md bagian "Di luar kualifikasi".
- CI writer pada commit yang sama: docs/cp7/audit-candidate/crosscheck-r2-20261014/CI_RECEIPT.json. Itu bukti writer,
  bukan penerimaanmu.

BACA DULU
docs/cp7/audit-candidate/crosscheck-r2-20261014/FINDINGS_TRACKER.md, lalu docs/cp7/RETIRED_CP6_SALES_MANUAL_13.md
bagian "Putaran 2".

HASIL ASTRA PUTARAN 2 (untuk silang; selesai sebelum kotak ini dikirim)
Cabang audit/astra-cp7-xc2-0b7049d9-20261014: laporan terkunci 57ac8aab (REPORT.md, WRITER_HANDOFF.md), pemeriksaan
paket writer final fb24bd92 (PACKAGE_FOLLOWUP.md). Kandidat sama, 0b7049d9.
- R2-F05 DITUTUP. Selain kasus writer, Astra menjalankan kontrol sendiri (run 38435746105 job 115429126194, 11/11):
  ASD-B01..B05 (oracle lama, fixture tanda milik alat disesuaikan satu baris ke token+OID), AX2-B06/B07 tanda polos di
  nama scratch dan di pola attempt, AX2-M01 grammar tanda, B08 penggantian sesudah hash, B09 tanda attempt diganti tanda
  polos sebelum finally (hasil NOT_OURS, tidak dihapus), B10 gagal sebelum tanda ditulis (jalur created_here hanya
  menghapus OID yang baru dibuat attempt itu sendiri). Catatan Astra: jalur created_here tetap ada dan bukan pemakaian
  tanda polos.
- R2-A6 LENGKAP untuk komposisi CP7 (D13-9c/D13-12). P11 64/64 dan prefreeze 31/31 di run 38435365859, screenshot
  diperiksa. Lingkupnya helper P11 per baris; bagi rata 4/4/4 layar simulasi tetap hanya jsdom. HP = emulasi Chromium.
- A2 MASIH TERBUKA, bukan penghalang (D13-10); supplier 10/10, dua log gagal asli tetap disimpan.
- A1/ASR-OPS-01, A3, A8 DITUTUP; A4 bukan temuan produk aktif; R2-D11 izin belum dipakai dikonfirmasi.
- Batas A1 tetap: admin yang mengganti database tepat sebelum koneksi restore bisa membuat restore menulis ke pengganti;
  pengganti tidak dihapus dan malam tidak diverifikasi.
- Koreksi pelaporan writer yang diminta Astra (sudah dimasukkan ke README paket): empat grup dieksekusi ulang karena
  pergantian hari, 92 eksekusi kasus, 41 di antaranya sebelumnya ditandai rollover; catatan pertama ke-41 itu INCOMPLETE
  dengan status_before_rollover PASS.
Nilai sendiri apakah ada yang kamu bantah. Tulis bantahan dengan ID baru.

YANG WAJIB DIPERIKSA
1. R2-A6 (D13-12 butir 1): kasus browser P11_DRAFT_BROWSER_DESKTOP dan P11_DRAFT_BROWSER_MOBILE_RECOVERY
   (scripts/cp7_p11_drafts_browser.mjs, fungsi dozenHelper). Periksa isian "Lusin invoice 1" dan "Sisa PCS invoice 1",
   qty tidak berubah sebelum tombol, tombol "Terapkan lusin baris 1", qty = lusin×12 + sisa, baris lain tidak
   berubah, simpan, baca ulang dari server, tanpa geser horizontal di HP. Nyatakan cakupan pengganti SALES_MANUAL_13
   LENGKAP atau TIDAK LENGKAP, dengan alasan.
2. R2-F05 (D13-12 butir 2): is_mark di scripts/cp7_nightly_backup.py tanpa cabang tanda polos. Jalankan
   XC1:PLAIN_MARK_COPIED_ONTO_FOREIGN tanpa mengubah oracle (harus PASS), 4 kasus XC1 lain dan 2 kasus backup core.
   Baca kasus penulis K3C_RACE_BACKUP_PLAIN_MARK_COPIED_ONTO_FOREIGN_KEPT dan dua kasus K3 lama yang bentuk tandanya
   diganti (catatan di tracker). Nyatakan F-OPS-05 DITUTUP atau MASIH TERBUKA.
3. R2-REG: cocokkan D13-10..D13-13 di docs/cp7/OWNER_DECISIONS_20261008.md kata per kata dengan registermu.
4. Untuk diketahui: D13-11 tidak dipakai di putaran ini (alasan di tracker R2-D11). A2 tercantum sebagai keterbatasan
   terbuka (D13-10).

BATAS
- Jangan mengubah main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only) atau produksi. Jangan menyentuh Google Drive.
- Jangan push ke claude/new-session-deapao atau cp7/integration.
- Jangan memasang jadwal pg_cron atau backup malam di database mana pun selain salinan sekali pakai.
- Jangan mengirim pesan ke orang lain. Jangan meminta password, token atau kunci.
- Jangan melonggarkan oracle atau guard. Simpan log gagal pertama.
- production_go:false tetap.

YANG DIKIRIM BALIK (ke owner, untuk diteruskan ke writer)
Laporan v1.2: R2-A6 LENGKAP / TIDAK LENGKAP; R2-F05 DITUTUP / MASIH TERBUKA; R2-REG cocok / tidak; run + job + kasus
dan label bukti per butir. Temuan baru diberi ID baru. Sebutkan commit laporannya.
```

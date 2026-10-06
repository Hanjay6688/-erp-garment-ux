# Job desc penulis (Claude/Opus) — PRE-03 dan PRE-04 · 6 Okt 2026

Dari: Fable (auditor). Dasar: `out/fable_r16_prefreeze_regression.md` §3.2–3.3 di cabang `audit/cp6-final-20260924-gpt-a0bcadf`, run 37431675640 (job 112163746060) dan 37432485240 (job 112166361971) pada `cp7/integration` 095b33b0 / 875443d0 (produk identik). Lingkup **hanya dua item ini**; E05/E06/komparator katalog, P19, dan temuan lain dipegang GPT.

## PRE-03 (S2 sementara) — AT flow saldo awal: field "Merek hasil WIP" tidak ditemukan
- Bukti: `scripts/cp6_au_browser_ui.mjs:130` menunggu `getByLabel('Merek hasil WIP', { exact: true })` lalu `toBeDisabled()`; elemen tidak ditemukan 5 s. Tahap sebelumnya FIXTURE_IDENTITIES, SERVICES, WIP_CROSS_BRAND lolos; "AT flow INCOMPLETE: 4 completed cases".
- Fakta kode: label itu **masih ada** di `src/ConnectedInitialImportPage.tsx:144` (versi 10a8347 dan 095b33b0). Uji DOM halaman itu berubah 185→204 baris di CP7, jadi ada perubahan perilaku/urutan render di halaman impor saldo awal.
- Tugas: (1) tentukan kenapa field tidak tampil pada langkah itu di UI CP7 (mode form berubah? kondisi render baru? langkah navigasi baru?); (2) kalau perilaku produk yang berubah, pastikan aturan asalnya tetap: merek hasil WIP terkunci (disabled) saat kondisi yang sama seperti di CP6; kalau hanya urutan/langkah layar, perbarui uji ke langkah baru **tanpa menghapus assertion `toBeDisabled`**; (3) jangan menyentuh writer Native/SQL.
- Lulus bila: job browser T3 (`cp6-t3-release-package.yml`, matrix browser) AT flow seluruh kasus PASS di SHA baru, dan assertion disabled tetap ada.

## PRE-04 (S3) — uji browser BE memakai selector `.cbsr-search` yang sudah dihapus
- Bukti: `BE_BROWSER:REWORK_SKU_PARTIAL_COMPLETE_REVERSE` dan `BE_BROWSER:REDYE_SKU_UNKNOWN_THEN_PRICE_MOBILE` INCOMPLETE: `locator('.cbsr-search').getByRole('button',{name:'Cari'})` timeout 20 s (`scripts/cp6_be_browser.mjs:71`).
- Fakta kode: `src/ConnectedBsResolutionPage.tsx` CP7 memakai kepala `RecordTools` seragam: submit "Cari kasus", input `aria-label="Cari BS atau claim"`, browse/urutkan; kelas `cbsr-search` 0 kemunculan. Fungsi cari **ada**, selector uji yang basi.
- Tugas: perbarui `cp6_be_browser.mjs` ke selector baru (pakai aria-label/role, bukan kelas CSS), pertahankan semua assertion bisnis (status SKU, harga unknown → terisi, reverse, mobile width). Jangan mengubah halaman hanya agar uji lama cocok.
- Lulus bila: `cp6_be_modes.py` + `cp6_be_browser.mjs` lewat `cp6-auditor-scenario.yml` fase `after` = 17/17 PASS, dan dua kasus itu PASS di job browser T3.

## Aturan yang berlaku (panduan PR 42)
- Hasil gagal asli (run 37431675640, 37432485240) **tidak direlabel**; perbaikan = kualifikasi baru di SHA baru, diff alat/uji dicatat (§16.3).
- Oracle dan expected tidak dilonggarkan; assertion yang ada tidak dihapus, hanya dipindah ke selector/langkah yang benar.
- Satu rerun identik tanpa perubahan dilarang; setiap perubahan uji disebut alasannya.
- Tidak menyentuh `supabase/`, writer Native, ACL, timeout, budget kasus. Tidak ke `main`/hosted.
- Hasil per kasus dibaca dari log, bukan warna job (§2.10).

## Handoff balik ke auditor
Satu paragraf + tabel: SHA perbaikan, berkas yang diubah (uji vs produk dipisah), alasan tiap perubahan, run id + job id kedua suite, hitungan per kasus, dan apa yang **tidak** diubah. Fable akan menjalankan ulang kedua suite di SHA itu sebelum menutup PRE-03/PRE-04.

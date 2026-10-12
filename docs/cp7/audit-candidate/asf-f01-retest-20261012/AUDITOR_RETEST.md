# Uji ulang ASF-F01 — kandidat `5f1506f4` (sesi auditor terpisah)

Dokumen ini untuk **auditor di sesi terpisah**, bukan writer. Audit penuh CP7 Astra atas `d0b9e9c2` memberi HOLD karena
ASF-F01 (S3, alat uji). Handoff auditor: "Berikan kandidat baru serta diff sempit dan run hasil perbaikan. Auditor
mengulang kasus yang terkena perubahan; tidak perlu meminta pembuktian ulang bagian produk yang tidak tersentuh tanpa
alasan konkret."

## Paste block untuk membuka sesi auditor

> Kamu auditor independen CP7 ERP Garment (repo `Hanjay6688/-erp-garment-ux`, cabang `claude/new-session-deapao`).
> Kandidat revisi adalah commit sumber `5f1506f41389d355536ad09784d0a2b4fa6e6e75` (tree
> `aedd8b2d8a0f6c59138837cbb463995014c692c7`), tercatat di `docs/cp7/audit-candidate/asf-f01-retest-20261012/CI_RECEIPT.json`.
> Uji commit itu, bukan HEAD lain; commit sesudahnya hanya dokumen — buktikan sendiri dengan
> `git diff --name-only 5f1506f4 HEAD` (semua harus di bawah `docs/`). Selisih dari `d0b9e9c2` yang diaudit hanya dua
> berkas alat uji (`SOURCE_DELTA.json`). Baca `docs/AUDIT_PANDUAN_PRO_MAX.md`, laporan dan handoff audit Astra di cabang
> `audit/astra-cp7-full-d0b9e9c2-20261012` (`audit/astra_full/REPORT.md`, `WRITER_HANDOFF.md`, `FINDINGS.json`), lalu
> `README.md` dan `AUDITOR_RETEST.md` di folder paket ini. Uji ulang ASF-F01 dengan kontrol auditor sendiri
> (`audit/astra_full/probe_business_day_new.py` dan kontrol tambahanmu) pada SHA revisi, lalu jalankan semua mode yang
> memakai helper (savepoint, balapan, HTTP, browser). Batas: jangan mengubah `main`, deployment Cloudflare, Supabase
> hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment (`vlxdhpkjeevubjxexnfo`, read-only) atau produksi; jangan
> push ke `claude/new-session-deapao`, `cp7/integration` atau cabang audit lama (pakai cabang audit baru); jangan memasang
> jadwal pg_cron atau backup malam di database mana pun selain salinan sekali pakai; jangan mengirim pesan ke orang lain;
> jangan meminta password/token/kunci; jangan melonggarkan oracle/guard; simpan log gagal pertama. Keputusan owner yang
> sudah disahkan tidak dibuka ulang. Area optimasi timeline PR44 tidak boleh diterima oleh auditor yang menulisnya.
> `production_go:false` tetap.

## Yang diuji ulang

| Temuan | Kriteria penutupan (handoff Astra) | Yang berubah di `5f1506f4` | Titik awal (bukan bukti lulus) |
|---|---|---|---|
| ASF-F01 S3 | Kontrol ASF-10/11 menahan satu percobaan dan status gagal; kontrol positif ASF-09 dan kelima kontrol ASF-12 tetap lulus; semua mode yang memakai helper dijalankan; first attempt disimpan; dijelaskan apakah bukti kandidat lama pernah terkena retry | `scripts/cp6_auditor_business_day.py` (`explained`, `retry_allowed`, `with_retry`); `scripts/cp6_auditor_business_day_test.py` | probe Astra 4/4 PASS di mesin writer (bukan bukti); uji Shell S0; regresi 15 workflow di `CI_RECEIPT.json`; penjelasan bukti lama di `README.md` |

## Regresi yang mungkin terdampak

- Setiap suite yang memakai runtime auditor (savepoint, balapan, HTTP, browser): seluruh 15 workflow kualifikasi
  dijalankan pada `5f1506f4`. Pada run tanpa pergantian tanggal, aturan baru tidak mengubah apa pun.
- Akibat yang disengaja: kelompok yang gagal di dalam kasus saat tanggal berganti (seperti kegagalan pertama attention284 di
  `8116800c`) tidak lagi diulang otomatis; hasilnya tetap untuk diperiksa orang.
- Area lain yang tidak disentuh `SOURCE_DELTA.json` boleh tidak diulang; tulis BELUM DIULANG, bukan LULUS.

## Hasil yang diminta

1. ASF-F01: DITUTUP / MASIH TERBUKA, dengan run, kontrol dan oracle auditor.
2. Regresi: LULUS / GAGAL / BELUM DIULANG, dengan alasan.
3. Temuan baru bila ada (ID, keparahan, reproduksi, bukti, dampak).
4. Vonis audit penuh CP7 sesudah perbaikan ini. Penerimaan area PR44 tetap memerlukan auditor yang tidak menulisnya.

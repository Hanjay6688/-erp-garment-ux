# Perbaikan ASF-F01 untuk uji ulang — 12 Okt 2026

Audit penuh CP7 Astra atas `d0b9e9c2` (cabang `audit/astra-cp7-full-d0b9e9c2-20261012`, `audit/astra_full/REPORT.md`,
`WRITER_HANDOFF.md`, draf PR #47) memberi putusan **HOLD** dengan satu temuan baru: **ASF-F01** (S3, OPEN_TOOLING) pada
alat uji. Paket ini adalah kandidat perbaikannya. Bukti writer (WRITER_CROSSCHECK), bukan penerimaan auditor.
`production_go:false`.

## Identitas

- **Commit sumber: `5f1506f41389d355536ad09784d0a2b4fa6e6e75`**, tree `aedd8b2d8a0f6c59138837cbb463995014c692c7`, cabang `claude/new-session-deapao`.
- Selisih dari `d0b9e9c2` yang diaudit: `SOURCE_DELTA.json` — 12 berkas, **2 bukan dokumen**:
  `scripts/cp6_auditor_business_day.py` dan `scripts/cp6_auditor_business_day_test.py`. Tidak ada kode produk, SQL,
  layar, oracle bisnis atau workflow yang berubah.

## Temuan dan perbaikannya

| | Isi |
|---|---|
| Temuan (Astra) | `explained()` menganggap baris yang *terjadi bersamaan* dengan pergantian tanggal WIB sebagai baris yang *disebabkan* pergantian tanggal. Akibatnya FAIL/COUNTEREXAMPLE yang tidak bergantung tanggal (10.001 ≠ 10.000 sen) ikut diulang, dan PASS percobaan kedua menjadi hasil utama. Percobaan pertama tetap tersimpan. Bukti: run 38159947839 (2 PASS + 2 COUNTEREXAMPLE). |
| Perbaikan | Kelompok hanya diulang bila **setiap** baris yang tidak PASS adalah PASS yang dijadikan INCOMPLETE oleh kontrol tanggal itu sendiri (`status_before_rollover=PASS`, error `AUDITOR_BUSINESS_DAY_ROLLOVER`). FAIL, COUNTEREXAMPLE atau INCOMPLETE dari kasusnya sendiri tetap satu percobaan dengan status aslinya, walaupun tanggal berganti di sekitarnya; baris `KEPT_FIRST_RESULT` di log menyebut kasus yang melewati pergantian tanggal agar diperiksa orang. Penolakan lain tidak berubah (pemeriksaan runtime, hasil rusak, error kelompok, kasus hilang, salinan tertinggal, cleanup gagal). Berlaku untuk keempat mode lewat `with_retry` (savepoint, balapan, HTTP, browser). |
| Akibat yang disengaja | Kegagalan pertama attention284 di `8116800c` (enam baris browser gagal di dalam kasus saat tanggal berganti) **tidak lagi diulang otomatis**; barisnya tetap INCOMPLETE bertanda pergantian tanggal untuk diperiksa orang. Uji replay-nya diubah mengikuti aturan baru. |
| Uji alat | `scripts/cp6_auditor_business_day_test.py` (24 uji): aturan baru, padanan kontrol ASF-09..12, dan pemanggil asli `strict_group`/`run_races`/`run_http`/`run_browser` dengan database palsu. Dijalankan di workflow CP7 Shell S0. Probe Astra `audit/astra_full/probe_business_day_new.py` tanpa diubah memberi 4/4 PASS di mesin writer (bukan bukti). |

## Apakah bukti lama pernah terkena retry ini

Pengulangan hanya mungkin bila tanggal WIB berganti selama satu kelompok berjalan. Kontrol tanggal pertama kali ada di
`af5e3941`. Sejak itu, 87 run workflow di cabang ini (11 Okt 2026 05:11–18:58 UTC) masing-masing mulai dan selesai pada
tanggal WIB yang sama, jadi tidak ada satu pun yang bisa memicu pengulangan. Laporan Astra juga mencatat 0 tanda
pergantian tanggal/pengulangan pada semua laporan kasus produk kandidat. Bukti lama tidak terkena dan tidak dibuang.

## CI pada satu commit (`CI_RECEIPT.json`)

CI_RECEIPT_PLACEHOLDER

## Yang tetap terbuka (tidak berubah oleh perbaikan ini)

- Penerimaan area optimasi timeline PR44 oleh auditor yang tidak menulisnya (bukan Astra).
- K4 browser mobile sempat diam dua kali sebelum ada batas waktu kasus (alat uji, penyebab belum ditemukan).
- Batas lama `AS20-39_VALIDATION_NEGATIVE` (trigger immutable sengaja dimatikan auditor) tetap tercatat, bukan bug baru.
- Belum diuji: HP fisik/Safari, tab HP yang benar-benar ditutup, pemasangan hosted. Jadwal dan backup belum dipasang.
- `independent_acceptance=false`, `installed_P21_acceptance=false`, `production_go=false`.

Untuk auditor: `AUDITOR_RETEST.md`.

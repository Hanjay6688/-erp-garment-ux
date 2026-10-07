# Bantuan untuk Claude: bukti head terbaru dan pemotongan dokumen besar

Owner meminta "cek kerjaan Claude dan bantu dia kalo bisa". Claude tetap satu penulis produk/integrator. Kontribusi ini hanya diagnosis, penguji dan dokumen di cabang terpisah; tidak mengganti SQL produk, RPC, UI, kontrak, batas, atau konfigurasi hosted. Ini bukan audit independen maupun izin produksi.

Source yang diperiksa: `5e8bb51385ba96c442ad717cd265e2be27e6ed87`, cabang `claude/new-session-deapao`. Hash `planning/analysis-jobs.sql`: `c22fb092edbffdc354c1444d0ca3e9461b457b2bbbc38a3b853073b18f684a60`.

**Bantuan tersedia di PR #46. Probe Native selesai:** PostgreSQL 16.15, 817/817 paritas, dua mutan tertangkap, segmen 210 MB identik; median 4,404 → 2,109 dtk. Bukti asli dan receipt ada di 4.1. SQL produk tetap belum diubah.

## 1. Kemajuan terverifikasi

- PR UX [#43](https://github.com/Hanjay6688/-erp-garment-ux/pull/43) sudah merge (7 Okt 01:24 UTC), termasuk FIN-3; penghalang merge demo sebelumnya sudah selesai. Default CodeQL berjalan sesudah push nyata, dan aturan main tidak dilonggarkan menurut handoff §15.4. Diagnosis event `opened` tetap belum terbukti.
- PR bantuan netting [#44](https://github.com/Hanjay6688/-erp-garment-ux/pull/44) sudah merge ke cabang Claude (7 Okt 09:30 UTC), dengan guard tambahan pada baris target identik. Jangan kerjakan ulang optimasi itu.
- Revisi UX lanjutan [#45](https://github.com/Hanjay6688/-erp-garment-ux/pull/45), head `049bb792`, masih OPEN. Build, preview Workers dan CodeQL success; `validate-full-schema` masih failure. PR ini merapikan spasi, drawer, picker, kolom, pencarian dan pecah batch **mode DEMO**. Pemilih Connected masih lama dan pecah batch Native belum dibuat menurut body PR; jangan menganggap simulasi itu sebagai fitur backend selesai. Cabang UX ini tidak disentuh bantuan #46.
- `0b3806b5` benar-benar punya 15/15 workflow success, termasuk P12 payroll-review. API GitHub untuk head itu diperiksa; ini bukti penulis pada source tersebut.
- Head produk terbaru `5e8bb513` punya **11/11 workflow terpicu success**. P08 Physical, PL Native, Shell, P19 Transport, P18, P21 rehearsal, Build UX dan CodeQL ikut lulus.
- Empat workflow belum punya run pada head `5e8bb513`: **P12 Payroll, P13 Finance, Note Correction, Supplier Payment Correction**. Ini bukan kegagalan tes: filter `paths` memang tidak memicu semuanya. Bila kandidat P20 harus 15 suite pada satu head, dispatch keempatnya pada head final dan perbarui §15.5. Jangan menempelkan hasil head lama pada produk baru: sejak `0b3806b5` sudah ada perubahan SQL dan UI.

Daftar exact SHA/run ID/status/link ada di `docs/cp7/evidence/claude-support-20261007/CI_SNAPSHOT_5e8bb513.json`.

## 2. P19 terbaru: hasil aplikasi dan hasil prototype berbeda

Sumber: [run 37638175395](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37638175395), job `112849785291`, head `5e8bb513`. Angka berikut klik sampai hasil atau penolakan tampil, bukan perkiraan dari kernel.

| Target | Operasional CAPTURE (1/30/100 hari) | BACKGROUND operasional | Dengan Keuangan |
|---|---|---|---|
| 100 | 1,78 / 1,82 / 2,33 dtk; hasil penuh | 1,95 / 2,05 / 2,50 dtk; hasil penuh | 6,95 / 6,97 / 8,40 dtk; hasil penuh |
| 300 | 6,46 / 6,67 / 8,23 dtk; hasil penuh | 5,23 / 5,72 / 7,14 dtk; hasil penuh | Ditolak timeout 8 dtk |
| 1000 | Ditolak timeout 8 dtk | Ditolak `CP7_ANALYSIS_JOB_STOPPED` | Ditolak timeout 8 dtk |
| 5000 | Ditolak `HISTORY_SOURCE_PRODUCTS_1000` | Ditolak batas yang sama | Ditolak timeout, batas produk juga berlaku |

Status kasus browser PASS membuktikan hasil atau penolakan yang sesuai kontrak. Ia **bukan** bukti seluruh ukuran selesai, SLA tercapai, atau kapasitas 5000 terpasang. Receipt memang masih menyatakan `owner_latency_acceptance=false` dan `full_P19_acceptance=false`.

Prototype bertahap pada [Shell run 37638175479](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37638175479), job `112849786073`:

| Ukuran | Unit | Unit terlama | Wall | Status |
|---|---:|---:|---:|---|
| 1000 × 1 | 19 | 0,922 dtk | 5,750 dtk | Byte-identik dengan single build |
| 1000 × 100 | 19 | 1,252 dtk | 8,573 dtk | Byte-identik dengan single build |
| 5000 × 1 | 50 | 1,251 dtk | 29,411 dtk | 5000 baris/kunci lengkap, 65,4 MB Original; single build menolak |
| 5000 × 100 | 55 | 1,387 dtk | 42,517 dtk | 5000 baris/kunci lengkap, 65,1 MB Original; single build menolak |

Skenario, kain dan aksesori prototype masih stand-in; bukan pembuktian 5000 melalui aplikasi Native. Fase B–E tetap terbuka di `P19_STAGED_5000_20261007.md`. Real Original sekitar 210 MB juga masih melewati kontrak klien 64 MB. Extraction angka CI ada di `P19_CI_MEASUREMENTS_5e8bb513.json`.

## 3. Temuan diagnosis: pemotong ekor masih menyalin bytes secara kuadratik

`cp7_analysis_jobs.store()` sekarang memakai `left(rest,n)` dan `right(rest,-n)`, dengan `n=2000000`. Ini menghindari hitungan ulang karakter sebelumnya, tetapi `right()` membuat teks baru yang berisi **seluruh ekor**. Source PostgreSQL 16 membuktikannya: `text_right` memanggil `cstring_to_text_with_len(p + off, len - off)`; pembuat teks itu mengalokasikan dan menyalin bytes. Sumber primer: [PostgreSQL REL_16_STABLE varlena.c](https://github.com/postgres/postgres/blob/REL_16_STABLE/src/backend/utils/adt/varlena.c).

Untuk dokumen 65.000.003 karakter (ASCII dominan, dengan satu emoji), loop saat ini menyalin **1.024.000.192 byte ekor**, selain pekerjaan hash dan potongan. Untuk 210 MB, total ekor menjadi sekitar 10,9 GB. Jadi perbaikan yang ada lebih cepat tetapi belum linear dalam ukuran dokumen. Ini diagnosis performa, **bukan** bukti angka ERP berubah.

Alternatif yang diuji (prototype, belum dipasang): ubah body sekali ke bytea UTF8; ambil jendela maksimum `4*n` byte dari offset byte; mundurkan batas maksimal tiga byte bila memotong karakter; decode jendela, ambil tepat `n` code point, lalu maju menurut `octet_length(part)`. Batas segmen 2.000.000 karakter dan hash/output tetap identik; ekor besar tidak disalin lagi. Jangan membelah menurut jumlah byte saja karena akan mengubah batas Unicode.

## 4. Bukti probe dan batasnya

Penguji: `scripts/cp7_analysis_segment_probe.mjs`; SQL diagnosis: `tests/cp7/families/f04/segment-cut-probe.sql`. Tidak masuk bundle pemasangan. Runtime memakai F04 disposable Unix-socket database; tidak menerima URL DB eksternal. Setiap panggilan menyetel timeout 8 dtk **dalam sesi yang sama**.

Paritas lokal: **817/817**, melawan pemotong lama `substr(body,i*n+1,n)`, loop saat ini dan oracle JavaScript berbasis Unicode code point. Termasuk batas 2.000.000 karakter, UTF8 2/3/4 byte, karakter non-BMP, combining marks, null/kosong, dan data acak. Dua mutan (`BAD_SIZE`, `SKIP_LAST`) tertangkap. Hash, jumlah karakter, bytes dan urutan tiap segmen diperiksa.

Runtime lokal: **PGlite 0.5.8 / PostgreSQL 18.3 WASM**, bukan Native PostgreSQL 16, Auth, HTTP atau browser. Receipt: `SEGMENT_CUT_PROBE_WASM.json`; angka pengukuran pertama di bawah disimpan di `SEGMENT_CUT_FIRST_WASM.log` (pengujian ulang dengan oracle pattern terpisah juga lulus). Pengukuran A/B/B/A synthetic ASCII + emoji:

| Karakter | Current (ms) | Window (ms) | Byte ekor current | Byte window didecode |
|---|---|---|---:|---:|
| 4.000.003 | 120 / 110 | 95 / 95 | 2.000.012 | 6.000.018 |
| 16.000.003 | 464 / 441 | 396 / 384 | 56.000.048 | 52.000.024 |
| 65.000.003 | 2086 / 2124 | 1728 / 1628 | 1.024.000.192 | 248.000.024 |

Semua metadata segmen identik. Angka WASM hanya membantu diagnosis, tidak diekstrapolasi menjadi manfaat Native atau SLA. Instalasi PostgreSQL lokal tidak tersedia; percobaan pengelola paket gagal karena operasi sistem tidak diizinkan. Verifikasi Native disiapkan lewat workflow **CP7 Claude Support Segment Diagnostic** pada cabang bantuan, memakai data synthetic sampai 210 MB dan menyimpan penolakan timeout apa adanya.

Claude bisa menilai inline pengganti loop `store` dari hasil Native berikut. Integrasi oleh Claude tetap membutuhkan uji `f05-analysis-jobs`, paritas Original/hash Unicode, transport P19, dan bukti di head gabungan. Probe ini sendiri tidak membuktikan penyimpanan 210 MB, parse `runs.result`, paging klien, atau proses 5000 selesai.

### 4.1 Verifikasi Native — selesai

[Run 37653417613](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37653417613) **success**, job `112902330530`, source probe `3f88bc9f7c43d7bf6fdb7e63ea663ed5b0014ef9`. PostgreSQL **16.15**, Ubuntu 24.04, database sekali pakai lewat Unix socket. Runtime dan semua angka dibaca dari ZIP artefak asli, bukan dari badge saja. Hash ZIP `a9841c19ae46008b77e847615e923b163ffd3099707177808b3605a3489f6d44`; CRC lulus.

**817/817** perbandingan serta kedua mutan lulus. Semua 16 panggilan benchmark (A/B/B/A × empat ukuran) selesai di bawah timeout 8 dtk; setiap segmen dibandingkan juga dengan oracle pola ASCII+emoji yang dihitung terpisah, sehingga timeout pada pembanding pun tidak akan membuat metode lain lulus dengan membandingkan dirinya sendiri.

| Dokumen synthetic | Current median | Window median | Pengurangan waktu | Segmen identik |
|---|---:|---:|---:|---:|
| 4 MB | 44,623 ms | 40,576 ms | 9,1% | 3 |
| 16 MB | 178,727 ms | 146,163 ms | 18,2% | 9 |
| 65 MB | 904,850 ms | 664,673 ms | 26,5% | 33 |
| 210 MB | 4404,059 ms | 2109,126 ms | 52,1% | 106 |

Yang diukur adalah pemotongan serta hash/metadata segmen oleh probe, setelah fixture dibuat; bukan seluruh `store()`, insert dokumen, compiler Native, atau browser. Keduanya menjalankan logika potongan atas data yang sama dalam sesi terpisah, dengan timeout 8 dtk tiap sesi. Memori puncak belum diukur. Tidak ada cap yang dinaikkan. Angka ini tidak dijadikan SLA maupun dukungan 5000 terpasang.

Bukti permanen di `docs/cp7/evidence/claude-support-20261007/`: `NATIVE_ORIGINAL.zip`, `SEGMENT_CUT_PROBE_NATIVE.json`, `SEGMENT_CUT_NATIVE.log`, `NATIVE_RECEIPT.json`. Receipt mencatat hash ketiga berkas probe/workflow dan SQL produk yang diperiksa. Pada penambahan bukti ini ketiga berkas executable tidak berubah dari run Native.

## 5. Urutan bantuan yang langsung berguna

1. Pertahankan peningkatan operasional 100 target yang sudah tampak di browser; lanjutkan staged 5000, bukan membuka ulang PR43/PR44/payroll lama.
2. Nilai pemotong window dari probe Native sebelum memasangnya. Jangan menaikkan cap 64 MB sebagai pengganti paging/penyimpanan yang benar.
3. Tentukan kandidat final setelah fase B–E, lalu lengkapi empat run yang belum ada pada kandidat itu dan tulis ulang handoff §15.2/15.3/15.5. Beberapa paragrafnya masih menyebut pekerjaan sudah selesai sebagai pending atau head lama sebagai kandidat.
4. P20 independen dan P21 pemasangan mengikuti kandidat final; P21 rehearsal hijau tetap dibedakan dari instalasi nyata. `independent_acceptance=false`, `production_go=false`.

# Audit silang r4 dan rencana r5 (ditulis penulis sesudah ketiga laporan r4 dikunci)

Laporan r4 yang sudah dikunci atas kandidat `663f6fae`:

| Auditor | Cabang / kunci | Vonis |
|---|---|---|
| Fable | `audit/fable-cp1-7-r4-663f6fae-20261019`, kunci `ff6045a9` (`audit/fable_cp17_r4/`) | Oracle D16-1 nomor 1–5 tetap ditutup, FABLE-016 dan FABLE-018 tetap ditutup, tidak ada temuan produk baru; FABLE-012 tetap ditunda (D14-9); matriks penjaga R4-05 70 sel, 0 beda; tiga catatan alat Fable sendiri |
| Astra | `audit/astra-cp1-7-r4-663f6fae-20261019`, kunci `40238e36` (`audit/astra_cp17_r4/`) | LULUS_UJI_ULANG_DENGAN_BATAS_BUKTI: ASTRA-R3-01, sisa ASTRA-R2-01, ASTRA-R3-02, ASTRA-R3-03 ditutup; tidak ada temuan produk baru; 565 kasus PASS |
| Sol | `audit/sol-cp1-7-r4-663f6fae-20261019`, segel `ecb44425` (`audit/sol_cp17_r4/`) | Satu temuan baru S1 (SOL-R4-001); KNOWN-P19-DIRECT-LATENCY tetap terbuka S2 (D17-2) |

## Per akar masalah

| Akar | Temuan | Pemeriksaan keabsahan oleh penulis | Butir r5 |
|---|---|---|---|
| Pemeriksa "Nota upah ke borongan yang salah" tidak mengenal upah perbaikan barang jadi tanpa sumber produksi | SOL-R4-001 (S1): Nota FG_REPAIR yang sah memunculkan dua alarm CRITICAL `payroll_work_wrong_contractor` (run Sol 39199375501 dan 39200571137) | Sah menurut sumber: `erp.run_v263a_payroll_integrity_checks()` (isi `supabase/migrations/20260901161322_erp_v2_6_15_payroll_component_entitlement.sql:185-202`, teks sama di bootstrap CP4.5a, tidak didefinisikan ulang sesudahnya) mencari borongan baris Nota hanya lewat PRODUCTION (`work_completion_events`) dan REWORK (`rework_orders`). AX (`scripts/cp6_ax_build.py`) mengajari view baris yang boleh dibayar, CHECK sumber, validator dan penggabungan sumber FG_REPAIR, tetapi tidak pemeriksa ini, sehingga setiap baris FG_REPAIR membandingkan borongan Nota dengan kosong. Sapuan keluarga (definisi CP6 terakhir di bootstrap + `supabase/release/cp6-t3/`, dan `scripts/cp7-src`): cabang jenis sumber upah lain khusus sumbernya sendiri atau sudah mengenal FG_REPAIR | R5-01 |
| Analisis langsung dengan angka keuangan di atas 3 detik | KNOWN-P19-DIRECT-LATENCY (S2, sudah diketahui): Sol 4,25–4,66 detik, Fable 4,6 detik SQL / 5,6 detik browser, Astra 4,65 detik pada 100 target | Sah sebagai pengukuran; owner D17-2: dikerjakan penulis sesudah audit r4 | R5-02 |

Butir yang dicatat auditor untuk dirinya sendiri (bukan pekerjaan penulis): catatan alat Fable FABLE-R4-TOOL-01..03, tabrakan nama
arsip di 12 job P19 Astra (183 kasus arsip pertama lulus), sepuluh run Sol yang dikelompokkan sebagai alat auditor atau
temuan SOL-R4-001. Batas bukti yang sama di ketiga laporan (CP7C, salinan data nyata, preflight hosted, restore CP2 penuh,
cakupan 12 jalur lama) tetap ditahan sesuai keputusan owner; tidak dibuka ulang.

## Keputusan owner di putaran ini

- D17-2 (19 Okt 2026 WIB): "Auditor dl ya, inget lu punya tugas ini di next turn ya" — auditor dulu; kecepatan analisis
  langsung dengan angka keuangan dikerjakan penulis sesudahnya. Kutipan lengkap di `docs/cp7/OWNER_DECISIONS_20261008.md`.
- 19 Okt sesudah uji ulang r4: "udah semua katanya" (ketiga auditor sudah melapor).

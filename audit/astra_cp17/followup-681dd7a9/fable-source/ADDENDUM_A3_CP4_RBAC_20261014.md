# Addendum A3 laporan cp17 — permukaan akses CP4/CP4.5 pada kode final (14 Okt 2026)

Tidak menimpa laporan v1.0. Label: FABLE, NATIVE_QUALIFIED (komposisi CP7 penuh 0b7049d9 di atas basis G-01 yang identik dengan hosted).

| Run / job | Kasus | Hasil |
|---|---|---|
| 38571378585 / 115877180312 | FABLE_RBAC:ERP_TABLES_WITHOUT_RLS | **PASS** — kode final: **0** tabel `erp` tanpa RLS. (Hosted hari ini 4 tabel tanpa RLS, addendum A1: itu kondisi v2.6.20 yang diperbaiki migrasi CP6 di kode final; berlaku sampai rilis dipasang.) |
| 38571378585 / 115877180312 | FABLE_RBAC:ERP_SCHEMA_REACH | **PASS** menurut oracle (anon tidak punya USAGE skema `erp`; satu-satunya fungsi `erp` "penulis" yang bisa dieksekusi anon adalah fungsi trigger `guard_attendance_record_period_and_dates()` yang tidak bisa dipanggil langsung). Fakta: `authenticated` punya **USAGE** skema `erp` dan **EXECUTE** pada 160 dari 940 fungsi `erp`, **108** di antaranya bernama penulis — termasuk `reopen_accounting_through`, `close_accounting_through`, `post_payroll_payment`, `approve_payroll`, `post_opening_balance`, `post_opening_*_correction`, `reverse_cutting_material_flow_before_sewing_v2`, `process_cost_recalc_queue`, `reopen_production_order`. |
| 38571378585 / 115877180312 | FABLE_RBAC:PUBLIC_FACADES_SECURITY | INCOMPLETE = AUDITOR_TOOL (placeholder `%` di pola LIKE skenario Fable) |
| 38572386253 / 115880664623 | FABLE_RBAC:PUBLIC_FACADES_SECURITY (run 2, oracle sama) | **PASS** — 266 fasad `public.erp_*`, semuanya SECURITY DEFINER dengan `search_path` terkunci; 0 dapat dieksekusi `anon`. |

## Temuan baru
### FABLE-012 (DUGAAN) — Peran `authenticated` dapat mengeksekusi 108 fungsi penulis Native di skema `erp` secara langsung, melewati fasad
- Keparahan hipotesis: **S2** (pengerasan); naik ke **S1** bila hosted mengekspos skema `erp` lewat PostgREST (`db_schemas`), karena pengguna login mana pun dapat memanggil langsung fungsi seperti `reopen_accounting_through` atau `reverse_cutting_material_flow_before_sewing_v2` dan hanya tertahan pemeriksaan peran di dalam fungsi (`require_owner_admin`), tanpa review token, idempotensi, atau lineage fasad.
- Invarian: INV-A05 (akses persis seperti yang dideklarasikan; tidak ada akses langsung ke skema privat), `review/R3` R3-07, `review/R4` R4-05 (pernyataan "UI tidak bisa reopen" hanya benar bila `erp` tidak diekspos).
- Bukti: TERBUKTI untuk hak akses katalog (run 38571378585); keterjangkauan dari klien **TIDAK DAPAT DIVERIFIKASI DARI SESI INI** (konfigurasi PostgREST hosted di luar izin D14-1 yang khusus CP1/CP2; CI memakai `public` saja).
- Usulan: `revoke execute on all functions in schema erp from authenticated` lalu beri kembali hanya yang memang dipanggil fasad sebagai invoker (fasad saat ini SECURITY DEFINER, jadi tidak butuh hak `authenticated` pada fungsi `erp`), atau cabut USAGE skema `erp` dari `authenticated`. Uji: panggilan langsung `erp.*` sebagai `authenticated` → 42501; seluruh suite fasad tetap PASS.

## Dampak pada vonis
- **CP4/CP4.5: LULUS DENGAN SYARAT** (sebelumnya LULUS dasar runtime). Syarat: FABLE-012 diputuskan (rekomendasi: cabut) dan owner/penulis mengonfirmasi skema yang diekspos PostgREST di hosted.

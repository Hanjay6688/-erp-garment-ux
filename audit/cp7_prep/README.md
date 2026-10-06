# Persiapan audit CP7 (Fable) — status pra-pembekuan

Dibuat 6 Okt 2026 atas arahan owner (#2 + #3 paralel). Dasar aturan: `docs/AUDIT_PANDUAN_PRO_MAX.md` versi PR 42 (belum merged; salinan `out/panduan_pr42.md`). Semua dokumen di folder ini **bukan hasil audit**; hanya inventaris, pemetaan, dan manifest draft. Hasil run pra-pembekuan ada di `out/fable_r16_prefreeze_regression.md` dengan label `PRA_PEMBEKUAN`, bukan bukti lomba.

| Berkas | Isi |
|---|---|
| `REQUIREMENTS_TO_SCENARIOS.md` | 133 kebutuhan NOT_RUN → SKN/INV (pemetaan awal otomatis, tinjau manual) + XCP-01..04 lintas CP |
| `TRANSACTION_CORRECTION_MATRIX.md` / `correction_matrix.csv` | 27 keluarga transaksi × (tombol tersedia, koreksi sah selesai, penghalang bernama) |
| `CASE_MANIFEST_DRAFT.json` | kerangka kasus TCM-nn-A/B/C/D (role, oracle_origin, fixture_origin, expected: belum diisi) |
| `requirements_notrun_raw.md` | dump mentah registri |

Yang belum: oracle angka per kasus, deklarasi peran, fixture_origin, dan commit beku. Diisi setelah owner menetapkan SHA beku.

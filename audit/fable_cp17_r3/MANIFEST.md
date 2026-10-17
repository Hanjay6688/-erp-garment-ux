# Fable r3 — manifest putaran (kandidat b53b5acd)

| Hal | Nilai |
|---|---|
| Kandidat | `b53b5acdf260b03ebac3474e9ae837fcef6f6eb1`, tree `32f54240a60e01ab8b1ffad7267d285a669be520` |
| Basis r2 | `2e9d6a46…` (tree `5e50d224…`); laporan Fable r2 terkunci 80f01cee; keputusan D16-1 + oracle 1–5 f2758f39 |
| Kepala penulis saat mulai | `64339905cc19e497f9fdb3599ff4a21cbf7da8ff`; beda dari kandidat hanya 6 berkas `docs/` |
| `supabase/` sejak 2e9d6a46 | 0 berkas berubah (tree `5d040436` sama) |
| Perubahan produk 2e9d6a46 → kandidat | `src scripts tests .github`: 106 berkas, +11935/−240 |
| Tree produk kandidat | src `b4041b3b`, supabase `5d040436`, scripts/cp7-src `633ef684`, scripts `842b7c25`, .github/workflows `51536639` |
| Panduan | `docs/AUDIT_PANDUAN_PRO_MAX.md` sha256 5752e96d… (sama) |
| Workflow Fable | `fable-cp7-native.yml`, default kandidat b53b5acd / tree 32f54240; input baru `ui_mode` (DISPOSABLE/ENTENG) meneruskan `AUDITOR_UI_MODE` ke host browser produk; oracle tidak berubah |
| Laporan yang akan dikunci | `RETEST_FABLE_b53b5acd.md`, `FINDINGS.json` |

## Paparan (§16.7)
`HANDOFF_FABLE.md` r3 dibaca lewat `git show` dari kepala penulis. `HANDOFF_ASTRA.md` dan `HANDOFF_SOL.md` tidak dibuka.
Laporan, cabang, run, artifact dan komentar auditor lain dari putaran r3 tidak dibuka sampai laporan Fable dikunci. Hosted
Enteng tidak diakses.

# Fable r4 — manifest putaran (kandidat 663f6fae)

| Hal | Nilai |
|---|---|
| Kandidat | `663f6faefcbb9c70f0f99bbc7e78164e03521329`, tree `023f3554432f80f994439f5d0b8cc164846a2041` |
| Basis r3 | `b53b5acd…` (tree `32f54240…`); laporan Fable r3 terkunci 2033fdfc |
| Kepala penulis saat mulai | `5eda90e10b2e87485ab710e9fd9ffa68d81a3565`; beda dari kandidat hanya 9 berkas `docs/` (`git diff --name-only`, tanpa berkas di luar `docs/`) |
| `supabase/` sejak b53b5acd | 0 berkas berubah (tree `5d040436` sama) |
| Perubahan produk b53b5acd → kandidat | `src scripts tests .github`: 37 berkas, +1394/−85 |
| Tree produk kandidat (sebelum audit) | src `c3008b5b`, supabase `5d040436`, scripts/cp7-src `d71b0bc4`, scripts `793d6ea6`, .github/workflows `e41df157`; sama di kepala `5eda90e1` |
| `package.json`/`package-lock.json` | sama dengan b53b5acd |
| Panduan | `docs/AUDIT_PANDUAN_PRO_MAX.md` sha256 5752e96d… (sama) |
| Workflow Fable | `fable-cp7-native.yml`, default kandidat 663f6fae / tree 023f3554; selain pin kandidat tidak ada yang berubah dari r3 (input `ui_mode`, pemetaan host Enteng ke 127.0.0.1) |
| Komposisi tumpukan | probe Fable memasang `cp7_f03_bundle.extension()` milik kandidat; di r4 fungsi itu ikut memuat `cp7_public_routes_bundle` (R4-01) dan `cp7_internal_guard_bundle` (R4-05) sebagai delta terakhir |
| Laporan yang akan dikunci | `RETEST_FABLE_663f6fae.md`, `FINDINGS.json` |

## Paparan (§16.7)
`HANDOFF_FABLE.md` r4 dan `README.md` paket dibaca lewat `git show` dari kepala penulis, juga D17-1/D17-2 di
`docs/cp7/OWNER_DECISIONS_20261008.md`. `HANDOFF_ASTRA.md` dan `HANDOFF_SOL.md` tidak dibuka (namanya hanya muncul di
daftar berkas `git ls-tree`/`git diff --stat`). Laporan, cabang, run, artifact dan komentar auditor lain dari putaran r4
tidak dibuka sampai laporan Fable dikunci. Hosted Enteng tidak diakses.

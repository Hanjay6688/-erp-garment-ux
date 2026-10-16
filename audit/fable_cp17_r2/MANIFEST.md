# Fable r2 — manifest putaran (kandidat 2e9d6a46)

| Hal | Nilai |
|---|---|
| Kandidat | `2e9d6a468c110684c278d585418eb404250d1150`, tree `5e50d224f8e74fa3bca83b599fb606739435b598` |
| Basis audit gabungan | `dfab13bf62398a69a02bf6221c06d29075e5e40b` (tree `886f8331…`); laporan Fable terkunci ccafdb18, keputusan owner 8677a399 |
| Kepala penulis saat mulai | `b388a4b7d4b0291de81b68d1e624a062eda5edd1`; beda dari kandidat hanya 8 berkas `docs/` (`docs/cp7/audit-candidate/cp1-7-r2-20261016/` 7 + 1) |
| `supabase/` sejak dfab13bf | 0 berkas berubah (tree `5d040436` sama) |
| Perubahan produk dfab13bf → kandidat | `src scripts tests .github`: 111 berkas, +7342/−290 |
| Tree produk kandidat | src `5fd3d2b8`, supabase `5d040436`, scripts/cp7-src `32edbc0b`, scripts `6c5f4e42`, .github/workflows `f94b33d9` |
| Panduan | `docs/AUDIT_PANDUAN_PRO_MAX.md` sha256 5752e96d… (sama) |
| Workflow Fable | `fable-cp7-native.yml`, default `product_ref` 2e9d6a46 / tree 5e50d224, run-name `AUDIT/r2-20261016/fable/...` |
| Laporan yang akan dikunci | `RETEST_FABLE_2e9d6a46.md`, `FINDINGS.json` |

## Paparan (§16.7)
Dibaca dari paket r2: `HANDOFF_FABLE.md` (lewat `git show` dari kepala penulis karena owner meneruskan laporan kemajuan
penulis, bukan kotaknya). `HANDOFF_ASTRA.md` dan `HANDOFF_SOL.md` tidak dibuka. Laporan, cabang, run, artifact dan komentar
auditor lain dari putaran r2 tidak dibuka sampai laporan Fable dikunci. Laporan yang terkunci sebelum putaran ini (audit
gabungan dfab13bf) boleh dibaca menurut paket. Berkas pemetaan Astra lama (`C6_75_ALL22_CROSSWALK.md`, cabang Astra commit
`d4a83b42`, dibuat sebelum putaran r1) hanya akan di-hash untuk FABLE-005, atas permintaan paket. Hosted Enteng: tidak
ada akses pada putaran ini.

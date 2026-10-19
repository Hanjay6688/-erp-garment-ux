# Fable r5 — manifest putaran (kandidat 17fa2507)

| Hal | Nilai |
|---|---|
| Kandidat | `17fa25075ba77f0853c3c16f504288ace03eec35`, tree `65f778479093d869a3354c0b9f19b4d9a541d98a` |
| Basis r4 | `663f6fae…` (tree `023f3554…`); laporan Fable r4 terkunci ff6045a9 |
| Kepala penulis saat mulai | `2766a9092f51f240267b9cbe1201d49a836fb490`; beda dari kandidat 9 berkas, semua `docs/` |
| `src/` dan `supabase/` sejak 663f6fae | 0 berkas berubah |
| Perubahan produk 663f6fae → kandidat | `src scripts tests .github`: 10 berkas, +518/−15; `scripts/cp7-src` tidak berubah; dua delta baru `cp7_payroll_checks_bundle.py` (R5-01) dan `cp7_report_accounts_bundle.py` (R5-02) |
| Tree produk kandidat (sebelum audit) | src `c3008b5b`, supabase `5d040436`, scripts/cp7-src `d71b0bc4`, scripts `5acd2558`, .github/workflows `592b48dd`; sama di kepala `2766a909` |
| `package.json`/`package-lock.json` | sama dengan 663f6fae |
| Panduan | `docs/AUDIT_PANDUAN_PRO_MAX.md` sha256 5752e96d… (sama) |
| Workflow Fable | `fable-cp7-native.yml`, default kandidat 17fa2507 / tree 65f77847; selain pin kandidat tidak berubah dari r4 |
| Laporan yang akan dikunci | `RETEST_FABLE_17fa2507.md`, `FINDINGS.json` |

## Paparan (§16.7)
`HANDOFF_FABLE.md` r5 dibaca lewat `git show` dari kepala penulis. `HANDOFF_ASTRA.md` dan `HANDOFF_SOL.md` tidak dibuka (nama
hanya muncul di `git ls-tree`). Owner meneruskan ringkasan status penulis yang menyebut temuan Sol r4 (S1/SOL-R4-001) dan
bahwa laporan Fable dan Astra r4 bersih; laporan r4 itu terkunci sebelum putaran ini. Laporan, cabang, run, artifact dan
komentar auditor lain dari putaran r5 tidak dibuka sampai laporan Fable dikunci. Hosted Enteng tidak diakses.

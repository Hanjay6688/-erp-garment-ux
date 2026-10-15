# Manifest putaran Fable cp17c-20261015 — paket gabungan D14-16 (uji ulang r1 + audit akhir D14-13)

| Butir | Nilai |
|---|---|
| Kandidat | `dfab13bf62398a69a02bf6221c06d29075e5e40b`, tree `886f83312958b53781a450a4ea2a8fb2147b3be3` |
| Basis audit penuh | `0b7049d9` (tree `ce6aed0a`), laporan `audit/fable_cp17/AUDIT_FABLE_0b7049d9.md` v1.0 + A1–A3 |
| Head cabang writer saat mulai | `65628336` — `git diff --name-only dfab13bf..65628336` hanya 11 berkas di `docs/cp7/audit-candidate/` (dokumen) |
| `supabase/` sejak 0b7049d9 | tidak berubah (0 berkas); tree `5d040436` |
| Perubahan produk 0b7049d9 → dfab13bf | 182 berkas, +7327/−199 (`src/`, `scripts/`, `scripts/cp7-src/`, `tests/`, `.github/workflows/`) |
| Tree produk | `src` 78915706, `supabase` 5d040436, `scripts/cp7-src` 52a931ef, `scripts` 1306bf8e, `.github/workflows` 47da8945 |
| Panduan | `docs/AUDIT_PANDUAN_PRO_MAX.md` sha256 5752e96d… (sama dengan audit penuh) |
| Keputusan owner yang dipakai | `docs/cp7/OWNER_DECISIONS_20261008.md` D14-1..D14-17 (dibaca di kandidat); register auditor `audit/fable_cp17/OWNER_DECISIONS_TO_AUDITOR_20261014.md` |
| Workflow Fable | `AUDIT/fable/cp7-native`, default `product_ref` dfab13bf / tree 886f8331, run-name `AUDIT/cp17c-20261015/fable/...` |
| Laporan yang akan dikunci | `RETEST_FABLE_dfab13bf.md` (bagian A), `FINAL_FABLE.md` + `FINDINGS.json` (bagian B) |

## Paparan (§16.7)
Dibaca dari paket: `HANDOFF_FABLE.md`, `README.md`, `CHAIN_MAP.md`, `SCREEN_MAP.md`, `GAPS_D14_14.md`, `CI_RECEIPT.json`, dan folder r1. `HANDOFF_ASTRA.md` / `HANDOFF_SOL.md` tidak dibuka. Cabang, run, artifact, dan laporan auditor lain di putaran ini tidak dibuka sampai laporan Fable dikunci. Laporan audit penuh auditor lain atas 0b7049d9 yang sudah terkunci boleh dibaca menurut paket, tetapi belum dibuka. Hosted Enteng: hanya baca daftar skema yang terbuka lewat Data API (D14-7); tidak ada tulis.

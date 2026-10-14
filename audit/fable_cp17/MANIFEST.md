# Manifest putaran — audit penuh CP1–CP7 oleh Fable (Pro Max §16.1)

| Hal | Nilai |
|---|---|
| round_id | cp17-20261014 |
| Waktu pembekuan paket (dibaca Fable) | 2026-10-14T06:20:30Z |
| Kandidat | commit `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18` (pembekuan final CP7, D13-13) |
| Head cabang writer saat mulai | `00b0eb24`; `git diff --name-only 0b7049d9 00b0eb24` di luar `docs/` = 0 berkas (diperiksa sendiri) |
| Tree produk (dicatat sebelum audit, §2.8) | src `d6553972f94a4ad4e9170e8a946b30cdac9712fd`; supabase `5d040436db384b4e574785376367b360a084acb7` (migrations `8f6053bb…`, dev `88759f4f…`, release `be1e91c1…`, rollbacks `9e216e7b…`); scripts/cp7-src `7bcf45e174499f3712c67ee08788a90a8c5f7881`; scripts `b67664091c4394b0ff6a187409d9e9b32213a0e0`; .github/workflows `4d7712279bfdfb6aec10dca4a216dd927875f483` — semua cocok dengan README paket |
| Panduan yang berlaku | `docs/AUDIT_PANDUAN_PRO_MAX.md` @0b7049d9, SHA-256 `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639` (dihitung sendiri, cocok dengan handoff), 553 baris |
| Register keputusan | `docs/cp7/OWNER_DECISIONS_20261008.md` sampai D13-13; `docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25*.md`; `docs/cp6-d11-kebijakan-dan-gbd03.md`; register auditor `audit/fable_cp7/OWNER_DECISIONS_TO_AUDITOR_20261013.md` |
| Workflow auditor | `.github/workflows/fable-cp7-native.yml` di cabang ini (nama `AUDIT/fable/cp7-native`), checkout writer `ca7f0955`, harness `c6b0e4fb`, candidate CP6 `25fa4736`, base `1bdca376`, produk = `product_ref` input (default 0b7049d9) dengan assert tree |
| Skenario Fable (oracle sendiri) | `audit/fable_cp7/scenarios/*.py`, `*.mjs` (hash dicatat per run oleh probe: `scenario_sha256`) + skenario CP1–7 baru di `audit/fable_cp17/scenarios/` |
| Lingkungan | GitHub ubuntu-24.04, Supabase CLI pinned, PostgreSQL 17.6 (stack lokal), psycopg 3.2.10, Node 22 |
| Peserta | Astra (terpisah), Fable (ini); penyatu Fable sesudah kedua laporan dikunci (§10, §16.7) |
| Paparan | Fable tidak membuka cabang/run/artifact Astra putaran ini sampai laporan ini dikunci. Daftar run yang dibuka: `REGISTER_RUNS.md` |
| Di luar cakupan | alat backup CP7C (D13-9a); PR #45; shadow run data nyata (§12.4); pemasangan dari salinan hosted (§12.10) |

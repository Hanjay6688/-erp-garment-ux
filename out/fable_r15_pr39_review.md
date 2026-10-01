# Fable — Putaran 15: tinjauan PR 39 (`cp6/release-readiness`, head f378b9e, dasar 10a8347)

Tanggal: 2026-10-01 (UTC). Status: **FINAL**. Posisi PR: draft, belum di-merge; tidak ada tulisan ke hosted/main oleh auditor.

## 1. Tinjauan sumber — INDEPENDENT_SOURCE_REVIEW
| Hal | Temuan |
|---|---|
| Paket DB (`supabase/release`, `supabase/migrations`, `supabase/dev`) | **tidak berubah sebyte pun** vs 10a8347 (`git diff --quiet` kosong) |
| 28 berkas pendahulu v2.6.20→AB (`PREDECESSOR_MANIFEST.json`) | **28/28 sha256 cocok** dengan berkas di repo; manifest `8368df52…` |
| Skenario BF "free" lama | ditulis ulang di tingkat vendor (`SAVE_COMPONENT_RATE`), SKU dikirim `laundry_rates: []`; produk tidak dilonggarkan (penjaga `BF_LAUNDRY_VENDOR_AUTHORITY` tetap, SQL sama) — sesuai D13 |
| UI (`src/`: 4 halaman + `cp6Readiness.ts` + tes) | panel "pengaturan belum diterapkan" (membedakan: perlu isian / keputusan belum diterapkan / sengaja mati), pesan prasyarat posting invoice, tombol prefill 4 keputusan owner (hanya mengisi formulir, simpan lewat RPC biasa), catatan W8/T3-A di HPP per SKU. Tidak ada perubahan hak akses. |
| Preflight hosted penulis (`cp6_readiness_hosted_preflight.sql`, receipt) | `begin transaction read only … rollback`; hanya `to_regclass`/`to_regprocedure`/`pg_stat_activity`. **Baca saja, tidak ada maintenance.** Temuan penulis: ERP Enteng & ERP-Garment masih v2.6.20 (A–AB belum ada), 3 sesi klien aktif. **Tidak dapat saya verifikasi dari sini** (akses baca proyek hosted ditolak kebijakan sesi) → REUSED_WRITER_EVIDENCE |
| Runbook `HOSTED_MAINTENANCE.md` | urutan: isian nyata → backup teruji pulih → jendela disetujui → `--apply` (admission ditutup sekali, tanpa kill sesi) → 58 receipt PASS + BF terverifikasi → canary → banding advisor → buka. Target ERP Enteng saja. Wajar; tidak ada go otomatis. |

## 2. Run ulang auditor pada cabang PR (ref `cp6/release-readiness`, head f378b9e) — INDEPENDENT_NATIVE_RERUN
| Run | Job | Hasil saya | Klaim penulis (run 36821348197) |
|---|---|---|---|
| 36824954256 `cp6-release-readiness.yml` | Hosted v2.6.20 → BF, 58 berkas, owner & work non-superuser | **10/10 PASS**, `install_file_count` 58, `native_stage` BE_PLUS_BF_T1, `control_is_superuser` false, `work_is_superuser` false, baseline v2.6.20 sejalan per objek (`ALIGNED_PER_OBJECT`) | 10 PASS, 58 berkas |
| 36824954256 | paket 30 berkas, runtime penulis, advisors, restore drill | **native 104, races 26, HTTP 9 — semua PASS**; primary unchanged | 104 / 26 / 9 |
| 36824954256 | browser AU + BF | **31/31 PASS, console errors 0** | 31, nol error |
| 36824956958 `cp6-auditor-scenario.yml` (after) | `cp6_bf_combined_modes.py` (readiness oracles + vendor-free + BF gabungan) + `cp6_bf_free_browser.mjs` | **166/166 PASS** (104 native, 26 balapan, 9 HTTP, 27 browser); termasuk `READINESS:W8_SEVEN_DOCUMENTS_*` (7 × 10.006 → 70.07), `READINESS:POST_REQUIRES_BOTH_POLICIES_DRAFT_PHYSICAL_ALLOWED`, `VENDOR_FREE:*`, `VENDOR_FREE_BROWSER:*` | — (skenario penulis di runtime auditor) |

Angka saya identik dengan klaim penulis. Run pertama penulis 36817969996 (c387f1b) memang gagal (fixture HTTP role tidak ada) dan dibiarkan merah — benar, tidak direlabel.

## 3. Putusan atas PR 39
- **Enam risiko yang saya sebut tertangani dengan benar**, tanpa menyentuh angka uang/stok/HPP. Skenario basi diperbaiki ke arah aturan owner (D13), bukan produk yang dilonggarkan.
- **Temuan baru yang penting dan benar dari penulis:** hosted masih v2.6.20, jadi pemasangan pertama butuh 58 berkas (28 pendahulu + 30 paket), bukan 30. Jalur 58 berkas itu lulus 10/10 di run saya dengan akun non-superuser seperti hosted.
- **Masih bukan go produksi**, dan PR ini sendiri bilang begitu. Sisa: (1) 8 isian nyata owner; (2) backup hosted yang terbukti pulih; (3) jendela maintenance ERP Enteng + eksekusi runbook; (4) banding advisor hosted (daftar advisor paket naik 73→216, semua tambahan INFO, "REVIEW_REQUIRED"); (5) kecocokan UI dengan demo acuan masih belum diperiksa siapa pun secara independen (host demo diblokir dari sesi saya).
- Rekomendasi saya ke owner: **PR 39 layak di-merge ke cabang penulis** (bukan main) sebagai dasar pemasangan pertama. Jangan ada yang mengubah 30 berkas paket atau 28 pendahulu lagi; hash sudah dikunci di manifest.

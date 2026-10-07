# Handover CP7 ke GPT — 7 Okt 2026 (checkpoint 5.000 target)

Claude berhenti di checkpoint ini karena kuota. Dokumen ini berdiri sendiri: semua yang belum masuk produk ada sebagai berkas patch di folder ini (container Claude akan hilang).

`production_go=false` · `independent_acceptance=false` · bukan audit independen.

## 0. Paste block singkat untuk GPT

> Lanjutkan CP7 dari head `013ea062` cabang `claude/new-session-deapao` (Hanjay6688/-erp-garment-ux). Baca `docs/cp7/handoff/wip-5k-20261007/HANDOFF_GPT_CP7_20261007.md` lengkap. Tugas utama: selesaikan "5.000 target sebagai kapasitas didukung" (arah owner 7 Okt butir 3) dengan menerapkan patch WIP di folder itu sesuai urutan §3, menyelesaikan sisa pekerjaan §4, lalu kualifikasi satu head (§6). Jangan buka ulang keputusan yang sudah disahkan; jangan longgarkan oracle/guard; simpan log gagal pertama; tidak menyentuh main, Cloudflare, Supabase hosted, legacy ERP, produksi.

## 1. Keadaan yang sudah terbukti (CI GitHub, bukan lokal)

Head `013ea062e69e3fb4a9d12431be8b74650bfc41c4` — **10/10 workflow terpicu hijau**:

| Workflow | Run |
|---|---|
| CP7 Shell S0 | 37655751305 |
| CP7 PL Native Planning | 37655751460 |
| CP7 P19 Analysis Job Transport (transport11 + scale5) | 37655751288 |
| CP7 P08 Physical Fabric | 37655751390 |
| CP7 P18 Full Cycle | 37655751513 |
| CP7 P21 Rehearsal | 37655751300 |
| CP7 Owning Receipt Correction | 37655751456 |
| CP7 Supplier Payment Create | 37655751570 |
| CP6 Candidate CodeQL (T3) | 37655751468 |
| Build UX | 37655751339 |

Belum terpicu di head ini (filter `paths`, bukan gagal): P12 Payroll, P13 Finance, Note Correction, Supplier Payment Correction — dispatch manual di head final (§6).

Isi `013ea062` di atas `5e8bb513`: pemotong segmen `cp7_analysis_jobs.store()` lewat jendela byte UTF-8 terbatas (tanpa salin ekor). Diagnosis dan bukti Native berasal dari PR bantuan owner [#46](https://github.com/Hanjay6688/-erp-garment-ux/pull/46) (817/817 paritas di PostgreSQL 16.15, 210 MB 4,40 → 2,11 dtk). Potongan identik: tiap segmen kecuali terakhir tepat 2.000.000 code point; hash dokumen sama.

## 2. Arah owner 7 Okt — status jujur

| Butir | Status | Catatan |
|---|---|---|
| 1 Review PR #44 | selesai | sudah merge ke cabang Claude |
| 2 Keuangan dimuat saat perlu; tidak dimuat ≠ nol | selesai | jalur operasional, CI hijau |
| 3 5.000 target kapasitas didukung | **BELUM** | fase A + C1 di produk; fase B/D/staged API masih prototipe + patch WIP (§3–4) |
| 4 PL-8 bukti grup habis tersimpan | selesai | e7542cf8 dst. |
| 5 Latensi: pengecualian latar dicatat | selesai | 3 dtk tidak pernah ditandai tercapai |
| 6 PL-5 | menunggu owner | proposal B di `docs/cp7/PL5_YIELD_POLICY_PROPOSAL_20261007.md` |
| 7 AP-5 | selesai | |

Fakta terukur 5.000 (CI, head lama 5e8bb513): satu capture operasional 5.000 produk = 4,4–4,6 dtk dari batas 8 dtk; jalur tunggal menolak 5.000 secara jujur (`HISTORY_SOURCE_PRODUCTS_1000`). Original nyata ≈ 42–50 KB/target (≈210 MB di 5.000) → tidak bisa satu jsonb/satu dokumen klien; karena itu desain bertahap + halaman (kontrak §10 di `docs/cp7/p19/P19_STAGED_5000_20261007.md`, ada di patch 0003).

## 3. Patch WIP di folder ini — urutan penerapan (sudah dicek: bersih)

Dasar: `013ea062`.

1. `git am integrator/0001-*.patch … 0005-*.patch` (commit lokal Claude):
   - 0001 fase D prototipe (halaman, pembaca, parser klien) — **berisi frontend yang memanggil RPC prototipe**; 3 dan 5 di bawah menggantikannya.
   - 0002 fase B prototipe (unit skenario nyata, kain/aksesori nyata) + bukti lokal.
   - 0003 dokumen rencana + **kontrak produk §10 (mengikat)** + prototipe API request/step/get.
   - 0004–0005 suite Native jalur bertahap `CP7_P19_STAGED` (12 kasus, `docs/cp7/p19/P19_STAGED.json`, probe `cp7_p19_staged_probe.py`, matriks `p19-staged12` di workflow P19 Transport) + titik ukur bertahap di tangga skala 100/300/1.000/5.000 (SQL dan kontrol browser `STAGED`) + deklarasi `P19_SCALE.json`.
2. `git apply agentP-product-sql.diff` → `scripts/cp7-src/planning/analysis-stages.sql` (produk, 2.101 baris), `scripts/cp7_analysis_stages_bundle.py`, `cp7_analysis_bundle.py`. Lokal: install bundle penuh + verify OK, reachability PASS. Catatan agen: `agentP-NOTES.md`.
3. `git am agentF-frontend.patch` → driver step-loop, parser §10 dengan `identity_hash`, tampilan halaman, tombol "Analisis bertahap (hingga 5.000 target)". Lokal: tsc bersih, uji baru 17/17 + DOM 9/9, katalog akses/kepemilikan PASS. Catatan: `agentF-NOTES.md`.

**Jangan push hasil langkah 1 sendirian**: 0001 memanggil RPC yang belum ada, dan 0004 menambah titik bertahap ke scale5 yang saat ini hijau — keduanya akan merah tanpa langkah 2–3 + §4.

## 4. Sisa pekerjaan (urut risiko)

1. **Uji kernel produk (agen P belum sempat):** f05-staged-analysis/-scenario/-pages harus memuat `analysis-stages.sql` produk (bukan prototipe); paritas byte demi byte header+halaman → teks analisis dan Original jalur tunggal, `semantic_hash` dihitung ulang, `identity_hash` dihitung ulang, batas halaman di banyak titik, penolakan sama dengan jalur tunggal. Fixture draf belum diuji: `agentP-staged-analysis-fixture.product.DRAFT_UNTESTED.mjs`. Uji baru f05-staged-api. Hapus prototipe setelah tidak dipakai. Benchmark produk: 5.000 × horizon default harus DONE dengan tiap unit < 8 dtk. Sambungkan job CI `p19-staged` (Shell).
2. **Rekonsiliasi kontrak P ↔ F** (lihat `agentF-NOTES.md` "Contract decisions"). Sudah cocok: status `cp7.native-analysis-staged-job.v1` tanpa `job_id` (prototipe lama masih `v0` + `job_id`). **Tidak cocok, harus diputuskan satu:** `identity_hash` run 0 halaman — SQL P = `sha256(header_sha256 || E'\n' || '')` (coalesce ke string kosong, ada `\n`), parser F = `sha256(header_sha256)` tanpa `\n`. Periksa juga: `failure.message` (F menerima), referensi page set = referensi status DONE, kunci respons cek sumber.
3. **Suite integrator (0004/0005) belum pernah jalan.** Asumsi yang harus dicocokkan dengan SQL P: kolom `cp7_analysis_stage.jobs` (actor = auth.uid(), request_id, state, run_id, reference, query, access_at_capture, units_done, unit_count, failure_code, created_at), `pages(run_id, idx, body, utf8_bytes)`, kunci `bounds()` (job_targets 5000, job_matching_products 10000, job_history_cells 500000), kode `CP7_ANALYSIS_PAGE_UNAVAILABLE` / `_RUN_UNAVAILABLE` / `_JOB_UNAVAILABLE` / `_STAGE_STOPPED` / `_STAGED_TARGET_LIMIT`, `unit_attempts` per unit berikutnya (3× henti → FAILED 57014).
4. **Frontend:** jalankan ulang seluruh `npx vitest run src` (baseline 1453/1453) dan suite DOM jalur tunggal pada commit F. Satu perubahan sengaja di jalur tunggal: capture yang ditolak salah satu dari enam kode batas melepas request agar tombol bertahap bisa dipakai — perlu ditinjau.
5. **Ukur 5.000 di CI lewat aplikasi** (scale5 dengan titik `STAGED`), dicatat sebagai pengecualian latar `P19_PLANNING_ANALYSIS_STAGED_20261007` — bukan target 3 dtk tercapai. Perhatikan total waktu job (timeout 330 menit; `MEASURE_PROCESS_MS` dinaikkan ke 5.400.000 sebagai batas driver).
6. Dokumen: tabel status di `P19_STAGED_5000_20261007.md`, SELF_CHECK §6 (baris 013ea062), P20/P21 §14.

## 5. Keputusan owner yang masih terbuka

- Nilai retensi data antara staged (PENDING_POLICY_VALUE; fungsi purge privat sudah ada, tanpa jadwal).
- Prioritas fitur di atas run bertahap: pengingat, laporan, workspace kain, draf rencana, AI (kini dinyatakan "tidak tersedia" di UI).
- Driver server-side (sekarang client-driven: halaman memanggil step berulang; job berhenti bila tidak ada sesi).
- Terima capture satu-statement di 5.000 dengan margin terukur (4,4–4,6 dtk dari 8 dtk) atau bangun capture bertahap.
- Runner `prove_exhausted` (PL-8); persetujuan PL-5 B; pemisahan produk legacy CP5; EnterpriseSelect tidak bisa dicari.

## 6. Kualifikasi akhir (#142)

Setelah §4 selesai di satu head: semua workflow CP7 hijau di head yang sama, termasuk dispatch manual P12, P13, Note Correction, Supplier Payment Correction (dan `p19-staged12`). Lalu perbarui P20/P21 dengan tiga bagian terpisah: **fitur selesai**, **batas yang masih terbuka**, **penerimaan auditor** (belum ada). `production_go:false` tetap.

## 7. Aturan yang tetap berlaku (verbatim dari owner)

- "Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment (`vlxdhpkjeevubjxexnfo`, read-only), production."
- "Jangan mengirim pesan/notifikasi ke orang lain. Jangan meminta password, token, atau kunci di chat; pakai autentikasi lokal."
- "Jangan melonggarkan oracle/guard lama agar hasil hijau. Simpan log gagal dan fixture salah."
- "Keputusan yang sudah disahkan jangan dibuka ulang." Kebijakan tetap PENDING_POLICY_VALUE; jangan mengarang angka. Hasil LOCAL_PG16_DEV bukan bukti.

## 8. PR terkait

- [#45](https://github.com/Hanjay6688/-erp-garment-ux/pull/45) UX (cabang `claude/ux-spacing-layout`): hijau kecuali `validate-full-schema` — gagal di step "Cutting Bridge identity, ancestry, ownership, and source gate" yang sudah ada sebelum PR (sudah dikomentari). Jangan merge ke main tanpa owner.
- [#46](https://github.com/Hanjay6688/-erp-garment-ux/pull/46) bantuan owner (draft): pemotong jendela sudah diporting ke produk di `013ea062`; PR itu cukup jadi arsip bukti.

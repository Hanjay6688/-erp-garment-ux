# Fable — Putaran 16 (PRA_PEMBEKUAN): regresi CP3–5 dan keluarga CP6 pada `cp7/integration`

Tanggal: 2026-10-06. Status: **BERJALAN** (hasil per kasus diisi saat run selesai). Label semua hasil: `PRA_PEMBEKUAN` — bukan bukti lomba, bukan penerimaan. Tujuan (arahan owner): menemukan kerusakan lama akibat penggabungan CP7 lebih awal.

## 0. Identitas yang dipin
| Hal | Nilai |
|---|---|
| Head saat gerbang didispatch | `095b33b036312d80d06f897144c2772461ca35ff` (6 Okt 13:45 WIB) |
| Head saat skenario CP6 didispatch | `875443d0a0cc5323e314941412f268765ecca055` (6 Okt 14:47 WIB; satu commit E06 docs/verifier) |
| Produk & runtime auditor identik antara kedua head | `git diff --quiet 095b33b0 875443d0 -- src supabase scripts/cp7-src scripts/cp6_auditor_* .github/workflows/cp6-auditor-scenario.yml` kosong → **ya** |
| Tree produk (095b33b0) | src `2ff2f157…`, supabase/release `be1e91c1…`, supabase/migrations `8f6053bb…`, supabase/dev `88759f4f…`, scripts/cp7-src `de49632e…` |
| Paket CP6 T3 30 berkas | **identik** dengan 10a8347 (diterima CP6) |
| Runtime auditor CP6 (runner/modes/probe/driver/workflow) | **identik** dengan 10a8347 |
| Cabang masih bergerak | ya → alat dispatch menolak saat head pindah (`REF_MOVED`), sesuai §2.8 |

## 1. Run yang didispatch (ref `cp7/integration`)
| Workflow | Skenario | Head | Run |
|---|---|---|---|
| cp5-full-schema-validation.yml | (gerbang) | 095b33b0 | 37431684320 |
| cp3-r4-full-schema-validation.yml | (gerbang) | 095b33b0 | 37431681102 |
| cp6-t3-rollback.yml | (gerbang) | 095b33b0 | 37431678427 |
| cp6-t3-release-package.yml | (gerbang) | 095b33b0 | 37431675640 |
| cp6-t2-regression.yml | (gerbang) | 095b33b0 | 37431672633 |
| cp6-auditor-scenario.yml | xaudit_7.py | 095b33b0 | 37431897400 |
| cp6-auditor-scenario.yml | xaudit_1_rev2.py | 875443d0 | 37432363272 |
| cp6-auditor-scenario.yml | xaudit_2_rev2.py | 875443d0 | 37432373626 |
| cp6-auditor-scenario.yml | xaudit_8.py | 875443d0 | 37432383898 |
| cp6-auditor-scenario.yml | xaudit_9.py | 875443d0 | 37432393989 |
| cp6-auditor-scenario.yml | open_1.py | 875443d0 | 37432403123 |
| cp6-auditor-scenario.yml | gpt_c0_oracles.py | 875443d0 | 37432412781 |
| cp6-auditor-scenario.yml | xaudit_12_f1f2.py | 875443d0 | 37432422456 |
| cp6-auditor-scenario.yml | xaudit_12_f4.py | 875443d0 | 37432432152 |
| cp6-auditor-scenario.yml | xaudit_13_d07.py | 875443d0 | 37432442663 |
| cp6-auditor-scenario.yml | xaudit_14_bf.py | 875443d0 | 37432453470 |
| cp6-auditor-scenario.yml | scripts/cp6_bc_modes.py | 875443d0 | 37432464202 |
| cp6-auditor-scenario.yml | scripts/cp6_bd_modes.py | 875443d0 | 37432475448 |
| cp6-auditor-scenario.yml | scripts/cp6_be_modes.py | 875443d0 | 37432485240 |
## 2. Yang sudah bisa diklasifikasi (tanpa menunggu)
| Run | Hasil | Klasifikasi §8 | Alasan |
|---|---|---|---|
| 37431684320 `cp5-full-schema-validation.yml` | failure dalam 25 detik | **AUDITOR_TOOL / NOT_APPLICABLE** | workflow warisan cabang CP5 2026-09-03: prasyarat identitas sumber (`merge-base` = `SOURCE_BASE_SHA 8bfac13b`, tanpa merge commit, remote head = sha) tidak mungkin terpenuhi di `cp7/integration`. Bukan produk. Regresi CP5 yang berlaku = suite T2 (AR 174, AT 16, AU 15 + 326). |
| 37431681102 `cp3-r4-full-schema-validation.yml` | failure dalam 60 detik | **INFRA / EXPIRED_ARTIFACT** (+ catatan S3 untuk penulis) | langkah `download-artifact cp2-encrypted-backup` dari run 33430989888: *Artifact not found* (kedaluwarsa). Bukan produk. Catatan §16.6: bukti backup CP2 yang dirujuk workflow sudah hilang dari CI; penulis menyatakan sumber backup CP2 terpulihkan di luar CI (`RESUME_QUALIFICATION_20261005`), workflow ini perlu dipin ulang ke sumber itu atau ditandai historis. |
| 37425555179 `cp7-f03-e06.yml` (push penulis, 095b33b0) | failure | **WRITER_RUN_INCOMPLETE (hygiene)** | 4 PASS / 1 INCOMPLETE `F03_E06_MARCH_ECONOMIC_CONTROL`: semua oracle bisnis `true` (GL hari tertutup immutable, replay/inverse, fakta fisik tetap, tidak ada pengetahuan Maret yang dikarang) **tetapi `public_schema_unchanged = false`** → runner ketat menandai INCOMPLETE, gate `writer_runtime` jatuh. Ini persis INV-C06 (kasus meninggalkan skema `public` berubah). Bukan bug angka; harus diselidiki penulis (fixture membuat fungsi sementara di `public`?). Commit 875443d0 penulis menyebut "preserve first integration failure" — belum perbaikan. |

## 3. Hasil per kasus (diisi setelah run selesai)
_menunggu_

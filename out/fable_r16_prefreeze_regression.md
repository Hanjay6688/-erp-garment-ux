# Fable — Putaran 16 (PRA_PEMBEKUAN): regresi CP3–5 dan keluarga CP6 pada `cp7/integration`

Tanggal: 2026-10-06. Status: **SELESAI DIBACA PER KASUS** (6 Okt ~16:30 UTC). Label semua hasil: `PRA_PEMBEKUAN` — bukan bukti lomba, bukan penerimaan. Tujuan (arahan owner): menemukan kerusakan lama akibat penggabungan CP7 lebih awal.

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

## 3. Hasil per kasus — INDEPENDENT_NATIVE_RERUN, label PRA_PEMBEKUAN

### 3.1 Tingkat database (native): **identik dengan hasil CP6 yang diterima**
| Run | Isi | r16 pada CP7 | Pembanding CP6 (r11/r13/r14) | Putusan |
|---|---|---|---|---|
| T2 37431672633 job 326+AS34 | 525 kasus | multiset status **identik** dengan r11 (500 kasus) + 25 kasus `T2_C0_ORACLE` baru semua PASS; disposisi beku sama (CONTROL_PASS 39, DATE_POLICY_REVIEW_REQUIRED 12, MATCH 8, COUNTEREXAMPLE 20, INCOMPLETE 5 di AO_TRIAL/NEW_CASES) | sama | **tidak ada perubahan status** |
| T2 job AR 174 | 181 | 174 PASS + `ACCESSORY_CONNECTED_ZERO` INCOMPLETE (`BC_FREE_REQUIRES_POLICY`) + kasus pengganti PASS | sama (EXPECTED_CHANGE) | sama |
| T2 job AT16+AU15 | 41 | 41 PASS | 41 | sama |
| T3 paket 30 berkas (install/advisor/restore) | 30 tahap | AC..BF semua PASS, `ALL_FILES_INSTALLED`, pins dibanding ulang PASS | sama | sama |
| T3 rollback 37431678427 | — | success | sama | sama |
| xaudit_1_rev2 / 2_rev2 / 7 / 9 / open_1 / f4 / xaudit_14_bf | 6/7/14/5/15/5/6 | semua PASS | sama | sama |
| xaudit_8 | 16 | 14 PASS + 2 COUNTEREXAMPLE W8 | sama (ACCEPTED_BY_DECISION T3=A) | sama |
| C0 (gpt_c0_oracles) | 27 | 26 PASS + 1 INCOMPLETE `permission denied` | sama (AUDITOR_TOOL) | sama |
| xaudit_12_f1f2 | 10 | 9 PASS + `BC_ABSENT` FAIL | sama (GUARD_BY_DESIGN) | sama |
| xaudit_13_d07 | 5 | 4 PASS + `NEG_FACT_TAMPER` INCOMPLETE | sama (append-only, INV-K07) | sama |
| modes BC (races/HTTP/browser) | 18 | 18 PASS | 18 | sama |
| modes BD native/races/HTTP | 12 | 12 PASS (+8 browser: 7 PASS, 1 INCOMPLETE → §3.2) | 20/20 | **browser berubah** |
| modes BE native/races/HTTP | 11 | 11 PASS (+6 browser: 4 PASS, 2 INCOMPLETE → §3.2) | 17/17 | **browser berubah** |

Kesimpulan 3.1: penggabungan CP7 **tidak mengubah satu pun hasil angka/stok/HPP/jurnal** dari suite CP3–5 dan CP6 pada head ini.

### 3.2 Tingkat browser: **11 kasus CP6 yang dulu PASS kini INCOMPLETE pada UI CP7** (baru)
| Kasus (run) | Gejala | Yang saya temukan di kode CP7 (INDEPENDENT_SOURCE_REVIEW) | Klasifikasi awal | Keparahan |
|---|---|---|---|---|
| `BE_BROWSER:REWORK_SKU_PARTIAL_COMPLETE_REVERSE`, `BE_BROWSER:REDYE_SKU_UNKNOWN_THEN_PRICE_MOBILE` (modes BE 37432485240; T3 browser 37431675640) | tombol `.cbsr-search` "Cari" tidak ada | `ConnectedBsResolutionPage.tsx` dirombak (+93 baris): kepala halaman memakai `RecordTools` seragam ("Cari kasus", browse, urutkan) sesuai mandat owner submenu; kelas `cbsr-search` dihapus, fungsi cari **masih ada** (`aria-label="Cari BS atau claim"`) | **STALE_TEST_SELECTOR** (uji CP6 penulis belum diperbarui ke UI CP7) | S3 untuk penulis: perbarui/retire uji; **fungsi tetap** |
| `BF_BROWSER:SALES_MANUAL_13_DESKTOP/MOBILE` (T3 browser) | `.biz-size-entry` 0 elemen | `App.tsx` CP7: dalam `DISPOSABLE_TEST`, rute penjualan kini merender `ConnectedSalesPage` (P11 terhubung), bukan halaman simulasi `SalesPages`; uji ini memang berlabel "Sales UX simulation only" | **SUPERSEDED_BY_CP7** (halaman demo digantikan halaman terhubung) | S3: retire, ganti dengan uji P11 |
| `READINESS_BROWSER:DESKTOP/MOBILE_NATIVE_POLICY_STATES_FINANCE_NOTE` (T3 browser) | di Keuangan → HPP & Rekalkulasi, `role=alert` diharapkan 0, terlihat **2** | CP7 menambah `role="alert"` dari 49 → 200 di `src/`; `App.tsx` merutekan `finance-overview` ke `ConnectedFinanceOverviewPage` baru yang menampilkan alert untuk gerbang izin, `error`, dan `recoveryBlocked`. Login uji = OWNER, jadi 2 alert itu kemungkinan **error pembaca atau blokir pemulihan** pada halaman keuangan, bukan gerbang izin. Teks alert tidak tertangkap log. | **UI_ALERT_UNEXPLAINED** — perlu teks alert | **S2 sementara** (bisa S1 bila halaman keuangan selalu menampilkan error di runtime uji) |
| `BD_BROWSER:LAU_T36_PHONE_MIXED_COVERAGE` (modes BD, T3 browser), `BD_REV_BROWSER:FREE_MASTER_THEN_PHYSICAL_DESKTOP`, `…WAIVED_MASTER_THEN_PHYSICAL_MOBILE` (T3 browser) | select "Pilihan rincian biaya" tidak muncul dalam 20 s | label **masih ada** di `LaundryBdPanel.tsx:289`, tetapi hanya dirender setelah batch terpilih; `useLaundryQcWorkspace.ts` (+33) dan `ConnectedQcFinalPage.tsx` (+63) berubah di CP7 (pembaca ledger v2). Kemungkinan alur data batch berubah sehingga panel tidak sampai ke langkah pilih rincian. Kasus yang sama **lulus di PR 39** (r15). | **UI_FLOW_CHANGE_UNVERIFIED** | **S2 sementara** (LAU-T36 cakupan campuran & FREE/WAIVED adalah fungsi yang owner minta usable) |
| AT flow `cp6_au_browser_ui.mjs:130` (`Merek hasil WIP` expected disabled) (T3 browser) | elemen tidak ditemukan 5 s | label masih ada di `ConnectedInitialImportPage.tsx:144`; halaman impor saldo awal berubah di CP7 (uji DOM-nya 185→204 baris) | **UI_FLOW_CHANGE_UNVERIFIED** | S2 sementara |

Catatan: `WRITER_PACKAGE_RUNTIME` penulis sendiri menilai job browser ini `INCOMPLETE` (8 dari 31), lalu gate T3 `BROWSER_FAIL`. Artinya **paket rilis CP6 yang sama, dipasang di cabang CP7, tidak lagi lolos bukti browser CP6-nya**. Angka tidak berubah; yang berubah adalah kontrak layar.

### 3.3 Temuan pra-pembekuan untuk penulis (bukan register lomba)
| ID | Isi | Tindakan yang disarankan |
|---|---|---|
| PRE-01 (S2) | Dua `role=alert` pada halaman Keuangan (HPP & Rekalkulasi) saat login OWNER di runtime uji | tangkap teks alert di uji readiness; bila error pembaca/pemulihan, perbaiki sumbernya; bila gerbang izin yang salah peran, perbaiki gerbang |
| PRE-02 (S2) | Panel Laundry "Rincian biaya" tidak tercapai di 3 kasus BD yang dulu lulus | telusuri perubahan `useLaundryQcWorkspace`/pembaca v2 vs fixture BD; buktikan LAU-T36 dan FREE/WAIVED masih bisa dipakai di UI CP7 |
| PRE-03 (S2) | AT flow saldo awal: field "Merek hasil WIP" tidak ditemukan | periksa perubahan halaman impor saldo awal di CP7; perbarui uji atau pulihkan perilaku |
| PRE-04 (S3) | Uji BE browser memakai selector `.cbsr-search` yang dihapus | perbarui ke `RecordTools` ("Cari kasus" / `Cari BS atau claim`) |
| PRE-05 (S3) | Uji BF `SALES_MANUAL_13` menguji halaman simulasi yang tak lagi dirutekan di runtime uji | retire; cakupan lusin/PCS pindah ke uji P11 `ConnectedSalesPage` |
| PRE-06 (S3) | Workflow `cp3-r4-full-schema-validation` bergantung artefak CI `cp2-encrypted-backup` yang kedaluwarsa; `cp5-full-schema-validation` terikat identitas cabang lama | pin ulang ke sumber backup CP2 yang dipulihkan atau tandai historis; nyatakan suite T2 sebagai regresi CP3–5 yang berlaku |
| PRE-07 (hygiene) | E06 `F03_E06_MARCH_ECONOMIC_CONTROL`: `public_schema_unchanged=false` | bersihkan fixture (fungsi sementara di `public`?), INV-C06 |

### 3.4 Putusan pra-pembekuan
- **Kerusakan lama akibat penggabungan di tingkat angka: tidak ada.** 525+181+41 kasus T2, 30 tahap T3, rollback, dan 14 skenario CP6 identik dengan hasil yang diterima.
- **Kerusakan di tingkat layar CP6: ada 11 kasus**, 4 di antaranya uji basi/superseded (S3), 7 perlu penyelidikan penulis (S2 sementara) karena fungsi yang owner minta "bisa dipakai" (LAU-T36, FREE/WAIVED, saldo awal WIP, halaman keuangan) belum terbukti di UI CP7.
- Belum waktunya membekukan kandidat: E06 masih merah, PRE-01..03 terbuka, cabang bergerak.

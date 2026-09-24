# AUDIT_REPORT_CP6 (v2, konsolidasi) — Audit independen kandidat CP6 ERP Garment `9add57e`

**Status:** rekomendasi auditor untuk owner dan writer. **Belum ada keputusan gate.** `production_go=false` sampai owner memutuskan. **Rekomendasi: CP6 tetap HOLD.**
**Versi:** v2 (2026-09-24 19:35 UTC) menggabungkan dua audit independen atas kandidat yang sama dan memverifikasi silang klaim keduanya; menggantikan v1 (sha256 `10fd4c83…`). Berkas kunci fase 1 kedua audit tidak diubah.

## 0. Identitas, sumber kebenaran, dan dua audit yang digabung
| Hal | Nilai |
|---|---|
| Kandidat beku | `Hanjay6688/-erp-garment-ux` cabang `claude/new-session-deapao` @ `9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc` (tree `5d5f833b2e75e23184c643d5ac469781f1c3ce5e`) |
| Baseline | `competition/cp6-j-closure-20260911` @ `ca7f09556397801c50a2277bdb65b1bf019f9a05` |
| Kontrak (satu-satunya oracle) | M `ERP_V3_2_Master_Pulih_20260923.md` (sha256 f21ac70360915a1f1021b42a3918e862ca7d11cf88c1b90c5627b4490c69af07), P `ERP_V3_2_Perubahan_Pulih_20260923.md` (92966cd6ed27e64123be6c52e2263bfbdb3db91c97f2e441c3bdc98589397676), A `ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md` (4566ab6f1c8e53bc21c70c0c777f780b526305815e04d5913a5c858dfaa85886). `M:n` = nomor baris Master. |
| **Audit A** (laporan ini, sesi auditor dengan runtime dispatch) | Kunci fase 1 `audit/PHASE1_FINDINGS.md` sha256 `72ccbfe8613fca783be4050f0f722096262c9849e6a308adc6f37bc68e41ab6e`; 11 skenario native, 15 run pada 9add57e; fase 2 di `audit/out/phase2_reconciliation.md` |
| **Audit B** (laporan auditor kedua, diunggah owner, disimpan `audit/input/AUDIT_REPORT_CP6_auditor2.md`, sha256 `eea36bd9b49a6b85256a47b40ed2f42606b69417aa44134f390e7062ffbbe38c`) | Kunci fase 1 mereka `cbca0c6c…`, manifest `50ba9228…`; tanpa kemampuan dispatch workflow (8 kasus SQL mereka **NOT_RUN**); rerun ulang job T2/T3/CodeQL milik run Audit A (attempt 2); probe frontend lokal; bundel bukti mereka (`CP6_AUDIT_EVIDENCE_9add57e.zip`) TIDAK diterima Audit A — hanya laporannya. |
| Verifikasi silang | Audit A memverifikasi setiap temuan Audit B terhadap sumber kandidat (INDEPENDENT_SOURCE_REVIEW), probe lokal (INDEPENDENT_ARTIFACT_CHECK), dan **secara native** lewat runtime skenario auditor (run 36048357523, job 107797410652, skenario `xaudit_1.py`). Audit B membaca laporan/temuan Audit A hanya sebagai "lead" (mereka mencatat kebocoran itu). |

**Label bukti:** INDEPENDENT_NATIVE_RERUN (run yang di-dispatch auditor pada 9add57e; status dibaca per kasus dari log JSON, bukan warna job) · INDEPENDENT_SOURCE_REVIEW · INDEPENDENT_ARTIFACT_CHECK · REUSED_EVIDENCE (run 36034620907 milik GPT; hanya jalur yang diujinya) · UNVERIFIED_OWNER_DECISION (keputusan owner yang hanya ada di handoff/skrip writer, tidak di M/P/A) · Label silang: **CONFIRMED / REFUTED / UNVERIFIED** untuk klaim writer dan klaim Audit B.

**Protokol buta:** fase 1 kedua audit tanpa `docs/cp6-*.md`, `docs/evidence/`, audit lama. Kontaminasi Audit A: pesan commit terpapar lewat `git worktree add`/API run (tidak dipakai sebagai oracle). Kontaminasi Audit B (dinyatakan mereka): memory audit lama, judul commit di UI Actions, bocoran temuan Audit A oleh user. Fase 2 keduanya dibuka setelah hash kunci dicatat.

**Catatan run:** run 36037876338 (T3), 36037873682 (T2), 36037878419 (CodeQL) yang di-dispatch Audit A kemudian di-*re-run* oleh pihak lain (attempt 2–4, semua head_sha 9add57e). Bukti Audit A memakai attempt 1 (job ID di §9); Audit B memakai attempt 2 (job 107772603343, 107772639059, 107772676223). Hasil keduanya konsisten.

## 1. Ringkasan eksekutif (gabungan)
1. **Kandidat 9add57e terpasang verbatim dan gate writer direproduksi** oleh kedua audit: T2 identik per kasus dengan referensi AU (12 HOLD, 8 AS COUNTEREXAMPLE, 1+4 INCOMPLETE; oracle-disetujui MATCH), T3 hijau (24 berkas, restore drill RESTORED_SAME_MEANING), CodeQL 0 hasil, vitest 454/454. Verdict T2 tetap `DISPOSITION_REQUIRED`.
2. **Temuan produk P1 yang terbukti (native atau deterministik):**
   - **F1-12** stok/nilai awal DOBEL lewat dua batch impor untuk item stok yang sama (MATERIAL dan FG): +15,75 dua kali untuk 7 unit fisik; guard AR hanya membandingkan impor vs legacy (Audit A, native, 2 run).
   - **F1-14** (= Audit B F01) waktu bisnis tiga halaman aktif (Potongan, Bagi Potongan, BS Resolution) mengikuti zona perangkat, bukan WIB: `new Date(v).toISOString()`; pada perangkat WITA/UTC/Kiritimati tanggal fisik bergeser (terbukti deterministik dengan probe Node 4 zona; facade menyimpan apa adanya). Halaman Laundry/QC sudah memakai helper WIB yang benar.
   - **F1-05** (= Audit B R02) rollback paket rilis T3 tidak pernah diuji (`rollbacks: NOT_TESTED`); tambahan Audit B (diverifikasi A): guard rollback AC hanya menerima digest `7b5690a2…`/`7a3613d8…`, sedangkan berkas AC versi rilis ber-sha256 `871fb32b…` → bahkan rollback AC tidak akan diterima di DB yang dipasang dari paket rilis.
   - **F1-16** (= Audit B U02) penyelesaian ulang WIP saldo awal bertanggal SEBELUM pembalikan penyelesaian sebelumnya DIBUKUKAN: saldo tahap SEWING −8 pcs dan WIP GL PO −20,00 pada hari itu (prefix histori negatif). CONFIRMED (native).
   - **F1-01** celah kontrak tanggal koreksi: 25 hasil T2 bergantung keputusan owner 24 Sep yang hanya ada di handoff; bacaan literal ERP-DEC01 secara fisik tidak konsisten (kedua audit sependapat: MATCH ≠ PASS beku).
3. **Temuan P2 produk:** **F1-17** (= Audit B U03) pembulatan koreksi harga pada 1 unit yang habis dikonsumsi meninggalkan nilai bahan ≠ 0 pada qty 0 (naik: persediaan −0,01 dan WIP 10,02; turun: persediaan +0,01 dan WIP 10,00) — naik CONFIRMED (native); turun CONFIRMED (native). **F1-15** (= Audit B U01) selector sumber laundry di BS Resolution dipotong `LIMIT 100` tanpa paging/pencarian pada lookups; sumber lama yang masih claimable bisa hilang dari daftar (sumber terkonfirmasi; native NOT_RUN). **F1-02** dua status ERP-DEC03 di kontrak.
4. **Tooling/protokol:** runner skenario menimpa hasil id ganda dan meloloskan status di luar kosakata (F1-04 = Audit B R01, terbukti native A); job install T3 hijau tidak bergantung pada restore drill/`primary_unchanged`/advisor (F1-18 = Audit B O01, sumber `cp6_t3_package_run.py:134-148`); harness T2 melengkapi fixture atas dasar keputusan di luar kontrak (F1-03).
5. **Yang LULUS oracle auditor pada 9add57e** (Audit A, native): tutup buku S06 atomik + penolakan persis + filing immutable; akses fail-closed 10 facade baru untuk anon/unmapped/nonaktif/5 role non-owner (lapisan DB); aksesori 7 PCS eceran persis M:94 (lifecycle + reversal); FG tanpa sumber (konservasi, 9 penolakan persis, periode tertutup); tumpang tindih jalur lama setelah impor ditolak 10/10; total kontrol tidak dibukukan; replay batch ditolak; replay UUID sama + payload beda ditolak persis `client_request_id was already used with a different payload` (native, PASS: replay UUID sama+payload beda DITOLAK; pesan produk: `client_request_id was already used with a different payload`); keluarga tanggal bentuk tak-ambigu dan periode tertutup; AZ menghilangkan WIP/persediaan negatif per tanggal pada bentuk dasar.

## 2. Verdict per gate (kontrak) dan pemetaan ke pengelompokan Audit B
| Gate (A) | Isi | Rujukan | Verdict gabungan | Dasar / batas | Gate B terkait |
|---|---|---|---|---|---|
| GATE-01 | Perlindungan tumpang tindih saldo awal pada SEMUA jalur | M:138, M:229, M:361, M:1043 | **HOLD** | Legacy setelah impor ditolak 10/10 (run 36044022037); impor→impor lintas batch DIBUKUKAN dan menggandakan stok (F1-12, run 36045629594) | C6-04 (UNVERIFIED di B; A: HOLD dengan bukti native) |
| GATE-02 | Gerbang gabungan keluarga terdampak pada kandidat beku | M:138, M:1763-1765, M:6661 | **HOLD** | T2 direproduksi identik (A run 36037873682; B attempt 2), verdict DISPOSITION_REQUIRED; 25 hasil bergantung keputusan di luar kontrak (F1-01) | C6-01, C6-05 (HOLD di B) |
| GATE-03 | Gerbang lama Full-Schema/Final Boundary tidak dilonggarkan/dilabel ulang | M:136, M:223, M:957 | **UNVERIFIED** | Tidak diperiksa kedua audit; T2 tidak melabel ulang hasil beku (CONFIRMED) | — |
| GATE-04 | HTTP/Auth-JWT/browser nyata + concurrency dua koneksi | M:229, M:317, M:422, M:4321 | **UNVERIFIED** | Kedua audit hanya identitas lapisan DB; browser writer 10 kasus = REUSED_EVIDENCE; concurrency hanya T2 AR_CONCURRENCY writer | C6-08, C6-09 (UNVERIFIED di B) |
| GATE-05 | 12 kasus tanggal HOLD ditutup di bawah ERP-DEC01 satu keluarga | M:1057-1065, M:1080-1086, M:1404, M:6144-6169 | **HOLD** | DECISION_EXISTS_EVIDENCE_MISSING; produk mengikuti aturan 24 Sep (UNVERIFIED_OWNER_DECISION); bentuk tak-ambigu/periode tertutup LULUS oracle A (run 36041422305, 36042210333) | C6-05 (HOLD) |
| GATE-06 | Jalur eceran PCS exact (ACC-DEC02) | M:1066-1071, M:1405, M:44, M:94 | **ACCEPT (terbatas)** | 7 PCS @3,25 → 22,75, stok 300→293, master tetap, replay, REVERSE pulih, 5 penolakan (run 36043204365); satu sesi; concurrency AQ tidak diuji auditor | C6-07 (UNVERIFIED di B karena mereka tidak native; A: native) |
| GATE-07 | Transport CSV nyata / ERP-DEC03 / ALL | M:138, M:1024-1025, M:1043, M:1072-1078, M:6381 | **HOLD** | F1-02; parser CSV browser ada; cakupan ALL end-to-end tidak diverifikasi keduanya | C6-04 |
| GATE-08 | Cakupan role/akses CP6 (AUD-G07) | M:1729, M:1407, M:1526, M:98, M:1322 | **HOLD** | Lapisan DB LULUS (run 36043758572, 36044313409; viewer baca aksesori sesuai M:281); HTTP/JWT nyata tidak diuji | C6-08 |
| GATE-09 | Keluarga perbaikan writer VERIFIED_INDEPENDENT | M:1259, M:1308, M:1720-1722, M:1222-1224 | **HOLD** | CONFIRMED: A04 vitest, S06/B04, AX perilaku, AZ bentuk dasar, AQ 7 PCS, AO/AP total kontrol. HOLD/BARU: F1-14 (input waktu bisnis), F1-15 (selector), F1-16/F1-17 (lihat §3). UNVERIFIED: AV perilaku, cabang AY rev6–7.4 | C6-02, C6-03, C6-06 |
| GATE-10 | Paket migrasi permanen: install / rollback / penolakan, byte-bound | M:163, M:206, M:108-115, M:2713-2719 | **HOLD** | Install 24/24 + verify + restore drill CONFIRMED (A run 36037876338; B attempt 2); rollback NOT_TESTED + digest AC rilis tidak diterima guard rollback (F1-05) | C6-10 (HOLD) |
| GATE-11 | Freeze SHA/tree/runtime; bukti terikat commit | M:1767, M:132 | **ACCEPT** | Runtime menginstal 9add57e verbatim (40/40 fungsi dev; run 36039753521); semua run head 9add57e. Catatan B (C6-01 HOLD karena R01/T2): R01 adalah cacat alat (F1-04), identitas kandidat sendiri terbukti | C6-01 |
| GATE-12 | Audit independen dengan oracle sendiri atas perbaikan DAN jalur residual | M:4500-4501, M:1436-1437 | **HOLD (sebagian terpenuhi)** | Dua audit independen; residual di §7 | — |
| GATE-13 | Tidak ada POLICY_BLOCKED/INCOMPLETE/HOLD dalam scope saat lock | M:1699, M:4387, M:1220-1221 | **HOLD** | 12 HOLD + 8 + 5 tetap; temuan baru F1-12, F1-14, F1-16/17 | — |
| GATE-14 | CP6_LOCK_READY sah lalu acceptance owner | M:1218-1219, M:1418-1420, M:229 | **BELUM (milik owner)** | — | — |
| GATE-15 | Matriks historis: label bukti jelas | M:4391, M:1766, M:1161-1163 | **UNVERIFIED** | — | C6-01 |
| GATE-16 | CR aksesori/laundry tuntas atau dikecualikan owner | M:1755-1756, M:1697 | **HOLD** | Tidak ada pernyataan owner di kontrak (B sependapat: "scope CR belum diputuskan") | C6-07 |

Perbedaan verdict A vs B yang perlu dicatat: B menilai C6-04/C6-07 UNVERIFIED karena mereka tidak bisa native; A menjalankan native → HOLD (F1-12) dan ACCEPT terbatas (7 PCS). B menilai C6-01 HOLD karena R01; A memisahkan identitas kandidat (ACCEPT) dari cacat alat (F1-04). Tidak ada verdict yang saling bertentangan pada substansi.

## 3. Temuan gabungan (P0 tidak ada). PRODUK dan TOOLING dipisah. ID `F1-xx` = Audit A; `(B: …)` = ID Audit B.
### 3A. Produk
**F1-12 — P1 — Stok/nilai awal dobel lewat dua batch impor (tumpang tindih impor→impor tidak dijaga)** — Audit A, INDEPENDENT_NATIVE_RERUN ×2.
- Reproduksi: impor MATERIAL 7 PCS @2,25 → POSTED; batch baru dengan `material_sku`+`location_code`+qty+unit_cost+cutover sama → FINALIZE → `POSTED, valid_rows 2, error_rows 0`; sama untuk cutover lebih awal dan FINISHED_GOODS.
- Oracle: M:138, M:1043, M:43-46, M:10. Hasil: `MATERIAL_INVENTORY +15,75` kedua kalinya; item POSTED 1→2, qty 7→14; FG `FG_INVENTORY +15,75`. Replay batch yang sama DITOLAK persis `Impor yang sudah disahkan tidak dapat diedit atau disahkan ulang dengan permintaan baru`.
- Akar: `supabase/migrations/20260922185015_erp_v2_6_20ar_cp6_opening_overlap.sql:372` predikat `((h.migration_batch_id is null)<>(oh.migration_batch_id is null))`. Writer mengakui batas AR (`docs/cp6-ar-opening-overlap.md:59-62`) tetapi item ini tidak ada di daftar terbuka handoff.
- Bukti: run 36044022037 job 107782968845 (`open_1.py`), run 36045629594 job 107788356714 (`open_2.py`); JSON `audit/runs/`.

**F1-14 (B: F01) — P1 — Waktu bisnis tiga halaman aktif mengikuti zona perangkat, bukan WIB** — CONFIRMED oleh Audit A: INDEPENDENT_SOURCE_REVIEW + INDEPENDENT_ARTIFACT_CHECK (deterministik).
- Oracle: M:3820 "Jam perangkat tidak menggantikan waktu bisnis WIB"; M:1691 (keluarga input dalam penutupan CP6).
- Sumber: `src/ConnectedCuttingPage.tsx:272` `cut_at: new Date(cutAt).toISOString()`; `src/ConnectedPickupPage.tsx:200` `picked_up_at: new Date(pickedUpAt).toISOString()`; `src/ConnectedBsResolutionPage.tsx:40` `toIso = (v) => new Date(v).toISOString()` (dipakai di 87,143,231,275,288,305). Route aktif `src/App.tsx:607,609,665`. Facade menyimpan apa adanya: `20260903022604_…cutting_persistence_pickup_wip.sql:656` `v_cut_at:=…::timestamptz`, `:759`, `:1009` `v_picked_up_at`. Kontrol positif: `src/cp6BusinessTime.ts:16-25` `cp6WibPhysicalTimeToIso` (offset +07:00 eksplisit) hanya dipakai `ConnectedLaundryPage.tsx` dan `ConnectedQcFinalPage.tsx`.
- Reproduksi Audit A (Node, ekspresi identik dengan sumber, input `2026-09-20T00:30`): TZ Asia/Jakarta → `2026-09-19T17:30Z` (= helper WIB, PASS kontrol); TZ UTC → `2026-09-20T00:30Z` (7 jam terlambat); TZ Pacific/Kiritimati → `2026-09-19T10:30Z`; **TZ Asia/Makassar (WITA, Indonesia) → `2026-09-19T16:30Z`** (hari bisnis WIB menjadi 19 Sep, bukan 20 Sep). Skrip `audit/tools/tzprobe.mjs`.
- Dampak: `cut_at`/`picked_up_at`/`physical_at` BS salah untuk operator di luar WIB (termasuk WITA/WIT), sehingga tanggal jurnal issue potongan (`(g.cut_at AT TIME ZONE 'Asia/Jakarta')::date`, AC:3455), prefix histori roll, dan laporan per tanggal bergeser. Efek ledger aktual tidak diuji native (deterministik dari sumber).
- Perbaikan yang diharapkan: ketiga halaman memakai `cp6WibPhysicalTimeToIso` (+ input `nowInput` BS yang juga memakai offset perangkat, baris 36-39), tes unit matriks zona + DOM.

**F1-05 (B: R02) — P1 (produk/protokol rilis) — Rollback paket T3 tidak pernah diuji; guard rollback AC tidak menerima varian rilis** — CONFIRMED (A: INDEPENDENT_ARTIFACT_CHECK + NATIVE_RERUN; B: SOURCE_REVIEW).
- `supabase/release/cp6-t3/MANIFEST.json:1372` `"rollbacks": "NOT_TESTED"`; tidak ada rollback AW..AZ di `supabase/rollbacks/` (terakhir AV); job install T3 tidak punya tahap rollback/penolakan pasca-pakai.
- Tambahan (B, diverifikasi A): `supabase/rollbacks/20260915031500_…20ac….rollback.sql:12-16` hanya menerima digest `7b5690a2…` / `7a3613d8…` untuk pernyataan ledger AC; applier T3 menyimpan seluruh teks berkas rilis sebagai satu statement ledger (`scripts/cp6_t3_release_package.py:211-213`); sha256 berkas AC rilis = `871fb32b1d4a1e7f9aedfef684b0f2c766092732c38552620eb394061f6240d1` ≠ digest yang diterima (sha256 berkas migrasi AC = `7b5690a2…`). Jadi di DB yang dipasang dari paket rilis, rollback AC yang ada pun menolak (`AC_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR`). Guard ini benar (fail-closed) dan tidak boleh dilonggarkan; yang hilang adalah set rollback terikat sumber untuk paket rilis.
- Oracle: M:108-115, M:206, M:2713-2719, M:3826, M:4306-4314. Writer mengakui (handoff §23.9 N2).

**F1-16 (B: U02) — P1 — Penyelesaian ulang WIP saldo awal bertanggal sebelum pembalikan penyelesaian sebelumnya dibukukan; prefix WIP negatif** — CONFIRMED (native)
- Oracle: M:369-371 (jumlah berlebih/versi usang/tanggal sebelum cutover ditolak; pembatalan membuat event kebalikan tertaut) dan M:3820 ("Backdate tidak boleh merusak prefix qty/value pada timeline").
- Sumber (B, diverifikasi A): `supabase/dev/cp6_az_t1_family.sql:817-818` sisa = qty − Σ output yang belum dibalik, tanpa dimensi tanggal; pembalikan `:837-845` bertanggal `statement_timestamp()`; batas tanggal COMPLETE `:850-853` hanya ≥ cutover dan ≤ hari ini — tidak ≥ tanggal pembalikan.
- Native Audit A (run 36048357523 job 107797410652, kasus `XA:U02_WIP_RECOMPLETION_DATED_BEFORE_REVERSAL`; fixture writer `cp6_initial_import_production_trial`: WIP 8 pcs @5 = 40 cutover D−8, selesai 8 pada D−3, dibalik pada D, selesai lagi 8 bertanggal D−1): second_result={'action': 'WIP_OUTPUT', 'lot_id': '0dc1f62b-b4cd-4546-b931-9233c323344f', 'status': 'POSTED', 'batch_id': '32d8e290-a9eb-4da5-8830-c1e01d596245', 'operation': 'COMPLETE', 'output_id': '46a80c6a-59f5-; refusal=null; stage=SEWING; cutover=2026-09-17; completion1=2026-09-22; reversal=2026-09-25; completion2=2026-09-24; saldo tahap per hari sesudah={"2026-09-17": "8", "2026-09-18": "8", "2026-09-19": "8", "2026-09-20": "8", "2026-09-21": "8", "2026-09-22": "0", "2026-09-23": "0", "2026-09-24": "-8", "2026-09-25": "0"}; WIP GL PO per hari={"2026-09-17": "60.00", "2026-09-18": "60.00", "2026-09-19": "60.00", "2026-09-20": "60.00", "2026-09-21": "60.00", "2026-09-22": "20.00", "2026-09-23": "20.00", "2026-09-24": "-20.00", "2026-09-25": "20.00"}; hari negatif (tahap)=['2026-09-24']; hari negatif (GL)=['2026-09-24']
- Hasil: penyelesaian kedua (8 pcs, tanggal D−1 = 24 Sep) POSTED tanpa penolakan; saldo tahap SEWING per hari 8,8,8,8,8,0,0,**−8**,0 (17–25 Sep); WIP GL PO 60→20→**−20,00** (24 Sep)→20. Prioritas P1: histori fisik dan nilai WIP negatif pada prefix (M:3820), sisa dihitung tanpa dimensi tanggal.

**F1-17 (B: U03) — P2 — Pembulatan koreksi harga pada 1 unit yang habis dikonsumsi meninggalkan nilai bahan ≠ 0 pada qty 0** — naik: CONFIRMED (native); turun: CONFIRMED (native)
- Oracle: M:1022, M:1059-1065, M:3820: satu unit diterima dan habis dikonsumsi meninggalkan qty dan nilai bahan 0; WIP membawa nilai terkoreksi dibulatkan ke sen; tidak ada persediaan harian negatif.
- Sumber (B): AC:3437-3458 (nilai issue dibulatkan), AZ rilis `:256-279` (`round(qty_signed*(current−original),2)`: selisih 0,009 → 0,01), AP:3292-3314 & AC:1327-1347 (delta endpoint yang sudah dibulatkan: 0,00). Diverifikasi A: baris-baris itu ada dan berisi pembulatan seperti dinyatakan.
- Native Audit A (run 36048357523; penerimaan FINAL 1 unit 21 Sep, potong seluruhnya 22 Sep, koreksi harga 23 Sep): NAIK 10,005→10,014 → delta akhir persediaan **−0,01** (qty 0), WIP **10,02** (seharusnya 10,01), persediaan harian negatif sejak 23 Sep; TURUN 10,014→10,005 → persediaan **+0,01** pada qty 0, WIP 10,00. Prediksi Audit B tepat. Dampak: nilai residu ±0,01 per koreksi pada bahan yang sudah habis; sisi negatif dapat memicu blocker `GL_INVENTORY_NEGATIVE_ASOF` pada tutup buku. Rincian: NAIK status=COUNTEREXAMPLE; checks={"correction_posted": true, "raw_qty_zero": true, "inventory_value_zero_at_end": false, "wip_equals_rounded_corrected_value": false, "no_negative_daily_inventory": false}; delta akhir (vs sebelum penerimaan)={"MATERIAL_INVENTORY": "-0.01", "WIP": "10.02", "FG_INVENTORY": "0", "COGS": "0"}; delta setelah potong={"MATERIAL_INVENTORY": "0.00", "WIP": "10.01", "FG_INVENTORY": "0", "COGS": "0"}; expected_wip=10.01; raw_qty=0.000000; pergerakan=[["PURCHASE", "1.000000", "10.014000", "10.005000"], ["CUTTING_ISSUE", "-1.000000", "10.014000", "10.005000"]]; refusal=null; delta harian={"2026-09-21": {"MATERIAL_INVENTORY": "10.01", "WIP": "0.00"}, "2026-09-22": {"MATERIAL_INVENTORY": "0.00", "WIP": "10.01"}, "2026-09-23": {"MATERIAL_INVENTORY": "-0.01", "WIP": "10.02"}, "2026-09-24": {"MATERIAL_INVENTORY": "-0.01", "WIP": "10.02"}, "2026-09-25": {"MATERIAL_INVENTORY": "-0.01", "WIP": "10.02"}} · TURUN status=COUNTEREXAMPLE; checks={"correction_posted": true, "raw_qty_zero": true, "inventory_value_zero_at_end": false, "wip_equals_rounded_corrected_value": true, "no_negative_daily_inventory": true}; delta akhir (vs sebelum penerimaan)={"MATERIAL_INVENTORY": "0.01", "WIP": "10.00", "FG_INVENTORY": "0", "COGS": "0"}; delta setelah potong={"MATERIAL_INVENTORY": "0.00", "WIP": "10.01", "FG_INVENTORY": "0", "COGS": "0"}; expected_wip=10.00; raw_qty=0.000000; pergerakan=[["PURCHASE", "1.000000", "10.005000", "10.014000"], ["CUTTING_ISSUE", "-1.000000", "10.005000", "10.014000"]]; refusal=null; delta harian={"2026-09-21": {"MATERIAL_INVENTORY": "10.01", "WIP": "0.00"}, "2026-09-22": {"MATERIAL_INVENTORY": "0.00", "WIP": "10.01"}, "2026-09-23": {"MATERIAL_INVENTORY": "0.01", "WIP": "10.00"}, "2026-09-24": {"MATERIAL_INVENTORY": "0.01", "WIP": "10.00"}, "2026-09-25": {"MATERIAL_INVENTORY": "0.01", "WIP": "10.00"}}

**F1-15 (B: U01) — P2 — Selector sumber laundry BS Resolution dipotong 100 baris tanpa paging** — CONFIRMED sumber (A); native NOT_RUN (keduanya).
- `supabase/migrations/20260903070932_…cp5_bs_resolution_recovery.sql:768-770` `where d.status in('SENT','PARTIAL_RETURN','RETURNED','CLOSED') … order by d.physical_at desc,d.id limit 100`; `:799`, `:828` limit 100 untuk penerimaan/klaim selesai; successor `20260904012525_…19b…:682-690` `erp_get_bs_resolution_workspace_v1(p_limit,p_offset)` hanya memaginasi `rows` — kata `lookups` tidak ada di 19b; UI `src/ConnectedBsResolutionPage.tsx:101,110` menyaring `qty_claimable_pcs > 0` SETELAH cap. Oracle: M:1691 "selector lengkap", M:3826, M:4486. Sumber lama yang masih claimable di luar 100 terbaru tidak dapat dipilih (fixture 101 sumber belum dijalankan).

**F1-01 — P1 (CONTRACT_GAP, bukan bug produk)** — kedua audit sependapat: keputusan 24 Sep (8 AS, prinsip WIP, 12 kalender, AO, ADJUSTMENT_DATE) hanya ada di handoff/skrip; MATCH oracle-disetujui bukan PASS beku; bacaan literal ERP-DEC01 menghasilkan WIP negatif (bukti A run 36041435083/36042223829 vs after). Owner harus menulis aturan penyelesaiannya ke kontrak, lalu kasus di-oracle ulang dan dijalankan ulang.

**F1-02 — P2 (CONTRACT_GAP)** ERP-DEC03/ALL dua status (M:1072-1078 vs M:1024); parser CSV browser ada (`src/initialImport.ts`); cakupan ALL end-to-end UNVERIFIED (B: C6-04 UNVERIFIED, sependapat).

**F1-06 — P3** Advisors 73→127 (+54 INFO `rls_enabled_no_policy`); B menelusuri 54 tabel: RLS aktif + REVOKE ALL tanpa grant lanjutan (INFO ≠ eksposur). Tetap REVIEW_REQUIRED tanpa ambang kontrak (M:112).

**Hipotesis (tidak dipromosikan menjadi defect; perlu keputusan/uji):**
- **H01 (B)** — penyelesaian WIP saldo awal tidak membandingkan produk opsional pada item opening: A memverifikasi `cp6_az_t1_family.sql:855-862` memilih produk dari `product_sku` payload + model PO + size sumber, tanpa merujuk `opening_balance_items.product_id`. Apakah kontrak mewajibkan pengikatan (M:369 "produk/model/ukuran yang sesuai") belum jelas → UNVERIFIED (keputusan owner + uji native).
- **H02 (B)** — edit DRAFT native yang sudah di-prepare meninggalkan sumber/kontrol lama → UNVERIFIED (tidak diuji kedua audit).
- **Ditarik:** A F1-09 (potong sebelum penerimaan; REFUTED native), A F1-13 (viewer baca aksesori; sesuai M:281). Catatan: teks penolakan SI03 yang diharapkan Audit B (`client_request_id was already used with a different payload`) tidak ditemukan grep di sumber SQL kandidat, tetapi memang dipancarkan produk secara native (kasus `XA:SI03`, §6) → oracle teks B CONFIRMED.

### 3B. Tooling / protokol
**F1-04 (B: R01) — P2 — Runner skenario auditor:** id kasus ganda menimpa hasil sebelumnya (`scripts/cp6_au_r1_probe.py:346-348`: `report['cases'][key]=row`), status di luar kosakata jatuh ke PASS di tingkat grup (`:356-357`: `'INCOMPLETE' if bad else 'COUNTEREXAMPLE' if … else 'PASS'`), commit ke skema `public` lewat koneksi kedua tidak terdeteksi, advisory lock sesi lolos rollback; hanya FAIL/INCOMPLETE membuat job merah. Terbukti native A (run 36039753521: `RT:DUP_ID` COUNTEREXAMPLE tersembunyi di hitungan akhir; `RT:STATUS_VOCAB_OK` diterima) dan repro AST B. `planned_case_ids` di log tetap mengungkap duplikat → cara baca: validasi id unik + kosakata status sebelum memakai agregat.

**F1-18 (B: O01) — P2 — Job install T3 hijau tidak bergantung pada restore drill, `primary_unchanged`, atau advisor.** `scripts/cp6_t3_package_run.py:134` `status='ALL_STAGES_INSTALLED' if len(installed)==len(stages)`; `:135` drill disimpan terpisah; `:148` job hanya meng-assert status ∈ {ALL_STAGES_INSTALLED, BROWSER_PASS}; `primary_unchanged` dicatat di `finally` tanpa assert. Komentar di kode ("a green job can be cited without reading the log") menyesatkan. Pada rerun A nilai-nilainya benar (`RESTORED_SAME_MEANING`, `primary_unchanged true`), jadi ini cacat alat, bukan bukti kegagalan. CONFIRMED sumber (A).

**F1-03 — P2** harness T2 `CP6_T2_SEED=QUIETED` + `CP6_T2_FIXTURE=PAYROLL_APPROVED` atas "arahan owner 24 Sep" (handoff §22:936) di luar kontrak; hasil readiness-dependent bersyarat (M:4322-4324).

**F1-07 — P3** toleransi restore drill "dijelaskan" = penilaian writer (data & engine identik; hanya pg_cron + katalog reparse).

**F1-08 / F1-10 — INFO** sys.path baseline mendahului kandidat untuk modul helper; tanpa dampak bukti.

## 4. Klasifikasi kasus T2 beku/HOLD (kedua audit sependapat; tidak ada relabel)
| Bucket | Jumlah | Kelas | Dasar |
|---|---|---|---|
| 12 kalender HOLD (beku COUNTEREXAMPLE `material_event_date`; disetujui 12/12 MATCH) | 12 | DECISION_EXISTS_EVIDENCE_MISSING | ERP-DEC01 ada; bukti mengikuti aturan hari potong (hanya di handoff); M:1406 tetap HOLD |
| 8 AS `DATE:False:*:True:*` (beku COUNTEREXAMPLE; disetujui 8/8 MATCH) | 8 | DECISION_MISSING | Aturan "HPP PO ikut hari barang/jual" tidak di kontrak; perilaku direproduksi A dengan oracle sendiri (date_family) |
| `ADJUSTMENT_DATE:False` (INCOMPLETE; disetujui MATCH) | 1 | DECISION_MISSING | M:4324 INCOMPLETE tetap; B: "butuh pembuktian semua pembaca dan nilai" |
| AO `INVOICE:*:False` (terbuka) | 2 | DECISION_MISSING | — |
| AO `INVOICE:*:True` (tertutup) | 2 | DECISION_EXISTS_EVIDENCE_MISSING | M:1061 |
| Sisanya (BUSINESS 179+39, IMPORTS 31, VALUES 65, NEW_CASES 25, AR 174, AT/AU 31 + race 10) | — | COVERED_BY_OWNER_DECISION+PROVEN | identik per id (`T2_IDENTITY` moved [] grup lama); caveat F1-03 |

## 5. Rekonsiliasi klaim
### 5A. Klaim writer (handoff §18–20, §23–27) — label Audit A (Audit B sependapat kecuali dicatat)
| Klaim writer | Label |
|---|---|
| T2 identik per kasus; 12 HOLD identik; DISPOSITION_REQUIRED | CONFIRMED (A run 36037873682; B attempt 2 job 107772639059) |
| Oracle-disetujui AS 8/8, kalender 12/12, AO 4/4, ADJUSTMENT_DATE MATCH | CONFIRMED sebagai reproduksi harness (A log baris 2196/2199; B sama); penerimaan = UNVERIFIED_OWNER_DECISION |
| T3 hijau, 24 file, RESTORED_SAME_MEANING (318 tabel/1.647 baris), advisor 127, browser 10/10 | CONFIRMED (A attempt 1, B attempt 2) kecuali browser (REUSED_EVIDENCE) |
| CodeQL 0 hasil 4 bahasa | CONFIRMED 4 bahasa (A run 36037878419); B hanya JS/TS |
| A04-R2 454/454 | CONFIRMED (A lokal) |
| AW P-01..P-04, registri 108, S06 atomik | CONFIRMED sebagian (S06/B04 native A); registri 108 & race dua sesi UNVERIFIED |
| AX perilaku | CONFIRMED (A run 36043204365); kebijakan UNVERIFIED_OWNER_DECISION |
| AZ menghilangkan WIP/persediaan negatif (bentuk dasar) | CONFIRMED (A before/after) |
| AB-01 diperbaiki 46ad845 | REUSED_EVIDENCE (run GPT 36034620907 4/4 PASS head 9add57e); B: UNVERIFIED |
| AV rev2 perilaku | UNVERIFIED (kedua audit); instalasi CONFIRMED |
| G-01 hosted selaras | UNVERIFIED (hosted di luar batas) |
| Rollback NOT_TESTED (§23.9 N2) | CONFIRMED — F1-05 |
| Tombol "Run workflow" di UI (§27.4) | B: REFUTED untuk workflow non-main (dispatch hanya lewat API); A memakai API dispatch — berjalan |
| "Tidak ada keputusan owner yang tertunda" (§26) | REFUTED sebagian: F1-12, P-03, keputusan 24 Sep belum di kontrak, CR aksesori/laundry, H01 |
| Penerimaan independen rev7.4/rev2.1/AB-01 RERUN_REQUIRED (§27.6) | Skenario A = jawaban parsial (bentuk dasar, periode tertutup, 3 jalur GPT); cabang rev6–7.4 lain UNVERIFIED |

### 5B. Klaim Audit B — verifikasi oleh Audit A
| ID B | Klaim | Verifikasi A | Label |
|---|---|---|---|
| F01 | Waktu bisnis 3 halaman ikut zona perangkat (P1) | Sumber + probe Node 4 zona (§3A F1-14) | **CONFIRMED** |
| U01 | Selector BS LIMIT 100 tanpa paging (P2) | Sumber 19/19b/UI (§3A F1-15) | **CONFIRMED (sumber)**; native NOT_RUN |
| U02 | Penyelesaian ulang WIP sebelum pembalikan (P1) | Sumber + **native** `XA:U02` | **CONFIRMED (native)** |
| U03 | Pembulatan 1 unit habis dikonsumsi (P2) | Sumber + **native** `XA:U03_*` | naik **CONFIRMED (native)**; turun **CONFIRMED (native)** |
| R01 | Id ganda menimpa; status tak dikenal → PASS | Native A rt_probe_1 + sumber | **CONFIRMED** |
| R02 | Rollback belum terkualifikasi; digest AC rilis tidak diterima guard | Artefak: sha256 berkas rilis `871fb32b…` vs guard `7b5690a2…/7a3613d8…`; manifest NOT_TESTED | **CONFIRMED** |
| H01 | Produk opsional WIP tidak diikat | Sumber `cp6_az_t1_family.sql:855-862` konsisten | **UNVERIFIED** (perlu keputusan kontrak + native) |
| H02 | DRAFT native ter-prepare menyisakan sumber/kontrol lama | tidak diuji | **UNVERIFIED** |
| O01 | Job T3 hijau tidak memuat drill/primary/advisor | Sumber `cp6_t3_package_run.py:134-148` | **CONFIRMED** (cacat alat; nilai pada rerun A benar) |
| SI03 (oracle teks) | Pesan penolakan `client_request_id was already used with a different payload` | native `XA:SI03`: PASS: replay UUID sama+payload beda DITOLAK; pesan produk: `client_request_id was already used with a different payload` (literal tidak ditemukan grep di SQL, tetapi dipancarkan produk) | **CONFIRMED** (native) |
| T2/T3/CodeQL rerun attempt 2 | konsisten dengan A | run yang sama, attempt berbeda, head 9add57e | **CONFIRMED** |
| Advisor 54 INFO = RLS aktif + REVOKE ALL | tidak diulang A | — | UNVERIFIED (klaim B) |

## 6. Bukti native tambahan Audit A untuk verifikasi silang (run 36048357523, job 107797410652, `xaudit_1.py`)
Ringkasan akhir run: {"status": "RUN_COMPLETE", "auditor_cases": {"status": "COUNTEREXAMPLE", "counts": {"COUNTEREXAMPLE": 3, "PASS": 1}}, "primary_unchanged": true, "error": null}
- `XA:U02_WIP_RECOMPLETION_DATED_BEFORE_REVERSAL`: CONFIRMED (native)
- `XA:U03_ROUNDING_UP_10.005_TO_10.014`: CONFIRMED (native)
- `XA:U03_ROUNDING_DOWN_10.014_TO_10.005`: CONFIRMED (native)
- `XA:SI03_IDEMPOTENT_REPLAY_DIFFERENT_PAYLOAD`: PASS: replay UUID sama+payload beda DITOLAK; pesan produk: `client_request_id was already used with a different payload` — detail: {"status": "PASS", "checks": {"same_payload_replays_identically": true, "different_payload_refused": true}, "first": "{'action': 'CREATE', 'status': 'DRAFT', 'batch_id': '021ac066-91a6-4fa8-a378-37b234d28970', 'revision': '94b875aaaa89ba638e93630b7ae03ed21e3fe3a255d005947df20b5e144aa174', 'error_rows': None, 'request", "replay": "{'action': 'CREATE', 'status': 'DRAFT', 'batch_id': '021ac066-91a6-4fa8-a378-37b234d28970', 'revision': '94b875aaaa89ba638e93630b7ae03ed21e3fe3a255d005947df20b5e144aa174', 'error_rows': None, 'request", "different_payload_result": null, "refusal": {"sqlstate": "P0001", "message": "client_request_id was already used with a different payload"}}
JSON lengkap: `audit/runs/auditor_xaudit1_36048357523.json`.

## 7. Yang TIDAK diperiksa (gabungan; batas klaim laporan ini)
- Jalur HTTP/JWT/browser nyata (browser→HTTP→RPC) untuk facade CP6; browser pada tiga zona waktu (F1-14 hanya probe Node + sumber).
- Concurrency/deadlock AQ dan race dua sesi (shared capacity/draft/finalize/close) dengan oracle auditor.
- IDENT/AV perilaku; rollback AV native; rollback paket T3 (NOT_TESTED).
- Transport CSV browser→RPC dan cakupan ALL impor end-to-end; G-01 hosted.
- Cabang AY rev6–7.4 / AZ rev2.x di luar bentuk dasar (retur, konversi/relabel, void, batch lintas hari, kantong per pool, kontraktor, PO tanpa state, invoice multi-penerimaan) kecuali 3 jalur REUSED_EVIDENCE.
- Guard lintas batch untuk jenis saldo pihak dan roll FABRIC pada jalur impor; fixture 101 sumber laundry (F1-15); H01/H02.
- Matriks historis writer (GATE-15); gerbang lama Full-Schema/Final Boundary (GATE-03).
- Verifikasi adversarial oleh agen terpisah atas temuan P1 belum berjalan (batas sesi akun); setiap P1 didukung ≥2 run native, atau sumber + artefak deterministik.

## 8. Daftar tindakan untuk WRITER (urut prioritas; tiap butir menyebut bukti yang diharapkan)
1. **F1-14 waktu bisnis (P1).** Ganti `new Date(v).toISOString()` di `ConnectedCuttingPage.tsx:272`, `ConnectedPickupPage.tsx:200`, `ConnectedBsResolutionPage.tsx:40` (dan `nowInput` :36-39) dengan `cp6WibPhysicalTimeToIso`/turunannya; tolak nilai tidak valid (null) alih-alih melempar. Bukti: tes unit matriks TZ (Asia/Jakarta, Asia/Makassar, UTC, Pacific/Kiritimati) yang gagal di kode lama dan lulus di kode baru; DOM test tiap halaman; probe `audit/tools/tzprobe.mjs` menghasilkan `equal:true` di keempat zona.
2. **F1-12 tumpang tindih impor→impor (P1).** Tambahkan identitas dokumen/item lintas batch pada FINALIZE impor (dan `erp.post_opening_balance` untuk header impor vs impor) untuk SEMUA jenis saldo (MATERIAL non-roll, roll, FG, BS, WIP, pihak, kas) — penolakan persis + tidak ada perubahan ledger. Bukti: rerun `audit/scenarios/open_1.py` + `open_2.py` pada head baru (semua kasus PASS dengan pesan penolakan tercatat), plus kasus positif (item berbeda tetap boleh).
3. **F1-05 rollback paket rilis (P1).** Sediakan rollback terikat sumber untuk 24 berkas rilis (termasuk varian AC rilis: guard digest harus mengenal statement ledger yang benar-benar dipasang applier T3), jalankan di job T3: pasang → pulihkan (pre-use) → pasang ulang → penolakan pasca-pakai; `MANIFEST.json.rollbacks` = TESTED dengan run/job ID. Jangan melonggarkan guard.
4. **F1-16 WIP saldo awal (bila CONFIRMED di §6).** COMPLETE harus menolak tanggal < tanggal pembalikan output sebelumnya untuk sumber yang sama (atau model sisa per tanggal); bukti native: kasus `XA:U02` PASS dengan penolakan persis + kasus positif (tanggal ≥ pembalikan).
5. **F1-17 pembulatan (bila CONFIRMED di §6).** Selisih pembulatan koreksi harga harus mengikuti nilai yang benar-benar diposting per unit (bukan `round(qty×Δ)` terpisah), sehingga bahan yang habis dikonsumsi bernilai 0; bukti: `XA:U03_*` PASS kedua arah + jalur invoice.
6. **F1-15 selector (P2).** Lookups sumber laundry/penerimaan/klaim selesai: saring claimable di SQL sebelum LIMIT dan sediakan pencarian/paging; bukti: fixture 101 sumber (sumber tertua tetap terpilih).
7. **F1-04 / F1-18 alat (P2).** Runner: tolak id kasus ganda, batasi kosakata status, deteksi commit skema `public`, cetak `planned_case_ids` vs hasil; job T3: assert `backup_restore_drill`, `primary_unchanged`, dan status advisor (atau hapus komentar "green job can be cited without reading the log"). Bukti: probe `rt_probe_1.py`/`rt_probe_2.py` menghasilkan INCOMPLETE untuk kasus yang sengaja bocor.
8. **F1-01/F1-02/GATE-16/P-03/AX (keputusan owner).** Kirim satu daftar keputusan ke owner untuk ditulis ke kontrak: amandemen ERP-DEC01 (prinsip WIP, 8 AS, kalender, AO, ADJUSTMENT_DATE), satu status ERP-DEC03/ALL, cakupan CR aksesori/laundry, P-03 (tahan semua tanggal vs per tanggal), kebijakan AX, invoice sebelum terima (§26.2), H01 (pengikatan produk opsional). Sampai tertulis: label UNVERIFIED_OWNER_DECISION tetap, kasus terdampak tidak dilabel ulang.
9. **Bukti yang masih kosong (GATE-04/08/09).** Jalur HTTP/JWT/browser nyata untuk 10 facade CP6 (anon/unmapped/nonaktif/view-only), perilaku AV, cabang AY/AZ tanpa fixture native (§7), race dua sesi. Label setiap run dengan head_sha dan attempt; simpan log per job.

## 9. Lampiran
### 9A. Run Audit A (semua head_sha 9add57e; attempt 1 kecuali dicatat)
| Workflow | Run | Job(s) | Isi |
|---|---|---|---|
| cp6-candidate-codeql.yml | 36037878419 | 107762403880 js-ts, 107762404091 python, 107762404177 actions, 107762404232 c-cpp | 4× `result_count 0` (B: attempt 2 job 107772676223 JS/TS) |
| cp6-t2-regression.yml | 36037873682 | 107762384861 ar, 107762384959 temporal, 107762385235 regression | §4 (B: attempt 2 job 107772639059; run kini attempt 4) |
| cp6-t3-release-package.yml | 36037876338 | 107762395202 install, 107762394813 capture, 107762395187 browser | 24/24, verify, restore drill, advisors 127 (B: attempt 2 job 107772603343; run kini attempt 3) |
| cp6-auditor-scenario.yml | 36039753521 | 107768697263 | rt_probe_1 |
| cp6-auditor-scenario.yml | 36040954954 | 107772716244 | rt_probe_2 (job merah by design) |
| cp6-auditor-scenario.yml | 36041422305 / 36041435083 | 107774254372 / 107774296346 | date_family_1 after / before |
| cp6-auditor-scenario.yml | 36042210333 / 36042223829 | 107776876564 / 107776920429 | date_family_2 after / before |
| cp6-auditor-scenario.yml | 36042716805 | 107778594395 | close_access_1 |
| cp6-auditor-scenario.yml | 36043204365 | 107780207435 | fg_acc_1 |
| cp6-auditor-scenario.yml | 36043758572 | 107782073208 | access_2 |
| cp6-auditor-scenario.yml | 36044022037 | 107782968845 | open_1 |
| cp6-auditor-scenario.yml | 36044313409 | 107783945930 | access_3 |
| cp6-auditor-scenario.yml | 36045629594 | 107788356714 | open_2 |
| cp6-auditor-scenario.yml | 36048357523 | 107797410652 | xaudit_1 (verifikasi U02/U03/SI03 Audit B) |
| (REUSED) cp6-auditor-scenario.yml | 36034620907 | 107751512664 | empat skenario GPT |
Per-kasus: `AUDIT_PROGRESS.md` tabel d) dan JSON di `audit/runs/`. Skenario NOT_RUN Audit B (`work/stock_import_scenario.py` ff92e8d9…, `work/money_dates_scenario.py` cfa1157b…) tidak diterima Audit A; U02/U03/SI03 ditulis ulang oleh A dengan oracle sendiri (`xaudit_1.py`).

### 9B. Skenario Audit A (`audit/scenarios/`, sha256 = `audit/scenarios/SHA256SUMS`)
| Berkas | sha256 |
|---|---|
| `access_2.py` | `e1f4093c9c683627af1a46a0f9a18ae0955718c1e6b72bc52a9abfd733acc310` |
| `access_3.py` | `1f1a25bc069d947db0441d64e4db30b9bc1a70e66d6267a6ef54c66be4453afd` |
| `close_access_1.py` | `cafea79d8d73f8979475c7ebe27837ecf65a4181630ba40bbbdc0cb5bd182f5f` |
| `date_family_1.py` | `492908b5dcf3184bacabcb99a878630c1b206e67c5d6f96586f02105f4a537d0` |
| `date_family_2.py` | `44f09ad11948e15cbfc0df20925c10acec055888f6f4b46c6b577eb3f4f4a9a8` |
| `fg_acc_1.py` | `79da4c2e77f5ad3dc0a57d084ad426faf7db5e42f81c4ebf244270539bfa11a7` |
| `open_1.py` | `983a66f58524aeebb8f57826023ada76b2bb5757b80ed61680cca0c3cb125333` |
| `rt_probe_1.py` | `13b3b800900e55d5ae60d67baafffec6aa07216da76bf6b7a95534f42da0c33a` |
| `rt_probe_2.py` | `cd6df40c868afefa9023c84d6c4f284f3b79d4abaa63907d66101b8395d82789` |
| `open_2.py` | `e8b84000396cc6e9ee27cdd49a50ea3d3806386a7b916e7868fc9b974709e9e0` |
| `xaudit_1.py` | `32a872e5ca4bfbae4a49ca05ca746454e2fc8d3c007c0e8bb10609f7b233d4a4` |

### 9C. Berkas
`audit/PHASE1_FINDINGS.md` (kunci fase 1 A), `audit/input/AUDIT_REPORT_CP6_auditor2.md` (laporan B), `audit/out/C1_gates.md`, `audit/out/T2_classification.md`, `audit/out/RT_probe1_findings.md`, `audit/out/RT_probe2_findings.md`, `audit/out/DATE_family_results.md`, `audit/out/phase2_reconciliation.md`, `audit/tools/` (dispatch_scenario.py, parse_saved_log.py, tzprobe.mjs, phase1_derive.js, phase1_verify.js), `audit/runs/` (JSON per run, ledger dispatch, log vitest).

## 10. Addendum (2026-09-24 20:06 UTC): pemeriksaan native lanjutan atas item yang semula 'belum diperiksa'

Run xaudit_2: 36051514868 job 107807966805 (sha skenario 108b3ebc…): ringkasan {"status": "RUN_COMPLETE", "auditor_cases": {"status": "COUNTEREXAMPLE", "counts": {"COUNTEREXAMPLE": 3, "PASS": 2}}, "primary_unchanged": true, "error": null}.
Run xaudit_3: 36052066150 job 107809808216 (sha 3915e006…; INCOMPLETE by design karena koneksi kedua COMMIT ke clone): ringkasan {"status": "INCOMPLETE", "auditor_cases": {"status": "INCOMPLETE", "counts": {"INCOMPLETE": 3}}, "primary_unchanged": true, "error": null}.

| Item | Kasus | Hasil |
|---|---|---|
| F1-17 jalur invoice naik | `XA2:F1-17_INVOICE_PATH_UP_10.005_TO_10.014` | **COUNTEREXAMPLE** — checks={"invoice_posted": true, "raw_qty_zero": true, "inventory_value_zero_at_end": false, "wip_equals_rounded_invoiced_value": false, "no_negative_daily_inventory": false}; {"delta_end": {"MATERIAL_INVENTORY": "-0.01", "WIP": "10.02", "FG_INVENTORY": "0", "COGS": "0"}, "delta_after_cut": {"MATERIAL_INVENTORY": "0.00", "WIP": "10.01", "FG_INVENTORY": "0", "COGS": "0"}, "expected_wip": "10.01", "raw_qty": "0.000000", "refusal": null} |
| F1-17 jalur invoice turun | `XA2:F1-17_INVOICE_PATH_DOWN_10.014_TO_10.005` | **COUNTEREXAMPLE** — checks={"invoice_posted": true, "raw_qty_zero": true, "inventory_value_zero_at_end": false, "wip_equals_rounded_invoiced_value": true, "no_negative_daily_inventory": true}; {"delta_end": {"MATERIAL_INVENTORY": "0.01", "WIP": "10.00", "FG_INVENTORY": "0", "COGS": "0"}, "delta_after_cut": {"MATERIAL_INVENTORY": "0.00", "WIP": "10.01", "FG_INVENTORY": "0", "COGS": "0"}, "expected_wip": "10.00", "raw_qty": "0.000000", "refusal": null} |
| F1-15 selector 101 sumber | `XA2:F1-15_SELECTOR_101_LAUNDRY_SOURCES` | **COUNTEREXAMPLE** — checks={"old_claimable_in_db": true, "old_selectable": false, "lookups_capped_at_100": true}; {"lookups_count": 100, "claimable_in_lookups": 100, "old_qty": "10", "newest_in_lookups": ["XA2-NEW-099", "XA2-NEW-098"], "oldest_in_lookups": ["XA2-NEW-001", "XA2-NEW-000"]} |
| AV identitas: edit efektif SEBELUM fakta stok baru | `XA2:AV_IDENTITY_EDIT_BEFORE_NEW_STOCK_FACT` | **PASS** — checks={"refused": true}; {"latest_new_stock_fact": "2026-09-25 02:41:05.091454+07:00", "effective_from": "2026-09-25 01:41:05.091454+07:00", "refusal": {"sqlstate": "P0001", "message": "Tanggal efektif SKU akan memotong histori produksi yang sudah tercatat (fakta fisik stok baru terakhir 2026-09-25 02:41:05.091454+07). Pilih tanggal efektif sesudahnya."}, "result": null, "versions": ["1", "2026-01-01 07:00:00+07", "2026-01-01 07:00:00+07"], "old_row": ["None", "CP6-E-AUR1-e61e2472d967"]} |
| AV identitas: edit efektif SESUDAH fakta | `XA2:AV_IDENTITY_EDIT_AFTER_NEW_STOCK_FACT` | **PASS** — checks={"accepted": true, "old_version_closed": true, "old_sku_unchanged": true}; {"latest_new_stock_fact": "2026-09-25 02:41:05.530732+07:00", "effective_from": "2026-09-25 03:41:05.530732+07:00", "refusal": null, "result": "3a1b57c1-19a2-4adb-bd02-aead19ed8817", "versions": ["2", "2026-01-01 07:00:00+07", "2026-09-25 03:41:05.530732+07"], "old_row": ["2026-09-25 03:41:05.530732+07", "CP6-E-AUR1-d4cd1b772834"]} |
| Race dua sesi: batch impor kedua item sama | `XA3:RACE_TWO_SESSIONS_SECOND_IMPORT_BATCH_SAME_ITEM` | **INCOMPLETE** — checks=null; {} ; error=OWNER or ADMIN access required
CONTEXT:  PL/pgSQL function erp.require_owner_admin() line 12 at RAISE
SQL statement "SELECT erp.require_owner_admin()"
PL/pgSQL function erp.save_initial_import_action_v1(text,jsonb,uuid) line 9 at PERFORM
SQL function "erp_save_initial_import_action_v1" statement 1 |
| Race dua sesi: tutup buku tanggal sama | `XA3:RACE_TWO_SESSIONS_CLOSE_SAME_DATE` | **INCOMPLETE** — checks=null; {} ; error=permission denied for schema erp
LINE 1: select current_user,session_user,erp.current_app_role()
                                         ^ |
| Race dua sesi: COMPLETE WIP expected_remaining sama | `XA3:RACE_TWO_SESSIONS_WIP_COMPLETE_SAME_REMAINING` | **INCOMPLETE** — checks=null; {} ; error=OWNER or ADMIN access required
CONTEXT:  PL/pgSQL function erp.require_owner_admin() line 12 at RAISE
SQL statement "SELECT erp.require_owner_admin()"
PL/pgSQL function erp.save_initial_import_action_v1(text,jsonb,uuid) line 9 at PERFORM
SQL function "erp_save_initial_import_action_v1" statement 1 |

**Race dua sesi (xaudit_3):** tidak dapat dijalankan di runtime skenario auditor: identitas operator, klaim JWT, dan grant `usage on schema erp to authenticated` yang dipakai helper writer bersifat transaksi-lokal pada koneksi utama runtime (rev2: koneksi samping admin mendapat `OWNER or ADMIN access required` / `permission denied for schema erp`). Race butuh dukungan runtime dari writer (fixture ter-commit atau mode dua sesi) — dicatat sebagai batas alat (perluasan F1-04). Bukti concurrency yang ada tetap milik writer (T2 AR_CONCURRENCY 28, AT/AU race 10).

**Tidak dapat dijalankan dari sesi ini:** (a) jalur HTTP/JWT nyata — skenario `xaudit_4.py` (sha 2cde1c4f…; kontainer PostgREST ke clone + JWT HS256 dari secret stack, hanya penolakan dan pembacaan) ditulis tetapi dispatch-nya DIBLOK oleh classifier izin sesi ("Credential Materialization"); owner/writer dapat men-dispatch berkas itu sendiri lewat API dengan `phase=after`; (b) rollback paket T3 native — tidak ada berkas rollback AW..AZ dan workflow T3 tidak punya mode rollback (butuh perubahan writer); (c) verifikasi adversarial oleh agen terpisah — batas sesi akun sampai 22:20 UTC (trigger 22:26 UTC terpasang).
JSON: `audit/runs/auditor_xaudit2_36051514868.json`, `audit/runs/auditor_xaudit3_36052066150.json`.

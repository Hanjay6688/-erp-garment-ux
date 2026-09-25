# Fable — hasil putaran 9 (head alat `d1bc8adff3ba1a2a7001ef39e4819d0c3813d00b`)

Tanggal: 2026-09-25. Label: INDEPENDENT_NATIVE_RERUN / INDEPENDENT_SOURCE_REVIEW / REUSED_WRITER_EVIDENCE / UNVERIFIED_OWNER_DECISION.
Oracle hanya dari M/P/BR + addendum C0 bagian 1–8 (disahkan owner ke auditor). Lampiran C6 rev3 bagian 0 **belum** disahkan owner ke auditor.
Semua run dispatch oleh Fable lewat API pada ref `claude/new-session-deapao` (workflow yang diizinkan saja); run_identity tiap log memuat `tool_head d1bc8ad`.
Putaran ini dikerjakan **independen dulu** (tanpa membaca hasil GPT putaran 9); audit silang GPT menyusul di dokumen terpisah.

## 0. Identitas

| Hal | Nilai |
|---|---|
| Head alat (handoff writer §29) | `d1bc8adff3ba1a2a7001ef39e4819d0c3813d00b` |
| `run_identity.product_ref` yang dicetak runtime | `61d88ee5224b2fb2da2af6f4df214fbaacf9f161` (paths: supabase/migrations, supabase/dev, supabase/release, supabase/rollbacks, src) |
| Produk per writer | BA dev `b6d81f9`, paket T3 `1dcf21b`, rollback `61d88ee`, frontend `21acae1` |
| Diff produk a095a9d..d1bc8ad | `supabase/dev/…20ba_cp6_audit_closure.sql` +1528, release copy +1530, MANIFEST/ROLLBACKS; `src/lib/requestEnvelope.ts` (+88, baru), `clientError.ts` (+27), `components/Cp6Kpi.tsx` (+10), `PatternPage.tsx`, `AccessControlPage.tsx`, `ConnectedLaundryPage.tsx`, `ConnectedQcFinalPage.tsx`; `scripts/cp6_auditor_modes.py` (+89), `cp6_ba_probe.py` (+159), `cp6_c0_oracles_auditor.py` (+277), `cp6_t2_regression.py` (+63), `cp6_cutover_data_checks.py` (+69) |
| Workflow `cp6-auditor-scenario.yml` | identik antara 9dd7bc2 dan d1bc8ad (diff kosong) |

## 1. Rerun skenario auditor pada d1bc8ad (phase=after) — INDEPENDENT_NATIVE_RERUN

| Skenario (sha) | Run / job | Hasil d1bc8ad | Hasil a095a9d (putaran 8) | Catatan |
|---|---|---|---|---|
| `xaudit_1_rev2.py` dad4331b | 36121849651 / 108028944640 | **4/4 PASS** | 4/4 PASS | U02, U03 UP/DOWN, SI03 |
| `xaudit_2_rev2.py` 06e6149c | 36121860362 / 108028976063 | **5/5 PASS** | 5/5 PASS | F1-17 invoice path, selector 101, AV identity |
| `xaudit_7.py` e21d9d0c | 36121871053 / 108029010163 | **12/12 PASS** | 12/12 PASS | kontrol positif & bypass A1/A3/A10/A9/A6 |
| `open_1.py` 983a66f5 | 36121881199 / 108029043535 | **13/13 PASS** | 13/13 PASS | overlap legacy 10 jenis, import twice, control mismatch, FG reverse |
| `c0_round8/gpt_c0_oracles.py` 7c2c19b6 (GPT, dipakai ulang sebagai oracle C0 yang konvergen) | 36121837956 / 108028906278 | **24 PASS + 1 INCOMPLETE** | 24 PASS + 1 INCOMPLETE | INCOMPLETE = `G8C0:AS:ADJUSTMENT_DATE:False` `permission denied for schema erp` — batas transport skenario rev1 (grant dicabut helper), sama persis dengan putaran 8; retry dengan grant dipulihkan dijalankan lewat workflow multi-file (§1b) |
| `combined_native15_reconstructed.py` cec2ad52 | 36121891481 / 108029077672 | 8 PASS, 6 INCOMPLETE, 1 COUNTEREXAMPLE | identik | Status **identik** per kasus dengan putaran 8: SI-01/SI-02 INCOMPLETE karena fixture pra-BA kini ditolak BA (`BA_WIP_OUTPUT_PRODUCT_BOUND`, `BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING`; perilaku yang benar, skenario lama tidak tahu kode BA); BCR1 DATED_CAPACITY ×3 INCOMPLETE karena skenario lama menuntut oracle kode dan kini ditolak `BA_ADVANCE_DATED_CAPACITY` (perilaku benar, A9); SEL_01 INCOMPLETE `column p.id does not exist` (cacat skenario rekonstruksi, bukan produk — ditutup oleh xaudit_2 selector 101 dan writer A5); SI-04 COUNTEREXAMPLE beku (CP6-19; rev3 `xaudit_6` PASS 2/2 di putaran 8 menutup pertanyaan produknya) |
| `round8/gpt_tool_modes.py` 0cad8382 (W7) | 36121901467 / 108029109648 | cases `G8_TOOL:CONTROL` PASS; **races & HTTP: grup DITOLAK `AUDITOR_DUPLICATE_CASE_IDS` (`G8_TOOL:HTTP_DUP`) sebelum operasi apa pun**, `database_remaining 0`, auth restored | (putaran 8: ID ganda tidak ditolak) | **W7 CONFIRMED** pada `scripts/cp6_auditor_modes.py:125–149` (`strict_rows`) — run merah by design |
| `xaudit_8.py` rev1 079e1c5b (W8 multi-receipt + LAU-T14, ditulis auditor) | 36122483797 / 108030977248 | 10/10 INCOMPLETE — **cacat skenario auditor** (`created_at` → `system_created_at`; `wash_process_id` ada di header sebagai `target_wash_process_id`) | — | rev2 d7e82997 dijalankan: run 36123155393 (§1a) |

### 1a. xaudit_8 rev2 dan xaudit_9 (menyusul; hasil ditambahkan di §9)

- `xaudit_8.py` rev2 sha `d7e82997…`: W8 dua penerimaan (DIRECT/INVOICE × UP/DOWN), **tiga penerimaan** (INVOICE UP, DIRECT DOWN), LAU-T14 (tarif naik, turun, kontrol, **celah versi** pada waktu kirim harus ditolak atomik). Oracle: M:1022/1059–1065/3818/3820 + M:485 (setiap dokumen dibulatkan sendiri; bahan habis = qty 0 nilai 0; WIP = jumlah nilai dokumen), M:4474 LAU-DEC03.
- `xaudit_9.py` rev1 sha `0b1a4bf2…`: W9 C0 D01 3.4 — koreksi di periode tertutup (tanggal ekonomi E, dibukukan hari ini) → `changed_since_filing=true` untuk d; kontrol tanpa perubahan → false; **adversarial**: koreksi bertanggal d+1 (setelah tanggal filing) tidak boleh menandai d (D01 5).

### 1b. Workflow multi-file `.github/workflows/fable-cp6-round9.yml` (cabang audit, pinned auditor `d1bc8ad`) — run 36123210828

Salinan `gpt-cp6-round8.yml` dengan ref auditor diganti ke d1bc8ad dan matriks tiga job: `unknown_rev6` (W13/W11, file GPT rev6 beku hash MANIFEST_rev6), `recovery` (W10, `recovery_round8`), `c0_adjustment_http` (retry ADJUSTMENT_DATE dengan grant dipulihkan + HTTP Auth nyata + browser WIB). Hash file diverifikasi terhadap manifest GPT (dibekukan pada 9dd7bc2); tool head yang dicek adalah d1bc8ad. Hasil di §9.

## 2. Alat: T2 / T3 pada d1bc8ad

| Workflow | Run | Hasil |
|---|---|---|
| CP6 T2 Combined Regression | 36121911881 (job regression 108029145846, ar 108029145723, at/au 108029145454) | `T2_IDENTITY` holds 12/12 identik, `DISPOSITION_REQUIRED` (by design). BUSINESS 179 PASS + 39 CONTROL_PASS + 12 DATE_POLICY_REVIEW_REQUIRED; IMPORTS 31/31; VALUES 65/65; NEW_CASES 25 PASS + 8 COUNTEREXAMPLE + 1 INCOMPLETE (beku, sama dengan referensi); T2_APPROVED_ORACLE MATCH 8; T2_CALENDAR_POLICY COUNTEREXAMPLE 12 (beku); AO_TRIAL 8 PASS + 4 INCOMPLETE (sama); APPROVED_ORACLE_B 5 PASS; **`T2_C0_ORACLE` 25/25 PASS (grup baru, W2) — CONFIRMED dari log**; `auditor_head d1bc8ad`, `production_go=false` |
| CP6 T3 Release Package | 36121924229 (3 job: 108029182401, 108029182558, 108029182713) | **success** (gate, pins, AU browser) — T3_PREP |
| CP6 T3 Rollback | 36121935168 (job 108029215854) | **failure infrastruktur** di "Start disposable database": `failed to bind host port 0.0.0.0:54324 … address already in use` (inbucket), sebelum tes apa pun berjalan; artefak kosong. Dijalankan ulang sekali: run 36123219619 (§9) |

## 3. Review sumber putaran 9 (INDEPENDENT_SOURCE_REVIEW, diff a095a9d..d1bc8ad)

| Item | Sumber | Temuan Fable |
|---|---|---|
| W7 grup ketat race/HTTP | `scripts/cp6_auditor_modes.py:125–149` `strict_rows` (ID ganda → tolak grup; non-dict / status di luar kosakata → INCOMPLETE dengan nilai asli; sesi tertinggal → INCOMPLETE; planned/final/missing dicetak); HTTP mengecualikan pool `authenticator` (`:302`) | CONFIRMED natively (§1, gpt_tool_modes) |
| W8 sen multi-penerimaan | `supabase/dev/cp6_ba_t1_family.sql:689–727` di `erp.sync_material_cost_revaluation`: pada tiap gerakan pemakaian, selisih (nilai dokumen dibulatkan per dokumen, dari `input_unit_cost`) − (perubahan rata-rata bergerak) untuk penerimaan sejak pemakaian sebelumnya ditambahkan ke target; sen tingkat dokumen multi-bahan ke material id terkecil | Logika masuk akal untuk 1 bahan/dokumen; kasus dokumen multi-bahan **belum diuji** siapa pun (dicatat sebagai sisa). Uji native: xaudit_8 rev2 (§9) |
| W9 `changed_since_filing` | `cp6_ba_t1_family.sql:1053–1060` di `get_owner_financial_snapshot_v2`: filing ada ∧ (status ≠ READY ∨ ada jurnal POSTED/REVERSED dengan `economic_date ≤ as_of` dan `transaction_date > closed_through` yang tidak terdaftar di `readiness.booked_after_filed_period` filing) | Sesuai C0 D01 3.4/5 secara teks. Sisa: jurnal yang dibukukan setelah filing dengan `economic_date ≤ as_of` tetapi `transaction_date ≤ closed_through` tidak mungkin (periode tertutup) — OK. Uji native: xaudit_9 (§9) |
| W10 identitas permintaan Pola/Hak Akses | `src/lib/requestEnvelope.ts` (envelope {id, rpc, args, fingerprint} disimpan **sebelum** kirim; `sendOnce` memakai ulang UUID untuk perubahan yang sama setelah hasil UNKNOWN; perubahan lain BLOCKED; REFUSED menghapus envelope; `isUnansweredFailure` menentukan UNKNOWN). Dipakai `PatternPage.tsx:110,134` (`erp_save_pattern_v1`, `erp_deactivate_pattern_v1`) dan `AccessControlPage.tsx:221,245,261,276` (`erp_save_role_v1`, `erp_save_app_user_v3` ×2, `erp_deactivate_role_v1`); tombol "Kirim ulang perubahan tertunda" | Sesuai M:1679/M:3819 secara sumber. `randomUUID` di `AccessControlPage.tsx:191` hanya untuk kode role duplikat, bukan `p_client_request_id`. Bukti browser: job `recovery` (§9). Catatan: fingerprint = `JSON.stringify({rpc,args})` — bergantung urutan kunci per call site (konsisten karena literal), diterima |
| W11 pesan asli | `src/lib/clientError.ts:71–77` (kode `REJECTED` dengan pesan asli bila bukan `isUnansweredFailure`), `isUnansweredFailure` (`:85–96`: TypeError, AbortError, status 0/502/503/504, pesan kosong, kata jaringan tanpa kode) | Sesuai. Efek samping yang diterima: pesan kosong = UNKNOWN (sisi aman). Bukti browser: job `unknown_rev6` (§9) |
| W13 KPI unknown | `src/components/Cp6Kpi.tsx` ("—" + "belum diketahui · data belum termuat" saat `value` null/undefined; 0 server tetap 0); `ConnectedLaundryPage.tsx:414–419,441` dan `ConnectedQcFinalPage.tsx:316–321,342` memberi `kpis` = null sebelum workspace terbaca | Sesuai M:3825 secara sumber. Bukti browser: job `unknown_rev6` (§9) |
| LAU-T14 | `cp6_ba_t1_family.sql:1646–1660` `save_laundry_qc_action_v1` POST_RECEIPT: tarif = versi yang berlaku pada `v_delivery.physical_at` (waktu kirim), tepat satu; lock `LRATE:` | Sesuai M:4474 LAU-DEC03. Celah versi pada waktu kirim → exception "found 0" (uji native GAP di xaudit_8 rev2) |
| W4 INCOMPLETE terstruktur, W12/W6 drill | `scripts/cp6_auditor_runner.py`, `scripts/cp6_cutover_data_checks.py` (+69) | Hanya dibaca diff-stat; drill tidak dijalankan Fable (butuh salinan hosted — di luar batas) |

## 4. Klaim CI writer §29.5 — REUSED_WRITER_EVIDENCE (status via API, log tidak dibaca)

| Run | Head | Workflow | Status |
|---|---|---|---|
| 36112965907 | f990c74 | CP6 BA T1 Family Probe | success |
| 36113586943 | 1dcf21b | CP6 T2 Combined Regression | success |
| 36113911869 | 61d88ee | CP6 T3 Release Package | success |
| 36113267241 | 1dcf21b | CP6 T3 Rollback | success |
| 36113867725 | 61d88ee | CP6 T3 Rollback | success |
| 36113589299 | 1dcf21b | CP6 Candidate CodeQL (T3) | success |
| 36109589498 | 21acae1 | CP6 Auditor Scenario (gpt_tool_modes) | failure (by design: grup ditolak) |

Semua run writer berada pada head **sebelum** d1bc8ad; bukti auditor sendiri (§1–§2, §9) adalah yang berlaku.

## 5. Keputusan scope owner (lampiran C6 rev3 bagian 0) — UNVERIFIED_OWNER_DECISION

Kutipan writer: "gw mau semuanya dibikin sekarang dan diuji di cp 6 termasuk all 22 lu harus bikin dan d06. so now what?". Tafsir writer (4 poin): semua CR-TUNDA (ACC-04b, LAU-05b, LAU-06b termasuk ganti SKU hasil BS) dibangun & diuji di CP6; ALL = 22 keadaan §29.6 semuanya punya jalur impor + lanjutan; baris KEBIJAKAN (ACC-DEC01,03–07, ERP-DEC02, LAU-DEC01–06) sebagai pengaturan aplikasi dengan default aman; D06 disahkan setelah revisi.
Status auditor: **belum dicocokkan** — kutipan hanya ada di dokumen writer. Ditanyakan langsung ke owner di sesi ini (lihat §10 setelah jawaban). Catatan kontrak yang perlu owner sadari saat memutuskan:
- M:1697 membolehkan owner menunda CR ke successor; M:1757 mewajibkan fitur baru yang sudah ada di kandidat diuji tuntas. Memasukkan semua CR ke CP6 berarti gate CP6 menunggu 75 kasus C6 + 22 keadaan ALL (estimasi auditor: bukan hitungan hari).
- "Kebijakan sebagai pengaturan aplikasi dengan default aman" bukan keputusan kebijakan: nilai defaultnya tetap harus disahkan owner satu per satu (ACC-DEC03/04/05/06, LAU-DEC01/03/05/06) — oracle pra-kode (§6) menandai ini `PENDING_POLICY_VALUE`.

## 6. Oracle pra-kode (permintaan writer #3) — draf agen, spot-check Fable

| Dokumen | Isi | Ringkasan status |
|---|---|---|
| `out/fable_c6_75_oracles_pre_code.md` (674 baris) | 75 kasus C6 (39 ACC + 36 LAU): baris M + kutipan, fixture angka, hasil per leg (stok/nilai, jurnal, hutang/piutang, HPP, UI/izin, penolakan), larangan, ketergantungan kebijakan | ≈50 ORACLE_READY penuh, ≈16 ORACLE_READY sebagian (invariant siap, fitur CR menahan sisanya), ≈25 memuat bagian NEEDS_OWNER_INPUT/PENDING_POLICY_VALUE; 8 ambiguitas kontrak (mis. OTHER_INCOME D05 ≠ ACC-DEC03; enum status harga LAU-R09 hanya usulan; borongan LAU-T20 tanpa metode alokasi) |
| `out/fable_all22_oracles_pre_code.md` (589 baris) | 22 keadaan ALL (P/S/Y/A/W/C): kutipan kontrak, fixture, ledger setelah impor, setelah lanjutan, setelah inverse, penolakan, status rute §29.6, verdict | ORACLE_READY 8 murni (P01, P02, S01, Y01, A01, A02, W03, C01) + 3 bersyarat kecil (A03, W01, W02); NEEDS_OWNER_INPUT 11 (P03, P04, S02, S03, Y02, W04, W05, W06, C02, C03, C04) — kontrak diam atau melarang solusi teknis termudah tanpa alternatif; 10 celah kontrak dikutip |

Batas: oracle diturunkan dari M + addendum 1–8 saja (bukan dari kode kandidat; lampiran/crosswalk hanya pemetaan ID). Ditulis agen atas instruksi Fable; Fable membaca ringkasan dan dua blok sampel (P01, LAU-T01–T03) — konsisten dengan M:383–388 dan M:4339–4341. Belum ditinjau baris per baris; writer memakainya sebagai target, bukan sebagai bukti.

## 7. Status register setelah putaran 9 (sementara; final di §9)

| Item | Status d1bc8ad |
|---|---|
| W7 (B1 race/HTTP grup ketat) | **CLOSED** — natively (§1) + sumber (§3) |
| W2 (grup oracle C0 di T2) | **CLOSED** — `T2_C0_ORACLE` 25/25 dari log T2 (§2) |
| W8 (sen multi-penerimaan) | menunggu xaudit_8 rev2 (§9) |
| W9 (`changed_since_filing`) | menunggu xaudit_9 (§9) |
| LAU-T14 | menunggu xaudit_8 rev2 (§9) |
| W10 / W13 / W11 (frontend) | sumber sesuai (§3); menunggu job browser (§9) |
| C0 ADJUSTMENT_DATE retry | menunggu job `c0_adjustment_http` (§9) |
| T3 package | success (§2) |
| T3 rollback | rerun 36123219619 (§9) |
| Sisa yang tidak ditutup putaran ini | dokumen multi-bahan W8 (tidak diuji); W12 drill pada hosted (di luar batas); W3/W5/W6 opsional; O2/D06 & scope (§5) menunggu owner |

Vonis: **CP6 HOLD, `audit_complete=false`, `production_go=false`** — tidak berubah; gate CP6 sekarang bergantung pada keputusan scope owner (§5).

## 8. Batas putaran 9

Baca saja; tidak ada push ke `claude/new-session-deapao`; tidak ada SQL ke hosted; tidak ada pesan ke pihak lain. Skenario GPT dipakai ulang hanya sebagai file beku (hash di manifest); hasil GPT putaran 9 sengaja **belum dibaca** (instruksi owner: independen dulu).

## 9. Hasil run susulan (2026-09-25T10:40Z)

| Run / job | Skenario | Hasil | Klasifikasi Fable |
|---|---|---|---|
| 36123155393 / 108033136977 | `xaudit_8.py` rev2 d7e82997 | **W8 dua penerimaan 4/4 PASS** (DIRECT/INVOICE × UP/DOWN: bahan qty 0 nilai 0, WIP 20,02 / 20,00, WIP per PO masing-masing = nilai dokumen dibulatkan). **LAU-T14 4/4 PASS** (tarif naik 7→9 dan turun: actual_rate = tarif saat kirim, actual_cost = qty × tarif kirim, estimasi tidak berubah; kontrol; **GAP**: tanpa versi tarif pada waktu kirim → ditolak atomik, tanpa baris penerimaan). **Tiga penerimaan 2 COUNTEREXAMPLE** di bawah check tambahan auditor `wip_per_po_each_equals_rounded_document` saja: total WIP 30,03 / 30,00 dan bahan 0 **benar**, tetapi per PO 10,02 / 10,00 / 10,01 (UP) dan 9,99 / 10,01 / 10,00 (DOWN) | W8 **CLOSED untuk total, per tanggal, dan bahan habis** (oracle kontrak: M:1022, M:3818/3820, M:6632 "nilai total dan per tanggal"). Sisa per-PO: M:485 secara eksplisit menerima pembagian sen deterministik antar kelompok ("5,63 dan 5,62 … seluruh sen habis terbagi"), jadi ini **NOTED (P3)**, bukan pelanggaran: HPP satu PO bisa selisih 1 sen dari dokumen bahannya sendiri saat ≥3 penerimaan dikoreksi sekaligus. Hasil beku tetap COUNTEREXAMPLE (oracle auditor lebih ketat dari kontrak); tidak dilabel ulang. LAU-T14 **CLOSED** |
| 36123165642 / 108033168261 | `xaudit_9.py` rev1 0b1a4bf2 | **3/3 PASS**: A koreksi di periode tertutup (tanggal ekonomi E, dibukukan setelah d) → `changed_since_filing=true`, nilai d dan baris filing tidak berubah, READY; B kontrol → false; C koreksi bertanggal d+1 → false untuk d (penanda spesifik pada gambaran yang difiling) | W9 **CLOSED** (termasuk adversarial) |
| 36123219619 / 108033340129 | CP6 T3 Rollback (rerun setelah gagal infra) | **success** | T3 rollback **VERIFIED (T3_PREP)** pada d1bc8ad |
| 36123210828 / 108033307472 | multi-file `unknown_rev6` (GPT rev6 beku, QC) | **2/2 PASS** (`QC_HEALTHY_CONTROL`, `QC_INITIAL_READ`) | W13 QC **CLOSED** natively di browser |
| 36123210828 / 108033307686 | multi-file `c0_adjustment_http` (GPT beku) | native `G8C0:AS:ADJUSTMENT_DATE:False:transport_rev2` **PASS** → C0 **25/25** pada d1bc8ad; HTTP Auth nyata 3/3 PASS (`VALID_FACADE_MATRIX`, `REVOKED_OWNER_READ`, `PREPARED_HELPER_REACHABILITY`); browser WIB **8 PASS + 4 INCOMPLETE**: `pickup` di 4 zona `getByLabel('Mandor',{exact:true})` timeout 20 s (cutting dan bs PASS di 4 zona) | C0 dan HTTP CLOSED. Pickup: **belum diketahui sebabnya** — di a095a9d 12/12 PASS dengan file yang sama; diff src d1bc8ad tidak menyentuh `ConnectedPickupPage.tsx`; diagnostik rev2 dijalankan (§9a) |
| 36123210828 / 108033307694 | multi-file `recovery` (GPT rev1 beku) | 4/4 INCOMPLETE: PATTERN/ROLE **strict-mode violation** — `.pattern-error`/`.access-error` kini cocok 2 elemen: `role=alert` (pesan) **dan** `role=status` "Ada perubahan yang hasilnya belum diketahui (UUID …). Kirim ulang perubahan tertunda" (banner W10 baru); LAUNDRY/QC INITIAL_READ: KPI tetap "—" setelah muat ulang karena fixture rev1 memakai UUID seed non-v4 yang ditolak parser halaman (akar masalah putaran 8), jadi muat ulang juga gagal — tampilan "—" adalah perilaku W13 yang benar | Bukan cacat produk. Banner W10 terlihat nyata di browser (UUID tertahan). Rev2 auditor dengan locator `[role="alert"]` dijalankan (§9a); unknown Laundry dijalankan ulang dengan rev5 (fixture v4) (§9a) |

### 9a. Run rev2 (workflow multi-file, commit 10940db): `recovery_rev2`, `wib_pickup_rev2`, `unknown_rev5` — hasil menyusul di §11

## 10. Register setelah §9

| Item | Status d1bc8ad |
|---|---|
| W2 grup oracle C0 di T2 | CLOSED (25/25 di T2 + retry native 25/25) |
| W7 grup ketat race/HTTP | CLOSED |
| W8 sen multi-penerimaan | CLOSED (total/per tanggal/bahan habis, 2 penerimaan per PO juga tepat); NOTED P3: per-PO ±1 sen pada ≥3 penerimaan; dokumen multi-bahan belum diuji |
| W9 changed_since_filing | CLOSED |
| LAU-T14 | CLOSED |
| W11 pesan asli | sumber sesuai; bukti browser: rev6 QC PASS (pesan parser tidak lagi ditutupi — kasus rev6 memuat jalur ini); Laundry menunggu rev5 (§11) |
| W13 KPI unknown | QC CLOSED (rev6 2/2); Laundry menunggu rev5 (§11) |
| W10 identitas permintaan Pola/Role | sumber sesuai + banner terlihat; PASS/COUNTEREXAMPLE menunggu rev2 (§11) |
| Browser WIB pickup | 4 zona INCOMPLETE (timeout label) — menunggu diagnostik rev2 (§11) |
| T2 / T3 package / T3 rollback / CodeQL | T2 identik (holds 12/12); T3 package success; T3 rollback success (rerun); CodeQL tidak di-dispatch ulang oleh Fable (writer 36113589299 success pada 1dcf21b, REUSED) |
| Scope owner (lampiran rev3 §0) | UNVERIFIED — ditanyakan ke owner |

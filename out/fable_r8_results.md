# Hasil auditor Fable — kandidat CP6 putaran 8 (head alat 9dd7bc2, produk acuan a095a9d) — 25 Sep 2026

Sumber tugas: `audit/input/WRITER_HANDOFF_R8_20260925.md` (handoff writer diteruskan owner). Semua run di bawah didispatch
auditor sendiri lewat API (INDEPENDENT_NATIVE_RERUN), `ref=claude/new-session-deapao`, head **9dd7bc2b9309d008e8a2e50d81876d831f3e5ea7**.
`run_identity` setiap run mencetak `product_ref=a095a9d804d29643721e18635c2c3e26adcd56ea`; diff `a095a9d..9dd7bc2` pada
`supabase/migrations supabase/dev supabase/release src` kosong (diperiksa auditor). Produk berubah dari 9add57e ke a095a9d
(BA family + frontend WIB + manifest): kandidat BARU, bukan kandidat beku 9add57e.
Verdict per kasus dibaca dari JSON per baris, bukan warna job. Hasil beku lama (run pada 9add57e) tetap tercatat apa adanya.

## 0. Identitas dan dokumen (permintaan #3)
| Item | Nilai | Status |
|---|---|---|
| Head alat | 9dd7bc2b9309d008e8a2e50d81876d831f3e5ea7 | diverifikasi (`git rev-parse origin/claude/new-session-deapao`) |
| Produk acuan | a095a9d804d29643721e18635c2c3e26adcd56ea | diff produk a095a9d..9dd7bc2 kosong |
| Addendum C0 `docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25.md` | sha256 e83d56e66812011c9a7a4057bf29987d0bcf62aabc17ad23ab422170abb00c99 | **cocok** |
| Bagian 1–8 yang disahkan (commit 5d54472) | sha256 d39762da0520f30268a73244e7471b7d990138e3cbe36475d639c7cfca8e926d | **cocok** (`git show 5d54472:…` di-hash auditor) |
| Lampiran C6 `…_LAMPIRAN_C6.md` | sha256 72621c8a978573506b8c829a2a8790de948f6cb10e83ecd14dfddf35d495bc0d | **cocok** |
| **Konfirmasi owner langsung ke auditor** | Owner (sesi auditor, 2026-09-25T05:29:02Z): "Ya, teks itu sah" — addendum C0 bagian 1–8 hash d39762da0520f30268a73244e7471b7d990138e3cbe36475d639c7cfca8e926d (commit 5d54472) disahkan untuk D01–D05. Label: OWNER_CONFIRMED_TO_AUDITOR. | O1 selesai |
| **D03 §5.3** | Owner (sesi auditor, 2026-09-25T05:29:02Z) atas D03 §5.3: "Boleh posting, dicatat unknown." Syarat yang dinyatakan owner: model PO dan ukuran tetap cocok; merek/warna yang terisi wajib cocok; yang kosong dicatat unknown, bukan dianggap cocok; produk hasil ditetapkan saat penyelesaian dan dasar penetapannya disimpan; WIP lama tidak perlu ditolak hanya karena atribut sumbernya belum lengkap. Perilaku kandidat a095a9d sesuai (xaudit_7 A10_UNBOUND_BRAND_ONLY_COLOR_UNKNOWN_POSTS, writer UNBOUND_SOURCE_NO_ATTRIBUTES_CONTROL). Pertanyaan terbuka #1 di out/fable_t2_oracles_post_addendum.md TERTUTUP. | O3 selesai |
| Kutipan bagian 9 | usulan writer "D01–D05 sah seperti tertulis, termasuk 3.4 dan 5.3…" + jawaban owner "sah bos" | teks ada dan konsisten dengan status baris; **kutipan itu dari sesi chat writer** → label auditor UNVERIFIED_OWNER_DECISION sampai owner mengonfirmasi langsung ke auditor (owner sudah mengonfirmasi D01–D06 pilihan A di sesi auditor 25 Sep ~01:25 UTC, sebelum addendum ditulis; konfirmasi atas TEKS addendum hash d39762da… belum ada di sesi auditor) |

## 1. Rerun skenario auditor pada head 9dd7bc2 (phase=after) — permintaan #1
| Skenario (sha256) | Run / job | Hasil per kasus | Arti |
|---|---|---|---|
| open_1.py (983a66f5…) | 36095519048 / 107946864058 | **13/13 PASS** (10 OVERLAP_LEGACY_AFTER_IMPORT, IMPORT_SAME_MATERIAL_TWICE, CONTROL_TOTAL_MISMATCH, FG:REVERSE_DIAGNOSTIC) | A1/CP6-09 impor-vs-impor tertutup (sebelumnya COUNTEREXAMPLE) |
| open_2.py (e8b84000…) | 36095526291 / 107946886331 | 4/4 PASS (MATERIAL same/earlier cutover, FG same cutover, FINALIZE replay); STOCK_READERS_CATALOG INCOMPLETE = kasus informatif (sama seperti run 36045629594, bukan cacat) | A1 tertutup untuk cutover sama/lebih awal |
| xaudit_1.py rev1 (32a872e5…) | 36095533518 / 107946908312 | U02 **PASS** (A3); U03 UP PASS; U03 DOWN COUNTEREXAMPLE → **oracle auditor salah** (lihat §1a); SI03 PASS | A3/CP6-02 tertutup; A4 lihat §1a |
| xaudit_2.py rev1 (108b3ebc…) | 36095540820 / 107946929867 | invoice UP PASS; invoice DOWN COUNTEREXAMPLE → oracle auditor salah (§1a); selector-101 **PASS** (A5); AV identity ×2 PASS | A5 laundry-101 tertutup |
| import_selector_fable_fix.py (d510df61…) | 36095555898 / 107946973741 | **PASS** (draf ke-51 tertua terpilih) | A5 impor-51 tertutup |
| xaudit_5.py rev1 (815781e1…) | 36095548305 / 107946952466 | R1 INCOMPLETE (skenario auditor mem-pre-commit impor pertama → dengan BA KEDUA sesi ditolak `BA_IMPORT_OPENING_ALREADY_POSTED` sebelum berlomba; kesalahan desain skenario, diperbaiki rev2 §1b); **R2 PASS** (dua sesi close tanggal sama → tepat satu filing, worker `CLOSE_ALREADY_CLOSED`, kontensi BLOCKED) = A6 tertutup; R3 COUNTEREXAMPLE-on-message (POCKET_PERIOD_BUSY ≠ STALE_VERSION, aman; A7 tidak dikerjakan writer — sesuai); H1 dua cek gagal sama seperti run 36065517737 (batas argumen dummy skenario auditor, bukan regresi); H2, H3 PASS; cleanup bersih (5 user Auth dibuat/dihapus, hitungan Auth pulih) | A6/CP6-24 tertutup; R1 diulang rev2 |
| combined_native15_reconstructed.py (cec2ad52…) | 36095563286 / 107946997431 | SI-01 INCOMPLETE dengan penolakan `BA_WIP_OUTPUT_PRODUCT_BOUND`; SI-02 INCOMPLETE dengan `BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING`; DATED_CAPACITY ×3 INCOMPLETE dengan `BA_ADVANCE_DATED_CAPACITY`; ORDERED_CONTROL ×3 PASS; MONEY ×4 PASS; SI-03 PASS; SI-04 COUNTEREXAMPLE (edit SQL langsung, kelas sudah dicatat: bukan jalur aplikasi); SEL INCOMPLETE (bug join GPT, versi perbaikan PASS di baris atas) | Oracle beku GPT sengaja menolak "PASS dari error" karena saat ditulis belum ada kode penolakan yang disahkan; kini kode itu ada di addendum (§4, §5) dan produk. Hasil beku **tidak dilabel ulang**; verdict PASS untuk perilaku ini datang dari skenario auditor sendiri (xaudit_7, §1c) |
| rt_probe_1.py (13b3b800…) | 36095570725 / 107947018623 | grup ditolak `AUDITOR_DUPLICATE_CASE_IDS` sebelum kasus berjalan (probe sengaja memuat ID ganda) | **B1 terbukti**: ID ganda menolak seluruh grup |
| rt_probe_2.py (cd6df40c…) | 36095577982 / 107947039844 | MODULE_ORIGINS/SEQ PASS; ERP_LEAK_SECOND_CONNECTION → runtime menandai `full_boundary_restored=false`, status INCOMPLETE; ERP_LEAK_VISIBLE_NEXT COUNTEREXAMPLE (baris yang di-commit lewat koneksi kedua memang terlihat di kasus berikutnya — itu yang diuji, runtime tetap fail-closed); kasus terakhir COMMIT di koneksi kasus → runtime gagal `savepoint "auditor_case" does not exist`, run INCOMPLETE | **B1 terbukti fail-closed** (bocor → INCOMPLETE). Catatan alat P3: COMMIT pada koneksi kasus membuat grup crash, bukan ditandai rapi (hasil tetap INCOMPLETE, aman) |

### 1a. Koreksi oracle auditor (A4, arah DOWN) — bukan cacat produk
Kasus U03 DOWN (10,014→10,005) dan invoice DOWN: semua cek substantif lulus (koreksi diposting, qty bahan 0, nilai persediaan 0,00
di akhir, tidak ada persediaan harian negatif). Satu cek gagal: `wip_equals_rounded_corrected_value` — skenario auditor menghitung
`Decimal('10.005').quantize(0.01)` dengan mode default Python (HALF_EVEN → 10,00), produk memposting 10,01 (half away from zero).
Kontrak tidak menetapkan banker's rounding; contoh M:485 (11,25/20 → 5,63 dan 5,62) memakai pembulatan setengah ke atas. Oracle GPT
(MONEY ×4, ROUND_HALF_UP) PASS pada run yang sama. **Disposisi: COUNTEREXAMPLE ditarik sebagai kesalahan oracle auditor**; skenario
rev2 (ROUND_HALF_UP) didispatch: xaudit_1 rev2 sha dad4331b… run 36096186788; xaudit_2 rev2 sha 06e6149c… run 36096194323 (hasil §1b).
Batas A4 yang diakui writer (≤0,01 per penerimaan pada bahan multi-penerimaan) tidak diuji auditor pada putaran ini.

### 1b. Rev2/rev3 (skenario auditor diperbaiki, produk sama)
| Skenario (sha256) | Run / job | Hasil |
|---|---|---|
| xaudit_1_rev2.py (dad4331b…, ROUND_HALF_UP) | 36096186788 / 107948841888 | **4/4 PASS** (U02, U03 UP, U03 DOWN, SI03). Job merah hanya karena mode `SAMPLE_BROWSER` runtime (bukan skenario auditor) mengembalikan INCOMPLETE dengan `users_created 0` — flake alat B4, dicatat untuk writer; kasus DB bersih, `primary_unchanged=true` |
| xaudit_2_rev2.py (06e6149c…, ROUND_HALF_UP) | 36096194323 / 107948864042 | **5/5 PASS** (invoice UP/DOWN, selector-101, AV identity ×2); browser sample RUN_COMPLETE |
| xaudit_5.py rev2 (4fec5b0d…) | 36096178430 / 107948820241 | R1: **secara substantif lulus** — holder POSTED, tepat satu opening POSTED untuk (M1,B), worker ditolak `BA_IMPORT_OPENING_ALREADY_POSTED` di bawah kontensi BLOCKED (holder memblokir worker) — tetapi status tercetak COUNTEREXAMPLE karena cek auditor membaca level pembungkus `two_sessions` (`outcome.ok`) bukan hasil op (`outcome.result.ok`); kesalahan cek, bukan produk. R2 PASS; R3 COUNTEREXAMPLE-on-message (sama); H1 dua cek dummy (sama); H2/H3 PASS; cleanup bersih |
| xaudit_5.py rev3 (ca2f7301…, cek R1 diperbaiki) | 36096552454 / 107949919590 | **R1 PASS** (exactly_one_posted, holder_posted, worker_refused, pesan = `BA_IMPORT_OPENING_ALREADY_POSTED`, kontensi BLOCKED, posted_items 1 / qty 7); R2 PASS; R3 COUNTEREXAMPLE-on-message (POCKET_PERIOD_BUSY, aman, A7); H1 dua cek dummy (sama), H2/H3 PASS; `RUN_COMPLETE`, `primary_unchanged=true`, cleanup Auth bersih |
Kesimpulan A4: dengan oracle pembulatan yang benar, seluruh 6 kasus sen auditor (U03 ×2, invoice ×2 di rev2; MONEY ×4 GPT) PASS pada a095a9d.

### 1c. Kontrol positif dan upaya bypass auditor (xaudit_7 rev2, sha e21d9d0c…, run 36095963570, job 107948186316) — **12/12 PASS**
Rev1 (sha 3ed20b76…, run 36095943675) gagal pada fixture MATERIAL auditor (field `unit` salah, bukan produk) — tercatat, tidak dipakai.
| Kasus | Expected (kontrak/addendum) | Actual |
|---|---|---|
| A1_OTHER_MATERIAL_SAME_WAREHOUSE_POSTS | sumber berbeda (bahan lain, gudang sama) tetap POSTED (M:1024; "sumber berbeda tetap boleh") | POSTED, 2 header POSTED, ledger +15,75/−15,75 |
| A1_SAME_ITEM_CASE_WHITESPACE_NOT_DOUBLED | item sama ditulis beda huruf besar/spasi tidak boleh dobel | 1 header POSTED, ledger tidak berubah (file ditolak validasi) |
| A3_PARTIAL_REVERSAL_3_OF_3_POSTS | 5 keluar d−3, dibalik hari ini; selesaikan 3 bertanggal d−1 → POSTED, timeline ≥ 0 | POSTED, minimum timeline 0 |
| A3_PARTIAL_REVERSAL_4_OF_3_REFUSED | selesaikan 4 bertanggal d−1 → ditolak, timeline tidak berubah | `BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING … hanya 3 pcs tersisa`, minimum 3 |
| A10_BOUND_SKU_A_BRAND_B_NOT_OTHER_PRODUCT | SKU A + brand B pada sumber terikat A → tidak boleh jadi produk lain (D03 §5.1) | ditolak `product_sku: pilih produk aktif…`; tidak ada lot |
| A10_UNBOUND_BRAND_MATCH_COLOR_MISMATCH_REFUSED | sumber brand A/Blue, hasil produk C (brand A, Red) → `BA_WIP_OUTPUT_SOURCE_MISMATCH` (D03 §5.2) | ditolak persis |
| A10_UNBOUND_BRAND_ONLY_COLOR_UNKNOWN_POSTS | sumber hanya brand A; hasil C (brand A, Red) → POSTED, basis SOURCE_ATTRIBUTES, BRAND checked, COLOR unknown (D03 §5.3) | POSTED; checked [PO_MODEL,SIZE,BRAND], unknown [COLOR,PATTERN,MATERIAL] |
| A10_BOUND_SAME_PRODUCT_POSTS | kontrol positif A→A, basis OPENING_PRODUCT | POSTED, basis OPENING_PRODUCT, checked [PRODUCT_IDENTITY,PO_MODEL,SIZE] |
| A9_SUPPLIER_REFUND_ON_CORRECTION_DAY_POSTS | refund 100 bertanggal TEPAT hari koreksi (kapasitas 100) → POSTED (D02 §4) | POSTED; saldo as-of 67,25 → 0,00, tidak negatif |
| A9_SUPPLIER_REFUND_DAY_BEFORE_CORRECTION_REFUSED | refund 100 sehari sebelum koreksi (kapasitas 67,25) → `BA_ADVANCE_DATED_CAPACITY`, saldo tidak berubah | ditolak persis; as-of 67,25/67,25/100/100 |
| A9_VENDOR_REFUND_DAY_BEFORE_CORRECTION_REFUSED | sama, pihak vendor | ditolak persis |
| A6_CLOSE_NEXT_DATE_AFTER_CLOSE_FILES | close d1 lalu close d2 → keduanya ACCEPTED, tepat satu filing per tanggal | ACCEPTED; filings d1=1, d2=1 |

## 2. T2 / T3 (permintaan #2)
| Workflow | Run | Hasil |
|---|---|---|
| CP6 T3 Release Package | 36095715362 (job install 107947449272, pins 107947449368, browser 107947449378) | `ALL_STAGES_INSTALLED`: 25 berkas AC..BA PASS; verify AV+AW..BA T1 (ba_sql_sha256 06d6dccb…); advisor REVIEW_REQUIRED tetapi tambahan hanya INFO `rls_enabled_no_policy` (73→129, tabel erp internal termasuk `initial_import_wip_output_identity_v1`), removed 0; drill backup/restore `RESTORED_SAME_MEANING` (19 error pg_cron dijelaskan, data identik, engine READY sama); `primary_unchanged=true`; Auth 0→0; gate {installed, primary_unchanged, drill, advisors} semua true. Browser: 10/10 PASS (login nyata, anon ditolak, replay, HPP brand exact, inverse), console_errors 0. Kapsul hosted equal. `release_evidence=false` (label T3_PREP) |
| CP6 T3 Rollback (auto → cycle) | 36095723676 / 107947475610 | `T3_ROLLBACK_CYCLE` **127/127 PASS**, `primary_unchanged=true` (AC..BA varian rilis + siklus penuh + matriks post-use, sesuai klaim B3). Bukti REUSED_WRITER_TOOLING dijalankan ulang auditor; auditor tidak mengaudit ulang isi generator rollback pada putaran ini |
| CP6 T2 Combined Regression | 36095707100 (job regression 107947426273, ar 107947426182, temporal 107947426290) | `T2_IDENTITY`: BUSINESS 230/230, IMPORTS 31/31, VALUES 65/65 tanpa perpindahan (dua kasus SUPPLIER_CENT yang regresi di BA awal kembali PASS — identik dengan referensi); NEW_CASES 34/34 dengan 9 perpindahan yang sama seperti referensi (8 DATE PASS→COUNTEREXAMPLE, ADJUSTMENT_DATE INCOMPLETE); `holds` 12/12 identik, `DISPOSITION_REQUIRED`; T2_APPROVED_ORACLE MATCH 8; T2_CALENDAR_POLICY COUNTEREXAMPLE 12 (oracle beku, tidak dilabel ulang); AO_TRIAL 8 PASS + 4 INCOMPLETE (sama); AR_CONCURRENCY 28 PASS (AR_SEQUENTIAL terbaca 106 pada 300 baris ekor log — log dipotong, job hijau); AT 16 + 4 race PASS, AU 15 + 6 race PASS, `primary_unchanged=true`. **T2 tidak hijau by design** (25 kasus beku), sesuai M:1769; oracle pengganti ada di §4 |

## 3. Lampiran C6 vs Master (permintaan #5) — `out/fable_c6_annex_review.md`
9 dari 11 baris cocok. **2 baris tidak cocok**: ACC-04 (aksesori internal/retur) dan LAU-05 (paket/komponen + invoice laundry susulan)
dilabeli CR-TUNDA "usulan", padahal M:1668 menyatakan "Tetap dibutuhkan" (LAU-05 bahkan "perluasan bisnis yang sudah disetujui",
M:3729–3737) dan M:1691–1699 menaruh keduanya dalam gelombang sebelum audit gabungan CP6. Ini melanggar aturan D06 butir 2 addendum
(bug/baseline tidak boleh ditunda sebagai CR). Tambahan: 7 sub-keputusan M:4448–4479 (ACC-DEC01/03/04/05/06/07, ERP-DEC02) dan
LAU-DEC01/02/03/05/06 tidak punya baris acceptance sendiri (aturan D06 butir 3: daftar per fitur).
**Rekomendasi auditor: owner belum bisa mengesahkan D06 apa adanya.** Writer: (1) ubah ACC-04 dan LAU-05 ke BASELINE untuk
mekanisme/tracking, tandai PENDING KEBIJAKAN hanya untuk sub-butir nilai/tarif yang memang belum diputus; (2) tambah baris untuk
ACC-DEC01/04/06/07, ERP-DEC02 dan pecah LAU-DEC01–06; (3) ajukan ulang → auditor cocokkan ulang → owner sahkan D06 → GATE-16 dinilai.

## 4. Oracle baru 25 kasus T2 + CP6-07/CP6-18 (permintaan #4) — `out/fable_t2_oracles_post_addendum.md`
Diturunkan dari addendum D01 §3.1–3.5, D02 §4, D03 §5 dan M (1059–1065, 625–646, 357–379, 3816–3825, 4324); fakta fixture dibaca
dari kode harness writer, expected harness TIDAK dipakai. Ringkasan disposisi: 12 CALENDAR + 8 DATE + 4 AO_TRIAL → di bawah D01
(kaki invoice/AP di tanggal invoice E; kaki WIP/FG/COGS di max(E, hari perpindahan fisik); periode tertutup di hari pengakuan)
perilaku kandidat yang dulu "cut-day dating" justru sesuai → expected **PASS** (24/25); ADJUSTMENT_DATE:False tetap **INCOMPLETE**
(M:4324) karena rumus tanggal di harness sendiri tidak sesuai D01 §3.3 (harus max(E, tanggal penyesuaian)) → perlu perbaikan fixture.
Oracle CP6-07 (3 negatif + 3 kontrol) dan CP6-18 (5 kasus) ditulis dengan assertion tabel/kolom persis; sudah terbukti natively di §1c.
**Hasil beku T2 lama tidak dilabel ulang** (M:1769). Tugas writer: tambahkan grup oracle pasca-addendum BARU di harness T2 (tanpa
menghapus assertion beku), perbaiki fixture ADJUSTMENT_DATE per §3.3; auditor membaca data per kasus dari run berikutnya.
Pertanyaan terbuka addendum (5 butir, §6 dokumen): D03 §5.3 "unknown" boleh posting vs ditolak (teks §5.3 sendiri minta penegasan
owner); kolom tanggal buku vs ekonomi pada `material_cost_revaluation_events`; contoh angka batas §3.4; rumus kapasitas stok AUD-S04;
D06/C6 belum disahkan.

## 5. Review sumber BA (adversarial, agen terpisah) — `out/fable_ba_source_review.md`
A3, A6, A9, A10, A2: CLOSED (guard + oracle independen, varian adversarial diblokir). A4: CLOSED untuk kasus satu penerimaan; residu
multi-penerimaan ≤0,01 diakui writer (batas, bukan cacat tersembunyi). A1: PARTIAL — identitas impor-vs-impor rapat (material/roll,
FG+gudang+grade, WIP/BS tanpa PO, kas per akun), tetapi (i) legacy-vs-legacy tidak dicek (di luar klaim A1) dan (ii) identitas
CASH_BANK memakai `cash_account_id`, bukan `coa_account_id` (dua akun kas ke COA yang sama tidak dianggap sama — belum diverifikasi
apakah itu alias nyata). Catatan: BA hidup di `supabase/dev/cp6_ba_t1_family.sql` + `supabase/release/cp6-t3(-src)/`; satu tabel baru
`erp.initial_import_wip_output_identity_v1` (RLS on, grant dicabut); tidak ada GRANT baru; guard idempoten/rollback ada.

## 6. A7 dan A8 (permintaan #6) — keputusan auditor
- **A7 (CP6-25, STALE_VERSION vs POCKET_PERIOD_BUSY)**: tidak perlu untuk gate CP6. Perilaku aman (output ganda tidak terjadi; R3
  membuktikan lagi di 9dd7bc2). Masuk backlog pesan/UX. Tidak menahan.
- **A8 (CP6-19 residu: grant `authenticated` pada `erp.prepare_migration_opening_balance` + tidak ada cek ulang item-vs-staging)**:
  tidak perlu untuk gate CP6 (jalur aplikasi sah terbukti benar, xaudit_6 rev3). **Direkomendasikan** dikerjakan sebelum rilis sebagai
  hardening kecil (cabut grant `authenticated`; hanya FINALIZE yang memanggil), karena biaya rendah dan menutup satu-satunya jalur
  (RPC langsung + edit tabel) menuju posting stale. Tidak menahan gate.

## 7. Status register setelah putaran 8 (dari bukti auditor sendiri; rev2 dan T2 menyusul)
| ID | Sebelum | Sesudah (9dd7bc2 / a095a9d) |
|---|---|---|
| CP6-09 / A1 | CONFIRMED P1 | **CLOSED** (open_1 13/13, open_2 4/4, xaudit_7 A1 ×2; R1 dua sesi menyusul rev2) |
| CP6-01 / A2 | CONFIRMED P1 | **CLOSED_BY_SOURCE_REVIEW** (INDEPENDENT_SOURCE_REVIEW: tiga halaman memakai helper WIB, test writer 4 zona); tanpa run browser auditor sendiri — lihat batas |
| CP6-02 / A3 | CONFIRMED P1 | **CLOSED** (U02 PASS, xaudit_7 A3 ×2, SI-02 menolak dengan kode yang disahkan) |
| CP6-03 / A4 | P2 | **CLOSED untuk kasus tunggal** (U03 UP, invoice UP, MONEY ×4 PASS; DOWN = oracle auditor salah, rev2 menyusul); batas multi-penerimaan ≤0,01 tercatat |
| CP6-04 / A5 | P2 | **CLOSED** (selector-101 PASS, selector-51 PASS) |
| CP6-24 / A6 | P3 | **CLOSED** (R2 dua sesi: satu filing; xaudit_7 A6 close tanggal berikutnya tetap jalan) |
| CP6-07 / A9 (D02) | P1 setelah D02 | **CLOSED** (ORDERED_CONTROL ×3 PASS; DATED ×3 ditolak `BA_ADVANCE_DATED_CAPACITY`; xaudit_7 A9 ×3 termasuk batas hari koreksi) |
| CP6-18 / A10 (D03) | P2 setelah D03 | **CLOSED** (SI-01 ditolak `BA_WIP_OUTPUT_PRODUCT_BOUND`; xaudit_7 A10 ×4 termasuk provenance unknown) |
| CP6-25 / A7 | P3 | tetap terbuka, tidak menahan |
| CP6-19 residu / A8 | P3 | tetap terbuka, direkomendasikan, tidak menahan |
| CP6-17 ALL coverage | CONTRACT_DECIDED_COVERAGE_OPEN | belum dikerjakan putaran ini (batas) |
| 25 T2 beku | HOLD | oracle baru tersedia (§4); harness belum memuatnya → tetap HOLD sampai run dengan grup oracle baru |
| D06 / GATE-16 | menunggu C6 | **C6 belum bisa disahkan** (§3) |
| Rollback T3 | AC..AV NOT_BUILT | **AC..BA cycle 127/127 PASS** (run 36095723676); BLOCKER-03 turun ke "tooling terbukti, kualifikasi rilis tetap T3_PREP" |

## 8. Batas putaran 8
Browser→HTTP→runtime UI oleh skenario auditor sendiri belum dibuat (mode B4 tersedia; T3 browser flow writer 10/10 dipakai sebagai
REUSED_WRITER_EVIDENCE); cakupan ALL 22 state/6 keluarga belum diuji; A4 multi-penerimaan; generator rollback tidak diaudit ulang;
konfirmasi owner langsung atas teks addendum (hash d39762da…) belum diterima auditor; H1 masih memakai argumen dummy pada dua facade.


## 9. Pembaruan akhir (2026-09-25T05:06:51Z)
- xaudit_5 rev3 (run 36096552454): R1 dua sesi **PASS** → CP6-09 tertutup juga di bawah dua sesi nyata pada a095a9d. Register §7 baris CP6-09: CLOSED (lengkap).
- Review C6 independen GPT (`out/gpt_round8_c6_review.md`, commit 1443f16) sejalan dengan §3: ACC-04 SPLIT (fitur baru boleh CR, perilaku lama baseline), LAU-05 SPLIT (desain sudah disetujui M4448/4479), LAU-07 terlalu luas; GPT menambah syarat crosswalk ke seluruh ID asli (39 ACC, 24 LAU-R, 36 LAU-T) dan inventaris CR-MASUK yang belum diverifikasi → temuan GPT R8-C6-01 (P2 dokumentasi). Kedua auditor: **D06/GATE-16 tetap HOLD sampai lampiran diperbaiki.**
- Verdict: CP6 HOLD, audit_complete=false, production_go=false.

## 10. Konfirmasi owner (2026-09-25T05:29:02Z)
- Owner (sesi auditor, 2026-09-25T05:29:02Z): "Ya, teks itu sah" — addendum C0 bagian 1–8 hash d39762da0520f30268a73244e7471b7d990138e3cbe36475d639c7cfca8e926d (commit 5d54472) disahkan untuk D01–D05. Label: OWNER_CONFIRMED_TO_AUDITOR.
- Owner (sesi auditor, 2026-09-25T05:29:02Z) atas D03 §5.3: "Boleh posting, dicatat unknown." Syarat yang dinyatakan owner: model PO dan ukuran tetap cocok; merek/warna yang terisi wajib cocok; yang kosong dicatat unknown, bukan dianggap cocok; produk hasil ditetapkan saat penyelesaian dan dasar penetapannya disimpan; WIP lama tidak perlu ditolak hanya karena atribut sumbernya belum lengkap. Perilaku kandidat a095a9d sesuai (xaudit_7 A10_UNBOUND_BRAND_ONLY_COLOR_UNKNOWN_POSTS, writer UNBOUND_SOURCE_NO_ATTRIBUTES_CONTROL). Pertanyaan terbuka #1 di out/fable_t2_oracles_post_addendum.md TERTUTUP.
- Yang masih terbuka untuk owner: O2 (D06 setelah lampiran C6 diperbaiki W1 dan dicocokkan ulang auditor).

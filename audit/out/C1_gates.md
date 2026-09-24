# C1 — Contract lens: CP6 gates, evidence labels, owner decisions, tiering, CP6/CP7 boundary

Agent: C1 (blind phase 1, contract lens). Date: 2026-09-24.
Candidate under audit: 9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc (tree 5d5f833b…). Contract's own "tested source" is a different commit (see §0).

Sources (only these are oracles):
- M = pack/kontrak/ERP_V3_2_Master_Pulih_20260923.md (7236 lines)
- P = pack/kontrak/ERP_V3_2_Perubahan_Pulih_20260923.md (1205 lines)
- A = pack/kontrak/ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md (617 lines; CP6/CP7 boundary only)
Background file (latar) was not used as an oracle. No docs/ file, no commit message, no run log, no prior audit report was read. Candidate/harness workflow YAML headers and script docstrings were read only to learn what tiers/decisions the writer quotes; those are WRITER CLAIMS.

Line references are `file:line`. Quotes are verbatim (Indonesian) so another agent can `sed -n` them.

---

## 0. Identity binding: what the contract calls "tested" is NOT the candidate

| Item | Contract value | Where |
|---|---|---|
| Tahap | "CP6 HOLD; CP7 belum dimulai" | M:26 |
| Kelulusan | "Writer AQ PASS pada database sementara; penerimaan independen dan owner belum selesai" | M:27 |
| Produksi | "production_go:false; hosted_migration_installed:false" | M:28 |
| Sumber kode diuji / tree | `5ae73305e118f3641202ae4070ae2264c92de44b` / `c34f0df572534759c0756bbb2b5dae084bb8ab78` | M:33-34, M:120-121 |
| Gerbang yang belum lulus | "Full-Schema berhenti pada batas sumber AC; Final Boundary pada batas sumber AI-R2" | M:36 |
| Pekerjaan berikutnya | "Overlap semua jalur opening lama; gerbang gabungan keluarga terdampak; audit independen; acceptance owner" | M:37 |

Consequence (contract rule): "PASS versi lama tidak otomatis berlaku setelah source/dependensi berubah." (M:1624); "Jika berubah, jangan menganggap bukti ini fresh pada kode baru." (M:1254); reuse must be labelled after hash + source-equivalence check (M:1295-1296, M:4393). Every PASS number in the contract is therefore historical for 9add57e until re-bound.

Document-level authority rule: "Instruksi owner terbaru tetap menentukan keputusan; konflik aturan yang belum mempunyai keputusan eksplisit harus dicatat, bukan ditebak." (M:19-20). "Angka pengujian historis tidak dijumlahkan menjadi klaim semua suite lulus pada AQ." (M:42).

---

## 1. Gates the contract requires before CP6 can be accepted

Status column = status *as the contract records it on 23 Sep 2026* (not the candidate's status). "Families" use the contract's own IDs (R1.4 map M:1706-1739; ACC/LAU/CROSS groups M:4330-4386, M:5250-5309).

### GATE-01 — Opening-overlap protection on ALL legacy opening paths
- Quote: "Berikutnya: buktikan perlindungan tumpang tindih saldo awal pada semua jalur lama" (M:138). "tutup overlap semua jalur opening lama" (M:229). "perlindungan overlap seluruh jalur opening lama masih menjadi gate berikutnya" (M:361). "identitas dokumen lintas batch dan tumpang tindih saldo awal vs dokumen operasional masih perlu kontrak/tes" (M:1043). "Jalur direct legacy yang membukukan opening setelah impor, koreksi dokumen, serta race antarsesi masih perlu pemetaan/tes sebelum mengklaim perlindungan global" (M:953).
- Status per contract: OPEN (listed as next work in the newest checkpoint AQ, M:37/M:138).
- Would prove: for every legacy opening/direct path (opening canonical, direct legacy opening after import, document correction, ordinary purchase path re-entering an imported receipt number, cross-batch identity, two-session race) a counterexample attempt is refused atomically with no ledger/stock change and boundary restored; plus positive controls. Evidence per case per M:4325.
- Families: Opening/import (AUD-B01–B03, AUD-T01/T02, AUD-G08), ALL impor (M:1024), transfer/histori (AUD-S02–S04), concurrency (ACC-D01–D05).

### GATE-02 — Combined affected-family gate on the frozen final candidate, with correct successor scope
- Quote: "jalankan gerbang gabungan keluarga terdampak dengan cakupan penerus yang tepat" (M:138). "Setelah keluarga stabil, jalankan satu gate keluarga yang diperlukan. Pada kandidat gabungan yang mengubah cost, tanggal, transfer atau kontrak laundry/aksesori, **rencanakan full business/integration gate**, termasuk hubungan lintas domain yang benar-benar terdampak; jangan cukup mengambil 65 tes AL sebagai bukti seluruh ERP." (M:1764). "Bekukan kandidat, jalankan gate bisnis/integrasi gabungan yang relevan, lalu final audit independen CP6 dan keputusan lock" (M:1693). "fresh full business/integration pada kandidat gabungan yang benar-benar berubah" (M:1582-1583). "audit global independen pada scope successor yang benar" (M:229).
- Status per contract: NOT RUN on the successor scope; the legacy global gates fail at the source boundary (GATE-03). Focused/native gates PASS but "Hasil focused gate yang lulus tidak menggantikan Final Boundary global yang masih gagal" (M:313; also M:407).
- Would prove: one gate run on the exact frozen SHA/tree/runtime whose source-routing guard *explicitly* accepts the successor delta ("source-routing guard tetap harus menerima delta secara eksplisit", M:6661) and executes the business/integration cases of every changed family (AL, AM, AN, AO, AP, AQ and later) plus the cross-domain scenarios actually affected (CROSS-T01–T06, M:4377-4384). Counts must not be blended (M:4393).
- Families: all changed families; CROSS-T01–T06.

### GATE-03 — Legacy global gates (Full-Schema, Final Boundary) must not be loosened or relabeled
- Quote: "Full-Schema 35753835628 masih gagal pada gerbang sumber lama `AC_ONLY_EXACT_SUCCESSOR_REPAIR_ALLOWED` sebelum pengujian bisnis. Final Boundary 35751402410 juga gagal pada batas sumber AI-R2 … Gerbang lama tidak dilonggarkan" (M:136). "Gerbang historis itu tidak diubah. Bukti writer yang lulus tidak menggantikannya." (M:223). "Workflow lama yang menolak scope successor tidak boleh dilabel ulang PASS." (M:957). "Routing workflow lain yang sukses bukan acceptance." (M:875). "Router full-schema SUCCESS juga bukan fresh matrix460." (M:1492).
- Status per contract: FAIL at source boundary (both), explicitly kept as failures.
- Would prove: either (a) the same workflows pass on the frozen candidate with an explicit, reviewed successor-scope delta accepted by the source-routing guard, or (b) a successor-scoped global gate exists and the old ones are still recorded as FAIL, never relabeled. The contract does not choose between (a) and (b) — see CONTRACT_GAP F-04.
- Families: harness/routing; every successor since AC / AI-R2.

### GATE-04 — Real HTTP/Auth-JWT/browser path and concurrency for ALL business transactions
- Quote: "buktikan RPC lewat HTTP dengan Auth JWT nyata dan browser; kualifikasi transaksi bisnis yang berjalan bersamaan" (M:229). "concurrency seluruh transaksi bisnis … belum selesai" (M:317; M:422). "Ini bukti mutex saja; seluruh transaksi bisnis serentak belum diuji." (M:489). "Dua sesi harus dua koneksi sungguhan dengan bukti blocking/winner/commit; urutan sequential bukan concurrency." (M:4323).
- Status per contract: PARTIAL — AQ: "29 pemeriksaan Auth/browser dan 6 skenario HTTP bersamaan PASS" (M:92), deadlock found and fixed in AQ (M:100-106); coverage is the listed families only, not all transactions.
- Would prove: for each connected writer domain (contract lists eight recovery domains, M:295) a real-Auth HTTP + browser flow and a two-connection schedule with blocking/winner/commit evidence; refusal keeps all ERP tables unchanged (M:98).
- Families: AUD-G07 (roles), AUD-G14 (race), AUD-G15 (cross-tab), ACC-D01–D06, LAU-T30–T33.

### GATE-05 — 12 date/report HOLD cases closed under ERP-DEC01 (one family: recost–GL–HPP–as-of–confidence–close)
- Quote: "Dua keputusan bisnis sudah ada, tetapi 12 kasus laporan/tanggal dan jalur jumlah fisik eceran masih perlu perbaikan serta bukti. Keputusan owner bukan hasil tes." (M:1080-1082). "Satu keluarga tanggal invoice, recost, HPP/FG/COGS, GL, confidence, backdate, as-of dan close/reopen.12 HOLD tetap sampai kebijakan dan bukti lengkap." (M:1404). "Banyaknya kontrol lulus tidak mengubah kelompok ini menjadi PASS." (M:1653). "Empat skenario tanggal yang baru tidak mengubah 12 catatan historis DATE_POLICY_REVIEW_REQUIRED menjadi PASS baru." (M:1045).
- Status per contract: HOLD (12 × DATE_POLICY_REVIEW_REQUIRED). Decision exists (ERP-DEC01, M:1059-1065); implementation claimed in AO ("Jurnal koreksi akibat invoice memakai tanggal invoice", M:837) but the 12 cases are not recorded as closed.
- Would prove: the 12 historical cases (invoice 1/2/3 months late; JAN31/FEB28/MAY31 boundaries; UTC/Kiritimati, M:1653) re-executed on the frozen candidate with expected values derived from ERP-DEC01, showing stock value, journal, WIP, FG, COGS, per-date report and readiness indicator consistent (M:1060-1062); closed period still uses controlled adjustment (M:1063); filed reports preserved (M:1064-1065); no false READY (M:1751).
- Families: AUD-B04, AUD-S06, ACC-D08, LAU-T23, CROSS-T06, BR-T30 (A:561).

### GATE-06 — Exact-PCS retail path under ACC-DEC02
- Quote: "harga eceran diketik manual … Jumlah fisik 7 buah harus tetap tepat 7. Keputusan ini tidak menetapkan aturan pembulatan baru dan tidak mengubah nominal transaksi lama" (M:1066-1071). "Pisahkan qty fisik exact dari satuan harga dan buktikan nominal/pembulatan/retur/recost. Jangan mengubah guard menjadi menerima qty pecahan." (M:1405). "7 PCS adalah aksesori." (M:44, M:1022).
- Status per contract: writer PASS on AO/AP/AQ ("draft 5 diubah menjadi 7 dengan harga eceran 3,25, menghasilkan 22,75 dan stok 300→293", M:94; M:210-211); independent pending.
- Would prove: 7 PCS against lusin/gross master posts qty exactly 7, bill = 7 × manual price, master untouched, replay once, linked inverse restores stock and all accounts; fractional PCS still refused (M:1534). Payroll/return/recost consumers (M:6647-6649 "PCS dan harga aksesori" tracing list).
- Families: AUD-S01, ACC-A01/A02/A04/A07/A08, CROSS-T04.

### GATE-07 — CSV transport through the application for the approved scope (ALL) — AUD-G08 / ERP-DEC03
- Quote: "ALL impor tetap merupakan kewajiban, bukan kesimpulan dari jumlah tipe CSV." (M:138). "Scope impor yang sudah disetujui adalah **ALL data awal**, sesuai keputusan owner di repo: master, stok dan nilai awal, kas/piutang/utang/uang muka, serta dokumen operasional yang masih terbuka." (M:1024-1025). "Tetap gate terbuka CP6 sampai lingkup/caller ditetapkan dan diuji; staging JSON tidak menggantikannya." (M:1730). "Bangun dan uji CSV sesuai scope termasuk quoting/delimiter/encoding, per-line error, perubahan draft, replay, role dan batch atomicity. NativeJSON31 bukan bukti CSV." (M:1406).
- Status per contract: OBLIGATION OPEN; writer evidence exists for file upload via file picker (M:92) and 17–19 template types (M:930, M:629); independent pending. Contract carries two states for ERP-DEC03 (see F-03).
- Would prove: real CSV/TSV files through the app's file picker → preview/edit → validate → finalize for each approved entity type; last-draft content posted once; control totals not posted (M:43-44); per-line errors; replay; roles; atomicity.
- Families: AUD-G08, AUD-B03, ALL impor (M:1043), recovery domain INITIAL_IMPORT.

### GATE-08 — Role/access scope for CP6 (AUD-G07) closed for the final scope
- Quote: "PARTIAL_EVIDENCE; role belum universal | Tutup scope Auth/action/location CP6 sekarang; setiap jalur baru wajib membuktikan scope-nya sebelum diterima." (M:1729). "Tutup role/akses yang terkait scope final; perluas matrix hanya bila ada contract atau jalur yang belum terbukti." (M:1407). "Jangan menutup AUD-G07 universal dengan jumlah itu." (M:1526).
- Status per contract: PARTIAL_EVIDENCE (92 access controls R4, M:1122; 12 writer attempts AQ, M:98).
- Would prove: every new facade/RPC since the last accepted scope has anon/viewer/unmapped/inactive/revoked refusals through real Auth/HTTP with table-content unchanged, plus positive reader controls.
- Families: AUD-G07, ACC-D06, LAU-T33, BR-T33 (CP7).

### GATE-09 — Writer-fixed families need VERIFIED_INDEPENDENT (frontend recovery A01–A05/G15; transfer S02–S04; selector S05; AL B01–B03/T01–T02; AO/AP/AQ families)
- Quote: "Writer PASS affected; independent acceptance pending." (M:1259; M:1308; M:1495). "FIXED_WRITER pada AL; independen pending" (M:1720-1722). "Auditor independen harus meninjau perbaikan frontend/AM/AN dan sisa scope dengan oracle sendiri. Hasil writer tidak menjadi oracle atau independent PASS." (M:1222-1224).
- Status per contract: FIXED_WRITER / writer PASS; independent_acceptance:false (M:84).
- Would prove: independent re-execution with the auditor's own expected values on the exact frozen SHA, including counterexamples outside the writer's list ("terutama interaksi transfer/recost/report, sesi/refetch, paging/selected identity/versi, role dan rollback/cleanup", M:1432-1433).
- Families: AUD-A01–A05, G15, S02–S05, B01–B03, T01–T02, AO/AP/AQ (import, accessory retail, pocket fabric, WIP/BS, advances, cash advance, uninvoiced receipts).

### GATE-10 — Permanent migration package (AO/AP + AQ) install / pre-use rollback / refusal on disposable, byte-bound
- Quote: "Paket SQL permanen AO lalu AP sudah dibuat, dipasang dengan commit pada database sementara, dipulihkan, dipasang ulang, dan dipulihkan kembali … Paket belum dipasang pada database hosted, UAT, legacy, atau produksi." (M:163). "Rollback **hanya sebelum pemakaian** … AP harus dipulihkan sebelum AO … Seluruh isi lama dan katalog harus kembali tepat sebelum commit." (M:206). AQ: "Dua siklus AP→AQ→AP memulihkan tepat katalog … Rollback dengan admission terbuka ditolak tanpa perubahan. Rollback setelah transaksi bisnis juga ditolak tanpa perubahan" (M:110). "Builder menghasilkan kembali SQL migrasi, rollback, dan pins AQ dengan byte identik." (M:114).
- Status per contract: WRITER_PACKAGE_PASS (M:155); hosted rollout "belum diberikan atau dijalankan" (M:200) — hosted install is NOT a CP6 gate.
- Would prove: on the frozen candidate the builder regenerates identical bytes (SHA256 table M:189-194), install/rollback cycles restore catalog/data/migration history exactly, the 38-refusal classes (M:208) still refuse, and any successor after AQ has its own capsule and refusal evidence.
- Families: AUD-T02, ACC-D11, LAU-T35, maintenance schedules.

### GATE-11 — Freeze exact SHA/tree/runtime; doc-only delta; per-ID evidence bound to the tested commit
- Quote: "Freeze exact SHA/tree/runtime, periksa hasil per ID, restore/refusal/cleanup yang relevan, lalu auditor berbeda menilai perbaikan serta jalur residual." (M:1767). "Checkpoint setelah sumber diuji hanya mengubah `docs/cp6-ap-flow.md`. CRC, SHA256, head/tree, hash semua berkas sumber terhadap objek Git … sudah diperiksa." (M:132). "Penerus harus membaca report JSON per-ID dan source pinned, bukan jumlah PASS dari ringkasan." (M:1596-1597). "Jangan memakai nama file “qualified” sebagai pengganti membaca status per kelompok." (M:1488).
- Status per contract: done for 5ae7330 only.
- Would prove: for 9add57e, artifact SOURCE/tested head+tree equal the candidate, product/SQL/pins byte-identical to what ran, failures preserved (M:132 "Bukti gagal tidak diganti menjadi PASS").
- Families: evidence integrity (PROTOCOL).

### GATE-12 — Independent audit by a different auditor with own oracles, on repairs AND residual paths
- Quote: "Sesudah writer memverifikasi versi final pada exact SHA, serahkan kepada auditor lain untuk menguji perbaikan **dan jalur residual di luar daftar writer**. Writer tidak memberikan independent PASS atas perbaikannya sendiri." (M:4500-4501). "Tidak ada self-acceptance. Jika alat, fixture atau waktu tidak cukup, tulis INCOMPLETE/BELUM TERUJI, jangan PASS." (M:1436-1437). "Audit **final CP6** harus menilai kandidat terakhir setelah semua perubahan dalam scope final stabil." (M:1624).
- Status per contract: independent_acceptance:false (M:84, M:27).
- Would prove: an audit report on the frozen SHA that (a) lists per-ID status with the columns of M:4492, (b) contains counterexamples attempted beyond the writer's list, (c) labels everything unexecuted INCOMPLETE/BELUM TERUJI.
- Families: all.

### GATE-13 — No POLICY_BLOCKED / INCOMPLETE / unfinished material case inside CP6 scope at lock
- Quote: "Untuk scope CP6 sendiri, belum boleh ada `POLICY_BLOCKED`, `INCOMPLETE`, atau kasus material yang belum selesai lalu diberi label lock." (M:1699). "Kasus yang memerlukan kebijakan belum dipilih tidak otomatis di-skip sebagai PASS." (M:4387). "Bagian yang terputus/tidak tereksekusi tetap INCOMPLETE/BELUM TERUJI." (M:1220-1221).
- Status per contract: not met (12 HOLD, open gates above).
- Would prove: zero POLICY_BLOCKED/INCOMPLETE/HOLD in the CP6-scope register at lock time; CP7+ items may stay open "pada tahapnya" (M:1699-1700).

### GATE-14 — CP6_LOCK_READY sah, then owner acceptance and owner command for CP7; production GO separate
- Quote: "Jangan mulai CP7 sampai CP6_LOCK_READY sah dan owner memberi perintah." (M:1218-1219). "Sesudah keluarga final stabil: gate bisnis/integrasi sesuai perubahan, freeze SHA/tree/runtime, audit independen pada kandidat itu, dan hasil CP6_LOCK_READY yang sah. Baru perintah owner membuka CP7." (M:1418-1420). "Penerimaan owner masih diperlukan sebelum CP7 atau production GO." (M:229). "CP6 GLOBAL: HOLD sampai seluruh gate sah ditutup / production_go:false" (M:4517-4518). "Go-live tetap membutuhkan gate serta keputusan owner tersendiri." (M:4527).
- Status per contract: not given.
- Would prove: an explicit owner statement after the independent audit; the contract defines no format for it (silence noted).

### GATE-15 — Historical matrices: rerun only what drift/counterexample invalidated, labelled; never blended
- Quote: "Matrix historis besar diulang bila perubahan source/runtime/lock behavior/invalid checksum/oracle/counterexample membatalkan buktinya." (M:4391). "Matrix460 historis adalah maintenance lintas generasi … tidak otomatis mengulang460 setelah tiap edit." (M:1766). "Rekonsiliasi 230 berisi HOLD tanggal dan reuse; tidak boleh dilaporkan sebagai 230 PASS baru. CodeQL 0 result tidak mengubah business failure menjadi PASS." (M:6663).
- Status per contract: 230/import31/value65/concurrency = REUSED_EVIDENCE on AN (M:1161-1163); "Matriks historis global belum dijalankan ulang" (M:229, M:317).
- Would prove: for the candidate, each historical group carries one of NEW_EXECUTION/REUSED_EVIDENCE/RECONCILED/RERUN_REQUIRED/DRIFT with hash + source-equivalence justification.

### GATE-16 — Accessory/laundry CR wave: either complete in the final candidate or explicitly excluded by owner; never used to defer old CP6 findings
- Quote: "Bila CR dipilih masuk kandidat final CP6, acceptance CR yang relevan juga harus tuntas atau scope kandidat direvisi owner secara eksplisit; tidak ada pengecualian diam-diam." (M:1755-1756). "Jika owner memilih CR itu dikerjakan setelah baseline CP6 dikunci, simpan sebagai successor terpisah … Tidak ada temuan lama CP6 yang boleh ikut ditunda melalui cara ini." (M:1697). "Penempatan change request aksesori/laundry tidak boleh dipakai untuk menggeser blocker CP6 ke CP7 tanpa keputusan." (M:4422).
- Status per contract: AO/AP checkpoints implemented the accessory retail form and pocket-fabric family inside the CP6 branch (M:238-323, M:436-517), so at least those CR parts are in the final candidate; laundry master/vendor/pending (LAU) is still APPROVED_NOT_IMPLEMENTED (M:4488). No owner statement in the contract fixes the CR boundary of the final candidate (F-07).

### Not a CP6 gate (explicitly out of scope, for boundary clarity)
- Hosted/UAT/legacy/production install: "jalur rollout hosted belum diberikan atau dijalankan" (M:200); "Main, PR24/25, hosted UAT/legacy/produksi, merge dan deploy tidak diubah." (M:138). Reproduction must use "database disposable exact-schema, bukan kedua endpoint hosted" (M:6606); Enteng `siimvrusnzxexizpyoib` is "konteks UAT/calon production" (M:6606).
- Security advisors: "109 temuan baseline belum dinyatakan selesai" (M:112) — recorded, no threshold/gate defined (F-06).
- CP7 items (planner, BR, UX32, Stok per-SKU, Tanya AI V1, scheduler, rebaseline, cutover): "tetap terbuka pada tahapnya" (M:1699), AUD-G09–G12 (M:1731-1736).

---

## 2. Evidence-label vocabulary required by the contract

Group/evidence level (M:4393): `NEW_EXECUTION`, `REUSED_EVIDENCE`, `RECONCILED`, `RERUN_REQUIRED`, `DRIFT`, `INCOMPLETE` — "Tidak mencampur helper observations, codeql results, jumlah payload, jadwal maintenance, dan kasus bisnis menjadi satu angka PASS." Also M:5315, M:5714 ("Bukti yang digunakan kembali ditandai REUSED_EVIDENCE/RECONCILED; yang perlu diulang RERUN_REQUIRED/DRIFT").

Per-ID status (M:4494): `OPEN`, `REPRODUCED`, `FIXED_WRITER`, `VERIFIED_INDEPENDENT`, `RISK_DISPROVED_WITH_EVIDENCE`, `POLICY_BLOCKED`, `TOOLING_BLOCKED`, `PLANNED_NOT_IMPLEMENTED`; columns `initial_evidence, current_status, candidate_sha/tree, source_changed, tests/evidence, remaining_decision, next_action` (M:4492). Additional per-ID statuses used by the contract's own register: `WRITER_VERIFIED`, `PARTIAL_EVIDENCE`, `NOT_AUTHORIZED / NOT_PROVEN`, `APPROVED_DESIGN / POLICY_PENDING / NOT_PROVEN_IMPLEMENTED`, `HOLD` (M:1724-1737); `APPROVED_NOT_IMPLEMENTED` (M:4488).

Per-case outcome: `PASS`, `CONTROL_PASS`, `BUG_PROVEN`, `GAP_PROVEN`, `INCOMPLETE`, `DATE_POLICY_REVIEW_REQUIRED` (= HOLD) (M:1534, M:1651-1653, M:1275-1276); `INCOMPLETE/BLOCKED_BY_TOOLING` (M:5313, M:3529); `NOT_RUN` (M:2115, M:2763); `BELUM TERUJI` (M:4402, M:3667). Rule: "Tool error/setup error/missing data = INCOMPLETE, bukan BUG_PROVEN atau PASS." (M:4325). "Hipotesis yang ditolak guard existing ditutup dengan bukti, bukan dipaksakan menjadi bug." (M:1762). "ACL denial tidak dihitung sebagai bukti guard." (M:487).

Global flags: `CP6_HOLD` / `CP6 HOLD`, `CP6_LOCK_READY` (M:1219), `production_go:false`, `hosted_migration_installed:false`, `independent_acceptance:false` (M:84), `global_cp6_acceptance:false` (M:1653), `migration_installed:false` (M:240).

Writer-verdict vocabulary (never equal to independent PASS): `WRITER PASS`, `WRITER_PACKAGE_PASS` (M:155), `WRITER_PASS_AFFECTED_*` (M:1259-1262), "Writer PASS terbatas" (M:1122); "Native/browser PASS pada cakupan tertentu bukan independent PASS atau izin lock CP6. Dilarang mengubah arti HOLD, GAP, INCOMPLETE atau reused evidence." (M:1467-1468).

Per-case record content (M:4325; M:5311): ID, candidate/tree/runtime, actor/role/location/timezone, input, expected, actual, request ID, before/after domain boundary, cleanup; "Kumpulkan hasil semua kasus meskipun satu gagal."

---

## 3. Owner decisions

### 3a. Decisions that ARE in the contract (quote + line)
| ID / topic | Status in contract | Quote |
|---|---|---|
| ERP-DEC01 book date for open-period corrections | DIPUTUSKAN, belum diterapkan/diuji | "koreksi biaya/invoice pada periode yang masih terbuka mengikuti **tanggal invoice** … Aturan periode tertutup tetap memakai penyesuaian terkendali yang sudah ada … data terkoreksi terbaru tetap menjadi acuan operasional." (M:1059-1065); owner words "invoice, eceran free text" (M:1056) |
| ACC-DEC02 retail price | DIPUTUSKAN, belum diterapkan/diuji | "**harga eceran diketik manual**, bukan wajib dihitung proporsional dari harga lusin/gross … Jumlah fisik 7 buah harus tetap tepat 7 … tidak menetapkan aturan pembulatan baru" (M:1066-1071) |
| 7 PCS = accessory | owner clarification quoted | "bro 7 pcs itu maksudny aksesoris kan?" (M:1023); "7 PCS adalah aksesori." (M:44, M:908) |
| ALL initial-data import scope | recorded as decided, owner words NOT quoted | "Scope impor yang sudah disetujui adalah **ALL data awal**, sesuai keputusan owner di repo … Jangan mengulang pertanyaan memilih scope." (M:1024-1025); "ALL impor tetap merupakan kewajiban" (M:138) |
| Draft editable until finalize; latest content under lock; control totals not posted | decided | "Draft boleh diedit sampai disahkan. Finalisasi wajib memakai isi terakhir di bawah lock, memeriksa rincian melawan total, dan tidak menggandakan stok atau uang." (M:1025-1026; M:43-44) |
| Pocket fabric (kain kantong) universal: warehouse stock only, no product HPP | decided | "Owner meminta tahap ringan untuk mengurangi stok saja, tanpa HPP celana." (M:555-556; M:45-47) |
| Pocket-fabric period allocation | decided, owner words quoted | "Owner mengizinkan pembagian per periode melalui “ya gas lah tanggung ye”." (M:466); denominator = all SELESAI_DIJAHIT incl. Afui (M:470) |
| Principles | decided | "**current latest-corrected data wins** dan **filed snapshot tidak ditimpa** sudah ada; tidak perlu ditanyakan ulang." (M:1187-1189) |
| Laundry items already clear | decided | "master per vendor; paket atau komponen; proses dapat diketahui walaupun harga belum; invoice pending berbeda dari harga unknown; SKU opsional; quantity/biaya tidak digandakan; snapshot posted lama tidak ditimpa" (M:4479-4480; M:1425-1427) |
| Afui special policy | decided (names of 3 free categories NOT) | "Afui khusus tanpa absensi, komisi lebih tinggi dan tiga kategori aksesori gratis. **Nama tiga kategori gratis belum memiliki sumber yang pasti**" (M:283; M:214) |
| Sequencing | decided by review under mandate | "tutup keluarga masalah pada fondasi CP6 sebelum mengunci CP6; kerjakan perubahan aksesori/laundry sebagai gelombang tersendiri sebelum audit final gabungan yang direkomendasikan; bangun planner, Business Report dan UX32 pada CP7" (M:1624) |
| Mandates (verbatim) | — | "bikin yang baru aja" (M:3); "yaudah baca handoff lu sendiri, lakukan" (M:1232); "lakuinnnn wjkwkkw" (M:802); "now what?" (M:618 in P / M:676); "lanjutt kenapa stop" (M:738); "lanjut" (M:605) |

### 3b. Decisions explicitly PENDING in the contract
| ID | Quote |
|---|---|
| ERP-DEC02 | "Tiga kategori gratis Special serta tarif aksesori future yang belum ditetapkan — Jangan mengambil kesimpulan dari nama Afui atau fixture demo" (M:4462) |
| ERP-DEC03 | Two states: "MASIH PERLU PENJELASAN CAKUPAN … Owner meminta penjelasan istilah tersebut, belum memilih jenis data impor." (M:1072-1078) vs newer layer "Scope impor yang sudah disetujui adalah ALL data awal" (M:1024). R1.5: "Menganggap semua CSV N/A atau memindahkannya ke CP7" is forbidden (M:1752). |
| ERP-DEC04 | "Volume operator/data, sasaran pemulihan, retensi backup dan go-live" (M:4464) |
| ACC-DEC01, 03, 04, 05, 06, 07 | M:4454, M:4456-4460; "Tarif eceran baru, recovery value, kapitalisasi, credit/refund setelah settlement, aturan pembulatan baru" held (M:1753) |
| LAU-DEC01–06 | M:4472-4477; held: "Tarif vendor nyata, dasar tagihan yang belum disetujui, akun/variance, izin sales/close dengan biaya unknown" (M:1754) |
| AUD-G07 scope | "Tutup role/akses yang terkait scope final" (M:1407) |
| CR-in-final-candidate | "scope kandidat direvisi owner secara eksplisit" required if CR is not complete (M:1756) — no such statement in contract |

### 3c. Decisions WRITER-QUOTED in the candidate but ABSENT from all three contract files (DECISION_MISSING_IN_CONTRACT)
Grep of the three contract files returned 0 hits for each of: `Geser tanggal`, `G-01`, `max(tanggal`, `hosted-faithful`, `OUT_OF_NOWHERE`, `T1_FAMILY|T2_|T3_`, `delapan kasus AS`, `tanggal fisik potong`, decisions `1C`/`2A`, `owner decision A+B`.
- "owner decision A+B" (T1 family probes then one T2 regression; T3 = release evidence) — cand `.github/workflows/cp6-t2-regression.yml:17-18`, `cp6-aw-t1-probe.yml:22-23`, `scripts/cp6_t2_regression.py:3`.
- "Owner decision G-01 (23 Sep 2026), option (b): align the test chain with hosted Enteng" — `scripts/cp6_t3_release_package.py:4`, `scripts/cp6_g01_align.py:2`; T3 "stays HOLD until every G-01 difference is explained and the AO-AV install passes" — `cp6-t3-release-package.yml:35-36`.
- "owner decisions 1C/2A" (found manual BS = NEW_STOCK; GOOD from rework = existing BS stock) — `scripts/cp6_av_definitions.py:5-10`, `scripts/cp6_ax_probe.py:314`.
- "Saya pilih Geser tanggal recost…" — `scripts/cp6_ay_build.py:4`, `scripts/cp6_ay_probe.py:3`.
- "WIP: setujui prinsip max(tanggal ekonomi invoice, tanggal fisik potong)…" — `scripts/cp6_az_build.py:4`, `scripts/cp6_az_probe.py:3`.
- "Owner decision (24 Sep 2026, option 1): an invoice dated before its goods were received is booked on the receipt day" — `scripts/cp6_az_build.py:442`, `scripts/cp6_az_probe.py:601,629,656,689`.
- "Saya setujui penyesuaian oracle hanya untuk delapan kasus AS tersebut" — `scripts/cp6_t2_regression.py:42`; "owner decision 24 Sep (second answer)" — `scripts/cp6_t2_regression.py:451,613`.
- T2 fixture completion "as the owner would" / "owner policy asks" — `cp6-t2-regression.yml:28-33`.
These post-date the contract snapshot (owner decisions in the contract end 22 Sep; recovery 23 Sep). Per M:19-20 and M:69-70 ("Keputusan yang hanya berada di percakapan lain harus diambil dari sumbernya sebelum ditambahkan"), any gate whose expected values depend on them cannot be judged against the contract; they must be labelled DECISION_MISSING_IN_CONTRACT and their oracle status becomes PENDING until the owner text is added to the contract. Note especially that "geser tanggal recost", "max(invoice date, cut date)" and "invoice-before-receipt on receipt day" touch the same family as ERP-DEC01 (tanggal invoice) — a later owner decision may legitimately refine it, but the contract does not contain it, so the 12 HOLD cases' oracle is undefined for the candidate.

---

## 4. What the contract says about tiered gating (T1/T2/T3-style)

The tokens `T1`, `T2`, `T3` (as tiers) occur **zero** times in M, P, A. The tiering is writer-introduced (cand workflows `CP6 A[WXYZ] T1 Family Probe`, `CP6 T2 Combined Regression`, `CP6 T3 Release Package (hosted-faithful baseline)`, `CP6 Candidate CodeQL (T3)`).

Contract's own layering (what each tier must be mapped to):
1. Targeted tests during repair — "tes terarah sepanjang perubahan" (M:2134); "focused checks saat edit, gate setelah stabil" (M:1213); "Jangan mengulangi500 tes untuk setiap satu edit." (M:1440); "reproduksi baseline → unit/helper → integration native → Auth/RPC → DOM/browser → concurrency/refusal/restore yang relevan → review independen exact SHA" (M:4321).
2. One affected acceptance gate per stable family — "Setelah **satu keluarga stabil**, jalankan satu affected acceptance gate." (M:4391); "satu gate keluarga UI/integrasi setelah stabil" (M:2134).
3. Combined business/integration gate on the frozen candidate + independent audit + owner acceptance — M:1418-1420, M:1693, M:1764, M:5337-5340 ("Gelombang 4 — satu gate gabungan dan audit independen … Status CP6 keseluruhan tetap mengacu seluruh blocker CP6, bukan hanya fitur aksesori").
4. Big historical matrix — only when invalidated (M:4391, M:1766, M:6661); "Kabari owner dengan alasan/cakupan sebelum gate besar" (M:3532).

Regression: the contract never uses "regresi" as a gate name; "regresi" appears only as a progress criterion: "Ukuran kemajuan adalah kebenaran, tidak munculnya regresi, dan berkurangnya kekurangan bukti." (M:4444).

"Rilis"/"paket"/"release": the contract's "paket" is the permanent migration package (GATE-10) whose acceptance is writer-level only; "release" of the demo (PR27) is explicitly not backend evidence ("Jangan memakai release demo sebagai bukti backend CP6 telah dirilis", M:1681). No "release gate" exists for CP6; release/go-live is CP8 + owner (M:4527, M:6472 "production_go tetap false").

Rollback: pre-use only, atomic refusal after use (M:206); refusal evidence required (M:208); "Rollback disposable per patch tidak menggantikan rebaseline final CP7.5 atau pemulihan operasional CP7C/CP8." (M:1671).

Acceptance: writer PASS ≠ independent PASS ≠ owner acceptance (M:1467-1468, M:4500, M:229). "Nama artifact, workflow SUCCESS untuk routing, dan CodeQL tidak menggantikan report per-ID." (M:1254-1255).

Implication for the writer's T3 "hosted-faithful baseline": the contract requires reproduction on an exact-schema disposable that pins the AC→AN(→AQ) catalog (M:462, M:6606) and forbids loosening the AC source gate (M:136, M:223). A chain that "stops after AB" because "the frozen path refuses at AC" and installs the package "from there" (writer comment, `cp6-t3-release-package.yml:36-39`) is, on its face, a different baseline than the contract's; whether it is a bypass of `AC_ONLY_EXACT_SUCCESSOR_REPAIR_ALLOWED` must be verified by the runtime agents (F-02).

---

## 5. CP6/CP7 boundary per the Addendum (and the Master lines that bind it)

- A:7 "**Gate diwariskan:** CP6 HOLD; `production_go:false`. Status ini dibawa dari handoff V2, bukan pemeriksaan runtime baru. CP7 tetap menunggu gate dan mandat penerus yang sah."
- A:16 "Semua audit, aksesori, laundry, reminder, tanggal dan gate terdahulu tetap berlaku … Dokumentasi baru tidak mengesahkan AL atau menutup temuan CP6."
- A:437 "Kontrak tanggal AP/GRNI/HPP yang masih pending pada CP6/V1 tetap pending. Business Report tidak boleh memilih sendiri kebijakan tanggal untuk menutupi ketidaksesuaian laporan."
- A:510-522 BR.10 roadmap: "Pertahankan urutan CP7 → CP7.5 → CP7C → CP8 … bukan membuat checkpoint pengganti"; wave "1 — Fondasi | Closure CP6 yang relevan, kontrak tanggal/unknown, snapshot/metrics mapping | Tidak menutupi blocker dengan report cantik" (A:515); wave "7 — CP8/penerimaan | … Writer tidak self-certify independent PASS atau production GO" (A:521).
- A:561 BR-T30: "kontrakCP6 unresolved tidak dipilihdiamdiam".
- A:589 writer checkpoint line "CP6/AL & gate: status asal dan delta terbukti".
- A:603 "Main/production tetap mengikuti gate/otorisasi owner, bukan keputusan renderer laporan."
- Master binding: "Business Report tidak menggantikan perbaikan laporan keuangan dasar pada CP6." (M:1666); "bug report backend CP6 tetap AUD-B04/S06" (M:1734); "Sesudah CP6 sah dan owner memberi perintah CP7" (M:1694); AUD-G09 PLANNED_NOT_IMPLEMENTED (M:1731), G10 CP7.5, G11 CP7C, G12 CP8 (M:1732-1736).

Boundary statement: CP6 = correctness of the transactional core (opening/import ALL, stock, HPP, journal, basic financial reports as-of/confidence, roles, recovery, migration/rollback) on a frozen candidate with independent acceptance. CP7 = planner/BR/UX32/per-SKU/Tanya AI V1 consumers; CP7C scheduler/delivery; CP7.5 rebaseline; CP8 cutover/go-live. Nothing in the Addendum adds a CP6 gate; it forbids using CP7 reporting to hide CP6 date/report blockers.

---

## 6. Findings (contract lens)

- F-01 [P1, CONTRACT_GAP] Writer-quoted owner decisions of 23–24 Sep (A+B tiering, G-01 option (b), 1C/2A, "Geser tanggal recost", max(invoice date, cut date), invoice-before-receipt option 1, AS oracle adjustment for 8 cases) are absent from all three contract files → DECISION_MISSING_IN_CONTRACT. Gates whose expected values depend on them (notably GATE-05 date family and any T2 "approved oracle" cases) are unverifiable against the contract. Evidence: cand `scripts/cp6_ay_build.py:4`, `scripts/cp6_az_build.py:4,442`, `scripts/cp6_t2_regression.py:42,451,613`, `scripts/cp6_t3_release_package.py:4`, `.github/workflows/cp6-t2-regression.yml:17-33`; contract grep counts 0 (see §3c).
- F-02 [P1, CONTRACT_GAP/TOOLING — to be confirmed by runtime agents] T3 chain declared to stop after AB because the frozen path refuses at AC on the "hosted-faithful baseline" and to install the release package from there (`cp6-t3-release-package.yml:36-39`, `cp6-t3-aligned-install.yml:3-4,13-15`). Contract: AC source gate "tidak dilonggarkan" (M:136, M:223); reproduction on exact-schema disposable, not hosted endpoints (M:6606); "source-routing guard tetap harus menerima delta secara eksplisit" (M:6661). If the refusal at AC is worked around rather than explicitly accepted as a reviewed delta, this is a gate bypass.
- F-03 [P1, CONTRACT_GAP] ERP-DEC03 carries two states in the contract: undecided (M:1072-1078, R4 addendum) vs decided "ALL … sesuai keputusan owner di repo" (M:1024, newer layer) with no owner utterance quoted. Under M:19-20 the newer instruction governs but the conflict must be recorded; the ALL obligation (M:138) is the operative gate, and the owner's words remain unverifiable from the contract.
- F-04 [P2, CONTRACT_GAP] The contract does not state whether the legacy Full-Schema/Final Boundary workflows must themselves turn green on the final candidate or whether a successor-scoped equivalent suffices; it only forbids loosening/relabeling them (M:136, M:223, M:957) and demands a successor-scoped global gate (M:138, M:229). Auditors must therefore report both: legacy status verbatim and the successor gate's explicit-delta acceptance.
- F-05 [P2, PROTOCOL] Contract's tested source is 5ae73305 / tree c34f0df5 (M:33-34); the candidate is 9add57e / 5d5f833b. Every PASS figure in the contract is historical for the candidate until re-bound (M:1254, M:1624); labels per M:4393 are mandatory.
- F-06 [INFO, CONTRACT_GAP] Security advisors: "109 temuan baseline belum dinyatakan selesai" (M:112) but no gate, threshold or owner decision is defined. Cannot be used to block or to pass.
- F-07 [P2, CONTRACT_GAP] Which CR (accessory/laundry) items are inside the final CP6 candidate is not fixed by an owner statement; the contract requires explicit owner scope revision if CR acceptance is incomplete (M:1755-1756) and forbids deferring old findings via CR placement (M:1697, M:4422). Accessory retail and pocket-fabric are demonstrably in the branch (M:238-323, M:436-517); laundry vendor/package/pending remains APPROVED_NOT_IMPLEMENTED (M:4488).
- F-08 [P1, CONTRACT_GAP → acceptance bar] As of the contract's newest layer, four items are explicitly still required before CP6 acceptance: opening-overlap on all legacy paths, successor-scoped combined gate, independent audit, owner acceptance (M:37, M:138). Any claim of CP6 acceptance for 9add57e must show all four with evidence bound to 9add57e; the contract offers no shortcut.
- F-09 [INFO, CONTRACT_GAP] The contract defines no format or artifact for "acceptance owner"/CP6_LOCK_READY (only that it must be "sah" and precede CP7: M:1218-1219, M:1419-1420). Silence noted; do not invent one.

---

## 7. Not examined
- Master 1795-4316 (V3.2 body: UX32, BR, CP7 rev3, laundry/accessory design, reminder) beyond targeted greps; Master 4531-7236 (V1/V2/audit archives) beyond greps and the read of 5246-5345 and 6596-6670; Perubahan 90-996 (headings only, confirmed as a copy of Master checkpoints); Addendum 61-507 except 430-440.
- The original 33-AUD register texts (expected/actual per ID) beyond the R1.4 map.
- Any product code, SQL bodies, script internals (only docstring/comment lines matched by grep), CI run logs, artifacts, docs/ (forbidden), base/harness/cand25fa worktree contents beyond workflow file names.
- Whether the writer-quoted 23–24 Sep owner decisions exist elsewhere (e.g. in repo docs) — forbidden in phase 1; must be reconciled in phase 2.

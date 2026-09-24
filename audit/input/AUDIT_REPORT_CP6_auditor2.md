# Audit independen CP6 — kandidat 9add57e

Tanggal: 24 September 2026. **Rekomendasi: HOLD. `production_go: false`.** Keputusan penerimaan tetap milik owner.

Kandidat dapat dipasang pada runtime disposable yang diuji. Namun, audit membuktikan kesalahan interpretasi waktu bisnis pada tiga halaman aktif, menemukan kelemahan agregasi hasil skenario, dan mengonfirmasi bahwa rollback paket final belum dikualifikasi. Tiga risiko tambahan mempunyai dukungan source tetapi belum direproduksi native. Karena cakupan native independen belum lengkap, laporan ini tidak menyatakan seluruh CP6 telah lulus atau seluruh defect telah ditemukan.

## 1. Identitas, kontrak, dan independensi

| Komponen | Identitas |
|---|---|
| Repository | `Hanjay6688/-erp-garment-ux` |
| Kandidat | `9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc` |
| Tree kandidat | `5d5f833b2e75e23184c643d5ac469781f1c3ce5e` |
| Baseline pembanding | `ca7f09556397801c50a2277bdb65b1bf019f9a05` |
| Lock fase 1 | `2026-09-24T18:42:13.921237+00:00` |
| SHA-256 temuan fase 1 | `cbca0c6cb3150f0005bbea877d1a6b0371afa6103d9907c21899b1e235e46156` |
| SHA-256 manifest fase 1 | `50ba9228c863d4c483404bd425d8d64aac3073c3cd6726e35d9ca840d653438a` |

Rujukan kontrak menggunakan nomor baris berkas yang diberikan owner:

- **M**: `input/kontrak/ERP_V3_2_Master_Pulih_20260923.md`, SHA-256 `f21ac70360915a1f1021b42a3918e862ca7d11cf88c1b90c5627b4490c69af07`.
- **P**: `input/kontrak/ERP_V3_2_Perubahan_Pulih_20260923.md`, SHA-256 `92966cd6ed27e64123be6c52e2263bfbdb3db91c97f2e441c3bdc98589397676`.
- **BR**: `input/kontrak/ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md`, SHA-256 `4566ab6f1c8e53bc21c70c0c777f780b526305815e04d5913a5c858dfaa85886`, hanya untuk batas tahap.

Gate dan oracle diturunkan dari tiga kontrak tersebut. Konteks garmen dipakai sebagai latar. Komentar kode, assertions writer, narasi audit lama di dalam kontrak, dan klaim persetujuan dalam handoff writer bukan oracle audit ini. Daftar rinci beserta contoh hitungan independen disimpan di `work/contract_gate_register.md`.

Fase 1 memakai sparse checkout yang mengecualikan `docs/`. Tidak ada isi `docs/cp6-*.md` atau `docs/evidence/` dibaca root/agen sebelum lock. Fase 2 baru membuka handoff writer dan enam berkas yang dicatat di `phase2/READ_LOG.json`. Berkas lock tidak diubah sesudah itu.

**Batas kebutaan yang diungkapkan:** sesi sempat memuat memory audit sebelumnya; memory itu dikecualikan sebagai bukti/oracle dan agen keluarga dimulai tanpa percakapan induk. Nama dokumen terlarang terlihat dalam inventory; satu snippet judul commit nonbisnis terlihat di UI Actions. User kemudian membocorkan temuan auditor lain. Duplicate-ID sudah direproduksi sebelum bocoran; advisory-lock dan second-connection tetap diperlakukan sebagai lead eksternal. Audit ini tidak mengklaim kebutaan sempurna terhadap informasi eksternal tersebut.

Tidak ada kode produk yang diubah, commit/push audit yang dibuat, SQL ke hosted/legacy, perubahan main/kompetisi/deployment, atau pesan ke pihak lain. Aturan branch/progress yang ditempel user telah dijelaskan sebagai milik auditor lain; tidak ada klaim bahwa kami melaksanakan push mereka. Pemeriksaan akhir worktree produk bersih dan HEAD/tree tetap identik.

## 2. Putusan per gate

ID C6-01–10 adalah pengelompokan audit, bukan nama gate baru dalam kontrak. **ACCEPT sub-scope berarti hanya operasi yang disebut; bukan ACCEPT seluruh gate.**

| Gate | Putusan | Alasan | Kontrak |
|---|---|---|---|
| C6-01 identitas dan integritas bukti | **HOLD** | SHA/tree dan rerun terikat. R01 merusak agregat bila ID duplikat; T2 masih DISPOSITION_REQUIRED dan independent residual scenarios belum native. | M:1624–1626,1693,1762–1767,4391–4393,4521–4525 |
| C6-02 atomicity, immutable facts, exact state | **UNVERIFIED** | U02/U03 belum native; tidak ada bukti independen lengkap untuk semua posting/correction/reversal. | M:3816–3826,5048–5052 |
| C6-03 recovery, input, unknown, selector | **HOLD** | F01 terbukti pada serialisasi input. U01 menunjukkan ekor selector tanpa akses. Recovery helper controls hanya mencakup fungsi lokal. | M:1678–1679,1691,3817–3820,3825–3826,3939 |
| C6-04 ALL initial import | **UNVERIFIED** | ALL berarti keluarga bisnis, bukan jumlah template. Final draft/control/source dan semua dokumen terbuka belum dikualifikasi end-to-end independen. | M:44–45,1024–1025,1691,359–365,749–755,829–843,934–938; P:966–967 |
| C6-05 tanggal, recost, HPP, jurnal, laporan bertanggal | **HOLD** | F01 melanggar waktu bisnis WIB; U03 memerlukan native ledger check. Pergeseran hasil tanggal T2 belum cukup untuk acceptance finansial independen. | M:1022,1059–1065,1666,1691,375,377,837,3816,3820,3825 |
| C6-06 produksi serta AP/AR | **UNVERIFIED** | U02 perlu historical-capacity proof. Full partial/rework/payroll/advance/conservation belum ditutup. | M:3822–3824,359–379,749–757,629–648 |
| C6-07 aksesori/pocket dalam scope | **UNVERIFIED** | Exact PCS/manual-price controls lokal berhasil; full posting/allocation/reversal belum diuji independen. Scope CR yang lebih luas belum diputuskan dalam bahan audit. | M:44–48,1023,466–472,495,557–561,3900–3902,3951,5192–5199 |
| C6-08 Auth, hak akses, UI tersambung | **UNVERIFIED** | Active route/facade ditelusuri. Browser writer hanya10 kasus; tidak menggantikan real JWT/location/action matrix independen. | M:1691,4486,5046–5052,5209,5213–5224 |
| C6-09 concurrency dan stale state | **UNVERIFIED** | Belum menjalankan own two-session schedules untuk race source/capacity/draft/close. | M:5048–5052,4165,4486,1025,751–755 |
| C6-10 install, compatibility, rollback/refusal, cleanup | **HOLD** | Install dan disposable restore diterima dalam scope. R02: paket final belum punya jalur rollback/refusal yang dikualifikasi. | M:3826,4306–4314,5192–5209,1767,4486 |

Planner, Business Report consumer, dan remaining UI CP7 tidak dijadikan blocker CP6 baru; rebaseline CP7.5, autonomous CP7C, production CP8 tetap tahap terpisah (M:1666–1672,1694–1695; BR:510–521). CR aksesori/laundry yang diperluas tidak otomatis menjadi seluruh scope CP6 (M:1697,1757). Sebaliknya, keputusan eksplisit ALL import,7PCS/manual price,invoice-date economics,dan pocket-period allocation tetap berlaku.

## 3. Bukti eksekusi

Label yang dipakai:

- `INDEPENDENT_NATIVE_RERUN`: auditor memicu ulang job native pada exact candidate dan membaca raw log. Assertions bawaan writer tetap tidak otomatis menjadi oracle independen.
- `INDEPENDENT_SOURCE_REVIEW`: penelusuran current effective source dan kontrak.
- `INDEPENDENT_ARTIFACT_CHECK`: hashes, exact-source execution, arithmetic, atau actual AST dengan doubles I/O yang dinyatakan; bukan PostgreSQL native.
- `REUSED_EVIDENCE`: arsip writer yang baru dibaca pada fase 2.

### Rerun native yang benar-benar dilakukan

| Sub-job | Run / attempt / job | Hasil dan batas |
|---|---|---|
| T3 install/restore | [36037876338](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36037876338) /2 /[107772603343](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36037876338/job/107772603343) | 24/24 paket terpasang; family verification lulus. Restore RESTORED_SAME_MEANING:318 tables/1647 rows,5 checks true. Primary unchanged,Auth0→0. Raw log1301–1330. |
| T2 regression | [36037873682](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36037873682) /2 /[107772639059](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36037873682/job/107772639059) | Job success, tetapi DISPOSITION_REQUIRED; rincian di bawah. Raw log2198–2199 mengikat head,IDs,counts,HOLD,primary unchanged,clone0. |
| CodeQL JS/TS | [36037878419](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36037878419) /2 /[107772676223](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36037878419/job/107772676223) | Log2415:PASS,language javascript-typescript,result_count0. Gate memeriksa SARIF,invocation,rules,dan SHA. Tiga bahasa lain tidak diulang auditor; SQL/business semantics di luar hasil ini. |

Ini rerun **job terpilih**, bukan klaim bahwa semua job pada setiap workflow diulang auditor. Raw logs utuh berada di `work/native/job_<job_id>.log`.

T3 restore mencatat `pg_restore` exit1 akibat19 error pg_cron yang diklasifikasi; source cron jobs0. Perbandingan mempertahankan catatan perbedaan pg_cron dan canonical IN-list parsing, bukan menyebut dump byte-identical. Advisor menambah54 INFO `rls_enabled_no_policy`. Semua54 table ditelusuri ke ENABLE RLS dan explicit REVOKE ALL dari public/anon/authenticated/service_role; tidak ditemukan later explicit grant dalam urutan release. INFO tersebut tidak membuktikan exposure, dan review ACL ini tidak membuktikan semua SECURITY DEFINER/public facades aman.

Artifact check membuktikan24 hash release dan40 function bodies dev/release cocok. Ini berbeda dari membandingkan seluruh40 definition pada installed T1 catalog: native verifier T1 memeriksa subset tertentu. Whole T1–T3 runtime equivalence tetap UNVERIFIED.

### T2: hasil beku dipertahankan

| Kelompok | Hasil raw rerun | Disposisi audit |
|---|---|---|
| BUSINESS230 |179 PASS +39 CONTROL_PASS +12 DATE_POLICY_REVIEW_REQUIRED |12 tetap HOLD; hasil writer assertion, bukan blanket independent business acceptance. |
| IMPORTS31 |31 PASS |Observed rerun result; semua ALL-import paths belum terbukti. |
| VALUES65 |65 PASS |Observed rerun result; U03 belum tercakup oleh own native fixture. |
| NEW_CASES34 |25 PASS +8 COUNTEREXAMPLE +1 INCOMPLETE |8 DATE dan ADJUSTMENT_DATE berubah dari expected PASS; identitas/order tetap. |
| AO_TRIAL12 |8 PASS +4 INCOMPLETE |Empat invoice assertions gagal pada tanggal; bukan installation SQL failure. |
| Kalender12 crosschecks |12 COUNTEREXAMPLE |Tidak dihitung ulang sebagai12bug tambahan; historical12 HOLD tetap. |
| Writer approved-oracle checks |8 DATE MATCH;5 additional MATCH;12 calendar MATCH |Terpisah dari frozen status. Bukan pengganti COUNTEREXAMPLE/INCOMPLETE/HOLD. |

326 kasus awal tetap314 PASS/CONTROL +12 HOLD. **Jangan menjumlahkan checks tambahan menjadi angka acceptance baru.** `phase2/T2_FULL_CASE_LEDGER.json` menyimpan status/ID/baris semua records per kasus yang dicetak job; `work/native/t2_parsed.json` menyimpan detail mismatch.

Claimed Owner24Sep policy ada di log dan handoff writer, tetapi tidak menjadi otoritas keempat. Secara independen, invoice pada D dan pemotongan/FG/penjualan pada D+1 tidak membenarkan penciptaan WIP/COGS sebelum barang memasuki tahap tersebut. Oleh sebab itu, delapan pergeseran tanggal bukan otomatis delapan defect produk. Acceptance dated valuation lengkap masih **UNVERIFIED**, dengan frozen hasil tetap utuh. `ADJUSTMENT_DATE` khususnya membutuhkan pembuktian semua pembaca dan nilai, bukan hanya assertion pertama yang lolos setelah tanggal diganti.

### Skenario independen yang belum native

Sesi tidak memiliki callable workflow-dispatch POST, GH CLI/token, Docker, atau PostgreSQL lokal. UI workflow non-main tidak menyediakan tombol dispatch. Tool yang tersedia mendukung rerun existing job, sehingga tiga job di atas diulang. Delapan SQL cases berikut disimpan dan hanya diperiksa sintaksnya; **NOT_RUN, tanpa run/job ID**:

| Berkas | Isi | SHA-256 |
|---|---|---|
| `work/stock_import_scenario.py` |4 kasus:optional WIP identity,historical reversal capacity,exact replay/refusal,prepared draft |`ff92e8d973ebb75c05ba8ac6b47da96565c9b50760c91b247f331a765d18df81` |
| `work/money_dates_scenario.py` |4 kasus:direct/invoice correction × harga naik/turun |`cfa1157b7ea39e6f5162d85a540ed5e22c30d8fef9ddfe840b5a9bf2f631d9ef` |

Helper writer hanya dipakai untuk transport/setup. Unexpected error atau product refusal pada valid-case berarti INCOMPLETE. Kasus replay SI03 mencocokkan pesan penolakan persis `client_request_id was already used with a different payload`. Tidak ada penolakan arbitrer yang dihitung PASS.

## 4. Temuan

Tidak ada P0 yang dibuktikan. P1/P2 di bawah adalah prioritas audit, bukan klaim dampak produksi yang telah terjadi.

### F01 — P1, CONFIRMED lokal: waktu bisnis berubah menurut zona perangkat

**Oracle:** M:3820 menetapkan waktu bisnis WIB terpisah dari waktu perangkat; M:1691 memasukkan closure alur terkait. Input `2026-09-20T00:30` harus menjadi `2026-09-19T17:30:00.000Z` pada semua perangkat.

**Reproduksi:** jalankan `node work/frontend/frontend_probe.mjs` dengan kandidat berada di `repo/`. Probe mengambil exact serialization expressions dari halaman aktif, menjalankannya pada Node dengan TZ Jakarta,UTC,Kiritimati,dan membandingkan expected independen. Exit1 dipertahankan karena ada kegagalan kontrak. Total34 checks:28 PASS,6 FAIL.

| Device timezone | Actual pada Cutting/Pickup/BS | Expected | Hasil |
|---|---|---|---|
| Asia/Jakarta |2026-09-19T17:30Z |2026-09-19T17:30Z |PASS control |
| UTC |2026-09-20T00:30Z |2026-09-19T17:30Z |7 jam terlambat |
| Pacific/Kiritimati |2026-09-19T10:30Z |2026-09-19T17:30Z |7 jam lebih awal; hari WIB menjadi19 Sep |

**Source final:** `src/App.tsx:607,609,665` mengaktifkan ketiga route. `src/ConnectedCuttingPage.tsx:272`, `src/ConnectedPickupPage.tsx:200`, dan `src/ConnectedBsResolutionPage.tsx:40` memakai `new Date(value).toISOString()`; BS memakai helper itu pada87,143,231,275,288,305. Shared mutation hook112–127 tidak mengubah interpretasinya.

Facade `supabase/migrations/20260903022604_erp_v2_6_18_cutting_persistence_pickup_wip.sql:1316–1333` meneruskan payload; private parsing656/1009 menyimpan timestamp tersebut pada756–764/1110–1118. BS facade `20260903070932_erp_v2_6_19_cp5_bs_resolution_recovery.sql:1127–1136` juga meneruskan payload. Tidak ditemukan later replacement yang dapat memulihkan intended wall time yang sudah hilang.

Adversarial control `src/cp6BusinessTime.ts:16–25`, yang dipakai Laundry/QC, menghasilkan expected WIB. Default/reload dapat round-trip pada satu perangkat, tetapi tidak memperbaiki input WIB manual di perangkat zona lain.

**Bukti:** INDEPENDENT_SOURCE_REVIEW + INDEPENDENT_ARTIFACT_CHECK. Probe SHA `b18f0a83f1b43b5518a4585b99faa9a3f7188f0d5e0be98806a6cc50783e2073`; output SHA `b9d0c2cb41f68693793719c9285538fe6df432a6329bc5454493556b82e683ce`. Reviewer kedua mereproduksi variasi rollover harinya. **Yang terbukti adalah payload salah; actual posted ledger corruption belum diuji native.**

### U01 — P2, UNVERIFIED native: selector BS kehilangan source setelah100 baris

**Oracle:** eligible source pada flow yang diterima harus dapat dipilih (M:1691,3826,4486).

**Reproduksi yang diperlukan:** siapkan satu laundry delivery lama yang masih claimable, lalu100 delivery lebih baru yang selesai/claimable 0; buka form klaim. Source lama harus tetap tersedia melalui daftar/pencarian/paging.

Private reader `supabase/migrations/20260903070932_erp_v2_6_19_cp5_bs_resolution_recovery.sql:768–770` memasukkan SENT/PARTIAL_RETURN/RETURNED/CLOSED, lalu LIMIT100. Limit lain ada pada799/828 untuk receipt/settled claims. Public successor `20260904012525_erp_v2_6_19b_cp5_reliability_closure.sql:682–745` hanya mengganti `rows`, bukan `lookups`. UI `ConnectedBsResolutionPage.tsx:101–110,124` menyaring claimable sesudah cap; case search/pagination tidak mengubah lookup. Native101-source fixture belum dijalankan.

**Bukti:** INDEPENDENT_SOURCE_REVIEW. Cap dan tidak adanya continuation terkonfirmasi di source; akibat pada fixture end-to-end masih UNVERIFIED. Detail di `work/frontend_findings.md`.

### U02 — P1, UNVERIFIED native: completion ulang setelah reversal dapat melewati kapasitas WIP historis

**Oracle:** linked reversal tidak menghapus histori fisik; setiap prefix WIP harus sah (M:369–371,3816,3820–3823).

**Reproduksi:** import8 PCS WIP SEWING bernilai 40 pada D−8; complete8 pada D−3; reverse pada D; complete lagi8 dengan tanggal D−1. Expected: penolakan atomik atau model yang menjaga prefix nonnegatif. Source memprediksi WIP −8 antara D−1 dan D, meskipun saldo kini nonnegatif.

Final `supabase/dev/cp6_az_t1_family.sql:817–820` menghitung remaining dengan mengecualikan seluruh reversed outputs tanpa tanggal. Reversal837–845 menambahkan inverse bertanggal aktual; batas completion850–853 hanya cutover/today. FG timeline guard tidak membuktikan prefix WIP. Reviewer kedua memeriksa linked-event interpretation dan source guards.

**Bukti:** INDEPENDENT_SOURCE_REVIEW; SI02 dalam scenario stok NOT_RUN. Unexpected SQL refusal harus INCOMPLETE sampai reason sesuai kontrak dibuktikan, bukan PASS rekaan. Detail `work/stock_import_findings.md` dan `work/adversarial_findings.md`.

### U03 — P2, UNVERIFIED native: rounded delta berbeda dari delta nilai jurnal yang telah dibulatkan

**Oracle:** satu unit diterima dan seluruhnya dikonsumsi meninggalkan raw qty/value 0. Perubahan harga10.005→10.014 membulatkan kedua nilai receipt menjadi10.01; sole consumption WIP harus tetap10.01. Tidak ada split allocation atau kebijakan remainder baru (M:1022,1059–1065,1664,3816,3818,3820).

**Reproduksi:** receipt FINAL qty 1 @10.005 pada D−4; cutting memakai seluruhnya D−3; direct correction ke10.014 D−2; baca raw quantity dan daily GL. Ulangi arah turun dan jalur estimated receipt→invoice.

| Arah | Expected raw/WIP/AP | Prediksi final source |
|---|---|---|
|10.005→10.014 |0.00 /10.01 /10.01 |−0.01 /10.02 /10.01 |
|10.014→10.005 |0.00 /10.01 /10.01 |+0.01 /10.00 /10.01 |

Source di `supabase/release/cp6-t3/`:

1. `20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql:3437–3458` membulatkan nilai issue awal ke cents.
2. `20260924010300_erp_v2_6_20az_cp6_material_recost_dated_from_movement.sql:256–279` membulatkan `qty_signed*(current_cost-original_cost)`. Selisih0.009 menjadi0.01.
3. `20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql:3292–3314` dan AC:1327–1347 memakai delta endpoint receipt yang telah dibulatkan, yaitu 0.00; tidak mengompensasi transfer recost 0.01 ini.
4. Direct correction final AZ:1213–1275 menerima biaya enam desimal dalam path yang diperiksa. Reviewer kedua memeriksa precision fields dan tidak menemukan two-decimal refusal yang membatalkan fixture.

**Bukti:** INDEPENDENT_SOURCE_REVIEW + INDEPENDENT_ARTIFACT_CHECK untuk Decimal arithmetic. Empat native scenarios NOT_RUN; compensating downstream effect masih mungkin membantah prediksi. Tidak mengklaim false READY: detector negative inventory dapat memblokir readiness tanpa memperbaiki selisih nilai.

### R01 — P2, CONFIRMED control flow: ID duplikat menimpa kegagalan di hasil agregat

**Oracle:** hasil per kasus harus tetap dapat ditelusuri; error tidak boleh menghilang dari final per-case evidence (M:1767,4391–4393,4521).

`scripts/cp6_au_r1_probe.py:337–348` menyimpan `report['cases'][key]` tanpa menolak ID duplikat;354–356 menghitung hanya entries yang tersisa. Driver `scripts/cp6_auditor_scenario.py:64–76` memberi RUN_COMPLETE bila group bukan INCOMPLETE.

| Input | Raw log | Artifact akhir |
|---|---|---|
|A error,B PASS |INCOMPLETE,PASS |INCOMPLETE;2 kasus — control benar |
|A error,A PASS |INCOMPLETE,PASS |PASS 1;RUN_COMPLETE — kegagalan tertimpa |
|A COUNTEREXAMPLE,A PASS |COUNTEREXAMPLE,PASS |PASS 1;RUN_COMPLETE |

Repro: `python3 work/runtime_release_repro.py`; reviewer kedua menjalankan `work/adversarial_runtime_repro.py`. Keduanya memakai actual unchanged AST dengan inert I/O doubles. Label INDEPENDENT_SOURCE_REVIEW + INDEPENDENT_ARTIFACT_CHECK; **bukan native SQL**. Repro SHA `3da1e4868c318b8ff28e2fad1ace345312bd67d390735e490772090c307cda54`.

Raw log dan planned IDs masih mengungkap duplikasi; tidak dibuktikan bahwa current T2 kehilangan kasus. Unknown status juga dapat fall through ke PASS, sedangkan missing status key menimbulkan INCOMPLETE. Legitimate COUNTEREXAMPLE→RUN_COMPLETE memang diizinkan handoff dan bukan defect. Sebelum memakai agregat, validasi unique IDs,exact planned/final count,dan status vocabulary.

### R02 — P2, gap terkonfirmasi: rollback paket final belum terkualifikasi

**Oracle:** patch/install/runtime harus terhubung ke rollback atau post-use refusal sebelum mutasi; restore tidak boleh menyamarkan penghapusan fakta (M:3826,4306–4314,5198–5209). Ini bukan tuntutan rebaseline CP7.5.

`supabase/release/cp6-t3/MANIFEST.json:1365–1372` menyatakan rollbacks NOT_TESTED. Builder `scripts/cp6_t3_awx_release.py:220–258` membuat forward SQL/capsule AW..AZ tanpa rollback file. Inventory tidak menemukan rollback AW/AX/AY/AZ final.

Original AC rollback `supabase/rollbacks/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.rollback.sql:10–21` menerima dua hash predecessor; release AC hash `871fb32b1d4a1e7f9aedfef684b0f2c766092732c38552620eb394061f6240d1` tidak cocok. Applier menyimpan whole release SQL sebagai platform statement (`scripts/cp6_t3_release_package.py:211–218,248–252`). Refusal guard adalah proteksi; jangan dilonggarkan agar tampak lolos.

Reproduksi artefak ada di runtime release repro. **Native downgrade/post-use refusal belum diuji.** Fresh restore mengembalikan installed state pada DB lain, bukan release→predecessor. Writer juga mengakui gap ini; tidak dilabel sebagai temuan baru yang mereka sembunyikan. Label INDEPENDENT_SOURCE_REVIEW + INDEPENDENT_ARTIFACT_CHECK.

### Hipotesis yang tidak dipromosikan menjadi defect

- **H01,P2/UNVERIFIED:** opening WIP yang opsional mengikat productA dapat diselesaikan ke productB dengan model/size sama. AR menyimpan optional product,AZ memvalidasi output tetapi tidak membandingkannya. M:359/369 memang mengizinkan WIP sebelum SKU; belum jelas apakah optional label selalu mengikat. Butuh native observation dan interpretasi kontrak; WIP tanpa SKU→SKU pilihan bukan bug.
- **H02,P2/UNVERIFIED:** edit native prepared DRAFT8/40→4/20 dapat meninggalkan production source/control8/40. Normal CSV SAVE_FILE membersihkan stale prepared items, sehingga bukan bug normal path tersebut. Intended native-owner reachability belum terbukti; runner sendiri memberi schema USAGE. SI04 belum native.
- **O01,batas alat:** T3 ALL_STAGES_INSTALLED dapat tetap hijau saat restore/advisor/primary-check bermasalah dalam local AST repro. Final object tetap menyimpan adverse fields dan release_evidence:false. Ini alasan membaca detail, bukan klaim restore aktual gagal.

## 5. Rekonsiliasi fase 2

Handoff `docs/cp6-au-r1-handoff.md` dibaca setelah lock. Tabel lengkap dengan line refs dan setiap artefak ada di `phase2/RECONCILIATION.md` dan READ_LOG. Ringkasan klaim relevan:

| Klaim writer | Disposisi |
|---|---|
|CP6 HOLD,12 HOLD,production_go=false (§27.6) |**CONFIRMED** sebagai status dan sesuai rekomendasi audit. |
|T2 raw counts/status/IDs dan MATCH terpisah (§23.3–23.6,27.5) |**CONFIRMED** oleh fresh native log; tidak mengubah makna acceptance. |
|Claimed Owner24Sep policy dan semua ADJUSTMENT_DATE readers aman (§23.1/23.6) |**UNVERIFIED** sebagai otoritas tambahan dan acceptance end-to-end; tiga kontrak tetap berlaku. |
|24 file install,restore318 tables/1647 rows,advisor54 INFO (§27.5) |**CONFIRMED** dalam scoped fresh rerun dan source ACL review. |
|Browser10 PASS (§27.5) |**UNVERIFIED independen**; archive writer konsisten, hanya REUSED_EVIDENCE. Tidak mencakup F01/U01. |
|CodeQL empat bahasa0 hasil (§27.5) |**CONFIRMED JS/TS** exact-candidate rerun; tiga bahasa lain **UNVERIFIED independen**, arsip208afce reused. |
|Rollback package NOT_TESTED (§22.8) |**CONFIRMED** oleh R02. |
|Savepoint/per-case JSON;RUN_COMPLETE bukan allPASS (§27.4) |**CONFIRMED** untuk mekanisme terbatas; aggregate duplicate-ID loss tetap R01. |
|Tombol UI Run workflow tersedia (§27.4) |**REFUTED** saat audit untuk workflow non-main; owner handoff sudah memperbaiki instruksi menjadi API POST. Bukan defect ERP. |
|AB-01 fixed 29 PASS,AY 8 PASS (§27.1/27.5) |**UNVERIFIED independent business acceptance**; auditor belum mengulang own pocket/AY native family. Writer sendiri tetap RERUN_REQUIRED. |
|Multi-receipt native dan write-state load masih gap (§26.7) |**CONFIRMED** sebagai gap yang mereka catat; audit ini belum menutupnya. |

Bukti terpilih tidak menutup F01,U01,U02,U03,atau R01. Tidak diklaim bahwa audit menelusuri seluruh350 evidence files untuk membuktikan tidak adanya testcase serupa.

Bocoran advisory-lock/second-connection diperiksa hanya setelah lock sebagai source follow-up. Snapshot tidak mencakup `pg_locks`,sequence state,atau seluruh tabel semua skema. Tetapi snapshot **memang** mencakup seluruh ordinary/partitioned ERP tables,platform,auth.users,dan ACL tertentu. Karena itu, klaim umum bahwa second-connection commit ke tabel bisnis ERP pasti tidak terdeteksi tetap **UNVERIFIED**; diperlukan bukti native mengenai tabel,isolation/visibility,waktu commit,dan boundary observations. Audit ini tidak mengklaim menjalankan probe ERP-table tersebut.

## 6. Cakupan yang belum diperiksa dan syarat closure

Belum dikerjakan: delapan own SQL scenarios;101-source selector fixture; browser pada tiga timezone; full role/location/revocation matrix; two-session races untuk shared capacity/draft/finalize/close; seluruh ALL-import families; all recost allocation/readiness/filing chains; exact release rollback/post-use refusal; native multi-receipt; performance data besar; independent full T1–T3 catalog equivalence; fresh hosted parity. Hosted operations memang di luar izin. Archive/SARIF ZIP writer tidak diunduh; raw fresh CodeQL gate log dan source gate diperiksa.

Urutan penutupan yang konkret:

1. Perbaiki F01 melalui writer; verifikasi route payload dan actual business date pada Jakarta/UTC/Kiritimati, termasuk reload/retry.
2. Jalankan delapan SQL cases yang di-hash pada disposable exact candidate, serta101-source fixture. Pertahankan raw errors sebagai INCOMPLETE. Bahas H01 hanya jika observable behavior dan semantik kontrak belum dapat dipastikan.
3. Perketat unique-ID/status handling runner; verifikasi session/connection isolation sesuai skenario yang benar-benar dibutuhkan.
4. Sediakan source-bound package rollback/refusal lalu buktikan pre-use restore dan post-use refusal tanpa mutasi. Jangan mengganti gate dengan successful dump restore.
5. Tutup remaining family/Auth/concurrency/readiness scopes dengan oracle kontrak; pertahankan per-case disposition T2. Bila product source berubah, ulangi bukti yang terinvalidasi sesuai impact map.
6. Owner menilai acceptance setelah bukti tersebut tersedia; laporan ini tidak memberikan production GO.

## 7. Artefak dan cara melanjutkan

`CP6_AUDIT_EVIDENCE_9add57e.zip` memuat kontrak,input handoff, lock/manifest fase1,catatan keluarga dan adversarial review,dua Python scenarios,local repro/results,raw native logs,serta rekonsiliasi fase2. `AUDIT_SHA256SUMS` mencatat setiap file; `AUDIT_RECEIPT.json` mengikat laporan,manifest,identity,dan waktu finalisasi. Repo produk tidak disalin ke bundle.

Untuk menjalankan ulang local probes, checkout kandidat exact SHA ke folder `repo/` di samping `work/`. Probe frontend membutuhkan Node yang mendukung TypeScript stripping; Python repro tidak membutuhkan DB. Jalankan di salinan bundle agar bukti frozen tidak tertimpa. SQL scenarios menggunakan runner `cases(cur,today)` pada disposable workflow yang diizinkan owner; scenario hash harus dicocokkan ke log dispatch.

SHA-256 raw logs:

| Job | SHA-256 |
|---|---|
|107772603343 |`e82c5b61dcfb60b1ba45c6c1645eb2c602bf538d0d5b5f04be716fdde0f38042` |
|107772639059 |`f0be4b154f3e0ffc6f8cf15e158c7e5e4a804a8a983597164b5c3075844c5404` |
|107772676223 |`a8d0c4b672e57e0e978ac26484987f8ea8ce83afbaf7792a4378779f14e6f0b3` |

Catatan agen asli dapat memakai ID lokal berbeda atau menyebut aturan checkpoint dari kutipan user yang kemudian diklarifikasi. ID dan disposisi kanonik dalam laporan ini adalah F01,U01–U03,R01–R02,H01–H02,O01. Tidak ada klaim commit/push yang berasal dari sesi audit ini.

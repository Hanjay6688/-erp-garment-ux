# Laporan audit CP6 — checkpoint pemulihan

Tanggal: 24 September 2026 UTC.
Kandidat: `9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc`.
Tree kandidat: `5d5f833b2e75e23184c643d5ac469781f1c3ce5e`.
Baseline pembanding: `ca7f09556397801c50a2277bdb65b1bf019f9a05`.
Cabang audit: `audit/cp6-final-20260924-gpt-a0bcadf`.

## Putusan

**HOLD; production_go=false; audit_complete=false.**

Audit yang diminta mencakup seluruh CP6. Laporan pertama berhenti terlalu dini; laporan itu tetap berstatus checkpoint parsial. Dokumen ini memperluas cakupan dan menyimpan hasil lanjutan, tetapi belum menutup seluruh kewajiban audit.

Dari sepuluh kelompok gate auditor, enam HOLD dan empat UNVERIFIED; belum ada ACCEPT untuk keseluruhan gate. Tidak ada P0 yang dibuktikan. U02/U03 telah dikonfirmasi melalui review independen atas log native Claude, berlabel REUSED_EVIDENCE; kasus original kami tetap NOT_RUN. Handoff gabungan tanpa duplikasi tersedia di AUDIT_HANDOFF_CP6.md; batas oracle dan koreksi laporan Claude ada di AUDIT_CLAUDE_CROSS_REVIEW.md.

HOLD berarti bukti dan pemenuhan kontrak belum cukup untuk menyetujui kandidat. Dokumen ini tidak menyatakan telah terjadi kehilangan uang atau insiden produksi.

## Pembaruan6140edb: sebagian bukti rollback tersedia

Run36063754595/job107848561550, attempt1/head6140edb1acd182efc84a4c85879860785335e688, telah diverifikasi dari log Actions: **22 pemeriksaan writer PASS**, mencakup dua siklus rollback AW..AZ dan pasang ulang serta empat refusal tanpa perubahan state pembanding. EmpatSQLrollback dan builder cocok hash manifest; capture18380bytes direkonstruksi dari log, SHA25662bb0e2a9a0bb69106538d32569239bf67bb8c79e05325808f837ad6f8450cf6. Produk forward tetap9add; tidak ada diff pada migrations/dev/release/cp6-t3/src.

**C6-10 tetap HOLD:** AW..AZ sudah tersedia dan diuji writer, sementara AC..AV versi release NOT_BUILT. AZ→AW kembali ke AV. Batas bukti: normalisasi capsule pada siklus2/reinstall mengecualikan captured_at dan boundary_snapshot; post-usefixture memakai satu INSERTaudit_logs. Review independen SQL/helper dan kecukupan oracle belum selesai. [Ledger](out/writer_6140edb_run_ledger.json) dan [catatan](out/writer_6140edb_review.md) menyimpan detail. Ini REUSED_WRITER_EVIDENCE; native15 tetap NOT_RUN.

## Dasar dan batas otoritas

Gate dan oracle berasal hanya dari tiga kontrak yang diserahkan pengguna:

- M: `ERP_V3_2_Master_Pulih_20260923.md`.
- P: `ERP_V3_2_Perubahan_Pulih_20260923.md`.
- BR: `ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md`, untuk batas tahap CP6/CP7.

SHA256 ketiganya tercatat dalam [AUDIT_PROGRESS.md](AUDIT_PROGRESS.md). Berkas latar ERP, komentar implementasi, status PASS writer, klaim auditor lain, serta ingatan audit lama tidak dijadikan oracle. Nomor baris M/P/BR mengacu pada berkas kontrak asli, bukan nomor baris laporan.

C6-01 sampai C6-10 adalah pengelompokan auditor. Satu operasi yang lolos pemeriksaan tidak menerima seluruh gate.

| Gate | Status | Contract file/lines | Current basis |
|---|---|---|---|
|C6-01 evidence identity/completeness|HOLD|M1624–1626,1693,1762–1767,4391–4393,4521–4525|Exact SHA/jobs bound; runner duplicate-ID loss; T2 disposition and missing independent cases remain.|
|C6-02 atomicity/immutable facts/exact state|HOLD|M3816–3826,5048–5052|U02/U03 corroborated from independently reviewed external native logs: historical WIP prefix and zero-qty inventory value counterexamples. REUSED_EVIDENCE; full lifecycle acceptance absent.|
|C6-03 recovery/input/unknown/selectors|HOLD|M1678–1679,1691,3817–3820,3825–3826,3939|Wrong WIB payloads, unstable request recovery and failed-read zero display reproduced locally; selector tails source-supported.|
|C6-04 ALL initial import|UNVERIFIED|M44–45,359–365,749–755,829–843,934–938,1024–1025,1691; P966–967|22-state semantic crosswalk persisted; native continuation and unmapped adapter obligations remain.|
|C6-05 dates/recost/HPP/journals/reports|HOLD|M375,377,837,1022,1059–1065,1666,1691,3816,3820,3825|F01 wrong WIB payload; U02/U03 native WIP/cent counterexamples corroborated via REUSED_EVIDENCE. Full dated financial acceptance absent.|
|C6-06 production/AP/AR/payroll/advances|HOLD|M359–379,629–648,749–757,3822–3824|U02 WIP counterexample corroborated via REUSED_EVIDENCE. Advance and payroll/BS attribution hypotheses still NOT_RUN; broader lifecycle coverage absent.|
|C6-07 accepted accessories/pocket|UNVERIFIED|M44–48,466–472,495,557–561,1023,3900–3902,3951,5192–5199|Positive local controls and source mechanisms; whole lifecycle/races not independently accepted; expanded CR scope separate.|
|C6-08 Auth/permissions/connected UI|UNVERIFIED|M1691,4486,5046–5052,5209,5213–5224|27 public RPCs traced;10 browser cases rerun; full real Auth/action/location/revocation matrix absent.|
|C6-09 concurrency/stale state|UNVERIFIED|M751–755,1025,4165,4486,5048–5052|Existing AR/AT/AU races rerun;20 AR observations independently checked narrowly; own full schedules absent.|
|C6-10 install/compatibility/rollback/cleanup|HOLD|M1767,3826,4306–4314,4486,5192–5209|Install/backup restore scoped positive;6140edb AW..AZ writercycle22PASS; AC..AV releaseNOT_BUILT and full rollback qualification remain open.|

## Cakupan yang telah dicatat

Matriks kewajiban yang terakhir disimpan di workspace memuat132 baris dalam27 keluarga:80 inti CP6,32 ekstensi CP6 yang diterima,13 baris bergantung pemilihan CR, dan7 batas tahap berikutnya/opsional.105 ID uji stabil dalam kontrak telah disilangkan. Angka itu bukan132 uji yang sudah dieksekusi.

Distribusi penilaian terakhir:96 UNVERIFIED,7 UNVERIFIED_SOURCE_RISK,5 HOLD_SOURCE_REPRO,2 PARTIALLY_VERIFIED,1 HOLD_QUALIFICATION,1 HOLD_EVIDENCE_PRODUCER,13 SCOPE_UNRESOLVED,7 DEFERRED. Baris yang belum dikerjakan tidak dihitung sebagai PASS.

Berkas matriks final belum berhasil dipulihkan byte-nya setelah workspace terputus. Receipt terakhir:
- `continuation/coverage_matrix.json`: `e5fdcc9fc6fdd165ee701094e2c60e8639b87673ec73bc9b1554c4c11491fd1d`.
- `continuation/coverage_completion.md`: `c5bb9160e0f6005e8d530a826504b0a61348d1bc8ba081278b70182e4c973394`.

Jangan menganggap kedua berkas itu sudah ada di cabang pemulihan ini. Versi checkpoint sebelumnya tersedia terpisah; pengganti byte tidak dibuat dengan mengklaim hash lama.

Hasil yang sekarang tersimpan langsung di cabang ini:

- [Ledger native per kasus](out/native_case_ledger.json): hasil terstruktur dan lokasi baris log dari sembilan job auditor yang sudah selesai, termasuk tahap install dan observasi restore.
- [Pemetaan semantik ALL](out/all_open_documents.md) dan [JSON](out/all_open_documents.json): enam keluarga dan22 keadaan dokumen cutover.
- [Pemeriksaan sumber payroll](out/payroll_source_followup.md): eligibility, snapshot/rate, kapasitas komponen, BS dan rework beserta batasnya.
- [Checkpoint dan langkah lanjut](AUDIT_PROGRESS.md).

## Bukti runtime yang benar-benar tersedia

Sembilan job di bawah merupakan eksekusi terpilih yang benar-benar baru pada saat dijalankan. Pengambilan ulang log dalam pemulihan ini bukan run baru. ID job warisan pada attempt berikutnya tidak dihitung sebagai eksekusi tambahan.

| Run ID | Job ID | Actual start UTC | Observed scope/result |
|---|---|---|---|
|36037873682|107772639059|18:23:54|Original326:314 PASS/control,12 date-policy HOLD; NEW34:25PASS/8COUNTEREXAMPLE/1INCOMPLETE; AO12:8PASS/4INCOMPLETE. DISPOSITION_REQUIRED, primary unchanged,clone0. Log2198–2199.|
|36037876338|107772603343|18:23:48|24install stages; restored same meaning318tables/1647rows,5checks; Auth0→0/primary unchanged.54advisorINFO reviewed, not assumed security exposure. Log1301–1330.|
|36037878419|107772676223|18:24:00|CodeQL JavaScript/TypeScript PASS,result_count0. Log2415.|
|36037873682|107792476681|19:15:14|AR146sequential+28race writerPASS. Independent raw-observation checker20scopedPASS/5INCOMPLETE/3UNVERIFIED.|
|36037876338|107792486765|19:15:17|Browser10PASS,console0,REST stopped,Auth0→0,primary unchanged. Opening WIP_OUTPUT flow only. Log1608–1609.|
|36037878419|107792495809|19:15:18|CodeQL Actions PASS,result_count0. Log1331.|
|36037878419|107794260297|19:19:58|CodeQL Python PASS,result_count0. Log1811.|
|36037873682|107795483321|19:23:12|AT16+AU15sequential and4+6races writerPASS. Raw worker results retained; boolean invariants not promoted to full independent proof. Log1739.|
|36037878419|107795615827|19:23:33|CodeQL C++ PASS,result_count0. Log1772.|

Semua terikat kandidat9add57e. Job pin T3 `107772660584`, baris1340, equal:true merupakan bukti existing yang dibaca, bukan rerun auditor baru.

Ledger menyimpan status output asli writer. Itu memungkinkan pemeriksaan ulang setiap kasus, tetapi PASS-only tanpa observasi bisnis rinci tetap terbatas. Seed/fixture diagnostics dikeluarkan dari jumlah kasus. Duplikasi pasangan group/case tidak ditemukan dalam catatan kasus native yang dipulihkan.

Tiga hash log fase1 cocok kembali setelah mempertahankan konvensi berkas lokal sebelumnya: UTF-8 hasil fetch ditambah satu LF. Ledger mencatat kedua hash, yaitu teks sebagaimana diambil dan varian dengan tambahan satu LF; tidak menyamarkan perbedaan encoding sebagai perubahan hasil.

### Interpretasi T2

BUSINESS230 terdiri dari179 PASS,39 CONTROL_PASS dan12 DATE_POLICY_REVIEW_REQUIRED; IMPORT31 dan VALUES65 PASS. Jadi326 kasus historis menghasilkan314 PASS/control dan12 HOLD kebijakan tanggal.

NEW34 tetap25 PASS,8 COUNTEREXAMPLE dan1 INCOMPLETE; AO12 tetap8 PASS dan4 INCOMPLETE. Overlay8 tanggal,5 tambahan dan12 calendar-policy disimpan terpisah. MATCH pada overlay writer tidak otomatis mengganti status mentah atau membuktikan oracle kontrak. Dua belas analisis calendar-policy merujuk keluarga kasus HOLD lama; tidak dihitung sebagai12 cacat tambahan.

Untuk AR, pemeriksaan auditor terhadap observasi mentah menghasilkan20 pemeriksaan sempit yang sesuai,5 INCOMPLETE karena rincian penolakan kurang, dan3 UNVERIFIED karena bukti hanya boolean writer. Pemeriksaan sempit mencakup satu header POSTED, satu efek kuantitas/nilai, debit-kredit agregat, dan beberapa penolakan yang teramati. Belum membuktikan semua akun, dimensi, lineage, prefix tanggal, baseline rollback, atau kesamaan respons replay.

AT/AU mempunyai hasil worker native, tetapi sejumlah invariant tetap hanya boolean writer. Menemukan mekanisme lock di source atau melihat status race PASS belum menerima seluruh C6-09.

### Interpretasi T3 dan CodeQL

Install24 tahap dan restore snapshot setelah install memberi bukti positif terbatas. Drill restore membandingkan318 tabel/1.647 baris dan lima pemeriksaan. Exit restore1 memuat19 error pg_cron yang diklasifikasikan; sumber memiliki0 cron jobs, data dibandingkan identik, dan engine dibandingkan sama. Ini belum membuktikan downgrade kandidat ke baseline.

Sepuluh kasus browser mencakup login nyata, penolakan anonymous, dua fixture identitas PRODUCT yang ambigu dalam WIP_OUTPUT, satu balasan hilang/remount/replay, stock/HPP dan inverse terkait. Kasus itu belum meliputi seluruh halaman, zona waktu perangkat, hak akses, lokasi atau pemulihan setiap command.

Empat CodeQL menghasilkan result_count0. Itu tidak menguji kebenaran bisnis SQL.54 INFO RLS-without-policy pada advisor mempunyai REVOKE eksplisit pada sumber yang ditinjau; jumlah INFO tidak dijadikan bukti otomatis kebocoran data.

## Temuan, oracle dan tingkat bukti

Prioritas adalah dampak potensial bila jalur dan kondisi yang dijelaskan terpenuhi, bukan pernyataan bahwa dampak produksi telah terjadi.

| ID | Priority/status | Independent oracle and evidence |
|---|---|---|
|F01|P1/local confirmed|M3820 WIB input2026-09-20T00:30 must serializeSep19T17:30Z on every device. Active Cutting/Pickup/BS serialize via device timezone.34exact-source checks28PASS/6FAIL; actual persisted ledger impact not native-tested.|
|U01|P2/source CONFIRMED,native corroboration limited|M1691 complete selectors. Claude XA2 returned100 recent eligible delivery rows while omitting oldqty10. Fixture uses privileged cloning; full legal producer/claim/UI sequence unverified. REUSED_EVIDENCE run36051514868/job107807966805.|
|U02|P1/CONFIRMED via REUSED_EVIDENCE|M3816,3820–3823. Claude XA1 on9add: second completion POSTED, stageprefix−8 and WIPGLPO−20. Run36048357523/job107797410652. Our original SI02 file remains NOT_RUN; reviewed equivalent native case is separately attributed.|
|U03|P2/CONFIRMED via REUSED_EVIDENCE|M1022,3818,3820. Claude XA1/XA2 correction+invoice paths endrawqty0 with inventory−0.01/up or+0.01/down. Up WIP10.02 vs10.01. Down half-tie oracle qualified; residual still confirmed. Jobs107797410652/107807966805. Our four original cases remain NOT_RUN.|
|R01|P2/local confirmed|M1767,4391–4393 traceable evidence. Duplicate IDs overwrite earlier INCOMPLETE in actual unchanged runner AST with I/O doubles. Raw logs retain both. Current indexed native cases had no duplicate group/ID.|
|R02|P2/qualification gap|M3826,4306–4314,5198–5209. At9add AW–AZ rollback absent. At6140edb four artifacts and22writercyclechecks PASS; AC..AV releaseNOT_BUILT, full inverse qualification open. Forward MANIFEST remainsNOT_TESTED; product unchanged.|
|C-AUTH-01|P2/local confirmed,post-lock|M1679,3819 retain exact request envelope. Pattern/Access retries regenerate UUID; quick-create can reuse UUID with changed payload.7local checks4PASS/3FAIL. Server uniqueness/version protections acknowledged; no committed duplicate/data-corruption claim.|
|C-SEL-01|P2/source confirmed,nativeUNVERIFIED|M1691,3826,4486;M495 for pocket cancel. Initial-import latest50 and pocket-period latest50 are sole action selectors; payroll/prepayment targets cap100. One public51draft scenario prepared; other valid fixtures unwritten.|
|C-UNK-01|P2/local confirmed,post-lock|M3825 unknown is not zero. Failed initial Laundry/QC workspace read leaves null but unconditional KPI expressions render0.4local checks2PASS/2FAIL. Error banners and writer locks remain; no financial finality or mutation bypass claim.|
|C-BIZ-01|candidateP1/nativeUNVERIFIED|M629–646 and3816–3820. Opening67.25D−8,correctionto100D−2,refund100D−4 predicts normal advance prefix−32.75 for supplier/vendor/customer while current0. Public route source traced; six cases NOT_RUN. Applying dated-prefix rule to advance monetary capacity is stated inference.|
|C-BIZ-02|unpromoted reachability lead|COUNT transfer/adjustment may admit0.5; no independent ordinary route proof. Runner conditionally grants schemaUSAGE. Four cases excluded from default batch; optional execution remains INCOMPLETE with privilege qualification.|

### Dampak dan batas temuan utama

**F01 — tanggal WIB bergantung zona perangkat.** Input2026-09-20T00:30 WIB harus menjadi2026-09-19T17:30Z. Callback aktif Cutting/Pickup/BS menggunakan `new Date(datetime-local).toISOString()`: pada perangkat UTC menghasilkan2026-09-20T00:30Z; pada Kiritimati menghasilkan2026-09-19T10:30Z. Ini dapat mengubah tanggal kejadian, urutan dan periode akuntansi yang diminta pengguna. Oracle M3820 dan34 pemeriksaan source lokal mendukung cacat payload; posting ledger pada browser nyata untuk fixture ini belum dijalankan. Locator: `src/ConnectedCuttingPage.tsx:272`, `src/ConnectedPickupPage.tsx:200`, `src/ConnectedBsResolutionPage.tsx:40` serta pemanggilnya. Laundry/QC dengan helper waktu bisnis menjadi kontrol positif.

**R01 — kehilangan kasus dalam ringkasan runner.** AST runner kandidat yang tidak diubah, dijalankan dengan I/O doubles, menimpa hasil pertama ketika ID kasus sama; ringkasan akhir dapat PASS walau kasus pertama INCOMPLETE. Log mentah tetap menyimpan keduanya. Ini kelemahan produsen bukti, bukan bukti transaksi ERP salah atau kasus T2 aktual hilang.

**C-AUTH-01 — identitas permintaan saat balasan tidak diketahui.** Retry save Pattern/Access membuat UUID baru; quick-create dapat mempertahankan UUID sambil mengubah payload dan kehilangan UUID ketika remount. Respons server setelah commit yang hilang belum direproduksi native. Unique/version guards mengurangi sebagian duplikasi, tetapi tidak memulihkan envelope permintaan semula. Dampak yang dibuktikan terbatas pada perilaku callback pemulihan, bukan committed double-write.

**C-UNK-01 — gagal membaca menjadi angka nol.** Awal workspace Laundry/QC yang gagal dibaca tetap null, sementara ekspresi KPI menampilkan0. M3825 membedakan data unknown dan zero. Error banner dan penguncian write masih ada; tidak diklaim sebagai bypass posting atau laporan keuangan final yang palsu.

**C-SEL-01/U01 — sumber valid di luar batas daftar.** Daftar import/pocket50 dan payroll/prepayment100 tidak memiliki kelanjutan pada pemilih tindakan yang diperiksa. Reader BS membatasi100 sebelum filter claimable. Ini berpotensi membuat tindakan terhadap sumber lama tak terjangkau dari UI. Satu skenario51 draft import telah disiapkan, belum dijalankan; fixture pocket/payroll/prepayment/BS lengkap masih harus ditulis.

**C-BIZ-01 — kapasitas advance pada tanggal historis.** Sumber67,25 padaD−8, koreksi menjadi100 padaD−2, refund100 padaD−4 diprediksi menghasilkan saldo normal−32,75 padaD−4 meskipun saldo sekarang0. Berlaku tanda aset untuk supplier/vendor dan tanda kewajiban untuk customer. Public dispatcher, state reducer dan period guard telah ditelusuri; koreksi dan refund memakai kapasitas kini. Enam skenario termasuk kontrol urutan disiapkan. Penerapan aturan dated-prefix M3816–3820 ke kapasitas uang muka dinyatakan sebagai inferensi auditor bersama M629–646; belum ada hasil native.

**U02/U03 — prefix WIP dan satu sen recost.** Oracle fase1 kami sekarang mendapat corroboration native dari kasus Claude pada exact kandidat. U02 menghasilkan stageprefix−8/WIPGLPO−20; U03 meninggalkan nilai persediaan±0.01 saat qty0 pada correction dan invoice. Ini REUSED_EVIDENCE yang diperiksa dari log asli, bukan run baru kami. Oracle half-even pada arah turun tidak dipakai untuk mengklaim WIP10.00 sendiri salah. Detail fixture, hash dan batas dampak ada di AUDIT_CLAUDE_CROSS_REVIEW.md.

**R02 — kualifikasi rollback seluruh paket belum lengkap.** Writer menambah empat rollback AW–AZ pada6140edb; dua siklus dan refusal tercatat PASS dalam22check native writer. Ini kembali ke AV; AC..AV versi paket rilis masihNOT_BUILT. OriginalAV teramati menolak releasechain tanpa perubahan state. GuarddigestAC tetap tidak boleh dilemahkan. Auditor perlu menilai generatedSQL/helper, normalisasi capsule dan cakupan oracle. Bukti AW..AZ ini dicatat sebagai kemajuan yang terbatas, dengan C6-10 tetapHOLD.

H01 identitas optional WIP, H02 perubahan alternate-route item draft, nullable expected_version pada deactivation, COUNT pecahan, dan kebijakan GRNI_ESTIMATE_OPEN tetap lead/kesenjangan yang belum dipromosikan.

## Lanjutan ALL dan payroll

Pemetaan [ALL](out/all_open_documents.md) mengikat kewajiban kontrak ke representasi yang diterima serta state yang diperlukan command berikutnya:

| Keluarga | Bukti sumber positif | Masih harus dibuktikan |
|---|---|---|
| Purchase/receipt/invoice | Uninvoiced receipt menjadi purchase item native; supplier debt lama menjadi opening subledger yang dapat diselesaikan. | Split receipt sebagian diinvoicing, hak retur lama, public cash-settlement chain dan procurement draft. |
| Sales/reservation/returns | AR lama bernomor dapat menjadi opening receivable. | Reservasi draft lama, alokasi lot untuk retur lama, credit/refund yang masih terbuka. |
| Payroll/attendance/reimburse | Kewajiban mandor yang sudah diakui dapat dibawa sebagai opening payable. | Kerja belum disetujui, attendance/carry, entitlement BOM dan pencegahan accrual kedua. |
| Advances/settlements | Sisa advance dan alokasi cash advance ke payroll baru mempunyai command lanjutan. | Prefix waktu, pemakaian bersamaan, pemilihan target lengkap, pemisahan utang aksesori dari cash advance. |
| Production/WIP/BS/laundry/rework | PO header, WIP SEWING/LAUNDRY, output terattestasi dan valued BS terpetakan. | Cut-but-unpicked, laundry delivery/claim lama dan rework yang sudah berjalan saat cutover. |
| Accessory/pocket custody | Stok awal dan tindakan issue/withdrawal baru terpetakan. | Hak retur nota lama, custody/condition/recovery bila CR dipilih, serta pool pocket lintas cutover. |

M930–938 mengizinkan provenance keuangan tanpa mengarang nota lama; M369–379 membatasi rekonstruksi sejarah WIP. Karena itu sumber yang belum terpetakan dicatat sebagai UNMAPPED, bukan otomatis cacat. Enam keluarga/22 keadaan juga bukan penerimaan ALL.

Pemeriksaan [payroll](out/payroll_source_followup.md) menolak dua dugaan dalam source: regular wages tidak diskalakan GOOD/laundry return, dan duplicate component rows tidak melewati cap melalui snapshot berbeda pada jalur yang diperiksa. Konservasi alokasi payroll, snapshot first-use, rate efektif, freeze rate yang sudah dipakai dan source lock telah ditelusuri. Installed definitions, lawful entry route dan native lifecycle tetap belum dibuktikan lengkap.

Satu risiko BS baru belum dipromosikan: group10 dengan komponenB selesai pada GOOD8 tetapi belum dikerjakan padaBS2 dapat mendapat baseline otomatis `min(2,8)=2`. Rework kemudian menghitung entitlement baru0, sementara fakta contoh mengharuskan2×25=50. Koreksi CLASSIFY_BS tersedia sebelum rework dan menjadi kontrol penting. Pemeriksaan dispatcher, save caller dan trigger menemukan koreksi itu opsional pada jalur source yang diperiksa; baseline tidak dikoreksi otomatis. Namun belum dibuktikan secara native bahwa fixture sah pada instalasi kandidat menyebabkan kehilangan entitlement. Tidak ada skenario executable/native untuk risiko ini.

Kepatuhan Special belum dapat dinilai normatif pada lanjutan ini karena bagian kontrak presisinya belum dibaca ulang. Source policy flags bukan pengganti oracle kontrak.

## Protokol buta dan rekonsiliasi

Lock fase1:
- `PHASE1_FINDINGS_LOCK.md`: `cbca0c6cb3150f0005bbea877d1a6b0371afa6103d9907c21899b1e235e46156`.
- `PHASE1_SHA256SUMS`: `50ba9228c863d4c483404bd425d8d64aac3073c3cd6726e35d9ca840d653438a`.

Writer evidence terpilih dibaca pada fase2 setelah lock. Recheck lokal terakhir menunjukkan kedua lock tidak berubah. Temuan C-* dan pemeriksaan ALL/payroll lanjutan dinyatakan post-lock.

Paparan sebelum lock tetap diungkap: ingatan audit sebelumnya, nama berkas terlarang/satu snippet judul commit, dan bocoran auditor lain. Semuanya dikecualikan sebagai oracle. R01 sudah direproduksi independen sebelum bocoran duplicate-ID. Klaim advisory lock dan second-connection commit tidak dinyatakan sebagai hasil native kita.

Rekonsiliasi mempertahankan batas klaim: install PASS tidak menerima rollback, browser10 tidak menerima semua flow/Auth, MATCH writer tidak mengganti status raw T2, INFO advisor bukan exposure otomatis, dan source/release40 body-match bukan bukti lengkap katalog terpasang. Tidak ada temuan native baru hanya karena dokumen writer menyebutnya.

Instruksi owner terbaru mengubah urutan: laporan Claude diminta diperiksa sekarang dan hasilnya digabung ke repo. Review dilakukan post-lock pada snapshotcf301a6, dengan kontrak/source/log Actions sebagai pembanding. Race36051535647/36052066150 terverifikasi gagal sebelum balapan; sumber xaudit_4 dibaca, tetapi kejadian classifier sendiri tetap laporan eksternal. Tidak ada upaya melewati penolakan izin atau mengambil credential. Lihat AUDIT_HANDOFF_CP6.md dan AUDIT_CLAUDE_CROSS_REVIEW.md.

## Skenario yang disiapkan

Default combined batch:15 cases, native **NOT_RUN**, run_id:null,job_id:null.
- combined_scenarios.py SHA256 `968cac54ac7fa7fe4e3fc1d666e257b04944faf1beec1f45a209274db00869d1`;25248bytes;33664base64chars.
- work/stock_import_scenario.py:4cases; SHA256 ff92e8d973ebb75c05ba8ac6b47da96565c9b50760c91b247f331a765d18df81.
- work/money_dates_scenario.py:4cases; SHA256 cfa1157b7ea39e6f5162d85a540ed5e22c30d8fef9ddfe840b5a9bf2f631d9ef.
- continuation/business/business_scenarios.py:6default advance cases,4held COUNT cases; SHA256 44b075c763a5d6962322d51e4b4ed0b75360b6e0135575420208ac39152b342b.
- continuation/auth_selector_scenarios.py:1case; SHA256 2276140a28ce27e9cd8e18b03285bdeee9aa33aee4118fe701eca20442bc3bd4.
Syntax, embedded-byte/hash equality, JSON roundtrip and unique factory IDs were checked. Factory enumeration used inert runtime imports. No case lambda/SQL executed.

Pembaruan recovery: exact stock_import_scenario.py dan money_dates_scenario.py (8kasus) telah dipulihkan dan disalin ke audit/scenarios/ dengan hash di atas. Byte final lama gabungan15/business6/selector1 tidak pulih utuh. Kini business6+selector1 telah direkonstruksi dengan hash baru dan digabung bersama8kasus exact menjadi payload15baru; native tetap NOT_RUN. Matrix lama tetap berbeda hash dari versi final.

Empat kasus COUNT yang membutuhkan kualifikasi privilege dikeluarkan dari batch default. Runner yang disetujui mempunyai conditional schema USAGE grant; keberhasilan di bawah grant tersebut tidak membuktikan ordinary reachability pada ACL kandidat yang belum diubah.

## Pekerjaan tersisa dan hambatan konkret

| Jenis | Keadaan aktual | Syarat lanjut |
|---|---|---|
| Workspace | Sudah online lagi; folder lama hilang. Penyebab platform dari409 terdahulu tidak teramati. | Kontrak, lock fase1 dan8kasus exact sudah pulih. Rekonstruksi hanya revisi yang hilang dengan hash baru; jangan mengaku sebagai byte lama. |
| Dispatch | Tool sesi ini dapat rerun job existing; tidak menyediakan custom workflow-dispatch POST atau DB lokal. | Jalankan payload yang sudah disiapkan melalui endpoint disposable yang disetujui dari lingkungan berkemampuan dispatch. Jangan ubah workflow atau produk untuk melewati batas. |
| Oracle Special/rate | Bagian kontrak rinci tidak tersedia untuk dibaca ulang pada fallback ini. | Pulihkan kontrak asli dan verifikasi hash/baris sebelum putusan normatif. |
| Rollback | Jalur AW–AZ lengkap belum tersedia/terkualifikasi. | Writer menyediakan downgrade atau demonstrasi refusal aman yang memenuhi kontrak; auditor memverifikasi native. |
| Pekerjaan audit belum dilakukan | Native15, fixture selector lain, browser timezone/unknown/recovery, Auth/action/location, jadwal concurrency sendiri, transitive HPP/source producers dan sejumlah adapter ALL. | Siapkan fixture sah dan oracle independen, jalankan serta catat dampak, replay/inverse, rollback/cleanup. Ini bukan semuanya hambatan alat. |
| Laporan auditor lain | Owner terbaru meminta review sekarang dan penggabungan repo. | Cross-review selesai untuk temuan/hambatan prioritas; hasil deduplikasi dan queue lanjut ada di AUDIT_HANDOFF_CP6.md. Seluruh CP6 tetap belum selesai. |

Tidak ada produk, main, cabang kompetisi/writer, hosted/legacy/production database atau deployment yang diubah oleh pekerjaan pemulihan. Cabang ini berisi artefak audit. Laporan dan log di sini memungkinkan sesi berikut melanjutkan tanpa mengulang fase1 atau mengandalkan chat sebagai satu-satunya checkpoint.


## Pembaruan integrasi audit silang — 24 September2026

Owner meminta audit GPT dan Claude digabung tanpa mengulang temuan yang sama. [AUDIT_HANDOFF_CP6.md](AUDIT_HANDOFF_CP6.md) menjadi pintu masuk lanjut: satu ID gabungan per isu, alias kedua audit, tingkat bukti, status disagreement,4hambatan runtime dan next actions. [AUDIT_CLAUDE_CROSS_REVIEW.md](AUDIT_CLAUDE_CROSS_REVIEW.md) menjelaskan verifikasi dan batas tiap klaim. Laporan asli/hasil gagal tetap dipertahankan melalui referensi commit.

Koreksi penting: ALL sudah disetujui menurutM1024; F1-02 bukan konflik keputusan aktif. F1-12 numeriknya terbukti tetapi identitas sumber fisik lintas batch belum ditentukan. Run race rev2 memakaiSHA5d640e42..., bukanSHA3915e006... milikrev1. Hasil tersebut belum menjadi penerimaan seluruh gate. Tidak ada custom native run baru selama recovery/cross-review.


## Sumber native15 siap, eksekusi belum berjalan

Payload audit/scenarios/combined_native15_reconstructed.py mempunyai SHA256`cec2ad521835476cf702119486e637d3eff4b62d8f72197a9ca2c2d50cf1fadb`,47183bytes dan15caseID unik. Manifest audit/scenarios/native15_manifest.json mengikat8kasus frozen exact dan7rekonstruksi post-lock. Sintaks, registrasi tanpa DB, source embedding dan hash sudah diperiksa; **belum ada native run atau hasil bisnis**. RunID/jobIDnull. BatasoracleSI01, moneyDOWN, advance danUIselector dicatat pada manifest. Ini tidak mengubah HOLD atau audit_complete=false.

## Addendum Fable — hasil native lanjutan (24 Sep 2026, run 36065350201 & 36065517737 pada head alat d284e9b, produk 9add57e)
Rincian expected/actual per kasus: `out/fable_native15_xaudit5_results.md`; register diperbarui di `audit/CP6_COMBINED_INDEX.json`.
- native15 (skenario GPT, oracle direview Fable): SI-01 COUNTEREXAMPLE (WIP teridentifikasi diselesaikan sebagai produk/brand/warna lain; CP6-18), SI-02 COUNTEREXAMPLE (prefix WIP −8; CP6-02), SI-03 PASS, SI-04 COUNTEREXAMPLE (draf prepared diedit lalu POSTED tanpa rekonsiliasi; CP6-19, caveat reachability), MONEY 4× COUNTEREXAMPLE (CP6-03), ADVANCE ORDERED 3× PASS, ADVANCE DATED_CAPACITY 3× COUNTEREXAMPLE (**CP6-07 P1**: uang muka −32,75 pada prefix), SELECTOR-51 INCOMPLETE (fixture GPT; rerun run 36066079063).
- xaudit_5 (oracle Fable pada mode dua sesi + Auth/HTTP nyata writer): R1 CP6-09 terbukti di bawah dua sesi (kunci ada, guard tidak); **R2 baru CP6-24 (P2)**: close tanggal yang sama diulang → dua filing; R3 aman (penolakan POCKET_PERIOD_BUSY, tidak ada output ganda; pesan ≠ STALE_VERSION); H1 matriks fail-closed anon/GUDANG/viewer(M:281)/OWNER lulus substansi (2 cek gagal = artefak argumen dummy probe); H2 revocation PASS; H3 unmapped PASS. Browser→HTTP→runtime UI belum.
- Verdict tetap: CP6 HOLD, audit_complete=false, production_go=false.

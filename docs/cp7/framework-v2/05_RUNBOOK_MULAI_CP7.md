# Runbook mulai, estafet, dan keputusan

> **Revisi2 aktif:** baca `06_RUSUK_KEBUTUHAN_OWNER.md` terlebih dahulu. Kontrak AnalysisResult v2 menggantikan bentuk v1; pin/head dan receipt v1 di bab ini adalah sejarah persiapan, bukan accepted base. WA readiness dibawa ke CP7; aktivasi live tetap punya gate tersendiri.

## 1. Status yang dibawa sekarang

```json
{
  "framework_version": "CP7-BACKBONE-20260928-v2",
  "mode": "PREPARATION_ONLY",
  "cp6_gate": "HOLD",
  "cp7_implementation": "NOT_STARTED",
  "observed_writer_branch": "claude/new-session-deapao",
  "observed_head": "2c2fd5e8e0df5f8ada44402c93f70dbaf0fbbb5b",
  "observed_tree": "20826407e5f98f798b1650f520300e85aebbd2eb",
  "production_go": false,
  "accepted_execution_base": null,
  "base_reason": "Independent CP6 acceptance pending",
  "first_execution_packet": "P00",
  "product_mutations": 0,
  "hosted_mutations": 0,
  "deployments": 0,
  "preparation_status": "FRAMEWORK_REVISED",
  "owner_delta_source": "Current owner message 2026-09-28 14:03 Asia/Bangkok",
  "messages_sent": 0,
  "next_action": "Review v2; P00 only after accepted CP6 and implementation mandate. Do not reuse historical writer head as accepted base."
}
```

Null accepted base adalah keadaan yang diketahui, bukan ruang kosong yang boleh diisi dengan HEAD terbaru secara otomatis. Setelah audit selesai, tulis delta receipt terhadap nilai ini; jangan membuat framework baru dari nol.

## 2. Sepuluh langkah pertama setelah CP6 sah dan owner memberi mandat CP7

1. Baca `00_MULAI_DI_SINI`, current handoff repo, accepted audit BD/BE/CP6, contract delta sesudah 28 Sep. Cocokkan remote head/base/tree dengan acceptance; jika berbeda lakukan impact map.
2. Verifikasi single writer; claim P00. Cek worktree/diff dan proses/test aktif yang diketahui. Writer tak dikenal → stop penulisan dan kabari Hansen; jangan force push atau mengasumsikan diam berarti berhenti.
3. Buat branch CP7 yang disepakati dari accepted base; branch CP6/auditor/main tidak dipakai sebagai scratch. Nama rekomendasi `cp7/integration`; ini belum dibuat oleh paket persiapan.
4. Buat disposable database dari qualified baseline, tanpa egress. Rekam PostgreSQL/Supabase/lockfile/build identity. Hosted/legacy tetap mengikuti batas izin yang sudah ada; tidak deploy dari langkah ini.
5. Ambil katalog definitions/signatures/owners/ACL/triggers/callers serta source hashes yang dibutuhkan. Verifikasi latest function definition, bukan file migration pertama yang cocok.
6. Buat source-read smoke untuk FG, sales lifecycle, WIP source+size, policies, material/capacity, HPP/readiness; catat missing adapter secara spesifik. Inventory static dalam paket adalah start point, bukan kelulusan runtime.
7. Kunci P01 contracts/metric/reason/permissions dan oracle. Verifier menulis expected sebelum melihat implementation baru; validasi fixture cutoff, role, predecessor state dan counts.
8. P02 snapshot coherence vertical slice: satu SKU/size dan dua child batch, satu sales draft, satu cost pending. UI diagnostic bukan fitur rilis; buktikan full facts/no ledger effects/native Auth terlebih dulu.
9. P03/P04 source normalization+WIP. Jalankan O15 dan E02, negative/control branches; baru masuk demand/baseline P05/P06. Setelah contract stable, integration lanes P09–P13 dapat diberi assignment terpisah.
10. Update CURRENT_STATE/packet receipt, jalankan gate T1 yang relevan, serahkan untuk challenge terarah. Jangan membuat T3 baru pada setiap kernel/komponen.

Existing commands yang ditemukan: `npm test`, `npm run build`, `npm run test:security`, `npm run build:cp6-disposable`, dan Playwright configs CP5/CP6. Gunakan sesuai delta/required gate; perintah deploy/Cloudflare upload bukan verifikasi lokal. Runner `cp7` belum ada; P01/P02 membangunnya sesuai case registry, jangan mengklaim perintah baru tersedia dari dokumen ini.

## 3. Instruksi siap diberikan kepada writer P02

> Kerjakan packet P02 pada accepted base hasil P00 dengan contract P01. Tujuan: capture snapshot coherent yang dipakai seluruh CP7. Baca02_BACKBONE_TEKNIS §2–3 dan cases E15/E20/E22. Sumber awal existing: src/config/runtime.ts, src/ConnectedWipStatusPage.tsx, useLaundryQcWorkspace.ts, src/types/database.preconnect.ts, dan resolved catalog P00. Miliki hanya scripts/cp7-src/snapshot/, source facts reader dan tests/cp7/families/snapshot yang ditugaskan; shared types/ACL changes kirim sebagai delta untuk integrator. Jangan menulis ledger, mengubah CP6 business rules, memanggil hosted mutator atau menutup 12HOLD. Expected: coherent concurrent snapshot, strict null/partial rejection, run+cursor complete, actor revocation tested, no business-table changes. Tulis test/oracle/fixture hashes, before/after where applicable, product/tool defect distinction dan remaining limitations. Jika remote writer head bergerak tak dikenal, stop dan lapor. Exit packet adalah T1_FAMILY, bukan CP7 PASS.

## 4. Instruksi siap diberikan kepada Claude sebagai challenger

> Review backbone CP7 dan packet P02–P08 secara read-only. Fokus pada source+size conservation, source reuse across stages/plans/filter, four clocks, no future leakage, quantity versus valuation, dan anti-double-start dari dua draft berbeda. Sebelum membaca implementasi writer, tulis expected untuk O02/O03/O04/O15 dan E06/E10/E11 dari kontrak CP7 rev3, BR V3.1, D01/D06 yang sah. Kritik asumsi/arsitektur yang menambah biaya tanpa menaikkan reliability. Setelah oracle terkunci, baca patch pada SHA yang diberi dan jalankan native probes sendiri bila akses tersedia. Jangan menulis branch writer, jangan mengarang runtime PASS jika alat tidak tersedia, dan jangan mengubah policy owner menjadi preferensi model. Serahkan finding root cause+repro+expected/actual+scope, atau hasil kontrol yang menolak dugaan. Bila kuota terbatas, prioritaskan seam source/time/permission sebelum kosmetik UI.

## 5. Instruksi siap diberikan kepada independent auditor P20

> Audit kandidat CP7 exact SHA/tree/schema/runtime yang dicatat P19. Ini bukan penulisan produk. Mulai dari accepted contracts, requirement registry dan fixture charter; buat scenario/oracle independen sebelum membaca expected writer. Verifikasi candidate capabilities dan full-flow, cari counterexample di luar daftar fix writer, khususnya sales draft lifecycle, WIP uniqueness, pre-SKU matching, two-plan apply, close/late invoice, revoked role, incomplete reader, report revision dan no-ledger-effects. Jalankan native+Auth/HTTP+browser yang relevan sendiri; pisahkan reuse evidence yang dependency-nya masih sah. Baca status per case, bukan summary CI. Jangan mutasi hosted/legacy/production, jangan push writer branch. Output verdict ACCEPT/HOLD/INCOMPLETE dengan exact scope, confirmed defects, limitations, dispositions dan next action. Tidak ada writer self-acceptance atau production GO.

## 6. Keputusan yang sudah ada — jangan ditanyakan ulang

| Topik | Keputusan |
|---|---|
| A+B | Bukti proporsional per keluarga, satu kandidat stabil, full release proof pada paket gabungan |
| WIP sebelum SKU | Diperbolehkan sebagai kandidat fisik bersyarat; bukan FG pasti |
| Actual unknown | Tetap unknown; estimasi/asumsi boleh pada rekomendasi dengan label |
| Draft sale | Availability sudah terpengaruh sekali; no reserved/ATP deduction kedua |
| Stop/Tunda | Terpisah dari master active/sales; tidak auto-reactivate atau auto-cancel WIP |
| AI | Tanya AI V1 copy/open/manual; engine dan report tanpa API AI berbayar |
| Business Report | Satu menu, deterministic narration, reason/dasar hitung per SKU di Stok |
| Timeline dan size | Dated gap dan exact size wajib; late source tidak menutup gap awal |
| Scope CP6 | ALL22/ACC39/LAU36 dan CR D06 yang dimandatkan tetap diselesaikan CP6 |
| CP sequence | CP6 → CP7 → CP7.5 → CP7C → CP8; production GO terpisah |

## 7. Hal yang perlu diisi dari sumber, bukan ditebak

| ID | Ketidakpastian | Tindakan sekarang / kapan mengunci |
|---|---|---|
| CP7-OPEN-01 | Accepted CP6 base dan hasil audit BD/BE final belum tersedia di paket | BLOCKED_UPSTREAM; import acceptance receipt di P00, bukan pertanyaan bisnis ulang |
| CP7-OPEN-02 | Nilai bisnis target layanan/buffer/calendar/capacity nyata | Gunakan fallback kontrak yang berlabel dan fixture terpisah; policy ditinjau saat setup operasional. Tidak menghalangi pembangunan jalur unknown/valid |
| CP7-OPEN-03 | Reconstruction known_at lengkap sebelum snapshot system tersedia | Query audit/history nyata di P02; bila tidak cukup, AS_KNOWN_UNAVAILABLE untuk periode itu |
| CP7-OPEN-04 | Scope role yang boleh melihat global planning/material/cost dan siapa mengubah policy | Petakan permission existing, default deny privilege baru; bawa hanya gap bisnis yang tak punya keputusan |
| CP7-OPEN-05 | Performance database engine pada volume nyata | Spike bounded di P02/P07, profile di P19. ADR teknis alternative hanya jika hasil gagal target dan bottleneck jelas |
| CP7-OPEN-06 | Policy pending nilai pada aksesori/laundry | Ikuti CP6 latest accepted config; pending tetap pending, tidak isi nol/free atau tariff ilustrasi |
| CP7-OPEN-07 | Apakah optional cash forecast/scorecard/order/export baru kelak dipilih | OPTIONAL_NOT_SELECTED; tidak dibangun dan tidak blocker CP7 inti |
| CP7-OPEN-08 | Kanal/schedule/delivery dan SLA/RPO/RTO operasional | Milik CP7C/cutover; seam saja sekarang, no unauthorized egress |

Keputusan teknis terdelegasi (folder, schema shape, grouping, query strategy, test organization) diselesaikan writer dari bukti. Jangan membawa semua pertanyaan teknis ke owner. Konflik kebijakan bisnis yang benar-benar baru harus ditulis konkret dengan contoh dampak, bukan ditutupi asumsi diam-diam.

## 8. Bentuk checkpoint yang harus disimpan penerus

Receipt wajib: packet/version; base/current heads; runtime/schema; allowed paths aktual; changed symbols/dependencies; evidence per case; tests not run+reason; findings status; artifact refs/hash; side effects/cleanup; active request/run IDs; writer ACTIVE/STOPPED/UNKNOWN; next exact command/task; independent gate status. Jangan mencatat secret/DSN/token.

Contoh receipt persiapan v1 di bawah adalah historis; receipt aktif ada di registries/current_state.json:

```text
packet=FRAMEWORK; status=PREPARATION_READY
observed_base=2c2fd5e8e0df5f8ada44402c93f70dbaf0fbbb5b
changed_product_paths=[]; hosted_mutations=0; deployments=0
evidence=document/schema/traceability/arithmetic validation only
ERP_CP7_runtime_tests=NOT_RUN
CP6=HOLD; independent_BE=awaiting; BD=separate audit
next=P00 after accepted CP6 and CP7 mandate
```

## 9. Tanda bahaya yang harus langsung mengubah tindakan

Unexpected writer push → stop writing dan kabari. Wrong database/legacy target → hentikan eksekusi mutatif. Unknown commit outcome → verify dengan request yang sama, jangan blind retry baru. Critical data partial → jangan publish READY/apply. Confirmed financial/stock/HPP correctness bug → tahan affected gate dan perbaiki satu keluarga. Tool failure → INCOMPLETE dan perbaiki lingkungan; jangan memodifikasi oracle untuk menghasilkan PASS.

Dokumen ini tidak membuat pengingat atau pemantauan latar belakang. Pemeriksaan branch berlaku saat sesi melakukan pemeriksaan; successor mengulangnya sebelum menulis.

## Instruksi estafet revisi2

Mulai dari bab06 → owner_delta → family/subpacket → kontrak v2 → relevant source. Buat delta teknis bila usulan dieliminasi, dengan coverage pengganti. Kebutuhan owner tidak dieliminasi diam-diam. P00 wajib menyertakan BD/BE/BF accepted receipts dan last check CP6. Tidak ada otomatisasi/pesan/produk yang diaktifkan oleh framework.

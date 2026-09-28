# Pembagian kerja, Claude/GPT, dan cara berhenti berputar

> **Revisi2 aktif:** baca `06_RUSUK_KEBUTUHAN_OWNER.md` terlebih dahulu. Kontrak AnalysisResult v2 menggantikan bentuk v1; pin/head dan receipt v1 di bab ini adalah sejarah persiapan, bukan accepted base. WA readiness dibawa ke CP7; aktivasi live tetap punya gate tersendiri.

## 1. Diagnosis dari riwayat CP6

Ini kesimpulan proses dari bukti yang dibaca, bukan tuduhan bahwa satu model selalu salah atau model lain selalu benar.

| Pola yang terbukti dalam sejarah | Dampaknya | Perubahan cara kerja CP7 |
|---|---|---|
| Claude mengkritik biaya paket per patch; owner menerima A+B pada 23 Sep | Install/rollback/pins penuh diulang sebelum kandidat stabil | T1 keluarga dahulu, T2 kandidat stabil, T3 sekali per paket yang relevan |
| Definisi aktif tersebar dan sebagian asal schema tidak di repo | Writer menilai fungsi lama, dependency terlewat | P00 resolved symbol registry + dependency map; tidak rebaseline global sebelum CP7.5 |
| Invariant sama dijaga terpisah pada banyak fungsi | Satu jalur diperbaiki, caller lain tetap bocor | Kontrak bersama + test family seluruh caller/trigger, bukan hanya fungsi yang ditemukan |
| GPT menemukan guard AV bisa dilewati variasi SQL dan fixture close salah periode | Tes memberi keyakinan melebihi cakupan | Oracle independen dan fixture qualification sebelum menilai produk; structural guard mendahului regex |
| AU/AV fixtures mengubah ACL/katalog atau seed ganda | Banyak INCOMPLETE yang terlihat seperti masalah produk | Fixture library typed/explicit; setup fingerprints; idempotent seeding; no source slicing/SQL text monkeypatch baru |
| BE sempat mengunci pocket domain untuk import yang tak punya pocket rows | Patch satu keluarga merusak race keluarga lain | Daftar lock/caller impact wajib; negative control untuk jalur tak terkait |
| Harga zero-delta bisa mengubah certainty walau tidak mengubah uang | Membandingkan balance saja melewatkan bug status | Reconcile jumlah/nilai **dan** confidence/readiness/provenance |
| Dokumen/klaim writer dianggap status final | Auditor harus memulai ulang pertanyaan yang sama | Pisahkan implemented, writer verified, independent accepted, release qualified, production authorized |
| Context/kuota/chat macet memutus pekerjaan | Estafet mengulang pembacaan dan berisiko double push | Satu CURRENT_STATE kecil, packet receipt, stopped/unknown worker state, remote-head precondition |

Pendapat Claude di handoff §12 tentang banyak migration/script adalah pengamatan 23 Sep, bukan hitungan source saat ini. Insightnya dipakai tanpa menerima semua saran lamanya: misalnya memajukan CP7.5 atau menunda temuan bukan otomatis keputusan owner. D06 terbaru tetap menentukan scope CP6.

## 2. Riset cara kerja resmi dan penerapannya

Sumber resmi dibaca 27Sep2026 UTC. Tidak ada sesi Claude yang dihubungi/diaktifkan dalam persiapan ini. Ketersediaan kuota Claude mengikuti akun owner; dokumen tidak mengasumsikan kuota sudah pulih.

- OpenAI, **Best practices**: prompt berisi goal/context/constraints/done; petunjuk repo ringkas; testing/review terarah. Penerapan kita: packet card, contract registry, satu entrypoint resume. [Sumber](https://learn.chatgpt.com/guides/best-practices)
- OpenAI, **Git worktrees**: checkout terpisah memungkinkan perubahan paralel. Penerapan kita: proposal branches/worktrees; ini tidak menyelesaikan konflik semantik atau race database. [Sumber](https://learn.chatgpt.com/docs/environments/git-worktrees)
- Anthropic, **Best practices**: eksplorasi dan rencana sebelum code; kriteria yang bisa diuji, bukti nyata, reviewer terpisah. Penerapan kita: oracle sebelum patch dan bukti before/after, bukan hanya persetujuan verbal antarmodel. [Sumber](https://code.claude.com/docs/en/best-practices)
- Anthropic, **Agent teams**: tugas mandiri cocok paralel; banyak dependency/edit file sama menambah overhead dan token. Penerapan kita: parallel hanya saat kontrak stabil dan paths terpisah; core schema/app routing tetap satu integrator. [Sumber](https://code.claude.com/docs/en/agent-teams)

Sumber itu mendukung metode kerja, bukan bukti Claude unggul matematika atau GPT unggul SQL. Pembagian di bawah adalah **keputusan proyek berdasar riwayat dan akses yang tersedia**, tidak bergantung peringkat merek/model atau API berbayar.

## 3. Formasi yang disarankan

| Peran | Penugasan awal yang konkret | Batas dan pengganti |
|---|---|---|
| Lead/integrator | GPT yang memegang estafet ini: baseline, source ownership, kontrak, merge queue, evidence index | Satu-satunya penulis branch integrasi; bukan pengesah independen pekerjaannya sendiri |
| Core domain writer | GPT pada P02–P08, setelah gate CP7 terbuka | Satu logical owner untuk snapshot/WIP/demand/scenario; jangan dibelah per SQL function lintas writer sebelum invariant stabil |
| Challenger desain | Claude ketika tersedia: sumber WIP, model evaluasi, dates/close, whole-family impact dan simplifying proposals | Input awal: kontrak+fixture+pertanyaan, sebelum membaca jawaban writer. Kuota dipakai pada seam mahal ini |
| Contributor terisolasi | Claude/GPT untuk satu packet consumer/vertical slice yang kontraknya stabil | Proposal branch sendiri; file/function allowance; tidak menyentuh canonical contracts/shared routing langsung |
| Independent verifier | Sesi/context terpisah, idealnya model lain; wajib punya akses native/Auth/HTTP/browser yang diperlukan | Reviewer yang ikut menulis packet tidak mengesahkan packet itu sebagai independen. Keterbatasan alat → INCOMPLETE, bukan PASS |
| Owner | Kebijakan bisnis yang betul-betul baru, prioritas, accepted checkpoint dan production GO | Tidak dibebani menjadi pengulang test manual atau perantara setiap detail teknis |

Saat Claude belum tersedia: GPT lanjut desain/implementation yang diizinkan, siapkan oracle/challenge packet, dan pakai reviewer independen yang memang tersedia. Jangan membuat persona “Claude” di sesi GPT lalu menyebut cross-model review. Bila tidak ada verifier yang dapat menjalankan gate, status tetap writer-ready; pekerjaan persiapan tidak perlu berhenti.

**Aturan aktif sekarang tetap satu writer.** Parallel code di bawah merupakan desain mode CP7 setelah mandat/assignment yang jelas; tidak mengaktifkan penulis lain pada branch CP6 sekarang. Read-only review dan penulisan oracle terpisah tidak memberi hak push produk.

## 4. Apa yang aman ditulis bersamaan

| Pasangan kerja | Kapan aman | Tidak boleh bersamaan |
|---|---|---|
| Core snapshot/WIP + reviewer oracle | P01 locked; reviewer tidak mengubah product source | Writer mengubah oracle supaya cocok dengan implementation |
| Sales vertical slice + attendance/payroll vertical slice | Reader/facade/DTO fixed; paths dan functions terpisah | `FinancePages.tsx`, shared ledger mutator, permission catalog atau migration manifest dikerjakan dua pihak |
| Planner/panel + BR template renderer | Result schema/reason catalog fixed; private components masing-masing | Menambah rumus netting/score/stock di masing-masing consumer |
| Native verifier + browser verifier | Same immutable candidate; disposable DB terpisah atau fixture partitions terbukti | Dua runner memodifikasi fixture/schema/actor yang sama |
| Model kernel + report presentation | Model interfaces and result shape frozen | Mengubah metric definitions/semantics hasil di kedua sisi |
| Dokumentasi evidence + implementasi | Dokumentasi mencatat source hash spesifik, tidak mengubah acceptance | Mengklaim dokumentasi head baru sebagai native PASS head itu tanpa parity |

Awal: maksimal dua contribution lanes + satu verifier. Tambah lane hanya jika tugas mandiri, source boundaries jelas, dan integration queue tidak menumpuk. Ini batas engineering usulan untuk menjaga biaya konteks, bukan batas teknis platform.

**Satu orang selalu memegang:** `src/App.tsx`, runtime config, database generated types, auth/access catalog, source/ownership registries, migration/release manifest, canonical contract schema, CI dispatch/qualification rules. Contributor mengirim delta terstruktur untuk file tersebut; lead menerapkan setelah rekonsiliasi. Dua worktree berbeda tetap dapat merusak invariant sama, jadi isolasi Git saja tidak cukup.

## 5. Protokol writer dan merge

Setiap assignment mempunyai packet_id, base SHA/tree/schema fingerprint, allowed files/functions, forbidden effects, dependencies, expected tests, claim version dan satu owner. Tidak ada assignment umum “bereskan backend” untuk dua penulis.

1. Lead mencatat assignment pada `CURRENT_STATE`/registry dan base immutable. Contributor bekerja pada branch proposal berbeda; tidak checkout branch yang sama di dua worktree.
2. Before edit dan sebelum push, cek remote integration head, own head, dirty diff dan kepemilikan path. Unexpected push pada writer aktif → STOP_WRITER_CONFLICT; simpan diff sendiri tanpa push lanjutan, kabari Hansen. Tidak force push/auto-rebase di atas penulis tak dikenal.
3. Contributor melakukan T1 keluarga dan menyerahkan patch SHA, changed symbols, dependency impact, fixture/hash, expected/actual, failure history, rollback impact dan remaining risk.
4. Lead review contract drift/semantic overlap; integrasikan satu proposal dalam satu waktu. Proposal kedua di-refresh ke integration base baru dan mengulang hanya tests yang dependency-nya berubah.
5. Pin candidate untuk T2; auditor tidak menulis branch writer. Satu writer juga saat perbaikan temuan audit.
6. Integrator tidak menganggap absent push = writer lama sudah mati. Estafet membutuhkan checkpoint terakhir dan status STOPPED atau UNKNOWN; bila UNKNOWN, jangan mengizinkan dua canonical pushers.

Worktree/branch dengan proposal bukan izin menulis hosted. Seluruh test mutatif di disposable environment; credentials/egress sesuai scope. Tidak mengubah branch protection, secrets atau permission demi memudahkan koordinasi.

## 6. Paket kerja dan dependency

Kartu lengkap yang dapat dibaca mesin ada di `registries/work_packets.json`: input, output, invariant, paths, owner lane, dependencies, exit test dan trap. Tabel ini ringkasannya. Nomor paket adalah ID stabil, bukan urutan serial wajib bagi semua lane.

| ID | Keluarga hasil | Dependency utama | Bukti keluar |
|---|---|---|---|
| P00 | Receipt CP6, status audit, resolved source/CP map | CP6 accepted + mandat sebelum eksekusi | Accepted base dan scope jelas; sekarang BLOCKED_CP6_GATE |
| P01 | Contract v1, oracle, permission/metric/reason catalogs | P00 | Schema/examples valid; semua requirement punya owner/gate |
| P02 | Capture snapshot, facts, completeness, version/stale | P01 | Concurrent capture coherent; incomplete fail-closed; no ledger write |
| P03 | Identity+production state+lineage normalization | P02 | Brand/size/version, Stop/Tunda, source conservation |
| P04 | WIP matching, stage ETA, shared physical capacity | P03 | Partial/rework/BS/stuck/rewash/reversal family native |
| P05 | Demand observation/availability/cutoff pipeline | P04 | Sale lifecycle once; censored versus zero; no future facts |
| P06 | Baseline target/timeline/size/material/capacity | P05 | Angka golden cases dan unknown/conditional valid |
| P07 | Adaptive kernels, rolling evaluation/version history | P06 | Baseline fallback, fold isolation, reproducibility |
| P08 | Scenario/draft/apply bridge dan anti-double-start | P07,P10 | Native same/different run race, replay, stale/refetch |
| P09 | Procurement/material/gudang connected | P03 | Receive/transfer/issue/invoice/reversal source benar |
| P10 | FG stock/Nota handoff/adjustment connected | P04 | Exact lot/size chronological, non-PO source, no demo fallback |
| P11 | Sales invoice/return/refund/payment connected | P10 | Draft availability, AR/cash/return lifecycle once |
| P12 | Attendance/payroll/Nota/advance connected | P03 | APPROVED/PAID/denominator/reimbursement exact |
| P13 | Finance/HPP/recost/close/report reader connected | P09,P11,P12 | Per-date preflight, zero-delta certainty, archived report |
| P14 | Planner/panel Buat+Bagi/Stok/master status UI | P08,P11 | UX32, parity, form preservation, real browser |
| P15 | Business Report on-demand/history/templates | P13,P14 | Metric parity, source refs, correction/revision, permissions |
| P16 | Manual Reminder connected + condition evaluator | P15 | Episode/attention/source separation; no scheduler egress |
| P17 | Tanya AI V1 | P14 | Clipboard/popup fail paths, authorized prompt, offline core |
| P18 | Full dummy lifecycle and predecessor integration | P09–P17 | Stock/WIP/HPP/GL/payables/cash reconcile end-to-end |
| P19 | Multiuser scale/resilience/operational boundary | P18 | Complete pagination, latency/load evidence, role revoke/recovery |
| P20 | Independent candidate audit | P19 | Exact candidate, own oracle+execution, no material unresolved scope |
| P21 | Release package and receipt for next CP | P20 | Install from representative base, T2 parity, rollback/refusal/restore |

Core A→B→C→D→E→F→G tetap dipertahankan. Integration lanes P09–P13 boleh bergerak saat kontrak data siap; tidak menunggu semua UI planner selesai untuk menemukan sumber penjualan masih demo. Consumer prototypes boleh dibuat dari fixture v1 namun tidak diberi label connected sebelum adapter asli lolos.

## 7. Tiga tingkat bukti A+B yang dipakai

| Tingkat | Trigger | Yang dijalankan | Yang tidak boleh diklaim |
|---|---|---|---|
| Contract readiness | Sebelum packet menulis | Schema, manually computed oracle, fixture validity, dependency/permissions | Ini belum runtime PASS |
| T1_FAMILY | Perubahan keluarga | Unit/pure math bila relevan, native controls+negative+replay+race, targeted Auth/browser pada facade berubah | Bukan independent acceptance atau package-ready |
| T2_CANDIDATE | Semua packet kandidat stabil | Full CP7 flow dan seluruh predecessor evidence terdampak; review status per kasus; independent audit | Jangan menjumlah 35/40/12 sebagai independent test count |
| T3_RELEASE | Kandidat diterima, paket dibuat | Representative accepted/hosted-equivalent base, install/pins, T2 pada installed output, CodeQL/advisors, restore/refusal, cleanup | Bukan hosted deployment atau production GO |

T1 failure safety penting tetap: sebelum/sesudah, bad role, wrong size/source, stale version, ambiguous commit, rollback atomic dan competing mutation jika jalurnya berubah. Yang dihemat adalah ritual package penuh yang tidak relevan dengan micro-change; bukan semua DB testing sampai akhir.

## 8. Aturan menghindari audit berulang tanpa akhir

- Satu finding ledger per **root cause** dengan impacted entrypoints, bukan satu nomor baru untuk tiap gejala. Tetap bedakan scope/case yang belum dibuktikan.
- Reviewer mengunci scenario dan expected dari kontrak dahulu. Melihat test writer boleh setelah independent probe awal; blind tidak berarti mengabaikan keputusan bisnis yang sah.
- Klasifikasi wajib: PRODUCT_DEFECT / CONTRACT_CONFLICT / FIXTURE_DEFECT / TOOL_BLOCKER / EVIDENCE_GAP. Exit CI hijau tidak mengubah INCOMPLETE menjadi PASS.
- Dua perbaikan pada akar yang sama belum menyelesaikan family → pause patch lokal, lakukan root-cause/impact review. Tiga setup/tool retry gagal → ubah metode/qualify environment. Ini aturan diagnosis, bukan batas yang membolehkan bug tersisa dikirim.
- Sebelum matrix mahal: schema/runtime/fixture smoke, before counterexample untuk regression fix, after targeted family, compile/access/ownership yang relevan. Kalau smoke gagal, hentikan matrix itu dengan status setup failure.
- Setelah satu batch findings, patch satu keluarga utuh dan verifikasi semua impacted callers; bukan puluhan putaran satu gejala→full suite.
- Tes tambahan harus membuktikan risiko atau mandat yang belum tertutup. Tidak menambah ratusan permutations tanpa invariant baru. Pairwise/metamorphic membantu cakupan namun tidak menggantikan race nyata.
- Audit final mencari defect lain di luar daftar writer, dengan charter dan budget area yang jelas. Berhenti ketika coverage yang disepakati lengkap, tidak ada confirmed material defect yang belum ditangani, serta semua hasil yang belum pasti punya disposition sah. Jangan mengklaim bug mustahil ada.

## 9. Kapan evidence gugur

Evidence receipt mengikat semantic dependency hash, test/oracle/fixture hash, actor setup, schema/runtime/migration base, command, result dan artifact. Artifact hash melindungi byte; semantic hash tidak boleh dipakai untuk mengabaikan perubahan permission/clock/lock.

| Delta | Minimal requalification |
|---|---|
| Teks label nonsemantik/CSS | Render/interaction pada viewport relevan; domain proof reuse bila closure tidak berubah |
| Parser/DTO/API field | Contract+negative parse, consumers, real HTTP, Auth redaction |
| Query/filter/pagination/cache | Snapshot completeness, permission aggregates, temporal/stale, large dataset |
| WIP/source identity/matching | Full WIP family+size+conversion/rework/claims; downstream netting/report parity |
| Forecast/policy/ranking | Frozen math vectors+rolling no-leakage+scenario+reason consistency |
| Command/lock/recovery | Full affected writer family, cross-domain races, refetch/timeout and predecessor controls |
| Financial/date/close/recost | Per-date GL/HPP/AR/AP, late invoice, closed period, historical reports and close race |
| Package/baseline/schema/ACL | Install/restore/refusal + affected T2 on installed runtime; independent disposition |

Documentation-only head boleh merujuk test product head asal beserta parity proof. Jangan memindah label PASS ke hash baru tanpa menjelaskan apa yang identik. Mandatory old source guards dipertahankan; successor qualification harus eksplisit, bukan guard dilonggarkan.

## 10. Paket estafet saat kuota hampir habis atau chat macet

Setelah satu packet atau perubahan arah, update satu receipt: head/tree/schema, active packet, contract version, owned paths, request/run IDs yang belum selesai, PASS/FAIL/INCOMPLETE per case, known defects, next exact action, writer status STOPPED/ACTIVE/UNKNOWN. Simpan patch/checkpoint sebelum memulai matrix panjang atau membuka packet baru.

Jangan menunggu konteks hampir penuh baru menulis master ribuan baris. Start berikut membaca CURRENT_STATE → packet → relevant source sections. Histori besar immutable diarsipkan terpisah. Kalau sesi hilang tanpa stopped receipt, successor read-only reconcile remote/worktree/evidence dahulu; writer tak dikenal tetap memicu stop dan pemberitahuan.

Metrik proses yang dicatat: packet lead time, first-family-pass rate, waktu setup versus waktu tes bisnis, rerun tanpa dependency change, defects lolos T1 ke T2, recurrence root cause, queue integrasi, biaya/kuota bila tersedia. Tidak ada target palsu “100% sembuh dalam N sesi”; arah perbaikan diukur dari pekerjaan ulang yang berkurang tanpa menurunkan gate.

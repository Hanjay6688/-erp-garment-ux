# Handoff Claude → ChatGPT — AU-R1 dan kandidat successor AV

Tanggal: 23 September 2026 (WIB). Writer: Claude Code (sesi cloud). Peninjau berikutnya: ChatGPT.
Dokumen ini adalah checkpoint utuh sesuai format bagian 8 handoff AU-R1. Tidak ada yang diringkas dari bukti; semua angka di bawah dapat ditelusuri ke run, commit, atau file yang disebut.

> Mulai dari AU `ca7f095`. Writer AU selesai, bukti tersimpan cocok, penerimaan independen belum ada. CP6 tetap HOLD, 12 HOLD historis dipertahankan, production tidak disentuh. Kandidat AU-R1 dari tinjauan chat **sudah terbukti native** dan sebuah kandidat successor **AV** sudah dibuat, diuji native, dan dibekukan untuk ditinjau. AV **bukan** penerimaan independen dan **belum** berada di cabang kompetisi. Di luar AU-R1, **AUD-S06** (tutup buku mengabaikan RECALC_PENDING/BLOCKED) juga terbukti native. Temuan ini belum dipatch karena kontraknya menuntut preflight per tanggal satu keluarga dengan AUD-B04; rancangannya ada di bagian 10.1. Master pulih, perubahan pulih, dan addendum CP7 sudah dibaca penuh; kaitannya dengan CP7 ada di bagian 10.2.

---

## 1. Identitas, writer, freeze

| Hal | Keadaan |
| --- | --- |
| Repo | https://github.com/Hanjay6688/-erp-garment-ux |
| Cabang kerja Claude | `claude/new-session-deapao` (dibuat dari `ca7f095`, bukan dari main) |
| Cabang kompetisi | `competition/cp6-j-closure-20260911` tetap `ca7f09556397801c50a2277bdb65b1bf019f9a05`, **tidak ditulis** |
| Main | `557005e…` tidak disentuh |
| Commit Claude | `897bb68` probe → `9d15cfd` kandidat AV → `bb4009c` race dua sesi (**AV beku**) → `3f2804f` probe observasi AUD-S06 → `dcbfe62` bukti native → commit handoff ini (hanya dokumen) |
| Tree `bb4009c` | `10c2040710534ee555268f547fb99d89942cb143` |
| Freeze | Writer Claude **berhenti** setelah commit dokumentasi. Jangan ada writer lain di `claude/new-session-deapao` tanpa serah-terima eksplisit. |
| Hosted Supabase Enteng | Hanya dibaca: `list_migrations` = 70 migration, terakhir `20260904232442 erp_v2_6_20_cp6_laundry_qc_fg_authoritative`. Cocok dengan catatan historis; 47 successor CP6 (20a…20au) belum ada di hosted. Tidak ada mutasi. |
| Legacy `vlxdhpkjeevubjxexnfo` | Tidak diakses, tidak dimutasi |
| Cloudflare | Hanya dibaca: satu Worker `erp-garment-ux`, modified `2026-09-23T05:35:04Z`. Tidak ada deploy. |
| production_go | false |
| Penerimaan independen AU / AV | false / false |

Orientasi yang sudah diverifikasi: paket `ERP_Claude_Kode_dan_Konteks_20260923` 1335/1335 file cocok manifest; bundle Git lengkap; clone HEAD `ca7f095`, tree `5b5f12c`; paket Ramping `SHA256SUMS_RAMPING.txt` lolos; bootstrap AC `eeb76d0c…` cocok pin. `VERIFY_HANDOFF.py`/`VERIFY_AU.py` tidak dijalankan karena tidak ikut paket kecil/ramping (**NOT_TESTED**).

## 2. Masalah bisnis dan dampak (AU-R1)

`erp.edit_product_identity_effective` (AU) membuat successor untuk SKU yang sudah punya histori. Batas waktunya hanya memeriksa `fg_lots.produced_at >= v_eff`. Fakta fisik NEW_STOCK lain yang juga terikat identitas produk, yaitu `bs_cases.physical_at` dari laundry receipt BS dan dari QC yang seluruhnya BS, tidak diperiksa. `v_eff` boleh mundur sampai 5 menit dan `physical_at` boleh maju sampai +5 menit, jadi jendelanya nyata walaupun sempit.

Akibatnya versi lama berakhir **sebelum** BS NEW_STOCK yang sudah tercatat padanya. Urutan terbalik (edit dulu, lalu BS) ditolak oleh guard periode produk, sehingga keadaan akhir bergantung pada urutan operasi. Tidak ada uang yang hilang langsung, tetapi lineage identitas BS menjadi tidak konsisten: as-of CP7-A, resolusi BS, dan rework dapat membaca versi yang periodenya sudah berakhir. Ini adalah P0 "AU physical timestamp cutoff" di `STATUS_DAN_TODO.csv` baris 4.

Eksposur hari ini kecil karena RPC edit belum dipanggil frontend. Eksposur akan terbuka ketika UI master identitas dibuat.

## 3. Kontrak yang dipakai sebagai expected

- `01_HANDOFF_UTAMA.md` §8.1: "Riwayat identitas efektif harus linear…". §8.6: "Laundry BS mengikat identitas pada receipt fisik." §8.7: "Klasifikasi size/product harus exact dan sesuai masa berlaku fisik."
- `ERP_Takeover_20260923.md` §7: "Identitas produk efektif bertanggal, linear, tidak boleh fork/overlap atau diedit setelah dibuat untuk mengubah histori."
- `ERP_GARMENT_MASTER_CONTEXT_2026-09-06.md`:313: "Fork, overlap, detached version, missing root, atau retroactive boundary move harus fail-closed."
- `04_BUKTI/AU_BACA_LANGSUNG/01_TEMUAN_DAN_PERBAIKAN.md`:19: "Successor tidak boleh memotong timestamp produksi yang sudah tercatat."
- Simetri: `erp.assert_product_identity_time(...,'NEW_STOCK')` menolak fakta baru pada versi yang sudah berakhir. Karena itu keadaan yang sama harus ditolak apa pun urutannya.

**Bagian yang DITAHAN (HOLD_CONTRACT):** apakah BS manual `LEGACY`/`OUT_OF_NOWHERE` (`erp.create_manual_bs_case_v2`) dan BS opening (`post_opening_balance`) ikut membatasi successor. Pencarian kontrak di takeover, handoff utama, runbook, dan status, ditambah pembacaan **penuh** master pulih, perubahan pulih, dan addendum CP7 (bagian 10.2), **tidak menemukan keputusan** (STATUS baris 4 masih REVIEW_REQUIRED; HANDOFF_UTAMA:387). Yang ada hanya petunjuk; lihat bagian 10.2. Kedua producer itu tidak memanggil assert identitas, jadi urutan terbalik pun tidak ditolak. Perilaku AU untuk keduanya **tidak diubah**. Ini keputusan owner yang masih terbuka, bukan kelalaian.

## 4. Bukti sebelum perbaikan (native, AU beku)

Runtime: GitHub Actions `ubuntu-24.04`, Supabase CLI 2.116.0, PostgreSQL image 17.6.1.165, Python 3.12, psycopg 3.2.10. Semua langkah install AC→AD…AN disalin **tanpa perubahan** dari `.github/workflows/cp6-au-qualification.yml`; kesamaannya diverifikasi programatik. Writer checkout = `ca7f095`; AS/AT/AU dipasang oleh runtime closed-admission mereka sendiri; tidak ada fungsi yang dipatch.

Run [35837408181](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35837408181) (commit `897bb68`), job `107104064445`, artifact `10739778362`. Direproduksi lagi di run [35838014072](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35838014072) fase before.

| Kasus | Status | Observasi (run 35837408181) |
| --- | --- | --- |
| CUTOFF:LAUNDRY_BS | **COUNTEREXAMPLE** | Edit diterima; versi lama berakhir 08:30:47.07Z; BS laundry NEW_STOCK 08:31:17.07Z tetap pada versi lama (`new_stock_bs_after_end=1`) |
| CUTOFF:QC_ALL_BS | **COUNTEREXAMPLE** | Sama untuk QC seluruhnya BS (08:30:47.83Z vs 08:31:17.83Z) |
| CUTOFF:QC_GOOD | CONTROL_PASS | Ditolak oleh cutoff `fg_lots` lama |
| CUTOFF:BS_BEFORE_EFFECTIVE | CONTROL_PASS | Edit sesudah fakta diterima, tanpa over-block |
| CUTOFF:MANUAL_BS | HOLD_CONTRACT | Diterima; `untracked_bs_after_end=1` (perilaku AU, kontrak terbuka) |
| REVERSED:LAUNDRY_BS | CONTROL_PASS | Ditolak: "Laundry BS product must be active at physical receipt time…" |
| REVERSED:QC_ALL_BS | CONTROL_PASS | Ditolak: "Final SKU must be active at physical QC time…" |
| AU master 15 / AT temporal 16 | PASS / PASS | Baseline runtime |

Semua kasus berjalan lewat sesi `authenticated` biasa dan RPC publik (laundry/QC), dengan fixture rantai AL rework yang sudah dipakai regresi AU (kerja → jahit → laundry → QC). Setiap kasus memulihkan seluruh boundary. Primary AN tidak berubah dan clone tersisa 0.

## 5. Perbaikan: kandidat successor AV

File: `supabase/migrations/20260923090000_erp_v2_6_20av_cp6_new_stock_physical_cutoff.sql` (SHA256 `3bd2f94f…6199`), rollback `…rollback.sql` (`bdff2769…2e14`), pins `docs/evidence/cp6-av-pins.json` (`0f9a5e15…1f2e`). Semua dibangkitkan oleh `scripts/cp6_au_r1_build.py` dari model AU yang dipin (bukan tulisan tangan).

Perubahan produk (hanya 3 objek katalog):

1. **Baru** `erp.latest_new_stock_physical_at_v1(uuid)`, SQL STABLE, ACL `{postgres=X/postgres}`. Ini sumber tunggal waktu fisik NEW_STOCK per versi:
   - seluruh `fg_lots.produced_at`. Cakupan AU dipertahankan dan **tidak dilonggarkan**, termasuk lot opening/rework/impor, yang tetap konservatif;
   - `bs_cases.physical_at` hanya bila lineage-nya immutable dan berasal dari producer yang menjalankan assert NEW_STOCK: `qc_item_id` atau `source_laundry_bs_allocation_id`. `untracked_type` tidak dipakai karena dapat dikosongkan oleh `classify_bs_case_v2`.
   - Baris CANCELLED/REVERSED tetap dihitung (konservatif, sama seperti `fg_lots`).
2. **Diganti** `erp.edit_product_identity_effective(...)`. Hanya pernyataan cutoff yang berubah; owner/ACL tetap:
   ```diff
   -  if exists(select 1 from erp.fg_lots l where l.product_id=p.id and l.produced_at>=v_eff) then
   -    raise exception 'Tanggal efektif SKU akan memotong histori produksi yang sudah tercatat';
   +  v_last:=erp.latest_new_stock_physical_at_v1(p.id);
   +  if v_last>=v_eff then
   +    raise exception 'Tanggal efektif SKU akan memotong histori produksi yang sudah tercatat (fakta fisik stok baru terakhir %). Pilih tanggal efektif sesudahnya.',v_last;
   ```
   Awal pesan lama dipertahankan. Owner kini melihat jam fakta terakhir agar bisa memilih tanggal efektif yang sah.
3. **Baru** `erp.assert_new_stock_cutoff_coverage_v1()`, plpgsql STABLE, ACL `{postgres=X/postgres}`. Ini guard katalog. Ia gagal bila:
   - fungsi apa pun di `erp`/`public` memanggil `assert_product_identity_time` dalam mode NEW_STOCK, default, atau dinamis (fail-closed), lalu `insert into` tabel berkolom FK produk yang tidak ada di cakupan helper (`bs_cases`, `fg_lots`) atau di daftar turunan eksplisit (`fg_inventory_balances`: cache saldo tanpa waktu fisik sendiri);
   - body helper tidak lagi membaca persis `{bs_cases, fg_lots}` (`NEW_STOCK_CUTOFF_HELPER_SCOPE_DRIFT`);
   - fungsi edit tidak lagi memanggil helper (`NEW_STOCK_CUTOFF_CONSUMER_DRIFT`).

   Guard dijalankan saat install dan pada setiap verifikasi runtime kandidat. Batasnya: hanya mendeteksi `insert` langsung di body producer, tidak mengikuti panggilan fungsi bertingkat. Ia bekerja di katalog native, sehingga fungsi dari skema dasar yang tidak ada di migration repo, misalnya `erp.validate_laundry_bs_product_allocation()`, tetap terbaca.

Paket dibuat dengan pola AU:
- closed admission dan drain;
- predecessor harus katalog AU terpasang persis, 7156 objek, fingerprint `ccb46dce…`. Model builder menghasilkan nilai yang identik dengan pin "AU_INSTALLED" milik AU sendiri;
- seluruh kapsul dan platform AO…AU dicek ulang;
- katalog terpasang persis 7158 objek;
- kapsul privat berisi definisi AU untuk pemulihan pre-use yang persis, dan rollback ditolak setelah ada pemakaian.

Timestamp migration dipilih builder, bukan dibuat Supabase CLI, sehingga provenance CLI **NOT_TESTED**.

Peta family native (katalog `ca7f095`, sama sebelum/sesudah):

| Pemanggil assert identitas | Mode | Insert |
| --- | --- | --- |
| `erp.post_laundry_receipt(uuid)` | NEW_STOCK | bs_cases, wip_stage_events |
| `erp.post_qc(uuid)` | NEW_STOCK | bs_cases, fg_lots |
| `erp.post_product_conversion(uuid)` | EXISTING_STOCK + NEW_STOCK | fg_inventory_balances, fg_lots, hpp_version_components, hpp_versions, product_conversion_allocations |
| `erp.validate_laundry_bs_product_allocation()` | NEW_STOCK | — (trigger validasi) |

Penulis `fg_lots`: initial-import WIP, opening, conversion, QC, rework. Penulis `bs_cases`: BS manual v2, laundry receipt, opening, QC.

## 6. Bukti sesudah perbaikan (native)

Run [35838014072](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35838014072) (commit `9d15cfd`), job `107106040737`. Fase before dan after berjalan pada commit yang sama, masing-masing di clone AN baru.

| Kelompok | Before | After |
| --- | --- | --- |
| CUTOFF:LAUNDRY_BS | COUNTEREXAMPLE | **PASS**: ditolak "…(fakta fisik stok baru terakhir 2026-09-23 08:38:47.29+00)…" |
| CUTOFF:QC_ALL_BS | COUNTEREXAMPLE | **PASS**: ditolak, jam 08:38:48.24+00 |
| CUTOFF:QC_GOOD | CONTROL_PASS | CONTROL_PASS (pesan baru) |
| CUTOFF:BS_BEFORE_EFFECTIVE | CONTROL_PASS | CONTROL_PASS (tetap diterima) |
| CUTOFF:MANUAL_BS | HOLD_CONTRACT | HOLD_CONTRACT (sengaja tidak berubah) |
| REVERSED ×2 | CONTROL_PASS | CONTROL_PASS |
| COVERAGE_GUARD NEW_STOCK / DEFAULT / DYNAMIC | NOT_APPLICABLE | CONTROL_PASS: `NEW_STOCK_CUTOFF_COVERAGE_MISSING: erp.cp6_au_r1_sample_post(uuid,text) -> erp.cp6_au_r1_sample_facts` |
| COVERAGE_GUARD EXISTING_STOCK | NOT_APPLICABLE | CONTROL_PASS (lolos, bukan sumber cutoff) |
| AU master 15 | PASS | PASS |
| AT temporal 16 | PASS | PASS |
| Paket AV | — | 2 siklus install → open-rollback ditolak → restore persis ke AU (data, riwayat, katalog) pada 71 tabel berisi; install akhir; runtime 650 fungsi / 7158 objek |
| Rollback sesudah pemakaian | — | Ditolak `AV_POST_USE_ROLLBACK_REFUSED`; data dan platform tidak berubah |
| Cleanup | primary tetap, clone 0 | primary tetap, clone 0 |

Verdict writer: `CANDIDATE_WRITER_PASS`. Ini bukan penerimaan independen.

### Race dua sesi

Run [35838611997](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35838611997) (commit `bb4009c`, **AV beku**), job `107108022412`. Run ini juga mengulang semua kasus sequential di bagian 4 dan 6 dengan hasil identik. Race memakai salinan clone terpisah (`cp6_au_r1_race`): fixture di-commit hanya di salinan itu, dan salinan dihapus di `finally` (`race_database_remaining=0`). Salinan diverifikasi runtime-nya sebelum GRANT USAGE fixture.

| Jadwal | Before (AU) | After (AU+AV) | Kontensi yang teramati |
| --- | --- | --- | --- |
| RACE:BS_FIRST:COMMIT | **COUNTEREXAMPLE**: edit pertama gagal cepat `POCKET_PERIOD_BUSY`; retry setelah BS commit **diterima**, dan BS NEW_STOCK tertinggal setelah akhir versi | **PASS**: retry ditolak "…(fakta fisik stok baru terakhir 2026-09-23 08:46:37.94+00)…" | FAIL_FAST |
| RACE:BS_FIRST:ABORT | PASS: successor dibuat, tanpa BS | PASS | FAIL_FAST |
| RACE:MASTER_FIRST:COMMIT | PASS: BS ditolak guard periode | PASS | BLOCKED (kunci baris produk via FK KEY SHARE; `pg_blocking_pids` terverifikasi) |
| RACE:MASTER_FIRST:ABORT | PASS: BS tercatat, tanpa successor | PASS | BLOCKED |

Di setiap jadwal: tepat satu pihak menang, tidak ada baris otorisasi yang tersisa, dan kontender yang kalah tidak meninggalkan efek. Kedua pola kontensi (fail-fast try-lock dan blocking baris) menghasilkan keadaan akhir yang sesuai kontrak pada AV.

## 7. Tes yang benar-benar dijalankan dan batasnya

- Native (PostgreSQL 17.6.1.165): seluruh isi bagian 4, 6, dan race di atas.
- Smoke lokal PostgreSQL 16 (bukan bukti native): format kanonik `pg_get_functiondef` ketiga fungsi sama persis dengan teks yang dipin; semantik helper benar (manual diabaikan; laundry/QC dihitung; tanpa fakta = null); guard menolak producer baru tak tercakup, mode dinamis, drift helper, dan drift consumer; EXISTING_STOCK dan tabel non-produk lolos.
- Simulasi tata letak CI lokal: pin kandidat ter-resolve dari checkout writer `ca7f095`; delta model AU→AV tepat 3 fungsi.
- **REUSED_EVIDENCE**: 500 kasus asli AU, 174 AR, 34 AS, browser, CodeQL, dan advisor dari run AU 35822980561. Semua itu berlaku untuk `ca7f095`, bukan untuk AU+AV.
- **RERUN_REQUIRED sebelum AV dianggap siap digabung**:
  - regresi 500 kasus asli pada runtime AV;
  - CodeQL pada commit final;
  - advisor keamanan delta;
  - browser/Auth nyata. UI master identitas belum ada, jadi jalur browser untuk edit memang belum tersedia.
- **NOT_TESTED**: provenance CLI migration; retry edit dengan timestamp default (tanpa UUID); referensi produk di dalam JSON/ekspor.

## 8. Kegagalan dan hambatan yang dipertahankan

1. Push pertama `897bb68` ditolak 403 karena GitHub App belum terhubung. Hansen menyambungkan ulang, lalu push berhasil. Tidak ada efek pada repo selama ditolak.
2. Proxy container menolak host blob Azure, sehingga artifact GitHub (bootstrap AC dan artifact probe) tidak bisa diunduh dari sesi ini. Bootstrap diambil dari paket Ramping (hash cocok). Bukti probe diambil dari log job, yang memuat JSON utuh setiap kasus, dan disimpan di `docs/evidence/cp6-au-r1/`.
3. Docker daemon tidak dapat dijalankan di container. Replay native hanya lewat GitHub Actions.
4. Bug harness saya sendiri yang tertangkap sebelum push: path AV relatif terhadap cwd writer (tidak akan ketemu di CI). Diperbaiki ke root auditor; pin tetap menyimpan path relatif repo.
5. Regex `fact_writers` di probe awal hanya menangkap `insert into erp.X(`. Diperbaiki menjadi batas kata sebelum run kandidat.
6. Parser source saya melewatkan `erp.validate_laundry_bs_product_allocation()` karena fungsinya berasal dari skema dasar, bukan dari migration repo. Katalog native menangkapnya. Pelajarannya: peta family harus dari katalog native.

## 9. Cleanup

Setiap run: primary AN tidak berubah (snapshot sama), clone `cp6_rollback` tersisa 0, dan database race dihapus di `finally`. PG16 lokal hanya berisi DB smoke di scratchpad sesi dan tidak terhubung ke apa pun. Tidak ada mutasi hosted, legacy, main, Cloudflare, atau cabang kompetisi.

## 10. Audit risiko lain (di luar AU-R1)

Rujukan baris di bagian 10: `L<n>` = `02_KONTEKS/ERP_V3_2_Master_Pulih_20260923.md` (paket Ramping), `A:<n>` = `02_KONTEKS/ERP_V3_2_Perubahan_Pulih_20260923.md`, "addendum baris n" = `02_KONTEKS/ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md`.

| ID | Temuan | Status bukti | Tindakan |
| --- | --- | --- | --- |
| R-P0-DEL | Kekhawatiran DELETE langsung `erp.products` + daftar hardcode guard + FK CASCADE (`accessory_bom_versions`, `product_price_versions`) | **RECONCILED native**: `authenticated` SELECT/INSERT/UPDATE tanpa DELETE; `anon` tidak punya hak; hanya `service_role` yang punya DELETE (dan guard memang di-bypass untuk role itu). RLS aktif, policy `internal_all` untuk OWNER/ADMIN/STAFF. | Tidak dapat dieksploitasi role aplikasi. Risiko `service_role` tetap urusan pengelolaan key. |
| R-P0-REF | Referensi produk di luar FK | **Sebagian**: pemindaian native kolom bernama `*product*` tanpa FK hanya menemukan `product_identity_mutation_context_v1.product_id` (tabel otorisasi privat). Referensi di dalam JSON (payload impor, `audit_logs.new_data`, cache idempotensi) dan dokumen eksternal **tidak** tercakup oleh pemindaian nama. | Perlu tinjauan semantik JSON; bukan klaim bersih. |
| R-OBS-REWORK | `post_rework_completion` menulis `fg_lots` untuk produk BS tanpa assert identitas. Cutoff (AU maupun AV) menghitungnya, jadi rework lalu edit ditolak, sedangkan edit lalu rework diterima. | STATIC ONLY | Arah ini fail-closed (over-strict), bukan kerusakan data. Pertanyaan kontrak: apakah GOOD hasil rework termasuk NEW_STOCK atau EXISTING_STOCK? Tidak diubah. |
| R-RETRY | Retry edit tanpa request UUID dengan timestamp default ditolak "Versi SKU sudah punya successor" | Diketahui (AU) | Aman tetapi membingungkan. Saran untuk UI nanti: tangkap `p_effective_from` sekali, simpan di envelope, dan kirim ulang nilai yang sama. |
| **AUD-S06** | Tutup buku tanpa preflight blocker | **COUNTEREXAMPLE native** (bagian 10.1) | Pekerjaan backend CP6 (L1730). Rancangan bertahap di 10.1; belum dipatch (alasan di 10.1) |
| R-CONF | `data_confidence` tidak dihitung per tanggal: pemeriksaan kritis memakai integritas saat ini, antrean recost dihitung global | STATIC (source AC, baris dirujuk di 10.1) | Satu keluarga dengan AUD-B04/S06. Jangan jadikan READY global sebagai satu-satunya gate close. |
| R-LOCK | Lock order edit vs producer | Analisis source + race di atas | Edit dan assert NEW_STOCK sama-sama memakai try-lock global `POCKET_HPP_PERIOD_V1` (fail-fast). Jalur laundry dapat menunggu kunci baris produk lewat FK KEY SHARE; race membuktikan keadaan akhir tetap sah. |

Selain AU-R1 dan AUD-S06, tidak ada temuan material lain yang terbukti native dalam putaran ini. Area yang **belum** ditinjau mendalam oleh Claude:
- 12 HOLD kalender;
- keluarga as-of/report (AUD-B04), serta close selain blocker recost: absensi/payroll/GRNI dan race posting vs close;
- cakupan ALL impor;
- aksesori internal/retur;
- laundry paket/komponen/invoice susulan;
- reminder V2;
- hipotesis dari pembacaan kontrak yang belum diuji native (daftar di bawah).

Master pulih, perubahan pulih, dan addendum CP7 kini sudah dibaca penuh (bagian 10.2). Hipotesis dari pembacaan itu, belum diuji native dan bukan temuan:
- H-OPEN-WIP: output WIP opening membuat "lot barang jadi PRODUCTION, mutasi stok QC_GOOD" (L370). Peta family native (bagian 5) menunjukkan penulis `fg_lots` impor WIP tidak memanggil `assert_product_identity_time`. Apakah masa berlaku identitas divalidasi dengan cara lain belum dicek. Polanya sama dengan rework: lot ini dihitung oleh cutoff, tetapi tidak dicek terhadap masa berlaku versi.
- H-FILED: recost, invoice terlambat, atau reversal yang menyentuh periode tertutup harus lewat penyesuaian terkendali tanpa menimpa laporan yang sudah diajukan (L4216, L5100, A:1041). Jalur close lalu recost perlu dibuktikan.
- H-UNKNOWN: unknown bisa hilang di `coalesce`/agregasi laporan (L3825, L4155).
- Item register 33 yang disebut ulang oleh kontrak: S05 (batas 200 PO/100 draft vs kelengkapan CP7 L7028), A04 (parser WIP missing→0), S02/S04, B01. Status item-item ini mengikuti register dan tidak diuji ulang oleh Claude.

### 10.1 AUD-S06: tutup buku mengabaikan status laporan resmi (terbukti native)

**Kontrak:** HANDOFF_UTAMA §8.10 menyatakan "Close memerlukan satu preflight authoritative dan recheck atomik terhadap blocker… READY/RECALC_PENDING/BLOCKED bermakna; … queue belum selesai tidak boleh menjadi final palsu". Master S06 menempatkannya sebagai P1 sebelum izin tutup buku produksi. Sebelumnya statusnya hanya "SOURCE + CONTRACT_GAP; belum native refusal test".

**Source (AU `ca7f095`):** `erp.close_accounting_through(date,text)` memeriksa role, alasan, dan tanggal, mengunci `accounting_period_control FOR UPDATE`, mengubah `closed_through`, lalu me-refresh checkpoint biaya bahan. Tidak ada pemeriksaan antrean recost atau pemeriksaan kritis. UI "Tutup buku" masih simulasi (`src/FinancePages.tsx`), jadi belum ada jalur publik hari ini.

**Bukti native:** run [35839202630](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35839202630) (commit `3f2804f`), job `107109943350`, pada AU beku lewat RPC owner biasa. Baris antrean adalah fixture administratif berlabel.

| Kasus | `data_confidence.status` laporan resmi sebelum close | Close | `closed_through` |
| --- | --- | --- | --- |
| AS_IS (antrean kosong) | READY | diterima (kontrol) | 2026-08-31 → 2026-09-22 |
| PENDING | **RECALC_PENDING** (`V268_COST_RECALC_PENDING`) | **diterima** | 2026-08-31 → 2026-09-22 |
| RUNNING | **RECALC_PENDING** | **diterima** | sama |
| FAILED, attempt 1 | **RECALC_PENDING** | **diterima** | sama |
| FAILED, attempt 3 (habis) | **BLOCKED** (`V268_COST_RECALC_EXHAUSTED`, critical) | **diterima** | sama |

Semua boundary pulih, primary tidak berubah, clone 0. Untuk antrean recost, hipotesis "laporan READY palsu" **ditolak**: laporan jujur menyebut RECALC_PENDING/BLOCKED, tetapi close tidak membacanya. Ini **bukan** bukti bahwa confidence benar secara historis (lihat temuan source di bawah dan AUD-B04).

**Temuan source tambahan (STATIC, AU `ca7f095`): `data_confidence` tidak dihitung per tanggal.** Di `erp.get_owner_financial_snapshot_v2` (`supabase/migrations/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql:2699`, tidak diganti sesudah AC):
- `v_critical` berasal dari `erp.run_v268_financial_report_checks()` tanpa argumen tanggal (:2827, :2831), jadi memakai integritas saat ini;
- `v_pending` menghitung seluruh `cost_recalc_queue` yang terbuka secara global (:2842), bukan hanya yang menyentuh periode yang ditutup;
- satu-satunya pemeriksaan yang dibatasi periode adalah jembatan pendapatan penjualan (`V2620D_PERIOD_SALES_REVENUE_BRIDGE_MISMATCH`).

Akibatnya gate "tolak kecuali READY" memiliki dua sisi:
- **terlalu ketat**: recost terbuka untuk PO lain atau tanggal sesudah periode tetap menahan close periode lama;
- **tidak cukup**: integritas hari ini bisa bersih, sedangkan per tanggal historis tidak konsisten. Ini tepat pola AUD-B04 (master pulih L1404: "qty0/nilai7, FG51/COGS34 namun confidence READY").

Kontrak menuntut hal yang sama:
- L3825: "Scope report dan tanggalnya harus sama dengan scope pemeriksaan";
- L4897 dan L5100: jangan memberi READY as-of memakai integritas hari ini saja;
- L6057: "semua blocker yang diwajibkan owner harus terbaca dari snapshot/tanggal yang sama".

**Kontrak S06 setelah pembacaan penuh master pulih** (dikutip langsung; baris diverifikasi):
- L3859 "Close membutuhkan preflight lengkap dan recheck atomik seluruh blocker … prioritas sebelum close production".
- L5628 "Queue gagal, absensi/payroll yang belum lengkap, GRNI dan integritas stok/jurnal harus ditangani dalam kontrak final close." **Kategori** blocker sudah ditetapkan kontrak; **ambang/perlakuannya** belum ada keputusan owner.
- L6057 "Satu preview preflight dan pengecekan ulang atomik sebelum final close; semua blocker yang diwajibkan owner harus terbaca dari snapshot/tanggal yang sama."
- L6066 acceptance: "Queue PENDING/FAILED, attendance kosong, payroll belum approved, jurnal/stock mismatch …, izin tidak sah, dua sesi posting vs close. Pastikan jalur public facade dan backend identik."
- L1718 "AUD-S06 | OPEN … CP6 bagian blocker tanggal/report yang terkait; full UI/preflight close pada wiring CP7, sebelum aktivasi finance/close dan CP8."
- L1730 "bug report backend CP6 tetap AUD-B04/S06". L1400: tidak boleh "memindahkan blocker lama ke CP7 agar CP6 tampak selesai". Artinya **perbaikan backend S06 adalah pekerjaan CP6**, bukan CP7.
- L1194 "Tutup satu keluarga recost–GL–HPP–as-of–confidence–close setelah diputus". S06 dan B04 adalah satu keluarga.
- ERP-DEC01 **sudah diputus** owner 22 September (L1056–L1065): koreksi pada periode terbuka mengikuti **tanggal invoice**, dan harus konsisten sampai "laporan menurut tanggal, dan indikator kesiapan data". Statusnya "belum diterapkan/diuji". Dokumen arsip yang masih menyebut ERP-DEC01 terbuka (misalnya L4461) sudah tergantikan.
- Keputusan yang masih terbuka: LAU-DEC04, yaitu close/penjualan ketika harga laundry UNKNOWN (L4475, L1754). Ini calon blocker close keempat.

**Mengapa belum dipatch di putaran ini:**
1. Fixture regresi 500 kasus asli memanggil `close_accounting_through` di tengah skenario, sehingga gate baru dapat mengubah hasil oracle lama. Buktinya butuh kualifikasi 500 kasus pada runtime successor. Pemetaan statis titik pemanggilan (grep `scripts/`, belum dieksekusi, jadi **NOT_TESTED** apakah antrean kosong saat itu):
   - modul pemanggil yang **terjangkau** dari graf import harness (`cp6_successor_regression`, tiga modul `cp6_v2620al_*`, `cp6_final_ak_independent`, `cp6_ar_trial`): `cp6_final_crossflow_review.py:96`, `cp6_final_gap_native.py:118`, `cp6_aa_invoice_partial_audit.py:331` (`invoice_case`), `cp6_pocket_period_trial.py:93`, `cp6_pocket_fabric_trial.py:51`, `cp6_initial_import_production_trial.py:101` ("Cutover recost date closed"), `cp6_initial_import_receipt_trial.py:145`, `cp6_initial_import_advance_trial.py:87`;
   - pemanggil lain di luar graf itu (tidak memengaruhi 500 kasus, tetapi memengaruhi probe/kualifikasi lama bila dijalankan ulang): `cp6_as_cases.py:96`, `cp6_initial_import_prepayment_trial.py:80`, `cp6_initial_import_ao_trial.py:92`, serta audit Y/Z/AB/AC;
   - skenario-skenario ini sengaja menutup periode lalu memposting koreksi terlambat, untuk membuktikan bahwa koreksi masuk periode terbuka. Bila recost masih antre pada saat close, gate baru akan menolak close dan oracle lama berubah. Itu harus diputuskan per kasus, bukan dilonggarkan.
2. Kontrak menuntut satu preflight **per tanggal** untuk seluruh kategori blocker, dan recheck atomik. Gate "READY global" hanya potongan kecilnya dan bisa menutupi B04. Ambang absensi/payroll/GRNI dan LAU-DEC04 belum diputus owner. Menambalnya sebagian sekarang berisiko menjadi "kebijakan diam-diam" (L1399).
3. Menumpuk successor kedua di atas AV yang belum ditinjau membuat keduanya saling bergantung.

**Rancangan perbaikan (bertahap, satu engine, tanpa kebijakan baru):**
- **Tahap 1, bisa dikerjakan tanpa keputusan baru.** Satu fungsi preflight privat `erp.accounting_close_preflight_v1(p_closed_through)`. Fungsi yang sama dipakai oleh preview UI (CP7) dan oleh `close_accounting_through` sesudah `FOR UPDATE`.
  - Isinya: antrean recost yang menyentuh `<= p_closed_through`, pemeriksaan kritis laporan, dan pemeriksaan integritas per tanggal yang dipakai B04, semuanya dievaluasi pada tanggal close yang sama.
  - Close menolak bila ada blocker, dengan daftar blocker yang bisa dibaca owner.
  - `get_owner_financial_snapshot_v2` membaca preflight yang sama untuk `data_confidence`, supaya tidak ada dua definisi kesiapan.
- **Tahap 2, menunggu owner.** Kategori absensi/payroll/GRNI/LAU-DEC04 dimasukkan sebagai blocker berlabel `POLICY_REQUIRED` sampai owner memutuskan ambangnya. Close tetap ditolak untuk kategori yang belum punya keputusan, bila owner memilih fail-closed. Ini keputusan owner, bukan pilihan writer.
- **Atomisitas (STATIC):** satu-satunya penulis baris `cost_recalc_queue` di migration repo adalah `erp._recalculate_material_cost_core` (`supabase/migrations/20260922135612_erp_v2_6_20ao_cp6_invoice_retail.sql`). Fungsi itu mengambil `accounting_period_control … FOR SHARE` di :209, sebelum insert antrean di :434/:443. Close mengambil `FOR UPDATE` (`…20ac…sql:2410`). Jadi pembuatan recost ter-serialisasi terhadap close. Fungsi skema dasar di luar repo **belum** dicek di katalog native (**NOT_TESTED**). Recost sesudah close tetap masuk periode terbuka sebagai residual, sesuai desain yang ada.
- **Acceptance:**
  - kelima kasus di atas, ditambah kasus CRITICAL non-queue;
  - kasus antrean untuk periode **sesudah** tanggal close, yang tidak boleh menahan close lama;
  - kasus B04, integritas historis tidak konsisten walau integritas hari ini bersih;
  - kontrol READY; role non-owner; facade publik sama dengan backend;
  - race posting-vs-close dua sesi (CROSS-T06);
  - regresi 500 kasus dengan disposisi eksplisit per kasus terdampak. Jangan melonggarkan oracle.

### 10.2 Kaitan dengan CP7 (hasil pembacaan penuh)

Pembacaan penuh sudah dilakukan untuk `ERP_V3_2_Master_Pulih_20260923.md` (7236 baris, dibaca utuh dalam empat rentang), `ERP_V3_2_Perubahan_Pulih_20260923.md` (1205 baris), dan `ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md` (617 baris). Pembacaan dikerjakan oleh sub-agen pembaca Claude. Kutipan yang dipakai di dokumen ini diverifikasi ulang langsung oleh Claude dengan `sed` pada nomor baris yang disebut. Arsip besar `08_ARSIP_HISTORIS` (handoff V2/V3 CP7 18 September) **tidak** dibaca baris per baris; isi pokoknya tersimpan di dalam master pulih sebagai arsip V1/V2/CP7 rev3.

**Gerbang masuk CP7:**
- Master pulih L2745: "CP7 tidak dimulai sampai seluruh gate CP6 yang berlaku selesai dan owner memberi mandat".
- Addendum baris 7: "CP7 tetap menunggu gate dan mandat penerus yang sah".
- Karena itu AU-R1/AV dan AUD-S06 adalah **prasyarat CP7**, bukan pekerjaan CP7.

| Kebutuhan CP7 | Bergantung pada | Akibat bila tidak diperbaiki |
| --- | --- | --- |
| Stok per-SKU dan ledger FG global. Kunci FG "Merek + root/SKU + exact size + lokasi + grade" (L3032). | AU-R1/AV | BS NEW_STOCK tertinggal di versi identitas yang sudah berakhir. Saldo per-SKU as-of bisa dibaca di bawah versi yang salah. |
| BR-T08/T09/T10/T14/T16: lineage exact; BS/rework/reversal dengan sisa sumber unik; SKU sama di merek lain terpisah. | AU-R1/AV, HOLD (a)(b) | Atribusi BS ke versi salah menjadi konflik lineage. |
| Acceptance CP7 no. 24–35, khususnya 27 ("Rework GOOD tidak menciptakan produksi baru", L7198) dan 32 ("konflik lineage menghasilkan Belum dapat dipastikan", L7203). | HOLD (b), AU-R1/AV | Rework dihitung sebagai produksi baru, atau planner jatuh ke "belum dapat dipastikan". |
| BR-T13/T29, acceptance 19: backtest tanpa kebocoran masa depan; effective/known/generated terpisah. | Waktu fisik vs tanggal efektif versi | Pembacaan as-of per versi identitas harus mengikuti cutoff fisik yang benar. |
| BR-T17/T18/T30, RMD-T17, LAU-T34, CROSS-T06, AUD-G06: recost pending menahan final; tidak ada READY palsu; arsip laporan tidak ditimpa. | AUD-S06 + AUD-B04 | Periode ditutup dengan HPP belum final. Business Report dan Reminder membaca angka "final" yang belum sah. |
| Satu engine: Stok/Planner/popup/BR/Reminder/Tanya AI V1 memakai definisi dan snapshot yang sama (L1694, L1666). | Preflight close dan `data_confidence` dengan satu definisi | Dua definisi kesiapan, yaitu laporan vs close, melanggar "tidak boleh ada mesin atau daftar perhitungan kedua" (L1849). |

Hal yang perlu dicatat untuk CP7:
- Urutannya CP7 → CP7.5 → CP7C → CP8.
- Jadwal dan pengiriman laporan ada di CP7C.
- Tanya AI V1 hanya menyalin snapshot, tanpa API berbayar.
- BR-T01..40 tumpang tindih dengan 35 acceptance CP7, WIP-T, dan RMD-T. Semuanya masih NOT_RUN.
- Addendum baris 591 mewajibkan setiap requirement CP7/BR dipetakan (done/verified/pending/excluded). AU-R1 dan bukti native AUD-S06 perlu masuk register penerus.

**Petunjuk untuk kontrak HOLD, bukan keputusan:**
- (a) BS saldo awal memang menjadi kasus BS native (master pulih L373, Perubahan Pulih 315: "BS awal terhubung ke kasus BS native"). Kasus seperti itu tidak punya `qc_item_id`/`source_laundry_bs_allocation_id`, sehingga tidak dihitung helper AV. Kontrak untuk cutoff successor tetap **tidak ditemukan**.
- (b) Tiga sumber condong ke "GOOD rework **bukan** produksi baru": master pulih L2504/addendum 275 ("Jangan menghitung GOOD rework sebagai produksi baru kedua") dan acceptance 27 (L7198). Bila owner menetapkan GOOD rework sebagai EXISTING_STOCK, maka AU dan AV yang menghitung **semua** `fg_lots` (termasuk rework) menjadi terlalu ketat. Perbaikannya kemudian: helper mengecualikan lot rework, dan `post_rework_completion` memanggil assert EXISTING_STOCK. Ini tetap harus diputus owner. Konteks sumber-sumber itu adalah metrik/denominator, bukan batas identitas.

## 11. Permintaan kepada ChatGPT (peninjau independen)

Ambil peran peninjau independen. Jangan menulis ke `claude/new-session-deapao` atau cabang kompetisi sebelum giliran writer diserahkan. Tugas:

1. **Validitas masalah AU-R1.** Periksa kontrak di bagian 3. Apakah BS laundry/QC memang harus membatasi successor? Apakah skenario ±5 menit realistis bagi UI? Tolak klaim yang tidak didukung bukti.
2. **Validitas perbaikan AV.** Cari cacat pada:
   - helper: predicate lineage, konservatisme CANCELLED/REVERSED, performa tanpa indeks khusus;
   - guard: mode dinamis, insert bertingkat yang tidak tertangkap, daftar turunan `fg_inventory_balances`;
   - paket: admission, pin, rollback pre/post-use, ACL fungsi baru;
   - race: tafsiran fail-fast vs blocking.
3. **Producer NEW_STOCK yang mungkin terlewat.** Periksa katalog native, bukan hanya migration repo. Apakah ada fakta fisik per produk selain `fg_lots`/`bs_cases` yang diterima di bawah pemeriksaan masa berlaku produk tanpa memanggil assert? Contohnya validasi tanggal langsung di RPC, atau trigger seperti `guard_cp6_*_v2620`.
4. **Kontrak HOLD.** Carikan keputusan owner untuk BS manual/opening dan GOOD hasil rework (bagian 3 dan R-OBS-REWORK). Bila tetap tidak ada, jangan ditebak.
5. **AUD-S06 + AUD-B04 (satu keluarga).** Nilai bukti dan rancangan bertahap di 10.1. Periksa temuan R-CONF di katalog native: apakah ada pemeriksaan per tanggal yang terlewat oleh Claude? Tentukan kasus 500-suite yang terdampak dari daftar pemanggil di 10.1 dengan menjalankannya, bukan menebak. Carikan keputusan owner untuk ambang absensi/payroll/GRNI dan LAU-DEC04; bila tidak ada, catat sebagai keputusan owner yang dibutuhkan. Terapkan ERP-DEC01 (tanggal invoice, sudah diputus 22 September) hanya lewat successor yang diuji.
6. **Area lain.** Audit risiko material lain di CP6: daftar "belum ditinjau" dan hipotesis H-* pada bagian 10. Buktikan dengan keadaan sebelum/sesudah.
7. **CP7.** Periksa tabel 10.2: apakah ada kebutuhan CP7 yang bergantung pada CP6 tetapi belum punya gate? Petakan AU-R1 dan AUD-S06 (bukti native) ke register penerus sesuai addendum baris 591. Jangan memulai CP7; itu menunggu seluruh gate CP6 dan mandat owner.
8. **Sebelum AV dianggap siap digabung**, jalankan atau minta: regresi 500 kasus pada runtime AV, CodeQL, dan delta advisor.
9. Setelah selesai, buat handoff balik ke Claude: temuan sah/ditolak, source, bukti gagal dan lulus, batas cakupan, risiko tersisa, dan prompt tinjauan berikutnya. Jangan menyatakan bug habis atau siap produksi.

## 12. Pendapat Claude tentang ERP (untuk diaudit, bukan keputusan)

- **Kuat:**
  - invariant bisnis tepat (tanggal fisik/invoice/buku terpisah, reversal tertaut, idempotensi, konservasi, hak bayar);
  - backend authoritative dan UI fail-closed;
  - disiplin bukti exact-SHA yang jarang ditemui.
- **Risiko:**
  - Biaya proses per perbaikan sangat tinggi: CP6 punya 48 migration dalam 19 hari (74.891 baris SQL), 288 script `cp6_*`, dan 34 workflow. Harness regresi mengiris AST script lama dan menambal teks SQL di tengah fixture, sehingga rapuh.
  - Nilai yang dipakai owner sehari-hari (CP7: penjualan, keuangan, laporan, Business Report) belum dimulai; hosted Enteng masih di v2.6.20 (4 September).
  - Invariant tersebar per fungsi, bukan satu sumber; AU-R1 adalah contohnya.
  - Definisi terbaru fungsi tersebar di banyak file, dan sebagian objek berasal dari skema dasar yang tidak ada di repo.
- **Saran:**
  1. Tutup AU/AV, lalu tetapkan kriteria keluar CP6 yang eksplisit dan diberi batas waktu. Edge case bereksposur kecil dicatat sebagai known issue.
  2. Pilot end-to-end nyata di UAT dengan data satu PO.
  3. Majukan rebaseline (CP7.5) supaya katalog lengkap ada di repo dan bisa direview.
  4. Selesaikan daftar keputusan owner yang terbuka dalam satu sesi.

## 13. Daftar file dan hash

Semua file di bawah ditambahkan relatif terhadap `ca7f095`; tidak ada file AU yang diubah. Kode produk dan probe AV dibekukan di `bb4009c` (tree `10c2040710534ee555268f547fb99d89942cb143`).

| File | SHA256 | Peran |
| --- | --- | --- |
| `supabase/migrations/20260923090000_erp_v2_6_20av_cp6_new_stock_physical_cutoff.sql` | `3bd2f94fc3415072b3f92b313ef8473d4b3e365b22daaa4e8416d0bea6426199` | Migration kandidat AV (dibangkitkan builder) |
| `supabase/rollbacks/20260923090000_erp_v2_6_20av_cp6_new_stock_physical_cutoff.rollback.sql` | `bdff27690a322e47d1e2d5949de18b23eb46d0d0dca66de188db4da9bb2c2e14` | Restore persis ke AU (pre-use saja) |
| `docs/evidence/cp6-av-pins.json` | `0f9a5e1578656fdcbcae09bc5d1e67fda07c7beea863150358980d1cf10b1f2e` | Pin migration/rollback/builder/definisi/fungsi |
| `scripts/cp6_au_r1_definitions.py` | `db65967c5b38019426de04a8bdf1fe671ae02b545e5c458ce1da6b8458a029d5` | Teks kanonik 3 fungsi (sumber kebenaran builder) |
| `scripts/cp6_au_r1_build.py` | `09bffd200ee3c110760502a594fde66f11ae36c9352e5cb390d717050a91caac` | Builder dari model AU yang dipin |
| `scripts/cp6_au_r1_candidate.py` | `0d71657efdb5ed6f4ab8328ea0a44ffd5fed7880df4f5747d896c3d983b614c4` | Runtime closed-admission install/restore, verifikasi, post-use refusal |
| `scripts/cp6_au_r1_probe.py` | `0bae51cab8d2d451b8a82690d75dce6a5ba70142844e8750ce148a43d644aed6` | Probe before/after, family map, race |
| `.github/workflows/cp6-au-r1-probe.yml` | `97c262daf39dfd8f454dded95239e75715204484920ecfc73ffee10ca36e5ef4` | Workflow native (langkah install disalin persis dari qualification AU) |
| `scripts/cp6_s06_close_probe.py` | `5521c90311f7245ccf6d5f82e3b89ad1b3062375849a3c85930f7f706daedc18` | Probe observasi AUD-S06 (bukan perbaikan), commit `3f2804f` |
| `.github/workflows/cp6-s06-close-probe.yml` | `aba4afc833ae3ddb21c049700206544a4b08a0ce72a57fa4851b592192afeaf5` | Workflow native AUD-S06 (langkah install sama dengan probe AU-R1) |
| `docs/evidence/cp6-au-r1/` | `MANIFEST.json` mencatat SHA256 tiap log/record | Bukti native hasil ekstraksi log job |

Bukti yang disimpan di repo: `docs/evidence/cp6-au-r1/` berisi hasil ekstraksi JSON per kasus dari log job, log mentah, dan `MANIFEST.json` (run, job, artifact, SHA256).

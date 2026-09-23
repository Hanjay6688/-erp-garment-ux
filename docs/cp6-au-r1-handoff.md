# Handoff Claude → ChatGPT — AU-R1 dan kandidat successor AV

Tanggal: 23 September 2026 (WIB). Writer: Claude Code (sesi cloud). Peninjau berikutnya: ChatGPT.

> **Pembaruan (giliran writer Claude berikutnya, 23 September 2026):** paket yang ditinjau sekarang adalah **AV rev2** (§16), bukan kandidat AV `bb4009c`. Keputusan owner lanjutan ada di §14–§15 dan §16.4. Bagian 1–13 dipertahankan sebagai riwayat.
Dokumen ini adalah checkpoint utuh sesuai format bagian 8 handoff AU-R1. Tidak ada yang diringkas dari bukti; semua angka di bawah dapat ditelusuri ke run, commit, atau file yang disebut.

> Mulai dari AU `ca7f095`. Writer AU selesai, bukti tersimpan cocok, penerimaan independen belum ada. CP6 tetap HOLD, 12 HOLD historis dipertahankan, production tidak disentuh. Kandidat AU-R1 dari tinjauan chat **sudah terbukti native** dan sebuah kandidat successor **AV** sudah dibuat, diuji native, dan dibekukan untuk ditinjau. AV **bukan** penerimaan independen dan **belum** berada di cabang kompetisi. Di luar AU-R1, **AUD-S06** terbukti native **sebagian**: close tidak membaca status laporan resmi (RECALC_PENDING/BLOCKED). Bahwa close juga menerima antrean yang benar-benar menyentuh periode yang ditutup baru terbukti dari source, belum native (koreksi di bagian 10.1). Temuan ini belum dipatch karena kontraknya menuntut preflight per tanggal satu keluarga dengan AUD-B04; rancangannya ada di bagian 10.1. Master pulih, perubahan pulih, dan addendum CP7 sudah dibaca penuh; kaitannya dengan CP7 ada di bagian 10.2.

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
| **AUD-S06** | Tutup buku tanpa preflight blocker | **COUNTEREXAMPLE native**: close mengabaikan status laporan resmi. Dampak pada periode yang ditutup: **NOT_TESTED native**, STATIC saja (koreksi di 10.1) | Pekerjaan backend CP6 (L1730). Rancangan bertahap di 10.1; belum dipatch (alasan di 10.1) |
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

**Koreksi cakupan bukti (masukan ChatGPT, dikonfirmasi Claude di source probe):** setiap fixture antrean dibuat dengan `recalc_from = statement_timestamp()` (`scripts/cp6_s06_close_probe.py:56-57`), yaitu hari pengujian 23 September 2026, sedangkan periode yang ditutup berakhir 22 September 2026 (`target_closed_through` di record). Jadi:
- **Terbukti native:** close tidak membaca `data_confidence` laporan resmi sama sekali. Laporan menyebut RECALC_PENDING/BLOCKED, close tetap diterima.
- **Belum terbukti native:** close menerima antrean yang benar-benar memengaruhi periode yang ditutup (`recalc_from` pada atau sebelum akhir hari bisnis `closed_through`). Source close (`…20ac…sql:2410` dst.) tidak memeriksa antrean sama sekali, jadi kasus itu hampir pasti diterima juga, tetapi statusnya **STATIC** sampai diuji. Dampak sesudah close juga belum diuji: ke mana recost untuk periode tertutup menulis ketika antrean diproses (residual di periode terbuka vs menyentuh periode tertutup).
- Fixture di probe ini justru contoh sisi **terlalu ketat** R-CONF: laporan untuk 22 September berstatus RECALC_PENDING karena antrean dihitung global, padahal recost-nya mulai 23 September. Di bawah gate per tanggal yang dirancang di bawah, close pada kasus ini **seharusnya diterima**.
- Label `COUNTEREXAMPLE` di record bukti (`docs/evidence/cp6-au-r1/run_35839202630_records.json`) tidak diubah karena bukti tidak boleh diedit. Tafsiran yang benar adalah paragraf ini.

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
  - kasus antrean untuk periode **sesudah** tanggal close, yang tidak boleh menahan close lama (fixture probe S06 yang sekarang);
  - kasus antrean **di dalam** periode, sebaiknya dibuat lewat jalur nyata (misalnya invoice susulan yang memicu `_recalculate_material_cost_core`), bukan insert administratif. Periksa juga batas hari bisnis Asia/Jakarta terhadap `recalc_from`, dan apa yang terjadi saat antrean itu diproses sesudah close;
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

## 14. Keputusan owner (23 September 2026, sesudah handoff ini dibuat)

Jawaban owner di chat sesi Claude, dicatat apa adanya. Ini keputusan bisnis, bukan bukti teknis. Belum ada yang diterapkan atau diuji.

| No | Pertanyaan | Jawaban owner | Arti teknis yang harus diterapkan (usulan Claude; peninjau silakan menguji tafsirannya) |
| --- | --- | --- | --- |
| 1 | BS manual/saldo awal vs tanggal ganti versi SKU (HOLD a) | "1c, menurut gw kurang signifikan sih ya dampaknya ke bisnis mau pilihan apapun juga." | Pilihan C: BS manual `OUT_OF_NOWHERE` diperlakukan sebagai fakta fisik baru. Ia harus berada pada versi yang aktif di `physical_at` (assert NEW_STOCK) dan ikut dihitung helper cutoff. BS manual `LEGACY` dan BS saldo awal tetap pada versinya (EXISTING_STOCK) dan tidak membatasi successor. Catatan: `untracked_type` bisa dikosongkan oleh `classify_bs_case_v2`, jadi dibutuhkan penanda asal yang immutable, bukan membaca kolom itu. Owner menilai dampak bisnisnya kecil, jadi prioritasnya rendah. |
| 2 | GOOD hasil rework (HOLD b) | "2A" | GOOD rework adalah stok lama (EXISTING_STOCK) pada versi SKU asal BS-nya. Tidak dihitung sebagai produksi baru dan tidak membatasi successor. Implementasinya: helper mengecualikan lot hasil rework (`rework_orders.good_fg_lot_id`), dan `post_rework_completion` memanggil assert EXISTING_STOCK. Cutoff AU/AV yang sekarang menghitung lot rework menjadi terlalu ketat dan harus disesuaikan pada successor. |
| 2b | Celup ulang BS menjadi warna/SKU baru, asal BS sering tidak diketahui | Owner bertanya, belum diputus: "ada penggantian celup warna dari BS … jadi SKU baru … gw udah gatau asal bs mana" | **Belum ada kontrak maupun alur di kode.** `post_rework_completion` selalu menulis ke `product_id` BS asal. `post_product_conversion` hanya memindahkan FG `GRADE_A`, tidak dari BS. Usulan Claude ada di bawah tabel; statusnya change request yang menunggu konfirmasi owner. |
| 3 | Syarat tutup buku (AUD-S06) | "ya no 3 saya setuju sudah sewajarnya itu, intinya kalo diganti kapanpun laporan gw bisa jadi laporan sebenarnya." | Disetujui sesuai saran. **Tahan close**: antrean/gagal hitung ulang HPP untuk periode itu; selisih stok/jurnal; absensi kosong pada hari kerja; payroll periode belum disetujui; harga laundry belum diketahui (LAU-DEC04) sampai owner mengisi harga estimasi. **Boleh close dengan estimasi**: GRNI (nota supplier belum datang), dikoreksi lewat penyesuaian terkendali. Penghalang hanya dihitung untuk periode yang ditutup. Prinsip owner: kapan pun koreksi masuk, laporan menunjukkan angka sebenarnya. Ini sama dengan kontrak "current-corrected wins" + filed snapshot tidak ditimpa + ERP-DEC01. |
| 4 | Urutan kerja | "kalau ada urutan CP nya ya lebih baik ikutin cp nya biar lu kerja sekali jalan kan, cp 7 banyak koneksi ke laporan keuangan yang notabene belum dibuat dan disambungkan loh" | Ikuti urutan CP. Tidak ada successor S06 terpisah sekarang. Menurut kontrak, perbaikan backend S06/B04 tetap bagian CP6 (L1730, L1400), sedangkan UI dan preflight close disambungkan di CP7 (L1718). Agar kerja sekali jalan, backend CP6 dibangun sebagai **satu engine** preflight/kesiapan per tanggal. Laporan keuangan, close, Business Report, dan Reminder di CP7 hanya membaca engine itu tanpa membuat definisi kedua. |

**Tambahan owner untuk 2b** (dicatat apa adanya): "bs harus dikumpulkan sampai bnyak dulu biar efisien dong, gabisa tuh lu suruh gw inget inget warna apa, sekali kirim 100 celana udah campur semua warna. biasa sih celup ulang tidak bayar lagi ya. sangat jarang sih"

**Usulan Claude untuk 2b (celup ulang BS → SKU baru), versi sesudah masukan owner, menunggu konfirmasi:**
- Perlakukan sebagai **konversi**, polanya sama dengan Ganti Merek: sumber keluar sebagai stok lama (EXISTING_STOCK), hasil masuk sebagai stok baru SKU tujuan (NEW_STOCK). Ini konsisten dengan 2A: rework yang kembali ke SKU yang sama adalah stok lama, sedangkan celup yang mengubah identitas menghasilkan stok baru bagi SKU tujuan.
- **Warna asal tidak diminta.** BS dikumpulkan campur warna.
  - Kirim celup: cukup tanggal dan jumlah total, supaya stok BS di gudang tidak terlihat lebih banyak selama barang ada di vendor.
  - Terima celup: hasil dihitung per model + warna baru + ukuran (memang harus dihitung begitu untuk masuk gudang), ditambah jumlah reject. Kirim = GOOD + reject + hilang.
- **Sumber dialokasikan sistem.** Sistem mengambil dari kumpulan BS dengan model dan ukuran yang sama, lintas warna, secara FIFO (BS tertua dulu), dengan label "alokasi sistem", bukan fakta.
  - Qty dan nilai total persediaan tetap tepat: nilai BS yang keluar sama dengan nilai yang masuk ke SKU baru.
  - Yang bisa sedikit meleset hanya atribusi per warna/PO asal. Selisih ini kecil karena model yang sama memakai bahan/biaya yang hampir sama, dan diberi label.
- **Biaya celup biasanya gratis.** Catat sebagai nol yang **diketahui** ("gratis"), bukan harga belum diketahui (kontrak: "gratis bukan kosong"). Bila suatu saat ada biaya, pakai pola kirim–terima–invoice seperti laundry. HPP SKU baru = nilai BS yang dialokasikan + biaya celup, kalau ada.
- **Jangan memakai jalan pintas** "rework ke SKU asal lalu Ganti Merek". Cara itu mengarang stok GOOD warna asal yang tidak pernah ada secara fisik.
- **Sementara fitur belum ada**, karena sangat jarang: catat kiriman dan hasilnya di nota. Masukkan nanti dengan tanggal fisik aslinya. Jangan dicatat lewat rework atau Ganti Merek.
- **Penempatan:** change request berprioritas rendah (sangat jarang), terpisah dari blocker CP6. Karena mengubah qty/nilai stok per-SKU yang dibaca CP7, kerjakan sebagai successor tersendiri sebelum Stok per-SKU dan laporan CP7 bergantung padanya (L1697), atau owner memutuskan penempatan lain.

Dampak pada permintaan bagian 11: item 4 terjawab untuk HOLD (a) dan (b), sedangkan 2b menjadi pertanyaan terbuka baru. Item 5 kini memakai ambang penghalang dari keputusan 3.

## 15. Keputusan dan temuan sesudah §14 (23 September 2026, sesi lanjutan)

Semua jawaban owner di bawah diberikan di chat sesi Claude, dicatat apa adanya. Fakta kode dibaca langsung dari source repo (read-only). Status implementasi setiap butir disebut eksplisit.

### 15.1 Keputusan owner baru

| No | Topik | Kutipan owner | Arti yang disepakati | Status |
| --- | --- | --- | --- | --- |
| 2b-final | Celup ulang BS menjadi SKU baru | "celup ulang ini rare case ya gausah di update dulu ga penting. kalo sampe kepepet ada SKU hasil rework gak ada sumber SKU bs nya. gw tinggal bs out of no where aja. toh langka." | Alur celup ulang khusus **tidak dibuat**. Menggantikan usulan 2b di §14. Kasus langka ditangani oleh jalur 15.1-FG di bawah. | Keputusan; tidak ada kode |
| FG | Jalur "barang jadi masuk tanpa sumber produksi" | "ya tentu saja. lu harus bikin itu nyambung menurut gua ya cara tergampang mengikuti nilai Hpp average saat itu untuk 2 tipe barang ini jadi pembagiannya tidak rusak" | Satu jalur untuk (a) barang jadi temuan saat stock opname dan (b) GOOD dari BS manual atau celup ulang. Nilai = **HPP rata-rata SKU saat barang masuk**, dikunci saat posting. Masuk sebagai **lot non-PO tersendiri** sehingga pembagian biaya PO tidak berubah. Alasan wajib dan review owner/admin. Tersambung end-to-end: backend, halaman Stock Adjustment, halaman BS/rework. | Keputusan; **belum dibangun** |
| FG-ref | Pembanding bila SKU belum punya rata-rata | "iya cari sku sejenis apalagi udah ada info pola, dan bahan, dan ukuran kan?" | Urutan: SKU sama → pola(+revisi) dan bahan sama dengan ukuran persis (warna lain) → pola dan bahan sama (ukuran lain) → model sama → owner mengisi nilai. **Tidak pernah otomatis Rp0.** Kunci pencocokan sama dengan pencocokan WIP CP7 (addendum baris 147), supaya satu engine. Review menampilkan SKU pembanding dan alasannya; owner boleh mengganti nilai dengan alasan. | Keputusan; belum dibangun |
| FG-order | Penempatan | "kalau ada urutan CP nya ya lebih baik ikutin cp nya" (§14 no. 4) | Backend jalur FG sebagai change request sesudah keluarga identitas AV. Penyambungan halaman opname/BS di CP7 bersama alur lain. | Rencana |

Usulan pembukuan jalur FG (menunggu review peninjau, bukan keputusan owner): debit persediaan barang jadi, kredit pendapatan lain (barang temuan), sama dengan pola adjustment plus bahan yang sudah ada. Untuk celup ulang, BS lama dikeluarkan lewat jalur BS (dispose/scrap).

### 15.2 Temuan kode yang mendasari keputusan di atas (STATIC, belum diuji native)

- `erp.post_rework_completion` menolak GOOD dari BS tanpa PO: "GOOD rework return requires native production PO and product lineage" (`supabase/migrations/…20aj…sql:137-138`; aturan ini sudah ada sebelum AJ). BS manual selalu tercatat `po_id = null` (`create_manual_bs_case_v2`). Jadi BS out of nowhere **tidak bisa** menjadi stok GOOD. Alasan yang terbaca dari kode: HPP lot barang jadi dihitung lewat PO (`rebuild_po_hpp`, lalu HPP per lot dengan default 0), sehingga GOOD tanpa PO akan ber-HPP Rp0 dan membuat margin palsu. Penjaganya benar; yang belum ada adalah jalur penggantinya (15.1-FG).
- `erp.post_fg_adjustment` (`…20ac…sql:3530`) hanya menambah/mengurangi qty pada **lot yang sudah ada**, dengan nilai HPP lot tersebut. SKU tanpa lot (misalnya warna baru) tidak bisa menerima stok lewat jalur ini.
- Halaman Stock Adjustment (`src/InventoryControlPages.tsx`) masih **simulasi** ("Draft simulasi siap direview. Belum ada data yang dikirim…", :169). Halaman itu memblokir adjustment plus pada lot PRODUCTION/CONVERSION (:116, :168), karena menambah qty lot PO akan menurunkan HPP semua pcs PO itu, termasuk yang sudah terjual. Pemblokiran di backend tidak bisa dipastikan: tabel adjustment berasal dari skema dasar yang tidak ada di repo.
- Adjustment plus bahan (`post_material_adjustment`) sudah ada dan mengkredit pendapatan lain. Padanannya untuk barang jadi belum ada. Ini celah yang ditutup 15.1-FG.
- Pola dan bahan tidak disimpan di master SKU. Keduanya tercatat di riwayat produksi (pola di data potong, bahan dari roll yang dipakai). Barang saldo awal/impor tanpa riwayat potong mungkin tidak punya info pola/bahan; untuk barang seperti itu pencarian pembanding turun ke model yang sama.
- Halaman impor menampilkan pesan umum dari `normalizeClientError` untuk error parser ("Layanan UAT belum dapat dihubungi…"). Perilaku lama, tidak diubah; dicatat sebagai perbaikan UX kecil.

### 15.3 Rekonsiliasi audit independen ChatGPT (`ERP_CP6_Audit_Independen_20260923`)

Paket dibaca penuh; 61 checksum cocok. Cabang kompetisi tetap `ca7f095`.

| Temuan ChatGPT | Sikap Claude | Tindakan |
| --- | --- | --- |
| AV-GUARD-01: tiga ejaan SQL sah lolos dari guard cakupan | **Diterima.** Cacat kerja Claude. | Guard diganti dengan registri klasifikasi setiap tabel/kolom yang merujuk produk (fail-closed, tidak bergantung ejaan SQL); sedang dikerjakan pada revisi AV. |
| AUD-A04-R2: koleksi saldo awal hilang dibaca kosong/nol | **Diterima dan direproduksi** (12 kasus: 5 lulus, 7 gagal, sama dengan audit). | **Diperbaiki** di commit `9323caa`. Bukti di `docs/evidence/cp6-a04-r2/`: 9 tes kontrak baru gagal pada kode lama; suite 454/454; probe ChatGPT versi adaptasi 12/12. Batas: jsdom dengan RPC tiruan, bukan browser/HTTP/DB. |
| AUD-S06: bukti belum mencakup antrean yang memengaruhi periode yang ditutup | Diterima (sudah dikoreksi di `2257431`). Penajaman ChatGPT juga diterima: `recalc_from` bukan satu-satunya tanggal dampak (konsumsi `min(physical_at)`, `invoice_date`, tanggal jurnal AS). | Masuk desain engine preflight per tanggal (langkah berikutnya sesudah AV). |
| ERP-DEC01 "belum diterapkan" terlalu luas | **Diterima.** Status yang benar: diterapkan sebagian pada keluarga AO/AS; laporan/confidence/close per tanggal belum. | Dikoreksi di sini. |
| H-OPEN-WIP ditolak (`complete_initial_import_wip_v1` punya validasi overlap sendiri) | Diterima. | Hipotesis dicabut. |

### 15.4 Pelajaran Claude (checklist wajib sebelum menyatakan sesuatu terbukti)

Ketiga kesalahan ini ditangkap peninjau independen. Dicatat supaya setiap sesi berikutnya (Claude atau ChatGPT) membacanya di awal kerja:

1. **Guard harus fail-closed dan diuji dengan cara mengakalinya dulu.** Contohnya nama berkutip, tanpa awalan skema di bawah `search_path`, huruf besar, komentar di tengah identifier, `MERGE`, SQL dinamis, pemanggilan lewat fungsi pembungkus. Utamakan pemeriksaan struktural katalog daripada membaca teks fungsi.
2. **Cakupan fixture harus dicocokkan dengan klaim.** Tanggal, periode, dan scope diperiksa sebelum menulis "terbukti". Contoh kesalahan: fixture AUD-S06 bertanggal hari uji, sedangkan periode yang ditutup berakhir sehari sebelumnya.
3. **Status implementasi tidak boleh dikutip dari dokumen tanpa membaca kode.** Contoh kesalahan: ERP-DEC01 disebut "belum diterapkan" padahal AO/AS sudah menerapkan sebagian.
4. **Tes baru harus terbukti gagal pada kode lama** sebelum dipakai sebagai bukti perbaikan (diterapkan pada A04-R2).
5. **Perbaikan minimal; jangan mengubah desain yang sudah ada tanpa alasan.** Contoh: pada A04-R2, penanganan data basi bawaan (`beginRead` menandai ruang kerja basi, KPI "—", penulisan terkunci) dipertahankan, bukan diganti.

## 16. AV rev2: successor keluarga identitas (23 September 2026, giliran writer Claude sesudah audit ChatGPT)

Bagian ini menggantikan kandidat AV lama (`bb4009c`) sebagai paket yang ditinjau. Kandidat lama dihapus dari tree di `ea82532` supaya keduanya tidak pernah terpasang bersama; bukti lamanya tetap di `docs/evidence/cp6-av-pins.json`, `docs/evidence/cp6-au-r1/` dan riwayat Git. Cabang kompetisi tetap `ca7f095` (diperiksa sebelum setiap push). Tidak ada deploy, tidak ada mutasi hosted/legacy/production.

### 16.1 Isi paket

| Hal | Nilai |
| --- | --- |
| Migration | `supabase/migrations/20260923110000_erp_v2_6_20av_cp6_identity_new_stock_cutoff.sql`, SHA-256 `193e84efac8ead7cab681071e40070e1f9249f82cec1b7972f0576e8df25a2dc` |
| Rollback | `supabase/rollbacks/20260923110000_erp_v2_6_20av_cp6_identity_new_stock_cutoff.rollback.sql`, SHA-256 `8c01b942a2d65dbad2876de233cf3d8f89517e04978a4c81753186b1fca2749f` |
| Pin paket | `docs/evidence/cp6-av-r2-pins.json`, SHA-256 `ceb2f9b1e8a00bd1fadec30ff60d2113e4e6210bc52d5ad1413ae87ed7861daf` (dipakai `scripts/cp6_av_runtime.py`) |
| Capture katalog native | `docs/evidence/cp6-av-r2-schema-capture.json`, SHA-256 `6c53571d8f09b80f8e101c9c545b5d3c2714995f9f09430cbacbc64f7afa6195`; run 35847809973, job 107138089292; PG17 native, di-rollback |
| Builder / definisi | `scripts/cp6_av_build.py`, `scripts/cp6_av_definitions.py` |

Delta terhadap AU (katalog lain dipin utuh, 7156 → 7169 objek):
- **Tiga fungsi diganti.**
  - `erp.edit_product_identity_effective(...)`: batas successor memakai helper fakta stok baru (FG dan BS), dengan `>=`.
  - `erp.create_manual_bs_case_v2(jsonb,uuid)`: OUT_OF_NOWHERE divalidasi `NEW_STOCK` pada versi SKU yang berlaku di jam fisik (keputusan owner 1C), lalu asal kasus dicatat.
  - `erp.post_rework_completion(uuid)`: GOOD hasil rework divalidasi `EXISTING_STOCK` pada versi BS-nya (keputusan owner 2A).
- **Tiga fungsi privat baru** (ACL hanya `postgres`):
  - `erp.latest_new_stock_physical_at_v1(uuid)`: fakta stok baru = lot FG kecuali GOOD hasil rework, plus BS dengan jejak QC/laundry atau asal OUT_OF_NOWHERE;
  - `erp.assert_new_stock_cutoff_coverage_v1()`: registri fail-closed;
  - `erp.guard_bs_case_manual_origin_immutable_v1()`.
- **Satu tabel baru** `erp.bs_case_manual_origins_v1`: hanya bisa ditambah; update, delete, dan truncate ditolak trigger; RLS aktif; tanpa grant.
- **Backfill saat install (tambahan run 3):** BS OUT_OF_NOWHERE yang dibuat sebelum AV mendapat baris asal. Nilainya diambil dari baris audit INSERT `bs_cases`, yang append-only, dan jatuh ke nilai sekarang bila audit tidak ada. Install menolak kecuali isi tabel persis sama dengan himpunan itu.

**Guard cakupan (jawaban AV-GUARD-01).**
- Guard lama membaca teks fungsi; guard baru adalah registri 23 kolom yang merujuk produk. Rinciannya: 2 NEW_STOCK_FACT, 6 SOURCE_DOCUMENT, 4 MASTER, 3 DERIVED, 2 MOVEMENT, 2 ACCOUNTING, 2 SALES, 1 AUTHORIZATION, 1 REPORT.
- Kolom yang dideteksi: setiap FK ke `erp.products` di skema mana pun, ditambah kolom uuid bernama `product_id` atau `%_product_id` di `erp`/`public`.
- Kolom baru yang belum diklasifikasi, kolom terdaftar yang hilang atau berganti nama, helper yang menyempit, dan konsumen yang tidak lagi memakai helper menggagalkan install dan pemeriksaan.
- **Batas yang terdokumentasi:** producer NEW_STOCK yang menulis ke tabel non-fakta yang sudah diklasifikasi tidak terdeteksi. Klasifikasinya per tabel, bukan per makna producer. Varian `LIMIT_NON_FACT_TABLE_WRITE` membuktikan batas ini secara native.

### 16.2 Bukti native

Semua bukti adalah bukti writer: PG17 native (Supabase CLI 2.116.0, image 17.6.1.165), clone disposable dari AN yang persis, dengan AU dipasang lewat runtime AU. Workflow kualifikasi dipecah menjadi lima job paralel; setiap fase memakai database sendiri dari rantai yang sama.

| Run | Head | Hasil |
| --- | --- | --- |
| 35848620445 | `ea82532` | Trial AR174, temporal, dan regresi lulus. Probe **INCOMPLETE** (10 kasus) karena dua cacat harness. |
| 35849556805 | `2335c0a` | Probe saja; INCOMPLETE yang sama. |
| **35850597894** | `7a2f895` | **Kelima fase lengkap** (tabel di bawah). Paket belum memuat backfill. |
| 35851917304 | `01cfd70` | Paket dengan backfill. AR174 (146 + 28), temporal (AT16/AU15 + 10 race), dan regresi (326 tanpa kasus bergeser, 12 HOLD, AS34) **WRITER_PASS**. Install dengan pemeriksaan eksak backfill lulus di ketiga database. Kedua fase probe **INCOMPLETE** sebelum kasus pertama: `AU_FULL_CATALOG_DRIFT` karena fixture pra-install meng-commit grant sesi (cacat harness, §16.5). Bukti: `docs/evidence/cp6-av-r2/run35851917304_*`. |
| 35852437460 | `acffc8c` | Fixture pra-install bekerja. Probe after: kasus AV 23 PASS + 11 CONTROL_PASS, termasuk `MANUAL:PREINSTALL_CLASSIFIED_OUT_OF_NOWHERE` **PASS** (successor ditolak dengan pesan cutoff; bukti native backfill) dan kontrol LEGACY. Probe before: kasus yang sama COUNTEREXAMPLE di AU beku. AU15 dan AT16 PASS di kedua fase. Kedua fase **INCOMPLETE** di grup race: seed fondasi dijalankan ulang pada salinan race yang sudah memuat seed dari fixture (cacat harness, §16.5). Trial AR174, temporal, dan regresi **WRITER_PASS** (326 tanpa kasus bergeser, 12 HOLD, AS34). Bukti: `docs/evidence/cp6-av-r2/run35852437460_*`. |
| **35853810855** | **`633176a`** | **Kelima fase lengkap dan lulus.** Probe before: REVIEW_COMPLETE, 8 COUNTEREXAMPLE kasus (7 dari run 2 + `MANUAL:PREINSTALL_CLASSIFIED_OUT_OF_NOWHERE`) dan 3 race COUNTEREXAMPLE di AU beku, 8 CONTROL_PASS. Probe after: `CANDIDATE_WRITER_PASS`, kasus AV 23 PASS + 11 CONTROL_PASS (termasuk backfill pra-install), race laundry 4/4, race BS temuan 4/4, dua siklus paket, post-use refusal PASS, AU15, AT16. AR174 (146 + 28). Temporal AT16/AU15 + 10 race. Regresi 326 tanpa kasus bergeser + 12 HOLD + AS34. Primary tidak berubah, clone 0 di semua fase. Bukti: `docs/evidence/cp6-av-r2/run35853810855_*`. |

Dua cacat harness itu:
1. Predikat BS stok baru di probe merujuk tabel asal pada AU beku, tempat tabel itu belum ada.
2. Fixture rework memanggil `ordinary()` dari modul yang salah.

Keduanya cacat probe, bukan cacat paket. Kasus yang gagal disimpan di `docs/evidence/cp6-av-r2/probe_defect_log_run1.json` (10/10 kasus terjelaskan: 6 + 4).

Run 35850597894 (records dan manifest per job di `docs/evidence/cp6-av-r2/run35850597894_*`, log lengkap; baris log = `original_length`):

| Fase | Hasil |
| --- | --- |
| Probe before (AU beku) | REVIEW_COMPLETE. **7 COUNTEREXAMPLE** kasus: cutoff laundry BS, cutoff QC semua BS, OUT_OF_NOWHERE cutoff, OUT_OF_NOWHERE sesudah versi berakhir, OUT_OF_NOWHERE terklasifikasi, SKU nonaktif, GOOD rework keliru membatasi successor. 7 CONTROL_PASS, 18 NOT_APPLICABLE (guard hanya ada di AV). Race: laundry BS_FIRST:COMMIT dan dua race BS temuan COUNTEREXAMPLE. AU15 dan AT16 PASS. |
| Probe after (AU + AV rev2) | REVIEW_COMPLETE, `CANDIDATE_WRITER_PASS`. Kasus AV: 22 PASS dan 10 CONTROL_PASS. 16 varian guard ditolak/diterima sesuai rancangan: nama huruf kecil/besar, tanpa skema, berkutip, komentar di tengah nama, MERGE, EXECUTE dinamis, pembungkus, tabel saja, tanpa FK, awalan di `public`, kolom terdaftar diganti nama, helper menyempit, konsumen tidak memakai helper; kontrol tabel tak terkait; batas terdokumentasi. Race laundry 4/4 dan race BS temuan 4/4 PASS. Dua siklus paket (install, rollback terbuka ditolak atomik, restore AU persis). Post-use refusal PASS. AU15 dan AT16 PASS. |
| AR 174 | WRITER_PASS: 146 sekuensial + 28 konkurensi PASS. |
| Temporal | WRITER_PASS: AT16 + 4 race temporal, AU15 + 6 race master. |
| Regresi | `WRITER_PASS_WITH_12_PRESERVED_HISTORICAL_HOLD`: bisnis 179 PASS + 39 CONTROL_PASS + 12 DATE_POLICY_REVIEW_REQUIRED, impor 31, nilai 65 (= 326), AS34 PASS. `moved_cases` kosong; setiap kelompok `matches_au_outcome`. |

Semua fase: primary tidak berubah, clone 0, database race 0.

**Status AV rev2: siap ditinjau (writer).** Head yang diuji: `633176a`, tree `58d7fa4ed6d489f099fe8495b9461654f8afd832`. File paket (migration `193e84ef…`, rollback `8c01b942…`, pin `ceb2f9b1…`, capture `6c53571d…`) tidak berubah sejak `01cfd70`; commit sesudahnya hanya memperbaiki harness probe. Ini bukan penerimaan independen.

### 16.3 Batas klaim

- Bukti writer, bukan penerimaan independen. `production_go=false`. Provenance CLI untuk timestamp migration: **NOT_TESTED**.
- CodeQL, advisor, dan browser **belum** dijalankan untuk AV. Ketiganya masuk gate gabungan (§11 langkah 6) bersama S06/B04.
- **Batas backfill:** kasus OUT_OF_NOWHERE tanpa baris audit INSERT dan dengan `untracked_type` yang sudah terhapus tidak bisa dipulihkan. Kasus seperti itu tidak membatasi successor. Uji lokal PG16 (`docs/evidence/cp6-av-r2/local_pg16_backfill.json`) menunjukkan himpunan backfill dan bahwa pemeriksaan eksak menangkap baris yang hilang; bukti native ada pada kasus `MANUAL:PREINSTALL_CLASSIFIED_*` di run 3.
- Kalimat terakhir docstring `scripts/cp6_av_definitions.py` ("Rows created before this successor have no origin record and keep AU behaviour") **sudah tidak berlaku** sejak backfill run 3; yang benar ada di docstring `scripts/cp6_av_build.py` dan di bagian ini. File definisi tidak diubah karena hash-nya dipin oleh capture native (mengubahnya menuntut capture ulang).
- BS LEGACY (manual lama dan saldo awal) tidak mendapat baris asal saat backfill. Tidak ada baris asal = tidak membatasi, jadi hasilnya sama.
- GOOD rework yang selesai sesudah versi BS-nya berakhir diterima sebagai stok lama pada versi itu (keputusan owner 2A; kasus `REWORK:AFTER_SUCCESSOR` menjadi kontrol bahwa assert EXISTING_STOCK baru tidak terlalu ketat).
- 12 HOLD historis tetap HOLD.

### 16.4 Keputusan owner untuk engine close per tanggal (S06/B04)

Ditanyakan lewat pilihan di chat sesi Claude, 23 September 2026; jawaban dicatat apa adanya.

| Topik | Pilihan owner | Arti yang dipakai engine |
| --- | --- | --- |
| Payroll yang melintasi tanggal tutup buku | "Ikut akhir periode (Rekomendasi)" | Upah satu periode payroll diakui pada `period_end`, sama seperti `approve_payroll` sekarang. Payroll dengan `period_end` sesudah tanggal tutup tidak memblokir. Payroll dengan `period_end` pada atau sebelum tanggal tutup wajib APPROVED/PAID. Hari kerja pada atau sebelum tanggal tutup yang punya absensi atau hasil kerja tetapi belum masuk payroll mana pun tetap memblokir. Tidak ada akrual parsial per hari. |
| Definisi hari kerja untuk blokir absensi kosong | "Pakai aturan yang ada (Rekomendasi)" | Setiap hari pekerja DAILY/HYBRID yang aktif pada kontraktor wajib-absensi harus punya catatan terposting; libur diisi OFF (aturan `post_attendance_period_v1`, M12:1358-1381). Sel kosong di rentang tutup buku = blokir, dengan daftar pekerja dan tanggal. Tidak ada tabel kalender baru. |

Keputusan sebelumnya yang tetap berlaku (§14 no. 3): blokir untuk recost pending/gagal pada periode, selisih stok/jurnal, absensi kosong, payroll belum disetujui, harga laundry belum diketahui sampai owner mengisi estimasi; GRNI boleh ditutup dengan estimasi; blokir dibatasi per periode.

### 16.5 Cacat harness Claude di putaran ini (dicatat sesuai §15.4)

1. Predikat probe merujuk tabel yang belum ada pada fase "before", dan fixture rework memanggil modul yang salah. Keduanya membuat 10 kasus INCOMPLETE di dua run.
2. Fixture pra-install yang baru meng-commit grant sesi pada skema `erp`, padahal `r1.group` selalu me-rollback grant itu. Akibatnya install AV menolak dengan `AU_FULL_CATALOG_DRIFT` (run 35851917304, kedua fase probe). Perbaikan: grant dicabut, ACL skema dipulihkan persis, dan fixture menolak commit bila inventaris katalog AU berbeda.

3. Seed fondasi yang ikut ter-commit oleh fixture pra-install membuat `r1.races` dan `found_races` gagal dengan duplikat `contractors_pkey` (run 35852437460), karena keduanya men-seed salinan race tanpa syarat. Perbaikan: seed hanya bila `erp.app_users` kosong, aturan yang sama dengan `r1.group`. Pada clone yang belum ber-seed, perilakunya identik.

Pelajaran tambahan: **fixture yang harus bertahan melewati install successor hanya boleh meng-commit data bisnis**; setiap perubahan katalog dibandingkan dengan inventaris sebelum commit, dan setiap langkah sesudahnya yang menyalin clone harus diperiksa apakah ia mengandaikan clone yang masih kosong.

## 17. AW: engine tutup buku per tanggal (AUD-S06 + AUD-B04), status kerja

**Status: definisi dan uji lokal saja.** Belum ada paket migration, belum ada bukti native PG17, belum ditinjau. Cara pembungkusan paket menunggu keputusan owner tentang standar bukti (opsi A/B sedang dibicarakan owner dengan GPT; belum menjadi keputusan).

**File:**
- `docs/cp6-aw-design.md`: desain, jendela tanggal, atomisitas, kasus penerimaan 1–11, dan penyempurnaan dari peta kode. Sumber fakta kodenya ada di `docs/evidence/cp6-aw/static_code_map_s06.md` dan `static_code_map_engine_queries.md` (STATIC, read-only).
- `scripts/cp6_aw_engine.sql`: `erp.period_blockers_v1(date,date)` dan `erp.period_readiness_v1(date,date)`.
- `scripts/cp6_aw_definitions.py`: teks lama kanonik `close_accounting_through` dan `get_owner_financial_snapshot_v2`, yang cocok dengan pin katalog AV rev2, beserta teks barunya, fungsi baru, facade, tabel, dan trigger.
- `scripts/cp6_aw_local_smoke.py` dan `docs/evidence/cp6-aw/local_pg16_smoke.json`.

**Satu engine, tiga pembaca:**
- `erp.accounting_close_preflight_v1` (preview; facade `public.erp_accounting_close_preflight_v1`);
- `close_accounting_through` menghitung ulang engine **sesudah** `FOR UPDATE` baris kontrol dan menolak dengan `CLOSE_BLOCKED` kecuali READY. Close yang diterima menulis snapshot filing insert-only `erp.accounting_close_filings_v1` (readiness dan saldo GL per akun per tanggal); facade `public.erp_close_accounting_through_v1`;
- `data_confidence` laporan resmi untuk `p_as_of`. Kunci lama dipertahankan; ditambah `engine`, `as_of`, `window_from`, `closed_through`, `blockers`, `info`.

**Keluarga penghalang (kebijakan owner §14 no. 3 dan §16.4):**

| Keluarga | Kode | Tingkat | Cakupan tanggal |
| --- | --- | --- | --- |
| Recost | `RECOST_PENDING`, `RECOST_FAILED_EXHAUSTED` | RECALC / CRITICAL | PO yang punya fakta ≤ tanggal: `recalc_from`, konsumsi bahan potong/kontraktor, lot FG, jurnal PO menurut `economic_date`. Antrean untuk PO yang semua faktanya sesudah tanggal **tidak** menahan. |
| Integritas saat ini | nama pemeriksaan yang gagal (CRITICAL/ERROR dari `run_v268`, `run_v267`, `run_integrity_checks`; pemeriksaan antrean dikecualikan) | CRITICAL | Tidak bisa diberi tanggal, jadi menahan semua tanggal (konservatif). |
| Integritas per tanggal | `GL_INVENTORY_NEGATIVE_ASOF`, `FG_QTY_NEGATIVE_ASOF`, `MATERIAL_QTY_NEGATIVE_ASOF` | CRITICAL | ≤ tanggal. Setiap pemeriksaan hanya di satu sisi (fisik atau GL). |
| Absensi | `ATTENDANCE_CELL_MISSING` (dirangkum per pekerja) | POLICY | Hari sesudah `closed_through` sampai tanggal. |
| Payroll | `PAYROLL_NOT_APPROVED` (`period_end` ≤ tanggal), `PAYROLL_ATTENDANCE_UNCOVERED` (lewat tautan, bukan rentang), `PAYROLL_WORK_UNCOVERED` | POLICY | ≤ tanggal. |
| Laundry | `LAUNDRY_PRICE_UNKNOWN` (tarif kirim kosong dan masih ada qty belum dibiayai) | POLICY | ≤ tanggal. Diselesaikan dengan `erp.set_laundry_rate_owner_estimate_v1`. Estimasi dicatat insert-only; tarif kirim diisi lewat trigger yang ada (akrual dan HPP pada tanggal kirim; `post_journal` menggeser ke periode terbuka bila tanggal itu sudah tertutup), plus residual WIP untuk PO FINISHED. |
| GRNI | `GRNI_ESTIMATE_OPEN` | INFO | Tidak pernah menahan (owner: boleh ditutup dengan estimasi). |

**Pemeriksaan yang sengaja ditolak.** Pemeriksaan "qty fisik 0 tetapi nilai GL masih ada" per tanggal tidak dipakai. Posting terlambat untuk periode tertutup mendapat tanggal GL `max(hari ini, closed+1)`, sedangkan tanggal fisiknya tetap; di antara kedua tanggal itu pemeriksaan seperti ini akan menahan tutup buku selamanya untuk posting yang sah. B04 dibuktikan lewat skenario invoice terlambat yang nilai dan confidence-nya dicocokkan pada tanggal yang sama (rencana kasus di desain, belum dijalankan).

**Atomisitas (penalaran, belum diuji native).**
- Produser yang membaca `closed_through` mengambil FOR SHARE, sehingga menunggu close: `post_journal`, inti recost, transfer, dan trigger stok negatif.
- Produser yang tidak membacanya tidak bergantung pada close. Fakta yang mereka commit selama close berlangsung setara dengan perubahan sesudah close: ikut terbaca berarti close menolak, tidak terbaca berarti menjadi koreksi terlambat.
- Uji race dua sesi (CROSS-T06) masuk rencana native.

**Uji lokal (PG16, tabel asli dari snapshot katalog, fungsi pemeriksaan dan dua view di-stub): 15/15 PASS.** Kasus yang diuji:
- recost di dalam periode;
- recost sesudah periode (kontrol);
- batas tengah malam Asia/Jakarta;
- recost habis percobaan;
- integritas saat ini, termasuk dedup dan pengecualian antrean;
- GL negatif historis padahal hari ini bersih, dengan kontrol kebalikannya;
- FG negatif historis, dengan kontrol;
- pasangan reversal bahan tidak dihitung;
- sel absensi (DRAFT tidak dihitung, OFF dihitung), dengan jendela kosong untuk tanggal yang sudah ditutup;
- payroll jatuh tempo, payroll melintasi tanggal, absensi tanpa tautan, hasil kerja sebelum/sesudah tanggal;
- laundry tarif kosong: kiriman DRAFT diabaikan, yang sudah dibiayai lewat penerimaan tidak dihitung;
- GRNI hanya info;
- gerbang close: READY lewat facade, filing insert-only, `CLOSE_BLOCKED` tanpa efek, close sebelum tanggal lot diterima.

Tiga mutasi sengaja (abaikan fakta lot, jangan buang pasangan reversal, anggap DRAFT sudah tercatat) masing-masing tertangkap, jadi tesnya terbukti bisa gagal. Ini **bukan** bukti native. Snapshot dan jalur laundry belum diuji, karena butuh skema penuh.

**Sisa pekerjaan AW:**
1. Pembungkusan paket (menunggu keputusan standar bukti).
2. Probe native: kasus 1–11 di `docs/cp6-aw-design.md` (bagian "Acceptance cases"), termasuk invoice terlambat B04, race dua sesi, akses non-owner, dan facade sama dengan backend.
3. Regresi 326 + AS34 + AR174 + AT/AU. Delapan modul lama memanggil close di tengah skenario; setiap kasus yang bergeser didisposisi per kasus tanpa mengubah oracle.

## 18. Keputusan owner: standar bukti A + B, dan pembekuan writer Claude (23 September 2026)

### 18.1 Keputusan

Owner menyetujui opsi A + B, sesudah berdiskusi dengan GPT. Rumusan pelaksanaan dari owner dicatat apa adanya:

> "Gue setuju A + B, bro. Kritik Claude soal biaya prosesnya masuk akal: pemeriksaan untuk paket rilis terlalu sering diulang pada kandidat yang masih diuji.
> * A — bukti proporsional: setiap perubahan menjalankan tes terarah untuk seluruh keluarga masalahnya. Setelah kandidat stabil, jalankan regresi penuh dan audit independen. Pembuktian instalasi serta pemulihan lengkap dilakukan pada paket rilis gabungan sebelum masuk hosted.
> * B — gabung sisa CP6: satu kandidat penutup, tetapi pengerjaannya tetap dibagi per keluarga masalah dengan bukti masing-masing. Tutup buku dan jalur stok tetap punya expected yang jelas, sehingga kegagalan mudah ditelusuri."

Dua penjaga teknis yang wajib:
1. **Bukti dan migration lama tetap utuh.** Cara pengembangan baru dibuat eksplisit. Pemeriksaan lama tidak boleh dihapus supaya runner terlihat lulus.
2. **Paket gabungan diuji berangkat dari versi yang mewakili hosted sebenarnya**, bukan hanya database uji paling baru, karena di situlah risiko pemasangan. Catatan fakta: menurut §1, hosted Enteng hanya dibaca dan memuat 70 migration sampai `20260904232442`, tanpa satu pun dari 47 successor CP6. Rantai kualifikasi yang ada sekarang berangkat dari bootstrap AC sampai AN di database disposable. Baseline yang mewakili hosted **belum** dibuat. Hosted tetap tidak boleh dimutasi.

Yang tetap berlaku:
- 12 HOLD tetap dilaporkan;
- aturan bisnis tetap diuji;
- penerimaan independen tetap diperlukan.

Yang dikurangi hanya pekerjaan berulang.

Catatan owner/GPT untuk CP7: tes tampilan memang cepat, tetapi planner, stok, dan Business Report tetap memerlukan pengujian perhitungan serta alur data.

**Berlaku mulai putaran berikutnya.** Urutan yang disampaikan owner:
1. GPT mengaudit pekerjaan Claude sejak audit terakhirnya;
2. owner meminta Claude menggabungkan pekerjaan sesuai A + B;
3. hasilnya kembali ke GPT;
4. sesudah itu eksekusi berikutnya.

### 18.2 Status beku writer Claude

- Writer Claude **berhenti** sesudah commit dokumen ini. Tidak ada pekerjaan yang sedang berjalan dan tidak ada pengingat terjadwal yang aktif.
- Cabang kompetisi tetap `ca7f095`. Tidak ada deploy. Tidak ada mutasi hosted, legacy, atau production.
- AV rev2: writer-qualified (§16), menunggu audit.
- AW: definisi dan uji lokal saja (§17), belum dibungkus, belum native.
- Jalur barang jadi tanpa sumber produksi (§15.1-FG): **belum dimulai**.
- Gate gabungan (CodeQL, advisor, browser): **belum dijalankan**.

### 18.3 Cakupan audit untuk GPT (commit sesudah `2257431`, yaitu dokumen terakhir yang sudah direkonsiliasi di audit sebelumnya)

| Commit | Isi | Yang perlu diaudit | Bukti |
| --- | --- | --- | --- |
| `9323caa` | Perbaikan AUD-A04-R2 (frontend: koleksi saldo awal yang hilang tidak lagi dibaca kosong/nol) | Parser dan tampilan kosong/unknown, fixture yang dilengkapi | `docs/evidence/cp6-a04-r2/` (tes baru gagal di kode lama; 454/454; probe GPT versi adaptasi 12/12) |
| `368665a` | Handoff §15 | Keputusan owner jalur FG, rekonsiliasi audit, pelajaran | — |
| `e5e2182`, `ea82532` | AV rev2: definisi, capture native, paket | Delta 3 fungsi diganti + 3 fungsi privat + tabel asal; registri cakupan (jawaban AV-GUARD-01) | `docs/evidence/cp6-av-r2-*.json`, `cp6-av-r2/local_pg16_smoke.json` |
| `2335c0a`, `7a2f895` | Workflow dan dua cacat harness probe | Kasus INCOMPLETE di run lama, apakah semuanya terjelaskan | `cp6-av-r2/probe_defect_log_run1.json` |
| `01cfd70` | Backfill asal BS OUT_OF_NOWHERE saat install (dari baris audit INSERT) | Himpunan backfill, pemeriksaan eksak, batas kasus tanpa audit | `cp6-av-r2/local_pg16_backfill.json`; native pada run 35852437460 dan 35853810855 |
| `acffc8c`, `633176a` | Dua cacat harness fixture pra-install | Fixture hanya meng-commit data bisnis; seed race bersyarat | run 35851917304 dan 35852437460 (gagal, disimpan) |
| `46a7089`, `fc67844` | Bukti run, handoff §16–§17, definisi AW | Kelengkapan klaim; desain dan SQL engine tutup buku | `cp6-av-r2/run35853810855_*` (lima fase lulus); `cp6-aw/local_pg16_smoke.json` |

Setiap run disimpan per job, termasuk yang gagal: 35848620445, 35849556805, 35850597894, 35851917304, 35852437460, 35853810855.

### 18.4 Usulan writer yang belum menjadi keputusan

- **Kunci daftar selesai CP6:** AV rev2, engine tutup buku S06/B04, jalur barang jadi tanpa sumber (backend), dan gate akhir.
  - Temuan di dalam daftar diperbaiki.
  - Temuan di luar daftar masuk daftar tunggu dengan tingkat keparahan, dan owner yang memutuskan: masuk CP6 bila P0/P1, atau dibawa ke CP7/nanti.
- Usulan ini disampaikan ke owner di chat dan belum dijawab; **bukan keputusan**.

### 18.5 Pernyataan owner lain di percakapan ini (dicatat apa adanya supaya tidak hilang)

| Topik | Kutipan owner | Tempat yang terkait |
| --- | --- | --- |
| Kebutuhan bisnis di balik jalur barang jadi tanpa sumber | "BS out of nowhere tidak bisa di-rework jadi GOOD. … ini kenapa gabisa ya, tujuannya apa dong bs out of nowhere di bikin kalo gabisa di rework? aneh. loh tujuan stock adjustment kan buat masukin barang barang yang tiba tiba muncul saat stock opname kenapa bisa ditolak jadi gabisa??? kok banyak celah aneh" | Fakta kode §15.2; keputusan §15.1-FG (belum dibangun) |
| Pertanyaan fitur | "oh ya kita juga punya fitur stock adjust right?" | §15.2: `post_fg_adjustment` hanya untuk lot yang sudah ada; halaman Stock Adjustment masih simulasi |
| Prioritas | "cp7 penting banget" | Urutan CP tetap (§14 no. 4); CP7 dimulai sesudah gate CP6 dan mandat owner |
| Maksud opsi A | "emang gw tuh maunya lu selesain semua nih sampe akhir baru kita cari salahnya gitu ga sih buat yang A?" | §18.1 |
| Urutan sesudah pembekuan | "nanti akan dimulai dari gpt last audit kerjaan lu dan gw akan suruh lu gabungin semua a, b itu, tanya gpt balik, abis tu baru ke fable the powerful buat libas semua" | §18.1: audit GPT → penggabungan A+B oleh Claude → GPT → eksekusi oleh sesi berikutnya |
| Aturan giliran | "jangan ngapa ngapain dl, disebelah dia lagi jadi writer tunggu giliran lu" | Aturan single writer; Claude hanya menulis pada gilirannya |
| Harapan atas kesalahan writer | "well disini udah ada cacat produksi ya dari lu sampe ketangkep gpt. lu bisa terus belajar kan?" | Pelajaran §15.4 dan §16.5 |

## 19. Mandat owner: kerjakan A+B dan semua temuan audit GPT (23 September 2026)

### 19.1 Dasar

- **Audit independen GPT atas `757b79a`:** `docs/reviews/ERP_CP6_Audit_757b79a_20260923.md`, disalin apa adanya.
  - A04-R2 dan AV rev2 **diterima dalam batas pengujian audit**; kelima fase AV diulang native oleh peninjau.
  - AW belum siap: temuan P-01 (P1), P-02 (P2), P-03 (P2), P-04 (P3).
  - Temuan alat uji H-01 (P2) dan gap rilis G-01 (P1).
  - Tidak ada P0 baru dalam lingkup audit.
  - Lampiran audit yang dirujuk (`02_FEEDBACK_CLAUDE.md`, `03_SCOPE_CP6.md`, `04_BASELINE_AB.md`, file bukti JSON) **belum diterima writer**; hanya laporan utama.
- **Draf keputusan GPT yang diteruskan owner:**
  - A+B disetujui.
  - Cakupan CP6 dikunci pada A04-R2, AV, AW, AX, dan gerbang rilis. Temuan lain dicatat terpisah; P0/P1 tidak otomatis memperlebar pekerjaan tanpa keputusan owner.
  - Metadata hosted boleh diperiksa **read-only** (query dan hasilnya ditunjukkan, tanpa data bisnis, tanpa mutasi). 70 riwayat migrasi hosted dan 19 file lokal dicocokkan menurut isi dan urutan.
  - Uji paket rilis menyertakan backup dan latihan pemulihan di lingkungan terpisah.
  - Kasus AX: pengulangan request, rework sebagian, pembalikan, valuasi mundur, akses bersamaan, angka tidak valid.
  - 12 HOLD tetap, CP6 tetap HOLD, belum untuk deployment. Pilihan kebijakan bisnis baru dikirim dengan contoh angka.
- **Mandat owner** (dicatat apa adanya): "yaudah gas yuk beresin semua A+B , sekalian semua revisi yang ditemukan gpt untuk dibereskan juga."

### 19.2 Keputusan owner yang dikoreksi atau ditambahkan di percakapan ini

| Topik | Kutipan owner | Arti yang dipakai |
| --- | --- | --- |
| Nilai barang tanpa sumber (AX) | "kalo bs from no where gimana bisa ada data nya? kalo good emang dari bs ya jelas ada nilainya dong? gimana cara dapet nilai barang yang out of no where? kecuali kasus celup langka yang mungkin ada nilai bawaannya tapi tercampur jadi satu jelas susah mau mngakui nya piece bs yg mana right? lu jangan pelintir omongan gw dah" | HPP rata-rata **hanya** untuk barang tanpa nilai asal: barang temuan stock opname, GOOD dari BS out-of-nowhere, dan celup ulang yang tercampur. GOOD dari BS biasa membawa nilai BS tercatat ditambah biaya rework di SKU asal (2A). Ini maksud asli §15.1-FG; Claude sempat keliru menyebutnya perubahan keputusan. |
| Dasar tanggal valuasi | (draf keputusan GPT yang disetujui owner) | HPP rata-rata dihitung pada **tanggal fisik kejadian**. |
| Akun kredit barang temuan | — (terjawab dari kode) | `post_fg_adjustment` (lot non-PO) dan adjustment bahan sudah memakai Pendapatan lain untuk selisih plus dan Beban lain untuk selisih minus. AX mengikuti pola ini. Pemisahan tampilan "selisih opname" di laporan dikerjakan di CP7. |
| Cadangan dan pemulihan | "supabase kecil soalnya gratis lu bisa cek di drive gw kok ada kode nya segala enkripsi." | Supabase memakai paket gratis, jadi cadangan utama ke Google Drive dengan kode backup dan enkripsi milik owner (belum dibaca Claude; konektor Drive belum tersambung). Operasionalnya CP7C. Latihan restore wajib di paket rilis. |

### 19.3 Rencana kerja (keluarga dan tingkat bukti sesuai §18)

1. **G-01:** cocokkan metadata hosted (read-only) dengan baseline uji.
2. **AW:** perbaiki P-01..P-04, bungkus sebagai migration pengembangan (T1), lalu probe native.
3. **AX:** backend baru dengan probe T1.
4. **H-01**, lalu **T2:** regresi per kasus, disposisi, audit independen.
5. **T3:** paket rilis dari baseline setara hosted, termasuk backup dan restore serta CodeQL, advisor, dan browser.

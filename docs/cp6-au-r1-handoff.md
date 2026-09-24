# Handoff Claude → ChatGPT — AU-R1 dan kandidat successor AV

Tanggal: 23 September 2026 (WIB). Writer: Claude Code (sesi cloud). Peninjau berikutnya: ChatGPT.

> **Pembaruan terbaru (24 September 2026, writer Claude): baca §22 lebih dulu.** Isinya T2 regresi gabungan (run 10: semua grup sama dengan AU, kecuali 8 kasus AS yang menunggu keputusan oracle) dan T3 paket rilis 23 file (AC..AY) di baseline setara Enteng. Juga dua keputusan owner 24 Sep yang sudah dikerjakan: upah perbaikan BS temuan lewat payroll (AX) dan tanggal recost dari barang jadi (AY rev3). Semua itu T2_REGRESSION/T3_PREP, bukan bukti rilis. CP6 tetap HOLD, 12 HOLD historis tetap HOLD, `production_go=false`.

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

## 20. Pelaksanaan A+B putaran pertama (23 September 2026, writer Claude)

Semua bukti di bagian ini berlabel **T1_FAMILY** (uji keluarga), kecuali G-01 (baca metadata hosted) dan H-01 (alat uji). Tidak ada yang merupakan bukti rilis. `production_go=false`. Cabang kompetisi tetap `ca7f095`; main, deploy, hosted, legacy dan production tidak diubah.

### 20.1 G-01: hosted Enteng dibandingkan dengan baseline uji (hanya SELECT)

- **Ledger.** 70 riwayat migration hosted cocok dengan 19 file lokal menurut isi dan urutan: 18 identik, 1 identik kecuali baris baru di akhir file (19b). 51 riwayat lama tercakup bootstrap katalog CP4.5a. 7 nomor versi berbeda (hosted memberi nomor sendiri). Isi v2.6.20 di hosted cocok dengan salah satu dari dua hash yang diterima 20a. Bukti: `docs/evidence/cp6-g01/ledger_content_order.json`.
- **Katalog.** Rantai uji dibangun ulang sampai v2.6.20 (run 35901222287), lalu dibandingkan dengan query sidik jari yang sama (`scripts/cp6_g01_fingerprint.py`).
  - Identik: 537 fungsi beserta pemilik dan ACL, 520 index, 435 trigger, 190 policy, 55 ledger aplikasi, hash konfigurasi, default ACL dan extension.
  - Berbeda:
    - CHECK pada 17 tabel. Fixture CP4.5a menyimpan bentuk "cantik" `IN (...)`; saat dipasang ulang, cast pindah ke tiap elemen array. Artinya sama, teks katalognya berbeda. Terbukti dengan reproduksi lokal: hash 662ff… di baseline vs 12080… di hosted.
    - Lima view. Sangat mungkin sebabnya sama; teks baseline per view belum dicetak.
    - Sequence: baseline punya 2 sequence identity tambahan, dan 4 sequence tidak dimiliki kolomnya.
    - ACL schema `erp`: hosted memberi USAGE ke `authenticated` dan `service_role`; baseline tidak.
  - Bukti: `docs/evidence/cp6-g01/baseline_compare_run35901222287.json`.
- **Dampak rilis (STATIC).** Migration AO s.d. AV (8 file) memuat guard katalog penuh yang mengunci teks constraint, view, sequence dan ACL schema dari rantai uji. Di hosted, guard ini sangat mungkin menolak pemasangan. Itu aman (gagal tertutup, tidak merusak), tetapi rilis terhenti. Penolakannya sendiri berstatus RERUN_REQUIRED pada baseline yang setia hosted.
- **Keputusan yang dibutuhkan (owner bersama GPT), lihat 20.5 no. 4.**

### 20.2 AW: perbaikan temuan GPT

- P-01, P-02, P-04 diperbaiki; P-03 dengan registri 108 nama cek. Rinciannya di `docs/cp6-aw-design.md`, bagian "Revision after GPT audit 757b79a".
- Uji lokal PG16 dengan stub: 30/30. Pada kode 757b79a, 14 kasus baru gagal atau error, sedangkan kontrol lulus.
- **Native, T1 (run 35901779495, fase after):**
  - pemasangan AW T1 dengan teks fungsi identik definisi;
  - registri mencakup 108/108 nama yang dikeluarkan runner asli;
  - P-01 dengan RPC absensi dan close asli PASS;
  - S06 recost dalam periode (pembelian mundur tanggal) PASS, kontrolnya PASS;
  - P-02 PASS;
  - akses non-owner dan facade PASS.
  - P-04 INCOMPLETE karena fixture (sudah diperbaiki). Race dua sesi ditambahkan di iterasi 2.

### 20.3 AX: barang jadi tanpa sumber produksi (backend CP6, UI CP7)

- **Kebijakan owner yang diterapkan:**
  - lot non-PO baru (asal OTHER);
  - nilai = HPP rata-rata pada tanggal fisik, dikunci saat posting, hanya untuk barang tanpa nilai asal;
  - tidak pernah Rp0 kecuali diisi owner dengan alasan;
  - jurnal Dr Persediaan Barang Jadi / Cr Pendapatan lain;
  - GOOD dari BS biasa tetap lewat rework (2A).
- **Mekanisme:**
  - Kredit Pendapatan lain dibuat **tanpa** product_id, supaya invariant buku HPP non-PO (V2620F) tetap sama dengan targetnya. Polanya sama dengan sisi ekuitas opening.
  - Tabel penerimaan tidak punya kolom produk, jadi registri cakupan AV tetap lengkap.
- **Tingkat pembanding:** SKU yang sama (semua versinya) → model dan ukuran sama → model sama → isian owner.
  - Pola dan bahan bukan atribut SKU. Keduanya hanya ada lewat riwayat produksi SKU itu sendiri, dan kalau riwayat itu ada, tingkat SKU sudah memberi nilai. Karena itu tidak ditebak.
- **Validasi dan perilaku:**
  - angka divalidasi;
  - permintaan idempoten;
  - NEW_STOCK harus aktif pada jam fisik;
  - BS temuan boleh diselesaikan sebagian;
  - pembatalan hanya bila lot belum dipakai.
- **Bukti:** T1 dipasang dan diuji sintaks di PG16. Probe native dijalankan di CI (`scripts/cp6_ax_probe.py`).

**Contoh angka (satu nilai tidak diakui dua kali).**
- SKU Kemeja-M-Navy pada 10 September: Lot A (PO-1) sisa 20 pcs @ Rp50.000, Lot B (PO-2) sisa 10 pcs @ Rp56.000. Opname menemukan 3 pcs.
- Rata-rata = (20×50.000 + 10×56.000) / 30 = **Rp52.000**. Lot baru: 3 × 52.000 = **Rp156.000**.
- Jurnal: Dr Persediaan BJ 156.000 / Cr Pendapatan lain 156.000. HPP Lot A dan Lot B tidak berubah.
- Saat 3 pcs itu terjual seharga Rp240.000: HPP penjualan 156.000.
- Total pengaruh ke laba = pendapatan lain 156.000 + (240.000 − 156.000) = 240.000. Nilai barang temuan diakui sekali sebagai pendapatan lain dan keluar sekali sebagai HPP.
- GOOD dari BS temuan: BS 5 pcs tanpa nilai. 3 pcs jadi GOOD → lot 3 × rata-rata; 2 pcs tetap BS (terbuka), dan kalau dibuang tidak ada jurnal karena memang tidak bernilai.

### 20.4 H-01

- `scripts/cp6_regression_identity.py` membandingkan status per ID kasus terhadap peta expected dari run AU 35822980561 (2703/2703 baris log).
- Uji-diri menangkap pertukaran PASS↔HOLD.
- Run AV 35853810855 identik per kasus, 12 HOLD sama persis (RECONCILED).
- Pembanding lama di `cp6_av_trial.py` tidak diubah (bukti historis).

### 20.5 Pertanyaan kebijakan untuk owner (dengan contoh angka)

1. **P-03, cek integritas yang bisa diberi tanggal.** Dari 108 cek, 94 cacatnya punya tanggal bisnis, tetapi engine belum membatasinya per tanggal. Saat ini (aman) cek ini menahan **semua** tanggal.
   - Contoh: invoice supplier bertanggal 20 September salah jurnal. Owner ingin menutup 31 Agustus. Sekarang ditolak, padahal cacatnya sesudah 31 Agustus.
   - Pilihan:
     - (a) tetap menahan semua tanggal, paling aman, CP6 tidak bertambah;
     - (b) buat versi per tanggal untuk 94 cek itu. Pekerjaannya besar dan tiap cek butuh tanggal jangkar serta uji; cek bertanggal NULL tetap menahan semua;
     - (c) campuran: per tanggal hanya untuk cek yang paling sering, sisanya (a).
   - Usulan Claude: (a) untuk CP6, (c) sesudah melihat data nyata.
2. **AX, definisi rata-rata.** Yang dipasang: rata-rata **stok yang ada pada jam fisik**. Kalau stok kosong, rata-rata semua lot yang pernah diproduksi sampai jam itu.
   - Contoh: Lot C lama 50 pcs @ Rp44.000 sudah habis terjual. Stok sekarang Lot A 20 @ 50.000 dan Lot B 10 @ 56.000.
     - Cara stok: **Rp52.000**.
     - Cara seluruh produksi: (100×50.000 + 20×56.000 + 50×44.000) / 170 = **Rp48.941**.
   - Mohon konfirmasi cara stok.
3. **AX, upah memperbaiki BS temuan.** BS temuan tidak bisa lewat order rework karena order rework butuh PO.
   - Contoh: 3 pcs dibetulkan penjahit dengan upah Rp2.000/pcs. Rata-rata SKU Rp52.000.
   - Pilihan:
     - (a) nilai lot tetap 52.000 dan upah 6.000 dicatat sebagai beban (sesuai "nilai = HPP rata-rata");
     - (b) nilai lot 54.000 (rata-rata + upah).
   - Yang dipasang (a). Upah dibayar lewat jalur biaya yang ada.
4. **G-01, baseline rilis (T3).** Pilihan:
   - (a) Bangun baseline dengan menjalankan ulang 70 SQL migration yang tersimpan di ledger hosted, supaya bentuk katalognya persis. Isi SQL itu harus dibaca dari hosted. Itu metadata, tetapi migration awal ("compact export proxy") mungkin memuat URL atau kunci, jadi perlu izin dan pemeriksaan sebelum disimpan (tidak masuk repo).
   - (b) Samakan rantai uji dengan bentuk hosted: 17 CHECK, 5 view, 4 sequence, ACL `erp` diambil dari hosted dengan SELECT. Paket rilis gabungan lalu mengambil pin dari rantai yang sudah disamakan.
   - (c) Ubah guard AO–AV menjadi pembanding makna. Ini melonggarkan guard lama, jadi Claude tidak menyarankannya.
   - Usulan Claude: (b). File migration lama tidak diubah; paket rilis gabungan (T3) memegang pin barunya sendiri.

### 20.6 Catatan teknis putaran ini

- ghcr.io membatasi unduhan image Supabase (`toomanyrequests`) sebelum tes berjalan (run 35898369683, 35899068186, 35899325557). Start kini mencoba ulang dan beralih ke public.ecr.aws dengan tag image yang sama. Tidak ada tes yang diulang.
- Seed harness memuat open item nyata untuk engine: payroll CALCULATED, sel absensi kosong, kerja belum masuk payroll. Probe menenangkannya dengan RPC owner di dalam savepoint uji (absensi OFF, approve payroll, payroll untuk kerja). Header payroll disisipkan administratif, seperti pola harness yang sudah ada.

## 21. Pelaksanaan A+B putaran kedua: bukti native T1, keputusan owner, G-01 (23 September 2026, writer Claude)

Semua bukti di bagian ini berlabel **T1_FAMILY**: uji keluarga di rantai disposable AN → AS/AT → AU → AV (+AW, +AX dari file `supabase/dev`). Ini **bukan** bukti rilis dan **bukan** penerimaan independen. CP6 tetap HOLD, 12 HOLD historis tetap HOLD. Production, hosted Enteng, main, dan Cloudflare tidak dimutasi. Log gagal disimpan, dan oracle lama tidak dilonggarkan. Setiap koreksi probe di bawah memperbaiki salah ukur di pihak probe, bukan menurunkan ekspektasi.

### 21.1 Keputusan owner di percakapan ini (dicatat apa adanya)

| No | Topik | Kata-kata owner | Yang dijalankan |
|---|---|---|---|
| 1 | P-03 cek integritas per tanggal | memilih "Tahan semua, bertahap nanti" | CP6: semua cek yang belum dibatasi tanggal tetap menahan semua tanggal (perilaku sekarang). Pembatasan per tanggal dibuat bertahap sesudah ada data nyata. |
| 2 | AX definisi rata-rata | memilih "Stok yang ada" | Rata-rata HPP dari lot yang masih ada di gudang pada jam fisik (sudah terpasang). |
| 3 | AX upah perbaikan BS temuan | "sebenarnya B, tapi biasa kan bikin bagus gada biayanya" | Prinsip B: upah ditambahkan ke nilai lot. Biasanya tanpa biaya, jadi nilai lot = rata-rata. Jalur untuk upah > 0 **belum dibuat** (lihat 21.6). |
| 4 | G-01 baseline rilis | "Pilih 1 — 'Salin definisi yang beda.' … samakan database uji lewat pembacaan metadata Enteng secara baca-saja, lalu uji pemasangan paket rilis di database uji." Tambahan: "Cakup juga dua sequence tambahan yang tercatat di perbandingan katalog; T3 tetap HOLD sampai seluruh selisih dijelaskan dan pemasangan AO–AV lulus." | Lihat 21.4. |
| 5 | Stok yang direservasi draft | "tapi secara stok harus keluar bro, karena data real time gudang, kalo udah reserved harus kurang karena orang toko jangan sampai anggap stok masih ada paham kan?" Lalu, untuk rata-rata HPP barang temuan, memilih "Ikut dihitung". | Stok tersedia tetap langsung berkurang saat direservasi (tidak diubah). Hanya perhitungan rata-rata HPP barang temuan yang menghitung barang yang direservasi tetapi belum terjual. |
| 6 | Lampiran audit dan backup Drive | "audit gpt kan udah? google drive juga back up an lama cp 5 doang itu." | Audit GPT sudah ada di repo dan sedang dikerjakan; permintaan lampiran dicabut. Backup Google Drive adalah backup lama CP5, tidak dipakai. Uji backup dan restore untuk rilis dilakukan di database uji terpisah (T3); backup operasional tetap CP7C. |
| 7 | Cara kerja sesi ini | "khusus sesi ini sampai selesai lu gausah minta konfirmasi ya buat sql gitu. lu beresin sampe beres bisa?" | SQL tidak lagi meminta konfirmasi di sesi ini. Batas tetap: Enteng hanya SELECT metadata, tidak ada mutasi, tidak ada deploy. |

### 21.2 AW (engine tutup buku per tanggal): T1 selesai

| Iterasi | Run | Hasil | Catatan |
|---|---|---|---|
| 1 | 35901779495 | 5 PASS, 2 INCOMPLETE | Fixture P-04 tidak menemukan lot. |
| 2 | 35903761656 | kasus lulus; race 2 FAIL + 3 INCOMPLETE | Fixture: semua race memakai satu salinan database, sehingga filing dan payroll terbawa ke race berikutnya. Kini tiap jadwal mendapat salinan segar. |
| 3 | 35905188928 | 9 kasus + 8 race lulus | |
| 4 | 35905834630 | 3 FAIL (probe) | (a) B04 mengira invoice terlambat meninggalkan antrean recost; ternyata jalur invoice langsung menghitung ulang, jadi READY memang benar. (b) Filing dibandingkan sebagai teks sesudah zona sesi berubah; kini dibandingkan sebagai instan UTC. (c) GRNI adalah INFO dan tercatat di `info`, bukan `blockers`. |
| 5 | **35909687266** | **16 kasus + 8 race lulus** | Primary tidak berubah, clone 0. |

Fase "before" pada run yang sama (AU+AV tanpa AW, job 107346092117) punya 4 **COUNTEREXAMPLE**:
- P-01 (absensi dibatalkan sesudah close);
- S06 recost dalam periode;
- recost gagal tiga kali;
- jurnal tidak seimbang.

Pada dua kasus terakhir, laporan sendiri sudah menyatakan BLOCKED, tetapi close lama tetap menerima. Artinya kasus ini menangkap masalah nyata yang diperbaiki AW, bukan sekadar lulus. Bukti: `docs/evidence/cp6-aw/native_t1_run35909687266_before_iter5.json`.

Kasus yang lulus di iterasi 5:
- P-01, P-02, P-04;
- S06 recost di dalam dan sesudah periode, recost gagal tiga kali (CRITICAL);
- B04 invoice terlambat di Jakarta dan Kiritimati. Nilai mengikuti oracle AA tanpa diubah, delta diakui di periode terbuka, GL hari yang sudah ditutup tidak bergeser, dan filing tidak ditimpa;
- P07: antrean recost muncul sesudah close, lalu diproses sampai READY lagi;
- histori salah yang sudah diperbaiki;
- CRITICAL non-antrean;
- kebijakan payroll dan GRNI;
- akses.

Race dua sesi: absensi dibatalkan vs close, dan pembelian mundur vs close, masing-masing dua urutan dan commit/abort.

Bukti: `docs/evidence/cp6-aw/native_t1_run*_after_iter*.json`.

### 21.3 AX (barang jadi tanpa sumber produksi)

| Iterasi | Run | Hasil |
|---|---|---|
| 1 | 35904115299 | 9 PASS, 1 OBSERVED |
| 2 | 35905188855 | 13 kasus lulus; race batal-vs-jual gagal karena fixture (draft sudah mereservasi lot) |
| 3 | 35906065887 | 12 kasus + 8 race lulus |
| 4 | 35909687233 | 28 PASS; 1 INCOMPLETE (fixture: identitas SKU yang sudah punya histori hanya boleh diganti mulai sekarang atau ke depan) |
| 5 | 35910555547 | 29 PASS + 1 OBSERVED (fixture versi penerus diperbaiki; lihat §22.1) |

**Perubahan AX putaran ini:**
- **Nilai isian owner hanya bila tidak ada pembanding.** Versi awal masih menerimanya walau rata-rata ada; itu menyimpang dari keputusan owner, sekarang ditolak.
- **Tinjauan adversarial independen** (sub-agent, baca-saja): `docs/evidence/cp6-ax/independent_review_20260923.md`. Tujuh temuan terbukti diperbaiki:
  - stok yang direservasi ikut dihitung dalam rata-rata;
  - resolusi BS milik penerimaan AX tidak bisa dibatalkan dari layar BS;
  - urutan kunci diseragamkan;
  - pcs yang sedang di-rework tidak tersedia;
  - versi SKU penerus berlaku sesudah BS ditemukan;
  - batas nilai sesuai kolom `numeric(18,6)`;
  - hanya GRADE_A.
- Dua temuan tidak diubah, dengan alasan yang dicatat di file tinjauan.
- Satu temuan dicatat untuk owner, lihat 21.6.

### 21.4 G-01 opsi 1: baseline uji disamakan dengan Enteng

- **Cara baca Enteng:** hanya SELECT katalog. Pertama hash per kelompok, lalu per objek khusus untuk kelompok yang berbeda, lalu teks definisinya. Tidak ada data bisnis yang dibaca dan tidak ada mutasi.
- **Kelompok yang cocok:** 26 dari 40 kelompok hash cocok persis. Selain itu fungsi (537), indeks, trigger, policy, relasi, dan ACL semua relasi lain juga cocok.
- **Semua selisih dan penjelasannya:**
  - **23 aturan CHECK di 17 tabel dan 5 view:** maknanya sama, teksnya beda. Daftar `IN (...)` pada kolom varchar disimpan Postgres sebagai `= ANY ((ARRAY[...])::text[])`. Fixture CP4.5a menyimpan teks hasil deparse itu, dan saat dibaca ulang, cast pindah ke tiap elemen. Bentuk sumber `IN` / `NOT IN` disusun ulang. Untuk ke-23 aturan CHECK, hasilnya persis hash Enteng di PG16 lokal; untuk view, pembuktiannya di CI.
  - **Sequence:** restore fixture meninggalkan `app_access_audit_id_seq` dan `production_pattern_audit_id_seq` yang berdiri sendiri. Akibatnya sequence identity yang sebenarnya bernama `*_seq1`; ini dua sequence tambahan yang disebut owner. Selain itu `audit_logs_id_seq` dan `cost_recalc_queue_id_seq` belum `OWNED BY` kolomnya.
  - **Schema `erp`:** Enteng memberi USAGE ke `authenticated` dan `service_role`.
  - **Hak akses relasi:** satu-satunya selisih adalah dua sequence `*_seq1` itu.
  - **Ledger platform:** sudah dijelaskan di G-01 putaran pertama (isi dan urutan cocok).
- **Alat:**
  - `docs/evidence/cp6-g01/hosted_alignment_metadata.json`: teks Enteng, tiap teks diverifikasi md5.
  - `scripts/cp6_g01_align.py`: hanya berjalan di endpoint disposable lokal (dipastikan lewat assert), lalu memeriksa tiap objek terhadap hash Enteng.
  - Workflow G-01 kini menyelaraskan baseline lalu membandingkan ulang semua jenis objek dengan Enteng.
- **Status:** T3 tetap HOLD, sesuai kata owner. Langkah berikutnya adalah menguji jalur pemasangan AO–AV (dan pendahulunya) di baseline yang sudah disamakan. Guard lama yang mengunci teks katalog rantai uji diperkirakan menolak; hasilnya dicatat apa adanya, dan guard lama tidak dilonggarkan.

### 21.5 T2 (regresi penuh)

Runner `scripts/cp6_t2_regression.py` sudah siap. Workflow-nya disiapkan dan dijalankan sesudah AX T1 lulus penuh. Regresi berjalan tanpa mengubah oracle. Delapan modul memanggil close di tengah skenario; dengan AW, close ditolak bila seed masih punya open item. Setiap kasus yang berpindah hasil akan didaftar per ID (H-01) untuk disposisi.

### 21.6 Hal terbuka untuk owner
- **Upah perbaikan BS temuan > 0 (keputusan B):** jalurnya belum ada. Pola rework yang sudah ada mencatat Dr WIP / Cr Hutang kontraktor lewat payroll, dan itu terikat PO. Untuk barang temuan (tanpa PO) perlu satu pilihan: dibayar tunai saat itu (Dr Persediaan BJ / Cr Kas), atau lewat payroll penjahit (butuh jalur baru di payroll). Karena biasanya tanpa biaya, CP6 tidak tertahan oleh ini.
- **Konversi (rebranding) terblokir oleh stok AX:** aturan lama menolak konversi SKU bila di lokasi yang sama ada lot non-PO. Tidak ada angka yang salah (transaksi ditolak, bukan dihitung keliru). Membukanya butuh alur HPP konversi lot non-PO dan dicatat sebagai backlog.

## 22. Pelaksanaan A+B putaran ketiga: T2, T3, audit independen, upah perbaikan, tanggal recost (23–24 September 2026, writer Claude)

Label bukti: **T2_REGRESSION** untuk regresi gabungan dan **T3_PREP** untuk paket rilis. Keduanya **bukan** bukti rilis dan **bukan** penerimaan independen. CP6 tetap HOLD, 12 HOLD historis tetap HOLD, `production_go=false`.

Batas yang dijaga:
- Tidak ada mutasi pada main, deploy Cloudflare, Enteng (`siimvrusnzxexizpyoib`), ERP-Garment lama (`vlxdhpkjeevubjxexnfo`), maupun production.
- Cabang kompetisi tetap `ca7f095` (dicek sebelum setiap push).
- Akses ke Enteng hanya SELECT metadata: definisi dan hash, tanpa data bisnis. Sejak owner meminta berhenti, tidak ada SQL ke hosted sama sekali (22.7).

### 22.1 Ringkasan status

| Item | Status | Bukti |
|---|---|---|
| AW T1 | selesai: 16 kasus + 8 race lulus (iterasi 5) | §21.2 |
| AX T1 | selesai: iterasi 5 (run 35910555547) 29 PASS + 1 OBSERVED; dengan upah perbaikan (run 35949833558) 32 PASS + 1 OBSERVED | 22.2c |
| Upah perbaikan BS temuan > Rp0 (keputusan owner 24 Sep: "Utang, dibayar via payroll") | selesai di AX: T1 3 kasus baru PASS, T3 PASS, T2 run 7 tidak memindahkan kasus apa pun | 22.2c |
| Tanggal recost invoice terlambat (keputusan owner 24 Sep: "Geser tanggal recost") | AY rev3: T1 7/7 PASS (run 35952988290), T3 PASS (run 35953286010), T2 run 10: semua grup sama dengan AU, kecuali 8 kasus AS yang menunggu keputusan oracle | 22.2a, 22.2b |
| G-01 baseline | sama dengan Enteng: seluruh katalog kecuali stempel ledger platform, dan 11 dari 11 kapsul historis | 22.4 |
| T2 regresi gabungan | run 6: BUSINESS 214/230 sama dengan AU, sisanya 16 kasus temuan 22.2a. Run 7 (dengan upah perbaikan): sama dengan run 6. Run 8 (AY teks pertama) dan run 9 (AY rev2): 16 kasus itu kembali ke AU, tetapi masing-masing memperlihatkan satu kesalahan writer (22.2b). Run 10 (AY rev3): AR 146/146 + 28/28 race, BUSINESS 230/230, IMPORTS 31/31, dan VALUES 65/65 sama dengan AU; temporal lulus; NEW_CASES 26 PASS + 8 kasus AS yang menunggu keputusan oracle (22.2b). | 22.2, 22.2b |
| T3 paket rilis gabungan | 23 file (AC..AY, run akhir 35953286010, head b242d45): terpasang di baseline setara Enteng, pin deterministik (kini wajib), browser 10/10, restore ketat lulus, advisor hanya INFO. Rollback NOT_TESTED. | 22.3, 22.6 |
| Audit independen alat T2/T3 | 7 temuan, semua diperbaiki | 22.5 |
| CodeQL (security-extended) | run 35944124414 di head 13dbcb1: 0 temuan; diulang di head akhir: run 35953312746 di head b242d45: 0 temuan | 22.6 |
| Akses hosted | 21 panggilan Supabase, 0 menulis, legacy 0 | 22.7 |

### 22.2 T2: regresi gabungan AU + AV + AW + AX (+ AY)

Arahan owner 24 September (inti, dicatat apa adanya):
- lengkapi persiapan tes yang tidak sedang menguji payroll, perbaiki lima benturan absensi, lalu jalankan ulang; 75 kasus itu belum boleh disebut lulus;
- "belum masuk payroll berbeda dengan belum dibayar": payroll yang sudah disetujui boleh masih berupa utang, jadi tes tidak boleh dipaksa membayar semuanya;
- tes khusus upah belum lunas atau baru dibayar sebagian harus tetap menguji kondisi itu;
- melengkapi data contoh sesuai kebijakan yang sah boleh; mengubah hasil yang diharapkan perlu diperiksa alasannya.

Runner: `scripts/cp6_t2_regression.py`. Kasus, oracle, dan jadwal race tidak diubah. Setiap kasus dibandingkan per ID dengan hasil AU (komparator H-01).

| Run | Seed | Hasil |
|---|---|---|
| 1 (35911656309) | AS_IS | 152 kasus berpindah. Semuanya berhenti karena open item milik seed sendiri (absensi, payroll CALCULATED, kerja kontraktor seed di luar payroll) di bawah kebijakan owner AW (P-03: tahan semua tanggal). |
| 2 (35914912522) | QUIETED | 75 berpindah. Open item seed dibersihkan sekali per grup dengan RPC owner. |
| 3 (35940435661) | QUIETED + diagnostik | Hasil sama persis dengan run 2. Diagnostik membuktikan untuk 26 kasus bahwa baris kerja yang belum dibayar dibuat oleh kasus itu sendiri. |
| 4 (35943232674) | QUIETED, aturan baru (22.5 no. 6) | Berhenti di gerbang pembersih, sesuai rancangan: OFF untuk seluruh rentang bertabrakan dengan periode absensi milik seed sendiri (kontraktor …0001 dan …0005), jadi grup tidak dijalankan. Temporal tetap lulus. |
| 5 (35944088575) | QUIETED + fixture kasus dilengkapi (arahan owner 24 Sep) | AR 174/174 WRITER_PASS; IMPORTS 31/31, VALUES 65/65, NEW_CASES 34/34 sama dengan AU; temporal lulus. BUSINESS: yang berpindah turun dari 75 menjadi 23. Rinciannya: 11 INCOMPLETE (payroll kasus ditolak karena bertabrakan dengan payroll seed yang disetujui) dan 12 BUG_PROVEN (temuan 22.2a). WORK, REWORK, RECOVERED_SALE, POCKET, RECEIPT, dan lima kasus absensi kembali sama dengan AU. |
| 6 (35945041135) | seperti run 5, ditambah payroll belum-dibayar yang bertabrakan dibuat ulang | 101 payroll fixture disetujui (11 dibuat ulang, 0 ditolak). BUSINESS 214/230 sama dengan AU; 59 dari 75 kasus run 2/3 kembali ke hasil AU. Sisa 16 = temuan 22.2a. Grup lain seperti run 5. |
| 7 (35950296669, bc650c3) | seperti run 6; AX kini dengan upah perbaikan | Semua grup sama dengan run 6; tidak ada kasus yang berpindah karena upah perbaikan (`docs/evidence/cp6-t2/run35950296669_repair_wage_no_ay.json`). |
| 8 (35950787577, cd0c9eb) | seperti run 7, ditambah AY teks pertama | 16 kasus temuan 22.2a kembali ke hasil AU. 28 kasus BUSINESS dan 16 kasus AS berpindah: 8 AS karena keputusan owner, sisanya karena kesalahan writer (22.2b). (`docs/evidence/cp6-t2/run35950787577_ay_first_text.json`) |
| 9 (35952233525, 09250d0) | seperti run 8, dengan AY rev2 | BUSINESS 230/230, IMPORTS 31/31, dan VALUES 65/65 sama dengan AU. AR: 3 INCOMPLETE (kesalahan rev2, 22.2b). NEW_CASES: 26 PASS + 8 AS yang menunggu keputusan oracle (22.2b). |
| 10 (35952990109, 8b1d555) | seperti run 9, dengan AY rev3 | AR 146/146 + 28/28 race; BUSINESS 230/230, IMPORTS 31/31, dan VALUES 65/65 sama dengan AU; temporal 16 + 15 kasus dan 4 + 6 race PASS. NEW_CASES 26 PASS + 8 kasus AS yang menunggu keputusan oracle. Tidak ada kasus yang berpindah dari AU. (`docs/evidence/cp6-t2/run35952990109_ay_rev3_final.json`) |

Pada run 1–3, bagian berikut tidak berubah:
- temporal: AT 16 + AU 15 kasus serta 4 + 6 race PASS;
- AR: 142/146 sekuensial + 28/28 race PASS;
- VALUES 65/65 dan NEW_CASES 34/34 identik dengan AU;
- BUSINESS 163/230 dan IMPORTS 27/31 identik dengan AU.

Disposisi sementara run 2/3 (`docs/evidence/cp6-t2/disposition_20260924.json`: 70 tertahan kebijakan, 5 benturan absensi) **sudah digantikan** oleh arahan owner di atas. Kasus-kasus itu tidak disebut lulus, tetapi dijalankan ulang dengan persiapan yang lengkap.

**Cara melengkapi persiapan (harness, file oracle tetap terkunci hash):**
- Tepat sebelum kasus membaca kesiapan (laporan owner, preflight, tutup buku), setiap hari absensi berbayar dan baris kerja payable **yang dibuat kasus itu sendiri** dan belum masuk payroll dimasukkan ke payroll baru kontraktor tersebut, di-*populate*, lalu **disetujui**. Persetujuan hanya mengakui biaya ke utang kontraktor (`approve_payroll`: tidak ada kas keluar); tidak ada pembayaran.
- Item yang sudah ada sebelum kasus tidak disentuh. Sesi kasus (session user, role, klaim JWT, zona waktu, search_path) dikembalikan persis dan dicek.
- Bila hari kasus jatuh di dalam payroll kontraktor yang sudah disetujui tetapi belum dibayar, payroll itu dibatalkan dengan `cancel_unpaid_payroll`, lalu satu payroll untuk rentang gabungan disetujui lagi (run 6). Payroll yang sudah PAID tidak disentuh: kasusnya ditolak dan dicatat.
- **WORK_UNPAID** berarti 10 pcs selesai dengan 0 pcs payable, jadi tidak ada yang dimasukkan ke payroll. **WORK_PARTIAL_PAY** berarti 7 pcs selesai dan 5 pcs payable (bukan "dibayar sebagian"); nominalnya diasersi sebelum laporan dibaca. Kedua asersi tidak berubah; kasusnya tetap menguji kondisinya sendiri, dan upahnya tetap utang.
- **Lima kasus absensi:** kasus memposting PRESENT untuk kontraktor seed pada hari-3 dan hari-2. Kedua hari itu kini dijadikan periode OFF tersendiri oleh pembersih seed, lalu dibatalkan dengan RPC owner hanya di dalam savepoint kasus itu.

**Pembersih seed (run 4 → 5):**
- Tanggal tutup dibaca, tidak diasumsikan.
- Periode absensi seed yang masih DRAFT dan sudah jatuh tempo diposting.
- OFF hanya mengisi hari yang belum dipegang periode aktif.
- Engine wajib menjawab READY untuk seluruh rentang yang dibuka (2 Jan s/d tanggal tutup).

Hasil run 5 dan 6: lihat tabel di atas. Rincian per kasus: `docs/evidence/cp6-t2/run35944088575_fixture_completed.json` dan `docs/evidence/cp6-t2/run35945041135_fixture_redone.json`; disposisi akhir: `docs/evidence/cp6-t2/disposition_run6_20260924.json`.

### 22.2a Temuan dari T2 run 5: saldo barang jadi negatif setelah invoice terlambat yang menurunkan harga

Setelah fixture dilengkapi, 12 kasus (INVOICE *:4:False dan CALENDAR 1/2/3 bulan serta MAY31 dengan hari terima masih terbuka) akhirnya mencapai asersi utamanya. Engine AW lalu menjawab BLOCKED dengan `GL_INVENTORY_NEGATIVE_ASOF` (CRITICAL). Mekanismenya (dari kode dan angka bukti, bukan dugaan):

- Contoh CALENDAR 1 bulan:
  - bahan diterima 23 Agu dengan harga estimasi Rp10/unit (GRNI 100);
  - barang jadi masuk 24 Agu (nilai 85);
  - 2 pcs terjual;
  - invoice datang 23 Sep dengan harga Rp8,25 (lebih murah).
- Recost menurunkan nilai barang jadi Rp1,57 dan HPP penjualan Rp1,05, tetapi **mencatatnya pada 23 Agu**, yaitu hari bahan diterima. Barang jadinya baru ada 24 Agu, sehingga saldo buku FG_INVENTORY pada 23 Agu = −Rp1,57.
- Engine AW (`supabase/dev/cp6_aw_t1_family.sql:386-399`) menghitung saldo berjalan harian persediaan sampai tanggal tutup. Saldo negatif di tanggal mana pun dianggap CRITICAL. Karena saldo 23 Agu itu permanen di histori, **setiap tutup buku sesudahnya tertahan** sampai ada keputusan.
- Pada kasus INVOICE *:4:False hasilnya sama: −Rp1,50 pada hari terima.
- Kasus dengan hari terima sudah ditutup (closed=True) lulus, karena selisihnya digeser ke periode terbuka.
- Kaitan dengan HOLD: 8 kasus CALENDAR ini termasuk 12 HOLD historis (kebijakan tanggal), dan statusnya tetap HOLD. Yang baru terlihat adalah akibat konkretnya di bawah engine AW. 4 kasus INVOICE dulu CONTROL_PASS karena laporan AU belum punya pengecekan ini.
- **Keputusan owner (24 Sep, dikutip):** "Saya pilih Geser tanggal recost. Jangan catat penurunan nilai barang jadi pada 23 Agustus ketika barang jadinya baru ada 24 Agustus. Alokasikan koreksi ke barang jadi sejak tanggal fisiknya dan ke HPP untuk bagian yang terjual, dengan tanggal jurnal mengikuti aturan periode terbuka/tertutup yang sudah diputuskan. Pertahankan pemeriksaan saldo negatif per tanggal. Tolong uji ulang empat kasus INVOICE, saldo harian, laporan menurut tanggal, serta tutup buku sebelum menyatakan beres. 12 HOLD historis tetap HOLD sampai dibuktikan dan diputus terpisah."
- Status: dikerjakan sebagai AY, lihat 22.2b. Versi akhir AY rev3: T2 run 10 mengembalikan ke-16 kasus ke hasil AU tanpa memindahkan kasus lain. Yang tersisa adalah keputusan oracle untuk 8 kasus AS (22.2b).

### 22.2b AY: koreksi HPP invoice terlambat diberi tanggal sejak barang jadinya ada (keputusan owner 24 Sep)

**Isi perubahan (AY rev3, versi akhir).** Hanya satu fungsi yang diganti: `erp.sync_po_hpp_to_gl(uuid,date)`, ditambah satu helper `erp.po_hpp_gl_leg_add_v1` (IMMUTABLE SQL, tanpa akses tabel). Sumber T1: `supabase/dev/cp6_ay_t1_family.sql` (dibangun oleh `scripts/cp6_ay_build.py` dari teks AS). Kandidat rilis: `supabase/release/cp6-t3/20260924010200_erp_v2_6_20ay_cp6_hpp_dated_from_goods.sql`, dengan guard yang sama seperti AW/AX. Tidak ada tabel baru dan tidak ada perubahan data saat instalasi.

Cara selisih HPP satu PO (FG, HPP terjual, dan lawannya WIP) diposting:
- **Bila E (tanggal ekonomi invoice) sudah ditutup:** tidak ada yang berubah dibanding sebelum AY. Semua kaki tetap pada E, jadi hasilnya satu jurnal dengan tanggal ekonomi E, dan `post_journal` memostingnya pada hari pengakuan menurut aturan yang sudah diputuskan (`resolve_accounting_transaction_date`: hari ini atau hari pertama sesudah tanggal tutup). Laporan sebelum hari itu tidak berubah, dan tanggal ekonominya tetap tercatat.
- **Bila E masih terbuka**, selisihnya dibagi ke tanggal fisik:
  - **Kaki A, per lot barang jadi:** tanggalnya `greatest(E, tanggal bisnis lot)`. Bobotnya pcs output lot. Seluruh selisih lot itu (bagian yang masih di gudang maupun yang sudah terjual) masuk ke FG_INVENTORY pada tanggal itu, dengan lawan WIP.
  - **Kaki B, per penjualan/retur:** pada `greatest(tanggal kaki A lotnya, tanggal penjualan atau retur)`, bagian yang terjual dipindah dari FG_INVENTORY ke COGS (retur ke arah sebaliknya). Bobotnya pcs terjual bersih.
- Pembulatan sen dengan sisa ke baris terakhir, jadi total per akun sama persis dengan total lama.
- Satu event dan satu jurnal per tanggal yang dihasilkan. `post_journal` tidak diubah.
- Pemeriksaan saldo negatif per tanggal (`GL_INVENTORY_NEGATIVE_ASOF`, AW) **tidak diubah**.

**Contoh angka (kasus AY:LATE_INVOICE_LOWER_OPEN_RECEIPT_DAY):**
- bahan diterima 21 Sep dengan harga estimasi; barang jadi dan penjualan 22 Sep; invoice datang dengan harga Rp8,25 (lebih murah); periode masih terbuka.
- **Sebelum AY:** satu event bertanggal 21 Sep (FG −5,25, COGS −3,50). Saldo FG 21 Sep = −5,25 → engine BLOCKED, tutup buku ditolak.
- Selisih per pcs −1,75: 3 pcs masih di gudang (FG −5,25) dan 2 pcs terjual (COGS −3,50); lawannya WIP +8,75.
- **Sesudah AY:** event bertanggal 22 Sep, hari barang jadi dan penjualan: FG −5,25, COGS −3,50. Laporan 21 Sep untuk FG dan COGS tidak berubah, tidak ada saldo negatif harian, engine READY, tutup buku diterima.
- Revaluasi bahan (GRNI/bahan → WIP, −17,50) tetap bertanggal 21 Sep, lihat catatan di akhir bagian ini.

**Bukti T1 (label T1_FAMILY, bukan bukti rilis):**
- Teks pertama, run 35950629646 (`docs/evidence/cp6-ay/native_t1_run35950629646_{before,after}.json`): 5 kasus. Sebelum AY 3 COUNTEREXAMPLE + 2 PASS, sesudah 5/5 PASS. Kombinasi hari terima tertutup dengan barang jadi terbuka belum diuji, dan justru di situ kesalahannya (lihat di bawah).
- AY rev2, run 35952201365 (`docs/evidence/cp6-ay/native_t1_run35952201365_{before,after}_rev2.json`): 7 kasus, sesudah 7/7 PASS. Probe ini belum memeriksa tanggal ekonomi jurnal, sehingga kesalahan rev2 lolos T1 dan baru tertangkap T2 run 9.
- **AY rev3 (versi akhir), run 35952988290** (`docs/evidence/cp6-ay/native_t1_run35952988290_{before,after}_rev3.json`): 7 kasus plus cek tanggal jurnal. Sebelum AY 3 COUNTEREXAMPLE + 4 PASS, sesudah **7/7 PASS**. Primary tidak berubah dan clone 0 di kedua fase.

| Kasus (AY rev3) | Sebelum AY | Sesudah AY rev3 |
|---|---|---|
| LATE_INVOICE_LOWER_OPEN_RECEIPT_DAY (UTC) | COUNTEREXAMPLE: event dan jurnal 21 Sep, FG −5,25 pada hari terima, close ditolak | PASS: event dan jurnal 22 Sep (ekonomi = posting), FG −5,25, COGS −3,50 |
| LATE_INVOICE_LOWER_OPEN_KIRITIMATI | COUNTEREXAMPLE (sama) | PASS |
| LATE_INVOICE_HIGHER_OPEN_RECEIPT_DAY (harga naik) | COUNTEREXAMPLE: kenaikan dicatat sebelum barangnya ada | PASS: +2,10 FG / +1,40 COGS pada 22 Sep |
| LATE_INVOICE_LOWER_CLOSED_HISTORY (tutup s/d hari barang jadi) | PASS: jurnal ekonomi 21 Sep, posting 24 Sep | PASS: sama persis dengan sebelum AY |
| LATE_INVOICE_HIGHER_CLOSED_HISTORY | PASS | PASS |
| LATE_INVOICE_LOWER_CLOSED_RECEIPT_OPEN_GOODS (tutup s/d hari terima saja) | PASS: ekonomi 21 Sep, posting 24 Sep | PASS: sama; laporan 22 dan 23 Sep tidak berubah |
| LATE_INVOICE_HIGHER_CLOSED_RECEIPT_OPEN_GOODS (Kiritimati) | PASS | PASS |

Setiap kasus memeriksa: nilai pada harga estimasi dan harga invoice, tanggal ekonomi dan posting jurnal HPP, tanggal event tidak mendahului barang jadi (atau tepat pada hari pengakuan bila hari terima tertutup), total event, laporan hari terima (FG/COGS tidak berubah), laporan hari barang jadi, saldo harian tidak negatif, jawaban engine untuk hari barang jadi, dan tutup buku sesudah invoice. Untuk kasus dengan hari terima tertutup, laporan hari barang jadi dan hari sebelum hari ini juga wajib tidak berubah. Primary tidak berubah dan clone 0 di kedua fase.

**Dua kesalahan writer yang ditangkap T2 sebelum AY dinyatakan beres:**
- **Run 8 (35950787577, AY teks pertama).**
  - Hasil baik: 16 kasus temuan 22.2a kembali ke hasil AU. 4 INVOICE `*:4:False` kembali CONTROL_PASS, dan 12 HOLD historis kembali ke DATE_POLICY_REVIEW_REQUIRED (tetap HOLD).
  - Hasil buruk: kasus dengan **hari terima sudah ditutup** ikut berpindah, yaitu 28 kasus BUSINESS (8 `CROSS:INVOICE:True:*`, 8 `INVOICE:*:{4,7}:True`, 12 `CALENDAR:*:True`) dan 8 kasus AS `DATE:True:*:True:*`.
  - Penyebab: aturan buka/tutup saya terapkan per tanggal kaki. Bila hari terima tertutup tetapi hari barang jadi masih terbuka, sebagian koreksi masuk ke hari barang jadi (22 Sep), padahal invoice baru datang 23 Sep, sehingga laporan hari-hari sebelum invoice ikut berubah.
  - Bukti: `docs/evidence/cp6-t2/run35950787577_ay_first_text.json`.
- **Run 9 (35952233525, AY rev2).**
  - Rev2 menaruh koreksi atas penerimaan tertutup pada tanggal pengakuan (`v_from`).
  - Hasil: BUSINESS, IMPORTS, dan VALUES kembali sama dengan AU, tetapi 3 kasus AR menjadi INCOMPLETE: `PRODUCTION_ORIGIN:LAUNDRY:True:False` dan `POCKET_PERIOD_LIFECYCLE:*:True`.
  - Penyebab: oracle AR (beku) mensyaratkan jurnal itu bertanggal ekonomi E dan bertanggal posting hari ini, seperti sebelum AY. Rev2 memberinya tanggal ekonomi hari ini, sehingga tanggal ekonomi aslinya hilang.
  - Bukti: `docs/evidence/cp6-t2/run35952233525_ay_rev2.json`.
- **Rev3 (versi akhir):** bila E tertutup, semua kaki tetap pada E, persis seperti sebelum AY. Hanya E yang terbuka yang digeser ke tanggal barang jadi.
  - Uji logika lokal mencakup: tertutup s/d hari terima, tertutup s/d hari barang jadi, dua lot dengan penjualan dan retur sesudahnya, dan E terbuka.
  - Probe T1 mendapat 2 kasus `CLOSED_RECEIPT_OPEN_GOODS` dan cek tanggal jurnal (tertutup: ekonomi d, posting hari ini; terbuka: ekonomi = posting, pada/sesudah hari barang jadi).
  - `ay_verified` mewajibkan badan fungsi terpasang sama persis dengan teks AY yang di-commit.

**8 kasus AS `DATE:False:*:True:*` (hari terima terbuka, sebagian sudah diproduksi) — perlu keputusan owner/GPT atas oracle:**
- Oracle AS (beku di `ca7f095`, ditulis sebelum keputusan 24 Sep) mengharapkan event dan jurnal HPP PO pada tanggal ekonomi invoice (hari beli, 21 Sep).
- AY menaruhnya pada hari barang jadi (22 Sep), sesuai keputusan owner. Contohnya: harga naik Rp10 → Rp20 untuk 10 unit, 3 pcs di gudang (+30) dan 2 pcs terjual (+20). Sebelum AY, kenaikan FG +30 tercatat 21 Sep, padahal barangnya baru ada 22 Sep.
- Selain tanggal jurnal `PO_HPP_GL_SYNC` itu tidak ada yang berbeda: nominal sama, revaluasi bahan (WIP) dan jurnal invoice pemasok tetap 21 Sep.
- Oracle tidak diubah dan kasusnya **tidak** disebut lulus. Yang diusulkan: hasil yang diharapkan untuk event/jurnal HPP PO menjadi `greatest(tanggal ekonomi invoice, tanggal barang jadi)`, sisanya tetap.

**Uji ulang yang diminta owner (AY rev3):** T2 run 10 (35952990109, head 8b1d555, `docs/evidence/cp6-t2/run35952990109_ay_rev3_final.json`):
- 4 kasus INVOICE `*:4:False` kembali CONTROL_PASS, sama dengan AU. Di run 5/6 keempatnya tertahan `GL_INVENTORY_NEGATIVE_ASOF`; kini tidak lagi.
- 12 HOLD historis kembali ke DATE_POLICY_REVIEW_REQUIRED, dan statusnya **tetap HOLD** sampai dibuktikan dan diputus terpisah.
- Tidak ada kasus lain yang berpindah dari AU: AR 146/146 + 28/28 race, BUSINESS 230/230, IMPORTS 31/31, VALUES 65/65, temporal 16 + 15 kasus dan 4 + 6 race PASS.
- NEW_CASES: 26 PASS; 8 kasus AS menunggu keputusan oracle (di atas).
- Saldo harian, laporan per tanggal, dan tutup buku juga diuji langsung di T1 rev3 (7 kasus, tabel di atas). T3 akhir (run 35953286010) memasang paket 23 file dengan AY rev3.

**Belum diubah, diusulkan terpisah (prinsip sama, belum diputus owner):** revaluasi bahan yang sudah dipakai (`sync_material_cost_revaluation`, MATERIAL/GRNI → WIP) masih bertanggal E. Bila pemotongan bahannya terjadi sesudah E dan WIP pada hari itu kosong, WIP bisa negatif di antara E dan hari potong. Contoh: bahan diterima 1 Sep, dipotong 3 Sep, invoice turun Rp1,00/unit untuk 10 unit → WIP 1–2 Sep −10. Di seed T2 hal ini tertutup karena WIP seed besar; belum ada kasus yang membuktikannya secara native. Usulan: tanggal revaluasi WIP = `greatest(E, tanggal potong)`. Perlu keputusan owner sebelum dikerjakan.

### 22.2c AX: upah perbaikan BS temuan di atas Rp0 (keputusan owner 24 Sep: "Utang, dibayar via payroll")

Contoh owner: BS temuan diperbaiki menjadi GOOD, nilai dasar Rp52.000 dan ongkos perbaikan Rp2.000 → nilai akhir Rp54.000/pcs.

**Isi perubahan (di dalam AX, bukan file baru):**
- `post_fg_unsourced_receipt_v1` menerima objek `repair` (tarif per pcs > 0 dengan paling banyak 2 desimal, alasan, kontraktor, komponen) **hanya** untuk GOOD dari BS temuan. Jurnal: Dr FG_INVENTORY (nilai dasar + upah) / Cr pendapatan lain (nilai dasar, jalur lama) / Cr CONTRACTOR_PAYABLE (upah). Unit lot = nilai dasar + tarif.
- Tabel baru `erp.fg_unsourced_repair_wages_v1` (RLS aktif, semua hak dicabut, immutable kecuali lewat pembatalan AX).
- Upah muncul sebagai baris kerja payroll `FG_REPAIR` kontraktor itu. Payroll mengambilnya seperti upah biasa. Persetujuan payroll tidak membuat jurnal kedua untuk upah ini (di bukti: 0 jurnal persetujuan), jadi utang tidak dobel; `post_payroll_payment` melunasi utangnya.
- Pembatalan penerimaan ditolak (`FG_UNSOURCED_REPAIR_WAGE_IN_PAYROLL`) selama upahnya ada di payroll yang belum dibatalkan. Sesudah payroll dibatalkan, pembatalan penerimaan juga membatalkan baris upahnya.
- Empat objek payroll dasar diganti agar mengenal sumber `FG_REPAIR`: `merge_eligible_work_into_payroll_v2`, `validate_payroll_work_item_source`, view `v_payroll_eligible_work_lines`, dan CHECK `payroll_work_items.source_type`.

**Bukti:**
- T1 AX run 35949833558: 32 PASS + 1 OBSERVED (`docs/evidence/cp6-ax/native_t1_run35949833558_after_repair_wage.json`). Tiga kasus baru:
  - REPAIR_WAGE_PAYROLL: 2 pcs, dasar Rp17 (rata-rata stok uji), tarif Rp2.000 → unit Rp2.017, total Rp4.034; utang kontraktor Rp4.000; payroll FG_REPAIR 2 pcs Rp4.000, APPROVED tanpa jurnal persetujuan tambahan; pembatalan ditolak selama di payroll; sesudah dibayar utang 0.
  - REPAIR_WAGE_CANCEL_THEN_REVERSE: payroll dibatalkan lalu penerimaan dibatalkan; upah REVERSED, BS kembali OPEN, utang 0, edit langsung ditolak.
  - REPAIR_WAGE_REFUSALS: 9 penolakan dengan kodenya sendiri (bukan BS temuan, tarif 0/negatif/NaN/3 desimal/teks, tanpa alasan, kontraktor atau komponen tidak dikenal).
- T3 run 35950297492: paket 22 file dengan AX baru terpasang di baseline setara Enteng, capture ulang identik, browser 10/10 (`docs/evidence/cp6-t3/run35950297492_package22_repair_wage.json`).
- T2 run 7 (35950296669, head bc650c3): hasil semua grup sama dengan run 6, tidak ada kasus baru yang berpindah (`docs/evidence/cp6-t2/run35950296669_repair_wage_no_ay.json`).

UI (form upah perbaikan) adalah pekerjaan CP7; backend-nya sudah siap.

### 22.3 T3: paket rilis gabungan (G-01 opsi b)

**Mengapa paket ulang:** di baseline yang sudah disamakan dengan Enteng, jalur beku menolak di AC (run 35911530080, `AC_VIEW_PREDECESSOR_MISMATCH: erp.v_payroll_nota_browser`), karena beberapa guard mengunci teks yang hanya ada di rantai fixture uji. Sesuai keputusan owner:
- file migrasi lama tidak diubah;
- salinan paket di `supabase/release/cp6-t3/` mengambil pin dari rantai yang sudah disamakan;
- **tidak ada guard yang dilonggarkan**; yang berubah hanya nilai yang diharapkan.

**Isi paket:** 23 file, AC..AV ditambah kandidat rilis AW, AX, dan AY (sumbernya `supabase/release/cp6-t3-src/`, dibangun oleh `scripts/cp6_t3_awx_release.py`). Angka substitusi di tabel ini dari paket 22 file; AY menambah substitusinya sendiri dengan jenis yang sama. Setiap substitusi tercatat di `MANIFEST.json` dan termasuk salah satu dari empat jenis:

| Jenis | Jumlah | Isi |
|---|---|---|
| AC_VIEW | 2 | Sumber `v_payroll_nota_browser` diganti bentuk IN-list yang di-parse menjadi teks Enteng; ikut sha256 statement restore-nya. |
| LEDGER | 42 | sha256 statement file pendahulu yang ikut di-pin ulang (berantai). |
| CATALOG | 20 | Jumlah objek dan fingerprint katalog erp/public sebelum dan sesudah AO..AX, dihitung dengan query guard itu sendiri. |
| CAPSULE | 16 | Hash kapsul historis yang isinya berbeda di rantai yang disamakan. |

**Sesudah audit (22.5):**
- AW/AX dibangun ulang dengan guard lengkap. Capture di rantai nyata (run 35943232759) memasang ke-22 file dari sumber.
- Pin AC..AV identik dengan yang sudah di-commit; hanya pin AW/AX yang baru (blob `079b4b1d…`, 47122 byte). Jumlah substitusi AW: LEDGER 20, CAPSULE 10, CATALOG 2. AX: LEDGER 21, CAPSULE 11, CATALOG 2.
- Paket dibangun ulang dengan `build` yang memvalidasi: AC..AV identik byte per byte; hanya AW, AX, dan `MANIFEST.json` yang berubah.
- **Hasil akhir (run 35943599257, `docs/evidence/cp6-t3/run35943599257_package22_guarded.json`):**
  - baseline: katalog sama dengan ringkasan Enteng di 16 jenis, dan 11/11 kapsul sama (keduanya kini wajib);
  - install: 22/22 PASS, AW/AX terverifikasi, primary tidak berubah;
  - capture ulang: pin identik (determinisme);
  - browser: 10/10 PASS dengan status job yang kini mengikuti hasil alur.

**Paket 23 file (AY, 24 Sep):**
- Run 35950297492 (paket 22 file dengan AX + upah perbaikan): lulus penuh (`docs/evidence/cp6-t3/run35950297492_package22_repair_wage.json`).
- Run 35950787494: paket 22 file yang di-commit terpasang, lalu **ditolak di `AY_T1_MARKER`** karena kandidatnya kini memuat AY. Ini sesuai rancangan (fail-closed). Capture di run yang sama mengambil pin 23 file; paket dibangun ulang dengan AC..AX identik byte per byte.
- Run 35951093685 (AY teks pertama): lulus penuh (`docs/evidence/cp6-t3/run35951093685_package23_ay.json`), tetapi teks AY itu kemudian diganti rev2 (22.2b).
- Run 35952201363: paket yang di-commit masih memuat teks AY lama, dan **ditolak di `AY_T1_SYNC_NOT_CURRENT`**. Cek baru ini mewajibkan badan fungsi terpasang sama persis dengan teks AY yang di-commit. Capture mereproduksi semua pin kecuali AY, tetapi job-nya tetap hijau; kini job capture merah bila pin berbeda dengan paket yang di-commit.
- Run 35952446339 (AY rev2, head 958c286, `docs/evidence/cp6-t3/run35952446339_package23_ay_rev2.json`), digantikan rev3:
  - install: 23/23 PASS, AW/AX/AY terverifikasi;
  - capture: pin identik dengan yang di-commit (blob `25212130…`, 55928 byte);
  - katalog: 16 jenis sama dengan Enteng, dan 11/11 kapsul sama;
  - drill restore ketat: RESTORED_SAME_MEANING;
  - advisor: 73 → 124 (+51 INFO);
  - browser: 10/10 PASS, 0 error konsol;
  - primary tidak berubah.
- Run 35952758220 (paket AY rev2, head 311e0cc): lulus penuh, tetapi digantikan rev3.
- Run 35952988259 (head 8b1d555, sumber AY rev3 dengan paket AY rev2): install ditolak di `AY_T1_SYNC_NOT_CURRENT`, capture merah dengan `T3_COMMITTED_PACKAGE_STALE` (hanya AY berbeda). Keduanya sesuai rancangan. Paket dibangun ulang dari pin itu (blob `1ec41066…`); hanya file AY dan MANIFEST yang berubah.
- **Run 35953286010 (AY rev3, head b242d45, versi akhir):** `docs/evidence/cp6-t3/run35953286010_package23_ay_rev3_final.json`
  - install: 23/23 PASS, AW/AX/AY terverifikasi (badan AY sama persis);
  - capture: pin identik dengan yang di-commit (blob `1ec41066…`, 55928 byte);
  - katalog: 16 jenis sama dengan Enteng, dan 11/11 kapsul sama;
  - drill restore ketat: RESTORED_SAME_MEANING (315 tabel identik);
  - advisor: 73 → 124 (+51 INFO saja);
  - browser: 10/10 PASS, 0 error konsol, 0 user Auth tersisa;
  - primary tidak berubah.

Hasil pada paket 22 file versi sebelum audit (run 35941885984, `docs/evidence/cp6-t3/run35941885984_package22.json`):
- 22/22 file terpasang;
- pin diambil ulang dan identik (blob sha256 `55aca6bc…`, 33799 byte, sama dengan run sumber pin 35940962700);
- AW/AX terverifikasi;
- kapsul hosted 11/11 sama;
- browser 10/10 PASS;
- primary tidak berubah, 0 user Auth tersisa.

Belum diuji (NOT_TESTED):
- file rollback paket;
- prosedur rilis ke hosted (CP8). Ledger ditulis dengan `statements` = seluruh teks file, jadi rilis nyata harus memakai stempel versi yang sama persis dan database yang ditutup. Supabase CLI biasa memecah statement, dan itu akan ditolak oleh guard ledger penerus.

### 22.4 Selisih kapsul v2.6.20 (dijelaskan dan disamakan)
- **Temuan:** perbandingan hash kapsul historis dengan Enteng (baca-saja, hanya hash) menemukan satu selisih, `erp.cp6_v2620_rollback_capsule`. Selisih ada di dua baris view (`v_fg_partial_completion_progress`, `v_wip_control_status_v1`) dan hanya pada teks definisi serta sha256-nya.
- **Penyebab:** v2.6.20 sendiri menyimpan `pg_get_viewdef(view,true)`, yang bukan titik tetap parse/deparse. v2.6.20 menerima dua hash, milik hosted dan milik replay CI. Rantai fixture menyimpan teks replay, hosted menyimpan teksnya sendiri. Maknanya sama, byte-nya beda.
- **Hipotesis awal yang salah:** saya sempat mengira penyebabnya urutan ACL. Itu salah dan sudah dicatat.
- **Perbaikan:** `scripts/cp6_g01_align.py` menulis teks hosted ke dua baris itu di baseline disposable, dan hanya bila hasilnya persis sama dengan sha256 hosted. Hasilnya 11/11 kapsul sama.
- **Gerbang baru (audit no. 3):** runner kini **menolak** bila ada kapsul yang tidak sama dengan hosted. Setelah penyelarasan, rantai juga membandingkan seluruh katalog dengan ringkasan hosted.

### 22.5 Audit independen alat T2/T3 (sub-agent baca-saja, 24 Sep) dan tindak lanjutnya

Auditor membangun ulang sumber AW/AX dan ke-22 file paket dari `release_pins.json`, dan hasilnya identik byte per byte. Pin kapsul dan rantai pin katalog (AV → AW → AX) juga benar. Tujuh temuan:

| No | Temuan | Perbaikan | Bukti |
|---|---|---|---|
| 1 | Status job browser tidak bergantung pada hasil alur. Alurnya sendiri tetap 10/10 PASS, tetapi job akan hijau walau gagal. | Status = hasil alur. Job merah kecuali 10/10 PASS dan kandidat terverifikasi ulang. Semua mode merah kecuali seluruh kandidat terpasang. | `scripts/cp6_t3_package_run.py` |
| 2 | Guard AW/AX lebih sedikit daripada AO..AV: tanpa kapsul historis, tanpa cek kapsul AO..AV, predecessor hanya satu, tanpa kapsul rollback, tanpa hash data. | Semua guard itu ditambahkan (daftar di bawah tabel). | Self-test lokal: keduanya terpasang, 10/10 perusakan ditolak dengan kodenya sendiri (`docs/evidence/cp6-t3/awx_guard_selftest_local.json`) |
| 3 | Pin diambil dari clone tanpa dicek terhadap hosted. Sudah pernah terjadi: pin kapsul v2.6.20 memakai nilai fixture. | Seluruh katalog wajib sama dengan ringkasan hosted setelah penyelarasan (kecuali stempel ledger platform). Setiap kapsul hosted wajib sama, kalau tidak runner menolak. | `scripts/cp6_t3_aligned_chain.py`, `cp6_t3_package_run.py` |
| 4 | `build` mempercayai substitusi CATALOG/CAPSULE apa adanya dan tidak memeriksa kelengkapan pin. | Pin wajib mencakup seluruh paket secara berurutan. Tiap substitusi harus satu jenis yang direview dan mengganti tepat satu pin guard di filenya. Bentuk guard dicek ulang. sha256 blob pin dicatat (dan dicek bila diberikan). | Pin lama membangun ulang 22 file byte per byte; 4 pin palsu ditolak |
| 5 | Status RESTORED_SAME_MEANING drill terlalu longgar. | Setiap galat pg_restore harus soal pg_cron dan tanpa job cron di sumber. Semua skema non-sistem dibandingkan. Jawaban engine wajib ada. Nilai IN-list dibandingkan sebagai list JSON. Setiap jenis yang berbeda wajib punya objek yang dijelaskan. | `scripts/cp6_t3_backup_restore_drill.py` |
| 6 | Pembersih seed T2: tanggal tutup dikodekan mati, hanya 120 hari yang dibersihkan, rentang yang dibuka tidak dicek engine, langkah gagal ditelan, diagnostik membaca di luar try. | Tanggal tutup dibaca, seluruh rentang yang dibuka dibersihkan, engine wajib menjawab READY untuk rentang itu, dan langkah yang ditolak menghentikan grup. Diagnostik jadi opsional dan diisolasi savepoint. | run 4 |
| 7 | Beberapa klaim bukti melebihi data. | Catatan `review_20260924` ditambahkan ke bukti lama (atribusi "fixture kasus" masih inferensi untuk yang tidak didiagnosis, arti INCOMPLETE, baseline lama belum setara hosted), dan bukti run 35941885984 ditulis. | `docs/evidence/cp6-t2/…`, `docs/evidence/cp6-t3/…` |

Guard yang ditambahkan ke AW/AX (temuan no. 2):
- setiap file paket sebelumnya ada di kedua ledger dengan sha256 persis;
- hash semua kapsul historis, termasuk AO..AV (dan AW untuk AX);
- cek keamanan, bentuk, dan boundary kapsul AO..AV, sama seperti AV;
- kapsul rollback sendiri (AW: 2 fungsi yang diganti; AX: tidak ada), yang dibuktikan lengkap terhadap semua fungsi erp/public;
- hash sebelum/sesudah semua tabel erp: instalasi tidak mengubah data dan tabel baru tetap kosong.

Catatan auditor yang juga ditindaklanjuti:
- REFUSED kini hanya untuk penolakan guard (SQLSTATE P0001); galat lain menjadi ERROR/INCOMPLETE.
- Verifikasi browser mengecek seluruh katalog terhadap pin terpasang file terakhir.
- Indeks AO tidak lagi dikodekan mati.

Yang dicatat tanpa diubah:
- guard Python memakai `assert`, jadi jangan dijalankan dengan `-O` (CI tidak memakai `-O`);
- urutan `sys.path` penulis/auditor: modul yang tertimpa saat ini identik.

### 22.6 Browser, drill, advisor, CodeQL
- **Browser:** alur AU yang tidak diubah (Auth/JWT nyata, PostgREST publik hanya ke clone, UI cabang ini). Hasilnya 10/10 PASS, 0 error konsol. Sesudah alur, kandidat diverifikasi ulang, termasuk seluruh katalog terhadap pin terpasang file terakhir (kini AY). Tidak ada user Auth dan container REST yang tersisa.
- **Drill backup/restore (aturan ketat):** RESTORED_SAME_MEANING, dengan semua pengecekan benar:
  - 311 tabel (paket 22 file) dan 315 tabel (paket 23 file, run akhir) di 8 skema (erp, auth, storage, vault, realtime, _realtime, supabase_functions, supabase_migrations) identik;
  - 19 galat pg_restore, semuanya soal pg_cron (hanya bisa ada di database `postgres`), dan 0 job cron di sumber;
  - selisih katalog seluruhnya bentuk IN-list varchar yang di-parse ulang (29 constraint, 1 indeks, 6 view) ditambah ekstensi pg_cron;
  - jawaban engine AW untuk kemarin READY di sumber maupun hasil restore.
- **Advisor keamanan Supabase:** 73 → 122 pada paket 22 file, dan 73 → 124 pada paket 23 file. Semua tambahan INFO `rls_enabled_no_policy`: 49 untuk tabel yang dibuat AC..AX (kapsul rollback, tabel import/pocket, tabel AV/AW/AX), +1 tabel upah perbaikan AX, dan +1 kapsul rollback AY. Tidak ada WARN atau ERROR yang bertambah atau hilang. Siapa yang bisa mengakses tabel itu ditentukan ACL, yang ikut di-pin di katalog tiap file. Advisor tidak memeriksa ACL, dan `service_role` melewati RLS.
- **CodeQL:** workflow `cp6-candidate-codeql.yml` (security-extended) dijalankan manual di head `13dbcb1` (run 35944124414). Keempat bahasa (actions, javascript-typescript, python, c-cpp) lolos gerbang `scripts/cp6_codeql_artifact_gate.py` dengan 0 temuan; gerbang itu gagal bila ada satu temuan saja. Diulang di head `311e0cc` (run 35952781538, AY rev2) dan terakhir di head `b242d45` (run 35953312746, semua kode AX upah perbaikan dan AY rev3 sudah masuk; sesudahnya hanya dokumen dan bukti yang berubah): keempat bahasa lulus gerbang dengan 0 temuan.

### 22.7 Akses hosted di sesi ini
- Log dibuat dari transkrip saja, tanpa menjalankan apa pun: `docs/evidence/hosted_access_log_20260924.json`.
- Isinya 21 panggilan Supabase:
  - 18 `execute_sql`, 2 di antaranya tidak jadi dijalankan;
  - 0 `apply_migration`;
  - 20 ke Enteng, 0 ke legacy;
  - **0 yang menulis data atau skema**.
- Setelah owner meminta berhenti, tidak ada SQL ke hosted lagi. Semua pekerjaan sesudahnya hanya di CI disposable dan Postgres lokal sekali pakai.

### 22.8 Yang belum selesai (jujur)
- **Rollback paket T3:** NOT_TESTED, termasuk file rollback AW/AX/AY yang belum ada.
- **Prosedur rilis CP8:** stempel versi persis, `statements` utuh, database ditutup. Belum dibuat.
- **T2:** 8 kasus AS `DATE:False:*:True:*` menunggu keputusan owner/GPT atas oracle (22.2b). Hasil lain run 10 sama dengan AU.
- **Upah perbaikan BS temuan > Rp0:** selesai di backend (22.2c). Form UI-nya pekerjaan CP7.
- **Saldo barang jadi negatif setelah invoice terlambat (22.2a):** dikerjakan sebagai AY rev3 (22.2b). Masih terbuka dua hal: keputusan atas oracle 8 kasus AS `DATE:False:*:True:*`, dan usulan tanggal revaluasi WIP. Keduanya menunggu owner/GPT.
- **Konversi lot non-PO:** backlog (§21.6).
- **HOLD tetap:** 12 HOLD historis tetap HOLD, dan CP6 tetap HOLD.

### 22.9 Kesalahan metode writer di putaran ini
- **Pembersih seed T2 terlambat:** baru disiapkan sesudah run 1 menunjukkan 152 perpindahan akibat seed. Seharusnya dipetakan sebelum run pertama.
- **T3 tanpa analisis statis lebih dulu:** T3 dijalankan sebelum analisis statis guard mana yang mengunci teks fixture. Akibatnya tiga run terbuang.
- **AY butuh tiga teks:**
  - Teks pertama menerapkan aturan buka/tutup per tanggal kaki, bukan pada tanggal pengakuan invoice.
  - Rev2 memperbaiki itu, tetapi membuang tanggal ekonomi asli jurnal.
  - T1 hanya menguji sebagian kombinasi status periode dan belum memeriksa tanggal ekonomi jurnal, sehingga kedua kesalahan baru tertangkap T2 (run 8 dan run 9).
  - Karena owner meminta uji ulang T2 sebelum menyatakan beres, tidak ada versi yang sempat disebut beres.
  - Pelajaran: untuk perubahan tanggal, sebelum T1 daftar semua kombinasi status periode (terbuka/tertutup) untuk setiap tanggal yang disentuh, lalu periksa **kedua** tanggal jurnal (ekonomi dan posting) terhadap perilaku lama pada kombinasi yang tidak dimaksudkan berubah.
- **Job capture T3 hijau walau pin berbeda:** perbandingannya hanya dicatat, tidak menentukan status job. Sudah diperbaiki; jenis celahnya sama dengan temuan audit no. 1.
- **Klaim di depan bukti:** beberapa klaim alat dan bukti mendahului buktinya (browser hijau, "same guard pattern" untuk AW/AX, drill longgar). Audit independen menangkapnya, dan semua sudah diperbaiki di 22.5. Pelajaran: sebelum menyebut guard "setara", uji dengan perusakan (sekarang ada self-test lokal).

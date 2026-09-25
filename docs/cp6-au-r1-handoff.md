# Handoff Claude → ChatGPT — AU-R1 dan kandidat successor AV

Tanggal: 23 September 2026 (WIB). Writer: Claude Code (sesi cloud). Peninjau berikutnya: ChatGPT.

> **Pembaruan terbaru (25 September 2026, putaran 9, `WRITER_HANDOFF_R9_20260925.md`): baca §29.**
> - §29: W1–W13 dari handoff auditor putaran 9.
>   - **Produk:** W8 sen multi-penerimaan (ternyata regresi BA), W9 `changed_since_filing` sesuai C0 §3.4, LAU-T14
>     (penerimaan laundry memakai tarif saat kirim, ditemukan saat inventaris C6), W10/W11/W13 di frontend.
>   - **Alat:** W7 grup ketat race/HTTP, W2 grup oracle C0 di T2 (25/25), W4 INCOMPLETE terstruktur, dan cek data cutover
>     (UUID + alias CASH_BANK).
>   - **Dokumen:** lampiran C6 rev2 dengan crosswalk 75 ID, dan inventaris jalur impor 22 keadaan ALL.
>   - Hasil CI di §29.5. Pertanyaan owner (D06 dan scope ALL) di §29.8.
> - CP6 tetap HOLD, `audit_complete=false`, `production_go=false`.
>
> **Pembaruan sebelumnya (25 September 2026, perbaikan audit independen `AUDIT_WRITER_HANDOFF_CP6.md`): baca §28.**
> - §28: keluarga BA (A1, A3, A4, A5, A6, A9, A10) dan A2 di frontend; regresi T2 akibat BA ditemukan dan diperbaiki; alat B1–B6 (grup ketat dan self-test, gate T3, rollback AC..BA varian rilis dengan siklus penuh dan matriks post-use, mode browser, ringkasan fixture, identitas run); addendum C0: D01–D05 disahkan tertulis owner (25 Sep, bagian 9 addendum); D06 menunggu tinjauan auditor atas draf lampiran C6.
> - Produk acuan `a095a9d`; hasil CI di §28.6; cara menjalankan ulang di §28.8. A7 dan A8 (opsional) belum dikerjakan.
> - Penerimaan independen menunggu rerun auditor. MATCH adalah oracle yang disetujui, bukan PASS kasus beku. Label T1_FAMILY/T2_REGRESSION/T3_PREP/AUDITOR_SCENARIO, bukan bukti rilis.
> - CP6 tetap HOLD, `audit_complete=false`, 12 HOLD historis tetap HOLD, `production_go=false`.
>
> **Pembaruan sebelumnya (24 September 2026, tindak lanjut audit GPT atas `737649b`): baca §27, lalu §26, §25, §24, dan §23.**
> - §27: AB-01 (pembalikan pemakaian kain kantong) terbukti native lalu diperbaiki; AB-02 fixture; AB-03 arsip T3/CodeQL; runtime **CP6 Auditor Scenario** untuk skenario auditor sendiri; T1/T2/T3/CodeQL akhir pada `208afce`.
> - §26 menutup sisa keluarga ini: AY rev7.2–rev7.4 (revaluasi pada harinya, pengenceran batch, kain kantong per pool, bahan potong yang dibatalkan keluar dari HPP), AZ rev2/rev2.1 (kantong, BS impor awal, lot pembuka non-PO, recost aksesori, invoice dan koreksi harga bertanggal sebelum barang diterima, gerakan potong dan penghapusan bahan yang dibalik dinilai ulang pada harinya), keputusan owner opsi 1, pemeriksaan independen `b110e54` beserta disposisinya, dan T1/T2/T3/CodeQL akhir.
> - Yang masih terbuka ada di §26.7 (kecuali pembalikan kain kantong, ditutup di §27.1). Penerimaan independen rev7.4/rev2.1 masih RERUN_REQUIRED. Tidak ada keputusan owner yang tertunda.
> - §25 berisi AY rev7/rev7.1: setiap fakta bahan dicatat pada hari fisiknya, relabel tidak berayun lewat akun lain, dan kinerja dengan running sum serta JIT dimatikan.
> - §24 berisi riwayat rev6/rev6.1. §23 berisi keputusan owner, oracle yang disetujui, AZ, dan penelusuran `ADJUSTMENT_DATE`.
> - MATCH adalah oracle yang disetujui, bukan PASS kasus beku. Semua bukti berlabel T1_FAMILY/T2_REGRESSION/T3_PREP, bukan bukti rilis.
> - CP6 tetap HOLD, 12 HOLD historis tetap HOLD, `production_go=false`.

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

## 23. Putaran keempat: 8 kasus AS, keluarga AZ (bahan → WIP → barang jadi → penjualan), celah cakupan T2 (24 September 2026, writer Claude)

Label: T1_FAMILY, T2_REGRESSION, T3_PREP; bukan bukti rilis dan bukan penerimaan independen. CP6 tetap HOLD, 12 HOLD historis tetap HOLD, `production_go=false`. Tidak ada SQL ke hosted; cabang kompetisi tetap `ca7f095`.

### 23.1 Keputusan owner (dikutip)
- **8 kasus AS:** "Saya setujui penyesuaian oracle hanya untuk delapan kasus AS tersebut: event/jurnal HPP PO mengikuti 22 Sep pada fixture ini, karena barang jadi dan penjualan terjadi hari itu. Nominal, tanggal invoice, dan revaluasi bahan tetap sesuai oracle lama. ... Jangan sebut delapan kasus AS lulus sebelum oracle yang disetujui diuji ulang dan diperiksa independen." Juga: "Kalau kelak tanggal jual berbeda dari tanggal barang jadi, bagian HPP mengikuti tanggal jual."
- **WIP:** "setujui prinsip `max(tanggal ekonomi invoice, tanggal fisik potong)` saat tanggal ekonomi masih terbuka. WIP belum ada pada 1–2 Sep, jadi koreksi −Rp10 tidak boleh membuat saldo WIP negatif di dua hari itu. Claude perlu membuktikan dulu kasusnya di database uji, lalu menguji alokasi nilai bahan sebelum dipotong, beberapa tanggal potong, serta aturan jurnal bila periode sudah tertutup. Menggeser tanggal WIP saja belum cukup bila saldo bahan menjadi salah."
- **Konflik yang ditanyakan writer** (fixture AS memotong bahan 22 Sep, padahal persetujuan AS menyebut revaluasi tetap 21 Sep): owner memilih **"Ikut prinsip WIP"**. Revaluasi bahan→WIP 22 Sep, jurnal invoice tetap 21 Sep, dan oracle kebijakan 12 HOLD ikut bergeser dengan cara yang sama (tetap HOLD, dilaporkan).
- **Jawaban kedua owner (dikutip):** "Boleh untuk tiga kelompok; AS `ADJUSTMENT_DATE` jangan disahkan otomatis. ... lanjutkan pengecek otomatis dan perbarui tiga kelompok pertama sesuai aturan per kasus. Untuk `ADJUSTMENT_DATE`, telusuri pembaca `effective_date` dulu; bila aman, ubah oracle tanggalnya dengan bukti. Bila tidak, benahi model tanggalnya. Nominal dan ekspektasi lain tetap. Belum ada izin menyebut kasus yang masih `INCOMPLETE` sebagai PASS." Tiga kelompok itu: 12 kalender HOLD (perpindahan nilai ke WIP mengikuti hari potong; tetap HOLD), AO periode terbuka (koreksi WIP/FG mengikuti hari barang berpindah tahap; jurnal invoice tetap pada tanggal invoice), dan AO periode tertutup (posting pada hari pengakuan, tanggal ekonomi invoice tetap tersimpan; sudah ada sejak AS).
- **Arahan proses owner:** keputusan teknis diambil writer sendiri; pertanyaan dikirim sekaligus.
- **Kritik owner atas proses writer (dicatat):** begitu pola "koreksi nilai mendahului barang fisik" ketemu di FG, seharusnya seluruh alur bahan → WIP → FG → penjualan langsung diperiksa sebagai satu keluarga, bukan diajukan sebagai pertanyaan terpisah. Prosesnya juga terlalu panjang dan sering baru menemukan langkah berikutnya setelah satu putaran selesai.

### 23.2 AZ: koreksi recost bahan bertanggal dari pergerakan fisiknya
**Bukti dulu (fase sebelum AZ, T1 run 35964635432, `docs/evidence/cp6-az/native_t1_run35964635432_before.json`):**
- Fixture: bahan 10 unit Rp10 diterima 21 Sep. Invoice terlambat Rp8,25 (turun Rp1,75/unit) dengan tanggal ekonomi 21 Sep (terbuka).
- ONE_CUT_LOWER (10 unit dipotong 22 Sep): event revaluasi bahan→WIP 21 Sep. WIP PO **−Rp17,50 pada 21 Sep**, sebelum bahannya dipotong. Nilai bahan 21 Sep tidak turun ke harga invoice, padahal 10 unit masih di gudang.
- TWO_CUT_DAYS_LOWER (5 unit 22 Sep, 5 unit 23 Sep): WIP PO kedua **−Rp8,75 pada 21 dan 22 Sep**. Ini persis contoh "WIP belum ada pada 1–2 Sep" dari owner.
- Juga terbukti pada harga naik, dua zona waktu, penyesuaian bahan sehari sesudah hari terima, dan penjualan sehari sesudah hari barang jadi.
- 4 kasus yang memang tidak boleh berubah (invoice sesudah potong, hari terima tertutup, tertutup sampai hari potong, penyesuaian tertutup) PASS sebelum AZ.

**Isi AZ (satu file rilis ke-24, `supabase/release/cp6-t3/20260924010300_erp_v2_6_20az_cp6_material_recost_dated_from_movement.sql`; sumber T1 `supabase/dev/cp6_az_t1_family.sql`, dibangun oleh `scripts/cp6_az_build.py`):**
- Jurnal invoice pemasok tetap pada E: bahan dikoreksi penuh untuk seluruh unit yang diterima.
- `erp.sync_material_cost_revaluation` (potong, retur potong, issue kontraktor termasuk aksesori, retur pemasok): koreksi tiap pergerakan dipindah keluar dari bahan pada `greatest(E, tanggal fisik pergerakan)` bila E terbuka.
- `erp._cp6_sync_material_adjustment_revaluation`: pada `greatest(E, tanggal fisik dokumen penyesuaian)` bila E terbuka.
- Bila E tertutup, tidak ada yang berubah dibanding sebelumnya: tanggal ekonomi tetap E, diposting pada hari pengakuan.
- Nominal, akun, state, dan event tidak berubah; yang berubah hanya tanggal. Di luar invoice, E = hari ini, jadi tidak ada yang bergeser.
- Konsekuensi yang ditemukan writer sebelum T2: penutupan sisa WIP PO FINISHED di jalur invoice (`erp.sync_finished_po_wip_residual`) tadinya diposting pada E. Sekarang tidak didahulukan dari posting WIP terakhir PO itu bila E terbuka. Ini hanya diuji logika lokal; fixture native PO FINISHED dengan sisa WIP belum ada.
- Recost periode pocket memakai tanggal fakta revaluasi penyesuaian, jadi otomatis ikut hari penyesuaian (efek berantai AZ). Suite pocket di AR tetap PASS.

**Sesudah AZ (fase sesudah, `..._after.json`): 10/10 PASS.** Primary tidak berubah dan clone 0.
- Dua tanggal potong: bahan −17,50 (21 Sep, 10 unit di gudang), −8,75 (22 Sep, 5 unit), 0 (23 Sep). WIP tiap PO 0 sampai hari potongnya, lalu Rp41,25.
- Penjualan sehari sesudah barang jadi: 22 Sep FG −5,25 dan HPP −3,50; 23 Sep FG +1,75 dan HPP −1,75 (1 pcs dijual hari itu). Bagian HPP ikut tanggal jual.
- Periode tertutup: jurnal bertanggal ekonomi 21 Sep, diposting 24 Sep, dan laporan hari-hari sebelumnya tidak berubah.
- Penyesuaian: revaluasinya 22 Sep (hari penyesuaian), potong 8 unit 23 Sep.

Run T1 pertama AZ (35964210256) INCOMPLETE di fixture probe sendiri: RPC potong mensyaratkan keluar = terpakai + sisa, dan kontraktor seed belum dibersihkan sebelum tutup buku. Keduanya sudah diperbaiki; kasus dengan fixture yang benar sudah PASS di run itu.

### 23.3 8 kasus AS: oracle tanggal yang disetujui
- Pembungkus di runner T2 (`approved_oracle`, `scripts/cp6_t2_regression.py`) hanya menyala untuk 8 ID `DATE:False:<zona>:True:<biaya>`, dan dicek ada tepat 8.
- Oracle AS beku dijalankan apa adanya, dan statusnya tetap tercatat (COUNTEREXAMPLE pada tanggal).
- Di dalam savepoint kasus, pembungkus membaca dari database: tanggal potong, tanggal lot barang jadi, tanggal jual (tanpa retur), jurnal event HPP, dan jurnal revaluasi. Hasilnya `approved_oracle_20260924`.
- MATCH hanya bila semua benar:
  - fixture potong = barang jadi = jual pada satu hari L sesudah E;
  - event dan jurnal HPP PO pada L (ekonomi dan posting);
  - event dan jurnal revaluasi bahan pada L;
  - jurnal lain (invoice pemasok) pada E;
  - oracle lama hanya gagal pada kunci tanggal;
  - replay persis dan konteks bersih.
- Run 11 (tanpa AZ): 8/8 MISMATCH hanya pada tanggal revaluasi. Ini membuktikan pembungkusnya tidak asal lolos.
- Run 12 (dengan AZ): **8/8 MATCH**. T2 akhir (run 35972527139, AY rev5): **8/8 MATCH**.
- Sesuai arahan owner, kasus ini **belum disebut lulus** sebelum pemeriksaan independen: pemeriksaan independen read-only (agen terpisah) menemukan satu BLOCKER dan beberapa perbaikan kecil (§23.9). Setelah diperbaiki, oracle yang disetujui diuji ulang di T2 akhir (§23.5). Statusnya tetap **approved oracle MATCH**, bukan PASS kasus beku; kasus beku tetap COUNTEREXAMPLE.

### 23.4 Celah cakupan T2 yang ditemukan writer (dan ditutup)
- **Oracle kebijakan kalender 12 HOLD** (bagian dari putusan regresi sendiri) hanya tersimpan di file laporan, tidak di log. Hasilnya tidak saya periksa di run 6–10. Sekarang dicetak: 12/12 PASS pada AY rev3 (run 11).
- **Trial AO** (`cp6_initial_import_ao_trial.py`, 12 kasus, termasuk INVOICE yang mengunci tanggal jurnal recost) tidak termasuk set T2, padahal menjalankan jalur yang diubah AY/AZ. Filenya menjalankan seluruh trial saat di-import (ke database utama), jadi T2 hanya mengambil tiga fungsi kasusnya lewat `ast` tanpa mengubahnya, lalu menyiapkan fondasi seperti runner aslinya. Hasil: 8 PASS; 4 INVOICE berubah (lihat §23.6). Keputusan owner atas keempatnya ada di §23.6.

### 23.5 Hasil akhir (AY rev5 + AZ)
Head kode akhir `f8c9e96`. Commit sesudahnya hanya dokumen dan bukti. Semua uji di database uji sekali pakai atau CI; tidak ada SQL ke hosted.

**T1:**
- AZ run 35973285008: sesudah AZ **14/14 PASS**, termasuk `MULTI_CUT_*` dan `WRITE_OFF_AFTER_LOT_*`. Sebelum AZ: 10 COUNTEREXAMPLE, 4 PASS; 4 yang PASS itu kasus yang memang tidak boleh berubah.
- AY run 35972503616: sesudah AY **7/7 PASS**.
- Primary tidak berubah, clone 0.
- Contoh write-off (harga naik): FG +7,00 pada hari lot, lalu +4,20 sesudah write-off 4 dari 10 pcs pada hari berikutnya; WIP PO 0 setiap hari. Write-off itu sendiri, yang diposting sebelum invoice di luar jalur invoice, tetap bertanggal hari write-off.

**T2 run 35972527139 (`4be3f05`, AY rev5 + AZ; seed QUIETED, fixture PAYROLL_APPROVED):**
- Grup lama sama per kasus dengan AU: BUSINESS 230 (179 PASS, 39 CONTROL_PASS, 12 HOLD), IMPORTS 31, VALUES 65. 12 HOLD identik.
- AR 174 PASS (146 + 28). Temporal: AT 16 + AU 15 PASS, race 4 + 6 PASS.
- Hasil oracle beku tetap tercatat apa adanya: NEW_CASES 25 PASS, 8 COUNTEREXAMPLE (AS DATE), 1 INCOMPLETE (ADJUSTMENT_DATE); trial AO 8 PASS, 4 INCOMPLETE (INVOICE); oracle kalender 12 COUNTEREXAMPLE hanya pada `material_event_date`. Verdict `DISPOSITION_REQUIRED`.
- Oracle yang disetujui (kunci terpisah):
  - AS 8 kasus: **8/8 MATCH**, 10 cek per kasus semua benar.
  - Kalender: **12/12 MATCH**; kasusnya tetap HOLD.
  - AO INVOICE: **4/4 MATCH**. Seluruh teks kasus beku ikut dijalankan, termasuk bagian yang tak pernah tercapai karena assert tanggal pertama gagal.
  - AS `ADJUSTMENT_DATE:False`: **MATCH**. Syarat MATCH-nya juga mencakup jumlah temuan `V2620T_MATERIAL_ADJUSTMENT_*` dan cek kantong tidak naik sesudah invoice dan sesudah invoice dibatalkan. Angkanya ada di file laporan run, tidak dicetak di log.
- Bukti: `docs/evidence/cp6-t2/run35972527139_ay_rev5_final.json`. Run 17 (35969330544, AY rev4) juga disimpan.

**T3 run 35973311813 (`f8c9e96`): hijau.** Tiga job lulus:
- Capture: pin yang ditangkap ulang sama dengan paket (blob `fe78de75`, 65.237 byte; sha256 dan panjang dicek).
- Instal paket 24 file AC..AZ; AW/AX/AY/AZ terverifikasi; backup/restore RESTORED_SAME_MEANING.
- Browser.
- Advisor: 73 → 126. Satu tambahan dibanding paket AZ sebelumnya: INFO `rls_enabled_no_policy` untuk tabel internal baru `erp.po_hpp_gl_lot_state_v1`, pola yang sama dengan tabel internal lain.

**CodeQL** run 35973863330 pada `e4584a3` (kode sama dengan `f8c9e96`): sukses.

### 23.6 Pergeseran oracle beku (satu daftar, dengan alasan)
Semua kasus yang ekspektasi bekunya bergeser pada putaran ini. Oracle beku tidak diubah; hasil bekunya tetap tercatat. Oracle yang disetujui berjalan terpisah dengan kunci sendiri (`approved_oracle_20260924` / `approved_oracle_20260924b`): teks kasus beku yang sama, hanya dengan substitusi tanggal yang tercantum, dan tiap substitusi diperiksa terjadi tepat sekali.

| Kasus | Penyebab | Keputusan owner | Status |
|---|---|---|---|
| AS `DATE:False:<4 zona>:True:<20\|20.003>` (8) | AY (HPP dari hari barang/jual) + AZ (revaluasi dari hari potong); fixture memotong, menyelesaikan, dan menjual pada 22 Sep | Disetujui 24 Sep: HPP 22 Sep; nominal dan tanggal invoice tetap; revaluasi ikut prinsip WIP | Oracle disetujui MATCH; kasus beku tetap COUNTEREXAMPLE |
| Oracle kebijakan kalender 12 HOLD historis | AZ: revaluasi bahan→WIP Rp5,25 pada hari potong (hari beli +1) | Disetujui 24 Sep (jawaban kedua): tanggal perpindahan nilai ke WIP mengikuti hari potong; status tetap HOLD | Oracle disetujui: lihat §23.5; 12 kasus tetap HOLD |
| AO trial `INVOICE:<UTC\|Kiritimati>:False` (2) | AY + AZ: revaluasi dan PO_HPP_GL_SYNC pada hari potong/barang (invoice +1) | Disetujui 24 Sep: koreksi WIP/FG mengikuti hari barang berpindah tahap; jurnal invoice tetap pada tanggal invoice | Oracle disetujui: lihat §23.5; kasus beku tetap INCOMPLETE |
| AO trial `INVOICE:<UTC\|Kiritimati>:True` (2) | Sudah ada sejak AS, bukan AY/AZ: AS menetapkan tanggal event revaluasi = tanggal posting (hari pengakuan); trial AO ditulis sebelum AS dan tidak dijalankan ulang sesudah AS | Disetujui 24 Sep: posting pada hari pengakuan, tanggal ekonomi invoice tetap tersimpan | Oracle disetujui: lihat §23.5; kasus beku tetap INCOMPLETE |
| AS `ADJUSTMENT_DATE:False` (1) | AZ: revaluasi penyesuaian bahan pada hari penyesuaian (22 Sep), bukan tanggal invoice (21 Sep) | Owner: jangan disahkan otomatis. Telusuri pembaca `effective_date`; bila aman, ubah oracle tanggalnya dengan bukti | Penelusuran dan bukti: di bawah; kasus beku tetap INCOMPLETE |

**Penelusuran `effective_date` fakta penyesuaian (ADJUSTMENT_DATE).** Pembaca di definisi terakhir, di luar fungsi penulisnya sendiri:
1. `erp.run_v267_financial_truth_checks`, cek `V2620T_MATERIAL_ADJUSTMENT_FACT_LEDGER`. Syaratnya `j.economic_date = f.effective_date` antara fakta dan jurnalnya sendiri. Cek ini tidak membandingkan dengan tanggal invoice. AZ menulis keduanya dengan nilai yang sama (`v_date`), dan untuk tanggal tertutup tetap E.
2. Trigger `pocket_period_recost` (`erp.guard_pocket_period_v1`), yang memanggil `erp.sync_pocket_period_v1(pool, new.effective_date, 'RECOST', ...)`. Tanggal fakta menjadi tanggal jurnal recost periode kantong, sehingga jurnal itu ikut bergeser dari E ke hari pengeluaran kain kantong. Arahnya sesuai prinsip (tidak mendahului fakta fisik). Cek kantong (`pocket_period_checks_v1`, `pocket_fabric_checks_v1`) tidak memuat syarat tanggal. Pocket suite AR PASS dengan AZ.
3. Registry AW (`V2620T_MATERIAL_ADJUSTMENT_*` = DATABLE) tidak membaca tanggal fakta. `erp.reverse_journal` menolak jurnal ini tanpa melihat tanggal.

Kesimpulan penelusuran: tidak ada pembaca yang membutuhkan tanggal invoice. Buktinya ada di dalam kasus: oracle yang disetujui menjalankan teks kasus beku dengan tanggal hari penyesuaian, ditambah cek (1) dan kedua cek kantong sebelum invoice, sesudah invoice, dan sesudah invoice dibatalkan. Jumlah temuannya tidak boleh naik. Hasilnya di §23.5.

### 23.7 Anggota keluarga yang belum dikerjakan (jalur impor awal/cutover)
Dipetakan oleh agen read-only (daftar lengkap di catatan writer). Belum dikerjakan, dan tidak boleh diklaim tertutup:
- **Recost periode kantong vs tanggal alokasi**: jurnal recost periode kantong kini mengikuti hari pengeluaran kain (efek AZ lewat fakta penyesuaian), tetapi tujuan alokasinya (event jahit) bisa jatuh lebih lambat di periode itu.
- **Nilai BS impor awal** (`INITIAL_IMPORT_BS_VALUE`): resolusi BS sesudah E.
- **Lot pembuka non-PO** (`NON_PO_HPP_GL_SYNC_V2620F`): penjualan, retur, dan penyesuaian FG sesudah E, hanya di kaki COGS/lainnya.
- **Kaki "other" AY** (write-off/BS) masih diletakkan pada tanggal lot terakhir, bukan tanggal write-off.
- **Invoice bertanggal sebelum barang diterima**: tidak ada guard; belum diverifikasi.
- `INITIAL_IMPORT_ORIGIN_RECOST` dan `OPENING_HPP_SOURCE_V2620G` tidak bisa mendahului barangnya (guard cutover memaksa E ≥ tanggal cutover).

Batasan yang diketahui:
- Pergerakan yang dibalik (reversed) memakai tanggal pembalikan. Ini sudah ada sebelum putaran ini.
- Cabang AZ tanpa fixture native: retur pemasok, issue kontraktor/aksesori, retur potong, penyesuaian positif.
- Penutupan sisa WIP PO FINISHED di jalur invoice hanya diuji logika lokal.
- AY rev4: lot yang terakhir di-sync sebelum tabel `po_hpp_gl_lot_state_v1` ada memakai versi HPP yang berlaku saat sync terakhir (`calculated_at <= updated_at`). Cabang ini tidak punya fixture native (semua probe dan T2 membuat lot sesudah instalasi, kecuali data seed AU di T2).

### 23.8 Kesalahan metode writer di putaran ini
- **Keluarga masalah tidak dipetakan sejak awal.** Begitu FG terbukti dikoreksi sebelum barangnya ada (AY), bahan→WIP (AZ), penjualan, dan PO dengan beberapa tanggal potong seharusnya langsung diperiksa. Yang terjadi, masing-masing baru ditemukan satu per satu setelah satu putaran selesai (kritik owner, valid).
- **AY tiga revisi berturut-turut.** rev1 memberi tanggal koreksi mendahului invoice pada hari terima yang sudah tertutup; rev2 menghilangkan tanggal ekonomi E (AR gagal); rev3 benar untuk satu kali potong, tetapi membagi per pcs (temuan pemeriksa independen, terbukti native, lalu rev4). Semua terlihat di T2/T1, tetapi bisa dihindari dengan menurunkan aturan dari definisi `rebuild_po_hpp` sebelum menulis kode.
- **`package()` T3 tidak diuji lokal** sebelum push, sehingga satu putaran capture terbuang (AZ dicari di folder migrasi).
- **Fixture probe salah dua kali** (syarat RPC potong; kontraktor seed belum dibersihkan).
- **Oracle kebijakan kalender tidak dicetak di log pada run 6–10**, jadi hasilnya tidak saya periksa. Trial AO tidak termasuk set T2 walaupun menjalankan jalur yang diubah.
- **Kata-kata bukti terlalu kuat:** laporan menyebut pergeseran kalender "diterima owner", padahal owner hanya memilih opsi yang menyebut pergeseran itu akan terjadi dan dilaporkan. Sudah dikoreksi (catatan `review_20260924` di JSON bukti).
- **Terlalu banyak pertanyaan terpisah ke owner.** Mulai sekarang keputusan teknis dalam prinsip yang sudah disetujui diambil writer, dan pertanyaan kebijakan dikirim sekaligus dalam satu daftar.

### 23.9 Pemeriksaan independen dan tindak lanjutnya
Pemeriksaan independen read-only pertama (agen terpisah, terhadap oracle AS dan AZ):
- **BLOCKER:** bukti menyebut pergeseran kebijakan kalender "diterima owner". Dikoreksi: catatan `review_20260924` di dua JSON bukti T2. Sesudah itu owner memang menyetujuinya (jawaban kedua, §23.6).
- Pembungkus oracle AS dibuat lebih ketat:
  - jurnal lain harus berupa invoice pemasok pada E;
  - pembungkus berjalan dalam savepoint sendiri;
  - kedelapan kasus wajib dievaluasi;
  - hasil trial AO yang bukan 12 PASS memaksa disposisi.
- AY/AZ: tanggal fisik dibatasi hari ini saat E terbuka. Penutupan sisa WIP hanya diubah di jalur invoice.
- **Temuan #3 (satu PO, dua tanggal potong)** dibuktikan native, lalu diperbaiki (§23.10).

Pemeriksaan independen read-only kedua (agen terpisah, terhadap AY rev4) menghasilkan 1 BLOCKER, 2 MAJOR, dan 4 MINOR:
- **B1 BLOCKER** (terbukti dari kode, belum ada tes): rev4 hanya menghitung pcs yang masih dimiliki dan yang terjual. Pcs yang di-write-off atau dikonversi membuat WIP PO negatif antara tanggal lot dan tanggal write-off/konversi. Contoh reviewer: konversi 40 dari 100 pcs pada hari 5 membuat WIP −40 pada hari 2–4. Masalah ini sudah ada sejak AY rev1 dalam bentuk lain, karena bobot pcs awal. **Diperbaiki di rev5** dan diuji native (`AZ:WRITE_OFF_AFTER_LOT_*`). Konversi belum punya fixture native.
- **M1 MAJOR** (terbukti dari kode): pemanggil di luar invoice mengirim tanggal fisik (penyesuaian FG, QC, penerimaan laundry, rework, koreksi potong, invoice vendor). AY memindahkan posting mereka ke tanggal lot; contoh reviewer: write-off stock opname 10 Sep jatuh ke tanggal lot 12 Sep. Ini juga sudah ada sejak AY rev1. **Diperbaiki di rev5**: di luar invoice, blok posting AS dipakai tanpa diubah.
- **M2 MAJOR** (dugaan): bila grup potong digabung dalam satu cutting batch lintas hari, `rebuild_po_hpp` merata-ratakan bahan se-batch, sehingga lot awal bisa ikut menanggung koreksi potongan yang lebih lambat. **Terbuka**; belum dibuktikan native.
- **N1**: `refresh_po_hpp_gl_baseline` (posting jual/retur) menulis ulang state PO tanpa state per lot. **Diperbaiki**: state per lot hanya dipakai bila ditulis bersamaan dengan atau sesudah state PO.
- **N2**: baris untuk lot VOIDED tidak dibersihkan; capsule rollback tidak mencakup tabel baru (rollback memang belum diuji). Grant, RLS, dan guard "instalasi tidak mengubah data" dinyatakan aman.
- **N3**: tanggal fisik dibatasi hari ini. Menjelang tengah malam, koreksi COGS bisa bertanggal sehari sebelum penjualan.
- **N4**: retur di kaki B tidak diberi batas bawah per lot seperti target; selisihnya bergeser ke tanggal terakhir.
- Yang dinyatakan benar: total per akun sama dengan satu jurnal lama; kuantitas yang dipakai sama dengan `compute_po_hpp_gl_targets_v2620d`; E tertutup identik dengan AS.
- Yang belum diuji native: konversi, retur, penjualan dibatalkan, batch, beberapa lot dari satu grup pada hari berbeda, E tertutup dengan beberapa tanggal, jalur fallback state per lot, dan beberapa sync dalam satu statement.

### 23.10 AY rev4 → rev5: koreksi per lot, lalu per pcs
**Bukti dulu** (AZ T1 run 35968507694, AY rev3 + AZ). Satu PO dipotong dua kali:
- 22 Sep: 4 unit jadi 8 pcs, langsung menjadi lot FG 8 pcs.
- 23 Sep: 6 unit jadi 3 pcs, lot FG 3 pcs.

`erp.rebuild_po_hpp` membagi bahan ke lot menurut kelompok potongnya, sehingga lot 1 berubah 4x dan lot 2 berubah 6x. rev3 membagi perubahan PO per pcs (8/11 dan 3/11):
- Harga naik: FG 22 Sep **+5,09**, seharusnya +2,80; WIP PO **−2,29**.
- Harga turun: FG −12,73, seharusnya −7,00; WIP PO +5,73.

Bukti: `docs/evidence/cp6-az/native_t1_run35968507694_after_ay_rev3_multicut.json`.

**Isi rev4:**
- Kaki A: tiap lot mendapat perubahan HPP-nya sendiri sejak sync terakhir × (FG dimiliki + terjual bersih), pada tanggal lot.
- Kaki B: perubahan HPP lot × pcs terjual pada tanggal jual/retur.
- Sisa pembulatan ke tanggal terakhir.
- HPP sebelumnya diambil dari tabel baru `erp.po_hpp_gl_lot_state_v1` (kosong saat instalasi, tanpa FK). Untuk lot yang terakhir di-sync sebelum tabel itu ada, dipakai versi HPP yang berlaku saat sync terakhir.
- Total per akun, aturan tanggal tertutup, dan jalur di luar invoice (satu tanggal E) tidak berubah.

**Sesudah rev4:**
- Harga naik: FG +2,80 (22 Sep) dan +4,20 (23 Sep).
- Harga turun: FG −7,00 dan −10,50.
- WIP PO 0 setiap hari, dan bahan tetap bernilai harga invoice untuk stok yang tersisa.

**rev5** (sesudah pemeriksaan independen rev4):
- Di luar invoice: blok posting AS apa adanya, satu jurnal pada tanggal pemanggil (M1).
- Di jalur invoice, koreksi tiap pcs mengikuti pcs itu (B1), dengan perubahan HPP lotnya sendiri:
  - produksi masuk (QC_GOOD/REWORK_IN/OPENING): WIP→FG pada tanggal pergerakan;
  - ADJUSTMENT/BS_OUT/REBRAND_OUT/IN: FG↔lainnya pada tanggalnya;
  - penjualan: FG→HPP pada tanggal jual; retur sebaliknya;
  - sisa pembulatan ke tanggal paling akhir.
- Hasil uji: lihat §23.5. Rev4 sudah lolos T2 run 17 dan T3 run 35970077436 sebelum pemeriksaan independen; rev5 menggantikannya. Yang belum diuji native: konversi (REBRAND), BS_OUT, retur, penjualan dibatalkan, batch lintas hari (M2), jalur fallback state per lot, dan penutupan sisa WIP PO FINISHED.

### 23.11 Status dan yang masih terbuka
- **Belum ada yang disebut PASS dari kasus beku yang berubah.** MATCH adalah oracle yang disetujui owner. Keputusan apakah hasil ini diterima sebagai regresi yang lulus ada pada peninjau independen/owner.
- CP6 tetap HOLD, 12 HOLD historis tetap HOLD, `production_go=false`, cabang kompetisi tetap `ca7f095`.
- Temuan terbuka:
  - **M2**: batch potong lintas hari, masih dugaan.
  - Anggota keluarga di §23.7.
  - Cabang tanpa fixture native (§23.10).
  - N2–N4 dari pemeriksaan independen.
- AY rev5 **belum** diperiksa independen lagi sesudah perbaikannya.

## 24. Putaran kelima: AY rev6/rev6.1 (saldo harian per lot) sesudah pemeriksaan independen rev5 (24 September 2026, writer Claude)

Label: T1_FAMILY, T2_REGRESSION, T3_PREP; bukan bukti rilis dan bukan penerimaan independen. CP6 tetap HOLD, 12 HOLD historis tetap HOLD, `production_go=false`. Tidak ada SQL ke hosted; cabang kompetisi tetap `ca7f095`. §23 tetap berlaku untuk keputusan owner dan oracle yang disetujui; bagian ini menggantikan §23.10–§23.11 untuk AY.

### 24.1 Kenapa rev6
Pemeriksaan independen read-only terhadap rev5 menemukan:
- **F1 BLOCKER:** penjualan yang dibatalkan belakangan tidak dihitung. Contoh: 10 pcs terjual 23 Sep, dibatalkan 25 Sep, harga 8,25. FG PO −17,50 pada 23–24 Sep.
- **F2:** lot yang di-void (Final SKU dibatalkan) membuat WIP PO negatif sampai QC ulang.
- **F3/M2:** grup potong dalam satu cutting batch yang dipotong pada hari berbeda. `rebuild_po_hpp` merata-ratakan bahan se-batch.
  - Terbukti native di AZ T1 run 35977288454 (fixture `BATCH_ACROSS_DAYS_*`, harga 10,70): FG +5,09 pada 22 Sep padahal bahan yang sudah dipotong baru +2,80, sehingga WIP PO **−2,29**.
  - Batch dapat dibuat pengguna lewat `save_cutting_batch_v2` (grant `authenticated`).
- **F4:** lot hasil relabel tanpa sync sendiri dihitung dari nol, sehingga terjadi ayunan lewat akun lainnya.
- F5–F10 minor (lihat §24.4).

Akar masalahnya sama sejak rev3: koreksi dihitung dari posisi barang **sekarang**, bukan mengikuti pergerakan tiap pcs dari hari ke hari. Menambal per alur (rev3→rev4→rev5) selalu meninggalkan alur lain, jadi rev6 diganti modelnya.

### 24.2 Isi rev6
Hanya jalur invoice; di luar invoice tetap blok posting AS apa adanya (M1).
- Untuk tiap tanggal fakta fisik (pergerakan FG lot PO termasuk pembatalan dan lot VOIDED, serta hari potong grup dalam batch), saldo koreksi di FG, HPP, dan lainnya = koreksi per pcs lot per tanggal itu × pcs lot itu yang ada di FG / terjual / keluar lainnya pada tanggal itu.
  - Terjual: SALE, SALE_RETURN, dan pembatalannya.
  - Keluar lainnya: ADJUSTMENT, BS_OUT, REBRAND, dan pembatalannya.
- Tiap tanggal memposting perubahan saldonya (sen) dengan WIP sebagai penyeimbang; tanggal terakhir mengambil sisa persis ke target. Total per akun sama dengan satu jurnal lama.
- **Koreksi per pcs** = HPP lot sekarang − HPP yang terakhir diposting. Sumber HPP lama, berurutan:
  1. `po_hpp_gl_lot_state_v1` bila ditulis bersama atau sesudah state PO;
  2. versi HPP saat sync terakhir;
  3. versi pertama lot (untuk relabel);
  4. nol.
- Lot VOIDED memakai koreksi lot hidup dari grup potongnya.
- Lot dalam batch memakai rata-rata ulang per hari potong: koreksi bahan grup yang sudah dipotong dibagi pcs-nya, ditambah bagian non-bahan lot itu. Nilai bahan grup saat sync terakhir disimpan di tabel baru `erp.po_hpp_gl_group_state_v1` (kosong saat instalasi). Batch tanpa state segar memakai koreksi konstan lot.
- E tertutup tetap satu jurnal pada E (seperti AS).

### 24.2a rev6.1 (sesudah pemeriksaan independen rev6)
Pemeriksaan independen read-only terhadap rev6 memakai database sekali pakai sendiri, dengan harness stub dan fungsi target asli. Hasilnya: F1, F4, F7 terbukti beres; F2 dan F3 beres sebagian. Temuan yang diperbaiki di rev6.1:
- **B-1 BLOCKER** (terbukti): perbaikan batch mati sendiri sesudah penjualan/retur/void/relabel. Penyebabnya, `refresh_po_hpp_gl_baseline` menulis ulang state PO dengan `clock_timestamp()`, sehingga state grup dianggap basi dan WIP PO kembali −2,29. State grup sekarang dipakai seperti ditulis sync terakhir; refresh tidak pernah mengubah nilai bahan.
- **M-2** (terbukti): lot VOIDED tanpa lot hidup di grupnya mendapat nol. Sekarang ia memakai koreksi bahan per pcs grupnya dari state grup.
- **M-3/F5** (terbukti): akun lainnya terpecah menjadi OTHER_INCOME dan OTHER_EXPENSE antartanggal. Sekarang tetap di satu akun, yaitu akun yang dipakai jurnal AS untuk total "other" PO (debit atau kredit), sehingga total per akun sama dengan AS.
- **m-1** (terbukti): pembulatan terpisah menggerakkan 1 sen lewat WIP pada hari jual murni. Sekarang total per tanggal dibulatkan sekali dan FG mengambil sisanya.

Harness lokal sesudah perbaikan:
- f1 dan m2 tidak berubah.
- s5 (skenario pemeriksa): OTHER_INCOME Dr 1,75 / Cr 7,00, netto 5,25 seperti AS.
- s7b: WIP 0 pada hari jual.
- s4b dengan urutan waktu realistis (versi recost sesudah refresh): FG +2,80 / +4,20 pada hari potong, WIP 0.

### 24.3 Hasil
Head kode akhir `768196a` (rev6.1); commit sesudahnya hanya paket, bukti, dan dokumen. Semua di database uji sekali pakai, CI, atau PostgreSQL lokal sekali pakai; tidak ada SQL ke hosted.

**T1:**
- AZ run 35981539090: sesudah AZ **21/21 PASS**. Sebelum AZ: 17 COUNTEREXAMPLE dan 4 PASS; 4 yang PASS itu kasus yang memang tidak boleh berubah.
- Kasus baru putaran ini:
  - `SALE_REVERSED_BEFORE_INVOICE`: 10 pcs terjual 23 Sep, kembali 24 Sep.
  - `QC_REVERSED_AND_REDONE`, `CONVERSION_THEN_SALE`, `BATCH_ACROSS_DAYS_HIGHER/LOWER`.
  - `SALE_THEN_RETURN`, `CONVERSION_AFTER_LOT`, `WRITE_OFF_AFTER_LOT_*`.
- Contoh angka:
  - Penjualan dibatalkan (harga 8,25): FG −17,50 / 0,00 / −17,50 dan HPP 0 / −17,50 / 0 pada 22/23/24 Sep.
  - Batch (harga 10,70): FG +2,80 lalu +7,00; WIP PO 0 setiap hari.
- AY run 35981539187: sesudah AY **7/7 PASS**.
- Primary tidak berubah, clone 0.
- Bukti: `docs/evidence/cp6-az/native_t1_run35981539090_*_rev6_1.json`, `docs/evidence/cp6-ay/native_t1_run35981539187_*_rev6_1.json`, serta run rev6 (35979149009/35979148978) dan run rev3 yang membuktikan M2.

**T2 run 35981556942 (`768196a`; seed QUIETED, fixture PAYROLL_APPROVED):**
- Grup lama sama per kasus dengan AU (230/31/65); 12 HOLD identik. AR 174 PASS. Temporal 31 PASS, race 4 + 6 PASS.
- Hasil oracle beku tetap tercatat apa adanya: NEW_CASES 8 COUNTEREXAMPLE + 1 INCOMPLETE, trial AO 4 INCOMPLETE, oracle kalender 12 COUNTEREXAMPLE.
- Oracle yang disetujui: AS 8/8, kalender 12/12, AO INVOICE 4/4, dan `ADJUSTMENT_DATE`, semuanya MATCH.
- Bukti: `docs/evidence/cp6-t2/run35981556942_ay_rev6_1_final.json` (run rev6: `run35979546348_ay_rev6.json`).

**T3 run 35982196363 (`ed6c4e7`): hijau.**
- Capture: pin sama dengan paket (blob `f7e68a49`, 65.237 byte; sha256 dan panjang dicek).
- Instal paket 24 file; AW/AX/AY/AZ terverifikasi; backup/restore RESTORED_SAME_MEANING; browser lulus.
- Advisor 73 → 127. Tambahannya hanya INFO `rls_enabled_no_policy` untuk tabel internal, termasuk dua tabel baru AY (`po_hpp_gl_lot_state_v1`, `po_hpp_gl_group_state_v1`).

**CodeQL:** run 35982826747 pada `ed6c4e7` (kode sama dengan `768196a`): sukses.

### 24.4 Temuan yang masih terbuka
Dicatat, **belum** diperbaiki di putaran ini:
- **M-1 MAJOR** (terbukti di harness untuk retur potong; sisanya dari kode): fakta bahan sesudah tanggal lot. Koreksi lot yang bukan batch, dan bagian non-bahan lot batch, konstan sejak tanggal lot. AZ memberi tanggal tiap pergerakan bahan pada harinya sendiri.
  - Contoh: potong 10 unit 20 Sep, lot 21 Sep, retur 2 unit 23 Sep, harga 8,25. AY: FG −14,00 pada 21 Sep; AZ: WIP −17,50 pada 20 Sep dan +3,50 pada 23 Sep. **WIP PO −3,50 pada 21–22 Sep.**
  - Kelas yang sama (dari kode, belum dijalankan): grup yang dipotong beberapa hari, bahan kontraktor non-aksesori yang dikeluarkan sesudah lot awal, dan lot tanpa grup potong (kolam bahan per PO).
  - Rancangan perbaikan: semua kolam bahan (grup, batch, kolam kontraktor dan kolam PO) diperlakukan seperti batch, dengan koreksi per pergerakan bahan pada tanggalnya sendiri. State disimpan per pergerakan, bukan per grup.
- **F6 MINOR**: relabel yang dibatalkan. Lot anak dari konversi REVERSED tidak di-recost, sehingga terjadi ayunan lewat akun lainnya di antara tanggal konversi dan pembatalannya (contoh pemeriksa: 7,00).
- **M-4 MAJOR (kinerja)**: CTE `cum` menggabungkan tanggal × pergerakan di bawah lock global `FG_HPP_SALES_V2620C`. Waktu yang diukur di stub: 1,4 s untuk 5 ribu pergerakan / 251 tanggal; 12,5 s untuk 50 ribu / 731. PO normal jauh lebih kecil. Rancangan perbaikan: running sum per lot dan tanggal (window function).
- **F9/F10 MINOR**: jam campuran (`now()`, `statement_timestamp()`, `clock_timestamp()`) pada fallback state, dan batas "hari ini" menjelang tengah malam.
- **Tanpa uji native**: skenario B-1 (batch lalu penjualan) hanya diuji di harness lokal. Jalur fallback state untuk data sebelum instalasi, E tertutup dengan banyak tanggal, dan beberapa sync dalam satu statement juga belum diuji native.
- Dari §23: anggota keluarga lain (§23.7) tetap terbuka.

### 24.5 Pelajaran
- Error pertama rev6 di CI (alias `t` bentrok dengan record `t` plpgsql) lolos dari cek sintaks lokal. Sejak itu fungsi diuji di **harness stub lokal** (PostgreSQL sekali pakai, skema minimal) dengan skenario angka sebelum push. Putaran uji turun dari ±30 menit ke hitungan detik.
- Ekspektasi fixture `SALE_REVERSED` yang pertama salah: penjualan yang dibatalkan dianggap tidak pernah terjual. Karena itu rev5 lolos padahal F1 ada. Sekarang ekspektasinya mengikuti tanggal fisik: pcs keluar pada hari jual dan kembali pada hari pembatalan.

## 25. Putaran keenam: AY rev7 (fakta bahan per tanggal fisik, relabel, kinerja) (24 September 2026, writer Claude)

Label: T1_FAMILY, T2_REGRESSION, T3_PREP; bukan bukti rilis dan bukan penerimaan independen. CP6 tetap HOLD, 12 HOLD historis tetap HOLD, `production_go=false`. Tidak ada SQL ke hosted; cabang kompetisi tetap `ca7f095`. Bagian ini menggantikan §24.4 untuk M-1, F6, dan M-4. Keputusan owner dan oracle yang disetujui tetap di §23.

### 25.1 Yang diperbaiki
- **M-1 (fakta bahan sesudah tanggal lot).** Setiap fakta bahan di balik HPP PO kini punya tanggal sendiri, sama dengan tanggal AZ untuk revaluasi WIP-nya:
  - pengeluaran dan retur bahan potong (per pergerakan);
  - bahan kontraktor non-aksesori (per item, tanggal gerakan stoknya).
  Kolamnya mengikuti `rebuild_po_hpp`: cutting batch (dibagi `effective_pcs`, termasuk grup PO lain dalam batch yang sama), grup lineage, atau kolam PO; bahan kontraktor dibagi `cp6_po_source_qty_v2620c`.
  Koreksi per pcs lot pada tanggal D = koreksi lot sekarang, dikurangi bagian koreksi bahan yang faktanya baru ada sesudah D.
- **State per fakta.** Tabel baru `erp.po_hpp_gl_material_state_v1 (po_id, source_key)` menggantikan `po_hpp_gl_group_state_v1`. Isinya nilai tiap fakta di dalam HPP yang terakhir diposting (`M:<gerakan>`, `C:<item>`), ditambah penanda `SYNC`.
  - State hanya ditulis bila HPP di-rebuild pada statement yang sama. Semua pemanggil `rebuild_po_hpp` langsung memanggil sync; lima pemanggil sync tidak me-rebuild (penyesuaian FG, pembatalan penjualan/retur/konversi), dan pada mereka state lama tetap berlaku karena HPP yang diposting juga masih HPP rebuild terakhir.
  - Fakta yang dibuat sesudah penanda `SYNC` belum ada di HPP mana pun, jadi nilai lamanya nol. Contoh: bahan ke mandor sesudah lot, yang tidak me-rebuild HPP.
  - rev7: fakta tanpa state dari sebelum AY dipasang tetap memakai koreksi konstan. rev7.1 menggantinya (F1 di §25.1a): nilai lamanya diturunkan dari HPP yang terakhir di-rebuild.
- **F6 (relabel dibatalkan).** Lot hasil relabel mengikuti koreksi lot sumbernya: relabel yang dibatalkan saling meniadakan, relabel yang diposting menambah selisih koreksinya sendiri. rev7.1 memperluasnya ke rantai relabel (F3 di §25.1a).
- **M-4 (kinerja).** Saldo per lot per tanggal dan saldo bahan per kolam dihitung dengan running sum (window), tanpa join tanggal × pergerakan.

### 25.1a Pemeriksaan independen rev7 dan rev7.1
Pemeriksa sub-agent read-only memakai database stub sekali pakai sendiri: rev7, rev6.1 untuk pembanding waktu, dan salinan fungsi AS sebagai acuan; ditambah fuzz 400 seed × 3 mode. Tidak ada BLOCKER.

**Terbukti beres:**
- M-1 untuk PO yang punya state (retur, kontraktor, kolam PO, harga naik).
- Relabel tunggal, dibatalkan atau diposting.
- Batch lintas dua PO.
- Dua bahan dalam satu statement.
- Data pinggir tanpa error.
- Jalur non-invoice dan E tertutup identik dengan AS.
- Total per akun = AS pada semua seed yang diterima AS sendiri.
- Model kolam sama dengan `rebuild_po_hpp`; aturan state segar dan penanda SYNC; keamanan tabel baru.

**Temuan:**
- **F1 MAJOR** (terbukti): PO yang diproduksi sebelum AY dipasang belum punya state bahan, jadi M-1 tetap terjadi pada invoice terlambat pertamanya (repro x2: WIP PO −3,50). Justru PO seperti ini yang paling sering menunggu invoice.
  - Usul pemeriksa, yaitu mengisi state saat instalasi, **tidak dipakai**: guard rilis mewajibkan tabel baru kosong saat instalasi, dan guard lama tidak dilonggarkan.
  - **rev7.1:** untuk PO tanpa state, nilai lama tiap fakta diambil dari HPP yang terakhir di-rebuild (tp = versi terbaru lot PO sebelum statement ini). Fakta yang dibuat sesudah tp bernilai lama nol. Fakta yang ada pada tp bernilai lama = nilainya sekarang dikurangi revaluasi gerakannya sejak tp (`material_cost_revaluation_events`; delta persediaan bergerak berlawanan dengan nilai di HPP).
  - Harness r13: −17,50 pada hari lot dan +3,50 pada hari retur, sama dengan PO yang punya state; state ikut tertulis.
- **F2 MAJOR bila JIT aktif di hosted** (terbukti di stub): perencana salah menaksir query saldo harian lalu mengompilasi JIT ±4 s di bawah lock global `FG_HPP_SALES_V2620C`.
  - **rev7.1:** fungsi berjalan dengan `SET jit TO 'off'`, dan probe AY memeriksanya.
  - Stub pemeriksa: 300 lot 5,3 s → 1,09 s (rev6.1: 1,8 s); 1000 lot 10,6 s → 6,27 s.
- **F3 MINOR** (terbukti): rantai relabel (b1→c1→c2) masih berayun ±0,70 lewat akun lainnya.
  - **rev7.1:** lot relabel mengikuti lot akarnya lewat seluruh rantai (CTE rekursif), ditambah selisih sendiri dari relabel yang diposting.
  - Harness r14 (= repro x1): tidak ada baris akun lainnya.
- **F4 MINOR** (terbukti, **tidak diubah**): pengenceran kolam batch oleh grup yang dipotong sesudah penanda state tercatat pada hari lot.
  - Contoh: FG −17,91 pada 21 Sep dan +48,60 pada 23 Sep, padahal seharusnya −7,00 dan +37,69.
  - Tidak membuat saldo negatif: FG terlalu rendah di awal dan WIP terlalu tinggi.
  - Perbaikannya perlu menyimpan pcs kolam di state (dicatat di §25.4).

Fuzz yang sama pada rev7.1: 0 error AY, 0 selisih total; 111 penolakan, semuanya dari cek konsistensi AS pada data acak. Repro dan fuzz: `docs/evidence/cp6-ay/rev7-review/`.

### 25.2 Bukti harness lokal (sebelum CI)
Harness stub ada di `docs/evidence/cp6-ay/rev7-harness/`. Isinya skema minimal, fungsi target asli, 18 skenario (14 skenario r1–r14 ditambah f1, m2, f1_noninv, f1_closed), `perf.sql`, `run.sh`, dan output. Semua skenario keluar sesuai harapan tanpa error:
- **Retur potong sesudah lot** (contoh pemeriksa rev6): FG −17,50 pada hari lot, lalu +3,50 pada hari retur. WIP PO ditambah AZ = 0 setiap hari (rev6.1: −3,50 pada 21–22 Sep).
- **Bahan kontraktor sesudah lot:** koreksi jatuh pada hari gerakan stoknya (23), bukan hari header (22) atau hari lot.
- **Lot tanpa grup (kolam PO):** sama dengan retur potong.
- **Relabel dibatalkan:** tidak ada baris akun lainnya. Relabel diposting dengan anak ikut di-recost: hanya FG pada hari lot.
- **Batch berisi grup dua PO:** +2,80 lalu +2,29, bahan PO lain masuk kolam pada harinya.
- **Fakta sesudah penanda SYNC:** bahan kontraktor 8,00 masuk pada harinya. Tanpa penanda (r10 `marker=no`), versi HPP stub tidak dibuat pada statement yang sama, jadi hasilnya koreksi konstan. Jalur rev7.1 untuk PO tanpa state diuji di r13.
- **rev7.1:**
  - r13, PO tanpa state (F1): −17,50 / +3,50, sama dengan r1.
  - r14, rantai relabel (F3): tidak ada baris akun lainnya.
  - r1–r12 tidak berubah (`output_rev7_1.txt`).
- **Skenario lama tetap sama:** f1, m2, E tertutup, jalur non-invoice, write-off (OTHER_INCOME netto −5,25 = AS), pembulatan hari jual (WIP 0), dan batch lalu jual.
- **Kinerja** (`perf.txt`, stub):

  | Pergerakan FG | Hari | rev7 | rev6.1 |
  | --- | --- | --- | --- |
  | 40 ribu | 400 | 1,28 s | 4,50 s |
  | 100 ribu | 700 | 1,72 s | 23,32 s |

### 25.3 Hasil CI (database uji sekali pakai; tidak ada SQL ke hosted)
Head kode akhir **AY rev7.1 `e51614a`**, SQL sha256 `8b23a824…`. Commit sesudahnya:
- `017001f`: paket T3;
- `adc8d67`: guard alias di builder, SQL identik;
- sisanya bukti dan dokumen.

**Akhir (rev7.1):**
- **AY T1 run 35988403292** (`e51614a`):
  - sebelum AY: 3 COUNTEREXAMPLE + 4 PASS; 4 yang PASS memang tidak boleh berubah;
  - sesudah AY: **7/7 PASS**;
  - primary tidak berubah, clone 0.
- **AZ T1 run 35988403143** (`e51614a`):
  - sesudah AZ: **23/23 PASS**; sebelum AZ: 19 COUNTEREXAMPLE + 4 PASS;
  - kasus baru `CONTRACTOR_AFTER_LOT_{HIGHER,LOWER}`: 6 unit dipotong menjadi lot 10 pcs pada 22 Sep, lalu 4 unit kain yang sama diserahkan ke mandor PO pada 23 Sep, lalu invoice terlambat. Penyerahan ke mandor tidak me-rebuild HPP, jadi invoice membawa bahan mandor ke HPP untuk pertama kali.
    - Harga 10,70: FG +4,20 pada 22 Sep (hanya bahan potong). Saldo FG 47,00 pada 23 Sep (40 bahan mandor + 7,00 koreksi). WIP PO 0 setiap hari.
    - Harga 8,25: FG −10,50 pada 22 Sep, lalu saldo 22,50 pada 23 Sep. WIP PO 0 setiap hari.
    - Komponen MATERIAL HPP 60 → 107 / 82,5. State tertulis: `C:` 42,80 / 33,00, `M:` 64,20 / 49,50, dan `SYNC`.
  - Pada fase sebelum AZ (angka dari run rev7 35986418146), pencatatan FG oleh AY sudah benar. COUNTEREXAMPLE-nya datang dari revaluasi bahan tanpa AZ: WIP PO −17,50 pada 21 Sep untuk harga 8,25.
- **T2 run 35988415205** (`e51614a`; seed QUIETED, fixture PAYROLL_APPROVED): semua nilai ringkasan sama dengan rev7 (35985750159) dan rev6.1 (35981556942).
  - Grup lama 230/31/65: tidak ada yang bertambah, hilang, atau pindah. 12 HOLD identik.
  - AR 146 + 28 PASS; temporal 16 + 15 dan race 4 + 6 PASS.
  - Oracle beku tercatat apa adanya: NEW_CASES 8 COUNTEREXAMPLE + 1 INCOMPLETE, trial AO 4 INCOMPLETE, kalender 12 COUNTEREXAMPLE.
  - Oracle yang disetujui: AS 8/8, kalender 12/12, AO INVOICE 4/4, dan `ADJUSTMENT_DATE`, semuanya MATCH.
  - Bukti: `docs/evidence/cp6-t2/run35988415205_ay_rev7_1_final.json`.
- **T3 run 35988838581** (`017001f`): hijau.
  - Pin sama: blob `5647147f…`, 65.237 byte, ditangkap run 35988403137 yang gagal karena paket basi, seperti biasa.
  - Instalasi 24 file AC..AZ; AW/AX/AY/AZ terverifikasi (`ay_sql_sha256` `8b23a824…`).
  - Backup/restore RESTORED_SAME_MEANING (318 tabel sama). Browser 10/10 PASS, 0 error konsol.
  - Advisor 73 → 127: tambahannya hanya INFO `rls_enabled_no_policy` untuk tabel internal, termasuk `po_hpp_gl_lot_state_v1` dan `po_hpp_gl_material_state_v1`.
- **CodeQL run 35988417934** (`e51614a`): sukses.
- **AY T1 run 35989442151 dan AZ T1 run 35989442123** (`adc8d67`, guard alias di builder, SQL identik): keduanya sukses.
- Bukti: `docs/evidence/cp6-ay/native_t1_run35988403292_*_rev7_1.json`, `docs/evidence/cp6-az/native_t1_run35988403143_*_rev7_1.json`.

**Riwayat rev7 (`0bbfd55`, sebelum pemeriksaan independen):**
- AY T1 35985019228: 7/7 PASS.
- AZ T1 35986418146 (`99e1175`): 23/23 PASS.
- T2 35985750159: nilai ringkasan sama dengan rev6.1.
- T3 35986418270: hijau.
- CodeQL 35985752683: sukses.
- Dua putaran AZ T1 sebelumnya (35985019097, 35985740578) berhenti di penyiapan fixture: harga jual bahan ke mandor belum diisi, lalu satuan lama `yd` pada bahan tiruan belum terdaftar di `uom_definitions`. Keduanya kesalahan fixture writer. Pada kedua run itu 21 kasus lainnya PASS.

### 25.4 Yang masih terbuka (jujur)
Dicatat, **tidak** diperbaiki di putaran ini:
- **F4 MINOR (pemeriksaan rev7): pengenceran kolam batch.**
  - Bila grup baru dalam batch dipotong sesudah penanda state tanpa rebuild PO ini, perubahan pembagi kolam dicatat sejak hari lot, bukan hari potong grup baru.
  - Tidak membuat saldo negatif (FG terlalu rendah di awal, WIP terlalu tinggi), dan total per akun tetap sama.
  - Perbaikan: simpan pcs kolam di state (mis. kunci `Q:<kolam>`) dan beri tanggal pengencerannya pada hari potong.
- **PO tanpa state sama sekali (jalur F1):**
  - Bila tidak ada versi HPP sebelum statement ini (tp kosong), koreksi tetap konstan sejak hari lot (perilaku rev6).
  - Bila gerakan bahan dibatalkan dengan gerakan REVERSAL sesudah tp, revaluasinya ditargetkan nol dan gerakan REVERSAL tidak direvaluasi. Tanggal koreksinya bisa salah (tidak diuji; jarang, karena pembatalan potong dikunci sesudah dipakai fisik).
- **Antrean recost non-invoice.** Pemeriksa (tidak diuji): bila antrean `cost_recalc_queue` masih berisi recost non-invoice saat invoice tiba, AZ memberi tanggal hari ini untuk perubahan itu, sedangkan AY memberi tanggal hari faktanya, yang bisa lebih awal.
- **Ditemukan pemeriksa, sudah ada sebelum rev7 (tidak diuji native):**
  - Recost aksesori mengkredit WIP tanpa pasangan debit WIP dari AZ (AZ memposting ke ACCESSORY_RECOVERY_COGS).
  - PO pasangan batch yang tidak memakai bahan yang di-invoice tidak masuk antrean, sehingga HPP-nya basi.
- **Dari writer (harness r9):** batch lintas PO membuat WIP per PO saling berlawanan (contoh: −2,29 / +2,29), sedangkan WIP per akun tetap benar. Ini akibat pengumpulan bahan lintas PO di `rebuild_po_hpp`, bukan akibat penanggalan. Pemeriksaan saldo negatif AW berjalan per akun.
- **Beban tulis state:** tiap rebuild menulis ulang semua kunci `M:` PO dan pasangan batch-nya. Belum diukur di data besar.
- **F9/F10 dari §24.4** (jam campuran pada fallback, batas "hari ini" menjelang tengah malam): tetap terbuka. Tanggal jurnal tidak boleh di masa depan.
- **Dari §23.7:** anggota keluarga lain (impor awal/cutover) tetap terbuka.
- **Fixture native kontraktor** memakai bahan tiruan dengan satuan lama `yd` yang didaftarkan fixture ke `uom_definitions`. Satuan bahan produksi sungguhan tidak diperiksa di sini.

### 25.5 Pelajaran
- Alias SQL yang sama dengan variabel plpgsql (`s`, sebelumnya `t`) baru ketahuan saat fungsi dijalankan. Harness lokal menangkapnya sebelum CI. Sekarang builder dicek juga dengan pemindai alias.
- Dua putaran AZ T1 terbuang karena fixture baru (bahan ke mandor) belum lengkap: harga jual mandor, lalu satuan bahan. Fixture baru yang memakai alur produk yang belum pernah dipakai probe perlu dicoba dulu di database disposable lokal, bukan langsung di CI.
- Usul perbaikan pemeriksa (mengisi state saat instalasi) berbenturan dengan guard rilis yang mewajibkan tabel baru kosong. Guard tidak dilonggarkan; nilai lama diturunkan dari data revaluasi yang sudah ada.

## 26. Putaran ketujuh: sisa keluarga "koreksi nilai tidak boleh mendahului fakta fisiknya" (24 September 2026, writer Claude)

Label: T1_FAMILY, T2_REGRESSION, T3_PREP; bukan bukti rilis dan bukan penerimaan independen. CP6 tetap HOLD, 12 HOLD historis tetap HOLD, `production_go=false`. Tidak ada SQL ke hosted; cabang kompetisi tetap `ca7f095`.

Bagian ini menutup §25.4 dan §23.7. Semua item di sini adalah pekerjaan CP6, bukan CP7. Master pulih L1400 melarang memindahkan blocker CP6 ke CP7, dan L2745 menetapkan bahwa CP7 baru mulai sesudah semua gate CP6 selesai. Tidak ada keputusan owner yang tertunda.

### 26.1 Yang diubah
**AY rev7.2 → rev7.3 → rev7.4** (`erp.sync_po_hpp_to_gl` jalur invoice; di luar invoice dan E tertutup tetap satu jurnal seperti AS; plus `erp.rebuild_po_hpp` di rev7.4):
- **Revaluasi pada harinya sendiri (rev7.2).** Bagian perubahan fakta bahan yang dijelaskan oleh revaluasinya (`material_cost_revaluation_events` sesudah jangkar fakta) diberi tanggal pada tanggal efektif revaluasi itu. Recost non-invoice yang masih mengantre saat invoice diproses masuk WIP pada harinya sendiri, dan AY memindahkannya pada hari yang sama. Sisa yang tidak dijelaskan revaluasi (misalnya nilai fakta baru) tetap pada hari fisik fakta. Harness r16: −7,50 / −10,00.
- **F4, pengenceran batch (rev7.2).** Grup baru dalam cutting batch sejak sync terakhir mengencerkan bahan lama. Pengenceran itu kini diberi tanggal pada hari potong grup baru. Harness r15 = repro x6 pemeriksa: −7,00 / +37,69.
- **F9 (rev7.2).** State lot dipakai sebagaimana ditulis sync terakhir. `refresh_po_hpp_gl_baseline` hanya menggeser jam state PO tanpa mengubah HPP.
- **Kain kantong (rev7.3).** Bagian kain kantong di HPP lot dipecah per pool kantong lewat helper baru `erp.po_hpp_gl_pocket_by_pool_v1`, yaitu pemecahan per pool dari `erp.pocket_lot_cost_v1` yang dipakai `rebuild_po_hpp`. Nilainya dibandingkan dengan nilai per pool yang diposting sync terakhir (kolom state lot `pocket_by_pool`). Tiap bagian diberi tanggal seperti recost pool-nya: tidak sebelum akhir periodenya selama terbuka, dan E bila tertutup.
  - Satu invoice yang mengenai beberapa periode mencatat tiap bagian pada harinya sendiri, dan sync kedua dalam statement yang sama tidak menghitungnya lagi (harness r18).
  - Lot VOIDED mengikuti perubahan per pool dari lot hidup di grupnya (r19).
- **Kinerja.** Fungsi berjalan dengan `SET jit TO 'off'` (dari rev7.1). Join revaluasi lewat `unnest` (rev7.3).
- **Bahan potong yang dibatalkan sebelum jahit (rev7.4, temuan writer saat menutup daftar risiko sisa pemeriksa).**
  - `erp.rebuild_po_hpp` (AP) menjumlahkan semua gerakan `CUTTING_GROUP`/`CUTTING_GROUP_RETURN`, termasuk yang sudah dibalik oleh `erp.reverse_cutting_material_flow_before_sewing_v2`.
  - Pembalikan itu mengembalikan bahan ke gudang, membalik jurnal pengeluaran dari WIP, dan revaluasinya ditargetkan nol (AS/AZ). Akibatnya HPP membawa bahan yang tidak lagi ada di WIP.
  - Dampaknya dua: sync berikutnya membuat WIP PO negatif, dan bila potongan diterbitkan ulang, bahannya terhitung dua kali.
  - Perbaikan: gerakan yang dibalik dikeluarkan dari semua kolam bahan di `rebuild_po_hpp` (kolam PO, batch, dan grup). Sync memberi fakta itu nilai nol sejak hari fisik pembalikannya, termasuk di state bahan.
  - Harness r20: FG −17,50 pada hari lot dan −40,00 pada hari pembatalan; WIP PO ditambah AZ dan jurnal pembatalan = 0 setiap hari.
  - Fixture native: `AY:PRESEWING_REVERSAL_QUEUE`. Varian dengan invoice terlambat ada di probe AZ (`AZ:PRESEWING_REVERSAL_THEN_LATE_INVOICE_LOWER`), karena pemeriksaan WIP dan persediaannya butuh AZ terpasang (§26.6).

**AZ rev2** (builder AZ yang sama):
- **Recost kain kantong** (`guard_pocket_period_v1`): tidak sebelum akhir periode alokasinya selama terbuka; E bila tertutup; hari ini bila non-invoice.
- **Nilai BS impor awal** (`sync_initial_import_bs_value_v1`): pada invoice terlambat dengan E terbuka, perubahan dibagi per hari pengeluaran BS secara pro rata pcs.
- **Lot pembuka non-PO** (`sync_non_po_product_hpp_to_gl_v2620f`): pada invoice terlambat dengan E terbuka, kaki HPP dan kaki lainnya mengikuti hari jual, retur, dan penyesuaian. Bobotnya perubahan HPP per pcs tiap lot terhadap HPP yang terakhir diposting sync lot pembuka (`opening_lot_hpp_gl_state.current_hpp`). FG menjadi penyeimbang; kaki lainnya tetap di satu akun.
- **Recost aksesori** (`refresh_accessory_hpp_after_material_recost`): lot yang akrualnya sudah diposting kini mendapat jurnal `ACCESSORY_HPP_RECOST`, yaitu WIP melawan `ACCESSORY_REIMBURSE_VARIANCE`, dengan tanggal yang sama dengan pemindahan oleh sinkronisasi HPP PO. Tanpa jurnal ini, sinkronisasi mengkredit WIP tanpa debit, dan WIP PO bergeser di semua jalur.
  - **Perubahan perilaku:** jurnal ini juga muncul di jalur non-invoice dan E tertutup, karena bug WIP-nya ada di semua jalur.
  - Jurnal ini ikut dibatalkan bersama akrual di `reverse_qc`, `reverse_rework_completion`, dan `complete_initial_import_wip_v1`.
- **Invoice bertanggal sebelum barangnya diterima** (`post_material_supplier_invoice`; keputusan owner §26.2): dibukukan pada hari terima, yaitu hari terima terakhir dari baris-barisnya. Tanggal invoice tetap menjadi tanggal dokumen. Konteks recost (E) memakai hari buku yang sama. Invoice bertanggal pada atau sesudah hari terima tidak berubah.
- **Gerakan yang dibalik (AZ rev2.1, temuan native).**
  - Kasus: invoice terlambat dengan harga lebih rendah untuk bahan yang pengeluaran potongnya sebagian dibatalkan sebelum jahit.
  - Akibatnya MATERIAL_INVENTORY −10,50 antara hari potong dan hari pembatalan, dan engine tutup buku menandainya `GL_INVENTORY_NEGATIVE_ASOF` CRITICAL (run AY T1 35998326956, `769abfe`).
  - Penyebab: mesin biaya memutar ulang riwayat tanpa gerakan yang dibalik dan pembaliknya, dan revaluasinya ditargetkan nol. Unit yang secara fisik ada di WIP tetap tercatat keluar pada harga lama, sementara stok asalnya sudah dinilai ulang.
  - Perbaikan (`sync_material_cost_revaluation`): gerakan yang dibalik dinilai ulang dengan biaya yang akan diberikan pemutaran ulang (rata-rata sebelum gerakan itu; untuk retur potong, biaya pengeluarannya) pada hari gerakan itu. Pembaliknya mengambil nilai itu kembali pada hari pembalik. Bila kedua kaki jatuh pada hari yang sama (E tertutup, recost tanpa invoice terlambat), nilai interim gerakan asal dipertahankan dan pembaliknya menetralkan pasangan pada hari itu. Buku per hari sama dengan posting tunggal sebelumnya.
  - Teks rev2.1 pertama (`ff9afb7`) menolkan target pada kasus hari yang sama, sehingga invoice terbuka berikutnya akan memposting interim lagi. Ini ditemukan writer saat meninjau `ff9afb7`; CI-nya hijau karena tidak menguji urutan itu. Diperbaiki di `0280d47` dan diuji di stub (`sequence.sql`).
  - Penghapusan bahan (item keluar penyesuaian bahan, bukan pemakaian kain kantong) yang dibalik punya celah yang sama. Sekarang ia membawa biaya hasil pemutaran ulang, melawan OTHER_EXPENSE, dari hari penyesuaian sampai hari pembalikan. Event dan state-nya dicatat pada gerakan pembalik, di luar buku kumulatif dokumen penyesuaian.
  - Uji stub `docs/evidence/cp6-az/rev21-logic/`:
    - potong, terbuka: +7,00 / +10,50 pada hari potong dan −10,50 pada hari pembatalan;
    - penghapusan bahan, terbuka: +17,50 / −17,50;
    - tertutup dan tanpa invoice: sama seperti sebelumnya;
    - urutan invoice → recost tanpa invoice → invoice lagi: hanya selisihnya yang ditambahkan.
  - Fixture native: `AZ:PRESEWING_REVERSAL_THEN_LATE_INVOICE_LOWER` dan `AZ:WRITE_OFF_REVERSED_THEN_LATE_INVOICE_LOWER`.
- **Koreksi harga pembelian** (`post_material_purchase_cost_correction`): dokumen ini juga membawa tanggal invoice untuk konteks dan kejadian sen pemasok, jadi aturan yang sama berlaku: dibukukan tidak sebelum hari terima pembeliannya, dan tanggal invoice tetap menjadi tanggal dokumen.
- **PO pasangan batch: tidak diubah.** Fixture native `AZ:BATCH_PARTNER_PO` membuktikan produk menolak grup PO lain dalam satu cutting batch: `validate_cutting_batch_link`, "Cutting batch must belong to the same production order". Perubahan antrean core yang sempat ditulis dicabut (`787e8a7`). Karena itu skenario harness r9 (batch dua PO) tidak mungkin terjadi di produk, dan WIP per PO yang saling berlawanan dari r9 juga tidak.

### 26.2 Keputusan owner (24 September 2026)
Pertanyaan: invoice pemasok diberi tanggal sebelum barangnya diterima. Pilihan owner: **"1"**, yaitu dibukukan pada hari terima, dengan tanggal invoice tetap sebagai tanggal dokumen (jatuh tempo dan umur utang). Writer menerapkan aturan yang sama pada koreksi harga pembelian karena dokumen itu memakai tanggal invoice dengan cara yang sama.

### 26.3 Pemeriksaan independen `b110e54` (AY rev7.2 + AZ rev2) dan disposisinya
Pemeriksa: sub-agent read-only dengan database stub sendiri. Repro ada di `docs/evidence/cp6-ay/rev72-review/`. Tidak ada BLOCKER.

| Temuan | Tingkat | Disposisi |
| --- | --- | --- |
| 1. Bagian kantong dibandingkan dengan versi sebelum statement, bukan dengan yang diposting sync terakhir | MAJOR | Per pool terhadap state lot (`pocket_by_pool`); harness r18 |
| 2. Satu tanggal kantong (maks akhir periode) untuk semua pool | MAJOR | Tiap pool pada tanggal recost-nya; harness r18 |
| 3. Non-PO: baseline versi sebelum statement (dua recost dalam satu statement) | MAJOR | Baseline `opening_lot_hpp_gl_state.current_hpp`; uji `rev2-logic/nonpo_two_recosts` |
| 4a. Jurnal recost aksesori juga di jalur non-invoice/E tertutup | MAJOR (kebijakan) | Dipertahankan sebagai perbaikan bug (§26.1) |
| 4b. Jurnal recost aksesori tidak ikut dibatalkan bersama akrual | MINOR | Dibatalkan di `reverse_qc`, `reverse_rework_completion`, `complete_initial_import_wip_v1` |
| 5. Lot VOIDED: bagian kantong tanpa tanggal | MINOR | Rata-rata perubahan per pool lot hidup; harness r19 |
| 6. Join `any(mids)` tanpa indeks | MINOR (kinerja) | `unnest` lateral (1,12 s tanpa indeks pada 200 ribu event, stub pemeriksa) |
| 7. Pengecek fixture batch terlalu longgar | MINOR (oracle) | Mencocokkan pesan produk persis |

Yang diperiksa dan OK menurut pemeriksa: harness r1–r17 identik; fuzz 400 seed × 3 mode dengan event revaluasi, grup baru, dan komponen kantong (0 error AY, 0 selisih total per akun terhadap AS; semua penolakan berasal dari pemeriksaan konsistensi AS sendiri); repro x1, x5–x10 tanpa regresi; F9 tanpa jalur state basi; tidak ada alias yang membayangi variabel; tidak ada fungsi SECURITY DEFINER baru.

Fuzz yang sama pada rev7.3 (`docs/evidence/cp6-ay/rev7-review/fuzz_out_rev7_3.txt`): 400 seed × 3 mode, 0 error AY, 0 selisih total; 111 penolakan, semuanya dari AS.

### 26.4 Daftar risiko sisa pemeriksa: disposisi
1. **`total_hpp_cost` pada recost aksesori dianggap kolom generated.** Tidak bergantung pada anggapan itu: `v_d` membaca kolom yang sama yang dijumlahkan `rebuild_po_hpp`, sebelum dan sesudah update snapshot. Jadi `v_d` sama dengan yang dipindahkan sync, entah kolomnya generated atau diisi trigger. Fakta katalog dari rantai uji yang mengikuti hosted (AY T1 run 36000143793): kolomnya generated, `(good_qty_pcs * qty_per_good_fg_base) * hpp_unit_cost_base_snapshot`.
2. **Indeks `material_cost_revaluation_events(movement_id)` di hosted tidak diketahui.** Join `fev` sekarang lewat `unnest` (hash join, 1,12 s tanpa indeks pada 200 ribu event di stub pemeriksa). Subquery `ov` per gerakan hanya berjalan pada sync pertama sebuah PO sesudah instalasi (jalur F1). Fakta katalog dari rantai uji yang mengikuti hosted (run yang sama): tidak ada indeks yang diawali `movement_id`. Tanpa indeks, join `unnest` tetap satu hash join per sync (1,12 s pada 200 ribu event di stub pemeriksa), jadi indeks tidak ditambahkan. Hosted sendiri tidak dibaca (tidak ada SQL ke hosted).
3. **Recost non-invoice yang mengantre dengan tanggal sebelum E dipindahkan pada E.** Ini aturan yang sudah disetujui, bukan cacat keluarga ini. Di luar invoice, `process_cost_recalc_queue` memindahkannya pada hari pemrosesan antrean (keputusan M1: jalur non-invoice = AS). Jalur invoice tidak pernah lebih lambat dari itu: `greatest(E, hari recost)`. Memberi tanggal sebelum E butuh saldo pcs sebelum E, yang tidak termasuk aturan yang disetujui.
4. **Gerakan potong yang dibalik dan punya event revaluasi.** Penelusuran item ini menemukan dua cacat, keduanya sudah diperbaiki (§26.1):
   - HPP masih membawa bahan yang dibalik (AY rev7.4);
   - revaluasi pasangan yang dibalik ditargetkan nol, sehingga persediaan bahan negatif di antara dua hari itu (AZ rev2.1).
   AY memberi tanggal bagian yang dijelaskan revaluasi gerakan asal pada harinya dan sisanya pada hari pembalik, sama dengan kaki AZ.
5. **Pemeriksaan WIP negatif per PO vs per akun.** Fixture T1 memeriksa WIP per PO (lebih ketat). Engine tutup buku AW memeriksa saldo negatif per akun per tanggal, sesuai keputusan owner ("Pertahankan pemeriksaan saldo negatif per tanggal"). Semua jalur yang pernah membuat WIP per PO negatif (batch lintas PO, pembatalan potong) kini tidak mungkin atau sudah diperbaiki.

### 26.5 Bukti lokal (sebelum CI)
- **Harness AY** (`docs/evidence/cp6-ay/rev7-harness/`): r1–r20 dan f1/m2/f1_noninv/f1_closed tanpa error. `output_rev7_3.txt` untuk rev7.3 dan `output_rev7_4.txt` untuk rev7.4. Pada rev7.4, r1–r19 sama dengan rev7.3 kecuali UUID dan jam acak.
- **Fuzz** rev7.3: lihat §26.3.
- **Logika AZ** (`docs/evidence/cp6-az/rev2-logic/`): nonpo, nonpo_two_recosts, bsv, acc, pocket pada mode E terbuka, E tertutup, dan tanpa invoice; semua sesuai harapan (`output_rev2.txt`).
- Fungsi AZ `post_material_supplier_invoice`, `post_material_purchase_cost_correction`, dan fungsi AY `rebuild_po_hpp` dikompilasi di PostgreSQL lokal sekali pakai sebelum push.

### 26.6 Hasil CI (database uji sekali pakai; tidak ada SQL ke hosted)
Kode akhir: **AY rev7.4** (SQL sha256 `29b89776…af43`, sejak `769abfe`) dan **AZ rev2.1** (SQL sha256 `e1968c8f…3028971`, `0280d47`). Paket T3 dibangun ulang di `0628a68` dari pin run 36000747775: blob `cb02b815…8ab4`, 65.237 byte, dan sha di log cocok.

**AY T1 run 36000143793** (`ff9afb7`; SQL AY sama dengan akhir):
- Sebelum AY: 4 COUNTEREXAMPLE + 4 PASS.
- Sesudah AY: **8/8 PASS**, primary tidak berubah, clone 0.
- `AY:PRESEWING_REVERSAL_QUEUE`:
  - sebelum: materi lot tetap 80,00 (harapan 32,00) dan WIP PO −40,00 pada hari pembatalan;
  - sesudah: 32,00, WIP PO 0 / 20,00 / 20,00 / 8,00, dan FG −48,00 pada hari pembatalan.
- Fakta katalog: lihat §26.4.
- Bukti: `docs/evidence/cp6-ay/native_t1_run36000143793_*_rev7_4.json`.

**AZ T1 run 36000747815** (`0280d47`):
- Sebelum AZ: 23 COUNTEREXAMPLE + 5 PASS.
- Sesudah AZ: **28/28 PASS**, primary tidak berubah, clone 0.
- Kasus baru putaran ini:
  - `INVOICE_BEFORE_RECEIPT_LOWER` (run 35996572941, `9b5fc09`): invoice bertanggal 20 Sep untuk barang yang diterima 21 Sep. Sebelum AZ jurnalnya 24 Sep (hari ini); sesudah AZ pada 21 Sep, tanggal dokumen tetap 20 Sep, dan tidak ada gerakan pada 20 Sep.
  - `COST_CORRECTION_BEFORE_RECEIPT_LOWER`: sebelum AZ jurnal 20 Sep dan persediaan −17,50 sejak 20 Sep (CRITICAL). Sesudah AZ jurnal 21 Sep, 0 pada 20 Sep, dan tidak ada blocker.
  - `PRESEWING_REVERSAL_THEN_LATE_INVOICE_LOWER`: sebelum AZ persediaan −10,50 sejak 22 Sep (CRITICAL) dan WIP PO −7,00 pada 21 Sep. Sesudah AZ persediaan −17,50 / 0 / 0 / −10,50 (harga invoice × unit di tangan), FG −14,00 pada hari lot dan −53,60 kumulatif pada hari pembatalan, WIP PO 0 / 16,50 / 16,50 / 6,60, dan tidak ada blocker.
  - `WRITE_OFF_REVERSED_THEN_LATE_INVOICE_LOWER`: sebelum AZ persediaan −17,50 sejak 22 Sep (CRITICAL). Sesudah AZ −17,50 / 0 / 0 / −17,50, tanpa blocker.
- Bukti: `docs/evidence/cp6-az/native_t1_run36000747815_*_rev2_1b.json` dan `native_t1_run35996572941_*_rev2_1.json`.

**Run yang gagal di putaran ini (dicatat apa adanya):**
- `769abfe`:
  - AY T1 35998326956 gagal pada `AY:PRESEWING_REVERSAL_THEN_LATE_INVOICE_LOWER`. Ini temuan produk yang menghasilkan AZ rev2.1. Pemeriksaan fixture yang bergantung pada AZ lalu dipindah ke probe AZ.
  - AZ T1 35998326947 INCOMPLETE di kedua fase karena label bahan tiruan melebihi varchar(60). Ini kesalahan fixture writer.
- T3 35993480811, 35996090223, 35996572950, 35998327146, 36000143854, dan 36000747775 merah karena paket basi. Ini memang disengaja: run-run itu menangkap pin untuk paket berikutnya.

**T2 run 36001522757** (`0628a68`, kode akhir; seed QUIETED, fixture PAYROLL_APPROVED):
- **Identik** dengan run 35992864405 (`b110e54`) pada semua nilai ringkasan, jumlah grup, status kasus, ID kasus, dan urutannya. Yang berbeda hanya run, job, head, catatan, dan 48 UUID hasil generate.
- Grup lama 230/31/65: tidak ada yang bertambah, hilang, atau pindah. 12 HOLD identik.
- AR 146 + 28 PASS; temporal 16 + 15 dan race 4 + 6 PASS.
- Oracle beku tercatat apa adanya: NEW_CASES 8 COUNTEREXAMPLE + 1 INCOMPLETE, trial AO 4 INCOMPLETE, kalender 12 COUNTEREXAMPLE.
- Oracle yang disetujui: AS 8/8, kalender 12/12, AO INVOICE 4/4, dan `ADJUSTMENT_DATE`, semuanya MATCH.
- Di luar berkas bukti, log hanya berbeda pada urutan baris jurnal dalam 5 contoh balik NEW_CASES dan satu error trial AO (himpunan barisnya sama), UUID dan hash per run di AR konkurensi, serta sha256 AY/AZ di baris akhir AR.
- Bukti: `docs/evidence/cp6-t2/run36001522757_ay_rev7_4_az_rev2_1.json`.

**T3 run 36001514536** (`0628a68`): **hijau**, ketiga job sukses.
- `T3_PINS_REPRODUCED` equal true.
- Instalasi 24 file AC..AZ PASS; AW/AX/AY/AZ terverifikasi dengan sha256 AY `29b89776…` dan AZ `e1968c8f…`.
- Backup/restore RESTORED_SAME_MEANING: 318 tabel dan 1.647 baris sama. 19 error restore semuanya pg_cron, dan perbedaan katalog semuanya terklasifikasi.
- Browser 10/10 PASS, 0 error konsol.
- Advisor 73 → 127: 54 tambahan, semuanya INFO `rls_enabled_no_policy` untuk tabel internal. Termasuk di dalamnya `invoice_recost_execution_context`, `po_hpp_gl_lot_state_v1`, dan `po_hpp_gl_material_state_v1`.
- Fingerprint hosted sama (16 jenis) dan kapsul 11/11.

**CodeQL run 36001525302** (`0628a68`): sukses, 0 hasil untuk python, actions, c-cpp, dan javascript-typescript.

**Riwayat putaran ini:** AY T1 dan AZ T1 hijau pada `c7eeabc` (rev7.3: 35996090230, 35996090212) dan `ff9afb7` (36000143793, 36000143836).

### 26.7 Yang masih terbuka (jujur)
- ~~**Pemakaian kain kantong yang dibalik** tidak diberi kaki interim.~~ Ditemukan auditor (AB-01), terbukti native, dan diperbaiki di §27.1.
- **F10:** tanggal jurnal dibatasi hari ini (tidak boleh di masa depan). Ini disengaja.
- **Fixture native** kontraktor memakai satuan lama `yd` yang didaftarkan fixture ke `uom_definitions`. Fixture invoice dan koreksi harga memakai satu penerimaan per dokumen; aturan "hari terima terakhir dari baris-barisnya" untuk invoice multi-penerimaan hanya diuji lewat kode, belum native.
- **Beban tulis state** (kunci `M:` per rebuild) belum diukur di data besar.

### 26.8 Pelajaran
- Item yang hampir dicatat sebagai "desain dasar, total benar" (pasangan yang dibalik) ternyata membuat saldo persediaan negatif CRITICAL begitu diuji native. Uji native dulu sebelum mengklasifikasi risiko sebagai bukan cacat.
- Fixture di probe AY yang ikut memeriksa WIP dan persediaan bergantung pada AZ. Pemeriksaan yang melibatkan dua paket dijalankan di probe tempat keduanya terpasang (probe AZ).
- Satu putaran AZ T1 gagal karena label bahan tiruan melebihi varchar(60). Itu kesalahan fixture writer, bukan temuan produk.
- Menelusuri "risiko sisa" sampai ke kode produk menghasilkan temuan nyata (rev7.4). Risiko yang hanya dicatat bisa menyembunyikan cacat.
- Aturan owner untuk satu dokumen (invoice) perlu dicek ke semua dokumen yang memakai kolom yang sama (koreksi harga pembelian).
- Fixture baru yang memakai alur produk yang belum pernah dipakai probe (pembatalan potong, koreksi harga) kini punya savepoint atau pemeriksaan fixture sendiri, supaya kegagalan setup terbaca sebagai kegagalan fixture, bukan temuan produk.

## 27. Tindak lanjut audit GPT atas `737649b` (24 September 2026, writer Claude)

Label: T1_FAMILY, T2_REGRESSION, T3_PREP, AUDITOR_SCENARIO; bukan bukti rilis dan bukan penerimaan independen. CP6 tetap HOLD, 12 HOLD historis tetap HOLD, `production_go=false`. Tidak ada SQL ke hosted; cabang kompetisi tetap `ca7f095`.

Audit GPT (baca-saja, `INDEPENDENT_SOURCE_REVIEW` + `INDEPENDENT_ARTIFACT_CHECK`) belum menerima A+B sebagai gate CP6 selesai. Ada tiga temuan (AB-01 P1 sementara, AB-02 P2, AB-03 P3) dan empat permintaan balik. Semuanya ditangani di bawah ini.

### 27.1 AB-01 (P1): pembalikan pemakaian kain kantong — terbukti native, diperbaiki
- **Percobaan pertama tidak sah (writer).**
  - Run 36008799715 (`b0afb99`): fixture memanggil fungsi internal `erp.save_pocket_fabric_action_v1`, mendapat "permission denied" pada REGISTER, lalu mencatat penolakan itu sebagai PASS. Ini oracle yang dilonggarkan oleh fixture writer.
  - Diperbaiki di `b746153`: aksi lewat RPC publik yang dipakai UI (`public.erp_save_pocket_fabric_action_v1`), dan setiap error membuat kasus INCOMPLETE.
  - Aturan yang sama diterapkan pada fixture koreksi harga. Run CI-nya selama ini sudah melewati jalur nyata, jadi hasilnya tidak berubah.
  - Bukti run yang tidak sah tetap disimpan dengan catatan: `docs/evidence/cp6-az/native_t1_run36008799715_*_ab01.json`.
- **Reproduksi pada AZ akhir yang belum diubah** (AZ T1 run 36009699973, `b746153`), urutan dari auditor:
  - pembelian 10 unit @ 10 pada 21 Sep;
  - pemakaian kain kantong 10 unit pada 22 Sep (tanpa periode kantong);
  - pembalikan pada 24 Sep;
  - invoice terlambat 8,25 bertanggal ekonomi 21 Sep.

  Hasilnya:
  - MATERIAL_INVENTORY −17,50 pada 22–23 Sep, padahal 0 unit di tangan;
  - AW `GL_INVENTORY_NEGATIVE_ASOF` CRITICAL per 22, 23, dan 24 Sep;
  - invoice hanya memposting jurnalnya sendiri pada 21 Sep (AP −82,50, GRNI +100,00, persediaan −17,50).

  Fase sebelum AZ sama (COUNTEREXAMPLE). Fase sesudah: 28 PASS + kasus ini FAIL. Angkanya sama dengan hitungan auditor.
  - Bukti: `docs/evidence/cp6-az/native_t1_run36009699973_*_ab01_repro.json`.
- **Penyebab:** kaki interim penghapusan bahan yang dibalik (AZ rev2.1) mengecualikan pemakaian kain kantong.
- **Perbaikan (`46ad845`):** pengecualian dicabut.
  - Pembalikan pemakaian kantong hanya bisa dilakukan selama tidak ada periode kantong aktif yang mencakupnya (`guard_pocket_period_v1`: "Batalkan alokasi periode sebelum membatalkan pengeluaran kain kantong"). Karena itu, saat dibalik, ia adalah penghapusan bahan biasa melawan OTHER_EXPENSE, akun yang juga dipakai `pocket_fabric_checks_v1` dan revaluasi dokumen penyesuaian.
  - Uji stub `docs/evidence/cp6-az/rev21-logic/pocket.sql`: +17,50 pada hari pemakaian, −17,50 pada hari pembalikan.
- **Sesudah perbaikan:** AZ T1 run 36010562795 (`46ad845`):
  - Sebelum AZ: 24 COUNTEREXAMPLE + 5 PASS.
  - Sesudah AZ: **29/29 PASS**.
  - Kasus AB-01 sesudah AZ: persediaan −17,50 / 0,00 / 0,00 / −17,50 (21–24 Sep, yaitu harga invoice × unit di tangan).
  - Jurnal tambahan: MATERIAL_COST_REVALUATION +17,50 persediaan / −17,50 OTHER_EXPENSE pada 22 Sep, dan kebalikannya pada 24 Sep.
  - Tidak ada blocker AW per 22, 23, atau 24 Sep.
  - Bukti: `docs/evidence/cp6-az/native_t1_run36010562795_*_ab01_fix.json`.

### 27.2 AB-02 (P2): cakupan fixture
Kasus native baru `AZ:POCKET_USAGE_REVERSED_THEN_LATE_INVOICE_LOWER`. Yang diperiksa:
- saldo harian per akun;
- baris jurnal invoice per tanggal dan akun;
- blocker AW per 22, 23, dan 24 Sep.

Kontrol yang sudah PASS: `AZ:WRITE_OFF_REVERSED_THEN_LATE_INVOICE_LOWER`.

### 27.3 AB-03 (P3): arsip bukti T3 dan CodeQL
- `docs/evidence/cp6-t3/run36001514536_package24_final.json`: semua baris JSON dari tiga job T3 akhir, baris `T3_PINS_SHA256`, dan digest ketiga artefak.
- `docs/evidence/cp6-t3/codeql_run36001525302_final.json`: baris gate keempat bahasa (`result_count` 0) dan digest keempat artefak.
- `manifest.json` per SARIF ada di dalam artefak Actions. Proxy sesi ini menolak unduhan artefak (403), jadi yang tercatat adalah digest zip artefak dari API. Artefak kedaluwarsa 24 Okt 2026; owner atau auditor dapat mengunduh dan mencocokkannya dengan digest itu sebelum tanggal tersebut.
- Arsip yang sama untuk run akhir sesudah AB-01: `run36011358760_package24_ab01_final.json` dan `codeql_run36011369322_ab01_final.json`.

### 27.4 Permintaan 3: runtime untuk skenario auditor sendiri
Workflow baru: **CP6 Auditor Scenario** (`.github/workflows/cp6-auditor-scenario.yml`, runner `scripts/cp6_auditor_scenario.py`).
- Rantainya sama dengan probe: klon AN, lalu AU, AV, AW, AX, AY, dan (fase `after`) AZ dari berkas T1 yang di-commit. Kandidat diverifikasi dulu.
- Tiap kasus auditor berjalan dalam savepoint yang di-rollback, dan hasil lengkapnya dicetak sebagai satu baris JSON. sha256 berkas skenario dicetak di awal log.
- Job hanya gagal bila run-nya sendiri tidak lengkap; hasil kasus (PASS/FAIL/COUNTEREXAMPLE) dibaca auditor.
- Uji asap pada `d5761d3` (run 36009043825) hijau. Uji asap itu hanya memutar ulang kasus kontrol writer.
- Cara pakai:
  1. Tulis `scenario.py` yang mendefinisikan `def cases(cur, today): return [(id, fungsi_tanpa_argumen), ...]`. Fungsi mengembalikan dict dengan `status`. Helper yang boleh diimpor: `cp6_az_probe` (`produce`, `cut_only`, `invoice`, `ledger_days`, `adjust`, `final_receipt`, dan lain-lain), `cp6_aw_probe.preflight`, serta RPC produk lewat `awp.chain.production`.
  2. `base64 -w0 scenario.py`.
  3. Di GitHub: Actions → CP6 Auditor Scenario → Run workflow → cabang `claude/new-session-deapao` → tempel base64 ke `scenario_b64` → `phase` = after.
  4. Baca baris `{"group": "AUDITOR_CASES_AFTER", ...}` di log.
- Hanya pemegang akses tulis repo yang bisa men-dispatch. Skenario hanya berjalan pada database sekali pakai milik job itu, tanpa secret.

### 27.5 Hasil CI akhir
Kode akhir: AY rev7.4 (SQL `29b89776…af43`, tidak berubah) dan AZ rev2.1 dengan perbaikan AB-01 (SQL `9007eefc…25c9`, `46ad845`). Paket T3 dibangun ulang di `208afce` dari pin run 36010562618: blob `80e30b96…3068`, 65.237 byte, dan sha di log cocok. Hanya berkas AZ dan manifest yang berubah.

| Uji | Run (head) | Hasil |
| --- | --- | --- |
| AZ T1 | 36010562795 (`46ad845`) | Sebelum AZ 24 COUNTEREXAMPLE + 5 PASS; sesudah AZ 29/29 PASS |
| AY T1 | 36000143793 (`ff9afb7`) | 8/8 PASS; SQL AY tidak berubah sejak itu |
| T2 | 36011365657 (`208afce`) | Identik dengan run 36001522757 pada semua status, jumlah, ID kasus, 12 HOLD, dan oracle yang disetujui (MATCH); beda hanya metadata dan 48 UUID |
| T3 | 36011358760 (`208afce`) | Hijau: `T3_PINS_REPRODUCED` equal true, 24 file terpasang, AW/AX/AY/AZ terverifikasi, RESTORED_SAME_MEANING (318 tabel / 1.647 baris; 19 error restore pg_cron terklasifikasi), browser 10/10, advisor 73 → 127 (54 INFO `rls_enabled_no_policy`) |
| CodeQL | 36011369322 (`208afce`) | 0 hasil di keempat bahasa |
| Runtime auditor | 36011380669 (`208afce`) | RUN_COMPLETE; kasus contoh PASS; primary tidak berubah, clone 0 |

Bukti: `docs/evidence/cp6-t2/run36011365657_ab01_fix.json`, `docs/evidence/cp6-t3/run36011358760_package24_ab01_final.json`, dan `docs/evidence/cp6-t3/codeql_run36011369322_ab01_final.json`.

### 27.6 Status
- AB-01 terbukti native dan diperbaiki; AB-02 dan AB-03 ditangani.
- Penerimaan independen AY rev7.4, AZ rev2.1, dan perbaikan AB-01 masih `RERUN_REQUIRED`: menunggu auditor menjalankan skenarionya sendiri lewat §27.4.
- CP6 tetap HOLD sampai penerimaan itu ada.

### 27.7 Pelajaran
- Fixture yang mengubah penolakan apa pun menjadi PASS adalah oracle yang dilonggarkan. Penolakan yang memang diharapkan harus dicocokkan dengan pesan produknya (seperti `AZ:BATCH_PARTNER_PO`); selain itu, error membuat kasus INCOMPLETE.
- Pengecualian yang ditulis "demi aman" (pemakaian kantong) perlu dibuktikan aman secara native. Temuan auditor muncul tepat di pengecualian itu.

## 28. Putaran kedelapan: perbaikan audit independen (handoff auditor 25 September 2026) (writer Claude)

Label: T1_FAMILY, T2_REGRESSION, T3_PREP, AUDITOR_SCENARIO; bukan bukti rilis dan bukan penerimaan independen. CP6 tetap
HOLD, `audit_complete=false`, 12 HOLD historis tetap HOLD, `production_go=false`. Tidak ada SQL ke hosted; cabang
kompetisi tetap `ca7f095`; `main`, Cloudflare, Supabase hosted, dan ERP-Garment lama tidak disentuh.

Sumber tugas: `AUDIT_WRITER_HANDOFF_CP6.md` di cabang auditor `audit/cp6-final-20260924-gpt-a0bcadf` (commit `8d3ee4c`,
dibaca saja). Keputusan owner D01–D06: semua opsi A, `OWNER_CONFIRMED_CHAT` 25 Sep 2026 (termasuk akun lawan AX =
OTHER_INCOME). Urutan kerja yang diminta: A1–A3 dan A9, C0, lalu A4, A5, A10, C6, rollback AC..AV, head baru.

### 28.1 Produk: keluarga BA (`v2.6.20ba`, `supabase/dev/cp6_ba_t1_family.sql`)
Dibangun oleh `scripts/cp6_ba_build.py` dari definisi yang sedang dijalankan rantai (AR, AP, AV, migration CP5 19;
berkas T1 AW dan AZ) dengan substitusi yang diperiksa satu per satu. BA menggantikan 8 fungsi dan menambah 1 fungsi serta
1 tabel. Registry lapisan (`scripts/cp6_layers.py`) mencatat fungsi AW/AZ yang diganti BA, sehingga verifikasi AW dan AZ
tidak lagi membandingkan fungsi itu setelah BA terpasang.

| ID | Temuan | Perbaikan | Kode penolakan / hasil |
| --- | --- | --- | --- |
| A1 (CP6-09, P1) | Batch impor kedua untuk item yang sama dibukukan lagi (stok/nilai dobel) | `erp.post_opening_balance`: batch impor tidak boleh membukukan item saldo awal yang sudah dibukukan batch impor lain dengan identitas sama (bahan+gudang+roll; FG produk+gudang+grade; kas per akun; WIP/BS tanpa sumber PO menurut aturan AR). Sumber berbeda tetap boleh | `BA_IMPORT_OPENING_ALREADY_POSTED` |
| A2 (CP6-01, P1) | Halaman potong/pickup/BS memakai zona perangkat | Frontend (`01c28e1`): helper WIB `cp6WibPhysicalTimeToIso`; nilai tidak valid menonaktifkan aksi | Matriks TZ + DOM test per halaman gagal di kode lama, lulus di kode baru |
| A3 (CP6-02, P1) | COMPLETE WIP bertanggal sebelum pembalikan output | `erp.complete_initial_import_wip_v1`: output butuh sisa tahap pada tanggalnya dan setiap hari sesudahnya; pada hari pembalikan, output dicatat sesudah pembalikan | `BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING` |
| A4 (CP6-03, P2) | Koreksi harga 1 unit yang habis dipakai menyisakan ±0,01 | `erp.sync_material_cost_revaluation`: recost gerakan pemakaian = nilai sekarang (selisih nilai stok yang dibulatkan sebelum/sesudah gerakan) dikurangi yang sudah diposting (pembulatan kumulatif dalam dokumen), sehingga stok 0 bernilai 0. Retur supplier tetap memakai aturan AZ (lihat 28.2) | Kasus sen UP/DOWN × DIRECT/INVOICE lulus |
| A5 (CP6-04, P2) | Selector BS Resolution dan draf impor terpotong 100/50 | Sumber yang masih bisa diklaim dan draf yang belum diposting selalu terdaftar; kotak cari di UI bila daftar > 20 (facade publik tidak berubah; cek batas CP5 lulus) | Klaim delivery tertua setelah 100 yang lebih baru; draf tertua setelah 51 |
| A6 (CP6-24, P3) | Close tanggal yang sama membuat filing kedua | `erp.close_accounting_through`: close ulang tanggal yang sudah ditutup ditolak; close sesudah reopen tetap boleh | `CLOSE_ALREADY_CLOSED` |
| A9 (CP6-07, D02=A, P1) | Refund/apply melebihi kapasitas pada tanggalnya | `erp.manage_initial_prepayment_v1`: ditolak bila kapasitas pada tanggalnya atau hari mana pun sesudahnya menjadi negatif (supplier, customer, vendor). Aturan stok AUD-S04 sudah ditegakkan AO (`AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY`); BA tidak menambah apa pun di sana | `BA_ADVANCE_DATED_CAPACITY` |
| A10 (CP6-18, D03=A, P2) | WIP awal produk A diselesaikan sebagai produk B | Produk pada WIP awal mengikat output; tanpa produk, brand/warna sumber harus cocok; yang diperiksa dan yang tidak diketahui dicatat di `erp.initial_import_wip_output_identity_v1` (tidak diketahui ≠ cocok) | `BA_WIP_OUTPUT_PRODUCT_BOUND`, `BA_WIP_OUTPUT_SOURCE_MISMATCH` |
| A7, A8 | Opsional (P3) | Tidak dikerjakan pada putaran ini | — |

Tabel baru punya dua referensi produk; keduanya diklasifikasikan DERIVED di registry AV
(`erp.assert_new_stock_cutoff_coverage_v1`), dan guard fail-closed AV dijalankan di akhir install BA. Guard AV tidak
dilonggarkan.

### 28.2 Regresi yang ditemukan T2 dan perbaikannya
- T2 run 36087253697 (`5d54472`, BA terpasang): dari 360 kasus, tepat dua bergerak terhadap hasil tercatat, keduanya
  PASS → INCOMPLETE dengan `N_SOURCE_CENT_BALANCE_MISMATCH`:
  - `CROSS:SUPPLIER_CENT:SPLIT_RETURN`: persediaan 0,01 dan variance −0,01 tersisa pada stok 0;
  - `CROSS:SUPPLIER_CENT:CROSS_SOURCE_INVERSE_IDENTITY`: persediaan 0,05, seharusnya 0,06.
  Semua kasus, HOLD, dan oracle yang disetujui lainnya identik dengan referensi tercatat (run 36011365657 pada `208afce`;
  produk `9add57e` sama).
- Penyebab: aturan sen A4 juga berjalan untuk gerakan retur supplier. Kredit persediaan retur ditentukan oleh cent state
  baris pembelian (v2.6.20n: 0,02 / 0,01 / 0,02 untuk tiga unit @0,015), sehingga sennya dipindah dua kali walau biaya
  tidak berubah.
- Perbaikan (`35612d6`): retur supplier kembali ke aturan AZ (hanya perubahan biaya yang direvaluasi). Oracle N tidak
  diubah. Probe BA mendapat kontrol `A4:SUPPLIER_RETURN_SPLIT_CONTROL` (PASS di kedua fase: tiga retur 1 unit @0,015,
  tanpa revaluasi, persediaan kembali 0).
- Hasil sesudah perbaikan: dua run T2 pada produk yang sudah diperbaiki, identitas per kasus **sama dengan referensi
  tercatat** (run 36011365657 pada `208afce`):
  - run 36089425974 (`35612d6`, dispatch) dan run 36089919596 (`a4ad590`, alat B5/B6);
  - kedua kasus SUPPLIER_CENT kembali PASS; 9 perpindahan NEW_CASES yang sudah tercatat (8 DATE dengan oracle disetujui
    MATCH, `ADJUSTMENT_DATE:False` INCOMPLETE) dan 12 HOLD identik;
  - business 179 PASS + 39 CONTROL_PASS + 12 DATE_POLICY_REVIEW_REQUIRED, imports 31, values 65; AR 146 + 28 race; AT 16,
    AU 15, race 4 + 6; oracle AS 8/8 MATCH; oracle B 5 PASS dan 12 kalender MATCH; AO trial sesuai catatan (8 PASS + 4
    INCOMPLETE);
  - baris kebijakan kalender hanya berbeda pada id fixture dan tanggal (tanggal run bergeser), statusnya sama;
  - run `a4ad590` mencetak `T2_FIXTURE_SUMMARY` (fase regression 103 completion, fase AR 6, tidak ada penolakan) dan
    `run_identity`.
  Bukti: `docs/evidence/cp6-t2/run36089425974_ba_fix.json`, `docs/evidence/cp6-t2/run36089919596_ba_b5_b6.json`.
  Hasil beku tetap; MATCH adalah oracle yang disetujui, bukan PASS kasus beku.

### 28.3 Alat dan protokol (bagian B)
- **B1 (CP6-10)** `scripts/cp6_auditor_runner.py`: grup ketat untuk kasus savepoint auditor.
  - ID kasus ganda menolak seluruh grup.
  - Status di luar PASS/FAIL/COUNTEREXAMPLE/INCOMPLETE, atau hasil bukan dict → INCOMPLETE (nilai asli dicatat).
  - Sesudah setiap kasus: batas ERP/platform/Auth/ACL, katalog dan hash baris skema `public`, advisory lock sesi runner,
    dan sesi klien lain pada clone. Lock/sesi yang **baru sejak kasus dimulai** membuat kasus INCOMPLETE lalu dibersihkan.
  - Planned vs final dicetak.
  - Job self-test (`cp6_auditor_scenario_selftest.py`): satu kasus per kebocoran; lulus hanya bila detektor yang
    diharapkan menyala dan tidak ada detektor lain.
  - Dua kesalahan alat writer yang ditemukan self-test dan diperbaiki: `pg_stat_activity` di-cache per transaksi
    (sekarang `pg_stat_clear_snapshot()` sebelum dibaca), dan 46 lock transaksi milik setup runner sempat terhitung
    sebagai kebocoran (sekarang hanya lock baru yang dihitung). Run 36088432785 (`f22f7b9`): self-test SELFTEST_PASS,
    sampel RUN_COMPLETE.
- **B2 (CP6-11)** `scripts/cp6_t3_package_run.py`: job install/capture T3 hijau hanya bila seluruh gate terpenuhi
  (terpasang, primary tidak berubah, drill backup/restore RESTORED_IDENTICAL atau RESTORED_SAME_MEANING, dan advisor
  baru hanya INFO `rls_enabled_no_policy` di skema erp). Gate dicatat di laporan. Komentar "green job can be cited
  without reading the log" dihapus.
- **B3 (CP6-12)** rollback seluruh paket rilis AC..BA (lihat 28.4).
- **B4 (GATE-04/08)** mode browser runtime auditor: `scripts/cp6_auditor_modes.py` (`run_browser`) dan
  `scripts/cp6_auditor_browser_host.mjs`.
  - Auditor memberi modul ES lewat input workflow `browser_b64` yang mengekspor `cases(ui, today)`.
  - Runtime membuat salinan yang dikomit, menyalakan PostgREST sendiri untuk salinan itu, mem-build UI cabang ini (mode
    DISPOSABLE_TEST; build ini hanya mau jalan di origin `http://127.0.0.1:4176`) di belakang proxy loopback yang hanya
    meneruskan Auth dan RPC publik, lalu menjalankan modul di Playwright.
  - `ui.login(role)` membuat user Auth nyata, memetakannya ke `erp.app_users` di salinan, dan masuk lewat form login.
  - ID ganda menolak run; status di luar kosakata menjadi INCOMPLETE; user Auth, container, server UI, dan salinan dihapus;
    jumlah baris Auth primary harus kembali. Kata sandi dan token per user tidak pernah dicetak (hanya diredaksi dari
    hasil dan error).
  - Sampel `scripts/cp6_auditor_browser_sample.mjs` jalan di setiap push: halaman login tanpa sesi; OWNER masuk lewat
    form, GUDANG (layar HP) ditolak preflight close.
  - Tiga kesalahan alat writer ditemukan CI dan diperbaiki (tidak ada guard produk yang diubah):
    - container PostgREST menunjuk salinan HTTP yang sudah dihapus (run 36089919668);
    - origin 4177 ditolak guard build disposable `DISPOSABLE_BUILD_REQUIRED` (run 36090518187); host pindah ke 4176;
    - CodeQL python menghitung 1 hasil sesudah mode HTTP ditambahkan (run 36090056167; gate versi itu hanya mencetak
      jumlahnya). Satu-satunya keluaran nilai sensitif yang baru adalah baris `::add-mask::` kata sandi/token per user;
      baris itu dihapus dan hasilnya 0 (run 36090824553). Gate CodeQL sekarang mencetak setiap temuan (`CODEQL_FINDING`).
  - Run 36090909397 (`4c379bf`): `RUN_COMPLETE`; kedua kasus browser PASS, 2 user dibuat dan dihapus, jumlah Auth
    kembali, salinan dan container terhapus, 0 console error; kasus DB, race, dan HTTP sampel PASS; self-test
    SELFTEST_PASS; primary tidak berubah. Bukti: `docs/evidence/cp6-auditor/run36090909397_samples.json`.
- **B5 (CP6-14)** T2 mencetak `T2_FIXTURE_SUMMARY` per fase (setiap completion fixture per kasus, penolakan), di samping
  baris per kasus `T2_FIXTURE_PAYROLL` dan `T2_SEED_QUIETED` per grup. Aturan tetap: hanya item yang dibuat kasus itu
  sendiri yang dilengkapi; kasus yang menguji pekerjaan belum dibayar tidak diubah.
- **B6** setiap runner (probe BA, T2, paket T3, rollback T3, skenario auditor) mencetak baris `run_identity` di awal:
  label, head alat, commit produk acuan (perubahan terakhir pada migrations, family dev, paket rilis/rollback, frontend),
  run id, dan attempt. Hasil beku tidak dilabel ulang.

### 28.4 B3: rollback AC..BA varian rilis
- `scripts/cp6_t3_rollback_acav.py`: rollback AC..AV yang sudah ditinjau (`supabase/rollbacks`) dipin ulang untuk
  rantai rilis dengan **hanya** substitusi yang tercatat di paket (`docs/evidence/cp6-t3/release_pins.json`):
  - digest statements berkas (sendiri dan pendahulu): sha sumber → sha paket. AC..AN sebelumnya menerima dua digest
    (berkas dan bentuk applier uji); varian rilis hanya menerima digest yang dicatat applier rilis;
  - jumlah objek dan fingerprint katalog, dan hash capsule historis, sesuai pin ulang paket;
  - teks view AC `erp.v_payroll_nota_browser` dalam bentuk hosted (temuan view G-01).
  Pin lain (hash fungsi, bentuk capsule, boundary yang dicatat saat install) tidak diubah. Pin katalog yang tidak
  terpetakan menghentikan build. Berkas asli tidak dilonggarkan.
- AW..BA dibangun dari capture native (BA: +17 objek, 8 fungsi diganti).
- Siklus (`scripts/cp6_t3_rollback.py cycle`), run 36089474604 (`2ed27cd`, paket dengan BA sebelum perbaikan 28.2):
  **127/127 PASS**, primary tidak berubah.
  - Penolakan tanpa perubahan: AZ, AV, dan AC di luar urutan saat BA terpasang; admission terbuka.
  - Siklus 1: BA..AC dibalik sampai AB; setiap keadaan sama dengan keadaan sebelum install berkas itu. Sebelum setiap
    varian AC..AV, rollback asli rantai uji ditolak di rantai rilis (`<K>_ROLLBACK_PLATFORM[_IDENTITY]_OR_SUCCESSOR`)
    tanpa perubahan.
  - Install ulang 25 berkas sama dengan install pertama.
  - Siklus 2 dibandingkan dengan keadaan saat install ulangnya sendiri, jadi setiap baris dihitung termasuk waktu
    capture dan boundary capsule (tidak ada kolom yang diabaikan); berakhir persis di AB.
  - Matriks post-use: di setiap keluarga (25), sesudah install, satu transaksi bisnis dikomit (saldo awal piutang
    pelanggan 17,25 diposting lewat `erp.post_opening_balance` dengan klaim OWNER: 1 jurnal, 2 baris), lalu rollback
    keluarga itu ditolak dengan `<K>_POST_USE_ROLLBACK_REFUSED` dan tidak ada yang berubah.
  - Bukti: `docs/evidence/cp6-t3/rollback_cycle_run36089474604.json`.
- Sesudah perbaikan BA (28.2), capture BA diulang dan siklus dijalankan lagi pada paket baru.
  - Capture run 36089919551 (`a4ad590`): CAPTURED, primary tidak berubah; blob `8b375814…1b47` (20495 byte). Entri
    AW..AZ identik; BA di-capture ulang untuk berkas paket BA baru (sha256 `135facce…7cd0`).
  - Rollback BA hanya berubah pada pin digest statements dan fingerprint katalog terpasang; AW..AZ hanya baris header;
    varian AC..AV tidak berubah.
  - Siklus run 36090518234 (`a095a9d`): **127/127 PASS**, cek yang sama dan urutan yang sama seperti run 36089474604,
    primary tidak berubah. Bukti: `docs/evidence/cp6-t3/rollback_cycle_run36090518234.json`.

### 28.5 Dokumen (bagian C)
- **C0** `docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25.md`: addendum ERP-ADD-CP6-2026-09-25-01 untuk
  D01–D06. Mengutip M/P/BR dengan hash yang dicatat auditor. Berisi aturan tanggal D01 (C1), daftar cek per tanggal D04
  (C4), dan akun lawan AX = OTHER_INCOME (C5).
  - Pengesahan: D01–D05 disahkan tertulis owner di chat 25 September 2026, termasuk batas periode tertutup (3.4) dan
    tafsir D03 untuk data yang belum diketahui (5.3). Jawaban owner "sah bos" atas usulan kalimat writer dikutip apa
    adanya di bagian 9.
  - Teks yang disahkan: bagian 1–8 versi sha256 `d39762da…926d` (commit `5d54472`). Berkas sesudah bagian 9 diisi:
    sha256 `e83d56e6…0c99`; yang berubah hanya baris status dan bagian 9.
  - D06 tetap `OWNER_CONFIRMED_CHAT` sampai lampiran C6 ditinjau auditor dan disahkan owner.
- **C6** `…_LAMPIRAN_C6.md` (sha256 `72621c8a…bc0d`): USULAN WRITER daftar acceptance aksesori (ACC-01..04) dan laundry
  (LAU-01..07) berlabel BASELINE/CR-TUNDA. Writer tidak memegang teks M:1691–1699, M:1753–1757, dan M:4448–4479;
  auditor diminta mencocokkan setiap baris, owner mengesahkan lewat addendum.

### 28.6 Hasil CI
Semua run di cabang ini, CI sekali pakai. Produk acuan (B6) untuk head baru adalah `a095a9d`; commit sesudahnya hanya
mengubah alat auditor, gate CodeQL, dan dokumen/bukti. Antara `a4ad590` dan `a095a9d` produk hanya berbeda di berkas
rollback T3 (tidak dipakai T2).

| Workflow | Run | Head alat | Produk acuan | Hasil |
| --- | --- | --- | --- | --- |
| CP6 BA T1 Family Probe | 36090518293 | `a095a9d` | `a095a9d` | before: 23 COUNTEREXAMPLE + 16 PASS sesuai rencana; after: 39/39 PASS (termasuk `A4:SUPPLIER_RETURN_SPLIT_CONTROL`); primary tidak berubah, clone terhapus |
| CP6 T2 Combined Regression | 36089919596 | `a4ad590` | `a4ad590` | identik per kasus dengan referensi (28.2) |
| CP6 T3 Release Package | 36090518284 | `a095a9d` | `a095a9d` | capture: semua pin tereproduksi (`d61ef045…3b1b`); install 25 berkas, verifikasi AW..BA; advisor baru hanya 56 × INFO `rls_enabled_no_policy` erp; drill RESTORED_SAME_MEANING; primary tidak berubah; gate B2 lulus; browser AT/AU 10/10 PASS |
| CP6 T3 Rollback | 36089919551 / 36090518234 | `a4ad590` / `a095a9d` | sama | CAPTURED / siklus 127/127 PASS |
| CP6 Candidate CodeQL | 36090824553 | `d113bed` | `a095a9d` | actions, c-cpp, python, javascript-typescript: 0 hasil |
| CP6 Auditor Scenario | 36090909397 | `4c379bf` | `a095a9d` | RUN_COMPLETE; self-test SELFTEST_PASS |

Run merah putaran ini (disimpan, tidak dilabel ulang):
- BA probe 36089919585 (`a4ad590`): 38/39 sesuai rencana; kontrol baru INCOMPLETE karena memanggil fungsi internal
  dengan klaim owner (izin). Diperbaiki di `a095a9d` (diposting seperti tes lifecycle T2). Rencana tidak diubah.
- Auditor Scenario 36089919668, 36090518187, 36090821697: mode browser (lihat B4).
- CodeQL 36090056167 (`a4ad590`): python 1 hasil; diperbaiki di `d113bed`.
- BA probe 36089417556 (`35612d6`): gagal di langkah pemasangan runtime CI (infra), digantikan run di atas.
- T3 Release Package 36089417657 (`35612d6`): merah yang diharapkan karena paket masih memuat BA lama (capture
  mencetak `differ ["BA"]`); paket dibangun ulang dari pin run itu di `a4ad590`.

Bukti putaran ini: `docs/evidence/cp6-ba/native_t1_run36090518293_{before,after}.json`,
`docs/evidence/cp6-t2/run36089425974_ba_fix.json`, `docs/evidence/cp6-t2/run36089919596_ba_b5_b6.json`,
`docs/evidence/cp6-t3/run36090518284_package25_ba_fix.json`, `docs/evidence/cp6-t3/rollback_cycle_run36090518234.json`,
`docs/evidence/cp6-t3/codeql_run36090824553_round8.json`, `docs/evidence/cp6-auditor/run36090909397_samples.json`.

### 28.7 Batas yang diketahui (jujur)
- A4: material dengan beberapa penerimaan masih bisa menyisakan sampai 0,01 per penerimaan (pembulatan per dokumen
  penerimaan vs rata-rata riwayat). Grup potong multi-bahan memposting satu total yang dibulatkan; pembagian sen per bahan
  mengikuti pembulatan per bahan. Retur supplier mengikuti cent state v2.6.20n (28.2).
- B3: transaksi bisnis matriks post-use sama di setiap keluarga (saldo awal piutang), bukan transaksi khas keluarga.
  Deteksi post-use rollback membandingkan semua data erp, jadi transaksi apa pun yang dikomit menolak rollback.
- A7 dan A8 (opsional) belum dikerjakan.
- Penerimaan independen semua perbaikan di atas menunggu rerun auditor pada head baru.

### 28.8 Untuk auditor: head baru dan cara menjalankan ulang
- Head baru: commit yang memuat bagian ini (hash lengkap ada di pesan serah terima). Produk acuan:
  `a095a9d804d29643721e18635c2c3e26adcd56ea`. Setiap run mencetak `run_identity` (head alat dan produk acuan).
- Cabang kompetisi tetap `ca7f09556397801c50a2277bdb65b1bf019f9a05`. Tidak ada SQL ke hosted.
- Skenario yang terdampak, dijalankan ulang lewat Actions → CP6 Auditor Scenario → Run workflow → cabang
  `claude/new-session-deapao` → `scenario_b64` = base64 berkas skenario, `phase` = after:
  - A1: `open_1.py`, `open_2.py`, `xaudit_5.py` (R1), ditambah kasus positif sumber berbeda;
  - A3: `xaudit_1.py` U02, `stock_import_scenario.py` SI-02, ditambah kontrol tanggal ≥ pembalikan;
  - A4: `xaudit_1.py` U03, `xaudit_2.py` invoice, MONEY×4 (dua arah);
  - A5: `xaudit_2.py` selector-101, `import_selector_fable_fix.py`;
  - A6: `xaudit_5.py` R2 (tepat satu filing);
  - A9: `business_scenarios_reconstructed.py` DATED_CAPACITY ×3 dan ORDERED_CONTROL ×3; AUD-S04/B04;
  - A10: SI-01 dan kontrol positif;
  - B1: `rt_probe_1.py` / `rt_probe_2.py` (kasus bocor harus INCOMPLETE); job self-test di workflow yang sama
    menunjukkan detektornya.
- Fase: `after` = klon AN + AU, AV, AW, AX, AY, lalu AZ dan BA (kandidat sekarang); `pre_ba` = tanpa BA; `before` = tanpa
  AZ dan BA.
- B4: input `browser_b64` = base64 modul ES yang mengekspor `async function cases(ui, today)` →
  `[[id, async () => ({status, ...})], ...]`. `ui.login(role, {label, mobile, timezoneId})`, `ui.anonPage()`,
  `ui.anonRpc()`, `ui.sql()` (hanya salinan sekali pakai), `ui.expect`. Modul tidak perlu mengimpor paket; pakai
  `ui.expect`. Contoh: `scripts/cp6_auditor_browser_sample.mjs`.
- T2: Actions → CP6 T2 Combined Regression → Run workflow (hasil per ID dibandingkan dengan hasil beku; HOLD tetap).
- T3: CP6 T3 Release Package dan CP6 T3 Rollback (auto memilih `cycle`) pada head baru.
- Addendum C0: D01–D05 sudah disahkan tertulis owner (bagian 9, termasuk 3.4 dan 5.3; berkas sha256 `e83d56e6…0c99`,
  teks bagian 1–8 = versi `d39762da…926d`). Auditor diminta mencatat hash dan mencocokkan kutipannya. Yang tersisa:
  tinjauan auditor atas lampiran C6, lalu pengesahan D06 oleh owner.

## 29. Putaran kesembilan: tugas W1–W13 dari handoff auditor R9 (25 September 2026) (writer Claude)

Label run: T1_FAMILY, T2_REGRESSION, T3_PREP, dan AUDITOR_SCENARIO. Semuanya bukan bukti rilis dan bukan penerimaan
independen.

Status yang tidak berubah:
- CP6 tetap HOLD, `audit_complete=false`, `production_go=false`.
- 12 HOLD historis tetap HOLD. Hasil beku tidak dilabel ulang.
- Tidak ada SQL ke hosted. Cabang kompetisi tetap `ca7f095`.
- `main`, Cloudflare, Supabase hosted, dan ERP-Garment lama tidak disentuh.

Sumber tugas (dibaca saja): `WRITER_HANDOFF_R9_20260925.md` (commit `c95d6b9`) dan `AUDIT_WRITER_HANDOFF_CP6.md` (commit
`a96bcaa`), keduanya di cabang auditor `audit/cp6-final-20260924-gpt-a0bcadf`. Kandidat yang dinilai auditor: produk
`a095a9d`, alat `9dd7bc2`.

### 29.1 Produk

| Tugas | Temuan | Perbaikan | Commit | Bukti |
| --- | --- | --- | --- | --- |
| W8 (CP6-03 sisa) | Dua penerimaan @10,00 dikoreksi ke 10,005: WIP 20,01, bahan 0,01 pada qty 0 (GPT run 36097284096) | Di `erp.sync_material_cost_revaluation` (BA), setiap gerakan pemakaian membawa selisih antara nilai dokumen pembelian (dibulatkan per dokumen) dan nilai yang diambil rata-rata bergerak, untuk penerimaan sejak pemakaian sebelumnya. Nilai dokumen diambil dari `input_unit_cost` gerakan penerimaan (lihat catatan di bawah tabel) | `75df787`, `1a443d7` | Probe BA `A4:MULTI_CENT_{DIRECT,INVOICE}_{UP,DOWN}`: PASS dengan BA (run 36112108521 dan run final) |
| W9 (C0 D01 §3.4) | Laporan di tanggal yang sudah difiling menandai `changed_since_filing` hanya selama tanggal itu tidak READY. Setelah recost diproses, penanda kembali false, padahal gambaran yang difiling sudah dikoreksi | `erp.get_owner_financial_snapshot_v2` (BA) menandai bila tanggal tidak READY, atau bila ada jurnal koreksi yang dibuat sesudah filing (lihat catatan di bawah tabel) | `1a443d7`, `b6d81f9` | Probe BA `W9:CHANGED_SINCE_FILING_AFTER_PROCESSED_CORRECTION`: tanpa BA COUNTEREXAMPLE, dengan BA PASS. Kontrol `W9:FILED_DATE_WITHOUT_LATER_CORRECTION_CONTROL` PASS di kedua fase |
| LAU-T14 (ditemukan saat inventaris W1) | POST_RECEIPT (20ac:9154–9165) memakai tarif pada waktu penerimaan, sehingga versi tarif baru di antara kirim dan kembali mengubah biaya kiriman. Ini melanggar M:4474 (LAU-DEC03: jangan reprice menurut tanggal kembali) | `erp.save_laundry_qc_action_v1` (BA, dari 20ac): penerimaan memakai tarif proses aktual yang berlaku saat barang dikirim. Estimasi kirim dan attempt cuci gagal tetap memakai waktunya sendiri | `1a57266` | Probe BA `LAU_T14:RECEIPT_AFTER_A_LATER_RATE_VERSION`: tanpa BA 9,00 (COUNTEREXAMPLE), dengan BA 7,00 (PASS). Kontrol PASS di kedua fase (run 36112408914) |
| W13 (CP6-06) | KPI Laundry/QC tampil 0 saat baca awal gagal | `src/components/Cp6Kpi.tsx`: tampil "—, belum diketahui" selama workspace belum terbaca; 0 dari server tetap 0; banner dan kunci tulis tetap | `21acae1` | Tes DOM `Cp6Kpi.dom.test.tsx` |
| W10 (CP6-05) | Pola dan duplikasi Role membuat UUID baru pada klik ulang setelah balasan hilang | `src/lib/requestEnvelope.ts` (lihat catatan di bawah tabel) | `21acae1` | `requestEnvelope.test.ts` |
| W11 | Semua exception tampil sebagai "Layanan UAT belum dapat dihubungi" | `src/lib/clientError.ts`: hanya kegagalan tanpa jawaban server (TypeError/abort, status 0/502/503/504, kata jaringan tanpa kode) yang dianggap jaringan; penolakan parser atau server tampil dengan pesannya sendiri (kode `REJECTED`) | `21acae1` | `clientError.test.ts` |

**Catatan W8.**
- **Kenapa `input_unit_cost`.** Koreksi harga langsung menghitung ulang sebelum koreksinya berstatus POSTED. Pada saat
  itu `material_purchase_current_unit_cost` masih mengembalikan harga lama; varian DIRECT gagal karena ini di run
  36110211074.
- **Dokumen multi-bahan.** Sen tingkat dokumen dibebankan ke material dengan id terkecil.
- **Asal temuan (jujur).** Pada fase tanpa BA (AU..AZ), keempat kasus sudah PASS (run 36112408914). Contoh tandingan
  auditor berasal dari aturan sen A4 versi pertama BA (produk `a095a9d`), jadi ini regresi BA yang kini diperbaiki. Kasus
  probe menjadi kontrol regresi, dengan expected PASS di kedua fase (`f990c74`).

**Catatan W9.**
- **Aturannya.** Laporan menandai `changed_since_filing` bila ada jurnal koreksi dengan tanggal ekonomi ≤ tanggal
  laporan dan dibukukan sesudah periode yang difiling, yang dibuat sesudah filing.
- **Cara membedakan "sesudah filing".** `erp.close_accounting_through` (BA) mencatat di readiness filing daftar jurnal
  sejenis yang sudah ada saat filing (`booked_after_filed_period`). Filing tetap immutable. Filing sebelum BA dianggap
  daftarnya kosong.
- **Alasan daftar itu diperlukan.** Seed yang dijinakkan sudah punya akrual payroll bertanggal ekonomi 2026-02-01 yang
  dibukukan hari ini (run 36112108521). Selain itu, `posting_at` memakai `now()`, sehingga tidak bisa mengurutkan filing
  dan koreksi dalam satu transaksi.

**Catatan W10.**
- Amplop request (id, rpc, argumen, fingerprint) disimpan sebelum kirim.
- Klik ulang dengan perubahan yang sama mengirim ulang UUID dan argumen yang sama. Server `_idempotency_begin`
  mengembalikan hasil lama, jadi efeknya tetap satu.
- Perubahan lain menunggu. Tombol "Kirim ulang perubahan tertunda" tersedia.
- Nama RPC tetap literal di setiap call site.

**Lapisan BA sekarang.** BA menggantikan 10 fungsi:
- 8 sebelumnya;
- `erp.get_owner_financial_snapshot_v2(date,date,date)` untuk W9;
- `erp.save_laundry_qc_action_v1(text,jsonb,uuid,bigint)` untuk LAU-T14.

Registry lapisan mengikuti `scripts/cp6_ba_build.py` (`REPLACED`).

### 29.2 Alat

**W7 (`scripts/cp6_auditor_modes.py`).** Mode race dan HTTP sekarang memakai grup ketat mode savepoint:
- ID ganda menolak grup sebelum operasi apa pun.
- Hasil bukan dict, atau status di luar PASS/FAIL/COUNTEREXAMPLE/INCOMPLETE, menjadi INCOMPLETE. Nilai aslinya dicatat.
- Sesi yang tertinggal di salinan membuat kasus INCOMPLETE lalu diputus. Pool `authenticator` PostgREST dikecualikan di
  mode HTTP.
- Planned, final, dan missing dicetak.
- Bukti: skenario auditor `audit/scenarios/round8/gpt_tool_modes.py` pada `21acae1` (run 36109589498). Hasilnya
  `AUDITOR_RACES_AFTER` dan `AUDITOR_HTTP_AFTER` ditolak dengan `AUDITOR_DUPLICATE_CASE_IDS`, status run INCOMPLETE, dan
  job merah. Itu hasil yang diminta.

**W2 (`scripts/cp6_t2_regression.py`).** Oracle C0 auditor dijalankan sebagai grup `T2_C0_ORACLE`:
- Berkasnya `audit/scenarios/c0_round8/gpt_c0_oracles.py`, disalin byte demi byte ke `scripts/cp6_c0_oracles_auditor.py`
  dengan sha256 `7c2c19b6…6a7` dipin.
- Grup memakai runner ketat auditor (`cp6_auditor_runner.strict_group`), bukan grup T2 yang dijinakkan, jadi tidak ada
  quiet seed maupun completion payroll. Ini sama dengan run auditor 36098555186 dan 36099496005.
- Kasus ADJUSTMENT_DATE mendapat koreksi transport auditor (transport_rev2), yaitu hanya mengembalikan USAGE yang dicabut
  helper penerimaan.
- Selain 25 PASS, hasil apa pun menjadi DISPOSITION_REQUIRED.
- Assertion dan hasil beku 25 ID lama tidak disentuh. Fixture ADJUSTMENT_DATE dengan max(E, tanggal penyesuaian)
  (D01 §3.3) ada di grup ini dan di oracle B yang sudah disetujui owner.

**W4.**
- `cp6_auditor_runner.strict_group`: kasus yang meng-COMMIT atau me-rollback transaksi grup menjadi INCOMPLETE
  terstruktur (`AUDITOR_CASE_ENDED_GROUP_TRANSACTION`), grup berhenti, dan kasus berikutnya tercatat missing. Sebelumnya
  grup crash dengan `savepoint "auditor_case" does not exist`. Self-test runner mendapat kasus `ST:COMMITS`.
- Browser host mencatat tahap gagal (`failed_stage` START/CASES). Dengan begitu `users_created 0` terbaca sebagai
  "berhenti di START", bukan hasil kasus.

**W12 (b) dan W6 (`scripts/cp6_cutover_data_checks.py`).** Skrip ini hanya membaca (transaksi read only):
- **uuid_quality:** pola UUID frontend (`laundryQcModel.ts:123`) dicek terhadap setiap kolom uuid skema erp, ditambah
  default uuid non-v4.
- **cash_bank_aliases:** cash account aktif yang berbagi satu akun COA.
- Install T3 mencatat keduanya pada clone final. Di baseline hosted-faithful hasilnya CLEAN (765 kolom) dan NONE (run
  36112870391).
- Skrip yang sama dijalankan owner/operator pada salinan drill cutover data hosted/legacy:
  `python3 scripts/cp6_cutover_data_checks.py --pgurl …`. Hasil FOUND harus diselesaikan sebelum cutover.

### 29.3 Dokumen: W1, lampiran C6 rev2

`docs/contracts/ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25_LAMPIRAN_C6.md` (commit `d841cba`, sha256 `06b6b5e7…a566`):
- **Pemisahan baris:**
  - ACC-04 → 04a BASELINE / 04b CR-TUNDA.
  - LAU-05 → 05a BASELINE / 05b CR-TUNDA. 05b adalah perluasan M:3729–3737 yang sudah disetujui tetapi belum diterapkan.
  - LAU-06 → cuci ulang BASELINE / celup ulang CR-TUNDA.
- **Baris keputusan:** LAU-07 diganti LAU-DEC01–06. ACC-DEC01–07 dan ERP-DEC02 mendapat baris sendiri, masing-masing
  dengan keadaan kandidat dan hal yang ditahannya.
- **Inventaris sumber per fitur:** entrypoint publik, storage, UI, dan status, dengan kata kunci pencarian untuk yang
  ABSENT. Tidak ada CR-MASUK.
- **Temuan baseline:** LAU-T14, diperbaiki di BA.
- **Crosswalk 75 ID asli:** 36 LAU dan 39 ACC, semua UNVERIFIED dengan penunjuk ke bukti parsial.
- **Pilihan owner O2** per baris CR-TUNDA.

### 29.4 Tidak dikerjakan, dengan alasan

| Tugas | Alasan |
| --- | --- |
| W12 (a): seed uji ke UUID v4 | Id `a1000000…`/`a2000000…` dirujuk harness auditor yang dipin (`c6b0e4fb`, mis. `ATTENDANCE_CONTRACTOR`) dan 20+ fixture/SQL uji beku. Mengubahnya akan memindahkan hasil beku. Seed hanya dipakai DB uji sekali pakai. Data produksi dibuat dengan `gen_random_uuid()`, dan cek drill (b) memeriksa data nyata |
| W3: cabut grant `authenticated` di `erp.prepare_migration_opening_balance` | Opsional P3. Auditor sudah memastikan fungsi ini tidak terjangkau lewat HTTP publik (tanpa USAGE skema dan tanpa facade). Perubahan ACL di luar daftar fungsi BA butuh capsule rollback ACL tambahan. Ditunda ke successor, tidak diubah diam-diam |
| W5: pesan STALE_VERSION | Sesuai catatan auditor: produk tidak diubah hanya untuk pesan selama kandidat dibekukan. Penolakan race sudah aman (`POCKET_PERIOD_BUSY`) |
| W6: alias CASH_BANK | Identitas impor tetap per `cash_account_id` (BA A1). Pertanyaan alias nyata dijawab oleh cek drill `cash_bank_aliases` pada data hosted; writer tidak boleh membaca hosted |

### 29.5 Hasil CI

Semua run memakai CI sekali pakai.

**Produk acuan.**
- Terakhir berubah: dev BA `b6d81f9`, lalu paket T3 `1dcf21b` dan rollback `61d88ee`.
- Frontend: `21acae1`.
- Sesudah itu hanya alat (`f990c74`, harapan probe) dan bukti/dokumen yang berubah.

| Workflow | Run | Head | Hasil |
| --- | --- | --- | --- |
| CP6 BA T1 Family Probe | 36112965907 | `f990c74` (produk `b6d81f9`) | after 47/47 PASS; before 25 COUNTEREXAMPLE + 22 PASS sesuai rencana; tidak ada expectation mismatch; primary tidak berubah, clone terhapus |
| CP6 T2 Combined Regression | 36113586943 | `1dcf21b` | Identitas per kasus sama dengan referensi: business 230, imports 31, values 65 tanpa perpindahan. NEW_CASES hanya 9 perpindahan beku yang sudah tercatat: 8 DATE dengan oracle AS MATCH 8/8; `ADJUSTMENT_DATE:False` INCOMPLETE dengan oracle B MATCH. 12 HOLD identik. **Grup baru T2_C0_ORACLE 25/25 PASS.** AR, AT/AU, dan race hijau |
| CP6 T3 Release Package | 36113911869 | `61d88ee` | Install 25 berkas dan verifikasi AW..BA; advisor baru hanya 56 × INFO `rls_enabled_no_policy` erp; drill RESTORED_SAME_MEANING; cek data cutover CLEAN/NONE; gate true. Browser AT/AU 10/10 PASS, 0 console error. Capture mereproduksi pin yang dikomit (`15aa4a85…ff17`, equal) |
| CP6 T3 Rollback | 36113267241 / 36113867725 | `1dcf21b` / `61d88ee` | CAPTURED (`1f0a0fcc…b9fd`) / siklus 127/127 PASS, primary tidak berubah |
| CP6 Candidate CodeQL | 36113589299 | `1dcf21b` | actions, c-cpp, python, javascript-typescript: 0 hasil |
| CP6 Auditor Scenario | 36109589498 (dispatch `gpt_tool_modes.py`) / 36112965965 (push) | `21acae1` / `f990c74` | W7: grup race/HTTP ditolak (INCOMPLETE, merah sesuai harapan) / RUN_COMPLETE, self-test SELFTEST_PASS termasuk `ST:COMMITS` |

**Run merah putaran ini.** Semuanya disimpan dan tidak dilabel ulang.

*Probe BA:*
- **36110211074 (`75df787`):** DIRECT gagal (current_unit_cost basi saat koreksi). Diperbaiki di `1a443d7`.
- **36112108521 (`1a443d7`):** W9 INCOMPLETE (koreksi seed yang sudah dikenal filing). Diperbaiki di `b6d81f9`.
- **36112408914 (`1a57266`):** sama, ditambah fase before MULTI_CENT PASS, yang mengungkap asal regresi BA. Harapan dikoreksi di `f990c74`.
- **36112870435 (`b6d81f9`):** fase before masih berharapan lama. Fase after lulus penuh.

*Paket T3:*
- 36110211041, 36112409047, dan 36112870391: paket basi dengan sengaja (`differ ["BA"]`). 36112870391 adalah sumber pin.
- Capture 36113264960 membandingkan dengan pin lama yang dikomit; paketnya sendiri sudah benar.
- 36112966052 dibatalkan (paket basi).

*Rollback:* 36113264970 dibatalkan (cycle sebelum capture ulang).

**Bukti putaran ini.**
- `docs/evidence/cp6-ba/native_t1_run36112965907_{before,after}.json`
- `docs/evidence/cp6-t2/run36113586943_round9.json`
- `docs/evidence/cp6-t3/run36113911869_package25_round9.json`
- `docs/evidence/cp6-t3/rollback_cycle_run36113867725_round9.json`
- `docs/evidence/cp6-t3/codeql_run36113589299_round9.json`
- `docs/evidence/cp6-t3/release_pins.json`
- `docs/evidence/cp6-t3/rollback_capture.json`

### 29.6 ALL: jalur impor yang ada per keadaan (untuk `out/gpt_all_round8_binding.md`)

Inventaris ini hanya membaca, pada kandidat. Status bukan hasil uji: MAPPED berarti jalurnya ada, bukan berarti sudah PASS.

**Singkatan.**
- AP, AR, AS, AZ, BA = berkas paket `supabase/release/cp6-t3/*_20{ap,ar,as,az,ba}_*.sql`. AC = migration 20ac.
  BSR = migration 19 (CP5 BS resolution).
- FX = skema baseline.
- OBI = entitas OPENING_BALANCE_ITEM.

**Jalur impor.** Semuanya lewat `public.erp_save_initial_import_action_v1` (AP:1705) → `erp.save_initial_import_action_v1`
(AR:504):
1. SAVE_FILE per entitas (AR:575–617).
2. FINALIZE (AR:629–642), yang berurutan menjalankan:
   - master;
   - `apply_migration_open_pos`;
   - `prepare_migration_opening_balance`;
   - `post_opening_balance` (BA);
   - `apply_initial_import_receipts_v1`;
   - `apply_initial_prepayments_v1`;
   - `finalize_migration_batch`.

**OSS (settlement saldo awal).** Baris DRAFT di `erp.opening_subledger_settlements`, lalu
`erp.post_opening_subledger_settlement` (AP:4655–4671); pembaliknya di AP:5321. Belum ada facade publik maupun UI untuk
ini.

| Keadaan | Status | Jalur impor | Lanjutan sesudah impor | Yang belum ada |
| --- | --- | --- | --- | --- |
| P01 diterima belum ditagih, sebagian terpakai | MAPPED | UNINVOICED_RECEIPT + stok sisa (MATERIAL_ROLL/OBI MATERIAL, `opening_source_key`) + OPENING_COST_ORIGIN untuk yang terpakai | invoice supplier (`save_material_supplier_invoice_draft_v2` AC:10194, `post_material_supplier_invoice_v2`) → recost origin (AP:6421); bayar `post_supplier_payment` atau APPLY uang muka | Qty terima wajib = sisa + terpakai (AP:4407–4413) |
| P02 hutang supplier sebagian dibayar | MAPPED | OBI SUPPLIER_PAYABLE (dokumen, nilai asli, `settled_before_cutover`) | OSS cabang supplier; APPLY uang muka supplier ke target OPENING | Tidak ada invoice native, jadi tidak ada retur/match ke invoice lama |
| P03 terima sebagian ditagih | PARTIAL | dua baris: SUPPLIER_PAYABLE (bagian tertagih) + UNINVOICED_RECEIPT (qty belum tertagih) | seperti P01 + P02 | Satu identitas penerimaan untuk kedua bagian; qty tertagih tidak tersimpan di penerimaan |
| P04 PO belum diterima / draf pengadaan | NO_ADAPTER | — | — | Impor hanya menulis penerimaan POSTED (AP:4544). Dicari: purchase order, PURCHASE_ORDER, OPEN_PURCHASE, header DRAFT |
| S01 invoice penjualan lama belum lunas | MAPPED | OBI CUSTOMER_RECEIVABLE (dokumen) | OSS cabang AR; APPLY uang muka pelanggan ke OPENING | Tidak ada `sales_headers`, jadi tidak ada retur/nota kredit ke invoice lama |
| S02 draf penjualan dengan reservasi | NO_ADAPTER | — (stok FG bisa diimpor, reservasi tidak) | — | Dicari: sales_headers, save_sale_draft_v2, reserve |
| S03 retur/kredit/refund pelanggan terbuka | PARTIAL | kredit pelanggan sebagai OPENING_ADVANCE CUSTOMER | PREPAYMENT APPLY/REFUND (BA) | Retur fisik penjualan lama (`sales_returns` tidak ditulis). Apakah uang muka sah sebagai pengganti nota kredit adalah pertanyaan kontrak |
| Y01 upah/reimburse mandor diakui belum dibayar | MAPPED | OBI CONTRACTOR_PAYABLE | OSS, tunai saja | Tidak bisa dinetting di payroll (payroll hanya menaut CASH_ADVANCE, AP:192–195) |
| Y02 jahit/absensi belum disetujui, carry komponen, reimburse belum dialokasi | NO_ADAPTER | — | — | Impor tidak menulis `payroll_work_items`, absensi, `sewing_terminal_events`, entitlement reimburse; dok impor melarang mengarang histori (`docs/cp6-initial-import-progress.md:166`) |
| A01 uang muka supplier/pelanggan/vendor laundry | MAPPED | OPENING_ADVANCE (SUPPLIER/CUSTOMER/VENDOR) | aksi PREPAYMENT → `manage_initial_prepayment_v1` (BA): APPLY/REVERSE_PAYMENT/REFUND/CORRECT/REVERSE_EVENT | — |
| A02 kasbon mandor dipotong payroll | MAPPED | OBI CONTRACTOR_RECEIVABLE + `source_kind` CONTRACTOR_CASH_ADVANCE | ALLOCATE_CASH_ADVANCE → `set_opening_cash_advance_payroll_v1` (AP:4936) → potongan payroll; bayar `post_payroll_payment`; tunai lewat OSS | — |
| A03 settlement historis / dokumen habis | PARTIAL | agregat `settled_before_cutover` pada OBI keuangan dan OPENING_ADVANCE | tidak perlu (hanya histori) | Dokumen yang sudah lunas penuh ditolak (sisa harus >0); pembayaran historis per transaksi tidak disimpan |
| W01 header PO terbuka | MAPPED | OPEN_PO → `apply_migration_open_pos` (AC:2108) | alur produksi native; guard selesai/batal (AP:6510–6520) | Prasyarat pola/BOM/potong tidak diimpor (belum ditelusuri penuh, UNSURE) |
| W02 WIP fisik SEWING/LAUNDRY | PARTIAL | OBI WIP (PO, ukuran, tahap, pemegang, `source key`, `accessory_cost_included`) | WIP_OUTPUT → `complete_initial_import_wip_v1` (BA): COMPLETE ke FG QC_GOOD / REVERSE | Memindah WIP SEWING pembuka ke laundry, BS dari WIP pembuka, upah sesudah cutover |
| W03 BS bernilai | MAPPED | OBI BS (PO, SKU, ukuran, tahap termasuk QC, pemegang) → `bs_cases` LEGACY | `erp_save_bs_resolution_action_v1` (BSR:1127): CLASSIFY/REWORK/DISPOSE/HOLD/CLAIM | BS tanpa PO bernilai 0 (AP:2342) |
| W04 potongan menunggu pickup | NO_ADAPTER | — (OPEN_PO tahap CUTTING hanya header) | — | Dicari: cutting_groups, cutting_pickups, CUTTING |
| W05 laundry di luar, cuci gagal, klaim, invoice lama | PARTIAL | WIP tahap LAUNDRY + vendor; OBI VENDOR_PAYABLE; OPENING_ADVANCE VENDOR | WIP_OUTPUT; OSS AP vendor; APPLY ke invoice vendor | Attempt gagal, klaim pending, penerimaan belum tertagih (tidak ada delivery/receipt/claim laundry yang ditulis). SAVE_CLAIM pada BS pembuka: UNSURE |
| W06 rework terkirim/sebagian/komponen belum dibayar | NO_ADAPTER | — (proksi: impor BS lalu rework baru; komponen sebagai CONTRACTOR_PAYABLE gabungan) | — | Dicari: rework_orders, rework_component_lines |
| C01 aksesori/kain kantong perusahaan | MAPPED | OBI MATERIAL (aksesori); MATERIAL_ROLL (kain kantong) | `erp_save_accessory_issue_action_v1`; `erp_save_pocket_fabric_action_v1` REGISTER/POST | — |
| C02 nota aksesori mandor sebelum cutover | PARTIAL | hutang sebagai OBI CONTRACTOR_RECEIVABLE (BALANCE) atau CASH_ADVANCE bila dipotong payroll | BALANCE: OSS tunai; CASH_ADVANCE: payroll | Identitas nota aksesori; retur aksesori tak terpakai ke nota lama |
| C03 titipan/karantina/pemulihan aksesori | NO_ADAPTER | — (proksi: OBI MATERIAL di lokasi mana pun, tercatat stok perusahaan) | — | Dicari: custody, quarantine, karantina, titipan, recovered |
| C04 kain kantong sudah ditarik / periode alokasi terbuka | NO_ADAPTER | — | — | `pocket_fabric_usage` dan periode tidak ditulis impor |

Ringkasan:
- **MAPPED 9:** P01, P02, S01, Y01, A01, A02, W01, W03, C01.
- **PARTIAL 6:** P03, S03, A03, W02, W05, C02.
- **NO_ADAPTER 7:** P04, S02, Y02, W04, W06, C03, C04.

Catatan:
- Aksi impor yang diterima (AR:519): CREATE, SAVE_FILE, VALIDATE, FINALIZE, ALLOCATE_CASH_ADVANCE, PREPAYMENT, dan
  WIP_OUTPUT.
- Entitas SAVE_FILE:
  - master: LAUNDRY_VENDOR, LOCATION, CHART_ACCOUNT, CASH_ACCOUNT, BRAND, SIZE, MODEL, PRODUCT, CUSTOMER, SUPPLIER,
    CONTRACTOR, ACCESSORY_CATEGORY, MATERIAL;
  - pembuka: MATERIAL_ROLL, OPENING_BALANCE_ITEM, OPEN_PO, UNINVOICED_RECEIPT, OPENING_ADVANCE, OPENING_COST_ORIGIN.
- OPENING_CONTROL hanya dicek terhadap baris detail, tidak pernah diposting.
- Workspace impor hanya menampilkan penerimaan belum tertagih, kasbon, payroll uang muka, uang muka, dan sumber produksi.
  Saldo AR/AP pembuka biasa belum punya lanjutan di UI (OSS tanpa facade).
- Kontrak (M:369–379, M:930–938) melarang mengarang histori lama demi adapter. Keadaan NO_ADAPTER adalah celah bukti atau
  celah adapter, bukan bukti fitur global tidak ada.
- **Pertanyaan scope ALL untuk owner ada di 29.8.**

### 29.7 Untuk auditor: head baru dan cara menjalankan ulang

**Identitas.**
- Head baru: commit yang memuat bagian ini (hash lengkap ada di pesan serah terima).
- Produk acuan: dev BA `b6d81f9`, paket T3 `1dcf21b`, rollback `61d88ee`, frontend `21acae1`.
- Setiap run mencetak `run_identity`.
- Cabang kompetisi tetap `ca7f095`. Tidak ada SQL ke hosted.

**Skenario auditor** (`cp6-auditor-scenario.yml`, phase=after, `scenario_b64` = berkas dari `audit/scenarios/`):

| Tugas | Skenario | Yang diharapkan |
| --- | --- | --- |
| W8 | `round8/gpt_round8.py`, empat kasus `G8:MULTI_CENT_*` | UP: WIP 20,02 dan bahan 0. DOWN: WIP 20,00 dan bahan 0. Kasus satu penerimaan tetap PASS |
| W7 | `round8/gpt_tool_modes.py` | Grup race/HTTP ditolak (sudah terlihat di run 36109589498) |
| W10 | `recovery_round8/gpt_recovery_browser.mjs` (input `browser_b64`) | Klik ulang setelah balasan hilang mengirim UUID dan payload yang sama, satu efek, tanpa 409 karena request baru |
| W13 | `unknown_round8/gpt_unknown_browser_rev6.mjs` + setup rev6 | KPI awal "—, belum diketahui", bukan 0. Kontrol sehat 20/10 tetap |
| W11 | Browser dengan input tidak valid | Pesan parser tampil apa adanya |
| W9 | Kasus AO tertutup C0 | Sesudah koreksi diproses, `changed_since_filing=true`; filing dan nilai hari yang difiling tidak berubah |
| LAU-T14 | Ditulis auditor | Tarif naik di antara kirim dan terima; biaya aktual tetap tarif saat kirim |

**Alat.**
- **T2:** dispatch CP6 T2 Combined Regression. Grup `T2_C0_ORACLE` ikut berjalan, bersama identitas per ID.
- **T3:** CP6 T3 Release Package (tiga job) dan CP6 T3 Rollback (auto = cycle).
- **Drill cutover (W12/W6):** `python3 scripts/cp6_cutover_data_checks.py --pgurl <salinan drill>` hanya membaca. Writer
  tidak menjalankannya pada data hosted.

### 29.8 Yang masih terbuka dan pertanyaan owner

**Pertanyaan owner:**
- **O2 (D06).** Sahkan lampiran C6 rev2 sesudah auditor mencocokkannya. Termasuk pilihan per CR-TUNDA (tabel bagian 7
  lampiran): ACC-04b, LAU-05b, dan LAU-06b, masing-masing successor sebelum consumer CP7 atau masuk kandidat final CP6.
- **ALL scope (bagian 29.6).** Semua 22 keadaan harus dibuktikan sebelum go, atau cukup keadaan yang benar-benar ada di
  data cutover? Bila opsi kedua, owner atau operator menyebut keadaan yang ada, dan drill cutover menjadi buktinya. Tujuh
  keadaan NO_ADAPTER dan enam PARTIAL di 29.6 menentukan besar pekerjaannya.

**Sisa audit (tidak ada indikasi cacat, yang belum ada adalah buktinya):**
- 75 kasus C6 (menunggu O2);
- matriks izin/lokasi penuh;
- payroll/BS/settlement lengkap;
- data hosted/legacy lewat drill.

**Status.** CP6 tetap HOLD, `audit_complete=false`, `production_go=false`.

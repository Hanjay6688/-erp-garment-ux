# Laporan Fable v1.1 — putaran silang 1 CP7, kandidat `ae0214ad`

**Status:** v1.1 FINAL (13 Okt 2026, 16:05 UTC). Review sumber dan 9 run independen selesai, semua dibaca per kasus (25 job, 22 di antaranya dengan baris kasus: 478 baris, 477 PASS, 1 COUNTEREXAMPLE milik kasus Fable baru, 0 FAIL, 0 INCOMPLETE, 0 pengulangan hari bisnis). Register run: `runs/xc1_ae0214ad/`.
Laporan ini melanjutkan `AUDIT_FABLE_7a0b4a90_RETEST.md` v1.0.1 (LULUS DENGAN SYARAT) dan menjawab butir A1–A9 dari
`docs/cp7/audit-candidate/crosscheck-r1-20261013/HANDOFF_FABLE.md`. Cakupan CP7 saja. Keputusan owner yang sudah
disahkan tidak dibuka ulang. `production_go:false`.

| | |
|---|---|
| Kandidat | `ae0214ad33184f7c2724783d663fb20fcb13820c`, tree `0217f5f6740f28c19b7894fcb0181f39d3aea727` (diperiksa sendiri: `git cat-file -t` commit, `rev-parse ^{tree}` sama) |
| Kode produk | identik dengan `7a0b4a90`: `git diff --name-only 7a0b4a90 ae0214ad -- supabase src scripts/cp7-src` kosong (diperiksa sendiri, 0 baris) |
| Berubah di luar `docs/` | 12 berkas, sama dengan daftar README penulis (diperiksa sendiri dengan `git diff --name-status`); semuanya dibaca baris per baris (§A8) |
| Head cabang saat uji | `856833dc`. Selisih `ae0214ad..856833dc` di luar `docs/`: hanya berkas backup/restore CP7C (`cp7_offsite_backup*.py`, `cp7_supabase_restore_drill.py`, `ops/backup-repo/*`, 4 workflow backup) yang **tidak dipakai** workflow kualifikasi mana pun yang saya dispatch. Workflow dan skrip yang dipakai run penulis di bawah identik dengan `ae0214ad` (diff kosong). Run Fable sendiri checkout `product_ref=ae0214ad` persis (assert HEAD + tree). |
| Register | `OWNER_DECISIONS_TO_AUDITOR_20261013.md`; keputusan owner D13-4..D13-9 dibaca dari `docs/cp7/OWNER_DECISIONS_20261008.md` di cabang penulis (A9) |

Label bukti: FABLE = oracle dan eksekusi Fable; INDEPENDENT_NATIVE_RERUN = oracle penulis/Astra, dispatch dan pembacaan
per kasus oleh Fable (dari log JSON, bukan warna job); INDEPENDENT_SOURCE_REVIEW = diff dibaca Fable;
WRITER_CROSSCHECK = bukti CI penulis, dikutip tanpa diklaim.

## A1 — ASR-OPS-01 (silang dari Astra; keluarga F-OPS-01)

### A1.1 Review sumber `scripts/cp7_nightly_backup.py` @ `85e17168` (INDEPENDENT_SOURCE_REVIEW)

| Bagian | Yang terbaca | Penilaian |
|---|---|---|
| `create_attempt` | `CREATE DATABASE <scratch>_<16 hex acak> OID <acak 1e9..4e9> TEMPLATE template0`; OID dicek bebas dulu; 8 percobaan; tidak pernah drop dulu. | Identitas database ditentukan alat sebelum pihak lain bisa menyentuhnya. Butuh PostgreSQL ≥ 15 (klausa `OID`). Di CI terbukti jalan sebagai peran `postgres` stack Supabase lokal. |
| `is_mark` / `mark_scratch` | Tanda percobaan = teks tanda + `attempt=<token> oid=<oid>`; hanya dihitung milik alat pada database yang OID-nya sama dengan yang tertulis. Tanda **polos** (tanpa token/OID, versi lama) masih dihitung milik alat pada nama `--scratch`. | Tanda yang disalin ke database lain tidak berlaku di sana (OID beda). **Tanda polos tetap bisa disalin** → §A1.3 temuan baru F-OPS-05. |
| `drop_owned` | Hanya lewat OID: baca nama saat ini, cek tanda (atau `created_here` tanpa komentar), akhiri sesi pada OID itu, `ALTER DATABASE RENAME` ke nama acak, cek lagi OID di nama baru, baru `DROP ... WITH (FORCE)`. Kalau nama ternyata milik database lain: dikembalikan, hasil `REPLACED`. | Tidak ada jalur hapus berdasarkan nama. Jalur `finally` lama (boolean `ours`) hilang; `finally` hanya `drop_owned(attempt_oid, token, created_here=True)`. Catatan kecil: database asing yang kebetulan memegang nama itu bisa **di-rename bolak-balik** dalam hitungan milidetik (koneksi baru ke nama itu gagal sesaat); tidak ada yang dihapus. Observasi, bukan temuan. |
| `leftovers` + `backup()` | Sisa malam lalu (nama `--scratch` atau `<scratch>_<hex>` bertanda) dibaca **dengan OID sebelum dump**, dihapus lewat OID yang sama sesudah dump; hasil selain DROPPED/ABSENT → `BACKUP_SCRATCH_REPLACED`, tidak ada verifikasi/pemangkasan. Nama `--scratch` wajib kosong sebelum `create_attempt`; kalau terisi → `REPLACED`/`NOT_CREATED`. | Urutan ASR-OPS-01 tertutup di sumber. |
| Restore & hash | OID database percobaan dicek sebelum dan sesudah `pg_restore`; koneksi hash memeriksa `oid` database tempat ia tersambung (`expected_oid`). | Hash tidak pernah dibaca dari database pengganti. |
| `Tools.drop` / `Tools.create` | **Dihapus.** `dropdb`/`createdb` tidak ada lagi di berkas. | Diverifikasi saat runtime oleh kasus Fable `XC1:NO_NAME_BASED_DROP_OR_CREATE_IN_TOOL`: PASS (sha256 berkas `f9e4235e…`, 0 kemunculan `dropdb`, satu-satunya `drop database` ada di `drop_owned`). |

Kesimpulan sumber: keluarga F-OPS-01 (hapus database yang bukan milik alat) **tertutup tanpa jalur hapus baru**, dengan
satu sisa yang bukan baru: tanda polos (§A1.3).

Catatan lingkungan (dari kasus Fable): di cluster CI peran yang dipakai alat adalah `supabase_admin` (superuser) pada
PostgreSQL 17.6. Klausa `CREATE DATABASE ... OID` tidak mensyaratkan superuser untuk OID ≥ 16384 menurut dokumentasi
PostgreSQL, tetapi menjalankannya sebagai peran `postgres` non-superuser di hosted **belum dibuktikan di sini**. Ini tidak
relevan bila verifikasi restore berjalan di mesin GitHub (D13-6/D13-8b), dan wajib diperiksa bila owner nanti memilih
verifikasi di server database.

### A1.2 Run (semua pada `product_ref=ae0214ad`, alat backup `85e17168`)

| Kasus | Oracle | Run / job | Hasil |
|---|---|---|---|
| FABLE_CORE:BACKUP_SCRATCH_DROPS_FOREIGN_DB (tidak diubah) | FABLE | 38414828309 / 115356368140 | **PASS** (database asing tetap ada; `BACKUP_SCRATCH_EXISTS_NOT_OURS`) |
| FABLE_CORE:BACKUP_VERIFY_UNDER_LIVE_WRITES (tidak diubah) | FABLE | 38414828309 / 115356368140 | **PASS** (`restore_verified=true` di bawah tulisan K4 heartbeat) |
| XC1:LEFTOVER_REPLACED_AFTER_DUMP_KEPT (urutan Astra, kanari Fable) | FABLE (baru) | 38414814884 / 115356320136 | **PASS**: sisa bertanda dibaca OURS, diganti database asing sesudah dump → asing **tetap ada** (kanari `FOREIGN_AFTER_DUMP`, tanpa tanda, 0 tabel restore), `restore_verified=false`, error `BACKUP_SCRATCH_REPLACED`, tidak ada database percobaan tersisa |
| XC1:ATTEMPT_SWAPPED_BEFORE_RESTORE_KEPT (batas operasional penulis) | FABLE (baru) | 38414814884 / 115356320136 | **PASS** terhadap oracle Fable (asing tidak dihapus; malam tidak terverifikasi), dan **batas operasional terkonfirmasi persis seperti dinyatakan**: database pengganti menerima 559 tabel hasil restore; database milik percobaan dihapus lewat OID di nama barunya (`DROPPED`, oid 3951292058); error `BACKUP_SCRATCH_REPLACED after restore` |
| XC1:COPIED_OID_MARK_ON_FOREIGN_KEPT | FABLE (baru) | 38414814884 / 115356320136 | **PASS**: database berpola `<scratch>_<hex>` tanpa tanda dan dengan tanda yang menyebut OID lain **tetap ada**; malam terverifikasi; `leftovers: []` |
| XC1:PLAIN_MARK_COPIED_ONTO_FOREIGN | FABLE (baru) | 38414814884 / 115356320136 | **COUNTEREXAMPLE** (→ F-OPS-05): database asing bernama `--scratch` yang komentarnya salinan tanda polos dibaca OURS, dicatat sebagai sisa, dan **dihapus** (`leftovers[0].result=DROPPED`, oid 69419); malam itu terverifikasi. Job merah hanya karena kasus ini (driver Fable), bukan alat. |
| K3C_RACE_BACKUP_SCRATCH_OWNERSHIP_BY_OID + 4 kasus backup K3 (`k3-cleanup-24`) | INDEPENDENT_NATIVE_RERUN | 38414371682 / 115354760145 | **24/24 PASS** (9 native, 11 balapan, 2 HTTP, 2 browser). Situasi A–D semua sesuai klaim penulis (A: pengganti tetap, `REPLACED`; B: pengganti tetap, milik sendiri di-drop lewat OID; C: terverifikasi, pengganti tetap; D: hanya yang bertanda OID sendiri dihapus). `NEVER_DROPS_ANOTHER_DATABASE`, `VERIFIED_UNDER_WRITES` (377 baris, 560 tabel), `NIGHTLY_BACKUP_VERIFIED` (559 tabel), `RETRY_SAME_SECOND` PASS. |

### A1.3 Penilaian batas operasional (ditulis terpisah, sesuai permintaan)

Batas yang dinyatakan penulis: admin database yang sengaja mengganti database percobaan (nama acak 16 hex) **tepat di
antara** cek OID dan saat `pg_restore` tersambung bisa menerima tabel hasil restore di database penggantinya; tidak ada
yang dihapus, malam dicatat tidak terverifikasi.

Penilaian Fable:
1. **Dampak nyata kecil dan tidak merusak.** Pelakunya harus admin cluster yang sama, yang memang sudah bisa membaca
   sumber secara langsung; data tidak hilang, dan malam itu tidak dilaporkan sukses. Yang hilang hanya satu malam
   verifikasi, yang terlihat di tanda terima.
2. **Batas ini hilang sendiri dengan keputusan owner D13-6/D13-8b** (pemeriksaan pemulihan di mesin GitHub, database
   sementara di runner). Di sana tidak ada admin lain, jadi balapan ini tidak mungkin. Rekomendasi: **terima batas ini**
   sebagai catatan, dan jangan memasang verifikasi restore di server database yang dipakai orang lain. Owner yang
   memutuskan; ini bukan dianggap disetujui.
3. **Temuan baru F-OPS-05 (minor, bukan pembuka ulang A1):** tanda polos versi lama masih dihormati pada nama
   `--scratch`. Database asing yang komentarnya **disalin** dari teks tanda itu akan dibaca sebagai sisa milik alat dan
   dihapus lewat OID-nya. Ini kelas yang sama dengan "admin sengaja" di atas (perlu penyalinan tanda yang disengaja),
   bukan kecelakaan. Karena belum pernah ada malam backup di luar CI, kompatibilitas tanda polos tidak melindungi apa
   pun. Rekomendasi: hapus penerimaan tanda polos; hanya tanda ber-OID yang dihitung milik alat. Bukti runtime:
   `XC1:PLAIN_MARK_COPIED_ONTO_FOREIGN` COUNTEREXAMPLE (run 38414814884, job 115356320136). Bobot: **minor**;
   tidak membuka ulang penutupan A1/F-OPS-01 karena membutuhkan penyalinan tanda yang disengaja oleh admin, kelas
   yang sama dengan batas operasional di atas.

## A2 — Selisih akhir grup `CP7 Supplier Payment Create` (syarat §3.1 Fable)

Dinilai dengan tabel bentuk bukti di register (`OWNER_DECISIONS_TO_AUDITOR_20261013.md`).

| Bentuk bukti yang diminta | Yang diberikan penulis | Penilaian Fable |
|---|---|---|
| Diff pencatatan selisih tidak mengubah hasil pembanding | `cp6_auditor_runner.py` @ `5b8e9d74`+`5e96cbcf`: tiga persamaan pembanding **tidak berubah** (`boundary_after==before`, `public_after==public_before`, `boundary_end==initial and public_end==public_initial`). Tambahan hanya: `state_difference` (fungsi murni tanpa akses database, di `cp6_auditor_difference.py`, 5 uji unit), `catalog_observation` (EXPLAIN + `pg_stat_sys_tables`, di savepoint sendiri, dibaca **sesudah** snapshot awal dan **sesudah** pembanding akhir), dan baris log `group_end_difference` hanya bila gagal. | **Diterima.** Pencatatan menambah detail, tidak mengubah keputusan. Saya cek `state_difference` membedakan ORDER_ONLY vs CONTENT dan menyebut anggota pertama yang bergeser; cocok untuk hipotesis CAT-01. |
| ≥ 3 run pada tree yang sama, SHA/tree, semua hasil termasuk gagal | 3 run @ `5b8e9d74` (tree `793863ec`) + 6 run @ `9e33fdab` (`7129bd37`) + 1 run di kandidat (38378246722): **semua 10/10 PASS, akhir grup sama**. Dua kegagalan lama (38288829388, 38330557862) dicatat apa adanya dengan log gagal pertama. 60 grup ulang alat diagnosis: 60 sama, 0 perubahan urutan, 0 baris berpindah, `autoanalyze` 2× tanpa efek. | **Diterima sebagai pekerjaan yang diminta owner.** Bundel produk sama di semua run (`source_sha256 d64ae6ed…`). |
| Akar penyebab | **Tidak ditemukan.** Penulis tidak menebak. Kecepatan mesin belum disingkirkan (kedua kegagalan di mesin cepat 8,4–8,5 s; mesin cepat lain lulus). Pesan commit `71594a0b` yang menulis "ruled out" diakui salah dan dokumen dibetulkan (riwayat tidak ditulis ulang). | **MASIH TERBUKA (OPEN)**, sesuai arahan owner. Penulis benar tidak menyebut "flake". |
| Run independen Fable dengan diagnosis terpasang | 3 × `claude-supplier-payment-create` pada tools `ae0214ad` (head `856833dc`, berkas identik): run 38414385732 job 115354813981, run 38414401092 job 115354861401, run 38414415980 job 115354912368 | **10/10 PASS di ketiganya** (4 native, 3 balapan, 1 HTTP, 2 browser), label grup PASS, `cp6_restored`, tidak ada baris `group_end_difference`. Kegagalan tidak terulang (INDEPENDENT_NATIVE_RERUN). |

Catatan auditor (bukan temuan): hipotesis yang masih paling masuk akal adalah CAT-01 (daftar fungsi `public` di
`PUBLIC_STATE` memakai `jsonb_agg(... order by 1)` dengan `1` sebagai konstanta, sehingga urutannya mengikuti urutan
fisik `pg_proc`). Belum ada bukti, dan 63 grup tidak pernah menunjukkannya. Dengan diagnosis terpasang, kegagalan
berikutnya akan langsung menjawab apakah itu ORDER_ONLY. Mengganti pembanding grup ini ke `exact_public_catalog`
(daftar diurutkan, tiap anggota dan hash tetap dibandingkan) menurut saya **bukan pelonggaran** oracle, melainkan
pembanding yang sama kuatnya tanpa ketergantungan pada urutan fisik; tetapi tanpa bukti bahwa urutan adalah
penyebabnya, perubahan itu juga tidak terbukti menutup apa pun. Rekomendasi: biarkan OPEN dengan diagnosis terpasang;
izinkan penulis **menambah** (bukan mengganti) pembanding terurut di grup ini supaya kegagalan berikutnya langsung
terklasifikasi.

## A3 — Gladi jadwal (syarat §3.2c Fable)

| Bentuk bukti yang diminta | Yang diberikan | Penilaian |
|---|---|---|
| run id, log install di salinan | run 38355904844 job 115158614355 (`k3-cleanup-23` @ `a09b6922`), kasus `K3C_RACE_SCHEDULE_INSTALLER_REHEARSAL`; log 08 dibaca per kasus | ada |
| `schedules()` vs deklarasi K3 | `defs == declaration['schedules'] == SCHEDULES` di kode kasus; 4 baris `cron.job` (nama, jadwal, perintah, database, pengguna, aktif) sama persis dengan deklarasi; `verify` → `matches: true` | **sama** |
| `cron.job` sebelum/sesudah | 0 → 4 (id 14–17, pasang ulang id sama) → 0; `cron.job_run_details` sejak pemasangan kosong (tidak ada job yang sempat jalan: dipasang di detik 3–35 dan dilepas beberapa detik kemudian) | **pulih persis** |
| uninstall `--removal-approved`; penolakan tanpa izin | `CP7_SCHEDULE_INSTALL_NOT_APPROVED`, `CP7_SCHEDULE_DATABASE_MISMATCH`, `CP7_SCHEDULE_UNINSTALL_NOT_APPROVED` semua ditolak tanpa mengubah `cron.job` | ada |
| tidak ada koneksi hosted | kasus menolak host selain `127.0.0.1`/`localhost`/soket (`K3C_REHEARSAL_DISPOSABLE_ONLY`); pemasang dijalankan sebagai proses terpisah `scripts/cp7_schedule.py` dengan jadwal asli (tanpa `TEST_SCHEDULE_OVERRIDE`) | ada |
| data salinan utuh | 559 tabel sama sebelum/sesudah | ada |
| backup 01:00 WIB | deklarasi K3 = `nightly.SCHEDULE` = `0 18 * * *` UTC; baris jadwal di `cp7-nightly-backup.yml` masih dikomentari (workflow nonaktif) | ada |
| Run independen Fable | `k3-cleanup-24` di 38414371682 / 115354760145, kasus `K3C_RACE_SCHEDULE_INSTALLER_REHEARSAL` | **PASS**: penolakan 3 jenis tanpa mengubah `cron.job`; 4 job terpasang (`*/5`, `30 19` = 02:30 WIB, `* * * * *`, `*/10`) di `cp6_auditor_race` sebagai `postgres`; pasang ulang id sama; `verify matches=true`; dilepas semua; `cron.job` 0 → 4 → 0; 0 job sempat jalan; data salinan sama. **DITUTUP.** |

Catatan: di Supabase hosted, database pg_cron dan database aplikasi sama-sama `postgres`, jadi nama job menjadi
`nama@postgres`; gladi ini memakai `cp6_auditor_race` + `postgres`, sehingga kombinasi "satu nama untuk keduanya" belum
tergladi. Bukan temuan; dicatat untuk daftar periksa pemasangan (CP7C).

## A5 — PR44

`scripts/cp7-src/` identik antara `7a0b4a90` dan `ae0214ad` (diff kosong, diperiksa sendiri), dan
`scripts/cp7_astra_timeline_reuse_probe.mjs` tidak termasuk 12 berkas yang berubah. **Penerimaan Fable atas area PR44
(retest §2.3) berlaku untuk `ae0214ad`.** Regresi netting dijalankan ulang juga: `pl-native/netting` run 38414446165 job 115355020037 **83/83 PASS** (60 native, 11 balapan, 6 HTTP, 6 browser). DITUTUP.

## A6 — Pensiun `SALES_MANUAL_13` (desktop & HP) dan PRE-05: cakupan pengganti

Dibaca: `docs/cp7/RETIRED_CP6_SALES_MANUAL_13.md`, kasus lama `scripts/cp6_bf_browser.mjs::salesManual`, pengganti
`tests/cp7/SalesPages.dozenHelper.dom.test.tsx`, `src/SalesDraftPanel.dom.test.tsx` (helper P11 di jsdom),
`scripts/cp7_p11_drafts_browser.mjs` (browser P11, `manual13_preserved`), `src/App.tsx` (mode tersambung membuka
`ConnectedSalesPage`, layar simulasi tidak tampil). Uji layar dijalankan di `CP7 Shell S0` yang saya dispatch
(run 38414431084, job 115354965906): `tests/cp7/SalesPages.dozenHelper.dom.test.tsx` **✓ 1 test**, total vitest 203 berkas / 1.727 tes PASS; uji unit `state_difference` 5/5 OK.

**Pernyataan Fable: cakupan pengganti TIDAK LENGKAP.** Rujukan keputusannya lengkap (writer 6 Okt + D13-9c), empat
pemeriksaan logika lama memang diulang di jsdom, tetapi:

| Yang ada di kasus lama | Pengganti sekarang | Yang kurang |
|---|---|---|
| Dijalankan di **browser sungguhan**, aplikasi hidup, **desktop dan HP** (viewport) | jsdom saja, tanpa viewport | Tidak ada bukti browser untuk helper lusin di layar mana pun, desktop maupun HP. Penulis sendiri menulis "uji itu tidak menggantikan kasus browser". |
| Layar yang dipakai pengguna | Layar simulasi `SalesPages` — di mode tersambung **tidak tampil** | Layar yang dipakai pengguna CP7 adalah P11 (`SalesDraftPanel`) dengan helper berbeda ("Lusin invoice N" + "Sisa PCS invoice N", tombol "Terapkan lusin baris N"). Kasus browser P11 **tidak menekan** helper itu; hanya jsdom (`src/SalesDraftPanel.dom.test.tsx`: lusin 2 → qty 24). |
| Bagi rata 1 lusin → 4/4/4 ke tiga ukuran; tolak 1,1 lusin | Hanya di layar simulasi | Di P11 tidak ada semantik "bagi rata ke ukuran" dan tidak ada input pecahan lusin (lusin bulat + sisa 0–11 PCS). Ini **bukan cacat**: baris P11 per ukuran. Tetapi harus diputuskan owner bahwa alur "lusin bulat + sisa PCS per baris" memang yang diinginkan (rekomendasi: ya, terima; tidak perlu bagi rata). |

Supaya menjadi LENGKAP (usulan untuk putaran 2, tanpa mengubah produk): satu kasus browser P11 desktop + satu HP yang
mengisi "Lusin invoice N" = 2 dan "Sisa PCS" = 1, menekan "Terapkan lusin baris N", memeriksa qty = 25 dan total baris,
memeriksa qty tidak berubah sebelum tombol ditekan, dan tidak ada overflow horizontal di HP. Uji jsdom yang ada boleh
tetap. Sampai itu ada, status pensiun menurut D13-9c **belum sah**; dampaknya nol pada produk (kasus lama tetap ada di
suite CP6 beku dan merah karena selector basi, seperti sebelumnya).

## A7 — `product_ref=ddedf06c` di identitas T3

Dibaca `scripts/cp6_run_identity.py`: `product_ref = git log -1 --format=%H -- supabase/migrations supabase/dev
supabase/release supabase/rollbacks src`. Penulis benar: **bukan pin**, melainkan commit terakhir yang menyentuh jalur
produk CP6 + frontend. Kata-kata saya di retest §2.5 ("memajukan pin") saya **tarik**. DITUTUP (TERIMA).

Dua catatan, bukan temuan:
- Nilai itu identitas **sentuhan**, bukan identitas **isi**. Di `ae0214ad` nilainya menjadi `144d0709` (commit yang
  memindahkan satu berkas uji keluar dari `src/`), padahal isi `src/` identik dengan `ddedf06c`/`7a0b4a90`. Kalau mau
  identitas isi, tambahkan hash tree jalur produk (`git rev-parse <commit>:src` dan seterusnya) di baris identitas.
  Opsional.
- Jalur produk itu tidak memuat `scripts/cp7-src` (SQL CP7). Untuk CP7 identitasnya memang `writer_runtime.source_sha256`
  bundel, jadi tidak ada celah; hanya nama kolom `product_ref` yang bisa menyesatkan pembaca CP7.

## A8 — Tinjauan diff 12 berkas alat/uji (INDEPENDENT_SOURCE_REVIEW)

| Berkas | Isi yang terbaca | Penilaian |
|---|---|---|
| `scripts/cp6_auditor_runner.py` | lihat A2: pembanding tidak berubah; tambahan diagnosis di savepoint sendiri; impor `state_difference` | aman; dipakai semua workflow → regresi per kasus pada runner baru: p19-transport 12 job (report-v2 20, plan-v2 22, k6 10, reminder-v2 16, k2 10, ai-v2 9, transport11 15, k4 17, staged 14, pl5 20, k3 24, scale5 5), pl-native 4 job (model 32, netting 83, schedule 71, supply 53), supplier-payment ×3 (10 each), shell (assembly paritas byte-identik, staged 5.000×100 DONE), Fable core/smoke/xc1 → **semua PASS** kecuali 1 COUNTEREXAMPLE milik kasus Fable (F-OPS-05) |
| `scripts/cp6_auditor_difference.py` + `_difference_test.py` | fungsi murni + 5 uji (sama, urutan saja, isi, tabel erp/baris public, auth) | aman; 5/5 OK di Shell S0 (job 115354965906) |
| `scripts/cp7_nightly_backup.py` | lihat A1 | aman, satu temuan minor F-OPS-05 |
| `scripts/cp7_k3_cleanup_cases.py` | 2 kasus baru: gladi jadwal (proses terpisah, penolakan dulu, pasang, verifikasi, lepas, pulih) dan kepemilikan OID (situasi A–D dengan DDL admin disisipkan lewat monkeypatch `Tools.dump/restore/data_hashes`; semua database sintetis dibersihkan di `finally`) | oracle penulis masuk akal dan ketat; sesuai sumber |
| `scripts/cp7_f05_analysis_probe.py`, `claude-p19-transport.yml`, `cp7-nightly-backup.yml` | hitungan K3 23→24, nama suite, komentar | kosmetik |
| `claude-p08-shell.yml` | satu baris: menjalankan uji `state_difference` | aman |
| `scripts/cp7_group_end_repeat_diagnosis.py` + `cp7-group-end-diagnosis.yml` | alat diagnosis ulang grup (20× per job, catat `ctid`/`xmin` fungsi public); bukan workflow kualifikasi; gerbang T3 merah sesuai rancangan | tidak memengaruhi kualifikasi |
| `tests/cp7/SalesPages.dozenHelper.dom.test.tsx` | lihat A6 | jsdom saja |

## A9 — Untuk diketahui

D13-4..D13-9 dibaca. Konsisten dengan register auditor saya (D13-1..3). Catatan: D13-7 (produksi = Enteng `postgres`)
berarti nama database tujuan untuk jadwal sudah ada; yang masih ditahan sampai CP7C adalah seluruh urusan backup/Drive
(D13-9a). Tidak ada tindakan di putaran ini.

## Ringkasan per butir

| Butir | Status | Run / job / kasus | Label |
|---|---|---|---|
| A1 | **DITUTUP** (keluarga F-OPS-01 / ASR-OPS-01 tertutup tanpa jalur hapus baru; batas operasional terkonfirmasi dan dinilai dapat diterima, keputusan owner) + 1 temuan minor baru F-OPS-05 | Fable: 38414814884/115356320136 (4 balapan + 1 native), 38414828309/115356368140 (2 kasus backup lama); penulis: 38414371682/115354760145 `k3-cleanup-24` 24/24 | FABLE + INDEPENDENT_NATIVE_RERUN + INDEPENDENT_SOURCE_REVIEW |
| A2 | MASIH TERBUKA (OPEN) — pekerjaan yang diminta owner selesai; akar penyebab belum ada | 3 run Fable 10/10 PASS (job 115354813981, 115354861401, 115354912368) | INDEPENDENT_NATIVE_RERUN + INDEPENDENT_SOURCE_REVIEW |
| A3 | **DITUTUP** (syarat §3.2c terpenuhi untuk gladi; pemasangan sungguhan tetap menunggu izin D13-3/CP7C) | 38414371682/115354760145 `K3C_RACE_SCHEDULE_INSTALLER_REHEARSAL`; bukti penulis log 08 | INDEPENDENT_NATIVE_RERUN + INDEPENDENT_SOURCE_REVIEW |
| A5 | **DITUTUP** (penerimaan PR44 berlaku untuk ae0214ad) | diff kosong; netting 38414446165/115355020037 83/83 | INDEPENDENT_SOURCE_REVIEW + INDEPENDENT_NATIVE_RERUN |
| A6 | **MASIH TERBUKA: cakupan pengganti TIDAK LENGKAP** (butuh kasus browser P11 desktop + HP yang menekan helper lusin; lihat A6). Pensiun belum sah menurut D13-9c. | Shell S0 38414431084/115354965906 (uji jsdom ✓) | INDEPENDENT_SOURCE_REVIEW + INDEPENDENT_NATIVE_RERUN |
| A7 | DITUTUP (TERIMA penjelasan penulis; kata-kata Fable ditarik) | — | INDEPENDENT_SOURCE_REVIEW |
| A8 | **DITUTUP** (12 berkas dibaca; runner baru lulus regresi per kasus di 22 job, 478 baris) | 38414371682, 38414385732, 38414401092, 38414415980, 38414431084, 38414446165 + 3 run Fable | INDEPENDENT_SOURCE_REVIEW + INDEPENDENT_NATIVE_RERUN |
| Temuan baru | **F-OPS-05 (minor):** tanda polos (tanpa OID) masih dihormati pada nama `--scratch`; database asing dengan salinan tanda itu dihapus. Rekomendasi: hanya tanda ber-OID yang dihitung milik alat. | 38414814884/115356320136 `XC1:PLAIN_MARK_COPIED_ONTO_FOREIGN` COUNTEREXAMPLE | FABLE |

## Vonis putaran silang 1

Kandidat `ae0214ad` (produk = `7a0b4a90`): **LULUS DENGAN SYARAT** tetap berlaku, dengan syarat yang kini tersisa:

1. **A2 OPEN** — penyebab dua kegagalan akhir grup bayar supplier belum ditemukan; diagnosis terpasang; 13 run berikutnya
   (penulis 10 + Fable 3) lulus. Bukan penghalang pembekuan menurut saya **kalau owner menerima** status OPEN dengan
   diagnosis terpasang (rekomendasi: terima; tambah pembanding terurut sebagai pelengkap, bukan pengganti).
2. **A6 TIDAK LENGKAP** — pensiun `SALES_MANUAL_13` belum sah sampai ada kasus browser P11 (desktop + HP) untuk helper
   lusin. Pekerjaan putaran 2, tanpa perubahan produk.
3. **F-OPS-05 (minor)** — perbaikan kecil di alat backup (hapus penerimaan tanda polos) sebelum CP7C memakai alat ini.
4. Batas operasional A1: diterima sebagai catatan bila verifikasi restore berjalan di mesin GitHub (D13-6/D13-8b);
   keputusan owner.
5. Yang tidak berubah: `production_go:false`; pemasangan jadwal/backup menunggu CP7C (D13-9a).

Commit laporan ini dicatat di pesan commit cabang `audit/fable-cp7-full-d0b9e9c2-20261011`.

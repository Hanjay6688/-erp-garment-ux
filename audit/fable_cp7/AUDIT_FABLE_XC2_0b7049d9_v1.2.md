# Laporan Fable v1.2 — putaran silang 2 CP7, kandidat `0b7049d9`

**Status:** v1.2 FINAL (14 Okt 2026, 03:35 UTC). Review sumber dan 6 run independen selesai, semua dibaca per kasus (24 job, 17 dengan baris kasus: 376 baris, 373 PASS, 2 INCOMPLETE legacy pre-freeze seperti sebelumnya, 1 COUNTEREXAMPLE = fixture Fable pada run pertama XC1, lihat R2-F05; 0 FAIL, 0 pengulangan hari bisnis). Register run: `runs/xc2_0b7049d9/`.
Menjawab `docs/cp7/audit-candidate/crosscheck-r2-20261014/HANDOFF_FABLE.md` (D13-12, D13-13). Cakupan CP7 saja.
Keputusan owner yang sudah disahkan tidak dibuka ulang. `production_go:false`.

| | |
|---|---|
| Kandidat | `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18` (diperiksa sendiri) |
| Kode produk | identik dengan `ae0214ad` dan `7a0b4a90`: `git diff --name-only ae0214ad 0b7049d9 -- supabase src scripts/cp7-src` kosong (0 baris, diperiksa sendiri) |
| Berubah di luar `docs/` sejak `ae0214ad` | kualifikasi: `cp7_nightly_backup.py`, `cp7_k3_cleanup_cases.py`, `cp7_f05_analysis_probe.py` (24→25), `claude-p19-transport.yml` (nama suite), `cp7-nightly-backup.yml` (komentar), `cp7_p11_drafts_browser.mjs`, `docs/cp7/k3/K3_CLEANUP.json`. CP7C ditahan (D13-9a), tidak dipakai kualifikasi: `cp7_offsite_backup*.py`, `cp7_supabase_restore_drill.py`, `ops/backup-repo/*`, 3 workflow backup. `cp6_auditor_runner.py` dan `cp6_auditor_difference.py` **tidak berubah** (diff kosong, diperiksa sendiri). |
| Head cabang saat uji | `0e45da9e`; selisih `0b7049d9..0e45da9e` di luar `docs/` **kosong** (diperiksa sendiri) → workflow penulis didispatch pada head, identik dengan kandidat. Run Fable checkout `product_ref=0b7049d9` persis (assert HEAD + tree). |
| Hasil Astra (silang) | dibaca hanya dari ringkasan di kotak handoff dan tracker; cabang Astra tidak dibuka. |

Label bukti: FABLE = oracle dan eksekusi Fable; INDEPENDENT_NATIVE_RERUN = oracle penulis, dispatch dan pembacaan per
kasus oleh Fable; INDEPENDENT_SOURCE_REVIEW = diff dibaca Fable; WRITER_CROSSCHECK = bukti CI penulis, dikutip tanpa
diklaim.

## R2-A6 — Cakupan pengganti `SALES_MANUAL_13` (D13-12 butir 1)

### Review sumber `scripts/cp7_p11_drafts_browser.mjs` @ `0b7049d9`, fungsi `dozenHelper` (INDEPENDENT_SOURCE_REVIEW)

| Yang diminta owner (D13-12) | Yang dilakukan kasus, dibaca baris per baris | Penilaian |
|---|---|---|
| browser sungguhan, desktop dan HP | dipanggil dari `lifecycle(ui,today,mobile)` untuk `P11_DRAFT_BROWSER_DESKTOP` (desktop) dan `P11_DRAFT_BROWSER_MOBILE_RECOVERY` (HP, emulasi Chromium viewport ponsel, zona `America/Los_Angeles`) pada aplikasi hidup mode tersambung | ya |
| menekan "Terapkan lusin baris N" | `form.getByRole('button',{name:'Terapkan lusin baris 1',exact:true})`; input `Lusin invoice 1` dan `Sisa PCS invoice 1` diisi setelah membuka "Isi dengan lusin + PCS" | ya (baris 1) |
| hasil qty | sebelum tombol: qty tetap `13` meski isian sah (`2`,`1`); sesudah tombol: `25` (= 2×12 + 1); lalu `1`,`1` → `13` lewat helper (nilai sebelumnya 25) | ya, dua arah |
| pemeliharaan baris lain | baris 2 (qty `2`, harga `10,01`, potongan `0,02`, catatan) dibandingkan `deepEqual` sebelum dan sesudah tiap penerapan | ya |
| simpan / baca ulang | draft disimpan; `read_draft` dari server: qty `[2,13]`, stok `[17,28]`; form edit membaca `13` dari server (`toHaveValue('13')` sebelum diubah ke 5) | ya |
| tambahan | lima isian tidak sah (kosong, `1,1`, `1.1`, sisa 12, `0`+`0`) → tombol nonaktif dan qty tetap 13; total `Rp520` lalu `Rp280`; tanpa geser horizontal (`scrollWidth<=innerWidth+1`, dicek di HP juga); tangkapan layar `P11_DOZEN_HELPER_{DESKTOP,MOBILE}.png` | melebihi permintaan |
| harapan lama kasus | semua assert lama tetap ada (manual13 preserved, edit 5, posting, balasan CREATE hilang di HP) | tidak ada yang dilonggarkan |

Pemetaan ke empat pemeriksaan kasus lama `salesManual` (CP6, layar simulasi): qty manual 13 tetap → **browser P11** ✓;
helper kosong tidak mengubah apa pun → **browser P11** (`EMPTY` ditolak, qty tetap) ✓; pecahan lusin ditolak →
**browser P11** (`1,1` dan `1.1`) ✓; 1 lusin → 4/4/4 ke tiga ukuran → **tidak ada padanan di P11** (baris per ukuran,
helper lusin + sisa PCS per baris), tetap hanya jsdom di layar simulasi yang tidak tampil di mode tersambung.

Bukti pertama penulis (WRITER_CROSSCHECK, log job 115419948325): kedua kasus pada catatan pertama INCOMPLETE dengan
`status_before_rollover: PASS` dan error `AUDITOR_BUSINESS_DAY_ROLLOVER` (run melewati tengah malam WIB), lalu
dieksekusi ulang dari salinan baru dan PASS; semua nilai helper identik di keempat catatan. Ini sesuai ASF-F01 (hanya
PASS sebelum pergantian hari yang boleh diulang), dan koreksi kalimat yang diminta Astra sudah ada di README.

### Run independen (INDEPENDENT_NATIVE_RERUN, dispatch Fable pada head `0e45da9e` = kandidat)

| Run / job | Kasus | Hasil |
|---|---|---|
| `cp7-f03-full` run 38499931807 / job 115644220763 (p11) | `P11_DRAFT_BROWSER_DESKTOP`, `P11_DRAFT_BROWSER_MOBILE_RECOVERY` + 62 kasus p11 lain | **64/64 PASS**. Kedua kasus: `refused_with_quantity_kept` = EMPTY, FRACTIONAL_DOZEN, FRACTIONAL_DOZEN_DOT, MORE_THAN_11_PCS, ZERO; `unchanged_before_apply` true; `applied_2_dozen_1_pcs` 25; `other_line_unchanged` true; total 520; `line1_set_back_by_helper` "1 dozen + 1 = 13"; `no_horizontal_overflow` true (HP juga); `dozen_helper_qty_saved_and_read_back` [2,13]; `edit_form_reads_back_13` true; HP: `lost_create_replay_identical` true. Tanpa pergantian hari (planned=before=after 2026-10-14). |
| `cp7-prefreeze-ui` run 38499939794 / job 115644248711 | 31 kasus termasuk kedua kasus P11 | **31/31 PASS** + 2 INCOMPLETE legacy (LEGACY_RUNTIME_OBSERVATION_ONLY, sama seperti semua run sebelumnya); kedua kasus P11 PASS dengan nilai helper identik. |

### Pernyataan

**Cakupan pengganti `SALES_MANUAL_13` (desktop dan HP): LENGKAP untuk komposisi CP7** (D13-9c, D13-12).

Alasan: semua yang diminta D13-12 ada dan terbukti di browser sungguhan, desktop dan HP, pada aplikasi mode tersambung
yang dipakai pengguna: tombol "Terapkan lusin baris 1" ditekan, qty = lusin×12 + sisa, qty tidak berubah sebelum tombol,
baris lain terpelihara, tersimpan dan terbaca ulang dari server, form edit membaca nilai dari server. Tiga dari empat
pemeriksaan kasus lama (13 tetap, helper kosong tidak mengubah, pecahan ditolak) kini ada di browser P11. Yang tidak ada
padanannya hanya "1 lusin → 4/4/4 ke tiga ukuran", dan itu memang bukan perilaku layar P11 (lusin + sisa per baris,
baris per ukuran). Catatan yang sama dengan Astra: bagi rata 4/4/4 tetap hanya jsdom di layar simulasi yang tidak tampil
di mode tersambung; HP = emulasi viewport Chromium, bukan perangkat fisik. Keduanya bukan kekurangan cakupan untuk CP7.
Pensiun `SALES_MANUAL_13_{DESKTOP,MOBILE}` dari komposisi CP7 dengan ini **sah** menurut D13-9c; di suite CP6 beku
keduanya tetap ada.

## R2-F05 — Tanda polos (D13-12 butir 2)

### Review sumber `scripts/cp7_nightly_backup.py` @ `0b7049d9` (INDEPENDENT_SOURCE_REVIEW)

| Bagian | Diff dari `ae0214ad` | Penilaian |
|---|---|---|
| `is_mark` | cabang `return token is None and comment == SCRATCH_MARK` **dihapus**; kini `bool(m) and int(m.group(2)) == oid and (token is None or m.group(1) == token)`: hanya tanda percobaan yang menyebut OID database itu sendiri | tepat sesuai D13-12 |
| `mark_scratch` | wajib `token` 16 hex dan `oid` int (`BACKUP_MARK_INVALID`); tidak bisa lagi menulis tanda polos | tidak ada jalur menulis tanda polos |
| `leftovers` | hanya database bertanda percobaan untuk OID-nya sendiri | konsisten |
| `drop_owned` | tidak berubah; jalur `created_here and comment is None` tetap: menghapus OID yang **dibuat percobaan ini** bila gagal sebelum tanda ditulis. Bukan pemakaian tanda polos; OID dipilih acak oleh alat dan hanya bisa "disusupi" dengan `CREATE DATABASE ... OID` yang sama secara sengaja di tengah percobaan | diterima; kelas yang sama dengan batas operasional A1 (Astra B10 menguji jalur ini) |
| kasus penulis | `K3C_RACE_BACKUP_PLAIN_MARK_COPIED_ONTO_FOREIGN_KEPT`: tanda polos disalin ke (1) database bernama `--scratch` → `BACKUP_SCRATCH_EXISTS_NOT_OURS`, utuh dengan OID dan barisnya; (2) database berpola `<scratch>_<hex>` dengan nama scratch bebas → bukan sisa, malam terverifikasi, utuh. Dua kasus lama yang memakai tanda polos sebagai "milik alat" diganti ke tanda ber-OID (`'c'*16`, `'d'*16` + OID database itu) dengan harapan yang sama | oracle ketat; perubahan fixture tidak melonggarkan harapan (saya baca kedua hunk: `scratch_before == OURS`, pengganti tetap, `REPLACED`; sisa milik alat dipakai ulang lalu dihapus) |

### Run independen ⏳

| Kasus | Oracle | Run / job | Hasil |
|---|---|---|---|
| XC1:PLAIN_MARK_COPIED_ONTO_FOREIGN (**oracle tidak diubah**; COUNTEREXAMPLE di ae0214ad) | FABLE | 38499948491 / 115644276036 **dan** 38500182116 / 115645028154 | **PASS di keduanya**: database asing bernama `--scratch` dengan salinan tanda polos → `scratch_before=FOREIGN`, `BACKUP_SCRATCH_EXISTS_NOT_OURS`, database **utuh** (OID sama, kanari `FOREIGN_WITH_COPIED_PLAIN_MARK`, komentar masih tanda polos), tidak ada yang dihapus. |
| XC1:ATTEMPT_SWAPPED_BEFORE_RESTORE_KEPT, COPIED_OID_MARK_ON_FOREIGN_KEPT, NO_NAME_BASED_DROP_OR_CREATE_IN_TOOL | FABLE | kedua run di atas | **PASS** (batas operasional terkonfirmasi lagi: pengganti menerima 559 tabel, tidak dihapus, malam tidak terverifikasi; database berpola tanpa tanda / tanda OID lain utuh; sha256 alat `efe6c6b4…`, 0 `dropdb`, satu `drop database` di `drop_owned`). |
| XC1:LEFTOVER_REPLACED_AFTER_DUMP_KEPT | FABLE | run 1: 38499948491 / 115644276036 → **COUNTEREXAMPLE (fixture Fable, AUDITOR_TOOL)**; run 2: 38500182116 / 115645028154 → **PASS** | Run 1: fixture Fable menulis sisa dengan **tanda polos** (meniru alat lama). Di alat baru tanda itu asing, malam ditolak `BACKUP_SCRATCH_EXISTS_NOT_OURS` sebelum dump, dan database itu **utuh** (kanari `OLD_OURS`, tidak dihapus); label COUNTEREXAMPLE muncul hanya karena kasus mengharapkan jalur "diganti sesudah dump" yang tidak pernah tercapai. Bukan cacat alat; log disimpan sebagai hasil pertama. Run 2: fixture menulis tanda ber-OID seperti yang kini ditulis alat (oracle tidak berubah) → urutan Astra tercapai: `scratch_before=OURS`, sisa `ABSENT` sesudah dump, pengganti asing **utuh** (kanari `FOREIGN_AFTER_DUMP`), `BACKUP_SCRATCH_REPLACED`, `restore_verified=false`, tidak ada database percobaan tersisa. |
| FABLE_CORE:BACKUP_SCRATCH_DROPS_FOREIGN_DB, BACKUP_VERIFY_UNDER_LIVE_WRITES (+ 9 kasus core lain) | FABLE | 38499956853 / 115644310853 | **11/11 PASS** (5 native, 5 balapan, 1 HTTP). |
| `k3-cleanup-25` (25 kasus) | INDEPENDENT_NATIVE_RERUN | 38499922493 / 115644190673 | **25/25 PASS**: `K3C_RACE_BACKUP_PLAIN_MARK_COPIED_ONTO_FOREIGN_KEPT` (tanda polos di nama scratch → ditolak & utuh; di pola percobaan → bukan sisa, malam dengan nama bebas terverifikasi, utuh, OID dan baris sama); `OWNERSHIP_BY_OID` A–D sesuai; `NEVER_DROPS_ANOTHER_DATABASE`; gladi jadwal tetap PASS. |

Catatan: kasus Fable `XC1:LEFTOVER_REPLACED_AFTER_DUMP_KEPT` memasang sisa dengan `nightly.mark_scratch(admin, scratch)`
tanpa token (tanda polos versi lama). Di alat baru `mark_scratch` menolak pemanggilan itu (`BACKUP_MARK_INVALID`) —
yang terjadi di run pertama adalah varian lain: fixture menulis tanda polos langsung sebagai komentar, sehingga alat baru
(benar) menolaknya sebagai asing sebelum dump; kasus berlabel COUNTEREXAMPLE karena jalur yang diharapkan tidak tercapai,
padahal tidak ada yang dihapus. Fixture diperbaiki (tanda ber-OID, oracle sama) dan dijalankan ulang: PASS. Kedua log
disimpan (`runs/xc2_0b7049d9/job_115644276036.json`, `job_115645028154.json`).

### Pernyataan

**F-OPS-05: DITUTUP.** Hanya tanda yang menyebut OID database itu sendiri yang dihitung milik alat; tanda polos tidak bisa
ditulis dan tidak dihormati di mana pun; database asing dengan salinan tanda polos tetap utuh (dibuktikan oleh kasus
Fable dengan oracle yang sama yang dulu menghasilkan COUNTEREXAMPLE, dan oleh kasus penulis). Keluarga F-OPS-01 /
ASR-OPS-01 tetap tertutup pada aturan tanda baru (situasi A–D PASS, kasus Fable PASS). Batas operasional A1 tetap seperti
dinyatakan.

## R2-REG — Register

`docs/cp7/OWNER_DECISIONS_20261008.md` @ `0b7049d9` baris D13-10, D13-11, D13-12, D13-13 dibandingkan **kata per kata**
(program, bukan mata) dengan `OWNER_DECISIONS_TO_AUDITOR_20261013.md` @ `9fc44978`: **keempatnya IDENTIK.** Cocok.

## R2-D11 dan A2 — untuk diketahui

D13-11 adalah izin, tidak dipakai; `state_difference` yang terpasang sudah membedakan ORDER_ONLY/CONTENT. Saya setuju
tidak ada yang perlu ditambah sekarang. A2 tetap keterbatasan terbuka (D13-10); `CP7 Supplier Payment Create` di
kandidat 10/10 menurut CI penulis (tidak saya ulang di putaran ini; tiga run saya di `ae0214ad` dengan runner yang
sama tetap berlaku karena runner tidak berubah).

## Silang dengan Astra

Dibaca dari ringkasan kotak/tracker saja. Tidak ada yang saya bantah: R2-F05 DITUTUP, R2-A6 LENGKAP untuk komposisi
CP7 dengan catatan yang sama (4/4/4 hanya jsdom; HP = emulasi Chromium), A2 terbuka bukan penghalang, batas A1 tetap.
Catatan Astra bahwa jalur `created_here` bukan pemakaian tanda polos: saya setuju (lihat tabel R2-F05).

## Ringkasan

| Butir | Status | Run / job / kasus | Label |
|---|---|---|---|
| R2-A6 | **LENGKAP** (pensiun `SALES_MANUAL_13` sah untuk komposisi CP7) | 38499931807/115644220763 P11 2 kasus browser (+62); 38499939794/115644248711 31 kasus; sumber `dozenHelper` dibaca | INDEPENDENT_NATIVE_RERUN + INDEPENDENT_SOURCE_REVIEW |
| R2-F05 | **DITUTUP** | Fable 38500182116/115645028154 5/5 (+ run pertama 38499948491/115644276036, 1 fixture Fable); core 38499956853/115644310853 11/11; k3-cleanup-25 38499922493/115644190673 25/25 | FABLE + INDEPENDENT_NATIVE_RERUN + INDEPENDENT_SOURCE_REVIEW |
| R2-REG | **COCOK** (D13-10..13 identik kata per kata) | perbandingan program | INDEPENDENT_SOURCE_REVIEW |
| R2-D11 | untuk diketahui; setuju tidak dipakai | runner/difference diff kosong | INDEPENDENT_SOURCE_REVIEW |
| A2 | MASIH TERBUKA, bukan penghalang (D13-10) | tidak diulang di putaran ini | — |
| Regresi alat (p19-transport 12 job) | semua PASS: staged 14, pl5 20, k2 10, scale5 5, transport11 15, reminder-v2 16, k4 17, ai-v2 9, report-v2 20, plan-v2 22, k6 10, k3 25 | 38499922493 | INDEPENDENT_NATIVE_RERUN |
| Temuan baru | tidak ada | — | — |
| Bantahan terhadap Astra | tidak ada | — | — |

## Vonis

Kandidat `0b7049d9` (produk = `7a0b4a90`): kedua butir pembekuan final menurut D13-13 **tertutup dari sisi Fable**:
R2-A6 LENGKAP dan R2-F05 DITUTUP. Dengan A2 tercantum sebagai keterbatasan terbuka (D13-10) dan batas operasional A1
sebagai catatan, **tidak ada hal yang menghalangi pembekuan final CP7 dari sisi Fable.** Pemasangan jadwal dan backup
tetap menunggu CP7C (D13-9a). `production_go:false` tetap.

Commit laporan ini dicatat di pesan commit cabang `audit/fable-cp7-full-d0b9e9c2-20261011`.

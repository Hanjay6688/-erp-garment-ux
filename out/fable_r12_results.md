# Fable — putaran 12 (pra-BC): reproduksi independen temuan "pre-existing" F1/F2 dari writer

Tanggal: 2026-09-25 17:15–17:45Z. Label: INDEPENDENT_NATIVE_RERUN (skenario sendiri, runtime `cp6-auditor-scenario.yml`, ref = cabang writer).
Oracle hanya dari kontrak (M:485 pembulatan, M:835 pembulatan kewajiban per dokumen, M:1066 ACC-DEC02 harga eceran manual, M:6632 total/per tanggal/jejak sumber)
dan keputusan owner T3 = opsi A (OWNER_CONFIRMED_TO_AUDITOR). CP6 tetap HOLD; `production_go=false`.

## 0. Konteks
- Head writer bergerak 4c61aca → 7c9d00a (probe BC 32 kasus, lokal saja) → 4b1bd66 (probe enam state ALL era BA = butir 3b handoff) → 95353aa
  (halaman BC, races/HTTP/browser BC, workflow CI BC, workflow auditor: fase `after` kini memasang BC, fase baru `pre_bc`).
- **BC belum final**: belum ada bagian handoff, belum ada tabel kasus di docs, belum ada run CI BC yang saya baca. Audit BC belum dimulai.
- Paket rilis DB (`supabase/migrations`, `supabase/release`, `supabase/rollbacks`) **identik byte** 4c61aca..95353aa. Perubahan hanya `supabase/dev/cp6_bc_t1_family.sql`,
  `scripts/cp6_bc_*`, berkas `src` BC, dua workflow. Jadi fase `after` pada 4b1bd66 dan fase `pre_bc` pada 95353aa = produk sebelum BC (dijaga kasus `XA12:BC_ABSENT`).
- Commit writer 7c9d00a menyebut dua temuan **pre-existing** dan **mengecualikan** salah satunya dari delta probe BC-nya sendiri (`STALE_F2` di `scripts/cp6_bc_probe.py`).
  Itu klaim writer (WRITER_EXPLANATION). Putaran ini mengujinya sendiri sebelum BC.

## 1. Skenario dan run
Skenario: `audit/scenarios/round12_fable/xaudit_12_f1f2.py` (rev5 sha256 `7ce9d35eab9657fc36aa3f8d7cc239d0457b1e74d523eb1018eca03aad11aafd`).
Kasus: `BC_ABSENT` (penjaga), `DETECTOR_SOURCE_AND_BASELINE` (teks fungsi dari `pg_proc`, baseline bersih), F2 lima jalur, F1 satu jalur lewat fasad nota AP.

| Run | Rev | Head | Fase | Hasil | Catatan |
|---|---|---|---|---|---|
| 36165571453 | 1 | 4b1bd66 | after | merah | cacat alat auditor: `cases()` mengembalikan dict, runner minta `[(id, callable)]`. Bukan bukti produk. |
| 36166046560 | 2 | 4b1bd66 | after | 4 PASS / 3 CE / 1 INCOMPLETE | status F2 sah; F1 INCOMPLETE karena jalur error saya tanpa savepoint. |
| 36166784262 | 3 | 4b1bd66 | after | 2 PASS / 6 CE | run detail; cek kewajiban saya salah kunci (nama mapping vs kode akun) → status rev3 tercemar; angka `accounts_delta` tetap sah. |
| 36167400464 | 4 | 4b1bd66 | after | 2 PASS / 5 INCOMPLETE / 1 CE | F1 lewat fasad asli **terbukti**; F2 gagal pada salah nama kolom saya (`triggering_material_id`). |
| **36168041413** | **5** | **95353aa** | **pre_bc** | **4 PASS / 4 COUNTEREXAMPLE, 0 INCOMPLETE** | **run beku putaran ini.** Semua run tercatat apa adanya; tidak ada relabel. |

Setup rev5: au/av/ay/az/ba/bb PASS, `bc_install` tidak ada (pre_bc). `BC_ABSENT`: marker v2.6.20bc tidak ada, fasad service BC tidak ada, fasad nota AP ada.

## 2. F2 — detektor `run_v255_material_cost_integrity_checks:MATERIAL_RECOST_GL_STATE_DRIFT` (ERROR)
Teks baseline (dari `pg_proc`): baris ini menandai setiap gerakan konsumsi (CUTTING_GROUP, MATERIAL_ADJUSTMENT_ITEM, …) yang
`|round(qty × (unit_cost − original_cost), 2) − material_cost_revaluation_state.applied_inventory_delta| > 0.01`, dengan `coalesce(applied, 0)` bila baris state tidak ada.

| Kasus (rev5) | Buku (oracle kontrak) | Detektor | Status | Mekanisme |
|---|---|---|---|---|
| CONTROL: terima 10 @10.00 (estimasi), invoice 10.005 | kewajiban −100.05 = 10×10.005 dibulatkan per dokumen ✓; persediaan 100.05 ✓ | diam | PASS | tidak ada gerakan konsumsi |
| ADJUST −3 lalu invoice 10.005 | kewajiban −100.05 ✓; persediaan 70.03 (7×10.005=70.035, selisih 1 sen dari qty×rata2, pembulatan M:485), beban 5900 +30.02; fakta v2.6.20t ada, jurnalnya cocok (V2620T_* = 0) | **+1** | COUNTEREXAMPLE | gerakan penyesuaian **tidak punya baris `material_cost_revaluation_state`** (`applied = NULL`); recost-nya dicatat mesin dokumen v2.6.20t (`material_adjustment_revaluation_facts`, target 0.02/−0.02) — detektor lama membaca tabel yang tidak ditulis mesin baru |
| ADJUST −3 lalu invoice 2.10 | kewajiban −21.00 ✓; persediaan 14.70 = 7×2.10 **tepat**; beban 6.30 = 3×2.10 tepat; fakta v2.6.20t −23.70/+23.70, V2620T_* = 0 | **+1** | COUNTEREXAMPLE | sama: `applied = NULL` vs target 23.70 |
| STACKED n=3 (pool, potong, invoice 10.005) | WIP 30.03 = 3×10.01 ✓; persediaan 0 ✓; kewajiban −30.03 ✓ | diam | PASS | applied per gerakan −0.02/0.00/−0.01 vs target −0.01: dalam batas 0.01 |
| STACKED n=10 | WIP 100.10 = 10×10.01 ✓; persediaan 0 ✓; kewajiban −100.10 ✓; 38 event revaluasi | **+1** | COUNTEREXAMPLE | satu gerakan potong `applied −0.05` vs target −0.01: **sen dokumen terkumpul di satu PO** (persis fenomena T3; owner memilih A: tidak ada batas per PO) |

Kesimpulan F2: **klaim writer CONFIRMED** — buku memenuhi oracle kontrak di kelima jalur, jejak penyesuaian ada di tabel fakta v2.6.20t dan lolos V2620T_*, tetapi detektor
v2.5.5 melapor ERROR pada dua mekanisme yang keduanya sah setelah v2.6.20t / BA W8 / T3-A. Ini **cacat detektor (pre-existing), bukan cacat buku**. Catatan penting:
1. Dampak: `run_v255_…` tidak dipanggil dari UI (`src`) dan tidak digate T2/T3 (T2 hanya membaca V2620T_* dari v267). Jadi dampaknya pada pemeriksaan operator/DB dan pada probe
   keluarga; bukan pada laporan pengguna. Tetap: sebuah guard ERROR yang salah positif harus **didisposisi tertulis**, bukan dikecualikan diam-diam di probe.
2. Aturan "≤ 0,01 per gerakan" di detektor lama **bertentangan** dengan keputusan owner T3-A (sen beberapa nota boleh terkumpul di satu PO). Penyelarasan/pensiun
   detektor ini perlu CR kecil atau catatan owner; auditor tidak menetapkan solusinya.
3. Pengecualian `STALE_F2` di probe BC writer harus dinyatakan di handoff BC sebagai temuan terbuka dengan disposisi, dan setiap kasus BC yang recost tetap mengunci
   `books = subledger` (writer sudah melakukannya) **dan** V2620T_* = 0.
4. Sub-catatan (bukan temuan): pada ADJUST+10.005 produk mengalokasikan sen dokumen 0.05 → beban 0.02 (3×0.005=0.015 dibulatkan) dan persediaan 0.03; nilai persediaan 70.03 vs
   70.035 tidak punya representasi sen; sesuai M:835 + carry BA W8. Detektor produk `MATERIAL_GL_VALUATION_MISMATCH` (toleransi 0.05) diam.

## 3. F1 — `run_v265_gudang_write_integrity_checks:contractor_issue_price_provenance_gap` (CRITICAL)
Rev5, jalur asli: fasad `public.erp_save_accessory_issue_action_v1` POST, mode MANUAL, `manual_price 3.00`, `physical_at` WIB. Baris nota terposting:
`manual_retail_unit_price 3.00`, `accessory_price_version_id NULL`, `unit_sale_price_snapshot 3.0000`. Detektor **+1 CRITICAL**.
Predikat baseline (dari `pg_proc`): `(ACCESSORY and accessory_price_version_id is null) or (bukan ACCESSORY and material_price_version_id is null)` — tidak mengenal
`manual_retail_unit_price`. M:1066 ACC-DEC02 memutuskan harga eceran manual sah. **Klaim writer CONFIRMED (pre-existing).**
Perbaikan writer di BC (`supabase/dev/cp6_bc_t1_family.sql` ~3946: menambah `and i.manual_retail_unit_price is null` pada cabang ACCESSORY) konsisten kontrak dan sempit;
baris tanpa keduanya tetap ditandai. **Diverifikasi di putaran BC**: seluruh badan fungsi v265 BC harus berbeda dari baseline hanya pada predikat itu (saya akan
mengekspor `prosrc` pre/post dan membandingkannya).


## 3a. F3 — halaman Nota Ambil Aksesori menolak seluruh bacaan bila ada mandor aktif ber-ID bukan RFC-4122 (INDEPENDENT_SOURCE_REVIEW)
Klaim writer (tabel kasus BC d385e7e, "lama; baru ditemukan, tidak diubah"). Verifikasi sumber:
- `src/accessoryIssue.ts:20` `accessoryUuid` = `/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i`; `list()` (baris ~33) melempar
  "Identitas aksesori tidak valid atau ganda." untuk **setiap** baris `contractors/locations/orders/materials/history` yang gagal → `parseAccessoryWorkspace` gagal total.
- Regex ini **tidak berubah** 4c61aca..95353aa (diff berkas hanya menambah FREE/rounding BC) → pre-existing (asal AP). ID mandor seed CP3
  `a1000000-0000-0000-0000-000000000001` (nibble versi 0, varian 0): uji Node — strict `false`, kanonik `true`. Tipe `uuid` Postgres menerimanya.
- **CONFIRMED, P3 (ketahanan halaman, fail-closed pada data sah).** Dampak nyata: rantai uji (mandor seed) dan data apa pun yang ID-nya bukan v1–v8/varian RFC;
  ID buatan aplikasi (`gen_random_uuid`) lolos. Efek samping untuk audit: writer menandai ACC-D09 (browser halaman nota) **terhalang F3** di rantai uji, jadi
  bukti browser halaman nota tidak bisa diambil selama guard ini ada.
- Saudara: `src/laundryQcModel.ts:123/151` memakai pola ketat yang sama ("… bukan UUID valid."); belum diuji, dicatat sebagai risiko sejenis.
- Pendapat auditor (bukan keputusan): perbaikan sempit = terima UUID kanonik seperti helper baru BC (`src/accessoryService.ts:58`, `src/initialImportBC.ts:5`);
  tanpa itu ACC-D09 tetap tanpa bukti browser. Keputusan di writer/owner.

## 3b. F4 — pelunasan saldo awal dari uang muka: bendera `reversible` NULL menyembunyikan seluruh batch impor (INDEPENDENT_NATIVE_RERUN)
Klaim writer (5e1ae83): cacat **BB** (ditemukan dari lanjutan ALL-A01), diperbaiki di BC. Skenario `audit/scenarios/round12_fable/xaudit_12_f4.py`
(sha256 `23a0b66a22bf2663bc2a70e7d13dbdc77df1cf9adffbd2b216788a3fd9e5faa8`; fixture memakai modul writer, pembacaan/oracle/predikat halaman milik auditor), head 0746c33:

| Run | Fase | Kasus | Hasil |
|---|---|---|---|
| 36171335601 | pre_bc (BB tanpa BC) | F4_ADVANCE_SETTLEMENT_FLAG | **COUNTEREXAMPLE**: pelunasan hutang awal 12.75 dari uang muka → `reversible: null`; predikat halaman (`src/initialImportBB.ts:98`) menolak batch |
| 36171335601 | pre_bc | F4_CASH_SETTLEMENT_CONTROL | PASS: pelunasan tunai → `reversible: true` |
| 36171347110 | after (dengan BC) | F4_ADVANCE_SETTLEMENT_FLAG | **PASS**: `reversible: false`, halaman menerima |
| 36171347110 | after | F4_CASH_SETTLEMENT_CONTROL | PASS: tetap `true` (coalesce BC tidak membalik nilai sah) |

Sumber: SQL BB (`…20bb…sql:1184`) `A and B and cash_account_id is not null or (POSTED and credit_kind in (...))` → tanpa akun kas dan tanpa baris kredit = `false or NULL` = NULL;
BC (`…20bc…sql:4165`) membungkusnya dengan `coalesce(…, false)`. **Klaim writer CONFIRMED; perbaikan CONFIRMED.**

**Koreksi laporan auditor:** `out/fable_r11_results.md` §6 menyatakan "BB tanpa cacat produk". Itu benar untuk kasus yang diuji (57 writer + 5 FAB), tetapi tidak
mencakup pelunasan saldo awal yang dibayar dari uang muka. F4 adalah cacat BB yang lolos dari putaran 11 (P2: halaman impor kosong untuk batch yang sah). Status
BB dikoreksi menjadi: **bersih pada kasus yang diuji; satu cacat (F4) ditemukan writer sesudahnya dan diperbaiki di BC**, diverifikasi independen di sini.

## 4. Cacat alat auditor (dicatat, tidak disembunyikan)
rev1 bentuk `cases()`; rev2 F1 tanpa savepoint; rev3 kunci kewajiban; rev4 nama kolom tabel fakta. Semua run tetap di ledger dan `audit/runs_fable/r12/`.

## 5. Yang sudah dicek dari commit writer (SOURCE_REVIEW)
- ab4ea6d: D06 dicatat verbatim (sha lampiran 42e04815…, OWNER_CONFIRMED_TO_AUDITOR), pertanyaan T3 ditulis ulang sesuai owner, kalimat lama "1 sen per PO" ditandai keliru. CONFIRMED.
- 4b1bd66: enam state ALL era BA (P01, A01 ×3, A02, W01, W03, C01 ×2) kini punya probe di `cp6_bc_probe.py` (butir 3b handoff). Baru teks; akan diuji di CI BC.
- 95353aa: workflow auditor berubah 4 baris (opsi `pre_bc`, deskripsi) + driver `cp6_auditor_scenario.py` memasang BC pada `after`. Runner/modes B1 tidak berubah.

## 6. Status
CP6 HOLD. Belum ada cacat produk baru di paket rilis; empat temuan writer terkonfirmasi independen (F4 = cacat BB, sudah diperbaiki di BC dan diverifikasi); tiga pre-existing lainnya: F1 (diperbaiki di BC, verifikasi menyusul), F2 (cacat detektor
lama, butuh disposisi tertulis, belum diperbaiki) dan F3 (guard UUID halaman nota, sumber; menghalangi bukti browser ACC-D09). Menunggu head final BC + tabel kasus + run CI dari writer untuk putaran 12 penuh.

---
# Fable — putaran 12 BC (head BC per §31 writer; produk `27e1a05`, paket DB `e21d15b`, tool head `23abac1`)

## 7. Identitas dan cara kerja putaran ini
- Writer menulis §31 di b7a1a2b ("head = commit yang memuat bagian ini"). Sesudahnya ia terus mendorong perbaikan **skrip uji** (browser nota D09, probe, alat rollback):
  `21ce322 … 23abac1`. Saya cek: `src` + `supabase` **identik sejak 27e1a05**; paket rilis `supabase/release` identik sejak e21d15b; runtime auditor (workflow, runner, modes,
  driver) identik sejak 95353aa. Karena itu dispatcher saya (`wf/pin_head.sh`) menerima head mana pun yang lolos tiga cek itu dan menolak bila produk berubah.
- Semua run putaran ini: INDEPENDENT_NATIVE_RERUN (dispatch sendiri, skenario sendiri atau PLAN writer di workflow pinned milik auditor). Bacaan log run writer diberi label REUSED_WRITER_EVIDENCE.

## 8. Rekonsiliasi bacaan GPT (`out/gpt_bc_20260926_initial_review.md`) dengan verifikasi Fable
| Klaim GPT | Verifikasi Fable | Status bersama |
|---|---|---|
| GPT-BC-01: filter cari tab Stok ikut menyaring Dokumen tanpa terlihat | Sumber pada 5e1ae83: `Documents` tidak punya kotak cari/status; head kini (27e1a05) punya kotak "Cari dokumen aksesori", status "Pencarian aktif…", tombol "Hapus pencarian" (diff 5e1ae83..27e1a05 menambah baris-baris itu). Writer mengakui di §31.3 butir 4. | **VALID pada 5e1ae83; DIPERBAIKI 27e1a05**; diuji ulang lewat browser lintas tab (menyusul) |
| GPT-BC-02: pembanding rollback dipersempit untuk baris seed | Sumber 9fb2473: hanya kolom `set_at` (settings) dan `id,set_at` (events) dua tabel seed yang dideklarasi registry, hanya pada cek `REINSTALL_*_SAME_AS_FIRST_INSTALL`; kolom lain tetap dibandingkan; assert tabel seed = registry. | **SETUJU: penyempitan sempit, terdokumentasi, dapat diterima**; run cycle 36172264420 (9fb2473) dan 36174363509 (21ce322) 135/135 = bukti writer; rerun auditor 36177907418 |
| ACC-C12 belum lengkap (barang sama) | Writer menambah `C12:SAME_GOODS_COUNTED_ONCE` (21ce322): saldo awal item sama ditolak, custody key sama ditolak, valuasi lot sama dua kali ditolak, pembelian baru +10; **batas**: custody key BARU untuk barang fisik yang mungkin sama diterima (sistem tidak punya identitas fisik). | **SETUJU dengan GPT: PARTIAL pada key baru**; bukan cacat kode, tetapi celah aturan → pertanyaan kebijakan owner (lihat §12) |
| ACC-D09 halaman nota belum terbukti; F3 | Sama (§3a). Writer menambah kasus browser D09 (21ce322) tetapi tiga rerun-nya merah di skrip (navigasi sesudah reload), 36177120018 lihat §9. | **SETUJU: belum PASS** |
| T2 27e1a05 per ID identik dengan fe226cf kecuali 1 | Writer §31.4a: `ACCESSORY_CONNECTED_ZERO` PASS→INCOMPLETE (nota harga manual 0 kini ditolak `BC_FREE_REQUIRES_POLICY`). Disposisi auditor di §10. | SETUJU |
| CodeQL 4 job sukses, jangan tulis "nol temuan" tanpa SARIF | Setuju; rerun auditor 36177919063. | SETUJU |

## 9. Run putaran 12 BC — semua INDEPENDENT_NATIVE_RERUN pada tool head 23abac1, produk 27e1a05 (19:09–19:25Z)
| Uji | Run | Hasil | Banding putaran 11 (BB final) |
|---|---|---|---|
| T2 gabungan | 36177884812 | 3/3 job sukses (status per ID: lihat §10 untuk satu-satunya perubahan) | identik kecuali `ACCESSORY_CONNECTED_ZERO` (§10) |
| T3 paket 27 berkas AC..BC | 36177895962 | 3/3 job sukses: install+verify+advisor+drill+gate, pins dicapture ulang = paket, browser AU | 26→27 berkas |
| T3 rollback (cycle auto) | 36177907418 | sukses | 131→135 cek (angka writer; log auditor dibaca status saja) |
| CodeQL 4 bahasa | 36177919063 | 4/4 job sukses (SARIF tidak dibaca; tidak mengklaim "nol temuan") | sama |
| xa1 | 36177930596 | 4/4 PASS | sama |
| xa2 | 36177941767 | 5/5 PASS | sama |
| xa7 | 36177953287 | 12/12 PASS | sama |
| xa8 rev4 | 36177965107 | 12 PASS + 2 COUNTEREXAMPLE beku (per-PO; T3-A: bukan cacat) | sama |
| xa9 | 36177978040 | 3/3 PASS | sama |
| open_1 | 36177989983 | 13/13 PASS | sama |
| C0 (GPT oracles) | 36178002278 | 24 PASS + 1 INCOMPLETE `G8C0:AS:ADJUSTMENT_DATE:False` (permission denied `get_owner_financial_snapshot_v2`: grant di skenario, bukan produk) | sama persis dengan r11 |
| xaudit_12_f1f2 rev5 (fase after = dengan BC) | 36178015645 | `BC_ABSENT` FAIL **sesuai desain penjaga** (BC memang terpasang); **F1 PASS** (baris harga manual lewat fasad tidak lagi ditandai → perbaikan F1 CONFIRMED natively); F2 3 COUNTEREXAMPLE seperti pra-BC (menunggu D07); kontrol + N3 PASS | F1 CE→PASS |
| Probe BC, PLAN writer 44 kasus, workflow pinned auditor | 36178145305 | before 33 NO_ROUTE + 3 CE + 8 PASS; **after 44/44 PASS**; mismatch {}; primary_unchanged | = run writer 36174363546 |
| Probe BC PLAN + 5 kasus Fable (rev1) | 36178552990 | after: FAB fill-sebelum-terima ditolak `AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY` PASS; pemakaian melebihi pos ditolak, tepat 20 diterima, +1 ditolak PASS; 6 bentuk qty tidak valid ditolak `BC_QTY_INVALID` PASS; pembalikan ganda: produk menolak `BC_ALREADY_REVERSED` dan buku pulih, **FAIL hanya pada pembanding stok auditor** (`'0'` vs `'0.000000'`); sidik jari: v265 BC = baseline + predikat harga manual saja (sha ternormalisasi sama), v255 identik. before: 4 INCOMPLETE = KeyError zona (alat auditor). Run beku apa adanya. | — |
| Probe BC PLAN + 5 kasus Fable (rev2) | **36179524130** | **before 33 NO_ROUTE + 3 CE + 9 PASS + 4 NO_ROUTE FAB (mismatch {}); after 49/49 PASS** (44 PLAN + 4 adversarial + sidik jari); primary_unchanged | run beku putaran ini untuk BC T1 |

Kesimpulan BC (T1 + gate), run beku 36179524130 + gate §9: **tidak ada cacat produk baru** pada kasus writer (44) maupun kasus auditor (4 adversarial + sidik jari). Yang masih terbuka: D09 browser
halaman nota (F3), D07 (F2), ACC-C12 key baru (kebijakan), `ACCESSORY_CONNECTED_ZERO` (disposisi §10 sudah ditulis, writer menambah kasus pengganti).

## 10. Disposisi T2 `ACCESSORY_CONNECTED_ZERO` (PASS → INCOMPLETE pada head BC)
Kasus AR lama mengharapkan nota mandor dengan harga eceran manual 0,00 terposting. ERP-DEC02 (M:1066) dan M:5023 butir B ("Jangan menjadikan gratis sebagai jalan untuk
melewati price validation Nota Mandor") menetapkan: nota harga 0 **bukan** cara gratis; jalur gratis yang sah = baris Special berbasis kebijakan owner. Penolakan
`BC_FREE_REQUIRES_POLICY` sesuai kontrak. **Disposisi: EXPECTED_CHANGE (bukan regresi).** Aturan beku: kasus T2 lama tetap tercatat INCOMPLETE dengan disposisi ini
(tidak dilabel ulang); writer menambahkan kasus pengganti di harness T2 yang mengunci penolakan (probe BC sudah punya `DEC02:MANUAL_ZERO_PRICE_REFUSED`) dan mencatat
kasus lama sebagai *superseded* di tabel kasus, bukan dihapus.

## 11. Tinjauan penyempitan pembanding rollback (§31.3 butir 7) — SOURCE_REVIEW
Lihat §8 baris GPT-BC-02. Tambahan: cek `<KEY>_SEED_CHANGED` / `<KEY>_SEED_NOT_PENDING` di berkas rilis tetap menjaga isi seed (7 baris, nilai kosong, versi 1); jadi yang
dikecualikan hanya jejak waktu pasang. Diterima; dicatat sebagai pengecualian eksplisit di register.

## 12. Pertanyaan kebijakan untuk owner (bukan blocker)
- **ACC-C12 key baru:** bila opname pembuka mencatat barang "pending nilai" tanpa identitas fisik, sistem tidak dapat membedakan pengajuan ulang barang yang sama dengan key
  baru dari barang baru. Pilihan: (a) wajibkan rujukan lembar hitung/lot sumber pada setiap item pending (sistem menolak key baru tanpa rujukan), atau (b) terima batas ini
  sebagai kontrol manual gudang dan catat di lampiran C6. Sampai diputuskan: ACC-C12 = PARTIAL.

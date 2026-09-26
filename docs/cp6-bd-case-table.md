# CP6 BD: tabel kasus → ID C6/ALL → oracle pra-kode

Label `WRITER_TABLE`, bukan bukti independen. CP6 tetap HOLD, `audit_complete=false`, `production_go=false`.

Family BD (`v2.6.20bd`, `supabase/dev/cp6_bd_t1_family.sql`) mencakup LAU-05b (harga paket, komponen dengan coverage sebagian, borongan per batch, minimum charge, tarif khusus model/ukuran/warna, invoice vendor laundry susulan), pengaturan kebijakan LAU-DEC01–06, dan bagian fisik ALL-W05 (klaim laundry dan penerimaan belum ditagih pada saat cutover).

## Sumber oracle pra-kode

Semua file ada di cabang auditor `audit/cp6-final-20260924-gpt-a0bcadf`:

| Singkatan | File | Cara merujuk |
|---|---|---|
| **F** | `out/fable_c6_75_oracles_pre_code.md` | bagian "#### LAU-Txx" |
| **G** | `out/r9_lau_oracle.md` | baris "LAU-Txx — M:43xx" pada matriks per kasus |
| **F22** | `out/fable_all22_oracles_pre_code.md` | bagian "### W05" |
| **G22** | `out/r9_all_oracle.md` | bagian "### ALL-W05" |
| **GBD** | `audit/scenarios/r13_bd/GPT_BD_ORACLE.md` | GBD-01..03 (dibekukan auditor GPT, lihat §GBD) |

Kutipan angka tiap oracle ada di docstring kasusnya (`scripts/cp6_bd_probe.py`, `scripts/cp6_bd_modes.py`, `scripts/cp6_bd_browser.mjs`). Bila dua oracle berbeda, dipakai bacaan yang lebih fail-closed. Semua nominal adalah fixture sintetis; tidak ada tarif vendor nyata yang dikarang.

Nilai kebijakan laundry tetap `PENDING_POLICY_VALUE` di produk (enam baris `erp.bd_policy_settings_v1`, versi 1). Pengaturan ini dibangun dan diuji (lampiran C6 rev4 §3). Kasus yang memerlukan kebijakan menetapkannya di dalam savepoint uji yang di-rollback, dan membuktikan bahwa tanpa nilai owner langkah keuangannya ditolak `BD_POLICY_PENDING`.

## Arti kolom *before*

*before* adalah hasil yang direncanakan pada rantai AN..BC tanpa BD:

- `NO_ROUTE`: facade BD (`erp_save_laundry_bd_action_v1` / `erp_get_laundry_bd_workspace_v1`) atau berkas impor BD belum dikenal, dan tidak ada yang berubah.
- `COUNTEREXAMPLE` (hanya D07): pada rantai tanpa BD, alarm v2.5.5 per gerakan berbunyi pada buku yang tepat. Itu temuan lama F2 yang diperbaiki D07.

Kolom *after* selalu `PASS`.

## T1 probe (`scripts/cp6_bd_probe.py`, 29 kasus, `.github/workflows/cp6-bd-t1-probe.yml`)

Sejak e49273f, setiap workspace BD, workspace impor, dan workspace Laundry/QC owner yang dibaca kasus disimpan lalu dijalankan lewat parser halaman sendiri (`scripts/cp6_bd_workspace_parse.mjs`: `src/laundryBd.ts`, `src/ConnectedInitialImportPage.tsx`, `src/laundryQcModel.ts`). Satu penolakan membuat fase INCOMPLETE. Pengecualian bernama hanya F3 (lihat §Temuan), dihitung terpisah sebagai `f3_seed_ids`.

| Kasus | ID | Oracle pra-kode | before |
|---|---|---|---|
| POLICY:LAU_DEC_SETTINGS_OWNER_VERSIONED_PENDING | LAU-DEC01–06 | lampiran C6 rev4 §3 (pengaturan, default `PENDING_POLICY_VALUE`); M:1757 | NO_ROUTE |
| T02:PACKAGE_ONE_CHARGE_PHYSICAL_QTY | LAU-T02 | F §LAU-T02; G LAU-T02 (M:4340) | NO_ROUTE |
| T03:COMPONENT_SUM_SAME_PIECES | LAU-T03 | F §LAU-T03; G LAU-T03 (M:4341) | NO_ROUTE |
| T04:FOUR_COMPONENTS | LAU-T04 | F §LAU-T04; G LAU-T04 (M:4342) | NO_ROUTE |
| T05:PARTIAL_COMPONENT_COVERAGE | LAU-T05 | F §LAU-T05; G LAU-T05 (M:4343) | NO_ROUTE |
| T06:PACKAGE_EXTRA_ONCE | LAU-T06 | F §LAU-T06; G LAU-T06 (M:4344) | NO_ROUTE |
| T07:VERSION_AFTER_POSTED_DELIVERY | LAU-T07, T14 (jalur BD) | F §LAU-T07, §LAU-T14; G (M:4345, M:4352) | NO_ROUTE |
| T08:BAD_NOMINAL_REFUSED | LAU-T08 (jalur BD) | F §LAU-T08; G (M:4346) | NO_ROUTE |
| T12:UNKNOWN_COMPONENT_KNOWN_SUBTOTAL | LAU-T12, T09, T34 | F §LAU-T12/T09/T34; G (M:4350, 4347, 4372); GBD-01 bagian A | NO_ROUTE |
| T13:NO_VERSION_IS_ERROR | LAU-T13 | F §LAU-T13; G (M:4351); GBD-01 bagian B | NO_ROUTE |
| T15:BD_RECEIPT_PROCESS_CHANGED | LAU-T15 (jalur BD) | F §LAU-T15; G (M:4353) | NO_ROUTE |
| T20:LUMP_SUM_SPLIT_RECEIPTS | LAU-T20, LAU-DEC01 | F §LAU-T20; G (M:4358) | NO_ROUTE |
| DEC01:MINIMUM_CHARGE_TOPUP | LAU-DEC01 | lampiran C6 rev4 LAU-DEC01 (M:4472) | NO_ROUTE |
| T24:SCOPED_SIZE_RATE | LAU-T24, T26, LAU-DEC05 | F §LAU-T24/T26; G (M:4362, 4364) | NO_ROUTE |
| T24:MULTI_SIZE_LOT_HPP | LAU-T24, T26, LAU-DEC05, LAU-T16 (HPP lot per ukuran) | F §LAU-T24/T26/T16; G (M:4362, 4364, 4354): satu kiriman BD dua ukuran (6 × 8.000 bertarif ukuran, 4 × 5.000 tarif dasar); tiap lot memakai laundry ukurannya sendiri (bukan rata-rata 6.800); selisih invoice 70.000 − 68.000 dibagi per potong baris penerimaan (1.200 dan 800) | NO_ROUTE |
| T32:REPLAY_ACCESS_GRANTS | LAU-T32, T33 (jalur BD) | F §LAU-T32/T33; G (M:4370–4371) | NO_ROUTE |
| T16:INVOICE_ABOVE_ESTIMATE_PRODUCT_COST | LAU-T16, T10 | F §LAU-T16/T10; G (M:4354, 4348) | NO_ROUTE |
| T17:PARTIAL_NM_CAPACITY | LAU-T17, T18, T19 | F §LAU-T17..T19; G (M:4355–4357); GBD-02 (bentuk, bukan angka; lihat §GBD) | NO_ROUTE |
| T21:DISCOUNT_TAX_ROUNDING | LAU-T21, LAU-DEC03 | F §LAU-T21; G (M:4359) | NO_ROUTE |
| DEC06:VARIANCE_ACCOUNT | LAU-DEC06 | lampiran C6 rev4 LAU-DEC06 (M:4477) | NO_ROUTE |
| T23:REVERSE_PAY_CORRECT | LAU-T23, LAU-DEC06 | F §LAU-T23; G (M:4361) | NO_ROUTE |
| DEC02:BILLABLE_CATEGORIES_ACCESS | LAU-DEC02 | lampiran C6 rev4 LAU-DEC02 (M:4473) | NO_ROUTE |
| T22:VARIANCE_TO_FG_AND_COGS | LAU-T22 | F §LAU-T22; G (M:4360) | NO_ROUTE |
| DEC04:SALE_UNKNOWN_LAUNDRY_PRICE | LAU-04, LAU-T34, LAU-DEC04 | F §LAU-T34; lampiran C6 rev4 LAU-DEC04 (M:4475) | NO_ROUTE |
| W05:OPENING_CUSTODY_CLAIM_SEPARATE | ALL-W05 | F22 §W05; G22 §ALL-W05; GBD-03 (struktur) | NO_ROUTE |
| W05:CLAIM_CONTINUATIONS | ALL-W05 | F22 §W05; G22 §ALL-W05 (lanjutan di jalur kanonik) | NO_ROUTE |
| W05:IMPORT_REFUSALS | ALL-W05 | G22 §ALL-W05 (negatif r9) | NO_ROUTE |
| W05:UNINVOICED_ACCRUAL_INVOICE | ALL-W05 | G22 §ALL-W05 (tanpa tagihan kedua; nilai unknown tetap pending dan menahan tutup buku) | NO_ROUTE |
| D07:RECOST_ALARM_DOCUMENT_LEVEL | D07 (bukan ID C6/ALL; handoff auditor R12 tugas 1) | usulan teknis auditor di handoff R12 §2 butir 1 (bukan rumus yang diratifikasi owner); lima jalur F2 `xaudit_12_f1f2.py` | COUNTEREXAMPLE (alarm berbunyi pada buku tepat di rantai BC) |

"Jalur BD" artinya kasus itu menguji ID tersebut untuk kiriman yang diberi harga BD. Perilaku ID yang sama untuk kiriman per PCS lama tetap BASELINE dan sudah punya bukti sendiri (lampiran C6 rev4 crosswalk).

## Race dua sesi dan HTTP Auth (`scripts/cp6_bd_modes.py`, runtime auditor fase `after`)

| Kasus | ID | Oracle pra-kode |
|---|---|---|
| BD_RACE:INV_TWO_POSTS_FIRST_COMMITS / _ABORTS | LAU-T19, T30 | F §LAU-T19/T30; dua invoice menagih 10 GOOD yang sama: sekali saja (`BD_INVOICE_CAPACITY`) |
| BD_RACE:W05_COMPLETE_VS_CLAIM_FIRST_COMMITS / _ABORTS | ALL-W05 | G22 §ALL-W05 ("return/klaim bersamaan pada PCS yang sama"); facade impor menolak seketika `POCKET_PERIOD_BUSY`, permintaan yang sama diulang: `STALE_VERSION` bila yang pertama commit, berhasil bila abort |
| BD_RACE:PRC_TWO_SETS_FIRST_COMMITS / _ABORTS | LAU-T12, T31 | F §LAU-T31; harga unknown ditetapkan sekali (`BD_PRICE_ALREADY_KNOWN`) |
| BD_RACE:POL_TWO_OWNER_SETS_SAME_VERSION | kebijakan (lampiran §3) | versi basi ditolak `STALE_VERSION` |
| BD_RACE:EST_INVOICE_VS_ESTIMATE_FIRST_COMMITS / _ABORTS | ALL-W05, LAU-T34 | G22 §ALL-W05; invoice atau estimasi, tidak pernah akrual pada record yang sudah ditagih (`BD_W05_ALREADY_BILLED`) |
| BD_HTTP:SET_POLICY_OWNER_ONLY | LAU-T33, kebijakan | lampiran C6 rev4 §3 (hanya owner; ADMIN `BD_OWNER_ONLY`, anon ditolak) |
| BD_HTTP:MONEY_HIDDEN_INVOICE_OWNER_ADMIN | LAU-T33, M:10.2 | F §LAU-T33; PRODUKSI_QC membaca workspace BD tanpa nominal dan tidak bisa membuat draf invoice; OWNER bisa |
| BD_HTTP:W05_CLAIM_OWNER_ADMIN_ONLY | ALL-W05, LAU-T33 | klaim saldo awal hanya owner/admin |

## Browser (`scripts/cp6_bd_browser.mjs`, runtime auditor mode browser)

| Kasus | ID | Oracle pra-kode |
|---|---|---|
| BD_BROWSER:OWNER_POLICY_SET_AND_CLEAR | kebijakan, LAU-DEC04 | lampiran C6 rev4 §3: tetapkan (SET, versi +1) lalu kembalikan ke `PENDING_POLICY_VALUE` (versi +2) dari tab "Harga & tagihan" |
| BD_BROWSER:W05_CLAIM_RECOVER_AND_REVERSE | ALL-W05 | F22 §W05: klaim 1 dari 8 potong tampil; pemulihan 1 dari halaman mengembalikannya ke sisa WIP (7 → 8); pembalikannya menahan lagi (8 → 7) |
| BD_BROWSER:W05_OPENING_ESTIMATE_QC_HIDDEN | ALL-W05, LAU-T33, LAU-T34 | G22 §ALL-W05: penerimaan lama bernilai unknown tampil "Belum diketahui" untuk PRODUKSI_QC tanpa input estimasi dan tanpa bagian invoice; estimasi owner 8.000,00 dari halaman membukukan akrual pembuka sekali dan mengangkat penahan tutup buku `BD_OPENING_LAUNDRY_PRICE_UNKNOWN` |

## GBD: oracle GPT BD yang dibekukan

Oracle `GPT_BD_ORACLE.md` ditulis auditor GPT dengan fixture dan assert auditor sendiri. Writer tidak menyesuaikan tes atau produk ke oracle itu; tabel ini hanya menunjukkan kasus writer yang menyentuh perilaku yang sama.

| GBD | Kasus writer terdekat | Catatan |
|---|---|---|
| GBD-01 unknown sengaja ≠ galat resolver | T12:UNKNOWN_COMPONENT_KNOWN_SUBTOTAL, T13:NO_VERSION_IS_ERROR, T32:REPLAY_ACCESS_GRANTS | Bentuk sama (A diterima sekali dengan kewajiban unknown dan penahan tutup buku; B ditolak atomik). Angka fixture berbeda |
| GBD-02 invoice parsial 40/60 dan n:m | T17:PARTIAL_NM_CAPACITY, BD_RACE:INV_TWO_POSTS_* | Writer memakai 6+4 PCS; GBD memakai 100+20 dan 40/60. Tidak diklaim sebagai hasil GBD |
| GBD-03 W05 fisik, klaim, credit | W05:* dan browser W05 | Struktur sama (hanya potongan yang masih di vendor menjadi WIP; klaim menahan potongannya; credit capped oleh utang vendor; inverse mengembalikan). GBD menandai representasi klaim lama `NEEDS_OWNER_INPUT`; writer tidak mengklaim ACCEPT penuh ALL-W05 sebelum keputusan tertulis owner |

## Tidak diklaim di BD

| ID | Letak |
|---|---|
| LAU-06b (celup ulang berbayar), bagian CR LAU-T28 | family BE |
| LAU-T01, T09–T11, T13–T15, T25, T27, T29–T31, T35 untuk kiriman per PCS lama | BASELINE (LAU-01..05a), bukti di rantai sebelumnya; lihat lampiran C6 rev4 crosswalk |
| LAU-T36 (UI desktop/HP, mixed coverage) | belum ada flow HP untuk tab BD; ditunda ke uji gabungan |
| ALL-C04 | family BE |

## Temuan dan perbaikan di BD

- **Kebocoran nominal (ditemukan dan diperbaiki sebelum commit W05/UI).** (1) `compensation_amount` klaim ikut di bagian baris WIP yang dibaca pemegang izin produksi; kini hanya di workspace impor owner/admin. (2) Nominal kiriman berharga dikirim ke semua pembaca laundry; kini `null` bila pembaca tidak punya izin uang. (1) dikunci probe `W05:CLAIM_CONTINUATIONS` (cek `production_reads_without_amounts`: bagian klaim di baris WIP dan di halaman status WIP tidak memuat kunci nominal apa pun sesudah kompensasi SETTLED 3,00, sedangkan workspace impor owner tetap memuat 3,00). Cek ini baru ditambahkan sesudah run 36189366030; sebelumnya kebocoran (1) hanya diperbaiki tanpa assert. (2) dikunci kasus HTTP `MONEY_HIDDEN_INVOICE_OWNER_ADMIN` dan browser `W05_OPENING_ESTIMATE_QC_HIDDEN`.
- **Parser Laundry/QC dan harga unknown (3460889).** Kiriman BD dengan harga komponen unknown membawa tarif/biaya estimasi `null`; parser halaman menolak seluruh workspace. Kini tampil "Belum diketahui"; string yang dipaksakan tetap ditolak.
- **F3 di halaman Laundry (run 36190024230).** Parser workspace Laundry/QC menolak seluruh bacaan bila ada ID non-RFC-4122. Di salinan auditor, mandor seed CP3 ber-ID `a1000000-0000-0000-0000-000000000001` memiliki batch siap kirim, sehingga halaman Laundry menampilkan "Data belum tersedia". Ini temuan lama yang sama dengan F3 di BC (halaman nota), direproduksi lokal pada rantai BC dan BD, dan bukan disebabkan BD. Guard UUID tidak dilonggarkan. Yang diubah (fec17f1): tab "Harga & tagihan" membaca workspace-nya sendiri, jadi tidak lagi menunggu workspace Laundry/QC; hanya bagian "Kirim dengan harga" (butuh batch siap kirim) yang terkunci sampai workspace Laundry/QC terbaca. Flow browser mencatat keadaan bacaan Laundry/QC (`laundry_qc_read`) sebagai observasi, bukan syarat lulus; run 36206435863 mencatat "ID Mandor bukan UUID valid.". Di cek parser probe, model seed CP3 (`a2000000-…`) juga non-RFC; file Laundry/QC dihitung F3 hanya bila lolos setelah setiap ID non-RFC ditulis ulang ke bentuk RFC (versi 4, varian 8, digit lain tetap), sehingga semua baris tetap diparse.
- **`released` tanpa dua desimal (cacat BD, diperbaiki e49273f).** Workspace BD owner dan workspace impor mengirim `released: "0"` untuk record saldo awal yang belum dilepas. Parser nominal halaman menolak seluruh bacaan, jadi bagian "Laundry saldo awal" tidak tampil untuk owner (browser `W05_OPENING_ESTIMATE_QC_HIDDEN` INCOMPLETE di run 36206435863; PRODUKSI_QC tidak terdampak karena nominal disembunyikan). Server kini mengirim `::numeric(18,2)::text`; parser tidak diubah. Cacat ini lolos dari probe karena probe BD belum menjalankan parser halaman; cek itu kini ada (lihat §T1 probe). Negatif kontrol: file yang sama dengan `released: "0"` ditolak.
- **Fixture HTTP (run 36190024230).** `bdp.fixture` membuat pembelian lewat jalur owner di schema privat, yang ditolak salinan HTTP (sengaja tanpa USAGE schema `erp` untuk `authenticated`, seperti produksi). Kini grant itu hanya ada di dalam transaksi fixture dan dicabut sebelum commit (atau ikut rollback); kasus memeriksa tidak ada grant yang ter-commit sebelum dan sesudahnya. Oracle dan nilai harapan tidak berubah.
- **Race pertama (lokal, bukan bukti).** W05 FAIL karena oracle mengira kunci menunggu, padahal facade impor menolak seketika (`POCKET_PERIOD_BUSY`); W05 abort ERROR karena nama merek fixture dipakai ulang lintas salinan yang di-commit. Keduanya diperbaiki di skrip uji saja. Log: `bd/races_first_run_failures.md` di scratchpad writer, dicatat di pesan commit 898def1.
- **Probe W05 (lokal).** Kasus lanjutan klaim sempat ERROR `BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING`: klaim dibuka pada hari kasus dan dibatalkan pada hari bisnis nyata, sehingga potongan memang tertahan pada hari kasus. Tes diperbaiki untuk menyelesaikan WIP pada hari bisnis nyata, dan ditambah cek bahwa penyelesaian sehari sebelumnya ditolak. Produk tidak diubah.

## Batas yang diketahui (jujur)

- **Tagihan potongan hilang.** Potongan yang hilang ditangani lewat alur klaim (kompensasi AP_VENDOR / OTHER_EXPENSE, dibatasi utang vendor), bukan sebagai baris invoice.
- **HPP lot multi-ukuran.** Kini punya kasus sendiri (`T24:MULTI_SIZE_LOT_HPP`): satu grup potong dua ukuran, satu kiriman dan satu penerimaan BD, dua lot barang jadi. Batas yang tersisa: selisih invoice (`bd_product_variance_v1`) dibagi rata per potong baris penerimaan, tidak menurut tarif ukuran. Untuk selisih 2.000 pada 6 + 4 potong, lot mendapat 1.200 dan 800 (bukan 48/68 dan 20/68 dari 2.000). Aturan pembagian itu belum diputuskan owner; dicatat, tidak diubah.
- **Guard invoice L8.** `erp.guard_cp6_vendor_invoice_receipt_on_post_v2620` diganti dengan satu substitusi yang diperiksa: utang yang diposting facade invoice BD dicek terhadap dokumen BD-nya (vendor dan total sama, ada baris), bukan terhadap `vendor_invoice_items` baseline. Invoice lain dicek seperti sebelumnya. Karena ini mengubah guard lama, dicatat terbuka untuk ditinjau auditor.
- **Kiriman berharga** dikirim dari tab "Harga & tagihan" (bagian "Kirim dengan harga"), bukan dari tab "Kirim ke Laundry". Tab lama menolak vendor/proses yang butuh harga BD dengan `BD_PRICING_REQUIRED` dan menunjuk ke tab itu.

## Run (head writer)

Diisi di §32.6 `docs/cp6-au-r1-handoff.md` (head, identitas, dan log gagal).

# CP6 BC: tabel kasus → ID C6/ALL → oracle pra-kode (ronde 11 butir 4)

Label `WRITER_TABLE`, bukan bukti independen. CP6 tetap HOLD, `audit_complete=false`, `production_go=false`.

## Sumber oracle pra-kode

Kedua file ada di cabang auditor `audit/cp6-final-20260924-gpt-a0bcadf`:

| Singkatan | File | Cara merujuk |
|---|---|---|
| **F** | `out/fable_c6_75_oracles_pre_code.md` | bagian "#### ACC-xx" |
| **F22** | `out/fable_all22_oracles_pre_code.md` | bagian "### Pxx/Axx/Wxx/Cxx" |
| **G** | `out/r9_acc_oracle.md` | baris ACC-xx pada §A–§D |
| **G22** | `out/r9_all_oracle.md` | bagian "### ALL-xx" |

Kutipan angka tiap oracle ada di docstring kasusnya (`scripts/cp6_bc_probe.py`, `scripts/cp6_bc_modes.py`,
`scripts/cp6_bc_browser.mjs`). Bila dua oracle berbeda, dipakai bacaan yang lebih fail-closed.

Nilai kebijakan aksesori tetap `PENDING_POLICY_VALUE` di produk. Pengaturan ini dibangun dan diuji (lampiran C6 rev4 §3). Tidak ada angka yang diisi sebagai nilai bawaan. Kasus yang memerlukan kebijakan menetapkannya di dalam savepoint uji yang di-rollback. Kasus itu juga membuktikan bahwa tanpa nilai owner transaksinya ditolak `BC_POLICY_PENDING`.

ACC-C06..C08 (ganti merek) milik family BE dan tidak diklaim di sini.

## Arti kolom *before*

*before* adalah hasil yang direncanakan pada rantai AN..BB tanpa BC:

- `NO_ROUTE`: facade atau berkas impor BC belum dikenal, dan tidak ada yang berubah.
- `COUNTEREXAMPLE`: cacat yang diperbaiki BC masih terlihat.
- `PASS`: jalurnya sudah ada sebelum BC.

Kolom *after* selalu `PASS`.

## T1 probe (`scripts/cp6_bc_probe.py`, 44 kasus, `.github/workflows/cp6-bc-t1-probe.yml`)

| Kasus | ID | Oracle pra-kode | before |
|---|---|---|---|
| B01:FILL_POST_KEEPS_TOTAL | ACC-B01 | F §ACC-B01; G §B (M:5267) | NO_ROUTE |
| B02:USE_95_RETURN_25 | ACC-B02 | F §ACC-B02; G §B (M:5268) | NO_ROUTE |
| B03:DIRECT_USE_PURPOSE_ACCOUNT | ACC-B03, ACC-DEC04 | F §ACC-B03; G §B (M:5269); lampiran C6 rev4 ACC-DEC04 | NO_ROUTE |
| B04:BACKDATED_TRANSFER_LATE_INVOICE | ACC-B04 | F §ACC-B04; G §B (M:5270) | NO_ROUTE |
| B05:LOCATION_AND_BYPASS_REFUSED | ACC-B05, ACC-DEC07 | F §ACC-B05; G §B (M:5271) | NO_ROUTE |
| B06:LINE_DAYS_AND_UNKNOWN_VARIANCE | ACC-B06 | F §ACC-B06; G §B (M:5272) | NO_ROUTE |
| B07:END_TO_END_RECONCILES | ACC-B07 | F §ACC-B07; G §B (M:5273) | NO_ROUTE |
| C01:RECEIVE_100_CLASSIFY_80_20 | ACC-C01 | F §ACC-C01; G §C (M:5279) | NO_ROUTE |
| C02:PARTIAL_INSPECTIONS_CAPPED | ACC-C02 | F §ACC-C02; G §C (M:5280) | NO_ROUTE |
| C03:USED_SOURCE_NEW_KEY_REFUSED | ACC-C03 | F §ACC-C03; G §C (M:5281) | NO_ROUTE |
| C04:THREE_SOURCES_SEPARATE | ACC-C04 | F §ACC-C04; G §C (M:5282) | NO_ROUTE |
| C05:NO_VALUE_STAYS_PENDING | ACC-C05, ACC-DEC03 | F §ACC-C05; G §C (M:5283) | NO_ROUTE |
| C09:PAID_NOTE_RETURN_POLICY | ACC-C09, ACC-DEC05 | F §ACC-C09; G §C (M:5287) | NO_ROUTE |
| C10:CUSTOMER_GARMENT_CUSTODY | ACC-C10, ACC-DEC04 | F §ACC-C10; G §C (M:5288) | NO_ROUTE |
| C11:TWO_REAL_TIMELINES | ACC-C11, ACC-DEC01 | F §ACC-C11; G §C (M:5289) | NO_ROUTE |
| C12:OPNAME_BASELINE_INCOMPLETE_SOURCE | ACC-C12 | F §ACC-C12; G §C (M:5290) | NO_ROUTE |
| C12:SAME_GOODS_COUNTED_ONCE | ACC-C12 | tinjauan GPT BC butir 3; F §ACC-C12 (barang yang sama dihitung sekali) | NO_ROUTE |
| A08:REPEATED_PARTIAL_RETURNS_CENTS | ACC-A08 | F §ACC-A08; G §A (M:5261) | NO_ROUTE |
| D05:REPLAY_SAME_KEY | ACC-D05 | F §ACC-D05; G §D (M:5300) | NO_ROUTE |
| D06:ACCESS_DENIED_BY_SERVER | ACC-D06 | F §ACC-D06; G §D (M:5301) | NO_ROUTE |
| D07:MID_COMMAND_FAILURE_ROLLS_BACK | ACC-D07 | F §ACC-D07; G §D (M:5302) | NO_ROUTE |
| D08:WIB_DATES_SEPARATE | ACC-D08 | F §ACC-D08; G §D (M:5303) | NO_ROUTE |
| D12:SERVER_PAGINATION | ACC-D12 | F §ACC-D12; G §D (M:5307) | NO_ROUTE |
| POLICY:SETTINGS_OWNER_VERSIONED_PENDING | ACC-DEC01, 03–07, ERP-DEC02 | lampiran C6 rev4 §3 (pengaturan, default `PENDING_POLICY_VALUE`) | NO_ROUTE |
| DEC07:APPROVAL_THRESHOLD_ZONE_USERS | ACC-DEC07 | lampiran C6 rev4 ACC-DEC07 (M:4461) | NO_ROUTE |
| DEC02:SPECIAL_FREE_LINE | ERP-DEC02 | lampiran C6 rev4 ERP-DEC02 | NO_ROUTE |
| DEC02:MANUAL_ZERO_PRICE_REFUSED | ERP-DEC02 | M:5023; nota 0 bukan cara gratis | COUNTEREXAMPLE |
| DEC06:ROUNDING_LINE | ACC-DEC06 | lampiran C6 rev4 ACC-DEC06 (M:4460); nominal resmi tetap (ACC-A08) | NO_ROUTE |
| F1:MANUAL_PRICE_PROVENANCE_DETECTOR | ACC-01 (temuan F1) | M:1066 (harga eceran manual sah) | COUNTEREXAMPLE |
| F4:ADVANCE_SETTLEMENT_REVERSIBLE_READ | ALL-A01 (temuan F4) | F22 §A01; kolom `reversible` selalu ya/tidak agar parser halaman impor tidak menolak batch | COUNTEREXAMPLE |
| REV:LINKED_INVERSE_MATRIX | ACC-B*, C* (M:6.3) | M:6.3, M:8.4 (pembalikan tertaut) | NO_ROUTE |
| ALL:C02_OLD_NOTE_PARTLY_PAID_RETURN | ALL-C02 | F22 §C02; G22 §ALL-C02 | NO_ROUTE |
| ALL:C02_IMPORT_REFUSALS | ALL-C02 | F22 §C02; G22 §ALL-C02 | NO_ROUTE |
| ALL:C03_CUSTODY_STATES | ALL-C03 | F22 §C03; G22 §ALL-C03 | NO_ROUTE |
| ALL:C03_IMPORT_REFUSALS | ALL-C03 | F22 §C03; G22 §ALL-C03 | NO_ROUTE |
| L:P01_RECEIPT_UNBILLED_PART_CONSUMED | ALL-P01 | F22 §P01; G22 §ALL-P01 | PASS |
| L:A01_SUPPLIER_ADVANCE | ALL-A01 | F22 §A01 (tabel M:634–643); G22 §ALL-A01 | PASS |
| L:A01_CUSTOMER_ADVANCE | ALL-A01 | sama | PASS |
| L:A01_VENDOR_ADVANCE | ALL-A01 | sama | PASS |
| L:A02_CASH_ADVANCE_PAYROLL | ALL-A02 | F22 §A02; G22 §ALL-A02 | PASS |
| L:W01_OPEN_PO_HEADER | ALL-W01 | F22 §W01; G22 §ALL-W01 | PASS |
| L:W03_OPENING_BS | ALL-W03 | F22 §W03; G22 §ALL-W03 | PASS |
| L:C01_STOCK_NOTE_ROUTE | ALL-C01 | F22 §C01; G22 §ALL-C01 | PASS |
| L:C01_STOCK_COMPANY_USE | ALL-C01 | G22 §ALL-C01 (pemakaian perusahaan) | NO_ROUTE |

Kasus `L:` menjawab ronde 11 butir 3b. Keenam keadaan era-BA (P01, A01, A02, W01, W03, C01) masing-masing diimpor, dilanjutkan lewat jalur nativenya, lalu dibalik. Dengan itu 20 dari 22 ALL punya bukti run penuh:

- P02, P03, P04, S01, S02, S03, A03, Y01, Y02, W02, W04, dan W06 dari BB;
- C02 dan C03 dari BC;
- enam keadaan era-BA di atas.

Dua sisanya belum penuh:

- W05 = PARTIAL. Bagian finansial ada di BB; bagian fisik menyusul di BD.
- C04 belum punya jalur; menyusul di BE.

Kasus `L:C01_STOCK_COMPANY_USE` berstatus NO_ROUTE sebelum BC karena pemakaian perusahaan baru ada di facade BC.

Pemeriksaan halaman ikut dalam run yang sama. Semua baca workspace (impor, Gudang · Aksesori, nota) disimpan, lalu dijalankan melalui parser halaman sendiri (`scripts/cp6_bc_workspace_parse.mjs`). Temuan F3 dihitung terpisah (lihat §Temuan).

## Race dua sesi dan HTTP Auth (`scripts/cp6_bc_modes.py`, runtime auditor fase `after`)

| Kasus | ID | Oracle pra-kode |
|---|---|---|
| BC_RACE:D01_TWO_USES_FIRST_COMMITS / _ABORTS | ACC-D01 | F §ACC-D01 (stok 7, dua sesi 4); G §D (M:5296) |
| BC_RACE:D02_FILL_VS_NOTE_FIRST_COMMITS / _ABORTS | ACC-D02 | F §ACC-D02; G §D (M:5297) |
| BC_RACE:C02_TWO_INSPECTIONS_FIRST_COMMITS / _ABORTS | ACC-C02 (+D) | F §ACC-C02; kode tolak sama dengan probe C02 (`BC_INSPECT_EXCEEDS_WAITING`) |
| BC_RACE:RET_TWO_NOTE_RECEIPTS_FIRST_COMMITS / _ABORTS | ACC-C03 (+D) | F §ACC-C03 (kapasitas sumber) |
| BC_RACE:D04_CREDIT_FIRST_THEN_PAYROLL / D04_PAYROLL_FIRST_THEN_CREDIT | ACC-D04, ACC-DEC05 | F §ACC-D04; G §D (M:5299) |
| BC_RACE:POL_TWO_OWNER_SETS_SAME_VERSION | kebijakan (lampiran §3) | versi basi ditolak `STALE_VERSION` |
| BC_HTTP:FILL_POST_STOCK_ADJUST_ONLY_VALUES_HIDDEN | ACC-D06, M:10.2 | F §ACC-D06; G §D (M:5301) |
| BC_HTTP:SET_POLICY_OWNER_ONLY | ACC-D06, kebijakan | lampiran C6 rev4 §3 (hanya owner) |

## Browser (`scripts/cp6_bc_browser.mjs`, runtime auditor mode browser)

| Kasus | ID | Oracle pra-kode |
|---|---|---|
| BC_BROWSER:FILL_POST_AND_REVERSE | ACC-B01, ACC-D09 | F §ACC-B01; F §ACC-D09 (UI) |
| BC_BROWSER:NOTE_PAGE_D09_DESKTOP_PHONE | ACC-D09 | F §ACC-D09; tinjauan GPT BC butir 2 (reload, klik ganda, hasil kosong, galat baca, memuat, HP) |
| BC_BROWSER:POLICY_SET_AND_CLEAR_BY_OWNER | kebijakan | lampiran C6 rev4 §3 |
| BC_BROWSER:IMPORT_PAGE_OPENING_ACCESSORIES | ALL-C03 | F22 §C03 (kategori tidak dijumlah menjadi satu stok siap) |

## Tidak diklaim di BC

| ID | Letak |
|---|---|
| ACC-C06, C07, C08 | family BE (ganti merek + aksesori) |
| ACC-D03, D10 | nota (ACC-01, BASELINE), di luar CR BC |
| ACC-D11 | paket T3 berkas ke-27 dan rollback BC: lihat §Run |

## Temuan

- **F1** (lama; diperbaiki N9): nota berharga eceran manual memicu detektor CRITICAL v265.
- **F2** (lama; tidak diubah): v255 `MATERIAL_RECOST_GL_STATE_DRIFT` sudah basi sejak 20t dan BA W8. Kasus yang melakukan recost memeriksa buku = subledger sebagai gantinya.
- **F3** (lama; baru ditemukan, tidak diubah): halaman Nota Ambil Aksesori menolak seluruh bacaan bila ada mandor aktif yang ID-nya bukan RFC-4122. Di rantai uji, ini terjadi karena mandor seed CP3 ber-ID `a1000000-0000-…`. Akibatnya halaman kosong dengan pesan galat. Server menyimpan tipe `uuid`, jadi ID itu sah. Guard lama tidak dilonggarkan dan diserahkan ke owner/auditor. Parser BC yang baru menerima semua teks UUID kanonik.
- **F4** (baru; cacat BB, diperbaiki di BC): pelunasan saldo awal yang dibayar dari uang muka impor tidak punya akun kas dan tidak punya baris kredit. Akibatnya `erp.bb_financial_workspace_v1` mengirim `reversible = false OR NULL`, yaitu `null`. Halaman impor menolak flag yang bukan boolean, sehingga seluruh batch tidak terlihat. Temuan ini muncul dari parse halaman atas workspace kasus `L:A01_*` dan bisa direproduksi tanpa BC. BC mengganti fungsi itu dengan satu substitusi yang diperiksa (`coalesce(..., false)`); teks pendahulunya diverifikasi sama dengan BB. Kasus `F4:ADVANCE_SETTLEMENT_REVERSIBLE_READ`: COUNTEREXAMPLE sebelum BC, PASS sesudah. Parse probe menghitung penolakan F4 terpisah hanya di fase before, dan menolaknya di fase after.
- **Batas C12** (dicatat, tidak ditutupi): baris tertunda impor dengan kunci custody baru diterima sebagai barang terpisah (tetap tertunda, di luar stok). Server tidak dapat membedakan barang fisik yang sama bila sumbernya memberi kunci baru; yang dijaga: opening kedua bahan yang sama ditolak (`BA_IMPORT_OPENING_ALREADY_POSTED`), kunci custody yang sama ditolak (`BC_C03_DUPLICATE`), dan nilai lot yang sama hanya sekali (`BC_QTY_EXCEEDS_BUCKET`).
- **ACC-C12 kunci baru: dua opsi untuk owner (handoff auditor R12 tugas 4).** GPT mereproduksi batas di atas (3 → 6 → 9: baris tertunda yang sama diimpor ulang dengan kunci custody baru dan terhitung lagi). Status ACC-C12 tetap **PARTIAL** sampai owner memilih salah satu:
  - **(a) Rujukan lembar hitung/lot wajib.** Setiap baris tertunda impor wajib membawa rujukan lembar hitung atau nomor lot sumber. Server menolak kunci baru tanpa rujukan, dan menolak rujukan yang sama bila dipakai lagi dengan kunci lain untuk barang yang sama. Akibatnya: data cutover harus dilengkapi rujukan sebelum diimpor. Baris lama tanpa rujukan tidak bisa masuk sampai dilengkapi. Writer menambah kolom, guard, dan kasus probe (reproduksi 3 → 6 → 9 berubah menjadi penolakan).
  - **(b) Kontrol manual gudang + catatan di lampiran C6.** Server tetap menerima kunci baru seperti sekarang. Gudang mencocokkan daftar tertunda dengan lembar hitung fisik sebelum dan sesudah impor. Lampiran C6 mencatat bahwa server hanya menjaga kunci yang sama, opening kedua, dan nilai lot; identitas fisik lintas kunci dijaga prosedur gudang. Kode tidak berubah; risiko hitung ganda bergantung pada disiplin prosedur itu.
- **Fixture D09:** di salinan disposable, enam mandor seed CP3 dengan ID bukan RFC-4122 dinonaktifkan hanya selama kasus `NOTE_PAGE_D09_DESKTOP_PHONE`, lalu diaktifkan lagi. Guard UUID halaman tidak diubah; F3 tetap tercatat.
- **Catatan D04** (koreksi laporan writer): hasil race D04 yang sempat disebut cacat BC ternyata bukan cacat. Sesi kedua memakai snapshot basi, lalu ditolak benar oleh guard kasbon. Kasus sekarang memakai anggaran payroll 100 dan mengulang populate bila ditolak.

## Run (head writer)

| Uji | Run | Head | Hasil |
|---|---|---|---|
| Probe BC (before + after, dengan cek parser halaman) | 36168802591 | 5e1ae83 | sukses: 43 kasus; `NO_ROUTE`/`COUNTEREXAMPLE` sesuai rencana di fase before, `PASS` di fase after. SQL produk dan probe tidak berubah sesudah head ini |
| Race 11, HTTP 2, browser 3 | 36171707986 (auditor scenario, `phase=after`) | 27e1a05 | 16/16 PASS, `RUN_COMPLETE`, 0 galat konsol |
| Probe BC dengan C12:SAME_GOODS_COUNTED_ONCE (before + after) | 36174363546 | 21ce322 | sukses: 44 kasus sesuai rencana |
| Race 11, HTTP 2, browser 4 (termasuk D09) | 36178858173 (auditor scenario, `phase=after`) | 62d05c4 | 17/17 PASS, `RUN_COMPLETE`, 0 galat konsol. D09: reload tidak menyimpan apa pun (0 nota, stok 20, form kosong); klik ganda menghasilkan satu nota 7 PCS (stok 13); hasil kosong tampil; galat baca tampil sebagai alert beserta pemberitahuan data belum dimuat ulang, tombol sahkan terkunci; bacaan yang ditahan menonaktifkan 'Muat ulang'; halaman pulih; HP menghasilkan nota 7 PCS kedua (stok 6) |
| Rollback: cycle dengan diff baris seed (GPT-BC-02) | 36174363509 | 21ce322 | 135/135 PASS; reinstall BC dibanding per (policy_key, version): kunci sama, beda hanya di kolom waktu pasang (`set_at`, dan `id` pada event) |
| Paket T3 (install, verify, advisor, drill) | 36174363719 | 21ce322 | sukses |
| CodeQL kandidat | 36174371647 | 21ce322 | sukses |
| T2 gabungan | 36171725748 | 27e1a05 | 3/3 job sukses. Per ID dibanding head BB final (run 36141237920): 326 asli + AS 34 = 422 status sama; AT 16 + AU 15 = 41 sama; AR 174: satu berubah, `ACCESSORY_CONNECTED_ZERO` PASS → INCOMPLETE, disengaja (ERP-DEC02, lihat §Disposisi T2) |
| Paket T3: capture pin | 36168802454, job 108183850580 | 5e1ae83 | 27/27 berkas `CAPTURED_AND_INSTALLED`; blob `b469a5ab…` |
| Paket T3: install 27 berkas, verify, advisor, drill restore, cek data | 36170892085 | e21d15b | `ALL_STAGES_INSTALLED`; advisor +92 INFO saja, gate `true`; drill `RESTORED_SAME_MEANING`; UUID `CLEAN` |
| Paket T3: pin dicapture ulang dan dibandingkan dengan paket | 36170892085 | e21d15b | sama |
| Rollback: capture | 36170892127, job 108189867439 | e21d15b | `CAPTURED`; blob `f9eeb8d3…` |
| Rollback: cycle | 36172264420 | 9fb2473 | 135/135 PASS: penolakan salah urutan dan admission terbuka, dua cycle BC..AC, reinstall sama dengan pasang pertama, 27 penolakan pasca-pakai; `primary_unchanged` |

Log gagal tetap disimpan di Actions:

- **36168808537:** browser `FILL_POST_AND_REVERSE` INCOMPLETE. Chromium menormalkan jam `09:00:00` dan Playwright menolak pengisian. Kesalahan skrip uji, diperbaiki di 792251f.
- **36170901705:** browser `FILL_POST_AND_REVERSE` INCOMPLETE. Tab Dokumen menyaring dengan pencarian stok tanpa menampilkannya. Cacat UI BC, diperbaiki di 27e1a05.
- **36171280254:** cycle rollback pertama gagal satu cek, `REINSTALL_BC_SAME_AS_FIRST_INSTALL`: baris seed kebijakan membawa waktu pasang dan id event baru. Pembanding disesuaikan secara sempit di 9fb2473; cek lain, termasuk 27 penolakan pasca-pakai, PASS.
- **36174368419, 36175345878, 36176077431, 36177120018, 36177813548:** kasus browser `NOTE_PAGE_D09_DESKTOP_PHONE` INCOMPLETE/FAIL berturut-turut karena skrip uji: halaman tidak disimpan di URL sehingga perlu dibuka lagi sesudah reload; pencarian terkunci sesudah galat baca sehingga perlu 'Muat ulang' dulu; route yang ditahan dilepas bersamaan dengan unroute (`Route is already handled`); dua alert sah (galat dan data belum dimuat ulang) sementara locator mengharapkan satu; `isVisible()` tidak menunggu hasil kosong. Tidak ada perubahan produk; kasus lain di run itu PASS.
- **36168802454:** job capture paket gagal dengan `T3_COMMITTED_PACKAGE_STALE` (differ `['BC']`). Ini memang yang diharapkan sebelum pin baru di-commit.

## Disposisi T2

Satu kasus lama berubah karena BC: `AR_SEQUENTIAL / ACCESSORY_CONNECTED_ZERO`, PASS → INCOMPLETE (run 36171725748).

- **Isi kasus:** nota aksesori dengan harga eceran manual 0,00 (`scripts/cp6_accessory_issue_trial.py`).
- **Sesudah BC:** ditolak `BC_FREE_REQUIRES_POLICY: harga eceran 0 hanya lewat gratis Special yang ditetapkan owner (ERP-DEC02)`.
- **Dasar:** keputusan owner ERP-DEC02 di lampiran C6 rev4 dan M:5023: nota harga 0 bukan cara gratis. Jalur gratis yang sah adalah baris Special. Perilaku yang sama dikunci kasus probe `DEC02:MANUAL_ZERO_PRICE_REFUSED` (COUNTEREXAMPLE sebelum BC, PASS sesudah).
- **Yang tidak diubah:** oracle, harness, dan hasil lama kasus itu. Perubahan ini dicatat untuk disposisi auditor, tidak diserap ke hitungan.

Verdict job regresi tetap `DISPOSITION_REQUIRED`, sama seperti head BB final, karena kasus AS historis (8 COUNTEREXAMPLE, 1 INCOMPLETE). Itu tidak terkait BC.

**Status kasus lama: *superseded*** (disposisi auditor R12 §1: `EXPECTED_CHANGE`, ERP-DEC02, M:5023 B). `AR_SEQUENTIAL / ACCESSORY_CONNECTED_ZERO` tetap tercatat INCOMPLETE apa adanya; berkas harness lama tidak diubah. Penggantinya grup T2 baru `AR_SUPERSEDING / ACCESSORY_CONNECTED_ZERO_REFUSED_BC_FREE_POLICY` (`scripts/cp6_t2_regression.py`): fixture yang sama dari harness lama, baris nota harga manual 0,00 diposting, harus ditolak `BC_FREE_REQUIRES_POLICY` dengan batas dan buku tidak berubah. Run lokal (LOCAL_PG16_DEV, bukan bukti): PASS; run CI dicatat di handoff §32.

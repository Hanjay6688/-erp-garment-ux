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

## T1 probe (`scripts/cp6_bc_probe.py`, 43 kasus, `.github/workflows/cp6-bc-t1-probe.yml`)

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

Kasus `L:` menjawab ronde 11 butir 3b. Keenam keadaan era-BA (P01, A01, A02, W01, W03, C01) masing-masing diimpor, dilanjutkan lewat jalur nativenya, lalu dibalik. Dengan itu 22/22 ALL punya bukti run:

- P02, P03, P04, S01, S02, S03, A03, Y01, Y02, W02, W04, W06, dan W05 (finansial) dari BB;
- C02 dan C03 dari BC;
- enam keadaan era-BA di atas;
- W05 fisik dan C04 menyusul di BD dan BE.

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
| BC_BROWSER:POLICY_SET_AND_CLEAR_BY_OWNER | kebijakan | lampiran C6 rev4 §3 |
| BC_BROWSER:IMPORT_PAGE_OPENING_ACCESSORIES | ALL-C03 | F22 §C03 (kategori tidak dijumlah menjadi satu stok siap) |

## Tidak diklaim di BC

| ID | Letak |
|---|---|
| ACC-C06, C07, C08 | family BE (ganti merek + aksesori) |
| ACC-D03, D10 | nota (ACC-01, BASELINE), di luar CR BC |
| ACC-D09 | halaman nota: terhalang F3 di rantai uji; parsernya diuji vitest dan parse probe |
| ACC-D11 | paket T3 berkas ke-27 + rollback (menunggu capture pin) |

## Temuan

- **F1** (lama; diperbaiki N9): nota berharga eceran manual memicu detektor CRITICAL v265.
- **F2** (lama; tidak diubah): v255 `MATERIAL_RECOST_GL_STATE_DRIFT` sudah basi sejak 20t dan BA W8. Kasus yang melakukan recost memeriksa buku = subledger sebagai gantinya.
- **F3** (lama; baru ditemukan, tidak diubah): halaman Nota Ambil Aksesori menolak seluruh bacaan bila ada mandor aktif yang ID-nya bukan RFC-4122. Di rantai uji, ini terjadi karena mandor seed CP3 ber-ID `a1000000-0000-…`. Akibatnya halaman kosong dengan pesan galat. Server menyimpan tipe `uuid`, jadi ID itu sah. Guard lama tidak dilonggarkan dan diserahkan ke owner/auditor. Parser BC yang baru menerima semua teks UUID kanonik.

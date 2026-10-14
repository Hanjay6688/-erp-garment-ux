# Run pertama dengan penjaga bertanggal (commit `597d6778`) — kegagalan yang disimpan

Commit `597d67784830e71ef140280a6f3d8d858f5a8e0e` memasang tiga penjaga baru (D14-2 upah tidak dibayar sebelum
utangnya ada, D14-3 kas/bank tidak boleh minus, FIN02 klaim laundry tidak mendahului sumber/utang vendor). Run
pertamanya **gagal**; kegagalan ini disimpan apa adanya, tidak di-retry dan tidak ditutup dengan melonggarkan penjaga.

## Penyebab yang sama di semua job merah

Semua kasus yang gagal ditolak oleh `cp7_guard.guard_cash_line()` (`CP7_CASH_NEGATIVE`): data uji membayar dari bank
fixture yang baru dibuat **kosong** (`cp6_bc_probe.fixture` / `bank_account`, docstring-nya sendiri: "no balance is
imported"), jadi saldo turun di bawah nol pada tanggal bayar. Setiap kekurangan sama dengan nominal bayar (saldo awal 0).
Tidak ada penolakan dari tiga penjaga lain di log mana pun. Ini akibat yang memang dikehendaki D14-3: skenario lama
"bayar dari bank kosong" kini dilarang; yang salah adalah fixture-nya, bukan penjaganya.

Contoh pesan pertama (job 116005626798):

```
CP7_CASH_NEGATIVE: saldo BC bank (BC2CCA5DBD5B) menjadi minus -400.00 pada tanggal 2026-10-15 atau sesudahnya. Kas/bank tidak boleh minus; catat dulu uang masuk atau pilih rekening lain.
CONTEXT:  PL/pgSQL function cp7_guard.guard_cash_line() line 11 at RAISE
SQL statement "insert into erp.journal_lines(...)"
PL/pgSQL function post_journal(text,uuid,date,text,jsonb) line 103 at SQL statement
PL/pgSQL function post_supplier_payment(uuid) line 18 at PERFORM
```

| Workflow (run) | Job | Kasus tidak PASS | Titik bayar dari bank kosong |
|---|---|---|---|
| CP7 P18 Full Cycle (38608544677) | 116005628257 | `P18_FULL_CYCLE_STOCK_WIP_HPP_GL_PAYABLES_CASH`, `P18_E13_LATE_SUPPLIER_PRICE_AFTER_FULL_CYCLE` | `cp7_p18_full_cycle_cases.py` `cycle()` bayar supplier 400 (−200 sesudah kas pelanggan 200) |
| CP7 P21 Rehearsal (38608544230), job pasang/rollback | 116005627215 | langkah USE | `cp7_p21_rehearsal_probe.py:124` bayar supplier 100 |
| CP7 P21 Rehearsal (38608544230), job komposisi penuh | 116005626889 | langkah USE | `cp7_p21_full_rehearsal_probe.py:250` bayar supplier 100 |
| CP7 Supplier Payment Create (38608544388) | 116005626798 | 9 dari 10 (semua kecuali `REFUSALS_ZERO_EFFECT`), termasuk 2 browser | `cp7_supplier_payment_create_cases.fixture` |
| CP7 Supplier Payment Correction (38608596332) | 116005814085 | 23 dari 23 | `cp7_supplier_payment_correction_cases.fixture` (pembayaran asal), bank `SUPEDIT-*` |
| CP7 Owning Receipt Correction (38608544658) | 116005629192 | 7 dari 37 native (`RF_SUPPLIER_TYPO`, `RF_PAYMENT_REPLAY`, `RF_PAID_EXCEEDS_CORRECTED_REFUSED`, `RF_OVERPAID_CREDIT_TO_NEXT_NOTA`, `RF_OPENING_ADVANCE_PAYMENT_REPLAY`, `RF_INVOICED_QTY_DOWN_WITH_PAYMENT`, `RF_SHARED_INVOICE_CORRECTED`) | `bc.fixture(...)` + `bc.supplier_payment` |
| CP7 Pre-freeze UI Regression (38608600115) | 116005824078 | 3 dari 31 browser: `BD_BROWSER:D12_PAYMENT_SCREEN_DAILY_CLAIM`, `BD_BROWSER:D12_PAYMENT_SCREEN_OPENING_CLAIM`, `BD_BROWSER:DEC06_CORRECTION_UP_DOWN_ON_SCREEN` | `cp6_bd_browser.mjs`: bayar kas 8.000.000 / 7.000 dari bank fixture sisa tahap lain yang saldonya 0 |

| CP7 P18 Fabric Rule (38608610910), job rule-lifecycle16 | 116005858491 | `P16_LIFECYCLE_PAID_AND_PAYMENT_INVERSE` | `cp7_payable_condition_cases.payment()`: bank baru kosong tiap panggilan, bayar 500 |
| CP7 F03 Full (38608586848) / p09 | 116005783118 | `P09_RECEIPT_REVERSE_PAYMENT` | `cp7_receipt_reversal_cases.payment_dependency` bayar 20 |
| CP7 F03 Full / p12 | 116005783231 | settlement native 4, race 1, HTTP 1, browser settlement/attendance-write/opening, `P12_OPENING_LIFECYCLE` | `cp7_settlement_cases.cash()` (bank `P12…L` kosong), bayar upah 6000–6125 |
| CP7 F03 Full / cash_installments | 116005783342 | misc 2 native + race + HTTP + browser; E05 16 native, 3 race, HTTP, browser | misc: rekening kas pertama (CASH-MAIN) kosong, biaya 12,34; E05: `cp7_installment_cases.fixture` (`cash()`), cicilan 600 dst. |
| CP7 F03 Full / supplier_credit | 116005782993 | `F03_P09_NATIVE_PAID_SUPPLIER_CREDIT_CARRY` + 2 browser | `cp6_bf_supplier_probe.fixture` (bank kosong), bayar 80 (+100 dibalik) |

Job lain pada commit yang sama yang hijau: P13 Finance, P12 Payroll (paket tanpa penjaga kas), Astra Timeline Reuse,
Note Correction, CodeQL, F03 Full p10/p11/p13/customer_refund, P18 Fabric Rule job fabric-rule11 dan p18-e01-9. Run
yang belum selesai saat catatan ini ditulis (P19 transport, P08, PL Native, Shell S0) dibaca di run berikutnya.

## Perbaikan fixture (bukan perbaikan penjaga)

Satu cara untuk semua: bank fixture yang membayar lebih dulu menerima **modal pemilik** lewat jurnal Native yang sudah
diterima (`erp.post_journal`, Dr bank / Cr `OPENING_EQUITY`), bertanggal pada atau sebelum pembayarannya:
`scripts/cp7_cash_funding.py` (Python) dan `ui.fund` di `scripts/cp6_auditor_browser_host.mjs` (browser).

- Semua angka hasil yang lama tetap: oracle kas di suite-suite ini adalah **perubahan** saldo, dan modal dicatat sebelum
  titik awal pengukuran (P18: sebelum snapshot awal; angka −200/−800/−1100/−1200 tetap sebagai perubahan, bank akhir
  100 dan 0).
- Tempat yang diisi modal: `cp7_supplier_payment_create_cases.funded()`, P18 `cycle()` (1.200 sebelum snapshot awal),
  `cp7_supplier_payment_correction_cases.fixture()` (pembayaran + 1.000 ruang koreksi; bank pengganti 1.000),
  `cp7_receipt_correction_cases.paying_bank()`, `cp7_payable_condition_cases.payment()`, `cp7_receipt_reversal_cases`
  (sebelum pembanding buku besar), `cp7_settlement_cases.cash()` (1.000.000 sejak tanggal buka paling awal;
  `cash(cur,None)` tetap kosong), `cp7_installment_cases.fixture()` (persis net payroll), `cp7_misc_cases.fixture()`
  (1.000 di rekening kas yang dipilih), `cp7_f03_supplier_credit_cases` (CP6 `cp6_bf_supplier_probe` tidak diubah;
  fixture-nya dibungkus), browser `cp6_bd_browser.mjs` lewat `ui.fund` baru di host browser.
- `cp7_supplier_payment_create_cases.fixture()` tanpa modal **tetap memberi bank kosong** (saksi Sol `SOL_CASH_*`
  memakainya dan memeriksa saldo 0); suite memakai `funded()`.
- Penolakan bank kosong sendiri dibuktikan oleh kasus tersendiri di suite perbaikan CP1–CP7, bukan dihapus.

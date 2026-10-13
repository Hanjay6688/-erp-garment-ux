# F-PAY-01: tanggal bayar gaji WIB, kedua cabang zona aktif (butir A4)

Catatan Astra (retest `7a0b4a90`): pada jam run Astra hanya zona yang harinya tertinggal dari WIB yang aktif. Cabang zona
yang sudah "besok" (`session_day_ahead_of_wib_refuses_wib_tomorrow`) tidak aktif, jadi tidak diklaim PASS.

Kasus `P12_SETTLEMENT_WIB_PAYMENT_DATE` (`scripts/cp7_settlement_cases.py`) memakai dua zona sesi:

- UTC−12, yang harinya tertinggal dari WIB sebelum 19.00 WIB;
- UTC+14, yang harinya sudah "besok" sejak 17.00 WIB.

Kedua cabang hanya aktif bersamaan pada pukul 17.00–19.00 WIB (10.00–12.00 UTC). Karena itu workflow didispatch tepat
pukul 10.00 UTC pada commit kandidat. Kode dan oracle tidak diubah.

| Hal | Nilai |
|---|---|
| Commit kandidat | `ae0214ad33184f7c2724783d663fb20fcb13820c` |
| Workflow / run / job | `CP7 P12 Payroll (Claude branch)`, run 38380339961 (didispatch 10:00:13 UTC), job 115238908371 `P12 payroll --payroll-review` |
| Baris kasus | 10:06:19 UTC (17:06 WIB) |
| `session_day_behind_wib_accepts_wib_today` | **true**: zona tertinggal aktif, tanggal WIB hari ini diterima |
| `session_day_ahead_of_wib_refuses_wib_tomorrow` | **true**: zona "besok" aktif, tanggal WIB besok ditolak ("masa depan") |
| `no_partial_write_on_refusal` | true |
| Batas | `full_boundary_restored`, `public_schema_unchanged`, tanpa kebocoran sesi |
| Suite | `CP7_P12_NATIVE_SETTLEMENT` PASS, 8/8 kasus settlement, `cp6_restored`, `advisor_gate` |
| Log | `p12_payroll_review_ae0214ad_run38380339961_job115238908371.log` (21 baris JSON dari log job, tanpa perubahan) |

Ini bukti writer (WRITER_CROSSCHECK), bukan penerimaan auditor. Astra boleh menjalankan ulang kasus yang sama pada
pukul 17.00–19.00 WIB.

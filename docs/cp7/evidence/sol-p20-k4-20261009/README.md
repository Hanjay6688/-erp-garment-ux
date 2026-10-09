# Kegagalan pertama — audit independen Sol atas `8cc1b081` (9 Okt 2026)

Audit gabungan P20 + K4 oleh Sol (cabang `audit/sol-p20-k4-8cc1b081-20261009`, `audit/sol_p20_k4/REPORT.md`,
`WRITER_HANDOFF.md`, `FINDINGS.json`): F01–F05 PASS, regresi 71/71 PASS, PR44 235 perbandingan PASS; **HOLD** pada satu
temuan baru. Kegagalan pertama dijalankan dan disimpan auditor; folder ini hanya menunjuk ke sana, tidak menyalin atau
mengedit.

| Temuan | Run auditor (kegagalan pertama) | Kasus |
|---|---|---|
| SOL-K4-01 S2 — heartbeat penjalan pertama kali dibuat: giliran server kedua menunggu transaksi giliran pertama (`transactionid` ShareLock) | [37954533118](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37954533118) (kernel PostgreSQL), [37954972794](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37954972794) (paket ERP lengkap) | `SOL_COLD_START` (kontrol `SOL_WARM_START` lulus) |

Dampak menurut auditor: penundaan awal bila dua pemanggil server berjalan bersamaan; tidak ada duplikasi, salah hitung,
kehilangan output atau macet permanen.

Perbaikan writer: `cp7_analysis_stage.run_next()` — hanya giliran yang mendapat kunci privat heartbeat tanpa menunggu
(`pg_try_advisory_xact_lock`) yang menulis baris penjalan; giliran lain melewati heartbeat dan langsung ke job-nya. Kasus
writer baru `K4R_RACE_COLD_START_TWO_TICKS` (suite `k4-runner-17`). Di salinan lokal (bukan bukti) writer menjalankan
`audit/sol_p20_k4/cold_runner.py` tanpa diubah: gagal pada sumber `8cc1b081` (`COLD_SECOND_TICK_NO_HEARTBEAT_WAIT`,
`transactionid`) dan lulus 8/8 pada sumber perbaikan; kasus writer baru juga gagal pada sumber lama dan lulus pada yang
baru. Uji penutup tetap milik auditor.

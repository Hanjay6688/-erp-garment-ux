# Kegagalan pertama P20 — audit independen atas `2e605bb7` (9 Okt 2026)

Kegagalan pertama untuk temuan F01–F05 dijalankan dan disimpan oleh auditor, bukan writer. Log aslinya ada di run CI
dan di cabang audit `audit/astra-p20-2e605bb7-20261009` (commit `56689b95eea3397146fdbc9d965dbb4a123bbc50`,
`audit/astra_p20/REPORT.md`, `WRITER_HANDOFF.md`). Folder ini hanya menunjuk ke sana; isinya tidak disalin atau diedit.

| Temuan | Run auditor (kegagalan pertama) | Kasus |
|---|---|---|
| F01 BLOCKER kapasitas lintas versi (61 dari 60) | [37879134926](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37879134926), job `113654511340` | `AS20-32_CROSS_VERSION_CAPACITY` |
| F02 MAJOR bersyarat nama cron lintas database | [37877803025](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37877803025) | `AS20-43_CRON_DATABASE_ISOLATION` |
| F03 MINOR receipt backup tertimpa di detik yang sama | [37877803025](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37877803025) | `AS20-45_FAILED_RETRY_COLLISION` |
| F04 MINOR batas detektor verifier pembersihan | [37877802981](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37877802981) | `AS20-39_VALIDATION_NEGATIVE` |
| F05 MINOR gate bukti (`NameError p19_plan_v2`) | [37878853771](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37878853771), job `113653612762`; lanjutan [37879768174](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37879768174) | `cp7_probe_evidence_test.py` |

Perbaikan writer ada di `870d4f79` (`../../audit-candidate/revision-p20-20261009/`). Writer mencoba ketiga balapan
F01 baru pada apply v1 lama di salinan PostgreSQL lokal dan ketiganya gagal (tidak ada tunggu kunci bersama); hasil
lokal itu **bukan bukti** dan tidak disimpan sebagai log. Kualifikasi `870d4f79` (15/15 workflow, 43/43 job) tidak
mencatat kegagalan baru. Penerimaan tetap menunggu uji ulang auditor.

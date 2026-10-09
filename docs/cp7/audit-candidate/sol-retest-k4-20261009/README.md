# Kandidat revisi K4 — perbaikan SOL-K4-01 (9 Okt 2026)

Audit independen Sol atas kandidat gabungan `8cc1b081` (cabang `audit/sol-p20-k4-8cc1b081-20261009`,
`audit/sol_p20_k4/REPORT.md`, `WRITER_HANDOFF.md`, `FINDINGS.json`): F01–F05 PASS, regresi 71/71 PASS, PR44 235 perbandingan
PASS, K4 fungsi utama PASS; **HOLD** pada satu temuan baru SOL-K4-01 (S2). Paket ini adalah kandidat revisi untuk uji ulang
temuan itu. Kandidat `8cc1b081` (`../final-p20-k4-20261009/`), kandidat sebelumnya dan semua bukti kegagalan tetap disimpan dan
tidak diubah. Tidak ada push ke cabang audit, `cp7/integration`, `main`, deployment, atau Supabase hosted; tidak ada jadwal
atau backup yang dipasang di database sungguhan. `production_go:false`.

## Identitas kandidat revisi

- **Commit sumber: `8116800c0586cfb27bd6c7d206d1b176666c9839`**, tree `12b81da97f5260596d2384765dd5e2d877e6c80f`, cabang `claude/new-session-deapao`.
- Selisih dari `8cc1b081` per berkas (status, ukuran, SHA-256 sebelum/sesudah): `SOURCE_DELTA.json` — 13 berkas (6 baru, 7 berubah, 0 dihapus; 4 bukan dokumen).
- Commit dokumentasi sesudah `8116800c` tidak mengubah sumber (`git diff --name-only 8116800c HEAD` hanya `docs/`).

## CI pada satu commit (`CI_RECEIPT.json`)

Ke-15 workflow kualifikasi cabang Claude dijalankan pada `8116800c` (push + `workflow_dispatch` tanpa commit baru):
**15/15 workflow dan 44/44 job sukses**, termasuk suite `k4-runner-17` (workflow CP7 P08 Physical Fabric pada percobaan ke-2; lihat Kegagalan pertama). Bukti writer (WRITER_CROSSCHECK), bukan
penerimaan auditor.

## Temuan dan perbaikannya

| Temuan | Perbaikan | Bukti writer di `8116800c` |
|---|---|---|
| **SOL-K4-01 S2** — pada instalasi baru (baris `cp7_analysis_stage.runner` belum ada), INSERT heartbeat giliran pertama yang belum commit membuat giliran server kedua menunggu (`transactionid` ShareLock) sebelum memilih job | `cp7_analysis_stage.run_next()`: hanya giliran yang mendapat kunci privat heartbeat **tanpa menunggu** (`pg_try_advisory_xact_lock(hashtextextended('CP7:K4_RUNNER_HEARTBEAT',0))`) yang menulis baris penjalan, pertama kali maupun sesudahnya; kunci dipegang sampai akhir transaksinya sehingga tidak ada penulis baris lain yang sedang berjalan. Giliran lain melewati heartbeat dan tetap memilih job. Kunci itu hanya untuk heartbeat, bukan untuk pekerjaan penjalan. Pemeriksaan isolasi dan batas 8 dtk, kunci per job (`skip locked`), identitas aktor dan pemulihan klaim tidak berubah; tidak ada waktu heartbeat palsu. | Kasus baru `K4R_RACE_COLD_START_TWO_TICKS` (tabel penjalan kosong, dua job, dua giliran bersamaan: keduanya berada di dalam unitnya pada saat yang sama, tidak ada yang menunggu `transactionid`, tiap unit tersimpan sekali, satu baris heartbeat). Suite `k4-runner-17` (dari 16); `K4R_RACE_TWO_TICKS_ONE_UNIT` (hangat) tetap. |

Di salinan lokal (bukan bukti) writer menjalankan `audit/sol_p20_k4/cold_runner.py` milik auditor **tanpa diubah**: gagal
pada sumber `8cc1b081` (`COLD_SECOND_TICK_NO_HEARTBEAT_WAIT`, `transactionid`) dan lulus 8/8 pada sumber revisi; kasus writer
baru juga gagal pada sumber lama dan lulus pada yang baru. Uji penutup tetap milik auditor (`cold_runner.py`,
`scripts/sol_p20_k4_installed_probe.py`).

## Kegagalan pertama

`../../evidence/sol-p20-k4-20261009/README.md` — run auditor 37954533118 (kernel) dan 37954972794 (paket ERP lengkap).
Kualifikasi `8116800c`: satu kegagalan, bukan karena perubahan K4. Percobaan pertama `attention284` (workflow CP7 P08 Physical Fabric, run 37958882487) berjalan 23.33–00.08 WIB dan melewati tengah malam: tanggal 'hari ini' fixture browser diambil saat setup (9 Okt) sedangkan server sudah 10 Okt, sehingga enam kasus browser pengingat/laporan kewajiban ditolak (`CP7_NOTA_AFTER_PERIOD`, hitungan '2' vs '1'). Baris aslinya disimpan di `../../evidence/sol-p20-k4-20261009/01_attention284_wib_midnight_first_attempt.log`; job yang gagal dijalankan ulang pada commit yang sama (percobaan ke-2, sesudah tengah malam) dan lulus. Suite yang sama lulus pada `8cc1b081`. Cacat waktu di alat uji ini (tanggal diambil sekali saat setup) dicatat sebagai pekerjaan alat uji terpisah; tidak ada pemeriksaan yang dilonggarkan.

## Yang tetap terbuka (bukan temuan baru)

- Belum diuji ulang auditor: 5.000 target diselesaikan seluruhnya oleh penjalan server K4; HP fisik/Safari; tab HP benar-benar
  ditutup.
- Pemasangan jadwal (pembersihan, hapus 7 hari, penjalan) dan backup malam di database sungguhan menunggu penerimaan, izin
  owner, tujuan backup di luar runner yang konkret, dan konfigurasi nyata.
- `independent_acceptance=false`, `installed_P21_acceptance=false`, `production_go=false`.

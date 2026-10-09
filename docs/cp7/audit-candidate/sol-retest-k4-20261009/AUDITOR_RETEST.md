# Uji ulang SOL-K4-01 — kandidat revisi `8116800c` (sesi auditor terpisah)

Dokumen ini untuk **auditor di sesi terpisah**, bukan writer. Audit Sol atas `8cc1b081` memberi putusan HOLD hanya karena
SOL-K4-01 (S2). Handoff auditor: "jalankan `cold_runner.py` dan `sol_p20_k4_installed_probe.py` pada SHA revisi baru. Cold dan
warm sama-sama harus mencapai langkah masing-masing tanpa menunggu heartbeat, tiap job/unit tetap disimpan sekali,
actor/claims dipulihkan, akses berubah tetap membatalkan unit. ... Jalankan regresi K4 + staged + K3 pada SHA itu. Temuan
kapasitas yang tidak berubah tidak perlu dibuka kembali tanpa delta baru."

## Paste block untuk membuka sesi auditor

> Kamu auditor independen CP7 ERP Garment (repo `Hanjay6688/-erp-garment-ux`, cabang `claude/new-session-deapao`). Kandidat
> revisi adalah commit sumber `8116800c0586cfb27bd6c7d206d1b176666c9839` (tree `12b81da97f5260596d2384765dd5e2d877e6c80f`), tercatat di
> `docs/cp7/audit-candidate/sol-retest-k4-20261009/CI_RECEIPT.json`. Uji commit itu, bukan HEAD lain; commit sesudahnya hanya
> dokumen — buktikan sendiri dengan `git diff --name-only 8116800c HEAD` (semua harus di bawah `docs/`). Baca
> `docs/AUDIT_PANDUAN_PRO_MAX.md`, laporan dan handoff audit Sol di cabang `audit/sol-p20-k4-8cc1b081-20261009`
> (`audit/sol_p20_k4/REPORT.md`, `WRITER_HANDOFF.md`, `FINDINGS.json`), lalu `README.md` dan `AUDITOR_RETEST.md` di folder paket
> revisi. Uji ulang SOL-K4-01 dengan uji penutup auditor sendiri (`audit/sol_p20_k4/cold_runner.py`,
> `scripts/sol_p20_k4_installed_probe.py`) pada SHA revisi, ditambah regresi K4, analisis bertahap dan K3 yang terdampak.
> Selisih sumber dari `8cc1b081` ada di `SOURCE_DELTA.json`. Batas: jangan mengubah `main`, deployment Cloudflare, Supabase
> hosted Enteng (`siimvrusnzxexizpyoib`), legacy ERP-Garment (`vlxdhpkjeevubjxexnfo`, read-only) atau produksi; jangan push ke
> `claude/new-session-deapao`, `cp7/integration` atau cabang audit lama (pakai cabang audit baru); jangan memasang jadwal
> pg_cron atau backup malam di database mana pun selain salinan sekali pakai; jangan mengirim pesan ke orang lain; jangan
> meminta password/token/kunci; jangan melonggarkan oracle/guard; simpan log gagal pertama. Keputusan owner yang sudah
> disahkan tidak dibuka ulang. `production_go:false` tetap.

## Yang diuji ulang

| Temuan | Kriteria retest (handoff Sol) | Yang berubah di `8116800c` | Titik awal (bukan bukti lulus) |
|---|---|---|---|
| SOL-K4-01 S2 | Cold dan warm: giliran kedua mencapai langkahnya tanpa menunggu heartbeat; tiap job/unit disimpan sekali; actor/claims dipulihkan; akses berubah tetap membatalkan unit | `scripts/cp7-src/planning/analysis-stages.sql` (`run_next`: penulis heartbeat dijaga `pg_try_advisory_xact_lock`, giliran lain melewati heartbeat); kasus `K4R_RACE_COLD_START_TWO_TICKS`; suite `k4-runner-17` | `cold_runner.py` (writer lokal: gagal di `8cc1b081`, lulus 8/8 di revisi — bukan bukti), `scripts/cp7_k4_runner_cases.py` |

## Regresi yang mungkin terdampak

- K4 seluruhnya (`k4-runner-17`), terutama heartbeat/status `server_runner` (aktif hanya sesudah giliran nyata; tidak ada waktu
  palsu), batas 8 dtk, identitas dan pemulihan klaim, akses berubah di tengah unit, pg_cron sungguhan.
- K3 (`k3-cleanup-19`): penjalan ada di daftar jadwal yang sama; pembersihan tetap menunda selama analisis bergerak.
- Analisis bertahap (`p19-staged12`) dan yang membacanya.
- Area lain yang tidak disentuh `SOURCE_DELTA.json` boleh tidak diulang; tulis BELUM DIULANG, bukan LULUS.

## Hasil yang diminta

1. SOL-K4-01: DITUTUP / MASIH TERBUKA, dengan run, kasus dan oracle auditor.
2. Regresi: LULUS / GAGAL / BELUM DIULANG, dengan alasan.
3. Temuan baru bila ada (ID, keparahan, reproduksi, bukti, dampak).
4. Vonis kandidat dan syarat sebelum owner memberi izin memasang jadwal (pembersihan, hapus 7 hari, penjalan) dan backup malam.

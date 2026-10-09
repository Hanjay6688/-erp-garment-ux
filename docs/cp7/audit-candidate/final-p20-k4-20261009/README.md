# Kandidat audit gabungan — revisi P20 + K4 (9 Okt 2026)

Owner 9 Okt: "kerjain dl aja nnti audit nya sekalian semua". Paket ini adalah **satu kandidat untuk satu putaran audit**:
perbaikan temuan audit P20 F01–F05 (kandidat revisi `870d4f79`, `../revision-p20-20261009/`) ditambah K4, penjalan server
untuk analisis bertahap (keputusan owner 8 Okt butir 6). Kandidat `870d4f79`, `2e605bb7`, `976f4c43`, `9d57b7f5` dan
semua bukti kegagalan tetap disimpan dan tidak diubah. Tidak ada push ke cabang audit, `cp7/integration`, `main`,
deployment, atau Supabase hosted; tidak ada jadwal atau backup yang dipasang di database sungguhan. `production_go:false`.

## Identitas kandidat

- **Commit sumber: `8cc1b0818fdba54f3ebeb64e132f7f3e20309e24`**, tree `2ea854abca572afa923297b0c304e92703ede136`, cabang `claude/new-session-deapao`.
- Selisih dari kandidat yang diaudit P20 `2e605bb7` (status, ukuran, SHA-256 sebelum/sesudah per berkas):
  `SOURCE_DELTA.json` — 44 berkas (16 baru, 28 berubah, 0 dihapus; 25 bukan dokumen).
- Selisih dari kandidat revisi `870d4f79` (hanya K4 dan dokumen): `SOURCE_DELTA_FROM_REVISION.json` — 23 berkas (10 baru, 13 berubah, 0 dihapus; 13 bukan dokumen).
- Commit dokumentasi sesudah `8cc1b081` tidak mengubah sumber (`git diff --name-only 8cc1b081 HEAD` hanya `docs/`).

## CI pada satu commit (`CI_RECEIPT.json`)

Ke-15 workflow kualifikasi cabang Claude dijalankan pada `8cc1b081` (push + `workflow_dispatch` tanpa commit baru):
**15/15 workflow dan 44/44 job sukses**. Suite baru `k4-runner-16` ada di workflow `CP7 P19 Analysis Job Transport`.
Ini bukti writer (WRITER_CROSSCHECK), bukan penerimaan auditor.

## Isi 1 — perbaikan temuan P20 (tidak berubah sejak `870d4f79`)

Lihat tabel temuan → perbaikan → bukti di `../revision-p20-20261009/README.md` dan petunjuk uji ulang
`../revision-p20-20261009/AUDITOR_RETEST.md`. Berkas temuan yang ikut disentuh K4 sesudahnya: daftar jadwal
`cp7_ops.schedules()` (F02) kini berisi tiga entri (ditambah `cp7-staged-runner`), sehingga deklarasi K3 dan ekspektasi
kasus K3 ikut mencantumkan entri itu; probe `scripts/cp7_f05_analysis_probe.py` mendapat flag `k4_runner` (gate F05 membaca
semua flag dari signature, jadi ikut diperiksa). Tidak ada pemeriksaan K3 atau F05 yang diubah atau dilonggarkan.

## Isi 2 — K4: analisis bertahap berjalan di server

Keputusan owner 8 Okt butir 6: "arah akhirnya berjalan di server, supaya tetap lanjut saat halaman ditutup. Membuka ulang
harus melanjutkan job yang sama, bukan menghitung ulang atau menggandakan pekerjaan." Deklarasi: `../../k4/K4_RUNNER.json`.

| Syarat | Penerapan | Bukti writer di `8cc1b081` |
|---|---|---|
| Lanjut saat halaman ditutup | Jadwal `cp7-staged-runner` (pg_cron tiap menit): `set statement_timeout to '8s'` lalu 60 kali `begin; select cp7_ops.analysis_tick(); commit;`. Tiap giliran: `cp7_analysis_stage.run_next()` mengambil job RUNNING dengan kemajuan paling lama yang tidak dipegang sesi lain dan menjalankan SATU unit lewat `step()` yang sama dengan halaman. | `K4R_SERVER_FINISHES_WITHOUT_PAGE` (hasil = jalur tunggal pada acuan yang sama), `K4R_RACE_PG_CRON_FINISHES_JOB` (pg_cron sungguhan), `K4R_HTTP_CLOSED_PAGE_FINISHES`, `K4R_BROWSER_DESKTOP/MOBILE_CLOSED_PAGE_FINISHES` |
| Buka ulang = job yang sama, tidak menggandakan | Kunci baris job (halaman yang melangkah saat server memegang job mendapat `worker_active`, dan sebaliknya), kunci utama unit; UUID permintaan yang sama memberi job dan run yang sama. | `K4R_PAGE_AND_SERVER_ONE_JOB`, `K4R_RACE_PAGE_AND_SERVER_ONE_UNIT`, `K4R_RACE_TWO_TICKS_ONE_UNIT`; browser: tanpa request/step baru saat dibuka ulang |
| Batas 8 dtk per unit tidak dilonggarkan | Giliran ditolak (`55000 CP7_RUNNER_STATEMENT_LIMIT_REQUIRED`) bila `statement_timeout` sesi tidak di-set atau lebih dari 8 dtk; unit yang dihentikan batas = percobaan, tiga kali = job gagal `CP7_ANALYSIS_STAGE_STOPPED`, sama dengan halaman. | `K4R_LIMIT_REQUIRED`, `K4R_RACE_LIMIT_STOPS_THEN_CONTINUES` |
| Hak aktor diperiksa ulang tiap unit | Tanpa sesi login: selama satu unit, aktor yang tersimpan di job dipakai sebagai identitas permintaan (role authenticated), lalu fungsi hak akses ERP yang sama dengan halaman dibaca sebelum dan sesudah unit; identitas sebelumnya dikembalikan. Hak berbeda dari saat capture atau dicabut = job gagal `CP7_ANALYSIS_ACCESS_CHANGED`; berubah di tengah unit = unit dibuang. Job yang ditolak tidak menahan job lain. | `K4R_ACCESS_RECHECKED_EACH_UNIT`, `K4R_DENIED_JOB_DOES_NOT_HOLD_OTHERS`, `K4R_RACE_ACCESS_CHANGED_DURING_UNIT` |
| Privat | `cp7_ops.analysis_tick()` SECURITY DEFINER milik `cp7_capture`, hanya bisa dijalankan `postgres`; `run_next` privat; tabel `cp7_analysis_stage.runner` (satu baris, tidak bisa dihapus); tidak ada RPC publik. | `K4R_SCHEDULE_DEFINED_PRIVATE`, `K4R_HTTP_TICK_NOT_REACHABLE` |
| Layar jujur | Status job membawa `server_runner` (aktif bila ada giliran dalam 2 menit terakhir). Hanya bila aktif layar menulis bahwa halaman boleh ditutup; tombol jeda menjadi "Berhenti memantau (server tetap menghitung)". Bila penjalan tidak aktif, teks lama tidak berubah. | `K4R_STATUS_REPORTS_RUNNER`; uji unit `src/nativeStagedJob.test.ts` |

Batas yang diketahui (bukan temuan baru): Business Report v2, daftar pengingat v2 dan job analisis tunggal tetap dijalankan
halamannya (singkat). Penjalan dibuat dan diuji, **belum dipasang** di database sungguhan; pemasangan bersama jadwal
pembersihan dan backup malam menunggu audit dan izin owner. Riwayat `cron.job_run_details` bertambah satu baris per menit
untuk penjalan.

## Kegagalan pertama

- Kegagalan pertama F01–F05: run auditor, ditunjuk di `../../evidence/p20-audit-20261009/README.md`.
- K4: tidak ada kegagalan CI. Run pada `7e5b7265` (versi K4 pertama) dibatalkan otomatis karena digantikan `8cc1b081` — bukan kegagalan; perubahan di antaranya: penanda detak penjalan tidak lagi membuat satu giliran menunggu giliran lain, dan uji balapan kini membuktikan dua giliran berada di dalam unitnya bersamaan. Sebelum push, uji di salinan lokal (bukan bukti) menemukan bahwa jenis sesi tidak terbaca dari fungsi SECURITY DEFINER; pemeriksaan jenis sesi diganti dengan alasan yang tertulis (mode background-worker pg_cron menolak perintah transaksi, jadi tidak ada giliran yang jalan di sana) — batas 8 dtk tetap wajib. Dua salah skrip uji lokal (pembanding identitas permintaan, urutan job saat uji batas) diperbaiki sebelum push.

## Yang tetap terbuka

- Penerimaan area optimasi timeline PR44 oleh auditor lain (konflik kepentingan Astra).
- Pemasangan jadwal (pembersihan, hapus 7 hari, penjalan) dan backup malam di database sungguhan: menunggu penerimaan,
  izin owner, tujuan backup di luar runner yang konkret, dan konfigurasi nyata.
- Pengiriman WA nyata, delapan konfigurasi operasional, K6 (penjalan bukti PL-8 di server).
- `independent_acceptance=false`, `installed_P21_acceptance=false`, `production_go=false`.

# Audit independen Sol — candidate P20 + K4

Audit selesai pada 9 Oktober 2026. **Penutupan bersih paket: HOLD**, karena `SOL-K4-01` terbukti FAIL pada kernel dan paket ERP lengkap. Keparahan S2: penundaan awal dua pemanggil server; hasil unit tetap benar dan unik setelah dilepas. Tidak ditemukan temuan baru S0/S1 dalam putaran yang dinyatakan di bawah. `production_go=false`.

Auditor tidak menulis PR44 atau revisi produk P20/K4. Semua perubahan auditor berada di branch `audit/sol-p20-k4-8cc1b081-20261009`: reproduksi, workflow audit, dan laporan. Source produk yang diuji tetap candidate beku. Handoff dan saran revisi: [WRITER_HANDOFF.md](WRITER_HANDOFF.md).

## Identitas dan cakupan

| Acuan | Identitas |
|---|---|
| Candidate produk | `8cc1b0818fdba54f3ebeb64e132f7f3e20309e24` |
| Tree produk | `2ea854abca572afa923297b0c304e92703ede136` |
| Audit P20 terdahulu | `2e605bb7d9b6b7903919b8df2be1443f1740140b` |
| Revisi sebelum K4 | `870d4f791bc72159f07ed7bd6a17275c19c5ddc7` |
| Baseline PR44 sebelum optimasi | `aa638356e13aeffe7b2a2aa96f17dbe19676db1f` |
| Hash SQL analysis-stages | `653b6ad195ea5e8f0f4dd0557e8fdf9fa25abe39cfca4d623433624d8343c473` |
| Bundle standar plan/staged | `5e0b56e9c7e0cba7b78a33640281b1772e10a57c26429090a3eb7543c9586e17` |
| Bundle K3/K4 dengan extension | `5f2967048185fb312605d7428f601d3e3f73c79890be36f91eb7e44732fde800` |

Seluruh **25 file non-dokumen** pada delta P20 → candidate dibaca/diperiksa. Bytes dan SHA-256 semuanya cocok dengan manifest: [SOURCE_IDENTITY.json](evidence/SOURCE_IDENTITY.json). Fokus runtime: lima temuan lama, penjalan K4, dan netting PR44 yang belum boleh diterima oleh penulisnya sendiri. Area lama yang tidak berubah dan sudah terbukti tidak dihitung ulang sebagai audit seluruh CP1–CP7.

Regresi memakai disposable Supabase PostgreSQL `17.6.1.165`, katalog CP6 yang dibangun melalui aligned chain, clone terpisah per skenario, Auth/PostgREST dan browser CI. Kernel independen memakai native PostgreSQL 16.15 lewat Unix socket privat; tidak menerima database URL eksternal. Tidak ada perubahan database hosted.

## Bukti dan putusan

| Pemeriksaan | Hasil | Asal oracle / batas |
|---|---|---|
| Source candidate/delta | PASS, 25 file | Bytes dan hash manifest dibandingkan dengan checkout beku |
| Klaim writer CI | PASS, 15 workflow / 44 job | Metadata GitHub, head SHA, job IDs dan conclusion diverifikasi; bukan acceptance independen |
| Regresi plan v2 | PASS, 22/22 | Oracle writer dijalankan independen; termasuk capacity v1→v2, v2→v1, rollback, exact fit, dan v2/v2 |
| Regresi cleanup/backup | PASS, 19/19 | Dua database cron, retry backup detik sama, pg_cron, reopen, guard immutable |
| Regresi staged lama | PASS, 14/14 | Race unit, retries, access, snapshot; nama historis workflow tetap `p19-staged12` |
| K4 standar | PASS, 16/16 | Akses sebelum/sesudah unit, timeout, unit sekali, pg_cron, browser reopen |
| K4 kernel Sol | FAIL, 7 PASS / 1 FAIL | `run_next()` dan DDL runner asli; step/access fixture dinyatakan; cold serialisasi, warm tidak |
| K4 paket lengkap Sol | Cold FAIL; warm PASS | `analysis_tick()`, `run_next()`, `step()`, jobs/users/output asli; heartbeat kosong dari instalasi; lock output nyata |
| PR44 kesetaraan | PASS, 235/235 | Full serialized JSON dan SQLSTATE+pesan dari baseline PR44 yang dipin; schedule producer fixture |
| PR44 negative control | PASS, 2 mutant tertangkap | Reuse key saja salah pada skipped twin; mengabaikan supply mengubah hasil |
| PR44 benchmark | PASS, 2 workload | A/B/B/A setelah warmup, seluruh hash/bytes identik; 300 target, 0 atau 40 posisi |
| F05 finalizer | PASS, 7 kontrol | Finalizer AST asli dijalankan; tidak diberi kredit kasus Native |

Keempat regresi utama mencakup **71 kasus unik**. Seluruh ID kasus sama dengan deklarasi, semua hasil per kasus PASS, case-count gate PASS, restore ERP/auth/public definitions+ACL/data PASS dan advisor gate PASS. Pengulangan 16 kasus K4 di workflow pembuktian paket lengkap tidak ditambahkan lagi ke angka 71.

Artefak lengkap diunduh dan hash ZIP diverifikasi terhadap digest GitHub. [NATIVE_SUMMARY.json](evidence/NATIVE_SUMMARY.json) mempertahankan ID/status/gate dan witness utama; raw lengkap dan gambar tetap dirujuk oleh [CI_INDEX.json](evidence/CI_INDEX.json). Screenshot desktop sedang berjalan dan mobile hasil reopen juga diperiksa visual. Bukan uji perangkat fisik.

P20 F01–F03 selesai melalui counterexample asli dan kontrol positif. F04 selesai sebagai koreksi cakupan verifier: `not_rederived_before_removal` sekarang menyatakan bahwa semantik indeks ditopang trigger immutable, bukan dihitung ulang sebelum cleanup. Tidak mengklaim detector privileged-tamper baru. F05 selesai dengan emisi kegagalan yang benar dan metadata budget yang selaras.

Putusan PR44 berlaku **pada source candidate 8cc**, dengan guard `line_edges=[] AND baseline_rows[index]=r::text`. Mutant yang membuang syarat kesamaan row berhasil ditangkap. Jangan memakai putusan ini untuk membenarkan versi historis yang hanya membandingkan target key. Parity mencakup 133 success, 102 refusal, 17 refusal berbeda, dan 121 supply events. Tidak menjadi pembuktian formal semua input atau SLA full application.

Benchmark independen: 300 target tanpa WIP, 1.224,4 → 722,5 ms (40,99%); dengan 40 posisi WIP, 1.567,3 → 1.098,1 ms (29,93%). Semua full-result MD5 dan ukuran byte identik antar sampel. Angka dibatasi fixture dan runtime ini.

## Temuan baru SOL-K4-01 — S2, OPEN, FAIL

**Invarian yang gagal:** heartbeat tidak membuat tick menunggu tick lain. **Lokasi:** `cp7_analysis_stage.run_next()`, INSERT pertama baris boolean singleton runner. Unique-conflict wait terjadi sebelum job selection; UPDATE dengan SKIP LOCKED hanya aman setelah heartbeat pertama commit.

**Reproduksi paket lengkap:** dua job valid pada clone baru; runner benar-benar kosong tanpa menghapus baris atau menonaktifkan trigger. Hold tabel `outputs`, mulai tick A dan pastikan A sudah menunggu INSERT output; mulai tick B. Setelah 1,5 detik B masih menunggu `transactionid/ShareLock`, belum mencapai output. Lepas holder. A/B masing-masing menyimpan satu unit, `[1,1]`, dua output unik. Ulangi pada clone baru dengan heartbeat dipanaskan memakai tick IDLE: kedua tick mencapai langkahnya tanpa saling menunggu heartbeat.

**Dampak:** kehilangan paralelisme saat inisialisasi pertama. Batas 8 detik tidak diubah. Timeout startup merupakan kemungkinan bila transaksi pertama lama; putaran ini membuktikan wait dan recovery, bukan mengukur timeout cold selama 8 detik. Tidak ditemukan salah angka, duplikasi, atau kemacetan permanen. Scheduler pg_cron normal satu job tidak otomatis mengeksekusi dua instance job tersebut bersamaan. S2 dipilih karena perilaku runtime berbeda dari klaim perbaikan; bukan S0/S1.

**Arah revisi:** inisialisasi/update heartbeat dengan pengaman nonblocking khusus heartbeat, contohnya `pg_try_advisory_xact_lock`. Tick yang tidak memperoleh pengaman tetap memilih job, sementara tick lain menulis heartbeat. Detail dan tes penutup ada di handoff. Referensi primer: [unique-index wait](https://www.postgresql.org/docs/17/index-unique-checks.html), [transaction try advisory lock](https://www.postgresql.org/docs/17/functions-admin.html). Rekomendasi tidak diterapkan auditor ke produk.

## Kegagalan dan batas terbuka

Kegagalan cold dipertahankan pada run `37954533118` dan `37954972794`. Workflow paket lengkap sengaja tetap merah ketika kontrol independen FAIL walaupun 16 oracle standar K4 PASS. Outer package mencatat `writer_runtime=false`; restore dan primary-unchanged tetap PASS. Ini kegagalan produk yang teruji, bukan tooling block.

Run `37955377803` salah memilih skrip karena konfigurasi workflow auditor. Tidak ada kredit benchmark untuk run itu. Pemilihan diperbaiki tanpa mengubah oracle produk; run `37955740692` melakukan benchmark yang benar dan PASS. Run pertama tidak dihapus.

- 5.000 target penuh melalui K4 server belum dijalankan ulang auditor. Writer scale receipt pada SHA yang sama hijau; proof K4 audit yang dinyatakan memakai fixture native 3 target dan browser 1 target. SLA beban live belum divalidasi.
- Mobile CI menggunakan Chromium/emulasi; alur menekan Berhenti memantau dan reload lulus. Tab mobile benar-benar ditutup, HP fisik dan Safari belum diuji dalam putaran ini.
- Jadwal/backup hosted, data cutover nyata dan produksi tidak diuji/dipasang. Status produksi tetap belum GO sesuai handoff writer.
- Temuan privilege-disabled semantic index yang sudah dinyatakan di F04 tidak direproduksi ulang; oracle keamanan reguler dan boundary cleanup diuji ulang.

Status terbuka di atas berarti **belum diuji pada cakupan tersebut**, kecuali SOL-K4-01 yang **sudah diuji dan FAIL**. Audit putaran ini selesai; writer menerima satu perbaikan konkret dan tes reproduksi yang siap dipakai. Penutupan bersih menunggu retest SHA revisinya, sesuai aturan temuan S2 pada panduan audit.

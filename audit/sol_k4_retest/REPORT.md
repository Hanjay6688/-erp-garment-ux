# Audit independen — uji ulang perbaikan K4 `8116800c`

Tanggal: 10 Oktober 2026. Auditor: Sol. **Vonis: PASS_RETEST; SOL-K4-01 CLOSED.** Tidak ada temuan produk baru dalam cakupan ini. Penerimaan terbatas pada perbaikan K4 dan tiga suite regresi yang terpengaruh. Seluruh CP1–CP7, pemasangan hosted, serta kinerja 5.000 target lewat server belum mendapat penerimaan menyeluruh dari putusan ini. `production_go:false`.

## Identitas dan cakupan

- Sumber: `8116800c0586cfb27bd6c7d206d1b176666c9839`.
- Tree: `12b81da97f5260596d2384765dd5e2d877e6c80f`.
- Paket writer: `docs/cp7/audit-candidate/sol-retest-k4-20261009/` di head dokumentasi `b10a0521bda4ad5191e4e9fcd82a76fcd7685dcc`.
- Perbandingan dengan `8cc1b081`: 13 file; seluruh ukuran dan hash sebelum/sesudah cocok dengan manifest writer. Empat non-dokumen: workflow transport, satu SQL produk, probe/finalizer, kasus K4. Product SQL hanya mengubah heartbeat dalam `run_next()`.
- Selisih kandidat terhadap head dokumentasi hanya `docs/`. Tidak ada perubahan diam-diam pada produk.
- Cabang auditor baru: `audit/sol-k4-retest-8116800c-20261010`. Run native memakai head `6d512cc1cef2d05e373b97cd86b0729d55dedd62`; kernel memakai `63156b88e343755a9741b45b8f09ed136884b4b8`. Delta kedua head hanya alat audit/workflow; sumber produknya sama dengan kandidat beku.

Audit membaca paket retest dan laporan Sol sebelumnya, memeriksa delta lengkap, lalu menjalankan bukti sendiri dalam database sekali pakai. Tidak membaca hasil auditor lain yang sedang bekerja. Tidak mengubah kode produk, oracle milik writer, main, cabang writer/integration, deployment atau database hosted.

## SOL-K4-01 — DITUTUP

**S2, sumber lama `8cc1b081`:** saat runner masih kosong, INSERT heartbeat yang belum commit membuat tick kedua menunggu unique-index transactionid sebelum mengambil job. Uji lama gagal pada kernel dan ERP terpasang: run [37954533118](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37954533118) / [37954972794](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37954972794). Dua job akhirnya tetap benar; dampaknya penundaan awal pada pemanggilan bersamaan.

**Perbaikan:** `pg_try_advisory_xact_lock(hashtextextended('CP7:K4_RUNNER_HEARTBEAT',0))` menjaga penulis heartbeat saja sampai akhir transaksi. Tick yang tidak mendapat kunci melewati heartbeat dan tetap memilih job dengan `FOR UPDATE SKIP LOCKED`. Pemeriksaan READ COMMITTED dan timeout 1..8000 ms tetap dilakukan sebelum penulisan; pemilihan job, peran aktor dan pemeriksaan akses sebelum/sesudah unit tidak berubah. UPSERT mempertahankan batas pembaruan heartbeat 10 detik.

**Uji penutup milik auditor dipakai byte-for-byte:**

| Berkas | SHA-256 |
|---|---|
| `audit/sol_p20_k4/cold_runner.py` | `a38864a9c6f68db6c84b853654a8d7b896a8b347edc213d57140d2cf3c232ab4` |
| `scripts/sol_p20_k4_installed_probe.py` | `065d2d295a6a41af4dc7a67b058f11277d1c6432cfd273b06186921a50773afe` |

Kernel mengandung literal label kandidat lama karena sengaja tidak diedit. Identitas eksekusi revisi dibuktikan oleh hash SQL aktual `325962068ec3ee9218b4b2aa76aec230fc79ba88844bf692be4704a89b84c8f6`, gate workflow dan `SOURCE_IDENTITY.json`. Docstring wrapper menyebut 16 kasus sebagai teks historis; oracle produk revisi memeriksa 17. Label lama tidak dipakai sebagai bukti versi baru.

Kernel: tick pertama ditahan dalam unit; tick kedua harus selesai sendiri dalam jendela observasi 1,5 detik. Cold/warm keduanya PASS, tanpa kunci tak-terpenuhi transactionid; dua output unik. Timeout 0/8001 ms ditolak sebelum heartbeat ditulis, repeatable-read ditolak, aktor job dipakai dan ketiga klaim sebelumnya dipulihkan. **8/8 PASS**, [run 38054431784](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38054431784), job `114219877085`. Kernel memakai step/access fixture terkontrol; tidak diberi kredit RLS/UI.

ERP terpasang: clone masing-masing baru dan runner benar-benar kosong. Cold tidak menghapus runner atau menonaktifkan trigger; warm menjalankan tick IDLE sungguhan lebih dulu. Kunci EXCLUSIVE pada outputs hanya menjadi gerbang observasi. A dan B masing-masing mencapai INSERT output asli bersamaan; B menunggu `relation/RowExclusiveLock` yang sengaja ditahan, tanpa menunggu heartbeat. Setelah gerbang dilepas, dua job berbeda masing-masing `units_done=1`, dua output unik, tanpa duplikasi. `SOL_COLD_START` / `SOL_WARM_START` keduanya PASS dan database_remaining=0. Product step tidak dimodifikasi. **2/2 PASS**, run native di bawah.

## Regresi yang dijalankan auditor

[Run 38054430466](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38054430466), ketiga job SUCCESS.

| Suite | Native | Race | HTTP | Browser | Jumlah | Job |
|---|---:|---:|---:|---:|---:|---|
| K4 | 7 | 6 | 2 | 2 | 17/17 PASS | `114219872881` |
| Staged | 6 | 4 | 2 | 2 | 14/14 PASS | `114219873012` |
| K3 | 9 | 6 | 2 | 2 | 19/19 PASS | `114219873096` |

Set ID kasus tepat sama dengan deklarasi sumber; tidak ada kasus kurang, diganti atau tambahan yang menutupi kasus wajib. Gate counts dan IDs keduanya true, tiap kasus PASS. Counts actual = expected. Native boundary restored; kebocoran advisory lock/session nol. Race/HTTP/browser database dibersihkan; Auth sebelum/sesudah identik; token HTTP berasal dari Auth runtime, bukan JWT buatan uji. Gate install, primary unchanged, backup–restore, security advisors, dan runtime semuanya true. Ketiga drill backup–restore RESTORED_SAME_MEANING.

K4 mencakup akses berubah antar unit dan di dalam unit (unit dibatalkan), job ditolak tidak menahan yang lain, page/server serta dua tick tidak mengerjakan unit yang sama dua kali, timeout retry dengan batas tetap, fungsi private tidak terjangkau HTTP, status runner dan pg_cron sungguhan. Staged memeriksa kesamaan dengan jalur tunggal, batas, identitas, source check, freshness dan browser reload. K3 memeriksa hasil tetap bisa dibaca setelah cleanup, penundaan/refusal yang benar, retry, retensi, jadwal dan backup.

Browser desktop memakai Chromium dan menutup tab sungguhan: 0 unit halaman, 16 unit server, request/run sama, tidak request/step ulang ketika dibuka, setiap unit sekali. Mobile Chromium emulasi **STOPPED_WATCHING**, lalu hasil dibuka kembali: 0 unit halaman, 16 unit server, hasil sama. Mobile bukan bukti tab HP benar-benar ditutup. Jadwal uji dipercepat ke 5 detik dengan label TEST_SCHEDULE_OVERRIDE; bukan bukti cadence hosted.

**Total independen: 60/60 PASS = 8 kernel + 2 race auditor + 17 K4 + 14 staged + 19 K3.** 50 kasus memakai oracle writer yang dijalankan ulang oleh auditor; 10 memakai probe auditor yang sudah menangkap kegagalan sumber lama.

## CI writer dan kegagalan tengah malam

Auditor mengambil ulang metadata 15 run dan 44 job di `CI_RECEIPT.json`: SHA, nomor percobaan, ID/nama job, status/conclusion seluruhnya cocok; semua SUCCESS pada `8116800c`. P08 menggunakan percobaan kedua. Ini verifikasi bukti writer; bukan klaim auditor menjalankan sendiri seluruh 15 workflow.

Kegagalan pertama `attention284`, run `37958882487`, job `113916327717`: 23.33–00.08 WIB, 280 kasus PASS dan 6 browser INCOMPLETE. Log asli dan dua ZIP lengkap dibaca; hash ZIP cocok dengan digest GitHub. Snapshot gagal memuat query `from_date/through_date=2026-10-09` sementara period metrik server `2026-10-10`. Sumber harness mengambil tanggal sekali saat setup dan menggunakannya ke seluruh journey; payroll menolak eligible_at sesudah period_end, sehingga CP7_NOTA_AFTER_PERIOD tepat. Dua assertion pengingat mendapat 2 dibanding 1. Jalur browser ini memakai capture operasional v1; SQL heartbeat K4 tidak menjadi penyebab pada bukti ini.

Percobaan kedua, job `113934690918`, pada source SHA dan hash bundle yang sama: **286/286 PASS**, dengan empat kelompok 181/40/29/36, oracle tidak berkurang dan restore/advisor gate true. Nama “attention284” historis; expected aktual 286. Kegagalan pertama tetap tersimpan; hasil hijau tidak menghapusnya.

**Catatan alat uji yang sudah ditemukan writer: masih OPEN_TOOLING (S3), tidak menghalangi penerimaan perbaikan K4 ini.** Root cause didukung sumber, tanggal snapshot gagal, dan rerun ketat pada SHA sama. Tidak dihitung sebagai temuan produk baru auditor. Tindakan: isolasi fixture peka tanggal, baca tanggal DB dekat aksi, periksa business-day sebelum/sesudah journey; pergantian hari memberi INCOMPLETE dan membutuhkan run baru pada salinan segar. Tambahkan kontrol rollover untuk alat uji; jangan melonggarkan assertion atau mengubah clock produksi.

## Putusan sebelumnya dan batas bukti

F01–F05 serta PR44 tidak dibuka kembali. Selisih seluruh tree telah diperiksa; area yang tidak berubah menggunakan putusan audit sebelumnya sesuai cakupannya, bukan diberi label “diuji ulang” di `8116800c`. Kapasitas plan 22 kasus dan 235 pembandingan PR44 tidak diulang. Batas F04 tetap: tidak ada perhitungan ulang indeks semantik sebelum cleanup setelah pelindung dimatikan oleh pihak berprivilege.

**BELUM DIUJI auditor**, bukan bukti rusak: 5.000 target selesai seluruhnya melalui K4; HP fisik/Safari; tab mobile benar-benar ditutup; konfigurasi pemasangan hosted/jadwal dan backup di luar runner. K4 browser/native menggunakan fixture kecil. Kelulusan scale5 milik writer tidak dijadikan penerimaan 5.000 target via runner atau SLA produksi.

PR #45 terpisah dan belum diaudit dalam putusan ini. Saat diperiksa PR masih OPEN, head `049bb7925bb8c75221cf605733d21350c8e54927`, berisi perubahan UI lain selain pecah batch; split batch baru simulasi DEMO dan belum Native backend. Tidak ada merge main. Uji ulang K4 tidak memberi penerimaan PR45.

Untuk pemasangan nyata, owner tetap perlu menerima batas bukti yang relevan, menetapkan konfigurasi dan tujuan backup di luar runner serta rencana restore, lalu mengizinkan pemasangan dan pemeriksaan pada target yang sudah ditentukan. Tidak ada jadwal/backup hosted yang dipasang di audit ini. `full_cp1_cp7_acceptance:false`, `installed_P21_acceptance:false`, `production_go:false`.

## Bukti yang bisa diolah

- `FINDINGS.json`: status temuan dan penerimaan yang terstruktur.
- `evidence/CI_INDEX.json`: run/job/artifact dan digest.
- `evidence/SOURCE_IDENTITY.json`, `DECLARED_SOURCE_DELTA.json`: tree serta hash sumber sebelum/sesudah.
- `evidence/NATIVE_SUMMARY.json`: 60 kasus, ID/witness dan gate; JSON original tetap pada artifact GitHub.
- `evidence/SOL_INSTALLED_COLD.json`, `SOL_INSTALLED_WARM.json`, `COLD_RUNNER.json`: bukti penutup auditor.
- `evidence/WRITER_CI_VERIFIED.json`, `ATTENTION_MIDNIGHT_REVIEW.json`: bukti writer yang diverifikasi dan kegagalan pertama.
- Artifact original memiliki batas retensi GitHub yang tercantum di CI_INDEX. Digest dan witness penting disimpan di cabang audit.

# Daftar gabungan temuan CP7 — putaran silang 1 (13 Okt 2026)

Permintaan owner, 13 Okt 2026: "lu stauin dan benerin dulu semua temuannya trus lu kasi panduan ya kirim apa buat
astra, kirim apa buat fable, dari hasil akhirnya biar semua tau konteks lengkapnya uji apa. audit ini indpenden masing
masing. semua masi scope cp7 only harusnya. jadi lu harus compile dengan baik temuan masing masing. pas lu kirim
feedback nanti auditor masing masing harus tau temuan pesaingnya dari handoff lu. jadi saling cross check."

Cakupan: **CP7 saja.** Temuan CP1–CP6 di luar delta CP7 tidak dibuka di sini. Keputusan owner yang sudah disahkan
tidak dibuka ulang. `production_go:false`.

## Sumber temuan

| Auditor | Laporan | Cabang / commit audit | Kandidat yang diuji |
|---|---|---|---|
| Fable | `audit/fable_cp7/AUDIT_FABLE_d0b9e9c2.md` (audit penuh, HOLD) dan `audit/fable_cp7/AUDIT_FABLE_7a0b4a90_RETEST.md` v1.0.1 (LULUS DENGAN SYARAT), `audit/fable_cp7/OWNER_DECISIONS_TO_AUDITOR_20261013.md` | `audit/fable-cp7-full-d0b9e9c2-20261011` @ `1a808bc9` | `7a0b4a90` |
| Astra | `audit/astra_retest_20261013/REPORT.md`, `WRITER_HANDOFF.md`, `ASR_OPS_01.md` (HOLD) | `audit/astra-cp7-retest-7a0b4a90-20261013` @ `41dbd14d` | `7a0b4a90` |

Kedua auditor bekerja terpisah dan tidak membaca laporan putaran yang sama milik pihak lain. Daftar ini menggabungkan
keduanya supaya masing-masing bisa memeriksa silang temuan pesaingnya.

## Kandidat putaran ini

**`ae0214ad33184f7c2724783d663fb20fcb13820c`** (tree `0217f5f6740f28c19b7894fcb0181f39d3aea727`), cabang `claude/new-session-deapao`.

- Kode produk sama dengan `7a0b4a90`: `git diff --name-only 7a0b4a90 ae0214ad -- supabase src scripts/cp7-src` kosong.
- Yang berubah di luar `docs/` (12 berkas): alat backup malam (ASR-OPS-01), runner uji dan pembanding selisih
  (diagnosis bayar supplier), kasus K3 (balapan ke-11 + gladi jadwal), alat diagnosis ulang, satu uji layar yang
  dipindah ke `tests/`, dan empat workflow. Daftar persisnya ada di `README.md` folder ini.
- CI writer pada commit yang sama: `CI_RECEIPT.json` (dibuat dengan `scripts/cp7_ci_receipt.py`).

## A. Butir yang masih bergerak di putaran ini

| No | ID | Asal | Isi singkat | Tindakan writer | Bukti writer | Diminta dari Astra | Diminta dari Fable |
|---|---|---|---|---|---|---|---|
| A1 | **ASR-OPS-01** | Astra (keluarga F-OPS-01 Fable) | Status scratch backup dibaca sebelum dump dan dipakai sesudahnya. Database pengganti bernama sama ikut dihapus, dan malam itu tetap `restore_verified=true`. | **Diperbaiki** di `85e17168`: kepemilikan scratch diikat ke OID database, bukan ke nama. Setiap percobaan memakai database sendiri dengan nama acak dan OID yang dipilih alat. Penghapusan hanya lewat OID: pindah ke nama acak, cek OID lagi, baru hapus. Jalur `finally` yang Astra temukan dari kode (boolean `ours`) sudah dihapus; `finally` hanya menghapus database milik percobaan (OID + token). **Batas operasional dinyatakan, tidak dianggap disetujui:** admin yang sengaja mengganti database percobaan (nama acak) tepat di antara cek OID dan `pg_restore` tersambung bisa menerima tabel hasil restore. Database itu tidak dihapus, dan malam itu tidak terverifikasi. | `../asr-ops-01-retest-20261013/README.md`, `CI_RECEIPT.md` di folder itu (`K3C_RACE_BACKUP_SCRATCH_OWNERSHIP_BY_OID` + 4 kasus backup K3 lama di `k3-cleanup-24`). Kontrol lokal: kasus B05 Astra di alat lama = COUNTEREXAMPLE, di alat baru = PASS. | Uji ulang `ASD-B01..B05` tanpa mengubah oracle, ditambah 4 kontrol dari handoff Astra (tulis ke sumber selama backup, sumber utuh, tidak ada pemangkasan saat ditolak, hapus akhir hanya scratch milik percobaan). Nilai batas operasionalnya. | **Silang:** jalankan ulang kasus Fable `BACKUP_SCRATCH_DROPS_FOREIGN_DB` dan `BACKUP_VERIFY_UNDER_LIVE_WRITES` di alat baru. Baca sumber `drop_owned`/`create_attempt`/`backup()`. Nilai apakah perbaikan Astra menutup keluarga F-OPS-01 tanpa membuka jalur hapus baru. |
| A2 | **Selisih akhir grup bayar supplier** | Fable (syarat §3.1); Astra mencatat "penyebab belum diketahui" | `CP7 Supplier Payment Create`: 10/10 kasus PASS, tetapi pemeriksaan akhir grup tidak sama di run 38288829388 dan 38330557862. | Diagnosis dipasang di runner (`state_difference`, `catalog_observation`, `group_end_difference`). Pembanding tidak diubah. 9 run kualifikasi + 60 grup ulang: kegagalan **tidak terulang pada pengujian berikutnya**. Yang sudah diperiksa: kode, `autoanalyze`, pemindaian paralel, baris berpindah. Kecepatan mesin **belum dapat disingkirkan**. Status **OPEN** (arahan owner 13 Okt). Pengujian tidak diulang lagi tanpa hipotesis baru. | `../../evidence/fable-retest-20261012/GROUP_END_DIAGNOSIS.md`, log `01`–`07`. Run `Supplier Payment Create` di kandidat ini ada di `CI_RECEIPT.json`. | **Silang:** bandingkan dengan 26 snapshot milikmu (`SUPPLIER_BOUNDARY_REVIEW.json`). Baca diff `cp6_auditor_runner.py`/`cp6_auditor_difference.py`: pencatatan hanya menambah detail dan tidak mengubah hasil pembanding? | Tinjau untuk laporan v1.1 sesuai tabel bentuk bukti di registermu. Status boleh tetap OPEN. |
| A3 | **Gladi jadwal** | Fable (syarat §3.2c) | Pasang jadwal sungguhan di salinan sekali pakai, cocokkan `schedules()` dengan K3, lalu lepas dan buktikan pulih. | Selesai: kasus `K3C_RACE_SCHEDULE_INSTALLER_REHEARSAL`. | `../../evidence/fable-retest-20261012/SCHEDULE_REHEARSAL.md`, log `08`. Diulang di `k3-cleanup-24` kandidat ini. | **Silang:** kamu sudah menguji CLI jadwal (mismatch dan izin). Periksa bahwa gladi tidak menyentuh hosted dan `cron.job` kembali 0 baris. | Tinjau untuk v1.1. |
| A4 | **F-PAY-01, cabang "sesi sudah besok"** | Fable menarik F-PAY-01; Astra mencatat cakupan | Uji `P12_SETTLEMENT_WIB_PAYMENT_DATE` di run Astra hanya mengaktifkan zona yang harinya tertinggal. Cabang zona yang sudah besok tidak aktif pada jam run, jadi tidak diklaim PASS. | Kode tidak diubah. Workflow `CP7 P12 Payroll` dijalankan pada pukul 17.00–19.00 WIB, jam ketika **kedua** cabang aktif. | `F_PAY_01_BOTH_BRANCHES.md` di folder ini (baris kasus dengan `session_day_behind_wib_accepts_wib_today` dan `session_day_ahead_of_wib_refuses_wib_tomorrow` keduanya `true`). | Periksa baris itu. Boleh menjalankan ulang kasus pada jam 17.00–19.00 WIB. | Untuk diketahui. Tidak ada tindakan, karena temuan sudah ditarik. |
| A5 | **Penerimaan PR44** (optimasi netting) | Astra adalah penulisnya, jadi tidak boleh menerima | Perlu penerimaan dari auditor yang bukan penulis. | — | — | Untuk diketahui: Fable sudah **MENERIMA** area PR44 di tree `7a0b4a90` (laporan retest §2.3: probe paritas 595/595, `mutations_caught 2`, netting 83/83). Tidak ada tindakan. | Konfirmasi bahwa penerimaan berlaku untuk kandidat ini. `scripts/cp7-src/` identik, jadi cukup membuktikan diff kosong. |
| A6 | **Dua kasus CP6 yang dipensiunkan** (`SALES_MANUAL_13`, PRE-05) | Owner 13 Okt: harus ada rujukan keputusan dan cakupan pengganti | Kasus browser CP6 lama tidak cocok lagi dengan layar CP7. | Dokumen rujukan dan tabel cakupan pengganti. Pemeriksaan lama diulang di uji layar `tests/cp7/SalesPages.dozenHelper.dom.test.tsx` (dipindah dari `src/` supaya `src/` tetap identik). Pengesahan pensiun menunggu ya/tidak dari owner. | `../../RETIRED_CP6_SALES_MANUAL_13.md` | **Silang:** jalankan uji layar itu dan nilai apakah empat pemeriksaan lama benar-benar tercakup. | Tinjau untuk v1.1 (permintaan owner). |
| A7 | **"Pin" `product_ref=ddedf06c` di identitas T3** | Fable (retest §2.5: "penulis sebaiknya memajukan pin itu") | Identitas T3 di job writer mencatat `product_ref=ddedf06c`. | **Tidak diubah, dengan alasan.** Nilai itu bukan pin. `scripts/cp6_run_identity.py` menghitungnya dengan `git log -1 -- <jalur produk>`, yaitu commit terakhir yang mengubah `supabase/*` dan `src`. Karena jalur itu tidak berubah sejak `ddedf06c`, nilai tersebut memang benar. Kalau "dimajukan", nilai itu justru salah menunjuk commit yang tidak mengubah produk. | Baca `scripts/cp6_run_identity.py`. | — | Terima atau bantah dengan alasan. |
| A8 | **Perubahan writer sesudah `7a0b4a90` belum diuji Astra** | Astra (`LATER_WRITER_DELTA.json`) | Alat uji, diagnosis dan tes tambahan sesudah kandidat belum mendapat PASS runtime independen. | Semua perubahan itu masuk kandidat putaran ini. | `README.md` folder ini (daftar 12 berkas). | Jalankan regresi yang kamu anggap perlu pada kandidat ini (minimal suite yang memakai `cp6_auditor_runner.py`). | Sama: tinjau diff alat uji. |
| A9 | **Keputusan owner D13-4..D13-7** | Owner | D13-4..6: proyek produksi, lokasi backup, uji pemulihan. D13-7 (13 Okt): **database produksi = Enteng `siimvrusnzxexizpyoib`, `postgres`** (mengganti D13-4), backup ke Google Drive dulu sebelum ada perubahan. Owner tidak mau mengeluarkan biaya. | Dicatat verbatim di `../../OWNER_DECISIONS_20261008.md`. Belum ada pemasangan, bucket, kunci atau jadwal yang dibuat. Alat backup versi berikutnya (salin ke penyimpanan luar, ambil kembali, pulihkan di mesin GitHub) **belum** masuk kandidat ini dan akan diaudit terpisah. | register | Untuk diketahui. | Untuk diketahui. Daftar periksa pemasangan menyusul sesudah owner menjawab sisa pertanyaan biaya. |

## B. Butir writer di luar temuan auditor (dicatat supaya tidak ada yang tersembunyi)

| No | Isi | Status | Bukti |
|---|---|---|---|
| B1 | `CP7 Shell S0` merah di `5b8e9d74` (run 38355457365), karena uji diagnosis memuat `psycopg` yang tidak terpasang di job itu. | Diperbaiki di `5e96cbcf`: fungsi dipindah tanpa perubahan isi ke `scripts/cp6_auditor_difference.py`. | Shell S0 di kandidat ini (`CI_RECEIPT.json`). |
| B2 | `CP6 Auditor Scenario` merah: READINESS ×2 (RPC CP7 tidak ada di paket CP6 saja, F-UI-02) dan `SALES_MANUAL_13` ×2 (butir A6). | Sudah tercatat sejak 2 Okt. Bukan bagian dari workflow kualifikasi. | — |
| B3 | Pesan commit `71594a0b` menulis "runner speed is ruled out". Kalimat itu tidak benar. | Dokumen sudah dibetulkan. Riwayat commit tidak ditulis ulang. | `GROUP_END_DIAGNOSIS.md` §4 butir 5 |
| B4 | Uji layar yang dipindah ke `tests/cp7/` sempat masuk commit `144d0709` dengan jalur impor lama. | Dibetulkan di `4dc0f3f0`, sebelum kandidat. | Shell S0 di kandidat ini |

## C. Butir yang sudah tertutup (untuk rujukan; tidak perlu diuji ulang kecuali auditor mau)

| ID | Asal | Status | Penutup |
|---|---|---|---|
| F-OPS-01 (kasus dasar) | Fable | DITUTUP oleh Fable di `7a0b4a90`; sisanya = A1 | FABLE `BACKUP_SCRATCH_DROPS_FOREIGN_DB` PASS |
| F-OPS-02 | Fable | DITUTUP (Fable), terverifikasi Astra | FABLE `CLEANUP_LOCK_VS_RUNNING_STEP`; kasus Astra cleanup A/B |
| F-OPS-03 | Fable | DITUTUP (Fable), terverifikasi Astra | snapshot dump; tulis bersamaan |
| F-OPS-04 | Fable | DITUTUP (Fable), terverifikasi Astra | `same_database`, `--removal-approved` |
| F-UI-01 | Fable | DITUTUP (Fable), terverifikasi Astra (4 browser) | keputusan owner 12 Okt, ditegaskan 13 Okt (D13-1) |
| F-AN-01 | Fable | DITUTUP (Fable), terverifikasi Astra | `CP7_ANALYSIS_STAGED_TARGET_LIMIT` di `request()` |
| F-PAY-01 | Fable | DITARIK oleh Fable (salah kutip versi fungsi); cakupan = A4 | migrasi v2.6.20ac/ap WIB |
| F-AP-01 | Fable | ACCEPTED_BY_DECISION (owner 2 Okt), terverifikasi Astra | `RF_OVERPAID_CREDIT_TO_NEXT_NOTA` |
| F-TOOL-01 | Fable | DITUTUP lewat ASF-F01 | anotasi `AUDITOR_BUSINESS_DAY_*` |
| F-TOOL-02 | Fable | DITUTUP | probe PR44, `mutations_caught 2` |
| F-TOOL-03 | Fable | FROZEN_CP6_DISPOSITION | — |
| F-UI-02, F-DOC-01 | Fable | DITUTUP / dicatat | — |
| OBS-01 | Fable | Diputuskan owner (PL-5 owner saja), terverifikasi keduanya | HTTP owner-only; PL5 20/20 |
| OBS-02, OBS-03 | Fable | Observasi, tidak diubah | — |
| ASF-F01 | Astra | DITUTUP (Astra) | 4 + 15 kontrol, empat mode |
| ASRA-T01 | Astra (alat Astra sendiri) | DITUTUP oleh Astra lewat pemeriksaan Original | bukan produk |
| AS20-39 | Astra (P20) | Batas lama yang tercatat, bukan bug baru | `K3_CLEANUP.json` `not_rederived_before_removal` |
| 2 INCOMPLETE pre-freeze UI (runtime CP6 lama) | keduanya | Diagnosis dengan nol kredit, sama seperti sebelumnya | — |

## Alur putaran

1. Owner mengirim `HANDOFF_ASTRA.md` ke Astra dan `HANDOFF_FABLE.md` ke Fable. Isinya sudah memuat temuan pihak lain.
2. Masing-masing auditor menguji secara independen, lalu mengirim konfirmasi per butir: DITUTUP, MASIH TERBUKA, atau
   temuan baru, lengkap dengan run, kasus dan log gagal pertama.
3. Writer menggabungkan kedua konfirmasi. Kalau masih ada masalah, writer memperbaikinya, lalu putaran 2 dikirim ke
   kedua auditor dengan cara yang sama.

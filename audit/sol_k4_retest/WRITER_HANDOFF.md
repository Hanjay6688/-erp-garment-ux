# Handoff writer — uji ulang K4 `8116800c`

**PUTUSAN: PASS_RETEST. SOL-K4-01 (S2) DITUTUP.** Tidak ada temuan produk baru dalam cakupan uji ulang ini. Ini penerimaan perbaikan K4 dan regresi yang terpengaruh; `production_go:false` tetap.

Sumber yang diuji: `8116800c0586cfb27bd6c7d206d1b176666c9839`, tree `12b81da97f5260596d2384765dd5e2d877e6c80f`. Cabang bukti baru: `audit/sol-k4-retest-8116800c-20261010`. Writer/main/hosted tidak diubah.

| Pemeriksaan oleh auditor | Hasil | Bukti |
|---|---:|---|
| Kernel auditor lama, byte tetap sama | 8/8 PASS | [run 38054431784](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38054431784) |
| Cold/warm auditor pada ERP terpasang; tabel runner benar-benar kosong dari instalasi | 2/2 PASS | [run 38054430466](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38054430466), `SOL_INSTALLED_COLD.json` / `SOL_INSTALLED_WARM.json` |
| K4, termasuk kasus cold baru, batas 8 detik, akses berubah, pg_cron, Auth/HTTP/browser | 17/17 PASS | run yang sama, job `114219872881` |
| Analisis bertahap | 14/14 PASS | job `114219873012`; label workflow `p19-staged12` memang lama |
| K3 | 19/19 PASS | job `114219873096` |
| **Total kasus yang dijalankan auditor** | **60/60 PASS** | 8 + 2 + 17 + 14 + 19 |

Cold dan warm: tick A ditahan pada INSERT output asli. Tick B juga mencapai INSERT outputnya dalam batas observasi 1,5 detik; yang ditunggu hanya kunci tabel output sengaja dipasang auditor, bukan `transactionid` heartbeat. Setelah kunci dilepas, dua job berbeda masing-masing maju satu unit, ada dua output unik, tanpa duplikasi. Cold memakai instalasi baru tanpa menghapus runner atau mematikan trigger; warm diawali tick IDLE sungguhan. Klaim/aktor, pemeriksaan akses, dan batas 8 detik tetap lulus. Semua paket lulus gate install, primary unchanged, backup–restore, keamanan, dan runtime; database uji dibersihkan.

**Yang writer perlu tindak lanjuti:**

1. Ubah status SOL-K4-01 menjadi CLOSED dan referensikan SHA + dua run auditor di atas. Bukti gagal pertama pada `8cc1b081` tetap dipertahankan. Perbaikan heartbeat diterima; tidak ada revisi produk K4 lanjutan yang diminta audit ini.
2. Masalah skrip `attention284` yang sudah writer catat **masih terbuka sebagai pekerjaan alat uji**, bukan temuan K4 baru. Auditor mengonfirmasi: percobaan pertama 280 PASS + 6 INCOMPLETE; query fixture 9 Okt, metrik server 10 Okt. Percobaan kedua pada SHA dan oracle yang sama 286/286 PASS. Nama suite historis “284”; kontrak aktualnya 286. Saran: pisahkan fixture peka tanggal agar tidak membawa data kasus terdahulu, ambil tanggal DB dekat aksi, dan deteksi pergantian hari sebelum/sesudah journey sebagai INCOMPLETE. Pertahankan kegagalan pertama, lalu ulang pada salinan baru. Jangan mengubah clock produksi atau mengurangi assertion. Tambahkan kontrol pergantian hari pada alat ujinya.
3. Klaim 15 workflow / 44 job writer terkonfirmasi lewat GitHub pada SHA yang sama, termasuk percobaan P08 ke-2. Labelnya tetap **writer crosscheck yang diverifikasi**. Uji auditor sendiri berjumlah 60; jangan gabungkan hitungannya.
4. F01–F05 dan PR44 tetap memakai putusan sebelumnya sesuai batasnya. Selisih non-dokumen hanya empat file; kode produk yang berubah hanya heartbeat `run_next()`. Area lain tidak seluruhnya diulang. Batas F04—indeks semantik tidak dihitung ulang setelah guard dimatikan oleh pihak berprivilege—tetap berlaku.
5. **BELUM DIUJI auditor:** 5.000 target selesai seluruhnya lewat K4; HP fisik/Safari; tab HP benar-benar ditutup. Browser desktop menutup tab sungguhan; browser mobile melakukan STOPPED_WATCHING lalu membuka hasil kembali. Jadwal dan backup di hosted belum dipasang/diuji. Ini batas bukti, tidak menyatakan bagian tersebut rusak.
6. PR #45 tetap terpisah. PR terbuka di head `049bb7925bb8c75221cf605733d21350c8e54927` memuat beberapa perubahan UI; pecah batch baru simulasi DEMO. Uji ulang K4 ini tidak memberi penerimaan PR45 atau izin merge. Audit UI/demo PR45 diperlukan sebelum menyebut perubahan itu diterima auditor.

Sebelum pemasangan sungguhan: owner perlu menerima batas bukti yang masih terbuka; finalisasi tujuan backup di luar runner, konfigurasi/jadwal dan rencana restore; lalu beri izin owner untuk pemasangan dan pemeriksaan pada target yang telah ditetapkan. Hasil audit ini tidak memasang jadwal atau memberi GO produksi.

Berkas olahan: `FINDINGS.json`, `REPORT.md`, `evidence/NATIVE_SUMMARY.json`, `evidence/CI_INDEX.json`, `evidence/SOURCE_IDENTITY.json`, `evidence/WRITER_CI_VERIFIED.json`, `evidence/ATTENTION_MIDNIGHT_REVIEW.json`.

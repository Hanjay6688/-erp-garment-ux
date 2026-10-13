# Astra — pemeriksaan paket writer final putaran 2

**Vonis Astra tetap berlaku: R2-A6 LENGKAP, R2-F05 dan ASR-OPS-01 DITUTUP. Tidak ada penghalang baru dari paket final writer. A2 tetap OPEN dan nonblocking menurut D13-10. `production_go:false`.**

Pemeriksaan lanjutan ini dilakukan atas perintah owner “lanjut oi”, setelah laporan Astra dikunci pada `57ac8aab164f7c3fc25cf8e2500a8346477da618`. Laporan terkunci beserta bukti independennya tidak diubah. Catatan ini menyelesaikan pemeriksaan paket writer yang masih pending ketika laporan utama dibuat.

## Kandidat dan paket

- Kandidat tetap **`0b7049d9203bac52b47a4c89f3e0d75646067a8f`**, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`.
- Paket writer final: **`fff2bde01d0bf4cc78ccbc78e786d720f1bf12a5`**, diterbitkan 13 Oktober 2026 19:00 UTC / 14 Oktober 02:00 WIB.
- Perbandingan kandidat dengan paket final menunjukkan dua commit tambahan dan tujuh berkas baru, seluruhnya di `docs/cp7/audit-candidate/crosscheck-r2-20261014/`. Tidak ada perubahan produk, alat uji, workflow, atau oracle.

## Receipt GitHub dan pergantian hari

Daftar run dari GitHub untuk SHA kandidat dicocokkan dengan `CI_RECEIPT.json`, lalu seluruh daftar job pada 20 run dibaca. ID, nama job, jumlah, status, SHA, dan attempt cocok: **20/20 workflow serta 57/57 job berhasil**, semuanya GitHub Actions `run_attempt:1`. Cakupan kualifikasi terdiri dari **18 workflow / 55 job**; dua workflow / dua job CP7C hanya informasi dan tetap di luar penerimaan CP7C.

`run_attempt:1` tidak berarti setiap kasus hanya dieksekusi sekali. Lima log job lengkap dibaca: empat job dengan pengulangan grup serta K3 untuk memeriksa kutipan F-OPS-05.

| Run / job | Grup | Kasus terkena pergantian hari | Seluruh kasus grup yang dieksekusi ulang |
|---|---|---:|---:|
| 38433019819 / 115419813235 | Note correction browser | 5 | 5 |
| 38432976212 / 115419656262 | P19 scale browser | 3 | 4 |
| 38433044128 / 115419899697 | PL schedule | 26 | 52 |
| 38433059108 / 115419948325 | Prefreeze browser | 7 | 31 |
| **Total** | **Empat grup** | **41** | **92** |

Ke-41 catatan awal tetap berstatus **INCOMPLETE**, dengan `status_before_rollover:PASS` dan alasan `AUDITOR_BUSINESS_DAY_ROLLOVER`. Ini bukan 41 penerimaan PASS pada eksekusi pertama. Catatan kasus lain dalam empat grup itu berstatus PASS. Daftar `first_attempt_final` cocok dengan catatan pertama; tidak ditemukan FAIL atau INCOMPLETE karena alasan lain di empat grup yang diulang tersebut.

Seluruh daftar kasus grup, termasuk 51 kasus yang sebelumnya sudah PASS tanpa penanda pergantian hari, dieksekusi ulang dari salinan baru. Ke-92 hasil ulang PASS, dengan tanggal rencana/sebelum/sesudah yang sama. Daftar ID sebelum dan sesudah identik dan tidak berduplikat dalam masing-masing grup. Tidak ada kegagalan produk yang disembunyikan oleh pengulangan pada empat grup ini.

Untuk ketepatan ringkasan writer, gunakan kalimat: **“Semua workflow pada GitHub attempt pertama; empat grup dieksekusi ulang karena pergantian hari, mencakup 92 eksekusi kasus, 41 di antaranya sebelumnya ditandai rollover.”** Angka 41 dalam receipt memang daftar kasus yang terkena rollover, bukan total eksekusi ulang. Ini penegasan pelaporan, bukan temuan produk atau syarat pembekuan baru.

Dua catatan INCOMPLETE lain pada grup `AUDITOR_BROWSER_CP7_PREFREEZE_LEGACY_RUNTIME_GAP` tetap tersimpan. Itu diagnosis CP6 sebelum pemasangan CP7 yang sudah dibahas laporan utama; bukan bagian dari empat grup di atas dan bukan kredit penerimaan produk.

## Bukti penutup dan status yang tersisa

Empat baris kutipan P11 serta tujuh baris kutipan K3 dalam paket final cocok persis dengan log job lengkap, termasuk timestamp dan hasil pertama. Bukti writer konsisten dengan penutupan independen Astra. Angka **141 eksekusi CI / 139 ID unik**, ditambah satu kasus DOM, pada laporan utama tetap; pemeriksaan lanjutan ini menambah **nol** eksekusi independen dan diberi label `REUSED_WRITER_EVIDENCE_REVIEW`.

Cabang Fable yang diketahui, `audit/fable-cp7-full-d0b9e9c2-20261011`, masih berada di `9fc44978e891c43afe900466bcc5791efb5440c5` ketika diperiksa. Commit itu berisi keputusan owner D13-10..13; jawaban Fable putaran 2 belum terlihat di cabang tersebut. Astra selesai. Penyatuan jawaban kedua auditor dan pembekuan kanonik tetap dilakukan writer/owner setelah jawaban Fable tersedia. Ini tidak mengklaim bahwa tidak ada pekerjaan Fable di tempat lain.

Offsite/Drive tetap ditahan sampai CP7C. Tidak ada perubahan pada cabang writer/integration, hosted, jadwal, deployment, atau produksi; tidak ada pesan dikirim kepada pihak lain.

## Bukti yang disimpan

Direktori `package_followup_20261014/` memuat:

- `GITHUB_RECEIPT_CHECK.json`: perbandingan tujuh berkas, metadata 20 run / 57 job, pencocokan kutipan, dan status cabang Fable yang diperiksa.
- `REUSED_WRITER_EVIDENCE.tar.xz`: lima log job lengkap, receipt, dan dokumen writer yang dibaca. Di dalamnya, `ROLLOVER_REVIEW.json` menyimpan catatan pertama dan catatan ulang setiap kasus pada empat grup, marker pengulangan, serta hasil pencocokan; `LOG_SOURCE_INTEGRITY.json` membuktikan kelima log tersimpan sama dengan respons sumber.
- `EVIDENCE_MANIFEST.json`: SHA-256 arsip dan setiap berkas di dalamnya.

Log pertama dipertahankan tanpa mengubah INCOMPLETE menjadi PASS. Penutupan tetap merujuk laporan independen dan `WRITER_HANDOFF.md` pada commit `57ac8aab`.

Pemeriksaan penyalinan lokal menemukan ekor dua berkas log belum tersimpan. Ekor dipulihkan dari respons sumber yang sama dan kecocokan seluruh isi diverifikasi sebelum publikasi. Ini perbaikan penyalinan bukti, tanpa menjalankan ulang kasus ERP.

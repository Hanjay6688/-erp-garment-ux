# Laporan lanjutan Astra — audit CP1–CP7, kandidat 0b7049d9

**Vonis tetap TAHAN penerimaan penuh.** FIN01 terbukti: pembayaran payroll biasa dapat mendahului akrual, menimbulkan kewajiban bertanggal negatif. Restore database historis CP2 belum dapat diverifikasi. Laporan pertama tetap terkunci; dokumen ini menambahkan hasil uji, pemetaan kebutuhan, observasi detector, dan materi Fable yang baru tersedia.

Kandidat `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`. Laporan pertama: `f70361d551d9dbc9931e330216901a8b702feab5`. Cabang audit: `audit/astra-cp1-7-0b7049d9-20261014`. Produk dan cabang penulis tidak diubah. `feature_complete:false`, `audit_complete:false`, `production_go:false`.

## 1. Cakupan tujuh tahap

| Tahap | Disposisi sekarang | Bukti dan batas |
|---|---|---|
| CP1 | Terverifikasi dengan batas historis | G01 Astra, 15 kategori katalog non-ledger cocok, 19 file historis dipetakan. 51 perintah lama tidak tersedia sebagai SQL terpisah; bukan replay independen setiap migrasi dan bukan fingerprint hosted hari ini. |
| CP2 | **Restore database belum terverifikasi** | Receipt pembukaan arsip 149 anggota sudah dibaca. Tidak ada payload/kunci/database restore historis yang diperiksa auditor. P21 modern tidak menggantikannya. |
| CP3/3.5 | **Tidak lulus: FIN01** | Jalur sah, overlap payroll/Nota dan reuse sumber HPP diuji; penolakan overlap tidak membantah semua varian hipotesis baru Fable. |
| CP4/4.5 | Regresi yang dijalankan memenuhi oracle yang berlaku | Identitas, produksi, WIP, temporal dan aliran nilai melalui baseline dan komposisi final; tidak menyatakan semua workflow historis memasang final hanya karena jobnya hijau. |
| CP5 | Regresi current memiliki bukti; hipotesis tambahan masih terbuka | BUSINESS rework, BB/BE/BF, native source, Auth/browser/race. Tiga SQL/race CP5 historis tidak diklaim semuanya dijalankan identik. R3-01/R3-08 dan alur koreksi yang baru disebut Fable tetap perlu pembuktian. |
| CP6 | Kasus yang dijalankan sesuai oracle current, dengan kualifikasi | AW–BE native; BB–BF mode; range, laundry, aksesori, saldo awal, close/recost dan restoration. Q08–Q14 mempertahankan seluruh hasil merah asli. |
| CP7 | **Tidak lulus penerimaan penuh: FIN01** | Komposisi transaksi/analisis/perencanaan/report/operasi diuji; keterbatasan CP2, hipotesis static, dan gerbang produksi tidak dihilangkan oleh banyak PASS. |

Ini penutupan putaran penilaian bukti yang tersedia, **bukan sertifikat bahwa setiap klausul dan setiap fitur telah lulus**. Bagian yang belum bisa dibuktikan dicatat di §7 dan rekap Fable.

## 2. Ledger kasus dan uji tambahan

Lanjutan: **1.198 eksekusi / 942 nama kasus unik**. Digabung dengan laporan pertama: **2.906 eksekusi / 2.395 nama kasus unik**. Nama yang sama dalam komposisi/group berbeda tetap eksekusi terpisah; tidak berarti desain oracle independen yang berbeda. Hasil carry 76 kasus tetap tidak dieksekusi ulang. Bukti putaran silang lama, Fable, CP1, unit/kernel dan CodeQL tidak ditambahkan sebagai eksekusi bisnis baru.

| Status mentah | Pertama | Lanjutan | Gabungan |
|---|---:|---:|---:|
| PASS | 1639 | 1181 | 2820 |
| CONTROL_PASS | 39 | 0 | 39 |
| DATE_POLICY_REVIEW_REQUIRED | 12 | 0 | 12 |
| COUNTEREXAMPLE | 12 | 1 | 13 |
| INCOMPLETE | 6 | 12 | 18 |
| FAIL | 0 | 4 | 4 |

Ledger: [CASE_LEDGER_CONTINUATION.json](CASE_LEDGER_CONTINUATION.json), [CONTINUATION_NONPASS.json](CONTINUATION_NONPASS.json). Ledger pertama dan hash penguncinya tidak berubah. Perbandingan himpunan case ID, jumlah, status dan count declaration tidak menyisakan masalah tanpa disposisi. Attention memiliki 286 kasus wajib **plus 3 source-admission smoke terpisah** yang kredit required-case-nya nol; ledger mencatat 289 eksekusi, tidak menyebut deklarasi 286 gagal.

| Run lanjutan | Isi | Eksekusi kasus tercatat |
|---|---|---:|
| [38558323653](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38558323653) | AW/AX/AY/AZ/BA/BB/BC/BD/BE native | 290 |
| [38558465155](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38558465155) | 11 suite native CP7, termasuk attention/analysis/transport/scale | 613 |
| [38558702356](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38558702356) | BB/BC/BD/BE/BF, revision, HTTP/race/browser | 291 |
| [38558702641](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38558702641) | Unit, build, shell browser dan dua analisis CodeQL (terpisah) | 0 |
| [38559168896](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38559168896) | FIN07 full detector observation | 1 |
| [38560416364](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38560416364) | Dua RANGE yang belum dipanggil adaptor awal | 2 |
| [38561483350](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38561483350) | Fase HTTP jahit sesudah kualifikasi fixture ACL | 1 |

7 run / 34 job; daftar job dan hasil per langkah ada di [CONTINUATION_JOB_RECEIPTS.json](CONTINUATION_JOB_RECEIPTS.json). Warna job bukan vonis produk. DRAFT: job masih berjalan [115833361095]

Oracle warisan/penulis tetap diberi asal tersebut walaupun Astra menjalankannya sendiri. FIN07 adalah observasi baru Astra yang dimanifestasikan sebelum run; tidak mengubah expected PAY06 atau mengulangnya demi mencari hijau. FULL composition dipakai oleh keluarga/modes/FIN/range/sewing; entry point CP7 lainnya memakai komposisi yang dideklarasikan sumber masing-masing, tidak semuanya dilabeli FULL.

## 3. Seluruh hasil lanjutan non-PASS

[CONTINUATION_QUALIFICATIONS.md](CONTINUATION_QUALIFICATIONS.md) memuat sebab dan bukti individual:

- Q08: lima INCOMPLETE menyimpan kosakata OBSERVED/CONTROL_PASS asli. Observasi tidak dianggap PASS.
- Q09: tiga FAIL AW mengharapkan marker filing dibersihkan setelah recost; kontrak BA W9 justru mempertahankannya. Kontrol current W9 PASS.
- Q10: adaptor BD-range awal tidak memanggil kasus (0 kasus). Dua kasus RANGE yang sebelumnya belum berjalan kini 2 PASS.
- Q11: empat hasil BC memakai fixture sebelum syarat provenance D09. Kontrol D09 current dan browser dengan source lengkap PASS.
- Q12: satu HTTP berhenti saat fixture menghapus USAGE baseline. Fase bisnis pertama setelah ACL fixture dipertahankan tepat: 1 PASS, clone 0, restoration/advisor true.
- Q13: BF-only rollback menolak perubahan CP7 yang sah. Guard dipertahankan; lifecycle CP7 diuji lewat P21.
- Q14: dua browser SALES_MANUAL_13 memakai selector lama; bukti P11 desktop/HP XC2 pada kandidat sama sudah diterima. A6 tidak dibuka kembali.
- FIN07: satu COUNTEREXAMPLE produk, akar yang sama dengan FIN01. Tetap menghalangi penerimaan.

## 4. FIN01: observasi keuangan dan detector diperluas

Run `38559168896`, job `115835678985`, artifact `11891897967`, kasus `CP17-ASTRA-FIN-07-FULL-DETECTOR-OBSERVATION`. Absensi diakui 13 Oktober; pembayaran biasa 375,25 pada 12 Oktober diterima. Payable kontraktor pada cutoff menjadi **−375,25**. Liabilities dan assets laporan berubah **1759 → 1383,75**, balance_difference tetap **0**.

Seluruh **135 baris** detector yang diambil (18 integrity, 49 v267, 68 v268) identik sebelum/saat kejadian dan semuanya issue=0. Report confidence serta close preflight **BLOCKED sebelum dan sesudah**, dengan delapan blocker seed yang sama: empat absensi kosong, tiga pekerjaan belum tercakup payroll, satu payroll belum disetujui. Tidak muncul alarm baru untuk pembayaran mendahului akrual.

**Tidak diklaim bahwa laporan ini READY palsu atau setiap banner UI sudah diuji.** Tidak melakukan business reversal yang API-nya ditebak; strict runner membuktikan rollback transaksi, public boundary dan session/lock bersih. [FIN01_FULL_OBSERVATION.json](FIN01_FULL_OBSERVATION.json) menyimpan pointer dan ringkasan lossless ke Original penuh. S0 tetap berdasarkan salah saji finansial melalui pembayaran biasa dan detector relevan yang tidak menangkapnya; satu akar, bukan tambahan temuan untuk setiap saksi.

Perbaikan tetap pada native owner pembayaran full/partial/final: utang yang dilunasi harus tersedia pada tanggal pembayaran. Kasbon memakai sumber advance eksplisit. Jaga current authority, version, lock, replay, closed-period semantics, dan refusal atomik. Forward fix; migrasi historis tidak diedit.

## 5. Matriks kebutuhan dan pemeriksaan tambahan

[REQUIREMENT_REVIEW.md](REQUIREMENT_REVIEW.md) mencatat **271 requirement**: 254 dalam lingkup sekarang, 17 future/opsional tidak dipilih. Disposisi 254: 247 review dengan bukti terbatas, 3 gate terdampak FIN01, 3 membedakan browser emulasi dari perangkat fisik owner, 1 membedakan beban fixture dari kapasitas pabrik nyata. Semuanya memiliki rujukan bukti; **tidak ada angka “254 requirement PASS”**.

84 charter O/E/M/X dan 10 kebutuhan tambahan owner dipetakan terpisah. JSON menyimpan seluruh EV, sumber dan hash. Sebuah charter E2E bisa memakai beberapa kasus pembukti; itu tidak berarti 84 perjalanan browser kontinu. Contoh exact O01/O02 dan model M/X dipautkan ke 143 private SQL kernel dengan kelas bukti berbeda dari native/Auth/browser. Uji SKN22 Astra yang sudah terkunci tetap bukti satu kisah opening→produksi→penjualan→retur→bayar→koreksi dengan angka independen.

Pemeriksaan tambahan: **203 file / 1727 unit tests PASS**, build/security/static ownership PASS; **6 shell browser PASS**. Kernel F04 143, material pool 12, fabric recipe 28, history parity 28 berada dalam total unit tersebut, tidak dijumlah ulang sebagai transaksi bisnis. Screenshot shell desktop/HP telah dilihat: memang preview data contoh, bukan layar transaksi ber-Auth. Bukti browser nyata ada pada ledger mode.

CodeQL JavaScript/TypeScript dan Actions: SARIF menunjukkan executionSuccessful=true, 0 results, 0 warning/error notifications. Ini hasil dua analisis tersebut, bukan klaim semua bahasa atau seluruh daftar alert repo kosong. [SUPPLEMENTAL_CHECKS.json](SUPPLEMENTAL_CHECKS.json).

## 6. Rekap Fable yang baru tersedia

[FABLE_CONTINUATION_REVIEW.md](FABLE_CONTINUATION_REVIEW.md) mencatat seluruh 31 butir R1/R3/R4 (termasuk INFO), tiga Original chain2/3/4, dan batas laporan draft. R1-05 mendukung FIN01. R1-03 ditolak oleh overlap guard pada probe Astra. R1-01 hanya dibantah untuk reuse sumber payroll identik; varian periode/Mandor berbeda belum ditutup.

Jangan menghitung PASS R3-03 sebagai bukti tanggal klaim benar: chain2 permission denied; chain3 transaksi aborted; chain4 gagal prasyarat BS. Ketiganya belum mencapai settlement bertanggal yang dimaksud. Chain4 membuktikan pengakuan koreksi supplier/payroll/vendor setelah tutup dan marker filing true; receipt correction-nya belum mencapai command sah. Draft Fable dan temuan STATIC tidak diangkat menjadi kelulusan atau bug terbukti tanpa pembuktian.

Astra tetap mengungkap konflik peran PR44/netting: peer acceptance Fable terdahulu dibawa dengan asalnya. Run regresi sendiri tidak dijadikan penerimaan independen atas kode optimisasi yang pernah Astra tulis.

## 7. Daftar terbuka dan batas penerimaan

1. FIN01 belum diperbaiki pada kandidat baru; sampai sekarang hanya kandidat beku ini yang diaudit.
2. CP2: pemegang arsip/kunci perlu memberi bukti restore disposable (schema/owner/ACL, data/control totals, invariant, cleanup), tanpa mengirim kunci ke auditor. Jika tidak tersedia, status tetap belum terverifikasi; pengecualian scope memerlukan keputusan owner, bukan relabel PASS.
3. Hipotesis Fable baru yang belum punya probe sah, khususnya all-BS rework payroll, reopen→re-POST bertanggal, policy denominator, dan tanggal klaim. Daftar lengkap serta prioritas ada pada rekap; tidak meminta penulis “memperbaiki” tuduhan tanpa bukti.
4. Replay 51 perintah historis CP1, inspeksi semantik setiap function body, seluruh oracle CP5 historis identik, dan kontrol negatif setiap detector belum diklaim selesai. Inventaris tekstual dan pemetaan evidence bukan penggantinya.
5. Shadow run data cutover nyata satu periode, preflight hosted terbaru, perangkat fisik owner dan pengawasan live adalah gerbang produksi yang belum dibuktikan di sesi ini. Uji sintetis/skala bukan SLA pabrik.
6. CP7C/Drive, pengiriman provider nyata, dan go-live tetap HOLD/di luar izin. A2 OPEN accepted D13-10; A6 dan F-OPS-05/ASR-OPS yang diterima tidak dibuka kembali.

## 8. Penguncian dan arsip

[CONTINUATION_ARCHIVE_INDEX.json](CONTINUATION_ARCHIVE_INDEX.json) mencatat ZIP Original dan log decoded yang disimpan permanen di branch audit, SHA256, ukuran, anggota ZIP, asal, run/artifact/job, dan Git blob tiap bagian. [verify_continuation_archives.py](verify_continuation_archives.py) memeriksa seluruh byte/CRC; `--extract` merekonstruksi Original untuk membangun ulang ledger/matriks. Artefak Fable diberi asal berbeda. Raw bundle yang tidak dipilih tidak diklaim seluruhnya disimpan; canonical per-case JSON lengkap, SARIF, shell screenshots, dan log yang dibaca dipertahankan.

[PRODUCT_PARITY_CONTINUATION.json](PRODUCT_PARITY_CONTINUATION.json) membuktikan seluruh perubahan sampai control commit terakhir hanya berada pada direktori audit dan workflow auditor. Commit penguncian laporan hanya menambah berkas auditor. Laporan/ledger pertama tidak ditimpa. Tidak ada SQL hosted, Drive, pesan kepada penulis/Fable, atau deployment yang diperintahkan auditor. Hook preview otomatis repo yang sudah dicatat bukan bukti go-live.

Serah-terima tindakan konkret: [HANDOFF_WRITER_CP17_CONTINUATION.md](HANDOFF_WRITER_CP17_CONTINUATION.md). Penerimaan penuh tetap ditahan; keputusan owner dan bukti baru tidak dikarang oleh auditor.

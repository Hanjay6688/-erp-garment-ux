# Audit Sol — CP1–CP7 r4

Kandidat `663f6faefcbb9c70f0f99bbc7e78164e03521329` · tree `023f3554432f80f994439f5d0b8cc164846a2041` · 19 Oktober 2026 WIB.

**Putusan: satu temuan baru S1, satu gap kinerja S2 yang sudah dikenal.** Nota FG_REPAIR yang sah menghasilkan dua alarm CRITICAL salah mandor meskipun sumber dan nilai 6.000 benar. INV-D01/D02/D03 dan integritas sambungan S3 gagal pada satu akar masalah ini. Perbaikan r4 yang ditargetkan mempunyai bukti 341 kasus CP17 PASS; hasil itu tetap sah dalam lingkupnya dan tidak menutup counterexample baru. `feature_complete=false`, `audit_complete=false`, `production_go=false`; CP6 tetap CLOSED dalam kontrak yang diterima.

## Ringkasan keparahan dan cakupan

| Kategori | Putusan |
|---|---|
| S0 | 0 temuan baru |
| S1 | 1 temuan baru: SOL-R4-001, false CRITICAL pada Nota FG_REPAIR sah |
| S2 | 1 gap dikenal tetap terbuka: KNOWN-P19-DIRECT-LATENCY |
| S3 | 0 temuan baru |
| 82 invariant | 72 PASS / 3 FAIL / 7 INCOMPLETE |
| 29 skenario | 22 PASS / 7 INCOMPLETE |
| 20 sambungan | 19 PASS / 1 FAIL; S3 gagal pada integritas, nilai finansialnya tetap tepat |

PASS dibatasi pada lingkup tertulis per baris. Jumlah testcase, ID, route dan fungsi tidak menjadi persentase ERP. Ketiga gate false bukan pernyataan bahwa semua fitur rusak. Kekurangan bukti, keputusan CP7C dan cacat produk dipisahkan dalam [FINDINGS](FINDINGS.json), [batas terbuka](OPEN_BOUNDARIES.json) dan [handoff writer](WRITER_HANDOFF.md).

## Identitas, lingkungan dan metode

Sol adalah auditor penilai lane ini; root hanya mengoleksi dan memublikasikan secara mekanis. Tidak ada isi branch, laporan, run, artifact atau komentar peer r4 yang dibaca sebelum seal sendiri. Sol r3 berasal dari seal `ff6374ad6edef19896c32258e3f30172a95069bd`, dengan kredit runtime r4 nol. CROSS_AUDIT writer terhadap r3 adalah keterangan writer.

Panduan ProMax dibaca seluruhnya, SHA256 `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`, bersama own HANDOFF_SOL, README, keputusan owner, CLAUDE dan ERP best practices; tidak ditemukan AGENTS. D17-2 menetapkan audit dahulu, finance writer berikut pada branch terpisah, target 3 detik tetap. D13-9a menunda patch backup replacement ke CP7C; D14-9 mempertahankan kompatibilitas grant/session Native DB sampai CP7C.

Writer pada freeze `2026-10-19T04:03:48Z` tetap `5eda90e10b2e87485ab710e9fd9ffa68d81a3565`; sembilan path setelah kandidat adalah dokumen, tujuh root produk sama. Addendum audit mempertahankan waktu pengamatan asli itu. Dibanding r3, 34 file produk berubah; direktori `supabase/` identik, tetapi bundle Python dapat mengganti definisi Native dan tetap ditinjau. SHA/tree produk sebelum/sesudah, workflow SHA serta harness SHA dicatat terpisah; GITHUB_SHA tidak dipalsukan. Tidak ada perubahan produk, main, writer, hosted, produksi atau pencarian kredensial.

CI memakai Ubuntu 24.04, Python 3.12 (log 3.12.15), psycopg 3.2.10, Supabase CLI 2.116.0, Node 22.23.3 dan Chromium melalui Playwright. PostgreSQL client 17 terpasang; versi server tidak diekspor sebagai pengamatan terpisah dalam bukti terakhir, sehingga tidak disamakan dengan versi client/image. Native, Auth HTTP dan browser memakai stack loopback/salinan disposable. Scratch lokal tidak memiliki psql/docker; pemeriksaan lokal hanya sumber, parsing, hash, hitungan dokumen dan gate metadata murni.

Perintah aktual mencakup `python ../auditor/scripts/cp7_cp17_fix_probe.py`, `python ../sol/audit/sol_cp17_r4/invoice_journey_q3_qualification.py`, entrypoint finite/Q2, derived dan dispute pada manifest masing-masing. Broad matrix memakai `python ../auditor/scripts/${{ matrix.probe }}`; daftar exact ada pada `REGRESSION_PREEXECUTION_MANIFEST.json` dan workflow yang disimpan dalam snapshot source. Instalasi memakai `npm ci`, dependency Python terpin serta `npx playwright install --with-deps chromium`. Register dan snapshot source mengikat perintah, candidate, workflow, versi alat, run/attempt dan hash; nama branch saja tidak dipakai sebagai identitas.

## Temuan SOL-R4-001 — Nota FG_REPAIR sah ditandai salah mandor

**S1, OPEN, level NATIVE_QUALIFIED.** Asal bukti: INDEPENDENT_NATIVE_RERUN dan INDEPENDENT_SOURCE_REVIEW. Panduan INV-D02 menetapkan false alarm pada buku benar sebagai S1. Ditemukan pada kandidat ini; tidak diklaim baru diperkenalkan oleh r4.

Lokasi resolver awal: `supabase/migrations/20260901161322_erp_v2_6_15_payroll_component_entitlement.sql:187`. Definisi runtime yang diekspor hanya menghubungkan source PRODUCTION dan REWORK. Mesin current sudah mendukung FG_REPAIR melalui `scripts/cp6_ax_build.py:101–159`, `scripts/cp7-src/payroll/source.sql:41` dan positive Nota `scripts/cp7_nota_cases.py:39–47`. Rantai dampaknya adalah repair wage sah → Nota SAVE/POST → payroll_work_items FG_REPAIR → resolver detektor tidak mengenali sumber → dua false CRITICAL `payroll_work_wrong_contractor`.

Reproduksi Sol yang dibekukan sebelum eksekusi:

1. Buat dua sumber repair Native sah: 2 PCS dan 1 PCS, tarif 2.000; simpan lalu post Nota publik dengan kedua source card yang tepat.
2. Baca actual payroll CALCULATED 6.000 dan kedua work line: qty 1/2, amount 2.000/4.000. Mandor dan komponen payroll sama persis dengan wage; wage dan receipt POSTED.
3. Seluruh 167 detektor bernilai 0 sebelum repair, sesudah repair dan sesudah DRAFT. Sesudah POST, hanya `run_v263a_payroll_integrity_checks:payroll_work_wrong_contractor` menjadi **2, severity CRITICAL**, padahal expected buku sehat 0.
4. Rollback mengembalikan seluruh 167 menjadi 0; subject, protected facts/guards serta tiga komponen restore utama cocok. Tidak ada PWI, source, jurnal, grant, guard atau trigger yang diedit langsung untuk membentuk anomali.

Bukti awal: run `39199375501`, artifact `12163127220`, membuka alarm sebelum counter opening sehingga tetap 8 PASS / 1 INCOMPLETE. Konfirmasi: run `39200571137`, job `117892503808`, artifact `12163559008`, raw **1 COUNTEREXAMPLE / 1 PASS**, protokol bukti lengkap. ZIP artifact SHA256 `e990bbc8dd48000d6947d847ee8dc84b9afef969ca7034c539f7721e6052bdf7`. Lihat [review actual lineage](PAYROLL_DETECTOR_DISPUTE_RESULT_REVIEW.json); COUNTEREXAMPLE tidak diganti PASS. Opening-only 65/0/OPEN pada run yang sama lulus sebagai kualifikasi terpisah; delapan PASS awal tidak diulang.

Dampak terbukti adalah kegagalan audit/integrity pada buku yang benar. Nilai 6.000 tidak salah; dampak blokir pembayaran atau tutup periode UI **belum diverifikasi**. Fingerprint runtime membandingkan stock/HPP/jurnal sebelum/sesudah Nota, tetapi laporan mengekspor assertion sukses, bukan seluruh nilai fingerprint. Actual PWI/wage/header dan semua 167 row detektor diekspor.

**Perbaikan writer:** tambahkan resolver sumber FG_REPAIR melalui wage/receipt, mandor/komponen/status yang benar pada checker Native; pertahankan deteksi orphan dan wrong-contractor nyata. Sesuaikan assembly AX/installer, pin definisi, capture serta restore yang benar. Jangan menyaring alarm atau mengubah migration historis beku sembarang. Uji dua line 6.000 harus membuktikan 2 sebelum fix dan 0 sesudah, disertai kontrol negatif nyata dan seluruh output detektor. Verifikasi install/restore serta invariants keuangan, stock dan HPP. Satu akar ini mengenai INV-D01/D02/D03, S3, FUN-039 dan FUN-041; tidak dihitung menjadi beberapa finding.

## Hasil uji dan asal bukti

| Kelompok | Hasil dibaca | Asal dan batas |
|---|---|---|
| CP17 current, run 39184657689 | 341 ID PASS = 161 Native / 39 jadwal-race / 27 Auth HTTP / 57 ordinary / 57 Enteng build | INDEPENDENT_NATIVE_RERUN. Fixture/oracle writer dinyatakan; 39 jadwal tidak otomatis 39 race ketat. |
| Broad current | 66 laporan, 40 run bisnis, 2.121 kemunculan kasus, 1.487 string ID unik | Eksekusi Sol atas oracle writer, ditambah hitung ulang captured document. Alias/copy tidak dihitung dua kali. |
| Kontrak Sol | 28 ID: 27 PASS / 1 COUNTEREXAMPLE; 11 bisnis, 1 pure-helper, 14 detector-control, 2 prevention-only | Manifest dan expected Sol terpisah. Sebelas bisnis termasuk satu counterexample; bukan 11 PASS. |
| Q1 metadata | 4 ID, 5 row succeeded/start/end, wait True, schedule 0/copy 0 | Pengamat baca-saja pada kasus existing, bukan kasus bisnis baru. Row sudah selesai ketika wait dipanggil; bukan race polling baru. |
| Fresh transaction guard | OWNER/ADMIN 2 PASS ID, 8 panggilan dengan txid entry NULL | STAFF 0 panggilan setelah dua fixture gagal. Sesudah call txid teralokasi; bukan benchmark/no-allocation. |
| Build/static | 1.861 tes / 221 file; CodeQL 4 bahasa, 0 result dan rules 95/23/103/50 | C/C++ hanya fixture jam. Mocked UAT 48 baris/46 eksekusi unik tidak menggantikan real Auth. |
| Writer reused | 116 run / 115 workflow / 179 job, 94 success / 22 failure | REUSED_WRITER_EVIDENCE, runtime Sol 0. Dua puluh historical holds, satu artifact AF expired dan 4 old CP6 INCOMPLETE dipertahankan. |
| Retained CP6/r3 | Sumber canonical/installer dan supabase accepted identik; dependency r4 dipilih ulang melalui F03/CP17/P21 | REUSED_AUDITOR_LOG_READ, runtime r4 record lama 0. CP6 CLOSED tidak dibuka ulang hanya karena literal suite lama tidak diulang wholesale. |

Jumlah akhir provider: **60 run terminal, 50 SUCCESS / 10 FAILURE**, seluruh run_attempt 1; 90 log exact decoded, 120 artifact metadata, 119 ZIP diunduh. Sebanyak 1.399 member teks hasil diverifikasi. [Hitungan](ASSESSMENT_COUNTS.json), [CP17](CP17_RESULT_REVIEW.json), [broad](RESULT_REVIEW.json), [writer](WRITER_CI_REVIEW.json) dan [retained CP6](CP6_SCOPE_RETENTION.json) memisahkan satuan hitungan.

Recorder identitas terakhir mewarisi static counts CP17 341, declaration `53fb2f86…` dan label WRITER_DECLARED_CASES. Itu bukan deklarasi/eksekusi 341 pada run dispute: laporan kualifikasi mengikat manifest Sol serta tepat dua actual ID. SHA/tree/root/workflow/run before/after tetap valid. Original tidak diubah.

## Retest bisnis dan hasil lama

R4-01 menutup tepat 25 public legacy Data API dengan 403/42501 serta facade sah 200; sensus 69 adalah 25 CLOSED / 40 KEEP / 4 reminder. Empat public pool wrapper termasuk yang tertutup Data API; grant/session Native DB tetap D14-9. R4-02 membuktikan 10+2−2=10, HPP 120÷10; active usage 2 menolak reopen dan cancel melepas. R4-03 membuktikan late commit ID 24183 di bawah cutoff 24184 mengubah marker; filter/reload tepat, bukan immutable transaction snapshot. R4-04 cocok 47 menu; 290 rasio WIP minimum **5,1718195**, ambang 4,5; 12 sampel Cutting >5,85. Ordinary detail ditimpa file Enteng terakhir; helper melewati opacity/disabled/image/unparsed text dan form pool yang tidak dibuka. Enteng 1.364 request loopback tanpa error bukan bukti hosted.

PO 999/1000/transisi/1001/10000 tepat dan bounded sekitar 9–13 ms; UUID replay satu efek. Cash tanggal ekonomi/buku, pay≥accrual, cutover WIB, pool cancel/replacement dan review token diretest pada guard global. Pool 1.000/10=100, cancel 0, replacement 20 PCS=50; dua PO masing-masing 500. OLD 2×(3+1)=8, NEW 2×(5+1)=12 dan enam PCS NEW=36, snapshot upah lama utuh. QC SKU dan nota 6.000−2.100=3.900 tetap benar; finding integritas di atas membatasi klaim end-to-end Nota/payroll.

Ordinary Q3 pada tiga viewport mempunyai total 124, FG 64/WIP 60, 12 write. Claim mobile total 130, FG 64/WIP 66: estimasi potong kelima 2 tetap WIP; invoice hanya empat GOOD×2=8. Claim 2 adalah AP Vendor Dr / Other Expense Cr. Credit/cash serta seluruh inverse selesai, AP 0/cash 8, tepat 18 write. Free same-product rewash first PASS bergerak partial FG 0 → complete FG 2 → inverse FG 0 tanpa AP/upah/jurnal rework baru. Native start diberi asal; Chromium viewport bukan perangkat Apple fisik.

Matcher finite membuktikan opening 8→projected 7/target 100→gap 93, forged color/CANDIDATE dan extra matching ditolak; satu legal draft cutting 2 tidak mengubah stock/uang/HPP. Raw AP 12,6 `999999999999.999998` dan `.999999` tetap tepat, masing-masing satu credit GL `1000000000000.00`. Scale 6, digit ketujuh refusal, sekitar 32-bit sen, maksimum Laundry numeric(18,2) DRAFT/two-line dan 27 actual client-helper controls diuji; bukan maksimum POST/cash atau klaim semua route numerik tercakup.

## Kinerja, operasi dan risiko tambahan

KNOWN-P19-DIRECT-LATENCY **OPEN S2**: run `39185235564`, artifact `12159513142`, measurement `P19S_BROWSER_100_{1,30,100}_CAPTURE_WITH_FINANCE` = **4.296,9 / 4.251,8 / 4.664,5 ms**, sasaran ≤3.000 ms. Direct operational 300 =5.453,6–7.022,9 ms; honest refusal sekitar 8 detik pada ukuran lebih besar bukan capacity PASS. Writer berikut mengoptimalkan pada branch terpisah sesuai D17-2, mengukur ID/ukuran sama dengan source/current authority/hash/caps utuh. Tidak menaikkan timeout, sampling atau memotong data.

Staged/background mempunyai pengecualian owner yang bernama: staged 5.000 selesai 26 halaman dalam 76,509–98,374 detik, progress 2.439–2.904 ms dan reopen 1.342–1.399 ms. Jangan menyebut seluruh perjalanan ≤3 detik. K4/K6 dan Q1 membuktikan terminal metadata/cleanup pada lingkup exported; Barrier tidak dijadikan bukti wait/PID. K2 memakai metadata aging, bukan tujuh hari nyata.

P21 restore used-backup/preinstall ke salinan baru cocok. Used-data uninstall ERP/platform/Auth/schema FALSE, 116 tabel berubah, meskipun katalog/ACL pulih; gunakan restore salinan baru yang terbukti. K3 boundary B masih menulis replacement sebelum mismatch. KNOWN_REPLACEMENT belum terpasang sesuai D13-9a; raw PASS bukan no-write safety. Belum ada hosted/Drive/cutover/shadow period nyata.

## Hasil merah yang bukan bug produk

| Run/kelompok | Klasifikasi | Disposisi |
|---|---|---|
| 39185988432 | AUDITOR_TOOL | STAFF role_code custom salah; OWNER/ADMIN PASS dipertahankan. |
| 39188635131 | AUDITOR_TOOL | STAFF existing inactive/duplicate sebelum call; tidak ada percobaan ketiga/aktivasi profil. |
| 39191503650 | AUDITOR_TOOL | Import jsonschema sebelum 4 kasus metadata; instalasi produk prerequisite sudah selesai. Satu retry dependency 4.25.1 terdeklarasi. |
| 39193178808 | AUDITOR_TOOL | Observer membaca core vendor invoice sebelum BD DRAFT diposting; 3 INCOMPLETE tetap. |
| 39193738642 | AUDITOR_TOOL pada claim | Oracle 128 menghilangkan outstanding estimate 2; kontrak 130. Free-rewash first PASS tidak diulang. |
| 39195171465 | AUDITOR_TOOL | Reason reset setelah remount, label/main capture Q2; 4 INCOMPLETE tetap. Q3 terpisah; main_text kosong tidak membuktikan crash. |
| 39195943779 | AUDITOR_TOOL | Tiga finite error rawAP vs GL-cent, TypeScript API, selector daily; lima PASS tidak diulang. |
| 39197469845 | AUDITOR_TOOL | Prefix accessory menghasilkan SKU 64>varchar 60 sebelum fixture; tiga PASS tidak diulang. |
| Attention job 117846167103 | INFRA_RACE_RERUN_PASSED | Port 54322 collision sebelum kasus, satu bootstrap retry; original failure dipertahankan. |
| Writer historical 20 holds | GUARD_BY_DESIGN / scope historis | Successor/current dinilai terpisah; guard tidak dilonggarkan. |
| Writer AF expired / old CP6 4 INCOMPLETE | Bukti unavailable / batas historis | Tetap tercatat, tidak mendapat PASS dari run lain. |

Dua FAILURE berikutnya **bukan** AUDITOR_TOOL: run 39199375501 menangkap false alarm pada predecessor sah; run 39200571137 mengonfirmasi COUNTEREXAMPLE S1. Seluruh hasil pertama, genuine tool diff, versi oracle dan manifest disimpan. Tidak ada identical rerun setelah kasus demi hijau. [Review 90 log](OWN_BOOTSTRAP_REVIEW.json) membedakan bootstrap dari qualification entrypoint yang gagal.

## Matriks, yang belum diperiksa, dan pemilik tindakan

[Invariant](INVARIANT_MATRIX.md), [skenario](SCENARIO_MATRIX.md), [sambungan](CHAIN_MATRIX.md) serta [inventaris](FUNCTION_DETAIL.md) mengikat kebutuhan→positif→penolakan→koreksi/revisi→hilir pada 57 kebutuhan dan 47 route. S3 FAIL hanya integritas Nota/payroll; periode/pay UI blocking tidak diasumsikan.

Sebanyak **21/167** identitas detektor mempunyai exact 0→+1→0, dengan seluruh keyset tiap fase dan rollback. Sisa 146 sensitivitas: 132 fact/lineage belum dieksekusi, 11 catalog/access tetap held, 1 schema/DDL, 2 dicegah Native guard. Guard refusal adalah pencegahan, bukan sensitivitas PASS. [Disposisi per ID](DETECTOR_DISPOSITIONS.json) menyimpan actual predicate, hash, relasi, alasan dan pekerjaan berikut. Source/fact counter yang belum dijalankan tidak dinyatakan mustahil atau semuanya ditunda owner. False-positive healthy-book dan partial sensitivity adalah dimensi terpisah; INV-D01 dominan FAIL karena S1.

Invariant INCOMPLETE: T02, T04, L07, M01, M03, M04, D04. Skenario INCOMPLETE: 07, 09, 16, 19, 21, 22, 29. Batas bernama mencakup Native legacy CP7C; general as_known belum diimplementasikan; loaded export/cache setelah revoke yang tetap held; one-third allocation yang belum dibuktikan; actual midnight; real opening/cutover/shadow serta hosted baseline; STAFF fresh ALLOW dan physical Apple UAT. Tiga desain r3 yang tertahan tidak dilanjutkan lewat nominal/transport lain. Owner/operator, writer dan auditor memiliki tindakan terpisah di OPEN_BOUNDARIES. Tidak ada current CI atau qualification yang masih menunggu.

## Pertanyaan owner dan ringkasan owner

Tidak ada keputusan baru yang perlu dijawab. D17-2 sudah menetapkan audit dahulu dan performance writer berikut pada branch terpisah dengan target 3 detik tetap; D13-9a/D14-9 dan go produksi tetap CP7C. S1 memerlukan perbaikan dan retest, bukan permintaan mematikan alarm atau menerima risiko.

Audit menemukan satu S1: Nota repair yang sah memicu dua alarm salah mandor. Sumber dan nilai 6.000 benar, sehingga masalah yang terbukti ada pada pemeriksaan integritas, bukan bukti pembayaran salah. Perbaikan r4 yang ditargetkan mempunyai 341 kasus PASS dalam lingkupnya. Finance masih 4,25–4,66 detik pada 100 target terhadap sasaran 3 detik dan menjadi pekerjaan writer berikut di branch terpisah. Semua 60 run telah dibaca, termasuk sepuluh hasil merah yang asalnya dijelaskan. Sebanyak 21 detektor mempunyai kontrol exact, sedangkan sisa sensitivitas dan batas CP7C tetap terbuka. CP6 tetap CLOSED; integrasi CP7 dan produksi belum diterima. Writer menerima langkah perbaikan serta uji ulang konkret di handoff.

## Bukti durable dan seal

Paket **Sol-r4-bukti-20261019.zip** tersimpan dan diverifikasi CRC/member/hash: 67.953.664 byte, SHA256 `11969e3f56e05a7870c0fb2f4d60664435c81b3c180f24a83921c4a652826a0f`. [Whitelist FINAL](RAW_EVIDENCE_WHITELIST.json) mengikat 2.104 berkas / 1.178.571.633 byte raw, termasuk Original teks, tiga ledger, log, receipt, expected/provenance dan snapshot exact source. [Receipt](RAW_EVIDENCE_ARCHIVE_RECEIPT.json) mencatat penyimpanan sukses. Laporan/handoff/matriks/seal berada di commit kecil terpisah agar tidak membentuk hash melingkar.

Delapan payload PNG build dikecualikan; derivative TEXT_ONLY menyimpan source path/hash dan attachment count/hash tanpa penerimaan visual. Satu built-app distribution sengaja tidak diunduh. Exact decoded log hash bukan hash ZIP-log provider; tambahan LF pada 22 log writer diungkap dalam capture metadata. Draf standalone matcher ditarik, tidak pernah dijalankan; komponen finite yang benar-benar dieksekusi tersimpan. Static maps/source snapshot tidak menambah kredit runtime. [Indeks bukti](EVIDENCE_INDEX.json) dan [seal](SEAL_MANIFEST.json) mengikat jalur serta hash penyerahan.

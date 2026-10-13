# Astra — retest independen CP7, kandidat 7a0b4a90

**LAPORAN TERKUNCI — retest temuan dan delta; keputusan HOLD, `production_go:false`.**

ASF-F01 sudah terverifikasi selesai pada kandidat ini. Empat kontrol asli dan 15 kontrol tambahan memenuhi oracle, serta pemeriksaan empat mode memenuhi delapan kontrol kelompok. Peringatan pergantian hari juga muncul dan terbaca lewat API GitHub. Dari 14 pemeriksaan delta buatan Astra, 13 lulus dan satu memperlihatkan celah backup dengan prasyarat admin yang bekerja bersamaan. Dalam kasus itu, database pengganti scratch terhapus walaupun tidak bertanda milik alat; sumber ERP uji tetap utuh. Dashboard terhubung pada desktop/HP, pembatasan OWNER, dan pembersihan analisis lulus. Dua label merah savepoint berasal dari penghitung hasil auditor sendiri dan dijelaskan dari bukti asli tanpa mengulang transaksi. PR44 tetap memerlukan penerimaan auditor yang tidak menulisnya. `production_go:false` tetap.

## Identitas dan batas

| Acuan | Nilai |
|---|---|
| Produk diuji | `7a0b4a90af234a906d3cda7fc8ec9fd411a15dd2` |
| Tree penuh | `05d4ccd84ed7faedede1d9161cd08952591659b2` |
| Audit sebelumnya | `d0b9e9c2e41a9f0f3a138346887434fd7d3c14f0`; laporan terkunci `e800e016281c2f2b203d23505e0ca10978039fbc` |
| Paket instruksi pada awal retest | Writer docs `5656f072036dfb8e7d4cb31013da8e57e425c240` |
| Selisih diperiksa pada awal retest | 49 berkas sejak audit pertama, 28 di luar `docs/`; kandidat → `5656f072` hanya delapan berkas di `docs/` |
| Tempat eksekusi | Cabang baru `audit/astra-cp7-retest-7a0b4a90-20261013`; candidate checkout terpisah dan dipin dalam setiap workflow |
| Infrastruktur | Supabase/PostgreSQL sekali pakai dalam GitHub Actions; Auth, PostgREST, Chromium sesungguhnya pada loopback |
| Independensi | Tidak membaca laporan/log Fable putaran ini; masukan tentang perbaikannya berasal dari paket writer yang diminta owner |

[SOURCE_RECEIPT.json](SOURCE_RECEIPT.json), [SOURCE_BINDING_SUPPLEMENT.json](SOURCE_BINDING_SUPPLEMENT.json), dan [DELTA_COVERAGE.json](DELTA_COVERAGE.json) mencatat identitas, hash direktori produk, dan pemetaan 28 berkas. Tidak ada perubahan kode produk, cabang writer/integration/main, deployment, atau SQL hosted. Jadwal/backup uji hanya di cluster sekali pakai. Hasil instalasi dari baseline terarsip bukan bukti kesetaraan dengan keadaan hosted terbaru.

**Pembaruan writer saat retest berlangsung.** Setelah owner menanyakan gelombang revisi berikutnya, HEAD writer diperiksa menjadi `5e96cbcf02e9cf6d4464b80d1de08a008f826cae`. Kandidat `7a0b4a90` sudah memuat perbaikan Fable sebelumnya. Sesudah kandidat ada sepuluh berkas di luar docs yang berubah: alat pencatat/periksa selisih, diagnosis, tes cleanup/jadwal, dan workflow. Pemeriksaan `git diff` memastikan `src/`, `supabase/`, `scripts/cp7-src/`, alat backup, serta helper business-day tetap identik. Audit runtime ini tetap terikat **7a0b4a90**; tambahan alat uji terbaru belum mendapat PASS independen. Tidak membaca laporan atau log peserta putaran ini. Lihat [LATER_WRITER_DELTA.json](LATER_WRITER_DELTA.json).

## Hasil tes Astra sendiri

### ASF-F01 — CLOSED

Asal bukti `INDEPENDENT_NATIVE_RERUN` / `INDEPENDENT_TOOL_RUNTIME`; oracle Astra. [Run kontrol](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353995484), [run empat mode](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38354144743), dan [validasi Original serta anotasi](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38355291749).

- Probe asli dijalankan **byte-identik**. Versi lama menghasilkan dua PASS dan dua COUNTEREXAMPLE yang memang diharapkan sebagai pembanding negatif. Kandidat baru menghasilkan 4/4 PASS. Nilai 10.001 vs 10.000 sen tetap kesalahan sintetis alat uji; tidak diklaim sebagai angka salah ERP.
- Tambahan 15 kontrol mencakup kelompok campuran FAIL/COUNTEREXAMPLE/INCOMPLETE, kegagalan pemulihan/pembersihan/kasus hilang, status tidak sah, error yang sudah ada, larangan percobaan ketiga, kegagalan pada percobaan kedua, serta escaping dan pembatasan anotasi pada Actions. Ada 17 baris ringkasan alat karena dua baris membungkus empat kontrol asli pada masing-masing versi; bukan 17 oracle bisnis baru.
- Savepoint, dua sesi PostgreSQL, Auth/RPC, dan browser masing-masing memeriksa dua kelompok: kegagalan asli bercampur pergantian hari tidak diulang; PASS yang hanya dibatalkan guard tanggal boleh diulang tepat sekali dengan hasil pertama tersimpan. Total delapan kontrol kelompok, 20 ID kasus dalam kelompok, dan 24 eksekusi karena empat pengulangan positif yang disengaja.
- Tanggal disimulasikan pada pembaca tanggal alat atau input tanggal rencana browser. Jam dan fungsi tanggal produk tidak diubah. Ini tidak diklaim sebagai run yang kebetulan melewati tengah malam nyata.
- `cp7_ci_receipt.py` kandidat dibaca lewat API pada run Astra saja: dua anotasi kontrol dan delapan anotasi mode nyata, terdiri dari lima `KEPT_FIRST_RESULT` dan lima `RERUN_FROM_FRESH_COPY`. Pengulangan sintetis ini dipisahkan dari regresi bisnis.

**ASRA-T01 — AUDITOR_TOOL, CLOSED melalui pemeriksaan Original.** Penghitung luar buatan Astra salah membaca objek `session_leaks={advisory_locks:0, advisory_lock_keys:[], other_sessions:[]}` sebagai kebocoran karena objek tersebut tidak kosong. Kedua kelompok savepoint ditandai COUNTEREXAMPLE di laporan awal meskipun setiap isi field dan setiap gate pemulihan benar. Original tetap utuh (SHA-256 `bb77504ca0a27ce9ee035844e681be6c550313cd565f450eb31e255a6028d3f0`) dan job merah tetap ada. Validator terpisah memeriksa semua delapan kelompok, setiap status/error/tanggal/transport/pemulihan, serta enam kontrol negatif yang menolak bukti rusak. Hasilnya 8/8 PASS. Tidak ada kasus produk dijalankan ulang, dan tidak ada guard yang diubah. Lihat [validate_asf_original.py](validate_asf_original.py).

Probe lama menulis SHA kandidat lama secara hardcoded dalam metadata laporannya. Metadata ini tidak diubah demi mempertahankan byte probe asli; receipt luar dan hash modul mencatat checkout yang benar untuk kedua eksekusi. Tidak ada bukti versi lama yang dipindahkan labelnya menjadi bukti versi baru.

### Delta aplikasi dan operasi — 13 PASS, 1 COUNTEREXAMPLE

[Run mandiri pertama](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38354577233). Oracle Astra; database canary, kontrol hak akses, dan browser dibuat Astra. Pembuatan fixture analisis sah memakai helper writer yang dicatat terpisah dari oracle.

| Bagian | Hasil | Yang dibuktikan |
|---|---|---|
| Cleanup dan immutability | 3 PASS native, 1 PASS dua sesi | Hanya pekerjaan A dibersihkan, B dan hasil final utuh, Original dapat dibuka lagi; ulang aman; GUC palsu tidak memberi akses anon/authenticated/service_role; operasi analisis lain berjalan 0,0166 detik ketika transaksi cleanup masih terbuka |
| Batas CLI jadwal | Termasuk tiga native di atas | Nama database salah ditolak pada install/verify/uninstall; izin install/uninstall yang tidak diberikan juga ditolak; tidak memasang jadwal |
| Backup | 4 PASS, 1 COUNTEREXAMPLE | Database asing sejak awal dan yang muncul sesudah pemeriksaan ABSENT terlindungi; snapshot tetap valid saat sumber ditulis; scratch milik alat dapat dipakai ulang; penggantian scratch lama di tengah proses masih bocor |
| PL-5 melalui Auth/RPC | 1 PASS | ADMIN membaca tetapi tidak menyimpan; OWNER menyimpan dan replay; setelah OWNER menjadi ADMIN, UUID lama dan baru sama-sama 403, jumlah revisi tetap |
| Dashboard terhubung | 4 PASS browser | OWNER dan ADMIN pada desktop dan HP: tidak ada angka/contoh grafik, pesan belum tersambung tampil, tidak ada overflow horizontal |

Snapshot batas/database/fungsi kembali benar dan pembersihan Auth serta salinan lulus. Empat screenshot diperiksa secara visual. Bukti HP adalah emulasi Chromium, bukan perangkat fisik atau Safari.

**ASR-OPS-01 masih OPEN.** Detail kondisi admin, reproduksi, dampak terbukti, batas klaim, dan kriteria retest ada di [ASR_OPS_01.md](ASR_OPS_01.md). S0 bersyarat mengikuti definisi kerusakan permanen data pada §8; frekuensi kejadian tidak diklaim. Ini bukan bukti pengguna ERP biasa dapat melakukannya. Tidak ada bukti uang, HPP, jurnal, atau stok sumber ERP berubah.

## Crosscheck perbaikan yang dilaporkan writer/Fable

Ini uji silang dengan kasus Astra dan eksekusi ulang skenario writer, **bukan** klaim telah menjalankan berkas skenario asli Fable atau membaca hasil putaran terbarunya.

| Acuan | Disposisi Astra | Asal bukti penutup/batas |
|---|---|---|
| F-OPS-01 scratch asing | Kasus dasar sudah lulus; keluarga masih memiliki residual ASR-OPS-01 | Canary Astra empat kontrol, satu variasi penggantian gagal; K3 writer dijalankan Astra |
| F-OPS-02 cleanup menghambat analisis | Perbaikan terverifikasi pada kasus yang diuji | Cleanup A terbuka, step B tetap berjalan; scope/immutability/reopen Astra; K3 dan consumer staged |
| F-UI-01 angka contoh dashboard | Terverifikasi disembunyikan pada mode terhubung | Empat browser Astra desktop/HP OWNER/ADMIN; shell DOM |
| F-OPS-03 snapshot backup | Terverifikasi pada penulisan bersamaan | Backup satu baris snapshot cocok, sumber sudah dua baris; K3 race |
| F-OPS-04 database jadwal | Terverifikasi | CLI asli dijalankan dengan mismatch; refusal sebelum mutasi jadwal |
| F-AN-01 >5.000 target | Terverifikasi penolakan sejak request | `P19G_STAGED_BOUNDS_VS_SINGLE`, error `CP7_ANALYSIS_STAGED_TARGET_LIMIT`, dijalankan ulang Astra |
| F-PAY-01 tanggal payroll WIB | Kasus aktif lulus; batas jam uji dicatat | Pada settlement, zona yang harinya tertinggal dari WIB menerima hari WIB saat ini. Cabang zona yang sudah besok tidak aktif pada jam run (`session_day_ahead_of_wib_refuses_wib_tomorrow=false`); tidak diklaim lulus. Token/card dibandingkan di tiga zona |
| F-AP-01 kredit ke nota berikutnya | Mengikuti keputusan owner 2 Okt; lulus | `RF_OVERPAID_CREDIT_TO_NEXT_NOTA`: bayar 1.000 dikoreksi menjadi 800, kredit 200 ke nota berikutnya, tanggal asli sebelum kedatangan nota berikutnya sesuai keputusan, kas tidak berubah; inverse kredit juga lulus |
| F-TOOL-01 anotasi | Terverifikasi | Sepuluh anotasi aktual terbaca dengan script kandidat; bukan receipt writer yang dipakai sebagai bukti |
| F-TOOL-02 / PR44 | Catatan maksud saja; penerimaan independen DIKECUALIKAN | [PR44_AUTHOR_INTENT_NOTE.md](PR44_AUTHOR_INTENT_NOTE.md) |
| F-TOOL-03 fixture kalender CP6 lama | Tidak dipindahkan menjadi bug produk baru | Kasus lama di luar delta tidak dijalankan ulang untuk penutupan CP6 |
| F-UI-02 runtime CP6 saja | Dibedakan dari UI CP7 pada komposisi benar | Own browser full composition lulus; F03 prefreeze mengarsip diagnosis CP6 terpisah dari kredit kasus produk |
| F-DOC-01 panduan | Review statis | Panduan lengkap dan aturan baru dibaca; tidak menggantikan pengujian runtime |
| OBS-01 PL5 owner-only | Terverifikasi | Own downgrade/replay; PL5 20/20, termasuk snapshot policy versi 3 pada rencana yang diterapkan |
| OBS-02/03 di luar delta | Tidak dibuka ulang; tidak diberi PASS baru | Batas kontrak snapshot dan inventaris helper CP7.5 tetap sesuai keputusan/penempatan sebelumnya |

## Regresi writer yang dijalankan sendiri

`INDEPENDENT_NATIVE_RERUN`; `oracle_origin=WRITER_UNCHANGED`, `fixture_origin=WRITER_UNCHANGED`. [Run regresi](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444). Seluruh **21/21 suite selesai pada percobaan pertama**: **880 eksekusi kasus PASS**, mencakup **684 ID kasus unik**, ditambah sembilan fase rehearsal. Kasus yang sama dalam komposisi berbeda tidak diklaim sebagai kasus unik tambahan. Semua gate pemulihan/advisor yang dideklarasikan lulus. Tidak ada retry pergantian hari pada regresi bisnis ini. Nama suite lama tidak dipakai sebagai hitungan: transport berisi 15 kasus, staged 14, plan 43, attention 286, dan F03 P12 91. [REGRESSION_LABEL_MAP.json](REGRESSION_LABEL_MAP.json) menjelaskan dua label lama dalam manifest awal.

| Suite / job | Kasus PASS | Pemulihan / advisor |
|---|---:|---|
| [analysis153](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009372) | 153 | Lulus / lulus |
| [attention284](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009509) | 286 | Lulus / lulus |
| [cp7-p21-full-rehearsal](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009013) | 9 fase rehearsal; bukan kasus bisnis | Lulus / lulus |
| [f03-full-p12](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152011047) | 91 | Lulus / lulus |
| [f03-full-prefreeze_ui](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152011129) | 31 | Lulus / lulus |
| [k2-retention-10](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009504) | 10 | Lulus / lulus |
| [k3-cleanup-22](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009362) | 22 | Lulus / lulus |
| [k4-runner-17](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009535) | 17 | Lulus / lulus |
| [k6-proof-runner-10](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009337) | 10 | Lulus / lulus |
| [p19-ai-v2-9](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009397) | 9 | Lulus / lulus |
| [p19-plan-v2-22](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009159) | 22 | Lulus / lulus |
| [p19-reminder-v2-16](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009145) | 16 | Lulus / lulus |
| [p19-report-v2-20](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009354) | 20 | Lulus / lulus |
| [p19-scale5](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009270) | 5 | Lulus / lulus |
| [p19-staged12](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009251) | 14 | Lulus / lulus |
| [p19-transport11](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009318) | 15 | Lulus / lulus |
| [payroll--payroll-review](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152011148) | 43 | Lulus / lulus |
| [pl5-history-yield-20](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152009142) | 20 | Lulus / lulus |
| [plan39](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152010989) | 43 | Lulus / lulus |
| [receipt_correction](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152011097) | 43 | Lulus / lulus |
| [supplier_payment_create](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818444/job/115152011069) | 10 | Lulus / lulus |

[REGRESSION_RESULTS.json](REGRESSION_RESULTS.json) menyimpan hitungan per kasus, ID unik vs jumlah eksekusi, smoke, diagnosis runtime lama yang mendapat nol kredit, dan sembilan fase rehearsal P21 secara terpisah. Rehearsal tidak dianggap sembilan kasus bisnis. Pada P21 yang sengaja melakukan USE committed, raw batas data sesudah USE tidak sama dengan sebelum USE; pembuktian restore penuh berasal dari salinan hasil backup sebelum instalasi. Ini bukan klaim uninstall dapat mempertahankan tulisan bisnis sesudah instalasi, dan bukan bukti pemasangan hosted.

F03 prefreeze UI mempunyai **31/31 kasus browser PASS** pada komposisi CP7 yang dideklarasikan. Dua pengamatan tambahan pada runtime CP6 lama tetap **INCOMPLETE**, karena `erp_cp7_get_recost_queue_v1` tidak ada pada runtime itu (404/PGRST202). Keduanya sudah dideklarasikan sebagai diagnosis dengan nol kredit kasus produk dan Original merahnya tetap disimpan. Ini tidak diubah menjadi PASS atau temuan baru untuk komposisi CP7. Tiga kontrol source admission pada attention juga disimpan terpisah dengan nol kredit keluarga.

**Skala aplikasi penuh, bukan benchmark kernel.** P19 5/5 kasus lulus; setiap kasus browser mencakup tiga panjang riwayat (1, 30, 100 hari) dan empat jalur. Pada data sintetis ini, jalur bertahap menampilkan hasil untuk semua ukuran berikut:

| Target | Klik → hasil tampil, riwayat 1–100 hari |
|---:|---:|
| 100 | 2,28–2,59 detik |
| 300 | 5,46–6,76 detik |
| 1.000 | 15,79–20,90 detik |
| 5.000 | 86,42–111,49 detik |

Pada 5.000 target, respons awal layar muncul 5,6–12,6 ms; progres tahap pertama 3,16–3,76 detik. Jalur capture/background biasa tetap menolak 5.000 pada batas 1.000 produk sumber; penolakan jujur itu tidak dihitung sebagai hasil analisis berhasil. Dalam pengukuran SQL bertahap 5.000 target, 26 halaman menampung seluruh target; cleanup mempertahankan hash/ukuran halaman. Jumlah ukuran kolom yang diukur memakai `pg_column_size` turun dari **126.165.990–128.981.941 byte** menjadi **31.161.786–31.161.849 byte**. Ini ukuran payload kolom setelah kompresi yang dipakai alat ukur, bukan seluruh konsumsi disk database, indeks, WAL, atau bukti kapasitas pabrik nyata. Rincian dan asal setiap pengukuran ada di [SCALE_BROWSER_SUMMARY.json](SCALE_BROWSER_SUMMARY.json) serta Original lengkap. Hasil ini tidak memberi penerimaan PR44 atau penerimaan target latensi oleh owner.

[Shell](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38353818482): **1.726 tes di 202 berkas, enam browser, build, dan dua analisis CodeQL lulus**; SARIF keduanya berisi nol hasil dan invocation sukses. Kontrol helper writer juga berjalan, tetapi penutupan ASF-F01 memakai kontrol mandiri di atas.

Supplier Payment Create **10/10 PASS pada percobaan pertama**, gate pemulihan dan advisor lulus. Instrumentasi read-only menyimpan 26 snapshot batas/public state tanpa mengubah return object, urutan pembanding, atau verdict. Sepuluh perbandingan awal–akhir (dua tingkat kelompok dan dua untuk masing-masing empat kasus native) sama persis; array public tidak disortir ulang. Bidang Auth pada salinan observasi disimpan sebagai jumlah dan hash, sementara comparator asli tetap menerima objek aslinya. [SUPPLIER_BOUNDARY_REVIEW.json](SUPPLIER_BOUNDARY_REVIEW.json) merinci pembanding. Kegagalan historis writer tetap disimpan; penyebabnya **belum diketahui** dan tidak dianggap dijelaskan oleh run hijau ini. Tidak ada perbaikan produk yang diminta tanpa bukti cacat saat ini.

## Area yang tidak diberi PASS baru

- Cakupan audit ini adalah retest temuan dan delta dari audit pertama, bukan audit penuh baru CP1–CP7. Area di luar delta yang tidak diulang berstatus **BELUM DIULANG pada 7a0b4a90**; bukti lama tetap terikat d0b9e9c2.
- Penerimaan PR44 dikecualikan karena konflik kepentingan penulis. Tes consumer tidak menggantikan penerimaan auditor lain.
- Pemasangan nyata, konfigurasi operasional pending, kesetaraan hosted terbaru, pengiriman WA nyata, backup malam produksi, dan perangkat mobile fisik tidak dibuktikan oleh cluster sementara ini.
- Hasil saat ini tidak memberi izin deploy, memasang cron/backup, membuka kembali keputusan D11/GBD-03, atau menutup tahapan owner berikutnya.

## Bukti dan kegagalan pertama

Manifest kasus dan workflow disimpan sebelum masing-masing eksekusi. Tidak ada manual rerun kasus untuk memperoleh hijau. Pengulangan positif yang sengaja diminta kontrol ASF tetap menyimpan percobaan pertama. Dua workflow merah mandiri tetap dipertahankan: satu `AUDITOR_TOOL` yang dibetulkan klasifikasinya dari Original, satu counterexample backup produk. [FINAL_ORIGINALS.tar.xz](FINAL_ORIGINALS.tar.xz) menyimpan seluruh Original JSON per job tanpa pemotongan, dua log gagal pertama, log diagnosis CP6 lama, SARIF, screenshot mandiri, dan indeks unduhan. [ORIGINALS_MANIFEST.json](ORIGINALS_MANIFEST.json) memberi ukuran/hash tiap berkas dan menjelaskan arsip raw besar yang tetap tersedia di CI. [LOCK.json](LOCK.json) mengikat laporan, handoff, receipt dan arsip final. Semua anggota arsip sudah diekstrak dalam memori dan hash-nya dicocokkan kembali.

Keputusan retest: **HOLD**, `production_go:false`. ASF-F01 ditutup; residual ASR-OPS-01 serta batas penerimaan PR44 tidak ditutupi hasil regresi hijau.

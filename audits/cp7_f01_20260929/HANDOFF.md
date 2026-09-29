# Audit independen keluarga 1 CP7 — P00–P02

**Putusan: ACCEPT untuk fondasi dengan cakupan di bawah. Tidak ada blocker produk baru yang terbukti. `production_go=false`.** CP6 tetap CLOSED sesuai penerimaan sebelumnya. Tidak ada permintaan perbaikan kode produk untuk writer dari audit ini.

Kandidat produk: `735056db3b42cc7fc3999149b42e2cadac7b42b2`; checkpoint dokumen: `88543e40320330e0cd95eae0bd54267f5f22d834`. Bundle SQL SHA-256: `bfe90effa5af89941a02669b05ed855f54cb2c76ae8433e7cd01ae3b5f5bc9c4`.

Oracle ditulis sebelum pemeriksaan implementasi. Handoff dan bukti writer dibaca untuk menentukan cakupan dan cross-check; audit ini **tidak mengaku blind**. Fixture dan installer terisolasi digunakan kembali; probe tambahan ditulis auditor. Kode produk, branch writer, hosted/UAT/produksi tidak diubah. P03–P04 yang sedang bergerak tidak dimasukkan ke penerimaan checkpoint ini.

## 1. Tes tambahan auditor dan temuannya

**15 kasus akhir PASS: 10 database, 3 concurrency, 2 real Auth/HTTP.** Dua metode pemeriksaan diperbaiki di alat auditor; riwayatnya dijelaskan di bagian 4. Hasil per kasus berada dalam [VERDICT.json](VERDICT.json).

| Yang diperiksa | Hasil nyata |
|---|---|
| Hak finansial dicabut dari pemilik arsip | Nilai, count, hash dan status tidak membocorkan perubahan biaya; isi arsip tetap |
| Operasional benar-benar tidak membaca biaya | Counter pemanggilan helper biaya dan pembacaan `fg_lots`/`hpp_versions` tetap **0**. Kontrol finansial membaca data dan memanggil helper, sehingga alat ukurnya terbukti aktif |
| Nol dan desimal | `0.000000`, `21474836.480001`, `999999999.123456` dipertahankan tepat sebagai string KNOWN; berbeda dari UNKNOWN. Ini fixture sumber HPP, bukan sertifikasi kebijakan BD FREE |
| Halaman dan input | Domain kosong sah; tepat 100 baris terbaca unik dengan total 299 PCS; 13 variasi cursor/domain/limit salah ditolak; cursor akhir memberi halaman kosong |
| Batas sumber | 501 gerakan stok atau 501 biaya lot menolak capture finansial tanpa run parsial; 501 biaya lot tidak memengaruhi capture operasional |
| Sumber hilang setelah capture | Arsip tetap dapat dibaca dengan `SOURCE_UNAVAILABLE`; capture baru ditolak |
| Seluruh hak efektif principal | Tidak ada grant menulis/trigger pada tabel bisnis; hanya enam fungsi biasa yang diizinkan. Delapan fungsi trigger lama tidak dapat dipanggil langsung. Tidak ada grant helper privat untuk anon/authenticated/service_role |
| Pencabutan akses | Keempat izin minimum masing-masing menolak baca dan replay. Aktor kosong/inaktif ditolak. Hak finansial atau izin stok yang dicabut saat menunggu request lock juga menolak; tidak menambah run |
| Transaksi dan REST | REPEATABLE READ/SERIALIZABLE ditolak untuk akses segar. Delapan percobaan REST privat ditolak. Token Auth yang sama langsung tunduk pada empat pencabutan izin dan dapat replay run yang sama setelah izin dipulihkan |

P00 juga diambil ulang secara read-only setelah pemulihan: **1.009 definisi fungsi cocok**, 409 relasi dan 531 trigger tercatat; percobaan write ditolak `25006`. Semua 48 hash framework, enam salinan kontrak, tujuh pin source/test/workflow keluarga 1 dan hash bundle cocok. SQL operasional CP6 tidak berubah dari accepted base `10a8347`.

## 2. Tes writer yang dijalankan ulang oleh auditor

**16/16 PASS: 10 database, 4 concurrency, 2 real Auth/HTTP.** Ini eksekusi auditor atas kasus writer, dipisahkan dari 15 probe baru.

- Fakta cutting 6+7, FG9, draft sale2, cost UNKNOWN; tidak mengubah batas bisnis.
- Replay stabil, root konflik ditolak, arsip immutable, cursor terikat, grant/revoke dan lintas aktor ditolak sesuai kontrak.
- Insert/backdate/delete/status/recost menandai perubahan yang relevan; perubahan biaya tidak menjadi sinyal untuk operasional.
- Halaman 1/101/500 lengkap; 501 menolak hasil parsial.
- Dua belas capture saat 30 update atomik hanya melihat pasangan utuh `(9,2)` atau `(12,5)`.
- Request bersamaan menghasilkan satu run. Akses dicabut saat menunggu ditolak. Perbaikan cutoff setelah antrean melihat `[2,3]` sesuai oracle.

Suite aplikasi lama juga dijalankan ulang: **633 unit/DOM, 6 browser cangkang, security dan build PASS**. Keenam browser bukan UI jual–retur R10 yang terhubung.

## 3. Cross-check bukti writer

[Run native writer 36505788525](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36505788525) cocok dengan receipt 10+4+2 PASS dan hash sumber. [Run aplikasi writer 36505793360](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36505793360) memuat 633 tes, 6 browser, build/security PASS dan CodeQL kedua bahasa selesai tanpa finding. CodeQL dibaca dari bukti writer, tidak dihitung sebagai eksekusi baru auditor.

Bug cutoff pada versi sebelumnya memang tercatat: `[2]` saat oracle `[2,3]`. Pada kandidat beku hasilnya `[2,3]`, dan kasus yang sama lulus lagi di run auditor. Tidak ada alasan membebankan bug yang sudah sembuh itu ke writer.

Receipt terpisah: [WRITER_CROSSCHECK.json](evidence/WRITER_CROSSCHECK.json) dan [PROVENANCE.json](PROVENANCE.json).

## 4. Koreksi alat auditor, bukan tiket bug produk

[Run awal 36512993335](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36512993335), audit commit `69423e50`, menghasilkan **29 PASS, 2 INCOMPLETE**. Run awal tetap merah dan laporan aslinya dipertahankan.

1. Mencabut grant helper biaya membuat query gagal sebelum hasil tersedia, termasuk bagi operasional. Kegagalan ini tidak membuktikan helper membaca biaya. Probe diperbaiki menjadi pengukuran `pg_stat_xact_user_functions` dan statistik baca tabel, dengan kontrol finansial positif. Hasil operasional: semua nol; kontrol finansial: helper 2 panggilan, lot 8 baca, HPP 2 baca. Grant yang hilang tetap diuji sebagai kegagalan sumber yang menolak capture tanpa run parsial.
2. Pemeriksaan ACL awal menganggap delapan grant PUBLIC pada fungsi trigger lama sebagai mutator yang dapat dipanggil. Semua delapan adalah trigger invoker; pemeriksaan berikutnya membuktikan panggilan langsung ditolak, dan principal tidak memiliki hak menulis ataupun memasang trigger pada tabel bisnis.

[Run terarah 36513500787](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36513500787), audit commit `61dd0884`, mengulang **hanya dua pemeriksaan tersebut: 2/2 PASS**, ditambah recapture P00. Kode produk dan bundle hash sama. Sebanyak 29 hasil PASS sebelumnya tetap dipakai. Jadi penerimaan 31 kasus unik berasal dari dua run, bukan klaim satu run 31/31 hijau. Statistik transaksi PostgreSQL yang digunakan didokumentasikan [di sini](https://www.postgresql.org/docs/17/monitoring-stats.html#MONITORING-STATS-VIEWS).

## 5. Pemulihan, bukti, dan batas penerimaan

Kedua run memasang **30/30 berkas paket CP6** dan lulus backup/restore, pemeriksaan primary tidak berubah, pemulihan batas CP6, serta gate advisor. Run awal gagal pada gate probe karena dua INCOMPLETE di atas; gate probe follow-up lulus. Seluruh database race/HTTP dibuang, lima akun Auth uji dibersihkan, count Auth kembali `[0,0,0,0]`, dan tidak ada sesi/lock tersisa.

Advisor mempertahankan 216 temuan baseline dan satu INFO `rls_enabled_no_policy` pada tabel privat `analysis_runs`; tabel tersebut memang tidak diberikan ke role API. Tidak ada klaim seluruh baseline bebas temuan.

Ringkasan yang mempertahankan seluruh hasil per kasus: [INITIAL_RESULTS.json](evidence/INITIAL_RESULTS.json), [TARGETED_RESULTS.json](evidence/TARGETED_RESULTS.json). Laporan asli dan gate paket disimpan sebagai gzip lossless pada direktori `evidence/`; hash raw/gzip dan ZIP tercatat di kedua ringkasan.

Penerimaan terbatas pada satu physical root/exact size, CURRENT, lima domain operasional plus lot cost berizin, maksimal 500 fakta/domain dan 100/halaman. Cutting masih `UNBOUND_CANDIDATE`. Tidak menutup seluruh E09/E14/E15/E20/E22/X09, historical AS_KNOWN/RESTATED, engine WIP/forecast/shared capacity, report/export/apply/ACK, R10/P11, maupun mandor/P12. Semua itu tetap mengikuti paket pemiliknya; bukan temuan rusak pada keluarga 1.

Writer dapat meneruskan keluarga berikutnya menggunakan fondasi yang diterima ini dan mencatat referensi acceptance ini. Saat sumber atau kontrak berubah, uji ulang jalur yang terdampak serta gate keluarga terkait. Audit keluarga 1 ini tidak memberikan izin produksi atau menggantikan integrasi T2/P20/P21.

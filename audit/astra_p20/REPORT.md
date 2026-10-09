# Audit independen P20 CP7 — 9 Oktober 2026

**Putusan: HOLD. `independent_acceptance:false`, `installed_P21_acceptance:false`, `production_go:false`.**

Kandidat aplikasi yang diuji adalah `2e605bb7d9b6b7903919b8df2be1443f1740140b`, tree `51935efb12c035496848e2a85590aa18a3ed3d76`. Audit ini meliputi komposisi beku `9d57b7f5` beserta seluruh kelanjutan sampai kandidat tersebut. Head dokumen yang diperiksa `a7f37aec69abfd24226abb77b8ad2f24973525f4`; `git diff --name-only 2e605bb7 a7f37aec` hanya berisi `docs/`. Setiap job memakai checkout produk terpisah dan memeriksa SHA/tree serta tidak adanya perubahan source.

## Penjelasan singkat untuk Bos

Ada satu blocker pada rencana produksi: dua jalur rencana bersamaan menerima 61 PCS saat kapasitasnya 60. Yang terbentuk masih draft potongan, sehingga tes ini tidak membuktikan stok atau uang rusak. Ada catatan operasional pada nama jadwal lintas database dan benturan receipt backup; kondisi serta tingkat dampaknya dijelaskan terpisah. Alur uang yang dihitung sendiri, kredit supplier, koreksi jual/retur, harga laundry belakangan, payroll, dan tanggal WIB lulus pada kasus yang dijalankan. Seluruh 5.000 target muncul utuh dan tetap bisa dibaca sesudah pembersihan. Isi data tersimpan turun sekitar 95,49 MB pada fixture mandiri. Satu alat uji writer masih gagal meski unit test, build, dan pengujian lanjutan lulus. Tidak ada perubahan aplikasi atau database asli dari audit ini. Handoff menyebut tepat apa yang perlu diperbaiki dan apa yang ternyata hanya kesalahan alat tes auditor. Penerimaan juga harus memisahkan area PR44 yang pernah ditulis Astra agar tidak disahkan sendiri.

## Asal bukti dan independensi

- **Kasus mandiri:** oracle ditulis dari kontrak/keputusan owner pada `CASE_MATRIX.md`, kemudian dieksekusi dengan angka, mutasi, dan urutan transaksi auditor. Angka/fakta bisnis tidak disisipkan sebagai hasil posted. Helper writer digunakan untuk bentuk input, master/draft, transport, instalasi, dan fixture; asalnya dicatat. Model/matcher privat diberi label kernel, bukan bukti posting live.
- **Rerun mandiri atas kasus writer:** checkout kandidat yang sama, suite asli tidak diubah, dipanggil auditor sendiri. Hasil per ID, bukan warna job saja, diperiksa. Ini tambahan cakupan; asal oracle tetap writer dan tidak disamarkan menjadi kasus mandiri.
- **Crosscheck dokumen writer:** hash kandidat, kontrak, CI receipt, dan ukuran K3. Angka dokumen writer tidak dipakai sendirian untuk memberi PASS.
- **Review source:** hanya membuktikan hal statis, termasuk inventaris izin, kepemilikan, perubahan assertion, dan sumber penyebab temuan. Tidak menggantikan pengujian perilaku.
- Tidak membaca laporan atau Actions auditor lain pada putaran yang sama. Astra pernah menulis optimasi timeline PR44: hasil yang menyentuh area itu tidak menjadi penerimaan bebas konflik. Auditor lain harus menutup bagian tersebut.

Panduan `AUDIT_PANDUAN_PRO_MAX.md` pada kandidat, README/prompt paket, kontrak framework, snapshot/staged v2, keputusan owner 8–9 Oktober, dan addendum CP6 dibaca sebagai dasar. Keputusan D11/GBD-03 tidak dibuka ulang. Bukti rinci dan indeks setiap eksekusi tersedia pada `EVIDENCE_INDEX.json`, `INDEPENDENT_CASE_RESULTS.md`, `REGRESSION_RESULTS.md`, serta arsip bukti di folder `evidence/`.

## Temuan dari pengujian mandiri

44 ID kasus mandiri menghasilkan 39 PASS mentah, 1 adjudikasi PASS untuk penolakan 5.001 yang benar, dan 4 counterexample dengan batas berbeda seperti tabel. Ini tidak sama dengan mengklaim 50/50 parent selesai.

| ID | Tingkat | Fakta yang terbukti | Batas dampak |
|---|---|---|---|
| F01 | **BLOCKER penerimaan perencanaan** | v1 APPLY59 belum commit; v2 APPLY2 commit lebih dulu; keduanya kemudian tersimpan61 pada kapasitas60. V2 menyebut pemakaian rencana lain0. | Native draft/intent saja. Tidak membuktikan stok fisik/jurnal berubah. |
| F02 | MAJOR operasional bersyarat | Install cron untuk database B memindahkan dua job A pada scheduler/role yang sama. | Kondisi beberapa database pada satu scheduler. Tidak ada hosted schedule yang disentuh. |
| F03 | MINOR utilitas backup | Percobaan gagal dengan nama timestamp detik yang sama menimpa receipt verified lama. | Dump SHA tetap sama; waktu tabrakan disimulasikan. Template nightly diserialkan, sehingga bukan bukti kegagalan jalur nightly tunggal. |
| F04 | MINOR/batas detektor | Dengan immutable trigger sengaja dilemahkan di salinan, empat perubahan indeks/metadata semantik tidak ditangkap sebelum respons CLEANED. | Mutasi biasa ditolak; semua kontrol di-rollback. Bukan bukti pengguna dapat merusak hasil, dan bukan blocker tambahan. |

F01: [run 37879134926](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37879134926). F02/F03: [run 37877803025](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37877803025). F04: [run 37877802981](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37877802981). Witness lengkap, input, source terkait, dan syarat retest ada pada [WRITER_HANDOFF.md](WRITER_HANDOFF.md).

## Temuan dari rerun dan crosscheck

**F05 — gate alat bukti gagal:** `scripts/cp7_probe_evidence_test.py` melempar `NameError: p19_plan_v2 is not defined` saat menjalankan finalizer aktual. File mock belum mengikuti flag finalizer. Ini test resmi `cp7-shell.yml`, bukan bug angka aplikasi. [First failure](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37878853771) dipertahankan; [kelanjutan langkah yang terlewat](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37879768174) menghasilkan **1.722/1.722 unit test, security/build, dan 6/6 browser shell lulus**. JS/TS dan Actions CodeQL juga lulus pada run shell pertama. Keberhasilan kelanjutan tidak mengubah gate pertama menjadi PASS.

Metadata expected pada dua laporan tertinggal: schedule70 vs actual71, P18 full cycle1 vs actual2. Kasus tambahan benar-benar berjalan dan lulus; tidak ada kasus yang disembunyikan oleh selisih ini. Banding source `976f4c43`→`2e605bb7` menemukan **nol assertion Python lama dihapus** dalam berkas yang berubah; browser report memperbaiki penantian/rekaman respons, scale menambah pengukuran cleanup. Tidak ada berkas di `tests/` yang berubah pada delta tersebut. Ini review statis, bukan jaminan bahwa semua desain test cukup.

Log writer yang sudah ada sebelum delta tetap; empat berkas log baru ditambahkan. Receipt writer 15 workflow/43 job tetap berstatus **WRITER_CROSSCHECK**, terpisah dari run yang dijalankan auditor. **Hasil akhir: 33/33 job dengan 1.256 eksekusi kasus PASS** (termasuk 6 kontrol tambahan dan pengulangan kasus pendahulu antarvarian). Dua gladi P21 dihitung sebagai fase, terpisah. Rerun menggunakan [run 37876648313](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37876648313); rincian final per suite, subgroup, case ID, budget dan pemulihan ada pada `REGRESSION_RESULTS.md`.

## Putusan per area wajib

LULUS berarti pemeriksaan yang dijelaskan pada baris itu selesai tanpa counterexample yang belum diselesaikan. Ini bukan klaim bahwa semua kombinasi input telah habis diuji. Asal oracle dan rincian yang belum lengkap pada 50 parent scenario tetap terlihat dalam `COVERAGE_50.md`; tidak ada parent yang ditutup hanya karena review kode.

| Area | Putusan | Bukti dan batas |
|---|---|---|
| Akses dan pemulihan | LULUS pada kasus diuji | Izin dicabut sebelum replay/reader dan saat menunggu kunci; Native ACL serta Auth/REST helper privat ditolak; lost-response/replay ditambah rerun. |
| Keuangan dan laporan | LULUS pada kasus diuji | Oracle73→41→jual13→retur4, exact Decimal, AP61.65 lunas tanpa residu, invoice22juta, biaya pending, laporan bertanggal, dua sisi tengah malam WIB. |
| AP/pembelian/bahan | LULUS pada kasus diuji | Dua invoice17+56 mengubah GRNI903.01 menjadi AP889.83; kredit22.46 tepat ke invoice lain, koreksi paid naik/turun, pembayaran dan koreksi lewat rerun. |
| AR/penjualan | LULUS pada kasus diuji | Draft mengurangi tersedia sekali, retur kembali ke asal; koreksi12jual−4retur menyisakan FG33/AR102.25; perubahan harga baris yang sudah diretur ditolak. |
| Stok/HPP/produksi | LULUS pada kasus diuji | Konservasi137=103WIP+27FG+7BS; tiga GOOD tambahan menghasilkan100WIP+30FG+7BS; snapshot lama tetap; recost tidak menambah PCS. PL8 diperluas melalui rerun. |
| Payroll | LULUS pada kasus diuji | Work46.33+aksesori36.49; ditambah hak lama85+carry7.50−advance30 menghasilkan kas145.32; replay/inverse tepat. Roster, pemeliharaan kode pekerja, attendance dan settlement dicakup rerun. |
| Perencanaan/model | **GAGAL pada integrasi kapasitas F01** | SES8,18,28 α.5→20.5; cutoff/holdout; PL5 own205cut/193FG→Wilson lower91.6%; matcher terikat. Jadwal/netting/model lain rerun; penerimaan area PR44 oleh auditor lain. |
| Analisis5.000 target | LULUS transport/cleanup yang diuji | 5.000 target unik, 26 halaman, SHA256/range/count, reconnect UUID, unit≤8s, page≤8MB;5.001 ditolak. Scale browser100/300/1000/5000 rerun. PR44 tidak disahkan sendiri. |
| Snapshot berlabel waktu v2 | LULUS pada kasus diuji | Data lama tidak ditulis ulang setelah stock/policy/membership berubah; ARCHIVED_STALE dan label waktu; tambahan perubahan sumber/races melalui rerun. |
| Rencana v2 | **GAGAL F01** | Recheck stok/policy/izin setelah lock lulus; gabungan v1/v2 kapasitas bersama gagal. |
| Business Report v2 | LULUS pada kasus diuji | Snapshot lama + finansial aktual bertanggal diuji dengan nominal sendiri; laporan historis bertahan setelah sumber kedaluwarsa; sealing/revisi/race via rerun. |
| Pengingat v2 | LULUS pada kasus diuji | Gap selesai setelah claim → finish SUPPRESSED/RESOLVED_NOW, sentfalse; business state tidak ditulis. Hanya sink lokal, tidak mengirim WA. |
| Tanya AI v2 | LULUS pada kasus diuji | Input bebas/ID asing/21 pilihan ditolak; batas25gap+20pilihan; tidak membuka uang/izin dan tidak mengubah fakta. Tidak menyatakan integrasi penyedia AI eksternal siap operasi. |
| Retensi7hari K2 | LULUS pada kasus diuji | Batas±30detik, semua reader/consumer yang diprobe, unfinished lebih tua tetap, dokumen historis selamat; tambahan lifecycle/race melalui rerun. |
| CleanupDONE K3 | LULUS jalur normal; **F04 batas detektor** | Hanya5set kerja dihapus; seluruh retained row/page/hash dibandingkan; busy defer, atomic fault, ulang, consumer sesudah cleanup. Verifier tidak membuktikan semua indeks semantik pada copy yang dilemahkan. |
| Jadwal dan backup CP7C | **GAGAL isolasi F02; catatan F03** | Realcron tick/uninstall lulus; dump/restore556tabel dibandingkan dengan SHA256 sendiri;15restore nyata/14retensi lulus. Tidak dipasang hosted. |
| Integritas uji | **GAGAL gate F05** | Tidak ditemukan pelemahan assertion lama pada delta yang diperiksa; finalizer mock rusak, metadata count perlu sinkron. Semua first failures dipertahankan. |
| UI | LULUS smoke dan akses yang diuji |48rute×desktop/mobile,111izin/243RPC inventory,35rute memanggil RPC nyata pada tiap viewport; tanpa overflow/JSexception. Bukan berarti setiap tombol diuji lewat browser. Prototype diberi label; transaksi browser dicakup suite terkait. |
| P21 gladi | LULUS gladi dalam salinan | Install→preuse rollback→reinstall→committeduse→guard postuse→backup/restore; ops dan cleanup tercakup. Perbedaan katalog pg_cron/formatvarchar dipisahkan. InstalledP21 tetapfalse. |

## Enam syarat owner 9 Oktober

1. **Pelestarian:** PASS pada retained jobs/units/capture marks, plan targets/scope/groups, headers/pages/page sets; field/timestamp ikut hash, tanpa mengabaikan kolom. Hanya `outputs,target_rows,pair_rows,pair_lists,fragments` hilang.
2. **Consumer sesudah cleanup:** PASS pada buka ulang DONE, rencana v2, report v2, reminder v2 dan AI v2; dokumen historis dan hasil final tidak dihitung ulang.
3. **Admission/atomicity:** PASS untuk DONE yang masih ditahan, job aktif, duplikasi cleaners, kegagalan di tengah delete dan rollback. Body/header hash corruption yang dikontrol ditolak. Batas detektor semantik F04 tetap dicatat; jangan menyebutnya detektor segala jenis korupsi.
4. **Uji lama tidak dilonggarkan:** source comparison mendukung ini; gate alat bukti F05 masih harus diperbaiki tanpa menonaktifkan kontrol asli.
5. **Ukuran nyata5.000:** PASS, lihat tabel berikut dan `evidence/SCALE5000_COMPARISON.json`.
6. **Scheduler/backup:** jalur normal diuji nyata, tetapi isolasi database F02 gagal; kondisi benturan receipt F03 dicatat. Pemasangan nyata belum diizinkan.

## Pengukuran5.000 mandiri dan crosscheck writer

| Pengukuran | Sebelum | Sesudah |
|---|---:|---:|
| Payload tersimpan, `pg_column_size` |126.608.050byte|31.120.366byte|
| Semua kolom yang dihitung, termasuk metadata |132.757.814byte|31.616.714byte|
| Target rekomendasi |5.000|5.000|
| Halaman hasil |26|26|

Payload yang dihemat95.487.684byte. Terbesar7.969.392byte/halaman; seluruh halaman206.448.568byte UTF8 sebelum kompresi, sehingga bukan satu respons raksasa. Header/halaman dan setiap retained row identik sebelum/sesudah. Pada fixture ini131panggilan request/step/status berjumlah64,79detik waktu panggilan dengan maksimum2,697detik; ini **bukan** waktu UI dari klik sampai seluruh halaman terunduh, bukan target3detik seluruh analisis, dan bukan pengukuran jaringan hosted. Statement timeout tetap8detik.

Writer melaporkan payload5.000 target126,12–128,90MB menjadi31,14MB untuk histori1/30/100hari. Fixture mandiri memakai histori10hari dan identitas baru: besaran sejalan, tetapi byte antarfixture tidak diklaim harus sama. Di dalam fixture mandiri sendiri identitas dan isi harus tepat sama sebelum/sesudah. `pg_total_relation_size` dicatat terpisah dan tidak langsung turun karena DELETE; tidak mengklaim ruang disk fisik langsung kembali ke OS.

## Pemulihan, batas dan keputusan akhir

Backup mandiri membandingkan556tabel dengan SHA256 atas seluruh row yang dikodekan secara kanonik, lalu membaca ulang hasil staged dari restore. Gladi penuh memeriksa150tabel CP7 dan1.886fungsi;9fase terekam. Preuse rollback kembali ke keadaan awal; rollback setelah pemakaian committed ditolak. Restore backup sebelum pemasangan menghilangkan transaksi setelah titik backup sesuai sifatnya, tidak disebut pemulihan tanpa kehilangan transaksi. pg_cron yang hanya berada di database postgres tidak diam-diam dinyatakan ikut terpasang di database restore; pemasangan ulang scheduler adalah langkah operasional terpisah.

Tidak ada klaim perubahan uang/stok dari F01, penghapusan dump dari F03, atau akses korupsi biasa dari F04. K4, tujuan backup eksternal, pengiriman WA nyata, delapan konfigurasi operasional, serta penerimaan PR44 yang bebas konflik tetap dibedakan dari bug. Rincian subkasus yang belum dibuktikan penuh tersurat dalam `COVERAGE_50.md`; tidak disembunyikan oleh total test hijau.

**Syarat sebelum izin pemasangan:** kandidat revisi yang menutup F01 dan memenuhi isolasi operasional yang akan dipakai; gate F05 sehat; retest auditor pada SHA/tree revisi; penerimaan bebas konflik untuk PR44; kelengkapan release P21 dan konfigurasi tujuan backup yang benar-benar persisten; lalu izin pemasangan owner. Audit ini tidak memasang cron, backup, aplikasi, atau koneksi WA ke sistem asli. Tindak lanjut writer digabung dalam satu [handoff](WRITER_HANDOFF.md), sementara asal temuan tetap dipisahkan.

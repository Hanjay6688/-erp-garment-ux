# Audit Astra CP1–CP7 — putaran penuh 1 — 14 Oktober 2026

**Vonis kandidat: TAHAN PENERIMAAN PENUH.** Ada **satu temuan produk S0 yang terbukti**, ASTRA-CP17-FIN-01, dengan tiga saksi runtime: pembayaran payroll biasa dapat mendahului akrual dan mengurangi kewajiban pada laporan tanggal yang lebih awal. CP2 juga **belum dapat diverifikasi sebagai pemulihan database historis**. Laporan putaran ini dikunci; status tersebut bukan izin produksi.

Panduan: `docs/AUDIT_PANDUAN_PRO_MAX.md`553 baris, SHA256 `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`.

Kandidat: `0b7049d9203bac52b47a4c89f3e0d75646067a8f`; tree: `ce6aed0a0af920e8aa80248f3cabcd293688df18`. Paket handoff penulis: `00b0eb24b2f014d102f0082111d13ee3be429cf2`, perubahan dokumentasi sesudah kandidat. Cabang auditor: `audit/astra-cp1-7-0b7049d9-20261014`. Sumber produk, migrasi, kontrak, frontend dan konfigurasi produk tidak diubah. Bukti merujuk candidate yang dipasang, bukan HEAD dokumentasi auditor.

## 1. Ringkasan untuk owner

Audit putaran ini telah selesai menilai bukti yang tersedia untuk tujuh tahap, termasuk CP1 dan CP2. Satu masalah payroll terbukti: bayar biasa atau cicilan dapat diberi tanggal sebelum biaya/utang diakui, sehingga saldo utang pada tanggal itu menjadi negatif tanpa alarm dari pemeriksaan integritas inti yang diuji. Penulis perlu memperbaiki batas tanggal di sumber pembayaran, kemudian menunjukkan bukti sebelum/sesudah pada ketiga jalurnya. Dugaan Fable tentang absensi dibayar lewat nota kedua dan biaya yang sama masuk kolam HPP kedua tidak terbukti pada kasus Astra yang dijelaskan di laporan. CP2 memiliki receipt pembukaan arsip149 anggota, tetapi itu belum membuktikan restore database lama. Uji sambungan saldo awal sampai koreksi setelah penjualan/pembayaran selesai dan cocok dengan perhitungan Astra sendiri. Seluruh1.708 eksekusi dicatat, termasuk hasil lama yang HOLD/INCOMPLETE/COUNTEREXAMPLE; angka hijau tidak dipakai untuk menutupi hasil tersebut. A2 tetap OPEN sesuai penerimaan owner sebelumnya, sementara A6 dan perbaikan backup yang sudah diterima tidak dibuka kembali. CP7C/Drive tetap ditahan, dan `production_go:false`.

## 2. Vonis tujuh tahap

| Tahap | Hasil dalam putaran ini | Batas yang tetap berlaku |
|---|---|---|
| CP1 — baseline awal | **TERVERIFIKASI DENGAN BATAS HISTORIS**: G-01 dijalankan sendiri;15 kategori katalog non-ledger cocok;19 SQL lokal diverifikasi terhadap pemetaan historis |70 entri ledger memiliki selisih bootstrap yang sudah dijelaskan;51 perintah historis tidak tersedia sebagai SQL terpisah; tidak memeriksa hosted saat ini |
| CP2 — backup terenkripsi lama | **RECEIPT ARSIP DIREVIEW; RESTORE DATABASE TIDAK DAPAT DIVERIFIKASI DARI SESI INI** |Bukan PASS; tidak ada ciphertext/kunci/restore database yang diperiksa auditor. Receipt writer149 anggota dibedakan dari bukti restore |
| CP3/3.5 — absensi, payroll, HPP | **TIDAK LULUS**, FIN-01 |Kontrol sah PASS; dua dugaan duplikasi tidak terkonfirmasi pada jalur yang diuji; ini tidak membebaskan seluruh kemungkinan kasus |
| CP4/4.5 — produksi, ledger, laundry/QC, sambungan nilai | **REGRESI YANG DIJALANKAN MEMENUHI ORACLE YANG BERLAKU** |Baseline lama dan disposisi tanggal tetap utuh; tidak menyatakan setiap klausul requirement diaudit satu per satu |
| CP5 — ownership dan permukaan pengguna | **BUKTI YANG DIPERIKSA MEMENUHI BATASNYA** |Guard predecessor89 owner efektif/66 file CP5; frontend current291 file/243 pasangan pemanggil-RPC; current browser evidence terpisah dari klaim predecessor |
| CP6 — temporal, saldo awal, close/report, correction | **REGRESI DAN C0 MEMENUHI ORACLE YANG BERLAKU; BATAS LAMA DICATAT** |326+AS34, AR146+28 serta pengganti1, AT16/AU15 dan10 race, AO12/pelengkap5/C025; FIN-01 tetap melintasi jalur laporan akhir; outer restoration dua fase lama terpengaruh fixture auditor |
| CP7 — komposisi final, engine, transaksi, laporan, operasi | **TIDAK LULUS PENERIMAAN PENUH**, FIN-01 |31 suite/1.041 kasus PASS dan P21 rehearsal tidak menghapus cacat payroll; staged-validator boundary dan A2 tetap tercatat |

`feature_complete:false`, `audit_complete:false`, `production_go:false` menyatakan **sertifikasi kelengkapan belum diberikan**, bukan bahwa seluruh implementasi tidak ada. Scope penilaian mencakup CP1–CP7, tetapi receipt CP2, batas inspeksi dan temuan blocker mencegah label100% lengkap. [FEATURE_INVENTORY.json](FEATURE_INVENTORY.json) menginventarisasi271 requirement/22 paket serta permukaan runtime; tautan bukti paket tidak otomatis menjadi PASS setiap requirement.

## 3. Temuan baru — ASTRA-CP17-FIN-01

**S0 · TERBUKTI · NATIVE_QUALIFIED.** Invariant terkait: pembayaran payroll settlement-only; akrual harus tersedia pada tanggal pelunasan; laporan bertanggal harus menjaga kewajiban sesuai tanggal. Satu akar masalah, tiga saksi; bukan tiga temuan terpisah. Detail sumber, langkah, angka dan saran penerimaan ada di [FINDING_FIN01_PAYROLL_DATE.md](FINDING_FIN01_PAYROLL_DATE.md).

| Saksi | Expected | Actual | Bukti |
|---|---|---|---|
| PAY-04-EARLY-FULL |Pembayaran biasa tidak melunasi absensi sebelum akrual tersedia |PAY6100 bertanggal13Okt diterima, termasuk absensi100 yang baru diakui14Okt |run38525930407/job115726145641 |
| PAY-05-EARLY-INSTALLMENT |Cicilan final mengikuti ketersediaan utang bertanggal |1000 dibayar12Okt untuk akrual13Okt |run38525930407/job115726145641 |
| PAY-06-DATED-PARTIAL |Cicilan375,25 tidak membuat utang biasa negatif sebelum akrual |Public RPC menerima PARTIAL; utang kontraktor12Okt menjadi−375,25; laporan mengurangi kewajiban375,25; akrual tetap13Okt |run38527771239/job115732095969 |

PAY-01-CONTROL membuktikan pembayaran sah pada hari yang sama berhasil, dengan satu akrual dan satu pelunasan. PAY-06 menunjukkan `erp.run_integrity_checks()` memiliki nol issue nonzero sebelum/sesudah; laporan tetap seimbang secara debit/kredit meskipun makna tanggal kewajibannya salah. **Batas observasi severity:** seluruh detector finansial/advisor lain dan semua banner UI pada saksi ini tidak diukur. S0 dinilai dari kesalahan finansial melalui command biasa, efek laporan cutoff, dan ketiadaan alarm integritas inti yang diuji; jangan memperluas ini menjadi klaim bahwa setiap detector pasti diam.

Sumber penyebab: `scripts/cp7-src/payroll/settlement-write.sql` PAY meneruskan tanggal; `scripts/cp7-src/payroll/installments.sql` PAY memeriksa not-future tanpa ketersediaan akrual; `scripts/cp7_installment_bundle.py` mewarisi native payment; migration `20260901023200_erp_v2_6_14c_attendance_hpp_uat_alignment.sql` memisahkan akrual period-end dan pembayaran tanpa pemeriksaan tanggal sumber yang cukup. Effective body dalam FULL composition diverifikasi pada runtime; file historis bukan satu-satunya bukti.

**Perbaikan yang diminta:** forward correction pada pemilik native payment untuk full/partial/final, jaga permission, lock, versi dan idempotency; kasbon harus lewat sumber advance yang eksplisit. Tambahkan pemeriksaan utang bertanggal serta kontrol same-day/later, reverse/replay, period closed, dan penolakan atomik tanpa sisa row/context. Tidak mengubah migrasi historis atau merapikan saldo lewat penyesuaian diam-diam.

## 4. Perhitungan independen dan sambungan antartahap

Kasus baru **CP17-ASTRA-SKN22-OPENING-TO-CORRECTION** PASS pada run38527771239. Dibuat setelah membaca kontrak, dengan angka Astra sendiri: saldo bank awal10.000; bahan73×12,37; potong41; jahit17+24; upah1,13 dan aksesori0,89/pcs; laundry2,07/pcs; FG41 dengan HPP16,46. Jual13×29,91, terima137,03, retur4 bernilai119,64 mengurangi AR. Setelah pembayaran bahan/laundry/payroll, koreksi harga penerimaan awal menjadi13,37; replay pembayaran terdahulu harus identik dan selisih73 dibayar terpisah.

Expected dan actual akhir cocok: **bank8.993,33; bahan32 senilai427,84; FG32 senilai558,72; AR132,16; penjualan269,19; COGS157,14; laba kotor112,05**. Akun kontrol, jurnal seimbang dan delta laporan bertanggal cocok. Snapshot baru dibuat atas kisah yang sama tanpa reset fixture (`setup=False`), semua halamannya dibaca/hash; reminder memakai kewajiban live dengan sumber sale yang benar dan sisa132,16, `sent:false`. Integritas inti nol sebelum/sesudah. Ini bukti E2E alur yang disebutkan, bukan klaim semua kombinasi bisnis telah dijelajahi.

## 5. Ledger eksekusi dan seluruh non-PASS

[CASE_LEDGER_FINAL.json](CASE_LEDGER_FINAL.json) berisi **1.708 eksekusi /1.545 nama case unik**. Nama sama di grup/factory berbeda tetap dihitung sebagai eksekusi terpisah.76 hasil awal dibawa byte-identik ke kelanjutan, tidak dieksekusi lagi dan tidak dihitung dua kali. CP1, static guards, langkah P21, dan carry putaran sebelumnya tidak ditambahkan sebagai kasus bisnis baru.

| Status mentah | Jumlah | Disposisi |
|---|---:|---|
| PASS |1639 |Tetap PASS sesuai oracle dan asal bukti masing-masing |
| CONTROL_PASS |39 |Kontrol sukses kontrak lama; tidak diganti label PASS |
| DATE_POLICY_REVIEW_REQUIRED |12 |HOLD historis tetap; pembanding tanggal yang disetujui owner MATCH |
| COUNTEREXAMPLE |12 |3 saksi FIN-01;8 kasus AS bertanggal dengan pembanding yang disetujui MATCH;1 batas validator staged yang sudah diterima |
| INCOMPLETE |6 |AS adjustment1/AO4 memiliki pelengkap yang disetujui PASS;AR zero-accessory1 memiliki pengganti yang menolak sesuai ERP-DEC02 |

Semua69 baris non-PASS mempunyai ID, Original, run dan disposisi individual di [NONPASS_DISPOSITIONS.json](NONPASS_DISPOSITIONS.json). **Tidak ada status merah mentah yang diubah menjadi hijau.** C0 merupakan25 kasus oracle bernama baru yang sebelumnya belum dieksekusi;25/25 PASS pada run38529725289, dengan batas database/public dan advisor gate kembali bersih. Sumber C0 tetap SHA256 `7c2c19b6e722d325ba902cfd9eb1ae2f98d4e2ec27245070ab485df0af9e66a7` dan keputusan D01.1–5 yang sudah diratifikasi.

Asal oracle:1.041 eksekusi memakai oracle writer,41 memakai kontrak Astra terdahulu,5 probe baru setelah petunjuk Fable,3 integrasi/lead baru Astra,593 oracle warisan,25 oracle C0 auditor. Menjalankan oracle penulis secara independen **tidak** mengubah asal oracle menjadi milik Astra. Manifest mencatat expected dan case IDs sebelum execution.

[RUN_RECEIPTS.json](RUN_RECEIPTS.json) mencatat10 workflow run/44 job, semua attempt1; satu run gagal evaluasi tanpa job. Beberapa run merah karena cacat alat, disposisi historis atau temuan produk; lulusnya individual case tidak menghapus gate luar yang gagal. Lihat [HARNESS_QUALIFICATIONS.md](HARNESS_QUALIFICATIONS.md): konfigurasi own/C0 sebelum case, logger setelah76 hasil tersimpan, verifier BA lama sebelum AR races/C0, fixture temporal/AR yang memang commit, dan label progress AR yang tertinggal. Kelanjutan hanya mengerjakan kasus yang belum pernah berjalan. Ada kegagalan alat auditor yang nyata; status dan bukti pertamanya disimpan.

## 6. Matriks invariant dan provenance

[INVARIANT_MATRIX.md](INVARIANT_MATRIX.md) memetakan aturan pokok ke sumber/kasus, hasil dan batas. [FEATURE_INVENTORY.json](FEATURE_INVENTORY.json) mencatat291 file runtime dengan hash,243 pasangan caller-RPC (**220 nama RPC unik**), deklarasi public SQL dan penyebutan relation. Klasifikasi reader/command berdasarkan nama hanya bantuan inventaris, bukan verifikasi mutabilitas. Katalog runtime P00 dan fingerprint dalam Originals tetap sumber authoritative untuk definisi/owner/ACL/member.

Environment: disposable localhost di GitHub Actions; Ubuntu24.04, Supabase CLI2.116, PostgreSQL17.6.1.165, Python3.12.15/psycopg3.2.10, Node22/Playwright1.62.1 sesuai receipt. Native harness memakai candidate0b7049d9, fixture writerca7f0955 dan harnessc6b0e4fb, CP6 driver25fa4736/base1bdca376; exact source/fixture/oracle hashes ada pada manifest dan execution receipts dalam ZIP. Candidate FULL composition, grants yang dideklarasikan, public catalog, function body/owner/ACL dan session/lock boundary dicatat; physical-order classifier tidak membuang anggota/duplikat/definisi/owner/hak akses. Batas committed-fixture temporal/AR dijelaskan eksplisit pada Q02, bukan diloloskan diam-diam.

Browser native memakai kasus penulis yang dijalankan ulang oleh Astra di CI;134 eksekusi berada dalam grup yang secara eksplisit bernama browser. Bukti itu dibedakan dari oracle baru Astra dan dari jsdom. P11 desktop/HP helper lusin beserta save/server reread/overflow sudah diuji pada **candidate sama** di putaran silang2, dan bukti lamanya dibawa dengan identitas, tidak dihitung sebagai browser baru dalam1.708.

P21 rehearsal run38522545215 membuktikan pre-use rollback exact, reinstall identik, penggunaan committed, penolakan rollback sesudah penggunaan, used-backup restore dengan559 tabel data cocok dan staged reread identik, serta pemulihan backup preinstall. Restore used-backup mencatat exit1/19 error **khusus pg_cron** yang dijelaskan; normalisasi katalog terbatas pada VARCHAR reparse, pg_cron database placement dan ACL default yang dijelaskan. Ini hasil **same meaning**, bukan raw pg_restore zero-error atau byte-identical semua katalog. Preinstall restore memang membuang writes sesudah backup, dan38 cluster roles masih ada; fixture dibuang oleh harness. P21 modern tidak membuktikan CP2 lama.

## 7. Paparan Fable dan temuan yang dibawa

Owner mengizinkan pembacaan Fable pada14Okt06:50:45UTC/13:50:45WIB. [FABLE_EXPOSURE_REGISTER.md](FABLE_EXPOSURE_REGISTER.md) mencatat kutipan izin, materi, waktu dan batas independensi. Sebelum paparan, native/baseline manifest dan oracle Astra lama sudah dikunci. Sesudah paparan, petunjuk payroll/HPP diberi kredit asal Fable; penemuan blind tidak diklaim.

| Materi Fable | Hasil Astra |
|---|---|
| Bayar sebelum akrual |TERBUKTI, FIN-01; angka/runtime/oracle Astra sendiri |
| Absensi sudah APPROVED/PAID dipakai Nota kedua |PAY-02/PAY-03 PASS refusal: `Payroll period overlaps another active payroll for this contractor`; dugaan tidak terbukti pada kedua jalur |
| Sumber absensi sama dialokasikan dua kali lewat kolam overlap |HPP-01 PASS refusal: `No eligible normal-Mandor attendance payroll cost exists for this exact period`; distinct legitimate payroll costs tidak disamakan dengan duplikasi |
| CP1/CP2 |CP1 dijalankan sendiri; CP2 receipt archival ditemukan, restore historis belum terverifikasi |
| Klaim53 run,12 dugaan, lima review belum selesai |Hanya tiga dugaan disebutkan. Cabang Fable terakhir diperiksa tetap31cf30090b712897714f35c5a507cd1cd48c5d04, hanya MANIFEST/REGISTER_RUNS di direktori CP17. Sembilan dugaan lain dan53 run tidak dihitung sebagai hasil terverifikasi Astra |

Carry putaran silang2: laporan Astra `57ac8aab164f7c3fc25cf8e2500a8346477da618` dan `fb24bd924fd7e790fba4cecbcd0c43651fab63e6`, candidate sama0b7049d9.141 eksekusi CI/139 nama unik +1 DOM dibawa terpisah. A6 COMPLETE; F-OPS-05/ASR-OPS ditutup; **A2 OPEN diterima sebagai non-blocker oleh D13-10**, dua log gagal asli tetap perlu tersedia dan penyebab belum diketahui. D13-11 pembanding tambahan tidak mengubah pembanding asli. Tidak meminta keputusan ulang untuk hal-hal yang sudah diputuskan owner.

**Konflik peran:** Astra pernah menulis optimisasi PR44/netting/timeline. Eksekusi netting saat ini tidak dipakai sebagai independent acceptance atas optimisasi sendiri; penerimaan peer Fable putaran sebelumnya tetap disebut sebagai asalnya. Laporan Fable putaran2v1.2 pada319e6624 telah dibaca sebagai bukti terdahulu, bukan laporan baru CP1–CP7.

## 8. Bukti yang disimpan dan batas pemeriksaan

[ARCHIVE_INDEX.json](ARCHIVE_INDEX.json) dan [ARCHIVE_PARTS_INDEX.json](ARCHIVE_PARTS_INDEX.json) memuat Original ZIP dan log yang disimpan di Git dengan byte count, SHA256 dan Git blob. ZIP besar dipecah tanpa mengubah byte; [verify_archives.py](verify_archives.py) merangkai dalam memori, memeriksa SHA256/ukuran/CRC. Semua canonical per-case JSON pada ledger, termasuk hasil pertama yang merah, dipertahankan; tidak hanya ringkasan console. Replikasi build ledger membutuhkan ekstraksi Originals pada jalur evidence yang tercatat; indeks ZIP menjelaskan asalnya. [PRODUCT_PARITY.json](PRODUCT_PARITY.json) mengikat tree produk yang tidak berubah.

Yang **belum/tidak dapat dinyatakan selesai**: restore database CP2; replay51 perintah historis CP1; inspeksi semantik setiap baris seluruh function body; sertifikasi individu semua271 klausul; seluruh kombinasi tanggal/concurrency/users; seluruh detector finansial/UI untuk PAY06; kondisi hosted saat ini; pengiriman WhatsApp/transport eksternal nyata; CP7C/Drive. Inventaris tekstual dan green CI tidak menggantikan hal-hal itu. Beberapa dokumen historis panjang dibaca pada bagian yang relevan; tidak diklaim semuanya dibaca utuh. Bukti browser penuh berada di artifact runtime; JSON lengkap serta dua PNG payroll settlement desktop/HP dari artifact11875499613 dipertahankan; SCREENSHOT_SELECTION.json membedakan ZIP pilihan baru dari Original sumber, bukan klaim semua screenshot/raw bundle telah diarsipkan permanen.

Dua project hosted dan database lama tidak dihubungi; tidak meminta kunci. Tidak mengirim pesan kepada penulis/Fable. Existing repository integration otomatis menjalankan **Cloudflare Workers Builds** pada push audit dan menerbitkan branch-preview version/alias. Astra tidak memanggil deployment, mengunjungi preview atau mengubah konfigurasi; check tersebut bukan bukti production cutover. CP7C/Drive tetap HOLD dan tidak ada izin go-live baru.

## 9. Tindak lanjut dan pertanyaan owner

1. **Penulis:** perbaiki FIN-01 lewat forward correction; kirim kandidat baru dan bukti tiga jalur dengan kontrol sah serta atomisitas/refusal. Astra akan menerima atau menolak perubahan pada kandidat baru, bukan mengedit produk dari cabang audit.
2. **Penulis/owner pemegang arsip CP2:** siapkan bukti restore disposable menggunakan secret tetap di lingkungan pemegangnya: identitas ciphertext, engine/recipe, inventory, schema-owner-ACL, data/control totals, invariant bisnis dan cleanup. Auditor membaca hasilnya tanpa mengambil kunci.
3. **Pertanyaan owner yang belum terjawab:** apakah bukti restore CP2 tersedia untuk disiapkan pemegang aslinya? **Rekomendasi: minta bukti tersebut sebelum menyatakan penerimaan penuh CP1–CP7.** Jika tidak tersedia, catat pengecualian scope secara eksplisit; jangan mengubah CP2 menjadi PASS.
4. **Fable:** rekap petunjuk yang tersedia sudah masuk. Jika sisa sembilan dugaan atau laporan lain muncul, tambah addendum dengan atribusi dan pembuktian; tidak mengarang statusnya sekarang.

Laporan ini menyelesaikan putaran bukti saat ini dengan vonis TAHAN. Perbaikan FIN-01 dan pembuktian CP2 masih merupakan pekerjaan terbuka yang nyata.

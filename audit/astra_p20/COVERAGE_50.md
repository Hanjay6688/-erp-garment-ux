# Matriks 50 parent: cakupan dan batas yang tidak disembunyikan

50 baris di `CASE_MATRIX.md` adalah parent yang luas, bukan 50 eksekusi tunggal. Hasil nyata terdiri dari44ID kasus oracle mandiri; banyak kasus mempunyai beberapa subpemeriksaan dan beberapa parent ditopang kasus yang sama. **Tidak ada klaim50/50parent diterima.** Putusan19area wajib di `REPORT.md` memakai ruang lingkup yang tertulis, dengan tambahan rerun yang asal oraclenya tetap writer.

`MANDIRI` berarti eksperimen utama parent terlaksana; batas di kolom terakhir tetap berlaku. `SEBAGIAN` tidak menutup seluruh rincian parent yang diregistrasikan. `RERUN` berarti subcakupan itu memiliki bukti eksekusi suite writer oleh auditor, tetapi tidak ada oracle baru yang ditulis auditor untuk menutup parent tersebut. `COUNTEREXAMPLE` tidak diubah menjadi PASS. Klaim source review tidak menutup perilaku runtime.

| Parent | Bukti mandiri | Bukti tambahan / batas |
|---|---|---|
|01 Akses/replay|SEBAGIAN: cached/staged/AI, actor inactive melalui Auth, receiptPOST, finance OWNER/GUDANG/anon|Rerun permission setiap modul memperluas; tidak mengklaim setiap kombinasi actor×action×cache diuji sendiri.|
|02 Private surface|MANDIRI: enumerasi ACL seluruh private CP7 + percobaan REST nyata|Enumerasi menyeluruh adalah pemeriksaan grant; HTTP merupakan sampel route yang eksplisit, bukan satu HTTP per fungsi.|
|03 Izin setelah lock|MANDIRI: cabut izin pada penantian lock kapasitas lalu APPLY ditolak tanpa intent|Untuk jenis command lain tambahan ada pada races rerun.|
|04 UUID|SEBAGIAN: receipt, sale, correction, payroll dan staged replay; payload berbeda ditolak|Matriks lintas actor/lintas action seluruh facade tidak dibuat sendiri; tambahan pada rerun.|
|05 Hilang respons|SEBAGIAN: koneksi staged ditutup/dibuka dengan UUID sama|Lost-response business write dan lintas tab/rute memakai browser recovery rerun.|
|06 Rekonsiliasi uang|MANDIRI:73receipt→41FG→13jual→4retur; jurnal, AP, AR, HPP, laporan|Angka oracle sendiri ada pada witness fullflow.|
|07 Batas nominal|SEBAGIAN:21.474.836,47 /21.474.836,48 /22.000.000,01 lulus posting|Varian diskon nonnol pada ambang besar tidak mendapat probe mandiri tersendiri.|
|08 Alokasi/presisi|SEBAGIAN: operand6desimal, payable sen, residual0, latecost7stock/3COGS|Semua variasi komponen berbayar lintas ukuran yang tidak eligible belum ditutup oleh oracle mandiri pada putaran ini.|
|09 WIB/periode|SEBAGIAN:23:59:59 dan00:00:01 WIB, laporan periode aktual|Koreksi setelah close dan pemindahan tanggal jurnal tambahan melalui note/receipt correction rerun.|
|10 Harga laundry pending|MANDIRI: ALLOW_PENDING, HPP NOT_FINAL/closeblocked, lateprice1.29, recost12.90|Jumlah fisik tetap7 setelah3sold; bukan sekadar membaca flag.|
|11 AP/GRNI|SEBAGIAN: invoice17+56 setelah produksi; GRNI903.01→AP889.83, payment/credit|Rangkaian retur supplier fisik + semua variasi kredit lintas sumber tidak dibuat mandiri lengkap.|
|12 Koreksi paid AP|MANDIRI:17×11.23→15/19; credit22.46 ke target23PCS; kas tetap|Kasus target masa depan dan invoice bersama diperluas lewat receipt correction rerun.|
|13 Draf/retur AR|MANDIRI: reserve13 sekali, POST tanpa reserve kedua, return4 dan AR132.16|Rute multi-lot/multi-grade diperluas oleh rerun.|
|14 Koreksi AR|MANDIRI: harga returned line naik/turun ditolak; qty12−retur4, AR102.25, replay|Original facts tetap; bank137.03 tidak dibayar ulang.|
|15 Konservasi fisik|SEBAGIAN:137=103+27+7, replay, tambahan3GOOD menjadi100+30+7|Dua completion yang berlomba pada sumber yang sama tidak dibuat ulang sebagai oracle baru; races inherited tetap terpisah.|
|16 Membership/SKU|SEBAGIAN: membership berubah, policyMEMBERSHIP_CHANGED, oldcaptureARCHIVED_STALE|Semua variasi conversion/REVERSED CP6 tidak ditutup ulang oleh probe mandiri ini. CP6 tidak dibuka ulang dari bukti statis.|
|17 Koreksi biaya/tanggal|SEBAGIAN: monetaryrecost tidak membuat PCS, lateinvoice setelah produksi|Backdate/closedperiod/return pada kombinasi lengkap ditambah melalui rerun, bukan satu skenario mandiri baru.|
|18 Payroll|SEBAGIAN:46.33labor+36.49accessory, attendance0, carry/oldbalances dan cash145.32|Kode/roster/attendance/repair/native compensation melalui payroll rerun. Semua variasi nama sama dan netnegatif belum menjadi oracle baru.|
|19 Carry|SEBAGIAN:3dari4 hak carry dipakai sekali; replay/inverse mengembalikan hak|Earliest eligible payroll dan dua claim opening bersamaan belum ditutup dengan probe mandiri baru.|
|20 Model|MANDIRI: SES8,18,28α.5, holdout/lateknown tidak menulis ulang fold|Probe ini privat/kernel; realmodel/public/browse tambahan dari rerun.|
|21 Matcher|SEBAGIAN: allocator terikat matcher untuk wrongcolor/wrongsize/wrongref meski CANDIDATE_MATCH|Kernel integration PASS; tidak disebut transaksi live. Semua constraint model/adapter tidak mendapat oracle baru.|
|22 Prioritas/netting|RERUN: supply53/netting83 dan analysis|Tie-break dan semua parent/child WIP tidak ditutup oleh kasus baru tersendiri.|
|23 Jadwal|RERUN:71kasus schedule|Spillover/UNKNOWN sesudah kalender berasal dari oracle writer yang dieksekusi lagi. F01 adalah admission kapasitas plan, bukan bukti semua rumus schedule salah.|
|24 PL5|SEBAGIAN:205cut/193FG →91.6%;4groups/162 insufficient|Threshold200persis,180hari persis, fallback same-model dan perubahan bukti melalui PL5 rerun20.|
|25 PL8|RERUN: exhausted-proof/version dan physical/source suites|Tidak ada probe exhausted-group baru terpisah di44kasus mandiri.|
|26 5.000transport|MANDIRI: actual5000, exactkeys/hash/page/count, timeout8s|Perhitungan ulang parity single-path dan desktop app ladder tambahan rerun.|
|27 5.001/boundary|SEBAGIAN:5001 FAILED tanpa hasil/truncation|Literalerror assertion auditor ditarik; empty/non-ASCII boundary memakai transport/staged rerun.|
|28 Staged recovery|SEBAGIAN: reconnect UUID, DONEreplay dan finalretention|Dua stepworker bersamaan pada satu unit berasal dari staged rerun.|
|29 Captureinflight|RERUN: sourcecommit/freshness race suite|Ownstock/membership mutation membuktikan stale setelah perubahan, bukan semua transaksi capture in-flight.|
|30 Optimized/fullcheck|RERUN/source comparison|Tidak ada oracle baru per kategori mutasi/deletion. Bagian optimasi PR44 yang authored Astra tetap memerlukan penerimaan bebas konflik.|
|31 Rechecklive|SEBAGIAN: FGnow, PAUSEDpolicy, izin setelahlock|Material/WIP/product/need dan race lain diperluas oleh planv2 rerun18.|
|32 Sharedcapacity|COUNTEREXAMPLE F01|59+2 commit pada kapasitas60. v2/v2 kontrol writer rerun tidak menyembuhkan cross-version.|
|33 Reporttanggal|MANDIRI: snapshotlama + actual datedfinance, sale13/return4/payment137.03|Sections/hash dan historical report setelah retensi diuji. Racepublikasi terpisah.|
|34 Reportsealrace|RERUN: reportv2 sixraces|Tidak ada publisher-race oracle baru.|
|35 Reminder|SEBAGIAN: barang datang setelahclaim → finishsuppressed, nomoneywrite|Perubahan kewajiban sebelumclaim dan paymentvariant menggunakan reminder/attention rerun. Noexternaldelivery.|
|36 TanyaAI|MANDIRI: free-text/foreignID/21selected denied; boundedbrief valid|Bukti contract/permission, bukan akurasi layanan model eksternal.|
|37 K2|SEBAGIAN:7hari±30detik, unfinishedtua, reader/consumer dan reporthistoris|Lifecyclecancelled/failed serta tambahan race melalui K2rerun10.|
|38 K3retained|MANDIRI: everykeptrow/hash/time/index before/after;5temporarysets|Timezone comparator memiliki positive/negative control; nofieldomission.|
|39 K3detector|COUNTEREXAMPLE F04|Empat blindspot semantik pada copy dengan triggerdilemahkan; ordinaryimmutability tetap menolak.|
|40 K3atomic/race|SEBAGIAN: busydefer, faultmiddelete, dualcleaner, repeat|Tambahan status RUNNING/FAILED pada cleaner melalui K3rerun17.|
|41 Consumeraftercleanup|MANDIRI: DONE/planv2/reportv2/reminderv2/AIv2|Tidak ada perubahan finalrows/recompute pada jalur diuji.|
|42 Storage|MANDIRI:per-column pg_column_size dan relationallocation terpisah|Actual5000;95.487.684payloadbytes removed, finalexact.|
|43 Scheduler|COUNTEREXAMPLE F02; realtick/uninstall PASS|Kondisi dua database scheduler/role sama. Approvalflag dan HTTPprivatesurface diperiksa.|
|44 Restore|MANDIRI data556tabel dan rereadhasil; catalog via rerunP21|Tidak menyebut exception pg_cron berarti cron turut dipasang di restore.|
|45 Backupretention|COUNTEREXAMPLE F03;15actualrestores/14retained PASS|Clockcollision disimulasikan, actualdump unchanged/receipt overwritten; bukan nightlyconcurrency failure yang terbukti.|
|46 Integritastest|GAGAL F05|Staticoldassertions preserved, tetapi actualfinalizer mockNameError; metadataexpected drift.|
|47 UI|SEBAGIAN:48desktop+48mobile, financeboundary, nooverflow|Tidak mengklaim setiapcommand/rolecrossproduct diuji lewat browser. Prototypeclear; realcommandbrowser tambahan dari rerun.|
|48 FullP21|MANDIRI backup/data; keseluruhan9fase rerun|P21gladiPASS; penerimaan pemasangan belum diberikan.|
|49 Detectors|SEBAGIAN: finaltableimmutability danK3negativecontrols|Tidak mengklaim seluruhdetektor uang/stok pasti hidup untuksemua jalur.|
|50 Wholeflow|SEBAGIAN: worksheetwholeflow + lateinvoice + corrections sebagai variasi terpisah|Tidak menyebut semua retur/lateinvoice/closedperiod/accessoryobligation digabung dalam satu transaksi skenario lengkap.|

Tidak ada pekerjaan writer yang dibuat-buat untuk mengganti kekurangan bukti di tabel ini. Kekurangan bukti adalah pekerjaan audit/penerimaan, sedangkan perbaikan produk yang benar-benar terbukti dipisahkan di handoff. HOLD tidak otomatis menuduh parent SEBAGIAN/RERUN sebagai bug.

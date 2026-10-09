# Matriks 50 parent: cakupan dan batas yang tidak disembunyikan

50 baris di `CASE_MATRIX.md` adalah parent yang luas, bukan 50 eksekusi tunggal. Hasil nyata terdiri dari67ID kasus oracle mandiri (44awal+23kelanjutan); banyak kasus mempunyai beberapa subpemeriksaan dan beberapa parent ditopang kasus yang sama. **Tidak ada klaim50/50parent diterima.** Putusan19area wajib di `REPORT.md` memakai ruang lingkup yang tertulis, dengan tambahan rerun yang asal oraclenya tetap writer.

`MANDIRI` berarti eksperimen utama parent terlaksana; batas di kolom terakhir tetap berlaku. `SEBAGIAN` tidak menutup seluruh rincian parent yang diregistrasikan. `RERUN` berarti subcakupan itu memiliki bukti eksekusi suite writer oleh auditor, tetapi tidak ada oracle baru yang ditulis auditor untuk menutup parent tersebut. `COUNTEREXAMPLE` tidak diubah menjadi PASS. Klaim source review tidak menutup perilaku runtime.

| Parent | Bukti mandiri | Bukti tambahan / batas |
|---|---|---|
|01 Akses/replay|SEBAGIAN: tambah11endpoint staged/cache/AI/report/reminder: positif dahulu, lalu izin WIP dicabut dan seluruhnya ditolak|AS20C-01-CONSUMERS; hasil tersimpan tidak berubah. Aktor ADMIN aktif dengan4viewpermission; tidak mengklaim seluruh kombinasi actor×action.|
|02 Private surface|MANDIRI: enumerasi ACL seluruh private CP7 + percobaan REST nyata|Enumerasi menyeluruh adalah pemeriksaan grant; HTTP merupakan sampel route yang eksplisit, bukan satu HTTP per fungsi.|
|03 Izin setelah lock|MANDIRI: cabut izin pada penantian lock kapasitas lalu APPLY ditolak tanpa intent|Untuk jenis command lain tambahan ada pada races rerun.|
|04 UUID|MANDIRI pada replay yang dipilih; receipt UUID lintas aktor/aksi tidak membocorkan sukses atau menggandakan stok|AS20C-04-ACTOR; tambahan matriks setiap facade tetap rerun, bukan dibuat sendiri semua.|
|05 Hilang respons|MANDIRI: receipt commit lalu respons dibuang/reconnect; mobile RETURN respons HTTP benar-benar dibatalkan sesudah server sukses|AS20C-05-LOST dan AS20C-47-WRITE-MOBILE. Reload/reconcile memakai UUID+body identik; satu efek. Receipt memakai simulasi client-discard yang dilabeli.|
|06 Rekonsiliasi uang|MANDIRI:73receipt→41FG→13jual→4retur; jurnal, AP, AR, HPP, laporan|Angka oracle sendiri ada pada witness fullflow.|
|07 Batas nominal|MANDIRI: batas nominal besar ditambah diskon0.01 dan13.17 pada invoice riil|AS20C-07-DISCOUNT: net21.474.836,47 dan21.999.986,84; AP/cost/jurnal tepat. Bukan semua kombinasi tarif.|
|08 Alokasi/presisi|MANDIRI: unequal sizes11+7, umum1.37/PCS dan extra2.03 hanya3PCS ukuran kedua|AS20C-08-SIZE:15.07/15.68,total30.75 hingga receipt dan FG; ukuran pertama tidak menerima extra. Enam desimal dan bayar sen tetap lulus sebelumnya.|
|09 WIB/periode|MANDIRI: tengah malam WIB ditambah koreksi jual setelah economic day ditutup|AS20C-09-CLOSED: tanggal jurnal lama utuh, jurnal koreksi setelah close, FG33/AR102.25. Tidak mengarang larangan semua koreksi backdate.|
|10 Harga laundry pending|MANDIRI: ALLOW_PENDING, HPP NOT_FINAL/closeblocked, lateprice1.29, recost12.90|Jumlah fisik tetap7 setelah3sold; bukan sekadar membaca flag.|
|11 AP/GRNI|MANDIRI: two-stage invoice dan retur supplier nyata5×7.31; credit36.55 dipindah ke invoice lain|AS20C-11-RETURN: AP58.48/80.41→95.03/43.86; alokasi tidak menambah stok/kas, dependency guard dan inverse lulus. Bukan semua variasi AP.|
|12 Koreksi paid AP|MANDIRI:17×11.23→15/19; credit22.46 ke target23PCS; kas tetap|Kasus target masa depan dan invoice bersama diperluas lewat receipt correction rerun.|
|13 Draf/retur AR|MANDIRI: native dan dua perjalanan UI jual13/bayar137.03/retur4, GradeA serta GradeB|AS20C-47-WRITE-DESKTOP/MOBILE; FG32/AR132.16/COGS148.14. Multi-lot diperluas rerun; tidak diklaim baru dibuat sendiri.|
|14 Koreksi AR|MANDIRI: harga returned line naik/turun ditolak; qty12−retur4, AR102.25, replay|Original facts tetap; bank137.03 tidak dibayar ulang.|
|15 Konservasi fisik|MANDIRI: konservasi137ditambah2operator19+17berebut30siap-QC|AS20C-15-RACE: satu winner, replay satu efek; sisa sah diproses hingga100input=70WIP+30FG. Tidak menyembuhkan F01 yang berbeda.|
|16 Membership/SKU|SEBAGIAN: membership berubah, policyMEMBERSHIP_CHANGED, oldcaptureARCHIVED_STALE|Semua variasi conversion/REVERSED CP6 tidak ditutup ulang oleh probe mandiri ini. CP6 tidak dibuka ulang dari bukti statis.|
|17 Koreksi biaya/tanggal|MANDIRI: recost lateinvoice sesudah sale+return dan koreksi closedperiod|AS20C-50-LATE serta09-CLOSED; source/economic/posting date dan biaya diperiksa. Bukan seluruh kombinasi dalam satu skenario.|
|18 Payroll|SEBAGIAN: tambah2pekerja Rina berkode/IDbeda, rate23.17/31.29, full/halfday38.815→38.82|AS20C-18-ROSTER: labor6000tetap,net6038.82; approval WIP/payable38.82 sekali dan replay. Salah akun awal auditor dipisahkan. Netnegatif dan semua repair tetap diperluas rerun.|
|19 Carry|SEBAGIAN: tambah2payroll berebut4carry×2.50; hanya satu dapat hak|AS20C-19-CARRY:4unit/10sekali, expense+payable tepat,replay tidak duplikat. Earliest automatic accessory-carry selection belum punya oracle baru.|
|20 Model|MANDIRI: SES8,18,28α.5, holdout/lateknown tidak menulis ulang fold|Probe ini privat/kernel; realmodel/public/browse tambahan dari rerun.|
|21 Matcher|SEBAGIAN: allocator terikat matcher untuk wrongcolor/wrongsize/wrongref meski CANDIDATE_MATCH|Kernel integration PASS; tidak disebut transaksi live. Semua constraint model/adapter tidak mendapat oracle baru.|
|22 Prioritas/netting|MANDIRI: native need130/supply5/gap125 serta source17dibagi11/6dengan tie-break ID|AS20C-22-NET/TIE: lateETA tidak menghapus gap lebih awal; urutan input tidak mengubah hasil, deadline mendahului ID, unknown masuk review. Tie adalah kernel; bukan posting native semua adapter.|
|23 Jadwal|MANDIRI: kalender37+83,otherload61+7,captured11+13+17,3menit/PCS→3PCS|AS20C-23-SPILL: beban melewati kalender menjadiUNKNOWN.71case schedule rerun tetap tambahan; F01 tetap terbuka.|
|24 PL5|SEBAGIAN: tambah199PCS insufficient,200PCS memenuhi threshold dan Wilson dihitung sendiri|AS20C-24-199 plus205/193sebelumnya. Tepat180hari dan semua fallback same-model tetap rerun, tidak diklaim oracle baru.|
|25 PL8|MANDIRI: reverse BS membuka kembali grup yang sebelumnya habis; proof lama immutable|AS20C-25-REOPEN: re-dispose saja tidak mengaktifkan proof lama; proof baru sah mengembalikan eligibility. Skala long-history tambahan rerun.|
|26 5.000transport|MANDIRI: actual5000, exactkeys/hash/page/count, timeout8s|Perhitungan ulang parity single-path dan desktop app ladder tambahan rerun.|
|27 5.001/boundary|SEBAGIAN:5001ditolak; labelไทย🧵é dipertahankan dan panjang/hash dihitung UTF8|AS20C-27-UTF8: injeksi client root_ids=[] ditolak. Belum membuktikan pabrik global benar-benar tanpa produk; tidak menyamakan kedua kasus.|
|28 Staged recovery|MANDIRI: reconnect/DONE ditambah2stepworker bersamaan dan heldjob busycontrol|AS20C-28-WORKERS:20unit=20outputunik,hashpages tepat,DONE3kali tidak menulis ulang retained rows.|
|29 Captureinflight|SEBAGIAN: perubahan master mulai sebelumcapture, commit sesudahcapture;freshness berubah,oldpages identik|AS20C-29-INFLIGHT juga memeriksa delete. Hanya MASTER_DATA; bukan seluruh kategori perubahan. PR44 tetap butuh penerimaan auditor lain.|
|30 Optimized/fullcheck|RERUN/source comparison|Tidak ada oracle baru per kategori mutasi/deletion. Bagian optimasi PR44 yang authored Astra tetap memerlukan penerimaan bebas konflik.|
|31 Rechecklive|SEBAGIAN: FGnow, PAUSEDpolicy, izin setelahlock|Material/WIP/product/need dan race lain diperluas oleh planv2 rerun18.|
|32 Sharedcapacity|COUNTEREXAMPLE F01|59+2 commit pada kapasitas60. v2/v2 kontrol writer rerun tidak menyembuhkan cross-version.|
|33 Reporttanggal|MANDIRI: snapshotlama + actual datedfinance, sale13/return4/payment137.03|Sections/hash dan historical report setelah retensi diuji. Racepublikasi terpisah.|
|34 Reportsealrace|MANDIRI: dua publikasi expectedrevision1 benar-benar menunggu kunci series lalu berebut seal|AS20C-34-PUBLISH:1DONE/1FAILED,revisions[1,2],SHA256section+report dihitung sendiri; tidak ada campur output.|
|35 Reminder|SEBAGIAN: barang datang setelahclaim → finishsuppressed, nomoneywrite|Perubahan kewajiban sebelumclaim dan paymentvariant menggunakan reminder/attention rerun. Noexternaldelivery.|
|36 TanyaAI|MANDIRI: free-text/foreignID/21selected denied; boundedbrief valid|Bukti contract/permission, bukan akurasi layanan model eksternal.|
|37 K2|MANDIRI:7hari±30detik ditambah job yang benar-benarFAILED akibat accesschange|AS20C-37-FAILED:failureevidence dipertahankan,purge1receipt,clean-as-DONE ditolak. Staged mendukungRUNNING/DONE/FAILED; tidak mengarang endpointCANCELLED.|
|38 K3retained|MANDIRI: everykeptrow/hash/time/index before/after;5temporarysets|Timezone comparator memiliki positive/negative control; nofieldomission.|
|39 K3detector|COUNTEREXAMPLE F04|Empat blindspot semantik pada copy dengan triggerdilemahkan; ordinaryimmutability tetap menolak.|
|40 K3atomic/race|SEBAGIAN: busydefer, faultmiddelete, dualcleaner, repeat|Tambahan status RUNNING/FAILED pada cleaner melalui K3rerun17.|
|41 Consumeraftercleanup|MANDIRI: DONE/planv2/reportv2/reminderv2/AIv2|Tidak ada perubahan finalrows/recompute pada jalur diuji.|
|42 Storage|MANDIRI:per-column pg_column_size dan relationallocation terpisah|Actual5000;95.487.684payloadbytes removed, finalexact.|
|43 Scheduler|COUNTEREXAMPLE F02; realtick/uninstall PASS|Kondisi dua database scheduler/role sama. Approvalflag dan HTTPprivatesurface diperiksa.|
|44 Restore|MANDIRI data556tabel dan rereadhasil; catalog via rerunP21|Tidak menyebut exception pg_cron berarti cron turut dipasang di restore.|
|45 Backupretention|COUNTEREXAMPLE F03;15actualrestores/14retained PASS|Clockcollision disimulasikan, actualdump unchanged/receipt overwritten; bukan nightlyconcurrency failure yang terbukti.|
|46 Integritastest|GAGAL F05|Staticoldassertions preserved, tetapi actualfinalizer mockNameError; metadataexpected drift.|
|47 UI|SEBAGIAN:48rute×desktop/mobile ditambah2perjalanan tulis UI dengan oracle uang/stok sendiri|CREATE→POST→PAY→RETURN→paymentinverse→returninverse→saleinverse;GradeA/B,mobile lostHTTPresponse,reload,reconcile,screenshots. Bukan setiapcommand/role diuji sendiri.|
|48 FullP21|MANDIRI backup/data; keseluruhan9fase rerun|P21gladiPASS; penerimaan pemasangan belum diberikan.|
|49 Detectors|SEBAGIAN: finaltableimmutability danK3negativecontrols|Tidak mengklaim seluruhdetektor uang/stok pasti hidup untuksemua jalur.|
|50 Wholeflow|MANDIRI pada rangkaian73receipt→41FG→13sale→4return→lateinvoice17+56|AS20C-50-LATE:AP889.83,GRNI0,raw32/FG32,AR132.16;recost ke raw/FG/COGS exact. Koreksi closedperiod merupakan variasi terpisah; bukan semua kombinasi dunia nyata.|

Tidak ada pekerjaan writer yang dibuat-buat untuk mengganti kekurangan bukti di tabel ini. Kekurangan bukti adalah pekerjaan audit/penerimaan, sedangkan perbaikan produk yang benar-benar terbukti dipisahkan di handoff. HOLD tidak otomatis menuduh parent SEBAGIAN/RERUN sebagai bug.

# R9 — audit kontrak untuk keputusan scope C6 §0

**Batas pemeriksaan:** hanya `owner_c6_rev3.md`, Master Pulih, Perubahan Pulih, dan addendum CP7. Ini audit interpretasi teks, bukan audit kandidat/kode atau verifikasi bukti runtime. `M` = `ERP_V3_2_Master_Pulih_20260923.md`; `P` = `ERP_V3_2_Perubahan_Pulih_20260923.md`; `BR` = `ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md`.

## 1. Otoritas instruksi dan tiga CR

**Teks yang ditinjau:** owner C6 rev3:6–22, terutama kutipan verbatim pada :8 dan tafsir writer :10–22.

**Langsung didukung:** instruksi terakhir “gw mau semuanya dibikin sekarang dan diuji di cp 6” memang memberi dasar kuat untuk memasukkan pekerjaan yang dimaksud owner ke CP6; ia lebih baru dari rekomendasi M:1697 agar CR yang ditunda disimpan sebagai successor sebelum consumer CP7. M:1668–1669 menegaskan bahwa aksesori internal/pos/retur dan perluasan laundry merupakan kebutuhan; M:1692 merekomendasikan gelombang aksesori/laundry sebelum audit gabungan; M:1697 memperbolehkan penundaan hanya atas CR pilihan owner dan melarang menunda temuan baseline. P:80 menyebut ALL import masih kewajiban dan CP7 belum dimulai. Maka “kerjakan semua scope yang dimaksud sekarang” dapat mengubah penempatan CR ke CP6, tetapi tidak mengubah HOLD CP6, kewajiban gate, atau bukti yang diperlukan.

**Belum langsung terentail:** kutipan tidak menyebut ID `ACC-04b`, `LAU-05b`, atau `LAU-06b`; pemetaan “semuanya” ke ketiga baris tersebut adalah keputusan cakupan writer yang masuk akal dari C6, tetapi perlu ditandai sebagai interpretasi, terutama untuk `LAU-06b`. M:3728–3737 menyebut perluasan laundry yang disetujui (vendor, paket/komponen, unknown cost, invoice susulan, SKU opsional/snapshot), namun tidak menetapkan celup ulang BS yang menghasilkan SKU baru. M:1669 menyebut laundry expansion approved; M:1697 hanya memberi default successor untuk CR yang owner pilih tunda. Rekomendasi: tulis bahwa owner’s latest “semuanya” dipakai sebagai mandat CP6 untuk seluruh tiga CR C6 yang ditampilkan, sementara LAU-06b adalah scope tambahan yang mandatnya berasal dari frasa “semuanya” dan perlu diterima sebagai interpretasi eksplisit, bukan klaim bahwa ia bagian desain laundry yang sudah disetujui.

**Risiko/status:** tidak ada alasan mengembalikan pertanyaan owner hanya untuk menegaskan tiga ID jika sesi writer memang memiliki konteks C6; tetapi jangan melaporkan LAU-06b sebagai requirement yang sudah disetujui oleh M. Status: **mandat CP6 kuat; pemetaan item—khusus LAU-06b—interpretasi writer.**

## 2. ALL22 dan jalur impor/lanjutan

**Teks yang ditinjau:** owner C6 rev3:14–16 mengartikan “all 22” sebagai 22 keadaan, tiap keadaan punya jalur impor dan lanjutan valid, diuji dari impor hingga jurnal/layar, termasuk 7 `NO_ADAPTER` dan 6 `PARTIAL`; tiada histori lama dikarang. Kutipan owner memang secara eksplisit menyebut “all 22”.

**Yang didukung:** P:80 menyatakan ALL import tetap merupakan kewajiban dan tidak bisa disimpulkan dari banyaknya tipe CSV. P:1024 menyebut cakupan impor ALL data awal telah disetujui (master, stok/nilai, kas/piutang/utang/uang muka, dokumen operasional terbuka). P:1041–1047 dan P:1146 mempertahankan kewajiban ALL serta menyatakan CP7 tidak dimulai pada checkpoint yang relevan. M:357–379 mendukung aturan sumber saldo WIP/BS dan larangan mengarang riwayat yang tidak diketahui; M:930–938 membahas jenis master/opening saldo dan larangan mengklaim WIP fisik yang tidak diuji.

**Tidak didukung oleh locator yang dicantumkan / perlu koreksi:** C6:16 merujuk “M:369–379, M:930–938” sebagai dukungan untuk 22 keadaan NO_ADAPTER/PARTIAL. Baris itu mengatur saldo WIP/BS dan master/opening tertentu; keduanya tidak mendefinisikan register 22 keadaan, jumlah 7/6, ataupun kewajiban setiap keadaan punya jalur lanjutan. Tidak ada definisi 22 keadaan yang ditemukan dalam tiga kontrak yang diizinkan untuk audit ini. Jadi angka serta rincian 22-state bukan terverifikasi dari locator tersebut. Larangan mengarang histori didukung oleh M:369, :379 dan P:967; cakupan ALL umum didukung oleh P:80, :1024.

**Usulan teks:** “Owner secara eksplisit meminta seluruh 22 keadaan yang dimaksud dalam register ALL yang menjadi konteks instruksi; inventaris/ID dan jumlah 7 NO_ADAPTER + 6 PARTIAL harus dirujuk ke register kasus asal (belum diverifikasi oleh locator M:369–379/930–938). ALL tetap kewajiban CP6; jangan merekonstruksi histori yang tidak diketahui.” Jika register tidak tersedia pada bahan berwenang, catat `22-state mapping: UNVERIFIED`, bukan mengklaim 22 definisi telah dicocokkan.

**Risiko/status:** label “ALL22” boleh dicatat sebagai scope owner langsung; klaim kelengkapan pemetaan/status 7/6 dan seluruh rute tidak boleh dinyatakan sudah disahkan/dibuktikan. Status: **ALL impor langsung; hitungan/ID-state belum terverifikasi dari kontrak.**

## 3. Keputusan kebijakan, configurable options, dan safe defaults

**Teks yang ditinjau:** C6:17–20 mengusulkan semua baris kebijakan sebagai pilihan konfigurasi aplikasi (per vendor/per policy), dengan default ditolak atau pending sampai owner mengisi nilai; semua pilihan diuji, nilai nyata diisi owner saat cutover.

**Langsung didukung:** M:4454–4464 menyebut pertanyaan kebijakan aksesori yang belum diputus dan batas aman—jangan mereka tanggal, nilai recovery, akun, hak baru, harga gratis, atau pembulatan. M:4472–4477 mencantumkan rincian laundry yang belum diputus, termasuk unit/basis qty/tanggal/extra/diskon/pajak/rounding/SKU/mapping dan tindakan finansial saat unknown. M:4479 secara eksplisit membolehkan konfigurasi per vendor bagi ketentuan laundry yang memang berbeda antarvendor. M:1678 melarang false Rp0/final status dan penjualan/close baru tanpa policy; M:4475 secara langsung mengizinkan fisik pending tetapi melarang izin final sales/close baru tanpa kebijakan. M:4139–4143 membedakan FREE yang dikonfigurasi secara eksplisit dari rate yang hilang/query gagal, yang wajib diblok.

**Rujukan keliru/penyempitan perlu:** C6:18–20 menyebut pendekatan itu “sesuai M:1757”. M:1757 sebenarnya menetapkan konsekuensi bila CR masuk kandidat final CP6: acceptance terkait harus tuntas atau scope direvisi owner; ia tidak mengatur configurable policy fields atau default-nya. Dukungan aman-default datang dari klausul kebijakan (terutama M:1678, :4139–4143, :4454–4479), bukan M:1757. Per-vendor configurable terms didukung langsung hanya untuk laundry dan untuk kondisi antarvendor yang berbeda; kontrak tidak mewajibkan setiap keputusan kebijakan aksesori menjadi setting aplikasi.

**Status pengujian/isi:** “ditolak/pending” adalah default desain aman yang sesuai batas kontrak untuk alur yang bergantung keputusan, tetapi blanket “setiap opsi dapat dikonfigurasi dan setiap opsi diuji” adalah pilihan implementasi C6. Itu tidak boleh menghasilkan opsi finansial default yang diaktifkan, memakai angka fixture sebagai production seed, atau menerima transaksi final yang memerlukan policy. C6:20 sendiri menetapkan nilai nyata hanya diisi owner saat cutover; nilai tersebut tidak tersedia di teks kontrak.

**Usulan teks:** ubah sitasi di C6:18 menjadi “konsisten dengan M:1678, M:4139–4143, M:4454–4479”; nyatakan configurable controls sebagai cara implementasi yang diusulkan (wajib menjaga least privilege, default pending/rejected, no fake zero), bukan kewajiban eksplisit bahwa semua keputusan harus menjadi option. Sebut M:1757 khusus untuk kewajiban acceptance bila CR masuk CP6.

**Risiko/status:** menganggap pending sebagai izin alur final melanggar M; menganggap seluruh ketentuan wajib configurable terlalu luas. Status: **default aman didukung; cakupan setting per field pilihan writer; angka/keputusan finansial tetap pending.**

## 4. Conversion, celup ulang, dan identitas SKU/produk

**Teks yang ditinjau:** C6:11–13 memasukkan “ganti SKU hasil BS lewat konversi dan celup ulang” ke ACC-04b; C6:84–85 mencantumkan conversion/reuse dan customer garment service.

**Conversion aksesori / ganti merek:** M:3925 langsung mendukung flow conversion garment existing dengan panel untuk aksesori baru terpakai dan aksesori lama yang benar-benar dilepas/kembali. M:3913 menetapkan return dari ganti merek sebagai source bongkaran bekas dengan nilai recovery terpisah dan policy-dependent. Jadi conversion ganti merek dan linkage aksesori masuk akal dalam scope aksesori, sementara valuasi recovered goods tetap pending sesuai M:3933–3935 dan M:4456.

**Batas SKU laundry:** M:3735 menetapkan SKU/merek sebagai referensi atau tarif khusus **opsional**, bukan syarat untuk mengirim WIP tanpa final SKU. M:3094 memperjelas “Laundry SKU pricing bukan final identity”: pemilihan SKU untuk recipe/tarif tidak boleh otomatis mengubah WIP menjadi pasokan produk pasti. M:4116 meminta wash-process identity tetap dapat ditelusuri. Karena itu keputusan tentang tarif SKU tidak mengentail alur fisik celup ulang yang mengubah identity/warna/SKU produk.

**Tidak terentail dalam desain M:** M:1669 dan M:3728–3737 tidak menyebut redye/recolor BS menjadi SKU baru; M:5236 D03 adalah keputusan **nilai aksesori bekas dan rounding/depreciation recovery**, bukan product identity, conversion approval, atau laundry SKU transformation. LAU-06b pada C6:115 sendiri mengakui “Tidak ada klausul M”; C6:144–145 menyatakan tidak ditemukan di M/P/BR dan bahwa keputusan lama menempatkannya sebagai CR successor prioritas rendah. Dengan demikian, mandat umum terbaru dapat ditafsirkan memasukkan fitur ekstra itu ke CP6, tetapi ia tidak menjadi desain yang sudah disahkan oleh kontrak sebelumnya. Perubahan SKU harus punya keputusan owner yang memisahkan identity fisik/lineage dari rate/recipe reference dan menentukan conservation, QC, inventory/HPP serta reporting.

**Usulan teks:** pecah kalimat C6:11 menjadi (a) conversion ganti merek dan pencatatan aksesori sebagai kebutuhan aksesori yang didukung M:3913, :3925; (b) celup ulang BS menjadi SKU baru sebagai `LAU-06b`, fitur tambahan yang hanya masuk CP6 karena tafsir mandat terbaru “semuanya”, bukan karena M menyetujuinya. Tambahkan pagar: tariff/reference SKU tidak mengubah product identity; identity change hanya terjadi oleh command conversion yang sah dan lineage/QC/HPP-nya dibuktikan. Jangan memetakan “D03” ke transformasi SKU.

**Risiko/status:** pencampuran accessory recovery value, laundry pricing SKU, dan physical product conversion dapat memalsukan identitas persediaan atau biaya. Status: **ganti merek/accessory linkage didukung; celup ulang/new SKU adalah scope tambahan dari interpretasi instruksi terakhir, desain/acceptance detail belum terentail.**

## 5. Arti “D06” dan pengesahan formal lampiran

**Teks yang ditinjau:** kutipan C6:8 berbunyi “... termasuk all 22 lu harus bikin dan d06”; C6:21–22 menafsirkannya sebagai owner melakukan pengesahan formal D06 setelah audit, sementara penerimaan runtime perlu bukti kasus.

**Dukungan / ambiguitas:** M:1697 mensyaratkan pilihan owner jika suatu CR akan ditunda sebagai successor; sebaliknya instruksi terbaru dapat dibaca sebagai pilihan memasukkan fitur ke CP6. M:1757 memerlukan acceptance CR selesai atau scope kandidat direvisi owner secara eksplisit bila masuk CP6. M:4488 membedakan desain yang disetujui dari implementasi yang belum dibuktikan; M:4523–4525 mengharuskan audit independen setelah writer memverifikasi exact SHA. Jadi scope owner, implementasi, bukti writer dan audit independen adalah tahapan berbeda. Namun tiga kontrak tidak menetapkan prosedur bernama “formal ratifikasi D06” atas Lampiran C6 rev3.

“D06” juga bukan ID yang unik tanpa namespace: M:5239 adalah keputusan aksesori cash rounding `D06`; M:5301 adalah acceptance/Auth kasus `D06`. Kutipan singkat tidak menentukan apakah D06 berarti dokumen keputusan, pembulatan, atau case ID. Konteks C6 rev3:21 memilih artian ratifikasi lampiran, tetapi itu tetap interpretasi writer. C6:3–4 dan :24 dengan tepat menyatakan usulan belum disahkan.

**Usulan teks:** C6:21–22 sebaiknya dilabeli “langkah pengesahan yang diusulkan setelah pencocokan auditor, untuk merekam mandat scope CP6; bukan makna literal D06 yang dapat dipastikan dari kutipan.” Catat statusnya `OWNER_ACK_REQUIRED / NOT YET SIGNED`, tanpa mengklaim formal ratification sudah dilakukan. Jangan menganggapnya sebagai pemutusan ACC-DEC06 (rounding) atau lulus acceptance D06 Auth.

**Risiko/status:** menukar persetujuan scope dengan penerimaan runtime berisiko mengklaim CR telah diterima; menukar “D06” dengan cash rounding/Auth case dapat memutus policy yang salah. Status: **owner memilih scope CP6 dengan kuat; mekanisme formal dan referen D06 tidak pasti; pengesahan dokumen masih outstanding menurut C6 sendiri.**

## 6. LAU-04: harga unknown dan `post_sale_v2`

**Teks yang ditinjau:** C6:111, :132–138, dan :165 menyatakan hanya perilaku close-block yang baseline, `post_sale_v2` tidak memeriksa harga laundry, dan meminta auditor menilai apakah laporan incomplete cukup atau apakah itu “izin final sales” dalam M:4475.

**Kontrak yang mengikat:** M:1678 distingue harga `UNKNOWN` yang disengaja dari query gagal, membolehkan pemisahan proses fisik/nilai melalui lifecycle pending, tetapi menyatakan ini tidak mengizinkan status finansial final palsu atau penjualan/close baru tanpa policy. M:4475 menyetujui fisik pending dan HPP/laporan incomplete; secara eksplisit melarang izin final sales/close baru tanpa kebijakan. Jadi laporan incomplete **tidak dengan sendirinya** membuktikan sales boleh diposting final: status laporan dan finalisasi transaksi adalah kontrol yang berbeda.

**Belum terentail / keputusan auditor yang tersisa:** klausul tersebut tidak mendefinisikan apakah `post_sale_v2` yang tidak mengecek harga tetapi mempertahankan status biaya pending adalah “final sales” yang dilarang, atau apakah command hanya mem-posting sale dengan financial effects yang memang masih pending. C6 benar menandai celah ini untuk audit; jangan menutupnya dengan asumsi. Periksa dependency cost dan status transaksi pada boundary posting. Sampai interpretasi/guard dibuktikan, klasifikasikan final sale yang terdampak sebagai belum dibolehkan/pending policy, dan catat baseline risk/open issue, bukan `PASS` hanya karena laporan incomplete.

**Usulan teks:** pertahankan catatan LAU-04 dengan status `AUDITOR DECISION OPEN`; tambahkan bahwa “laporan incomplete saja belum menjawab izin posting sale; finalisasi sale yang bergantung pada nilai laundry unknown harus diblok sampai kontrak menyatakan bagaimana efek finansial pending dicatat.” Tidak perlu bertanya ulang kepada owner hanya untuk menegaskan hal yang M:4475 sudah jawab; eskalasi owner hanya jika implementasi/desain membutuhkan pilihan finansial baru.

**Risiko/status:** memungkinkan posted sale tanpa state/efek biaya yang eksplisit dapat melanggar M:1678/M:4475; menolak seluruh aktivitas fisik tanpa alasan juga melampaui aturan karena fisik pending memang diperbolehkan. Status: **close-block baseline dinyatakan; izin final sales belum diputus/dibuktikan.**

## 7. Dependency CP7 dan status ALL/CR

**Teks yang ditinjau:** C6:11–16 mengatakan tidak ada CR dipindah ke successor; C6:21–22 memisahkan penerimaan runtime dari pengesahan lampiran.

**Langsung didukung:** M:1694 menyatakan CP7 dimulai sesudah CP6 sah dan owner memberi perintah CP7. M:1697 menetapkan bila CR dikerjakan setelah baseline CP6 dikunci, ia harus disimpan sebagai successor sebelum consumer CP7 yang bergantung padanya, dependency yang berubah diuji ulang, dan PASS baseline lama tidak diwariskan ke kode baru. M:1678 menyebut laundry/accessory data akan dikonsumsi oleh planner dan melarang false finalization; M:1692 merekomendasikan aksesori/laundry sebelum audit gabungan bila dipilih. P:80 menyatakan CP7 belum dimulai dan gate CP6 masih ada. BR:510–523 mempertahankan urutan CP7 → CP7.5 → CP7C → CP8 serta menyatakan tambahan BR tidak mengganti checkpoint atau mengecilkan scope CP7; BR:7 membawa `CP6 HOLD`/`production_go:false`.

**Implikasi:** jika instruksi terbaru benar-benar memasukkan ketiga CR ke CP6, tidak ada dependency yang boleh dipakai untuk menurunkan cakupan CP7 atau menganggap CR selesai hanya dari C6/D06. CP7 tetap sesudah CP6 acceptance/gate dan perintah owner tersendiri; consumer-nya harus memakai data/linkage laundry/accessory yang dibuktikan. Bila sebagian CR tidak selesai dan kandidat CP6 diterima dengan baseline saja, simpan CR tersebut sebagai successor sebelum consumer CP7 membutuhkannya, sebagaimana M:1697.

**Konjektur yang harus dihindari:** “karena tidak ditunda ke successor” tidak berarti CP7 otomatis berizin dimulai setelah penulisan C6, atau bahwa semua CP7 consumer harus ditunda sampai setiap kebijakan bisnis terisi. M:1695 tetap menempatkan CP7.5/CP7C/CP8 sesuai urutannya; policy yang unresolved menahan bagian terkait, bukan otomatis seluruh roadmap (M:1695, :1747, :1757). BR tetap mewajibkan seluruh scope CP7 asli dan bukti tahapannya.

**Usulan teks:** C6:13 gunakan “CR tersebut dimandatkan untuk kandidat CP6; status selesai bergantung pada acceptance dan audit, bukan persetujuan dokumen. CP7 tetap menunggu CP6 sah + perintah owner. Jika ada bagian CR yang dikeluarkan dari kandidat final, daftarkan sebagai successor sebelum consumer CP7-nya.”

**Risiko/status:** scope CP6 boleh diperbesar instruksi baru, tetapi code/design signoff tidak mengubah HOLD atau CP7 gate. Status: **CP7 dependency tetap berlaku; C6 tidak mengotorisasi CP7 atau menyelesaikan requirement CP7.**

## 8. Ringkasan keputusan audit dan TODO

| Pernyataan C6 §0 | Penilaian teks | Status / tindak lanjut |
|---|---|---|
| “semuanya ... di CP6” | Instruksi scope terbaru langsung dan berdaya mengubah penempatan CR; mapping ke tiga ID C6 adalah tafsir yang kuat, khusus LAU-06b tetap tambahan terhadap desain disetujui M | Pertahankan sebagai mandat writer dengan catatan interpretasi LAU-06b |
| “all 22” | Frasa ALL22 eksplisit; kewajiban ALL eksplisit. Citations M:369–379/930–938 tidak membuktikan 22-state mapping atau hitungan 7/6 | TODO: cocokkan register asal atau tandai mapping 22 sebagai UNVERIFIED |
| pengaturan kebijakan/default pending | Safe defaults supported; konfigurasi laundry per-vendor supported. Menjadikan tiap policy option sebagai setting adalah pendekatan, bukan tuntutan eksplisit; M:1757 bukan dasar konfigurasi | Ganti sitasi M:1757 dengan klausul tepat; jangan isi tarif/hak/akun nyata |
| conversion/new SKU | Accessory ganti merek didukung. Laundry SKU rate reference bukan identity; redye/new SKU tidak disetujui eksplisit M | Pisahkan conversion aksesori dari LAU-06b; identitas/lineage/QC/HPP harus jadi acceptance eksplisit |
| formal D06 ratification | Scope owner diminta; kutipan “D06” ambigu, kontrak tidak menentukan proses ratifikasi bernama ini. C6 sendiri berstatus belum disahkan | Sebut sebagai rencana pencatatan approval; jangan klaim selesai, jangan samakan dengan DEC06/Auth D06 |
| LAU-04 sales | Close blocker disebut; batas M juga melarang final sales/close baru tanpa policy. Incomplete report tidak otomatis memberi izin final sale | Auditor harus menyelesaikan pertanyaan C6:137–138 sebelum menyatakan baseline diterima |
| CP7 dependency | CP7 sesudah CP6 sah + instruksi owner; successor CR sebelum consumer CP7 jika tidak masuk final CP6 | Tetap HOLD; jangan jadikan dokumen scope atau audit ini sebagai CP7 go |

**TODO tersisa:** (1) cari/rujuk register otoritatif untuk pemetaan ALL22 tanpa mengubah arti jumlah; (2) audit independen menilai `post_sale_v2` against M:1678/:4475; (3) pastikan approval owner scope dicatat dan berstatus belum formal sampai ada penerimaan nyata; (4) untuk LAU-06b, spesifikasikan perubahan identity BS→SKU target sebagai fitur tambah dan acceptance-nya; (5) tidak ada source, runtime, tests, code atau product changes yang diperiksa/diubah dalam audit ini.

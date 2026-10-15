# Astra — audit akhir gabungan CP1–CP7

Kandidat **dfab13bf62398a69a02bf6221c06d29075e5e40b**, tree **886f83312958b53781a450a4ea2a8fb2147b3be3**. Audit15OktUTC/16OktWIB, cabang `audit/astra-cp1-7-combined-dfab13bf-20261016`. Panduan Pro Max sha256 `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`. Tidak membaca laporan/run/cabang auditor lain dari putaran gabungan ini sebelum penguncian.

**Vonis: TAHAN penerimaan akhir dan pemasangan Enteng.** Lima akar cacat runtime Astra lama lulus uji ulang. Namun penjualan masih mempunyai dua cacat frontend yang dibuktikan sendiri, dan mode Enteng belum menyediakan sejumlah alur yang diuji CI. Status akhir tidak ditentukan oleh warna hijau80workflow. Detail tiap temuan terstruktur di `FINDINGS.json`; jawaban setiap temuan lama di `RETEST_ASTRA_dfab13bf.md`.

## Temuan yang harus ditangani

### ASTRA-C17-01 — seri lusin mencampur merek (S1, BARU)

**Akar:** `SalesDraftPanel.tsx:17,37–48` mengelompokkan, mencari, dan membagi seri hanya dengan string `commercial_sku`. Identitas merek/group tidak dibawa ke `Line` atau kunci seri. `scripts/cp7-src/sales/form.sql:22–27` dapat mengembalikan lebih dari satu merek. Native BF mendefinisikan `bf_skus_v1 UNIQUE(brand_id,sku)`, sehingga nomor SKU sama pada Vivo dan Widie merupakan keadaan sah.

**Reproduksi independen:** run38787151612/job116601978427, `ASTRA_UI_SERIES_MUST_PRESERVE_BRAND` **COUNTEREXAMPLE**. Dua pilihan stok sah: Vivo/73001/32 dan Widie/73001/32, stok30masing-masing. Pilih Vivo saja. Aplikasi membuat “Seri73001 · 2ukuran(32/32)” dengan **Vivo6 + Widie6**. Seharusnya seri Vivo satu ukuran menerima12; Widie tidak ikut dipilih. Perhitungan total12 benar tetapi identitas barang salah. Kondisi sama juga mencampur kelompok ketika draft lama memuat kedua merek.

Label bukti `INDEPENDENT_DOM_PROBE` + `INDEPENDENT_SOURCE_REVIEW`, bukan browser/PostgREST lintas merek atau posting penjualan nyata. Fixture/transport DOM diadaptasi dari penulis; oracle identitas Astra. Ini tidak membuktikan SQL memilih lot yang salah setelah menerima product_id yang benar; cacat terjadi lebih awal saat UI memilih product_id.

**Perbaikan:** bawa identitas seri stabil (SKU group/versi dan merek) dari server sampai form, grouping dan split. Uji merek sama/beda, nomor sama, ukuran sama/beda, draft reread/correction dan desktop/HP. Jangan hanya mengganti teks tampilan atau mengunci nomor SKU global yang sah per merek.

### ASTRA-C17-02 — simpan bisa mendahului muat ukuran (S2, BARU)

Run38786981837/job116601389798, `ASTRA_UI_PENDING_SERIES_SAVE` **COUNTEREXAMPLE**. Draft valid dengan2baris telah direview. Pilih seri baru3ukuran lalu tahan respons pembaca seri. Saat “Memuat semua ukuran…” terlihat, tombol Simpan masih aktif dan `onSave` menerima **2baris lama**. Setelah respons dibuka, form mempunyai5baris. `valid`/`blocked`/`save()` tidak memasukkan `seriesBusy`; review baru dihapus setelah respons, bukan ketika pilihan dimulai. Parent `ConnectedSalesPage.tsx:70,104` menutup draft setelah hasil commit diterima, sehingga pilihan baru dapat tertinggal dari nota tersimpan.

Bukti adalah DOM nyata dengan respons RPC ditahan, plus source parent; belum posting server pada jaringan lambat. Perbaiki dengan membatalkan review dan memblokir save/correction selama pemuatan seri; pertahankan draft ketika hasil gagal/terlambat. Uji respons setelah save attempt, gagal, ganti tanggal, dan tutup form. Tidak perlu melonggarkan pemeriksaan stok server.

### ASTRA-C17-03 — build Enteng masih membuka contoh (S1 penerimaan operasional, sudah diketahui penulis; dikonfirmasi)

`App.tsx:637–638,761`, `ConnectedFgHandoffBoundary`, `TransactionSourceNavigation`: sales, enam layar finance, absensi dan Nota yang diuji lewat disposable belum dibuka sebagai alur nyata Enteng. Inventaris48menu: **Enteng23tersambung di kode,23contoh,1batas Nota,1pemberitahuan Dashboard**; disposable35tersambung,12contoh,1pemberitahuan. Tersambung di kode tidak berarti CP7 sudah dipasang pada hosted.

DOM Astra `ASTRA_UI_FINANCE_SAMPLE_IDENTIFICATION` **COUNTEREXAMPLE**: hero Ringkasan Keuangan dan Payroll berisi tombol sehingga `FinanceHero` tidak merender tanda “SIMULASI UX”, padahal angka rupiah contoh tetap terlihat. Dashboard connected menyuruh pengguna melihat menu lain untuk angka asli, walau sebagian tujuan Enteng masih contoh. Ini dapat membuat pengguna menganggap angka contoh sebagai angka usaha.

Jangan memasang dengan klaim semua alur siap. Tetapkan activation matrix dan rencana migrasi CP7 yang disetujui, lindungi halaman contoh dengan tanda yang tidak tergantung tombol, dan uji **build Enteng** ke backend sekali pakai dengan Auth nyata. Larangan menyentuh hosted tetap dipatuhi. Mengganti enum secara massal tanpa memastikan RPC/otoritas/kontrak bukan perbaikan yang cukup.

### ASTRA-C17-04 — master harian belum punya jalan tersambung (S1 kelengkapan operasional, diketahui penulis)

Pelanggan, supplier/partner, mandor, lokasi, kain/benchmark, aksesori/harga mandor tetap komponen state lokal di semua mode (`MasterDataPages`, `MaterialMasterPages`; route `App.tsx:753–754`). Impor saldo awal dan master vendor laundry tertentu tidak menyediakan seluruh CRUD harian ini. Contoh: menu Pelanggan tidak bisa menambahkan pelanggan server yang kemudian dipilih invoice. Daftar barang/mandor yang sudah ada di fixture CI menutupi kebutuhan ini.

Bukti `INDEPENDENT_SOURCE_REVIEW`; tidak mengklaim setiap domain sama sekali tidak memiliki fungsi Native. Sediakan alur master harian dengan aturan edit/deactivate/identity yang sah atau nyatakan batas operasi yang diputuskan owner. Catat sebagai pekerjaan produk, bukan meminta owner memakai SQL.

### ASTRA-C17-05 — layar selesai PO tidak mencerminkan seluruh keadaan server (S2, BARU)

Oracle Astra run38786437050/job116599507708 membuktikan alur10pcs, bahan100+upah40+laundry20→HPP160 danWIP0. Hasil `FINISHED` sah namun HPP server masih **BELUM_LENGKAP / ESTIMATED**, alasan laundry belum final dan engine estimated. `PoFinishPanel.tsx:83–85,99–100,135–138` tetap menyebut “HPP final”, “menjadi final”, “kunci HPP final”. Catatan pending memang ditampilkan; jangan mengklaim pending disembunyikan seluruhnya. Masalahnya kalimat final yang bertentangan dengan status tersebut.

Dua kontrol lain:10dipotong, baru4menjadiFG (enam belum dijahit atau sudah dijahit tetapi belum dikirim). Workspace memberi `eligible=true, blockers=[]`, lalu Native `guard_finished_po_source_accounting` menolak penyelesaian dan seluruh perubahan rollback. **Tidak ada kehilangan stok yang terbukti**; hipotesis korupsi penutupan dibantah. Preflight UI perlu memakai batas fisik yang sama dan pesan sukses harus mengikuti `display_status`/pending, sambil tetap mengizinkan produksi selesai dengan biaya provisional bila kontraknya mengizinkan.

### ASTRA-C17-06 — pengganti arsip belum diterapkan ke semua entry point (S2 alat uji, BARU)

G01 run38786023729/job116598114330 dan tiga job T2 run38786023817 berhenti **sebelum kasus** karena arsip10392910720HTTP410. Writer benar memperbaiki paket T3/CP17, tetapi `cp6-g01-baseline.yml`/`cp6-t2-regression.yml` kandidat masih mengunduhnya tanpa fallback; T2 juga memanggil bootstrap dari checkout CP6 lama. Hasil hijau sebelumnya tetap bukti pada waktunya, bukan bukti workflow dapat dijalankan sekarang.

Astra melakukan tepat satu retry pre-case lewat adapter pada cabang audit, bukan produk: T2 memakai bootstrap dfab13bf dengan D14-17; G01 berhenti sebelum U/X dan membuktikan input itu tidak dikonsumsi. `INFRA_RETRY.md` menjelaskan perubahan dan log pertama dipertahankan. G01 retry kembali15kategori cocok, ledger platform70entri beda metadata bootstrap seperti batas lama. Entry point writer harus diperbaiki secara eksplisit tanpa mengubah frozen apply/X/oracle.

### ASTRA-C17-07 — penerimaan “seluruh rantai melalui aplikasi” belum terbukti (S2 cakupan)

`CHAIN_REVIEW.md` memberi vonis masing-masing B1–B13/S1–S7; `SCREEN_REVIEW.md` memberi48vonis per mode. Bukti Native kuat tidak diganti menjadi klaim browser. POST potongan/bagi/QC dari awal, nota aksesori→potong payroll→kas, rework→nota→bayar, imporWIP→produksi→jual→kas dan lifecycle pool HPP absensi masih mempunyai batas bukti aplikasi. Sebagian browser source-navigation membuka atau membalik transaksi yang disiapkan fixture; itu tidak membuktikan langkah penciptaannya. Kalender, close period/adjustment di tengah satu perjalanan penuh, dan semua role/HP juga belum teruji menyeluruh.

## Vonis tujuh tahap

| Tahap | Hasil audit | Batas yang tetap |
|---|---|---|
| CP1 baseline | LULUS DENGAN BATAS BUKTI | Hash7salinan cocok; rekonstruksiG01 Astra15kategori cocok, metadata ledger platform berbeda. Hosted16/16 adalah laporan Fable putaran lama yang sudah dikunci, bukan akses Astra hari ini. |
| CP2 backup lama | BUKTI LOKAL DITERIMA BERSYARAT; BELUM LULUS PENUH | Laporan restore PG16/stub lama dibaca; image Supabase asli, definisi/owner/ACL lengkap dan Storage round-trip belum dibuktikan. Pekerjaan CP7C ditahan sesuai owner, tidak dijalankan diam-diam. |
| CP3/3.5 absensi–HPP–payroll | Perbaikan akar FIN01/HPP01 lulus; cakupan qualified | Rerun CP17, kontrol overlap dan T2; lifecycle UI pool dan perjalanan seluruh payroll masih batas. |
| CP4/4.5 HPP/akses/pola | Qualified; penerimaan operasional bersyarat | Access gate/HTTP teruji;82EXECUTE ditunda D14-9; G2 status/pra-kondisi UI perlu dibetulkan. |
| CP5 potong–laundry–QC–BS | Perbaikan STK01/FIN02/RWK01/SG1–3 lulus dalam batas | A3 konservasi tambahan lulus; semua cabang browser tidak disertifikasi. |
| CP6 regresi/ledger/cutover | Qualified, bukan semua kasus berlabel PASS | T2 mempertahankan disposition historis, G01 metadata limit, entry point arsip harus diperbaiki. Detail akhir run di EXECUTION_RECEIPT. |
| CP7 integrasi dan layar | **TAHAN** | Dua cacat penjualan baru, statusHPP, activationEnteng, master harian dan kekurangan bukti aplikasi di atas. |

## Keputusan lama yang tetap berlaku

A2 akar dua kegagalan lama tetap OPEN/non-blocker (D13-10); pembanding stabil teruji. SOL-003 penyebab AZ pertama belum terbukti, mitigasi drain teruji. FABLE-01282EXECUTE tetap tugas CP7C dan tidak boleh melewati exposure gate. CP2 kunci yang dilaporkan terpapar tidak dipakai untuk backup baru. CP7C/Drive tetap HOLD; tidak meminta kunci/password, tidak mengakses hosted, tidak mengubah main/deployment/branch writer. FABLE-011 batas tanggal cutover global belum menjadi aturan owner baru. SG-01 tingkat lanjut tetap ditolak; SG-02 inverse current-clock diterima; SG-03 mengikuti D06 gratis. Tidak mengulang pertanyaan yang sudah diputuskan owner.

## Bukti dan batas penghitungan

- A61:61PASS tepat menurut manifest; comparator1PASS terpisah; kontrol drain terpisah.
- AP18:2PASS, delapan batas siklus dan dua batas koreksi harga; seluruh akun terjelaskan dan jurnal seimbang. Modal1200 sudah ada sebelum delta kas dihitung.
- A3:3PASS dari oracle Astra, restorasi/public/ACL/session/advisor gates lulus; selesaiPO dengan sisa enam pcs ditolak Native.
- DOM Astra:4skenario,1PASS dan3COUNTEREXAMPLE (dua penjualan serta label contoh). Job hijau berarti program observasi selesai; **bukan empat kasus lulus**.
- T2 selesai: 326 kasus asli = 275 PASS, 39 CONTROL_PASS, 12 kebijakan tanggal; AS34 = 25 PASS, 8 COUNTEREXAMPLE, 1 INCOMPLETE; AO12 = 8 PASS, 4 INCOMPLETE. Oracle yang disetujui memberi 8 MATCH, 5 PASS, dan 25 PASS C0 terpisah. AR174 = 173 PASS, 1 INCOMPLETE karena kebijakan gratis; kasus pengganti penolakan gratis 1 PASS. Temporal/master 41 PASS. Semua clone dibersihkan dan primary tetap sama. Status lama tetap dipertahankan; rincian diagnostik kalender dan kelompok tambahan ada pada receipt. T2 memakai stack Native CP6 gabungan, bukan seluruh ekstensi CP7.
- Penulis:80run/131job latest attempt dibaca;79run success+1cancelled,127job success+4cancelled. Bukan80test case.4730rekaman unik job/group/case yang eksplisit JSON:4613PASS,58CONTROL_PASS,18NOT_APPLICABLE,16NO_ROUTE,12DATE_POLICY_REVIEW_REQUIRED,11COUNTEREXAMPLE,2INCOMPLETE. Ini subset structured logs, bukan total semua SQL/Vitest/CodeQL assertions. BEFORE AV/BE, status kebijakan dan legacy CP6 UI gap diberi konteks, tidak dituduh sebagai regresi produk dfab13bf begitu saja.
- Offsite percobaan pertama job116435556014 gagal bind port54324 sebelum kasus; percobaan kedua berhasil. Log membuktikan port terpakai, tidak membuktikan siapa yang memakainya. CodeQL cancel dan run pengganti dicatat terpisah; penyebab niat “dinyalakan dua kali” adalah penjelasan writer, metadata membuktikan cancel/replace.

Asal-bukti, SHA log, URL run/job/artifact, case ID, kegagalan pertama dan status akhir ada di `EXECUTION_RECEIPT.json`, `WRITER_LOG_INDEX.json`, `REUSED_WRITER_CASE_LEDGER.json`, `INDEPENDENT_CASE_DETAILS.json`. Identitas produk sebelum/sesudah ada di `MANIFEST.json`/`REPORT_LOCK.json`. Tidak ada bukti auditor lain putaran ini yang dibaca untuk menyusun vonis.

## Sebelum pemasangan Enteng

1. Perbaiki pemisahan seri berdasarkan identitas merek/SKU dan pagar save saat seri dimuat; buktikan desktop/HP, payload dan reread server.
2. Cocokkan label/pra-kondisi selesaiPO dengan statusHPP dan sisa fisik server; jangan melemahkan Native guard.
3. Tetapkan aktivasi layar, kebutuhan master harian dan penandaan contoh; jalankan alur build Enteng ke backend disposable, termasuk celah20sambungan yang dicatat.
4. Perbaiki entry point bukti yang masih bergantung arsip kedaluwarsa; pertahankan first-failure, frozen gates dan oracle.
5. Setelah owner membuka CP7C, penuhi backup/restore, kunci baru, revoke/exposure gate, detector data lama dan pembersihan data UAT sesuai keputusan yang sudah ada. Laporan ini bukan izin melangkahi HOLD.

`feature_complete=false`; `production_go=false`. `audit_complete` berarti pemeriksaan lingkup putaran ini selesai dengan keterbatasan terbuka yang dinyatakan, bukan jaminan semua perilaku ERP telah diuji. Seluruh job Astra selesai; penguncian dan hash bukti dicatat di REPORT_LOCK.json.

# Astra — audit ulang CP1–CP7, r2

**Vonis: TAHAN.** Audit putaran ini selesai; kandidat belum memenuhi penerimaan penuh. Ada **dua akar cacat baru S1**, dibuktikan oleh tiga kontra-contoh independen. Lima temuan lama Astra tertutup; entry point G01/T2 pulih; bukti alur aplikasi bertambah, tetapi lifecycle UI pool HPP absensi masih terbuka. `feature_complete=false`, `production_go=false`.

Kandidat: `2e9d6a468c110684c278d585418eb404250d1150`, tree `5e50d224f8e74fa3bca83b599fb606739435b598`. Dokumen penulis dibaca pada `b388a4b7d4b0291de81b68d1e624a062eda5edd1`; deltanya hanya dokumen. Cabang auditor: `audit/astra-cp1-7-r2-2e9d6a46-20261016`. Basis laporan lama: lock `3a3da9ef`, dilengkapi sampai `5a5beeb23d7f57f157e02bca877fcfd19e5c6f86`. Panduan Pro Max SHA-256 `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`.

## 1. Batas dan asal bukti

Tujuh run auditor, sebelas job, seluruhnya selesai. Checkout aplikasi selalu dipin dan diperiksa ke kandidat di atas. Karena connector tidak menyediakan dispatch, run dipicu oleh perubahan workflow auditor sendiri pada cabang auditor; kode produk dan workflow penulis tidak diubah. Ini `INDEPENDENT_NATIVE_RERUN`, bukan pemakaian warna hijau penulis sebagai vonis. Fixture pembangun runtime memakai helper penulis beku; asal oracle dibedakan di bawah.

Tidak membaca laporan/cabang/run auditor lain dari r2 sebelum laporan ini dikunci. Laporan lama yang sudah dikunci serta audit silang penulis atas laporan lama boleh dibaca. Tidak mengakses/mengubah hosted, legacy DB, Drive, deployment, main, atau cabang penulis. Semua mutasi uji berada dalam database CI sekali pakai.

`FINAL_IDENTITY_CHECK.json` membuktikan tree produk sebelum/sesudah sama, `supabase/` tidak berubah sejak dfab13bf, serta delta cabang hanya berkas audit dan tujuh workflow auditor. Setiap job Native/browser memeriksa pemulihan boundary dan membersihkan database. Log mentah, termasuk seluruh kegagalan, disimpan di `RAW_LOGS.tar.xz`; indeks ukuran/hash di `RAW_LOG_INDEX.json`.

## 2. Hasil eksekusi, tanpa menghitung ganda

| Run | Cakupan | Hasil dan asal oracle |
|---|---|---|
| [38928849615](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38928849615) | G01 baseline | SUCCESS. Rekonstruksi dan alignment terhadap fingerprint hosted yang disimpan; bukan query hosted hari ini. Oracle penulis, dieksekusi auditor. |
| [38928849640](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38928849640) | CP17 | **145/145 ID persis manifest PASS**: Native80, race18, HTTP Auth nyata14, browser33. Tambahan comparator1 PASS dicatat terpisah. Oracle penulis. |
| [38928849710](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38928849710) | T2, temporal, AR | Tiga job SUCCESS; status kasus lama tetap memerlukan disposition, lihat §5. Bukan seluruh kasus mentah PASS. Oracle beku/historis. |
| [38930682418](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38930682418) | DOM Astra | 4 PASS, kasus Astra lama dipertahankan. |
| [38930682447](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38930682447) | Native Astra | 11 ID: **8 PASS, 2 COUNTEREXAMPLE, 1 INCOMPLETE**. Job FAILURE dipertahankan. |
| [38931015958](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38931015958) | Matriks browser Astra | 288 PASS: 48 menu × desktop/HP × tiga mode. Termasuk 34 pemeriksaan menu tersembunyi; **254 halaman benar-benar dirender**, bukan 288 perjalanan transaksi. |
| [38938202330](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38938202330) | Kualifikasi oracle FG v2 | Hanya satu ID yang sama: **COUNTEREXAMPLE**. INCOMPLETE sebelumnya tetap tersimpan; bukan tambahan kasus unik. |

Kasus beroracle Astra: **303 ID unik = 300 PASS + 3 COUNTEREXAMPLE**, dari 304 observasi karena satu kualifikasi alat. Angka ini memasukkan pemeriksaan render/menu, bukan 303 rantai bisnis. Tidak dijumlahkan dengan 145 CP17, T2, predecessor checks, atau bukti historis. Detail: `CASE_ATTEMPTS.json.gz`, `CASE_COUNTS.json`, `INDEPENDENT_CASES.json.gz`, `RUN_REGISTER.json`.

Oracle independen Native yang lulus: konservasi 10 potong/HPP160/WIP0; dua kontrol sisa6 yang harus menolak FINISH; kas37,13−20,11=17,02, koreksi20,10 ditolak karena −0,01 dan31,15 menghasilkan11,04; batas UTC16:59:59/17:00:00 terhadap WIB00:00 dan otoritas owner; pelanggan dipakai draf→tolak nonaktif→batal draf→boleh nonaktif, akses dicabut→replay ditolak; detektor dua basis tanggal; urutan input wave B1/A2 tetap upah31+22=53, tiga potong, UUID sama satu efek. Fault injection detektor mematikan guard hanya dalam savepoint terisolasi, dipulihkan dan diperiksa; itu bukan bukti bypass aman.

## 3. Dua temuan baru

### ASTRA-R2-01 — S1 — Pembukaan ulang PO tetap terkunci setelah pemakaian FG dibatalkan

**BARU; NATIVE_QUALIFIED; `INDEPENDENT_NATIVE_RERUN` + `INDEPENDENT_SOURCE_REVIEW`.** Satu akar masalah, dua reproduksi; bukan dua temuan.

1. PO selesai dengan10PCS. Draf penjualan mereservasi2, stok10→8. Batalkan draf melalui jalur publik: statusCANCELLED, stok kembali10, seluruh akun sama dengan awal. Ruang kerja baru tetap mengembalikan `FG_USED qty2`; command publik dengan review baru ditolak `CP7_PO_REOPEN_BLOCKED`. Kasus `ASTRA_R2_REOPEN_AFTER_CANCELLED_SALES_DRAFT`, run38930682447/job117073574552.
2. PO selesai dengan10PCS, HPP120/basis10. PenyesuaianFG−2 memang memblokir pembukaan ulang saat stok8 (kontrol positif). Sesudah inverse sah, stok10 dan HPP120/basis10 pulih; workspace/command tetap ditolak FG_USED2. Kasus `ASTRA_R2_REOPEN_AFTER_REVERSED_FG_ADJUSTMENT`, kualifikasi v2 run38938202330/job117098919279.

Akar: `scripts/cp7-src/cutting-correction/po-reopen.sql`, `reopen_po_snapshot`, baris46–47 menjumlahkan **semua mutasi historis negatif** tanpa meniadakan pasangan pembalikannya. Jalur command memakai snapshot yang sama. Penggunaan yang sudah tidak aktif tetap dianggap pemakaian hilir. Ini merusak alur koreksi D15-4, walaupun menolak secara aman dan tidak terbukti menghilangkan uang/stok. Menurut Pro Max §keparahan, alur koreksi yang macet adalah S1.

Perbaikan: nilai pemakaian aktif dari fakta/pasangan reversal yang benar; jangan sekadar memakai saldo total jika itu dapat menghapus penggunaan hilir yang masih aktif. Pertahankan penghalang untuk reservasi aktif, penjualan/pemindahan/penyesuaian aktif, periode tertutup, izin, stale review, dan concurrency. Retest kedua kasus Astra tanpa mengubah hasil yang diharapkan, tambah kontrol pembatalan sebagian dan dua tab, lalu reopen→finish ulang harus tetap tepat stok/HPP/GL dan idempoten.

**Koreksi alat terbuka:** percobaan pertama FG berhenti INCOMPLETE pada oracle auditor `accounts()==before`. Oracle opening lot itu keliru untuk production lot: Native `sync_po_hpp_to_gl` yang sudah diterima memakai OTHER_EXPENSE+24 dan OTHER_INCOME−24 saat pasangan adjustment/inverse ini. Sebelum v2 dijalankan, sumber AY dan perubahan oracle didokumentasikan di `QUALIFIED_ORACLES_V2.json`/`TOOL_QUALIFICATION.md`. V2 mencatat semua delta akun dan equality lama=false; hanya ekspektasi klasifikasi akun diperbaiki, stok/HPP/reopen tidak dilonggarkan. Penyajian gross income/expense warisan ini tidak disahkan ulang sebagai kebijakan keuangan baru. Tidak ada rerun kasus lain untuk mengejar hijau.

### ASTRA-R2-02 — S1 — Nomor PO otomatis tidak melewati 999

**BARU; NATIVE_QUALIFIED; `INDEPENDENT_NATIVE_RERUN` + `INDEPENDENT_SOURCE_REVIEW`.** Kasus `ASTRA_R2_AUTO_PO_NUMBER_999_TO_1000`, run38930682447/job117073574552.

Fixture memasang998 PO DRAFT sah yang belum dipakai, nomor harian001–998. Posting potongan nyata berikutnya sukses membuat999 dan stok bahan10→8. Posting berikutnya, yang seharusnya membuat1000 dan stok6, macet sampai `statement_timeout=10s` yang sudah dideklarasikan sebelum uji (SQLSTATE57014). Setelah rollback savepoint, stok tetap8 dan boundary/history/request tidak berubah. Tidak ada percobaan kedua.

Akar: `scripts/cp7-src/cutting-correction/auto-po.sql`, baris216–217, memakai `lpad(v_n::text,3,'0')` juga untuk angka lebih dari tiga digit. Angka1000 menjadi100, sehingga loop terus mencari di nomor yang sudah terpakai. Dengan001–999 terisi, tidak ada jalan keluar lewat nomor empat digit; lock nomor harian tertahan sampai statement dibatalkan. Dampak terbukti membutuhkan volume999 PO pada hari yang sama; bukan klaim bahwa penggunaan biasa selalu macet.

Perbaikan: format nomor tanpa memotong digit, tetap serialize penomoran harian dan atomik bersama posting. Retest998→999→1000→1001, nomor berlubang/tabrakan, dua posting bersamaan, serta resend UUID sama. Jangan mengubah timeout atau menurunkan fixture untuk menyatakan kasus lama lulus.

## 4. Uji ulang temuan lama dan fitur r2

| Butir | Vonis | Bukti / batas |
|---|---|---|
| ASTRA-C17-01, seri lintas merek | **DITUTUP** | DOM Astra merekVivo73001 hanya satu ukuran/12PCS, Widie tidak masuk. Browser CP17 desktop/HP memakai dua merek dengan SKU sama; stok merek lain tetap5, hasil server dibaca ulang. |
| ASTRA-C17-02, simpan saat seri masih dimuat | **DITUTUP** | DOM asli `disabled=true`, `saves=0` selama lookup; sumber mereset review dan menahan save. |
| ASTRA-C17-03, angka contoh di Enteng | **DITUTUP pada kontrak aktivasi kandidat** | DOM label SIMULASI dan matriks mode Enteng pada server sekali pakai.17 menu contoh tidak ada di navigasi; sumber direct route menampilkan batas. Tidak menyatakan CP7 sudah terpasang di Enteng. |
| ASTRA-C17-04, master harian | **DITUTUP untuk cakupan D15-3** | CP17 lifecycle/race/HTTP dan enam keluarga layar desktop/HP; mandor/rate→pickup→jahit; kasus Astra pelepasan blocker dan pencabutan akses. Bukan seluruh kemungkinan katalog/import/volume. |
| ASTRA-C17-05, selesai PO/HPP | **DITUTUP** | Tiga Native Astra lama dipertahankan:10fisik/HPP160/WIP0, sisa6belumjahit dan6belumkirim ditolak. Label BELUM_LENGKAP mengikuti sumber laundry estimasi; guard Native tidak dilemahkan. Cacat buka ulang di atas merupakan akar baru. |
| ASTRA-C17-06, arsip G01/T2 | **DITUTUP untuk G01/T2; klaim seluruh entry point lama belum lengkap** | Kedua entry point dipulihkan dan dijalankan sendiri. Masih ada21 workflow historis merah pada receipt penulis; §5 memisahkan scope guard dan arsipAE, bukan memberi PASS atas job itu. |
| ASTRA-C17-07, seluruh rantai melalui aplikasi | **DITUTUP SEBAGIAN / MASIH TERBUKA S2** | Dua rantai baru berjalan, lihat bawah. Lifecycle pool HPP absensi tetap tanpa layar; pengakuan batas oleh penulis bukan keputusan penundaan owner. |
| R2-01 / FABLE-013 / SOL-R1-001 | **DITUTUP pada kasus yang diuji** | Dua basis tanggal, koreksi majemuk, detektor, race dan exact-cents Astra PASS. Pengaman Native lama tetap diuji CP17. |
| R2-04 / D15-6 | **MASIH TERBUKA** | Posting biasa/atomik/UUID/race/browser PASS, tetapi ASTRA-R2-02 menggagalkan batas nomor. |
| R2-05 / D15-4 | **MASIH TERBUKA** | Reopen biasa dan blockers aktif PASS; transaksi yang sudah dibalik tetap memblokir menurut ASTRA-R2-01. |
| R2-09, QC/HPP pada HP | **DITUTUP untuk overflow halaman masuk yang diuji** | Semua matriks memakai `document.documentElement.scrollWidth <= window.innerWidth`, tanpa toleransi1px, sesudah lazy workspace siap dan network tenang800ms. HP390, desktop1440. |
| R2-10, wave per SKU | **DITUTUP pada kasus yang diuji** | Native/race/HTTP/browser CP17 dan oracle Astra input urutan B/A, upah53 tepat. |
| D15-5 / FABLE-011 | **DITUTUP pada kontrak cutover** | CP17 dan oracle Astra UTC/WIB/otoritas owner. Lantai belum aktif sebelum tanggal resmi diatur; tidak diam-diam mengatur hosted. |
| FABLE-005, indeks C6/ALL | **Ketersediaan indeks terkonfirmasi** |97ID unik (39ACC+36LAU+22ALL),40tautan bernama; sisanya profil. Indeks historis0b7049d9 bukan97kasus baru lulus di r2; statusFAIL/INCOMPLETE yang dirujuk tidak dihapus. |

**Lusin yang Bos minta sudah terbukti di browser desktop dan HP pada kandidat ini:** satu lusin/3ukuran→4/4/4; manual3/5/4→tulisan1lusin; manual4/5/4→1lusin1potong;2lusin→8/8/8; satu ukuran/1lusin→12PCS; simpan dan buka kembali membaca qty yang sama dari server. Mereknya tidak tercampur. Input helper sementara bukan nilai total tersimpan: DOM mencatat input helper masih2 ketika total manual menjadi1lusin; yang mengikuti manual adalah tampilan total.

Dua rantai aplikasi baru, `CP17_BROWSER_R2_07_*`, dieksekusi auditor dengan oracle penulis: (1) imporWIP→FG4→ganti merek2→tutup buku→jual2→bayar30000→buka, buku tertutup tidak berubah oleh langkah kemudian; (2) impor→BS3→resep→reworkGOOD3→nota→payroll→bayar3000. Fixture non-UI memberi rekening bank; rantai kedua juga modal3000 sesuai D14-3, dan keduanya menyiapkan bulan/seed alat. Ini bukan proses membuka rekening/modal lewat UI dan bukan semua cabang bisnis menjadi satu perjalanan.

**Koreksi terhadap laporan Astra sebelumnya:** klaim “nol overflow” lama tidak dapat dipertahankan karena pengukuran mendahului kesiapan lazy page; audit silang penulis membuktikan konflik dengan Sol. Bukti pengganti sekarang menunggu siap, merekam screenshot dan memakai rumus ketat. Screenshot QC/HPP demo HP juga dibaca visual. QC mempunyai strip langkah dengan anak yang melewati viewport, dan tabel HPP connected punya anak lebih lebar; hasil PASS adalah lebar dokumen, bukan klaim semua elemen selalu terlihat tanpa scroll internal atau semua keadaan formulir sudah diuji.

## 5. T2 dan receipt penulis: status mentah tetap utuh

T2 regression: BUSINESS179PASS+39CONTROL_PASS+12DATE_POLICY_REVIEW_REQUIRED; IMPORTS31PASS; VALUES65PASS; NEW_CASES25PASS+8COUNTEREXAMPLE+1INCOMPLETE; T2_APPROVED_ORACLE8MATCH; T2_CALENDAR_POLICY12COUNTEREXAMPLE; AO_TRIAL8PASS+4INCOMPLETE; APPROVED_ORACLE_B5PASS; T2_C0_ORACLE25PASS. Temporal AT/AU41PASS. AR174ID asli:145sequentialPASS+1INCOMPLETE+28racePASS, ditambah satu replacementPASS terpisah.

25 oracle C0 (8AS+12kalender+4AO+1adjustment) memakai keputusan D01.1–5 yang diratifikasi e83d56e6, berkas auditor historis dipin SHA-256 `7c2c19b6e722d325ba902cfd9eb1ae2f98d4e2ec27245070ab485df0af9e66a7`. Semua lulus sekarang; frozen oracle lama tetap mencetak hasil lama. AR `ACCESSORY_CONNECTED_ZERO` INCOMPLETE karena `BC_FREE_REQUIRES_POLICY`; replacement yang secara eksplisit mengharapkan penolakan lulus sesuai ERP-DEC02/M:5023B. `T2_DISPOSITION.json` mempertahankan setiap non-PASS, sumber keputusan dan replacement. Tidak mengganti status asli dengan PASS, dan tidak menganggap setiap counterexample tanggal historis sebagai cacat produk baru.

Receipt API dipaginasi sendiri: **116 run,115 workflow,94success,22failure**, seluruhnya kandidat2e9d6a46. Angka81/81 adalah kelompok utama penulis, bukan semua workflow.28log job dari22run gagal dibaca dan disimpan:

- 20 workflow historis berhenti pada source-scope/no-merge guard yang memang mengharapkan cabang lama. Beberapa menjalankan predecessor/control sebelum berhenti; hasil itu bukan penerimaan penuh kandidat sekarang.
- 1 workflow `CP6 AF Posted Child Family` masih gagal mengambil artifactAE yang kedaluwarsa(HTTP410).
- 1 run penuh `CP6 Auditor Scenario` menghasilkan166PASS (104Native+26race+9HTTP+27browser),4INCOMPLETE:duaREADINESSfinance memerlukan RPC_CP7 yang tidak dipasang stackCP6 itu, duaSALES_MANUAL_13 memakai selector lama yang dipensiunkan. Job selftest terpisah sengaja menciptakan INCOMPLETE dan tidak dihitung cacat aplikasi. Run sampel5yang lulus tidak menggantikan run penuh.

Semua22failure tetap dicatat, tidak disamarkan sebagai gangguan jaringan. Perbaikan G01/T2 terbukti; daftar37bootstrap yang disentuh penulis bukan bukti37entrypoint diterima di kandidat akhir. Sebelum mengklaim regresi seluruh arsip lengkap, perlu pemetaan penerus/kasus yang setara atau kualifikasi alat untuk bagian itu. Tidak meminta guard sejarah dilonggarkan hanya supaya hijau. Rincian langkah dan cuplikan error pertama ada di `WRITER_FAILURE_REVIEW.json.gz`.

## 6. Vonis semua checkpoint

| Checkpoint | Status akhir putaran ini | Bukti yang benar-benar tersedia |
|---|---|---|
| CP1 baseline | **LULUS DENGAN BATAS BUKTI** |7salinan sejarah kembali cocok hash/ukuran. G01 baru merekonstruksi dan memeriksa alignment constraints/views/sequences/schema/capsules terhadap snapshot tersimpan. Hasil15kategori+beda metadata70ledger pada audit lama tetap bukti historis, bukan pembacaan hosted baru. Riwayat `supabase/` tidak diubah. |
| CP2 backup lama | **BELUM LULUS PENUH; HOLD CP7C** |Laporan restore PG16/stub lama tersedia dan diterima bersyarat sebagai `REUSED_AUDITOR_LOCAL_RESTORE_REPORT`; bukan nihil bukti. Engine/image asli, definisi/owner/ACL lengkap, dan Storage round-trip belum dibuktikan Astra. Tidak meminta/menggunakan ulang kunci lama yang dilaporkan terpapar. |
| CP3/3.5 absensi–HPP–payroll | **Perbaikan backend lulus; kelengkapan UI masih terbuka** |FIN01/HPP01/overlap/rate/payroll retestPASS, dua tanggal kas dan upah tidak mendahului akrual. Lifecycle pool HPP absensi belum tersedia melalui aplikasi. |
| CP4/4.5 HPP/akses/master | **Qualified dalam cakupan; belum izin operasi penuh** |Master/rate/akses, wave upah, versi biaya, finishpreflight diuji.82EXECUTE FABLE-012 tetap gateCP7C, bukan telah dicabut. |
| CP5 stok/laundry/BS | **Perbaikan lama lulus; integrasi koreksi r2 terbuka** |STK01/RWK01/SG01–03, konservasi fisik, rework/rewash dan inverse relevan dipertahankan; ASTRA-R2-01 menghalangi pembukaan ulang setelah inverseFG/reservasi. |
| CP6 baseline/regresi/saldo awal | **LULUS BERSYARAT pada bukti yang dipetakan** |G01/T2 berjalan; C0/AR disposition eksplisit; dua rantai UI saldo awal bertambah.21entrypoint legacy dan4scenario INCOMPLETE tidak diberi PASS. |
| CP7 aplikasi dan integrasi | **TAHAN** |DuaS1baru dan sisaASTRA-C17-07S2 belum selesai. Browser render/menu dan alur yang diuji lulus tidak menyiratkan fitur lengkap atau CP7 terpasang di hosted. |

Akar lama FIN01,FIN02,STK01,RWK01,HPP01 dan SG01–03 yang sudah ditutup pada dfab13bf tetap lulus kasus retestCP17 sekarang; statusnya tidak dibuka ulang tanpa bukti baru. A2 dua kegagalan asli masih tidak diketahui penyebabnya, diterima bukan penghalang D13-10; comparator stabil lulus. Penyebab awal SOL-003/AZ tidak ditebak, mitigasi drain tetap bukti yang terbatas. Tidak membuka ulang keputusan owner D13/D14/D15.

## 7. Yang harus beres, dan yang belum saya periksa

Sebelum penerimaan kandidat: perbaiki duaS1di§3 dan retest tanpa mengubah oracle; selesaikan lifecycle UI pool HPP absensi beserta perjalanan server→HPP→laporan/koreksi, atau catat keputusan owner eksplisit atas cakupan yang ditunda. Untuk klaim regresi historis penuh, tutup pemetaan entrypoint/selector di§5; status mentah tidak boleh dihapus.

Sesudah owner membuka CP7C, gate lama tetap berlaku:backup/restore yang qualified, penanganan kunci, revoke82/exposure gate, detector data lama, pemasangan CP7 yang terkendali dan pembersihan UAT. Belum diperiksa di putaran ini: operasi hosted/Drive/deployment; restoreCP2engineasli/Storage; seluruh variasi form/role/perangkat/tanggal/volume; semua cabang transaksi dalam satu rantaiUI;82revocation aktual; akar dua kegagalan A2/AZ; pengulangan seluruh paket backup yang tidak berubah. Batas-batas ini tidak diberi label PASS.

`FINDINGS.json` adalah register mesin; `HANDOFF_OWNER.md` ringkasan≤10kalimat. Laporan dan sumber kasus dikunci bersama hash manifest; tidak ada job audit tertinggal.

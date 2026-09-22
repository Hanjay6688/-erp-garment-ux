# CP6 — koreksi fixture pembaca nota aksesori

Native35731316138 pada d81c7a70121e6c8d7602e186709219d0682b98c7/tree8baef780f173fbd9be8d9ab8f607da882fe9f737:184 kasus AP, **183 PASS /1 INCOMPLETE**. Seluruh21 kasus connected selesai kecuali fixture otorisasi pembaca; role STAFF legacy sengaja nonaktif sehingga reader menolak dengan benar. Fixture kini memakai AUDITOR_VIEW_ONLY yang aktif dan hanya izin finance.contractor_accessory.view. Tidak ada perubahan izin/kode aplikasi dalam koreksi ini.12 AO dan142 frontend PASS; semua boundary pulih. Native184/184 belum PASS. CodeQL35731316355 empat bahasa SUCCESS.

Artifact native gagal10696160988,144.403byte,11entri,SHA256c45a21bebb637547bed68e4091691948a09ad62191ad42cee7ca83b4f37abdef terverifikasi dan dipertahankan. Final Boundary35731316235/job106757298660 gagal pada Verify unchanged AI-R2 backend and bounded writer UI scope sebelum database, konsisten dengan blocker scope successor lama; artifact10695671086,479.720byte,7entri,SHA25685ba0c4657bd6311df4344a0ee642488bceee83bae132dd1387eccba26208faa. Guard tidak diubah. CP6_HOLD; production_go:false; migration_installed:false; independent_acceptance:false.

---

# CP6 — proposal form eceran aksesori terhubung

22 September 2026. **CP6_HOLD · production_go:false · migration_installed:false · independent_acceptance:false.**

Kelanjutan owner “lanjutt” dari checkpoint 212ef0d4. Halaman Nota Ambil Aksesori sebelumnya memakai seed lokal; mode tersambung sekarang memakai pembaca dan facade transaksi khusus, sementara mode demo tetap ditandai simulasi. Form menerima PCS utuh, harga eceran per buah manual atau harga master dengan konversi exact, mandor/gudang/waktu WIB dan PO opsional. Draft tidak menulis ledger; pengesahan menyimpan isi terakhir dan memposting secara atomik. Master lusin/gross tidak diubah. Jangan menebak tiga kategori gratis Afui dari nama atau seed: konfigurasi harga per mandor dan tanggal tetap sumbernya.

Facade memeriksa izin existing per aksi sebelum lookup idempotensi, menolak versi nota/harga usang, dan memanggil save/post/reverse native. Identitas request dan versi bigint dipertahankan sebagai teks; pengesahan/reversal memakai UUID tetap serta domain ACCESSORY_ISSUE dalam recovery global. Riwayat posted read-only dan pengunci payroll tetap berlaku. Dua RPC publik baru terdaftar ownership; tidak membuka akses tabel browser. Balasan yang hilang/tidak cocok tetap memerlukan reconcile dengan payload asal.

Lokal: 142/142 frontend/recovery PASS, TypeScript serta source/access/recovery ownership PASS. 106 runtime files,30 browser RPC,111 permissions,48 route/nav labels,20 sensitive actions,37 stylesheets,8 recovery domains. AP101 fungsi +AO11; predecessor AP30 +AO11;54 source pins. Native disiapkan184 AP (163 existing +21 connected accessory) dan12 AO. **Native connected accessory belum PASS pada proposal ini.** HTTP/browser nyata, migrasi permanen dan acceptance independen tetap belum selesai. Tidak ada perubahan main/hosted UAT/legacy/prod/CP7.

---

# CP6 — WIP fisik, BS bernilai, dan asal biaya sebelum cutover terverifikasi

22 September 2026. **CP6_HOLD · production_go:false · migration_installed:false · independent_acceptance:false.**

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa.
Keuangan—termasuk laporan—stok, dan HPP adalah raja.

## Bukti terbaru

| Bukti | Hasil |
| --- | --- |
| Repository / branch | Hanjay6688/-erp-garment-ux / competition/cp6-j-closure-20260911 |
| Tested commit | `8ab48bb944d55128f453a2b6c926c895aec308eb` |
| Tested tree | `808b4a477476385a3682eef5ceeba7c397397385` |
| Native gate | [35725836562 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35725836562), job 106739749025 |
| Proposal AP gabungan AO+AP | **163/163 PASS**: 136 existing +27 WIP/BS/asal biaya |
| AO biaya/eceran pada AN | **12/12 PASS** |
| Frontend/recovery | **108/108 PASS**, enam berkas uji |
| TypeScript; source/access/CSS/recovery ownership | PASS |
| CodeQL | [35725836537 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35725836537), empat bahasa |
| Static Laundry QC fullschema | [35725836516 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35725836516) |
| Artifact native | 10693529303, 139.354 byte, 11 entri ZIP |
| SHA256 artifact native | `a8cfd66648ae88d5601feb171a5e6c67efdcfa361e5e500b84a06692075c3a91` |
| Main saat diverifikasi | `557005e6674058f1e5e966b350cba05501e06182` |

CRC dan SHA256 ZIP cocok. SOURCE.json menunjuk tepat ke tested commit/tree. Seluruh 163 AP dan 12 AO PASS dengan boundary_restored:true; kedua laporan complete_boundary_restored:true. AP combined_ao_ap:true. Semua flag deployment, migrasi permanen dan acceptance independen tetap false. Proposal beserta fixture dijalankan pada database disposable, di-ROLLBACK, dan runtime dibersihkan. Ini bukti writer native serta unit/DOM, belum bukti HTTP/browser nyata atau audit global independen.

## Data awal yang sekarang dapat dibawa masuk

Keluarga ini melanjutkan cakupan ALL yang telah diizinkan. OPENING_BALANCE_ITEM menerima WIP fisik per PO, ukuran, tahap, pemegang, jumlah pcs dan nilai; SEWING wajib mandor dan LAUNDRY wajib vendor laundry. BS bernilai membutuhkan identitas produk, ukuran, PO dan pemegang/lokasi yang dikenal. Nilai nol harus dinyatakan eksplisit, pcs harus bilangan bulat positif, dan target PO harus menampung total WIP/BS. PO selesai atau dibatalkan tidak menerima saldo produksi yang belum selesai.

Total kontrol WIP fisik mencakup kuantitas; total kontrol BS mencakup nilai. Rincian dan total dicocokkan tanpa ikut membukukan baris kontrol. Campuran WIP ringkasan tanpa rincian dengan sumber fisik dalam batch yang sama ditolak. Dukungan lama untuk WIP nilai saja/BS tanpa nilai tetap ada; perlindungan overlap seluruh jalur opening lama masih menjadi gate berikutnya.

Jenis CSV baru **OPENING_COST_ORIGIN** menghubungkan penerimaan supplier yang telah digunakan sebelum cutover ke sumber WIP, BS atau barang jadi awal. Kuantitasnya adalah satuan bahan, bukan pcs celana. Persamaan wajib: jumlah penerimaan = sisa bahan awal + seluruh jumlah asal biaya terpakai. Asal biaya harus muat dalam nilai saldo tujuan; relasi ini menjelaskan nilai yang sudah ada dan tidak menambah biaya awal kedua. Penerimaan yang seluruhnya sudah terpakai dapat diimpor tanpa membuat stok bahan fiktif. Retur supplier tidak boleh mengambil kuantitas yang telah habis sebelum cutover.

Draft masih dapat diedit setelah validasi. Pengesahan memeriksa isi terakhir, termasuk perubahan nilai sumber fisik; hasil validasi lama tidak dipakai untuk membukukan isi baru. Sumber yang telah disahkan tetap immutable, dengan perubahan biaya dan pembatalan sebagai event tertaut. Seluruh kuantitas/nilai diproses exact; nilai besar tidak dikonversi menjadi JavaScript Number.

## Kelanjutan produksi dan biaya

WIP awal membuat saldo tahap produksi pada tanggal cutover, tanpa mengarang cutting, hasil jahit historis, absensi atau upah lama. Di halaman impor, owner/admin dapat memilih sumber WIP dan mencatat sebagian hasil baik setelah diperiksa, dengan produk/model/ukuran yang sesuai serta gudang barang jadi. Sisa dibaca ulang saat pengesahan; jumlah berlebih, versi sisa usang dan tanggal sebelum cutover/di masa depan ditolak. UUID yang sama tidak menggandakan hasil. Pemulihan respons hilang memakai domain INITIAL_IMPORT dan kunci pemulihan global existing.

Hasil tersebut membuat lot barang jadi PRODUCTION, mutasi stok QC_GOOD dan perpindahan tahap ke FINISHED. HPP memakai bagian nilai awal yang tepat serta biaya PO native berikutnya. Penanda accessory_cost_included menghindari penambahan aksesori yang telah termasuk nilai awal; jalur BOM existing tersedia ketika aksesori belum termasuk. Pembatalan hasil membuat event dan mutasi kebalikan tertaut, mempertahankan sumber awal dan mematuhi pengunci transaksi lanjutan/payroll. PO harus tetap terbuka; finish/cancel ditolak selama WIP/BS awal masih tersisa.

BS awal terhubung ke kasus BS native. Scrap/writeoff memindahkan bagian nilai BS dari WIP ke biaya lainnya. Rework yang menghasilkan barang baik membawa bagian nilai BS ke HPP barang jadi; sisa BS tetap mempunyai nilai. Pembatalan canonical membalik nilai melalui event tertaut. Biaya BS yang dibuang dikecualikan dari biaya PO yang dapat terserap ke barang jadi, sehingga tidak masuk HPP dua kali.

Ketika nota supplier masuk atau dikoreksi, sisa bahan menerima koreksi bagiannya dan asal biaya terpakai meneruskan koreksi ke WIP, BS, barang jadi tersedia serta COGS barang yang sudah terjual. Nilai persediaan tidak dibukukan ulang dari total penerimaan. Pembulatan mengikuti nilai sen tiap sumber, dengan selisih dokumen dikelola variance native. Tanggal ekonomi seluruh kaki jurnal mengikuti invoice; periode tertutup tetap memakai tanggal pembukuan canonical.

HPP tetap **ESTIMATED** selama sumber penerimaan terkait belum seluruhnya dicocokkan dengan nota. Nota dengan harga sama juga menyelesaikan status kepastian biaya walau nilainya tidak berubah; inverse nota mengembalikannya ke ESTIMATED. Status ini diuji untuk lot awal dan hasil produksi lanjutan.

Halaman status WIP menampilkan sumber awal, ukuran, jumlah dan pemegang; tahap diberi keterangan **saat cutover** agar tidak dianggap tahap operasional terkini. Nilai keuangan sumber tidak diekspos ke pembaca produksi. Jalur kelanjutan di halaman impor adalah pengesahan hasil baik dari saldo lama; riwayat distribusi/laundry yang belum diketahui tidak direkonstruksi. Biaya kerja baru tetap dicatat lewat transaksi domain biasa.

## Angka dan penolakan yang dibuktikan

Skenario utama menerima 12 satuan bahan @10: sisa bahan 4 bernilai 40, asal terpakai 4 dalam WIP 8 pcs bernilai 40, 2 dalam BS 2 pcs bernilai 20, dan 2 dalam FG awal 4 pcs bernilai 20. Hasil baik 4 pcs dari WIP memindahkan 20 ke FG; scrap 1 pcs BS memindahkan 10 ke biaya lainnya. Berikut tambahan saldo terhadap baseline fixture:

| Titik pemeriksaan | Bahan | WIP | FG | Biaya lainnya | COGS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Setelah impor | 40 | 60 | 20 | 0 | 0 |
| Setelah hasil baik 4 pcs dan scrap BS 1 pcs | 40 | 30 | 40 | 10 | 0 |
| Setelah harga nota menjadi 12 | 48 | 36 | 48 | 12 | 0 |

Laporan owner dan jurnal cocok pada setiap tahap; seluruh pembatalan mengembalikan nilai semula, tanpa mengubah snapshot awal. Siklus mencakup SEWING/LAUNDRY, periode terbuka/tertutup, UTC/Pacific-Kiritimati dan penerimaan sepenuhnya terpakai. Skenario terpisah membuktikan penjualan 2 pcs FG awal: nota parsial mengubah FG tersisa dan COGS menjadi 12 masing-masing; inverse nota mengembalikan keduanya ke 10.

27 kasus baru terdiri atas tiga lifecycle; 18 penolakan sumber/hasil; rework; pengesahan draft terakhir; barang terjual; dua guard retur/penutupan PO; dan nota dengan harga tetap. Penolakan memeriksa pemegang/PO/nilai hilang, pcs pecahan, ukuran/produk tidak sesuai, target PO terlalu kecil, asal biaya melampaui nilai, relasi target/penerimaan hilang, sumber duplikat, jumlah terpakai tanpa asal, total kontrol tidak cocok, output berlebih/usang dan tanggal salah. Penolakan harus terjadi tanpa perubahan bisnis, serta seluruh boundary kembali setelah setiap kasus.

Implementasi memuat 96 fungsi AP +11 AO; 30 predecessor AP +11 AO; 48 source pins. Pemeriksaan ownership mencatat 104 runtime files, 28 browser RPC, 111 permissions, 48 route/nav labels, 20 sensitive actions, 37 stylesheets dan tujuh recovery domains. Tabel riwayat baru privat, RLS dan tanpa grant langsung ke browser; tidak ada pelebaran batas RPC atau izin. Parser sumber produksi, halaman WIP dan pemulihan WIP_OUTPUT termasuk 108 pemeriksaan frontend yang lulus.

## Bukti percobaan sebelumnya

Bukti gagal disimpan bersama hasil lulus agar riwayat perbaikan dapat ditelusuri:

| Run native | Sumber | Hasil dan tindak lanjut |
| --- | --- | --- |
| [35723701641](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35723701641) | 05e18f0eafc6f6ae616146442d706e59399554b8 | 150 PASS /3 INCOMPLETE dari 153; stage_to FG tidak sah diperbaiki menjadi FINISHED. 12 AO dan 94 frontend PASS; seluruh boundary pulih. |
| [35724693999](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35724693999) | 7854f3e4bdcb7a5048533230cc054404f1106fc4 | 158 PASS /1 INCOMPLETE dari 159; fixture penjualan memakai primitive private yang EXECUTE-nya dicabut. Diganti facade canonical post_sale_v2, tanpa grant baru. 12 AO dan 108 frontend PASS; seluruh boundary pulih. |
| [35725367063](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35725367063) | 6e495c5969a6f61bbf7ce09b3d0cdd22d5419a87 | 162 AP, 12 AO dan 108 frontend PASS. Ini sebelum tambahan kasus kepastian biaya harga tetap; hasil final di atas memakai 163 AP. |

Final Boundary lama pada run [35723701737](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35723701737), [35724694064](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35724694064) dan [35725366997](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35725366997) tetap FAILURE pada langkah **Verify unchanged AI-R2 backend and bounded writer UI scope**, sebelum audit database. Harness lama belum menerima scope successor AJ→AP. Guard itu tidak dilonggarkan dan hasil focused gate tidak menggantikan penerimaan global ini.

| Artifact | Byte / entri ZIP | SHA256 |
| --- | --- | --- |
| Native gagal 10693200310 | 138.512 /11 | e37eb16f8b69fc026b5de40f373f26f8efe8c99808f73c7323ae51af233ee0ee |
| Boundary 10692239537 | 479.059 /7 | 8e028d9aef6b6796ffc2ffb6cc2a8a90233653534ea91c39382d89049f8330aa |
| Native gagal 10693116797 | 138.905 /11 | 4bf9413074bf7de8f3d3874eb217c3bda4c88251cb4216fa2f757010fdbf7acc |
| Boundary 10693006906 | 478.305 /7 | 31bb5bb07bf44397c335b86a20df80e4b36ff64f621d92da5b243d296779b5e9 |
| Native lulus 162 kasus 10692573121 | 138.985 /11 | 55e5ff7cc242c9c6a342184e9f5afec7b087a138df9e0926623be2150fd686c8 |
| Boundary 10693342579 | 478.611 /7 | 56a8057be77491b00a92284f966ce902dffe3a1f296720031ce36717b7c05885 |

Seluruh ZIP di tabel dan artifact final diperiksa CRC serta SHA256. Bukti checkpoint terdahulu tetap berlaku menurut scope dan sumber masing-masing.

## Status dan pekerjaan berikutnya

Keluarga WIP fisik/BS bernilai/asal biaya terpakai selesai pada tingkat writer native dan frontend/DOM. **CP6 keseluruhan masih HOLD.** Belum ada migrasi permanen, pembuktian HTTP/browser nyata keluarga ini, concurrency seluruh transaksi bisnis, perlindungan global terhadap jalur opening lama, atau acceptance independen. Matriks historis global belum dieksekusi ulang. Main, PR24/25, hosted UAT, legacy/prod dan CP7 tidak diubah.

Urutan berikutnya yang sudah diizinkan: form eceran aksesori terhubung; paket migrasi AO/AP dan rollback maintenance; HTTP/browser/concurrency serta perlindungan opening lama; penerimaan independen CP6. **7 PCS adalah aksesori**, dengan harga eceran manual dan master lusin/gross tetap. Kain kantong universal tetap memakai stok gudang dan opsi pembagian per periode atas hasil SELESAI_DIJAHIT yang sah, termasuk Afui; tidak memerlukan catatan pengambilan bebas atau saldo per mandor. WIP awal tidak mengarang hasil jahit historis untuk denominator tersebut.

Mandor Epi, Selo, Afat dan Afui tetap mengikuti kontrak yang sudah diputuskan. Afui khusus tanpa absensi, komisi lebih tinggi, tiga kategori aksesori gratis, dan tetap ikut pembagian kain kantong. Satu writer pada branch yang sama, fast-forward saja; checkpoint ini melanjutkan persetujuan owner tanpa meminta ulang cakupan.


---

# Riwayat checkpoint sebelumnya

# CP6 — pembagian kain kantong per periode terverifikasi

22 September 2026. **CP6_HOLD · production_go:false · migration_installed:false · independent_acceptance:false.**

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa.
Keuangan—termasuk laporan—stok, dan HPP adalah raja.

## Bukti terbaru

| Bukti | Hasil |
| --- | --- |
| Repository / branch | Hanjay6688/-erp-garment-ux / competition/cp6-j-closure-20260911 |
| Tested commit | `c40332c8ec594a75c04c0c4994d671580c897456` |
| Tested tree | `aab9f0f80ab839a0e49506a70a1300fb8a47a1e3` |
| Native gate | [35715449337 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35715449337), job106705744294 |
| Proposal AP gabungan AO+AP | **136/136 PASS**:103 impor +17 stok kain kantong +16 pembagian periode |
| AO biaya/eceran pada AN | **12/12 PASS** |
| Frontend/recovery | **84/84 PASS**:72 existing +12 connected DOM kain kantong |
| TypeScript; source/access/CSS/recovery ownership | PASS |
| CodeQL | [35715449278 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35715449278), empat bahasa |
| Artifact native |10688624847,122.802byte,11entri ZIP |
| SHA256 artifact native | `6d8be12e48380ede69afd3fe669e6868ea66bf38980225509440d1bcbf3924f7` |
| Main saat diverifikasi | `557005e6674058f1e5e966b350cba05501e06182` |

CRC dan SHA256 ZIP cocok. SOURCE.json menunjuk tepat ke tested commit/tree.136 AP dan12 AO seluruhnya PASS dengan boundary_restored:true; kedua laporan complete_boundary_restored:true. AP combined_ao_ap:true. Seluruh flag deployment/migrasi/acceptance independen tetap false. Database disposable memakai Supabase CLI2.116.0/PostgreSQL17.6.1.165 dan katalog AC→AN yang dipin; proposal beserta fixture di-ROLLBACK dan runtime dibersihkan.

## Keputusan owner dan cara pakai

Owner mengizinkan pembagian per periode melalui “ya gas lah tanggung ye”. Ini melanjutkan keputusan pengurangan stok kain kantong universal. Pengambilan bebas, pemotongan bebas dan sisa per mandor tetap tidak perlu dicatat. Saldo yang diketahui adalah kain di gudang; nilai keluar menjadi dasar alokasi bersama, tanpa mengklaim konsumsi aktual per celana atau on-hand mandor.

Menu Gudang → Kain kantong tetap mendukung jumlah keluar atau hitung sisa roll. Pengurangan stok terlebih dahulu mencatat biaya periode. Opsi **Bagi ke HPP per periode** menambah alur: pilih tanggal awal/akhir, lihat jumlah biaya dan hasil jahit, lalu sahkan. Membuka pratinjau dan mengubah formulir belum menulis ledger. Alokasi memerlukan hak warehouse.stock.adjust dan finance.hpp.manage pada owner/admin.

Denominator adalah seluruh pcs **SELESAI_DIJAHIT** yang sah pada periode, termasuk **Afui**. Kebijakan mandor khusus tanpa absensi tidak mengecualikannya dari kain kantong. Biaya dibagi per pcs hasil jahit; bagian yang belum menjadi FG tinggal di WIP. Pemakaian stok tanpa pengesahan alokasi tetap tersedia dan tidak menambah HPP produk.

Pengesahan mengalihkan biaya periode ke WIP per PO, lalu perhitungan HPP native meneruskannya ke barang jadi dan barang terjual. Tidak ada pengurangan stok kedua atau biaya ganda. Koreksi harga nota memperbarui biaya sumber, alokasi, HPP, jurnal dan laporan. Tanggal ekonomi seluruh jurnal koreksi mengikuti invoice; periode tertutup memakai tanggal pembukuan canonical. Pembatalan alokasi membalik perpindahan biaya dan menghitung ulang HPP, tanpa mutasi stok.

## Hasil transaksi yang dibuktikan

Empat lifecycle mencakup mandor biasa dan mandor khusus, periode terbuka/tertutup, UTC/Pacific-Kiritimati.10pcs selesai dijahit;5pcs telah menjadi FG, terdiri atas3pcs masih tersedia dan2pcs terjual.5pcs lain masih WIP. Berikut bagian biaya kain kantong yang berpindah, terpisah dari biaya produksi yang sudah ada:

| Nilai kain keluar | Tambahan WIP | Tambahan FG tersedia | Tambahan COGS/HPP penjualan |
| --- | ---: | ---: | ---: |
|11,25 sebelum koreksi nota |5,62 |3,38 |2,25 |
|15,00 setelah koreksi nota |7,50 |4,50 |3,00 |

Saldo kain tetap15 setelah pengeluaran awal5 dari20. Replay UUID tidak menggandakan transaksi. Laporan owner cocok dengan ledger, termasuk material inventory, WIP, FG, COGS, biaya lainnya dan neraca seimbang. Cancel alokasi memulihkan HPP; setelah nota dibalik, semua akun persis kembali ke baseline. Header/snapshot sumber tidak ditulis ulang. Alokasi baru pada periode yang sama dapat dibuat setelah yang lama dibatalkan.

Kasus campuran mandor biasa dan khusus membagi11,25 pada20pcs menjadi5,63 dan5,62 per kelompok10pcs; seluruh sen habis terbagi. Urutan deterministik dan selisih pembulatan kumulatif mencegah kehilangan/kelebihan biaya. Cancel memulihkan semua akun.

Delapan penolakan mencakup sumber biaya berubah sejak preview, tanggal masa depan, rentang terbalik/terlalu panjang, alasan kosong, periode tumpang tindih, tanpa hasil jahit dan periode kosong. Guard menolak inverse sumber yang sedang dialokasikan, pengeluaran baru dalam periode aktif, koreksi denominator hasil jahit, inverse jurnal tanpa periode, dan perubahan langsung histori immutable. Penolakan guard wajib memuat pesan bisnis yang tepat; ACL denial tidak dihitung sebagai bukti guard. Actor yang dinonaktifkan tidak dapat preview atau replay write.

Uji dua koneksi membuktikan mutex menolak konflik secara atomik dan dapat dicoba setelah lock dilepas. Ini bukti mutex saja; seluruh transaksi bisnis serentak belum diuji.12 DOM cases mencakup exact decimal/versi besar, draft tanpa efek, stock stale, preview tanpa write, tanggal preview berubah/tidak cocok, overlap/output kosong, permission, alasan cancel, serta respons hilang dan remount dengan UUID/payload yang sama.

## Batas implementasi

Manifest menyimpan sumber pengeluaran, biaya saat disahkan, event hasil jahit, mandor, PO, kelompok cutting dan posisi alokasi. Riwayat pool/source/destination/event immutable, privat dan RLS. Status aktif dibaca dari event pembatalan, tanpa mengubah histori lama. Revision dibaca ulang saat pengesahan di bawah mutex; snapshot diperiksa konsisten dalam UTC.

Periode aktif tidak boleh saling tumpang tindih. Jika sumber pengeluaran atau hasil jahit yang memengaruhi denominator/urutan perlu diubah, batalkan alokasi terkait lalu hitung ulang. Koreksi harga nota memakai recost tertaut dan tidak memerlukan pengurangan stok baru. Mutex memakai try-lock agar konflik urutan lock dengan penulis biaya/produksi gagal atomik, bukan deadlock. Global recovery memakai domain POCKET_FABRIC dan UUID existing; izin diperiksa sebelum cache idempotensi.

79 fungsi AP +11 AO;25 predecessor AP +11 AO.40source pins;103 runtime files,28browser RPC,111permissions,48route/nav labels,20sensitive actions,37stylesheet,7recovery domains. Native rebuild_po_hpp dipin dari predecessor dan ditambah komponen OTHER/POCKET_PERIOD_ALLOCATION. Kebijakan absensi, harga eceran aksesori dan model potongan kain utama tidak diganti.

## Bukti gagal yang dipertahankan

Native [35714697164 FAILURE](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35714697164), job106703320497, commit5d5242d422628ef9aee3b922b36260730b98a8e0:136 AP berjalan,132PASS/4INCOMPLETE;12AO dan84frontend PASS; seluruh boundary pulih. Satu pemeriksaan snapshot bergantung zona sesi; diperbaiki dengan UTC. Tiga kasus fixture mandor khusus memanggil primitive private yang EXECUTE-nya dicabut; diganti ke facade publik existing sebagai actor biasa. Tidak ada pelebaran ACL. Artifact10688353421,123.792byte,11entri,SHA256e89aff4b4a37c62281a74795d61d23a3227b5eb28fbb5a15f3ebc31e484a4b36.

[Final Boundary35714697227 FAILURE](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35714697227), job106703317931: harness lama menolak scope successor AJ→AP pada langkah Verify unchanged AI-R2 backend and bounded writer UI scope, sebelum audit database berjalan. Guard tidak dilonggarkan; ini tetap blocker global. Artifact10688343222,478.406byte,7entri,SHA256f82af0b6734494671faccfc3f540704f54f5b552e205f41b571761f3022ff2ba. Bukti gagal stok-only dari checkpoint sebelumnya tetap dipertahankan dalam histori dokumen.

## Status dan kelanjutan

Keluarga pembagian kain kantong selesai pada tingkat writer native/DOM. **CP6 keseluruhan masih HOLD.** Nama workflow “Final Boundary” bukan pernyataan ERP sudah final. Belum ada migrasi permanen, HTTP/browser nyata untuk keluarga ini, concurrency seluruh transaksi bisnis, ataupun acceptance independen. Main, PR24/25, hosted UAT, legacy/prod dan CP7 tidak diubah. Matriks historis global tidak dieksekusi ulang.

Kelanjutan ALL yang sudah diizinkan: WIP fisik per ukuran/tahap/pemegang dan nilai BS beserta asal biaya penerimaan terpakai sebelum cutover; form eceran aksesori terhubung; paket migrasi AO/AP dan rollback maintenance; HTTP/browser/concurrency, perlindungan opening lama, kemudian acceptance independen. Satu writer, fast-forward saja, tanpa persetujuan scope berulang.

Aturan sebelumnya tetap: draft impor dapat diedit dan pengesahan memakai isi terakhir; total kontrol tidak dibukukan; replay tidak menggandakan transaksi. **7 PCS adalah aksesori** dengan harga eceran manual, master lusin/gross tetap. Mandor Epi, Selo, Afat, Afui; Afui khusus tanpa absensi, komisi lebih tinggi dan tiga kategori aksesori gratis. Keputusan kain kantong per periode terbaru di atas menggantikan keterangan lama “opsi mendatang/belum dibuat”; bagian lama disimpan sebagai histori.


---

# Riwayat checkpoint dan proposal sebelumnya

# CP6 — koreksi pemeriksaan zona waktu dan fixture mandor khusus

Native35714697164 pada commit5d5242d422628ef9aee3b922b36260730b98a8e0/treeb19efae6832443c81d80c3d616adc51a56120517 menjalankan136 AP: **132 PASS /4 INCOMPLETE**, seluruh boundary kembali;12 AO dan84 frontend PASS. Siklus mandor biasa/UTC selesai sampai recost, cancel, invoice inverse dan realokasi. Mutex dua koneksi,8 penolakan periode, guard sumber/denominator dan authorization PASS.

Siklus Pacific/Kiritimati menunjukkan false positive pada checker snapshot: manifest memakai UTC, sedangkan to_jsonb saat pemeriksaan mengikuti zona sesi. Checker kini secara eksplisit memakai UTC. Tiga kasus mandor khusus terhenti di fixture policy karena memakai primitive private yang EXECUTE-nya dicabut; fixture diperbaiki ke public.erp_set_contractor_hpp_policy_v1 sebagai actor biasa tanpa grant tambahan. Pemeriksaan periode juga diperluas ke laporan owner serta tanggal seluruh jurnal recost invoice, karena keduanya merupakan kontrak fitur.

Artifact gagal10688353421,123.792byte,11entri,SHA256e89aff4b4a37c62281a74795d61d23a3227b5eb28fbb5a15f3ebc31e484a4b36 dipertahankan. CodeQL35714697017 SUCCESS empat bahasa. Final Boundary lama35714697227 kembali menolak scope AJ→AP pada Verify unchanged AI-R2 backend and bounded writer UI scope, sebelum database audit; guard tidak diubah. Artifact10688343222,478.406byte,7entri,SHA256f82af0b6734494671faccfc3f540704f54f5b552e205f41b571761f3022ff2ba dipertahankan. **136/136 native belum PASS; CP6_HOLD, production_go:false, migration_installed:false, independent_acceptance:false.**

---

# CP6 — proposal pembagian kain kantong per periode

22 September 2026. **CP6_HOLD · production_go:false · migration_installed:false · independent_acceptance:false.**

Owner mengizinkan: “ya gas lah tanggung ye”. Pembagian biaya per periode sekarang menjadi scope aktif. Dasarnya seluruh celana SELESAI_DIJAHIT pada periode, termasuk Afui; pengecualian absensi mandor khusus tidak mengecualikan kain kantong. Ini alokasi nilai pengeluaran gudang, bukan pengukuran konsumsi aktual atau saldo setiap mandor. Alur stok tetap dapat dipakai tanpa alokasi HPP.

Pratinjau memperlihatkan periode, biaya, jumlah hasil jahit dan biaya per pcs tanpa menulis ledger. Pengesahan terpisah memerlukan warehouse.stock.adjust serta finance.hpp.manage. Manifest sumber biaya/output dan revision diperiksa ulang di bawah mutex; histori sumber/destinasi/event immutable. Pembulatan memakai selisih total kumulatif sehingga semua sen terbagi. Periode aktif tidak boleh bertumpang tindih.

Pengesahan mengalihkan OTHER_EXPENSE ke WIP per PO, kemudian rebuild HPP dan GL native mengikuti barang belum jadi, FG dan barang terjual. Koreksi nota memicu recost dengan tanggal ekonomi AO serta pembukuan canonical; biaya tidak digandakan dan stok tidak bergerak lagi. Pembatalan tertaut mengembalikan biaya periode dan HPP, mempertahankan sumber asli. Penambahan pengeluaran di periode aktif, inverse sumber, serta perubahan hasil jahit yang memengaruhi denominator/urutan memerlukan pembatalan alokasi dahulu. Generic reversal jurnal alokasi ditolak.

Mutex transaksi memakai try-lock agar konflik dengan penulis invoice/produksi gagal atomik dan dapat dicoba lagi tanpa membentuk deadlock urutan lock. Uji konflik dua koneksi mencakup mutex, belum seluruh transaksi bisnis serentak. Global concurrency dan HTTP/browser nyata tetap gate berikutnya.

Lokal: **84/84 frontend/recovery PASS**, TypeScript dan source/access/CSS/recovery ownership PASS. 103 runtime files,28 browser RPC,111 permissions,48 routes/nav labels,20 sensitive actions,37 stylesheet,7 recovery domains. AP berisi79 fungsi dan25 predecessor; AO11 fungsi/predecessor unchanged.40 source pins. Native direncanakan **136 AP** (120 existing +16 periode termasuk mutex, campuran mandor/pembulatan, recost, cancel, tanggal tertutup dan penolakan) +12 AO. **Native periode belum PASS pada proposal ini.** Semua perubahan adalah proposal pada runtime disposable; migrasi permanen dan penerimaan independen belum selesai. Bukti checkpoint stok-only sebelumnya disimpan di bawah sebagai riwayat.

---

# CP6 — kain kantong universal: stok gudang tanpa HPP produk

22 September 2026. **CP6_HOLD · production_go:false · migration_installed:false · independent_acceptance:false.**

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa.
Keuangan—termasuk laporan—stok, dan HPP adalah raja.

## Bukti yang terverifikasi

| Bukti | Hasil |
| --- | --- |
| Repository / branch | `Hanjay6688/-erp-garment-ux` / `competition/cp6-j-closure-20260911` |
| Tested commit | `d5dc352914c4dce12b45891b4e083fdeb2a28da9` |
| Tested tree | `7b652a20232adb50cb6453ed09e1a8bf28354902` |
| Native gate | [35709929688 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35709929688), job `106687787002` |
| Proposal AP gabungan AO+AP | **120/120 PASS**:103 impor existing +17 kain kantong |
| AO biaya/eceran pada AN | **12/12 PASS** |
| Frontend/recovery | **78/78 PASS**:72 existing +6 connected DOM kain kantong |
| TypeScript; source/access/CSS/recovery ownership | PASS |
| CodeQL | [35709929851 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35709929851), empat bahasa |
| Artifact native | `10686835261`,112.667byte,11entri ZIP |
| SHA256 artifact native | `535508f819aef6e5cbf76f1411a825c89f83d7ad885d9a78e5af9a7bfe6c6af7` |
| Main saat diverifikasi | `557005e6674058f1e5e966b350cba05501e06182` |

Hash dan CRC ZIP cocok; SOURCE.json terikat tepat ke tested commit/tree. Seluruh120 AP dan12 AO mencatat PASS dengan `boundary_restored:true`; kedua laporan `complete_boundary_restored:true`. AP mencatat `combined_ao_ap:true`. Seluruh status deployment, migration dan independent acceptance tetap false. Runtime disposable AC→AN memakai katalog asal yang dipin, Supabase CLI2.116.0/PostgreSQL17.6.1.165; proposal/fixture di-ROLLBACK dan database sementara dibersihkan. Uji ini belum mencakup HTTP/browser nyata atau concurrency antarsesi.

Empat siklus mencakup cara jumlah keluar/hitung sisa pada UTC-periode terbuka dan Pacific/Kiritimati-periode tertutup. Saldo20 berkurang5 menjadi15; biaya11,25 berubah menjadi15,00 setelah harga nota berubah2,25→3,00. WIP/FG/COGS tidak berubah. Pembatalan pocket memulihkan stok20 dan biaya0; setelah nota dibalik, seluruh akun kembali tepat ke sebelum siklus. Replay UUID tidak menambah transaksi.

Sebelas skenario penolakan memeriksa revision usang, jumlah berlebih/negatif/nol, presisi, numeric JSON, tanggal masa depan/sebelum penerimaan, hitung sisa sebelum pergerakan, lokasi salah, dan bahan yang belum didaftarkan. Dua skenario lain membuktikan sisa0, riwayat tetap, versi pembatalan usang, penolakan inverse tanpa sumber, serta actor yang dinonaktifkan tidak dapat membaca atau replay. Enam DOM cases memeriksa form tanpa efek sebelum disahkan, jumlah exact, respons hilang/remount, refresh stale, alasan/versi pembatalan, izin dan data malformed.

## Keputusan owner dan perilaku

Kain kantong universal dipotong dan diambil bebas; pengambilan per orang serta sisa di setiap mandor belum dicatat. Owner meminta tahap ringan untuk mengurangi stok saja, tanpa HPP celana. Pembagian biaya ke jumlah hasil produksi per periode, mirip biaya absensi, merupakan opsi mendatang atas permintaan owner. Keputusan ini sudah menjadi batas implementasi; tidak perlu meminta ulang persetujuan scope.

Menu **Gudang → Kain kantong** tersedia untuk owner/admin dengan hak penyesuaian stok. Pilih master kain khusus, roll dan gudang; kemudian isi **jumlah keluar** atau **sisa roll yang masih terlihat**. Sisa 0 mengeluarkan seluruh saldo roll. Mandor, model, ukuran dan hasil potongan tidak diwajibkan. Form dapat disiapkan dan diubah sebelum disahkan; belum ada mutasi stok selama pengisian. Pengesahan membuat dan memposting satu adjustment native secara atomik.

Saldo yang dicatat hanya stok roll di gudang terukur. Jumlah keluar tidak mengklaim konsumsi aktual atau saldo bahan pada mandor. Untuk menjaga nilai persediaan dan laporan tetap cocok, biaya pengeluaran masuk **OTHER_EXPENSE / biaya periode**, tanpa WIP, barang jadi, COGS/HPP produk, ataupun piutang mandor. HPP per celana tidak bertambah. Penerimaan roll tetap mengikuti alur pembelian/penerimaan yang ada.

Riwayat sumber menyimpan material, roll, gudang, tanggal, metode/input pencatatan, stok sebelum, jumlah keluar, dan kebijakan PERIOD_EXPENSE. Catatan yang disahkan tetap immutable. Pembatalan tertaut mengembalikan stok dan membalik biaya bersama. Perubahan harga nota mengikuti revaluation native dan tanggal kebijakan AO; periode tertutup memakai tanggal pembukuan canonical tanpa mengubah tanggal ekonomi sumber.

Pembagian per periode **belum dibuat atau diaktifkan**. Riwayat disiapkan sebagai dasar pengembangan nanti, dengan ketentuan tidak membebankan dua kali biaya yang sudah diakui. Basis periode/output, sisa produksi jika diperlukan, serta aturan periode tertutup harus disepakati saat fitur itu diminta. Tidak ada perhitungan saldo mandor yang dibuat-buat.

## Batas teknis yang dijaga

Dua RPC publik memakai autentikasi owner/admin dan izin existing; tiga tabel pendukung privat memakai RLS dan tidak memberi DML langsung ke authenticated/service_role. Permission diperiksa sebelum respons idempotensi dapat dipakai ulang. Tidak ada pelebaran ACL predecessor untuk mengatasi kegagalan tes.

POCKET_FABRIC menjadi domain ketujuh pada UUID recovery dan global writer lock existing. Respons hilang menggunakan UUID dan payload yang sama. Snapshot pilihan roll tidak diam-diam diganti ketika memuat ulang; perubahan stok/harga mengharuskan pemeriksaan ulang. Server mengunci material dan roll, memeriksa revision, saldo, tanggal dan angka teks dengan maksimal enam desimal. Sisa nol didukung; input negatif, pengurangan nol/berlebih, numeric JSON, presisi berlebih, serta hitung sisa yang mundur melewati pergerakan berikutnya ditolak.

Master kain kantong yang didaftarkan tidak boleh sudah terkait potongan ukuran. Guard native menolak menghubungkannya ke cutting_group_rolls, dan detector memeriksa batas itu. Pembatalan generic terhadap stok/jurnal pocket ditolak; gunakan pembatalan pada dokumen asal. Guard tersebut diuji dari primitive privat dengan fixture authority dan pesan penolakan bisnis yang persis, agar kegagalan permission tidak disalahartikan sebagai bukti penjagaan sumber.

Implementasi menambah 7 fungsi pada proposal AP, menjadi 63 AP +11 AO dengan 24 predecessor AP +11 AO. Source pin berjumlah37. Ownership:103 runtime files,27 browser RPC,111 permissions,48 route/nav labels,20 sensitive actions,37 stylesheet. Tidak ada migration permanen baru pada checkpoint ini.

## Kegagalan yang tetap dipertahankan

1. Native [35708050129 FAILURE](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35708050129), job106681644849, commit `b3e9e4245df0cb5dfc398de395c11e2a8d1bf621`: pemasangan checker gagal karena jumlah kolom UNION berbeda. **0 kasus AP** berjalan;12AO dan78frontend PASS. Return checker diperbaiki menjadi empat kolom. Kamus audit REGISTER juga disesuaikan ke INSERT. Artifact10685621506,32.538byte,10entri,SHA256 `1c9c11b8d68d6ca634e88b2ece0eae75e5dd9bb0916c45dab0ab7ecfb9f2d374`.
2. Native [35709090018 FAILURE](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35709090018), job106685034682, commit `b0579c61825a2d5202339f78de67118ae4dbbde9`:120 kasus dijalankan,116PASS/4INCOMPLETE. Empat siklus pocket mencapai pembatalan pocket, lalu tes gagal memanggil primitive private pembatalan invoice yang EXECUTE-nya memang dicabut. Skrip diperbaiki ke API v2 beserta versi hasil post; dua tes generic inverse diperketat untuk memeriksa pesan bisnis, bukan permission denial.12AO dan78frontend PASS; seluruh boundary dipulihkan. Artifact10685023976,113.228byte,11entri,SHA256 `94ae759f7632a61270f8c1221ef71fb7d746ab44c9a0c1b48c30fa450ce6c2f7`.
3. [Final Boundary 35708050014 FAILURE](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35708050014), job106681643767: harness lama menolak scope successor AJ→AP pada langkah Verify unchanged AI-R2 backend and bounded writer UI scope; database audit tersebut belum berjalan. Guard tidak dilonggarkan dan kegagalan tetap terbuka. Artifact10684997354,478.169byte,7entri,SHA256 `1099e7a6b956bb7bc940fff27e434fb7fe8a28e325a8663441c94f987c000256`.

## Status CP6 dan kelanjutan

Ini checkpoint satu keluarga fitur pada branch writer tunggal `competition/cp6-j-closure-20260911`, bukan penutupan CP6 atau deployment. Nama workflow “Final Boundary” tidak berarti seluruh ERP selesai diaudit. Main, PR24/25, hosted UAT, legacy/prod database, serta CP7 tidak diubah. Matriks global historis tidak dijalankan ulang.

Sesudah keluarga kain kantong, cakupan ALL tetap berlanjut: WIP fisik per ukuran/tahap/pemegang dan nilai BS beserta asal biaya penerimaan yang terpakai sebelum cutover; form eceran aksesori terhubung; paket migrasi AO/AP serta rollback maintenance; pengujian HTTP/browser/concurrency dan perlindungan jalur opening lama; lalu acceptance independen. Bukti writer disposable/DOM tidak menggantikan gate tersebut.

Keputusan sebelumnya tetap: draft impor dapat diedit dan pengesahan membaca isi terakhir di bawah lock; total kontrol tidak dibukukan; replay tidak menggandakan transaksi; tanggal invoice menentukan koreksi biaya pada periode terbuka, periode tertutup mengikuti jalur canonical. **7 PCS adalah aksesori dengan harga eceran manual**; master lusin/gross tetap. Mandor Epi, Selo, Afat, Afui; Afui khusus tanpa absensi, komisi lebih tinggi, tiga kategori aksesori gratis. Satu writer, fast-forward saja, lanjut sesuai scope yang telah disetujui tanpa konfirmasi berulang.


---

# Riwayat proposal sebelum hasil akhir kain kantong

# CP6 kain kantong — koreksi jalur uji pembatalan nota

Native [35709090018 FAILURE](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35709090018), commit `b0579c61825a2d5202339f78de67118ae4dbbde9`, menjalankan 120 kasus:116 PASS dan4 lifecycle INCOMPLETE. Empat siklus telah melewati pengurangan, recost, serta pembatalan kain kantong; gagal pada pembatalan invoice terakhir karena skrip memakai primitive private yang EXECUTE-nya memang dicabut. Skrip diperbaiki memakai `reverse_material_supplier_invoice_v2` beserta versi dokumen hasil post. Tidak ada ACL aplikasi yang dilonggarkan.

Dua penolakan generic inverse juga diperketat: fixture authority memanggil primitive privat dan wajib menerima pesan penolakan bisnis kain kantong yang persis, sehingga penolakan permission tidak lagi dihitung sebagai bukti guard baru. 103 kasus lama,13 kasus pocket lain,12AO dan78frontend PASS pada run gagal; pemulihan seluruh boundary tetap true. CodeQL35709090031 SUCCESS. Artifact10685023976,113.228byte,11entri,SHA25694ae759f7632a61270f8c1221ef71fb7d746ab44c9a0c1b48c30fa450ce6c2f7 dipertahankan. **120/120 belum PASS sampai gate berikutnya; CP6_HOLD tetap.**

---

# CP6 kain kantong — percobaan database pertama dan koreksi kontrak

Native35708050129 pada b3e9e4245df0cb5dfc398de395c11e2a8d1bf621 gagal ketika memasang proposal: checker baru mengembalikan dua kolom, sedangkan run_v267 memerlukan empat kolom (nama,severity,jumlah,details). **0 kasus AP berjalan.** 12 AO dan78 frontend/recovery PASS. Diperbaiki format empat kolom serta action log REGISTER memakai INSERT sesuai kamus audit native. Kegagalan tidak dihapus: artifact10685621506,32.538byte,SHA2561c9c11b8d68d6ca634e88b2ece0eae75e5dd9bb0916c45dab0ab7ecfb9f2d374. Native120AP belum PASS sampai gate berikut membuktikannya; CP6_HOLD tetap.

---

# CP6 — proposal pengurangan stok kain kantong tanpa HPP produk

22 September 2026. CP6_HOLD; production_go:false; migration_installed:false; independent_acceptance:false.

Keputusan owner: kain kantong universal dipotong dan diambil bebas; pengambilan per orang dan sisa di mandor tidak diketahui. Tahap sekarang hanya mengurangi stok roll gudang. Mandor, model, ukuran, hasil potongan, serta alokasi ke HPP produk tidak diwajibkan. Pemisahan biaya ke jumlah hasil produksi per periode merupakan opsi mendatang atas permintaan owner; belum diaktifkan dan tidak diam-diam mengubah transaksi lama.

Menu Gudang → Kain kantong: owner/admin dengan hak warehouse.stock.adjust mendaftarkan master kain khusus, memilih roll/gudang, lalu mengisi jumlah keluar atau sisa roll yang masih terlihat. Sisa nol diperbolehkan. Form belum mengubah stok sampai disahkan. Pengesahan membuat dan memposting satu material adjustment native INTERNAL_FACTORY_USE secara atomik. Nilai persediaan berpindah ke biaya periode OTHER_EXPENSE, tanpa WIP/FG/COGS atau piutang mandor. Jumlah keluar berarti keluar dari stok gudang terukur; bukan klaim konsumsi aktual ataupun sisa bahan pada mandor.

Riwayat privat immutable menyimpan asal material/roll/gudang, tanggal dokumen native, cara/input pencatatan, stok sebelumnya, jumlah keluar dan kebijakan PERIOD_EXPENSE. Koreksi harga/invoice tetap memakai revaluation native dengan tanggal kebijakan AO. Pembatalan sumber mengembalikan stok dan biaya bersama; generic journal/movement reversal tanpa sumber diblokir. Kain yang didaftarkan tidak boleh menjadi hasil potongan ukuran; native cutting guard dan detector menjaga batasnya. Future allocation harus menghindari pembebanan ganda biaya yang sudah dicatat, memilih periode/output basis yang disepakati saat fitur diminta, dan mempertahankan history/snapshot lama.

UUID recovery memakai domain ketujuh POCKET_FABRIC dan global writer lock existing. Stock revision disimpan bersama pilihan roll; muat ulang tidak otomatis mengganti dasar input yang sedang disiapkan. Server mengunci material dan roll, memeriksa saldo/revision/tanggal/raw decimal, serta memakai native stock writer. Tidak ada pemakaian negatif, saldo negatif, pembulatan input diam-diam, atau backdated remaining count yang melewati pergerakan berikutnya.

Verifikasi lokal: 78/78 frontend/recovery PASS (72 sebelumnya +6 form kain kantong); TypeScript, source/access/CSS/recovery ownership PASS. 103 runtime files,27 browser RPC,111 permissions,48 routes/nav labels,20 sensitive actions,37 stylesheets. Komposisi 63 fungsi AP +11 AO,24 predecessor AP +11 AO. Native baru:17 kasus yang belum dijalankan pada commit proposal ini; rencana gabungan120 AP +12 AO. Jangan menyebut native PASS sebelum artifact membuktikannya. Semua perubahan masih proposal rolled-back pada runtime disposable; hosted database dan main tidak disentuh.

---

# Checkpoint sebelum kain kantong

# CP6 — uang muka supplier, pelanggan, dan vendor terverifikasi

22 September 2026. **CP6_HOLD · production_go:false · migration_installed:false · independent_acceptance:false.**

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa.
Keuangan—termasuk laporan—stok, dan HPP adalah raja.

Permintaan owner “lanjut” diteruskan dari checkpoint kasbon `4ce534cf43f2327c73282a4cabf8cc1e34041fc4`. Keluarga uang muka saldo awal sekarang terhubung dari template impor, validasi, pengesahan, pemakaian ke tagihan, pengembalian, koreksi, sampai reversal. Seluruh perubahan tetap pada branch writer tunggal; cakupan ALL sudah disetujui dan tidak memerlukan konfirmasi ulang.

## Identitas bukti

| Bukti | Hasil |
| --- | --- |
| Repository / branch | `Hanjay6688/-erp-garment-ux` / `competition/cp6-j-closure-20260911` |
| Tested commit | `5cb0edd840a06e91120690cad20ff415ace45e88` |
| Tested tree | `1e9d4caa86dbc89ac3418ed49f7b36818bc4084c` |
| Native gate | [35703453198 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35703453198), job `106666645850` |
| Impor AP pada proposal gabungan AO+AP | **103/103 PASS**: 72 existing + 31 uang muka |
| AO biaya/eceran tambahan pada AN | **12/12 PASS** |
| Frontend/recovery | **72/72 PASS**: 31 parser/template, 13 connected DOM, 28 recovery |
| TypeScript dan ownership | PASS: source, access, CSS, shared recovery |
| CodeQL | [35703453203 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35703453203) |
| Artifact native | `10682928523`, 108.562 byte, 11 entri ZIP |
| SHA256 artifact native | `89a852b1d88edbb3249374179630f772cfda4e051c8b54ddb319f8496ec8fead` |
| Main saat diverifikasi | `557005e6674058f1e5e966b350cba05501e06182` |

Hash dan CRC ZIP cocok. SOURCE.json menunjuk tepat ke commit/tree di atas. NATIVE_TRIAL.json mencatat `combined_ao_ap:true`, seluruh 103 kasus PASS dan setiap `boundary_restored:true`. AO_TRIAL.json mencatat 12 kasus PASS dengan pemulihan setiap kasus. Kedua laporan menunjukkan `complete_boundary_restored:true`, serta deployment, migration dan independent acceptance tetap false. Runtime disposable AC→AN memakai katalog asal yang dipin, Supabase CLI 2.116.0 / PostgreSQL 17.6.1.165. Proposal serta fixture di-ROLLBACK, kemudian database disposable dibersihkan. Matriks historis global tidak dijalankan ulang.

## Perilaku yang dibuktikan

Template ke-19, `OPENING_ADVANCE`, menyimpan jenis/kode pihak, akun khusus uang muka, nomor dan tanggal dokumen sumber, nominal asli, bagian yang sudah dipakai/dikembalikan sebelum cutover, saldo tersisa dan total kontrol. Supplier serta vendor laundry memakai akun aset/debit; pelanggan memakai kewajiban/kredit. Contoh 100,00 − 32,75 menghasilkan saldo awal 67,25. Bagian historis tetap menjadi provenance, tanpa membukukan kas historis lagi. Total kontrol hanya untuk rekonsiliasi dan tidak ikut dijurnal.

Pemakaian uang muka menghasilkan pembayaran native supplier, penjualan, atau vendor laundry; tagihan lama hasil impor memakai opening subledger settlement. Tautan privat yang immutable menghubungkan pembayaran dengan uang muka asal. Pihak harus sama, nominal tidak boleh melebihi uang muka ataupun tagihan, dan tanggal tidak boleh mendahului cutover/tagihan atau berada di masa depan. Penerimaan yang belum ditagih (GRNI) tidak bisa dibayar sebagai invoice. Jalur pembayaran kas biasa tetap berfungsi, termasuk kombinasi uang muka 67,25 dan kas 32,75 untuk melunasi invoice 100,00.

UI impor menampilkan dokumen sumber, nominal asli, pemakaian lama, opening terkini, pemakaian baru, refund dan saldo. Owner/admin dapat memilih tagihan, memakai uang muka, mengembalikan kas, mengoreksi opening, atau membalik pembayaran/event dengan alasan wajib. Nominal tetap teks exact; revision, UUID idempotency dan pemulihan respons hilang memakai batas RPC dan recovery existing. Tidak ada RPC browser baru. Bentuk baris pembayaran dan immutable facts lama dipertahankan.

| Tahap siklus tagihan lama | Sisa uang muka | Sisa tagihan | Bank supplier/vendor | Bank pelanggan |
| --- | ---: | ---: | ---: | ---: |
| Saldo awal | 67,25 | 67,25 | 100,00 | 100,00 |
| Pakai uang muka 12,75 | 54,50 | 54,50 | 100,00 | 100,00 |
| Refund 10,00 | 44,50 | 54,50 | 110,00 | 90,00 |
| Pakai uang muka 44,50 | 0,00 | 10,00 | 110,00 | 90,00 |
| Pelunasan kas 10,00 | 0,00 | 0,00 | 100,00 | 100,00 |
| Balik seluruh pelunasan, pemakaian dan refund | 67,25 | 67,25 | 100,00 | 100,00 |

Enam siklus mencakup tiga jenis pihak, UTC pada periode terbuka dan Pacific/Kiritimati pada tanggal ekonomi yang sudah ditutup. Tanggal pembukuan mengikuti jalur canonical pada hari terbuka. Seluruh akun jurnal kembali tepat ke posisi sebelum siklus; saldo bank cocok dengan laporan neraca. Replay UUID mengembalikan hasil yang sama tanpa transaksi tambahan. Tiga siklus tagihan native juga kembali tepat setelah pembayaran kas dan pemakaian uang muka dibalik.

Koreksi opening 67,25→80,25 mempertahankan dokumen asli 100,00 dan bagian historis 32,75. Setelah 75,00 dipakai, koreksi/reversal yang membuat kapasitas kurang ditolak. Membalik pembayaran lalu koreksi memulihkan saldo 67,25. Sumber, tautan, dan event tidak dapat diubah atau dihapus; perubahan sesudah posting berupa event tertaut. Generic journal reversal ditolak untuk sumber uang muka agar saldo tidak terpisah dari jurnalnya.

Akun khusus yang sudah dipakai tidak dapat dinonaktifkan, diubah jenis/normal balance/report group, dilarang posting, atau dijadikan rekening kas/mapping utama. Enam detector uang muka ditambahkan ke pemeriksaan finansial existing, termasuk kapasitas, identitas pembayaran, jurnal opening/pemakaian/event, serta kecocokan seluruh saldo subledger dengan GL akun khusus. Pemeriksaan normal bernilai nol; negative control berupa selisih jurnal 0,01 terdeteksi.

31 kasus baru terdiri dari 6 siklus tagihan lama, 3 tagihan native, 3 koreksi, 10 penolakan command, 6 sumber invalid, 1 duplikat lintas batch, 1 penjagaan akun/negative control, dan 1 penolakan GRNI belum ditagih. Penolakan mencakup pihak salah, revision usang, nominal berlebih/negatif/lebih dari dua desimal, tanggal salah, reversal generik, serta DML langsung. Proposal memiliki 56 fungsi AP + 11 AO, 24 native predecessor AP + 11 AO, dan 33 source pins. Ownership tetap 102 runtime files, 25 browser RPC, 111 permissions, 47 routes/nav labels, 20 sensitive actions, 37 stylesheets dan enam connected writer domains.

## Kegagalan yang dipertahankan

Percobaan pertama [35702980670 FAILURE](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35702980670), job `106665117481`, memakai commit `cb9f95e55f3f3189b61ca0455341240d9a9e3d45`. Pemasangan proposal gagal pada sintaks PL/pgSQL perbandingan CASE di pemeriksaan akun uang muka; **0 kasus AP sempat dijalankan**. Pada run itu 12 AO dan 72 frontend/recovery tetap PASS. Empat ekspresi CASE kemudian diberi tanda kurung; penjagaan semantik akun dan dua skenario bermakna ditambahkan sebelum gate kedua. Artifact gagal `10683840196`: 32.508 byte, 10 entri, SHA256 `876ac40b799d4e66f6b16d8b31d5605da0749657097b2bfe59e69192adc7ca7a`.

Audit lama [Final Boundary 35702980578 FAILURE](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35702980578), job `106665116573`, berhenti pada `Verify unchanged AI-R2 backend and bounded writer UI scope`. Assertion daftar perubahan successor AJ→AP melampaui scope lama; langkah database audit tersebut belum berjalan. Guard tidak dilemahkan. Artifact gagal `10683571156`: 477.439 byte, 7 entri, SHA256 `c6e310ad7bacb684741856bee41bb9c2b640018585ae4409f37ac0f7973e96d6`. Kegagalan ini tetap terbuka dan tidak diganti dengan klaim lulus native writer. Ketiga ZIP dipertahankan bersama checkpoint ini.

## Batas dan pekerjaan berikut

Writer PASS ini berasal dari database sementara dan DOM tests. Belum ada migrasi AO/AP permanen, pembuktian HTTP/browser terhadap database, concurrency antarsesi untuk keluarga baru, ataupun acceptance independen. Main, PR24/25, hosted UAT, legacy/prod database, dan CP7 tidak disentuh. Commit dokumentasi setelah tested commit tidak mengubah kode yang diuji.

ALL impor belum selesai. Urutan berikut: WIP fisik per ukuran/tahap/pemegang dan nilai BS beserta asal biaya penerimaan yang terpakai sebelum cutover; form eceran aksesori yang terhubung; paket migrasi AO/AP dan rollback maintenance; HTTP/browser/concurrency serta perlindungan opening jalur lama; lalu acceptance independen. Bukti lama tetap disimpan dan tidak dianggap otomatis mencakup fungsi baru.

Keputusan owner tetap berlaku: draft dapat diedit dan finalize membaca isi terakhir di bawah lock; total kontrol tidak dibukukan; tanggal invoice menentukan koreksi biaya pada periode terbuka, periode tertutup mengikuti jalur canonical; **7 PCS adalah aksesori dengan harga eceran manual**, master lusin/gross tetap. Mandor: Epi, Selo, Afat, Afui. Afui khusus: tanpa absensi, komisi lebih tinggi, tiga kategori aksesori gratis. Satu writer, fast-forward saja; lanjut sesuai scope yang sudah disetujui tanpa konfirmasi berulang.


---

# Riwayat proposal dan checkpoint sebelumnya

# CP6 — perbaikan pemasangan proposal uang muka

Percobaan native [35702980670](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35702980670), tested commit `cb9f95e55f3f3189b61ca0455341240d9a9e3d45`, tree `2358f733cdb161d9538324ebd97d54237c1203e7`, gagal saat CREATE fungsi funding karena CASE dalam kondisi PL/pgSQL perlu tanda kurung. **0kasus AP dijalankan**,12AO dan72frontend PASS. Tidak ada klaim AP PASS pada proposal tersebut. Artifact10683840196 (32.508byte),SHA256`876ac40b799d4e66f6b16d8b31d5605da0749657097b2bfe59e69192adc7ca7a`,CRC dan isi kegagalan telah diperiksa.

Empat ekspresi CASE terkait diperbaiki bersama. Guard akun uang muka ditambahkan agar akun sumber tidak bisa berubah jenis/saldo normal/kelompok laporan, dinonaktifkan, dijadikan rekening kas, atau mapping ledger utama setelah dipakai. Dua kasus baru membuktikan penjagaan akun/negative control drift0,01 dan penolakan membayar GRNI yang belum ditagih. Rencana sekarang103AP (72existing+31uangmuka) +12AO; **belum PASS sampai runtime membuktikannya**.56fungsi AP+11AO,24predecessor AP+11AO,33pins. CP6_HOLD,production_go:false,migration_installed:false,independent_acceptance:false.

---

# CP6 — proposal uang muka supplier, pelanggan dan vendor

22 September 2026. **CP6_HOLD · production_go:false · migration_installed:false · independent_acceptance:false.**

Owner meminta lanjut dari checkpoint kasbon `4ce534cf43f2327c73282a4cabf8cc1e34041fc4`. Scope ALL tetap disetujui. Perubahan berikut siap untuk native gate; **29 kasus uang muka baru belum dijalankan** pada saat commit proposal ini. Bukti sebelumnya tetap terkait commit lamanya.

Template ke-19 `OPENING_ADVANCE` mencatat jenis/kode pihak, akun khusus uang muka, identitas dan tanggal sumber, nominal awal, pemakaian/pengembalian lama, saldo tersisa, serta total pembanding. Supplier/vendor memakai akun aset, customer memakai kewajiban; akun uang muka tidak boleh menjadi akun kas atau mapping ledger utama. Sumber bernomor unik lintas batch, saldo awal tidak membukukan kas historis, dan total kontrol tidak ikut diposting.

Pemakaian memakai pembayaran native supplier/customer/vendor atau pelunasan opening subledger untuk tagihan lama. Tautan privat immutable mencatat sumber advance; bentuk baris pembayaran/fakta lama dipertahankan. Cash account boleh kosong hanya untuk jalur advance yang sah; ordinary cash posting tetap memerlukan rekening aktif. Status lunas, retur, invoice reversal, immutable payment facts, jurnal asli dan inverse mengikuti lifecycle native. Generic reversal untuk jurnal advance ditolak; gunakan sumber pemakaian atau event tertaut.

`PREPAYMENT` pada public import RPC existing menangani APPLY,REVERSE_PAYMENT,REFUND,CORRECT,REVERSE_EVENT. Request memakai UUID recovery, revision batch, lock dokumen→sumber, pemeriksaan pihak/kapasitas/tanggal dan nominal teks exact. Opening source/link/event tidak dapat diubah atau dihapus; koreksi/refund/reversal merupakan event append-only. Akun kas hanya bergerak saat refund atau pembayaran kas sungguhan. Koreksi atau reversal koreksi ditolak bila menghapus saldo yang sudah dipakai. UI menampilkan sisa, tagihan pihak yang sama, rekening pengembalian dan riwayat.

Validasi lokal: **72/72 frontend/recovery PASS** (31 parser/template,13 DOM,28 recovery); TypeScript,source,access,CSS,recovery ownership PASS. Python syntax/composition PASS:55fungsi AP +11AO,24native predecessor AP +11AO,33source pins. Tidak ada owned browser RPC baru. Gate native yang direncanakan:101AP (72existing+29baru) dan12AO terpisah; angka ini belum merupakan PASS. Native baru mencakup6siklus opening (3pihak,UTC/closedKiritimati),3tagihan native,3koreksi,10penolakan,6sumber invalid,1duplikat lintas batch. Semua diuji pada transaksi rolled-back runtime AN, bukan hosted database.

Supabase/Postgres docs ditinjau: https://supabase.com/changelog, https://supabase.com/docs/guides/database/functions, https://www.postgresql.org/docs/17/explicit-locking.html. Pinned runtime dan dependency tidak diubah.

---

# Checkpoint terverifikasi sebelum proposal uang muka

# CP6 — kasbon tunai saldo awal dan potongan payroll terverifikasi

22 September 2026. **CP6_HOLD · production_go:false · migration_installed:false · independent_acceptance:false.**

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa.
Keuangan—termasuk laporan—stok, dan HPP adalah raja.

Permintaan owner “now what?” diteruskan dengan memulihkan akses GitHub, mengirim proposal kasbon pada branch kerja tunggal, dan menjalankan native gate. Blocker HTTP400 pada checkpoint sebelumnya sudah teratasi. PostgreSQL lokal tidak digunakan; seluruh pengujian database berlangsung pada runtime disposable GitHub Actions. Tidak ada approval baru yang diminta.

## Identitas bukti

| Bukti | Nilai |
| --- | --- |
| Branch writer | `competition/cp6-j-closure-20260911` |
| Tested commit | `b6f5073734a183a54b434e4d2fecfbf9a55eeefa` |
| Tested tree | `23a5f260b263365dc094bc2cb88b2eb148b8a1b1` |
| Parent | `30e11e7e44b93bfb27819498853d3fbc9074924c` |
| Native | [35692777806 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35692777806), job106633111581 |
| Import AP, runtime gabungan AO+AP | **72/72 PASS**:52 existing +20 kasbon tunai |
| AO tambahan pada AN | **12/12 PASS** |
| Frontend/recovery | **67/67 PASS**:30 parser/template,9 connected DOM,28 recovery |
| TypeScript/ownership | PASS:source,access,CSS,shared recovery |
| CodeQL | [35692777861 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35692777861) |
| Artifact | `10679002266`,95.475byte,11 entri ZIP |
| Artifact SHA256 | `0d3088c0a7b6cce1ddfe04e178803b0771b832ddd2223ecfaa1fb55a8e7f942c` |
| Main, diperiksa ulang | `557005e6674058f1e5e966b350cba05501e06182` |

ZIP CRC dan hash cocok. SOURCE.json cocok dengan commit/tree; NATIVE_TRIAL.json menunjukkan combined_ao_ap:true, seluruh72kasus PASS dan boundary_restored:true. AO_TRIAL.json menunjukkan12kasus PASS; kedua laporan complete_boundary_restored:true dan seluruh flag deployment/acceptance:false. Runtime AC→AN dipasang dengan katalog asal yang dipin, Supabase CLI2.116.0 / PG17.6.1.165. Proposal AO+AP dan fixture di-ROLLBACK; database disposable dibersihkan. Tidak ada perubahan pada main, PR24/25, hosted UAT, database produksi, atau CP7.

## Perilaku yang dibuktikan

Impor `OPENING_BALANCE_ITEM` dengan `source_kind=CONTRACTOR_CASH_ADVANCE` memerlukan rincian dokumen `CONTRACTOR_RECEIVABLE`. Nilai dokumen100 dikurangi pembayaran lama32,75 menghasilkan kasbon tersisa67,25. Impor membukukan saldo awal sekali; pembayaran lama tidak menciptakan kas keluar historis. Sumber asli dan pembayaran lama tetap tersimpan sebagai provenance.

Owner/admin dapat mengalokasikan kasbon dari workspace impor ke payroll draft mandor yang sama. Alokasi memakai command existing `ALLOCATE_CASH_ADVANCE`, UUID idempotency, batch revision dan payroll row version. Nominal serta row version tetap teks exact di browser. Draft alokasi menyisihkan kapasitas tanpa jurnal; pelepasan draft atau pembatalan payroll belum dibayar memulihkan kapasitas. Persetujuan dan pembayaran mengunci serta memeriksa ulang sumber, saldo, pendapatan dan tanggal.

Pembayaran payroll memisahkan kasbon dari penalti: Dr CONTRACTOR_PAYABLE / Cr CONTRACTOR_RECEIVABLE untuk kasbon; kas hanya sebesar net payroll; penalti existing tetap OTHER_INCOME. Reversal payroll memulihkan saldo kasbon dan membalik seluruh jurnal terkait. Pengembalian kas langsung memakai opening settlement canonical dan tidak boleh memakai saldo yang sedang dialokasikan ke payroll lain.

| Tahap oracle | Bank | Kasbon tersisa |
| --- | ---: | ---: |
| Saldo awal | 100,00 | 67,25 |
| Payroll20, potongan kasbon12,75; kas keluar7,25 | 92,75 | 54,50 |
| Pengembalian tunai10 | 102,75 | 44,50 |
| Payroll berikut44,50 seluruhnya dipotong; kas keluar0 | 102,75 | 0,00 |
| Balik payroll kedua, pengembalian tunai, lalu payroll pertama | 100,00 | 67,25 |

Seluruh akun jurnal kembali ke posisi sebelum siklus. Saldo bank cocok dengan laporan neraca; sisa kasbon cocok dengan piutang ber-dimensi mandor. Siklus lolos di UTC dan Pacific/Kiritimati, serta tanggal ekonomi yang sudah ditutup dengan tanggal pembukuan canonical pada hari terbuka. Replay command mengembalikan hasil yang sama tanpa efek tambahan.

20kasus mencakup3lifecycle,2pelepasan cadangan,10penolakan,1campuran penalti,3sumber invalid,1koreksi dan negative control. Penolakan mencakup piutang umum yang bukan kasbon, mandor salah, data payroll berubah, pendapatan turun, tanggal sebelum cutover, koreksi di bawah cadangan, pecahan uang berlebih, nominal negatif, potongan di atas pendapatan, dan DML langsung. Cadangan gabungan dua payroll tidak dapat melebihi saldo; refund tidak dapat menggunakan bagian yang sudah dipesan. Koreksi tertaut67,25→80,25→67,25 mempertahankan dokumen asal100 dan pembayaran lama32,75. Drift settled_amount tanpa sumber pembayaran terdeteksi oleh checker.

Delapan pemeriksaan finansial kasbon bernilai0 pada fase normal, termasuk identitas sumber, kapasitas, jurnal payroll, settlement, orphan payment dan tanggal reversal. Native pass ini adalah bukti writer pada database sementara; belum merupakan pengujian HTTP/browser terhadap database maupun concurrency antarsesi.

## Audit yang masih gagal dan cakupan tersisa

[CP6 Final Boundary Audit35692777930](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35692777930), job106633112620, tetap **FAILURE** pada `Verify unchanged AI-R2 backend and bounded writer UI scope`. Log menunjukkan AssertionError daftar perubahan successor AJ→AP yang tidak diterima scope lama, termasuk import dan advance. Guard ini tidak diubah atau dilemahkan; kegagalannya tidak disamakan dengan PASS native. Artifact audit gagal10678553884 tetap tersedia pada run tersebut. Tidak ada kegagalan native kasbon pada percobaan35692777806.

ALL impor belum selesai. Urutan berikut tetap: uang muka supplier/customer/vendor dengan aplikasi invoice dan reversal; WIP fisik per ukuran/tahap/custody dan nilai BS serta asal biaya penerimaan yang terpakai sebelum cutover; form eceran aksesori terhubung; paket migrasi AO/AP dan rollback maintenance; HTTP/browser/concurrency serta perlindungan opening jalur lama; lalu acceptance independen. Jangan mengubah uang muka menjadi saldo utang negatif: schema AN yang ditelusuri belum memiliki tabel advance khusus dan native vendor payable memang menolak saldo negatif.

Keputusan owner tetap berlaku: ALL data awal sudah disetujui; draft dapat diedit dan finalize membaca isi terakhir di bawah lock; total kontrol tidak ikut dibukukan; tanggal invoice menentukan koreksi biaya pada periode terbuka; koreksi periode tertutup mengikuti jalur canonical; **7 PCS adalah aksesori dengan harga eceran manual**, master lusin/gross tetap. Empat mandor:Epi,Selo,Afat,Afui;Afui yang khusus tanpa absensi,komisi lebih tinggi,dan tiga kategori aksesori gratis.

Checkpoint ini menggantikan status blocker pada `CP6_Cash_Advance_Draft_Blocked.md`. Bukti serta catatan sebelumnya tetap dipertahankan sebagai riwayat. Commit dokumentasi setelah tested commit tidak mengubah kode yang diuji.


---

# Riwayat sebelum native kasbon

# CP6 — draft kasbon tunai saldo awal, native gate belum tersedia

22 September 2026. **CP6_HOLD · production_go:false · migration_installed:false · independent_acceptance:false.**

Owner meminta “lanjutt kenapa stop”. Instruksi lanjut berlaku; tidak diperlukan persetujuan ulang. Incoming canonical commit `30e11e7e44b93bfb27819498853d3fbc9074924c`. Perubahan di bagian ini adalah **proposal lokal yang belum dikirim ke GitHub dan belum diuji pada database native**. Bukti 52 AP +12 AO di bawah tetap berlaku hanya pada commit lamanya.

## Hasil yang benar-benar dijalankan

- 67/67 frontend/recovery PASS: 30 parser/template, 9 connected DOM, 28 recovery. Empat DOM tambahan memeriksa pilihan payroll mandor yang sesuai, pengiriman nominal/row version sebagai teks exact, replay setelah respons hilang, pelepasan alokasi draft, serta penolakan saldo rusak/negatif.
- TypeScript, source ownership, access ownership, CSS ownership, dan shared recovery checks PASS. Tetap102 runtime files,25 owned browser RPC,111permissions,47routes,20sensitiveactions,37stylesheets.
- Python syntax dan komposisi proposal PASS:35fungsi AP +11AO,16predecessor AP +11AO. Helper SQL baru ditempatkan sebelum SQL financial checker yang memanggilnya.30source pins.
- **20 skenario cash advance disiapkan tetapi BELUM dieksekusi.** Jika runtime dapat dijalankan, AP gabungan akan mengumpulkan72kasus (52existing+20baru), kemudian12AO terpisah. Angka rencana ini bukan PASS.

## Kontrak proposal kasbon

OPENING_BALANCE_ITEM mendapat kolom opsional `source_kind`. `BALANCE`/kosong mempertahankan jalur existing. `CONTRACTOR_CASH_ADVANCE` hanya boleh dipakai dengan CONTRACTOR_RECEIVABLE dan rincian dokumen bernomor; nominal awal dikurangi pembayaran lama harus cocok dengan saldo awal tersisa. Pembayaran sebelum cutover tetap provenance, tanpa arus kas historis baru. Registry privat menyimpan jenis sumber; kontrol total tetap tidak diposting. Ini merupakan kontrak kasbon tunai mandor, bukan implementasi advance supplier/pelanggan/vendor.

`payroll_deductions` mendapat tautan nullable ke opening subledger dan jenis CASH_ADVANCE. Constraint memastikan sumber kasbon tunai tidak bercampur dengan source aksesori/BS. Alokasi hanya melalui controlled owner/admin command `ALLOCATE_CASH_ADVANCE` pada public import RPC existing, dengan UUID idempotency, batch revision, payroll row version, pemeriksaan mandor, saldo, pendapatan dan status draft. Nominal dan row version dikirim sebagai teks; DML langsung untuk cash advance ditolak sebelum menerima pembulatan diam-diam sebagai input yang sah. Tidak ada grant browser baru.

Draft allocation menyisihkan kapasitas tanpa jurnal. Approval dan payment memeriksa ulang kapasitas di bawah lock. Payment membukukan Dr CONTRACTOR_PAYABLE / Cr CONTRACTOR_RECEIVABLE melalui PAYROLL_CASH_ADVANCE_DEDUCTION, serta kas hanya untuk net payroll. Kasbon dikeluarkan dari kategori potongan OTHER_INCOME; penalti existing tetap terpisah. Reversal payroll membalik jurnal ini dan memulihkan saldo subledger. Pembatalan unpaid payroll atau pelepasan alokasi draft membebaskan cadangan.

Cash repayment tetap melalui opening settlement canonical. Batas sisa memperhitungkan cadangan payroll serta tanggal cutover. Koreksi nominal canonical tidak boleh menyusutkan saldo di bawah bagian yang sudah dilunasi/dialokasikan. Original source tetap immutable; nominal opening operasional mengikuti koreksi tertaut. Pemeriksa opening subledger diperluas untuk memasukkan potongan kasbon dari payroll PAID; tiga detector baru memeriksa kapasitas, identitas sumber dan jurnal payroll.

Workspace impor menampilkan nominal asal, pembayaran lama, opening saat ini, pelunasan baru, sisa, cadangan, dan saldo bebas. Owner dapat memilih payroll draft milik mandor yang sama, mengisi/mengganti alokasi, atau melepaskannya; approved/paid tidak dapat dilepas melalui editor ini. Ini belum menghubungkan keseluruhan UI payroll CP7.

## Oracle database yang disiapkan

- Awal100 − pembayaran lama32,75 = saldo67,25, bank awal100.
- Pendapatan payroll20, potong kasbon12,75 → kas7,25; bank92,75; kasbon54,50.
- Pengembalian kas10 → bank102,75; kasbon44,50.
- Payroll berikut44,50 dipotong seluruhnya → kasbon0; tidak ada jurnal kas baru.
- Balik payroll kedua, pengembalian kas, payroll pertama → bank100 dan kasbon67,25; seluruh akun kembali ke saldo sebelum siklus.
- UTC/Kiritimati, payment date terbuka/tertutup; cadangan dua payroll dan refund yang mencoba memakai saldo sama; wrong party/general AR; stale version/earnings; tanggal sebelum cutover; koreksi di bawah cadangan; precision/negative/direct DML; penalti terpisah; metadata sumber; koreksi tertaut dan negative control settled drift.

Oracle baru memeriksa **semua akun**, bukan hanya helper lama enam akun inventory/supplier. Saldo bank juga dibandingkan dengan get_balance_sheet; piutang mandor dibandingkan terhadap jurnal berdimensi contractor. Fixture payroll memakai manual adjustment yang benar-benar diakui lewat approval canonical. Uji ini tidak menciptakan riwayat payroll historis sebagai bagian dari impor.

## Blocker aktual

GitHub `fetch` dan alternatif `fetch_commit` gagal sebelum mengembalikan data: HTTP400 `Invalid MCP request metadata`. Personal Context dan browsing juga menerima error transport yang sama. Tidak ada push/update_ref/workflow dispatch yang dilakukan. Head remote belum dapat diperiksa ulang pada giliran ini.

Fallback PostgreSQL17 lokal tidak dapat dimulai: chown menghasilkan `Invalid argument` dan runuser `cannot set groups: Operation not permitted`. Tidak ada perubahan SQL pada database mana pun. Tidak dilakukan eskalasi atau pelemahan pemeriksaan runtime/permission. Ini bukan automatic approval rejection dan bukan kebutuhan keputusan bisnis baru.

## Lanjut setelah akses pulih

Periksa remote branch tunggal dan parent lokal sebelum fast-forward; jangan menimpa commit lain. Jalankan native gabungan, perbaiki setiap temuan produk/fixture, pertahankan semua percobaan gagal, lalu cocokkan artifact terhadap commit/tree. Jangan menyebut20kasus baru lulus sebelum laporan native membuktikannya.

Setelah kasbon ini memenuhi gate, lanjutkan advance supplier/customer/vendor beserta invoice allocation/reversal, WIP fisik/BS dan asal nilai penerimaan terpakai sebelum cutover, form eceran aksesori, migrasi/rollback/HTTP/concurrency, lalu independent acceptance. Tidak ada approval baru yang dibutuhkan untuk scope tersebut. Writer PASS tetap bukan audit independen.

---

# Riwayat sebelumnya — checkpoint penerimaan belum ditagih

# CP6 — penerimaan belum ditagih dan konservasi biaya

22 September 2026. CP6_HOLD; production_go:false; migration_installed:false; independent_acceptance:false.

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa.
Keuangan—termasuk laporan—stok, dan HPP adalah raja.

Kelanjutan atas permintaan owner “lakuinnnn wjkwkkw”; semua keputusan sebelumnya tetap berlaku, termasuk ALL impor, tanggal invoice untuk koreksi akibat invoice, harga eceran manual, dan 7 PCS khusus aksesori. Satu writer, competition/cp6-j-closure-20260911, fast-forward saja.

## Checkpoint terverifikasi

| Bukti | Hasil |
| --- | --- |
| Tested commit | `1556508637aac8aed770070b21d51365c652a037` |
| Tested tree | `5cf33c7210996e6ade20d64b4a86cc3d58f97a9f` |
| Native | [35689137794 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35689137794) · job106622198770 |
| AP pada runtime gabungan AO+AP | **52/52 PASS**:28 kasus impor sebelumnya +24 keluarga penerimaan |
| AO tambahan pada AN | **12/12 PASS**:10 kasus sebelumnya +2 direct correction/reversal |
| Frontend/recovery | **63/63 PASS**:30 parser/template +5 connected DOM +28 recovery |
| Checks | TypeScript,source,access,recovery,CSS PASS;[CodeQL35689137795 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35689137795) |
| Artifact | `10678192143` ·87.860byte ·11 entriZIP |
| SHA256 ZIP | `879064d1172c80f62a294482592099efd20e6c735edc7f03c4bb0943750cd07e` |
| Main terverifikasi | `557005e6674058f1e5e966b350cba05501e06182` ·tidak ditulis |

ZIP CRC,source/tree,status semua kasus,seluruh restoration,dan flag hold sudah dicocokkan. Runtime tetap Supabase CLI2.116.0 / PG17.6.1.165,baseline AC→AN dengan692 objek tervalidasi. AP kini memasang **AO+AP bersama dalam satu transaksi uji**;12 kasus AO juga dijalankan terpisah pada AN. Semua perubahan proposal dan fixture di-ROLLBACK; database disposable dibersihkan. **Ini tidak membuktikan pemasangan migrasi, deployment rollback, concurrency antarsesi, atau acceptance independen.**

Koreksi invoicing dapat mengubah source valuation, sehingga source detector juga diperbaiki secara terbatas dan mempunyai negative control: biaya yang bergeser0,000001 tanpa sumber invoice sah tetap menghasilkan temuan lineage. Enam belas pemeriksaan finansial receipt family memeriksa saldo GRNI/AP,source/jurnal,cent facts,status match/return,pembayaran,orphan,revaluasi adjustment dan tanggal reversal;seluruhnya0 pada fase normal yang diuji.

Graph produksi memakai10 unit bahan estimasi10,10 pencucian nyata masing-masing7,5 unit selesai,3 FG tersisa dan2 terjual. Setelah invoice3×8,25:WIP82,37;FG49,43;COGS32,95;AP24,75;GRNI70. Setelah7×11,75:WIP88,50;FG53,10;COGS35,40;AP107;GRNI0. Ledger dan laporan sama dengan aritmetika ini,raw stock0,queue HPP selesai sebelum invoice RPC kembali,confidence READY;cutover terbuka dan tertutup sama-sama diuji.

Kasus dua baris1×0,333333 membukukan stok0,66 dan GRNI0,67. Invoice akhir membuat inventory2,00 tepat;reversal kembali ke opening0,66. Bank100 tidak berubah saat impor;setelah invoice pembayaran10 memberi90,dan reversal pembayaran kembali100. Pembayaran GRNI tanpa invoice serta reversal invoice yang masih dibayar ditolak.

## Kontrak yang disambungkan

Template ke-18 UNINVOICED_RECEIPT menghubungkan identitas supplier/penerimaan/baris/tanggal asal ke opening_source_key pada tepat satu rincian MATERIAL atau MATERIAL_ROLL dalam batch yang sama. Bahan, gudang, qty dan biaya harus cocok. Registrasi ini mewakili kewajiban yang masih belum ditagih, bukan penerimaan fisik kedua. Jumlah yang sudah terpakai sebelum cutover ditolak sampai kontrak asal WIP/HPP tersedia.

Pengesahan membukukan stok hanya melalui opening canonical. Header dan item penerimaan operasional baru diberi provenance opening yang privat, sementara jurnal kewajiban awal mendebit OPENING_EQUITY dan mengkredit GRNI_MATERIAL pada cutover. Tidak ada jurnal MATERIAL_PURCHASE, reclass AP sementara, invoice historis atau pembayaran historis sintetis. Tanggal penerimaan asli disimpan terpisah; tanggal operasional saldo awal tetap cutover.

Invoice berikutnya menggunakan sumber penerimaan tersebut pada API invoice canonical: kuantitas yang belum ditagih, AP final, pembulatan, pembayaran, retur, dan reversal mengikuti domain yang sudah ada. Recost mengubah biaya operasional movement OPENING yang tertaut; dokumen opening dan snapshot biaya asal tetap utuh. Retur roll menemukan sumber melalui tautan opening tanpa mengganti identitas asal roll menjadi pembelian biasa.

Pembulatan kewajiban dilakukan per dokumen penerimaan, sedangkan opening fisik mempertahankan pembulatan per barisnya. Target cent untuk penerimaan opening mempertahankan dasar baris tersebut sehingga invoice tidak menyisakan sen yang hilang. Selisih yang benar tetap melalui akun variance canonical.

Jurnal koreksi akibat invoice memakai tanggal invoice. Pembatalan memakai tanggal bisnis pembatalan canonical pada jurnal balik dan seluruh revaluasi turunannya, termasuk koreksi harga pembelian langsung. Aturan tanggal bisnis Jakarta, penyesuaian periode tertutup, dan snapshot laporan yang sudah filed tetap dipertahankan.

Pemeriksa lineage opening menerima recost hanya jika ada tautan penerimaan yang sah dan input cost sama dengan biaya invoice authoritative; snapshot asal tetap diperiksa. Ini bukan pengecualian bebas terhadap perubahan harga. Detector asal/jurnal GRNI baru memeriksa source, qty, material/lokasi, nilai dan tanggal, serta melarang movement/jurnal pembelian ganda.

## Batas penolakan

Identitas penerimaan dan baris dinormalisasi untuk duplikat; satu rincian stok hanya boleh mendukung satu baris kewajiban. Dokumen yang sama lintas batch ditolak. Jalur pembelian biasa tidak boleh memasukkan nomor penerimaan supplier yang sudah diimpor. Ringkasan utang yang berpotensi tumpang tindih dengan penerimaan belum ditagih ditolak. Finalisasi canonical lama juga menolak batch dengan penerimaan/master baru yang belum diterapkan.

Header penerimaan opening yang sudah disahkan tidak dapat diubah menjadi REVERSED lewat reversal pembelian biasa. Invoice/retur/pembayaran memiliki reversal tertaut masing-masing. Jalur koreksi menyeluruh atau pembatalan batch penerimaan opening masih harus dibentuk; pesan penolakan bukan klaim bahwa jalur itu sudah tersedia.

## Pemetaan keluarga

| Jalur | Implementasi / batas |
| --- | --- |
| CSV/template/editor → public action RPC | Entity baru memakai uploader editable dan durable replay existing; petunjuk batas on-hand ada di UI. |
| Stok awal dan GRNI | Satu stock layer; liability terpisah melalui opening equity; total kontrol tidak ikut posting. |
| Invoice sebagian/penuh dan reversal | Canonical source capacity/AP/recost; tidak ada stock receipt tambahan. |
| Penggunaan setelah cutover | Stock adjustment dan produksi nyata diuji pada family ini; penggunaan sebelum cutover ditolak. |
| HPP/laporan | Recost AO+AP diuji bersama; source confidence mengenali koreksi sah dan tetap menangkap drift. |
| Retur supplier | Source fallback opening roll, native AP/GRNI allocation dan reversal. |
| Pembayaran | Hanya final AP dapat dibayar; GRNI belum invoice tidak dapat dibayar; pembayaran harus dibalik sebelum invoice terkait. |
| Cent per dokumen / per stock line | Nilai kontrol mengikuti masing-masing posting; target koreksi persediaan memakai dasar opening yang tepat. |
| Legacy finalization | Refusal bila detail baru belum diterapkan. |
| Migrasi / rollback / concurrency | Belum terpasang; transaksi proposal di Supabase disposable bukan deployment rollback atau jadwal antarsesi. |

## Bukti percobaan yang dipertahankan

- f680d95c69541191a4dac864e1d2db6bc4fc5a0b / tree7949a955f4b22c79204c78bcddd1acaf34a790b6 / native35687868601, job106618465221: 42AP PASS,4INCOMPLETE karena pemanggil fixture reversal kelebihan argumen;10AO PASS. Semua boundary dipulihkan. Artifact10677600886,76.509byte,SHA256 c91aae35c560e55d32e21d168947e9f91bffb8c54912c112d0b5fe86298e8e0c.
- 62ccc4aed8b3aebcf31b7a39ce307fd688d2d0dc / tree969cd8fd056697549725d7f73d11226a4f0fac08 / native35688243333, job106619562896:45AP PASS,6INCOMPLETE. Empat kasus menunjukkan perbedaan aturan reversal/recost;dua graph produksi membuktikan detector opening belum mengenali recost invoice.10AO PASS. Semua boundary dipulihkan. Artifact10677381670,76.992byte,SHA256 e826bea1604d3ef26de5b91ec1c3a2b478e73a2e2dc1e58f8f1fc292c6808e81.
- c1d674528891b76c208f4701b0eb5a36fffacf31 / tree42045545cf3b76d1b110772c703c43e8d003b5f7 / native35688824772, job106621270467:52AP PASS dalam runtime gabungan;10AO PASS,2INCOMPLETE karena nama material fixture direct correction melebihi varchar(60). CodeQL35688824793 PASS. Artifact10678436152,88.235byte,SHA256 af6f59c76d318256834a078cd785c6f9b6677ee4d8b7f0c99053b7e3859b2833. Semua boundary dipulihkan.
- 1556508637aac8aed770070b21d51365c652a037 / tree5cf33c7210996e6ade20d64b4a86cc3d58f97a9f / native35689137794,job106622198770: **52AP +12AO PASS**,0 unfinished;63 frontend/recovery PASS. CodeQL35689137795 PASS. Perubahan terhadap c1 hanya dua file penguji dan source pins; kode produknya sama. Semua boundary dipulihkan.

## Sisa kerja ALL

Penerimaan yang sudah terpakai sebelum cutover memerlukan asal nilai dan fisik WIP/FG/BS; invoice sebelum cutover perlu rekonsiliasi opening, tidak boleh langsung memposting ke periode tanpa saldo awal. Uang muka/advance beserta alokasi dan reversal masih terbuka. WIP fisik per ukuran/tahap/custody, nilai BS, dan form eceran aksesori yang benar-benar tersambung juga belum selesai.

Impor public RPC dan native invoice diuji pada jalurnya; fixture invoice/retur memakai API private-schema canonical dengan USAGE sementara untuk aktor ordinary di database disposable. Ini tidak membuktikan form invoice atau browser→HTTP→installed runtime. Migrations AO/AP, maintenance rollback, concurrency antarsesi, perlindungan global terhadap semua direct legacy opening, dan audit independen masih harus diselesaikan. CP7 tidak dimulai.

Workflow legacy Final Boundary Audit35687868628,job106618465380 tetap FAIL pada Verify unchanged AI-R2 backend and bounded writer UI scope; tidak diubah atau dilabel PASS. Routing workflow lain yang sukses bukan acceptance.

## Sambungan teknis untuk melanjutkan

- Produk utama: scripts/cp6_initial_import_receipts.py;8 predecessor native di docs/evidence/cp6-initial-import-receipt-predecessor.json. AP kini26 fungsi (12 replacement native),AO11 fungsi;trial gabungan memasang37 fungsi. Source pins27 file.
- Tabel baru privat/RLS: initial_import_opening_stock_sources,initial_import_receipt_headers,initial_import_receipt_lines. Tidak ada grant DML browser/service role.
- Fungsi native yang disambung: refresh_material_purchase_item_cost,validate_supplier_return_source,validate_material_supplier_invoice_line,sync_material_purchase_grni_on_status,_cp6_supplier_cent_state,run_v267_financial_truth_checks,run_v268_financial_report_checks,finalize_migration_batch. Original definitions/ACL/owner dibandingkan dengan AN sebelum proposal.
- AO reverse_material_supplier_invoice dan reverse_material_purchase_cost_correction sekarang membawa tanggal bisnis pembatalan pada context recost dan cent event;post tetap membawa tanggal invoice. Generic reverse_journal tidak diubah.
- Penguji baru: scripts/cp6_initial_import_receipt_trial.py. Main AP trial memasang AO+AP bersamaan;AO trial menambah direct correction/reversal terbuka/tertutup.
- Tidak ada file migrasi atau rollback AO/AP yang dipasang. Source runtime dan predecessor lama tetap immutable.
- Urutan lanjut: advances dengan aplikasi/pelunasan/reversal;WIP fisik dan asal nilai untuk penerimaan pre-cutover consumed/BS;form aksesori terhubung;paket migrasi/rollback,HTTP/browser/concurrency,kemudian handoff independen. Jangan meminta ulang keputusan owner yang sudah disepakati.

---

# Checkpoint sebelumnya — riwayat pada 8a7616f / 590c7b7

# CP6 AP — master dan dokumen saldo awal, checkpoint lanjutan

**22 September 2026 · CP6_HOLD · production_go:false · migration_installed:false · independent_acceptance:false.**

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa.
Keuangan—termasuk laporan—stok, dan HPP adalah raja.

Lapisan ini melanjutkan checkpoint 8+10 di bawah. Owner meminta lanjut dan menegaskan bahwa **7 PCS adalah aksesori**. Keputusan tanggal invoice, harga eceran manual per buah, dan scope **ALL impor** tetap berlaku; jangan meminta keputusan yang sama lagi.

## Sumber dan bukti terbaru

| Item | Nilai |
| --- | --- |
| Branch penulis tunggal | competition/cp6-j-closure-20260911 · fast-forward saja |
| Commit yang diuji | `8a7616f823d409a1d086690f2391c965e932cf0a` |
| Tree yang diuji | `d71425b722efab8aa8225f64491547ab2cea7d04` |
| Native | [35684520266 SUCCESS](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35684520266) · job106608391252 |
| Impor AP | **28/28 PASS**, 0 unfinished |
| Biaya/eceran AO | **10/10 PASS**, 0 unfinished |
| Frontend/recovery | **62/62 di CI**; **85/85 lokal** termasuk23 recovery produksi existing |
| Pemeriksaan lain | TypeScript, source/access/recovery/CSS dan [CodeQL35684520242](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35684520242) PASS |
| Artifact | `10675464571` · 51.228byte · 11entriZIP |
| SHA256 artifact | `4089be3dd968c1c8d5a10e7ed1de67aba16b7afcb12c5fff75f1a1e2e6803805` |
| Main terverifikasi | `557005e6674058f1e5e966b350cba05501e06182` · tidak diubah |

CRC, hash, SHA/tree, jumlah/status seluruh kasus, restoration, serta flag hold pada laporan ZIP sudah dicocokkan. Kedua proposal tetap hanya dipasang dalam transaksi uji yang dibatalkan pada database disposable AC→AN. Data/fungsi kembali ke batas sebelumnya dan database dibersihkan. Ini tidak membuktikan deployment rollback atau pemasangan migrasi permanen.

## Perubahan yang sudah teruji

**Empat master baru:** LAUNDRY_VENDOR, LOCATION, CHART_ACCOUNT dan CASH_ACCOUNT. Kini17 jenis template/entity berjalan melalui uploader yang sama. Akun induk boleh muncul setelah anak di CSV. Validasi memeriksa graf induk tanpa membuat akun pada preview; siklus dan induk hilang ditolak. Impor menolak perubahan arti/induk/status akun buku besar existing, pemindahan rekening existing ke COA lain, COA kas yang bukan ASSET aktif/postable, jenis lokasi tidak dikenal, dan master ganda. Guard stok dan akun existing tetap digunakan.

**Satu batch17 jenis** diuji dari master yang belum ada sampai opening dan OPEN_PO. Preview tidak mengubah master/jurnal/stok. Posting menghasilkan tepat11 rincian opening, dengan stock/roll, FG, BS fisik, WIP nilai, kas, dan kelima jenis saldo pihak yang diharapkan. Sebelas total pembanding tidak ikut menjadi opening. OPEN_PO hanya header/target/status; **WIP fisik tidak diklaim**.

**Dokumen piutang/utang yang sudah dibayar sebagian:** kolom nomor/tanggal/jatuh tempo, nominal awal, dan pembayaran sebelum cutover ditambahkan pada OPENING_BALANCE_ITEM. Nilai awal100 dikurangi pembayaran lama32,75 harus sama dengan amount/saldo67,25. Nominal dan pembayaran lama disimpan sebagai fakta asal pada registry privat; opening subledger/jurnal hanya mengakui67,25. Tidak dibuat invoice penjualan/pembelian atau arus kas historis palsu.

Kelima saldo diuji: CUSTOMER_RECEIVABLE, SUPPLIER_PAYABLE, VENDOR_PAYABLE, CONTRACTOR_RECEIVABLE dan CONTRACTOR_PAYABLE. Bank awal100 tetap100 saat impor; pembayaran berikut7,25 memberi sisa60 dan arus bank yang tepat; reversal kembali ke67,25 dan bank100. Empat pemeriksaan canonical atas sumber/jurnal, orphan, status saldo dan tanggal tetap0 temuan sebelum/sesudah impor, settlement dan reversal pada setiap jenis pihak.

**Pencegahan pencatatan ganda:** nomor dokumen yang sama pada pihak/jenis saldo yang sama ditolak dalam maupun lintas batch, termasuk beda huruf besar/kecil. Ringkasan saldo dan rincian dokumennya tidak boleh dicampur walaupun total kontrol secara aritmetika cocok. Dua dokumen berbeda pada pihak yang sama boleh masuk dan berjumlah134,50 sesuai data. Nominal sisa salah atau tanggal dokumen melewati cutover ditolak tanpa perubahan ledger/registry. Saat pencatatan, advisory lock per pihak/jenis saldo dan unique index melindungi identitas sumber; **jadwal concurrency antarsesi belum dikualifikasi oleh trial ini**.

## Urutan bukti gelombang ini

| Commit | Native | Hasil |
| --- | --- | --- |
| `4ed70c35cc3d7db78b0a8fced9652d0411c4142d` | `35683545804` | 15AP +10AO PASS · master dan seluruh17 entity |
| `d50d0ebe7990d9f35265324eb8f3d67cd1307f96` | `35684189688` | 23AP +10AO PASS · dokumen parsial/penolakan duplikat |
| `8a7616f823d409a1d086690f2391c965e932cf0a` | `35684520266` | 28AP +10AO PASS · seluruh5 saldo pihak dan oracle jurnal/tanggal |

Commit terakhir menambah penguji/pin terhadap produk d50. Rangkaian lama di bawah tetap bukti historis sesuai SHA masing-masing; hasilnya tidak diubah menjadi hasil baru.

## Yang masih terbuka dan urutan lanjut

- ALL masih memerlukan **uang muka, penerimaan belum ditagih, serta WIP fisik per ukuran/tahap/custody**. Opening BS yang diuji masih fisik saja; kebutuhan nilainya belum selesai. Tidak ada tabel advance dedicated dalam schema AN yang diperiksa; jangan menyamakan uang muka dengan saldo pihak tanpa kontrak pelunasan/alokasinya.
- Dokumen parsial sudah mempunyai provenance dan dapat diteruskan melalui settlement opening canonical. Ini tidak membuatnya menjadi ordinary sales/supplier-invoice history; penerimaan belum ditagih beserta pencocokan tagihan/stok masih harus disambungkan terpisah.
- Guard lintas batch terbukti untuk jalur impor baru, termasuk penolakan jika saldo pihak sudah ada lewat opening lama. Jalur direct legacy yang membukukan opening setelah impor, koreksi dokumen, serta race antarsesi masih perlu pemetaan/tes sebelum mengklaim perlindungan global.
- Form aksesori yang benar-benar terhubung, reader, dan HTTP/browser masih perlu selesai. Tetap7PCS aksesori × harga manual; jangan mengganti keputusan owner dengan pecahan lusin.
- Tidak ada migrasi AO/AP dan rollback maintenance terikat sumber yang terpasang. Bentuk paket setelah kontrak produk stabil, lalu uji runtime gabungan AO+AP (trial sekarang masing-masing di atas AN), jalur public HTTP/browser, rollback/refusal/cleanup, dan seluruh keluarga tanggal/invoice direct/reverse yang terdampak.
- Audit independen tetap belum lulus. Workflow lama yang menolak scope successor tidak boleh dilabel ulang PASS. Main/PR24/25/hosted DB/deploy/CP7 tidak ditulis.

Workflow legacy Final Boundary Audit `35683545792` dan `35684189846` tetap **FAIL** pada `Verify unchanged AI-R2 backend and bounded writer UI scope`, sebelum pengujian bisnis successor. Workflow tersebut tidak diubah untuk meloloskan scope baru; native trial khusus di atas tidak menggantikan acceptance gate itu.

Jangan mengulang matrix historis yang masih terikat sumber hanya untuk menambah angka; perubahan fungsi/kontrak yang memengaruhi bukti wajib mempunyai pengujian keluarga yang tepat. Simpan branch tunggal, idempotency, draft inert, latest-data finalization, append-only correction dan laporan filed yang tetap utuh.

---

# Riwayat checkpoint pertama — status historis pada 1b3fbaa

# CP6 AO/AP — verified writer trial, 22 September 2026

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa. Keuangan—termasuk laporan—stok, dan HPP adalah raja.

**CP6_HOLD · production_go:false · independent_acceptance:false · migration_installed:false.**

Continuation from `3767458fa571f3a6f8e20945ccd01bd7ce1ab47c` on the single writer branch `competition/cp6-j-closure-20260911`, fast-forward only. The decisions in `docs/cp6-ao-ap-owner-decisions.md` remain authoritative: invoice date in an open period, manually entered retail price, and **ALL initial data**. These choices do not need to be asked again. Closed-period controlled adjustments and filed reports remain protected.

Owner clarification in this continuation: **7 PCS refers to accessories**, with the physical count independent of the dozen/gross master price. The manual price is per physical unit. This is not a change to garment quantities or a new rounding policy.

## Exact tested source and evidence

| Item | Result |
| --- | --- |
| Tested commit | `1b3fbaaec5e16962f608c5fc40e480b21e619144` |
| Tested tree | `688f8c1d8ed403e2d811a8cfff84ab6cb324e653` |
| Native writer trial | [35681922366](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35681922366) · SUCCESS · job `106600496797` |
| AP import cases | 8/8 PASS; no unfinished cases |
| AO invoice/retail cases | 10/10 PASS; no unfinished cases |
| Frontend checks in that run | 58/58 parser, connected-form and recovery tests; TypeScript, source, access, recovery and CSS checks PASS |
| Additional local affected recovery checks | 81/81 across four test files, including the existing 23 connected-production recovery tests; TypeScript clean |
| CodeQL | [35681922634](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/35681922634) · SUCCESS |
| Artifact | `10674874864` · 43,025 bytes · 11 ZIP entries |
| Artifact SHA256 | `bee475d7ef95b08604d1abafe276c0b7055250089e293bd0a032fb549cd862c2` |
| Main, rechecked after the trial | `557005e6674058f1e5e966b350cba05501e06182` · unchanged |

ZIP CRC and the GitHub digest match. `SOURCE.json`, `NATIVE_TRIAL.json` and `AO_TRIAL.json` bind the results to the tested commit. The workflow reconstructed AC through AN with frozen source, verified the 692-object AN runtime, installed each proposal only inside a transaction, ran the tests, then rolled back. Both reports confirm the full data/function boundary was restored. The disposable database was removed successfully. No hosted database, deployment, main, PR24/25 or CP7 was changed.

This documentation may be committed after the tested SHA. It does not turn the later documentation commit into a fresh native test or upgrade the result to migration/independent acceptance. Historical matrices were not rerun or relabelled.

## Implemented proposal

The connected admin page reads actual UTF-8 CSV/TSV files, preserves exact numeric text, supports quoted/multiline cells and comma/semicolon/tab delimiters, and supplies templates, editable rows and row-specific errors. Files are bounded to 5 MiB and 5,000 rows. The selected entity can be replaced while the batch remains a draft. Posted batches are read-only.

The page uses the shared global writer lock and durable request envelope. A stable UTC revision fingerprint binds edits and finalization to the server draft. Late reads cannot silently overwrite the editor. A stale draft is refused and the user's unsaved content is retained visibly. A lost response replays the same request UUID and payload. Server authorization is checked before cached replay.

Finalization locks the batch, validates the latest rows, reconciles their totals and invokes the canonical master/open-PO/opening-balance writers in one transaction. The native test changed a validated amount from 14.25 to 17.25: the old total blocked posting, correcting the total posted exactly 17.25, and replay did not duplicate it. Draft and refusal cases left the ledger unchanged.

Opening details require `control_key`. `OPENING_CONTROL` compares quantities and the sum of each posting line rounded to cents; control rows create no opening item, stock movement or journal. Missing, duplicate or mismatched controls prevent finalization. Native material and roll cases each posted exactly 7 units, value 15.75, and one stock movement. Those separate stock fixtures do not redefine the owner's 7-PCS accessory requirement. Excess precision was refused rather than silently rounded. An owner disabled through the canonical access rules could no longer read the draft.

AO adds an explicit manual retail-price field to the contractor-accessory issue proposal. With either a dozen or gross master basis, a manual price of 3.25 posts exactly 7 physical accessory PCS and a 22.75 receivable; the 300-PCS fixture ends at 293. Negative, nonfinite and overprecise prices, and fractional PCS input before column coercion, are refused. The master dozen/gross price is not overwritten.

Invoice cost posting carries a private, transaction-scoped invoice date through material revaluation, PO HPP, FG/COGS and journal synchronization. Affected queued PO recalculations finish before the invoice command returns. Four two-month-delayed, partly invoiced production scenarios passed in UTC and Pacific/Kiritimati, with periods open and closed. New correction journals use invoice economic date; closed periods retain the existing controlled accounting date. Totals, reports, confidence, replay and removal of the private context were checked by the fixture. This does not convert all twelve historical date-policy observations into new PASS results.

## Affected paths and remaining scope

| Path | Current disposition |
| --- | --- |
| File decode → editor → public workspace/action RPC → canonical staging | Implemented proposal; parser/DOM and native public RPC checks pass separately. Full browser → HTTP → installed successor remains unproven. |
| Master import | Nine existing types exposed: BRAND, SIZE, MODEL, PRODUCT, CUSTOMER, SUPPLIER, CONTRACTOR, ACCESSORY_CATEGORY, MATERIAL. The new trial exercises customer and material routes; no fresh positive coverage claimed for all nine. |
| Physical opening stock | MATERIAL_ROLL and MATERIAL opening paths pass focused native cases. Existing FINISHED_GOODS and BS routes are exposed through the opening contract; their full affected-family regressions remain required. |
| WIP | Existing `erp.post_opening_balance(uuid)` creates value only. It does not create physical work by size, stage or custody. Physical WIP still needs a domain contract and implementation. |
| Cash and party balances | Existing types: CASH_BANK, CUSTOMER_RECEIVABLE, SUPPLIER_PAYABLE, VENDOR_PAYABLE, CONTRACTOR_RECEIVABLE, CONTRACTOR_PAYABLE. Customer receivable passed latest-draft/replay; other affected routes still need focused verification. |
| Open production orders | Existing `erp.apply_migration_open_pos(uuid)` maps OPEN_PO to legacy PO headers and target/status metadata. It does not create physical WIP or historical production events. |
| Laundry vendors, locations, chart/cash accounts as imported masters | Not yet implemented as new upload types. Existing references must resolve to existing records. |
| Advances, uninvoiced receipts, partly settled invoices and other outstanding documents | Not yet implemented. Must map original document identity, outstanding quantity/value and settlement linkage without inventing historical transactions. |
| Detail/control double count | Prevented within the tested batch: controls never post; exact request replay is idempotent. Cross-batch duplicate source documents and overlap between opening summary and operational documents remain uncovered. |
| BS valuation | Current BS opening is physical-only with zero control value. This does not complete all legacy BS valuation requirements. |
| Manual accessory retail entry | Native trigger/save/post proposal verified. A connected contractor-issue editor, workspace reader and HTTP family still need completion; the existing simulation UI is not evidence of that connection. |
| Invoice writer family | Four post/reverse functions for supplier invoices and direct purchase-cost corrections are modified. New native cases exercise invoice finalization with production consumption; direct-correction/reversal and concurrent queue schedules still need proof. |
| SQL admission and rollback | No AO/AP migration or maintenance rollback package generated/installed. Trial transaction rollback proves isolation of the experiment, not deployment rollback qualification. |
| Independent acceptance | Pending. Writer-owned tests cannot grant independent PASS. |

The total scope remains ALL. The first transport contract has 12 existing types plus `OPENING_CONTROL`; that count does not mean ALL is finished. Unknown amounts, historical invoices and physical production events must not be fabricated to fill the remaining contracts.

## Attempts retained as observed

| Candidate | Native run | Outcome at that attempt |
| --- | --- | --- |
| `793a11a5b2b89fec586661d85c35115f617be719` | `35680566540` | Fixture called a private role helper after private-schema access was revoked; no business-case PASS. |
| `968227774003caf2e0aa23ac1efe74b10cff1453` | `35680813968` | Four import cases passed; revocation fixture hit the real LAST_ACTIVE_OWNER_PROTECTED guard. |
| `53c67714bf23495a6fcb23e5d0a7fd7d0c0a2761` | `35681139619` | Five import cases passed; two new physical-stock fixtures lacked a required location. |
| `bb801b917f2c747c400f75eb3027b767f061dc06` | `35681575334` | Six import cases passed; roll fixture used an unknown unit alias. AO was skipped by that workflow version. |
| `1b3fbaaec5e16962f608c5fc40e480b21e619144` | `35681922366` | AP 8/8 and AO 10/10 PASS with complete boundary restoration. |

Fixture repairs preserved the last-owner guard, server authorization and installed UOM definitions. Original failing runs remain failures.

On the tested SHA, general router run `35681922247` succeeded only as routing evidence. The automatically triggered legacy AI-R2 independent workflow `35681922487` failed its unchanged bounded-source assertion before business tests because this successor is outside its old scope. It remains a failure, not independent evidence for AO/AP. Earlier generic source-gate and workbench failures remain as recorded.

## Resume from this checkpoint

Keep the writer branch and source pins above. Map and complete the remaining ALL import contracts, including document-to-opening reconciliation; finish the connected accessory retail editor; enumerate direct/reverse/date/report and concurrency paths. Then generate pinned AO/AP migration and pre-use rollback packages from genuine CLI provenance, complete installed-runtime/HTTP/UI checks, and run one combined affected-family gate after the product stabilizes. Preserve old evidence only where exact source/runtime equivalence permits it. Hand off the qualified writer result for independent review; do not self-certify CP6 or begin CP7.

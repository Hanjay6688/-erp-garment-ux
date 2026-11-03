# B — UI Kain kantong dan Impor data awal, 3 November 2026

Pemeriksaan dua halaman yang sebelumnya berhenti pada batas sign-in kini mencakup komponen aslinya melalui Auth/RPC tiruan terisolasi. Matriks 80 tampilan pada 320/390/768/1440 px selesai dan diperiksa. Ini penutupan celah bukti UI fixture; Auth/database/HPP backend aktual belum diuji dalam paket ini.

A tetap integrator tunggal dan pemilik Afui, SKU, keuangan/HPP, SQL, izin, kontrak bersama dan pemulihan. B bekerja pada `astra-b/ui-connected-forms-20261103`, terpisah dari worktree A. Konteks A yang dibaca: V352; cabang tema A masih `462099c6cc59fa93766c81db66ec820b6cd54055` saat diperiksa ulang. Tidak ada pekerjaan database bersama, perubahan hosted/Enteng, deployment, WA, CP7C, timer atau subagen.

| Identitas | Nilai |
| --- | --- |
| Base paket UI B sebelumnya | `bb826c3b74ce962b507df92e7f94861f339165c1` |
| Sumber browser akhir | `81e5a313a8ed25105fafd781bdb99bf296dee975` |
| Tree sumber browser | `0e301aa65ae2be6c0708c131d14e6573d4ba5ca0` |
| Run / job / percobaan | [41644508539](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/41644508539) / 125946200449 / 1 |
| Kesimpulan asli | SUCCESS; semua tahap selesai, server anak dipastikan berhenti |
| Artefak asli | 13235191080; 8.954.858 bytes; 85 anggota; SHA-256 `a8a148c74c6f9411721532ae7469dbd91f24f9bdefdf9873193d454ea4c78984` |
| Batas penerimaan | Formal 5/16; `production_go=false`; `independent_acceptance=false` |

Perubahan produk hanya tiga berkas. Kain kantong menampilkan status pemuatan, membedakan jumlah alokasi yang belum tersedia dari nol, dan menunda pesan stok kosong sampai pembacaan memberi array kosong. Impor data awal menampilkan status pemuatan. `initial-import.css` memakai `--on-accent` untuk teks tombol primary agar terbaca pada tema yang sudah ada. Selector CSS ini juga menjadi ketergantungan visual form connected lain yang memakai `.initial-import button.primary`; pemeriksaan browser baru ini mencakup kedua halaman tersebut saja.

Prefix controller, parser, RPC, formula, sumber tanggal dan guard kedua komponen identik dengan base. AuthProvider, client Supabase, hook/envelope recovery, katalog izin, package/lock dan config Vite produksi tetap identik. Tidak ada SQL atau kontrak transaksi yang berubah.

Regresi terarah mula-mula benar-benar gagal: pembacaan tertahan menampilkan `0 dari 0 alokasi` dan stok kosong. Bukti pertama tetap tersimpan. Sesudah perbaikan render, 45 tes terkini lolos: 41 tes DOM kedua halaman yang sudah ada, tiga kontrol kontrak fixture, dan satu regresi jumlah belum diketahui. Jangan menjumlahkan 44 tes pra-perbaikan sebagai tes unik tambahan. Build/typecheck produk lolos; 149 artefak hasil build tidak mengandung marker fixture. Seluruh `src` pada sumber tes/build `2ce9d8ec422190c7096f55331e68f0b6545d7424` identik dengan sumber browser akhir sehingga tes tersebut digunakan kembali.

| Cakupan browser | Bukti |
| --- | --- |
| Kedua halaman, empat lebar, delapan keadaan | 64 tampilan: siap, data panjang, kosong, loading, error, pending, tanpa izin dan akses dicabut |
| Pratinjau HPP periode baca saja | 4 tampilan; angka berasal dari fixture, bukan hasil keuangan backend |
| Bytes file CSV dibaca ke editor | 4 tampilan; tidak ada RPC simpan selama pratinjau |
| Buka ulang pending | 8 tampilan; UUID/payload lokal tetap sama, tidak ada pengiriman ulang otomatis |
| Klik ganda | Delapan keadaan pending menghasilkan satu panggilan simpan ke double dan UUID sesuai envelope lokal |
| Visual dan console | 80 PNG sesuai hash; tidak ada overflow dokumen, galat console/page/network, atau temuan pada sampel kontras yang diukur |

Penulis B memeriksa contact sheet seluruh 80 identitas dan detail ukuran asli untuk status jumlah belum tersedia, recovery impor, CSV serta pratinjau periode. Tabel lebar tetap memakai gulir lokal; teks panjang dan kontrol tidak melebarkan dokumen. Ini pemeriksaan penulis, bukan audit aksesibilitas menyeluruh atau audit independen.

Dua kegagalan browser tetap FAILURE. Run 41641552705/job125936053635 pada `2ce9d8` menghasilkan nol tampilan karena modul seed fixture yang sudah ada ikut ditolak HTTP403. Pengaman diperbaiki hanya untuk path modul itu, lalu preflight mencakup seluruh graph impor statis (51 modul). Run 41642954385/job125940822601 pada `6599150` menghasilkan 52 tampilan valid dan berhenti pada tiga pemeriksaan pending impor yang mencari tombol simpan yang sudah dihapus oleh recovery observer. Controller yang sudah ada sengaja menutup workspace/editor saat SAVE_FILE dimulai. Pemeriksaan penerus membuktikan editor hilang, pemilih batch terkunci dan tombol reconcile muncul; pemeriksaan klik ganda, UUID/payload dan reload dipertahankan.

Sumber UI, fixture dan dependency terkunci tidak berubah dari `6599150`. Arsip dan 52 PNG masing-masing diverifikasi sebelum dipakai kembali; status run asal tetap gagal. Penerus hanya menjalankan 28 tampilan yang belum selesai. Tahap browser baru terukur 27 detik; job lengkap 88 detik termasuk checkout/dependency/browser. Tahap browser gagal terdahulu 65 dan 78 detik, termasuk timeout pemeriksaan yang salah. Angka tersebut adalah waktu perangkat uji CI, bukan latensi transaksi atau ukuran kinerja backend. Tidak ada kenaikan timeout atau pengurangan pemeriksaan angka.

Config fixture hanya boleh serve dalam mode khusus; build fixture, root produk, Auth asli dan client Supabase asli ditolak. Graph impor dikompilasi sebelum browser; browser menolak jaringan luar; server menerima environment yang sudah dibatasi. Satu kegagalan parser graph lokal juga dipertahankan: TypeScript 7 menyediakan versi saja, bukan JS Compiler API yang semula dicoba. Pemeriksaan akhirnya memakai es-module-lexer yang sudah terkunci tanpa dependency baru.

Untuk penerapan, gunakan `APPLICATION.json`, `APPLICATION_CHECK.json` dan `CONNECTED_UI_ONLY.patch.gz`. Patch hanya tiga berkas terhadap base paket UI B sebelumnya. A perlu menerapkan paket keluarga UI terdahulu secara selektif dahulu jika belum diadopsi, mencocokkan hash/hunk dengan cabang A terkini, lalu memilih tiga perubahan render/style ini. Jangan merge seluruh cabang atau memasang ulang tema/reopen lama. Penerapan pada indeks sementara base menghasilkan blob yang sesuai kandidat tanpa menyentuh worktree A.

Dokumen hasil merupakan penerus bukti saja dari sumber browser akhir. Verifikasi kesamaan runtime tercatat pada `EVIDENCE_ONLY_SUCCESSOR.json`; SOURCE/SOURCE_V2/SOURCE_V3 dan semua bukti gagal historis dipertahankan. Bukti 328 tampilan paket keluarga UI sebelumnya tetap merupakan bukti pada sumber terdahulu; jangan menyebutnya pengujian ulang pada kandidat ini atau menjumlahkannya sebagai satu run browser baru.

Arsip asli, identitas dan salinan permanen tercantum pada `ORIGINALS.json`. [Pratinjau desktop/HP](https://chatgpt.com/library?file_id=libfile_ac17617f90088191b97c2fa36ed46f11&account_id=personal) dan [Original 80 tampilan](https://chatgpt.com/library?file_id=libfile_115e1a275f3c8191afabcf954df220ad&account_id=personal) tersedia. `BROWSER_REVIEW.json` dan report terkompresi menyimpan matriks serta batas klaim.

Yang tersisa: A meninjau/menerapkan patch, menjalankan pemeriksaan dampak pada kandidat integrasi, dan menyediakan penerimaan Auth/backend gabungan. Penyelesaian reconcile di server, idempotensi backend, konsistensi sumber, stok, saldo dan HPP resmi tidak dibuktikan oleh transport tiruan ini. Tidak ada kenaikan formal, pembukaan produksi atau penerimaan independen.

# Checkpoint CP7: input kain dan recovery

Checkpoint besar input kain dan recovery selesai untuk ruang lingkup yang dinyatakan di bawah. Checkpoint inti tersimpan di `1ee958f5408bb75fd6bbff513ff117da5362082c`, yang juga menjadi sumber Native reminder284 terakhir. Kode aplikasi yang dikualifikasi berada di `e7e4ddefefcbb603304a43141c71e7fa9bb02122`; source1ee menambahkan bukti dan ekspor JSON CI dengan kode aplikasi, SQL produksi, oracle dan jumlah kasus yang sama. Penutupan checkpoint ini hanya menambahkan dokumentasi dan bukti lengkap.

Input pemakaian kain untuk produk fisik dan ukuran yang tepat sudah terhubung ke satu analisis bersama. Bahan dan satuan berasal dari master ERP. Angka pemakaian, tanggal berlaku dan alasan review diisi secara eksplisit; pola opsional tetap belum diketahui jika tidak dipilih. Hasil rencana ditandai sebagai asumsi. Versi berlaku mengikuti waktu pencatatan dan tanggal efektif, termasuk kedaluwarsa, perubahan master dan koreksi terakhir. Riwayat lama tetap utuh.

Simpan memakai UUID yang sama untuk pemulihan respons hilang. Penolakan yang pasti belum menulis melepas request tersebut dan mewajibkan pembacaan baru. Respons yang belum jelas mempertahankan payload dan UUID lengkap. Izin diperiksa kembali setelah lock benar-benar ditunggu. Pergantian tab, konflik versi dan pencabutan izin tidak boleh mempertahankan angka lama atau membuat simpan ganda.

| Pemeriksaan | Bukti lengkap yang sudah diperiksa | Sumber |
| --- | --- | --- |
| Input kain Native | 13/13: 8 database, 2 race menunggu lock, 1 Auth HTTP, 2 browser | e7e4ddef |
| Regresi analisis bersama | 152/152: 106 database, 20 race, 12 Auth HTTP, 14 browser | e7e4ddef |
| Reminder, publikasi, aturan dan laporan kewajiban | 284/284: 179 database, 40 race, 29 Auth HTTP, 36 browser; admission3 tidak dihitung lagi | 1ee958f5, kode aplikasi e7e4ddef |
| Rencana dan hasil produksi | 39/39: 25 database, 8 race, 2 Auth HTTP, 4 browser | 190078a8 |
| Koreksi nota historis | 40/40: 28 database, 4 race, 3 Auth HTTP, 5 browser; admission3 tidak dihitung lagi | e7e4ddef |
| Paid redye | 5/5: 2 database, 1 Auth HTTP, 2 browser | e7e4ddef |
| Shell | 161 berkas, 1.538 tes, 6 browser sintetis | e7e4ddef |
| CodeQL | Dua analisis berhasil, nol temuan | e7e4ddef |
| Recovery lokal | 69 tes terkait berhasil, build dan pemeriksaan keamanan berhasil | kode perbaikan menuju e7e4ddef |

Kasus di tabel dapat saling memakai kontrol yang sama. Jumlahnya bukan penjumlahan oracle independen. Bukti Shell juga tidak dihitung sebagai kasus bisnis Native.

Native kain membuktikan gap fixture 85 PCS dengan review rate 2 menghasilkan 170 dalam satuan master sebenarnya, lalu versi review berikutnya rate 3 menghasilkan 255. Ini angka fixture; bukan keputusan pemakaian operasional owner. Desktop dan mobile sama-sama membuktikan penolakan backdate lebih dari satu tahun tanpa menulis, review baru, respons simpan hilang, reload, replay UUID yang sama dan hanya satu simpan. Stok, uang, HPP dan jurnal Native tidak berubah oleh penulisan metadata recipe. Semua gate paket, primary, backup/restore, Auth cleanup, pemulihan schema/data/fungsi/ACL dan advisor lolos.

Kelima JSON gate Original lengkap beserta hash setiap anggota ZIP disimpan untuk setiap suite Native yang dikualifikasi. Nota40 mempertahankan sepuluh JSON top-level dan reminder284 mempertahankan seluruh delapan belas JSON top-level, termasuk diagnostik aslinya. Kain menyimpan seluruh 8 PNG Native, 18 katalog mentah dan 8 kontrol sensitivitas pembanding yang dihitung ulang. Paid redye menyimpan 6 katalog mentah beserta kontrolnya. Seluruh field, pasangan signature/hash fungsi, relation dan hash row dipertahankan. Analisis152, reminder284 dan rencana39 memiliki audit pembanding asli dalam Original; mode tersebut tidak menyimpan seluruh snapshot katalog mentah, sehingga tidak diberi kredit raw-snapshot baru. Flag bernilai false yang memiliki ruang lingkup tertentu dalam kasus asli tetap dipertahankan.

Bukti kegagalan pertama di source190 tetap ada. Native kain pertama 12 PASS/1 gagal persiapan fixture; fixture penerus memperbaiki izin baca awal tanpa melonggarkan guard produksi. Penyebab tepat perbandingan katalog publik pada kegagalan nota/redye pertama tetap UNPROVED. Raw body redye penerus membuktikan perubahan urutan pasangan fungsi saja pada source penerus; kesimpulan itu tidak dipindahkan ke run lama.

Koreksi nota40 dan 3 admission sudah dikualifikasi: semua ID predeclared dan planned cocok, sepuluh JSON utuh dipertahankan, serta 58 katalog utama dan 8 katalog admission dihitung ulang. Regresi reminder284 sekarang juga dikualifikasi dari run37313916811/job111775775298: semua ID planned cocok, seluruh 284 kasus dan 3 admission lolos, 360 pemeriksaan katalog utama dan 8 admission tercatat dalam Original, Auth HTTP/browser benar-benar memakai Auth runtime, dan seluruh gate install/primary/backup/restore/advisor serta Auth0→0 lolos. Dua belas JSON diagnostik HTTP memiliki nol kredit kasus tambahan; diagnostik Native155 historis tetap mempertahankan kegagalan aslinya. Tidak ada klaim waktu respons produksi atau audit independen dari diagnostik tersebut.

Artifact JSON lengkap11348714546 berukuran 65.445 byte, SHA-256 `4b7da57fc85d2f7488dc5e86d384be1974aa9214413f095a31346c12d0eddb69`; seluruh CRC dan hash anggota diperiksa. Arsip penuh11349048986 berukuran 370.866.392 byte tetap tersimpan pada run yang sama, SHA-256 `66291f7e335fd926d2168dce94b96a6959e3c81ab1b4cfc2b65778d9dcbc737f`. Arsip penuh ini belum dimaterialisasi di workspace; kualifikasi dilakukan dari semua JSON Original top-level yang diekspor utuh oleh job yang sama. Arsip reminder source190 gagal diambil dua kali dengan HTTP502; itu tidak membuktikan isi ZIP rusak dan tidak memberi kualifikasi Original284 pada run lama. Jumlah kasus, kode runtime dan oracle tetap sama.

Batas checkpoint: pemasangan kain yang benar-benar terjadi, sisa layak yang dialokasikan, tambahan bahan dari luar dan kemampuan produksi global masih UNKNOWN sampai sumber fisiknya terbukti. Full P08, aktivasi reminder kain/P18, skala representatif P19, audit independen P20 dan pemasangan P21 masih terbuka. `production_go:false`; belum ada pemasangan hosted produksi.

Untuk melanjutkan, baca `CURRENT_STATE.json`, `f04/NATIVE_FABRIC_RECIPE.md`, declaration13 dan receipt lengkap di `evidence/fabric-recipe/qualified13-e7/`, `evidence/fabric-recipe/qualified-shell-e7/`, `evidence/f05-analysis/qualified152-e7/`, `evidence/f05-attention/qualified284-1ee/`, `evidence/f04-plan/qualified39-190/`, `evidence/f03-redye/qualified5-e7/` dan `evidence/note-correction/qualified40-e7/`. Semua kualifikasi checkpoint di tabel sudah ditutup. Pekerjaan berikutnya adalah menghubungkan bukti fisik P08 tanpa menjadikan angka yang belum terbukti sebagai nol atau asumsi bawaan, kemudian reminder kain/P18 dan skala representatif/P19. Audit independen/P20 dan pemasangan/P21 tetap memiliki bukti tersendiri. Tetap satu writer, periksa ref canonical sebelum fast-forward, dan jangan force-push.

Chat writer lama yang menjadi titik pemulihan adalah 5 Oktober 02.44.40 WIB, berbeda dari commit b215 pada 01.19.46 WIB. Kedua waktu itu tetap dicatat terpisah; checkpoint baru ini tidak mengganti sejarah chat atau mengaku memulihkan perubahan lama yang belum pernah dikomit.

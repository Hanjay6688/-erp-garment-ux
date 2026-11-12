# Cakupan Native SKU untuk uji lanjutan

12 November 2026 WIB. Pemeriksa membaca arsip asli E4EA dan AE0D dan memeriksa 398 CRC. Keduanya tetap tercatat gagal di GitHub.

| Arsip | Kandidat | Hasil Native yang diikat ke bukti asli |
| --- | --- | --- |
| [43132617378 / 13914600256](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/43132617378/artifacts/13914600256) | `e4eaaece` | 12 skenario dari lingkup lama yang telah ditetapkan |
| [43187520935 / 13940756296](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/43187520935/artifacts/13940756296) | `ae0df1ef` | 13 skenario, termasuk delapan yang sekarang benar-benar berjalan di WIB |

Kedua daftar mencakup tepat 25 ID. Setiap ID diikat ke hasil lengkap di JSONL, pemeriksaan pemulihan per kasus, dan file asli sebelum/sesudah seluruh 15 sequence. Prasyarat aktor, pemanggil dan fixture uang cocok dengan bukti lama. Arsip AE0D mencatat pemulihan 407 tabel, sequence kembali ke baseline, dan worker selesai. [Pemetaan bukti](SKU_NATIVE25_ORIGINAL_OBSERVATIONS.json)

Kedua salinan database mulai dengan `erp.audit_logs_id_seq = (1, false)`. Saat skenario pertama mulai nilainya `(222, true)`. Pada AE0D, 14 sequence lain sama, semua sambungan antarskenario cocok, dan observasi terakhir cocok dengan akhir grup. Pemeriksa lama berhenti pada selisih awal tersebut. Uji lanjutan perlu mengikat alokasi audit dari setup sebenarnya di salinan uji dan tetap menolak perubahan sequence di luar setup yang terbukti.

Build, impor modul dan empat pemeriksaan Chromium 1440/390 pada kedua checkout sudah lulus. Dua transaksi browser dengan login nyata dan penolakan pembatalan setelah transaksi terpakai masih perlu dijalankan. Pakai 25 hasil Native ini setelah kesetaraan kandidat lanjutan terbukti. Jalankan bagian yang terdampak jika sumber, fixture, hak akses, atau assertion yang dipakainya berubah. Penerimaan SKU tetap menunggu lima pemeriksaan, pemulihan salinan, pembersihan Auth, dan arsip kanonis. Katalog diagnostik lengkap diikat ke AE0D. Global menunggu bukti SKU akhir.

## Kontrol browser sebelum run berikutnya

Tes lama mengasumsikan nilai pintu masuk selalu kosong, sehingga tes penolakan gagal ketika dibaca dari checkout SKU yang sudah terikat ke sumber. [Patch tes](SKU_BROWSER_TEST_CLOSED_CONTEXT.patch) memberi tes penolakan kondisi tertutup secara eksplisit dan memeriksa bahwa nilai awal kembali setelah tes. Patch menyentuh dua berkas tes saja.

Pada checkout `ae0df1ef`, 24 kontrol Python dan 8 kontrol Node lulus. Satu kontrol Python yang mensyaratkan checkout penuh `090b85d3` belum dijalankan lokal. Dua helper yang dipakainya, `cp6_be_probe.py` dan `cp6_bf_probe.py`, dibaca di GitHub pada `090b85d3` dan `f1674ae8` dengan isi serta Git blob identik. Arsip AE0D juga memuat hasil admission checkout dari runner. Kontrol ini belum menghasilkan kredit transaksi browser.

Pemeriksa `verify_ae0d_native.py` memakai helper yang sudah ada di direktori sebelah `sku-43166466578-combined` dan pembaca Original yang dipakai oleh `verify_wib_successor.py`. Berikan repositori sumber dengan objek commit terkait, kedua direktori Original (`canonical.zip`, `run.json`, `job.json`, `artifact.json`) dan path hasil baru. Pemeriksa tidak menjalankan SQL atau workflow.

# Serah terima Writer B untuk Planner dan BS/Laundry

12 November 2026. Cabang `astra-b/planner-bs-laundry-20261112`. Basis build `ae0df1ef17b4d84478d50a2a144cf0382d662ad0`, tree `b8f534ba09226311c6eb83b967732dd7545db6ea`, tree `src` `f817f1f3ae0e53c679fdcf1a404fa0602d6bafbd`.

Saat diperiksa kembali, kandidat A sudah maju ke `beda75853d9cb698ec912639002b3e4bd1ec52cf`. Tree `src`, fixture, aset publik, kontrak, input build dan konfigurasi browser yang dibandingkan masih identik. Patch lolos `git apply --cached --check` di index terpisah yang diisi dari `beda7585`. Run SKU penerus milik A dan masih berjalan saat pemeriksaan. [Kandidat A](https://github.com/Hanjay6688/-erp-garment-ux/commit/beda75853d9cb698ec912639002b3e4bd1ec52cf) · [run SKU penerus](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/43211990138).

## Planner / OW13a

Form login App dijalankan di browser dengan respons Auth dan RPC fixture. Owner diuji di desktop 1440 px dan Admin di HP 390 px. Pengujian penolakan memakai Staff dengan izin dasar yang sama serta Admin tanpa `sales.invoice.view`.

| Skenario | Harapan | Aktual di kedua viewport | Status fixture |
| --- | --- | --- | --- |
| Produk aktif kosong | CTA membuka Data Master | **Lengkapi produk di Data Master** membuka halaman **Produk & SKU** dan membaca `erp_get_sku_workspace_v1`. | `PASS` 2/2 |
| Dua produk, target belum lengkap | CTA memilih SKU yang diklik | **Lengkapi target TARGET-B-002** membuka formulir Aturan dan target produksi untuk SKU kedua. RPC profil menerima `root_id` SKU kedua. | `PASS` 2/2 |
| Analisis berjalan, tutup, buka lagi dan refresh | Status dan hasil mengikuti job yang sama | Satu `ENSURE`, satu job `00000000-0000-4000-8000-000000000095`. Setelah fixture mengubah status ke selesai, hasil periode 25–29 September 2026 kembali dengan stok fisik 76 PCS dan nilai yang belum tersedia tetap berlabel **Belum diketahui**. Baris hasil identik setelah refresh. | `PASS` 2/2 |
| Analisis gagal | Tampilkan kegagalan tanpa membuat job baru | Pesan gagal tetap terlihat setelah periksa ulang. Driver merekam pembacaan `STATUS` dan nol `ENSURE`. | `PASS` 2/2 |
| Izin tidak memenuhi syarat | Panel tidak tersedia dan tidak memanggil RPC awal | Staff dan Admin tanpa izin terkait sama-sama tidak melihat panel. RPC awal tidak dipanggil. | `PASS` 2/2 |

Total **10/10** dalam 19,342 detik untuk tahap browser Planner. Build App asli sudah memiliki penghubung Data Master dan pembukaan profil terpilih. [Run asli dan tahap Planner](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/43210650647/job/131157068674) · [receipt tahap](SECOND_BROWSER_RUN.json).

Bukti lama OW13a dipertahankan sesuai sumber dan cakupannya. Dari 15 berkas yang dibandingkan, tujuh identik termasuk SQL awal, panel awal, parser dan driver historis. Host, profil dan pembaca hasil sudah berubah sehingga pengujian difokuskan pada sambungan dan pembukaan hasil. Dua kasus login nyata progres keuangan tetap menjadi bukti pada jalurnya sendiri. [Bukti OW13a 126 kasus](https://github.com/Hanjay6688/-erp-garment-ux/blob/ae0df1ef17b4d84478d50a2a144cf0382d662ad0/docs/cp7/d17-14/ow13a/README.md) · [perbandingan sumber](SOURCE_COMPARISON.json) · [dua kasus progres keuangan](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/40697846383/job/122849290624).

## BS dan Laundry

| Skenario | Harapan | Aktual di build dengan patch | Status fixture |
| --- | --- | --- | --- |
| Reject BS `BS-OPERATOR-01` | Tiga kategori terbaca dan keterangan bebas bisa dibuka ulang | **Belum diketahui**, **Jahit**, **Laundry** terlihat. Keterangan panjang tentang bolong, noda dan jahitan lepas tampil kembali di detail dan kolom edit. Versi baris 4 menjadi 5 dengan satu `CLASSIFY_BS` per pengujian. Refresh tidak mengulang simpan. | `PASS` 2/2 |
| Laundry `LDR-PARTIAL-07`, `Laundry A`, `PO-PARTIAL-07`, batch 7 | Identitas benar dan seluruh ukuran terlihat | Ukuran 31 menunjukkan **5 dikirim / 5 kembali / 0 di luar** dan hanya dibaca. Ukuran 32 menunjukkan **8 / 3 / 5**. Sebelum memilih surat kirim, petunjuk keadaan kosong tampil. | `PASS` 2/2 pada skenario Laundry |
| Claim Laundry `CLM-PARTIAL-01` | Klaim tertaut dan sisa barang tetap di luar | Klaim `DAMAGE` tertaut ke `LRC-PARTIAL-07` dan surat kirim `LDR-PARTIAL-07`. Klaim menunjukkan 1 PCS dengan Rp0. Lima PCS tetap tercatat belum kembali. Perjalanan UI ini merekam nol simpan Laundry atau claim. | `PASS` pada skenario Laundry yang sama |

Kedua skenario dijalankan di 1440 dan 390 px. Detail panjang BS dan formulir penerimaan Laundry juga diperiksa di 320 dan 768 px. Semua lebar dokumen pada hasil yang lulus sama dengan viewport. Khusus penerimaan di 768 px, baseline mencapai 790 px dan patch menurunkannya ke 768 px. Respons fixture terverifikasi dan tidak ada galat console atau page pada kasus yang lulus. [Laundry 2/2](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/43211906751/job/131161386815) · [BS 2/2](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/43212478566/job/131163327456).

Pada baseline, BS menampilkan kode `UNKNOWN/SEWING/LAUNDRY`. Header penerimaan tidak mencantumkan PO dan ukuran yang sudah kembali semua tidak tampil. Patch usulan hanya menyentuh `src/ConnectedBsResolutionPage.tsx`, `src/ConnectedLaundryPage.tsx` dan `src/connected-laundry-qc.css`. Kode kategori yang dikirim tetap sesuai kontrak. Baris ukuran yang selesai hanya menambah informasi yang dibaca. A dapat menerapkan patch selektif setelah memeriksa preimage pada basis integrasi. [Patch untuk A](OPERATOR_UI.patch) · [hash patch dan postimage](FINAL_BROWSER_RUN.json).

## Reproduksi dan bukti asli

Build memakai `npm ci --ignore-scripts --no-audit --no-fund` dan `npm run build:cp6-disposable`, Node 22 pada runner serta Chrome Headless Shell `151.0.7922.34`. Driver memakai konfigurasi dasar CP7 dan fixture awal OW13a, profil, staged job, reorder dan Laundry/QC yang tercatat hash-nya. Semua permintaan aplikasi dibatasi ke loopback dan dijawab fixture. Jalur aktual database, Auth gabungan, stok, HPP, jurnal dan kredit tagihan memerlukan bukti tersendiri. [Konfigurasi browser](../../../../playwright.cp7-b-operator.config.ts) · [driver](../../../../tests/browser/cp7-b-operator.spec.ts).

| Bukti | Run / job / arsip | Lokasi hasil dan layar di arsip |
| --- | --- | --- |
| Kegagalan setup pertama. Port B 4178 berbeda dari origin 4176 yang disyaratkan App. | `43208745905 / 131150505979 / 13941030902` | [Receipt kegagalan pertama](FIRST_BROWSER_RUN.json) |
| Planner lulus. Job gabungan berakhir gagal pada tahap operator. | `43210650647 / 131157068674 / 13939889711` | `planner/results.json`, `planner/artifacts/` |
| Laundry lulus dengan patch yang sama. Job berakhir gagal saat selector catatan BS gagal menemukan textarea yang sudah berisi nilai. Snapshot memperlihatkan catatan tersimpan. | `43211906751 / 131161386815 / 13939959758` | `operator-after/results.json`, `operator-after/artifacts/`, [receipt kegagalan BS](THIRD_BROWSER_RUN.json) |
| BS lulus setelah driver memakai role textbox. | `43212478566 / 131163327456 / 13942381406` | `operator-after/results.json`, `operator-after/artifacts/`, [receipt final](FINAL_BROWSER_RUN.json) |

## Prasyarat yang masih terbuka

| Bagian | Bukti yang tersedia | Prasyarat berikutnya | Status |
| --- | --- | --- | --- |
| Planner pada backend gabungan | Sepuluh kasus browser fixture di atas | Salinan gabungan yang sah dengan jalur Planner dan akun Owner/Admin serta akun pembanding. | `BLOCKED` untuk login/server aktual |
| QC → WIP → Business Report `INCLUDED` | Fixture Admin menunjukkan WIP Rp288 → Rp180, FG Rp0 → Rp108 dan HPP penjualan Rp0. | Basis gabungan yang disetujui A, login nyata Owner, periode yang memuat tanggal QC, dan pencocokan buku besar serta stok dari transaksi yang sama. | `BLOCKED` untuk Auth dan pembandingan gabungan |
| Laporan aksesori S05 | Reproduksi dan patch A pada dua sesi PostgreSQL. | Salinan gabungan yang mendukung login nyata, patch terpasang, dan akun untuk memeriksa tampilan serta penolakan akses. | `BLOCKED` untuk login dan UI gabungan |

[Bukti QC fixture](https://github.com/Hanjay6688/-erp-garment-ux/blob/7b3373762ccc347a6374d2e1cdd482fc1d4d4f70/docs/cp7/review/shutdown-20261111/sku-43166466578-combined/qc-p19/README.md) · [bukti S05 dua sesi](https://github.com/Hanjay6688/-erp-garment-ux/tree/99dc1e1b922ef3e4d6365974cffcba168b2588e4/docs/cp7/review/shutdown-20261111/sku-43166466578-combined/closure-source/accessory-report-snapshot).

Keputusan penilaian tetap pada A dan penerimaan independen. Formal CP7 masih 5/16 pada pemeriksaan A terakhir.

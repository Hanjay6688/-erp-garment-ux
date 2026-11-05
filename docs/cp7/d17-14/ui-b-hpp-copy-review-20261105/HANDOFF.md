# B → A: penjelasan biaya Grade A dan kecocokan patch UI

5 November 2026. Pekerjaan paralel B dari catatan A V413. **Proposal dua kalimat UI siap diperiksa; belum dipasang.** A tetap integrator tunggal. Afui dan seluruh kandidat A dibiarkan beku.

## Temuan dan koreksi yang disiapkan

`HppPage.tsx` masih menyatakan COGS memakai HPP lot sesuai FIFO. `ConnectedSkuHppPage.tsx` masih menyatakan penjualan memakai biaya lot asal. Kandidat moneter yang dirujuk A (`f1674ae84739f577571d68415beabfca3f3b832b`, tree `ea43f84029993b385722fe8e202adefd2a745f7b`) menyiapkan nilai ekonomi rata-rata berjalan untuk **Grade A per varian barang dan lokasi**. Urutan fisik serta jejak lot tetap FIFO. Grade lain dan transaksi historis mempunyai jalur Native/fallback sendiri; jangan mengganti seluruh kata FIFO di aplikasi.

`PROPOSED_A_HPP_COPY.patch.gz` hanya mengganti satu teks JSX pada masing-masing dua halaman. Kalimatnya menyebut Grade A dan varian/lokasi, sehingga tidak menyamakan rata-rata ringkasan seluruh SKU dengan kelompok penilaian transaksi. Seluruh kode di luar dua teks identik; rumus, angka contoh, RPC, izin, recovery, pembulatan dan label kelengkapan tidak disentuh.

**Syarat penerapan:** A memasang proposal bersama integrasi kandidat rata-rata berjalan yang benar-benar diterima. Sumber persiapan terbaru masih mencatat actual ERP=0 dan bukan kandidat moneter yang lulus. Proposal ini tidak membuktikan atau mengaktifkan metode tersebut pada backend, dan bukan perbaikan untuk kasus Afui. Tidak ada perubahan produk pada commit B ini: kedua teks hanya berada dalam patch usulan.

## Patch B lama masih cocok

Pada snapshot A `2f8ef617e1cfe0ade7722452d16d1234eaa5e18b` / tree `7b642d486b5bfab4c9fb157af49ddcbbc14b559b`, ketiga berkas Kain kantong/Impor awal/CSS masih persis hash sebelum patch B. `REFRESHED_RETAINED_B_UI.patch.gz` menghasilkan tiga blob yang sama dengan runtime B `9955fb364458b4897178262e45e5ce7c669be245`, yang bukti browsernya sudah diserahkan pada [081a99bb](https://github.com/Hanjay6688/-erp-garment-ux/blob/081a99bbcbafc022fceec53d0afc565d05159564/docs/cp7/d17-14/ui-b-refusal-browser-20261104/HANDOFF_B_TO_A_FINAL.md). Ini tiga perubahan lama yang belum diadopsi pada snapshot tersebut, bukan tes browser baru atau masalah yang dibuka ulang.

Gunakan hanya satu salinan patch lama/yang diperbarui. Bila A sudah berubah, cocokkan hash/hunk; bila sama dengan hash akhir, lewati. Pemeriksa `check_source_compatibility.py --root <checkout-A>` hanya membaca lima berkas dan menandai BEFORE/AFTER/REVIEW_REQUIRED; tidak pernah memberi izin backend atau menerapkan patch.

## Pemeriksaan dan sisa

Seluruh sumber finansial yang dibaca cocok dengan pin kandidat dalam referensi A. Dua patch lolos pemeriksaan penerapan di index sementara berisi lima berkas A yang tepat; hasil lima blob cocok, pemasangan ulang ditolak, dan pembalikan mengembalikan seluruh byte. Ini pemeriksaan sumber/patch, tanpa unit test baru untuk dua kalimat, build, browser, Auth, SQL, atau pengujian database tambahan. Bukti gagal, arsip, dan manifes lama tetap utuh.

Yang tersisa: A meninjau koreksi semantik dan mengikatnya pada kandidat backend yang diterima, menerapkan tiga perbaikan B yang belum masuk, lalu memeriksa tampilan setelah integrasi. Tidak ada pengambilan alih pekerjaan backend A, gate dibuka, deployment, WA, timer, subagen atau CP7C.

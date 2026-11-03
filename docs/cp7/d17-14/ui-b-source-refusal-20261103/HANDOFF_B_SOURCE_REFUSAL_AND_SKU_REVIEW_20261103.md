# B — Penolakan sumber dan pemeriksaan UI SKU, 3 November 2026

Ada temuan baru yang terbukti pada UI Kain kantong: sesudah pembacaan ditolak 401/403, data stok/HPP yang sebelumnya berhasil dibaca masih berada di layar ketika provider login tetap AUTHORIZED. B menyiapkan dan menguji usulan perbaikannya tanpa mengubah cabang/worktree A. Perluasan pemeriksaan visual stok SKU pada sumber A yang sama juga selesai; tidak ditemukan cacat tampilan baru.

A tetap integrator tunggal. Basis pekerjaan adalah `astra-a/ui-sku-reader-prepared-20261103`, commit `8678feba7652d1d483536d1baf82135030dc3548`, tree `6ff52aa488c61051e3238fe6683f13c5c64ffca8`. B memakai branch/worktree tersendiri `astra-b/ui-source-revocation-review-20261103`. Patch produksi berada sebagai usulan di berkas `.patch`; semua perubahan sementara pada tiga berkas produk di worktree B dikembalikan ke byte basis sesudah pengujian. Tidak ada penerapan pada A, SQL, backend, hosted/Enteng, produksi, WA, CP7C, timer atau subagen.

## Temuan dan batas bukti

Delapan kasus terarah memakai komponen asli, recovery hook asli, dan Auth/RPC double yang dinyatakan. Identitas provider sengaja tetap AUTHORIZED; penolakan dikembalikan dari RPC tiruan, bukan pengujian HTTP/Auth nyata. Enam kasus Kain kantong gagal: muat ulang workspace, halaman periode berikutnya, serta pratinjau periode, masing-masing pada 401 dan 403. Fakta dari sumber sebelumnya tetap terlihat. Dua kontrol Impor data awal lolos karena workspace batch sudah ditutup saat memuat ulang.

Ini bagian yang belum dicakup oleh pengujian B terdahulu: 80 tampilan sebelumnya mencakup perubahan hak pada provider, bukan penolakan pembacaan saat provider belum berubah. Hasil 80 tampilan tetap merupakan bukti pada sumber dan cakupannya sendiri; jangan menyebutnya bukti penutupan temuan ini.

Percobaan pertama tetap disimpan. Dari enam kegagalannya, dua sudah membuktikan masalah produk; empat berhenti sebelum RPC karena fixture belum menyediakan browser Locks API, sehingga kontrol periode memang terkunci. Fixture kemudian memakai double kunci yang sama dengan tes halaman existing; tidak ada expected hasil, aturan produk atau timeout yang dilonggarkan. Percobaan kedua membuktikan keenam kegagalan produk. `FAILURE_CLASSIFICATION.json` memisahkan keduanya. Salinan sumber fixture pertama diberi label rekonstruksi dari pembalikan tepat perubahan fixture, bukan diklaim sebagai snapshot yang dibuat saat run pertama.

## Usulan perbaikan yang sudah diuji

`PROPOSED_A_POCKET_SOURCE_REFUSAL.patch.gz` menutup fakta tampilan segera pada AUTH_REQUIRED/FORBIDDEN di ketiga pembaca Kain kantong. Workspace, roll terpilih, pratinjau, formulir pembalikan dan pembatalan alokasi ditutup. Pesan server yang dinormalisasi tetap tampil. Penolakan yang sudah kalah dari pembacaan lebih baru tetap diabaikan oleh guard generasi yang sudah ada.

Parser, rumus, payload transaksi, predikat izin, handler penulis dan envelope/hook recovery tidak berubah. Penanda transaksi tertunda tidak dihapus dan transaksi tidak dikirim ulang otomatis oleh usulan ini. Kegagalan baca biasa tidak diperlakukan sebagai pencabutan izin. Ini usulan penutupan fakta UI pada jalur baca; bukan klaim bahwa seluruh jalur penulisan/perubahan akses di ERP telah diaudit.

`PROPOSED_A_COMBINED_UI.patch.gz` menyatukan usulan tersebut dengan tiga perubahan UI B yang sudah diuji sebelumnya: loading dua halaman, jumlah alokasi yang belum tersedia, dan foreground tombol primary. Cakupannya tetap tiga berkas: `ConnectedPocketFabricPage.tsx`, `ConnectedInitialImportPage.tsx`, `initial-import.css`. Semua 653 berkas `src` lainnya pada basis A tetap identik, termasuk lima berkas reader SKU dan perbaikan toolbar FG A. Urutan dan hasil hash penerapan tercatat pada `APPLICATION.json`.

| Pengujian lokal | Hasil dan cakupan |
| --- | --- |
| Baseline valid | 8 kasus; 6 gagal produk, 2 kontrol Impor lolos |
| Usulan penolakan sumber saja | 8 kasus terarah + 41 tes DOM existing lolos; pemeriksaan tipe lolos |
| Usulan gabungan tiga berkas | 50 tes lolos: 8 kasus penolakan sumber, 41 existing dan 1 regresi jumlah belum diketahui; pemeriksaan tipe lolos |
| Empat kontrol tambahan | 4 lolos pada byte produk gabungan yang sama; 8 kasus sebelumnya dilewati dalam run berfilter, bukan dihitung sebagai eksekusi baru |
| Total unik pada usulan gabungan | 54 kasus; jangan menjumlahkan 49 percobaan usulan awal sebagai 49 kasus unik tambahan |

Empat kontrol tambahan membuktikan respons 401/403 yang terlambat tidak menghapus hasil pembacaan baru yang berhasil, serta formulir pembatalan alokasi yang sudah terbuka ikut ditutup pada penolakan sumber. Durasi aktual tercatat pada receipt: gabungan 50 tes 14,469 detik, pemeriksaan tipe 19,595 detik, empat kontrol baru 4,434 detik. Ini waktu tes lokal, bukan latensi operasi ERP. Setelah setiap evaluasi, ketiga berkas produk dipastikan kembali identik dengan A. Tidak ada rangkaian database atau browser yang diulang.

## Pemeriksaan visual SKU tanpa pengulangan CI

Original A dari [run 41658644243](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/41658644243), job 125995665057, artifact 13239669983, tetap SUCCESS. ZIP 3.948.952 bytes, SHA-256 `11dd127cbd4d65b1c7ca71f3db87ce0d0c5fc87154c6f73c76812ad0c578a287`, 42 anggota, CRC cocok. Tidak ada perubahan pada arsip atau screenshot asal.

B memeriksa 32 identitas screenshot melalui empat contact sheet, lalu empat detail ukuran asli: known320-details, operations390, unknown1440 dan pending390. Ini perluasan pemeriksaan penulis, bukan klaim semua 32 PNG dilihat satu per satu pada ukuran asli. Teks pilihan urutan dan penjelasan toolbar terbaca; biaya belum diketahui tidak menjadi nol; mode tanpa hak keuangan tidak memperlihatkan angka uang. Tidak ada temuan baru pada pemeriksaan ini. Hasil pengukuran A yang dipakai kembali: 32 kasus, empat lebar 320/390/768/1440, kontras minimum 5,208347819737491, tanpa overflow. Hash 32 PNG ditambahkan pada `SKU_RETAINED_VISUAL_REVIEW.json`. B tidak menjalankan browser identik lagi.

[Pratinjau desktop/HP](https://chatgpt.com/library?file_id=libfile_35ef1610cad08191a309e911183969f4&account_id=personal) tersedia. [Original A yang sudah disimpan](https://chatgpt.com/library?file_id=libfile_21ac2d0b4f90819194639dafd32ccb73&account_id=personal) dipakai kembali; tidak dibuat salinan arsip kedua. [Arsip bukti baru B](https://chatgpt.com/library?file_id=libfile_b02a3b8c6da4819199b9b4681b480833&account_id=personal) mempertahankan hasil pertama, hasil sebelum/sesudah, serta receipt pengujian. Kode dan patch disimpan di Git.

## Penerapan oleh A

Jika tiga berkas UI A masih seperti `8678feba`, gunakan usulan gabungan satu kali. Jika patch UI terdahulu dari `d3165377af56191ee51a44ce6dbaaf9fb5cbf1c4` sudah diterapkan, gunakan patch penolakan sumber saja. Kedua cara menghasilkan blob Kain kantong yang sama, sudah dibuktikan pada indeks sementara tanpa menyentuh checkout A. Jangan menerapkan usulan gabungan dan patch UI lama sekaligus atau merge seluruh branch B.

Patch disimpan dengan gzip untuk mempertahankan byte konteks unified diff, termasuk spasi pada baris kosong. Dekompresi lebih dahulu sebelum memakai git apply. Setelah penerapan, A mencocokkan sumber kandidat integrasi, meninjau dampak penjagaan fakta UI, serta menjalankan pemeriksaan integrasi/Auth yang sesuai. Tes baseline bersifat counterexample dengan nama `_BEFORE.case.tsx` dan hanya berjalan lewat konfigurasi eksplisit; tidak dimasukkan ke glob tes produk default. Setelah patch diterapkan pada checkout kandidat, `vitest-combined.config.mjs` menjalankan seluruh 54 kasus. SOURCE.json mengikat berkas usulan, fixture dan bukti; sumber produk pada commit laporan B tetap basis A karena patch belum diadopsi.

Yang masih terbuka: penerimaan dan penerapan usulan oleh A, pengujian Auth/backend/full App kandidat terbaru, dan audit independen. Tidak ada penerimaan angka keuangan resmi atau perbaikan cost lineage SKU backend dalam paket ini. Formal tetap 5/16, actual Auth/SQL/full App baru 0, `production_go=false`, `independent_acceptance=false`.

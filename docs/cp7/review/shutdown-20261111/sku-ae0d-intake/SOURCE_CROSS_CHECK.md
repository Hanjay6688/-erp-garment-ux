# Pemeriksaan sumber untuk kelanjutan SKU dan Global

## Sequence saat setup

Pemindaian skrip di tree BEDA menemukan 137 berkas dengan pemanggilan `strict_group`. Perbandingan sequence dari sebelum grup ke awal kasus muncul di jalur uang SKU dan turunan Native27. Jalur uang yang dipakai BEDA mengukur seed dan ID audit pada cursor yang menjalankan setup. [Pemeriksa setup BEDA](https://github.com/Hanjay6688/-erp-garment-ux/blob/beda75853d9cb698ec912639002b3e4bd1ec52cf/scripts/current-sku-automatic-composite-preparation/setup_sequences.py)

Native27 menjalankan Native7 beserta transaksi pembuktian penolakan pembatalan, yang melakukan seed bila pengguna kosong dan commit sebelum snapshot untuk lima kasus biaya. Lima kasus biaya bergantung pada prasyarat tersebut. Bila kelanjutan dimulai dengan database baru, prasyarat itu perlu dibentuk kembali dan urutan audit perlu diobservasi sebelum membandingkan awal kasus. Bukti Native27 yang sudah disimpan tetap terikat ke urutan awalnya. [Derivasi Native27](https://github.com/Hanjay6688/-erp-garment-ux/blob/beda75853d9cb698ec912639002b3e4bd1ec52cf/scripts/current-sku-managed-recovery-native27-qualification/derive.py)

Pada persiapan Global yang tersimpan, pemeriksaan awal memakai katalog aktual SKU sebagai input. Jalur S03/S05 `native_sku.py` memanggil grup ketat tanpa memakai pembanding sequence awal lintas-grup tersebut. Ini pemeriksaan jalur sumber dan bukti lama. Global dan S03/S05 tetap perlu kualifikasi aktual yang diwajibkan masing-masing.

## Pemeriksaan sebelum run mahal

Pada checkout tepat BEDA, tes sumber lokal awal mencatat 32 kegagalan assertion/subtes dan 7 error. Tes menjalankan fixture sumber tertutup pada checkout yang sudah punya binding aktif atau membaca donor lama lewat berkas checkout saat ini. Sebagian kontrol juga membutuhkan berkas historis yang belum ada lokal.

[Patch tes](SKU_BEDA_SOURCE_CONTROL_CONTEXT.patch) memberi kontrol penolakan nilai tertutup sendiri, membaca prasyarat Mandor lama dari commit yang terikat, dan memeriksa kontrol seluruh sumber dalam mode yang sesuai dengan kandidat. Tujuh berkas tes dan pin tes di `SOURCE.json` berubah. Patch disiapkan terhadap BEDA untuk penilaian penerus. Kandidat aktif menggunakan versi GitHub yang sudah terbit.

Setelah patch, 166 metode tes dicoba dan 0 assertion gagal. Empat kontrol semula masih memerlukan input luar. Blob `complete_original_io.py` lama diambil dari commit `92a37609` dengan Git blob `d91c3b99`; enam kontrol `test_report_io.py` lalu lulus. Tiga prasyarat tes lokal tersisa adalah `POSTGRES_ORIGINALS.json` untuk kontrol advisor, checkout `090b85d3` untuk kontrol ancestor, dan objek commit historis `a5944f25` untuk pengujian pembaca artefak. Isi helper historis terakhir sudah dibaca langsung, dengan Git blob `57129b07`. Kontrol ekonomi browser Node lulus 8/8. Semua ini pemeriksaan sumber dan fixture.

## Bukti B yang dipakai ulang

21 berkas yang mengikat uji B cocok di AE0D dan BEDA. Seluruh 29 definisi lengkap cocok dengan katalog diagnostik aktual AE0D dari artefak 13940756296. Ini menguatkan penggunaan kembali uji terarah moving average, stok fisik WIP/FG, dan arsip/filter stok laporan. Pembuktian valuasi WIP/FG resmi dan laporan `INCLUDED`, replay invoice pemasok pada gabungan, serta katalog terminal BEDA masih terbuka. [Receipt](B_52B6_ACTUAL_AE0D_SCOPE_RECHECK.json) · [Handoff B](https://github.com/Hanjay6688/-erp-garment-ux/blob/52b6cf93dd85bc76a713e29beb5ae6d91247f9c7/docs/cp7/review/sku-snapshot-report-focused-20261112/HANDOFF.md)

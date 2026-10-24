# OW-06 — satu transfer supplier ke beberapa penerimaan

Status 24 Oktober 2026: Astra A mengambil estafet Claude. Mesin pembayaran, Auth/race, layar desktop/HP, alokasi lintas halaman, pemasangan current A/B dan pemulihan transfer sesudah dipakai sudah mempunyai bukti penulis PASS. Rinciannya di bagian terbaru di bawah. Ini belum penerimaan audit independen; jumlah formal tetap5/16. [Checkpoint awal](CHECKPOINT.json) tetap disimpan sebagai sejarah.

Dasar owner D17-14 butir5: satu transfer dialokasikan ke beberapa penerimaan/tagihan, jumlah alokasi sama dengan pembayaran, kas keluar tercatat sekali, pembatalan/koreksi konsisten. Tidak ada FIFO, rekening perantara atau angka kebijakan baru.

Implementasi: `scripts/cp7_supplier_transfer/`, kini terhubung ke layar dan pemasang current `scripts/cp7_current_installation.py`. Pada checkpoint awal modul masih terisolasi. Pemasang tahap memverifikasi seluruh OW-05 dahulu; hanya sembilan perubahan fungsi terdahulu yang diturunkan dengan penggantian satu lokasi yang dihitung. Metadata/izin fungsi lama tetap. Seluruh22 kelompok katalog dibandingkan penuh; tidak menulis ulang definisi lama supaya pemeriksa lolos.

- Satu induk transfer dan alokasi privat. Tiap penerimaan mempunyai fakta pembayaran Native sendiri untuk utangnya; hanya satu jurnal Native debit utang dan kredit kas bagi seluruh transfer. Tidak ada jurnal bank per anak atau saling hapus tersembunyi.
- Penulis Native tetap memeriksa sisa utang kini dan kredit pada tanggal bayar, sumber, rekening dan status. Delegasi jurnal hanya lewat kapabilitas privat untuk backend/transaksi/aktor/permintaan/induk yang sama.
- Balik seluruh transfer melalui induknya; anak tidak boleh dibalik/diedit sendiri. Koreksi membalik induk lama dan membuat penerus, mempertahankan tanggal dan sejarah. Pergeseran tanggal ekonomi mengikuti pola koreksi supplier yang sudah ada.
- Pembaca pembayaran dan pembuka sumber jurnal mengenali induk. Pemeriksa integritas Native memeriksa uang induk serta ketepatan seluruh anak; kontrol korupsi satu sen harus0→1→0.
- Kunci bersama sebelum request dan baca ulang hak sesudah menunggu/replay. Baris lama memakai NOWAIT ketika urutan penulis lama bisa berlawanan. Seluruh kegagalan harus nol efek.

Uji checkpoint: enam kasus baru (uang400+600=1000; penolakan atomik/replay; pembalikan induk; empat koreksi berturut-turut; bank kosong/gagal posting terakhir; detektor dan penolakan pencopotan sesudah dipakai), ditambah empat oracle pembayaran tunggal lama tanpa mengubah berkas/nominal/expected.

Pemeriksaan lokal hanya lulus kompilasi tipe Native, bentuk masukan, jumlah alokasi dan penolakan draf tanpa kapabilitas. Tidak dihitung sebagai bukti jurnal Native. Hasil CI dan kegagalan pertama dicatat terpisah setelah selesai.

Batas tetap: tidak menyentuh main, kandidat auditor55c885d1, Enteng, database hosted/produksi atau WA nyata. CP7C formal belum mulai. Laporan sesudah kredit pelanggan masih BLOCKED di OW-08.

Hasil final: f764c508, run39808778963/job119929044980, enam kontrol grup dan empat oracle lama semuanya PASS. Seluruh22 kelompok, pencopotan sebelum dipakai, pengembalian CP6 dan advisor lulus. Dua kegagalan pemasangan asli tetap disimpan; satu run versi lama masih dilaporkan berjalan pada persiapan alat dan tidak dipakai sebagai bukti. Claude mengambil alih sisa OW06 sesuai handoff; jangan menambah hitungan selesai menjadi6 sebelum layar, hak/race, perjalanan nyata serta pemulihan sesudah dipakai terbukti.

## Lanjutan oleh penulis A (23 Okt 2026)

| Uji | Kepala | Run/job | Hasil |
|---|---|---|---|
| Login Auth nyata, hak dan rebutan (Auth4) | `b9456b5a` | 39825964400 percobaan 3 / 120015131365 | **4/4 PASS**. Artefak `cp7-ow06-real-auth4`, 1.633.962 byte, sha256 `35d0e3453989303e55456c1723bbf75562e170ef9597cee7bcf62997d95d68a4`. Percobaan 1 (`33581706`) 1/4: tiga kesalahan uji (perbandingan teks angka, kode penolakan sesudah menunggu, peran STAFF tidak aktif), bukti `auth4-33581706-first-failure.json`; percobaan 2 berhenti di langkah menyalakan database uji |
| Browser desktop + HP (Browser2) | `eda58db5` | 39831356518 | Berhenti di langkah menyalakan database uji (server CI). Dua kegagalan sebelumnya karena uji (`browser2-*-first-failure.json`) sudah dibetulkan; dijalankan ulang |
| Browser desktop + HP (Browser2) | `77a48da6` | 39835578930 | Semua angka uang benar (bank, bayar per penerimaan, koreksi, pembatalan); gagal di satu harapan uji: layar sengaja mengurutkan baris menurut kode penerimaan, uji mengira urutan ketik. Uji dibetulkan, bukti `browser2-77a48da6-allocation-order-failure.json`; dijalankan ulang |

| Browser desktop + HP (Browser2) | `d8b0164e` | 39884070148 / 120188022797 | **2/2 PASS**: bank -1000 → -750 → 0, bayar per surat jalan 400+600 → 250+500, balasan hilang pulih dengan UUID sama (desktop), lebar HP 390 tanpa geser samping. Bukti `browser2-d8b0164e-pass.json` |

Catatan di atas adalah posisi 23 Oktober. Bukti berikut memperbarui bagian pemulihan dan pemasangan, tanpa menghapus kegagalan pertama atau menaikkan hitungan penerimaan formal.

## Bukti current A/B, 24 Oktober 2026

| Batas | Bukti penulis terverifikasi |
|---|---|
| Mesin pembayaran current | [Native62](../ow15/owner62-28abdeef-pass.json) mempertahankan seluruh ID keluarga transfer dan oracle uang lama pada gabungan A/B. |
| Hak/rebutan/login nyata | [Auth8](../ow15/owner-auth8-28abdeef-pass.json) mencakup empat ID OW06; hak diperiksa sesudah wait/replay. |
| Pemasangan current | [Current installer](../ow15/current-install-28abdeef-used-restore-pass.json): inventaris resmi, seluruh22 kelompok katalog, inverse pra-pakai, penolakan pencopotan sesudah dipakai, full backup/restore dan tipe hasil generator. |
| Transfer sesudah full restore | [Group restore](../ow15/current-transfer-aea44fa9-used-restore-pass.json):400+600, seluruh pembacaan sama, replay tanpa efek, empat koreksi beserta tanggal/sejarah, inverse induk mengembalikan kas neto0; stok/HPP tetap. |
| Pilihan penerimaan lintas halaman | [Desktop dan HP390](../ow15/transfer-pages-535c97af-final-ui-pass.json), head535c97af/run40061613739:31penerimaan25+6; pilihan halaman1/2 bertahan;400+600→250+500→inverse0. Sebanyak29penerimaan lain tidak dibayar. Desktop memulihkan balasan committed yang hilang dengan UUID sama. |
| Tampilan setelah pembalikan | Kedua perjalanan menunggu refresh selesai, memeriksa status sudah dibalik, jurnal pembalik dan kedua penerimaan, serta tombol transfer baru siap. Gambar pilihan halaman2 dan tampilan akhir turut diperiksa. |

Setiap receipt current di atas mempunyai CP6/advisor dan lima gate paket PASS;
run browser/Auth mengembalikan Auth dan database uji ke keadaan awal. Bukti
sebelumnya `transfer-pages-28f73c0f-pass.json` tetap disimpan: uang/aksi sudah
PASS, tetapi gambar akhir dapat mendahului refresh; penguatan535c97af menutup
batas pengamatan itu tanpa mengubah produk atau oracle lama.

Batas yang masih terbuka adalah penerimaan auditor atas seluruh scope dan
kualifikasi satu kandidat lengkap, termasuk perjalanan seluruh uang P21.
Restore group OW06 tidak otomatis membuktikan setiap perjalanan A/B.
Integrasi resmi/main/kandidat audit lama tetap; `production_go=false`.

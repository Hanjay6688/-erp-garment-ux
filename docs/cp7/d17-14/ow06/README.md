# OW-06 — satu transfer supplier ke beberapa penerimaan

Checkpoint mesin pembayaran, pembatalan dan koreksi lulus10/10 pada database sekali pakai: [bukti dan batas](CHECKPOINT.json). Ini belum menyelesaikan OW-06: layar nyata, hak/race melalui login, pemulihan sesudah dipakai dan pemasangan bawaan masih menjadi pekerjaan Claude. Jumlah pekerjaan selesai tetap5/16.

Dasar owner D17-14 butir5: satu transfer dialokasikan ke beberapa penerimaan/tagihan, jumlah alokasi sama dengan pembayaran, kas keluar tercatat sekali, pembatalan/koreksi konsisten. Tidak ada FIFO, rekening perantara atau angka kebijakan baru.

Implementasi terisolasi: `scripts/cp7_supplier_transfer/`. Tidak diimpor pemasang bawaan atau layar. Pemasang baru memverifikasi seluruh OW-05 dahulu; hanya sembilan perubahan fungsi terdahulu yang diturunkan dengan penggantian satu lokasi yang dihitung. Metadata/izin fungsi lama tetap. Seluruh22 kelompok katalog dibandingkan penuh; tidak menulis ulang definisi lama supaya pemeriksa lolos.

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

Belum selesai: Browser2 lulus, pemulihan sesudah dipakai (P21) dan sambungan ke pemasang bawaan.

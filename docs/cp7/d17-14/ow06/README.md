# OW-06 — satu transfer supplier ke beberapa penerimaan

Checkpoint yang sedang diselesaikan: mesin pembayaran, pembatalan dan koreksi di database sekali pakai. Ini belum menyelesaikan OW-06: layar nyata, hak/race melalui login, pemulihan sesudah dipakai dan pemasangan bawaan masih menjadi pekerjaan Claude. Jumlah pekerjaan selesai tetap5/16.

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

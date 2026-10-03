# Kontrol submenu dan koreksi seluruh transaksi — keputusan owner, 3 Oktober 2026

Ini bagian wajib CP7. Permintaan owner mencakup seluruh pergerakan stok, pembayaran, penerimaan uang, biaya, dan pergerakan lain; cakupannya tidak terbatas pada koreksi nota yang baru selesai. Seluruh tombol dan jalur di bawah harus mempunyai bukti sebelum dianggap selesai. Hasil stress test backend pada jalur yang sudah ada tidak membuktikan bahwa semua jalur edit telah tersedia.

## Kepala setiap submenu

- Cari dokumen dan browse daftar, dengan batas akses pengguna yang sedang aktif.
- Filter yang jelas dan bisa dikembalikan ke semua pilihan.
- Urutkan dengan cakupan yang terlihat. Urutan satu halaman tidak boleh diberi label seolah mengurutkan seluruh database. Urutan tampilan tidak mengubah waktu kejadian, saldo resmi, identitas baris, atau urutan buku yang sengaja disimpan owner.
- Pilihan pencarian dan filter tidak boleh menyembunyikan bahwa data masih belum dimuat, sudah kedaluwarsa, atau ditolak aksesnya.

## Setiap entry transaksi

- Tindakan Edit dan Hapus/Batalkan mudah ditemukan pada dokumen sumber, mengikuti hak akses, status, versi, dan penguncian hasil transaksi yang belum pasti.
- Draft: gunakan writer draft yang dimiliki modul untuk edit atau hapus; jangan membuat panggilan langsung ke tabel.
- Transaksi tercatat resmi: edit melalui koreksi/pengganti yang menjaga riwayat asli. Hapus melalui pembatalan/pembalikan bisnis. Jangan menghapus riwayat posted dengan SQL DELETE.
- Mutasi stok, jurnal, HPP dan ringkasan pembayaran yang dihasilkan dokumen lain: buka transaksi sumbernya. Jangan membuat pembalikan kedua dari baris turunannya.
- Edit yang memengaruhi beberapa buku harus atomik. Memanggil beberapa writer terpisah dari browser tidak cukup untuk disebut edit atomik.
- Pembatalan dari pangkal yang masih punya pemakaian lanjutan: tampilkan penghalang yang berasal dari data yang berhak dibaca, nomor dokumen/jenisnya jika tersedia, halaman untuk membereskannya, dan urutan dari ketergantungan terakhir ke asal. Jangan menebak nomor sumber atau memberi pesan umum “gagal”.
- Pengecekan ulang versi, sumber, akses dan ketergantungan di backend tetap wajib saat perintah dikirim. Daftar penghalang di UI bukan izin untuk melewati guard.
- Balasan hilang: pertahankan UUID/payload yang sama, kunci writer, lalu baca atau reconcile. Pembacaan baru boleh menampilkan fakta terkini tanpa membuka writer.
- Penolakan maupun kegagalan di langkah terakhir harus meninggalkan semua stok, uang, utang/piutang, HPP, dan jurnal dalam keadaan konsisten. Laporan harus menyatakan perubahan ekonomi/historis sesuai aturan periode yang dimiliki backend.

## Daftar rollout dan bukti yang harus ditutup

| Kelompok | Jalur yang sudah dimiliki | Sisa mandat owner |
| --- | --- | --- |
| Penjualan/nota | Edit draft, batalkan draft, koreksi posted atomik, pembalikan penjualan; Native40 dan P11 dimiliki | Kepala submenu seragam; tindakan jelas; penghalang pembayaran/retur beserta arah tindak lanjut; uji kembali UI pada sumber baru |
| Pembayaran/retur pelanggan | Penambahan dan pembalikan Native, current Auth, expected version dan UUID recovery | Jalur edit pembayaran/retur tersendiri jangan dianggap selesai dari adanya tombol pembalikan; telusur, urutan, filter, dan tindakan pada setiap entry |
| Penerimaan/invoice supplier/nama bahan | Koreksi penerimaan32 yang sudah terintegrasi; draft, pembatalan dan name-only writer dimiliki | Tunggu Claude menyelesaikan bagiannya; compose kontrol dan blocker, jangan menimpa WIP atau menggandakan koreksi final-price miliknya |
| Hitung bahan/penyesuaian FG | Draft save/edit/delete, post dan reverse | Kontrol seragam; edit posted melalui jalur pengganti yang dimiliki atau tandai belum tersedia; ketergantungan/saldo kronologis harus terlihat |
| Transfer bahan, aksesori, kain kantong, konversi | Jalur Native masing-masing dan pengaman ketergantungan | Inventaris per-entry edit/hapus dan seluruh koreksi historis; jangan menganggap reversal sama dengan fitur edit penuh |
| Potong/bagi/ambil/sewing/laundry/QC/BS/rework | Draft dan writer lifecycle CP5/CP6; beberapa reversal dengan guard pemakaian/claim | Penghalang bernama dan arah halaman; jalur edit setiap sumber serta pembatalan dari ketergantungan akhir; lindungi snapshot pola dan lineage campuran |
| Absensi/payroll/kasbon/kas lain/scrap | Writer dan pembalikan yang dimiliki masing-masing | Edit atomik yang benar-benar tersedia, filter/urutan, dampak uang/biaya/nota mandor dan akses terkini |
| Buku FG, bahan, kas, piutang, jurnal, HPP, laporan | Reader resmi, saldo restated dan lineage/source dimiliki | Buka/edit/batalkan dokumen sumber, tanpa menghapus baris hasil hitung; urutan visual tidak menghitung ulang saldo dari subset |
| Master, pengaturan, reminder, planning, arsip | Writer sumber, immutable snapshots, CURRENT/STALE dan Original recovery | Kepala submenu dan browse/filter/urutan; snapshot historis tidak diedit; master yang terpakai diberi penghalang atau penonaktifan sesuai domain |

## Uji penerimaan

Nomor, identitas, tanggal asal termasuk mikrodetik, harga/jumlah persis, versi besar, penolakan hak akses saat ini, balasan lama, UUID replay, perintah paralel, batas saldo berjalan, periode tutup, dan laporan sebelum/sesudah wajib dicocokkan pada jalur masing-masing. Sertakan satu tahun riwayat, multi-lot/multi-baris, pemakaian lintas tahap, partial return, pembayaran/kredit yang sudah dipakai, serta kegagalan langkah terakhir. Existing Native40/32 dan delapan paket F03 tetap bukti sumber terdahulu; perubahan UI berikutnya harus mempunyai bukti sumber baru. Seluruh rollout belum selesai.

CP6 HOLD. audit_complete=false; production_go=false. **VENI. VIDI. VICI. ERP. Reliable data adalah dewa. Keuangan—termasuk laporan—stok, dan HPP adalah raja.**

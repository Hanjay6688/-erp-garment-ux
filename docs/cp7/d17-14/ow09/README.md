# OW-09 — urut dan saring berlaku untuk seluruh data

Status 24 Oktober 2026: kedelapan layar mempunyai bukti penulis pada gabungan ERP current, termasuk lintas halaman dengan login nyata desktop/HP. Browser19 sebelumnya mencakup kas33baris; InvoiceHistory2 membuktikan dua riwayat31baris; OwnerLists10 menutup lima daftar sisanya. Rincian dan batas bukti di bawah. Ini belum penerimaan audit independen atau izin produksi; jumlah formal tetap5/16.

Keputusan owner D17-16: "Urut/saring seluruh data: berlaku pada seluruh hasil pencarian, termasuk lintas halaman; angka
total dan ekspor mengikuti filter yang sama."

## Yang berubah per layar

| Layar | Yang berubah |
|---|---|
| Kas & Bank (daftar jurnal kas) | Cari, status jurnal dan urutan berlaku untuk seluruh periode. Ada baris "jumlah jurnal yang cocok" (debit, kredit, bersih) yang ikut saringan. Saldo resmi periode di atasnya tetap untuk seluruh periode. |
| Pembayaran invoice (riwayat) | Cari, status dan urutan berlaku untuk seluruh riwayat pembayaran invoice itu. |
| Retur invoice (riwayat) | Cari juga menemukan SKU, lot, gudang dan catatan baris di semua halaman; status dan urutan untuk seluruh riwayat. |
| Nota FG tersimpan | Status dan urutan berlaku untuk seluruh nota yang cocok. |
| Penyesuaian barang jadi (riwayat dokumen) | Status dan urutan berlaku untuk seluruh dokumen. |
| Kartu mutasi barang jadi | Jenis mutasi dan urutan berlaku untuk seluruh mutasi posisi itu; pilihan jenis mutasi sekarang lengkap. Saldo per baris tetap dari seluruh riwayat. |
| Hitung fisik bahan (riwayat dokumen) | Status dan urutan berlaku untuk seluruh dokumen. |
| Nota Ambil Aksesori | Dulu hanya 50 nota terbaru, saring status hanya di daftar yang tampil. Sekarang cari, status dan urutan berlaku untuk seluruh riwayat nota, ada tombol "Nota sebelumnya / Nota berikutnya", dan angka "… nota cocok" adalah jumlah seluruh nota yang cocok. |

Di semua layar ini tulisan kecil di bawah alat cari berbunyi "Filter dan urutan berlaku untuk seluruh hasil, termasuk
halaman lain; jumlah hasil mengikuti filter yang sama", dan pilihan urutan bernama "Urutkan semua hasil". Mengganti
urutan, status atau pencarian selalu kembali ke halaman pertama. "Nama / nomor A–Z" mengurutkan angka di dalam nomor
menurut nilainya (NA-2 sebelum NA-10); nomor yang sama diurutkan menurut urutan standar.

Ekspor: kedelapan layar ini tidak punya tombol ekspor, jadi tidak ada ekspor yang diubah atau dibuat.

## Cara pemasangannya: sebagai tahap

Versi pertama mengubah berkas SQL dasar CP7 dan harus dibatalkan, karena berkas dasar itu dikunci sidik jarinya untuk
semua tahap berikutnya (pelajaran E25j2). Sekarang perubahan dipasang sebagai satu tahap tersendiri
(`scripts/cp7_ow09_lists`) di atas tahap-tahap sebelumnya yang sudah lulus (sejak 23 Okt di atas tahap OW-12a, sesuai
urutan rantai OW-15; tidak ada tahap lain yang menyentuh delapan fungsi baca ini). Artinya:

- Berkas SQL dasar CP7 tidak diubah sama sekali (sidik jarinya tetap `e7701eaa`).
- Tahap mengganti delapan fungsi baca yang sudah terpasang dengan potongan pengganti yang dihitung persis: setiap
  potongan lama harus ada tepat satu kali, kalau tidak pemasangan berhenti. Tidak ada tabel, hak akses atau data yang
  berubah, dan tahap bisa dicopot kembali ke keadaan semula persis.
- Pemanggilan lama (tanpa pilihan baru) tetap menghasilkan jawaban yang sama persis; ini diuji berdampingan dengan versi
  sebelum perubahan.
- Hak akses tidak berubah: pengguna tanpa izin tetap ditolak sebelum daftar dibaca.

## Yang sudah diuji di komputer penulis

- Kedelapan fungsi baca di database percobaan sekali pakai: setiap kombinasi urutan, status/jenis dan pencarian,
  halaman demi halaman, plus jawaban lama dibandingkan dengan versi asli. Lulus. Uji ini sengaja dirusak tiga kali dan
  langsung gagal, jadi uji ini memang memeriksa.
- Latihan pemasangan dengan susunan peran seperti di Supabase: pasang, periksa, copot kembali persis. Lulus.
- Uji layar Nota Ambil Aksesori (36 uji) dan pemeriksaan tipe kode: lulus.

## Yang belum terbukti

1. **Uji di database ERP lengkap belum jalan.** Workflow yang harus dijalankan: `cp7-ow09-native.yml` (8 kasus). Sebelum
   lulus, perubahan layar belum digabung ke cabang utama kerja.
2. **Layar butuh tahap ini terpasang.** Uji browser lain yang memasang CP7 tanpa tahap ini (penjualan, kas, barang jadi,
   sumber transaksi, nota aksesori, OW-04) akan ditolak di layar-layar ini sampai tahap ini masuk ke rantai pemasangan
   mereka (pekerjaan OW-15).
3. **Catatan sidik jari uji browser OW-04** untuk `src/SalesReturnPanel.tsx` dan dua berkas uji penjualan perlu
   diperbarui saat penggabungan; tidak saya ubah.

Risiko lama yang tidak diubah: daftar berhalaman ini belum membawa tanda isi di kursor (aturan B8e), jadi baris yang baru
tercatat di antara dua perpindahan halaman bisa membuat satu baris bergeser, sama seperti sebelumnya.

## Catatan teknis

Kunci baru (opsional) per pembaca; tanpa kunci ini jawabannya sama persis. Bila salah satu dikirim, jawaban membawa gema
pilihan (`list`; kas juga `sums`, kartu FG juga daftar jenis, aksesori `history_page`).

| Pembaca | Kunci baru |
|---|---|
| `cp7_finance.analysis` (Kas & Bank) | `entry_q`, `entry_status`, `entry_order` |
| `cp7_sales.cash_workspace` | `payment_q`, `payment_status`, `payment_order` |
| `cp7_sales.return_workspace` (kind RETURNS) | `history_q`, `history_status`, `history_order` |
| `cp7_payroll.note_workspace` (NOTES) | `status`, `order` |
| `cp7_fg.adjust_workspace` | `status`, `order` |
| `cp7_fg.corrected_ledger` | `movement_type`, `order` |
| `cp7_material.count_workspace` | `status`, `order` |
| `erp.get_accessory_issue_workspace_v1` | `history_status`, `history_order`, `history_offset`, `history_limit` (1–50) |

`order` = `SOURCE` | `LABEL_ASC` | `LABEL_DESC`; seri dipecah dengan urutan standar lama yang berakhir pada id. Uji:
`tests/cp7/families/ow09-record-lists.test.ts` (memakai fungsi pengganti milik tahap itu sendiri),
`scripts/cp7_ow09_lists/cases.py` (database lengkap), uji layar `src/*.dom.test.tsx` terkait.

## Bukti current A/B, 24 Oktober 2026

| Layar | Jumlah dan halaman yang benar-benar diuji | Receipt penulis |
|---|---|---|
| Kas & Bank |33jurnal,25+8; jumlah/saldo yang mengikuti filter diuji terpisah dari saldo resmi periode | [Browser19](../ow15/owner-browser19-7b26351f-pass.json) |
| Riwayat pembayaran dan retur invoice | Masing-masing31,25+6; filter30,25+5 | [InvoiceHistory2](../ow15/invoice-history-6c3e5a9e-pass.json) |
| Nota FG tersimpan |31,25+6; filterVOID30,25+5 | [OwnerLists10](../ow15/owner-lists-fefb20f3-pass.json) |
| Penyesuaian barang jadi |31,25+6; filterPOSTED29,25+4; satu dokumen sudah dibalik dan satu draft tetap ada | OwnerLists10 |
| Kartu mutasi FG |32,25+7; filter jenis dominan31,25+6; saldo prefix setiap mutasi mengikuti seluruh sejarah, saldo akhir39 | OwnerLists10 |
| Hitung fisik bahan |31,25+6; filterDRAFT30,25+5 | OwnerLists10 |
| Nota Ambil Aksesori |56,50+6; filterDRAFT55,50+5, sesuai ukuran halaman asli50 | OwnerLists10 |

InvoiceHistory2 dan OwnerLists10 memeriksa UUID dari tabel Native, nomor serta
urutan DOM, urut global, maju/mundur, pencarian baris yang sebelumnya di
halaman2, hasil kosong, dan Browse semua. Seluruh perjalanan baca mempertahankan
semua baris bisnis dan sequence, dengan0writerRPC. Login nyata desktop/HP390,
Auth kembali0000, DB sisa0, console0, CP6/advisor serta lima gate paket PASS.
Gambar kartuFG/aksesori HP dan dokumenFG desktop ikut diperiksa.

First failure invoicea17 dan daftar23ec tetap disimpan pada receipt masing-masing.
Perbaikan hanya menata import fixture invoice dan menambahkan satu pembalikan
Native sah untuk menyediakan dua jenis mutasi kartu; SQL produk, kasus lama
dan oracle uang/stok/HPP tidak diubah. Bukti ini menutup celah lintas halaman
yang sebelumnya dicatat pada delapan daftar. Penerimaan scope lengkap oleh
auditor, kualifikasi satu kandidat dan arsip CP6 tetap pekerjaan terpisah;
`production_go=false`.

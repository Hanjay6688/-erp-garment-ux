# OW-09 — urut dan saring berlaku untuk seluruh data

Kedelapan layar sudah dikerjakan, termasuk Nota Ambil Aksesori, dan lulus semua uji di komputer penulis. Yang belum:
uji di database ERP lengkap (CI) belum dijalankan, jadi belum terbukti di sana. Perubahan layar baru boleh digabung
setelah uji itu lulus.

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

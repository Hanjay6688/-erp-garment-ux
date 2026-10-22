# OW-09 — urut dan saring berlaku untuk seluruh data

Tujuh dari delapan layar sudah selesai dan lulus uji di komputer penulis: urutan, saringan status/jenis, dan pencarian
sekarang dikerjakan pada seluruh data, termasuk halaman berikutnya, dan angka jumlah ikut saringan yang sama. Layar
Nota Ambil Aksesori belum, karena datanya dibaca oleh bagian sistem lama yang hanya mengirim 50 nota terbaru; layar itu
tetap jujur menulis "hanya halaman yang tampil". Uji lengkap di server uji otomatis (CI) belum dijalankan.

Keputusan owner D17-16: "Urut/saring seluruh data: berlaku pada seluruh hasil pencarian, termasuk lintas halaman; angka
total dan ekspor mengikuti filter yang sama."

## Yang berubah per layar

| Layar | Hasil | Yang berubah |
|---|---|---|
| Kas & Bank (daftar jurnal kas) | Selesai | Cari, status jurnal dan urutan berlaku untuk seluruh periode. Muncul baris "Jumlah jurnal yang cocok: debit · kredit · bersih" yang ikut saringan. Kartu saldo di atasnya (saldo awal, akhir, debit, kredit periode) tetap seluruh periode, karena itu saldo resmi, bukan jumlah daftar. |
| Pembayaran invoice (riwayat) | Selesai | Cari (nomor, referensi, catatan, rekening), status dan urutan berlaku untuk seluruh riwayat invoice itu. |
| Retur invoice (riwayat) | Selesai | Cari sekarang juga menemukan SKU, lot, gudang dan catatan baris di semua halaman; status dan urutan juga seluruh riwayat. |
| Nota FG tersimpan | Selesai | Status dan urutan berlaku untuk seluruh nota yang cocok (pencarian memang sudah seluruh data). |
| Penyesuaian barang jadi (riwayat dokumen) | Selesai | Status dan urutan berlaku untuk seluruh dokumen. |
| Kartu mutasi barang jadi (di layar stok barang jadi) | Selesai | Jenis mutasi dan urutan berlaku untuk seluruh mutasi posisi itu. Pilihan "jenis mutasi" sekarang lengkap (dulu hanya jenis yang kebetulan ada di halaman). Saldo per baris tetap dihitung dari seluruh riwayat. |
| Hitung fisik bahan (riwayat dokumen) | Selesai | Status dan urutan berlaku untuk seluruh dokumen. |
| Nota Ambil Aksesori | Belum | Lihat "Yang belum dikerjakan". Tulisannya tetap "Filter dan urutan hanya mengatur halaman yang sedang tampil". |

Di layar yang selesai, tulisan kecil di bawah alat cari berbunyi "Filter dan urutan berlaku untuk seluruh hasil,
termasuk halaman lain; jumlah hasil mengikuti filter yang sama", dan pilihan urutan bernama "Urutkan semua hasil".
Setiap kali urutan, status atau pencarian diganti, daftar kembali ke halaman pertama. "Nama / nomor A–Z" mengurutkan
angka di dalam nomor menurut nilainya (INV-2 sebelum INV-10); nomor yang sama diurutkan menurut urutan standar.

Ekspor: tidak satu pun dari delapan layar ini punya tombol ekspor, jadi tidak ada ekspor yang diubah atau dibuat.

## Yang diuji di komputer penulis

- Ketujuh pembaca data diuji di database percobaan sekali pakai (PostgreSQL 16): daftar 31 baris dengan halaman kecil,
  setiap kombinasi urutan × status/jenis × pencarian, halaman demi halaman. Semua lulus. Uji ini sengaja dirusak dua kali
  (urutan tanpa nilai angka, saringan jenis dimatikan) dan uji langsung gagal, jadi uji ini memang memeriksa.
- Panggilan lama (tanpa pilihan baru) diuji berdampingan dengan versi sebelum perubahan pada data yang sama: 319
  panggilan, jawabannya sama persis sampai ke huruf.
- Semua uji layar (2054 uji di 201 berkas) lulus, termasuk uji baru: pilihan dikirim ke server, halaman kembali ke 1,
  jumlah dan total dari server, tulisan cakupan benar, dan jawaban server yang tidak cocok ditolak.
- Pemeriksaan struktur kode (`scripts/check-*.mjs`): hasil sama dengan sebelum perubahan (33 lulus; 3 pemeriksaan
  kepemilikan backend memang sudah merah sebelumnya, keluarannya sama persis).
- Kompilasi dan pemeriksaan bentrok nama untuk ketujuh berkas SQL yang diubah: bersih.

## Yang menunggu uji otomatis (CI)

Uji di database ERP lengkap hanya bisa berjalan di CI. Yang wajib dijalankan:

- `cp7-f03-combined.yml` — 6 uji baru OW-09 di database lengkap (semua pembaca), ditambah uji browser riwayat
  pembayaran/retur. Jumlah kasus yang diharapkan naik dari 22 ke 28.
- `cp7-p11-sales.yml` (pembayaran/retur, uji browser), `cp7-f03-cash.yml` (Kas & Bank di browser),
  `cp7-p13-analysis.yml` dan `cp7-p13-finance.yml` (termasuk uji "jawaban lama sama persis" untuk analisis keuangan),
  `cp7-p10-fg.yml` (barang jadi, uji browser), `cp7-f03-redye.yml` dan `cp7-f03-capacity.yml` (kartu barang jadi),
  `cp7-note-correction.yml`, `cp7-p12-nota.yml`, `cp7-p09-procurement.yml`, `cp7-transaction-source.yml`,
  `claude-p21-rehearsal.yml` (pemasangan lengkap), dan `ci.yml` (semua uji layar dan uji SQL baru).

## Yang belum dikerjakan dan alasannya

1. **Nota Ambil Aksesori.** Daftar nota dibaca oleh fungsi sistem lama (`erp.get_accessory_issue_workspace_v1`) yang
   hanya mengirim 50 nota terbaru, tanpa halaman berikutnya, tanpa pilihan status atau urutan, dan menolak pilihan baru.
   Mengubahnya butuh tahap perubahan sistem lama tersendiri (cara yang sama dengan tahap kasbon) beserta uji CI-nya.
   Layar tetap jujur menyebut "hanya halaman yang tampil"; tidak dipalsukan di layar. Saya perlu Bos memutuskan: kerjakan
   sebagai butir lanjutan (ya/tidak)?
2. **Daftar posisi stok barang jadi dan daftar sumber bahan/FG di layar yang sama** memakai pembaca lain yang bukan bagian
   delapan daftar OW-09. Urutannya masih per halaman dan tulisannya jujur ("Urutan hanya mengatur halaman yang sedang
   tampil"). Saringan dan pencariannya memang sudah seluruh data.
3. **Uji browser OW-04 akan berhenti di pemeriksaan sumber** sampai catatan sidik jari berkasnya diperbarui, karena
   `src/SalesReturnPanel.tsx` (dan dua berkas uji penjualan) berubah. Catatan itu milik kualifikasi OW-04
   (`scripts/ow04-qualification/ACTIVE_UI_SOURCE.json`, `scripts/ow04-source-inverse-ui-qualification/`,
   `scripts/ow04-payment-positive-qualification/SOURCE.json`); tidak saya ubah. Perlu diperbarui dan diuji ulang saat
   penggabungan.

## Catatan teknis

Kunci baru (opsional) pada pembaca CP7; tanpa kunci ini jawabannya sama persis seperti dulu. Bila salah satu kunci baru
dikirim, halaman jawaban membawa `list` (gema pilihan yang dipakai; kas juga `sums`, kartu FG juga daftar jenis).

| Pembaca (berkas) | Kunci baru |
|---|---|
| `erp_cp7_get_finance_analysis_v1` (`scripts/cp7-src/finance/analysis.sql`) | `entry_q`, `entry_status` (POSTED/REVERSED/null), `entry_order` |
| `erp_cp7_get_sales_cash_v1` (`sales/payments.sql`) | `payment_q`, `payment_status`, `payment_order` |
| `erp_cp7_get_sales_returns_v1` (`sales/returns.sql`, hanya kind RETURNS) | `history_q`, `history_status`, `history_order` |
| `erp_cp7_get_nota_workspace_v1` (`payroll/note-read.sql`, hanya NOTES) | `status`, `order` |
| `erp_cp7_get_fg_adjustments_v1` (`fg/adjustment-read.sql`) | `status`, `order` |
| `erp_cp7_get_fg_ledger_v2` (`fg/corrected-ledger.sql`) | `movement_type`, `order` |
| `erp_cp7_get_material_counts_v1` (`materials/count-read.sql`) | `status`, `order` |

`order` = `SOURCE` | `LABEL_ASC` | `LABEL_DESC`. Kunci urut alami: deret angka dibandingkan menurut nilai (panjang
diawali, tidak ada pemotongan), teks huruf kecil, perbandingan byte; seri dipecah dengan urutan standar lama yang sudah
berakhir pada id. Hak akses pembaca tidak diubah. Uji: `tests/cp7/families/ow09-record-lists.test.ts` (SQL, butuh
PostgreSQL dan pengguna bukan root), `scripts/cp7_ow09_list_cases.py` (database lengkap, grup `CP7_OW09_WHOLE_LIST`),
uji layar `src/*.dom.test.tsx` terkait. Modul kasus dan probe lama tidak diubah karena sidik jarinya dikunci oleh
tahap kredit pelanggan (OW-04).

Risiko yang sudah ada sebelumnya dan tidak diubah: daftar berhalaman ini belum membawa tanda isi di kursor (aturan B8e),
jadi baris yang baru tercatat di antara dua perpindahan halaman bisa membuat satu baris bergeser (terlewat atau tampil
dua kali), sama seperti sebelum perubahan ini.

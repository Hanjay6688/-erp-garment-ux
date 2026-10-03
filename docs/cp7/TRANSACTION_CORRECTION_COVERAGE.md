# Koreksi dan pembatalan transaksi · 3 Oktober 2026

Ini status CP7 sesudah merge Claude. Bukti mengikuti commit yang benar-benar diuji. CURRENT_PROGRESS.md dan CURRENT_STATE.json memisahkan hasil lolos dari penerus yang masih diuji. Independent acceptance dan production GO tetap false.

| Permintaan | Alur dan bukti Native yang tersedia | Batas |
|---|---|---|
| Nota salah jumlah, termasuk setahun lalu | Benerin nota adalah perintah atomik. NOTE_YEAR_30 dan NOTE_YEAR_364 pada Native40 di967b5087 mengubah seluruh30/364 saldo berikutnya sebesar selisih12PCS. Buku utama dan kartu lot mengembalikan seluruh366 baris pada4 halaman sebelum/sesudah. | Fakta nota dan lineage asal tetap tersimpan; saldo per baris mengikuti koreksi efektif. Kas, retur, uang muka, HPP dan laporan mengikuti pengaman yang sama. Bukan izin edit semua jenis transaksi arbitrer. |
| Dua baris SKU sama, lot/jumlah/harga berbeda | NOTE_DUPLICATE_SKU_LINES, NOTE_DUPLICATE_SKU_DELETE_REORDER, NOTE_DUPLICATE_SKU_RETURN_ATOMIC pada Native40 menjaga setiap identitas baris, termasuk menghapus/mengurutkan ulang dan retur. | Identitas baris bukan SKU saja. Pemisahan kejadian fisik tetap mengikuti transaksi fisiknya; nilai nota tidak memberi izin menyatukan waktu keluar barang. |
| Invoice FINAL366 hari lalu salah harga bahan | Claude sudah tergabung. RF_YEAR_FINAL_INVOICE_PRICE pada Native42 merge48fe7c22:12 transfer bulanan, harga12→11, AP12000→11000 pada tanggal ekonominya dan recost setiap pemakaian. | Lingkup didukung dan pengaman biaya/pembayaran/periode tetap berlaku; bukan jaminan semua rantai pemakaian arbitrer. |
| Salah jumlah penerimaan/hitung roll setelah potong | Benerin penerimaan: RF_QTY_DOWN_AFTER_CUTTING, RF_QTY_UP_AFTER_CUTTING, RF_ROLL_COUNT_TYPO_UNUSED_ROLL, RF_YEAR_HISTORY_364. Roll sudah dipakai tidak boleh dihapus; jumlah tidak boleh di bawah pemakaian. | Pemakaian selain jalur potong yang didukung tetap memblokir. Penolakan menjaga data, tetapi tidak dihitung sebagai tersedianya koreksi otomatis untuk jalur itu. |
| Salah bahan A→B setelah dipakai | RF_WRONG_MATERIAL_AFTER_CUTTING dan RF_WRONG_MATERIAL_AND_PRICE mengoreksi lineage potong yang didukung. | Pemakaian lain disebutkan dan harus diselesaikan dahulu. Nama master tidak boleh dipakai untuk menyamarkan perubahan identitas. |
| Salah nama/SKU bahan, nomor roll atau surat jalan | RF_MATERIAL_NAME_TYPO, RF_MATERIAL_NAME_REFUSALS, RF_MATERIAL_SKU_TYPO, RF_ROLL_NUMBER_TYPO_USED_ROLL, RF_HEADER_TYPO, RF_INVOICE_HEADER_TYPO, RF_ARRIVAL_DATE_TYPO, RF_WAREHOUSE_TYPO, RF_SUPPLIER_TYPO. | Keunikan nama/SKU/roll; tanggal sebelum pemakaian pertama; gudang hanya barang belum dipakai/dipindah; supplier dibatasi invoice gabungan/uang muka lama. |
| Pembayaran supplier dari transaksi asal | Native57 a8e5b8e membuka pembayaran tepat termasuk anak di halaman berikutnya, lalu inverse Native. AP/kas/jurnal/stok/HPP diperiksa; balasan hilang dipulihkan dengan UUID/payload/versi asal. | Pembatalan tersedia. Pembuatan/penggantian pembayaran arbitrer dalam satu koreksi atomik belum merupakan lingkup bukti ini. |
| Finalisasi QC dari mutasi FG | Native57 a8e5b8e mengikuti FK QC item→inspection asli. Inverse FG membuka inspection sama. Desktop/mobile membuktikan satu efek, saldo1→0, dan pemulihan balasan hilang. | Legacy tanpa lineage lengkap dan keluarga inverse FG lainnya tetap tidak didukung. |
| Transaksi keuangan lain posted | Koreksi atomik Native20 di203ff0e7: tanggal lama, sen, akses/periode, kegagalan akhir membatalkan semua efek, lost-reply recovery dan memulihkan nilai sebelumnya melalui koreksi baru dengan riwayat. | Ini khusus transaksi lain; bukan editor umum jurnal dari produksi/invoice/payroll. |

Bukti Original lengkap:

- evidence/owning-note-correction/qualified40-967b/RECEIPT.json dan HISTORICAL_READ_MEASUREMENTS.json — Native40. P95 buku48.756ms/10 sampel dan kartu66.562ms/8 sampel adalah SQL/Auth fixture; belum SLA produksi/UI/jaringan atau penuh P19.
- evidence/claude-merge-20261003/receipt-qualified42/RECEIPT.json — Native42 merge; aturan lengkap di RECEIPT_CORRECTION.md.
- evidence/transaction-source/qualified57-a8/RECEIPT.json — Native57 supplier/QC dan gambar desktop/mobile asli.
- evidence/misc-correction/qualified203f/RECEIPT.json — Native20. Kedua kegagalan terdahulu tetap tersimpan.

## Sambungan Laundry/QC yang sudah qualified

| Bagian | Status | Bukti wajib |
|---|---|---|
| Antrean QC→penerimaan Laundry tepat | Semua64 ID sebelumnya tetap dan PASS dalam Native69 pada3af3be8a (38 DB/4 race/9 Auth HTTP/18 browser).6 sumber Laundry memakai FK asli, nomor pengiriman dari reader Native, dan UUID penerimaan di dalam parent yang tepat. | Inverse Native dan lost-reply reload/recovery tetap. LAUNDRY_SOURCE_HANDOFF.md; Original qualified69-3af3. |
| Penerimaan blocked→daftar QC aktif→owning QC | Native69 pada3af3 lolos, termasuk26 QC pada halaman25+1 serta halaman2 benar-benar kosong setelah inverse membuat total25. Izin Laundry/QC saat ini, source asli dan dua inverse owning Native terbukti. | Semua69 ID tetap, seluruh restore/primary/backup/advisor/Auth gates lolos. TRANSACTION_DEPENDENCIES_HANDOFF.md. |

Potongan yang sudah mengeluarkan bahan/pickup/QC tidak dapat dibuka sebagai draft oleh pembaca Native sekarang. Batas selector dan kemungkinan sambungan berikutnya: CUTTING_SOURCE_CONTRACT_HANDOFF.md. Inspection ini tidak menambah writer/grant/route atau mengaku koreksi posted sudah tersedia.

QC lalu penerimaan adalah dua transaksi Native terpisah, masing-masing atomik pada efeknya sendiri. Tidak dijanjikan satu rollback atomik seluruh rantai. Invoice vendor, payroll, claim, PO selesai dan pemakaian lain tetap diperiksa Native. Daftar QC bukan daftar semua penghalang.

Koreksi arbitrer lintas transaksi, penggantian bahan melalui pemakaian non-potong, daftar penghalang semua domain, P18–P19 penuh, audit independen P20 dan pemasangan/bukti installed P21 masih terbuka. First failure tetap Original dan tidak diberi label PASS sesudah perbaikan.

## Tambahan bukti setahun melalui login sungguhan

Original diagnostic2 pada07dd (run37134007452) memakai session_user authenticator, role authenticated dan batas8s asli. Koreksi24→12 menghasilkan seluruh366 baris buku/kartu dan setiap364 saldo berikutnya+12; stok112/nilai1120/net240/dibayar0/piutang240. Perintah6211.860ms, pembacaan857.075ms, HTTP7108.019ms pada fixture ini. Pemeriksaan ulang dari data mentah cocok. Setiap percobaan sengaja dipulihkan penuh sesudah hasil diamati; ini bukti diagnosis, bukan tambahan kelulusan Native40, pembuktian commit tahun yang dibaca ulang di request lain, atau SLA produksi. Arsip: evidence/note-actual-http-diagnostic/qualified2-07dd/RECEIPT.json. Penyebab timeout lama masih terbuka.

Saldo yang ditampilkan dihitung dari prefix seluruh riwayat efektif sebelum filter/halaman, sehingga koreksi lama mengubah saldo semua baris sesudahnya tanpa menghapus fakta asal. Pemisahan pengeluaran pagi/malam tetap membutuhkan dua kejadian fisik yang benar-benar direkam; nota malam tidak dapat mengarang waktu pagi.

A candidate now strengthens the same existing Native40 HTTP corrected-book case with a genuinely committed year correction and independent Auth request readbacks/replay.15 local declared-stand-in refusal controls pass; actual full40 is pending. No earlier diagnostic or prior-source proof closes it. NOTE_COMMITTED_HTTP_YEAR_HANDOFF.md controls the successor.

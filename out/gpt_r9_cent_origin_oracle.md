# CP6 W8 — oracle independen sebelum run

Head kandidat yang diuji: `d1bc8adff3ba1a2a7001ef39e4819d0c3813d00b` (produk `61d88ee5224b2fb2da2af6f4df214fbaacf9f161`). Label `AUDITOR_SCENARIO`, database salinan sekali pakai, bukan bukti rilis. Skenario `audit/scenarios/r9_cent_origin/gpt_cent_origin.py` memakai API pembelian, potong, dan nota supplier yang sah. Tidak mengimpor `xaudit_8.py` milik Fable.

## Pertanyaan dan oracle (dibekukan sebelum output dibaca)

Tiga penerimaan satu unit memakai satu bahan, tetapi pada tiga hari berurutan. Setiap unit sudah dipotong dengan roll-nya ke PO tersendiri dan stok bahan kembali nol **sebelum penerimaan berikutnya**. Nota supplier masuk sesudah semua pemakaian, urutan dokumen dibalik (`ketiga → pertama → kedua`). Satu kasus tambahan mengoreksi dokumen tengah saja.

- `THREE_STAGGERED_INVOICE_REVERSE_ORDER_UP`: estimasi 10,00 per sumber, nota akhir 10,005 per dokumen → tiga PO masing-masing 10,01; WIP total 30,03; bahan fisik dan nilai akhir nol.
- `THREE_STAGGERED_INVOICE_REVERSE_ORDER_DOWN`: estimasi 10,01 per sumber, nota akhir 10,004 per dokumen → tiga PO masing-masing 10,00; WIP total 30,00; bahan fisik dan nilai akhir nol.
- `THREE_STAGGERED_ONLY_MIDDLE_CORRECTED`: estimasi 10,00 per sumber, hanya nota kedua menjadi 10,015 → PO [10,00; 10,02; 10,00]; WIP total 30,02; bahan fisik dan nilai akhir nol.

Validasi mencatat stok nol pada tiap jeda, WIP per PO sebelum dan sesudah nota, WIP total, nilai stok akhir dan saldo bertanggal. Prefix nilai stok tidak boleh negatif. Jika setup tidak dapat membuktikan stok nol tiap jeda atau posting invoice gagal, hasil bukan PASS; error dari runner tetap INCOMPLETE. Hasil dibaca persis seperti dicetak, termasuk COUNTEREXAMPLE; tidak ada pelabelan ulang.

Dasar kontrak: Master Pulih M:3820 (prefix qty/nilai bertanggal tidak boleh rusak), M:6632 (recost harus cocok total dan per tanggal, jejak sumber/adjustment dapat dibuka), M:375 (pembulatan menurut sen tiap sumber pada opening linked receipts; analogi dibatasi), M:485 hanya memberi contoh pembagian biaya kain kantong *satu pool* antarkelompok, bukan izin langsung bagi selisih sen lintas dokumen pembelian/PO. Bila realisasi per PO meleset, periksa dulu apakah sumber cost engine masih dibagi ke pool meski stok kosong di antara penerimaan; klasifikasikan pelanggaran kontrak setelah memeriksa jejak sumber, bukan berdasar angka total saja.

## Batas

Tes ini mencakup tiga penerimaan satu bahan, satu unit per penerimaan, WIP pada PO yang masing-masing menerima satu roll. Belum mencakup satu PO menerima beberapa sumber, beberapa bahan dalam satu dokumen, FG/COGS setelah WIP, atau transaksi serentak. CP6 tetap HOLD.

## LANGKAH BERIKUTNYA

1. Pin SHA256 skenario dan workflow; commit/push ke cabang audit.
2. Ambil run ID/job ID workflow `GPT CP6 W8 Isolated Source Cent Audit`; baca setiap JSON kasus, status grup, identitas run, `primary_unchanged`, dan pembersihan clone.
3. Bedakan hasil tiga penerimaan berurutan ini dari hasil Fable yang menerima ketiga dokumen sebelum pemakaian. Jika ada kontra, audit source origin dan saluran jurnal PO; jika PASS, batasnya tetap hanya urutan terpisah.

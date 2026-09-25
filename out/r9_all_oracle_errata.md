# Errata oracle ALL22 — ALL-S01 tanda jurnal saldo awal

## Temuan audit oracle, bukan cacat produk

Dalam `out/r9_all_oracle.md:63` (oracle beku SHA256 `01b1c1b3d6acdc0c92ad1b8bff0b1f66ddbc3164af202ed696abb7f7dba5de9b`) tertulis `Dr OPENING_EQUITY / Cr CUSTOMER_RECEIVABLE 70.00`. Itu arah terbalik untuk piutang pelanggan 70.00, dan juga bertentangan dengan ALL-A02 di oracle yang sama (`out/r9_all_oracle.md:121`, opening mandor receivable debit / opening equity kredit). M:934–938 menuntut hanya sisa piutang 70.00 yang dibukukan, tanpa pendapatan atau kas historis baru.

**Oracle benar untuk ALL-S01:** invoice lama 100.00, historis diterima 30.00, opening receivable 70.00 = **Dr CUSTOMER_RECEIVABLE 70.00 / Cr OPENING_EQUITY 70.00**. Penerimaan setelah cutover 25.00 = **Dr kas/bank 25.00 / Cr CUSTOMER_RECEIVABLE 25.00**; sisa piutang 45.00. Reversal tertaut mengembalikan piutang 70.00 dan bank awal. Semua persyaratan identitas, tanggal, idempoten, anti-sejarah-sintetis, dua sesi, dan tampilan di berkas beku tetap berlaku.

**Penanganan transparan:** oracle beku dan SHA tidak diedit atau ditimpa. Errata ini ditulis ketika writer BB head `72bf53f8d808e18fd3e2866491f28667c1b6193d` sudah terbit, sebelum ada rerun auditor BB; karena itu uji ALL-S01 memakai kedua pencatatan dan tidak boleh diberi label bukti oracle pra-kode independen untuk *arah jurnal* ini. Validasi terpisah terhadap kontrak dan ledger kanonis diperlukan; semua gate ALL22 tetap UNVERIFIED/HOLD. Klasifikasi P2 kualitas oracle audit, bukan P2 produk.

**Langkah berikutnya:** cocokkan jurnal sumber BB di database sekali pakai dengan arah benar serta kontrak; simpan hasil per kasus dan jangan ubah status historis maupun hasil T2 yang telah dibekukan.

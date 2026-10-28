# OW08b / 2.19 — keputusan owner: dua penyelesaian piutang vendor

Owner menjawab: **“gw udah jawab C bisa 22 nya, B juga udah selesai tolong dilanjutkan.”**

C berarti keduanya: sisa kelebihan bayar laundry menjadi piutang tertaut ke
dokumen koreksi, dapat dipakai untuk tagihan vendor yang sama atau diterima
kembali melalui kas/bank. Ini menutup pertanyaan bisnis 2.19; bukan kelulusan
implementasi, audit, pemasangan, atau production GO.

Implementasi meneruskan LAU-DEC06 dan kredit vendor BD. Invoice/pembayaran asal
tetap utuh. Dokumen koreksi yang memakai akun piutang mendebit akun aset khusus
yang dipilih pengguna; pemakaiannya melunasi utang dengan AP debit / piutang
kredit. Sisa piutang dan utang disajikan terpisah, tanpa membuat AP negatif.
Jalur koreksi lama yang tertutup utang tetap tersedia. Akun tidak diciptakan
atau ditebak otomatis. Pengembalian hanya mengonsumsi saldo piutang sumbernya,
bukan penerimaan pendapatan. Pembatalan berupa jurnal pembalik tertaut.

A mengerjakan pada cabang terpisah dari kandidat B. Bukti backend3194 dan
browser B tetap berlaku untuk sumber/cakupannya sendiri; delta uang ini wajib
mempunyai bukti penerus. Formal 5/16, independent_acceptance=false,
production_go=false; CP7C belum dimulai.

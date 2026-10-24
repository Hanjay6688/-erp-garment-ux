# P21 seluruh alur uang pada pemasangan current A/B

Penerus terpisah dari `cp7_p21_current_chain_rehearsal_probe.py`. Seluruh helper
lama dipertahankan dengan AST yang sama; berkas induk, gold uang, SQL produk,
kasus beku dan sumber B tidak diedit. ADAPTATION.json mencatat setiap penggantian
teks: pemasang current, trusted recovery A/B, identitas report/admission, serta
satu fixture bounded dan verifikasi ulangnya sesudah restore.

Dua rantai APPLY/REFUND tetap memakai gold immutable: P1000/P900, koreksi turun
naik, saldo kredit dan kas, jurnal lama, undo bernama dan inverse retur. Tiga
langkah mandor, empat langkah siklus P21 serta enam langkah A (pool HPP sebelum
E01 READY, empat AR checks nol, transfer400+600, sumber kasbon/FG, angka laporan,
cuci hargaUNKNOWN) tetap wajib. Langkah ketujuh membandingkan bounded DONE
job/header/semua halaman/draft setelah restore dan replay dua UUID tanpa efek.

Pemasangan wajib melewati current legacy inventory; inverse pra-pakai harus
sama seluruh22 katalog/data/sequence. Guard used berlaku sebelum DDL. Sesudah
dipakai hanya full dump ke database segar; kontrol negatif tetap, full22 dan
semua baris/sequence cocok sebelum satu seal OID lokal dan salinan metadata
argumen composite untuk verifier B dipasang. Tidak ada SQL/hak/policy diubah
supaya pemeriksa lolos. Semua aktor/fixture berada pada loopback sekali pakai.

Ini satu skenario pemulihan, bukan penjumlahan baru seluruh Native286 atau
factory3600. Auth/browser dinilai oleh receipt terpisah. Assertion E01 READY,
unknown≠0, uang/stok/HPP dan original tidak boleh dilonggarkan. PASS baru boleh
dicatat setelah Original, CP6/advisor, pembersihan dan lima gate paket diperiksa.
Main/integrasi resmi/audit beku/hosted/WA nyata tetap; production_go=false.

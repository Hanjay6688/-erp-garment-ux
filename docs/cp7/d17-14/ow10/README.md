# OW10 — satu mesin target dan titik pesan ulang

23 Oktober2026 WIB. Implementasi inti; **OW10 belum ditutup**.

Target langsung/bertahap dan titik pesan ulang barang jadi memakai `cp7_baseline.target(jsonb)` yang sama.
Kontrak privat v2 memakai jumlah/hari utuh dan satu pilihan cadangan. Hasil memisahkan ambang kebutuhan selama
waktu produksi dari target sampai pemeriksaan berikutnya. Panel menampilkan rinciannya tanpa menghitung angka kedua.
Kontrak v1/arsip lama tetap terbaca; stempel versi mesin pada hash target/supply mencegah arsip lama disebut segar.

Pembanding lokal independen Fraction/Decimal80 digit cocok162 kasus;129 jawaban lengkap kontrak lama identik.
Contoh perbaikan:1PCS/3hari ×3,000000000001hari sedikit melebihi1PCS, sehingga target2PCS; memotong mean12 desimal
lebih dulu menghasilkan1PCS. ROP lama sudah memakai rasio utuh: angka ROP diharapkan tetap pada sumber/aturan sama.
Empat kelompok SQL lokal,49 uji klien/DOM, TypeScript dan CSS ownership lulus. Kegagalan fixture UUID awal disimpan.
Ini belum bukti Native/HTTP pada commit baru. Semua parameter statistik ROP tetap dari aturan lama, bukan keputusan baru.

Tidak ada fungsi/role/tabel/grant ERP baru; jumlah fungsi kernel tetap22. Bundle tidak perlu daftar sumber baru.
Pemanggil langsung dan bertahap memakai v2. Native target38 dan analisis bertahap15 harus lulus lagi; workflow stock
formula99 juga dijalankan untuk memeriksa ROP pada transaksi Native. Hasil server harus dibaca sebelum integrasi.

Sisa OW10: satu aturan/sumber permintaan pada semua jalur, kapan mulai menurut suplai tepat pada horizon yang relevan,
dan alokasi WIP/rencana agar satu proses tidak dikreditkan ke beberapa varian barang jadi. OW11/OW13c masih terbuka.
Rincian target bukan izin memulai produksi. Keuangan/HPP, data Enteng dan branch A tidak disentuh.

Acuan modul ROP yang sudah ada: Chris Caplice, MIT ESD.260, Inventory Management: Probabilistic Demand, slide5–7/9/13,
https://ocw.mit.edu/courses/esd-260j-logistics-systems-fall-2006/resources/lect11/ .

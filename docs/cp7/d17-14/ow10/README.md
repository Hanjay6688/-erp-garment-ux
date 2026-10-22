# OW10 — satu mesin target dan titik pesan ulang

23 Oktober2026 WIB. Implementasi inti; **OW10 belum ditutup**.

Target langsung/bertahap dan titik pesan ulang barang jadi memakai `cp7_baseline.target(jsonb)` yang sama.
Kontrak privat v2 memakai jumlah/hari utuh dan satu pilihan cadangan. Hasil memisahkan ambang kebutuhan selama
waktu produksi dari target sampai pemeriksaan berikutnya. Panel menampilkan rinciannya tanpa menghitung angka kedua.
Kontrak v1/arsip lama tetap terbaca; stempel versi mesin pada hash target/supply mencegah arsip lama disebut segar.

Pembanding lokal independen Fraction/Decimal80 digit cocok168 kasus;129 jawaban lengkap kontrak target lama identik.
Contoh perbaikan:1PCS/3hari ×3,000000000001hari sedikit melebihi1PCS, sehingga target2PCS; memotong mean12 desimal
lebih dulu menghasilkan1PCS. ROP lama sudah memakai rasio utuh: angka ROP diharapkan tetap pada sumber/aturan sama.
Lima kelompok SQL lokal,82 uji klien/DOM, TypeScript dan CSS ownership lulus. Kegagalan pertama tetap disimpan.
Modern v2 menerima lama produksi0 yang diketahui; v1 tetap menolak horizon0. Nol tetap dibedakan dari unknown.
Semua parameter statistik ROP tetap dari aturan lama, bukan keputusan baru.

## Dua waktu, satu pembagian suplai

`cp7.net-input.v2` membaca daftar suplai hasil pembagian global yang **sama** pada dua batas: L untuk titik pesan
ulang dan L+R untuk jumlah target. Kedua pembacaan memanggil kernel netting v1 yang tetap; tidak ada pembagian
kedua. Rencana langsung dan analisis bertahap sama-sama memakai jalur ini. Panel membaca posisi, status dan batas
waktu dari server, menjaga kontrak arsip lama, dan menghapus hasil bila hak saat ini dicabut.

Pembanding konkret SQL aktual: satu pool20PCS untuk dua varian, masing-masing kekurangan15, terbagi15+5; bukan20+20.
Bila selesai setelah L tetapi sebelum L+R, suplai itu mengurangi jumlah target tanpa menghapus pemicu pesan ulang.
Batas ETA tepat L termasuk; posisi tepat titik tetap memicu; tujuan terikat ke varian pertama tidak mengisi varian
lain. Balasan fisik identik tidak dihitung dua kali, jumlah berubah ditolak.12 jawaban netting v1 tetap identik penuh.
Ini uji kernel lokal dengan fakta sintetis, bukan klaim transaksi Native. Kasus Native netting lama tetap84; tambahan
assertion memeriksa kejadian sama pada hari5 di antara lead3 dan target10, tanpa menghapus kontrol hari11 yang lama.

Tidak ada fungsi/role/tabel/grant ERP baru; jumlah fungsi kernel tetap22. Bundle tidak perlu daftar sumber baru.
Pada **b6c041157f0f5888f8d0d50081de25f7538fb594**, Original yang sudah dibaca membuktikan target38/38,
analisis bertahap15/15, serta stock formula/WA99/99, termasuk pasang/pulih dan gerbang advisor.
Receipt/hash di b6c0411-pass.json. Bukti itu berlaku untuk b6, sebelum pemisahan suplai dua horizon di atas.
Pada **4d881bfc20da641d2ed4a941cb97a3d125e9e65a**, Original membuktikan38/38,15/15,84/84; termasuk Native hari5
di antara lead3 dan target10, desktop/HP, hak saat ini, UUID, pasang/pulih dan gerbang advisor. Receipt terpisah
4d881bf-38-15-84-pass.json. Stock99 gagal boot pada batas unduh image:0 kasus, bukan hasil uji fitur. Log pertama
ditahan privat, potongan/hash di 4d881bf-first-stock-boot.json; tidak mengulang tes tanpa perubahan/risiko konkret.
Stock99 pada4d masih belum terverifikasi. Tidak memakai bukti99 b6 untuk menyebut4d lulus penuh.

Sisa OW10: satu aturan/sumber permintaan pada semua jalur dan penggantian kredit WIP mentah per-model pada pengingat
dengan suplai yang relevan dari mesin rencana yang sama; pengingat belum boleh dianggap sudah bebas hitung ganda.
Kualifikasi server pemisahan dua horizon38/15/84 sudah lulus; sisa pemeriksaan stock99 belum berjalan. OW11/OW13c tetap terbuka.
Rincian target bukan izin memulai produksi. Keuangan/HPP, data Enteng dan branch A tidak disentuh.

Acuan modul ROP yang sudah ada: Chris Caplice, MIT ESD.260, Inventory Management: Probabilistic Demand, slide5–7/9/13,
https://ocw.mit.edu/courses/esd-260j-logistics-systems-fall-2006/resources/lect11/ .

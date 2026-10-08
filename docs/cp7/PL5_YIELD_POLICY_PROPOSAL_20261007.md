# PL-5 — paket rekomendasi parameter yield histori (B) · 7 Oktober 2026

**Status 8 Okt 2026: DISETUJUI owner** ("setuju paket usulan histori: 180 hari, minimal 5 grup selesai dan 200 PCS potong, per produk+size lalu fallback model yang sama, batas bawah Wilson satu sisi 90%. Jangan lintas model atau menganggap yield 100%. Bila data kurang, gunakan A yang ditinjau atau UNKNOWN. Simpan keputusan sebagai kebijakan berversi dan uji sebelum diaktifkan.").

Dibuat (`scripts/cp7-src/plan-native/history-yield.sql`): kebijakan berversi `cp7_yield_policy.policies` yang disimpan pemilik/admin dengan alasan (aktor, peran, waktu tercatat; versi tidak bisa diubah; tingkat keyakinan 90%, rumus, pembulatan dan urutan tingkat tetap); pembaca `history_yield(target, model)` memakai bukti grup habis PL-8 yang masih cocok dengan fakta sekarang; tanggal selesai = kejadian fisik terakhir grup, jendela dalam hari kalender WIB; lebih dari 200 grup pada satu tingkat = belum diketahui. Tanpa kebijakan tersimpan, jawabannya tetap `PENDING_POLICY_VALUE` persis seperti sebelumnya. Layar: panel "Kebijakan yield histori" di Data permintaan & stok (paket keputusan owner tampil terisi, berlaku setelah disimpan); pratinjau rencana menyebut batas bawah, jumlah grup/PCS, tingkat dan versi kebijakan. Uji: suite CI `pl5-history-yield-20` (`docs/cp7/pl5/PL5_HISTORY_YIELD.json`: 14 Native, 2 balapan, 2 HTTP, 2 browser). Aktif di aplikasi setelah disimpan sekali oleh pemilik atau admin.

## Yang sudah berlaku (keputusan owner 7 Okt)

- **Tidak pernah dianggap 100%.** Tanpa yield, batas potong tetap = kebutuhan (`NEED_CAP_YIELD_UNKNOWN_NOT_ASSUMED_100_PERCENT`), sedangkan PCS bagus dan kekurangan yang belum tertutup = belum diketahui (null), bukan `kebutuhan − potong`.
- **A — perkiraan per rencana:** perencana mengisi "PCS bagus dari PCS potong" (bilangan bulat, bagus ≤ potong). Masuk sebagai asumsi `PLAN_NEW_START_YIELD` yang wajib ditinjau bersama asumsi lain; label "Perkiraan per rencana yang ditinjau (bukan histori)". Batas potong `ceil(kebutuhan × potong / bagus)`, PCS bagus `floor(potong_dipilih × bagus / potong)`, sisa `max(0, kebutuhan − PCS bagus)`. Contoh 9/10, kebutuhan 100 → batas 112.
- **B — histori produksi (arah utama):** bila tersedia, B dipakai dan perkiraan A ditolak (`CP7_PLAN_NEW_START_YIELD_HISTORY_AVAILABLE`) supaya hanya satu sumber.

## Usulan parameter B (satu paket)

| Parameter | Usulan | Alasan | Alternatif yang ditimbang |
|---|---|---|---|
| Data yang dihitung | Hanya grup potong yang **terbukti habis** (setiap potongan sudah FG atau keluar/BS), memakai bukti tersimpan PL-8 yang terikat versi sumber. Yield = Σ PCS FG ÷ Σ PCS potong. | Grup yang masih berjalan belum punya hasil akhir; memasukkannya membuat yield terlihat rendah atau tinggi secara semu. Bukti terikat versi menjamin koreksi/pembatalan/transaksi mundur memaksa hitung ulang. | Memakai grup setengah jalan dengan proyeksi — ditolak karena mengarang hasil. |
| Tingkat pengelompokan | Per produk+size (target) dulu; bila sampel kurang, per model (semua size model itu). Tidak pernah lintas model. | Yield banyak dipengaruhi pola dan bahan model; size dalam satu model biasanya mirip. | Lintas model per kategori — ditolak, terlalu beda pola. |
| Jendela histori | **180 hari** ke belakang dari tanggal grup selesai. | Cukup panjang untuk mengumpulkan beberapa grup produk yang tidak setiap minggu diproduksi; cukup pendek agar perubahan pola, bahan, atau tim tetap tercermin. | 90 hari (sering kurang sampel untuk SKU pelan), 365 hari (mencampur kondisi lama). |
| Sampel minimum | **≥ 5 grup selesai dan ≥ 200 PCS potong** pada tingkat yang dipakai. | Satu grup bisa ekstrem karena satu roll bermasalah; 5 grup meratakan. 200 PCS membuat galat baku proporsi sekitar 2 poin persen pada yield ±90%. | 3 grup/100 PCS (lebih cepat tersedia tetapi lebih berisiko). |
| Batas bawah | **Batas bawah Wilson satu sisi 90%** dari proporsi gabungan, dibulatkan ke bawah ke 0,1%. | Rencana memotong sedikit lebih banyak dari rata-rata sehingga risiko kurang produksi rendah. Contoh: 180 bagus dari 200 potong (90%) → batas bawah ±86,9% → kebutuhan 100 dipotong 116, bukan 112. | Rata-rata gabungan tanpa margin (lebih hemat bahan, risiko kurang lebih tinggi); yield grup terendah (terlalu pesimis karena satu pencilan). |
| Bila sampel kurang | Tingkat model; bila tetap kurang → A bila perencana mengisi, selain itu UNKNOWN. | Sesuai keputusan "saat data belum cukup boleh A". | — |

## Yang dibutuhkan sesudah persetujuan

1. Simpan kebijakan sebagai catatan bertanda tangan owner (versi, alasan, waktu), sama seperti kebijakan produksi lain; perubahan membuat versi baru.
2. `history_yield` membaca bukti grup habis PL-8 yang masih berlaku dalam jendela, menghitung per target lalu per model, dan mengembalikan `AVAILABLE` beserta pembilang/penyebut, jumlah grup, jumlah PCS, dan tingkat yang dipakai.
3. Kasus Native: sampel cukup/kurang, batas bawah tepat, bukti yang dibatalkan oleh koreksi/pembatalan/transaksi mundur mengeluarkan grup itu dari histori.

Sampai langkah 1 disetujui, butir B tercatat sebagai **batas terbuka**, bukan fitur selesai.

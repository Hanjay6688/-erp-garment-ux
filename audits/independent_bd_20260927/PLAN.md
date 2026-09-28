# Audit independen BD — rencana sebelum eksekusi

Tanggal: 27 September 2026 WIB. Mandat: audit independen BD (laundry), source produk tidak diperbaiki oleh auditor. Rencana ini ditulis sebelum membaca implementasi BD atau menjalankan tes baru.

## Kandidat dan batas kesimpulan

Repository Hanjay6688/-erp-garment-ux; kandidat awal 08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec dari cabang claude/new-session-deapao. Kandidat tersebut juga memuat pekerjaan BE; audit BD harus mencatat secara eksplisit lapisan yang benar-benar diinstal. Identitas source, checksum, baseline database, dan pengecualian instalasi akan dicatat. Tidak ada PASS yang dipindahkan dari hash lain tanpa bukti kesetaraan source.

Lingkungan: database dan aplikasi lokal/disposable; tidak menyentuh production, hosted Enteng, atau legacy Garment. Uji mutasi hanya memakai data sintetis milik audit. Membaca definisi API dan skema untuk menyusun adapter diizinkan sesudah rencana ini dikunci. Skrip, fixture operasional, expected result, serta verdict tes writer tidak menjadi oracle.

Paparan terdahulu: ringkasan percakapan otomatis, metadata CI, dan bagian status handoff memuat sebagian temuan lama. Audit ini independen dalam rancangan, perhitungan, eksekusi, dan penilaian; tidak diklaim sebagai audit buta tanpa paparan.

## Dasar bisnis

ERP_V3_2.md versi 15, bagian keputusan owner 1.1, invariant 3, serta kontrak laundry 7.2–7.6. Keputusan owner 26 September yang terpulihkan: tarif tidak dibedakan ukuran; biaya/selisih dibagi per potong dalam sumber tagihan yang sama; penjualan ketika harga laundry belum diketahui diperbolehkan dengan status biaya pending; retur memakai kredit lalu sisa dibawa; koreksi sesudah pembayaran memakai dokumen koreksi; kredit klaim lintas tagihan mempunyai alokasi terpisah. Konfigurasi finansial yang belum diputuskan tidak diasumsikan aktif.

Prioritas: reliable data; keuangan, stok, HPP. Fakta posted immutable; koreksi tertaut. Proses fisik, harga, invoice, pembayaran, dan kelengkapan HPP adalah dimensi berbeda. Unknown bukan nol; nilai sementara bukan final. Satu sumber tidak boleh ditagih atau dibebankan dua kali. Hak akses diterapkan di server. Draft dapat diedit; posting memakai versi terakhir dengan atomisitas, idempotensi, dan pemeriksaan kapasitas sumber.

## Data dan oracle independen

Vendor sintetis AUD-CEDAR dan AUD-BIRCH, nama proses AUD-WASH dan AUD-FINISH; dua identitas produk yang memiliki nomor SKU sama tetapi merek berbeda; semua UUID baru dan sah. Sumber A berisi 13 PCS, sumber B 9 PCS, tanggal bisnis tetap pada periode terbuka yang ditetapkan fixture. Sumber dibuat melalui kontrak aplikasi jika tersedia; setup langsung yang diperlukan dicatat dan tidak dihitung sebagai pengujian alur produksinya.

Angka ditetapkan dengan aritmetika Decimal terpisah:

- 13 PCS wash × 4.321,09 + 5 PCS finish × 678,91 = 59.568,72. Fisik tetap 13 PCS, bukan 18.
- Paket tetap 8.712,35 × 13 = 113.260,55. Included process tidak menambah biaya.
- Harga wash invoice 4.450,13: tagihan 7 PCS = 31.150,91; tagihan sisa 6 PCS = 26.700,78; total wash 57.851,69. Ditambah finish 3.394,55, total akhir 61.246,24. Perubahan dari estimasi = 1.677,52.
- Biaya batch 1.000,01 pada 13 PCS harus tetap berjumlah 1.000,01 setelah pembulatan/alokasi; tidak menjadi 13.000,13. Aturan penempatan sen residual dicatat dari kebijakan; auditor tidak mengarang aturan yang belum disepakati.
- Pembayaran menyelesaikan utang tanpa mengakui biaya kedua. Invoice dan koreksi tidak mengubah jumlah/custody fisik.

## Matriks rencana

Setiap baris adalah tujuan pemeriksaan, bukan klaim sudah dieksekusi. Hasil harus menunjuk command, input, respons, dan observasi database/layar. Ketiadaan API atau runtime menghasilkan BLOCKED/NOT_RUN, bukan PASS.

| ID audit | Pemeriksaan independen | Hasil wajib |
|---|---|---|
| IND-01 | Komponen parsial pada 13 PCS, finish 5 PCS | 59.568,72; fisik 13 |
| IND-02 | Paket fixed dengan included processes | Hanya 113.260,55 dibebankan |
| IND-03 | Mode paket dan komponen dicampur secara ilegal | Ditolak atomik, tidak tagih dua kali |
| IND-04 | Vendor B menggunakan komponen/katalog vendor A | Ditolak, saldo kedua vendor utuh |
| IND-05 | Ubah harga/nama/nonaktifkan master setelah snapshot | Fakta transaksi lama tetap; transaksi baru mengikuti aturan master |
| IND-06 | WIP tanpa SKU final dikirim ke laundry | Fisik sah tanpa menciptakan SKU/FG otomatis |
| IND-07 | Komponen diketahui bercampur UNKNOWN | Subtotal diketahui terbaca; total/HPP tidak final |
| IND-08 | Harga nol eksplisit dengan alasan gratis | Dibedakan dari UNKNOWN, tanpa utang palsu |
| IND-09 | Harga ESTIMATED dan AGREED, invoice belum ada | Status harga dan tagihan terpisah |
| IND-10 | Harga berbeda per ukuran saat fitur tidak aktif | Tidak diam-diam membedakan tarif per ukuran |
| IND-11 | Komponen parsial salah sumber/ukuran/merek | Tidak memakai kapasitas sumber lain |
| IND-12 | Qty negatif, nol tidak sah, pecahan PCS, melebihi sumber | Ditolak sesuai kontrak, tanpa efek parsial |
| IND-13 | Draft invoice dibuat lalu diedit | Belum ada utang/biaya/fisik authoritative baru |
| IND-14 | Posting invoice parsial 7 lalu 6 PCS | Total wash 57.851,69; sisa kapasitas 0 |
| IND-15 | Tagihan ke-14 pada sumber 13 PCS | Ditolak, total tetap 13 PCS tertagih |
| IND-16 | Invoice mengganti estimasi | Biaya akhir 61.246,24; selisih 1.677,52; tidak double cost |
| IND-17 | Invoice untuk vendor berbeda dari sumber | Ditolak atomik |
| IND-18 | Satu invoice berisi baris valid dan baris invalid | Seluruh posting gagal; tidak tersisa posted parsial |
| IND-19 | Request sama dan payload sama diulang | Hasil sama dan satu dampak |
| IND-20 | Request sama tetapi payload berbeda | Ditolak; dokumen pertama tidak berubah |
| IND-21 | Dua versi draft; submit dari versi basi | Tidak memposting isi lama secara diam-diam |
| IND-22 | Dua sesi menagih kapasitas sumber yang sama | Total tidak pernah melebihi kapasitas |
| IND-23 | Dua sesi menjalankan request identik bersamaan | Satu transaksi efektif |
| IND-24 | Pembayaran sebagian dan penuh | Utang turun tepat; biaya/HPP tidak bertambah kedua kali |
| IND-25 | Reversal invoice belum dibayar | Nilai dibalik tertaut; snapshot dan fisik tetap |
| IND-26 | Koreksi invoice setelah dibayar | Dokumen koreksi tertaut, sejarah pembayaran utuh |
| IND-27 | Reversal kedua pada dokumen yang sama | Tidak menghasilkan pembalikan kedua |
| IND-28 | Klaim vendor dikreditkan ke tagihan | Kredit tidak dapat dipakai ganda; vendor/source tertaut |
| IND-29 | Kredit dipakai lintas tagihan | Ada alokasi terpisah; jumlah kredit tetap terkonservasi |
| IND-30 | Penjualan barang dengan biaya laundry pending | Sesuai ALLOW_PENDING; biaya/laporan tetap ditandai belum final |
| IND-31 | Invoice susulan setelah barang terjual | Rekonsiliasi WIP/FG/COGS dan utang; fisik tidak berubah |
| IND-32 | Retur ketika biaya berubah atau masih pending | Qty/nilai konservatif dan lineage utuh |
| IND-33 | Invoice mundur tanggal di periode terbuka | Tanggal ekonomi invoice digunakan secara konsisten |
| IND-34 | Koreksi berkaitan periode tertutup | Pembukuan terkendali tanpa mengubah sejarah posted |
| IND-35 | Tanggal dekat batas hari WIB | Hari bisnis konsisten di input, ledger, dan laporan |
| IND-36 | Biaya batch 1.000,01 / 13 PCS | Total alokasi tepat 1.000,01; basis jelas |
| IND-37 | Kebijakan belum diisi | Operasi bergantung padanya ditolak jelas, bukan memakai contoh tarif |
| IND-38 | Pengguna tanpa hak finansial membuka/mutasi data | Nominal terlindungi; mutasi ditolak server |
| IND-39 | Pengguna selain owner mengubah kebijakan owner-only | Ditolak, versi/kebijakan tetap |
| IND-40 | UI sampai API sampai database | Tampilan, input, fakta tersimpan, dan hitungan oracle cocok |
| IND-41 | Rewash gratis dan pencucian ulang berbayar | Sumber/attempt serta biaya dibedakan |
| IND-42 | Rollback sebelum digunakan dan sesudah digunakan | Bila didukung: bersih sebelum pakai; menolak setelah fakta aktif |

## Aturan verdict

PASS hanya untuk observasi baru yang memenuhi oracle independen dan memeriksa efek samping. FAIL memuat langkah reproduksi, expected vs actual, dampak, dan bukti mentah. BLOCKED memuat hambatan lingkungan/kontrak; jangan samakan dengan bug produk atau PASS. NOT_RUN berarti belum dieksekusi. Pemeriksaan setup yang gagal dicatat terpisah, tidak dihapus untuk mempercantik angka.

Jika adaptasi diperlukan karena kontrak API berbeda, input adapter boleh diperbaiki; oracle bisnis tidak boleh dilonggarkan agar hasil aktual cocok. Perubahan rencana hanya append dengan alasan dan waktu. Hasil tidak boleh menyatakan produksi aman atau CP6 keseluruhan lulus dari audit BD saja.

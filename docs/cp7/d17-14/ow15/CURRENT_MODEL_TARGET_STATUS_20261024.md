# Status gabungan uang, model dan target — 25 Oktober 2026

VENI. VIDI. VICI. ERP. — I CONQUERED ERP.
Reliable data adalah dewa. Keuangan termasuk laporan, stok, dan HPP adalah raja.

**Lima kelompok uji pada susunan target berversi terbaru sudah lulus. Uji
pemulihan yang dibetulkan masih berjalan. Skala pabrik bersama keuangan resmi
belum selesai. Formal tetap 5/16; belum ada penerimaan independen atau izin
produksi.** Posisi ini dicatat 25 Oktober 2026 pukul 22.00 WIB. Status run
berikutnya dicatat di [catatan aktif A](ACTIVE_WRITER_A_20261025.json).

Astra A menjalankan estafet Claude: uang, stok, HPP, laporan dan penggabungan.
Penulis B tetap menangani produksi, perencanaan dan bagian analisis yang
sudah dibagi. Bukti komponen B tidak otomatis menjadi bukti susunan gabungan A.

## Hasil aktual pada susunan terbaru

| Kelompok uji | Hasil yang sudah diperiksa | Bukti |
|---|---|---|
| Mesin gabungan, 36 kasus | Semua lulus; keuangan, riwayat, evaluasi model, target berversi dan retur terpilih. Seluruh 22 kelompok katalog, baris, nomor urut, CP6 dan pemeriksaan advisor pulih. | [Native36, `014019a6`](versioned-native36-scoped-fixed-actual-014019a6.json) |
| Layar, 6 kasus | Kebijakan, evaluasi dan target melalui login nyata. Izin yang dicabut menutup panel target. Tampilan target HP/komputer diperiksa; riwayat sendiri dibedakan dari produk pembanding. | [Browser6](versioned-current-browser6-actual-055cbc9a.json), [pemeriksaan tampilan](versioned-current-browser6-visual-review.json) |
| Keuangan, 10 kasus | Tiga alur login dan tujuh persaingan transaksi lulus. Semua 23 kolom hasil perhitungan tetap dibandingkan, termasuk waktu yang dinormalisasi ke UTC; sesi dibersihkan. | [Finance10, `34ecfe89`](versioned-current-finance10-actual-34ecfe89.json) |
| Hak akses dan transaksi bersamaan, 28 kasus | Sembilan alur login dan 19 persaingan transaksi lulus; hak akses terbaru, riwayat, pengulangan perintah dan pemulihan tetap diperiksa. | [Transport28, `34ecfe89`](versioned-current-transport28-actual-34ecfe89.json) |
| Proses server terjadwal | Jadwal menit asli benar-benar berjalan tanpa langkah manual. Operasional selesai, keuangan siap, 24 metrik sama dengan laporan resmi dan pemeriksaan pembukuan terpisah. Nilai belum diketahui tetap UNKNOWN. | [Cron1, `055cbc9a`](versioned-current-cron1-actual-055cbc9a.json) |

Setiap kelompok mempunyai versi sumber dan laporan asli sendiri; hubungan
prasyaratnya diperiksa. Angka kasus bukan jumlah fitur baru. Hasil ini juga
belum membuktikan skala pabrik atau model historis yang unggul.

## Pemulihan sesudah dipakai: satu koreksi urutan data uji

[Percobaan pertama](versioned-current-restore8-first-actual-055cbc9a.json)
menghasilkan tujuh dari delapan langkah lulus. Kedua pemulihan backup penuh,
29 kontrol penolakan, dan pemulihan akhir data lulus. Langkah terakhir gagal
karena target dibuat lebih dahulu daripada dua evaluasi model dalam data uji;
evaluasi yang lebih baru memang membuat target tadi tidak mutakhir.

[Kandidat koreksi `7de9d4b9`](versioned-restore-order2-running-7de9d4b9.json)
menyiapkan target sesudah seluruh evaluasi, kemudian memeriksa bahwa target
masih mutakhir sebelum backup diambil. Semua pemeriksaan bisnis, tujuh berkas
data uji, batas waktu dan 29 kontrol penolakan dipertahankan. Kegagalan pertama
tetap disimpan. Run `40202238928` masih menjalankan pemulihan aktual pada
pembaruan ini; hasil lulus belum diklaim.

## Performa dan skala pabrik

Kandidat A `1b7dbf30` sudah menyiapkan penggabungan tepat dua fungsi optimasi B
yang mempunyai bukti komponen sebelumnya. Rantai uji berikutnya menunggu hasil
pemulihan aktual di atas: mesin 36 kasus, lalu lima kelompok pemulihan/layar/
akses/keuangan/proses server, terakhir 1.200 SKU × tiga ukuran dengan angka
keuangan dan HPP resmi. Semua tujuh deklarasi uji performa belum diikat;
belum ada hasil runtime A untuk kandidat ini.

[Kandidat terbaru B `dd22f085`](B-dd22-initial-component-intake.json)
menambah fungsi privat untuk mengambil satu salinan sumber lengkap lalu
menjalankan mesin hitung yang sama terhadap salinan tersebut. Belum ada
pemasangan ke jalur permintaan aplikasi atau unit pekerjaan, dan belum masuk
susunan A. Uji komponen pengambilan sumber baru masih berjalan. Pada kepala
kode ini, komponen stok empat kasus dan dua regresi lama berjumlah 36 kasus
sudah lulus; pengulangan diagnostik empat kasus pada kepala sebelumnya
disimpan terpisah tanpa menambah klaim kecepatan atau penerimaan.

[Uji pabrik B terbaru](B-factory-dd22-first-actual-dd22f085.json) tetap
INCOMPLETE: permintaan pendahulu melewati batas delapan detik. Pemulihan
katalog/data, CP6 dan advisor lulus, tetapi perbandingan pabrik lengkap belum
tercapai. Uji tersebut masih memakai jalur permintaan lama; ia tidak menguji
pemasangan fungsi pengambilan sumber baru ke aplikasi. Tidak ada pelonggaran
batas waktu atau pemilihan hanya hasil tercepat.

## Lingkup A yang tetap dijaga

| Lingkup | Posisi dan batas |
|---|---|
| Pembayaran supplier (OW-06) | Bukti satu transfer, alokasi lintas halaman, bayar sebagian, pembalikan dan pemulihan tersedia; penerimaan paket gabungan belum ditutup. |
| HPP dan tutup buku (OW-07) | Penahanan karena prasyarat pool serta aktivasi/pembatalan pada PO selesai teruji; aturan pembagian absen tanpa jahit tidak dikarang. |
| Koreksi uang/HPP (OW-08) | Kredit sah dalam laporan, sumber kasbon, koreksi FG/QC dan cuci tanpa tarif mempunyai bukti; kelebihan bayar/piutang vendor laundry masih menunggu keputusan bisnis. |
| Delapan daftar (OW-09) | Urutan dan filter seluruh hasil lintas halaman mempunyai bukti; fitur ekspor baru tidak diklaim. |
| Keuangan skala pabrik (OW-12a) | Sumber angka resmi, 24 metrik dan proses server sudah teruji pada cakupan yang disebut di atas; 3.600 varian bersama keuangan/HPP belum selesai. |
| Penggabungan dan paket auditor (OW-15) | Menjaga satu versi yang dapat ditelusuri, kegagalan pertama, pemulihan penuh dan pembanding CP6. Audit independen tetap terpisah. |

Rincian bukti penutupan awal tetap ada di
[peta pekerjaan](../../OPEN_WORK_D17_14_20261020.md) dan
[peta kualifikasi](CURRENT_QUALIFICATION_MAP_20261024.md).
Perubahan terakhir ini memperbarui posisi pengujian A, bukan menutup butir B.

## Pekerjaan terbuka dan aturan penerimaan

Selesaikan pemulihan terkoreksi, rantai performa, skala pabrik dengan keuangan
resmi, pemetaan seluruh batas CP6, lalu paket satu kandidat untuk pemeriksa.
Hasil AI135 dan Race36 sebelumnya tetap INCOMPLETE. Dua puluh satu kegagalan
CP6 dan empat kasus browser baseline tetap ditampilkan bersama pembanding;
keputusan pensiun layar mengikuti ruang lingkup pemeriksaan yang disetujui.

Kebijakan kelebihan bayar laundry, kredit retur yang sudah terpakai, pembagian
absen tanpa jahit dan batas umur koreksi HPP tetap mengikuti keputusan owner.
Metode yang datanya belum cukup memakai baseline atau UNKNOWN sesuai kontrak.
Kegagalan dan laporan asli lama tidak diubah; tes penulis yang lulus bukan izin
produksi. Checkpoint disimpan, lalu pekerjaan yang sudah diotorisasi diteruskan.

# HANDOFF BERSAMA A + B — ANALISIS BESAR, PROGRES NYATA, TETAP EFISIEN

Sumber: arahan owner di chat Writer A, 26 Oktober 2026. Isi keputusan di bawah
disalin utuh. Dicatat sebagai D17-18; batas kepemilikan D17-17 tetap berlaku.

Keputusan Bos: analisis besar boleh memakan waktu lebih lama dari 8 detik, asalkan pengguna melihat progres yang jujur dan mengetahui apakah proses sedang berjalan, selesai, atau gagal. Kelonggaran ini khusus pekerjaan besar, bukan untuk semua operasi.

Pegangan tetap:
“VENI. VIDI. VICI. ERP.”
“Reliable data adalah dewa.”
“Keuangan—termasuk laporan—stok, dan HPP adalah raja.”

1. RUANG LINGKUP

Berlaku untuk analisis seluruh pabrik, ribuan SKU/ukuran, perhitungan historis besar, serta analisis gabungan produksi dengan keuangan/HPP.

Pencarian biasa, membuka detail, filter daftar, dan simpan transaksi sehari-hari tetap ditargetkan cepat. Jangan mengubah semua operasi menjadi pekerjaan latar belakang.

Jika penyimpanan pilihan memicu perhitungan seluruh pabrik, pisahkan perhitungan berat dari penyimpanannya. Pemeriksaan sumber, kelayakan, dan hak akses saat penyimpanan tetap wajib.

2. KELONGGARAN BUKAN IZIN MEMPERLAMBAT

Analisis tetap harus seefisien mungkin. Waktu tambahan hanya digunakan jika volume data dan pekerjaan yang memang diperlukan membutuhkannya.

* Jangan menambah hitungan, mengulang pembacaan data tanpa alasan, atau menghitung ulang seluruh pabrik jika cukup bagian yang berubah.
* Pertahankan optimasi yang sudah benar. Hasil sebelumnya hanya boleh digunakan kembali jika sumber dan ketergantungannya masih valid.
* Operasi kecil tetap cepat. Analisis besar juga harus selesai secepat yang wajar tanpa mengorbankan ketepatan.
* Jangan menambah jeda, memperlama animasi, atau menahan hasil yang sudah siap demi menampilkan loading.
* Ukur waktu proses dan jelaskan jika memburuk. Jangan langsung menaikkan batas waktu untuk menutupi masalah.

3. PERILAKU YANG DIMINTA

* Jalankan pekerjaan besar secara bertahap di belakang layar agar halaman tetap bisa dipakai.
* Tampilkan tahap aktif, waktu berjalan, serta jumlah pekerjaan selesai/total jika tersedia.
* Persentase harus berdasarkan pekerjaan nyata. Jangan memakai timer untuk mengarang kemajuan.
* Jika total belum diketahui, tampilkan tahap seperti “Menyiapkan data…” tanpa persentase palsu.
* Bedakan progres tahap dengan progres keseluruhan. Selesai menghitung SKU belum berarti seluruh analisis selesai jika keuangan masih diproses.
* Pengguna boleh pindah halaman atau membuka kembali aplikasi dan melihat pekerjaan yang sama beserta progresnya.
* Cegah pekerjaan dobel akibat klik ulang, respons hilang, atau pemuatan ulang halaman.
* Bedakan status mengantre, berjalan, selesai, gagal, dan tertahan karena data/config belum lengkap.
* Jika proses macet atau gagal, tampilkan penjelasan yang bisa dipahami dan pemulihan yang aman. Jangan loading tanpa akhir.
* Hasil parsial tidak boleh diberi label lengkap. Hasil sebelumnya boleh tetap terlihat dengan tanggal dan status yang jelas.

4. BATAS WAKTU DAN KONSISTENSI DATA

Batas total 8 detik tidak lagi menjadi syarat universal bagi analisis besar.

Ini bukan izin memperpanjang semua query atau menahan transaksi/database lock tanpa batas. Gunakan pekerjaan bertahap dengan transaksi pendek, batas waktu tiap tahap, deteksi proses macet, dan pemulihan yang aman.

A dan B menentukan batas teknis berdasarkan pengukuran, lalu mencatat alasan dan buktinya. Jangan menaikkan batas berulang hanya agar tes hijau.

Sumber data harus konsisten selama analisis. Perubahan data di tengah proses wajib ditangani secara eksplisit. Jangan mencampur angka dari waktu berbeda tanpa penjelasan. Hasil analisis lama tidak boleh langsung mengesahkan transaksi baru tanpa pemeriksaan kondisi terkini.

5. PEMBAGIAN KERJA

B:

* Tangani analisis produksi/perencanaan besar dan tampilan progres pada bagian milik B.
* Sediakan status dan progres yang bisa dibaca kembali.
* Koordinasikan kontrak pemanggilan dengan A sebelum mengubah antarmuka bersama.

A:

* Tetap pemilik keuangan, stok/HPP, dan integrator tunggal.
* Integrasikan analisis produksi dengan perhitungan keuangan resmi.
* Pastikan status, progres, hasil akhir, dan pemulihan konsisten pada versi gabungan.

Gunakan mekanisme pekerjaan bertahap yang sudah ada sejauh memungkinkan. Jangan membangun ulang arsitektur tanpa kebutuhan yang terbukti. Pembagian kepemilikan A/B tetap berlaku.

6. PENGUJIAN DAN BUKTI SELESAI

Buktikan pada data skala besar:

* Progres sesuai pekerjaan nyata dan halaman tetap bisa dipakai.
* Membuka ulang aplikasi menampilkan pekerjaan yang sama.
* Klik ulang atau respons hilang tidak menggandakan pekerjaan/transaksi.
* Kegagalan dan proses macet terlihat jelas serta dapat dipulihkan dengan aman.
* Hasil akhir cocok dengan perhitungan resmi, termasuk keuangan/HPP.
* Waktu proses diukur dan tidak ada perlambatan yang tidak dijelaskan.

Uji operasi kecil yang terdampak agar tetap cepat. Selama pengembangan, fokuskan pengujian pada perubahan dan ketergantungannya; pemeriksaan lengkap tetap dilakukan pada kandidat gabungan sebelum penerimaan akhir.

Pertahankan bukti kegagalan lama. Hasil yang diterima berdasarkan kebijakan waktu baru harus dicatat sebagai kebijakan baru, bukan mengubah kegagalan lama menjadi keberhasilan.

7. BATAS YANG TETAP WAJIB

Jangan melonggarkan kebenaran saldo, stok, HPP, hak akses, idempotensi, pemulihan data, maupun larangan menghitung WIP dua kali.

Kegagalan yang penyebabnya belum diketahui harus tetap diselidiki; jangan otomatis dianggap masalah batas waktu.

Perubahan ini tidak otomatis menutup scope, meluluskan audit, atau memberi izin produksi.

Tujuan Bos: analisis efisien, angka benar, dan waktu tunggu transparan. Lanjutkan pekerjaan dalam pembagian A/B yang berlaku. Laporkan hambatan yang benar-benar teratasi dan pekerjaan yang masih tersisa.

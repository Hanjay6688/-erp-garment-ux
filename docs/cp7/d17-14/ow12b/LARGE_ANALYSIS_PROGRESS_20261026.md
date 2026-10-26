# Analisis besar — keputusan owner dan kontrak pelaksanaan B, 26 Oktober 2026

Sumber: arahan langsung owner dalam percakapan Writer B, berjudul
“HANDOFF BERSAMA A + B — ANALISIS BESAR, PROGRES NYATA, TETAP EFISIEN”.
Dokumen ini merangkum pelaksanaan; bukan penambahan keputusan bisnis.

> Keputusan Bos: analisis besar boleh memakan waktu lebih lama dari 8 detik, asalkan pengguna melihat progres yang jujur dan mengetahui apakah proses sedang berjalan, selesai, atau gagal. Kelonggaran ini khusus pekerjaan besar, bukan untuk semua operasi.

> Jika penyimpanan pilihan memicu perhitungan seluruh pabrik, pisahkan perhitungan berat dari penyimpanannya. Pemeriksaan sumber, kelayakan, dan hak akses saat penyimpanan tetap wajib.

> Jangan menaikkan batas berulang hanya agar tes hijau.

> Hasil yang diterima berdasarkan kebijakan waktu baru harus dicatat sebagai kebijakan baru, bukan mengubah kegagalan lama menjadi keberhasilan.

## Kontrak yang berlaku

- Analisis seluruh pabrik, ribuan SKU/ukuran, riwayat besar dan gabungan dengan
  keuangan/HPP boleh melampaui delapan detik secara keseluruhan. Pencarian,
  detail, filter dan simpan harian tetap cepat. Tidak mengubah seluruh operasi
  menjadi pekerjaan latar belakang.
- Pakai pekerjaan bertahap yang sudah ada, transaksi pendek, batas tiap tahap,
  pendeteksian macet dan pemulihan aman. Batas teknis ditentukan dari pengukuran,
  dicatat alasannya. Tidak menambah jeda atau animasi untuk memperlama hasil.
- Optimasi lama yang benar dipertahankan. Penggunaan ulang hasil memerlukan
  sumber dan ketergantungan yang masih valid. Hindari pembacaan/hitungan ulang
  tanpa alasan dan perhitungan seluruh pabrik bila cukup bagian yang berubah.
- Tahap aktif, waktu berjalan dan selesai/total harus berasal dari pekerjaan
  nyata. Total belum diketahui: tampilkan tahap tanpa persentase. Progres tahap
  dipisah dari keseluruhan; produksi selesai tidak berarti keuangan selesai.
- Pindah halaman, buka ulang, klik ulang dan respons hilang tetap mengacu pada
  pekerjaan/UUID yang sama. Pisahkan antre, berjalan, selesai, gagal dan
  tertahan karena data/konfigurasi. Gangguan harus terlihat dan dapat dipulihkan;
  loading tidak boleh tanpa akhir. Hasil parsial bukan hasil lengkap; hasil
  terdahulu harus bertanggal dan diberi status jelas.
- Sumber konsisten dalam satu analisis. Perubahan sumber ditangani eksplisit;
  hasil lama tidak mengesahkan transaksi baru. Saldo, stok, HPP, hak akses,
  idempotensi, pemulihan dan larangan menggandakan WIP tidak dilonggarkan.
- B memiliki produksi/perencanaan dan progresnya. A tetap pemilik keuangan,
  stok/HPP dan integrator tunggal. Kontrak bersama dibicarakan melalui
  `KOORDINASI.md` sebelum diubah; pemasang dan antarmuka A tidak diambil B.
- Uji skala besar: progres nyata, halaman dapat dipakai, pemulihan pekerjaan
  yang sama, anti-duplikasi, kegagalan/macet, hasil identik perhitungan resmi dan
  waktu terukur. Uji kecil yang tersentuh tetap dilakukan. Kualifikasi lengkap
  tetap di kandidat gabungan. Kebijakan ini tidak menutup scope/audit/produksi.

## Implementasi B yang sedang dikerjakan

Pakai `cp7_analysis_stage.jobs/units`, runner K4 dan request frozen-v2 yang
sudah ada. Progres B membaca `stage`, `units_done`, `unit_count`, `plan_final`,
`targets_done_in_stage`, `targets_total`, `last_progress_at`, `worker_active`
dan `server_runner`. Tidak mengarang total akhir saat rencana masih tumbuh.
Keuangan tetap dari sidecar A; tidak menghitung persentase gabungan dari unit
produksi dan unit keuangan yang berbeda bobot.

Antarmuka bersama belum diubah. Permintaan untuk A: pertahankan identitas
request/query/clock/source yang sama dalam gabungan, status keuangan resmi
dan hak akses terbaru, serta runner/pemulihan menyeluruh. Bila diperlukan
status antre/tertahan eksplisit atau waktu awal/akhir resmi, tambahkan melalui
kontrak versi yang disepakati; jangan menebak status database dari timer.

Langkah B berikutnya: perbaiki observabilitas/progres dan batas tunggu klien;
pisahkan rekonstruksi berat pembanding setelah K3 dari simpan pilihan dengan
memakai pekerjaan bertahap. Rekonstruksi tidak boleh mengubah acuan lama,
menghidupkan cache yang dihapus secara diam-diam, atau melewati dua pemeriksaan
sumber/hak akses saat simpan.

## Bukti sebelum kebijakan baru

Cutting4826 Native6/run40244633440 PASS6; Transport10/run40244633462 PASS10;
cutting f843 actual Auth/run40246233021 PASS2. Complete Originals, sumber,
deklarasi dan seluruh gerbang paket telah diperiksa. Waktu checked SAVE
skala3602: 5285.194/5339.539ms. Ini pengamatan satu run, bukan janji SLA.

Choice f843 Native6/run40246232934 tetap5PASS/1INCOMPLETE. Cached SAVE7220.494ms;
K3 berhenti8029.112ms. Diagnostik UUID/payload sama tanpa profiling juga
berhenti8003.031ms, semua efek dibatalkan. Ini belum terselesaikan dan tidak
diubah menjadi PASS oleh kebijakan baru. Eksperimen diagnostik JIT tambahan
yang belum diterbitkan disimpan lokal dan tidak dipasang ke produk.

Formal keseluruhan5/16, B belum selesai, independent_acceptance=false,
production_go=false. A+B finance, pemasangan bawaan dan pemulihan gabungan
masih memerlukan bukti tersendiri.

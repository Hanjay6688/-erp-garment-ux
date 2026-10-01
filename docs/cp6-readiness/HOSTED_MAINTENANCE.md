# Pemasangan pertama CP6 di hosted: paket untuk persetujuan

Target historis paket: **ERP Enteng (`siimvrusnzxexizpyoib`)**, baseline G-01 yang sudah dicocokkan secara baca saja. ERP-Garment (`vlxdhpkjeevubjxexnfo`) adalah proyek berbeda; tidak dianggap otomatis cocok atau target pemasangan. Paket yang dipakai hanya `supabase/release/cp6-t3/MANIFEST.json`, 30 SQL AC–BF sesuai urutan manifest, dari source CP6 yang diterima. Cabang CP7 tidak dipasang.

## Sebelum menjadwalkan

1. Periksa receipt Native/Shell terbaru, identitas source, 30 hash paket, hasil advisor dan pemulihan. Tidak ada langkah dengan FAIL/INCOMPLETE yang diterima.
2. Owner/keuangan meninjau delapan isian nyata pada README. Catat akun/kategori yang dipilih, unsur vendor yang dipakai, serta yang sengaja tidak digunakan. Empat keputusan tertulis boleh disiapkan sebagai formulir; pemasangan schema tidak berarti pengaturannya sudah SET.
3. Tentukan tanggal, durasi, pelaksana dan batas berhenti. Persetujuan harus menyebut **ERP Enteng** serta penghentian transaksi sementara. Persetujuan perbaikan kode tidak dipakai sebagai persetujuan maintenance.
4. Jalankan `scripts/cp6_readiness_hosted_preflight.sql` melalui koneksi yang benar. Periksa versi Postgres, ledger dan katalog terhadap predecessor AB, kapsul historis dan ACL yang dipin paket. Bila beda, berhenti; jangan melemahkan guard atau menyesuaikan pin berdasarkan tebakan.
5. Pastikan tersedia akses pemulihan di luar database sasaran. Ketersediaan backup hosted atau PITR bukan dianggap bukti backup telah dipulihkan.

## Dalam jendela yang disetujui

1. Aktifkan maintenance aplikasi dan hentikan writer, integrasi, scheduler serta koneksi layanan ke sasaran. Tutup admission memakai mekanisme maintenance yang sudah dimiliki paket. Kosongkan sesi lain dan transaksi terbuka; pastikan tidak segera tersambung kembali. Jangan menyamakan maintenance aplikasi dengan admission database yang tertutup.
2. Ambil backup konsisten **sebelum** pemasangan, record katalog/ACL/ledger, hash isi dan jumlah baris sumber. Pulihkan backup ke lingkungan terpisah; periksa hasil dan pembacaan mesin. Jika tidak bisa memulihkan atau perbedaannya tidak terjelaskan, berhenti sebelum memasang.
3. Jalankan **applier maintenance CP6 yang sudah diuji**, mengikuti manifest 30 berkas. Jangan memakai apply_migration biasa atau editor SQL yang melewati closed admission. Record PASS/refusal tiap berkas, ledger, pin katalog dan kapsul. Bila ada refusal, hentikan; jangan lompat berkas.
4. Setelah schema terpasang dan sebelum admission transaksi umum dibuka, owner login melalui akses maintenance terkontrol. Baca versi pengaturan saat itu dan simpan nilai yang disetujui lewat RPC Native, dengan expected version, alasan dan request ID. Simpan receipt pengaturan. Jangan menyalin akun/angka fixture CI atau mengisi tabel policy secara langsung.
5. Jalankan canary yang telah disepakati: tarif vendor, satu kiriman/penerimaan ukuran nyata, satu invoice, satu kredit retur bila fitur digunakan, serta pembacaan HPP/utang/jejak dokumen. Canary menyebut sumber dan tanggalnya; setiap kebalikan memakai alur dokumen Native, tanpa delete/update data manual. Bila memakai data nyata, gunakan transaksi dan dokumen bisnis yang memang disetujui owner.
6. Bandingkan advisor sebelum/sesudah. Kelas INFO `rls_enabled_no_policy` pada tabel privat ERP hanya boleh diterima sesuai keputusan historis dan ACL/fasadnya; temuan baru lain harus dijelaskan atau menjadi HOLD. Periksa akses lintas peran, ledger, uang, stok, HPP dan hash data historis.
7. Buka admission dan aplikasi hanya setelah semua gate disetujui pelaksana dan owner. Pantau transaksi pertama dan pesan pengaturan yang belum siap; simpan hasil sebagai **pemasangan hosted pertama**, tidak digabung dengan receipt CI.

## Bila harus berhenti atau pulih

- Paket rollback hanya untuk komponen yang belum dipakai, dengan guard identitas dan admission yang sama. Jika ada pemakaian, rollback harus menolak; jangan memaksa penghapusan.
- Bila database belum pernah dipakai sesudah backup, restore backup melalui jalur pemulihan yang telah diuji, lalu periksa katalog, isi, ledger dan pembacaan mesin.
- Bila sudah ada transaksi baru, tetap maintenance. Owner dan pelaksana menilai konsekuensi pemulihan terhadap transaksi tersebut; jangan diam-diam menghilangkan transaksi. Catat batas data yang dipulihkan dan rekonsiliasi yang diperlukan sebelum membuka kembali.

Status paket ini: **siap ditinjau, belum dijalankan di hosted**. Durasi/jadwal dan isian nyata belum diisi karena tidak terdapat keputusan terbaru yang menyebutnya.

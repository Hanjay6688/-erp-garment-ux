# Rencana uji Sol r4 sebelum eksekusi

Kandidat produk: `663f6faefcbb9c70f0f99bbc7e78164e03521329`, tree `023f3554432f80f994439f5d0b8cc164846a2041`.
Dokumen writer terbaru: `5eda90e10b2e87485ab710e9fd9ffa68d81a3565`. Auditor membaca panduan Pro Max seluruhnya,
HANDOFF_SOL, README, CROSS_AUDIT writer atas r3, R4_WRITER_HANDOFF, CLAUDE, best practice, dan keputusan owner.
Tidak ada AGENTS.md yang ditemukan dalam checkout. Belum membaca hasil auditor lain pada r4.

## Batas dan asal

341 kasus CP17 dijalankan utuh menggunakan kasus, fixture, dan oracle writer yang dipin. Eksekusi Sol akan memberi
bukti runtime mandiri; rancangan kasus tersebut tetap berlabel writer atau reproduksi auditor r3 yang disebut writer.
Tabel berikut adalah expected kontrak yang Sol tetapkan sebelum hasil dibaca, bukan probe baru yang dijalankan.
Kredit runtime tetap nol sampai hasil per ID, jumlah kemunculan, nilai, dan identitas benar-benar diperiksa.

Probe baru yang tertahan oleh pemeriksaan otomatis pada sesi r3 tidak dimasukkan atau dijalankan ulang. Pesan yang
diketahui adalah `content was flagged for possible cybersecurity risk`; aksi persis yang ditolak tidak tersedia pada
checkpoint lane ini, sehingga tidak ditebak. Workflow ini menyalin kualifikasi writer yang sudah ada, pada server
sekali pakai, dan tidak melanjutkan rancangan probe tertahan melalui jalur lain. Bila aksi tertentu ditolak lagi,
aksi itu dihentikan dan alasan aslinya dipertahankan.

## Expected kontrak Sol

| Risiko / kebutuhan | Expected yang ditetapkan sebelum hasil | Bukti dan batas yang diperiksa |
|---|---|---|
| R4-01, jalur publik lama, D14-9 | Semua 25 signature CLOSED menolak sesi Data API dengan SQLSTATE 42501, pesan `CP7_PUBLIC_ROUTE_CLOSED`, dan nama route yang tepat sebelum efek bisnis. Fasad aplikasi yang sah tetap berfungsi. | Per ID HTTP, Auth/PostgREST sungguhan di loopback; snapshot efek sebelum/sesudah; kontrol sesi DB dipisahkan. Grant DB lama bukan otomatis bukti akses internet. Sensus juga memeriksa anon dan route baru yang belum ditinjau. |
| R4-02, buka ulang PO, D15-4 | Penyesuaian masuk dan pembaliknya memberi perubahan bersih nol. Untuk 10 PCS: 10 → 12 → 10; HPP dan lineage tetap, PO boleh dibuka ulang. Pemakaian aktif 2 PCS tetap menghalangi walau ada pasangan penyesuaian lain. | Hasil stock, HPP, status dan sumber blocker sebelum cleanup; selesai ulang tidak menambah stok/HPP. Dua sesi harus punya urutan lock/commit yang teramati dan hanya satu perubahan sah. Oracle reproduksi semula milik Astra r3 diberi asal itu. |
| R4-03, daftar audit lengkap | ID bukan urutan commit. Baris dengan ID lebih kecil yang commit di dalam cutoff dan filter menambah jumlah isi satu dan jumlah ID sebesar ID itu; halaman berikut wajib berkata berubah. Baris di luar filter tidak mengubah tanda daftar itu. Muat ulang menampilkan setiap baris relevan tepat sekali. | Barrier tiga sesi, ID dan waktu commit, tanda sebelum/sesudah, cursor/cutoff, respons `changed`/`newer`, serta UI Muat ulang. Daftar biasa tidak boleh selalu dipaksa berubah. Cursor tidak sah harus ditolak dengan alasan tepat. |
| R4-04 dan D16-1, keterbacaan | Rasio `(L_terang+0.05)/(L_gelap+0.05)` setiap teks terlihat minimal 2:1, angka WIP utama minimal 4.5:1; tidak ada menu tersambung yang hilang. | Desktop dan HP, build biasa dan Enteng, data terisi; latar/gradien/opacity diwarisi ikut dinilai. Sensus teks bukan bukti seluruh perjalanan transaksi. |
| R4-05, guard global | Hasil guard baru sama dengan guard sebelumnya untuk setiap caller/konteks yang diuji. Tanpa row konteks milik backend dan transaksi sekarang, hanya aturan role akhir menentukan. Bila row itu ada, urutan dispatch serta penolakan rinci lama tetap dijalankan. | Bentuk sumber, daftar tabel identik, hash predecessor, hasil dan SQLSTATE lama-lawan-baru, row transaksi/backend lain, service role, pengguna tak dikenal dan caller sah. Delapan caller writer dicatat sebagai delapan, bukan seluruh ruang kombinasi role/konteks. |
| D14-2, tanggal utang upah | Pembayaran biasa sebelum accrual ditolak; pembayaran pada/sesudah accrual sah jika syarat lain terpenuhi. Kasbon merupakan jalur tersendiri dan tidak melonggarkan payroll biasa. | Native, HTTP, browser; saldo dan jurnal tidak berubah pada penolakan. |
| D14-3 / D15-1, kas | Saldo kumulatif setiap akun harus nonnegatif pada seluruh tanggal ekonomi dan tanggal buku, dinilai di keadaan akhir satu perintah majemuk. Koreksi sah tidak ditolak hanya karena langkah balik sementara. | Kas kosong, tepat nol, pembayaran mundur, tanggal sesudahnya, koreksi dan dua sesi. Nilai akhir, pihak, akun dan kedua dasar tanggal diperiksa terpisah. |
| D15-5, cutover | Transaksi operasional baru sebelum 00:00 WIB tanggal resmi ditolak di server; tepat batas boleh. Saldo awal, invoice terlambat, pelunasan dan koreksi lama memakai pengecualian sumber resmi, tanpa efek ganda. | Trigger jurnal/stok, jalur positif, batas sehari sebelumnya, replay dan kegagalan di tengah. Ini memakai tanggal sintetis; tidak membuktikan cutover produksi. |
| HPP dan review | Pembatalan/replacement pool menghapus hanya alokasi yang dibalik, mempertahankan sumber dan total yang sah. Periode tertutup, izin dicabut, serta token review yang basi menolak atomik dengan alasan yang dimaksud. | Native/HTTP/dua sesi; sumber HPP, stok, jurnal dan nilai sebelum cleanup. D16-4 tetap membatasi pilihan tarif baru ke Owner/Admin sebelum mode per-PO dinyalakan. |
| R4-Q1, pg_cron | Terlihatnya efek bisnis belum cukup: setelah uninstall dan sesi tenang, minimal satu run selesai dan semua run wajib punya akhir tertulis serta status sukses. Menunggu paling lama 60 detik tidak mengubah expected kasus. | K4/K6 Original JSON dan log: waktu cabut jadwal, sesi, run detail, hasil bisnis, timeout/refusal; hasil pertama candidate 769f2cc3 tetap dipertahankan sebagai writer failure yang terpisah. |
| D17-2, kinerja | Target interaksi 3 detik tetap berlaku. Sampel finance yang lebih lambat tetap OPEN, sekalipun job/kasus measurement PASS. Batas 8 detik dan pemeriksaan sumber/akses/hash/kelengkapan tidak dilonggarkan. | Measurement ID, ukuran data, mode direct/finance/staged, waktu aktual dan refusal dipisahkan. Pengecualian background owner 7 Okt tidak diterapkan otomatis pada semua mode. Writer melanjutkan finance pada branch terpisah sesudah audit ini. |
| Backup replacement, D13-9a | Patch CP7C yang belum dipasang bukan PASS kandidat. Perubahan scratch dan risiko r3 dipertahankan dengan disposisi OWNER_DEFERRED_CP7C. | Baca patch dan kontrak saja; tidak memasang patch, tidak menyentuh Drive/hosted atau menjalankan probe restore baru. |

## Urutan kualifikasi

1. CP17 lengkap: 161 Native, 39 race, 27 Auth HTTP, 57 browser biasa, 57 browser Enteng. Himpunan 341 ID disimpan
   dalam `CP17_PREEXECUTION_MANIFEST.json`; tidak ada hasil ganda, ID hilang atau INCOMPLETE yang dihitung PASS.
2. Tentukan suite lanjutan dari call graph bundle dan perubahan r4: gabungan F03 untuk guard uang/stok/HPP/review,
   P19 untuk report/otoritas dan pengukuran direct/finance, serta K4/K6 untuk penjadwal. Rencana file dan ID fase
   dibekukan sebelum meminta publikasi. Penerimaan r3 yang tidak terpengaruh dapat dipertahankan dengan label kandidat lama.
3. Frontend: build/type check dan sensus lebar HP/keterbacaan terdampak; retained journey r3 diberi batas yang benar.
4. Lengkapi disposisi CP1–CP7: inventaris fungsi, 82 invarian, 29 skenario dan 20 sambungan. Bukti asal, bagian yang
   tidak diuji, keputusan penundaan dan gate produksi dicatat. Tidak menggunakan rasio test case sebagai persentase ERP.

Tidak ada rerun identik sesudah kasus berjalan untuk mencari hijau. Koreksi alat yang terbukti cacat, bila diperlukan
dan diizinkan, menjadi kualifikasi terpisah dengan diff, identitas dan first-result tetap tersimpan. Laporan disegel
sebelum pembacaan peer r4. `feature_complete`, `audit_complete` dan `production_go` belum dinyatakan benar.

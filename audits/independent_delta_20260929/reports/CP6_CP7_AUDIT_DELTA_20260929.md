# Audit independen perubahan CP6 dan cangkang CP7

Tanggal: 29 September 2026 WIB. Pemeriksaan selesai pada kandidat yang dibekukan di bawah.

**Hasil: revisi CP6 yang diuji lulus; tidak ada bug CP6 baru yang terbukti dalam pemeriksaan ini. Satu temuan aktif berada di penyaringan data cangkang CP7 sebelum integrasi data asli.**

Ini audit perubahan sesuai permintaan owner: pertahankan yang sudah aman, uji dampak kebijakan baru dan CP7. Ini bukan sertifikasi ulang seluruh kombinasi CP6, bukan izin produksi, dan bukan alasan mengulang pekerjaan writer yang buktinya sudah lengkap.

| Kandidat | Commit |
|---|---|
| CP6 writer | `cce68d37083ac2d477f559e3192c7bc8d459aebf` |
| Paket produk CP6 terakhir sebelum dokumentasi/bukti | `91445b4e1cd6a6c5363b70b92fdc7d71020a21cc` |
| CP7, PR #31, draft | `6465825d0f8a865f28264626a4e0af818d66967e` |
| Audit awal | `3853afe12a0f92ce8d92a0cb45a061d7841abf6b` |
| Retest terarah dan browser CP7 | `d3106cdf1f3ec524125f07fb900aeef219550105` |

Head writer dan PR #31 diperiksa ulang setelah pengujian; keduanya masih sesuai pin. Berkas `src` dan `supabase` CP6 tidak berubah antara `91445b4` dan `cce68d3`. Tidak ada kode produk diubah oleh auditor. Audit hanya menambah oracle, probe, dan workflow pada branch audit tersendiri. Tidak ada akses production/UAT/legacy, merge, deployment, atau pengiriman pesan ke writer.

## Hasil tes auditor sendiri

Oracle dan pemeriksaan berikut ditulis auditor. Installer dan pembangun data uji yang sudah ada dipakai sebagai sarana. Ini audit independen setelah membaca perubahan dan handoff, **bukan audit buta**. Bukti writer dipisahkan pada bagian berikut.

**CP6: 11 kasus native + 1 kasus Auth/HTTP lulus, 0 temuan produk, 0 kasus belum selesai pada lingkup probe ini.**

| Yang diuji | Hasil konkret |
|---|---|
| Kredit retur aksesori dan kain, masing-masing satu kasus | Saldo awal 80/100/60. Alokasi 7,13 + 2,87 menghasilkan 90/92,87/57,13; ganti alokasi menjadi 3,01 menghasilkan 83,01/96,99/60. Total tetap 240. Inverse kembali ke awal; fakta gerakan stok/biaya tidak berubah. |
| Replay alokasi lama setelah alokasi diganti | Balasan replay tidak menerapkan kembali alokasi kedaluwarsa dan tidak menambah event. UUID sama dengan isi berbeda ditolak. Ini bukan pengujian pencabutan izin replay. |
| Pembayaran bertanggal lama | Kredit yang dipindah hari ini tidak dapat dipakai untuk membenarkan pembayaran 90 kemarin ketika utang historis hanya 80. Pembayaran 70 yang sah tetap diterima. |
| Riwayat kredit | UPDATE dan DELETE event yang sudah diposting ditolak. |
| SKU pada batas waktu keanggotaan | Sebelum batas memakai SKU lama, tepat pada batas memakai SKU baru. Tidak ada keanggotaan ganda; identitas fisik tidak berubah. |
| Perpindahan range yang dijadwalkan | Keanggotaan masa depan belum berlaku pada waktu sekarang. |
| Laporan HPP historis, invoice, inverse | Nilai FG awal 100. Invoice 73,17 menaikkan nilai kini menjadi 173,17. Snapshot sebelum invoice tetap 100, memakai versi HPP lama dan tetap provisional. Inverse kembali 100 dan status biaya belum lengkap. Tidak diklaim bahwa semua alasan provisional lain telah selesai. |
| Helper privat baru | EXECUTE ditolak bagi anon dan authenticated pada empat helper kredit/alias impor yang dipilih. Ini pemeriksaan privilege SQL, bukan REST langsung seluruh helper. |
| FREE → berbayar | Riwayat FREE tetap nol dan berbeda dari tarif vendor baru 7,13. |
| WAIVED → berbayar | Riwayat WAIVED tetap nol dan tidak berubah menjadi tarif baru. |
| UNKNOWN → berbayar | Riwayat UNKNOWN tetap NULL, tidak diubah menjadi gratis. Tarif tetap berasal dari versi vendor, tanpa tarif SKU pengganti. |
| Sumber kredit untuk pengingat, Auth sungguhan | OWNER dapat membaca; PRODUKSI_QC dan anonim ditolak. |

Run awal [36456038419](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36456038419) mencatat 10 native PASS, 1 Auth PASS, dan 1 INCOMPLETE. Kasus HPP belum memasang kebijakan invoice yang diperlukan dalam fixture. Auditor melengkapi fixture dengan pilihan yang didukung, tanpa mengubah produk atau melonggarkan hasil yang diharapkan. Kasus tersebut kemudian PASS pada [36457111605](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36457111605). Riwayat run pertama tetap disimpan; kesalahan fixture tidak dibebankan ke writer. Kedua run mengonfirmasi primary tidak berubah dan clone uji tersisa nol.

**CP7:**

- 34/34 tes fokus yang sudah tersedia dijalankan ulang auditor dan lulus.
- Build resmi lulus, termasuk pemeriksaan kepemilikan akses/RPC dan pemindaian artefak klien.
- 6/6 alur browser desktop/HP lulus pada kandidat beku, tanpa skip atau flaky. Cakupan: enam pemakai analisis bersama, perubahan kondisi data/akses, salin teks saat clipboard ditolak, navigasi benchmark dan kembali ke ERP. Screenshot desktop/HP ikut diperiksa.
- 7 probe baru auditor: **6 PASS, 1 FAIL**. Hasil sama pada eksekusi lokal dan CI; tidak dijumlahkan menjadi 14 kasus berbeda.
- Enam PASS meliputi identitas fisik tetap saat kelompok SKU berubah, UNKNOWN tidak menjadi Rp0, akses ditolak mengosongkan keluaran, revisi sumber/kebijakan meminta analisis baru tanpa memulai training, alokasi fisik berlebihan ditolak, serta EMPTY/PARTIAL/ERROR tidak memakai keluaran lama.
- Upaya browser lokal gagal sebelum aplikasi diuji karena izin socket lingkungan. Eksekusi dipindahkan ke CI dan lulus; ini bukan bug produk.
- Pemeriksaan gabungan Git dengan CP6 terbaru tidak menemukan konflik teks. Itu belum merupakan uji integrasi aplikasi yang sudah digabungkan.

## Temuan auditor yang masih aktif

**CP7-DELTA-01 — nilai biaya pada perbandingan rencana belum tersaring untuk akses OPERATIONS.**

Prioritas: **sedang pada cangkang; wajib ditutup sebelum menyambungkan data asli. Tidak menjadi blocker CP6.**

Lokasi: [`src/cp7/workspace.ts`, fungsi `projectShell`](https://github.com/Hanjay6688/-erp-garment-ux/blob/6465825d0f8a865f28264626a4e0af818d66967e/src/cp7/workspace.ts).

Reproduksi: isi `plan_comparisons` dengan perbandingan COST berunit IDR senilai `987654321.09`, kemudian panggil `projectShell(..., 'OPERATIONS')`. Input lulus JSON Schema lengkap dan pemeriksaan koherensi cangkang. `metrics` dikosongkan, tetapi `analysis.plan_comparisons[].planned/actual` masih membawa nominal tersebut.

Dampak terbukti saat ini adalah **objek analisis hasil proyeksi masih memuat nominal yang seharusnya disaring**. Contoh bawaan memiliki `plan_comparisons` kosong dan belum tersambung data ERP asli. Nominal perbandingan ini juga belum dirender oleh laporan saat ini. Karena itu auditor tidak menyebutnya kebocoran data nyata, akses finansial production, atau kebocoran browser yang sudah terjadi.

Writer perlu menyaring proyeksi keuangan secara menyeluruh sesuai kewenangan, termasuk perbandingan rencana, sebelum data dibagikan ke laporan, Tanya AI, dan pengingat. Otorisasi backend tetap diperlukan saat adapter asli dibuat. Tes minimal setelah perbaikan: OWNER mempertahankan nilai yang sah, OPERATIONS tidak mendapat nominal terlarang, DENIED tetap kosong, dan data sumber tidak termutasi.

Probe: `audits/independent_delta_20260929/cp7.delta.test.ts` pada branch `audit/cp6-policy-cp7-delta-20260929`. Data lengkap yang lolos schema ada di `cp7.financial-comparison-probe.json`. Artefak CI juga memuat hasil JSON serta screenshot. Job browser berwarna hijau karena langkah kontrak sengaja menyimpan kegagalan lalu melanjutkan pengujian browser; **warna job tidak menghapus 1 FAIL kontrak**.

## Cross-check bukti writer

Ini pemeriksaan log, pin, dan artefak writer, bukan klaim auditor menjalankan sendiri semua kasus di bawah.

| Bukti writer | Hasil cross-check |
|---|---|
| Paket AC..BF | 30 berkas telah tersedia; hash sumber/paket cocok dengan manifest. Builder BF `--check` lulus. Kekurangan lama berupa paket belum sampai BF tidak dipertahankan. |
| [Paket/runtime 36452814728](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36452814728) | Log cocok dengan 90 native + 22 race + 8 Auth/HTTP + 27 browser BF PASS. Bukti tambahan 10 browser AU dipisahkan, tidak dihitung dua kali. |
| Gabungan range/rework | 14 kasus baru di log mencakup R03, R06–R09, R11–R14. Kasus resep sama/berbeda, empat variasi rework, penjualan lalu range pindah/biaya terlambat/retur, alias historis, paket + extra + klaim, dan HPP dua lokasi tercatat PASS. Kekurangan lama berupa belum ada bukti rangkaian tersebut sudah diperbaiki. |
| [Rollback 36450928491](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36450928491) | 147 pemeriksaan PASS; dua siklus dan penolakan sesudah pemakaian. Perbaikan constraint varchar masuk paket; sumber produk setelahnya tidak berubah. |
| BC/BD, build, CodeQL | Status run writer cocok dengan handoff: BC45, BD41, build, CodeQL sukses. Angka ini tetap bukti writer; bukan penamaan ulang audit lama atau kasus baru auditor. |

Hash BF development: `58b97662a093147f3e594987bcc662e0f7cf376aaaf7664364739508ab1fafbd`.

Hash BF release: `fa4dadf5cbab6ac34de94c72c4d67459a2cd1ba28eee33efee965fedc1de8caf`.

Advisor bukan nol temuan: writer mencatat 143 INFO tambahan dari kelas `rls_enabled_no_policy` yang diterima gate terdahulu. Hasil tersebut tidak disamakan dengan nihil temuan keamanan.

## Batas yang tetap dijelaskan, tanpa dijadikan bug baru

- R03: dua SKU berukuran sama dengan referensi pekerjaan berbeda memerlukan wave fisik terpisah. Satu wave ambigu ditolak atomik. Jika ingin satu wave mendukung keduanya, itu perubahan kemampuan bisnis, bukan kegagalan kasus yang sudah lulus.
- R10: `SalesPages.tsx` masih simulasi. Bukti jual/retur native tidak membuktikan posting penjualan dari layar. Audit ini tidak memutuskan sendiri apakah layar tersebut wajib untuk penutupan CP6.
- R14: dua lokasi dan anggota stok nol diuji; filter Grade B kosong bukan bukti persediaan campuran grade yang berisi.
- CP7 masih cangkang sintetis: belum membuktikan adapter ERP, saldo/jatuh tempo asli, reminder terjadwal, pengiriman WA, maupun training/model operasional. Ini batas fase yang diizinkan owner, bukan daftar bug cangkang.
- Kalimat dokumen writer lama “CP7 belum diizinkan” tidak mengalahkan izin owner di percakapan untuk mengerjakan cangkang terpisah.

Keputusan akhir pemeriksaan perubahan: **CP6 delta PASS; 0 blocker CP6 baru yang terbukti. CP7 boleh dilanjutkan sebagai cangkang, dengan CP7-DELTA-01 ditutup sebelum integrasi data asli.** Penutupan checkpoint menyeluruh dan `production_go` tidak otomatis diberikan oleh audit perubahan ini.

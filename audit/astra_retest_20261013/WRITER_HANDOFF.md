# Handoff Astra — retest CP7 7a0b4a90

**FINAL — laporan dan bukti terkunci; tidak ada job retest yang masih berjalan.** Kandidat produk tetap `7a0b4a90af234a906d3cda7fc8ec9fd411a15dd2`; tidak ada perubahan aplikasi dari auditor. Semua temuan, uji mandiri, dan crosscheck digabung dalam handoff ini, dengan asal bukti dipertahankan dalam [REPORT.md](REPORT.md).

## Yang sudah selesai, tidak perlu diperbaiki ulang

- **ASF-F01 CLOSED.** Empat kontrol Astra lama lulus pada kandidat; versi lama tetap memperlihatkan dua counterexample sebagai kontrol sensitif. Lima belas kontrol tambahan dan empat mode nyata memenuhi oracle; seluruh sepuluh anotasi GitHub terbaca. Raw job pertama tetap merah karena kesalahan penghitung luar auditor, yang direklasifikasi dari Original tanpa rerun transaksi. Tidak ada pekerjaan produk yang diminta untuk kesalahan auditor tersebut.
- **Cleanup dan dashboard:** canary analisis A/B, immutability, pemalsuan GUC oleh tiga peran, concurrent step, reopen dan repeat lulus; desktop/HP OWNER/ADMIN tidak menampilkan angka contoh. Keputusan owner 12 Okt tidak dibuka ulang.
- **PL-5:** ADMIN membaca tetapi tidak menulis; perubahan OWNER menjadi ADMIN memblokir UUID lama maupun baru. Rencana yang diterapkan tetap menyimpan versi kebijakan. Regresi PL5 20/20 sudah lulus.
- **Backup kasus dasar:** penolakan database asing sejak awal, database asing yang muncul saat awalnya ABSENT, snapshot saat sumber ditulis, dan sisa scratch milik alat lulus. Jangan merombak jalur yang sudah benar hanya karena ada variasi tambahan di bawah.
- **Nama database jadwal:** mismatch ditolak oleh CLI; pemeriksaan persetujuan install/uninstall bekerja. Tidak ada jadwal produksi dipasang.
- **>5.000 target:** penolakan sudah terjadi di request dengan kode yang dideklarasikan, dibuktikan oleh skenario writer yang dijalankan ulang Astra.

## Satu residual yang memerlukan perbaikan atau batas operasional eksplisit

**ASR-OPS-01 / keluarga F-OPS-01: kepemilikan scratch basi.** [Detail lengkap](ASR_OPS_01.md), [run pertama](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38354577233), kasus `ASD-B05-REPLACED_LEFTOVER`.

Urutannya: scratch lama bertanda → alat membaca OURS → dump berlangsung → admin mengganti scratch dengan database asing bernama sama → alat memakai status OURS lama dan menghapus pengganti → receipt tetap `restore_verified=true`. Canary hilang sebelum teardown auditor; sumber ERP uji tetap utuh. S0 bersyarat mengikuti §8 karena data pengganti terhapus permanen; ini membutuhkan hak administrasi database dan bukan jalur pengguna ERP biasa.

Titik kode: `backup()` di `scripts/cp7_nightly_backup.py`, antara `scratch_state` awal, `tools.drop` setelah dump, dan keputusan cleanup pada `finally`. Jangan hanya mengandalkan status/nama lama. Pertahankan identitas dan cakupan scratch per percobaan, termasuk saat membersihkan sisa. Jika desain sengaja mengecualikan pergantian database oleh admin ketika backup aktif, nyatakan batas itu secara eksplisit; auditor tidak akan menganggapnya disetujui diam-diam.

Retest minimal sesudah perbaikan: `ASD-B01..B05` dengan oracle tetap, kontrol concurrent source write, sumber tetap utuh, tidak ada pruning ketika operasi ditolak, serta penghapusan akhir hanya pada scratch milik percobaan. Perubahan tidak perlu melebar ke transaksi ERP. Jangan jalankan probe pada hosted; workflow audit membangun database sekali pakai.

## Disposisi lain dan penerimaan

- **Versi terbaru:** audit ini menutup retest pada `7a0b4a90`, yang sudah berisi revisi Fable sebelumnya. Saat owner bertanya, HEAD writer sudah `5e96cbcf`; perubahan alat uji/diagnosis/tes tambahan sesudah kandidat belum diterima runtime oleh Astra. Kode `src/`, `supabase/`, `scripts/cp7-src/`, `cp7_nightly_backup.py`, dan helper business-day identik. Jadi counterexample backup masih menunjuk kode yang belum berubah, tetapi jangan melabeli seluruh commit baru sebagai lulus berdasarkan audit ini. Lihat [LATER_WRITER_DELTA.json](LATER_WRITER_DELTA.json).
- **PR44:** Astra tidak menerima optimasi yang ditulisnya. [Catatan maksud probe](PR44_AUTHOR_INTENT_NOTE.md) menyatakan adaptasi `_within` dan mutan masih sesuai tujuan; penerimaan runtime harus oleh Fable/auditor lain.
- **Supplier Payment Create:** 10/10 lulus pada percobaan pertama, pemulihan dan advisor lulus. Eksekusi Astra memakai source/oracle asli ditambah penyimpanan snapshot read-only; sepuluh pembandingan tingkat kelompok/per kasus sama persis. Hasil lama writer yang merah tetap disimpan dan penyebabnya belum diketahui. Tidak ada permintaan memperbaiki produk tanpa counterexample saat ini. Lihat [SUPPLIER_BOUNDARY_REVIEW.json](SUPPLIER_BOUNDARY_REVIEW.json).
- **Kredit dan payroll:** receipt correction 43/43 dan F03 P12 91/91 lulus. Kredit 200 dari pembayaran 1.000 yang dikoreksi menjadi 800 dapat dipakai ke nota berikutnya pada tanggal asli sesuai keputusan owner. Uji WIB pada run ini mengeksekusi zona yang harinya tertinggal; cabang zona yang sudah besok belum aktif pada jam run dan tidak mendapat klaim PASS tersendiri.
- **UI lama:** F03 prefreeze 31/31 kasus CP7 lulus. Dua diagnosis pada runtime CP6 lama tetap INCOMPLETE karena fungsi CP7 tidak dipasang; keduanya nol kredit kasus produk dan Original tetap disimpan.
- **Skala:** lima kasus aplikasi penuh lulus; 5.000 target lewat jalur bertahap menampilkan hasil dalam 86,42–111,49 detik pada data sintetis, sedangkan jalur biasa tetap menolak pada batas produk sumber. Cleanup mempertahankan hasil dan mengurangi payload kolom terukur dari sekitar 126–129 MB menjadi 31,16 MB. Ini bukan penerimaan SLA, seluruh ukuran disk, atau penerimaan PR44.
- Regresi 21/21 suite selesai: 880 eksekusi PASS / 684 ID unik, ditambah sembilan fase rehearsal. Shell 1.726 tes dan enam browser lulus; dua CodeQL nol temuan. Ini tidak menggantikan penerimaan PR44. Area lain yang tidak diulang tetap **BELUM DIULANG pada kandidat ini**, bukan PASS baru. Bukti audit sebelumnya tetap pada commitnya.
- Keputusan owner terdahulu mengenai kredit lintas nota, dashboard, PL5, D11/GBD-03, dan pembagian CP6/CP7 tidak dibuka ulang. Penerimaan audit, tahapan CP1–CP7 berikutnya, dan izin pemasangan tetap terpisah.

`production_go:false` tetap. Hasil lengkap, Original, log gagal pertama, hitungan per kasus, asal oracle/fixture dan hash penguncian tersimpan pada [REPORT.md](REPORT.md), [REGRESSION_RESULTS.json](REGRESSION_RESULTS.json), [FINAL_CI_RECEIPT.json](FINAL_CI_RECEIPT.json), [FINAL_ORIGINALS.tar.xz](FINAL_ORIGINALS.tar.xz), dan [LOCK.json](LOCK.json).

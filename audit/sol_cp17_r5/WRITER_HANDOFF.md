# Handoff Sol r5 untuk writer

Kandidat: `17fa25075ba77f0853c3c16f504288ace03eec35`.

**Uji ulang selesai; CP7 dan audit penuh tetap HOLD.** Paket ini independen. Sol tidak membaca laporan sejawat r5 dan tidak mengubah produk.

## Hasil yang bisa langsung dipakai

|Item|Hasil Sol|Tindakan writer|
|---|---|---|
|SOL-R4-001, S1: alarm palsu Nota FG_REPAIR|**CLOSED pada kandidat r5 yang dipasang di lingkungan uji**|Pertahankan resolver serta pin pemasangan, capture, dan restore yang lolos. Belum dipasang ke Enteng.|
|R5-02: 11 reader lookup akun|**PASS dalam lingkup input, graf panggilan, dan mapping yang diuji**|Gunakan bukti ini dengan batasnya; belum membuktikan seluruh latensi selesai.|
|KNOWN-P19-DIRECT-LATENCY, S2 lama|**OPEN**|Lanjutkan optimasi di cabang terpisah sesuai D17-2; ukur ulang alur yang sama.|
|CP6|**CLOSED dalam lingkup yang sudah diterima**|Pertahankan keputusan CP6/R10.|
|CP7 dan pemasangan Enteng|**HOLD**|Penuhi batas bukti serta pekerjaan CP7C yang sudah diputuskan.|

## Bukti penutupan S1

- Oracle Sol asli tidak diubah: sumber repair 2+1 PCS × Rp2.000 menghasilkan Nota Rp6.000. Seluruh 167 detektor bernilai nol sebelum transaksi, sesudah sumber, DRAFT, POST, dan rollback. Checker lama tetap menghasilkan +2.
- Nota sah → REVERSED Native → Nota pengganti Rp6.000: seluruh 167 detektor nol pada lima tahap; jurnal, stok, dan HPP tetap.
- Kontrol negatif Sol mengekspor 167 output pada enam tahap: awal nol, Nota sah nol, kontraktor salah tepat satu, rollback nol, sumber upah hilang tepat satu, rollback nol. Guard upah dimatikan hanya saat menulis fixture korupsi dan sudah aktif kembali saat pemeriksaan; ini bukan bukti hak akses atau pencegahan oleh guard.
- Run: 39237249873, 39239045650, 39246794670. Rincian: `READER_AND_DETECTOR_RESULT_REVIEW.json`.

## Prioritas produk: kecepatan analisis

|Browser, 100 barang dengan keuangan|Waktu|Target 3.000 ms|
|---|---:|---|
|Histori 1 hari|2.977,1 ms|Terpenuhi pada sampel ini|
|Histori 30 hari|2.936,3 ms|Terpenuhi pada sampel ini|
|Histori 100 hari|3.448,8 ms|Belum terpenuhi|

300 barang operasional membutuhkan 6.219–8.044,2 ms. Pada 300 barang dengan keuangan, histori 1/30 hari membutuhkan 10.241,6/10.714,7 ms; histori 100 hari menampilkan refusal 57014 dalam 8.045,6 ms. Refusal jujur bukan hasil kapasitas berhasil.

Profil diagnosis 100 barang dengan keuangan mencatat `account_id` 2.476 panggilan, `require_internal` 3.652, dan resolver opening FG HPP 588. Ini petunjuk untuk menelusuri kerja berulang, bukan bukti lookup akun satu-satunya penyebab. Kurangi pembacaan book/perhitungan berulang dan evaluasi agregasi per query. Pertahankan izin, source hash, hasil lengkap, batas 8 detik, dan cap produk. Jangan menutup S2 dengan sampling atau perubahan batas.

Staged 5.000 barang **operasional** selesai lengkap pada tiga sampel, masing-masing 26 halaman: 79,24/88,28/108,78 detik. Buka ulang hasil 1,06/1,30/1,41 detik; progress terlihat 2,29/2,62/3,15 detik. Pengecualian staged bernama dinilai tersendiri; seluruh alur tidak menjadi selesai dalam tiga detik. Tidak ada klaim staged keuangan 5.000 barang.

## Penguatan uji permanen

1. `scripts/cp7_r5_cases.py:110`: assert baseline benar-benar nol dan jumlah detektor tepat 167. Saat ini boolean hanya direkam; kontrol Sol terpisah sudah memeriksa output aktual.
2. Bandingkan seluruh 11 badan reader lama **bersama**, supaya nested call juga memakai graf lama.
3. `with_value` yang menerima `'0'` kurang membedakan hasil. Pertahankan PO 120 → FG96/COGS24 → FG108/COGS12, lifecycle +24/−12, SQL NULL untuk jurnal yang hilang, serta empty/multirow.
4. Pertahankan statement PREPARE yang sama saat mapping berubah 120→0→120. Pisahkan masa hidup PREPARE manual dari pembersihan cache psycopg.
5. Simpan semua 167 output pada buku sehat, korupsi terkontrol, dan rollback. Penolakan guard tidak menggantikan kontrol sensitivitas.

Ini saran penguatan uji, bukan lima bug produk baru.

## Batas penutupan penuh

- Detektor r5: 11/167 memiliki kontrol negatif yang qualified; 156 belum memiliki kontrol negatif r5. Gabungan putaran Sol: 22 qualified dan 145 belum qualified. INV-D01 tetap INCOMPLETE.
- Invarian: 74 PASS/8 INCOMPLETE; skenario: 22 PASS/7 INCOMPLETE; 20 sambungan PASS dalam lingkup tertulis. Inventaris 57 kebutuhan/47 layar bukan persentase ERP selesai.
- Sumber cutover bertanda tangan, fresh hosted preflight, pemasangan dari baseline hosted dengan akun serupa hosted, serta cutover/shadow: prasyarat CP7C belum dijalankan Sol.
- Native entrypoint/grant D14-9 dan patch perlindungan backup replacement D13-9a tetap CP7C. K3 masih menulis ke replacement sebelum mismatch. Restore backup terpakai ke **salinan baru** terbukti cocok untuk 590 tabel; uninstall sesudah dipakai bukan restore data exact.
- General `as_known`, probe akses/file cache yang ditahan, serta perangkat Apple fisik belum ditutup Sol. Batas probe lama tidak dilanjutkan melalui nama atau transport lain.
- D17-2 dan keputusan CP7C tidak perlu ditanyakan ulang. Alasan dan tindakan per ID ada di `OPEN_BOUNDARIES.json`. Ini batas Sol; laporan peer r5 tidak dibaca.

## Tiga kegagalan alat auditor tetap dicatat

12 run: 9 SUCCESS/3 FAILURE; 31 job: 28 SUCCESS/3 FAILURE. Tidak ada rerun job asal. Tiga kesalahan alat Sol adalah constructor akun yang kurang field NOT NULL, decoder SQL NULL, dan interaksi cache prepared psycopg. Bukti kualifikasi diterbitkan terpisah dengan oracle angka tetap; hasil mentah 1.036 PASS/3 INCOMPLETE dipertahankan. Empat kontrol decoder murni menambah nol eksekusi Native. Jangan menulis semua CI hijau. Rincian: `AUDITOR_TOOL_FAILURES.json`.

## Berkas kerja

- `FINDINGS.json`: status closed/open, keparahan, kandidat, tindakan writer.
- `RETEST_SOL_17fa2507.md`: laporan lengkap, asal bukti, dan batas.
- `PERFORMANCE_RESULT_REVIEW.json`: ID pengukuran dan angka asli.
- `READER_AND_DETECTOR_RESULT_REVIEW.json`: resolver, 11 reader, PREPARE, dan output negatif.
- Matriks invarian/skenario/sambungan serta `FUNCTION_DETAIL.json`: lingkup dan bukti per ID, dengan bukti lama dipisahkan dari eksekusi r5.
- `RUN_REGISTER.json`, `OWN_CI_RECEIPT_FINAL.json`, `CASE_LEDGER.json`, `COMMAND_LEDGER.json`: pelacakan eksekusi.
- Arsip `Sol-r5-bukti-20261019.zip` sudah disimpan; SHA256 `13d650feb033c02abc4d35d562e53f8503071ff7ffe96e56c78e73445bf43e3c`; CRC PASS. `RAW_EVIDENCE_WHITELIST.json` dan `ARCHIVE_RECEIPT.json` mengunci byte asli.

Tidak ada job Sol yang masih berjalan. Paket ini tidak memberikan persetujuan produksi.

# Jawaban Astra untuk writer — XC1 diselesaikan pada kandidat XC2

Kandidat: **`0b7049d9203bac52b47a4c89f3e0d75646067a8f`**. Tree: **`ce6aed0a0af920e8aa80248f3cabcd293688df18`**. `production_go:false`.

**R2-F05 DITUTUP. R2-A6 LENGKAP. Dua syarat D13-13 terpenuhi dari sisi Astra.** A2 tetap OPEN, nonblocking sesuai D13-10. Tidak ada temuan produk baru dalam cakupan retest ini.

| Butir | Jawaban dan bukti |
|---|---|
| A1 / ASR-OPS-01 | DITUTUP. `ASD-B01..B05` PASS, termasuk database pengganti tetap utuh, sumber tetap, dan tidak ada pruning saat ditolak. Run **38435746105**, job **115429126194**. Oracle lama tidak diubah; fixture owned mark disesuaikan satu baris ke token+OID aktual. |
| R2-F05 | DITUTUP. Kontrol Astra tanda polos pada scratch/pola attempt serta `finally` PASS; keseluruhan **11/11**. K3 `K3C_RACE_BACKUP_PLAIN_MARK_COPIED_ONTO_FOREIGN_KEPT` dan situasi A–D kepemilikan OID juga PASS di run **38435365859**, job **115427813121**, K3 **25/25**. |
| R2-A6 / A6 | **LENGKAP** menurut D13-9c/D13-12 untuk komposisi CP7. Browser P11 desktop dan HP menekan helper; 13→25→13, baris kedua tetap, total Rp520→Rp280, simpan/baca ulang qty `[2,13]`, stok `[17,28]`, tanpa overflow. PASS pada job **115427812633** (P11 **64/64**) dan **115427813178** (prefreeze **31/31**) dalam run **38435365859**. DOM simulasi juga PASS pada job **115427812937**. |
| A2 / R2-D11 | Akar penyebab tetap OPEN, diterima nonblocking. Diagnosis tidak mengubah equality, tidak ada comparator penerimaan baru. Supplier **10/10**, akhir grup pulih, job **115427813220** pada run **38435365859**. Dua log gagal asli tetap tersimpan. |
| A3 | DITUTUP. Gladi jadwal di K3: deklarasi cocok, pasang/lepas, `cron.job` **0→0**, **0** job sempat berjalan, **559** tabel tetap. Hosted tidak disentuh. |
| A4 | F-PAY-01 bukan temuan produk aktif karena sudah ditarik. Catatan cakupan Astra lama dipertahankan; log writer dua cabang aktif telah dibaca dan diberi label reused, bukan PASS independen baru. |
| A8 | DITUTUP dalam cakupan delta. Seluruh 12 berkas alat putaran 1 dibaca; supplier, K3, dan F03 menjalankan runner kandidat. Produk identik dengan ae0214ad dan 7a0b4a90. |

Jumlah baru: **141 eksekusi CI PASS / 139 ID unik**, ditambah satu kasus DOM. Dua ID helper browser muncul pada dua komposisi dan tidak dihitung dua kali sebagai ID unik. Enam job pada attempt pertama, tanpa retry pergantian hari. Dua diagnosis CP6 sebelum pemasangan tetap INCOMPLETE dan mendapat nol kredit produk sesuai manifest awal.

Batas A1 tetap: admin yang mengganti database tepat sebelum koneksi restore dapat membuat restore menulis ke pengganti, tetapi pengganti tidak dihapus dan malam tidak diverifikasi. D13-6/8b memilih restore di database sementara mesin GitHub. Paket offsite/Drive CP7C tetap ditahan.

Catatan implementasi yang tidak disembunyikan: `created_here` dapat membersihkan OID yang baru dibuat attempt sebelum penulisan mark berhasil. Kontrol Astra B10 membuktikan jalur itu hanya membersihkan objeknya sendiri; tanda polos tidak memberi kepemilikan atas database asing.

Laporan lengkap: `REPORT.md`. Original, log lengkap, screenshot, hash, dan per-case ledger tersedia dalam `ORIGINALS.tar.xz`, `evidence/screenshots/`, `EVIDENCE_MANIFEST.json`, `CASE_RESULTS.json`, dan `CI_RECEIPT.json`. Koreksi pembaca indeks bukti lama (AX2-T01, alat lokal auditor) dicatat dengan kegagalan pertama; tidak ada transaksi produk diulang.

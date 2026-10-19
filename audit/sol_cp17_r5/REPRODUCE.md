# Menelusuri bukti Sol r5

Kandidat `17fa25075ba77f0853c3c16f504288ace03eec35`, tree `65f778479093d869a3354c0b9f19b4d9a541d98a`. Ini petunjuk baca ulang; tidak ada uji baru saat penyegelan.

1. Cocokkan SHA256 arsip dengan `ARCHIVE_RECEIPT.json`; ekstrak ke direktori salinan sekali pakai. `RAW_EVIDENCE_WHITELIST.json` memuat path relatif repo, byte, serta SHA256 setiap file.
2. `RUN_REGISTER.json` mencatat 12 run beserta SHA workflow. `COMMAND_LEDGER.json` memuat teks langkah tepat pada SHA itu; `JOB_LOG_INDEX.json` menunjuk log decoded asli serta status langkah.
3. `OWN_CI_RECEIPT_FINAL.json` mencocokkan 31 job/43 artifact provider. `ci_receipts/sol_artifacts/<id>/DOWNLOAD_RECEIPT.json` merekam hash ZIP provider dan member terpilih.
4. `CASE_LEDGER.json` memakai path dokumen, group_pointer, serta case ID. Salinan complete-json tidak dihitung sebagai uji baru.
5. Baca review reader/detektor, performance, dan regression/restore untuk kualifikasi semantik. PASS mentah tidak menjadi persetujuan tiga detik, restore postuse, atau hosted.
6. Bukti r4 dipertahankan melalui segel `ecb44425710a0a29203835076f32ef83f7d436d2`. Path bukti r4 di matriks merujuk arsip r4, bukan eksekusi r5.

Log adalah teks UTF-8 exact dari konektor, bukan ZIP log GitHub asli. Arsip memuat 695 member teks asli artifact beserta metadata/log; tidak memilih gambar biner. Seluruh 12 run sudah terminal: 9 success/3 failure, attempt1. Kualifikasi pure capture tidak menjalankan SQL.

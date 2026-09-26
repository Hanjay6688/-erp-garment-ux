# GPT — pemeriksaan status D11, LAU-T36, D12 (26 September 2026)

Label: SOURCE_REVIEW + WRITER_ACTIONS_LOG_READ. Diminta owner saat mengirim status 13 pengaturan dan run 36218288935. Bukan run auditor mandiri; tidak ada penerimaan independen baru. CP6 HOLD, audit_complete=false, production_go=false. Writer masih Opus; GPT tidak mengubah produk.

## Identitas dan cakupan
- Repo: Hanjay6688/-erp-garment-ux. Catatan ini hanya di audit/cp6-final-20260924-gpt-a0bcadf.
- Head writer dibaca: 7d33d84d0f93c54c43e7acd9d2df4d89d6d6f2e2 (D12).
- Sumber keputusan: docs/cp6-d11-kebijakan-dan-gbd03.md, blob 3450aeccceb34d8c5a39614cfd82a7899d2ea48c.
- Sumber oracle kebutuhan D12: owner ingin invoice lebih tua daripada reject dapat dilunasi pada tanggal berjalan oleh kas + kredit klaim vendor yang sama, tanpa sisa semu, penggunaan kredit ganda, atau perubahan histori.
- Tidak ada skenario GPT baru/dispatched pada pemeriksaan ini. Status gate historis dan hasil beku tidak diubah.

## D11 — keputusan, konfigurasi, dan pengujian berbeda
Dokumen repo masih mencantumkan 4/11/13 perlu keputusan owner dan 12 tidak perlu diisi. Dalam chat GPT telah menyusun draf jawaban sesuai permintaan owner: CREDIT_THEN_CARRY untuk USABLE; ALLOW_PENDING dengan HPP belum final dan close ditahan; tarif khusus tidak diaktifkan; PRODUCT_COST + CORRECTION_DOCUMENT. Draf jawaban bukan bukti konfigurasi aplikasi sudah diisi, bukan alasan melabel ulang pengujian. Catat ratifikasi owner di jalur dokumen writer; jangan mengisi akun, ambang biaya, atau kategori gratis dari asumsi.
D10: ukuran bukan dasar tarif laundry owner. Pembagian per potong berada dalam sumber layanan/tagihan yang sama.

## LAU-T36 — layout diperbaiki, kasus belum PASS
1. Run 36218288935 / job 108338554401; tool 116834b13c6aa1fe71557be85a1d2f8aeb3feae5, product ea8f884833720d3566fa206154d77dde34b8417a:
   - LAU_T36_PHONE_MIXED_COVERAGE INCOMPLETE, timeout klik Isi harga T36 SPR.
   - Diagnostik viewport 390 px, halaman 407 px pada kebijakan dan 598 px pada harga unknown.
   - Empat kasus browser lain PASS. Ini hasil beku.
2. Perbaikan produk 3199c4f27b52ceb54dd3c2846687c1d5f2191278 memuat initial-import.css pada LaundryBdPanel. Writer menyebut sebelumnya layout bergantung halaman impor pernah dibuka.
3. Run 36218676593 / job 108339662157 pada 3199c4f:
   - Workflow success, tetapi per-kasus LAU-T36 **FAIL**. Empat kasus lain PASS.
   - no_sideways_scroll=true: semua lima tahap page=viewport=390. Tombol dapat diklik. filled_complete=true; accrual_matches=true (13000.00).
   - Satu check false: mixed_coverage. Aktual "T36 GAR:2:KNOWN,T36 SPR:1:UNKNOWN"; pembanding scripts/cp6_bd_browser.mjs mengharapkan "GAR:2:KNOWN,SPR:1:UNKNOWN".
   - Pembanding salah masih identik pada head 7d33d84 (baris sekitar 240), blob browser baru 963e6c104b2ad6f73eff42c0f45baa604efa8f65. Blob browser 3199c4f: 92b9823042b5b5e9c6ecac12b6dfb2f3c888821d.
   - Ini kesalahan alat/fixture-comparator, bukan bukti biaya produk salah. Tidak melabel ulang FAIL menjadi PASS.
   - Scenario .py SHA256 yang dicetak kedua run: 296f6d6d66cb2cb242bfb1c78b95dfedcefed645b6011e020fd237fdca5a9355. Ini hash skenario Python, bukan hash modul browser.
   - RUN_COMPLETE menunjukkan seluruh kasus dilaporkan; tidak berarti semua PASS. independent_acceptance=false; primary_unchanged=true.

Temuan alat baru GPT-BD-T36-COMP (P3 tooling): perbaiki pembanding agar identitas fixture konsisten, tetap cek qty 2/1 dan KNOWN/UNKNOWN. Rerun pada head terpin; pertahankan log lama.

## D12 — celah dokumen diakui writer, perbaikan masuk dev dan UI
Commit 7d33d84 mengakui kompensasi lama hanya mengurangi AP_VENDOR agregat; sisa invoice/saldo awal tidak mendapat alokasi kredit. Writer menambahkan tabel aplikasi kredit, penerapan ke invoice/payable saldo awal, pembayaran vendor nyata, pembalikan, dan panel Pembayaran vendor.
Ini menegaskan batas pemeriksaan sumber GPT sebelumnya: jurnal agregat tidak cukup membuktikan pelunasan invoice.
- Kode baru: scripts/cp6_bd_objects_claimcredit.sql (blob 6ff3c9e36143cd8f56b046ee519c5f2c4f2cddfc), facade APPLY_CLAIM_CREDIT / PAY_VENDOR_DOCUMENT / REVERSE_VENDOR_SETTLEMENT. Belum direview penuh secara adversarial oleh GPT.
- Run writer T1 36219651334, after job 108342359124: **33/33 PASS** dari JSON BD_CASES_AFTER yang dibaca.
  - D12:CLAIM_CREDIT_DAILY_OLDER_INVOICE PASS. Invoice 15 Juni, reject 15 Juli, approval/payment 25 September. Total 10000000.00, cash 8000000.00, claim_credit 2000000.00, remaining 0, PAID; AP 0; kredit tersedia 0. Replay, double-use, overpay, reversal-in-use refusal, inverse/reapply, dan histori Juni dicek.
  - D12:CLAIM_CREDIT_OPENING_OLDER_PAYABLE PASS. Dokumen 16 Agustus, pembayaran 25 September; total/cash/credit sama, remaining 0, SETTLED; AP 0, histori cutover tetap.
  - Before job 108342359324 success menurut metadata; log before belum dibaca GPT, jangan mengklaim hasil per-kasus.
- Run 36219651374 / job 108342359330 success: sample runtime, SAMPLE_HTTP:PREFLIGHT_OWNER_ALLOWED_GUDANG_AND_ANON_REFUSED PASS. Ini **bukan** bukti browser/race D12.
- Run 36219655269 / job 108342372279 masih berjalan ketika checkpoint disusun; hasil per-kasus belum dibaca. Jangan asumsikan PASS dari metadata workflow.

## T3 pada D12 belum lulus
Run 36219651391 head 7d33d84: ketiga job failure.
- Install job 108342359350: BD_T1_FUNCTION_NOT_CURRENT pada erp.bb_opening_credit_lines_v1(uuid); primary_unchanged=true, restore drill dan security advisors true, installed=false.
- Capture/compare job 108342359474: capture ALL_STAGES_INSTALLED, tetapi T3_PINS_REPRODUCED equal=false, differ=["BD"]; assert T3_COMMITTED_PACKAGE_STALE.
- Browser package job 108342359457 failure menurut metadata; log belum ditinjau.
Sesuai commit writer, sumber BD sudah diperbarui tetapi paket committed masih versi lama sampai capture/rebuild. Gate paket tetap HOLD. Bukti T3/rollback sebelum D12 tidak otomatis berlaku untuk D12.

## LANGKAH BERIKUTNYA
1. Writer membetulkan comparator LAU-T36 dan rerun browser dengan input/head terpin; jangan menyamakan workflow success dengan semua kasus PASS.
2. Ambil hasil 36219655269 / 108342372279. Cek khusus dua kasus browser D12, T36, dan efek samping/cleanup. Jika input berbeda, catat cakupan sebenarnya.
3. Writer membangun ulang paket BD dari capture D12 lalu menjalankan T3, rollback yang sesuai, serta gate regresi terdampak pada final head. Tidak ada perubahan produk oleh GPT dalam checkpoint ini.
4. Auditor penerus memeriksa penerapan kredit parsial/lintas beberapa invoice, vendor salah, dua sesi berebut kredit, tanggal aplikasi vs approval/period close, pembayaran dan inverse; oracle diturunkan dari kontrak dan keputusan owner. Hasil writer dibaca sebagai bukti writer.
5. Sinkronkan keputusan 4/11/13 dengan ratifikasi owner; aplikasi konfigurasi masih tindakan terpisah. Jangan membuat nilai akun/ambang/kategori.

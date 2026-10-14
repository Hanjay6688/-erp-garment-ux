# ASTRA-CP17-HPP-01 — Kebijakan baru meninggalkan pool HPP aktif dengan basis kedaluwarsa

**TERBUKTI, S1.** Kandidat `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, FULL composition. Petunjuk Fable R1-02; fixture, oracle dan eksekusi Astra sendiri sesudah exposure yang diizinkan owner. Perubahan kebijakan yang diterima membuat validasi native menyatakan `STALE_POOL_INPUT`, tetapi pool dan alokasinya tetap ACTIVE tanpa alarm pada 135 detector yang diperiksa. Dampak nominal laporan hilir belum diukur; ini bukan klaim kerugian HPP seluruh pabrik.

Run `38572768164`, job `115881983672`, control commit `0d7f3dcc72e1fbee19883c1056361c54527f6885`. Artifact `11899491205`, SHA256 `38b288036169c8c0e9a679cb0f2734484a4c66a4d2f4a486de327c474d62a928`. Manifest `FINAL_GAPS_MANIFEST.json` dan `cases_pool_closure.py` dikunci sebelum eksekusi.

## Reproduksi dan hasil

1. Mandor A mempunyai kebijakan absensi, payroll sah 1000, dan fakta selesai jahit 10 PCS. Mandor C mempunyai fakta selesai jahit 10 PCS pada periode yang sama tetapi belum mempunyai kebijakan, sehingga tidak masuk manifest pool.
2. Preview pool tanggal 13 Oktober memberi READY, numerator 1000, denominator 10, biaya per PCS 100. Buat lalu aktifkan: validasi PASS dan status ACTIVE.
3. Melalui `public.erp_set_contractor_hpp_policy_v1`, tambahkan kebijakan C dengan effective_from 12 Oktober, Mandor biasa dan attendance_required=true. Writer **menerima** perubahan ini.
4. Validasi native pool yang sama kini menolak `P0001: STALE_POOL_INPUT: payroll, policy, journal debit, or SELESAI_DIJAHIT facts changed after preview`.
5. Pool tetap ACTIVE, row_version 2, numerator 1000, denominator 10, unit cost 100; seluruh source dan allocation sebelum/sesudah identik. Seluruh 135 baris detector juga identik, issues=0.

`CP17-ASTRA-POOL-03-POLICY-AFTER-ACTIVE`: COUNTEREXAMPLE. Batas database dan public dipulihkan, session_leaks kosong dan lock nol. Outer restoration/advisor true. `POOL_CLOSURE_OBSERVATION.json` mengikat hash Original dan menyimpan nilai sebelum/sesudah; byte Original penuh tetap ada dalam arsip.

## Kontrol yang membatasi tuduhan

`CP17-ASTRA-POOL-02-DISTINCT-PERIOD-CONSERVATION` PASS. Dua payroll masing-masing 1000 untuk Mandor/periode berbeda dialokasikan melalui dua pool yang mempunyai tujuan jahit beririsan: masing-masing pool membagi 500+500; total 2000 dan setiap sumber payroll dipakai sekali. Tujuan yang menerima dua alokasi **tidak otomatis berarti biaya digandakan**. Hasil ini membantah klaim tersebut untuk fixture yang diuji, tanpa membuat larangan umum periode overlap atau mengklaim semua kebijakan penyelarasan periode selesai.

## Penyebab dan batas

`erp._cp3_r4_active_pool_affects_contractor` pada migrasi `20260901023400_erp_v2_6_14d_cp3_r4_race_and_reversal_hardening.sql` menelusuri keanggotaan kontraktor pada child pool yang sudah ada. Kontraktor C belum menjadi anggota karena dahulu dikeluarkan oleh pemilih policy; penambahan policy yang mengubah himpunan eligible lolos. Patch `set_contractor_hpp_policy_v1` memakai predicate itu untuk menolak perubahan atas pool ACTIVE. Manifest builder/validator pada `20260901023200_erp_v2_6_14c_attendance_hpp_uat_alignment.sql` kemudian mengenali basis yang berubah, tetapi tidak membatalkan status aktifnya.

Belum diambil fresh preview sesudah perubahan, laporan keuangan lengkap, business cancellation atau browser untuk saksi ini. Jangan mengubah hitungan dugaan 20 PCS/50 per PCS menjadi hasil observasi. Preview awal memang menyertakan manifest A saja; ini belum membuktikan seluruh UI menyembunyikan exclusion R1-07. Tidak diklaim false READY pada laporan keuangan.

## Penerimaan perbaikan

Perbaiki native policy/active-pool dependency agar perubahan eligibility yang memengaruhi pool aktif ditolak atomik atau melalui alur pembatalan dan koreksi yang sah. Jangan hanya memeriksa kontraktor yang sudah tercatat pada child pool. Pertahankan lineage, jurnal dan conservation; gunakan forward fix tanpa mengedit migrasi historis.

Wajib: kasus asli dengan kontraktor yang sebelumnya excluded, kontrol policy tidak relevan, policy pada anggota lama, batas effective date/next version, cancellation→policy→pool pengganti, race aktivasi/policy, detector sebelum/saat/sesudah, serta hasil HPP WIP/FG/COGS hilir dan browser desktop/HP. Reproduksi 1000/10 tidak boleh tetap ACTIVE dengan basis yang validator sendiri nyatakan stale.

# ASTRA-CP17-RWK-01 — Upah rework hilang dari Nota setelah semua hasil di-scrap

**TERBUKTI, S1: jalur pelunasan upah yang sudah diakui macet.** Kandidat `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, FULL composition. Kredit petunjuk: Fable R3-01; oracle dan eksekusi baru Astra sesudah izin owner membaca Fable. Bukan penemuan buta.

Run `38567853922`, job `115865040095`, control commit `7912acb719e80365a40776f8df0e8a020377990d`, artifact Original `11895499774`, SHA256 `861863d06a71c20bf59d9ce3e5226f8bb003b4c09d09d4ab1b01708d816ab22e`. Source/manifes dikunci sebelum run. Hasil: kontrol GOOD PASS; ALL-BS/SCRAP COUNTEREXAMPLE. Semua kasus memulihkan batas database/public, tanpa lock/sesi bocor; outer restoration/advisor true. Warna job merah berasal dari oracle produk.

## Reproduksi dan angka yang diamati

1. Fixture memakai writer produksi, laundry dan QC yang berlaku. Dua PCS masuk BS; komponen diklasifikasi belum dikerjakan sebelum BS.
2. `public.erp_save_bs_resolution_action_v1` membuat rework CONTRACTOR: dua komponen dilakukan, tarif snapshot 30, `qty_newly_payable=2`, `amount_payable=60`.
3. COMPLETE_REWORK mengembalikan GOOD=0 / BS=2. Jurnal `REWORK_COMPLETION` POSTED mengkredit `CONTRACTOR_PAYABLE` sebesar **60** pada 14 Oktober.
4. DISPOSE_BS SCRAP 2 menutup kasus menjadi **SCRAPPED**. Jurnal utang dan baris hak upah 60 tetap ada.
5. `erp.v_payroll_eligible_work_lines` tidak mengembalikan baris rework tersebut. Reader publik Nota juga tidak mengembalikan kartunya: `eligible=[]`, `matching_cards=[]`. Respons workspace lengkap tidak terpotong (`next_offset=null`). Pengguna tidak dapat memilih upah itu untuk Nota.

Kontrol independen memakai alur dan tarif sama, tetapi GOOD=2 / BS=0: BS menjadi RESOLVED, kartu 60 muncul, SAVE/POST Nota berhasil dan `labor_total=60`. Ini membedakan cacat eligibility dari setup/izin yang gagal.

Original lengkap: `CP17_OWN_CASES_FABLE_SEAMS.json`, `ASTRA_CP17_R3_REWORK_True_FIRST.json`, serta kontrol False. Ringkasan terstruktur di `FABLE_SEAMS_OBSERVATION.json`. Tidak dibuat jurnal atau status POSTED dengan SQL auditor.

## Penyebab dan batas kesimpulan

REWORK branch pada `supabase/release/cp6-t3/20260924010100_erp_v2_6_20ax_cp6_fg_unsourced_receipts.sql` mensyaratkan `bc.status='RESOLVED'` pada view eligibility dan trigger `validate_payroll_work_item_source`. Reader `scripts/cp7-src/payroll/source.sql` memakai view itu. Sementara itu reducer BS memberi SCRAPPED pada penyelesaian yang seluruhnya SCRAP, dan native completion tetap mengakui kerja yang benar-benar dilakukan. Hak upah dikaitkan dengan label hasil barang, bukan hanya source kerja yang telah sah.

Yang dibuktikan adalah jalur Nota current tidak menawarkan sumber utang tersebut. Tidak diklaim semua rute pembayaran alternatif telah dicoba, semua status akhir/partial mempunyai hasil identik, seluruh detector diam, atau browser baru dijalankan untuk saksi ini. Full detector observation baru tidak termasuk kasus ini; beri label **TIDAK TERUJI untuk saksi ini**.

## Perbaikan dan penerimaan kandidat berikutnya

Selaraskan eligibility reader, validator dan native allocation dengan hak kerja yang benar-benar diakui. Pertahankan aturan komponen sudah dibayar/telah selesai, source identity, current authority, versi, lock dan UUID; jangan membuka semua status tanpa memeriksa kontrak.

Saksi ALL-BS/SCRAP asli harus dapat memasukkan tepat dua komponen/60 ke Nota dan melunasinya sekali melalui jalur sah. Buktikan kontrol GOOD tetap lulus; WRITE_OFF, mixed GOOD/BS, partial/HOLD sesuai keputusan owner; double allocation/replay/refusal atomik; pembalikan rework/payroll tidak meninggalkan utang atau pembayaran ganda. Tambahkan browser Nota desktop/HP, baca ulang server dan jurnal/detector sebelum-saat-sesudah. Gunakan perubahan maju; migrasi historis tetap utuh.

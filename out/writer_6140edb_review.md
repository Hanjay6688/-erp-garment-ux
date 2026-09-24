# Pembaruan handoff rollback 6140edb

Diperiksa: 2026-09-24T21:55:57.301Z.
Produk acuan: `9add57ea8c2b6b2dc37c0134717d4d39ba30b5dc`.
Commit alat dan rollback: `6140edb1acd182efc84a4c85879860785335e688`.
Provenance: **REUSED_WRITER_EVIDENCE**. Hasil berasal dari log Actions; tiga kontrak tetap menjadi oracle penerimaan.

## Catatan pembacaan dan verifikasi

1. Compare 9add57e..6140edb memuat 12 berkas: enam berkas tooling dari 81fef32, satu capture JSON, empat SQL rollback, dan ROLLBACKS.json. Tidak ada diff pada `supabase/migrations supabase/dev supabase/release/cp6-t3 src`. Sebanyak 24 berkas SQL forward dan MANIFEST tetap sama. Path capture terlihat di diff; isi berkas docs/evidence tidak dibaca.
2. ROLLBACKS.json menyatakan urutan AZ, AY, AX, AW. Rollback AC..AV yang dipin ulang untuk paket rilis masih **NOT_BUILT**. Berkas rollback dev AC..AV yang sudah ada tidak berubah. Label tetap T3_PREP, production_go=false.
3. Empat SQL rollback diambil pada commit6140edb untuk verifikasi byte/hash. Hash AW a31e6c1e…, AX 5a55c695…, AY 317180db…, AZ 4b043221… semuanya cocok manifest. Hash builder 3a425c35… juga cocok. Hash lengkap dan ukuran tersedia di ledger.
4. Empat chunk capture direkonstruksi dari log run36063106225/job107846479593: 18380 bytes, SHA256 `62bb0e2a9a0bb69106538d32569239bf67bb8c79e05325808f837ad6f8450cf6`. Nilainya cocok dengan manifest dan hash yang dicetak log. Tidak memakai docs/evidence sebagai hasil atau oracle.
5. Run36063754595/job107848561550, attempt1, head6140edb selesai dengan conclusion success. Baris1325–1346 memuat 22 check PASS; baris1347 memuat mode=cycle, status=PASS, primary_unchanged=true, error=null.
6. Runner dibaca terarah: generation guards137–199; comparator327–358; pemeriksaan361–434; cleanup438–462. Workflow memilih mode cycle ketika ROLLBACKS.json ada. Review adversarial lengkap atas generated SQL dan seluruh helper yang diimpor belum selesai.

## Hasil dan batas bukti

- Identical rebuild: 1 PASS; install24file: 1 PASS; rollback predecessor: 8 PASS; reinstall: 8 PASS; refusal: 4 PASS. Total **22 PASS**.
- Refusal yang teramati: AY dijalankan di luar urutan; admission terbuka; rollback AV dev dipakai pada rantai rilis; AZ setelah perubahan data ter-commit. Semuanya SQLSTATE P0001, dengan error yang tercatat dan `changed={}`.
- Siklus pertama membandingkan hash seluruh baris ERP secara penuh. Siklus kedua untuk AZ/AY/AX, serta seluruh reinstall, memakai hash capsule yang mengabaikan `captured_at` **dan** `boundary_snapshot`. Perbandingan AW→AV tetap strict. Jangan menyatakan semua capsule byte-identik pada kedua siklus.
- Fixture post-use berupa INSERT ter-commit ke `erp.audit_logs` (runner49–50,429). Ini membuktikan penolakan untuk perubahan tersebut; belum menjadi matrix berbagai transaksi bisnis.
- Perbandingan katalog memakai query guard AZ. Dua ledger migrasi dan hash baris ERP juga dibandingkan. Kecukupan cakupan comparator serta normalisasinya masih perlu dinilai dengan oracle kontrak.
- Primary_unchanged=true tercatat di log. Runner menjalankan dropclone dengan check=True sebelum summary. Summary tidak memuat clone_remaining, sehingga tidak dicatat sebagai count0.
- AW..AZ kini **tersedia dan telah diuji writer**. Jangan lagi menyebut file atau cycle belum ada pada6140edb. Keadaan commit9add tetap menjadi catatan historis.
- Gate rollback keseluruhan tetap **HOLD**: AZ→AW kembali ke AV; AC..AV versi paket rilis NOT_BUILT. Native AV mengonfirmasi refusal, bukan keberhasilan AC..AZ→AB. Gap digest AC tetap terbuka.
- Native15 tetap NOT_RUN; run baru GPT=0. Smoke81fef32 dan rollback6140edb tidak menggantikan15kasus auditor atau seluruh CP6.

## LANGKAH BERIKUTNYA

Baca AUDIT_HANDOFF_CP6.md terbaru. Fable me-review helper dan oracle yang tersisa, menjalankan native15 satu kali dengan phase=after, kemudian melanjutkan race/Auth/browser independen. Catat actual tool SHA terpisah dari produk9add.

Untuk rollback, review SQL, normalisasi capsule, serta gap AC..AV versi paket rilis. Tidak perlu mengulang capture, penyelidikan absennya file lama, atau cycle hanya untuk memperbaiki narasi. Simpan hash skenario, run/job/attempt/head, expected/actual, cleanup, dan lanjutkan gate CP6 yang terbuka.

Ledger: [writer_6140edb_run_ledger.json](writer_6140edb_run_ledger.json).

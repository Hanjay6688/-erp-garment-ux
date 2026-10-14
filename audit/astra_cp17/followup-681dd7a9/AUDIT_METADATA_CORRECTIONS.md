# Koreksi administrasi bukti Astra — addendum, bukan penimpaan

Dua koreksi ditemukan saat pemeriksaan silang lanjutan. Tidak ada Original JSON, ledger, laporan terkunci, produk atau oracle lama yang diubah.

## Q16 — nama manifest dalam dua artifact final-gaps salah

Workflow `.github/workflows/audit-astra-cp17-final-gaps.yml` pada control `0d7f3dcc` menyalin `CLAIM_DATE_MANIFEST.json` ke `ASTRA_CASE_MANIFEST.json`, padahal job menjalankan pool-closure dan program CP5-exact. Kedua artifact11899491205/11898319571 run38572768164 benar-benar memuat hash `5a99ee93f08357020c4bb37def4256979407d5007265041dea5b3ccaace3e6d8` milik manifest claim-date. Ini kesalahan auditor, bukan identitas kandidat berubah.

Manifest yang benar `FINAL_GAPS_MANIFEST.json` sudah dikomit **sebelum** run pada control yang sama; SHA256 `56bca7c11f8920802d008a24fa0c111adcd3ac962df836bef7f40963a619d0f1`. Ia mencatat dua case pool, empat program CP5 asli, hash sumber dan hash program. Runner juga menyimpan `CP17_OWN_CASES_POOL_CLOSURE_PREEXECUTION_PLAN.json` sebelum operasi pertama, dan program CP5 merekam hash file yang dieksekusi. Jadi pembaca harus memakai kedua bukti prapelaksanaan itu dengan controlSHA; berkas bernama `ASTRA_CASE_MANIFEST.json` di dua artifact tersebut **tidak sah sebagai daftar kasus run ini**. Status mentah/hasil/oracle tidak diubah. Koreksi workflow baru RBAC menunjuk manifest RBAC yang benar; artifact lama dibiarkan apa adanya.

## Q17 — kalimat handoff CP5 tertinggal

`HANDOFF_WRITER_CP17_CONTINUATION.md` masih menyatakan operand assertion cutting belum diketahui. Penjelasan final sebenarnya sudah ada di `CP5_EXACT_REVIEW.md`/`CP5_EXACT_OBSERVATION.json`: program CP5 mengharapkan MD5 `require_owner_admin()` lama `965de305e5a381cfdf5588f2b9d4babc`, sedangkan FULL memasang delta owner P12/P13 yang dideklarasikan, MD5 `ec31bbfd0fba3e18a66f7f3ea33473e8`, SHA256 `57efdfe8af1a3dddba35332e81f00a27c7e2fcf9c0708e31c53a3eb74766fcdf`.

Operand hash tersebut pasti berbeda; tidak berarti semua operand gabungan sudah diukur. Hasil program asli tetap INCOMPLETE/qualified, bukan PASS. Penulis tidak perlu mengembalikan guard lama untuk memuaskan pin CP5. Handoff baru menunjuk penjelasan final ini. Laporan/handoff lama tetap dipertahankan dengan hash kuncinya.

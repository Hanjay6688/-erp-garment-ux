# Bukti kegagalan pertama — kandidat uji ulang Fable (12–13 Okt 2026)

Log gagal pertama disimpan apa adanya (baris kasus dan penutup dari log job; URL database sudah disamarkan GitHub).

| Berkas | Commit | Run / job | Yang terjadi | Disposisi |
|---|---|---|---|---|
| (log tidak disalin; ringkasan di `../../audit-candidate/fable-retest-20261012/README.md`) | `ddedf06c` | `CP7 F03 Full Retained Components` run 38285236686, job 114931910017–114931910456 (kelompok p12: job 114931910284) | Semua kasus PASS; 91 kasus berjalan dari 90 yang dideklarasikan (kasus gaji baru belum dihitung) | Angka di `scripts/cp7_f03_full_manifest.json` dinaikkan di `7a0b4a90` |
| `01_supplier_payment_create_7a0b4a90_run38288829388_job114943655473_FIRST_FAILURE.log` | `7a0b4a90` | `CP7 Supplier Payment Create` run 38288829388, job 114943655473 | Keempat kasus native PASS dan setiap kasus memulihkan batasnya, tetapi pemeriksaan akhir kelompok (`complete_boundary_restored`, keadaan seluruh ERP + `auth.users` + skema sesudah rollback dibanding awal kelompok) tidak sama, sehingga kelompok INCOMPLETE. Kode produk identik dengan `ddedf06c`, tempat workflow yang sama lulus (run 38285188586). Laporan tidak menyimpan tabel mana yang berbeda. | Penyebab belum ditemukan. Dijalankan sekali lagi: dispatch jatuh pada `e0583314` (commit sesudahnya, hanya dokumen) dan lulus (run 38289562249). Kegagalan ini tetap tercatat; bukan PASS. |

# OW-07 — cek HPP tutup buku (penulis A, 23 Okt 2026)

Owner (OPEN_WORK OW-07, dari D17-13 kelompok 3 dan D17-14): pastikan tutup buku tertahan bila kain kantong atau pool absen
periode itu belum dibagi; pastikan sisa WIP PO yang sudah selesai ditutup saat pool absen diaktifkan sesudahnya. Betulkan
bila celah terbukti.

## Fakta dari kode (kepala `2d625616`; R = `supabase/release/cp6-t3/`)

| Pertanyaan | Hasil |
|---|---|
| Tutup buku ditolak bila kain kantong belum dibagi? | **Tidak.** Tutup buku (`erp.close_accounting_through`, 20ba:1002) hanya menolak bila `period_readiness_v1` belum READY; `erp.period_blockers_v1` (20bf:2102) tidak punya keluarga kain kantong. `pocket_period_checks_v1` (20be:7032) hanya memeriksa periode kantong yang sudah ada. Pemakaian kain kantong yang tidak dicakup periode aktif tetap di OTHER_EXPENSE dan tidak pernah masuk HPP PO, tanpa pemeriksa |
| Tutup buku ditolak bila pool absen belum diaktifkan? | **Tidak.** Tidak ada pemeriksa periode yang membaca `attendance_hpp_pools`. Biaya absen yang sudah disetujui di payroll tetap di WIP tanpa PO; sesudah tutup buku, pool periode itu malah tidak bisa dibuat/diaktifkan (CP7 `pool.sql:261-265`) |
| Sisa WIP PO selesai ditutup saat pool absen aktif/batal belakangan? | **Tidak.** Jalur kain kantong memanggil `sync_finished_po_wip_residual` (20be:6978); aktivasi dan pembatalan pool absen (migrasi 16, baris 364-374 dan 408-418) tidak. Pemeriksa sisa WIP PO selesai hanya ada di `run_v257_integrity_checks` yang tidak dipanggil tutup buku |
| Uji yang ada | Tidak ada untuk ketiganya. Uji lama `scripts/cp6_pocket_period_trial.py:89-127` mengharapkan tutup buku berhasil saat pemakaian kain kantong belum dibagi (perilaku lama yang akan berubah) |

Ketiga celah terbukti; perbaikan dikerjakan penulis A sebagai tahap terpisah dan dicatat di sini.

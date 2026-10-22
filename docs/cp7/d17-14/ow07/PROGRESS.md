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

## Perbaikan (tahap `scripts/cp7_hpp_close/`, 23 Okt 2026)

Dipasang di atas produk OW-05 yang sudah lulus, terpisah dari pemasang bawaan sampai penggabungan.

| Bagian | Isi |
|---|---|
| Penghalang tutup buku | `erp.period_blockers_v1` (dipakai tutup buku, pratinjau tutup, dan keyakinan laporan) mendapat keluarga `HPP_POOL` dari `cp7_hpp_close.blockers_v1`; baris lama tidak berubah |
| Kain kantong | `POCKET_USAGE_UNALLOCATED` (menahan): pemakaian kain kantong yang disahkan dan bernilai, tanggalnya sampai tanggal tutup, belum menjadi sumber periode "Bagi ke HPP per periode" yang aktif; termasuk pemakaian saldo awal yang diimpor "belum dibagi". Satu baris berisi jumlah, nilai, tanggal awal-akhir dan sampai 50 rincian |
| Absen | `ATTENDANCE_POOL_NOT_ACTIVE` (menahan): payroll absen mandor biasa (persis sumber pool Native) pada periode yang selesai sampai tanggal tutup dan belum diambil pool AKTIF. `ATTENDANCE_POOL_POLICY_MISSING` dan `ATTENDANCE_POOL_SOURCE_UNCLEAR` (menahan): kondisi yang membuat pratinjau pool Native menolak. `ATTENDANCE_POOL_ZERO_OUTPUT` (hanya info): periode tanpa jahitan mandor biasa; aturan Native menyimpan biaya itu di WIP tanpa PO dan tidak ada pool yang bisa membaginya |
| Sisa WIP PO selesai | Aktivasi dan pembatalan pool absen memanggil `erp.sync_finished_po_wip_residual` untuk PO berstatus FINISHED sesudah HPP disinkronkan ke buku besar, sama dengan jalur kain kantong, memakai tanggal pembukuan jurnal pool |
| Mandor khusus | Payroll mandor khusus (mis. Afui) dan mandor tanpa wajib absen tidak memicu pemeriksaan pool (tidak ikut pool menurut aturan owner) |

Uji Native7 (`cp7-ow07-native.yml`) membandingkan mesin lama dan baru pada keadaan yang sama: baris yang ditambah OW-07
harus persis yang diharapkan dan tidak ada baris lama yang hilang. Hasil CI dicatat di bawah setelah selesai.

Dampak saat digabung ke pemasang bawaan: uji CP7 lain yang menutup buku dengan kain kantong atau payroll absen yang belum
dibagi akan tertahan; datanya harus dibagi dulu (bukan pemeriksa dilonggarkan). Uji CP6 lama tidak memakai tahap ini.

## Hasil CI

| Percobaan | Kepala | Run/job | Hasil |
|---|---|---|---|
| 1–2 | `70c8e91d` | 39822642176 | 6/7. Uji mengira hanya ada satu periode absen; data awal punya 5 periode lain yang juga belum dibagi, jadi baris penghalang tidak tunggal. Bukti: `native7-70c8e91d-first-case-failure.json`. Uji dibetulkan dengan mencocokkan baris milik payroll uji itu (pemeriksa tidak diubah) |
| 3 | `3a044782` (tahap sama, hanya uji) | 39828046424 / 119996487794 | **7/7 PASS**. Artefak `cp7-ow07-hpp-close-native7`, 1.818.707 byte, sha256 `65a67db78a76802acc2c22840c7441e64bcb74bd5008b076b3ed33d241d1f82f` |

Masih terbuka:
- Tahap ini belum masuk pemasang bawaan; disambung berantai saat penggabungan (OW-15).
- Biaya absen periode tanpa jahitan (`ATTENDANCE_POOL_ZERO_OUTPUT`) hanya dilaporkan, tidak menahan. Aturan lama menyimpan
  biaya itu di WIP tanpa PO dan tidak ada pool yang bisa membaginya. Perlu keputusan owner ke mana biaya itu dibebankan.

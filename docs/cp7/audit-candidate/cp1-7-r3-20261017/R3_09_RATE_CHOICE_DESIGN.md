# R3-09 — pilihan tarif lama atau baru saat jahit selesai (owner D16-2, D16-3, D16-4)

Rancangan penulis sebelum kode dibuat. Keputusan owner persis ada di `docs/cp7/OWNER_DECISIONS_20261008.md` (D16-2,
D16-3, D16-4).

## 1. Aturan Native sekarang

- Upah pertama sebuah PO mengunci tarif per komponen (`erp.ensure_po_work_component_snapshots`): satu baris
  `erp.po_work_component_snapshots` per PO × komponen (× versi SKU untuk potongan wave, `erp.bf_ensure_work_v1`), unik lewat
  indeks `bf_work_snapshot_scope (po_id, work_component_id, bf_sku_version_id) nulls not distinct`.
- Trigger `erp.validate_work_completion` menyalin tarif snapshot ke baris upah (`work_completion_lines.rate_snapshot`).
- Penjaga Native menolak baris upah yang tarifnya berbeda dari snapshot yang dirujuknya
  (`erp.guard_work_completion_posting_consistency`: `AI_WORK_SOURCE_SNAPSHOT_MISMATCH`), dan pemeriksaan pemasang paket CP6
  (`AI_PREEXISTING_WORK_SOURCE_REVIEW_REQUIRED`) serta laporan `erp.run_v268_financial_report_checks` menghitung baris seperti
  itu sebagai rusak.

Akibatnya tarif baru tidak boleh ditulis langsung ke baris upah. Tarif baru harus datang dari **baris snapshot baru (revisi)
PO itu** yang dirujuk baris upah, supaya semua penjaga di atas tetap berlaku tanpa diubah.

## 2. Rancangan

### 2.1 Revisi snapshot tarif (perubahan Native yang dideklarasikan)

- Indeks `bf_work_snapshot_scope` diganti dengan unik `(po_id, work_component_id, bf_sku_version_id, committed_at) nulls not
  distinct`. Revisi baru selalu `committed_at` = saat dibuat, di bawah kunci PO, jadi tidak bisa kembar.
- Revisi hanya dibuat oleh perintah CP7 jahit selesai di transaksinya sendiri (pola `pickup_context` SG-01: tabel konteks per
  `backend_pid` + `txid_current()`), dengan tarif yang sama persis dengan aturan Native pada tanggal jahit: tarif mandor
  (`erp.contractor_work_rates`) yang berlaku, atau tarif standar Work BOM; untuk SKU wave `erp.bf_work_rate_v1`. Satu revisi
  per perubahan tarif; bila tarif pada tanggal jahit sama dengan revisi yang sudah ada, revisi itu dipakai lagi.
- Baris snapshot tidak pernah diubah atau dihapus; revisi lama tetap dirujuk upah lama.
- Uninstall: indeks lama dikembalikan hanya bila belum ada revisi; bila sudah ada, uninstall menolak dengan pesan jelas
  (data upah yang sudah memakai tarif baru tidak boleh dibuang diam-diam).

### 2.2 Fungsi Native yang harus tahu ada revisi (patch berjangkar, dipulihkan persis saat uninstall)

Inventaris 19 fungsi Native terbaru yang membaca `po_work_component_snapshots` (lihat daftar di bawah). Yang membaca lewat
`id` snapshot atau hanya `exists(...)` tidak berubah perilakunya. Yang perlu patch:

| Fungsi | Masalah bila ada revisi | Patch |
|---|---|---|
| `erp.bf_ensure_work_v1` | Mengulang semua baris dasar PO; dengan revisi dasar, SKU baru mendapat snapshot ganda | Hanya baris dasar asli (revisi pertama per komponen) |
| `erp.prepare_rework_component_line` (cabang SKU wave) | `select ... into` tanpa urutan; dengan dua revisi hasilnya acak | Urut `committed_at desc, id desc limit 1`, sama dengan cabang non-wave |

Tidak perlu patch (dibaca per `id`, `exists`, atau sudah memilih yang terbaru): `bb_po_contractor_used_v1`,
`bf_assert_work_scope_v1`, `bf_save_groups_v1`, `bf_snapshot_matches_v1`, `bf_snapshot_sku_v1`, `bf_work_capacity_v1`,
`classify_bs_case_v2` (terbaru), `ensure_po_work_component_snapshots` (hanya bila belum ada), `get_hpp_completeness`,
`get_product_conversion_workspace_v1` (hanya daftar fungsi), `guard_work_completion_posting_consistency`,
`post_work_completion`, `run_v263c_bs_rework_integrity_checks`, `run_v268_financial_report_checks`,
`seed_bs_case_component_baseline` (jumlah per komponen dan SKU, bukan per revisi), `validate_work_completion`.

### 2.3 Perintah dan layar (CP7, `scripts/cp7-src/cutting-correction/sewing.sql`, `src/SewingCompletionPanel.tsx`)

- Ruang kerja menampilkan per komponen (dan per SKU wave): tarif terkunci PO, tarif yang berlaku pada tanggal jahit, dan
  nilai upah keduanya untuk jumlah yang diisi. Bila sama, tidak ada pilihan.
- Bila berbeda dan PO belum "pakai tarif baru seterusnya": pengguna wajib memilih "Tarif lama PO" atau "Tarif baru" dan
  mengisi alasan (yang sudah wajib). Tidak ada pilihan bawaan.
- Tombol per PO "Pakai tarif baru seterusnya": sekali tekan, dengan alasan dan tinjauan; riwayat tidak bisa diubah. Sesudahnya
  setiap pencatatan untuk PO itu memakai tarif yang berlaku pada tanggal jahit tanpa ditanya.
- Hak: perintah jahit selesai sudah hanya untuk OWNER/ADMIN (`sewing_access_now`), jadi D16-4 terpenuhi; tombol juga
  OWNER/ADMIN.
- Batal (REVERSE) tetap lewat pembalik Native; revisi yang sudah dibuat tetap ada.
- Nota, payroll dan HPP membaca baris upah, jadi mengikuti tarif yang dipilih tanpa perubahan.

## 3. Uji (ditetapkan sebelum kode)

Native: tarif sama tanpa pilihan; tarif berubah → pilih lama (upah = tarif lama, tanpa revisi); pilih baru (revisi dibuat,
upah = tarif baru, baris upah merujuk revisi, penjaga AI tetap lulus); pencatatan kedua dengan tarif baru memakai revisi yang
sama; tombol seterusnya → pencatatan berikutnya tanpa pilihan dan memakai tarif baru; upah lama tidak berubah; wave per SKU;
batal pencatatan bertarif baru; BS sesudah upah bertarif baru (baseline dan tarif rework); Nota → payroll → bayar dengan
jumlah tarif baru; HPP akhir PO = jumlah upah tercatat; detektor dan `run_v268_financial_report_checks` nol; pilihan wajib bila
berbeda (tanpa pilihan ditolak); bukan OWNER/ADMIN ditolak. Race: dua tab memilih baru pada saat yang sama (satu revisi);
tombol dan pencatatan bersamaan. HTTP: Auth nyata pilih baru dan tombol. Browser: desktop dan HP, dua tarif tampil, pilih,
simpan, tombol, pencatatan berikutnya tanpa pilihan. Instal/uninstall: patch berjangkar dipulihkan persis; uninstall
menolak bila revisi sudah ada.

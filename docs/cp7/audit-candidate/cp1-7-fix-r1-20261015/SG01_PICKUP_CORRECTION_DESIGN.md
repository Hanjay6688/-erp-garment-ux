# SG-01 — koreksi Bagi Potongan (pickup) yang sudah POSTED: rancangan (belum dibangun)

Temuan Fable FABLE-009 / Astra SG-01. Rancangan penulis dari penelusuran kode Native; belum ada kode produk.

## Fakta Native

- POST pickup (`erp.save_cutting_pickup_v1`, M18:997-1233) menulis: pickup POSTED, batch/alokasi, `cutting_groups`
  (`picked_up_at`, status PICKED_UP, `executor_name`), `production_orders` (mandor, status/stage SEWING), audit.
  Tidak ada stok, jurnal, event WIP, atau fakta payroll.
- Status `REVERSED` sudah ada di skema `cutting_pickups` (kolom reversed_by/at/reason, CHECK bentuk, indeks pickup aktif
  hanya DRAFT/POSTED), **tetapi tidak ada penulisnya** dan dua pengaman menolak semua jalan ke sana:
  `guard_cutting_pickup_lifecycle` (M18:253-276: UPDATE/DELETE dari non-DRAFT ditolak) dan baseline
  `normalize_cutting_group_pickup` (mengosongkan `picked_up_at` ditolak bila bahan sudah keluar — selalu benar sesudah pickup).
- `erp.cutting_group_has_downstream_after_pickup` = ada event WIP (termasuk yang dibalik), work completion non-DRAFT,
  laundry non-DRAFT/REVERSED, QC non-DRAFT, lot FG, kasus BS, scrap, koreksi qty. Sekali ada event WIP, selamanya true.
- Tidak ada penulis "ganti mandor" atau "pecah ulang batch" yang diterima.

## Rancangan

**Tingkat (a), sebelum ada proses lanjutan** — perlu delta Native yang dideklarasikan:
fungsi Native baru `erp.reverse_cutting_pickup_before_sewing_v1(pickup, alasan, request, versi pickup, versi grup)`
(SECURITY DEFINER milik postgres, idempoten, OWNER/ADMIN + `production.distribution.post`, kapabilitas transaksi seperti
`cutting_bridge_execution_context`) dan dua admission sempit pada kapabilitas itu:
- D1a `guard_cutting_pickup_lifecycle`: hanya POSTED→REVERSED, kolom lain tetap, tanpa downstream dan tanpa baris
  laundry yang menunjuk batchnya. REVERSED final; DELETE tetap dilarang.
- D1b `normalize_cutting_group_pickup`: boleh mengosongkan `picked_up_at` walau bahan sudah keluar, hanya di bawah
  kapabilitas dan bila grup tidak punya pickup aktif.
Tulisan bisnis: pickup REVERSED (+ siapa/kapan/alasan), grup kembali CUT tanpa `picked_up_at`, `executor_name` kembali
ke nilai sebelum POST (dari audit), status/stage PO dihitung ulang dengan urutan bukti Native, `contractor_id` PO
dikosongkan hanya untuk kasus salah mandor dan hanya bila tidak ada fakta lain yang mengikat mandor itu. Tanpa stok/jurnal.
Bahan tetap terposting; grup kembali ke antrean "siap dibagi". POST ulang memakai penulis biasa.
Fasad CP7 mengikuti `cutting-correction/reopen.sql` (akses, snapshot termasuk batch/alokasi, token, kunci `CP6FLOW`,
panggilan Native, cek pasca, riwayat immutable). Penghalang tambahan di luar helper downstream: work completion/QC/laundry
DRAFT, terminal jahit, alokasi pool absensi, flag WIP terbuka.

**Tingkat (b), sesudah ada proses lanjutan**: ditolak, menyebut tiap dokumen penghalang (id, nomor, status). Ganti mandor
sesudah jahit butuh rancangan Native baru (mandor tercap di work completion, terminal, WIP, payroll, snapshot tarif).
Kemungkinan tingkat berikut (masing-masing delta baru): koreksi jam saja (dibatasi waktu downstream paling awal) dan
pecah ulang batch bila belum ada baris laundry yang menunjuk batch lama.

## Sumber
M18 = `supabase/migrations/20260903022604_erp_v2_6_18_cutting_persistence_pickup_wip.sql`; baseline FX =
`supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz`; downstream laundry 20ac:8894-8968; work source 20ai:154-243.

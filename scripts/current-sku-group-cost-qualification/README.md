# SKU group cost Native3 — prepared, not executed

Namespace ini tidak mengubah produk, engine biaya, frozen Native7, installer,
callback lain, package, workflow atau default. Backend pin:
`21c69cf25defcee854beb08e998062d7e883d968`, tree
`a0d2c0da83bf5dc29f2c6b2e02abe6d7ed68f89e`. Tiga callback actual Native telah
disiapkan; belum ada runtime PASS, Auth, browser atau full restore dari berkas
ini. Source/oracle controls lokal tidak menjadi bukti transaksi Native.

Integrator memverifikasi Original Native7, raw bytes/source/package/restoration
dan semua gate sebelum memberikan objek inner `strict_group` tujuh kasus:

```python
cost = load('sku_actual_group_cost', ROOT / 'scripts/current-sku-group-cost-qualification/cases.py')
cost.admit_native7(
    native_group,  # actual original counts PASS7, all seven full boundaries restored
    original_report_sha256=verified_original_sha256,
    backend_commit='21c69cf25defcee854beb08e998062d7e883d968',
)
report = native.strict_group('CP7_SKU_GROUP_COST_NATIVE3', cost.cases, verify)
```

`cases(cur,today)` menolak sebelum menyentuh cursor bila Original Native7 belum
diadmit. Source guard kemudian membaca seluruh pin dan koneksi wajib loopback
54322/database `cp6_rollback`. Modul tidak membuat koneksi, commit, instalasi,
trigger CI atau pengiriman eksternal. Callback tetap di bawah savepoint runner
Native yang sudah ada. Verifier lengkap, copy authority, parent bindings,
backup/restore all22/data/sequences/roles/advisors dan lima package gates
merupakan kewajiban outer adapter; Native3 PASS sendiri belum cukup.

| Kasus | Expected independen | Batas klaim |
| --- | --- | --- |
| `SKU29_COST_GROUP_RETURN_OVER_FIRST_PART_SAFETY_REFUSAL_ONLY` | Child20,02+40,04, recovery30,03 ke child pertama akan meminta HPP−5,005; Native menolak dan seluruh census sesudah receipt/inspect tetap persis | **Safety refusal saja**, `group_recovery_supported=false`; kemampuan recovery seluruh grup belum ada |
| `SKU29_COST_BOTH_PARTS_USAGE_LATE_INVOICE_SOLD_AND_DESCENDANT` | Usage1+2PCS@2 memberi22,02/44,04; invoice3 memberi23,02/46,04 (total69,06); descendant dari child2 naik22,02→23,02; material97 | Dua dokumen usage Native per child, bukan satu recovery induk yang dibagi otomatis |
| `SKU29_COST_FIRST_PART_ACTIVE_USAGE_ATOMIC_GROUP_INVERSE` | Child2 tanpa biaya dibalik dahulu, lalu child1 menolak karena usage aktif; seluruh statement kembali persis. Sesudah inverse usage sah, kedua child bisa dibalik | Actual Native atomic inverse dengan cost dependant; tidak mengklaim recovery seluruh grup |

Kasus2 memprediksi FIFO dari fakta lot yang diketahui **sebelum** sale:
4PCS target lama lalu1PCS dari lot grup lebih dahulu menurut produced_at/ID.
Satu konversi Native terpilih dari child2 ke master baru dengan model/ukuran
yang sama sudah dibuat sebelumnya. Sesudah late invoice, koreksi COGS adalah
0,50 jika sale mengambil child1 atau1,00 jika child2; koreksi FG seluruh stok
yang tersisa, termasuk descendant, adalah2,50 atau2,00. Jumlah koreksi garment
tetap3,00. Material yang masih ada97PCS naik nilainya97,00; jumlah fisik tetap.
Jurnal Native, account targets/books, detector lama, dan HPP source10,01/20,02
harus tetap konsisten. Tidak ada oracle yang dihitung dari hasil sale/recost.

Snapshot penuh `product_conversions`, `product_conversion_allocations`,
`be_conversion_sources_v1` dan `sale_stock_allocations` yang sudah posted harus
tetap persis pada recost dan invoice inverse. Source HPP rows juga dibandingkan
penuh. Dest HPP boleh membuat versi Native baru; current values harus sama
dengan gold. Replay masing-masing usage dan posting invoice memakai UUID serta
payload/revisi lama yang sama dan harus mempertahankan seluruh current census.
Inverse invoice sah harus memulihkan nilai22,02/44,04, descendant22,02 dan semua
account balances sebelum invoice; riwayat baru tetap disimpan.

`native_fixture.py` memakai helper Native yang sudah ada: opening, material
purchase, accessory service, selected-lot conversion, sales dan supplier invoice
v2. Insert langsung hanya untuk master sintetis baru, dengan model/size dipilih
saat insert dan BOM kosong eksplisit. Tidak ada posted stock/HPP/journal/cost
source yang disisipkan dari SQL fixture. Tidak ada GUC bypass atau perubahan
cap. Temporary Native-schema usage yang diperlukan dipelihara oleh helper
existing `b.internal`; hak produk tidak diproyeksikan atau dihapus dari census.

Semua waktu lanjutan memakai offset dari timestamp parent fixture yang sudah
di masa lalu: usage+1detik, descendant+15, sale+30, receipt+20, inspection+30,
valuation+40. Purchase material enam hari sebelumnya; invoice memakai tanggal
WIB `today` dari runner. Business-day control runner tetap berlaku. Tidak ada
jam masa depan yang dipaksa demi fixture.

Penolakan dan replay menyimpan before/after raw seluruh22 grup katalog dan
`catalog._data` semua row/sequence ke `cp6-proof/t3/SKU_COST_*` dengan token unik.
Perubahan sekecil apa pun membuat kasus gagal; tidak ada dropped field atau
sequence yang diabaikan. First failure harus dipertahankan oleh outer package.
Laporan menghindari key `group` yang bertabrakan dengan logger Native frozen.
Pada kasus3, lintasan DML child2 sebelum error child1 merupakan inferensi dari
source Native yang dipin, kedua status awal POSTED, urutan member tersimpan dan
error sumber biaya child1. Tidak diklaim ada audit eksternal per-child yang
bertahan di luar rollback; bukti runtime yang langsung diamati adalah exact
zero-effect census dan inverse sah berikutnya.

Pemeriksaan lokal: `python3 .../test_oracle.py`, `python3 .../check_import.py`
dan Python compile. Import check menjaga CLI kosong dependency asli dan
membuktikan callback menolak sebelum Native7 admission tanpa membuka DB.
`production_go=false`, `independent_acceptance=false`.

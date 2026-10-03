# Batas pembaca potongan dari transaksi asal

Inspection read-only pada source088f446c. Native runtime atau sambungan baru belum dijalankan. Exact frozen/UI file hashes: `evidence/cutting-source-contract/READ_ONLY_INSPECTION.json`.

Pembaca `erp_get_cutting_workspace_v2` milik CP6 mengembalikan `selected_order` dan `selected_draft` terpisah dari halaman hasil pencarian. Identitas PO dan kelompok potongan harus diperiksa bersamaan; memilih baris pertama atau mencari nomor saja tidak membuktikan target yang benar.

Namun `selected_draft` hanya berasal dari eligibility Native berikut:

```sql
where g.status='CUT' and g.picked_up_at is null and not g.material_issue_posted
```

Kelompok yang sudah mengeluarkan bahan, pickup, atau sampai QC tidak akan muncul sebagai draft terpilih pada pembaca ini. `ConnectedCuttingPage` juga memeriksa `editable`, UUID kelompok, PO dan versi Native sebelum Save/Delete/Post. Jangan menambahkan tautan QC→editor draft untuk kelompok tersebut lalu menganggap detail/edit sudah tersedia. Tidak ada tautan, grant, reader atau writer baru yang ditambahkan dalam inspection ini.

Penerus yang bisa dipertimbangkan: pembaca posted-history terpisah dengan current view permission sebelum metadata, exact group→PO FK, closed read-only fields, batas halaman lengkap, stale/denied retirement dan no-ERP-DML proof. Route/edit/inverse baru tetap memerlukan kontrak owning writer yang benar dan qualification Native/Auth/browser. Alternatif yang lebih sempit adalah exact source navigation hanya untuk draft Native yang masih eligible, dengan selected PO/group di luar halaman pertama; itu tidak mencakup potongan posted dari QC atau mutasi bahan.

Native writers/guards/frozen CP6 tetap unchanged. Ini penjelasan batas yang ditemukan, bukan keputusan owner untuk membuka edit posted atau klaim bahwa semua koreksi potongan tersedia.

# S05 — kategori aksesori: diambil mandor versus standar GOOD

**Prepared, Native/browser qualification belum dijalankan.** `independent_acceptance=false`, `production_go=false`. Owner D17-19C, commit `20e0a8677b738cd934e47ef1dd113cd168635581`, `docs/cp7/OWNER_DECISIONS_20261008.md`: BOM kategori dulu; laporan pengambilan versus standar tetap wajib; varian fisik tetap terlacak. Ini satu reader terpisah dan UI standalone, tanpa mengubah menu, shared types, frozen parent, stok, jurnal, payroll, HPP, BOM atau metode posting.

## Arti angka dan kelengkapan

| Bagian | Dasar yang dibaca | Batas interpretasi |
| --- | --- | --- |
| Diambil | Detail nota `POSTED`, `physical_at` pada tanggal WIB terpilih; jumlah dasar, konversi transaksi, biaya stok, harga/tagihan dan mutasi fisik tersimpan | Pengambilan bruto. Retur/credit melalui alur lain tidak otomatis dianggap konsumsi atau pengurang fisik. Nota `DRAFT`/`REVERSED` dikecualikan. |
| Standar GOOD | Lot `PRODUCTION`, `produced_at` pada tanggal WIB terpilih; `good_qty_pcs × qty_per_good_fg_base` dari `fg_accessory_cost_snapshots` | Lot `VOIDED_PRODUCTION`, conversion/opening/return dikecualikan. `cached_qty_pcs` atau stok yang masih ada tidak menjadi denominator; pengeluaran/penjualan tidak menghapus standar historis. |
| HPP/penggantian | Nilai snapshot Native efektif dan seluruh ID revisinya | Biaya dapat direvisi oleh recost Native. Ini bukan GL periode atau pengakuan biaya baru. Biaya stok nota, tagihan, HPP dan penggantian ditampilkan terpisah tanpa selisih uang palsu. |
| Selisih jumlah periode | Pengambilan pada periode dikurangi standar output pada periode, hanya bila seluruh bukti cocok | Dua kelompok tanggal. Tidak menyatakan waste atau konsumsi per PO. Filter PO diterapkan pada kedua kelompok; tanpa filter, pengambilan tanpa PO tetap masuk dan ditandai. |
| Nol standar | Komitmen BOM kosong atau keputusan rework `NONE` eksplisit, dengan lineage lengkap | Tidak ada GOOD, tidak ada snapshot/komitmen, atau tidak ada standar kategori tidak menjadi nol otomatis. Pada kategori tanpa snapshot, nol hanya saat seluruh lot teralokasi mempunyai standar kosong eksplisit. |

Snapshot positif dengan penggantian nol tetap masuk walau tidak ada entitlement. Native menolak HPP positif dengan penggantian nol; kasus Native nol yang disiapkan memakai biaya/rate nol yang sah, dengan jumlah standar tetap positif. Tidak mengubah penolakan Native.

Penerima normal berasal dari PO dengan penjaga koreksi mandor aktif. Rework memakai `rework_accessory_decisions.reimbursement_contractor_id` sendiri; penerima kosong tidak diganti mandor PO. Lot tanpa penerima pada periode/PO pilihan tetap terlihat dan menahan selisih. Komitmen, set snapshot, produk, jumlah GOOD dan lineage BOM/selection diperiksa; pembaca tidak memanggil `ensure`, `commit`, recost atau posting untuk melengkapi data.

**Satuan historis:** snapshot tidak memiliki field UOM. Pembaca memerlukan audit pembuatan kategori dengan satuan yang sama dan tidak ada perubahan satuan pada audit retained. Perubahan nama tidak mengganggu. Riwayat tanpa audit awal, perubahan satuan (termasuk berubah lalu kembali), atau sumber mutasi pengambilan yang tidak cocok menjadi `UNKNOWN`; jumlah sumber tetap terbaca dengan label satuan belum terbukti dan selisih ditahan. Tidak memakai `updated_at` sebagai bukti urutan karena `now()` sama dalam satu transaksi. ID audit satuan ditampilkan. Ini batas sumber historis yang eksplisit, bukan izin menambah ulang snapshot lama.

Semua nilai uang/jumlah melewati RPC sebagai string desimal; ID bigint audit/revisi juga string. UI memeriksa kelengkapan baris, identitas, periode WIB, konversi/jumlah/biaya, sumber summary, nol versus unknown dan selisih sebelum menampilkan hasil. Tidak ada agregat kuantitas lintas satuan. Batas 367 hari/3000 sumber menolak hasil terlalu besar secara utuh, tidak memotong diam-diam. Mandor dicari sebelum paging (30/halaman), PO maksimal1000 dengan refusal eksplisit bila lebih.

## Berkas dan integrasi

| Berkas baru | Tanggung jawab |
| --- | --- |
| `report.sql` | Satu public read, private statement snapshot, live access sebelum/sesudah baca. Tidak ada tabel/triggers/penulis baru. |
| `stage.py` | Default exact current vendor parent `cp7_vendor_receivable.composition` (qualified head41c, source pada ab506); verify actual parent sebelum additive DDL, admission seluruh22catalog, seluruh data/sequence sama, inverse ke parent tepat. |
| `cases.py` | Sepuluh kasus actual Native yang dipersiapkan; setiap interval reader berisi baca saja. Full raw jawaban/refusal SQLSTATE dipertahankan pada `actual_raw_reads`. |
| `preflight.py`, `SOURCE.json` | Offline source pins dan kontrol negatif mutation/catalog. Bukan PL/pgSQL compile atau actual qualification. |
| `src/ConnectedAccessoryStandardReportPage.tsx` | Halaman tersambung standalone siap dipasang root sesudah SKU; memakai client/auth tunggal aplikasi dan adapter tipe RPC yang sempit. Tidak menyentuh menu atau file tipe parent. |
| `src/accessoryStandardReport.ts`, CSS, tests dan fixture | Kontrak presisi, render sumber/kondisi unknown, stale-read/auth/filter guards, worksheet independen dan DOM controls. |

Akses awal dipersempit ke Owner/Admin dengan kedua hak existing `finance.contractor_accessory.view` dan `finance.hpp.view`. Role reader NOLOGIN/NOINHERIT/NOBYPASSRLS, tanpa membership, grant tabel ERP atau grant writer Native baru. Browser hanya mendapat public read; private schema dan fungsi tetap tertutup. Fungsi entry milik postgres memeriksa user/role/permission database saat ini, bukan metadata JWT. `READ COMMITTED` wajib agar cek hak kedua memakai snapshot baru. HTTP401/403, perubahan identitas/hak atau filter segera menutup angka lama; balasan terlambat tidak diterapkan.

## Jalur qualification yang disiapkan

Tidak ada `connect`, `commit`, main executable, workflow atau auto-install predecessor baru. Caller/root memasok cursor transaksi disposable dan **state hasil instalasi parent aktual yang terverifikasi**, bukan receipt JSON.

```python
from cp7_accessory_standard_report import cases, stage

# qualified_vendor_state berasal dari integrator runtime exact vendor.
# Jalankan masing-masing callable dengan strict runner/savepoint rollback yang ada.
factory = lambda cur, today: cases.cases(cur, today, qualified_vendor_state)
```

Fixture dan transisi Native dijalankan saat parent tepat masih terpasang. `stage.reader_only` kemudian memasang reader, membuktikan actual all22, membaca, membuktikan semua baris/sequence tetap sama, melepas reader, lalu memverifikasi parent aktual kembali. Transisi berikutnya baru dilakukan sesudah inverse. Ini mencegah penulis Native menggunakan catalog tambahan yang belum dibuktikan seal-nya. Menyatukan reader dengan runtime SKU baru memerlukan wrapper additive integrator yang memverifikasi parent SKU aktual; tidak boleh mengganti state/pin vendor atau memproyeksikan catalog agar lolos.

| ID Native yang disiapkan | Oracle yang ditetapkan sebelum run |
| --- | --- |
| `S05_NATIVE_CATEGORY_VARIANTS_PO` | Dua varian stok Native pada satu kategori, diambil11, standar7,5, selisih3,5; biaya stok30/HPP15; tanpa filter tambah1 tanpa PO menjadi12. Semua material/note/movement/BOM/snapshot IDs nyata. |
| `S05_NATIVE_HISTORICAL_BOM` | Successor BOM3×rate9 sah tidak mengganti snapshot lama7,5/HPP15 dan identitasnya. |
| `S05_NATIVE_LATE_INVOICE_COST_REVISIONS` | Invoice Native30×3,50 menghasilkan AP105/GRNI0/stok23×3,50; qty fisik tetap; biaya stok nota14→24,50, HPP standar15→26,25, penggantian15 tetap, qty/sumberBOM7,5 tetap. Raw revisi Native ditampilkan, GL material/subledger dan integrity delta wajib cocok. |
| `S05_NATIVE_ZERO_REIMBURSEMENT` | Snapshot jumlah7,5 tetap ada dengan biaya0/penggantian0 dan entitlement kosong. |
| `S05_NATIVE_EMPTY_AND_NO_OUTPUT` | Sebelum GOOD standarunknown; setelah GOOD dengan komitmen BOM kosong, standar0 eksplisit. |
| `S05_NATIVE_WIB_COHORTS` | Lima session zone memberi report identik; pengambilan kemarin7 dipisah, hari ini dua transaksi pada00:00/23:59:59,999999 berjumlah5 versus standar7,5. |
| `S05_NATIVE_NOTE_DRAFT_INVERSE` | Draft tidak masuk; inverse nota Native mengeluarkan pengambilan, menjaga standar GOOD. |
| `S05_NATIVE_QC_INVERSE` | Inverse QC Native mengeluarkan lot voided beserta standar report tanpa menghapus sejarah snapshot. |
| `S05_NATIVE_REWORK_NONE_RECORDED_RECIPIENT` | Laundry rework NONE memakai penerima yang benar-benar direkam Native pada keputusan, standar0 eksplisit; tidak menghitung ulang penerima dari PO saat laporan dibaca. |
| `S05_NATIVE_CURRENT_ACCESS_PRIVATE_ACL` | Staff dengan hak tetap ditolak, service JWT ditolak; Admin aktif terbaca lalu hakHPP dicabut dan ditolak; owner aktif terbaca lalu owner nonaktif ditolak. Private ACL/data/sequence diperiksa tiap interval. |

Belum dijalankan: SQL/PLpgSQL compile terhadap Native schema aktual, sepuluh kasus di atas (termasuk recost), real Auth/HTTP revocation during read dan real browser desktop/mobile. Source-hole corruption controls (missing commitment/partial snapshot), penerima kosong dan UOM-audit-loss dipertahankan sebagai adversarial contract controls lokal; tidak mengarang posted-row injection lalu menyebutnya jalur transaksi sah. Original `save_rework_order_v2` secara sah merekam mandor PO pada laundry rework, termasuk NONE; kasus Native itu tidak disebut unallocated. Untuk klaim runtime source-hole/unallocated branches dibutuhkan retained actual hole atau isolated auditor fault fixture yang disepakati. Parser unit/DOM controls tidak menutup kebutuhan ini. Empty rework NONE tanpa komitmen juga tetapunknown, mengikuti aturan missing commitment.

## Status lokal dan pekerjaan yang tetap terbuka

- TypeScript noEmit: PASS. Kontrak/DOM worksheet:29 PASS (21 kontrak,8 DOM). Python compile dan source preflight27pin/4mutation/4catalog negative controls PASS. Tidak menjalankan database.
- Offline source/mutation/catalog controls: jalankan `python scripts/cp7_accessory_standard_report/preflight.py`.
- Actual Native/HTTP/browser: **NOT RUN**, tidak ada run/artifact/PASS yang dibuat. Integrasi menu/tipe umum masih milik root.
- S03 tetap terbuka: pilihan owner per periode, carry WIP versus beban periode, alasan/audit, sumber/alokasi satu kali dan penjaga tanggal/period/dependency. Reader ini tidak menafsirkan atau mengimplementasikan pilihan tersebut.
- S04 tidak menambah batas umur; writer/guard yang ada tidak diubah.
- Full independent acceptance, coverage replacement CP6 dan production_go tetap terpisah.

## Inventory S03 yang tidak ikut diimplementasikan

| Sumber existing | Perilaku aktual | Gap terhadap keputusan owner |
| --- | --- | --- |
| `scripts/cp7_hpp_close/hpp_close.sql`, `native_delta.py`, `cases.py` | Native attendance manifest mengambil payroll dengan `period_start/end` yang persis dan hasil jahit pada periode yang sama. Positif biaya/tanpa jahit menolak preview dengan `POSITIVE_POOL_ZERO_SEWING_OUTPUT`. `ATTENDANCE_POOL_ZERO_OUTPUT` di close adalah INFO, bukan lifecycle pilihan biaya. | Memperlebar periode akan mengganti identitas sumber. Belum ada keputusan owner per periode, alasan/audit, reservation carry ke output berikut, atau reclassification beban periode dengan invariant satu kali. |
| `scripts/cp7-src/hpp-pool/pool.sql`, `src/AttendanceHppPoolPanel.tsx`, `src/hppPoolContract.ts` | UI `CREATE`/`ACTIVATE`/`CANCEL`/`REPLACE` memakai writer Native, periode/review token, permission HPP dan envelope transaksi. | Pilihan S03 belum menjadi aksi/halaman. Owner/Admin manage pool bukan otomatis kewenangan memilih policy owner per periode. |
| `scripts/cp7-src/planning/material-requirements.sql`, `src/ContractorIssuePage.tsx` | Material requirement adalah perencanaan bersyarat; halaman lama contractor issue berisi demo. | Keduanya tidak menjadi bukti actual installed/consumed atau report mandor produksi. S05 ini memakai connected note + actual FG snapshots. |

S03 memerlukan slice tersendiri: keputusan owner per periode yang insert-only/versioned, alasan, sumber payroll APPROVED yang sama (PAID settlement), jalur carry atau WIP→beban melalui writer Native yang sah, reversal/dependency/closed-period guard, dan bukti tidak mengakui biaya kedua kali. Tidak ada financial posting baru dibuka oleh pekerjaan ini.

# Pembetulan retur pelanggan tercatat

Kandidat ini menambah edit retur fisik pelanggan: retur lama dibalik dan satu retur pengganti disahkan dalam satu transaksi database. Nomor, waktu dan isian fisik retur lama tetap tersimpan. Pulihkan isi lama membuat pembetulan baru dengan alasan dan pemeriksaan baru. Ini tidak menghapus transaksi lama atau otomatis membatalkan seluruh rantai usaha.

## Batas dan sumber

- Read: `erp_cp7_get_sales_return_correction_v1(p_query)`; write: `erp_cp7_correct_sales_return_v1(p_payload,p_request,p_expected)`.
- Parent, alokasi baris penjualan, lot, stok, gudang aktif, grade, nilai retur, pembayaran aktif dan HPP berasal dari Native yang terpasang. Client tidak mengirim produk, lot atau HPP buatan.
- Setiap dokumen tetap memakai satu baris per alokasi, mengikuti batas Native. Kombinasi grade/gudang untuk alokasi yang sama tetap memakai dokumen retur terpisah.
- Review mengikat revisi/token parent dan token retur yang mencakup stok lot terkait, HPP, gudang serta jurnal sumber. Pemeriksaan otoritas dan token diulang setelah menunggu kunci.
- Izin edit memerlukan Owner/Admin dengan izin create/post/reverse retur serta lihat HPP yang sekarang berlaku. Cached outcome tidak melewati pemeriksaan otoritas sekarang.
- UUID dan payload yang sama mengembalikan satu hasil committed. UUID sama dengan payload berubah ditolak. Error akhir mengembalikan seluruh efek transaksi, termasuk metadata CP7.
- Stock yang sudah dipakai tetap bisa menahan pembalikan Native. Pembayaran aktif tidak otomatis direfund. Tidak ditambahkan batas umur koreksi atau kebijakan pemilik baru.
- Waktu WIB yang tidak diedit mempertahankan mikrodetik sumber. Pembalikan private menggunakan waktu fisik asli. Jurnal Native tetap memakai tanggal posting yang diizinkan Native; metadata penataan waktu dan overlay laporan mengikat jurnal asli/invers sebenarnya.

## Native tetap utuh

Empat helper inverse Native disalin ke namespace private dengan empat delta yang dinyatakan: penjagaan context, panggilan helper private, timestamp gerakan inverse asli, dan pencatatan penataan waktu jurnal/HPP retur. Definisi Native asli dibandingkan dengan SHA-256 sumber dan derivasi private harus identik dengan delta yang dinyatakan. Tidak ada aplikasi diberi DML ERP atau EXECUTE private. Tabel history dan helper source menolak UPDATE, DELETE dan TRUNCATE.

Resolver sumber membaca tautan nyata dan mengembalikan parent/child serta offset halaman. Outcome membawa offset pengganti yang dihitung resolver Native; UI tidak menebak halaman pertama. Sumber inverse yang tidak memiliki tautan pembetulan ini mempertahankan pembatasan sebelumnya.

## UI dan recovery

`ConnectedSalesPage` memiliki write/recovery UUID. `SalesReturnPanel` membaca riwayat dan gudang memakai tiket owning invoice. `SalesReturnCorrectionPanel` memiliki satu read RPC, meminjam tiket tersebut, dan tidak membuat atau menyelesaikan tiket parent. Reply lama/retired tidak menghidupkan fakta kembali. Error read sekarang meretire owning invoice.

Input operator disimpan sementara dalam sesi per actor/permission/parent dan dihapus setelah commit. Yang disimpan hanya ID pilihan dan isian pengguna; kapasitas, baris katalog, token, tiket dan tanda sudah diperiksa tidak disimpan. Alokasi yang belum dimuat kembali tidak dapat disimpan.

Riwayat mempunyai `Edit retur …`, `Lihat perubahan retur …`, tautan transaksi lama/pengganti dan `Pulihkan isi retur sebelum pembetulan`. Tombol inverse lama tetap mengikuti perilaku dan label yang telah diuji sebelumnya.

## Uji yang dinyatakan sebelum hasil

`scripts/cp7_sales_return_correction_cases.py` menetapkan 25 ID unik: 16 Native, 4 race dengan koneksi/kunci nyata, 3 Auth HTTP, 2 browser desktop/mobile. Alur browser melakukan 2 PCS/Rp40 → 1 PCS/Rp20 → 2 PCS/Rp40, menautkan child asli/pengganti, dan desktop membuang reply setelah backend commit lalu mereconcile UUID yang sama setelah reload.

YEAR_364 membuat transaksi Native sungguhan: saldo awal 4.516 PCS, penjualan asal 48, retur 24, 364 penjualan kemudian masing-masing 12. Retur pengganti 36 harus menambah semua 364 saldo berjalan berikutnya sebesar 12 di urutan buku dan kronologi, baik stok fisik maupun tersedia. Empat array asli sebelum/sesudah disimpan. Ini bukan bukti SLA produksi atau seluruh P19.

Tes history menambah 26 peer-return Native supaya child pengganti benar-benar di offset 25. Pembatasan field, jumlah, cents, pembayaran aktif, stok yang telah dipakai, gagal posting terakhir, closed books, akses dicabut, source berubah, replay dan pemulihan diuji dengan rollback boundary Native/private lengkap.

Status ketika kandidat ditulis: Python/JS/TS parser syntax dan diff whitespace lolos lokal. Runtime Native dan browser baru belum dikualifikasi. Jalankan workflow `CP7 Native Atomic Customer Return Correction`, simpan ZIP asli/digest/seluruh JSON roots/log, periksa setiap 25 ID dan empat grup, install/restore/advisor gates, pin source serta screenshot asli sebelum memperbarui status. Shell, CodeQL dan regresi F03 yang terpicu juga harus diperiksa pada head baru; hijau head sebelumnya bukan penerimaan kandidat ini.

`production_go=false`; penulis bukan auditor independen. Supplier-return, cutting-posted edit/inverse, rollback seluruh dependency, recipe/material eligibility, P18/P19 penuh, keputusan owner dan hosted P21 masih terpisah.


## First c79 UI compile result

Actual cash/misc run37173078125/job111349864833 and run37173077938/job111349864508 stop before disposable provisioning on six TypeScript diagnostics. Completed Original full logs and exact diagnostics are retained at evidence/sales-return-correction/first-c79-ui/RECEIPT.json. No Native/restore credit is claimed. The successor uses the actual TransactionSourceLink sourceType/sourceId props with pending/stale disablement, a nullable ticket signature in the declared DOM stand-in, explicit globalThis.document for its DOM container, and Number only after the strict outcome parser has accepted the actual page offset. No Native budget, guard or timeout is altered. Fresh Shell/Native25 and triggered regressions remain required.


## Ba Shell qualified; mobile E01 refresh defect

Exact ba721df6 Shell/run37173411901 completes 1468 tests in152 files,6 Shell browsers,138 private-kernel-only controls,264 runtime files/195 owned RPC boundaries/53 stylesheets and both original SARIF with zero findings. The full Original proof is evidence/sales-return-correction/qualified-ba-shell/RECEIPT.json. This does not qualify the current Native25 or later patch.

E01/run37173411862/job111350911010 is INCOMPLETE:1 DB/1 Auth/1 desktop PASS,1 mobile INCOMPLETE. Its ordinary return save remains disabled after review was reset. All6 original roots, full log, member hashes and3 unedited captures are retained at first-ba-e01; the actual mobile failure is visually reviewed. Restore/advisor/install/primary/backup pass; package runtime remains false. The owning history can render a new mutation object with the same callbacks; depending on that whole object reloads the child and clears review. The successor depends on stable ticket callbacks, preserving lines/review during unrelated history renders. Child facts remain bound to the ticket that actually read them: a new owning ticket, even with equal header fields, requires a new child read and review. Two DOM controls cover both boundaries. Native budgets, guards and deadlines remain unchanged.

The same16-case Native budget strengthens INCREASE with genuine return edit2→3, then note correction4→3 with actual child replay, then correction of that new active child3→2. Its expected positions are source7/destination2 and receivable20. This cross-contract scene is authored, not yet executed/accepted. The client maps known refusal codes to operator guidance without altering unanswered-write recovery classification. All additions require a fresh exact-head run.

## 1d0 actual results and oracle repair successor

Exact1d0 completed22/24 workflows. Its complete Shell passes1470 tests/152 files/6 browser controls/138 private controls/264 runtime files/195 owned RPC/53 CSS and both CodeQL. E01 passes all4 actual cases including mobile lost-return-reply, reload and same UUID. The old ba mobile failure is not retroactively passed. The actual return→note→replayed-return Native scene now passes at1d0.

Return25/run37174410987/job111353931126 is INCOMPLETE:14 Native/4 races/3 Auth HTTP/2 browser pass; EXACT fails on the fixture's future timestamp and CLOSED_BOOKS calls a nonexistent probe read function. Original artifact11293411029 has SHA2563fae0a3796f86ea11e4a267f1a9caa10e62828bd5e11d7a3b71ab69c9f64c134. Combined22/run37174410929/job111353930840 is INCOMPLETE21PASS/1INCOMPLETE (late-filing public catalog equality). Original artifact11292703229 has SHA2565cedf654c2fd9543efbd27d0c1b485b59ec1eb78f0710691b8f8923f6200c0fc. Its end restore differs only in identical function pair order, but original case-level snapshots were not retained; do not retroactively pass that case.

The successor changes only oracle/qualifier code: the actual Native clock's preceding second retains123456 microseconds; the real finance cases reader includes actual source dates and4 exact revenue/COGS/AR/FG report deltas; a future-date replacement still must restore the full Native/private boundary. Combined binds the existing exact catalog comparator locally with every raw snapshot and7 read-only sensitivity controls, and verifies the private return derivation/capabilities. Native SQL, guards, permissions,25/22 budgets and deadlines remain unchanged. Fresh exact-head qualification is required.

Workspace maintenance removed the unpublished local evidence directory. The Original remote artifacts remain available. No lost local proof file is represented as published; the large evidence copy is separate from this small repair. Resume fresh Return25/Combined22 and triggered regressions, then remaining CP7 edit/rollback work. Full CP7/independent/production GO remain open.

## D776 Native25 qualified with exact product-byte reconciliation

Run37220228014/job111488892693/artifact11309799311 qualifies all25 predeclared cases:16Native/4real races/3real AuthHTTP/2actual browser PASS. Complete Original roots, ZIP member hashes and unedited desktop/mobile captures are retained at evidence/sales-return-correction/qualified25-d776. All install/primary/backup/security/writer-runtime/CP6 restore gates pass and Auth returns0→0. The report explicitly pins tool_head d776b19227032be255a59214bf750ddef4ff70d8 and product_ref1d0e6dc8254de5a3f0e2c0abfbb8a4b4084889fe; git comparison verifies every declared product path is byte-identical between those commits. D776 changed only two CP7 oracle drivers and this handoff. These exact pins are preserved rather than rewritten as identical commit identities.

Both actual browsers complete2PCS/Rp40→1PCS/Rp20→2PCS/Rp40, preserve original facts and immutable links, and use exact UUID recovery with zero console/cleanup failures. Independent read-only arithmetic checks the four raw367-row arrays in both YEAR_364 and actual HTTP YEAR_364: all364 subsequent Native sales have unchanged identities, timestamps, lots, locations, grades and book ranks, and every official/book/physical/available running prefix increases12. All full prefixes recompute exactly; final124→136 and original24→effective36 remain consistent. The actual HTTP case took7129.616ms within the unchanged8s bound; this is not a production SLA. Receipt: RAW_ARITHMETIC_VERIFICATION.json. Retention and arithmetic add zero Native execution credit and are not independent P20 acceptance. First c79/ba/1d0 failures remain unchanged. Later1766 and successor candidates require their own fresh qualification.

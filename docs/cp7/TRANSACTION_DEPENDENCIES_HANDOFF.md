# Penerimaan Laundry → QC yang menghalangi pembatalan

Native69 sudah qualified pada3809968e455486f66eea46b726e276644e845b7c/tree ae23ca9195c34bec8d05259099323243558e9a45:38 DB/4 race/9 Auth HTTP/18 browser, seluruh64 ID sebelumnya tetap. Original dan16 gambar asli: evidence/transaction-source/qualified69-3809/RECEIPT.json. Shell pada source yang sama lolos1403/146/6 dengan dua CodeQL nol temuan. Writer evidence bukan independent acceptance.

Penerus pagination-shrink sudah qualified pada3af3be8a/run37127410144/job111215429856:69/69 dengan seluruh ID sebelumnya dan assertion halaman kosong setelah26→25. Shell source sama lolos1404/146/6; seluruh20 workflow terpicu lolos. Jika perangkat lain mengurangi26 QC menjadi25 saat operator membuka halaman2, halaman bisa kosong; tombol sebelumnya tetap ada dan rentang26–25 tidak ditampilkan. Tidak menambah atau mengurangi budget69. Original: evidence/transaction-source/qualified69-3af3/RECEIPT.json. Kontrol lokal116/9 tetap di receipt sebelumnya sebagai sejarah. Status pending yang lebih bawah adalah sejarah awal kandidat3809, bukan keputusan terbaru.

## Alur operator

Pada penerimaan fisik POSTED yang belum bisa dibatalkan, **Lihat QC terkait** menampilkan QC aktif yang benar-benar memakai baris penerimaan ini,25 per halaman. **Buka QC terkait** memakai current source resolver, nomor inspection Native dan owning reader yang memeriksa UUID tepat. Jika QC memang salah dan pengaman Native mengizinkan, operator memakai inverse QC yang sudah ada. Buka penerimaan kembali dari antrean QC, muat hasil terbaru dan periksa ulang sebelum inverse penerimaan.

Ini dua perintah terpisah. Tidak ada writer baru, penghapusan sejarah atau janji satu rollback atomik seluruh rantai. Invoice vendor, claim, payroll dan status PO masih bisa memblokir. “Tidak ada QC aktif” hanya menjawab keluarga QC.

## Kontrak / akses

`erp_cp7_get_transaction_dependencies_v1(p_source jsonb,p_offset integer)` memakai private role cp7_transaction_source_read yang sudah ada: tetap35 tabel SELECT/32 private roles, nol ERP DML/tambahan EXECUTE writer Native. Tidak menambah role, cache, job, trigger atau tabel.

Input hanya LAUNDRY_RECEIPT dan UUID asal, offset kelipatan25 pada0..1000000, limit25. Kedua izin saat ini (production.laundry.view, production.final_sku.view) diperiksa sebelum header/FK dan di akhir. Public RPC hanya authenticated; private function/schema tidak tersedia bagi anon/authenticated/service_role.

Relasi persis pengaman frozen Native reverse_laundry_receipt: qc_inspection_items.source_laundry_receipt_line_id→laundry_receipt_lines.id, receipt_id tepat dan qc_inspections.status <> REVERSED. EXISTS menghasilkan satu baris/inspection walau beberapa item merujuk receipt sama. Tidak mengganti dengan filter POSTED yang lebih sempit. Tidak mengedit migrasi/fungsi CP6.

Kontrak tertutup cp7.transaction-dependencies.v1 mengikat actor/source/parent UUID/nomor/status/revision, offset/limit/total/has_more, setiap QC UUID/nomor/status/revision, read_at dan business_DML=false. Tidak mengembalikan jumlah, tarif, HPP, uang atau metadata bebas. Parser menolak field tambahan, duplikat, REVERSED, truncation dan konteks lain. UI menolak parent berbeda versi/nomor/POSTED dari yang sedang ditampilkan.

Read dimulai saat tombol ditekan. Read baru mengosongkan daftar lama; jawaban lama ditolak sesudah perubahan actor/proyek/izin/versi/parent/kesiapan workspace/unmount. Kegagalan bukan daftar kosong. Viewer bisa menelusuri tanpa reverse; tombol inverse tetap mengikuti Native/current rights. Data input alasan tidak pernah menjadi fakta tepercaya.

## Berkas

- scripts/cp7-src/transactions/dependencies.sql, digabung source bundle setelah resolver; verify() memeriksa owner/ACL/volatility/nol DML.
- LaundryReceiptDependencies.tsx, transactionDependencies.ts, integrasi terbatas ConnectedLaundryPage.tsx dan CSS yang sudah dimiliki.
- Satu RPC terdaftar di database.preconnect.ts/source ownership/access catalog. Hitungan berdasarkan daftar batas tepat, bukan melonggarkan pemeriksaan.
- Provider Native/browser/fixture/probe yang sudah ada, tanpa workflow alternatif/pengaman ringan.

## Bukti penerus

Budget69 =38 DB/4 races/9 Auth HTTP/18 browser. Semua64 ID terdahulu tetap wajib. Lima ID baru:

- CP7_SOURCE_LAUNDRY_QC_DEPENDENCY_PAGES:26 QC dari perintah Native asli, halaman25+1, QC penerimaan lain tidak ikut, read full boundary unchanged, satu QC inverse mengurangi satu dependency;25 sisanya tetap memblokir parent.
- CP7_SOURCE_LAUNDRY_QC_DEPENDENCY_AUTHORITY_FIELDS: masing-masing revoke current view menolak sumber ada/tidak ada sebelum metadata; malformed scope/offset/missing source dan full boundary unchanged.
- CP7_SOURCE_LAUNDRY_QC_DEPENDENCY_HTTP_CURRENT_VIEW: JWT ADMIN asli, exact actual relationship, same-token QC view revoke→403 untuk UUID ada/tidak ada tanpa DML.
- CP7_SOURCE_LAUNDRY_QC_DEPENDENCY_BROWSER_DESKTOP dan _MOBILE: Auth OWNER asli, blocked receipt→actual related QC→owning QC inverse→actual receipt source→receipt inverse; FG1→0 dan satu WIP inverse30PCS, original items/movements retained. Empat gambar asli, overflow check.

Restore CP6/full public catalogue, exact source hashes, primary untouched, backup/restore/advisors/Auth0→0/console checks/private-role budget/timeout/semua retained packages tetap wajib. First failure tetap Original; perbaikan wajib requalification.

Local115/9 files/build/security/syntax lolos. Whole-suite local Native run is blocked by unavailable non-root PostgreSQL. Explicit local PGlite0.5.8 yields1400/1403 with3 unchanged internal-guard mock-table permission failures; it is INCOMPLETE, not Native proof. Both first and stand-in logs are retained in evidence/transaction-source/laundry-dependencies-local. Current source-bound CI Shell at7300 is1396/1396 with native private-kernel runtime; successor CI must qualify independently. Bukan bukti Native69. WIP source/invoice vendor, full P08/P18/P19, independent P20/installed P21 dan production GO tetap terbuka.

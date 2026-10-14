# Laporan Pro Max — Sol CP1–CP7

## Identitas dan putusan

Kandidat produk `0b7049d9203bac52b47a4c89f3e0d75646067a8f`, tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`. Cabang auditor `audit/sol-cp1-7-0b7049d9-20261014`; sumber/runtime/harness/oracle/fixture terikat oleh `ROUND_MANIFEST.json`, supplemental manifests, `RUN_REGISTER_FINAL.json`, identitas per job dan hash arsip/member. Panduan SHA-256 `5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639`. Tidak membaca laporan auditor lain pada putaran ini; paparan personal-context terdahulu dicatat di `EXPOSURE_LOG.md` dan tidak digunakan sebagai bukti mandiri CP2.

Ubuntu24.04, SupabaseCLI2.116.0, PostgreSQL image17.6.1.165, Python3.12/psycopg3.2.10 dan Node22; PR44 memiliki Native PG16 kernel scope terpisah. DB sementara CI saja, synthetic input eksplisit; real Auth/PostgREST/Chromium pada keluarga yang menyatakannya. Bootstrap historis disebut sebagai input rekonstruksi, bukan uji baru original CP2/hosted. Workflow SHA dan product SHA berbeda dan dibind terpisah. Putusan HOLD; pekerjaan audit putaran selesai, `audit_complete=false`, `production_go=false`.

## Vonis per checkpoint

| CP | Vonis | Bukti dan batas |
|---|---|---|
| CP1 | LULUS cakupan sumber/baseline rekonstruksi | Tree/guide/ledger/body/config identity dan build/security/source ownership. Bukan fresh hosted preflight. |
| CP2 | INCOMPLETE pemulihan; arsip LULUS | Original encrypted archive dibaca/dekripsi privat, 149/148/142/104 terverifikasi, Auth0. Tidak ada original functional restore runtime. |
| CP3/3.5 | LULUS regresi yang tercatat, dengan disposisi | 326 exact identities pada final CP7; frozen historical outputs tidak direlabel. C0 D01 terpisah. |
| CP4/4.5 | LULUS Auth/identity/WIP pada permukaan teruji | F01/F02 86, current role/revoke/real HTTP, exact ACL/catalogue. Alternative API/GraphQL belum tertutup. |
| CP5 | LULUS core Native yang tercatat | BS/rework/rewash/claim, WIP, temporal identity dan correction families; bukan semua kombinasi/perangkat. |
| CP6 | GAGAL/HOLD | SOL-001 money policy/capacity, SOL-002 evidence; positive install pertama AZ OPEN dan SOL-003 diagnostik. |
| CP7 | GAGAL/HOLD penerimaan penuh | Public supplier payment counterexample; Native range-dozens known gap. F03/F04/F05/P19/K2–K6 banyak PASS dengan batas per bukti. |

## Temuan per akar masalah

### SOL-001 — Pembayaran supplier dapat membuat saldo bank negatif tanpa kebijakan overdraft yang teridentifikasi

**S1 / P1; CONFIRMED_BUSINESS_COUNTEREXAMPLE; OPEN.** Command memeriksa AP, izin, tanggal, token, dan akun aktif, lalu menyerahkan posting kepada Native. Kapasitas kas/bank bukan bagian tinjauan atau penjagaan yang terlihat pada jalur ini.

Expected: Tolak atomik jika dana tidak cukup, kecuali ada kebijakan saldo negatif yang sah dan batasnya dipenuhi. Actual: POSTED: 0 → -1.00; tidak ada kolom overdraft pada bank fixture dan izin kebijakan tersebut tidak ditemukan dalam inventaris acuan.

Repro: Bank baru aktif, tanpa opening/funding, saldo GL 0; receipt FINAL menimbulkan AP 1000. → Sebagai OWNER, kirim command publik pembayaran supplier 1.00 dengan review token sah. → Respons POSTED, AP 999, saldo bank -1.00. Kontrol funded 34.50 → pembayaran 1.00 → 33.50 lulus.

Dampak: Saldo bank dapat tercatat di bawah nol walau jurnal seimbang dan AP tidak kelebihan bayar. Bukti ini tidak berarti uang nyata hilang; seluruh fixture sintetis.

Perbaikan: Gunakan penjagaan kas bersama pada otoritas Native, dengan lock per akun dan aturan per tanggal. Jika owner mengizinkan overdraft, simpan kebijakan, batas dan periode berlaku secara eksplisit. Jangan mengarang default atau hanya menambah pemeriksaan UI.

Code: `scripts/cp7-src/invoices/payment-create.sql`, `erp.post_supplier_payment(uuid)`, `erp.cash_accounts`, `erp.journal_lines`. Bukti: `FINDINGS.json` dan original report pointer/hash dalam ledger.

Acceptance:

- Dana cukup, tepat habis, dana kurang dan kebijakan pending.
- Dua invoice berbeda membayar dari bank yang sama bersamaan: gabungan tidak melampaui kapasitas.
- Backdate, reversal dan koreksi mempertahankan aturan histori serta sumber pendanaan.
- Terapkan kontrol yang sama pada vendor/laundry, payroll, pengeluaran lain, uang muka dan refund; bukti bug saat ini khusus supplier.
- UUID replay sekali; semua penolakan memulihkan payment/journal/request/stock/HPP.

### SOL-002 — Artefak BE hanya menyimpan empat dari enam belas hasil yang telah dijalankan

**S2 / P2; CONFIRMED_EVIDENCE_PACKAGING_DEFECT; OPEN.** BE memakai global r1.OUT. Kasus kelima lazy-import cp6_av_probe; import itu mengganti r1.OUT ke folder av. Hasil selanjutnya dan terminal report ditulis di av, sementara workflow mengunggah be.

Expected: Seluruh 16 ID dan hasil terminal berada dalam artefak yang diunggah. Actual: Produk BE lulus 16 kasus menurut log lengkap; paket bukti parsial 4/16.

Repro: Jalankan unchanged BE after pada kandidat ini. → Artefak 11892298930 berisi BE_CASES_AFTER status INCOMPLETE dengan empat kasus; terminal RESULT_AFTER tidak ada. → Log job auditor sendiri memuat 16 PASS, terminal REVIEW_COMPLETE, primary unchanged dan clone remaining 0.

Dampak: Auditor berikutnya dapat menerima bukti parsial atau tidak dapat memeriksa kelulusan dari artefak.

Perbaikan: Jadikan tujuan output eksplisit dan tetap per run/group; hindari mutasi global pada import. Unggahan wajib memeriksa set ID, jumlah, status terminal dan cleanup. Pertahankan artefak lama yang parsial.

Code: `scripts/cp6_be_probe.py:252`, `scripts/cp6_be_probe.py:rework_new_sku`, `scripts/cp6_av_probe.py:32`, `scripts/cp6_au_r1_probe.py:save`. Bukti: `FINDINGS.json` dan original report pointer/hash dalam ledger.

Acceptance:

- Lazy import pada kasus kelima tidak memindahkan output.
- Artefak final 16/16, exact ID set dan seluruh expected/actual serta boundary.
- Hilangkan/ubah satu hasil: gate artefak harus gagal.

### SOL-003 — Pemasang membuang diagnostik PostgreSQL saat pemasangan berhenti di AZ

**S2 / P2; CONFIRMED_INSTALLER_DIAGNOSTIC_LOSS; OPEN.** except di owner installer menyimpan error_type/sqlstate serta proyeksi MAINTENANCE_RUNTIME_FAILED, tanpa message_primary/context/detail dari kegagalan SQL.

Expected: Diagnostik terikat file/hash tersedia secara privat bagi operator/auditor, dengan pesan UI tetap terbatas. Actual: Penyebab pertama tidak dapat ditentukan. Qualification berinstrumen berikutnya memasang 58/58, tetapi tidak mereproduksi atau menjelaskan kegagalan pertama.

Repro: Jalankan FULL_FROM_V2620 dengan owner/work postgres NOSUPERUSER pada clone disposable. → A..AY (51/58) terpasang; AZ berhenti dengan P0001. → Artefak hanya menyatakan MAINTENANCE_RUNTIME_FAILED; nama penjagaan PostgreSQL yang menolak tidak tersimpan.

Dampak: Pemasangan parsial tidak mempunyai informasi cukup untuk membedakan drift, admission/session, atau kondisi lain. Admission tetap tertutup dengan aman.

Perbaikan: Simpan message_primary, context/detail yang aman, constraint/object, file key/hash dan katalog/session diagnostic dalam bukti privat. Telusuri kegagalan pertama tanpa menurunkan penjagaan pemasangan.

Code: `scripts/cp6_readiness_owner_install.py:run except`, `core._public_failure_code`. Bukti: `FINDINGS.json` dan original report pointer/hash dalam ledger.

Acceptance:

- Kesalahan terkontrol meninggalkan nama/kode penjagaan dan identitas file dalam receipt privat.
- Tampilan umum tidak membocorkan kredensial/data sensitif.
- 51 file yang berhasil dan admission state tetap tercatat; tidak direlabel sebagai 58/58.

## Matriks dan inventaris

`INVARIANT_MATRIX.json/.csv`: semua 82 invarian, PASS/FAIL/INCOMPLETE, dasar dan batas. `SCENARIO_MATRIX.json`: seluruh SKN-01..29. `SOURCE_INVENTORY.json` (archive metadata): 456 src files, 310 RPC/from/schema occurrences serta SQL declarations statis; historical/superseded declarations bukan katalog efektif. `evidence/CASE_LEDGER.json` mempertahankan setiap outcome dan pointer original; alias identik dibind per SHA tanpa mengangkat total unique-oracle dari eksekusi ulang atau stand-in kernel.

Modul yang ditelusuri: opening/import/advance/settlement → procurement/invoice/return/transfer/count → cutting/work/WIP/BS/rework/rewash → accessory/laundry/conversion/pocket/recost → sales/draft/reserve/payment/return/refund → payroll → finance/report/obligation/reminder → identity/model/matching/netting/supply/plan/AI → staged retention/cleanup/K4/K6 dan release/rollback. Source requirement berasal dari dua master yang hash-nya dicocokkan dengan acuan dan framework v2, bukan status writer semata. Link jalur: komponen src → public RPC → private facade/Native writer → stock/HPP/AP/AR/cash/journal → readers; catalogue/ACL/body checks dan scoped Native/HTTP/browser evidence menentukan penerimaan, inventory regex tidak menutup runtime.

## Merah yang bukan bug produk

| Bukti awal | Klasifikasi / tindak lanjut |
|---|---|
| CodeQL scan run38560025889 failed source/workflow SHA gate | Scan empat bahasa sukses, qualification38564516689 membind SARIF asli tanpa rescan/oracle weakening; 0 result dengan positive rule/execution controls. |
| CodeQL binding38563769739 401 | Download redirect membawa Authorization lintas origin; alat diperbaiki, original merah disimpan. |
| Sol contract38562774720 4 PASS/1 INCOMPLETE | Exact Decimal formatting −30.00 vs −30 comparator; angka/oracle sama, qualification38564813436 5/5. |
| PR44 proof38564650375 ENOENT | Report output path alat tidak konsisten; qualification38565259193 235/235 dan dua mutant. |
| CP6 release readiness/source guard dan empat legacy browser | Scope era CP6 saja menolak konten/route CP7; original tetap merah. Full-stack prefreeze31 adalah replacement source-specific sesuai D13. |
| Full-stack AR stopped before races / C0 metadata blocked | CP6 BA verifier mengharapkan original owner report, sementara CP7 mempunyai declared overlay. Dua metadata callback dikualifikasi ke exact final CP7; 28 missing AR races dan 25 C0 berjalan, case bodies/amounts unchanged. |
| C0 package38578838814 cleanup failure | 25 C0 cases PASS dan group boundary restored. Satu backend active/null-user menghentikan audit copy restoration; tipe/penyebab backend pertama tidak tersimpan, tidak disahkan sebagai infra race. Qualification38584549739 memakai original25 tanpa rerun + satu timing cleanup control: bounded natural close, no termination, full boundary/catalogue restored. |
| Cleanup38583969555 cancelled | Audit packaging callback namespace diperbaiki dan qualified workflow menggantikannya; cancellation bukan PASS dan tidak diberi kredit kasus. |
| Raw AS/AO/calendar/AR zero-price outcomes | Owner D01/ERP-DEC02 superseding rule, original statuses tetap utuh; replacement proof terpisah. |

## Asal bukti

Eksekusi native independen dengan provider/fixture lama: F03 447, prefreeze31, F01/F02 86, regression and original races, correction/consumer families. Oracle baru literal Sol: lima contract cases dan paired cash capacity control. PR44: independent historical Sol oracle235, PG16 kernel only. Detector poisoning: controlled privileged injection, explicitly not proof of append-only prevention. Archive CP2: original user recovery material, no runtime restore credit. Source/static, shell/DOM, Native kernel, real Auth/HTTP/browser, measurement-scale, reused bootstrap dan owner-deferred work diberi scope masing-masing; jangan menjumlahkannya menjadi kelulusan end-to-end.

## Belum terbukti dan pengecualian owner

- Original CP2 functional restore, actual data cutover/full period, fresh hosted clone/shadow/cutover: tidak dijalankan; tidak diganti dengan synthetic green. Backup/offsite/restore kit CP7C ditunda D13-9a dan tidak dibuka oleh audit ini.
- Exact +1 poison control belum mencakup semua detektor. Dua target Sol mempunyai full before/during/after 29-function outputs. D07 control deletion yang naik +2 tidak dihitung sebagai exact +1.
- GraphQL/alternative API belum diperiksa. HTTP harness mengatur PGRST_DB_SCHEMAS=public. Observasi direct legacy SQL pada role authenticated bukan otomatis bukti bypass browser; juga bukan bukti seluruh alternative surface aman. Official references: https://supabase.com/docs/guides/graphql/security dan https://supabase.com/docs/guides/graphql/functions (14 Okt2026).
- Range-wide auto-distribution dozens pada connected sales belum terbukti/tersedia menurut source dan known writer handoff; per-line A6 browser helper lulus.
- Physical HP/iPad/Safari, real WA recipient/live delivery dan factory SLA/capacity bukan bukti ini. K7 3s tidak tercapai; temporary background acceptance owner dipertahankan. Source inventory tidak berarti setiap 456 file dibaca manual baris demi baris.
- A2 supplier old final-group failures tetap OPEN diterima D13-10; tidak duplikasi sebagai temuan baru. First AZ failure bukan otomatis A2. Semua konfigurasi pending yang sah tetap pending, tidak diisi angka buatan.

## Keputusan owner / rekomendasi

1. Bila bank boleh negatif, writer perlu keputusan eksplisit account/limit/effective policy. Rekomendasi: default aman menolak tanpa kebijakan sah; jangan menafsirkan kewenangan membayar sebagai izin overdraft tanpa batas.
2. Acceptance pemasangan: rekomendasi HOLD sampai first AZ cause/diagnostic dan recovery path dapat diperiksa. Later58/58 tetap evidence positif tersendiri.
3. Kebutuhan range-dozens: user sebelumnya meminta auto-bagi range; rekomendasi implementasi dan real connected browser proof sebelum mengatakan fitur lengkap. D13 retirement per-line tidak membatalkan kebutuhan range.
4. Urutan CP7.5/CP7C/CP8 dan keputusan D11/D13 yang sudah ada tidak ditanya ulang. Perbaikan temuan menjadi kandidat baru untuk audit ulang terpengaruh.

## Ringkasan owner

Kandidat belum boleh ditutup. Bank kosong masih dapat membayar supplier dan menjadi negatif; kontrol bank yang didanai bekerja. Artefak BE tidak lengkap walaupun 16 kasusnya lulus dalam log. Pemasangan pertama berhenti di AZ setelah51 file, sedangkan percobaan berinstrumen berikutnya memasang58; penyebab pertama belum terjelaskan. Core F03, F01/F02, temporal/races dan banyak consumer lulus pada sumber yang dibekukan. K4 menyelesaikan5.000 target lewat penjadwal asli tanpa halaman menghitung. Original CP2 utuh, tetapi pemulihannya belum diuji di runtime. Writer menerima tugas, acceptance dan pointer bukti per akar masalah; produksi tetap belum diizinkan.

## Fokus risiko berikutnya

Kapasitas kas bersama antardokumen dan backdate; penjagaan izin lewat seluruh API yang dipakai; range identity/quantity/HPP melalui correction/recost; detector sensitivity; installation/rollback diagnostics serta source-bound evidence. Tidak ada produk/main/hosted/deployment yang diubah audit ini.

## Paket original

`SOL_CP1_7_NATIVE_ORIGINALS.tar.xz` menyimpan original JSON/SARIF byte-for-byte, 722 artifact/member aliases dan 330 unique byte reports; ini bukan jumlah unique oracle. `PROOF_ARCHIVE_RECEIPT.json` mengikat hash dan identitasnya. Inventaris dan ledger lengkap berada di folder archive `metadata/`; `ALIASES.json` menunjuk original report per SHA. Tidak ada dump/key CP2, screenshot, atau dump database.

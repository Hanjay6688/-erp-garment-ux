# BD — kandidat revisi audit, 28 September 2026 WIB

**Revisi siap diuji ulang auditor. CP6 HOLD; production_go=false, audit_complete=false. Semua temuan tetap terbuka sampai auditor/owner menguji dan menerima.** Kandidat audit lama08065a3 tetap HOLD. Tidak ada hosted migration, perubahan UAT/legacy, merge ke main, atau deployment.

Intake: handoff gabungan auditor507931d, run36341741346. Baseline revisi2c2fd5e sudah memuat BE. Product revision awal e2b33f9; source final0133b16; paket dari capture source tersebut4851cca; rollback78ce98b; locator browser terakhir d493144. Daftar bukti final di bawah harus dibaca bersama batas dan hasil putaran sebelumnya.

Kandidat lengkap untuk audit ulang: **`d493144fb98728731d686bf285445f8eb6e91b3d`**. Commit handoff sesudahnya hanya menambahkan dokumentasi/bukti. Ringkasan mesin, hash, setiap verdict, serta riwayat kegagalan ada di [revision_20260928.json](evidence/cp6-bd/revision_20260928.json). Plan dan perubahan oracle/fixture tercatat di [cp6-bd-revision-plan-20260928.md](cp6-bd-revision-plan-20260928.md).

## Cara menguji jalur yang diminta owner

1. **FREE/WAIVED sah:** Laundry → Harga & tagihan → pilih vendor → Harga vendor. Pilih komponen, `Status harga komponen = Gratis` atau `Tidak ditagih`, waktu berlaku WIB, dan alasan; simpan versi. Vendor memakai cara harga Komponen. Pada Kirim dengan harga, pilih batch dan isi qty kirim serta cakupan jasa per ukuran. Harga0 adalah snapshot dari versi FREE/WAIVED itu. Aksi master memerlukan OWNER/ADMIN +`master.partner.manage`; angka kosong tetap UNKNOWN. KNOWN0, FREE positif, alasan kosong, dan role tanpa hak ditolak.
2. **UNKNOWN menjadi waiver:** Harga belum diketahui → pilih status Gratis/Tidak ditagih pada baris yang belum diketahui → isi alasan → Isi harga. Memerlukan OWNER/ADMIN +`finance.hpp.manage`. Alokasi mengikuti coverage tersimpan, resync estimasi/HPP, replay satu efek. Harga yang sudah diketahui tidak bisa ditimpa melalui aksi ini.
3. **Paket + extra:** pilih paket pada Kirim dengan harga. Komponen yang sudah termasuk tercantum tanpa input extra. Isi coverage per ukuran pada komponen di luar paket dan alasan tambahan. `LAU-DEC03.extra=ALLOWED` wajib; backend menolak included component/duplikat/ukuran asing/qty berlebih/cakupan ambigu.
4. **Invoice/source lewat batas lama:** Invoice vendor menyediakan Muat invoice berikutnya (50 per halaman), Muat penerimaan berikutnya (200), serta pencarian pada daftar yang sudah dimuat. Tidak mengklaim pencarian server atas data yang belum dimuat. Form draf tetap ada saat memuat halaman; sumber terpilih tetap tersedia ketika teks pencarian berubah. Posting selalu memeriksa ulang kapasitas dan versi.
5. **Tarif celup:** pada runtime BD+BE, Invoice vendor → Jasa celup ulang → isi tarif + alasan → Isi tarif celup. UI mengarah ke `erp_save_product_conversion_action_v1`, dengan validator respons BE dan izin konversi + keuangan. BD-only tidak menampilkan jasa BE yang tidak tersedia.

## Kontrak yang berubah

| Bagian | Kontrak revisi |
|---|---|
| Komponen/extra | `coverage:[{size_id,qty}]`; jumlah sama dengan `covered_qty`, tiap ukuran milik kiriman dan tidak berlebih. Multi-size parsial wajib eksplisit. Full coverage lama dan single-size parsial lama tetap tidak ambigu. Snapshot menyimpan qty per sumber ukuran. |
| Status harga | Komponen master dan penyelesaian charge menerima `KNOWN`, `UNKNOWN`, `FREE`, `WAIVED` sesuai aksi. FREE/WAIVED wajib nominal teks`0.00` +alasan; UNKNOWN/null tetap terpisah. Tidak memperluas semua tarif proses/paket menjadi nol. |
| Respons kirim | `estimated_cost` mengambil total exact snapshot; belum lengkap menghasilkan null. Average rate tetap hanya representasi per-PCS. |
| Invoice besar | Pembagi diskon memakai bobot numeric, bukan sen yang dicast integer32. Nominal18,2, kebijakan diskon, kapasitas, ledger dan atomisitas tetap berlaku. |
| Replay | Otorisasi aksi sekarang diperiksa sebelum mengembalikan cache, juga setelah menunggu request lock. Aktor/payload/action tetap diikat. |
| Reader paging | Filteropsional`invoice_after`,`receipt_after`,`page_as_of`; cursor UUID mengacu baris vendor yang sama. Urutan keyset waktu+ID, cutoff menyisihkan insert baru. Balasan`pagination:{as_of,invoice_next,receipt_next}`. Client merge menurut ID; kehilangan hak nominal membuang cache lama. |

Contoh audit X-01: kirim7+6PCS; wash13×4321.09=56174.17; finish5×678.91=3394.55 hanya pada ukuran kedua. Laundry ukuran pertama30247.63, kedua29321.09, total59568.72. Coverage adalah qty aggregate jasa pada source batch/size; bukan identitas serial per PCS. Penerimaan parsial membagi biaya ukuran penerimanya dengan residual terakhir. Harga UNKNOWN memakai coverage yang sama ketika diselesaikan.

## Kandidat dan pemasangan untuk audit ulang

- Branch writer `claude/new-session-deapao`; source produk final `0133b160af704f1620a19e95956594223ca698ee`.
- SHA256 BD dev: `f480f8dd7dc2620e19994e328b971ef159ba81dca1b8272ae42b59e0d370f947`.
- SHA256 BE dev: `c4f91fd690e3308122d14b5fdb8d2c30f59bb7809136e63824109c51c462746e`.
- Paket AC..BE29 berkas dibangun dari capture run36345520698, blob SHA256 `bc8d5bd910398c0219918b9b09b86c2265fe943944167bed1d2b58fe348090b9`, lalu dipasang pada4851cca. AC..BC tetap byte-identical dengan paket baseline sebelum revisi; BD dan BE perlu pin baru karena BD adalah predecessor BE.
- Rollback final `78ce98bcf4cd7bb5bea349572c26c8c78c14c136`, capture run36346155950, SHA256 `84619f1558db3a43adec67154af498d9435a65541bc6e394b69e3690bf6c4472`. Sesudah commit paket hanya file pembuktian/rollback/dokumentasi yang berubah; produk yang diuji tetap sama.
- Gunakan disposable baru dan harness chain yang dipin atau applier paket. BD tetap memakai marker keluarga unreleased yang sama; jangan menimpa dev SQL baru pada database yang sudah mempunyai marker kandidat lama. Ini bukan migration upgrade hosted dan bukan instruksi produksi.
- Rollback paket adalah **pre-use**: hanya sebelum ada transaksi bisnis setelah pemasangan. Sesudah pemakaian, rollback wajib ditolak tanpa perubahan. Jangan menganggap rollback menghapus transaksi bisnis pengguna.

## Bukti writer dan batasnya

Belum merupakan penerimaan independen. HP fisik dan Safari belum diuji. Pengujian penjualan pada fixture native tidak menjadi klaim browser penjualan.

- Lokal: official `npm run build` PASS,563 unit tests PASS,`npm run test:security` PASS. Boundary ownership menambah tepat satu pasangan file/RPC untuk tarif celup; guard tidak dilonggarkan.
- e2b33f9 /36344158914:35 kasus BD existing PASS,4 dari6 revisi PASS. Dua assertion writer tentang HPP pecahan diperbaiki, dengan sumber expected tercatat dalam plan; run awal tetap FAIL. Reader232 berkas diterima parser tanpa penolakan.
- e2b33f9 /36344158927: BE T1 before/after PASS. /36344158887:9 race BE,2 HTTP,6 browser BE semuanya PASS, termasuk tarif celup mobile. Ini enam browser total, termasuk celup.
- T3 lama /36344158905: ditolak karena source BD berbeda dari paket yang dipasang. Bukan paket revisi final.
- Source final0133b16 /36345520728:41/41 kasus BD PASS;232 berkas reader (14 BD,205 import,13 Laundry) diterima parser tanpa penolakan. Enam kasus baru mencakup coverage+partial receipt+QC/HPP, UNKNOWN completion, FREE/WAIVED, invoice besar, auth-before-replay, dan paging.
- 0133b16 /36345520659:6 kasus native revisi pada BD+BE,18 race dua sesi,6 Auth/HTTP PASS; browser9 PASS/6 INCOMPLETE karena locator cakupan lama dan read-back fixture privat. Perbaikan4851cca tidak menambah grant produksi atau melonggarkan verdict; semua kegagalan lama tetap tercatat.
- Nominal invoice end-to-end:21474836.47,21474836.48,28123456.78, termasuk diskon1.23 pada invoice dua baris dan AP/jurnal seimbang. Batas9999999999999999.99 hanya diuji pada helper pembagian, bukan seluruh journal end-to-end.
- 4851cca /36346155951: native6, race18, HTTP6 PASS; browser14 PASS/1 FAIL. Kelima browser baru PASS. T36 gagal pada pencarian teks sel exact karena alasan harga kini ikut ditampilkan. Job hijau hanya berarti eksperimen selesai; belum semua kasus lolos. Locator d493144 harus menemukan sel status UNKNOWN yang terlihat pada baris SPR yang sama sebelum pengisian; total dan accrual tetap13000 setelah diisi. Kegagalan ini tetap tersimpan.

| Bukti final | Run / job | Hasil per kasus/gate |
|---|---|---|
| Browser + native/Auth BD+BE | 36346789834 /108697391554 |6/6 native,18/18 race,6/6 Auth/HTTP,15/15 browser PASS;45 verdict diperiksa, nol FAIL/INCOMPLETE; console_errors0, Auth dipulihkan, primary tidak berubah, clone0 |
| T2 temporal/master | 36346155941 /108695591170 | AT16+4 race, AU15+6 race PASS; primary tidak berubah |
| T2 AR | 36346155941 /108695591155 | Sequential145 PASS+1 superseded INCOMPLETE; pengganti BC PASS;28/28 race PASS |
| T2 regresi | 36346155941 /108695591005 |422/422 status per kasus identik dengan BE sebelum revisi (36334558842 /108663058496) dan putaran sebelumnya; delta kosong. BUSINESS230/IMPORTS31/VALUES65 tetap sama dengan AU; C0 25/25 PASS |
| Paket install/compare/restore | 36346155942 /108695591160,108695591193 |29/29; ALL_STAGES_INSTALLED; pins equal=true,differ=[]; empat gate true |
| Browser paket | 36346155942 /108695591053 |10/10 PASS; login, anonymous refusal, lost reply/replay, stok/HPP per brand, inverse; console_errors0 |
| Rollback | 36346508510 /108696596257 |143/143 PASS; dua cycle29 keluarga, reinstall identik, urutan/admission refusal,29 post-use refusal; primary tidak berubah |
| CodeQL security-extended | 36346789851 /108697391515,108697391662,108697391722,108697391728 | JS/TS,Actions,C/C++,Python PASS; masing-masing result_count0; SARIF artifacts, bukan upload Code Scanning |

T2 AR juga dibandingkan dengan BE sebelum revisi:175 identitas kasus (174 asli ditambah1 pengganti BC), status seluruhnya sama. T2 raw tetap `DISPOSITION_REQUIRED`: BUSINESS179 PASS+39 CONTROL_PASS+12 DATE_POLICY_REVIEW_REQUIRED; NEW_CASES25 PASS+8 COUNTEREXAMPLE+1 INCOMPLETE; AO8 PASS+4 INCOMPLETE. Oracle AS yang disetujui8/8 MATCH, oracle tambahan5 PASS, kalender12 MATCH, C0 25 PASS. Hasil frozen tidak diubah menjadi PASS dan kalender12 tetap HOLD.

Advisor raw tetap `REVIEW_REQUIRED`:73 baseline menjadi205,132 tambahan semuanya INFO `rls_enabled_no_policy` pada schema privat/capsule, tanpa penghapusan. Ini jenis yang sudah diterima gate existing dan dicatat pada handoff BE; bukan zero-advisory. Restore `RESTORED_SAME_MEANING`:data identik, hasil engine sama; exit1 berisi19 galat pg_cron saja pada clone non-`postgres`, unexplained kosong. Restore cron produksi tidak diklaim.

## Pemetaan temuan untuk auditor

Semua baris berikut berstatus **revisi disediakan, belum ditutup auditor**.

| Temuan | Bukti yang dapat diuji ulang |
|---|---|
| X-01 salah alokasi | `REV:X01_EXPLICIT_SIZE_COVERAGE_AND_RESPONSE`, `REV:X01_UNKNOWN_COMPLETION_PRESERVES_COVERAGE`; coverage ukuran, partial receipt, QC/HPP, dan harga historis setelah master berubah |
| X-02 invoice besar | `REV:X02_MONEY_OVER_INT32`; tiga batas audit, diskon dua baris, AP dan jurnal seimbang, helper batas atas dibedakan |
| X-03 nominal saat replay | `REV:X03_AUTH_BEFORE_REPLAY`, `BD_REV_HTTP:REVOKED_PERMISSION_REPLAY_NO_MONEY`; revoke/fresh/replay ditolak, restore satu efek |
| X-04 extra paket | `BD_REV_BROWSER:PACKAGE_EXTRA_SIZE_DESKTOP/MOBILE`; hanya5 PCS ukuran kedua, qty berlebih dan alasan kosong ditolak UI, backend menjaga policy dan included component |
| X-05 batas50/200 | `REV:X05_PAGES_55_INVOICES_201_SOURCES`, `BD_REV_BROWSER:PAGING_PRESERVES_EDIT_MOBILE`;55 invoice,201 sumber unik, form tidak hilang, source halaman lanjut dipilih dan disimpan |
| X-06 tarif celup | `BE_BROWSER:REDYE_SKU_UNKNOWN_THEN_PRICE_MOBILE`; facade BE, izin saat replay, receipt/FG dan tarif |
| X-07 build resmi | `npm run build` dan security PASS; masalah enam ownership BE sudah diperbaiki di baseline2c2fd5e, revisi ini menambah satu pasangan RPC yang benar |
| OWN-01 respons lebih0.01 | Respons exact59568.72 pada native dan browser, sama dengan snapshot; pembukuan yang sudah benar dipertahankan |
| OWN-02 FREE/WAIVED | `REV:OWN02_FREE_WAIVED_LEGAL_PATH`, `BD_REV_BROWSER:FREE_MASTER_THEN_PHYSICAL_DESKTOP`, `BD_REV_BROWSER:WAIVED_MASTER_THEN_PHYSICAL_MOBILE`; versi0+alasan dengan izin sah, beda dari UNKNOWN, physical quantity13PCS dan known total0.00 |

Disposisi historis T2 (tanggal dan BC free policy) tetap tercatat pada `docs/cp6-be-writer-handoff-20260927.md`; tidak mengubah frozen oracle menjadi PASS. Kutipan angka skenario auditor tidak dengan sendirinya menjadi hasil uji writer; lihat matriks per kasus/run.

Single writer tetap `claude/new-session-deapao`. Remote diperiksa sebelum update ref, update tanpa force. Tidak ada klaim dapat mengamati editor yang belum push.

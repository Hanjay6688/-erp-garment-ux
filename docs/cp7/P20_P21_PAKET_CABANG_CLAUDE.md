# Paket P20/P21 — bagian cabang Claude (P08 fisik kain, P18 pengingat kain)

Tambahan writer GPT 8 Okt: paket sumber kandidat gabungan, manifest seluruh
ERP dan kompilasi F03/full-staged ada di
`audit-candidate/staged-5000-20261008/README.md`. Source `59d63e46` sudah
lulus kualifikasi writer: 15/15 workflow, 35/35 job, seluruh 5.000 target
staged pada 1/30/100 hari dan semua halaman terverifikasi (rincian 14.5).
Latihan P21 saat ini memasang F03, yang tidak memuat
`cp7_analysis_stage`; pemasangan keluarga staged bukan otomatis receipt P21
paket penuh. USE ditahan lalu di-rollback, bukan committed-use restore proof.
Status historis di bawah tetap dibaca sesuai SHA/cakupannya.

Catatan integrasi6 Oktober2026: kandidat cabang2ae1db92 dan bukti lama di bawah tetap historis. Build UX merah3c7cb2cf sudah diperbaiki; source0bd kini lulus1,558 tes/165 file. Bukti gabungan aktual, Native/regresi yang sudah dibaca serta pekerjaan P18/P19/P20/P21 yang masih terbuka ada di `p19/P19_UTF8_QUALIFICATION_CHECKPOINT_20261006.md`. Belum ada pembekuan kandidat audit atau pemasangan nyata.

Status: draf persiapan. Belum ada audit independen dan belum ada pemasangan. `independent_acceptance=false`, `production_go=false`. CP6 ditutup sesuai cakupannya; HOLD operasional/pemasangan CP6 tetap berlaku (GBD-03 dan lima keputusan D11 sudah disetujui dan tidak dibuka ulang; delapan konfigurasi nyata masih pending). Audit independen CP7 dan `production_go=false` terpisah dari status CP6. Dokumen ini melengkapi `docs/AUDIT_PANDUAN_PRO_MAX.md` dan handoff (§9, §10). Bukan pengganti paket kandidat gabungan milik GPT.

## 1. Kandidat dan bukti

| Lingkup | Suite | Bukti CI terakhir | Catatan |
|---|---|---|---|
| P08 fisik kain | NATIVE_FABRIC_PHYSICAL (21) | PASS 21/21 run 37387866413 (b292ae4c) | Kegagalan pertama 37357315101, 37360628807, 37366015511 dan 37374383973 tetap tercatat. |
| P08 penerus resep | NATIVE_FABRIC_RECIPE (13) | PASS 13/13 run 37387866413 (b292ae4c) | ID dan jumlah tetap. |
| Regresi analisis | analysis152, plan39 | PASS run 37366015511 (7b89f767) | Sumber produk SQL sama dengan head berikutnya. |
| Rantai pengingat | attention284 | PASS 284/284 run 37387866413 (b292ae4c) | Termasuk SQL pengingat `FABRIC_NEED`. |
| P18 pengingat kain | CP7_P18_FABRIC_RULE (11) | PASS run 37374231262 (6f3216e2) | 7 DB, 1 race, 1 Auth/HTTP, 2 browser. |
| P18 regresi | rule-lifecycle16, p18-e01-9 | PASS run 37366015710 (7b89f767) | |
| Shell + CodeQL | Shell S0 (28 kontrol kain), CodeQL | PASS run 37387866583 / 37387866362 (b292ae4c) | |

Kandidat untuk audit ditetapkan setelah seluruh baris di atas PASS pada satu head. Head a4ebb6a8 sudah memenuhi ini: kedelapan suite Native PASS dengan jumlah kasus penuh, ditambah Shell S0, CodeQL dan receipt-correction (run 37404829353, 37404835115, 37404829371, 37404829367, 37404829416). Perubahan `condition_rows` sesudahnya juga sudah PASS penuh di 882fc40a/2ae1db92 (run 37406898697 dan 37408720092). Hash sumber pengingat sama di kedua run, dan 2ae1db92 hanya menambah dokumen. **Kandidat audit cabang Claude saat ini: 2ae1db92** (sumber produk sama dengan 882fc40a). Hasil LOCAL_PG16_DEV tidak dihitung sebagai bukti.

## 2. Objek database baru atau berubah

| Objek | Jenis | Catatan untuk auditor |
|---|---|---|
| `cp7_fabric_native.material_hash/physical_source/index/recipe_state/plan` | fungsi baru (pemilik `cp7_capture`, `search_path=''`) | Dihitung sekali per analisis; masuk tanda tangan mesin analisis. |
| `cp7_fabric_native.source` → `cp7.fabric-source.v2`; `needs(c,r,a,plan)` | fungsi berubah | Blok `physical` ikut sidik jari analisis (tanpa `captured_at`). |
| `cp7_plan_native.apply_own_drafts` | tabel baru (pemilik `cp7_plan_writer`, RLS + kebijakan `false`) | Hanya dipakai di dalam satu transaksi apply. Baris disisipkan dan dihapus sebelum commit, terikat `txid`. Verifier menuntut tabel kosong. |
| `cp7_plan_native.apply` | fungsi berubah (milik GPT) | Sisip penanda → preflight ulang → hapus penanda. |
| `cp7_reminder_native.rule_policies` | cek `rule_id` dan lingkup TARGET berubah | Menambah `FABRIC_NEED`. CP7 belum terpasang di mana pun; bila kelak sudah terpasang, perubahan cek ini perlu `ALTER TABLE … DROP/ADD CONSTRAINT`. |
| `policy_validate`, `policy_scope_access`, `policy_workspace`, `policy-history`, `local-sink`, `condition_domain/_access/_rows/_source` | fungsi berubah (milik GPT) | Aturan kelima, domain `FABRIC`, cakupan `fabric`. |
| `cp7_fabric_native.plan/needs/recipe_state` (P19) | fungsi berubah, signature tetap | Hitungan sekali per bahan/draf dan baca path tanpa salinan. Keluaran `plan` datar (kunci indeks di tingkat atas), konsumennya hanya `needs`. Kesetaraan lokal 3.300 set data. |
| `cp7_reminder_native.condition_rows` (P19) | fungsi berubah (milik GPT), signature tetap | Hash analisis dibaca sekali, label dan dokumen piutang lewat peta kunci (kecocokan pertama), larik `jsonb[]`. Kesetaraan lokal 3.000 set data. |

Hak baru untuk `cp7_capture`:
- **SELECT kolom tertentu saja, tanpa harga atau biaya:**
  - `erp.material_rolls(id,material_id,status)`
  - `erp.material_stock_movements(material_id,roll_id,location_id,qty_signed,physical_at)`
  - `erp.locations(id,location_type,is_active)`
  - `erp.bb_purchase_commitments_v1(id,po_number,location_id,expected_date)`
  - `erp.bb_purchase_commitment_lines_v1(id,commitment_id,material_id,line_number)`
  - `cp7_plan_native.intents(id,target_key,cutting_group_id)`
  - `cp7_plan_native.apply_own_drafts(cutting_group_id,txid)`
- **EXECUTE** `erp.bb_commitment_line_remaining_v1(uuid,uuid)`.

Tidak ada role, RPC publik, atau hak tulis bisnis baru.

## 3. Titik audit prioritas (risiko angka salah)

1. **Penanda apply.**
   - Pastikan tidak ada jalur yang bisa menyembunyikan draf di luar transaksi apply yang sedang berjalan: siapa yang bisa menulis tabel, perbandingan `txid`, rollback saat error, dan pemanggilan `physical_source` dari transaksi lain.
   - Cek juga akibat yang disengaja: setelah apply ter-commit, Original lama menjadi basi.
2. **Batas sumber fisik.**
   - Roll ikut hanya bila jumlah per lokasi ≠ 0, atau bila roll dipakai draf belum diposting. Periksa stok negatif, gerakan dengan bahan berbeda, dan jumlah yang saling meniadakan antar lokasi.
   - Batas PO berlaku setelah memilih baris terbuka.
   - Melewati batas harus menolak; tidak boleh ada pemotongan diam-diam (kontrol Shell 27 dan 28).
3. **Pembagian stok bebas dan PO.**
   - Angka hanya keluar bila himpunan pemakai lengkap dan pembagiannya unik. PO dihitung sekali, hanya ke gudang bahan aktif, dan hanya bila tepat waktu menurut akhir hari WIB.
   - Draf manual atau stok tidak konsisten → UNKNOWN.
4. **Terpasang = 0.**
   - Hanya untuk PCS yang terbukti belum dipotong.
   - WIP sejenis yang identitasnya belum pasti → UNKNOWN dengan batas atas.
   - Setelah POST potong nyata, celah rencana menjadi UNKNOWN; oracle penerus memastikan pengeluaran terhitung sekali.
5. **Identitas resep.**
   - `material_hash` hanya memakai field master. Perubahan nama, satuan, jenis, status aktif, atau kategori harus membatalkan review.
   - Penulisan ulang cache stok atau biaya tidak membatalkan review.
6. **`FABRIC_NEED`.**
   - Nilai adalah salinan persis fakta bersama. Alasan wajib cocok dengan keadaan.
   - Nol yang masih asumsi tidak pernah selesai. UNKNOWN tidak membuka episode.
   - Satuan ambang dibandingkan persis. Huruf kecil diterima hanya untuk `FABRIC_NEED`; aturan lama tidak berubah.
7. **Laporan.** Baris kebutuhan bahan mengutip sumber keempat fakta tanpa duplikat. Baris tanpa sumber fisik tidak berubah teksnya.
8. **Penerima frontend.** Angka fisik kain hanya diterima dalam batas kernel: gross − terpasang − sisa layak ≥ tambahan dari luar ≥ 0, dengan asumsi resep yang benar.
9. **Perubahan P19 (kecepatan, hasil wajib sama).**
   - `plan`: periksa agregasi per bahan (`free`, `bad`, `manual`, `incoming`, `hash`), termasuk perilaku saat roll, sel atau baris PO ganda.
   - Pemeriksaan draf: setiap draf unik diperiksa sekali lewat hash join, dan join ke sel memakai `is not distinct from` untuk lokasi kosong.
   - `condition_rows`: aturan "kecocokan pertama" pada label dan dokumen piutang (`order by … desc` di `jsonb_object_agg`).
   - Pastikan tidak ada jalur yang membuat angka berbeda dari versi lama. Skrip pembanding lama-lawan-baru ada di `scripts/cp7_p19_equivalence.py`, dengan kontrol negatif yang terbukti menangkap beda kecil.

## 4. Catatan pemasangan (P21) dan rollback

- **Belum ada pemasangan hosted.** Semua objek di atas masuk bundel CP7 yang dipasang oleh harness T3 dari basis representatif. Uji pemasangan ulang, pemulihan, dan backup/restore dijalankan oleh probe (cek `cp6_restored`, `advisor_gate`, gerbang backup).
- **Rollback bundel CP7.** Probe melakukan `drop owned by <role> cascade` dan `drop role` untuk role CP7, sehingga tabel penanda ikut terhapus. Definisi fungsi pendahulu dikembalikan dari salinan aslinya, dan pemeriksaan ACL fungsi pendahulu (`F03_UNDECLARED_ACL_DELTA`) memastikan hanya hak yang dideklarasikan yang berubah.
- **Paket rilis dan siklus rollback.** Bila kelak dibuat paket rilis CP7 (setara T3 CP6), objek di bagian 2 harus masuk daftar siklus pasang → rollback → pasang ulang. Data runtime CP7 (resep, kebijakan, episode, klaim lokal) termasuk data yang diputuskan pemilik soal disimpan atau dibuang saat rollback.

## 5. Yang masih terbuka

- **Uji beban P19** untuk sumber fisik dan sumber kondisi pengingat. Saat ini hanya ada batas desain dan bukti penolakan.
- **Build UX merah bawaan** dari commit GPT 3c7cb2cf. Usulan patch ada di handoff §9.4; keputusan ada di GPT.
- **Kebijakan pemilik (dua daftar terpisah).**
  - **13 kebijakan CP6 (D11, aksesori dan laundry):** 5 sudah diputuskan owner pada 26 Sep 2026: no. 4 ACC-DEC05, no. 6 ACC-DEC07, no. 11 LAU-DEC04, no. 12 LAU-DEC05 (tidak diaktifkan) dan no. 13 LAU-DEC06. Keputusan itu sudah dipakai sebagai oracle uji. Delapan sisanya tinggal dipilih owner di aplikasi, sebagian besar berupa pilihan akun atau kategori. Rinciannya ada di `docs/cp6-d11-kebijakan-dan-gbd03.md`.
  - **Pengaturan CP7, di luar daftar 13 itu:** ambang pengingat per aturan (termasuk `FABRIC_NEED`) dan kemampuan/kelipatan produksi masih PENDING_POLICY_VALUE dan diisi owner di aplikasi.
  - Belum ada pemasangan ke data nyata. Karena itu, keputusan yang sudah ada belum terpasang sebagai nilai di database mana pun selain fixture uji.

## 6. Tambahan 6 Okt 2026 sore: P18 siklus penuh, Bayar supplier, latihan P21

Basis cabang: fast-forward ke `cp7/integration` `ab6f1f97` (checkpoint UTF8 GPT), lalu commit cabang ini. Rinciannya ada di `p18/P18_FULL_CYCLE.md`, `SUPPLIER_PAYMENT_CREATE_HANDOFF.md` dan handoff §12.

### 6.1 Objek database baru

| Objek | Jenis | Catatan untuk auditor |
|---|---|---|
| Skema `cp7_supplier_payment_create` (`requests`, `context`) | skema dan tabel baru (pemilik `cp7_invoice_read`/`cp7_invoice_write`, RLS + kebijakan `false`) | `context` hanya hidup di dalam satu transaksi dan wajib kosong sesudah commit. |
| `access_now`, `validate` (invoker, pemilik `cp7_invoice_read`); `review`, `workspace`, `apply` (definer `postgres`, `TimeZone=UTC`); `command` (invoker, pemilik `cp7_invoice_write`) | fungsi baru | `apply` adalah satu-satunya penulis: baris DRAFT, lalu Native `erp.post_supplier_payment` yang tidak diubah. |
| `public.erp_cp7_get_supplier_payment_create_v1(jsonb)`, `public.erp_cp7_create_supplier_payment_v1(jsonb,uuid)` | RPC publik baru, hanya `authenticated` | Hak: OWNER/ADMIN + `finance.ap.pay` + `finance.ap.view` + `warehouse.procurement.view`. |

Tidak ada role baru, perubahan definisi Native, atau hak DML ERP untuk role App.

### 6.2 Titik audit prioritas

1. **Bayar dua kali.** Coba dari dua tab, dua sesi, replay, atau UUID sama dengan isi berbeda. Token tinjauan mencakup penerimaan, jawaban hutang Native, dan semua baris pembayaran. Hasil yang diharapkan: satu pembayaran, dan yang lain `STALE_REVIEW` atau `REQUEST_CHANGED`.
2. **Melebihi sisa hutang.** Termasuk ketika kredit retur, koreksi harga, atau pembalikan pembayaran terjadi di antara tinjauan dan sahkan.
3. **Tanggal.**
   - Masa depan ditolak.
   - Sebelum barang datang ditolak; itu alur uang muka.
   - Periode tertutup mengikuti Native `post_journal`.
4. **Hak berubah saat menunggu kunci.** Harus ditolak sebelum ada efek.
5. **P18:** di setiap batas, buku besar sama dengan buku pembantu. Periksa apakah ada akun yang berubah tanpa dijelaskan subledger, dan apakah laporan posisi keuangan cocok di awal, sesudah produksi, dan di akhir.
6. **Temuan bawaan hosted (bukan bagian perintah baru).** Role `authenticated` punya USAGE pada skema `erp` (dipertahankan G-01) dan pada klon setara hosted bisa menyisipkan baris DRAFT `erp.supplier_payments` secara langsung. Native `erp.post_supplier_payment` bisa dieksekusi `authenticated` dan hanya memeriksa peran OWNER/ADMIN/STAFF, tidak memeriksa `finance.ap.pay`. PostgREST hanya membuka `public`, jadi ini bukan rute aplikasi. Hasil pengamatan lengkapnya ada di laporan kasus `CURRENT_ACCESS`. Keputusan menutup jalur ini ada di GPT dan owner.

### 6.3 Latihan P21

`scripts/cp7_p21_rehearsal_probe.py` (workflow `claude-p21-rehearsal.yml`) berjalan hanya di klon sekali pakai:

1. Pasang tumpukan F03 gabungan.
2. Rollback sebelum dipakai dengan bukti pemulihan persis.
3. Pasang ulang; katalog terpasang harus identik.
4. Satu penulisan CP7 nyata.
5. Rollback sesudah dipakai harus ditolak.
6. Pemulihan oleh harness.

Ini latihan, bukan receipt P21. P21 tetap butuh kandidat yang diterima P20 dan T2 pada hasil pasang.

**Hasil latihan P21.** Penerus 0fcc04ac (run 37492771185) PASS:
- pasang dan pasang ulang menghasilkan katalog identik `e75968e2…`;
- rollback sebelum dipakai memulihkan keadaan persis;
- rollback sesudah dipakai ditolak;
- pemulihan berhasil.

Run pertama 15baeb3e INCOMPLETE di langkah pakai karena fixture probe; buktinya disimpan.

## 7. Tambahan 6 Okt 2026 malam: P19 kernel, hitung latar belakang, transport segmen

Rincian: `p19/P19_KERNEL_JOB_TRANSPORT_CLAUDE.md` dan handoff §13.

### 7.1 Objek database baru

| Objek | Jenis | Catatan untuk auditor |
|---|---|---|
| Skema `cp7_analysis_jobs` (`jobs`, `documents`, `segments`) | skema dan tabel baru (pemilik `cp7_capture`, RLS + kebijakan `false`) | `documents` dan `segments` imutabel (trigger `cp7_private.immutable_run`). Indeks `jobs(run_id)`. |
| `compute_key`, `worker_active`, `status`, `original`, `store`, `request`, `run`, `get`, `manifest`, `segment` | fungsi invoker baru (pemilik `cp7_capture`, `search_path=''`, `TimeZone=UTC`) | `run` memakai kunci per-UUID yang sama dengan capture biasa. Pembatalan statement ditangkap, dan hanya status FAILED yang di-commit. |
| `public.erp_cp7_{request,run,get}_analysis_job_v1`, `public.erp_cp7_read_analysis_{manifest,segment}_v1` | RPC publik baru (definer `cp7_capture`, hanya `authenticated`) | `manifest` = pemeriksaan setara `serve` sekali. `segment` mensyaratkan epoch akses yang sama dan run milik aktor. |

### 7.2 Titik audit prioritas

1. **Kesetaraan kernel.** Pastikan peta per target, per posisi, dan per sumber memberi hasil yang sama dengan pencarian lama untuk:
   - edge ganda dengan match JSON null atau tanpa match;
   - ETA ganda, hilang, atau tanpa `result`;
   - input null;
   - target null.

   Ujinya `f05-kernel-maps` dan analysis152.
2. **Satu komputasi per UUID.** Dua worker, ditambah capture biasa dengan UUID yang sama, harus menghasilkan tepat satu Original.
3. **Batas tidak dinaikkan.** Job memakai batas statement yang ada. Pembatalan meninggalkan hanya status FAILED (tanpa run atau dokumen), dan attempt berikutnya memakai UUID yang sama.
4. **Otoritas per segmen.** Epoch akses yang berubah, aktor lain, akses keuangan yang dicabut (harus sama dengan `serve`), dan source basi (harus sama dengan `serve`) semuanya harus tertangani.
5. **Klien.** Pengecekan code point per segmen, sha256 per segmen dan seluruh dokumen, batas dokumen 64 MB (teknis, bukan kebijakan), dan validator lengkap yang tidak dilonggarkan.

### 7.3 Pindaian jalur langsung lama (pengamatan P20)

`scripts/cp7_p20_direct_path_scan.py` dijalankan baca-saja di dalam latihan P21. Hasilnya:
- fungsi `erp` yang bisa dieksekusi `authenticated`/`anon`;
- penulis definer tanpa pemeriksaan `has_permission`;
- penulis yang hanya memakai penjaga peran;
- tabel `erp` dengan DML untuk `authenticated`;
- konfigurasi skema PostgREST.

Klasifikasinya heuristik teks dan bukan temuan yang diterima. Setiap kandidat perlu dibaca isinya oleh auditor P20.

**Hasil pindaian pertama** (latihan P21 di `7d9041fa`, run 37520305963, job 112463706478, PASS). Ringkasannya ada di `evidence/p20-direct-path-scan-7d9041fa/SCAN_SUMMARY.json`. Ini pengamatan heuristik, bukan temuan yang diterima.

| Pengamatan | Jumlah |
|---|---|
| Fungsi `erp` | 940 |
| Bisa dieksekusi `authenticated` | 160 |
| Bisa dieksekusi `anon` (semuanya fungsi trigger penjaga) | 8 |
| Penulis definer yang bisa dieksekusi `authenticated`, tanpa `has_permission` di badan fungsinya (semuanya hanya memakai penjaga peran seperti `require_internal`) | 82 |
| Tabel `erp` dengan DML untuk `authenticated` | 55 |
| Tabel tanpa RLS di antara 55 itu | 0 |
| Tabel yang bisa diakses `anon` | 0 |

Keadaan role: `authenticated` punya USAGE pada skema `erp` (G-01), sedangkan `anon` tidak. Role `authenticator` memakai `statement_timeout=8s` dan `lock_timeout=8s`.

Ke-82 penulis itu antara lain posting dan pembalikan pembayaran (`post_supplier_payment`, `post_vendor_payment`, `post_sales_payment`, `post_payroll_payment`, `reverse_*`), `approve_payroll`, `close_accounting_through`/`reopen_accounting_through`, `process_cost_recalc_queue`, impor migrasi, dan simpan draf `*_v2`.

**Yang perlu dibaca auditor P20:**
1. Apakah pemeriksaan hak terjadi di fungsi pembantu yang dipanggil, sehingga heuristik ini tidak menangkapnya.
2. Kebijakan RLS pada ke-55 tabel itu.
3. Apakah ada endpoint selain PostgREST `public` yang bisa mencapai skema `erp` untuk `authenticated`. Contohnya GraphQL (`graphql_public`/pg_graphql) atau koneksi database langsung, dan ini harus diperiksa pada konfigurasi hosted.

Pembayaran supplier lewat jalur langsung sudah terbukti pada kasus `CURRENT_ACCESS` (lihat `SUPPLIER_PAYMENT_CREATE_HANDOFF.md`). Menutupnya mengubah ACL atau definisi Native di hosted, jadi itu keputusan owner/GPT.

## 8. Tambahan 7 Okt 2026: pemeriksaan mandiri rumus/keuangan dan P19 bagian 2

Rinciannya ada di `SELF_CHECK_FORMULAS_20261006.md`; nomor run CI per commit dicatat di §6 dokumen itu. Ini persiapan audit, bukan audit independen.

### 8.1 Objek yang berubah

Tidak ada role, RPC publik, tabel, atau hak baru. Semua perubahan ada di badan fungsi yang sudah ada (signature tetap).

| Berkas SQL | Fungsi | Perubahan perilaku |
|---|---|---|
| `finance/analysis.sql` | analisis keuangan | Pertumbuhan dan selisih margin `null` bila basis pendapatan ≤ 0; `formula_version` → `GROWTH_POSITIVE_BASE_AND_GROSS_MARGIN_PP_V2` |
| `procurement/correction.sql` | `restate_all`, penghalang kredit | Hanya pembalikan yang dibuat perintah ini yang dipindah tanggalnya; kredit supplier dianggap aktif bila netto ≠ 0 |
| `invoices/payment-correction.sql` | koreksi pembayaran supplier | Tolak tanggal masa depan dan tanggal yang diubah ke sebelum barang datang |
| `sales/correction.sql` | `cp7_note.command` | Tolak bila ada pembayaran realokasi Native (`…REALLOCATED_PAYMENT…`) atau bila harga bersih per pcs baris yang sudah diretur berubah (`CP7_NOTE_RETURNED_LINE_PRICE_CHANGED`) |
| `payroll/roster-write.sql`, `payroll/settlement-read.sql` | ubah pekerja, `totals_match_items` | Kode pekerja dipertahankan; payroll beku dibandingkan dengan itemnya sendiri |
| `cutting-yield/model-producer.sql` | evaluasi model | Hanya record batch prospektif terpilih |
| `demand/estimate.sql` | laju harian | `trunc(…,12)`, bukan dibulatkan ke atas |
| `planning/netting.sql` | suplai terarah | Posisi WIP dengan sisa 0 bukan suplai |
| `demand/history.sql`, `planning/history.sql` | `cp7_demand.history`, `history_build` | Bentuk linear, byte-identik dengan `c1f91041` |
| `planning/schedule-scenario.sql`, `wip/yield.sql` | `cp7_schedule_native.build`, `cp7_wip.project_yield` | Bentuk linear, byte-identik dengan `117732fb` |

Frontend: field rupiah 6 desimal menolak pola ribuan ambigu (`moneyDecimal`), label "Nilai absensi" dan "HPP lot saat ini", pesan Indonesia untuk dua kode penolakan nota.

Harness: mode `--payroll-review` P12 kini memasang paket settlement + buku kas E05 yang dibutuhkan layar payroll sejak F03 E05. Asersi oracle tidak berubah.

### 8.2 Titik audit prioritas

1. **Pertumbuhan dan margin.** Pembanding nol atau minus harus `null` (N/A), bukan persen bertanda terbalik. Pendapatan minus pada salah satu periode membuat selisih margin `null`.
2. **Ruang lingkup restate (AP-1).** Saring `created_at = statement_timestamp()` mengandalkan satu pernyataan per perintah. Periksa apakah ada pembalikan lain yang dibuat dalam pernyataan yang sama, misalnya oleh trigger Native.
3. **Retur pada koreksi nota (SL-4).** Perbandingan harga bersih per pcs memakai perkalian silang eksak `(q·p−d)·q' ≠ (q'·p'−d')·q`. Periksa diskon null, qty berubah dengan harga sama, dan baris ganda dengan SKU sama.
4. **Target perencanaan (PL-1).** `trunc` laju 12 desimal tidak pernah melebihi nilai eksak. Karena pecahan sejati ≥ 1/hari, `ceil` tetap sama dengan ceil eksak (uji acak 120 kasus vs BigInt).
5. **Kesetaraan P19.** Semua bentuk linear memakai peta yang dibangun di titik pemindaian lama, sehingga error pertama sama. Kunci ganda di konfigurasi jadwal tetap gagal `21000` seperti subquery skalar lama. Kebijakan yield ganda tetap `CP7_WIP_YIELD_DUPLICATE` pada urutan yang sama. `project_yield` mengambil posisi pertama dengan kunci itu. Uji paritas: `f04-demand-history-linear`, `f04-history-build-linear`, `f04-schedule-scenario-linear` (job Shell `p19-assembly`).
6. **Input rupiah.** Aturan "16.000" ditolak hanya di layar. Server tetap menerima desimal seperti sebelumnya; harga tersimpan yang tidak diubah tetap diterima.

### 8.3 Masih terbuka

- **Skala aplikasi penuh.** Capture aplikasi 5.000 target end-to-end (sumber Native nyata, serve, render browser) dan latensi klik-sampai-tampil belum diukur.
- **ETA skenario jadwal.** Biaya tersisa O(posisi × langkah × jendela kalender). Lokal (bukan bukti): 5.000 posisi yang semuanya mendapat ETA butuh 10,9 dtk, jadi termasuk pekerjaan latar belakang. Batas tidak dinaikkan.
- **Kebijakan pemilik.** PL-3, PL-4, PL-5, PL-7, PL-8 dan AP-5 tetap tercatat di `SELF_CHECK_FORMULAS_20261006.md` §4; nilainya tidak dikarang.
- **PR UX #43 ke `main`.** Tertahan aturan CodeQL repo (analisis PR bawaan GitHub tidak berjalan sejak sekitar 3 Okt).

## 9. Tambahan 7 Okt 2026 (pagi): PL-3/4/5/7, P19 riwayat permintaan, P18 pembanding katalog

Status §8.3 diperbarui: ETA jadwal sudah hanya membaca jendela terpakai (`8e0319e4`); PL-3, PL-4 dan PL-7 diperbaiki sebagai masalah implementasi/kontrak (bukan nilai kebijakan); PL-5 diberi label jujur dan pilihan untuk owner; PR UX #43 sudah di-merge ke `main` (`a58385e4`) lewat jalur CodeQL yang sah. Rincian dan bukti uji ada di `SELF_CHECK_FORMULAS_20261006.md` §2b/§4/§6/§7.

### 9.1 Objek yang berubah (signature tetap, tanpa role/RPC/tabel/hak baru)

| Berkas SQL | Fungsi | Perubahan |
|---|---|---|
| `models/evaluation.sql` | `cp7_models.evaluate` | **Kontrak:** pengetahuan latih fold ditutup akhir hari origin+1 WIB (`rolling-evaluation-2`); jendela latih, aktual, dan penjaga registrasi tetap |
| `baseline/capacity.sql` | `cp7_baseline.capacity` | **Perilaku:** beban berlebih dibawa ke jendela berikut; sisa sesudah jendela terakhir → `UNKNOWN`/`EXISTING_LOAD_EXCEEDS_CALENDAR` (`calendar-capacity-2`); beban 12 desimal yang sama dengan menit jendela dibulatkan ke atas dianggap pas |
| `plan-native/preflight.sql` | `cp7_plan_native.preflight` | **Perilaku:** rencana kedua untuk target ditolak (`40001 CP7_PLAN_LINKED_INTENT_CONFLICT`) sampai Original yang sama membuktikan semua potongan grup rencana yang terposting sudah FG/EXIT |
| `demand/history.sql` | `cp7_demand.history` | Jalur cepat validasi berbasis himpunan; byte-identik termasuk penolakan pertama |
| `planning/schedule-scenario.sql` | `cp7_schedule_native.build` | ETA hanya membaca jendela terpakai; byte-identik |

Frontend: pratinjau rencana menyebut asumsi yield 100% dan bahwa yield start baru belum ditentukan (PL-5 opsi C, label saja).

### 9.2 Catatan pemasangan/rollback (P21)

- Perubahan badan fungsi mengubah hash mesin; Original model/analisis/jadwal yang dibuat sebelum pemasangan akan terbaca `ARCHIVED_STALE` dan tetap utuh (tidak ditulis ulang). Jadwal perlu ditinjau ulang sekali sesudah pemasangan bila sumbernya berubah — perilaku yang sama dengan pemasangan sebelumnya.
- Rollback mengembalikan definisi pendahulu dari salinan asli seperti §4; tidak ada objek baru yang perlu dihapus.
- Suite yang jumlah kasusnya berubah: model **31 → 32** (`PL3_PRIVATE_NEXT_DAY_KNOWLEDGE`), rencana **39 → 40** (`PL7_POSTED_CUT_NOT_PLANNED_TWICE`). Deklarasi lama dan kegagalan pertama tetap tercatat.

### 9.3 Titik audit prioritas tambahan

1. **PL-3 kontrak.** Revisi hari ≤ O yang baru diketahui selama O+1 (mis. retur yang diposting O+1 atas penjualan lama) ikut latih; nilai hari target (O+1..O+h) tidak pernah masuk jendela latih. Periksa apakah ini dapat diterima untuk prakiraan harian yang diterbitkan pagi O+1.
2. **PL-4 resolusi.** Aturan "≤ menit jendela dibulatkan ke atas 12 desimal dianggap pas" hanya menyerap pembulatan representasi (< 1e-12 menit); periksa tidak ada beban nyata yang hilang karena aturan ini.
3. **PL-7 predikat.** Intent tetap terbuka bila status WIP Original bukan COMPLETE, grup tidak ada di cakupan Original, atau input > FG + EXIT pada pool `CUT:<grup>:%`. Periksa `NOT` dan operator JSON diberi kurung (riwayat bug `1a6196d3`).
4. **Jalur cepat riwayat.** Predikat himpunan harus *cukup* (bila menyatakan bersih, loop pasti tidak menolak). Uji mutasi membuktikan pelonggaran regex pcs atau aturan kolom ekstra langsung terdeteksi.

### 9.4 Masih terbuka

- **PL-8 / skala grup potong:** normalisasi potong kuadratik (lokal: 250 grup 8,6 dtk; 500 grup 31,6 dtk) dan posisi qty 0 dari grup yang sudah habis menghabiskan batas netting 1000 posisi. Linearisasi dengan paritas sedang dikerjakan; pemangkasan grup habis butuh kenaikan versi kontrak.
- **Skala aplikasi penuh 5.000 target:** batas desain (1000 target per capture, grid 100.000, 8 dtk per request, tanpa worker di luar request) membuat 5.000 target tidak bisa lewat satu capture tanpa keputusan kapasitas; pengukuran alur penuh dan klik-sampai-tampil di 100/300/1000 target sedang disiapkan. Bukti kernel dan bukti aplikasi dipisahkan.
- **PL-5 dan AP-5:** menunggu pilihan owner; tidak ada angka dikarang.


## 10. Tambahan 7 Okt 2026 (siang): PL-8 bagian 1 dan 2, netting, alokasi dan baseline linear, kasus Native PL-4

Ketiga perubahan kernel di bawah ini **byte-identik terhadap pendahulunya termasuk penolakan pertama** (kode SQLSTATE dan pesan sama, di posisi baris yang sama), diuji pada mode plan cache auto/custom/generic, dan setiap uji paritas membuktikan diri dengan mutasi yang sengaja salah. Tidak ada batas yang dinaikkan (1000 target/produk per capture, 100.000 pasangan, 1000 posisi, 8 dtk per request tetap). Lokal PG16 bukan bukti; bukti CI ada di `SELF_CHECK_FORMULAS_20261006.md` §6.

### 10.1 Objek yang berubah

| Berkas SQL | Fungsi | Perubahan | Uji paritas (pendahulu) |
|---|---|---|---|
| `wip/graph.sql`, `wip/normalize.sql`, `wip/bs.sql`, `wip/production.sql` | `normalize_cutting`, `settle_bs`, `reconcile`, `normalize_production` | Linear terhadap jumlah grup potong (peta malas di titik pindai lama, `jsonb[]`, bucket hash, flag jendela untuk kunci ganda/pembalikan berulang). Signature, owner, `search_path` tetap; tanpa fungsi baru | `f04-wip-normalize-linear` (`3c0aca7f`) |
| `planning/netting.sql` | `cp7_netting_native.build`, `matching`, `timeline` | Linear terhadap posisi × target; posisi dengan fakta sumber+model sama memakai ulang hasil pemimpin sesudah panggilan `match_target` sendiri | `f04-netting-linear` (`d7548eb8`; 885 kasus build, 225 `timeline`) |
| `planning/netting.sql` | **baru:** `cp7_netting_native.matching_models(jsonb,jsonb)` | Helper privat `immutable security invoker`, owner `cp7_capture`, di skema yang USAGE-nya dicabut dari `public/anon/authenticated/service_role`; terdaftar di `cp7_netting_bundle.py` (`'i'`) | ikut `f04-netting-linear` |
| `baseline/allocation.sql` | `cp7_baseline.allocate` | Linear terhadap pasangan; vonis `match_target` dipakai ulang per pasangan fakta hanya sesudah pasangan itu lolos validasinya sendiri | `f04-allocation-linear` (`083c90e3`; 1.187 kasus × 3 mode, 8 mutasi) |
| `planning/baseline-source.sql` | `cp7_baseline_native.build` | Linear terhadap target; peta profil/stok/kebijakan dibangun malas, `21000` untuk dua profil per root (`IDENTITY_CONFLICT`) atau dua stok per target ditiru, kebijakan `LIMIT 1` urutan array dengan semantik `jsonb ?` | `f04-baseline-build-linear` (`9e3394e3`; 503 capture × 3 mode, 7 mutasi) |
| `planning/supply-source.sql` | **baru:** `cp7_supply_native.exhausted_groups(jsonb)`; `wip_source_at` (kini plpgsql, tetap STABLE); `build` | **Kontrak `cp7.native-supply.v2` (PL-8 bagian 2):** grup potong yang terbukti habis per batch 50 keluar dari fakta produksi dan dicantumkan di `production_scope.exhausted_cutting_groups`; batas 1000 berlaku pada grup tidak habis; >20000 grup terposting ditolak sebelum klasifikasi. `exhausted_groups` immutable, security invoker, owner `cp7_capture`, terdaftar di `cp7_supply_bundle.py` | `f04-supply-exhausted` (6 uji, 11/12 mutasi) + Native `PL8_*` |
| `plan-native/preflight.sql` | `cp7_plan_native.preflight` | Jalur daftar grup habis PL-7 dibetulkan ke `production_scope.exhausted_cutting_groups` (jalur lama tidak pernah dikeluarkan siapa pun) | `f04-supply-exhausted` (intent PL-7) |

Tidak ada tabel, role, RPC, grant, atau batas baru. Hasil yang sama berarti hash mesin Original yang ada tidak berubah karena isi, tetapi hash definisi fungsi berubah — lihat 10.3.

### 10.2 Titik audit prioritas tambahan

1. **Memo vonis di `allocate` dan `build`.** Kunci memo harus memuat *semua* fakta yang dibaca `match_target` (constraint, `confirmed_target`, kualitas, bukti, target). Mutasi `MEMO_WITHOUT_PROOF/CONSTRAINTS/CONFIRMED/TARGET` membuktikan uji menangkap kunci yang kurang; periksa juga bahwa tidak ada fakta lain yang dibaca `match_target` di luar daftar itu (kopling pemeliharaan: bila `cp7_wip.match_target` kelak membaca kolom baru, kunci memo wajib ikut).
2. **Penolakan pertama.** Sumber/target dengan fakta sama tetapi ref tidak sah harus ditolak di pasangannya sendiri, bukan memakai vonis pasangan sebelumnya (kasus `MEMO_PROBE_BAD_SOURCE/BAD_TARGET` → `22023 CP7_WIP_DUPLICATE_REF`).
3. **Subquery skalar.** Bentuk linear meniru penolakan `21000` (subquery mengembalikan >1 baris) dari pendahulu; periksa setiap tempat `SELECT INTO` (ambil baris pertama) vs subquery skalar (tolak) tetap sesuai pendahulu.
4. **Baseline `IDENTITY_CONFLICT`.** `cp7_profile.source` mengeluarkan satu baris per versi produk; root dengan dua versi aktif membuat build menolak `21000` (perilaku lama yang dipertahankan, bukan diperbaiki). Periksa apakah penolakan seluruh capture ini yang diinginkan, atau root tersebut seharusnya `UNKNOWN` — keputusan kontrak, bukan optimasi.
5. **Sisa biaya.** Bila setiap sumber/target punya fakta unik, biaya tetap didominasi satu `match_target` per pasangan (lokal 300×100: 3,5 → 2,1 dtk). Ini bukan regresi, tetapi batas atas yang jujur.

### 10.3 Catatan pemasangan/rollback (P21)

- Badan fungsi berubah → hash mesin berubah; Original lama terbaca `ARCHIVED_STALE` dan tetap utuh. Jadwal/netting perlu ditinjau ulang sekali sesudah pemasangan bila sumbernya berubah.
- Rollback tetap mekanisme §4: `drop owned by <role CP7> cascade` + `drop role`, lalu definisi Native (erp/public) pendahulu dikembalikan dari salinan aslinya. Semua fungsi di 10.1, termasuk `cp7_netting_native.matching_models` yang baru, dimiliki `cp7_capture`/role CP7 sehingga ikut terhapus; tidak ada langkah rollback tambahan. Belum ada pemasangan CP7 hosted, jadi tidak ada jalur "CP7 lama → CP7 baru" yang perlu di-rollback ke definisi kernel CP7 sebelumnya; bila kelak ada, definisi kernel sebelumnya diambil dari commit pendahulu yang dipakai uji paritas (WIP `3c0aca7f`, netting `d7548eb8`, alokasi `083c90e3`, baseline `9e3394e3`) dan `matching_models` di-drop sesudah `build`/`matching` lama terpasang (pendahulu tidak memanggilnya).
- Jumlah kasus suite berubah: jadwal **70 → 71** (`PL4_OVERFLOW_CARRIED`), netting **82 → 83** (suite netting ikut menjalankan kasus jadwal). Rencana **40 → 42** (`PL8_SPENT_HISTORY_1100_NETTED_AS_OPEN_WORK_ALONE`, `PL8_OPEN_SCOPE_1001_STILL_REFUSED`). Analisis **152 → 153** dan attention **284 → 285** (keduanya ikut menjalankan kasus jadwal; kegagalan pertama 37570105099 dicatat).
- **Supply v2 mengubah fingerprint sekali:** fingerprint supply → jadwal → netting → analisis. Run supply/jadwal/netting/analisis lama terbaca `ARCHIVED_STALE`, jadwal tersimpan perlu ditinjau ulang sekali, draf rencana ditolak `CP7_PLAN_SOURCE_CHANGED` sampai di-capture ulang, ruang kerja kain dan publikasi laporan basi, perbandingan laporan lintas mesin menampilkan UNKNOWN. Karena CP7 belum pernah dipasang di hosted, dampak ini hanya ada di lingkungan uji. Frontend tetap membaca arsip supply v1. Kegagalan pertama dengan deklarasi lama (run 37568940391) tetap tercatat.

### 10.4 Masih terbuka

- **PL-8 bagian 2** masuk sebagai supply v2. Batas jujur yang tersisa: klasifikasi per request ±1,6 ms/grup satu ukuran, ±4,4 ms/grup tiga ukuran (lokal), jadi ±1500 / ±550 grup historis muat 8 dtk; bukti habis yang dipersistenkan dan di-hash isi adalah keputusan berikutnya.
- **Skala aplikasi penuh:** run `p19-scale5` dengan harness commit-per-writer sedang berjalan (head `a634296e`, sebelum alokasi linear); hasil 300/1000/5000 dan profil fase dicatat di `p19/P19_FULL_APP_SCALE.md` setelah selesai.
- **Bukti satu head** untuk kandidat P20: `0b3806b5`, 15/15 workflow success (tabel run di handoff §15.5). Bukti penulis; penerimaan akhir mengikuti kandidat yang lolos audit independen P20.

## 11. Tambahan 7 Okt 2026 (sore): arahan owner butir 1–7

Keputusan owner 7 Okt dijalankan tanpa membuka ulang keputusan sebelumnya. Pemisahan status: **fitur selesai** (kode + kasus Native + uji frontend, menunggu CI satu head), **batas terbuka** (belum dikerjakan atau menunggu nilai owner), **penerimaan auditor** (belum ada; P20 tetap audit independen). `production_go: false`.

### 11.1 Objek yang berubah

| Berkas SQL | Fungsi / objek | Perubahan | Bukti |
|---|---|---|---|
| `planning/netting.sql` | `cp7_netting_native.build` | **PR #44 (Astra)** memakai ulang timeline target tanpa tepi; **penjaga** (`a68abf1e`): pakai ulang hanya bila baris target yang dibaca panggilan pertama identik (`baseline_rows[...] = r::text`) | `f04-netting-linear` vs `d7548eb8` + kasus `DUP_ROW_SKIPPED_TARGET/FG` + mutan `REUSE_BY_KEY_ONLY`; md5 benchmark identik sebelum/sesudah |
| `planning/analysis.sql`, `analysis-finance.sql`, `analysis-jobs.sql` | **baru:** `finance_mode(jsonb)` (i), `source_for(jsonb,text)` (s); `capture(jsonb,uuid,text)` (menggantikan 2-arg); `cp7_analysis_jobs.request(jsonb,uuid,text)`; kolom `jobs.finance`; **RPC baru** `erp_cp7_capture_operational_analysis_v1`, `erp_cp7_request_operational_analysis_job_v1` (authenticated saja, owner `cp7_capture`, definer, `search_path=''`) | Butir 2: jalur operasional tidak memanggil laporan pemilik dan tidak memindai buku besar; run ditandai `financial_capture=DEFERRED`; serve/manifest membandingkan dengan sumber operasional yang sama. Jalur penuh tidak berubah | `P19T_FINANCE_DEFERRED_NO_BOOK_READ` (0 scan `journal_lines/account_daily_balances/cash_accounts`, kontrol positif), `P19T_FINANCE_MODE_IDENTITY`, `P19T_HTTP_FINANCE_ON_DEMAND`, `P19T_BROWSER_FINANCE_ON_DEMAND`, `f05-analysis-jobs` |
| `reminders/payable-source.sql` | **baru:** `payable_due_rule(jsonb,text,text)` (i, owner `cp7_payable_read`); **grant baru** `EXECUTE erp.material_purchase_current_unit_cost(uuid)` ke `cp7_payable_read`; kontrak `cp7.native-material-ap-source.v2` | Butir 7 (AP-5): pembayaran per penerimaan dihitung ke jatuh tempo tertua dulu, berlabel aturan, bukan bukti per invoice; tidak mengubah jurnal/pembayaran | `P16_NATIVE_AP_CONDITION_AP5_OLDEST_DUE_FIRST` |
| `reminders/local-sink.sql`, `obligation-report.sql` | teks pesan/lampiran | Label "menurut aturan … bukan bukti per invoice" bila `due_basis` diawali `RULE_` | uji frontend renderer kembar |
| `plan-native/preflight.sql`, `commands.sql`, `ownership.sql` | **baru:** `cp7_plan_native.history_yield(text)` (s, owner `cp7_plan_writer`); kontrak `cp7.plan-preview.v3`; field payload opsional `new_start_yield` | Butir 6 (PL-5): yield start baru tidak pernah dianggap 100%; A (perkiraan per rencana, asumsi `PLAN_NEW_START_YIELD` ditinjau) atau UNKNOWN; B menunggu kebijakan owner | `PL5_NEW_START_YIELD`, `P08_PREVIEW_READONLY` (kini UNKNOWN) |

### 11.2 Titik audit prioritas tambahan

1. **Jalur operasional benar-benar tanpa buku besar.** Bukti memakai penghitung transaksi `pg_stat_xact_user_tables`; periksa bahwa tidak ada pembaca lain (mis. laporan publikasi, lampiran, pengingat) yang memanggil `cp7_analysis_native.source(q)` langsung untuk run DEFERRED. Semua memanggil `serve`, yang memilih sumber lewat `finance_mode`.
2. **Satu UUID satu mode.** Capture biasa tidak membaca tabel job; run mode lain pada UUID job yang menunggu membuat job FAILED `CP7_ANALYSIS_REQUEST_CHANGED` (tidak mencampur). Periksa apakah ini cukup atau capture biasa juga harus menolak UUID job.
3. **AP-5 tidak memundurkan jatuh tempo karena retur/kredit.** Pengurang tingkat penerimaan tidak dialokasikan ke invoice; sisa yang tidak bisa dikaitkan memakai jatuh tempo tercatat lama. Periksa `invoice gabungan` (satu invoice beberapa penerimaan): bagian invoice per penerimaan dihitung dari baris invoice untuk item penerimaan itu.
4. **PL-5 aritmetika.** `ceil(kebutuhan×penyebut/pembilang)`, `floor(potong×pembilang/penyebut)`; klien menghitung ulang dengan rasional eksak. Tanpa yield: batas potong = `ceil(kebutuhan)` sebagai batas aman, bukan klaim hasil.

### 11.3 Catatan pemasangan/rollback (P21)

- RPC publik baru (2) dan fungsi privat baru (4) dimiliki role CP7 → ikut `drop owned by`. Grant baru ke `cp7_payable_read` pada fungsi Native `erp.material_purchase_current_unit_cost(uuid)` ikut hilang saat role di-drop; tidak ada definisi Native yang diubah.
- Hash mesin analisis berubah (definisi `serve`, `capture`, jobs) → Original lama `ARCHIVED_STALE` sekali.
- Jumlah kasus: transport P19 **11 → 15**, attention **285 → 286** (native 181), rencana **42 → 43** (native 29).

### 11.4 Batas terbuka

- **B (yield histori) belum aktif:** paket usulan jendela 180 hari, ≥5 grup dan ≥200 PCS, batas bawah Wilson 90% di `PL5_YIELD_POLICY_PROPOSAL_20261007.md` menunggu persetujuan owner; penyimpanan kebijakan bertanda tangan dan pembaca histori dibuat sesudahnya.
- **Target 3 dtk** untuk analisis berat tidak tercapai dan tidak ditandai tercapai; berjalan sebagai pengecualian latar tercatat `P19_PLANNING_ANALYSIS_BACKGROUND_20261007`.

## 12. Tambahan 7 Okt 2026 (malam): PL-8 bagian 3 — bukti grup habis tersimpan (butir 4)

Status terpisah: **fitur selesai** (kode + uji kernel + kasus Native lokal; CI di head berikutnya), **batas terbuka** di 12.4, **penerimaan auditor** belum ada. `production_go: false`.

### 12.1 Objek yang berubah

| Berkas SQL | Fungsi / objek | Perubahan | Bukti |
|---|---|---|---|
| `planning/supply-source.sql` | **tabel baru** `cp7_supply_native.exhaustion_proofs` | Append-only (trigger `cp7_private.immutable_run`), RLS dengan kebijakan tanpa akses, owner `cp7_capture`, semua hak dicabut dari `public/anon/authenticated/service_role`. Satu baris = grup + `facts_hash` + `kernel_version` + jam capture + vonis `EXHAUSTED` + ukuran graf | `cp7_supply_bundle.verify` memeriksa RLS, kebijakan, owner, trigger dan hak kedua tabel |
| `planning/supply-source.sql` | **baru:** `classify(jsonb)` (i), `proof_kernel()` (s), `batch_reuse(jsonb,text)` (s), `batch_verdict(jsonb,text)` (s), `wip_source_parts(timestamptz)` (s), `source_parts()` (s), `store_proofs(jsonb,timestamptz)` (v), `prove_exhausted(timestamptz,uuid,integer)` (v); `exhausted_groups`, `wip_source_at`, `source` kini pembungkus; `capture` menyimpan bukti baru dalam statement yang sama | Semua owner `cp7_capture`, `security invoker`, `search_path=''`; **tanpa RPC dan tanpa grant baru** (`prove_exhausted` tidak bisa dipanggil authenticated). Kontrak keluaran tetap `cp7.native-supply.v2` | `f04-supply-proofs` (3 uji, 25/25 mutan), `f04-supply-exhausted` 6/6, Native supply 38 (lokal) |

### 12.2 Titik audit prioritas tambahan

1. **Isi hash lengkap?** Hash memuat setiap baris fakta milik grup dari 19 array capture (urutan capture), status selesai rework terhadap jam capture, `contract_version` dan `knowledge_mode`. Periksa bahwa `classify` tidak membaca fakta lain di luar 19 array itu (kopling pemeliharaan: kolom fakta baru di `cp7_wip.capture_cutting_sources` wajib masuk daftar `own`, kalau tidak batch_reuse menolak memakai ulang karena baris tanpa grup → aman, tetapi periksa).
2. **Isolasi grup.** Bukti hanya dipakai bila tidak ada tautan (14 kolom referensi) atau baris bersama (selain klaim) ke grup lain di batch yang sama. Mutan `outgoing/incoming_link_not_isolated` membuktikan uji menangkap isolasi yang kurang.
3. **Versi kernel.** `proof_kernel()` meng-hash definisi fungsi yang dijangkau secara rekursif dari capture/klasifikasi + `server_version_num`; perubahan fungsi apa pun di jalur itu atau upgrade PostgreSQL membuat semua bukti tidak terpakai (dihitung ulang, bukan salah). Periksa pola regex pemanggilan (`skema.fungsi(`) menangkap semua panggilan di jalur itu.
4. **Batch yang menolak.** Bila sisa batch tidak COMPLETE atau graf melewati batas `reconcile`, batch tidak memangkas apa pun, termasuk grup berbukti (sama seperti bagian 2; mutan `refused_batch_still_prunes`).

### 12.3 Catatan pemasangan/rollback (P21)

- Tabel dan fungsi baru dimiliki `cp7_capture` → ikut `drop owned by cp7_capture cascade`; tidak ada objek Native yang diubah. Pemasangan ulang mulai dengan tabel kosong: capture pertama membayar biaya klasifikasi penuh lalu menyimpan bukti.
- Hasil supply byte-identik dengan pendahulu (dengan atau tanpa bukti), tetapi definisi fungsi berubah → hash mesin berubah → run supply/jadwal/netting/analisis lama `ARCHIVED_STALE` sekali.
- Jumlah kasus suite tidak berubah (supply 53, rencana 43).

### 12.4 Batas terbuka (keputusan, bukan cacat)

- **Siapa menjalankan `prove_exhausted`** untuk riwayat besar (job admin, pg_cron, atau facade berizin owner). Sampai diputuskan, bukti hanya bertambah lewat capture biasa (yang tetap dibatasi 8 dtk/1000 grup tidak habis).
- **Bukti dari capture netting/analisis/jadwal:** sekarang hanya `cp7_supply_native.capture` yang menyimpan; jalur lain memakai bukti tetapi tidak menulis.
- **Upgrade PostgreSQL atau perubahan kernel** membatalkan semua bukti sekaligus (aman, tetapi capture pertama sesudahnya lambat). Belum ada sinyal perubahan berbasis trigger di tabel Native (sengaja: Native tidak diubah).
- **Baca riwayat bukti** (bukti lama yang tergantikan) hanya untuk admin; belum ada layar.

## 13. Tambahan 7 Okt 2026 (malam): 5.000 target fase A (butir 3) — belum memenuhi keputusan owner

Catatan historis fase A; lanjutan produk dan bukti penulis terkini ada di §14.

Status terpisah: **fitur selesai** hanya untuk perubahan di 13.1 (paritas byte-identik, CI di head `d2c98812`); **batas terbuka**: kapasitas 5.000 target belum didukung (fase B–E di `p19/P19_STAGED_5000_20261007.md`); **penerimaan auditor** belum ada. `production_go: false`.

### 13.1 Objek yang berubah

| Berkas SQL | Fungsi | Perubahan | Uji paritas (pendahulu) |
|---|---|---|---|
| `wip/matching.sql` | `cp7_wip.check_allocations` | Cek kunci kembar sumber/target: satu penanda jendela (posisi kembar pertama) menggantikan objek yang disalin per entri (kuadratik di 5.000 target). Kunci setiap entri tetap divalidasi sebelum cek kembar di entri itu, jadi penolakan pertama sama | `f05-staged-analysis` uji 2 (1.890 perbandingan vs `a68abf1e`, termasuk kunci berulang/non-string/null) |
| `planning/netting.sql` | **baru:** `cp7_netting_native.matching_models_within(jsonb,jsonb,integer)` (i); `matching_models` kini membungkus dengan 5000 | Panggilan tunggal tetap 5000 | `f04-netting-linear` vs `d7548eb8` |
| `planning/analysis-finance.sql` | **baru:** `finance_apply(jsonb,jsonb)` (i), `finance_overlay(jsonb,jsonb)` (i); `build` = `finance_overlay(build_operational(...)-'semantic_hash', c)` | Pemisahan murni, isi sama | Native analisis (P08 `analysis152`, attention) dan `f05-staged-analysis` uji 3 |
| `planning/analysis-jobs.sql` | `cp7_analysis_jobs.store` | Potongan segmen satu lintasan (`left`/`right(s,-n)`), potongan sama dengan `substr(body,i*n+1,n)` yang menghitung ulang semua karakter sebelumnya (lokal 25,5 dtk di 65 MB) | `f05-analysis-jobs`: setiap segmen kecuali terakhir tepat 2.000.000 code point; gabungan = Original; hash per segmen |
| `planning/history-source.sql`, `baseline-source.sql`, `supply-source.sql`, `schedule-scenario.sql`, `netting.sql`, `analysis.sql` | **baru:** `cp7_planning.history_source_within(integer)`, `cp7_baseline_native.source_within(integer)`, `cp7_supply_native.source_parts_within(integer)` / `source_within(integer)`, `cp7_schedule_native.source_within(integer)`, `cp7_netting_native.source_within(integer,integer)`, `cp7_analysis_native.source_within(integer,integer)` (semua `s`) | Batas produk yang dibaca menjadi parameter; fungsi tanpa argumen kini pembungkus dengan batas lama (1000 produk, 5000 produk pencocokan), jadi isi capture tunggal sama. Disiapkan untuk capture job bertahap (5000/10000); belum ada pemanggil produk selain pembungkus | Native semua suite (memanggil pembungkus); `f04-supply-exhausted`/`f04-supply-proofs` dengan stub `source_within` |

Semua fungsi baru `security invoker`, `search_path=''`, owner `cp7_capture`, tanpa grant; terdaftar di verifikasi bundle masing-masing (planning, baseline, supply, schedule, netting, analysis). Tidak ada tabel, RPC, role, grant, atau batas baru.

### 13.2 Bukan produk

Kernel job bertahap ada di `tests/cp7/families/f04/staged-analysis.prototype.sql` (tidak dipasang; skenario, kain, dan aksesori masih stand-in). Ia diuji paritas terhadap `build` tunggal di job CI `p19-staged`. Pengukuran capture satu statement di 5.000 produk dilakukan oleh harness skala P19 dengan batas sumber dilonggarkan **hanya di savepoint yang dibatalkan** (`CAP_LIFTED_MEASUREMENT_ONLY_ROLLED_BACK_NOT_INSTALLED`); produk tetap 1000.

### 13.3 Catatan pemasangan/rollback (P21)

Fungsi baru milik `cp7_capture` → ikut `drop owned by`. Definisi berubah → hash mesin netting/analisis berubah → run lama `ARCHIVED_STALE` sekali; hasil sama.

## 14. Takeover writer GPT: produk bertahap 5.000 target

Seluruh patch checkpoint `7927b42c` dipasang bersama. Kontrak mengikat tetap
`p19/P19_STAGED_5000_20261007.md` §10. Head pertama `cb98b0f8` belum lulus
kualifikasi penuh; seluruh bukti hijau dan kegagalan pertamanya dicatat di
`evidence/gpt-staged-5000-20261008/README.md`, dengan Original dan hash ZIP.
`independent_acceptance=false`, `production_go=false`.

Writer aktif GPT atas mandat owner. Rujukan takeover seluruh ERP, otoritas
dan kelanjutan: `handoff/GPT_WRITER_STAGED_5000_20261008.md`.

### 14.1 Objek dan prioritas auditor

| Objek | Perilaku dan batas yang harus diaudit |
|---|---|
| `cp7_analysis_stage` | Sepuluh tabel privat milik `cp7_capture`, RLS deny-all, tanpa hak publik; satu acuan MVCC, UUID run tetap, unit/intermediate/header/halaman immutable. Job hanya boleh memperbarui kemajuan. |
| Enam RPC staged v1 | Request/step/get, indeks halaman, satu halaman, pemeriksaan sumber; authenticated saja, definer, `search_path=''`, hak diperiksa lagi setelah kunci. Batas unit tetap 8 detik; tiga penghentian membuat FAILED tanpa hasil parsial. |
| Identitas hasil | SHA-256 hash header + newline + hash halaman berurutan, termasuk daftar kosong. Klien memverifikasi byte UTF-8, rentang, jumlah, identitas, hak, header dan setiap halaman. Uji menyusun ulang analisis/Original persis dari header dan seluruh halaman. |
| UUID lintas jalur | Satu kunci actor/request untuk capture biasa, job biasa dan staged. Pemakaian UUID yang sama oleh jalur lain ditolak dua arah; tidak ada transaksi baru saat pemulihan. |
| Pembaca hasil lama | Run staged tidak masuk `cp7_analysis_native.runs`; pembaca seluruh hasil tetap menolak UUID staged. Laporan/pengingat/AI/rincian stok/kain/draf/arsip belum tersedia untuk staged dan tidak diberi hasil halaman sebagai hasil lengkap. |
| Driver dan klien | Pause menghentikan driver klien; reload GET UUID yang sama. Pointer hasil selesai hanya menyimpan UUID/query; buka ulang DONE memeriksa hak/hash dan membaca halaman, tanpa request/step/hitung ulang. |

Kapasitas/batas: 5.000 target, 500.000 sel riwayat, 1.000.000 pasangan,
10.000 produk pencocokan; header/halaman maksimal 8.000.000 byte UTF-8.
Batas jalur tunggal dan dokumen klien 64.000.000 byte tetap. UNKNOWN tetap
UNKNOWN, keuangan staged DEFERRED dan tidak dianggap nol. Tidak ada yield,
retensi otomatis, driver server atau fungsi downstream baru yang dikarang.

### 14.2 Bukti dan latensi

Head `cb98b0f8`: seluruh 1.659 uji Shell dan 14 uji kernel staged lulus;
transport Native/Auth/HTTP/browser lama 15/15 lulus. Kernel capture sintetis
5.000×100 selesai 148,808 detik, unit terlama 2,1006 detik, semua 5.000
target tercakup, tanpa retry. Ini pengukuran kernel, bukan SLA pabrik.
Uji browser pertama 5.000 target/1 hari memuat 26 halaman dalam 60,0456
detik tetapi pemeriksaan akhir gagal di SQL bukti; belum diterima penuh.

Koreksi harness dan berkas sementara benchmark yang ditandai CodeQL sedang
dikualifikasi pada head berikutnya. PAGES/PAGE_INDEX juga berhenti membaca
acuan dan hasil kernel yang tidak dipakai. Waktu buka hasil selesai dan
tiap halaman harus diukur dari klik asli sampai hasil terverifikasi dan dua
frame paint. Arahan owner 8 Okt 02:09 WIB: **3 detik menjadi sasaran,
bukan gerbang wajib; optimalkan semaksimal mungkin**. Waktu akumulasi job,
capture, acknowledgement dan load hasil dicatat terpisah.

### 14.3 Pemasangan dan rollback

Skema, tabel dan fungsi staged dimiliki `cp7_capture`; rollback `drop owned
by cp7_capture cascade` menghapusnya bersama objek CP7. Tidak ada role/grant
Native permanen tambahan. Pemeriksaan bundle mencakup katalog tepat,
RLS/trigger/hak, enam RPC dan larangan menulis run/dokumen jalur tunggal.
Hash mesin berubah; Original lama tetap utuh dan bisa ARCHIVED_STALE.

P21 rehearsal sudah lulus di head pertama tetapi **bukan receipt pemasangan**.
Paket final harus dibekukan sesudah bukti 15 workflow pada satu head, lalu
P20 audit independen. Integrasi, hosted, main, Cloudflare, pemasangan dan GO
belum dilakukan. PL-5 B dan konfigurasi owner yang masih pending tetap terbuka.

### 14.4 Rehearsal kandidat perbaikan 43d26996

Run `37677705173`, artifact `11508795699`: PASS. Pemasangan memuat 1.407
fungsi, 75 tabel CP7 dan 34 role CP7; pasang ulang memiliki hash katalog
persis sama `691c0eff044b0c606e489ac449593ab7431e389499d701cb8fb15e5f1a1e1b1d`.
Rollback sebelum penggunaan dan pemulihan katalog terverifikasi, advisor
gate lulus, Native CP6 dipulihkan.

Batas bukti yang penting: langkah USE runtime berlabel
`HELD_OPEN_THEN_ROLLED_BACK`, walaupun docstring lama skrip menyebut commit.
Penolakan rollback sesudah USE dibuktikan dalam transaksi terbuka tersebut;
ini bukan bukti restore pemasangan yang sudah dipakai dan di-commit.
P21 nyata tetap menunggu kandidat diterima P20 dan bukti pemasangan/T2/
backup-restore yang sesuai cakupan nyata. `installed_P21_acceptance=false`.

### 14.5 Kandidat writer final 59d63e46 — bukti, paket, batas penerimaan

**Fitur selesai dalam cakupan writer:** source
`59d63e46ea5b109101a4e0a2eff7d27a8f3541f8`, tree
`2ac496cbacca2fe9ed1a924d0ffcc93bdb2b8844`, 15/15 workflow / 35/35 job sukses.
Semua patch checkpoint 7927b42c terintegrasi, enam RPC staged v1 dan sepuluh
tabel privat/RLS/immutable diuji; Native/Auth/HTTP/browser staged12 12/12,
transport15 15/15, tangga aplikasi scale5 5/5. Seluruh 5.000 target pada
1/30/100 hari selesai, kontrak beku/hash/cakupan penuh dan semua 26 halaman
terbaca. P12 review lama sudah hijau bersama roster/absensi. Seluruh suite
keuangan/koreksi/pembayaran/planning/P08/P18 terpicu pada source yang sama.

Buka DONE 1,003–1,074 dtk tanpa hitung ulang; 75 klik halaman lanjutan
0,554–0,723 dtk. Hitung baru sampai halaman pertama 83,030–110,541 dtk;
progres pertama 5,212–7,258 dtk, acknowledgement 5,7–6,5 ms. Ketiganya dicatat
terpisah. Tiga detik sasaran optimasi owner, bukan gerbang wajib. Semua waktu
merupakan observasi disposable/loopback sekali per vektor, bukan SLA hosted.
Batas 8 dtk/RPC dan 8.000.000 byte/header/halaman tetap. Jalur tunggal tetap
berbatas lama; kapasitas 5.000 adalah jalur staged operasional dalam §10.

**Paket source review P20 tersedia:** `audit-candidate/staged-5000-20261008/`.
Manifest 2.098 berkas Git/source, hash/ukuran, seluruh framework dan acuan
keputusan ERP, seluruh uji/fixture serta kompilasi deterministik F03 dan
full-rule-source-with-staged. Receipt/source/run/Original disimpan di
`evidence/gpt-staged-5000-20261008/`. Seluruh kegagalan cb98/43d tetap utuh;
errata schema/label model/schedule/P18 tercatat dan tidak ditulis ulang.
Auditor dapat memeriksa sumber yang dipin meski HEAD dokumentasi berikutnya
berbeda. Manifest ini bukan klaim acceptance seluruh requirement framework.

**P21 rehearsal 59d:** run `37681765951` sukses, exact Original/receipt
`59d63e46-cp7-p21-rehearsal-retained/`. Cakupannya F03: 988.746 byte SQL,
SHA-256 `d64ae6edbd881b5e915647d98138c3b206c25d3fc318044546ba20d7175daa79`.
Tidak memuat `cp7_analysis_stage`. Kompilasi full-rule-source-with-staged
1.892.844 byte, hash
`1db3baf8f810c7c74bdbd076104c8a0d4a63d345a570bb4ec903e5dc802b44c3`,
tersedia untuk review; belum memiliki receipt pemasangan gabungan P21.
USE di Original F03 adalah HELD_OPEN_THEN_ROLLED_BACK. Tidak dipromosikan
menjadi bukti restore setelah pemasangan penuh yang dipakai dan di-commit.

**Batas terbuka:** integration merge, audit independen P20, lalu P21 komposisi
penuh/T2/pins/advisors/CodeQL/backup-restore/rollback sesudah pemakaian sesuai
cakupan nyata. Laporan/pengingat/AI/rincian stok/workspace kain/draf/arsip
whole-result tidak otomatis tersedia untuk staged. Retensi, server driver,
prioritas downstream, PL-5 B, konfigurasi nyata CP6 dan runner PL-8 masih
keputusan owner; tidak diisi diam-diam. GBD-03 opsi 1 dan D11 tetap disahkan.

**Penerimaan auditor:** belum ada untuk CP7 atau installed P21.
`independent_acceptance=false`, `installed_P21_acceptance=false`,
`full_P19_acceptance=false`, `production_go=false`. Tidak ada perubahan
main, Cloudflare/deployment, hosted Enteng/Supabase, legacy atau produksi.

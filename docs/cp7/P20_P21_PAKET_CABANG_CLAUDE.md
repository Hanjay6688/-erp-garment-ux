# Paket P20/P21 — bagian cabang Claude (P08 fisik kain, P18 pengingat kain)

Catatan integrasi6 Oktober2026: kandidat cabang2ae1db92 dan bukti lama di bawah tetap historis. Build UX merah3c7cb2cf sudah diperbaiki; source0bd kini lulus1,558 tes/165 file. Bukti gabungan aktual, Native/regresi yang sudah dibaca serta pekerjaan P18/P19/P20/P21 yang masih terbuka ada di `p19/P19_UTF8_QUALIFICATION_CHECKPOINT_20261006.md`. Belum ada pembekuan kandidat audit atau pemasangan nyata.

Status: draf persiapan. Belum ada audit independen dan belum ada pemasangan. `independent_acceptance=false`, `production_go=false`, CP6 tetap HOLD. Dokumen ini melengkapi `docs/AUDIT_PANDUAN_PRO_MAX.md` dan handoff (§9, §10). Bukan pengganti paket kandidat gabungan milik GPT.

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

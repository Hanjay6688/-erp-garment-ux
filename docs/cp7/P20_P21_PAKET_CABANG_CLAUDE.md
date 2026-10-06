# Paket P20/P21 — bagian cabang Claude (P08 fisik kain, P18 pengingat kain)

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

# Lampiran C6: daftar acceptance per fitur aksesori dan laundry (pengesahannya = "D06")

**Status: DISAHKAN (D06), 25 September 2026, 15:55 UTC.** Owner mengesahkan rev4 pada commit
`4c61acad2270e11a2aca762237790a68cf36278a` (sha256 berkas `42e0481579497c0acfe45d7092681741d431efaaeb7c200533051690b1d25f35`)
langsung kepada auditor; teks owner dikutip di addendum induk bagian 9. Sesudah pengesahan hanya baris status ini dan centang
bagian 7 butir 2 yang berubah. Nilai `PENDING_POLICY_VALUE` tetap pending sampai owner menyetujui angkanya; pengesahan bukan
penerimaan uji; CP6 tetap HOLD dan `production_go=false`.

Riwayat: USULAN WRITER rev4, 25 September 2026 (OWNER_ACK_REQUIRED sampai pengesahan di atas). Rev4 memperbaiki rev3 menurut
handoff auditor gabungan `AUDIT_WRITER_HANDOFF_CP6.md` tugas T1 (cabang `audit/cp6-final-20260924-gpt-a0bcadf`, commit
08294c2) dan audit teks GPT `out/r9_scope_contract.md`. Daftar perubahan ada di bagian 8.

## 0. Keputusan scope owner (25 September 2026, chat sesi writer, dikutip apa adanya)

> "gw mau semuanya dibikin sekarang dan diuji di cp 6 termasuk all 22 lu harus bikin dan d06. so now what?"

Owner mengonfirmasi keempat butir di bawah langsung ke auditor Fable ("Ya, keempat poin benar"). Dokumen ini tetap belum
ditandatangani. Tafsir writer:
1. **CR yang dimandatkan untuk kandidat CP6.** Instruksi owner terbaru lebih baru dari default successor M:1697, jadi ia
   memindahkan CR ke CP6. Status selesai tetap bergantung pada acceptance dan audit, bukan pada pengesahan dokumen ini.
   Kolom "Kelompok" di bagian 2 dan 3 dibaca **CR-CP6** untuk baris berikut:
   - **ACC-04b**, termasuk konversi ganti merek beserta aksesori baru yang terpakai dan aksesori lama yang benar-benar
     dilepas atau kembali (didukung M:3913, M:3925; nilai barang bekas tetap pending, M:3933–3935, M:4456).
   - **LAU-05b**, perluasan laundry yang sudah disetujui (M:3728–3737).
   - **LAU-06b**, celup ulang BS menjadi SKU baru. Ini **scope tambahan yang masuk CP6 hanya karena mandat "semuanya"**,
     bukan desain di M. M tidak menyebutnya (M:1669, M:3728–3737), dan M:5236 (D03) adalah nilai aksesori bekas, bukan
     transformasi SKU. Pagarnya:
     - tarif atau referensi SKU laundry tidak mengubah identitas produk (M:3094, M:3735);
     - identitas berubah hanya lewat command konversi yang sah, dengan lineage, QC, dan HPP yang dibuktikan.
2. **ALL = 22 keadaan.** Owner menyebut "all 22" secara eksplisit, dan ALL tetap kewajiban CP6 (P:80, P:1024). Registernya
   adalah inventaris writer di handoff §29.6. Pembagian 9 MAPPED / 6 PARTIAL / 7 NO_ADAPTER adalah **inventaris writer
   yang belum diverifikasi auditor dari SQL** (`22-state mapping: UNVERIFIED`). Setiap keadaan harus punya jalur impor
   dan lanjutan yang sah, diuji dari impor sampai jurnal dan layar. Histori lama tidak boleh dikarang (M:369, M:379,
   P:967).
   - Label W05 di BB adalah **PARTIAL: hanya finansial**, yaitu pelunasan dan nota potongan hutang laundry saldo awal.
     Kiriman di luar, cuci gagal, klaim, dan penerimaan belum tertagih masuk BD.
3. **Baris KEBIJAKAN.** ACC-DEC01, 03–07, ERP-DEC02, dan LAU-DEC01–06 diusulkan dibangun sebagai **pengaturan di aplikasi**.
   Ini cara implementasi pilihan writer, bukan kewajiban kontrak bahwa setiap keputusan harus menjadi pengaturan.
   Pengaturan per vendor didukung langsung hanya untuk laundry (M:4479). Batas yang dipakai konsisten dengan M:1678,
   M:4139–4143, dan M:4454–4479. M:1757 hanya mengatur kewajiban acceptance bila CR masuk CP6.
   - Setiap nilai default kebijakan (ACC-DEC03, 04, 05, 06 dan LAU-DEC01, 03, 05, 06) berstatus
     **`PENDING_POLICY_VALUE`** sampai owner melihat angkanya.
   - Default aman adalah **ditolak atau pending**. Default tidak boleh berupa nol, OTHER_INCOME, akun karangan, atau tarif
     karangan. Angka fixture uji tidak pernah menjadi nilai produksi.
   - Setiap pilihan diuji. Nilai nyata diisi owner saat persiapan cutover.
4. **"D06" = pengesahan lampiran ini oleh owner, setelah auditor mencocokkan rev4.** D06 adalah keputusan bagian 8
   addendum induk (batas CR aksesori/laundry), dan lampiran ini isinya. Ini tafsir writer atas kutipan, bukan makna literal
   yang pasti. D06 di sini **bukan** ACC-DEC06 (pembulatan, M:4460, M:5239) dan **bukan** kasus Auth
   ACC-D06 (M:5301). Pengesahan dokumen bukan penerimaan runtime. Penerimaan tetap lewat bukti per kasus (75 C6 + 22 ALL).
5. **CP7 tetap menunggu.** CP7 dimulai setelah CP6 sah dan owner memberi perintah CP7 (M:1694). Bila ada bagian CR yang
   dikeluarkan dari kandidat final, bagian itu didaftarkan sebagai successor sebelum consumer CP7 yang memerlukannya
   (M:1697). Dokumen ini tidak mengizinkan CP7 dan tidak menyelesaikan kewajiban CP7 (BR:510–523).

 Belum disahkan owner. Addendum induknya adalah
`ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25.md` bagian 8. Rev1 (sha256 `72621c8a…5bc0d`, commit 5d54472) sudah ditinjau
auditor dan diganti oleh revisi ini. Hasil tinjauan itu tetap tercatat di cabang auditor.

**Masukan rev2.** Sumbernya cabang `audit/cp6-final-20260924-gpt-a0bcadf`, commit a96bcaa:
- `out/fable_c6_annex_review.md`: 9 baris sesuai, 2 tidak sesuai (ACC-04 dan LAU-05), 7 sub-keputusan belum punya baris.
- `out/gpt_c6_scope_amendment.md`: ACC-04 dan LAU-05 dipecah di batas fitur; LAU-07 diganti LAU-DEC01–06; setiap CR
  dilampiri entrypoint, storage, dan status.
- `out/gpt_c6_75_case_crosswalk.md` dan `.json`: 39 kasus aksesori dan 36 kasus laundry dengan ID asli.

**Teks kontrak.** Master `ERP_V3_2_Master_Pulih_20260923.md` (M, sha256 `f21ac703…9af07`). Baris yang dipakai adalah
M:1668, M:1691–1699, M:1753–1757, M:3727–3737, M:4339–4374, M:4448–4479, dan M:5254–5307. Writer kini memegang teks M.
Keterbatasan di rev1 ("writer tidak memegang teks M") sudah tidak berlaku.

**Inventaris sumber.** Inventaris ini dibaca pada kandidat, head 1a57266. Rincian lengkap ada di bagian 5. Setiap CR diberi
entrypoint publik, storage, UI, dan status IMPLEMENTED, PARTIAL, atau ABSENT. Untuk status ABSENT, kata kunci pencarian
ikut dicatat.

## 1. Aturan yang diterapkan

1. **Temuan lama tidak boleh ditunda (M:1697).** Perilaku yang sudah ada di kandidat adalah BASELINE. Cacatnya harus
   diperbaiki di CP6. Contohnya LAU-T14 di bagian 4.
2. **Fitur baru boleh ditunda owner (M:1697).** Syaratnya, fitur itu disimpan sebagai successor terpisah sebelum consumer
   CP7 yang bergantung padanya. PASS baseline lama tidak diwariskan ke kode baru.
3. **Fitur baru yang sudah ada di kandidat (M:1757) diuji tuntas**, atau scope kandidat direvisi owner secara eksplisit.
   Tidak ada pengecualian diam-diam.
4. **Persetujuan desain tidak sama dengan fitur selesai.** Desain laundry M:3729–3737 sudah disetujui owner, tetapi
   belum diterapkan. Fitur itu tidak boleh diklaim selesai (M:1695, M:1699).
5. **Keputusan yang belum diputus hanya menahan fitur terkait (M:1695).** Status pending tidak boleh dipakai untuk
   menerima alur yang wajib final. Pengesahan dokumen bukan penerimaan runtime. GATE-16 dinilai dari scope yang sah
   ditambah bukti baseline.

Arti kolom "Kelompok":
- **BASELINE** adalah kewajiban CP6 pada perilaku yang sudah ada.
- **CR-MASUK** adalah fitur baru yang sudah ada di kandidat. Revisi ini tidak menemukan satu pun, lihat bagian 5.
- **CR-TUNDA** adalah fitur baru yang belum ada di kandidat (istilah rev1–rev2).
- **CR-CP6** adalah CR-TUNDA yang dimandatkan owner untuk CP6 (bagian 0 butir 1). Di rev4 setiap CR-TUNDA dibaca
  CR-CP6, termasuk di kolom scope crosswalk bagian 6.
- **KEBIJAKAN** adalah keputusan bisnis yang belum diputus di M §14. Yang ditahan hanya bagian yang bergantung padanya.

## 2. Aksesori

| ID | Fitur | Kelompok | Klausul | Entrypoint / storage (bagian 5) | Kasus asli |
|---|---|---|---|---|---|
| ACC-01 | Nota pengeluaran aksesori ke mandor per PCS utuh; harga eceran manual; post, hapus draf, balik; potong lewat payroll | BASELINE | M:1066–1071, M:1691 | A1: `erp_get_accessory_issue_workspace_v1`, `erp_save_accessory_issue_action_v1` | ACC-A01–A08, D01–D12 |
| ACC-02 | Hak reimburse aksesori per lot FG (GOOD × BOM, akrual) | BASELINE | M:3900–3962, M:6503 | A5: internal lewat FG/QC/rework | ACC-D01–D12 (kontrol yang terkait) |
| ACC-03 | Recost HPP aksesori setelah koreksi harga bahan | BASELINE | M:5966, M:833 | A5: `refresh_accessory_hpp_after_material_recost` (AZ) | ACC-C08 (bagian lama) |
| ACC-04a | Perilaku lama di sekitar pemakaian dan retur (lihat catatan di bawah tabel) | BASELINE | M:1668, M:1697 | A2 (backend), A1 (balik nota) | ACC-A08, B01–B07 (invarian), C03, C04, C09, D01–D12 |
| ACC-04b | Fitur baru pemakaian dan retur (lihat catatan di bawah tabel) | CR-CP6 (ABSENT; A2 hanya backend) | M:1668, M:1695 | A2 (UI/facade), A3, A4, A6: tidak ada | ACC-B01–B07 (pos/UI), C01–C12 |

**Isi ACC-04a.** Semuanya perilaku yang sudah ada dan wajib aman:
- Pembalikan nota utuh, yang ditolak setelah nota masuk payroll (20ac:6151; UI :146).
- Invarian qty, nilai, tanggal, dan lokasi pada transfer bahan (`post_material_transfer_v2`, 20am) dan penyesuaian
  pemakaian internal (`post_material_adjustment_v2`, alasan INTERNAL_FACTORY_USE dan lainnya) bila dipakai untuk
  aksesori.
- Tidak ada kasbon, reimburse, atau pendapatan palsu dari jalur itu.

**Isi ACC-04b.** Semuanya fitur baru:
- Facade publik dan UI untuk transfer, pemakaian internal, dan "pos servis" aksesori. Tipe lokasi servis juga belum ada.
- Retur aksesori dari mandor, sebagian, termasuk sesudah nota lunas atau sebagian lunas.
- Inspeksi penerimaan.
- Barang bekas atau pemulihan dengan nilai pending.
- Konversi atau pakai ulang, misalnya ganti merek atau bongkaran (M:3913, M:3925). Celup ulang BS ke SKU baru bukan
  bagian ini; itu LAU-06b.
- Servis garmen milik pelanggan.

### 2.1 Keputusan aksesori (M §14.1)

| ID | Pertanyaan (M) | Keadaan kandidat | Kelompok | Yang ditahan |
|---|---|---|---|---|
| ACC-DEC01 | Barang akhir tahun sudah kembali fisik atau baru diserahkan saat itu (M:4453) | Tidak ada jalur retur/inspeksi (A3, A4 ABSENT) | KEBIJAKAN + CR-TUNDA | Hanya ACC-04b retur/inspeksi (ACC-C11). Tanggal fisik fiktif tidak dibuat |
| ACC-DEC02 | Prorata atau tarif eceran | **Sudah diputus** (M:1066–1071): PCS persis, eceran diketik manual; diterapkan di ACC-01 | BASELINE | Tidak ada |
| ACC-DEC03 | Nilai pemulihan barang bekas dan akunnya (M:4457) | Tidak ada storage nilai pemulihan (A4 ABSENT) | KEBIJAKAN + CR-TUNDA | ACC-C05, C06, C08. Tidak boleh nol palsu atau harga barang baru otomatis |
| ACC-DEC04 | Biaya servis pelanggan vs kapitalisasi FG (M:4458) | Tidak ada jalur servis pelanggan (A6 ABSENT). Tidak ada jalur yang menambah FG/AR karena servis | KEBIJAKAN + CR-TUNDA | ACC-C10 |
| ACC-DEC05 | Retur nota setelah lunas atau sebagian: credit, carry, atau refund (M:4459) | Settlement asli dipertahankan. Balik nota ditolak setelah masuk payroll (baseline ACC-04a). Credit/carry/refund belum ada | KEBIJAKAN + CR-TUNDA | ACC-C09 (bagian baru). Blok finalisasi yang belum didukung tetap BASELINE |
| ACC-DEC06 | Pembulatan pembayaran ke rupiah bulat (M:4460) | Nominal resmi dipertahankan (harga manual 2 desimal, 20ap:520). Tidak ada baris pembulatan | KEBIJAKAN | Hanya baris pembulatan. Nominal resmi tetap BASELINE (ACC-A08 batas sen) |
| ACC-DEC07 | Role/lokasi servis dan ambang approval (M:4461) | Tidak ada tipe lokasi servis. Izin existing dipakai | KEBIJAKAN + CR-TUNDA | Pos servis ACC-04b. Kontrol izin existing ACC-D06 tetap BASELINE |
| ERP-DEC02 | Tiga kategori gratis Special dan tarif aksesori masa depan (M:4463) | Versi harga per mandor/global bertanggal ada (A7), setter privat. Belum ada flag gratis/Special; "Default gratis Mandor Special" hanya di data simulasi | KEBIJAKAN + CR-TUNDA | Kategori gratis dan UI tarif. Tidak ada kesimpulan dari nama Afui atau fixture demo |

Baris "Role, Special, volume/operasi, kanal" (M:1757) diperlakukan begini:
- Inventaris hak existing dan kontrol negatifnya adalah BASELINE (ACC-D06, LAU-T33).
- Hak baru dan angka gratis tidak dikarang.

## 3. Laundry

| ID | Fitur | Kelompok | Klausul | Entrypoint / storage (bagian 5) | Kasus asli |
|---|---|---|---|---|---|
| LAU-01 | Kirim, terima, cuci gagal, balik; QC; FG authoritative | BASELINE | M:359, M:1691, M:4479 | L1: `erp_get_laundry_qc_workspace_v1`, `erp_save_laundry_qc_action_v1`, `erp_post_final_sku_allocation_v1` | LAU-T01, T07–T15, T22–T23, T25, T27, T30–T36 |
| LAU-02 | Klaim STUCK/MISSING/DAMAGE dan kompensasi | BASELINE | M:4210 | L2: `erp_save_bs_resolution_action_v1` (SAVE_CLAIM, RESOLVE_CLAIM, REVERSE_CLAIM_RESOLUTION) | LAU-T29 |
| LAU-03 | Identitas produk BS laundry pada penerimaan fisik | BASELINE | M:359 | L1: `erp_search_laundry_bs_products_v1`, POST_RECEIPT | LAU-T25 |
| LAU-04 | Harga laundry tidak diketahui: estimasi owner dan blokir tutup buku | BASELINE (hanya perilaku blokir) | M:4475, M:4145 | L6: `erp_set_laundry_rate_owner_estimate_v1`, `erp_accounting_close_preflight_v1`, `erp_close_accounting_through_v1` (paket T3 AW; belum ada UI) | LAU-T09, T11, T12, T34 |
| LAU-05a | Master dan snapshot tarif yang sudah ada (lihat catatan di bawah tabel) | BASELINE | M:4479, M:4474 | L3, L5 (backend terkunci) | LAU-T01, T07, T08, T13, T14, T15, T31, T35 |
| LAU-05b | Perluasan laundry yang sudah disetujui, belum diterapkan (lihat catatan di bawah tabel) | CR-CP6 (ABSENT; L5 backend terkunci) | M:3729–3737, M:1668, M:1695 | L3 (penulis master), L4, L5 (draf/alokasi), L8 | LAU-T02–T06, T16–T21, T24, T26 |
| LAU-06a | Cuci ulang BS yang sudah ada: kirim ke vendor lewat SAVE_REWORK tujuan LAUNDRY, produk sama, tanpa tagihan vendor | BASELINE | M:4210 | L7: `erp_save_bs_resolution_action_v1` SAVE_REWORK/COMPLETE_REWORK | LAU-T28 (bagian lama) |
| LAU-06b | Celup ulang BS ke warna atau SKU baru | CR-CP6 tambahan dari mandat "semuanya" (ABSENT; tidak ada di M) | Tidak ada klausul M; pagar identitas di bagian 0 butir 1 | L7: tidak ada | Tidak ada (tidak ada di 36 kasus); acceptance ditulis writer dan dicocokkan auditor |

**Isi LAU-05a.** Semuanya perilaku yang sudah ada:
- Tarif per vendor × proses cuci. Tepat satu versi berlaku, ada guard overlap, dan tarif harus ≥0.
- Estimasi tercatat saat kirim. Biaya aktual tercatat saat terima, **pada tarif saat kirim** (setelah perbaikan
  LAU-T14, bagian 4).
- Akrual tetap ESTIMATED sampai invoice vendor.
- Akrual disinkronkan setelah versi tarif diedit.
- Posting invoice vendor terkunci dari semua role (20b:155–158).

**Isi LAU-05b.** Perluasan ini sudah disetujui (M:3729–3737), tetapi belum diterapkan:
- Master per vendor dengan paket harga jadi atau komponen berharga (checkbox).
- Penulis master vendor, proses, dan versi tarif.
- Invoice susulan: draf, alokasi ke kiriman dan sumber, invoice parsial, n:m, selisih, dan akun variance.
- Tarif khusus SKU.
- Diskon, pajak, pembulatan, dan borongan.

**Catatan LAU-04.**
- Kode perilaku blokirnya ada di paket T3 (AW), tidak di `supabase/migrations`, dan belum punya UI. Perilaku blokir itu
  BASELINE. Izin final sales/close baru dengan harga unknown tidak diberikan (M:4475).
- Kiriman lewat jalur connected sudah menolak tarif yang tidak ada (20ac:8940). Jadi harga unknown hanya muncul pada
  baris lama yang diberi estimasi owner.
- **Terbuka (M:1678, M:4475):** `post_sale_v2` tidak memeriksa harga laundry unknown. Laporan incomplete saja tidak
  menjawab izin posting sale. Sale final yang bergantung pada nilai laundry unknown **diblok** sampai ada aturan tertulis
  tentang cara efek finansial pending dicatat. Blok ini dibangun di BD. Fisik pending tetap boleh.

**Catatan LAU-06a/06b.**
- Cuci ulang yang ada memang tidak punya jalur biaya vendor; jurnal biaya rework hanya untuk CONTRACTOR (20av:739). Nol
  itu hasil desain, bukan harga yang hilang.
- LAU-T28 meminta fee 0 yang eksplisit dan berversi. Bila owner ingin fee cuci ulang, itu masuk LAU-05b atau LAU-06b.
- Celup ulang ke SKU baru tidak ditemukan di M, P, maupun BR. Keputusan owner lama "CR prioritas rendah, successor
  tersendiri" digantikan mandat 25 September (bagian 0 butir 1). Fitur ini tetap scope tambahan dengan pagar identitas.
  "Gratis" harus nol eksplisit yang disahkan, bukan disimpulkan dari harga kosong.

### 3.1 Keputusan laundry (M §14.2), pengganti LAU-07

Berikut hal yang **sudah jelas dan tidak ditanyakan ulang (M:4479)**:
- Master per vendor.
- Paket atau komponen.
- Proses bisa diketahui walaupun harganya belum.
- Invoice pending berbeda dari harga unknown.
- SKU opsional.
- Qty dan biaya tidak digandakan.
- Snapshot posted lama tidak ditimpa.

Persetujuan master vendor tidak dibuka ulang.

| ID | Detail yang belum ditetapkan (M) | Keadaan kandidat | Kelompok | Yang ditahan |
|---|---|---|---|---|
| LAU-DEC01 | Satuan harga vendor nyata: per PCS, per batch, minimum charge, tarif aktif (M:4472) | Hanya per PCS (`rate_per_pcs`). Tidak ada batch atau minimum | KEBIJAKAN + CR-TUNDA | Satuan batch/minimum di LAU-05b (LAU-T20, T36 per-batch). Per PCS tetap BASELINE |
| LAU-DEC02 | Dasar qty yang ditagih: GOOD, BS, missing, cuci gagal, komponen, attempt (M:4473) | Tetap, tidak bisa dikonfigurasi: estimasi = qty kirim × tarif (20ac:9099); aktual = (GOOD+BS) × tarif (20ac:9233); cuci gagal punya attempt sendiri. Delivered, returned, dan attempt disimpan terpisah | KEBIJAKAN | Konfigurasi dasar tagih per vendor (LAU-05b). Aturan tetap saat ini didokumentasikan sebagai BASELINE, bukan kebijakan final |
| LAU-DEC03 | Tanggal kesepakatan/pricing, extra, diskon, pembulatan, pajak (M:4474) | Snapshot tarif saat kirim. **Perbaikan BA 1a57266:** penerimaan tidak lagi reprice menurut tanggal kembali (LAU-T14). Extra, diskon, pajak, dan pembulatan belum ada | BASELINE (snapshot) + KEBIJAKAN (sisanya) | Extra, diskon, pajak, dan pembulatan di LAU-05b |
| LAU-DEC04 | Tindakan finansial saat harga unknown, termasuk penjualan dan closing (M:4475) | Close diblok (LAU-04). Fisik pending boleh. Sales belum memeriksa: terbuka, blok dibangun di BD (catatan LAU-04) | BASELINE (blokir) + KEBIJAKAN (izin baru) | Izin final sales/close baru |
| LAU-DEC05 | Scope override SKU: produk, ukuran, proses, fallback (M:4476) | Tidak ada `product_id` di tabel tarif. SKU tidak wajib untuk kirim/terima (LAU-T25) | KEBIJAKAN + CR-TUNDA | Tarif khusus SKU (LAU-T24, T26) |
| LAU-DEC06 | Mapping jasa, accrual, variance, dan koreksi setelah payment (M:4477) | Mapping LAUNDRY_COST, ACCRUED_MANUFACTURING, AP_VENDOR. Tidak ada akun variance. Invoice vendor terkunci | KEBIJAKAN + CR-TUNDA | Invoice susulan dan variance (LAU-T16–T18, T21–T23). Tanggal buku mengikuti ERP-DEC01/D01 |

## 4. Temuan baseline dari inventaris sumber

**LAU-T14: penerimaan reprice menurut tanggal kembali (M:4474, LAU-DEC03).**
- **Masalahnya.** POST_RECEIPT (20ac:9154–9165) memakai tarif yang berlaku pada waktu penerimaan. Versi tarif yang mulai
  di antara kirim dan kembali mengubah biaya aktual kiriman itu.
- **Status.** Ini perilaku lama, jadi tidak ditunda (M:1697).
- **Perbaikan.** Di BA (commit 1a57266), biaya aktual memakai tarif proses aktual yang berlaku saat barang dikirim.
  Estimasi kiriman dan attempt cuci gagal tetap memakai waktunya sendiri. Attempt cuci gagal adalah peristiwa jasa
  tersendiri (LAU-T27).
- **Probe.** `LAU_T14:RECEIPT_AFTER_A_LATER_RATE_VERSION` adalah temuan: tanpa BA tarifnya 9, dengan BA 7.
  `LAU_T14:RECEIPT_WITHOUT_RATE_CHANGE_CONTROL` adalah kontrolnya.

Tidak ada temuan lain dari inventaris ini. Butir-butir berikut adalah catatan, bukan temuan:
- Penutupan LAU-04 hanya ada di paket T3.
- `post_sale_v2` tanpa pemeriksaan harga laundry.
- Jalur transfer/adjustment untuk aksesori hanya ada di backend.

Auditor yang menilainya.

## 5. Inventaris sumber per fitur (kandidat head 1a57266, hanya baca)

Singkatan: FX = skema baseline `supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz`; 20xx =
`supabase/migrations/*_erp_v2_6_20xx_*.sql`; R/aw, R/az, R/ba = paket `supabase/release/cp6-t3`. Skema `erp` tidak diekspos ke
browser; fungsi `erp.*` tanpa facade `public.erp_*` bukan entrypoint browser.

| # | Status | Entrypoint publik | Implementasi / storage | UI |
|---|---|---|---|---|
| A1 Nota aksesori ke mandor | IMPLEMENTED | `erp_get_accessory_issue_workspace_v1` (20ap:549); `erp_save_accessory_issue_action_v1` (20ap:552): SAVE_DRAFT, POST, DELETE, REVERSE | `contractor_material_issues`/`_items` (FX:487/467) + `manual_retail_unit_price` (20ao:132); `contractor_accessory_price_versions` (FX:421); potong via `payroll_deductions.contractor_issue_item_id` | `ConnectedAccessoryIssuePage.tsx`; route `App.tsx:611` |
| A2 Transfer / pemakaian internal / pos servis | PARTIAL (hanya backend) | tidak ada | `post_material_transfer_v2` (20am:130), `post_material_adjustment_v2` (FX:13694; alasan INTERNAL_FACTORY_USE, PERSONAL_USE, MAINTENANCE, GIVEAWAY, FX:3377); tidak ada tipe lokasi servis (FX:3353) | tidak ada (`WarehousePages.tsx:313` data simulasi) |
| A3 Retur dari mandor; retur sesudah lunas | ABSENT (hanya balik nota utuh, ditolak setelah payroll 20ac:6151) | tidak ada | tidak ada tipe gerakan retur mandor (FX:3429) | simulasi saja (`WarehousePages.tsx:101`) |
| A4 Inspeksi, bekas/pemulihan, konversi | ABSENT | tidak ada | tidak ada | tidak ada |
| A5 Reimburse per lot FG, recost HPP aksesori | IMPLEMENTED (internal) | lewat FG/QC dan `erp_save_bs_resolution_action_v1` | `post_accessory_reimbursement_accrual` (20ac:3211), `refresh_accessory_hpp_after_material_recost` (R/az:721, jurnal `ACCESSORY_HPP_RECOST` R/az:776); `contractor_accessory_reimbursement_entitlements`, `fg_accessory_cost_snapshots`, `accessory_bom_versions` | `ConnectedBsResolutionPage.tsx:297` |
| A6 Servis pelanggan, pembulatan rupiah, role/lokasi servis | ABSENT | tidak ada | tidak ada | tidak ada |
| A7 Gratis Special, tarif aksesori masa depan | PARTIAL (model data) | tidak ada | `set_accessory_selling_price_v2` (FX:23652, privat); `contractor_accessory_price_versions` per mandor/global, bertanggal, ≥0 | simulasi saja (`MaterialMasterPages.tsx:25`) |
| L1 Kirim/terima/cuci gagal/balik, QC, FG | IMPLEMENTED | `erp_get_laundry_qc_workspace_v1` (20:4729), `erp_save_laundry_qc_action_v1` (20:4743), `erp_post_final_sku_allocation_v1` (20:4760), `erp_search_laundry_bs_products_v1` (20c:499), `erp_search_final_sku_products_v1` (20b:771) | `save_laundry_qc_action_v1` (20ac:8607; diganti BA untuk LAU-T14); `laundry_deliveries`/`_lines`, `laundry_receipts`/`_lines`, `laundry_*_batch_size_lines` (20:503/516/551), `laundry_failed_wash_attempts` (20:536) | `ConnectedLaundryPage.tsx`, `ConnectedQcFinalPage.tsx`; route `App.tsx:697/645` |
| L2 Klaim dan kompensasi | IMPLEMENTED | `erp_save_bs_resolution_action_v1` (19:1127), `erp_get_bs_resolution_workspace_v1` | `laundry_claims` (FX:1009), `resolve_laundry_claim` (20ac:6095), `reverse_laundry_claim_resolution` (20ac:6436) | `ConnectedBsResolutionPage.tsx:101–156, 311–331`; route `App.tsx:665` |
| L3 Master vendor, proses, versi tarif | PARTIAL: baca saja | tidak ada penulis master (vendor hanya lewat impor awal 20ap:2065) | `laundry_vendors` (FX:1135), `wash_processes` (FX:2375), `laundry_vendor_rate_versions` (FX:1122, guard overlap FX:9681); `apply_bulk_rate_change` privat | peringatan "master belum lengkap" `ConnectedLaundryPage.tsx:89` |
| L4 Paket vs komponen | ABSENT | tidak ada | tarif hanya per vendor × proses | tidak ada |
| L5 Invoice susulan, alokasi, variance | PARTIAL (backend terkunci) | tidak ada | `post_vendor_invoice` (20ac:5670) dan `reverse_vendor_invoice` dicabut dari semua role (20b:155–158); `vendor_invoices`/`_items` (FX:2341/2326); akrual `laundry_cost_accrual_state` (FX:1041); tidak ada penulis draf invoice | tidak ada |
| L6 Harga unknown: estimasi owner, blokir tutup | PARTIAL (paket T3 saja) | `erp_set_laundry_rate_owner_estimate_v1` (R/aw:1063), `erp_accounting_close_preflight_v1` (R/aw:1039), `erp_close_accounting_through_v1` (R/aw:1047) | `laundry_rate_owner_estimates_v1` (R/aw:189); blocker LAUNDRY_PRICE_UNKNOWN (R/aw:649) | tidak ada |
| L7 Cuci ulang; celup ulang | Cuci ulang IMPLEMENTED; celup ulang ABSENT | SAVE_REWORK tujuan LAUNDRY (19:928) | `rework_orders` (FX:2037), `post_rework_completion` (20av:646; produk sama, tanpa jurnal biaya vendor); `product_conversions` tidak terhubung ke laundry | `ConnectedBsResolutionPage.tsx:253, 283, 299–307` |
| L8 Dasar qty tagih, tanggal kesepakatan, override SKU | Aturan tetap; tidak bisa dikonfigurasi | tidak ada | estimasi = kirim × tarif (20ac:9099); aktual = (GOOD+BS) × tarif (20ac:9233), tarif saat kirim (BA); tidak ada kolom tanggal kesepakatan atau `product_id` di tarif | tidak ada |

Kata kunci pencarian untuk ABSENT (Indonesia dan Inggris):
- **A3:** retur aksesori, retur mandor, accessory_return, CONTRACTOR_RETURN, MANDOR_RETURN, credit_note, carry_forward.
- **A4:** inspeksi, receipt_inspection, bekas, pemulihan, recovery_value, salvage, reuse, rekondisi, used_accessory.
- **A6:** servis pelanggan, service_fee, kapitalisasi, pembulatan, round_to_rupiah, service_location, approval_threshold.
- **A7:** gratis, is_free, afui, Mandor Special.
- **L4:** paket, laundry_package, laundry_component, wash_component, bundle.
- **L5:** invoice susulan, pending_invoice, invoice_allocation, tagihan laundry.
- **L7:** celup ulang, recolor, redye, warna baru.
- **L8:** billing_basis, agreement, kesepakatan, sku_rate, rate_override.

Pencarian ini mencakup `src/`, `supabase/migrations`, `supabase/dev`, paket T3, dan FX.

**CR-MASUK: tidak ada.** Semua fitur baru di atas berstatus ABSENT, atau hanya ada di backend yang tidak terjangkau:
- tanpa facade publik (A2, A7 setter), atau
- dicabut dari semua role (L5).

Bila auditor menemukan fitur baru yang terjangkau, baris itu dipindah ke CR-MASUK. Owner lalu memilih: diuji tuntas, atau
kandidat direvisi (addendum bagian 8, aturan 4).

## 6. Crosswalk 75 kasus asli

Tabel ini daftar cakupan, bukan 75 hasil uji.
- Semua kasus tetap **UNVERIFIED** sampai auditor menautkan hasil kandidat, fixture, dan oracle yang tepat.
- Kolom "Bukti parsial" hanya penunjuk untuk auditor; isinya tidak berarti PASS.
- ID asli dan baris M dipertahankan dari `out/gpt_c6_75_case_crosswalk.json`.

### 6.1 Laundry (M:4339–4374)

| Kasus | M | Baris C6 rev2 | Scope | Entrypoint yang diuji | Bukti parsial |
|---|---|---|---|---|---|
| LAU-T01 | 4339 | LAU-01, LAU-05a | BASELINE (tarif per vendor × proses) | POST_DELIVERY/POST_RECEIPT | — |
| LAU-T02 | 4340 | LAU-05b | CR-TUNDA | tidak ada | — |
| LAU-T03 | 4341 | LAU-05b | CR-TUNDA | tidak ada | — |
| LAU-T04 | 4342 | LAU-05b | CR-TUNDA | tidak ada | — |
| LAU-T05 | 4343 | LAU-05b | CR-TUNDA | tidak ada | — |
| LAU-T06 | 4344 | LAU-05b | CR-TUNDA | tidak ada | — |
| LAU-T07 | 4345 | LAU-05a | BASELINE (transaksi posted lama tetap) | POST_RECEIPT setelah versi tarif baru | BA probe LAU_T14 |
| LAU-T08 | 4346 | LAU-05a | BASELINE | versi tarif (CHECK ≥0 FX:3351) | — |
| LAU-T09 | 4347 | LAU-04, LAU-DEC04 | BASELINE (unknown bukan nol) + KEBIJAKAN | `erp_set_laundry_rate_owner_estimate_v1` | AW T1 P-02 |
| LAU-T10 | 4348 | LAU-05a, LAU-DEC06 | BASELINE (ESTIMATED sampai invoice) + CR-TUNDA (invoice) | POST_RECEIPT, akrual | — |
| LAU-T11 | 4349 | LAU-04, LAU-06a | BASELINE (nol diketahui ≠ null) | owner estimate, rework | — |
| LAU-T12 | 4350 | LAU-05b, LAU-04 | CR-TUNDA (komponen) + BASELINE (laporan pending) | preflight | — |
| LAU-T13 | 4351 | LAU-05a | BASELINE (error bukan unknown/fallback) | workspace laundry | W13 (KPI unknown) |
| LAU-T14 | 4352 | LAU-05a, LAU-DEC03 | BASELINE | POST_RECEIPT | BA probe LAU_T14 (commit 1a57266) |
| LAU-T15 | 4353 | LAU-05a | BASELINE (proses aktual tertaut) | POST_RECEIPT dengan proses lain | T2 (AL mixed rates) |
| LAU-T16 | 4354 | LAU-05b, LAU-DEC06 | CR-TUNDA | tidak ada | — |
| LAU-T17 | 4355 | LAU-05b | CR-TUNDA | tidak ada | — |
| LAU-T18 | 4356 | LAU-05b | CR-TUNDA | tidak ada | — |
| LAU-T19 | 4357 | LAU-05b, LAU-01 | CR-TUNDA (tagih) + BASELINE (kapasitas sumber kirim/terima) | POST_RECEIPT kapasitas | — |
| LAU-T20 | 4358 | LAU-05b, LAU-DEC01 | CR-TUNDA | tidak ada | — |
| LAU-T21 | 4359 | LAU-05b | CR-TUNDA | tidak ada | — |
| LAU-T22 | 4360 | LAU-01, LAU-05b | BASELINE (turunan biaya estimasi) + CR-TUNDA (invoice final) | akrual laundry → FG/COGS | — |
| LAU-T23 | 4361 | LAU-01, LAU-05b | BASELINE (fisik dan histori tetap) + CR-TUNDA | — | — |
| LAU-T24 | 4362 | LAU-05b, LAU-DEC05 | CR-TUNDA | tidak ada | — |
| LAU-T25 | 4363 | LAU-01, LAU-03 | BASELINE | POST_DELIVERY/RECEIPT/FINAL_SKU tanpa SKU | T3 browser AU (10 kasus WIP) |
| LAU-T26 | 4364 | LAU-05b, LAU-DEC05 | CR-TUNDA | tidak ada | — |
| LAU-T27 | 4365 | LAU-01 | BASELINE | POST_FAILED_WASH, retry HTTP | — |
| LAU-T28 | 4366 | LAU-06a, LAU-06b | BASELINE (cuci ulang tanpa tagihan) + CR-TUNDA (fee cuci ulang/celup) | SAVE_REWORK LAUNDRY | — |
| LAU-T29 | 4367 | LAU-02 | BASELINE | SAVE_CLAIM/RESOLVE_CLAIM + penerimaan terlambat | A5 (selector klaim) |
| LAU-T30 | 4368 | LAU-01 | BASELINE | dua sesi pada sumber yang sama | T2 AR (`cp6_laundry_qc_concurrency`) |
| LAU-T31 | 4369 | LAU-01, LAU-05a | BASELINE | STALE_VERSION pada aksi laundry | — |
| LAU-T32 | 4370 | LAU-01 | BASELINE | envelope request laundry (halaman connected) | — |
| LAU-T33 | 4371 | LAU-01, LAU-02 | BASELINE | Auth/HTTP per role | matriks HTTP auditor (10 facade × 4 role) |
| LAU-T34 | 4372 | LAU-04 | BASELINE | preflight/close | AW T1 P-02, P07 |
| LAU-T35 | 4373 | LAU-01, LAU-05a | BASELINE | paket T3, rollback | T3 paket + rollback 127/127 |
| LAU-T36 | 4374 | LAU-01, LAU-05b | BASELINE (UI existing) + CR-TUNDA (per batch, mode vendor) | UI laundry desktop/HP | T3 browser AU |

### 6.2 Aksesori (M:5254–5307)

| Kasus | M | Baris C6 rev2 | Scope | Entrypoint yang diuji | Bukti parsial |
|---|---|---|---|---|---|
| ACC-A01 | 5254 | ACC-01 | BASELINE | `erp_save_accessory_issue_action_v1` | oracle auditor "7 PCS eceran persis" |
| ACC-A02 | 5255 | ACC-01 | BASELINE | POST | oracle auditor "7 PCS" |
| ACC-A03 | 5256 | ACC-01 | BASELINE | quote/POST (hanya PCS/COUNT, 20ap:385) | — |
| ACC-A04 | 5257 | ACC-01 | BASELINE | validator `accessoryIssue.ts:66–78` + RPC | — |
| ACC-A05 | 5258 | ACC-01 | BASELINE (meter/kg tetap desimal) | quote | — |
| ACC-A06 | 5259 | ACC-01 | BASELINE | SAVE_DRAFT/POST stale | — |
| ACC-A07 | 5260 | ACC-01 | BASELINE | nota legacy + upgrade | T3 paket |
| ACC-A08 | 5261 | ACC-01, ACC-04a, ACC-04b | BASELINE (multi-line, balik penuh, sen) + CR-TUNDA (retur sebagian berulang) | POST/REVERSE | — |
| ACC-B01 | 5267 | ACC-04a, ACC-04b | BASELINE (invarian transfer) + CR-TUNDA (pos servis) | `post_material_transfer_v2` (backend) | — |
| ACC-B02 | 5268 | ACC-04a, ACC-04b | idem | adjustment/transfer (backend) | — |
| ACC-B03 | 5269 | ACC-04a | BASELINE | `post_material_adjustment_v2` INTERNAL_FACTORY_USE (backend) | — |
| ACC-B04 | 5270 | ACC-04a | BASELINE | transfer backdate (20am) | A9 S04 (transfer backdate bahan) |
| ACC-B05 | 5271 | ACC-04a | BASELINE | transfer lokasi tidak sah | — |
| ACC-B06 | 5272 | ACC-04a | BASELINE | adjustment opname | — |
| ACC-B07 | 5273 | ACC-04a, ACC-04b | BASELINE (alur existing) + CR-TUNDA (retur/settlement baru) | pembelian → transfer → nota → laporan | — |
| ACC-C01 | 5279 | ACC-04b | CR-TUNDA | tidak ada | — |
| ACC-C02 | 5280 | ACC-04b | CR-TUNDA | tidak ada | — |
| ACC-C03 | 5281 | ACC-04a, ACC-04b | BASELINE (kapasitas sumber existing) + CR-TUNDA | REVERSE nota ulang | — |
| ACC-C04 | 5282 | ACC-04a, ACC-04b | BASELINE (efek finansial per sumber existing) + CR-TUNDA | — | — |
| ACC-C05 | 5283 | ACC-04b, ACC-DEC03 | CR-TUNDA + KEBIJAKAN | tidak ada | — |
| ACC-C06 | 5284 | ACC-04b, ACC-DEC03 | CR-TUNDA + KEBIJAKAN | tidak ada | — |
| ACC-C07 | 5285 | ACC-04b | CR-TUNDA | tidak ada | — |
| ACC-C08 | 5286 | ACC-03, ACC-04b | BASELINE (recost tertaut existing) + CR-TUNDA | recost AZ | AZ T1 |
| ACC-C09 | 5287 | ACC-04a, ACC-DEC05 | BASELINE (balik ditolak setelah payroll) + KEBIJAKAN/CR-TUNDA | REVERSE setelah payroll | — |
| ACC-C10 | 5288 | ACC-04b, ACC-DEC04 | CR-TUNDA + KEBIJAKAN | tidak ada | — |
| ACC-C11 | 5289 | ACC-04b, ACC-DEC01 | CR-TUNDA + KEBIJAKAN | tidak ada | — |
| ACC-C12 | 5290 | ACC-04a | BASELINE (opname tanpa nota palsu) | adjustment/impor awal | — |
| ACC-D01 | 5296 | ACC-01, ACC-04a | BASELINE | dua sesi POST nota | — |
| ACC-D02 | 5297 | ACC-01, ACC-04a | BASELINE | transfer vs nota (backend) | — |
| ACC-D03 | 5298 | ACC-01 | BASELINE | POST vs SAVE_DRAFT | — |
| ACC-D04 | 5299 | ACC-01, ACC-04a | BASELINE (balik vs payroll) + CR-TUNDA (retur/inspeksi) | REVERSE vs payroll | — |
| ACC-D05 | 5300 | ACC-01 | BASELINE | replay/mismatch kunci | — |
| ACC-D06 | 5301 | ACC-01, ACC-02 | BASELINE | Auth/HTTP per role | matriks HTTP auditor |
| ACC-D07 | 5302 | ACC-01 | BASELINE | gagal di tengah multi-line | — |
| ACC-D08 | 5303 | ACC-01 | BASELINE | tanggal WIB/backdate/closed | A2 helper WIB |
| ACC-D09 | 5304 | ACC-01 | BASELINE | UI desktop/HP | — |
| ACC-D10 | 5305 | ACC-01 | BASELINE | refetch gagal sesudah commit | — |
| ACC-D11 | 5306 | ACC-01, ACC-02, ACC-03 | BASELINE | paket T3, rollback | T3 paket + rollback 127/127 |
| ACC-D12 | 5307 | ACC-01 | BASELINE | pencarian/pagination server | A5 selector |

Ringkasan scope, dihitung dari tabel di atas:
- **Laundry:**
  - BASELINE penuh: 17 kasus (T01, T07–T09, T11, T13–T15, T25, T27, T29–T35).
  - Campuran BASELINE dan CR-TUNDA: 7 kasus (T10, T12, T19, T22, T23, T28, T36).
  - CR-TUNDA penuh: 12 kasus (T02–T06, T16–T18, T20, T21, T24, T26).
  - Total 36.
- **Aksesori:**
  - BASELINE penuh: 23 kasus (A01–A07, B03–B06, C12, D01–D03, D05–D12).
  - Campuran: 9 kasus (A08, B01, B02, B07, C03, C04, C08, C09, D04).
  - CR-TUNDA, ada yang disertai KEBIJAKAN: 7 kasus (C01, C02, C05, C06, C07, C10, C11).
  - Total 39.

Auditor diminta mencocokkan hitungan ini dengan JSON.

## 7. Yang diminta

1. **Auditor:**
   - Cocokkan rev4 dengan M, P, BR, `out/r9_scope_contract.md`, dan bagian 5a Fable.
   - Tautkan bukti per kasus di bagian 6 setelah BC, BD, dan BE dibangun.
   - Pindahkan baris yang ternyata CR-MASUK.
2. **Owner, pengesahan "D06" atas rev4.** Yang disahkan:
   - ☑ bagian 0 butir 1–5, termasuk LAU-06b sebagai scope tambahan dengan pagar identitas;
   - ☑ semua nilai kebijakan tetap `PENDING_POLICY_VALUE` (default ditolak/pending) sampai owner melihat angkanya;
   - ☑ penerimaan runtime tetap lewat bukti per kasus, bukan lewat pengesahan ini.

Nilai kebijakan (ACC-DEC01, 03–07, ERP-DEC02, LAU-DEC01–06) **tidak perlu diputus sekarang.** Keputusannya hanya menahan
fitur terkait. Owner mengisi nilainya saat persiapan cutover, kecuali ingin memutus sekarang.

## 8. Perubahan rev4 terhadap rev3

| Butir T1 | Perubahan |
|---|---|
| (a) | Sitasi pengaturan kebijakan: "sesuai M:1757" diganti "konsisten dengan M:1678, M:4139–4143, M:4454–4479". M:1757 hanya kewajiban acceptance CR yang masuk CP6. |
| (b) | Bagian 0 butir 1 dipisah: konversi ganti merek + aksesori (M:3913, M:3925) di ACC-04b; celup ulang BS → SKU baru = LAU-06b, scope tambahan dari mandat "semuanya", dengan pagar identitas produk. |
| (c) | "D06" ditulis eksplisit sebagai pengesahan lampiran ini, bukan ACC-DEC06 atau kasus Auth ACC-D06. |
| (d) | Nilai default ACC-DEC03/04/05/06 dan LAU-DEC01/03/05/06 = `PENDING_POLICY_VALUE`; default aman = ditolak/pending, tidak nol/OTHER_INCOME/tarif karangan. |
| (e) | LAU-04: `post_sale_v2` tanpa cek harga laundry unknown dicatat **terbuka**; sale final yang bergantung nilai unknown diblok (dibangun di BD). |
| (f) | Label W05 di BB = PARTIAL (hanya finansial). |
| GPT §2 | Sitasi M:369–379/M:930–938 untuk 22 keadaan dicabut; hitungan 9/6/7 = inventaris writer, `UNVERIFIED`. |
| GPT §7 | Butir 5 baru: CP7 tetap menunggu CP6 sah dan perintah owner; bagian CR yang dikeluarkan menjadi successor sebelum consumer CP7. |
| GPT §4 | M:5236 (D03) tidak dipakai untuk transformasi SKU. |

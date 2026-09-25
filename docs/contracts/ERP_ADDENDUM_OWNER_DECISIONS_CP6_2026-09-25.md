# Addendum keputusan owner CP6 — ERP-ADD-CP6-2026-09-25-01

**Status: D01–D05 disahkan tertulis oleh owner (25 September 2026, kutipan di bagian 9). D06 tetap OWNER_CONFIRMED_CHAT
sampai lampiran C6 ditinjau auditor dan disahkan owner.**
Addendum ini tidak mengubah teks ketiga kontrak. Isinya memperjelas cara menerapkan klausul yang dirujuk untuk keputusan
D01–D06. Sampai owner mengesahkannya secara tertulis (bagian 9), label setiap keputusan tetap OWNER_CONFIRMED_CHAT.
CP6 tetap HOLD, `production_go=false`, dan 12 butir HOLD historis tetap HOLD.

## 1. Kontrak acuan

| Kode | Berkas | SHA-256 (dicatat auditor di `AUDIT_PROGRESS.md`) |
|---|---|---|
| M | `ERP_V3_2_Master_Pulih_20260923.md` | `f21ac70360915a1f1021b42a3918e862ca7d11cf88c1b90c5627b4490c69af07` |
| P | `ERP_V3_2_Perubahan_Pulih_20260923.md` | `92966cd6ed27e64123be6c52e2263bfbdb3db91c97f2e441c3bdc98589397676` |
| BR | `ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md` | `4566ab6f1c8e53bc21c70c0c777f780b526305815e04d5913a5c858dfaa85886` (hanya batas CP6/CP7) |

Nomor baris (mis. M:3820) mengikuti rujukan auditor di `OWNER_DECISIONS_CP6_DRAFT.md`. Writer tidak memegang salinan
ketiga kontrak. Kutipan di bawah hanya kalimat yang dikutip auditor. Auditor diminta mencocokkan isi dan hash.

## 2. Asal keputusan

- Usulan: `OWNER_DECISIONS_CP6_DRAFT.md` pada branch auditor `audit/cp6-final-20260924-gpt-a0bcadf`, commit
  `8d3ee4c050c969e11d5f78c287d63389d48fe69c`. Rekomendasi A untuk D01–D06.
- Konfirmasi owner: di sesi audit Fable, 25 Sep 2026 sekitar 01:25 UTC, owner menulis "Ya, semua sesuai usulan". Ini
  berlaku untuk D01–D06, termasuk akun lawan AX = pendapatan lain-lain (OTHER_INCOME).
- Diteruskan ke writer: di sesi writer pada 25 Sep 2026, dengan pesan "D01–D06 semua pilihan A, termasuk akun lawan AX
  = pendapatan lain-lain".
- Keputusan sebelumnya yang tetap berlaku (tidak diubah addendum ini):
  - 24 Sep, prinsip WIP: max(tanggal ekonomi invoice, tanggal fisik potong) selama tanggal ekonomi masih terbuka.
  - 24 Sep, 8 kasus AS mengikuti prinsip WIP.
  - 24 Sep, opsi 1: invoice yang bertanggal sebelum penerimaan dibukukan pada hari penerimaan, dan tanggal invoice
    tetap menjadi tanggal dokumen.
  - 24 Sep: upah perbaikan BS temuan di atas Rp0 menjadi utang yang dibayar lewat payroll.
  - Aturan yang sudah ada di kontrak juga tetap berlaku: ALL (M:1024), draf yang di-prepare (M:1025, M:3817), dasar
    tanggal invoice (M:1022, M:1059–1065), dan aksesori 7 PCS (M:44, M:1023).

## 3. D01 — Tanggal koreksi mengikuti posisi nyata barang (pilihan A)

Klausul yang diperjelas: M:1022, M:1059–1065, M:3816, M:3820 ("Backdate tidak boleh merusak prefix qty/value pada
timeline"), M:3825, M:6148–6162.

Aturan (C1):

1. **Tanggal dokumen.** Tanggal invoice tetap tanggal dokumen dan tanggal ekonomi E. Jurnal invoice pemasok berada pada
   E. Pengecualiannya opsi 1 (24 Sep): E yang lebih awal dari penerimaan dibukukan pada hari penerimaan.
2. **Periode terbuka.** Selisih biaya dibawa oleh unit ke tempat unit itu benar-benar berada. Untuk setiap perpindahan
   sah (potong, keluar ke kontraktor, retur pemasok, penyesuaian, selesai jadi FG, jual, retur jual), bagian selisihnya
   bertanggal max(E, tanggal bisnis perpindahan). Tanggal ini tidak melewati hari ini.
   - Selisih tidak pernah masuk WIP sebelum bahan dipakai.
   - Selisih tidak masuk FG sebelum barang selesai.
   - Selisih tidak masuk HPP penjualan sebelum barang terjual.
   - Nominal per unit tidak berubah dan tidak dihitung dua kali.
3. **Hari ADJUSTMENT_DATE untuk bahan.**
   - Kuantitas penyesuaian tetap pada waktu fisik kejadiannya.
   - Koreksi nilai yang datang belakangan bertanggal max(E, tanggal penyesuaian) selama E terbuka.
   - Write-off yang kemudian dibatalkan membawa nilai hasil hitung ulang sejak hari write-off sampai hari pembatalannya.
4. **Batas periode tertutup.** Bila E sudah tertutup, semua bagian koreksi memakai tanggal ekonomi E dan dibukukan pada
   hari pengakuan di periode terbuka (controlled adjustment, satu jurnal per bagian). Aturan ini juga berlaku bila
   penerimaannya tertutup tetapi tahap berikutnya (potong, selesai, jual) jatuh di hari yang masih terbuka.
   - Tidak ada bagian yang dipindah ke hari terbuka sebelum hari pengakuan. Alasannya, bahan baru menerima koreksi pada
     hari pengakuan.
   - Filing dan snapshot yang sudah ditutup tidak ditimpa. Laporan menandai `changed_since_filing`.
   - Ini aturan yang sudah dijalankan kandidat (AY/AZ). **Owner diminta menegaskannya secara tertulis sebagai expected
     untuk kasus batas ini.**
5. **Penyajian lintas periode.** Laporan pada tanggal D memakai fakta terkoreksi yang bertanggal ≤ D. Dokumen dan
   filing lama tetap tidak berubah.

Pelaksanaan: AY rev7.4 dan AZ rev2.x (`supabase/dev/cp6_ay_t1_family.sql`, `supabase/dev/cp6_az_t1_family.sql`,
T3 `…20ay…`, `…20az…`). Bukti keluarga: probe T1 AZ (29 kasus). Setelah addendum ini ada, auditor menulis oracle untuk
25 kasus T2: 8 AS, 12 kalender, 4 AO, dan 1 ADJUSTMENT_DATE. Hasil beku lama tetap tercatat.

## 4. D02 — Kapasitas saldo mengikuti tanggal pemakaiannya (pilihan A)

Klausul yang diperjelas: M:629–646 ("koreksi/reversal yang membuat kapasitas kurang ditolak"), M:3816, M:3820, M:3825,
M:6008–6021, M:6152, BR:271, BR:375.

Aturan:

1. **Uang muka saldo awal** (pemasok, pelanggan, vendor laundry).
   - Operasi yang menurunkan sisa uang muka hanya boleh memakai kapasitas yang ada pada tanggal operasi itu. Sisa pada
     setiap hari sesudahnya juga tidak boleh negatif.
   - Operasi yang dimaksud: pemakaian/alokasi ke tagihan (APPLY), refund, koreksi yang menurunkan, dan pembatalan koreksi
     yang menaikkan.
   - Penambahan yang bertanggal lebih akhir tidak membiayai pemakaian yang lebih awal.
   - Sisa per tanggal dibaca dari baris akun uang muka milik transaksi uang muka itu (tanggal ekonomi), di atas saldo
     awalnya. Ini sama dengan cara auditor membaca saldo per tanggal.
   - Contoh: saldo 67,25; koreksi efektif 22 Sep menjadi 100; refund 100 bertanggal 21 Sep ditolak. Refund pada atau
     setelah 22 Sep boleh bila tidak ada pemakaian lain.
   - Operasi yang menaikkan kapasitas tidak diperiksa: koreksi naik, dan pembatalan pemakaian (REVERSE_PAYMENT).
   - Produk tidak memiliki reservasi uang muka yang terpisah. Pemakaian adalah APPLY.
2. **Stok (AUD-S04).** Aturan yang sama untuk stok sudah ditegakkan sebelum addendum ini:
   - Stok bahan: hitung ulang biaya bahan (AO `erp._recalculate_material_cost_core`) menolak setiap gerakan yang membuat
     riwayat efektif satu gudang/roll negatif, dengan kode `AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY`.
     Contohnya transfer keluar gudang yang bertanggal sebelum barang tiba di gudang itu.
   - Stok barang jadi: diperiksa per SKU dan lot, prefix demi prefix (AW P-04).
   - Bukti: probe T1 BA run 36085934997 fase "before" menunjukkan penolakan itu terjadi tanpa BA. BA tidak mengubah
     guard stok.
3. **Penolakan.** Semua penolakan bersifat atomik, tanpa perubahan ledger. Kodenya:
   - `BA_ADVANCE_DATED_CAPACITY` untuk uang muka;
   - `AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY` untuk stok bahan (sudah ada).
4. **Kesalahan tanggal.** Bila tanggal koreksi ternyata salah, perbaikannya lewat koreksi fakta yang tertaut dan
   diaudit, bukan dengan meminjam kapasitas masa depan.

Pelaksanaan: family BA (`supabase/dev/cp6_ba_t1_family.sql`):
- `erp.initial_prepayment_dated_floor_v1`;
- `erp.manage_initial_prepayment_v1`.

Bukti: probe T1 BA. Kasus A9 REFUND/APPLY × pemasok/pelanggan/vendor, masing-masing DATED_CAPACITY dan
ORDERED_CONTROL, ditambah S04 sebelum/sesudah barang tiba (kontrol regresi). Auditor menjalankan ulang
`business_scenarios_reconstructed.py`.

## 5. D03 — Produk pada WIP saldo awal mengikat bila diisi (pilihan A)

Klausul yang diperjelas: M:359–379, M:3822.

Aturan:

1. **Produk diisi pada sumber WIP awal.** Hasilnya harus identitas produk yang sama. Versi produk yang berlaku pada
   tanggal hasil diperbolehkan, dengan akar identitas yang sama. Produk, merek, warna, atau ukuran lain ditolak dengan
   `BA_WIP_OUTPUT_PRODUCT_BOUND`.
2. **Produk kosong.** Hasil ditetapkan saat penyelesaian (boundary yang sah).
   - Model PO dan ukuran selalu dicocokkan.
   - Merek dan warna yang tertulis di baris sumber harus cocok. Bila tidak cocok, ditolak dengan
     `BA_WIP_OUTPUT_SOURCE_MISMATCH`.
3. **Pencatatan provenance.** Setiap hasil mencatat dasar penetapannya: `OPENING_PRODUCT`, `SOURCE_ATTRIBUTES`, atau
   `ASSIGNED_AT_COMPLETION`. Tercatat juga apa yang diperiksa dan apa yang tidak diketahui (tabel
   `erp.initial_import_wip_output_identity_v1`).
   - Data yang tidak diketahui dicatat sebagai tidak diketahui, bukan sebagai cocok. Contohnya pola dan bahan (sumber WIP
     impor tidak memuatnya), serta merek/warna yang tidak diisi.
   - Ini tafsiran writer atas kalimat "Data yang belum diketahui tidak dianggap cocok otomatis". **Owner diminta
     menegaskannya.**
4. **Mengubah tujuan.** Tujuan sumber yang sudah posted tidak boleh diubah lewat penyelesaian. Perubahan produk setelah
   selesai memakai jalur konversi yang tertaut.

Pelaksanaan: family BA, `erp.complete_initial_import_wip_v1`. Bukti: probe T1 BA, kasus A10 (dua penolakan, tiga
kontrol). Auditor menjalankan ulang SI-01.

## 6. D04 — Masalah menahan tanggal yang terbukti terdampak (pilihan A, dengan syarat auditor)

Klausul yang diperjelas: M:3825, M:5100.

Aturan (C4):

1. **Cek yang dibatasi per tanggal.** Hanya cek yang garis tanggalnya terbukti:
   - Detektor bertanggal milik mesin close: `GL_INVENTORY_NEGATIVE_ASOF`, `FG_QTY_NEGATIVE_ASOF`,
     `MATERIAL_QTY_NEGATIVE_ASOF`, `RECOST_PENDING`, `RECOST_FAILED_EXHAUSTED`, `ATTENDANCE_CELL_MISSING`,
     `ATTENDANCE_CELL_REVERSED_UNREPLACED`, `PAYROLL_NOT_APPROVED`, `PAYROLL_WORK_UNCOVERED`,
     `PAYROLL_ATTENDANCE_UNCOVERED`, `LAUNDRY_PRICE_UNKNOWN`, `LAUNDRY_PRICE_INVALID`, `GRNI_ESTIMATE_OPEN`.
   - Dua cek current-state yang setara dengan detektor bertanggal: `NEGATIVE_FG_BALANCE` → `FG_QTY_NEGATIVE_ASOF` dan
     `NEGATIVE_MATERIAL_LOCATION_BALANCE` → `MATERIAL_QTY_NEGATIVE_ASOF`. Keduanya menjadi INFO
     (`SCOPED_BY_DATED_DETECTOR`) hanya bila setiap kunci yang gagal ditemukan juga oleh detektornya.
   - `V268_COST_RECALC_EXHAUSTED` ditangani per tanggal oleh keluarga RECOST. Baris non-PO dan PO tanpa fakta bertanggal
     tetap memblokir semua tanggal (`RECOST_UNSCOPED_ENTITY`).
2. **Semua cek lain tetap memblokir semua tanggal** (`BLOCKS_EVERY_DATE`, perilaku sekarang):
   - 94 cek DATABLE yang garis tanggalnya belum dibuktikan;
   - 9 cek SYSTEMIC;
   - 2 cek UNCERTAIN;
   - setiap nama yang belum terdaftar (`UNCLASSIFIED`).
   Daftar lengkapnya ada di `scripts/cp6_aw_integrity_registry.sql` dan
   `docs/evidence/cp6-aw/p03_integrity_check_classification.md`.
3. **Menambah cek per tanggal.** Sebuah cek DATABLE baru boleh dibatasi per tanggal hanya setelah garis tanggalnya
   dibuktikan per kunci, lalu dicatat di registry dan ditinjau auditor.

Pelaksanaan: AW (tidak berubah oleh addendum ini).

## 7. D05 — Barang jadi nyata tanpa sumber produksi (pilihan A) dan akun lawan

Klausul yang diperjelas: M:3816, M:3818, M:3822–3825.

Aturan:

1. **Lot non-PO.** Dicatat dengan asal, pemeriksaan, pelaku, alasan, qty, dan waktu fisik. Tidak ada produksi, upah,
   atau reimbursement PO yang diciptakan.
2. **Nilai.**
   - Nilai mengikuti pembanding HPP yang sah pada tanggal fisik.
   - Bila tidak ada pembanding, owner mengisi nilai dan alasannya. Nol hanya boleh bila dipilih secara eksplisit.
   - Bila pembanding sah ada, nol eksplisit ditolak dan tidak ada override bebas.
3. **Akun lawan: pendapatan lain-lain (OTHER_INCOME) — disahkan owner.**

Pelaksanaan: AX (tidak berubah). Bukti yang sudah lulus oracle auditor: `fg_acc_1`.

## 8. D06 — Batas change request aksesori/laundry (pilihan A)

Klausul yang diperjelas: M:1691–1699, M:1753–1757, M:4448–4479.

Aturan:

1. **Kewajiban CP6 diselesaikan di CP6.** Termasuk bug baseline, kelengkapan ALL, 7 PCS, jalur lifecycle, dan perilaku
   kandidat yang diteruskan.
2. **CR tambahan dipisah.** CR yang belum masuk baseline dipisah sebagai kelanjutan, sebelum consumer CP7 yang
   bergantung padanya. Bug baseline tidak boleh ditunda dengan menyebutnya CR.
3. **Daftar acceptance ID per fitur (C6).** Isinya: baseline CP6, CR yang sudah masuk kandidat, CR yang ditunda, dan
   dependensi CP7. Daftar ini disusun writer, ditinjau auditor, lalu disahkan owner sebagai lampiran addendum ini.
   **Status: draf usulan writer** di `ERP_ADDENDUM_OWNER_DECISIONS_CP6_2026-09-25_LAMPIRAN_C6.md`, menunggu
   tinjauan auditor terhadap M:1691–1699, M:1753–1757, dan M:4448–4479.
4. **Butir yang sudah masuk kandidat** tidak boleh diam-diam diberi N/A. Owner memilih salah satu: diuji tuntas, atau
   kandidat direvisi secara eksplisit.

## 9. Pengesahan tertulis owner

Owner diminta menandai salah satu pilihan per keputusan. Hash addendum yang disahkan dicatat oleh auditor.

| ID | Sah seperti tertulis | Sah dengan catatan (tulis klausulnya) |
|---|---|---|
| D01 (termasuk aturan batas periode tertutup 3.4) | ☑ | ☐ |
| D02 | ☑ | ☐ |
| D03 (termasuk pencatatan "tidak diketahui" 5.3) | ☑ | ☐ |
| D04 | ☑ | ☐ |
| D05 (akun lawan OTHER_INCOME) | ☑ | ☐ |
| D06 (termasuk lampiran C6 setelah ditinjau auditor) | ☐ menunggu tinjauan auditor atas lampiran C6 | ☐ |

Nama/tanda tangan owner: pengesahan tertulis owner di chat sesi writer Claude (kutipan apa adanya di bawah).
Tanggal: 25 September 2026.

Catatan pengesahan (dicatat writer Claude, dicocokkan auditor):
- Usulan writer di chat: "D01–D05 sah seperti tertulis, termasuk 3.4 dan 5.3. D06 menunggu tinjauan auditor atas
  lampiran C6."
- Jawaban owner, apa adanya: "sah bos".
- Teks yang disahkan: bagian 1–8 berkas ini sama persis dengan versi sha256
  `d39762da0520f30268a73244e7471b7d990138e3cbe36475d639c7cfca8e926d` (commit `5d54472`). Sesudah pengesahan, yang
  berubah hanya baris status di awal dan isian bagian 9 ini.
- D06 dan lampiran C6 disahkan terpisah setelah auditor mencocokkan setiap baris lampiran dengan teks master.

Sebelum baris di atas diisi, addendum ini tetap berlabel OWNER_CONFIRMED_CHAT. Pengesahan kebijakan tidak membuat gate
mana pun ACCEPT dan tidak memberi production GO.

# Peta sambungan antar tahap (fokus 1 audit akhir, D14-13)

Disusun penulis pada 15 Okt 2026 dari kode dan workflow di `66baa8e8` (hanya membaca). Titik awal untuk auditor,
bukan bukti lulus. "Q25" = 25 workflow kualifikasi kandidat (`../cp1-7-fix-r1-20261015/CI_RECEIPT.json`).

Lapisan uji: **DB** = SQL lewat `public.*` dengan klaim JWT buatan; **HTTP** = login Auth + PostgREST sungguhan;
**Browser** = Chromium pada build `DISPOSABLE_TEST` ke backend sekali pakai; **Tiruan** = `tests/browser/*.spec.ts`
dengan data simulasi atau HTTP tiruan; **Basi** = workflow di luar Q25 yang terakhir berjalan 8 Okt.

## 1. Rantai utama

| # | Sambungan | Mekanisme (RPC → penulis Native; jurnal) | Uji di Q25 | Di luar Q25 (basi) |
|---|---|---|---|---|
| B1 | Penerimaan supplier → stok bahan (roll) | `erp_cp7_save_procurement_v1` → `erp.post_material_purchase_v2` (`MATERIAL_PURCHASE`); transfer `erp_cp7_save_materials_v1`; koreksi `erp_cp7_correct_receipt_v1` | DB, HTTP, Browser (F03 Full p09, Receipt Correction) | `cp7-p09-procurement`, `cp7-f03-e24-issue` |
| B2 | Bahan → Buat Potongan → WIP potong | `erp_save_cutting_group_before_sewing_v2` → `erp.post_cutting_material_issue` (`CUTTING_MATERIAL_ISSUE`); buka ulang `erp_cp7_reopen_cutting_v1`; kain kembali/batal `erp_cp7_return_cutting_fabric_v1`, `erp_cp7_reverse_cutting_return_v1` | DB (P18, CP17 STK01, SG02); Browser hanya kain kembali (fixture membuat potongan). **Tidak ada browser Q25 yang mem-POST potongan** | `cp7-f04-*`, `cp7-cutting-correction` |
| B3 | Potongan → Bagi Potongan ke mandor | `erp_save_cutting_pickup_v1` (tanpa stok/jurnal); batal `erp_cp7_reverse_pickup_v1` (SG-01) | DB; Browser hanya pembatalan (CP17 SG01) | POST di browser hanya `cp6_frontend_recovery_ui` (era CP6) |
| B4 | **Bagi Potongan → jahit selesai → siap laundry** | `public.erp_record_sewing_terminal_v1` → `erp.sewing_terminal_events` (jumlah "siap kirim" laundry dihitung dari sini, migrasi v2_6_20 baris 2270–2337, 3324–3331); upah: `erp.post_work_completion` (`WORK_COMPLETION`), **tanpa pembungkus public** | **Hanya DB**: fixture menyisipkan langsung lalu memanggil sebagai owner (`scripts/cp7_f03_e01_cases.py` baris 139–143) | — |
| B5 | Jahit → kirim/terima laundry (+ klaim, cuci ulang) | `erp_save_laundry_qc_action_v1` POST_DELIVERY/RECEIPT → `erp.post_laundry_delivery/_receipt` (`LAUNDRY_ESTIMATE_ACCRUAL`); `erp_save_laundry_bd_action_v1`; klaim `erp.save_laundry_claim_v2` | DB (P18, CP17 SG03); Browser (Pre-freeze 31: `BD_BROWSER:D08_*`, `RANGE_BROWSER:*`, `W05_CLAIM_*`) | `cp7-p04-wip` (cuci ulang, klaim tertahan, hilang) |
| B6 | Invoice/klaim laundry → hutang vendor → kas | `erp_save_laundry_bd_action_v1` POST_INVOICE (`VENDOR_INVOICE`), PAY_VENDOR_DOCUMENT (`VENDOR_PAYMENT`); penjaga `cp7_guard.guard_laundry_claim_date`, `guard_cash_line` | DB (P18, CP17 FIN02, kas kosong); Browser (`BD_BROWSER:D12_*`). FIN02 tanpa HTTP/browser | — |
| B7 | Terima laundry → QC & Final SKU → lot barang jadi (+BS) | `erp_save_laundry_qc_action_v1` POST_FINAL_SKU → `erp.post_final_sku_allocation_v1`, `erp.post_qc` | DB (P18). **Tidak ada browser Q25 yang mem-POST QC** (D08 hanya membuka layar); Tiruan `cp6-laundry-qc.spec.ts` | `cp7-transaction-source` |
| B8 | Barang jadi → HPP final (WIP → nilai FG) | `erp.finish_production_order` + `erp.process_cost_recalc_queue` → `PO_HPP_GL_SYNC`, **tanpa pembungkus public**; dari aplikasi hanya hitung ulang `erp_cp7_process_recost_v1` | DB (P18, CP17 HPP01); Browser recost (F03 Full p13) | `cp7-f03-e06`, `cp7-f03-cost-continuation` |
| B9 | Barang jadi → buku Vivo/Widie, penyesuaian, Ganti Merek | baca `erp_cp7_get_fg_*`; `erp_cp7_save_fg_adjustment_v1` (`FG_ADJUSTMENT`); Ganti Merek `erp_save_product_conversion_action_v1` (`PRODUCT_CONVERSION`) | DB, HTTP, Browser (F03 Full p10, Note Correction). Ganti Merek: **DB saja, di tumpukan CP6** (BE T1) | `cp7-f03-cost-continuation`, `cp7-f03-redye`, `cp7-f03-x04` |
| B10 | Barang jadi → draf/invoice penjualan | `erp_cp7_save_sale_v1` → `erp.save_sale_draft_v2`, `erp.post_sale_v2` (`SALE`) | DB, HTTP, Browser (F03 Full p11, CP17 D14-5) | `cp7-f03-e01`, `cp7-f03-capacity` |
| B11 | Penjualan → piutang → bayar pelanggan → kas | PAYMENT → `erp.post_sales_payment` (`SALES_PAYMENT`); koreksi `erp_cp7_correct_sales_payment_v1`; balik rantai `erp_cp7_reverse_sales_chain_v1`; koreksi nota `erp_cp7_correct_note_v1` | DB, HTTP, Browser (F03 Full p11, Note Correction, P18 E01 bridge) | `cp7-payment-correction`, `cp7-sales-chain` |
| B12 | Retur penjualan → stok FG + kredit piutang (+ refund) | RETURN → `erp.post_sales_return`; koreksi `erp_cp7_correct_sales_return_v1` | DB, Browser (F03 Full p11 returns, customer_refund) | `cp7-sales-return-correction`, `cp7-f03-e03` |
| B13 | Semua uang → kas/bank → buku besar → laporan / tutup periode | `erp.post_journal`, `erp.reverse_journal`; penjaga `CP7_CASH_NEGATIVE`; laporan `erp_cp7_get_finance_report_v1`; periode `erp_cp7_save_period_control_v1`; lain-lain `erp_cp7_save_misc_finance_v1` | DB (P18: GL = buku pembantu di 8 titik), HTTP, Browser (F03 Full p13, cash_installments), CP17 `CASH_*`. **Tidak ada browser yang memperlihatkan penolakan kas minus** | `cp7-misc-correction`, `cp7-f03-cash`, `cp7-f03-e06` |

## 2. Rantai samping

| # | Rantai | Uji di Q25 | Catatan |
|---|---|---|---|
| S1 | Hutang supplier → bayar supplier → kas | DB, race, HTTP, Browser (Supplier Payment Create/Correction, F03 Full p09, P18) | — |
| S2 | Retur/kredit supplier | DB, HTTP, Browser (F03 Full p09, supplier_credit, Pre-freeze) | `cp7-f03-return-documents`, `cp7-supplier-credit-authority` basi |
| S3 | Payroll: absensi, Nota borongan, upah rework, kasbon → kas | DB, race, HTTP, Browser (F03 Full p12, P12 Payroll, CP17 FIN01/KASBON) | Upah rework (RWK01) DB saja |
| S4 | Nota Ambil Aksesori → potongan payroll | DB saja, di tumpukan CP6 (AV) | `cp7-f03-e24-issue` (browser) basi |
| S5 | BS dan rework | DB (CP17 RWK01, BE T1); Tiruan `cp5-bs-resolution.spec.ts` | `cp7-p04-wip` basi; tidak ada browser nyata di Q25 |
| S6 | Hitung fisik / penyesuaian | DB, race, HTTP, Browser (F03 Full p09/p10) | Tidak pernah di dalam skenario rantai |
| S7 | Impor saldo awal → tahap berikutnya | CP6 AV (DB, tumpukan CP6); di CP7: `P12_OPENING_*`, `F03_E03_IMPORTED_REFUND*`, `E05_OPENING_*` | Browser WIP awal hanya di UI beku CP6 (`e43e0ed4`) |

## 3. Celah yang sudah terlihat penulis

**Terbukti dari kode (penulis memeriksa sendiri):**

1. **Jahit selesai tidak bisa dicatat dari aplikasi tersambung.** Backend punya `public.erp_record_sewing_terminal_v1`,
   tetapi tidak ada layar di `src/` yang memanggilnya (`grep` atas `src/`: nol). Layar WIP & Sewing tersambung hanya
   membaca dan memasang tanda (`erp_get_wip_control_v1`, `erp_set_wip_control_flag_v1`). Jumlah "siap kirim" di
   laundry dihitung dari catatan jahit selesai itu, jadi **barang tidak bisa berpindah dari jahit ke laundry lewat
   aplikasi**. Di UX demo, layar WIP & Sewing punya alur kirim ke laundry. Semua uji rantai membuat catatan ini lewat
   SQL langsung.
2. **Upah borongan dan HPP final tidak punya jalan dari aplikasi.** `erp.post_work_completion` (jurnal
   `WORK_COMPLETION`, sumber baris upah yang bisa masuk Nota) dan `erp.finish_production_order` tidak punya pembungkus
   `public`; uji memanggilnya sebagai owner. Auditor perlu memastikan dari mana upah borongan dan HPP final terbentuk
   saat aplikasi dipakai sungguhan.
3. **Sekitar 60 workflow `cp7-*` hanya berjalan saat push ke `cp7/integration`** (head masih `9d57b7f5`, 8 Okt) dan
   tidak punya tombol jalankan manual (`workflow_dispatch`). Hasil terakhirnya dari 8 Okt, **sebelum** penjaga D14-2
   (upah tidak boleh dibayar sebelum hutangnya ada), D14-3 (kas tidak boleh minus) dan FIN02. Saat penjaga itu pertama
   dipasang, beberapa suite lain gagal karena data ujinya (`../cp1-7-fix-r1-20261015/FIRST_RUN_597d6778.md`) dan dibetulkan;
   suite basi ini belum pernah dijalankan ulang, jadi hasilnya sekarang **tidak diketahui**. Contoh: balik rantai
   penjualan, koreksi pembayaran pelanggan, koreksi retur, buka ulang potongan, koreksi transaksi lain, navigasi ke
   transaksi asal, E01/E03/E05/E06/E24, X04/celup ulang, kapasitas, dokumen retur, kelanjutan biaya, P04 WIP, F04/F05.
4. `docs/cp7/p18/P18_FULL_CYCLE.md` masih menulis kas boleh minus (−1.100). Sejak D14-3 kasus P18 menambah modal
   1.200 ke bank sebelum titik awal (`scripts/cp7_p18_full_cycle_cases.py` baris 19–23); angka di dokumen sekarang
   berarti perubahan, bukan saldo. Koreksi bertanggal ditambahkan di akhir dokumen itu; teks lama tidak dihapus.

**Dari pemetaan (auditor memeriksa):**

5. Tidak ada uji yang melewati sambungan ini dari ujung ke ujung lewat aplikasi: B4; QC → selesai PO → HPP final;
   absensi → pool HPP absensi (tanpa layar); impor saldo awal → produksi → jual → kas di tumpukan CP7; Ganti Merek →
   jual → HPP di tumpukan CP7; Nota Ambil Aksesori → potongan payroll → kas; klaim laundry → BS/rework/cuci ulang → QC
   sebagian; upah rework → Nota → bayar; hitung fisik atau tutup periode di tengah rantai.
6. Hanya DB atau tiruan, tanpa browser nyata di Q25: POST potongan, POST bagi potongan, POST QC/Final SKU, selesai PO
   dan HPP final, Ganti Merek, penyelesaian BS/rework, Nota Ambil Aksesori, tanggal klaim laundry (FIN02), kartu stok
   STK01, RWK01, rekonsiliasi buku besar P18. Penolakan D14-2/D14-3 hanya DB + HTTP.
7. P18 siklus penuh hanya DB (2 kasus) dan melewati: saldo awal, invoice supplier terpisah/GRNI, retur supplier,
   Nota Ambil Aksesori, upah absensi, kasbon, cicilan, BS/rework/klaim/cuci ulang, Ganti Merek, buku FG, hitung fisik,
   refund tunai, koreksi/pembalikan penjualan, transaksi lain-lain, tutup periode, recost dari layar, batal bagi
   potongan, kain kembali (`full_P18_acceptance=false`).

**Status butir 1–3 (ditambahkan 15 Okt 2026, D14-14):** butir 1 dan upah borongan di butir 2 dikerjakan sebagai G1
(layar WIP & Sewing mencatat "selesai dijahit" + upah mandor; B4 sekarang punya jalan aplikasi dan uji DB, race, HTTP,
browser HP dan komputer). HPP final di butir 2 dikerjakan sebagai G2 (layar HPP & Rekalkulasi menyelesaikan PO lewat
`erp.finish_production_order`; B8). Butir 3 dikerjakan sebagai G3: 51 workflow dijalankan ulang, 3 merah karena data uji
lama, dibetulkan tanpa melonggarkan penjaga. Rincian, batas yang diketahui, dan nomor run: `GAPS_D14_14.md`. Teks butir di
atas dibiarkan sebagai catatan keadaan sebelum perbaikan.

## 4. Butir terbuka yang harus diperhitungkan audit akhir

A2 akar dua kegagalan lama (D13-10); FABLE-012 pencabutan 82 penulis ditunda ke CP7C dengan gerbang (D14-9);
FABLE-011 lantai tanggal cutover (butuh keputusan owner); FABLE-007 (hanya kasus regresi); SG-01 tingkat (b) tetap
ditolak; SG-02 batal/betulkan berlaku sejak disimpan; SG-03 cuci ulang berbayar produk sama tanpa tagihan (D06);
R-EV02/SOL-003 akar kegagalan AZ pertama belum terbukti; R-DOC03 dan kunci CP2 ke CP7C; CP7C ditahan (D13-9a);
D13-7a/D13-8f Enteng tidak diubah sebelum backup terverifikasi dan data UAT dibersihkan sebelum dipakai; D13-8b batas
uji pemulihan lokal; D14-7 bacaan Data API hosted oleh Fable; `cp7_guard.findings()` belum dijalankan atas data
hosted; K8 8 dari 13 kebijakan CP6 dan ambang pengingat/kapasitas CP7 diisi di aplikasi saat dipakai; P19 uji beban,
`independent_acceptance=false`, `production_go=false`.

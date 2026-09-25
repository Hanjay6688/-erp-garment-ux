# Audit Lampiran C6 (D06) — Aksesori & Laundry vs Master

**Status:** Tinjauan auditor independen atas draf writer, 25 September 2026.

**Integritas file:**
- Lampiran C6 — sha256 diverifikasi: **YA** — `72621c8a978573506b8c829a2a8790de948f6cb10e83ecd14dfddf35d495bc0d` cocok dengan target.
- Master (M) `ERP_V3_2_Master_Pulih_20260923.md` — sha256: `f21ac70360915a1f1021b42a3918e862ca7d11cf88c1b90c5627b4490c69af07` (sama dengan yang dicatat di addendum induk §2, baris "M").
- Kontrak yang dipakai: M, P (`ERP_V3_2_Perubahan_Pulih_20260923.md`), BR (`ERP_ADDENDUM_BUSINESS_REPORT_CP7_2026-09-18.md`). Handoff/audit writer lain (mis. `ERP_AKSESORI_HANDOFF_PROMPT_WRITER_2026-09-18.md`) dipakai hanya sebagai bukti pendukung, bukan penentu label.

## 1. Tabel pencocokan baris

| Baris (ID) | Teks lampiran (ringkas) | Label writer | Klausul M/P/BR penentu | Penilaian auditor | Catatan |
|---|---|---|---|---|---|
| ACC-01 | Pengeluaran aksesori ke mandor per PCS utuh, harga eceran manual valid (7 PCS tetap 7) | BASELINE | M:1066–1071 "ACC-DEC02 — DIPUTUSKAN, belum diterapkan/diuji: harga eceran diketik manual... Jumlah fisik 7 buah harus tetap tepat 7"; M:44, M:1023 "7 PCS adalah aksesori"; P:37,154,211 menegaskan ulang | **BASELINE** | Sesuai — sudah diputuskan kontrak, tinggal diuji |
| ACC-02 | Hak reimbursement aksesori per lot FG (akrual, BOM, default dari hak belum dibayar) | BASELINE | M:6503 `post_accessory_reimbursement_accrual(p_lot_id)`; M:3900–3962 "Hak reimburse melalui GOOD×BOM kategori yang sah"; M:1753 baris 1 (kolom kiri: "PCS exact, source/ownership/purpose... nominal legacy" = aman dikerjakan) | **BASELINE** | Sesuai |
| ACC-03 | Recost HPP aksesori setelah koreksi harga bahan (`refresh_accessory_hpp_after_material_recost`) | BASELINE | M:5966 fungsi persis sama nama & dump 19351–19399; kewajiban recost umum M:833,839,1194 | **BASELINE** | Sesuai. Nama jurnal `ACCESSORY_HPP_RECOST` sendiri tidak ditemukan verbatim di M — hanya nama fungsi; tidak mengubah label |
| ACC-04 | Pemakaian aksesori internal dan retur aksesori | **CR-TUNDA (usulan)** | M:1668 "Aksesori internal/pos/retur/PCS \| **Tetap dibutuhkan**. Bedakan qty fisik, ownership, condition, tagihan mandor dan reimburse; keputusan nilai/settlement yang belum ada tetap terbuka"; M:1695 menaruhnya dalam "Gelombang aksesori/laundry ... **direkomendasikan sebelum audit final gabungan CP6**" ("pemakaian/pos/retur/inspection/conversion"); M:1699 "fitur itu tidak boleh diklaim selesai" (bukan "boleh ditunda") | **TIDAK SESUAI — seharusnya BASELINE** (mekanisme tracking-nya), dengan **sub-bagian nilai PENDING KEBIJAKAN** (ACC-DEC03 nilai pemulihan M:4457; ACC-DEC05 retur nota setelah lunas M:4459) | Writer melabeli seluruh fitur sebagai CR "usulan" yang "belum ditinjau" — padahal M secara eksplisit mewajibkannya sebelum audit final gabungan CP6. Ini persis pelanggaran aturan addendum induk §8.2: "Bug baseline tidak boleh ditunda dengan menyebutnya CR" |
| LAU-01 | Kirim/terima laundry, QC, FG authoritative | BASELINE | M:359/301 "LAUNDRY wajib vendor laundry... BS bernilai membutuhkan identitas produk, ukuran, PO dan pemegang/lokasi" — alur dasar existing | **BASELINE** | Sesuai |
| LAU-02 | Claim laundry STUCK/MISSING/DAMAGE dan kompensasi | BASELINE | M:4210 "Claim STUCK/MISSING/DAMAGE dan pemulihan barang tetap mengikuti pool/lineage existing" | **BASELINE** | Sesuai |
| LAU-03 | Identitas produk BS laundry pada penerimaan fisik | BASELINE | M:359 "BS bernilai membutuhkan identitas produk, ukuran, PO dan pemegang/lokasi yang dikenal" | **BASELINE** | Sesuai |
| LAU-04 | Tarif laundry kosong: estimasi owner dan blokir tutup buku | BASELINE | M:4475 LAU-DEC04 kolom kanan ("aman"): "Fisik pending disetujui; HPP/laporan incomplete. Jangan memberi izin final sales/close baru tanpa kebijakan"; M:4145 (§8.4 Fisik dengan harga unknown); M:4479 "invoice pending berbeda dari harga unknown ... sudah jelas" | **BASELINE** | Sesuai untuk bagian "blokir tutup buku". Catatan: rujukan writer "keputusan §14 no.3" tidak ditemukan verbatim sebagai penomoran di M — kemungkinan penomoran dokumen lain, bukan M. LAU-DEC04 sendiri masih berstatus "belum ditetapkan" di M §14.2, jadi hanya perilaku blokir yang baseline, bukan izin final sales/close baru |
| LAU-05 | Paket/komponen laundry dan invoice laundry susulan | **CR-TUNDA (usulan)** | M:1668 "Laundry vendor/paket/komponen/pending \| Tetap dibutuhkan **dan merupakan perluasan bisnis yang sudah disetujui**"; M:3729–3737 (§1.1) — desain paket/komponen per vendor dan invoice susulan **eksplisit "sudah disetujui"**, bukan diusulkan; BR:165 "Paket laundry versus komponen ... tetap mengikuti **kontrak lama**" | **TIDAK SESUAI — seharusnya BASELINE** (desain/mekanisme), dengan **tarif vendor nyata per vendor tetap CR-TUNDA** (LAU-DEC01, M:4472) | Sama seperti ACC-04: M menyebut ini "sudah disetujui" (owner) dan bagian dari gelombang wajib sebelum audit final gabungan CP6, bukan "usulan" yang "belum ditinjau" seperti ditulis writer |
| LAU-06 | Celup ulang BS menjadi warna/SKU baru | CR-TUNDA | Tidak ditemukan — grep "celup" di M, P, BR: nihil hasil | **TIDAK DITEMUKAN DI KONTRAK** | Label CR-TUNDA writer secara praktik masih wajar (fitur baru di luar M, bukan kewajiban yang ditunda), tapi secara formal auditor tidak bisa mengutip klausul M karena memang tidak ada teksnya |
| LAU-07 | Tarif/vendor/retur/servis laundry yang belum diputus | CR-TUNDA; hanya menahan fitur terkait | M:4470–4477 LAU-DEC01–06 (tarif vendor nyata, dasar qty tagih, tanggal kesepakatan, override SKU, mapping akrual/variance — semua berstatus "yang masih perlu dipastikan"); M:1757 "Tarif vendor nyata, dasar tagihan yang belum disetujui, akun/variance, izin sales/close dengan biaya unknown" | **CR-TUNDA** | Sesuai — ini memang daftar keputusan yang secara eksplisit masih terbuka di M |

## 2. Kewajiban M:1691–1699 / 1753–1757 / 4448–4479 yang TIDAK dicakup lampiran

Butir aksesori/laundry pada rentang wajib yang tidak punya baris acceptance sendiri di C6:

- **ACC-DEC01** (M:4453) — barang akhir tahun sudah kembali fisik atau baru diserahkan saat itu; tidak ada ID acceptance.
- **ACC-DEC03** (M:4457) — nilai pemulihan barang bekas dan akun yang sah; hanya disebut umum di catatan ACC-04, tanpa baris sendiri.
- **ACC-DEC04** (M:4458) — biaya servis pelanggan vs kapitalisasi FG perusahaan; tidak dicakup.
- **ACC-DEC05** (M:4459) — retur nota mandor setelah lunas/parsial (credit/carry/refund); tidak dicakup.
- **ACC-DEC06** (M:4460) — pembulatan pembayaran ke rupiah bulat; tidak dicakup sama sekali.
- **ACC-DEC07** (M:4461) — role/lokasi servis dan ambang approval; tidak dicakup.
- **ERP-DEC02** (M:4463) — tiga kategori gratis Special (Afui) serta tarif aksesori future yang belum ditetapkan; ini jelas terkait aksesori tapi tidak muncul di C6 sama sekali.
- **M:1757 baris 3** — "Role, Special, volume/operasi, kanal": inventaris hak existing dan kontrol negatif untuk Special/Afui; tidak ada baris.
- **LAU-DEC01, 02, 03, 05, 06** (M:4472–4477) — dibungkus umum di LAU-07 tanpa ID/baris masing-masing, sehingga owner tidak bisa menyetujui/menahan per-butir seperti diminta aturan D06 rule 3 ("Daftar acceptance ID per fitur").

## 3. Verdict

**Lampiran C6 tidak sepenuhnya cocok dengan Master.** Dari 11 baris: **9 baris SESUAI** (ACC-01, ACC-02, ACC-03, LAU-01, LAU-02, LAU-03, LAU-04, LAU-06, LAU-07) dan **2 baris TIDAK SESUAI** (ACC-04, LAU-05) — keduanya dilabeli CR-TUNDA "usulan" padahal M secara eksplisit menyatakan "tetap dibutuhkan" dan menaruhnya dalam gelombang wajib sebelum audit final gabungan CP6 (M:1691–1699), plus untuk LAU-05 M bahkan menyebutnya "perluasan bisnis yang sudah disetujui" (M §1.1, sekitar M:3729–3737). Ini melanggar aturan addendum induk §8 butir 2: "Bug baseline tidak boleh ditunda dengan menyebutnya CR." Selain itu, 7 sub-keputusan M:4448–4479 (ACC-DEC01/03/04/05/06/07, ERP-DEC02) tidak punya baris acceptance sendiri di C6 (lihat §2).

**Owner belum bisa mengesahkan D06 apa adanya.** Diperlukan koreksi sebelum pengesahan bagian 9 addendum induk:
1. Ubah label ACC-04 dan LAU-05 dari CR-TUNDA menjadi **BASELINE** untuk bagian mekanisme/tracking (qty, custody, kondisi, pemisahan fisik/harga/invoice, paket vs komponen), sambil tetap menandai **PENDING KEBIJAKAN** khusus untuk sub-butir nilai/tarif nyata yang memang belum diputus (ACC-DEC03, ACC-DEC05, ACC-DEC06 untuk aksesori; LAU-DEC01/02/03/05/06 untuk laundry).
2. Tambahkan baris acceptance terpisah untuk ACC-DEC01, ACC-DEC04, ACC-DEC06, ACC-DEC07, dan ERP-DEC02 agar owner dapat menandai per-butir sesuai aturan D06 rule 3.
3. Setelah revisi tersebut, lampiran dapat diajukan ulang untuk pengesahan D06.

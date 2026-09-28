# Handoff untuk writer utama — delta SKU range CP1–6

**Basis baca:** branch `claude/new-session-deapao` pada `e96db5a270da5aa6d0f12c3812ac1c0542df938e`; source produk BD `2f6ac0d`. Baca bersama [handoff writer SKU range](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/docs/cp6-sku-range-impact-20260928.md#L1). Dokumen ini hanya mencatat dampak **tambahan** yang belum dijabarkan secara spesifik di sana. CP6 tetap HOLD, `production_go=false`; tidak ada klaim audit data live atau hasil runtime impor di sini.

## Kontrak owner yang harus tampak di penjualan

- SKU komersial mempunyai daftar **anggota ukuran nyata**, bukan selalu tiga dan bukan semua bilangan di dalam teks range. Ukuran 27 khusus adalah SKU sendiri, contoh `32007-27`.
- Isi cepat 1 lusin menghasilkan **total 12 PCS** dan membagikannya ke anggota SKU. Contoh anggota 31,32,33 → `[4,4,4]`; anggota 31,32,33,34 → `[3,3,3,3]`; singleton 27 → `[12]`. Kuantitas per ukuran tetap sumber akhir untuk cek stok/reservasi.
- Input manual `12` PCS ditampilkan `1 lusin · 0 potong`; `13` PCS ditampilkan `1 lusin · 1 potong`. Angka desimal lusin yang dibulatkan tidak boleh menggantikan total PCS atau dipakai ulang sebagai nilai exact.
- **Usulan untuk kasus ukuran yang tidak membagi 12 habis**, belum keputusan owner: distribusikan sisa PCS secara deterministik pada urutan anggota ukuran yang eksplisit. Misalnya lima ukuran → `[3,3,2,2,2]`. Jangan menyimpulkan kebijakan stok atau urutan dari string “31–35”; minta keputusan owner sebelum mengunci oracle ini. Jika stok hasil pembagian tidak cukup, beri pesan dan biarkan operator mengubah PCS per ukuran; jangan menggeser ke ukuran lain diam-diam.

## Temuan delta dan tindakan

### SR-01 — Builder penjualan hanya mengenal tiga ukuran

**Bukti:** [`productCatalog.ts`](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/productCatalog.ts#L1) memberi `sizes`/`stocks` tuple tiga; [`SalesPages.tsx`](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/SalesPages.tsx#L15) memakai `quantities: [number,number,number]` dan [helper](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/sales/distributeDozensEvenly.ts#L1) membagi hanya bila total habis dibagi tiga. [Route App](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/App.tsx#L602) merender halaman ini juga di runtime connected, tetapi [hero](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/SalesPages.tsx#L92) menyatakan simulasi UX, belum menulis backend. Uji langsung atas helper source, setelah anotasi tipe dihapus: `1` → `[4,4,4]`.

**Dampak:** singleton 27 dan 31–34 tidak dapat dibuat sesuai kontrak melalui builder; stok per ukuran tidak bisa direview untuk anggota keempat. Ini temuan UI/demo, **bukan bukti ledger live salah**.

**Saran revisi:** bentuk baris draft sebagai daftar `{size_id, size_code, product_id, qty_pcs, available_pcs}` yang berasal dari keanggotaan SKU berlaku pada waktu transaksi. Distribusi memakai jumlah anggota dan bilangan bulat PCS; pisahkan helper input dari total PCS. Saat layanan sale connected dipasang, simpan tepat `product_id`/ukuran fisik per baris melalui domain RPC. Jangan memasukkan `product_id` SKU komersial sebagai pengganti barang fisik.

**Oracle:** 31–33=4/4/4; 31–34=3/3/3/3; singleton=12; sku sama beda merek tidak tercampur; size tanpa stok memblokir review dengan qty lama tetap terlihat.

### SR-02 — Konversi balik manual sudah benar di label baris, tetapi tidak di helper/ringkasan

**Bukti:** [`qtyLabel`](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/SalesPages.tsx#L25) benar untuk total 12/13, dipakai di [footer baris](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/SalesPages.tsx#L209). Namun [`updateQty`](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/SalesPages.tsx#L159) menulis `sum/12` dengan maksimum dua desimal ke input helper; [`applyDozens`](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/SalesPages.tsx#L169) menghitungnya balik sebagai PCS exact. Reproduksi: 13 PCS → teks `1,08` → 12,96 PCS → helper menolak. [Ringkasan invoice](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/SalesPages.tsx#L215) juga menampilkan desimal lusin.

**Saran revisi:** setelah edit manual, tampilkan `q = floor(total/12)`, `sisa = total%12` sebagai label; kosongkan/tandai helper sebagai input baru yang perlu sengaja diterapkan, atau simpan nilai exact PCS terpisah. Ringkasan invoice memakai label lusin+potong. Jangan round-trip melalui lusin dua desimal.

**Oracle:** total 12→1/0, 13→1/1, 23→1/11, 24→2/0; edit lalu klik helper tanpa input baru tidak merusak atau menolak qty manual.

### SR-03 — OPEN_SALES_DRAFT impor: SKU tunggal tidak menentukan ukuran fisik

**Bukti paket BB:** [validator](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/supabase/release/cp6-t3/20260925020000_erp_v2_6_20bb_cp6_open_cutover_states.sql#L2791) memerlukan `product_sku` dan qty, hanya memeriksa keberadaan SKU. [Apply](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/supabase/release/cp6-t3/20260925020000_erp_v2_6_20bb_cp6_open_cutover_states.sql#L2872) melakukan `SELECT id INTO STRICT` berdasar SKU saja sebelum `save_sale_draft_v2`. Beberapa produk fisik pada satu SKU komersial membuat lookup ini ambigu (`TOO_MANY_ROWS`). Baris impor belum memberi alokasi ukuran tepercaya.

**Saran revisi:** minta setiap baris impor punya identitas fisik yang bisa diselesaikan menjadi **tepat satu** produk pada cutover (size + brand/model/warna sesuai kontrak atau `product_id` yang divalidasi). Validasi keunikan sebelum status VALID; pakai ID terselesaikan yang sama saat apply. Bila sumber lama hanya punya SKU+total, tandai `SIZE_ALLOCATION_REQUIRED` untuk rekonsiliasi operator; **jangan** bagi rata historis secara otomatis. Pertahankan transaksi atomik, reservasi per ukuran dan replay idempoten.

**Oracle:** dua produk 31/32 ber-SKU sama + baris tanpa size → ERROR eksplisit sebelum apply; baris size32 → draft memegang hanya produk32; stok tidak cukup → rollback tanpa draft/reserve parsial.

### SR-04 — Impor titipan pelanggan dan jahit kain kantong COGS serupa

**Bukti:** [BC apply](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/supabase/release/cp6-t3/20260925040000_erp_v2_6_20bd_cp6_laundry_prices_invoices.sql#L6887) memberi `bc_customer_custody_v1.product_id` melalui subquery `sku` tunggal. Kolom itu boleh null untuk titipan deskriptif, tetapi SKU yang diisi dan punya banyak ukuran akan menghasilkan subquery multibaris. [BE validator](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/supabase/release/cp6-t3/20260926050000_erp_v2_6_20be_cp6_conversion_redye_pocket.sql#L1037) pada historical `OPENING_POCKET_SEWING` target COGS hanya memastikan produk ada; [BE apply](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/supabase/release/cp6-t3/20260926050000_erp_v2_6_20be_cp6_conversion_redye_pocket.sql#L1100) menyimpan satu `product_id` dari subquery SKU, sehingga SKU multiukuran ambigu. Hanya lintasan yang memakai `product_sku` terdampak; titipan tanpa SKU tetap mungkin disimpan sebagai deskripsi.

**Saran revisi:** resolver identitas fisik yang sama dipakai validator dan apply; untuk COGS, butuh ukuran/produk dari referensi jual historis yang benar. Jangan pilih sibling pertama atau isi null untuk menghindari ambiguitas COGS. Jika titipan memang hanya deskriptif, null tetap sah sesuai kontrak existing.

**Oracle:** SKU 31/32 tanpa size ditolak sebelum apply, size32 menjadi FK32; titipan deskriptif tanpa SKU tetap diterima; batch gagal tidak menyisakan posting sebagian. Jalankan pada paket BB→BE disposable, jangan menganggap uji native HPP writer menutup skenario impor ini.

### SR-05 — Pemeriksaan BOM rework impor memilih sibling secara arbitrer

**Bukti paket BB:** [`bb_check_rework_import_row_v1`](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/supabase/release/cp6-t3/20260925020000_erp_v2_6_20bb_cp6_open_cutover_states.sql#L2558) mengambil `products` berdasar `b.product_sku`, mengurutkan versi, lalu `LIMIT 1`; BOM dicek terhadap `identity_root_id` hasil pilihan itu. Padahal input sudah merujuk `bs_source_key` dan tahap apply mempunyai kasus BS sumber. Bila SKU bersaudara punya BOM lama berbeda, hasil pemeriksaan bisa bergantung pada sibling lain.

**Saran revisi:** turunkan produk dari baris BS asal yang sudah lolos identitas ukuran/brand/model/warna atau dari `bs_case.product_id` saat apply; gunakan root **produk fisik yang sama** untuk pemeriksaan BOM. Bila writer menerapkan satu master BOM SKU, tetap deteksi konflik legacy per sibling, bukan `LIMIT 1`. Native `save_rework_order_v2` mungkin mempunyai guard lain; jangan klaim posting keliru tanpa tes.

**Oracle:** fixture SKU31/32, BOM31 ada BOM32 tidak ada dan BS size32 → validasi menolak pada size32; balikkan kondisi → size31 sukses, size32 tidak meminjam BOM31; replay tidak menggandakan biaya.

### SR-06 — Permukaan simulasi lain yang perlu ikut regresi UI

[`MasterDataPages.tsx`](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/MasterDataPages.tsx#L33) hanya menawarkan 28–36; ukuran27 tidak dapat dipilih, dan saat toggle daftar diambil lagi dari himpunan itu. [`QcFinalPage.tsx`](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/QcFinalPage.tsx#L7) dan [`fgNota.ts`](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/fgNota.ts#L1) memakai triple; [`App.tsx`](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/App.tsx#L62) juga menyimpan triple untuk kartu stok/cutting simulasi. [Konversi merek demo](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/src/InventoryControlPages.tsx#L201) menuntut `source.range===target.range`, sehingga perpindahan identitas fisik yang cocok size tetapi beda teks range bisa ditolak. Ini **demo/simulasi**; jalur connected QC/conversion sudah memeriksa `size_id` dan tidak boleh dirusak untuk menyesuaikan demo.

**Saran revisi:** setelah master SKU dinamis tersedia, pakai daftar ukuran nyata pada permukaan simulasi yang masih akan dipertahankan; hapus ketergantungan triple/teks range hanya pada tampilan terkait. Jangan mengganti transaksi connected per ukuran dengan agregat SKU.

## Urutan eksekusi untuk writer

1. Ikuti [backbone master SKU writer](https://github.com/Hanjay6688/-erp-garment-ux/blob/e96db5a270da5aa6d0f12c3812ac1c0542df938e/docs/cp6-sku-range-impact-20260928.md#L55) untuk identitas grup bertanggal, konflik tarif/BOM, dan resolver. Catat dependensi ini; delta di atas tidak menggantikannya.
2. Kerjakan SR-01/02 pada builder sales serta pengujian ukuran nyata. Ini kebutuhan langsung owner; pastikan helper 1 lusin tidak mengubah sumber akhir per ukuran tanpa konfirmasi.
3. Kerjakan SR-03/04 pada validasi + apply impor secara bersamaan; setiap input ambigu harus ERROR sebelum tahap post. Pisahkan impor lama dari distribusi otomatis draft baru.
4. Kerjakan SR-05 berdasarkan source BS fisik, baru tutup gap master BOM. SR-06 menyusul pada UI simulasi yang tetap dipakai.
5. Bukti tutup: unit helper, native disposable import/rework BB→BE, browser singleton27/31–34/manual13, dan tetap jalankan kontrol penjualan/retur/HPP per lot yang writer sudah miliki. Catat jumlah PASS/FAIL/INCOMPLETE per source SHA; tidak ada klaim production-go dari dokumen ini.

## Batas bukti

Scan source TS/TSX, 67 migration, 9 dev family SQL, 28 script SQL, serta BB–BE release package pada SHA di atas. Helper penjualan dijalankan langsung dari source setelah hanya menghapus anotasi tipe TypeScript. Jalur SQL diidentifikasi **secara statis** pada kandidat paket yang dipin; belum ada eksekusi batch multiukuran untuk SR-03/04/05, belum ada audit data live. CP1–3 tidak menambah temuan di luar handoff writer. Tidak membaca audit pesaing.

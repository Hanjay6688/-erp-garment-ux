# SKU range: aturan owner, revisi kiriman jasa, dan dampak lintas CP

Status: pekerjaan writer, CP6 tetap HOLD; `production_go=false`, `audit_complete=false`.
Dasar awal: `08b270337aa4e4d151085e80ece7a061bf4102c7`. Bukti sebelumnya tetap di `cp6-bd-revision-handoff-20260928.md`.

## Aturan awal ERP yang ditegaskan kembali — 28 September 2026 WIB

- SKU komersial dapat berisi range ukuran, misalnya 28–30, 31–33, 34–36. Kasus spesial ukuran27 dibuat owner sebagai SKU baru tersendiri, contoh `32007-27`, beranggotakan satu ukuran. Ini bukan override harga ukuran27 di SKU range.
- Satu SKU mempunyai satu master harga jual, tarif dasar jasa (termasuk jahit dan laundry), serta resep aksesori. Tiga ukuran dalam SKU memakai master yang sama. Memproduksi hanya ukuran 32 tetap memakai tarif SKU asalnya. Owner tidak perlu mengatur harga tiga kali.
- Stok wajib ukuran fisik. HPP utama yang dibaca owner per SKU, menggunakan rata-rata tertimbang bila rincian sumber berbeda.
- Jasa dapat dipilih sekali untuk kiriman biasa; pengecualian penerima jasa tetap dicatat dalam PCS per ukuran.
- Harga sama lintas ukuran tidak berarti semua PCS pasti menerima jasa yang sama. Finishing 5 PCS ukuran 32 hanya memiliki 5 penerima; tidak menciptakan pekerjaan untuk ukuran 31/33.
- Contoh angka di pengujian sintetis; bukan penetapan tarif bisnis owner.

Ini bukan tambahan atau perubahan aturan owner. Writer sempat salah menyebutnya aturan tambahan dan terlalu cepat menyimpulkan revisi cukup pada form. Kesalahan pemetaan itu dikoreksi di sini. Kesamaan hasil hitung satu vendor/proses belum membuktikan adanya master tarif per SKU.

## Revisi produk dalam follow-up ini

`src/LaundryBdPanel.tsx`, form kirim berharga:

1. Tiap jasa harus dicentang; default cakupan jasa terpilih adalah **Seluruh kiriman**.
2. Cakupan seluruh kiriman diturunkan dari kuantitas positif yang benar-benar dikirim, dengan `size_id` asli; bukan kapasitas batch atau jumlah anggota range.
3. Operator memilih **Sebagian ukuran/jumlah** untuk pengecualian, lalu mengisi PCS penerima. Cakupan kosong/berlebih/pecahan ditolak; mengecilkan qty kirim tidak diam-diam mengecilkan cakupan yang pernah diisi.
4. Perubahan qty atau pilihan membatalkan konfirmasi. Ganti batch/paket menghapus pilihan cakupan, qty relevan, dan alasan tambahan. Membatalkan pilihan jasa menghapus rincian lamanya.
5. Ukuran tidak dikirim dapat diisi 0 atau kosong. SKU satu ukuran tidak harus menambah dua ukuran kosong.
6. Tambahan paket tetap eksplisit dan wajib alasan; isi paket tidak ditagih sebagai tambahan. UNKNOWN/FREE/WAIVED, hak akses, RPC, snapshot, replay, dan minimum tetap memakai server yang sudah ada.

Tidak ada perubahan SQL/migrasi, metode pembukuan, atau deployment dalam follow-up ini. Tarif khusus MODEL_SIZE/MODEL_SIZE_COLOR existing belum diganti menjadi master SKU; status kesenjangan itu tetap terbuka.

## Daftar dampak yang benar-benar ditemukan

| Area | Sumber kode / kondisi saat dibaca | Tindakan dan status |
|---|---|---|
| Input laundry | `LaundryBdPanel.tsx` sebelumnya meminta cakupan setiap jasa setiap ukuran | Direvisi: pilih seluruh kiriman, detail hanya pengecualian |
| Master laundry | `cp6_bd_objects_master.sql`: vendor+proses; package/component versi vendor; scoped MODEL/MODEL_SIZE/MODEL_SIZE_COLOR. Tidak ada kunci SKU komersial | Kesenjangan master SKU terkonfirmasi. Nilai sama saat kiriman campuran/satu ukuran adalah bukti aritmetika saja |
| Harga jual | `product_price_versions.product_id` mengacu produk fisik | Harus satu master harga jual SKU dan dipakai seluruh ukuran saudara. Harga transaksi/discount/version historis tetap ditelusuri; tidak memaksa owner mengisi harga tiga kali |
| Produksi sebelum final SKU | `Cp6ReadyBatch` membawa PO/model/pola dan ukuran; SKU akhir dipilih pada QC | Butuh referensi SKU tarif sebelum jasa bila tarif dibedakan per SKU. Referensi tidak boleh langsung menjadi FG atau memaksa SKU akhir |
| Jahit/komisi | Hak kerja dan tarif snapshot PO/komponen digunakan oleh completion/payroll | Telusuri binding ke master SKU; belum ada bukti dari follow-up ini bahwa nominalnya salah. Jangan menghitung ulang riwayat payroll hanya karena display dikelompokkan |
| Resep aksesori | `accessory_bom_versions.product_id`; komitmen PO+product_id; produk fisik berbeda menurut size | Pemetaan resep bersama per SKU diperlukan untuk mencegah saudara ukuran tertinggal. Snapshot lot tetap per sumber dan waktunya |
| HPP owner | `HppPage.tsx` sudah merangkum weighted average brand+SKU, namun bersumber fixture | Integrasi authoritative tetap pekerjaan terbuka. Jangan menjual formula demo sebagai laporan produksi |
| Rincian HPP demo | `HppPage.tsx` membagi stok lot secara merata menurut string range | Tidak boleh dijadikan adapter data asli. Qty ukuran harus dibaca dari ledger; 31=4,32=7,33=2 tidak boleh berubah menjadi pembagian rata |
| Katalog dan BS demo | `productCatalog.ts` dan `BsReworkPage.tsx` memiliki tuple tiga ukuran | Perlu daftar ukuran dinamis untuk SKU singleton27; bukan alasan mengubah struktur stok connected yang sudah exact-size |
| QC/FG/stock/sale/return | `product_id`, `size_id`, source line, lot dan allocation asli | Pertahankan; uji regresi membuktikan grouping tidak menyatukan barang fisik |
| Ganti merek/redye | BE mengikat product asal/tujuan, ukuran, qty dan lot; SKU akhir tidak berarti tarif jasa otomatis diketahui | Referensi SKU baru harus punya resep/tarif yang jelas; lineage origin/target dan harga UNKNOWN dipertahankan |
| Invoice/correction/replay | Biaya snapshot dan selisih invoice mengikuti sumber serta kebijakan owner existing | Rata-rata SKU dihitung dari nilai terbaru, tidak membuat jurnal kedua atau mengganti snapshot penjualan |
| Import/cutover | Data per product fisik dan biaya yang sudah termasuk | Master SKU bersama harus memetakan setiap anggota eksplisit; aksesori yang sudah termasuk tidak ditambahkan lagi |

## Backbone revisi master SKU berikutnya

1. Pisahkan identitas komersial dari produk fisik. Kunci kelompok tidak cukup berupa teks kode SKU saja: merek/model/warna dan versi identitas harus konsisten. Keanggotaan ukuran eksplisit; jangan menebak dari urutan angka, substring, atau banyaknya size yang diproduksi.
2. Master harga jual dan jasa berisi identitas SKU komersial, jenis harga/penyedia/proses/komponen yang relevan, nominal, satuan, periode berlaku dan versi. Semua anggota ukuran merujuk versi yang sama. SKU27 dapat mempunyai master sendiri; tidak otomatis lebih mahal. Diskon transaksi yang sah bukan master harga per ukuran baru.
3. SKU referensi tarif sebelum QC dicatat sebagai referensi pada order/kiriman dan dibawa ke snapshot. Target barang jadi di QC tetap identitas aktual. Perbedaan referensi dan target harus terlihat, tidak menyebabkan repricing diam-diam.
4. Master BOM/resep berbagi versi SKU. Resolver mengambil resep yang berlaku pada transaksi dan membuat komitmen/snapshot untuk produk fisik dan lot. Perubahan master berikutnya tidak mengedit penggunaan lama.
5. Migrasi tarif/BOM lama memeriksa seluruh sibling. Bila tiga ukuran memiliki tarif/resep berbeda, laporkan konflik dan minta penyelesaian atas data konkret; jangan mengambil yang pertama atau merata-ratakannya diam-diam.
6. Aturan kompatibilitas tarif khusus per ukuran existing harus diselesaikan saat migrasi master. Pengujian existing MODEL_SIZE membuktikan perilaku lama, bukan persetujuan untuk tiga harga pada satu SKU. Kasus khusus27 memakai master SKU baru `32007-27`, bukan jalur MODEL_SIZE di SKU range.
7. Order lama tetap membawa versi yang sudah disepakati. Order baru memakai master SKU. Revisi historis hanya melalui koreksi/versioned recost yang sah.

Paket ini memerlukan perubahan lintas master/PO/laundry/BOM/import dan kualifikasi migrasi sendiri. Follow-up UI tidak mengklaim paket master ini sudah selesai.

## HPP per SKU tanpa kehilangan asal biaya

Rumus ringkasan stok: **jumlah nilai stok tersisa semua lot anggota SKU / jumlah PCS stok tersisa anggota SKU**. Pembulatan hanya saat penyajian; total biaya sumber, selisih dan jurnal tetap dipertahankan sesuai presisi server. Stok nol ditampilkan tidak tersedia, bukan HPP nol. Biaya belum lengkap tetap berlabel sementara/belum final.

Contoh 10 PCS × Rp50.000 ditambah 2 PCS × Rp80.000 = Rp660.000 /12 = Rp55.000/PCS. Rata-rata dua harga tanpa bobot menghasilkan Rp65.000 dan salah untuk komposisi tersebut.

- Ringkasan owner boleh satu angka SKU. Drill-down menunjukkan ukuran, lot, versi biaya dan penerima jasa.
- Penjualan mengambil barang dan sumber biaya lot yang dialokasikan oleh engine existing. Memakai rata-rata untuk ringkasan tidak mengganti metode FIFO penjualan.
- Retur merujuk allocation penjualan dan lot/produk ukuran asal; tidak memasukkan ukuran baru hanya karena satu SKU.
- Invoice terlambat/koreksi mengubah versi biaya dan membagi selisih ke FG tersisa/COGS sesuai aturan existing. Ringkasan dihitung ulang dari hasil itu tanpa jurnal tambahan.
- Filter lokasi/grade/tanggal dan status biaya harus berlaku konsisten pada pembilang serta penyebut. Pencarian teks di UI tidak boleh mengubah total SKU seolah semua lot sudah tercakup.

## Aksesori sebagai HPP — sumber angka yang sekarang dipakai

Jalur produksi normal: lot FG → produk fisik → komitmen BOM untuk PO/produk → versi BOM → item kategori + jumlah per GOOD FG → snapshot biaya saat FG diterima.

`ensure_fg_accessory_cost_snapshot` versi AP (`20260922135615_erp_v2_6_20ap_cp6_connected_import_materials.sql`) mendukung:

- `CATEGORY_MOVING_AVG`: `accessory_category_weighted_avg_cost_at(category_id, lot.produced_at)`, yaitu nilai historis kategori pada tanggal FG; missing basis ditolak.
- `BOM_STANDARD`: `hpp_standard_rate / accessory_uom_factor(category_id,hpp_uom_code,lot.produced_at)`. Harga per lusin diubah menjadi per unit dasar.
- Kuantitas: `good_qty_pcs × qty_per_good_fg_base`. Unit HPP diambil dari jalur terpilih di atas. Resep 1 ritsleting Rp2.000 +2 kancing Rp300 +1 label Rp400 menghasilkan Rp3.000/GOOD PCS;100 GOOD PCS Rp300.000.
- `reimbursement_rate / reimbursement_uom_factor` adalah angka penggantian mandor terpisah. Nota ambil/penagihan aksesori dan actual inventory cost juga terpisah; tidak dijumlahkan otomatis sebagai HPP ganda.
- Rework hanya memotret item BOM yang dipilih dan disimpan dalam keputusan rework, bukan seluruh BOM sekali lagi.
- Impor WIP yang ditandai aksesori sudah termasuk tidak menambah snapshot biaya aksesori kedua.
- `refresh_accessory_hpp_after_material_recost` versi AC merevisi snapshot CATEGORY_MOVING_AVG yang terdampak dengan history, membangun ulang HPP, meneruskan ke conversion, dan menyelaraskan GL. Tidak mengganti seluruh harga historis dengan master hari ini.

Belum dilakukan pembacaan master bisnis live untuk menentukan SKU owner mana yang memakai masing-masing metode. Bukti repository menjelaskan mekanisme, bukan menyatakan konfigurasi live telah sesuai.

## Rencana bukti sebelum eksekusi

- Build resmi dan tes parser/model laundry serta conversion.
- Tambahan browser desktop/HP emulasi: ALL31–33, single32 dalam batch, singleton27, finishing5×32, perubahan qty, cakupan kosong/berlebih, reset pilihan. Jalur package extra/FREE/WAIVED dan audit sebelumnya tetap diuji.
- Native: satu versi tarif jasa pada kiriman campuran31/32/33, hanya32, dan singleton27; tidak menambah anggota ukuran fiktif atau harga khusus otomatis. Ini menguji aritmetika kiriman; belum menguji master harga SKU baru `32007-27`.
- Native: satu SKU dengan tiga product fisik, stok4/7/2; biaya finishing hanya5×32; HPP tertimbang; jual2×32; invoice+13 dibagi FG11/COGS2; retur1×32 kembali ke lot yang sama.
- Semua verdict per kasus wajib diperiksa. Job berstatus selesai tidak berarti semua kasus PASS. Native derivation HPP bukan bukti halaman HPP connected sudah dibuat.

Hasil eksekusi dan commit kandidat akan dicatat terpisah setelah selesai. Auditor/user tetap pemilik penutupan temuan.

# P08 — Bukti fisik kain (pemasangan, sisa layak, tambahan dari luar)

Status: kandidat sumber di cabang `claude/new-session-deapao`, belum dikualifikasi Native. `full_P08_acceptance=false`, `independent_acceptance=false`, `production_go=false`. CP6 tetap HOLD.

## Tujuan

Sebelumnya baris kain yang resepnya sudah direview hanya punya `gross` (celah rencana × pemakaian per PCS). Tiga angka fisik — terpasang terbukti, sisa layak yang dialokasikan, dan tambahan dari luar — selalu UNKNOWN. Perubahan ini menghubungkan ketiganya ke sumber fisik ERP yang benar-benar ada, dengan aturan gagal-tertutup: angka hanya keluar bila sumbernya terbukti dan pembagiannya pasti. Selain itu tetap UNKNOWN dengan kode alasan; tidak ada angka yang dikarang dan tidak ada UNKNOWN yang diubah menjadi nol.

## Sumber fisik (dibaca pada jam ambil analisis yang sama)

`cp7_fabric_native.source` naik ke kontrak `cp7.fabric-source.v2` dan membawa blok `physical` (`cp7.fabric-physical.v1`) untuk setiap bahan kain yang punya resep terpilih:

- roll bahan itu: status, konsistensi bahan pada semua gerakan roll, dan stok per lokasi (jumlah `qty_signed` dengan `physical_at` ≤ jam ambil);
- semua grup potong Native yang belum diposting dan menyentuh roll bahan itu, atau yang ditautkan intent rencana CP7 ke target yang direview — beserta komposisi roll-nya;
- lokasi yang dipakai (jenis dan status aktif);
- baris PO terbuka saldo awal (ALL-P04) untuk bahan itu, dengan sisa dari fungsi BB yang sudah ada `erp.bb_commitment_line_remaining_v1` dan tanggal datang yang tercatat.

Hak baca yang ditambahkan hanya kolom tertentu (bukan harga/biaya): `material_rolls(id,material_id,status)`, `material_stock_movements(material_id,roll_id,location_id,qty_signed,physical_at)`, `locations(id,location_type,is_active)`, `bb_purchase_commitments_v1(id,po_number,location_id,expected_date)`, `bb_purchase_commitment_lines_v1(id,commitment_id,material_id,line_number)`, `cp7_plan_native.intents(id,target_key,cutting_group_id)`, plus EXECUTE pada fungsi sisa PO BB. Tidak ada hak tulis, role, atau RPC publik baru. Batas skala (P19): hanya roll yang masih memegang jumlah tidak nol pada suatu lokasi (positif atau negatif) atau yang dipakai draf belum diposting yang ikut sumber. Roll lama yang sudah habis tidak mengubah angka, jadi bertahun-tahun penerimaan tidak membuat ambil analisis ditolak. Batas 10.000 baris PO berlaku setelah memilih baris yang masih terbuka, sehingga baris yang sudah tutup tidak pernah menyingkirkan baris terbuka. Melewati batas tetap menolak dengan `CP7_FABRIC_PHYSICAL_LIMIT`; tidak ada pemotongan diam-diam. Karena blok fisik ikut sidik jari analisis, setiap penerimaan, draf potong, posting potong, atau perubahan PO pada bahan yang direview membuat Original lama `ARCHIVED_STALE`; Original lama tidak pernah diubah.

## Aturan

1. **Terpasang terbukti** = 0 (ASSUMED, ikut asumsi skenario) hanya untuk PCS yang terbukti belum dipotong pada jam analisis: celah resep diketahui dan seluruh WIP produk/ukuran itu sudah pasti identitasnya (tidak ada pencocokan UNKNOWN/NEEDS_CHECK). WIP yang sudah dipotong tetap butuh sumber fisik pemasangan dan kaitan produk/ukuran yang tepat; identitas belum pasti → UNKNOWN. Bahan yang dikeluarkan tidak pernah dianggap terpasang.
2. **Sisa layak yang dialokasikan** = komposisi draf potong Native yang belum diposting dan ditautkan intent ke target itu, bila setiap baris memakai bahan resep, roll AVAILABLE/HALF_USED dan konsisten, di gudang bahan aktif, dan stok roll/lokasi menutup semua draf belum diposting pada roll itu (bertaut maupun tidak). Ini rencana, bukan reservasi stok (KNOWN bila hanya dari draf).
3. **Stok bebas** (stok roll layak dikurangi semua draf belum diposting) ditambahkan hanya bila himpunan pemakai lengkap — tidak ada baris lain yang ACTIVE/belum direview dengan bahan atau celah yang belum diketahui — dan pembagiannya unik: stok bebas cukup untuk semua kebutuhan, atau hanya ada satu pemakai bahan itu (ASSUMED).
4. **PO terbuka** dihitung sekali, hanya untuk satu pemakai yang lengkap, hanya ke gudang bahan aktif, dan hanya bila akhir hari WIB tanggal datang ≤ batas waktu target. Tanggal kosong atau sudah lewat (overdue) → UNKNOWN; setelah batas waktu → tidak dihitung. PO di luar ERP tidak terlihat.
5. **WIP sejenis yang identitasnya belum pasti.** Di Native, potongan dari PO hanya terikat model dan ukuran; warna/merek belum terbukti, sehingga pencocokan ke produk menjadi NEEDS_CHECK. PCS produk ini mungkin sudah terpotong di WIP itu, jadi terpasang UNKNOWN (`FABRIC_WIP_IDENTITY_UNRESOLVED`). Kernel dihitung dengan terpasang 0 hanya sebagai batas atas: tambahan dari luar tetap UNKNOWN dan alasan menyebut "paling banyak X" (juga bila batasnya 0).
6. Draf potong manual yang belum diposting pada bahan itu, stok roll negatif/beda bahan, pembagian bersama yang belum diputuskan, batas waktu yang belum diketahui, atau produksi yang dihentikan → tambahan dari luar UNKNOWN dengan kode alasan.
7. **Tambahan dari luar** dihitung oleh kernel bahan yang sudah dipercaya (`cp7_baseline.material`, oracle O09): max(0, gross − terpasang − sisa layak − PO tepat waktu).
8. **Kemampuan produksi global** tetap UNKNOWN: kelipatan produksi dan kapasitas masih kebijakan yang belum dikonfirmasi pemilik (PENDING_POLICY_VALUE).

Kode alasan UNKNOWN: `FABRIC_GAP_UNKNOWN`, `FABRIC_WIP_IDENTITY_UNRESOLVED` (dengan batas atas), `FABRIC_LINKED_DRAFT_NOT_ELIGIBLE`, `FABRIC_STOCK_INCONSISTENT`, `FABRIC_UNLINKED_NATIVE_DRAFT`, `FABRIC_OTHER_NEEDS_UNREVIEWED`, `FABRIC_SHARED_NEED_UNKNOWN`, `FABRIC_SHARED_SUPPLY_SPLIT_UNDECIDED`, `FABRIC_INCOMING_LOCATION_NOT_ELIGIBLE`, `FABRIC_DEADLINE_UNKNOWN`, `FABRIC_INCOMING_OVERDUE`, `FABRIC_INCOMING_ETA_UNKNOWN`, `FABRIC_PRODUCTION_DISABLED`, `FABRIC_PHYSICAL_SOURCE_NOT_CAPTURED`, `FABRIC_PHYSICAL_NOT_PROVEN`.

## Perbaikan identitas resep (cacat yang ditemukan oleh P08)

Resep kain sebelumnya mengikat hash **seluruh** baris `erp.materials`. Native (`erp._recalculate_material_cost_core`) menulis ulang stok tersimpan, biaya rata-rata, `row_version` dan `updated_at` pada setiap penerimaan atau pemakaian bahan, sehingga setiap barang masuk/keluar membuat resep yang sudah direview menjadi UNKNOWN. Kini identitas review memakai `cp7_fabric_native.material_hash`: semua field master (id, SKU, nama, jenis, satuan, aktif, kategori aksesori, waktu dibuat) tanpa cache stok/biaya dan penghitung audit. Revisi master yang nyata tetap membatalkan review; counterfixture fabric13 `P08_FABRIC_MASTER_CHANGED` kini mengganti nama master (bukan hanya menaikkan `row_version`), dan kontrol SQL Shell menambah bukti bahwa penulisan ulang cache stok/biaya tidak membatalkan review (25 → 26 kontrol). Seluruh baris bahan tetap masuk sumber analisis, jadi Original lama tetap `ARCHIVED_STALE` setelah gerakan stok.

## Penerima (frontend)

`src/nativeAnalysis.ts` kini menerima angka fisik kain hanya dalam batas kernel: terpasang harus 0 dan ASSUMED dengan asumsi resep; sisa layak tidak negatif; tambahan dari luar harus ASSUMED, butuh terpasang dan sisa layak yang diketahui, dan tidak boleh melebihi gross − terpasang − sisa layak. Baris kain yang belum direview tetap wajib UNKNOWN. Teks tampilan kebutuhan bahan menjelaskan bahwa sisa layak bukan reservasi stok dan hanya PO yang tercatat di ERP yang dihitung.

## Oracle dan kasus

Deklarasi: `NATIVE_FABRIC_PHYSICAL.json` — 21 kasus (16 DB, 2 race nyata dua sesi, 1 HTTP Auth nyata, 2 browser desktop/mobile). Jalur angka KNOWN memakai fixture analisis dengan WIP saldo awal yang terikat ke produk (gap 93 × 2 = 186: terpasang 0, sisa layak 10, tambahan 176; dengan PO tepat waktu 50: 126). Jalur draf rencana memakai fixture rencana (gap 85 × 2 = 170) yang WIP sejenisnya NEEDS_CHECK, sehingga terpasang dan tambahan dari luar UNKNOWN dengan batas atas 160. Kedua fixture dipertahankan: yang terikat untuk jalur pasti, yang ambigu untuk UNKNOWN dan batas atasnya.

Label: hanya komposisi draf Native yang bertaut (atau tidak ada alokasi sama sekali) yang KNOWN. Terpasang, bagian stok bebas dan tambahan dari luar tetap ASSUMED karena bertumpu pada resep dan skenario; fixture yang terikat produk tidak membuatnya KNOWN. Semua operand dibuat lewat perintah publik yang tidak diubah (penerimaan, rencana → draf Native, SAVE_DRAFT/POST Native, impor OPEN_PURCHASE_ORDER). Satu kasus kernel diberi label sintetis dan tidak memberi kredit Native. Pemakaian per PCS 2 dan 0,1 adalah pilihan fixture, bukan nilai operasional pemilik.

Suite `NATIVE_FABRIC_RECIPE` (13 kasus) adalah pendahulu: ID dan jumlah tidak berubah; hanya oracle tiga angka fisik pada baris yang direview berubah: sisa layak 10 (satu roll bebas fixture); terpasang dan tambahan dari luar tetap UNKNOWN karena WIP sejenis fixture itu NEEDS_CHECK, dengan batas atas gross − 10 di alasan. Original `qualified13-e7` tetap disimpan apa adanya.

Karena tanda tangan mesin analisis berubah, fabric13, analysis152, attention284, plan39, Shell, dan CodeQL wajib dikualifikasi ulang di sumber ini (workflow `claude-p08-physical.yml` dan `claude-p08-shell.yml`).

## Perbaikan apply rencana (cacat kedua yang ditemukan P08)

Run CI 37360628807 menunjukkan lima kasus rencana → draf Native tetap gagal dengan `CP7_PLAN_SOURCE_CHANGED`, padahal setiap kasus hanya beberapa detik. Penyebabnya bukan jam menit seperti dugaan lokal sebelumnya (diagnosis itu salah karena dibandingkan sesudah rollback). `cp7_plan_native.apply` menulis draf Native (SAVE_DRAFT), lalu memeriksa ulang Original. Sejak P08, sidik jari Original memuat draf potong belum diposting pada kain yang direview, sehingga pemeriksaan ulang melihat draf buatannya sendiri sebagai perubahan sumber. Buktinya: draf pada kain lain (WRONG_MATERIAL) lolos, semua draf pada kain yang direview gagal.

Perbaikan: `apply` menandai draf barunya sendiri di `cp7_plan_native.apply_own_drafts` tepat sebelum pemeriksaan ulang, lalu menghapusnya. `physical_source` mengabaikan draf itu hanya bila `txid` sama dengan transaksi yang sedang berjalan. Baris penanda tidak pernah terlihat transaksi lain dan tidak pernah ter-commit. Semua perubahan lain (stok, draf lain, PO, intent) tetap dibandingkan. Tabel ini privat (RLS false, pemilik `cp7_plan_writer`, `cp7_capture` hanya SELECT dua kolom) dan diverifikasi kosong di luar apply.

Akibat yang disengaja: setelah satu apply ter-commit, Original lama menjadi `ARCHIVED_STALE` karena draf baru bertaut ke target yang direview. Apply berikutnya perlu analisis baru. Ini gagal-tertutup: tidak ada angka lama yang dipakai ulang.

Run CI pertama dan kedua tetap tercatat FAIL. Retry di `link()` tetap dibatasi pada perbedaan jam saja.

## Bukti lokal (bukan bukti kualifikasi)

LOCAL_PG16_DEV (5 Okt 2026): kontrol SQL Shell kain 27/27 PASS (kontrol batas skala baru terbukti gagal pada SQL lama, lulus pada perbaikan), uji unit penerima dan DOM PASS, build dan pemeriksaan keamanan PASS, kasus DB fabric13 penerus 8/8 PASS. Kasus `P08_PHYSICAL_LINKED_DRAFT_KNOWN` lulus lokal setelah perbaikan apply. Hasil kualifikasi hanya dari CI (tabel di bawah).

## Riwayat CI

| Run | Commit | Hasil | Catatan |
|---|---|---|---|
| 37357315101 | 1850619c | FAIL (5/5 suite, 0 kasus) | `F03_UNDECLARED_ACL_DELTA` pada `erp.bb_commitment_line_remaining_v1(uuid,uuid)`. Diperbaiki di ebf3a394 (hanya deklarasi). |
| 37360628807 | ebf3a394 | fabric13 PASS, analysis152 PASS, plan39 PASS, attention284 PASS; fabric-physical21 INCOMPLETE 13/21 | Native 11/16 dan race 1/2: `CP7_PLAN_SOURCE_CHANGED` karena apply memeriksa ulang drafnya sendiri (diperbaiki di 0cb8994d). Browser 0/2: fixture `state` tanpa `today` (`KeyError`). |
| 37366015511 | 7b89f767 | analysis152 PASS, plan39 PASS; fabric-physical21 INCOMPLETE 17/21; fabric13 dan attention284 tidak dijalankan | Perbaikan apply terbukti (semua kasus draf bertaut lulus). Sisa: `P08_PHYSICAL_POSTED_ISSUE_ONCE` dan race `NATIVE_POST`, karena fixture memanggil helper `post` milik GPT saat sesi masih berperan `authenticated` (izin baca `erp.cutting_groups`). Browser 0/2: `KeyError: 'today'` yang sama. Diperbaiki di fixture saja (kembali ke admin sebelum `post`; `today` dikirim pada setiap panggilan fixture); oracle tidak diubah. fabric13/attention284: "job was not acquired by Runner" (kapasitas runner, bukan kode), dijalankan ulang. |

## Batas

Belum ada: aktivasi reminder kain (P18), skala representatif (P19), audit independen (P20), pemasangan (P21). Aksesori BOM tetap terpisah (terpasang/sisa/tambahan aksesori masih UNKNOWN).

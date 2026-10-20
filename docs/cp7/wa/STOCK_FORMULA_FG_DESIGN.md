# SS-1..SS-3 Titik pesan ulang barang jadi, kain, dan aksesori dengan rumus (desain teknis, 20 Okt 2026)

Dasar: owner D17-8 dan D17-9 (kutipan persis di `docs/cp7/OWNER_DECISIONS_20261008.md`), usulan
`docs/cp7/wa/PROPOSAL_SAFETY_STOCK_R6_20261020.md`, riset 28 Sep `docs/cp7/benchmark-decisions.md` (MIT ESD.260; kontrak
DAYS versus STATISTICAL tidak boleh ditumpuk). Kode: `scripts/cp7-src/stock-formula/formula.sql`. Kasus:
`scripts/cp7_stock_formula_cases.py` (dijalankan di suite "CP7 WA Forward", deklarasi `docs/cp7/wa/WA_FORWARD.json`).

## Barang dan angka

| Bagian | Aturan | Sumber |
|---|---|---|
| Barang | Satu versi produk yang berlaku dan aktif per akar identitas; kunci `root:size` (sama dengan target analisis) | `erp.products` |
| Stok bebas | Jumlah `qty_signed` GRADE_A + GRADE_B, semua gudang, `physical_at` dan `system_created_at` ≤ sekarang; cadangan draf penjualan sudah keluar | `erp.fg_stock_movements` (aturan ketersediaan analisis yang sudah diterima, `NATIVE_SELLABLE_GRADE_A_AND_B`) |
| Penjualan per hari | Gerakan `SALE` yang bukan pembalik dan tidak punya pembalik yang sudah diketahui, per hari WIB lengkap dalam jendela (bawaan 30 hari, sampai kemarin) | sama |
| Hari terhitung | Hari yang ada penjualan, atau yang diawali stok bebas > 0. Hari kehabisan stok tanpa penjualan tidak dihitung sebagai permintaan nol (riset 28 Sep) | saldo awal jendela + gerakan harian |
| D, σ | Rata-rata dan simpangan baku sampel penjualan per hari terhitung; perlu ≥ 14 hari terhitung | |
| Lama produksi L | Median `produced_at − cut_at` (hari) lot asal PRODUCTION dengan QC POSTED, potongan sudah keluar bahan, 365 hari terakhir, per model, dari ≥ 3 potongan; kalau tidak ada: `lead_days` profil perencanaan barang itu (versi produk sama); kalau tidak ada: belum cukup data | `erp.fg_lots`, `erp.cutting_groups`, `erp.production_orders`, `erp.qc_*`, `cp7_profile.profiles` |
| Cadangan (safety stock) | STATISTICAL: z × σ × √L, z = 1,2816 / 1,6449 / 2,3263 untuk 90 / 95 / 99%; DAYS: D × `buffer_days` bila profil barang mengisinya. Tidak pernah keduanya | |
| Titik pesan ulang | ceil(D × L + cadangan) | |
| Angka manual | Owner/Admin per barang, menggantikan rumus; 0 berarti tidak pernah diingatkan; hapus = kembali ke rumus | `cp7_stock_formula.manual_points` |
| Sedang diproduksi | WIP potong yang sudah diterima (`cp7_wip.capture_cutting_sources` + `normalize_cutting`, pool CUT, milik perusahaan) untuk model dan ukuran barang, atas potongan dari PO yang tidak FINISHED/CANCELLED; > 200 potongan, sumber tidak lengkap atau normalisasi menolak: belum bisa dihitung | aturan pembaca langsung `cp7_plan_native.staged_live`, kecuali pengecualian PO selesai |
| Menipis | titik > 0 dan stok bebas + sedang diproduksi ≤ titik; kalau sedang diproduksi belum diketahui: stok bebas ≤ titik | |

Batas yang ditulis jujur:
- Tingkat layanan 95% belum diuji ke data penjualan owner (tidak ada di lingkungan uji); diuji sesudah CP7C.
- Waktu tunggu dari keputusan produksi sampai potong tidak tercatat di ERP, jadi lama produksi terukur dimulai dari potong.
  Owner bisa memakai angka manual bila perlu.
- Sedang diproduksi dihitung per model dan ukuran, lalu dihitung untuk setiap barang model dan ukuran itu (aturan analisis
  yang sudah ada). Kalau satu model punya beberapa barang per ukuran (warna/merek), angkanya sama di masing-masing barang.
- PO yang sudah FINISHED tidak dihitung: sisa WIP-nya sudah ditutup ke biaya saat PO diselesaikan (`finish.sql`).

## Kapan dihitung

- Tiap menit oleh tick pengumpul Pengingat sistem (`cp7_alert_native.collect_tick` → `cp7_stock_formula.fg_source()`), dengan
  identitas owner yang menyimpan pengaturan WhatsApp dan hak layar Ringkasan Barang Jadi (`warehouse.fg.view`).
- Semua barang dihitung ulang dalam satu kueri tiap kali (bukan "hanya yang berubah"): hasilnya sama untuk setiap perubahan,
  dan lebih sederhana dibuktikan. Waktu terukur: 0,6 detik untuk 2.000 barang dan 202.000 gerakan (lokal, JIT mati); kasus
  `SS1_VOLUME_2000_ITEMS_EVERY_MINUTE` memeriksanya di CI dengan batas 3 detik. Baris hasil hanya ditulis ulang bila nilainya
  berubah.
- Sedang diproduksi dibaca per model dalam anggaran 2 detik per tick: model barang yang menipis dulu (bila bacaan > 55 detik),
  lalu model lain yang punya PO berjalan (bila bacaan > 10 menit). Model yang tidak punya potongan berjalan: 0 tanpa dibaca.
- Satu kunci modul (`CP7:FORMULA:FG`). Pemanggil yang mendapatinya terpegang (tick kirim, atau simpan owner yang sedang
  berjalan) tidak menulis apa pun: barang yang menipis pada hitungan terakhir dicek ulang ke stok bebas saat itu, dengan titik
  dan bacaan sedang diproduksi hitungan itu (kasus `WAF_RACE_FG_BUSY_RECHECKS_LIVE_STOCK`). Tombol "Hitung sekarang" ditolak
  `CP7_FORMULA_BUSY`.
- Sebelum pesan WA dikirim, tick kirim membaca sumber ini lagi; barang yang stoknya sudah naik menjadi
  `RESOLVED_BEFORE_SEND` (kasus `WAF_FG_RESOLVED_BEFORE_SEND`).

## Pemasangan dan hak

- Skema `cp7_stock_formula` milik `cp7_capture` (peran CP7 yang sudah membaca stok, penjualan, produksi, WIP, dan profil
  perencanaan). Untuk barang jadi tidak ada hak baca Native baru; untuk bahan ditambah hak baca kolom: empat kolom
  `erp.material_stock_movements`, dua kolom `erp.fabric_master_profiles`, dan `location_id` `erp.bc_accessory_zones_v1`.
  Dipasang oleh bundle WA sebelum `alerts.sql`; diverifikasi `cp7_alert_bundle.verify_formula`.
- Modul pengingat (`cp7_alert`) hanya boleh menjalankan `cp7_stock_formula.fg_source()` dan `material_source(text)`.
- RPC: `erp_cp7_get_fg_reorder_v1` (baca, `warehouse.fg.view`), `erp_cp7_refresh_fg_reorder_v1` (hitung sekarang, sama),
  `erp_cp7_save_fg_reorder_manual_v1` dan `erp_cp7_save_stock_formula_settings_v1` (Owner/Admin dengan `warehouse.fg.view`;
  revisi diharapkan, id permintaan sekali pakai, riwayat tidak bisa diubah).

## Beda dari usulan

- Angka manual disimpan di tabel CP7 `manual_points`, bukan di `erp.stock_policy_versions`. Alasan: tabel Native terikat ke
  satu versi produk (bukan akar identitas), mewajibkan angka target stok, hanya satu perubahan per tanggal, dan penulisnya
  ditutup untuk browser sejak R4-01. Isinya tidak dibaca. Saat CP7C: hitung baris `basis_source='MANUAL'` di Enteng (baca saja);
  kalau ada, angkanya dimasukkan ulang lewat layar baru.
- Usulan menyebut "dihitung ulang hanya untuk barang yang berubah"; yang dibuat menghitung ulang semua barang tiap menit
  (lihat "Kapan dihitung"). Hasil untuk owner sama.

## Kain dan aksesori (SS-2, SS-3)

Kode: `scripts/cp7-src/stock-formula/materials.sql`. Kasus: `SS2_*` dan `SS3_*` di `scripts/cp7_stock_formula_cases.py`, dan
`WAF_FABRIC_REORDER_POINT_FORWARDED`, `WAF_ACCESSORY_REORDER_POINT_FORWARDED`, `WAF_RACE_MATERIAL_BUSY_RECHECKS_LIVE_STOCK`,
`WAF_HTTP_MATERIAL_REORDER_SCREEN` di suite WA.

| Bagian | Kain | Aksesori |
|---|---|---|
| Barang | Bahan aktif jenis FABRIC | Bahan aktif jenis ACCESSORY |
| Pemakaian per hari | Keluar ke potong (`CUTTING_ISSUE`) dikurangi kembali dari potong (`CUTTING_RETURN`), pemakaian pabrik (`INTERNAL_USE`), keluar ke mandor (`CONTRACTOR_ISSUE`) | Nota mandor (`CONTRACTOR_ISSUE`) dan pemakaian pabrik (`INTERNAL_USE`), dikurangi retur nota yang dikreditkan layak pakai (`ADJUSTMENT` dari `BC_NOTE_RETURN_CREDIT` ke gudang, bukan ke area rusak) |
| Gerakan yang dibalik | Gerakan yang punya pembalik dan pembaliknya tidak dihitung (aturan STK01 Bahan & Roll) | sama |
| Stok | Semua lokasi (aturan Ringkasan Gudang dan minimum kain) | Yang Bahan & Roll sebut "ada di gudang": gudang bahan aktif, bukan pos servis, area periksa, atau area rusak |
| Sedang dipesan | Sisa PO terbuka saldo awal (`erp.bb_commitment_line_remaining_v1`, sumber yang dipakai analisis kain) | Tidak ada sumbernya; 0 |
| Lama kirim L | Isian "lama kirim (hari)" per bahan oleh Owner/Admin (`material_settings`, riwayat tidak bisa diubah); kosong: belum cukup data | sama |
| Angka manual | Minimum di Kain & Benchmark (tidak diubah); kain itu tetap di pengingat lama "Stok kain di bawah minimum" (stok < minimum) | Angka manual di pengaturan yang sama; 0 = tidak pernah diingatkan; kosong = rumus |
| Titik | Rumus barang jadi, dalam satuan bahan, dibulatkan ke atas 0,01 | sama |
| Menipis | Kain pakai rumus: stok + dipesan ≤ titik | stok ≤ titik (rumus atau manual) |
| Pengingat | `FABRIC_AT_REORDER_POINT` "Stok kain menipis" (hak Bahan & Roll + Kain & Benchmark) | `ACCESSORY_AT_REORDER_POINT` "Stok aksesori menipis" (hak Aksesori) |

- Dihitung tiap menit bersama barang jadi, satu kunci modul yang sama. Satu tick menghitung sekali untuk ketiga sumber
  (`ensure_computed()`, kunci: waktu mulai perintah). Saat kunci dipegang, kain/aksesori yang menipis dicek ulang ke stok saat
  itu dengan titik dan angka dipesan hitungan terakhir, tanpa menulis apa pun (kasus race bahan).
- RPC: `erp_cp7_get_material_reorder_v1`, `erp_cp7_refresh_material_reorder_v1`, `erp_cp7_save_material_reorder_v1`.

### Beda dari usulan (perlu keputusan owner)

- Usulan §3: "Peringatan 'stok kain di bawah minimum' yang sudah ada tetap jalan, memakai angka rumus bila tidak ada angka
  manual." Yang dibuat: kain yang memakai rumus diingatkan dengan judul sendiri "Stok kain menipis"; judul lama tetap hanya
  untuk kain yang punya minimum. Alasan: pengingat lama dan daftar Ringkasan Gudang dibuktikan sama (kasus
  `WAF_FABRIC_EQUALS_WAREHOUSE_SUMMARY`), dan aturannya beda (stok < minimum, tanpa barang dipesan). Kalau owner memilih
  satu judul, keduanya digabung dan Ringkasan Gudang ikut diubah.
- Usulan §3/§4: lama kirim diisi "di data master". Panel isian dipasang di Master Data (Kain & Benchmark, Aksesori & Harga
  Mandor) dan juga di Gudang (Bahan & Roll, Aksesori); datanya satu.
- Usulan §4: "Kebutuhan aksesori dari rencana produksi ikut diteruskan ke WA" dengan cek ulang sebelum kirim. Belum dibuat:
  analisis rencana produksi selalu menyatakan kebutuhan aksesori "belum diketahui" (aturan yang sudah diterima: pemakaian
  aksesori per potong tidak tercatat), jadi tidak ada kebutuhan yang bisa dicek ulang atau dikirim. Yang dikirim ke WA untuk
  aksesori adalah "Stok aksesori menipis" dari rumus stok di atas.
- Usulan §5 "Belum diperiksa: pemakaian aksesori per hari": sudah diperiksa, sumbernya nota mandor, pemakaian pabrik, dan
  retur nota yang dikreditkan (tabel di atas).

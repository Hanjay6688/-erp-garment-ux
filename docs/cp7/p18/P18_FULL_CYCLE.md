# P18 — siklus penuh stok → WIP → HPP → buku besar → hutang → kas

Status: bukti penulis (writer). Ini bukan audit independen P20, bukan pemasangan P21, dan bukan GO produksi. `full_P18_acceptance=false`.

## Yang dibuktikan

Kerangka CP7 mendefinisikan P18 sebagai "Stock/WIP/HPP/GL/payables/cash reconcile end-to-end". Kasus E01 yang sudah lulus berhenti di penjualan, kas pelanggan dan retur; hutang yang muncul selama produksi tidak pernah dibayar. Skenario ini meneruskan lembar kerja E01 yang dibekukan (`framework-v2/04_BUKTI_DAN_ORACLE.md`) sampai semua hutang lunas. Tidak ada angka oracle baru: semua angka berasal dari E01 dan hutang yang dibuatnya.

| Langkah | Penulis yang dipakai |
|---|---|
| Penerimaan bahan 100 × 10, potong 60, jahit 30+30, laundry 30+30, QC 20+40, HPP final 900 (15/pcs) | Jalur E01 yang sudah lulus, tanpa perubahan |
| Upah mandor: nota kerja → payroll disetujui 180 (120 jahit + 60 aksesori) | Jalur E01 |
| Jual 20 pcs × 25, kas pelanggan 200, retur 5 pcs | Jalur E01 (perintah CP7 penjualan) |
| Bayar supplier bahan 400 lalu 600 | Run pertama: posting Native di atas baris DRAFT. Penerusnya memakai perintah aplikasi baru `erp_cp7_create_supplier_payment_v1` |
| Bayar vendor laundry 120 | Penulis aplikasi `erp_save_laundry_bd_action_v1` `PAY_VENDOR_DOCUMENT` |
| Bayar upah mandor 180 | Penulis aplikasi CP7 `erp_cp7_save_payroll_v1` `PAY` |

## Pencocokan di setiap batas

Ada 8 batas. Di setiap batas, perubahan buku besar sejak awal harus sama persis dengan buku pembantu masing-masing:

- nilai stok bahan;
- WIP per PO;
- nilai lot barang jadi;
- sisa hutang supplier dari dokumen;
- sisa invoice vendor;
- hutang mandor dari payroll;
- sisa piutang dari invoice;
- kas.

Pengecekan tambahan yang ikut dijalankan:

- **Dimensi:** hutang vendor dicek per `vendor_id`, hutang mandor per `contractor_id`, dan piutang per `customer_id`.
- **Akun lain:** perubahan pada akun di luar daftar ini membuat kasus gagal.
- **Neraca saldo:** harus nol.
- **Laporan keuangan:** posisi keuangan di awal, sesudah produksi dan di akhir dibandingkan langsung.

Sebelum titik awal diambil, kewajiban data fondasi diselesaikan dulu lewat penulis yang sudah diterima. Sesudah titik awal, hanya skenario ini yang menulis. Pengecekan juga memastikan pembersihan fondasi kedua tidak menulis apa pun.

## Hasil run pertama (sumber 8beab7fe)

Run 37488624358, job 112355139471: `status=PASS`, 1/1 kasus, `cp6_restored=true`, `advisor_gate=true`. Log job lengkap dan receipt ada di `../evidence/p18-full-cycle/first-8beab7fe/`. Artefak 1,6 MB tidak bisa diunduh dari sesi ini, tetapi seluruh titik batas dan ringkasan probe tercetak di log.

| Batas | Bahan | WIP | Barang jadi (pcs) | Hutang supplier | Hutang vendor | Hutang mandor | Piutang | Kas |
|---|---|---|---|---|---|---|---|---|
| B1 produksi, HPP final | 400 | 0 | 900 (60) | 1.000 | 120 | 180 | 0 | 0 |
| B2 penjualan diposting | 400 | 0 | 600 (40) | 1.000 | 120 | 180 | 500 | 0 |
| B3 kas pelanggan | 400 | 0 | 600 (40) | 1.000 | 120 | 180 | 300 | +200 |
| B4 retur 5 pcs | 400 | 0 | 675 (45) | 1.000 | 120 | 180 | 175 | +200 |
| B5 bayar supplier 400 | 400 | 0 | 675 (45) | 600 | 120 | 180 | 175 | −200 |
| B6 bayar supplier 600 | 400 | 0 | 675 (45) | 0 | 120 | 180 | 175 | −800 |
| B7 bayar vendor 120 | 400 | 0 | 675 (45) | 0 | 0 | 180 | 175 | −920 |
| B8 bayar upah 180 | 400 | 0 | 675 (45) | 0 | 0 | 0 (PAID) | 175 | −1.100 |

Di setiap baris, angka buku besar dan buku pembantu sama persis.

**Akhir siklus:**

| Pos | Angka |
|---|---|
| Bahan | 400 |
| Barang jadi | 675 |
| Piutang | 175 |
| Kas | −1.100 |
| Pendapatan | 375 |
| HPP penjualan | 225 |
| Laba kotor | 150 |

Persamaan neraca juga tertutup. Aset berubah +150, yaitu 400 + 675 + 175 − 1.100. Laba berjalan juga +150. Jadi selisih neraca tetap nol.

**Pengecekan tolakan dan pengulangan:**

- Posting ulang pembayaran supplier yang sama ditolak.
- Kelebihan bayar supplier sebesar 0,01 ditolak.
- Kelebihan bayar vendor 0,01 ditolak.
- Pengulangan dengan UUID yang sama, baik untuk pembayaran vendor maupun upah, mengembalikan hasil yang sama tanpa efek kedua.
- Dalam semua kasus di atas, buku besar tidak berubah.

## Hasil penerus (sumber 4042235f): semua hutang dibayar lewat aplikasi

Run 37490923997, job 112363128079: `status=PASS`, 1/1 kasus, `cp6_restored=true`, `advisor_gate=true`. Log dan receipt ada di `../evidence/p18-full-cycle/qualified-4042235f/`.

- Penulis yang dipakai:
  - supplier: `erp_cp7_create_supplier_payment_v1`;
  - vendor laundry: `PAY_VENDOR_DOCUMENT`;
  - upah mandor: payroll `PAY`.
- Kedelapan batas dan angka akhir sama persis dengan run pertama.
- Pengecekan pembayaran supplier:
  - pengulangan UUID tanpa efek kedua;
  - token tinjauan basi ditolak `CP7_SUPPLIER_PAYMENT_STALE_REVIEW`;
  - pembayaran sesudah lunas ditolak `CP7_SUPPLIER_PAYMENT_NOTHING_PAYABLE`;
  - buku besar tidak berubah pada semua tolakan.

## Temuan produk: pembayaran supplier belum ada di aplikasi

Sebelum perbaikan ini, aplikasi hanya bisa **melihat, membetulkan, dan membatalkan** pembayaran supplier. Pembayaran baru tidak bisa dicatat. Akibatnya hutang supplier tidak pernah bisa dilunasi dari ERP, sehingga angka hutang dan kas pasti salah.

Pembayaran vendor laundry dan upah mandor sudah punya penulis aplikasi, jadi hanya supplier bahan yang terdampak.

Penutupnya ada di `../SUPPLIER_PAYMENT_CREATE_HANDOFF.md`, berupa perintah owning baru di atas posting Native yang tidak diubah. Run pertama tetap tercatat apa adanya, yaitu memakai posting Native. Penerusnya membayar supplier lewat perintah aplikasi, dengan pemeriksaan tambahan:

- token tinjauan basi ditolak;
- pembayaran ditolak bila hutang sudah lunas;
- pengulangan UUID yang sama tidak menimbulkan efek kedua.

## Catatan untuk owner (bukan keputusan yang dikarang)

- **Kas boleh minus.** Native `erp.post_supplier_payment`, `erp.post_vendor_payment` dan pembayaran payroll tidak memeriksa saldo kas, jadi kas boleh menjadi minus; di skenario ini −1.100 karena tidak ada setoran modal. Ini perilaku CP6 yang sudah ada dan tidak diubah. Apakah kas boleh minus adalah kebijakan owner. Belum ada nilai kebijakan yang diputuskan untuk ini.
- **Hak bayar vendor laundry.** Penulis BD memakai hak `finance.hpp.manage`, bukan `finance.ap.pay`. Ini juga perilaku CP6 yang sudah ada dan hanya dicatat.

## Yang belum

- Langkah produksi di skenario ini masih lewat fixture Native E01. Belum ada perjalanan browser untuk produksi.
- Kasus P18 lain (E02–E08, E12–E14, E22, E24) punya suite F03 masing-masing. Hasil suite itu tidak dijumlahkan menjadi penerimaan P18 penuh.
- P19 kapasitas, P20 audit independen, P21 paket pemasangan dan GO tetap terbuka. CP6 tetap HOLD.

## Kasus kedua: harga supplier terlambat sesudah siklus penuh (E13)

Kasus `P18_E13_LATE_SUPPLIER_PRICE_AFTER_FULL_CYCLE` menjalankan siklus yang sama sampai B8. Setelah itu ternyata harga bahan di nota supplier 11, bukan 10. Pada saat itu bahan sudah dipotong, barang jadi sudah dijual dan diretur, dan semua hutang sudah lunas.

Koreksinya memakai penulis aplikasi "Benerin penerimaan" (`erp_cp7_correct_receipt_v1`), lalu selisihnya dibayar lewat `erp_cp7_create_supplier_payment_v1`.

Oracle-nya hanya diturunkan dari jumlah E01, tidak ada angka kebijakan yang dikarang:
- sisa bahan 40 m naik 40;
- HPP 60 pcs naik dari 15 ke 16, sehingga sisa barang jadi 45 pcs naik 45;
- HPP penjualan untuk 15 pcs bersih naik 15;
- hutang supplier naik 100.

| Batas | Bahan | WIP | Barang jadi (pcs) | Hutang supplier | Hutang vendor | Hutang mandor | Piutang | Kas |
|---|---|---|---|---|---|---|---|---|
| B9 harga 10→11 sesudah lunas | 440 | 0 | 720 (45) | 100 | 0 | 0 | 175 | −1.100 |
| B10 selisih 100 dibayar | 440 | 0 | 720 (45) | 0 | 0 | 0 | 175 | −1.200 |

**Pengecekan di batas ini:**
- Kedua pembayaran supplier lama dibalik dan diputar ulang ke penerimaan yang benar, dengan tanggal dan jumlah aslinya. Karena itu kas tidak berubah di B9.
- Semua `erp.run_v*_checks()` tidak berubah, dan `V2620U_JOURNAL_REVERSAL_BUSINESS_DATE` tetap 0.

**Akhir siklus:**
- Buku besar: bahan 440, barang jadi 720, piutang 175, pendapatan 375, HPP 240, kas −1.200.
- Laporan posisi keuangan: aset dan laba berjalan masing-masing naik 135.

Hasil CI dicatat di bawah sesudah run selesai. Kegagalan pertama tetap disimpan.

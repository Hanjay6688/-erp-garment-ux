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

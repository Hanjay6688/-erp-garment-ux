# Waktu penerimaan barang retur — perbaikan kecil OW-04

Sumber kontrak: `docs/erp-reliability-invariants.md`, Physical time. Barang
yang kembali adalah penerimaan fisik; waktu harus dikonfirmasi operator,
bukan disimpulkan dari saat halaman dibuka. Ini belum penyelesaian kredit/refund.

Expected sebelum perbaikan: input retur baru kosong, penulis tidak dapat
dijalankan tanpa waktu, perubahan waktu membatalkan konfirmasi pemeriksaan,
dan waktu WIB yang diketik menjadi tepat satu instant UTC pada payload.
Timestamp dokumen lama/correction berasal dari sumbernya dan tidak diubah.

Uji baru pada produk878/bb76 gagal: input justru berisi waktu buka halaman
(`local-physical-time-first-failure.log`: 1 gagal, 9 kontrol lulus).
Perbaikan membuang default `new Date()` dari formulir retur baru. Semua
validasi, token sumber, jumlah, HPP dan jalur penulis tetap yang sama.

Dua browser Native P11 desktop/HP diperkuat tanpa mengubah expected bisnis:
input harus kosong; setelah baris lengkap dan review, simpan masih terkunci;
operator mengisi waktu fixture WIB secara eksplisit lalu konfirmasi lagi.
Retur tersimpan harus memiliki instant yang tepat, termasuk replay balasan
hilang. Uji yang sudah ada tidak cukup karena sebelumnya bergantung default.
Jumlah kasus suite P11 tetap64. Workflow diaktifkan pada cabang writer;
checkout auditor memakai commit workflow itu dan merupakan sumber build UI.
Pin paket candidate/penulis/AB/harness tetap. Pemeriksa internal menelusuri
sumber browser dan mengoreksi penjelasan awal yang keliru menyamakan pin
candidate dengan sumber UI; perubahan pin yang tidak diperlukan dibatalkan.

Hasil browser Native perbaikan ini belum tersedia saat expected ditulis.
Tidak ada perubahan rumus uang atau implementasi penyelesaian retur lunas.

Sesudah perbaikan: **32/32 DOM** pada formulir retur, koreksi retur dan
pembayaran lulus (`local-physical-time-fixed.log`); TypeScript, Node syntax,
source/access/CSS ownership dan diff check lulus. Pemeriksa internal Sol Max
menelusuri urutan fixture: waktu retur yang diketik tepat2menit sesudah
waktu penjualan UI, dan sebelum waktu database, termasuk saat melewati
tengah malam WIB dan browser Los Angeles. Ini source review, bukan Native.

## Hasil Native pada kandidat yang memuat perbaikan

Kandidat `4e3c98b3ce04427c65c7bc7c1b21ec3bdacfea71`, tree
`29db6ac1b6fd80de2e1480930eeaae36713be621`: run39430283909 attempt1,
job118653236629 **64/64 PASS**, CP6 restored dan advisor PASS. SQL terpasang
`722aca08e1788960794e5b65aee4e7df774df6c62e68c781cffe8468a43c241f`
cocok komposisi bundle lokal kandidat. Receipt lengkap:
`CI_39430283909_PHYSICAL_TIME.json`.

Dua kasus `P11_RETURN_BROWSER_R10_DESKTOP_A` dan
`P11_RETURN_BROWSER_R10_MOBILE_B_RECOVERY` menjalankan assertion pada
`scripts/cp7_p11_returns_browser.mjs`: input kosong; simpan tetap terkunci
sesudah isian lain dan review; isi WIB membatalkan review; instant hasil
readback sama persis; replay balasan hilang di HP tidak membuat efek ganda.
Semua assertion uang, stok, HPP dan inverse lama tetap berjalan. Nilai baru
itu diperiksa oleh assertion, bukan kolom boolean tambahan pada receipt.

Reproduksi Native mengikuti `.github/workflows/cp7-p11-sales.yml` pada pin
tersebut, memakai database sekali pakai dan pin runtime yang tercatat dalam
workflow. Ini bukti baru untuk perbaikan waktu; bukan bukti CREDIT/REFUND
atau retur setelah lunas. Kontrol negatif `P11_RETURN_PAID_REFUSAL` tetap PASS.

## Kualifikasi silang perjalanan produksi E01

Pencarian semua browser `Catat retur pelanggan` menemukan satu pemakai lain:
`scripts/cp7_f03_e01_browser.mjs` pada4e masih mengandalkan default waktu.
Ini diagnosis sumber, bukan klaim kegagalan Native baru. Perbaikan alat uji
harus mengisi waktu fisik yang benar secara eksplisit, tanpa mengembalikan
default produk atau melonggarkan perhitungan. Sumber awal tetap tersimpan4e.

Expected sebelum perubahan alat: input kosong; simpan terkunci sampai waktu
diisi; perubahan waktu membatalkan review; waktu tersimpan persis input WIB
pada desktop/HP, termasuk replay dan tab kedua. Tetap produksi60PCS/HPP15,
jual20×25, bayar200, retur5/nilai125: FG45/nilai675, kas200, AR175,
pendapatan375, COGS225, laba kotor150. Seluruh assertion lama tetap.
Jumlah kasus E01 tidak diubah; hasil Native lanjutan belum tersedia di titik ini.

Hasil kemudian tersedia pada alat `5ae9979cb60f18b6db47524441f6ac6f7787d8e6`,
produk4e3c98b3 byte-identik: run39433112026 attempt1/job118663009654,
**4/4 PASS sekali jalan** (Native1/HTTP1/browser2), restore/advisor PASS.
Bundle `a7305cfc9ceacd5a2637a02f82f958d274c42a6af2c4031352fb31fcc43042c1`
cocok komposisi lokal. Kedua browser mempertahankan tepat angka expected
di atas dan assertion waktu; HP mempertahankan replay UUID identik serta
tab kedua tanpa penulisan ganda. Receipt: `CI_39433112026_E01.json`.
Reproduksi persis mengikuti `.github/workflows/cp7-f03-e01.yml` pada5ae.
Ini tidak mengubah kasus E01 menjadi retur lunas: bayar200, nilai tersisa
sebelum retur300, setelah retur125 masih AR175, sehingga kredit tidak terbit.

# OW-08b — empat butir koreksi uang/HPP (D17-13 2.18–2.21)

Owner (OPEN_WORK OW-08): "Jurnal kasbon bisa dibuka dari buku besar; piutang ke vendor laundry, cuci gagal tanpa tarif,
koreksi barang jadi lain di QC: periksa apakah tercakup keputusan owner (LAU-DEC06, dsb.), betulkan atau ajukan pilihan
bisnis." D17-16: "Semua tetap masuk scope."

| Butir | Sudah diputuskan Bos? | Status |
|---|---|---|
| 2.18 Jurnal kasbon dibuka dari buku besar | Tidak perlu keputusan baru | **Lulus** di database penuh: Native4 4/4 `6c8be6f6` (run 39847032024), bukti `kasbon-native4-6c8be6f6-pass.json`. Dua kegagalan alat uji sebelumnya disimpan (`kasbon-native4-eda58db5-first-failure.json`, `kasbon-native4-1f9fd987-second-failure.json`) |
| 2.19 Piutang ke vendor laundry | **Belum.** LAU-DEC06 hanya mengatur koreksi sesudah bayar memakai dokumen koreksi; kalimat "piutang vendor belum punya alur" di D11 adalah tulisan penulis, bukan keputusan Bos. D17-16 tidak menjawab pertanyaan ini per butir | Pertanyaan ke Bos (23 Okt): kelebihan bayar dicatat sebagai piutang ke vendor itu, dipotong ke tagihan berikutnya atau ditutup pengembalian tunai — ya/tidak. Belum dikerjakan sebelum dijawab |
| 2.20 Cuci gagal sebelum tarif vendor diketahui | Ya: LAU-DEC04 ("harga yang belum diketahui tidak boleh dianggap nol … tutup buku tertahan sampai harga diisi") | **Lulus** di database penuh: Native11 11/11 `efa800cd` (run 39886298512), bukti `wash-native11-efa800cd-pass.json`. Tutup buku tertahan sampai harga diisi lalu sama dengan kembaran bertarif; invoice laundry ditolak lalu tertagih 30,00 sesudah harga; penjualan mengikuti LAU-DEC04 (FG +24, HPP penjualan +6 saat harga diisi); harga hanya sekali oleh owner/admin. Kegagalan sebelumnya disimpan (`wash-native11-3c3dea91-admission-failure.json`, `-cc5766e7-first-failure.json`, `-c6e073b5-second-failure.json`) |
| 2.21 Koreksi barang jadi lain di QC | Ya: D14-10 ("tampilkan bagian mana yang harus dibetulkan terlebih dahulu"), D15-4 | **Lulus** di database penuh: Native9 9/9 `048f194e` (run 39884816533), bukti `fgqc-native9-048f194e-pass.json`. Baris pembalik barang jadi dari penjualan, retur, penyesuaian stok dan rework membuka dokumennya; penolakan batal QC menyebut dokumen penghalang dan menunya. Kegagalan pertama disimpan (`fgqc-native9-fe95ba50-first-failure.json`). Belum dicoba dengan data nyata: QC di luar POSTED/REVERSED (tidak ada penulis yang membuatnya) dan aksesori yang sudah masuk gaji |

Penelusuran lengkap (baris kode dan kutipan keputusan): ringkasan agen penelusur 23 Okt, disalin di bagian bawah.

## Ringkasan penelusuran

- 2.19: koreksi turun invoice laundry yang melebihi seluruh utang ke vendor ditolak `BD_CORRECTION_EXCEEDS_PAYABLE`
  (`scripts/cp6_bd_objects_invoice.sql:17-20,545-551`); penjaga buku besar menolak utang vendor negatif; tidak ada akun
  piutang/uang muka vendor laundry selain uang muka saldo awal; uang masuk dari vendor tidak punya jalur yang tertaut.
- 2.20: `POST_FAILED_WASH` selalu meminta tepat satu tarif vendor/proses; tanpa tarif, cuci gagal dan "kembali belum
  diproses" tidak bisa dicatat; layar mematikan tombol dengan "tarif authoritative belum cocok".
- 2.21: "tidak didukung" di `QC_SOURCE_HANDOFF.md:7` adalah tautan sumber baris pembalik barang jadi (selain QC dan retur
  terkoreksi); penolakan batal QC (`erp.reverse_qc`) belum menyebut dokumen penghalang.

## Penerus keputusan 29 Oktober 2026

Butir 2.19 sudah dijawab owner C: **keduanya**, pemakaian pada tagihan berikut
dan pengembalian kas/bank. Lihat `docs/cp7/OWNER_VENDOR_RECEIVABLE_20261029.md`.
Catatan “belum dijawab” di atas adalah histori. Delta `cp7_vendor_receivable`
sedang diimplementasikan pada cabang A terpisah; belum qualified dan belum ada
kelulusan browser untuk delta itu. Tidak mengubah bukti 2.18/2.20/2.21.

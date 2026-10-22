# OW-08b — empat butir koreksi uang/HPP (D17-13 2.18–2.21)

Owner (OPEN_WORK OW-08): "Jurnal kasbon bisa dibuka dari buku besar; piutang ke vendor laundry, cuci gagal tanpa tarif,
koreksi barang jadi lain di QC: periksa apakah tercakup keputusan owner (LAU-DEC06, dsb.), betulkan atau ajukan pilihan
bisnis." D17-16: "Semua tetap masuk scope."

| Butir | Sudah diputuskan Bos? | Status |
|---|---|---|
| 2.18 Jurnal kasbon dibuka dari buku besar | Tidak perlu keputusan baru | Dibuat (`scripts/cp7_kasbon_source/`, layar Payroll & Kasbon). Uji pertama 1/4: kesalahan alat uji (bukan produk), bukti `kasbon-native4-eda58db5-first-failure.json`. Uji kedua 3/4: kasus "jenis jurnal lain tidak berubah" hanya menemukan 2 jenis jurnal di data uji (keduanya sama dengan pembaca lama); kasus itu kini membuat sendiri rantai PO selesai, payroll dan kasbon lalu membandingkan semua jenis, bukti `kasbon-native4-1f9fd987-second-failure.json`; uji ketiga dikirim |
| 2.19 Piutang ke vendor laundry | **Belum.** LAU-DEC06 hanya mengatur koreksi sesudah bayar memakai dokumen koreksi; kalimat "piutang vendor belum punya alur" di D11 adalah tulisan penulis, bukan keputusan Bos. D17-16 tidak menjawab pertanyaan ini per butir | Pertanyaan ke Bos (23 Okt): kelebihan bayar dicatat sebagai piutang ke vendor itu, dipotong ke tagihan berikutnya atau ditutup pengembalian tunai — ya/tidak. Belum dikerjakan sebelum dijawab |
| 2.20 Cuci gagal sebelum tarif vendor diketahui | Ya: LAU-DEC04 ("harga yang belum diketahui tidak boleh dianggap nol … tutup buku tertahan sampai harga diisi") | Dibuat (`scripts/cp7_laundry_unknown_wash/`, layar Laundry dan BD Laundry, rincian `CUCI_GAGAL_TARIF.md`): cuci gagal bisa dicatat dengan "Tarif vendor belum diketahui" (biaya belum dihitung, bukan nol), HPP PO belum final, tutup buku tertahan sampai harga diisi sekali oleh owner/admin, invoice laundry ditolak sampai harga ada. Uji lokal lulus; uji database penuh (Native11) dikirim |
| 2.21 Koreksi barang jadi lain di QC | Ya: D14-10 ("tampilkan bagian mana yang harus dibetulkan terlebih dahulu"), D15-4 | Dibuat (`scripts/cp7_fg_correction_source/`, rincian `KOREKSI_FG_QC.md`): baris pembalik stok barang jadi dari penjualan, retur, penyesuaian stok dan rework kini bisa dibuka ke dokumennya; penolakan batal QC menyebut nomor dokumen penghalang dan menu tempat membetulkannya. Uji lokal lulus; uji database penuh (Native9) dikirim |

Penelusuran lengkap (baris kode dan kutipan keputusan): ringkasan agen penelusur 23 Okt, disalin di bagian bawah.

## Ringkasan penelusuran

- 2.19: koreksi turun invoice laundry yang melebihi seluruh utang ke vendor ditolak `BD_CORRECTION_EXCEEDS_PAYABLE`
  (`scripts/cp6_bd_objects_invoice.sql:17-20,545-551`); penjaga buku besar menolak utang vendor negatif; tidak ada akun
  piutang/uang muka vendor laundry selain uang muka saldo awal; uang masuk dari vendor tidak punya jalur yang tertaut.
- 2.20: `POST_FAILED_WASH` selalu meminta tepat satu tarif vendor/proses; tanpa tarif, cuci gagal dan "kembali belum
  diproses" tidak bisa dicatat; layar mematikan tombol dengan "tarif authoritative belum cocok".
- 2.21: "tidak didukung" di `QC_SOURCE_HANDOFF.md:7` adalah tautan sumber baris pembalik barang jadi (selain QC dan retur
  terkoreksi); penolakan batal QC (`erp.reverse_qc`) belum menyebut dokumen penghalang.

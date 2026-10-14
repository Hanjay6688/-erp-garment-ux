# SG-01: batal Bagi Potongan sebelum dijahit (Fable FABLE-009, Astra SG-01)

Dibangun menurut `SG01_PICKUP_CORRECTION_DESIGN.md` tingkat (a). Tingkat (b), yaitu ganti Mandor sesudah jahit, tetap
ditolak.

## Yang terjadi saat dibatalkan
| Data | Sesudah dibatalkan |
|---|---|
| Bagi Potongan (`erp.cutting_pickups`) | `REVERSED` + siapa/kapan/alasan. Batch dan alokasinya tetap tersimpan sebagai riwayat. Semua pembaca Native (antrean Bagi Potongan, WIP, laundry) hanya membaca pickup `POSTED`, jadi batch lama tidak muncul lagi |
| Potongan (`erp.cutting_groups`) | `CUT`, jam diambil kosong, nama pelaksana kembali ke nilai sebelum POST. Bahan tetap tercatat keluar dari gudang |
| PO | Status/tahap kembali ke nilai sebelum POST, kecuali masih ada potongan lain di PO itu yang sudah dibagi (tetap `SEWING`). Mandor dikosongkan hanya bila POST ini yang mengisinya dan tidak ada hal lain yang mengikat Mandor itu ke PO |
| Stok, jurnal, WIP, payroll | Tidak ada yang ditulis (POST pickup memang tidak menulisnya) |

Nilai sebelum POST dibaca dari jejak audit Native pada POST itu sendiri: satu baris pickup `DRAFT→POSTED`, lalu pada
statement yang sama baris potongan dan baris PO. Kalau jejak tidak lengkap, atau datanya berubah sejak POST, pembatalan
ditolak dan alasannya disebut.

## Ditolak bila
Ditolak bila ada proses lanjutan atau dokumen apa pun yang menunjuk potongan atau batchnya, termasuk draf:
- event WIP;
- setoran jahit;
- QC;
- laundry (termasuk baris batch);
- lot barang jadi;
- kasus BS;
- scrap;
- koreksi jumlah;
- terminal jahit;
- pool HPP absensi;
- tanda WIP;
- kain kantong.

Juga ditolak bila PO `ON_HOLD`, `FINISHED`, atau `CANCELLED`.

Setiap penghalang disebut dengan id dan statusnya.

## Delta Native yang dideklarasikan (`scripts/cp7_pickup_reversal_bundle.py`, dipulihkan persis saat uninstall)
1. `erp.guard_cutting_pickup_lifecycle()`: `POSTED→REVERSED` diizinkan hanya di dalam perintah ini
   (`cp7_cutting_correction.pickup_context`, transaksi yang sama), dan hanya kolom pembatalan yang boleh berubah. Semua
   ubah atau hapus lain pada pickup non-draf tetap ditolak seperti sebelumnya.
2. `erp.normalize_cutting_group_pickup()`: jam diambil boleh dikosongkan walau bahan sudah keluar, hanya di dalam perintah
   ini. Laundry, setoran jahit yang sudah diposting, dan lot barang jadi tetap menolak seperti sebelumnya.

Penulis pickup Native dan semua penjaga PO tidak berubah. Potongan dibagi ulang lewat POST pickup Native biasa.

## Akses
- OWNER/ADMIN dengan `production.distribution.view`, `edit_draft`, dan `post`.
- Idempoten per (aktor, request).
- Token tinjauan dari seluruh data yang dibaca.
- Kunci `CP6FLOW` per potongan.
- Riwayat `pickup_history` tidak bisa diubah.

## Bukti
- Kasus CP17:
  - `CP17_SG01_PICKUP_REVERSE_BEFORE_SEWING`: balik, ulang request yang sama memberi hasil identik, PO/potongan/Mandor
    pulih sesuai nilai yang dibaca langsung sebelum pickup, stok dan jurnal tidak berubah, lalu POST ulang ke Mandor lain.
  - `CP17_SG01_PICKUP_REVERSE_REFUSED`: penjaga Native tetap menolak tulis langsung, token basi ditolak, alasan pendek
    ditolak, draf setoran jahit memblok, dan tidak ada yang berubah.
- Uji lokal pada basis data tiruan (PG16): fungsi penjaga dan audit Native yang asli; delta dipasang lewat blok DO bundle;
  PO yang dipakai dua potongan tetap `SEWING` dan Mandornya tidak berubah.
- Layar `src/PickupReversalPanel.tsx` (+ uji DOM) ada di halaman Bagi Potongan, dan hanya muncul untuk pickup yang sudah
  diposting.

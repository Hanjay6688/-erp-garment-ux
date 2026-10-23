# Cuci gagal yang tarif vendornya belum diketahui (OW-08b, baris 2.20)

Sudah dibuat dan sudah dicoba di komputer kerja. Belum diuji di database percobaan lengkap (CI), jadi belum boleh dipakai
sebelum hasil uji itu lulus.

Aturan Bos (LAU-DEC04): harga yang belum diketahui tidak boleh dianggap nol atau membuat HPP terlihat final. Statusnya harus
jelas, dan tutup buku yang terdampak tetap tertahan sampai harga dan biayanya selesai dihitung.

## Yang sekarang bisa

- **Mencatat cuci gagal walau tarif vendor belum ada.** Di Produksi › Laundry › Cuci gagal berbayar, bila untuk vendor dan
  proses itu belum ada tarif sama sekali, muncul pilihan "Tarif vendor belum diketahui". Petugas harus mencentangnya
  sendiri. Layar langsung menulis bahwa biayanya belum dihitung (bukan nol) dan HPP PO itu belum final.
- **Barangnya tercatat sama persis seperti biasa.** Posisi barang (tetap di vendor, atau seluruh kiriman kembali tanpa
  diproses) sama dengan cuci gagal yang tarifnya sudah ada. Yang berbeda hanya biayanya: kosong dan berstatus menunggu,
  tidak pernah diisi nol.
- **Mengisi harganya belakangan.** Di Produksi › Laundry › Harga & tagihan › Harga belum diketahui ada daftar
  "Cuci gagal berbayar dengan harga vendor belum diketahui". Owner atau admin yang berhak mengelola HPP mengisi harga per
  pcs dengan alasan. Bila vendor ternyata tidak menagih, pilih Gratis atau Tidak ditagih (nol, tetap dengan alasan).
  Harga hanya bisa diisi sekali; siapa yang mengisi, kapan dan alasannya tersimpan dan tidak bisa diubah atau dihapus.
- **Setelah harga diisi, biaya dihitung seperti biasa:** jumlah pcs × harga, lalu biaya laundry yang masih harus dibayar,
  HPP PO, dan jurnalnya diperbarui pada tanggal kejadian cuci gagal itu, sama seperti bila tarifnya sudah ada sejak awal.
- **Membatalkan cuci gagal yang harganya belum diketahui** tetap bisa dari Riwayat & koreksi, tanpa jurnal uang apa pun.

## Yang tetap tertahan sampai harganya diisi

- **Tutup buku** sampai tanggal kejadian itu (atau sesudahnya) ditolak. Layar Tutup Periode menyebut cuci gagal mana,
  kiriman dan PO-nya, jumlah pcs, tanggalnya, dan tempat mengisi harganya. Tutup buku sebelum tanggal kejadian tidak
  terganggu.
- **HPP PO itu belum final.** Barang jadi dari PO itu tampil di daftar "HPP belum final".
- **Penjualan barang dari PO itu** mengikuti pilihan Bos di LAU-DEC04, sama seperti harga laundry lain yang belum
  diketahui: bila "tolak", penjualan ditolak; bila "boleh jual, HPP menyusul", penjualan dicatat dan HPP-nya dihitung
  ulang setelah harga diisi.
- **Invoice vendor** tidak bisa menagih cuci gagal itu sampai harganya diisi.

Yang tidak berubah: bila tarif sudah ada, cuci gagal dicatat persis seperti sebelumnya. Bila tarif ada dua yang berlaku
bersamaan, tetap ditolak seperti sebelumnya. Perintah laundry lain (kirim, terima, final SKU, batal, invoice) tidak berubah.

## Yang sudah dicoba di komputer kerja

- Perubahan pada 10 fungsi database dicoba pada teks fungsi versi terakhir dari berkas rilis ditambah perubahan OW-07:
  setiap perubahan cocok tepat satu kali, hasilnya bisa dipasang di PostgreSQL percobaan, dan menolak dipasang dua kali
  atau di atas versi yang salah.
- 36 pemeriksaan kecil pada database percobaan tiruan lulus (mencatat tanpa tarif, menolak tanpa centang, menahan tutup
  buku, isi harga sekali, hanya owner/admin, gratis harus nol, riwayat harga tidak bisa diubah, pembatalan, pendeteksi
  data tidak cocok).
- Layar: 12 uji baru untuk pilihan "tarif vendor belum diketahui", riwayat, dan daftar isi harga; seluruh 1.938 uji
  aplikasi lulus; pemeriksa TypeScript lulus. Pemeriksa sumber lain hasilnya sama dengan sebelum perubahan (tiga pemeriksa
  kepemilikan backend memang sudah merah sebelumnya, dengan pesan yang sama persis).

## Yang menunggu uji CI

Uji lengkap "CP7 OW08b failed wash with unknown vendor price Native11" (11 kasus) pada salinan database yang disamakan
dengan database asli. Uji ini membandingkan setiap hasil dengan kembarannya yang tarifnya sudah diketahui, dan dengan mesin
lama pada keadaan yang sama.

Percobaan pertama (23 Okt, run 39883305777): 3 dari 11 kasus lulus, 8 belum selesai. Penyebabnya satu penjaga lama di
database: saat cuci gagal disimpan, penjaga itu mewajibkan tarif sudah terisi, jadi cuci gagal tanpa tarif selalu ditolak.
Penjaga itu sekarang ikut disesuaikan: hanya cuci gagal yang memang dicatat "tarif belum diketahui" boleh disimpan tanpa
tarif, dan harus benar-benar kosong (bukan nol). Cuci gagal lain tetap diperiksa persis seperti dulu. Satu catatan
keamanan juga dirapikan (tabel harga diberi aturan tolak-semua). Rincian: `wash-native11-cc5766e7-first-failure.json`.

Percobaan kedua (run 39884771546): 6 dari 11 kasus lulus, termasuk mencatat tanpa tarif, membatalkan, dan pemeriksa data.
Lima kasus yang mengisi harga berhenti karena catatan riwayat (log audit) memakai nama aksi yang tidak dikenal database.
Sekarang dicatat sebagai perubahan biasa dengan keterangan "isi harga cuci gagal". Uji diulang; hasilnya dicatat di sini
(rincian: `wash-native11-c6e073b5-second-failure.json`).

## Catatan teknis untuk pemeriksa

- Tahap: `scripts/cp7_laundry_unknown_wash/` di atas produk OW-07 (`cp7_hpp_close`), workflow
  `.github/workflows/cp7-ow08b-wash-native.yml`, laporan `CP7_OW08B_LAUNDRY_UNKNOWN_WASH_NATIVE11.json`.
- Isian baru `price_status:'UNKNOWN'` pada POST_FAILED_WASH; aksi baru `SET_FAILED_WASH_PRICE` pada fasad BD yang sudah ada
  (tidak ada fungsi publik baru). Kode tutup buku baru `LAUNDRY_FAILED_WASH_PRICE_UNKNOWN` (POLICY, per tanggal kejadian) dan
  pendeteksi `LAUNDRY_FAILED_WASH_PRICE_STATE_MISMATCH` (CRITICAL).
- Daftar di layar memuat paling banyak 100 baris (yang menunggu harga lebih dulu); tutup buku tetap menyebut semuanya.
- Mencopot tahap ini hanya bisa sebelum ada cuci gagal tanpa tarif; sesudahnya perlu pemulihan dari cadangan.

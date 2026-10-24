# OW11 — model teruji dan produk pembanding

24 Oktober2026. Semua kebutuhan D17-16 tetap lingkup. Dokumen ini mendahului
implementasi; OW11a/b belum selesai. Jangan mengubah47 sumber qualified,
pemasang A, generated types atau registry bersama untuk prototype.

## Temuan pada sumber yang benar-benar dibaca

- `cp7_model_native.build` dan `cp7_models.evaluate/predict` sudah membandingkan
  delapan metode dengan paired chronological validation, holdout terpisah,
  pengetahuan saat keputusan dan stok habis/censored bukan nol. Hasilnya masih
  `automatic_activation=false/apply_allowed=false`; layar hanya meninjau.
- Registry `cp7.native-model-policy.v1` menyebut dirinya usulan teknis, bukan
  persetujuan owner. Tiga fold, perbaikan MAE ketat dan penjaga bias/tail yang ada
  tidak boleh diubah menjadi kebijakan owner tanpa konfirmasi/config berversi.
- Dataset Native menggunakan waktu capture history yang sungguhan; registry
  harus sudah diketahui sebelum validation. Jangan backdate capture/registry
  atau menganggap snapshot sekarang sudah diketahui dulu demi model menang.
- Caller `cp7_baseline_native.build` dan `cp7_analysis_stage.baseline_rows`
  belum memakai forecast model dan selalu memasukkan `analog=null`.
- `cp7_demand.estimate` sudah mendukung analog dengan ukuran fisik sama,
  scale_factor/alasan/refs eksplisit dan `reviewed=true`. Manual yang dipilih
  tetap didahulukan, lalu own history cukup, lalu analog; selain itu UNKNOWN.
  Jangan mengalikan mean yang sudah dibulatkan untuk mengarang total PCS asli.

## Urutan komponen

1. Pembaca kandidat dari satu snapshot Native bounded yang lengkap untuk SQL.
   Gunakan identitas root+size, model/merek yang benar-benar terekam dan jumlah
   hari tersedia/mean Native. Jangan menyimpulkan kesamaan kain/pola dari nama.
   Alasan atribut ditampilkan, bukan skor bisnis berbobot buatan. Ukuran fisik
   harus sama. Kandidat bukan pilihan atau konfirmasi pengguna.
2. Konfirmasi analog dan kebijakan pemilihan model sebagai konfigurasi privat
   berversi/immutable, hak owner yang tepat, CAS/UUID/global lock dan current
   access sesudah tunggu. User memilih skala dan alasan; tidak ada skala default
   yang dianggap keputusan owner. Tanpa pembanding layak tetap data belum cukup.
3. Sambungkan pilihan yang sah ke satu mesin target yang juga dipakai reorder,
   perencanaan dan saran potong. Pertahankan stok/WIP/order/cadangan tunggal,
   kedua clock, source/producer hashes dan semua pembaca. Label analog/assumption,
   metode, waktu bukti dan alasan fallback harus berasal dari server.
4. Model kompleks baru dipakai bila bukti memenuhi kebijakan berversi dan masih
   berlaku. Data pendek/unknown atau bukti tidak layak memakai baseline dengan
   alasan. Jangan sekadar mengganti angka mean di UI, membuang unsur forecast
   horizon atau menambah safety stock kedua. Horizon/kecukupan tetap dibatasi.

Tahap baru harus opt-in/countable dengan predecessor/owner/ACL/catalog delta
dan invers22 tepat. A mengomposisikan default/fullchain/after-use. Pemakaian
modul keuangan A dan source method lama tidak diambil sepihak.

## Kriteria pembaca kandidat pertama

`cp7_product_analog_stage` dimulai sebagai private pure consumer prototype:
satu fungsi, nol facade/tabel/penggantian Native, belum dipasang atau dipakai UI.
Input hanya reference bounded yang lolos `require_inputs`, q/clock/hash tetap.
Ambang hari berasal dari profil target yang sudah dipilih; tanpa profil tidak
membuat angka sendiri. Kandidat dibaca dari seluruh target sebelum pagination;
hari UNKNOWN/STOCKOUT tidak dianggap tersedia, nol penjualan yang benar sah.
Mean ditampilkan dari histori Native, belum merupakan forecast yang dipilih.
Kesamaan model/merek adalah alasan yang dapat diperiksa; opsi tanpa alasan
atribut yang tercatat memerlukan tinjauan/pilihan manual.

Selanjutnya wajib Native/source-binding/UNKNOWN/ukuran/identitas/duplikat/
pagination, Auth/current-token, konfirmasi/CAS/replay/race, pemakaian satu mesin,
browser desktop/HP serta install/restore. Prototype, kernel abstrak dan fallback
tidak menjadi penerimaan penuh OW11. Induk tetap5/16.

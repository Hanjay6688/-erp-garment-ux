# Retur transaksi lunas — daftar penutupan OW-04

Retur belum dinyatakan selesai. Batas pekerjaan mengikuti tujuh syarat
[arahan owner22 Oktober](../../handoff/ARAHAN_ASTRA_20261022.md), bukan jumlah commit atau uji.
Writer hanya bekerja di `astra/d17-14-integrasi`; cabang lama dipertahankan.

| Syarat owner | Bukti yang sudah ada | Yang masih perlu ditutup |
|---|---|---|
|1. Invoice lunas; pilih uang kembali atau kredit di layar |Alur Native dan layar pada kandidat91f71ce7/da6a5454 serta browser9 pada642d7a00 |18HTTP dan9browser kini lulus pada36a6b880 dengan sumber keuangan8c yang sama; lihat kuitansi gabungan INCOMPLETE di bawah |
|2. Uang keluar sekali; kas per tanggal tetap dijaga |Native32 pada8c437dbe lulus; literal uang, replay, penolakan UUID berubah dan penjaga tanggal tetap |Bukti transport terakhir pada sumber yang sama |
|3. Kredit ke invoice berikutnya dan pembatalan tanpa saldo ganda |Native32 lulus APPLY/REFUND/UNDO bernama; HTTP18 dan browser9 pada sumber527 sudah lulus |18HTTP dan9browser sudah lulus pada36a6b880; dua uji pengguna berbeda masih dibenahi |
|4. Stok/HPP retur termasuk saldo awal; jurnal seimbang |Native63/87/90 mencakup fondasi retur/HPP; Native32 terkini membuktikan koreksi pembayaran tidak mengubah stok/HPP |14 vektor langsung Native serta14 vektor uang/kredit/HPP asli kini lulus pada36a6b880; bukan klaim mengulang90 |
|5. Koreksi dua arah, beberapa angkatan, histori dan petunjuk pembalikan |Native32 lulus1000→900→1000 dan inverses; petunjuk di browser pernah diuji |Dua perjalanan tambahan membuktikan empat generasi1000→900→1000→950→1000. Itu satu kelompok retur; beberapa kelompok retur berbeda pada invoice yang sama belum diklaim |
|6. Native, dua penulis, HTTP Auth, desktop/HP, P21 di salinan |Native32 terkini lulus; bukti18HTTP/8balapan SQL/9browser sumber527; full restore6/6 langkah pada1e8e1b0d |P21 bawaan baru dialihkan ke pemasang terkini; pasang/copot sebelum pakai/pasang ulang/pakai/pulihkan harus lulus, serta transport sumber8c perlu diuji |
|7. Temuan di luar daftar menjadi batas tersisa |Batas tercatat di bawah |Tidak memperpanjang OW-04 dengan penyelidikan lain |

## Bukti baru dan cara menguji

- Native32: [kuitansi ringkas](consumer-closure-8c437dbe-pass.json),
  [run39734958661/job119678374447](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39734958661/job/119678374447).
  Semua26 kasus lama benar-benar diulang, ditambah6 pengaman penjadwalan pemeriksaan.
- Pemulihan sumber527:
  [kuitansi enam langkah](payment-used-restore-1e8e1b0d-pass.json),
  [run39730341474/job119663686362](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39730341474/job/119663686362).
  Dua rantai sudah tersimpan;649 tabel cocok;8 replay tidak mengubah data;
  UNDO dan pembalikan retur lulus. Ini belum bukti P21 baru atau sumber8c.
- Empat generasi koreksi: [kuitansi2/2 lulus](four-generations-6e843f9b-pass.json),
  [run39741995021/job119701210253](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39741995021/job/119701210253).
  APPLY dan REFUND lulus1000→900→1000→950→1000; histori, replay, stok/HPP, pembalikan dan pemulihan CP6 lulus.
  Setiap perjalanan tetap satu kelompok retur; beberapa kelompok berbeda belum dibuktikan.
- P21 pertama: [kegagalan yang dipertahankan](p21-6e843f9b-first-failure.json),
  [run39741995021/job119701209927](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/39741995021/job/119701209927).
  Pemasangan lulus, lalu kesamaan katalog setelah pencopotan gagal. P21 belum lulus.
  [Pemeriksaan rinci](p21-48584c1a-diagnostic-failure.json) menemukan dua representasi katalog dari satu tampilan piutang yang berubah saat SQL dibaca lalu ditulis ulang.
  Data, urutan nomor, hak akses dan CP6 sama. Adapter memulihkan definisi asli; kesamaan penuh22 kelompok tetap diwajibkan.
  Reproduksi/perbaikan lokal lulus; uji P21 lengkap berikutnya belum diklaim lulus.
  `.github/workflows/cp7-ow04-final-p21.yml` mengulang P21 saja.
  P21 mempertahankan pemakaian pembayaran supplier dan analisis bertahap dari
  rehearsal lama, ditambah dua rantai kredit/refund dan pemeriksaan penuh sesudah restore.
- Kandidat transport terkini menyiapkan18 kasus HTTP lama ditambah2 balapan dua pengguna Auth berbeda,9 browser desktop/HP,8 balapan SQL,
  serta14 vektor saldo awal/HPP yang tetap beku. Belum dinyatakan lulus sebelum hasil run tersedia.
- Log lengkap baru berada di artifact Actions dan arsip privat owner.
  Repo hanya memuat kuitansi ringkas dan potongan kegagalan pertama.
  Semua data uji berasal dari stack lokal sekali pakai; tidak ada data produksi.
- Untuk menjalankan kandidat: sediakan JSON asli Native32 dari artifact12407224140
  atau arsip privat owner sebagai `OW04_NATIVE32_ORIGINAL_REPORT`; byte/hash
  diperiksa sebelum database digunakan. Native tambahan:
  `python scripts/ow04-final-qualification/native_generations_probe.py`;
  P21 bawaan: `python scripts/cp7_p21_full_rehearsal_probe.py`.

- Kode36a6b880: [14 vektor stok/HPP lulus](opening-hpp14-36a6b880-pass.json) dan [8 balapan SQL lulus](sql8-36a6b880-pass.json).
  Keduanya membersihkan salinan dan memulihkan CP6/advisor. Uji HPP ini langsung Native dengan nilai uang retur nol;14 vektor asli dengan kredit bernilai berjalan terpisah.
- [P21 berikutnya](p21-36a6b880-readiness-boundary.json) lulus pasang, copot dengan seluruh katalog/data sama, dan pasang ulang;
  pembuat contoh E01 mengasumsikan laporan global READY setelah kredit OW04 telah dibuat. Pemeriksa laporan lama belum mengurangi/menambah kredit.
  Batas ini masuk [OW-08](../ow08/README.md), sesuai syarat7 owner. Pembuat contoh E01 tetap diuji READY sebelum kredit;
  tanda laporan sesudah kredit tetap dicatat dan wajib sama setelah restore. Belum ada klaim P21 lengkap lulus.

- [18HTTP dan9browser pada sumber terkini lulus](auth18-browser9-36a6b880-subsets-and-first-failures.json).
  Run gabungan tetap INCOMPLETE karena dua uji tambahan150; kegagalan dan gold aslinya dipertahankan.
  Pengamatan antrean diperbarui, dan dua contoh80 yang tetap cukup saldonya menguji tepat penjaga ulasan berubah.
  Dua contoh baru ini memakai ID/gold tersendiri; belum dinyatakan lulus.
- [14 vektor retur dengan kredit bernilai dan HPP saldo awal/PO lulus](monetary-hpp14-793bb51f-pass.json),
  run39748075152/job119721445604, produk beku36a6b880; seluruh CP6/advisor/pembersihan lulus.

## Batas tersisa

Kecepatan simpan belum mencapai2detik. Observasi terisolasi sumber8c adalah
koreksi12,00detik dan pemakaian kredit9,09detik; satu pemeriksaan lengkap
terjadwal menggantikan10 pemanggilan berulang, sementara pemeriksaan lengkap
lain tetap ada. Batas aplikasi8detik/8MB tetap. Pengukuran ini bukan uji
kecepatan browser atau penerimaan skala pabrik OW-12.

Pemeriksa kesiapan laporan lama masih menandai piutang yang sah sesudah kredit: perhitungannya memakai pembayaran P tanpa penyesuaian U-I.
Akibatnya tanda kesiapan laporan tetap BLOCKED; perbaikan pembaca pemeriksa ini belum dikerjakan dan masuk OW-08 yang sudah terbuka.
Uang/AR literal pada kasus Native tetap diperiksa terpisah; tidak ada klaim seluruh laporan READY.

Adapter pembayaran masih dibatasi pada sumber/kelompok retur yang telah
didukung: pemetaan kelompok baru, riwayat kredit masuk yang lebih luas,
perubahan pasangan tanggal asli dan kelompok HPP tambahan tidak diklaim
berhasil. Bila suatu batas termasuk syarat5, butir5 tetap terbuka; tidak
dipindahkan ke batas tersisa untuk membuat status selesai.

OW-05,06,07/08 dikerjakan sesudah OW-04 sesuai urutan owner. Tidak ada
pemasangan Enteng/produksi, WA nyata, perubahan kandidat audit55c885d1,
atau CP7C formal dari pekerjaan ini.

# Retur transaksi lunas — penutupan OW-04

**Selesai pada cakupan tujuh syarat owner22 Oktober; siap diuji ulang secara terpisah.**
Dasar: [arahan owner](../../handoff/ARAHAN_ASTRA_20261022.md). Semua hasil di bawah
berasal dari salinan uji; ini bukan audit independen atau izin pemasangan produksi.
Writer bekerja di `astra/d17-14-integrasi`; cabang lama tetap disimpan.

## Tujuh syarat dan bukti

| Syarat owner | Hasil yang terbukti | Kuitansi |
|---|---|---|
|1. Retur invoice lunas; pilih uang kembali atau kredit di layar |Kedua pilihan tercatat lewat Native, HTTP Auth dan browser komputer/HP |[18HTTP/9browser](auth18-browser9-36a6b880-subsets-and-first-failures.json) |
|2. Kas/bank keluar sekali dan penjaga tanggal tetap berlaku |REFUND, replay dan pembatalan bernama mempertahankan uang literal; UUID berubah ditolak |[Native32](consumer-closure-8c437dbe-pass.json), [Auth2](auth2-e2aeef46-pass.json) |
|3. Kredit ke invoice berikutnya; pemakaian dibatalkan tanpa saldo ganda |APPLY/REFUND/UNDO bernama, replay tanpa efek ulang dan dua penulis bersamaan lulus |[Native32](consumer-closure-8c437dbe-pass.json), [8race SQL](sql8-36a6b880-pass.json), [Auth2 nyata](auth2-e2aeef46-pass.json) |
|4. Stok/HPP termasuk saldo awal; jurnal seimbang |14 vektor langsung Native dan14 vektor asli dengan kredit bernilai mencakup saldo awal/PO/non-PO serta penolakan yang diwajibkan |[Native14](opening-hpp14-36a6b880-pass.json), [uang/HPP14](monetary-hpp14-793bb51f-pass.json) |
|5. Koreksi positif/negatif beberapa angkatan; histori dan petunjuk pembalikan |APPLY dan REFUND masing-masing melewati1000→900→1000→950→1000, empat generasi; fakta/jurnal lama, stok/HPP dan replay tetap; UNDO lalu pembalikan retur lulus. Petunjuk di layar diuji browser |[empat generasi2/2](four-generations-6e843f9b-pass.json), [Native32](consumer-closure-8c437dbe-pass.json), [browser9](auth18-browser9-36a6b880-subsets-and-first-failures.json) |
|6. Native, race, HTTP Auth, desktop/HP dan P21 di salinan |Semua cakupan tersebut mempunyai hasil lulus pada sumber keuangan yang sama; P21 bawaan lulus pasang/copot/pasang ulang dan enam langkah pemulihan |[Auth2](auth2-e2aeef46-pass.json), [P21](p21-bb752227-pass.json), kuitansi lain di atas |
|7. Temuan lain dicatat sebagai batas tersisa |Kesiapan laporan tetap BLOCKED dan masuk OW-08; kecepatan masuk OW-12; batas tambahan tertulis di bawah |[OW-08](../ow08/README.md), bagian batas tersisa |

"Beberapa angkatan" pada syarat5 dibuktikan dengan empat generasi koreksi
pembayaran pada satu kelompok retur per perjalanan. Ini tidak mengklaim
beberapa kelompok retur berbeda pada invoice yang sama sudah diuji.

## Versi dan hasil aktual

Produk beku `36a6b880d789452dbe4096fd4c401430bba1a5cb` memakai sumber keuangan
yang sama dengan Native32 `8c437dbe0d6e62e246b2cf0cda75fb6c19330357`.
Perubahan sesudahnya untuk P21 dan Auth2 adalah alat uji/adapter dan catatan;
sumber keuangan produk tidak diubah. Setiap kuitansi menyatakan versi produk
serta versi alatnya; hasil beberapa run tidak disebut satu suite gabungan baru.

| Cakupan aktual | Commit alat/kandidat | Run/job | Hasil |
|---|---|---|---|
|Native32:26 kasus lama benar-benar diulang +6 pengaman antrean |8c437dbe |39734958661/119678374447 |32PASS |
|Empat generasi koreksi APPLY dan REFUND |6e843f9b |39741995021/119701210253 |2PASS |
|Stok/HPP langsung Native |36a6b880 |39746622801/119716563875 |14PASS |
|Balapan dua sesi SQL; bukan dua login Auth |36a6b880 |39746622801/119716563804 |8PASS |
|HTTP Auth dan browser desktop/HP |36a6b880 |39746622801/119716563410 |18HTTP +9browser PASS; job gabungan tetap INCOMPLETE karena2 kasus150 |
|Vektor asli kredit bernilai + saldo awal/HPP |793bb51f |39748075152/119721445604 |14PASS |
|P21 bawaan lengkap |bb752227 |39749850579/119727373442 |4 langkah adapter +6 langkah restore PASS |
|Dua login Auth berbeda, APPLY80 dan REFUND80 |e2aeef46 |39761252503/119765697767 |2PASS |

Pada Auth2, dua penulis nyata sama-sama terlihat menunggu kunci. Sesudah
kunci dilepas, tepat satu berhasil dan satu ditolak `CP7_CREDIT_CONSUMER_REVIEW_CHANGED`;
saldo sisa120 masih cukup untuk permintaan80 kedua. Uang, piutang, stok/HPP,
satu jurnal, replay dan pembersihan diperiksa; batas waktu produk tidak dinaikkan.

P21 memulihkan650 tabel dengan seluruh hash data, katalog dan urutan nomor
cocok; delapan tanda terima lama/terkini diputar ulang tanpa efek ulang.
UNDO dan pembalikan retur sesudah restore juga lulus. Pemakaian pembayaran
supplier serta analisis bertahap tetap diuji; CP6 dan advisor kembali sama.

## Kegagalan pertama tetap dipertahankan

- [P21 awal](p21-6e843f9b-first-failure.json) dan
  [diagnosis katalog](p21-48584c1a-diagnostic-failure.json): PostgreSQL menulis
  ulang cast pada satu tampilan dan aturan SELECT-nya. Adapter memulihkan
  definisi asli; kesamaan penuh22 kelompok katalog tetap diwajibkan.
- [P21 berikutnya](p21-36a6b880-readiness-boundary.json): pembuat contoh E01
  mengharapkan READY sesudah kredit. E01 beserta pemeriksaan READY aslinya
  kini dijalankan sebelum kredit; tanda BLOCKED sesudah kredit dipertahankan
  dan wajib sama setelah restore. Pemeriksa produk belum diperbaiki.
- [Run Auth/browser awal](auth18-browser9-36a6b880-subsets-and-first-failures.json)
  tetap INCOMPLETE. Kasus150 dan gold aslinya tidak diubah menjadi lulus;
  dua kasus80 baru mempunyai ID/gold tersendiri dan menguji saldo yang masih
  cukup setelah penulis pertama. Pengamatan antrean menyegarkan snapshot statistik.
- [Auth2 pertama](auth2-51a416fe-first-failure.json): alat salah membandingkan
  status20 dengan200. Perbaikan hanya pembanding respons; nilai uang, pesan
  penolakan, pemeriksaan efek dan gold tetap. Dua kasus yang sama kemudian lulus.

Log asli baru berada di artifact Actions dan arsip privat owner. Repo hanya
memuat kuitansi ringkas dan potongan kegagalan pertama; data uji bukan produksi.
Bukti lama tidak dihapus atau ditulis ulang menjadi hasil baru.

## Cara menguji ulang

Gunakan versi dan run pada tabel, bukan menghitung kuitansi sebagai eksekusi baru.
Alat memeriksa byte/hash laporan asli sebelum database digunakan:

- Native empat generasi: `scripts/ow04-final-qualification/native_generations_probe.py`.
- P21 bawaan: `scripts/cp7_p21_full_rehearsal_probe.py`;
  workflow `cp7-ow04-final-p21.yml`.
- Auth2: `scripts/ow04-real-auth-two-user-qualification/probe.py`;
  workflow `cp7-ow04-real-auth-two-user.yml`.
- Vektor kredit/HPP asli: `scripts/ow04-opening-credit-hpp-qualification/`.

Laporan asli Native32 pada artifact12407224140 diikat sebagai
`OW04_NATIVE32_ORIGINAL_REPORT`. Auth2 juga memeriksa laporan asli
Auth18/browser9 dan mempertahankan status INCOMPLETE gabungannya.
Semua stack dan akun uji lokal sekali pakai dipulihkan/dibersihkan.

## Batas tersisa dan alasannya

1. **Kesiapan laporan keuangan masih BLOCKED, ditangani OW-08 yang sudah ada.**
   Pemeriksa lama memakai pembayaran P tanpa penyesuaian kredit U-I yang
   tervalidasi, sehingga kredit sah ditandai selisih. Uang/AR literal diuji
   terpisah; OW-04 selesai tidak berarti seluruh laporan READY. Dasar pemisahan
   adalah syarat7 owner, bukan menghapus kegagalan atau melonggarkan penjaga.
2. **Kecepatan dan skala tetap OW-12.** Observasi terisolasi sumber8c:
   koreksi12,00detik, pemakaian kredit9,09detik; ini bukan penerimaan kecepatan
   browser. Batas aplikasi8detik/8MB tetap. Tidak ada klaim2detik atau3.600SKU.
3. **Cakupan koreksi dibatasi yang dibuktikan.** Empat generasi pada satu
   kelompok retur per perjalanan memenuhi koreksi positif/negatif berangkatan;
   pemetaan beberapa kelompok retur berbeda, riwayat kredit masuk yang lebih
   luas, perubahan pasangan tanggal asli dan kelompok HPP tambahan tidak
   diklaim lulus. Penolakan yang ada tetap berlaku, bukan diubah menjadi sukses.

OW-05 koreksi mandor dilanjutkan sesudah penutupan ini, lalu OW-06 dan OW-07/08.
Tidak ada pemasangan Enteng/produksi, WA nyata, perubahan kandidat audit55c885d1,
atau CP7C formal. Pemeriksaan ulang Claude dan audit Fable/Sol tetap terpisah.

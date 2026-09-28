# CP6 — kelanjutan alur gabungan dan paket BF, 28 September 2026

Status: **cakupan kelanjutan writer dan paket BF lulus** pada `add1704a21e953757a26c4f2a13dc603fed61470`.
CP6 tetap HOLD; `audit_complete=false`, `production_go=false`; CP7 belum diizinkan.
Hasil ini merupakan eksekusi writer pada database PostgreSQL disposable. Tidak ada
penulisan ke production, UAT, atau legacy, serta tidak ada merge/deployment.

**Keuangan (termasuk laporan), stok dan HPP adalah raja. Reliable data adalah dewa.**

## Apa yang dilanjutkan

Checkpoint 133 PASS pada produk `86f057c` menutup cakupan sumber tarif vendor,
biaya menyusul, kredit supplier dan PR30 saat itu. Checkpoint tersebut belum
mencakup seluruh rangkaian range/rework baru atau satu paket rilis sampai BF.
Kelanjutan ini mengerjakan dua bagian tersebut. Angka lama tetap disimpan sebagai
bukti historis; angka itu tidak dipindahkan ke kandidat baru.

Perubahan produk terakhir ada pada `790d0ffc1bd2f33945221c4b873a99bf734cce3b`:
pencarian konversi dan resolver impor menerima kode SKU komersial sesuai tanggal,
dengan tetap memilih identitas fisik/ukuran yang tepat. Label dokumen konversi
menggunakan keanggotaan pada waktu dokumen. Kode fisik dan lot lama tidak ditulis
ulang. Dua fungsi BD yang tubuhnya tidak berubah dikeluarkan dari daftar fungsi
pengganti BF agar pemeriksaan kapsul rollback tetap akurat.

Komit sesudahnya menambah fixture/bukti gabungan, paket/manifest, dan memperbaiki
pemulihan constraint. Tidak ada sumber tarif laundry baru dari master SKU.

## Keputusan bisnis yang dipertahankan

- Tarif laundry berasal dari vendor: proses panjang/paket atau komponen terpilih
  seperti Garment, Spray, Whisker. Riwayat SKU membantu memilih dan membandingkan.
- Rincian saat kirim boleh kosong; biaya tetap UNKNOWN, tidak dibuat Rp0/FREE.
  Kontra bon mengisi biaya aktual sesuai penerima jasa fisik; pembatalannya
  membuka kembali bagian biaya yang belum diketahui.
- Kredit klaim laundry dapat dipakai pada kontra bon lain dari vendor yang sama.
  Kredit retur kain/aksesori dapat tetap di pembelian asal, dibagi atau dipindah
  ke pembelian lain dari supplier yang sama, sesuai saldo dan riwayat kas.
  Pemakaian kredit tidak mengurangi total utang kedua kali.
- Perubahan range tidak mengubah stok/biaya historis. Koreksi tercatat melalui
  tindakan baru dan pembalikan, bukan mengedit transaksi yang telah diposting.

## Cakupan gabungan

| Kasus | Bukti dan batas |
|---|---|
| R03 — ukuran sama pada dua SKU | Satu wave menolak dua referensi pekerjaan untuk ukuran yang sama secara atomik. Dua wave fisik terpisah mendukung referensinya masing-masing. |
| R06 — tambah 34 pada PO berjalan | Resep identik melanjutkan sampai QC/HPP; resep berbeda ditolak tanpa mengubah lot 31–33 atau pin resep PO. |
| R07 — pindah range ketika BS lalu rework | Empat kombinasi komitmen resep fisik sudah/belum ada × mandor sama/berbeda. Snapshot sah, sumber tarif/resep, pemulihan stok, HPP positif, pemeriksaan keuangan dan pembalikan diuji. |
| R08 — BS belum teridentifikasi | Receipt Laundry BS ditolak sebelum pencatatan parsial bila produk fisik BS belum jelas. Setelah ukuran 32 diidentifikasi, entitlement memakai snapshot A yang tepat. Ini tidak mewajibkan SKU final pada kiriman laundry biasa. |
| R09 — kode SKU komersial | Pencarian source/target konversi menerima kode komersial dan kode fisik lama. Konversi satu PCS ukuran 32 dan inverse memengaruhi lot yang tepat; label dokumen bertanggal. |
| R11 — jual, pindah range, invoice terlambat, retur | Dua kasus harga awal dikenal/UNKNOWN: jual seluruh 4 PCS ukuran 34, pindah ke A, biaya susulan +160 hanya ke sumber 34, retur 1 PCS lot asal. Invoice mula-mula menambah COGS 160; retur membawa biaya aktual satu PCS. Pembalikan invoice kemudian mengurangi FG tepat 40 dan COGS 120; alokasi penjualan lama tetap. |
| R12 — impor historis dan versi fisik | Alias komersial mengikuti waktu cutover, menolak keanggotaan masa depan. Dua identitas fisik dengan konstruksi/root/ukuran sama memerlukan `product_id` eksplisit bila alias+ukuran ambigu. Edit nama saja tidak dihitung sebagai versi fisik baru. |
| R13 — paket, extra sebagian, wash berulang, BS, klaim | Paket 20×6,17=123,40 dan extra hanya 2 PCS ukuran 32×0,19=0,38. Dua attempt berbayar, receipt 18 GOOD/1 BS/1 hilang, invoice/variance/koreksi/inverse, klaim 10 dan pemakaiannya diuji. Dua rewash garansi hanya memulihkan satu barang fisik dan tidak menjadi tagihan redye baru. |
| R14 — HPP lokasi, stok nol, biaya menyusul | Stok FG 16 PCS tersebar 2 dan 14 PCS pada dua lokasi; anggota 34 belum punya stok FG. Biaya UNKNOWN tetap terlihat; invoice 123,20 menambah bagian FG tepat 98,56 (16/20); inverse mengembalikan nilai dan status pending. |

R10 tetap batas terpisah: `SalesPages.tsx` adalah simulasi existing. Bukti engine
jual/retur native tidak dinyatakan sebagai bukti posting penjualan dari browser.
R14 menguji filter Grade B yang kosong; tidak ada klaim stok Grade B berisi dan
multi-grade telah diuji. Matriks di atas adalah kasus konkret, bukan klaim setiap
variasi bisnis yang mungkin.

## Paket dan bukti eksekusi

Paket terpasang berisi **30 berkas AC sampai BF**, dibangun dari baseline hosted
yang diselaraskan sampai AB. Ini bukti pemasangan/upgrade pada baseline tersebut,
bukan izin pemasangan ke production. SHA-256:

| Artefak | SHA-256 |
|---|---|
| BF development | `58b97662a093147f3e594987bcc662e0f7cf376aaaf7664364739508ab1fafbd` |
| BF release | `fa4dadf5cbab6ac34de94c72c4d67459a2cd1ba28eee33efee965fedc1de8caf` |
| BE tetap | `695475db3719617bd2c10d82c4dee2eaa567f4c10f322697a1714b17b60d29f6` |
| Release pins | `3e9dc0047f0f62b575d2c4d2df817667080e3729cb6e3f296624ef73d753db2a` |
| Rollback capture | `b0d0157528c5cf89c6290974acd3a963d784f5c938736e299e2d27f461bfe655` |
| BF packaged rollback | `30723c59726a47ccfeb27b7b97405b295c85d7665b60dc176fddc6f85ff82716` |

- [Paket/runtime akhir 36452814728](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36452814728): **90 native + 22 contention + 8 Auth/HTTP + 27 browser BF PASS**, 0 FAIL/INCOMPLETE, ditambah 10 browser AU PASS. Ketiga job (capture/install/browser) sukses. Seluruh gate true: 30 berkas terpasang, pins deterministik, backup/restore `RESTORED_SAME_MEANING`, advisor sesuai gate, primary tetap, runtime lulus. ACL hosted tetap dan tidak ada console error.
- [Checkpoint paket 36451999967](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36451999967): 27 browser BF dan 10 browser AU PASS, console error 0, pins terulang identik, backup/restore `RESTORED_SAME_MEANING`; primary dan ACL tidak berubah.
- Runtime pada checkpoint yang sama: **90 native + 22 contention + 8 Auth/HTTP + 27 browser BF PASS**, 0 FAIL/INCOMPLETE. Semua 14 kasus gabungan baru lulus pada paket terpasang. 10 browser AU adalah bukti tambahan, tidak dihitung dua kali di angka 147 tersebut.
- [Baseline development 36452000113](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36452000113) pada `a97962f` juga lulus 90/22/8/27, primary tidak berubah, clone tersisa 0. Dengan demikian helper fixture diuji pada baseline development dan hosted; ini tetap skenario writer walaupun nama workflow memuat Auditor.
- [Regresi BC 36452814699](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36452814699), commit `add1704a21e953757a26c4f2a13dc603fed61470`: **45 native PASS**, termasuk SQLSTATE penolakan akses langsung dan ACL tetap; primary tidak berubah, clone tersisa 0.
- [Regresi keluarga BD 36452814750](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36452814750) pada commit yang sama: **41 native PASS**, tanpa mismatch oracle; primary tidak berubah, clone tersisa 0. Angka ini adalah suite keluarga BD, bukan penamaan ulang suite auditor BD140 terdahulu.
- [Build UX 36452814726](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36452814726) dan [CodeQL 36452814716](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36452814716): PASS pada commit `add1704a`.
- [Rollback 36450928491](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/36450928491), commit `91445b4e1cd6a6c5363b70b92fdc7d71020a21cc`: **147/147 PASS**. Dua siklus pemasangan/pencabutan 30 berkas mengembalikan predecessor dan akhirnya AB; reinstall mempunyai arti yang sama; setiap rollback menolak keadaan sesudah pemakaian. Primary tidak berubah.
- [Bukti per kasus dan riwayat kegagalan](cp6-combined-release-writer-proof-20260928.json).

Rollback hanya untuk keadaan belum dipakai dan akses penulisan ditutup/drained.
Penolakan sesudah pemakaian merupakan hasil yang diharapkan; bukan izin menghapus
transaksi bisnis untuk memaksa rollback. Backup/restore diuji terpisah oleh paket.

Advisor keamanan menghasilkan 143 INFO tambahan, seluruhnya kelas
`rls_enabled_no_policy` pada schema `erp` untuk tabel yang diakses melalui RPC
security-definer. Ini kelas yang telah diterima gate B2 CP6-11; tidak ada kelas
tambahan lain yang diloloskan. Hasil advisor bukan pernyataan "nol temuan".

## Kegagalan yang diperbaiki selama kualifikasi

Riwayat run merah tetap ada. Fixture awal memakai reimbursement nol sehingga QC
menolak dengan benar; observasi private schema sempat memakai peran aplikasi;
R08 sempat mencari penolakan terlalu terlambat dan memakai parser kode untuk
pesan tanpa kode; R12 sempat mengubah konstruksi lalu hanya nama sehingga tidak
membuat successor yang dimaksud. Fixture kini membangun prasyarat yang sesuai
tanpa melemahkan guard produk.

Baseline hosted G-01 memang memiliki schema USAGE. Helper HTTP/browser yang
mengasumsikan baseline AN tanpa USAGE diperbaiki dengan profil eksplisit yang
mempertahankan ACL lengkap. Helper internal supplier kini hanya mencabut grant
yang dibuatnya sendiri. BF menggunakan salinan paket sebelum fixture master AU
berjalan. Izin produk tidak diubah untuk membuat tes hijau.

Tes akses BC lama mengharapkan penolakan pada schema, padahal setelah helper
mempertahankan grant semula, tabel tetap menolak dengan SQLSTATE `42501`.
Oracle sekarang memeriksa batas penolakan sesuai ACL asli, SQLSTATE, dan bahwa
ACL lengkap tidak berubah; penolakan akses langsung tetap wajib.

Rollback BF pertama gagal kesamaan katalog karena bentuk parse constraint
`varchar` berubah ketika definisi PostgreSQL dicetak dan dibaca kembali. Builder
memulihkan ekspresi `IN` asli melalui helper G-01 yang sudah ada; perbandingan
katalog tetap ketat. Dua siklus dan penolakan sesudah pemakaian kemudian lulus.

## Batas penutupan

Pengujian writer akhir tercatat dengan SHA dan log yang sama. Retest/putusan
independen CP6 tetap terpisah; nama workflow yang memuat kata Auditor tidak
menjadikan fixture writer sebagai audit independen. Owner tidak perlu mengulang
keputusan tarif atau fleksibilitas kredit untuk melanjutkan pekerjaan ini.

Pemantau per jam sudah dinonaktifkan sesuai permintaan owner. Setiap push writer
dalam kelanjutan ini memeriksa ref branch lebih dahulu dan tidak memakai force.
Kemampuan itu hanya melihat push GitHub, bukan menghentikan chat lain atau
mengamati tulisan yang belum dipush.

# Uji ulang penulis A atas butir yang dinyatakan selesai (bukan audit)

Uji ulang terpisah oleh Claude sesuai `PEMBAGIAN_DUA_PENULIS_20261022.md` (butir A1). Audit tetap oleh Fable/Sol.

## OW-05 koreksi mandor sesudah dijahit (23 Okt 2026, kepala `2d625616`)

Hasil singkat: bukti CI cocok dan kode yang diuji sama dengan kepala cabang; uang dan riwayat tidak ditemukan cacat.
Ada empat catatan tampilan; tiga di antaranya menyentuh syarat owner "langkah membalik dokumen terkait ditampilkan
jelas", jadi OW-05 dibuka lagi untuk bagian itu.

| Yang diuji | Hasil |
|---|---|
| Run CI yang dirujuk | Native28 39786776421/119851971167 (`56830738`), Auth4 39792851198/119872918589 (`347a1baf`), layar 39797404450/119888156171 dan laundry/FG 39797404458/119888156506 (`5e4b4c1c`), P21 39789070200/119859922468 (`9dde276f`): semua `success`, SHA sesuai klaim, hash laporan asli di log sama dengan `ow05/completion.json` |
| Kode yang diuji vs kepala cabang | Semua commit klaim adalah leluhur kepala; `contractor.sql`, `composition.py`, `native_probe.py` tidak berubah sejak `e3a37d73`; 45 pin sumber cocok |
| Typecheck | `tsc -p tsconfig.app.json` dan `-p tsconfig.contracts.json` lulus |
| Uji klien vitest | 2.022 lulus, 50 gagal (33 berkas) sama persis dengan pembanding `1e8e1b0d`; semua kegagalan butuh PostgreSQL asli (F04), tidak ada kegagalan baru |
| Upah, nota, payroll, HPP | Ditangani dengan penolakan selama dokumen terkait masih aktif (`blockers_v1`, `contractor.sql:95-169`) dan pemeriksaan bahwa koreksi tidak mengubah uang/stok/HPP (`:173-196`, `:325-330`) |
| Riwayat | Pickup lama dibalik (REVERSED), pengganti diposting; tabel riwayat koreksi tidak bisa diubah/dihapus |

Catatan yang harus dibetulkan (OW-05 terbuka kembali untuk tampilan):

1. Nama layar di petunjuk tidak sama dengan menu: "layar Nota/Gaji" (menu: Payroll & Kasbon), "layar WIP & Jahit"
   (menu: WIP & Sewing), "layar PO" (buka-ulang PO ada di HPP & Rekalkulasi), "layar Bahan Mandor" (tidak ada).
2. Petunjuk sesudah koreksi hanya menyebut catat ulang jahit dan buat ulang nota; dokumen lain yang dibalik
   (pool HPP/kantong, laundry, QC/barang jadi, nota aksesori) tidak disebut.
3. Riwayat koreksi (mandor lama, mandor baru, alasan, oleh siapa) tersimpan tetapi tidak bisa dilihat di aplikasi.
4. Penghalang tampil sebagai teks tanpa tautan ke dokumennya (kecil).

Batas yang sudah diungkap penulis tetap berlaku: uji layar tidak menjalankan nota/payroll lewat layar (nota diuji
lewat API pada Auth4); data master uji dibuat dengan SQL.

## OW-04 retur transaksi lunas (23 Okt 2026, kepala `2d625616`; berkas kredit sama dengan produk `36a6b880`)

Hasil singkat: retur pertama atas invoice lunas berjalan benar (uang kembali atau saldo kredit, pakai dan batal pakai,
stok/HPP, jurnal seimbang, koreksi pembayaran). Tetapi beberapa keadaan yang wajar di pabrik ditolak sistem, jadi OW-04
belum memenuhi kebutuhan owner sepenuhnya. Run CI sudah dicek 22 Okt (`ARAHAN_ASTRA_20261022.md` bagian 2).

| Syarat (ARAHAN bagian 3) | Hasil |
|---|---|
| 1. Pilih uang kembali / saldo kredit di layar | Ada, label jelas (`src/SalesReturnSettlementSection.tsx:212-221,243`). **Batas:** ditolak (`CP7_CREDIT_INITIAL_SOURCE_FAMILY_UNSUPPORTED`, `02_initial_projection.sql:314-318`) bila invoice sudah punya retur bersaldo kredit sebelumnya, sudah "Benerin nota", punya koreksi retur, atau pernah menerima pemakaian kredit; layar hanya menulis "Sumber penyelesaian retur belum dapat diperiksa" tanpa alasan dan langkah. Uji browser9 tidak membuka layar pilihan ini (fixture lewat HTTP); layar diuji di `91f71ce7` dan tidak berubah sejak itu |
| 2. Uang kembali tercatat sekali, penjaga kas per tanggal | Kode benar (kunci kas, cek kas tanggal ekonomi dan buku, ulang permintaan tidak dobel). **Batas:** tidak ada uji yang membuktikan uang kembali ditolak bila kas/bank tidak cukup |
| 3. Saldo kredit dipakai dan dibatalkan tanpa dobel | Terbukti (batal kedua ditolak, ulang permintaan aman, unik di database); belum ada uji dua sesi bersamaan untuk batal |
| 4. Stok/HPP termasuk saldo awal; jurnal seimbang | Terbukti (14 kasus HPP saldo awal; jurnal tepat dua baris) |
| 5. Koreksi sesudahnya; riwayat; langkah balik di layar | Koreksi pembayaran berkali-kali terbukti; langkah membatalkan pemakaian kredit tampil di layar. **Batas:** koreksi retur dan "Benerin nota" atas invoice yang ikut kredit belum ada (`CP7_CREDIT_SOURCE_CORRECTION_ADAPTER_UNIMPLEMENTED`, `05_factual_profile.sql:45-48`) |
| 6. Bukti Native, race, Auth, browser, P21 | Ada (lihat batas browser di syarat 1) |
| 7. Batas tersisa tercatat | Sebagian: README OW-04 menulis "retur bertingkat belum diuji", padahal sistem menolaknya; penolakan Benerin nota/koreksi retur dan uji kas tidak cukup belum dicatat |

Yang harus dikerjakan (OW-04 dibuka lagi, penulis A):

1. Retur kedua dan seterusnya atas invoice lunas yang sudah punya retur bersaldo kredit, dan retur atas invoice yang
   pernah menerima kredit, harus bisa diselesaikan (uang kembali atau saldo kredit).
2. Koreksi retur dan "Benerin nota" atas invoice yang ikut kredit.
3. Bila sistem tetap harus menolak sesuatu, layar menyebut alasan dan langkah berikutnya, bukan "belum dapat diperiksa".
4. Uji: uang kembali ditolak tanpa efek bila kas/bank tidak cukup pada tanggal itu; dua batal pakai kredit bersamaan.
5. Laporan sesudah kredit: dikerjakan di OW-08a.

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

## OW-04 retur transaksi lunas

Run CI sudah dicek pada 22 Okt (`docs/cp7/handoff/ARAHAN_ASTRA_20261022.md` bagian 2). Pemeriksaan isi kode terhadap
tujuh syarat sedang berjalan; hasil ditambahkan di sini.

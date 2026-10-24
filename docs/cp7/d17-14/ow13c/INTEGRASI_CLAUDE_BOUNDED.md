# Integrasi Claude: jadwal dan saran potong bertahap

Status24 Oktober2026 WIB: komponen server Native6, layar jadwal Entry2 dan
SAVE2000 lulus; kandidat layar kebutuhan d2fdf31f,
run40041003292/job120711808034 INCOMPLETE2/2 karena nama parameter halaman
klien salah (`p_access_epoch`, Native memerlukan `p_access`). Receipt
`d2fdf31-quantity-first-incomplete.json` mempertahankan kegagalan itu;
perbaikan klien dan sambungan langsung Buat Potongan menunggu uji ulang. Dokumen ini tidak menutup OW13c, pemasangan
bawaan, pemulihan sesudah dipakai, rantai A, atau audit independen.

## Dasar yang sudah diuji

| Komponen | Kandidat dan run | Hasil yang dapat dipakai |
| --- | --- | --- |
| Server bounded Native6 | 708c4658 /40034224254 | 6/6; pekerjaan Native nyata DONE pada2000 produk/202000 gerakan, hash stok utuh, izin terkini, K2, kontrak lama dan penolakan UUID lintas metode |
| Jadwal komputer/HP Entry2 | 8f8728bc /40036980136 | 2/2; sumber/keterangan baru, simpan stale ditolak, respons200 terputus lalu pulih dengan UUID/payload/hasil sama, izin terkini |
| SAVE2000 | 8f8728bc /40036980183 | 2/2: satu jangkar lama dan satu kasus skala single-session committed; tiga SAVE5354.884/5375.739/5307.551ms masing-masing <8s termasuk kedua cek sumber dan kedua cek kelayakan |

`BOUNDED_COMPONENT_MATRIX.json` mengikat47 berkas backend yang sama di ketiga
komponen. Jangan menjumlahkan kasus jangkar berulang atau memberi kredit race
pada kasus committed. Kegagalan pertama dan Original utuh tetap disimpan.

## Benturan request yang harus dikomposisikan

`cp7_bounded_analysis_stage` adalah tahap12 pada probe B. Delta tahap ini tepat:
13 fungsi privat, satu facade publik baru, nol tabel, tujuh penggantian fungsi
yang tercantum pada `scripts/cp7_bounded_analysis_stage/MANIFEST.json`.
Installer menyimpan badan/owner/ACL/GUC aktual dan menolak predecessor berbeda.

Predecessor B memuat OW13a `initial_auto` dan OW10 `reorder_supply`. Modul
`cp7_analysis_finance_bridge` juga mengganti
`cp7_analysis_stage.request(jsonb,uuid)`. Keduanya belum dikualifikasi bersama.
Menerapkan salah satunya di atas yang lain akan ditolak pin predecessor; jangan
mengatasi penolakan dengan menghapus pin atau menimpa badan terakhir.

A sebagai integrator perlu menyatukan kedua perubahan request dengan manifest
predecessor/final yang eksplisit, tetap menjaga:

- Jalur lama: dispatch `initial_auto`, mode keuangan dan pemulihan UUID lama.
- Penolakan UUID bounded lewat metode lama dan UUID lama lewat metode bounded.
- `create_job`, satu snapshot Native, izin terkini, K2, idempotensi dan atomicity.
- Jalur bounded saat ini tepat tiga kolom query
  `from_date/group_mode/through_date` dan keuangan `DEFERRED`; parameter
  `finance_mode` tidak sah untuk facade baru. Mengaktifkan keuangan pada metode
  baru memerlukan kontrak/caller dan pengujian komposisi tersendiri.
- Header/halaman operasional tersegel; status keuangan resmi A tetap terpisah,
  UNKNOWN tidak dijadikan nol dan biaya/laba tidak disimpulkan sebelum siap.

Jangan mengubah47 sumber server yang sudah diuji hanya untuk merapikan flag
prototype pada `SOURCE_MANIFEST.json`. Flag itu deklarasi awal; hasil runtime
dan receipt Native6 menjadi bukti kualifikasi komponen, bukan izin produksi.

## Klien, daftar endpoint, dan pemasang

Pemanggil baru milik B ada di `nativeBoundedAnalysis.ts`,
`nativeBoundedQuantity.ts` dan panelnya; tidak mengubah panel analisis/keuangan
bersama milik A. Sumber jadwal menggunakan scope `work-schedule:project:profile`,
hasil kebutuhan `quantity:project:profile`; prefix penyimpanan baru
`erp.cp7.bounded-analysis-request.v1:`. Penanda DONE tetap disimpan untuk reload.
Pemulihan netting/jadwal lama tetap memakai metode asal dan UUID/payload asal.

Gerbang sumber aktual masih menolak17 pasangan endpoint yang belum didaftarkan
oleh A. Daftar tepatnya ada di `BOUNDED_QUANTITY_CLIENT_CHECK.json`. Usulan17
entri persis lulus364 berkas runtime/312 batas RPC; pemeriksa bersama tidak
diubah. Terapkan patch daftar secara berurutan, satu kali saja:

1. Sepuluh entri lama dan satu entri request Native jadwal sesuai catatan
   koordinasi sebelumnya: total11.
2. `BOUNDED_ANALYSIS_REGISTRY.patch`: satu facade bounded, menjadi12.
3. `BOUNDED_QUANTITY_REGISTRY.patch`: lima endpoint Native yang sudah ada,
   menjadi17. Ini bukan lima endpoint server baru.

A memegang pemasang/bundle bawaan, generated types, daftar endpoint, transaksi
pemasangan, lock envelope, serta komposisi rantai. B tidak mengedit berkas itu.
Probe terfokus memasang12 tahap opt-in dan memeriksa invers sebelum-pakai22
kelompok pada masing-masing tahap; bukan bukti pemasang bawaan A sudah berubah.

## Pemulihan sesudah dipakai dan penerimaan akhir

Invers sebelum-pakai menolak sebelum DDL pertama bila ada job bounded nyata
atau receipt jadwal bertanda bounded. Purge job tidak membuat sistem kembali
belum dipakai. Jangan menghapus receipt/hasil agar invers lulus.

A perlu memasukkan seluruh schema/fungsi baru dan tujuh hook ini ke sensus
backup/restore sesudah-pakai serta pemeriksaan pemakaian global. Pada salinan
sekali pakai: simpan keadaan sesudah transaksi nyata, buktikan invers ditolak,
restore backup lengkap, lalu cocokkan22 kelompok katalog dan seluruh data,
termasuk job/reference, jadwal/command, draft/receipt dan stok/uang/HPP.
Pemeriksaan komponen B tidak menggantikan restore global tersebut.

Sesudah komposisi: ulang uji yang terpengaruh, Auth/API/browser nyata pada
request gabungan, kesamaan angka dengan laporan A dan waktu±3600 barang,
baru rantai kualifikasi penuh dan auditor. Semua status ini tetap OPEN sampai
ada Original hasilnya. `production_go` tetap false.

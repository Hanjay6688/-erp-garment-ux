# OW12b — sambungan laporan resmi ke analisis bertahap

23 Oktober2026 WIB. **Kode pemakai dan layar tersedia; OW12b tetap OPEN.** Tidak ada rumus uang baru.
Kontrak ditulis sebelum caller di [CONTRACT.md](CONTRACT.md); dasar A dibaca pada b91a60b, dibandingkan
lagi dengan cabang A16bf8e56 (kontrak/module OW12a tidak berubah).

`scripts/cp7_analysis_finance_bridge` dipasang A sesudah OW12a dan tahap produksi B. API:
`install_delta(cur)`, `verify(cur,state)`, `admit_catalog(before22,after22,state)`,
`rollback_preuse(cur,state)`. A memegang transaksi, envelope lock, penjaga setelah-pakai **global**
dan komposisi/restore penuh. B memeriksa pemakaian job STAGED sebelum DDL rollback pertama.
Setelah job dipurge, pemeriksaan global A atas capture/hasil tetap wajib; penghapusan job tidak membuktikan
tahap belum dipakai. Tidak ada koneksi/commit/penjadwalan/penulis Native di tahap ini.

Delta tepat: satu schema privat/satu pembaca, dua badan request/status yang dipatch dengan anchor sekali
dan hash predecessor. Owner, ACL, proconfig, signature dan atribut dua fungsi lama dipertahankan. Pembaca
baru tetap privat, katalog schema/fungsi persis tersimpan; admisi22 menolak perubahan lainnya. Tidak ada
kolom/tabel/endpoint publik baru dan tidak ada perubahan header/halaman operasional sesudah disegel.

Layar memakai endpoint status analisis yang sudah ada. Pilihan keuangan ikut UUID persisten, termasuk
penunjuk hasil selesai. Operasional bisa selesai ketika laporan masih RUNNING. Pemulihan hanya membaca
job/halaman yang sama. Angka keuangan diperiksa ulang terhadap request/query/run/reference/jam capture;
403 atau pergantian hak/hasil membuang angka lama. Sumber laporan belum READY tidak dijadikan nol.

Bukti lokal:

- `local-finance.json`:7/7 kelompok menjalankan SQL consumer sebenarnya dan finance_apply resmi; identitas,
  job dan API A adalah adapter terkontrol, **bukan Native**. Memeriksa READY/RUNNING/FAILED, akses sebelum
  status dan sesudah hasil, tanggal/pemilik/hash, nilai rupiah9007199254740993.01 dan laba UNKNOWN.
-114/114 uji klien/DOM pada9 berkas (perintah di local-client.json), termasuk uji lama angka keuangan.
  Satu uji tambahan mengikat pergantian waktu capture walau hash sumber tetap sama. TypeScript/CSS lulus.
- Hash predecessor request/status dan kedua patch terhitung cocok. Gerbang seluruh sumber owning-chain
  beku PASS. Pemeriksa sumber berhenti pada6 registry lama milik A, persis permintaan OW16 terdahulu.
- Kegagalan pertama bootstrap, parent UI dan import ownership disimpan terpisah. Adapter parent yang
  dahulu menegaskan keuangan dikecualikan diganti dengan kontrak eksplisit STAGED: request tepat, hasil
  uang menunggu, angka resmi, halaman operasional tersegel dan remount tanpa request baru. Kontrol
  operasional-only lama tetap dijalankan; pengujian/scanner bersama tidak dilonggarkan.

Belum dibuktikan: pemasangan/invers22 pada ujung rantai A, Auth/API/browser asli untuk sambungan ini,
angka identik laporan pada Native, serta waktu sebelum/sesudah pada±3.600 barang. Angka114 dan uji lokal7
tidak menutup kekurangan itu. A menggabungkan dan menguji modul miliknya; B melanjutkan bagian produksi.
Status induk5/16, audit independen dan CP7C tetap belum disetujui.

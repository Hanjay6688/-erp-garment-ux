# CP1/CP2: bukti baru sesudah laporan Astra dikunci

Kandidat tetap `0b7049d9`. Sumber Fable dikunci pada `681dd7a965e1e96267cd64d927faf44f03a92848`. Astra membaca hasil Fable; Astra tidak mengakses hosted, Drive, arsip mentah, atau kunci. Izin D14-1 dicatat sebagai keputusan yang dilaporkan dalam sesi Fable, bukan izin baru untuk tindakan Astra.

## CP1

`CP1_REUSED_EVIDENCE_COMPARISON.json` membandingkan seluruh 16 kategori hasil hosted Fable dengan `docs/evidence/cp6-g01/hosted_summary.json` pada kandidat: semuanya identik, termasuk ledger platform 70 entri. Hash SQL G-01 `223a9653df576581677627a569186d0213d9a8a9145d4b4ed9346910b897aef5`; hash query CP1 V1 `943bf1180e39a898e38aea359a14f1a3459a1e7ad8dde7f35657ced672376509`. Query dan hasil lengkap disalin di `fable-source/`.

**Disposisi: bukti baru Fable diterima sebagai REUSED_AUDITOR_REPORT untuk keadaan hosted pada 14 Oktober 13:18 UTC.** Ini melengkapi rekonstruksi G-01 Astra sendiri. Tidak mengubah perbedaan ledger fixture Astra yang telah dijelaskan: 15 kategori cocok, ledger platform berjumlah sama dengan hash berbeda karena metadata bootstrap. Jangan gabungkan dua jenis pembanding menjadi klaim bahwa semua ledger rekonstruksi byte-identik.

Empat tabel hosted tanpa RLS adalah keadaan baseline v2.6.20 yang dilaporkan Fable; hasil FULL Fable mempunyai nol tabel erp tanpa RLS. Nama empat tabel belum diberikan pada bukti hosted itu. Bukti FULL mengurangi dugaan cacat kandidat, tetapi tidak membuktikan keadaan hosted sudah diperbaiki atau rilis sudah dipasang.

## CP2

Pernyataan lama “restore independen belum tersedia di sesi ini” kini dilengkapi: **Fable menyediakan laporan restore lokal independen**, dengan 142 tabel, 48 view, 436 fungsi, 383 trigger, 419 index, 944 constraint, 190 policy, 104 baris ERP, ledger platform55/aplikasi41; mismatch data/count/identitas kosong, kedua ledger cocok, integrity finding kosong. Arsip terenkripsi dan arsip mentah yang disebut Fable mempunyai hash yang sama dengan receipt penulis yang sebelumnya dibaca Astra. Klaim 148/148 hash mencakup anggota dalam daftar checksum; inventaris 149 anggota penulis juga mencakup berkas daftar checksum, jadi kedua angka tidak otomatis bertentangan.

Label bukti Astra: **REUSED_AUDITOR_LOCAL_RESTORE_REPORT**, bukan restore yang dijalankan Astra. Target aktual menurut addendum A2 adalah **PostgreSQL16.13 dengan stub platform**, lima perintah extension dilewati. Storage hanya dicek hash, tidak diunggah/dibaca ulang melalui layanan storage. Tidak ada transcript restore mentah atau receipt `SELECT version()` pada paket ini untuk diperiksa Astra.

Astra membaca verifier asli `cp2_verify_local_restore.py` pada `41bda0f7`, tidak hanya status PASS. Batas yang ditemukan:

1. `postgres_image:17.6.1.165` dan `mode:FREE_LOCAL_SUPABASE_RESTORE` ditulis sebagai konstanta. Jadi kedua field di laporan Fable **bukan hasil pengukuran engine**; addendum A2 PG16 berlaku. `source_commit_sha` dan `expected_schema_fingerprint` disalin dari recovery manifest, bukan hash engine/working tree yang baru diukur.
2. Perbandingan fungsi memeriksa nama/signature, view nama, trigger nama, constraint/index nama, policy nama. Tidak membandingkan definisi fungsi/view/policy, owner, grant/ACL, definisi trigger/index/constraint lengkap, atau menghitung ulang fingerprint seluruh skema. Tabel memeriksa flags RLS; kolom memeriksa tipe/null/default/generated; data ERP dibandingkan sebagai daftar JSON lengkap; ledger dibandingkan terpisah. PASS ini berharga, tetapi **tidak menyatakan semua definisi dan hak akses byte-identik**.
3. `auth_users=app_users=0` adalah pemeriksaan keadaan kosong, bukan bukti perilaku Auth. `cron.job` stub/record dan `net.http_post` stub tidak menjalankan layanan cron/net yang asli.

**Disposisi: pemulihan katalog/data lokal didukung laporan auditor lain; penerimaan CP2 penuh tetap belum terpenuhi.** Tidak mengulang klaim “tidak ada bukti restore”, tetapi juga tidak mengubah CP2 menjadi NATIVE_ACCEPTED. Bukti lanjutan yang tepat: target engine/platform yang benar, versi aktual tercatat, perbandingan definisi+owner+ACL, data/ledger/integritas, round-trip Storage dan cleanup. Jalankan di lingkungan pemegang arsip tanpa menyalin kunci ke laporan. CP7C tetap HOLD; laporan ini tidak mengizinkan pemasangan atau akses Drive baru.

## Insiden kunci yang dilaporkan Fable

A2 menyatakan sebagian passphrase CP2 tercetak dalam log sesi Fable. Astra tidak membuka log tersebut atau mengambil nilainya. Catat sebagai insiden nyata terpisah dari cacat produk: anggap kunci CP2 itu terpapar, jangan pakai ulang untuk backup baru; pemegang arsip menentukan penggantian/enkripsi ulang dengan bukti pemulihan sebelum salinan lama dihapus. Tidak ada kunci yang ditulis dalam paket Astra.

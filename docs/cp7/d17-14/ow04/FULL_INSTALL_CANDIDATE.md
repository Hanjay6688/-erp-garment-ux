# Paket owning CP7 lengkap dengan OW04

Kandidat ini menghubungkan seluruh komposisi CP7 yang sudah ada dengan owning
installer OW04, termasuk direct Native EMPTY. Entry aplikasi untuk transaksi
tetap RPC produk yang sama. Entry pemasangan atomik sekarang
`scripts/cp7_full_owning_install.py:install(cur)`; caller memiliki transaksi.
Tidak ada commit, penjadwalan cron, pemasangan key ataupun pengiriman WA di
installer. Ini kandidat pengembangan; belum menjadi izin memasang hosted.

Komposisi predecessor adalah F03, planning, baseline, supply, schedule,
netting, analysis, staged reminder, background dispatcher, formula FG/material
dan alert/WA. Hash SQL predecessor hasil generator persis
`e7701eaada592cfd74a8555cf4cdcb7df8d180448213d3bbf5698c3bfa025127`,
sama dengan sumber full bundle yang tercatat pada ledger. Bukan fitur baru
yang ditambahkan akibat pertanyaan tentang WA.

Seluruh pemeriksaan definisi, owner dan ACL predecessor yang sebelumnya ada
pada full rehearsal dipertahankan. Verifier asli note/return correction
berjalan sebelum capture; setelah komposisi, keduanya tetap berjalan melalui
verifikasi ketat live target dan baseline immutable milik OW04. Tidak ada
perubahan terhadap355 pin sumber,30 context atau oracle Native63.

`rollback_preuse(cur,state)` memeriksa hash seluruh baris dan jumlah baris
private, termasuk tiga schema OW04 yang namanya bukan `cp7_*`. Perubahan
baris dengan jumlah tetap juga harus menolak pembatalan. Instalasi yang
sudah dipakai perlu pemulihan backup; pengaman menolak sebelum DROP pertama.
Jalur ini dipakai khusus administrasi, tidak menambah beban simpan produk.

Kualifikasi baru terpisah: `FULL_INSTALL_QUALIFICATION.json` menetapkan64
kasus sebelum eksekusi. Seluruh63 kasus lama dipakai tanpa mengganti oracle;
satu kasus tambahan melakukan penyelesaian CREDIT nyata, meminta pembatalan
instalasi, lalu membuktikan penolakan dan kesamaan semua baris/catalog.
Sebelum suite, installer penuh dibatalkan sebelum dipakai dan keadaan CP6
harus pulih persis, lalu dipasang lagi. Perbandingan hash katalog deterministik
antarinstalasi belum diklaim: guard OW04 mengikat identitas katalog aktual.

Pemeriksaan lokal: AST/import dan64 ID unik lulus; belum eksekusi Native.
Import generator pertama terhenti karena salinan kerja sparse tidak memiliki
file tracked `docs/cp7/evidence/p00/CP7_P00_CATALOGUE.json.gz`. Input asli
dipulihkan dari blob HEAD, SHA256
`274a0f8649ddb4d22887c65f7da1757a92e62e650fb572009af34194a960da2a`;
setelah itu generator/import lulus. Tidak ada isi katalog/oracle diganti.

Uji pertama559dd5f9, run39575195553/job119138875319, berhenti sebelum
kasus Native(0/64): psycopg membaca persen literal pada query berparameter
sebagai placeholder. Seluruh SQL owning OW04 telah terpasang dan diperiksa
sebelum query administrative row guard ini, tetapi itu bukan PASS64.
Transaksi instalasi gagal belum di-commit. Kegagalan/report asli, seluruh
laporan paket dan log lengkap disimpan pada `full-install-559dd5f9/`.
Koreksi memakai perbandingan prefix literal `left(n.nspname,4)='cp7_'`;
set schema yang diikutkan tidak berubah. Lima kontrol offline memakai
parser psycopg asli, mereproduksi error lama dan membuktikan penolakan
sebelum DROP saat hash isi berubah walaupun jumlah baris tetap. Ini bukan
Native execution. Suite64 dan restore tetap wajib dijalankan ulang.

Receipt Native63 e928 dan transport91f tetap bukti kandidat masing-masing.
Kandidat full ini memerlukan hasil baru, bukan pelabelan ulang receipt lama.
OW04 lebih luas, performa global, audit dan pemasangan tetap terbuka;
`production_go=false`, `feature_complete=false`, `audit_complete=false`.

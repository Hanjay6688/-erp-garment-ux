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


## Pembaruan terbaru: installer owning penuh lulus64; runtime lokal offline

Kandidat `d2f3e9bf2bd8fccdd359eac15d6da7ebd85e79dc`, tree
`eab0f603e2bb5cea6a319a65e23e182eaf6afea1`, selesai sukses pada
run39576615486/job119143593080. Native64/64 PASS:63 oracle lama tetap,
ditambah satu penyelesaian CREDIT nyata yang membuktikan rollback instalasi
ditolak sebelum DROP. Semua batas kasus, public catalog, session/advisory
cleanup, restore CP6, advisor dan lima gate paket lulus. Pemeriksaan status
PASS juga mewajibkan rollback sebelum pemakaian dan pemulihan CP6 persis
sebelum pemasangan ulang. Hash SQL predecessor tetap
`e7701eaada592cfd74a8555cf4cdcb7df8d180448213d3bbf5698c3bfa025127`.

Bukti: `full-install-d2f3e9bf/RECEIPT.json`, log job asli lengkap dan
`CASE_RESULTS_FROM_JOB_LOG.jsonl`. Metadata ZIP asli12334494522
(3797682byte, SHA256877dff2b8ef1f31db132b172463f2ea3902b6ff9f1f43ae47f39cd172e65b7bf)
tercatat, tetapi byte ZIP belum diunduh/diverifikasi lokal. Tidak melabeli
hasil rekonstruksi log sebagai salinan byte asli laporan JSON artifact.

Hambatan konkret setelah suite: executor lokal mengembalikan
`409 Conflict, environment_offline: Environment is not connected`.
Tiga percobaan pemulihan gagal; satu probe baca yang tersangkut dihentikan.
GitHub/API tetap tersedia, sehingga hasil CI dan checkpoint disimpan lewat
connector. Ini gangguan lingkungan kerja, bukan permintaan persetujuan owner.

Pekerjaan berikut sudah ditulis pada worktree lokal
`/workspace/scratch/05009cca93f2/erp-ow04-next`,
branch `codex/ow04-next-20261021`, basis559dd5f9; belum commit/push:
pembaca konsumsi kredit read-only, contract/tampilan dan tautan sumber.
Enam uji contract baru + enam DOM baru + tujuh DOM invoice lama lulus19/19;
TypeScript/build/source/access/CSS/secret scan juga lulus pada draft lokal
setelah wiring. Census292 RPC. Dua fingerprint sumber owning/reader berubah,
pin356; ordinary trigger25/fungsi18 dan FK99/117/119 tetap sama.
Belum Native/HTTP/browser proof dan belum consumer undo/APPLY implementation.

File draft:
- `scripts/cp7_customer_credit/readers/04_credit_dependencies.sql`
- `src/salesCreditDependenciesContract.ts` dan test
- `src/SalesCreditDependencies.tsx` dan DOM test
- wiring pada `SalesInvoiceDependencies.tsx`, `database.preconnect.ts`,
  `integration/owning_bundle.py`, kedua source/access census dan SOURCE_PINS.
Generator pin draft juga tersimpan pada
`/workspace/scratch/05009cca93f2/recovered/dependency-reader-source-pins.json`.

Saat lingkungan tersambung: fetch checkpoint terbaru tanpa menghilangkan
draft; commit/rebase draft di atas perbaikan d2f3 (basis lokal draft559 masih
memiliki bug persen lama). Selanjutnya tulis case Native pembaca: REFUND
aktual dan CREDIT tanpa consumer, akses/aktor/revisi/review salah, malformed
query, empty yang terbukti, serta readonly boundary; belum ada case tersebut
yang ditulis. Jalankan qualifier lengkap pada kandidat baru dan update
binding HTTP/browser serta manifest UI hanya setelah bukti Native tepat.
Jangan mengganti receipt e928/91f/d2f3 atau menganggap draft sudah diterima.

Library context file `ERP_WRITER_CONTEXT_20261021.txt` sudah tersimpan versi3,
28 sumber lengkap, dengan Native63/HTTP14/race8/browser4 terbaru91f.
Lead dan sumber tambahan installer64 belum dimasukkan karena executor offline;
checkpoint git ini menjadi tambahan yang harus diserap pada pembaruan berikut.
Identitas file `libfile_900863b8ea248191a20d9f8144bf8dd3` harus dipertahankan.

OW04, CP7 lebih luas dan semua13 item terbuka tidak ditutup oleh64 kasus ini.
Entry baru `cp7_full_owning_install.install(cur)` lengkap sudah qualified,
tetapi adapter default legacy P21, perbandingan deterministik instance guard
dan kelengkapan backup/restore kredit sesudah dipakai belum diklaim.
`production_go=false`, `feature_complete=false`, `audit_complete=false`.

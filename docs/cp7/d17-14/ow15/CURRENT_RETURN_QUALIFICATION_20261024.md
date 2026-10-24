# Perbaikan retur pada instalasi current A/B

**VENI. VIDI. VICI. ERP. — Reliable data adalah dewa.**
Keuangan termasuk laporan, stok, dan HPP adalah raja.

Retur DRAFT dengan pelanggan yang salah sebelumnya menghalangi retur sah lain
pada penjualan yang sama. Perbaikan mempertahankan seluruh baris draft dalam
hash dependensi dan seluruh penguncian sumber. Hanya pemeriksaan pelanggan
pada sibling DRAFT yang dipisahkan dari fakta keuangan POSTED. Memilih draft
yang salah tetap ditolak pengaman Native yang sama.

Entrypoint baru `scripts/cp7_current_return_installation.py` memasang komposisi
A/B, memverifikasi pendahulunya pada database yang sebenarnya, lalu memasang
delta satu fungsi. Entrypoint pendahulu dan sumber SQL yang sudah dibekukan
tetap utuh. `scripts/cp7_current_return_recovery.py` mengikat backup penuh pada
hash sumber komposisi, delta, dan adapter pemulihan.

| Bukti asli | Hasil dan batas |
|---|---|
| Contract Native6, head7a7110f7 | Baseline6 lulus; current5 lulus dan1 counterexample draft. Tetap INCOMPLETE. |
| Closure Native32, headfbc04b53 | Sebelum perbaikan30 lulus+2 counterexample; setelah perbaikan32 lulus.64 eksekusi. Inverse awal tepat; guard setelah penggunaan dan pemulihan penuh tepat. |
| Used restore8, headfbc04b53 | Delapan tahap dan enam kontrol negatif lulus. Backup dipulihkan lagi setelah fault yang menaikkan sequence audit. Retur berikutnya sah; draft salah tetap ditolak. |
| Composed installation8, head4541499e | Delapan tahap, tujuh kontrol negatif dan lima gate paket lulus. Seluruh komposisi membuktikan inverse sebelum penggunaan dan pemulihan setelah penggunaan. |
| Return Race2, head6b7dab37 | Run40082444870 lulus2 baseline+2 current; commit pembatalan penjualan dan kontrol abort, seluruh efek transaksi kedua tepat. |
| Opening replay Native10, head0e29c834 | Run40082679978 INCOMPLETE:10 baseline lulus,0 current berjalan; inverse awal tertahan lock. Original tetap utuh. |

**ReturnRace2 lulus2 baseline+2 current**, termasuk
perbandingan seluruh baris, sequence dan22 kelompok katalog terhadap hasil
pembatalan pertama saja. Receipt: `current-return-race2-first-pass-6b7dab37.json`.
Opening10 pertama tetap **INCOMPLETE**:10 baseline lulus,0 kasus current berjalan.
Inverse awal tertahan SHARE NOWAIT pada `erp.attendance_records`; identitas
pemegang lock belum diamati sehingga penyebab prosesnya tidak ditebak.
Pemulihan penuh data/sequence/katalog dan kesamaan advisor terbukti, tetapi
diagnostik berikutnya membaca variabel advisor instalasi yang belum tersedia.
Seluruh status asli tetap disimpan dalam
`current-opening-replay10-first-incomplete-0e29c834.json`.

Penerus head`e99c1ca7`, run40083710530, memakai kasus bisnis yang sama persis.
Persiapan qualifier menunggu maksimal45detik untuk SHARE lock pada seluruh
tabel yang memang diperiksa produk, mencatat pemegang lock, dan mempertahankan
pengaman NOWAIT produk. Laporan pemulihan parsial juga menangani instalasi yang
belum sempat mengambil advisor. **Original penerus lulus10 baseline+10 current**,
termasuk inverse sebelum digunakan, penolakan inverse setelah sequence berubah,
dan pemulihan penuh seluruh baris/sequence/22 kelompok katalog. Advisor dan lima
gate paket lulus. Persiapan memegang407 tabel baseline dan669 tabel instalasi,
tanpa membatalkan backend. Receipt: `current-opening-replay10-ready-pass-e99c1ca7.json`.

Head`c52f3923`, run40084287050, menambah dua perjalanan Auth nyata untuk retur
Grade A/B dengan sibling DRAFT salah. Original pertama INCOMPLETE: kedua kasus
berhenti sebelum quote karena fixture tidak memiliki pelanggan kedua.
CP6/advisor dan pembersihan Auth tetap lulus. Receipt:
`current-return-auth2-first-incomplete-c52f3923.json`.
Penerus head`b18853df` menyiapkan pelanggan aktif kedua secara eksplisit memakai
helper Native yang sama; seluruh oracle uang/stok/replay/izin/inverse tetap.
Run40085550449 INCOMPLETE: kode pelanggan fixture49karakter melebihi batas30.
Run40085550446 INCOMPLETE sebelum login: argumen fixture masuk ke CLI pemulihan.
Keduanya mempertahankan CP6/advisor dan pembersihan. Receipt pertama tetap utuh.
Penerus head66d41d2e memakai kode29karakter yang diperiksa sebelum DB serta
isolasi argumen fixture yang diuji lewat subprocess sebenarnya. Auth run40086882133 sudah lulus dua kasus, lima gate paket, CP6/advisor dan
pembersihan Auth. Quote/replay/refusal membuktikan seluruh data/sequence/katalog
tepat; angka AR/revenue/FG/COGS dan dua inverse Native tepat. Receipt:
`current-return-auth-bounded2-first-pass-66d41d2e.json`.
Browser run40086882093 juga lulus desktop GradeA dan HP390 GradeB; respons
penyimpanan HP diputus lalu reconcile UUID identik menghasilkan tepat satu retur.
Angka AR/revenue/FG/COGS, tanggal WIB, draft salah tetap utuh dan inverse saldo/stok
tepat. Dua screenshot diperiksa; host keluar0, console0, Auth/data/katalog pulih,
CP6/advisor dan lima gate paket lulus. Invoice POSTED tetap fixture Native,
bukan klaim pembuatan invoice melalui UI. Receipt:
`current-return-browser-bounded2-first-pass-66d41d2e.json`.

Diagnostik tiga kasus laporan, run40085047355, menangkap seluruh enam kegagalan
baseline/current. Masing-masing memiliki satu `PAYROLL_WORK_UNCOVERED`:10 pcs
hasil kerja dengan tarif sumber yang diketahui nol belum terkait payroll.
H_R02 memiliki nol masalah detektor sasaran; seluruh pemulihan dan advisor lulus.
Status asli tetap INCOMPLETE. Receipt:
`current-cash-readiness3-diagnostic-e59e5e5a.json`.
Penerus Native3 melengkapi payroll baru melalui populate/approve Native,
memeriksa linkage tepat satu sumber dan saldo eligible nol, serta modal bank
Native untuk pembayaran0.03. Lima tubuh fungsi oracle diperiksa terhadap
transformasi eksplisit yang hanya menambah prasyarat. Semua pemeriksaan lama
READY/tanggal/sen/inverse/korupsi tetap utuh. Run40086198827 INCOMPLETE pada seluruh3 baseline+3 current:
periode payroll fixture1September bertabrakan dengan payroll seed30Agustus–1September.
Receipt: `current-cash-ready3-first-incomplete-4cec061c.json`.
Penerus `current-cash-linked-qualification` memakai periode kosong2September,
sesuai aturan backlog fungsi populate Native. Sumber pekerjaan tetap1September;
nota/link lama, pool HPP dan seluruh jurnal tetap tepat. Run40087715870 sudah
lulus3 baseline+3 current; enam receipt payroll membuktikan seluruh prasyarat.
Pembayaran/inverse net0 dan tanggal historis tepat; fault tanggal memblokir laporan,
serta fault kronologi failed-wash kembali READY setelah rollback. Lima gate paket,
CP6/advisor dan pemulihan seluruh22 katalog/baris/sequence lulus. Receipt:
`current-cash-linked3-first-pass-31b77abb.json`.

Original composed installation: run40081846443/job120836847789,
artifact12556450449. JSON1133688byte,
SHA256 `8cd8d526218c2e6336c4d3c60cc540767469a13617ed610d05536001a787c59f`.
Receipt rinci: `current-return-installation-first-pass-4541499e.json`.
Backup yang sudah dipakai dipulihkan ke database baru dengan seluruh baris,
sequence, dan22 kelompok katalog tepat; hanya seal OID Native lokal yang
diikat ulang. Pembacaan sumber keuangan/dependensi sama, retur sah berikutnya
berhasil, dan draft salah tetap utuh. CP6 dipulihkan dan advisor identik.

Rekonsiliasi arsip v9 memverifikasi34 Original (21PASS,13INCOMPLETE) beserta
hash setiap berkas yang dipertahankan.28 deklarasi cocok dengan instalasi
pendahulu; enam tidak memuat objek entrypoint lengkap. Arsip v9 belum memuat
hasil composed installation di atas. Kesamaan pohon UI/migrasi tidak meniadakan
perubahan semantik fungsi privat yang terpasang. Karena itu hasil lama tidak
otomatis dipindahkan menjadi penerimaan instalasi yang diperbaiki.

Hasil pertama yang gagal, pengujian lama dan anggaran kasusnya tetap utuh.
Funded12 sudah lulus12 baseline+12 current dengan modal awal fixture yang sah;
hasil Crossflow142 sebelumnya tetap INCOMPLETE. Lima kasus attendance tanpa
jahit,13 kasus FG lama, serta kasus lintas mode yang belum dijalankan tetap
terbuka. Total historis286 terdiri dari248 kontrol unik dan38 duplikasi;
153 Native dan95 lintas mode tidak boleh saling menggantikan.

Ini bukti penulis pada kandidat terpisah. Formal parent tetap5/16,
`production_go=false`; tidak mengubah cabang resmi, hosted, kandidat audit
beku, atau kebijakan owner yang belum diputuskan.

# Pembagian kerja dua penulis untuk sisa D17-14 — versi 2 (22 Okt 2026)

Dasar: D17-14 (daftar kerja), D17-15 (status hasil potong) dan **D17-16** (semua butir tetap lingkup, cara implementasi
diperhalus), kutipan persis di `docs/cp7/OWNER_DECISIONS_20261008.md`. Versi 1 dokumen ini menyarankan beberapa butir
ditunda atau dihapus; owner menolaknya di D17-16, jadi saran itu dicabut.

Prinsip owner: "reliable data adalah dewa, laporan dll adalah raja". Yang menunggu kecukupan data hanya **aktivasi**
metode yang butuh data, bukan keberadaan fiturnya. Bagian yang belum dibuat tetap dicatat terbuka; tampilan atau
cadangan (fallback) bukan bukti selesai.

## 1. Titik awal (serah-terima Astra, `astra/d17-14-integrasi` `01c5f856`)

- Dinyatakan selesai oleh penulis (belum diaudit): OW-01 WA, OW-02 proses server, OW-03 kelipatan produksi, OW-04 retur,
  OW-05 koreksi mandor (`docs/cp7/d17-14/SELESAI_UNTUK_DIUJI.md`).
- OW-06 bayar supplier: mesin di belakang (backend) lulus 10/10 (`docs/cp7/d17-14/ow06/CHECKPOINT.json`), belum ada layar,
  belum di pemasang bawaan, belum uji login/dua pengguna/layar/pasang-pulih.
- Laporan keuangan sesudah retur bersaldo kredit masih BLOCKED (tiga pemeriksa lama) — dicatat di OW-08.
- Batas lama yang tetap terbuka: SQL langsung oleh pengguna login bisa membuat draf dan memanggil penulis supplier
  Native tanpa hak `finance.ap.pay` (FABLE-012, ditunda ke CP7C oleh D14-9; harus dicabut sebelum jalur dipakai).
- Serah-terima Astra menulis "satu writer". Owner (D17-16) meminta pembagian dua penulis; dokumen ini yang berlaku.

## 2. Pembagian per butir dengan cara implementasi D17-16

**Penulis A = Claude** (uang, stok, HPP, laporan; sekaligus penggabung). **Penulis B = Astra** (daftar, produksi,
perencanaan, gudang).

| ID | Butir dan cara implementasi (D17-16) | Penulis | Syarat selesai yang dibuktikan |
|---|---|---|---|
| A1 | Uji ulang OW-04 dan OW-05 | A | Run pembanding dicek, uji klien lokal, alur dibaca ulang |
| OW-08a | Laporan keuangan sesudah saldo kredit pelanggan: pemeriksa laporan mengenal kredit yang sah tanpa melonggarkan selisih lain | A | Laporan READY pada fixture retur bersaldo kredit; selisih yang benar tetap tertangkap |
| OW-07 | Cek HPP: tutup buku tertahan bila kain kantong/absen belum dibagi; sisa WIP PO selesai ditutup saat pool absen aktif belakangan | A | Celah dibuktikan ada/tidak dengan kasus; bila ada, dibetulkan dan diuji |
| OW-06 | Bayar supplier: **satu transaksi kas/bank**, rincian alokasi ke masing-masing utang; **bayar sebagian dan sisa utang**; pembatalan/koreksi konsisten (melanjutkan checkpoint Astra) | A | Layar Pembelian & Penerimaan; alokasi lintas halaman; jumlah sen tepat; login nyata, dua pengguna, layar komputer/HP; pasang/pulih |
| OW-08b | Jurnal kasbon bisa dibuka dari buku besar; piutang ke vendor laundry; cuci gagal sebelum tarif diketahui; koreksi barang jadi lain di QC | A | Alur aplikasi tiap kejadian terbukti; riwayat tetap |
| OW-09 | Urut/saring **atas seluruh hasil pencarian**, lintas halaman; **angka total dan ekspor** memakai filter yang sama — komponen bersama `src/RecordTools.tsx` dan 8 layar | A | Jumlah hasil, total, perpindahan halaman dan ekspor (di layar yang punya ekspor) konsisten pada data di atas satu halaman |
| OW-12a | Keuangan/HPP di analisis skala pabrik: **sumber perhitungan resmi yang sama dengan laporan** (modul baru milik A, dipanggil analisis); hasil operasional tampil dulu, bagian keuangan menunjukkan progres dan kelengkapan; kesimpulan laba/biaya menunggu angka siap; **pembanding periode lalu** di laporan | A (modul angka + laporan) | ±3.600 barang dengan angka keuangan/HPP sama persis dengan laporan; pembanding periode |
| OW-15 | Penggabungan harian dan paket auditor satu versi | A | Kualifikasi penuh; 21 gagal CP6 dan 4 kasus layar tetap gagal dengan pembanding; pemetaan uji pengganti layar yang dipensiunkan |
| OW-16 | Status hasil potong: **mengikuti kejadian fisik dan progres proses**; jelas apa yang selesai dan yang tertunda; rentang wajar per jenis bahan + pola + rentang ukuran, riwayat seluruh pabrik | B | Status keluar sendiri saat potong selesai; layar komputer/HP; nilai batas dari owner |
| OW-10 | Target produksi: **satu mesin hitung** (kebutuhan, stok tersedia, WIP relevan, pesanan, lama produksi, cadangan) — termasuk menyatukan titik pesan ulang barang jadi yang sudah ada; bedakan **kapan perlu produksi** dan **berapa jumlahnya**; rincian ditampilkan agar cadangan tidak dobel | B | Pembanding dihitung terpisah; tidak ada hitung ganda stok/WIP/rencana; hasil lama berubah hanya di tempat yang dijelaskan |
| OW-11a | Model perkiraan: **pemilihan metode menurut kecukupan data**; data minim = metode dasar + penjelasan keterbatasan; metode kompleks dipakai hanya bila **terbukti lebih baik lewat uji terhadap riwayat**; tidak menjanjikan akurasi | B | Uji mundur dengan pembanding; label metode dan alasannya tampil |
| OW-11b | Produk baru: sistem menyarankan **kandidat produk serupa dengan alasan kemiripan**, pengguna mengonfirmasi atau memilih sendiri; label "perkiraan berbasis produk pembanding"; tanpa pembanding layak = "data belum cukup" | B | Saran, konfirmasi, label dan keadaan "data belum cukup" terbukti |
| OW-12b | Kecepatan analisis skala pabrik tanpa mengubah hasil hitung; memasang panggilan ke modul angka A (OW-12a) | B | Ukuran waktu sebelum/sesudah; hasil identik |
| OW-13a | Analisis awal otomatis **setelah data dan konfigurasi minimum siap**; bila belum, tampil apa yang kurang + tombol melengkapinya; tidak mengulang analisis tanpa perubahan data | B | Tiga keadaan terbukti: belum siap, siap → jalan sekali, tanpa perubahan → tidak diulang |
| OW-13b | Yield histori lebih dari 200 grup tidak lagi "belum diketahui" | B | Kasus di atas 200 grup |
| OW-13c | Saran potong di form Buat Potongan: **dari mesin yang sama dengan panel rencana**, dengan waktu analisis dan alasan; pengguna menerapkan atau mengubah jumlah; **cek ulang ketersediaan dan kelayakan saat simpan** | B | Saran sama dengan panel rencana; simpan menolak bila sudah tidak layak |
| OW-14a | Kain berumus di Ringkasan Gudang: ringkasan singkat yang bisa dibuka; **sumber sama** dengan Pengingat/WA/panel; **stok fisik dibedakan dari perkiraan kebutuhan** | B | Angka sama dengan sumber pengingat; label jelas |
| OW-14b | Angka minimum lama di Enteng: tersedia sebagai **referensi konfigurasi lama**, diperiksa saat pemasangan; tampil **angka mana yang aktif**; aturan lama dan baru tidak berjalan bersamaan tanpa keputusan | B (tampilan dan aturan) + A (langkah daftar pemasangan) | Satu aturan aktif yang jelas; referensi lama terbaca saja |

Perkiraan beban: A sekitar 7 hari kerja, B sekitar 7 hari kerja, berjalan bersamaan; total sekitar 7–8 hari kerja
termasuk penggabungan dan paket auditor. Perkiraan kasar; OW-10, OW-11 dan kecepatan OW-12 paling tidak pasti.

## 3. Kepemilikan berkas (mencegah tabrakan)

| Pemilik | Berkas |
|---|---|
| A | `scripts/cp7_customer_credit/**`, `scripts/cp7_supplier_transfer/**`; `scripts/cp7-src/{invoices,finance,hpp-pool,transactions,sales,payroll,supplier-returns}/**`; modul baru angka keuangan untuk analisis (mis. `scripts/cp7-src/planning/finance-capture.sql`) dan `planning/report-staged.sql`; `src/RecordTools.tsx` dan 8 layar OW-09 (`ConnectedCashLedgerPage`, `SalesPaymentPanel`, `SalesReturnPanel`, `ConnectedNotaPage`, `ConnectedAccessoryIssuePage`, `ConnectedFgAdjustmentPage`, `ConnectedFgStockPage`, `ConnectedMaterialCountPage`); layar uang/keuangan/HPP/tutup buku/Pembelian & Penerimaan; workflow dan deklarasi uji bagian itu |
| B | `scripts/cp7-src/{cutting-yield,planning (kecuali dua berkas milik A di atas),baseline,demand,model-native,models,plan-native,stock-formula,warehouse-summary,alerts,reminders,ops,snapshot}/**`; `src/ConnectedCuttingPage.tsx`, `src/NativeCutting*`, `src/Native*Analysis*`, `src/NativeStaged*` (kecuali panel laporan bertahap: koordinasi), `src/NativePlanning*`, `src/NativeModelEvaluation*`, `src/NativePlanDraftPanel.tsx`, layar Ringkasan Gudang dan titik pesan ulang; workflow dan deklarasi uji bagian itu |
| Hanya penggabung (A) | Pemasang dan bundle (`scripts/cp7_*bundle*.py`, pemasang P21 bawaan), tipe hasil generator `src/types/database*.ts`, daftar workflow kualifikasi, migrasi Native `supabase/**` |
| Bersama dengan aturan | `src/App.tsx`, `package.json` dan lock, `docs/cp7/OPEN_WORK_D17_14_20261020.md`, `docs/cp7/OWNER_DECISIONS_20261008.md`, `docs/ERP_BEST_PRACTICES.md`, `docs/cp7/d17-14/SELESAI_UNTUK_DIUJI.md` |

Aturan:
1. Mengubah berkas milik penulis lain: minta lewat `docs/cp7/d17-14/KOORDINASI.md` (berkas, alasan, bentuk perubahan).
   Penggabung atau pemiliknya yang menulis.
2. Berkas bersama: commit kecil tersendiri berlabel `[bersama]`, dicatat di `KOORDINASI.md` hari itu. `OPEN_WORK` dan
   `SELESAI_UNTUK_DIUJI` hanya baris butir sendiri; `OWNER_DECISIONS` dan `ERP_BEST_PRACTICES` hanya menambah di akhir.
   Tanpa paket npm baru kecuali disetujui penggabung.
3. Titik temu yang sudah diketahui:
   - OW-12: A membuat modul angka keuangan/HPP dengan kontrak tertulis di `KOORDINASI.md`; B hanya menambah panggilan
     ke modul itu di analisis bertahap. A tidak mengubah `analysis-stages.sql`; B tidak mengubah modul angka A.
   - OW-10 dan OW-13c memakai mesin yang sama (milik B); OW-16 dan OW-13c sama-sama di halaman Potongan (milik B).
   - OW-09 layar Nota/aksesori/barang jadi/hitung fisik milik B untuk hal lain; untuk OW-09 hanya A yang mengubah bagian
     daftar/urut/saring di layar itu, dicatat di `KOORDINASI.md` sebelum mulai.
   - OW-14b: B membuat tampilan dan aturan "angka aktif"; A menambah langkah pemeriksaan ke daftar pemasangan.

## 4. Cabang, penggabungan, dan uji silang

- Dasar: `astra/d17-14-integrasi` `01c5f856`. Cabang kerja A: `claude/d17-14-uang`; B: `astra/d17-14-produksi`. Cabang
  gabungan tetap `astra/d17-14-integrasi`, hanya digabung oleh A (merge, tanpa rebase atau dorongan paksa).
- Setiap hari pukul 17.00 WIB: kedua penulis mendorong pekerjaan dan menulis satu baris status bahasa sehari-hari. A
  menggabung, lalu menjalankan typecheck, uji klien, pemeriksa sumber dan suite yang tersentuh. Perubahan yang membuat
  merah tidak digabung sampai dibetulkan pemiliknya.
- Setiap dua hari dan sebelum paket: kualifikasi penuh (±117 workflow + skenario CP6 lengkap dengan masukan yang sama
  dengan pembanding) di cabang gabungan, dibandingkan dengan pembanding sebelumnya.
- Ketergantungan: OW-12b (panggilan modul angka) menunggu OW-12a; OW-12a menunggu OW-08a. Selain itu tidak saling tunggu.
- Butir yang dinyatakan selesai dicatat di `SELESAI_UNTUK_DIUJI.md`; penulis yang lain menguji ulang sebelum paket.
  Audit tetap oleh Fable atau Sol.
- Bukti di repo hanya ringkasan dan potongan kegagalan pertama; log lengkap di artifact. Kegagalan pertama disimpan;
  pemeriksaan lama tidak dilonggarkan; nilai kebijakan tidak dikarang.

## 5. Nilai yang masih perlu keputusan owner (diajukan dengan usulan, saat butirnya dikerjakan)

1. OW-16: seberapa lebar batas "wajar" dan minimal berapa kali potong sebelum status keluar.
2. OW-10: tingkat layanan target produksi bila berbeda dari titik pesan ulang barang jadi (bawaan 95%, D17-9).
3. OW-11a: syarat metode dianggap "lebih baik" pada uji terhadap riwayat.
4. D17-13 2.17: batas umur koreksi HPP/harga (bila owner ingin ada batas).

## 6. Kotak untuk owner (salin ke sesi Astra)

````text
Astra, owner memutuskan dua penulis (D17-16). Baca docs/cp7/PEMBAGIAN_DUA_PENULIS_20261022.md versi 2 di cabang
claude/new-session-deapao. Kamu Penulis B: OW-16, OW-10, OW-11a, OW-11b, OW-12b, OW-13a, OW-13b, OW-13c, OW-14a,
OW-14b (tampilan dan aturan), dengan cara implementasi persis seperti tabel bagian 2 (kata-kata owner D17-16).
Buat cabang astra/d17-14-produksi dari astra/d17-14-integrasi 01c5f856. Ubah hanya berkas milik B (bagian 3);
butuh berkas lain: tulis di docs/cp7/d17-14/KOORDINASI.md. Jangan menggabung ke astra/d17-14-integrasi; Claude yang
menggabung tiap hari 17.00 WIB. Uang, stok, HPP, laporan, OW-06, OW-07, OW-08, OW-09 dan paket auditor dikerjakan
Claude. Aturan lama tetap: selesai hanya bila kebutuhan owner terbukti berjalan; kegagalan pertama disimpan; nilai
kebijakan tidak dikarang; bukti besar tidak masuk repo; status ke owner dua kalimat bahasa sehari-hari.
````

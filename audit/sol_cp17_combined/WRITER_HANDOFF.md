# Handoff writer utama — audit Sol CP1–CP7, dfab13bf

**Kandidat masih HOLD.** Tiga perbaikan temuan Sol lama sudah lulus dalam scope `RETEST_SOL_dfab13bf.md`; jangan mengerjakan ulang akar yang sudah ditutup. Kerjakan temuan baru dan lanjutkan pekerjaan lama yang memang belum ditutup. Tidak ada perbaikan produk dari auditor pada cabang ini.

Input produk harus tetap `dfab13bf62398a69a02bf6221c06d29075e5e40b`, tree `886f83312958b53781a450a4ea2a8fb2147b3be3`, sampai writer membekukan kandidat perbaikan berikutnya. Bukti run per kasus ada di `CASE_LEDGER.json`, register `RUN_REGISTER.json`, raw outcome pada paket bukti dengan artifact/member yang disebut. Semua pengujian baru memakai data sekali pakai.

## Daftar kerja tanpa hitung ganda

| Urut | ID / tingkat | Asal | Hasil yang harus dibuat |
|---|---|---|---|
| 1 | KNOWN-UI-MODE / S0 | Sudah diungkap writer; Sol verifikasi | Layar uang UAT tidak mempresentasikan seed sebagai angka buku; sambungan mode UAT terencana dan dibuktikan sebelum dipakai. |
| 2 | SOL-R1-001 / S1 | **Baru, Native + real Auth HTTP** | Koreksi pemasukan sah dapat commit, saldo negatif akhir/prefix tetap ditolak. |
| 3 | SOL-R1-002 / S1 | **Baru, trace kode** | Jalur PO harian Native tersedia tanpa fixture SQL/impor legacy. |
| 4 | KNOWN-DAILY-MASTER / S1 | Sudah diungkap writer; Sol verifikasi | Enam kelompok master harian dapat dipakai pada transaksi nyata. |
| 5 | KNOWN-BF-WAVE / S1 | Sudah diungkap writer; Sol verifikasi kode | Selesai jahit/upah per SKU/ukuran wave BF mempunyai jalur aplikasi sah. |
| 6 | SOL-R1-004 dan SOL-R1-005 / S2 | **Baru, geometri browser demo** | QC/HPP terbaca di HP tanpa overflow body. Dua lokasi diperiksa terpisah, tidak diasumsikan satu akar CSS. |
| 7 | SOL-R1-003 / S3 alat | **Baru, sebelum kasus owner** | Stop baseline sebelum U tidak menuntut capture U; setelah U tetap fail-closed. |

`FINDINGS.json` menyediakan objek per akar: lokasi, expected/observed, tingkat bukti, saran, kasus penerimaan. Dua S1 baru bukan klaim kebocoran angka diam-diam: koreksi tertahan atomik dan PO harian tidak tersedia. S0 adalah presentasi contoh sebagai uang buku pada UAT; tidak ada klaim perubahan database asli.

## SOL-R1-001 — jangan menilai saldo pada setengah koreksi

**Sumber:** `scripts/cp7-src/finance/dated-guards.sql:39–57` membuat trigger AFTER INSERT per credit jurnal. `sales/payment-correction.sql:180–182` membalik pembayaran lama; pengganti baru diposting pada baris 198–201. Trigger membunyikan `CP7_CASH_NEGATIVE` di tengah inverse sebelum pengganti atomik sempat berjalan.

**Reproduksi yang sudah sah, bukan dugaan:**

1. Buat penjualan/payable sah dengan fixture Native yang tersedia; akun OWNER memakai facade public dan token workspace koreksi resmi.
2. Terima pembayaran pelanggan **30,01** ke bank.
3. Bayar supplier **20,00** melalui public writer. Saldo sekarang **10,01**.
4. Koreksi pembayaran menjadi **25,01** pada rekening/tanggal yang sama.
5. Expected: command commit, saldo **5,01**, AR/lineage/GL sesuai pengganti. Actual: `P0001`, HTTP **400**, `CP7_CASH_NEGATIVE ... -20.00`, bank tetap **10,01**.
6. Dengan pembayaran tetap **30,01**, hanya mengubah catatan pun gagal dengan alasan yang sama; expected saldo tetap **10,01**.

Kontrol positif **unspent** 30,01→25,01 berhasil. Kontrol final negatif sungguhan, spent 20/replacement 15,01, ditolak dan seluruh batas unchanged. Karena itu penolakan di langkah 4/6 bukan sekadar fixture salah, izin kurang, token basi atau rekening tidak sah.

**Bukti:** [run 38787925433](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/38787925433), job `116604642907`, artifact `11998368969`, `SOL_CORRECTION_QUALIFIED.json`:

- Native `SOL_R1_CUSTOMER_PAYMENT_CORRECTION_FINAL_POSITIVE` → COUNTEREXAMPLE.
- Real Auth HTTP `SOL_HTTP_SPENT_INCOME_CORRECTION_FINAL_POSITIVE` → COUNTEREXAMPLE.
- Real Auth HTTP `SOL_HTTP_SPENT_INCOME_NOTE_ONLY_CORRECTION` → COUNTEREXAMPLE.
- `SOL_HTTP_UNSPENT_INCOME_CORRECTION_CONTROL` dan `SOL_HTTP_SPENT_INCOME_GENUINE_NEGATIVE_REFUSAL` → PASS.

**Arah perbaikan:** pertahankan aturan D14-3 pada keadaan akhir command/transaksi dan seluruh tanggal ekonominya. Koordinasikan inverse→pengganti sehingga keadaan sementara yang belum bisa di-commit tidak dinilai sebagai saldo akhir. Semua rekening yang terlibat harus tetap terkunci dengan urutan yang konsisten; final validator wajib berjalan sebelum commit. Bila memakai konteks privat, konteks tidak boleh dibuat/dipalsukan oleh caller aplikasi dan tidak boleh membypass pengeluaran/reversal biasa. Jangan mematikan trigger, mengizinkan overdraft, mengubah uang fixture, menambah modal buatan untuk meloloskan koreksi, atau memutasi fakta terposting.

**Uji penerimaan:** pertahankan kasus gagal dan kontrol di atas tanpa mengganti expected. Tambahkan nominal naik/turun/tetap, note-only, bank sama/berbeda, tanggal sama/backdate/later-prefix, dua sesi, grant/revoke, replay UUID/payload berbeda, serta inverse tanpa pengganti yang memang membuat bank negatif. Periksa saldo kas/AR per tanggal, akun/pelanggan, jurnal inverse/pengganti dan lineage, lalu pemulihan seluruh batas. Setelah itu buktikan lewat browser perubahan yang diminta pengguna dan angka hilirnya.

**Cari dampak satu akar, tidak membuat duplikat temuan:** `finance/misc-correction.sql:116–141` juga inverse dahulu baru pengganti; koreksi nota yang membalik pemasukan perlu diperiksa. Dampak di dua jalur itu baru trace statis, belum dinyatakan runtime rusak. Pengeluaran tunggal kosong, backdate sebelum dana dan pemakaian modal yang dibalik sudah lulus/refused sesuai kontrak; pertahankan kontrol tersebut.

**Catatan alat:** INCOMPLETE pertama pada run `38785656146` memakai generic sales token yang tergantung zona session. Qualification mengambil token dari workspace koreksi public seperti UI, tanpa mengubah uang/tanggal/oracle. Metadata `original_posted_facts_immutable=false` pada spent HTTP berasal dari JSON timestamp Asia/Jakarta vs UTC, bukan perubahan fakta; full UTC business/private boundary unchanged pada setiap refusal. Raw asli tetap disimpan.

## SOL-R1-002 — operator membutuhkan PO baru untuk produksi harian

**Bukti STATIC, jangan dipasarkan sebagai Native counterexample:**

- `ConnectedCuttingPage.tsx:193,355` mewajibkan `orderId` dan hanya mencari/memilih PO yang sudah ada.
- `erp_save_cutting_group_before_sewing_v2` menolak bila tidak ada PO aktif (`20260903022604...sql:715–717`).
- `NativePlanDraftPanel.tsx` dan `plan-native/preflight.sql` juga memilih PO existing. `planning/schedule.sql` menyimpan rencana sidecar, tidak menulis `erp.production_orders`.
- Scan `src`, seluruh `scripts/cp7-src`, migrasi dan body bootstrap hanya menemukan INSERT PO pada `erp.apply_migration_open_pos`. Jalur OPEN_PO itu impor saldo awal dan memberi `is_legacy`/`migration_batch_id`, bukan transaksi PO harian biasa.
- Fixture CP17 menyisipkan PO melalui SQL (`cp7_cp17_fix_cases.py:152,166,194`), jadi PASS G1/G2 tidak membuktikan operator bisa memulai PO harian.

**Hasil yang diminta:** jalur PO harian yang jelas dari produksi/Buat Potongan: nomor/identitas, model/ukuran, target, prasyarat master, izin dan request UUID. Gunakan writer Native atau delta Native yang dideklarasikan dengan pembaca hilir; jangan menyalahgunakan impor pembukaan untuk mengaku membuat transaksi harian. Stok/jurnal baru bergerak pada tahap yang memang memosting, bukan karena memilih rencana.

**Penerimaan:** mulai dari master sah tanpa satu PO aktif; buat PO melalui layar, lanjut potong/pickup/G1/laundry/QC/G2. Cocokkan PCS/WIP/upah/HPP/GL; tambah penolakan nomor ganda, referensi model/ukuran, izin, konflik versi dan replay. Jika writer menemukan jalur PO harian yang terlewat, balas dengan komponen→RPC→Native dan saksi positif, bukan hanya nama menu/fitur schedule.

## Pekerjaan lama yang tetap perlu selesai

**KNOWN-UI-MODE:** perbandingan mandiri 48 menu menghasilkan UAT **23 connected, 23 contoh, 1 batas Nota FG, 1 notice Dashboard**; disposable **35 connected, 12 contoh, 1 notice**. Source gates `App.tsx:637,638,761` serta `FinancePages.tsx:51` menyebabkan Ringkasan Keuangan dan Payroll UAT menampilkan angka contoh tanpa label lokal. Inventory browser melihat Rp284,6 jt sebagai “Saldo buku seluruh akun” dengan nol panggilan RPC bisnis halaman itu. Urutan menu dan data lengkap ada di `MENU_MATRIX`.

Badge global memang berbunyi “UAT · MODUL TERPILIH LIVE”; itu tidak memberi tahu bahwa angka pada dua halaman uang ini contoh. Rencanakan aktivasi dan buktikan build UAT terhadap backend disposable sah lebih dulu; kegagalan/403/RPC belum terpasang harus menutup fakta, bukan fallback seed. Merapikan label penting tetapi belum menyelesaikan koneksi jual/uang/absensi. Jangan sekadar mengganti enum mode sebelum jalur, izin, pemulihan dan pembacaan angka terbukti. Hosting/instalasi Enteng tetap di luar izin audit ini.

**KNOWN-DAILY-MASTER:** enam menu `master-fabric`, `master-accessory`, `master-customers`, `master-partners`, `master-workforce`, `master-locations` masih seed/state. Sambungkan operasi harian dan pastikan perubahan master tidak merombak identitas historis. Import awal/master laundry khusus tidak otomatis membuktikan pengelolaan umum harian.

**KNOWN-BF-WAVE:** `sewing.sql:106–107` menambahkan blocker WAVE_SKU_RATES bila `bf_wave_skus_v1` ada. Jalur dasar G1 lulus; jangan memperbaiki ulang dasar. Sediakan jalur wave per SKU/ukuran dengan tarif snapshot dan alokasi per komponen, diuji parsial/replay/inverse/upah/siap laundry, desktop/HP. Jangan membayar tarif dasar untuk melewati blocker wave.

## Dua koreksi tata letak dan satu koreksi alat

- **SOL-R1-004:** `DEMO_SIMULATION/phone/qc`, run `38786177957`, artifact `11998406630`: viewport 390, document 669. Elemen formula CUCI ULANG/GOOD OTOMATIS keluar sisi kanan.
- **SOL-R1-005:** `DEMO_SIMULATION/phone/hpp`, artifact yang sama: viewport 390, document 627. `hpp-size-summary` dan kartu ukuran melebar. Periksa `HppPage.tsx:301`, `hpp.css:23`.
- Kedua inventory raw tetap PASS karena kontraknya hanya membuka dan merekam halaman; geometri menjadi temuan terpisah. Periksa body overflow dan keterbacaan angka, bukan menyembunyikan angka kanan dengan `overflow:hidden`. Layar connected 403 kosong tidak membuktikan layout positif aman. Tidak ada klaim perangkat fisik diuji.
- **SOL-R1-003:** `cp6_t3_aligned_chain.py:88` memanggil `pre_u.finished(PENDING)` meski stop di G01/v2.6.20 sebelum U. Run asli `38785656090` gagal sebelum kasus; kualifikasi `38787131786` menjalankan **58 berkas exact dan 10 owner controls tanpa mengubah SQL/guard**. Buat pemeriksaan stop-aware: sebelum U N/A yang eksplisit, sesudah U tetap wajib capture/count/hash/frozen function dan X admission unchanged. Simpan laporan penolakan sebelum keluar. Jangan menghapus kewajiban pre-U pada chain yang memang melewatinya.

## Bukti aplikasi yang masih kurang — paketkan per rantai

`CHAIN_MATRIX` memberi status per 20 sambungan. Prioritas saksi positif yang belum tersedia pada final stack: POST potong/pickup/QC dari aplikasi; konversi→jual→HPP; Nota Ambil→potongan payroll→kas; BS/rework/klaim/cuci ulang→QC parsial→Nota/bayar; impor WIP→produksi→jual→kas; hitung fisik/tutup periode di tengah rantai. G1/G2 baru diuji pada fixture dasar yang sudah tersedia, bukan membuktikan semua prasyarat bisa dibuat operator.

Untuk setiap saksi baru, rekam angka **sesudah commit sebelum cleanup**: akun/pihak/PO/SKU/ukuran/lot, PCS/nilai, saldo kronologis, HPP, AP/AR, lineage dan laporan sumber. Record Native/control/refusal/replay/race, kemudian browser dengan public facade dan Auth sah. Data fixture perlu untuk isolasi, tetapi pembuatan fakta yang diklaim berasal dari operator harus lewat layar yang sedang dibuktikan. Tiruan HTTP atau sekadar membuka halaman tidak menutup jalur transaksi positif.

## Yang jangan dibuka ulang atau diubah oleh audit ini

SOL-001 direct negative-bank, SOL-002 BE packaging, SOL-003 diagnosis retention, lusin/range, G1 dasar dan G2 dasar mempunyai bukti kelulusan terarah. Raw historis dan qualification tetap dipertahankan. Penyebab AZ pertama dan dua A2 lama tetap unknown/open; jangan menamai autovacuum sebagai fakta tanpa diagnosis lama. Comparator stabil kini lulus sendiri, tidak menghapus root historis.

D14-9 menunda pencabutan 82 penulis hingga CP7C dengan exposure gate; D14-10/11 dan kebijakan SG03 sudah diputuskan owner. Backup/Drive, original CP2 restore, data cutover asli, hosted dan nilai kebijakan pending mengikuti register yang ada; tidak perlu meminta owner mengulang keputusan. Audit ini tidak memberi izin deploy, merge main atau SQL hosted.

## Paket uji ulang berikutnya

Bekukan satu kandidat perbaikan dan tree-nya. Berikan diff per akar, file/ID kasus gagal sebelum→lulus setelah, run/attempt/original artifact, set ID yang cocok, boundary/Auth/session cleanup dan daftar pekerjaan yang belum selesai. Tetap pisahkan **feature_complete / audit_complete / production_go**. Gunakan kasus Sol gagal tanpa mengganti nominal/expected atau menambah modal untuk menyembunyikan kegagalan; uji kontrol negatif dan dampak satu akar. Tidak perlu rerun semua suite yang tidak berubah untuk sekadar menambah jumlah hijau.

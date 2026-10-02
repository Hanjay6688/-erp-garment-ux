# Koreksi nota lama dan seluruh saldo berjalan berikutnya

Permintaan pemilik, 2 Oktober 2026: satu kejadian setahun lalu dibetulkan; saldo berjalan setiap baris berikutnya sampai hari ini harus mengikuti pembetulan. Baris transaksi berikutnya tetap menunjukkan jumlah kejadian aslinya. Koreksi harus atomic. Contoh: 100 lusin awal, salah keluar 2 lusin, lalu 30 pengeluaran masing-masing 1 lusin. Jika pengeluaran pertama sebenarnya 1 lusin, saldo akhir berubah dari 68 menjadi 69 lusin.

**Putusan: mesin saldo resmi mendukung hitung ulang seluruh suffix; kebutuhan produk belum terpenuhi pada buku utama dan alur koreksi nota final.** Tidak ada perubahan pada kode produk F03/F04/F05, paket CP6, branch writer, framework beku atau database hosted. Cabang bukti terpisah: `audit/historical-fg-balances-20261002`, basis `2f504ff994a37cfd2000c0d62eb24231f023e61d`.

## Bukti yang benar-benar dijalankan

Runtime terisolasi: PostgreSQL 18.3 melalui PGlite 0.5.8, database in-memory. Sembilan fungsi SQL asli dimuat tanpa mengubah isi: pembaca buku/ledger, penulis mutasi, guard kronologi, inverse mutasi dan pengurutan/reset buku. Minimal schema/master/auth/label fixtures dinyatakan di REPORT.json. Ini **uji terbatas fungsi stok**, bukan qualification Native lengkap CP6/CP7, audit keuangan, browser, HTTP atau race.

Run final: **12 pemeriksaan PASS**, termasuk dua pemeriksaan yang sengaja membuktikan kebutuhan produk belum terpenuhi. Bukan klaim fitur koreksi selesai. Lihat [REPORT.json](REPORT.json) dan setiap saldo dari 30 pengeluaran di [THIRTY_ROWS.json](THIRTY_ROWS.json).

| Bukti | Hasil |
| --- | --- |
| 100 lusin / 2 lusin / 30 × 1 lusin | Awal 1200 PCS; saldo awal setelah pengeluaran salah 1176 PCS; akhir 816 PCS / 68 lusin. |
| Mutasi koreksi +12 PCS bertanggal kejadian setahun lalu | Semua 30 saldo resmi berikutnya naik 12 PCS. Akhir 828 PCS / 69 lusin; semua jumlah/waktu mutasi asli tetap. |
| Ledger/kartu stok | Semua 30 saldo berikutnya ikut benar; produk ukuran lain tetap 120 PCS. |
| Filter tanggal/toko/jenis dan halaman kedua | Prefix resmi tetap lengkap meskipun mutasi pembentuk saldo disembunyikan. |
| Riwayat setahun, 364 pengeluaran berikutnya | Seluruh 364 saldo resmi diperiksa, melewati 15 halaman berisi 25 baris. Jumlah pengeluaran asli tetap. |
| Koreksi lalu penulis native gagal | Seluruh mutasi, cache stok, lot dan audit kembali ke baseline dalam transaksi uji. |
| Koreksi lalu penempatan buku gagal | Perubahan mutasi dan buku batal bersama dalam transaksi uji. |
| Koreksi membuat stok masa lalu negatif, saldo sekarang masih positif | Guard kronologi asli menolak; tidak ada perubahan tersisa. |

Uji atomic memakai `BEGIN/ROLLBACK` yang membungkus panggilan stok asli. **Belum ada satu API koreksi nota final**; tidak ada bukti atomic nota + piutang + jurnal + HPP dari uji ini. Tidak ada pengujian visibility antar-session maupun command replay.

## FGH-01 — saldo utama buku tidak ikut koreksi historis yang ditambahkan di akhir

`scripts/cp7-src/fg/book.sql` menghitung dua prefix: `book_physical_after` berdasarkan `book_order`, dan `official_physical_after` berdasarkan `physical_at, system_created_at, id`. UI utama `src/ConnectedFgBookPage.tsx` menampilkan saldo buku; saldo resmi berada di detail.

Penulis mutasi asli mendapat `book_order` baru dari sequence sehingga koreksi lama ditambahkan di akhir buku. Dalam uji +12 PCS, semua 30 saldo resmi naik, tetapi semua 30 saldo buku pada kartu lama tetap. Kartu pengeluaran terakhir menampilkan saldo buku 816 PCS sementara saldo resminya 828 PCS. Ini mengikuti aturan manual-order yang sudah ada, namun belum memenuhi permintaan pemilik untuk koreksi yang otomatis terbaca pada seluruh saldo berikutnya di buku.

Kontrol native: memindahkan koreksi tepat setelah sumbernya mengubah semua 30 prefix buku menjadi benar, tanpa mengubah jumlah atau waktu mutasi lain. Kontrol ini adalah panggilan pengurutan eksplisit, **bukan penempatan otomatis dalam fitur koreksi**. Jangan menyelesaikan masalah dengan reset seluruh buku karena susunan manual pemilik akan hilang.

Baris asli pertama tetap immutable dan terpisah dari kompensasi. UI koreksi perlu menampilkan kejadian efektif yang sudah benar beserta riwayat lama/kompensasinya; menggeser kompensasi saja belum membuat jumlah dan saldo pada baris asli pertama menjadi angka revisi. Tentukan pengelompokan sumber + koreksi tanpa menghapus audit asli.

## FGH-02 — inverse saat ini bukan pembetulan bertanggal kejadian lama

`erp.reverse_fg_movement` pada bootstrap yang diterima menggunakan `clock_timestamp()` untuk tanggal inverse. Tidak ditemukan override berikutnya. `SALE_REVERSE` di CP7 tidak menerima tanggal berlaku, dan tidak menggabungkan inverse dengan nota pengganti.

Kontrol 1: inverse sekarang + pengganti sekarang memperbaiki stok saat ini menjadi 69 lusin tetapi seluruh 30 saldo historis tetap salah. Kontrol 2: inverse sekarang + pengganti bertanggal lama justru menurunkan 30 saldo historis sebesar 12 PCS, sementara saldo saat ini tetap 69 lusin. Membetulkan tanggal pengganti saja tidak membetulkan tanggal inverse.

Jalur inverse transaksi nyata dan jalur pembetulan salah catat perlu mempunyai arti yang jelas. Permintaan pemilik adalah pembetulan kesalahan lama: tanggal berlaku pada kejadian sumber, waktu pencatatan hari ini, dengan source/revision lineage yang utuh. Ini perlu implementasi dan proof baru; uji ini tidak mengubah fungsi CP6.

## Handoff untuk writer/integrator

1. Pertahankan fakta posted asli. Simpan revisi/kompensasi terhubung ke kejadian sumber, produk fisik/ukuran, lot, gudang, grade dan tanggal berlaku yang tepat. Pisahkan waktu pencatatan serta alasan/aktor. Label efektif dan sejarah audit harus dapat diperiksa.
2. Susun satu command koreksi final yang mengurus stok dan seluruh dampak nota/uang/HPP yang memang terpengaruh. Jangan memakai stock adjustment saja untuk menyembunyikan nota/piutang yang masih salah. Pakai versi/review sumber yang tepat, izin terkini, request UUID dan penguncian yang sesuai.
3. Koreksi harus berlaku lengkap atau gagal seluruhnya. Uji kegagalan pada tahap uang/HPP, rollback efek stok dan buku, replay setelah respons hilang, intent berubah, izin dicabut serta operasi bersaing. Uji di stack Native asli dan UI terhubung.
4. Kaitkan penempatan/pengelompokan koreksi dengan sumber di buku secara atomic, dengan mempertahankan susunan manual lainnya. Pembaca resmi tetap mengikuti kronologi. Semua saldo berikutnya harus benar melewati filter dan paging.
5. Tanggal efektif yang sama perlu urutan sumber yang tegas; pagi/malam harus tetap berupa kejadian berbeda. Pengambilan pagi/malam dalam satu nota harian belum diuji oleh paket ini.
6. Uji peningkatan dan pengurangan jumlah, beberapa ukuran/lot/gudang/grade, koreksi ulang, retur/pembayaran aktif dan ketergantungan sumber. Hitung prefix lengkap; tolak saldo historis negatif. Jangan menganggap semua perubahan hanya menggeser satu SKU jika ada ketergantungan lain.
7. Tentukan aturan koreksi stok setahun vs periode keuangan/retroaktif HPP ≤3 bulan. Paket ini membuktikan hitung saldo setahun, **tidak memberi izin membuka ulang periode uang setahun**.

Catatan atas penjelasan sebelumnya: `COUNT_CORRECTION` saat ini disimpan sebagai **delta bertanda**, bukan target jumlah fisik absolut. Jangan menganggap opname otomatis menyerap koreksi lama. Jika konsep target fisik absolut ditambahkan, kontrak dan uji ulangnya harus eksplisit.

## Run pertama dipertahankan

[RUN1_REPORT.json](RUN1_REPORT.json): 7 PASS / 1 FAIL. H08 memakai saldo resmi dari kartu terakhir dalam urutan manual sebagai saldo saat ini; kartu itu bertanggal fisik lama. Oracle diperbaiki dengan membaca posisi stok saat ini dan mencocokkannya dengan jumlah seluruh mutasi. Tidak ada fungsi bisnis atau aturan yang diubah. [RUN1_RECEIPT.json](RUN1_RECEIPT.json) dan salinan probe pertama menyimpan hash serta kegagalan asli.

## Menjalankan ulang

Dependency dipasang terpisah dari dependency produk:

```bash
npm install --prefix /tmp/cp7-history-runtime --ignore-scripts --no-audit --no-fund @electric-sql/pglite@0.5.8
CP7_HISTORY_PGLITE_MODULE=/tmp/cp7-history-runtime/node_modules/@electric-sql/pglite/dist/index.js node scripts/audit/cp7_fg_history_probe.mjs
```

Probe tidak menggunakan database URL atau koneksi remote. Source file/function SHA-256 dicatat. Qualification Native lengkap, audit independen keluarga dan production GO tetap tidak diklaim oleh bukti ini.

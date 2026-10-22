# Pembagian kerja dua penulis untuk sisa D17-14 (22 Okt 2026)

Owner (persis): "abis ini astra bakal siapin handoff untuk lu takeover pekerjaannya, lu siapin scope pekerjaannya kalo gitu
kalo mau pake 2 writer biar efektif dan tetap reliable data adalah dewa, laporan dll adalah raja. lu jelasin sedetil
mungkin pembagiannya hindari ada tabrakan yang malah memperpanjang lagi urusan penulisan erp ini, btw kalo yg lu lewati
ini gak usa disentuh sama sekali sbenernya aman aman aja gak buat erp? apa kerugian dan keuntungan dari fitur terlewat
ini? ada poin yang bisa gausah dikerjakan karena overengineeres"

Prinsip: data yang benar nomor satu, laporan nomor dua; kecepatan kerja tidak boleh mengorbankan keduanya. Status per
22 Okt (cabang `astra/d17-14-integrasi`, `0fd3e781`): OW-01..OW-05 dinyatakan selesai oleh penulis, OW-06 sedang
dikerjakan, OW-07..OW-16 belum. Penilaian Claude atas OW-04: belum selesai bagi owner (lihat A2).

## 1. Aman atau tidak bila butir tertentu tidak dikerjakan

Patokan: apakah butir itu bisa membuat **uang, stok, HPP, atau laporan salah atau menyesatkan**. Kalau ya: wajib.
Kalau hanya membuat kerja lebih repot atau rencana kurang tajam: boleh ditunda, dengan kerugian yang jelas.

| Butir | Kalau tidak dikerjakan | Keuntungan bila dikerjakan | Saran Claude |
|---|---|---|---|
| Sisa retur: laporan keuangan menandai saldo kredit sah sebagai selisih | Laporan keuangan tidak bisa dipercaya/dinyatakan siap setelah ada retur bersaldo kredit | Laporan benar | **Wajib** |
| Sisa retur: satu uji gabungan lulus utuh; koreksi 12 dtk, pakai kredit 9 dtk | Bukti belum utuh; pengguna menunggu lama | Bukti bersih; kerja lebih cepat | **Wajib** (bukti); kecepatan sebaiknya |
| OW-07 cek HPP: tutup buku saat kain kantong/absen belum dibagi; sisa WIP PO selesai | Kalau celahnya ada, HPP bisa salah tanpa ketahuan | Kepastian HPP | **Wajib** (cek dulu; perbaikan hanya bila celah terbukti) |
| OW-06 satu transfer untuk banyak penerimaan | Data tetap benar (dicatat per penerimaan), tapi satu transfer bank jadi beberapa catatan; cocokkan rekening bank lebih repot, rawan salah pecah | Kas cocok 1:1 dengan rekening bank | **Penting** |
| OW-09 urut/saring seluruh data di 8 layar | Data aman, tapi daftar panjang bisa menyesatkan ("tidak ada" padahal ada di halaman lain) | Pencarian dan urutan benar | **Penting** |
| OW-08 jurnal kasbon bisa dibuka dari buku besar | Data aman; hanya tidak bisa diklik | Kenyamanan | Ringan, kerjakan |
| OW-08 piutang ke vendor laundry, cuci gagal tanpa tarif, koreksi barang jadi lain di QC | Bila kejadiannya ada di pabrik: tidak bisa dicatat lengkap | Catatan lengkap | **Tanya owner apakah kejadiannya ada**; kerjakan yang ada |
| OW-16 status hasil potong | Pemborosan kain tidak terlihat otomatis | Deteksi potong tidak wajar | **Kerjakan** (permintaan owner D17-15) |
| OW-10 target produksi dengan cadangan | Target = rata-rata jual × hari, tanpa cadangan | Lebih jarang kehabisan | **Sederhanakan**: pakai titik pesan ulang barang jadi yang sudah ada (sudah memuat variasi permintaan dan lama produksi) sebagai cadangan, bukan rumus kedua — mencegah cadangan ganda |
| OW-12 skala pabrik: pembanding periode lalu di laporan | Laporan tidak membandingkan dengan periode lalu | Laporan lebih berguna | **Kerjakan** |
| OW-12 skala pabrik: keuangan/HPP di dalam analisis bertahap | Analisis skala pabrik tanpa angka keuangan; angka keuangan tetap ada di Laporan & Tutup Buku | Satu layar lengkap | **Tunda** (dobel dengan laporan keuangan yang sudah ada); keputusan owner |
| OW-12 kecepatan | Lambat | Cepat | Kerjakan, tanpa mengubah hasil hitung |
| OW-11 model perkiraan pintar (SES/Holt/Croston dipakai bila terbukti) | Rencana pakai rata-rata sederhana atau angka manual | Lebih tepat bila ada pola tren/musim | **Tunda**: Enteng baru mulai; histori penjualan belum cukup untuk membuktikan model lebih baik, jadi hasilnya tetap jatuh ke rata-rata |
| OW-11 produk baru pakai pola produk serupa | SKU baru "belum diketahui" kecuali diisi manual | Rencana awal produk baru | **Sederhanakan**: pengguna memilih sendiri "mirip produk X" (dasar pemilihan jelas), tanpa pemilihan otomatis |
| OW-13 analisis otomatis sebelum analisis pertama | Cukup jalankan analisis sekali saat mulai pakai | — | **Tidak perlu** |
| OW-13 yield histori >200 grup jadi "belum diketahui" | Produk yang paling sering dipotong justru tanpa yield histori | Yield tepat untuk produk utama | **Kerjakan** (kecil) |
| OW-13 saran potong di form Buat Potongan | Saran ada di panel rencana, bukan di form | Kenyamanan | **Tunda** |
| OW-14 angka minimum manual lama di Enteng | Dicek saat pemasangan (baca saja); kalau ada, diketik ulang | — | **Jadikan langkah daftar pemasangan CP7C**, bukan pekerjaan program |
| OW-14 kain berumus di Ringkasan Gudang | Sudah tampil di Pengingat, WA dan panel titik pesan ulang | — | **Tidak perlu** |
| OW-15 paket auditor satu versi | Tidak bisa diaudit | — | **Wajib** |

Kesimpulan: tanpa butir yang ditunda, **data uang, stok dan HPP tetap aman** karena penjaga lama tetap jalan; yang
wajib hanyalah sisa retur (laporan), cek HPP (OW-07) dan paket auditor. Butir lain menambah kenyamanan atau ketajaman
rencana.

## 2. Pembagian kerja

Dua penulis, dibagi menurut **bagian aplikasi dan berkas**, bukan menurut butir. Penulis A = Claude (uang, stok, HPP,
laporan, sekaligus penggabung). Penulis B = Astra (daftar, produksi, perencanaan, pengingat).

### Penulis A — Claude

| Urutan | Pekerjaan |
|---|---|
| A1 | Uji ulang OW-04 dan OW-05 sesudah serah-terima Astra (bukan audit) |
| A2 | Sisa retur: pemeriksa kesiapan laporan keuangan mengenal saldo kredit yang sah tanpa melonggarkan selisih lain; satu uji gabungan lulus utuh; kecepatan koreksi/pemakaian kredit tanpa mengubah hasil |
| A3 | OW-07 cek HPP (kain kantong, absen, sisa WIP PO selesai, tutup buku) |
| A4 | OW-06 satu transfer ke banyak penerimaan (melanjutkan pekerjaan Astra yang sedang berjalan) |
| A5 | OW-08 jurnal kasbon + butir yang owner nyatakan memang terjadi |
| A6 | OW-09 untuk 3 layar uang: `ConnectedCashLedgerPage`, `SalesPaymentPanel`, `SalesReturnPanel` — sesudah komponen bersama dari B (B1) digabung |
| A7 | Penggabungan harian dan OW-15 paket auditor |

### Penulis B — Astra

| Urutan | Pekerjaan |
|---|---|
| B0 | Serah-terima pekerjaan berjalan (OW-06) ke A, dengan titik simpan yang jelas |
| B1 | OW-09 komponen bersama `src/RecordTools.tsx` (urut/saring di server sebelum dibagi halaman, jumlah hasil konsisten) + 5 layar: `ConnectedNotaPage`, `ConnectedAccessoryIssuePage`, `ConnectedFgAdjustmentPage`, `ConnectedFgStockPage`, `ConnectedMaterialCountPage`. Gabungkan `RecordTools` paling awal |
| B2 | OW-16 status hasil potong (per jenis bahan + pola + rentang ukuran, otomatis saat selesai potong) |
| B3 | OW-13 yield histori >200 grup |
| B4 | OW-10 target produksi (versi sesuai keputusan owner) |
| B5 | OW-12 kecepatan dan pembanding periode lalu; bagian angka keuangan/HPP (bila owner tetap meminta) baru dimulai sesudah A2 digabung |
| B6 | OW-11 bila owner tetap meminta (versi sesuai keputusan owner) |

### Kepemilikan berkas

| Pemilik | Berkas |
|---|---|
| A | `scripts/cp7_customer_credit/**`; `scripts/cp7-src/{invoices,finance,hpp-pool,transactions,sales,payroll,supplier-returns}/**`; layar uang dan keuangan (`ConnectedCashLedgerPage`, `SalesPaymentPanel`, `SalesReturnPanel`, `CustomerCreditPanel`, `ConnectedSalesPage`, `ConnectedReceivablesPage`, `ConnectedCustomerHistoryPage`, layar bayar supplier/hutang, layar keuangan, pool HPP, tutup buku); workflow dan deklarasi uji untuk bagian itu |
| B | `src/RecordTools.tsx` dan 5 layar B1; `scripts/cp7-src/{cutting-yield,planning,baseline,demand,model-native,models,plan-native,stock-formula,alerts,reminders,ops,snapshot}/**`; `src/ConnectedCuttingPage.tsx`, `src/NativeCutting*`, `src/Native*Analysis*`, `src/NativeStaged*`, `src/NativePlanning*`, `src/NativeModelEvaluation*`, layar pengingat/WA; workflow dan deklarasi uji untuk bagian itu |
| Bersama (pakai aturan di bawah) | `src/App.tsx`; tipe hasil generator `src/types/database*.ts`; `package.json` dan lock; pemasang dan bundle (`scripts/cp7_*bundle*.py`, pemasang P21 bawaan); daftar workflow kualifikasi; `docs/cp7/OPEN_WORK_D17_14_20261020.md`; `docs/cp7/OWNER_DECISIONS_20261008.md`; `docs/ERP_BEST_PRACTICES.md`; migrasi Native `supabase/**` |

Aturan berkas bersama:
1. Pemasang/bundle, tipe hasil generator, daftar workflow kualifikasi dan `supabase/**` hanya diubah penggabung (A).
   B menulis permintaannya di `docs/cp7/d17-14/KOORDINASI.md` (berkas apa, kenapa).
2. `App.tsx` dan `package.json`: perubahan kecil dalam commit tersendiri berlabel `[bersama]`, dicatat di
   `KOORDINASI.md` pada hari yang sama. Tidak menambah paket npm tanpa persetujuan penggabung.
3. `OPEN_WORK`: masing-masing hanya mengubah baris butirnya sendiri. `OWNER_DECISIONS` dan `ERP_BEST_PRACTICES`: hanya
   menambah di akhir, dalam commit tersendiri.
4. Butuh perubahan di berkas milik penulis lain: minta lewat `KOORDINASI.md`, jangan diubah sendiri.

### Cabang dan penggabungan

- Dasar: titik simpan serah-terima Astra di `astra/d17-14-integrasi`. Cabang kerja A: `claude/d17-14-uang`; B:
  `astra/d17-14-produksi`. Cabang gabungan tetap `astra/d17-14-integrasi`, hanya digabung oleh A.
- Setiap hari pukul 17.00 WIB: kedua penulis mendorong pekerjaannya dan menulis satu baris status. A menggabung keduanya
  (merge, tanpa rebase atau paksa), lalu menjalankan typecheck, uji klien, pemeriksa sumber dan suite yang tersentuh
  hari itu. Yang merah karena perubahan baru tidak ikut digabung sampai dibetulkan pemilik bagiannya.
- Setiap dua hari, dan sebelum paket auditor: kualifikasi penuh (±117 workflow + skenario CP6 lengkap) pada cabang
  gabungan, dibandingkan dengan pembanding sebelumnya.
- Ketergantungan: B5 bagian keuangan/HPP menunggu A2 digabung; A6 menunggu B1 (`RecordTools`) digabung. Selain itu
  kedua penulis berjalan tanpa saling menunggu.

### Standar selesai dan uji silang

- Selesai = kebutuhan owner terpenuhi dan alurnya terbukti (database, dua pengguna bersamaan, login sungguhan, layar
  komputer dan HP, pasang/pulihkan bila menyentuh pemasangan). Kegagalan pertama disimpan ringkas; pemeriksaan lama
  tidak dilonggarkan; nilai kebijakan tidak dikarang.
- Setiap butir yang dinyatakan selesai dicatat di `docs/cp7/d17-14/SELESAI_UNTUK_DIUJI.md`; penulis yang lain menguji
  ulang sebelum paket. Audit tetap oleh Fable atau Sol.
- Bukti di repo hanya ringkasan dan potongan kegagalan pertama; log lengkap di artifact GitHub Actions.

## 3. Keputusan owner yang dibutuhkan di awal

1. Butir yang disarankan "tunda/tidak perlu/sederhanakan" di bagian 1 disetujui atau tidak.
2. Apakah kejadian berikut ada di pabrik: kelebihan bayar ke laundry yang harus dikembalikan vendor; cuci gagal sebelum
   tarif vendor diketahui; koreksi barang jadi di QC selain yang sudah ada.
3. Untuk status hasil potong: seberapa lebar batas "wajar" dan minimal berapa kali potong sebelum status keluar
   (penulis mengajukan usulan, owner memutuskan).
4. Bila OW-10 tidak disederhanakan: tingkat layanan target produksi. Bila OW-11 tetap: syarat model dianggap lebih baik.

## 4. Perkiraan waktu (kasar)

- Dengan saran bagian 1 diterima: sekitar 4–5 hari kerja dengan dua penulis, termasuk penggabungan dan paket auditor.
- Lingkup penuh tanpa penyederhanaan: sekitar 7–8 hari kerja dengan dua penulis.

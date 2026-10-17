# UJI ULANG FABLE r3 — kandidat b53b5acdf260b03ebac3474e9ae837fcef6f6eb1, tree 32f54240 — 2026-10-17

Auditor: Fable, independen, baca-saja terhadap produk. Dasar: laporan Fable r2 terkunci (80f01cee) dan keputusan owner
D16-1 beserta oracle 1–5 yang saya tulis sebelum pekerjaan dibuat (f2758f39,
`audit/fable_cp17_r2/OWNER_DECISION_TO_AUDITOR_20261016_UNHIDE.md`). Kepala penulis saat run `64339905`; beda dari
kandidat hanya 6 berkas `docs/` (pohon produk sama). Status per kasus dibaca dari baris JSON log. Rincian: `WORKLOG.md`,
`MANIFEST.md`. `production_go: false`.

## Ringkasan

Kelima oracle D16-1 terpenuhi. FABLE-016 dan FABLE-018 **DITUTUP**. FABLE-012 **MASIH TERBUKA** (ditunda ke CP7C, D14-9).
**Tidak ada temuan produk baru.** Di build Enteng, 46 menu tersambung tanpa label contoh, tanpa layar batas, dan tanpa luapan,
baik di 1440 px maupun 390 px. Dashboard tetap berupa pemberitahuan tanpa angka, sesuai keputusan F-UI-01. Skenario kas saya
tetap lulus tanpa perubahan. Semua 10 workflow penulis yang saya jalankan ulang lulus per kasus, termasuk 321 kasus CP17
yang separuh browsernya berjalan di build Enteng. Satu kesalahan alat ada di pihak saya (pengecualian Dashboard di sensus) dan
saya catat terbuka.

## Oracle D16-1

| Oracle | Status | Bukti (label) |
|---|---|---|
| 1. Tanpa menu tersembunyi dan tanpa angka contoh di build Enteng; komponen sama dengan build uji; Dashboard angka asli atau pemberitahuan tanpa angka | **DITUTUP** | `src/screenActivation.ts`: 46 CONNECTED + Dashboard NOTICE di kedua mode, tanpa HIDDEN/SAMPLE/BOUNDARY (INDEPENDENT_SOURCE_REVIEW). Sensus saya build ENTENG (run 39053069356) dan DISPOSABLE (run 39052826601): 46 menu tanpa label contoh dan tanpa layar batas; Dashboard berupa pemberitahuan tanpa angka (FABLE). Modul sensus saya menandai Dashboard karena teks "belum tersambung"; oracle tertulis mengizinkannya → kesalahan alat saya, bukan cacat |
| 2. Uji browser build Enteng; OWNER + peran terbatas; 1440 dan 390 px tanpa luapan | **DITUTUP** | Sensus saya build ENTENG: OWNER 1440 dan 390, 0 luapan di 47 menu; GUDANG membuka semua menunya tanpa menu Keuangan (FABLE). Host browser produk membelokkan origin Enteng ke API loopback dan memblokir origin lain; workflow saya dan workflow penulis memetakan host Enteng ke 127.0.0.1 (sensus 159, CP17 1217 permintaan dijawab loopback, 0 error). CP17 menjalankan 55 kasus browser di build Enteng: semua PASS (run 39052840551, INDEPENDENT_NATIVE_RERUN) |
| 3. Rantai lewat layar di build Enteng; penjaga D14-2, D14-3/D15-1, D15-5 tetap menolak | **DITUTUP** | `CP17_BROWSER_R3_03_CHAIN_SEWING_TO_CLOSE`, `_CHAIN_FG_TO_AR_ZERO`, `_GUARDS_REFUSE` PASS di kedua build (run 39052840551). Skenario kas saya tanpa perubahan PASS (runs 39052813501, 39052820257, FABLE) |
| 4. Enam layar baru membaca data nyata; native, race, HTTP, browser desktop + HP; akses sesuai katalog; tanpa tulis yang melewati Native | **DITUTUP** | Sumber: audit, pengaturan, riwayat pelanggan, ringkasan gudang = fasad baca-saja; reminder di atas tabel Native pengingat; pool HPP memanggil penulis Native di bawah kunci periode; tidak ada `insert/update/delete` langsung ke `erp` (INDEPENDENT_SOURCE_REVIEW). `CP17_R3_03_{REMINDERS,ERP_SETTINGS,AUDIT,HISTORY,WAREHOUSE}_*`, `CP17_R3_04_HPP_POOL_*` PASS |
| 5. Skenario Fable lama tetap lulus, juga di build Enteng | **DITUTUP** | `fable_cp17c_cash_basis.py` dan `fable_r2_cash_both.py` tanpa perubahan: PASS. Sensus layar berjalan di build Enteng (dengan catatan Dashboard di atas) |

## Status temuan

| Temuan | Status | Bukti |
|---|---|---|
| FABLE-016 sisa (QC & Final SKU, potongan Nota Ambil Aksesori ke payroll) | **DITUTUP** | `CP17_BROWSER_R3_05_QC_FINAL_SKU_DESKTOP/_MOBILE`, `CP17_BROWSER_R3_05_ACCESSORY_NOTE_TO_PAYROLL_DESKTOP` PASS di kedua build (run 39052840551) |
| FABLE-018 helper alert Laundry | **DITUTUP** | `cp6_bd_browser.mjs` memakai `allInnerTexts()` tanpa menunggu; oracle kasus tidak diubah; `BD_BROWSER:OWNER_POLICY_SET_AND_CLEAR` PASS (run 39052847979) |
| FABLE-012 EXECUTE `authenticated` ke penulis `erp` | **MASIH TERBUKA (ditunda D14-9)** | Tidak berubah. Penulis menambahkan satu hal ke batch pencabutan CP7C: pembungkus publik CP4 pool HPP masih bisa dipanggil pengguna login tanpa penolakan periode tertutup milik fasad baru. Ini satu keluarga dengan FABLE-012 |

## Juga diperiksa (bukan temuan saya)
- **R3-09 pilihan tarif (D16-2..4):** tarif baru dibayar lewat baris revisi tambahan di tabel snapshot tarif PO, dengan indeks
  unik ditambah `committed_at`. Saya periksa semua pembaca tabel itu di paket rilis CP6: lewat `id`, `exists`, `count>0`
  sebagai tanda "sudah ada", atau baris terbaru dengan urutan eksplisit. Tidak ada yang menjumlah per PO × komponen sehingga
  bisa dobel. Fungsi skema dasar di luar pohon tidak bisa saya periksa.
- **R3-02 buka ulang PO:** hanya pemakaian aktif yang menghalangi. Kasus tepi: pembalik barang masuk ikut dihitung pemakaian,
  jadi lebih ketat, bukan lebih longgar.
- **R3-01 nomor PO** lewat 999 tidak macet. **D16-5 Tutup Buku:** tab ada (sensus PASS), riwayat 50 perubahan.
- Jumlah kasus regresi yang bisa dibandingkan sama persis dengan r2 (F03 cash 21, misc 20, payment 23, P12 64/81/43, cutting
  19, P13 25, sales chain 25). Sidik pre-U `eb7f121d` sama.

## Catatan untuk owner (bukan cacat)
- **Dashboard** masih tanpa angka (keputusan F-UI-01). D16-1 hanya mencakup menu yang dulu disembunyikan. Kalau Bos ingin
  Dashboard berisi angka asli, itu permintaan baru.
- **Tarif upah:** sekarang bisa memilih tarif lama atau baru saat jahit selesai, atau memindah PO ke tarif baru seterusnya
  (hanya Owner/Admin).

## Yang harus beres sebelum pemasangan ke Enteng
1. Pasang lapisan database CP7 (CP7C) sebelum UI CP7. Semua 46 layar memanggil fungsi `erp_cp7_*`; di database lama layar
   kesiapan masih gagal 404 (`LEGACY_RUNTIME_GAP`, run 39052847979). Jalankan pemeriksaan di
   `docs/cp7/cp17/R3_INSTALL_TIME_CHECKS.md` yang hanya bisa di Enteng.
2. FABLE-012 / D14-9 dan pembungkus publik pool HPP: cabut hak panggil langsung `authenticated` sebelum `erp` terbuka ke Data
   API.
3. Sahkan tanggal cutover resmi di aplikasi sebelum transaksi operasional pertama (D15-5).
4. Isi data master, tarif mandor, dan resep aksesori produk hasil impor sebelum QC atau rework.
5. Kunci CP2 yang terpapar tidak dipakai lagi.

## Yang belum saya periksa
- Data dan setelan Supabase Enteng: tidak ada akses hosted pada putaran ini.
- Fungsi skema dasar yang membaca tabel snapshot tarif (di luar pohon); ditutup di runtime oleh kasus payroll/detektor penulis.
- Panel detail di balik layar daftar: sensus hanya mencatat tampilan pertama tiap menu.
- Workflow kualifikasi penulis yang tidak saya ulang (receipt 117 run; saya ulang 10 workflow + 4 run Fable). 21 workflow
  CP6 lama tidak saya ulang (pemeriksa lingkup historis dan arsip kedaluwarsa).
- Alat backup CP7C (D13-9a), red team di luar RBAC, pekerjaan auditor lain putaran ini (§16.7).

## Pernyataan paparan
Lihat `MANIFEST.md` §Paparan. Tidak ada laporan, cabang, run, artifact atau komentar auditor lain putaran r3 yang dibuka.
Hosted Enteng tidak diakses; satu run sensus Enteng saya dibatalkan sebelum kasus dan dikirim ulang dengan pemetaan host
ke loopback (WORKLOG CP2).

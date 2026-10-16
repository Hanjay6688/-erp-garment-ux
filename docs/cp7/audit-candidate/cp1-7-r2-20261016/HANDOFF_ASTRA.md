# Uji ulang r2 CP1–CP7 — untuk Astra

Owner menyalin **seluruh isi kotak di bawah** ke sesi Astra. Kandidatnya sama untuk Fable, Astra dan Sol.
Rincian: `README.md` di folder ini.

````text
Kamu Astra, auditor independen. Ini UJI ULANG PUTARAN r2 untuk ERP Garment, repo Hanjay6688/-erp-garment-ux, cabang
writer claude/new-session-deapao. Kamu sudah mengaudit kandidat gabungan dfab13bf (audit/astra_cp17_combined/FINAL_ASTRA.md, RETEST_ASTRA_dfab13bf.md, FINDINGS.json dan audit/astra_cp17_completion/FINAL_ADDENDUM_ASTRA.md, CHAIN_CLOSURE.md, cabang audit/astra-cp1-7-combined-dfab13bf-20261016, kunci 3a3da9ef). Penulis memperbaiki
temuan ketiga auditor di putaran r2 dan menerapkan keputusan owner D15-1 sampai D15-6. Fable, Astra dan Sol menguji
ulang kandidat yang sama secara terpisah.

KANDIDAT
- Commit 2e9d6a468c110684c278d585418eb404250d1150, tree 5e50d224f8e74fa3bca83b599fb606739435b598. Basis audit gabunganmu: dfab13bf62398a69a02bf6221c06d29075e5e40b
  (tree 886f83312958b53781a450a4ea2a8fb2147b3be3). Commit sesudah kandidat di cabang writer hanya dokumen; buktikan:
  git diff --name-only 2e9d6a468c110684c278d585418eb404250d1150 origin/claude/new-session-deapao. Catat tree produk sebelum dan sesudah auditmu (Pro Max §2.8).
- supabase/ tidak berubah sejak dfab13bf (git diff --name-only dfab13bf 2e9d6a468c110684c278d585418eb404250d1150 -- supabase kosong). Perubahan produk ada di
  scripts/cp7-src/ (lapisan CP7) dan src/; daftar lengkap: git diff --stat dfab13bf 2e9d6a468c110684c278d585418eb404250d1150 -- src scripts tests .github.
- Bukti penulis: docs/cp7/audit-candidate/cp1-7-r2-20261016/CI_RECEIPT.json (116 run dari 115 workflow pada 2e9d6a46, semua percobaan pertama, 94 lulus; daftar utama 81/81 lulus; hasil dan sebab 35 workflow CP6 lama lainnya di README.md bagian Kandidat); docs/cp7/cp17/CP17_FIXES.json
  (145 kasus CP17 dideklarasikan sebelum dijalankan: 80 Native, 18 race, 14 HTTP Auth nyata, 33 browser; workflow
  "CP7 CP17 Fixes"; log juga mencetak satu kasus tambahan CP6_AUDITOR_PUBLIC_STATE_STABLE_ORDER). Run, job dan kasus
  disebut terpisah.
- Paket: docs/cp7/audit-candidate/cp1-7-r2-20261016/ (README.md per akar R2-01..R2-10 + D15-5, CROSS_AUDIT.md audit silang
  penulis atas ketiga laporan dfab13bf, SCREEN_MAP.md 48 menu × 3 mode sesudah D15-2). Isinya titik awal penulis, bukan
  bukti lulus.

KEPUTUSAN OWNER BARU (kutipan persis di docs/cp7/OWNER_DECISIONS_20261008.md, baris D15-1..D15-4 dan bagian
"D15-5 dan D15-6"): D15-1 kas minus dinilai menurut tanggal ekonomi dan tanggal buku, juga detektor dan koreksi/
pembalikan; D15-2 layar uang dan absensi di Enteng disembunyikan sampai tersambung; D15-3 layar data master dan tarif
mandor tingkat menengah; D15-4 tombol buka ulang PO dengan penghalang; D15-5 lantai tanggal cutover resmi (WIB) untuk
transaksi operasional baru, dijaga server, jalur saldo awal tetap; D15-6 PO dibuat otomatis oleh Buat Potongan, atomik
dengan posting, kirim ulang UUID sama = hasil sama, draf tanpa efek. Keputusan yang sudah disahkan tidak dibuka ulang;
uji dengan oracle-mu sendiri.

YANG DIUJI ULANG (temuanmu → klaim penulis; uji dengan kasusmu sendiri, angka dan hasil yang kamu harapkan tidak diganti)
- ASTRA-C17-01 (seri dikunci SKU tanpa merek) dan ASTRA-C17-02 (invoice bisa disimpan saat ukuran seri masih dimuat)
  → R2-06: src/SalesDraftPanel.tsx memakai merek + SKU dari baris server, menghapus centang tinjauan saat memilih seri,
  dan memblokir simpan sampai ukuran selesai dimuat. Kasus DOM src/SalesDraftPanel.dom.test.tsx (dua kasus yang
  menyebut ASTRA-C17-01 dan -02; bandingkan dengan kasusmu sendiri); browser
  CP17_BROWSER_D14_5_SERIES_DOZENS_DESKTOP dan _MOBILE dengan merek kedua yang SKU-nya sama (ukuran 32, stok 5) yang
  harus tetap di luar invoice dengan stok tidak berubah.
- ASTRA-C17-03 (angka contoh di mode Enteng) → R2-02: tabel aktivasi src/screenActivation.ts; di Enteng menu tanpa layar
  tersambung tidak tampil, rute langsungnya layar batas tanpa angka; label SIMULASI UX tidak lagi bergantung pada
  tombol; Dashboard hanya menyebut bagian tersambung. src/screenActivation.test.ts; SCREEN_MAP.md.
- ASTRA-C17-04 (data master harian tanpa layar) → R2-03: master.sql, rates.sql, enam layar Master Data (pelanggan,
  supplier/vendor, mandor + tarif upah, gudang/lokasi, kain + benchmark, aksesori + harga mandor); CP17_R2_MASTER_*, race
  per layar, HTTP, browser desktop dan HP per layar.
- ASTRA-C17-05 (panel selesai PO menyebut HPP final dan eligible padahal Native menolak) → R2-05: ruang kerja memakai
  predikat erp.guard_finished_po_source_accounting (SOURCE_UNACCOUNTED), teks dari display_status. Tiga perjalananmu
  dengan hitunganmu: CP17_R2_ASTRA_G1_G2_TEN_PIECES_CONSERVED, CP17_R2_ASTRA_G2_UNSEWN_SIX_MUST_NOT_FINISH,
  CP17_R2_ASTRA_G2_SEWN_UNSENT_SIX_MUST_NOT_FINISH; browser G2 desktop dan HP.
- ASTRA-C17-06 (entry point arsip CI kedaluwarsa) → R2-08: G01, T2 dan 37 workflow CP6 lama memanggil bootstrap dari
  checkout cabang sekarang dan tetap jalan walau arsip AC terhapus; daftar "sebelum U" sadar titik berhenti. Langkah X dan
  oracle tidak diubah (commit e3e12ea7). Hasil per workflow (lulus, pemeriksaan cakupan historis yang sengaja
  tidak dilonggarkan, artifact kedaluwarsa, tanpa pemicu manual) ada di README.md bagian Kandidat dan CI_RECEIPT.json.
- ASTRA-C17-07 (bukti alur lewat aplikasi) → R2-07: CP17_BROWSER_R2_07_IMPORT_WIP_BRAND_SALE_CASH_CLOSE dan
  CP17_BROWSER_R2_07_BS_REWORK_NOTA_PAYROLL_PAY (rincian di README.md). Fixture hanya memberi rekening bank, modal sebesar
  upah untuk rantai kedua (D14-3), dan keadaan alat uji.
- Pertentangan "nol overflow" dengan Sol: penulis mengukur ulang QC 669 px dan HPP 627 px pada 390 px (CROSS_AUDIT.md §4).
  Sesudah R2-09, rumus yang dipakai ditulis: document.documentElement.scrollWidth <= window.innerWidth
  (scripts/ui_phone_width_census.mjs). Ukur ulang dengan rumusmu dan tulis rumusnya.
- "80 uji" di laporan penulis yang lalu → CI_RECEIPT.json dan README menyebut run, job dan kasus terpisah.

JUGA PERIKSA (fitur baru r2 yang bukan temuanmu, dan regresi di sekitarnya)
- R2-01 penjaga kas dua tanggal dan koreksi majemuk (FABLE-013, SOL-R1-001; dated-guards.sql).
- R2-04 / D15-6 PO otomatis dari Buat Potongan (auto-po.sql; layar terkunci sesudah posting mode "PO yang sudah ada"
  ditemukan dan diperbaiki penulis saat kualifikasi, 3b7cf370) dan D15-5 lantai tanggal cutover (cutover.sql).
- R2-05 tombol buka ulang PO (po-reopen.sql), R2-09 layar demo QC/HPP di HP, R2-10 jahit selesai per SKU untuk
  potongan wave BF (sewing.sql; CP17_R2_10_*).
- Bahwa penjaga lama tidak dilonggarkan: kas per tanggal (D14-3) di semua pengeluaran, bayar upah tidak mendahului akrual
  (D14-2), kartu stok, kebijakan HPP, dan bahwa delta Native yang dideklarasikan tetap hanya berlaku di dalam perintahnya.

YANG SUDAH DIKETAHUI PENULIS (uji sendiri; jangan dianggap benar atau salah tanpa bukti)
- Pool HPP absensi tidak punya layar yang menjalankan siklusnya; r2 tidak menambahkannya. Ini batas yang dicatat penulis,
  bukan keputusan owner.
- Lapisan CP7 belum terpasang di Enteng (CP7C ditahan, D13-9a). Layar yang tersambung untuk Enteng menurut
  src/screenActivation.ts, termasuk layar master baru, memanggil RPC erp_cp7_* yang baru ada sesudah pemasangan itu.
  Semua uji browser memakai build DISPOSABLE_TEST di database sekali pakai.
- Produk dari impor belum punya resep aksesori: QC → barang jadi dan order rework ditolak Native sampai resep ditetapkan di
  Produk & SKU (boleh tanpa aksesori), dan resep itu berlaku mulai saat disimpan.
- Penjaga tanggal cutover (D15-5) tidak menolak apa pun sampai tanggal resmi disahkan lewat aplikasi.
- Sensus lebar HP 48 menu memakai build demo; layar tersambung diperiksa hanya pada layar yang dilewati uji browser HP.
- FABLE-012: 82 penulis erp masih bisa dieksekusi authenticated lewat SQL, tidak terjangkau Data API; pencabutan ditunda ke
  CP7C (D14-9).
- Alat receipt scripts/cp7_ci_receipt.py di kandidat hanya membaca 100 run pertama per commit; CI_RECEIPT.json dibuat
  dengan salinan yang membaca semua halaman (README.md bagian Kandidat). Hitung sendiri run pada commit kandidat.

ATURAN
- Tanpa saling intip (Pro Max §2.2, §16.7): jangan membaca laporan, cabang, run, artifact atau komentar auditor lain dari
  putaran ini sampai laporanmu dikunci dengan commit. Laporan yang sudah terkunci sebelum putaran ini (ketiga audit
  gabungan dfab13bf) boleh dibaca; audit silang penulis ada di CROSS_AUDIT.md.
- Label asal-bukti per klaim (§2.9). Baca status per kasus dari log atau artifact, bukan warna job (§2.10). Rerun paling
  banyak sekali dan hanya bila job mati sebelum kasus berjalan (§1.9).
- Dispatch workflow writer hanya dengan ref claude/new-session-deapao dan catat head_sha yang terpakai; bila head sudah
  bergeser, buktikan tree produk sama sebelum memakai hasilnya (§1.7, §2.8, §16.1).
- Jangan percaya klaim penulis begitu saja: susun oracle sendiri dari kontrak dan keputusan owner (D14-2..D15-6).
  Pertanyaan yang sudah dijawab owner tidak ditulis ulang sebagai terbuka (§2.12).
- Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only), production. Jangan meminta password, token atau kunci di chat.
- Panduan: docs/AUDIT_PANDUAN_PRO_MAX.md (SHA-256 5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639,
  sama dengan putaran sebelumnya). Bila ada beda, berkas di repo yang berlaku.

LAPORAN
- Satu cabang audit baru, usul: audit/astra-cp1-7-r2-2e9d6a46-<tanggal>, dikunci dengan commit sebelum membaca laporan
  auditor lain di putaran ini:
  1. audit/astra_cp17_r2/RETEST_ASTRA_2e9d6a46.md — per temuanmu: DITUTUP / MASIH TERBUKA / BARU, dengan bukti;
  2. audit/astra_cp17_r2/FINDINGS.json — temuan baru per akar masalah (fitur baru r2 dan regresi), tingkat, bukti;
     daftar yang harus beres sebelum pemasangan ke Enteng; daftar "belum saya periksa".
- Ringkasan untuk owner ≤ 10 kalimat, bahasa sehari-hari. Owner bukan programmer.
````

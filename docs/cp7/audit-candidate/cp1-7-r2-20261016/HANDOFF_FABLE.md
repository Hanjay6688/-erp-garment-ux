# Uji ulang r2 CP1–CP7 — untuk Fable

Owner menyalin **seluruh isi kotak di bawah** ke sesi Fable. Kandidatnya sama untuk Fable, Astra dan Sol.
Rincian: `README.md` di folder ini.

````text
Kamu Fable, auditor independen. Ini UJI ULANG PUTARAN r2 untuk ERP Garment, repo Hanjay6688/-erp-garment-ux, cabang
writer claude/new-session-deapao. Kamu sudah mengaudit kandidat gabungan dfab13bf (audit/fable_cp17_combined/RETEST_FABLE_dfab13bf.md, FINAL_FABLE.md, FINDINGS.json dan OWNER_DECISIONS_TO_AUDITOR_20261016.md, cabang audit/fable-cp1-7-combined-dfab13bf-20261015, kunci ccafdb18). Penulis memperbaiki
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
- FABLE-013 (penjaga kas hanya tanggal ekonomi) → R2-01: penjaga menilai tanggal ekonomi dan tanggal buku; koreksi
  pembayaran pelanggan, koreksi lain-lain dan koreksi nota penjualan dinilai pada keadaan akhirnya; detektor memeriksa
  kedua tanggal. scripts/cp7-src/finance/dated-guards.sql (+ misc-correction.sql, sales/correction.sql,
  sales/payment-correction.sql). Skenariomu fable_cp17c_cash_basis.py dengan angkamu: CP17_R2_CASH_BOOK_DATE_REFUSED;
  detektor: CP17_R2_DETECTOR_BOOK_DATE_LISTED.
- FABLE-014 (PO selesai tidak bisa dibuka ulang; komentar "no Native inverse" salah) → R2-05: po-reopen.sql membuka
  ulang lewat erp.reopen_production_order dengan token tinjauan, alasan, idempotensi, riwayat tetap dan penghalang
  NOT_FINISHED, FG_USED, PERIOD_CLOSED; komentar dibetulkan. Oraclemu D15-4: CP17_R2_PO_REOPEN_THEN_FINISH_SAME_HPP,
  CP17_R2_PO_REOPEN_BLOCKERS_UNCHANGED, CP17_RACE_R2_PO_REOPEN_TWO_TABS_ONE_WINS, CP17_HTTP_R2_PO_REOPEN, browser
  CP17_BROWSER_R2_PO_REOPEN_DESKTOP dan _MOBILE.
- FABLE-015 (angka contoh di mode Enteng) → R2-02: tabel aktivasi src/screenActivation.ts; di Enteng menu tanpa layar
  tersambung tidak tampil, rute langsungnya layar batas tanpa angka; label SIMULASI UX tidak lagi bergantung pada tombol.
  Oraclemu D15-2: src/screenActivation.test.ts, src/OwnerDashboard.dom.test.tsx; SCREEN_MAP.md.
- FABLE-016 (bukti alur lewat aplikasi) → R2-07: dua rantai browser yang hanya memakai layar, mulai dari Impor data awal:
  CP17_BROWSER_R2_07_IMPORT_WIP_BRAND_SALE_CASH_CLOSE (WIP → barang jadi → Ganti Merek → tutup buku di tengah rantai →
  jual → bayar ke bank → buka buku; buku tertutup tetap sama) dan CP17_BROWSER_R2_07_BS_REWORK_NOTA_PAYROLL_PAY (komponen
  dan tarif mandor di Master Data → pisah BS → resep aksesori produk di Produk & SKU → klasifikasi BS dengan komponen
  itu → rework ke mandor → hasil → upah rework di Nota → payroll dihitung, disetujui, dibayar). Fixture hanya memberi rekening bank, modal sebesar upah untuk rantai kedua (D14-3), dan keadaan alat uji.
- FABLE-017 (data master dan tarif mandor tanpa penulis) → R2-03: master.sql, rates.sql dan enam layar Master Data.
  Oraclemu D15-3: rantai CP17_BROWSER_R2_FABLE_D15_3_SCREEN_CHAIN_DESKTOP dan CP17_R2_FABLE_D15_3_SCREEN_CHAIN_WAGE_AT_SEWING_DATE
  (mandor + tarif baru → Bagi Potongan → jahit selesai dengan tarif pada tanggal jahit; ubah tarif sesudahnya tidak
  mengubah upah tercatat), CP17_R2_MASTER_*, race per layar, HTTP, browser desktop dan HP per layar.
- FABLE-011 (tanpa lantai tanggal cutover) → D15-5: scripts/cp7-src/cutover/cutover.sql; CP17_R2_D15_5_* (batas 00:00
  vs 23:59:59 WIB untuk jurnal dan stok, jalur saldo awal + invoice terlambat + pelunasan, gagal di tengah, kirim ulang),
  dua race, HTTP, browser desktop dan HP.
- FABLE-005 (pemetaan 75 C6 + 22 ALL hanya di cabang Astra) → disalin byte demi byte ke docs/evidence/c6-all-crosswalk/
  (syaratmu sendiri); bandingkan hash dengan berkas Astra.
- Catatanmu soal T2/arsip CI → R2-08 (lihat Juga periksa).
- FABLE-012 → tidak berubah, tetap ditunda ke CP7C (D14-9).

JUGA PERIKSA (fitur baru r2 yang bukan temuanmu, dan regresi di sekitarnya)
- R2-04 / D15-6 PO otomatis dari Buat Potongan (auto-po.sql): CP17_R2_D15_6_* (satu transaksi, UUID sama, gagal di tengah,
  draf tanpa efek, hak akses, lanjut Bagi Potongan dan jahit), dua race, HTTP, browser. Saat kualifikasi penulis menemukan
  layar terkunci sesudah posting mode "PO yang sudah ada" dan memperbaikinya (3b7cf370; CROSS_AUDIT.md §7).
- R2-06 seri lusin penjualan (merek + SKU), R2-08 alat uji arsip CI (G01, T2 dan 37 workflow CP6 lama; hasil per workflow di README.md dan CI_RECEIPT.json),
  R2-09 layar demo QC dan HPP di HP 390 px (workflow "UI phone width census"), R2-10 jahit selesai per SKU untuk potongan
  wave BF (sewing.sql; CP17_R2_10_*).
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
- Satu cabang audit baru, usul: audit/fable-cp1-7-r2-2e9d6a46-<tanggal>, dikunci dengan commit sebelum membaca laporan
  auditor lain di putaran ini:
  1. audit/fable_cp17_r2/RETEST_FABLE_2e9d6a46.md — per temuanmu: DITUTUP / MASIH TERBUKA / BARU, dengan bukti;
  2. audit/fable_cp17_r2/FINDINGS.json — temuan baru per akar masalah (fitur baru r2 dan regresi), tingkat, bukti;
     daftar yang harus beres sebelum pemasangan ke Enteng; daftar "belum saya periksa".
- Ringkasan untuk owner ≤ 10 kalimat, bahasa sehari-hari. Owner bukan programmer.
````

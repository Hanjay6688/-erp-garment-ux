# Uji ulang r3 CP1–CP7 — untuk Fable

Owner menyalin **seluruh isi kotak di bawah** ke sesi Fable. Kandidatnya sama untuk Fable, Astra dan Sol.
Rincian: `README.md` di folder ini. Kotak belum boleh dikirim selama masih ada tanda `<...>` (angka receipt diisi penulis sesudah semua run kandidat
selesai).

````text
Kamu Fable, auditor independen. Ini UJI ULANG PUTARAN r3 untuk ERP Garment, repo Hanjay6688/-erp-garment-ux, cabang
writer claude/new-session-deapao. Kamu sudah menguji ulang kandidat r2 2e9d6a46 (audit/fable_cp17_r2/RETEST_FABLE_2e9d6a46.md,
FINDINGS.json, cabang audit/fable-cp1-7-r2-2e9d6a46-20261016, kunci 80f01cee) dan sesudah lock mencatat keputusan owner
D16-1 beserta oracle uji ulangmu 1–5 (OWNER_DECISION_TO_AUDITOR_20261016_UNHIDE.md, commit f2758f39). Penulis memperbaiki
temuan ketiga auditor di putaran r3 dan menerapkan keputusan owner D16-1 sampai D16-5. Fable, Astra dan Sol menguji ulang
kandidat yang sama secara terpisah.

KANDIDAT
- Commit b53b5acdf260b03ebac3474e9ae837fcef6f6eb1, tree 32f54240a60e01ab8b1ffad7267d285a669be520. Basis r2: 2e9d6a468c110684c278d585418eb404250d1150
  (tree 5e50d224f8e74fa3bca83b599fb606739435b598). Commit sesudah kandidat di cabang writer hanya dokumen; buktikan:
  git diff --name-only b53b5acdf260b03ebac3474e9ae837fcef6f6eb1 origin/claude/new-session-deapao. Catat tree produk sebelum dan sesudah auditmu (Pro Max §2.8).
- supabase/ tidak berubah sejak 2e9d6a46 (git diff --name-only 2e9d6a46 b53b5acdf260b03ebac3474e9ae837fcef6f6eb1 -- supabase kosong). Perubahan produk ada
  di scripts/cp7-src/ (lapisan CP7) dan src/; daftar lengkap: git diff --stat 2e9d6a46 b53b5acdf260b03ebac3474e9ae837fcef6f6eb1 -- src scripts tests .github.
- Bukti penulis: docs/cp7/audit-candidate/cp1-7-r3-20261017/CI_RECEIPT.json (<RECEIPT>); docs/cp7/cp17/CP17_FIXES.json
  (321 kasus CP17 dideklarasikan sebelum dijalankan: 153 Native, 34 race, 24 HTTP Auth nyata, 55 browser, dan 55 kasus
  browser yang sama di build mode Enteng; workflow "CP7 CP17 Fixes"). Run, job dan kasus disebut terpisah.
- Paket: docs/cp7/audit-candidate/cp1-7-r3-20261017/ (README.md per akar R3-01..R3-09 + D16-5, CROSS_AUDIT.md audit silang
  penulis atas ketiga laporan r2, SCREEN_MAP.md 47 menu × 3 mode). Isinya titik awal penulis, bukan bukti lulus.

KEPUTUSAN OWNER BARU (kutipan persis di docs/cp7/OWNER_DECISIONS_20261008.md, D16-1 sampai D16-5): D16-1 "selesain biar
gausa sembunyiin" (layar yang disembunyikan di Enteng diselesaikan dan disambungkan; tafsiranmu dan oracle 1–5 dicatat di
sana); D16-2..D16-4 pilihan tarif mandor lama atau baru saat jahit selesai, tombol per PO "pakai tarif baru seterusnya",
hanya Owner/Admin; D16-5 "Tutup Periode" digabung sebagai tab "Tutup Buku" di "Laporan & Tutup Buku", hak lihat dan hak
tutup tetap terpisah, arsip dan riwayat lengkap, tautan lama diarahkan. Keputusan yang sudah disahkan tidak dibuka ulang;
uji dengan oracle-mu sendiri.

YANG DIUJI ULANG (temuanmu dan oraclemu → klaim penulis; angka dan hasil yang kamu harapkan tidak diganti)
- Oracle D16-1 nomor 1 (tidak ada menu tersembunyi atau angka contoh di build Enteng; komponen sama dengan build uji) →
  R3-03: src/screenActivation.ts tanpa HIDDEN; src/screenActivation.test.ts; SCREEN_MAP.md.
- Oracle nomor 2 (uji browser build Enteng, OWNER + peran terbatas, 1440 dan 390 px, tanpa luapan) → setiap kasus browser
  CP17 berjalan lagi di build mode Enteng (scripts/cp6_auditor_browser_host.mjs AUDITOR_UI_MODE=ENTENG; id berakhiran _ENTENG;
  alamat proyek Enteng dijawab API lokal di runner, alamat lain diblokir).
- Oracle nomor 3 (rantai layar): CP17_BROWSER_R3_03_CHAIN_SEWING_TO_CLOSE, CP17_BROWSER_R3_03_CHAIN_FG_TO_AR_ZERO,
  CP17_BROWSER_R3_03_GUARDS_REFUSE (D14-2, D14-3/D15-1, D15-5 menolak dengan kalimat server persis, tanpa perubahan). Fixture
  rantai jahit → tutup buku mengisi hari absensi kosong peninggalan data uji lain sebagai OFF sebelum menutup (lihat
  README.md, "Ditemukan penulis").
- Oracle nomor 4 (layar baru membaca data nyata; Native, race, HTTP, browser; akses sesuai katalog; tidak ada tulis yang
  melewati Native) → Reminder, Pengaturan ERP, Audit Trail, Riwayat Pelanggan, Ringkasan Gudang, Pool HPP absensi:
  CP17_R3_03_{REMINDERS,ERP_SETTINGS,AUDIT,HISTORY,WAREHOUSE}_*, CP17_R3_04_HPP_POOL_*.
- Oracle nomor 5 (skenario lama tetap lulus, juga di build Enteng) → semua kasus CP17 lama ada di grup browser dan
  browser_enteng; receipt.
- FABLE-016 sisa (QC & Final SKU dan potongan nota aksesori ke payroll hanya diuji lewat SQL/UI beku) → R3-05:
  CP17_BROWSER_R3_05_QC_FINAL_SKU_DESKTOP/_MOBILE, CP17_BROWSER_R3_05_ACCESSORY_NOTE_TO_PAYROLL_DESKTOP.
- FABLE-018 (helper alert Laundry menunggu elemen yang sudah hilang) → R3-06: scripts/cp6_bd_browser.mjs (commit 0e9e6fbc);
  oracle BD_BROWSER:OWNER_POLICY_SET_AND_CLEAR tidak diubah.
- FABLE-012 → tidak berubah, tetap ditunda ke CP7C (D14-9).

JUGA PERIKSA (bukan temuanmu, dan regresi di sekitarnya)
- R3-01 nomor PO otomatis lewat 999 (ASTRA-R2-02, SOL-R2-001), R3-02 buka ulang PO hanya dihalangi pemakaian aktif
  (ASTRA-R2-01), R3-09 pilihan tarif (D16-2..D16-4; R3_09_RATE_CHOICE_DESIGN.md), D16-5 tab Tutup Buku (ADMIN punya hak
  laporan tanpa hak tutup: tanpa tab, fasad periode menolak).
- Layar kasbon: penulis menemukan saat kualifikasi bahwa penolakan kasbon diberi tambahan palsu "Refetch authoritative
  gagal" dan memperbaikinya (src/PayrollKasbonPanel.tsx, uji DOM; README.md).
- Bahwa penjaga lama tidak dilonggarkan: kas per tanggal ekonomi dan buku (D14-3, D15-1), bayar upah tidak mendahului akrual
  (D14-2), lantai cutover (D15-5), kebijakan HPP, dan bahwa delta Native yang dideklarasikan tetap hanya berlaku di dalam
  perintahnya.

YANG SUDAH DIKETAHUI PENULIS (uji sendiri; jangan dianggap benar atau salah tanpa bukti)
- Lapisan CP7 belum terpasang di Enteng (CP7C ditahan, D13-9a); build Enteng diuji terhadap salinan sekali pakai.
  Pemeriksaan yang hanya bisa di database Enteng: docs/cp7/cp17/R3_INSTALL_TIME_CHECKS.md.
- Pembungkus publik CP4 pool HPP masih bisa dipanggil pengguna login (tanpa penolakan periode tertutup fasad baru);
  dicatat untuk batch pencabutan CP7C bersama FABLE-012.
- Sensus lebar HP 47 menu memakai build demo; layar tersambung diperiksa per uji browser HP.

ATURAN
- Tanpa saling intip (Pro Max §2.2, §16.7): jangan membaca laporan, cabang, run, artifact atau komentar auditor lain dari
  putaran ini sampai laporanmu dikunci dengan commit. Laporan yang sudah terkunci sebelum putaran ini (ketiga laporan r2)
  boleh dibaca; audit silang penulis ada di CROSS_AUDIT.md.
- Label asal-bukti per klaim (§2.9). Baca status per kasus dari log atau artifact, bukan warna job (§2.10). Rerun paling
  banyak sekali dan hanya bila job mati sebelum kasus berjalan (§1.9).
- Dispatch workflow writer hanya dengan ref claude/new-session-deapao dan catat head_sha yang terpakai; bila head sudah
  bergeser, buktikan tree produk sama sebelum memakai hasilnya (§1.7, §2.8, §16.1).
- Jangan percaya klaim penulis begitu saja: susun oracle sendiri dari kontrak dan keputusan owner (D14-2..D16-5).
  Pertanyaan yang sudah dijawab owner tidak ditulis ulang sebagai terbuka (§2.12).
- Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only), production. Jangan meminta password, token atau kunci di chat.
- Panduan: docs/AUDIT_PANDUAN_PRO_MAX.md (SHA-256 5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639,
  sama dengan putaran sebelumnya). Bila ada beda, berkas di repo yang berlaku.

LAPORAN
- Satu cabang audit baru, usul: audit/fable-cp1-7-r3-b53b5acd-<tanggal>, dikunci dengan commit sebelum membaca laporan
  auditor lain di putaran ini:
  1. audit/fable_cp17_r3/RETEST_FABLE_b53b5acd.md — per temuan dan per oracle D16-1: DITUTUP / MASIH TERBUKA / BARU,
     dengan bukti;
  2. audit/fable_cp17_r3/FINDINGS.json — temuan baru per akar masalah, tingkat, bukti; daftar yang harus beres sebelum
     pemasangan ke Enteng; daftar "belum saya periksa".
- Ringkasan untuk owner ≤ 10 kalimat, bahasa sehari-hari. Owner bukan programmer.
````

# Uji ulang r3 CP1–CP7 — untuk Astra

Owner menyalin **seluruh isi kotak di bawah** ke sesi Astra. Kandidatnya sama untuk Fable, Astra dan Sol.
Rincian: `README.md` di folder ini. Kotak belum boleh dikirim selama masih ada tanda `<...>` (angka receipt diisi penulis sesudah semua run kandidat
selesai).

````text
Kamu Astra, auditor independen. Ini UJI ULANG PUTARAN r3 untuk ERP Garment, repo Hanjay6688/-erp-garment-ux, cabang
writer claude/new-session-deapao. Kamu sudah menguji ulang kandidat r2 2e9d6a46 (audit/astra_cp17_r2/RETEST_ASTRA_2e9d6a46.md,
FINDINGS.json, HANDOFF_OWNER.md, cabang audit/astra-cp1-7-r2-2e9d6a46-20261016, kunci bfa007f6; vonis TAHAN). Penulis
memperbaiki temuan ketiga auditor di putaran r3 dan menerapkan keputusan owner D16-1 sampai D16-5. Fable, Astra dan Sol
menguji ulang kandidat yang sama secara terpisah.
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
gausa sembunyiin" (layar yang disembunyikan di Enteng diselesaikan dan disambungkan; tafsiran dan oracle uji ulang Fable 1–5 dicatat di
sana); D16-2..D16-4 pilihan tarif mandor lama atau baru saat jahit selesai, tombol per PO "pakai tarif baru seterusnya",
hanya Owner/Admin; D16-5 "Tutup Periode" digabung sebagai tab "Tutup Buku" di "Laporan & Tutup Buku", hak lihat dan hak
tutup tetap terpisah, arsip dan riwayat lengkap, tautan lama diarahkan. Keputusan yang sudah disahkan tidak dibuka ulang;
uji dengan oracle-mu sendiri.

YANG DIUJI ULANG (temuanmu → klaim penulis; uji dengan kasusmu sendiri, angka dan hasil yang kamu harapkan tidak diganti)
- ASTRA-R2-02 (S1, nomor PO otomatis tidak bisa lewat 999) → R3-01: auto-po.sql memakai tiga digit sebagai lebar minimum;
  kunci per tanggal, UUID dan atomik tetap. Kasusmu apa adanya (hari kosong, 998 header, lalu 999 dan 1000 dengan roll
  10 → 8 → 6, batas 10 detik): CP17_R3_01_AUTO_PO_NUMBER_999_TO_1000_ASTRA; ditambah 999 kontrol, 1000 terbatas waktu,
  1001 dan 9999 → 10000, penolakan + UUID sama sesudah 1000, dua sesi di batas (CP17_R3_01_*, CP17_RACE_R3_01_*).
- ASTRA-R2-01 (S1, buka ulang PO tetap terkunci sesudah pemakaian barang jadi dibatalkan atau dibalik) → R3-02: po-reopen.sql
  hanya menghitung pemakaian yang masih aktif. Dua kasusmu apa adanya (draf penjualan batal; penyesuaian barang jadi dibalik
  dengan delta akun Native sync_po_hpp_to_gl yang kamu kualifikasi): CP17_R3_02_REOPEN_AFTER_CANCELLED_SALES_DRAFT,
  CP17_R3_02_REOPEN_AFTER_REVERSED_FG_ADJUSTMENT; kontrol: pemakaian aktif tetap menghalangi, pemasukan lain tidak menutupi,
  satu dari dua draf batal tetap menghalangi, buka ulang lalu selesai lagi memberi stok dan HPP sama, dua tab sekali.
- ASTRA-C17-07 sisa (S2, layar pool HPP absensi) → R3-04: "Pool HPP absensi" di HPP & Rekalkulasi lewat penulis Native
  (scripts/cp7-src/hpp-pool/pool.sql, src/AttendanceHppPoolPanel.tsx): CP17_R3_04_HPP_POOL_* (10 Native), 3 race, 2 HTTP,
  browser desktop + HP (batal → koreksi sumber di Master Data → Mandor → pool pengganti; KEUANGAN tanpa bagian pool).
- Batas klaim §5 (37 workflow CP6 lama) → R3-08: penulis tidak mengklaim regresi arsip lengkap; pemetaan kasus pengganti
  per workflow di R3_08_CP6_WORKFLOW_SUCCESSORS.md/.json.
- ASTRA-C17-06 (G01/T2) sudah kamu tutup; hasil workflow CP6 lama pada kandidat ada di README.md bagian Kandidat.

JUGA PERIKSA (fitur baru r3 yang bukan temuanmu, dan regresi di sekitarnya)
- D16-1 (oracle uji ulang Fable 1–5): tidak ada menu tersembunyi di Enteng; lima layar baru membaca data nyata (Reminder,
  Pengaturan ERP, Audit Trail, Riwayat Pelanggan, Ringkasan Gudang); semua kasus browser CP17 berjalan lagi di build mode
  Enteng (id _ENTENG); rantai lewat layar CP17_BROWSER_R3_03_CHAIN_* dan CP17_BROWSER_R3_03_GUARDS_REFUSE.
- R3-09 pilihan tarif mandor lama/baru (D16-2..D16-4; R3_09_RATE_CHOICE_DESIGN.md), D16-5 tab Tutup Buku, R3-05 uji layar
  QC & Final SKU dan potongan nota aksesori ke payroll.
- Layar kasbon: penulis menemukan saat kualifikasi bahwa penolakan kasbon diberi tambahan palsu "Refetch authoritative
  gagal" dan memperbaikinya (src/PayrollKasbonPanel.tsx, uji DOM; README.md).
- Bahwa penjaga lama tidak dilonggarkan: kas per tanggal ekonomi dan buku (D14-3, D15-1), bayar upah tidak mendahului akrual
  (D14-2), lantai cutover (D15-5), kebijakan HPP, dan delta Native yang dideklarasikan hanya berlaku di dalam perintahnya.

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
- Satu cabang audit baru, usul: audit/astra-cp1-7-r3-b53b5acd-<tanggal>, dikunci dengan commit sebelum membaca laporan
  auditor lain di putaran ini:
  1. audit/astra_cp17_r3/RETEST_ASTRA_b53b5acd.md — per temuan dan per oracle D16-1: DITUTUP / MASIH TERBUKA / BARU,
     dengan bukti;
  2. audit/astra_cp17_r3/FINDINGS.json — temuan baru per akar masalah, tingkat, bukti; daftar yang harus beres sebelum
     pemasangan ke Enteng; daftar "belum saya periksa".
- Ringkasan untuk owner ≤ 10 kalimat, bahasa sehari-hari. Owner bukan programmer.
````

# Uji ulang r2 CP1–CP7 — untuk Sol

Owner menyalin **seluruh isi kotak di bawah** ke sesi Sol. Kandidatnya sama untuk Fable, Astra dan Sol.
Rincian: `README.md` di folder ini.

````text
Kamu Sol, auditor independen. Ini UJI ULANG PUTARAN r2 untuk ERP Garment, repo Hanjay6688/-erp-garment-ux, cabang
writer claude/new-session-deapao. Kamu sudah mengaudit kandidat gabungan dfab13bf (audit/sol_cp17_combined/FINAL_SOL.md, RETEST_SOL_dfab13bf.md, FINDINGS.json, WRITER_HANDOFF.md dan OPEN_BOUNDARIES.json, cabang audit/sol-cp1-7-combined-dfab13bf-20261016, 278a95ce). Penulis memperbaiki
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
- SOL-R1-001 (koreksi pemasukan yang sudah terpakai ditolak pada saldo setengah jalan) → R2-01: koreksi pembayaran
  pelanggan, koreksi lain-lain dan koreksi nota penjualan dinilai pada keadaan akhirnya; penolakan saldo minus sungguhan
  tetap. Contoh-penyangkalmu dengan angkamu: CP17_R2_SPENT_INCOME_CORRECTION_COMMITS, CP17_R2_SPENT_INCOME_NOTE_ONLY_COMMITS,
  CP17_R2_MISC_SPENT_INCOME_CORRECTION_COMMITS, CP17_R2_NOTE_CORRECTION_SPENT_PAYMENT_COMMITS; kontrol
  CP17_R2_SPENT_INCOME_GENUINE_NEGATIVE_REFUSED; HTTP CP17_HTTP_R2_SPENT_INCOME_*; race
  CP17_RACE_R2_CORRECTION_AND_PAYMENT_ONE_BANK; lingkup majemuk tertutup CP17_R2_COMPOUND_SCOPE_PRIVATE_AND_CLOSED.
- SOL-R1-002 (PO harian tidak bisa dibuat) → R2-04, owner D15-6 pilihan A: Buat Potongan membuat PO otomatis saat
  disahkan, satu transaksi dengan posting (scripts/cp7-src/cutting-correction/auto-po.sql). Penerimaanmu: mulai tanpa PO
  aktif, buat lewat layar, lanjut sampai jahit: CP17_R2_D15_6_* (satu transaksi, UUID sama, gagal di tengah tanpa PO/stok/
  nomor terpakai, draf tanpa efek, hak akses, lanjut Bagi Potongan dan jahit), race roll sama dan UUID sama, HTTP,
  browser desktop dan HP. Nomor ganda: nomor berikutnya per hari potong (WIB) di bawah kunci. Saat kualifikasi penulis
  menemukan layar Buat Potongan terkunci sesudah posting mode "PO yang sudah ada" dan memperbaikinya (3b7cf370;
  CROSS_AUDIT.md §7).
- SOL-R1-003 (pre-U finished() pada rantai yang berhenti sebelum U) → R2-08: finished() mencatat
  NOT_APPLICABLE_STOPPED_BEFORE_U bila rantai berhenti sebelum U dan tetap mewajibkan daftar sesudah U
  (scripts/cp6_pre_u_inventory.py, commit e3e12ea7). G01, T2 dan 37 workflow CP6 lama: hasil per workflow di README.md
  bagian Kandidat dan CI_RECEIPT.json.
- SOL-R1-004 / SOL-R1-005 (QC 669 px, HPP 627 px di HP 390 px) → R2-09: tata letak diperbaiki tanpa menyembunyikan isi;
  sensus 48 menu build demo (scripts/ui_phone_width_census.mjs, rumus scrollWidth <= innerWidth; build sebelum perbaikan
  gagal tepat di dua menu itu), workflow "UI phone width census".
- KNOWN-UI-MODE → R2-02 (D15-2): src/screenActivation.ts; SCREEN_MAP.md.
- KNOWN-DAILY-MASTER → R2-03 (D15-3): enam layar Master Data + tarif upah mandor.
- BROWSER-CHAIN → R2-07: dua rantai browser yang hanya memakai layar (README.md).
- KNOWN-BF-WAVE (S1) → R2-10: RECORD_WAVE mencatat jahit selesai per SKU wave dalam satu transaksi; per SKU satu work
  completion pada snapshot Native SKU itu; sisa per SKU = potongan di ukurannya dikurangi yang sudah selesai/terutang per
  komponen; pratinjau tarif per SKU pada waktu jahit (sewing_wave_at, dibandingkan dengan penulis Native pada empat
  waktu); jalur dasar menolak potongan wave (CP7_SEWING_WAVE_PER_SKU). sewing.sql, src/SewingCompletionPanel.tsx;
  CP17_R2_10_* (upah per SKU, pratinjau = Native, penolakan tetap, gagal di tengah, batal satu SKU), race, HTTP, browser.
- Perbarui OPEN_BOUNDARIES.json-mu: batas mana yang tertutup, mana yang masih terbuka.

JUGA PERIKSA (fitur baru r2 yang bukan temuanmu, dan regresi di sekitarnya)
- R2-05 / D15-4 tombol buka ulang PO dan panel selesai PO yang mengikuti Native (finish.sql, po-reopen.sql).
- R2-06 seri lusin penjualan (merek + SKU) dan D15-5 lantai tanggal cutover (cutover.sql; CP17_R2_D15_5_*).
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
- Satu cabang audit baru, usul: audit/sol-cp1-7-r2-2e9d6a46-<tanggal>, dikunci dengan commit sebelum membaca laporan
  auditor lain di putaran ini:
  1. audit/sol_cp17_r2/RETEST_SOL_2e9d6a46.md — per temuanmu: DITUTUP / MASIH TERBUKA / BARU, dengan bukti;
  2. audit/sol_cp17_r2/FINDINGS.json — temuan baru per akar masalah (fitur baru r2 dan regresi), tingkat, bukti;
     daftar yang harus beres sebelum pemasangan ke Enteng; daftar "belum saya periksa".
- Ringkasan untuk owner ≤ 10 kalimat, bahasa sehari-hari. Owner bukan programmer.
````

# Handoff audit akhir CP1–CP7 (sambungan dan layar) — untuk Astra

**DRAF. Jangan dikirim sebelum `README.md` di folder ini bertuliskan "SIAP DIKIRIM".** Owner menyalin **seluruh isi
kotak di bawah** ke sesi Astra. Kandidat dan isi kotaknya sama untuk Fable, Astra dan Sol.

````text
Kamu Astra, auditor independen. Ini AUDIT AKHIR CP1–CP7 ERP Garment (keputusan owner D14-13, 15 Okt 2026), sesudah
audit penuh 0b7049d9 dan uji ulang perbaikan r1. Repo Hanjay6688/-erp-garment-ux, cabang writer
claude/new-session-deapao. Fable dan Sol mengaudit kandidat yang sama secara terpisah.

KANDIDAT
- Commit 66baa8e8ddf601625bc831c7256f38eec883b496, tree 3587d97afbef0350271cce51f2e77db5b8a3ff59. Commit sesudahnya di
  cabang writer hanya dokumen; buktikan sendiri dengan git diff --name-only <kandidat> origin/claude/new-session-deapao.
  Catat tree produk sebelum dan sesudah auditmu (Pro Max §2.8).
- Paket: docs/cp7/audit-candidate/cp1-7-final-integration-20261015/ (README.md, CHAIN_MAP.md, SCREEN_MAP.md).
  Isinya titik awal dari penulis, bukan bukti lulus.

DUA FOKUS (kata owner, persis: "interkonkesi hubungan dengan ux semuanya")
1. Sambungan antar tahap dari awal sampai akhir: pembelian → stok → potong → bagi potongan → jahit → laundry → QC →
   barang jadi → jual → kas, hutang, piutang, buku besar, laporan; plus rantai samping (hutang supplier, retur
   supplier, payroll/absensi/kasbon, Nota Ambil Aksesori, BS/rework, hitung fisik, saldo awal). Untuk tiap sambungan:
   apakah bisa dijalankan lewat APLIKASI (layar → RPC public → penulis Native), apakah angka stok, WIP, HPP, hutang,
   piutang, kas dan buku besar tetap cocok sesudahnya, dan apakah ada uji yang benar-benar melewatinya. CHAIN_MAP.md
   §1–2 memetakan 13 sambungan utama dan 7 rantai samping.
2. Setiap layar UX demo dibandingkan dengan layar tersambungnya, di mode DISPOSABLE_TEST dan mode Enteng
   (UAT_AUTH_SIMULATION): data asli atau contoh, alur, isian, hitungan, pesan tolak, tampilan HP. SCREEN_MAP.md §1
   memetakan 48 menu × 3 mode. Contoh perilaku demo yang sempat tidak ikut ke layar tersambung: bagi lusin per seri
   (D14-5).

YANG SUDAH DIKETAHUI PENULIS (uji sendiri; jangan dianggap benar atau salah tanpa bukti)
- Jahit selesai tidak bisa dicatat dari layar tersambung (public.erp_record_sewing_terminal_v1 ada, tidak dipanggil
  dari src/); upah borongan (erp.post_work_completion) dan HPP final (erp.finish_production_order) tanpa jalan dari
  aplikasi.
- Mode Enteng menampilkan data contoh di 23 dari 48 menu (semua Penjualan, 6 Keuangan, Absensi, master data, admin);
  rencana menyalakannya belum tertulis.
- Data induk harian tidak punya layar tersambung.
- Sekitar 60 workflow cp7-* hanya berjalan di cp7/integration dan basi sejak 8 Okt (sebelum penjaga D14-2/D14-3/FIN02);
  penulis menjalankannya ulang sebelum paket ini dikirim (lihat README "Sebelum dikirim").
- Butir terbuka lama: CHAIN_MAP.md §4.

ATURAN
- Tanpa saling intip (Pro Max §2.2, §16.7): jangan membaca laporan, cabang, run, artifact atau komentar auditor lain
  dari putaran ini sampai laporanmu dikunci dengan commit.
- Label asal-bukti per klaim (§2.9). Baca status per kasus dari log atau artifact, bukan warna job (§2.10). Rerun
  paling banyak sekali dan hanya bila job mati sebelum kasus berjalan (§1.9).
- Dispatch workflow writer hanya dengan ref claude/new-session-deapao dan catat head_sha yang terpakai; bila head
  sudah bergeser, buktikan tree produk sama sebelum memakai hasilnya (§1.7, §2.8, §16.1).
- Susun oracle sendiri dari kontrak dan keputusan owner (sampai D14-13, docs/cp7/OWNER_DECISIONS_20261008.md).
  Keputusan owner yang sudah disahkan tidak dibuka ulang (§2.12).
- Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only), production. Mode Enteng diuji dengan build lokal + backend sekali pakai atau HTTP
  tiruan. Jangan meminta password, token atau kunci di chat.
- Panduan: docs/AUDIT_PANDUAN_PRO_MAX.md (SHA-256 5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639).
  Bila ada beda, berkas di repo yang berlaku.

LAPORAN
- Cabang audit baru, usul: audit/astra-cp1-7-final-<kandidat8>-<tanggal>, berkas
  audit/astra_cp17_final/FINAL_ASTRA.md (+ FINDINGS.json).
- Isi: vonis per sambungan B1–B13 dan S1–S7 (TERSAMBUNG DAN TERUJI / TERSAMBUNG TANPA UJI APLIKASI / TIDAK
  TERSAMBUNG); vonis per menu (SAMA / BEDA / TIDAK ADA LAYAR TERSAMBUNG) untuk DISPOSABLE_TEST dan mode Enteng;
  daftar yang harus beres sebelum pemasangan ke Enteng; temuan per akar masalah dengan bukti; daftar "belum saya
  periksa".
- Ringkasan untuk owner ≤ 10 kalimat, bahasa sehari-hari. Owner bukan programmer.
````

# Paket gabungan CP1–CP7: uji ulang r1 + audit akhir — untuk Fable

Owner menyalin **seluruh isi kotak di bawah** ke sesi Fable. Kandidatnya sama untuk Fable, Astra dan Sol
(keputusan owner D14-16: satu paket gabungan, satu kandidat). Rincian: `README.md` di folder ini.

````text
Kamu Fable, auditor independen. Ini PAKET GABUNGAN untuk ERP Garment (keputusan owner D14-16, 15 Okt 2026), repo
Hanjay6688/-erp-garment-ux, cabang writer claude/new-session-deapao. Satu kandidat untuk dua bagian:
(A) UJI ULANG perbaikan penulis atas temuanmu di audit penuh CP1–CP7 (audit/fable_cp17/AUDIT_FABLE_0b7049d9.md v1.0 + addendum A1–A3, cabang audit/fable-cp1-7-0b7049d9-20261014);
(B) AUDIT AKHIR CP1–CP7 (D14-13): sambungan antar tahap dan layar demo vs layar tersambung.
Astra dan Sol mengaudit kandidat yang sama secara terpisah. Kandidat uji ulang 66baa8e8 sempat disiapkan tetapi tidak
pernah dikirim (D14-16); kandidat di bawah menggantikannya.

KANDIDAT
- Commit dfab13bf62398a69a02bf6221c06d29075e5e40b, tree 886f83312958b53781a450a4ea2a8fb2147b3be3. Basis audit penuhmu: 0b7049d9 (tree ce6aed0a). Commit sesudahnya di cabang writer
  hanya dokumen; buktikan: git diff --name-only dfab13bf62398a69a02bf6221c06d29075e5e40b origin/claude/new-session-deapao. Catat tree produk sebelum
  dan sesudah auditmu (Pro Max §2.8).
- supabase/ tidak berubah sejak 0b7049d9 (buktikan: git diff --name-only 0b7049d9 dfab13bf62398a69a02bf6221c06d29075e5e40b -- supabase kosong).
  Perubahan produk ada di scripts/cp7-src/ (lapisan CP7 + delta Native yang dideklarasikan) dan src/.
- Bukti penulis: docs/cp7/audit-candidate/cp1-7-final-integration-20261015/CI_RECEIPT.json (semua 80 run workflow
  dan 131 job pada kandidat; satu run dibatalkan antrean dan satu run diulang sekali, alasannya di README.md
  bagian Kandidat), docs/cp7/cp17/CP17_FIXES.json (61 kasus yang dideklarasikan sebelum dijalankan; workflow
  "CP7 CP17 Fixes").
- Paket: docs/cp7/audit-candidate/cp1-7-final-integration-20261015/ (README.md, CHAIN_MAP.md, SCREEN_MAP.md,
  GAPS_D14_14.md) dan docs/cp7/audit-candidate/cp1-7-fix-r1-20261015/ (README.md per temuan, FINDINGS_TRACKER.md
  bagian G dan H, dokumen desain). Isinya titik awal dari penulis, bukan bukti lulus. CI_RECEIPT.json di folder r1
  milik 66baa8e8 (riwayat).

YANG BERUBAH SESUDAH 66baa8e8 (git diff 66baa8e8 dfab13bf62398a69a02bf6221c06d29075e5e40b -- src scripts supabase tests .github)
- G1 (D14-14) selesai jahit + upah borongan dari layar WIP & Sewing: satu perintah server memanggil penulis Native
  yang sudah ada (kunci tarif PO, work completion POSTED → jurnal WIP / hutang mandor, catatan SELESAI_DIJAHIT yang
  dihitung laundry sebagai siap kirim); batal hanya selama potongan masih di mandor dan upah belum masuk payroll.
  Sebelum catatan pertama layar menampilkan perkiraan upah dari tarif yang akan dikunci. scripts/cp7-src/
  cutting-correction/sewing.sql, src/SewingCompletionPanel.tsx, src/sewingCompletionContract.ts; kasus
  CP17_G1_SEWING_*, CP17_RACE_G1_SEWING_TWO_TABS_ONE_WINS, CP17_HTTP_G1_SEWING_RECORD, browser
  CP17_BROWSER_G1_SEWING_DESKTOP dan _MOBILE.
- G2 (D14-14) selesaikan PO + HPP final dari layar HPP & Rekalkulasi: perintah server hanya memanggil
  erp.finish_production_order dan menolak kecuali PO berakhir FINISHED dengan saldo WIP nol. Tidak ada pembalik
  Native untuk PO selesai; tanggal selesai selalu hari ini WIB. scripts/cp7-src/cutting-correction/finish.sql,
  src/PoFinishPanel.tsx, src/poFinishContract.ts; kasus CP17_G2_FINISH_*, CP17_RACE_G2_FINISH_TWO_TABS_ONE_WINS,
  CP17_HTTP_G2_FINISH_PO, browser CP17_BROWSER_G2_FINISH_DESKTOP dan _MOBILE.
- G3 (D14-14): 51 workflow cp7-* yang basi sejak 8 Okt dijalankan ulang; 3 data uji lama dibetulkan (modal bank uji,
  daftar 37 peran) tanpa melonggarkan penjaga; log gagal disimpan di run aslinya (GAPS_D14_14.md §3).
- D14-17 alat uji, bukan produk: arsip CI 10392910720 (daftar tabel "sebelum U") terhapus otomatis 15 Okt;
  scripts/cp6_pre_u_inventory.py mengambil ulang daftar itu dengan fungsi beku yang sama tepat sebelum langkah beku
  U (juga di rantai database bagian browser paket rilis T3); langkah X tidak diubah. Batasnya ditulis di GAPS_D14_14.md §3a; periksa bahwa tidak ada yang dilonggarkan.

BAGIAN A — UJI ULANG r1
Keputusan owner D14-2..D14-17 tercatat persis di docs/cp7/OWNER_DECISIONS_20261008.md. Uji bagian di bawah dengan
oracle-mu sendiri.
Bagian yang berubah di putaran r1 (sesudah 55d72775):
Utama (dari temuanmu atau yang menyentuh temuanmu):
- Dua perbaikan alat uji saat kualifikasi (bukan produk): scripts/cp7_catalog_state.py membaca entri D14-8 (pasangan sama + owner harus cocok; run F03 38668243786 gagal sebelum itu) dan scripts/cp6_av_runtime.py refuse_post_use mengulang hanya penolakan PACKAGE_REQUIRES_CLOSED_DRAINED_DATABASE seperti change() (run AV 38670698254 gagal sebelum itu). Ketiga: tests/cp7/families/f05-timeline.test.ts memberi batas 180 detik hanya untuk proses pembanding sekali pakai (fungsi pendahulu yang dibandingkan bersifat kuadratik; fungsi produk 0,3 detik; run Shell S0 38673762153 gagal sebelum itu), seperti P19 di ce455269. Periksa bahwa tidak ada yang dilonggarkan.
- D14-8 pembanding skema public (A2): urutan stabil (kolasi "C"), semua anggota dan duplikat, definisi, owner dan hak akses dibandingkan; query lama disimpan untuk bukti. A2_COMPARATOR_D14_8.md, scripts/cp6_auditor_runner.py (PUBLIC_STATE), bukti sebelum/sesudah scripts/cp6_auditor_public_state_test.py (langkah sendiri di workflow CP17). Akar dua kegagalan A2 lama tetap OPEN (D13-10).
- D14-9 FABLE-012: pencabutan EXECUTE 82 penulis erp ditunda ke CP7C sebagai pekerjaan keamanan terbuka; gerbang exposure_gate (scripts/cp7_access_inventory.py) menolak CP7_FABLE012_REVOKE_BEFORE_EXPOSING_ERP bila erp akan terjangkau Data API (dinyatakan, extra search path, atau penimpaan tersimpan di peran authenticator) sebelum pencabutan. FABLE012_D14_9_GATE.md; kasus CP17_FABLE012_EXPOSURE_GATE_REVOKE_FIRST.
- D14-10 batal/betulkan kain kembali (SG-02): satu transaksi — jurnal kain kembali dibalik lewat erp.reverse_journal Native, gerakan REVERSAL per gerakan kembali, hitung ulang biaya bahan (+ antrean HPP bila ada barang jadi), fakta kembali dikosongkan, pembetulan langsung diposting lagi; riwayat asli tetap; pemakaian sesudahnya disebut dan menghalangi. SG02_FABRIC_RETURN.md bagian D14-10, scripts/cp7-src/cutting-correction/return.sql, src/CuttingFabricReturnReversalPanel.tsx; kasus CP17_SG02_CANCEL_*, CP17_SG02_CORRECT_RETURN_ONE_TRANSACTION, browser CP17_BROWSER_SG02_FABRIC_RETURN_CORRECT_DESKTOP. Batas: dicatat pada saat disimpan (seperti pembalik Native), hari-hari di antaranya tetap menunjukkan angka lama.
- D14-11 upah rework untuk bagian yang selesai walau kasus BS OPEN/PARTIAL (RWK01): baris pekerjaan rework dengan order COMPLETED dan biaya terposting bisa masuk Nota; yang belum selesai ditahan; dibayar sekali, tidak muncul lagi saat kasus ditutup. RWK01_D14_11.md, scripts/cp7_rework_eligibility_bundle.py; kasus CP17_RWK01_OPEN_CASE_FINISHED_PART_PAID_ONCE.
Juga periksa bila sempat:
- D14-5 lusin per seri di draf penjualan tersambung (Sol SALES_MANUAL_13): satu pilih menambah semua ukuran SKU itu yang ada stoknya, seri baru mulai 1 lusin dibagi rata; ketik manual 3/5/4 terbaca "1 lusin"; SKU satu ukuran: 1 lusin = 12 di ukuran itu (seperti UX demo). src/SalesDraftPanel.tsx, src/sales/seriesDozens.ts; browser CP17_BROWSER_D14_5_SERIES_DOZENS_DESKTOP dan _MOBILE (Auth dan PostgREST nyata, fixture stok 3 ukuran dan 1 ukuran). Sesudah f1a1ae69 hanya tampilan seri ini yang berubah (D14-12, owner "ya": ringkas seperti demo): ukuran satu seri berdampingan juga di HP, satu baris harga/potongan/catatan per ukuran, bantuan lusin + PCS per seri dalam satu blok yang bisa dibuka; label isian dan tombol tetap; browser D14-5 kini juga memeriksa tiga ukuran satu baris (git diff f1a1ae69 66baa8e8 -- src scripts).

YANG DIUJI ULANG (temuanmu → klaim penulis)
- FABLE-001 bayar upah sebelum utangnya ada → ditolak (D14-2), kasbon jalur sendiri. Kasus CP17_FIN01_*.
- FABLE-002/003/004 dan A1 (dokumen, salinan paket, bukti CP1/CP2, 4 tabel tanpa RLS) → README tabel R-DOC.
- FABLE-005 → pemetaan 75 C6 + 22 ALL milik Astra (C6_75_ALL22_CROSSWALK, d4a83b42); tidak ada kode baru.
- FABLE-006 rework sesudah SCRAP → upah yang sudah diakui bisa masuk Nota sekali. Kasus CP17_RWK01_*.
- FABLE-007 (dugaan absensi dobel) → tidak ada perubahan produk. Penjaganya ada di skema dasar, bukan di migrasi pohon
  ini: erp.guard_payroll_period_overlap (supabase/tests/fixtures/erp_enteng_cp45a_catalog_bootstrap.sql.gz baris
  10325-10342) mengunci per mandor lalu menolak payroll aktif kedua yang periodenya bertumpuk. Regresi
  CP17_RACE_OVERLAPPING_PAYROLL_ONE_WINS: payroll kedua di atas hari absensi ditolak; dua payroll bertumpuk dikirim
  bersamaan, satu lolos.
- FABLE-008 klaim laundry bertanggal mundur → ditolak. Kasus CP17_FIN02_*.
- FABLE-009 pickup POSTED tanpa koreksi → batal Bagi Potongan sebelum dijahit (SG01_PICKUP_REVERSAL.md); dua delta
  Native dideklarasikan dan dipulihkan persis saat uninstall. Kasus CP17_SG01_* + browser desktop.
- FABLE-010 sisa kain → kain kembali ke gudang (D14-4, SG02_FABRIC_RETURN.md). Kasus CP17_SG02_* + browser HP.
- FABLE-011 → tidak diubah (bergantung keputusan owner).
- FABLE-012 hak EXECUTE authenticated ke erp → inventaris + bukti 82 penulis tidak terjangkau dari Data API
  (CP17_HTTP_ERP_WRITERS_NOT_REACHABLE). Pencabutan EXECUTE ditunda ke CP7C dengan gerbang (D14-9, di atas). Owner mengizinkan kamu membaca
  setelan API hosted (D14-7): baca saja, tanpa mengubah apa pun.
Juga periksa regresi di sekitar perubahan: kas per tanggal (D14-3) untuk semua pengeluaran, kasbon (D14-6), kartu
stok sesudah REOPEN/POST ulang (Astra STK01), kebijakan HPP (Astra HPP01), dan bahwa delta Native yang baru tidak
melonggarkan penjaga lama.

BAGIAN B — AUDIT AKHIR
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
- Jahit selesai, upah borongan dan HPP final sekarang punya jalan dari aplikasi (G1, G2 di atas). Batasnya: potongan
  dengan tarif per SKU/ukuran (wave BF) ditolak WAVE_SKU_RATES; erp.post_work_completion masih bisa dieksekusi
  authenticated lewat SQL (FABLE-012, ditunda ke CP7C, D14-9) tetapi tidak terjangkau lewat Data API.
- Mode Enteng menampilkan data contoh di 23 dari 48 menu (semua Penjualan, 6 Keuangan, Absensi, master data,
  admin); rencana menyalakannya belum tertulis.
- Data induk harian tidak punya layar tersambung.
- Butir terbuka lama: CHAIN_MAP.md §4.

ATURAN
- Tanpa saling intip (Pro Max §2.2, §16.7): jangan membaca laporan, cabang, run, artifact atau komentar auditor lain
  dari putaran ini sampai laporanmu dikunci dengan commit. Laporan yang sudah terkunci sebelum putaran ini
  (ketiga audit penuh atas 0b7049d9 dan addendumnya) boleh dibaca.
- Label asal-bukti per klaim (§2.9). Baca status per kasus dari log atau artifact, bukan warna job (§2.10). Rerun
  paling banyak sekali dan hanya bila job mati sebelum kasus berjalan (§1.9).
- Dispatch workflow writer hanya dengan ref claude/new-session-deapao dan catat head_sha yang terpakai; bila head
  sudah bergeser, buktikan tree produk sama sebelum memakai hasilnya (§1.7, §2.8, §16.1).
- Jangan percaya klaim penulis begitu saja: susun oracle sendiri dari kontrak dan keputusan owner (D14-2..D14-17).
  Keputusan owner yang sudah disahkan tidak dibuka ulang; pertanyaan yang sudah dijawab tidak ditulis ulang sebagai
  terbuka (§2.12).
- Tidak boleh dimutasi: main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only), production. Jangan meminta password, token atau kunci di chat.
- Panduan: docs/AUDIT_PANDUAN_PRO_MAX.md (SHA-256 5752e96df751de5ebe4b86d3f572cffa1bbe94eb42bf8e283fa6e04f9f593639,
  sama dengan saat audit penuh). Bila ada beda, berkas di repo yang berlaku.

LAPORAN
- Satu cabang audit baru, usul: audit/fable-cp1-7-combined-dfab13bf-<tanggal>, dua berkas yang dikunci dengan commit
  sebelum membaca laporan auditor lain di putaran ini:
  1. audit/fable_cp17_combined/RETEST_FABLE_dfab13bf.md — bagian A, per temuan: DITUTUP / MASIH TERBUKA / BARU,
     dengan bukti.
  2. audit/fable_cp17_combined/FINAL_FABLE.md (+ FINDINGS.json) — bagian B: vonis per sambungan B1–B13 dan
     S1–S7 (TERSAMBUNG DAN TERUJI / TERSAMBUNG TANPA UJI APLIKASI / TIDAK TERSAMBUNG); vonis per menu (SAMA / BEDA /
     TIDAK ADA LAYAR TERSAMBUNG) untuk DISPOSABLE_TEST dan mode Enteng; daftar yang harus beres sebelum pemasangan ke
     Enteng; temuan per akar masalah dengan bukti; daftar "belum saya periksa".
- Ringkasan untuk owner ≤ 10 kalimat, bahasa sehari-hari. Owner bukan programmer.
````

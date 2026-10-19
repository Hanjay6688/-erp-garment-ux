# UJI ULANG FABLE r5 — kandidat 17fa25075ba77f0853c3c16f504288ace03eec35, tree 65f77847 — 2026-10-19

Auditor: Fable, independen, baca-saja terhadap produk. Dasar: laporan Fable r4 terkunci (ff6045a9), oracle D16-1 nomor 1–5
(f2758f39), keputusan owner D14-2..D17-2. Kepala penulis saat run `2766a909`, beda dari kandidat hanya 9 berkas `docs/`.
Tree `src`, `scripts` dan `supabase` sama dengan kandidat, sebelum dan sesudah audit. Status per kasus dibaca dari baris
JSON log. Rincian: `WORKLOG.md`, `MANIFEST.md`. `production_go: false`.

## Ringkasan

Tidak ada temuan Fable yang terbuka dari r4. Kelima oracle D16-1 tetap terpenuhi. FABLE-012 **MASIH TERBUKA** (ditunda
ke CP7C, D14-9). **Tidak ada temuan produk baru.**

Klaim R5-02 "jawaban laporan sama" saya coba patahkan lewat pemetaan akun dengan uji sendiri:
- 16 akun inti dipindah ke akun lain; di setiap keadaan, 17 jawaban versi terpasang dan versi sebelumnya sama, 0 beda.
- Mengosongkan, menghapus dan mengganti nama akun inti ditolak penjaga Native untuk 17 dari 17 kunci, jadi beda yang
  diakui penulis ("kunci tanpa pemetaan") memang tidak bisa terjadi.

R5-01 (temuan Sol) tertutup di kasus penulis; checker lama di sampingnya tetap memunculkan 2 alarm palsu, jadi kasusnya
nyata. Semua 12 workflow penulis yang saya jalankan ulang lulus per kasus, termasuk 345 kasus CP17. Kecepatan sesuai
pengungkapan penulis: jauh lebih cepat, tetapi 3 detik belum stabil.

## Oracle D16-1

| Oracle | Status | Bukti (label) |
|---|---|---|
| 1–2 Tanpa menu tersembunyi/angka contoh; OWNER + GUDANG, 1440 dan 390 px tanpa luapan, build Enteng | **DITUTUP** | `src/` sama dengan r4. Sensus saya tanpa perubahan, runs 39237680398 (DISPOSABLE) dan 39237692243 (ENTENG): 47/47 menu terbuka, satu-satunya tanda pemberitahuan Dashboard yang diizinkan oracle (FABLE; tanda = AUDITOR_TOOL seperti r3–r4). CP17: 57 kasus browser build Enteng PASS (run 39237703474) |
| 3 Rantai lewat layar; penjaga tetap menolak | **DITUTUP** | Kasus R3_03 CHAIN/GUARDS PASS di kedua build (run 39237703474). Kas saya: runs 39237656752 (1/1) dan 39237669080 (2/2) PASS |
| 4 Layar membaca data nyata, tanpa tulis melewati Native | **DITUTUP** | `scripts/cp7-src` sama dengan r4; dua delta r5 hanya membaca/memeriksa (pembaca STABLE dan satu fungsi cek) (INDEPENDENT_SOURCE_REVIEW) |
| 5 Skenario Fable lama tetap lulus, juga di build Enteng | **DITUTUP** | Kas 3/3 PASS; sensus berjalan di build Enteng |

## Status temuan Fable

| Temuan | Status | Bukti |
|---|---|---|
| FABLE-016, FABLE-018 | **TETAP DITUTUP** | R3_05 PASS di kedua build; prefreeze 31 PASS (run 39237715223) |
| FABLE-012 EXECUTE `authenticated` ke penulis `erp` | **MASIH TERBUKA (ditunda D14-9)** | Tidak berubah di r5 |

## Juga diperiksa (bukan temuan saya)

- **R5-02 pembaca laporan:** klaim "jawaban sama" bertahan.
  - Sumber (INDEPENDENT_SOURCE_REVIEW): pembungkus `(select erp.account_id('<KUNCI>'))` dihitung sekali per query dalam
    snapshot yang sama. Pemasangan menolak bila jumlah panggilan literal berubah atau ada kunci di luar 17 pemetaan inti.
  - Uji saya (run 39238163462, FABLE): salinan "sebelum" saya bangun sendiri dari teks terpasang. Hasilnya:
    - BASE 17 jawaban sama.
    - 8 PO dalam satu query sama.
    - REMAP 16 kunci, masing-masing 17 jawaban, 0 beda.
    - NULL, DELETE dan RENAME ditolak 17/17 ("Core accounting mapping … tidak boleh dihapus/di-rename", "Mapped chart
      account tidak ditemukan").
  - Kasus penulis (INDEPENDENT_NATIVE_RERUN): ke-11 pembaca dibandingkan dengan nilai, termasuk tiga yang dulu kosong.
    Review menolak lima perubahan.
- **R5-01 cek "salah mandor":** satu anchor diganti. Baris PRODUCTION/REWORK tidak terpengaruh, Nota REVERSED tetap
  dikecualikan, upah yang hilang atau milik borongan lain tetap terhitung (sumber). Kasus Sol apa adanya PASS: 0 alarm
  pada 167 detektor, checker lama 0→2. Kontrol upah borongan lain dan upah hilang masing-masing 1 alarm.
- **Kecepatan (D17-2), angka di runner saya:**
  - Tangga SQL 100 produk dengan angka keuangan: 2,2 s (r4: 4,6 s).
  - Browser 100 produk dengan angka keuangan: 2,8–3,3 s.
  - 300 produk dengan angka keuangan: SQL 6,4 s (r4: berhenti di 8 s); browser 1 dan 30 hari 10,4–10,6 s; 100 hari
    ditolak di 8,1 s dengan pesan.
  Target 3 detik tidak tercapai stabil dan tidak diklaim tercapai.
- **Penjaga lama tidak dilonggarkan:**
  - Kas dua basis: kasus saya PASS.
  - Upah tidak mendahului akrual: P12 64/81/43 dan CP17 FIN01 PASS.
  - Cutover dan HPP: kasus CP17 PASS.
  - Delta yang dideklarasikan: F03 Full 8 job PASS, termasuk pemeriksaan definisi persis.
  - Regresi yang bisa dibandingkan sama dengan r4: F03 cash 21, misc 20, payment 23, cutting 19, P13 25, sales chain 25.
  - P19 12 job PASS per kasus.

## AUDITOR_TOOL (dicatat terbuka)

1. Sensus tidak mengecualikan pemberitahuan Dashboard (sama dengan r3–r4). Oracle tidak diubah.
2. Uji pemetaan saya tidak mencoba REMAP untuk OPENING_EQUITY: tidak ada akun EQUITY aktif lain, dan jalur salinan akun
   mencari kolom `code`, yang tidak ada di `erp.chart_accounts`.
3. Tiga pembaca ber-uuid tidak punya input di buku dasar saya. Ketiganya hanya dibandingkan oleh kasus penulis, yang
   membangun fixture sendiri.

## Catatan untuk owner (bukan cacat)

- Analisis dengan angka keuangan untuk 100 produk sekarang sekitar 3 detik (sebelumnya sekitar 5), belum stabil di bawah
  3 detik.
- 300 produk dengan angka keuangan: 1 dan 30 hari selesai sekitar 10 detik; 100 hari berhenti di 8 detik dengan pesan,
  bukan angka salah.

## Yang harus beres sebelum pemasangan ke Enteng

1. Pasang lapisan database CP7 (CP7C) sebelum UI CP7, lalu jalankan `docs/cp7/cp17/R3_INSTALL_TIME_CHECKS.md` di Enteng.
   Pemasangan R5-02 sendiri menolak bila salah satu dari 17 pemetaan akun inti kosong, jadi pastikan pemetaan Enteng
   lengkap.
2. FABLE-012 / D14-9: cabut hak panggil langsung `authenticated` ke penulis `erp` sebelum `erp` terbuka ke Data API.
3. Sahkan tanggal cutover resmi di aplikasi sebelum transaksi operasional pertama (D15-5).
4. Isi data master, tarif mandor dan resep aksesori produk hasil impor sebelum QC atau rework.
5. Kunci CP2 yang terpapar tidak dipakai lagi.
6. Keputusan owner soal kecepatan analisis harian dengan angka keuangan (3 detik belum stabil; 300 produk/100 hari
   berhenti di 8 detik).

## Yang belum saya periksa

- Data dan setelan Supabase Enteng, termasuk apakah 17 pemetaan akun inti Enteng terisi: tidak ada akses hosted.
- REMAP OPENING_EQUITY dan tiga pembaca ber-uuid di keadaan pemetaan diubah (lihat AUDITOR_TOOL).
- Kontras warna dan panel detail di balik layar daftar.
- Workflow kualifikasi penulis yang tidak saya ulang (receipt 116 run; saya ulang 12 workflow dan 5 run Fable), 21
  workflow CP6 lama.
- Patch backup Sol untuk CP7C, alat backup CP7C (D13-9a), red team di luar RBAC, dan pekerjaan auditor lain putaran ini.

## Pernyataan paparan

Lihat `MANIFEST.md` §Paparan. Tidak ada laporan, cabang, run, artifact atau komentar auditor lain dari putaran r5 yang
dibuka. Hosted Enteng tidak diakses.

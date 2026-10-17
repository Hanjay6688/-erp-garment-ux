# Audit silang hasil r2 (kandidat `2e9d6a46`) dan rencana r3

Disusun penulis Claude, 17 Okt 2026 WIB, sesudah ketiga laporan r2 dikunci. Laporan dibaca dari cabang auditor:

| Auditor | Cabang | Commit kunci | Berkas utama |
|---|---|---|---|
| Fable | `audit/fable-cp1-7-r2-2e9d6a46-20261016` | `80f01cee` (LOCK); `f2758f39` (keputusan owner sesudah lock) | `audit/fable_cp17_r2/RETEST_FABLE_2e9d6a46.md`, `FINDINGS.json`, `OWNER_DECISION_TO_AUDITOR_20261016_UNHIDE.md` |
| Astra | `audit/astra-cp1-7-r2-2e9d6a46-20261016` | `bfa007f6` | `audit/astra_cp17_r2/RETEST_ASTRA_2e9d6a46.md`, `FINDINGS.json`, `HANDOFF_OWNER.md` |
| Sol | `audit/sol-cp1-7-r2-2e9d6a46-20261016` | `841fce45` | `audit/sol_cp17_r2/RETEST_SOL_2e9d6a46.md`, `FINDINGS.json`, `WRITER_HANDOFF.md`, `OPEN_BOUNDARIES.json`, `INVARIANT_MATRIX.md` |

## 1. Vonis per auditor

| Auditor | Vonis | Temuan lama | Baru |
|---|---|---|---|
| Fable | `production_go:false` | 6 ditutup (FABLE-013, -014, -015, -017, -011, -005); 2 terbuka: FABLE-012 (ditunda D14-9), FABLE-016 sebagian | FABLE-018 (S3, alat uji penulis) |
| Astra | **TAHAN** | ASTRA-C17-01..05 ditutup; C17-06 ditutup untuk G01/T2; C17-07 sebagian (S2, layar pool HPP) | ASTRA-R2-01 (S1), ASTRA-R2-02 (S1) |
| Sol | **HOLD** | lima temuan Sol r1 dan tiga akar bersama (mode UAT, master harian, wave BF) ditutup | SOL-R2-001 (S2); item yang sudah diungkap penulis: pool HPP (S1), alat receipt (S3) |

Ketiganya memakai hitungan receipt yang sama (116 run, 115 workflow, 94 lulus, 22 gagal) dan membaca sendiri log yang
gagal. CP17 145/145 lulus pada run Astra dan Sol; Fable mengulang 13 workflow penulis dan semua lulus per kasus kecuali
satu kasus INCOMPLETE karena alat uji (FABLE-018).

## 2. Akar r3 (gabungan per akar masalah)

Penulis memeriksa setiap klaim ke kode sebelum memperbaiki (best practice F27). Bila tingkat berbeda, dipakai yang lebih
tinggi.

| Akar | Temuan | Tingkat | Pemeriksaan penulis | Perbaikan dan uji |
|---|---|---|---|---|
| R3-01 Nomor PO otomatis tidak bisa lewat 999 | ASTRA-R2-02 (S1), SOL-R2-001 (S2) | S1 | Benar: `scripts/cp7-src/cutting-correction/auto-po.sql` baris 216–217 memakai `lpad(v_n::text,3,'0')`, jadi 1000 menjadi `100` dan perulangan tidak pernah keluar | Tiga digit menjadi lebar minimum; kunci per tanggal, UUID dan atomik tetap. Kasus auditor dipakai apa adanya (Astra: 998 PO DRAFT lalu 999 dan 1000; Sol: 999 header, batas 3 detik), ditambah 1001, 9999→10000, dua sesi di batas, UUID sama, gagal di tengah, draf |
| R3-02 Buka ulang PO tetap terkunci sesudah pemakaian barang jadi dibatalkan | ASTRA-R2-01 (S1) | S1 | Benar: `po-reopen.sql` baris 46–47 (`reopen_po_snapshot`) menjumlahkan semua mutasi keluar barang jadi tanpa meniadakan pasangan pembatalan/pembaliknya | Hitung hanya pemakaian yang masih aktif; penghalang untuk reservasi aktif, penjualan, pindah, penyesuaian aktif, periode tertutup, izin dan versi tinjauan tetap. Uji: dua kasus Astra apa adanya, batal sebagian, dua tab, buka ulang lalu selesai lagi (stok, HPP, jurnal sama) |
| R3-03 Layar Enteng diselesaikan, bukan disembunyikan | Keputusan owner **D16-1** (`docs/cp7/OWNER_DECISIONS_20261008.md`), oracle Fable 1–5 | — | Di kandidat: 17 menu HIDDEN di Enteng (`src/screenActivation.ts`), 11 di antaranya sudah tersambung di mode uji | 11 menu (+ Susun Nota FG) dinyalakan untuk Enteng dengan komponen tersambung yang sama; 6 layar baru (Ringkasan Gudang, Riwayat Pelanggan, Reminder, Pengaturan ERP, Tutup Periode, Audit Trail; penggabungan menunggu owner); uji browser build mode Enteng terhadap database sekali pakai, OWNER + peran terbatas, desktop 1440 + HP 390; rantai Fable oracle 3 |
| R3-04 Siklus layar pool HPP absensi | Sol KNOWN-R2-POOL-UI (S1), sisa ASTRA-C17-07 (S2), catatan Fable | S1 | Benar: penulis Native `create/activate/cancel_attendance_hpp_pool` ada, pemanggil di `src` dan fasad CP7 tidak ada; pesan pengaman meminta pool dibatalkan dulu | Layar pool (pratinjau, buat, aktifkan, batalkan) lewat penulis Native, tinjauan/versi, izin saat ini, riwayat, penghalang periode; satu perjalanan layar sampai batal → koreksi sumber → pool pengganti, juga periode tertutup, izin berubah, UUID sama, dua tab. Bagian dari D16-1 |
| R3-05 Langkah rantai tanpa uji lewat layar | FABLE-016 sisa (S3) | S3 | Benar: posting QC & Final SKU dan potongan Nota Ambil Aksesori ke payroll hanya diuji lewat SQL atau UI CP6 beku | Uji browser posting QC & Final SKU dan potongan nota aksesori sampai payroll |
| R3-06 Helper uji membaca alert yang sudah hilang | FABLE-018 (S3) | S3 | Benar: `scripts/cp6_bd_browser.mjs` baris 62–65 memanggil `innerText` sesudah `count` tanpa menunggu | Ambil teks alert tanpa menunggu elemen yang sudah hilang dan simpan teksnya; kasus `BD_BROWSER:OWNER_POLICY_SET_AND_CLEAR` tidak diubah oraclenya |
| R3-07 Alat receipt hanya halaman pertama | Diungkap penulis (E19a); Sol KNOWN-RECEIPT-FIRST100 (S3) | S3 | Benar, juga daftar job per run | Paginasi run, job dan anotasi; uji lebih dari 100 baris |
| R3-09 Pilihan tarif lama atau baru saat jahit selesai | Keputusan owner **D16-2** | — | Native mengunci tarif per PO sejak upah pertama (`erp.po_work_component_snapshots`, unik per PO × komponen × SKU; trigger menyalin tarifnya ke baris upah) | Perubahan Native yang dideklarasikan: pencatatan jahit selesai boleh memakai tarif mandor yang berlaku pada tanggal jahit bila dipilih; layar menampilkan kedua tarif dan nilai upahnya, wajib pilih dan alasan; pilihan disimpan; upah tercatat tidak berubah; Nota/payroll/HPP ikut. Uji: tarif sama (tanpa pilihan), tarif beda pilih lama, pilih baru, wave per SKU, batal, dua tab, UUID sama, hak akses |
| R3-08 Klaim regresi 37 workflow CP6 lama | Astra §5 (batas klaim, bukan cacat) | — | 21 workflow lama merah karena pemeriksa cakupan historis atau artifact kedaluwarsa | Penulis tidak mengklaim regresi arsip lengkap; susun pemetaan kasus pengganti per workflow, atau tetap tulis sebagai batas |

## 3. Ketidakcocokan dan catatan antar laporan

1. **Tingkat R3-01:** Astra S1 (alur posting macet), Sol S2. Dipakai S1.
2. **Tingkat R3-04:** Sol S1 (fungsi belum tersedia), Astra S2. Dipakai S1.
3. **Sol, teks matriks:** `INVARIANT_MATRIX.md` INV-POL03 menulis "bank-negative policy gap SOL-001 masih OPEN", sedangkan
   `RETEST_DISPOSITIONS.json` Sol menulis SOL-001 `RETAINED_CLOSED_FRESH_CASH_CONTROL`. Penulis membacanya sebagai teks
   lama di matriks; ditanyakan ke Sol di putaran berikut, tidak mengubah apa pun.
4. **Fable, catatan owner:** tarif upah terkunci per PO sejak upah pertama (aturan Native `po_work_component_snapshots`);
   kenaikan tarif di tengah PO berlaku untuk PO berikutnya. Fable menyebutnya bukan cacat. Ditanyakan ke owner (§5).
5. **Fable, catatan D15-2:** selama layar uang tersembunyi di Enteng, upah menumpuk sebagai utang dan tidak bisa dibayar
   lewat aplikasi Enteng. D16-1 menyelesaikan ini.
6. **Astra:** penyajian gross OTHER_EXPENSE/OTHER_INCOME (+24/−24) pada pembalik penyesuaian barang jadi lot produksi
   adalah perilaku warisan AY yang tidak disahkan ulang sebagai kebijakan baru. Tidak diubah di r3.
7. **Astra:** di HP, strip langkah QC dan tabel HPP tersambung punya anak yang lebih lebar dengan gulir di dalam; lebar
   halaman lulus. Bukan temuan.
8. **Alat auditor yang dikoreksi auditor sendiri** (Astra oracle akun lot produksi v2; Sol pengamat menu dan checkout
   dangkal): kegagalan pertama disimpan auditor; tidak ada tindakan penulis.

## 4. Batas yang tetap (tidak dikerjakan di r3 kecuali owner membuka)

CP7C (backup awal, Drive, pemasangan hosted; D13-9a), pencabutan EXECUTE 82 penulis `erp` (FABLE-012, D14-9), restore
fungsional CP2 asli, penyebab dua kegagalan A2 dan AZ pertama, perangkat fisik/iPad, data cutover nyata (INV-M01/M03),
preflight hosted baru (INV-M04). Batas bukti yang bisa dikerjakan penulis tanpa hosted dan dicatat untuk r3 bila waktu
cukup: kontrol 0 → +1 → 0 untuk setiap detektor dan catatan detektor sebelum/sesudah setiap skenario (Sol INV-D01/D04).

## 5. Pertanyaan untuk owner

1. Tarif mandor naik di tengah PO: (A) sisa PO itu tetap tarif lama, tarif baru untuk PO berikutnya (aturan sekarang);
   (B) sisa PO ikut tarif baru mulai tanggal berlakunya. **Dijawab owner 17 Okt (D16-2):** "bisa gak dikasih pilihan
   harga lama apa baru, kadang bisa random soalnya" → R3-09. Pertanyaan lanjutan: siapa yang boleh memilih tarif baru.
2. Menu "Tutup Periode" (Pengaturan & Audit) dan "Laporan & Tutup Buku" (Keuangan) sama-sama untuk menutup buku: (A)
   digabung jadi satu menu; (B) dua menu terpisah.

## 6. Urutan kerja r3

1. R3-01 dan R3-02 (kode kecil, kasus auditor apa adanya + kontrol).
2. R3-06 dan R3-07 (alat uji).
3. R3-03 dan R3-04 (D16-1): nyalakan 11 menu + Susun Nota FG, buat 6 layar (atau gabungannya) + layar pool HPP, uji build
   mode Enteng, rantai oracle Fable 3.
4. R3-05 uji browser QC & Final SKU dan potongan nota aksesori.
5. R3-08 pemetaan kasus pengganti workflow CP6 lama.
6. Kualifikasi satu commit, paket uji ulang untuk Fable, Astra dan Sol.

# Handoff putaran silang 1 — untuk Astra

Owner menyalin seluruh isi kotak di bawah ke sesi Astra.

```text
Kamu Astra, auditor independen CP7 ERP Garment. Repo Hanjay6688/-erp-garment-ux, cabang writer
claude/new-session-deapao. Ini PUTARAN SILANG 1 dari owner: kamu menguji ulang temuanmu sendiri, sekaligus memeriksa
silang temuan auditor lain (Fable) yang ikut diperbaiki writer. Audit tetap independen. Cakupan CP7 saja. Keputusan
owner yang sudah disahkan tidak dibuka ulang.

KANDIDAT
- ae0214ad33184f7c2724783d663fb20fcb13820c (tree 0217f5f6740f28c19b7894fcb0181f39d3aea727).
- Kode produk sama dengan 7a0b4a90 yang kamu uji. Bukti: git diff --name-only 7a0b4a90 ae0214ad -- supabase src
  scripts/cp7-src harus kosong.
- 12 berkas alat/uji/workflow berubah. Daftar dan alasannya ada di
  docs/cp7/audit-candidate/crosscheck-r1-20261013/README.md.
- CI writer pada commit yang sama: CI_RECEIPT.json di folder itu. Itu bukti writer, bukan penerimaanmu.

BACA DULU
docs/cp7/audit-candidate/crosscheck-r1-20261013/FINDINGS_TRACKER.md, yaitu gabungan temuanmu (WRITER_HANDOFF 41dbd14d)
dan temuan Fable (audit/fable_cp7/AUDIT_FABLE_7a0b4a90_RETEST.md v1.0.1, cabang
audit/fable-cp7-full-d0b9e9c2-20261011 @ 1a808bc9).

TEMUAN FABLE YANG PERLU KAMU KETAHUI (ringkas; detail di tracker bagian A dan C)
- Vonis Fable atas 7a0b4a90: LULUS DENGAN SYARAT. Diterima owner sebagai dasar pembekuan bersyarat (D13-2).
- Fable menutup F-OPS-01 (kasus dasar), F-OPS-02/03/04, F-UI-01 dan F-AN-01 dengan kasusnya sendiri. Kamu juga
  memverifikasinya. ASR-OPS-01 milikmu adalah sisa keluarga F-OPS-01.
- F-PAY-01 DITARIK oleh Fable (salah kutip versi fungsi). Catatan cakupanmu (cabang "sesi sudah besok" tidak aktif
  pada jam run) tetap dikerjakan di butir A4.
- PR44: Fable MENERIMA area optimasi netting di tree 7a0b4a90 (probe paritas 595/595, mutations_caught 2, netting
  83/83). Kamu penulisnya, jadi tidak ada tindakan darimu.
- Syarat Fable yang masih berlaku: (1) selisih akhir grup bayar supplier belum terjelaskan; (2) pemasangan jadwal dan
  backup menunggu keputusan owner; (3) production_go:false.
- Fable meminta writer "memajukan pin" product_ref=ddedf06c di identitas T3. Writer tidak mengubahnya, dengan alasan
  di tracker A7. Itu urusan Fable, tetapi kamu boleh berkomentar.

TUGAS
1. A1 ASR-OPS-01 (temuanmu). Perbaikan: kepemilikan scratch diikat ke OID database (85e17168). Paket:
   docs/cp7/audit-candidate/asr-ops-01-retest-20261013/ (README.md, CI_RECEIPT.md). Jalankan ulang ASD-B01..B05 dari
   audit/astra_retest_20261013/cases_delta.py tanpa mengubah oracle. Tambahkan kontrolmu sendiri:
   - tulis ke sumber selama backup;
   - sumber tetap utuh;
   - tidak ada pemangkasan saat operasi ditolak;
   - hapus akhir hanya pada scratch milik percobaan, termasuk jalur finally yang kamu temukan dari kode.
   Nilai batas operasional yang dinyatakan writer (penggantian database percobaan oleh admin di antara cek OID dan
   pg_restore). Jangan anggap batas itu sudah disetujui; owner yang memutuskan.
2. A2, silang dari Fable: selisih akhir grup bayar supplier. Baca
   docs/cp7/evidence/fable-retest-20261012/GROUP_END_DIAGNOSIS.md. Bandingkan dengan 26 snapshot milikmu
   (SUPPLIER_BOUNDARY_REVIEW.json). Baca diff scripts/cp6_auditor_runner.py dan scripts/cp6_auditor_difference.py,
   lalu nilai: apakah pencatatan hanya menambah detail dan tidak mengubah hasil pembanding? Status penyebab tetap
   OPEN kecuali kamu punya bukti.
3. A3, silang dari Fable: gladi jadwal. Baca SCHEDULE_REHEARSAL.md di folder yang sama, kasus
   K3C_RACE_SCHEDULE_INSTALLER_REHEARSAL. Periksa bahwa hosted tidak disentuh dan cron.job kembali 0 baris.
4. A4, cakupan F-PAY-01 (catatanmu). Baca F_PAY_01_BOTH_BRANCHES.md di folder putaran ini. Isinya kasus
   P12_SETTLEMENT_WIB_PAYMENT_DATE yang dijalankan pukul 17.00-19.00 WIB, ketika kedua cabang aktif. Kalau mau,
   jalankan sendiri pada jam itu.
5. A6, silang: dua kasus CP6 yang dipensiunkan (SALES_MANUAL_13). Baca docs/cp7/RETIRED_CP6_SALES_MANUAL_13.md.
   Jalankan tests/cp7/SalesPages.dozenHelper.dom.test.tsx, lalu nilai apakah keempat pemeriksaan lama tercakup.
6. A8, perubahan writer sesudah 7a0b4a90 yang belum kamu uji (LATER_WRITER_DELTA.json). Jalankan regresi yang kamu
   anggap perlu pada kandidat ini, minimal suite yang memakai cp6_auditor_runner.py (strict_group). Supplier Payment
   Create dan k3-cleanup-24 disarankan.
7. A9, untuk diketahui: keputusan owner D13-4..D13-7 di docs/cp7/OWNER_DECISIONS_20261008.md. Database produksi =
   Enteng siimvrusnzxexizpyoib, database postgres (D13-7 mengganti D13-4). Owner tidak mau mengeluarkan biaya. Alat
   backup versi berikutnya (salin ke penyimpanan luar, ambil kembali, pulihkan di mesin GitHub) BELUM masuk kandidat
   ini dan akan diaudit terpisah.

BATAS
- Jangan mengubah main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only) atau produksi.
- Jangan push ke claude/new-session-deapao, cp7/integration atau cabang audit lama. Pakai cabang audit baru.
- Jangan memasang jadwal pg_cron atau backup malam di database mana pun selain salinan sekali pakai, dan jangan
  menjalankan probe di hosted.
- Jangan mengirim pesan ke orang lain. Jangan meminta password, token atau kunci.
- Jangan melonggarkan oracle atau guard. Simpan log gagal pertama dan Original.
- production_go:false tetap.

YANG DIKIRIM BALIK (ke owner, untuk diteruskan ke writer)
Satu tabel per butir A1, A2, A3, A4, A6, A8. Untuk setiap butir: DITUTUP / MASIH TERBUKA / TIDAK BERLAKU, run + job +
kasus, asal oracle, dan log gagal pertama kalau ada. Penilaianmu atas batas operasional A1 ditulis terpisah. Temuan
baru diberi ID baru. Simpan laporan dan bukti di cabang audit baru, lalu sebutkan commit-nya.
```

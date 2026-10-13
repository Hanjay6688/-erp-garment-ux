# Handoff putaran silang 1 — untuk Fable

Owner menyalin seluruh isi kotak di bawah ke sesi Fable. Kotak ini menggantikan paste block di
`../fable-retest-20261012/FABLE_V11_REVIEW_REQUEST.md`; isinya sudah tercakup di sini.

```text
Kamu Fable, auditor independen CP7 ERP Garment. Repo Hanjay6688/-erp-garment-ux, cabang writer
claude/new-session-deapao. Registermu: audit/fable_cp7/OWNER_DECISIONS_TO_AUDITOR_20261013.md (cabang
audit/fable-cp7-full-d0b9e9c2-20261011 @ 1a808bc9). Ini PUTARAN SILANG 1 dari owner: kamu menyelesaikan laporan v1.1
atas syarat-syaratmu, sekaligus memeriksa silang temuan auditor lain (Astra) yang ikut diperbaiki writer. Audit tetap
independen. Cakupan CP7 saja. Keputusan owner yang sudah disahkan tidak dibuka ulang.

KANDIDAT
- ae0214ad33184f7c2724783d663fb20fcb13820c (tree 0217f5f6740f28c19b7894fcb0181f39d3aea727).
- Kode produk sama dengan 7a0b4a90 yang kamu uji. Bukti: git diff --name-only 7a0b4a90 ae0214ad -- supabase src
  scripts/cp7-src harus kosong.
- 12 berkas alat/uji/workflow berubah. Daftar dan alasannya ada di
  docs/cp7/audit-candidate/crosscheck-r1-20261013/README.md.
- CI writer pada commit yang sama: CI_RECEIPT.json di folder itu. Itu bukti writer, bukan penerimaanmu.

BACA DULU
docs/cp7/audit-candidate/crosscheck-r1-20261013/FINDINGS_TRACKER.md, yaitu gabungan temuanmu dan temuan Astra
(audit/astra_retest_20261013/REPORT.md, WRITER_HANDOFF.md dan ASR_OPS_01.md, cabang
audit/astra-cp7-retest-7a0b4a90-20261013 @ 41dbd14d).

TEMUAN ASTRA YANG PERLU KAMU KETAHUI (ringkas; detail di tracker bagian A dan C)
- Vonis Astra atas 7a0b4a90: HOLD, karena ASR-OPS-01 dan karena penerimaan PR44 bukan wewenangnya.
- ASR-OPS-01 (keluarga F-OPS-01-mu, S0 bersyarat). Kasus ASD-B05: scratch lama bertanda dibaca OURS sebelum dump, lalu
  admin menggantinya dengan database asing bernama sama. Alat menghapus pengganti itu, dan malam itu tetap
  restore_verified=true. Kasus FABLE_CORE:BACKUP_SCRATCH_DROPS_FOREIGN_DB milikmu lulus karena menguji database asing
  sejak awal, bukan penggantian di tengah. Astra juga menunjuk jalur kedua di finally (boolean ours) dari kode.
- Astra memverifikasi F-OPS-02/03/04, F-UI-01 (4 browser OWNER/ADMIN desktop/HP), F-AN-01, OBS-01 PL-5 owner-only,
  dan F-AP-01 sesuai keputusan owner.
- F-PAY-01: kasus aktif lulus, tetapi cabang "sesi sudah besok" tidak aktif pada jam run Astra, jadi tidak diklaim
  PASS. Writer menjalankannya pada jam ketika kedua cabang aktif (butir A4).
- Supplier Payment Create: 10/10 lulus di run Astra dengan 26 snapshot batas/public state. Sepuluh pembandingan
  awal-akhir sama persis. Penyebab kegagalan writer tetap "belum diketahui" menurut Astra juga.
- ASF-F01 DITUTUP oleh Astra. Kamu memakainya untuk menutup F-TOOL-01.
- ASRA-T01 adalah kesalahan penghitung milik Astra sendiri, ditutup dari Original. Bukan produk.
- Regresi Astra: 21/21 suite, 880 eksekusi PASS, 684 ID unik. Shell 1.726 tes, 6 browser, 2 CodeQL nol temuan.

TUGAS
1. A1, silang dari Astra: ASR-OPS-01. Perbaikan: kepemilikan scratch diikat ke OID database (85e17168). Paket:
   docs/cp7/audit-candidate/asr-ops-01-retest-20261013/ (README.md, CI_RECEIPT.md).
   - Jalankan ulang FABLE_CORE:BACKUP_SCRATCH_DROPS_FOREIGN_DB dan BACKUP_VERIFY_UNDER_LIVE_WRITES di alat baru tanpa
     mengubah oracle. Keduanya hanya memanggil backup().
   - Baca sumber drop_owned / create_attempt / leftovers / backup() di scripts/cp7_nightly_backup.py.
   - Nilai apakah keluarga F-OPS-01 tertutup tanpa membuka jalur hapus baru, dan nilai batas operasional yang
     dinyatakan writer. Jangan anggap batas itu sudah disetujui; owner yang memutuskan.
2. A2, syarat §3.1-mu: selisih akhir grup bayar supplier. Bukti: docs/cp7/evidence/fable-retest-20261012/
   GROUP_END_DIAGNOSIS.md, log 01-07, 06_group_end_repeat_diagnosis_run38357098820.json. Nilai sesuai tabel bentuk
   bukti di registermu. Status yang ditulis writer: OPEN, "tidak terulang pada pengujian berikutnya", kecepatan mesin
   belum dapat disingkirkan (arahan owner 13 Okt). Pesan commit 71594a0b ("runner speed is ruled out") salah; dokumen
   sudah dibetulkan dan riwayat commit tidak ditulis ulang. Supplier Payment Create di kandidat ini ada di
   CI_RECEIPT.json.
3. A3, syarat §3.2c-mu: gladi jadwal. Bukti: SCHEDULE_REHEARSAL.md dan log 08 di folder yang sama. Diulang di
   k3-cleanup-24 kandidat ini.
4. A5, PR44: konfirmasi bahwa penerimaanmu (laporan retest §2.3) berlaku untuk kandidat ini. scripts/cp7-src
   identik, jadi diff kosong sudah cukup sebagai bukti.
5. A6, permintaan owner: dua kasus CP6 yang dipensiunkan (SALES_MANUAL_13, PRE-05). Owner menyetujui pensiun
   BERSYARAT (D13-9c): berlaku sesudah auditor memastikan cakupan penggantinya lengkap. Catatan owner: sebagian
   pemeriksaan helper baru diuji lewat DOM simulasi, belum seluruhnya di browser sungguhan. Baca
   docs/cp7/RETIRED_CP6_SALES_MANUAL_13.md (rujukan, cakupan pengganti, dan "Fakta tambahan untuk auditor": helper
   lusin di layar simulasi dan di P11 belum diuji di browser sungguhan), lalu uji layar
   tests/cp7/SalesPages.dozenHelper.dom.test.tsx. Nyatakan cakupan pengganti LENGKAP atau TIDAK LENGKAP, dengan alasan
   dan apa yang kurang.
6. A7, catatan §2.5-mu ("penulis sebaiknya memajukan pin" product_ref=ddedf06c). Writer tidak mengubahnya. Nilai itu
   bukan pin: scripts/cp6_run_identity.py menghitungnya dengan git log -1 -- <jalur produk>, yaitu commit terakhir yang
   mengubah supabase/* dan src. Terima atau bantah dengan alasan.
7. A8: tinjau diff 12 berkas alat/uji sesudah 7a0b4a90, terutama scripts/cp6_auditor_runner.py, yang dipakai
   strict_group di semua workflow.
8. A9, untuk diketahui: keputusan owner D13-4..D13-9 di docs/cp7/OWNER_DECISIONS_20261008.md. Database produksi =
   Enteng siimvrusnzxexizpyoib, database postgres (D13-7 mengganti D13-4). Owner tidak mau mengeluarkan biaya. Semua
   urusan backup dan Google Drive (lokasi, uji pemulihan, repo privat, daftar periksa pemasangan, backup pertama)
   ditahan sampai tahap CP7C (D13-9a), jadi bukan bagian dari putaran ini.

BATAS
- Jangan mengubah main, deployment Cloudflare, Supabase hosted Enteng (siimvrusnzxexizpyoib), legacy ERP-Garment
  (vlxdhpkjeevubjxexnfo, read-only) atau produksi.
- Jangan push ke claude/new-session-deapao, cp7/integration atau cabang audit lama milik orang lain.
- Jangan memasang jadwal pg_cron atau backup malam di database mana pun selain salinan sekali pakai.
- Jangan mengirim pesan ke orang lain. Jangan meminta password, token atau kunci.
- Jangan melonggarkan oracle atau guard. Simpan log gagal pertama.
- production_go:false tetap.

YANG DIKIRIM BALIK (ke owner, untuk diteruskan ke writer)
Laporan v1.1 dengan satu tabel per butir A1, A2, A3, A5, A6, A7, A8. Untuk setiap butir: DITUTUP / MASIH TERBUKA /
TIDAK BERLAKU, run + job + kasus, dan label bukti (FABLE / INDEPENDENT_NATIVE_RERUN / INDEPENDENT_SOURCE_REVIEW).
Penilaianmu atas batas operasional A1 ditulis terpisah. Temuan baru diberi ID baru. Sebutkan commit laporannya.
```

# OW13a — checkpoint B,23 Oktober2026 WIB

Pemicu awal, status kesiapan, tombol pengisian target dan pembukaan hasil dengan
UUID server sudah dibuat. **OPEN**:68/68 Native lulus, kelompok dua pengguna/HTTP/layar
tertahan penyiapan salinan; paket126 belum lulus. Rantai A,
pemasangan jadwal dan tombol Master pada host A belum dikualifikasi. Parent
tetap5/16. B tidak memasang Enteng, mengubah main atau memberi production_go.
Audit independen tetap Fable/Sol.

## Perilaku

- Minimum dan batas peran di [CONTRACT.md](CONTRACT.md). Profil kosong tidak
  diberi angka. Semua produk masuk analisis dengan unknown yang sebenarnya;
  kesiapan awal belum memastikan kelayakan produksi.
- Sekali per actor Owner/Admin dengan empat hak operasi sekarang. Job yang
  periode/akses/sumbernya sama dipakai lagi, termasuk job manual. Unique actor
  dan mutex menahan duplikasi; job actor dengan kueri lain yang masih berjalan
  ditunggu. Runner tetap dapat memproses pekerjaan pengguna lain.
- Pemicu berada sebelum syarat pengaturan WA pada tick lama; tidak membuat
  jadwal, pesan atau provider. Sesudah intent dibuat, tick tidak mengambil
  seluruh sumber tiap menit. Claims dipulihkan pada semua jalan keluar.
- Layar membaca STATUS lalu ENSURE kondisional bila READY, tanpa UUID klien
  palsu. Kehilangan jawaban dibaca ulang dari intent server. Tombol hasil
  memasukkan UUID server ke driver lama tanpa mengganti request tertunda lain.
  Buka ulang me-remount driver dengan UUID sama;401/403 membatalkan fakta.
- Periode awal mengikuti window pengingat yang dipilih (bawaan30 yang sudah
  disetujui owner), AS_SOLD sampai kemarin WIB. Periode/waktu sumber terlihat;
  snapshot lama tidak diam-diam menjadi data sekarang. Keuangan DEFERRED.

## Bukti penulis

`local-initial.json`: **11/11 kelompok SQL**. Fungsi produk, wrapper publik,
create_job/status dan penjaga akses sebenarnya; ERP/source/Auth/unit WA memakai
adapter terkontrol. Pemasang dan22 kelompok katalog sebenarnya: apply/admit,
rollback tepat, reapply; setelah intent ada, penolakan sebelum DDL pertama.
Ini PGlite lokal, bukan Native/Auth/dua sesi atau pasang-pulih rantai A.

`local-client.json`: **197 uji/17 berkas lulus**; pemeriksaan terfokus sesudah
perbaikan buka ulang42 uji/5 berkas juga lulus. TypeScript/CSS lulus. Fixture
READY/RUNNING/EXPIRED berasal dari SQL aktual di atas. DOM integrasi membuka
formulir profil dan driver lama. Enam kontrol manual lama kini eksplisit STAFF;
Owner/Admin mendapat pemicu baru D17-16. Oracle manual tidak dihapus.

Kegagalan pertama tetap tersimpan. `local-first-failure.json`: epoch identitas
fixture berada di luar proyeksi akses dan owner tabel fixture belum sesuai
principal beku; penjaga produk tidak dilonggarkan. `local-installer-first-failure.json`:
PG18 mencatat enam NOT NULL sebagai constraint; PG17 lewat atribut kolom.
Pemeriksa meminta set tepat per versi. Referensi primer:
[PG18](https://www.postgresql.org/docs/18/catalog-pg-constraint.html),
[PG17](https://www.postgresql.org/docs/17/catalog-pg-constraint.html).

Native126 sudah dideklarasikan, **belum PASS**: seluruh113 WA/kain lama +13 baru
(7 Native,2 races,2 HTTP,2 browser), total68/36/9/13. Dua tahap target/awal wajib
invers22 sebelum kasus. Kasus halaman ditutup memanggil worker K4 sebenarnya
dari alat uji; bukan klaim cron terpasang. Native286 sebelumnya tetap bukti
a753ebc tersendiri, tanpa pilihan statistik, bridge keuangan atau pemicu ini.

Kandidat6738da4c/run39881934739/job120181076950: **INCOMPLETE,0/126 diamati**.
Pemasangan dua tahap/invers22 lulus; sesudahnya pemeriksa WA lama menolak satu
grant tambahan `cp7_initial_analysis.tick()` yang memang dideklarasikan tahap
baru. Receipt [6738da4-first-native126.json](6738da4-first-native126.json),
Original lengkap dan log tetap privat. Pemulihan lulus; advisor runtime belum
dijalankan sehingga belum PASS. Tidak ada kasus gagal yang diganti lulus.

Perbaikan komposisi alat uji: pemeriksa WA **tidak diubah**. Invers awal yang
terverifikasi dipakai di savepoint untuk memeriksa predecessor tepat, lalu
rollback savepoint wajib mengembalikan seluruh22 grup katalog tahap terpasang.
Verifikasi tahap baru di kedua sisi menjaga izin tambahan tepat satu; tidak
menambah pengecualian umum. Lokal11 kelompok tetap lulus; API/katalog aktual
juga membuktikan oracle gagal diteruskan dan keadaan22 tetap pulih pada jalur
lulus maupun gagal. Native126 perbaikan masih harus membuktikan komposisi ini.

Perbaikan39360e5/run39883844008/job120187290457 juga **0 kasus**: oracle P09
atas seluruh fungsi/ACL masih terikat snapshot tahap baru saat memeriksa
predecessor. Receipt39360e5-native126-first-composition-fix.json disimpan.
Komposisi kini wajib cocok tepat22 grup dengan katalog predecessor yang
ditangkap **sebelum** pemasangan awal, baru mengikat snapshot fungsi oracle
ke predecessor terverifikasi itu; snapshot tahap kini dipulihkan di finally.
Oracle kesamaan P09 dan pemeriksa WA tetap tidak diubah. Lokal11 SQL/invers22
serta42 klien lulus; juga dibuktikan pengikatan sementara dan pemulihan
snapshot oracle pada jalur lulus/gagal. Hasil Native berikutnya belum diklaim.

17d9d62a/run39885283105/job120191923758: **68/68 Native PASS**, seluruh ID tepat,
termasuk tujuh tambahan awal/statistik; restore/advisor PASS. Races/HTTP/browser
belum punya kasus: guard predecessor22 menolak salinan. Receipt
[17d9d62-native126-first-mode-copy.json](17d9d62-native126-first-mode-copy.json).
Sumber mode lama memakai createdb TEMPLATE tanpa menyalin pemilik/ACL/GUC
database; skrip clone AB yang diterima sudah menjaga hal itu. Wrapper B baru
memperbaiki hanya tiga database mode lokal, memakai pemilik/grantor postgres,
menyalin ACL dan GUC di server, lalu meminta **seluruh otoritas database sama**
dengan sumber. Tidak menerima pemilik baru sebagai pengecualian oracle22.
Skrip A tidak diedit; perbedaan berikut akan mencetak nama grup/objek tanpa
isi fungsi atau nilai rahasia. Empat kontrol transport/otorisasi lokal lulus;
pelaksanaan SQL replay dan semua kasus mode masih harus dibuktikan Native.

a86d22a2/run39887742896/job120199774843: **124/126 PASS**; Native68/68,
races36/36, HTTP8/9, browser12/13, seluruh ID126 hadir tepat. Restore/advisor
PASS. Seluruh38 salinan mode membuktikan pemilik/ACL/GUC sama dengan sumber;
pemilik sebelumnya supabase_admin, dipulihkan postgres tanpa mengecualikan
grup katalog. Receipt [a86d22a-first-native126-124.json](a86d22a-first-native126-124.json);
Original lengkap/log dan kegagalan mobile disimpan, bukan diganti hijau.

Dua kegagalan berada di alat uji baru. HTTP menuntut NOT_READY sesudah tujuh
kontrol lama sudah mengisi profil global; server benar menjawab READY dengan
tiga target eligible. Journey min-data kini berjalan pertama di salinan segar,
**expected NOT_READY tetap**, diikuti seluruh tujuh kontrol lama. Hanya urutan
daftar/deklarasi HTTP berubah; tidak ada ID atau assertion lama dihapus.
Navigasi mobile kini menunggu sidebar/Auth/App benar-benar terpasang sebelum
memeriksa tombol menu, sama dengan helper mobile lama. Drawer nyata tetap
dibuka dan viewport390 dipertahankan, tanpa force-click. Review fixture worker
juga menambah satu putaran antrean yang dibatasi jumlah job: run_next global
dapat memilih job desktop lebih tua dulu. Tetap worker K4 yang sebenarnya,
tanpa mengubah job atau memanggil step actor langsung. Native berikutnya masih
diperlukan; kode produk/SQL/UI tidak diubah oleh perbaikan fixture ini.

## Permintaan integrasi A

1. SQL dasar tetap beku. Tahap produksi18, OW16 dan registry terdahulu, lalu
   `cp7_target_policy_stage`. Bila OW12a + bridge OW12b dipakai, pasang bridge
   **sebelum** `cp7_initial_analysis_stage`. Invers kebalikannya. Request awal
   menerima tepat dua predecessor terpin, tanpa bridge atau dengan bridge.
2. API `install_delta/verify/admit_catalog/rollback_preuse` mengandalkan
   transaksi/envelope/global use guard A. Delta:1 skema/1 tabel immutable dan
   metadata/4 fungsi,2 badan lama. Intent bertahan sesudah hasil kedaluwarsa;
   setelah dipakai wajib backup/restore. Owner/RLS/ACL/objek dan22 grup dijaga.
3. [SHARED_INTEGRATION.patch](SHARED_INTEGRATION.patch) menggantikan patch enam
   pasangan lama: sekarang **tujuh** pasangan registry. Berkas bersama tidak
   diedit B. Salinan sementara dengan patch tepat ini lulus Source Ownership
   (358 runtime files/302 boundaries); repo B masih merah sampai A menerapkan.
   Tambahkan nullable p_request pada tipe request bersama; null hanya sah pada
   mode awal tertutup. B memakai addon tipe sempit pada client yang sama.
4. Teruskan `onOpenMaster` ke NativeDemandHistoryPanel dari host stok milik A,
   menuju Master produk sebenarnya. Tombol target sudah membuka formulir B;
   keadaan tanpa produk belum punya tombol Master di host.
5. Pasang **jadwal analisis yang sudah ada dan runner K4** bersama proses
   server, termasuk bila WA belum pernah dikonfigurasi. B tidak memasang cron.
   Kualifikasi A membuktikan siap → diminta → selesai tanpa browser, bukan
   hanya tick manual.

OW10 sumber/periode/lead/WIP varian, OW11a/b, OW12b Native/3.600 barang dan OW13c
tetap terbuka. UI atau uji lokal di atas tidak menutup pekerjaan tersebut.

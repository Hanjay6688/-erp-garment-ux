# OW04: kandidat writer untuk pembatalan sumber, 21 Oktober 2026

Ini kandidat internal writer, belum bukti Native63, belum audit independen,
belum OW04 lengkap, dan `production_go:false`.
Cabang kerja `codex/ow04-reconciliation-20261021` berawal dari checkpoint
`81da8181f428fa790b812d90a86832913ef5424d`; kandidat yang harus diperiksa adalah
commit tepat yang dicatat workflow, bukan nama cabangnya saja.
Kandidat audit `55c885d1` tetap beku. Enteng, Drive, WA nyata, `main`, dan
`cp7/integration` tidak disentuh.

## Perubahan dan expected yang dikunci sebelum CI

Jalur public CP7 untuk `RETURN_REVERSE` dan `PAYMENT_REVERSE` mengikat pekerjaan
ke actor/request/action/payload/version/PID/transaction yang benar-benar sedang
berjalan. Native tetap membuat pembalik sumber dan pergerakan stoknya.
Tepat sebelum Native menghitung ulang pembayaran efektif, coordinator menghitung
selisih setiap keluarga retur terhadap seluruh INITIAL dan ADJUSTMENT historis.
Selisih negatif diposting sebagai jurnal ADJUSTMENT baru pada pasangan tanggal
pembalik Native yang sebenarnya. Jurnal lama dan jejak sumber tetap disimpan.
Semua rencana satu operasi dipasang sebelum part pertama diposting; pengecualian
pembacaan hanya berlaku untuk seluruh rencana milik operasi yang persis sama.

Closure menuntut kecocokan sumber, seluruh jurnal/part, saldo, status nota,
receipt CP7 yang sesungguhnya, dan tiadanya scope sementara. Operasi tanpa
selisih uang tetap punya bukti operasi dan completion, tetapi tidak membuat
jurnal nol atau financial marker palsu. Reader publik memeriksa materialisasi
aktual tanpa meminjam scope atau izin pekerjaan yang sudah selesai.

Lima kasus baru memakai transaksi Native/public asli dan expected uang yang
dibekukan pada dua berkas berikut; expected lama58 tidak diubah:

- `reconciliation/native/EXPECTED.json`: SHA256
  `9b038e877372848b4e7f86695107d6e99695013b4e443ecda55e1fa6e989dffd`.
  Retur dibatalkan: I200→0, E800→1000, AR tetap0; stok6→5.
  Pembayaran dibatalkan: P1000→0, I200→0, E800→0, AR0→800; stok tetap6.
  Keduanya mempertahankan INITIAL200, menambah ADJ−200, dan replay tanpa efek.
  Izin actor yang dicabut menolak request baru maupun replay; konsumsi REFUND200
  menolak pembatalan dengan identitas ketergantungan yang nyata.
- `reconciliation/native/ZERO_DIFF_EXPECTED.json`: SHA256
  `0eaa6829643dc5675c4d854a75ea855486bc78db6d8aa54c2d09d803945c2a7a`.
  Pembatalan retur lebih awal yang nilai uangnya nol mempertahankan kredit200
  retur berikutnya; stok7→6. Hanya jurnal HPP Native10 yang bertambah.
  Tidak ada ADJ, konsumsi, atau financial marker baru.

Fixture menyatakan prasyarat satu hari Jakarta sebelum/sesudah command karena
stock memakai `clock_timestamp`, sedangkan jurnal memakai `statement_timestamp`.
Tidak ada perubahan jam atau penggantian oracle uang.

## Pemeriksaan pemicu dan temuan silang

Manifest pemicu berasal dari katalog P00 yang diterima, sumber paket CP6,
seluruh generator predecessor saat ini, dan DDL OW04 yang tepat. Bukan dari
menerima sembarang katalog yang kebetulan ditemukan saat instalasi.
Ada25 attachment biasa/18 fungsi, serta99/117/119 FK untuk fase predecessor,
OW04, dan OW04+EMPTY. RI internal juga dihitung dari FK sumber.
Installer memeriksa transisi tersebut; pelepasan menuntut katalog awal kembali
persis. Guard runtime privat diperiksa pada entry dan completion sumber.
Table lock kompatibel DML menahan perubahan trigger/table DDL.
Perubahan definisi fungsi oleh admin lain tidak dikunci table lock ini;
verifikasi katalog sesudah operasi tetap wajib. Ini bukan bukti seluruh callgraph.

TG-C1 ditemukan pemeriksa kedua setelah penilaian awal dikunci: FK dan RI lama
bisa dibuat ulang dengan OID baru dan lolos pembanding transisi semantik.
Contoh accepted-bad disimpan di `trigger-counter/ACCEPTED_BAD_REPRO.json`.
Perbaikan menuntut seluruh FK/RI dengan semantik yang tetap ada di kedua fase
mempertahankan baris katalog dan identitasnya. Counterexample yang sama sekarang
ditolak, termasuk varian RI saja; tiga transisi yang sah masih lulus.

Pemeriksa 06/07 tidak menemukan recursion loop: pemeriksaan closure/completion
berakhir di pembacaan mekanis objek aktual. Bukti historis memakai part/jurnal
historis yang tepat, sedangkan keadaan hidup dicocokkan dengan ordinal terbaru.
Empat sumber helper yang memang berubah dipin ulang secara eksplisit dan14
overlay EMPTY diregenerasi tanpa mengganti algoritma builder atau oracle Native.
Ini review internal writer; bukan penerimaan auditor eksternal.

## Bukti dan batas

- `internal-compile/`:223 fungsi, termasuk50 fungsi baru, lolos validator lokal
  PostgreSQL18.6/PGlite dengan `check_function_bodies=on` pada hash yang dicatat.
  Bukan instalasi Native17.6; scaffold sengaja tidak menjalankan Native/Auth.
  Pertama ditemukan42601 pada CASE di `source_inverse_proof_v1`; input/error asli
  disimpan dan diperbaiki dengan tanda kurung CASE. Delapan celah scaffold/
  pemeriksaan metadata bukan PASS instalasi dan tidak disembunyikan.
- Tiga hitungan pure SQL sintetis menguji−200, retained INITIAL200+ADJ−50
  menghasilkan−150, serta selisih nol. Tidak membuktikan kelengkapan sumber.
- `runtime-guard/`: query katalog dan fungsi guard hasil renderer benar-benar
  dikompilasi pada PGlite; katalog scaffold yang salah ditolak. Expected digest
  nol di artefak itu hanya kontrol penolakan, tidak pernah input installer.
  Installer nyata menghitung SHA kanonik jsonb memakai PostgreSQL sendiri dari
  snapshot aktual yang sudah lolos manifest sumber; fungsi menyimpan64 digit,
  sementara snapshot lengkap tetap disimpan untuk verifikasi.
- `PURE_ADMISSION_CONTROLS.json`: import32/44/58/63 tanpa koneksi, reproduksi
  byte-exact14 overlay, dan perubahan sumber tanpa pin yang ditolak.
- Bukti Native58 pada3a667 dan HTTP8/race6/browser4 pada d6f tetap bukti kandidat
  sebelumnya. Tidak dipindahkan menjadi bukti kandidat ini. Penyimpanan mobile
  lama2041,726075ms masih melewati target2000ms; bukan PASS kinerja global.

## Reproduksi kualifikasi dan pekerjaan berikut

Expected63 dan ID persis ada di
`docs/cp7/d17-14/ow04/NATIVE_SIGNED_SOURCE_QUALIFICATION.json`.
Workflow `.github/workflows/cp7-ow04.yml` pada cabang kerja ini membangun ulang
Supabase sekali pakai, memasang predecessor yang diterima, memasang kandidat
secara atomik, menjalankan `python scripts/cp7_ow04_probe.py --signed-source`,
lalu membuktikan restore skema/data/fungsi dan advisor. Ikuti layout checkout dan
variabel konfirmasi workflow; jangan arahkan ke Enteng.

Cakupan pertama sengaja hanya existing CREDIT tanpa konsumen pada sumber noPO,
tanpa opening-HPP state, recost, konversi atau advance. Kelas lain ditolak sebelum
efek sampai adapter lengkapnya dibuktikan. Aktivasi kredit baru/selisih positif,
APPLY dan undo konsumen, koreksi nota/retur yang lebih luas, UI lengkap, serta
HTTP/race/browser sumber baru masih terbuka. Regresi baru harus dibuktikan pada
commit yang sama; kode hijau subset ini tidak menutup OW04 atau D17-14 seluruhnya.
Sesudah checkpoint disimpan, writer melanjutkan backlog terotorisasi.

## Kegagalan CI pertama dan perbaikan alat uji

Run39542503493 pada17e9d587 berhenti di allowlist argumen __main__, sebelum
package.run dan sebelum transaksi Native. Opsi signed-source sudah dikenali
saat import, tetapi terlewat pada allowlist pemanggilan langsung. Log penuh,
identitas artefak dan disposisinya disimpan di native-first-17e9d587/.
Allowlist diperbaiki; tujuh kontrol mengeksekusi __main__ yang sebenarnya
dalam child terisolasi dengan dispatcher dicatat dan semua koneksi menolak.
Kontrol ini tidak menjalankan callback writer dan tidak menjadi Native PASS.
Expected uang, stok dan daftar63 kasus tetap sama; kandidat perbaikan perlu
menjalankan kualifikasi Native63 sungguhan.

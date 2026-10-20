# OW-03 — kelipatan produksi yang dipilih di aplikasi

Dasar: D17-14/OW-03. Writer di `astra/d17-14-20261020`; kandidat auditor
`55c885d1` tetap beku. Pemeriksaan di sini milik writer, bukan audit independen.

## Expected yang dideklarasikan sebelum kualifikasi Native/browser

- Profil yang sudah ada berlaku per identitas produk/ukuran. Isian baru bersatuan
  PCS, mula-mula kosong; menerima bilangan bulat positif kanonis berupa string,
  maksimal 30 digit, atau null untuk belum dipilih. Tidak ada angka bawaan baru.
- Profil lama enam kunci dan permintaan UUID lama tetap persis sama. Menambahkan
  null pada payload UUID lama harus ditolak sebagai payload berbeda. Izin kini
  tetap diperiksa sebelum replay; revisi/profil lama tidak ditulis ulang.
- Saran dihitung dari kebutuhan bersih kondisional yang sudah ada:
  `tambahan = (M - (gap mod M)) mod M`, `saran = gap + tambahan`.
  Nilai pilihan ini berstatus ASSUMED dengan rujukan profil dan asumsi asal.
- Contoh independen: gap 13/M12 -> 24+tambahan11; gap12/M12 ->12+0;
  gap0/M12 ->0+0; gap93/M12 ->96+3; gap13/M5 ->15+2.
  Perhitungan melewati batas integer JavaScript tetap tepat.
- Nilai kosong, profil belum ditinjau/kedaluwarsa, atau gap belum diketahui
  tetap UNKNOWN. PAUSED/STOPPED mempertahankan saran nol dan tambahan UNKNOWN.
- Seluruh hasil analisis langsung dan bertahap pada satu sumber harus identik.
  Dua produk dengan kelipatan berbeda tetap memakai profil masing-masing.
  Perubahan profil membuat sumber lama menjadi arsip; hasil lama tetap utuh.
- Gap, stok, WIP, alokasi, kebutuhan bahan, kapasitas, `feasible_new`, dan
  kesiapan produksi tetap mengikuti sumber/guard yang berlaku. Saran kelipatan
  bukan bukti bahwa bahan atau kapasitas cukup. Formulir rencana tetap harus
  memenuhi pemeriksaan yield/bahan yang berlaku.
- Browser komputer/HP: isian benar-benar disimpan, dibaca kembali, dan dipakai
  analisis; kehilangan balasan memakai UUID/payload yang sama. Tabel dan laporan
  menyebut saran sebelum pemeriksaan bahan/kapasitas serta tambahan kelipatan.

## Bukti lokal awal dan batas

- `local-profile-first-failure.log`: lima kasus positif baru gagal pada kode
  sebelum OW-03; 33 kontrol lain lulus. `local-profile-fixed.log`: 38/38 lulus.
- `local-sql-first-failure.log`: penulis SQL lama menerima kontrol legacy lalu
  menolak profil dengan kelipatan eksplisit. `local-sql-fixed.jsonl`: 165/165
  pemeriksaan sintetis PGlite lulus, termasuk 120 kasus BigInt acak dan batas
  30 digit. Ini tidak menggantikan PostgreSQL Native atau uji dua sesi.
- Isian, compiler, dan skenario Native/browser telah/akan ditambahkan dalam
  kandidat ini. Hasil Native/browser baru belum tersedia saat expected ini
  ditulis; tidak ada klaim syarat selesai penuh atau `production_go`.

## Kandidat kualifikasi yang disiapkan

- Profil: 40/40 unit+DOM setelah tambahan replay enam kunci melawan profil
  tujuh kunci yang lebih baru dan clear 12 -> null -> revisi2 -> remount kosong.
- Temuan internal lama: hasil bertahap masih terlihat sesudah HTTP401, selama
  provider login belum memuat ulang identitas. Tiga kasus CHECK/FRESHNESS/PAGE
  gagal sebelum perbaikan (`local-staged-401-first-failure.log`); reset seluruh
  state bertahap saat AUTH_REQUIRED/FORBIDDEN memberi 17/17 PASS
  (`local-staged-401-fixed.log`). Gangguan jaringan biasa tetap mengikuti
  kontrak kesegaran snapshot; penolakan autentikasi/hak menghapus fakta.
- Manifest staged naik menjadi **15 = 7 Native + 4 balapan + 2 HTTP + 2 browser**.
  Kasus baru memakai dua sumber Native terpisah: FG0, WIP8, yield9/10 ->7,
  target100, gap93. M12 ->96+3; M5 ->95+2. BOM2 tetap kebutuhan186.
  Perbandingan langsung/bertahap memakai satu referensi tersimpan dan seluruh
  hasil; antar revisi, metadata rujukan berubah secara sah sementara nilai,
  keadaan, bahan, kapasitas, kualitas dan kesiapan tetap dibandingkan.
- Kedua publikasi laporan Native (langsung dan bertahap) diuji dengan nilai
  pilihan tersebut dan hash dokumen/bagian; clear profil tidak mengubah
  publikasi atau Original lama. Ini deklarasi expected, belum hasil CI.
- Browser profile benar-benar mengisi/simpan/retry12 dan membacanya kembali.
  Browser analisis langsung serta bertahap memperoleh gap93/saran96/tambahan3,
  rujukan profil yang persis, kelayakan UNKNOWN, dan mencabut akses sesudahnya.
  Browser bertahap mencari halaman yang berisi produk fixture; tidak berasumsi
  produk acak itu ada pada halaman pertama. Batas overflow tepat innerWidth.
- Satu kasus Native profil ditambahkan tanpa menghapus kasus lama; anggaran
  suite turunan ikut naik: baseline38, supply54, schedule72, netting84,
  analysis154, attention287 (Native182). Ini kenaikan jumlah uji, bukan
  perubahan batas kapasitas atau pelemahan gerbang.

Counter-review awal terikat base333005ed + patch `fa614dcd…`, final pada
patch `8b65c887…`; semua empat pembantu GPT-6.1 Sol Max hanya membaca dan
memberi temuan/usulan, integrasi oleh satu writer. Temuan asumsi halaman0
diperbaiki sesudah review final; perbandingan kualitas/kesiapan dan publikasi
Native ditambah. Tidak ada klaim bahwa kesepakatan agen membuktikan produk.
Replay lintas versi penuh di PostgreSQL Native belum dibuktikan; fixture
Native menggunakan bentuk legacy, sedangkan pemeriksaan upgrade apply lama
ke baru yang dilaporkan pemeriksa memakai sumber/identitas sintetis PGlite.

## Hasil Native pertama — kandidat2ad56e14

Run `39420750723`, job `118620792464`: **38/38 PASS**, pemulihan CP6 dan advisor
PASS; receipt lengkap `CI_39420750723.json`. Hash sumber terpasang
`9e2603d23d8dcdf25861f5956f87b2eb94c9f9fcda9cc25c0d7214c17cc306d2`.
Bukti ini mencakup simpan12 dari browser sungguhan, ulang UUID sesudah
balasan hilang dan pembacaan kembali; bukti ini sendiri belum membuktikan
bahwa compiler analisis memakai profil hasil simpan yang sama.

Run `39420750819`, job `118620792620`: **154/154 PASS**. Run `39420750772`,
job `118620792697`: **15/15 PASS**, termasuk kasus Native baru dengan dua
kelipatan12/5, parity hasil utuh pada referensi sama, publikasi laporan kedua
jalur, clearUNKNOWN dan arsip immutable. Kedua receipt mencatat hash sumber
`3c0364ceafa88804e5ae8ab0804e2d0902aff036c249d344808ebb9936e40005`;
pemulihan CP6/advisor PASS. Browser langsung dan bertahap desktop/HP PASS.
Receipt: `CI_39420750819.json` dan `CI_39420750772_STAGED.json`.
Transport juga **15/15 PASS** pada job118620792626, receipt
`CI_39420750772_TRANSPORT.json`; nama job lama bukan jumlah kasus aktual.
Hasil ini memakai kandidat produk2ad, sebelum penguatan perjalanan tunggal
di bawah; tidak dilabeli sebagai runtime alat uji yang belum dijalankan.

## Penguatan alat uji setelah produk2ad — expected sebelum run

Hanya dua berkas alat uji berubah: `cp7_f05_analysis_browser.mjs` dan
`cp7_f05_analysis_browser_fixture.py`. Kode produk tetap byte-identik dengan
2ad56e14. Perjalanan browser utama sekarang tidak menyuntikkan M melalui
fixture: profil mula-mula kosong, pengguna mengisi12, menyimpan lewat RPC,
memuat aturan kembali dan membaca12. Analisis sesudahnya wajib memberi
gap93/saran96/tambahan3 dengan ID/revisi **hasil simpan layar yang sama**,
pada desktop dan HP. Expected keuangan, arsip, replay,403 dan larangan efek
bisnis tetap utuh. Jumlah kasus F05 tetap154; ini penguatan dua kasus browser.

Jadwal fixture terikat hash sumber. Sesudah simpan profil, langkah terpisah
`review_schedule` meninjau ulang pekerjaan Native yang sama terhadap suplai
terbaru, tanpa mengubah konfigurasi. Ini dinyatakan terbuka sebagai langkah
fixture; bukan bukti bahwa peninjauan kalender dilakukan melalui layar.
Operasi lama `update_schedule` tetap mengubah unit_minutes menjadi4 untuk
menguji arsip basi. Counter-review read-only Sol Max pada patch
`13ee8eae1c44405b25dfaa4293d17b6433bbb6e01dc34b094e70dd130e07947f`
tidak menemukan penghalang; Node syntax dan Python AST PASS. Runtime baru
belum ada ketika expected ini ditulis. F05 terpicu; matriks P19 tidak perlu
diulang karena produk dan kasus matriks tidak berubah.

Tambahan pemeriksaan lokal: `local-compile-check.mjs` membuat60 fungsi dari
lima sumber SQL kandidat2ad di PGlite0.5.10 dengan row-type kosong;
`local-compile-result.jsonl` mencatat60/60 berhasil. Ini hanya kompilasi tubuh,
bukan bukti perencanaan kueri, izin atau bisnis Native. Log stderr kosong
dipertahankan. Jangan menambahkan angka60 ke jumlah kasus Native.

## Hasil penguatan perjalanan layar — kandidat878e0a9c

Run `39423331714`, job `118629536646`, head persis
`878e0a9cad779db42826d7cb1fb97d978d498b73`: **154/154 PASS**,
termasuk desktop dan HP yang mengetik12 pada profil kosong, menyimpan,
memuat kembali12, lalu memperoleh gap93/saran96/tambahan3 dengan ID/revisi
profil hasil simpan layar yang sama. Replay, arsip, laporan/AI, keuangan,
pencabutan izin403, pemulihan CP6 dan advisor juga tetap PASS.
Receipt lengkap: `CI_39423331714.json`.

Hash SQL terpasang `3c0364ceafa88804e5ae8ab0804e2d0902aff036c249d344808ebb9936e40005`
cocok komposisi bundle lokal878. Semua berkas produk byte-identik terhadap2ad;
perubahan non-dokumen sesudah2ad hanya dua berkas alat browser yang disebut
di atas. Bukti2ad digunakan kembali dengan batas identitas ini, bukan dengan
mengganti label kandidat lama. **OW-03 selesai pada kontrak isian dan analisis.**

Kualifikasi umum tetap terpisah: K6 pada2ad gagal sebelum satu kasus pun
berjalan, karena port database bentrok lalu registry menolak unduhan akibat
batas data (`CI_39420750772_K6_ENVIRONMENT.json`). Permintaan ulang satu job
ditolak GitHub karena workflow yang sama masih berjalan; itu bukan hasil
uji produk. Skala5.000 masih dipantau terpisah. Tidak ada klaim kecepatan
1/2/3detik, audit independen, kesiapan seluruh ERP, atau izin produksi.

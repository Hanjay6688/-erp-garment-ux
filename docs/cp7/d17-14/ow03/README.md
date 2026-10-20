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

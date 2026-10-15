# Keputusan owner 8 Okt 2026 — catatan writer

Sumber: pesan owner di chat writer Claude, 8 Okt 2026. Kalimat owner dikutip apa adanya; kolom "arti untuk
pekerjaan" adalah catatan writer dan tidak menambah aturan. Keputusan yang sudah disahkan sebelumnya
(GBD-03 opsi 1, lima keputusan D11, arahan 7 Okt) tidak dibuka ulang.

**Pembekuan.** Owner: "Bekukan kandidat audit sekarang. Pengembangan kebijakan dan fitur tambahan di atas dicatat
sebagai kelanjutan terpisah, supaya paket yang sedang diaudit tidak terus berubah." Maka butir 3–9 di bawah
**tidak** diimplementasikan di kandidat audit; semuanya masuk `CONTINUATION_AFTER_FREEZE_20261008.md`.
Kandidat audit: `audit-candidate/final-20261008/`.

| # | Keputusan owner (kutipan) | Arti untuk pekerjaan |
|---|---|---|
| Integrasi | "Boleh push ke `cp7/integration`, tanpa force push dan tanpa menyentuh `main`. Catat SHA akhirnya dan pastikan bukti CI sesuai kode yang digabung." | Fast-forward `cp7/integration` ke SHA kandidat; seluruh workflow yang terpicu dan 15 workflow kualifikasi dijalankan pada SHA itu; receipt di `audit-candidate/final-20261008/FREEZE_RECEIPT.json`. |
| 1 P20 | "siapkan paket final untuk auditor di sesi terpisah. Audit harus memeriksa sendiri seluruh cakupan, bukan cuma mengulang temuan penulis. Penulis tetap boleh membantu reproduksi dan perbaikan, tetapi tidak memberi penerimaan independen." | `audit-candidate/final-20261008/AUDITOR_START_P20.md`. Writer tidak pernah menulis `independent_acceptance=true`. |
| 2 P21 | "tunggu audit diterima dan izin pemasangan terpisah. Gladi yang hijau tetap dicatat sebagai gladi. `production_go:false`." | Gladi `37716123319` tetap berlabel latihan; `installed_P21_acceptance=false`, `production_go=false`. |
| 3 PL-5 B | "setuju paket usulan histori: 180 hari, minimal 5 grup selesai dan 200 PCS potong, per produk+size lalu fallback model yang sama, batas bawah Wilson satu sisi 90%. Jangan lintas model atau menganggap yield 100%. Bila data kurang, gunakan A yang ditinjau atau UNKNOWN. Simpan keputusan sebagai kebijakan berversi dan uji sebelum diaktifkan." | Parameter usulan `PL5_YIELD_POLICY_PROPOSAL_20261007.md` disetujui. Implementasi (kebijakan berversi + `history_yield` + kasus Native) adalah kelanjutan; sampai lulus uji, sistem tetap `PENDING_POLICY_VALUE`. |
| 4 Retensi | "hasil analisis sementara disimpan 7 hari setelah selesai atau dibatalkan. Jangan hapus job yang belum selesai, dokumen transaksi, atau bukti yang diperlukan audit. Hasil kedaluwarsa harus diberi keterangan jelas." | Nilai 7 hari menggantikan `PENDING_POLICY_VALUE` retensi staged. Implementasi (jadwal purge + label kedaluwarsa) adalah kelanjutan. |
| 5 Prioritas 5.000 | "rencana/rekomendasi produksi → Business Report → pengingat → AI. Setiap fitur baru harus memakai hasil lengkap yang sudah diverifikasi." | Urutan kelanjutan downstream staged. Halaman tidak pernah dipakai sebagai hasil lengkap. |
| 6 Penjalan | "arah akhirnya berjalan di server, supaya tetap lanjut saat halaman ditutup. Membuka ulang harus melanjutkan job yang sama, bukan menghitung ulang atau menggandakan pekerjaan." | Driver server (pg_cron) adalah kelanjutan; kontrak UUID/job yang sama tetap. |
| 7 Capture | "Capture 4,4–4,6 detik: diterima sementara sebagai bagian pekerjaan latar belakang. Layar tetap responsif dan progresnya jelas. Optimalkan semaksimal mungkin; 3 detik sasaran, bukan alasan melonggarkan angka, hash, akses, atau batas 8 detik." | Pilihan capture ditutup sementara: diterima sebagai latar. Batas 8 dtk, hash dan akses tetap. |
| 8 PL-8 | "arahkan penjalan bukti otomatis di server. Bukti harus diperiksa terhadap versi sumber dan tidak boleh tetap dianggap berlaku setelah koreksi atau pembatalan." | Runner server PL-8 adalah kelanjutan; aturan versi sumber yang sudah ada tetap. |
| 9 CP6 | "keputusan yang sudah disahkan jangan ditanyakan ulang. Untuk delapan pengaturan nyata yang masih kosong, kirim tabel sederhana berisi pilihan, rekomendasi, dan transaksi yang tertahan. Akun serta kategori nyata jangan dikarang." | Tabel dikirim ke owner; nilai nyata tetap diisi owner. |
| PR #45 | "PR #45 tetap terpisah; jangan merge ke `main` dulu." | Tidak ada merge ke `main`. |

Status tetap: `independent_acceptance=false`, `installed_P21_acceptance=false`, `production_go=false`.

## Tambahan 8 Okt (sesudah pembekuan)

- Owner: "1200 sku, masing masing 3 ukuran" → ±3.600 target perencanaan (1 target = 1 ukuran). Ini di atas kapasitas
  analisis biasa (±100–300 target, batas 1.000 produk), jadi di pabrik ini rencana produksi, Business Report, pengingat
  dan AI baru bisa dipakai kalau tersambung ke analisis bertahap.
- Owner: "better kerjaan lanjutan baru diaudit gak sih? kalo kerjaan lanjutan lu gakjelas masa audit 2x?" → arah: kelanjutan
  CP7 dikerjakan dulu, lalu dikunci ulang dan diaudit sekali. Urutan: rencana/rekomendasi produksi → Business Report →
  pengingat → AI (butir 5), lalu empat lanjutan kecil (yield histori, aturan simpan 7 hari + tanda kedaluwarsa, hemat
  penyimpanan, percepat "Cek sumber"). Pekerjaan CP7C (jadwal otomatis di server, hapus terjadwal, backup malam) tidak
  dikerjakan di sini.
- Kandidat beku `9d57b7f5` tetap tercatat sebagai titik periksa; kandidat audit berikutnya menggantikannya.

## Keputusan owner 8 Okt: snapshot berlabel waktu untuk analisis bertahap (kontrak versi baru)

Kutipan owner apa adanya:

> Pakai hasil analisis dengan label waktu. Jangan mewajibkan seluruh ERP berhenti berubah selama analisis.
>
> Hasil tetap merupakan snapshot yang tidak diubah. Tampilkan “data per tanggal/jam …”, status kesegarannya, dan perubahan relevan sejak analisis. Jangan disebut data terkini kalau sudah berubah.
>
> Business Report, pengingat, dan AI boleh memakai snapshot tersebut sebagai analisis. Angka aktual keuangan, stok, dan HPP tetap mengikuti sumber otoritatif sesuai tanggal laporan.
>
> Rencana boleh dibuat dan disimpan sebagai draf. Saat disahkan atau dijalankan, server wajib memeriksa ulang stok, bahan, WIP, kebutuhan, kebijakan, dan akses yang relevan dalam transaksi yang sama. Kalau berubah sehingga rencana tidak valid, tolak dengan alasan jelas dan minta tinjau ulang.
>
> Pengingat juga diperiksa ulang sebelum dikirim, supaya kondisi yang sudah selesai tidak tetap ditagih.
>
> Perubahan ini dibuat sebagai versi kontrak baru beserta uji; jangan mengubah kandidat audit yang sudah dibekukan.

Penerapan: kontrak `docs/cp7/p19/P19_STAGED_SNAPSHOT_V2.md`. Kandidat beku `9d57b7f5` (`cp7/integration`) tidak diubah;
pekerjaan ini di cabang Claude sesudahnya.

## Keputusan owner 9 Okt: hapus data kerja sementara sesudah analisis DONE; jadwal pembersihan dan backup malam

Kutipan owner apa adanya:

> Ya, setuju. Hapus data kerja yang benar-benar sementara setelah analisis DONE dan seluruh hasil final tersimpan serta terverifikasi.
> Syaratnya:
>
> 1. Hasil final, halaman, hash, waktu analisis, dan asal data yang diperlukan tetap tersedia selama retensi 7 hari. Dokumen transaksi dan bukti audit tetap dilindungi.
> 2. Pastikan Business Report, rencana, pengingat, AI, serta buka ulang hasil DONE tetap berfungsi setelah pembersihan. Data yang masih diperlukan fitur tersebut harus dipertahankan.
> 3. Pembersihan harus aman diulang dan tidak menyentuh job yang belum selesai. Kalau pembersihan gagal, hasil analisis tetap tersedia dan pembersihannya bisa dicoba lagi.
> 4. Dua uji lama boleh disesuaikan dengan perilaku baru, tetapi pemeriksaan angka, kelengkapan, hash, dan asal data harus tetap ketat. Tambahkan uji buka ulang hasil sesudah pembersihan.
> 5. Ukur penyimpanan langsung pada 5.000 target sebelum dan sesudah pembersihan. Angka 125 MB dan penghematan 100 MB tetap ditulis sebagai perkiraan sampai terbukti.
> 6. Lanjutkan pembuatan dan uji jadwal pembersihan serta backup malam yang sudah disepakati. Pemasangan sungguhan tetap menunggu audit dan izin pemasangan.
>
> Satukan perubahan yang diperlukan, jalankan kualifikasi pada satu versi final, lalu bekukan paket audit terbaru. Kandidat lama dan bukti kegagalan tetap disimpan. `production_go:false`.

Penerapan: `docs/cp7/k3/K3_CLEANUP.json`, `scripts/cp7-src/planning/analysis-stages.sql` (bagian cleanup),
`scripts/cp7-src/ops/schedule.sql`, `scripts/cp7_schedule.py`, `scripts/cp7_nightly_backup.py`, suite CI `k3-cleanup-17`.
Pembersihan berjalan dari jadwal server (tiap 5 menit), tidak di dalam permintaan pengguna; karena itu tidak ada uji lama
yang perlu diubah. Waktu dan jumlah simpan backup malam yang dipakai (01:00 WIB, 14 malam terverifikasi) adalah pilihan
bawaan yang bisa diubah; tempat simpan backup di luar database ditentukan saat pemasangan.

## Keputusan owner 9 Okt: K4 dikerjakan sekarang, audit nanti sekalian

Pertanyaan writer: "Saya perlu Bos memutuskan: bagian itu [K4, penjalan server] dikerjakan sekarang sambil menunggu
audit, atau sesudah pemasangan?" Jawaban owner apa adanya:

> kerjain dl aja nnti audit nya sekalian semua

Penerapan: K4 (keputusan 8 Okt butir 6, "arah akhirnya berjalan di server, supaya tetap lanjut saat halaman ditutup")
dikerjakan sekarang di cabang Claude, di atas kandidat revisi P20 `870d4f79`. Uji ulang F01–F05 dan audit K4 dijadikan
satu putaran audit. Deklarasi: `k4/K4_RUNNER.json`. Penjalan dibuat dan diuji (pg_cron sungguhan di salinan uji),
**belum dipasang**: pemasangan tetap menunggu audit dan izin owner. `production_go:false`.

## Keputusan owner 12 Okt: dashboard terhubung dan hak ubah kebijakan PL-5 B

Dua pertanyaan dari audit penuh CP7 Fable atas `d0b9e9c2` (F-UI-01 dan OBS-01). Jawaban owner apa adanya:

1. Pertanyaan: "Halaman depan (Dashboard) di mode terhubung sekarang menampilkan angka uang contoh (Rp284,6 jt dst.)
   yang bukan angka ERP. Mau diapakan?" Jawaban: **"Sembunyikan (Rekomendasi)"**.

   Penerapan: di mode terhubung, Dashboard hanya menampilkan keterangan "Ringkasan angka belum tersambung ke data ERP";
   tidak ada angka contoh. Mode demo tidak berubah. `src/OwnerDashboard.tsx`, uji `src/OwnerDashboard.dom.test.tsx`.

2. Pertanyaan: "Siapa yang boleh mengubah angka kebijakan yield histori PL-5 (180 hari, 5 grup, 200 PCS)?" Jawaban
   pilihan pertama di layar pertanyaan adalah "Owner + admin (tetap)"; owner lalu menulis jawaban akhir yang
   menggantikannya:

   > Pilih **Owner saja — opsi 1**. Admin tetap boleh melihat. Hak mengubah wajib diperiksa di server. Setiap perubahan
   > disimpan sebagai **versi baru**, lengkap dengan alasan, waktu, dan identitas owner. Analisis serta riwayat lama tetap
   > memakai versi kebijakan asalnya.

   Penerapan: hanya peran OWNER yang bisa menyimpan versi kebijakan (diperiksa di server, `CP7_YIELD_POLICY_OWNER_REQUIRED`;
   tabel versi menolak baris selain `actor_role='OWNER'`). Admin dan pengguna lain hanya bisa melihat. Versi hanya
   ditambah, tidak pernah diubah, dan menyimpan alasan, waktu serta identitas owner. Rencana yang sudah disahkan menyimpan
   yield yang dipakai saat dipotong, termasuk nomor versi kebijakannya, sehingga perubahan kebijakan sesudahnya tidak
   mengubah analisis atau riwayat lama. Kasus: `scripts/cp7_pl5_history_yield_cases.py`, deklarasi
   `pl5/PL5_HISTORY_YIELD.json`.

## Keputusan owner 13 Okt: penegasan 12 Okt, dasar pembekuan bersyarat, penundaan pemasangan

Disalin tanpa mengubah kata-kata dari register auditor Fable
`audit/fable_cp7/OWNER_DECISIONS_TO_AUDITOR_20261013.md` (cabang `audit/fable-cp7-full-d0b9e9c2-20261011`, commit
`1a808bc9`), yang mencatat pesan owner langsung ke auditor. Waktu penegasan: **2026-10-13T05:53:51Z** (13 Okt 2026
12:53 WIB). Berkas auditor itu adalah sumbernya.

| No | Keputusan owner (verbatim) |
|---|---|
| D13-1 | "Ya, tegaskan keputusan 12 Oktober: dashboard disembunyikan sesuai cakupan keputusan tersebut; perubahan kebijakan PL-5 hanya oleh owner. Admin tetap boleh melihat. Catat waktu penegasan sekarang." |
| D13-2 | "Ya, terima `7a0b4a90` sebagai dasar pembekuan bersyarat. Pencatatan selisih, tiga run bayar supplier, dan verifikasi auditor atas hasilnya harus selesai sebelum pembekuan final." |
| D13-3 | "Ya, tunda izin pemasangan jadwal dan backup malam sampai nama database tujuan yang persis serta lokasi dump di luar mesin database ditetapkan. Penulis siapkan usulan lokasi dan cara pemulihannya untuk saya pilih." |

Instruksi owner kepada penulis (verbatim dari register yang sama):

1. "Tambahkan diagnosis selisih pemeriksaan akhir, lalu jalankan workflow bayar supplier tiga kali pada tree yang sama. Laporkan SHA/tree, seluruh hasil termasuk kegagalan, dan akar penyebabnya. Tiga run hijau saja belum menjelaskan penyebab kegagalan sebelumnya."
2. "Gladi jadwal di salinan sekali pakai CI dengan deklarasi 01:00 WIB, cocokkan `schedules()` dengan K3, lalu uninstall dan buktikan pemulihannya. Hosted tetap tidak disentuh."

Status label di laporan auditor: keputusan 12 Okt di atas kini OWNER_CONFIRMED_TO_AUDITOR. Tidak ada pemasangan
pg_cron atau backup malam di database mana pun selain salinan sekali pakai sampai owner memilih tujuan (D13-3).
`production_go:false`.

## Keputusan owner 13 Okt (lanjutan): database tujuan, lokasi backup, uji pemulihan

Jawaban owner atas `docs/cp7/BACKUP_DESTINATION_PROPOSAL_20261013.md` (pilihan B, L1, ya), disampaikan langsung ke
penulis pada 13 Okt 2026. Kata-kata owner dikutip apa adanya.

| No | Keputusan owner (verbatim) |
|---|---|
| D13-4 | "B — proyek Supabase baru khusus produksi. Enteng tetap untuk UAT. Catat ID proyek baru dan database `postgres` di register. Siapkan biaya serta langkah penyelarasannya sebelum dibuat; perpindahan aplikasi tetap menunggu hasil verifikasi dan izin pemasangan." |
| D13-5 | "L1 — Cloudflare R2. Gunakan bucket privat, dump terenkripsi, dan kunci melalui GitHub Secrets. Simpan 14 backup malam terakhir yang sudah terverifikasi beserta tanda terimanya. Backup baru yang gagal jangan menyebabkan backup baik sebelumnya terhapus." |
| D13-6 | "Ya — pemeriksaan restore di mesin GitHub, menggunakan database sementara dengan versi PostgreSQL dan ekstensi yang sesuai. Periksa isi data, struktur, owner, serta hak akses. Ambil kembali file dari R2 untuk memastikan file yang tersimpan itulah yang bisa dipulihkan. Dump produksi jangan masuk repo, artifact publik, atau log." |

Syarat dan arahan lain dari pesan yang sama (verbatim):

- "Sebelum produksi, buktikan juga pemulihan ke proyek Supabase terpisah. Kelulusan di PostgreSQL lokal belum membuktikan seluruh konfigurasi hosted pulih."
- "Untuk dua kegagalan bayar supplier, tetap OPEN. Tulis “tidak terulang pada pengujian berikutnya”; jangan menyatakan kecepatan mesin pasti tersingkir hanya karena mesin lebih cepat juga lulus. Tidak perlu terus mengulang tanpa hipotesis baru."
- "Minta Fable meninjau bukti diagnosis dan gladi untuk laporan v1.1. Dua kasus CP6 yang disebut dipensiunkan harus punya rujukan keputusan dan cakupan penggantinya."
- "Pilihan ini menjadi dasar persiapan. `production_go:false`; hosted yang sekarang tetap tidak diubah."
- "Kalau ERP memakai file Supabase Storage, file itu perlu backup tersendiri—dump database hanya mencakup metadatanya."

Register proyek produksi: **Enteng `siimvrusnzxexizpyoib`, database `postgres`** (D13-7 di bawah, mengganti D13-4).
Tidak ada proyek baru yang dibuat. Belum ada jadwal, backup malam,
bucket atau kunci yang dibuat atau dipasang. `production_go:false`.

### Batas biaya (owner, 13 Okt 2026)

Verbatim: "btw gw sih gamau keluarin duit 1000 pun loh."

Akibatnya bagi D13-4..D13-6: semua persiapan harus tanpa biaya. Yang perlu dijawab owner sebelum proyek produksi atau
penyimpanan dibuat: (1) apakah Enteng dan ERP-Garment lama ada di akun Supabase gratis yang sama (paket gratis: 2
proyek aktif per akun, 500 MB, berhenti sesudah 7 hari tanpa aktivitas, tanpa backup otomatis); (2) boleh
mendaftarkan kartu/PayPal ke Cloudflare untuk R2 (gratis sampai 10 GB, tidak ditagih), atau memakai Google Drive;
(3) backup produksi dijalankan dari repo GitHub privat terpisah (repo ini publik, sehingga log dan artifact-nya
terbuka untuk umum).

### Jawaban owner 13 Okt 2026: proyek produksi = Enteng (D13-7, mengganti D13-4)

Verbatim: "1 ya, erp enteng juga merupakan database yg bakal kita pakai bukan. kalau takut rusak kita bisa backup dulu
ke drive. pake akalnya bos."

| No | Isi | Catatan penulis |
|---|---|---|
| Pertanyaan 1 | "ya": Enteng dan ERP-Garment lama ada di akun Supabase gratis yang sama. | Konektor Supabase penulis (hanya baca) melihat satu organisasi "ERP enteng", paket `free`. Daftar proyeknya tidak terlihat oleh konektor, jadi jawaban owner yang dipakai. |
| D13-7 | Database produksi = Enteng `siimvrusnzxexizpyoib`, database `postgres`. Tidak ada proyek baru. | Mengganti D13-4 (B). Alasannya: akun gratis hanya boleh 2 proyek aktif, keduanya sudah terpakai, dan ERP-Garment lama tidak boleh diubah (termasuk dijeda). Enteng juga proyek yang selama ini dipakai untuk menyelaraskan semua uji CP6/CP7, jadi langkah penyelarasan dan biaya proyek baru tidak diperlukan. |
| D13-7a | Sebelum ada perubahan di Enteng, isinya di-backup dulu ke Google Drive. | Backup ini dijalankan dengan alat backup (sesudah versi Drive siap). Perubahan di Enteng tetap menunggu izin pemasangan. |

Alat backup versi 2 untuk D13-5/6/7 sudah dibuat dan diuji di server sekali pakai: lulus 11/11 ke penyimpanan S3 dan ke
folder (`docs/cp7/OFFSITE_BACKUP.md`). Alat ini belum dipasang, dan Drive, R2 maupun Enteng belum disentuh.

Yang tetap berlaku: `production_go:false`. Hosted yang sekarang belum diubah. D13-6 (pemeriksaan pemulihan di mesin
GitHub) tetap. Data uji (UAT) yang sekarang ada di Enteng perlu dibersihkan sebelum live, sesudah dibackup ke Drive.
Itu masuk persiapan CP8.

Masih perlu jawaban owner (ya/tidak), karena bertabrakan dengan batas biaya:

1. Backup malam juga ke Google Drive, bukan R2. Alasannya, R2 meminta kartu atau PayPal didaftarkan (D13-5).
2. Syarat "buktikan pemulihan ke proyek Supabase terpisah" butuh proyek ketiga, dan itu tidak muat di akun gratis.
   Usulan tanpa biaya: sebelum live, selagi Enteng masih berisi data uji, pemulihan dibuktikan ke Enteng sendiri.
   Urutannya: backup ke Drive dulu, lalu pulihkan dari file Drive itu, lalu cocokkan isi, struktur, owner dan hak
   akses. Langkah ini dijalankan dengan izin owner saat itu.
3. Backup produksi dijalankan dari repo GitHub privat terpisah (gratis). Repo ini publik.

### Keputusan owner 13 Okt 2026: Google Drive, uji pemulihan lokal, repo privat (D13-8)

Verbatim:

> Keputusan saya:
>
> 1. Ya, backup awal dan backup malam ke Google Drive. R2 dibatalkan untuk sekarang. Dump tetap terenkripsi, disertai
>    hash dan tanda terima. Pertahankan 14 backup terakhir yang terverifikasi selama kuota Drive mencukupi; jangan
>    menghapus backup baik karena backup baru gagal.
> 2. Tidak untuk uji yang menimpa Enteng sendiri. Enteng tetap calon produksi. Gunakan lingkungan Supabase
>    lokal/container sekali pakai di mesin GitHub, dengan versi, ekstensi, dan batas hak akses yang sesuai hosted. Ini
>    tidak membutuhkan proyek hosted ketiga. Catat batas pembuktiannya: keberhasilan di lingkungan lokal belum otomatis
>    membuktikan pemulihan hosted.
> 3. Ya, gunakan repo GitHub privat terpisah untuk backup produksi. Tetap wajib Rp0: gunakan runner standar, batasi
>    penggunaan, dan blokir pemakaian berbayar. Kredensial melalui Secrets; dump tidak masuk repo, log, artifact, atau
>    cache.
>
> Sebelum alat dipakai, buktikan jalur Google Drive sungguhan: unggah → unduh kembali → periksa hash → pulihkan →
> cocokkan data, struktur, dan hak akses. Kelulusan peniru S3/folder belum membuktikan koneksi Drive.
> Kirim paket versi yang sama ke Astra dan Fable untuk uji silang. Penyeragaman constraint/ACL dan perlakuan skema
> GraphQL harus ikut diperiksa, dengan perbedaan aslinya tetap tercatat.
> Enteng belum boleh diubah sebelum backup awal berhasil dan terverifikasi. `production_go:false`.

| No | Isi | Akibat |
|---|---|---|
| D13-8a | Penyimpanan backup awal dan malam = Google Drive. R2 dibatalkan untuk sekarang. | Mengganti D13-5 (L1 R2) untuk sekarang. Enkripsi, hash, tanda terima, 14 malam terverifikasi, dan aturan "malam gagal tidak menghapus" tetap berlaku. |
| D13-8b | Uji pemulihan sebelum produksi tidak menimpa Enteng. Uji dilakukan di Supabase lokal/container sekali pakai di mesin GitHub, dengan versi, ekstensi dan batas hak akses seperti hosted. | Mengganti syarat "proyek Supabase terpisah". Batasnya wajib dicatat: lulus di lokal belum otomatis membuktikan pemulihan hosted. |
| D13-8c | Backup produksi dijalankan dari repo GitHub privat terpisah, Rp0. | Runner standar, pemakaian dibatasi, pemakaian berbayar diblokir, kredensial lewat Secrets. Dump tidak masuk repo, log, artifact atau cache. |
| D13-8d | Sebelum alat dipakai, jalur Google Drive sungguhan dibuktikan (unggah, unduh kembali, hash, pulihkan, cocokkan). | Kelulusan peniru S3 atau folder tidak dihitung sebagai bukti Drive. |
| D13-8e | Paket versi yang sama dikirim ke Astra dan Fable. Penyeragaman constraint/ACL dan perlakuan skema GraphQL ikut diperiksa, dan perbedaan aslinya tetap tercatat. | — |
| D13-8f | Enteng tidak diubah sebelum backup awal berhasil dan terverifikasi. | `production_go:false`. |

Status D13-8b (13 Okt 2026, penulis): uji pemulihan ke Supabase lokal baru sebagai `postgres` bukan admin penuh sudah
dibuat dan lulus di CI (run 38397645331, commit `bebf2dc5`). Batasnya tercatat: lulus di lokal belum membuktikan
pemulihan hosted. Rincian: `docs/cp7/evidence/restore-drill-20261013/CI_RECEIPT.md`. Uji silang auditor: paket
`docs/cp7/audit-candidate/restore-drill-r1-20261013/`.

### Keputusan owner 13 Okt 2026: urutan backup, kirim putaran 1, pensiun SALES_MANUAL_13 (D13-9)

Pertanyaan penulis: (1) semua urusan backup dan Drive, termasuk dua paket backup untuk auditor, ditahan sampai CP7C?
(2) paket putaran 1 CP7 dikirim sekarang ke Astra dan Fable? (3) pensiun kasus `SALES_MANUAL_13` disahkan?

Sebelumnya owner bertanya: "btw kenapa lu nanyain gdrive sekarang ya? emang cp7 lu udah beres? drive kan 7.5 punya?"

Jawaban owner (verbatim):

> 1ya, 2ya, 3 = Itu dua tes otomatis lama untuk helper lusin → pcs di form penjualan, versi desktop dan HP. Angka "13"
> berasal dari jumlah manual 5 + 4 + 4 = 13 pcs.
> Tesnya memastikan:
>
> * Isi manual tetap tersimpan kalau helper kosong.
> * 1,1 lusin ditolak karena menghasilkan pecahan pcs.
> * 1 lusin dibagi tiga ukuran menjadi 4/4/4 pcs.
>
> Menurut catatan penulis, tes lama mencari form simulasi, sedangkan aplikasi tersambung sekarang membuka layar
> penjualan P11. Karena itu selector lamanya gagal.
> "Pensiun" berarti mengeluarkan kedua tes itu dari paket CP7. Tes asli tetap tersimpan di paket CP6.
> Gue sarankan setuju bersyarat setelah auditor memastikan cakupan penggantinya lengkap. Saat ini, sebagian
> pemeriksaan helper baru diuji lewat DOM simulasi; cakupannya belum seluruhnya dibuktikan di browser sungguhan.

(Tautan "catatan penulis" di pesan owner menunjuk `docs/cp7/RETIRED_CP6_SALES_MANUAL_13.md` pada commit `0b3df8de`.)

| ID | Keputusan | Akibat |
|---|---|---|
| D13-9a | Semua urusan backup dan Google Drive ditahan sampai tahap CP7C, termasuk dua paket backup untuk auditor (`audit-candidate/offsite-backup-r1-20261013/`, `audit-candidate/restore-drill-r1-20261013/`). | Paket itu tidak dikirim sekarang. Tidak ada langkah Drive atau repo privat yang diminta dari owner sebelum CP7C. Alat dan bukti yang sudah ada tetap disimpan. D13-7 dan D13-8 tetap berlaku untuk tahap CP7C. |
| D13-9b | Paket putaran silang 1 CP7 (`audit-candidate/crosscheck-r1-20261013/`) dikirim sekarang ke Astra dan Fable. | Owner yang mengirim. |
| D13-9c | Pensiun `SALES_MANUAL_13` (desktop dan HP) dari komposisi CP7 **disetujui bersyarat**: berlaku sesudah auditor memastikan cakupan penggantinya lengkap. | Sampai auditor memastikan, status pensiun belum sah. Catatan owner ikut diperiksa auditor: sebagian pemeriksaan helper baru diuji lewat DOM simulasi, belum seluruhnya di browser sungguhan. |

### Keputusan owner 13 Okt 2026 sesudah laporan Fable v1.1 putaran silang 1 (D13-10..D13-13)

Disalin tanpa mengubah kata-kata dari register auditor Fable
`audit/fable_cp7/OWNER_DECISIONS_TO_AUDITOR_20261013.md` (cabang `audit/fable-cp7-full-d0b9e9c2-20261011`, commit
`9fc44978`), yang mencatat pesan owner langsung ke auditor. Waktu penegasan: **2026-10-13T16:30:49Z** (13 Okt 2026
23:30 WIB). Berkas auditor itu adalah sumbernya. Laporan yang dijawab: `audit/fable_cp7/AUDIT_FABLE_XC1_ae0214ad_v1.1.md`
(commit `6e3a8983`).

| No | Keputusan owner (verbatim) |
|---|---|
| D13-10 | "Ya, A2 diterima sebagai bukan penghalang pembekuan, dengan diagnosis tetap terpasang. Status akar penyebab tetap OPEN, dan dua kegagalan lama beserta bukti aslinya tetap disimpan." |
| D13-11 | "Saya izinkan pembanding terurut sebagai pelengkap diagnosis. Pembanding asli tetap menentukan hasil pemeriksaan. Pelengkap harus mempertahankan semua anggota, duplikat, definisi, owner, dan hak akses; tujuannya membedakan perubahan urutan dari perubahan isi, tanpa menyamarkan kegagalan." |
| D13-12 | Putaran 2 penulis: (1) "A6: tambahkan kasus browser sungguhan P11 desktop dan HP yang menekan 'Terapkan lusin baris N'. Periksa hasil qty, pemeliharaan baris lain, serta hasil simpan/baca ulang. Pensiun `SALES_MANUAL_13` baru sah setelah auditor menyatakan cakupan penggantinya LENGKAP." (2) "F-OPS-05: hanya tanda kepemilikan dengan OID yang cocok boleh mengizinkan penghapusan. Tambahkan uji tanda lama disalin ke database asing: database itu harus tetap utuh." |
| D13-13 | "Simpan bukti pertama, catat SHA/tree setiap hasil, lalu kirim kandidat putaran 2 yang sama ke Astra dan Fable. Pembekuan final mengikuti penutupan dua butir tersebut; A2 tetap tercantum sebagai keterbatasan terbuka. `production_go:false`." |

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner):

- A2 tercantum sebagai keterbatasan terbuka, bukan syarat pembekuan. Diagnosis tetap terpasang. Dua kegagalan lama
  (run 38288829388 dan 38330557862) dan log aslinya tetap disimpan apa adanya.
- D13-11 adalah izin, bukan perintah. Di putaran 2 penulis tidak menambah pembanding kedua. Alasannya:
  `state_difference` yang sudah terpasang sudah membedakan ORDER_ONLY dari CONTENT setiap kali grup gagal, dan
  menambah pembanding di `cp6_auditor_runner.py` akan menyentuh semua workflow.
- Putaran 2 berisi dua butir D13-12: kasus browser P11 desktop dan HP untuk helper lusin (A6), dan F-OPS-05 (hanya
  tanda ber-OID yang boleh mengizinkan penghapusan, ditambah uji tanda lama yang disalin ke database asing).
- Kandidat putaran 2 satu SHA/tree yang sama untuk Astra dan Fable (D13-13). Register ini masuk ke kandidat itu.

Status D13-13 (14 Okt 2026, penulis): kedua butir D13-12 ditutup oleh Astra (`57ac8aab`, `fb24bd92`) dan Fable
(`46fe722c`..`319e6624`) pada kandidat `0b7049d9`. CP7 dibekukan final pada `0b7049d9203bac52b47a4c89f3e0d75646067a8f`
(tree `ce6aed0a0af920e8aa80248f3cabcd293688df18`), dengan A2 sebagai keterbatasan terbuka. Rincian:
`docs/cp7/FREEZE_CP7_FINAL_20261014.md`. `production_go:false`.

## Keputusan owner 14 Okt 2026: audit penuh CP1–CP7 (D14-1..D14-5)

### D14-1 (owner ke auditor Fable)

Disalin tanpa mengubah kata-kata dari register Fable `audit/fable_cp17/OWNER_DECISIONS_TO_AUDITOR_20261014.md`
(cabang `audit/fable-cp1-7-0b7049d9-20261014`, commit `29c7fbd21f0eecbbc7f72af7ccf2507e390a14a9`,
2026-10-14T13:17:08Z). Berkas auditor itu sumbernya.

| No | Keputusan owner (verbatim) | Konsekuensi menurut register Fable |
|---|---|---|
| D14-1 | "gw kasi ijin akses 1-2" — dijawab pada pertanyaan cakupan Fable dengan dua pilihan: **"Baca-saja hosted Enteng"** dan **"Ambil arsip CP2 dari Drive"**. | Hanya untuk verifikasi CP1/CP2: query SELECT katalog baca-saja ke Enteng `siimvrusnzxexizpyoib`, dan mengambil arsip CP2 terenkripsi + kuncinya dari Drive untuk restore di database sekali pakai. Tidak ada tulis ke hosted dan tidak ada pemasangan. |

Catatan penulis: D14-1 adalah izin untuk auditor Fable, bukan untuk penulis. Larangan penulis menyentuh hosted dan
Drive (D13-9a) tidak berubah.

### D14-2..D14-5 (owner ke penulis Claude, sesudah laporan Fable, Astra dan Sol)

Diberikan langsung di sesi penulis pada 15 Okt 2026 sekitar 00:15 WIB (2026-10-14T17:15Z), lewat pertanyaan
pilihan. Pertanyaan dan jawaban ditulis persis.

| No | Pertanyaan penulis | Jawaban owner (verbatim) |
|---|---|---|
| D14-2 | "Upah mandor dibayar dengan tanggal sebelum utang upahnya tercatat (sebelum Nota/periode disetujui). Aturannya mau bagaimana?" Pilihan yang dipilih berbunyi: "Tanggal bayar harus sama atau sesudah utang upahnya ada. Bayar duluan hanya lewat kasbon yang tercatat. Tanggal mundur tetap boleh asal tidak mendahului utangnya." | "Tolak, kecuali kasbon (Disarankan)" |
| D14-3 | "Kas atau bank jadi minus karena pembayaran (Sol: bank saldo 0 bisa bayar supplier 1 rupiah). Boleh minus?" Pilihan yang dipilih berbunyi: "Semua pembayaran keluar (supplier, laundry, upah, kas lain) ditolak kalau membuat saldo kas/bank minus pada tanggal mana pun." | "Tidak boleh, tolak (Disarankan)" |
| D14-4 | "Sisa kain sesudah potong yang benar-benar dikembalikan ke gudang. Sekarang aplikasi hanya mencatat 'sisa terlapor', belum ada tombol untuk memasukkannya lagi ke stok. Dibuatkan?" Pilihan yang dipilih berbunyi: "Ada langkah 'kain kembali ke gudang': roll yang sama masuk stok lagi beserta nilainya, biaya PO berkurang sebesar itu." | "Ya, masuk stok lagi (Disarankan)" |
| D14-5 | "Form penjualan asli: helper lusin sekarang hanya mengisi satu baris ukuran. Perlu fitur bagi 1 lusin ke beberapa ukuran sekaligus (misal 4/4/4)?" | "justru biar gampang gitu dong auto bagi kalo lusin, apalagi sales, lu inget kan kalau gw jual itu biasa satu seri. berjalan 2 arah juga misal gw ketik 4/5/4 tulisannya jadi 1 lusin 1 potong kan gitu" |

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner):

- D14-2 (FABLE-001 / Astra FIN01): pembayaran upah biasa, penuh maupun cicilan, ditolak bila tanggal bayarnya
  mendahului tanggal utang upah yang dilunasinya. Bayar duluan hanya lewat kasbon yang tercatat. Tanggal mundur yang
  tidak mendahului utangnya, aturan periode tertutup, dan pembalikan tetap seperti sekarang.
- D14-3 (SOL-001): semua pengeluaran kas/bank ditolak bila saldo akun itu menjadi minus pada tanggal bayar atau tanggal
  sesudahnya. Belum ada rekening yang diizinkan minus.
- D14-4 (FABLE-010 / Astra SG-02): dibuat langkah "kain kembali ke gudang" untuk roll yang sama, dengan nilai ikut
  kembali dan biaya PO berkurang sebesar itu.
- D14-5 (Sol, kebutuhan lama `SALES_MANUAL_13`): form penjualan tersambung mendapat bagi lusin otomatis ke satu seri
  ukuran dan tampilan balik "x lusin y potong" dari isian per ukuran. Bagi rata yang tidak pas tetap ditolak dengan
  pesan jelas (perilaku helper lama: pecahan pcs ditolak), sampai owner menentukan lain.
- `production_go:false`.

### D14-6 dan D14-7 (owner ke penulis Claude, 15 Okt 2026, lanjutan)

Lewat pertanyaan pilihan di sesi penulis, sesudah D14-2..D14-5. Pertanyaan dan jawaban ditulis persis.

| No | Pertanyaan penulis | Jawaban owner (verbatim) |
|---|---|---|
| D14-6 | "Kasbon tunai baru ke mandor (sesudah tanggal cutover) ternyata belum bisa dicatat di aplikasi. Yang ada baru kasbon dari saldo awal dan kasbon aksesori. Karena bayar upah duluan sekarang hanya boleh lewat kasbon, perlu saya buatkan pencatatan kasbon tunai?" Pilihan yang dipilih berbunyi: "Catat kasbon tunai ke mandor (kas keluar, jadi piutang mandor), lalu otomatis dipotong di Nota/payroll berikutnya. Kasbon tidak bisa melebihi saldo kas (aturan kas tidak boleh minus)." | "Ya, buatkan (Disarankan)" |
| D14-7 | "Fable minta izin membaca pengaturan API di database Enteng (baca saja) untuk memastikan data internal tidak terbuka langsung ke aplikasi. Diizinkan?" Pilihan yang dipilih berbunyi: "Hanya membaca daftar bagian database yang terbuka lewat API. Tidak mengubah apa pun. Saya tetap mencabut hak langsung yang tidak perlu, jadi aman apa pun hasilnya." | "Ya, baca saja (Disarankan)" |

Akibat (ringkasan penulis):

- D14-6: dibuat pencatatan kasbon tunai ke mandor sesudah cutover (kas keluar menjadi piutang mandor), yang dipotong
  otomatis di payroll berikutnya dan tunduk pada D14-3.
- D14-7 adalah izin untuk auditor Fable. Penulis tidak membaca hosted. Bagi Fable, keputusan ini berlabel
  `UNVERIFIED_OWNER_DECISION` sampai owner menyampaikannya langsung (Pro Max §2.9).

### D14-5a (owner ke penulis Claude, 15 Okt 2026, penegasan D14-5)

Owner membaca laporan penulis yang menyebut uji browser lusin "belum", lalu menulis (persis):

> "Pembagian lusin ke ukuran sudah jadi di layar draf penjualan, tapi belum diuji lewat browser. Untuk itu perlu data
> uji stok 3 ukuran untuk satu SKU. Masa sih ini belum beres padahal gw pernah bahas ini spesifik buat penjualan loh. Lu
> bisa cek di UX demo udah begini loh. Bahkan gw pernah bilang jelas. Gw bahkan bilang misal SKU nya cuma punya 1 ukuran
> kalo tulis selusin ya jadi 12 pt di satu ukuran. Misal gw ketik manual 3/5/4 ya bakal jadi tulisan 1 lusin auto coba
> lu cek dl deh. Aneh gamungkin gw salah ingat coba. Yg lain gw jawab ntar lu fokus sini dl ya 1-1"

Akibat (ringkasan penulis, bukan kata-kata owner):

- Owner benar: aturannya sudah ada di UX demo (`src/SalesPages.tsx`: pilih produk → semua ukurannya masuk dan langsung
  1 lusin dibagi rata; singleton 27 → 12; total baris "x lusin y potong") dan di handoff 28 Sep
  (`docs/cp6-sku-range-audit-delta-writer-handoff-20260928.md`).
- Celah di layar tersambung: ukuran dipilih satu per satu, jadi "seri" hanya berisi ukuran yang sudah ditambahkan. Bila
  baru satu ukuran dari SKU 3 ukuran yang dipilih, 1 lusin masuk 12 ke ukuran itu. Sekarang satu pilihan menambahkan
  semua ukuran SKU itu yang ada stoknya di gudang yang sama, dan seri baru langsung 1 lusin dibagi rata bila pas
  (seperti demo). Bila tidak pas (misalnya 5 ukuran), jumlah dikosongkan dengan pesan.
- Bukti browser sungguhan (desktop dan HP): `CP17_BROWSER_D14_5_SERIES_DOZENS_DESKTOP` / `_MOBILE`.

### D14-8..D14-11 (owner ke penulis Claude, 15 Okt 2026 sekitar 08:08 WIB, jawaban empat pertanyaan laporan r1)

Jawaban atas empat pertanyaan di akhir laporan penulis (pembanding A2, FABLE-012, batal retur kain, upah rework).
Ditulis persis.

| No | Pertanyaan penulis | Jawaban owner (verbatim) |
|---|---|---|
| D14-8 | "Alat pembanding lama kadang mengurutkan daftar fungsi secara acak karena cara mengurutkannya salah. Boleh saya betulkan?" | "Ya, betulkan pembanding lama. Gunakan urutan yang stabil, dengan seluruh anggota, duplikat, definisi, owner, dan hak akses tetap dibandingkan. Simpan bukti sebelum/sesudah. Penyebab dua kegagalan lama tetap OPEN sampai benar-benar terbukti." |
| D14-9 | "Hak panggil langsung ke 82 fungsi penulis data belum dicabut ... Boleh ditunda sampai tahap CP7C?" | "Ya, pencabutan 82 fungsi boleh ditunda ke CP7C, berdasarkan bukti auditor bahwa jalur tersebut tidak dapat dijangkau dari internet. Catat sebagai pekerjaan keamanan yang belum selesai. Jika konfigurasi akses berubah sehingga fungsi itu bisa dijangkau, pencabutannya menjadi prasyarat sebelum jalur tersebut diaktifkan." |
| D14-10 | "Retur kain yang salah jumlah belum bisa dibatalkan ... Perlu dibuatkan tombol batal?" | "Ya, buat tombol batal/koreksi retur kain. Pembalikan stok, hutang/kredit, jurnal, dan HPP yang terdampak harus selesai dalam satu transaksi, dengan riwayat asli tetap tersimpan. Kalau ada transaksi lanjutan yang menghalangi, tampilkan bagian mana yang harus dibetulkan terlebih dahulu." |
| D14-11 | "Upah rework boleh dibayar saat kasus BS-nya belum selesai (masih terbuka atau baru sebagian)?" | "Ya, upah rework boleh dibayar untuk bagian pekerjaan yang sudah selesai, diperiksa, dan disetujui, walaupun keseluruhan kasus BS masih terbuka atau sebagian. Bagian yang belum selesai tetap ditahan. Qty dan upah harus tertaut ke pekerjaan yang jelas, tercatat sekali, dan tidak dibayar ulang saat kasus BS akhirnya ditutup." |

Penutup owner (persis): "Catat sebagai keputusan owner, tambahkan uji untuk perubahan perilaku, dan minta auditor
memverifikasi bagian yang berubah. Ini buat pertanyaan lu ya."

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner):

- D14-8 menggantikan batas D13-11 untuk pembanding lama: pembanding lama sendiri yang diperbaiki (bukan pembanding
  kedua). D13-10 tetap: akar penyebab dua kegagalan lama tetap OPEN dan bukti aslinya tetap disimpan.
- D14-9: FABLE-012 tercatat sebagai pekerjaan keamanan terbuka di CP7C, dengan gerbang: bila Data API mulai
  menjangkau skema `erp`, pencabutan EXECUTE wajib selesai lebih dulu.
- D14-10: langkah batal/koreksi untuk "kain kembali ke gudang" (D14-4).
- D14-11: menggantikan penahanan RWK01 untuk kasus OPEN/PARTIAL, terbatas pada bagian yang selesai, diperiksa dan
  disetujui.
- `production_go:false`.

### D14-12 (owner ke penulis Claude, 15 Okt 2026, sesudah laporan kandidat f1a1ae69)

| No | Pertanyaan penulis | Jawaban owner (verbatim) |
|---|---|---|
| D14-12 | "Saya perlu Bos memutuskan satu hal: tampilan layar penjualan di HP masih lebih panjang daripada demo. Mau saya buat ringkas seperti demo? Ya atau tidak." | "ya" |

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner):

- Blok seri di draf penjualan tersambung (`src/SalesDraftPanel.tsx`, `src/procurement-connected.css`) disusun seperti
  demo: ukuran satu seri berupa kotak kecil berdampingan (juga di HP), satu baris harga/potongan/catatan per ukuran,
  bantuan "lusin + PCS" per seri dalam satu blok yang bisa dibuka. Label semua isian dan tombol tidak berubah; aturan
  lusin (D14-5) tidak berubah.
- Uji browser D14-5 (desktop dan HP) sekarang juga memeriksa bahwa ketiga ukuran seri berada di satu baris.
- Karena `src/` berubah, kandidat baru dikualifikasi ulang pada satu commit dan handoff auditor menunjuk ke commit itu.
- `production_go:false`.

### D14-13 (owner ke penulis Claude, 15 Okt 2026, audit akhir CP1–7)

Pertanyaan owner (persis): "btw kalo udah beres semua di akhir perlu audit cp1-7 lagi gak interkonkesi hubungan
dengan ux semuanya??"

| No | Pertanyaan penulis | Jawaban owner (verbatim) |
|---|---|---|
| D14-13 | "Saya perlu Bos memutuskan: setelah uji ulang auditor selesai, mau saya siapkan paket audit akhir dengan dua fokus di atas? Ya atau tidak." (dua fokus: sambungan antar tahap dari awal sampai akhir; tiap layar UX demo dibandingkan dengan layar tersambungnya) | "ya siapin, sekarang apa tapi?" |

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner):

- Paket audit akhir CP1–7 disiapkan sekarang di `docs/cp7/audit-candidate/cp1-7-final-integration-20261015/`, dikirim
  owner ke auditor **sesudah** uji ulang r1 (Fable, Astra, Sol) selesai dan temuannya ditutup.
- Fokus: (1) sambungan antar tahap pembelian → stok → potong → jahit → laundry → QC → barang jadi → jual → kas,
  hutang, piutang, buku besar; (2) setiap layar UX demo dibandingkan dengan layar tersambungnya (data asli, perilaku
  sama).
- `production_go:false`.

### D14-14 dan D14-15 (owner ke penulis Claude, 15 Okt 2026, sebelum audit akhir)

| No | Pertanyaan penulis | Jawaban owner (verbatim) |
|---|---|---|
| D14-14 | "Saya perlu Bos memutuskan: celah yang sudah pasti ini (layar jahit selesai, jalan upah borongan dan HPP final dari aplikasi, dan menjalankan ulang 60 uji lama) boleh saya kerjakan dulu sebelum audit akhir? Ya atau tidak. Saran saya ya." | "ya yg jelas lu beresin lah" |
| D14-15 | "Boleh saya simpan pekerjaan baru di cabang terpisah (claude/final-gaps-20261015), lalu saya gabungkan setelah uji ulang mereka selesai?" (pilihan: "Ya, cabang terpisah" / "Tidak, cabang yang sama") | "Ya, cabang terpisah (Recommended)" |

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner):

- Dikerjakan sebelum audit akhir, terbatas pada tiga celah yang sudah terbukti (`audit-candidate/cp1-7-final-integration-20261015/CHAIN_MAP.md` §3 butir 1–3):
  layar jahit selesai di WIP & Sewing tersambung; jalan upah borongan dan HPP final dari aplikasi; menjalankan ulang
  workflow `cp7-*` yang basi sejak 8 Okt dan membetulkan data uji yang ditolak penjaga baru tanpa melonggarkan apa pun.
- Pekerjaan itu ada di cabang `claude/final-gaps-20261015`. Cabang `claude/new-session-deapao` tetap pada kandidat uji
  ulang r1 `66baa8e8` (sesudahnya hanya dokumen) sampai uji ulang selesai; sesudah itu cabang baru digabung dan semua
  workflow dikualifikasi ulang pada satu commit.
- Layar mode Enteng (23 menu data contoh) dan layar data induk tidak termasuk "yang jelas": tetap tercatat untuk audit
  akhir dan pemasangan.
- `production_go:false`.

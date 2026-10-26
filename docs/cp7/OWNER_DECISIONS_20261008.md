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

### D14-16 (owner ke penulis Claude, 15 Okt 2026, urutan kirim ke auditor)

Owner (persis): "gw sih gamau suruh dia kerja dulu ya biar ga 2 kali. jadi abis lu beres baru gw suruh"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): paket uji ulang r1 **belum** dikirim ke auditor.
Sesudah tiga celah D14-14 selesai dan dikualifikasi, penulis menyiapkan **satu paket gabungan** (uji ulang r1 + audit
akhir CP1–7 D14-13) pada satu kandidat, supaya auditor bekerja sekali. `production_go:false`.

### D14-17 (owner ke penulis Claude, 15 Okt 2026, arsip uji yang kedaluwarsa)

Konteks (penulis): arsip CI 10392910720 (run 34956212157, 15 Sep 2026) disimpan 30 hari (`retention-days: 30` di
workflow pembuatnya) dan terhapus otomatis 15 Okt 2026; semua workflow CP7 berhenti di langkah pertama (HTTP 410, run
38721795013, 38721797914, 38721801271, 38721804060, 38721806508). Arsip itu tidak bisa dibuat ulang persis karena
pembuatnya bergantung pada arsip 10320611163 yang juga sudah terhapus. 14 arsip lain yang masih hidup disalin utuh ke
artifact 11967162735 (run 38723163085, disimpan sampai 13 Jan 2027).

Penulis bertanya: "boleh saya ganti dengan cara ini? Ya atau tidak." — yaitu mengganti arsip yang hilang dengan daftar
tabel yang diambil ulang di setiap uji oleh fungsi beku yang sama, tepat sebelum langkah U, dengan pemeriksaan X yang
tidak diubah, jumlah 208 tabel wajib, dan nama-nama tabel dikunci sesudah pengambilan pertama; batasnya ditulis untuk
auditor (tidak bisa lagi dibuktikan sama persis dengan daftar 15 Sep).

Owner (persis): "kok bisa hilang?" lalu "kalo ganti bakal bisa aman gak?" lalu "ya"

Akibat untuk penulis: `scripts/cp6_pre_u_inventory.py` dipakai bila arsip tidak ada; jalur lama yang dikunci SHA-256
tetap dipakai bila arsip ada. Batas dicatat di paket audit akhir. `production_go:false`.

### D15-1 .. D15-4 (owner atas pertanyaan Fable, 16 Okt 2026; dicatat Fable, diteruskan owner ke penulis)

Sumber: `audit/fable_cp17_combined/OWNER_DECISIONS_TO_AUDITOR_20261016.md` di cabang
`audit/fable-cp1-7-combined-dfab13bf-20261015` (commit 8677a399), dicatat Fable sesudah laporannya dikunci. Owner
meneruskan teks siap-tempel Fable ke penulis pada 16 Okt 2026. Teks owner di bawah disalin persis dari berkas itu;
oracle uji ulang Fable ada di berkas yang sama dan tidak diubah penulis.

| No | Pertanyaan (temuan) | Jawaban owner (persis) |
|---|---|---|
| D15-1 | D14-3, saldo kas "tanggal mana pun" menurut tanggal apa? (FABLE-013) | "Ya, untuk aturan kas minus, ikuti rekomendasi Fable: periksa saldo harian per rekening menurut tanggal ekonomi dan tanggal buku/pengakuan. Tolak transaksi jika salah satunya menjadi minus. Terapkan juga pada detektor dan koreksi/pembalikan, tanpa mengubah tanggal asli atau membuka ulang periode tertutup secara otomatis." |
| D15-2 | Layar uang dan absensi di mode Enteng (FABLE-015) | "sembunyikan begitu terhubung langsung muncul, doesnt matter juga kalau mau langsung muncul karena gabakal dipakai juga jadi ga kerja 2 kali sih klo mau munculin" |
| D15-3 | Data master dan tarif mandor: layar atau prosedur admin? (FABLE-017) | "dibuatkan layar tapi jangan simple banget juga, sedeng lah muat info dan fitur yg dibutuhkan" |
| D15-4 | Buka ulang PO yang terlanjur selesai (FABLE-014) | "Tombol buka ulang PO dibuat, dengan penghalang seperti fitur koreksi lain" |

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner):
- D15-1: penjaga kas menilai keadaan **akhir** satu perintah (bukan keadaan setengah jalan) dan memeriksa dua dasar tanggal:
  tanggal ekonomi dan tanggal buku. Ini juga menyelesaikan SOL-R1-001 (koreksi sah yang ditolak di tengah jalan) tanpa
  melonggarkan penolakan saldo minus sungguhan. Detektor memeriksa kedua dasar tanggal.
- D15-2: di mode Enteng, layar uang dan absensi yang belum tersambung disembunyikan. Menyambungkannya ke Enteng
  membutuhkan pemasangan lapisan CP7 di Enteng (CP7C, masih ditahan D13-9a), jadi sampai saat itu layar tetap
  tersembunyi. Tidak boleh ada angka contoh tanpa label di mode Enteng.
- D15-3: layar data master tingkat menengah untuk pelanggan, supplier/vendor, mandor, gudang/lokasi, kain, aksesori,
  dan tarif upah mandor (model × komponen kerja × mandor, dengan tanggal berlaku), dengan riwayat dan hak akses.
- D15-4: tombol buka ulang PO memanggil `erp.reopen_production_order` lewat fasad CP7 dengan penghalang yang disebut di
  layar.
- `production_go:false`.

### D15-5 dan D15-6 (owner ke penulis Claude, 16 Okt 2026, jawaban dua pertanyaan penulis)

Pertanyaan penulis: (1) "Transaksi baru (pembelian, penyesuaian stok, penjualan) tidak boleh bertanggal sebelum tanggal
mulai pakai aplikasi di Enteng: ya atau tidak?" (FABLE-011). (2) "Cara membuat PO harian. Pilihan A: PO dibuat otomatis
waktu Buat Potongan, seperti demo. Pilihan B: PO dibuat dulu di layar sendiri." (SOL-R1-002)

Owner (persis):

"1. Ya, untuk transaksi operasional baru. Gunakan tanggal cutover resmi yang saya sahkan dalam WIB, bukan tanggal pertama login atau uji coba. Pengamannya wajib di server.
Data sebelum cutover masuk melalui saldo awal/migrasi. Invoice terlambat yang merujuk penerimaan saldo awal, pelunasan sesudah cutover, serta koreksi dokumen lama tetap memakai jalur resminya. Tanggal asli tetap tersimpan dan efeknya tidak boleh dihitung dua kali.
2. Pilih A — PO otomatis dari Buat Potongan, seperti alur demo. Pengguna cukup mengisi pekerjaan potong; sistem membuat PO terkait dan menampilkan nomornya untuk pelacakan.
Saat disahkan, pembuatan PO dan posting potongan harus atomik. Pengiriman ulang memakai UUID yang sama harus mendapatkan hasil yang sama, tanpa PO atau stok ganda. Draf tetap belum memengaruhi stok maupun keuangan.

Catat kedua keputusan dan uji batas tanggal, jalur saldo awal, kegagalan di tengah proses, serta pengiriman ulang. langsung kerjain yg lu bilang juga ye"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner):
- D15-5 (lantai tanggal cutover, FABLE-011): tanggal cutover resmi disahkan owner di aplikasi (tanggal WIB), disimpan di
  server dengan riwayat. Server menolak transaksi operasional baru yang bertanggal sebelum tanggal itu. Jalur saldo awal/
  migrasi, invoice terlambat atas penerimaan saldo awal, pelunasan sesudah cutover, dan koreksi dokumen lama tetap lewat
  jalur resminya; tanggal asli disimpan, efek tidak dihitung dua kali. Uji: tepat di batas tanggal, sehari sebelum,
  jalur saldo awal, gagal di tengah proses, dan pengiriman ulang.
- D15-6 (PO harian, SOL-R1-002): Buat Potongan membuat PO terkait secara otomatis saat potongan disahkan, dalam satu
  transaksi dengan posting potongan, dan menampilkan nomornya. Pengiriman ulang dengan UUID yang sama memberi hasil yang
  sama tanpa PO atau stok ganda. Draf tidak memengaruhi stok atau keuangan. Uji: gagal di tengah proses (tidak ada PO
  yatim, tidak ada stok bergerak) dan pengiriman ulang.
- `production_go:false`.

## Keputusan owner 16 Okt 2026 sesudah audit r2 (D16-1)

### D16-1 (owner ke auditor Fable, sesudah laporan r2 Fable dikunci; dicatat Fable di
`audit/fable_cp17_r2/OWNER_DECISION_TO_AUDITOR_20261016_UNHIDE.md`, commit `f2758f39`, cabang
`audit/fable-cp1-7-r2-2e9d6a46-20261016`)

Owner (persis): "selesain biar gausa sembunyiin"

Tafsiran Fable (ditulis Fable sebagai tafsiran, "dikembalikan ke owner bila keliru"): menggantikan D15-2 untuk mode
Enteng. Layar yang sekarang disembunyikan di Enteng diselesaikan dan disambungkan, bukan disembunyikan: 11 menu yang
sudah tersambung di mode uji dinyalakan untuk Enteng (Penjualan & Invoice, Semua Invoice, Retur Penjualan, Pembayaran
Pelanggan, Ringkasan Keuangan, Kas & Bank, Piutang Pelanggan, Payroll & Kasbon, Absensi & Rate Harian, Jurnal & Transaksi
Lain, Laporan & Tutup Buku; juga Susun Nota FG yang di Enteng berupa layar batas), dan 6 menu yang belum punya layar
tersambung dibuatkan (Ringkasan Gudang, Riwayat Pelanggan, Reminder, Pengaturan ERP, Tutup Periode, Audit Trail),
ditambah layar pool HPP absensi. Menu yang isinya sama dengan menu lain boleh digabung dengan persetujuan owner. Oracle
uji ulang Fable ditetapkan di berkas itu sebelum pekerjaan dibuat.

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): tabel aktivasi mode Enteng tidak lagi memakai HIDDEN
untuk menu yang selesai; layar tersambung yang sama dengan mode uji dipakai di Enteng; enam layar yang belum ada dan
layar pool HPP absensi dibuat dengan kasus Native, race, HTTP dan browser desktop + HP; uji browser juga memakai build
mode Enteng terhadap database sekali pakai. Layar ini baru berfungsi di Enteng sesudah lapisan CP7 terpasang (CP7C
tetap ditahan, D13-9a). `production_go:false`.

### D16-2 (owner ke penulis Claude, 17 Okt 2026, jawaban pertanyaan penulis soal tarif mandor yang naik di tengah PO)

Pertanyaan penulis: "Tarif mandor naik di tengah PO: (A) sisa PO itu tetap tarif lama, tarif baru untuk PO berikutnya
(aturan sekarang); (B) sisa PO ikut tarif baru mulai tanggal berlakunya."

Owner (persis): "bisa gak dikasih pilihan harga lama apa baru, kadang bisa random soalnya"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): saat mencatat jahit selesai, bila tarif mandor yang
berlaku pada tanggal jahit berbeda dari tarif yang terkunci untuk PO itu, layar menampilkan keduanya dengan nilai
upahnya dan pengguna memilih salah satu per pencatatan, dengan alasan. Pilihan disimpan di catatan upah dan riwayat;
upah yang sudah tercatat tidak berubah; Nota, payroll dan HPP mengikuti tarif yang dipilih. Aturan Native sekarang
selalu memakai tarif terkunci PO (`erp.po_work_component_snapshots`, satu baris per PO × komponen × SKU), jadi ini butuh
perubahan Native yang dideklarasikan dan diuji. Siapa yang boleh memilih tarif baru ditanyakan ke owner.
`production_go:false`.

### D16-3 (owner ke penulis Claude, 17 Okt 2026, lanjutan D16-2)

Owner (persis): "mungkin setelah beberapa waktu kasih tombol biar nanti bisa yaudah pake yg baru terus kali ya."

Akibat untuk penulis (tafsiran penulis, bukan kata-kata owner; dikoreksi bila keliru): selain memilih tarif per
pencatatan (D16-2), ada tombol per PO "pakai tarif baru seterusnya". Sesudah ditekan, pencatatan jahit selesai berikutnya
untuk PO itu memakai tarif baru tanpa ditanya lagi. Upah yang sudah tercatat tidak berubah. Tombol mencatat siapa,
kapan, dan alasannya di riwayat. Siapa yang boleh menekannya ditanyakan ke owner bersama pertanyaan D16-2.
`production_go:false`.

### D16-4 dan D16-5 (owner ke penulis Claude, 17 Okt 2026, jawaban dua pertanyaan penulis)

Pertanyaan penulis: (1) "Siapa yang boleh memilih tarif baru dan menekan tombol itu? (A) semua orang yang boleh mencatat
jahit selesai; (B) hanya Owner/Admin." (2) "Menu 'Tutup Periode' dan 'Laporan & Tutup Buku' sama-sama untuk tutup buku:
(A) digabung jadi satu menu; (B) tetap dua menu."

Owner (persis): "B pokoknya kalo belom dipencet bakal ada 2 pilihan lalu klo dah dipencet udah baru terus pas peralihan
biar ga kagok, kedua Pilih A — gabungkan menjadi satu menu “Laporan & Tutup Buku” di Keuangan. Penutupan periode menjadi
bagian/tab di dalamnya. Hak melihat laporan dan hak menutup buku tetap terpisah. Arsip, riwayat, dan pengaman penutupan
tetap lengkap; tautan lama diarahkan ke halaman gabungan."

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner):
- D16-4 (tarif, lanjutan D16-2/D16-3): hanya Owner/Admin yang boleh memilih tarif baru dan menekan tombol "pakai tarif
  baru seterusnya". Sebelum tombol ditekan, Owner/Admin melihat dua pilihan saat mencatat jahit selesai; peran lain
  mencatat dengan tarif lama PO (sesuai pilihan B yang ditanyakan). Sesudah ditekan, semua pencatatan berikutnya untuk PO
  itu memakai tarif baru.
- D16-5 (menu): "Tutup Periode" digabung ke "Laporan & Tutup Buku" di Keuangan; penutupan periode menjadi tab di
  dalamnya. Hak melihat laporan dan hak menutup buku tetap terpisah. Arsip, riwayat dan pengaman penutupan tetap
  lengkap. Rute lama "Tutup Periode" diarahkan ke halaman gabungan.
- `production_go:false`.

## Keputusan owner 19 Okt 2026 sesudah audit r3 (D17-1)

### D17-1 (owner ke penulis Claude, 19 Okt 2026 WIB, jawaban pertanyaan penulis soal kecepatan layar analisis)

Pertanyaan penulis: "Saya perlu Bos memutuskan soal layar analisis yang lambat (Sol KNOWN-P19-DIRECT-LATENCY: 'Ambil
analisis ERP terbaru' 6–8 detik untuk 300 produk, dengan angka keuangan 7–8 detik untuk 100 produk, target 3 detik):
A. dikerjakan sekarang di putaran ini (paket uji ulang mundur sekitar 1–2 hari); B. paket uji ulang dikirim dulu,
kecepatan dikerjakan putaran berikutnya."

Owner (persis): "A beresin aja, mau gw tinggal tidur soalnya"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): kecepatan analisis langsung dan analisis dengan angka
keuangan dikerjakan di r4 sebelum paket uji ulang. Batas 8 detik, pemeriksaan sumber/otoritas/hash/kelengkapan dan
keputusan 7 Okt (pekerjaan berat boleh di latar belakang sebagai pengecualian yang dicatat; target 3 detik tidak ditandai
tercapai kalau belum) tetap berlaku. `production_go:false`.

### D17-2 (owner ke penulis Claude, 19 Okt 2026 WIB, jawaban pertanyaan penulis sesudah kualifikasi r4)

Pertanyaan penulis: "Saya perlu Bos memutuskan: kirim paket ke auditor sekarang, lalu kecepatan dengan angka keuangan
dikejar sesudahnya (saran saya)? Atau kecepatannya dikejar dulu, dan pengiriman paket ditunda?"

Owner (persis): "Auditor dl ya, inget lu punya tugas ini di next turn ya"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): paket uji ulang r4 pada kandidat `663f6fae` dikirim ke
auditor tanpa menunggu. Kecepatan analisis langsung dengan angka keuangan (100 target 4,57–5,92 detik pada runner
kualifikasi, target 3 detik; `docs/cp7/p19/P19_R4_05_DIRECT_LATENCY.md`) adalah tugas penulis berikutnya, di cabang
baru dari `claude/new-session-deapao`; kandidat yang sedang diaudit tidak diubah. Batas 8 detik, pemeriksaan
sumber/otoritas/hash/kelengkapan dan keputusan 7 Okt tetap berlaku. `production_go:false`.

### D17-3 (owner ke penulis Claude, 19 Okt 2026 WIB, cara kirim pengingat)

Owner sebelumnya: "pikirin ya aplikasi buat kirim ke wanya ya", lalu "ada app lain yg ngirim ke diri sendiri". Pertanyaan
penulis: "Saya perlu Bos memutuskan: pengingat ke HP Bos sendiri lewat Telegram (saran saya) atau lewat CallMeBot di
WhatsApp?"

Owner (persis): "yaudah desain callmebot buat gw"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): pengingat dikirim ke WhatsApp owner sendiri lewat
CallMeBot (gratis; pihak ketiga; situsnya menulis "hanya untuk pemakaian pribadi"). Yang diminta sekarang desain:
`docs/cp7/WA_CALLMEBOT_DESIGN_20261019.md`. Pengiriman nyata butuh pengirim terjadwal di server, jadi pemasangannya ikut
CP7C (ditahan, D13-9a). Kunci CallMeBot tidak pernah diminta atau dikirim lewat chat. `production_go:false`.

### D17-4 (owner ke penulis Claude, 19 Okt 2026 WIB, tanggapan atas desain CallMeBot)

Desain pertama penulis hanya mengirim ringkasan dua kali sehari.

Owner (persis): "gw maunya tiap kena safety stock dll auto kirim terus, yg sehari 2kali itu juga mau kan ringkasan"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): dua jenis kiriman. (1) Pesan langsung setiap kali sebuah
kondisi baru kena (stok di bawah stok minimum/titik pesan ulang, kekurangan kain/aksesori, tagihan jatuh tempo, dan
sejenisnya), otomatis tanpa ditekan. (2) Ringkasan dua kali sehari tetap ada. Penulis membaca "auto kirim terus" sebagai
"langsung dikirim otomatis"; selama kondisinya belum beres, ia ikut di setiap ringkasan, dan pesan langsung ulangan
mengikuti jeda yang bisa diatur di aplikasi. Desain: `docs/cp7/WA_CALLMEBOT_DESIGN_20261019.md`.

### D17-5 (owner ke penulis Claude, 19 Okt 2026 WIB, tanggapan atas desain D17-4)

Desain D17-4 penulis: pesan langsung untuk tujuh pemicu (stok di bawah minimum/titik pesan ulang, kekurangan kain/aksesori,
target produksi, tagihan dan piutang jatuh tempo) yang dicek tiap 5 menit, ditambah ringkasan dua kali sehari.

Owner (persis): "bukan cuma itu, semua hal yg masuk ke reminder harus langsung forward wa biar realtime
triger lu pasti lebih gampang kan"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): setiap hal yang muncul di Pengingat diteruskan ke WhatsApp
owner saat itu juga, bukan hanya tujuh pemicu. Yang tercatat sebagai baris di tabel pengingat diteruskan lewat trigger
(hitungan detik); yang muncul karena waktu (jatuh tempo, pengingat pribadi yang waktunya tiba) dan stok dicek tiap menit,
tanpa trigger di tabel transaksi gudang. Ringkasan dua kali sehari tetap. Desain:
`docs/cp7/WA_CALLMEBOT_DESIGN_20261019.md`.

### D17-6 (owner ke penulis Claude, 19 Okt 2026 WIB, jawaban "mau saya mulai buat sekarang?")

Pertanyaan penulis: "Saya perlu Bos memutuskan: mau saya mulai buat sekarang? Pengujiannya pakai server CallMeBot palsu, jadi
tidak ada pesan sungguhan dan tidak dipasang ke Enteng. Ya atau tidak?"

Owner (persis): "karna safety stock dll bakal masuk reminder anyway. ya boleh pake yg palsu gw perlu kasi no hape?"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): penulis membangun penerusan pengingat ke WhatsApp sesuai
`docs/cp7/WA_CALLMEBOT_DESIGN_20261019.md`, diuji dengan server CallMeBot palsu di CI. Pengingat stok (safety stock dan
sejenisnya) adalah pengingat biasa dan lewat jalur yang sama. Nomor HP tidak diminta: uji memakai nomor contoh; nomor asli
dan kunci diisi owner sendiri di layar aplikasi saat pemasangan (CP7C, ditahan D13-9a), tidak lewat chat. Tidak ada pesan
sungguhan dan tidak ada pemasangan ke Enteng.

### D17-7 (owner ke penulis Claude, 20 Okt 2026 WIB, bawaan analisis otomatis untuk WhatsApp)

Penjelasan penulis sebelumnya: analisis otomatis menghitung ulang kekurangan produksi dan kain yang perlu dibeli di server
secara berkala, hanya pada jam kerja dan hanya kalau data berubah; setiap hasil disimpan 7 hari; bawaan diusulkan tiap 4
jam supaya database gratis tidak cepat penuh, dan angkanya bisa diubah owner di layar Sambungan WhatsApp.

Owner (persis): "Ya 4 jam, tapi kan analisis jalan tiap terjadi sesuatu di background kan? Atau gimana sih"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): bawaan analisis otomatis 240 menit, dibuat dan diuji
bersama pemasangan CP7C (kandidat r6 `b1649535` masih 60 menit). Pertanyaan owner dijawab di chat: stok di bawah minimum,
piutang dan tagihan jatuh tempo, dan pengingat pribadi dicek server tiap menit tanpa analisis; hanya kekurangan produksi dan
kain yang perlu dibeli yang menunggu analisis, dan setiap kondisi dicek ulang ke data terbaru sebelum pesannya dikirim.

### D17-8 (owner ke penulis Claude, 20 Okt 2026 WIB, safety stock barang jadi)

Penjelasan penulis sebelumnya: kekurangan produksi menunggu analisis besar; peringatan "stok barang jadi menyentuh titik
pesan ulang" belum dibuat.

Owner (persis): "Bro masalahnya safety stock buat barang jadi kan bakal adjust terus dan angkanya kan snap shot kan, setiap
ada perubahan dia baru hitung ulang safety stock kan? Itu bakal jalan di background simple. Jadi kalo kena safety stok itu
ya sama aja kek hitungan safety stock barang mentah dong?? Semua kan pake rumus kalo kita punya barang, gimana dah?"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): safety stock / titik pesan ulang barang jadi dihitung
dengan rumus dari data barang itu sendiri dan dihitung ulang di belakang setiap ada perubahan pada barang itu; stok sekarang
dibandingkan dengan angka itu tiap menit seperti stok kain, dan yang kena langsung diteruskan ke WhatsApp, tanpa menunggu
analisis besar. Fakta yang diluruskan penulis di chat: minimum kain saat ini angka manual di data master kain; untuk barang
jadi ERP sudah menyimpan tempat angka titik pesan ulang manual dan rumus rekomendasinya, tetapi rumus itu belum disambungkan
ke data penjualan (`erp_get_fg_stock_explainability_v1` menjawab `BELUM_CUKUP_DATA`) dan belum ada layarnya.

### D17-9 (owner ke penulis Claude, 20 Okt 2026 WIB, sambungkan rumus stok)

Usulan penulis: `docs/cp7/wa/PROPOSAL_SAFETY_STOCK_R6_20261020.md` (safety stock barang jadi, kain dan aksesori dengan rumus
pakar, peringatan WA tiap menit, sebelum paket r6 dikirim). Owner sebelumnya: "Lama kirim supplier cenderung gak ada data ke
record pula".

Owner (persis): "Konek in lah rumus rumus itu penting loh, kenapa writer gak hubungi itu sama sekali ya??"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): usulan disetujui; rumus safety stock/titik pesan ulang
disambungkan ke data ERP untuk barang jadi, kain dan aksesori, lalu ke Pengingat sistem dan WA, sebelum paket r6 dikirim.
Lama kirim supplier menjadi isian per bahan karena tidak tercatat. Penulis menjelaskan di chat mengapa rumus belum
tersambung (riset 28 Sep: "tidak aktif otomatis", lalu tidak diangkat lagi ke owner).

### D17-10 (owner ke penulis Claude, 20 Okt 2026 WIB, aksesori pakai minimum manual, satu judul kain)

Penjelasan penulis sebelumnya (chat): tiga beda dari usulan D17-9 (`docs/cp7/wa/STOCK_FORMULA_FG_DESIGN.md`): (1) kain yang
memakai rumus diberi judul sendiri "Stok kain menipis", terpisah dari "Stok kain di bawah minimum" — pilihan A terpisah
(dibuat) atau B digabung; (2) kebutuhan aksesori dari rencana produksi tidak diteruskan; (3) isian lama kirim di Master Data
dan Gudang. Lalu jawaban atas pertanyaan owner soal BOM aksesori per judul besar (kancing per warna, sleting per ukuran,
dibeli mandor lewat nota) dan isi HPP (kain kantong, aksesori).

Owner (persis): "aksesoris pake batas minimum manual aja nanti gw kasih tau ke lu minimal order tuh berapa pcs dan lama
kirim dari cina ya. tar bantu hitungin stok minimum harus berapa. ini karena harus bulk order moq rumus ga penting keknya.
lalu untuk judul itu merge aja yg stok menipis atau di bawah minimum"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner):
- Aksesori tidak memakai rumus titik pesan ulang. Pengingat aksesori hanya dari batas minimum yang diisi manual per
  aksesori; kosong berarti tidak diingatkan. Owner nanti memberi tahu jumlah pesanan minimum (MOQ, pcs) dan lama kirim dari
  Cina; penulis membantu menghitung batas minimumnya, lalu angkanya diisi di aplikasi.
- Beda (1): pilihan B. Kain yang memakai rumus masuk ke pengingat yang sudah ada "Stok kain di bawah minimum", memakai
  angka rumus bila minimum manual kosong (kalimat usulan bagian 3 yang disetujui di D17-9). Tidak ada lagi judul terpisah
  "Stok kain menipis".
- Beda (2) dan pertanyaan BOM per warna/ukuran, laporan aksesori mandor, dan waktunya belum dijawab owner; tidak dikerjakan.

### D17-11 (owner ke penulis Claude, 20 Okt 2026 WIB, baca ERP lama untuk pemakaian aksesori)

Pertanyaan penulis (chat): "Saya perlu Bos memutuskan: boleh saya baca data ERP lama untuk angka pemakaian itu? Hanya
dibaca, tidak diubah apa pun. Ya atau tidak?" (pemakaian aksesori per bulan, untuk menghitung batas minimum D17-10).

Owner (persis): "ya"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): penulis membaca proyek ERP lama (`vlxdhpkjeevubjxexnfo`)
dengan kueri SELECT saja untuk pemakaian aksesori per bulan; tidak ada yang diubah. Angka dari data produksi tidak masuk repo
(repo publik) atau artifact; hasilnya disampaikan ke owner di chat dan disimpan di folder kerja sementara penulis.

Sesudahnya (penulis): konektor Supabase sesi ini tidak terhubung ke proyek mana pun, jadi tidak ada yang dibaca. Owner
(persis): "erp lama mah gada datanya orang ini pertama kali wkwk". Akibat (ringkasan penulis): ERP lama tidak menyimpan
pemakaian aksesori; batas minimum dihitung dari perkiraan pemakaian yang diberikan owner, lalu diperbaiki dengan pemakaian
nyata yang diukur ERP sesudah dipakai.

### D17-12 (owner ke penulis Claude, 20 Okt 2026 WIB, isian hitung minimum aksesori di aplikasi)

Penjelasan penulis sebelumnya (chat): untuk menghitung batas minimum aksesori penulis meminta per aksesori MOQ, lama kirim
dari Cina, dan perkiraan pemakaian per bulan; contoh hitung: pemakaian selama menunggu kiriman + cadangan untuk kiriman
telat; MOQ hanya mengubah jumlah pesan. Pertanyaan: cadangan dipukul rata 2 minggu, ya atau tidak.

Owner (persis): "itu nanti lu bikin slot untuk diisi aja in app kan?"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): angka-angka itu diisi di aplikasi, bukan dikirim ke
penulis. Panel aksesori (Owner/Admin) mendapat isian per aksesori: MOQ (pcs), lama kirim (hari), perkiraan pemakaian per
bulan, dan cadangan (hari). Aplikasi menghitung batas minimum = pemakaian per hari (perkiraan per bulan / 30) × (lama kirim +
cadangan), dibulatkan ke atas, dan memakainya untuk pengingat "Stok aksesori menipis". Batas minimum yang diketik langsung
tetap bisa dipakai dan menang atas hitungan. Cadangan juga isian (tidak ada angka bawaan dari penulis); pertanyaan "2 minggu"
gugur. Pemakaian nyata yang diukur ERP ditampilkan di samping perkiraan, tidak dipakai otomatis (D17-10: tanpa rumus).

### D17-13 (owner ke penulis Claude, 20 Okt 2026 WIB, periksa CP7 untuk penundaan yang diputuskan penulis sendiri)

Percakapan sebelumnya (chat): owner bertanya kenapa rumus safety stock, yang masuk lingkup CP7, baru dibuat sekarang
("iya itu tapi scope cp7 begok, lu kenapa baru bikin sekarang"). Penulis mengakui: catatan riset 28 Sep
(`docs/cp7/benchmark-decisions.md`) menunda safety stock statistik ("kelak", "tidak aktif otomatis") atas pilihan penulis
sendiri, tanpa bertanya ke owner dan tanpa dicatat sebagai pekerjaan terbuka. Pertanyaan penulis: "Saya perlu Bos
memutuskan: boleh saya periksa seluruh daftar pekerjaan CP7 untuk mencari hal lain yang saya tunda sendiri tanpa keputusan
Bos, lalu laporkan daftarnya? Ya atau tidak?"

Owner (persis): "ya"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): penulis memeriksa dokumen dan kode CP7 untuk setiap hal yang
ditunda, dimatikan, atau dikecilkan atas pilihan penulis sendiri (bukan keputusan owner yang tercatat), lalu melaporkan
daftarnya ke owner. Laporan saja; tidak ada yang dibuat atau diubah sebelum owner memutuskan per butir.

### D17-14 (owner ke penulis Claude, 20 Okt 2026 WIB, jawaban atas daftar D17-13 dan serah-terima ke Astra)

Pertanyaan penulis (chat): "1. Tiga hal di Kelompok 1 saya betulkan dulu sebelum paket dikirim ke auditor? Ya atau tidak?
2. Untuk Kelompok 2, boleh saya susun usulan urutan kerjanya? Ya atau tidak?" (daftar:
`docs/cp7/D17_13_PENUNDAAN_PENULIS_20261020.md`).

Owner (persis):

> Catat semuanya sebagai pekerjaan yang belum selesai dan lanjutkan perbaikannya. Keuangan, stok, dan HPP tetap prioritas utama.
> Arahan saya:
>
> 1. WhatsApp: seluruh jenis pengingat harus tercakup, termasuk gaji, laundry, nota aksesori mandor, dan saldo awal. Pengiriman mengikuti penerima serta hak akses, punya status pengiriman, dan pengaman duplikasi.
> 2. Proses di server: analisis, laporan bisnis, dan pengingat harus tetap berjalan ketika halaman ditutup. Saat dibuka kembali, pengguna bisa melihat progres atau hasilnya. Buktikan dengan menutup browser saat proses berlangsung.
> 3. Kelipatan produksi: sediakan pengaturannya di aplikasi, lengkap dengan satuan dan validasi. Jangan menulis bahwa saya bisa mengisi sesuatu yang belum tersedia. Nilai kebijakan yang belum disepakati jangan dikarang.
> 4. Retur transaksi lunas dan koreksi mandor setelah dijahit: sediakan jalur penyelesaian yang benar. Retur harus jelas menjadi pengembalian uang atau saldo kredit. Koreksi mandor harus menangani dampaknya ke upah, nota, payroll, dan HPP. Riwayat tetap tersimpan; kalau perlu membalik dokumen terkait, tampilkan langkahnya dengan jelas.
> 5. Pembayaran supplier: satu transfer harus bisa dialokasikan ke beberapa penerimaan/tagihan. Jumlah alokasi harus cocok dengan pembayaran, kas keluar tercatat sekali, dan pembatalan/koreksinya tetap konsisten.
> 6. Urut dan saring: perbaiki kedelapan layar agar berlaku atas seluruh hasil pencarian sebelum dibagi halaman. Jumlah hasil dan perpindahan halaman harus konsisten.
> 7. Target produksi: tambahkan cadangan yang memperhitungkan variasi permintaan dan waktu tunggu. Pastikan stok, WIP, dan rencana yang sudah ada tidak dihitung dua kali. Ajukan hanya parameter kebijakan yang memang masih membutuhkan keputusan saya.
> 8. Model perkiraan: model yang terbukti lebih baik lewat pengujian harus benar-benar bisa dipakai. Baseline tetap menjadi cadangan ketika bukti/data belum cukup. Produk baru dapat memakai pola produk serupa dengan dasar pemilihan yang jelas dan ketidakpastian yang terlihat.
> 9. Skala pabrik: buktikan analisis sekitar 3.600 barang dengan angka keuangan, HPP, dan pembanding periode lalu. Tetap kejar kecepatan maksimal tanpa menghilangkan isi analisis atau mengubah hasil hitung.
>
> Mulai dari jalur uang, stok, HPP, dan koreksi transaksi. Jaga kandidat yang sedang diaudit tetap beku; kerjakan perubahan ini di cabang terpisah.
> Untuk setiap butir, catat perubahan, bukti pengujian, dan batas yang masih tersisa. Pertahankan pemeriksaan yang ketat. Status selesai harus berarti kebutuhan saya terpenuhi dan alurnya terbukti berjalan.Ya. Betulkan ketiga hal Kelompok 1 sebelum paket dikirim ke auditor. Buktikan seluruh jenis pengingat tercakup di WA, laporan dan pengingat tetap diproses saat browser ditutup, serta pengaturan kelipatan produksi benar-benar tersedia dan berfungsi.
>
> 1. Ya. Susun urutan Kelompok 2, lalu langsung kerjakan bagian yang kebutuhannya sudah jelas. Prioritaskan retur transaksi lunas, koreksi mandor setelah dijahit, dan pembayaran supplier lintas penerimaan karena menyangkut uang, stok, serta HPP. Berikutnya filter/urut seluruh data, perencanaan, dan analisis skala pabrik. Minta keputusan hanya untuk nilai kebijakan atau pilihan bisnis yang memang belum ditetapkan.
>
> Untuk 21 kegagalan CP6 dan empat kasus layar, tetap tampilkan sebagai gagal beserta pembanding versi sebelumnya. Sertakan pemetaan uji pengganti untuk layar yang sudah dipensiunkan agar auditor bisa menilai cakupannya. Pemeriksaan jangan dilonggarkan.
> Siapkan paket pada satu versi yang jelas, dengan daftar temuan tertutup dan masih terbuka. “Tidak ada kegagalan baru” belum berarti seluruh kebutuhan selesai. ini jawabannya karna limit lu mepet siapin handover buat astra

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): semua butir D17-13 dicatat sebagai pekerjaan belum selesai
di `docs/cp7/OPEN_WORK_D17_14_20261020.md`, dengan urutan dan syarat selesai dari kata-kata owner di atas. Pekerjaan
dilanjutkan oleh Astra (serah-terima `docs/cp7/handoff/HANDOFF_ASTRA_WRITER_D17_14_20261020.md`) di cabang terpisah;
kandidat yang diaudit (`55c885d1`) tetap beku. Paket r6 belum dikirim.

### D17-15 (owner ke penulis Claude, 20 Okt 2026 WIB, status hasil potong tidak wajar)

Pertanyaan owner sebelumnya: "boleh cek analisis hasil potongan yang ga wajar itu udah ada apa belom?" Jawaban penulis:
sudah ada panel penilaian potong di halaman Potongan (hasil nyata per roll dibanding rentang empiris; di luar rentang =
"Periksa kejadian ini"), tetapi manual per potongan, perlu riwayat cukup, riwayat per akun, tanpa daftar dan tanpa
peringatan. Pertanyaan penulis: "hasil potong tidak wajar dicek otomatis untuk seluruh pabrik, muncul di Pengingat dan
WA, lalu ditambahkan ke daftar kerja Astra? Ya atau tidak?"

Owner (persis): "gaperlu wa, cuma perlu pas udah selesai dipotong keluar statusnya. per jenis barang"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): tidak ke WA (dan tidak sebagai pengingat). Begitu
potongan selesai, statusnya keluar sendiri di potongan itu (wajar / lebih sedikit / lebih banyak dari biasanya / riwayat
belum cukup), dengan rentang wajar per jenis barang dari riwayat pabrik. Dicatat sebagai OW-16 di
`docs/cp7/OPEN_WORK_D17_14_20261020.md`. Arti "jenis barang" (penulis menafsirkan: model/pola produk yang dipotong)
ditanyakan ke owner.

Lanjutan. Pertanyaan penulis: ""jenis barang" maksudnya per model celana (misalnya Chino dan Cargo dihitung terpisah), ya
atau tidak? Kalau tidak, sebutkan pembagiannya."

Owner (persis): "per jenis bahan dengan pola dong kan dia hasilin ukurannya range juga"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): rentang wajar dikelompokkan per pasangan jenis bahan +
pola, dan dinilai untuk rentang ukuran yang dihasilkan pola itu (bukan satu angka total), karena satu pola menghasilkan
beberapa ukuran.

Lanjutan kedua. Penjelasan penulis sebelumnya (chat): butir 2 yang perlu dibuat, "Penilaian per rentang ukuran yang
dihasilkan pola. Sekarang yang dinilai hanya satu angka total pcs per roll."

Owner (persis): "nomor 2 emang dari total tapi dia harus lihat dari range ukuran dong, pola jumbo apa kecil"

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): yang dinilai tetap total pcs hasil potong, tetapi rentang
wajarnya dibedakan menurut rentang ukuran pola (pola ukuran jumbo dan pola ukuran kecil punya rentang wajar sendiri), di
dalam kelompok jenis bahan + pola. Ini mengoreksi ringkasan lanjutan pertama di atas ("bukan satu angka total").

### Arahan kerja paralel (owner ke Codex, 22 Okt 2026 WIB)

Owner (persis): "siap kan diri lu abis ini lu akan bagi tugas sama claude pastikan lu bikin kerjaannya jangan tabrak tabrak ya biar nanti mergenya gampang, lu liat poin poin itu mungkin kan buat kerjaan dibagi 2 atau bahkan di bagi 3 masih oke?"

Pembagian pelaksanaan oleh penulis, bukan keputusan bisnis baru owner: siapkan dua jalur dengan batas file/cabang yang
jelas, Claude OW06 sekaligus integrator tunggal, Codex OW07; orang ketiga opsional untuk pengujian tanpa mengubah kode
produk. Rincian dan urutan gabung di `docs/cp7/handoff/PEMBAGIAN_KERJA_20261022.md`. Ini menggantikan aturan satu writer
untuk seluruh repo pada handoff awal22 Oktober. Tidak mengizinkan perubahan main/kandidat auditor/Enteng/hosted/produksi,
pengiriman WA nyata, pelonggaran tes, atau menganggap salah satu pekerja telah mulai sebelum ada pekerjaan nyata.

### D17-16 (owner ke penulis Claude, 22 Okt 2026 WIB, semua butir tetap lingkup; cara implementasi diperhalus)

Pertanyaan penulis (chat, atas `docs/cp7/PEMBAGIAN_DUA_PENULIS_20261022.md`): "1. Daftar "tunda / sederhanakan / tidak
perlu" di atas disetujui? Ya atau tidak? 2. Apakah kejadian ini ada di pabrik: kelebihan bayar ke laundry yang harus
dikembalikan vendor, atau cuci gagal sebelum tarif vendor diketahui? Ya atau tidak untuk masing-masing."

Owner (persis):

> Bisa, Bos. Semua kebutuhan tetap ada; yang diperhalus itu cara kerjanya supaya sesuai data, nggak dobel hitung, dan gampang dipakai. Ini arahan buat writer:
> Jangan hapus atau menunda seluruh fitur karena concern tadi. Refine implementasinya seperti ini:
>
> * Bayar supplier sekali untuk banyak penerimaan: satu transaksi kas/bank, dengan rincian alokasi ke masing-masing utang. Dukung bayar sebagian, sisa utang, dan pembatalan yang konsisten.
> * Urut/saring seluruh data: berlaku pada seluruh hasil pencarian, termasuk lintas halaman; angka total dan ekspor mengikuti filter yang sama.
> * Status hasil potong: tetap ada, mengikuti kejadian fisik dan progres proses; pengguna bisa memahami apa yang selesai dan apa yang masih tertunda.
> * Model perkiraan pintar: tetap disediakan dengan pemilihan metode berdasarkan kecukupan data. Saat data minim, gunakan metode dasar dan jelaskan keterbatasannya; metode lebih kompleks baru dipakai jika bisa dibuktikan lebih baik lewat pengujian terhadap riwayat. Jangan menjanjikan akurasi yang belum terbukti.
> * Produk baru memakai produk serupa: sistem boleh menyarankan kandidat beserta alasan kemiripannya, lalu pengguna mengonfirmasi atau memilih sendiri. Hasilnya diberi label perkiraan berbasis produk pembanding; kalau tidak ada pembanding layak, nyatakan data belum cukup.
> * Target produksi dengan cadangan: gunakan satu mesin perhitungan yang menyatukan kebutuhan, stok tersedia, WIP yang relevan, pesanan, lama produksi, dan cadangan. Bedakan kapan perlu produksi dengan berapa jumlahnya, serta tampilkan rincian agar cadangan tidak dihitung dua kali.
> * Keuangan/HPP dalam analisis skala pabrik: tetap tersedia memakai sumber perhitungan resmi yang sama dengan laporan. Hasil operasional boleh muncul lebih dulu, sementara bagian keuangan menunjukkan progres dan status kelengkapannya. Kesimpulan yang membutuhkan laba atau biaya harus menunggu angka tersebut siap; pembanding periode dan optimasi kecepatan tetap dikerjakan.
> * Analisis awal otomatis: jalankan setelah data serta konfigurasi minimum siap. Kalau belum siap, tampilkan apa yang kurang dan tombol melengkapinya; hindari analisis berulang tanpa perubahan data.
> * Kain berumus di Ringkasan Gudang: tetap tampil sebagai ringkasan singkat yang bisa dibuka rinciannya, memakai sumber yang sama dengan Pengingat, WA, dan panel titik pesan ulang. Bedakan jelas stok fisik dengan perkiraan kebutuhan.
> * Angka minimum lama di Enteng: tetap tersedia sebagai referensi konfigurasi lama dan diperiksa saat pemasangan. Jelaskan angka mana yang aktif; jangan biarkan aturan lama dan baru berjalan bersamaan tanpa keputusan yang jelas.
> * Saran potong di form Buat Potongan: tampilkan rekomendasi dari mesin yang sama dengan panel rencana, lengkap dengan waktu analisis dan alasannya. Pengguna dapat menerapkan atau mengubah jumlah; sistem memeriksa ulang ketersediaan serta kelayakan saat transaksi disimpan.
>
> Semua tetap masuk scope. Yang menunggu kecukupan data hanya aktivasi metode yang memang membutuhkan data tersebut, bukan keberadaan fiturnya. Implementasi boleh bertahap, tetapi bagian yang belum dibuat tetap dicatat terbuka; jangan dinyatakan selesai hanya karena ada tampilan atau fallback. astra udah selesai check point, baca dan lakukan pembagian ulang dengan poin baru ini, dan apakah ini masuk akal buat lu?

Akibat untuk penulis (ringkasan penulis, bukan kata-kata owner): saran "tunda/sederhanakan/tidak perlu" di dokumen
pembagian ditolak; semua butir tetap lingkup dengan cara implementasi di atas. Pertanyaan 2 (laundry kelebihan bayar, cuci
gagal) tidak dijawab per butir; karena "Semua tetap masuk scope", butir OW-08 itu dikerjakan. Pembagian dua penulis disusun
ulang di `docs/cp7/PEMBAGIAN_DUA_PENULIS_20261022.md` (versi 2).

Catatan penerimaan Penulis B (Codex/Astra, 22 Okt2026): sumber kutipan dan pembagian versi2 diambil dari commit
349a3b30580394f66b29637fcba51ff644e36959 cabang Claude. Pembagian terbaru memindahkan OW07 ke Claude dan produksi/
perencanaan ke B; pembagian OW06-Claude/OW07-Codex sebelumnya digantikan. B menyiapkan cabang astra/d17-14-produksi
dari integrasi a255e48 (produk sama dengan01c5f856; hanya dokumen koordinasi lebih baru). Rincian di d17-14/KOORDINASI.md.
Ini catatan pelaksanaan, bukan keputusan owner baru tentang angka kebijakan atau kepastian tanggal selesai.


### Arahan analisis besar A+B (owner langsung ke Writer B, 26 Oktober 2026 WIB)

Owner (persis):

> Keputusan Bos: analisis besar boleh memakan waktu lebih lama dari 8 detik, asalkan pengguna melihat progres yang jujur dan mengetahui apakah proses sedang berjalan, selesai, atau gagal. Kelonggaran ini khusus pekerjaan besar, bukan untuk semua operasi.

> Jika penyimpanan pilihan memicu perhitungan seluruh pabrik, pisahkan perhitungan berat dari penyimpanannya. Pemeriksaan sumber, kelayakan, dan hak akses saat penyimpanan tetap wajib.

> Hasil yang diterima berdasarkan kebijakan waktu baru harus dicatat sebagai kebijakan baru, bukan mengubah kegagalan lama menjadi keberhasilan.

Pelaksanaan seluruh arahan, termasuk efisiensi, progres nyata, pemulihan, sumber
konsisten, batas per tahap, operasi kecil cepat dan pembagian A/B, dicatat dalam
`d17-14/ow12b/LARGE_ANALYSIS_PROGRESS_20261026.md`. Ini mengganti syarat total8detik
universal untuk pekerjaan besar; tidak memperpanjang semua query atau lock dan
tidak mengubah kegagalan lama menjadi PASS. A tetap integrator; tidak ada izin
produksi atau penutupan scope otomatis.

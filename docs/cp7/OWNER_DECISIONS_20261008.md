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

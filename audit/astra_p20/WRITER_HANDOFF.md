# P20 — handoff terpadu untuk writer

Kandidat produk: `2e605bb7d9b6b7903919b8df2be1443f1740140b`, tree `51935efb12c035496848e2a85590aa18a3ed3d76`.
Seluruh kasus di bawah dijalankan auditor di database disposable. Produk tidak diubah. `production_go:false`.
Status penerimaan: **HOLD**. Perbaikan paling penting adalah F01. Dokumen ini tidak meminta membuka ulang keputusan owner.

## F01 — BLOCKER penerimaan perencanaan: kapasitas lolos 61 dari 60

- Bukti mandiri: [run 37879134926](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37879134926), job `113654511340`, `AS20-32_CROSS_VERSION_CAPACITY`.
- Reproduksi: sediakan dua target/roll berbeda pada kapasitas bersama 60. APPLY v1 sebesar 59 dalam transaksi yang belum commit. Di koneksi kedua, APPLY v2 sebesar 2. V2 berhasil commit sebelum v1 commit; setelah keduanya selesai, dua intent tersimpan berjumlah 61.
- V2 melaporkan `capacity_used_by_other_plans_pcs=0`, `capacity_now_pcs=60`, `CAPACITY=OK`.
- Batas dampak: yang terbentuk adalah Native cutting draft/intents. `material_issue_posted:false`, `reservation_created:false`, `physical_production_confirmed:false`. Ini tidak membuktikan stok fisik atau jurnal berubah.
- Probe: `cases_planning.py`, `probe_plan_race.py`, workflow `astra-p20-plan-race.yml`. Source pendukung: `scripts/cp7-src/plan-native/staged.sql` mengambil `CP7:PLAN_CAPACITY`; jalur v1 di `commands.sql` perlu diperiksa terhadap penguncian/admission yang sama.
- Perbaikan yang dituju: kedua versi harus menilai kapasitas dalam batas transaksi yang sama untuk sumber kapasitas bersama, sesudah kunci yang benar diperoleh. Jaga izin sesudah kunci, replay, dan larangan dua rencana atas potongan yang sama.
- Kriteria retest: v1/v2 dan v2/v1 yang tumpang tindih tidak dapat commit total >60; v2/v2 tetap lulus; 59+1 menjadi kontrol sah; rollback pemenang pertama membolehkan kapasitas dipakai kembali. Tidak boleh mengubah oracle menjadi sekadar peringatan.

## F02 — MAJOR operasional bersyarat: nama cron lintas database bertabrakan

- Bukti: [run 37877803025](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37877803025), `AS20-43_CRON_DATABASE_ISOLATION`.
- Reproduksi: pada satu instance pg_cron dan scheduler role yang sama, install dua job CP7 untuk database disposable A lalu B. Job ID 3 dan 4 yang semula menunjuk A berpindah ke B; daftar job A menjadi kosong.
- Source: `scripts/cp7_schedule.py::install`, nama tetap `cp7-staged-cleanup` dan `cp7-staged-retention`. Fungsi mengaku mengganti job untuk satu database, tetapi nama scheduler tidak unik per database.
- Batas: ini kondisi dua database pada scheduler/role yang sama. Bukan bukti jadwal hosted sudah rusak; hosted tidak disentuh. Jadwal normal, real tick, dan uninstall di satu salinan lulus.
- Kriteria retest: pemasangan B tidak boleh mengubah A; pemasangan ulang harus idempoten; uninstall hanya menghapus job milik target. Nama yang memasukkan identitas database atau penolakan tabrakan sebelum perubahan sama-sama dapat memenuhi oracle.

## F03 — MINOR, utilitas backup: retry dengan nama detik sama menimpa receipt

- Bukti: run operasional di atas, `AS20-45_FAILED_RETRY_COLLISION`.
- Satu backup valid benar-benar di-dump dan di-restore. Percobaan gagal dari database sumber yang tidak ada, pada timestamp simulasi yang sama dan folder yang sama, mengganti receipt menjadi `restore_verified:false`.
- SHA256 dump tetap sama; SHA256 receipt berubah. **Tidak ada bukti file dump lama hilang.** Yang rusak adalah keterikatan bukti verifikasi lama dengan filenya.
- Source: `scripts/cp7_nightly_backup.py::backup`; basename hanya memakai timestamp sampai detik, receipt ditulis tanpa pengecekan benturan.
- Batas: waktu tabrakan disimulasikan; dump/restore/failure nyata. Workflow templat mempunyai concurrency group, sehingga probe ini bukan bukti benturan pada jalur nightly tunggal yang diserialkan. Relevan untuk pemanggilan utilitas di luar jalur itu atau tujuan penyimpanan bersama.
- Kriteria retest: benturan ditolak sebelum menimpa artefak, atau setiap percobaan punya nama unik; percobaan gagal mempertahankan dump **dan receipt** valid lama. Pertahankan uji 15 restore nyata → 14 malam disimpan dan malam gagal tidak memangkas.

## F04 — MINOR/batas detektor, tidak terbukti sebagai jalur korupsi pengguna

- Bukti: [run 37877802981](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37877802981), `AS20-39_VALIDATION_NEGATIVE`.
- Pada salinan yang **sengaja dilemahkan** untuk kontrol negatif, perubahan nilai plan target, scope kosong, rentang metadata halaman, dan totals kosong masih mendapat respons `CLEANED` beserta jumlah baris kerja yang akan dihapus.
- Setiap pemanggilan dalam kontrol ini di-rollback. Tidak ada penghapusan produksi atau klaim bahwa pengguna biasa bisa melakukan mutasi tersebut.
- Kontrol tanpa melemahkan trigger menolak mutasi dengan `55000 / CP7_RUN_IMMUTABLE`. Header/body halaman, identity, dan target yang hilang mempunyai deteksi yang bekerja.
- Source: verifier/cleanup dalam `scripts/cp7-src/planning/analysis-stages.sql`.
- Tindakan: jangan menyebut verifikasi ini membuktikan seluruh isi indeks semantik. Jika cakupan detektor diperluas, ikat isi indeks/scope/rentang/totals ke hasil final dan jalankan kontrol negatif masing-masing. Jangan melemahkan immutable guard. Ini bukan blocker tambahan karena jalur mutasinya memerlukan pengaman salinan sengaja dimatikan.

## F05 — MINOR produk, tetapi gate bukti gagal: harness finalizer basi

- [Run shell pertama 37878853771](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37878853771), job `113653612762`.
- `python scripts/cp7_probe_evidence_test.py` gagal `NameError: p19_plan_v2 is not defined`. Test mengeksekusi AST finalizer aktual, tetapi environment mock belum membawa flag yang dipakai finalizer tersebut. Perintah itu memang ada di `.github/workflows/cp7-shell.yml`.
- Ini cacat alat uji writer; bukan bukti salah hitung uang di aplikasi. Pertahankan first failure. Perbaiki mock agar menjalankan seluruh kontrol negatif asli; jangan melewati test atau mengubah keluaran wajib menjadi lulus.
- [Kelanjutan shell 37879768174](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37879768174) menjalankan langkah yang tadinya terlewat: 1.722 unit test, security/build, dan 6 browser shell lulus. Ini tidak menghapus kegagalan gate pertama.
- Rapikan juga metadata laporan yang tertinggal: schedule menyatakan expected70 tetapi actual71; P18 full cycle expected1 tetapi actual2. Kedua suite benar-benar menjalankan kasus tambahan dan lulus; ini **bukan** kasus yang hilang. Cocokkan header dengan budget aktual, tanpa mengurangi pengujian.

## Yang tidak perlu diperbaiki karena kesalahan alat/oracle auditor

- Perbedaan hash retained rows akibat serialisasi timestamptz dalam zona waktu berbeda: ditutup oleh comparator UTC dan kontrol negatif; semua field tetap dibandingkan.
- AP intermediate `61.648683507697`: tepat sebagai operand eksak. Public payable61.65 dibayar61.65 dan residual0; bukan ghost debt.
- 5.001 target: benar-benar ditolak sebelum hasil selesai (`FAILED`, `run_id:null`, `units_done:0`). Assertion auditor yang menuntut literal `TARGET_LIMIT` terlalu spesifik. Tidak meminta mengganti error code agar tes auditor hijau.
- Kegagalan awal fixture izin receipt, matching refs, v1 assumption IDs, dan duplikasi nomor dua invoice WIB adalah kesalahan setup auditor. Guard produk bekerja; oracle inti tetap.
- Browser awal membaca placeholder terlalu cepat. Probe auditor diperbaiki; 48 rute desktop dan 48 rute mobile kemudian menunggu halaman nyata dan lulus.

## Batas pemasangan dan penyerahan kandidat revisi

1. Serahkan SHA+tree baru, diff terhadap `2e605bb7`, dan bukti writer per kasus. Auditor membekukan kandidat revisi lalu mengulang kasus terkait serta regresi yang relevan. Jangan push ke cabang audit atau mengubah oracle auditor.
2. Area optimasi timeline yang Astra tulis dalam PR44 memerlukan penerimaan auditor lain; hasil di sini tidak menutup konflik kepentingan itu.
3. Jadwal dan backup tetap belum dipasang pada database asli. Sesudah penerimaan yang diperlukan, izin pemasangan owner, konfigurasi nyata yang sudah terdaftar, dan tujuan backup di luar runner harus konkret; gladi P21 bukan pemasangan.
4. K4 (lanjut di server setelah browser ditutup), pengiriman WA nyata, serta konfigurasi operasional yang memang masih pending bukan bug baru dan tidak dibuka ulang sebagai keputusan bisnis.
5. Semua perbaikan dilakukan writer pada jalurnya sendiri. Tidak ada perubahan kode aplikasi, cabang writer/main/integration, deployment, atau hosted database dari audit ini.

## Tambahan setelah kelanjutan mandiri

23 kasus tambahan sudah dituntaskan pada produk yang sama; tidak ada temuan produk baru yang terkonfirmasi dari kelanjutan ini. Lihat CONTINUATION_RESULTS.md dan REPORT.md untuk bukti per kasus. F01–F05 tetap berlaku. Kontrol tambahan yang lulus tidak membuktikan temuan lama sudah diperbaiki.

Writer tidak perlu memperbaiki urutan input yang dikembalikan allocator, akun WIP attendance, akun bersaldo nol setelah pembatalan, atau penolakan akibat setup aktor dan mode QC auditor. Kesalahan tersebut telah dipisahkan, diuji atau direkonsiliasi terhadap fakta runtime dan kontrak, dengan first failure tetap tersimpan. Kode produk tidak diubah.

Bukti positif tambahan untuk memilih regresi revisi: diskon invoice besar; extra jasa per ukuran; invoice bahan datang setelah jual/retur; kredit retur supplier lintas invoice; koreksi setelah tutup buku; payroll pekerja bernama sama; benturan QC, worker, publikasi laporan, dan carry; pencabutan izin pada11endpoint; batas PL5; PL8 setelah grup dibuka kembali; netting, jadwal, dan prioritas; serta perjalanan browser GradeA/B dengan respons hilang dan pembatalan lengkap. Asal oracle mandiri tetap dipisahkan dari1.256eksekusi suite writer.

Saat kandidat revisi diserahkan, retest F01–F05 dan bagian yang mungkin terdampak perubahan. Tidak perlu mengulang seluruh kasus yang aman tanpa alasan. PR44 tetap memerlukan penerimaan auditor bebas konflik. `production_go:false`.

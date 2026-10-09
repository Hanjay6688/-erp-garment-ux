# Handoff audit independen Sol — P20 + K4 + PR44

**Candidate:** `8cc1b0818fdba54f3ebeb64e132f7f3e20309e24`.
**Tree:** `2ea854abca572afa923297b0c304e92703ede136`.
**Putusan:** lima temuan P20 lama selesai sesuai batasnya; PR44 pada candidate ini lulus. **Paket gabungan HOLD untuk penutupan bersih: satu temuan baru S2 masih terbukti FAIL.** Tidak ditemukan temuan baru S0/S1 pada cakupan ini. Produksi tetap belum GO.

| Bagian | Putusan | Bukti yang memutuskan |
|---|---|---|
| P20 F01 — kapasitas v1/v2 | PASS | Batas 60: 59+2 ditolak kedua arah; 59+1 diterima; rollback melepas kapasitas; v2/v2 tetap aman |
| P20 F02 — jadwal lintas database | PASS | A tidak dipindahkan oleh pemasangan B; reinstall mempertahankan ID; collision ditolak sebelum perubahan; uninstall hanya target |
| P20 F03 — retry backup detik sama | PASS | Dump dan receipt terverifikasi tetap identik; retry mendapat nama baru; collision ditolak sebelum tulis; kegagalan tidak memangkas backup |
| P20 F04 — batas verifier cleanup | PASS pada batas yang dinyatakan | Dokumen sekarang jujur: indeks semantik tidak dihitung ulang; guard immutable tetap berlaku. Ini penutupan batas klaim, bukan penambahan detektor |
| P20 F05 — finalizer bukti | PASS | Tujuh kontrol finalizer asli lulus, termasuk kegagalan restore dan ID pengganti; deklarasi kasus serta restore/advisor diperiksa dari artefak audit |
| K4 fungsi utama | PASS pada 16 kasus standar | Server menyelesaikan; akses dicabut/berubah ditolak; unit sekali; batas 8 detik; pg_cron asli; buka ulang hasil yang sama |
| K4 awal dua tick bersamaan | **FAIL — SOL-K4-01, S2** | Tabel runner baru masih kosong: tick kedua menunggu transaksi tick pertama sebelum masuk ke langkahnya |
| PR44 pada candidate 8cc | PASS, cakupan SQL | 235 perbandingan penuh, 17 macam refusal, 121 supply events; dua mutant salah ditangkap; benchmark juga identik |

## Satu revisi produk yang diminta: SOL-K4-01

**Lokasi:** `scripts/cp7-src/planning/analysis-stages.sql`, `cp7_analysis_stage.run_next()`, cabang `else INSERT INTO runner ... ON CONFLICT DO NOTHING`.

**Pemicu:** instalasi baru, `runner` belum berisi baris; dua tick server masuk ketika unit pertama belum commit. Kedua transaksi melihat tabel kosong. INSERT kedua tetap menunggu unique-index transaction milik INSERT pertama. `SKIP LOCKED` pada cabang UPDATE tidak mencakup cabang INSERT ini.

**Bukti paket lengkap:** [run 37954972794](https://github.com/Hanjay6688/-erp-garment-ux/actions/runs/37954972794), kasus `SOL_COLD_START`: `initial_runner_rows=0`, `second_wait_event=transactionid`, ungranted `ShareLock`; tick kedua belum mencapai INSERT output setelah 1,5 detik. Setelah gate dilepas, kedua job maju `[1,1]`, output tetap dua dan unik. Kontrol `SOL_WARM_START` mencapai INSERT output pada kedua tick secara bersamaan. Tidak ada fungsi produk diganti atau trigger dinonaktifkan untuk reproduksi ini.

**Dampak terukur:** serialisasi awal pada dua pemanggil server bersamaan. Tidak ditemukan duplikasi, salah hitung, atau kehilangan output. Tidak terbukti sebagai kemacetan permanen. Satu job pg_cron biasa tidak otomatis menghasilkan dua tick paralel; jangan membesar-besarkan temuan ini menjadi korupsi stok/uang.

**Saran revisi:** beri inisialisasi heartbeat pengaman yang tidak menunggu. Pilihan kecil: `pg_try_advisory_xact_lock` dengan key privat khusus heartbeat, sebelum membaca/membuat baris runner. Bila key sedang dipegang tick lain, lewati penulisan heartbeat dan **tetap lanjutkan pemilihan job**. Jangan menjadikan key tersebut mutex untuk seluruh penjalan, karena itu kembali menahan pekerjaan lain. Pertahankan pemeriksaan isolation/statement timeout sebelum perubahan, limit 8 detik, dan penguncian per job saat ini. Hindari mengisi waktu heartbeat palsu yang membuat UI mengaku server aktif sebelum tick nyata.

**Tes penutup:** jalankan `cold_runner.py` dan `sol_p20_k4_installed_probe.py` pada SHA revisi baru. Cold dan warm sama-sama harus mencapai langkah masing-masing tanpa menunggu heartbeat, tiap job/unit tetap disimpan sekali, actor/claims dipulihkan, akses berubah tetap membatalkan unit. Tambahkan kasus cold start ke deklarasi K4 writer; kasus dua tick sekarang sudah melakukan tick pemanasan sebelum pengujian dua job. Jalankan regresi K4 + staged + K3 pada SHA itu. Temuan kapasitas yang tidak berubah tidak perlu dibuka kembali tanpa delta baru.

## Yang sudah diuji dan yang belum

- Empat kelompok regresi audit: **71/71 PASS**, dengan ID/deklarasi, restore katalog/data dan advisor gate diverifikasi. Klaim writer **15 workflow / 44 job** juga cocok dengan metadata GitHub dan SHA 8cc; angka tersebut bukan jumlah kasus produk.
- PR44: 235 perbandingan SQL PASS; mutant reuse hanya berdasarkan key dan mutant mengabaikan supply sama-sama gagal sesuai harapan. Pada 300 target: tanpa WIP 1.224 ms → 723 ms (41%); 40 posisi WIP 1.567 ms → 1.098 ms (30%). Ini benchmark fixture SQL, bukan SLA aplikasi/produksi.
- Cold start **sudah diuji dan masih bermasalah**; bukan batas yang belum dites. Ada dua reproduksi: kernel PostgreSQL native dan paket ERP lengkap dengan `step()` asli.
- Beban 5.000 target melalui runner K4 seluruhnya belum dijalankan ulang auditor. Receipt writer untuk scale tersedia dan hijau; uji K4 auditor memakai 3 target pada fixture native dan 1 target pada browser. Jangan menyebutnya bukti audit K4 5.000 target atau SLA pabrik.
- Browser adalah Chromium desktop/mobile pada CI. Desktop menutup tab; mobile menekan Berhenti memantau kemudian reload. Belum ada uji HP fisik, Safari, atau tab mobile benar-benar ditutup pada putaran ini.
- Jadwal produksi/backup produksi belum dipasang oleh audit ini. Tidak ada perubahan source produk, main, data asli atau database hosted.

Baca [REPORT.md](REPORT.md) untuk identitas dan batas putusan, [FINDINGS.json](FINDINGS.json) untuk data revisi, dan [CI_INDEX.json](evidence/CI_INDEX.json) untuk run, SHA serta digest artefak. Script reproduksi berada di folder audit ini dan `scripts/sol_p20_k4_installed_probe.py`. Kegagalan pertama dipertahankan; tidak ada assertion, timeout, budget kasus, atau oracle produk yang dilonggarkan.
